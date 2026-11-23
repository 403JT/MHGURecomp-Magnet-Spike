# Install v0.1.0-alpha.2

## Before installing

1. Close MHGURecomp.
2. Back up your entire save folder. On Windows the default is
   `%APPDATA%\MHGURecomp\save\`. A custom **Save folder** setting takes precedence.
   Keep the backup outside the live save folder and record that it predates this mod.
3. Use your own MHGU **1.4.0** game data and select English. Confirm the runtime
   version against [COMPATIBILITY.md](COMPATIBILITY.md).
4. For this alpha, disable other mods before testing. Another mod providing
   `exefs/subsdk1`, another new-weapon implementation, or overlapping executable
   patches can conflict. No particular mod combination is certified.

## Install

1. Download `Magnet-Spike-v0.1.0-alpha.2.zip` from GitHub Releases.
2. Extract it and copy its **Magnet-Spike** folder into MHGURecomp's **mods** folder:

   ```text
   MHGURecomp/
     mhgurecomp.exe
     mods/
       Magnet-Spike/
         exefs/
           subsdk1
           FB08F1D20FD1204FE7070672777F869B.ips
         romfs/
         README.md
         LICENSE
   ```

3. In the normal MHGURecomp settings, enable **Magnet-Spike** in the Mods tab if
   needed. Save the settings and restart the game.
4. Continue your own hunter. Visit the smithy and select **Magnet Spike** on the
   third weapon-category page. Craft an **MS** weapon using its listed materials.
   Recipes follow the normal progression/unlock rules.

Do not copy anything into `data/exefs` or `data/romfs`. The game files stay intact.
Do not install the development project's test profile, launcher, runtime or saves.

## Update

Close the game and make a new save backup. Move the old **Magnet-Spike** folder
out of `mods`, then put the new version in its place. Keep only one copy enabled.
Read the new version's notes before loading a save from an older mod version.

Alpha.2 includes the cumulative feedback fixes described in
[FEEDBACK_FIXES.md](FEEDBACK_FIXES.md). Existing Magnet Spike weapon IDs,
recipes, stats and models are preserved; no save editing or recrafting is
needed when updating from alpha.1.

This release also includes the earlier fix for crafted weapons being capped at red/low
sharpness. Restart with the updated mod; existing weapons use their correct
sharpness automatically. Recrafting or editing your save is unnecessary.

## Remove or roll back

This alpha has no automatic migration for saves that own Magnet Spike equipment.
The supported removal procedure is to close the game, remove/disable the mod and
restore your **pre-mod save backup** before starting the game again. That backup
does not contain progress made after it was created.

Do not assume that simply unequipping the weapon makes a modded save safe to use
without the mod. Selling/removing gear as a migration path has not been validated.

## If it does not appear

Check for an extra nested folder, verify that the mod is enabled, restart, and
check the game's `log.txt` for `[mods]` lines. Confirm MHGU 1.4.0 and English.
If you changed MHGURecomp's files/mods location, use that location's `mods` folder.
