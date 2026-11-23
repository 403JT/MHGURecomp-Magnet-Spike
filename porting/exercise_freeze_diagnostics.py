"""Official-runtime smoke test for the separate observational diagnostic build."""
import json
import argparse
import re
import struct
import time
from feedback_session import Session
from prepare_frontier import HERE


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--label',required=True);args=p.parse_args()
    s=Session(args.label,payload_root=HERE/'output/freeze-diagnostics/magnet-spike-experimental')
    try:
        s.ready();s.wait(lambda:'magnet gauge 1 bars' in s.log(),20)
        s.send('R 40\nX 8 6');time.sleep(6)
        s.report['ordinary_R_X']={'started':'msport: action 11 (' in s.log(),
            'input_logged':'ms-freeze: input' in s.log(),'after':s.state()}
        s.send('Y 8');time.sleep(3)
        start=len(s.log());s.send('R 180\nSTICK_UP 240');time.sleep(1)
        sprint=s.state();s.send('B 8');time.sleep(1.5)
        text=s.log()[start:]
        s.report['sprint_roll']={'before':sprint,
            'sprinting':sprint['category']==2 and sprint['action']==2,
            'native_evade_observed':bool(re.search(r'\[moves\].* do 0001:(?:006|013|014) ',text))}
        s.send('STICK_NEUTRAL 6000');time.sleep(3)
        table=struct.unpack('<I',s.memory(0x24ac,4))[0]
        start=len(s.log());s.send('R 40\nX 8 6\nA 8 6');time.sleep(6)
        text=s.log()[start:];after=s.state()
        s.report['guard_draw']={'before_table':table,'ordinary_inputs':True,
            'Impact_guard_observed':'msport: action 112 (Impact)' in text,
            'legacy_GS_guard_absent':not re.search(r'\[moves\].* do 0020:',text),
            'after':after,'drawn_table':struct.unpack('<I',s.memory(0x24ac,4))[0]}
        s.report['all_passed']=(s.report['ordinary_R_X']['started'] and s.report['ordinary_R_X']['input_logged']
            and s.report['ordinary_R_X']['after']['category']!=16
            and s.report['sprint_roll']['sprinting'] and s.report['sprint_roll']['native_evade_observed']
            and table==1000 and s.report['guard_draw']['Impact_guard_observed']
            and s.report['guard_draw']['legacy_GS_guard_absent']
            and after['category']!=16 and s.report['guard_draw']['drawn_table']==2000)
    except Exception as exc:
        s.report['failure']=str(exc);raise
    finally:s.close()
    print(json.dumps({k:v for k,v in s.report.items() if k not in ('payload_files','cases')}))
    assert s.report['all_passed'] and s.report['source_saves_unchanged'] and not s.report['fatal']


if __name__=='__main__':main()
