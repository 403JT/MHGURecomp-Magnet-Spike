"""Bind scoped native command rows to the supplied Frontier temporal predicates."""
import hashlib,json,os,re,sys
from prepare_frontier import HERE,ROOT,CONVERTER

def generate():
    os.environ['GU_ROMFS']=str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs')
    ms=CONVERTER/'weapons/magnet_spike'
    sys.path[:0]=[str(CONVERTER/'tools'),str(ms/'tools')]
    import msbuild,msact,arcpack
    generated=(ms/'gen/ms_data.inc').read_text(encoding='utf-8')
    block=generated.split('static const struct ms_pair ms_pairs[] = {',1)[1].split('};',1)[0]
    pairs={tuple(map(int,v)):i for i,v in enumerate(re.findall(r'\{(\d+),\s*(\d+)\}',block))}
    msbuild.PAIRS.clear();msbuild.PAIRS.update(pairs)
    path=CONVERTER/'dump/mhf/zz/mhfdat.dec.prefix.bin';source=path.read_bytes();acts=msact.actions(source)
    msbuild.MODES.update(msact.modes(source))
    msbuild.ACTIONS[:]=[n for n,a in enumerate(acts) if a['steps'] and all(k<=2 or m//1000==1 for k,m,*_ in a['steps'])]
    cmds,tbl,index,_=msbuild.build_commands(acts,msbuild.gu_arc('player/quest/w00_m0.arc'))
    if msbuild.PAIRS!=pairs:raise RuntimeError('Temporal binding changed compiled class-input IDs')
    seen={}
    steps=generated.split('static const struct ms_step ms_steps[] = {',1)[1].split('};',1)[0]
    for fields,no in re.findall(r'\{([^}]+)\},\s*/\* (\d+):',steps):
        a=int(no);k=seen.get(a,0);seen[a]=k+1
        if int(fields.split(',')[-1])!=2000+index[(a,k)]:raise RuntimeError('Temporal binding changed compiled table IDs')
    files={}
    for k,style in enumerate(msbuild.STYLES):
        entries=[(p,msbuild.T_CMD,b) for p,b in sorted(cmds.items())]
        entries.append(('player\\cmd\\w05\\plcmd_w05_'+style,msbuild.T_TBL,tbl))
        payload=arcpack.build(entries);arc=ms/'romfs/nativeNX/arc/player/quest'/f'w05_m{k}.arc'
        if arc.read_bytes()!=payload:raise RuntimeError('Rebuild the six command archives before the temporal module')
        files[arc.name]=hashlib.sha256(payload).hexdigest()
    rules=[];tables=[];rows=[];starts={}
    for t in msbuild.WINDOW_TABLES:
        a=t['action'];cs=t['cancels']
        if not 0<len(cs)<=32 or not 0<len(t['rows'])<=48:raise RuntimeError('Temporal masks/native buffer capacity exceeded')
        if any(q[2]>0 for c in cs for q in c['buf']+c['go']):raise RuntimeError('Level-qualified cancels require a separate traced binding')
        if any(c['buf'][1]!=c['go'][1] for c in cs):raise RuntimeError('Independent close times require a separately traced native input filter')
        if a not in starts:
            starts[a]=len(rules);rules.extend(c['buf']+c['go'] for c in cs)
        tables.append((a,t['table'],starts[a],t['step'],len(cs),len(t['rows']),len(rows),t.get('recovery',0)))
        rows.extend(t['rows'])
    out=['/* Generated locally from source timing rules; do not publish. */',
         'static const struct window_rule window_rules[] = {']
    out+=['    {{'+','.join('{'+','.join(map(str,q))+'}' for q in rule)+'}},' for rule in rules]
    out+=['};','static const struct window_table window_tables[] = {']
    out+=['    {'+','.join(map(str,t))+'},' for t in tables]
    out+=['};','static const unsigned char window_rows[] = {'+','.join(map(str,rows))+'};']
    target=HERE/'output/cancel_windows.inc';target.write_text('\n'.join(out)+'\n',encoding='utf-8')
    status={'actions':sorted(starts),'source_cancels':len(rules),'native_step_tables':len(tables),
            'native_rows':len(rows),'source_sha256':hashlib.sha256(source).hexdigest(),
            'generated_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'command_archives':files,
            'native_sites':{'range':0x281388},
            'scope':'Source loop-specific charge timing plus explicit GU combo-end recovery; equal raw buffer/transition close times required',
            'input_ids_preserved':True,'table_indices_preserved':True}
    (HERE/'cancel-window-build.json').write_text(json.dumps(status,indent=2)+'\n',encoding='utf-8')
    return status
if __name__=='__main__':
    d=generate();print('Bound temporal predicates for',len(d['actions']),'actions and',d['native_step_tables'],'native step tables.')
