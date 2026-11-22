"""Check every serialized hit through the original GU HDP getter and constructor."""
import json,re,struct,sys
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn import arm_const as A
from build_module import HERE,MS
sys.path[:0]=[str(MS/'tools'),str(MS.parents[1]/'tools')]
import arcpack,mshit,sdt

def main():
    data=(HERE/'work/gu_main/mem.bin').read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    u.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
    u.mem_map(0,max(0x2600000,(len(data)+4095)&~4095));u.mem_write(0,data)
    heap,stack,ret=0xc000000,0x71000000,0x70000000
    u.mem_map(heap,0x100000);u.mem_map(stack,0x10000);u.mem_map(ret,4096)
    u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
    resource,vt,attack,file=heap+0x1000,heap+0x2000,heap+0x4000,heap+0x10000
    stream,stream_vt,temp=heap+0x3000,heap+0x3800,heap+0x30000
    fake_size,fake_read=heap+0x60000,heap+0x60010
    stream_data=b''
    def w32(at,v):u.mem_write(at,struct.pack('<I',v))
    def hook(uc,pc,size,_):
        if pc in (0x16b920,0x887648,0x887660):
            uc.reg_write(A.UC_ARM_REG_R0,1);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
        elif pc in (0x270c54,0x270cd8):
            # Supply only the external allocator result; execute the original
            # parser's validation, copy, resource fields and success paths.
            uc.reg_write(A.UC_ARM_REG_R0,temp if pc==0x270c54 else file)
            uc.reg_write(A.UC_ARM_REG_PC,0x270c74 if pc==0x270c54 else 0x270cf8)
        elif pc==0x270d2c:uc.reg_write(A.UC_ARM_REG_PC,0x270d48) # external temporary-buffer free
        elif pc==fake_size:
            uc.reg_write(A.UC_ARM_REG_R0,len(stream_data));uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
        elif pc==fake_read:
            uc.mem_write(uc.reg_read(A.UC_ARM_REG_R1),stream_data)
            uc.reg_write(A.UC_ARM_REG_R0,len(stream_data));uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
        elif pc==0x13efe30:
            dst,src,n=(uc.reg_read(r) for r in (A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2))
            uc.mem_write(dst,bytes(uc.mem_read(src,n)));uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook)
    def call(pc,*args,shape=0):
        for reg,v in zip((A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3),args):u.reg_write(reg,v)
        sp=stack+0xf000;u.mem_write(sp,bytes(64));w32(sp+4,shape)
        u.reg_write(A.UC_ARM_REG_SP,sp);u.reg_write(A.UC_ARM_REG_LR,ret);u.emu_start(pc,ret,count=10000)
        assert u.reg_read(A.UC_ARM_REG_PC)==ret
        return u.reg_read(A.UC_ARM_REG_R0)
    def load(blob):
        u.mem_write(file,blob);w32(resource,vt);w32(vt+0x40,0x270d8c)
        w32(resource+0x64,file);w32(resource+0x68,file+16)
    def hdp(path):return next(d for p,t,d in arcpack.read(path.read_bytes())[1] if p.endswith('pl_we05_hitdata'))
    old=hdp(HERE/'backups/parity1-before-world-hits/w05.arc');new=hdp(MS/'romfs/nativeNX/arc/player/quest/w05.arc')
    base=int(re.search(r'#define MS_MAG_BASE (\d+)',(MS/'gen/ms_data.inc').read_text(encoding='utf-8'))[1])
    load(old);ptr=call(0x270d98,resource,base-3)
    checks={'legacy_shape_binding_failure_reproduced':u.mem_read(ptr+0x20,1)[0]!=(base-4),
        'legacy_last_record_exceeds_serialized_span':call(0x270d98,resource,2*base)+56>file+len(old)}
    try:mshit.hdp_parse(old);checks['legacy_truncated_layout_rejected']=False
    except ValueError:checks['legacy_truncated_layout_rejected']=True
    source=(MS.parents[1]/'dump/mhf/zz/mhfsdt.dec.bin').read_bytes()
    banks={e['kind']:sdt.attacks(source,e) for e in sdt.entries(source) if e['kind'] in (0x78,0x79)}
    expected={}
    for line in (MS/'gen/report.txt').read_text(encoding='utf-8').splitlines():
        m=re.match(r'hit\s+(\d+): .* MHF (attack|special)\s+(\d+) MV',line)
        if m:
            hit,kind,ident=m.groups();expected[int(hit)]=banks[0x78 if kind=='attack' else 0x79][int(ident)]
    stream_data=new
    w32(resource,vt);w32(vt+0x3c,0x270bd0);w32(vt+0x40,0x270d8c)
    w32(resource+0x64,0);w32(resource+0x68,0)
    w32(stream,stream_vt);w32(stream_vt+0x4c,fake_size);w32(stream_vt+0x34,fake_read)
    checks['original_native_loader_accepts_repaired_file']=call(0x270c18,resource,stream)==1
    checks['original_loader_points_to_16_byte_record_start']=int.from_bytes(u.mem_read(resource+0x68,4),'little')==file+16
    bounds=shape_ids=power=duration=damage=wide=True
    for hit in range(2*base+1):
        ptr=call(0x270d98,resource,hit);bounds &= file+16<=ptr and ptr+56<=file+len(new)
        if not hit:continue
        normal=hit if hit<=base else hit-base;r=expected[normal]
        mv=r['mv'] if hit<=base else r['mv']*110//100;shape=normal-1
        got=u.mem_read(ptr+0x20,1)[0];shape_ids &= got==shape
        call(0x168960,attack,8,0,ptr,shape=got)
        shape_ids &= int.from_bytes(u.mem_read(attack+0x88,4),'little')==shape
        power &= int.from_bytes(u.mem_read(attack+0x38,2),'little')==min(mv,250)
        duration &= struct.unpack('<f',u.mem_read(attack+0x60,4))[0]==2*r['raw'][1] and struct.unpack('<f',u.mem_read(attack+0x5c,4))[0]==0
        damage &= int.from_bytes(u.mem_read(attack+0x40,2),'little')==(2 if r['type']&0x200 else 1)
        wide &= int.from_bytes(u.mem_read(attack+0x9c,2),'little')==mv
    checks.update(all_native_record_spans_in_file=bounds,all_source_shape_ids_reach_native_attack=shape_ids,
        all_source_attack_powers_retained=power,all_source_live_durations_retained=duration,
        all_cutting_and_impact_types_retained=damage,all_full_motion_values_retained=wide,
        out_of_range_native_getters_return_null=call(0x270d98,resource,2*base+1)==0)
    report={'checks':checks,'all_passed':all(checks.values()),'native_records_checked':2*base+1,
        'scope':'Original GU HDP loader, count/getter and attack constructor; synthetic stream/allocators and supplied source hits'}
    (HERE/'reports/hit-layout-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
