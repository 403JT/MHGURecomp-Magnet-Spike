"""Validate all eleven native class kills and compute the arithmetic TTK target."""
import argparse,json,math,statistics
from pathlib import Path
from prepare_frontier import HERE,sha

REFERENCES={'gs':'balance3-gs','ls':'balance4-ls','sns':'balance5-sns-probe',
    **{w:'balance6-'+w for w in ('hammer','lance','sa','gl','db','hh','ig')},'cb':'balance7-cb'}


def reference():
    baseline=HERE/'backups/before-balance-1/mod'
    expected={str(f.relative_to(baseline)):sha(f) for f in baseline.rglob('*') if f.is_file()}
    cases=[]
    for weapon,label in REFERENCES.items():
        folder=HERE/'runs'/label;path=folder/'balance-run.json'
        d=json.loads(path.read_text(encoding='utf-8'));assert d['success'] and not d['censored']
        assert d['exit_code']==0 and d['source_saves_unchanged'] and d['output_muted'] and d['style']==0
        assert d['mod_files']==expected and d['fixture']['rank']=='max' and d['fixture']['weapon_id']==1
        assert d['controlled_kill_seconds']>0 and d['target_max_hp']>0
        events=[e for e in d['events'] if e['frame']<=d['kill_frame'] and e['hp']>0]
        assert events and all(e['class']==d['fixture']['class'] for e in events)
        assert events[0]['hp']==d['target_max_hp'],'Target damaged before timed combat'
        assert all(e['max_hp']==d['target_max_hp'] for e in events)
        effective=sum(min(max(e['damage'],0),e['hp']) for e in events)
        assert effective==d['target_max_hp'],'Native HP damage does not account for complete kill'
        lethal=[e for e in events if e['damage']>=e['hp']]
        assert len(lethal)==1 and lethal[0]==events[-1]
        lethal_frame=lethal[0]['frame'];seconds=(lethal_frame-d['start_frame'])/60
        assert 0<seconds<=d['controlled_kill_seconds']
        cases.append({'weapon':weapon,'class':d['fixture']['class'],'run':label,'report_sha256':sha(path),
            'kill_seconds':seconds,'lethal_frame':lethal_frame,'native_hp':d['target_max_hp'],
            'later_death_callback_frame':d['kill_frame'],'legacy_reported_seconds':d['controlled_kill_seconds'],
            'normalized_2000hp_seconds':seconds*2000/d['target_max_hp'],
            'effective_native_damage':effective,'hunter_damage_events':len(events),
            'runtime_sha256':d['benchmark_executable_sha256']})
    times=[c['normalized_2000hp_seconds'] for c in cases]
    r={'all_passed':True,'reference_classes':len(cases),'cases':cases,'arithmetic_mean_seconds':statistics.mean(times),
        'median_seconds':statistics.median(times),'min_seconds':min(times),'max_seconds':max(times),
        'mod_files':expected,'scope':'Held-target normal-input Guild comparisons, no armor/talisman/Arts, non-hunter hits excluded. Native random HP normalized to2000. Not unrestricted hunt or expert speedrun times.',
        'excluded_attempts':['balance1-gs-probe','balance2-guild-probe','balance3-ls','balance4-sns','balance6-cb'],
        'timing_metric':'First native lethal HP-damage event. The hook death log can occur on a later callback because original native calls are deferred. Original run reports remain unchanged.',
        'setup_versions':'Successful older cases retained; later harness changes camp readiness/stop timing. All measurements here use the same lethal-event/HP metric.'}
    return r


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='balance-melee-reference-v2.json');args=parser.parse_args()
    path=(HERE/'reports'/args.output).resolve();assert path.is_relative_to((HERE/'reports').resolve())
    if path.exists():raise RuntimeError('Reference evidence already exists; original receipts are never overwritten')
    r=reference()
    path.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print('Validated all11 reference classes. Mean normalized TTK:',round(r['arithmetic_mean_seconds'],3),'seconds')


if __name__=='__main__':main()
