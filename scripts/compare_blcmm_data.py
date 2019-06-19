#!/usr/bin/env python
# vim: set expandtab tabstop=4 shiftwidth=4:

# Copyright 2019 Christopher J. Kucera
# <cj@apocalyptech.com>
# <http://apocalyptech.com/contact.php>
#
# This program is free software: you can redistribute it
# and/or modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 3 of
# the License, or (at your option) any later version.
#
# Borderlands ModCabinet Sorter is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import io
import os
import zipfile

output_dir = 'comparisons'
data_dir = 'categorized'
stock_files_dir = '/home/pez/.local/share/BLCMM/data/BL2/bak'

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
                                blcmm_objects.add(obj_name.lower())
                                lower_to_upper[obj_name.lower()] = obj_name

                        # Get our own list of objects for the given class
                        with open(os.path.join(data_dir, '{}.dict'.format(class_name))) as df:
                            for line in df:
                                obj_name = line.strip().split(' ', 1)[1]
                                our_objects.add(obj_name.lower())
                                lower_to_upper[obj_name.lower()] = obj_name

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

