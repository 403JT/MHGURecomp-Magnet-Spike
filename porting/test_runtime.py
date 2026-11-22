"""Regression tests execute the actual compiled ARM weapon functions.

The legacy source is also tested to establish that the regressions reproduce.
All guest objects are synthetic, bounded test fixtures.
"""
import json
from pathlib import Path
import struct
import sys

from unicorn import Uc, UcError, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE
from unicorn import arm_const as A
from build_module import MS, UPMOD, OUT, HERE, run, symbols

TESTS = HERE / 'tests'
BIN = OUT / 'regression'
EXPORTS = ['test_pointer', 'test_owned', 'test_shot_id', 'test_carrier', 'test_follow', 'test_stop',
           'test_marker', 'test_pin_start', 'test_pin_tick']
BASE, HEAP, PLAYER, CARRIER, VECTOR = 0x200000, 0x0c000000, 0x0c010000, 0x0c020000, 0x0c021000
PROXY, PEL, RECORDS, RECORD = 0x0c001000, 0x0c002000, 0x0c003000, 0x0c004000
RET, STACK, STALE = 0x70000000, 0x71010000, 0x0e000000


def compile_test(legacy=False):
    name = 'legacy' if legacy else 'fixed'
    BIN.mkdir(parents=True, exist_ok=True)
    obj, elf = BIN / (name + '.o'), BIN / (name + '.elf')
    flags = ['--target=armv7a-none-eabihf', '-mcpu=cortex-a57', '-marm', '-mfloat-abi=hard',
             '-ffreestanding', '-fno-builtin', '-nostdlib', '-O2', '-ffunction-sections', '-fdata-sections',
             '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-DMS_RECOMP',
             '-I', MS / 'module', '-I', MS / 'gen', '-I', UPMOD]
    if legacy:
        flags.append('-DMS_TEST_SOURCE="' + (HERE / 'reports/baseline-ms_act.c').as_posix() + '"')
    run('clang', *flags, '-c', TESTS / 'runtime_harness.c', '-o', obj)
    run('ld.lld', '-m', 'armelf_linux_eabi', '-static', '--gc-sections', '--image-base=0x10000',
        '-e', EXPORTS[0], *[v for name in EXPORTS for v in ('-u', name)], '-o', elf, obj)
    data = elf.read_bytes()
    return data, symbols(data)


class Emulator:
    def __init__(self, binary):
        data, self.symbols = binary
        self.uc = u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
        phoff = struct.unpack_from('<I', data, 0x1c)[0]
        entsize, n = struct.unpack_from('<HH', data, 0x2a)
        pages = set()
        for i in range(n):
            kind, off, va, _, fsize, msize = struct.unpack_from('<6I', data, phoff + i * entsize)
            if kind != 1 or not msize:
                continue
            for page in range(va & ~4095, (va + msize + 4095) & ~4095, 4096):
                if page not in pages:
                    u.mem_map(page, 4096); pages.add(page)
            u.mem_write(va, data[off:off + fsize])
        u.mem_map(BASE, 0x2200000)
        u.mem_map(HEAP, 0x400000)
        u.mem_map(RET, 4096)
        u.mem_map(STACK - 0x10000, 0x10000)
        u.reg_write(A.UC_ARM_REG_C1_C0_2, 0xf << 20)
        u.reg_write(A.UC_ARM_REG_FPEXC, 0x40000000)
        self.calls = {'post': 0, 'move': 0, 'stop': 0, 'action': 0}
        self.monster = 0
        self.w32(BASE + 0x1851fe0, HEAP + 0x30000)
        u.hook_add(UC_HOOK_CODE, self.engine, begin=BASE, end=BASE + 0x2200000 - 1)

    def w32(self, at, value): self.uc.mem_write(at, struct.pack('<I', value))
    def w16(self, at, value): self.uc.mem_write(at, struct.pack('<H', value))

    def proxy(self, address, ident):
        # Each fixture's PEL record is separate, even if the allocator reuses a proxy.
        pel, table, record = address + 0x400, address + 0x600, address + 0x700
        self.w32(address, BASE + 0x1731578)
        self.w32(address + 0xc, 1)
        self.uc.mem_write(address + 0x30, b'\x01')
        self.w32(address + 0x34, pel)
        self.w32(address + 0x40, 0)
        self.w32(address + 0x44, 0)
        self.w32(pel + 0x68, 1)
        self.w32(pel + 0x74, table)
        self.w32(table, record)
        self.w16(record + 0x50, ident)
        return address

    def engine(self, u, address, size, _):
        offset = address - BASE
        if offset == 0x5ceb4:
            u.reg_write(A.UC_ARM_REG_R0, self.monster if u.reg_read(A.UC_ARM_REG_R1) == 0 else 0)
        elif offset == 0x32a45c: self.calls['move'] += 1
        elif offset == 0x32a400: self.calls['stop'] += 1
        elif offset == 0x2831e0: self.calls['action'] += 1
        elif offset == 0x40b10:
            u.mem_write(u.reg_read(A.UC_ARM_REG_R0), bytes(0xd8))
        elif offset == 0x40b50: pass
        elif offset == 0x282548:
            self.calls['post'] += 1
            hp = HEAP + 0x100000 + self.calls['post'] * 0x1000
            self.proxy(hp, u.reg_read(A.UC_ARM_REG_R3))
            u.reg_write(A.UC_ARM_REG_R0, hp)
        else:
            raise AssertionError(f'Unexpected engine call {offset:x}')
        u.reg_write(A.UC_ARM_REG_PC, u.reg_read(A.UC_ARM_REG_LR))

    def call(self, name, *args):
        u = self.uc
        for reg, value in zip((A.UC_ARM_REG_R0, A.UC_ARM_REG_R1, A.UC_ARM_REG_R2, A.UC_ARM_REG_R3), args):
            u.reg_write(reg, value)
        u.reg_write(A.UC_ARM_REG_SP, STACK - 0x100)
        u.reg_write(A.UC_ARM_REG_LR, RET)
        u.emu_start(self.symbols[name], RET, count=100000)
        if u.reg_read(A.UC_ARM_REG_PC) != RET:
            raise AssertionError('Guest function did not return within the instruction limit')
        return u.reg_read(A.UC_ARM_REG_R0)


def suite(binary):
    e = Emulator(binary)
    checks = {}
    checks['recomp_heap_pointer'] = e.call('test_pointer', PROXY) == 1
    checks['invalid_pointer_rejected'] = all(e.call('test_pointer', p) == 0 for p in (0, 0x3000000, PROXY + 1, 0xf0000000))
    ident = e.call('test_shot_id')
    e.proxy(PROXY, ident)
    checks['live_proxy_owned'] = e.call('test_owned', PROXY, ident) == 1
    checks['reused_proxy_rejected'] = e.call('test_owned', PROXY, ident + 1) == 0
    e.call('test_carrier', CARRIER, PROXY, ident)
    e.w32(PLAYER + 0x3304, PEL)
    e.uc.mem_write(VECTOR, struct.pack('<3f', 0, 0, 0))
    for _ in range(600):
        e.call('test_follow', PLAYER, CARRIER, VECTOR)
    checks['600_updates_reuse_proxy'] = e.calls['move'] == 600 and e.calls['post'] == 0
    e.call('test_stop', CARRIER)
    checks['carrier_stopped_once'] = e.calls['stop'] == 1
    e.call('test_stop', CARRIER)
    checks['second_stop_is_noop'] = e.calls['stop'] == 1
    for function, expected in [('test_marker', 0), ('test_pin_start', 1), ('test_pin_tick', 1)]:
        try:
            checks[function + '_removed_target'] = e.call(function, PLAYER, STALE, VECTOR) == expected
        except UcError:
            checks[function + '_removed_target'] = False
    monster, record = HEAP + 0x300000, HEAP + 0x320000
    e.monster = monster
    e.w32(monster + 0x1428, record)
    e.w32(record + 0x370, 100)
    e.uc.mem_write(monster + 0x1054, b'\x01')
    e.uc.mem_write(PLAYER + 0x1054, b'\x01')
    e.uc.mem_write(record + 0x40, struct.pack('<3f', 10, 20, 30))
    checks['live_marker_target_kept'] = e.call('test_marker', PLAYER, monster, VECTOR) == 1 and \
        struct.unpack('<3f', e.uc.mem_read(VECTOR, 12)) == (10.0, 320.0, 30.0)
    checks['live_pin_target_kept'] = e.call('test_pin_start', PLAYER, monster) == 0
    e.w32(record + 0x370, 0)
    checks['dead_marker_target_rejected'] = e.call('test_marker', PLAYER, monster, VECTOR) == 0
    e.w32(record + 0x370, 100)
    e.uc.mem_write(monster + 0x1054, b'\x02')
    checks['other_area_marker_rejected'] = e.call('test_marker', PLAYER, monster, VECTOR) == 0
    return checks, e.calls


def main():
    legacy, _ = suite(compile_test(True))
    fixed, calls = suite(compile_test(False))
    expected_regressions = ('recomp_heap_pointer', 'live_proxy_owned', '600_updates_reuse_proxy',
                            'carrier_stopped_once', 'test_marker_removed_target',
                            'test_pin_start_removed_target', 'test_pin_tick_removed_target')
    assert all(not legacy[k] for k in expected_regressions), legacy
    assert all(fixed.values()), fixed
    report = {'legacy': legacy, 'fixed': fixed, 'fixed_engine_calls': calls}
    (HERE / 'reports/runtime-regression.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
