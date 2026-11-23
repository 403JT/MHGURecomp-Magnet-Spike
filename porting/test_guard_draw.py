"""Compiled routing/initialization regression for Frontier's sheathed guard draw."""
import json
import struct
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,PLAYER,HEAP
from build_module import HERE,MS,UPMOD,OUT,run,symbols


def compile_test(kind,old):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    name=f'{kind}-'+('old' if old else 'fixed')
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-DMS_GS_TREE',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD,'-I',OUT]
    before=HERE/'backups/before-draw-chord-1/module'
    if old:flags+=['-D'+('MS_TEST_CLASS_SOURCE' if kind=='draw-route' else 'MS_TEST_SOURCE')+'="'+
                    (before/('ms_class.c' if kind=='draw-route' else 'ms_act.c')).as_posix()+'"']
    sources=[HERE/'tests'/('draw_route_harness.c' if kind=='draw-route' else 'guard_draw_harness.c')]
    if kind!='draw-route':sources.append(MS/'module/ms_class.c')
    objects=[]
    for i,source in enumerate(sources):
        obj=folder/(name+f'-{i}.o');run('clang',*flags,'-c',source,'-o',obj);objects.append(obj)
    exports=['test_draw_route'] if kind=='draw-route' else ['test_guard_draw_start','test_guard_draw_mode']
    elf=folder/(name+'.elf')
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,*objects)
    b=elf.read_bytes();return b,symbols(b)


class Guard(Emulator):
    def __init__(self,b):super().__init__(b);self.draw_flags=[]
    def engine(self,u,address,size,arg):
        off=address-BASE
        if off==0x2a264c:self.draw_flags.append(u.reg_read(A.UC_ARM_REG_R1))
        elif off in (0x282fd8,0x282a48):pass
        else:return super().engine(u,address,size,arg)
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))


def main():
    checks={};old=compile_test('draw-route',True);fixed=compile_test('draw-route',False)
    for category in (1,2,4,64):
        for index in range(10):
            rows=[]
            for binary in (old,fixed):
                e=Emulator(binary);e.w16(PLAYER+0x2506,category)
                e.call('test_draw_route',PLAYER,index,HEAP+0x300000)
                rows.append(struct.unpack('<3H',e.uc.mem_read(HEAP+0x300000,6)))
            guarded=index in (2,4) and category!=4
            checks[f'{category}_{index}_route']=rows[1]==((16,112,0) if guarded else rows[0])
            if guarded:checks[f'{category}_{index}_old_GS_guard_reproduced']=rows[0]==(32,0,0)
    for old in (True,False):
        binary=compile_test('guard-draw',old)
        for action in (112,14,12,78,79):
            for drawn in (0,1):
                e=Guard(binary);e.call('test_guard_draw_start',PLAYER,action,drawn)
                expected=action in (78,79) or (not old and action==112 and not drawn)
                checks[f'{old}_{action}_{drawn}_draw_flag']=e.draw_flags==([1] if expected else [])
                if action==112:checks[f'{old}_{drawn}_Impact_mode']=e.call('test_guard_draw_mode',PLAYER)==1
    report={'checks':checks,'all_passed':all(checks.values()),'scope':'Real compiled indirect routes and action_start; native flag calls intercepted'}
    (HERE/'reports/guard-draw-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'checks':len(checks),'failed':[n for n,v in checks.items() if not v],'all_passed':report['all_passed']}))
    assert report['all_passed']


if __name__=='__main__':main()
