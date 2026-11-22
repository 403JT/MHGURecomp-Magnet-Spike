"""Reuse a run only when its executed command tables are byte-for-byte equivalent.

Code and all non-command assets must still match exactly. This avoids rerunning
unrelated audio/shot tests for a timing fix in an unvisited command table.
"""
import hashlib,re,sys
from prepare_frontier import CONVERTER

def command_equivalence(run,folder,candidate,expected):
    old=run.get('mod_files',{})
    if set(old)!=set(expected):return None
    changed=[p for p in expected if expected[p]!=old[p]]
    if not changed:return {'exact_files':True}
    allowed=r'romfs[\\/]nativeNX[\\/]arc[\\/]player[\\/]quest[\\/]w05_m[0-5]\.arc'
    if any(not re.fullmatch(allowed,p) for p in changed):return None
    sys.path.insert(0,str(CONVERTER/'tools'));import arcpack,xfs
    log=(folder/'log.txt').read_text(encoding='utf-8',errors='replace')
    used={int(n)-2000 for n in re.findall(r'msport: state .*? table (\d+)',log) if 2000<=int(n)<3000}
    used|={int(n) for n in re.findall(r'\[moves\].*?weapon table (\d+) ',log)}
    if not used:return None
    for rel in changed:
        path=folder/'mods/magnet-spike-experimental'/rel
        payload=path.read_bytes()
        if hashlib.sha256(payload).hexdigest()!=old[rel]:return None
        before=arcpack.read(payload)[1];after=arcpack.read((candidate/rel).read_bytes())[1]
        def split(entries):
            tables=[(p,d) for p,t,d in entries if t==0x4b4c2bd3]
            others={(p,t):d for p,t,d in entries if t!=0x4b4c2bd3}
            if len(tables)!=1:return None,None,None
            name,blob=tables[0];root=xfs.parse(blob);arr=root['TblList']['mpArray']
            root['TblList']['mpArray']=[]
            return (name,root),arr,others
        a,ta,ea=split(before);b,tb,eb=split(after)
        if a is None or a!=b or ea!=eb or len(ta)!=len(tb):return None
        if any(i>=len(ta) or ta[i]!=tb[i] for i in used):return None
    return {'exact_files':False,'equivalent_command_archives':changed,'identical_executed_tables':sorted(used),
            'basis':'Same executable and all other assets; same command resources and all tables logged as used'}
