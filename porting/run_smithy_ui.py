"""Muted disposable town session, driven through the runtime's control API."""
import argparse,json,os,shutil,subprocess,time
from prepare_frontier import HERE,ROOT,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--seconds',type=int,default=600)
    p.add_argument('--approach',action='store_true',help='Repeat the observed Bherna smithy approach on the copied slot-3 hunter')
    p.add_argument('--save-run',help='Reload a prior disposable session instead of the baseline copy')
    a=p.parse_args()
    if not a.label.replace('-','').replace('_','').isalnum() or not 10<=a.seconds<=1800:raise ValueError('Invalid session')
    dest=HERE/'runs'/a.label
    if dest.exists():raise RuntimeError('Evidence session already exists')
    source=(HERE/'runs'/a.save_run/'save/save_0') if a.save_run else HERE/'test-profile/save/save_0'
    if not source.resolve().is_relative_to(HERE.resolve()):raise ValueError('Save source outside local test workspace')
    before={n:sha(source/n) for n in ('system','system_backup')}
    save=dest/'save/save_0';save.mkdir(parents=True)
    for n in before:shutil.copyfile(source/n,save/n)
    shutil.copytree(HERE/'output/magnet-spike-experimental',dest/'mods/magnet-spike-experimental')
    shutil.copyfile(ROOT/'MHGURecomp-master/build/pipelines.list',dest/'pipelines.list')
    from cache_helpers import seed,retire
    seed(dest/'cache')
    config=dest/'mhgurecomp.ini';config.write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n[Application]\nConfirmExit = Off\n[Audio]\nVolume = 0\n',encoding='utf-8')
    control=dest/'control.txt';control.write_text('fps 60\n',encoding='utf-8')
    env={k:v for k,v in os.environ.items() if not k.startswith('MHGU_')}
    env.update({k:str(v) for k,v in {'MHGU_HOME':dest,'MHGU_DATA_DIR':ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data',
        'MHGU_SAVE_DIR':dest/'save','MHGU_CONFIG':config,'MHGU_MODS_DIR':dest/'mods','MHGU_CONTROL':control,
        'MHGU_QUICKHUNT':'town','MHGU_HIDDEN':1,'MHGU_AUDIO_GAIN':0,'MHGU_LDN_SERVER':'Off',
        'MHGU_PAD_PATH':'__isolated_smithy_no_controller__','MHGU_LOG_MOVES':1}.items()})
    report={'output_muted':True,'mod_files':{str(f.relative_to(dest/'mods/magnet-spike-experimental')):sha(f)
        for f in (dest/'mods/magnet-spike-experimental').rglob('*') if f.is_file()}}
    with (dest/'console.log').open('wb') as log:
        process=subprocess.Popen([str(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')],cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
        report['pid']=process.pid;(dest/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        print('Muted disposable town session:',a.label,'PID',process.pid,flush=True)
        if a.approach:
            deadline=time.monotonic()+100
            while process.poll() is None and time.monotonic()<deadline:
                log_path=dest/'log.txt'
                if log_path.exists() and '[quickhunt] in town' in log_path.read_text(encoding='utf-8',errors='replace'):
                    with control.open('a',encoding='utf-8') as f:
                        f.write('STICK_UP 90\nSTICK_LEFT 35\nSTICK_LEFT 65 100\nSTICK_UP 145 180\n'
                            'STICK_UPLEFT 240 340\nSTICK_UPLEFT 180 595\nSTICK_UP 100 790\nA 5 910\n')
                    print('Replaying observed approach to Bherna smithy.',flush=True);break
                time.sleep(.25)
        try:process.wait(timeout=a.seconds)
        except subprocess.TimeoutExpired:
            with control.open('a',encoding='utf-8') as f:f.write('sdlquit\n')
            try:process.wait(timeout=30)
            except subprocess.TimeoutExpired:process.terminate();process.wait(timeout=10)
    report.update({'exit_code':process.returncode,'source_saves_unchanged':before=={n:sha(source/n) for n in before},
        'renderer_cache':retire(dest/'cache')})
    (dest/'run.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Town session ended:',report['exit_code'],'source saves unchanged:',report['source_saves_unchanged'])
if __name__=='__main__':main()
