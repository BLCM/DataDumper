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

import os
import math
import random
import bl2sdk

class DataDumper(bl2sdk.BL2MOD):

    Name = "Data Dumper"
    Description = "Dumps data from BL2, for use in BLCMM OE resource files"
    Author = 'apocalyptech'

    dd_input_name = 'Run Dumps'
    dd_key = 'B'

    cancel_input_name = 'Cancel Dumps'
    cancel_key = 'P'

    mode_input_name = 'Cycle Mode'
    mode_key = 'O'

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
    magic_commands = {}

    (MODE_FWD,
            MODE_REV,
            MODE_DUMP,
            MODE_DUMP_CHARVEHICLE,
            ) = range(4)

    MODE_ENG = {
            MODE_FWD: ('Maps Forward', None),
            MODE_REV: ('Maps Reverse', None),
            MODE_DUMP: ('Dump Data', None),
            MODE_DUMP_CHARVEHICLE: ('Dump Character/Vehicle Data Only', None),
            }

    level_list = [
            'Stockade_P',
            'Fyrestone_P',
            'DamTop_P',
            'Dam_P',
            'Boss_Cliffs_P',
            'Caverns_P',
            'VOGChamber_P',
            'Interlude_P',
            'TundraTrain_P',
            'Ash_P',
            'BanditSlaughter_P',
            'Fridge_P',
            'HypInterlude_P',
            'IceCanyon_P',
            'FinalBossAscent_P',
            'Outwash_P',
            'Grass_P',
            'Luckys_P',
            'Grass_Lynchwood_P',
            'CreatureSlaughter_P',
            'HyperionCity_P',
            'RobotSlaughter_P',
            'SanctuaryAir_P',
            'Sanctuary_P',
            'Sanctuary_Hole_P',
            'CraterLake_P',
            'Cove_P',
            'SouthernShelf_P',
            'SouthpawFactory_P',
            'ThresherRaid_P',
            'Grass_Cliffs_P',
            'Ice_P',
            'Frost_P',
            'TundraExpress_P',
            'Boss_Volcano_P',
            'PandoraPark_P',
            'Glacial_P',
            'Orchid_Caves_P',
            'Orchid_WormBelly_P',
            'Orchid_Spire_P',
            'Orchid_OasisTown_P',
            'Orchid_ShipGraveyard_P',
            'Orchid_Refinery_P',
            'Orchid_SaltFlats_P',
            'Iris_DL1_TAS_P',
            'Iris_DL1_P',
            'Iris_Moxxi_P',
            'Iris_Hub_P',
            'Iris_DL2_P',
            'Iris_DL3_P',
            'Iris_DL2_Interior_P',
            'Iris_Hub2_P',
            'Sage_PowerStation_P',
            'Sage_Cliffs_P',
            'Sage_HyperionShip_P',
            'Sage_Underground_P',
            'Sage_RockForest_P',
            'Dark_Forest_P',
            'CastleKeep_P',
            'Village_P',
            'CastleExterior_P',
            'Dead_Forest_P',
            'Dungeon_P',
            'Mines_P',
            'TempleSlaughter_P',
            'Docks_P',
            'DungeonRaid_P',
            'Backburner_P',
            'Sandworm_P',
            'OldDust_P',
            'Helios_P',
            'SanctIntro_P',
            'ResearchCenter_P',
            'GaiusSanctuary_P',
            'SandwormLair_P',
            'Hunger_P',
            'Pumpkin_Patch_P',
            'Xmas_P',
            'TestingZone_P',
            'Distillery_P',
            'Easter_P',
            ]

    char_vehicle_packages = [
            'GD_Assassin_Streaming_SF',
            'GD_Mercenary_Streaming_SF',
            'GD_Siren_Streaming_SF',
            'GD_Lilac_Psycho_Streaming_SF',
            'GD_Tulip_Mechro_Streaming_SF',
            'GD_Soldier_Streaming_SF',
            'GD_Runner_Streaming_SF',
            'CD_Runner_Skin_Blood_SF',
            'CD_Runner_Skin_BlueDk_SF',
            'CD_Runner_Skin_BlueLt_SF',
            'CD_Runner_Skin_BlueScrp_SF',
            'CD_Runner_Skin_Blue_SF',
            'CD_Runner_Skin_CamoBlue_SF',
            'CD_Runner_Skin_CamoGrey_SF',
            'CD_Runner_Skin_CamoGrn_SF',
            'CD_Runner_Skin_CamoTan_SF',
            'CD_Runner_Skin_Default_SF',
            'CD_Runner_Skin_DirtGrey_SF',
            'CD_Runner_Skin_DirtGrng_SF',
            'CD_Runner_Skin_DirtSpl_SF',
            'CD_Runner_Skin_DirtStn_SF',
            'CD_Runner_Skin_F_Burst_SF',
            'CD_Runner_Skin_F_Char_SF',
            'CD_Runner_Skin_F_Infern_SF',
            'CD_Runner_Skin_F_Propan_SF',
            'CD_Runner_Skin_Graffiti_SF',
            'CD_Runner_Skin_GreenDk_SF',
            'CD_Runner_Skin_GreenLt_SF',
            'CD_Runner_Skin_GreenScrp_SF',
            'CD_Runner_Skin_Green_SF',
            'CD_Runner_Skin_GreyBlk_SF',
            'CD_Runner_Skin_GreyDark_SF',
            'CD_Runner_Skin_GreyLt_SF',
            'CD_Runner_Skin_GreyWht_SF',
            'CD_Runner_Skin_HexBlue_SF',
            'CD_Runner_Skin_HexGrn_SF',
            'CD_Runner_Skin_HexOrng_SF',
            'CD_Runner_Skin_HexPrpl_SF',
            'CD_Runner_Skin_M_Blue_SF',
            'CD_Runner_Skin_M_Grey_SF',
            'CD_Runner_Skin_M_Purple_SF',
            'CD_Runner_Skin_M_White_SF',
            'CD_Runner_Skin_OrangeDk_SF',
            'CD_Runner_Skin_OrangeLt_SF',
            'CD_Runner_Skin_Orange_SF',
            'CD_Runner_Skin_Paint_SF',
            'CD_Runner_Skin_PinkDark_SF',
            'CD_Runner_Skin_PinkLt_SF',
            'CD_Runner_Skin_Pink_SF',
            'CD_Runner_Skin_PurpleDk_SF',
            'CD_Runner_Skin_PurpleLt_SF',
            'CD_Runner_Skin_Purple_SF',
            'CD_Runner_Skin_RedDark_SF',
            'CD_Runner_Skin_RedLt_SF',
            'CD_Runner_Skin_RedScrp_SF',
            'CD_Runner_Skin_Red_SF',
            'CD_Runner_Skin_RingBlue_SF',
            'CD_Runner_Skin_RingOrng_SF',
            'CD_Runner_Skin_RingPrpl_SF',
            'CD_Runner_Skin_RingRed_SF',
            'CD_Runner_Skin_Rust_SF',
            'CD_Runner_Skin_S_BluBlk_SF',
            'CD_Runner_Skin_S_GrnBlk_SF',
            'CD_Runner_Skin_S_RedBlk_SF',
            'CD_Runner_Skin_S_YelBlk_SF',
            'CD_Runner_Skin_TerqDark_SF',
            'CD_Runner_Skin_TerqLt_SF',
            'CD_Runner_Skin_Terq_SF',
            'CD_Runner_Skin_WoodBrl_SF',
            'CD_Runner_Skin_WoodEpic_SF',
            'CD_Runner_Skin_WoodOak_SF',
            'CD_Runner_Skin_WoodOld_SF',
            'CD_Runner_Skin_YellowDk_SF',
            'CD_Runner_Skin_YellowLt_SF',
            'CD_Runner_Skin_YellowScrp_SF',
            'CD_Runner_Skin_Yellow_SF',
            'GD_BTech_Streaming_SF',
            'CD_BanditTech_Skin_Blood_SF',
            'CD_BanditTech_Skin_BlueBlk_SF',
            'CD_BanditTech_Skin_BlueDk_SF',
            'CD_BanditTech_Skin_BlueLt_SF',
            'CD_BanditTech_Skin_Blue_SF',
            'CD_BanditTech_Skin_CamoBlue_SF',
            'CD_BanditTech_Skin_CamoGrey_SF',
            'CD_BanditTech_Skin_CamoGrn_SF',
            'CD_BanditTech_Skin_CamoTan_SF',
            'CD_BanditTech_Skin_Default_SF',
            'CD_BanditTech_Skin_DirtGrey_SF',
            'CD_BanditTech_Skin_DirtGrng_SF',
            'CD_BanditTech_Skin_DirtSpl_SF',
            'CD_BanditTech_Skin_DirtStn_SF',
            'CD_BanditTech_Skin_F_Burst_SF',
            'CD_BanditTech_Skin_F_Char_SF',
            'CD_BanditTech_Skin_F_Infern_SF',
            'CD_BanditTech_Skin_F_Propan_SF',
            'CD_BanditTech_Skin_Graffiti_SF',
            'CD_BanditTech_Skin_GreenBlk_SF',
            'CD_BanditTech_Skin_GreenDk_SF',
            'CD_BanditTech_Skin_GreenLt_SF',
            'CD_BanditTech_Skin_Green_SF',
            'CD_BanditTech_Skin_GreyBlk_SF',
            'CD_BanditTech_Skin_GreyDark_SF',
            'CD_BanditTech_Skin_GreyLt_SF',
            'CD_BanditTech_Skin_GreyWht_SF',
            'CD_BanditTech_Skin_HexBlue_SF',
            'CD_BanditTech_Skin_HexGrn_SF',
            'CD_BanditTech_Skin_HexOrng_SF',
            'CD_BanditTech_Skin_HexPrpl_SF',
            'CD_BanditTech_Skin_M_Alien_SF',
            'CD_BanditTech_Skin_M_Blue_SF',
            'CD_BanditTech_Skin_M_Grey_SF',
            'CD_BanditTech_Skin_M_White_SF',
            'CD_BanditTech_Skin_OrangeDk_SF',
            'CD_BanditTech_Skin_OrangeLt_SF',
            'CD_BanditTech_Skin_Orange_SF',
            'CD_BanditTech_Skin_Paint_SF',
            'CD_BanditTech_Skin_PinkDark_SF',
            'CD_BanditTech_Skin_PinkLt_SF',
            'CD_BanditTech_Skin_Pink_SF',
            'CD_BanditTech_Skin_PurpleDk_SF',
            'CD_BanditTech_Skin_PurpleLt_SF',
            'CD_BanditTech_Skin_Purple_SF',
            'CD_BanditTech_Skin_RedBlk_SF',
            'CD_BanditTech_Skin_RedDark_SF',
            'CD_BanditTech_Skin_RedLt_SF',
            'CD_BanditTech_Skin_Red_SF',
            'CD_BanditTech_Skin_RingBlue_SF',
            'CD_BanditTech_Skin_RingOrng_SF',
            'CD_BanditTech_Skin_RingPrpl_SF',
            'CD_BanditTech_Skin_RingRed_SF',
            'CD_BanditTech_Skin_Rust_SF',
            'CD_BanditTech_Skin_S_BluBlk_SF',
            'CD_BanditTech_Skin_S_GrnBlk_SF',
            'CD_BanditTech_Skin_S_RedBlk_SF',
            'CD_BanditTech_Skin_S_YelBlk_SF',
            'CD_BanditTech_Skin_TerqDark_SF',
            'CD_BanditTech_Skin_TerqLt_SF',
            'CD_BanditTech_Skin_Terq_SF',
            'CD_BanditTech_Skin_WoodBrl_SF',
            'CD_BanditTech_Skin_WoodEpic_SF',
            'CD_BanditTech_Skin_WoodOak_SF',
            'CD_BanditTech_Skin_WoodOld_SF',
            'CD_BanditTech_Skin_YellowBk_SF',
            'CD_BanditTech_Skin_YellowDk_SF',
            'CD_BanditTech_Skin_YellowLt_SF',
            'CD_BanditTech_Skin_Yellow_SF',
            'GD_Orchid_Hovercraft_SF',
            'GD_Orchid_HarpoonHovercraft_SF',
            'GD_Orchid_RocketHovercraft_SF',
            'GD_Orchid_SawHovercraft_SF',
            'GD_Sage_FanBoat_SF',
            'GD_Sage_CorrosiveFanBoat_SF',
            'GD_Sage_IncendiaryFanBoat_SF',
            'GD_Sage_ShockFanBoat_SF',
            ]

    getall_files = []

    cur_mode = -1
    cur_command_idx = -1
    command_list = []
    waiting_for_command = False
    elapsed_time = 0

    def Enable(self):

        # We need to have a non-class function to call
        def staticDoApocTick(caller: bl2sdk.UObject, function: bl2sdk.UFunction, params: bl2sdk.FStruct) -> bool:
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

        # Get a list of all classes
        self.classes = []
        for obj in bl2sdk.UObject.FindAll('Class'):
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
            bl2sdk.Log('Writing exec file "{}"'.format(getall_file))
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
            bl2sdk.Log('Writing defaults file "{}"...'.format(defaults_filename))
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

        # Initialize our default mode
        self.cycleMode()

        # Set up hooks
        self.RegisterGameInput(self.dd_input_name, self.dd_key)
        self.RegisterGameInput(self.mode_input_name, self.mode_key)
        self.RegisterGameInput(self.cancel_input_name, self.cancel_key)
        bl2sdk.RegisterHook(self.tick_func_name, self.tick_hook_name, staticDoApocTick)

    def Disable(self):

        # Get rid of hooks
        self.UnregisterGameInput(self.dd_input_name)
        self.UnregisterGameInput(self.mode_input_name)
        self.UnregisterGameInput(self.cancel_input_name)
        bl2sdk.RemoveHook(self.tick_func_name, self.tick_hook_name)

    def cycleMode(self):
        """
        Cycle through our available modes.
        """
        self.cur_mode = (self.cur_mode + 1) % len(self.MODE_ENG)
        self.cur_command_idx = -1
        self.command_list = []

        if self.cur_mode == self.MODE_FWD:
            # Loop through levels, then do chars/vehicles, then main menu, then quit!
            for level in self.level_list:
                self.add_open_level(level)
                self.add_getall()
            self.add_chars_vehicles()
            self.add_getall()
            self.add_main_menu()
            self.add_getall()
            self.add_exit()

        elif self.cur_mode == self.MODE_REV:
            # Lead off with a couple of random map loads, to further mix things up
            self.add_user_feedback('Loading random map 1/2...')
            self.add_open_level(random.choice(self.level_list), do_switch_to=False)
            self.add_user_feedback('Loading random map 2/2...')
            self.add_open_level(random.choice(self.level_list), do_switch_to=False)

            # Then it's more or less just the same as FWD, but with some reversed
            # loading orders
            for level in reversed(self.level_list):
                self.add_open_level(level)
                self.add_getall()
            self.add_chars_vehicles(reverse=True)
            self.add_getall()
            self.add_main_menu()
            self.add_getall()
            self.add_exit()

        elif self.cur_mode == self.MODE_DUMP:

            # May as well grab defaults first
            self.add_dumps('defaults')

            # Loop through levels, then do chars/vehicles, then main menu, then quit!
            for level in self.level_list:
                self.add_open_level(level)
                self.add_dumps(level)
            self.add_chars_vehicles()
            self.add_dumps('charvehicle')
            self.add_main_menu()
            self.add_dumps('mainmenu')
            self.add_exit()

        elif self.cur_mode == self.MODE_DUMP_CHARVEHICLE:

            # Special mode to *just* do characters/vehicles.  On my
            # first runthrough of MODE_DUMP, only the first charvehicle
            # `exec` returned data - beyond that it was all "No objects found."
            # Possibly I'd just gotten unlucky with GC, or it could potentially
            # be systemic.  Regardless, it works just fine if it's the *only*
            # thing you do, so here it is.
            self.add_chars_vehicles()
            self.add_dumps('charvehicle')
            self.add_exit()

        else:
            # This actually shouldn't get hit anymore
            self.say('ERROR: How did you get here?  Unknown mode...')
            self.add_switch_to(self.MODE_ENG[self.cur_mode][1])
            self.add_getall()

        # Report to the user
        self.say('Switched to mode: {} - hit "{}" to start, or "{}" to change modes.'.format(
            self.MODE_ENG[self.cur_mode][0],
            self.dd_key,
            self.mode_key,
            ))

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
        if do_switch_to:
            self.add_switch_to(levelname)
        self.command_list.append(('open {}'.format(levelname), self.map_change_delay))

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
            self.command_list.append((self.pkg_load_magic, reversed(self.char_vehicle_packages)))
        else:
            self.command_list.append((self.pkg_load_magic, self.char_vehicle_packages))
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

    def load_packages(self, packages):
        """
        Load the specified packages, then wait for the given delay
        """
        for pkg in packages:
            bl2sdk.LoadPackage(pkg)
        self.setNextDelay(self.pkgload_delay)

    def escape_to_main_menu(self, junk):
        """
        Escape out to the main menu
        """
        pc = bl2sdk.GetEngine().GamePlayers[0].Actor
        pc.ReturnToTitleScreen(False, False)
        self.setNextDelay(self.mainmenu_delay)

    def exit(self, junk):
        """
        Exits the game
        """
        self.consoleCommand('exit')

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
        self.waiting_for_command = False
        self.cur_command_idx = -1
        self.elapsed_time = 0
        self.say('Cancelled runthrough, use "{}" to start again or "{}" to change modes'.format(
            self.dd_key,
            self.mode_key,
            ))

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
            pc = bl2sdk.GetEngine().GamePlayers[0].Actor
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
        elif input_obj.Name == self.cancel_input_name:
            self.cancelCycle()

bl2sdk.Mods.append(DataDumper())
