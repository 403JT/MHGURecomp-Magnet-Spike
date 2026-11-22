"""Validate world geometry and charge behavior before the full immutable batch."""
import argparse,hashlib,json,subprocess,sys
from prepare_frontier import HERE,ROOT

def tree():
    root=HERE/'output/magnet-spike-experimental'
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--prefix',required=True)
    ap.add_argument('--cancel-run');args=ap.parse_args()
    expected=tree();path=HERE/'reports'/(args.prefix+'-preflight.json')
    if path.exists():raise RuntimeError('Preflight label already exists')
    report={'mod_files':expected,'steps':[],'all_passed':False}
    if json.loads((HERE/'output/module-status.json').read_text(encoding='utf-8'))['hooks']>=27:
        if not args.cancel_run:raise RuntimeError('Temporal candidate needs its matching live cancel proof')
        proof_path=HERE/'runs'/args.cancel_run/'cancel-verification.json'
        proof=json.loads(proof_path.read_text(encoding='utf-8'))
        if not proof.get('all_passed') or proof.get('baseline') or proof.get('mod_files')!=expected:
            raise RuntimeError('Cancel proof failed or belongs to different code/assets')
        report['cancel_verification']=str(proof_path)
    def save():path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save()
    for script,argv in [('exercise_worldhits.py',['--label',args.prefix+'-worldprobe']),
        ('exercise_charge.py',['--label',args.prefix+'-charge']),
        ('exercise_movement.py',['--label',args.prefix+'-movement']),
        ('validate_moveset.py',['--prefix',args.prefix,'--movement-run',args.prefix+'-movement'])]:
        if tree()!=expected:raise RuntimeError('Candidate changed during parity validation')
        step={'script':script,'args':argv,'status':'running'};report['steps'].append(step);save()
        print('Running',script,' '.join(argv),flush=True)
        result=subprocess.run([sys.executable,str(HERE/script),*argv],cwd=ROOT,capture_output=True,text=True)
        output=HERE/'reports'/(args.prefix+'-'+script.removesuffix('.py')+'.txt')
        output.write_text(result.stdout+result.stderr,encoding='utf-8')
        step.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,output=str(output));save()
        print(step['status'],flush=True)
        if result.returncode:raise RuntimeError('Parity validation failed; retained evidence: '+str(output))
    report['all_passed']=True;save()
if __name__=='__main__':main()
