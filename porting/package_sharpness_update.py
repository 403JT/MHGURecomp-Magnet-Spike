"""Prepare a new private-draft attachment set without overwriting the old one."""
import hashlib,importlib.util,json,shutil,zipfile
from pathlib import Path
from prepare_frontier import HERE,sha
from hunt_session import files
from package_public_release import VERSION,NAME,DOCS,put,make_zip


def main():
    previous=HERE/'public-release'/VERSION
    dest=previous/'sharpness-1';assert not dest.exists(),'Update staging already exists'
    r=json.loads((HERE/'reports/sharpness-validation.json').read_text())
    install=json.loads((HERE/'reports/sharpness-install-integrity.json').read_text())
    prior=json.loads((HERE/'installed-build.json').read_text())
    payload=HERE/'test-profile/mods/magnet-spike-experimental'
    assert r['all_passed'] and install['all_passed'] and prior['revision']=='sharpness-1'
    assert files(payload)==r['mod_files']==install['files']==prior['files']
    for e in r['evidence'].values():assert sha(HERE/e['path'])==e['sha256']
    repo=dest/'repo';ready=dest/'ready';shutil.copytree(previous/'repo',repo);ready.mkdir()
    sources=['build_module.py','test_sharpness.py','exercise_sharpness.py',
        'validate_sharpness.py','install_sharpness_candidate.py','package_sharpness_update.py']
    for n in sources:put(HERE/n,repo/'porting'/n)
    for n in ('README.md','INSTALL.md','COMPATIBILITY.md','RELEASE_NOTES.md'):
        put(DOCS/n,repo/n);put(DOCS/n,repo/'porting/release-docs'/n)
    arm=json.loads((HERE/'reports/sharpness-regression.json').read_text())
    native=[json.loads((HERE/r['evidence'][k]['path']).read_text()) for k in ('whetstone','red_case','crafted')]
    assert all(x['all_passed'] and x['mod_files']==prior['files'] for x in native)
    old_proof=json.loads((previous/'repo/release-validation.json').read_text())
    proof={'mod_version':VERSION,'build_revision':'sharpness-1','game':'MHGU 1.4.0',
        'runtime':'official MHGURecomp 0.18.0 Windows x64','language':'English',
        'module_sha256':prior['module_sha256'],'normal_builtin_mod_loader':True,
        'runtime_executable_sha256':native[0]['runtime_sha256'],
        'change':'One equipment-type mask admits type12 to the native sharpness-level getter.',
        'code_module_and_all_assets_identical_to_recovery_1':True,
        'tests':[{'scenario':'Native ARM sharpness getters, colours, skills and Whetstone restoration',
            'passed':arm['all_passed'],'levels':arm['levels_checked'],'Handicraft_cases':arm['skill_cases'],
            'restoration_calls':arm['native_whetstone_calls'],'checks':arm['checks']},
            *[{'scenario':scenario,'passed':p['all_passed'],'checks':p['checks'],
                'weapon_id':p['fixture']['weapon_id'],'level':p['fixture']['level'],
                'starting_sharpness':p['samples']['quest-start'],
                **({'loss_and_recovery':p['native_loss_and_recovery']} if 'native_loss_and_recovery' in p else {})}
                for scenario,p in zip(('Real collision and ordinary Whetstone use','Previously red-capped family',
                    'Previously crafted equipment, no weapon-entry edit'),native)]],
        'historical_recovery_1_smoke_tests':old_proof['tests'],
        'historical_test_scope':'Before this single-mask fix; module and assets are byte-identical. Only the current sharpness cases above used the updated IPS.',
        'limits':old_proof['limits']+['Focused sharpness correction, no new full-hunt or damage-balance guarantee.']}
    (repo/'release-validation.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    spec=importlib.util.spec_from_file_location('source_check',DOCS/'check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker);count=checker.check(repo)
    mod_zip=ready/('Magnet-Spike-'+VERSION+'.zip')
    entries=[('Magnet-Spike/'+p.relative_to(payload).as_posix(),p) for p in payload.rglob('*') if p.is_file()]
    for n in ('README.md','INSTALL.md','COMPATIBILITY.md','CONTROLS.md','LICENSE','THIRD_PARTY_NOTICES.md','release-validation.json'):
        entries.append(('Magnet-Spike/'+n,repo/n))
    make_zip(mod_zip,entries)
    source_zip=ready/('Magnet-Spike-'+VERSION+'-source.zip')
    make_zip(source_zip,[(NAME+'-'+VERSION+'/'+p.relative_to(repo).as_posix(),p) for p in repo.rglob('*') if p.is_file()])
    manifest=json.loads((previous/'ready/release-manifest.json').read_text())
    manifest.update(build_revision='sharpness-1',published=False,
        source_file_count=count,source_files={p.relative_to(repo).as_posix():sha(p) for p in repo.rglob('*') if p.is_file()},
        payload_files={k.replace('\\','/'):v for k,v in prior['files'].items()},
        downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)})
    (ready/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    put(repo/'release-validation.json',ready/'release-validation.json')
    (ready/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in
        (mod_zip,source_zip,ready/'release-manifest.json',ready/'release-validation.json')),encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        actual={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
            if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
        assert actual==manifest['payload_files']
    changed=[]
    for p in sorted(repo.rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(repo);old=previous/'repo'/rel
        if not old.exists() or p.read_bytes()!=old.read_bytes():
            changed.append({'path':rel.as_posix(),'mode':'100644','type':'blob',
                'content':p.read_text(encoding='utf-8').replace('\r\n','\n')})
    # Only locally scanned text sources and public aggregate validation travel
    # through Git's object API; generated assets remain release attachments.
    upload=dest/'source-update.json'
    upload.write_text(json.dumps(changed,ensure_ascii=False)+'\n',encoding='utf-8')
    report={'version':VERSION,'revision':'sharpness-1','all_passed':True,'private':True,'draft':True,
        'source_file_count':count,'changed_source_files':[x['path'] for x in changed],
        'attachments':{p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in ready.iterdir()},
        'payload_file_count':len(actual),'mod_files':prior['files']}
    (HERE/'reports/sharpness-release-packaging.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Prepared updated private-draft attachments:',count,'source files;',len(changed),'changed text files;',len(actual),'payload files.')


if __name__=='__main__':main()
