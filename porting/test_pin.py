"""Execute owned monster restraint as real ARM, including cleanup paths."""
import json
import struct
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,HEAP,PLAYER,RET
from build_module import HERE,OUT,MS,UPMOD,run,symbols

MON,REC,INFO,PMGR,REGS=HEAP+0x100000,HEAP+0x120000,HEAP+0x80000,HEAP+0x40000,HEAP+0x70000
EXPORTS=['ms_monster_pin_begin','ms_monster_pin_end','ms_monster_pin_valid',
         'ms_local_pin_ai_c','ms_local_pin_action_c','ms_local_pin_update_c','test_pin_bind','test_pin_target']

def compile_test():
    obj,elf=OUT/'regression/pin.o',OUT/'regression/pin.elf'
    run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections','-DMS_RECOMP',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-I',MS/'module','-I',UPMOD,
        '-c',HERE/'tests/pin_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',EXPORTS[0],*[v for n in EXPORTS for v in ('-u',n)],'-o',elf,obj)
    data=elf.read_bytes();return data,symbols(data)

class PinEmulator(Emulator):
    def __init__(self,binary):
        super().__init__(binary);self.monster=MON;self.rates=[];self.actions=[];self.exits=[];self.flags=[]
        self.w32(BASE+0x1885b58,PMGR);self.w32(PMGR+0x1c,PLAYER)
        self.w32(PLAYER+0x13c4,INFO);self.uc.mem_write(INFO+0x4d4,b'\x05')
        self.w16(PLAYER+0x13d6,150);self.w16(PLAYER+0x2506,0x10);self.w16(PLAYER+0x250a,99)
        self.uc.mem_write(PLAYER+0x1054,b'\1');self.uc.mem_write(MON+0x1054,b'\1')
        self.w32(MON+0x1428,REC);self.w16(MON+0xb5f0,58);self.w16(REC+0x1b6,3)
        self.w32(REC+0x370,1000);self.w16(REC+0x54,12345)
        self.uc.mem_write(REC+0x40,struct.pack('<3f',100,200,300))
        self.uc.mem_write(REC+0x10,struct.pack('<3f',1,2,3));self.w32(REC+0x1c,0xfeedbeef)
        self.uc.mem_write(REC+0x20,struct.pack('<3f',4,5,6))
        self.wf(REC+0x5c,7);self.wf(REC+0x398,1.25)
        self.call('test_pin_bind',PLAYER,MON)

    def wf(self,a,v):self.uc.mem_write(a,struct.pack('<f',v))
    def rf(self,a):return struct.unpack('<f',self.uc.mem_read(a,4))[0]
    def engine(self,u,address,size,_):
        off=address-BASE;r0=u.reg_read(A.UC_ARM_REG_R0)
        if off==0x5ceb4:r0=self.monster if u.reg_read(A.UC_ARM_REG_R1)==0 else 0
        elif off==0x7bdd4:
            u.mem_write(REC+0x10,bytes(12));u.mem_write(REC+0x20,bytes(12))
        elif off==0x7e048:self.flags.append(u.reg_read(A.UC_ARM_REG_R1))
        elif off==0xb0870:
            rate=struct.unpack('<f',struct.pack('<I',u.reg_read(A.UC_ARM_REG_S0)))[0]
            self.rates.append(rate);self.wf(REC+0x398,rate)
        elif off==0x76154:self.actions.append(tuple(u.reg_read(r) for r in (A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3)))
        elif off==0x2831e0:self.exits.append(u.reg_read(A.UC_ARM_REG_R2))
        else:raise AssertionError(f'Unexpected engine call {off:x}')
        u.reg_write(A.UC_ARM_REG_R0,r0);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))
    def call(self,name,*args):
        u=self.uc;u.reg_write(A.UC_ARM_REG_SP,0x7100fff0);u.reg_write(A.UC_ARM_REG_LR,RET)
        for reg,v in zip((A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3),args):u.reg_write(reg,v)
        u.emu_start(self.symbols[name],RET,count=100000)
        assert u.reg_read(A.UC_ARM_REG_PC)==RET
        return u.reg_read(A.UC_ARM_REG_R0)
    def callback(self,name,*args):
        words=list(args)+[0]*(8-len(args));self.uc.mem_write(REGS,struct.pack('<8I',*words))
        result=self.call(name,REGS)
        return result,struct.unpack('<8I',self.uc.mem_read(REGS,32))
    def begin(self):assert self.call('ms_monster_pin_begin',PLAYER,MON)==1
    def tick(self):self.callback('ms_local_pin_update_c',0)

def main():
    binary=compile_test();checks={}
    e=PinEmulator(binary);e.begin();e.tick()
    handled,regs=e.callback('ms_local_pin_ai_c',MON)
    checks['only_held_ai_is_paused']=handled==1 and regs[0]==0 and e.callback('ms_local_pin_ai_c',MON+0x30000)[0]==0
    checks['motion_and_attacks_stopped']=e.rf(REC+0x398)==0 and e.flags==[0,1,0,1]
    e.uc.mem_write(REC+0x40,struct.pack('<3f',900,901,902));e.tick()
    checks['contact_position_is_held']=struct.unpack('<3f',e.uc.mem_read(REC+0x40,12))==(100.,200.,300.)
    e.w32(REC+0x370,900)
    checks['damage_is_not_undone']=e.call('ms_monster_pin_valid',PLAYER,MON)==1 and struct.unpack('<I',e.uc.mem_read(REC+0x370,4))[0]==900
    checks['ai_transition_is_blocked']=e.callback('ms_local_pin_action_c',MON,1,9,0)[0]==1
    e.call('ms_monster_pin_end',PLAYER)
    checks['release_restores_original_rate']=e.rf(REC+0x398)==1.25
    checks['release_restores_movement']=struct.unpack('<3f',e.uc.mem_read(REC+0x10,12))==(1.,2.,3.) and struct.unpack('<3f',e.uc.mem_read(REC+0x20,12))==(4.,5.,6.) and e.rf(REC+0x5c)==7
    checks['padding_and_flags_not_overwritten']=struct.unpack('<I',e.uc.mem_read(REC+0x1c,4))[0]==0xfeedbeef
    calls=len(e.rates);e.call('ms_monster_pin_end',PLAYER)
    checks['release_is_idempotent']=len(e.rates)==calls and e.callback('ms_local_pin_ai_c',MON)[0]==0
    e=PinEmulator(binary);e.begin();e.tick();e.callback('ms_local_pin_action_c',MON,10,23,5);e.call('ms_monster_pin_end',PLAYER)
    checks['status_reaction_is_deferred_then_replayed']=e.actions==[(10,23,5)]
    for name,mutate in [
        ('removed_monster',lambda e:setattr(e,'monster',0)),
        ('dead_monster',lambda e:e.w32(REC+0x370,0)),
        ('other_area',lambda e:e.uc.mem_write(PLAYER+0x1054,b'\2')),
        ('interrupted_hunter',lambda e:e.w16(PLAYER+0x2506,64)),
        ('dead_hunter',lambda e:e.w16(PLAYER+0x13d6,0)),
        ('removed_hunter',lambda e:e.w32(PMGR+0x1c,0)),
        ('reused_record',lambda e:e.w32(MON+0x1428,REC+0x4000)),
        ('reused_serial',lambda e:e.w16(REC+0x1b6,9))]:
        e=PinEmulator(binary);e.begin();e.tick();mutate(e);e.tick()
        checks[name+'_releases']=e.call('ms_monster_pin_valid',PLAYER,MON)==0 and e.callback('ms_local_pin_ai_c',MON)[0]==0
        if name in ('dead_monster','other_area','interrupted_hunter','dead_hunter','removed_hunter'):
            checks[name+'_restores_motion']=e.rf(REC+0x398)==1.25
        if name in ('removed_monster','other_area','dead_monster'):
            checks[name+'_ends_hunter_hold']=e.call('test_pin_target')==0 and e.exits==[100]
        if name in ('dead_hunter','interrupted_hunter'):
            checks[name+'_does_not_override_hunter_state']=not e.exits
        if name in ('reused_record','reused_serial','removed_monster'):
            checks[name+'_no_stale_restore']=len(e.rates)==1
    e=PinEmulator(binary);e.begin();e.tick();e.wf(REC+0x398,.75);e.call('ms_monster_pin_end',PLAYER)
    checks['external_speed_change_is_preserved']=e.rf(REC+0x398)==.75
    e=PinEmulator(binary);e.wf(REC+0x398,0);e.begin();e.tick();e.call('ms_monster_pin_end',PLAYER)
    checks['prior_pause_is_preserved']=e.rf(REC+0x398)==0
    e=PinEmulator(binary);e.begin();e.tick();h,_=e.callback('ms_local_pin_action_c',MON,11,0,0)
    checks['death_transition_is_allowed']=h==0 and e.rf(REC+0x398)==1.25
    report={'checks':checks,'all_passed':all(checks.values()),'adaptation':'Owned pause of current GU action/pose, not a Frontier monster animation port'}
    (HERE/'reports/pin-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));return int(not report['all_passed'])

if __name__=='__main__':raise SystemExit(main())
