"""Natural Cutting inputs against a live monster, with animation diagnostics.

Instrumented Recomp only places the live monster once; hunter HP and position
are free. Inputs and read-only samples drive the remainder of this fixture.
"""
import argparse
import json
import re
import time

from feedback_session import Session


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    session=Session(args.label,args.baseline,quest=404,live=True,instrumented=True)
    try:
        session.ready()
        session.send('STICK_UP 550')
        session.wait(lambda:'summoned the large monster' in session.log(),25)
        session.send('STICK_NEUTRAL 6000\nL 2')
        time.sleep(.4)
        for stage in range(5):
            start=len(session.log())
            # Face-button links and the advancing double slash, with stick
            # reversals while the animations and cancel windows are active.
            session.send('X 6\nX 6 30\nX 6 60\nX 6 100\nA 6 100\n'
                'R 12 150\nX 6 152\nSTICK_UP 25 15\nSTICK_LEFT 25 40\n'
                'STICK_RIGHT 25 65\nSTICK_DOWN 20 90\nSTICK_NEUTRAL 6000 110')
            time.sleep(9)
            state=session.state()
            log=session.log()[start:]
            case={'stage':stage,'after':state,
                'started_weapon_actions':[int(n) for n in re.findall(r'msport: action (\d+) \(',log)],
                'incoming_hit_reactions':len(re.findall('msport: hit into 64/',log)),
                'outgoing_hit_callbacks':len(re.findall(r'msport: hit \d+',log)),
                'invalid_step_observed':'ms-feedback: invalid step' in log,
                'exited_weapon_action':state['category']!=0x10}
            session.report['cases'].append(case)
            session.write()
            print(json.dumps(case),flush=True)
            if not case['exited_weapon_action']:
                time.sleep(6)
                case['later_state']=session.state()
                session.write()
                break
        session.report['all_passed']=len(session.report['cases'])==5 and all(
            c['exited_weapon_action'] and not c['invalid_step_observed'] for c in session.report['cases'])
    except Exception as exc:
        session.report['failure']=str(exc)
        raise
    finally:
        session.close()


if __name__=='__main__':main()
