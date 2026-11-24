# Magnet Spike for MHGURecomp

Bring Frontier's **Magnet Spike** to Monster Hunter Generations Ultimate as an additional craftable weapon category. Switch between Cutting and Impact forms, mark monsters, move with magnetic attraction and repulsion, and build toward Magnetise and magnetic pin finishers.

All fourteen original weapon classes and the original Great Sword tree remain available. This is an experimental port with GU adaptations; full Frontier parity is still in progress.

**Current public package: Beta 4.** This README describes the MHGURecomp release. Its matching source and complete documentation are included with the release downloads.

[Download Beta 4](https://github.com/403JT/MHGURecomp-Magnet-Spike/releases/tag/v0.1.3-beta.4) · [Watch the trailer](https://youtu.be/p3nbBdvC3DU?si=ApiMDIyX8Fa5GNaP) · [Discord — bugs and suggestions](https://discord.gg/XRjyKzkPsX)

## Download

| File | Use |
| --- | --- |
| [Magnet-Spike-v0.1.0-beta.4.zip](https://github.com/403JT/MHGURecomp-Magnet-Spike/releases/download/v0.1.3-beta.4/Magnet-Spike-v0.1.0-beta.4.zip) | Play the mod with MHGURecomp. |
| [Magnet-Spike-v0.1.0-beta.4-source.zip](https://github.com/403JT/MHGURecomp-Magnet-Spike/releases/download/v0.1.3-beta.4/Magnet-Spike-v0.1.0-beta.4-source.zip) | Matching Beta 4 source for developers. |
| `SHA256SUMS.txt`, `release-manifest.json`, `release-validation.json` | Download checksums, file inventory and recorded validation, attached to the same release. |

The release page uses tag `v0.1.3-beta.4`; the uploaded package filenames use `v0.1.0-beta.4`. The links above select the intended Beta 4 files. Separately labelled emulator assets are experimental builds with their own versions.

## Features

### A separate smithy weapon tree

- **Magnet Spike category** on the smithy's third weapon-category page. Craft and upgrade through the normal equipment menus.
- **136 weapon families, 959 upgrade levels and 95 forge recipes** based on the Great Sword tree. Materials, quantities, prices, unlock requirements and upgrade branches follow that progression.
- **40 Frontier weapon models**, assigned across related families. Upgrades within a family retain their model until branching to a different appearance.
- Existing Great Swords retain their own equipment records, recipes and names.
- The 13 requested Great Sword-related display names now use **Magnet Spike**, including Avidya, Tigrex, Alatreon and Elderfrost. Most other names retain their **MS** prefix.
- Correct sharpness capacity for crafted weapons, normal Whetstone sharpening and Sharpness +1/+2 support.
- Tuned attack damage: current raw attack uses 95% of the matching Great Sword baseline, with separate move-damage tuning. Balance remains subject to further testing.
- The public release uses normal crafting progression; it does not inject equipment into hunter saves. Existing Magnet Spikes need no recrafting when updating.

### Cutting and Impact combat

- **Cutting form:** vertical and horizontal chains, Upslash, Finishing Slash, Magnetic Double Slash, Retreat Slash and aerial downslash routes.
- **Impact form:** swipes, horizontal chains, Suplex, Magnetic Double Swipe and Triple Strike with charged, uncharged and overcharge releases.
- Form switching from neutral and transform attacks during supported combo windows.
- Magnetic Assault leaps, magnetic evasions, evasion follow-ups and Impact Magnetic Shock attacks.
- Timed guards/counters and their follow-up routes, including drawing directly into Impact Guard.
- Ordinary drawing, sheathing, rolls, sprint rolls and moving/post-roll attacks adapted to GU.
- Added commitment at selected combo endings: **0.30–0.50 seconds** of recovery before another action can take over. Valid combo links retain their own input windows.
- Four restored animation lengths, including the late Double Slash X+A follow-up that previously stalled. Three restored lead-ins make their attacks begin roughly **0.75–0.85 seconds later** than the earlier alpha build; damage was not retuned for those longer openings.

### Marking and magnetic movement

- Fire a magnetic marker at a large monster, then use **attraction** to approach or **repulsion** to move away.
- Attraction follow-up aerial attacks in both forms, with an approach-cancel input.
- **Insect Glaive-style aiming:** normal third-person camera, native pink centre cursor and the game's normal right-stick camera settings.
- A separate **five-bar movement gauge**. Magnetic movement and many R attacks consume gauge; changing form and firing a marker do not.
- **Magnetic Pin:** take the double-attack follow-up into a monster hold, tap X/A during the restraint and build toward the form's Pin Finisher.
- **Magnetise:** charge Cutting and Impact independently by landing attacks, then activate the form's boost and supported extra hits for approximately 80 seconds, followed by a cooldown.

### Models, sound and interface

- Frontier weapon models and **40 converted Frontier sound waves**, including swings and magnetic effects.
- Beta 3's 48 kHz audio restoration is retained: corrected decoding overshoots, cleaned sound tails and improved DSP-ADPCM encoding.
- A custom weapon icon, HUD and gauge presentation.
- Runtime weapon-icon painting for all seven game-language icon atlases: English, Spanish, French, German, Italian, Simplified Chinese and Traditional Chinese.
- Icon scaling for supported RGBA8 HD UI atlas layouts, with populated icon cells preserved. Third-party HD packs have not been tested live in game; compressed or differently arranged atlases are not covered by that support.

### Cumulative fixes in Beta 4

- Duplicate floating marker effects: keep tracked effects alive correctly and defer cleanup until newly created effects can be stopped.
- Marker-shot gun model: correct the looping emitter so the hand piece despawns after firing.
- Effects after area changes: stamp new effects with the hunter's current area so shots, markers and particles remain visible.
- Stop pending Magnetic Shock damage and owned hitboxes when the attack is interrupted.
- Preserve active hunter weapon state and advance remote recovery/effect tasks through their appropriate update path.
- Suppress the conflicting online quick-message shortcut for the local Magnet Spike hunter. These remote-path fixes do not establish connected multiplayer support.
- Retain the sprint-roll, sheathed guard-draw, sharpness, weapon-name, aim and animation-length corrections from earlier releases.

## Essential controls

These are **Switch button labels**: **X = top face**, **A = right face**, **B = bottom face**, **Y = left face**. **R is the right shoulder; ZR is the right trigger.** Map them through MHGURecomp's input settings.

| Action | Input |
| --- | --- |
| Draw / sheathe | X while sheathed / Y while drawn, outside a combo |
| Basic attack chains | X or A; supported follow-ups also use X+A |
| Switch form | Minus from drawn neutral |
| Roll / sheathed sprint roll | B / hold R + movement, then B |
| Draw into Impact Guard | R+X+A while sheathed |
| Magnetic Double Slash / Double Swipe | R+X while drawn |
| Magnetic Assault | R+X+A from drawn neutral |
| Timed guard | Hold R, press ZR just before an incoming hit |
| Aim / shoot marker | Hold ZR without R / ZR+A |
| Attraction | ZR+X with a marker more than 14 m and less than 40 m away |
| Repulsion | ZR+B with a marker within 14 m |
| Attraction follow-up / cancel | X / B during the approach |
| Activate Magnetise | R+Minus when that form is charged |

Attraction and repulsion require stamina and one movement-gauge bar. Distances are measured to the attached marker and change as the monster moves. Magnetic Pin uses a follow-up from the double attack and needs two gauge bars across the sequence; R+X+A from neutral alone is not the complete pin route.

See the [shared move guide](CONTROLS.md) for detailed routes. The Beta 4 ZIP includes its matching `CONTROLS.md` and release-specific documentation.

## Install or update

**Target:** your own MHGU **1.4.0** game data, primarily English, on Windows MHGURecomp. The recorded Beta 4 live tests used official **MHGURecomp 0.18.0**. Other runtime versions are not established by those tests. Seven-language icon support does not imply complete translation or validation of the whole mod in every language.

1. Close MHGURecomp and back up your save folder. The default Windows location is `%APPDATA%\MHGURecomp\save\`; a custom Save folder setting takes precedence.
2. Extract `Magnet-Spike-v0.1.0-beta.4.zip`.
3. Put its **Magnet-Spike** folder in MHGURecomp's **mods** folder:

   ```text
   MHGURecomp/
     mhgurecomp.exe
     mods/
       Magnet-Spike/
         exefs/
         romfs/
         README.md
   ```

4. Enable Magnet Spike in the normal Mods settings and restart the game.
5. Visit the smithy, open the third weapon-category page and select Magnet Spike. Recipes follow normal unlock progression.

When updating, move the previous Magnet-Spike folder outside `mods`, then install the new folder. Keep only one copy enabled. The standard mod loader handles the files; no custom game executable, launcher, supplied save or save editor is required.

Other mods providing `subsdk1`, overlapping executable patches or new-weapon allocations require explicit integration. Other code-mod combinations are not certified. For removal, use a pre-mod save backup: loading a save containing Magnet Spike equipment without the mod has no validated migration path. The ZIP's `INSTALL.md` contains the full update and rollback guidance.

### Why is Beta 4 smaller?

Weapon icons are now painted at runtime into the loaded language/UI atlas. This allows the large bundled English `resident_eng.arc` to be removed, saving about **1.74 MB** in the download. The weapon models, sound banks and motion archives are retained. Beta 4's hovering-gun asset correction changes one byte within one effect; the other 383 members of that archive match Beta 3.

## Testing and remaining limits

Recorded Beta 4 testing includes compiled marker-cleanup, seven-language icon and gun-effect regressions; three matching isolated builds; official 0.18.0 Spanish/English icon and firing checks; and controlled monster/area-transition tests for marker survival, cleanup, attraction and repulsion. The broad script sweep reported **34/41 successful scripts**, with the same seven unsuccessful results as Beta 3 and no additional failures. This is not an entirely passing suite.

Connected multiplayer, split screen, a new full hunt on this build, live third-party HD UI packs and other Recomp versions remain unverified. Not every input branch or hunting-style combination has been replayed on Beta 4. Other freeze causes and the intermittent parry report are not ruled out. Full Frontier parity remains in progress.

The release includes `release-validation.json` for the recorded scope and `release-manifest.json` / `SHA256SUMS.txt` for file integrity. Its detailed notes include `ISSUES_4_5_FIX.md`, `AUDIO_UPSCALE.md`, `EFFECT_AREA_FIX.md`, `NAME_CHANGES.md`, `GLAIVE_AIM.md` and `MOTION_FIXES.md`.

## Report a problem

[Open a GitHub issue](https://github.com/403JT/MHGURecomp-Magnet-Spike/issues) or use [Discord](https://discord.gg/XRjyKzkPsX). Include the mod filename/version, MHGURecomp version, operating system, quest/monster, weapon form, hunting style and input sequence, plus the expected and actual result. A short clip and a reviewed game log help reproduce a problem. Keep saves, game files, keys and credentials out of reports.

## Source and credits

**For Beta 4 development, use the matching source ZIP linked above.** The current `main` code snapshot predates Beta 4; this README describes the released package. The source ZIP contains the corresponding code, converters, build tools and documentation, with game assets, audio, executables, saves and test captures excluded. Existing repository guides such as [BUILDING.md](BUILDING.md) describe the development layout.

The weapon code and converters derive from Scrimas's [MHGU Definitive Edition](https://github.com/Scrimas/MHGU-Definitive-Edition), pinned to `209959bcf08f9d54be25b92ba8b6346d70cd57d8`, with local porting changes. Code is **GPL-3.0-or-later**; see [LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

[MHGURecomp](https://github.com/morerokk/MHGURecomp) is a separate project. Monster Hunter content belongs to Capcom; the code license does not license that content. Use your own game data. Full games, Frontier clients, saves and credentials are not included in the source repository.
