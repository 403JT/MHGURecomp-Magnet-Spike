# Magnet Spike v0.1.0-alpha.1

First public alpha, based on `recovery-1` with the validated `sharpness-1` fix.

- Adds Magnet Spike as a separate weapon category with Cutting and Impact forms.
- Adds 136 families / 959 levels to the smithy, using Great Sword crafting trees.
- Includes forty Frontier models and converted weapon sounds.
- Uses tuned damage values and 0.30–0.50 seconds of added finisher recovery.
- Preserves the original fourteen weapon classes and Great Sword crafting tree.
- Fixes a native equipment-type check that capped crafted Magnet Spikes at 150
  sharpness points. Weapons now use the matching Great Sword's actual sharpness
  capacity and colour. Existing crafted gear benefits without recrafting.

The sharpness fix passed all 959 levels, native Sharpness +1/+2 calculations,
and native restoration checks. Muted official MHGURecomp 0.18.0 tests verified
an existing crafted weapon at 400/white, another affected family at 300/blue,
and ordinary Whetstone restoration after a real hit. The weapon module and
assets are unchanged; one additional checked executable patch fixes the getter.

Install through MHGURecomp's normal `mods` folder. Craft an MS weapon at the
smithy; no bundled save or save editing is required. **Back up your saves first.**

Scope: MHGU 1.4.0, English, Windows x64, single-player. Consult the compatibility
manifest for the tested MHGURecomp release. This is a prerelease, not complete
Frontier parity. Multiplayer, long-hunt lifecycle cases and some effect overlaps
remain unverified or incomplete. See the README and installation/removal guide.

Provide the source ZIP alongside the mod ZIP. The source license is GPL-3.0-or-later;
original game content is not covered by that code license.
