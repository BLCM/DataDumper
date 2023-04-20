Borderlands 2/TPS/AoDK Data Dumper
==================================

This is a system for generating data dumps from Borderlands
2, The Pre-Sequel, and the standalone Assault on Dragon Keep, for the
purposes of generating Object Explorer data for use in
[OpenBLCMM](https://github.com/BLCM/OpenBLCMM) and 
[FT Explorer](https://github.com/apocalyptech/ft-explorer).  It was also
used as the basis for data in the original [BLCMM](https://github.com/BLCM/BLCMods/wiki/Borderlands-Community-Mod-Manager),
starting with v1.2.0, though the extracts here required extra processing
to be fully compatible with the original BLCMM.

The main data collection component of this project is a
[PythonSDK](https://borderlandsmodding.com/sdk-mods/) mod which allows the
user to cycle through the various steps in the process in an interactive
way.  It also uses a few external [Python](https://www.python.org/) scripts
to massage the resulting `Launch.log` files into more useful formats and
finish up the data collection.

- [Caveats/Warnings](#caveatswarnings)
- [Overview](#overview)
- [A Note About Missing Objects](#a-note-about-missing-objects)
- [Getting The Game Ready For Dumps](#getting-the-game-ready-for-dumps)
- [Getting Characters/Vehicles Ready For Dumps](#getting-charactersvehicles-ready-for-dumps)
  - [Chars and Vehicles for Borderlands 2](#chars-and-vehicles-for-borderlands-2)
  - [Chars and Vehicles for Assault on Dragon Keep](#chars-and-vehicles-for-assault-on-dragon-keep)
  - [Chars and Vehicles for The Pre-Sequel](#chars-and-vehicles-for-the-pre-sequel)
- [The Process](#the-process)
  - [Install](#install)
  - [Preparing the Scripts](#preparing-the-scripts)
  - [Dumping and Processing](#dumping-and-processing)
- [Filtering/Scrubbing Sensitive Data](#filteringscrubbing-sensitive-data)
- [What's Happening Behind-The-Scenes](#whats-happening-behind-the-scenes)
- [FT/BLCMM Explorer Integration](#ftblcmm-explorer-integration)
- [Other Scripts](#other-scripts)
- [License](#license)

Caveats/Warnings
----------------

- The PythonSDK mod component of this project relies on using the
  `say` command to give feedback to the user as you interact with it.  Ever
  since BL2/TPS was updated with crossplatform multiplayer, the `say` command
  will crash the game if you're playing in offline mode.  So, dumping data
  using this method currently relies on having the game online.

- This whole process assumes at least a working knowledge of dealing with
  Python from the commandline (shell if on Linux, `cmd.exe` or Powershell
  if on Windows), and installing/running (and potentially tweaking) PythonSDK mods.
  The process necessarily requires quite a bit of handholding, and some
  scripts will *require* at least minor edits to work properly in your
  environment.  You're likely to end up needing to debug errors if they pop
  up, etc.  If you're interested in getting a "release-quality" set of
  dumps generated, you'll also need to be motivated enough to dig into
  data comparisons and debug issues when some objects don't get dumped, etc.

- This process has, to my knowledge, only ever been tested/run on Linux.
  There's one step in particular which, in its current state, might *only*
  work on Linux, due to some open-filehandle limits on Windows.  If you're
  running this on Windows, `categorize_data.py` might need to be adapted
  for use on your OS, and other scripts may end up needing some tweaking
  too.  PRs are welcome, for cross-platform support!

Overview
--------

There are various challenges inherent with dumping data from Borderlands
games.  There are a bunch of "transient" objects which might exist in every
level but have wildly differing content.  There's a lot of dynamically-named
objects whose numerical suffixes can change from level to level, or between
game sessions.  There's various data that's only available when specific
characters are loaded, or specific vehicles.  Ideally, you want to know what
objects are specific to an individual level, because you don't want to have
to dump *all* objects for every level, lest you end up having to sift through
hundreds of gigs of spurious dumps, when you're done.

This mod, and its associated scripts, aims to try and iron out as much of that
as possible.  The mod has various modes which you'll cycle through and kick
off at various points, depending on where you are in the process.  The app
will output the currently-available keybinds via in-game chat whenever you
interact with it, and will pop up the initial message as soon as you activate
the mod via the "Mods" menu.

Interacting with the mod is done via some keybinds, though note that the keys
are *only* available when you're actually in the game, not from the main menu.
So be sure to "continue" with the chosen character before trying to play with
it.  The keybinds were chosen based on what keys Apocalyptech had unused at the
time.  At the moment, to change them, you'll have to update the mod sourcecode:

Function | Keybind
--- | ---
Next Mode | `N`
Previous Mode | `P`
Activate/Run Mode | `B`
Cancel Current Run | `O`

The general procedure, glossing over every detail imaginable, is:

1. Do one pass of `getall`s in all levels, with all chars + vehicles, to
   figure out what objects exist.
2. Do another pass of `getall`s, loading everything in a different order,
   to try to filter out dynamically-named objects which can't be relied on
   for modding.
3. Then with the filtered list of objects, loop through all
   levels/chars/vehicles again with `obj dump`, to get the dumps.
4. Run the final processing scripts to get the data packaged for OpenBLCMM.

There are a set of modes for the `getall` steps, and then a separate set
of modes for the `obj dump` steps.  As mentioned above, you can cycle
through them with `N` and `P`.  Just pay attention to the names of the
modes, so you know whether you've got a `Getall` or `Dump` mode active!

Inbetween each step there's one or more Python scripts to be run from the
commandline to massage the data and do sanity checks, etc.  Once you've got
the dumps in hand, there's some more commands to work the data into an
export format for OpenBLCMM, and to compare the extracted dataset against
previous extractions, etc.

A Note About Missing Objects
----------------------------

Throughout the course of working with this app, I have yet to discover
a method which ends up dumping a "100% complete" set of data on its own.
Each method I've tried seems to omit at least an object or two.  The methods
currently active in the mod tend to give the results that I'm happiest
with, but there seems to be no getting around having to do some manual
cleanup after the fact.  The objects which are missing seem to change
as time goes on, in fact -- after having gone through several iterations
of data dumping, I seem to have a different set each time.

So, to help figure out what might be missing, there are a couple of
utilities which can be used to investigate the discrepancies.  Those are
listed as part of the procedure, below.

It's possibly worth noting that even in the worst cases, the vast majority
of objects *do* get dumped.  There's generally only a handful of objects
which need manual handling, out of a total of over a million (for BL2).

Getting The Game Ready For Dumps
--------------------------------

Apart from simply [having PythonSDK installed and working](https://borderlandsmodding.com/sdk-mods/),
the only other thing you'll probably want to do is apply the "array limit"
hexedit.  Ordinarily, when the game does an `obj dump` on an object with
a top-level array attribute, only the first 100 elements will be printed,
with a message afterwards saying `... N more elements`.  That's obviously
not ideal for an object database which aims to be complete, so you'll want
to fix that up.

OpenBLCMM (and BLCMM) has a hex-edit available right in the app to update
this for both BL2 and TPS.  [c0dycode's Hex Multitool](https://github.com/c0dycode/BL2ModStuff/tree/master/Hexediting#removing-the-100-element-limit)
should be able to handle it as well.  Eventually, PythonSDK will probably
take care of doing this transparently, but for now, hexedits are all we've
got for it.

Note that we do not currently have a hexedit available for the standalone
Assault on Dragon Keep, so dumps for that game will just be limited to
100 elements on top-level arrays.

Getting Characters/Vehicles Ready For Dumps
-------------------------------------------

There are some methods available in PythonSDK to automatically load in
character and vehicle data, but it tends to result in different datasets
than what's actually seen in-game, so unfortunately the best results are
achieved when you manually head to the main menu to switch up chars, and
then spawn vehicles in-game via a Catch-A-Ride.

The "modes" in the DataDumper mod are set up with some specific character
and vehicle mappings.  For instance, you'll use Axton to spawn in Skiffs
(from DLC1), and Maya to spawn in Fan Boats (from DLC3), etc.  You're free
to deviate from the pre-assigned scheme if you want, of course, but the
labels of the modes in DataDumper won't match what you're doing unless
you also tweak the mod code.

In general, I recommend using max-level characters but loading them in Normal
mode.  That way if any combat ends up getting triggered while the dumping
is happening, there's zero risk in just sitting there and taking it.  In
practice, that never really happens so long as you don't move around before
dumping, but there's a few levels where enemies spawn quite close.

### Chars and Vehicles for Borderlands 2

- Sal/Gunzerker will do the bulk of the automated dumping.  Starting
  map location is irrelevant.  Make sure he's gone through the *entire* game
  content, including DLC5 (Commander Lilith), so no cutscenes are triggered
  when hopping around.
- Axton/Commando, stationed in Wurmwater or Oasis (so long as Catch-a-Ride is
  active in that DLC).  He will be the one to spawn two sets of Skiffs during
  the process.  (First Rocket + Harpoon, and then Sawblade.)
- Maya/Siren, stationed in Scylla's Grove.  She will be the one to spawn two
  sets of Fan Boats.  (First Corrosive + Flamethrower, then then Shock.)
- Gaige/Mechromancer, stationed in the Dust (or anywhere else near a Catch-A-Ride
  where enemies are unlikely to spawn).  She will be the one to spawn first
  a pair of Bandit Technicals, and then a pair of Runners.
- Zer0/Assassin, stationed anywhere
- Krieg/Psycho, stationed anywhere

### Chars and Vehicles for Assault on Dragon Keep

The character order is the same as in Borderlands 2, though since AoDK doesn't
have any vehicles, those can be ignored.  I actually did all these dumps with
Level 1 characters who had done none of the game (since I wasn't actually
interested in playing the standalone version).  I never had any problems with
enemies attacking during the process.

- Sal/Gunzerker will do the bulk of the automated dumping.
- Axton/Commando
- Maya/Siren
- Gaige/Mechromancer
- Zer0/Assassin
- Krieg/Psycho

### Chars and Vehicles for The Pre-Sequel

I'm honestly not sure why I'd had Claptrap spawn both Moon Buggies but split
up the stingrays between Wilhelm and Jack.  At this point it's ever so slightly
more work to change it in the mode settings than it is to leave it, though,
so there it is.

- Nisha/Lawbringer will do the bulk of the automated dumping.  Starting
  map location is irrelevant.  She should have gone through the *entire* game
  content, including Claptastic Voyage, so no cutscenes are triggered when
  hopping around.
- Claptrap/Fragtrap, stationed somewhere with a handy Moon Zoomy station (Triton
  Flats or Serenity's Waste is best).  He will be the one to spawn a pair of Moon
  Buggies.
- Wilhelm/Enforcer, stationed somewhere with a handy Moon Zoomy station (Triton
  Flats or Serenity's Waste is best).  He will be the one to spawn the Flak
  Stingray.
- Jack/Doppelganger, stationed somewhere with a handy Moon Zoomy station (Triton
  Flats or Serenity's Waste is best).  He will be the one to spawn the Cryo
  Stingray.
- Athena/Gladiator, stationed anywhere
- Aurelia/Baroness, stationed anywhere

The Process
-----------

### Install

The `DataDumper` mod from this repo should be copied into PythonSDK's `Mods`
dir.  Then copy the scripts from the `scripts` dir into your `WillowGames`
folder (where your `Logs` and `SaveData` dirs are).  Make sure you can
activate "Data Dumper" mod from PythonSDK's "Mods" menu, and prep the
characters listed above -- make sure they're stationed at the correct maps
to be able to spawn vehicles, etc.

If you've run the data dumper in the past, you may want to head into the game's
`Binaries` dir to see if there are control files left inside the `datadumper`
directory there.  If so, you may want to delete all those just so nothing has
an opportunity to get in the way.

### Preparing the Scripts

At the moment, there's at least a couple of things you'll have to tweak in
the scripts, even if you're running on Linux.

1. In `check_undumped.py` and `generate_obj_dump_lists.py`, update the
   `output_dirs` var to point to your actual game install locations.  Keep
   the `datadumper` path at the end, after `Binaries`.
2. In `compare_blcmm_data.py`, update the `stock_files_dir` to point at
   the location of your original BLCMM data jars, so it knows where to find
   the data to compare to.
3. You may want to read the notes about open filehandles in `categorize_data.py`
   and make sure you understand what to do about that.  As I've mentioned
   elsewhere, it's possible that this utility, as written, is only usable by
   folks on Linux.  If a Windows user ever does want to go through this
   process, I'd welcome a PR with a Windows-friendly version.

### Dumping and Processing

1. Start the game, activate Data Dumper, and head into game as Sal or Nisha.
   You're already in `Maps Getall Forward` mode, but you can hit `N` and `P` to
   cycle through the modes to verify.  Hit `B` to run it.  Once the dumping is
   done, and you're back on the main menu, load each of the other chars above,
   in order, hit `N` to cycle to the appropriate mode (for instance,
   `Axton + Rocket/Harpoon Skiff Getall` for the first Axton dump), spawn any
   vehicles requested by the mode (for instance, Axton should spawn the rocket
   and harpoon skiffs), and then `B` to run the mode.  Repeat for all
   character/vehicle modes.  Hit `P` to cycle backwards if you accidentally miss a mode.
    1. Once done and you've exited the game, copy `Launch.log` up alongside the
       scripts you copied, with the filename `Launch.log-all_object_names_fwd`
2. Start the game again, activate Data Dumper, and you'll be going through the same
   process as the previous step but in reverse order.  I like to do the
   char+vehicle steps first (starting with Kreig or Aurelia), before arriving
   at the `Maps Getall Reverse` mode for use with Sal or Nisha.  Use `N` and `P`
   to cycle through the modes to find the ones you want.  Keep in mind that there
   are a set of `Dump` modes *after* the `Getall` modes, and we still want to do
   `getall` here.
    1.  Once you've exited again, copy `Launch.log` up alongside the scripts
        you copied, with the filename `Launch.log-all_object_names_rev`
3. From the commandline, run `generate_obj_dump_lists.py`.  This creates a bunch of
   control files inside `Binaries/datadumper` which the mod will use in the next step.
4. Start the game again, activate Data Dumper, head into game as Sal or Nisha,
   and hit `N` a bunch until you cycle to `Maps Dump` mode.  Hit `B` to start.
   When you're back at the main menu and the automated dumps have finished, hop
   into your individual characters again, using `N` to cycle into the associated
   char/vehicle mode (with `Dump` in the title, not `Getall`!).  Spawn whatever
   vehicles are necessary, and use `B` to run the mode.
    1. Once you've exited, copy `Launch.log` up alongside the scripts, with the
       filename `Launch.log-data_dumps`
5. If you want, run `check_undumped.py` to compare the list of attempted object dumps
   versus the dumps that we actually got.  If any are missing (and there probably will
   be), they'll be saved out in new "control" files in your game `Binaries` dir, under
   `datadumper/makeup`.
    1. Note first off that objects whose name have a `Willow` prefix, or with big-looking
       numeric suffixes, are likely to be dynamic objects which just didn't get caught
       by the initial round of `getall` filtering.  Many of the results in here can be
       pretty safely ignored.  `MatineeActor` objects are likely to be not worth bothering
       with, too.
    2. If you want to try re-dumping from these "makeup" files, move the original control
       files in the `datadumper` dir out of the way, and replace with the `makeup`
       files.  Then head back into the game and switch to the `Makeup Dumps` mode (which
       is near the end of the mode list), and run that.  (That mode is practically identical
       to the usual map-dumping mode, but will *not* dump the "Default" objects beforehand.)
       The `check_undumped.py` script will also have let you know if you need to
       head into any of the char/vehicle-specific modes and re-run from there.
    3. Note that in my experience, this rarely actually succeeds in getting new dumps,
       without manually tweaking the makeup control files.  Many cases seem to be
       objects which have been categorized into the wrong level.  So the first map
       (`Ash_P`) may have a bunch of objects which are clearly intended for other maps.
       So you may want to move things around so they make sense, creating your own
       control files like `Caverns_P.1` and shuffling objects around.  You may need to
       head into an existing BLCMM Object Explorer install to run some references to
       find out where some objects are intended to be.
    4. Alternatively, if there's not much, you could always just dump the missing
       objects manually in-game, of course, instead of loading up the `Makeup Dumps`
       mode and running that.
    5. If you did get some fresh object dumps, concatenate the new `Launch.log` onto
       the end of your `Launch.log-data_dumps` file.
6. Create a `scrub.txt` file alongside your scripts (and the collected `Launch.log-*`
   files).  This file will contain patterns to scrub out of the data, used to hide
   things like usernames and Steam IDs when prepping datasets for public release.  If
   you don't care about sanitizing data, just create it as an empty file.  Keep in
   mind that if any string you put in here is too generic, you may end up replacing
   strings in more data than you intend.  Strings to consider adding:
    1. Steam Username
    2. 17-digit Steam ID
    3. Steam Support Token
    4. Epic Games equivalents of the above, if running off EGS.
    5. Local box hostname (in all uppercase)
7. Run `categorize_data.py`
    1. This step may currently only work on Linux, and even on Linux will probably
       require temporarily tweaking your user's allowed open filehandle count.
    2. This step will also use the contents of `scrub.txt` to automatically scrub
       data from the dumps.  See below for some known locations of information you
       might want to remove, or where to find some of the info if you're not sure
       what it is (like your Steam ID or support token, etc).
    3. This utility will also recommend manually clearing the `Scrollback` attribute
       from an object which holds console scrollback info.  Do so manually, if you
       want.
8. If you want, run `compare_blcmm_data.py` to compare the categorized dataset against
   the dumps provided by the original vanilla BLCMM data.  This will generate a
   `comparisons` directory which you can browse through, and see if anything in there
   merits manual dumping.  Note that there are various CLI args to this util which can
   filter out various objects which are likely to be "noise" in the results.  You'll
   probably want to run it with `-c`/`--clean` to turn on all of these.
    1. If you do have objects you want to manually dump, hop into the game and do so.
       You can make use of the `Makeup Dumps` mode, if you want to use control files
       such as describe above in the `check_undumped.py` section.
    2. Once you've exited the game, concatenate the new `Launch.log` to the end of
       your `Launch.log-data_dumps` file, and re-run `categorize_data.py`
9. Copy `resources/enums.dat` into the same directory as the scripts you've been
   running, and then run `generate_blcmm_data.py` - this will generate OE-compatible
   files inside the directory `generated_blcmm_data`.  Note that the current version
   of this script generates data for OpenBLCMM, the newer 2023 version, *not*
   the BLCMM version that's been in-use for awhile now.

Filtering/Scrubbing Sensitive Data
----------------------------------

The `categorize_data.py` script will attempt to scrub sensitive data for you,
as it's looping through the dumps, based on the contents of a `scrub.txt` file
which you can provide yourself.  As mentioned above, you probably want to be
scrubbing your steam username/userid/support-token, and possibly your box's
local hostname.  For users on Epic/EGS, there's probably some similar things
to filter out.

Also as mentioned above, if your Steam username (or other info) happens to be
a string which might appear somewhere in the Borderlands data, you may end up
wanting to scrub that info manually instead of using `scrub.txt`.  The scrubbing
process is pretty stupid, and could match strings inside dialog subtitles, or
even inside object or attribute names.  Make sure to watch the output of
`categorize_data.py` to make sure that the list of objects with scrubs ends up
looking mostly like the list below.  The process will replace the given strings
with `<hidden>`, so you can search the resulting dump files for that string
to see what might've been replaced.

Here are the locations of sensitive information that I've found thus far, across
all of BL2/TPS/AoDK.  Some may only exist for one or two of the three games.
Also, some of these don't seem to exist at all, anymore -- there have been various
changes to how the game handles its interaction with storefronts since this list
was first compiled.  There could very well be other objects with other information
in existence that haven't been found by myself, too.

- Your hostname (just the local component, and in all uppercase) can be found in:
  - `WorldInfo'Loader.TheWorld:PersistentLevel.WorldInfo_1'`
- Your Steam username can be found in:
  - `WillowPlayerReplicationInfo'Loader.TheWorld:PersistentLevel.WillowPlayerReplicationInfo_44'` *(bl2 only)*
  - `OnlineSubsystemSteamworks'Transient.OnlineSubsystemSteamworks_0'`
  - `UIDataStore_OnlinePlayerData'Transient.DataStoreClient_0:UIDataStore_OnlinePlayerData_42'` *(bl2 only)*
  - `WillowGameViewportClient'Transient.WillowGameEngine_0:WillowGameViewportClient_0'`
  - `WillowOnlineGameSettings'Transient.WillowOnlineGameSettings_0'`
- Your 17-digit Steam user ID can be found in:
  - `GearboxAccountData'Transient.GearboxAccountData_1'`
  - `OnlineSubsystemSteamworks'Transient.OnlineSubsystemSteamworks_0'`
  - `WillowSaveGameManager'Transient.WillowSaveGameManager_0'` *(tps only)*
- Your console history can be found in:
  - `WillowConsole'Transient.WillowGameEngine_0:WillowGameViewportClient_0.WillowConsole_0'`

The other thing to look out for, which `categorize_data.py` takes care of as well,
is that there are various instances in the data which output a `ShiftId` attribute,
which encodes your (and possibly your friends') Shift ID, as an array of sixteen
bytes.  You can search the dumps for `ShiftId` to take a look at that if you want.  The
`categorize_data.py` script automatically replaces the data in every instance of this
with zeroes, so no Shift IDs should be leaked in the data.

*(some other objects to look into, will get this merged up above once I'm through with
my current OpenBLCMM-related dumping)*

- Scrubbed info from WorldInfo'Loader.TheWorld:PersistentLevel.WorldInfo_1'
- Scrubbed info from GearboxAccountData'Transient.GearboxAccountData_1'
- Scrubbed info from OnlineRecentPlayersList'Transient.OnlineRecentPlayersList_0'
- Scrubbed info from OnlineSubsystemSteamworks'Transient.OnlineSubsystemSteamworks_0'
- Scrubbed info from WillowGameEngine'Transient.WillowGameEngine_0'
- Scrubbed info from WillowGameViewportClient'Transient.WillowGameEngine_0:WillowGameViewportClient_0'
- Scrubbed info from WillowConsole'Transient.WillowGameEngine_0:WillowGameViewportClient_0.WillowConsole_0'
- Scrubbed info from WillowOnlineGameSettings'Transient.WillowOnlineGameSettings_0'
- Scrubbed info from WorldInfo'menumap.TheWorld:PersistentLevel.WorldInfo_0'

What's Happening Behind-The-Scenes
----------------------------------

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
    tree manually, and exclude from that, but likewise, it's a lot of
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
  what I've done is restrict it to 600 `obj dump` statements at once, which
  seems to be sufficient to dump the whole game.
- This should generate a dump file that's a little over 6GB (as of mid June, 2019),
  and on my PC took a little under 90 minutes to complete.

### 6. Filter out any sensitive data

- A few objects can contain information like your local system username and the
  like.  See above for some sanitization tips.

### 7. Convert to OpenBLCMM Format

- This step is simple in that it can be done by executing a single script, but
  it's actually a pretty involved process.  Check the script for more details!
  The core of the script is generating a big ol' SQLite database which things
  can query, and then reorganizing the data dumps for ease of access.

FT/BLCMM Explorer Integration
-----------------------------

This is really only of interest to Apocalyptech, but in case you were interested
too: importing this data into FT/BLCMM Explorer is pretty simple.  The main
thing is, after running `generate_blcmm_data.py`, to compress the `.dump` files using
[lzma](https://en.wikipedia.org/wiki/Lempel%E2%80%93Ziv%E2%80%93Markov_chain_algorithm#xz_and_7z_formats)
(on Linux this can be done with the `xz` utilitiy).  You'll end up with files
named `ClassName.dump.xz`.  Copy those into the relevant FT Explorer resource
directory, and then run FT Explorer's `generate_indexes.py` (at the top level of
that project).  That's it!

Apoc may or may not eventually convert FT/BLCMM Explorer to use the new OpenBLCMM
data format instead, which is better in just about every way except for diskspace
requirements.

Other Scripts
-------------

There have historically been a scripts in the `scripts` directory which aren't
part of the main dumping process, but I wanted to get committed into source
control.  They probably won't be of interest to most folks, but I'll briefly
describe them here:

- `verify_encoding.py`: Just used to verify the text encoding on the generated
  dump files, to confirm that they really were latin1/iso-8859-1.  Note that
  this utility is *expected* to generate some errors as it runs.
- A collection of utilities to modify/work with the `Launch.log` files which
  are generated by various parts of this process.  All of these write to a
  new file rather than overwriting anything, so you'll need to shuffle files
  around once you've made changes.
  - `extract_section.py`: Used to extract a section (map name or char/vehicle
    mode) from a logfile.  For instance, you could specify `Cove_P` to extract
    that section, or `axton2` for Axton's second Skiff run.
  - `replace_section.py`: In the event that you want to completely *replace*
    a section inside the file (such as if you totally screwed up `axton2` and
    want to replace it with a fresh version), this is the util which can help
    with that.  Note that the utility replaces the specified section with an
    *entire* file -- if you've got a larger file with multiple sections, you
    may want to extract the new section with `extract_section.py` first.
  - `strip_duplicate_section.py`: In case you accidentally end up with the same
    section repeated more than once, you can use this script to strip out the
    *second* instance of that section.  For instance, if you accidentally run
    the second set of Axton skiff dumps while still on the `axton1` mode, you
    can specify `axton1` for the section to skip the second category.

License
-------

This code is licensed under the
[GPLv3 or later](https://www.gnu.org/licenses/quick-guide-gplv3.html).
See [COPYING.txt](COPYING.txt) for the full text of the license.

