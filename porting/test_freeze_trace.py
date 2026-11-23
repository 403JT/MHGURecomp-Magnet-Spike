"""Verify diagnostic logging stays observational and survives long hunts."""
import json
import struct
from test_runtime import Emulator,PLAYER,BASE
from unicorn import arm_const as A
from build_module import HERE,MS,UPMOD,OUT,run,symbols


def compile_test(diagnostic):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    name='freeze-trace'+('-diagnostic' if diagnostic else '-normal')
    obj,elf=folder/(name+'.o'),folder/(name+'.elf')
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD]
    if diagnostic:flags.append('-DMS_FREEZE_DIAGNOSTICS')
    run('clang',*flags,'-c',HERE/'tests/freeze_trace_harness.c','-o',obj)
    exports=['test_freeze_trace','test_freeze_lines']
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,obj)
    b=elf.read_bytes();return b,symbols(b)


def prepare(e,p=PLAYER,category=16,dt=1.):
    e.w16(p+0x2506,category);e.w16(p+0x250a,11)
    e.uc.mem_write(p+5,b'\1');e.uc.mem_write(p+0x1c,struct.pack('<f',dt))


class Trace(Emulator):
    def engine(self,u,address,size,arg):
        if address==BASE+0x53a058:
            u.reg_write(A.UC_ARM_REG_R0,5001)
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        return super().engine(u,address,size,arg)


def main():
    binary=compile_test(True);checks={}
    e=Trace(binary);prepare(e)
    before=bytes(e.uc.mem_read(PLAYER,0x3340))
    e.call('test_freeze_trace',PLAYER)
    checks['first_sample_three_lines']=e.call('test_freeze_lines')==3
    for _ in range(179):e.call('test_freeze_trace',PLAYER)
    checks['no_early_heartbeat']=e.call('test_freeze_lines')==3
    e.call('test_freeze_trace',PLAYER)
    checks['heartbeat_at_180_game_frames']=e.call('test_freeze_lines')==6
    checks['observer_leaves_actor_bytes_unchanged']=bytes(e.uc.mem_read(PLAYER,0x3340))==before
    e=Trace(binary);prepare(e,category=1)
    for _ in range(1000):e.call('test_freeze_trace',PLAYER)
    checks['idle_does_not_emit_periodic_spam']=e.call('test_freeze_lines')==3
    e=Trace(binary)
    players=[PLAYER+i*0x10000 for i in range(5)]
    for p in players:prepare(e,p);e.call('test_freeze_trace',p)
    for _ in range(179):
        for p in players:e.call('test_freeze_trace',p)
    checks['five_owners_do_not_trigger_each_others_samples']=e.call('test_freeze_lines')==15
    for p in players:e.call('test_freeze_trace',p)
    checks['five_independent_heartbeats']=e.call('test_freeze_lines')==30
    for diagnostic in (False,True):
        e=Trace(binary if diagnostic else compile_test(False));prepare(e)
        for i in range(700):
            e.w16(PLAYER+0x250a,11+i%2);e.call('test_freeze_trace',PLAYER)
        expected=2100 if diagnostic else 600
        checks['diagnostics_pass_600_transitions' if diagnostic else 'normal_trace_limit_unchanged']=e.call('test_freeze_lines')==expected
    report={'checks':checks,'all_passed':all(checks.values()),
            'scope':'Compiled ARM observer; no weapon or hunter state mutation and independent per-owner samples'}
    (HERE/'reports/freeze-trace-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report));assert report['all_passed']


if __name__=='__main__':main()
