"""Seal balance-specific evidence without relabeling historical smithy tests."""
import argparse,json,re,struct
from pathlib import Path
from prepare_frontier import HERE,sha
from audit_balance_preservation import files
from build_smithy_tree import audit
from prepare_test_profile import BOX,WORN,ENTRY,FILE_SIZE


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True)
    parser.add_argument('--analysis');parser.add_argument('--output');a=parser.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.prefix)
    output=(HERE/'reports'/(a.output or f'{a.prefix}-validation.json')).resolve()
    assert output.is_relative_to((HERE/'reports').resolve())
    if output.exists():raise RuntimeError('Validation receipt already exists')
    expected=files(HERE/'output/magnet-spike-experimental');evidence={};checks={}
    def read(name,path):
        data=json.loads(path.read_text(encoding='utf-8'))
        evidence[name]={'path':str(path.relative_to(HERE)),'sha256':sha(path)}
        return data
    def current(data):return data.get('mod_files')==expected
    def native(name,label):
        folder=HERE/'runs'/label;data=read(name,folder/'run.json')
        checks[name+'_exact_muted_clean_run']=bool(current(data) and data.get('exit_code')==0
            and not data.get('failure') and not data.get('fatal') and data.get('output_muted')
            and data.get('source_saves_unchanged') and not data.get('invalid_effect_handles')
            and not data.get('premature_effect_reposts'))
        return data,(folder/'log.txt').read_text(errors='replace'),folder
    reference=read('reference',HERE/'reports/balance-melee-reference-v2.json')
    checks['eleven_native_melee_references_valid']=reference.get('all_passed') and reference.get('reference_classes')==11
    analysis_path=(HERE/'reports'/(a.analysis or f'{a.prefix}-spike-analysis.json')).resolve()
    assert analysis_path.is_relative_to((HERE/'reports').resolve())
    analysis=read('primary_ttk',analysis_path)
    evidence['special_damage']=evidence['primary_ttk']
    checks['primary_and_special_damage_routes_valid']=bool(current(analysis) and analysis.get('all_passed')
        and analysis['policy_sha256']==sha(HERE/'balance-policy.json')
        and analysis['reference_mean_2000hp_seconds']==reference['arithmetic_mean_seconds'])
    for label,item in analysis['evidence'].items():
        p=HERE/item['path'];assert sha(p)==item['sha256']
        evidence['ttk_'+label]=item
    static=read('static',HERE/'reports'/f'{a.prefix}-static-pipeline.json')
    checks['all_18_static_suites_passed']=bool(current(static) and static.get('all_passed')
        and len(static['steps'])==18 and all(x['passed'] for x in static['steps']))
    arm=read('live_field_ARM',HERE/'reports/balance-regression.json')
    checks['all_562_live_hit_slot_cases_passed']=bool(arm.get('all_passed') and arm['hit_slot_cases']==562
        and arm['policy_sha256']==sha(HERE/'balance-policy.json'))
    transaction=read('installer_transaction',HERE/'reports/balance-install-transaction-regression.json')
    checks['installer_success_refusal_and_rollback_tested']=bool(transaction.get('all_passed')
        and transaction['installer_sha256']==sha(HERE/'install_balance_candidate.py'))
    equivalence=read('unchanged_path_equivalence',HERE/'reports/balance-equivalence-regression.json')
    checks['changed_native_paths_cannot_reuse_old_timing_evidence']=bool(current(equivalence) and equivalence.get('all_passed'))
    preservation=read('preservation',HERE/'reports/balance-preservation.json')
    checks['assets_executable_and_saves_preserved']=bool(current(preservation) and preservation.get('all_passed'))
    equipment=read('equipment',HERE/'reports'/f'{a.prefix}-equipment-runtime.json')
    checks['all_14_native_max_level_equipment_cases_passed']=bool(current(equipment) and equipment.get('all_passed')
        and len(equipment['cases'])==14 and all(all(c['checks'].values()) for c in equipment['cases']))
    pipeline=read('native_pipeline',HERE/'reports'/f'{a.prefix}-native-pipeline.json')
    checks['all_native_processes_completed']=bool(current(pipeline) and pipeline.get('all_passed')
        and {s['group'] for s in pipeline['steps']}=={'equipment','progression','combat','charge','cancel','inputs','pins','magnetise'}
        and all(s['status']=='passed' and s['exit_code']==0 for s in pipeline['steps']))
    tables,_,mapping,_=audit();levels=tables['level'][0]
    policy=json.loads((HERE/'balance-policy.json').read_text(encoding='utf-8'))
    for rank,level in (('low',1),('mid',5)):
        run,log,_=native('progression_'+rank,a.prefix+'-'+rank)
        row=next(r for r in levels if r[4]==1 and r[5]==level)
        raw=(struct.unpack_from('<H',row,8)[0]*policy['raw_percent']+50)//100
        stats=re.findall(r'hunter stats: element type (\d+) value (\d+), raw (\d+)',log)
        checks[rank+'_native_stats_match_policy']=bool(stats and tuple(map(int,stats[-1]))==(0,0,raw)
            and run['fixture_weapon_id']==1 and run['fixture_weapon_level']==level)
    historic=read('historical_smithy_transactions',HERE/'runs/smithy8-town/smithy-verification.json')
    checks['historical_smithy_transaction_proof_intact']=bool(historic.get('all_passed'))
    # Reuse the native crafted save, with no edited fixture weapon or level.
    run,log,folder=native('crafted_run',a.prefix+'-crafted-combat')
    data=(folder/'save/save_0/system').read_bytes();assert len(data)==FILE_SIZE
    slot=data[0x2b];base=0x24+struct.unpack_from('<I',data,0x34+4*slot)[0]
    worn=struct.unpack_from('<H',data,base+WORN)[0]
    flags,ident=struct.unpack_from('<HH',data,base+BOX+worn*ENTRY);level=((flags>>5)&31)+1
    row=next(r for r in levels if r[4]==ident and r[5]==level)
    raw=(struct.unpack_from('<H',row,8)[0]*policy['raw_percent']+50)//100
    stats=re.findall(r'hunter stats: element type (\d+) value (\d+), raw (\d+)',log)
    loaded=re.findall(r'ms-tree: model '+str(mapping[ident])+r' resource ([0-9a-f]+)',log)
    checks['native_crafted_save_reload_has_correct_new_stats_and_model']=bool(
        run['save_source_run']=='smithy8-town' and run['fixture_weapon_id'] is None
        and (flags&31,ident,level)==(12,historic['saved_id'],historic['saved_level'])
        and stats and tuple(map(int,stats[-1]))==(0,0,raw) and any(int(v,16) for v in loaded))
    crafted={'all_passed':checks['native_crafted_save_reload_has_correct_new_stats_and_model']
        and checks['crafted_run_exact_muted_clean_run'],'mod_files':expected,
        'run':a.prefix+'-crafted-combat','saved_type':flags&31,'saved_id':ident,'saved_level':level,
        'observed_raw':raw,'scope':'Fresh native load/quest of the original crafted save; no forge transactions repeated. Historical transactions remain identified separately.'}
    crafted_path=HERE/'reports'/f'{a.prefix}-crafted-reload.json'
    if crafted_path.exists():assert json.loads(crafted_path.read_text(encoding='utf-8'))==crafted
    else:crafted_path.write_text(json.dumps(crafted,indent=2)+'\n',encoding='utf-8')
    read('crafted_reload',crafted_path)
    sound=read('combat_audio',folder/'audio-verification.json')
    ko=read('combat_KO',folder/'hitstats-verification.json')
    modes=set(re.findall(r'ms-sound: collision kind [012] tier [234] mode ([01])',log))
    # Use the established combat-playback gate from install_candidate.py:
    # actual Cutting/Impact material cues, not quiet-sequence match counts.
    collision_playback=all(any(r['request'] in requests and r['slot']==4 and abs(r['correlation'])>=.25
        for r in sound['detected']) for requests in ((541,542,543),(544,545,546)))
    checks['native_collision_audio_unclipped_both_modes']=bool(current(sound) and modes=={'0','1'}
        and sound.get('clipped_fraction')==0 and collision_playback and run.get('collision_sounds',0)>=4
        and run.get('sound_files_loaded',0)>=2)
    checks['balanced_charged_KO_submitted_to_native_processing']=bool(ko.get('all_passed')
        and ko.get('module_sha256')==expected[str(Path('exefs/subsdk1'))]
        and ko.get('KO_policy')=='balanced' and ko.get('required_charged_KO')==50)
    for name,file in (('charge','charge-verification.json'),('cancel','cancel-verification.json'),('magnetise','mechanics-verification.json')):
        proof=read(name,HERE/'runs'/f'{a.prefix}-{name}'/file)
        checks[name+'_native_mechanics_passed']=bool(current(proof) and proof.get('all_passed'))
    run,_,_=native('normal_pin_inputs',a.prefix+'-inputs')
    checks['both_normal_control_pin_combos_passed']=bool(run.get('normal_pin_combos') and all(run['normal_pin_combos'].values()))
    for mode,finisher in (('cutting',105),('impact',157)):
        run,log,_=native('live_pin_'+mode,a.prefix+'-pin-'+mode)
        checks['live_pin_'+mode+'_finishes_and_releases']=bool(run.get('pin_successes',0)>=1
            and run.get('pin_restraints',0)>=1 and run.get('pin_releases')==run['pin_restraints']
            and run.get('pin_target_position_held') and run.get('pin_animation_paused')
            and 0<run.get('pin_hunter_hp',5000)<=500 and f'state action 16/{finisher} ' in log)
    result={'all_passed':all(checks.values()),'checks':checks,'mod_files':expected,
        'policy_sha256':sha(HERE/'balance-policy.json'),'save_hashes':preservation['save_hashes'],
        'evidence':evidence,'reference_mean_2000hp_seconds':reference['arithmetic_mean_seconds'],
        'historical_evidence_scope':'Original smithy transactions validate unchanged recipes/encoding only. New balance stats, saved-weapon reload and affected combat have fresh exact-candidate evidence.',
        'full_port_complete':False,'limits':analysis['scope']}
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Balance validation gates:',sum(bool(v) for v in checks.values()),'/',len(checks))
    if not result['all_passed']:print('Failed:',[k for k,v in checks.items() if not v]);raise SystemExit(1)


if __name__=='__main__':main()
