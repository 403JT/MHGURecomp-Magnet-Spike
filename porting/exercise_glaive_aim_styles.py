"""Ordinary aim/pin inputs in both forms and all six styles, muted/cloned saves."""
import argparse
import json
import math
import re
import struct
import time
from PIL import Image
from exercise_glaive_aim import AimSession
from prepare_frontier import HERE
from prepare_test_profile import FILE_SIZE
from prepare_glaive_aim_build import STAGE


def cursor_pixels(path):
    with Image.open(path) as source:
        image = source.convert('RGB')
    # Native Glaive's saturated pink overlay at the centre of a 720p frame.
    return sum(r > 150 and b > 80 and g < 100 and r > 1.2 * b and b > 1.3 * g
               for r, g, b in image.crop((610, 330, 670, 390)).getdata())


def style_setup(style):
    def setup(save):
        for name in ('system', 'system_backup'):
            path = save / name
            data = bytearray(path.read_bytes())
            assert len(data) == FILE_SIZE
            base = 0x24 + struct.unpack_from('<I', data, 0x34 + 4 * data[0x2b])[0]
            data[base + 0x23b4c] = style
            path.write_bytes(data)
        return {'style': style, 'only_disposable_save_modified': True}
    return setup


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--label', required=True)
    p.add_argument('--styles', default='0,1,2,3,4,5')
    args = p.parse_args()
    styles = [int(v) for v in args.styles.split(',')]
    assert styles and all(0 <= v <= 5 for v in styles)
    results = []
    for style in styles:
        s = AimSession(args.label + '-style-' + str(style),
                       payload_root=STAGE / 'output/magnet-spike-experimental', save_setup=style_setup(style))
        checks = {}
        try:
            s.ready()
            for form, shot in (('cutting', 82), ('impact', 84)):
                if form == 'impact':
                    s.send('MINUS 8')
                    time.sleep(2.5)
                before = s.snapshot(form + '-before')
                start = len(s.log())
                s.send('ZR 240')
                time.sleep(.6)
                aim = s.snapshot(form + '-aim')
                checks[form + '_native_cursor_visible'] = cursor_pixels(s.folder / 'shots' / (form + '-aim.png')) >= 60
                checks[form + '_normal_camera_kept'] = aim['camera_aim'] == aim['aim_byte'] == 0
                checks[form + '_no_camera_jump'] = sum((a - b) ** 2 for a, b in zip(aim['eye'], before['eye'])) < 1
                s.send(('RSTICK_RIGHT' if form == 'cutting' else 'RSTICK_UP') + ' 18')
                time.sleep(.7)
                looked = s.snapshot(form + '-looked')
                d = [b - a for a, b in zip(looked['eye'], looked['look_at'])]
                n = math.sqrt(sum(x * x for x in d))
                expected = [x / n for x in d]
                s.send('A 8')
                time.sleep(4.5)
                after = s.snapshot(form + '-released')
                text = s.log()[start:]
                actions = [int(v) for v in re.findall(r'msport: action (\d+) \(', text)]
                directions = [list(map(int, v)) for v in re.findall(
                    r'marker shot from .*?direction (-?\d+) (-?\d+) (-?\d+) / 1000', text)]
                checks[form + '_correct_shot_action'] = shot in actions
                checks[form + '_pin_launched'] = bool(directions)
                checks[form + '_pin_matches_camera'] = bool(directions) and max(
                    abs(a / 1000 - b) for a, b in zip(directions[0], expected)) < .015
                checks[form + '_finished_normally'] = after['category'] in (1, 2)
                checks[form + '_cursor_hidden_on_release'] = cursor_pixels(s.folder / 'shots' / (form + '-released.png')) < 30
                s.report.setdefault('shot_evidence', []).append({'form': form, 'actions': actions,
                    'directions': directions, 'expected_camera_direction': expected})
                assert all(checks.values()), {k: v for k, v in checks.items() if not v}
            if style == 0:
                s.send('ZR 120\nSTICK_RIGHT 45')
                time.sleep(.7)
                moving = s.snapshot('moving-aim')
                checks['moving_cursor_visible'] = cursor_pixels(s.folder / 'shots/moving-aim.png') >= 60
                checks['moving_camera_finite'] = moving['finite_camera'] and not moving['camera_aim']
                time.sleep(2)
                s.send('Y 8')
                time.sleep(2.5)
                s.send('ZR 90')
                time.sleep(.6)
                sheathed = s.snapshot('sheathed-trigger')
                checks['sheathed_trigger_does_not_aim'] = cursor_pixels(s.folder / 'shots/sheathed-trigger.png') < 30
                checks['sheathed_camera_normal'] = sheathed['camera_aim'] == sheathed['aim_byte'] == 0
                time.sleep(1.5)
                s.send('X 8')
                time.sleep(2.5)
                for _ in range(8):
                    s.send('ZR 18')
                    time.sleep(.55)
                toggled = s.snapshot('after-repeated-toggles')
                checks['repeated_toggle_recovers'] = toggled['category'] in (1, 2) and not toggled['camera_aim']
                checks['repeated_toggle_hides_cursor'] = cursor_pixels(s.folder / 'shots/after-repeated-toggles.png') < 30
            checks['all_camera_samples_finite'] = all(c['finite_camera'] for c in s.report['cases'])
            s.report['checks'] = checks
            s.report['all_passed'] = all(checks.values())
            assert s.report['all_passed'], checks
        except Exception as exc:
            s.report['failure'] = str(exc)
            s.write()
            raise
        finally:
            s.close()
        assert s.report['exit_code'] == 0 and not s.report['fatal'] and s.report['source_saves_unchanged']
        results.append({'style': style, 'run': s.folder.name, 'checks': checks, 'passed': True})
        print(json.dumps({'style': style, 'checks': len(checks), 'passed': True}), flush=True)
    proof = {'all_passed': True, 'styles': styles, 'results': results,
             'scope': 'Ordinary trigger, stick, Minus and A inputs; official 0.18.0, no live monster, muted disposable saves'}
    (STAGE / ('native-' + args.label + '.json')).write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__': main()
