# Source layout and local inputs

The source snapshot includes the modified pinned MHGU Definitive Edition source,
the local weapon module and Python build tools. Generated game assets and tables
are intentionally excluded from source control. The binary mod ZIP contains the
locally generated mod payload; neither archive includes a complete game/client,
game executable, credentials, save or test capture.

The source follows the development layout:

```text
porting/
  module/                         local compatibility/mechanics hooks
  tests/                          ARM test fixtures
  third_party/
    MHGU-Definitive-Edition-209959bcf08f9d54be25b92ba8b6346d70cd57d8/
      module/
      tools/
      weapons/magnet_spike/
  *.py                            local build and verification tools
  balance-policy.json
```

Read the pinned upstream `CONTRIBUTING.md`, `ARCHITECTURE.md`, and Magnet Spike
notes before building. Use your own MHGU 1.4.0 ExeFS/RomFS and Frontier ZZ source
inputs. Frontier formats/extraction are documented in the upstream weapon notes.
The external ReFrontier extraction tool is not bundled or relicensed here.

The current build tools expect the same local folder layout described by
`porting/prepare_frontier.py`, `sound_env.py` and `build_module.py`: MHGU game data
under `MHGURecomp.0.14.0/Windows-MHGURecomp/data/`, the runtime/toolchain source
tree under `MHGURecomp-master/`, and extracted Frontier inputs under the pinned
converter's ignored `dump/mhf/`. These are **development paths**, not a requirement
to use MHGURecomp 0.14.0 when playing the released mod.

Required tools include Python, NumPy, Unicorn, Capstone, Pillow, soundfile,
Clang/LLD and the audio conversion dependencies documented by the source.
Locally generated input manifests/reports must be regenerated from your own
files. The historical QA scripts also depend on local run fixtures and receipts;
those private captures and saves are not part of the source release.

The build stages are input extraction/audit, base asset conversion, model
catalogue/smithy assets, sound conversion, command rebuilding and module linking.
See the respective scripts' entry points and upstream source notes. This alpha
does not claim a tested one-command clean-room source build.

`package_public_release.py` packages the historical alpha.1 build. It refuses unknown
payload files and creates a source-only repository staging tree and separate
release attachments. It does not publish anything by itself.

`package_feedback_release.py` stages alpha.2 from the tested cumulative
feedback candidate, preserving all 56 payload files and checking the matching
validation receipt. `FEEDBACK_FIXES.md` describes the changes and remaining
reports. Historical old/new regression comparisons require the locally kept
source checkpoints; they are not bundled with game inputs, saves or captures.
