#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

# Copyright 2023 Christopher J. Kucera
# <cj@apocalyptech.com>
# <https://apocalyptech.com/contact.php>
#
# This program is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# Borderlands DataDumper is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import re
import sys
import lzma

filename_dumps = 'Launch.log-data_dumps'
output_dirs = {
        'BL2': '/games/Steam/steamapps/common/Borderlands 2/Binaries/datadumper',
        'AoDK': '/games/Steam/steamapps/common/Pawpaw/Binaries/datadumper',
        'TPS': '/games/Steam/steamapps/common/BorderlandsPreSequel/Binaries/datadumper',
        }
game = None
if os.path.exists(filename_dumps):
    open_func = open
elif os.path.exists(f'{filename_dumps}.xz'):
    open_func = lzma.open
    filename_dumps = f'{filename_dumps}.xz'
else:
    raise RuntimeError('Could not find dump file!')
with open_func(filename_dumps, 'rt', encoding='latin1') as df:
    line_num = 0
    for line in df:
        if line.startswith('Log: Base directory: '):
            if 'Borderlands 2' in line:
                game = 'BL2'
                break
            elif 'BorderlandsPreSequel' in line:
                game = 'TPS'
                break
            elif 'TTAoDKOneShotAdventure' in line or 'Pawpaw' in line:
                game = 'AoDK'
                break
            else:
                raise RuntimeError(f'Unknown Base Directory line: {line}')

        # Don't process the whole file
        line_num += 1
        if line_num > 10:
            raise RuntimeError('Could not find engine version number!')

# Make sure we got a result
if game is None:
    raise RuntimeError('Gametype not detected!')
output_dir = output_dirs[game]

# Get a mapping of objects that we tried to dump
command_filename_re = re.compile(r'^(?P<section>\w+)\.(?P<sequence>\d+)$')
command_re = re.compile(r'^obj dump (?P<obj_name>.*)\s*$')
ignore_sections = {
        'getall',
        'defaults',
        }
attempted = {}
for filename in os.listdir(output_dir):
    if match := command_filename_re.match(filename):
        section = match.group('section')
        sequence = match.group('sequence')
        if section in ignore_sections:
            continue
        with open(os.path.join(output_dir, filename), encoding='latin1') as df:
            for line in df:
                if match2 := command_re.match(line):
                    obj_name = match2.group('obj_name')
                    attempted[obj_name] = (section, sequence)
                else:
                    raise RuntimeError(f'Unknown line in {filename}: {line.strip()}')
    else:
        if not os.path.isdir(os.path.join(output_dir, filename)):
            raise RuntimeError(f'Unknown command file found: {filename}')

# Create a new dir
makeup_dir = os.path.join(output_dir, 'makeup')
os.makedirs(makeup_dir, exist_ok=True)

# Loop through our dump file to see which ones we didn't get
makeup_map = {}
missing = {}
not_found_re = re.compile(r'.*No objects found using command \'obj dump (?P<obj_name>.*)\'\s*$')
dump_start_re = re.compile('.*\*\*\* Property dump for object \'(?P<obj_class>\S+) (?P<obj_name>\S+)\' \*\*\*\s*')
with open_func(filename_dumps, 'rt', encoding='latin1') as df:
    for line in df:
        if match := not_found_re.match(line):
            obj_name = match.group('obj_name')
            if obj_name == 'Default__Default__Class':
                continue
            if obj_name.startswith('switch.to.'):
                continue
            if obj_name.startswith('Loader.TheWorld:'):
                continue
            if obj_name.startswith('Transient.'):
                continue
            if obj_name not in missing:
                missing[obj_name] = attempted[obj_name]

        elif match := dump_start_re.match(line):
            # Checking this because if we *do* process makeups, we'll likely be
            # appending them to the file.  So we'd get a Not Found above, and
            # then later on see a proper dump.  This way we can avoid reporting
            # false positives (at the cost of 2 regexes per line, which ain't
            # quick).
            obj_name = match.group('obj_name')
            if obj_name in missing:
                del missing[obj_name]

# Report and write out makeups
filehandles = {}
for obj_name, (section, sequence) in missing.items():
    #print(f'{obj_name}: {section}, {sequence}')
    if section not in filehandles:
        new_file = os.path.join(makeup_dir, f'{section}.1')
        filehandles[section] = open(new_file, 'wt', encoding='latin1')
    print(f'obj dump {obj_name}', file=filehandles[section])
for fh in filehandles.values():
    fh.close()
print('')
print(f'Makeup control files written to {makeup_dir}: {len(filehandles)}')
print('')

# Report on "special" dumps that might need to be made up
section_to_eng = {
        # BL2
        'axton1': 'Axton + Rocket/Harpoon Skiff',
        'axton2': 'Axton + Sawblade Skiff',
        'maya1': 'Maya + Corrosive/Flame Fan',
        'maya2': 'Maya + Shock Fan',
        'gaige1': 'Gaige + BTech',
        'gaige2': 'Gaige + Runner',
        'zero': 'Zer0',
        'krieg': 'Krieg',
        # TPS
        'claptrap': 'Claptrap + Buggy',
        'wilhelm': 'Wilhelm + Flak Stingray',
        'jack': 'Jack + Cryo Stingray',
        'athena': 'Athena',
        'aurelia': 'Aurelia',
        # Additional AoDK
        'axton': 'Axton',
        'maya': 'Maya',
        'gaige': 'Gaige',
        }
seen_report = False
for section in sorted(filehandles.keys()):
    if section in section_to_eng:
        if not seen_report:
            print('You will also need to run manual dump steps for:')
            print('')
            seen_report = True
        print(' - {}'.format(section_to_eng[section]))
if seen_report:
    print('')
