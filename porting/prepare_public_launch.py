"""Finalize public documentation and attachments around the tested sharpness fix.

No network access or publishing. Prior draft artifacts remain untouched.
"""
import hashlib,importlib.util,json,re,shutil,zipfile
from pathlib import Path
from prepare_frontier import HERE,sha
from hunt_session import files
from package_public_release import VERSION,NAME,DOCS,put,make_zip


def git_tree(root):
    entries=[]
    for p in root.iterdir():
        if p.is_dir():mode='40000';ident=git_tree(p);key=p.name+'/'
        else:
            mode='100644';b=p.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8')
            ident=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).digest();key=p.name
        entries.append((key.encode('utf-8'),mode.encode()+b' '+p.name.encode('utf-8')+b'\0'+ident))
    b=b''.join(x[1] for x in sorted(entries))
    return hashlib.sha1(b'tree '+str(len(b)).encode()+b'\0'+b).digest()


def main():
    stage=HERE/'public-release'/VERSION;old=stage/'sharpness-1';dest=stage/'public'
    if dest.exists():raise RuntimeError('Public launch staging already exists')
    prior=json.loads((HERE/'installed-build.json').read_text())
    proof=json.loads((HERE/'reports/sharpness-validation.json').read_text())
    install=json.loads((HERE/'reports/sharpness-install-integrity.json').read_text())
    payload=HERE/'test-profile/mods/magnet-spike-experimental'
    assert prior['revision']=='sharpness-1' and proof['all_passed'] and install['all_passed']
    assert files(payload)==prior['files']==proof['mod_files']==install['files']
    for p in proof['evidence'].values():assert sha(HERE/p['path'])==p['sha256']
    assert git_tree(old/'repo').hex()=='0693a77455466c13b846f3d63181477b4c866f96'
    repo=dest/'repo';ready=dest/'ready';shutil.copytree(old/'repo',repo);ready.mkdir()
    put(HERE/'prepare_public_launch.py',repo/'porting/prepare_public_launch.py')
    for name in ('README.md','INSTALL.md','CONTROLS.md','COMPATIBILITY.md','RELEASE_NOTES.md',
        'BUILDING.md','THIRD_PARTY_NOTICES.md'):
        put(DOCS/name,repo/name)
        put(DOCS/name,repo/'porting/release-docs'/name)
    # A public controls guide must not depend on a development save/profile.
    controls=(repo/'CONTROLS.md').read_text(encoding='utf-8')
    assert 'copied hunter' not in controls and 'BALANCE.md' not in controls
    broken=[]
    for p in repo.glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' in link or link.startswith('#'):continue
            target=link.split('#')[0]
            if target and not (p.parent/target).exists():broken.append((p.name,target))
    assert not broken,broken
    spec=importlib.util.spec_from_file_location('source_checker',DOCS/'check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker);count=checker.check(repo)
    # Check private workspace paths and obvious credential assignments only in
    # this task's new/changed public text; never scan credential stores.
    changed=[]
    for p in sorted(repo.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(repo);baseline=old/'repo'/rel
        if baseline.exists() and baseline.read_bytes()==p.read_bytes():continue
        text=p.read_text(encoding='utf-8').replace('\r\n','\n')
        assert not re.search(r'C:[/\\]Users[/\\]thesu|gh[pousr]_[A-Za-z0-9]{20,}',text),rel
        changed.append({'path':rel.as_posix(),'mode':'100644','type':'blob','content':text})
    mod_zip=ready/('Magnet-Spike-'+VERSION+'.zip')
    items=[('Magnet-Spike/'+p.relative_to(payload).as_posix(),p) for p in payload.rglob('*') if p.is_file()]
    for name in ('README.md','INSTALL.md','COMPATIBILITY.md','CONTROLS.md','RELEASE_NOTES.md',
        'LICENSE','THIRD_PARTY_NOTICES.md','release-validation.json'):
        items.append(('Magnet-Spike/'+name,repo/name))
    make_zip(mod_zip,items)
    source_zip=ready/('Magnet-Spike-'+VERSION+'-source.zip')
    make_zip(source_zip,[(NAME+'-'+VERSION+'/'+p.relative_to(repo).as_posix(),p)
        for p in repo.rglob('*') if p.is_file()])
    manifest=json.loads((old/'ready/release-manifest.json').read_text())
    # GitHub is authoritative for whether a release has been published. Do not
    # encode the previous draft's transient published=false in a public artifact.
    manifest.pop('published',None)
    manifest.update(source_file_count=count,
        source_files={p.relative_to(repo).as_posix():sha(p) for p in repo.rglob('*') if p.is_file()},
        downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)})
    (ready/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    put(repo/'release-validation.json',ready/'release-validation.json')
    (ready/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in
        (mod_zip,source_zip,ready/'release-manifest.json',ready/'release-validation.json')),encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        actual={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
            if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
        assert actual==manifest['payload_files']
    (dest/'source-update.json').write_text(json.dumps(changed,ensure_ascii=False)+'\n',encoding='utf-8')
    report={'version':VERSION,'build_revision':'sharpness-1','all_passed':True,
        'payload_exactly_matches_installed_tested_fix':True,'payload_files':len(actual),
        'source_only_files':count,'source_tree_sha':git_tree(repo).hex(),
        'changed_source_files':[x['path'] for x in changed],'top_level_documentation_links_pass':True,
        'attachments':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ready.iterdir()},
        'publication_status':'prepared_not_yet_published'}
    (HERE/'reports/public-launch-preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='attachments'},indent=2))


if __name__=='__main__':main()
