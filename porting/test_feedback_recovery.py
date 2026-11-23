"""Local/remote combo recovery, executing real ARM actions and state ownership."""
import json
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,PLAYER
from build_module import MS,UPMOD,HERE,OUT,run,symbols


def compile_test(baseline=False):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    tag='feedback-recovery-baseline' if baseline else 'feedback-recovery'
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-DMS_GS_TREE',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD,'-I',OUT]
    if baseline:flags+=['-DMS_TEST_SOURCE="'+(HERE/'backups/before-feedback-1/module/ms_act.c').as_posix()+'"']
    obj=folder/(tag+'.o');cls=folder/(tag+'-class.o');elf=folder/(tag+'.elf')
    run('clang',*flags,'-c',HERE/'tests/feedback_harness.c','-o',obj)
    class_source=HERE/'backups/before-feedback-1/module/ms_class.c' if baseline else MS/'module/ms_class.c'
    run('clang',*flags,'-c',class_source,'-o',cls)
    exports=['test_feedback_begin','test_feedback_act','test_feedback_clock','test_feedback_pending',
             'test_feedback_stamp','test_feedback_stamp_read','test_feedback_swing_begin']
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,obj,cls)
    b=elf.read_bytes();return b,symbols(b)


class Recovery(Emulator):
    def __init__(self,b):super().__init__(b);self.neutrals={}
    def engine(self,u,address,size,arg):
        if address==BASE+0x280e4c:
            u.reg_write(A.UC_ARM_REG_R0,1)
        elif address==BASE+0x2b6e94:
            p=u.reg_read(A.UC_ARM_REG_R0)
            self.neutrals[p]=self.neutrals.get(p,0)+1
            self.w16(p+0x2506,1);self.w16(p+0x250a,0)
        else:return super().engine(u,address,size,arg)
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))


def main():
    import re
    policy={int(a):int(n) for a,n in re.findall(r'\bX\((\d+),\s*(\d+)\)',
                                             (MS/'module/ms_recovery.h').read_text())}
    old=compile_test(True);new=compile_test();checks={};cases=0
    for action,frames in policy.items():
        for dt in (50,100,200):
            ticks=(frames*100+dt-1)//dt
            outcomes=[]
            for binary in (old,new):
                e=Recovery(binary)
                players=[PLAYER+i*0x10000 for i in range(4)]
                for i,p in enumerate(players):e.call('test_feedback_begin',p,action,i==0,dt)
                for step in range(ticks+1):
                    for p in players:
                        if not e.neutrals.get(p):e.call('test_feedback_act',p)
                    if step<ticks:
                        checks[f'{action}_{dt}_{len(outcomes)}_no_early_release_{step}']=not e.neutrals
                outcomes.append([e.neutrals.get(p,0) for p in players])
            checks[f'{action}_{dt}_old_local_completes']=outcomes[0][0]==1
            checks[f'{action}_{dt}_old_remote_stalls']=outcomes[0][1:]==[0,0,0]
            checks[f'{action}_{dt}_all_four_hunters_complete']=outcomes[1]==[1,1,1,1]
            cases+=1
    report={'checks':checks,'all_passed':all(checks.values()),'finisher_timestep_cases':cases,
        'scope':'Real compiled action/finish handlers and four-entry state pool; local input clock simulated; animation end predicates supplied'}
    (HERE/'reports/feedback-recovery-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'failed':failed,'all_passed':report['all_passed']}))
    assert report['all_passed'],failed


if __name__=='__main__':main()
