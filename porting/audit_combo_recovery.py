"""Prove only selected finisher timing tables and code differ from balance-1."""
import copy,json,os,sys
from pathlib import Path
from prepare_frontier import HERE,ROOT,CONVERTER,sha
from hunt_session import files


def main():
    os.environ['GU_ROMFS']=str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs')
    sys.path[:0]=[str(CONVERTER/'tools'),str(CONVERTER/'weapons/magnet_spike/tools')]
    import arcpack,xfs,msbuild
    old=HERE/'backups/before-recovery-1/mod';new=HERE/'output/magnet-spike-experimental'
    before,after=files(old),files(new)
    allowed={str(Path('exefs/subsdk1')),str(Path('exefs/FB08F1D20FD1204FE7070672777F869B.ips'))}
    styles=[str(Path(f'romfs/nativeNX/arc/player/quest/w05_m{i}.arc')) for i in range(6)]
    allowed.update(styles)
    changed={p for p in after if before.get(p)!=after[p]}
    assert before.keys()==after.keys() and changed==allowed
    checks={'same_file_layout':True,'only_code_and_six_command_archives_changed':True,
        'models_sounds_textures_and_other_assets_unchanged':all(before[p]==v for p,v in after.items() if p not in allowed)}
    # Determine affected table indexes locally; retain metadata only.
    from build_cancel_windows import generate
    generate()
    scoped={t['table']-2000 for t in msbuild.WINDOW_TABLES if t['action'] in msbuild.RECOVERY_FRAMES}
    changed_tables=set()
    for rel in styles:
        a={(p,t):b for p,t,b in arcpack.read((old/rel).read_bytes())[1]}
        b={(p,t):b for p,t,b in arcpack.read((new/rel).read_bytes())[1]}
        assert a.keys()==b.keys()
        for key in a:
            if a[key]==b[key]:continue
            assert key[1]==0x4b4c2bd3,'Command resource content changed'
            x,y=xfs.parse(a[key]),xfs.parse(b[key]);xx=x['TblList']['mpArray'];yy=y['TblList']['mpArray']
            assert len(xx)==len(yy)
            for i,(v,w) in enumerate(zip(xx,yy)):
                if v==w:continue
                assert i in scoped
                expected=copy.deepcopy(v)
                rows=expected['Command']['mpArray'];rows=rows if isinstance(rows,list) else [rows] if rows else []
                for r in rows:r.update(PreFrame=0x3f800000,StartFrame=0,EndFrame=0x3f800000)
                assert expected==w,'Non-timing field changed'
                changed_tables.add(i)
            x['TblList']['mpArray']=[];y['TblList']['mpArray']=[];assert x==y
    checks.update(command_resources_and_combo_targets_unchanged=True,
        earlier_combo_and_common_tables_unchanged=True,only_scoped_timing_placeholders_changed=True,
        six_styles_identically_audited=True)
    prior=json.loads((HERE/'backups/before-recovery-1/installed-build.json').read_text())
    checks['installed_baseline_not_modified']=files(HERE/'test-profile/mods/magnet-spike-experimental')==prior['files']
    report={'checks':checks,'all_passed':all(checks.values()),'changed_table_count':len(changed_tables),
        'mod_files':after,'previous_mod_files':before,'balance_policy_sha256':sha(HERE/'balance-policy.json'),
        'scope':'Six complete archive comparisons; all resource sets, command targets, row order and non-scoped tables preserved.'}
    (HERE/'reports/combo-recovery-preservation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'all_passed':report['all_passed'],'checks':len(checks),'changed_files':len(changed),'changed_tables':len(changed_tables)}))


if __name__=='__main__':main()
