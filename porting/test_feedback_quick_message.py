"""Execute the scoped hook with GU's real quick-message/R button getters."""
import json
import struct
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,HEAP,PLAYER,STACK
from test_hooks import builder
from build_module import HERE,OUT,UPMOD,MS,MOD,run,symbols
import hook_codegen

SITE=0x65f920
CALLER=0x576a60
OPTIONS,NETWORK,MANAGER,INFO=HEAP+0x50000,HEAP+0x70000,HEAP+0x80000,HEAP+0x90000


def compile_test():
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    asm,obj,srcobj,elf=[folder/('feedback-quick-message'+s) for s in ('.S','.o','-source.o','.elf')]
    build=builder();build.main_ref=lambda off:hex(BASE+off)
    data=(HERE/'work/gu_main/mem.bin').read_bytes()
    assert build.branch_into(data,SITE) is None
    asm.write_text('.text\n.arm\n'+hook_codegen.trampoline(build,data,'ms_local_quick_message',SITE),encoding='utf-8')
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP',
        '-I',MS/'module','-I',UPMOD,'-I',MOD]
    run('clang',*flags,'-c',asm,'-o',obj)
    run('clang',*flags,'-c',HERE/'tests/quick_message_harness.c','-o',srcobj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e','ms_local_quick_message_tramp','-u','test_quick_owner','-o',elf,obj,srcobj)
    b=elf.read_bytes();return b,symbols(b)


class QuickMessage(Emulator):
    def __init__(self,b):
        super().__init__(b)
        self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.enabled=False;self.online=1
        self.w32(BASE+0x1838d88,BASE+0x1897f78)
        self.w32(BASE+0x1897f78,OPTIONS)
        self.w32(BASE+0x18843f0,NETWORK)
        self.w32(BASE+0x1885b58,MANAGER)
        self.w32(MANAGER+0x1c,PLAYER)
        self.w32(PLAYER+0x13c4,INFO)
        self.w32(PLAYER+0x13cc,1)
        self.w32(PLAYER+0x13f4,0x840)
        self.w32(PLAYER+0x13f8,0x800)
        self.uc.mem_write(INFO+0x4d4,b'\5')
        self.call('test_quick_owner',PLAYER,1)

    def engine(self,u,address,size,arg):
        off=address-BASE
        if off==SITE and self.enabled:
            u.reg_write(A.UC_ARM_REG_PC,self.symbols['ms_local_quick_message_tramp']);return
        if 0x65f914<=off<0x65f964:return
        if off==0x227ba8:
            u.reg_write(A.UC_ARM_REG_R0,self.online)
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        return super().engine(u,address,size,arg)

    def native(self,offset,caller=CALLER):
        u=self.uc
        u.reg_write(A.UC_ARM_REG_SP,STACK-0x100)
        u.reg_write(A.UC_ARM_REG_LR,BASE+caller)
        u.emu_start(BASE+offset,BASE+caller,count=10000)
        assert u.reg_read(A.UC_ARM_REG_PC)==BASE+caller
        return u.reg_read(A.UC_ARM_REG_R0)


def main():
    binary=compile_test();checks={};cases=0
    for option in (0,1):
        for cls in range(16):
            for online in (0,1):
                e=QuickMessage(binary);e.online=online
                e.uc.mem_write(OPTIONS+0x446e,bytes([option]))
                e.uc.mem_write(INFO+0x4d4,bytes([cls]))
                before=e.native(0x65f914)
                scope_before=e.native(0x65f93c)
                input_before=bytes(e.uc.mem_read(PLAYER+0x13f4,12))
                assert before!=0 and scope_before!=0
                e.enabled=True
                after=e.native(0x65f914)
                checks[f'{option}_{cls}_{online}_scoped_result']=after==(0 if cls==5 and online else before)
                checks[f'{option}_{cls}_{online}_other_callers_unchanged']=e.native(0x65f914,0x123456)==before
                checks[f'{option}_{cls}_{online}_weapon_modifier_unchanged']=e.native(0x65f93c)==scope_before
                checks[f'{option}_{cls}_{online}_held_input_unchanged']=bytes(e.uc.mem_read(PLAYER+0x13f4,12))==input_before
                cases+=1
    for missing in ('owner','local','info','manager','network'):
        e=QuickMessage(binary);e.enabled=True
        if missing=='owner':e.call('test_quick_owner',PLAYER,0)
        if missing=='local':e.w32(PLAYER+0x13cc,0)
        if missing=='info':e.w32(PLAYER+0x13c4,0)
        if missing=='manager':e.w32(BASE+0x1885b58,0)
        if missing=='network':e.w32(BASE+0x18843f0,0)
        checks['missing_'+missing+'_falls_through']=e.native(0x65f914)!=0
    report={'checks':checks,'all_passed':all(checks.values()),'class_option_online_cases':cases,
        'scope':'Actual native button getters plus real injected hook wrapper/callback; synthetic roster and online predicate'}
    (HERE/'reports/feedback-quick-message-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'failed':failed,'all_passed':report['all_passed']}))
    assert report['all_passed'],failed


if __name__=='__main__':main()
