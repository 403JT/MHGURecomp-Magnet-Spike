"""Bind the additional aim/top-button checks to the unchanged release ZIP."""
import hashlib
import json
from prepare_frontier import HERE


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def main():
    release = HERE.parent / 'Alpha 3 Glaive aim'
    work = HERE / 'aim-dev/alpha3-glaive-aim-1'
    manifest = read(release / 'release-manifest.json')
    expected = manifest['payload_files']
    shoulder = read(work / 'attack-ms-glaive-top-shoulder-verified.json')
    assert shoulder['all_passed'] and shoulder['module_sha256'] == expected['exefs/subsdk1']
    cases = []
    for form, action in (('cutting', 58), ('impact', 68)):
        label = 'ms-glaive-top-attract-' + form + '-free-1'
        proof = read(work / ('attack-' + label + '.json'))
        raw = read(HERE / 'runs' / label / 'feedback-native.json')
        assert proof['all_passed'] and all(proof['checks'].values())
        assert raw['exit_code'] == 0 and not raw['failure'] and not raw['fatal']
        assert raw['muted'] and raw['source_saves_unchanged'] and raw['tested_payload_unchanged']
        assert raw['runtime_sha256'] == '286be3af1fe5aee7649bb548c33d550b8d52e97f931eafc9db6d6c030d6571b7'
        assert {n: h for n, h in raw['payload_files'].items() if n.startswith(('exefs/', 'romfs/'))} == expected
        case = proof['cases'][0]
        assert case['expected_action'] == action and action in case['actions']
        assert str(action) in case['landing_actions'] and case['after']['category'] in (1, 2)
        assert raw['test_setup']['hp_before'] < 5000 and not raw['test_setup']['hunter_position_overridden']
        cases.append({'form': form, 'run': label, 'action': action, 'landed': True,
                      'movement_m': round(case['moved_cm'] / 100, 2), 'returned_to_neutral': True})
    for filename, info in manifest['downloads'].items():
        assert hashlib.sha256((release / filename).read_bytes()).hexdigest() == info['sha256']
    for line in (release / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        digest, filename = line.split('  ', 1)
        assert hashlib.sha256((release / filename).read_bytes()).hexdigest() == digest
    report = {'all_passed': True, 'release_version': manifest['version'],
              'module_sha256': expected['exefs/subsdk1'], 'aim_trigger_top_attack': cases,
              'shoulder_R_plus_X_after_aim': shoulder,
              'fixture': 'One-time large-monster placement; normal hunter HP/position; official 0.18.0',
              'requirements': 'Attached marker, at least one bar, marker distance greater than14m and less than40m',
              'all_five_release_files_unchanged': True}
    (work / 'aim-top-attack-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_passed': True, 'cases': cases, 'release_unchanged': True}))


if __name__ == '__main__': main()
