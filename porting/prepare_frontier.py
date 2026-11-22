"""Decode the supplied client into the pinned converter's ignored input directory.

Original files are read only. The manifest records their hashes for verification.
Run using porting/.venv/Scripts/python.exe from any working directory.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REV = "209959bcf08f9d54be25b92ba8b6346d70cd57d8"
CONVERTER = HERE / "third_party" / ("MHGU-Definitive-Edition-" + REV)
CLIENT = ROOT / "MHFZZ" / "Monster Hunter Frontier - Full Game + Rain patch installed + English patch"
OUT = CONVERTER / "dump" / "mhf"
WORK = HERE / "work"


def sha(path: Path) -> str:
    return hashlib.file_digest(path.open("rb"), "sha256").hexdigest()


def decode(jobs: list[tuple[Path, Path]]) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    jobfile = WORK / "decode-jobs.json"
    jobfile.write_text(json.dumps([{"input": str(a), "output": str(b),
                                   "diagnosticPrefix": a.name == "mhfdat.bin"}
                                  for a, b in jobs]), encoding="utf-8")
    subprocess.run([shutil.which("pwsh") or "powershell", "-NoProfile", "-File",
                    str(HERE / "codec" / "decode.ps1"), "-Jobs", str(jobfile)], check=True)


def parts(data: bytes) -> list[bytes]:
    if len(data) < 4:
        raise ValueError("Container header is truncated")
    count, = struct.unpack_from("<I", data)
    if not 0 < count <= 10000 or 4 + count * 8 > len(data):
        raise ValueError("Invalid container directory")
    out = []
    for index in range(count):
        offset, size = struct.unpack_from("<II", data, 4 + index * 8)
        if size and (offset < 4 + count * 8 or offset + size > len(data)):
            raise ValueError(f"Container entry {index} is out of bounds")
        out.append(data[offset:offset + size] if size else b"")
    return out


def save(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def abn_parts(data: bytes) -> dict[int, bytes]:
    """ABN directory is at the end: 20-byte entries include a stable model ID."""
    directory, count = struct.unpack_from("<II", data, 4)
    if not 0 < count <= 1000 or directory + count * 20 != len(data):
        raise ValueError("Unsupported ABN directory shape")
    out = {}
    for i in range(count):
        _, offset, size, padded, number = struct.unpack_from("<5I", data, directory + 20 * i)
        if offset < 24 or size > padded or offset + padded > directory or number in out:
            raise ValueError("Invalid ABN entry")
        out[number] = data[offset:offset + size]
    return out


def main() -> None:
    relative = ["motion/w13.mot", "motion/w13w.mot", "mhfdat.bin", "mhfsdt.bin", "effect.bin",
                "mhf_90c.bin.xbox", "parts/m00/m_editpl.bin", "extend/wk000.abn", "extend/wk500.abn"]
    inputs = [CLIENT / "dat" / name for name in relative]
    before = {str(p.relative_to(ROOT)): sha(p) for p in inputs}
    initial = [(p, WORK / (name.replace("/", "_") + ".decoded")) for p, name in zip(inputs, relative)]
    decode(initial)
    decoded = {name: path.read_bytes() for (_, path), name in zip(initial, relative)}
    for name, dest in [("motion/w13.mot", "motion/w13.aan"), ("motion/w13w.mot", "motion/w13w.aan"),
                       ("mhfdat.bin", "zz/mhfdat.dec.prefix.bin"), ("mhfsdt.bin", "zz/mhfsdt.dec.bin"),
                       ("effect.bin", "effect/effect.bin.dec")]:
        save(OUT / dest, decoded[name])

    nested = []
    def nested_job(data: bytes, dest: Path) -> None:
        raw = WORK / "packed" / (str(len(nested)) + ".bin")
        save(raw, data)
        nested.append((raw, dest))

    body = parts(decoded["parts/m00/m_editpl.bin"])
    print(f"Player container: {len(body)} parts", flush=True)
    for i, dest in [(0, "player/m_editpl.0.bin"), (1, "player/m_editpl.fskl")]:
        nested_job(body[i], OUT / dest)
    for base in (0, 500):
        archive = abn_parts(decoded[f"extend/wk{base:03d}.abn"])
        print(f"Weapon archive {base}: {len(archive)} entries", flush=True)
        for number in (400, 404, 407, 414, 415, 595, 606):
            if number not in archive:
                continue
            nested_job(archive[number], WORK / f"wk{number}.container")
    effect = parts(decoded["effect.bin"])
    nested_job(effect[18], OUT / "effect/sets.bin")
    nested_job(effect[0], WORK / "effect-models.container")
    nested_job(decoded["mhf_90c.bin.xbox"], WORK / "ui.container")
    decode(nested)

    final = []
    for number in (400, 404, 407, 414, 415, 595, 606):
        model = parts((WORK / f"wk{number}.container").read_bytes())
        if len(model) < 3:
            raise ValueError(f"wk{number} does not have model, skeleton and texture")
        for i, ext in enumerate(("fmod", "fskl", "tex")):
            raw = WORK / f"wk{number}-{i}.packed"
            save(raw, model[i])
            final.append((raw, OUT / f"weapon/wk{number}/{i}.{ext}"))
    effect_model = parts((WORK / "effect-models.container").read_bytes())
    raw = WORK / "effect-model0.packed"
    save(raw, effect_model[0])
    final.append((raw, OUT / "effect/model0.fmod"))
    decode(final)

    # Locate complete PNG streams by PNG chunk boundaries, checking every chunk CRC.
    import zlib
    ui = (WORK / "ui.container").read_bytes()
    pngs, cursor = [], 0
    while (start := ui.find(b"\x89PNG\r\n\x1a\n", cursor)) >= 0:
        at = start + 8
        while True:
            size, = struct.unpack_from(">I", ui, at)
            end = at + 12 + size
            if end > len(ui):
                raise ValueError("PNG chunk exceeds UI container")
            kind = ui[at + 4:at + 8]
            crc, = struct.unpack_from(">I", ui, at + 8 + size)
            if zlib.crc32(ui[at + 4:at + 8 + size]) != crc:
                raise ValueError("UI PNG CRC mismatch")
            at = end
            if kind == b"IEND":
                break
        pngs.append(ui[start:at])
        cursor = at
    save(OUT / "ui/mhf_90c_04.png", pngs[4])
    if before != {str(p.relative_to(ROOT)): sha(p) for p in inputs}:
        raise RuntimeError("Source files changed during extraction")
    manifest = {"converter_revision": REV, "source_sha256": before,
                "outputs": {str(p.relative_to(OUT)): {"bytes": p.stat().st_size, "sha256": sha(p)}
                            for p in sorted(OUT.rglob("*")) if p.is_file()}}
    (HERE / "extraction-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Extracted {len(manifest['outputs'])} files; all original hashes unchanged.", flush=True)


if __name__ == "__main__":
    main()
