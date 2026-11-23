"""Compiled full input translator: preserve sheathed sprint evades and MS binds."""
import json
import struct
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,HEAP,PLAYER
from build_module import HERE,MS,UPMOD,OUT,run,symbols


def compile_test(baseline=False):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    tag='sprint-roll-old' if baseline else 'sprint-roll'
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-DMS_GS_TREE',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD,'-I',OUT]
    if baseline:flags+=['-DMS_TEST_SOURCE="'+(HERE/'backups/before-sprint-roll-1/module/ms_act.c').as_posix()+'"']
    objects=[]
    for i,p in enumerate((HERE/'tests/sprint_roll_harness.c',MS/'module/ms_class.c')):
        obj=folder/(tag+f'-{i}.o');run('clang',*flags,'-c',p,'-o',obj);objects.append(obj)
    exports=['test_sprint_begin','test_sprint_input']
    elf=folder/(tag+'.elf')
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,*objects)
    b=elf.read_bytes();return b,symbols(b)


class Sprint(Emulator):
    def __init__(self,b):
        super().__init__(b)
        self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.w32(BASE+0x1838d88,BASE+0x1897f78)
        self.w32(BASE+0x1897f78,HEAP+0x200000)
    def engine(self,u,address,size,arg):
        off=address-BASE
        if 0x65f93c<=off<0x65f964 or 0x285e54<=off<0x285e78:return
        if off in (0x27e770,):
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        if off==0x53a058:
            u.reg_write(A.UC_ARM_REG_R0,0)
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        return super().engine(u,address,size,arg)
    def input(self,drawn,option,button,gauge,mode):
        self.call('test_sprint_begin',PLAYER,drawn,gauge,mode)
        self.uc.mem_write(HEAP+0x20446e,bytes([option]))
        r=0x800 if option else 0x40
        self.w16(PLAYER+0x13f4,r|button);self.w16(PLAYER+0x13f8,button)
        self.w32(PLAYER+0x1414,0xa5ffffff);self.w32(PLAYER+0x1418,0x5affffff)
        self.call('test_sprint_input',PLAYER)
        return struct.unpack('<2I',self.uc.mem_read(PLAYER+0x1414,8)),bytes(self.uc.mem_read(PLAYER+0x1424,16))


def exercise(old,new):
    checks={};baseline_failures=0
    for option in (0,1):
        for button in (0x80,0x10,0):
            for gauge in (0,1999,2000,10000):
                for mode in (0,1):
                    a,b=Sprint(old),Sprint(new)
                    prior=a.input(0,option,button,gauge,mode)
                    fixed=b.input(0,option,button,gauge,mode)
                    name=f'{option}_{button}_{gauge}_{mode}'
                    expected=(0xa5ffffff,0x5affffff)
                    baseline_failures+=prior[0]!=expected
                    checks[name+'_sheathed_native_inputs_preserved']=fixed[0]==expected
                    checks[name+'_class_input_ids_preserved']=fixed[1]==prior[1]
                    a,b=Sprint(old),Sprint(new)
                    checks[name+'_drawn_modifier_behavior_unchanged']=a.input(1,option,button,gauge,mode)==b.input(1,option,button,gauge,mode)
    return checks,baseline_failures


def main():
    checks,failures=exercise(compile_test(True),compile_test())
    report={'checks':checks,'all_passed':all(checks.values()),'baseline_failing_cases':failures,
        'scope':'Full compiled ms_input and native R-role getter; synthetic hunter/common-ID bits supplied before class translation'}
    (HERE/'reports/sprint-roll-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'baseline_failing_cases':failures,'failed':failed,'all_passed':report['all_passed']}))
    assert report['all_passed'] and failures,failed


if __name__=='__main__':main()
