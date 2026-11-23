# Magnet Spike v0.1.0-alpha.2 feedback fixes

This update targets MHGU 1.4.0 English through the normal mod loader in
official Windows MHGURecomp 0.18.0. It includes the cumulative fixes from
feedback candidates 1 and 2. Connected multiplayer testing is still required.

## Changes

- Preserve active hunters' weapon state when hunter objects are replaced.
  The previous full state pool could overwrite an active hunter's attack-event
  latches, repeatedly arming a hit during one animation. Reclaim departed
  objects instead, with space for a replacement awaiting roster registration.
- Advance remote hunters' combo recovery clocks in their action handler.
  GU skips their local input handler, leaving the previous recovery timer frozen.
  The local hunter keeps the existing recovery timing.
- Suppress the quick-message shortcut for the local Magnet Spike hunter in an
  online quest. Other weapon classes and other users of the native button
  getter retain their original behavior. Weapon input words are not changed.
- Stop pending Magnetic Shock pulses and owned native attack slots when their
  action is interrupted or replaced. A scoped collision check also rejects a
  cancelled hit before the following player update. Native replacement attacks
  retain their own slots; uninterrupted Shock retains all four pulses.
- Advance remote hunters' pending weapon tasks after their native update.
  Their input callback is skipped by GU, which previously left fired pins and
  attached marker effects without updates. Local tasks retain their existing
  update path and run once. This addresses a reproduced remote-path cause of a
  detached pin glow; it is not proof that every reported occurrence is resolved.

Models, crafting, damage, sharpness, combo links, guard windows, gauge costs,
and added combo-end recovery durations retain the public release values.

## What remains unconfirmed

The reported R + X Magnetic Double Slash freeze has not been reproduced in
the standing/walking/stick tests so far. The state corruption above is fixed,
but that does not establish that every cause of that particular freeze is gone.
The parry report was deferred at the user's request. Connected multiplayer
still needs a real hunt retest, including newly fired pins and attraction on
each player's screen. The isolated remote-path test does not validate network
synchronisation. Scope selection and attraction physics have not been changed.
Diablos-specific play has not been validated.

## Evidence and next test

The included validation receipt distinguishes compiled ARM regressions, native
game tests and connected multiplayer, which has not yet been tested. Regression
fixtures reproduce repeated attack arming and a local finisher softlock on the
old allocator, then verify both stop after the fix. A native game fixture also
reproduces the old nonlocal recovery freeze and verifies its exit after the fix.
Native cancellation tests reproduce live hitboxes after all four Shock actions
are rolled out of on the old build, and verify cleared hitboxes on this build.
Marker tests compare the actual effect with the saved bone-local hit point,
including effect expiry/replacement, target translation and rotation. The old
remote-input path leaves the glow behind; the corrected path follows the target.
These controlled fixtures are not connected multiplayer hunts.
All game tests are muted and use disposable save copies.

Install using the accompanying INSTALL.md, with only one Magnet Spike code mod
enabled. Keep the old release ZIP for rollback. For the next multiplayer test,
check R + X while walking and changing the stick, scope input, interrupted
attacks, and another hunter joining/leaving across consecutive quests. Report
the MHGURecomp version and hunting style with any remaining freeze.

The source archive excludes game assets, saves, memory samples and captures.
Historical regression comparisons require the locally retained baseline source
checkpoint; they are not self-contained game-free distribution tests.
