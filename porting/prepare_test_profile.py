"""Create a disposable MHGU profile with one Magnet Spike equipped.

Never overwrite an existing profile or any original save. Save offsets are from
the pinned upstream installer/vendor/mhgu-save/src/{save,equipment}.rs.
"""
import hashlib
import json
import shutil
import struct
from prepare_frontier import HERE, ROOT

PROFILE = HERE / 'test-profile'
SOURCE = ROOT / 'MHGURecomp-master/build/couch-smoke/player1/save/save_0'
FILE_SIZE, SLOT_SIZE = 5159100, 0x11f8c4
BOX, WORN, SETS, ENTRY, BOX_COUNT = 0x62ee, 0x23b39, 0x208c8, 36, 2000


def edit_starter(original):
    if len(original) != FILE_SIZE:
        raise ValueError('Unsupported save size')
    bases = [0x24 + struct.unpack_from('<I', original, 0x34 + 4 * s)[0] for s in range(3)]
    if any(b < 0x40 or b + SLOT_SIZE > len(original) for b in bases):
        raise ValueError('Invalid character slot pointers')
    used = [s for s in range(3) if original[0x28 + s]]
    if not used:
        raise ValueError('No existing hunter in the source profile')
    slot = original[0x2b] if original[0x2b] in used else used[0]
    base = bases[slot]
    refs = set(struct.unpack_from('<7H', original, base + WORN))
    for i in range(40):
        refs.update(struct.unpack_from('<7H', original, base + SETS + i * 0x88 + 0x30))
    free = next((i for i in range(BOX_COUNT) if i not in refs and
                 not any(original[base + BOX + i * ENTRY:base + BOX + (i + 1) * ENTRY])), None)
    if free is None:
        raise ValueError('No unused equipment entry')
    modified = bytearray(original)
    at = base + BOX + free * ENTRY
    struct.pack_into('<HH', modified, at, 12, 1)
    struct.pack_into('<H', modified, base + WORN, free)
    allowed = set(range(at, at + 4)) | set(range(base + WORN, base + WORN + 2))
    changed = {i for i, (a, b) in enumerate(zip(original, modified)) if a != b}
    if not changed <= allowed or struct.unpack_from('<HH', modified, at) != (12, 1):
        raise AssertionError('Unexpected save modification')
    return modified, {'character_slot': slot + 1, 'box_index': free, 'changed_bytes': len(changed)}


def main():
    if PROFILE.exists():
        raise RuntimeError('Test profile already exists; it will not be overwritten')
    original = (SOURCE / 'system').read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    modified, result = edit_starter(original)
    target = PROFILE / 'save/save_0'
    target.mkdir(parents=True)
    for name in ('system', 'system_backup'):
        (target / name).write_bytes(modified)
    backup = HERE / 'backups/starter-source-system'
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists() and backup.read_bytes() != original:
        raise RuntimeError('Existing source backup differs')
    backup.write_bytes(original)
    shutil.copytree(HERE / 'output/magnet-spike-experimental', PROFILE / 'mods/magnet-spike-experimental')
    shutil.copyfile(ROOT / 'MHGURecomp-master/build/pipelines.list', PROFILE / 'pipelines.list')
    (PROFILE / 'mhgurecomp.ini').write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n', encoding='utf-8')
    if hashlib.sha256((SOURCE / 'system').read_bytes()).hexdigest() != digest:
        raise RuntimeError('Source save changed')
    result.update({'source_sha256': digest, 'source_unchanged': True,
                   'equipped_type': 12, 'equipped_id': 1, 'profile': str(PROFILE)})
    (HERE / 'starter-profile.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
