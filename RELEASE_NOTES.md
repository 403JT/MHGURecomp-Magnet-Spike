# Magnet Spike v0.1.0-alpha.2 — feedback fixes

Cumulative bug-fix alpha for **MHGU 1.4.0 English**, using the normal mod loader
in **MHGURecomp 0.18.0 on Windows x64**.

## Fixes

- Preserve active hunters' weapon state when player objects are replaced.
  The previous state-pool fallback could reset another hunter's attack latches,
  repeatedly arming hits during one animation and stalling combo recovery.
- Advance remote hunters' recovery clocks and pending weapon tasks. GU skips
  their input callback, which previously left recovery, fired pins and marker
  effects without updates. Local updates still run once.
- Stop pending Shock pulses and owned hitboxes after an attack is interrupted
  or replaced. A collision check also rejects cancelled hits before the next
  update. Uninterrupted Magnetic Shock retains all four pulses.
- Fix a reproduced remote-update cause of pin glows remaining detached from
  the monster. Marker tracking was checked through movement, rotation and
  native effect expiry/replacement.
- Suppress the conflicting quick-message shortcut for the local Magnet Spike
  hunter in an online quest, while preserving other weapon classes and inputs.

Includes all alpha.1 smithy content, models, sounds, damage tuning, finisher
recovery and the crafted-weapon sharpness fix. This update preserves weapon
IDs, recipes, stats, combo links, guard windows, gauge costs, scope selection
and attraction physics.

## Install or update

1. Close MHGURecomp and back up your save folder.
2. Download **Magnet-Spike-v0.1.0-alpha.2.zip**.
3. Move the previous Magnet-Spike folder out of `mods`, then copy in the new
   **Magnet-Spike** folder. Keep only one copy enabled and restart.
4. Continue using existing MS weapons or craft one in the smithy's Magnet Spike
   category on the third page. No recrafting or save editing is needed.

The mod uses the standard loader; no custom game executable or supplied save
is required. Removing the mod from a save containing MS gear remains unsupported;
restore a pre-mod save backup when removing it.

[Installation](https://github.com/403JT/MHGURecomp-Magnet-Spike/blob/v0.1.0-alpha.2/INSTALL.md) ·
[Controls](https://github.com/403JT/MHGURecomp-Magnet-Spike/blob/v0.1.0-alpha.2/CONTROLS.md) ·
[Compatibility](https://github.com/403JT/MHGURecomp-Magnet-Spike/blob/v0.1.0-alpha.2/COMPATIBILITY.md)

## Validation and remaining reports

All **52 cumulative validation gates** passed. Regression suites include 61
cancellation checks, 190 marker/task checks, state ownership, recovery, input,
balance and native sharpness checks across all 959 upgrade levels. The exact
payload passed four native cancellation cases, five ordinary R+X/stick cases
and the remote-input recovery case on official MHGURecomp 0.18.0. All test
games were muted and used disposable save copies.

**This remains an experimental alpha.** Connected multiplayer hunts,
Diablos-specific play and broad long-hunt lifecycle coverage are unvalidated.
The specific intermittent R+X freeze was not reproduced; the parry freeze
report remains unconfirmed. The glow fix addresses one reproduced cause,
not every possible occurrence. Full Frontier parity, other platforms/languages,
mod combinations and some effect overlaps remain incomplete or unverified.

See **release-validation.json** and **FEEDBACK_FIXES.md** for the tested scope.
Report the mod/runtime version, style, form, inputs and quest/monster with any
remaining issue. Do not upload saves, game files or credentials.

## Downloads and credits

The mod ZIP, matching source ZIP, release manifest, validation details and
**SHA256SUMS.txt** form the release attachment set. Use the mod ZIP to play.

Based on Scrimas and contributors' MHGU Definitive Edition weapon port, with
local MHGURecomp integration and fixes. Code is **GPL-3.0-or-later**; original
game content belongs to Capcom and is not covered by that code license.
