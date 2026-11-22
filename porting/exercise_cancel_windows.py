"""Probe charge roll windows through real controls, with muted device playback."""
import argparse,json,re,subprocess,sys,time
from prepare_frontier import HERE,ROOT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True)
    ap.add_argument('--baseline',action='store_true');args=ap.parse_args()
    profile=HERE/'runs'/args.label
    proc=subprocess.Popen([sys.executable,str(HERE/'regression_run.py'),'--label',args.label,
        '--seconds','95','--manual'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    def log():
        p=profile/'log.txt';return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
    def send(s):
        with (profile/'control.txt').open('a',encoding='utf-8') as f:f.write(s+'\n')
    cases=[('early',20,True),('gap',35,False),('late',60,True),('walk',20,False)]
    records=[];start=None;draw=-10;index=0
    try:
        while proc.poll() is None:
            text=log()
            if start is None and 'msport: hunter stats:' in text:start=time.monotonic()
            if start is None:time.sleep(.2);continue
            elapsed=time.monotonic()-start
            if 'weapon in hand (joint' not in text and elapsed>=6 and elapsed-draw>=3:
                send('X 8');draw=elapsed
            if index<len(cases) and elapsed>=12+index*18:
                name,frames,expected=cases[index]
                records.append({'case':name,'target_motion_frame':frames,'expected_roll':expected,'log_start':len(text),'sent':False})
                send('STICK_NEUTRAL 400\nplact 10 34\nA 240')
                if args.baseline:send(f'B 2 {frames}');records[-1]['sent']=True
                index+=1
            if records and not records[-1]['sent']:
                record=records[-1];chunk=text[record['log_start']:]
                samples=re.findall(r'ms-window: action 34 step 0 loop (\d+) frame (\d+)',chunk)
                if samples and int(samples[-1][1])>=record['target_motion_frame']:
                    loop,frame=map(int,samples[-1]);record['trigger_frame']=frame;record['trigger_loop']=loop
                    send('STICK_UP 35' if record['case']=='walk' else 'B 2');record['sent']=True
            if index==len(cases) and elapsed>=12+index*18:send('sdlquit');break
            time.sleep(.02)
        out=proc.communicate(timeout=30)[0].decode('utf-8',errors='replace')
    except BaseException:
        if proc.poll() is None:
            if (profile/'control.txt').exists():send('sdlquit')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
        raise
    text=log();run=json.loads((profile/'run.json').read_text(encoding='utf-8'));results={}
    for i,row in enumerate(records):
        chunk=text[row['log_start']:records[i+1]['log_start'] if i+1<len(records) else len(text)]
        rolls=re.findall(r'\[moves\] \d+ pl [0-9a-f]+ do 0001:0(?:06|13|14) ',chunk)
        results[row['case']]={k:v for k,v in row.items() if k!='log_start'}
        results[row['case']].update(roll_observed=bool(rolls),charge_started='msport: action 34 (' in chunk,
            roll_button_seen=bool(re.search(r'\[control\] B 2 at frame',chunk)),
            walk_observed=bool(re.search(r'\[moves\] \d+ pl [0-9a-f]+ do 0002:000 ',chunk)))
        clock=re.findall(r'ms-window: roll input frame (\d+) loop (\d+)',chunk)
        if clock:results[row['case']].update(actual_input_frame=int(clock[0][0]),actual_input_loop=int(clock[0][1]))
    checks={n+'_roll_window_correct':v['roll_observed']==v['expected_roll'] for n,v in results.items()}
    checks['stick_cancel_starts_drawn_movement']=results.get('walk',{}).get('walk_observed',False)
    checks['all_four_cases_exercised']=len(results)==4 and all(v['charge_started'] and (v['roll_button_seen'] or n=='walk') for n,v in results.items())
    if not args.baseline:
        checks['inputs_follow_actual_motion_clock']=all(v.get('trigger_loop')==0 and
            (20<=v.get('trigger_frame',-1)<36 if n in ('early','walk') else 35<=v.get('trigger_frame',-1)<50 if n=='gap' else 50<=v.get('trigger_frame',-1)<100)
            for n,v in results.items())
        checks['button_arrives_inside_each_intended_window']=all(v.get('actual_input_loop')==0 and
            (20<=v.get('actual_input_frame',-1)<35 if n=='early' else 36<=v.get('actual_input_frame',-1)<49 if n=='gap' else 50<=v.get('actual_input_frame',-1)<100)
            for n,v in results.items() if n!='walk')
    checks['device_output_muted']=run.get('output_muted') is True
    checks['normal_exit_and_unchanged_source_saves']=not run.get('failure') and run.get('exit_code')==0 and run.get('source_saves_unchanged')
    report={'checks':checks,'all_passed':all(checks.values()),'cases':results,'baseline':args.baseline,
            'scope':'Debug charge entry; real held charge and early/gap/late roll presses; native command evaluation',
            'module_sha256':run['module_sha256'],'mod_files':run['mod_files']}
    (profile/'cancel-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='mod_files'},indent=2))
    if not args.baseline and not report['all_passed']:print(out[-1000:]);raise SystemExit(1)
if __name__=='__main__':main()
