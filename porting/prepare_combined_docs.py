"""Write cumulative alpha.5 documentation in the isolated publication source."""
import re
from prepare_combined_release import STAGE, VERSION


NOTES = '''# Magnet Spike v0.1.0-alpha.5

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
'''

README = '''# MHGURecomp Magnet Spike — v0.1.0-alpha.5

Adds Magnet Spike as its own smithy weapon category in MHGU 1.4.0 English.
This combined alpha includes the 13 weapon-name corrections, Insect Glaive-style
camera and cursor, and all four motion-length fixes from the supplied alpha.4.
The late Double Slash X+A follow-up now completes; three other restored opening
animations make their attacks start roughly 0.75–0.85 seconds later.

Use **Magnet-Spike-v0.1.0-alpha.5.zip** with official Windows MHGURecomp 0.18.0's
built-in mod loader. Replace the previous mod folder and enable only one copy.
Existing equipment needs no recrafting. The source archive contains no game
assets, game executable, saves or test captures.

Read [INSTALL.md](INSTALL.md), [CONTROLS.md](CONTROLS.md),
[RELEASE_NOTES.md](RELEASE_NOTES.md) and [COMPATIBILITY.md](COMPATIBILITY.md).
Details: [NAME_CHANGES.md](NAME_CHANGES.md), [GLAIVE_AIM.md](GLAIVE_AIM.md),
[MOTION_FIXES.md](MOTION_FIXES.md) and [FEEDBACK_FIXES.md](FEEDBACK_FIXES.md).

The exact merged build passed compiled regressions and focused muted native
tests. Connected multiplayer and a new full hunt of this combination remain
untested. See release-validation.json for the exact scope and file hashes.

Developer information: [BUILDING.md](BUILDING.md), [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
'''

AIM = '''# Insect Glaive-style Magnet Spike aiming

Included in the combined v0.1.0-alpha.5 release alongside the name and motion
fixes. Hold **ZR / right trigger**, without R, to keep the standard third-person
camera and display GU's native pink Glaive cursor at screen centre. Right-stick
aiming uses the normal camera settings, inversion and pitch limits.

**ZR+A / right face** fires the existing magnetic pin. With a valid marker more
than 14 m and less than 40 m away, stamina and one movement-gauge bar,
**ZR+X / top face** attracts the hunter. ZR+B repels when the marker is within
14 m. Distances are measured to the attached marker and change as the monster
moves. Release ZR to hide the cursor. Other bindings retain their existing
meaning. See [CONTROLS.md](CONTROLS.md).

The native Glaive reference uses neither the gunner aim byte nor quest-camera
aim mode. This port does the same. The Magnet Spike vtable's slot 342 supplies
the native Glaive cursor capability only for the local aiming hunter. It does
not call Glaive action handlers or access Glaive's larger private player fields.
The normal camera handles input once; the weapon reads its direction. Shot
speed, collision, marker attachment and distance requirements are unchanged.

The aim change is copied exactly from the alpha.3 Glaive-aim source: ms_act.c,
ms_class.c and ms.h. State layout is unchanged. The fresh combined-build tests
verify cursor/camera continuity, pin shots and completed attraction attacks in
both forms using Guild style. The standalone aim release's six-style tests
remain historical evidence; connected multiplayer and mouse aiming are not
covered by the fresh merged tests. See release-validation.json.
'''

MOTIONS = '''# Motion-length corrections in alpha.5

This release preserves all four corrections in the supplied root alpha.4
**motion-length-1** build. Some Frontier motions have a zero frame-count header
despite containing later animation keys. Trusting the header produced a
one-frame motion. The converter now uses the greater of the header length and
the last key's frame, and rejects a frame-wait step its motion cannot reach.

| Slot | Frontier motion | Frames before → after | First use |
| --- | --- | --- | --- |
| 135 | 1426 | 1 → 27 | action 153, late Double Slash X+A follow-up |
| 46 | 1057 | 1 → 45 | action 21, Impact Down Swipe variant |
| 49 | 1055 | 1 → 47 | action 24, Impact Horizontal Swipe after Overhead Horizontal |
| 78 | 1067 | 1 → 49 | action 49, Cutting A attack from the stick move |

The late Double Slash follow-up waits for frame 26. Previously its motion ended
at frame 0, so it could hold the hunter's pose until a hit interrupted it. The
restored motion reaches that frame and lets the action continue normally.

The other three actions previously skipped their lead-in. They now play it,
so attack onset is later. Alpha.4's measured delay relative to alpha.3 was
0.74 s for action 21, 0.75 s for action 24 and 0.85 s for action 49. These inherited
timing changes are included intentionally in this combination. Damage, motion
values, hit data, combo links, end recovery and gauge costs are unchanged;
balance has not been retuned for the longer openings.

All 54 RomFS files match the supplied alpha.4. Relative to original alpha.3,
only player/quest/w05.arc and weapon/w05/g00.arc differ: one motion-list member
per archive, with only the four slots above changed. The frame-wait tables are
unchanged. The combined code module and executable patch are newly linked to
include the name and aim changes; alpha.4's code-module hash does not describe
this alpha.5 build. The converter changes in msmot.py, msbuild.py and msfx.py
are copied exactly from the matching alpha.4 source.

Independent in-memory conversion reproduced both alpha.3 lists before the
change and the exact alpha.4 lists after it. Fresh muted tests on the combined
payload reached action 153 through ordinary inputs twice without stalling;
targeted native timelines verified all four restored first steps, their advance
to the attack and completion. The supplied alpha.4's broader action sweep is
historical, not a fresh sweep of this combination.

The reported video has no matching game log, so this is not proof of every
reported freeze's cause. Other stuck states and the parry report are not ruled
out. Human assessment of animation appearance/feel and connected multiplayer
remain outstanding. See release-validation.json.
'''

COMPAT = '''# Compatibility — v0.1.0-alpha.5

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
'''

FEEDBACK = '''# Cumulative feedback fixes

The combined alpha.5 retains the earlier public fixes:

- Correct crafted-weapon sharpness capacity and normal sharpening.
- Preserve active hunters' weapon state when player objects change, preventing
  repeated arming from overwritten event latches; reclaim departed objects.
- Advance remote recovery clocks and pending weapon tasks through their update
  path, preserving local timing and updating fired pins/attached marker effects.
- Suppress the online quick-message shortcut for the local Magnet Spike hunter.
- Cancel owned attack slots and pending Magnetic Shock pulses when interrupted,
  without deleting a native replacement attack's own slots.
- Allow sheathed sprint rolls and route sheathed R+X+A to Impact Guard draw.
- Use Insect Glaive-style camera/cursor and apply the 13 requested weapon names.
- Restore four motion lengths, including the late Double Slash X+A follow-up
  stall; see [MOTION_FIXES.md](MOTION_FIXES.md) for the inherited timing changes.

Fresh compiled regressions cover names/smithy, aiming, sprint-roll, guard-draw,
damage cancellation and recovery. Fresh muted native tests cover both forms'
aim/pin/attraction and the four restored motions, including ordinary inputs into
the formerly stalled follow-up. See release-validation.json for the exact scope.
Earlier remote-path and marker diagnostics were controlled tests, not connected
multiplayer hunts; the combination still needs a real multiplayer retest.

The reproduced follow-up stall is fixed. The original video is not proven to
show that exact case; other freezes are not ruled out. The parry report remains
unconfirmed. The new animations' look and longer openings need human play
assessment. No claim of complete Frontier parity or universal stability is made.
'''


def main():
    repo = STAGE / 'source'
    docs = {'README.md': README, 'RELEASE_NOTES.md': NOTES, 'GLAIVE_AIM.md': AIM,
            'MOTION_FIXES.md': MOTIONS, 'COMPATIBILITY.md': COMPAT, 'FEEDBACK_FIXES.md': FEEDBACK}
    controls = (repo / 'CONTROLS.md').read_text(encoding='utf-8')
    controls = controls[controls.index('# Magnet Spike controls'):]
    controls = re.sub(r'^# Magnet Spike controls[^\n]*', '# Magnet Spike controls — ' + VERSION, controls, count=1)
    controls = controls.replace('Names have an **MS** prefix.', 'Most names have an **MS** prefix; the 13 corrected names instead end in **Magnet Spike** (see [NAME_CHANGES.md](NAME_CHANGES.md)).')
    controls = controls.replace('This variant uses the native pink Insect Glaive cursor.', 'Aiming keeps the normal third-person camera and uses the native pink Insect Glaive cursor.')
    start = controls.index('## Validation scope')
    controls = controls[:start] + '''## Restored opening animations

The late Double Slash **X+A** follow-up now completes instead of stalling.
Three other attacks play restored lead-ins, delaying attack onset roughly
0.75–0.85 s relative to alpha.3. Existing input windows, damage values and end
recovery durations are unchanged. See [MOTION_FIXES.md](MOTION_FIXES.md).

## Validation scope

Fresh merged-build tests cover both forms' camera/cursor, pin shots and
attraction attacks, ordinary inputs into the previously stalled follow-up,
and all four restored motion timelines. The wider controls guide also reflects
historical tests; not every branch or all 160 entries was rerun on this build.
Connected multiplayer and a new full hunt remain untested. See
[COMPATIBILITY.md](COMPATIBILITY.md) and release-validation.json.
'''
    docs['CONTROLS.md'] = controls
    install = (repo / 'INSTALL.md').read_text(encoding='utf-8')
    install = install.replace('v0.1.0-alpha.3-glaive-aim', VERSION)
    install = install.replace('Craft an **MS** weapon using its listed materials.', 'Craft a Magnet Spike using its listed materials (most names have an **MS** prefix).')
    install = install.replace('Alpha.3 includes the cumulative feedback fixes described in', 'Alpha.5 includes the cumulative feedback fixes described in')
    install = install.replace('needed when updating from alpha.1.', 'needed when updating from an earlier Magnet Spike Recomp alpha.')
    install = install[:install.index('Alpha.3 adds the sprinting-roll')].rstrip() + '''

This combined release includes the 13 weapon-name corrections, Glaive-style
camera/cursor and all four alpha.4 motion-length corrections. The reproduced
Double Slash follow-up stall is fixed; three restored lead-ins make their
attacks start later. Read [RELEASE_NOTES.md](RELEASE_NOTES.md) before updating.
'''
    docs['INSTALL.md'] = install
    building = (repo / 'BUILDING.md').read_text(encoding='utf-8')
    building = building[:building.index('For this source branch, test_aim.py')]
    building += '''## Combined alpha.5 source

The production merge is exactly seven files relative to original alpha.3:
porting/module/smithy.c (names), ms.h/ms_act.c/ms_class.c in the pinned weapon's
module (aim), and msmot.py/msbuild.py/msfx.py in its tools (motion lengths).
They match their respective completed release sources exactly. No stall
watchdog or additional runtime mechanics were introduced.

Normal build_module.py consumes the included name and aim code. Asset generation
uses the included corrected converters, including weapon hand-holder and effect
timing lengths. The frame-wait guard rejects motions too short for their waits.
The published binary was linked in an isolated workspace, then supplied with
the exact two accepted alpha.4 motion archives; all other 52 RomFS files match
original alpha.3. Independent in-memory builds reproduced those motion lists
from the included converter source.

test_aim.py delegates to test_glaive_aim.py once generated local inputs exist.
The new prepare/build/test/verify/exercise/package_combined_release.py tools and
prepare_combined_docs.py record this publication workflow. They require the
local prior release snapshots, licensed inputs, toolchain and test fixtures;
they are provenance tools, not a clean-room one-command installer. The normal
working output and the other agent's stall-fix folder were not modified.

The release contains a source-only check_source_tree.py and semantic validation
receipts. Game inputs, generated tables, converted assets, saves, captures and
runtime executables remain excluded from the source ZIP. See the matching
release-manifest.json attached to the release for every source and payload hash.
'''
    docs['BUILDING.md'] = building
    docs['FREEZE_DIAGNOSTICS.md'] = '''# Freeze status for alpha.5

The reproduced action-153 stall in Double Slash's late X+A follow-up is fixed
by restoring its motion length, without adding a runtime watchdog. See
[MOTION_FIXES.md](MOTION_FIXES.md) and release-validation.json. Ordinary input
tests on the combined build entered and completed the follow-up twice.

The user video lacks a matching game log, so it is not established that it
shows this exact path. Other freeze causes and the parry report remain
unconfirmed. Extra freeze tracing is disabled in this release. A report should
include the mod/runtime versions, hunting style, input sequence and game log
when available.
'''
    docs['NAME_CHANGES.md'] = (repo / 'NAME_CHANGES.md').read_text(encoding='utf-8')
    for name, content in docs.items():
        for dest in (repo / name, repo / 'porting/release-docs' / name):
            dest.write_text(content, encoding='utf-8')
    # One current guide instead of the obsolete disposable-hunter instructions.
    (repo / 'porting/CONTROLS.md').write_text(controls, encoding='utf-8')
    print('Updated combined alpha.5 documentation:', len(docs), 'documents and mirrors')


if __name__ == '__main__': main()
