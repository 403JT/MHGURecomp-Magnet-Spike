"""Convert only the supplied starter's sounds. Game data remains in ignored/local outputs."""
import collections
import ctypes
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import zlib
import numpy as np
import soundfile as sf
from sound_env import *
from prepare_frontier import sha
import msbuild

WORK = HERE / 'work/sound'
GEN = HERE / 'output'
ASSETS = CONVERTER / 'weapons/magnet_spike/romfs/nativeNX/arc'
BASE = 512
# Local mix calibration: Frontier's normalised shock/finisher layers overlapped
# into full scale in GU (captured in sound-combat-final). These are explicit
# output trims, separate from the unmodified source gain-chain interpretation.
CLASS_MIX_TRIM_DB={5:-6.0,23:-6.0,26:-4.0,27:-6.0}
# Repeated ordinary attack layers also overlap at full scale in the extended
# Magnetise test. Reserve headroom for every converted weapon voice in GU's mix.
WEAPON_HEADROOM_DB=-3.0
MODEL_PATH = r'sound\se\pl\wp\ms\snd_ms_wk400'
CLASS_PATH = r'sound\se\pl\wp\ms\snd_ms_we13'

def encoder():
    toolchain = ROOT / 'MHGURecomp-master/obj/toolchain/ucrt64/bin'
    dll = WORK / 'ms_dsp.dll'
    subprocess.run([str(toolchain / 'clang.exe'), '-O2', '-shared',
                    str(HERE / 'codec/dsp_encode.c'), str(HERE / 'third_party/gc-dspadpcm-encode/grok.c'),
                    '-o', str(dll)], check=True, capture_output=True)
    lib = ctypes.CDLL(str(dll))
    f = lib.ms_dsp_encode
    f.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
    f.restype = ctypes.c_int
    return f

def encoded_wave(pcm, rate, encode):
    pcm = np.ascontiguousarray(pcm, dtype='<i2')
    coefs = np.zeros(16, dtype='<i2')
    packed = np.zeros(((len(pcm)+13)//14)*8, dtype=np.uint8)
    if encode(pcm.ctypes.data, len(pcm), coefs.ctypes.data, packed.ctypes.data):
        raise RuntimeError('DSP encoding failed')
    data = packed.tobytes()[:snd.dsp_data_bytes(len(pcm))]
    wave = snd.gu_wave(dict(samples=len(pcm), rate=rate, coefs=coefs, data=data, flags=b'\x01\0\0\x01'))
    parsed = snd.gu_wave_parse(wave)
    back = np.asarray(snd.dsp_decode(parsed['data'], parsed['coefs'], parsed['samples']), dtype=np.float64)
    source = pcm.astype(np.float64)
    energy = np.sum(source * source); error = np.sum((source-back)**2)
    snr = 10*math.log10(energy/error) if energy and error else None
    if len(back) != len(pcm) or (snr is not None and snr < 20):
        raise RuntimeError(f'Unacceptable DSP round trip: {snr}')
    return wave, dict(samples=len(pcm), rate=rate, snr_db=snr,
                      peak_error=int(np.max(np.abs(source-back))))

def request_bytes(template, rows, bank_paths):
    n = len(rows); stab = 0x34 + 132*n
    blob = bytearray(); offsets = []
    for path in bank_paths:
        offsets.append(stab + 4*len(bank_paths) + len(blob))
        blob += path.encode('ascii') + b'\0'
    end = (stab + len(offsets)*4 + len(blob) + 15)//16*16
    hdr = struct.pack('<4s2I', b'SRQR', 5, n) + template[0x0c:0x20] + struct.pack('<5I',stab,end,end,end,end)
    body = hdr + b''.join(struct.pack('<33I', *r) for r in rows) + struct.pack('<%dI'%len(offsets),*offsets) + blob
    return body + bytes(end-len(body))

def make_bank(name, source, donor_rel, target, encode, report):
    bank = mhfsnd.parse(source.read_bytes())
    whole, rate = sf.read(io.BytesIO(bank['bd']), dtype='int16')
    if whole.ndim != 1 or rate != 48000:
        raise ValueError('Unexpected Frontier sound format')
    donor = entries(donor_rel)
    original_bank_path, _, original_bank = next(e for e in donor if e[1] == snd.TG['BANK'])
    _, _, original_req = next(e for e in donor if e[1] == snd.TG['REQ'])
    tb = snd.bank_parse(original_bank)
    tr = snd.reqgu_parse(original_req)
    # Native draw/sheath/hit requests remain available in a separately named fallback bank.
    fallback = target + '_gu'
    renamed = {p: target + '_g' + str(i) for i,(p,t,d) in enumerate(donor) if t==snd.TG['WAVE']}
    es = [(renamed[p],t,d) for p,t,d in donor if t==snd.TG['WAVE']]
    b = struct.pack('<4s4I',b'SBKR',4,len(tb['recs']),len(tb['ents']),tb['x'])
    b += b''.join(struct.pack('<HHII',*r) for r in tb['recs'])
    for p,t,a in tb['ents']:
        b += renamed.get(p,p).encode('ascii') + b'\0' + struct.pack('<I',t) + a
    b += tb['tail_raw']
    es.append((fallback,snd.TG['BANK'],b))
    # Use the verified, non-looping model request for ALL new one-shot sounds.
    # Common-bank request 50 has guard-specific routing/flags; copying those
    # suppressed the class sounds even though the resource loaded successfully.
    one_shot = entries('weapon/w00/snd/001.arc')
    tone_template = snd.bank_parse(next(d for p,t,d in one_shot if t==snd.TG['BANK']))
    request_template = snd.reqgu_parse(next(d for p,t,d in one_shot if t==snd.TG['REQ']))
    template_ent = tone_template['ents'][0][2]
    template_req = next(w for w in request_template['ents'] if w[0]&65535 == 1)
    converted = {}; wave_stats = []
    for i,v in enumerate(bank['vagi']):
        if v['start'] + v['samples'] > len(whole) or v['rate'] != rate or v['odd']:
            raise ValueError('Frontier wave slice is invalid')
        pcm = whole[v['start']:v['start']+v['samples']]
        wav, stats = encoded_wave(pcm, rate, encode)
        path = target + '_w%02d'%i
        converted[i] = path
        es.append((path,snd.TG['WAVE'],wav))
        wave_stats.append(stats)
    own = []; requests = list(tr['ents']); valid = set(); gain_stats = []
    for i in range(len(bank['table'])):
        r = mhfsnd.resolve(bank,i)
        if r['vagi'] is None: continue
        if r['semitones'] or r['rvol']:
            raise ValueError('Unimplemented pitch/volume transformation')
        gain = math.prod(x/127 for x in (r['vol'],r['tvol'],r['svol'],bank['programs'][r['prog']]['vol']))
        if gain <= 0: continue
        a = bytearray(template_ent)
        a[5] = 127
        a[72:76] = bytes((i,i,0,0))
        own.append((converted[r['vagi']],snd.TG['WAVE'],bytes(a)))
        words = list(template_req)
        words[0] = (words[0]&0xff000000) | (i<<16) | (BASE+i)
        source_db=20*math.log10(gain)
        trim=CLASS_MIX_TRIM_DB.get(i,0.0) if name=='we13' else 0.0
        output_db=source_db+trim+WEAPON_HEADROOM_DB
        words[9] = words[10] = struct.unpack('<I',struct.pack('<f',output_db))[0]
        words[21] = 1
        requests.append(tuple(words)); valid.add(i)
        gain_stats.append(dict(request=i,source_db=source_db,mix_trim_db=trim,
                               headroom_db=WEAPON_HEADROOM_DB,db=output_db))
    own_path = target + '_src'
    b = struct.pack('<4s4I',b'SBKR',4,1,len(own),tone_template['x'])
    b += struct.pack('<HHII',tone_template['recs'][0][0],0x800|2*len(own),0,tone_template['recs'][0][3])
    for p,t,a in own:
        b += p.encode('ascii')+b'\0'+struct.pack('<I',t)+a
    b += tone_template['tail_raw']
    es += [(own_path,snd.TG['BANK'],b),
           (target,snd.TG['REQ'],request_bytes(original_req,requests,[fallback,own_path]))]
    report[name] = dict(input_sha256=sha(source), waves=wave_stats, requests=len(valid),
                        gains=gain_stats, uncompressed_bytes=sum(len(d) for p,t,d in es))
    return es, valid

def sound_rows(data):
    def span(off,size):
        if off<0 or size<0 or off+size>len(data): raise ValueError('Sound table exceeds decoded prefix')
        return off
    p = struct.unpack_from('<I',data,0x61c)[0]
    n,_,p = struct.unpack_from('<HHI',data,span(p+14*8,8))
    if not 1<=n<=512: raise ValueError('Invalid motion sound directory')
    out = []
    for i in range(n):
        mot,count,q = struct.unpack_from('<HHI',data,span(p+i*8,8))
        span(q,count*22)
        for j in range(count):
            f,kind,condition,pad,*pairs=struct.unpack_from('<HHBB8H',data,q+j*22)
            out.append((mot,f,kind,condition,list(zip(pairs[::2],pairs[1::2]))))
    return out

def main():
    WORK.mkdir(parents=True,exist_ok=True); GEN.mkdir(exist_ok=True)
    source_paths=[CLIENT/'dat/sound/we13.snd',CLIENT/'dat/extend/wk000snd.abn']
    before={str(p.relative_to(ROOT)):sha(p) for p in source_paths}
    from inspect_audio import extract_model
    extract_model()
    encode=encoder(); report={}
    model,model_valid=make_bank('wk400',WORK/'wk400.snd','weapon/w00/snd/001.arc',MODEL_PATH,encode,report)
    common,class_valid=make_bank('we13',source_paths[0],'weapon/w00/snd/mat_b.arc',CLASS_PATH,encode,report)
    data=(OUT/'zz/mhfdat.dec.prefix.bin').read_bytes()
    acts=msbuild.msact.actions(data)
    msbuild.ACTIONS[:] = [a for a,r in enumerate(acts) if r['steps'] and all(
        k in (0,1,2) or m//1000==1 for k,m,*_ in r['steps'])]
    plan,own=msbuild.slot_plan(acts)
    motion_slots=collections.defaultdict(set)
    for slot,mot in plan.items():
        if slot not in msbuild.GU_COPY: motion_slots[mot].add(slot)
    events=[]; unresolved=collections.Counter()
    for mot,frame,kind,cond,choices in sound_rows(data):
        if kind not in (3,4,6): continue
        if cond==1:
            # 0x1091eac4[1] -> 0x1091e7f0: requires weapon class 0xb
            # rather than Magnet Spike 0xd, so this cue is intentionally silent.
            unresolved['condition_for_another_weapon_class']+=1;continue
        if cond: unresolved['conditional']+=1; continue
        if mot not in motion_slots: unresolved['motion_not_ported']+=1; continue
        valid=class_valid if kind==6 else model_valid
        if not sum(w for r,w in choices): choices=[(choices[0][0],0)]
        # Unresolved requests in the merged hunter bank are voices. Keep their
        # original probability as silence; never remap them to weapon samples.
        mapped=[(BASE+r if r in valid else 0xffff,w) for r,w in choices]
        if not any(r!=0xffff for r,w in mapped): unresolved['voice_or_silent']+=1; continue
        mapped += [(0xffff,0)]*(4-len(mapped))
        for slot in motion_slots[mot]: events.append((slot,frame,4 if kind==6 else 2,mapped))
    events.sort()
    # Explicit sound call 13 is made by Frontier's effect-post helper for these
    # hand effects. It is rate-limited once per update (0x1032f446 clears the
    # flag each update; 0x10336440 sets it). Action/gauge gates match the effects.
    codes=set()
    for row in list(msbuild.msfxposts.MOTION_POSTS)+msbuild.msfxposts.motion_keys(data):
        key,frame,eff,bone,off,gate=row[:6]
        if eff[0]!=0xfc5 or eff[1] not in (3,4,0x46,0x47) or bone not in (14,18):continue
        action=key[1] if key[0]=='act' else key[2] if len(key)>2 else 65535
        if key[0]=='act':
            steps=[(m,start) for kind,m,start,*_ in acts[action]['steps'] if kind in (3,4,5)]
            if not steps:continue
            mot,start=steps[0];frame+=start
        else:mot=key[1]
        if mot not in own:continue
        codes.add((own[mot],frame,action,gate,13,8 if bone==14 else 12,*map(round,off)))
    # Source task 0xf/0x10 starts both sounds; use the same action/motion gates as
    # msfxposts.MOTION_POSTS, rather than adding them to every use of a motion.
    for mot,action,frame in ((1031,159,8),(1032,160,8),(1082,162,0),
                             (1031,95,8),(1032,96,8),(1082,161,0)):
        if mot in own:
            for req in (5,23):codes.add((own[mot],frame,action,0,req,255,0,0,0))
    if 1488 in own:
        for frame,req in ((114,26),(184,27)):codes.add((own[1488],frame,65535,0,req,255,0,0,0))
    # Do not add a second post when the ordinary table already contains exactly
    # this cue. Source sound and effect data can describe the same frame.
    def can_play(choices,request):
        return (choices[0][0]==request if not sum(w for r,w in choices)
                else any(r==request and w>0 for r,w in choices))
    codes=sorted(c for c in codes if not any(s==c[0] and f==c[1] and b==4 and
                 can_play(choices,BASE+c[4]) for s,f,b,choices in events))
    code_per=collections.Counter(c[0] for c in codes)
    if code_per and max(code_per.values())>32:raise ValueError('Code sound mask too small')
    per=collections.Counter(s for s,f,b,c in events)
    if max(per.values())>64: raise ValueError('Sound event mask too small')
    lines=['/* Generated from local sound tables. Do not publish. */',
           '#define MS_NSOUNDS %d'%len(events),
           'static const struct ms_sound_event ms_sounds[] = {']
    for slot,frame,bank,choices in events:
        lines.append('{%d,%d,%d,{%s},{%s}},'%(slot,frame,bank,','.join(str(r) for r,w in choices),','.join(str(w) for r,w in choices)))
    lines+=['};']
    lines+=['#define MS_NCODE_SOUNDS %d'%len(codes),'static const struct ms_code_sound ms_code_sounds[] = {']
    lines+=['{%d,%d,%d,%d,%d,%d,{%d,%d,%d}},'%c for c in codes]
    lines+=['};']
    for ident,path in [('MODEL',MODEL_PATH),('CLASS',CLASS_PATH)]:
        lines.append('#define MS_SOUND_%s_HASH 0x%xu'%(ident,zlib.crc32(path.encode('ascii'))^0xffffffff))
    (GEN/'ms_sound_data.inc').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    player=ASSETS/'player/quest/w05.arc'
    baseline=WORK/'w05-before-sound.arc'
    # A fresh asset rebuild must become the new baseline. Never silently reuse
    # the preceding revision's effects/motions when adding its sound resources.
    current_entries=arcpack.read(player.read_bytes())[1]
    has_converted_bank=any(p==MODEL_PATH and t==snd.TG['REQ'] for p,t,d in current_entries)
    if not has_converted_bank:
        shutil.copyfile(player,baseline)
    elif not baseline.exists():
        raise RuntimeError('Original player archive is missing; rebuild assets first')
    es=arcpack.read(baseline.read_bytes())[1]
    # Dedicated paths prevent a Great Sword hunter sharing/replacing these resources.
    es=[(p,t,d) for p,t,d in es if t not in (snd.TG['WAVE'],snd.TG['BANK'],snd.TG['REQ'])]
    for i,(p,t,d) in enumerate(es):
        if p==r'sound\call\pl\pl_wp05':
            # Remove synthetic swing cues and native GS cues on converted motions.
            es[i]=(p,t,msbuild.msfx.mss_rebuild(d,{5000+s for ss in motion_slots.values() for s in ss},{}))
    es+=model+common
    sound_bytes=sum(len(d) for p,t,d in es if t in snd.TG.values())
    if sound_bytes>=20*1024*1024: raise ValueError('Sound resources exceed sound heap budget')
    player.write_bytes(arcpack.build(es))
    for name,bank_es in [('001',model),('mat_b',common),('mat_i',common)]:
        path=ASSETS/f'weapon/w05/snd/{name}.arc';path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(arcpack.build(bank_es))
    if before!={str(p.relative_to(ROOT)):sha(p) for p in source_paths}: raise RuntimeError('Source sound input changed')
    report.update(dict(status='experimental',source_hashes=before,motion_events=len(events),
                       motions=len(per),unresolved=dict(unresolved),
                       code_sound_rows=len(codes),
                       player_arc_uncompressed_bytes=sum(len(d) for p,t,d in es),
                       sound_resource_bytes=sound_bytes,
                       player_arc_sha256=sha(player),
                       source_sounds_unchanged=True,limits=['GU spatial mix and voice limits',
                       'Frontier gain interpreted as linear; random pitch untraced',
                       'Native fallback includes draw/sheath and unmapped collision categories']))
    (HERE/'sound-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','motion_events','motions','unresolved','player_arc_uncompressed_bytes')}))

if __name__=='__main__': main()
