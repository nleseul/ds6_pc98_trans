import configparser
import ips_util
import os
from ds6_util import *


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
    encoded_opening = encoded_opening.ljust(0x585, b'\x00')
    event_disk_patch.add_record(0x1b572, encoded_opening)


def event_disk_patch_misc(event_disk_patch):
    # Original text: 
    # プログラムディスクをドライブ１に
    # シナリオディスクを　ドライブ２に
    # セットして【RETURN】キーを
    # 押してください。
    event_disk_patch.add_record(0x1a667, b"Insert the Program Disk into\x01drive 1 and the Scenario Disk\x01into drive 2, then press the\x01\x81\x79RETURN\x81\x7a key.\x0d\x0d\x00")


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
    patch_data_table(program_disk_patch, "csv/Items.csv", 0x1491f, 14, 20)
    patch_data_table(program_disk_patch, "csv/Spells.csv", 0x15243, 8, 11)
    patch_data_table(program_disk_patch, "csv/Locations.csv", 0x1538d, 12, 12)

    # Build the scenario disk
    scenario_disk_patch_misc(scenario_disk_patch)

    # Create patch files
    os.makedirs(os.path.dirname(config['OutputEventDiskPatch']), exist_ok=True)
    open(config['OutputEventDiskPatch'], 'w+b').write(event_disk_patch.encode())
    os.makedirs(os.path.dirname(config['OutputProgramDiskPatch']), exist_ok=True)
    open(config['OutputProgramDiskPatch'], 'w+b').write(program_disk_patch.encode())
    os.makedirs(os.path.dirname(config['OutputScenarioDiskPatch']), exist_ok=True)
    open(config['OutputScenarioDiskPatch'], 'w+b').write(scenario_disk_patch.encode())

    # Apply patches to disks
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