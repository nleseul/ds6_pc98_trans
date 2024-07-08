import sys
from PIL import Image

def load_bitplanes_from_image_file(image_file_name):
    image = Image.open(image_file_name)

    planes = [[], [], []]
    for row in range(image.height):
        for plane in range(3):
            planes[plane].append(bytearray(image.width // 8))
        for col in range(image.width):
            pixel_color = image.getpixel((col, row))
            byte_index = col // 8
            bit_index = 7 - (col % 8)

            is_red = pixel_color[0] >= 200
            is_green = pixel_color[1] >= 200
            is_blue = pixel_color[2] >= 200

            if is_red:
                planes[1][row][byte_index] |= (1 << bit_index)
            if is_green:
                planes[2][row][byte_index] |= (1 << bit_index)
            if is_blue:
                planes[0][row][byte_index] |= (1 << bit_index)

    return planes

def load_image_from_bitplanes(planes):
    width = len(planes[0][0] * 8)
    height = len(planes[0])

    image = Image.new("RGB", (width, height))

    for row in range(height):
        for col in range(width):
            byte_index = col // 8
            bit_index = 7 - (col % 8)
            if byte_index < 0x8000:

                is_red = (planes[1][row][byte_index] & (1 << bit_index) != 0)
                is_green = (planes[2][row][byte_index] & (1 << bit_index) != 0)
                is_blue = (planes[0][row][byte_index] & (1 << bit_index) != 0)

                image.putpixel((col, row), (220 if is_red else 0, 220 if is_green else 0, 220 if is_blue else 0))

    return image


def encode_row_rle(row):
    counts = []
    for byte in row:
        if len(counts) == 0 or counts[-1]['byte'] != byte:
            counts.append( { 'byte': byte, 'count': 1 } )
        else:
            counts[-1]['count'] += 1

    segments = []
    for count in counts:
        if len(segments) == 0 or count['count'] > 2:
            segments.append( { 'rle_byte': count['byte'], 'rle_count': count['count'] } )
        elif 'raw_bytes' in segments[-1]:
            segments[-1]['raw_bytes'] += bytearray([count['byte']] * count['count'])
        else:
            segments.append( { 'raw_bytes': bytearray([count['byte']] * count['count']) } )

    encoded = bytearray()
    for segment in segments:
        if 'rle_byte' in segment:
            encoded.append(segment['rle_count'])
            encoded.append(segment['rle_byte'])
        else:
            encoded.append(len(segment['raw_bytes']) | 0x80)
            encoded += segment['raw_bytes']

    return encoded


def encode_diffs(planes, original_plane, original_row, new_row_data):
    original_row_data = planes[original_plane][original_row]

    if len(original_row_data) != len(new_row_data):
        raise Exception("Not same length")

    diff_list = []
    total_count = 0
    for index, (original_byte, new_byte) in enumerate(zip(original_row_data, new_row_data)):
        if original_byte != new_byte:
            total_count += 1
            if len(diff_list) > 0 and diff_list[-1]['count'] < 3 and diff_list[-1]['index'] == index - diff_list[-1]['count']:
                diff_list[-1]['count'] += 1
            else:
                diff_list.append( { 'index': index, 'count': 1} )

    if total_count < 0x2a:
        encoded = bytearray()

        encoded.append((total_count + original_plane * 0x2a) | 0x80)
        encoded.append(original_row)
        for diff in diff_list:
            encoded.append(diff['index'] + (diff['count'] - 1) * 0x50)
            for offset in range(diff['count']):
                encoded.append(new_row_data[diff['index'] + offset])

        return encoded
    else:
        return None


def find_optimal_diff(planes, current_row, current_plane):
    new_row_data = planes[current_plane][current_row]

    best_encoded_diff = None

    for row_index in range(current_row + 1):
        for plane_index in range(current_plane if current_row == row_index else 3):
            encoded_diff = encode_diffs(planes, plane_index, row_index, new_row_data)
            if encoded_diff is not None and (best_encoded_diff is None or len(encoded_diff) < len(best_encoded_diff)):
                best_encoded_diff = encoded_diff

    return best_encoded_diff


def encode_bitplanes(planes, draw_position, magic_offset):

    width = len(planes[0][0] * 8)
    height = len(planes[0])

    encoded = bytearray()
    encoded += (draw_position[1] * 80 + draw_position[0] + magic_offset).to_bytes(2, byteorder='little')
    encoded += (height * 3).to_bytes(2, byteorder='little')
    encoded += (width // 8).to_bytes(2, byteorder='little')

    for row in range(len(planes[0])):
        for plane in range(3):
            optimal_diff = find_optimal_diff(planes, row, plane)
            if optimal_diff is None:
                encoded += encode_row_rle(planes[plane][row])
            else:
                encoded += optimal_diff

    return encoded


def decode_bitplanes(in_file, magic_offset = 0):
    start_addr = int.from_bytes(in_file.read(2), byteorder='little')

    start_addr_with_offset = start_addr - magic_offset
    if start_addr_with_offset < 0:
        start_addr_with_offset += 0x10000

    start_x = start_addr_with_offset % 80
    start_y = start_addr_with_offset // 80

    total_row_count = int.from_bytes(in_file.read(2), byteorder='little')
    bytes_per_row = int.from_bytes(in_file.read(2), byteorder='little')

    height = total_row_count // 3

    planes = [[], [], []]

    for row_index in range(height):
        for plane_index in range(3):
            current_row = bytearray()

            first_count = int.from_bytes(in_file.read(1), byteorder='little')

            is_diff_row = (first_count & 0x80) != 0

            if is_diff_row:
                diff_byte_count = first_count & 0x7f
                source_plane = 0
                for _ in range(2):
                    if diff_byte_count >= 0x2a:
                        diff_byte_count -= 0x2a
                        source_plane += 1
                source_row = int.from_bytes(in_file.read(1), byteorder='little')
                current_row = planes[source_plane][source_row].copy()

                while diff_byte_count > 0:
                    diff_length = 1
                    diff_offset = int.from_bytes(in_file.read(1), byteorder='little')
                    for _ in range(2):
                        if diff_offset >= 0x50:
                            diff_offset -= 0x50
                            diff_length += 1
                    diff_bytes = in_file.read(diff_length)

                    current_row[diff_offset:diff_offset+diff_length] = diff_bytes

                    diff_byte_count -= diff_length
            else:
                remaining_bytes = bytes_per_row
                while remaining_bytes > 0:
                    if remaining_bytes == bytes_per_row:
                        count = first_count
                    else:
                        count = count = int.from_bytes(in_file.read(1), byteorder='little')

                    if (count & 0x80) != 0:
                        # Copy the next n bytes
                        bytes_to_write = in_file.read(count & 0x7f)
                    else:
                        if count == 0:
                            raise Exception("This probably shouldn't happen?")
                        # Repeat the next byte n times
                        bytes_to_write = in_file.read(1) * count
                    current_row += bytes_to_write
                    remaining_bytes -= len(bytes_to_write)

            planes[plane_index].append(current_row)

    return start_x, start_y, planes


def explain_encoded_image(in_file, out_file=sys.stdout, magic_offset = 0):
    start_addr = int.from_bytes(in_file.read(2), byteorder='little')

    start_addr_with_offset = start_addr - magic_offset
    if start_addr_with_offset < 0:
        start_addr_with_offset += 0x10000

    start_x = start_addr_with_offset % 80
    start_y = start_addr_with_offset // 80

    total_row_count = int.from_bytes(in_file.read(2), byteorder='little')
    bytes_per_row = int.from_bytes(in_file.read(2), byteorder='little')

    width = bytes_per_row * 8
    height = total_row_count // 3

    print(f"Start address is {start_addr:04x} ({start_x, start_y}, offset by {magic_offset:04x})", file=out_file)
    print(f"Width is {width} ({bytes_per_row} bytes), height is {height} ({total_row_count} rows)", file=out_file)

    for row_index in range(height):
        for plane_index in range(3):
            print(f"{in_file.tell():6x} Row {row_index}, plane {plane_index}", file=out_file)

            first_count = int.from_bytes(in_file.read(1), byteorder='little')

            is_diff_row = (first_count & 0x80) != 0

            if is_diff_row:
                diff_byte_count = first_count & 0x7f
                source_plane = 0
                for _ in range(2):
                    if diff_byte_count >= 0x2a:
                        diff_byte_count -= 0x2a
                        source_plane += 1
                source_row = int.from_bytes(in_file.read(1), byteorder='little')
                print(f"       Diff from plane {source_plane} row {source_row}, {diff_byte_count} bytes", file=out_file)

                while diff_byte_count > 0:
                    diff_length = 1
                    diff_offset = int.from_bytes(in_file.read(1), byteorder='little')
                    for _ in range(2):
                        if diff_offset >= 0x50:
                            diff_offset -= 0x50
                            diff_length += 1
                    diff_bytes = in_file.read(diff_length)

                    print(f"{in_file.tell():6x}  Apply diff {diff_bytes.hex()} at offset {diff_offset:02x}", file=out_file)

                    diff_byte_count -= diff_length
            else:
                remaining_bytes = bytes_per_row
                while remaining_bytes > 0:
                    if remaining_bytes == bytes_per_row:
                        count = first_count
                    else:
                        count = count = int.from_bytes(in_file.read(1), byteorder='little')

                    if (count & 0x80) != 0:
                        # Copy the next n bytes
                        bytes_to_write = in_file.read(count & 0x7f)
                        print(f"{in_file.tell():6x}  Write {bytes_to_write.hex()} ({count & 0x7f} bytes encoded directly)", file=out_file)
                    else:
                        if count == 0:
                            raise Exception("This probably shouldn't happen?")
                        # Repeat the next byte n times
                        bytes_to_write = in_file.read(1) * count
                        print(f"{in_file.tell():6x}  Write {bytes_to_write.hex()} (repeated {count} times)", file=out_file)
                    remaining_bytes -= len(bytes_to_write)
    print(f"{in_file.tell():6x} Done.", file=out_file)
