#!/usr/bin/env python3
# vim: set expandtab tabstop=4 shiftwidth=4:

import os
import re
import sys
import lzma
import sqlite3
import argparse

# NOTE: this is still a work-in-progress, and the BLCMM version which
# uses this data hasn't been released yet (and will probably have a
# slightly new name for the fork, when it is released)

# When the BLCMM core was opensourced in 2022, we needed to reimplement the
# Data Library components if we wanted a fully-opensource BLCMM, since those
# parts were reserved.  This is the code to generate the required data
# structures for this new 2023 BLCMM fork!
#
# The original BLCMM data library has a pretty thorough understanding of UE
# objects, including their attributes, and had a complete object model for
# basically everything found in the engine.  That allows for some pretty
# nifty functionality, but at the moment that's way more work than Apocalyptech's
# willing to spend reimplementing, in 2023.  If I ever do start digging into
# that, I expect that'll get folded up into some generation stuff in here,
# but for now this just generates enough metadata to support knowing about the
# class structure, how it correlates to the objects, and the structure of the
# whole object tree (plus where exactly to find the raw dump data).
#
# The core of the new data library functionality is a Sqlite3 database which
# OE (or any other app) can use to query information about the data.  There's
# a set of tables describing the engine class layout, and another set of tables
# describing the object layout.  "Object" entries are technically just nodes in
# a tree -- there may not be an object dump attached.  But the whole parent/child
# structure lets us put in the dump info where it's applicable.
#
# The app expects to have a `completed` directory that was populated via
# `categorize_data.py`, so this has to be run at the tail end of the data
# extraction process.  You could alternatively just grab the data extracts
# provided with FT Explorer (https://github.com/apocalyptech/ft-explorer).  That's
# basically just the raw `completed` dir.
#
# While processing, in addition to creating the sqlite database, this'll
# copy/store the dumps into a new directory with a different format.  For the
# new BLCMM OE dumps, it'll still be categorized by class type, but there's also
# a maximum individual file size.  That's done so that random access to object
# dumps near the end of the file don't take a noticeable amount of time to load,
# since those dumps will be compressed, and need to be uncompressed to seek to
# the specified position.
#
# That position is found via the `object` table, in the fields `filename_index` and
# `filename_position`.  The index is the numeric suffix of the filename, and
# the main filename comes from the class name.  So for instance there's
# `StaticMeshComponent.dump.0` as the first dump file, `StaticMeshComponent.dump.1`
# as the next, and so on.  Then the `filename_position` attribute is the starting
# byte in the specified uncompressed dump file.
#
# The database itself has several denormalizations done in the name of speed.
# Theoretically, all OE interactions apart from fulltext searching (and refs, at
# the moment, which is effectively just fulltext search) should be nice and snappy,
# and the database structure should let us dynamically populate the Class and Object
# trees as users click around, without having to load *everything* all at once.
# This should let us get rid of the annoying "there are too many objects!" notifications
# (though of course that could've been reimplemented in a less-annoying way, too).
#
# As mentioned elsewhere below, the denormalization does come at a cost: database size.
# At time of writing, the uncompressed "base" database (classes, class aggregation,
# and objects) clocks in at about 350MB.  Adding in the "shown class IDs" table (see
# below for details on that - it's what lets the lower-left-hand Object Explorer
# window be nice and quick) adds in another 230MB or so.
#
# ================================================================
# NOTE: ASSUMPTIONS ABOUT THE DATABASE WHICH BLCMM'S OE RELIES ON:
# ================================================================
#
#   1. The `class.id` numbering starts at 1 for the first valid object (ResultSet
#      objects will end up with `0` for integer values when they're null -- you
#      can explicitly check for null after getting the value, but since sqlite
#      autoincrement PKs are already 1-indexed, we're not bothering).
#
#   2. There is a single root `class` element, which is `id` 1 (and is the first
#      row in the database.  (This happens to be named `Object`, but BLCMM
#      doesn't actually care about that.)
#
#   3. When ordered by `id`, the `class` table rows are in "tree" order -- as in,
#      there will *never* be a `parent` field whose row we haven't already seen.
#
#   4. Datafile filename indexes start at 1, for the same reason as point #1 above.


class UEClass:
    """
    Class to hold info about a single UE Class.
    """

    def __init__(self, name):
        self.name = name
        self.id = None
        self.parent = None
        self.children = []
        self.total_children = 0
        self.aggregate_ids = set()
        self.num_datafiles = 0

    def __lt__(self, other):
        # BLCMM's historically sorted *with* case sensitivity, but nuts to that.  I've long
        # since come to terms with case-insensitive sorting.  :)  Swap these around to
        # order differently.  (Note that this technically only has bearing on the row
        # ordering in the DB, of course -- the Java app's free to sort however it likes.)
        #return self.name < other.name
        return self.name.casefold() < other.name.casefold()

    def set_parent(self, parent):
        """
        Sets our parent, and sets the reciprocal `children` reference on
        the parent obj
        """
        if self.parent is not None:
            raise RuntimeError(f'{self.name} already has parent {self.parent}, tried to add {parent}!')
        self.parent = parent
        self.parent.children.append(self)

    def display(self, level=0):
        """
        Print out the class tree starting at this level
        """
        print('  '*level + ' -> ' + self.name)
        for child in sorted(self.children):
            child.display(level+1)

    def populate_db(self, conn, curs):
        """
        Recursively populate ourselves in the database.  Intended to be called
        initially from the top-level `Object` class.
        """
        if self.parent is None:
            curs.execute('insert into class (name, num_children) values (?, ?)',
                    (self.name, len(self.children)))
        else:
            curs.execute('insert into class (name, num_children, parent) values (?, ?, ?)',
                    (self.name, len(self.children), self.parent.id))
        self.id = curs.lastrowid
        for child in sorted(self.children):
            child.populate_db(conn, curs)
            curs.execute('insert into class_children (parent, child) values (?, ?)',
                    (self.id, child.id))

    def inc_children(self):
        """
        Keeping track of how many objects in total are of this class
        type (including objects belonging to a descendant of this class).
        Used to denormalize that info in the DB, to provide some info to
        the user when clicking through the tree.  With our current schema,
        this is probably gonna be ignored entirely 'cause our performance
        for building the trees shouldn't care.  Still, no good reason
        *not* to keep it in here, since we've already implemented it.
        """

        self.total_children += 1
        if self.parent is not None:
            self.parent.inc_children()

    def fix_total_children_and_datafiles(self, conn, curs):
        """
        Store our `total_children` value in the database.  When building the DB
        we process the Classes first, then Objects, but we don't have this
        information until we're through with the Object processing, so we've
        gotta come back after the fact and update the record.

        This also updates `num_datafiles` as well, since that's something else
        we don't know until we've processed objects
        """
        curs.execute('update class set total_children=?, num_datafiles=? where id=?',
                (self.total_children, self.num_datafiles, self.id))

    def set_aggregate_ids(self, ids=None):
        """
        Sets our "aggregate" IDs.  This basically lets us easily know the
        full inheritance path for a given class.  For instance, an
        `ItemPoolDefinition` object is also a `GBXDefinition` object, and
        an instance of the top-level `Object`.  We need to know about that
        because we technically want to show all ItemPoolDefinition objects
        when the user's clicked on GBXDfinition, so having the info
        denormalized is pretty helpful.
        """
        if ids is None:
            ids = {self.id}
        else:
            ids = set(ids)
            ids.add(self.id)
        self.aggregate_ids |= ids
        for child in self.children:
            child.set_aggregate_ids(self.aggregate_ids)

    def store_aggregate_ids(self, conn, curs):
        """
        And here's where we store those aggregate IDs in the database, once we've
        walked the whole tree and generated it.  Note that there's not really much
        call to store this in the DB -- we use the information in this script to
        generate the huge and actually-useful `object_show_class_ids` class, but
        probably nothing in OE will actually query this table.  Still, compared to
        the size of the rest of the DB, this is pretty small potatoes, so we may
        as well store it anyway.
        """
        for idnum in sorted(self.aggregate_ids):
            curs.execute('insert into class_aggregate (id, aggregate) values (?, ?)',
                    (self.id, idnum))


class ClassRegistry:
    """
    Class to hold info about all the UE Classes we know about.
    Basically just a glorified dict.
    """

    def __init__(self):
        self.classes = {}

    def __getitem__(self, key):
        """
        Act like a dict
        """
        return self.classes[key]

    def get_or_add(self, name):
        """
        This is here to support dynamically building out the tree from arbitrary
        starting locations; this way we can request parent entries and if they
        don't already exist, they'll get created -- if they *do* already exist,
        they'll just get returned, so we can link up parents/children properly.
        """
        if name not in self.classes:
            self.classes[name] = UEClass(name)
        return self.classes[name]

    def populate_db(self, conn, curs):
        """
        Kick off populating the database, once we have the entire tree.  We
        assume that `Object` is the single top-level entry.
        """
        self['Object'].populate_db(conn, curs)
        conn.commit()

    def fix_total_children_and_datafiles(self, conn, curs):
        """
        Once our `total_children` metric has been populated in all the Class
        objects (which happens as we build out the Object Registry), this will
        update the database with all those totals.

        This method now also updates the num_datafiles count as well, since
        that's another thing we can only know after processing objects.
        """
        for class_obj in self.classes.values():
            class_obj.fix_total_children_and_datafiles(conn, curs)
        conn.commit()

    def set_aggregate_ids(self):
        """
        This kicks off calculating the "aggregate" IDs which lets us have a
        shortcut to the whole object inheritance structure.  See the docs
        inside `Class` for a bit more info on that.  We assume that `Object`
        is the single top-level entry.
        """
        self.classes['Object'].set_aggregate_ids()

    def store_aggregate_ids(self, conn, curs):
        """
        Once all our aggregate IDs have been computed, this updates the database
        with the freshly-populated values.
        """
        for class_obj in self.classes.values():
            class_obj.store_aggregate_ids(conn, curs)
        conn.commit()


class UEObject:
    """
    Class to hold info about a single UE Object
    """

    def __init__(self, name, short_name,
            separator=None,
            parent=None,
            class_obj=None,
            file_index=None,
            file_position=None,
            ):
        self.name = name
        self.short_name = short_name
        self.separator = separator
        self.parent = parent
        if self.parent is not None:
            self.parent.children.append(self)
        self.class_obj = class_obj
        self.file_index = file_index
        self.file_position = file_position
        self.bytes = None
        self.id = None
        self.children = []
        self.total_children = 0
        self.show_class_ids = set()
        self.has_class_children = set()

    def __lt__(self, other):
        return self.name.casefold() < other.name.casefold()

    def inc_children(self):
        """
        Recursively keep track of how many child objects exist here.  This
        number's primarily just used so we know whether the entry in the
        tree needs to be expandable or not.
        """
        self.total_children += 1
        if self.parent is not None:
            self.parent.inc_children()

    def populate_db(self, conn, curs):
        """
        Recursively inserts ourself and all children into the database, once
        the whole tree structure's been built in memory.
        """
        fields = [
                'name',
                'short_name',
                'num_children',
                'total_children',
                ]
        values = [
                self.name,
                self.short_name,
                len(self.children),
                self.total_children,
                ]
        if self.class_obj is not None:
            fields.append('class')
            values.append(self.class_obj.id)
        if self.parent is not None:
            fields.append('parent')
            values.append(self.parent.id)
        if self.separator is not None:
            fields.append('separator')
            values.append(self.separator)
        if self.file_index is not None:
            fields.append('file_index')
            values.append(self.file_index)
        if self.file_position is not None:
            fields.append('file_position')
            values.append(self.file_position)
            fields.append('bytes')
            values.append(self.bytes)
        curs.execute('insert into object ({}) values ({})'.format(
            ', '.join(fields),
            ', '.join(['?']*len(fields)),
            ), values)
        self.id = curs.lastrowid
        for child in sorted(self.children):
            child.populate_db(conn, curs)
            curs.execute('insert into object_children (parent, child) values (?, ?)',
                    (self.id, child.id))

    def set_show_class_ids(self, ids=None):
        """
        Calculate what Class IDs result in showing this object.  For instance, if
        the user clicks on the top-level `Object`, we'd be showing basically
        everything.  If they click on `ItemPoolDefinition`, we'd want to mark
        all `CrossDLCItemPoolDefinition` and `KeyedItemPoolDefinition` as shown
        as well, since those classes inherit from `ItemPoolDefinition`.  This is
        basically just a big ol' denormalization which we're using to increase
        performance -- it lets us find valid children based on class with a single
        SELECT statement (with just a single indexed join) which should be pretty
        fast even in the worst-case scenario.

        It does come at the cost of database size, though!  During development on
        the BL2 dataset, this increases the uncompressed database size by over
        200MB.

        The has_class_children field is used to assist with the tree rendering
        in BLCMM -- a simple boolean so that the tree-building routines know
        right away whether a UEObject is a leaf or not, so it can skip adding
        a "dummy" entry where one isn't needed.
        """
        if ids is None:
            if self.class_obj is None:
                return
            ids = self.class_obj.aggregate_ids
        else:
            # The only way to get here is if we're a recursive call to a parent,
            # which means that this object has children for this class.  So,
            # mark that down
            self.has_class_children |= ids
        self.show_class_ids |= ids
        if self.parent is not None:
            self.parent.set_show_class_ids(ids)

    def store_show_class_ids(self, conn, curs):
        """
        Once all our shown class IDs have been populated, insert that into the
        database.  Note that for BL2 data, this results in over seven million
        rows in the table!
        """
        for idnum in sorted(self.show_class_ids):
            if idnum in self.has_class_children:
                has_children = 1
            else:
                has_children = 0
            curs.execute('insert into object_show_class_ids (id, class, has_children) values (?, ?, ?)',
                    (self.id, idnum, has_children))


class ObjectRegistry:
    """
    Class to hold information about *all* of our UE Objects
    """

    def __init__(self):
        self.objects = {}

    def get_or_add(self, name,
            class_obj=None,
            index=None,
            position=None,
            ):
        """
        Much like in ClassRegistry, this method assists us in building out the
        tree from arbitrary starting points, so we can re-use parent objects
        when necessary, to keep the tree structure clean.
        """
        if name in self.objects:
            # Fill in some data that could have been left out by building
            # our parent/child tree while looping
            if class_obj is not None:
                obj = self.objects[name]
                obj.class_obj = class_obj
                obj.file_position = position
                obj.file_index = index
                class_obj.inc_children()
        else:
            # Otherwise, we're adding a new object
            split_idx = max(name.rfind('.'), name.rfind(':'))
            if split_idx == -1:
                self.objects[name] = UEObject(name, name,
                        class_obj=class_obj,
                        file_index=index,
                        file_position=position,
                        )
            else:
                parent = self.get_or_add(name[:split_idx])
                parent.inc_children()
                if class_obj is not None:
                    class_obj.inc_children()
                self.objects[name] = UEObject(name, name[split_idx+1:],
                        separator=name[split_idx],
                        parent=parent,
                        class_obj=class_obj,
                        file_index=index,
                        file_position=position,
                        )

        return self.objects[name]

    def get_top_levels(self):
        """
        Returns all top-level objects
        """
        for obj in self.objects.values():
            if obj.parent is None:
                yield obj

    def populate_db(self, args, conn, curs):
        """
        Populates the database once the tree has been constructed
        """
        for obj in sorted(self.get_top_levels()):
            if args.verbose:
                print(f"\r > {obj.name:60}", end='')
            obj.populate_db(conn, curs)
            conn.commit()
        if args.verbose:
            print("\r   {:50}".format('Done!'))

    def set_show_class_ids(self):
        """
        Kicks off the process of deciding which class IDs trigger showing
        which objects.  See the docs in `UEObject` for some more info on
        all that.
        """
        for obj in self.objects.values():
            obj.set_show_class_ids()

    def store_show_class_ids(self, conn, curs):
        """
        Once we have those shown-class-ID attributes set properly, add them
        into the database.
        """
        for obj in self.objects.values():
            obj.store_show_class_ids(conn, curs)
        conn.commit()


def get_class_registry(categorized_dir):
    """
    Populate a ClassRegistry object using the `Default__*` dumps at the beginning
    of our already-categorized dump files.
    """

    cr = ClassRegistry()
    for filename in sorted(os.listdir(categorized_dir)):
        if not filename.endswith('.dump.xz'):
            continue
        class_obj = cr.get_or_add(filename[:-8])
        with lzma.open(os.path.join(categorized_dir, filename), 'rt', encoding='latin1') as df:
            for line in df:
                if line.startswith('  ObjectArchetype='):
                    parent_name = cr.get_or_add(line.split('=', 1)[1].split("'", 1)[0])
                    class_obj.set_parent(parent_name)
                    break

    return cr


def get_object_registry(args, cr):
    """
    Creates our object registry
    """

    max_bytes = args.max_dump_size*1024*1024

    obj_reg = ObjectRegistry()
    for filename in sorted(os.listdir(args.categorized_dir)):
        if not filename.endswith('.dump.xz'):
            continue
        class_obj = cr[filename[:-8]]
        with lzma.open(os.path.join(args.categorized_dir, filename), 'rt', encoding='latin1') as df:
            pos = 0
            cur_index = 1
            odf = None
            new_obj = None
            for line in df:
                if line.startswith('*** Property dump for object'):
                    if new_obj is not None:
                        new_obj.bytes = pos-new_obj.file_position
                    obj_name = line.split("'")[1].split(' ')[-1]
                    new_obj = obj_reg.get_or_add(obj_name, class_obj, cur_index, pos)
                    if odf is None or pos >= max_bytes:
                        if odf is not None:
                            odf.close()
                            cur_index += 1
                        if args.verbose:
                            print("\r > {:60}".format(
                                f'{class_obj.name}.{cur_index}'), end='')
                        odf = open(os.path.join(args.obj_dir, f'{class_obj.name}.dump.{cur_index}'), 'wt', encoding='latin1')
                        pos = 0
                        class_obj.num_datafiles += 1
                odf.write(line)
                pos = odf.tell()
            if new_obj is not None:
                new_obj.bytes = odf.tell()-new_obj.file_position
            odf.close()
        # Break here to only process the first of the dump files
        #break
    if args.verbose:
        print("\r   {:60}".format('Done!'))
    return obj_reg


def write_schema(conn, curs):
    """
    Given a database object `conn` and cursor `curs`, initialize our schema.

    Show all top-level object entries which should be shown for class ID 1683:
        select o.* from object o, object_show_class_ids i where o.id=i.id and i.class=1683 and parent is null;

    Then drill down to a specific entry:
        select o.* from object o, object_show_class_ids i where o.id=i.id and i.class=1683 and parent=604797;
    """

    # Info about a particular class
    curs.execute("""
        create table class (
            id integer primary key autoincrement,
            name text unique not null,
            parent integer references class (id),
            num_children int not null default 0,
            total_children int not null default 0,
            num_datafiles int not null default 0
        )
        """)
    # Direct class children, for generating the GUI tree
    curs.execute("""
        create table class_children (
            parent integer not null references class (id),
            child integer not null references class (id),
            unique (parent, child)
        )
        """)
    # "Aggregate" class IDs, allowing us to know with a single query what
    # the whole inheritance tree is.  (For instance, the aggregates for
    # the `AIBehaviorProviderDefinition` class will also include the IDs
    # for `BehaviorProviderDefinition`, `GBXDefinition`, and `Object`.
    curs.execute("""
        create table class_aggregate (
            id integer not null references class (id),
            aggregate integer not null references class (id),
            unique (id, aggregate)
        )
        """)
    # Info about a particular object (may not *actually* be an object;
    # this also includes folder-only elements of the tree)
    curs.execute("""
        create table object (
            id integer primary key autoincrement,
            name text unique not null,
            short_name text not null,
            class integer references class (id),
            parent integer references object (id),
            separator character(1),
            file_index int,
            file_position int,
            bytes int,
            num_children int not null default 0,
            total_children int not null default 0
        )
        """)
    curs.execute('create index idx_object_parent on object(parent)')
    # Direct object children, for generating the GUI tree
    curs.execute("""
        create table object_children (
            parent integer not null references object (id),
            child integer not null references object (id),
            unique (parent, child)
        )
        """)
    # The list of Class IDs which this object should show up "under",
    # when selected by Class Explorer
    curs.execute("""
        create table object_show_class_ids (
            id integer not null references object (id),
            class integer not null references class (id),
            has_children tinyint not null default 0,
            unique (id, class)
        )
        """)
    conn.commit()

def main():

    parser = argparse.ArgumentParser(
            description="Populate new-style BLCMM data dumps (for 2023)",
            formatter_class=argparse.ArgumentDefaultsHelpFormatter,
            )

    parser.add_argument('-s', '--sqlite',
            type=str,
            default='data.db',
            help="SQLite database file to write to (wiping if needed, first)",
            )

    parser.add_argument('-c', '--categorized-dir',
            type=str,
            default='categorized',
            help="Directory containing categorized .dump.xz output",
            )

    parser.add_argument('-o', '--obj-dir',
            type=str,
            default='generated_2023_blcmm_data',
            help="Output directory for data dumps",
            )

    parser.add_argument('-m', '--max-dump-size',
            type=int,
            default=15,
            help="Maximum data dump file size",
            )

    parser.add_argument('-v', '--verbose',
            action='store_true',
            help="Verbose output while running.  (Does NOT imply the various --show-* options)",
            )

    parser.add_argument('--show-class-tree',
            action='store_true',
            help="Show the generated class tree after constructing it",
            )

    # Parse args
    args = parser.parse_args()

    # Wipe + recreate our sqlite DB if necessary
    if args.verbose:
        print('Database:')
    if os.path.exists(args.sqlite):
        if args.verbose:
            print(f' - Cleaning old DB: {args.sqlite}')
        os.unlink(args.sqlite)
    if args.verbose:
        print(f' - Creating new DB: {args.sqlite}')
    conn = sqlite3.connect(args.sqlite)
    curs = conn.cursor()
    write_schema(conn, curs)

    # Get class registry
    if args.verbose:
        print('Class Registry:')
        print(' - Generating')
    cr = get_class_registry(args.categorized_dir)
    if args.verbose:
        print(' - Populating in DB')
    cr.populate_db(conn, curs)
    if args.verbose:
        print(' - Setting aggregate IDs')
    cr.set_aggregate_ids()
    if args.verbose:
        print(' - Storing aggregate IDs')
    cr.store_aggregate_ids(conn, curs)
    if args.show_class_tree:
        print('Generated class tree:')
        cr.get_or_add('Object').display()
        print('')

    # Populate objects
    if args.verbose:
        print('Object Registry:')
        print(' - Generating')
    if not os.path.exists(args.obj_dir):
        os.makedirs(args.obj_dir, exist_ok=True)
    obj_reg = get_object_registry(args, cr)
    if args.verbose:
        print(' - Populating in DB')
    obj_reg.populate_db(args, conn, curs)
    if args.verbose:
        print(' - Setting shown class IDs')
    obj_reg.set_show_class_ids()
    if args.verbose:
        print(' - Storing shown class IDs')
    obj_reg.store_show_class_ids(conn, curs)

    # Clean up class total_children counts
    if args.verbose:
        print('Cleaning up Class total_children counts')
    cr.fix_total_children_and_datafiles(conn, curs)

    # Close the DB
    curs.close()
    conn.close()

if __name__ == '__main__':
    main()

