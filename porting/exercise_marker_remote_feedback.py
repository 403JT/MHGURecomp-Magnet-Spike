"""Native marker tracking while the test actor uses GU's remote-input path.

This is a disposable single-runtime diagnostic, not connected multiplayer.
Measures the actual native effect against the marked bone after target moves.
"""
import argparse
import json
import math
import re
import struct
import time
from feedback_session import Session
from prepare_frontier import HERE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--baseline',action='store_true')
    parser.add_argument('--local',action='store_true')
    args=parser.parse_args()
    payload=HERE/'backups/before-feedback-2/candidate-payload' if args.baseline else None
    s=Session(args.label,args.baseline,quest=404,instrumented=True,dummy_distance=800,payload_root=payload)
    original=None
    try:
        s.ready()
        s.send('shot starting-area')
        if s.memory(0x1054,1)[0] in (0,255):s.send('STICK_UP 550')
        s.wait(lambda:s.memory(0x1054,1)[0] not in (0,255),60)
        s.send('STICK_NEUTRAL 6000\ndummy 800 180\nL 2\nZR 6000 12')
        time.sleep(2)
        start=len(s.log())
        for attempt in range(12):
            s.send('A 8');time.sleep(1.2)
            if 'marker shot hit monster' in s.log()[start:]:break
            if attempt in (2,5):s.send('RSTICK_DOWN 8')
        else:raise RuntimeError('No marker hit from ordinary ZR+A')
        hit=re.findall(r'marker shot hit monster ([0-9a-f]+).*joint (\d+)',s.log())[-1]
        monster,joint=int(hit[0],16),int(hit[1])
        proxy=int(re.findall(r'mhf carrier 32 .*: ([0-9a-f]+)',s.log())[-1],16)
        def mem(address,size):return s.memory(address-s.player,size)
        def word(address):return struct.unpack('<I',mem(address,4))[0]
        def vec(address):return struct.unpack('<3f',mem(address,12))
        ids,js=word(monster+0x498),word(monster+0x494)
        matrix=js+mem(ids+joint,1)[0]*0xa0+0x10
        effect=word(proxy+0x150)
        if not effect:raise RuntimeError('Marker effect was not created')
        before=vec(effect+0x40)
        # Bone translation is sufficient for this held-pose translation test.
        origin=vec(matrix+0x30)
        s.send('ZR 0\nSTICK_NEUTRAL 6000')
        time.sleep(.5)
        if not args.local:
            original=word(s.player+0x13cc)
            s.send(f'poke {s.player+0x13cc:x} {original&~1:x}')
        if not args.baseline:
            # Inspect only our own module's state and ARM struct layout. This
            # tracks its current handle across native effect expiry/reposts.
            from build_module import symbols
            from test_marker_feedback import Marker,compile_test
            layout=Marker(compile_test())
            size,carrier,local,joint_offset=[layout.call('test_marker_layout',i) for i in range(4)]
            base=int(re.findall(r'subsdk1 at ([0-9a-f]+)',s.log())[0],16)
            state_base=base+symbols((HERE/'output/magnet-spike.elf').read_bytes())['s_state']
            states=mem(state_base,size*5)
            index=next(i for i in range(5) if struct.unpack_from('<I',states,i*size)[0]==s.player)
            state_address=state_base+size*index
        schedule=((900,180),(900,90),(900,0),(900,270),(1200,180)) if args.local else ((900,180),(850,180),(925,180),(1200,180))
        for distance,turn in schedule:
            s.send(f'dummy {distance} {turn}');time.sleep(1)
            now=vec(matrix+0x30)
            expected=[before[k]+now[k]-origin[k] for k in range(3)]
            if not args.baseline:
                state=mem(state_address,size)
                proxy=struct.unpack_from('<I',state,carrier)[0]
                effect=word(proxy+0x150)
                if not effect:raise RuntimeError('Current marker proxy has no native effect')
                # Reconstruct the intended target from the real saved local
                # hit point and the real current bone matrix, including yaw.
                point=struct.unpack_from('<3f',state,local)
                mat=struct.unpack('<16f',mem(matrix,64))
                expected=[sum(point[j]*mat[j*4+k] for j in range(3))+mat[12+k] for k in range(3)]
            actual=vec(effect+0x40)
            error=math.dist(expected,actual)
            case={'distance_cm':distance,'turn_degrees':turn,'nonlocal_input_path':not args.local,
                  'target_translation_cm':math.dist(origin,now),
                  'effect_error_cm':error,'tracks_target':error<10}
            s.send(f'shot marker-case-{len(s.report["cases"])}')
            s.report['cases'].append(case);s.write();print(json.dumps(case),flush=True)
        s.report['all_passed']=all(c['tracks_target'] for c in s.report['cases']) and any(c['target_translation_cm']>50 for c in s.report['cases'])
        s.report['diagnostic_only']=True
    except Exception as exc:
        s.report['failure']=str(exc);raise
    finally:
        if original is not None and s.process.poll() is None:
            s.send(f'poke {s.player+0x13cc:x} {original:x}');time.sleep(.1)
        s.close()


if __name__=='__main__':main()
