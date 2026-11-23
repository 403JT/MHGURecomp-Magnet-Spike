"""Native cancellation probe for pending Shock attacks in a disposable profile."""
import argparse
import json
import re
import struct
import time
from feedback_session import Session
from prepare_frontier import HERE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    baseline=HERE/'backups/before-feedback-2/candidate-payload' if args.baseline else None
    session=Session(args.label,args.baseline,payload_root=baseline)
    try:
        session.ready()
        for action in (159,160,161,162):
            session.send('STICK_NEUTRAL 6000\nplact 1 0')
            time.sleep(.25)
            start=len(session.log())
            session.send(f'plact 10 {action}')
            session.wait(lambda:'Magnetic Shock 5 x 3' in session.log()[start:],15)
            session.send('plact 1 6')
            session.wait(lambda:bool(re.search(r'\[moves\].* do 0001:006 ',session.log()[start:])),10)
            cancel=session.log().rfind(' do 0001:006 ')
            time.sleep(.1)
            slots=session.memory(0x3020,0x170)
            time.sleep(1)
            after=session.log()[cancel:]
            case={'action':action,'cancel':'native common roll request',
                'armed_hits_after_cancel':[int(h) for h in re.findall(r'msport: armed hit (\d+)',after)],
                'slot_live_timers_after_cancel':[struct.unpack_from('<f',slots,i*0xb8+0x60)[0] for i in range(2)],
                'slot_active_bytes_after_cancel':[slots[i*0xb8+5] for i in range(2)],
                'after':session.state()}
            case['no_future_attack_arming']=not case['armed_hits_after_cancel']
            case['no_live_attack_slots']=not any(case['slot_active_bytes_after_cancel'])
            session.report['cases'].append(case);session.write()
            print(json.dumps(case),flush=True)
        session.report['all_passed']=all(c['no_future_attack_arming'] and c['no_live_attack_slots'] for c in session.report['cases'])
    except Exception as exc:
        session.report['failure']=str(exc);raise
    finally:session.close()


if __name__=='__main__':main()
