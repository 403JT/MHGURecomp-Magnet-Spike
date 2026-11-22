"""Execute GU's original hit-sound selector against synthetic collision records."""
import json
import struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn import arm_const as A
from prepare_frontier import HERE

HEAP=0x0c000000
P,INFO,ATTACK,MON,POS=HEAP,HEAP+0x20000,HEAP+0x30000,HEAP+0x40000,HEAP+0x50000
RET,STACK=0x70000000,0x71010000

def trace(cls,kind,tier):
    data=(HERE/'work/gu_main/mem.bin').read_bytes()
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
    u.mem_map(0,0x2400000);u.mem_write(0,data)
    u.mem_map(HEAP,0x100000);u.mem_map(RET,4096);u.mem_map(STACK-0x10000,0x10000)
    u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
    u.mem_write(P+0x13c4,struct.pack('<I',INFO));u.mem_write(INFO+0x4d4,bytes([cls]))
    u.mem_write(ATTACK+0x70,struct.pack('<I',P));u.mem_write(ATTACK+0x55,bytes([kind]));u.mem_write(ATTACK+6,bytes([tier,2]))
    posts=[]
    def hook(uc,addr,size,_):
        if addr==0x4ef098:
            posts.append({'bank':'system','request':uc.reg_read(A.UC_ARM_REG_R1)})
        elif addr==0x4ef7a4:
            posts.append({'bank':'player-'+str(uc.reg_read(A.UC_ARM_REG_R1)),'request':uc.reg_read(A.UC_ARM_REG_R2)})
        elif addr==0x4efb98:posts.append({'bank':'monster','request':uc.reg_read(A.UC_ARM_REG_R1)})
        elif addr in (0x27c7ec,0x27bcd0,0x180c84):pass
        else:return
        uc.reg_write(A.UC_ARM_REG_R0,0);uc.reg_write(A.UC_ARM_REG_PC,uc.reg_read(A.UC_ARM_REG_LR))
    for addr in (0x4ef098,0x4ef7a4,0x4efb98,0x27c7ec,0x27bcd0,0x180c84):u.hook_add(UC_HOOK_CODE,hook,begin=addr,end=addr)
    for reg,value in ((A.UC_ARM_REG_R0,MON),(A.UC_ARM_REG_R1,MON),(A.UC_ARM_REG_R2,ATTACK),(A.UC_ARM_REG_R3,POS),(A.UC_ARM_REG_SP,STACK-16),(A.UC_ARM_REG_LR,RET)):u.reg_write(reg,value)
    u.emu_start(0x1802cc,RET,count=10000)
    if u.reg_read(A.UC_ARM_REG_PC)!=RET:raise RuntimeError('Selector did not return')
    return posts

def main():
    rows=[]
    for cls in (0,5):
        for kind in (0,1,2,3,4,5,6,14):
            for tier in range(5):rows.append(dict(weapon_class=cls,hit_kind=kind,tier=tier,posts=trace(cls,kind,tier)))
    (HERE/'reports/native-hit-selector.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    print('Traced',len(rows),'native class/kind/tier combinations; report written locally.')

if __name__=='__main__':main()
