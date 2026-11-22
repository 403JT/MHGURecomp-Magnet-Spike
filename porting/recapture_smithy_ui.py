"""Repeat the final smithy proof after core tests, waiting for complete PNGs."""
import argparse,json,subprocess,sys,time
from PIL import Image
from prepare_frontier import HERE,ROOT
from validate_smithy_build import files

def main():
    p=argparse.ArgumentParser();when=p.add_mutually_exclusive_group(required=True)
    when.add_argument('--after-pipeline');when.add_argument('--now',action='store_true')
    p.add_argument('--run',required=True);p.add_argument('--reload',required=True)
    p.add_argument('--reload-only',action='store_true',help='Reload and verify an already completed native UI run')
    a=p.parse_args()
    expected=files()
    if a.after_pipeline:
        pipeline=HERE/'reports'/a.after_pipeline
        if not pipeline.resolve().is_relative_to((HERE/'reports').resolve()):raise ValueError('Invalid pipeline path')
        deadline=time.monotonic()+4200;last=None
        while time.monotonic()<deadline:
            data=json.loads(pipeline.read_text(encoding='utf-8'))
            if data['mod_files']!=expected:raise RuntimeError('Core pipeline belongs to another candidate')
            if any(s['status']=='failed' for s in data['steps']):raise RuntimeError('A core gate failed; UI recapture not launched')
            if data['all_passed']:break
            progress=len(data['steps'])
            if progress!=last:print('Waiting for core pipeline; step',progress,flush=True);last=progress
            time.sleep(1)
        else:raise RuntimeError('Core tests did not complete within the bounded wait')
    def log_job(script,args,label):
        result=subprocess.run([sys.executable,str(HERE/script),*args],cwd=ROOT,capture_output=True,text=True)
        (HERE/'reports'/f'{label}.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
        if result.returncode:raise RuntimeError(script+' failed; see '+label)
    if files()!=expected:raise RuntimeError('Candidate changed')
    if not a.reload_only:
        print('Starting fresh UI/save replay with complete image checks.',flush=True)
        folder=HERE/'runs'/a.run
        proc=subprocess.Popen([sys.executable,str(HERE/'run_smithy_ui.py'),'--label',a.run,'--seconds','360','--approach'],
            cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        try:
            log_job('exercise_smithy_ui.py',['--run',a.run],a.run+'-replay')
            output=proc.communicate(timeout=30)[0]
            (HERE/'reports'/f'{a.run}-console.txt').write_bytes(output)
            if proc.returncode:raise RuntimeError('Fresh smithy replay failed')
        finally:
            if proc.poll() is None:
                control=folder/'control.txt'
                if control.exists():
                    with control.open('a',encoding='utf-8') as f:f.write('sdlquit\n')
                try:proc.wait(timeout=20)
                except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
    print('Reloading the fresh native save.',flush=True)
    folder=HERE/'runs'/a.reload
    proc=subprocess.Popen([sys.executable,str(HERE/'run_smithy_ui.py'),'--label',a.reload,'--seconds','180','--save-run',a.run],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    try:
        deadline=time.monotonic()+110
        while time.monotonic()<deadline:
            log=folder/'log.txt'
            if log.exists() and '[quickhunt] in town' in log.read_text(encoding='utf-8',errors='replace'):break
            if proc.poll() is not None:raise RuntimeError('Reload game exited before reaching the town')
            time.sleep(.25)
        else:raise RuntimeError('Reload timed out')
        control=folder/'control.txt'
        with control.open('a',encoding='utf-8') as f:f.write('PLUS 4\nRIGHT 4 30\nDOWN 4 60\nDOWN 4 85\nA 4 115\n')
        time.sleep(3.5)
        with control.open('a',encoding='utf-8') as f:f.write('shot reloaded-equipment\n')
        target=folder/'shots/reloaded-equipment.png';deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            try:
                with Image.open(target) as im:im.verify()
                with Image.open(target) as im:im.load();assert im.size==(1280,720)
                break
            except (OSError,ValueError,AssertionError):time.sleep(.1)
        else:raise RuntimeError('Reload PNG did not finish encoding')
        with control.open('a',encoding='utf-8') as f:f.write('sdlquit\n')
        output=proc.communicate(timeout=30)[0]
        (HERE/'reports'/f'{a.reload}-console.txt').write_bytes(output)
        if proc.returncode:raise RuntimeError('Fresh reload failed')
    finally:
        if proc.poll() is None:
            control=folder/'control.txt'
            if control.exists():
                with control.open('a',encoding='utf-8') as f:f.write('sdlquit\n')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
    log_job('verify_smithy_session.py',['--run',a.run,'--reload',a.reload],a.run+'-verification')
    if files()!=expected:raise RuntimeError('Candidate changed during recapture')
    print('Fresh UI/native save proof passed with fully decoded screenshots.',flush=True)
if __name__=='__main__':main()
