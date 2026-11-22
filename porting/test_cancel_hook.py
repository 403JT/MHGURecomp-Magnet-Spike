"""Verify the scoped range-hook ABI on both handled and native fallback paths."""
import json,struct
from unicorn import arm_const as A
from test_runtime import Emulator,BIN,RET,STACK,HEAP
from test_hooks import builder
from build_module import HERE,run,symbols
import hook_codegen

def main():
    BIN.mkdir(exist_ok=True);build=builder();img=(HERE/'work/gu_main/mem.bin').read_bytes()
    name='ms_local_cancel_range';checks={k:True for k in (
        'native_row_index_forwarded','integer_state_and_intentional_result_preserved',
        'all_fp_registers_preserved','flags_and_fpscr_preserved','stack_and_return_preserved')}
    for handled in (0,1):
        asm=hook_codegen.trampoline(build,img,name,0x281388)
        asm+='''
    .global ms_local_cancel_range_c
    .hidden ms_local_cancel_range_c
ms_local_cancel_range_c:
    movw ip, #0x500
    movt ip, #0xc00
    str r1, [ip]
    vmov.i32 q0, #0
    vmov.i32 q8, #0
    vmov.i32 q15, #0
    mov r2, #0x400000
    vmsr fpscr, r2
'''
        if handled:asm+='    mov r2, #42\n    str r2, [r0]\n'
        asm+=f'    mov r0, #{handled}\n    cmp r0, #0\n    bx lr\n'
        path=BIN/f'cancel-hook-{handled}';src=path.with_suffix('.S');obj=path.with_suffix('.o');elf=path.with_suffix('.elf')
        src.write_text('.text\n.arm\n'+asm,encoding='utf-8')
        run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard','-c',src,'-o',obj)
        run('ld.lld','-m','armelf_linux_eabi','-static','--image-base=0x10000','-e',name+'_tramp','-o',elf,obj)
        data=elf.read_bytes();e=Emulator((data,symbols(data)));u=e.uc
        for flags in (0,0x40000000,0xa80f0000):
            ints=[0x1000+i*16 for i in range(13)];doubles=[0x3ff0000000000000+i for i in range(32)]
            for i,v in enumerate(ints):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
            for i,v in enumerate(doubles):u.reg_write(getattr(A,f'UC_ARM_REG_D{i}'),v)
            u.reg_write(A.UC_ARM_REG_CPSR,0x10|flags);u.reg_write(A.UC_ARM_REG_FPSCR,0x03000000)
            u.reg_write(A.UC_ARM_REG_SP,STACK-0x100);u.reg_write(A.UC_ARM_REG_LR,RET)
            u.emu_start(e.symbols[name+'_tramp'],RET,count=1000)
            expected=ints.copy()
            if handled:expected[0]=42
            else:expected[1]=ints[0]+0x4f4  # Actual displaced movw and add r1,r0,r1.
            checks['native_row_index_forwarded'] &= int.from_bytes(u.mem_read(HEAP+0x500,4),'little')==ints[8]
            checks['integer_state_and_intentional_result_preserved'] &= all(u.reg_read(getattr(A,f'UC_ARM_REG_R{i}'))==v for i,v in enumerate(expected))
            checks['all_fp_registers_preserved'] &= all(u.reg_read(getattr(A,f'UC_ARM_REG_D{i}'))==v for i,v in enumerate(doubles))
            checks['flags_and_fpscr_preserved'] &= u.reg_read(A.UC_ARM_REG_CPSR)&0xf80f0000==flags and u.reg_read(A.UC_ARM_REG_FPSCR)==0x03000000
            checks['stack_and_return_preserved'] &= u.reg_read(A.UC_ARM_REG_SP)==STACK-0x100 and u.reg_read(A.UC_ARM_REG_PC)==RET
    report={'checks':checks,'all_passed':all(checks.values()),'scope':'Both actual displaced GU instructions; both hook paths and three status-flag patterns'}
    (HERE/'reports/cancel-hook-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
