"""Run existing regression logic against the isolated aim branch.

Only report destinations are adapted in memory; original test source files,
normal output and historical reports are preserved.
"""
import ast
import hashlib
import json
import sys
import build_module as build
from feedback_session import files
from prepare_glaive_aim_build import STAGE


def main():
    normal = files(build.OUT / 'magnet-spike-experimental')
    build.MS, build.MOD, build.OUT = STAGE / 'weapon', STAGE / 'module', STAGE / 'output'
    selected = ('test_sprint_roll.py', 'test_guard_draw.py', 'test_damage_feedback.py', 'test_feedback_recovery.py')
    reports = {'reports/sprint-roll-regression.json', 'reports/guard-draw-regression.json',
               'reports/damage-feedback-regression.json', 'reports/feedback-recovery-regression.json'}
    source_hashes = {}

    class Reports(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value in reports:
                node.value = 'aim-dev/alpha3-glaive-aim-1/' + node.value
            return node

    for name in selected:
        path = build.HERE / name
        raw = path.read_bytes()
        source_hashes[name] = hashlib.sha256(raw).hexdigest()
        if '--collect-only' not in sys.argv:
            tree = Reports().visit(ast.parse(raw, filename=str(path)))
            ast.fix_missing_locations(tree)
            print('Running unchanged regression logic:', name, flush=True)
            exec(compile(tree, str(path), 'exec'), {'__name__': '__main__', '__file__': str(path)})
    assert files(build.HERE / 'output/magnet-spike-experimental') == normal
    results = {}
    for path in (STAGE / 'reports').glob('*regression.json'):
        report = json.loads(path.read_text(encoding='utf-8'))
        assert report['all_passed'], path.name
        count = len(report['checks']) if 'checks' in report else len(report['fixed']) + len(report['collision_gate'])
        results[path.name] = {'passed': True, 'checks': count}
    assert len(results) == 4
    proof = {'all_passed': True, 'results': results, 'test_source_sha256': source_hashes,
             'payload_files': files(STAGE / 'output/magnet-spike-experimental'), 'normal_output_unchanged': True}
    (STAGE / 'regressions.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_passed': True, 'results': results}))


if __name__ == '__main__': main()
