"""Check that a damage-only candidate preserves the installed smithy assets."""
import json
from pathlib import Path
from prepare_frontier import HERE,ROOT,sha


def files(folder):
    return {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}


def main():
    backup=HERE/'backups/before-balance-1'
    manifest=json.loads((backup/'manifest.json').read_text(encoding='utf-8'))
    expected=files(HERE/'output/magnet-spike-experimental')
    original=files(backup/'mod')
    changed=[p for p in expected if original.get(p)!=expected[p]]
    allowed={str(Path('exefs/subsdk1')),
        str(Path('exefs/FB08F1D20FD1204FE7070672777F869B.ips'))}
    saved={p.name:sha(p) for p in (HERE/'test-profile/save/save_0').glob('system*')}
    checks={
        'backup_manifest_intact':all(sha(backup/p)==v for p,v in manifest.items()),
        'same_56_file_layout':set(expected)==set(original) and len(expected)==56,
        'only_code_and_matching_patch_changed':set(changed)==allowed,
        'all_54_romfs_assets_identical':sum(p.startswith('romfs') for p in expected)==54
            and all(v==original[p] for p,v in expected.items() if p.startswith('romfs')),
        'public_executable_unchanged':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')==
            manifest[str(Path('files/MHGURecomp-master/build/mhgurecomp.exe'))],
        'public_saves_unchanged':bool(saved) and all(v==manifest[str(Path('save')/p)] for p,v in saved.items()),
    }
    report={'mod_files':expected,'checks':checks,'all_passed':all(checks.values()),
        'changed_files':changed,'save_hashes':saved,
        'scope':'Binary assets, stable file paths, public launcher and saves. Compiled ARM smithy tests separately verify every recipe/level field.'}
    (HERE/'reports/balance-preservation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Balance preservation checks:',sum(checks.values()),'/',len(checks))
    assert report['all_passed'],checks


if __name__=='__main__':main()
