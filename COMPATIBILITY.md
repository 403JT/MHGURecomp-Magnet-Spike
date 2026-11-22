# Compatibility

- **Game:** Monster Hunter Generations Ultimate 1.4.0, title
  `0100770008DD8000`, executable build ID `FB08F1D20FD1204FE7070672777F869B`.
- **Language:** English.
- **Initial platform:** Windows x64.
- **Play mode:** Single-player. Multiplayer is not validated.
- **Tested public runtime:** official **MHGURecomp 0.18.0 for Windows x64**.
  Its built-in mod loader passed an equipped-weapon combo/recovery test and a
  clean-save town load with no preinjected Magnet Spike equipment. Both tests
  were muted and used disposable save copies. See `release-validation.json`.

The mod uses the normal `mods/<folder>/exefs` and `romfs` loader. It does not
require a modified MHGURecomp executable or a mandatory external launcher.
Future/older MHGURecomp releases and other operating systems are not guaranteed.

Only one code mod is covered by this alpha's tests. In particular, multiple
mods supplying `subsdk1` do not combine automatically. Executable-patch and
weapon-class allocation conflicts require explicit integration.
