"""Bind the single-mask fix to native and source/asset-preservation evidence."""
import json
from prepare_frontier import HERE,ROOT,sha
from hunt_session import files


def main():
    paths={'ARM':'reports/sharpness-regression.json','tree':'reports/smithy-tree-regression.json',
        'damage':'reports/balance-regression.json',
        'whetstone':'runs/sharpness-official-max-3/sharpness-native.json',
        'red_case':'runs/sharpness-official-red-case-1/sharpness-native.json',
        'crafted':'runs/sharpness-official-crafted-1/sharpness-native.json'}
    d={k:json.loads((HERE/v).read_text(encoding='utf-8')) for k,v in paths.items()}
    baseline=json.loads((HERE/'backups/before-sharpness-1/baseline.json').read_text())
    prior=json.loads((HERE/'installed-build.json').read_text())
    candidate=files(HERE/'output/magnet-spike-experimental')
    saved={p.name:sha(p) for p in (HERE/'test-profile/save/save_0').glob('system*')}
    runs=[d[k] for k in ('whetstone','red_case','crafted')]
    checks={
        'all_959_levels_and_native_restoration_pass':d['ARM']['all_passed'] and d['ARM']['levels_checked']==959,
        'only_one_checked_mask_changes':all(d['ARM']['checks'].values()),
        'original_tree_and_damage_policy_pass':d['tree']['all_passed'] and d['damage']['all_passed'],
        'official_runtime_all_cases_pass':all(x['all_passed'] and all(x['checks'].values()) for x in runs),
        'same_candidate_in_every_native_run':all(x['mod_files']==candidate for x in runs) and d['ARM']['mod_files']==candidate,
        'ordinary_whetstone_restores_after_native_collision':d['whetstone']['native_loss_and_recovery']['before']['current']<400
            and d['whetstone']['native_loss_and_recovery']['after']['current']==400,
        'red_regression_family_now_starts_blue':d['red_case']['fixture']['weapon_id']==4 and
            d['red_case']['samples']['quest-start']=={'current':300,'maximum':300,'colour':4},
        'previously_crafted_weapon_loads_without_recrafting':not d['crafted']['fixture']['equipped_record_changed']
            and d['crafted']['fixture']['weapon_id']==104 and d['crafted']['fixture']['level']==2
            and d['crafted']['samples']['quest-start']=={'current':400,'maximum':400,'colour':5},
        'all_games_muted':all(x['output_muted'] for x in runs),
        'source_saves_unchanged':saved==baseline['save_hashes'],
        'installed_baseline_preserved':prior['revision']=='recovery-1' and files(HERE/'test-profile/mods/magnet-spike-experimental')==baseline['installed_files']==prior['files'],
        'runtime_unchanged':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')=='d8cb5f527abba7ab8a92ba70f8d45fe5d9219b518409bf6d9afbb034c4af7fce',
        'game_1_4_0_unchanged':sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')=='b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef'}
    report={'revision':'sharpness-1','all_passed':all(checks.values()),'checks':checks,
        'mod_files':candidate,'previous_mod_files':prior['files'],'source_save_hashes':saved,
        'evidence':{k:{'path':v,'sha256':sha(HERE/v)} for k,v in paths.items()},
        'runtime_sha256':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe'),
        'game_main_sha256':sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main'),
        'limits':['Focused sharpness tests; no new unrestricted hunt or balance claim.',
            'Item driver attempts 1/2 retained: No Item was selected, so sharpening was not exercised. Attempt3 uses the normal mouse-wheel item selector.']}
    (HERE/'reports/sharpness-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Sharpness validation:',sum(checks.values()),'/',len(checks))
    assert report['all_passed'],checks


if __name__=='__main__':main()
