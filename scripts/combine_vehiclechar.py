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

cv_filename = 'Launch.log-data_dumps_charvehicle'
main_filename = 'Launch.log-data_dumps_minus_charvehicle'
out_filename = 'Launch.log-data_dumps'

wait_for_next_switch_to = False
with open(out_filename, 'w', encoding='latin1') as odf:
    with open(main_filename, encoding='latin1') as df:
        for line in df:
            if 'switch.to' in line:
                if 'charvehicle' in line:
                    wait_for_next_switch_to = True
                    with open(cv_filename, encoding='latin1') as cv_df:
                        for cv_line in cv_df:
                            odf.write(cv_line)
                else:
                    wait_for_next_switch_to = False
                    odf.write(line)
            elif not wait_for_next_switch_to:
                odf.write(line)
