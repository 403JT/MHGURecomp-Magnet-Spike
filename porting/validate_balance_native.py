"""Fresh native stat, crafted-save and affected combat checks for one candidate."""
import argparse,json,re,subprocess,sys
from prepare_frontier import HERE,ROOT
from audit_balance_preservation import files


def main():
    p=argparse.ArgumentParser();p.add_argument('--prefix',required=True)
    p.add_argument('--cases',nargs='+',choices=('equipment','progression','combat','charge','cancel','inputs','pins','magnetise'))
    a=p.parse_args();assert re.fullmatch('[a-z0-9_-]+',a.prefix)
    expected=files(HERE/'output/magnet-spike-experimental')
    path=HERE/'reports'/f'{a.prefix}-native-pipeline.json'
    if path.exists():raise RuntimeError('Evidence prefix already exists')
    journal={'mod_files':expected,'steps':[],'all_passed':False}
    groups={
        'equipment':[('test_equipment_runtime.py',['--prefix',a.prefix])],
        'progression':[('regression_run.py',['--label',a.prefix+'-'+rank,'--seconds','12','--manual',
            '--weapon-id','1','--weapon-level',str(level)]) for rank,level in (('low',1),('mid',5))],
        'combat':[('regression_run.py',['--label',a.prefix+'-crafted-combat','--save-run','smithy8-town',
            '--seconds','135','--quest','404','--combat-sounds','--audio']),
            ('verify_audio.py',[a.prefix+'-crafted-combat']),('verify_hitstats.py',[a.prefix+'-crafted-combat'])],
        'charge':[('exercise_charge.py',['--label',a.prefix+'-charge'])],
        'cancel':[('exercise_cancel_windows.py',['--label',a.prefix+'-cancel'])],
        'inputs':[('regression_run.py',['--label',a.prefix+'-inputs','--seconds','85','--input-sequence'])],
        'pins':[('regression_run.py',['--label',a.prefix+'-pin-'+mode,'--seconds','65','--quest','404',
            '--live','--pin-sequence',mode]) for mode in ('cutting','impact')],
        'magnetise':[('exercise_magnetise.py',['--label',a.prefix+'-magnetise'])],
    }
    def save():path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    save()
    for group in a.cases or groups:
        for script,args in groups[group]:
            if files(HERE/'output/magnet-spike-experimental')!=expected:raise RuntimeError('Candidate changed during native checks')
            item={'group':group,'script':script,'args':args,'status':'running'};journal['steps'].append(item);save()
            print('Checking',group,script,flush=True)
            result=subprocess.run([sys.executable,str(HERE/script),*args],cwd=ROOT,capture_output=True,text=True)
            out=HERE/'reports'/f'{a.prefix}-native-step-{len(journal["steps"])}.txt'
            out.write_text(result.stdout+result.stderr,encoding='utf-8')
            item.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,output=str(out));save()
            if result.returncode:raise RuntimeError('Native validation stopped; see '+str(out))
    journal['all_passed']=True;save()
    print('Native processes passed; detailed receipts still require review.',flush=True)


if __name__=='__main__':main()
