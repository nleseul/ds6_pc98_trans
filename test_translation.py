import configparser
import re
import sys
from ds6_util import *
from build_patch import *


if __name__ == '__main__':
    sector_key_str = sys.argv[1]
    match = re.search("^([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})\.([0-9a-fA-F]{2})$", sector_key_str)
    sector_key = (int(match.group(1), base=16), int(match.group(2), base=16), int(match.group(3), base=16))

    packing_strategy = sys.argv[2] if len(sys.argv) > 2 else None
    
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    with open(config['OriginalScenarioDisk'], 'rb') as scenario_disk:
        scenario_directory = get_scenario_directory(scenario_disk)
        combat_directory = get_combat_directory(scenario_disk)

        if sector_key in scenario_directory:
            print(f"Reading scenario {format_sector_key(sector_key)}...")
            sector_info = scenario_directory[sector_key]
            event_list, global_refs = extract_scenario_events(scenario_disk, sector_key, sector_info)
            trans = load_translations_csv(f"csv/Scenarios/{format_sector_key(sector_key)}.csv")
            base_addr = 0xe000
        elif sector_key in combat_directory:
            print(f"Reading combat {format_sector_key(sector_key)}...")
            sector_info = combat_directory[sector_key]
            event_list, global_refs = extract_combat_events(scenario_disk, sector_key, sector_info)
            trans = load_translations_csv(f"csv/Combats/{format_sector_key(sector_key)}.csv")
            base_addr = 0xdc00
        else:
            raise Exception(f"Sector key {format_sector_key(sector_key)} is neither a scenario nor a combat.")

        for global_ref in global_refs:
            print(f"Global ref: {global_ref['source_addr']:04x} -> {global_ref['target_addr']:04x}{' (Event)' if 'is_event' in global_ref and global_ref['is_event'] else ''}")

        data_length = sector_info['sector_length'] * len(sector_info['sector_addresses'])
        translation_count = len([t for t in trans.values() if 'translation' in t])
        space_at_end_length = (base_addr + data_length - sector_info['space_at_end_length'] + 1, base_addr + data_length - 1) if sector_info['space_at_end_length'] > 0 else None
        print(f"Translated {translation_count}/{len(event_list)} events ({100 * translation_count / len(event_list)}%)")

        encoded_translations = encode_translations(event_list, trans)
        relocations = relocate_events(event_list, encoded_translations, space_at_end_length, packing_strategy)
        reference_changes = update_references(event_list, relocations, encoded_translations)

        for event_addr, event_info in event_list.items():
            if event_addr in relocations:
                print(f"Event {event_addr:04x} relocated to {relocations[event_addr]:04x}")

                for translation_addr, translation_info in encoded_translations.items():
                    if translation_info['orig_event_addr'] == event_addr and translation_addr != event_addr:
                        if translation_addr in relocations:
                            print(f"  New event {translation_addr:04x} split out and relocated to {relocations[translation_addr]:04x}")
                        else:
                            print(f"  New event {translation_addr:04x} split out, but not relocated")

                for locator_addr, locator_offset in encoded_translations[event_addr]['locators'].items():
                    print(f"  Locator at {locator_addr:04x} relocated to {relocations[locator_addr]:04x}")
                for ref_info in event_info['references']:
                    if 'source_event_addr' not in ref_info:
                        print(f"  Fixed reference to {ref_info['target_addr']:04x} at {ref_info['source_addr']:04x} updated to {reference_changes[ref_info['source_addr']]:04x}")
            else:
                print(f"Event {event_addr:04x} was not relocated.")

            if event_addr in encoded_translations:
                translation_info = encoded_translations[event_addr]
                for offset, target_addr in translation_info['references']:
                    if target_addr in relocations:
                        print(f"  Reference to {target_addr:04x} at offset {offset:x} updated to {relocations[target_addr]:04x}")
                    else:
                        print(f"  Reference to {target_addr:04x} at offset {offset:x} was not updated")