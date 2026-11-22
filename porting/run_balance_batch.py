"""Sequential, immutable hunter-only kill comparisons; preserve every attempt."""
import argparse,json,subprocess,sys
from prepare_frontier import HERE,ROOT,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True)
    p.add_argument('--mod-source',default='backups/before-balance-1/mod')
    p.add_argument('--rank',default='max',choices=('low','mid','max'))
    p.add_argument('--weapons',nargs='+',default=['ms-cut','ms-impact','gs','ls','sns','hammer','lance','sa','gl','db','hh','ig','cb'])
    p.add_argument('--seconds',type=int,default=150);a=p.parse_args()
    path=HERE/'reports'/f'{a.prefix}-batch.json'
    if path.exists():raise RuntimeError('Batch label already exists')
    mod=(HERE/a.mod_source).resolve();assert mod.is_relative_to(HERE.resolve())
    def files():return {str(f.relative_to(mod)):sha(f) for f in mod.rglob('*') if f.is_file()}
    expected=files();journal={'mod_files':expected,'rank':a.rank,'steps':[],'all_passed':False}
    code=sha(HERE/'benchmark_balance.py')
    def save():path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    save()
    for weapon in a.weapons:
        if files()!=expected or sha(HERE/'benchmark_balance.py')!=code:raise RuntimeError('Benchmark input or driver changed')
        label=f'{a.prefix}-{weapon}';step={'weapon':weapon,'label':label,'status':'running'};journal['steps'].append(step);save()
        print('Testing',weapon,flush=True)
        args=[sys.executable,str(HERE/'benchmark_balance.py'),'--label',label,'--weapon',weapon,
            '--rank',a.rank,'--seconds',str(a.seconds),'--distance','160','--mod-source',a.mod_source]
        r=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
        out=HERE/'reports'/f'{label}-console.txt';out.write_text(r.stdout+r.stderr,encoding='utf-8')
        step.update(status='passed' if r.returncode==0 else 'failed',exit_code=r.returncode,output=str(out));save()
        if r.returncode:raise RuntimeError('Balance fixture failed; see '+str(out))
        d=json.loads((HERE/'runs'/label/'balance-run.json').read_text())
        step.update(kill_seconds=d.get('controlled_kill_seconds'),native_hp=d.get('target_max_hp'),
            dps=d.get('dps'),censored=d.get('censored'))
        save();print(weapon,'seconds',step['kill_seconds'],'DPS',step['dps'],flush=True)
    journal['all_passed']=True;save();print('Controlled comparison batch completed.',flush=True)


if __name__=='__main__':main()
