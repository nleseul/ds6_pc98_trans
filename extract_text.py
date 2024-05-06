import configparser
import csv
import os
from ds6_util import *


def import_data_table(disk, filename, start_disk_addr, entry_count, text_length, entry_stride):
    with open(filename, 'w+', encoding='utf8', newline='') as out_file:
        csv_writer = csv.writer(out_file, quoting=csv.QUOTE_ALL)

        disk.seek(start_disk_addr)
        for index in range(entry_count):
            text = disk.read(text_length).decode('shift-jis')
            disk.read(entry_stride - text_length)

            csv_writer.writerow( [index, text] )



if __name__ == '__main__':
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    with open(config['OriginalScenarioDisk'], 'rb') as scenario_disk:
        print("Extracting scenarios...")
        scenario_directory = get_scenario_directory(scenario_disk)

        os.makedirs("csv/Scenarios", exist_ok=True)
        
        for scenario_key, scenario_info in scenario_directory.items():
            print(f"\r{format_sector_key(scenario_key)}", end='')
            scenario_events = extract_scenario_events(scenario_disk, scenario_key, scenario_info)

            if len(scenario_events) == 0:
                continue

            with open(f"csv/Scenarios/{format_sector_key(scenario_key)}.csv", 'w+', encoding='utf8', newline='') as csv_out:
                csv_writer = csv.writer(csv_out, quoting=csv.QUOTE_ALL, lineterminator=os.linesep)
                for start_addr, event_info in scenario_events.items():
                    csv_writer.writerow([f"{start_addr:04x}", event_info['text']])
        print()

        print("Extracting combats...")
        combat_directory = get_combat_directory(scenario_disk)

        os.makedirs("csv/Combats", exist_ok=True)

        for combat_key, combat_info in combat_directory.items():
            print(f"\r{format_sector_key(combat_key)}", end='')
            combat_events = extract_combat_events(scenario_disk, combat_key, combat_info)

            if len(combat_events) == 0:
                continue

            with open(f"csv/Combats/{format_sector_key(combat_key)}.csv", 'w+', encoding='utf8', newline='') as csv_out:
                csv_writer = csv.writer(csv_out, quoting=csv.QUOTE_ALL, lineterminator=os.linesep)
                for start_addr, event_info in combat_events.items():
                    csv_writer.writerow([f"{start_addr:04x}", event_info['text']])
        print()

    with open(config['OriginalProgramDisk'], 'rb') as program_disk:
        print("Extracting data tables...")
        import_data_table(program_disk, "csv/Items.csv", 0x1491f, 117, 14, 20)
        import_data_table(program_disk, "csv/Spells.csv", 0x15243, 30, 8, 11)
        import_data_table(program_disk, "csv/Locations.csv", 0x1538d, 51, 12, 12)

    with open(config['OriginalEventDisk'], 'rb') as event_disk:
    
        print("Extracting opening text...")
        with open("csv/Opening.csv", 'w+', encoding='utf8', newline='') as csv_out:
            csv_writer = csv.writer(csv_out, quoting=csv.QUOTE_ALL, lineterminator=os.linesep)

            opening_string = ""
            opening_string_count = 0
            event_disk.seek(0x1b572)
        
            while True:
                next_byte = event_disk.peek()[0]
                if next_byte == 0x01:
                    event_disk.read(1)
                    opening_string += "<P>"
                elif next_byte == 0x02 or next_byte == 0x03:
                    event_disk.read(1)

                    csv_writer.writerow([opening_string_count + 1, opening_string])
                    
                    opening_string = ""
                    opening_string_count += 1
                    if next_byte == 0x03:
                        break
                else:
                    string_bytes = bytearray()
                    while True:
                        string_bytes += event_disk.read(1)
                        if string_bytes[-1] == 0x00:
                            string_bytes = string_bytes[:-1]
                            break
                    opening_string += string_bytes.decode('shift-jis')
                    opening_string += "\n"

        print("Extracting ending text...")
        with open("csv/Ending.csv", "w+", encoding='utf8', newline='') as csv_out:
            csv_writer = csv.writer(csv_out, quoting=csv.QUOTE_ALL, lineterminator=os.linesep)
            for ending_info in get_ending_strings():
                event_disk.seek(0x14a10 + ending_info['addr'])
                ending_string = read_ending_string(event_disk)

                csv_writer.writerow([f"{ending_info['addr']:04x}", ending_string])
