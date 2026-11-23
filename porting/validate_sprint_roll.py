"""Bind the sprinting-roll regression and native reproduction to this payload."""
import json
import re
from build_module import HERE,MS,sha
from feedback_session import files


def main():
    old_root=HERE/'backups/before-sprint-roll-1'
    current=files(HERE/'output/magnet-spike-experimental');old=files(old_root/'payload')
    paths={
        'sprint_input':'reports/sprint-roll-regression.json',
        'damage':'reports/damage-feedback-regression.json',
        'marker':'reports/marker-feedback-regression.json',
        'aim':'reports/aim-regression.json',
        'quick_message':'reports/feedback-quick-message-regression.json',
        'recovery':'reports/feedback-recovery-regression.json',
        'repeat_hits':'reports/feedback-repeat-hit-regression.json',
        'balance':'reports/balance-regression.json',
        'combo_recovery':'reports/combo-recovery-regression.json',
        'command_routes':'reports/command-route-regression.json',
        'sharpness':'reports/sharpness-functional-regression.json',
        'native_old':'runs/sprint-roll-baseline-2/feedback-native.json',
        'native_fixed':'runs/sprint-roll-fixed-1/feedback-native.json'}
    evidence={k:json.loads((HERE/v).read_text(encoding='utf-8')) for k,v in paths.items()}
    checks={k+'_passes':v['all_passed'] for k,v in evidence.items() if k!='native_old'}
    checks['same_56_payload_paths']=current.keys()==old.keys() and len(current)==56
    checks['only_module_binary_changed']=[p for p in current if current[p]!=old[p]]==['exefs/subsdk1']
    checks['baseline_matches_public_alpha2']=old==json.loads((HERE/'public-release/v0.1.0-alpha.2/ready/release-manifest.json').read_text(encoding='utf-8'))['payload_files']
    before=(old_root/'module/ms_act.c').read_text(encoding='utf-8')
    after=(MS/'module/ms_act.c').read_text(encoding='utf-8')
    restored=after.replace("    /* While sheathed, R is GU's sprint button and must keep its native evades.\n     * Only drawn Magnet Spike commands replace the common roll/sheathe inputs. */\n",'')
    restored=restored.replace('    if (ms_drawn(p) && (held & r)) {      /* R + B / Y','    if (held & r) {                     /* R + B / Y')
    checks['only_input_scope_guard_changed']=restored==before and after!=before
    checks['all_other_weapon_sources_preserved']=all(sha(p)==sha(old_root/'module'/p.name) for p in (MS/'module').iterdir() if p.is_file() and p.name!='ms_act.c')
    checks['all_local_module_sources_preserved']=all(sha(p)==sha(old_root/'local-module'/p.name) for p in (HERE/'module').iterdir() if p.is_file())
    for key,payload in (('native_old',old),('native_fixed',current)):
        run=evidence[key];log=(HERE/paths[key]).parent.joinpath('log.txt').read_text(errors='replace')
        checks[key+'_correct_payload']=run['payload_files']==payload and run['tested_payload_unchanged']
        checks[key+'_clean_muted_exit_safe_saves']=run['muted'] and run['source_saves_unchanged'] and run['exit_code']==0 and not run['failure'] and not run['fatal']
        checks[key+'_four_actual_locomotion_cases']=len(run['cases'])==4 and all(c['before']['category']==2 and c['before']['action']==(2 if c['sprint_held'] else 1 if c['weapon_sheathed'] else 0) for c in run['cases'])
        # Confirm the sprint button was still held when each evade was pressed.
        r_events=[tuple(map(int,x)) for x in re.findall(r'\[control\] R (\d+) at frame (\d+)',log)]
        b_events=list(map(int,re.findall(r'\[control\] B \d+ at frame (\d+)',log)))
        checks[key+'_two_evades_pressed_while_sprinting']=sum(any(start<=b<start+length for length,start in r_events) for b in b_events)==2
    checks['old_sprinting_failure_reproduced']=not evidence['native_old']['all_passed'] and all(c['evade_observed']==(not c['sprint_held']) for c in evidence['native_old']['cases'])
    checks['compiled_old_failure_reproduced']=evidence['sprint_input']['baseline_failing_cases']>0
    report={'revision':'sprint-roll-1','target':'recomp','checks':checks,'all_passed':all(checks.values()),
        'payload_files':current,'evidence':{k:{'path':v,'sha256':sha(HERE/v)} for k,v in paths.items()},
        'published':False,'installed':False,'game':'MHGU 1.4.0 English',
        'native_runtime':'official MHGURecomp 0.18.0 Windows x64',
        'native_scope':'Four ordinary-input movement/evade cases; two old sprint failures, four fixed passes. Muted disposable saves.',
        'compiled_scope':evidence['sprint_input']['scope'],
        'compiled_checks':len(evidence['sprint_input']['checks']),
        'connected_multiplayer_tested':False,'full_hunt_validation_complete':False,
        'excluded_diagnostics':{'sprint-roll-baseline-1':'Fixture used BUTTON 0, which this runtime interprets as an eight-frame press; superseded by baseline-2.'}}
    (HERE/'reports/sprint-roll-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'failed':failed,'all_passed':report['all_passed']}))
    assert report['all_passed'],failed


if __name__=='__main__':main()
