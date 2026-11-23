"""Bind public feedback regressions to the exact local candidate payload."""
import json
from build_module import HERE,MS,sha
from feedback_session import files
from test_sharpness import ips_records


def main():
    payload=HERE/'output/magnet-spike-experimental'
    current=files(payload);baseline=files(HERE/'backups/before-feedback-1/public-payload')
    changed=sorted(p for p in current if current[p]!=baseline.get(p))
    paths={
        'state_pool':'reports/feedback-state-pool-regression.json',
        'repeat_hits':'reports/feedback-repeat-hit-regression.json',
        'recovery':'reports/feedback-recovery-regression.json',
        'quick_message':'reports/feedback-quick-message-regression.json',
        'sharpness':'reports/sharpness-functional-regression.json',
        'balance':'reports/balance-regression.json',
        'recovery_unchanged':'reports/combo-recovery-regression.json',
        'slash':'runs/feedback-slash-fixed-1/feedback-native.json',
        'double_slash':'runs/feedback-double-slash-fixed-1/feedback-native.json',
        'native_recovery':'runs/feedback-remote-recovery-fixed-2/feedback-native.json',
        'old_native_recovery':'runs/feedback-remote-recovery-baseline-1/feedback-native.json'}
    evidence={k:json.loads((HERE/v).read_text(encoding='utf-8')) for k,v in paths.items()}
    checks={k+'_passes':bool(evidence[k]['all_passed']) for k in paths if k!='old_native_recovery'}
    checks['payload_path_set_unchanged']=set(current)==set(baseline) and len(current)==56
    checks['all_54_assets_unchanged']=len(changed)==2 and all(p.startswith('exefs/') for p in changed)
    old_ips=ips_records(next((HERE/'backups/before-feedback-1/public-payload/exefs').glob('*.ips')))
    new_ips=ips_records(next((payload/'exefs').glob('*.ips')))
    checks['one_new_scoped_native_hook']=new_ips.keys()-old_ips.keys()=={0x65f920} and not old_ips.keys()-new_ips.keys()
    checks['sharpness_patch_unchanged']=new_ips[0xdb91c]==old_ips[0xdb91c]
    for name in ('ms.h','ms_recovery.h'):
        release=HERE/'public-release/v0.1.0-alpha.1/public/repo/porting/third_party'/MS.parents[1].name/'weapons/magnet_spike/module'/name
        checks[name+'_unchanged']=sha(MS/'module'/name)==sha(release)
    checks['balance_policy_unchanged']=sha(HERE/'balance-policy.json')==sha(HERE/'backups/before-feedback-1/balance-policy.json')
    checks['command_converter_unchanged']=sha(MS/'tools/msbuild.py')==sha(HERE/'backups/before-feedback-1/tools/msbuild.py')
    for key in ('slash','double_slash','native_recovery'):
        run=evidence[key]
        checks[key+'_same_payload']=run['payload_files']==current and run['tested_payload_unchanged']
        checks[key+'_muted_clean_exit_and_safe_saves']=run['muted'] and run['source_saves_unchanged'] and run['exit_code']==0 and not run['failure'] and not run['fatal']
    old=evidence['old_native_recovery']
    checks['old_native_freeze_reproduced']=not old['cases'][0]['exited_weapon_action'] and old['cases'][0]['after']['motion_end_flag'] and not old['fatal']
    report={'candidate':'public-feedback-1','target':'recomp','checks':checks,
        'all_passed':all(checks.values()),'payload_files':current,
        'evidence':{k:{'path':v,'sha256':sha(HERE/v)} for k,v in paths.items()},
        'connected_multiplayer_tested':False,'release_ready':False,'published':False,
        'remaining_reports':['Specific R+X softlock not reproduced; connected hunt retest needed',
                             'Parry deferred by user','Third feedback item not addressed in this candidate'],
        'sharpness_audit_note':'The historical sharpness-only package audit expects an unchanged code module and a single new IPS record. This candidate intentionally changes code and adds a scoped hook; the functional sharpness gates and independent 54-asset preservation audit are required here.'}
    (HERE/'reports/feedback-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'failed':failed,'all_passed':report['all_passed'],
                      'connected_multiplayer_tested':False,'release_ready':False}))
    assert report['all_passed'],failed


if __name__=='__main__':main()
