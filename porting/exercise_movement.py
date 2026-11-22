"""Normal inputs for a marker, attraction and repulsion with a free hunter/target."""
import argparse,json,re,subprocess,sys,time,struct,math
from prepare_frontier import HERE,ROOT

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);args=parser.parse_args()
    profile=HERE/'runs'/args.label
    proc=subprocess.Popen([sys.executable,str(HERE/'regression_run.py'),'--label',args.label,
        '--seconds','160','--quest','404','--manual','--live','--summon-distance','2400','--audio'],
        cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    def log():
        p=profile/'log.txt';return p.read_text(encoding='utf-8',errors='replace') if p.exists() else ''
    def send(text):
        with (profile/'control.txt').open('a',encoding='utf-8') as f:f.write(text+'\n')
    def snapshot(name,text):
        found=re.findall(r'\[moves\] \d+ pl ([0-9a-f]+) ',text)
        if found:
            player=int(found[-1],16)
            if 0x8000000<=player<0x30000000:send(f'memsave {player+0x40:x} c {name}.bin')
    start=None;stage=0;at=0;last=-10.;last_draw=-10.;complete=False
    manager=None;monster=None;record=None;track=None;track_at=-10.;track_no=0;repelled_first=False
    def memory(name,address,size):
        path=profile/(name+'.bin')
        if not path.exists():
            if 0x200000<=address<0x30000000:send(f'memsave {address:x} {size:x} {name}.bin')
            return None
        data=path.read_bytes()
        return data if len(data)==size else None
    try:
        while proc.poll() is None:
            text=log()
            if start is None and 'msport: hunter stats:' in text:start=time.monotonic()
            if start is None:time.sleep(.25);continue
            elapsed=time.monotonic()-start
            # Read-only target feedback steers normal camera inputs. No target
            # or hunter positions, HP or weapon state are written by this test.
            if manager is None:
                data=memory('target-manager',0x1a51fe0,4)
                if data:manager=int.from_bytes(data,'little')
            elif monster is None:
                data=memory('target-slots',manager+0x1c,40)
                if data:monster=next((v for v in struct.unpack('<10I',data) if v),None)
            elif record is None:
                data=memory('target-record',monster+0x1428,4)
                if data:record=int.from_bytes(data,'little')
            if stage<=1 and elapsed>=6 and 'weapon in hand (joint' not in text and elapsed-last_draw>=3:
                send('X 8');last_draw=elapsed;stage=1
            elif stage==1 and elapsed>=28 and 'weapon in hand (joint' in text:
                send('STICK_UP 550');stage=2
            elif stage==2 and 'summoned the large monster' in text:
                # Stop the walk immediately and centre the normal GU camera
                # behind the hunter before entering aim. The target was placed
                # along that heading. Neutral overrides the remaining walk.
                send('STICK_NEUTRAL 6000\nL 2\nZR 6000 12\nshot movement-target');stage=3
            elif stage==3:
                if 'marker shot hit monster' in text:
                    reticles=re.findall(r'aim reticle frame ([012]) .*?marker (\d+) cm',text)
                    frame=int(reticles[-1][0]) if reticles else 2
                    if frame==1:
                        snapshot('attraction-before',text)
                        send('X 8\nshot attraction-start');stage=4;at=elapsed
                    elif frame==0:
                        snapshot('repulsion-before',text)
                        send('B 8\nshot repulsion-start');stage=6;at=elapsed;repelled_first=True
                elif 'aim view on' in text and record:
                    if track is None and elapsed-track_at>=.7:
                        cameras=re.findall(r'quest camera ([0-9a-f]+), yaw',text)
                        players=re.findall(r'\[moves\] \d+ pl ([0-9a-f]+) ',text)
                        if cameras and players:
                            track_no+=1;track_at=elapsed;track=(track_no,int(cameras[-1],16),int(players[-1],16))
                    if track:
                        n,cam,player=track
                        target=memory(f'track-{n}-target',record+0x40,12)
                        hunter=memory(f'track-{n}-hunter',player+0x40,12)
                        view=memory(f'track-{n}-view',cam+0x40,44)
                        if target and hunter and view:
                            m=struct.unpack('<3f',target);h=struct.unpack('<3f',hunter);v=struct.unpack('<11f',view)
                            dx,dy,dz=(v[8]-v[0],v[9]-v[1],v[10]-v[2])
                            wanted=math.atan2(m[0]-h[0],m[2]-h[2]);yaw=math.atan2(dx,dz)
                            delta=(wanted-yaw+math.pi)%(2*math.pi)-math.pi
                            pitch=math.atan2(dy,math.hypot(dx,dz))
                            wanted_pitch=math.atan2(m[1]-h[1],math.hypot(m[0]-h[0],m[2]-h[2]))
                            dp=wanted_pitch-pitch
                            if all(math.isfinite(a) for a in (delta,dp)):
                                frames=round(abs(delta)*65536/(2*math.pi*288))
                                vertical=round(abs(dp)*65536/(2*math.pi*176))
                                if frames>1:send(f'RSTICK_{"LEFT" if delta>0 else "RIGHT"} {min(frames,90)}')
                                elif vertical>1:send(f'RSTICK_{"UP" if dp>0 else "DOWN"} {min(vertical,20)}')
                                elif elapsed-last>=2:
                                    send('A 8');last=elapsed
                            track=None
            elif stage==4 and 'msport: landed in action 58' in text:
                snapshot('attraction-after',text)
                if repelled_first:
                    send('shot movement-complete\nsdlquit');complete=True;break
                stage=5;at=elapsed
            elif stage==5 and elapsed-at>=3:
                snapshot('repulsion-before',text)
                send('B 8\nshot repulsion-start');stage=6;at=elapsed
            elif stage==6 and 'msport: action 66 (Cutting)' in text and elapsed-at>=5:
                snapshot('repulsion-after',text)
                if repelled_first:
                    snapshot('attraction-before',text)
                    send('X 8\nshot attraction-start');stage=4;at=elapsed
                else:
                    send('shot movement-complete\nsdlquit');complete=True;break
            if 'FATAL:' in text:break
            time.sleep(.2)
        output=proc.communicate(timeout=30)[0].decode('utf-8',errors='replace')
    except BaseException:
        if proc.poll() is None:
            if (profile/'control.txt').exists():send('sdlquit')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10)
        raise
    text=log();run=json.loads((profile/'run.json').read_text())
    distances={}
    for kind in ('attraction','repulsion'):
        a,b=profile/(kind+'-before.bin'),profile/(kind+'-after.bin')
        if a.exists() and b.exists():
            x,y=struct.unpack('<3f',a.read_bytes()),struct.unpack('<3f',b.read_bytes())
            distances[kind]=math.dist(x,y)
    checks={'marker_hit_from_normal_shot':'marker shot hit monster' in text,
            'attraction_started_from_normal_input':'msport: action 58 (Cutting)' in text,
            'attraction_landed':'msport: landed in action 58' in text,
            'repulsion_started_from_normal_input':'msport: action 66 (Cutting)' in text,
            'attraction_changed_hunter_position':distances.get('attraction',0)>300,
            'repulsion_changed_hunter_position':distances.get('repulsion',0)>50,
            'free_hunter_test_mode':'summon mode: hunter free (normal HP)' in text,
            'normal_exit_and_unchanged_source_saves':not run.get('failure') and run.get('exit_code')==0 and run.get('source_saves_unchanged'),
            'no_premature_effect_expiry':not run.get('invalid_effect_handles') and run.get('premature_effect_reposts',1)==0,
            'sequence_completed':complete}
    report={'checks':checks,'all_passed':all(checks.values()),'stage':stage,'movement_cm':distances,
            'scope':'Normal inputs with read-only aim tracking; active target placed once; no hunter position/HP overrides',
            'module_sha256':run['module_sha256'],'mod_files':run['mod_files']}
    (profile/'mechanics-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='mod_files'},indent=2))
    if not report['all_passed']:print(output[-1500:]);raise SystemExit(1)
if __name__=='__main__':main()
