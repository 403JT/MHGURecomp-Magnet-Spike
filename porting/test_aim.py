"""Real ARM aim update plus the original GU input reader; synthetic controls."""
import json, struct, math
from unicorn import arm_const as A
from test_runtime import Emulator, BASE, HEAP, PLAYER, VECTOR
from build_module import MS, UPMOD, OUT, HERE, run, symbols

def compile_test(legacy=False):
    folder=OUT/'aim-regression';folder.mkdir(exist_ok=True)
    obj=folder/('legacy.o' if legacy else 'fixed.o');elf=obj.with_suffix('.elf')
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD]
    if legacy:flags+=['-DMS_TEST_LEGACY','-DMS_TEST_SOURCE="'+(HERE/'reports/baseline-ms_act.c').as_posix()+'"']
    run('clang',*flags,'-c',HERE/'tests/aim_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e','test_aim',*(['-u','test_aim_frame','-u','test_aim_callback','-u','test_aim_callback_view'] if not legacy else []),'-o',elf,obj)
    data=elf.read_bytes();return data,symbols(data)

class AimEmulator(Emulator):
    def __init__(self,binary):
        super().__init__(binary)
        self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.options=HEAP+0x300000;self.option_ptr=HEAP+0x380000
        self.w32(self.option_ptr,self.options)
        self.uc.mem_write(self.options+0x446c,b'\x02')
        self.w32(BASE+0x188ca48,0)  # Extra GU inversion option is disabled in this fixture.
        self.w32(PLAYER,HEAP+0x390000)
        self.w32(HEAP+0x390000+0x1b0,BASE+0x27d5c0)
        self.uc.mem_write(PLAYER+0x1c,struct.pack('<f',1.0))
    def engine(self,u,address,size,_):
        pc=address-BASE
        if pc==0x27d5e8:u.reg_write(A.UC_ARM_REG_R0,self.option_ptr)
        if 0x27d5c4<=pc<=0x27db6c:return
        if 0x2a714c<=pc<=0x2a73fc:return
        if pc in (0x13efde8,0x13efdf4):
            x=struct.unpack('<f',struct.pack('<I',u.reg_read(A.UC_ARM_REG_S0)))[0]
            y=(math.sin if pc==0x13efde8 else math.cos)(x)
            u.reg_write(A.UC_ARM_REG_S0,struct.unpack('<I',struct.pack('<f',y))[0])
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        if pc==0x27d5c0:
            u.reg_write(A.UC_ARM_REG_R0,0)
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        raise AssertionError(f'Unexpected aim dependency {pc:x}')
    def aim(self,left=False,right=0,mag=100,pitch=0,yaw=1000,invert=0):
        self.uc.mem_write(PLAYER+0x140c,struct.pack('<4h',0,0,100 if left else 0,mag if right else 0))
        self.w32(PLAYER+0x13fc,right)
        opt=HEAP+0x3a0000
        self.w32(BASE+0x188ca48,opt if invert else 0)
        self.uc.mem_write(opt+0x66,bytes([invert]))
        self.uc.mem_write(VECTOR,struct.pack('<2f',yaw,pitch))
        self.call('test_aim',PLAYER,VECTOR)
        return struct.unpack('<2f',self.uc.mem_read(VECTOR,8))

def main():
    old=AimEmulator(compile_test(True));e=AimEmulator(compile_test())
    assert old.aim(left=True)!=(1000,0),'Old movement-stick bug did not reproduce'
    checks={
        'neutral_keeps_aim':e.aim()==(1000,0),
        'movement_stick_does_not_move_aim':e.aim(left=True)==(1000,0),
        'right_stick_up':e.aim(right=0x100000)==(1000,176),
        'right_stick_down':e.aim(right=0x200000)==(1000,-176),
        'right_stick_left':e.aim(right=0x400000)==(1288,0),
        'right_stick_right':e.aim(right=0x800000)==(712,0),
        'both_sticks_only_camera_input':e.aim(left=True,right=0x200000)==(1000,-176),
        'right_stick_dead_zone':e.aim(right=0x100000,mag=49)==(1000,0),
        'pitch_upper_clamp':e.aim(right=0x100000,pitch=3300)[1]==3356,
        'pitch_lower_clamp':e.aim(right=0x200000,pitch=-3300)[1]==-3356,
        'yaw_wrap':e.aim(right=0x800000,yaw=0)[0]==65248,
        'vertical_invert':e.aim(right=0x100000,invert=1)[1]==-176,
        'horizontal_invert':e.aim(right=0x400000,invert=2)[0]==712,
    }
    e.uc.mem_write(PLAYER+0x40,struct.pack('<3f',123,-42,876))
    sentinel=struct.pack('<16f',*([float('nan')]*16))
    e.symbols['native_gs_frame']=BASE+0x2a714c
    e.uc.mem_write(VECTOR,sentinel);e.call('native_gs_frame',PLAYER,VECTOR,0)
    checks['native_GS_does_not_initialise_aim_matrix']=all(math.isnan(v) for v in struct.unpack('<16f',e.uc.mem_read(VECTOR,64)))
    e.symbols['native_common_frame']=BASE+0x2a72e0
    matches=True
    for yaw in (0,8192,16384,32768,49152,65535):
        for pitch in (0,1024,-1024,3356,-3356):
            e.w32(PLAYER+0xfec,yaw);e.w16(PLAYER+0x2714,pitch&65535)
            e.uc.mem_write(VECTOR,sentinel);e.call('test_aim_frame',PLAYER,VECTOR)
            actual=struct.unpack('<16f',e.uc.mem_read(VECTOR,64))
            e.call('native_common_frame',PLAYER,VECTOR)
            expected=struct.unpack('<16f',e.uc.mem_read(VECTOR,64))
            matches &= all(math.isfinite(a) and abs(a-b)<2e-5 for a,b in zip(actual,expected))
    checks['all_16_matrix_fields_match_native_30_angle_cases']=matches
    e.uc.mem_write(VECTOR,sentinel);e.call('test_aim_callback',PLAYER,VECTOR)
    checks['actual_slot_260_initialises_all_matrix_fields']=all(math.isfinite(v) for v in struct.unpack('<16f',e.uc.mem_read(VECTOR,64)))
    e.w32(BASE+0x2126504,0);e.w32(PLAYER+0xfec,1000)
    e.call('test_aim_callback_view',PLAYER,VECTOR,32768,1024)
    actual=struct.unpack('<16f',e.uc.mem_read(VECTOR,64))
    unchanged=int.from_bytes(e.uc.mem_read(PLAYER+0xfec,4),'little')==1000
    e.w32(PLAYER+0xfec,32768);e.w16(PLAYER+0x2714,1024)
    e.call('native_common_frame',PLAYER,VECTOR)
    expected=struct.unpack('<16f',e.uc.mem_read(VECTOR,64))
    checks['active_aim_frame_follows_look_without_turning_hunter']=unchanged and all(abs(a-b)<2e-5 for a,b in zip(actual,expected))
    report={'checks':checks,'all_passed':all(checks.values()),'legacy_movement_drift_reproduced':True,
        'scope':'Compiled weapon aim update and original GU reader; synthetic player/options/input'}
    (HERE/'reports/aim-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
