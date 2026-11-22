"""Install only a completely validated balance receipt, with paired rollback saves.

The existing full-moveset installer keeps its stricter, separate gates. This
installer requires fresh damage/stat evidence plus explicit asset preservation;
historical smithy evidence is identified as historical in the balance receipt.
"""
import argparse,json,msvcrt,os,shutil
from prepare_frontier import HERE,ROOT,sha
from audit_balance_preservation import files


def local(path):
    p=path.resolve()
    if not p.is_relative_to(ROOT.resolve()):raise ValueError('Path leaves MHGU P2')
    return p


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--receipt',required=True);a=ap.parse_args()
    receipt_path=local(HERE/'reports'/a.receipt)
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    source=local(HERE/'output/magnet-spike-experimental');expected=files(source)
    if not receipt.get('all_passed') or not receipt.get('checks') or not all(receipt['checks'].values()):
        raise RuntimeError('Balance validation has not passed')
    if receipt.get('mod_files')!=expected or receipt.get('policy_sha256')!=sha(HERE/'balance-policy.json'):
        raise RuntimeError('Receipt belongs to a different candidate/policy')
    required={'reference','primary_ttk','special_damage','static','preservation','equipment',
        'charge','cancel','normal_pin_inputs','combat_audio','combat_KO','crafted_reload'}
    if not required<=set(receipt.get('evidence',{})):
        raise RuntimeError('Required balance gates are missing')
    for item in receipt['evidence'].values():
        p=local(HERE/item['path'])
        if sha(p)!=item['sha256']:raise RuntimeError('Evidence changed after validation: '+str(p))
    profile=local(HERE/'test-profile');installed=local(profile/'mods/magnet-spike-experimental')
    prior_path=HERE/'installed-build.json';prior=json.loads(prior_path.read_text(encoding='utf-8'))
    if files(installed)!=prior['files']:raise RuntimeError('Installed build differs from its receipt')
    import hashlib
    short=hashlib.sha256(json.dumps(expected,sort_keys=True).encode()).hexdigest()[:12]
    backup=local(HERE/'backups'/('mod-before-'+short))
    save_backup=local(HERE/'backups'/('save-before-'+short))
    pending=local(installed.parent/('mod-pending-'+short))
    prior_backup=local(HERE/'backups'/('installed-build-before-'+short+'.json'))
    if any(p.exists() for p in (backup,save_backup,pending,prior_backup)):
        raise RuntimeError('Install/rollback paths already exist; nothing overwritten')
    with (profile/'session.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            before={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')}
            if not before or before!=receipt['save_hashes']:raise RuntimeError('Public saves changed since validation')
            save_backup.mkdir()
            for name,digest in before.items():
                shutil.copyfile(profile/'save/save_0'/name,save_backup/name)
                if sha(save_backup/name)!=digest:raise RuntimeError('Rollback save hash mismatch')
            shutil.copyfile(prior_path,prior_backup)
            shutil.copytree(source,pending)
            if files(pending)!=expected:raise RuntimeError('Pending files differ from tested build')
            result={'revision':'balance-1','module_sha256':sha(source/'exefs/subsdk1'),
                'files':expected,'backup':str(backup),'save_backup':str(save_backup),
                'preinstall_save_hashes':before,'saves_unchanged':True,
                'balance_receipt':str(receipt_path),'balance_receipt_sha256':sha(receipt_path),
                'previous_revision':prior['revision'],'full_port_complete':False}
            # Prepare receipt before swapping directories. Restore the old mod
            # if the new receipt cannot be installed; never leave a mixed pair.
            next_receipt=local(HERE/'installed-build.pending.json')
            if next_receipt.exists():raise RuntimeError('Pending receipt already exists')
            next_receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            os.replace(installed,backup)
            try:
                os.replace(pending,installed)
                if files(installed)!=expected:raise RuntimeError('Installed files differ from tested build')
                if before!={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')}:
                    raise RuntimeError('Public saves changed during installation')
                os.replace(next_receipt,prior_path)
            except BaseException:
                if installed.exists():os.replace(installed,pending)
                os.replace(backup,installed)
                raise
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    print('Installed validated balance-1 with matching module/save rollback copies.')


if __name__=='__main__':main()
