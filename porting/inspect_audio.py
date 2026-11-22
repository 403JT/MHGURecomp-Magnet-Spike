"""Emit structural metadata only; source tables and samples stay local."""
import collections
import json
import struct
from sound_env import *
from prepare_frontier import abn_parts, decode

def extract_model():
    work = HERE / 'work/sound'
    work.mkdir(parents=True, exist_ok=True)
    source = CLIENT / 'dat/extend/wk000snd.abn'
    decoded = work / 'wk000snd.abn.dec'
    decode([(source, decoded)])
    model = abn_parts(decoded.read_bytes())[400]
    packed = work / 'wk400.packed'
    packed.write_bytes(model)
    decode([(packed, work / 'wk400.snd')])
    return work / 'wk400.snd'

def main():
    model = extract_model()
    banks = {}
    for name, path in [('we13', CLIENT / 'dat/sound/we13.snd'), ('wk400', model)]:
        b = mhfsnd.parse(path.read_bytes())
        resolvable = [i for i in range(len(b['table'])) if mhfsnd.resolve(b, i)['vagi'] is not None]
        banks[name] = dict(waves=len(b['vagi']), requests=len(b['table']), resolvable=resolvable,
                           pitched=[i for i in resolvable if mhfsnd.resolve(b, i)['semitones']])
    data = (OUT / 'zz/mhfdat.dec.prefix.bin').read_bytes()
    candidates = {}
    for header in (0x61c,):
        p = struct.unpack_from('<I', data, header)[0]
        n, _, p = struct.unpack_from('<HHI', data, p + 14 * 8)
        counts, conds, weights = collections.Counter(), collections.Counter(), collections.Counter()
        total = 0
        if n > 1000:
            continue
        for i in range(n):
            motion, count, q = struct.unpack_from('<HHI', data, p + i * 8)
            if q + count * 22 > len(data):
                raise ValueError('Sound table out of bounds')
            for j in range(count):
                f, k, c, pad, *pairs = struct.unpack_from('<HHBB8H', data, q + 22 * j)
                counts[k] += 1; conds[k,c] += 1; total += 1
                if k in (3,4,6): weights[sum(w > 0 for w in pairs[1::2])] += 1
        candidates[hex(header)] = dict(motions=n, events=total, kinds=dict(counts),
                                      conditions={str(k):v for k,v in conds.items()}, weighted_choices=dict(weights))
    templates = {}
    for rel in ('weapon/w00/snd/001.arc','weapon/w00/snd/mat_b.arc'):
        es = entries(rel)
        b = snd.bank_parse(next(d for p,t,d in es if t == snd.TG['BANK']))
        req = snd.reqgu_parse(next(d for p,t,d in es if t == snd.TG['REQ']))
        templates[rel] = dict(waves=sum(t==snd.TG['WAVE'] for p,t,d in es), groups=len(b['recs']),
                             keys=[a[72] for p,t,a in b['ents']], requests=len(req['ents']))
    result = dict(banks=banks, tables=candidates, templates=templates)
    (HERE / 'reports/sound-inspection.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
