"""Isolate real charge/release controls at three timings, with device audio muted."""
import argparse,json,re,subprocess,sys,time
from prepare_frontier import HERE,ROOT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
    profile=HERE/'runs'/args.label
    proc=subprocess.Popen([sys.executable,str(HERE/'regression_run.py'),'--label',args.label,
        '--seconds','65','--manual'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    def log():
        path=profile/'log.txt';return path.read_text(encoding='utf-8',errors='replace') if path.exists() else ''
    def send(command):
        with (profile/'control.txt').open('a',encoding='utf-8') as f:f.write(command+'\n')
    start=None;draw=-10;index=0;records=[]
    cases=[('early',70,36),('charged',100,35),('overcharge',160,36)]
    try:
        while proc.poll() is None:
            text=log()
            if start is None and 'msport: hunter stats:' in text:start=time.monotonic()
            if start is None:time.sleep(.2);continue
            elapsed=time.monotonic()-start
            if 'weapon in hand (joint' not in text and elapsed>=6 and elapsed-draw>=3:
                send('X 8');draw=elapsed
            if index<len(cases) and elapsed>=12+index*15:
                name,frames,expected=cases[index]
                records.append({'case':name,'frames_held':frames,'expected_action':expected,'log_start':len(text)})
                send(f'plact 10 34\nA {frames}\nshot charge-{name}');index+=1
            if index==len(cases) and elapsed>=12+index*15:send('sdlquit');break
            time.sleep(.1)
        output=proc.communicate(timeout=30)[0].decode('utf-8',errors='replace')
    except BaseException:
        if proc.poll() is None:
            if (profile/'control.txt').exists():send('sdlquit')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
        raise
    text=log();run=json.loads((profile/'run.json').read_text(encoding='utf-8'))
    results={}
    for i,item in enumerate(records):
        chunk=text[item['log_start']:records[i+1]['log_start'] if i+1<len(records) else len(text)]
        actions=[int(n) for n in re.findall(r'msport: action (35|36) \(',chunk)]
        results[item['case']]={'frames_held':item['frames_held'],'expected_action':item['expected_action'],
            'observed_actions':actions,'manual_release_seen':'Triple Strike released' in chunk,
            'charge_cue_seen':'Triple Strike charged' in chunk,
            'overcharge_seen':'Triple Strike overcharged' in chunk}
    checks={name+'_selects_correct_strike':v['expected_action'] in v['observed_actions'] for name,v in results.items()}
    for name in ('early','charged'):checks[name+'_responds_to_button_release']=results.get(name,{}).get('manual_release_seen',False)
    checks['overcharge_releases_automatically']=results.get('overcharge',{}).get('overcharge_seen',False)
    checks['all_cases_exercised']=len(results)==3
    checks['device_output_muted']=run.get('output_muted') is True
    checks['normal_exit_and_unchanged_source_saves']=not run.get('failure') and run.get('exit_code')==0 and run.get('source_saves_unchanged')
    report={'checks':checks,'all_passed':all(checks.values()),'cases':results,
        'scope':'Debug entry into Triple Strike charge; real face-button hold/release and native command evaluation',
        'module_sha256':run['module_sha256'],'mod_files':run['mod_files']}
    (profile/'charge-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='mod_files'},indent=2))
    if not report['all_passed']:print(output[-1000:]);raise SystemExit(1)
if __name__=='__main__':main()
