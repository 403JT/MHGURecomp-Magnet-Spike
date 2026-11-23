"""Stage the authorised alpha.2 release from the exact tested feedback payload.

No install, game launch, credential access, network access or publishing.
"""
import hashlib
import importlib.util
import json
import shutil
import zipfile
from prepare_frontier import HERE,sha
from build_module import MS
from feedback_session import files
from package_public_release import DOCS,NAME,make_zip,put
from prepare_public_launch import git_tree

VERSION='v0.1.0-alpha.2'


def main():
    proof_path=HERE/'reports/feedback-2-validation.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    receipt=json.loads((HERE/'reports/feedback-2-packaging.json').read_text(encoding='utf-8'))
    payload=HERE/'output/magnet-spike-experimental'
    expected=files(payload)
    assert proof['all_passed'] and all(proof['checks'].values()) and proof['target']=='recomp'
    assert receipt['payload_files']==proof['payload_files']==expected and len(expected)==56
    assert receipt['validation_sha256']==sha(proof_path)
    for item in proof['evidence'].values():assert sha(HERE/item['path'])==item['sha256']
    candidate=HERE/'public-release/feedback-candidate-2'
    for name,item in receipt['downloads'].items():assert sha(candidate/'ready'/name)==item['sha256']
    dest=HERE/'public-release'/VERSION
    if dest.exists():raise RuntimeError('Release already staged; do not overwrite evidence')
    repo=dest/'repo';ready=dest/'ready'
    shutil.copytree(candidate/'source',repo);ready.mkdir()
    for name in ('README.md','INSTALL.md','COMPATIBILITY.md','RELEASE_NOTES.md','BUILDING.md','THIRD_PARTY_NOTICES.md'):
        put(DOCS/name,repo/name)
    for p in DOCS.iterdir():
        if p.is_file():put(p,repo/'porting/release-docs'/p.name)
    put(HERE/'FEEDBACK_FIXES.md',repo/'FEEDBACK_FIXES.md')
    put(HERE/'FEEDBACK_FIXES.md',repo/'porting/FEEDBACK_FIXES.md')
    put(HERE/'package_feedback_release.py',repo/'porting/package_feedback_release.py')
    # Compare every production source file with the frozen tested snapshot.
    for source in list((MS/'module').glob('*'))+list((HERE/'module').glob('*')):
        if source.is_file():assert sha(source)==sha(repo/'porting'/source.relative_to(HERE))
    validation={
        'mod_version':VERSION,'build_revision':'feedback-2','target':'recomp',
        'game':'MHGU 1.4.0 English','runtime':'official MHGURecomp 0.18.0 Windows x64',
        'module_sha256':expected['exefs/subsdk1'],
        'ips_sha256':next(v for k,v in expected.items() if k.endswith('.ips')),
        'all_focused_checks_passed':True,'validation_checks':proof['checks'],
        'validation_gate_count':len(proof['checks']),
        'regression_counts':{'damage_cancellation':61,'marker_tasks':190,'state_pool':80,
            'recovery':2031,'quick_message':261,'combo_recovery':441,'balance':11,
            'sharpness_levels':959,'sharpness_skill_cases':2877,'native_whetstone_calls':17262},
        'native_tests':[],
        'unchanged':['all 54 RomFS assets','weapon IDs and smithy recipes','damage values',
            'combo links and recovery durations','marker/shot attachment math',
            'guard windows and gauge costs','scope selection','attraction physics'],
        'connected_multiplayer_tested':False,'diablos_play_tested':False,
        'full_play_validation_complete':False,'full_frontier_parity':False,
        'remaining_reports':proof['remaining_reports'],
        'limits':['Focused fixtures are not connected multiplayer hunts.',
            'The intermittent R+X and parry freezes remain unconfirmed.',
            'The glow fix addresses a reproduced remote-update cause, not every possible occurrence.',
            'Broad long-hunt lifecycle coverage, other platforms/languages and mod combinations remain unvalidated.'],
        'evidence_sha256':{k:v['sha256'] for k,v in proof['evidence'].items()}}
    for name,info in proof['evidence'].items():
        if not name.startswith('native_'):continue
        run=json.loads((HERE/info['path']).read_text(encoding='utf-8'))
        assert run['payload_files']==expected and run['all_passed']
        assert run['source_saves_unchanged'] and run['muted'] and run['exit_code']==0 and not run['fatal']
        validation['native_tests'].append({'scenario':name,'runtime':run['runtime'],
            'runtime_sha256':run['runtime_sha256'],'cases':len(run['cases']),
            'passed':True,'muted':True,'source_saves_unchanged':True,'clean_exit':True})
    (repo/'release-validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    # Match the published Git tree and source ZIP byte-for-byte using UTF-8/LF.
    for p in repo.rglob('*'):
        if p.is_file():p.write_bytes(p.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8'))
    spec=importlib.util.spec_from_file_location('feedback_release_source_check',DOCS/'check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    source_count=checker.check(repo)
    tree=git_tree(repo).hex()
    mod_zip=ready/f'Magnet-Spike-{VERSION}.zip'
    source_zip=ready/f'Magnet-Spike-{VERSION}-source.zip'
    docs=('README.md','INSTALL.md','COMPATIBILITY.md','CONTROLS.md','LICENSE','THIRD_PARTY_NOTICES.md',
          'FEEDBACK_FIXES.md','RELEASE_NOTES.md','release-validation.json')
    entries=[('Magnet-Spike/'+p.relative_to(payload).as_posix(),p) for p in payload.rglob('*') if p.is_file()]
    make_zip(mod_zip,entries+[('Magnet-Spike/'+name,repo/name) for name in docs])
    make_zip(source_zip,[(NAME+'-'+VERSION+'/'+p.relative_to(repo).as_posix(),p) for p in repo.rglob('*') if p.is_file()])
    downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)}
    manifest={'version':VERSION,'release_type':'prerelease','build_revision':'feedback-2',
        'repository':'https://github.com/403JT/'+NAME,'game_version':'MHGU 1.4.0',
        'language':'English','runtime':'MHGURecomp 0.18.0 Windows x64','target':'recomp',
        'payload_files':expected,'source_git_tree':tree,'source_file_count':source_count,
        'source_files':{p.relative_to(repo).as_posix():sha(p) for p in repo.rglob('*') if p.is_file()},
        'downloads':downloads,'focused_validation_passed':True,
        'connected_multiplayer_tested':False,'full_play_validation_complete':False,
        'contains_game_executable':False,'contains_saves_or_test_captures':False,'published':False}
    (ready/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    put(repo/'release-validation.json',ready/'release-validation.json')
    (ready/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in
        (mod_zip,source_zip,ready/'release-manifest.json',ready/'release-validation.json')),encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        assert z.testzip() is None
        actual={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest()
            for n in z.namelist() if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
    assert actual==expected
    with zipfile.ZipFile(source_zip) as z:assert z.testzip() is None
    report={'version':VERSION,'all_passed':True,'source_only_tree_passed':True,
        'source_file_count':source_count,'source_git_tree':tree,'exact_tested_payload':True,
        'payload_files':expected,'downloads':downloads,'validation_sha256':sha(proof_path),
        'release_authorised_by_user':True,'published':False,'installed':False}
    (HERE/'reports/feedback-release-preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('version','all_passed','source_file_count','source_git_tree','downloads')}))


if __name__=='__main__':main()
