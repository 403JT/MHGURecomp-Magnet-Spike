"""Build the isolated aim-only alpha.3 branch; never install or publish it."""
import json
import shutil
import sys
import build_module as build
from feedback_session import files
from prepare_glaive_aim_build import STAGE, BASE


def configure():
    if not (STAGE / 'baseline.json').is_file(): raise RuntimeError('Prepare the isolated branch first')
    out = STAGE / 'output'
    out.mkdir(exist_ok=True)
    (STAGE / 'reports').mkdir(exist_ok=True)
    for rel in ('balance-policy.json', 'reports/smithy-model-catalog.json'):
        shutil.copyfile(build.HERE / rel, STAGE / rel)
    shutil.copyfile(build.OUT / 'ms_sound_data.inc', out / 'ms_sound_data.inc')
    # Generators read the shared immutable game inputs, but all generated
    # headers/status reports go to this branch's output directory.
    import build_hitstats, build_cancel_windows, build_smithy_tree, build_balance
    for module in (build_hitstats, build_cancel_windows, build_smithy_tree, build_balance): module.HERE = STAGE
    build_hitstats.OUT = out
    build.MS = STAGE / 'weapon'
    build.MOD = STAGE / 'module'
    build.OUT = out
    return out


def main():
    current = build.HERE / 'output/magnet-spike-experimental'
    before = files(current)
    out = configure()
    build.main([])
    payload = files(out / 'magnet-spike-experimental')
    baseline = json.loads((STAGE / 'baseline.json').read_text(encoding='utf-8'))
    assert payload.keys() == baseline['base_payload'].keys()
    assert all(payload[n] == h for n, h in baseline['base_payload'].items() if n.startswith('romfs/'))
    assert files(current) == before
    source_changes = [n for n, h in baseline['source_files_before'].items()
                      if files(STAGE / 'weapon/module')[n] != h]
    assert sorted(source_changes) == ['ms.h', 'ms_act.c', 'ms_class.c']
    assert files(STAGE / 'module') == baseline['local_module_before']
    status = json.loads((out / 'module-status.json').read_text(encoding='utf-8'))
    assert status['hooks'] == 32 and status['patch_records'] == 106
    assert 'MS_FREEZE_DIAGNOSTICS' not in status['defines']
    proof = {'payload_files': payload, 'base_version': 'v0.1.0-alpha.3',
             'changed_production_sources': source_changes, 'normal_output_unchanged': True,
             'weapon_module_sources': files(STAGE / 'weapon/module'),
             'local_module_sources': files(STAGE / 'module'),
             'all_54_assets_unchanged': True, 'hooks': status['hooks'], 'patch_records': status['patch_records'],
             'name_fix_included': False, 'stall_fix_included': False, 'installed': False, 'uploaded': False}
    (STAGE / 'build-validation.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print('Isolated Glaive-aim build passed scope and payload checks:', out)


if __name__ == '__main__': main()
