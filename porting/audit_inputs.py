"""Check the exact source spans used for Magnet Spike conversion; print metadata only."""
from pathlib import Path
import hashlib
import json
import struct
import sys

from prepare_frontier import CONVERTER, HERE, OUT, ROOT


def audit():
    dat = (OUT / "zz/mhfdat.dec.prefix.bin").read_bytes()
    spans = []

    def span(offset, size, label):
        if offset < 0 or size < 0 or offset + size > len(dat):
            raise ValueError(f"Unavailable data in {label}")
        spans.append((offset, offset + size, label))

    def u32(offset):
        span(offset, 4, "pointer")
        return struct.unpack_from("<I", dat, offset)[0]

    actions = u32(0x614)
    span(actions, 14 * 8, "weapon action directory")
    count, records = struct.unpack_from("<iI", dat, actions + 13 * 8)
    if count != 165:
        raise ValueError(f"Unexpected Magnet Spike action count: {count}")
    span(records, count * 24, "action records")
    for i in range(count):
        ns, ps, nc, pc, ne, pe = struct.unpack_from("<6I", dat, records + i * 24)
        if ns > 64 or nc > 1000 or ne > 1000:
            raise ValueError(f"Implausible action {i}")
        for n, p, stride, label in ((ns, ps, 12, "steps"), (nc, pc, 40, "cancels"), (ne, pe, 12, "events")):
            span(p, n * stride, f"action {i} {label}")
    modes = u32(0xb90)
    span(modes, 0x24, "mode header")
    for co, po in ((2, 0x18), (4, 0x1c), (6, 0x20)):
        n, = struct.unpack_from("<h", dat, modes + co)
        span(u32(modes + po), n * 2, "mode assignments")
    effects = u32(0x618)
    span(effects, 14 * 8, "motion effect directory")
    n, ptr = struct.unpack_from("<iI", dat, effects + 13 * 8)
    if not 0 < n < 1000:
        raise ValueError("Implausible motion effect count")
    span(ptr, n * 8, "motion effect entries")
    for i in range(n):
        _, k, p = struct.unpack_from("<HHI", dat, ptr + i * 8)
        span(p, k * 16, "motion effect keys")
    sys.path.insert(0, str(CONVERTER / "weapons/magnet_spike/tools"))
    import aan, fmod, fskl, msact, msfxposts, sdt
    acts = msact.actions(dat)
    active = [a for a, r in enumerate(acts) if r["steps"] and all(
        k in (0, 1, 2) or m // 1000 == 1 for k, m, *_ in r["steps"])]
    if len(active) != 160:
        raise ValueError("Unexpected active moveset")
    body = aan.parse((OUT / "motion/w13.aan").read_bytes())
    weapon = aan.parse((OUT / "motion/w13w.aan").read_bytes())
    meshes = fmod.parse((OUT / "weapon/wk400/0.fmod").read_bytes())
    bones = fskl.parse((OUT / "weapon/wk400/1.fskl").read_bytes())[1]
    hit = (OUT / "zz/mhfsdt.dec.bin").read_bytes()
    entries = sdt.entries(hit)
    for kind in (0x78, 0x79):
        row = next(e for e in entries if e["kind"] == kind)
        sdt.attacks(hit, row)
        sdt.shape_sets(hit, row)
    game = ROOT / "MHGURecomp.0.14.0/Windows-MHGURecomp/data"
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    main_hash = sha(game / "exefs/main")
    if main_hash != "b3935415499549adaf4c0e89822831daa175cfd456a7990791c79be3997645ef":
        raise ValueError("MHGU executable does not match the port's 1.4 target")
    result = {"mhgu_main_sha256": main_hash, "frontier_table_status": "decoded prefix; 10 declared tail bytes absent",
              "decoded_prefix_bytes": len(dat), "highest_moveset_reference_end": max(s[1] for s in spans),
              "all_moveset_references_available": True, "active_actions": len(active),
              "steps": sum(len(a["steps"]) for a in acts), "cancels": sum(len(a["cancels"]) for a in acts),
              "events": sum(len(a["events"]) for a in acts), "effect_posts": len(msfxposts.motion_keys(dat)),
              "body_tracks": sum(len(p) for p in body), "weapon_tracks": sum(len(p) for p in weapon),
              "weapon_meshes": len(meshes), "weapon_bones": len(bones), "runtime_verified": False}
    (HERE / "input-audit.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(audit(), indent=2))
