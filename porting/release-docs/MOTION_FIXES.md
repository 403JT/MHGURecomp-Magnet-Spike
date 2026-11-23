# Motion-length corrections in alpha.5

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
