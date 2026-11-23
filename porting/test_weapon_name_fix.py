"""Check exact requested MS names against the compiled alpha.3 name getter."""
import json
import struct
import sys
from build_module import HERE,MS,UPMOD,OUT,run,symbols
from prepare_frontier import ROOT,CONVERTER
from test_smithy_tree import TreeEmulator,GS,VT,STR,BASE
sys.path.insert(0,str(CONVERTER/'tools/gulib'))
from gmd import gmd_strings

EXPECTED={
    'Avidya Great Sword':'Avidya Magnet Spike',
    'Tigrex Great Sword':'Tigrex Magnet Spike',
    'Skeletal Great Sword':'Skeletal Magnet Spike',
    'Infernal Great Sword':'Infernal Magnet Spike',
    'Alatreon Great Sword':'Alatreon Magnet Spike',
    'Rusted Great Sword':'Rusted Magnet Spike',
    'Worn Great Sword':'Worn Magnet Spike',
    'Aged Great Sword':'Aged Magnet Spike',
    'Gold Great Sword':'Gold Magnet Spike',
    'Silverwing Great Sword':'Silverwing Magnet Spike',
    'Elderfrost Great Sword':'Elderfrost Magnet Spike',
    'Research Great Sword':'Research Magnet Spike',
    'Discovery Great Sword':'Discovery Magnet Spike',
}


def compile_getter(old):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    name='weapon-names-'+('alpha3' if old else 'fixed')
    obj,elf=folder/(name+'.o'),folder/(name+'.elf')
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-DMS_RECOMP','-DMS_GS_TREE','-DMS_BALANCE',
        '-I',MS/'module','-I',UPMOD,'-I',OUT]
    if old:
        source=HERE/'public-release/v0.1.0-alpha.3/repo/porting/module/smithy.c'
        flags+=['-DMS_TEST_SMITHY_SOURCE="'+source.as_posix()+'"']
    run('clang',*flags,'-c',HERE/'tests/smithy_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--image-base=0x10000',
        '-e','test_name','-o',elf,obj)
    data=elf.read_bytes();return data,symbols(data)


def setup(binary):
    e=TreeEmulator(binary)
    e.uc.mem_write(VT,struct.pack('<92I',*[BASE+0x100]*92))
    e.w32(VT+8+0xbc,BASE+0x104)
    for ident in range(137):
        row=bytearray(40);struct.pack_into('<II',row,0,VT+8,ident)
        e.uc.mem_write(GS+40*ident,bytes(row))
    return e


def displayed(e,p,level=None):
    address=e.call('test_base_name',p) if level is None else e.call('test_name',p,level)
    return bytes(e.uc.mem_read(address,64)).split(b'\0')[0].decode('utf-8')


def main():
    gmd=ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs/nativeNX/eng/table/weapon00MsgData_eng.gmd'
    text=gmd_strings(gmd.read_bytes());assert len(text)==137*6
    old,new=setup(compile_getter(True)),setup(compile_getter(False))
    snapshots=[bytes(e.uc.mem_read(GS,40*137)) for e in (old,new)]
    checks={'every_requested_name_exact':True,'other_names_match_alpha3':True,
        'base_name_getter_uses_requested_name':True,'cached_repeat_reads_match':True,
        'native_GS_strings_unchanged':True}
    changed=[];unchanged=0
    for ident in range(1,137):
        variants=[text[ident*6+j] for j in (0,2,4)]
        for e in (old,new):
            for k,name in enumerate(variants):
                encoded=name.encode('utf-8');assert len(encoded)<64
                e.uc.mem_write(STR+k*64,encoded+b'\0'+bytes(63-len(encoded)))
        before=[bytes(e.uc.mem_read(STR,192)) for e in (old,new)]
        records=[]
        for e in (old,new):
            handled,registers=e.hook('ms_base_c',12,ident)
            assert handled and registers[0];records.append(registers[0])
        for variant,(source,level) in enumerate(zip(variants,(1,4,8)),1):
            prior=displayed(old,records[0],level);actual=displayed(new,records[1],level)
            assert prior=='MS '+source
            expected=EXPECTED.get(source,prior)
            if source in EXPECTED:
                checks['every_requested_name_exact'] &= actual==expected
                changed.append({'weapon_id':ident,'variant':variant,'old_name':prior,'new_name':actual})
            else:
                checks['other_names_match_alpha3'] &= actual==prior;unchanged+=1
            checks['cached_repeat_reads_match'] &= displayed(new,records[1],level)==expected
            if variant==1:checks['base_name_getter_uses_requested_name'] &= displayed(new,records[1])==expected
        checks['native_GS_strings_unchanged'] &= all(bytes(e.uc.mem_read(STR,192))==snapshot for e,snapshot in zip((old,new),before))
    checks['exactly_13_variants_renamed']=len(changed)==13 and {c['new_name'] for c in changed}==set(EXPECTED.values())
    checks['all_395_other_variants_unchanged']=unchanged==395
    checks['native_GS_records_unchanged']=all(bytes(e.uc.mem_read(GS,40*137))==snapshot for e,snapshot in zip((old,new),snapshots))
    checks['native_GS_type_falls_through']=new.hook('ms_base_c',7,19)[0]==0
    report={'all_passed':all(checks.values()),'checks':checks,'families_checked':136,
        'name_variants_checked':408,'renamed':changed,'other_name_variants_unchanged':unchanged,
        'scope':'Actual compiled old/new MS getters; native GS getter supplies its three name variants; no game launch'}
    (HERE/'reports/weapon-name-fix-validation.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({n:report[n] for n in ('all_passed','checks','families_checked','name_variants_checked','other_name_variants_unchanged')}))
    assert report['all_passed']


if __name__=='__main__':main()
