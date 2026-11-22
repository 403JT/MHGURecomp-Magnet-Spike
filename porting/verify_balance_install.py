"""Independently verify the installed balance pair, rollback and unchanged saves."""
import json
from pathlib import Path
from prepare_frontier import HERE,ROOT,sha
from audit_balance_preservation import files


def local(path):
    p=Path(path).resolve();assert p.is_relative_to(ROOT.resolve());return p


def main():
    install=json.loads((HERE/'installed-build.json').read_text(encoding='utf-8'))
    assert install['revision']=='balance-1'
    receipt_path=local(install['balance_receipt'])
    receipt=json.loads(receipt_path.read_text(encoding='utf-8'))
    manifest=json.loads((HERE/'backups/before-balance-1/manifest.json').read_text(encoding='utf-8'))
    baseline=files(HERE/'backups/before-balance-1/mod')
    saved={p.name:sha(p) for p in (HERE/'test-profile/save/save_0').glob('system*')}
    backup_saves={p.name:sha(p) for p in local(install['save_backup']).glob('system*')}
    checks={
        'all_56_installed_files_equal_staged_and_receipt':len(install['files'])==56
            and files(HERE/'test-profile/mods/magnet-spike-experimental')==files(HERE/'output/magnet-spike-experimental')==install['files']==receipt['mod_files'],
        'validation_receipt_intact_and_passing':sha(receipt_path)==install['balance_receipt_sha256'] and receipt['all_passed'] and all(receipt['checks'].values()),
        'rollback_module_exactly_matches_original_smithy_build':files(local(install['backup']))==baseline,
        'rollback_save_and_live_save_equal_preinstall_hashes':backup_saves==saved==install['preinstall_save_hashes']==receipt['save_hashes'],
        'source_profile_saves_unchanged_since_balance_started':all(v==manifest[str(Path('save')/p)] for p,v in saved.items()),
        'original_public_executable_unchanged':sha(ROOT/'MHGURecomp-master/build/mhgurecomp.exe')==manifest[str(Path('files/MHGURecomp-master/build/mhgurecomp.exe'))],
        'policy_matches_validated_build':sha(HERE/'balance-policy.json')==receipt['policy_sha256']==json.loads((HERE/'output/module-status.json').read_text())['balance_policy_sha256'],
        'full_port_parity_not_claimed':install['full_port_complete'] is False and receipt['full_port_complete'] is False,
    }
    result={'all_passed':all(checks.values()),'checks':checks,'module_sha256':install['module_sha256'],
        'installed_files':install['files'],'save_hashes':saved,'rollback_module':install['backup'],'rollback_save':install['save_backup']}
    path=HERE/'reports/balance-install-integrity.json'
    if path.exists():raise RuntimeError('Install integrity receipt already exists')
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Installed balance integrity:',sum(checks.values()),'/',len(checks));assert result['all_passed']


if __name__=='__main__':main()
