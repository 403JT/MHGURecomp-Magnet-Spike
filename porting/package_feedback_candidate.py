"""Package a local public-Recomp test candidate; never install or publish it."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import zipfile
from prepare_frontier import HERE,sha
from feedback_session import files
from package_public_release import make_zip

NEW=[
    'feedback_session.py','exercise_parry_feedback.py','exercise_parry_contact.py',
    'exercise_guard_inputs.py','exercise_slash_feedback.py','exercise_slash_combat.py',
    'exercise_remote_recovery_feedback.py','exercise_double_slash_feedback.py',
    'trace_feedback_input.py','native_references.py','test_feedback_recovery.py',
    'test_feedback_state_pool.py','test_feedback_repeat_hits.py',
    'test_feedback_quick_message.py','validate_feedback.py','package_feedback_candidate.py',
    'module/feedback.c','tests/feedback_harness.c','tests/quick_message_harness.c','FEEDBACK_FIXES.md']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--revision',type=int,choices=(1,2),default=1)
    args=parser.parse_args()
    name=f'Magnet-Spike-Public-Feedback-Candidate-{args.revision}'
    proof=HERE/('reports/feedback-validation.json' if args.revision==1 else 'reports/feedback-2-validation.json')
    validation=json.loads(proof.read_text(encoding='utf-8'))
    payload=HERE/'output/magnet-spike-experimental'
    assert validation['all_passed'] and validation['target']=='recomp'
    assert files(payload)==validation['payload_files']
    dest=HERE/f'public-release/feedback-candidate-{args.revision}'
    if dest.exists():raise RuntimeError('Candidate already exists; never overwrite a tested package')
    baseline=HERE/'public-release/v0.1.0-alpha.1/public/repo'
    repo=dest/'source';shutil.copytree(baseline,repo)
    # Overlay current source files already present in the public snapshot.
    # All newly introduced files are named explicitly below.
    for p in (repo/'porting').rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(repo/'porting');current=HERE/rel
        if current.is_file() and sha(current)!=sha(p):shutil.copyfile(current,p)
    additions=NEW+(['exercise_interruption_feedback.py','exercise_marker_remote_feedback.py',
        'test_damage_feedback.py','test_marker_feedback.py','validate_feedback_2.py',
        'tests/damage_feedback_harness.c','tests/marker_feedback_harness.c'] if args.revision==2 else [])
    for item in additions:
        target=repo/'porting'/item;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(HERE/item,target)
    shutil.copyfile(HERE/'FEEDBACK_FIXES.md',repo/'FEEDBACK_FIXES.md')
    prefix=(f'# Public MHGURecomp feedback candidate {args.revision}\n\n'
        'Local test candidate; connected multiplayer is not yet validated. '
        'The published v0.1.0-alpha.1 release is unchanged. '
        'Read [FEEDBACK_FIXES.md](FEEDBACK_FIXES.md) for changes and remaining reports.\n\n')
    (repo/'README.md').write_text(prefix+(baseline/'README.md').read_text(encoding='utf-8'),encoding='utf-8')
    checker_path=HERE/'release-docs/check_source_tree.py'
    spec=importlib.util.spec_from_file_location('feedback_source_check',checker_path)
    checker=importlib.util.module_from_spec(spec);spec.loader.exec_module(checker)
    count=checker.check(repo)
    ready=dest/'ready';ready.mkdir()
    entries=[('Magnet-Spike/'+p.relative_to(payload).as_posix(),p) for p in payload.rglob('*') if p.is_file()]
    for item in ('README.md','INSTALL.md','COMPATIBILITY.md','CONTROLS.md','LICENSE','THIRD_PARTY_NOTICES.md','FEEDBACK_FIXES.md'):
        entries.append(('Magnet-Spike/'+item,repo/item))
    entries.append(('Magnet-Spike/feedback-validation.json',proof))
    mod_zip=ready/(name+'.zip');source_zip=ready/(name+'-source.zip')
    make_zip(mod_zip,entries)
    make_zip(source_zip,[(name+'-source/'+p.relative_to(repo).as_posix(),p) for p in repo.rglob('*') if p.is_file()])
    with zipfile.ZipFile(mod_zip) as z:
        actual={n.removeprefix('Magnet-Spike/'):hashlib.sha256(z.read(n)).hexdigest()
                for n in z.namelist() if n.startswith(('Magnet-Spike/exefs/','Magnet-Spike/romfs/'))}
    assert actual==validation['payload_files']
    downloads={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in (mod_zip,source_zip)}
    (ready/'SHA256SUMS.txt').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in downloads.items()),encoding='utf-8')
    receipt={'candidate':name,'target':'recomp','published':False,'installed':False,
        'release_ready':False,'connected_multiplayer_tested':False,'source_files':count,
        'payload_files':actual,'validation_sha256':sha(proof),'downloads':downloads}
    receipt_path='reports/feedback-packaging.json' if args.revision==1 else 'reports/feedback-2-packaging.json'
    (HERE/receipt_path).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'source_files':count,'payload_files':len(actual),'downloads':downloads}))


if __name__=='__main__':main()
