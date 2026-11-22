"""Farm real training-target hits, then activate both modes through normal inputs.

Attack debug entry isolates charging from combo timing. Activation uses R+Minus;
this complements, rather than replaces, normal-control combo tests.
The maximum-level GS baseline keeps the long charge farm from consuming the
starter's short sharpness bar and turning the successful-hit sound probe into
a low-sharpness collision test. No live/source save is changed.
"""
import argparse,json,re,subprocess,sys,time
from pathlib import Path
from prepare_frontier import HERE,ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    profile=HERE/'runs'/args.label
    process=subprocess.Popen([sys.executable,str(HERE/'regression_run.py'),'--label',args.label,
        '--seconds','300','--quest','404','--manual','--audio','--weapon-id','1','--weapon-level','11'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    control=profile/'control.txt'
    def send(text):
        with control.open('a',encoding='utf-8') as f:f.write(text+'\n')
    def log():
        p=profile/'log.txt';return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
    def layer_modes(text):
        layers=set();last_collision=None
        for n,line in enumerate(text.splitlines()):
            match=re.search(r'ms-sound: collision .* mode ([01]) ',line)
            if match:last_collision=(n,int(match[1]))
            if 'ms-sound: post slot 4 request 547 ' in line and last_collision and n-last_collision[0]<=3:
                layers.add(last_collision[1])
        return layers
    start=None;stage=0;stage_at=0;last_attack=-10;activation_sent=False;completed=False
    retries={0:0,1:0}
    try:
        while process.poll() is None:
            text=log()
            if start is None and 'msport: hunter stats:' in text:start=time.monotonic()
            if start is None:time.sleep(.25);continue
            elapsed=time.monotonic()-start
            if stage==0 and elapsed>=6:send('STICK_UP 350');stage=1;stage_at=elapsed
            elif stage==1 and elapsed>=18:send('dummy 240 180\nX 8');stage=2;stage_at=elapsed
            elif stage==2:
                if 'Cutting Magnetise ready' in text:stage=3;stage_at=elapsed
                elif elapsed-last_attack>=2.5:send('plact 10 12');last_attack=elapsed
            elif stage==3 and elapsed-stage_at>=3:
                send('R 60\nMINUS 8 6');stage=4;stage_at=elapsed
            elif stage==4 and 'Cutting Magnetise on' in text:
                stage=5;stage_at=elapsed
            elif stage==5 and elapsed-stage_at>=3:
                send('plact 10 6');stage=6;stage_at=elapsed
            elif stage==6 and elapsed-stage_at>=4:
                if 0 not in layer_modes(text) and retries[0]<3:
                    retries[0]+=1;send('dummy 240 180\nplact 10 6');stage_at=elapsed
                else:
                    send('plact 10 18');stage=7;stage_at=elapsed;last_attack=elapsed
            elif stage==7:
                if 'Impact Magnetise ready' in text:stage=8;stage_at=elapsed
                elif elapsed-last_attack>=3.0:send('plact 10 35');last_attack=elapsed
            elif stage==8 and elapsed-stage_at>=3:
                send('R 60\nMINUS 8 6');stage=9;stage_at=elapsed
            elif stage==9 and 'Impact Magnetise on' in text:
                stage=10;stage_at=elapsed
            elif stage==10 and elapsed-stage_at>=3:
                send('dummy 240 180\nplact 10 18\nshot magnetise-active');stage=11;stage_at=elapsed
            elif stage==11 and elapsed-stage_at>=5:
                if 1 not in layer_modes(text) and retries[1]<3:
                    retries[1]+=1;send('dummy 240 180\nplact 10 18\nshot magnetise-impact-retry-'+str(retries[1]));stage_at=elapsed
                else:
                    completed=True;send('sdlquit');break
            if 'FATAL:' in text:break
            time.sleep(.2)
        output=process.communicate(timeout=30)[0].decode('utf-8',errors='replace')
    except BaseException:
        if process.poll() is None:
            if control.exists():send('sdlquit')
            try:process.wait(timeout=20)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
        raise
    text=log();run=json.loads((profile/'run.json').read_text())
    checks={m+'_ready':m+' Magnetise ready' in text for m in ('Cutting','Impact')}
    checks.update({m+'_activated_by_input':m+' Magnetise on' in text for m in ('Cutting','Impact')})
    checks['normal_exit_and_unchanged_source_saves']=not run.get('failure') and run.get('exit_code')==0 and run.get('source_saves_unchanged')
    checks['no_premature_effect_expiry']=not run.get('invalid_effect_handles') and run.get('premature_effect_reposts',1)==0
    checks['sequence_completed']=completed
    layers=layer_modes(text)
    checks['magnetised_collision_layer_posted_in_both_modes']=layers=={0,1}
    report={'checks':checks,'all_passed':all(checks.values()),'stage':stage,
            'fixture_weapon_id':1,'fixture_weapon_level':11,
            'target_reposition_retries':retries,'qualified_collision_layer_modes':sorted(layers),
            'scope':'Training target, real collision/charge callbacks, debug attack entry, normal activation inputs',
            'module_sha256':run['module_sha256'],'mod_files':run['mod_files']}
    (profile/'mechanics-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='mod_files'},indent=2))
    if not report['all_passed']:print(output[-1500:]);raise SystemExit(1)
if __name__=='__main__':main()
