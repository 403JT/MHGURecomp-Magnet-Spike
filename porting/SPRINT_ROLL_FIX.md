# Sprinting roll fix — public MHGURecomp build

This release includes the cumulative alpha.2 fixes and the correction for
being unable to roll while sprinting with the weapon sheathed.

Hold **R + movement**, then press **B** to roll while sheathed. The old input
translator treated R as a drawn-weapon modifier even when it was the sprint
button, clearing GU's native evade inputs. The suppression is now restricted
to when the weapon is drawn. Native stamina and evade selection still apply.

Drawn-weapon R combinations, aiming, combo links, damage values, recovery,
gauge costs, crafting, sounds, models and attraction physics are unchanged.
All earlier alpha.2 fixes are included. Use only one Magnet Spike mod folder.

## Verification

The public alpha.2 build reproduced blocked sprint rolls in two directions;
drawn and sheathed walking rolls were working. The corrected build passes
all four ordinary-input scenarios on official MHGURecomp 0.18.0, muted and
using disposable save copies. Compiled ARM tests execute the full input
translator and native R-role getter across both control options, gauge values
and forms, preserving drawn modifier behavior. Earlier cancellation, marker,
recovery, aim, input, balance and sharpness regressions also pass.

This correction is included in v0.1.0-alpha.3. Alpha.2's
remaining multiplayer, intermittent freeze and full-hunt testing limits apply.
The package contains no supplied save or game executable.

## Install

Close the game and back up your save. Move the existing Magnet-Spike folder
out of `mods`, then extract this package's **Magnet-Spike** folder into `mods`.
Keep one copy enabled and restart. Existing weapons need no recrafting or
save editing. Keep the alpha.2 ZIP to roll back.
