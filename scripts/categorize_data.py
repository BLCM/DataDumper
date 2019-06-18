#!/usr/bin/env python3
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

import os
import re

dump_file = 'Launch.log-data_dumps'
output_dir = 'categorized'

filehandles = {}
seen_objects = set()

dump_start_re = re.compile('^\*\*\* Property dump for object \'(\S+) (\S+)\' \*\*\*\s*')

print('NOTE: This utility will open up about 3,500 files simultaneously while writing')
print('data.  If your OS imposes a limit on open filehandles, it may error out')
print('before finishing.  If running this on Linux, you may need to add a line to')
print('/etc/security.limits.conf with content such as:')
print('')
print('    <username>     soft    nofile  4096')
print('')
print('And then log in with a totally-fresh shell, to bypass the more-usual open-file')
print('limit of 1024.')
print('')
print('Windows users might be SOL, actually - I\'ve been reading that Windows may have')
print('a default limit of 512, which can only be expanded to 2048.  I may have to')
print('do this differently once I confirm that.  If someone on a Windows system')
print('ever gives this a run, please contact me to let me know how it runs - ')
print('http://apocalyptech.com/contact.php')
print('')

print('Processing...')
if not os.path.isdir(output_dir):
    os.mkdir(output_dir)
with open(dump_file, 'r', encoding='latin1') as df:

    cur_fh = None
    cur_type = None
    cur_name = None
    last_line = None

    for line in df:

        line_without_log = line[15:]

        match = dump_start_re.match(line_without_log)
        if match:
            if cur_name:
                if last_line and last_line.strip() != '':
                    print('', file=cur_fh)
            cur_type = match.group(1)
            cur_name = match.group(2)
            if cur_name in seen_objects:
                cur_type = None
                cur_name = None
                cur_fh = None
            else:
                seen_objects.add(cur_name)
                if cur_type not in filehandles:
                    filehandles[cur_type] = open(os.path.join(output_dir, '{}.dump'.format(cur_type)), 'w', encoding='latin1')
                cur_fh = filehandles[cur_type]

        if 'Log file open' in line or 'ExecWarning' in line or 'Closing by request' in line:
            if cur_fh and last_line and last_line.strip() != '':
                print('', file=cur_fh)
            cur_type = None
            cur_name = None
            cur_fh = None

        if cur_fh:
            cur_fh.write(line_without_log)
            last_line = line_without_log

# Clean up
for fh in filehandles.values():
    fh.close()

print('Done!')
