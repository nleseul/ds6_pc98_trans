import configparser
import ips_util
import os
from ds6_util import *
from tempfile import NamedTemporaryFile


def patch_data_table(patch, file_name, disk_addr, max_length, entry_stride):
    translations = load_translations_csv(file_name)
    for context, text_info in translations.items():
        if 'translation' in text_info:
            index = int(context)
            encoded = text_info['translation'].encode('shift-jis')
            if len(encoded) > max_length:
                raise Exception(f"Translation at index {index} of Data/Items is too long! original={text_info['original']}, translation={text_info['translation']} ({len(encoded)} bytes)")
            elif len(encoded) < max_length:
                encoded = encoded.rjust(max_length, b' ')
            patch.add_record(disk_addr + index*entry_stride, encoded)


def patch_menu(patch, base_addr, items, max_length, references):
    patch_data = b''
    offsets = []

    for item in items:
        offsets.append(4 + len(patch_data))
        patch_data += item.encode('shift-jis') + b'\x00'

    if len(patch_data) > max_length:
        raise Exception(f"Not enough space to patch menu at {base_addr:04x}! available={max_length} bytes; used={len(patch_data)} bytes")

    patch.add_record(base_addr - 0x4000 + 0x13e10 + 4, patch_data.ljust(max_length - 4, b'\x00'))
    
    for offset, ref_addr in zip(offsets, references):
        if ref_addr is not None:
            patch.add_record(ref_addr - 0x4000 + 0x13e10, int.to_bytes(base_addr + offset + 1, length=2, byteorder='little'))


def patch_asm(patch, nasm_path, base_addr, max_length, asm_code):
    if isinstance(asm_code, str):
        with NamedTemporaryFile(mode="w+", delete=False) as src_file, NamedTemporaryFile(mode="rb", delete=False) as dest_file:
            src_file_name = src_file.name
            dest_file_name = dest_file.name

            src_file.write("BITS 16\n")
            src_file.write(f"org 0x{base_addr:04x}\n\n")
            src_file.write(asm_code)

        if not os.path.exists(nasm_path):
            raise Exception(f"NASM is not available at the path {nasm_path}!")

        os.system(f"\"{nasm_path}\" {src_file.name} -o {dest_file_name}")

        with open(dest_file_name, "rb") as dest_file:
            encoded = dest_file.read()

        os.remove(src_file_name)
        os.remove(dest_file_name)

    else:
        encoded = asm_code

    print(f"Encoding asm patch at {base_addr:04x} ({len(encoded)}/{max_length} bytes)")

    if len(encoded) > max_length:
        raise Exception(f"Not enough space to patch asm code at {base_addr}! available={max_length} bytes; used={len(encoded)} bytes")
    
    patch.add_record(base_addr - 0x4000 + 0x13e10, encoded.ljust(max_length, b'\x90'))


def event_disk_patch_opening(event_disk_patch):
    # Opening text
    opening_trans = load_translations_csv("csv/Opening.csv")
    encoded_opening = b''
    for opening_index in range(3):
        opening_info = opening_trans[f"{opening_index+1}"]
        if 'translation' in opening_info:
            text = opening_info['translation']
        else:
            text = opening_info['original']
        
        while len(text) > 0:
            if text.startswith("<P>"):
                encoded_opening += b'\x01'
                text = text[3:]
            elif text.startswith("\n"):
                encoded_opening += b'\x00'
                text = text[1:]
            else:
                encoded_opening += text[0:1].encode('shift-jis')
                text = text[1:]
        
        if encoded_opening[-1] != 0x00:
            encoded_opening += b'\x00'
        
        if opening_index == 2:
            encoded_opening += b'\x03'
        else:
            encoded_opening += b'\x02'
        
    
    if len(encoded_opening) > 0x585:
        raise Exception(f"Opening text is too long! {len(encoded_opening)}/{0x585} bytes")
    else:
        print(f"Opening: {len(encoded_opening)}/{0x585} bytes")
        print()
    encoded_opening = encoded_opening.ljust(0x585, b'\x00')
    event_disk_patch.add_record(0x1b572, encoded_opening)


def event_disk_patch_misc(event_disk_patch):
    # Original text: 
    # プログラムディスクをドライブ１に
    # シナリオディスクを　ドライブ２に
    # セットして【RETURN】キーを
    # 押してください。
    event_disk_patch.add_record(0x1a667, b"Insert the Program Disk into\x01drive 1 and the Scenario Disk\x01into drive 2, then press the\x01\x81\x79RETURN\x81\x7a key.\x0d\x0d\x00")


def program_disk_patch_asm(program_disk_patch, nasm_path):
    # Modify the spell name formatter to use half-width digits.
    patch_asm(program_disk_patch, nasm_path, 0xa041, 0xb, '''
        mov al,0x31
        add al,[0x4183]
        stosb
        mov al,0x6
        stosb
        inc di
    ''')
    
    # Modify the first bit of spell/item text to use the passed-in SI instead of just "wa."
    patch_asm(program_disk_patch, nasm_path, 0xa798, 0x21, '''
        mov al,[0x417e]
        and al,0x3
        jz orig_a7b3
        dec al
        jz orig_a7a7
        dec al
        jz orig_a7ad

    orig_a7a7:
        call 0xa7d6
        jnc orig_a7b3
        ret

    orig_a7ad:
        push si
        call 0xa7fb
        pop si
        jnc orig_a7b3
        ret

    orig_a7b3:
        call 0x99ba
        ret
    ''')

    # Modify the second half of spell/item text to display the target as the end of a sentence where appropriate.
    patch_asm(program_disk_patch, nasm_path, 0xa7b9, 0x1d, '''
        mov si,0x57ed

        mov al,[0x417e]
        and al,0x3
        jz orig_a7d1
        mov bx,[0x40d1]
        mov al,[bx]
        cmp al,[di]
        jz orig_a7d1
        mov si,0x57e5
        
    orig_a7d1:
        and al,al
        jmp 0x8559
    ''')

    # Modify the item text to rearrange the order of output.
    patch_asm(program_disk_patch, nasm_path, 0xa1a5, 0x2a, '''
        mov si,0x57fe
        call 0xa798
        jc 0xa1da
        call 0xa7b9
        mov al,[0x419a]
        and al,0x7
        jz orig_a1c3

        mov si,0x4173
        call 0x84d7
        mov si,0x580e
        call 0x8559

    orig_a1c3:
        mov si,[0x40d1]
        call 0xa22d
        jmp 0xa1d8
    ''')

    # Modify the spell text to rearrange the order of output.
    patch_asm(program_disk_patch, nasm_path, 0xa1ed, 0x11, '''
        mov si,0x5866
        call 0xa798
        jc short 0xa22b
        mov si,0x4173
        call 0x84d7
        call 0xa7b9
    ''')

    # Modify the formatting of the save/load text.
    patch_asm(program_disk_patch, nasm_path, 0xb2a7, 0x30, '''
        push si
        mov si,0xb2de
        call 0x8559
        pop si
        call 0x8559

        cmp byte [0x82a],0xa
        jc orig_b2be

        mov si,0xb2d7
        call 0x8559
        jmp orig_b2ce

    orig_b2be:
        call 0x8559

        mov al,[0x82b]
        mov ah,0xa
        mul ah
        add al,byte [0x82a]
        inc al
        call 0x84be

    orig_b2ce:
        jmp 0x7418
    ''')

    # This is the function used to draw compressed text for location names.
    patch_asm(program_disk_patch, nasm_path, 0x893c, 0x33, '''
        push dx
        push cx
        push ax
        pushf
        
        mov cx, 0x00
    
    loop:
        lodsb
        cmp al,0x20
        jc handle_opcode
        cmp al,0x80
        jc handle_char

        jmp loop

    handle_opcode:
        sub al,0x18
        jc done
        jmp loop

    handle_char:
        mov [0x896f], cl
        call 0x8a49
        
        test cx, 1
        jz skip_stuff
        
        call 0x8b07
        inc di
        
    skip_stuff:
        inc cx
        jmp loop
        
    done:
        popf
        pop ax
        pop cx
        pop dx
        ret
    ''')
    
    # Stealing the last byte of the above routine for a local variable.
    program_disk_patch.add_record(0x896f - 0x4000 + 0x13e10, b'\x00')
    
    # This is a helper function used by the compressed text to load each
    # glyph from the font ROM.
    patch_asm(program_disk_patch, nasm_path, 0x8a49, 0x50, '''
        push di
        push dx
        push cx
        push bx
    
        mov dl, al
        mov dh, 0x09
        mov al, 00001011b
        out 01101000b, al
        mov ax, dx
        out 10100001b, al
        xchg al, ah
        out 10100011b, al
        mov di, 0x4076
        mov dl, 0x20
        mov cx, 0x10
        mov bl, 0x0
        
    row_loop:
        push cx
        mov al, dl
        out 10100101b, al
        in al, 10101001b
        mov bh, al
        mov al, dl
        mov cx, 0x8
        
    split_loop:
        rol bx, 1
        rcl ah, 1
        rol bx, 1
        rcl al, 1
        loop split_loop
        
        or al, ah
        
        test byte [0x896f], 1
        jz skip_stuff
        
        shr al, 4
        or al, [di]
    skip_stuff:
        stosb
        stosb
        inc dl
        pop cx
        loop row_loop

        pop bx
        pop cx
        pop dx
        pop di
        ret
    ''')
    
    # Bits of code used to draw the modifying descriptions for overworld
    # location names.
    patch_asm(program_disk_patch, nasm_path, 0xa11e, 0xa, '''
        mov dl, 0x57 ; W
        jnc short 0xa128
        mov dl, 0x45 ; E
        neg ax
    ''')
    patch_asm(program_disk_patch, nasm_path, 0xa133, 0xa, '''
        mov dh, 0x4e ; N
        jnc short 0xa13d
        mov dh, 0x53 ; S
        neg ax
    ''')
    patch_asm(program_disk_patch, nasm_path, 0xa164, 0x3, '''
        mov al, dh
        stosb
    ''')
    patch_asm(program_disk_patch, nasm_path, 0xa173, 0x3, '''
        mov al, dl
        stosb
    ''')

    # Clear out some unnecessary text concatenation used by the Hyper 2000/Hyper 660 item code.
    program_disk_patch.add_record(0xa73a - 0x4000 + 0x13e10, b'\x90' * 0x6)

    print()


def program_disk_patch_misc(program_disk_patch):
    # Miscellaneous program disk text
    program_disk_patch.add_record(0x117a3, b"  \x87\x54  The Prince's Departure  ")
    program_disk_patch.add_record(0x11940, ("Selios".encode('shift-jis') + b'\x06').ljust(0x10, b'\x00'))
    program_disk_patch.add_record(0x11980, ("Runan".encode('shift-jis') + b'\x06').ljust(0x10, b'\x00'))
    program_disk_patch.add_record(0x119c0, ("Roh".encode('shift-jis') + b'\x06').ljust(0x10, b'\x00'))
    program_disk_patch.add_record(0x11a00, ("Gail".encode('shift-jis') + b'\x06').ljust(0x10, b'\x00'))

    program_disk_patch.add_record(0xab7a - 0x4000 + 0x13e10, b"  HELL  \x00  Hard  \x00 Normal \x00  Easy  \x00")

    patch_menu(program_disk_patch, 0x7453,
        [ " Yes", " No" ], 0x11, [ None, None] )

    patch_menu(program_disk_patch, 0xa9c5,
        [ " Buy", " Sell" ], 0x1a, [ ] )

    patch_menu(program_disk_patch, 0xab1f, 
        [ " Previous town", " Restart battle", " Load a save" ], 0x3c, [ None, None, None ] )
    
    patch_menu(program_disk_patch, 0xafb7,
        [ " Spell", " Item", " Equip", " Drop", " Stats", " Other", " Leader" ], 0x36,
        [ 0xb0f4,   0xb12d,  0xb14f,   0xb182,  0xb18e,   None,     0xb1a2 ] )

    patch_menu(program_disk_patch, 0xb1e6, 
        [ " Save", " Load", " System", " Combat" ], 0x2c, 
        [ 0xb213,  0xb235,  0xb2f6,    0xb44b])

    program_disk_patch.add_record(0x1bb89, b" Fight   Spell   Guard\x01 Use     Weapon  Auto\x01 Stats   Run\x07\x00\x00\x00\x00")


def scenario_disk_patch_misc(scenario_disk_patch):
    scenario_disk_patch.add_record(0x79c66, b"Sonia\x06          ")
            
    scenario_disk_patch.add_record(0x5d438, b"  \x87\x55     The Silent Spell     ")
    scenario_disk_patch.add_record(0x88782, b"  \x87\x56    The Mark of Kings     ")
    scenario_disk_patch.add_record(0xa1770, b"  \x87\x57    The Enchanted King    ")

    # Scenario 20.00.20 (pirate minigame)
    scenario_disk_patch.add_record(0x90b63, b"\x30") # Number of wins are changed to a half-width digit.
    scenario_disk_patch.add_record(0x90b75, b"\x90") # Skip only one byte when the number of wins is 1.
    scenario_disk_patch.add_record(0x90d19, b" HP\x00 Attack\x00 Defense\x00 Speed\x00 Left\x00\x00\x00\x00\x00")


if __name__ == '__main__':
    # Setup
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    event_disk_patch = ips_util.Patch()
    program_disk_patch = ips_util.Patch()
    scenario_disk_patch = ips_util.Patch()


    # Build the event disk
    event_disk_patch_opening(event_disk_patch)
    event_disk_patch_misc(event_disk_patch)

    # Build the program disk
    program_disk_patch_misc(program_disk_patch)
    program_disk_patch_asm(program_disk_patch, config['NasmPath'])
    patch_data_table(program_disk_patch, "csv/Items.csv", 0x1491f, 14, 20)
    patch_data_table(program_disk_patch, "csv/Spells.csv", 0x15243, 8, 11)
    patch_data_table(program_disk_patch, "csv/Locations.csv", 0x1538d, 12, 12)

    # Build the scenario disk
    scenario_disk_patch_misc(scenario_disk_patch)

    # Create patch files
    print("Creating patches...")
    print(config['OutputEventDiskPatch'])
    os.makedirs(os.path.dirname(config['OutputEventDiskPatch']), exist_ok=True)
    open(config['OutputEventDiskPatch'], 'w+b').write(event_disk_patch.encode())
    print(config['OutputProgramDiskPatch'])
    os.makedirs(os.path.dirname(config['OutputProgramDiskPatch']), exist_ok=True)
    open(config['OutputProgramDiskPatch'], 'w+b').write(program_disk_patch.encode())
    print(config['OutputScenarioDiskPatch'])
    os.makedirs(os.path.dirname(config['OutputScenarioDiskPatch']), exist_ok=True)
    open(config['OutputScenarioDiskPatch'], 'w+b').write(scenario_disk_patch.encode())
    print()

    # Apply patches to disks
    print("Patching...")

    print(f"{config['OutputEventDiskSource']} -> {config['OutputEventDisk']}")
    os.makedirs(os.path.dirname(config['OutputEventDisk']), exist_ok=True)
    with open(config['OutputEventDiskSource'], 'rb') as event_disk_in, open(config['OutputEventDisk'], 'w+b') as event_disk_out:
        event_disk_out.write(event_disk_patch.apply(event_disk_in.read()))

    print(f"{config['OutputProgramDiskSource']} -> {config['OutputProgramDisk']}")
    os.makedirs(os.path.dirname(config['OutputProgramDisk']), exist_ok=True)
    with open(config['OutputProgramDiskSource'], 'rb') as program_disk_in, open(config['OutputProgramDisk'], 'w+b') as program_disk_out:
        program_disk_out.write(program_disk_patch.apply(program_disk_in.read()))

    print(f"{config['OutputScenarioDiskSource']} -> {config['OutputScenarioDisk']}")
    os.makedirs(os.path.dirname(config['OutputScenarioDisk']), exist_ok=True)
    with open(config['OutputScenarioDiskSource'], 'rb') as scenario_disk_in, open(config['OutputScenarioDisk'], 'w+b') as scenario_disk_out:
        scenario_disk_out.write(scenario_disk_patch.apply(scenario_disk_in.read()))