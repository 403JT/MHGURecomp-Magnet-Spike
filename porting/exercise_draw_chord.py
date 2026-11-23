"""Compare sheathed draw chords and the drawn Magnetic Assault input."""
import argparse
import json
import re
import struct
import time
from feedback_session import Session
from prepare_frontier import HERE


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label',required=True)
    p.add_argument('--public',action='store_true')
    p.add_argument('--alternatives',action='store_true')
    p.add_argument('--guard-only',action='store_true')
    args=p.parse_args()
    payload=HERE/'backups/before-sprint-roll-1/payload' if args.public else None
    s=Session(args.label,payload_root=payload)
    try:
        s.ready()
        cases=(('diagnostic_Impact_draw_79',True,False,False,79),
               ('diagnostic_Magnetic_Assault_12',True,False,False,12)) if args.alternatives else (
            ('sheathed_R_X_A',True,True,False,None),('sheathed_X_A',True,False,False,None),
            ('drawn_R_X_A',False,True,False,None),('walking_sheathed_R_X_A',True,True,True,None))
        if args.guard_only:cases=tuple(c for c in cases if c[0] in ('sheathed_R_X_A','walking_sheathed_R_X_A'))
        for name,sheathed,modifier,walking,diagnostic in cases:
            s.send('STICK_NEUTRAL 6000\nplact 1 0');time.sleep(.5)
            # Every previous case ends drawn; sheathing also resets the form.
            s.send('Y 8');time.sleep(3)
            if not sheathed:s.send('X 8');time.sleep(3)
            time.sleep(11)
            before=s.state()
            table=struct.unpack('<I',s.memory(0x24ac,4))[0]
            start=len(s.log())
            commands=[]
            if walking:commands+=['STICK_UP 65']
            if modifier:commands+=['R 50']
            delay=12 if walking else 6
            commands += [f'X 8 {delay}',f'A 8 {delay}', 'STICK_NEUTRAL 6000 70']
            s.send(f'plact 10 {diagnostic}' if diagnostic is not None else '\n'.join(commands));time.sleep(8)
            text=s.log()[start:];after=s.state()
            case={'name':name,'ordinary_inputs':diagnostic is None,'diagnostic_entry':diagnostic,'sheathed':sheathed,
                'before':before,'before_table':table,
                'indirect_rows':[int(n) for n in re.findall(r'msport: sheathed command (\d+)',text)],
                'weapon_actions':[int(n) for n in re.findall(r'msport: action (\d+) \(',text)],
                'native_actions':[(int(cat,16),int(no)) for cat,no in re.findall(r'\[moves\].* do ([0-9a-f]{4}):(\d+) ',text)],
                'after':after,'after_table':struct.unpack('<I',s.memory(0x24ac,4))[0]}
            s.report['cases'].append(case);s.write();print(json.dumps(case),flush=True)
    except Exception as exc:s.report['failure']=str(exc);raise
    finally:s.close()


if __name__=='__main__':main()
