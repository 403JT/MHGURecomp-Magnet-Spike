"""Compiled aim lifecycle and real GU cursor selector, with synthetic actors."""
import argparse
import json
import math
import struct
from pathlib import Path
from unicorn import arm_const as A
from build_module import HERE, MS, UPMOD, OUT, run, symbols
from test_runtime import Emulator, BASE, HEAP, PLAYER, VECTOR
from native_cfg import instruction_addresses

CAM, MGR, DTI, CVT, PVT, INFO, WIDGET = [HEAP + x for x in
    (0x50000, 0x60000, 0x70000, 0x80000, 0x90000, 0xa0000, 0xb0000)]


def compile_test(source, out):
    out.mkdir(parents=True, exist_ok=True)
    obj, elf = out / 'glaive-aim.o', out / 'glaive-aim.elf'
    flags = ['--target=armv7a-none-eabihf', '-mcpu=cortex-a57', '-marm', '-mfloat-abi=hard',
             '-ffreestanding', '-fno-builtin', '-nostdlib', '-O2', '-ffunction-sections', '-fdata-sections',
             '-fno-unwind-tables', '-fno-asynchronous-unwind-tables', '-DMS_RECOMP',
             '-I', source / 'module', '-I', source / 'gen', '-I', UPMOD]
    run('clang', *flags, '-c', HERE / 'tests/glaive_aim_harness.c', '-o', obj)
    exports = ['test_aim_reset', 'test_aim_flags', 'test_aim_view', 'test_aim_read', 'ms_aim_cursor']
    run('ld.lld', '-m', 'armelf_linux_eabi', '-static', '--gc-sections', '--image-base=0x10000',
        '-e', exports[0], *[v for n in exports for v in ('-u', n)], '-o', elf, obj)
    data = elf.read_bytes()
    return data, symbols(data)


class Aim(Emulator):
    def __init__(self, binary):
        super().__init__(binary)
        data = (HERE / 'work/gu_main/mem.bin').read_bytes()
        self.uc.mem_write(BASE, data)
        self.allowed = instruction_addresses(data, 0x61e438, 0x2a05b8, 0x283060, 0x27c7ec, 0x27bcd0, 0x2a9ec0,
                    0x2a784c, 0x269908, 0x269910, 0x269918, 0x2a8458, 0x269558, 0x2a1c48,
                    0x285e2c, 0x27e608)
        self.w32(PLAYER, PVT)
        self.w32(PLAYER + 0x13c4, INFO)
        self.uc.mem_write(INFO + 0x4d4, bytes([5]))
        self.w16(PLAYER + 0x2506, 16)
        self.w16(PLAYER + 0x250a, 84)
        for slot in range(556):
            fn = struct.unpack_from('<I', data, 0x1749a88 + 4 * slot)[0]
            self.w32(PVT + 4 * slot, BASE + fn if fn else 0)
        self.w32(PVT + 342 * 4, self.symbols['ms_aim_cursor'])
        # Supply unrelated GUI capability queries with their ordinary melee
        # defaults. Their complete implementations need live AI/input managers.
        # The classifier itself and our slot 342 predicate run as real ARM code.
        for slot in (113, 256, 433, 440, 441, 442): self.w32(PVT + slot * 4, BASE + 0x11000)
        self.w32(BASE + 0x184d8b8 + 4, 1234)
        self.w32(DTI + 4, 1234)
        self.w32(CAM, CVT)
        self.w32(CVT + 0x14, BASE + 0x10000)
        self.w32(MGR + 0x54, CAM)
        self.symbols['native_cursor_kind'] = BASE + 0x61e438
        self.camera_starts = 0

    def engine(self, u, address, size, _):
        off = address - BASE
        if off in self.allowed: return
        if off == 0x10000:
            u.reg_write(A.UC_ARM_REG_R0, DTI)
        elif off == 0x11000:
            u.reg_write(A.UC_ARM_REG_R0, 0)
        elif off == 0x13efd70:
            x, y = [struct.unpack('<f', struct.pack('<I', u.reg_read(r)))[0]
                    for r in (A.UC_ARM_REG_S0, A.UC_ARM_REG_S1)]
            u.reg_write(A.UC_ARM_REG_S0, struct.unpack('<I', struct.pack('<f', math.atan2(x, y)))[0])
        elif off == 0x1baa4:
            self.camera_starts += 1
        else:
            raise AssertionError('Unexpected native dependency: ' + hex(off) + ' from ' +
                                 hex(u.reg_read(A.UC_ARM_REG_LR) - BASE))
        u.reg_write(A.UC_ARM_REG_PC, u.reg_read(A.UC_ARM_REG_LR))

    def angles(self):
        self.call('test_aim_read', VECTOR)
        return struct.unpack('<4f', self.uc.mem_read(VECTOR, 16))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--weapon-source', type=Path, default=MS)
    p.add_argument('--output-dir', type=Path, default=OUT / 'glaive-aim-tests')
    args = p.parse_args()
    e = Aim(compile_test(args.weapon_source.resolve(), args.output_dir.resolve()))
    checks = {}
    for local in (0, 1, 2, 3):
        for flags in (0, 1, 0x10, 0x11, 0x20, 0x21, 0x8001, 0x8011):
            e.call('test_aim_reset', PLAYER)
            e.call('test_aim_flags', PLAYER, flags, local)
            want = bool(flags & 1 and not flags & 0x10 and local & 1)
            checks[f'cursor_owner_{local}_{flags}'] = e.call('ms_aim_cursor', PLAYER) == want
            e.w32(BASE + 0x2126504, 0)
            e.call('test_aim_view', PLAYER)
            view = e.angles()
            checks[f'view_lifecycle_{local}_{flags}'] = bool(view[2]) == want
            checks[f'no_bowgun_byte_{local}_{flags}'] = e.uc.mem_read(PLAYER + 0x2716, 1) == b'\0'
            # GU creates this HUD for the local player only. Remote ownership
            # is checked directly above; do not invoke a local HUD on an AI actor.
            if local & 1:
                kind = e.call('native_cursor_kind', WIDGET, PLAYER)
                checks[f'native_kind_{local}_{flags}'] = kind == (4 if want else 8)
    e.call('test_aim_reset', PLAYER)
    e.call('test_aim_flags', PLAYER, 1, 1)
    e.w32(BASE + 0x2126504, MGR)
    e.uc.mem_write(CAM + 0x40, struct.pack('<3f', 10, 20, 30))
    cases = [(0, 0, 500), (500, 0, 0), (-500, 0, 0), (0, 0, -500),
             (100, 200, 300), (100, -200, 300), (0, 500, 0), (0, -500, 0)]
    for i, (x, y, z) in enumerate(cases):
        e.uc.mem_write(CAM + 0x60, struct.pack('<3f', 10 + x, 20 + y, 30 + z))
        before = bytes(e.uc.mem_read(CAM, 0xae0))
        e.w32(PLAYER + 0xfec, 12345)
        e.call('test_aim_view', PLAYER)
        actual = e.angles()
        expected_pitch = math.atan2(y, math.hypot(x, z)) * 10430.378
        expected_yaw = int(math.atan2(x, z) * 10430.378) & 65535
        checks[f'camera_pitch_{i}'] = abs(actual[1] - expected_pitch) < .01
        if x or z: checks[f'camera_yaw_{i}'] = abs(actual[0] - expected_yaw) <= 1
        checks[f'camera_not_changed_{i}'] = bytes(e.uc.mem_read(CAM, 0xae0)) == before
        checks[f'hunter_not_turned_{i}'] = int.from_bytes(e.uc.mem_read(PLAYER + 0xfec, 4), 'little') == 12345
    previous = e.angles()[:2]
    for i, direction in enumerate(((0., 0., 0.), (float('nan'), 0., 1.), (float('inf'), 1., 1.))):
        e.uc.mem_write(CAM + 0x60, struct.pack('<3f', *(v + o for v, o in zip(direction, (10, 20, 30)))))
        e.call('test_aim_view', PLAYER)
        checks[f'invalid_camera_rejected_{i}'] = e.angles()[:2] == previous
    for i in range(100):
        e.call('test_aim_flags', PLAYER, i % 2, 1)
        e.call('test_aim_view', PLAYER)
    checks['final_toggle_enters_view'] = e.angles()[2] == 1
    e.call('test_aim_flags', PLAYER, 0, 1)
    e.call('test_aim_view', PLAYER)
    checks['final_release_clears_view'] = e.angles()[2] == 0
    checks['no_bowgun_camera_start_calls'] = e.camera_starts == 0
    failed = [n for n, good in checks.items() if not good]
    report = {'checks': checks, 'check_count': len(checks), 'failed': failed,
              'all_passed': not failed, 'scope': 'Compiled cursor/view plus real native GUI classification; synthetic actors/camera'}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / 'validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({n: report[n] for n in ('check_count', 'failed', 'all_passed', 'scope')}))
    assert not failed


if __name__ == '__main__': main()
