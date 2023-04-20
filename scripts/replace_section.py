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
import argparse

parser = argparse.ArgumentParser(
        description='Replace a section from Launch.log files with the contents of another file',
        epilog="""
            NOTE: The section seen *first* is the one that will be replaced.
            Also, the input file is read blind -- there is no checking to
            see if the contents happen to be for the same-named section, for
            instance.

            This util assumes CRLF line endings on the Launch.log file,
            which is true for Windows (or Windows-via-Proton on Linux).
            Other platforms may have to tweak the code in here to
            process properly.
            """,
        )
parser.add_argument('-f', '--filename',
        type=str,
        required=True,
        help='The filename from which to replace a section',
        )
parser.add_argument('-i', '--input',
        type=str,
        required=True,
        help='The input filename to read the new section from',
        )
parser.add_argument('-o', '--output',
        type=str,
        required=True,
        help='The output filename to write the new version of the file to',
        )
parser.add_argument('-s', '--section',
        type=str,
        required=True,
        help='The section to be replaced',
        )
args = parser.parse_args()

switch_to_re = re.compile(r'obj dump switch\.to\.(?P<category>.*?)\'')

writing = True
seen_section = False
removed = 0
written = 0
with open(args.filename, 'rt', encoding='latin1', newline="\r\n") as df:
    with open(args.output, 'wb') as odf:
        for line in df:
            if match := switch_to_re.search(line):
                if match.group('category') == args.section:
                    if not seen_section:
                        seen_section = True
                        writing = False
                        with open(args.input, 'rt', encoding='latin1', newline="\r\n") as idf:
                            for new_line in idf:
                                written += 1
                                odf.write(new_line.encode('latin1'))
                    else:
                        writing = True
                else:
                    writing = True
            if writing:
                odf.write(line.encode('latin1'))
            else:
                removed += 1

print(f'Done, removed {removed} lines but added {written} more')

