"""Find converted Frontier samples in the recorded game mix, without exporting source audio."""
import argparse
import json
import math
import re
import numpy as np
import soundfile as sf
from sound_env import *
from build_sounds import MODEL_PATH, CLASS_PATH

def correlation(mix, signal, stride=4):
    # Downsample both paths identically for a bounded FFT; audio fidelity was
    # already measured at 48 kHz during conversion. This only detects playback.
    x=np.asarray(signal[::stride],dtype=np.float64)/32768
    y=np.asarray(mix[::stride],dtype=np.float64)
    x-=x.mean();y-=y.mean()
    n=len(x);size=1<<(len(y)+n-1).bit_length()
    c=np.fft.irfft(np.fft.rfft(y,size)*np.conj(np.fft.rfft(x,size)),size)[:len(y)-n+1]
    energy=np.r_[0,np.cumsum(y*y)]
    denom=np.sqrt(np.maximum((energy[n:]-energy[:-n])*np.sum(x*x),1e-30))
    scores=c/denom
    k=int(np.argmax(np.abs(scores)))
    return dict(correlation=float(scores[k]),at_seconds=k*stride/48000)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('profile');args=parser.parse_args()
    profile=HERE/'runs'/args.profile
    run=json.loads((profile/'run.json').read_text(encoding='utf-8'))
    assets=profile/'mods/magnet-spike-experimental/romfs/nativeNX/arc'
    mix,rate=sf.read(profile/'audio.wav',dtype='float32')
    if rate!=48000:raise ValueError('Unexpected capture rate')
    clipped_fraction=float(np.mean(np.abs(mix)>=0.999))
    peak=float(np.max(np.abs(mix)))
    mix=mix.mean(axis=1) if mix.ndim>1 else mix
    text=(profile/'log.txt').read_text(encoding='utf-8',errors='replace')
    posted={(int(slot),int(req)) for slot,req in re.findall(r'ms-sound: post slot (\d+) request (\d+)',text)}
    results=[]
    for slot,req in sorted(posted):
        path=CLASS_PATH if slot==4 else MODEL_PATH
        es=arcpack.read((assets/('weapon/w05/snd/mat_b.arc' if slot==4 else 'weapon/w05/snd/001.arc')).read_bytes())[1]
        tr=snd.reqgu_parse(next(d for p,t,d in es if p==path and t==snd.TG['REQ']))
        w=next(w for w in tr['ents'] if w[0]&0xffff==req)
        bank=snd.bank_parse(next(d for p,t,d in es if p==path+'_src' and t==snd.TG['BANK']))
        key=(w[0]>>16)&255
        wave_path=next(p for p,t,a in bank['ents'] if a[72]<=key<=a[73])
        wav=snd.gu_wave_parse(next(d for p,t,d in es if p==wave_path and t==snd.TG['WAVE']))
        pcm=np.asarray(snd.dsp_decode(wav['data'],wav['coefs'],wav['samples']),dtype=np.int16)
        if not np.any(pcm):continue
        found=correlation(mix,pcm)
        results.append(dict(slot=slot,request=req,sample_id=wave_path,**found))
    report=dict(profile=args.profile,duration_seconds=len(mix)/rate,detected=results,
                strong_matches=sum(abs(r['correlation'])>=0.55 for r in results),
                distinct_sample_matches=len({r['sample_id'] for r in results if abs(r['correlation'])>=.55}),
                clipped_fraction=clipped_fraction,peak_stereo=peak,
                module_sha256=run['module_sha256'],mod_files=run['mod_files'])
    (profile/'audio-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
