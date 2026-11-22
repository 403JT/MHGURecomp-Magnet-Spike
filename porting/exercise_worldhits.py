"""Native Shock cache/lifetime probe; controlled two-metre translation after spawn."""
import argparse,json,re,struct,subprocess,sys,time
from prepare_frontier import HERE,ROOT

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);args=ap.parse_args()
    folder=HERE/'runs'/args.label
    proc=subprocess.Popen([sys.executable,str(HERE/'regression_run.py'),'--label',args.label,
        '--seconds','180','--manual'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    def log():
        p=folder/'log.txt';return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
    def send(cmd):
        with (folder/'control.txt').open('a',encoding='utf-8') as f:f.write(cmd+'\n')
    start=None;last_draw=-10;index=0;sampled=False;translated=False;player=None
    next_at=12;pending=None;ack_before=0
    try:
        while proc.poll() is None:
            text=log()
            if start is None and 'msport: hunter stats:' in text:start=time.monotonic()
            if start is None:time.sleep(.1);continue
            elapsed=time.monotonic()-start
            if elapsed>=6 and 'weapon in hand (joint' not in text and elapsed-last_draw>=3:
                send('X 8');last_draw=elapsed
            if not sampled and elapsed>=10:
                players=re.findall(r'\[moves\] \d+ pl ([0-9a-f]+) ',text)
                if players:
                    player=int(players[-1],16);send(f'memsave {player+0x40:x} c world-owner-start.bin');sampled=True
            if pending is not None and text.count(f'0010:{pending:03d} param 0')>ack_before:
                pending=None;next_at=elapsed+8
            if pending is None and index<4 and elapsed>=next_at:
                pending=159+index;ack_before=text.count(f'0010:{pending:03d} param 0')
                send('plact 10 '+str(pending));index+=1
            if not translated and 'ms-world: anchored' in text and (folder/'world-owner-start.bin').exists():
                x=struct.unpack('<3f',(folder/'world-owner-start.bin').read_bytes())[0]
                word=struct.unpack('<I',struct.pack('<f',x+200))[0]
                send(f'poke {player+0x40:x} {word:x}');translated=True
            if index==4 and pending is None and elapsed>=next_at:send('sdlquit');break
            time.sleep(.02)
        output=proc.communicate(timeout=30)[0].decode('utf-8',errors='replace')
    except BaseException:
        if proc.poll() is None:
            if (folder/'control.txt').exists():send('sdlquit')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
        raise
    text=log();data=json.loads((folder/'run.json').read_text(encoding='utf-8'))
    anchors=re.findall(r'ms-world: anchored hit (\d+) slot (\d+) shape (\d+)',text)
    radii=[int(v) for v in re.findall(r'ms-world: anchored .*?radius (\d+)',text)]
    retained=re.findall(r'ms-world: retained hit (\d+)',text)
    checks={'all_four_shock_actions_started':all(f'msport: action {n} (Impact)' in text for n in range(159,163)),
      'all_four_pulse_descriptors_anchored':len({h for h,_,_ in anchors})>=4,
      'anchors_created_for_each_sequence':len(anchors)>=16,
      'source_pillar_radius_reaches_native_cache':bool(radii) and all(v==100 for v in radii),
      'each_pulse_uses_its_single_source_shape':bool(anchors) and all(index=='0' for _,_,index in anchors),
      'world_geometry_retained_after_transform_changed':len(retained)>0,
      'controlled_translation_applied':translated,
      'device_output_muted':data.get('output_muted') is True,
      'no_premature_effect_expiry':data.get('premature_effect_reposts',1)==0 and not data.get('invalid_effect_handles'),
      'normal_exit_and_unchanged_source_saves':not data.get('failure') and data.get('exit_code')==0 and data.get('source_saves_unchanged')}
    report={'checks':checks,'all_passed':all(checks.values()),'anchor_count':len(anchors),'retained_count':len(retained),
      'scope':'Native collision cache, four debug Shock entries, one controlled hunter translation; no monster damage/balance claim',
      'module_sha256':data['module_sha256'],'mod_files':data['mod_files']}
    (folder/'worldhit-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='mod_files'},indent=2))
    if not report['all_passed']:print(output[-1200:]);raise SystemExit(1)
if __name__=='__main__':main()
