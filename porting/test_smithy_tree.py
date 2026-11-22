"""Execute compiled ARM tree hooks against every original GS base record.

Verify field preservation, unchanged upgrade graph, full native row routing,
names at level boundaries, model ID isolation and unrelated class fallthrough.
No original data or generated tables are printed.
"""
import json,struct
from build_module import HERE,OUT,MS,UPMOD,run,symbols
from build_smithy_tree import audit,generate
from test_runtime import Emulator,BASE,HEAP
from build_balance import generate as generate_balance,scale,policy
from unicorn import arm_const as A

EXPORTS=['ms_base_c','ms_base_find_c','ms_level_c','ms_forge_create_c','ms_forge_process_c',
    'ms_tree_model_file_c','ms_tree_file_id','ms_tree_forge_count_c','test_name','test_type']
GS,VT,REG,STR=HEAP+0x10000,HEAP+0x20000,HEAP+0x30000,HEAP+0x40000
LEVELS=HEAP+0x50000

class TreeEmulator(Emulator):
    def engine(self,u,pc,size,data):
        off=pc-BASE
        if off==0x13c208:
            assert u.reg_read(A.UC_ARM_REG_R1)==7
            i=u.reg_read(A.UC_ARM_REG_R2)
            u.reg_write(A.UC_ARM_REG_R0,GS+40*i if i<137 else 0)
        elif off==0x13ed08:
            assert u.reg_read(A.UC_ARM_REG_R1)==7
            i=u.reg_read(A.UC_ARM_REG_R2)
            u.reg_write(A.UC_ARM_REG_R0,LEVELS+20*i if i<959 else 0)
        elif off in (0x100,0x104):
            # Simulates the source's three name variants. Native GS record ptr
            # must be passed, never the retyped Magnet Spike record.
            p=u.reg_read(A.UC_ARM_REG_R0);assert GS<=p<GS+40*137
            lv=u.reg_read(A.UC_ARM_REG_R1);k=0 if lv<4 else 1 if lv<8 else 2
            u.reg_write(A.UC_ARM_REG_R0,STR+k*64)
        else:return super().engine(u,pc,size,data)
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))

    def hook(self,name,ty,n,r3=0):
        values=[HEAP,ty,n,r3]+[0xfeed0000+i for i in range(12)]
        self.uc.mem_write(REG,struct.pack('<16I',*values))
        handled=self.call(name,REG)
        return handled,struct.unpack('<16I',self.uc.mem_read(REG,64))

def main():
    generate();generate_balance();balance=policy();tables,models,mapping,_=audit()
    dest=OUT/'regression';dest.mkdir(exist_ok=True)
    obj,elf=dest/'smithy.o',dest/'smithy.elf'
    run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-DMS_RECOMP','-DMS_GS_TREE','-DMS_BALANCE',
        '-I',MS/'module','-I',UPMOD,'-I',OUT,'-c',HERE/'tests/smithy_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--image-base=0x10000','-e',EXPORTS[0],'-o',elf,obj)
    data=elf.read_bytes();e=TreeEmulator((data,symbols(data)));checks={}
    # Typed packed->memory loader follows documented native 33->40 layout.
    rows=[];level_start=0
    for i,p in enumerate(tables['base'][0]):
        r=bytearray(40);struct.pack_into('<I',r,0,VT+8)
        r[4:23]=p[:19];r[24:28]=p[19:23]
        for j in range(5):r[28+j]=p[23+2*j];r[33+j]=p[24+2*j]
        struct.pack_into('<H',r,38,level_start);level_start+=p[9]+p[10]
        rows.append(bytes(r));e.uc.mem_write(GS+40*i,bytes(r))
    e.uc.mem_write(VT,struct.pack('<92I',*[BASE+0x100]*92));e.w32(VT+8+0xbc,BASE+0x104)
    for k,n in enumerate((b'Iron Sword',b'Carbalite Sword',b'Eltalite Sword')):e.uc.mem_write(STR+k*64,n+b'\0')
    before=bytes(e.uc.mem_read(GS,40*137))
    preserved=names_ok=identity=True
    for i,original in enumerate(rows):
        handled,regs=e.hook('ms_base_c',12,i);assert handled==1 and regs[0]
        p=regs[0];r=bytes(e.uc.mem_read(p,40))
        preserved &= all(r[j]==original[j] for j in range(4,40) if j not in range(8,12))
        identity &= struct.unpack_from('<I',r,4)[0]==i and struct.unpack_from('<H',r,8)[0]==mapping[i]
        for lv,source in ((1,b'Iron Sword'),(4,b'Carbalite Sword'),(8,b'Eltalite Sword')):
            ptr=e.call('test_name',p,lv)
            actual=bytes(e.uc.mem_read(ptr,64)).split(b'\0')[0]
            names_ok &= actual==b'MS '+source
    checks['all_137_base_records_preserve_stats_prices_sort_and_upgrade_links']=bool(preserved)
    checks['all_base_records_keep_independent_ids_and_assigned_models']=bool(identity)
    checks['names_follow_all_three_source_level_variants']=bool(names_ok)
    checks['source_gs_records_are_byte_identical']=bytes(e.uc.mem_read(GS,40*137))==before
    checks['new_type_is_12']=e.call('test_type')==12
    checks['base_out_of_bounds_returns_null']=all(e.hook('ms_base_c',12,n)[1][0]==0 for n in (137,255,0xffffffff))
    packed=[]
    for i,row in enumerate(tables['level'][0]):
        r=struct.pack('<I',VT+8)+row+b'\xa5';assert len(r)==20
        packed.append(r);e.uc.mem_write(LEVELS+20*i,r)
    snapshot=bytes(e.uc.mem_read(LEVELS,len(packed)*20));levels_ok=distinct=True
    for i,original in enumerate(packed):
        h,r=e.hook('ms_level_c',12,i);assert h==1 and r[0]
        got=bytes(e.uc.mem_read(r[0],20));distinct &= r[0]!=LEVELS+20*i
        raw,elem=struct.unpack_from('<H',original,12)[0],struct.unpack_from('<H',original,16)[0]
        levels_ok &= struct.unpack_from('<H',got,12)[0]==scale(raw,balance['raw_percent'])
        levels_ok &= struct.unpack_from('<H',got,16)[0]==(elem*balance['element_percent']+50)//100
        levels_ok &= all(got[j]==original[j] for j in range(20) if j not in (12,13,16,17))
    checks['all_959_cloned_levels_change_only_policy_raw_and_element_fields']=bool(levels_ok)
    checks['level_rows_have_independent_stable_storage']=bool(distinct)
    checks['source_gs_level_records_are_byte_identical']=bytes(e.uc.mem_read(LEVELS,len(packed)*20))==snapshot
    checks['out_of_range_level_rows_return_null']=all(e.hook('ms_level_c',12,n)[1][0]==0 for n in (959,0xffffffff))
    for function,key in [('ms_forge_create_c','create'),('ms_forge_process_c','process')]:
        valid=True
        for i in range(len(tables[key][0])+1):
            h,r=e.hook(function,12,i);valid &= h==0 and r[:4]==(HEAP,7,i,0)
        checks[key+'_all_rows_and_end_sentinel_use_original_native_getter']=bool(valid)
    unchanged=True
    for ty in range(32):
        if ty==12:continue
        for fn in ('ms_base_c','ms_base_find_c','ms_level_c','ms_forge_create_c','ms_forge_process_c'):
            h,r=e.hook(fn,ty,7);unchanged &= h==0 and r[:4]==(HEAP,ty,7,0)
    checks['all_other_equipment_types_unchanged']=bool(unchanged)
    isolated=True
    for n in range(1,41):
        h,r=e.hook('ms_tree_model_file_c',5,0,n);isolated &= h==1 and r[0]==0x10b00+n-1
        h,r=e.hook('ms_tree_model_file_c',5,1,n);isolated &= h==1 and r[0]==0
    checks['40_models_use_new_file_ids_without_native_collisions']=bool(isolated)
    checks['invalid_model_ids_are_rejected']=all(e.hook('ms_tree_model_file_c',5,0,n)[1][0]==0 for n in (0,41,0xffffffff))
    checks['other_classes_keep_native_model_lookup']=all(e.hook('ms_tree_model_file_c',c,0,1)[0]==0 for c in range(16) if c!=5)
    checks['new_type_cannot_increment_the_native_LBG_forge_counter']=all(e.hook('ms_tree_forge_count_c',c,0)[0]==int(c==12) for c in range(32))
    checks['branches_to_different_original_appearances_change_spike_model']=all(
        mapping[i]!=mapping[child]
        for i,r in enumerate(tables['base'][0]) for child in (r[24+2*j] for j in range(5))
        if child and r[4:6]!=tables['base'][0][child][4:6])
    report={'all_passed':all(checks.values()),'checks':checks,'rows_checked':{k:len(v[0]) for k,v in tables.items()},
        'source_table_hashes':{k:v[1] for k,v in tables.items()}}
    (HERE/'reports/smithy-tree-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('ARM smithy tree checks:',sum(checks.values()),'/',len(checks));assert report['all_passed']
if __name__=='__main__':main()
