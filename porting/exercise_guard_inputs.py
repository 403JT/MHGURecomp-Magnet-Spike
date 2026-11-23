"""Public Recomp guard exits using ordinary guard buttons and stick changes."""
import argparse
import json
import re
import time

from feedback_session import Session


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--baseline', action='store_true')
    args = parser.parse_args()
    session = Session(args.label, args.baseline)
    try:
        session.ready()
        for action in (14, 112):
            # Set the form through its real action handler, then let it finish.
            session.send(f'STICK_NEUTRAL 6000\nplact 10 {action}')
            time.sleep(4)
            for hold, stick_delay in ((8, 0), (8, 15), (8, 65), (180, 15), (180, 65)):
                session.send('STICK_NEUTRAL 6000\nplact 1 0')
                time.sleep(.3)
                start = len(session.log())
                session.send(f'R {hold}\nZR {hold}\nSTICK_LEFT 30 {stick_delay}\n'
                             f'STICK_RIGHT 30 {stick_delay + 30}\n'
                             f'STICK_NEUTRAL 6000 {stick_delay + 60}')
                time.sleep(6)
                log = session.log()[start:]
                state = session.state()
                observed = bool(re.search(r'msport: action ' + str(action) + r' \(', log))
                case = {'action': action, 'guard_button_hold_frames': hold,
                        'stick_start_frame': stick_delay,
                        'ordinary_guard_input_observed': observed, 'after': state,
                        'exited_weapon_action': state['category'] != 0x10}
                session.report['cases'].append(case)
                session.write()
                print(json.dumps(case), flush=True)
        session.report['all_passed'] = all(c['ordinary_guard_input_observed'] and
            c['exited_weapon_action'] for c in session.report['cases'])
    except Exception as exc:
        session.report['failure'] = str(exc)
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
