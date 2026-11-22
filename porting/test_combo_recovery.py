"""Real ARM finisher tails and native command gates, including the old bypass."""
import json,struct,sys
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,PLAYER
from build_module import HERE,OUT,MS,UPMOD,run,symbols
from test_cancel_windows import NativeGU,compile_test as compile_windows


def compile_finish(legacy=False):
    tag='recovery-tail-old' if legacy else 'recovery-tail'
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    obj,elf=folder/(tag+'.o'),folder/(tag+'.elf')
    exports=['test_recovery_begin','test_recovery_clock','test_recovery_finish']
    if not legacy:exports+=['test_recovery_tick','test_recovery_pending']
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD]
    if legacy:flags+=['-DMS_TEST_OLD_RECOVERY','-DMS_TEST_SOURCE="'+(HERE/'backups/before-recovery-1/ms_act.c').as_posix()+'"']
    run('clang',*flags,'-c',HERE/'tests/recovery_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,obj)
    b=elf.read_bytes();return b,symbols(b)


class Finish(Emulator):
    def __init__(self,b):super().__init__(b);self.neutral=0
    def engine(self,u,address,size,arg):
        if address==BASE+0x2b6e94:
            self.neutral+=1;u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        return super().engine(u,address,size,arg)


def main():
    from build_cancel_windows import generate
    status=generate()
    import msbuild
    policy=msbuild.RECOVERY_FRAMES
    checks={};old=compile_finish(True);new=compile_finish();gates=compile_windows()
    for action,frames in policy.items():
        e=Finish(old);e.call('test_recovery_begin',PLAYER,action);e.call('test_recovery_finish',PLAYER)
        checks[f'{action}_old_natural_end_had_no_extra_recovery']=e.neutral==1
        e=Finish(new);e.call('test_recovery_begin',PLAYER,action);e.call('test_recovery_finish',PLAYER)
        checks[f'{action}_cannot_return_to_idle_immediately']=e.neutral==0
        e.call('test_recovery_clock',frames*100-1);e.call('test_recovery_finish',PLAYER)
        checks[f'{action}_remains_committed_before_boundary']=e.neutral==0
        e.call('test_recovery_clock',frames*100);e.call('test_recovery_finish',PLAYER)
        checks[f'{action}_releases_at_exact_boundary']=e.neutral==1
    for dt100,updates in ((50,36),(100,18),(200,9)):
        e=Finish(new);e.call('test_recovery_begin',PLAYER,10);e.call('test_recovery_finish',PLAYER)
        for _ in range(updates-1):e.call('test_recovery_tick',PLAYER,dt100,16,10)
        e.call('test_recovery_finish',PLAYER)
        checks[f'dt_{dt100}_does_not_release_early']=e.neutral==0
        e.call('test_recovery_tick',PLAYER,dt100,16,10);e.call('test_recovery_finish',PLAYER)
        checks[f'dt_{dt100}_same_game_time_boundary']=e.neutral==1
    for st,no,label in ((64,1,'hit_reaction'),(1,0,'quest_or_area_transition'),(16,3,'different_attack')):
        e=Finish(new);e.call('test_recovery_begin',PLAYER,10);e.call('test_recovery_finish',PLAYER)
        e.call('test_recovery_tick',PLAYER,100,st,no)
        checks[label+'_clears_stale_recovery']=e.call('test_recovery_pending')==0
    # Use all real native command rows of every selected final animation step.
    # Each row is advanced through its original open/close predicates; no timing
    # tables or game bytes are copied to the report.
    tested=0
    for table in msbuild.WINDOW_TABLES:
        delay=table.get('recovery',0)
        if not delay:continue
        for row,ci in enumerate(table['rows']):
            c=table['cancels'][ci];start=c['go'][0]
            if start[1]==2:continue
            e=NativeGU(gates);a=table['action'];step=table['step']+1
            e.call('ms_cancel_windows_reset',PLAYER)
            f=start[3] if start[1]!=1 else 0
            e.clock(a,step,start[4],f);e.call('fixture_clock',0)
            # A prior-step open is already eligible in the final step.
            checks[f'{a}_{row}_source_eligibility_delayed']=e.query(row,2)==(1,0)
            e.call('fixture_clock',delay*100-1)
            checks[f'{a}_{row}_no_early_attack_or_utility']=e.query(row,2)==(1,0)
            e.call('fixture_clock',delay*100)
            checks[f'{a}_{row}_opens_after_delay']=e.query(row,2)==(1,1)
            tested+=1
    checks['ordinary_combo_links_not_selected']=all(n not in policy for n in (0,1,3,6,7,9,18,20,23,24,27,32,33,34))
    report={'checks':checks,'all_passed':all(checks.values()),'finisher_count':len(policy),
        'native_transition_rows_checked':tested,'added_frames_at_60hz':policy,
        'scope':'Compiled ARM natural-end functions, old immediate-idle regression, actual scoped native transition gates'}
    (HERE/'reports/combo-recovery-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'checks':len(checks),'failed':failed,'all_passed':report['all_passed'],'native_rows':tested}))
    assert report['all_passed'],failed


if __name__=='__main__':main()
