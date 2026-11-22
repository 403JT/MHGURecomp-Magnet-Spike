"""Verify KO field interpretation using the user's original GU ARM routines."""
import json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn import arm_const as A
from build_module import HERE

def main():
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
    data=(HERE/'work/gu_main/mem.bin').read_bytes()
    u.mem_map(0,max(0x2600000,(len(data)+4095)&~4095));u.mem_write(0,data)
    heap=0xc000000;stack=0x71000000;ret=0x70000000
    u.mem_map(heap,0x100000);u.mem_map(stack,0x10000);u.mem_map(ret,4096)
    u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
    attack,header,monster,record,part=heap+0x1000,heap+0x2000,heap+0x10000,heap+0x20000,heap+0x30000
    def hook(uc,pc,size,_):
        if pc in (0x16b920,0x887648,0xbab60):
            uc.reg_write(A.UC_ARM_REG_R0,part if pc==0xbab60 else 1)
            uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,hook)
    def call(pc,*args):
        for reg,v in zip((A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3),args):u.reg_write(reg,v)
        u.reg_write(A.UC_ARM_REG_SP,stack+0xf000);u.mem_write(stack+0xf000,bytes(64))
        u.reg_write(A.UC_ARM_REG_LR,ret);u.emu_start(pc,ret,count=10000)
        assert u.reg_read(A.UC_ARM_REG_PC)==ret
    checks={}
    u.mem_write(header+0x22,b'\xbe');call(0x168960,attack,8,0,header)
    checks['native_constructor_would_drop_190_KO']=u.mem_read(attack+0x56,1)[0]==0
    u.mem_write(header+0x22,b'\x19');call(0x168960,attack,8,0,header)
    checks['native_constructor_maps_header_0x22_to_hit_0x56']=u.mem_read(attack+0x56,1)[0]==25
    u.mem_write(attack+0x56,b'\xbe');u.reg_write(A.UC_ARM_REG_R6,attack)
    u.reg_write(A.UC_ARM_REG_R7,heap+0x40000)
    u.emu_start(0x173040,0x173064,count=20)
    value=u.reg_read(A.UC_ARM_REG_R5)
    checks['native_collision_reads_full_unsigned_190']=value==190
    u.mem_write(monster+0x1428,struct.pack('<I',record))
    for multiplier,expected,label in ((100,190,'head'),(50,95,'scaled_part'),(0,0,'non_stunnable_part')):
        u.mem_write(record+0x4d2,b'\0\0');u.mem_write(part+8,bytes([multiplier]))
        call(0x9db54,monster,1,0,value)
        checks['native_'+label+'_KO_processing_preserved']=struct.unpack('<H',u.mem_read(record+0x4d2,2))[0]==expected
    report={'checks':checks,'all_passed':all(checks.values()),'scope':'Original GU constructor, unsigned KO load, and part-scaled pending-KO routine; synthetic objects'}
    (HERE/'reports/native-hitstats-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
