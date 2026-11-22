"""Create separate source-only staging and normal-loader mod ZIPs; never publish."""
import argparse,hashlib,importlib.util,json,shutil,zipfile
from pathlib import Path
from prepare_frontier import HERE,ROOT,CONVERTER,REV,sha
from hunt_session import files

VERSION='v0.1.0-alpha.1'
OWNER='403JT'
NAME='MHGURecomp-Magnet-Spike'
DOCS=HERE/'release-docs'
SOURCE_SUFFIXES={'.py','.c','.h','.cpp','.hpp','.S','.s','.ld','.md','.toml','.json',
    '.rs','.sh','.ps1','.txt','.yml','.yaml','.in','.po','.pot','.cfg','.template'}
SKIP={'.git','.venv','__pycache__','dump','gen','romfs','out','output','work','runs',
    'backups','ryuroot','target','node_modules','release-validation','test-profile'}
ROOT_NAMES={'LICENSE','COPYING','NOTICE','.gitignore','.gitattributes','Makefile','Cargo.lock'}


def put(src,dest):
    if src.is_symlink():raise RuntimeError('Symlink in source selection')
    dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)


def source_copy(src,dest):
    n=0
    for p in sorted(src.rglob('*')):
        rel=p.relative_to(src)
        if any(x in SKIP for x in rel.parts) or not p.is_file():continue
        if p.suffix in SOURCE_SUFFIXES or p.name in ROOT_NAMES or p.name.startswith(('LICENSE','COPYING','NOTICE')):
            put(p,dest/rel);n+=1
    return n


def make_zip(path,entries):
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,p in sorted(entries):
            i=zipfile.ZipInfo(name,date_time=(2026,11,22,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED
            i.external_attr=0o100644<<16;z.writestr(i,p.read_bytes())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--version',default=VERSION);a=ap.parse_args()
    if a.version!=VERSION:raise RuntimeError('Update reviewed version metadata before another release')
    prior=json.loads((HERE/'installed-build.json').read_text(encoding='utf-8'))
    payload=HERE/'test-profile/mods/magnet-spike-experimental'
    if prior['revision']!='recovery-1' or files(payload)!=prior['files']:
        raise RuntimeError('Installed build does not match the intended recovery-1 payload')
    vpath=Path(prior['validation_receipt'])
    if sha(vpath)!=prior['validation_receipt_sha256'] or not json.loads(vpath.read_text())['all_passed']:
        raise RuntimeError('Installed validation receipt is stale')
    integrity=json.loads((HERE/'reports/combo-recovery-install-integrity.json').read_text())
    if not integrity['all_passed'] or integrity['module_sha256']!=prior['module_sha256']:
        raise RuntimeError('Installed integrity check is missing')
    allowed={'exefs','romfs'}
    if len(prior['files'])!=56 or any(Path(p).parts[0] not in allowed for p in prior['files']):
        raise RuntimeError('Unexpected mod payload path')
    dest=HERE/'public-release'/VERSION
    if dest.exists():raise RuntimeError('Release staging already exists; evidence is not overwritten')
    repo=dest/'repo';dist=dest/'dist';repo.mkdir(parents=True);dist.mkdir()
    for name in ('README.md','INSTALL.md','COMPATIBILITY.md','RELEASE_NOTES.md','BUILDING.md','THIRD_PARTY_NOTICES.md'):
        put(DOCS/name,repo/name)
    put(DOCS/'gitignore.template',repo/'.gitignore')
    put(DOCS/'bug_report.yml',repo/'.github/ISSUE_TEMPLATE/bug_report.yml')
    put(DOCS/'check_source_tree.py',repo/'check_source_tree.py')
    put(CONVERTER/'LICENSE',repo/'LICENSE')
    put(HERE/'CONTROLS.md',repo/'CONTROLS.md')
    for p in sorted(HERE.glob('*.py')):put(p,repo/'porting'/p.name)
    put(HERE/'balance-policy.json',repo/'porting/balance-policy.json')
    source_copy(HERE/'module',repo/'porting/module')
    source_copy(HERE/'tests',repo/'porting/tests')
    # Only the MIT audio encoder is bundled. External ReFrontier code and the
    # local extraction codec are not part of this publication tree.
    put(HERE/'codec/dsp_encode.c',repo/'porting/codec/dsp_encode.c')
    source_copy(HERE/'third_party/gc-dspadpcm-encode',repo/'porting/third_party/gc-dspadpcm-encode')
    source_copy(CONVERTER,repo/'porting/third_party'/CONVERTER.name)
    # Package tooling can also be inspected/re-run in the source snapshot.
    source_copy(DOCS,repo/'porting/release-docs')
    spec=importlib.util.spec_from_file_location('release_source_check',DOCS/'check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    count=checker.check(repo)
    source_manifest={str(p.relative_to(repo)).replace('\\','/'):sha(p) for p in repo.rglob('*') if p.is_file()}
    mod_zip=dist/('Magnet-Spike-'+VERSION+'.zip')
    entries=[('Magnet-Spike/'+str(p.relative_to(payload)).replace('\\','/'),p) for p in payload.rglob('*') if p.is_file()]
    for name in ('README.md','INSTALL.md','COMPATIBILITY.md','CONTROLS.md','LICENSE','THIRD_PARTY_NOTICES.md'):
        entries.append(('Magnet-Spike/'+name,repo/name))
    make_zip(mod_zip,entries)
    source_zip=dist/('Magnet-Spike-'+VERSION+'-source.zip')
    make_zip(source_zip,[(NAME+'-'+VERSION+'/'+str(p.relative_to(repo)).replace('\\','/'),p) for p in repo.rglob('*') if p.is_file()])
    manifest={'version':VERSION,'repository':f'https://github.com/{OWNER}/{NAME}',
        'release_type':'prerelease','build_revision':prior['revision'],'module_sha256':prior['module_sha256'],
        'game_version':'MHGU 1.4.0','game_build_id':'FB08F1D20FD1204FE7070672777F869B',
        'language':'English','initial_platform':'Windows x64','play_mode':'single-player',
        'runtime_compatibility':{'status':'pending_official_runtime_test','target':'MHGURecomp 0.18.0'},
        'payload_files':{k.replace('\\','/'):v for k,v in prior['files'].items()},
        'source_base':{'project':'Scrimas/MHGU-Definitive-Edition','revision':REV,'license':'GPL-3.0-or-later'},
        'source_file_count':count,'source_files':source_manifest,
        'downloads':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)},
        'contains_game_executable':False,'contains_saves_or_test_captures':False,
        'published':False,'full_frontier_parity':False}
    (dist/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (dist/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in (mod_zip,source_zip,dist/'release-manifest.json')),encoding='utf-8')
    # Verify payload bytes straight from the distributable, including nested paths.
    with zipfile.ZipFile(mod_zip) as z:
        actual={n[len('Magnet-Spike/'):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
            if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
    if actual!=manifest['payload_files']:raise RuntimeError('ZIP payload differs from the tested installation')
    (HERE/'reports/public-release-packaging.json').write_text(json.dumps({
        'version':VERSION,'source_only_check_passed':True,'source_file_count':count,
        'exact_installed_payload_verified':True,'payload_file_count':len(actual),
        'downloads':manifest['downloads'],'runtime_validation_pending':True,'published':False},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'version':VERSION,'source_files':count,'payload_files':len(actual),'downloads':manifest['downloads']}))


if __name__=='__main__':main()
