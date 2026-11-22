"""Generate scoped live-hit motion values from a reviewed local damage policy.

Original Frontier/GU assets, the serialized attacks and charge/gauge bookkeeping
remain untouched. All positive hit records retain at least one motion value.
"""
import collections,hashlib,json,re,sys
from prepare_frontier import HERE,CONVERTER

MS=CONVERTER/'weapons/magnet_spike'
GROUPS={'cutting','impact','charged_impact','pin_finisher','magnetic_shock'}


def policy():
    p=json.loads((HERE/'balance-policy.json').read_text(encoding='utf-8'))
    assert set(p['motion_percent'])==GROUPS
    assert all(type(v) is int and 5<=v<=200 for v in p['motion_percent'].values())
    assert 50<=p['raw_percent']<=150 and 25<=p['element_percent']<=150
    assert p['magnetise_percent']==110
    for key,value in p.get('source_motion_percent',{}).items():
        assert re.fullmatch(r'(attack|special):\d+',key) and type(value) is int and 5<=value<=200
    for key,value in p.get('action_motion_percent',{}).items():
        assert key.isdecimal() and 0<=int(key)<160 and type(value) is int and 5<=value<=200
    for key,value in p.get('source_ko_overrides',{}).items():
        assert re.fullmatch(r'(attack|special):\d+',key) and type(value) is int and 0<=value<=255
    return p


def scale(value,percent):return max(1,(value*percent+50)//100) if value else 0


def generate():
    p=policy();sys.path.insert(0,str(MS/'tools'));import sdt
    data=(MS.parents[1]/'dump/mhf/zz/mhfsdt.dec.bin').read_bytes()
    banks={e['kind']:sdt.attacks(data,e) for e in sdt.entries(data) if e['kind'] in (0x78,0x79)}
    generated=(MS/'gen/ms_data.inc').read_text(encoding='utf-8')
    base=int(re.search(r'#define MS_MAG_BASE (\d+)',generated)[1]);count=2*base+1
    values=[0]*count;kos=[0]*count;rows=[];seen=set()
    for line in (MS/'gen/report.txt').read_text(encoding='utf-8').splitlines():
        m=re.match(r'hit\s+(\d+): (.*?) MHF (attack|special)\s+(\d+) MV\s+(-?\d+)',line)
        if not m:continue
        ident,where,kind,source,mv=m.groups();ident=int(ident);source=int(source);mv=int(mv)
        assert 0<ident<=base and ident not in seen;seen.add(ident)
        r=banks[0x78 if kind=='attack' else 0x79][source];assert r['mv']==mv
        action=re.search(r'action\s+(\d+)',where);action=int(action[1]) if action else None
        if action in (105,157):group='pin_finisher'
        elif action in (35,36):group='charged_impact'
        elif 'shock' in where.lower():group='magnetic_shock'
        else:group='cutting' if r['type']&0x200 else 'impact'
        source_key=f'{kind}:{source}'
        percent=p.get('source_motion_percent',{}).get(source_key,p['motion_percent'][group])
        percent=p.get('action_motion_percent',{}).get(str(action),percent)
        tuned=scale(mv,percent);assert tuned<=65535
        values[ident]=tuned;values[ident+base]=tuned*p['magnetise_percent']//100
        source_ko=int(r['ko']);assert source_ko==r['ko'] and 0<=source_ko<=255
        tuned_ko=p.get('source_ko_overrides',{}).get(source_key,source_ko)
        kos[ident]=kos[ident+base]=tuned_ko
        rows.append({'hit':ident,'action':action,'group':group,'source_key':source_key,'applied_motion_percent':percent,'source_mv':mv,'balanced_mv':tuned,
            'magnetised_mv':values[ident+base],'source_ko':source_ko,'balanced_ko':tuned_ko})
    assert len(seen)==base and all(values[1:])
    assert set(p.get('source_motion_percent',{}))<=set(r['source_key'] for r in rows)
    assert set(p.get('action_motion_percent',{}))<=set(str(r['action']) for r in rows)
    out=HERE/'output';out.mkdir(exist_ok=True)
    text=['/* Generated damage/KO policy. Source gauges and timing retained. */',
      f'#define MS_BALANCE_RAW_PERCENT {p["raw_percent"]}u',
      f'#define MS_BALANCE_ELEMENT_PERCENT {p["element_percent"]}u',
      f'#define MS_BALANCE_HIT_COUNT {count}u',
      'static const uint16_t ms_balance_mv[MS_BALANCE_HIT_COUNT] = {',','.join(map(str,values)),'};',
      'static const uint8_t ms_balance_ko[MS_BALANCE_HIT_COUNT] = {',','.join(map(str,kos)),'};','']
    target=out/'ms_balance_data.inc';target.write_text('\n'.join(text),encoding='utf-8')
    report={'policy':p,'policy_sha256':hashlib.sha256((HERE/'balance-policy.json').read_bytes()).hexdigest(),
      'configuration_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
      'hit_count':count,'source_hit_count':base,'groups':dict(collections.Counter(r['group'] for r in rows)),
      'hits':rows,'scope':'Only type12 level raw/element fields and live Magnet Spike power/full-MV/KO fields; originals read-only.'}
    (HERE/'reports/balance-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Prepared balance policy:',base,'source hits plus Magnetise copies;',report['groups'])
    return report


if __name__=='__main__':generate()
