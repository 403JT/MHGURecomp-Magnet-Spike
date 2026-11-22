"""Execute the live-hit KO update as ARM; guard adjacent native hit fields."""
import json,struct
from test_runtime import Emulator,PLAYER
from build_module import HERE,OUT,MS,UPMOD,run,symbols
from unicorn import arm_const as A
from test_runtime import BASE

class HitStatsEmulator(Emulator):
    def __init__(self,b):super().__init__(b);self.skill=0;self.blocked=False
    def engine(self,u,pc,size,_):
        off=pc-BASE
        if off==0x27b918:r=int(self.blocked)
        elif off==0x2864c4:r=int(u.reg_read(A.UC_ARM_REG_R1)==self.skill)
        elif off==0x2864d4:r=int(self.skill==0x28)
        else:return super().engine(u,pc,size,_)
        u.reg_write(A.UC_ARM_REG_R0,r);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))

def main():
    obj,elf=OUT/'regression/hitstats.o',OUT/'regression/hitstats.elf'
    run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections','-DMS_RECOMP',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-I',MS/'module','-I',UPMOD,
        '-I',HERE/'tests','-c',HERE/'tests/hitstats_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e','ms_apply_hit_stats','-o',elf,obj)
    b=elf.read_bytes();e=HitStatsEmulator((b,symbols(b)));checks={}
    atk=PLAYER+0x3020
    original=bytes([0xa5])*0x170
    e.uc.mem_write(atk,original);e.call('ms_apply_hit_stats',PLAYER,0,1)
    actual=bytes(e.uc.mem_read(atk,len(original)))
    checks['full_source_190_KO_is_retained']=actual[0x56]==190
    checks['only_native_KO_byte_changes']=all(actual[i]==v for i,v in enumerate(original) if i!=0x56)
    e.call('ms_apply_hit_stats',PLAYER,1,2)
    checks['second_attack_slot_is_independent']=e.uc.mem_read(atk+0x56,1)[0]==190 and e.uc.mem_read(atk+0xb8+0x56,1)[0]==25
    e.call('ms_apply_hit_stats',PLAYER,1,4)
    checks['magnetised_copy_keeps_same_KO']=e.uc.mem_read(atk+0xb8+0x56,1)[0]==190
    for skill in (0xac,0x109,0x132,0x28):
        e.skill=skill;e.call('ms_apply_hit_stats',PLAYER,0,1)
        checks[f'native_KO_skill_{skill:x}_applies_once']=e.uc.mem_read(atk+0x56,1)[0]==209
    e.call('ms_apply_hit_stats',PLAYER,0,3)
    checks['skill_adjusted_KO_stays_within_unsigned_byte']=e.uc.mem_read(atk+0x56,1)[0]==255
    e.blocked=True;e.call('ms_apply_hit_stats',PLAYER,0,1)
    checks['native_skill_eligibility_gate_is_preserved']=e.uc.mem_read(atk+0x56,1)[0]==190
    snapshot=bytes(e.uc.mem_read(atk,len(original)))
    for slot,hit in ((2,1),(0,7),(0,0xffffffff)):e.call('ms_apply_hit_stats',PLAYER,slot,hit)
    checks['invalid_slot_and_hit_are_noops']=bytes(e.uc.mem_read(atk,len(original)))==snapshot
    e.call('ms_apply_hit_stats',0,0,1);checks['null_owner_is_noop']=True
    e.call('ms_apply_hit_stats',PLAYER,0,0)
    checks['zero_source_KO_removes_template_KO']=e.uc.mem_read(atk+0x56,1)[0]==0
    report={'checks':checks,'all_passed':all(checks.values())}
    (HERE/'reports/hitstats-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
