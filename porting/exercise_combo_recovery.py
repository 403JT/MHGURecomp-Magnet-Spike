"""Muted native normal-input combo, followed by labelled finisher fixtures."""
import argparse,json,re,subprocess,sys,time
from prepare_frontier import HERE,ROOT,CONVERTER


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--baseline',action='store_true')
    a=p.parse_args();folder=HERE/'runs'/a.label
    proc=subprocess.Popen([sys.executable,str(HERE/'regression_run.py'),'--label',a.label,
        '--seconds','220','--quest','101','--manual'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    def log():
        f=folder/'log.txt';return f.read_text(errors='replace') if f.exists() else ''
    def send(s):
        with (folder/'control.txt').open('a',encoding='utf-8') as f:f.write(s+'\n')
    ready=drawn=None;last_draw=-10;last_press=-1;natural_end=False;cases=[];next_case=0
    fixture_time=0;fixture_pressed=False;last_request=0
    # Deliberate debug entries isolate recovery/interrupt handling. These are
    # separate from the first normal-input Cutting right-button combo.
    fixtures=[(4,'X'),(10,'A'),(26,'B'),(28,'STICK_UP'),(29,'MINUS'),
        (35,'R+ZR'),(36,'Y'),(60,'A'),(74,'B'),(105,'A'),(157,'A')]
    sys.path.insert(0,str(CONVERTER/'weapons/magnet_spike/tools'))
    import msact
    acts=msact.actions((CONVERTER/'dump/mhf/zz/mhfdat.dec.prefix.bin').read_bytes())
    final_steps={no:len(acts[no]['steps']) for no,_ in fixtures}
    try:
        while proc.poll() is None:
            text=log();now=time.monotonic()
            if ready is None and 'msport: hunter stats:' in text:ready=now
            if ready is None:time.sleep(.1);continue
            elapsed=now-ready
            if drawn is None:
                if 'weapon in hand (joint' in text:drawn=now
                elif elapsed>=7 and elapsed-last_draw>=2.5:send('X 8');last_draw=elapsed
            if drawn is not None:
                active=now-drawn
                if active<18 and active-last_press>=.17:
                    send('A 3');last_press=active
                if active>=18 and not natural_end:
                    natural_end=True
                    if a.baseline:send('sdlquit');break
                if not a.baseline and active>=20 and next_case<len(fixtures) and (not cases or
                    (fixture_pressed and now-fixture_time>=7 and
                     (('ms-recovery: command action '+str(cases[-1]['action'])+' ') in text[cases[-1]['log_start']:] or
                      ('ms-recovery: action '+str(cases[-1]['action'])+' tail') in text[cases[-1]['log_start']:]))):
                    no,button=fixtures[next_case];cases.append({'action':no,'button':button,'log_start':len(text)})
                    send(f'plact 10 {no}')
                    fixture_time=last_request=now;fixture_pressed=False
                    next_case+=1
                if cases and not fixture_pressed:
                    c=cases[-1];chunk=text[c['log_start']:]
                    if re.search(r'msport: state action 16/'+str(c['action'])+r' step '+str(final_steps[c['action']])+r'\b',chunk):
                        button=c['button'];fixture_pressed=True;fixture_time=now
                        if button=='STICK_UP':send('STICK_UP 280')
                        else:send('\n'.join(button+' 3 '+str(15+i*8) for i in range(30)))
                    elif not re.search(r'msport: action '+str(c['action'])+r' \(',chunk) and now-last_request>=3:
                        send('plact 10 '+str(c['action']));last_request=now
                if not a.baseline and next_case==len(fixtures) and fixture_pressed and now-fixture_time>=8:
                    send('STICK_NEUTRAL 1\nsdlquit');break
            time.sleep(.03)
        output=proc.communicate(timeout=30)[0].decode(errors='replace')
    finally:
        if proc.poll() is None:
            send('sdlquit')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
    text=log();r=json.loads((folder/'run.json').read_text())
    natural=text[:cases[0]['log_start']] if cases else text
    reached={int(n) for n in re.findall(r'msport: action (\d+) \(',natural)}
    checks={'normal_right_button_combo_reached_all_three':{6,9,10}<=reached,
        'muted':r['output_muted'],'normal_exit':r['exit_code']==0 and not r['failure'] and not r['fatal'],
        'source_saves_unchanged':r['source_saves_unchanged']}
    if not a.baseline:checks['normal_right_finisher_recovery_seen']='ms-recovery: command action 10' in natural or 'ms-recovery: action 10 tail' in natural
    details=[]
    for i,c in enumerate(cases):
        chunk=text[c['log_start']:cases[i+1]['log_start'] if i+1<len(cases) else len(text)]
        details.append({'action':c['action'],'button':c['button'],
            'started':bool(re.search(r'msport: action '+str(c['action'])+r' \(',chunk)),
            'recovery_seen':('ms-recovery: command action '+str(c['action'])+' ') in chunk or ('ms-recovery: action '+str(c['action'])+' tail') in chunk})
    if not a.baseline:
        checks['all_finisher_fixtures_started']=len(details)==len(fixtures) and all(c['started'] for c in details)
        checks['all_finisher_fixtures_reached_recovery']=all(c['recovery_seen'] for c in details)
    report={'checks':checks,'all_passed':all(checks.values()),'cases':details,'baseline':a.baseline,
        'normal_combo_actions':sorted(reached),'mod_files':r['mod_files'],'module_sha256':r['module_sha256'],
        'scope':'First phase is ordinary draw/right-button inputs. Later finisher entries are explicit debug fixtures, not natural-hunt evidence.'}
    (folder/'recovery-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='mod_files'},indent=2))
    assert report['all_passed'],checks


if __name__=='__main__':main()
