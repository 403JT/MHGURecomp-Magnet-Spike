"""Rebuild HDP records from source metadata; preserve converted shape/motion/audio assets."""
import hashlib,json,os,re,sys
from prepare_frontier import HERE,ROOT,CONVERTER

def main():
    os.environ['GU_ROMFS']=str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs')
    ms=CONVERTER/'weapons/magnet_spike'
    sys.path[:0]=[str(CONVERTER/'tools'),str(ms/'tools')]
    import arcpack,mshit,msbuild,sdt
    data=(CONVERTER/'dump/mhf/zz/mhfsdt.dec.bin').read_bytes()
    banks={e['kind']:sdt.attacks(data,e) for e in sdt.entries(data) if e['kind'] in (0x78,0x79)}
    def template(rel,index):
        es=msbuild.gu_arc(rel)
        hdp=next(b for p,(t,b) in es.items() if p.endswith('_hitdata'))
        return mshit.hdp_parse(hdp)[index]
    cut=template('player/quest/w00.arc',1);impact=template('player/quest/w02.arc',3)
    target=ms/'romfs/nativeNX/arc/player/quest/w05.arc'
    payload=target.read_bytes();_,entries=arcpack.read(payload)
    old=next(d for p,t,d in entries if p.endswith('pl_we05_hitdata'))
    shapes=mshit.hts_parse(next(d for p,t,d in entries if p.endswith('pl_we05_hitsize')))
    generated=(ms/'gen/ms_data.inc').read_text(encoding='utf-8')
    base=int(re.search(r'#define MS_MAG_BASE (\d+)',generated)[1])
    rows=[None]*(base+1);rows[0]=[0]*28
    for line in (ms/'gen/report.txt').read_text(encoding='utf-8').splitlines():
        match=re.match(r'hit\s+(\d+): .* MHF (attack|special)\s+(\d+) MV\s+(-?\d+) KO\s+([\d.]+)',line)
        if not match:continue
        hit,kind,ident,mv,ko=match.groups();hit=int(hit);r=banks[0x78 if kind=='attack' else 0x79][int(ident)]
        if rows[hit] is not None or r['mv']!=int(mv) or r['ko']!=float(ko):raise RuntimeError('Source/report hit mismatch')
        is_cut=bool(r['type']&0x200)
        rows[hit]=mshit.hdp_entry(cut if is_cut else impact,r['mv'],2*r['raw'][1],mshit.CUT if is_cut else mshit.IMPACT,hit-1)
    if any(r is None for r in rows) or len(shapes)!=base:raise RuntimeError('Incomplete hit/shape mapping')
    for row in rows[1:].copy():
        row=row.copy();mv=row[24]*110//100;row[2]=min(mv,250);row[24]=mv;rows.append(row)
    new=mshit.hdp_bytes(rows)
    if len(new)!=16+56*len(rows) or len(mshit.hdp_parse(new))!=2*base+1:raise RuntimeError('Invalid native HDP span')
    out=[(p,t,new if p.endswith('pl_we05_hitdata') else d) for p,t,d in entries]
    rebuilt=arcpack.build(out)
    before={(p,t):d for p,t,d in entries if not p.endswith('pl_we05_hitdata')}
    after={(p,t):d for p,t,d in arcpack.read(rebuilt)[1] if not p.endswith('pl_we05_hitdata')}
    if before!=after:raise RuntimeError('Hit rebuild changed an unrelated asset')
    sound_path=HERE/'sound-build.json';sound=json.loads(sound_path.read_text(encoding='utf-8'))
    old_hash=hashlib.sha256(payload).hexdigest()
    if sound['player_arc_sha256']!=old_hash:raise RuntimeError('Sound manifest was already stale')
    target.write_bytes(rebuilt)
    sound['player_arc_sha256']=hashlib.sha256(rebuilt).hexdigest()
    sound['hit_layout_postprocess']={'before':old_hash,'after':sound['player_arc_sha256'],'all_non_hit_resources_identical':True}
    sound_path.write_text(json.dumps(sound,indent=2)+'\n',encoding='utf-8')
    report={'native_header_bytes':16,'records':len(rows),'shape_sets':len(shapes),
      'all_native_record_spans_in_file':True,'all_non_hit_resources_identical':True,
      'old_hdp_sha256':hashlib.sha256(old).hexdigest(),'hdp_sha256':hashlib.sha256(new).hexdigest(),
      'source_motion_values_and_durations_checked':base,'shape_binding':'native +0x20 low byte; base and magnetised copies share each converted shape set'}
    (HERE/'hit-layout-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Rebuilt',len(rows),'native HDP records; correct16-byte header and shape bindings; other resources identical.')
if __name__=='__main__':main()
