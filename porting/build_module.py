"""Build only the Magnet Spike code, without the upstream monster expansion.

The output stays in porting/output. This script never installs or launches it.
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

from prepare_frontier import CONVERTER, HERE, ROOT
from prepare_frontier import sha
from audit_inputs import audit
import hook_codegen

OUT = HERE / "output"
MOD = HERE / "module"
UPMOD = CONVERTER / "module"
MS = CONVERTER / "weapons/magnet_spike"
TOOLCHAIN = ROOT / "MHGURecomp-master/obj/toolchain/ucrt64/bin"


def symbols(elf):
    shoff = struct.unpack_from('<I', elf, 0x20)[0]
    shsize, count = struct.unpack_from('<HH', elf, 0x2e)
    sections = [struct.unpack_from('<10I', elf, shoff + shsize * i) for i in range(count)]
    out = {}
    for sec in sections:
        if sec[1] != 2:
            continue
        names = sections[sec[6]]
        names = elf[names[4]:names[4] + names[5]]
        for off in range(sec[4], sec[4] + sec[5], sec[9]):
            name, value, _, _, _, _ = struct.unpack_from('<IIIBBH', elf, off)
            end = names.find(b'\0', name)
            out[names[name:end].decode()] = value
    return out


def run(exe, *args):
    cmd = [str(TOOLCHAIN / (exe + '.exe')), *map(str, args)]
    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.stderr:
        print(result.stderr, end='', file=sys.stderr)
    if result.returncode:
        raise RuntimeError(f'{exe} failed: exit {result.returncode}')
    return result.stdout


def main():
    audit()
    if not (MS / 'gen/ms_data.inc').is_file():
        raise RuntimeError('Run build_assets.py --native-reticle first')
    sound_status = json.loads((HERE / 'sound-build.json').read_text(encoding='utf-8'))
    if sound_status.get('player_arc_sha256') != sha(MS / 'romfs/nativeNX/arc/player/quest/w05.arc'):
        raise RuntimeError('Run build_sounds.py after the asset build; sound resources are missing or stale')
    OUT.mkdir(parents=True, exist_ok=True)
    from build_hitstats import generate
    generate()
    from build_cancel_windows import generate as generate_windows
    generate_windows()
    from build_smithy_tree import generate as generate_tree
    tree = generate_tree()
    from build_balance import generate as generate_balance
    balance = generate_balance()
    os.environ['GOG_DEFINES'] = 'MS_SLICE MS_GS_TREE MS_RECOMP MS_BALANCE'
    os.environ['GU_CODE'] = str(HERE / 'work/gu_main')
    os.environ['GU_EXEFS'] = str(ROOT / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs')
    sys.path.insert(0, str(CONVERTER / 'tools'))
    spec = importlib.util.spec_from_file_location('upstream_module_build', UPMOD / 'build.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    img = (HERE / 'work/gu_main/mem.bin').read_bytes()
    hooks = [(name, site) for name, site in build.HOOKS
             if name.startswith('ms_') and name != 'ms_scope']
    hooks.append(('ms_local_text', 0xb83c48))
    hooks.append(('ms_local_file_id', 0x152960))
    hooks.append(('ms_local_hit_sound', 0x1802cc))
    hooks.extend([('ms_local_pin_ai',0xa5c40),('ms_local_pin_action',0x76154),('ms_local_pin_update',0xadb3c)])
    hooks.append(('ms_local_world_shape',0x169828))
    hooks.append(('ms_local_cancel_range',0x281388))
    hooks.append(('ms_tree_model_file',0x286ac0))
    hooks.append(('ms_tree_forge_count',0x162e0c))
    trampolines = []
    for name, site in hooks:
        if build.branch_into(img, site) is not None:
            raise RuntimeError(f'Branch targets the displaced word of {name}')
        trampolines.append(hook_codegen.trampoline(build, img, name, site))
    (OUT / 'hooks.inc').write_text('\n'.join(trampolines), encoding='utf-8')
    (OUT / 'layout.inc').write_text(f'    .equ MAIN_GAP, 0x{build.MAIN_GAP:x}\n', encoding='utf-8')
    includes = ['-I', str(OUT), '-I', str(UPMOD), '-I', str(MS / 'module'), '-I', str(MS / 'gen')]
    flags = build.CFLAGS + ['-DMS_SLICE', '-DMS_GS_TREE', '-DMS_RECOMP', '-DMS_BALANCE'] + includes
    sources = [UPMOD / 'crt0.S', UPMOD / 'util.c', MOD / 'local.c', MOD / 'sound.c', MOD / 'pin.c', MOD / 'hitstats.c', MOD / 'worldhits.c', MOD / 'cancel_windows.c', MOD / 'smithy.c', MS / 'module/ms_class.c', MS / 'module/ms_act.c']
    objects = []
    for source in sources:
        obj = OUT / (source.name + '.o')
        run('clang', *flags, '-c', source, '-o', obj)
        objects.append(obj)
    elf = OUT / 'magnet-spike.elf'
    win_source, win_obj = OUT / 'hookwin.S', OUT / 'hookwin.o'

    def link(entries, windows):
        win_source.write_text(build.hookwin_asm(entries, windows), encoding='utf-8')
        run('clang', *flags, '-c', win_source, '-o', win_obj)
        run('ld.lld', '-m', 'armelf_linux_eabi', '-shared', '-T', UPMOD / 'link.ld', '--hash-style=sysv', '-z', 'norelro',
            '-z', 'max-page-size=0x1000', '-init=module_init', '--no-undefined', '-o', elf, *objects, win_obj)
        return symbols(elf.read_bytes())

    windows = 1
    while True:
        syms = link([], windows)
        win = syms['__hookwin']
        entries, used = [], set()
        for name, site in hooks:
            offset = (site + 8 - build.MAIN_GAP - win) % build.HOOKWIN_SPAN
            while offset in used:
                offset += build.HOOKWIN_SPAN
            used.add(offset)
            entries.append((offset, name, site))
        if max(e[0] for e in entries) < windows * build.HOOKWIN_SPAN:
            break
        windows += 1
    final = link([(off, name) for off, name, _ in entries], windows)
    for name in ['__hookwin', *[n + '_tramp' for n, _ in hooks]]:
        if syms[name] != final[name]:
            raise RuntimeError('Hook layout moved during final link')
    moddir = OUT / 'magnet-spike-experimental'
    (moddir / 'exefs').mkdir(parents=True, exist_ok=True)
    (moddir / 'exefs/subsdk1').write_bytes(build.nso.elf2nso(elf.read_bytes()))
    records, touched = [], set()

    def record(site, data):
        if touched.intersection(range(site, site + len(data))):
            raise RuntimeError(f'Overlapping patch at {site:x}')
        touched.update(range(site, site + len(data)))
        records.append(struct.pack('>IH', site + 0x100, len(data)) + data)

    for offset, name, site in entries:
        delta = build.MAIN_GAP + win + offset - (site + 8)
        if delta % build.HOOKWIN_SPAN or not 0 < delta // build.HOOKWIN_SPAN < 256:
            raise RuntimeError(f'Unencodable hook {name}')
        record(site, struct.pack('<I', 0xe28ff700 | delta // build.HOOKWIN_SPAN))
    for lit, use, name in build.MS_LIT_PATCHES:
        old = struct.unpack_from('<I', img, lit)[0]
        delta = (use + 8 + old - build.MS_TABLES[name]) & 0xffffffff
        if delta > 0x10:
            raise RuntimeError(f'Unexpected original table reference at {lit:x}')
        new = (build.MAIN_GAP + final[name] + delta - (use + 8)) & 0xffffffff
        record(lit,struct.pack('<I',new))
    icon = json.loads((HERE/'reports/smithy-icon-build.json').read_text(encoding='utf-8'))
    if icon['output_arc_sha256'] != sha(MS/'romfs/nativeNX/eng/arc/resident_eng.arc'):
        raise RuntimeError('Prepare the isolated icon atlas before enabling its slot')
    for site, old, new in build.ms_patches(img):
        if struct.unpack_from('<I', img, site)[0] != old:
            raise RuntimeError(f'Unexpected original instruction at {site:x}')
        record(site, struct.pack('<I', new))
    # cEquipBoxData's sharpness-level getter (0xdb900) accepts only the native
    # melee equipment types. Type 12 otherwise returns zero before reading its
    # level row, capping every Magnet Spike at 150 points in hunter stat 0xe.
    # Add only bit 12, as the existing element getters do for the same new type.
    sharpness_site = 0xdb91c
    old = struct.unpack_from('<I', img, sharpness_site)[0]
    if old != 0xe30c2780:
        raise RuntimeError('Unexpected sharpness equipment-type mask')
    record(sharpness_site, struct.pack('<I', build.movw_imm(old, 0xd780)))
    (moddir / 'exefs' / (build.MAIN_BUILD_ID + '.ips')).write_bytes(b'IPS32' + b''.join(records) + b'EEOF')
    shutil.copytree(MS / 'romfs', moddir / 'romfs', dirs_exist_ok=True)
    (OUT / 'symbols.json').write_text(json.dumps(final, indent=2) + '\n', encoding='utf-8')
    (OUT / 'module-status.json').write_text(json.dumps({
        'status': 'experimental build; gameplay verification is recorded separately', 'hooks': len(hooks),
        'patch_records': len(records), 'weapon_count': tree['counts']['base']-1,
        'smithy_tree': True, 'balance_revision': balance['policy']['revision'],
        'sharpness_revision': 'sharpness-1',
        'balance_policy_sha256':balance['policy_sha256'],
        'full_port_complete': False}, indent=2) + '\n', encoding='utf-8')
    print(f'Built experimental smithy-tree module: {len(hooks)} hooks, {len(records)} verified patch sites.')


if __name__ == '__main__':
    main()
