#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import re
import os
import math
import gzip
import tempfile

filename_fwd = 'Launch.log-all_object_names_fwd'
filename_rev = 'Launch.log-all_object_names_rev'
output_dir = '/usr/local/games/Steam/SteamApps/common/Borderlands 2/Binaries/objdump'

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

class MapFileDumps(object):
    """
    An object used to reorganize a monolithic `Launch.log`-style
    list of objects into a group of files, organized by map.  This
    is useful to save on RAM while comparing files, since the
    two files we're comparing will be in completely different
    orders.

    We use gzip for compressing the files we right - I'd rather use
    lzma but the embedded Python used by PythonSDK right now doesn't
    seem to include that module, and I'd prefer to keep everything
    compatible, even if PythonSDK wouldn't be reading these particular
    files.
    """

    def __init__(self, filename, switch_re, obj_re):
        self.filename = filename
        self.dirname = tempfile.mkdtemp()
        self.files = set()

        cur_level = None
        with open(self.filename, encoding='latin1') as df:
            for line in df:
                match = obj_re.match(line)
                if match:
                    if not cur_level:
                        raise Exception('found object name but no level')
                    print(match.group(2), file=cur_level)
                else:
                    match = switch_re.match(line)
                    if match:
                        if cur_level:
                            cur_level.close()
                        print(' * Extracting data for {}...'.format(match.group(1)))
                        cur_level = gzip.open(os.path.join(self.dirname, '{}.gz'.format(match.group(1))), 'wt', encoding='latin1')
                        self.files.add(match.group(1))
        if cur_level:
            cur_level.close()

    def get_object_set(self, level):
        """
        Returns a set of object names from the given level
        """
        with gzip.open(os.path.join(self.dirname, '{}.gz'.format(level)), 'rt', encoding='latin1') as df:
            return set([l.strip() for l in df])

    def clean(self):
        """
        Deletes all our temp files, and our temp directory.  Don't use
        the object after doing this.
        """
        for filename in self.files:
            os.unlink(os.path.join(self.dirname, '{}.gz'.format(filename)))
        os.rmdir(self.dirname)

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

# Dump out our "reverse" file in a way that's more useful to us
print('Loading reverse file getall lists...')
rev_objs = MapFileDumps(filename_rev, switch_re, obj_re)

# Now run comparisons.  Some duplicated code from our class, above, but eh.
print('Comparing dumps between runs...')
seen_objects = set()
cur_level = None
cur_set = None
cur_rev_set = None
with open(filename_fwd, encoding='latin1') as df:
    for line in df:
        match = obj_re.match(line)
        if match:
            if not cur_level:
                raise Exception('found object name but no level')
            obj_type = match.group(1)
            obj_name = match.group(2)
            if obj_type not in type_blacklist and obj_name in cur_rev_set and obj_name not in seen_objects:
                cur_set.add(obj_name)
                seen_objects.add(obj_name)
        else:
            match = switch_re.match(line)
            if match:
                if cur_level:
                    write_obj_dump_files(cur_level, sorted(cur_set), output_dir, max_per_file)
                print(' * Comparing {}...'.format(match.group(1)))
                cur_level = match.group(1)
                cur_set = set()
                cur_rev_set = rev_objs.get_object_set(cur_level)
if cur_level:
    write_obj_dump_files(cur_level, sorted(cur_set), output_dir, max_per_file)

# Clean up
rev_objs.clean()

print('Done!')
