"""Independently verify combined source scope and rebuild motion lists in memory."""
import ast
import hashlib
import json
import os
import struct
import sys
import zlib
from pathlib import Path
from build_module import HERE, MS, UPMOD
from feedback_session import files
from prepare_combined_release import STAGE, BASE, WEAPON, TOOLS, read

sys.dont_write_bytecode = True


def arc(data):
    assert data[:4] == b'ARC\0'
    out = []
    for i in range(struct.unpack_from('<H', data, 6)[0]):
        name, typ, size, unpacked, offset = struct.unpack_from('<64s4I', data, 12 + 80 * i)
        raw = zlib.decompress(data[offset:offset + size])
        assert len(raw) == unpacked & 0x1fffffff
        out.append((name.split(b'\0')[0].decode('ascii'), typ, raw))
    return out


def slots(data):
    assert data[:4] == b'LMT\0' and struct.unpack_from('<H', data, 4)[0] == 67
    result, lengths = {}, {}
    for slot in range(struct.unpack_from('<H', data, 6)[0]):
        at = struct.unpack_from('<I', data, 8 + 4 * slot)[0]
        if not at: continue
        track, count, frames, loop = struct.unpack_from('<IIIi', data, at)
        values = [data[at + 8:at + 0x34], data[at + 0x38:at + 0x40]]
        for k in range(count):
            t = track + k * 0x24
            size, buf = struct.unpack_from('<II', data, t + 8)
            bound = struct.unpack_from('<I', data, t + 32)[0]
            values.extend((data[t:t + 12], data[t + 16:t + 32], data[buf:buf + size] if buf else b'',
                           data[bound:bound + 32] if bound else b''))
        event = struct.unpack_from('<I', data, at + 0x34)[0]
        if event:
            for group in range(4):
                e = event + 0x48 * group
                n, p = struct.unpack_from('<II', data, e + 0x40)
                values.extend((data[e:e + 0x44], data[p:p + 8 * n]))
        result[slot], lengths[slot] = tuple(values), frames
    return result, lengths


def main():
    base, inputs, build = [read(STAGE / n) for n in ('baseline.json', 'inputs.json', 'build-validation.json')]
    merged = STAGE / 'source/porting'
    originals = BASE / 'repo/porting'
    checks = {}
    for name in ('ms.h', 'ms_act.c', 'ms_class.c'):
        assert (merged / WEAPON / 'module' / name).read_bytes() == (STAGE / 'inputs/aim/source').glob('*').__iter__().__next__().joinpath('porting', WEAPON, 'module', name).read_bytes()
    checks['all_aim_source_exact_original_aim_release'] = True
    name_root = next((STAGE / 'inputs/names/source').iterdir())
    checks['all_name_source_exact_name_release'] = (merged / 'module/smithy.c').read_bytes() == (name_root / 'porting/module/smithy.c').read_bytes()
    for name in ('msbuild.py', 'msfx.py', 'msmot.py'):
        assert (merged / TOOLS / name).read_bytes() == (STAGE / 'inputs/motions/source/porting' / TOOLS / name).read_bytes()
    checks['all_motion_converter_source_exact_alpha4'] = True
    expected_changes = {'module/smithy.c', *[str(WEAPON / 'module' / n).replace('\\', '/') for n in ('ms.h', 'ms_act.c', 'ms_class.c')],
                        *[str(TOOLS / n).replace('\\', '/') for n in ('msbuild.py', 'msfx.py', 'msmot.py')]}
    actual_changes = set()
    for folder in ('module', str(WEAPON / 'module'), str(TOOLS)):
        for p in (merged / folder).iterdir():
            if not p.is_file(): continue
            old = originals / p.relative_to(merged)
            assert old.is_file()
            if p.read_bytes() != old.read_bytes(): actual_changes.add(p.relative_to(merged).as_posix())
    assert actual_changes == expected_changes, actual_changes
    checks['production_source_changes_exactly_seven_expected_files'] = True
    assert files(STAGE / 'output/magnet-spike-experimental') == build['payload_files']
    assert all(build['payload_files'][n] == h for n, h in inputs['motion_payload'].items() if n.startswith('romfs/'))
    checks['all_54_assets_exact_supplied_alpha4'] = True
    lists, scope = {}, {}
    for rel in base['motion_changed_assets']:
        before = arc((STAGE / 'inputs/aim/mod/Magnet-Spike' / rel).read_bytes())
        after = arc((STAGE / 'output/magnet-spike-experimental' / rel).read_bytes())
        assert [(p, t) for p, t, _ in before] == [(p, t) for p, t, _ in after]
        diff = [(a, b) for a, b in zip(before, after) if a[2] != b[2]]
        assert len(diff) == 1
        a, b = diff[0]
        x, xf = slots(a[2]); y, yf = slots(b[2])
        assert x.keys() == y.keys()
        changed = [k for k in x if x[k] != y[k]]
        assert changed == [46, 49, 78, 135]
        assert {k: yf[k] for k in changed} == {46: 45, 49: 47, 78: 49, 135: 27}
        assert all(xf[k] == 1 for k in changed)
        kind = 'body' if '/player/' in rel else 'weapon'
        lists[kind] = (a[2], b[2])
        scope[kind] = {'slots_compared': len(x), 'changed_slots': changed, 'members_compared': len(before),
                       'changed_member': a[0], 'frames_after': {k: yf[k] for k in changed}}
    checks['only_four_expected_motion_slots_change_one_member_per_archive'] = True
    os.environ['GU_ROMFS'] = str(HERE.parent / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs')
    os.environ['GU_EXEFS'] = str(HERE.parent / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs')
    os.environ['GU_CODE'] = str(HERE / 'work/gu_main')
    sys.path[:0] = [str(MS / 'tools'), str(MS.parents[1] / 'tools')]
    import msbuild, msmot, msfx, msact
    dat = (Path(msbuild.MHF) / 'zz/mhfdat.dec.bin').read_bytes()
    acts, modes = msact.actions(dat), msact.modes(dat)
    def prepare():
        msbuild.MODES.update(modes)
        msbuild.ACTIONS[:] = [i for i, a in enumerate(acts) if a['steps'] and all(k <= 2 or m // 1000 == 1 for k, m, *_ in a['steps'])]
        return msbuild.slot_plan(acts)[0]
    plan = prepare()
    gs = msbuild.gu_arc('player/quest/w00.arc')['player\\mot\\w00\\w00'][1]
    print('Rebuilding baseline and merged motion lists in memory...', flush=True)
    old_body, old_weapon, *_ = msbuild.build_motions(plan, gs)
    assert (old_body, old_weapon) == (lists['body'][0], lists['weapon'][0])
    for module, name in ((msmot, 'msmot.py'), (msfx, 'msfx.py'), (msbuild, 'msbuild.py')):
        source = (merged / TOOLS / name).read_text(encoding='utf-8')
        # The shared input paths stay in this process's existing __file__;
        # only the copied source is executed. main() is never invoked.
        exec(compile(source, str(merged / TOOLS / name), 'exec'), vars(module))
    plan = prepare()
    new_body, new_weapon, *_ = msbuild.build_motions(plan, gs)
    assert (new_body, new_weapon) == (lists['body'][1], lists['weapon'][1])
    msbuild.check_frame_waits(acts)
    saved = msbuild.MOTION_FRAMES[1426]
    msbuild.MOTION_FRAMES[1426] = 1
    rejected = False
    try: msbuild.check_frame_waits(acts)
    except AssertionError: rejected = True
    finally: msbuild.MOTION_FRAMES[1426] = saved
    assert rejected
    checks['baseline_motion_lists_reproduced_byte_for_byte'] = True
    checks['merged_converter_reproduces_exact_alpha4_motion_lists'] = True
    checks['frame_wait_guard_passes_valid_data_rejects_original_stall'] = True
    checks['normal_output_preserved'] = files(HERE / 'output/magnet-spike-experimental') == base['normal_payload']
    assert all(checks.values()), checks
    report = {'all_passed': True, 'checks': checks, 'motion_scope': scope,
              'production_changes': sorted(actual_changes), 'payload_files': build['payload_files']}
    (STAGE / 'scope-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'all_passed': True, 'checks': checks, 'motion_scope': scope}))


if __name__ == '__main__': main()
