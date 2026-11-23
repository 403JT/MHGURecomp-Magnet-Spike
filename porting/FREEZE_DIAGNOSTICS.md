# Private freeze diagnostic build

The reported alpha.2 freeze remains under investigation. This build includes
the sprint-roll and guard-draw corrections plus extra logging. It does not
automatically cancel a stuck move or alter weapon mechanics.

Use MHGU1.4.0 English with official Windows MHGURecomp0.18.0. Close the game,
keep a save backup, and move the existing Magnet-Spike mod folder outside the
mods directory. Extract the diagnostic ZIP's Magnet-Spike folder in its place.
Keep only one Magnet Spike code-mod copy enabled. Use your normal runtime;
no development executable, launcher or test save is supplied or required.

Try the inputs/hunt that produced the freeze. If it happens, leave the hunter
stuck for about five seconds before trying to recover or closing the game.
Keep that run's log.txt and note the button input, weapon form and hunting style.
Attach the log in this chat. A short clip alongside the log can help match the
visible pose to the recorded action.

The ms-freeze lines record input edges, action/step, animation frame/speed/blend,
owner state and recovery clock. Unlike the regular trace, they continue after
600 transitions. Periodic samples during an unchanged action can also occur
during intentional holds; they do not establish a freeze by themselves.
There is no automatic raw-memory dump or video capture in this build.

Restore the normal candidate mod folder after testing. Do not install the
normal and diagnostic ZIPs together. Neither package has been uploaded or
published as a release.

Source build: run porting/build_module.py --freeze-diagnostics. Its output is
kept under porting/output/freeze-diagnostics. The default build omits the extra
logging. The source archive contains no game data or save files.
