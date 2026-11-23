"""Package the exact tested normal roll/draw payload for manual GitHub upload."""
import hashlib
import importlib.util
import json
import re
import shutil
import zipfile
from build_module import HERE,MS,sha
from feedback_session import files
from package_public_release import NAME,make_zip,put
from prepare_public_launch import git_tree

VERSION='v0.1.0-alpha.3'

NOTES='''# Magnet Spike v0.1.0-alpha.3 — sprint roll and guard draw fixes

Alpha.2 with two gameplay corrections, for **MHGU 1.4.0 English** on official
**Windows MHGURecomp 0.18.0**, using its built-in mod loader.

## Changes from alpha.2

- **Sprinting roll:** with the weapon sheathed, hold R + movement and press B
  to roll. The weapon input translator now preserves the native sprint evade.
- **Sheathed R+X+A:** hold R and press X+A to draw into the existing Impact
  Guard, matching Frontier's draw handler. This replaces an inherited Great
  Sword guard path. Drawn R+X+A remains Magnetic Assault.

All alpha.2 content and earlier fixes are included. Weapon stats, damage,
combo links, recovery durations, gauge costs, guard windows, recipes, models
and sounds are unchanged. The executable patch file and all54 RomFS assets
are byte-identical to alpha.2. Extra freeze logging is not enabled or bundled.
The controls guide also corrects an unverified plain sheathed X+A binding.

## Install or update

1. Close MHGURecomp and back up your save folder.
2. Download **Magnet-Spike-v0.1.0-alpha.3.zip**.
3. Move the previous Magnet-Spike folder outside `mods`, then put the new
   **Magnet-Spike** folder in `mods`. Keep only one copy enabled and restart.

Existing weapons require no recrafting or save editing. No custom runtime,
launcher or supplied save is required. See INSTALL.md inside the ZIP.

## Validation and known issues

The exact normal payload passed four ordinary walking/sprinting roll cases
and two ordinary standing/moving sheathed guard-draw cases on official0.18.0.
Compiled regressions cover the draw routes, both control options, recovery,
cancelled damage and per-hunter state ownership. Games were muted and used
disposable save copies; original saves were unchanged.

**The intermittent freeze shown in the reported video remains unconfirmed
and is not claimed fixed by this release.** Connected multiplayer and broad
full-hunt coverage remain unvalidated. This is still an experimental alpha.
Full Frontier parity, other runtimes/platforms/languages and mod combinations
are not guaranteed. See release-validation.json for the tested scope.

## Downloads

Use **Magnet-Spike-v0.1.0-alpha.3.zip** to play. The separately attached
**Magnet-Spike-v0.1.0-alpha.3-source.zip** contains the matching source.
The other three attachments are release-manifest.json, release-validation.json
and SHA256SUMS.txt. The diagnostic build is not part of this release.

Code is GPL-3.0-or-later; see LICENSE and THIRD_PARTY_NOTICES.md. Original game
content belongs to Capcom and is not covered by the code license.
'''

README='''# Magnet Spike v0.1.0-alpha.3

A separate Magnet Spike weapon category for MHGU1.4.0 English, using the normal
mod loader in official Windows MHGURecomp0.18.0. The smithy has136 weapon
families and959 upgrade levels, with the earlier models, sounds and balance.

This update adds the sprinting-roll and sheathed R+X+A corrections to alpha.2.
Sheathed R+X+A draws into Impact Guard; drawn R+X+A remains Magnetic Assault.
There are no additional gameplay changes or extra diagnostic logging in the
playable download. The intermittent video freeze is not confirmed fixed.

Use **Magnet-Spike-v0.1.0-alpha.3.zip** to play and keep only one Magnet Spike
mod copy enabled. Read [INSTALL.md](INSTALL.md) before updating, including the
save backup instructions. Existing weapons need no recrafting or save editing.

See [CONTROLS.md](CONTROLS.md), [RELEASE_NOTES.md](RELEASE_NOTES.md) and
[COMPATIBILITY.md](COMPATIBILITY.md) for controls, changes and testing limits.
This remains an experimental alpha; multiplayer is unvalidated.

The attached source ZIP matches this build and contains no game data, saves
or runtime. Developer diagnostic tools remain optional and are disabled in
the default build. See [BUILDING.md](BUILDING.md), [LICENSE](LICENSE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
'''


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    candidate=HERE/'public-release/roll-draw-candidate-1'
    proof_path=HERE/'reports/roll-draw-validation.json'
    scope_path=HERE/'reports/roll-draw-release-scope.json'
    proof,scope=read(proof_path),read(scope_path)
    candidate_receipt=read(HERE/'reports/roll-draw-packaging.json')
    payload=HERE/'output/magnet-spike-experimental';expected=files(payload)
    assert proof['all_passed'] and all(proof['checks'].values())
    assert scope['all_passed'] and all(scope['checks'].values())
    assert expected==scope['payload_files']==proof['payload_files'] and len(expected)==56
    assert sha(proof_path)==candidate_receipt['validation_sha256']
    for item in proof['evidence'].values():assert sha(HERE/item['path'])==item['sha256']
    candidate_zip=candidate/'ready/Magnet-Spike-Roll-Draw-Test.zip'
    assert sha(candidate_zip)==candidate_receipt['downloads'][candidate_zip.name]['sha256']
    dest=HERE/'public-release'/VERSION;short=HERE.parent/'RELEASE UPLOAD - ALPHA 3'
    if dest.exists() or short.exists():raise RuntimeError('Release staging exists; do not overwrite')
    repo,ready=dest/'repo',dest/'ready'
    shutil.copytree(candidate/'source',repo);ready.mkdir()
    for p in (HERE/'package_roll_draw_release.py',HERE/'verify_roll_draw_scope.py'):
        put(p,repo/'porting'/p.name)
    for name,text in (('README.md',README),('RELEASE_NOTES.md',NOTES)):
        (repo/name).write_text(text,encoding='utf-8')
        (repo/'porting/release-docs'/name).write_text(text,encoding='utf-8')
    install=(HERE/'public-release/v0.1.0-alpha.2/repo/INSTALL.md').read_text(encoding='utf-8')
    install=install.replace('v0.1.0-alpha.2',VERSION).replace('Alpha.2 includes','Alpha.3 includes')
    install += ('\nAlpha.3 adds the sprinting-roll and sheathed Impact Guard draw corrections. '
                'The separate intermittent video freeze is not confirmed fixed.\n')
    (repo/'INSTALL.md').write_text(install,encoding='utf-8')
    (repo/'porting/release-docs/INSTALL.md').write_text(install,encoding='utf-8')
    compatibility=(repo/'COMPATIBILITY.md').read_text(encoding='utf-8')
    compatibility += ('\n**Alpha.3 validation:** the exact normal build passed four ordinary roll '
        'cases and two sheathed R+X+A guard-draw cases on official Windows0.18.0. '
        'The sprint-roll, routing, recovery, damage-cancellation and state-ownership '
        'regressions passed. Additional freeze logging is disabled. The reported '
        'video freeze remains unconfirmed; it is not included among the fixes.\n')
    (repo/'COMPATIBILITY.md').write_text(compatibility,encoding='utf-8')
    (repo/'porting/release-docs/COMPATIBILITY.md').write_text(compatibility,encoding='utf-8')
    guard=(repo/'GUARD_DRAW_FIX.md').read_text(encoding='utf-8')
    start=guard.index('With the weapon sheathed')
    guard='# Sheathed guard-draw correction — '+VERSION+'\n\n'+guard[start:]
    (repo/'GUARD_DRAW_FIX.md').write_text(guard,encoding='utf-8')
    (repo/'porting/GUARD_DRAW_FIX.md').write_text(guard,encoding='utf-8')
    sprint=(repo/'SPRINT_ROLL_FIX.md').read_text(encoding='utf-8')
    sprint=sprint.replace('This local test package includes the cumulative alpha.2 fixes plus the fix for',
        'This release includes the cumulative alpha.2 fixes and the correction for')
    sprint=sprint.replace('This is a local test candidate, not an updated GitHub release. Alpha.2\'s',
        'This correction is included in v0.1.0-alpha.3. Alpha.2\'s')
    (repo/'SPRINT_ROLL_FIX.md').write_text(sprint,encoding='utf-8')
    (repo/'porting/SPRINT_ROLL_FIX.md').write_text(sprint,encoding='utf-8')
    # Freeze diagnostics remain a developer source tool, not a playable attachment.
    native=[]
    for label in ('draw-chord-fixed-2','sprint-roll-draw-fixed-1'):
        r=read(HERE/'runs'/label/'feedback-native.json')
        assert r['payload_files']==expected and r['source_saves_unchanged'] and r['muted']
        assert r['exit_code']==0 and not r['failure'] and not r['fatal']
        native.append({'scenario':label,'runtime':r['runtime'],'runtime_sha256':r['runtime_sha256'],
            'cases':len(r['cases']),'passed':True,'muted':True,'source_saves_unchanged':True})
    checks={n:v for n,v in proof['checks'].items() if not n.startswith(('freeze-','diagnostic_')) and n!='logging_opt_in_only'}
    checks.update({'scope_'+n:v for n,v in scope['checks'].items()})
    validation={'mod_version':VERSION,'base_version':'v0.1.0-alpha.2','build_revision':'roll-draw-1',
        'target':'recomp','game':'MHGU1.4.0 English','runtime':'official Windows MHGURecomp0.18.0',
        'all_focused_checks_passed':True,'validation_checks':checks,'validation_gate_count':len(checks),
        'module_sha256':expected['exefs/subsdk1'],'ips_sha256':next(v for n,v in expected.items() if n.endswith('.ips')),
        'payload_identical_to_tested_normal_candidate':True,'extra_freeze_logging_enabled':False,
        'gameplay_changes':['Preserve sheathed sprint evades','Restore Frontier sheathed Impact Guard draw'],
        'native_tests':native,'source_scope_sha256':sha(scope_path),'candidate_validation_sha256':sha(proof_path),
        'evidence_sha256':{n:v['sha256'] for n,v in proof['evidence'].items() if n not in ('freeze-trace-regression','freeze-diagnostic-smoke-2')},
        'video_freeze_reproduced':False,'video_freeze_confirmed_fixed':False,
        'connected_multiplayer_tested':False,'full_play_validation_complete':False,
        'unchanged':['IPS patch file','all54 RomFS assets','weapon stats and damage','combo links and recovery durations',
            'guard windows and gauge costs','smithy recipes and weapon IDs','models and sounds'],
        'limits':['Video freeze remains unconfirmed','Connected multiplayer and broad full-hunt coverage remain unvalidated']}
    (repo/'release-validation.json').write_text(json.dumps(validation,indent=2)+'\n',encoding='utf-8')
    # Bind the shipped source to the tested production source, with LF text.
    for source in list((MS/'module').glob('*'))+list((HERE/'module').glob('*')):
        if source.is_file():assert source.read_text(encoding='utf-8')==(repo/'porting'/source.relative_to(HERE)).read_text(encoding='utf-8')
    for p in repo.rglob('*'):
        if p.is_file():p.write_bytes(p.read_text(encoding='utf-8').replace('\r\n','\n').encode('utf-8'))
    spec=importlib.util.spec_from_file_location('release_source_check',HERE/'release-docs/check_source_tree.py')
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker);count=checker.check(repo)
    for p in repo.glob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)',p.read_text(encoding='utf-8')):
            if '://' not in link and not link.startswith('#'):
                target=link.split('#')[0];assert not target or (p.parent/target).exists(),(p.name,target)
    tree=git_tree(repo).hex()
    mod_zip=ready/f'Magnet-Spike-{VERSION}.zip';source_zip=ready/f'Magnet-Spike-{VERSION}-source.zip'
    docs=('README.md','INSTALL.md','CONTROLS.md','COMPATIBILITY.md','RELEASE_NOTES.md','LICENSE',
          'THIRD_PARTY_NOTICES.md','FEEDBACK_FIXES.md','SPRINT_ROLL_FIX.md','GUARD_DRAW_FIX.md','release-validation.json')
    make_zip(mod_zip,[('Magnet-Spike/'+p.relative_to(payload).as_posix(),p) for p in payload.rglob('*') if p.is_file()]
        +[('Magnet-Spike/'+name,repo/name) for name in docs])
    make_zip(source_zip,[(NAME+'-'+VERSION+'/'+p.relative_to(repo).as_posix(),p) for p in repo.rglob('*') if p.is_file()])
    downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)}
    manifest={'version':VERSION,'base_version':'v0.1.0-alpha.2','build_revision':'roll-draw-1',
        'repository':'https://github.com/403JT/'+NAME,'game_version':'MHGU1.4.0','language':'English',
        'runtime':'MHGURecomp0.18.0 Windows x64','target':'recomp','payload_files':expected,
        'source_file_count':count,'source_git_tree':tree,
        'source_files':{p.relative_to(repo).as_posix():sha(p) for p in repo.rglob('*') if p.is_file()},
        'downloads':downloads,'extra_freeze_logging_enabled':False,'contains_diagnostic_build':False,
        'focused_validation_passed':True,'video_freeze_confirmed_fixed':False,
        'contains_game_executable':False,'contains_saves_or_test_captures':False}
    (ready/'release-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    put(repo/'release-validation.json',ready/'release-validation.json')
    (ready/'SHA256SUMS.txt').write_text(''.join(sha(p)+'  '+p.name+'\n' for p in
        (mod_zip,source_zip,ready/'release-manifest.json',ready/'release-validation.json')),encoding='utf-8')
    with zipfile.ZipFile(mod_zip) as z:
        assert z.testzip() is None
        packed={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist()
            if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
        assert packed==expected
        assert not any('Diagnostic' in n or 'FREEZE_DIAGNOSTICS' in n for n in z.namelist())
    with zipfile.ZipFile(source_zip) as z:assert z.testzip() is None
    assert len(list(ready.iterdir()))==5
    shutil.copytree(ready,short)
    note_path=HERE.parent/'RELEASE NOTES - ALPHA 3.md';note_path.write_text(NOTES,encoding='utf-8')
    for p in ready.iterdir():assert sha(p)==sha(short/p.name)
    report={'version':VERSION,'all_passed':True,'exact_tested_normal_payload':True,'source_file_count':count,
        'source_git_tree':tree,'downloads':downloads,'payload_files':expected,'upload_folder':str(short),
        'notes':str(note_path),'uploaded':False,'published':False,'installed':False}
    (HERE/'reports/roll-draw-release-preparation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({n:report[n] for n in ('version','all_passed','source_file_count','source_git_tree','downloads','upload_folder')}))


if __name__=='__main__':main()
