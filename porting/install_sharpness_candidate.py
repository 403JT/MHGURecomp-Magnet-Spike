"""Install the validated sharpness mask with paired backups; never modify saves."""
import json,msvcrt,os,shutil
from prepare_frontier import HERE,ROOT,sha
from hunt_session import files


def main():
    receipt_path=HERE/'reports/sharpness-validation.json'
    r=json.loads(receipt_path.read_text());assert r['all_passed'] and all(r['checks'].values())
    for e in r['evidence'].values():
        p=(HERE/e['path']).resolve();assert p.is_relative_to(HERE.resolve()) and sha(p)==e['sha256']
    prior_path=HERE/'installed-build.json';prior=json.loads(prior_path.read_text())
    assert prior['revision']=='recovery-1' and prior['files']==r['previous_mod_files']
    profile=HERE/'test-profile';installed=profile/'mods/magnet-spike-experimental'
    source=HERE/'output/magnet-spike-experimental';expected=files(source);assert expected==r['mod_files']
    assert sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')==r['runtime_sha256']
    assert sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')==r['game_main_sha256']
    suffix='sharpness-'+sha(next((source/'exefs').glob('*.ips')))[:12]
    backup=HERE/'backups'/('mod-before-'+suffix);save_backup=HERE/'backups'/('save-before-'+suffix)
    pending=installed.parent/('mod-pending-'+suffix);next_receipt=HERE/'installed-build.pending.json'
    prior_backup=HERE/'backups'/('installed-build-before-'+suffix+'.json')
    assert not any(p.exists() for p in (backup,save_backup,pending,next_receipt,prior_backup))
    with (profile/'session.lock').open('a+b') as lock:
        lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        try:
            saved={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')}
            assert saved==r['source_save_hashes'] and files(installed)==prior['files']
            save_backup.mkdir()
            for n,h in saved.items():
                shutil.copyfile(profile/'save/save_0'/n,save_backup/n);assert sha(save_backup/n)==h
            shutil.copyfile(prior_path,prior_backup);shutil.copytree(source,pending);assert files(pending)==expected
            result={'revision':'sharpness-1','module_sha256':sha(source/'exefs/subsdk1'),
                'files':expected,'backup':str(backup),'save_backup':str(save_backup),
                'previous_revision':prior['revision'],'preinstall_save_hashes':saved,'saves_unchanged':True,
                'validation_receipt':str(receipt_path),'validation_receipt_sha256':sha(receipt_path),
                'balance_policy_sha256':sha(HERE/'balance-policy.json'),'full_port_complete':False}
            next_receipt.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            os.replace(installed,backup)
            try:
                os.replace(pending,installed);assert files(installed)==expected
                assert saved=={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')}
                os.replace(next_receipt,prior_path)
            except BaseException:
                if installed.exists():os.replace(installed,pending)
                os.replace(backup,installed);raise
        finally:
            lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
    checks={'installed_exact_validated_candidate':files(installed)==expected,
        'rollback_exact_previous_mod':files(backup)==prior['files'],
        'paired_save_backup_verified':all(sha(save_backup/n)==h for n,h in saved.items()),
        'source_saves_unchanged':saved=={p.name:sha(p) for p in (profile/'save/save_0').glob('system*')},
        'runtime_unchanged':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')==r['runtime_sha256'],
        'game_unchanged':sha(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs/main')==r['game_main_sha256']}
    out={'all_passed':all(checks.values()),'checks':checks,'revision':'sharpness-1','files':expected}
    (HERE/'reports/sharpness-install-integrity.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8')
    assert out['all_passed'];print('Installed sharpness-1; six independent integrity checks passed; original saves unchanged.')


if __name__=='__main__':main()
