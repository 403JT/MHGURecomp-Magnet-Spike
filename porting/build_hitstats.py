"""Bind each generated hit ID to the supplied client's original KO value."""
import hashlib,json,re,sys
from prepare_frontier import HERE,CONVERTER
MS=CONVERTER/'weapons/magnet_spike'
OUT=HERE/'output'

def generate():
    sys.path.insert(0,str(MS/'tools'));import sdt
    source=MS.parents[1]/'dump/mhf/zz/mhfsdt.dec.bin'
    data=source.read_bytes();banks={e['kind']:sdt.attacks(data,e) for e in sdt.entries(data) if e['kind'] in (0x78,0x79)}
    generated=(MS/'gen/ms_data.inc').read_text()
    base=int(re.search(r'#define MS_MAG_BASE (\d+)',generated)[1])
    count=int(re.search(r'#define MS_NHITS (\d+)',generated)[1])
    values=[0]*count;found=set()
    report=MS/'gen/report.txt'
    for line in report.read_text().splitlines():
        m=re.match(r'hit\s+(\d+): .* MHF (attack|special)\s+(\d+) MV\s+(-?\d+) KO\s+([\d.]+)',line)
        if not m:continue
        hit,kind,ident,mv,ko=m.groups();hit=int(hit);ident=int(ident);ko=float(ko)
        row=banks[0x78 if kind=='attack' else 0x79][ident]
        if not 0<hit<=base or hit in found or row['ko']!=ko or row['mv']!=int(mv):
            raise RuntimeError('Generated hit report does not match the source attack record')
        if ko!=int(ko) or not 0<=ko<=255:raise RuntimeError('Source KO cannot be represented by the native hit byte')
        values[hit]=int(ko);found.add(hit)
    if len(found)!=base or count!=2*base+1:raise RuntimeError('Incomplete generated hit-to-source mapping')
    for i in range(1,base+1):values[i+base]=values[i]
    OUT.mkdir(exist_ok=True)
    payload=('#define MS_NHIT_STATS '+str(count)+'\nstatic const unsigned char ms_hit_ko[] = {\n'+
             ',\n'.join(','.join(map(str,values[i:i+24])) for i in range(0,count,24))+'\n};\n')
    target=OUT/'ms_hitstats_data.inc';target.write_text(payload)
    status={'entries':count,'source_hits':base,'max_ko':max(values),'values_over_constructor_signed_byte_cap':sum(v>127 for v in values[:base+1]),
            'source_sha256':hashlib.sha256(data).hexdigest(),'hit_report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
            'generated_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'native_field':'attack +0x56 (u8), after native arming; native part/skill processing retained',
            'exhaust':'GU template retained; source equivalent untraced'}
    (HERE/'hitstats-build.json').write_text(json.dumps(status,indent=2)+'\n')
    return status
if __name__=='__main__':
    d=generate();print('Bound',d['source_hits'],'source hits and their magnetised copies; max KO',d['max_ko'])
