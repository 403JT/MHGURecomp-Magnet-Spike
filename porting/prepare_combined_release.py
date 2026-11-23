"""Copy and merge the three completed releases into an isolated alpha.5 tree."""
import hashlib
import importlib.util
import json
import shutil
import zipfile
from pathlib import Path
from build_module import HERE, MS
from feedback_session import files

STAGE = HERE / 'combined-dev/alpha5-1'
BASE = HERE / 'public-release/v0.1.0-alpha.3'
ALPHA4 = HERE.parent / 'Magnet-Spike-v0.1.0-alpha.4/Magnet-Spike'
TOOLS = MS.relative_to(HERE) / 'tools'
WEAPON = MS.relative_to(HERE)
VERSION = 'v0.1.0-alpha.5'


def read(path): return json.loads(path.read_text(encoding='utf-8'))
def digest(data): return hashlib.sha256(data).hexdigest()


def unzip(archive, dest):
    existing = dest.exists()
    if not existing: dest.mkdir(parents=True)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(set(names)) == len(names)
        for name in names:
            if name.endswith('/'): continue
            path = (dest / name).resolve()
            assert path.is_relative_to(dest.resolve())
            if existing:
                assert path.is_file() and digest(path.read_bytes()) == digest(z.read(name))
                continue
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(z.read(name))
    return dest / names[0].split('/')[0]


def release_input(folder, label):
    manifest = read(folder / 'release-manifest.json')
    for name, meta in manifest['downloads'].items(): assert digest((folder / name).read_bytes()) == meta['sha256']
    src_name = next(n for n in manifest['downloads'] if n.endswith('-source.zip'))
    mod_name = next(n for n in manifest['downloads'] if n.endswith('.zip') and not n.endswith('-source.zip'))
    src = unzip(folder / src_name, STAGE / 'inputs' / label / 'source')
    mod = unzip(folder / mod_name, STAGE / 'inputs' / label / 'mod')
    assert files(src) == manifest['source_files']
    assert {n: h for n, h in files(mod).items() if n.startswith(('exefs/', 'romfs/'))} == manifest['payload_files']
    return src, mod, manifest


def main():
    if STAGE.exists():
        assert sorted(p.name for p in STAGE.iterdir()) == ['inputs'], 'Prepared stage exists; preserve it'
    normal = files(HERE / 'output/magnet-spike-experimental')
    STAGE.mkdir(parents=True, exist_ok=True)
    name_src, name_mod, name_meta = release_input(HERE.parent / 'Alpha 3 name fix', 'names')
    aim_src, aim_mod, aim_meta = release_input(HERE.parent / 'Alpha 3 Glaive aim', 'aim')
    base_meta = read(BASE / 'ready/release-manifest.json')
    for meta in (name_meta, aim_meta):
        assert meta['base_version'] == 'v0.1.0-alpha.3'
        assert meta['payload_files'].keys() == base_meta['payload_files'].keys()
        assert all(meta['payload_files'][n] == h for n, h in base_meta['payload_files'].items() if n.startswith('romfs/'))
    alpha4_mod = STAGE / 'inputs/motions/mod/Magnet-Spike'
    if alpha4_mod.exists(): assert files(alpha4_mod) == files(ALPHA4)
    else: shutil.copytree(ALPHA4, alpha4_mod)
    a4proof = read(alpha4_mod / 'release-validation.json')
    assert a4proof['build_revision'] == 'motion-length-1'
    a4files = {n: h for n, h in files(alpha4_mod).items() if n.startswith(('exefs/', 'romfs/'))}
    assert a4files.keys() == base_meta['payload_files'].keys()
    differ = sorted(n for n, h in a4files.items() if h != base_meta['payload_files'][n])
    assert differ == ['romfs/nativeNX/arc/player/quest/w05.arc', 'romfs/nativeNX/arc/weapon/w05/g00.arc']
    for rel, proof in a4proof['data_fix']['repack'].items():
        assert a4files['romfs/nativeNX/arc/' + rel] == proof['sha256_after']
    # Read-only copy of the other agent's matching publication source. All
    # examination/builds below use our copy, never its work directory.
    other_src = HERE.parent / 'claude-stall-fix/release-build/repo'
    alpha4_src = STAGE / 'inputs/motions/source'
    spec = importlib.util.spec_from_file_location('combined_source_check', HERE / 'release-docs/check_source_tree.py')
    checker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checker)
    if not alpha4_src.exists():
        checker.check(other_src)
        shutil.copytree(other_src, alpha4_src, ignore=shutil.ignore_patterns('.git'))
    checker.check(alpha4_src)
    assert read(alpha4_src / 'release-validation.json') == a4proof, 'Alpha.4 source does not match the supplied root build'
    assert (alpha4_src / 'MOTION_FIXES.md').read_bytes() == (alpha4_mod / 'MOTION_FIXES.md').read_bytes()
    base_src = BASE / 'repo'
    # The three production changes occupy different files. Require exact
    # unchanged baselines for every non-owning input before combining them.
    original_weapon = files(base_src / 'porting' / WEAPON / 'module')
    assert files(name_src / 'porting' / WEAPON / 'module') == original_weapon
    assert files(alpha4_src / 'porting' / WEAPON / 'module') == original_weapon
    assert files(aim_src / 'porting/module') == files(base_src / 'porting/module')
    assert files(alpha4_src / 'porting/module') == files(base_src / 'porting/module')
    local_diff = [n for n, h in files(name_src / 'porting/module').items()
                  if files(base_src / 'porting/module').get(n) != h]
    assert local_diff == ['smithy.c']
    aim_diff = sorted(n for n, h in files(aim_src / 'porting' / WEAPON / 'module').items() if original_weapon.get(n) != h)
    assert aim_diff == ['ms.h', 'ms_act.c', 'ms_class.c']
    tool_diff = sorted(n for n, h in files(alpha4_src / 'porting' / TOOLS).items()
                       if files(base_src / 'porting' / TOOLS).get(n) != h)
    assert tool_diff == ['msbuild.py', 'msfx.py', 'msmot.py']
    merged = STAGE / 'source'
    shutil.copytree(aim_src, merged)
    for rel in ('module/smithy.c', 'tests/smithy_harness.c', 'test_weapon_name_fix.py'):
        shutil.copyfile(name_src / 'porting' / rel, merged / 'porting' / rel)
    for name in tool_diff:
        shutil.copyfile(alpha4_src / 'porting' / TOOLS / name, merged / 'porting' / TOOLS / name)
    for name in ('NAME_CHANGES.md',): shutil.copyfile(name_src / name, merged / name)
    shutil.copyfile(alpha4_src / 'MOTION_FIXES.md', merged / 'MOTION_FIXES.md')
    shutil.copytree(merged / 'porting' / WEAPON / 'module', STAGE / 'weapon/module')
    shutil.copytree(merged / 'porting/module', STAGE / 'module')
    shutil.copytree(MS / 'gen', STAGE / 'weapon/gen')
    # Link against the validated sound-bearing baseline assets first; after
    # linking, overlay alpha.4's exact two archives as a separate verified step.
    shutil.copytree(aim_mod / 'romfs', STAGE / 'weapon/romfs')
    input_meta = {'names': name_meta, 'aim': aim_meta, 'motion_payload': a4files,
                  'motion_validation_sha256': digest((alpha4_mod / 'release-validation.json').read_bytes()),
                  'motion_source_files': files(alpha4_src), 'motion_revision': a4proof['build_revision']}
    (STAGE / 'inputs.json').write_text(json.dumps(input_meta, indent=2) + '\n', encoding='utf-8')
    proof = {'version': VERSION, 'base_version': 'v0.1.0-alpha.3', 'base_payload': base_meta['payload_files'],
             'merged_weapon_sources': files(STAGE / 'weapon/module'), 'merged_local_sources': files(STAGE / 'module'),
             'production_changes': {'names': local_diff, 'aim': aim_diff, 'motions': tool_diff},
             'motion_changed_assets': differ, 'normal_payload': normal, 'normal_output_unchanged': True}
    assert files(HERE / 'output/magnet-spike-experimental') == normal
    (STAGE / 'baseline.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'prepared': True, 'version': VERSION, 'changes': proof['production_changes'], 'motion_assets': differ}))


if __name__ == '__main__': main()
