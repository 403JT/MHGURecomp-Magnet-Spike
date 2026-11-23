# Magnet Spike for MHGURecomp

An alpha port of Frontier's Magnet Spike in Monster Hunter Generations
Ultimate. Adds a separate weapon category; all fourteen original weapon classes
and the Great Sword tree remain available.

Project: https://github.com/403JT/MHGURecomp-Magnet-Spike

**Source version: v0.1.0-alpha.2 (feedback fixes).** See Releases for currently
published downloads. This is an experimental single-player mod,
not a claim of complete Frontier parity or release-quality multiplayer support.

## Download and install

Download the mod ZIP from this repository's **Releases**, then follow
[INSTALL.md](INSTALL.md). The intended installation is the normal
`MHGURecomp/mods/Magnet-Spike/` folder. No custom game executable, development
launcher, save editor or supplied hunter save is required.

The game must be **MHGU 1.4.0**, with the English game language. Runtime and
platform compatibility are recorded separately in [COMPATIBILITY.md](COMPATIBILITY.md).
MHGU 1.4.0 is the game's version, not an MHGURecomp release number.

## Trailer 
  https://youtu.be/p3nbBdvC3DU?si=ApiMDIyX8Fa5GNaP

## Included

- Cutting and Impact forms, magnetic marking/movement, charging, guard/counter,
  Magnetise and magnetic pin mechanics.
- A separate Magnet Spike smithy category on the third category page.
- 136 weapon families, 959 upgrade levels and 95 forge recipes based on the
  Great Sword tree. Materials, costs, unlocks and branches follow that tree.
- Forty Frontier weapon models, reused across related families. Upgrades within
  a family retain their model.
- Frontier weapon sounds, a custom weapon icon/HUD, and tuned damage values.
- Great Sword baseline sharpness at every upgrade level, with native sharpening
  and Sharpness +1/+2 support. The pre-release sharpness-cap bug is fixed.
- Added combo-end commitment: 0.30–0.50 seconds at selected finishers, including
  the right-face-button combo.
- Feedback fixes for interrupted attacks retaining damage, active hunter state
  being overwritten, remote recovery/tasks stalling, and the multiplayer
  quick-message/scope shortcut conflict. See [FEEDBACK_FIXES.md](FEEDBACK_FIXES.md).

Craft a weapon at the smithy. Names start with **MS**, such as **MS Petrified
Blade**. The public mod does not inject a weapon into existing or new saves.
See [CONTROLS.md](CONTROLS.md) for the buttons and move routes.

## Limits of this alpha

Single-player and English are the supported scope. Guild-style moves and shared
Hunter Arts are the current design; other styles are not separate implementations.
Connected multiplayer, other platforms/languages and combinations with other
code mods are not validated. This update fixes defects reproduced through
controlled remote-player paths; it does not establish reliable multiplayer play.
Full Frontier parity remains incomplete.

Normal combat, an area change, a save reload and focused weapon tests passed.
Long hunts, faint/camp recovery, capture and multiple-large-monster coverage remain
incomplete. Independent overlapping Magnetic Shock attacks also need further work.
Prior kill-time measurements predate the latest added recovery; they are not
measurements of this alpha's current attack cadence.

The intermittent parry and R + X freeze reports remain unconfirmed, and
Diablos-specific play has not been validated. The detached-glow fix addresses
one reproduced remote-update cause. Scope selection, attraction physics,
damage values, crafting and combo-end recovery are unchanged from alpha.1.

Back up your saves before enabling the mod. Removing it while a save contains
Magnet Spike gear is not supported by this alpha; see the removal procedure.

## Report a problem

Open an issue with the mod version, MHGURecomp version, OS, quest/monster,
weapon/form and inputs, expected result, and what happened. Attach a screenshot
or short clip if useful. Logs can contain local paths; review them before sharing.
Do not upload saves, game files, keys or credentials.

## Discord Link for Bugs and suggestions
https://discord.gg/XRjyKzkPsX
## Source and credits

The weapon code/converters derive from Scrimas's
[MHGU Definitive Edition](https://github.com/Scrimas/MHGU-Definitive-Edition),
pinned to `209959bcf08f9d54be25b92ba8b6346d70cd57d8`, with local porting changes.
Code is provided under **GPL-3.0-or-later**; see [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

[MHGURecomp](https://github.com/morerokk/MHGURecomp) is a separate project.
Monster Hunter game content belongs to Capcom; the code license does not license
that content. Full game files, client files, saves and development captures are
not included in this repository. Mod binaries belong in release attachments,
not source-control commits. See [BUILDING.md](BUILDING.md) for source layout.
