#!/usr/bin/env python
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
import math
import random
import unrealsdk
from . import dumperdata
from Mods.ModMenu import RegisterMod, SDKMod, ModTypes, EnabledSaveType
from Mods.ModMenu.ModObjects import Game
from Mods.ModMenu.KeybindManager import Keybind

class DataDumper(SDKMod):

    Name = "Data Dumper"
    Description = "Dumps data, for use in BLCMM OE resource files"
    Author = 'apocalyptech'
    Types = ModTypes.Utility
    SaveEnabledState = EnabledSaveType.NotSaved

    dd_input_name = 'Run Dumps'
    dd_key = 'B'

    cancel_input_name = 'Cancel Dumps'
    cancel_key = 'O'

    mode_input_name = 'Cycle Mode'
    mode_key = 'N'

    mode_rev_input_name = 'Cycle Mode Backwards'
    mode_rev_key = 'P'

    Keybinds = [
            Keybind(dd_input_name, dd_key),
            Keybind(mode_input_name, mode_key),
            Keybind(mode_rev_input_name, mode_rev_key),
            Keybind(cancel_input_name, cancel_key),
            ]

    tick_func_name = 'WillowGame.WillowGameViewportClient.Tick'
    tick_hook_name = 'TickHook'

    map_change_delay = 15
    getall_delay = 9
    dump_delay = 1.3
    info_text_delay = 0.5
    switch_to_delay = 0.1
    pkgload_delay = 5
    mainmenu_delay = 6

    exec_file_dir = 'datadumper'

    max_getall_per_run = 500
    max_objdump_per_run = 2500

    # These get set up in Enable; `self` isn't yet valid in this
    # context, since there's no object yet.
    pkg_load_magic = '<pkgload>'
    mainmenu_magic = '<mainmenu>'
    exit_magic = '<exit>'
    map_magic = '<map>'
    magic_commands = {}

    # TODO: this should really be an Enum
    (MODE_FWD,
            MODE_FWD_WITHOUT_CHAR,
            MODE_REV,
            MODE_REV_WITHOUT_CHAR,
            MODE_AXTON_SKIFF1,
            MODE_AXTON_SKIFF2,
            MODE_MAYA_FAN1,
            MODE_MAYA_FAN2,
            MODE_GAIGE_BTECH,
            MODE_GAIGE_RUNNER,
            MODE_ZERO,
            MODE_KRIEG,
            MODE_DUMP,
            MODE_DUMP_WITHOUT_CHAR,
            MODE_DUMP_AXTON_SKIFF1,
            MODE_DUMP_AXTON_SKIFF2,
            MODE_DUMP_MAYA_FAN1,
            MODE_DUMP_MAYA_FAN2,
            MODE_DUMP_GAIGE_BTECH,
            MODE_DUMP_GAIGE_RUNNER,
            MODE_DUMP_ZERO,
            MODE_DUMP_KRIEG,
            MODE_RANDOM_MAPS,
            MODE_MAKEUP,
            # Extra TPS modes
            MODE_CLAPTRAP_BUGGY,
            MODE_WILHELM_STINGRAY_FLAK,
            MODE_JACK_STINGRAY_CRYO,
            MODE_ATHENA,
            MODE_AURELIA,
            MODE_DUMP_CLAPTRAP_BUGGY,
            MODE_DUMP_WILHELM_STINGRAY_FLAK,
            MODE_DUMP_JACK_STINGRAY_CRYO,
            MODE_DUMP_ATHENA,
            MODE_DUMP_AURELIA,
            # Extra AoDK modes
            MODE_AXTON,
            MODE_MAYA,
            MODE_GAIGE,
            MODE_DUMP_AXTON,
            MODE_DUMP_MAYA,
            MODE_DUMP_GAIGE,
            ) = range(40)

    MODELIST = []
    MODES = {
            Game.BL2: [
                #MODE_FWD,
                MODE_FWD_WITHOUT_CHAR,
                #MODE_REV,
                MODE_REV_WITHOUT_CHAR,
                MODE_AXTON_SKIFF1,
                MODE_AXTON_SKIFF2,
                MODE_MAYA_FAN1,
                MODE_MAYA_FAN2,
                MODE_GAIGE_BTECH,
                MODE_GAIGE_RUNNER,
                MODE_ZERO,
                MODE_KRIEG,
                #MODE_DUMP,
                MODE_DUMP_WITHOUT_CHAR,
                MODE_DUMP_AXTON_SKIFF1,
                MODE_DUMP_AXTON_SKIFF2,
                MODE_DUMP_MAYA_FAN1,
                MODE_DUMP_MAYA_FAN2,
                MODE_DUMP_GAIGE_BTECH,
                MODE_DUMP_GAIGE_RUNNER,
                MODE_DUMP_ZERO,
                MODE_DUMP_KRIEG,
                MODE_MAKEUP,
                MODE_RANDOM_MAPS,
                ],
            Game.AoDK: [
                #MODE_FWD,
                MODE_FWD_WITHOUT_CHAR,
                #MODE_REV,
                MODE_REV_WITHOUT_CHAR,
                MODE_AXTON,
                MODE_MAYA,
                MODE_GAIGE,
                MODE_ZERO,
                MODE_KRIEG,
                #MODE_DUMP,
                MODE_DUMP_WITHOUT_CHAR,
                MODE_DUMP_AXTON,
                MODE_DUMP_MAYA,
                MODE_DUMP_GAIGE,
                MODE_DUMP_ZERO,
                MODE_DUMP_KRIEG,
                MODE_MAKEUP,
                MODE_RANDOM_MAPS,
                ],
            Game.TPS: [
                #MODE_FWD,
                MODE_FWD_WITHOUT_CHAR,
                #MODE_REV,
                MODE_REV_WITHOUT_CHAR,
                MODE_CLAPTRAP_BUGGY,
                MODE_WILHELM_STINGRAY_FLAK,
                MODE_JACK_STINGRAY_CRYO,
                MODE_ATHENA,
                MODE_AURELIA,
                #MODE_DUMP,
                MODE_DUMP_WITHOUT_CHAR,
                MODE_DUMP_CLAPTRAP_BUGGY,
                MODE_DUMP_WILHELM_STINGRAY_FLAK,
                MODE_DUMP_JACK_STINGRAY_CRYO,
                MODE_DUMP_ATHENA,
                MODE_DUMP_AURELIA,
                MODE_MAKEUP,
                MODE_RANDOM_MAPS,
                ],
            }

    (TYPE_GETALL,
            TYPE_DUMP) = range(2)

    MODE_ENG = {
            MODE_FWD: ('Maps Getall Forward (w/ char+vehicle)', None, TYPE_GETALL),
            MODE_FWD_WITHOUT_CHAR: ('Maps Getall Forward', None, TYPE_GETALL),
            MODE_REV: ('Maps Getall Reverse (w/ char+vehicle)', None, TYPE_GETALL),
            MODE_REV_WITHOUT_CHAR: ('Maps Getall Reverse', None, TYPE_GETALL),
            MODE_AXTON_SKIFF1: ('Axton + Rocket/Harpoon Skiff Getall', 'axton1', TYPE_GETALL),
            MODE_AXTON_SKIFF2: ('Axton + Sawblade Skiff Getall', 'axton2', TYPE_GETALL),
            MODE_MAYA_FAN1: ('Maya + Corrosive/Flame Fan Getall', 'maya1', TYPE_GETALL),
            MODE_MAYA_FAN2: ('Maya + Shock Fan Getall', 'maya2', TYPE_GETALL),
            MODE_GAIGE_BTECH: ('Gaige + BTech Getall', 'gaige1', TYPE_GETALL),
            MODE_GAIGE_RUNNER: ('Gaige + Runner Getall', 'gaige2', TYPE_GETALL),
            MODE_ZERO: ('Zer0 Getall', 'zero', TYPE_GETALL),
            MODE_KRIEG: ('Krieg Getall', 'krieg', TYPE_GETALL),
            MODE_DUMP: ('Maps Dump (w/ char+vehicle)', None, TYPE_DUMP),
            MODE_DUMP_WITHOUT_CHAR: ('Maps Dump', None, TYPE_DUMP),
            MODE_DUMP_AXTON_SKIFF1: ('Axton + Rocket/Harpoon Skiff Dump', 'axton1', TYPE_DUMP),
            MODE_DUMP_AXTON_SKIFF2: ('Axton + Sawblade Skiff Dump', 'axton2', TYPE_DUMP),
            MODE_DUMP_MAYA_FAN1: ('Maya + Corrosive/Flame Fan Dump', 'maya1', TYPE_DUMP),
            MODE_DUMP_MAYA_FAN2: ('Maya + Shock Fan Dump', 'maya2', TYPE_DUMP),
            MODE_DUMP_GAIGE_BTECH: ('Gaige + BTech Dump', 'gaige1', TYPE_DUMP),
            MODE_DUMP_GAIGE_RUNNER: ('Gaige + Runner Dump', 'gaige2', TYPE_DUMP),
            MODE_DUMP_ZERO: ('Zer0 Dump', 'zero', TYPE_DUMP),
            MODE_DUMP_KRIEG: ('Krieg Dump', 'krieg', TYPE_DUMP),
            MODE_MAKEUP: ('Makeup Dumps', None, TYPE_DUMP),
            MODE_RANDOM_MAPS: ('Random Maps', None, None),
            # Additional TPS modes
            MODE_CLAPTRAP_BUGGY: ('Claptrap + Buggy Getall', 'claptrap', TYPE_GETALL),
            MODE_WILHELM_STINGRAY_FLAK: ('Wilhelm + Flak Stingray Getall', 'wilhelm', TYPE_GETALL),
            MODE_JACK_STINGRAY_CRYO: ('Jack + Cryo Stingray Getall', 'jack', TYPE_GETALL),
            MODE_ATHENA: ('Athena Getall', 'athena', TYPE_GETALL),
            MODE_AURELIA: ('Aurelia Getall', 'aurelia', TYPE_GETALL),
            MODE_DUMP_CLAPTRAP_BUGGY: ('Claptrap + Buggy Dump', 'claptrap', TYPE_DUMP),
            MODE_DUMP_WILHELM_STINGRAY_FLAK: ('Wilhelm + Flak Stingray Dump', 'wilhelm', TYPE_DUMP),
            MODE_DUMP_JACK_STINGRAY_CRYO: ('Jack + Cryo Stingray Dump', 'jack', TYPE_DUMP),
            MODE_DUMP_ATHENA: ('Athena Dump', 'athena', TYPE_DUMP),
            MODE_DUMP_AURELIA: ('Aurelia Dump', 'aurelia', TYPE_DUMP),
            # Additional AoDK modes
            MODE_AXTON: ('Axton Getall', 'axton', TYPE_GETALL),
            MODE_MAYA: ('Maya Getall', 'maya', TYPE_GETALL),
            MODE_GAIGE: ('Gaige Getall', 'gaige', TYPE_GETALL),
            MODE_DUMP_AXTON: ('Axton Dump', 'axton', TYPE_DUMP),
            MODE_DUMP_MAYA: ('Maya Dump', 'maya', TYPE_DUMP),
            MODE_DUMP_GAIGE: ('Gaige Dump', 'gaige', TYPE_DUMP),
            }

    getall_files = []

    cur_mode_idx = -1
    cur_mode = -1
    cur_command_idx = -1
    command_list = []
    waiting_for_command = False
    elapsed_time = 0
    running = False

    def Enable(self):

        # We need to have a non-class function to call
        def staticDoApocTick(caller: unrealsdk.UObject, function: unrealsdk.UFunction, params: unrealsdk.FStruct) -> bool:
            """
            Processes a UE tick, and activates our next modeStep if we need to
            """
            if self.waiting_for_command:
                self.elapsed_time += params.DeltaTime
                if self.elapsed_time >= self.waiting_for_command:
                    self.waiting_for_command = False
                    self.elapsed_time = 0
                    self.modeStep()
            return True

        # Find out what game we're running in.  This is technically a bit fragile, since
        # theoretically the game(s) could get updated at some point with new engine
        # versions, though that seems unlikely.
        self.game = Game.GetCurrent()
        self.MODELIST = self.MODES[self.game]

        # Get a list of all classes
        self.classes = []
        for obj in unrealsdk.UObject.FindAll('Class', True):
            if obj.Name != 'Field' and obj.Name != 'Object':
                self.classes.append(obj.Name)
        self.classes.sort()

        # Find our 'Binaries' dir.
        path_parts = os.getcwd().split(os.sep)
        binaries_idx = [p.lower() for p in path_parts].index('binaries')
        binaries_path = os.sep.join(path_parts[:binaries_idx+1])

        # Create the dir where we'll store `exec` files
        full_exec_file_dir = os.path.join(binaries_path, self.exec_file_dir)
        if not os.path.isdir(full_exec_file_dir):
            os.mkdir(full_exec_file_dir)

        # Set up our "getall" structures.  There are *far* more elegant ways
        # to do this than I'm doing.  We've gone back to using files and
        # `exec` because pysdk seems to freak out after three maps if we
        # try and run all the getall stuff via the API.
        iterations = math.ceil(len(self.classes) / self.max_getall_per_run)
        for i in range(iterations):
            getall_file = 'getall.{}'.format(i)
            unrealsdk.Log('Writing exec file "{}"'.format(getall_file))
            self.getall_files.append('{}/{}'.format(self.exec_file_dir, getall_file))
            with open(os.path.join(full_exec_file_dir, getall_file), 'w') as df:
                for class_idx in range(
                        self.max_getall_per_run*i,
                        min(
                            len(self.classes),
                            self.max_getall_per_run*i+self.max_getall_per_run
                            )
                        ):
                    print('getall {} name'.format(self.classes[class_idx]), file=df)

        # Write out 'defaults' obj dumps
        iterations = math.ceil(len(self.classes) / self.max_objdump_per_run)
        for i in range(iterations):
            defaults_filename = 'defaults.{:03d}'.format(i)
            unrealsdk.Log('Writing defaults file "{}"...'.format(defaults_filename))
            with open(os.path.join(full_exec_file_dir, defaults_filename), 'w') as df:
                for classname in self.classes[self.max_objdump_per_run*i:min(len(self.classes), self.max_objdump_per_run*i+self.max_objdump_per_run)]:
                    if classname != 'Class':
                        print('obj dump Default__{}'.format(classname), file=df)

        # Find objdump files to execute
        self.objdump_files = {}
        for filename in sorted(os.listdir(full_exec_file_dir)):
            try:
                (levelname, num) = filename.split('.', 1)
                if levelname not in self.objdump_files:
                    self.objdump_files[levelname] = []
                self.objdump_files[levelname].append('{}/{}'.format(self.exec_file_dir, filename))
            except ValueError:
                pass

        # Set up "magic" commands
        self.magic_commands[self.pkg_load_magic] = self.load_packages
        self.magic_commands[self.mainmenu_magic] = self.escape_to_main_menu
        self.magic_commands[self.exit_magic] = self.exit
        self.magic_commands[self.map_magic] = self.open_map

        # Initialize our default mode
        self.cycleMode()

        # Set up hooks
        unrealsdk.RegisterHook(self.tick_func_name, self.tick_hook_name, staticDoApocTick)

    def Disable(self):

        # Get rid of hooks
        unrealsdk.RemoveHook(self.tick_func_name, self.tick_hook_name)

    def cycleMode(self, backwards=False):
        """
        Cycle through our available modes.
        """

        if not self.running:

            if backwards:
                self.cur_mode_idx = (self.cur_mode_idx - 1) % len(self.MODELIST)
            else:
                self.cur_mode_idx = (self.cur_mode_idx + 1) % len(self.MODELIST)
            self.cur_mode = self.MODELIST[self.cur_mode_idx]
            self.cur_command_idx = -1
            self.command_list = []

            if self.cur_mode == self.MODE_FWD or self.cur_mode == self.MODE_FWD_WITHOUT_CHAR:

                do_char_vehicle = (self.cur_mode == self.MODE_FWD)

                # Don't bother changing levels if we're starting out on the starting level
                # already
                cur_level = self.get_current_level_name()

                # Loop through levels, then do chars/vehicles, then main menu, then quit!
                for idx, level in enumerate(dumperdata.level_list[self.game]):
                    if idx == 0 and level == cur_level:
                        # Make sure to add in our level-change indicator, though
                        self.add_switch_to(level)
                    else:
                        self.add_open_level(level)
                    self.add_getall()
                if do_char_vehicle:
                    self.add_chars_vehicles()
                    self.add_getall()
                self.add_main_menu()
                self.add_getall()
                if do_char_vehicle:
                    self.add_exit()
                else:
                    self.add_user_feedback('Done!  Hit "{}/{}" to cycle modes.'.format(
                        self.mode_key,
                        self.mode_rev_key,
                        ))

            elif self.cur_mode == self.MODE_REV or self.cur_mode == self.MODE_REV_WITHOUT_CHAR:

                do_char_vehicle = (self.cur_mode == self.MODE_REV)

                # Originally was randomizing some level loads, but ended up thinking better
                # of it. Don't bother.  :)
                #num_randoms = 2
                #randoms = random.sample(dumperdata.level_list[self.game][1:-1], num_randoms)
                #for idx, level_name in enumerate(randoms):
                #    self.add_user_feedback(f'Loading random map {idx+1}/{num_randoms}...')
                #    self.add_open_level(level_name, do_switch_to=False)

                # Don't bother changing levels if we're starting out on the starting level
                # already
                cur_level = self.get_current_level_name()

                # Then it's more or less just the same as FWD, but with some reversed
                # loading orders
                for idx, level in enumerate(reversed(dumperdata.level_list[self.game])):
                    if idx == 0 and level == cur_level:
                        # Make sure to add in our level-change indicator, though
                        self.add_switch_to(level)
                    else:
                        self.add_open_level(level)
                    self.add_getall()
                if do_char_vehicle:
                    self.add_chars_vehicles(reverse=True)
                    self.add_getall()
                self.add_main_menu()
                self.add_getall()
                if do_char_vehicle:
                    self.add_exit()
                else:
                    self.add_user_feedback('Done!  Hit "{}/{}" to cycle modes.'.format(
                        self.mode_key,
                        self.mode_rev_key,
                        ))

            elif self.cur_mode == self.MODE_DUMP or self.cur_mode == self.MODE_DUMP_WITHOUT_CHAR or self.cur_mode == self.MODE_MAKEUP:

                do_char_vehicle = (self.cur_mode == self.MODE_DUMP)

                # May as well grab defaults first
                if self.cur_mode != self.MODE_MAKEUP:
                    self.add_dumps('defaults')

                # Don't bother changing levels if we're starting out on the starting level
                # already
                cur_level = self.get_current_level_name()

                # Loop through levels, then do chars/vehicles, then main menu, then quit!
                idx = 0
                for level in dumperdata.level_list[self.game]:
                    if level in self.objdump_files:
                        if idx == 0 and level == cur_level:
                            # Make sure to add in our level-change indicator, though
                            self.add_switch_to(level)
                        else:
                            self.add_open_level(level)
                        self.add_dumps(level)
                        idx += 1
                if do_char_vehicle:
                    self.add_chars_vehicles()
                    self.add_dumps('charvehicle')
                self.add_main_menu()
                if 'mainmenu' in self.objdump_files:
                    self.add_dumps('mainmenu')
                if do_char_vehicle:
                    self.add_exit()
                else:
                    self.add_user_feedback('Done!  Hit "{}/{}" to cycle modes.'.format(
                        self.mode_key,
                        self.mode_rev_key,
                        ))

            elif self.cur_mode == self.MODE_RANDOM_MAPS:

                # Go to a few random maps, just to mix things up and increment
                # some dynamically-named object suffixes.
                map_count = 3
                cur_level = self.get_current_level_name()
                level_set = set(dumperdata.level_list[self.game])
                level_set.discard(cur_level)
                # I think Python3.11 requires that the collection be a sequence, so passing
                # in a set here wouldn't work, hence converting it back to a list
                rando_maps = random.sample(list(level_set), map_count)
                for idx, rando_map in enumerate(rando_maps):
                    self.add_user_feedback('Loading random map {}/{}...'.format(idx+1, map_count))
                    self.add_open_level(rando_map, do_switch_to=False)

            else:

                # This is either a char-specific getall, or char-specific dump
                (eng_name, section, mode_type) = self.MODE_ENG[self.cur_mode]
                self.add_switch_to(section)
                if self.MODE_ENG[self.cur_mode][2] == self.TYPE_GETALL:
                    self.add_getall()
                else:
                    self.add_dumps(section)

            # Report to the user
            self.say('Switched to mode {}: {} - hit "{}" to start, or "{}/{}" to change modes.'.format(
                self.cur_mode_idx + 1,
                self.MODE_ENG[self.cur_mode][0],
                self.dd_key,
                self.mode_key,
                self.mode_rev_key,
                ))

            # Debug output
            if False:
                unrealsdk.Log('{} command(s) to execute:'.format(len(self.command_list)))
                for idx, (command, delay) in enumerate(self.command_list):
                    unrealsdk.Log(f'{idx+1}. {command} @ {delay}')

    def add_switch_to(self, label):
        """
        Adds a dummy little `obj dump` statement which will be useful for parsing
        Launch.log once this is all done
        """
        self.command_list.append(('obj dump switch.to.{}'.format(label), self.switch_to_delay))

    def add_open_level(self, levelname, do_switch_to=True):
        """
        Adds a command to load a new level
        """

        # Now switch to the new map (adding in our "switch.to.levelname" logfile notifier
        # if requested)
        if do_switch_to:
            self.add_switch_to(levelname)
        self.command_list.append(('open {}'.format(levelname), self.map_change_delay))

        # Instead of using `open`, there's a fancier way of level loading which we could
        # use.  In practice, this leaves more objects un-dumped than using `open`, though,
        # so we're not doing it.
        #if levelname in dumperdata.level_pkgs[self.game]:
        #    self.command_list.append((self.map_magic, levelname))
        #else:
        #    self.command_list.append(('open {}'.format(levelname), self.map_change_delay))

    def add_getall(self):
        """
        Adds our full list of `getall` statements to our command list
        """
        for (idx, filename) in enumerate(self.getall_files):
            self.add_user_feedback('Executing getall step {}/{} ("{}" to cancel)'.format(
                idx+1,
                len(self.getall_files),
                self.cancel_key,
                ))
            self.command_list.append(('exec {}'.format(filename), self.getall_delay))

    def add_dumps(self, level):
        """
        Adds actions to run dumps for the given level
        """
        if level in self.objdump_files:
            for (idx, filename) in enumerate(self.objdump_files[level]):
                self.add_user_feedback('Executing {} obj dumps step {}/{} ("{}" to cancel)'.format(
                    level,
                    idx+1,
                    len(self.objdump_files[level]),
                    self.cancel_key,
                    ))
                self.command_list.append(('exec {}'.format(filename), self.dump_delay))

    def add_chars_vehicles(self, reverse=False):
        """
        Adds actions which will load vehicle and char data for us
        """
        self.add_user_feedback('Loading char and vehicle packages ("{}" to cancel)'.format(self.cancel_key))
        if reverse:
            self.command_list.append((self.pkg_load_magic, reversed(dumperdata.char_vehicle_packages[self.game])))
        else:
            self.command_list.append((self.pkg_load_magic, dumperdata.char_vehicle_packages[self.game]))
        self.add_switch_to('charvehicle')

    def add_main_menu(self):
        """
        Adds an action to return to the main menu
        """
        self.add_user_feedback('Returning to main menu ("{}" to cancel)'.format(self.cancel_key))
        self.command_list.append((self.mainmenu_magic, None))
        self.add_switch_to('mainmenu')

    def add_exit(self):
        """
        Adds an `exit` step to our command list.  This, uh, should be the last in the
        series.
        """
        self.add_user_feedback('Exiting!')
        self.command_list.append((self.exit_magic, None))

    def add_user_feedback(self, text):
        """
        Adds a note to the user into our command list, as a `say` command
        with a short delay.
        """
        self.command_list.append(('say {}'.format(text), self.info_text_delay))

    def runMode(self):
        """
        Runs our currently-defined mode
        """
        if not self.running:
            self.running = True
            self.say('Running current mode ({}) - hit "{}" to cancel'.format(
                self.MODE_ENG[self.cur_mode][0],
                self.cancel_key,
                ))
            self.cur_command_idx = -1
            self.modeStep()

    def modeStep(self):
        """
        Executes a single step of our current mode
        """
        self.cur_command_idx += 1
        if self.cur_command_idx < len(self.command_list):
            (command, delay) = self.command_list[self.cur_command_idx]
            if command in self.magic_commands:
                # `delay` is actually the arguments in this case.
                self.magic_commands[command](delay)
            else:
                self.consoleCommand(command)
                self.setNextDelay(delay)
        else:
            self.say('Finished running {}'.format(self.MODE_ENG[self.cur_mode][0]))
            self.running = False

    def load_packages(self, packages):
        """
        Load the specified packages, then wait for the given delay
        """
        for pkg in packages:
            unrealsdk.LoadPackage(pkg)
        self.setNextDelay(self.pkgload_delay)

    def escape_to_main_menu(self, junk):
        """
        Escape out to the main menu
        """
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor
        pc.ReturnToTitleScreen(False, False)
        self.setNextDelay(self.mainmenu_delay)

    def exit(self, junk):
        """
        Exits the game
        """
        self.consoleCommand('exit')

    def open_map(self, levelname):
        """
        Loads the specified map name.  Right now this uses some hardcoded
        lists in dumperdata.py, but really we should be grabbing this info
        dynamically from `LevelDependencyList` objects.  We're not actually
        using this method anywhere at the moment, though, so I'm not
        bothering to make that change.
        """
        pc = unrealsdk.GetEngine().GamePlayers[0].Actor
        maplist = dumperdata.level_pkgs[self.game][levelname]
        maplist_len = len(maplist)
        for idx, pkgname in enumerate(maplist):
            unrealsdk.Log('Preparing map change for {}: {}, {}'.format(
                pkgname,
                idx == 0,
                idx == (maplist_len - 1),
                ))
            pc.ClientPrepareMapChange(pkgname, idx == 0, idx == (maplist_len - 1))
        pc.ClientCommitMapChange()
        self.setNextDelay(self.map_change_delay)

    def setNextDelay(self, delay):
        """
        Sets our next mode iteration to fire after `delay` seconds
        """
        self.elapsed_time = 0
        self.waiting_for_command = delay

    def cancelCycle(self):
        """
        Cancel our runthrough
        """
        if self.running:
            self.waiting_for_command = False
            self.cur_command_idx = -1
            self.elapsed_time = 0
            self.say('Cancelled runthrough, use "{}" to start again or "{}/{}" to change modes'.format(
                self.dd_key,
                self.mode_key,
                self.mode_rev_key,
                ))
            self.running = False

    def say(self, text):
        """
        Executes a `say` command
        """
        self.consoleCommand('say {}'.format(text))

    def consoleCommand(self, command):
        """
        Runs a console command
        """
        try:
            # The `True` in the call to ConsoleCommand is absurdly important for
            # our purposes!  Without it, Unreal doesn't free up any memory
            # allocated during the run of the command, which for our `getall`
            # statements is a lot.  We can't get through more than about 18
            # maps before the engine runs out of virtual memory and crashes,
            # without specifying `True` here.  Presumably an unintended side
            # effect, but something to keep in mind.
            pc = unrealsdk.GetEngine().GamePlayers[0].Actor
            pc.ConsoleCommand(command, True)
        except:
            pass

    def GameInputPressed(self, input_obj):
        """
        Invoked by the SDK when one of the inputs we've registered is pressed
        """
        if input_obj.Name == self.dd_input_name:
            self.runMode()
        elif input_obj.Name == self.mode_input_name:
            self.cycleMode()
        elif input_obj.Name == self.mode_rev_input_name:
            self.cycleMode(backwards=True)
        elif input_obj.Name == self.cancel_input_name:
            self.cancelCycle()

    def get_current_level_name(self):
        """
        Returns our current level name, if possible, or None.  (If it's None,
        it's almost certainly the main menu.)
        """
        wi = unrealsdk.GetEngine().GetCurrentWorldInfo()
        cpl = wi.CommittedPersistentLevel
        if cpl:
            return cpl.PathName(cpl).split('.')[0]
        else:
            # Probably the main menu
            return None

RegisterMod(DataDumper())
