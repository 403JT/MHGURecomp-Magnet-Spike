# Cumulative feedback fixes

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
