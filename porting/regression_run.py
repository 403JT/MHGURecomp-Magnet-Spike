"""Run repeatable, isolated gameplay stress tests without touching player progress."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import subprocess
import time

from prepare_frontier import HERE, ROOT


def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    if (HERE/'hold-regressions').exists():
        raise RuntimeError('Queued regressions held while the next candidate is prepared; no game launched')
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--seconds', type=int, default=65)
    parser.add_argument('--quest', type=int, default=101)
    parser.add_argument('--save-run',help='Read a prior disposable session save instead of the baseline copy')
    parser.add_argument('--weapon-id',type=int,help='Equip this type-12 ID in the disposable copy only')
    parser.add_argument('--weapon-level',type=int,default=1,help='Level for --weapon-id in the disposable fixture')
    parser.add_argument('--legacy', action='store_true')
    parser.add_argument('--manual', action='store_true', help='Leave scripted combat to commands appended during this test')
    parser.add_argument('--audio', action='store_true', help='Record the renderer mix and audio voice diagnostics')
    parser.add_argument('--audible', action='store_true', help='Enable device playback only for an intentional listening test')
    parser.add_argument('--sound-sequence', action='store_true', help='Exercise cutting, impact, charge, and magnetic animations')
    parser.add_argument('--wall-shots', action='store_true', help='Schedule normal inputs by wall time, independent of renderer frame rate')
    parser.add_argument('--combat-sounds', action='store_true', help='Quest-404 collision and code-cue playback sequence')
    parser.add_argument('--live', action='store_true', help='Summon an active monster once; do not freeze it or alter its damage')
    parser.add_argument('--summon-distance',type=int,default=240,help='Live-test placement distance in cm')
    parser.add_argument('--pin-sequence', choices=('timeout','cutting','impact'), help='Live-target pin entry and QTE regression (debug attack entry)')
    parser.add_argument('--input-sequence', action='store_true', help='Normal controls: draw, both pin combos and transformation, without debug actions')
    parser.add_argument('--action-sweep', type=int, choices=(0,1), help='Debug-entry smoke test of half the 160 converted actions; does not verify combos or balance')
    parser.add_argument('--guard-sequence', action='store_true', help='Live incoming-hit guard/counter regression, with repeated debug guard entry')
    parser.add_argument('--cross-step',action='store_true',help='Buffer R+top in Impact action 54 and carry it into action 146')
    args = parser.parse_args()
    if not 100<=args.summon_distance<=4000:raise ValueError('Invalid live-test placement distance')
    if args.pin_sequence and (not args.live or args.quest!=404):raise ValueError('Pin sequence requires --live --quest 404')
    if args.guard_sequence and (not args.live or args.quest!=404):raise ValueError('Guard sequence requires --live --quest 404')
    sweep=[]
    cross_frame=0
    if args.cross_step:
        from build_module import MS
        sys.path.insert(0,str(MS/'tools'));import msact
        acts=msact.actions((MS.parents[1]/'dump/mhf/zz/mhfdat.dec.prefix.bin').read_bytes())
        cancel=next(c for c in acts[54]['cancels'] if c['next']==146)
        cross_frame=cancel['buf'][0][3]+3
    if args.action_sweep is not None:
        if args.seconds<335:raise ValueError('An action sweep requires at least 335 seconds')
        from build_module import MS
        sys.path.insert(0,str(MS/'tools'))
        import msact
        acts=msact.actions((MS.parents[1]/'dump/mhf/zz/mhfdat.dec.prefix.bin').read_bytes())
        ids=[n for n,a in enumerate(acts) if a['steps'] and all(k<=2 or m//1000==1 for k,m,*_ in a['steps'])]
        sweep=ids[args.action_sweep*80:(args.action_sweep+1)*80]
    if args.combat_sounds and args.quest!=404:raise ValueError('Combat sound sequence requires quest 404')
    if not re.fullmatch('[a-z0-9_-]+', args.label) or not 10 <= args.seconds <= 600:
        raise ValueError('Invalid test label or duration')
    profile = HERE / 'runs' / args.label
    if profile.exists():
        raise RuntimeError('Test label already exists; evidence will not be overwritten')
    source = HERE/'runs'/args.save_run/'save/save_0' if args.save_run else HERE / 'test-profile/save/save_0'
    if not source.resolve().is_relative_to(HERE.resolve()):raise ValueError('Save source outside the local test workspace')
    original = {name: digest(source / name) for name in ('system', 'system_backup')}
    save = profile / 'save/save_0'
    save.mkdir(parents=True)
    for name in original:
        shutil.copyfile(source / name, save / name)
    if args.weapon_id is not None:
        from build_smithy_tree import audit as tree_audit
        from prepare_test_profile import BOX,WORN,ENTRY,FILE_SIZE
        tables,_,_,_=tree_audit()
        if not 1<=args.weapon_id<len(tables['base'][0]):raise ValueError('Invalid fixture weapon ID')
        row=tables['base'][0][args.weapon_id]
        if not 1<=args.weapon_level<=row[9]+row[10]:raise ValueError('Invalid fixture weapon level')
        for name in original:
            data=bytearray((save/name).read_bytes());assert len(data)==FILE_SIZE
            slot=data[0x2b];assert slot<3 and data[0x28+slot]
            base=0x24+struct.unpack_from('<I',data,0x34+4*slot)[0]
            index=struct.unpack_from('<H',data,base+WORN)[0];assert index<2000
            at=base+BOX+ENTRY*index
            flags=struct.unpack_from('<H',data,at)[0];assert flags&31==12
            struct.pack_into('<HH',data,at,(flags&0xfc00)|12|((args.weapon_level-1)<<5),args.weapon_id)
            (save/name).write_bytes(data)
    shutil.copytree(HERE / 'output/magnet-spike-experimental', profile / 'mods/magnet-spike-experimental')
    if args.legacy:
        shutil.copyfile(HERE / 'backups/revision0-subsdk1', profile / 'mods/magnet-spike-experimental/exefs/subsdk1')
    shutil.copyfile(ROOT / 'MHGURecomp-master/build/pipelines.list', profile / 'pipelines.list')
    cache = profile / 'cache'
    from cache_helpers import seed
    seed(cache)
    (profile / 'mhgurecomp.ini').write_text(
        '[Display]\nMode = Windowed\nResolution = 1280x720\n'
        '[Application]\nConfirmExit = Off\n'
        '[Audio]\nVolume = '+('100' if args.audible else '0')+'\n', encoding='utf-8')
    control = profile / 'control.txt'
    control.write_text('fps 60\n', encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith('MHGU_')}
    env.update({'MHGU_HOME': str(profile), 'MHGU_SAVE_DIR': str(profile / 'save'),
                'MHGU_DATA_DIR': str(ROOT / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
                'MHGU_CONFIG': str(profile / 'mhgurecomp.ini'), 'MHGU_MODS_DIR': str(profile / 'mods'),
                'MHGU_HIDDEN': '1', 'MHGU_QUICKHUNT': str(args.quest), 'MHGU_LDN_SERVER': 'Off',
                'MHGU_PAD_PATH': '__isolated_regression_no_physical_controller__',
                'MHGU_CONTROL': str(control), 'MHGU_LOG_MOVES': '1',
                # Device gain is applied after raw WAV capture. Sound analysis
                # can therefore remain silent on the user's speakers.
                'MHGU_AUDIO_GAIN':'1' if args.audible else '0'})
    if args.quest != 101 and not args.live:
        env.update({'MHGU_DUMMY': '240', 'MHGU_DUMMY_FACE': '1'})
    if args.live:env.update({'MHGU_SUMMON':str(args.summon_distance),'MHGU_SUMMON_FREE':'1'})
    if args.audio:
        env.update({'MHGU_AUDIO_WAV': str(profile / 'audio.wav')})
    if args.combat_sounds:env['MHGU_KOTRACE']='1'
    console = (profile / 'console.log').open('wb')
    process = subprocess.Popen([str(ROOT / 'MHGURecomp-master/build/mhgurecomp.exe')], cwd=profile, env=env,
                               stdout=console, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    console.close()
    info = {'pid': process.pid, 'profile': str(profile), 'seconds': args.seconds, 'quest': args.quest,
            'legacy': args.legacy, 'module_sha256': digest(profile / 'mods/magnet-spike-experimental/exefs/subsdk1')}
    info['test_mode'] = ('cross-step-input' if args.cross_step else 'incoming-guard' if args.guard_sequence else 'action-sweep-'+str(args.action_sweep) if args.action_sweep is not None else 'normal-pin-combos' if args.input_sequence else 'pin-'+args.pin_sequence if args.pin_sequence else 'combat-sounds' if args.combat_sounds else 'debug-sound-sequence' if args.sound_sequence else 'wall-shots' if args.wall_shots
                         else 'manual' if args.manual else 'frame-shots')
    info['live_monster']=args.live
    info['fixture_weapon_id']=args.weapon_id
    info['fixture_weapon_level']=args.weapon_level if args.weapon_id is not None else None
    info['save_source_run']=args.save_run
    info['output_muted']=not args.audible
    info['mod_files'] = {str(p.relative_to(profile / 'mods/magnet-spike-experimental')): digest(p)
                         for p in (profile / 'mods/magnet-spike-experimental').rglob('*') if p.is_file()}
    (profile / 'run.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in info.items() if k!='mod_files'}), flush=True)

    def log():
        path = profile / 'log.txt'
        return path.read_text(encoding='utf-8', errors='replace') if path.exists() else ''

    def send(commands):
        with control.open('a', encoding='utf-8') as f:
            f.write(commands + '\n')

    ready, failure = False, None
    try:
        deadline = time.monotonic() + 100
        while process.poll() is None and time.monotonic() < deadline:
            text = log()
            if 'msport: hunter stats:' in text:
                ready = True
                break
            if 'FATAL:' in text:
                failure = 'startup fatal'
                break
            time.sleep(0.5)
        if not ready:
            failure = failure or 'quest startup did not complete'
        else:
            print('Quest ready; stress interval started.', flush=True)
            if not args.manual and not args.cross_step and not args.guard_sequence and not sweep and not args.input_sequence and not args.pin_sequence and not args.sound_sequence and not args.wall_shots and not args.combat_sounds:
                # Draw, then hold aim. Separate trigger presses give the shot
                # animation time to finish; the active shot is replaced in flight.
                # The first player update precedes the quest-intro input unlock.
                send('X 8 300\nZR ' + str(args.seconds * 60 - 480) + ' 420\n' +
                     '\n'.join('A 8 ' + str(450 + n * 120) for n in range(max(1, (args.seconds - 10) // 2))))
            deadline = time.monotonic() + args.seconds
            start = time.monotonic()
            last_draw = last_shot = -10.0
            aim_sent = False
            pin_entered=pin_attack=False
            impact_origin_ready=False
            pin_press_time=-1.0
            pin_press_count=0
            pin_qte_scheduled=False
            pin_capture_at=None
            pin_record=None
            pin_sampled=False
            input_stage=0
            input_stage_time=0
            sweep_index=0
            sweep_pending=False
            sweep_ack_count=0
            sweep_next_at=10.0
            guard_entered=False
            guard_at=-10.0
            guard_hits_seen=0
            guard_retry_at=0
            guard_hit_offset=0
            guard_raced_epochs=set()
            guard_sent=0
            cross_stage=0
            # Debug action entry deliberately isolates cue timing from command
            # buffering. It supplements the separate normal-input shot test.
            sequence = [(6, 'plact 10 0'), (9, 'plact 10 1'), (13, 'plact 10 2'),
                        (18, 'plact 10 20'), (23, 'plact 10 21'), (28, 'plact 10 34\nA 140'),
                        (35, 'plact 10 35'), (40, 'plact 10 82'), (47, 'plact 10 84'),
                        (54, 'plact 10 57'), (61, 'plact 10 77'), (70, 'plact 10 0')]
            if args.combat_sounds:
                sequence=[(6,'STICK_UP 350'),(18,'dummy 240 180\nX 2'),
                          (24,'plact 10 0'),(28,'plact 10 6'),(32,'plact 10 12'),
                          (36,'plact 10 18'),(40,'plact 10 32'),(44,'plact 10 34\nA 140'),
                          (51,'plact 10 35'),(59,'plact 10 105'),(69,'plact 10 159'),
                          (77,'plact 10 95'),(85,'plact 10 157'),(98,'plact 10 0'),
                          (104,'plact 10 18'),(110,'plact 10 35'),(118,'shot sound-combat')]
            while process.poll() is None and time.monotonic() < deadline:
                if args.cross_step:
                    elapsed=time.monotonic()-start;current=log()
                    if elapsed>=6 and 'weapon in hand (joint' not in current and elapsed-last_draw>=3:
                        send('X 8');last_draw=elapsed
                    if cross_stage==0 and elapsed>=20 and 'weapon in hand (joint' in current:
                        send('R 240\nplact 10 54');cross_stage=1
                    if cross_stage==1:
                        m=re.search(r'msport: state action 16/54 step 1 motion \d+ frame (\d+)',current)
                        if m:
                            send('X 8 '+str(max(6,cross_frame-int(m[1]))));cross_stage=2
                if args.guard_sequence:
                    elapsed=time.monotonic()-start;current=log()
                    if elapsed>=6 and 'weapon in hand (joint' not in current and elapsed-last_draw>=3:
                        send('X 2');last_draw=elapsed
                    if not guard_entered and 'weapon in hand (joint' in current:
                        send('STICK_UP 550');guard_entered=True
                    guard_ack=len(re.findall(r'\[moves\] plact [0-9a-f]+ 0010:014 ',current))
                    guard_hits=len(re.findall('msport: guarded hit',current))
                    counter=bool(re.search(r'msport: action (57|76|77) \(',current) or
                                 re.search(r'\[moves\] \d+ pl [0-9a-f]+ (?:do|is) 0010:0(?:57|76|77) ',current))
                    counter_damage=bool(re.search(r'msport: hit .*in action (?:57|76|77)\b',current))
                    if guard_hits>guard_hits_seen:
                        guard_hits_seen=guard_hits;guard_hit_offset=current.rfind('msport: guarded hit')
                        guard_retry_at=elapsed+3
                        # Exercise the X counter itself; a simultaneous A can
                        # cancel it into a later combo before its damage window.
                        send('X 8 20\nshot guard-contact-'+str(guard_hits))
                    # A CLI restart already queued when the AI hit arrived can
                    # run afterward and clear gc_hits. Retry only that diagnosed
                    # test interference. A completed counter that missed a live
                    # moving target can also receive another genuine AI attack,
                    # after six seconds of recovery. The hit gate stays strict.
                    raced=guard_hits and bool(re.search(r'\[moves\] \d+ pl [0-9a-f]+ do 0010:014 ',current[guard_hit_offset:]))
                    if raced:guard_raced_epochs.add(guard_hits)
                    missed_counter=counter and not counter_damage and elapsed>=guard_retry_at+3
                    retry=not guard_hits or (raced and elapsed>=guard_retry_at) or missed_counter
                    if ('summoned the large monster' in current and not counter_damage and (not counter or missed_counter) and retry
                            and guard_ack>=guard_sent and elapsed-guard_at>=.18):
                        # Keep the early guard window available for a real AI
                        # attack; never overwrite multiple pending CLI actions.
                        send('plact 10 14');guard_at=elapsed;guard_sent+=1
                if sweep:
                    elapsed=time.monotonic()-start
                    current=log()
                    if sweep_pending:
                        token=r'\[moves\] plact [0-9a-f]+ 0010:'+str(sweep[sweep_index]).zfill(3)+r' '
                        if len(re.findall(token,current))>sweep_ack_count:
                            sweep_index+=1;sweep_pending=False;sweep_next_at=elapsed+4
                    if not sweep_pending and sweep_index<len(sweep) and elapsed>=sweep_next_at:
                        token=r'\[moves\] plact [0-9a-f]+ 0010:'+str(sweep[sweep_index]).zfill(3)+r' '
                        sweep_ack_count=len(re.findall(token,current))
                        send('plact 10 '+str(sweep[sweep_index]));sweep_pending=True
                    if sweep_index==len(sweep) and elapsed>=sweep_next_at:break
                if args.input_sequence:
                    elapsed=time.monotonic()-start;current=log()
                    if elapsed>=6 and 'weapon in hand (joint' not in current and elapsed-last_draw>=3:
                        send('X 2');last_draw=elapsed
                    if input_stage==0 and elapsed>=28 and 'weapon in hand (joint' in current:
                        send('R 180\nX 8 6');input_stage=1
                    elif input_stage==1 and 'msport: state action 16/11 step 1 ' in current:
                        send('X 8 55\nA 8 55');input_stage=2
                    elif input_stage==2 and 'msport: action 97 (Cutting)' in current:
                        input_stage=3;input_stage_time=elapsed
                    elif input_stage==3 and elapsed-input_stage_time>=5:
                        send('MINUS 2');input_stage=4;input_stage_time=elapsed
                    # The preceding Cutting combo spent two bars. Refill two
                    # before Impact's first attack and its costed pin cancel.
                    elif input_stage==4 and elapsed-input_stage_time>=12:
                        send('R 240\nX 8 6');input_stage=5
                    elif input_stage==5 and 'msport: state action 16/39 step 2 ' in current:
                        send('X 8 30\nA 8 30');input_stage=6
                if args.pin_sequence:
                    elapsed=time.monotonic()-start
                    current=log()
                    if elapsed>=6 and 'weapon in hand (joint' not in current and elapsed-last_draw>=3:
                        send('X 2');last_draw=elapsed
                    if not pin_entered and 'weapon in hand (joint' in current:
                        send('STICK_UP 550');pin_entered=True
                    if not pin_attack and 'summoned the large monster' in current:
                        # Impact's source action 39 records the origin (event 40)
                        # before its shared Cutting-form leap 94. Entering 94
                        # directly omits that event and tests the wrong finisher.
                        send('plact 10 '+('39' if args.pin_sequence=='impact' else '97'));pin_attack=True
                    if args.pin_sequence=='impact' and pin_attack and not impact_origin_ready and 'msport: action 39 (Impact)' in current:
                        send('plact 10 94');impact_origin_ready=True
                    restraint=re.search(r'ms-pin: restrained monster ([0-9a-f]+) owner ([0-9a-f]+)',current)
                    if restraint and pin_capture_at is None:
                        pin_capture_at=elapsed
                        monster=int(restraint[1],16);hunter=int(restraint[2],16)
                        send(f'memsave {monster+0x1428:x} 4 pin-record.bin\n'
                             f'memsave {hunter+0x13d6:x} 2 pin-hunter-hp.bin\nshot pin-start')
                    ptr_path=profile/'pin-record.bin'
                    if pin_capture_at is not None and pin_record is None and ptr_path.exists():
                        pin_record=struct.unpack('<I',ptr_path.read_bytes())[0]
                        send(f'memsave {pin_record+0x40:x} 20 pin-position-start.bin\n'
                             f'memsave {pin_record+0x398:x} 4 pin-rate-start.bin')
                    if pin_record and not pin_sampled and elapsed-pin_capture_at>=1.0:
                        send(f'memsave {pin_record+0x40:x} 20 pin-position-held.bin\n'
                             f'memsave {pin_record+0x398:x} 4 pin-rate-held.bin\nshot pin-held')
                        pin_sampled=True
                    if args.pin_sequence!='timeout' and not pin_qte_scheduled and 'msport: state action 16/99 ' in current:
                        # Wall-time polling and PNG encoding can collapse or
                        # delay individual CLI presses. Schedule real alternating
                        # button edges on presented frames, beyond the four-tick
                        # QTE cooldown. Do not edit the QTE state or threshold.
                        send('\n'.join(('X' if n%2==0 else 'A')+' 2 '+str(n*6) for n in range(24)))
                        pin_qte_scheduled=True
                if args.wall_shots:
                    elapsed = time.monotonic() - start
                    current = log()
                    drawn = 'weapon in hand (joint' in current
                    if not drawn and elapsed >= 6 and elapsed-last_draw >= 3:
                        send('X 2');last_draw=elapsed
                    if drawn and not aim_sent:
                        send('ZR 60000');aim_sent=True
                    if aim_sent and 'aim view on' in current and elapsed-last_shot >= 2:
                        send('A 2');last_shot=elapsed
                if args.sound_sequence or args.combat_sounds:
                    while sequence and time.monotonic() - start >= sequence[0][0]:
                        send(sequence.pop(0)[1])
                if 'FATAL:' in log():
                    failure = 'runtime fatal'
                    break
                time.sleep(0.1 if args.pin_sequence or args.guard_sequence else 0.5)
            if process.poll() is None and not failure:
                send('shot stress-end')
                time.sleep(0.5)
    finally:
        if process.poll() is None:
            send('sdlquit')
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                failure = failure or 'normal exit timed out'
                process.terminate()  # only this test's own child handle
                process.wait(timeout=10)
    text = log()
    info.update({'quest_ready': ready, 'exit_code': process.returncode, 'failure': failure,
                 'sound_posts': len(re.findall('ms-sound: post', text)),
                 'sound_files_loaded': len(re.findall(r'ms-sound: file [0-9a-f]+ loaded [1-9a-f][0-9a-f]*', text)),
                 'collision_sounds': len(re.findall(r'ms-sound: collision',text)),
                 'fatal': 'FATAL:' in text,
                 'invalid_effect_handles': len(re.findall('invalid: handle', text)),
                 'effect_reposts': len(re.findall('ended by itself: re-posted', text)),
                 'marker_shots': len(re.findall('marker shot from', text)),
                 'dummy_hits': len(re.findall(r'\[dummy\] hit:', text)),
                 'pin_restraints':len(re.findall('ms-pin: restrained',text)),
                 'pin_releases':len(re.findall('ms-pin: released',text)),
                 'pin_successes':len(re.findall('pin QTE success',text)),
                 'pin_timeouts':len(re.findall('pin over ',text)),
                 'guarded_hits':len(re.findall('msport: guarded hit',text)),
                 'ko_hits':len(re.findall(r'\[ko\].*hit: KO ',text)),
                 'ko_starts':len(re.findall(r'\[ko\].*KO started:',text)),
                 'source_saves_unchanged': original == {name: digest(source / name) for name in original}})
    from effect_checks import lifetime_checks
    info.update(lifetime_checks(text))
    if args.pin_sequence:
        files=['pin-position-start.bin','pin-position-held.bin','pin-rate-start.bin','pin-rate-held.bin','pin-hunter-hp.bin']
        if all((profile/n).exists() for n in files):
            a,b=[(profile/n).read_bytes() for n in files[:2]]
            info['pin_target_position_held']=a[:12]==b[:12]
            info['pin_animation_paused']=all(struct.unpack('<f',(profile/n).read_bytes())[0]==0 for n in files[2:4])
            info['pin_hunter_hp']=struct.unpack('<h',(profile/files[4]).read_bytes())[0]
    if args.pin_sequence and not failure:
        if info['pin_restraints']<1 or info['pin_releases']!=info['pin_restraints']:failure='pin was not acquired and released'
        elif args.pin_sequence=='timeout' and info['pin_timeouts']<1:failure='pin timeout not exercised'
        elif args.pin_sequence!='timeout' and info['pin_successes']<1:failure='pin success not exercised'
        elif args.pin_sequence=='impact' and 'msport: state action 16/157 ' not in text:failure='Impact finisher was not exercised'
        elif args.pin_sequence=='cutting' and 'msport: state action 16/105 ' not in text:failure='Cutting finisher was not exercised'
        info['failure']=failure
    if args.input_sequence and not failure:
        info['normal_pin_combos']={str(n):bool(re.search(r'msport: action '+str(n)+r' \(',text)) for n in (11,97,90,39,94)}
        if not all(info['normal_pin_combos'].values()):info['failure']=failure='normal pin combo path was not completed'
    if args.guard_sequence and not failure:
        info['guard_followup_attempts']=guard_hits_seen
        info['guard_debug_restart_races']=len(guard_raced_epochs)
        info['guard_counter_hits']=len(re.findall(r'msport: hit .*in action (?:57|76|77)\b',text))
        if not info['guarded_hits']:info['failure']=failure='no incoming hit was guarded'
        elif not (re.search(r'msport: action (57|76|77) \(',text) or
                  re.search(r'\[moves\] \d+ pl [0-9a-f]+ (?:do|is) 0010:0(?:57|76|77) ',text)):
            info['failure']=failure='guard counter follow-up was not exercised'
        elif not info['guard_counter_hits']:
            info['failure']=failure='guard counter damage was not exercised'
    if args.cross_step and not failure:
        info['cross_step_followup']='msport: action 146 (Impact)' in text
        if not info['cross_step_followup']:info['failure']=failure='the buffered Impact follow-up did not survive its animation step'
    if sweep:
        seen={int(n) for n in re.findall(r'msport: action (\d+) \(',text)}
        info['action_sweep_requested']=sweep;info['action_sweep_missing']=sorted(set(sweep)-seen)
        info['action_sweep_coverage']='Debug action start and up to four seconds playback; not combo/collision fidelity'
        if info['action_sweep_missing']:info['failure']=failure='some requested actions did not start'
    if not args.manual and not args.cross_step and not args.guard_sequence and not sweep and not args.input_sequence and not args.pin_sequence and not args.sound_sequence and not args.combat_sounds and not failure and info['marker_shots'] < max(1, (args.seconds - 12) // 3):
        info['failure'] = failure = 'script did not exercise enough marker shots'
    from cache_helpers import retire
    info['renderer_cache']=retire(cache)
    (profile / 'run.json').write_text(json.dumps(info, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in info.items() if k!='mod_files'}, indent=2), flush=True)
    return int(bool(failure) or bool(info['fatal']) or process.returncode != 0 or not info['source_saves_unchanged'])


if __name__ == '__main__':
    raise SystemExit(main())
