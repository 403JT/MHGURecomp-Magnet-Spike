"""Bounded Frontier draw-path probe; outputs semantic action requests only."""
import json
import struct
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EAX,UC_X86_REG_EIP
from dis_audio import image
from prepare_frontier import HERE


def main():
    data,base,_=image('mhf')
    actor,stack,ret=0x20000000,0x30010000,0x40000000
    out=[]
    for entry in (0x1032d110,0x1032d210):
        for picked in (2,4,9):
            for moving in (0,1):
                u=Uc(UC_ARCH_X86,UC_MODE_32)
                u.mem_map(base,(len(data)+4095)&~4095);u.mem_write(base,bytes(data))
                u.mem_map(actor,0x10000);u.mem_map(stack-0x10000,0x10000);u.mem_map(ret,4096)
                sp=stack-0x100;u.mem_write(sp,struct.pack('<2I',ret,actor));u.reg_write(UC_X86_REG_ESP,sp)
                calls=[];actions=[]
                def code(u,address,size,arg):
                    if entry<=address<(0x1032d1d8 if entry==0x1032d110 else 0x1032d2a8):return
                    sp=u.reg_read(UC_X86_REG_ESP)
                    args=struct.unpack('<6I',u.mem_read(sp+4,24))
                    if address==0x10a80a00:
                        actions.append({'category':args[1],'action':args[2],'parameter':args[3]})
                        u.emu_stop();return
                    calls.append(hex(address))
                    value={0x1032ce50:actor+0x1000,0x10337390:picked,0x109a9d80:moving,
                           0x109a3c40:1}.get(address,0)
                    back=struct.unpack('<I',u.mem_read(sp,4))[0]
                    u.reg_write(UC_X86_REG_ESP,sp+4);u.reg_write(UC_X86_REG_EAX,value);u.reg_write(UC_X86_REG_EIP,back)
                u.hook_add(UC_HOOK_CODE,code,begin=base,end=base+len(data)-1)
                try:u.emu_start(entry,ret,count=20000);error=None
                except Exception as exc:error=type(exc).__name__
                out.append({'entry':hex(entry),'picked_input':picked,'moving':moving,'actions':actions,
                            'calls':list(dict.fromkeys(calls))[:10],'error':error})
    report={'source':'Frontier HD DLL, read-only; shared picker result supplied by fixture','cases':out}
    (HERE/'work/frontier-draw-paths.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
