"""Ordinary movement + evade input on the public Recomp build, muted clones."""
import argparse
import json
import re
import time
from feedback_session import Session
from prepare_frontier import HERE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label',required=True)
    parser.add_argument('--baseline',action='store_true')
    args=parser.parse_args()
    payload=HERE/'backups/before-sprint-roll-1/payload' if args.baseline else None
    s=Session(args.label,args.baseline,payload_root=payload)
    try:
        s.ready()
        # All evade requests below are ordinary button presses, not plact.
        # Reset to neutral only between independent scenarios.
        cases=[('drawn_walk',False,False,'STICK_UP'),
               ('sheathed_walk',True,False,'STICK_UP'),
               ('sheathed_sprint',True,True,'STICK_UP'),
               ('sheathed_sprint_left',True,True,'STICK_LEFT')]
        for name,sheathed,sprint,stick in cases:
            s.send('STICK_NEUTRAL 6000\nplact 1 0')
            time.sleep(.5)
            # Use the native sheathe/draw actions and their completion logs.
            # The current native drawn flag is queried by the existing log.
            if sheathed:
                s.send('Y 8');time.sleep(2)
            elif name!='drawn_walk':
                s.send('X 8');time.sleep(2)
            start=len(s.log())
            s.send(stick+' 180'+ ('\nR 120' if sprint else ''))
            time.sleep(1)
            before=s.state()
            s.send('B 8')
            time.sleep(1.2)
            actions=[(int(cat,16),int(no)) for cat,no in re.findall(r'\[moves\].* do ([0-9a-f]{4}):(\d+) ',s.log()[start:])]
            r_events=re.findall(r'\[control\] R (\d+) at frame (\d+)',s.log()[start:])
            b_events=re.findall(r'\[control\] B \d+ at frame (\d+)',s.log()[start:])
            r_active=bool(r_events and b_events and int(r_events[-1][1])<=int(b_events[-1])<sum(map(int,r_events[-1])))
            expected_action=2 if sprint else 1 if sheathed else 0
            case={'case':name,'weapon_sheathed':sheathed,'sprint_held':sprint,
                'ordinary_evade_button':True,'before':before,'actions':actions,
                'movement_confirmed':before['category']==2 and before['action']==expected_action,
                'sprint_held_at_evade':r_active if sprint else None,
                'after':s.state(),'evade_observed':any(cat==1 and no in (6,7,13,14) for cat,no in actions)}
            s.report['cases'].append(case);s.write();print(json.dumps(case),flush=True)
            s.send('STICK_NEUTRAL 6000');time.sleep(1)
            if sheathed:
                s.send('X 8');time.sleep(2)
        s.report['all_passed']=all(c['evade_observed'] and c['movement_confirmed'] and
            (not c['sprint_held'] or c['sprint_held_at_evade']) for c in s.report['cases'])
    except Exception as exc:
        s.report['failure']=str(exc);raise
    finally:s.close()


if __name__=='__main__':main()
