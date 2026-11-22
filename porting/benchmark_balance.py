"""Controlled native monster-kill comparison using normal inputs and isolated saves.

Target motion/position are held. HP, hitzones, sharpness, weapon resources and
damage processing remain native. This is a reproducible balance proxy, not a
claim about unrestricted hunt times or expert play.
"""
import argparse,json,os,re,shutil,struct,subprocess,time
from PIL import Image
from prepare_frontier import HERE,ROOT,sha
from prepare_test_profile import BOX,WORN,ENTRY,BOX_COUNT,FILE_SIZE
from build_smithy_tree import entries,table
from cache_helpers import seed,retire

CLASSES={'gs':0,'sns':1,'hammer':2,'lance':3,'ls':7,'sa':8,'gl':9,
         'db':11,'hh':12,'ig':13,'cb':14,'ms-cut':5,'ms-impact':5}

# Each tuple is (frame offset, held frames, buttons); repeated normal inputs.
# Different weapons keep their own native command windows and resource limits.
ROUTES={
 'gs':(210,[(0,100,'X'),(115,4,'A'),(165,4,'B')],[]),
 'sns':(150,[(0,4,'X'),(25,4,'X'),(50,4,'A'),(75,4,'A'),(110,4,'X+A')],[]),
 'hammer':(180,[(0,4,'X'),(45,4,'X'),(90,4,'X')],[]),
 'lance':(130,[(0,4,'X'),(27,4,'X'),(54,4,'X'),(95,4,'B')],[]),
 'ls':(210,[(0,4,'X'),(30,4,'A'),(60,4,'X'),(90,4,'R'),(125,4,'R'),(160,4,'R')],[]),
 'sa':(150,[(0,4,'X'),(35,4,'X'),(70,4,'A'),(110,4,'X')],[(60,4,'R')]),
 'gl':(210,[(0,4,'X'),(35,4,'X'),(70,4,'X+A'),(105,4,'A'),(130,4,'A'),(165,4,'R+A')],[]),
 'db':(210,[(0,4,'X'),(30,4,'X'),(65,4,'A'),(100,4,'X+A')],[(60,4,'R')]),
 'hh':(210,[(0,4,'X'),(40,4,'A'),(80,4,'X+A'),(135,4,'R')],[(50,4,'X'),(95,4,'X'),(140,4,'R')]),
 'ig':(170,[(0,4,'X'),(30,4,'X'),(65,4,'A'),(110,4,'X+A')],[(60,4,'R+X'),(180,4,'R+A')]),
 'cb':(300,[(0,4,'X'),(35,65,'A'),(115,4,'R+A'),(155,4,'X+A'),(200,4,'X+A'),(245,4,'X+A')],[]),
 'ms-cut':(190,[(0,4,'X'),(35,4,'X'),(70,4,'X'),(110,4,'X+A')],[]),
 'ms-impact':(270,[(0,4,'A'),(40,4,'A'),(85,110,'A')],[(60,4,'MINUS')]),
}


def fixture(destination,cls,rank):
    source=HERE/'test-profile/save/save_0';before={f.name:sha(f) for f in source.glob('system*')}
    nn=0 if cls==5 else cls
    stride=16 if nn in (9,12) else 17 if nn in (8,11,14) else 15
    resident=entries('nativeNX/loc/arc/resident.arc')
    levels,_=table(resident,f'weapon{nn:02d}LevelData',stride)
    candidates=[r for r in levels if r[4]==1];assert candidates
    maxlv=max(r[5] for r in candidates)
    lv={'low':1,'mid':max(2,maxlv//2),'max':maxlv}[rank]
    raw=struct.unpack_from('<H',next(r for r in candidates if r[5]==lv),8)[0]
    for name in before:
        data=bytearray((source/name).read_bytes());assert len(data)==FILE_SIZE
        slot=data[0x2b];base=0x24+struct.unpack_from('<I',data,0x34+4*slot)[0]
        found=[]
        for i in range(BOX_COUNT):
            at=base+BOX+i*ENTRY;flags,ident=struct.unpack_from('<HH',data,at)
            if flags&31==cls+7 and ident==1:found.append(i)
        assert found,'Missing original native starter fixture'
        index=found[0];at=base+BOX+index*ENTRY;flags=struct.unpack_from('<H',data,at)[0]
        struct.pack_into('<H',data,at,(flags&0xfc00)|(cls+7)|((lv-1)<<5))
        struct.pack_into('<7H',data,base+WORN,index,*([65535]*6))
        # Confirmed separately by the native style getter in every run.
        data[base+0x23b4c]=0
        (destination/name).write_bytes(data)
    return before,{'class':cls,'weapon_id':1,'level':lv,'original_native_raw':raw,
        'rank':rank,'armor_and_talisman':'unequipped in copied save only'}


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--weapon',choices=CLASSES,required=True);p.add_argument('--rank',choices=('low','mid','max'),default='max')
    p.add_argument('--quest',type=int,default=404);p.add_argument('--seconds',type=int,default=120)
    p.add_argument('--distance',type=int,default=200);p.add_argument('--turn',type=int,default=180)
    p.add_argument('--mod-source',default='output/magnet-spike-experimental')
    p.add_argument('--rotation',choices=('base','horizontal','basic','charged','pin','shock','magnetise'),default='base')
    p.add_argument('--verify-setup',action='store_true',help='Wait for a verified field screenshot before pinning position or starting combat')
    a=p.parse_args();assert re.fullmatch('[a-z0-9_-]+',a.label) and 15<=a.seconds<=600
    folder=HERE/'runs'/a.label
    if folder.exists():raise RuntimeError('Evidence label already exists')
    save=folder/'save/save_0';save.mkdir(parents=True)
    original,gear=fixture(save,CLASSES[a.weapon],a.rank)
    mod=(HERE/a.mod_source).resolve();assert mod.is_relative_to(HERE.resolve())
    shutil.copytree(mod,folder/'mods/magnet-spike-experimental')
    expected={str(f.relative_to(mod)):sha(f) for f in mod.rglob('*') if f.is_file()}
    shutil.copyfile(ROOT/'MHGURecomp-master/build/pipelines.list',folder/'pipelines.list');seed(folder/'cache')
    config=folder/'mhgurecomp.ini';config.write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n[Application]\nConfirmExit = Off\n[Audio]\nVolume = 0\n',encoding='utf-8')
    control=folder/'control.txt';control.write_text('fps 60\n',encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.startswith('MHGU_')}
    env.update({'MHGU_HOME':str(folder),'MHGU_SAVE_DIR':str(folder/'save'),
      'MHGU_DATA_DIR':str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
      'MHGU_CONFIG':str(config),'MHGU_MODS_DIR':str(folder/'mods'),'MHGU_HIDDEN':'1','MHGU_AUDIO_GAIN':'0',
      'MHGU_QUICKHUNT':str(a.quest),'MHGU_LDN_SERVER':'Off','MHGU_PAD_PATH':'__isolated_balance_no_controller__',
      'MHGU_CONTROL':str(control),'MHGU_LOG_MOVES':'1','MHGU_DUMMY':'1000',
      'MHGU_DUMMY_FACE':'1','MHGU_BALANCE_KILL':'1'})
    exe=HERE/'output/benchmark-runtime/mhgurecomp.exe'
    report={'weapon':a.weapon,'fixture':gear,'quest':a.quest,'seconds_budget':a.seconds,
      'mod_files':expected,'benchmark_executable_sha256':sha(exe),'output_muted':True,
      'test_scope':'Normal-input controlled kill, native HP/damage and resources, held target position/motion',
      'success':False,'failure':None}
    def save_report():(folder/'balance-run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    save_report()
    with (folder/'console.log').open('wb') as log:
        process=subprocess.Popen([str(exe)],cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    def read():
        f=folder/'log.txt';return f.read_text(errors='replace') if f.exists() else ''
    def send(cmd):
        with control.open('a',encoding='utf-8') as f:f.write(cmd+'\n')
    try:
        deadline=time.monotonic()+110
        while process.poll() is None and time.monotonic()<deadline:
            text=read()
            if '[quickhunt] in town: ordered quest' in text and re.search(r'\[moves\] \d+ pl [0-9a-f]+ is ',text):break
            if 'FATAL:' in text:raise RuntimeError('Startup fatal')
            time.sleep(.25)
        else:raise RuntimeError('Quest did not initialize')
        # Stop the stick immediately when the real area changes. Holding a
        # direction through the camera reset can walk straight back into camp.
        # State packets include camp/invalid states, so an old ready line cannot
        # survive a return transition and start a false combat measurement.
        def location():
            states=re.findall(r'\[balance\] state frame (\d+) zone (\d+) target ([0-9a-f]+)',read())
            return tuple((int(states[-1][0]),int(states[-1][1]),int(states[-1][2],16))) if states else None
        send('STICK_NEUTRAL 6000');time.sleep(2)
        ready=False
        for direction in ('UP','DOWN','RIGHT','LEFT'):
            state=location();after=state[0]+15 if state else 0
            send(f'STICK_{direction} 1800');deadline=time.monotonic()+22
            while process.poll() is None and time.monotonic()<deadline:
                state=location()
                if state and state[0]>=after and state[1] not in (0,255) and state[2]:
                    send('STICK_NEUTRAL 6000');time.sleep(2.5)
                    latest=location()
                    if latest and latest[0]>state[0] and latest[1] not in (0,255) and latest[2]:ready=True
                    break
                time.sleep(.1)
            send('STICK_NEUTRAL 6000')
            if ready:break
        if not ready:raise RuntimeError('No current non-camp target; combat benchmark not started')
        send('shot setup-ready')
        deadline=time.monotonic()+12
        while time.monotonic()<deadline:
            try:
                with Image.open(folder/'shots/setup-ready.png') as im:im.verify()
                break
            except (OSError,ValueError):time.sleep(.1)
        else:raise RuntimeError('Setup screenshot did not finish')
        if a.verify_setup:
            report['waiting_for_visual_setup']=True;save_report()
            proof=folder/'setup-verified.json';deadline=time.monotonic()+600
            while not proof.exists() and process.poll() is None and time.monotonic()<deadline:time.sleep(.2)
            if not proof.exists():raise RuntimeError('Field setup was not visually verified; no combat measurement started')
            verified=json.loads(proof.read_text(encoding='utf-8'))
            picture=(folder/'shots'/verified['image']).resolve()
            assert picture.is_relative_to((folder/'shots').resolve()) and sha(picture)==verified['sha256']
            assert verified['field_and_target_visible'] is True
            loc=location()
            if not loc or loc[1] in (0,255) or not loc[2]:raise RuntimeError('Area changed after visual setup verification')
            report['visual_setup']=verified;report['waiting_for_visual_setup']=False;save_report()
        # Setup frame markers are not part of measured combat.
        report['setup_end_log_offset']=len(read())
        draw='X 4'
        send(f'dummy {a.distance} {a.turn}\nframe\n'+draw)
        from balance_route_controls import alternate,Controller
        cycle,sequence,setup=alternate(a.weapon,a.rotation,ROUTES[a.weapon]);commands=[]
        driver=Controller(a.weapon,a.rotation,len(read()))
        def press(offset,length,buttons):
            for b in buttons.split('+'):commands.append(f'{b} {length} {offset}')
        for spec in setup:press(*spec)
        begin=300 if a.weapon=='ms-impact' and a.rotation=='horizontal' else 270 if a.weapon=='ig' else 230 if a.weapon=='hh' else 100
        for at in range(begin,a.seconds*60,cycle):
            for offset,length,buttons in sequence:press(at+offset,length,buttons)
        send('\n'.join(commands))
        start=time.monotonic();deadline=start+a.seconds
        while process.poll() is None and time.monotonic()<deadline:
            text=read()
            if '[balance] kill frame ' in text:break
            if 'FATAL:' in text:raise RuntimeError('Runtime fatal')
            driver.tick(send,text,time.monotonic()-start)
            time.sleep(.05 if a.rotation in ('charged','horizontal') else .1 if a.rotation=='pin' else .25)
        send('frame\nshot balance-end');time.sleep(2)
    except Exception as e:report['failure']=str(e)
    finally:
        if process.poll() is None:
            send('sdlquit')
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.terminate();process.wait(timeout=10);report['failure']=report['failure'] or 'Normal exit timed out'
    text=read();events=[]
    if 'driver' in locals():report['route_controller']=driver.summary()
    report['rotation']=a.rotation
    pattern=r'\[balance\] frame (\d+) class (\d+) action (\d+)/(\d+) part (\d+) damage (-?\d+) kind (\d+) hp (-?\d+) max (\d+)'
    for m in re.finditer(pattern,text):
        vals=list(map(int,m.groups()));events.append(dict(zip(('frame','class','category','action','part','damage','kind','hp','max_hp'),vals)))
    combat=text[report.get('setup_end_log_offset',0):]
    starts=[int(v) for v in re.findall(r'\[control\] frame (\d+)\b',combat)]
    killed=re.search(r'\[balance\] kill frame (\d+)',text)
    meta=re.search(r'\[balance\] player [0-9a-f]+ class (\d+) style (\d+) target [0-9a-f]+ max_hp (\d+)',text)
    if killed:
        events=[e for e in events if e['frame']<=int(killed[1]) and e['hp']>0]
    report.update(exit_code=process.returncode,events=events,kill_frame=int(killed[1]) if killed else None,
       start_frame=starts[0] if starts else None,end_frame=starts[-1] if starts else None,
       source_saves_unchanged=all(sha(HERE/'test-profile/save/save_0'/n)==v for n,v in original.items()),
       style=int(meta[2]) if meta else None,target_max_hp=int(meta[3]) if meta else None,
       damage_kinds={str(k):sum(e['damage'] for e in events if e['kind']==k) for k in {e['kind'] for e in events}},
       renderer_cache=retire(folder/'cache'))
    if report['start_frame'] is not None and report['end_frame'] is not None:
        end=report['kill_frame'] or report['end_frame'];duration=(end-report['start_frame'])/60
        effective=sum(min(max(e['damage'],0),max(e['hp'],0)) for e in events)
        report.update(controlled_seconds=duration,total_native_damage=sum(e['damage'] for e in events),effective_native_hp_damage=effective,
            dps=effective/duration if duration>0 else None,
            controlled_kill_seconds=duration if killed else None,censored=not bool(killed))
    if not events:report['failure']=report['failure'] or 'No native damage observed'
    if report['style']!=0:report['failure']=report['failure'] or 'Fixture is not Guild style'
    if not report['source_saves_unchanged']:report['failure']='Source saves changed'
    report['success']=not report['failure'] and process.returncode==0 and 'FATAL:' not in text
    save_report();print(json.dumps({k:v for k,v in report.items() if k not in ('mod_files','events','renderer_cache')},indent=2))
    if not report['success']:raise RuntimeError('Balance fixture failed; retained at '+str(folder))


if __name__=='__main__':main()
