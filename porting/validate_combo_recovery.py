"""Bind the recovery candidate to fresh boundary/native/preservation evidence."""
import json,re
from prepare_frontier import HERE,ROOT,sha
from hunt_session import files


def main():
    paths={'recovery':'reports/combo-recovery-regression.json','windows':'reports/cancel-window-regression.json',
        'hook':'reports/cancel-hook-regression.json','moveset':'reports/moveset-regression.json',
        'damage':'reports/balance-regression.json','preservation':'reports/combo-recovery-preservation.json',
        'native':'runs/recovery-native-3/recovery-verification.json','reference':'reports/combo-recovery-native-reference.json'}
    d={k:json.loads((HERE/v).read_text(encoding='utf-8')) for k,v in paths.items()}
    mod=files(HERE/'output/magnet-spike-experimental')
    prior=json.loads((HERE/'installed-build.json').read_text(encoding='utf-8'))
    r=json.loads((HERE/'runs/recovery-native-3/run.json').read_text(encoding='utf-8'))
    saved={p.name:sha(p) for p in (HERE/'test-profile/save/save_0').glob('system*')}
    # Saves legitimately change during ordinary play after installation. Compare
    # with this task's first untouched copy, not the older install-time saves.
    first={n:sha(HERE/'runs/recovery-baseline-right/save/save_0'/n) for n in saved}
    human=json.loads((HERE/'runs/hunt-human3/hunt-run.json').read_text(encoding='utf-8'))['source_save_hashes']
    log=(HERE/'runs/recovery-native-3/log.txt').read_text(errors='replace')
    clocks=re.findall(r'ms-recovery: command action (\d+) row \d+ delay (\d+) clock (\d+) ready (\d+)',log)
    policy={int(k):v for k,v in d['recovery']['added_frames_at_60hz'].items()}
    checks={
        'compiled_ARM_recovery_checks':d['recovery']['all_passed'] and len(d['recovery']['checks'])==441,
        'all_129_native_command_rows_verified':d['recovery']['native_transition_rows_checked']==129,
        'source_timing_and_charge_windows_pass':d['windows']['all_passed'],
        'range_hook_ABI_pass':d['hook']['all_passed'],
        'flight_pin_QTE_regressions_pass':all(d['moveset']['fixed'].values()),
        'damage_and_KO_regressions_pass':d['damage']['all_passed'],
        'damage_policy_unchanged':sha(HERE/'balance-policy.json')==sha(HERE/'backups/before-recovery-1/balance-policy.json'),
        'only_selected_finisher_tables_and_code_changed':d['preservation']['all_passed'],
        'all_non_timing_assets_preserved':d['preservation']['checks']['models_sounds_textures_and_other_assets_unchanged'],
        'native_normal_right_combo_and_all_11_finishers_pass':d['native']['all_passed'] and len(d['native']['cases'])==11,
        'native_measured_gate_clocks_match_policy':bool(clocks) and all(int(b)==policy[int(a)] and int(end)-int(start)==int(b) for a,b,start,end in clocks),
        'native_exact_candidate_files':d['native']['mod_files']==mod==r['mod_files'],
        'native_clean_exit_and_saves_unchanged':r['exit_code']==0 and not r['failure'] and not r['fatal'] and r['source_saves_unchanged'],
        'all_native_testing_muted':r['output_muted'],
        'installed_baseline_unchanged':files(HERE/'test-profile/mods/magnet-spike-experimental')==prior['files'],
        'source_saves_unchanged_since_task_start':saved==first==human,
        'runtime_unchanged':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')=='d8cb5f527abba7ab8a92ba70f8d45fe5d9219b518409bf6d9afbb034c4af7fce',
        'MHGU_1_4_0_target':sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')=='b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef',
        'native_melee_reference_sampled':all(x['roll_window_count']>0 for x in d['reference']['native_command_window_metadata'])}
    assert all(checks.values()),checks
    report={'revision':'recovery-1','checks':checks,'all_passed':True,'mod_files':mod,'previous_mod_files':prior['files'],
        'source_save_hashes':saved,'runtime_sha256':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe'),
        'game_main_sha256':sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main'),
        'balance_policy_sha256':sha(HERE/'balance-policy.json'),
        'evidence':{k:{'path':v,'sha256':sha(HERE/v)} for k,v in paths.items()},
        'added_frames_at_60hz':policy,
        'limits':['Extra18-30 frames are a GU commitment tuning choice, not exact Frontier parity.',
            'Previous balance-1 kill timings are historical after this intentional cadence change.',
            'Natural faint/capture/multi-monster cases remain deferred by the user.',
            'Earlier setup/test-driver attempts retained and excluded from the passing native gate.'],
        'failed_or_excluded_attempts':['recovery-baseline-right: draw scheduled before quest input unlocked',
            'recovery-native-1: incomplete debug-entry/recovery coverage; superseded by synchronized native3',
            'recovery-native-2: deliberately closed while improving fixture sequencing'],
        'full_port_complete':False}
    (HERE/'reports/combo-recovery-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Recovery validation:',sum(checks.values()),'/',len(checks),'checks passed.')


if __name__=='__main__':main()
