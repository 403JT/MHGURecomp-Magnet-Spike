"""Complete the strict guard-damage gate after the unchanged batch and boundary test."""
import json,re,subprocess,sys,time
from prepare_frontier import HERE,ROOT,sha
from validate_smithy_build import files


def main():
    expected=files();batch=HERE/'reports/smithy20-batch.json'
    boundary=HERE/'reports/smithy19-equipment-runtime.json'
    path=HERE/'reports/smithy21-guard-continuation.json'
    if path.exists():raise RuntimeError('Continuation evidence already exists')
    deadline=time.monotonic()+2400
    while time.monotonic()<deadline:
        data=json.loads(batch.read_text(encoding='utf-8'))
        if data['mod_files']!=expected or files()!=expected:raise RuntimeError('Candidate changed')
        if any(s['status']=='failed' for s in data['steps']):raise RuntimeError('Batch failed; no guard game launched')
        if data['all_passed'] and boundary.exists():
            proof=json.loads(boundary.read_text(encoding='utf-8'))
            if proof.get('all_passed') and proof['mod_files']==expected:break
        time.sleep(1)
    else:raise RuntimeError('Batch/boundary wait expired; no guard game launched')
    journal={'mod_files':expected,'source_batch':str(batch),'source_batch_sha256':sha(batch),
        'reason':'Original guard run blocked and entered counter57, but only later combo154 hit. Require actual57/76/77 damage. Driver uses X alone and bounded live-target attempts; production candidate unchanged.',
        'steps':[],'all_passed':False}
    step={'script':'regression_run.py','args':['--label','smithy21-guard','--seconds','150','--quest','404',
        '--live','--guard-sequence','--audio'],'status':'running'}
    journal['steps'].append(step);path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    result=subprocess.run([sys.executable,str(HERE/step['script']),*step['args']],cwd=ROOT,capture_output=True,text=True)
    out=HERE/'reports/smithy21-guard-console.txt';out.write_text(result.stdout+result.stderr,encoding='utf-8')
    log=(HERE/'runs/smithy21-guard/log.txt').read_text(encoding='utf-8',errors='replace')
    hit=bool(re.search(r'msport: hit .*in action (?:57|76|77)\b',log))
    step.update(status='passed' if result.returncode==0 and hit else 'failed',exit_code=result.returncode,output=str(out))
    journal['all_passed']=step['status']=='passed' and files()==expected
    path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    if not journal['all_passed']:raise RuntimeError('Strict counter-damage gate failed; see '+str(out))
    print('Strict live guard/counter damage passed for the unchanged candidate.',flush=True)


if __name__=='__main__':main()
