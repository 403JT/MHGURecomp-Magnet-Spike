"""Muted official-runtime sharpness and normal-item check in disposable saves."""
import argparse,json,os,re,shutil,struct,subprocess,time
from prepare_frontier import HERE,ROOT,sha
from prepare_test_profile import BOX,WORN,ENTRY,FILE_SIZE
from build_smithy_tree import audit,entries,table
from hunt_session import files


def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True)
    p.add_argument('--source-run');p.add_argument('--weapon-id',type=int);p.add_argument('--level',type=int)
    p.add_argument('--sharpen',action='store_true');a=p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+',a.label)
    folder=HERE/'runs'/a.label
    if folder.exists():raise RuntimeError('Evidence already exists')
    folder.mkdir();save=folder/'save/save_0';save.mkdir(parents=True)
    source=HERE/'runs'/a.source_run/'save/save_0' if a.source_run else HERE/'test-profile/save/save_0'
    assert source.resolve().is_relative_to(HERE.resolve())
    original={n:sha(source/n) for n in ('system','system_backup')}
    tables,*_=audit();brows=tables['base'][0];rows=tables['level'][0]
    kire,_=table(entries('nativeNX/loc/arc/resident.arc'),'kireajiData',14)
    whet=json.loads((HERE/'reports/hunt-fixture-item-identities.json').read_text())['Whetstone']
    fixture=None
    for name in original:
        data=bytearray((source/name).read_bytes());assert len(data)==FILE_SIZE
        slot=data[0x2b];base=0x24+struct.unpack_from('<I',data,0x34+slot*4)[0]
        ix=struct.unpack_from('<H',data,base+WORN)[0];at=base+BOX+ix*ENTRY
        flags,ident=struct.unpack_from('<HH',data,at);assert flags&31==12
        lv=((flags>>5)&31)+1
        if a.weapon_id is not None:
            ident=a.weapon_id;lv=a.level
            assert 0<ident<len(brows) and 1<=lv<=brows[ident][9]+brows[ident][10]
            struct.pack_into('<HH',data,at,(flags&0xfc00)|12|((lv-1)<<5),ident)
        # Skills and supplies are controlled only inside this test copy.
        struct.pack_into('<7H',data,base+WORN,ix,*([65535]*6))
        data[base+0x27bf:base+0x27bf+76]=(whet|(20<<12)).to_bytes(76,'little')
        (save/name).write_bytes(data)
        fixture={'weapon_id':ident,'level':lv,'equipped_record_changed':a.weapon_id is not None,
            'copied_armor_unequipped':True,'copied_pouch':'20 ordinary Whetstones, no other items'}
    row=next(r for r in rows if r[4:6]==bytes((ident,lv)))
    maximum=min(450,150+25*row[7]);thresholds=struct.unpack('<7H',kire[row[6]])
    colour=next(i for i,n in enumerate(thresholds) if n>=maximum)
    mod=HERE/'output/magnet-spike-experimental';expected=files(mod)
    shutil.copytree(mod,folder/'mods/Magnet-Spike')
    config=folder/'mhgurecomp.ini';config.write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n[Application]\nConfirmExit = Off\n[Audio]\nVolume = 0\n',encoding='utf-8')
    control=folder/'control.txt';control.write_text('fps 60\n',encoding='utf-8')
    exe=HERE/'release-validation/runtime-0.18.0/Windows-MHGURecomp/mhgurecomp.exe'
    assert sha(exe)=='286be3af1fe5aee7649bb548c33d550b8d52e97f931eafc9db6d6c030d6571b7'
    env={k:v for k,v in os.environ.items() if not k.startswith('MHGU_')}
    env.update(MHGU_HOME=str(folder),MHGU_SAVE_DIR=str(folder/'save'),MHGU_CONFIG=str(config),
        MHGU_DATA_DIR=str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
        MHGU_MODS_DIR=str(folder/'mods'),MHGU_QUICKHUNT='404' if a.sharpen else '101',
        MHGU_HIDDEN='1',MHGU_AUDIO_GAIN='0',MHGU_LDN_SERVER='Off',MHGU_LOG_MOVES='1',
        MHGU_PAD_PATH='__isolated_sharpness_test__',MHGU_CONTROL=str(control))
    if a.sharpen:env.update(MHGU_DUMMY='240',MHGU_DUMMY_FACE='1')
    report={'fixture':fixture,'runtime':'official Windows MHGURecomp 0.18.0','runtime_sha256':sha(exe),
        'mod_files':expected,'source_save_hashes':original,'output_muted':True,
        'expected_maximum':maximum,'expected_colour':colour,'samples':{},'failure':None,'all_passed':False,
        'scope':'Native load of copied equipment; optional real training-target collision and normal Y-button Whetstone use. No live sharpness fields are edited.'}
    receipt=folder/'sharpness-native.json'
    def write():receipt.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    def send(cmd):
        with control.open('a',encoding='utf-8') as f:f.write(cmd+'\n')
    def read():
        q=folder/'log.txt';return q.read_text(errors='replace') if q.exists() else ''
    def wait_for(test,seconds=30):
        until=time.monotonic()+seconds
        while proc.poll() is None and time.monotonic()<until:
            if 'FATAL:' in read():raise RuntimeError('Native fatal')
            value=test()
            if value:return value
            time.sleep(.1)
        raise RuntimeError('Native condition timed out')
    def sample(label):
        path=folder/(label+'.bin');cpath=folder/(label+'-colour.bin')
        send(f'memsave {player+0x2774:x} 8 {path.name}\nmemsave {player+0x13f0:x} 4 {cpath.name}')
        wait_for(lambda:path.exists() and path.stat().st_size==8 and cpath.exists() and cpath.stat().st_size==4,10)
        current,cap=struct.unpack('<II',path.read_bytes());c=struct.unpack('<I',cpath.read_bytes())[0]
        out={'current':current,'maximum':cap,'colour':c};report['samples'][label]=out;write();return out
    write()
    with (folder/'console.log').open('wb') as output:
        proc=subprocess.Popen([str(exe)],cwd=folder,env=env,stdout=output,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
    started=time.monotonic()
    try:
        wait_for(lambda:'msport: hunter stats:' in read(),180)
        player=int(re.findall(r'msport: class 5 object ([0-9a-f]+)',read())[-1],16)
        time.sleep(7)
        first=sample('quest-start');send('shot sharpness-start')
        assert first=={'current':maximum,'maximum':maximum,'colour':colour},first
        print('Native starting sharpness verified:',fixture,first,flush=True)
        if a.sharpen:
            send('STICK_UP 350');time.sleep(13);send('STICK_NEUTRAL 2000');time.sleep(3)
            send('dummy 240 180\nX 8');time.sleep(3)
            reduced=None
            for attempt in range(8):
                send('dummy 200 180\nplact 10 12');time.sleep(3)
                value=sample('after-hit-'+str(attempt))
                if value['current']<maximum:reduced=value;break
            if reduced is None:raise RuntimeError('No native sharpness loss from the collision fixture')
            send('Y 8');time.sleep(4)
            # A copied save may retain the "No Item" selection. Cycle using
            # normal controls so the sole finite pouch item is selected.
            send('wheel -1');time.sleep(2)
            send('shot whetstone-selected\nY 8');time.sleep(1);send('shot whetstone-use')
            for attempt in range(18):
                time.sleep(1);value=sample('sharpen-'+str(attempt))
                if value['current']==maximum:break
            else:raise RuntimeError('Normal Whetstone use did not restore full sharpness')
            report['native_loss_and_recovery']={'before':reduced,'after':value,'normal_item_buttons':'Y to sheathe, mouse wheel to select the sole pouch item, Y to use Whetstone'}
            send('shot sharpness-restored');time.sleep(1)
    except Exception as error:report['failure']=str(error)
    finally:
        if proc.poll() is None:
            send('sdlquit')
            try:proc.wait(timeout=25)
            except subprocess.TimeoutExpired:proc.terminate();proc.wait(timeout=10);report['failure']=report['failure'] or 'Normal exit timed out'
        report['exit_code']=proc.returncode;report['wall_seconds']=time.monotonic()-started
        report['checks']={'normal_exit':proc.returncode==0 and not report['failure'],
            'correct_starting_sharpness':report['samples'].get('quest-start')=={'current':maximum,'maximum':maximum,'colour':colour},
            'no_fatal':'FATAL:' not in read(),'source_saves_unchanged':all(sha(source/n)==v for n,v in original.items()),
            'candidate_unchanged':files(folder/'mods/Magnet-Spike')==expected==files(mod),'muted':True}
        if a.sharpen:report['checks']['normal_whetstone_restored_lost_sharpness']='native_loss_and_recovery' in report
        report['all_passed']=all(report['checks'].values());write()
        print(json.dumps({k:v for k,v in report.items() if k not in ('mod_files','source_save_hashes','samples')},indent=2),flush=True)
    assert report['all_passed'],report['failure'] or report['checks']


if __name__=='__main__':main()
