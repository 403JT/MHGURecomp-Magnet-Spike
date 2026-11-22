"""Exercise real ARM flight events and pin QTE, including observed failures."""
import json,struct,math
from unicorn import arm_const as A
from test_runtime import Emulator,BASE,HEAP,PLAYER
from build_module import HERE,OUT,MS,UPMOD,run,symbols

EXPORTS=['test_flight_begin','test_flight_step','test_qte_begin','test_qte_step','test_qte_points','test_pin_hit']
MON,REC=HEAP+0x300000,HEAP+0x320000
def compile_test(legacy=False):
    tag='moveset-legacy' if legacy else 'moveset'
    obj,elf=OUT/'regression'/f'{tag}.o',OUT/'regression'/f'{tag}.elf'
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
           '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
           '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP',
           '-I',MS/'module','-I',MS/'gen','-I',UPMOD]
    if legacy:flags+=['-DMS_TEST_SOURCE="'+(HERE/'reports/baseline-ms_act.c').as_posix()+'"']
    run('clang',*flags,'-c',HERE/'tests/moveset_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',EXPORTS[0],*[v for n in EXPORTS for v in ('-u',n)],'-o',elf,obj)
    data=elf.read_bytes();return data,symbols(data)

class MovesetEmulator(Emulator):
    def __init__(self,binary):
        super().__init__(binary);self.monster=MON;self.actions=[];self.contacts=0
        self.w32(MON+0x1428,REC);self.w32(REC+0x370,1000)
        self.w32(PLAYER,HEAP+0x200000);self.w32(HEAP+0x200300,BASE+0x282a48)
        for off in (0xb5f9,0x7652):self.uc.mem_write(MON+off,b'\1')
        self.uc.mem_write(REC+0x1a0,b'\1')
        self.uc.mem_write(MON+0x1054,b'\1');self.uc.mem_write(PLAYER+0x1054,b'\1')
    def wf(self,a,v):self.uc.mem_write(a,struct.pack('<f',v))
    def rf(self,a):return struct.unpack('<f',self.uc.mem_read(a,4))[0]
    def engine(self,u,address,size,_):
        off=address-BASE
        if off==0x2a84d8:
            self.contacts+=1;r=int(self.rf(PLAYER+0x44)<=self.rf(PLAYER+0x10f0))
            if r:self.wf(PLAYER+0x44,self.rf(PLAYER+0x10f0))
            u.reg_write(A.UC_ARM_REG_R0,r)
        elif off==0x2831e0:self.actions.append(u.reg_read(A.UC_ARM_REG_R2))
        elif off in (0x13efde8,0x13efdf4):
            x=struct.unpack('<f',struct.pack('<I',u.reg_read(A.UC_ARM_REG_S0)))[0]
            value=(math.sin if off==0x13efde8 else math.cos)(x)
            u.reg_write(A.UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',value))[0])
        elif off in (0x282a48,0x2a6760):pass
        else:return super().engine(u,address,size,_)
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))

def suite(binary):
    checks={}
    for no,launch_frame in ((97,6),(94,22)):
        e=MovesetEmulator(binary);e.call('test_flight_begin',PLAYER,no)
        early=False;peak=0;land=None
        for f in range(160):
            landed=e.call('test_flight_step',PLAYER)
            peak=max(peak,e.rf(PLAYER+0x44))
            if landed and f<=launch_frame+1:early=True;break
            if landed:land=f;break
        checks[f'action_{no}_waits_for_launch']=not early
        checks[f'action_{no}_leaves_ground_and_lands']=peak>30 and land is not None
    e=MovesetEmulator(binary);e.call('test_qte_begin',PLAYER,MON,0)
    # Wait 30 ticks, then rapid presses must still respect a fresh cooldown.
    for _ in range(60):e.call('test_qte_step',PLAYER)
    e.w16(PLAYER+0x13f8,0x20)
    for _ in range(4):e.call('test_qte_step',PLAYER)
    checks['qte_cooldown_does_not_accumulate_negative_credit']=e.call('test_qte_points')==4
    e=MovesetEmulator(binary)
    e.uc.mem_write(MON+0xb5f9,b'\0');e.uc.mem_write(REC+0x1a0,b'\0')
    checks['confirmed_pin_hit_survives_transient_hurt_gate']=e.call('test_pin_hit',PLAYER,MON)==1
    e.call('test_qte_begin',PLAYER,MON,0);e.call('test_qte_step',PLAYER)
    checks['held_pin_survives_transient_hurt_gate']=not e.actions
    for impact,expected in ((0,105),(1,157)):
        e=MovesetEmulator(binary);e.call('test_qte_begin',PLAYER,MON,impact)
        for n in range(18):
            e.w16(PLAYER+0x13f8,0x20 if n%2==0 else 0x100)
            e.call('test_qte_step',PLAYER);e.w16(PLAYER+0x13f8,0)
            for _ in range(7):e.call('test_qte_step',PLAYER)
        checks[f'qte_success_selects_{expected}']=expected in e.actions
        e=MovesetEmulator(binary);e.call('test_qte_begin',PLAYER,MON,impact)
        for _ in range(180):e.call('test_qte_step',PLAYER)
        checks[f'qte_timeout_selects_{156 if impact else 100}']=(156 if impact else 100) in e.actions
    return checks

def main():
    legacy=suite(compile_test(True));fixed=suite(compile_test())
    for k in ('action_94_waits_for_launch','action_97_waits_for_launch','qte_cooldown_does_not_accumulate_negative_credit',
              'confirmed_pin_hit_survives_transient_hurt_gate','held_pin_survives_transient_hurt_gate'):
        assert not legacy[k],(k,legacy)
    assert all(fixed.values()),fixed
    report={'legacy':legacy,'fixed':fixed}
    (HERE/'reports/moveset-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
