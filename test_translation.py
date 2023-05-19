import configparser
import re
import sys
from ds6_util import *
from build_patch import *


if __name__ == '__main__':
    sector_key_str = sys.argv[1]
    match = re.search("^([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})$", sector_key_str)
    sector_key = (int(match.group(1), base=16), int(match.group(2), base=16), int(match.group(3), base=16))
    
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    with open(config['OriginalScenarioDisk'], 'rb') as scenario_disk:
        scenario_directory = get_scenario_directory(scenario_disk)
        combat_directory = get_combat_directory(scenario_disk)

        if sector_key in scenario_directory:
            print(f"Reading scenario {format_sector_key(sector_key)}...")
            sector_info = scenario_directory[sector_key]
            event_list = extract_scenario_events(scenario_disk, sector_key, sector_info)
            trans = load_translations_csv(f"csv/Scenarios/{format_sector_key(sector_key)}.csv")
            base_addr = 0xe000
        elif sector_key in combat_directory:
            print(f"Reading combat {format_sector_key(sector_key)}...")
            sector_info = scenario_directory[sector_key]
            event_list = extract_combat_events(scenario_disk, sector_key, sector_info)
            trans = load_translations_csv(f"csv/Combats/{format_sector_key(sector_key)}.csv")
            base_addr = 0xdc00
        else:
            raise Exception(f"Sector key {format_sector_key(sector_key)} is neither a scenario nor a combat.")

        data_length = sector_info['sector_length'] * len(sector_info['sector_addresses'])
        translation_count = len([t for t in trans.values() if 'translation' in t])
        print(f"Translated {translation_count}/{len(event_list)} events ({100 * translation_count / len(event_list)}%)")

        encoded_translations = encode_translations(event_list, trans)
        relocations = relocate_events(event_list, encoded_translations, (base_addr + data_length - sector_info['space_at_end_length'] + 1, base_addr + data_length - 1))
        reference_changes = update_references(event_list, relocations, encoded_translations)

        for event_addr, event_info in event_list.items():
            print(f"Event {event_addr:04x} relocated to {relocations[event_addr]:04x}")
            for locator_addr, locator_offset in encoded_translations[event_addr]['locators'].items():
                print(f"  Locator at {locator_addr:04x} relocated to {relocations[locator_addr]:04x}")
            for ref_info in event_info['references']:
                if 'source_event_addr' not in ref_info:
                    print(f"  Fixed reference to {ref_info['target_addr']:04x} at {ref_info['source_addr']:04x} updated to {reference_changes[ref_info['source_addr']]:04x}")