"""Run a muted, disposable natural hunt; no target/HP/action manipulation.

Quickhunt only skips the town quest-selection UI. Natural spawns, AI, hunter
damage and all quest objectives remain native. Human observations and actual
outcomes are recorded separately; a clean exit never means every scenario passed.
"""
import argparse,json,msvcrt,os,re,shutil,struct,subprocess,time
from prepare_frontier import HERE,ROOT,sha
from cache_helpers import seed,retire


def files(folder):
    return {str(p.relative_to(folder)):sha(p) for p in folder.rglob('*') if p.is_file()}


def prepare(label,quest,seconds,visible=False,supplies=False,max_starter=False):
    assert re.fullmatch('[a-z0-9_-]+',label) and 60<=seconds<=3600
    folder=HERE/'runs'/label
    if folder.exists():raise RuntimeError('Hunt evidence label already exists')
    game_sha=sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')
    if game_sha!='b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef':
        raise RuntimeError('Game executable is not the verified MHGU1.4.0 target')
    installed=json.loads((HERE/'installed-build.json').read_text(encoding='utf-8'))
    mod=HERE/'test-profile/mods/magnet-spike-experimental'
    if installed['files']!=files(mod):raise RuntimeError('Installed files differ from their receipt')
    source=HERE/'test-profile/save/save_0';original={p.name:sha(p) for p in source.glob('system*')}
    assert set(original)=={'system','system_backup'}
    save=folder/'save/save_0';save.mkdir(parents=True)
    for name in original:shutil.copyfile(source/name,save/name)
    fixture={}
    if supplies or max_starter:
        from prepare_test_profile import BOX,WORN,ENTRY,FILE_SIZE
        ids=json.loads((HERE/'reports/hunt-fixture-item-identities.json').read_text()) if supplies else {}
        amounts={'Potion':10,'Mega Potion':10,'Whetstone':20,'Shock Trap':1,'Pitfall Trap':1,'Tranq Bomb':8,'Farcaster':1,'Paintball':20}
        for name in original:
            data=bytearray((save/name).read_bytes());assert len(data)==FILE_SIZE
            slot=data[0x2b];assert slot<3 and data[0x28+slot]
            base=0x24+struct.unpack_from('<I',data,0x34+slot*4)[0]
            before=bytes(data);allowed=set()
            if max_starter:
                index=struct.unpack_from('<H',data,base+WORN)[0];assert index<2000
                at=base+BOX+index*ENTRY;flags,ident=struct.unpack_from('<HH',data,at)
                assert flags&31==12 and ident==1,'Max-level fixture requires the copied starter'
                struct.pack_into('<H',data,at,(flags&0xfc00)|12|(10<<5));allowed.update(range(at,at+2))
                fixture['weapon']='Owned starter copied at level11 for finite natural-hunt tests'
            if supplies:
                at=base+0x27bf;size=76;stream=int.from_bytes(data[at:at+size],'little')
                empty=[i for i in range(32) if not (stream>>(19*i))&0x7ffff]
                assert len(empty)>=len(ids),'Copied pouch has insufficient free slots; no existing item overwritten'
                for i,(item_name,ident) in zip(empty,ids.items()):stream|=(ident|(amounts[item_name]<<12))<<(19*i)
                data[at:at+size]=stream.to_bytes(size,'little');allowed.update(range(at,at+size))
                fixture['supplies']='Finite ordinary consumables added only to empty copied-pouch slots'
            assert all(a==b or i in allowed for i,(a,b) in enumerate(zip(before,data)))
            (save/name).write_bytes(data)
    shutil.copytree(mod,folder/'mods/magnet-spike-experimental')
    shutil.copyfile(ROOT/'MHGURecomp-master/build/pipelines.list',folder/'pipelines.list')
    seed(folder/'cache')
    config=folder/'mhgurecomp.ini'
    config.write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n[Application]\nConfirmExit = Off\n[Audio]\nVolume = 0\n',encoding='utf-8')
    control=folder/'control.txt';control.write_text('fps 60\n',encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.startswith('MHGU_')}
    env.update({'MHGU_HOME':str(folder),'MHGU_SAVE_DIR':str(folder/'save'),
        'MHGU_DATA_DIR':str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
        'MHGU_MODS_DIR':str(folder/'mods'),'MHGU_CONFIG':str(config),
        'MHGU_AUDIO_GAIN':'0','MHGU_LDN_SERVER':'Off','MHGU_CONTROL':str(control),
        'MHGU_LOG_MOVES':'1','MHGU_EMTRACE':'1','MHGU_QUICKHUNT':str(quest)})
    # This runtime tests getenv(), so even "0" hides the window. A human
    # session must omit both hidden mode and the controller override entirely.
    if not visible:
        env['MHGU_HIDDEN']='1';env['MHGU_PAD_PATH']='__isolated_natural_hunt_no_controller__'
    forbidden={'MHGU_DUMMY','MHGU_SUMMON','MHGU_KILL_AFTER','MHGU_FORCE_EVENT','MHGU_BALANCE_KILL'}
    assert not forbidden.intersection(env)
    report={'label':label,'quest':quest,'seconds_budget':seconds,'game_version':'MHGU 1.4.0',
        'mod_revision':installed['revision'],'mod_files':installed['files'],
        'game_main_sha256':game_sha,
        'executable_sha256':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe'),
        'source_save_hashes':original,'output_muted':True,'visible':visible,
        'native_AI_HP_and_damage':True,'fixture':fixture,'setup_shortcut':'Town quest selection skipped by quickhunt',
        'scope':'Natural-quest session; completion/capture/fainting require observed evidence, not just a clean process exit.',
        'failure':None,'coverage':{k:'not_observed' for k in ('long_hunt','multiple_large_monsters',
            'area_changes','fainting','capture','quest_completion','interrupted_moves','return_to_town','save_reload')}}
    return folder,env,report


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--quest',type=int,default=404);p.add_argument('--seconds',type=int,default=1200)
    p.add_argument('--visible',action='store_true');p.add_argument('--supplies',action='store_true')
    p.add_argument('--max-starter',action='store_true');p.add_argument('--town',action='store_true')
    p.add_argument('--prepared',action='store_true');a=p.parse_args()
    if a.prepared:
        assert re.fullmatch('[a-z0-9_-]+',a.label)
        folder=HERE/'runs'/a.label;setup=folder/'hunt-prepared.json'
        prepared=json.loads(setup.read_text(encoding='utf-8'));report=prepared['report']
        if (folder/'hunt-run.json').exists():raise RuntimeError('Prepared hunt session was already used; its evidence will not be overwritten')
        assert files(folder/'mods/magnet-spike-experimental')==report['mod_files']
        assert report['mod_files']==json.loads((HERE/'installed-build.json').read_text())['files']
        env={k:v for k,v in os.environ.items() if not k.startswith('MHGU_')};env.update(prepared['environment'])
        assert env['MHGU_AUDIO_GAIN']=='0' and env['MHGU_HOME']==str(folder) and env['MHGU_SAVE_DIR']==str(folder/'save')
        if report['visible']:assert 'MHGU_HIDDEN' not in env and 'MHGU_PAD_PATH' not in env
        a.seconds=report['seconds_budget'];a.quest=report['quest']
    else:
        a.quest='town' if a.town else a.quest
        folder,env,report=prepare(a.label,a.quest,a.seconds,a.visible,a.supplies,a.max_starter)
    path=folder/'hunt-run.json'
    exe=ROOT/'MHGURecomp-master/build/mhgurecomp.exe'
    assert sha(exe)==report['executable_sha256'],'Test executable differs from prepared receipt'
    assert sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')==report['game_main_sha256']
    # A sandbox can display SDL windows while denying HID device access. Check
    # in the same launch context, before consuming a prepared human session.
    if report.get('controller_required'):
        result=subprocess.run([str(exe),'--list-controllers'],cwd=folder,env=env,
            capture_output=True,text=True,check=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        controllers=json.loads(result.stdout)['controllers']
        if not controllers:
            raise RuntimeError('No accessible controller. Launch this human test from the desktop, or from an approved process outside the sandbox.')
        report['controller_preflight']={'count':len(controllers),'names':[c['name'] for c in controllers]}
    profile_lock=(folder/'session.lock').open('a+b');profile_lock.seek(0)
    msvcrt.locking(profile_lock.fileno(),msvcrt.LK_NBLCK,1)
    def write():path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def send(text):
        with (folder/'control.txt').open('a',encoding='utf-8') as f:f.write(text+'\n')
    def log():
        f=folder/'log.txt';return f.read_text(errors='replace') if f.exists() else ''
    write()
    with (folder/'console.log').open('wb') as output:
        proc=subprocess.Popen([str(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')],cwd=folder,env=env,
            stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    report['pid']=proc.pid;write();start=time.monotonic();ready=None;next_shot=0
    print('Natural hunt launched:',a.label,'muted; no target/HP/AI overrides.',flush=True)
    try:
        while proc.poll() is None:
            text=log();elapsed=time.monotonic()-start
            if 'FATAL:' in text:report['failure']='Native fatal error';break
            condition='[quickhunt] in town' if a.quest=='town' else '[quickhunt] in town: ordered quest'
            if ready is None and condition in text:
                ready=time.monotonic();report['town_entry_seen' if a.quest=='town' else 'quest_departure_seen']=True;write()
            if ready is None and elapsed>140:report['failure']='Quest departure not observed';break
            if ready is not None:
                active=time.monotonic()-ready
                if active>=next_shot:
                    send('shot hunt-'+str(int(active)));next_shot+=60
                if active>=a.seconds:
                    if report.get('operator')=='human playtest requested by user':
                        if not report.get('suggested_duration_reached'):
                            report['suggested_duration_reached']=True;write()
                    else:break
            time.sleep(.5)
    except BaseException:
        report['failure']='Session driver interrupted';raise
    finally:
        if proc.poll() is None:
            send('shot hunt-final\nsdlquit')
            try:proc.wait(timeout=20)
            except subprocess.TimeoutExpired:
                proc.terminate();proc.wait(timeout=10);report['failure']=report['failure'] or 'Normal exit timed out'
        text=log();commands=(folder/'control.txt').read_text()
        debug=re.findall(r'^(?:poke|plact|plsweep|emact|emsweep|dummy)\b.*',commands,re.M)
        report.update(exit_code=proc.returncode,wall_seconds=time.monotonic()-start,
            source_saves_unchanged=all(sha(HERE/'test-profile/save/save_0'/n)==v for n,v in report['source_save_hashes'].items()),
            tested_mod_files_unchanged=files(folder/'mods/magnet-spike-experimental')==report['mod_files'],
            debug_gameplay_commands=debug,monster_action_lines=len(re.findall(r'^\[em\]',text,re.M)),
            pin_acquisitions=len(re.findall(r'ms-pin: restrained monster',text)),
            pin_releases=len(re.findall(r'ms-pin: released monster',text)),
            invalid_effect_handles=len(re.findall(r'msfx: invalid|invalid effect handle',text,re.I)),
            fatal='FATAL:' in text,renderer_cache=retire(folder/'cache'))
        report['clean_session']=bool(proc.returncode==0 and not report['failure'] and not report['fatal']
            and report['source_saves_unchanged'] and report['tested_mod_files_unchanged'] and not debug)
        report['all_scenarios_passed']=False
        write()
        profile_lock.seek(0);msvcrt.locking(profile_lock.fileno(),msvcrt.LK_UNLCK,1);profile_lock.close()
        print('Natural hunt ended:',a.label,'clean session:',report['clean_session'],
            'individual lifecycle coverage requires review.',flush=True)


if __name__=='__main__':main()
