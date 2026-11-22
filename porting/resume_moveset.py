"""Complete a batch stopped at the guard driver, retaining its failed evidence."""
import argparse,hashlib,json,subprocess,sys
from prepare_frontier import HERE,ROOT
from validate_moveset import tree

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prefix',required=True)
    ap.add_argument('--guard-run',required=True);args=ap.parse_args()
    source=HERE/'reports'/(args.prefix+'-batch.json')
    data=json.loads(source.read_text(encoding='utf-8'));expected=tree()
    steps=data['steps']
    if (data['mod_files']!=expected or data['all_passed'] or not steps or
        any(s['status']!='passed' for s in steps[:-1]) or
        steps[-1]['status']!='failed' or '--guard-sequence' not in steps[-1]['args']):
        raise RuntimeError('Only an unchanged batch stopped at its guard step can continue here')
    path=HERE/'reports'/(args.prefix+'-continuation.json')
    if path.exists():raise RuntimeError('Continuation evidence already exists')
    report={'source_batch':str(source),'source_batch_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'mod_files':expected,'steps':[],'all_passed':False}
    def save():path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    jobs=[['--label',args.guard_run,'--seconds','130','--quest','404','--live','--guard-sequence','--audio'],
          *[['--label',args.prefix+'-actions-'+part,'--seconds','480','--action-sweep',str(i)]
            for i,part in enumerate(('a','b'))]]
    for i,argv in enumerate(jobs):
        if tree()!=expected:raise RuntimeError('Candidate changed during continuation')
        step={'script':'regression_run.py','args':argv,'status':'running'};report['steps'].append(step);save()
        print('Running regression_run.py',' '.join(argv),flush=True)
        result=subprocess.run([sys.executable,str(HERE/'regression_run.py'),*argv],cwd=ROOT,capture_output=True,text=True)
        output=HERE/'reports'/(args.prefix+'-continuation-'+str(i)+'.txt')
        output.write_text(result.stdout+result.stderr,encoding='utf-8')
        step.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,output=str(output));save()
        print(step['status'],flush=True)
        if result.returncode:raise RuntimeError('Continuation failed; see '+str(output))
    if tree()!=expected:raise RuntimeError('Candidate changed during continuation')
    report['all_passed']=True;save()
if __name__=='__main__':main()
