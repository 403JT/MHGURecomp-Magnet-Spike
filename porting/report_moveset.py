"""Consolidate installed moveset evidence without claiming full Frontier parity."""
import argparse,hashlib,json,re
from pathlib import Path
from prepare_frontier import HERE

def read(path):return json.loads(path.read_text(encoding='utf-8'))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True)
    parser.add_argument('--audio-run',required=True)
    parser.add_argument('--action-sweep-b-run')
    parser.add_argument('--guard-run');parser.add_argument('--continuation')
    parser.add_argument('--world-run');parser.add_argument('--charge-run')
    parser.add_argument('--cancel-run');args=parser.parse_args()
    if bool(args.world_run)!=bool(args.charge_run):raise RuntimeError('World and charge evidence must be supplied together')
    installed=read(HERE/'installed-build.json')
    expected=installed['files'];digest=installed['module_sha256']
    batch=read(HERE/'reports'/(args.prefix+'-batch.json'))
    if batch['mod_files']!=expected:
        raise RuntimeError('Installed candidate does not match the gameplay batch')
    continuation=None
    if bool(args.guard_run)!=bool(args.continuation):raise RuntimeError('Replacement guard evidence requires its continuation journal')
    if args.continuation:
        continuation=read(HERE/'reports'/args.continuation)
        source=HERE/'reports'/(args.prefix+'-batch.json')
        if (not continuation['all_passed'] or continuation['mod_files']!=expected or
            continuation['source_batch']!=str(source) or
            continuation['source_batch_sha256']!=hashlib.sha256(source.read_bytes()).hexdigest()):
            raise RuntimeError('Continuation does not complete this unchanged batch')
    folder=HERE/'test-profile/mods/magnet-spike-experimental'
    actual={str(p.relative_to(folder)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in folder.rglob('*') if p.is_file()}
    if actual!=expected:raise RuntimeError('Installed mod files changed')
    suites={}
    names=['runtime','hook','sound','pin','moveset','command-window','hitstats','native-hitstats','aim']
    if args.world_run:names+=['worldhit','worldhook','hit-layout']
    if args.cancel_run:names+=['cancel-window','cancel-hook','command-route']
    has_smithy='smithy' in installed.get('moveset_tests',{})
    if has_smithy:names+=['smithy-tree']
    for name in names:
        path=HERE/'reports'/(name+'-regression.json');data=read(path)
        checks=data.get('fixed',data.get('checks',{}))
        if not checks or not all(checks.values()):raise RuntimeError('Failing suite: '+name)
        suites[name]={'passed':len(checks),'report':str(path)}
    gameplay={}
    labels=batch.get('run_labels',{})
    modes=['movement','magnetise','combat','shots','inputs','cutting','impact','timeout','cross','guard','actions-a','actions-b']
    if args.world_run:modes+=['worldprobe','charge']
    if args.cancel_run:modes+=['cancel']
    for mode in modes:
        label=args.action_sweep_b_run if mode=='actions-b' and args.action_sweep_b_run else labels.get(mode,args.prefix+'-'+mode)
        if mode=='worldprobe':label=args.world_run
        if mode=='charge':label=args.charge_run
        if mode=='movement':label=batch.get('movement_run',label)
        if mode=='cancel':label=args.cancel_run
        if mode=='guard' and args.guard_run:label=args.guard_run
        root=HERE/'runs'/label;data=read(root/'run.json')
        if (data['mod_files']!=expected or data.get('failure') or data.get('exit_code')
                or data.get('fatal') or not data.get('source_saves_unchanged')):
            raise RuntimeError('Failing or mismatched gameplay: '+mode)
        keys=['marker_shots','collision_sounds','ko_hits','guarded_hits','pin_restraints','pin_releases',
              'pin_successes','pin_timeouts','pin_target_position_held','pin_animation_paused','pin_hunter_hp',
              'effect_reposts','premature_effect_reposts','invalid_effect_handles','normal_pin_combos','cross_step_followup','output_muted',
              'guard_followup_attempts','guard_debug_restart_races']
        result={k:data[k] for k in keys if k in data}
        result.update(report=str(root/'run.json'),test_mode=data['test_mode'])
        if mode=='guard':
            log=(root/'log.txt').read_text(encoding='utf-8',errors='replace')
            result['confirmed_counter_hits']=len(re.findall(r'msport: hit .*in action (?:57|76|77)\b',log))
            if not result['confirmed_counter_hits']:raise RuntimeError('Guard counter did not hit a target')
        if mode in ('movement','magnetise','worldprobe','charge','cancel'):
            filename={'worldprobe':'worldhit-verification.json','charge':'charge-verification.json','cancel':'cancel-verification.json'}.get(mode,'mechanics-verification.json')
            mechanics=read(root/filename)
            if not mechanics['all_passed']:raise RuntimeError('Failing mechanics: '+mode)
            result['mechanics']=mechanics['checks']
            if mode=='cancel':result['cases']=mechanics['cases']
            if 'movement_cm' in mechanics:result['movement_cm']=mechanics['movement_cm']
        if mode.startswith('actions-'):
            result['actions_started']=len(data['action_sweep_requested'])-len(data['action_sweep_missing'])
            result['scope']=data['action_sweep_coverage']
        gameplay[mode]=result
    audio={}
    for label in [args.audio_run,labels.get('combat',args.prefix+'-combat'),labels.get('magnetise',args.prefix+'-magnetise')]:
        path=HERE/'runs'/label/'audio-verification.json';data=read(path)
        if data['mod_files']!=expected or data['clipped_fraction']!=0:
            raise RuntimeError('Mismatched or clipped capture: '+label)
        audio[label]={k:data[k] for k in ['duration_seconds','strong_matches','distinct_sample_matches','clipped_fraction','peak_stereo']}
        audio[label]['report']=str(path)
    report={'revision':installed['revision'],'installed':True,'module_sha256':digest,
        'full_port_complete':False,'scope':('Offline MHGURecomp, independent smithy class and copied hunter equipped with MS Petrified Blade; automated native gameplay and ARM/static checks'
            if has_smithy else 'Offline MHGURecomp, copied hunter equipped with Proto Spike; automated native gameplay and ARM/static checks'),
        'regression_suites':suites,'regression_checks_passed':sum(v['passed'] for v in suites.values()),
        'codec_synthetic_cases':len(read(HERE/'reports/audio-codec-regression.json')['synthetic_signals']),
        'gameplay':gameplay,'audio':audio,'source_assets':read(HERE/'reports/source-integrity-final.json'),
        'saves_unchanged':installed['saves_unchanged'],
        'batch_journal':str(HERE/'reports'/(args.prefix+'-batch.json')),
        'initial_batch_completed':batch['all_passed'],
        'replacement_sweep_b':args.action_sweep_b_run,
        'replacement_guard':args.guard_run,'continuation_journal':str(HERE/'reports'/args.continuation) if args.continuation else None,
        'continuation_completed':continuation['all_passed'] if continuation else None,
        'remaining_limits':[
            'Frontier monster restraint animations, monster-specific pin caps and original QTE UI are adapted',
            ('Exhaust remains from the GU template; Shock overlap still uses GU\'s two attack slots'
             if args.world_run else 'Exhaust remains from the GU template; Magnetic Shock hit shapes follow the hunter'),
            'All hit placements, combo/cancel windows and alternate camera/style options are not exhaustively verified',
            ('Other cancel conditions, native multi-loop edge cases and attraction-cancel input remain unverified'
             if args.cancel_run else 'Loop-qualified hold and roll-cancel boundaries need further native verification'),
            'Marker part-break lifecycle, draw/sheath/carry and exact effect fidelity remain incomplete',
            'Unmapped collision/state/pin-special sounds, source random pitch and exact gain law remain incomplete',
            'Multiplayer and automatic equip for newly created characters are not implemented',
            'Automated checks do not replace human visual, sound and playability QA']}
    if has_smithy:
        smithy=read(Path(installed['moveset_tests']['smithy']))
        equipment=read(Path(installed['moveset_tests']['equipment']))
        models=read(HERE/'reports/smithy-model-regression.json')
        if not all(d.get('all_passed') for d in (smithy,equipment,models)):
            raise RuntimeError('Smithy installation proof is incomplete')
        if any(d.get('mod_files')!=expected for d in (smithy,equipment)):
            raise RuntimeError('Smithy proof belongs to another candidate')
        report['smithy']={'weapon_families':136,'frontier_models':len(models['models']),
            'native_equipment_cases':len(equipment['cases']),'transaction_checks':smithy['checks'],
            'transaction_report':installed['moveset_tests']['smithy'],
            'equipment_report':installed['moveset_tests']['equipment'],
            'model_report':str(HERE/'reports/smithy-model-regression.json'),
            'asset_preservation_report':str(HERE/'reports/smithy-asset-audit.json')}
        report['remaining_limits']+=['Smithy preview can crop the weapon; separate saved guild-card counter and non-English custom icon atlases are not implemented']
    if args.cancel_run:
        audit=read(HERE/'reports/cancel-archive-diff.json')
        if not audit['all_passed'] or audit.get('mod_files')!=expected:raise RuntimeError('Archive audit does not match installed candidate')
        report['cancel_timing']={'original_predicate_comparisons':read(HERE/'reports/cancel-window-regression.json')['original_predicate_comparisons'],
            'source_actions':read(HERE/'cancel-window-build.json')['actions'],
            'archive_audit':str(HERE/'reports/cancel-archive-diff.json'),'source_tables_changed':audit['changed_table_count']}
    path=HERE/'moveset-verification.json';path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Recorded installed moveset evidence:',report['regression_checks_passed'],'regression checks,',report['codec_synthetic_cases'],'codec cases')
if __name__=='__main__':main()
