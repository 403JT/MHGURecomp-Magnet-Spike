"""Install matching tested code/assets together, with rollback. Never writes saves."""
import argparse
import hashlib
import json
import msvcrt
import os
import shutil

from prepare_frontier import HERE, ROOT


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def within_workspace(path):
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT.resolve()):
        raise ValueError('Install path leaves MHGU P2')
    return resolved


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stress-run', default='stable-hooks-shots')
    parser.add_argument('--audio-run', required=True)
    parser.add_argument('--combat-run', required=True)
    parser.add_argument('--revision', default='sounds-2')
    parser.add_argument('--pin-cutting-run')
    parser.add_argument('--pin-impact-run')
    parser.add_argument('--pin-timeout-run')
    parser.add_argument('--input-run')
    parser.add_argument('--action-sweep-runs',nargs=2)
    parser.add_argument('--guard-run')
    parser.add_argument('--cross-step-run')
    parser.add_argument('--magnetise-run')
    parser.add_argument('--movement-run')
    parser.add_argument('--world-run')
    parser.add_argument('--charge-run')
    parser.add_argument('--cancel-run')
    parser.add_argument('--smithy-run')
    parser.add_argument('--equipment-proof')
    args = parser.parse_args()
    source = within_workspace(HERE / 'output/magnet-spike-experimental')
    profile = within_workspace(HERE / 'test-profile')
    installed = within_workspace(profile / 'mods/magnet-spike-experimental')
    report_path = within_workspace(HERE / 'runs' / args.stress_run / 'run.json')
    report = json.loads(report_path.read_text(encoding='utf-8'))
    digest = sha(source / 'exefs/subsdk1')
    def tree(path):
        return {str(p.relative_to(path)): sha(p) for p in path.rglob('*') if p.is_file()}
    expected = tree(source)
    reused={}
    def matching_files(data,folder):
        from evidence_matching import command_equivalence
        result=command_equivalence(data,folder,source,expected)
        if result and not result['exact_files']:reused[str(folder/'run.json')]=result
        return result is not None
    if report['module_sha256'] != digest or report['exit_code'] or report['fatal'] or report['failure'] or report['marker_shots'] < 20:
        raise RuntimeError('The candidate does not match the passing gameplay stress test')
    if not matching_files(report,report_path.parent) or not report.get('source_saves_unchanged'):
        raise RuntimeError('The code/assets do not match the tested mod, or saves changed')
    audio_path = within_workspace(HERE / 'runs' / args.audio_run)
    audio_run = json.loads((audio_path / 'run.json').read_text(encoding='utf-8'))
    audio = json.loads((audio_path / 'audio-verification.json').read_text(encoding='utf-8'))
    if audio.get('mod_files')!=audio_run.get('mod_files') or audio.get('module_sha256')!=audio_run.get('module_sha256'):
        raise RuntimeError('Playback verification does not identify the captured mod')
    if (not matching_files(audio_run,audio_path) or audio_run.get('exit_code') or audio_run.get('failure')
            or audio_run.get('fatal') or not audio_run.get('source_saves_unchanged')
            or audio_run.get('sound_files_loaded', 0) < 2 or audio.get('strong_matches', 0) < 6
            or not all(any(r['slot'] == slot and abs(r['correlation']) >= .55 for r in audio['detected']) for slot in (2,4))):
        raise RuntimeError('The candidate lacks matching, successful playback evidence for both sound banks')
    combat_path=within_workspace(HERE/'runs'/args.combat_run)
    combat=json.loads((combat_path/'run.json').read_text(encoding='utf-8'))
    combat_audio=json.loads((combat_path/'audio-verification.json').read_text(encoding='utf-8'))
    hitstats=json.loads((combat_path/'hitstats-verification.json').read_text(encoding='utf-8'))
    if not hitstats.get('all_passed') or hitstats.get('module_sha256')!=digest:
        raise RuntimeError('The candidate lacks matching source-KO collision evidence')
    import re
    combat_log=(combat_path/'log.txt').read_text(encoding='utf-8',errors='replace')
    modes=set(re.findall(r'ms-sound: collision kind [012] tier [234] mode ([01])',combat_log))
    if (not matching_files(combat,combat_path) or combat.get('exit_code') or combat.get('failure') or combat.get('fatal')
            or not combat.get('source_saves_unchanged') or combat.get('collision_sounds',0)<4 or modes!={'0','1'}
            or not all(any(r['request'] in reqs and r['slot']==4 and abs(r['correlation'])>=.25
                           for r in combat_audio['detected']) for reqs in ((541,542,543),(544,545,546)))):
        raise RuntimeError('The candidate lacks matching Cutting/Impact collision playback evidence')
    if combat_audio.get('clipped_fraction',1)!=0:
        raise RuntimeError('The combat audio capture still contains clipped peaks')
    moveset_evidence={}
    if json.loads((HERE/'output/module-status.json').read_text())['hooks']>=25:
        def gameplay(label,mode):
            if not label:raise RuntimeError('The restraint candidate requires its moveset gameplay evidence')
            folder=within_workspace(HERE/'runs'/label)
            data=json.loads((folder/'run.json').read_text(encoding='utf-8'))
            if (not matching_files(data,folder) or data.get('failure') or data.get('exit_code') or data.get('fatal')
                or data.get('test_mode')!=mode or not data.get('source_saves_unchanged')
                or data.get('invalid_effect_handles') or data.get('premature_effect_reposts',data.get('effect_reposts',1))):
                raise RuntimeError('Moveset gameplay evidence is failing, incomplete, or belongs to another candidate')
            moveset_evidence[mode]=str(folder/'run.json')
            return data,(folder/'log.txt').read_text(encoding='utf-8',errors='replace')
        for label,mode,finisher in ((args.pin_cutting_run,'cutting',105),(args.pin_impact_run,'impact',157),
                                     (args.pin_timeout_run,'timeout',None)):
            data,log=gameplay(label,'pin-'+mode)
            if (not data.get('live_monster') or data.get('pin_restraints',0)<1
                or data.get('pin_releases')!=data['pin_restraints'] or not data.get('pin_target_position_held')
                or not data.get('pin_animation_paused') or not 0<data.get('pin_hunter_hp',5000)<=500):
                raise RuntimeError('Pin ownership lacks matching free-hunter, active-monster evidence')
            if (finisher and (data.get('pin_successes',0)<1 or 'msport: state action 16/'+str(finisher)+' ' not in log)):
                raise RuntimeError('The expected pin finisher was not exercised')
            if not finisher and data.get('pin_timeouts',0)<1:raise RuntimeError('Pin timeout was not exercised')
        data,_=gameplay(args.input_run,'normal-pin-combos')
        if not data.get('normal_pin_combos') or not all(data['normal_pin_combos'].values()):
            raise RuntimeError('Normal-control pin combos were not exercised')
        if not args.action_sweep_runs:raise RuntimeError('Both converted-action smoke tests are required')
        action_ids=set()
        for i,label in enumerate(args.action_sweep_runs):
            data,_=gameplay(label,'action-sweep-'+str(i))
            ids=set(data.get('action_sweep_requested',[]))
            if len(ids)!=80 or ids&action_ids or data.get('action_sweep_missing'):
                raise RuntimeError('Converted-action smoke test coverage is incomplete')
            action_ids|=ids
        if len(action_ids)!=160:raise RuntimeError('Converted-action smoke tests did not cover all 160 entries')
        if args.guard_run:
            data,log=gameplay(args.guard_run,'incoming-guard')
            if data.get('guarded_hits',0)<1:raise RuntimeError('No incoming guarded hit was recorded')
            if not re.search(r'msport: hit .*in action (?:57|76|77)\b',log):
                raise RuntimeError('No guard counter damage callback was recorded')
        data,_=gameplay(args.cross_step_run,'cross-step-input')
        if not data.get('cross_step_followup'):raise RuntimeError('Early cross-step Impact input was not exercised')
        for key,label in (('magnetise',args.magnetise_run),('movement',args.movement_run)):
            gameplay(label,'manual')
            path=within_workspace(HERE/'runs'/label/'mechanics-verification.json')
            data=json.loads(path.read_text(encoding='utf-8'))
            if not data.get('all_passed') or data.get('module_sha256')!=digest:
                raise RuntimeError('Required '+key+' mechanics have not passed for this candidate')
            if key=='magnetise':
                sound=json.loads((path.parent/'audio-verification.json').read_text(encoding='utf-8'))
                if (sound.get('mod_files')!=data.get('mod_files') or sound.get('clipped_fraction',1)!=0
                        or sound.get('peak_stereo',1)>=.999):
                    raise RuntimeError('Extended Magnetise playback lacks matching unclipped audio evidence')
            moveset_evidence[key]=str(path)
    for name in ('runtime-regression.json', 'hook-regression.json','moveset-regression.json'):
        data = json.loads((HERE / 'reports' / name).read_text(encoding='utf-8'))
        if not all(data['fixed'].values()):
            raise RuntimeError('ARM regression checks have not passed')
    for name in ('sound-regression.json','audio-codec-regression.json','pin-regression.json',
                 'command-window-regression.json','hitstats-regression.json','native-hitstats-regression.json','aim-regression.json'):
        if not json.loads((HERE/'reports'/name).read_text(encoding='utf-8'))['all_passed']:
            raise RuntimeError('Sound regression checks have not passed')
    if json.loads((HERE/'output/module-status.json').read_text())['hooks']>=26:
        for name in ('worldhit-regression.json','worldhook-regression.json','hit-layout-regression.json'):
            if not json.loads((HERE/'reports'/name).read_text(encoding='utf-8'))['all_passed']:
                raise RuntimeError('World geometry/native hit-layout checks have not passed')
        for kind,label,filename in (('world',args.world_run,'worldhit-verification.json'),
                                    ('charge',args.charge_run,'charge-verification.json')):
            if not label:raise RuntimeError('The parity candidate requires '+kind+' gameplay evidence')
            data,_=gameplay(label,'manual')
            folder=within_workspace(HERE/'runs'/label)
            proof=json.loads((folder/filename).read_text(encoding='utf-8'))
            if (not proof.get('all_passed') or not matching_files(proof,folder)
                    or not data.get('output_muted')):
                raise RuntimeError('The parity candidate lacks matching muted '+kind+' verification')
            moveset_evidence[kind]=str(folder/filename)
    if json.loads((HERE/'output/module-status.json').read_text(encoding='utf-8'))['hooks']>=27:
        for name in ('cancel-window-regression.json','cancel-hook-regression.json','command-route-regression.json'):
            if not json.loads((HERE/'reports'/name).read_text(encoding='utf-8'))['all_passed']:
                raise RuntimeError('Temporal/input-route regression checks have not passed')
        archive_audit=json.loads((HERE/'reports/cancel-archive-diff.json').read_text(encoding='utf-8'))
        if not archive_audit['all_passed'] or archive_audit.get('mod_files')!=expected:
            raise RuntimeError('Command archive difference audit has not passed')
        if not args.cancel_run:raise RuntimeError('Temporal candidate requires matching live cancel evidence')
        data,_=gameplay(args.cancel_run,'manual')
        folder=within_workspace(HERE/'runs'/args.cancel_run)
        proof=json.loads((folder/'cancel-verification.json').read_text(encoding='utf-8'))
        if (not proof.get('all_passed') or proof.get('baseline') or not matching_files(proof,folder)
                or not data.get('output_muted')):
            raise RuntimeError('Temporal candidate lacks matching muted live cancel verification')
        moveset_evidence['cancel']=str(folder/'cancel-verification.json')
    if json.loads((HERE/'output/module-status.json').read_text(encoding='utf-8')).get('smithy_tree'):
        if not args.smithy_run:
            raise RuntimeError('The new weapon tree requires matching forge/upgrade/save-reload evidence')
        folder=within_workspace(HERE/'runs'/args.smithy_run)
        proof=json.loads((folder/'smithy-verification.json').read_text(encoding='utf-8'))
        if not proof.get('all_passed') or proof.get('mod_files')!=expected:
            raise RuntimeError('Smithy verification failed or belongs to different code/assets')
        for name in ('smithy-tree-regression.json','smithy-model-regression.json'):
            if not json.loads((HERE/'reports'/name).read_text(encoding='utf-8')).get('all_passed'):
                raise RuntimeError('Smithy ARM/model validation has not passed')
        model_proof=json.loads((HERE/'reports/smithy-model-regression.json').read_text(encoding='utf-8'))
        for model in model_proof['models']:
            if sha(source/f"romfs/nativeNX/arc/weapon/w05/{model['id']:03d}.arc")!=model['sha256']:
                raise RuntimeError('A staged model differs from its validated conversion')
        preservation=json.loads((HERE/'reports/smithy-asset-audit.json').read_text(encoding='utf-8'))
        if not preservation.get('all_passed') or preservation.get('mod_files')!=expected:
            raise RuntimeError('Smithy gameplay-asset preservation audit is missing or stale')
        if not args.equipment_proof:raise RuntimeError('The new tree needs native upgraded/elemental equipment evidence')
        equipment_path=within_workspace(HERE/'reports'/args.equipment_proof)
        equipment=json.loads(equipment_path.read_text(encoding='utf-8'))
        if not equipment.get('all_passed') or equipment.get('mod_files')!=expected:
            raise RuntimeError('Native equipment evidence failed or belongs to another candidate')
        moveset_evidence['smithy']=str(folder/'smithy-verification.json')
        moveset_evidence['equipment']=str(equipment_path)
    short = hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest()[:12]
    backup = within_workspace(HERE / 'backups' / ('mod-before-' + short))
    staged = within_workspace(installed.parent / ('mod-pending-' + short))
    if staged.exists() or backup.exists():
        raise RuntimeError('Candidate install or backup already exists; nothing overwritten')
    save_before = {p.name: sha(p) for p in (profile / 'save/save_0').glob('system*')}
    save_backup=within_workspace(HERE/'backups'/('save-before-'+short))
    # The normal launcher takes this same file exclusively. Holding an open
    # handle also prevents it from starting while the module pair is replaced.
    with (profile / 'session.lock').open('a+b') as lock:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        try:
            # New type-12 IDs require the new tree. Keep the matching preinstall
            # save beside the rollback module without writing the live save.
            save_backup.mkdir(exist_ok=True)
            for name,digest_before in save_before.items():
                destination=save_backup/name
                if destination.exists() and sha(destination)!=digest_before:
                    raise RuntimeError('Existing rollback save differs; nothing overwritten')
                if not destination.exists():shutil.copyfile(profile/'save/save_0'/name,destination)
                if sha(destination)!=digest_before:raise RuntimeError('Rollback save copy mismatch')
            shutil.copytree(source, staged)
            if expected != tree(staged):
                raise RuntimeError('Staged module hash mismatch')
            # All absolute directory targets were resolved and checked above.
            os.replace(installed, backup)
            try:
                os.replace(staged, installed)
            except BaseException:
                os.replace(backup, installed)
                raise
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    if save_before != {p.name: sha(p) for p in (profile / 'save/save_0').glob('system*')}:
        raise RuntimeError('Save changed while installing')
    prior = HERE / 'installed-build.json'
    if prior.exists():
        shutil.copyfile(prior,HERE/'backups'/('installed-build-before-'+short+'.json'))
    result = {'revision': args.revision, 'module_sha256': digest, 'files': expected,
              'backup': str(backup), 'stress_test': str(report_path), 'saves_unchanged': True,
              'save_backup':str(save_backup),'preinstall_save_hashes':save_before,
              'audio_test': str(audio_path/'audio-verification.json'),
              'combat_test': str(combat_path/'audio-verification.json'),
              'moveset_tests':moveset_evidence,
              'equivalent_command_evidence':reused,
              'full_port_complete': False}
    (HERE / 'installed-build.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}, indent=2))


if __name__ == '__main__':
    main()
