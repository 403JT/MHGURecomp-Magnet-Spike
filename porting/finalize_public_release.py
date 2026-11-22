"""Finalize locally reviewed attachments after official-runtime tests; no upload."""
import importlib.util,json,shutil,zipfile,hashlib
from pathlib import Path
from prepare_frontier import HERE,ROOT,sha
from hunt_session import files
from package_public_release import VERSION,NAME,DOCS,source_copy,make_zip,put


def main():
    stage=HERE/'public-release'/VERSION;repo=stage/'repo';ready=stage/'ready'
    if ready.exists():raise RuntimeError('Final release attachments already exist')
    runs=[HERE/'runs'/label/'public-release-run.json' for label in
        ('release-official-equipped-1','release-official-pristine-1')]
    proof=[json.loads(p.read_text(encoding='utf-8')) for p in runs]
    assert all(p['all_passed'] and all(p['checks'].values()) and p['output_muted'] for p in proof)
    prior=json.loads((HERE/'installed-build.json').read_text())
    expected={k.replace('\\','/'):v for k,v in prior['files'].items()}
    assert all(p['payload_files']==expected for p in proof)
    runtime_zip=HERE/'release-validation/downloads/Windows-MHGURecomp.0.18.0.zip'
    assert sha(runtime_zip)=='f29342e8d58a4dda1e1ca5aa580dc048834cc3ea53c633c99e83df07cc509ce6'
    for name in ('README.md','INSTALL.md','COMPATIBILITY.md','RELEASE_NOTES.md','BUILDING.md','THIRD_PARTY_NOTICES.md'):
        put(DOCS/name,repo/name)
    for p in HERE.glob('*.py'):put(p,repo/'porting'/p.name)
    source_copy(DOCS,repo/'porting/release-docs')
    source_copy(HERE/'third_party/gc-dspadpcm-encode',repo/'porting/third_party/gc-dspadpcm-encode')
    spec=importlib.util.spec_from_file_location('source_check',DOCS/'check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    source_count=checker.check(repo)
    public_proof={'mod_version':VERSION,'build_revision':prior['revision'],
        'game':'MHGU 1.4.0','language':'English','runtime':'official MHGURecomp 0.18.0 Windows x64',
        'runtime_download_sha256':sha(runtime_zip),'runtime_executable_sha256':proof[0]['runtime_executable_sha256'],
        'module_sha256':prior['module_sha256'],'normal_builtin_mod_loader':True,
        'tests':[{'scenario':'Equipped Magnet Spike: startup, normal right-button combo and finisher recovery',
            'passed':proof[0]['all_passed'],'checks':proof[0]['checks']},
            {'scenario':'Unmodified save with no Magnet Spike gear: normal town startup',
            'passed':proof[1]['all_passed'],'checks':proof[1]['checks']}],
        'payload_exactly_matches_installed_recovery_1':True,
        'prior_checks':{'ARM_recovery_checks':441,'native_command_rows':129,'recovery_validation_gates':19},
        'limits':['These are focused smoke tests, not a complete hunt campaign.',
            'No fresh smithy transaction was performed on the official0.18.0 runtime in these smoke tests; prior crafting evidence used the same guest game and mod code.',
            'Multiplayer, other languages/platforms and general mod combinations are not validated.',
            'Long-hunt, faint/capture/multiple-large-monster coverage remains incomplete.']}
    (repo/'release-validation.json').write_text(json.dumps(public_proof,indent=2)+'\n',encoding='utf-8')
    ready.mkdir()
    payload=HERE/'test-profile/mods/magnet-spike-experimental'
    mod_zip=ready/('Magnet-Spike-'+VERSION+'.zip')
    entries=[('Magnet-Spike/'+str(p.relative_to(payload)).replace('\\','/'),p) for p in payload.rglob('*') if p.is_file()]
    for name in ('README.md','INSTALL.md','COMPATIBILITY.md','CONTROLS.md','LICENSE','THIRD_PARTY_NOTICES.md','release-validation.json'):
        entries.append(('Magnet-Spike/'+name,repo/name))
    make_zip(mod_zip,entries)
    source_zip=ready/('Magnet-Spike-'+VERSION+'-source.zip')
    make_zip(source_zip,[(NAME+'-'+VERSION+'/'+str(p.relative_to(repo)).replace('\\','/'),p) for p in repo.rglob('*') if p.is_file()])
    old=json.loads((stage/'dist/release-manifest.json').read_text())
    old.update(runtime_compatibility={'status':'passed_focused_smoke_tests','runtime':'official MHGURecomp 0.18.0 Windows x64',
        'runtime_archive_sha256':sha(runtime_zip),'validation_file':'release-validation.json'},
        source_file_count=source_count+1,
        source_files={str(p.relative_to(repo)).replace('\\','/'):sha(p) for p in repo.rglob('*') if p.is_file()},
        downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)},
        published=False)
    (ready/'release-manifest.json').write_text(json.dumps(old,indent=2)+'\n',encoding='utf-8')
    put(repo/'release-validation.json',ready/'release-validation.json')
    (ready/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in
        (mod_zip,source_zip,ready/'release-manifest.json',ready/'release-validation.json')),encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        actual={n[len('Magnet-Spike/'):]:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
            if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
        assert actual==expected
        assert all(not any(x in Path(n).parts for x in ('save','runs','cache','data','MHFZZ')) for n in z.namelist())
    checker.check(repo)
    report={'version':VERSION,'all_passed':True,'official_runtime_tests_passed':True,
        'source_only_tree_passed':True,'exact_validated_payload':True,'payload_file_count':len(expected),
        'source_file_count':source_count+1,'downloads':old['downloads'],'published':False,
        'target_repository':old['repository'],'connection_verified_as':'403JT'}
    (HERE/'reports/public-release-final-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
