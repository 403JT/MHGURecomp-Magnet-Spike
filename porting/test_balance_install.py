"""Exercise install success, refusal and two rollback failures on synthetic files."""
import contextlib,io,json,sys
from pathlib import Path
from unittest.mock import patch
import install_balance_candidate as installer
from prepare_frontier import HERE,ROOT,sha
from audit_balance_preservation import files


def fixture(root):
    mod=root/'output/magnet-spike-experimental/exefs';mod.mkdir(parents=True)
    (mod/'subsdk1').write_bytes(b'synthetic-new-module')
    old=root/'test-profile/mods/magnet-spike-experimental/exefs';old.mkdir(parents=True)
    (old/'subsdk1').write_bytes(b'synthetic-old-module')
    save=root/'test-profile/save/save_0';save.mkdir(parents=True)
    (save/'system').write_bytes(b'synthetic-save-must-not-change')
    (root/'backups').mkdir();(root/'reports').mkdir()
    (root/'balance-policy.json').write_text('{}\n',encoding='utf-8')
    proof=root/'reports/proof.json';proof.write_text('{"synthetic":true}\n',encoding='utf-8')
    names={'reference','primary_ttk','special_damage','static','preservation','equipment',
        'charge','cancel','normal_pin_inputs','combat_audio','combat_KO','crafted_reload'}
    receipt={'all_passed':True,'checks':{'synthetic':True},'mod_files':files(mod.parent),
        'policy_sha256':sha(root/'balance-policy.json'),'save_hashes':{'system':sha(save/'system')},
        'evidence':{n:{'path':'reports/proof.json','sha256':sha(proof)} for n in names}}
    (root/'reports/receipt.json').write_text(json.dumps(receipt),encoding='utf-8')
    (root/'installed-build.json').write_text(json.dumps({'revision':'smithy-1','files':files(old.parent)}),encoding='utf-8')
    return receipt


def main():
    base=HERE/'output/install-transaction-fixtures'
    if base.exists():raise RuntimeError('Synthetic fixture label already exists')
    checks={};real_replace=installer.os.replace
    for case in ('success','reject_changed_receipt','fail_new_directory','fail_receipt_commit'):
        root=base/case;receipt=fixture(root)
        installed=root/'test-profile/mods/magnet-spike-experimental'
        old=files(installed);old_receipt=(root/'installed-build.json').read_bytes()
        if case=='reject_changed_receipt':(root/'balance-policy.json').write_text('{"changed":true}',encoding='utf-8')
        injected=False
        def replace(source,destination):
            nonlocal injected
            source,destination=Path(source),Path(destination)
            if not injected and ((case=='fail_new_directory' and source.name.startswith('mod-pending-') and destination==installed)
                    or (case=='fail_receipt_commit' and source.name=='installed-build.pending.json')):
                injected=True;raise OSError('Synthetic one-time install failure')
            return real_replace(source,destination)
        error=None
        with patch.object(installer,'HERE',root),patch.object(installer,'ROOT',ROOT),\
             patch.object(sys,'argv',['install_balance_candidate.py','--receipt','receipt.json']),\
             patch.object(installer.os,'replace',side_effect=replace),contextlib.redirect_stdout(io.StringIO()):
            try:installer.main()
            except (OSError,RuntimeError) as exc:error=exc
        saves={p.name:sha(p) for p in (root/'test-profile/save/save_0').glob('system*')}
        if case=='success':
            result=json.loads((root/'installed-build.json').read_text())
            passed=not error and files(installed)==receipt['mod_files'] and files(Path(result['backup']))==old
            passed=passed and {p.name:sha(p) for p in Path(result['save_backup']).glob('system*')}==saves==receipt['save_hashes']
        else:
            passed=bool(error) and files(installed)==old and (root/'installed-build.json').read_bytes()==old_receipt and saves==receipt['save_hashes']
            if case.startswith('fail_'):passed=passed and injected
        checks[case]=bool(passed)
    report={'all_passed':all(checks.values()),'checks':checks,'installer_sha256':sha(HERE/'install_balance_candidate.py'),
        'scope':'Synthetic local files only. Verifies clean success/refusal and directory/receipt failure rollback without changing any real game profile.'}
    (HERE/'reports/balance-install-transaction-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Synthetic installer transaction checks:',sum(checks.values()),'/',len(checks));assert report['all_passed'],checks


if __name__=='__main__':main()
