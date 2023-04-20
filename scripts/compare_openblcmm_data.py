#!/usr/bin/env python
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

import io
import os
import re
import sys
import lzma
import zipfile
import argparse

# This utility *could* make use of the SQLite database inside the OpenBLCMM
# datapacks, but that would require extracting them into a temporary location,
# and since they're pretty big, I don't particularly care to do it. So, we're
# just going to examine the dump contents themselves.

parser = argparse.ArgumentParser(description='Compare OpenBLCMM OE Datapack to our own generated files')
parser.add_argument('-f', '--filename',
        type=str,
        required=True,
        help='The path to the OpenBLCMM datapack to compare against',
        )
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
args = parser.parse_args()
if args.clean:
    args.ignoretransient = True
    args.ignoredefault = True
    args.ignoreloader = True
    args.ignorewillow = True

output_dir = 'comparisons_openblcmm'
data_dir = 'categorized'

dump_start_re = re.compile('^\*\*\* Property dump for object \'(?P<obj_class>\S+) (?P<obj_name>\S+)\' \*\*\*\s*')

if not os.path.isdir(output_dir):
    os.mkdir(output_dir)

# Loop through our own categorized dumps
print('Processing our own dumps...')
our_objects = {}
for filename in sorted(os.listdir(data_dir)):
    full_filename = os.path.join(data_dir, filename)
    print(f" - {full_filename:80}\r", end='')
    if filename.endswith('.dump'):
        df = open(full_filename, 'rt', encoding='latin1')
        class_name = filename[:-5]
    elif filename.endswith('.dump.xz'):
        df = lzma.open(full_filename, 'rt', encoding='latin1')
        class_name = filename[:-8]
    else:
        print(f' - WARNING: Ignoring unknown file in categorized dir: {filename:80}')
        continue
    our_objects[class_name] = set()
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
            our_objects[class_name].add(obj_name)
    df.close()
print(' - {:80}'.format("Done!"))
print('')

# Now loop through the OpenBLCMM data.  These *should* be well-ordered
# due to how they're packed by the generation script, so we should be
# processing all of a single class at once.
openblcmm_file_re = re.compile(r'^data/.*?/dumps/(?P<class_name>\S+)\.dump\.\d+$')
openblcmm_objects = {}
print(f'Processing {args.filename}...')
with zipfile.ZipFile(args.filename, 'r') as zf:
    for inner_file in zf.infolist():
        if match := openblcmm_file_re.match(inner_file.filename):
            class_name = match.group('class_name')
            if class_name not in openblcmm_objects:
                openblcmm_objects[class_name] = set()
                print(f" - {class_name:80}\r", end='')
            with zf.open(inner_file) as df:
                wrapped = io.TextIOWrapper(df, encoding='latin1')
                for line in wrapped:
                    if match2 := dump_start_re.match(line):
                        obj_name = match2.group('obj_name')
                        obj_name_lower = obj_name.lower()
                        if args.ignoretransient and obj_name_lower.startswith('transient.'):
                            continue
                        if args.ignoredefault and '.default__' in obj_name_lower:
                            continue
                        if args.ignoreloader and obj_name_lower.startswith('loader.theworld:'):
                            continue
                        if args.ignorewillow and obj_name_lower.rsplit('.', 1)[-1].startswith('willow'):
                            continue
                        openblcmm_objects[class_name].add(obj_name)
print(' - {:80}'.format("Done!"))
print('')

# First check to see if we have mismatched classes
our_classes = set(our_objects.keys())
openblcmm_classes = set(openblcmm_objects.keys())
only_our = our_classes - openblcmm_classes
only_openblcmm = openblcmm_classes - our_classes
if len(only_our) > 0 or len(only_openblcmm) > 0:
    with open(os.path.join(output_dir, 'class_mismatches.txt'), 'w') as odf:
        if len(only_our) > 0:
            print('Classes which only exist in our own dumps:', file=odf)
            print('', file=odf)
            for class_name in sorted(only_our):
                print(f' - {class_name}', file=odf)
            print('', file=odf)
        if len(only_openblcmm) > 0:
            print('Classes which only exist in OpenBLCMM dumps:', file=odf)
            print('', file=odf)
            for class_name in sorted(only_openblcmm):
                print(f' - {class_name}', file=odf)
            print('', file=odf)

# Now loop through to see what objects might differ
found_mismatches = False
with open(os.path.join(output_dir, 'object_mismatches.txt'), 'w') as odf:
    for class_name, our_comp in sorted(our_objects.items()):
        if class_name in openblcmm_objects:
            their_comp = openblcmm_objects[class_name]

            only_in_openblcmm = their_comp - our_comp
            only_in_ours = our_comp - their_comp
            if len(only_in_openblcmm) > 0 or len(only_in_ours) > 0:
                found_mismatches = True

                print('Class: {}'.format(class_name), file=odf)
                if len(only_in_openblcmm) > 0:
                    print('', file=odf)
                    print(' * Only in OpenBLCMM data:', file=odf)
                    for cn_loop in sorted(only_in_openblcmm):
                        print('   - {}'.format(cn_loop), file=odf)
                if len(only_in_ours) > 0:
                    print('', file=odf)
                    print(' * Only in our own data:', file=odf)
                    for cn_loop in sorted(only_in_ours):
                        print('   + {}'.format(cn_loop), file=odf)
                print('', file=odf)

    if not found_mismatches:
        print('No discrepancies found!', file=odf)


# Report
print('')
print(f'See the "{output_dir}" dir for the results of the comparison')
print('')

