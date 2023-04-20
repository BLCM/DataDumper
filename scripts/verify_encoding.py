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
import sys
import lzma

# This is a stupid little script to sort-of verify our file encodings.
# We expect the dumps to be in ISO-8859-1/latin1 (maybe those two aren't
# actually the exact same thing, but whatever), so the hope is that this
# util ends up complaining about some stuff when we try to interpret
# as utf-8.  So, UTF-8 exceptions are *expected*, and we want to see
# some while looking through.

processed = 0
for filename in sorted(os.listdir('categorized')):
    if filename.endswith('.dump') or filename.endswith('.dump.xz'):
        full_filename = os.path.join('categorized', filename)

        # Initial pass, try latin1 encoding.  I *suspect* that this
        # probably would never fail?  We'd just end up with nonsensical
        # weird chars, if we saw some utf-8 or whatever
        try:
            if filename.endswith('.xz'):
                df = lzma.open(full_filename, 'rt', encoding='latin1')
            else:
                df = open(full_filename, 'rt', encoding='latin1')
            for line in df:
                pass
            df.close()
        except Exception as e:
            print(f'Invalid latin1 in {filename}: {e}')
        finally:
            df.close()

        # Pass 2; try UTF-8?  I think this would fail if there's "special"
        # latin1 chars in there
        try:
            if filename.endswith('.xz'):
                df = lzma.open(full_filename, 'rt', encoding='utf-8')
            else:
                df = open(full_filename, 'rt', encoding='utf-8')
            for line in df:
                pass
            df.close()
        except Exception as e:
            print(f'Invalid UTF-8 {filename}: {e}')
        finally:
            df.close()

        processed += 1

print(f'Processed files: {processed}')

