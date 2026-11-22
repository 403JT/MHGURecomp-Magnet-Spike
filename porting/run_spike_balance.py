"""Measure the unchanged tuned candidate over common and special normal-input routes."""
import argparse,json,subprocess,sys
from prepare_frontier import HERE,ROOT,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True);p.add_argument('--cases',nargs='+')
    p.add_argument('--seconds',type=int,default=150);a=p.parse_args()
    cases={'cut-base':('ms-cut','base'),'impact-charged':('ms-impact','charged'),
        'cut-horizontal':('ms-cut','horizontal'),'impact-basic':('ms-impact','basic'),
        'impact-horizontal':('ms-impact','horizontal'),'cut-pin':('ms-cut','pin'),
        'impact-pin':('ms-impact','pin'),'impact-shock':('ms-impact','shock')}
    chosen=a.cases or list(cases)
    mod=HERE/'output/magnet-spike-experimental'
    def files():return {str(f.relative_to(mod)):sha(f) for f in mod.rglob('*') if f.is_file()}
    expected=files();path=HERE/'reports'/f'{a.prefix}-spike-batch.json'
    if path.exists():raise RuntimeError('Batch evidence already exists')
    report={'mod_files':expected,'steps':[],'all_passed':False}
    def save():path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save();driver=sha(HERE/'benchmark_balance.py');routes=sha(HERE/'balance_route_controls.py')
    for name in chosen:
        assert files()==expected and sha(HERE/'benchmark_balance.py')==driver and sha(HERE/'balance_route_controls.py')==routes
        weapon,rotation=cases[name];label=a.prefix+'-'+name
        step={'case':name,'label':label,'status':'running'};report['steps'].append(step);save()
        print('Measuring',name,flush=True)
        r=subprocess.run([sys.executable,str(HERE/'benchmark_balance.py'),'--label',label,'--weapon',weapon,
            '--rotation',rotation,'--seconds',str(a.seconds),'--distance','160','--verify-setup'],cwd=ROOT,capture_output=True,text=True)
        out=HERE/'reports'/f'{label}-console.txt';out.write_text(r.stdout+r.stderr,encoding='utf-8')
        step.update(status='completed' if r.returncode==0 else 'failed',exit_code=r.returncode,output=str(out));save()
        if r.returncode:raise RuntimeError('Native measurement failed; see '+str(out))
        d=json.loads((HERE/'runs'/label/'balance-run.json').read_text())
        step.update(kill_seconds=d.get('controlled_kill_seconds'),native_hp=d.get('target_max_hp'),censored=d['censored'])
        if d.get('controlled_kill_seconds'):step['normalized_2000hp_seconds']=d['controlled_kill_seconds']*2000/d['target_max_hp']
        save();print(name,'normalized seconds',step.get('normalized_2000hp_seconds'),'censored',step['censored'],flush=True)
    report['all_passed']=all(s['status']=='completed' and not s['censored'] for s in report['steps']);save()
    print('Measurements complete; evaluate route coverage and TTK separately.',flush=True)


if __name__=='__main__':main()
