"""Compare compiled ARM temporal gates with the original MHF x86 predicates."""
import json,struct,sys
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn import x86_const as X,arm_const as A
from test_runtime import Emulator,BASE,HEAP,PLAYER,STACK
from build_module import HERE,OUT,MS,UPMOD,run,symbols
from build_cancel_windows import generate
from dis_audio import image

REGS,INFO=HEAP+0x250000,HEAP+0x260000
EXPORTS=['fixture_setup','fixture_time','fixture_remove','fixture_input_mode','fixture_native_input',
         'fixture_native_range','fixture_clock','ms_cancel_windows_reset','ms_local_cancel_range_c']

def compile_test():
    folder=OUT/'cancel-regression';folder.mkdir(exist_ok=True)
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-I',MS/'module','-I',UPMOD,'-I',OUT]
    obj=folder/'fixture.o';elf=folder/'fixture.elf'
    run('clang',*flags,'-c',HERE/'tests/cancel_windows_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',EXPORTS[0],*[v for n in EXPORTS for v in ('-u',n)],'-o',elf,obj)
    b=elf.read_bytes();return b,symbols(b)

class NativeMHF:
    def __init__(self):
        data,base,_=image('mhf');u=self.u=Uc(UC_ARCH_X86,UC_MODE_32)
        for page in (0x10a68000,0x108ff000):
            u.mem_map(page,4096);u.mem_write(page,bytes(data[page-base:page-base+4096]))
        self.player=0x100000;self.stack=0x200000;self.ret=0x300000
        for p in (self.player,self.stack,self.ret):u.mem_map(p,4096)
    def passed(self,t,step,loop,frame):
        u=self.u;p=self.player
        u.mem_write(p+0xf96,struct.pack('<HH',step,loop));u.mem_write(p+0x334,b'\1')
        u.mem_write(p+0x1dc,struct.pack('<f',frame));u.mem_write(p+0x204,bytes(4))
        u.mem_write(self.stack+0x800,struct.pack('<4I',self.ret,t[1],t[2]&0xffffffff,t[3]))
        for r,v in ((X.UC_X86_REG_ESP,self.stack+0x800),(X.UC_X86_REG_EAX,p),
                    (X.UC_X86_REG_EDX,t[0]),(X.UC_X86_REG_ESI,t[4])):u.reg_write(r,v)
        u.emu_start(0x10a68090,self.ret,count=200)
        assert u.reg_read(X.UC_X86_REG_EIP)==self.ret
        return bool(u.reg_read(X.UC_X86_REG_EAX))

class NativeGU(Emulator):
    def __init__(self,b):
        super().__init__(b);self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.prowler=False;self.use_range=False;self.walk=False
        self.w32(PLAYER+0x13c4,INFO);self.uc.mem_write(INFO+0x4d4,b'\5')
        self.wfloat(PLAYER+0x504,1000000)
    def wfloat(self,p,v):self.uc.mem_write(p,struct.pack('<f',v))
    def engine(self,u,address,size,_):
        if self.walk and address==BASE+0x2ecea8:
            u.emu_stop();return
        if self.use_range and address==BASE+0x281388:
            u.reg_write(A.UC_ARM_REG_R1,u.reg_read(A.UC_ARM_REG_R8))
            u.reg_write(A.UC_ARM_REG_PC,self.symbols['fixture_native_range']);return
        if BASE+0x280e4c<=address<=BASE+0x280f20:return
        if BASE+0x281388<=address<=BASE+0x281470:return
        if BASE+0x2ea974<=address<=BASE+0x2ea9cc:return
        if address==BASE+0x27b918:
            u.reg_write(A.UC_ARM_REG_R0,int(self.prowler));u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        if address==BASE+0x2ecefc:
            u.reg_write(A.UC_ARM_REG_PC,self.symbols['fixture_native_input']);return
        return super().engine(u,address,size,_)
    def clock(self,action,step,loop,frame):
        self.call('fixture_setup',PLAYER,action,step,loop)
        for off in (0x4fc,0x14d0):self.wfloat(PLAYER+off,frame)
        self.wfloat(PLAYER+0x14d4,0);self.wfloat(PLAYER+0x4f4,0)
    def query(self,row,phase,caller=None):
        name='ms_local_cancel_range_c'
        regs=[PLAYER,123,234,345,456,567,678,BASE+(caller if caller is not None else (0x2eb298 if phase==2 else 0x2ea984))]
        self.uc.mem_write(REGS,struct.pack('<8I',*regs));handled=self.call(name,REGS,row)
        after=struct.unpack('<8I',self.uc.mem_read(REGS,32));assert after[1:]==tuple(regs[1:])
        return handled,after[0]
    def native_buffer(self,row,cached,window,filter_=True,raw=1):
        u=self.uc;self.call('fixture_input_mode',raw)
        self.use_range=filter_;self.walk=True
        self.uc.mem_write(PLAYER+0x24b0+row,bytes([cached]))
        for r,v in ((A.UC_ARM_REG_R4,PLAYER),(A.UC_ARM_REG_R5,INFO),(A.UC_ARM_REG_R6,int(window[0])),
                    (A.UC_ARM_REG_R8,row),(A.UC_ARM_REG_R10,PLAYER+0x24b0),(A.UC_ARM_REG_SP,STACK-0x400)):
            u.reg_write(r,v)
        for r,v in ((A.UC_ARM_REG_S20,window[1]),(A.UC_ARM_REG_S21,window[0]),(A.UC_ARM_REG_S22,window[2])):
            u.reg_write(r,struct.unpack('<I',struct.pack('<f',v))[0])
        u.emu_start(BASE+0x2ea974,BASE+0x2ea9cc,count=100000)
        assert u.reg_read(A.UC_ARM_REG_PC) in (BASE+0x2ea9cc,BASE+0x2ecea8),hex(u.reg_read(A.UC_ARM_REG_PC))
        self.use_range=False;self.walk=False
        return u.mem_read(PLAYER+0x24b0+row,1)[0]

def main():
    status=generate();sys.path.insert(0,str(MS/'tools'));import msbuild
    tables=msbuild.WINDOW_TABLES;rules=[];starts={}
    for t in tables:
        if t['action'] not in starts:
            starts[t['action']]=len(rules);rules.extend(c['buf']+c['go'] for c in t['cancels'])
    source=NativeMHF();e=NativeGU(compile_test());checks={};comparisons=0;match=True
    for ri,rule in enumerate(rules):
        for si,t in enumerate(rule):
            for step in sorted({0,t[0]+1,t[0]+2}):
                for loop in sorted({0,t[4],t[4]+1}):
                    for frame in sorted({0,max(0,t[3]-1),t[3],t[3]+1}):
                        e.clock(34,step,loop,frame)
                        match &= bool(e.call('fixture_time',PLAYER,ri,si))==source.passed(t,step,loop,frame)
                        comparisons+=1
    checks['all_source_time_boundaries_match_original_x86_and_ARM_frame_helpers']=match
    table=next(t for t in tables if t['action']==34 and t['step']==0)
    ci=next(i for i,c in enumerate(table['cancels']) if c['input']==0 and c['buf'][0][3]==50)
    row=table['rows'].index(ci)
    e.call('ms_cancel_windows_reset',PLAYER);e.clock(34,1,0,49)
    checks['late_roll_does_not_open_before_its_first_frame']=e.query(row,0)==(1,0)
    e.clock(34,1,0,50)
    checks['late_roll_opens_at_source_frame']=e.query(row,0)==(1,1) and e.query(row,2)==(1,1)
    e.clock(34,1,1,10)
    checks['source_open_window_survives_motion_loop']=e.query(row,0)==(1,1) and e.query(row,2)==(1,1)
    old_window=msbuild.command_window(table['cancels'][ci],0)
    checks['legacy_native_range_loses_input_after_motion_wrap']=e.native_buffer(row,0,old_window,False)==0
    checks['source_gates_accept_input_after_motion_wrap_in_original_native_buffer']=e.native_buffer(row,0,(1,0,1))==1
    checks['positive_lookback_preserves_native_cached_input']=e.native_buffer(row,1,(1,0,1),raw=0)==1
    e.clock(34,1,3,117)
    checks['loop_qualified_end_stays_open_before_boundary']=e.query(row,2)==(1,1)
    e.clock(34,1,3,118)
    checks['loop_qualified_end_closes_at_boundary']=e.query(row,2)==(1,0)
    e.clock(34,1,4,0)
    checks['closed_window_does_not_reopen_on_later_loop']=e.query(row,0)==(1,0)
    e.call('ms_cancel_windows_reset',PLAYER);e.clock(34,1,0,0)
    checks['same_action_restart_clears_temporal_latches']=e.query(row,0)==(1,0)
    checks['native_input_before_source_window_is_blocked']=e.native_buffer(row,0,(1,0,1))==0
    checks['unrelated_caller_falls_through']=e.query(row,0,0x12345)==(0,PLAYER)
    checks['out_of_range_row_falls_through']=e.query(99,0)==(0,PLAYER)
    e.w32(PLAYER+0x24ac,9999)
    checks['unmatched_native_table_falls_through']=e.query(row,0)==(0,PLAYER)
    e.clock(34,1,0,50);e.uc.mem_write(INFO+0x4d4,b'\0')
    checks['other_weapon_class_falls_through']=e.query(row,0)==(0,PLAYER);e.uc.mem_write(INFO+0x4d4,b'\5')
    e.prowler=True;checks['prowler_falls_through']=e.query(row,0)==(0,PLAYER);e.prowler=False
    e.call('fixture_remove');checks['removed_hunter_falls_through']=e.query(row,0)==(0,PLAYER)
    checks['source_action_scope_is_exact']=set(status['actions'])=={34,*msbuild.RECOVERY_FRAMES}
    report={'checks':checks,'all_passed':all(checks.values()),'original_predicate_comparisons':comparisons,
        'source_cancels_checked':len(rules),'scope':'Original MHF x86 time predicate and frame helper; compiled ARM gates and original GU buffer block'}
    (HERE/'reports/cancel-window-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
