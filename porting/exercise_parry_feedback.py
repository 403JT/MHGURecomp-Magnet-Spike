"""Observe public-release guard/counter exits with and without analog input."""
import argparse
import json
import re
import time

from feedback_session import Session


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--baseline', action='store_true')
    args = p.parse_args()
    session = Session(args.label, args.baseline)
    try:
        session.ready()
        for action, stick in ((14, False), (14, True), (57, False),
                              (112, False), (112, True), (113, False)):
            session.send('STICK_NEUTRAL 1\nplact 1 0')
            time.sleep(.25)
            start = len(session.log())
            session.send(f'plact 10 {action}')
            session.wait(lambda: bool(re.search(r'msport: action ' + str(action) + r' \(', session.log()[start:])))
            if stick:
                time.sleep(.5)
                session.send('STICK_UP 120')
            time.sleep(5)
            state = session.state()
            case = {'action': action, 'stick_during_animation': stick, 'after': state,
                    'exited_weapon_action': state['category'] != 0x10}
            session.report['cases'].append(case)
            session.write()
            print(json.dumps(case), flush=True)
        session.report['all_passed'] = all(c['exited_weapon_action'] for c in session.report['cases'])
    except Exception as exc:
        session.report['failure'] = str(exc)
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
