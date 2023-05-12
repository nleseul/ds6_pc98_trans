import configparser
import ips_util
import os

if __name__ == '__main__':
    # Setup
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    event_disk_patch = ips_util.Patch()
    program_disk_patch = ips_util.Patch()
    scenario_disk_patch = ips_util.Patch()


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