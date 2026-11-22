"""Run final immutable UI/save, equipment, sound and moveset gates sequentially."""
import json,subprocess,sys,time
from PIL import Image
from prepare_frontier import HERE,ROOT,sha

def files():
    folder=HERE/'output/magnet-spike-experimental'
    return {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}

def main():
    expected=files();journal={'mod_files':expected,'steps':[],'all_passed':False}
    path=HERE/'reports/smithy8-validation-pipeline.json'
    if path.exists():raise RuntimeError('Pipeline evidence already exists')
    def save():path.write_text(json.dumps(journal,indent=2)+'\n',encoding='utf-8')
    def job(script,args):
        if files()!=expected:raise RuntimeError('Staged candidate changed')
        step={'script':script,'args':args,'status':'running'};journal['steps'].append(step);save()
        print('Running',script,' '.join(args),flush=True)
        r=subprocess.run([sys.executable,str(HERE/script),*args],cwd=ROOT,capture_output=True,text=True)
        out=HERE/'reports'/f'smithy8-pipeline-{len(journal["steps"])}.txt'
        out.write_text(r.stdout+r.stderr,encoding='utf-8')
        step.update(status='passed' if r.returncode==0 else 'failed',exit_code=r.returncode,output=str(out));save()
        if r.returncode:raise RuntimeError('Validation stopped: '+str(out))
    save();deadline=time.monotonic()+300
    ui=HERE/'runs/smithy8-town/run.json'
    while time.monotonic()<deadline:
        data=json.loads(ui.read_text(encoding='utf-8'))
        if 'exit_code' in data:break
        time.sleep(.5)
    else:raise RuntimeError('Smithy replay did not exit')
    if data['exit_code'] or not data.get('source_saves_unchanged') or data['mod_files']!=expected:
        raise RuntimeError('Smithy replay failed or belongs to another candidate')
    print('Reloading the native crafted save.',flush=True)
    label='smithy8-reload';folder=HERE/'runs'/label
    proc=subprocess.Popen([sys.executable,str(HERE/'run_smithy_ui.py'),'--label',label,
        '--seconds','180','--save-run','smithy8-town'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+110;ready=False
        while proc.poll() is None and time.monotonic()<deadline:
            log=folder/'log.txt'
            if log.exists() and '[quickhunt] in town' in log.read_text(encoding='utf-8',errors='replace'):
                ready=True;break
            time.sleep(.25)
        if not ready:raise RuntimeError('Reload failed to reach the town')
        control=folder/'control.txt'
        with control.open('a',encoding='utf-8') as f:
            f.write('PLUS 4\nRIGHT 4 30\nDOWN 4 60\nDOWN 4 85\nA 4 115\n')
        time.sleep(3.5)
        with control.open('a',encoding='utf-8') as f:f.write('shot reloaded-equipment\n')
        deadline=time.monotonic()+15
        complete=False
        while time.monotonic()<deadline:
            try:
                with Image.open(folder/'shots/reloaded-equipment.png') as im:im.verify()
                with Image.open(folder/'shots/reloaded-equipment.png') as im:im.load()
                complete=True;break
            except (OSError,ValueError):time.sleep(.1)
        if not complete:raise RuntimeError('Reload equipment screenshot did not finish encoding')
        with control.open('a',encoding='utf-8') as f:f.write('sdlquit\n')
        output=proc.communicate(timeout=30)[0]
        (HERE/'reports/smithy8-reload-console.txt').write_bytes(output)
        if proc.returncode:raise RuntimeError('Reload session failed')
    finally:
        if proc.poll() is None:
            c=folder/'control.txt'
            if c.exists():
                with c.open('a',encoding='utf-8') as f:f.write('sdlquit\n')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
    job('verify_smithy_session.py',['--run','smithy8-town','--reload',label])
    job('audit_smithy_assets.py',[])
    job('audit_cancel_archives.py',[])
    job('exercise_cancel_windows.py',['--label','smithy8-cancel'])
    job('test_equipment_runtime.py',['--prefix','smithy9'])
    job('regression_run.py',['--label','smithy9-crafted-combat','--save-run','smithy8-town',
        '--seconds','135','--quest','404','--combat-sounds','--audio'])
    job('verify_audio.py',['smithy9-crafted-combat'])
    job('verify_hitstats.py',['smithy9-crafted-combat'])
    job('validate_parity.py',['--prefix','smithy10','--cancel-run','smithy8-cancel'])
    if files()!=expected:raise RuntimeError('Candidate changed after tests')
    journal['all_passed']=True;save();print('All final smithy pipeline gates passed.',flush=True)
if __name__=='__main__':main()
