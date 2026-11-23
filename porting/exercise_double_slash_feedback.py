"""Ordinary R+X entry and stick changes for the reported Double Slash freeze."""
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
    session=Session(args.label,args.baseline)
    try:
        session.ready()
        session.wait(lambda:'magnet gauge 1 bars' in session.log(),20)
        cases=[('standing',0,False,30),('early-stick',15,False,120),
               ('late-stick',70,False,120),('walking',0,True,30),
               ('walking-held-modifier',30,True,180)]
        for name,stick_at,walking,hold in cases:
            session.send('STICK_NEUTRAL 6000\nplact 1 0')
            time.sleep(.3)
            start=len(session.log())
            delay=20 if walking else 0
            commands=[]
            if walking:commands.append('STICK_UP 35')
            commands.extend((f'R {hold} {delay}',f'X 6 {delay+6}'))
            if name!='standing':
                commands.extend((f'STICK_LEFT 30 {delay+stick_at}',
                    f'STICK_RIGHT 30 {delay+stick_at+30}',
                    f'STICK_NEUTRAL 6000 {delay+stick_at+60}'))
            session.send('\n'.join(commands))
            time.sleep(6)
            state=session.state()
            actions=[int(n) for n in re.findall(r'msport: action (\d+) \(',session.log()[start:])]
            result={'case':name,'ordinary_inputs':True,'modifier_hold_frames':hold,
                'actions_started':actions,'double_slash_observed':any(n in (11,135) for n in actions),
                'after':state,'exited_weapon_action':state['category']!=0x10}
            session.report['cases'].append(result);session.write()
            print(json.dumps(result),flush=True)
            if not result['exited_weapon_action']:
                time.sleep(5);result['later_state']=session.state();session.write();break
            # Native passive regeneration replaces the spent bar before the
            # next case. Gauge, damage and eligibility are never edited.
            time.sleep(4)
        session.report['all_passed']=len(session.report['cases'])==len(cases) and all(
            c['double_slash_observed'] and c['exited_weapon_action'] for c in session.report['cases'])
    except Exception as exc:
        session.report['failure']=str(exc);raise
    finally:
        session.close()


if __name__=='__main__':main()
