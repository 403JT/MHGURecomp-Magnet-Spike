# Compatibility — v0.1.0-alpha.5

- **Game:** Monster Hunter Generations Ultimate 1.4.0, English, title
  `0100770008DD8000`, executable build ID `FB08F1D20FD1204FE7070672777F869B`.
- **Runtime tested:** official Windows x64 MHGURecomp **0.18.0**, using its
  built-in `mods/<folder>/exefs` and `romfs` loader. No modified executable or
  external launcher is required to play the release.
- **Fresh merged native tests:** single-player, Guild style, disposable copied
  saves, muted. Both forms' aim/pin/attraction, the formerly stalled follow-up
  via ordinary inputs, and the four restored motion timelines passed.
- **Compiled checks:** names and smithy, aim, sprint-roll, guard-draw,
  interrupted damage and recovery passed against the merged source.

Earlier releases supply historical evidence for sharpness/Whetstone use,
smithy/progression, six-style aiming, ordinary sprint-roll/guard-draw and remote
state/marker diagnostics. Those are not fresh full-play tests of this combined
build. Connected multiplayer, a new full hunt, all styles on the combination,
human assessment of the restored lead-ins and mouse aim remain unvalidated.
The reproduced Double Slash follow-up stall is fixed; other freezes and the
unconfirmed parry report are not ruled out.

This is an experimental **Recomp** package. Switch emulators, Switch hardware,
other game versions/languages, operating systems and older/future Recomp
versions are outside the tested target. Enable only one Magnet Spike package.
Multiple mods supplying subsdk1 or overlapping patches/new weapon allocations
need explicit integration; no other mod combination is certified.

See [INSTALL.md](INSTALL.md), [RELEASE_NOTES.md](RELEASE_NOTES.md) and the exact
payload/test record in release-validation.json.
