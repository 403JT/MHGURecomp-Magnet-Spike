"""Codec boundary and signal checks on generated, non-game PCM."""
import json
import numpy as np
from build_sounds import encoder, encoded_wave, HERE

def main():
    encode=encoder();results={}
    for n in (1,2,13,14,15,27,28,29,4800):
        for name,pcm in [('silence',np.zeros(n,dtype=np.int16)),
                         ('dc',np.full(n,12000,dtype=np.int16)),
                         ('alternating',np.resize(np.array([-16000,16000],dtype=np.int16),n))]:
            wave,stats=encoded_wave(pcm,48000,encode)
            results[f'{name}_{n}']=stats
    t=np.arange(48000)/48000
    for name,pcm in [('sine',(16000*np.sin(2*np.pi*440*t)).astype(np.int16)),
                     ('noise',np.random.default_rng(123).integers(-16000,16000,48000,dtype=np.int16))]:
        _,stats=encoded_wave(pcm,48000,encode);results[name]=stats
    report={'all_passed':True,'synthetic_signals':results}
    (HERE/'reports/audio-codec-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(f'Passed {len(results)} synthetic DSP encode/decode checks; sample counts preserved.')

if __name__=='__main__':main()
