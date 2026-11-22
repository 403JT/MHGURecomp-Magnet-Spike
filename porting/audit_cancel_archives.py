"""Limit archive changes to traced roll/walk routes and charge timing fields."""
import copy,hashlib,json,re,sys
from prepare_frontier import HERE,CONVERTER

def main():
    sys.path.insert(0,str(CONVERTER/'tools'));import arcpack,xfs
    ms=CONVERTER/'weapons/magnet_spike'
    source=(ms/'gen/ms_data.inc').read_text(encoding='utf-8')
    source=source.split('static const struct ms_step ms_steps[] = {',1)[1].split('};',1)[0]
    actions={int(f.split(',')[-1])-2000:int(a) for f,a in re.findall(r'\{([^}]+)\},\s*/\* (\d+):',source)}
    changed=set()
    def rows(v):return v if isinstance(v,list) else [v] if v else []
    for style in range(6):
        old={(p,t):b for p,t,b in arcpack.read((HERE/'backups/parity2-before-cancel-windows'/f'w05_m{style}.arc').read_bytes())[1]}
        new={(p,t):b for p,t,b in arcpack.read((ms/'romfs/nativeNX/arc/player/quest'/f'w05_m{style}.arc').read_bytes())[1]}
        assert old.keys()==new.keys(),'Command resource set changed'
        for key in old:
            if key[1]!=0x4b4c2bd3:
                assert old[key]==new[key],'Command resource bytes changed';continue
            a=xfs.parse(old[key]);b=xfs.parse(new[key]);ta=a['TblList']['mpArray'];tb=b['TblList']['mpArray']
            assert len(ta)==len(tb)
            for n,(x,y) in enumerate(zip(ta,tb)):
                if x==y:continue
                changed.add(n);assert n in actions,'Common table changed'
                expected=copy.deepcopy(x);out=[];previous=None
                for row in rows(expected['Command']['mpArray']):
                    path=row['CmdBase'][1];name=path.split('\\')[-1]
                    if name=='plcmd_com_0x0001_014a':
                        assert previous and previous['CmdBase'][1].endswith('plcmd_com_0x0001_013a')
                        twin=copy.deepcopy(previous);twin['CmdBase']=row['CmdBase'];assert twin==row
                        previous=row;continue
                    previous=copy.deepcopy(row)
                    if name=='plcmd_com_0x0001_013a':path=path.rsplit('\\',1)[0]+'\\plcmd_com_0x0001_006e'
                    elif name=='plcmd_com_0x0001_006e':path=path.rsplit('\\',1)[0]+'\\plcmd_com_0x0002_000a'
                    row['CmdBase']=(row['CmdBase'][0],path,row['CmdBase'][2])
                    if actions[n]==34:row.update(PreFrame=0x3f800000,StartFrame=0,EndFrame=0x3f800000)
                    out.append(row)
                actual=copy.deepcopy(y);actual['Command']['mpArray']=rows(actual['Command']['mpArray'])
                expected['Command']['mpArray']=out
                assert expected==actual,'Unexpected change in source table '+str(n)
            a['TblList']['mpArray']=[];b['TblList']['mpArray']=[];assert a==b
    checks={'all_six_styles_checked':True,'common_tables_unchanged':True,'command_bytes_and_resource_set_unchanged':True,
            'only_expected_routes_and_charge_timing_changed':True}
    staged=HERE/'output/magnet-spike-experimental'
    for style in range(6):
        rel=f'romfs/nativeNX/arc/player/quest/w05_m{style}.arc'
        assert (staged/rel).read_bytes()==(ms/rel).read_bytes(),'Staged style archive differs'
    files={str(p.relative_to(staged)):hashlib.sha256(p.read_bytes()).hexdigest() for p in staged.rglob('*') if p.is_file()}
    proof={'checks':checks,'all_passed':True,'changed_table_count':len(changed),'mod_files':files,
           'scope':'All changed tables match only roll/walk substitutions and charge timing placeholders; all command-resource bytes identical'}
    (HERE/'reports/cancel-archive-diff.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8')
    print('Verified all six styles;',len(changed),'source tables changed only through expected routes/timing; common tables/resources unchanged.')
if __name__=='__main__':main()
