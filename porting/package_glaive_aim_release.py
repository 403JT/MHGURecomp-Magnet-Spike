"""Package the tested separate alpha.3 Glaive-aim variant; no installation/network."""
import hashlib
import importlib.util
import json
import re
import shutil
import zipfile
from build_module import HERE, MS, sha
from feedback_session import files
from package_public_release import NAME, make_zip, put
from prepare_public_launch import git_tree
from prepare_glaive_aim_build import STAGE, BASE

VERSION = 'v0.1.0-alpha.3-glaive-aim'
RELEASE = HERE / 'public-release/alpha3-glaive-aim-1'
HANDOFF = HERE.parent / 'Alpha 3 Glaive aim'
RUNTIME_SHA = '286be3af1fe5aee7649bb548c33d550b8d52e97f931eafc9db6d6c030d6571b7'


def read(path): return json.loads(path.read_text(encoding='utf-8'))


def native_run(label, expected):
    report = read(HERE / 'runs' / label / 'feedback-native.json')
    assert report['exit_code'] == 0 and not report['failure'] and not report['fatal'], label
    assert report['muted'] and report['source_saves_unchanged'] and report['tested_payload_unchanged'], label
    assert report['runtime_sha256'] == RUNTIME_SHA and report['payload_files'] == expected, label
    assert files(HERE / 'runs' / label / 'mods/Magnet-Spike') == expected
    return report


def main():
    if RELEASE.exists() or HANDOFF.exists(): raise RuntimeError('Release folder already exists; do not overwrite')
    baseline = read(BASE / 'ready/release-manifest.json')
    payload = STAGE / 'output/magnet-spike-experimental'
    expected = files(payload)
    build, scope, regressions = [read(STAGE / p) for p in ('build-validation.json', 'source-scope.json', 'regressions.json')]
    unit = read(STAGE / 'unit/validation.json')
    matrix = read(STAGE / 'native-ms-glaive-aim-matrix-2.json')
    target = read(STAGE / 'native-target-validation.json')
    assert scope['all_passed'] and regressions['all_passed'] and unit['all_passed'] and matrix['all_passed'] and target['all_passed']
    assert expected == build['payload_files'] == scope['payload_files'] == regressions['payload_files'] == target['payload_files']
    assert files(STAGE / 'weapon/module') == build['weapon_module_sources'] == scope['weapon_source_files']
    assert files(STAGE / 'module') == build['local_module_sources'] == scope['local_source_files']
    assert matrix['styles'] == list(range(6)) and len(expected) == 56
    assert all(expected[n] == h for n, h in baseline['payload_files'].items() if n.startswith('romfs/'))
    native = []
    for item in matrix['results']:
        r = native_run(item['run'], expected)
        assert r['all_passed'] and all(r['checks'].values())
        assert [q['form'] for q in r['shot_evidence']] == ['cutting', 'impact']
        native.append({'run': item['run'], 'style': item['style'], 'checks': r['checks'],
                       'shot_evidence': r['shot_evidence'], 'passed': True})
    r = native_run(target['run'], expected)
    assert r['all_passed'] and all(r['checks'].values())
    hits = sum(q['hit'] for q in target['shots'])
    validation = {'version': VERSION, 'base_version': 'v0.1.0-alpha.3', 'revision': 'glaive-aim-1',
        'all_passed': True, 'payload_files': expected, 'target': 'recomp',
        'game_version': 'MHGU 1.4.0 English', 'runtime': 'official Windows MHGURecomp 0.18.0',
        'runtime_sha256': RUNTIME_SHA, 'source_scope_checks': scope['checks'],
        'compiled_aim_checks': unit['check_count'], 'compiled_regressions': regressions['results'],
        'native_styles': native, 'marker_collision': target,
        'extra_freeze_logging_enabled': False, 'name_fix_included': False, 'additional_stall_fix_included': False,
        'unchanged': ['all 54 assets', 'all attacks, damage and recovery durations', 'weapon stats and smithy data',
                      'shot collision and marker tracking', 'trigger/face-button bindings', 'save IDs and state layout'],
        'limits': ['Connected multiplayer not tested', 'Controlled marker collision fixture is not a full hunt',
                   'The separate alpha.4 stall fix and alpha.3 name fix are not included'],
        'installed': False, 'uploaded': False, 'published': False}
    notes = f'''# Magnet Spike — alpha.3 Glaive aim

Separate **{VERSION}** variant of the original alpha.3 release, for **MHGU 1.4.0 English**
on **Windows MHGURecomp 0.18.0** and its built-in mod loader.

Holding **ZR / right trigger** now keeps the normal third-person camera and shows
the native Insect Glaive pink centre cursor. Right-stick aiming uses the game's
normal camera controls and settings. **ZR+A / right face button** still fires the
magnetic pin. Release ZR to hide the cursor. Drawing, sheathing, changing form,
attacks, damage and recovery retain their alpha.3 behaviour.

This includes alpha.3's sprint-roll and sheathed R+X+A guard-draw fixes. The
separate weapon-name update and alpha.4 stall correction are **not included**.
All 54 asset files match the original alpha.3 release; the change is in the code module.

Validation: {unit['check_count']} compiled aim checks; sprint-roll, guard-draw,
interrupted-damage and recovery regressions; ordinary aim and pin inputs in both
forms across all six hunting styles on official 0.18.0; and {hits}/{len(target['shots'])}
pin hits against a controlled monster target. Camera continuity, cursor visibility,
pin direction, action completion, moving aim, sheathing and repeated toggles were
checked. All test games were muted and used copied saves. Connected multiplayer
and a new full hunt are not claimed as tested.

Close MHGURecomp, back up your save, move the old Magnet-Spike folder out of mods,
and copy in the new folder from **Magnet-Spike-{VERSION}.zip**. Keep only one Magnet
Spike mod copy enabled. Existing weapons need no recrafting. Upload the mod ZIP,
matching source ZIP, release-manifest.json, release-validation.json and SHA256SUMS.txt.
'''
    aim_doc = '''# Insect Glaive-style Magnet Spike aiming

ZR keeps the standard third-person camera and displays GU's native pink Glaive
cursor at screen centre. ZR+A fires the existing pin; ZR+X, ZR+B and the other
Magnet Spike bindings retain their existing conditions and meanings.

The native Glaive reference run leaves the gunner aim byte and quest-camera aim
mode off. This variant does the same. It supplies the native scope selector's
Glaive cursor capability through the Magnet Spike vtable's slot 342, for the
local aiming hunter only. It does not call Glaive action handlers or read its
larger player object's private fields. Native Glaive and other weapons are unchanged.

The normal camera owns the stick input, inversion and pitch limits. The weapon
reads its direction without applying another stick update or rotating the hunter.
The existing shot-start code already takes the camera's direction, so projectile
speed, collision, marker tracking and attack behaviour are unchanged.

Only aim_look, aim_view, ms_after_update and the new ms_aim_cursor differ in
ms_act.c. ms_class.c adds one vtable override; ms.h adds its declaration while
preserving state layout. Other weapon-action code is token-identical to alpha.3.

See release-validation.json for the exact payload and tests. The source contains
test fixtures and metadata only, with no original game assets, saves or captures.
The historical alpha.3 limitations remain, including its separate unfixed stall.
'''
    repo, ready = RELEASE / 'repo', RELEASE / 'ready'
    shutil.copytree(BASE / 'repo', repo)
    ready.mkdir()
    for name in ('ms.h', 'ms_act.c', 'ms_class.c'):
        put(STAGE / 'weapon/module' / name, repo / 'porting' / MS.relative_to(HERE) / 'module' / name)
    for name in ('native_cfg.py', 'test_glaive_aim.py', 'tests/glaive_aim_harness.c', 'feedback_session.py',
                 'exercise_glaive_aim.py', 'exercise_glaive_aim_styles.py', 'exercise_glaive_aim_target.py',
                 'prepare_glaive_aim_build.py', 'build_glaive_aim.py', 'test_glaive_aim_regressions.py',
                 'verify_glaive_aim_scope.py', 'package_glaive_aim_release.py'):
        put(HERE / name, repo / 'porting' / name)
    # This source branch now tests native-camera aim, replacing the historical
    # MHF look-step expectations. The working tree's older tests are untouched.
    (repo / 'porting/test_aim.py').write_text(
        '"""Aim regression entry point for the Glaive-aim variant."""\n'
        'from test_glaive_aim import main\n\nif __name__ == "__main__": main()\n', encoding='utf-8')
    readme = ('# Magnet Spike — alpha.3 Glaive aim\n\n'
        'A separate alpha.3 variant with Insect Glaive-style third-person aiming and its native pink cursor. '
        'Read [GLAIVE_AIM.md](GLAIVE_AIM.md), [CONTROLS.md](CONTROLS.md), '
        '[INSTALL.md](INSTALL.md) and [RELEASE_NOTES.md](RELEASE_NOTES.md).\n\n'
        'Includes the original alpha.3 sprint-roll and guard-draw fixes. The separate name update and '
        'alpha.4 stall fix are not included. This remains an experimental alpha for '
        'MHGU 1.4.0 English on Windows MHGURecomp 0.18.0.\n\n'
        'Use the mod ZIP to play; the source ZIP is for developers and contains no game data. '
        'See [BUILDING.md](BUILDING.md), [COMPATIBILITY.md](COMPATIBILITY.md), '
        '[LICENSE](LICENSE) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).\n')
    for name, text in (('README.md', readme), ('RELEASE_NOTES.md', notes), ('GLAIVE_AIM.md', aim_doc)):
        for dest in (repo / name, repo / 'porting/release-docs' / name): dest.write_text(text, encoding='utf-8')
    for rel in ('INSTALL.md', 'porting/release-docs/INSTALL.md'):
        path = repo / rel
        path.write_text(path.read_text(encoding='utf-8').replace('v0.1.0-alpha.3', VERSION), encoding='utf-8')
    for rel in ('CONTROLS.md', 'porting/CONTROLS.md', 'porting/release-docs/CONTROLS.md'):
        path = repo / rel
        text = path.read_text(encoding='utf-8')
        # Put the branch's behaviour before the retained detailed move guide.
        text = ('> **Glaive-aim variant:** ZR/right trigger uses the normal third-person camera '
                'and native pink centre cursor. ZR+A still fires the pin. Normal camera settings apply.\n\n' + text)
        text = text.replace("The installed build uses GU's scope art; use the distance requirements rather\n"
                            "than expecting Frontier's coloured reticle.",
                            'This variant uses the native pink Insect Glaive cursor. Attraction and repulsion still use the existing distance requirements.')
        path.write_text(text, encoding='utf-8')
    for rel in ('COMPATIBILITY.md', 'porting/release-docs/COMPATIBILITY.md'):
        path = repo / rel
        path.write_text(path.read_text(encoding='utf-8') + '\nThis separate Glaive-aim variant was tested in both forms '
            'across all six hunting styles on official Windows 0.18.0. Connected multiplayer remains untested. '
            'See GLAIVE_AIM.md and release-validation.json.\n', encoding='utf-8')
    for rel in ('BUILDING.md', 'porting/release-docs/BUILDING.md'):
        path = repo / rel
        path.write_text(path.read_text(encoding='utf-8') + '\nFor this source branch, test_aim.py delegates to '
            'test_glaive_aim.py after the local generated inputs exist. Normal build_module.py uses the included '
            'Glaive-aim source. The isolated preparation/packaging scripts additionally require the prior alpha.3 '
            'release snapshot and local evidence layout; they are retained for provenance.\n', encoding='utf-8')
    (repo / 'release-validation.json').write_text(json.dumps(validation, indent=2) + '\n', encoding='utf-8')
    for path in repo.rglob('*'):
        if path.is_file(): path.write_bytes(path.read_text(encoding='utf-8').replace('\r\n', '\n').encode('utf-8'))
    for path in repo.glob('*.md'):
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if '://' not in target and not target.startswith('#'):
                dest = target.split('#')[0]
                assert not dest or (path.parent / dest).exists(), (path.name, target)
    spec = importlib.util.spec_from_file_location('aim_source_check', HERE / 'release-docs/check_source_tree.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    count = checker.check(repo)
    tree = git_tree(repo).hex()
    mod_zip, source_zip = ready / f'Magnet-Spike-{VERSION}.zip', ready / f'Magnet-Spike-{VERSION}-source.zip'
    docs = ('README.md', 'INSTALL.md', 'CONTROLS.md', 'COMPATIBILITY.md', 'RELEASE_NOTES.md', 'GLAIVE_AIM.md',
            'LICENSE', 'THIRD_PARTY_NOTICES.md', 'FEEDBACK_FIXES.md', 'SPRINT_ROLL_FIX.md', 'GUARD_DRAW_FIX.md', 'release-validation.json')
    make_zip(mod_zip, [('Magnet-Spike/' + path.relative_to(payload).as_posix(), path) for path in payload.rglob('*') if path.is_file()]
             + [('Magnet-Spike/' + name, repo / name) for name in docs])
    make_zip(source_zip, [(NAME + '-' + VERSION + '/' + path.relative_to(repo).as_posix(), path) for path in repo.rglob('*') if path.is_file()])
    downloads = {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path)} for path in (mod_zip, source_zip)}
    manifest = {'version': VERSION, 'base_version': 'v0.1.0-alpha.3', 'revision': 'glaive-aim-1',
        'repository': baseline['repository'], 'game_version': 'MHGU 1.4.0', 'language': 'English',
        'runtime': 'MHGURecomp 0.18.0 Windows x64', 'target': 'recomp', 'payload_files': expected,
        'source_file_count': count, 'source_git_tree': tree, 'source_files': files(repo), 'downloads': downloads,
        'focused_validation_passed': True, 'extra_freeze_logging_enabled': False,
        'name_fix_included': False, 'additional_stall_fix_included': False, 'contains_saves_or_game_executable': False}
    (ready / 'release-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    put(repo / 'release-validation.json', ready / 'release-validation.json')
    (ready / 'SHA256SUMS.txt').write_text(''.join(sha(path) + '  ' + path.name + '\n' for path in
        (mod_zip, source_zip, ready / 'release-manifest.json', ready / 'release-validation.json')), encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        assert z.testzip() is None
        actual = {name.removeprefix('Magnet-Spike/'): hashlib.sha256(z.read(name)).hexdigest() for name in z.namelist()
                  if name.startswith(('Magnet-Spike/exefs/', 'Magnet-Spike/romfs/'))}
        assert actual == expected
    with zipfile.ZipFile(source_zip) as z: assert z.testzip() is None
    assert len(list(ready.iterdir())) == 5
    shutil.copytree(ready, HANDOFF)
    for path in ready.iterdir(): assert sha(path) == sha(HANDOFF / path.name)
    (HERE.parent / 'Alpha 3 Glaive aim - Release notes.md').write_text(notes, encoding='utf-8')
    receipt = {'all_passed': True, 'version': VERSION, 'source_file_count': count, 'source_git_tree': tree,
               'downloads': downloads, 'handoff': str(HANDOFF), 'installed': False, 'uploaded': False, 'published': False}
    (STAGE / 'release-preparation.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__': main()
