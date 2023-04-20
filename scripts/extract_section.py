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
        description='Extract a section from Launch.log files',
        epilog="""
            NOTE: The section seen *first* is the one that will be extracted.
            This util assumes CRLF line endings on the Launch.log file,
            which is true for Windows (or Windows-via-Proton on Linux).
            Other platforms may have to tweak the code in here to
            process properly.
            """,
        )
parser.add_argument('-f', '--filename',
        type=str,
        required=True,
        help='The filename from which to extract the section',
        )
parser.add_argument('-o', '--output',
        type=str,
        required=True,
        help='The output filename to write to',
        )
parser.add_argument('-s', '--section',
        type=str,
        required=True,
        help='The section whose duplicate needs stripping',
        )
args = parser.parse_args()

switch_to_re = re.compile(r'obj dump switch\.to\.(?P<category>.*?)\'')

writing = False
written = 0
with open(args.filename, 'rt', encoding='latin1', newline="\r\n") as df:
    with open(args.output, 'wb') as odf:
        for line in df:
            if match := switch_to_re.search(line):
                if match.group('category') == args.section:
                    writing = True
                elif writing:
                    break
            if writing:
                odf.write(line.encode('latin1'))
                written += 1

print(f'Done, wrote {written} lines')

