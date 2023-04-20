Borderlands 2/TPS Data Dumper - Original Method
===============================================

These are some legacy docs for an alternate dumping method which I haven't
actually used in a long time.  This method was still available via the mod
for some time, but during the 2023 data refresh for
[OpenBLCMM](https://github.com/BLCM/OpenBLCMM) development, I ended up
commenting it out because I doubted I'd ever end up using it again, and
the only thing it was doing was making both the mod and the project
documentation more confusing to work with.

The actual code for this method is still present in the DataDumper mod
file, and it would only take uncommenting a couple of actions in the action
lists to re-enable it (specifically uncommenting the `MODE_FWD`, `MODE_REV`,
and `MODE_DUMP` elements inside the main `MODES` structure in `__init__.py`).

For docs about the preferred method for generating public dumps, see
[the main README](README.md).

### A Note About Character Data

This version of the dump process uses a fully automated method of
dumping characters and vehicles, by using PythonSDK's ability to
load packages on the backend.  It turns out that doing so will omit
six objects from the dumps, though (and technically will include some
objects in the dumps which never get loaded by the game while actually
playing it).  So *technically*, to get the full object set, you'll have
to do some manual work to load a character, get the object dumps, then
load the next character, get *those* object dumps, etc.  Alternatively,
if you don't mind having the not-actually-in-the-game objects in your
dumps, you could do the fully-automated process, and then just do a
handful of manual dumps, putting them into your `Launch.log` where
appropriate.  The objects which are missing from the fully-automated
method are:

- `GD_Attributes_Lilac.Init_PlayerSkillDamage_AdditionalDamagePerLvl`
- `GD_Attributes_Lilac.Init_PlayerSkillDamage_Part2`
- `GD_Attributes_Lilac.Init_PsychoSkillDamage`
- `GD_Balance_HealthAndDamage.Init_PlayerSkillDamage_AdditionalDamagePerLvl`
- `GD_Balance_HealthAndDamage.Init_PlayerSkillDamage_Part2`
- `GD_Tulip_DeathTrap.AI.WillowAIDef_DeathTrap:AIBehaviorProviderDefinition_1.Behavior_DeathTrapSoundFix`

The first three will be present if you load up Krieg, and the next three
can be dumped when Gaige is loaded.  (The `GD_Balance_HealthAndDamage`
objects also show up for Maya, and possibly others, but since you're
grabbing the DeathTrap one anyway, you may as well just grab them from
Gaige.)

After finding out about the missing data (at first I'd only known about
`Init_PlayerSkillDamage_AdditionalDamagePerLvl`), I'd also done manual
dumps for all vehicles, just in case I was missing anything.  It turns
out that I wasn't, but the manual character-dump process below also
includes vehicles in the manual steps.  That's not really necessary,
but if you're doing the character work already it's not *that* much
more.

Whether or not those six objects are worth going through each character
to dump manually is certainly up to you.  In the end, if I wasn't
doing these to provide "clean" BLCMM OE dumps, I probably wouldn't care,
though the data that I'm providing for OE is now constructed using
the manual dumps.

### Original, Fully-Automated Dumps

0. Install the `DataDumper` mod into PythonSDK's `Mods` dir, copy the
   scripts in `scripts` to your `WillowGames` folder (where your
   `Logs` and `SaveData` dirs are), make sure you can activate "Data Dumper"
   from PythonSDK's "Mods" menu.  Have a level 80 char who's been through
   *all* game content ready to go, and when you enter the game, play in
   Normal so that you won't be in danger of getting killed.
1. Start BL2, activate Data Dumper, head into game, hit `B` to run in the
   default `Maps Forward (with char+vehicle)` mode.  Once the game
   auto-exits, copy `Launch.log` up alongside the scripts you copied, with
   the filename `Launch.log-all_object_names_fwd`
2. Start BL2 again, activate Data Dumper, head into game, hit `N` twice to
   cycle to `Maps Reverse (with char+vehicle)` mode, and hit `B` to run
   again.  Once the game auto-exits, copy `Launch.log` up alongside the scripts
   you copied, with the filename `Launch.log-all_object_names_rev`
3. Run `generate_obj_dump_lists.py`
4. Start BL2 again, activate Data Dumper, head into game, hit `N` a bunch until
   you cycle to `Dump Data (with char+vehicle)` mode, and hit `B` to start.
   Once the game auto-exits, check `Launch.log` starting from
   `switch.to.charvehicle` and see if there are a bunch of `No objects found`
   errors after awhile.
5. If there were no `No objects found` errors in the `charvehicle` section,
   copy `Launch.log` up alongside the scripts, with the filename
   `Launch.log-data_dumps`
6. If there *were* errors in the `charvehicle` section, copy `Launch.log`
   up with the scripts as `Launch.log-data_dumps_minus_charvehicle`.
   Start BL2 again, activate Data Dumper, head into game, hit `N` three
   times to switch to the character/vehicle mode, and hit `B` to start.
   Once the game exits, save `Launch.log` as `Launch.log-data_dumps_charvehicle`
   and run `combine_vehiclechar.py` to generate `Launch.log-data_dumps`.
7. Run `categorize_data.py`
8. If desired, hop back into BL2, load a Krieg and Gaige char, in turn, and
   dump the above six objects mentioned in the previous section.  Save the
   dumps manually in the appropriate file in the `categorized` directory.
9. Sanitize any data if you like, removing some personal information from
   the dumps in the `categorized` directory.  See below for known locations
   of personal information (steam username/userid, hostname, etc).
10. Head back into BL2 as Krieg and manually dump
    `GD_Lilac_Skills_Hellborn.Skills.Projectile_FireBall:BehaviorProviderDefinition_0.Behavior_AttemptStatusEffect_1`,
    saving it inside `Behavior_AttemptStatusEffect.dump` once you're out.
11. If you want, run `compare_blcmm_data.py` to generate a list of how the new
    data files compare to your existing files, just to spot-check the data.
12. Run `generate_blcmm_data.py` - this will generate OE-compatible files
    inside the directory `generated_blcmm_data`.  Note that the current version
    of this script generates data for OpenBLCMM, the newer 2023 version, *not*
    the BLCMM version that's been in-use for awhile now.

For BL2, steps 1 and 2 should take about two hours each, and generate about a 6GB
logfile each.  Step 4 should take about 90 minutes, and generate another
6GB file.  While processing, you'll want another 8GB or so free space
beyond that, to allow for processing.  So make sure you've got at least
26GB free on your HD before starting this off.  You can decrease that
requirement by removing some files as you go, of course -- once you've
done step 4, you don't actually need the files from steps 1 or 2 anymore,
for instance.

For TPS, steps 1 and 2 should take a little under an hour each, and generate
logfiles a bit less than 3GB each.  Step 4 should take about 45 minutes, and
generate a file that's a little over 3GB.  While processing, you'll want
another 5GB or so free space beyond that, to allow for processing.  So make
sure you've got at least 14GB free on your HD before starting this off.  As
with BL2, you could decrease the requirement by removing some unnecessary
files as you go.

