"""Package a complete public-build sprinting-roll test candidate; no install/upload."""
import importlib.util
import json
import shutil
import zipfile
import hashlib
from build_module import HERE,MS,sha
from feedback_session import files
from package_public_release import make_zip
from prepare_public_launch import git_tree


def main():
    proof_path=HERE/'reports/sprint-roll-validation.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    payload=HERE/'output/magnet-spike-experimental'
    assert proof['all_passed'] and proof['payload_files']==files(payload)
    for item in proof['evidence'].values():assert sha(HERE/item['path'])==item['sha256']
    dest=HERE/'public-release/sprint-roll-fix-1'
    if dest.exists():raise RuntimeError('Candidate already exists; do not overwrite tested artifacts')
    repo=dest/'source';ready=dest/'ready'
    shutil.copytree(HERE/'public-release/v0.1.0-alpha.2/repo',repo);ready.mkdir()
    changed=[MS/'module/ms_act.c',HERE/'exercise_sprint_roll.py',HERE/'test_sprint_roll.py',
        HERE/'tests/sprint_roll_harness.c',HERE/'validate_sprint_roll.py',HERE/'package_sprint_roll.py',
        HERE/'SPRINT_ROLL_FIX.md']
    for p in changed:
        target=repo/'porting'/p.relative_to(HERE);target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(p,target)
    shutil.copyfile(HERE/'SPRINT_ROLL_FIX.md',repo/'SPRINT_ROLL_FIX.md')
    for name in ('CONTROLS.md',):
        shutil.copyfile(HERE/'release-docs'/name,repo/name)
        shutil.copyfile(HERE/'release-docs'/name,repo/'porting/release-docs'/name)
    prefix=('# Sprinting roll fix — local test candidate\n\n'
        'Includes alpha.2 and the verified sheathed sprint-roll fix. Use '
        '**Magnet-Spike-Sprint-Roll-Fix.zip** to play. '
        'Read [SPRINT_ROLL_FIX.md](SPRINT_ROLL_FIX.md) before installing. '
        'This candidate has not been installed or published to GitHub.\n\n')
    (repo/'README.md').write_text(prefix+(repo/'README.md').read_text(encoding='utf-8'),encoding='utf-8')
    install=(repo/'INSTALL.md').read_text(encoding='utf-8').replace('# Install v0.1.0-alpha.2','# Install the sprinting-roll test candidate').replace('Magnet-Spike-v0.1.0-alpha.2.zip','Magnet-Spike-Sprint-Roll-Fix.zip')
    (repo/'INSTALL.md').write_text(install,encoding='utf-8')
    (repo/'release-validation.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    for p in repo.rglob('*'):
        if p.is_file():p.write_bytes(p.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8'))
    spec=importlib.util.spec_from_file_location('sprint_source_check',HERE/'release-docs/check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    count=checker.check(repo)
    entries=[('Magnet-Spike/'+p.relative_to(payload).as_posix(),p) for p in payload.rglob('*') if p.is_file()]
    for name in ('README.md','INSTALL.md','CONTROLS.md','COMPATIBILITY.md','LICENSE','THIRD_PARTY_NOTICES.md','SPRINT_ROLL_FIX.md','release-validation.json'):
        entries.append(('Magnet-Spike/'+name,repo/name))
    mod_zip=ready/'Magnet-Spike-Sprint-Roll-Fix.zip'
    source_zip=ready/'Magnet-Spike-Sprint-Roll-Fix-source.zip'
    make_zip(mod_zip,entries)
    make_zip(source_zip,[('Magnet-Spike-Sprint-Roll-Fix-source/'+p.relative_to(repo).as_posix(),p) for p in repo.rglob('*') if p.is_file()])
    with zipfile.ZipFile(mod_zip) as z:
        assert z.testzip() is None
        actual={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
    assert actual==proof['payload_files']
    with zipfile.ZipFile(source_zip) as z:assert z.testzip() is None
    downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)}
    (ready/'SHA256SUMS.txt').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in downloads.items()),encoding='utf-8')
    receipt={'revision':'sprint-roll-1','all_passed':True,'source_files':count,
        'source_git_tree':git_tree(repo).hex(),'payload_files':actual,'downloads':downloads,
        'validation_sha256':sha(proof_path),'installed':False,'published':False}
    (HERE/'reports/sprint-roll-packaging.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_files':count,'payload_files':len(actual),'downloads':downloads}))


if __name__=='__main__':main()
