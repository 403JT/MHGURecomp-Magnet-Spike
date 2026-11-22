"""Match real collision KO arguments to the checked source-hit mapping."""
import argparse,json,re
from prepare_frontier import HERE

def main():
    p=argparse.ArgumentParser();p.add_argument('profile');args=p.parse_args()
    folder=HERE/'runs'/args.profile
    run=json.loads((folder/'run.json').read_text())
    table=(HERE/'output/ms_hitstats_data.inc').read_text().split('{',1)[1].split('}',1)[0]
    expected=[int(v) for v in re.findall(r'\d+',table)]
    status=json.loads((HERE/'output/module-status.json').read_text(encoding='utf-8'))
    policy_name='source'
    required_ko=max(expected)
    if status.get('balance_revision'):
        from prepare_frontier import sha
        if sha(HERE/'output/magnet-spike-experimental/exefs/subsdk1')==run['module_sha256']:
            balance=json.loads((HERE/'reports/balance-build.json').read_text(encoding='utf-8'))
            assert balance['policy_sha256']==status['balance_policy_sha256']
            base=balance['source_hit_count'];expected=[0]*balance['hit_count']
            for r in balance['hits']:expected[r['hit']]=expected[r['hit']+base]=r['balanced_ko']
            policy_name='balanced'
            required_ko=next(r['balanced_ko'] for r in balance['hits'] if r['action']==35)
    latest={};matches=[];mismatches=[]
    for n,line in enumerate((folder/'log.txt').read_text(errors='replace').splitlines()):
        m=re.search(r'\[ko\].* ([0-9a-f]{8}) own \d+ hit: KO (\d+) on part (\d+).*pending (-?\d+) \(\+(-?\d+)\)',line)
        if m:latest[int(m[1],16)]=(n,int(m[2]),int(m[3]),int(m[5]))
        m=re.search(r'msport: hit (\d+) .*monster ([0-9a-f]+) in action (\d+)',line)
        if not m:continue
        hit,mon,action=int(m[1]),int(m[2],16),int(m[3])
        if hit>=len(expected) or not expected[hit]:continue
        event=latest.get(mon)
        if not event or n-event[0]>5:continue
        row={'action':action,'hit':hit,'expected_KO':expected[hit],'native_KO_argument':event[1],
             'part':event[2],'pending_KO_delta':event[3]}
        (matches if event[1]==expected[hit] else mismatches).append(row)
    checks={'at_least_four_active_hit_matches':len({r['hit'] for r in matches})>=4,
            'charged_strike_KO_reaches_live_native_processing':any(r['expected_KO']==required_ko for r in matches),
            'no_mismatched_source_values':not mismatches,
            'successful_run':not run.get('failure') and run.get('exit_code')==0 and run.get('source_saves_unchanged')}
    report={'checks':checks,'all_passed':all(checks.values()),'matches':matches,'mismatches':mismatches,
            'module_sha256':run['module_sha256'],'KO_policy':policy_name,'required_charged_KO':required_ko,
            'scope':'KO submitted to native part processing; non-stunnable body parts correctly add zero. Native head multiplier is checked separately under ARM.'}
    (folder/'hitstats-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
