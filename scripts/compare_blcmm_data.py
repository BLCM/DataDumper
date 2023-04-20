#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

# Copyright 2019-2023 Christopher J. Kucera
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

import io
import os
import re
import sys
import lzma
import zipfile
import argparse

parser = argparse.ArgumentParser(description='Compare BLCMM OE Datafiles to our own generated files')
parser.add_argument('-i', '--ignoretransient',
        action='store_true',
        help='Ignore Transient.* objects',
        )
parser.add_argument('-d', '--ignoredefault',
        action='store_true',
        help='Ignore Default__* objects',
        )
parser.add_argument('-l', '--ignoreloader',
        action='store_true',
        help='Ignore Loader.Theworld:* objects',
        )
parser.add_argument('-w', '--ignorewillow',
        action='store_true',
        help='Ignore *.Willow* objects',
        )
parser.add_argument('-c', '--clean',
        action='store_true',
        help='"Cleanest" comparison (implies all available --ignore options)',
        )
parser.add_argument('-g', '--game-name',
        type=str,
        required=True,
        choices=['bl2', 'tps'],
        help="The game we'll compare against",
        )
args = parser.parse_args()
if args.clean:
    args.ignoretransient = True
    args.ignoredefault = True
    args.ignoreloader = True
    args.ignorewillow = True

output_dir = 'comparisons_blcmm'
data_dir = 'categorized'
game = args.game_name.upper()
stock_files_dir = f'/home/pez/.local/share/BLCMM/data/{game}'

dump_start_re = re.compile('^\*\*\* Property dump for object \'(?P<obj_class>\S+) (?P<obj_name>\S+)\' \*\*\*\s*')

if not os.path.isdir(output_dir):
    os.mkdir(output_dir)

for filename in os.listdir(stock_files_dir):
    if filename.endswith('.jar'):
        print('Processing {}...'.format(filename))
        package_name = filename.split('.', 1)[0]
        with open(os.path.join(output_dir, '{}.txt'.format(package_name)), 'w') as odf:

            print('Data comparisons for package: {}'.format(package_name), file=odf)
            print('', file=odf)

            with zipfile.ZipFile(os.path.join(stock_files_dir, filename), 'r') as zf:
                for inner_file in zf.infolist():
                    if inner_file.filename.endswith('.dict'):
                        blcmm_objects = set()
                        our_objects = set()
                        lower_to_upper = {}
                        class_name = inner_file.filename.split('/')[-1].split('.', 1)[0]
                        print(' * {}'.format(class_name))

                        # Get a list of all objects for the given class, from BLCMM's files
                        with zf.open(inner_file) as df:
                            wrapped = io.TextIOWrapper(df)
                            for line in wrapped:
                                obj_name = line.strip().split(' ', 1)[1]
                                obj_name_lower = obj_name.lower()
                                if args.ignoretransient and obj_name_lower.startswith('transient.'):
                                    continue
                                if args.ignoredefault and '.default__' in obj_name_lower:
                                    continue
                                if args.ignoreloader and obj_name_lower.startswith('loader.theworld:'):
                                    continue
                                if args.ignorewillow and obj_name_lower.rsplit('.', 1)[-1].startswith('willow'):
                                    continue
                                blcmm_objects.add(obj_name_lower)
                                lower_to_upper[obj_name_lower] = obj_name

                        # Get our own list of objects for the given class.
                        # This would be quicker if we waited until we've generated BLCMM data of
                        # our own, or if we waited for FT Explorer indexing too.  But whatever,
                        # this way it works so long as we've got categorized data in place.
                        our_base = os.path.join(data_dir, f'{class_name}.dump')
                        if not os.path.exists(our_base):
                            our_base = f'{our_base}.xz'
                        if not os.path.exists(our_base):
                            raise RuntimeError(f'Could not find our own dumps for class "{class_name}"')
                        if our_base.endswith('.dump'):
                            df = open(our_base, 'rt', encoding='latin1')
                        else:
                            df = lzma.open(our_base, 'rt', encoding='latin1')
                        for line in df:
                            if match := dump_start_re.match(line):
                                obj_name = match.group('obj_name')
                                obj_name_lower = obj_name.lower()
                                if args.ignoretransient and obj_name_lower.startswith('transient.'):
                                    continue
                                if args.ignoredefault and '.default__' in obj_name_lower:
                                    continue
                                if args.ignoreloader and obj_name_lower.startswith('loader.theworld:'):
                                    continue
                                if args.ignorewillow and obj_name_lower.rsplit('.', 1)[-1].startswith('willow'):
                                    continue
                                our_objects.add(obj_name_lower)
                                lower_to_upper[obj_name_lower] = obj_name
                        df.close()

                        # Report!
                        only_in_blcmm = blcmm_objects - our_objects
                        only_in_ours = our_objects - blcmm_objects
                        if len(only_in_blcmm) > 0 or len(only_in_ours) > 0:
                            print('Class: {}'.format(class_name), file=odf)
                            if len(only_in_blcmm) > 0:
                                print('', file=odf)
                                print(' * Only in BLCMM data:', file=odf)
                                for cn_loop in sorted(only_in_blcmm):
                                    print('   - {}'.format(lower_to_upper[cn_loop]), file=odf)
                            if len(only_in_ours) > 0:
                                print('', file=odf)
                                print(' * Only in our own data:', file=odf)
                                for cn_loop in sorted(only_in_ours):
                                    print('   + {}'.format(lower_to_upper[cn_loop]), file=odf)
                            print('', file=odf)

# Report
print('')
print(f'See the "{output_dir}" dir for the results of the comparison')
print('')

