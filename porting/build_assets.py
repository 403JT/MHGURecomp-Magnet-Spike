"""Build an isolated, single-model experimental asset set. Does not install it."""
import os
import argparse
import json
import shutil
import sys
from audit_inputs import audit
from prepare_frontier import CONVERTER, HERE, OUT, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--native-reticle', action='store_true', help='Experimental build with GU scope art; full MHF reticle remains incomplete')
    args = parser.parse_args()
    audit()
    # The converter reads only the spans checked by audit_inputs. Preserve the
    # exact decoded prefix: no missing tail bytes are invented or appended.
    shutil.copyfile(OUT / "zz/mhfdat.dec.prefix.bin", OUT / "zz/mhfdat.dec.bin")
    os.environ["GU_ROMFS"] = str(ROOT / "MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs")
    os.environ["GU_EXEFS"] = str(ROOT / "MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs")
    os.environ["GU_CODE"] = str(HERE / "work/gu_main")
    sys.path.insert(0, str(CONVERTER / "tools"))
    import nso
    flat, _, _ = nso.flat((ROOT / "MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main").read_bytes())
    code_dir = HERE / "work/gu_main"
    code_dir.mkdir(parents=True, exist_ok=True)
    (code_dir / "mem.bin").write_bytes(flat)
    shader_dir = CONVERTER / "dump/gu"
    shader_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs/nativeNX/system/app_shader/AppShaderPackage.mfx",
                    shader_dir / "AppShaderPackage.mfx")
    sys.path.insert(0, str(CONVERTER / "weapons/magnet_spike/tools"))
    import msbuild
    msbuild.MODELS.clear()
    msbuild.MODELS[1] = "wk400"
    msbuild.main(build_reticle=not args.native_reticle)
    (HERE / 'asset-status.json').write_text(json.dumps({
        'status': 'experimental', 'single_weapon_model': 'wk400', 'moveset_actions': 160,
        'reticle': 'GU native' if args.native_reticle else 'MHF converted',
        'runtime_verified': False, 'full_port_complete': False}, indent=2) + '\n', encoding='utf-8')


if __name__ == "__main__":
    main()
