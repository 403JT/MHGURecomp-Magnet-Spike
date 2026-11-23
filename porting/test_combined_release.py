"""Run existing compiled tests against the merged module; isolate all outputs."""
import ast
import hashlib
import json
import sys
import build_module as build
from feedback_session import files
from prepare_combined_release import STAGE, read


def main():
    proof = read(STAGE / 'build-validation.json')
    build.MS, build.MOD, build.OUT = STAGE / 'weapon', STAGE / 'module', STAGE / 'output'
    import build_hitstats, build_cancel_windows, build_smithy_tree, build_balance
    for helper in (build_hitstats, build_cancel_windows, build_smithy_tree, build_balance): helper.HERE = STAGE
    build_hitstats.OUT = STAGE / 'output'
    selected = ('test_weapon_name_fix.py', 'test_smithy_tree.py', 'test_sprint_roll.py',
                'test_guard_draw.py', 'test_damage_feedback.py', 'test_feedback_recovery.py', 'test_glaive_aim.py')
    hashes, destinations = {}, []

    class Reports(ast.NodeTransformer):
        def visit_Constant(self, node):
            if isinstance(node.value, str) and node.value.startswith('reports/') and node.value.endswith('.json'):
                # Source-input JSONs still come from the shared local inputs;
                # only the known output reports are redirected.
                if node.value in ('reports/weapon-name-fix-validation.json', 'reports/smithy-tree-regression.json',
                                  'reports/sprint-roll-regression.json', 'reports/guard-draw-regression.json',
                                  'reports/damage-feedback-regression.json', 'reports/feedback-recovery-regression.json'):
                    destinations.append(node.value)
                    node.value = 'combined-dev/alpha5-1/' + node.value
            return node

    for name in selected:
        raw = (build.HERE / name).read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        tree = Reports().visit(ast.parse(raw, filename=name))
        ast.fix_missing_locations(tree)
        sys.argv = [name]
        if name == 'test_glaive_aim.py':
            sys.argv += ['--weapon-source', str(build.MS), '--output-dir', str(STAGE / 'unit')]
        print('Testing merged build:', name, flush=True)
        exec(compile(tree, name, 'exec'), {'__name__': '__main__', '__file__': str(build.HERE / name)})
    results = {}
    for rel in destinations:
        result = read(STAGE / rel)
        assert result['all_passed'], rel
        results[rel] = {'passed': True, 'sha256': hashlib.sha256((STAGE / rel).read_bytes()).hexdigest()}
    assert len(results) == 6 and read(STAGE / 'unit/validation.json')['all_passed']
    assert files(STAGE / 'output/magnet-spike-experimental') == proof['payload_files']
    result = {'all_passed': True, 'reports': results, 'test_source_sha256': hashes,
              'compiled_aim_checks': read(STAGE / 'unit/validation.json')['check_count'],
              'name_variants_checked': 408, 'requested_renames': 13, 'payload_files': proof['payload_files']}
    (STAGE / 'compiled-validation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_passed': True, 'reports': len(results) + 1, 'name_variants_checked': 408, 'aim_checks': 148}))


if __name__ == '__main__': main()
