"""Muted native Glaive/reference and Magnet Spike aim captures on cloned saves."""
import argparse
import json
import math
import re
import struct
import time
from pathlib import Path
from feedback_session import Session
from prepare_frontier import HERE


class AimSession(Session):
    def absolute(self, address, size):
        self.samples += 1
        path = self.folder / f'memory-{self.samples}.bin'
        self.send(f'memsave {address:x} {size:x} {path.name}')
        self.wait(lambda: path.exists() and path.stat().st_size == size, 10)
        return path.read_bytes()

    def snapshot(self, name, native=False):
        p = self.absolute(self.player, 0x3400 if native else 0x3340)
        mgr = struct.unpack('<I', self.absolute(0x2326504, 4))[0]
        cam = struct.unpack('<I', self.absolute(mgr + 0x54, 4))[0] if mgr else 0
        block = self.absolute(cam, 0xae0) if cam else bytes(0xae0)
        v = struct.unpack_from('<3f', block, 0x40) + struct.unpack_from('<3f', block, 0x60)
        self.send('shot ' + name)
        # The path can appear before the PNG writer closes its Windows file
        # handle. The runtime's completion log is emitted after the write.
        self.wait(lambda: '[vk] saved shots/' + name + '.png' in self.log(), 10)
        row = {'name': name, 'category': struct.unpack_from('<H', p, 0x2506)[0],
               'action': struct.unpack_from('<H', p, 0x250a)[0], 'step': p[5],
               'hunter_yaw': struct.unpack_from('<H', p, 0xfec)[0],
               'position': list(struct.unpack_from('<3f', p, 0x40)),
               'aim_byte': p[0x2716], 'aim_pitch': struct.unpack_from('<h', p, 0x2714)[0],
               'camera': hex(cam), 'camera_aim': block[0xacc], 'camera_mode': block[0xac8],
               'eye': list(v[:3]), 'look_at': list(v[3:]), 'finite_camera': all(math.isfinite(x) for x in v)}
        if native: row['glaive_aim_scalar'] = struct.unpack_from('<f', p, 0x3348)[0]
        self.report['cases'].append(row)
        self.write()
        return row


def native_setup(save):
    from benchmark_balance import fixture
    _, gear = fixture(save, 13, 'low')
    return gear


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--payload', type=Path, required=True)
    parser.add_argument('--native-glaive', action='store_true')
    args = parser.parse_args()
    s = AimSession(args.label, payload_root=args.payload, save_setup=native_setup if args.native_glaive else None)
    try:
        s.wait(lambda: re.search(r'\[moves\] \d+ pl ([0-9a-f]+) is ', s.log()), 180)
        s.player = int(re.findall(r'\[moves\] \d+ pl ([0-9a-f]+) is ', s.log())[-1], 16)
        time.sleep(7)
        s.send('X 8')
        time.sleep(3)
        s.snapshot('neutral', args.native_glaive)
        for button in ('ZR', 'R') if args.native_glaive else ('ZR',):
            s.send(button + ' 240')
            time.sleep(1)
            s.snapshot(button.lower() + '-aim', args.native_glaive)
            s.send('RSTICK_RIGHT 30')
            time.sleep(.7)
            s.snapshot(button.lower() + '-right', args.native_glaive)
            time.sleep(3)
            s.snapshot(button.lower() + '-released', args.native_glaive)
        assert all(c['finite_camera'] for c in s.report['cases'])
    except Exception as exc:
        s.report['failure'] = str(exc)
        raise
    finally:
        s.close()
    print(json.dumps({'run': args.label, 'cases': s.report['cases'], 'exit_code': s.report['exit_code']}))


if __name__ == '__main__': main()
