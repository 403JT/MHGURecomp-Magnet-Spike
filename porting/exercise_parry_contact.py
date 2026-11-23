"""Check genuine incoming guard contacts, followed by untouched recovery.

Repeated debug guard entry is a contact fixture, not normal-hunt evidence.
Only a contact with no later queued restart is accepted for the exit check.
"""
import argparse
import json
import re
import time
from feedback_session import Session


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--baseline', action='store_true')
    p.add_argument('--instrumented', action='store_true')
    args = p.parse_args()
    session = Session(args.label, args.baseline, quest=404, live=True, instrumented=args.instrumented)
    try:
        session.ready()
        # A quest starts in camp. Leave it with ordinary movement before the
        # placement helper can find an active hunt area.
        session.send('STICK_UP 550')
        session.wait(lambda: 'summoned the large monster' in session.log(), 25)
        session.send('STICK_NEUTRAL 1')
        print('Live monster placement observed; checking real guard contacts.', flush=True)
        for action in (14, 112):
            start = len(session.log())
            until = time.monotonic() + 95
            last_request = 0
            contact = None
            while time.monotonic() < until and session.process.poll() is None:
                text = session.log()[start:]
                hits = list(re.finditer('msport: guarded hit', text))
                if hits:
                    index = hits[-1].start()
                    # A restart queued before the contact may consume the next
                    # update. Exclude that epoch instead of treating it as a bug.
                    time.sleep(.25)
                    after = session.log()[start + index:]
                    if not re.search(r'\[moves\].*(?:do|plact).*0010:' + f'{action:03}', after):
                        contact = start + index
                        break
                    start += index + len('msport: guarded hit')
                if time.monotonic() - last_request >= .4:
                    session.send(f'plact 10 {action}')
                    last_request = time.monotonic()
                time.sleep(.05)
            if contact is None:
                session.report['cases'].append({'action': action, 'contact_observed': False})
                session.write()
                print(f'No accepted contact for {action}', flush=True)
                continue
            session.send('STICK_NEUTRAL 1')
            time.sleep(6)
            state = session.state()
            after = session.log()[contact:]
            result = {'action': action, 'contact_observed': True, 'after': state,
                'counter_or_reaction_started': bool(re.search(r'msport: action (57|76|77|113) \(', after)),
                'exited_weapon_action': state['category'] != 0x10}
            session.report['cases'].append(result)
            session.write()
            print(json.dumps(result), flush=True)
        session.report['all_passed'] = all(c.get('contact_observed') and c.get('exited_weapon_action')
            for c in session.report['cases'])
    except Exception as exc:
        session.report['failure'] = str(exc)
        raise
    finally:
        session.close()


if __name__ == '__main__':
    main()
