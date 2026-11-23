"""Test the released ZIP's aim + top-face attack and shoulder transition.

Public official runtime, muted, disposable saves. The target is placed once
using control-file data writes; hunter HP/position are never overridden.
"""
import argparse
import hashlib
import json
import math
import re
import struct
import time
import zipfile
from pathlib import Path
from exercise_glaive_aim import AimSession
from feedback_session import files
from prepare_frontier import HERE

RELEASE = HERE.parent / 'Alpha 3 Glaive aim'
WORK = HERE / 'aim-dev/alpha3-glaive-aim-1'


def extract(label):
    manifest = json.loads((RELEASE / 'release-manifest.json').read_text(encoding='utf-8'))
    archive = RELEASE / 'Magnet-Spike-v0.1.0-alpha.3-glaive-aim.zip'
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['downloads'][archive.name]['sha256']
    dest = WORK / ('extracted-' + label)
    if dest.exists(): raise RuntimeError('Extracted test folder already exists')
    dest.mkdir()
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():
            if name.endswith('/'): continue
            target = (dest / name).resolve()
            assert target.is_relative_to(dest.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    payload = dest / 'Magnet-Spike'
    assert {n: h for n, h in files(payload).items() if n.startswith(('exefs/', 'romfs/'))} == manifest['payload_files']
    return payload, manifest


def actions(text): return [int(n) for n in re.findall(r'msport: action (\d+) \(', text)]


def gauge_ready(s):
    bars = re.findall(r'msport: magnet gauge (\d+) bars', s.log())
    return bool(bars) and int(bars[-1]) >= 1


def shoulder_case(s, form):
    s.wait(lambda: gauge_ready(s), 25)
    before = s.snapshot(form + '-shoulder-before')
    start = len(s.log())
    s.send('ZR 40')
    time.sleep(.4)
    aimed = s.snapshot(form + '-shoulder-aim')
    # Release the aim trigger naturally, then the literal shoulder R+X chord.
    time.sleep(.5)
    s.send('R 45\nX 8 6')
    time.sleep(4.5)
    after = s.snapshot(form + '-shoulder-after')
    # Frontier msact.IDLE[7] routes R1+top to 11 (Cutting) / 39 (Impact).
    expected = 11 if form == 'cutting' else 39
    observed = actions(s.log()[start:])
    return {'input': 'Aim with ZR; release; shoulder R + top face X', 'form': form,
            'expected_action': expected, 'actions': observed,
            'started_expected': expected in observed, 'returned_to_neutral': after['category'] in (1, 2),
            'camera_finite': all(c['finite_camera'] for c in (before, aimed, after))}


def target_info(s):
    mgr = struct.unpack('<I', s.absolute(0x1a51fe0, 4))[0]
    pointers = struct.unpack('<10I', s.absolute(mgr + 0x1c, 40))
    for monster in pointers:
        if not monster: continue
        record = struct.unpack('<I', s.absolute(monster + 0x1428, 4))[0]
        if not record: continue
        if struct.unpack('<H', s.absolute(record + 0x1b6, 2))[0] >= 10000: continue
        return monster, record
    raise RuntimeError('No large monster available')


def target_pose(s):
    _, record = target_info(s)
    return struct.unpack('<3f', s.absolute(record + 0x40, 12))


def place_target_once(s):
    monster, record = target_info(s)
    body = s.memory(0x40, 32)
    x, y, z = struct.unpack_from('<3f', body)
    qx, qy, qz, qw = struct.unpack_from('<4f', body, 16)
    fx, fz = 2 * (qx * qz + qw * qy), 1 - 2 * (qx * qx + qy * qy)
    zone = s.memory(0x1054, 1)[0]
    old_zone_word = struct.unpack('<I', s.absolute(monster + 0x1054, 4))[0]
    coords = (x + 3200 * fx, y, z + 3200 * fz)
    commands = []
    for i, value in enumerate(coords):
        word = struct.unpack('<I', struct.pack('<f', value))[0]
        commands.append(f'poke {record + 0x40 + i * 4:x} {word:08x}')
    commands.append(f'poke {monster + 0x1054:x} {(old_zone_word & ~255) | zone:08x}')
    s.send('\n'.join(commands))
    s.report['test_setup'] = {'monster_placed_once_cm': 3200, 'hunter_position_overridden': False,
        'hunter_hp_overridden': False, 'runtime_summon_fixture_disabled': True,
        'hp_before': struct.unpack('<H', s.memory(0x13d6, 2))[0]}
    s.write()


def aim_towards_target(s, number):
    view = s.snapshot('servo-' + str(number))
    t = target_pose(s)
    d = [b - a for a, b in zip(view['eye'], view['look_at'])]
    wanted = [t[0] - view['look_at'][0], t[1] + 120 - view['look_at'][1], t[2] - view['look_at'][2]]
    yaw = math.atan2(wanted[0], wanted[2]) - math.atan2(d[0], d[2])
    yaw = (yaw + math.pi) % (2 * math.pi) - math.pi
    pitch = math.atan2(wanted[1], math.hypot(wanted[0], wanted[2])) - math.atan2(d[1], math.hypot(d[0], d[2]))
    if abs(yaw) > .08:
        s.send('RSTICK_' + ('LEFT' if yaw > 0 else 'RIGHT') + ' ' + str(min(20, max(1, round(abs(yaw) / .043)))))
    if abs(pitch) > .035:
        s.send('RSTICK_' + ('UP' if pitch > 0 else 'DOWN') + ' ' + str(min(10, max(1, round(abs(pitch) / .018)))))
    time.sleep(.45)
    return view


def audit_shoulder(label, run):
    assert re.fullmatch('[a-z0-9_-]+', run)
    report = json.loads((HERE / 'runs' / run / 'feedback-native.json').read_text(encoding='utf-8'))
    manifest = json.loads((RELEASE / 'release-manifest.json').read_text(encoding='utf-8'))
    assert report['exit_code'] == 0 and not report['fatal']
    assert report['source_saves_unchanged'] and report['tested_payload_unchanged'] and report['muted']
    assert report['failure'] == "{'impact_shoulder_started': False}", report['failure']
    assert {n: h for n, h in report['payload_files'].items() if n.startswith(('exefs/', 'romfs/'))} == manifest['payload_files']
    # Correct the test's erroneous Impact expectation against the existing
    # source mapping msact.IDLE[7] = (11, 39), without rewriting raw evidence.
    checks = {}
    for case in report['attack_cases']:
        form = case['form']
        expected = 11 if form == 'cutting' else 39
        checks[form + '_starts_correct_attack'] = expected in case['actions']
        checks[form + '_finishes_normally'] = case['returned_to_neutral']
        checks[form + '_camera_finite'] = case['camera_finite']
    assert len(checks) == 6 and all(checks.values())
    proof = {'all_passed': True, 'run': run, 'checks': checks,
             'test_expectation_correction': 'Impact idle R+X is action39, not135; native run already executed39 and returned to neutral',
             'raw_evidence_unchanged': True, 'release_files_changed': False,
             'module_sha256': manifest['payload_files']['exefs/subsdk1']}
    (WORK / ('attack-' + label + '.json')).write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--shoulder-only', action='store_true')
    p.add_argument('--form', choices=('cutting', 'impact'), default='cutting')
    p.add_argument('--audit-shoulder-run')
    args = p.parse_args()
    if args.audit_shoulder_run:
        audit_shoulder(args.label, args.audit_shoulder_run)
        return
    payload, manifest = extract(args.label)
    s = AimSession(args.label, quest=101 if args.shoulder_only else 404, payload_root=payload)
    checks, cases = {}, []
    try:
        s.ready()
        if args.shoulder_only:
            for form in ('cutting', 'impact'):
                if form == 'impact': s.send('MINUS 8'); time.sleep(2.5)
                case = shoulder_case(s, form)
                cases.append(case)
                checks[form + '_shoulder_started'] = case['started_expected']
                checks[form + '_shoulder_completed'] = case['returned_to_neutral'] and case['camera_finite']
        else:
            if args.form == 'impact': s.send('MINUS 8'); time.sleep(2.5)
            s.send('STICK_UP 600')
            s.wait(lambda: s.memory(0x1054, 1)[0] not in (0, 255), 25)
            s.send('STICK_NEUTRAL 6000\nL 8')
            time.sleep(.4)
            place_target_once(s)
            time.sleep(1.0)
            s.send('RSTICK_UP 10\nZR 1800')
            time.sleep(.5)
            start = len(s.log())
            for attempt in range(8):
                before = aim_towards_target(s, attempt)
                s.send('A 8')
                time.sleep(1.4)
                if 'marker shot hit monster' in s.log()[start:]: break
            else: raise RuntimeError('No ordinary marker hit in the live-target setup')
            s.wait(lambda: gauge_ready(s), 30)
            start = len(s.log())
            s.send('X 8')
            time.sleep(.7)
            during = s.snapshot(args.form + '-attract-during')
            time.sleep(7)
            after = s.snapshot(args.form + '-attract-after')
            text = s.log()[start:]
            expected = 58 if args.form == 'cutting' else 68
            observed = actions(text)
            moved = math.dist(before['position'], after['position'])
            case = {'input': 'Right trigger ZR held + top face X, attached marker and one bar', 'form': args.form,
                    'expected_action': expected, 'actions': observed, 'moved_cm': moved,
                    'landing_actions': re.findall(r'landed in action (\d+)', text),
                    'before': before, 'during': during, 'after': after}
            cases.append(case)
            checks['marker_hit_from_ordinary_input'] = True
            checks['attraction_started'] = expected in observed
            checks['approach_moved_hunter'] = moved > 300
            checks['approach_finished'] = after['category'] in (1, 2, 64)
            checks['camera_remains_finite'] = all(c['finite_camera'] for c in (before, during, after))
            checks['normal_camera_used'] = not during['camera_aim'] and not after['camera_aim']
            checks['hunter_not_fixed_by_runtime'] = s.report['test_setup']['hp_before'] < 5000 and moved > 300
        s.report.update(attack_cases=cases, checks=checks, all_passed=all(checks.values()))
        assert s.report['all_passed'], {n: v for n, v in checks.items() if not v}
    except Exception as exc:
        s.report['failure'] = str(exc)
        s.write()
        raise
    finally:
        s.close()
    assert s.report['exit_code'] == 0 and not s.report['fatal']
    assert s.report['source_saves_unchanged'] and s.report['tested_payload_unchanged']
    assert {n: h for n, h in s.report['payload_files'].items() if n.startswith(('exefs/', 'romfs/'))} == manifest['payload_files']
    proof = {'all_passed': True, 'run': args.label, 'checks': checks, 'cases': cases,
             'release_version': manifest['version'], 'module_sha256': manifest['payload_files']['exefs/subsdk1'],
             'muted': True, 'source_saves_unchanged': True, 'release_files_changed': False}
    (WORK / ('attack-' + args.label + '.json')).write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'run': args.label, 'checks': checks, 'cases': [{k: v for k, v in c.items() if k not in ('before', 'during', 'after')} for c in cases]}))


if __name__ == '__main__': main()
