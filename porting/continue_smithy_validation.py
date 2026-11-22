"""Continue the unchanged candidate after the disk-space test infrastructure failure."""
import json,subprocess,sys
from prepare_frontier import HERE,ROOT,sha
from validate_smithy_build import files

def main():
    expected=files();prior=HERE/'reports/smithy8-validation-pipeline.json'
    old=json.loads(prior.read_text(encoding='utf-8'))
    if old['mod_files']!=expected:raise RuntimeError('Candidate differs from the retained successful evidence')
    journal={'mod_files':expected,'source_pipeline':str(prior),'source_pipeline_sha256':sha(prior),
        'reason':'Renderer-cache copy exhausted disk before case122 launched. Successful native cases retained; partial run preserved.',
        'ui_proof_status':'Prior save transactions passed; complete-PNG proof will be recaptured separately.',
        'steps':[],'all_passed':False}
    path=HERE/'reports/smithy12-continuation.json'
    if path.exists():raise RuntimeError('Continuation evidence already exists')
    def save():path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    save()
    jobs=[('test_equipment_runtime.py',['--prefix','smithy12','--continue-from','smithy9-equipment-runtime.json']),
        ('regression_run.py',['--label','smithy12-crafted-combat','--save-run','smithy8-town','--seconds','135',
            '--quest','404','--combat-sounds','--audio']),
        ('verify_audio.py',['smithy12-crafted-combat']),('verify_hitstats.py',['smithy12-crafted-combat']),
        ('validate_parity.py',['--prefix','smithy10','--cancel-run','smithy8-cancel'])]
    for script,args in jobs:
        if files()!=expected:raise RuntimeError('Candidate changed')
        step={'script':script,'args':args,'status':'running'};journal['steps'].append(step);save()
        print('Running',script,' '.join(args),flush=True)
        result=subprocess.run([sys.executable,str(HERE/script),*args],cwd=ROOT,capture_output=True,text=True)
        output=HERE/'reports'/f'smithy12-step-{len(journal["steps"])}.txt'
        output.write_text(result.stdout+result.stderr,encoding='utf-8')
        step.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,output=str(output));save()
        if result.returncode:raise RuntimeError('Continuation stopped; see '+str(output))
    journal['all_passed']=True;save();print('Core continuation passed; fresh UI PNG proof still required.',flush=True)
if __name__=='__main__':main()
