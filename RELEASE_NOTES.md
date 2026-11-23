# Magnet Spike v0.1.0-alpha.5

Combined release for **MHGU 1.4.0 English** using the built-in mod loader in
**official Windows MHGURecomp 0.18.0**. This brings together the alpha.3 name-fix
release, alpha.3 Glaive-aim release and the supplied alpha.4 motion-length-1 build.
Install this one package in place of the older Magnet Spike versions.

## Included changes

- All 13 requested weapon names now end in **Magnet Spike** instead of Great
  Sword. Existing equipment receives the names automatically. Native Great
  Sword names are unchanged. See [NAME_CHANGES.md](NAME_CHANGES.md).
- Holding **ZR / right trigger** uses the normal third-person camera and the
  native Insect Glaive pink centre cursor. **ZR+A / right face** fires the pin;
  **ZR+X / top face** still performs attraction when its normal requirements
  are met. The camera uses the normal right-stick settings. See
  [GLAIVE_AIM.md](GLAIVE_AIM.md) and [CONTROLS.md](CONTROLS.md).
- Fixes the reproduced stall in Magnetic Double Slash's late **X+A** follow-up:
  its animation can now reach the frame that the action is waiting for.
- Includes all four animation-length corrections from the supplied alpha.4.
  Three other attacks now play their previously skipped opening animations:
  an Impact Down Swipe variant, Impact Horizontal Swipe after Overhead
  Horizontal, and the Cutting A attack from the stick move. Their attacks start
  roughly **0.75–0.85 seconds later** than alpha.3. This is inherited from alpha.4,
  not a new balance pass. See [MOTION_FIXES.md](MOTION_FIXES.md).

Also retains the earlier sharpness, sprint-roll, sheathed R+X+A guard-draw,
interrupted-damage, state-ownership, quick-message suppression and remote-marker
update fixes. Weapon IDs, crafting/upgrade trees, models, stats, damage values,
combo links, recovery windows and gauge costs remain at the prior release
values. Damage has not been retuned for the restored lead-ins.

## Validation

The exact combined payload passed seven compiled regression groups, including
all 408 name variants (13 corrected, 395 unchanged), smithy data, 148 aim checks,
sprint-roll, guard-draw, interrupted damage and recovery. Independent conversion
checks reproduce the supplied alpha.4 motion lists exactly and verify that only
the four expected slots change from alpha.3. The frame-wait build guard also
rejects the original one-frame stall condition.

Fresh muted tests on official Windows 0.18.0 used disposable save copies. Both
forms displayed the cursor, fired pins and completed their aiming attacks
against a moving monster. Ordinary inputs entered the formerly stalled follow-up
twice and recovered; targeted timelines verified all four restored motions
advance and finish. Original saves and the tested mod files were unchanged.
ZIP contents, source scope and SHA-256 checksums are checked during packaging.

This remains an experimental alpha. The fresh merged tests use Guild style and
controlled single-player fixtures; connected multiplayer, all six styles on the
combined build, human assessment of the restored animation timing and a new full
hunt are not claimed. The separate aim release had six-style testing; that is
historical evidence. The reproduced follow-up stall is fixed, but other causes
of freezes and the unconfirmed parry report are not ruled out.

## Updating

Close MHGURecomp, back up your save, move the older Magnet-Spike mod folder out
of mods, and install the **Magnet-Spike** folder from
**Magnet-Spike-v0.1.0-alpha.5.zip**. Keep only one copy enabled. Existing Magnet
Spike equipment needs no recrafting or save editing. Use the mod ZIP to play;
the matching source ZIP is for developers. See [INSTALL.md](INSTALL.md).

GitHub upload files: the mod ZIP, source ZIP, release-manifest.json,
release-validation.json and SHA256SUMS.txt. This package preparation does not
upload or publish the release.
