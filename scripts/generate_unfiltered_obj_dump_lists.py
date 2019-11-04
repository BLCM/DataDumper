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

import re
import os
import math
import gzip
import lzma
import tempfile

filename_fwd = 'Launch.log-all_object_names_fwd'
filename_fwd_compressed = '{}.xz'.format(filename_fwd)
if os.path.exists(filename_fwd_compressed):
    filename_fwd = filename_fwd_compressed
    is_compressed = True
else:
    is_compressed = False
output_dirs = {
        'BL2': '/usr/local/games/Steam/SteamApps/common/Borderlands 2/Binaries/datadumper',
        'TPS': '/usr/local/games/Steam/SteamApps/common/BorderlandsPreSequel/Binaries/datadumper',
        }
if is_compressed:
    df = lzma.open(filename_fwd, 'rt')
else:
    df = open(filename_fwd)
line_num = 0
for line in df:
    if line.startswith('Log: Version: '):
        version = int(line.strip()[len('Log: Version: '):])
        if version == 8638:
            game = 'BL2'
        elif version == 8630:
            game = 'TPS'
        else:
            raise Exception('Unknown engine version found in logfile: {}'.format(version))
        break
    line_num += 1
    if line_num > 5:
        raise Exception('Could not find engine version number!')
df.close()
output_dir = output_dirs[game]
print('Found {}, writing to {}'.format(game, output_dir))

# 800 feels absurdly low to me, but 1k was too much for the objects that
# happened to get dumped in Caustic Caverns.  When I was doing some more
# ad-hoc data dumping on the Linux TPS version, I was dumping 10k objects
# at once; c0dy suggested that the inherent output limits are higher in
# TPS in general.  I wonder if there's something about the Linux versions,
# too...  Anyway, it's 800 for now.
max_per_file = 800

obj_re = re.compile('^\[[0-9\.]+\] Log: \d+\) (\w+) (\S+)\.Name = .*$')
switch_re = re.compile('.*switch\.to\.(\w+)\'.*')

type_blacklist = set([
    # AnimSequences generate *huge* dumps.  Huge enough that a single object,
    # say, Anemone_GD_Marcus.Anims.AnimSet_Anemone_Marcus:Idle_Panic2, will
    # crash the engine while trying to dump it.  c0dy's EndlessLoopProtectionDisabler.dll
    # could potentially save us from that , but that doesn't work with
    # PythonSDK yet, and there's no pysdk equivalent.
    'AnimSequence',

    # Ditto for these.  Probably there are no "base" GfxRawData objects,
    # just stuff that inherits from them, but just in case...
    'SwfMovie',
    'GFxRawData',

    # ... and for these:
    'GBXNavMesh',
    'Terrain',
    ])

def write_obj_dump_files(level, obj_set, output_dir, max_per_file):
    """
    Writes out the given `objects` for `level` into `output_dir`
    """
    objects = sorted(obj_set)
    iterations = math.ceil(len(objects) / max_per_file)
    for i in range(iterations):
        filename = '{}.{:03d}'.format(level, i)
        print('   - Writing {}'.format(filename))
        with open(os.path.join(output_dir, filename), 'w', encoding='latin1') as df:
            for obj_name in objects[max_per_file*i:min(len(objects), max_per_file*i+max_per_file)]:
                print('obj dump {}'.format(obj_name), file=df)

# Generate dump lists
print('Generating dump lists...')
seen_objects = set()
cur_level = None
cur_set = None
if is_compressed:
    df = lzma.open(filename_fwd, 'rt', encoding='latin1')
else:
    df = open(filename_fwd, encoding='latin1')
for line in df:
    match = obj_re.match(line)
    if match:
        if not cur_level:
            raise Exception('found object name but no level')
        obj_type = match.group(1)
        obj_name = match.group(2)
        obj_name_lower = obj_name.lower()
        if obj_type not in type_blacklist and obj_name_lower not in seen_objects:
            cur_set.add(obj_name)
            seen_objects.add(obj_name_lower)
    else:
        match = switch_re.match(line)
        if match:
            if cur_level:
                write_obj_dump_files(cur_level, sorted(cur_set), output_dir, max_per_file)
            print(' * Processing {}...'.format(match.group(1)))
            cur_level = match.group(1)
            cur_set = set()
if cur_level:
    write_obj_dump_files(cur_level, sorted(cur_set), output_dir, max_per_file)
df.close()

print('Done!')
