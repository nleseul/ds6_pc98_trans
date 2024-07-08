import configparser
import os
from ds6_gfx_util import *

if __name__ == '__main__':
    configfile = configparser.ConfigParser(interpolation=configparser.ExtendedInterpolation())
    configfile.read("ds6_patch.conf")
    config = configfile['DEFAULT']

    os.makedirs("gfx/Program", exist_ok=True)

    with open(config['OriginalProgramDisk'], 'rb') as program_disk:
        program_disk.seek(0x2ea10)
        _, _, function_bar_planes = decode_bitplanes(program_disk, 0xc000)
        function_bar_image = load_image_from_bitplanes(function_bar_planes)
        function_bar_image.save("gfx/Program/function_bar.png")
