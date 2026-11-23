"""Cancelled weapon damage: real ARM lifecycle and native active-hit predicates."""
import json
import struct
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,HEAP,PLAYER,STACK,RET
from build_module import MS,UPMOD,MOD,HERE,OUT,run,symbols

REGS=HEAP+0x290000
RESOURCE=HEAP+0x280000


def compile_test(baseline=False,wrapper=False):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    tag='damage-feedback-old' if baseline else 'damage-feedback'
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-DMS_GS_TREE',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD,'-I',OUT]
    if baseline:flags+=['-DMS_TEST_SOURCE="'+(HERE/'backups/before-feedback-2/module/ms_act.c').as_posix()+'"']
    source=HERE/'backups/before-feedback-2/module/ms_class.c' if baseline else MS/'module/ms_class.c'
    objects=[]
    for i,p in enumerate([HERE/'tests/damage_feedback_harness.c',source]+([] if baseline else [MOD/'feedback.c'])):
        obj=folder/(tag+f'-{i}.o');run('clang',*flags,'-c',p,'-o',obj);objects.append(obj)
    exports=['test_damage_begin','test_damage_arm','test_damage_tick','test_damage_pending','test_damage_after_update']
    if not baseline:exports+=['ms_local_attack_live_c']
    if wrapper:
        from test_hooks import builder
        import hook_codegen
        build=builder();build.main_ref=lambda off:hex(BASE+off)
        native=(HERE/'work/gu_main/mem.bin').read_bytes()
        asm=folder/(tag+'-hook.S');obj=folder/(tag+'-hook.o')
        asm.write_text('.text\n.arm\n'+hook_codegen.trampoline(build,native,'ms_local_attack_live',0x169328),encoding='utf-8')
        run('clang',*flags,'-c',asm,'-o',obj);objects.append(obj)
        exports+=['ms_local_attack_live_tramp']
    elf=folder/(tag+'.elf')
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,*objects)
    b=elf.read_bytes();return b,symbols(b)


class Damage(Emulator):
    def __init__(self,b):
        super().__init__(b);self.arms=[];self.wrapper=False
        self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.symbols['native_live']=BASE+0x169328
        self.symbols['native_timer']=BASE+0x16929c
        self.w32(BASE+0x1885b58,HEAP+0x270000)
        self.w32(HEAP+0x27001c,PLAYER)
        self.w32(PLAYER+0x13c4,HEAP+0x260000)
        self.uc.mem_write(HEAP+0x2604d4,b'\5')
    def engine(self,u,address,size,arg):
        off=address-BASE
        if off==0x169328 and self.wrapper:
            u.reg_write(A.UC_ARM_REG_PC,self.symbols['ms_local_attack_live_tramp']);return
        if off==0x169298:
            u.reg_write(A.UC_ARM_REG_R0,0);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        if 0x16929c<=off<0x16938c:return
        if off==0x2b7240:
            p=u.reg_read(A.UC_ARM_REG_R0);slot=u.reg_read(A.UC_ARM_REG_R1);hit=u.reg_read(A.UC_ARM_REG_R2)
            self.arms.append((p,slot,hit))
            a=p+0x3020+slot*0xb8
            self.w32(a+0xc,p);self.w32(a+0x70,p)
            self.w32(a+0x84,RESOURCE);self.w32(a+0x88,hit-1)
            self.uc.mem_write(a+5,b'\1')
            self.w32(a+0x5c,0);self.w32(a+0x60,0x42700000)
        elif off==0x53a058:u.reg_write(A.UC_ARM_REG_R0,0)
        elif off==0x281ef8:pass
        else:return super().engine(u,address,size,arg)
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
    def state(self,cat,no,p=PLAYER):self.w16(p+0x2506,cat);self.w16(p+0x250a,no)
    def active(self,slot,p=PLAYER):return self.call('native_live',p+0x3020+slot*0xb8)
    def arm_both(self,p=PLAYER):
        self.call('test_damage_arm',p,1);self.call('test_damage_arm',p,2)
    def hook(self,slot=0,caller=0x16b1b8,p=PLAYER):
        before=[p+0x3020+slot*0xb8,123,234,345,456,567,678,BASE+caller]
        self.uc.mem_write(REGS,struct.pack('<8I',*before))
        handled=self.call('ms_local_attack_live_c',REGS)
        after=struct.unpack('<8I',self.uc.mem_read(REGS,32))
        assert after[1:]==tuple(before[1:])
        return handled,after[0]
    def native_hook(self,slot=0,caller=0x16b1b8):
        u=self.uc
        u.reg_write(A.UC_ARM_REG_R0,PLAYER+0x3020+slot*0xb8)
        u.reg_write(A.UC_ARM_REG_SP,STACK-0x100);u.reg_write(A.UC_ARM_REG_LR,BASE+caller)
        u.emu_start(BASE+0x169328,BASE+caller,count=10000)
        assert u.reg_read(A.UC_ARM_REG_PC)==BASE+caller
        return u.reg_read(A.UC_ARM_REG_R0)


def exercise(binary):
    checks={}
    for dt in (25,50,100):
        for cat,no,name in ((1,6,'roll'),(64,30,'hit'),(2,0,'walk'),(1,2,'sheathe'),(16,11,'new_attack')):
            e=Damage(binary);e.call('test_damage_begin',PLAYER,159,1)
            e.arm_both();e.state(cat,no)
            before=len(e.arms)
            for _ in range(50):e.call('test_damage_tick',PLAYER,dt)
            key=f'{dt}_{name}'
            checks[key+'_no_queued_pulses']=len(e.arms)==before and not e.call('test_damage_pending',PLAYER)
            checks[key+'_native_hit_predicates_false']=e.active(0)==e.active(1)==0
        e=Damage(binary);e.call('test_damage_begin',PLAYER,159,1)
        for _ in range(50):e.call('test_damage_tick',PLAYER,dt)
        checks[f'{dt}_uncancelled_shock_keeps_four_pulses']=len(e.arms)==4
    e=Damage(binary);e.call('test_damage_begin',PLAYER,11,0);e.arm_both()
    e.w32(PLAYER+0x3020+0x84,RESOURCE+0x1000) # native action reused slot 0
    e.state(1,6);e.call('test_damage_tick',PLAYER,50)
    checks['replacement_native_attack_preserved']=e.active(0)==1
    checks['old_other_slot_stopped']=e.active(1)==0
    e=Damage(binary);e.call('test_damage_begin',PLAYER,159,1);e.arm_both()
    e.uc.mem_write(PLAYER+0x13cc,b'\0')
    e.state(64,30);e.call('test_damage_after_update',PLAYER)
    checks['nonlocal_after_update_cleans_interruptions']=e.active(0)==e.active(1)==0 and not e.call('test_damage_pending',PLAYER)
    # Native timer cannot revive a slot whose active byte and timers were cleared.
    for slot in range(2):
        attack=PLAYER+0x3020+slot*0xb8
        e.uc.reg_write(A.UC_ARM_REG_R4,attack);e.uc.reg_write(A.UC_ARM_REG_S0,0x3f800000)
        # These outlined blocks return through their caller's saved frame.
        e.uc.mem_write(STACK-0x100,struct.pack('<4I',attack,0,STACK-0x80,RET))
        e.call('native_timer',attack)
    checks['native_lifetime_update_does_not_reactivate_cancelled_slots']=e.active(0)==e.active(1)==0
    for local in (0,1):
        e=Damage(binary);e.call('test_damage_begin',PLAYER,159,1)
        e.uc.mem_write(PLAYER+0x13cc,bytes([local]))
        for _ in range(80):e.call('test_damage_after_update',PLAYER)
        checks['local_after_update_does_not_double_tick' if local else 'remote_after_update_runs_pending_tasks']=len(e.arms)==(0 if local else 4)
    return checks


def main():
    old=compile_test(True);new=compile_test();baseline=exercise(old);fixed=exercise(new)
    e=Damage(new);e.call('test_damage_begin',PLAYER,159,1);e.arm_both()
    checks={}
    for caller in (0x16ac74,0x16b1b8):
        for slot in range(2):
            e.state(16,159);checks[f'{caller:x}_{slot}_live_move_falls_through']=e.hook(slot,caller)[0]==0 and e.active(slot)==1
            e.state(64,30);checks[f'{caller:x}_{slot}_cancel_rejected_before_cleanup']=e.hook(slot,caller)==(1,0) and e.active(slot)==1
    checks['other_predicate_callers_untouched']=e.hook(0,0x123456)[0]==0
    e.uc.mem_write(HEAP+0x2604d4,b'\0')
    checks['other_weapon_class_untouched']=e.hook()[0]==0
    e=Damage(compile_test(wrapper=True));e.call('test_damage_begin',PLAYER,159,1);e.arm_both();e.wrapper=True
    for caller in (0x16ac74,0x16b1b8):
        for slot in (0,1):
            e.state(16,159);checks[f'wrapper_{caller:x}_{slot}_live_native_result']=e.native_hook(slot,caller)==1
            e.state(64,30);checks[f'wrapper_{caller:x}_{slot}_cancelled_native_result']=e.native_hook(slot,caller)==0
    checks['wrapper_other_caller_untouched']=e.native_hook(0,0x123456)==1
    e=Damage(new);other=PLAYER+0x10000
    e.call('test_damage_begin',other,11,0);e.arm_both(other)
    e.call('test_damage_begin',PLAYER,159,1);e.arm_both()
    e.state(64,30);e.call('test_damage_tick',PLAYER,50)
    checks['cancelling_one_hunter_preserves_other_hunters_slots']=e.active(0,other)==e.active(1,other)==1
    e=Damage(new);e.call('test_damage_begin',PLAYER,159,1);e.arm_both()
    e.w32(PLAYER+0x3020+0xc,other);e.state(64,30);e.call('test_damage_tick',PLAYER,50)
    checks['native_slot_with_changed_owner_is_not_cleared']=e.active(0)==1 and e.active(1)==0
    e=Damage(new);e.call('test_damage_begin',PLAYER,159,1);e.arm_both()
    e.w32(HEAP+0x27001c,0)
    checks['departed_owner_cannot_leave_collision_hits_live']=e.hook()==(1,0)
    report={'baseline':baseline,'fixed':fixed,'collision_gate':checks,
        'all_passed':all(fixed.values()) and all(checks.values()),
        'baseline_defect_reproduced':not all(baseline.values()),
        'scope':'Actual ARM tick/shock/arm/after-update and real native 169328 active predicate / 16929c timer; native arming and resource services supplied by bounded fixtures'}
    (HERE/'reports/damage-feedback-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in fixed.items() if not v]+[k for k,v in checks.items() if not v]
    print(json.dumps({'baseline_failures':sum(not v for v in baseline.values()),'checks':len(fixed)+len(checks),'failed':failed,'all_passed':report['all_passed']}))
    assert report['baseline_defect_reproduced'] and report['all_passed'],failed


if __name__=='__main__':main()
