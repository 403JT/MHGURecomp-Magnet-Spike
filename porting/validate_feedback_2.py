"""Audit the cumulative public feedback candidate against both checkpoints."""
import json
import re
from build_module import HERE,MS,sha
from feedback_session import files
from test_sharpness import ips_records


def main():
    payload=HERE/'output/magnet-spike-experimental'
    current=files(payload)
    old=files(HERE/'backups/before-feedback-1/public-payload')
    previous=files(HERE/'backups/before-feedback-2/candidate-payload')
    paths={
        'state_pool':'reports/feedback-state-pool-regression.json',
        'repeat_hits':'reports/feedback-repeat-hit-regression.json',
        'recovery':'reports/feedback-recovery-regression.json',
        'quick_message':'reports/feedback-quick-message-regression.json',
        'damage':'reports/damage-feedback-regression.json',
        'marker':'reports/marker-feedback-regression.json',
        'aim':'reports/aim-regression.json',
        'sharpness':'reports/sharpness-functional-regression.json',
        'balance':'reports/balance-regression.json',
        'combo_recovery':'reports/combo-recovery-regression.json',
        'native_cancellation':'runs/feedback-interruption-fixed-2/feedback-native.json',
        'native_double_slash':'runs/feedback-double-slash-fixed-2/feedback-native.json',
        'native_recovery':'runs/feedback-remote-recovery-fixed-3/feedback-native.json',
        'native_marker_remote':'runs/feedback-marker-remote-fixed-2/feedback-native.json',
        'native_marker_local':'runs/feedback-marker-local-fixed-1/feedback-native.json',
        'old_cancellation':'runs/feedback-interruption-baseline-2/feedback-native.json',
        'old_marker':'runs/feedback-marker-remote-baseline-1/feedback-native.json'}
    evidence={k:json.loads((HERE/v).read_text(encoding='utf-8')) for k,v in paths.items()}
    checks={k+'_passes':v['all_passed'] for k,v in evidence.items() if not k.startswith('old_')}
    checks['same_56_payload_paths']=current.keys()==old.keys()==previous.keys() and len(current)==56
    checks['54_assets_preserved_since_public_release']=all(current[p]==old[p]==previous[p] for p in current if p.startswith('romfs/')) and sum(p.startswith('romfs/') for p in current)==54
    public_ips=ips_records(next((HERE/'backups/before-feedback-1/public-payload/exefs').glob('*.ips')))
    prev_ips=ips_records(next((HERE/'backups/before-feedback-2/candidate-payload/exefs').glob('*.ips')))
    ips=ips_records(next((payload/'exefs').glob('*.ips')))
    checks['two_added_hooks_since_public']=ips.keys()-public_ips.keys()=={0x65f920,0x169328} and not public_ips.keys()-ips.keys()
    checks['one_added_hook_since_candidate_1']=ips.keys()-prev_ips.keys()=={0x169328} and not prev_ips.keys()-ips.keys()
    checks['sharpness_patch_preserved']=ips[0xdb91c]==public_ips[0xdb91c]
    checks['recovery_durations_preserved']=sha(MS/'module/ms_recovery.h')==sha(HERE/'backups/before-feedback-2/module/ms_recovery.h')
    checks['balance_policy_preserved']=sha(HERE/'balance-policy.json')==sha(HERE/'backups/before-feedback-1/balance-policy.json')
    checks['command_converter_preserved']=sha(MS/'tools/msbuild.py')==sha(HERE/'backups/before-feedback-1/tools/msbuild.py')
    checks['other_weapon_sources_preserved']=all(sha(p)==sha(HERE/'backups/before-feedback-2/module'/p.name) for p in (MS/'module').glob('*') if p.is_file() and p.name not in ('ms.h','ms_act.c'))
    checks['other_local_sources_preserved']=all(sha(p)==sha(HERE/'backups/before-feedback-2/local-module'/p.name) for p in (HERE/'module').glob('*') if p.is_file() and p.name!='feedback.c')
    header=(MS/'module/ms.h').read_text(encoding='utf-8')
    header=header.replace('    const uint8_t *armed_resource[2]; /* identity of our native slot after arming */\n    uint32_t armed_shape[2];\n','')
    header=header.replace('int ms_attack_matches(uint8_t *p,const struct ms_state *s,unsigned slot);\n','')
    checks['header_only_adds_attack_identity']=header==(HERE/'backups/before-feedback-2/module/ms.h').read_text(encoding='utf-8')
    before=(HERE/'backups/before-feedback-2/module/ms_act.c').read_text(encoding='utf-8')
    after=(MS/'module/ms_act.c').read_text(encoding='utf-8')
    for name in ('marker','shot_step','marker_shot','fx_follow','att_start','attraction','pin_start','pin_tick','charge_tick','aim_look','aim_frame'):
        pattern=r'^static [^\n]*\b'+name+r'\([^;]*?\n\{.*?^\}'
        a,b=[re.search(pattern,t,re.M|re.S) for t in (before,after)]
        checks[name+'_implementation_preserved']=a is not None and b is not None and a.group()==b.group()
    for k,v in evidence.items():
        if k.startswith('native_'):
            checks[k+'_exact_final_payload']=v['payload_files']==current and v['tested_payload_unchanged']
            checks[k+'_clean_muted_exit_safe_saves']=v['muted'] and v['source_saves_unchanged'] and v['exit_code']==0 and not v['failure'] and not v['fatal']
    checks['old_live_cancelled_hitboxes_reproduced']=not evidence['old_cancellation']['all_passed'] and all(not c['no_live_attack_slots'] for c in evidence['old_cancellation']['cases'])
    checks['old_detached_remote_marker_reproduced']=not evidence['old_marker']['all_passed'] and evidence['old_marker']['cases'][0]['effect_error_cm']>50
    for k in ('old_cancellation','old_marker'):
        v=evidence[k]
        checks[k+'_checkpoint_payload_and_safe_exit']=v['payload_files']==previous and v['tested_payload_unchanged'] and v['source_saves_unchanged'] and v['muted'] and v['exit_code']==0 and not v['failure'] and not v['fatal']
    checks['no_temporary_marker_tracing']='marker_trace' not in (MS/'module/ms_act.c').read_text(encoding='utf-8')
    report={'candidate':'public-feedback-2','target':'recomp','checks':checks,'all_passed':all(checks.values()),
        'payload_files':current,'evidence':{k:{'path':v,'sha256':sha(HERE/v)} for k,v in paths.items()},
        'connected_multiplayer_tested':False,'release_ready':False,'published':False,
        'remaining_reports':['Connected multiplayer pin firing, marker tracking, attraction and interrupted attacks need a real hunt retest',
            'The specific intermittent R+X freeze remains unconfirmed','Parry deferred by user; scope and attraction physics unchanged'],
        'excluded_diagnostics':{'feedback-marker-remote-fixed-1':'The first sample tracked correctly; later samples inspected an expired handle instead of the replacement. Superseded by fixed-2.',
            'feedback-marker-diablos-1':'Fixture did not leave camp; not a weapon failure',
            'feedback-marker-diablos-fixed-1':'Fixture did not leave camp; not a weapon failure',
            'feedback-marker-diablos-fixed-2':'Fixture reached a blocked camp edge; not a weapon failure',
            'feedback-marker-diablos-fixed-3':'Sheathed running also reached the blocked camp edge. Diablos-specific play is not validated.'}}
    (HERE/'reports/feedback-2-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'failed':failed,'all_passed':report['all_passed'],'release_ready':False}))
    assert report['all_passed'],failed


if __name__=='__main__':main()
