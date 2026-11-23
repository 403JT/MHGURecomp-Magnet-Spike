"""Controlled marker collision checks on official 0.18.0, muted/cloned save.

Uses Recomp's built-in held-monster fixture, never a gameplay release feature.
The hunter is free; target placement/motion is controlled, so this is not a hunt.
"""
import argparse
import json
import re
import struct
import time
from exercise_glaive_aim import AimSession
from prepare_glaive_aim_build import STAGE


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    args = p.parse_args()
    s = AimSession(args.label, quest=404, dummy_distance=1200,
                   payload_root=STAGE / 'output/magnet-spike-experimental')
    checks = {}
    try:
        s.ready()
        s.send('STICK_UP 600')
        s.wait(lambda: s.memory(0x1054, 1)[0] not in (0, 255), 25)
        s.send('STICK_NEUTRAL 6000\nL 8')
        time.sleep(1.3)
        # The normal camera begins looking down ~10 degrees. Raise the view
        # with normal right-stick input so the centre cursor meets the target.
        s.send('RSTICK_UP 10')
        time.sleep(.7)
        for form, action in (('cutting', 82), ('impact', 84)):
            if form == 'impact':
                s.send('MINUS 8')
                time.sleep(2.5)
            hits = 0
            for attempt in range(3):
                start = len(s.log())
                s.send('ZR 150')
                time.sleep(.6)
                s.snapshot(f'{form}-target-{attempt}')
                s.send('A 8')
                time.sleep(3.0)
                text = s.log()[start:]
                hit = 'marker shot hit monster' in text
                hits += hit
                s.report.setdefault('shots', []).append({'form': form, 'attempt': attempt,
                    'expected_action': action, 'actions': [int(x) for x in re.findall(r'msport: action (\d+) \(', text)],
                    'hit': hit, 'missed': 'marker shot missed' in text,
                    'directions': re.findall(r'marker shot from .*?direction (-?\d+) (-?\d+) (-?\d+) / 1000', text)})
                time.sleep(.7)
                s.write()
            checks[form + '_marker_hits'] = hits >= 2
            checks[form + '_shot_actions_correct'] = all(action in q['actions'] for q in s.report['shots'] if q['form'] == form)
        after = s.snapshot('target-test-finished')
        checks['native_fixture_loaded'] = 'training dummy' in s.log().lower() or '[dummy]' in s.log()
        checks['all_camera_samples_finite'] = all(c['finite_camera'] for c in s.report['cases'])
        checks['normal_camera_after_shots'] = after['camera_aim'] == after['aim_byte'] == 0
        checks['returned_to_normal_action'] = after['category'] in (1, 2)
        s.report.update(checks=checks, all_passed=all(checks.values()),
            scope='Controlled held Volvidon, ordinary ZR+A shots in both forms; hunter free, official 0.18.0, muted copied save')
        assert s.report['all_passed'], {n: v for n, v in checks.items() if not v}
    except Exception as exc:
        s.report['failure'] = str(exc)
        s.write()
        raise
    finally:
        s.close()
    assert s.report['exit_code'] == 0 and not s.report['fatal']
    assert s.report['tested_payload_unchanged'] and s.report['source_saves_unchanged']
    (STAGE / 'native-target-validation.json').write_text(json.dumps({
        'all_passed': True, 'run': args.label, 'checks': checks, 'shots': s.report['shots'],
        'payload_files': s.report['payload_files'], 'scope': s.report['scope']}, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run': args.label, 'checks': checks, 'shots': s.report['shots']}))


if __name__ == '__main__': main()
