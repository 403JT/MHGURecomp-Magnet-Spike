"""Keep matching passed gates; repeat the successful-hit Magnetise probe and remaining batch."""
import argparse,json,subprocess,sys,time
from prepare_frontier import HERE,ROOT,sha
from validate_smithy_build import files

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True);parser.add_argument('--ui-run',required=True)
    args=parser.parse_args()
    expected=files();prior=HERE/'reports/smithy12-continuation.json'
    old=json.loads(prior.read_text(encoding='utf-8'))
    if old['mod_files']!=expected:raise RuntimeError('Candidate changed')
    for label,name in [('smithy10-worldprobe','worldhit-verification.json'),('smithy10-charge','charge-verification.json'),
                       ('smithy10-movement','mechanics-verification.json')]:
        proof=json.loads((HERE/'runs'/label/name).read_text(encoding='utf-8'))
        if not proof['all_passed'] or proof['mod_files']!=expected:raise RuntimeError('Prior matching geometry/charge/movement gate missing')
    path=HERE/'reports'/f'{args.prefix}-continuation.json'
    if path.exists():raise RuntimeError('Continuation evidence already exists')
    journal={'mod_files':expected,'source_continuation':str(prior),'source_sha256':sha(prior),
        'reason':'Both Magnetise activations passed; final Impact tier0 collision did not exercise the successful-hit sound layer. Driver repositions and retries within a bounded budget; required layer predicate unchanged.',
        'steps':[],'all_passed':False}
    path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    deadline=time.monotonic()+500;ui=HERE/'runs'/args.ui_run/'smithy-verification.json'
    while time.monotonic()<deadline:
        if ui.exists():
            proof=json.loads(ui.read_text(encoding='utf-8'))
            if not proof['all_passed'] or proof['mod_files']!=expected:raise RuntimeError('Fresh UI proof failed')
            break
        time.sleep(.5)
    else:raise RuntimeError('Fresh UI proof did not complete')
    print('Starting remaining immutable batch with successful-hit probe.',flush=True)
    step={'script':'validate_moveset.py','args':['--prefix',args.prefix,'--movement-run','smithy10-movement'],'status':'running'}
    journal['steps'].append(step);path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    result=subprocess.run([sys.executable,str(HERE/step['script']),*step['args']],cwd=ROOT,capture_output=True,text=True)
    out=HERE/'reports'/f'{args.prefix}-batch-console.txt';out.write_text(result.stdout+result.stderr,encoding='utf-8')
    step.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,output=str(out))
    journal['all_passed']=result.returncode==0 and files()==expected
    path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    if not journal['all_passed']:raise RuntimeError('Remaining batch failed; retained evidence: '+str(out))
    print('Remaining matching batch passed.',flush=True)
if __name__=='__main__':main()
