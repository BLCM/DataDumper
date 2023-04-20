#!/usr/bin/env python3
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

import os
import re
import sys

dump_file = 'Launch.log-data_dumps'
output_dir = 'categorized'

filehandles = {}
seen_objects = set()

dump_start_re = re.compile('^\*\*\* Property dump for object \'(?P<obj_class>\S+) (?P<obj_name>\S+)\' \*\*\*\s*')
shiftid_re = re.compile(r'(?P<prefix>ShiftId\[\d+\]=)\d+(?P<suffix>[,)])')

print('NOTE: This utility will open up about 3,500 files simultaneously while writing')
print('data.  If your OS imposes a limit on open filehandles, it may error out')
print('before finishing.  If running this on Linux, you may need to add a line to')
print('/etc/security/limits.conf with content such as:')
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
print('https://apocalyptech.com/contact.php')
print('')

# Check to see if we have a scrub file
if not os.path.exists('scrub.txt'):
    print("ERROR: Could not find a scrub.txt file!  This is used to sanitize the")
    print("game data as it's processed, to remove things like your Steam username,")
    print("Steam user ID, and hostname.  If you don't want to scrub data, just")
    print("create an empty scrub.txt file, but otherwise fill it in with one bit")
    print("of info-to-scrub per line, and the script will replace data as it goes.")
    print('')
    print("Keep in mind that if your steam username happens to be a string which")
    print("might legitimately pop up inside Borderlands data dumps, this util might")
    print("end up scrubbing more info than you expect!")
    print('')
    sys.exit(1)

# Read in our scrub patterns
print('Scrubbing patterns:')
print('')
scrubs = set()
with open('scrub.txt') as df:
    for line in df:
        scrub = line.strip()
        scrubs.add(scrub)
        print(f' - {scrub}')
print(' - `ShiftId` byte-array representations')
print('')
scrubbed = set()

def scrub_shiftid(match):
    return '{}0{}'.format(
            match.group('prefix'),
            match.group('suffix'),
            )

prefix_len = 15

print('Processing...')
if not os.path.isdir(output_dir):
    os.mkdir(output_dir)
with open(dump_file, 'r', encoding='latin1') as df:

    cur_fh = None
    cur_type = None
    cur_name = None
    last_line = None

    for line in df:

        # If we had a dump that took long enough, we could get into a five-digit
        # second, which throws off our prefix.  This can happen if you leave an
        # automated dump to run overnight and then do manual char/vehicle sections
        # in the morning, or something.
        if prefix_len == 15 and len(line) > 9 and line[9] == ']':
            prefix_len = 16
        line_without_log = line[prefix_len:]

        # Until recently, the hexedit for BL2's array-limit message removal actually
        # leaves in the "more elements" message when there are *exactly* 100 items in
        # thie array.  So with the hexedit active, we'd occasionally need to strip
        # that out.  We've got a better hexedit now, though, so this isn't needed (and
        # we wouldn't've wanted this active in general, anyway -- would only want this
        # once we've manually confirmed that the dumps were experiencing this problem).
        #if False:
        #    if line_without_log.startswith('  ... 1 more elements'):
        #        continue

        match = dump_start_re.match(line_without_log)
        if match:
            if cur_name:
                if last_line and last_line.strip() != '':
                    print('', file=cur_fh)
            cur_type = match.group('obj_class')
            cur_name = match.group('obj_name')
            if cur_name in seen_objects:
                cur_type = None
                cur_name = None
                cur_fh = None
            # Was intentionally omitting these at some point inbetween BL2/TPS dumps and
            # AoDK, for whatever reason, but our current OpenBLCMM data processing scripts
            # rely on the class structure gleaned from these defaults.
            #elif 'Default__' in cur_name and ':' not in cur_name:
            #    cur_type = None
            #    cur_name = None
            #    cur_fh = None
            else:
                seen_objects.add(cur_name)
                if cur_type not in filehandles:
                    filehandles[cur_type] = open(os.path.join(output_dir, '{}.dump'.format(cur_type)), 'w', encoding='latin1', newline="\r\n")
                cur_fh = filehandles[cur_type]

        if 'Log file open' in line or 'ExecWarning' in line or 'Closing by request' in line:
            if cur_fh and last_line and last_line.strip() != '':
                print('', file=cur_fh)
            cur_type = None
            cur_name = None
            cur_fh = None

        if cur_fh:
            scrubbed_line = line_without_log

            # Scrubs from scrub.txt.  At least for the volume of scrubs
            # that we currently have, this is noticeably faster than using
            # regexes, as you'd probably expect.
            for scrub in scrubs:
                scrubbed_line = scrubbed_line.replace(scrub, '<hidden>')

            # A ShiftId attribute exists in a couple of places which breaks
            # the ID apart into sixteen bytes, expressed as an array.  Reset
            # all those to zero
            if 'ShiftId' in scrubbed_line:
                scrubbed_line = shiftid_re.sub(scrub_shiftid, scrubbed_line)

            # Report if anything got scrubbed
            if cur_name not in scrubbed and scrubbed_line != line_without_log:
                print(f"Scrubbed info from {cur_type}'{cur_name}'")
                scrubbed.add(cur_name)

            # ... and now write 'em out.
            cur_fh.write(scrubbed_line)
            last_line = scrubbed_line

# Clean up
for fh in filehandles.values():
    fh.close()

print("Done!")
print('')
print("You may want to manually clear out the Scrollback attribute inside")
print("WillowConsole'Transient.WillowGameEngine_0:WillowGameViewportClient_0.WillowConsole_0'")
print('')

