"""Muted official-runtime checks of the merged release on disposable profiles."""
import argparse
import json
import math
import re
import struct
import time
from exercise_glaive_aim import AimSession
from exercise_glaive_aim_styles import cursor_pixels, style_setup
from exercise_glaive_aim_top_attack import gauge_ready, place_target_once, aim_towards_target
from feedback_session import files
from prepare_combined_release import STAGE, read


def started(text): return [int(n) for n in re.findall(r'msport: action (\d+) \(', text)]


def camp(s, checks):
    for form, expected in (('cutting', 82), ('impact', 84)):
        if form == 'impact': s.send('MINUS 8'); time.sleep(2.5)
        before = s.snapshot(form + '-before')
        start = len(s.log())
        s.send('ZR 150')
        time.sleep(.6)
        aimed = s.snapshot(form + '-aim')
        s.send('A 8')
        time.sleep(4)
        after = s.snapshot(form + '-after')
        checks[form + '_glaive_cursor_visible'] = cursor_pixels(s.folder / 'shots' / (form + '-aim.png')) >= 60
        checks[form + '_normal_camera_without_jump'] = not aimed['camera_aim'] and not aimed['aim_byte'] and math.dist(before['eye'], aimed['eye']) < 1
        checks[form + '_pin_action_starts'] = expected in started(s.log()[start:]) and 'marker shot from ' in s.log()[start:]
        checks[form + '_shot_completes_cursor_clears'] = after['category'] in (1, 2) and cursor_pixels(s.folder / 'shots' / (form + '-after.png')) < 30
    s.send('Y 8'); time.sleep(2.5)
    s.send('X 8'); time.sleep(2.5)
    trials = []
    for frame in (82, 88, 92, 100, 104, 106):
        s.wait(lambda: gauge_ready(s), 25)
        start = len(s.log())
        s.send(f'R 20 0\nX 6 6\nX 6 {frame}\nA 6 {frame}')
        time.sleep(7)
        state = s.state()
        actions = started(s.log()[start:])
        trials.append({'x_a_at_frame': frame, 'actions': actions, 'reached_153': 153 in actions, 'after': state})
        assert not (state['category'] == 16 and state['action'] == 153), 'Reproduced stall on merged build'
        s.report['ordinary_stall_trials'] = trials
        s.write()
        if sum(t['reached_153'] for t in trials) >= 2: break
    checks['ordinary_double_slash_followup_reaches_153'] = sum(t['reached_153'] for t in trials) >= 2
    checks['ordinary_followups_complete_without_stall'] = all(t['after']['category'] in (1, 2) for t in trials if t['reached_153'])
    timelines = []
    for action, end in ((153, 26), (21, 44), (24, 46), (49, 48)):
        s.send('plact 1 0'); time.sleep(.4)
        s.send('plact 10 ' + str(action))
        begin, rows = time.monotonic(), []
        while time.monotonic() - begin < 5:
            p = s.memory(0, 0x600)
            act = s.memory(0x2506, 6)
            rows.append({'t': round(time.monotonic() - begin, 3), 'category': struct.unpack_from('<H', act)[0],
                         'action': struct.unpack_from('<H', act, 4)[0], 'step': p[5],
                         'frame': struct.unpack_from('<f', p, 0x4fc)[0], 'end': struct.unpack_from('<f', p, 0x504)[0]})
        current = [r for r in rows if r['t'] > .2 and r['category'] == 16 and r['action'] == action]
        first = [r for r in current if r['step'] == 1]
        checks[str(action) + '_restored_motion_length'] = bool(first) and {r['end'] for r in first} == {float(end)}
        checks[str(action) + '_advances_to_attack_step'] = any(r['step'] >= 2 for r in current)
        checks[str(action) + '_completes'] = rows[-1]['category'] in (1, 2)
        timelines.append({'action': action, 'expected_first_end': end, 'rows': rows})
        s.report['motion_timelines'] = timelines
        s.write()


def field(s, form, checks):
    if form == 'impact': s.send('MINUS 8'); time.sleep(2.5)
    s.send('STICK_UP 600')
    s.wait(lambda: s.memory(0x1054, 1)[0] not in (0, 255), 25)
    s.send('STICK_NEUTRAL 6000\nL 8')
    time.sleep(.4)
    place_target_once(s)
    time.sleep(1)
    s.send('RSTICK_UP 10\nZR 1800')
    time.sleep(.5)
    start = len(s.log())
    for attempt in range(8):
        before = aim_towards_target(s, attempt)
        s.send('A 8')
        time.sleep(1.4)
        if 'marker shot hit monster' in s.log()[start:]: break
    else: raise RuntimeError('Marker setup did not hit the moving target')
    s.wait(lambda: gauge_ready(s), 25)
    start = len(s.log())
    s.send('X 8')
    time.sleep(.7)
    during = s.snapshot('approach-during')
    time.sleep(7)
    after = s.snapshot('approach-after')
    text = s.log()[start:]
    expected = 58 if form == 'cutting' else 68
    checks['marker_shot_hits'] = True
    checks['aim_top_attack_starts'] = expected in started(text)
    checks['approach_moves_free_hunter'] = math.dist(before['position'], after['position']) > 300
    checks['approach_lands_and_completes'] = f'landed in action {expected}' in text and f'action {expected} done' in text
    checks['camera_finite_and_normal'] = all(r['finite_camera'] and not r['camera_aim'] for r in (before, during, after))
    checks['normal_hunter_hp_no_position_override'] = s.report['test_setup']['hp_before'] < 5000
    s.report['approach'] = {'form': form, 'action': expected, 'movement_m': round(math.dist(before['position'], after['position']) / 100, 2),
                            'after_category': after['category'], 'after_action': after['action']}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--scenario', choices=('camp', 'cutting', 'impact'), required=True)
    p.add_argument('--payload')
    args = p.parse_args()
    payload = args.payload or str(STAGE / 'output/magnet-spike-experimental')
    from pathlib import Path
    s = AimSession(args.label, quest=101 if args.scenario == 'camp' else 404,
                   payload_root=Path(payload), save_setup=style_setup(0))
    checks = {}
    try:
        s.ready()
        if args.scenario == 'camp': camp(s, checks)
        else: field(s, args.scenario, checks)
        checks['all_camera_samples_finite'] = all(c['finite_camera'] for c in s.report['cases'])
        s.report.update(checks=checks, all_passed=all(checks.values()), scenario=args.scenario)
        assert s.report['all_passed'], {k: v for k, v in checks.items() if not v}
    except Exception as exc:
        s.report['failure'] = str(exc)
        s.write()
        raise
    finally: s.close()
    assert not s.report['fatal'] and s.report['exit_code'] == 0
    assert s.report['source_saves_unchanged'] and s.report['tested_payload_unchanged']
    actual = {n: h for n, h in s.report['payload_files'].items() if n.startswith(('exefs/', 'romfs/'))}
    assert actual == read(STAGE / 'build-validation.json')['payload_files']
    proof = {'all_passed': True, 'label': args.label, 'scenario': args.scenario, 'checks': checks,
             'payload_files': actual, 'muted': True, 'original_saves_unchanged': True,
             'runtime_sha256': s.report['runtime_sha256']}
    (STAGE / ('native-' + args.scenario + '.json')).write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, 'scenario': args.scenario, 'checks': checks}))


if __name__ == '__main__': main()
