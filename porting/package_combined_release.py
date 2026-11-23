"""Package the tested cumulative alpha.5 release without installing or uploading."""
import hashlib
import importlib.util
import json
import re
import shutil
import zipfile
from build_module import HERE, sha
from feedback_session import files
from package_public_release import NAME, make_zip, put
from prepare_public_launch import git_tree
from prepare_combined_release import STAGE, BASE, VERSION, WEAPON, ALPHA4, read

RELEASE = HERE / 'public-release/v0.1.0-alpha.5'
HANDOFF = HERE.parent / 'RELEASE UPLOAD - ALPHA 5'
RUNTIME_SHA = '286be3af1fe5aee7649bb548c33d550b8d52e97f931eafc9db6d6c030d6571b7'
DOCS = ('README.md', 'INSTALL.md', 'CONTROLS.md', 'COMPATIBILITY.md', 'RELEASE_NOTES.md',
        'GLAIVE_AIM.md', 'NAME_CHANGES.md', 'MOTION_FIXES.md', 'FEEDBACK_FIXES.md',
        'FREEZE_DIAGNOSTICS.md', 'SPRINT_ROLL_FIX.md', 'GUARD_DRAW_FIX.md',
        'LICENSE', 'THIRD_PARTY_NOTICES.md', 'release-validation.json')
SCRIPTS = ('prepare_combined_release.py', 'build_combined_release.py', 'test_combined_release.py',
           'verify_combined_release.py', 'exercise_combined_release.py', 'prepare_combined_docs.py',
           'package_combined_release.py', 'exercise_glaive_aim_top_attack.py', 'validate_glaive_top_attack.py')


def payload_files(root):
    return {n: h for n, h in files(root).items() if n.startswith(('exefs/', 'romfs/'))}


def native(proof, expected):
    assert proof['all_passed'] and all(proof['checks'].values())
    assert proof['payload_files'] == expected and proof['runtime_sha256'] == RUNTIME_SHA
    label = proof['label']
    run = read(HERE / 'runs' / label / 'feedback-native.json')
    assert run['all_passed'] and not run['failure'] and not run['fatal'] and run['exit_code'] == 0, label
    assert run['muted'] and run['source_saves_unchanged'] and run['tested_payload_unchanged'], label
    assert run['payload_files'] == expected == payload_files(HERE / 'runs' / label / 'mods/Magnet-Spike')
    result = {'run': label, 'scenario': proof['scenario'], 'checks': proof['checks'],
              'muted': True, 'original_saves_unchanged': True, 'passed': True}
    if proof['scenario'] == 'camp':
        result['ordinary_followup_trials'] = [
            {'x_a_at_frame': t['x_a_at_frame'], 'actions': t['actions'],
             'reached_153': t['reached_153'], 'after_category': t['after']['category']}
            for t in run['ordinary_stall_trials']]
    else:
        result['approach'] = run['approach']
        result['fixture'] = 'Monster placed once with native control; free AI and unmodified hunter HP/position; not a full hunt'
    return result


def docs_check(repo):
    for path in repo.glob('*.md'):
        text = path.read_text(encoding='utf-8')
        for target in re.findall(r'\]\(([^)]+)\)', text):
            if '://' not in target and not target.startswith('#'):
                assert (path.parent / target.split('#')[0]).exists(), (path.name, target)
    for name in ('README.md', 'RELEASE_NOTES.md', 'GLAIVE_AIM.md', 'MOTION_FIXES.md', 'FEEDBACK_FIXES.md', 'COMPATIBILITY.md'):
        text = (repo / name).read_text(encoding='utf-8')
        assert 'not included' not in text and 'separate unfixed stall' not in text, name
    assert all((repo / n).is_file() for n in DOCS)


def main():
    if RELEASE.exists() or HANDOFF.exists(): raise RuntimeError('Preserve existing release folder; do not overwrite')
    build, scope, compiled = [read(STAGE / p) for p in ('build-validation.json', 'scope-validation.json', 'compiled-validation.json')]
    assert build['all_passed'] and scope['all_passed'] and compiled['all_passed']
    payload = STAGE / 'output/magnet-spike-experimental'
    expected = files(payload)
    assert len(expected) == 56 and expected == build['payload_files'] == scope['payload_files'] == compiled['payload_files']
    assert build['hooks'] == 32 and build['patch_records'] == 106 and not build['watchdog_included']
    assert build['module_sha256'] == '2e0183e5813103ce8051e308fb797266b026af5fede9d61903a493bc26bb0eac'
    assert payload_files(ALPHA4) == payload_files(STAGE / 'inputs/motions/mod/Magnet-Spike')
    assert all(expected[n] == h for n, h in payload_files(ALPHA4).items() if n.startswith('romfs/'))
    assert files(HERE / 'output/magnet-spike-experimental') == read(STAGE / 'baseline.json')['normal_payload']
    results = [native(read(STAGE / ('native-' + name + '.json')), expected) for name in ('camp', 'cutting', 'impact')]
    compiled_checks = {}
    for rel, meta in compiled['reports'].items():
        report = read(STAGE / rel)
        assert report['all_passed'] and sha(STAGE / rel) == meta['sha256']
        compiled_checks[rel.rsplit('/', 1)[1]] = report.get('checks', report)
    unit = read(STAGE / 'unit/validation.json')
    assert unit['all_passed'] and unit['check_count'] == 148
    inputs = {}
    for label, folder in (('names', 'Alpha 3 name fix'), ('aim', 'Alpha 3 Glaive aim')):
        manifest = read(HERE.parent / folder / 'release-manifest.json')
        assert all(sha(HERE.parent / folder / n) == d['sha256'] for n, d in manifest['downloads'].items())
        inputs[label] = {k: manifest[k] for k in ('version', 'source_git_tree', 'downloads')}
    inputs['motions'] = {'version': 'v0.1.0-alpha.4', 'build_revision': 'motion-length-1',
                         'root_folder': 'Magnet-Spike-v0.1.0-alpha.4',
                         'validation_sha256': sha(ALPHA4 / 'release-validation.json'),
                         'payload_files': payload_files(ALPHA4)}
    validation = {'version': VERSION, 'revision': 'combined-1', 'base_version': 'v0.1.0-alpha.3',
        'all_passed': True, 'target': 'recomp', 'game_version': 'MHGU 1.4.0 English',
        'runtime': 'official Windows MHGURecomp 0.18.0', 'runtime_sha256': RUNTIME_SHA,
        'payload_files': expected, 'constituents': inputs, 'production_changes': scope['production_changes'],
        'source_scope_checks': scope['checks'], 'motion_scope': scope['motion_scope'],
        'compiled_regressions': compiled_checks, 'compiled_aim_checks': unit['check_count'],
        'name_variants_checked': 408, 'requested_renames': 13, 'native_tests': results,
        'native_hunting_style': 'Guild (0)', 'name_fix_included': True, 'glaive_aim_included': True,
        'motion_length_fix_included': True, 'all_four_alpha4_motion_corrections_included': True,
        'watchdog_included': False, 'extra_freeze_logging_enabled': False,
        'hooks': build['hooks'], 'patch_records': build['patch_records'],
        'timing_change': 'Inherited alpha.4 lead-ins: actions21/24/49 start attacks about0.75–0.85 seconds later than alpha.3; damage not retuned',
        'unchanged': ['equipment IDs, crafting costs and upgrade links', 'models and sounds',
                      'weapon stats, motion values and hit data', 'combo links, end-recovery windows and gauge costs',
                      'aim bindings, marker collision and attachment', 'native Great Sword records and names'],
        'historical_evidence_not_rerun': ['Standalone aim release six-style tests',
            'Supplied alpha.4 full action-entry sweep', 'Earlier full hunts, sharpness and remote-marker diagnostics'],
        'limits': ['Connected multiplayer not tested', 'No new full hunt on this combined build',
            'Fresh merged native tests use Guild style; other styles not rerun',
            'Restored lead-in appearance and feel not judged by a human',
            'Other freeze causes and the unconfirmed parry report not ruled out', 'Mouse aim not tested'],
        'installed': False, 'uploaded': False, 'published': False}
    repo, ready = RELEASE / 'repo', RELEASE / 'ready'
    shutil.copytree(STAGE / 'source', repo)
    ready.mkdir()
    for name in SCRIPTS: put(HERE / name, repo / 'porting' / name)
    for name, digest in compiled['test_source_sha256'].items(): assert sha(repo / 'porting' / name) == digest, name
    # A developer opening porting/CONTROLS.md gets the same current guide with valid links.
    guide = (repo / 'CONTROLS.md').read_text(encoding='utf-8')
    guide = re.sub(r'\]\(([^)#]+\.md)(#[^)]*)?\)', lambda m: '](../' + m[1] + (m[2] or '') + ')', guide)
    (repo / 'porting/CONTROLS.md').write_text(guide, encoding='utf-8')
    # Correct the mirrored README's one link whose target lives at repository root.
    mirror = repo / 'porting/release-docs/README.md'
    mirror.write_text(mirror.read_text(encoding='utf-8').replace('](LICENSE)', '](../../LICENSE)'), encoding='utf-8')
    (repo / 'release-validation.json').write_text(json.dumps(validation, indent=2) + '\n', encoding='utf-8')
    assert {n: sha(repo / 'porting' / n) for n in scope['production_changes']} == {
        n: sha(STAGE / 'source/porting' / n) for n in scope['production_changes']}
    assert files(repo / 'porting/module') == files(STAGE / 'module')
    assert files(repo / 'porting' / WEAPON / 'module') == files(STAGE / 'weapon/module')
    docs_check(repo)
    spec = importlib.util.spec_from_file_location('combined_source_check', repo / 'check_source_tree.py')
    checker = importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)
    count = checker.check(repo)
    source_files, tree = files(repo), git_tree(repo).hex()
    mod_zip = ready / f'Magnet-Spike-{VERSION}.zip'
    source_zip = ready / f'Magnet-Spike-{VERSION}-source.zip'
    make_zip(mod_zip, [('Magnet-Spike/' + p.relative_to(payload).as_posix(), p) for p in payload.rglob('*') if p.is_file()]
             + [('Magnet-Spike/' + n, repo / n) for n in DOCS])
    source_root = NAME + '-' + VERSION + '/'
    make_zip(source_zip, [(source_root + p.relative_to(repo).as_posix(), p) for p in repo.rglob('*') if p.is_file()])
    downloads = {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in (mod_zip, source_zip)}
    manifest = {'version': VERSION, 'revision': 'combined-1', 'base_version': 'v0.1.0-alpha.3',
        'repository': read(BASE / 'ready/release-manifest.json')['repository'],
        'game_version': 'MHGU 1.4.0', 'language': 'English', 'runtime': 'MHGURecomp 0.18.0 Windows x64',
        'target': 'recomp', 'payload_files': expected, 'source_file_count': count,
        'source_git_tree': tree, 'source_files': source_files, 'downloads': downloads,
        'name_fix_included': True, 'glaive_aim_included': True, 'motion_length_fix_included': True,
        'watchdog_included': False, 'extra_freeze_logging_enabled': False,
        'focused_validation_passed': True, 'contains_saves_or_game_executable': False}
    (ready / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    put(repo / 'release-validation.json', ready / 'release-validation.json')
    (ready / 'SHA256SUMS.txt').write_text(''.join(sha(p) + '  ' + p.name + '\n' for p in
        (mod_zip, source_zip, ready / 'release-manifest.json', ready / 'release-validation.json')), encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist())) == len(expected) + len(DOCS)
        actual = {n.removeprefix('Magnet-Spike/'): hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
                  if n.startswith(('Magnet-Spike/exefs/', 'Magnet-Spike/romfs/'))}
        assert actual == expected
        for n in DOCS: assert hashlib.sha256(z.read('Magnet-Spike/' + n)).hexdigest() == sha(repo / n)
    with zipfile.ZipFile(source_zip) as z:
        assert z.testzip() is None and len(z.namelist()) == len(set(z.namelist())) == count
        assert {n.removeprefix(source_root): hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()} == source_files
    assert len(list(ready.iterdir())) == 5
    shutil.copytree(ready, HANDOFF)
    assert files(ready) == files(HANDOFF)
    put(repo / 'RELEASE_NOTES.md', HERE.parent / 'Alpha 5 - Release notes.md')
    receipt = {'all_passed': True, 'version': VERSION, 'source_file_count': count, 'source_git_tree': tree,
               'downloads': downloads, 'handoff': str(HANDOFF), 'installed': False, 'uploaded': False, 'published': False}
    (STAGE / 'release-preparation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__': main()
