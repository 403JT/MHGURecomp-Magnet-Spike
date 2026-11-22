"""Install the specifically validated recovery change with paired rollback saves."""
import json,msvcrt,os,shutil
from prepare_frontier import HERE,ROOT,sha
from hunt_session import files


def local(p):
    p=p.resolve()
    if not p.is_relative_to(ROOT.resolve()):raise ValueError('Path leaves MHGU P2')
    return p


def main():
    receipt_path=HERE/'reports/combo-recovery-validation.json'
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    if not receipt.get('all_passed') or not receipt.get('checks') or not all(receipt['checks'].values()):
        raise RuntimeError('Recovery validation has not passed')
    required={'recovery','windows','hook','moveset','damage','preservation','native','reference'}
    if set(receipt['evidence'])!=required:raise RuntimeError('Required evidence missing')
    for item in receipt['evidence'].values():
        if sha(local(HERE/item['path']))!=item['sha256']:raise RuntimeError('Validation evidence changed')
    source=local(HERE/'output/magnet-spike-experimental');expected=files(source)
    prior_path=HERE/'installed-build.json';prior=json.loads(prior_path.read_text(encoding='utf-8'))
    if expected!=receipt['mod_files'] or prior['files']!=receipt['previous_mod_files']:
        raise RuntimeError('Candidate or installed baseline differs from validated files')
    if sha(HERE/'balance-policy.json')!=receipt['balance_policy_sha256']:
        raise RuntimeError('Damage policy changed after validation')
    if sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')!=receipt['runtime_sha256']:
        raise RuntimeError('Runtime changed after validation')
    if sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')!=receipt['game_main_sha256']:
        raise RuntimeError('Target game version changed after validation')
    profile=local(HERE/'test-profile');installed=local(profile/'mods/magnet-spike-experimental')
    suffix=sha(source/'exefs/subsdk1')[:12]
    backup=local(HERE/'backups'/('mod-before-'+suffix));save_backup=local(HERE/'backups'/('save-before-'+suffix))
    pending=local(installed.parent/('mod-pending-'+suffix))
    prior_backup=local(HERE/'backups'/('installed-build-before-'+suffix+'.json'))
    next_receipt=local(HERE/'installed-build.pending.json')
    if any(p.exists() for p in (backup,save_backup,pending,prior_backup,next_receipt)):
        raise RuntimeError('Transaction path already exists; nothing overwritten')
    with (profile/'session.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            saved={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')}
            if saved!=receipt['source_save_hashes'] or files(installed)!=prior['files']:
                raise RuntimeError('Public profile changed since validation')
            save_backup.mkdir()
            for n,digest in saved.items():
                shutil.copyfile(profile/'save/save_0'/n,save_backup/n)
                if sha(save_backup/n)!=digest:raise RuntimeError('Rollback save hash mismatch')
            shutil.copyfile(prior_path,prior_backup);shutil.copytree(source,pending)
            if files(pending)!=expected:raise RuntimeError('Pending mod differs from validated mod')
            result={'revision':'recovery-1','module_sha256':sha(source/'exefs/subsdk1'),
                'files':expected,'backup':str(backup),'save_backup':str(save_backup),
                'preinstall_save_hashes':saved,'saves_unchanged':True,'previous_revision':prior['revision'],
                'validation_receipt':str(receipt_path),'validation_receipt_sha256':sha(receipt_path),
                'balance_policy_sha256':receipt['balance_policy_sha256'],
                'balance_ttk_scope':'Previous balance-1 kill timings are historical; recovery intentionally changes attack cadence.',
                'full_port_complete':False}
            next_receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            os.replace(installed,backup)
            try:
                os.replace(pending,installed)
                if files(installed)!=expected:raise RuntimeError('Installed mod differs from validated mod')
                if saved!={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')}:
                    raise RuntimeError('Public saves changed during install')
                os.replace(next_receipt,prior_path)
            except BaseException:
                if installed.exists():os.replace(installed,pending)
                os.replace(backup,installed);raise
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    print('Installed recovery-1; original saves unchanged, paired rollback retained.')


if __name__=='__main__':main()
