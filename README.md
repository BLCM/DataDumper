Borderlands 2/TPS Data Dumper
=============================

This is a system for generating data dumps from Borderlands
2 and TPS, for the purposes of generating Object Explorer data for use
in [BLCMM](https://github.com/BLCM/BLCMods/wiki/Borderlands-Community-Mod-Manager),
and for [FT Explorer](https://github.com/apocalyptech/ft-explorer).  It
was put together after
[Commander Lilith and the Fight for Sanctuary](https://store.steampowered.com/app/872280/Borderlands_2_Commander_Lilith__the_Fight_for_Sanctuary/)
was released, since that DLC introduced a bunch of new data which modders
would find interesting.

This method of data collection utilizes the
[PythonSDK](https://github.com/bl-sdk/PythonSDK/) project, which allows
modders to write Python code which executes directly alongside the
BL2/TPS engines, having access to engine functions directly.  It also
uses a few external [Python](https://www.python.org/) scripts to massage
the data and get it into a usable format.

Note that currently this process has *only* been tested in Borderlands 2,
though the same process should work fine on The Pre-Sequel.  There are
various places in the utilities which would have to be updated to work
with TPS, though.

The "Short" Version
-------------------

If you're familiar with Python, and already have PythonSDK running, here's
a "brief" step-by-step process of how to get your own full data dumps
from BL2.

When running scripts manually, you will doubtless have to change some file
paths in these utilities, since those are hardcoded in there.  For instance,
`generate_obj_dump_lists.py` has a hardcoded path to your Borderlands
`Binaries` directory.  The filenames I specify in these steps are the
ones hardcoded into the utilities, but you can feel free to name them
whatever you want so long as you don't mind changing them in the scripts,
too.

The utilities here have only ever been run on Linux, but they should
theoretically work fine on Windows as well.  Just remember to update
those file paths in the scripts!

### A Note About Character Data

The original version of this dump process fully automated getting object
dumps for all characters and vehicles, by using PythonSDK's ability to
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
10. Run `generate_blcmm_data.py` - this will generate OE-compatible files
   inside the directory `generated_blcmm_data`
11. Run `compare_blcmm_data.py` to generate a list of how the new data
    files compare to your existing files, just to spot-check the data.

Steps 1 and 2 should take about two hours each, and generate about a 6GB
logfile each.  Step 4 should take about 90 minutes, and generate another
6GB file.  While processing, you'll want another 8GB or so free space
beyond that, to allow for processing.  So make sure you've got at least
26GB free on your HD before starting this off.  You can decrease that
requirement by removing some files as you go, of course -- once you've
done step 4, you don't actually need the files from steps 1 or 2 anymore,
for instance.

### Newer Dumping Style, with Manual Character/Vehicle Dumps

This method requires some additional setup.  For ease of use, you'll want
to have some characters ready to go.  What I'd used, and what DataDumper's
default modes expect, is the following:

- Sal, level 80, who will do the bulk of the automated dumping.  Starting
  map location is irrelevant.  He should have gone through the *entire* game
  content, including DLC5 (Commander Lilith), so no cutscenes are triggered
  when hopping around.  Doesn't actually *have* to be level 80, but if he's
  overlevelled (and you start the game in Normal), he won't be under threat
  if enemies end up attacking in the middle of the dumps.
- Axton, stationed in Wurmwater or Oasis (so long as Catch-a-Ride is active
  in that DLC).  He will be the one to spawn two sets of Skiffs during the
  getall/dump stages (Rocket + Harpoon, then Sawblade, or whatever order you
  want, so long as you're consistent through runs.)
- Maya, stationed in Scylla's Grove.  She will be the one to spawn two
  sets of Fan Boats during the getall/dump stages (Corrosive + Flamethrower,
  then Shock, or whatever order you want, so long as you're consistent
  through runs.)
- Gaige, stationed in the Dust (or anywhere else near a Catch-A-Ride where
  enemies are unlikely to spawn).  She will be the one to spawn first
  a pair of Bandit Technicals, and then a pair of Runners.
- Zer0, stationed anywhere
- Krieg, stationed anywhere

You can, of course, use your own combinations of characters + locations, but
that setup will match the labels which DataDumper provides via its modes.
It should be pretty easily editable to match whatever else you want, though
that's probably about as much work as just using that setup anyway.
Wurmwater/Oasis and Scylla's Grove seem to be the most convenient maps to spawn
those vehicles from -- the Fan Boat spawn is just a quick hop down to the
ground level.

0. Install the `DataDumper` mod into PythonSDK's `Mods` dir, copy the
   scripts in `scripts` to your `WillowGames` folder (where your
   `Logs` and `SaveData` dirs are), make sure you can activate "Data Dumper"
   from PythonSDK's "Mods" menu.  Have the characters listed above ready
   to go.
1. Start BL2, activate Data Dumper, head into game as Sal, hit `N` once to
   cycle to the `Maps Forward (without char+vehicle)` mode.  Hit `B` to run.
   Once the dumping is done, and you're back on the main menu, load each of the
   other chars above, in order, hit `N` to cycle to the appropriate mode (for
   instance, `Axton + Skiff 1 Getall` for the first Axton dump), spawn any
   vehicles requested by the mode (for instance, Axton should spawn a couple of
   Skiffs), and then `B` to run the mode.  Repeat for all character/vehicle
   modes, of which there'll be eight total.  Hit `P` to cycle backwards if you
   accidentally miss a mode.  Once done and you've exited the game, copy
   `Launch.log` up alongside the scripts you copied, with the filename
   `Launch.log-all_object_names_fwd`
2. Start BL2 again, activate Data Dumper, head into game, hit `N` three times
   to cycle to `Maps Reverse (without char+vehicle)` mode, and hit `B` to run
   again.  Once you're at the main menu, go through the list of
   character+vehicle dumps manually, as you did in the previous step, though
   you may want to do it backwards, just to have a better chance of catching
   any dynamically-named objects.  The `P` cycle key should be helpful here.
   Remember, if going backwards, to spawn the same vehicles in the same
   "section" as before.  If you spawned a Rocket+Harpoon during `Axton + Skiff
   1 Getall`, and a Sawblade during `Axton + Skiff 2 Getall`, be sure to only
   spawn the sawblade when going backwards into #2, again.  Once you've exited
   again, copy `Launch.log` up alongside the scripts you copied, with the
   filename `Launch.log-all_object_names_rev`
3. Run `generate_obj_dump_lists.py`
4. Start BL2 again, activate Data Dumper, head into game, hit `N` a bunch until
   you cycle to `Dump Data (without char+vehicle)` mode, and hit `B` to start.
   When you're back at the main menu and the automated dumps have finished, hop
   into your individual characters again, using `N` to cycle into the `Axton +
   Skiff 1 Dump`-style modes, spawning the required vehicles, and using `B` to
   run the mode.  Once you've exited, copy `Launch.log` up alongside the
   scripts, with the filename `Launch.log-data_dumps`
5. Run `categorize_data.py`
6. If desired, hop back into BL2, load a Krieg and Gaige char, in turn, and
   dump the above six objects mentioned in the previous section.  Save the
   dumps manually in the appropriate file in the `categorized` directory.
7. Sanitize any data if you like, removing some personal information from
   the dumps in the `categorized` directory.  See below for known locations
   of personal information (steam username/userid, hostname, etc).
8. Run `generate_blcmm_data.py` - this will generate OE-compatible files
   inside the directory `generated_blcmm_data`
9. Run `compare_blcmm_data.py` to generate a list of how the new data
   files compare to your existing files, just to spot-check the data.

General Method Outline
----------------------

The general method for data collection goes like this:

### 1. Generate a list of objects to dump, part 1:

- Open each level and do a `getall <ClassName> Name` for each Class
  in the game, to get a list of all objects in each level.
  - Note that a `getall Object Name` would theoretically return all
    the objects as well, but without extra hacking, Borderlands 2 will
    crash beacuse of too much output, so we're doing it by class,
    instead.  Likewise, `getall Field Name` would crash as well, so
    skip that one too.
  - Prior to each level dump, generate an easily-recognizable line in
    the logfile by doing an `obj dump switch.to.LevelName_P`
- Load in all character and vehicle packages, then do the same `getall`
  loop to get those object names
  - Prior to this section, generate an easily-recognizable line in the
    logfile by doing an `obj dump switch.to.charvehicle`
  - This method of package loading *technically* misses six objects which
    are only loaded if characters are "really" active ingame.  You may
    want to load characters manually and run dumps that way -- if so,
    be sure to `obj dump switch.to.charactername` before each of those,
    to clearly mark the sections.
- Finally, return to the main menu to do a further set of `getall`.
  - Getting dumps from the main menu is very unlikely to be helpful
    for anything, but it's included for completeness' sake.
  - We do the main menu last, because we want object data after hotfixes
    and other engine changes have been applied.
  - Prior to this section, generate an easily-recognizable line in the
    logfile by doing an `obj dump switch.to.mainmenu`
- Quit the game and save `Launch.log` where it can be found later.  The
  file should be little under 6GB (as of mid-June, 2019), and on my PC took
  a little under two hours to complete.

### 2. Generate a list of objects to dump, part 2

- Many objects are dynamically named and can't actually be used in
  traditional mods, since the object names will change each time a
  map is loaded.
- Knowing which objects are like that is a bit tricky - in the engine
  itself, it's attributes labelled with `transient` which get the
  dynamic names, but attempting to use that information leads to a
  lot of processing that we'd have to do.
  - We *could* also just build up a list of places in the object
    tree manually, and exlude from that, but likewise, it's a lot of
    work.
- So, what we do is just repeat our previous data-collection loop, but
  just to be sure, we loop through levels in a different order, and
  load vehicle/character data in a different order as well.
- Quit the game, and save *this* `Launch.log` file alongside the original
  one.

### 3. Compare the two data dumps

- It's *possible* at this point that some of the transient data might
  by pure chance end up with the same name while in the same level, but
  it's supremely unlikely.
- So, loop through each `Launch.log`, using the `No objects found using
  command 'obj dump switch.to.foo'` markers to differentiate what stage
  of the dump you're in, and generate a list of objects per map/whatever
  which only contains objects found in both dumps.
- Make sure to do your checking in a case-insensitive manner.  The object
  names returned by `getall` can vary sometimes, for some reason.  For
  instance, you're likely to see an object with `CaraVan` versus `Caravan`
  at some point in your dumps.

### 4. Generate a list of objects to dump in each level

- Using the combined object list above, generate a "condensed" list of
  objects to dump, while looping through levels in-game again.  There
  are a lot of objects which will be active on every single level, so
  there's no point dumping the stock item pools for each level, for
  instance.
- This should be easily-generatable using the condensed list: simply
  remember which objects you've seen before, and only set up dump commands
  when you've gotten to a new object.
- There are some class types which generate extremely long `obj dump`
  outputs, which can lead to crashing the game similar to `getall Object Name`
  from above.  Rather than try to work around this, we're going to just
  exclude these classes from the dumps.  These have not historically been
  part of the BLCMM OE dataset anyway, so shouldn't be missed:
  - `AnimSequence`
  - `GBXNavMesh`
  - `GFxRawData`
  - `SwfMovie`
  - `Terrain`

### 5. Then, use that list of objects to dump to actually loop through and dump objects.

- Remember that there's a step to load characters/vehicles,
  and heading out to the main menu, as well!
- Also be sure to dump some special object names called `Default__<Classname>`
  (that's with two underscores inbetween).  There'll be one for each class
  in the game, and some modders find those objects useful.
  - Do not attempt to dump `Default__Class` - the engine freaks out and crashes.
- Restrict the number of `obj dump` commands sent by each `exec` statement,
  to avoid engine crashing problems.  Since some object types will generate
  longer dumps than others, this could theoretically be fairly intelligently
  dealt-with, to condense the number of `exec`s that have to be done, but
  what I've done is restrict it to 800 `obj dump` statements at once, which
  seems to be sufficient to dump the whole game.
- This should generate a dump file that's a little over 6GB (as of mid June, 2019),
  and on my PC took a little under 90 minutes to complete.

### 6. Filter out any sensitive data

- This still needs filling in, but a few objects can apparently contain
  information like your local system username and the like.  Still need to
  figure out what objects those are, and the best way to sanitize them.

### 7. Convert to BLCMM Format

- At this point, this is a pretty trivial step.  The BLCMM OE data format
  is basically just zip files containing the plaintext dumps, with a few
  extra files to serve as indexes for the data.  I won't document it
  fully here, but it should be easy enough to look into the code.

Status / HOWTO
--------------

### In-game Data Dumping (getall and obj-dump steps)

All ingame dumping is done via a PythonSDK mod called `DataDumper`, which
you can find in the `Mods` folder here.  Place it into `Binaries/Win32/Mods`
like you would for any other PythonSDK mod.

After activating it in PythonSDK's mod interface, hit "continue" on a character
to load into a level.  I recommend using a level 80 char running on Normal,
just in case you end up spawning into a group of enemies or something (this is
rare, but can happen in the Dust, for instance, if you happened to enter there
from Lynchwood).  Also make sure that the character you're using has been
through *all* game content, to prevent any automatic cutscene loading or the
like.

Once ingame, you can use the `N`/`n` or `P`/`p` keys to cycle through modes
("next" and "previous").  By default it starts with "forward" `getall` loading
-- ie: the first step of the above procedure.  Hitting `n` once will switch to
"reverse" `getall` loading -- ie: the second step of the above procedure.  Once
more will put it into data dumping mode, which requires that you've set up the
data files outside of the game.  A fourth mode will let you *just* do `obj
dump` statements for characters/vehicles, in case that fails on the global run
-- it seems that it's possible to be hit with garbage collection and have some
of those dumps not work, so check on that when you're done.  Hitting `n` again
will cycle back to the first mode.

Hit `B`/`b` to start running the dumps.  You'll get ingame chat messages to
let you know what it's doing, and will automatically exit the game once
it's done.  Be sure to save your `Launch.log` files inbetween, if you're
using the forward/reverse `getall` modes.

If you want to stop running at any point, you can hit `O`/`o`, though note
that if you hit `b` again after doing so, it'll start over again, which
could make your `Launch.log` a little inconsistent.  If you cancel, it'll
be best to quit the game and restart before running again.  (You can, of
course, simply quit the game manually instead of cancelling.)

### Generating objects to dump (steps 3 and 4, above)

These steps are handled via a single Python 3 script named
`generate_obj_dump_lists.py`, which you can find in the `scripts` directory.
This is a command-line utility, so you'll have to install Python, and then run
it from a commandline (for Windows users that means either `cmd.exe` or
Powershell, usually).  Make sure when installing Python to check the box which
adds Python to your system `PATH`, so it can be executed properly.

Running on Windows would look something like:

    C:\Program Files\Steam\whatever\> python generate_obj_dump_lists.py

Right now the operational parameters of the script are just hardcoded at
the top, so you may have to change some paths up there to get it to work.

Regardless, once this script is done, it will have generated a ton of files
which the DataDumper PythonSDK mod can use (in its "data dump" mode) to
actually dump data.  So head back in to Borderlands, enable the mod, change
to that mode, and start it up again!

**NOTE:** In the event that your vehicle/character dumps fail during
the dump, you'll need to head back in to Borderlands, flip the Data Dumper
mod to its fourth mode (vehicle/char dumps) and run it.  This will result
in having one huge `Launch.log` file with nearly everything it, and a
small one with just the vehicle/character data in it.  You'll want to
merge the vehicle/char data back into the big file, replacing the old
segment which started with `obj dump switch.to.charvehicle`.  I wrote
a little Python script to do it for me, which is `combine_vehiclechar.py`
(in the `scripts` dir).  This is undocumented and pretty bare; you'll
need to edit it to change file paths at the very least.

### Prep the data for tweaking and conversion

This isn't a step listed above, but I have a script which pulls all the
dumps out of `Launch.log` and saves them into about 3,500 individual
files, with filenames of `ClassName.dump` (inside a `categorized`
directory).  The script is called `categorize_data.py`, inside the
`scripts` folder here.

Like the other scripts here, it's somewhat rough, and requires some
editing of file paths right in the script itself.  Let me know if you
experience problems running this app on Windows - it opens up a *lot*
of filehandles at the same time, and I'm not sure if Windows will allow
that or not.

### Filter out sensitive data

Here are the locations where personal information seems to be stored.
This may not be exhaustive -- these are just the locations I've found so far.

- Your hostname can be found in:
  - `WorldInfo'Loader.TheWorld:PersistentLevel.WorldInfo_1'`
- Your Steam username can be found in:
  - `WillowPlayerReplicationInfo'Loader.TheWorld:PersistentLevel.WillowPlayerReplicationInfo_44'`
  - `OnlineSubsystemSteamworks'Transient.OnlineSubsystemSteamworks_0'`
  - `UIDataStore_OnlinePlayerData'Transient.DataStoreClient_0:UIDataStore_OnlinePlayerData_42'`
  - `WillowGameViewportClient'Transient.WillowGameEngine_0:WillowGameViewportClient_0'`
  - `WillowOnlineGameSettings'Transient.WillowOnlineGameSettings_0'`
- Your 17-digit Steam user ID can be found in:
  - `GearboxAccountData'Transient.GearboxAccountData_1'`
  - `OnlineSubsystemSteamworks'Transient.OnlineSubsystemSteamworks_0'`
- Your console history can be found in:
  - `WillowConsole'Transient.WillowGameEngine_0:WillowGameViewportClient_0.WillowConsole_0'`

Of those objects, only `Loader.TheWorld:PersistentLevel.WorldInfo_1` and
`Loader.TheWorld:PersistentLevel.WillowPlayerReplicationInfo_44` have historically
appeared in the BLCMM resource dumps.

I didn't bother writing anything automated to remove any of this, so
just edit the dump files by hand at this point (they should be nicely split
up by class after the previous step).  Our to-BLCMM process will only grab
the two objects listed in the previous paragraph, so it should be a very
small number of edits.

### Convert dumps to BLCMM format

This is done via a `generate_blcmm_data.py` script, inside the `scripts`
directory.  It expects to be run in the same directory that `categorize_data.py`
was run, so it's got that `categorized` directory to work with.  It will
output the Jars into `generated_blcmm_data`.

After the data's been generated, you can also run `compare_blcmm_data.py` to
compare our own data collection versus BLCMM's original data, just to spot-check
the data in case anything obvious was missing.  Like other utilities, you'll
have to change a file path or two in the code itself.  This expects to have
the `categorized` folder still available, and the `generate_blcmm_data.py`
script already run.  My first runthrough of this process generated the following:
https://drive.google.com/open?id=1vLBRgs-UkYfOmStP6D3KjjcYbOvMunvX

FT/BLCMM Explorer Integration
-----------------------------

This is really only of interest to Apocalyptech, but in case you were interested
too: importing this data into FT/BLCMM Explorer is pretty simple.  The main
thing is, after running `generate_blcmm_data.py`, to compress the `.dump` files using
[lzma](https://en.wikipedia.org/wiki/Lempel%E2%80%93Ziv%E2%80%93Markov_chain_algorithm#xz_and_7z_formats)
(on Linux this can be done with the `xz` utilitiy).  You'll end up with files
named `ClassName.dump.xz`.  Copy those into the relevant FT Explorer resource
directory, and then run `generate_indexes.py` (at the top level of that project).
That's it!

License
-------

This code is licensed under the
[GPLv3 or later](https://www.gnu.org/licenses/quick-guide-gplv3.html).
See [COPYING.txt](COPYING.txt) for the full text of the license.
