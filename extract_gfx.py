import configparser
import os
from ds6_gfx_util import *

if __name__ == '__main__':
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    os.makedirs("gfx/Event", exist_ok=True)

    with open(config['OriginalEventDisk'], 'rb') as event_disk:
        event_disk.seek(0x11610)
        for segment in range(2):
            segment_start_addr = event_disk.tell()
            x, y, boot_screen_planes = decode_bitplanes(event_disk)
            boot_screen_image = load_image_from_bitplanes(boot_screen_planes)
            boot_screen_image.save(f"gfx/Event/boot_screen_{segment}.png")
            print(f"{segment_start_addr:4x}~{event_disk.tell():x} - ({x}, {y})")

            event_disk.read(1)

    os.makedirs("gfx/Program", exist_ok=True)

    with open(config['OriginalProgramDisk'], 'rb') as program_disk:
        program_disk.seek(0x2ea10)
        _, _, function_bar_planes = decode_bitplanes(program_disk, 0xc000)
        function_bar_image = load_image_from_bitplanes(function_bar_planes)
        function_bar_image.save("gfx/Program/function_bar.png")