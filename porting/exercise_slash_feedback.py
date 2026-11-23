"""Observe Cutting attack exits while changing the movement stick.

Debug action entry isolates animation handling; this is not a normal-combo or
multiplayer play test. Every case stops before another debug action is issued.
"""
import argparse
import json
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
        for action in (0, 1, 2, 3, 6, 7, 8, 9, 10, 11, 12, 16, 48, 49, 51, 78, 107, 108):
            session.send('STICK_NEUTRAL 6000\nplact 1 0')
            time.sleep(.2)
            start = len(session.log())
            session.send(f'plact 10 {action}\nSTICK_UP 20 12\nSTICK_LEFT 20 32\n'
                         'STICK_DOWN 20 52\nSTICK_RIGHT 20 72\nSTICK_NEUTRAL 6000 92')
            time.sleep(5)
            state = session.state()
            case = {'action': action, 'stick_changed_during_animation': True,
                    'handler_started': f'msport: action {action} (' in session.log()[start:],
                    'after': state, 'exited_weapon_action': state['category'] != 0x10}
            session.report['cases'].append(case)
            session.write()
            print(json.dumps(case), flush=True)
            if not case['exited_weapon_action']:
                # Observe the failure again before resetting, to distinguish a
                # softlock from a single late sample of an ordinary animation.
                time.sleep(5)
                case['ten_second_state'] = session.state()
                session.write()
                print(json.dumps(case), flush=True)
                break
        session.report['all_passed'] = len(session.report['cases']) == 18 and all(
            c['handler_started'] and c['exited_weapon_action'] for c in session.report['cases'])
    except Exception as exc:
        session.report['failure'] = str(exc)
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
