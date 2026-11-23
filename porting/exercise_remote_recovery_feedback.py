"""Native recovery with the disposable hunter on GU's nonlocal input path.

This switches only the test actor's local-input flag, then restores it. It is
an isolated native-path reproduction, not a connected multiplayer hunt.
"""
import argparse
import json
import struct
import time
from feedback_session import Session


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    session=Session(args.label,args.baseline)
    original=None
    try:
        session.ready()
        # Read runtime class metadata for the next quick-message investigation.
        dti=session.memory(0x200000+0x189a018-session.player,32)
        vt=struct.unpack_from('<I',dti)[0]
        methods=session.memory(vt-session.player,12)
        session.report['fixed_phrase_dti']={'vtable':hex(vt),
            'methods':[hex(v) for v in struct.unpack('<3I',methods)]}
        original=struct.unpack('<I',session.memory(0x13cc,4))[0]
        session.send('STICK_NEUTRAL 6000\nplact 10 10')
        session.wait(lambda:'msport: action 10 (' in session.log(),15)
        session.send(f'poke {session.player+0x13cc:x} {original&~1:x}')
        time.sleep(7)
        state=session.state()
        case={'nonlocal_input_flag':True,'after':state,
              'exited_weapon_action':state['category']!=0x10,
              'recovery_tail_entered':'ms-recovery: action 10 tail' in session.log(),
              'recovery_tail_completed':'ms-recovery: action 10 ready' in session.log()}
        session.report['cases'].append(case)
        session.report['all_passed']=case['exited_weapon_action'] and case['recovery_tail_completed']
        print(json.dumps(case),flush=True)
    except Exception as exc:
        session.report['failure']=str(exc)
        raise
    finally:
        if original is not None and session.process.poll() is None:
            session.send(f'poke {session.player+0x13cc:x} {original:x}')
            time.sleep(.1)
        session.close()


if __name__=='__main__':main()
