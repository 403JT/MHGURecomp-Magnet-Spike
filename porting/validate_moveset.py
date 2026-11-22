"""Repeat gameplay gates against one immutable staged candidate, sequentially."""
import argparse, hashlib, json, subprocess, sys, time
from prepare_frontier import HERE,ROOT

def tree():
    root=HERE/'output/magnet-spike-experimental'
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob('*') if p.is_file()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',required=True)
    parser.add_argument('--movement-run',required=True)
    parser.add_argument('--continue-from',help='Retain completed passing steps from the identical immutable batch')
    args=parser.parse_args()
    expected=tree();journal={'prefix':args.prefix,'mod_files':expected,'movement_run':args.movement_run,'steps':[],'all_passed':False}
    path=HERE/'reports'/(args.prefix+'-batch.json')
    if path.exists():raise RuntimeError('Batch evidence already exists')
    previous=[]
    if args.continue_from:
        prior=(HERE/'reports'/args.continue_from).resolve()
        if not prior.is_relative_to((HERE/'reports').resolve()):raise ValueError('Invalid prior batch path')
        data=json.loads(prior.read_text(encoding='utf-8'))
        if data['mod_files']!=expected or data.get('movement_run')!=args.movement_run:
            raise RuntimeError('Prior batch belongs to a different candidate or movement fixture')
        previous=data['steps']
        journal['continuation_of']={'path':str(prior),'sha256':hashlib.sha256(prior.read_bytes()).hexdigest()}
        journal['run_labels']={}
    def save():path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    save()
    movement=HERE/'runs'/args.movement_run/'mechanics-verification.json'
    deadline=time.monotonic()+360
    while not movement.exists() and time.monotonic()<deadline:time.sleep(.5)
    data=json.loads(movement.read_text())
    if not data.get('all_passed') or data.get('mod_files')!=expected:
        raise RuntimeError('Movement sequence has not passed for this candidate')
    jobs=[('exercise_magnetise.py',['--label',args.prefix+'-magnetise']),
        ('verify_audio.py',[args.prefix+'-magnetise']),
        ('regression_run.py',['--label',args.prefix+'-audio','--seconds','85','--sound-sequence','--audio']),
        ('verify_audio.py',[args.prefix+'-audio']),
        ('regression_run.py',['--label',args.prefix+'-combat','--seconds','135','--quest','404','--combat-sounds','--audio']),
        ('verify_audio.py',[args.prefix+'-combat']),('verify_hitstats.py',[args.prefix+'-combat']),
        ('regression_run.py',['--label',args.prefix+'-shots','--seconds','95','--wall-shots','--audio']),
        ('regression_run.py',['--label',args.prefix+'-inputs','--seconds','85','--input-sequence']),
        *[('regression_run.py',['--label',args.prefix+'-'+mode,'--seconds',seconds,'--quest','404','--live','--pin-sequence',mode,'--audio'])
          for mode,seconds in (('cutting','65'),('impact','65'),('timeout','55'))],
        ('regression_run.py',['--label',args.prefix+'-cross','--seconds','45','--cross-step']),
        ('regression_run.py',['--label',args.prefix+'-guard','--seconds','100','--quest','404','--live','--guard-sequence','--audio']),
        *[('regression_run.py',['--label',args.prefix+'-actions-'+part,'--seconds','480','--action-sweep',str(i)])
          for i,part in enumerate(('a','b'))]]
    for number,(script,argv) in enumerate(jobs):
        if tree()!=expected:raise RuntimeError('Candidate changed during batch; evidence retained')
        if number<len(previous) and previous[number]['status']=='passed':
            retained=previous[number]
            # Compare the operation, allowing only the run-prefix to differ.
            old_args=retained['args']
            old_label=old_args[old_args.index('--label')+1] if '--label' in old_args else old_args[0]
            label=argv[argv.index('--label')+1] if '--label' in argv else argv[0]
            if not label.startswith(args.prefix+'-'):raise RuntimeError('Unexpected requested run label')
            suffix=label[len(args.prefix)+1:]
            replaced=[old_label if a==label else a for a in argv]
            if retained['script']!=script or replaced!=old_args or retained.get('exit_code')!=0:
                raise RuntimeError('Retained batch step does not match the requested operation')
            evidence=HERE/'runs'/old_label/'run.json'
            run=json.loads(evidence.read_text(encoding='utf-8'))
            if run['mod_files']!=expected or run.get('failure') or run.get('fatal') or run.get('exit_code')!=0:
                raise RuntimeError('Retained native run failed or differs from the candidate')
            step=dict(retained);step['retained_from']=str(prior)
            journal['steps'].append(step);journal['run_labels'][suffix]=old_label;save()
            print('Retaining passed',script,old_label,flush=True)
            continue
        step={'script':script,'args':argv,'status':'running'};journal['steps'].append(step);save()
        print('Running',script,' '.join(argv),flush=True)
        result=subprocess.run([sys.executable,str(HERE/script),*argv],cwd=ROOT,capture_output=True,text=True)
        output=HERE/'reports'/(args.prefix+'-step-'+str(number)+'.txt')
        output.write_text(result.stdout+result.stderr,encoding='utf-8')
        step.update(status='passed' if result.returncode==0 else 'failed',exit_code=result.returncode,output=str(output));save()
        print(step['status'],flush=True)
        if result.returncode:raise RuntimeError('Batch step failed; see '+str(output))
    if tree()!=expected:raise RuntimeError('Candidate changed during batch')
    journal['all_passed']=True;save();print('All batch processes passed; installer checks detailed gameplay gates.',flush=True)
if __name__=='__main__':main()
