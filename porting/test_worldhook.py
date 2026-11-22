"""Check extra shape-hook arguments and preserved interrupted ARM machine state."""
import json,struct
from unicorn import arm_const as A
from test_runtime import Emulator,BIN,RET,STACK,HEAP
from test_hooks import builder
from build_module import HERE,run,symbols
import hook_codegen

def main():
    BIN.mkdir(exist_ok=True);build=builder();img=bytearray(0x200)
    struct.pack_into('<2I',img,0x100,0xe1a01000,0xe1a04004)
    name='ms_local_world_shape';asm=hook_codegen.trampoline(build,img,name,0x100)
    asm+='''
    .global ms_local_world_shape_c
    .hidden ms_local_world_shape_c
ms_local_world_shape_c:
    movw ip, #0x500
    movt ip, #0xc00
    str r1, [ip]
    str r2, [ip, #4]
    str r3, [ip, #8]
    mov r1, #0
    mov r2, #0
    vmov.i32 q0, #0
    vmov.i32 q15, #0
    mov r0, #0
    cmp r0, #0
    bx lr
'''
    source=BIN/'worldhook.S';obj=source.with_suffix('.o');elf=source.with_suffix('.elf')
    source.write_text('.text\n.arm\n'+asm,encoding='utf-8')
    run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard','-c',source,'-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--image-base=0x10000','-e',name+'_tramp','-o',elf,obj)
    data=elf.read_bytes();e=Emulator((data,symbols(data)));u=e.uc
    ints=[0x1000+i*16 for i in range(13)];doubles=[0x3ff0000000000000+i for i in range(32)]
    for i,v in enumerate(ints):u.reg_write(getattr(A,f'UC_ARM_REG_R{i}'),v)
    for i,v in enumerate(doubles):u.reg_write(getattr(A,f'UC_ARM_REG_D{i}'),v)
    u.reg_write(A.UC_ARM_REG_CPSR,0xa80f0010);u.reg_write(A.UC_ARM_REG_FPSCR,0x03000000)
    u.reg_write(A.UC_ARM_REG_SP,STACK-0x100);u.reg_write(A.UC_ARM_REG_LR,RET)
    u.emu_start(e.symbols[name+'_tramp'],RET,count=1000)
    got=[u.reg_read(getattr(A,f'UC_ARM_REG_R{i}')) for i in range(13)]
    expected=ints.copy();expected[1]=ints[0]  # Original displaced mov r1,r0.
    checks={
      'native_shape_record_output_and_index_are_forwarded':struct.unpack('<3I',u.mem_read(HEAP+0x500,12))==(ints[6],ints[9],ints[7]),
      'interrupted_integer_state_and_displaced_instruction':got==expected,
      'all_fp_registers_preserved':all(u.reg_read(getattr(A,f'UC_ARM_REG_D{i}'))==v for i,v in enumerate(doubles)),
      'flags_and_fpscr_preserved':u.reg_read(A.UC_ARM_REG_CPSR)&0xf80f0000==0xa80f0000 and u.reg_read(A.UC_ARM_REG_FPSCR)==0x03000000,
      'stack_and_return_preserved':u.reg_read(A.UC_ARM_REG_SP)==STACK-0x100 and u.reg_read(A.UC_ARM_REG_PC)==RET}
    report={'checks':checks,'all_passed':all(checks.values())}
    (HERE/'reports/worldhook-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
