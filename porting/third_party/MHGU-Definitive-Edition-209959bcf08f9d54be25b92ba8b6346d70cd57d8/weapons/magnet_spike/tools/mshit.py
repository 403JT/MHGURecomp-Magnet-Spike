"""mshit.py : Magnet Spike hit data for MHGU: player\\hit\\pl_we05_hitdata (HDP) and pl_we05_hitsize (HTS), from MHF's
attack records (dat/mhfsdt.bin kind 0x78, tools/sdt.py) and the weapon poses at each attack's frame.

GU formats (C, notes/gu-weapon-class.md "Hit data"; reader 0x168960):
  HDP: 16-byte header ('HDP\\0', u32 version, u32 count, u32 reserved), then count x 56 B (28 i16).
       GU's loader 0x270d18..28 points data at file+0x10; getter 0x270d98 uses stride 0x38.
       [0] start delay, [1] live frames, [2] attack power byte (<=250), [6] damage type (1 impact,2 cut),
       [16] low byte = hit-shape set, [20..23] two float multipliers, [24] full motion value.
       The old 12-byte reader shifted template indices and wrote shape IDs into a multiplier field;
       it also left the last native record four bytes beyond the serialized file.
       The other fields come from a GU template entry of the same damage type (GS 1 for cut, Hammer 3 for impact).
  HTS: 'HTS\\0', u32 0x20131015, u32 set count, u32 0, count x {u32 shape count, u32 offset}, shapes 48 B:
       u16 joint A, u16 joint B (player joints: 8 right hand, 12 left hand, 255 root), u16 type (1 = capsule),
       u16 flag, f32, f32 radius, vec4 A, vec4 B (cm, in the joint's frame).
MHF (C): an ATTACK event arms its attack at the event frame for raw[1] frames (MV raw[2], type raw[7] 0x20a cut /
0x10a impact, KO raw[16] / 256, shape set raw[8]); its shapes sit on weapon bones (5 / 7 blades, 4 head; flag 8) or
around the hunter (flag 0). GU shapes sit on player joints only, so each weapon shape is placed in the holding hand's
frame (GU 8 or 12, msgrip) from the weapon motion's pose at the middle of the live window, one HTS set per attack
event (the same MHF attack posed by different motions differs).
The standalone module applies source KO after native arming; exhaust and other untouched fields use the template.

Library: hdp_entry(template, mv, dur, cut, shape), hts_bytes(sets), hdp_bytes(entries)."""
import struct

HDP_VERSION, HTS_VERSION = 0x20160209, 0x20131015
CUT, IMPACT = 2, 1


def hdp_parse(d):
    magic, ver, n = struct.unpack_from('<4sII', d, 0)
    if magic!=b'HDP\0' or ver!=HDP_VERSION or len(d)<16+56*n:
        raise ValueError('HDP header/version/record span is invalid')
    # GU 270d18..28 sets resource+68 to file+10; 270d98 uses stride38.
    return [list(struct.unpack_from('<28h', d, 16 + 56 * i)) for i in range(n)]


def hdp_bytes(entries):
    out = struct.pack('<4sIII', b'HDP\0', HDP_VERSION, len(entries),0)
    for e in entries:
        out += struct.pack('<28h', *e)
    return out


def hdp_entry(template, mv, dur, kind, shape, ko=None):
    """A native GU entry: live now for dur frames, source MV/type and converted shape set.
    ko is retained for caller compatibility; the standalone module applies source KO after native arming."""
    e = list(template)
    e[0], e[1] = 0, dur             # Native constructor: delay +0, life +2.
    e[2] = min(mv, 250)             # Native attack-power byte from +4.
    e[6] = kind                    # Native damage type at +0xc.
    e[16] = (e[16] & ~0xff) | shape
    e[24] = mv                     # Full motion value at +0x30.
    return e


def hts_parse(d):
    _, ver, n, _ = struct.unpack_from('<IIII', d, 0)
    sets = []
    for i in range(n):
        cnt, off = struct.unpack_from('<II', d, 16 + 8 * i)
        sets.append([struct.unpack_from('<4H2f4f4f', d, off + 48 * k) for k in range(cnt)])
    return sets


def capsule(joint, radius, a, b):
    """one capsule shape in a joint's frame (GS's header: type 1, flag 1)"""
    return (joint, joint, 1, 1, 0.0, radius, a[0], a[1], a[2], 0.0, b[0], b[1], b[2], 0.0)


def hts_bytes(sets):
    head = struct.pack('<4sIII', b'HTS\0', HTS_VERSION, len(sets), 0)
    table, body = b'', b''
    base = 16 + 8 * len(sets)
    for s in sets:
        table += struct.pack('<II', len(s), base + len(body) if s else 0)
        for sh in s:
            body += struct.pack('<4H2f4f4f', *sh)
    return head + table + body
