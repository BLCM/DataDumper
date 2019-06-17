Borderlands 2/TPS Data Dumper
=============================

This is an in-progress system for generating data dumps from Borderlands
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

Method
------

The general method for data collection goes like this:

### 1. Generate a list of objects to dump, part 1:

* Open each level and do a `getall <ClassName> Name` for each Class
  in the game, to get a list of all objects in each level.
  * Note that a `getall Object Name` would theoretically return all
    the objects as well, but without extra hacking, Borderlands 2 will
    crash beacuse of too much output, so we're doing it by class,
    instead.  Likewise, `getall Field Name` would crash as well, so
    skip that one too.
  * Prior to each level dump, generate an easily-recognizable line in
    the logfile by doing an `obj dump switch.to.LevelName_P`
* Load in all character and vehicle packages, then do the same `getall`
  loop to get those object names
  * Prior to this section, generate an easily-recognizable line in the
    logfile by doing an `obj dump switch.to.charvehicle`
* Finally, return to the main menu to do a further set of `getall`.
  * Getting dumps from the main menu is very unlikely to be helpful
    for anything, but it's included for completeness' sake.
  * We do the main menu last, because we want object data after hotfixes
    and other engine changes have been applied.
  * Prior to this section, generate an easily-recognizable line in the
    logfile by doing an `obj dump switch.to.mainmenu`
* Quit the game and save `Launch.log` where it can be found later.  The
  file should be about 5.7GB (as of mid-June, 2019).

### 2. Generate a list of objects to dump, part 2

* Many objects are dynamically named and can't actually be used in
  traditional mods, since the object names will change each time a
  map is loaded.
* Knowing which objects are like that is a bit tricky - in the engine
  itself, it's attributes labelled with `transient` which get the
  dynamic names, but attempting to use that information leads to a
  lot of processing that we'd have to do.
  * We *could* also just build up a list of places in the object
    tree manually, and exlude from that, but likewise, it's a lot of
    work.
* So, what we do is just repeat our previous data-collection loop, but
  just to be sure, we loop through levels in a different order, and
  load vehicle/character data in a different order as well.
* Quit the game, and save *this* `Launch.log` file alongside the original
  one.

### 3. Compare the two data dumps

* It's *possible* at this point that some of the transient data might
  by pure chance end up with the same name while in the same level, but
  it's supremely unlikely.
* So, loop through each `Launch.log`, using the `No objects found using
  command 'obj dump switch.to.foo'` markers to differentiate what stage
  of the dump you're in, and generate a list of objects per map/whatever
  which only contains objects found in both dumps.

### 4. Generate a list of objects to dump in each level

* Using the combined object list above, generate a "condensed" list of
  objects to dump, while looping through levels in-game again.  There
  are a lot of objects which will be active on every single level, so
  there's no point dumping the stock item pools for each level, for
  instance.
* This should be easily-generatable using the condensed list: simply
  remember which objects you've seen before, and only set up dump commands
  when you've gotten to a new object.
* There are some class types which generate extremely long `obj dump`
  outputs, which can lead to crashing the game similar to `getall Object Name`
  from above.  Rather than try to work around this, we're going to just
  exclude these classes from the dumps.  These have not historically been
  part of the BLCMM OE dataset anyway, so shouldn't be missed:
  * `AnimSequence`
  * `GBXNavMesh`
  * `SwfMovie`
  * `Terrain`

### 5. Then, use that list of objects to dump to actually loop through and

dump objects.  Remember that there's a step to load characters/vehicles,
and heading out to the main menu, as well!
* Also be sure to dump some special object names called `Default__<Classname>`
  (that's with two underscores inbetween).  There'll be one for each class
  in the game, and some modders find those objects useful.
* Restrict the number of `obj dump` commands sent by each `exec` statement,
  to avoid engine crashing problems.  Since some object types will generate
  longer dumps than others, this could theoretically be fairly intelligently
  dealt-with, to condense the number of `exec`s that have to be done, but
  what I've done is restrict it to 800 `obj dump` statements at once, which
  seems to be sufficient to dump the whole game.

### 6. Filter out any sensitive data

* This still needs filling in, but a few objects can apparently contain
  information like your local system username and the like.  Still need to
  figure out what objects those are, and the best way to sanitize them.

### 7. Convert to BLCMM Format

Status / HOWTO
--------------

This is still in-progress, so details may change.

### In-game Data Dumping (getall and obj-dump steps)

All ingame dumping is done via a PythonSDK mod called `DataDumper`, which
you can find in the `Mods` folder here.  Place it into `Binaries/Win32/Mods`
like you would for any other PythonSDK mod.

After activating it in PythonSDK's mod interface, hit "continue" on a character
to load into a level.  I recommend using a level 80 char running on Normal,
just in case you end up spawning into a group of enemies or something (this is
rare, but can happen in the Dust, for instance, if you happened to enter there
from Lynchwood).

Once ingame, you can use the `O`/`o` key to cycle through modes.  By default
it starts with "forward" `getall` loading -- ie: the first step of the above
procedure.  Hitting `o` once will switch to "reverse" `getall` loading -- ie:
the second step of the above procedure.  Once more will put it into data
dumping mode, which requires that you've set up the data files outside of
the game.  (Hitting `o` again will cycle back to the first mode.)

Hit `B`/`b` to start running the dumps.  You'll get ingame chat messages to
let you know what it's doing, and will automatically exit the game once
it's done.  Be sure to save your `Launch.log` files inbetween, if you're
using the forward/reverse `getall` modes.

If you want to stop running at any point, you can hit `P`/`p`, though note
that if you hit `b` again after doing so, it'll start over again, which
could make your `Launch.log` a little inconsistent.  If you cancel, it'll
be best to quit the game and restart before running again.  (You can, of
course, simply quit the game manually instead of cancelling.)

### Generating objects to dump (steps 3 and 4, above)

These steps are handled via a single Python 3 script, which you can find in
the `scripts` directory.  This is a command-line utility, so you'll have
to install Python, and then run it from a commandline (for Windows users
that means either `cmd.exe` or Powershell, usually).  Make sure when installing
Python to check the box which adds Python to your system `PATH`, so it
can be executed properly.

Running on Windows would look something like:

    C:\Program Files\Steam\whatever\> python generate_obj_dump_lists.py

Right now the operational parameters of the script are just hardcoded at
the top, but I plan on making that a little more user-friendly before I'm
through with creating these utilities.

Regardless, once this script is done, it will have generated a ton of files
which the DataDumper PythonSDK mod can use (in its "data dump" mode) to
actually dump data.  So head back in to Borderlands, enable the mod, change
to that mode, and start it up again!

### Filter out sensitive data

This hasn't been started yet!

### Convert dumps to BLCMM format

This hasn't been started yet!
