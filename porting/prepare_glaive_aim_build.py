"""Prepare an isolated alpha.3 aiming branch without touching other work."""
import json
import shutil
import zipfile
from build_module import HERE, MS
from feedback_session import files

STAGE = HERE / 'aim-dev/alpha3-glaive-aim-1'
BASE = HERE / 'public-release/v0.1.0-alpha.3'


def main():
    if STAGE.exists(): raise RuntimeError('Isolated aiming branch already exists')
    before = files(HERE / 'output/magnet-spike-experimental')
    baseline = json.loads((BASE / 'ready/release-manifest.json').read_text(encoding='utf-8'))
    repo = BASE / 'repo'
    source_ms = repo / 'porting' / MS.relative_to(HERE)
    shutil.copytree(source_ms / 'module', STAGE / 'weapon/module')
    shutil.copytree(repo / 'porting/module', STAGE / 'module')
    shutil.copytree(MS / 'gen', STAGE / 'weapon/gen')
    # Assets are unchanged in this separate aim-only alpha.3 branch.
    shutil.copytree(MS / 'romfs', STAGE / 'weapon/romfs')
    with zipfile.ZipFile(BASE / 'ready/Magnet-Spike-v0.1.0-alpha.3.zip') as z:
        for name in z.namelist():
            if name.startswith(('Magnet-Spike/exefs/', 'Magnet-Spike/romfs/')) and not name.endswith('/'):
                dest = STAGE / 'baseline-payload' / name.removeprefix('Magnet-Spike/')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))
    assert files(STAGE / 'baseline-payload') == baseline['payload_files']
    assert all(files(STAGE / 'weapon/romfs')[n.removeprefix('romfs/')] == h
               for n, h in baseline['payload_files'].items() if n.startswith('romfs/'))
    assert files(HERE / 'output/magnet-spike-experimental') == before
    proof = {'base_version': baseline['version'], 'base_payload': baseline['payload_files'],
             'source_files_before': files(STAGE / 'weapon/module'),
             'local_module_before': files(STAGE / 'module'), 'normal_output_unchanged': True,
             'stall_fix_included': False, 'name_fix_included': False}
    (STAGE / 'baseline.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print('Prepared isolated original-alpha.3 aiming branch:', STAGE)


if __name__ == '__main__': main()
