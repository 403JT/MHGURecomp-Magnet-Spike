"""Evaluate native balance runs, with strict binary proof for unchanged paths."""
import argparse,collections,json,re
from prepare_frontier import HERE,sha
from audit_balance_preservation import files
from balance_evidence_equivalence import prove


def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True)
    p.add_argument('--primary',nargs='+',required=True);p.add_argument('--special',nargs='+',required=True)
    a=p.parse_args();assert re.fullmatch('[a-z0-9_-]+',a.prefix)
    path=HERE/'reports'/f'{a.prefix}-spike-analysis.json'
    if path.exists():raise RuntimeError('Analysis evidence already exists')
    expected=files(HERE/'output/magnet-spike-experimental')
    reference=json.loads((HERE/'reports/balance-melee-reference-v2.json').read_text(encoding='utf-8'))
    assert reference['all_passed']
    # Read the computed reference, never a hand-entered desired result.
    mean=reference['arithmetic_mean_seconds']
    policy=json.loads((HERE/'balance-policy.json').read_text(encoding='utf-8'))
    tolerance=policy['target_ttk_tolerance_percent']/100
    results=[];evidence={};keys={'primary':set(),'special':set()}
    for group,labels in (('primary',a.primary),('special',a.special)):
        for label in labels:
            assert re.fullmatch('[a-z0-9_-]+',label)
            folder=HERE/'runs'/label;file=folder/'balance-run.json'
            d=json.loads(file.read_text(encoding='utf-8'));text=(folder/'log.txt').read_text(errors='replace')
            key=d['weapon']+':'+d['rotation'];assert key not in keys[group];keys[group].add(key)
            events=d['events'];counts=collections.Counter(e['action'] for e in events)
            equivalence=prove(d,folder,HERE/'output/magnet-spike-experimental',expected)
            setup=d.get('visual_setup')
            reviewed=folder/'setup-reviewed-after-run.json'
            if not setup and reviewed.exists():
                setup=json.loads(reviewed.read_text(encoding='utf-8'))
                picture=(folder/'shots'/setup['image']).resolve()
                assert picture.is_relative_to((folder/'shots').resolve()) and sha(picture)==setup['sha256']
                setup=setup if setup.get('field_and_target_visible') else None
            common=bool(d['success'] and d['exit_code']==0 and not d['failure'] and d['style']==0
                and equivalence and d['source_saves_unchanged'] and d['output_muted']
                and setup and events and events[0]['hp']==d['target_max_hp']
                and 0<=events[0]['frame']-d['start_frame']<=300)
            normalized=d['controlled_seconds']*2000/d['target_max_hp']
            lethal_frame=None
            if not d['censored']:
                lethal=[e for e in events if e['damage']>=e['hp']]
                assert len(lethal)==1 and lethal[0]==events[-1]
                lethal_frame=lethal[0]['frame']
                normalized=(lethal_frame-d['start_frame'])/60*2000/d['target_max_hp']
            coverage=False
            # The base script is the vertical chain. Its X+A finisher is an
            # occasional optional follow-up, not one per vertical repetition.
            if key=='ms-cut:base':coverage=all(counts[n]>=3 for n in (1,3,4)) and counts[152]>=1
            elif key=='ms-cut:horizontal':coverage=all(counts[n]>=2 for n in (9,10,155))
            elif key=='ms-impact:basic':coverage=counts[29]>=3 and counts[18]+counts[20]>=3
            elif key=='ms-impact:charged':coverage=counts[35]>=3 and counts[36]==0 and d['route_controller'].get('overcharges')==0
            elif key=='ms-impact:horizontal':
                horizontal_damage=sum(min(e['damage'],e['hp']) for e in events if e['action'] in (24,25,28,120))
                coverage=all(counts[n]>=3 for n in (24,25,28)) and horizontal_damage>=.8*d['effective_native_hp_damage']
            elif d['rotation']=='pin':
                finisher=157 if d['weapon']=='ms-impact' else 105
                coverage=counts[finisher]>=1 and d['route_controller']['qte_input_batches']>=1
                coverage=coverage and 'ms-pin: released monster' in text
            elif key=='ms-impact:shock':
                coverage=counts[95]+counts[96]>=3 and 'action 117 (Impact)' in text
            killed=not d['censored'] and d.get('controlled_kill_seconds') is not None
            if killed:common=common and d['effective_native_hp_damage']==d['target_max_hp']
            timing=(killed and abs(normalized/mean-1)<=tolerance) if group=='primary' else normalized>=mean*(1-tolerance)
            # Utility loops may be slower or censored, but must actually land
            # the special and must not beat the reference by over tolerance.
            row={'run':label,'group':group,'route':key,'native_hp':d['target_max_hp'],
                'normalized_2000hp_seconds':normalized,'censored':d['censored'],
                'lethal_frame':lethal_frame,'later_death_callback_frame':d.get('kill_frame'),
                'percent_vs_reference':100*(normalized/mean-1),'action_hit_counts':dict(counts),
                'candidate_identity_or_proven_unchanged_path':equivalence,
                'setup_evidence':setup,
                'checks':{'valid_native_measurement':common,'required_route_covered':bool(coverage),
                    'time_within_primary_tolerance_or_safe_utility_bound':bool(timing)}}
            results.append(row);evidence[label]={'path':str(file.relative_to(HERE)),'sha256':sha(file)}
    checks={'all_five_primary_routes_present':keys['primary']=={'ms-cut:base','ms-cut:horizontal','ms-impact:basic','ms-impact:charged','ms-impact:horizontal'},
        'both_pin_modes_and_shock_present':keys['special']=={'ms-cut:pin','ms-impact:pin','ms-impact:shock'},
        'every_measurement_and_route_passed':all(all(r['checks'].values()) for r in results)}
    report={'mod_files':expected,'policy_sha256':sha(HERE/'balance-policy.json'),
        'reference_mean_2000hp_seconds':mean,'tolerance_percent':100*tolerance,
        'results':results,'evidence':evidence,'checks':checks,'all_passed':all(checks.values()),
        'scope':'Held-target normal-input Guild comparisons, timed to the first lethal HP-damage event. Shock loop is the normal evasion follow-up; strong Shock pulse field checks are static. HP normalized to2000; utility routes need a safe lower TTK bound, not equal sustained DPS. Not unrestricted hunt or expert-play equivalence.'}
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Current or binary-equivalent balance routes:',sum(all(r['checks'].values()) for r in results),'/',len(results))
    assert report['all_passed'],checks


if __name__=='__main__':main()
