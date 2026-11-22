"""Validate max-level GS baseline stats and model routing in the native game.

Fixtures edit only the copied worn entry. Original saves remain unchanged.
One representative of every element/status and the last model are tested.
"""
import argparse,json,re,struct,subprocess,sys
from build_smithy_tree import HERE,ROOT,audit,sha

def files(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}

def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True)
    p.add_argument('--continue-from',help='Reuse successful cases for the identical candidate; missing cases use the new prefix')
    a=p.parse_args()
    tables,models,mapping,_=audit();base=tables['base'][0];levels=tables['level'][0]
    selected={}
    for i,r in enumerate(base[1:],1):
        if r[17] not in selected:selected[r[17]]=i
    ids=list(selected.values())
    last=next(i for i in range(1,len(mapping)) if mapping[i]==len(models))
    if last not in ids:ids.append(last)
    # Two branches explicitly recolored by the appearance-graph audit.
    for i in (122,125,len(base)-1):
        if i not in ids:ids.append(i)
    expected=files(HERE/'output/magnet-spike-experimental')
    report={'mod_files':expected,'cases':[],'all_passed':False}
    status=json.loads((HERE/'output/module-status.json').read_text(encoding='utf-8'))
    balance=None
    if status.get('balance_revision'):
        built=json.loads((HERE/'reports/balance-build.json').read_text(encoding='utf-8'))
        if built['policy_sha256']!=status['balance_policy_sha256']:raise RuntimeError('Staged balance policy is stale')
        balance=built['policy'];report['weapon_stat_policy']=balance
    path=HERE/'reports'/f'{a.prefix}-equipment-runtime.json'
    if path.exists():raise RuntimeError('Evidence prefix already used')
    previous={}
    if a.continue_from:
        prior=HERE/'reports'/a.continue_from
        if not prior.resolve().is_relative_to((HERE/'reports').resolve()):raise ValueError('Invalid prior evidence path')
        data=json.loads(prior.read_text(encoding='utf-8'))
        if data['mod_files']!=expected:raise RuntimeError('Prior equipment cases belong to a different candidate')
        if len({c['id'] for c in data['cases']})!=len(data['cases']):raise RuntimeError('Duplicate prior case IDs')
        previous={c['id']:c for c in data['cases']}
        if not set(previous)<=set(ids) or not all(all(c['checks'].values()) for c in previous.values()):
            raise RuntimeError('Prior equipment cases contain an invalid or failing case')
        report['continuation_of']={'path':str(prior),'sha256':sha(prior)}
    for i in ids:
        if files(HERE/'output/magnet-spike-experimental')!=expected:raise RuntimeError('Candidate changed')
        lv=base[i][9]+base[i][10]
        row=next(r for r in levels if r[4]==i and r[5]==lv)
        raw=struct.unpack_from('<H',row,8)[0];elem=struct.unpack_from('<H',row,12)[0]
        if balance:
            raw=(raw*balance['raw_percent']+50)//100
            elem=(elem*balance['element_percent']+50)//100
        ty=base[i][17];label=f'{a.prefix}-gear-{i}'
        if i in previous:
            c=previous[i]
            if (c['level'],c['model'],c['element_type'])!=(lv,mapping[i],ty):raise RuntimeError('Prior case metadata differs')
            label=c['run'];code=0;print('Rechecking retained native evidence:',label,flush=True)
        else:
            print(f'Native equipment case: ID {i}, level {lv}, model {mapping[i]}, element/status {ty}',flush=True)
            result=subprocess.run([sys.executable,str(HERE/'regression_run.py'),'--label',label,'--seconds','12',
                '--manual','--weapon-id',str(i),'--weapon-level',str(lv)],cwd=ROOT,capture_output=True,text=True)
            out=HERE/'reports'/f'{label}-console.txt';out.write_text(result.stdout+result.stderr,encoding='utf-8')
            code=result.returncode
            if not (HERE/'runs'/label/'run.json').exists():raise RuntimeError('Native case did not launch; see '+str(out))
        folder=HERE/'runs'/label;run=json.loads((folder/'run.json').read_text())
        text=(folder/'log.txt').read_text(encoding='utf-8',errors='replace')
        observed=re.findall(r'hunter stats: element type (\d+) value (\d+), raw (\d+)',text)
        loaded=re.findall(r'ms-tree: model '+str(mapping[i])+r' resource ([0-9a-f]+)',text)
        checks={'native_stats_equal_active_weapon_policy':bool(observed) and tuple(map(int,observed[-1]))==(ty,elem,raw),
            'assigned_model_loaded':any(int(v,16) for v in loaded),
            'clean_exit':code==0 and run.get('exit_code')==0 and not run.get('failure') and not run.get('fatal'),
            'muted_and_source_saves_unchanged':run.get('output_muted') and run.get('source_saves_unchanged'),
            'exact_candidate_tested':run['mod_files']==expected,
            'correct_fixture_identity':run.get('fixture_weapon_id')==i and run.get('fixture_weapon_level')==lv}
        case={'run':label,'id':i,'level':lv,'model':mapping[i],'element_type':ty,'checks':checks}
        report['cases'].append(case)
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if not all(checks.values()):raise RuntimeError('Equipment case failed: '+label+' '+str(checks))
    report['all_passed']=True;path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('All native equipment cases passed:',len(ids),flush=True)
if __name__=='__main__':main()
