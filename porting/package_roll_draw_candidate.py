"""Prepare local normal/diagnostic test packages; never install or publish."""
import hashlib
import importlib.util
import json
import shutil
import zipfile
from build_module import HERE,MS,sha
from feedback_session import files
from package_public_release import make_zip
from prepare_public_launch import git_tree


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    revision='roll-draw-candidate-1'
    payload=HERE/'output/magnet-spike-experimental'
    diagnostic=HERE/'output/freeze-diagnostics/magnet-spike-experimental'
    normal_files,diag_files=files(payload),files(diagnostic)
    baseline=files(HERE/'backups/before-sprint-roll-1/payload')
    evidence={}
    checks={}
    names=('guard-draw-regression','sprint-roll-regression','feedback-recovery-regression',
           'damage-feedback-regression','feedback-repeat-hit-regression',
           'feedback-state-pool-regression','freeze-trace-regression')
    for name in names:
        path=HERE/'reports'/(name+'.json');report=read(path)
        checks[name]=report['all_passed'];evidence[name]={'path':path.relative_to(HERE).as_posix(),'sha256':sha(path)}
    runs={}
    for label,expected in (('draw-chord-fixed-2',normal_files),('sprint-roll-draw-fixed-1',normal_files),
                           ('freeze-diagnostic-smoke-2',diag_files)):
        path=HERE/'runs'/label/'feedback-native.json';r=read(path);runs[label]=r
        checks[label+'_integrity']=(r['payload_files']==expected and r['source_saves_unchanged']
            and r['tested_payload_unchanged'] and r['muted'] and r['exit_code']==0
            and not r['failure'] and not r['fatal'])
        evidence[label]={'path':path.relative_to(HERE).as_posix(),'sha256':sha(path)}
    draw=runs['draw-chord-fixed-2']['cases']
    checks['standing_and_moving_guard_draw']=len(draw)==2 and all(c['ordinary_inputs'] and c['before_table']==1000
        and c['weapon_actions']==[112] and c['after_table']==2000 and c['after']['category']!=16
        and not any(cat==32 for cat,no in c['native_actions']) for c in draw)
    checks['four_native_roll_cases']=runs['sprint-roll-draw-fixed-1']['all_passed']
    checks['diagnostic_native_smoke']=runs['freeze-diagnostic-smoke-2']['all_passed']
    checks['normal_only_NSO_changed_since_alpha2']=[n for n in normal_files if normal_files[n]!=baseline.get(n)]==['exefs/subsdk1']
    checks['normal_file_set_preserved']=normal_files.keys()==baseline.keys() and len(normal_files)==56
    checks['diagnostic_assets_preserved']=all(diag_files[n]==v for n,v in normal_files.items() if n.startswith('romfs/'))
    # installed-build.json predates the alpha.1 public-payload handoff. Use
    # the preserved installed/public snapshot, not that older sharpness receipt.
    checks['installed_profile_unchanged']=files(HERE/'test-profile/mods/magnet-spike-experimental')==files(HERE/'backups/before-feedback-1/public-payload')
    normal_status=read(HERE/'output/module-status.json')
    diag_status=read(HERE/'output/freeze-diagnostics/module-status.json')
    checks['builds_bound_to_receipts']=(normal_status['module_sha256']==normal_files['exefs/subsdk1'] and
        diag_status['module_sha256']==diag_files['exefs/subsdk1'] and normal_status['hooks']==diag_status['hooks']==32
        and normal_status['patch_records']==diag_status['patch_records']==106)
    checks['logging_opt_in_only']='MS_FREEZE_DIAGNOSTICS' not in normal_status['defines'] and 'MS_FREEZE_DIAGNOSTICS' in diag_status['defines']
    assert all(checks.values()),[n for n,v in checks.items() if not v]
    proof={'revision':revision,'all_passed':True,'checks':checks,'evidence':evidence,
        'payload_files':normal_files,'diagnostic_payload_files':diag_files,
        'video_freeze_reproduced':False,'video_freeze_fixed':False,
        'fixes':['sheathed sprinting roll','Frontier sheathed Impact Guard draw'],
        'limitations':['Video freeze requires a human reproduction/log','Connected multiplayer unvalidated'],
        'installed':False,'published':False}
    proof_path=HERE/'reports/roll-draw-validation.json'
    proof_path.write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    dest=HERE/'public-release'/revision
    if dest.exists():raise RuntimeError('Candidate already exists; do not overwrite evidence')
    repo=dest/'source';ready=dest/'ready';private=dest/'diagnostic'
    shutil.copytree(HERE/'public-release/sprint-roll-fix-1/source',repo)
    ready.mkdir();private.mkdir()
    changed=[MS/'module/ms_act.c',MS/'module/ms_class.c',HERE/'build_module.py',HERE/'feedback_session.py',
        HERE/'test_guard_draw.py',HERE/'tests/draw_route_harness.c',HERE/'tests/guard_draw_harness.c',
        HERE/'test_freeze_trace.py',HERE/'tests/freeze_trace_harness.c',HERE/'exercise_draw_chord.py',
        HERE/'exercise_freeze_diagnostics.py',HERE/'probe_frontier_draw.py',HERE/'dis_audio.py',
        HERE/'package_roll_draw_candidate.py',HERE/'GUARD_DRAW_FIX.md',HERE/'FREEZE_DIAGNOSTICS.md',HERE/'CONTROLS.md']
    for p in changed:
        target=repo/'porting'/p.relative_to(HERE);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
    for name in ('GUARD_DRAW_FIX.md','FREEZE_DIAGNOSTICS.md'):shutil.copyfile(HERE/name,repo/name)
    shutil.copyfile(HERE/'release-docs/CONTROLS.md',repo/'CONTROLS.md')
    shutil.copyfile(HERE/'release-docs/CONTROLS.md',repo/'porting/release-docs/CONTROLS.md')
    shutil.copyfile(proof_path,repo/'release-validation.json')
    readme=('# Magnet Spike — local roll/draw test candidate\n\n'
        'For MHGU1.4.0 English on official Windows MHGURecomp0.18.0. This candidate includes alpha.2, '
        'the sheathed sprint-roll correction and Frontier\'s sheathed Impact Guard draw. '
        'The video freeze is **not confirmed fixed**. This is not a published release.\n\n'
        'Use `Magnet-Spike-Roll-Draw-Test.zip` for the normal candidate. To capture a freeze, use '
        '`Magnet-Spike-Freeze-Diagnostic.zip` instead and follow [FREEZE_DIAGNOSTICS.md](FREEZE_DIAGNOSTICS.md). '
        'Keep only one Magnet Spike code-mod copy enabled.\n\n'
        'Read [INSTALL.md](INSTALL.md) for installation and save backups, [CONTROLS.md](CONTROLS.md) for inputs, '
        'and [GUARD_DRAW_FIX.md](GUARD_DRAW_FIX.md) for the correction and validation limits. '
        'Sprinting with the weapon sheathed now permits B rolls. Sheathed R+X+A draws into Impact Guard; '
        'drawn R+X+A remains Magnetic Assault. No balance or RomFS assets changed.\n\n'
        'Magnet Spike is a separate smithy category with136 weapon families and959 levels. '
        'Existing weapon IDs and progression are retained. Multiplayer remains unvalidated. '
        'See [COMPATIBILITY.md](COMPATIBILITY.md) for the base alpha requirements and prior checks.\n\n'
        'The source archive contains build tools and source only. It does not include game data, saves, '
        'the runtime, or the supplied video. See [BUILDING.md](BUILDING.md), [LICENSE](LICENSE), '
        'and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).\n')
    (repo/'README.md').write_text(readme,encoding='utf-8')
    # Replace the old release-specific install title/download while retaining save/loader instructions.
    install=(repo/'INSTALL.md').read_text(encoding='utf-8').replace('# Install the sprinting-roll test candidate','# Install the roll/draw test candidate').replace('Magnet-Spike-Sprint-Roll-Fix.zip','Magnet-Spike-Roll-Draw-Test.zip')
    install=install.replace(' from GitHub Releases',' from the local candidate folder')
    (repo/'INSTALL.md').write_text(install,encoding='utf-8')
    for p in repo.rglob('*'):
        if p.is_file():p.write_bytes(p.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8'))
    spec=importlib.util.spec_from_file_location('candidate_source_check',HERE/'release-docs/check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker);count=checker.check(repo)
    docs=('README.md','INSTALL.md','CONTROLS.md','COMPATIBILITY.md','LICENSE','THIRD_PARTY_NOTICES.md',
          'SPRINT_ROLL_FIX.md','GUARD_DRAW_FIX.md','FREEZE_DIAGNOSTICS.md','release-validation.json')
    archives=[]
    for folder,target,name in ((payload,ready,'Magnet-Spike-Roll-Draw-Test.zip'),
                               (diagnostic,private,'Magnet-Spike-Freeze-Diagnostic.zip')):
        entries=[('Magnet-Spike/'+p.relative_to(folder).as_posix(),p) for p in folder.rglob('*') if p.is_file()]
        entries += [('Magnet-Spike/'+name,repo/name) for name in docs]
        path=target/name;make_zip(path,entries);archives.append(path)
        with zipfile.ZipFile(path) as z:
            assert z.testzip() is None
            packed={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
        assert packed==(normal_files if folder==payload else diag_files)
    source_zip=ready/'Magnet-Spike-Roll-Draw-source.zip'
    make_zip(source_zip,[('Magnet-Spike-Roll-Draw-source/'+p.relative_to(repo).as_posix(),p) for p in repo.rglob('*') if p.is_file()]);archives.append(source_zip)
    with zipfile.ZipFile(source_zip) as z:assert z.testzip() is None
    shutil.copyfile(proof_path,ready/'release-validation.json')
    downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in archives}
    manifest={'revision':revision,'status':'local test candidate; video freeze unconfirmed','files':downloads,
        'source_files':count,'source_git_tree':git_tree(repo).hex(),'installed':False,'published':False}
    (ready/'candidate-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (ready/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in sorted(ready.iterdir()) if p.is_file()),encoding='utf-8')
    shutil.copyfile(repo/'FREEZE_DIAGNOSTICS.md',private/'READ-ME.md')
    (private/'SHA256SUMS.txt').write_text(sha(archives[1])+'  '+archives[1].name+'\n',encoding='utf-8')
    short=HERE.parent/'TEST BUILD - ROLL AND DRAW'
    if short.exists():raise RuntimeError('Short handoff folder exists; do not overwrite')
    shutil.copytree(ready,short/'normal');shutil.copytree(private,short/'diagnostic')
    shutil.copyfile(repo/'GUARD_DRAW_FIX.md',short/'READ-ME.md')
    receipt={'all_passed':True,'validation_sha256':sha(proof_path),'downloads':downloads,
             'source_files':count,'source_git_tree':manifest['source_git_tree'],'handoff':str(short),
             'installed':False,'published':False}
    (HERE/'reports/roll-draw-packaging.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt))


if __name__=='__main__':main()
