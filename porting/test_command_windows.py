"""Check source buffer windows against GU's actual ARM frame-range predicate."""
import json,struct,sys
import re
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM
from unicorn import arm_const as A
from build_module import MS,HERE
sys.path[:0]=[str(MS/'tools'),str(MS.parents[1]/'tools')]
import msbuild,msact,arcpack,xfs

def native_range(frame,lo,hi):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
    u.mem_map(0x281000,0x1000)
    data=(HERE/'work/gu_main/mem.bin').read_bytes()
    u.mem_write(0x281000,data[0x281000:0x282000])
    player=0x100000;ret=0x70000000
    u.mem_map(player,0x10000);u.mem_map(ret,0x1000)
    u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
    for off,val in ((0x14d0,frame),(0x14d4,1),(0x504,1000)):
        u.mem_write(player+off,struct.pack('<f',val))
    for reg,val in ((A.UC_ARM_REG_S0,lo),(A.UC_ARM_REG_S1,hi)):
        u.reg_write(reg,struct.unpack('<I',struct.pack('<f',val))[0])
    u.reg_write(A.UC_ARM_REG_R0,player);u.reg_write(A.UC_ARM_REG_LR,ret)
    u.emu_start(0x281388,ret,count=200)
    assert u.reg_read(A.UC_ARM_REG_PC)==ret
    return bool(u.reg_read(A.UC_ARM_REG_R0))

def native_keeps_buffer(pre):
    u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
    data=(HERE/'work/gu_main/mem.bin').read_bytes()
    u.mem_map(0x2ea000,0x1000);u.mem_write(0x2ea000,data[0x2ea000:0x2eb000])
    u.mem_map(0x100000,0x10000);u.mem_write(0x100000,b'\1')
    for r,v in ((A.UC_ARM_REG_R6,pre),(A.UC_ARM_REG_R8,0),(A.UC_ARM_REG_R10,0x100000),(A.UC_ARM_REG_SP,0x108000)):
        u.reg_write(r,v)
    u.emu_start(0x2ea98c,0x2ea9a0,count=10)
    return bool(u.mem_read(0x100000,1)[0])

def main():
    source=(MS.parents[1]/'dump/mhf/zz/mhfdat.dec.prefix.bin').read_bytes();acts=msact.actions(source)
    checks={}
    pin=next(c for c in acts[39]['cancels'] if c['next']==94)
    pre,start,end=msbuild.command_window(pin,1)
    checks['native_reproduces_lost_early_impact_press']=not native_range(32,start-pin['buf'][0][3],end)
    checks['impact_press_inside_source_buffer_is_accepted']=native_range(32,start-pre,end)
    checks['press_before_source_buffer_is_rejected']=not native_range(22,start-pre,end)
    checks['press_after_source_window_is_rejected']=not native_range(78,start-pre,end)
    cross=next((c,k) for a in acts for c in a['cancels'] for k in range(len(a['steps']))
               if c['buf'][0][0]==k and c['go'][0][0]>k and c['buf'][0][1]!=2)
    c,k=cross;pre,start,end=msbuild.command_window(c,k)
    fb=0 if c['buf'][0][1]==1 else c['buf'][0][3]
    checks['cross_step_buffer_opens_at_source_frame']=start-pre==fb and native_range(fb+1,start-pre,end)
    checks['cross_step_transition_stays_out_of_current_motion']=start==msbuild.NEVER
    checks['native_zero_lookback_reproduces_buffer_loss']=not native_keeps_buffer(0)
    carry=next(c for c in acts[54]['cancels'] if c['next']==146)
    pre,_,_=msbuild.command_window(carry,1)
    checks['early_impact_input_survives_zero_frame_transition']=native_keeps_buffer(pre)
    max_commands=0;stable=True;buffer_indices_stable=True
    for i in range(6):
        entries=arcpack.read((MS/'romfs/nativeNX/arc/player/quest'/f'w05_m{i}.arc').read_bytes())[1]
        root=xfs.parse(next(d for p,t,d in entries if t==msbuild.T_TBL))
        tables=root['TblList']['mpArray']
        def count(table):
            v=table['Command']['mpArray'];return len(v) if isinstance(v,list) else 1 if v else 0
        max_commands=max(max_commands,max(count(t) for t in tables))
        generated=(MS/'gen/ms_data.inc').read_text().split('static const struct ms_step ms_steps[] = {',1)[1].split('};',1)[0]
        groups={}
        for fields,no in re.findall(r'\{([^}]+)\},\s*/\* (\d+):',generated):
            table=int(fields.split(',')[-1])-2000
            commands=tables[table]['Command']['mpArray']
            paths=[v['CmdBase'] for v in commands] if isinstance(commands,list) else [commands['CmdBase']] if commands else []
            if no in groups:buffer_indices_stable &= paths==groups[no]
            else:groups[no]=paths
        # The action/step table indices are verified by rebuild_commands.py.
        status=json.loads((HERE/'command-build.json').read_text())
        stable &= status['input_ids_preserved'] and status['table_indices_preserved']
    checks['compiled_input_and_table_indices_preserved']=stable
    checks['buffered_commands_keep_same_indices_across_steps']=buffer_indices_stable
    checks['native_buffer_capacity_is_respected']=max_commands<=48
    report={'checks':checks,'max_commands_per_table':max_commands,'all_passed':all(checks.values()),
            'basis':'Native GU 0x26d018 and 0x2ea974: input range begins at StartFrame - PreFrame'}
    (HERE/'reports/command-window-regression.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
