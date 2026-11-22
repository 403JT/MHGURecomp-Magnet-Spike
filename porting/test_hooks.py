"""Execute old/new injected hook wrappers against synthetic ARM instructions."""
import importlib.util
import json
import os
import struct
import sys
from unicorn import arm_const as A
from build_module import HERE, CONVERTER, UPMOD, run, symbols
from test_runtime import Emulator, BIN, RET, STACK
import hook_codegen


def builder():
    os.environ['GU_CODE'] = str(HERE / 'work/gu_main')
    sys.path.insert(0, str(CONVERTER / 'tools'))
    spec = importlib.util.spec_from_file_location('hook_test_build', UPMOD / 'build.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    build.main_ref = lambda offset: hex(RET)
    return build


def compile_test(build, fixed, handled):
    name = f'hook-{fixed}-{handled}'
    source, obj, elf = [BIN / (name + suffix) for suffix in ('.S', '.o', '.elf')]
    image = bytearray(0x200)
    # Conditional add needs the incoming Z flag. The second instruction is neutral.
    struct.pack_into('<2I', image, 0x100, 0x02800001, 0xe1a05005)
    make = hook_codegen.trampoline if fixed else lambda b, i, n, s: b.trampoline(i, n, s)
    assembly = make(build, image, 'fixture', 0x100)
    callback = '''
    .text
    .global fixture_c
    .hidden fixture_c
fixture_c:
    vmov.i32 q0, #0
    vmov.i32 q8, #0
    vmov.i32 q15, #0
    mov r2, #0x400000
    vmsr fpscr, r2
'''
    if handled:
        callback += '    mov r2, #0x55000000\n    str r2, [r0]\n'
    callback += f'    mov r0, #{int(handled)}\n    cmp r0, #0\n    bx lr\n'
    source.write_text('.text\n.arm\n' + assembly + callback, encoding='utf-8')
    run('clang', '--target=armv7a-none-eabihf', '-mcpu=cortex-a57', '-marm', '-mfloat-abi=hard',
        '-c', source, '-o', obj)
    run('ld.lld', '-m', 'armelf_linux_eabi', '-static', '--image-base=0x10000', '-e', 'fixture_tramp',
        '-o', elf, obj)
    data = elf.read_bytes()
    return data, symbols(data)


def suite(build, fixed):
    checks = {'conditional_instruction': True, 'all_fp_registers': True, 'fpscr': True,
              'integer_registers': True, 'status_flags': True, 'handled_register_edit': True}
    for handled in (False, True):
        binary = compile_test(build, fixed, handled)
        for flags in (0, 0x40000000, 0xa80f0000):
            e = Emulator(binary)
            u = e.uc
            integers = [0x1000 + i * 16 for i in range(13)]
            doubles = [0x3ff0000000000000 + i for i in range(32)]
            for i, value in enumerate(integers): u.reg_write(getattr(A, f'UC_ARM_REG_R{i}'), value)
            for i, value in enumerate(doubles): u.reg_write(getattr(A, f'UC_ARM_REG_D{i}'), value)
            u.reg_write(A.UC_ARM_REG_FPSCR, 0x03000000)
            u.reg_write(A.UC_ARM_REG_CPSR, 0x10 | flags)
            u.reg_write(A.UC_ARM_REG_SP, STACK - 0x100)
            u.reg_write(A.UC_ARM_REG_LR, RET)
            u.emu_start(e.symbols['fixture_tramp'], RET, count=1000)
            actual = [u.reg_read(getattr(A, f'UC_ARM_REG_R{i}')) for i in range(13)]
            expected0 = 0x55000000 if handled else integers[0] + int(bool(flags & 0x40000000))
            checks['conditional_instruction'] &= handled or actual[0] == expected0
            checks['handled_register_edit'] &= not handled or actual[0] == expected0
            checks['integer_registers'] &= actual[1:] == integers[1:]
            checks['all_fp_registers'] &= all(u.reg_read(getattr(A, f'UC_ARM_REG_D{i}')) == value
                                               for i, value in enumerate(doubles))
            checks['fpscr'] &= u.reg_read(A.UC_ARM_REG_FPSCR) == 0x03000000
            checks['status_flags'] &= u.reg_read(A.UC_ARM_REG_CPSR) & 0xf80f0000 == flags
            assert u.reg_read(A.UC_ARM_REG_SP) == STACK - 0x100
    return checks


def main():
    BIN.mkdir(parents=True, exist_ok=True)
    build = builder()
    legacy, fixed = suite(build, False), suite(build, True)
    assert not legacy['conditional_instruction'] and not legacy['all_fp_registers'] and not legacy['fpscr'], legacy
    assert all(fixed.values()), fixed
    report = {'legacy': legacy, 'fixed': fixed}
    (HERE / 'reports/hook-regression.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
