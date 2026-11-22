"""Test the release ZIP through an unmodified official runtime, muted and isolated."""
import argparse,json,os,re,shutil,struct,subprocess,time,zipfile
from prepare_frontier import HERE,ROOT,sha
from hunt_session import files
from prepare_test_profile import BOX,ENTRY,BOX_COUNT,FILE_SIZE


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--pristine',action='store_true');a=p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.label)
    folder=HERE/'runs'/a.label
    if folder.exists():raise RuntimeError('Test evidence already exists')
    folder.mkdir()
    runtime=HERE/'release-validation/runtime-0.18.0/Windows-MHGURecomp'
    exe=runtime/'mhgurecomp.exe'
    archive=HERE/'public-release/v0.1.0-alpha.1/dist/Magnet-Spike-v0.1.0-alpha.1.zip'
    manifest=json.loads((archive.parent/'release-manifest.json').read_text())
    if sha(archive)!=manifest['downloads'][archive.name]['sha256']:raise RuntimeError('Release ZIP changed')
    mods=folder/'mods';mods.mkdir()
    with zipfile.ZipFile(archive) as z:
        for i in z.infolist():
            if not (mods/i.filename).resolve().is_relative_to(mods.resolve()):raise RuntimeError('Unsafe ZIP entry')
        z.extractall(mods)
    mod=mods/'Magnet-Spike'
    payload={k.replace('\\','/'):v for k,v in files(mod).items() if k.startswith(('exefs','romfs'))}
    assert payload==manifest['payload_files']
    source=(ROOT/'MHGURecomp-master/build/couch-smoke/player1/save/save_0') if a.pristine else HERE/'test-profile/save/save_0'
    original={n:sha(source/n) for n in ('system','system_backup')}
    save=folder/'save/save_0';save.mkdir(parents=True)
    for n in original:shutil.copyfile(source/n,save/n)
    data=(save/'system').read_bytes();assert len(data)==FILE_SIZE
    counts=[]
    for slot in range(3):
        if not data[0x28+slot]:continue
        base=0x24+struct.unpack_from('<I',data,0x34+slot*4)[0]
        counts.append(sum(struct.unpack_from('<H',data,base+BOX+ENTRY*i)[0]&31==12 for i in range(BOX_COUNT)))
    if a.pristine:assert not any(counts),'Pristine fixture already contains Magnet Spike gear'
    config=folder/'mhgurecomp.ini'
    config.write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n[Application]\nConfirmExit = Off\n[Audio]\nVolume = 0\n',encoding='utf-8')
    control=folder/'control.txt';control.write_text('fps 60\n',encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.startswith('MHGU_')}
    env.update(MHGU_HOME=str(folder),MHGU_SAVE_DIR=str(folder/'save'),MHGU_CONFIG=str(config),
        MHGU_MODS_DIR=str(mods),MHGU_DATA_DIR=str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
        MHGU_HIDDEN='1',MHGU_AUDIO_GAIN='0',MHGU_PAD_PATH='__isolated_release_test__',
        MHGU_LDN_SERVER='Off',MHGU_CONTROL=str(control),MHGU_LOG_MOVES='1',
        MHGU_QUICKHUNT='town' if a.pristine else '101')
    report={'runtime':'official MHGURecomp 0.18.0 Windows x64','runtime_executable_sha256':sha(exe),
        'release_zip_sha256':sha(archive),'payload_files':payload,'pristine_unmodified_save_fixture':a.pristine,
        'source_save_hashes':original,'fixture_Magnet_Spike_counts':counts,'output_muted':True,
        'normal_builtin_mod_loader':True,'failure':None,'source_save_edited':False}
    report_path=folder/'public-release-run.json'
    def write():report_path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def read():
        f=folder/'log.txt';return f.read_text(errors='replace') if f.exists() else ''
    def send(s):
        with control.open('a',encoding='utf-8') as f:f.write(s+'\n')
    write()
    with (folder/'console.log').open('wb') as output:
        proc=subprocess.Popen([str(exe)],cwd=folder,env=env,stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    report['pid']=proc.pid;write();started=time.monotonic();ready=None;last_draw=-10;last_press=-1;shot=False
    try:
        while proc.poll() is None:
            text=read();elapsed=time.monotonic()-started
            if 'FATAL:' in text:report['failure']='Native fatal';break
            marker='[quickhunt] in town' if a.pristine else 'msport: hunter stats:'
            if ready is None and marker in text:ready=time.monotonic()
            if ready is None and elapsed>180:report['failure']='Native ready condition not seen';break
            if ready is not None:
                active=time.monotonic()-ready
                if active>=8 and not shot:send('shot public-release-ready');shot=True
                if a.pristine:
                    if active>=18:break
                else:
                    if 'weapon in hand (joint' not in text and active>=7 and active-last_draw>=3:
                        send('X 8');last_draw=active
                    if 'weapon in hand (joint' in text and active-last_press>=.17:
                        send('A 3');last_press=active
                    if active>=32:break
            time.sleep(.05)
    finally:
        if proc.poll() is None:
            send('shot public-release-final\nsdlquit')
            try:proc.wait(timeout=25)
            except subprocess.TimeoutExpired:
                proc.terminate();proc.wait(timeout=10);report['failure']=report['failure'] or 'Normal exit timed out'
        text=read();actions={int(x) for x in re.findall(r'msport: action (\d+) \(',text)}
        source_same=all(sha(source/n)==v for n,v in original.items())
        checks={'normal_exit':proc.returncode==0 and not report['failure'],
            'no_fatal':'FATAL:' not in text,'source_saves_unchanged':source_same,
            'release_payload_unchanged':payload=={k.replace('\\','/'):v for k,v in files(mod).items() if k.startswith(('exefs','romfs'))},
            'module_started':'msport: forge label appended' in text,
            'normal_mod_loader_saw_romfs':bool(re.search(r'\[mods\].*Magnet-Spike.*romfs',text)),
            'ready_condition_seen':ready is not None,'muted':env['MHGU_AUDIO_GAIN']=='0'}
        if a.pristine:checks['no_preinjected_weapon']=not any(counts)
        else:checks.update(normal_three_hit_combo={6,9,10}<=actions,
            finisher_recovery='ms-recovery: command action 10' in text or 'ms-recovery: action 10 tail' in text)
        report.update(exit_code=proc.returncode,wall_seconds=time.monotonic()-started,
            checks=checks,all_passed=all(checks.values()),actions_seen=sorted(actions),
            fatal='FATAL:' in text,source_saves_unchanged=source_same)
        write();print(json.dumps({k:v for k,v in report.items() if k not in ('payload_files','source_save_hashes')},indent=2),flush=True)
    assert report['all_passed'],report['checks']


if __name__=='__main__':main()
