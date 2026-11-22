"""Rebuild only the six style command archives; preserve motion/sound assets."""
import json,os,re,sys,hashlib
from prepare_frontier import HERE,ROOT,CONVERTER

def main():
    os.environ['GU_ROMFS']=str(ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs')
    sys.path[:0]=[str(CONVERTER/'tools'),str(CONVERTER/'weapons/magnet_spike/tools')]
    import msbuild,msact,arcpack
    ms=CONVERTER/'weapons/magnet_spike'
    source=(ms/'gen/ms_data.inc').read_text()
    pairs_block=source.split('static const struct ms_pair ms_pairs[] = {',1)[1].split('};',1)[0]
    pairs=[tuple(map(int,x)) for x in re.findall(r'\{(\d+),\s*(\d+)\}',pairs_block)]
    msbuild.PAIRS.update({p:i for i,p in enumerate(pairs)})
    data=(CONVERTER/'dump/mhf/zz/mhfdat.dec.prefix.bin').read_bytes()
    acts=msact.actions(data);msbuild.MODES.update(msact.modes(data))
    msbuild.ACTIONS[:]=[n for n,a in enumerate(acts) if a['steps'] and all(k<=2 or m//1000==1 for k,m,*_ in a['steps'])]
    cmds,tbl,index,report=msbuild.build_commands(acts,msbuild.gu_arc('player/quest/w00_m0.arc'))
    if msbuild.PAIRS!={p:i for i,p in enumerate(pairs)}:raise RuntimeError('Command rebuild changed compiled input IDs')
    # The compiled action engine holds these table indices. Check every one.
    generated_steps=source.split('static const struct ms_step ms_steps[] = {',1)[1].split('};',1)[0]
    rows=re.findall(r'\{([^}]+)\},\s*/\* (\d+):',generated_steps)
    seen={}
    for fields,no in rows:
        no=int(no);step=seen.get(no,0);seen[no]=step+1
        if int(fields.split(',')[-1])!=2000+index[(no,step)]:raise RuntimeError('Command table index changed')
    files={}
    for k,style in enumerate(msbuild.STYLES):
        entries=[(p,msbuild.T_CMD,b) for p,b in sorted(cmds.items())]
        entries.append(('player\\cmd\\w05\\plcmd_w05_'+style,msbuild.T_TBL,tbl))
        target=ms/'romfs/nativeNX/arc/player/quest'/f'w05_m{k}.arc'
        payload=arcpack.build(entries);target.write_bytes(payload)
        files[target.name]=hashlib.sha256(payload).hexdigest()
    (HERE/'command-build.json').write_text(json.dumps({'style_files':files,'actions':len(msbuild.ACTIONS),
        'tables':len(index),'input_ids_preserved':True,'table_indices_preserved':True,
        'format':'GU lookback for ordinary windows; scoped source predicates for charge and GU finisher recovery',
        'runtime_window_actions':sorted({t['action'] for t in msbuild.WINDOW_TABLES}),
        'remaining_limits':['Native integration and exact boundary behavior require matching temporal verification']},indent=2)+'\n')
    (HERE/'output/command-build-report.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
    print('Rebuilt six command archives; compiled input IDs and all action table indices preserved.')
if __name__=='__main__':main()
