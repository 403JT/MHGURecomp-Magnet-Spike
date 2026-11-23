"""Link names + Glaive aim, then carry alpha.4's verified motion archives."""
import json
import shutil
import build_module as build
import build_glaive_aim as isolated
from feedback_session import files
from prepare_combined_release import STAGE, read


def main():
    baseline, inputs = read(STAGE / 'baseline.json'), read(STAGE / 'inputs.json')
    assert files(build.HERE / 'output/magnet-spike-experimental') == baseline['normal_payload']
    isolated.STAGE = STAGE
    out = isolated.configure()
    build.main([])
    payload = out / 'magnet-spike-experimental'
    before_overlay = files(payload)
    assert all(before_overlay[n] == h for n, h in baseline['base_payload'].items() if n.startswith('romfs/'))
    for rel in baseline['motion_changed_assets']:
        shutil.copyfile(STAGE / 'inputs/motions/mod/Magnet-Spike' / rel, payload / rel)
    current = files(payload)
    assert current.keys() == baseline['base_payload'].keys() and len(current) == 56
    assert all(current[n] == h for n, h in inputs['motion_payload'].items() if n.startswith('romfs/'))
    assert files(STAGE / 'weapon/module') == baseline['merged_weapon_sources']
    assert files(STAGE / 'module') == baseline['merged_local_sources']
    assert files(build.HERE / 'output/magnet-spike-experimental') == baseline['normal_payload']
    status = read(out / 'module-status.json')
    assert status['hooks'] == 32 and status['patch_records'] == 106
    assert 'MS_FREEZE_DIAGNOSTICS' not in status['defines']
    proof = {'all_passed': True, 'version': baseline['version'], 'payload_files': current,
             'sources': baseline['production_changes'], 'module_sha256': current['exefs/subsdk1'],
             'all_54_assets_exact_alpha4': True, 'hooks': 32, 'patch_records': 106,
             'name_fix_included': True, 'glaive_aim_included': True, 'motion_length_fix_included': True,
             'watchdog_included': False, 'normal_output_unchanged': True,
             'installed': False, 'uploaded': False}
    (STAGE / 'build-validation.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in proof.items() if k != 'payload_files'}))


if __name__ == '__main__': main()
