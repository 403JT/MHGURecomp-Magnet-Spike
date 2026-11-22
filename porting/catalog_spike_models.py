"""Catalogue source weapon models with the proven Magnet Spike skeleton layout.

Original client archives and the installed mod are read-only. Extracted data is
kept under the local ignored work directory, never printed or published.
"""
import hashlib,json,sys
from prepare_frontier import HERE,WORK,CONVERTER,abn_parts,parts,decode,save

def main():
    sys.path.insert(0,str(CONVERTER/'weapons/magnet_spike/tools'));import fskl
    dest=WORK/'smithy_models';dest.mkdir(exist_ok=True)
    archives=[WORK/f'extend_wk{n:03d}.abn.decoded' for n in (0,500)]
    sources={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archives}
    entries={}
    for p in archives:
        for n,b in abn_parts(p.read_bytes()).items():
            if n in entries:raise RuntimeError('Duplicate source model ID')
            entries[n]=b
    jobs=[]
    for n,b in sorted(entries.items()):
        packed=dest/f'wk{n:03d}.packed';container=dest/f'wk{n:03d}.container'
        if not container.exists():save(packed,b);jobs.append((packed,container))
    print('Cataloguing',len(entries),'source model containers.',flush=True)
    if jobs:decode(jobs)
    jobs=[];containers={};rejected=[]
    for n in sorted(entries):
        try:
            c=parts((dest/f'wk{n:03d}.container').read_bytes())
            if len(c)<3 or not all(c[:3]):raise ValueError('Incomplete model container')
        except ValueError:
            rejected.append(n);continue
        containers[n]=c;skeleton=dest/f'wk{n:03d}.fskl'
        if not skeleton.exists():
            raw=dest/f'wk{n:03d}-skeleton.packed';save(raw,c[1]);jobs.append((raw,skeleton))
    if jobs:decode(jobs)
    def signature(blob):
        _,bones=fskl.parse(blob)
        return tuple((b['node'],b['parent'],b['child'],b['sibling']) for b in bones)
    reference=signature((CONVERTER/'dump/mhf/weapon/wk400/1.fskl').read_bytes())
    compatible=[];jobs=[]
    for n,c in sorted(containers.items()):
        try:sig=signature((dest/f'wk{n:03d}.fskl').read_bytes())
        except (ValueError,AssertionError,IndexError):continue
        if sig!=reference:continue
        compatible.append(n);folder=dest/f'wk{n:03d}';folder.mkdir(exist_ok=True)
        save(folder/'1.fskl',(dest/f'wk{n:03d}.fskl').read_bytes())
        for i,ext in ((0,'fmod'),(2,'tex')):
            target=folder/f'{i}.{ext}'
            if not target.exists():
                raw=dest/f'wk{n:03d}-{i}.packed';save(raw,c[i]);jobs.append((raw,target))
    if jobs:decode(jobs)
    models=[]
    for n in compatible:
        folder=dest/f'wk{n:03d}'
        models.append({'source_model':n,'folder':str(folder),
            'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}})
    if sources!={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest() for p in archives}:
        raise RuntimeError('Source decoded archives changed')
    report={'source_archive_hashes':sources,'source_container_count':len(entries),'compatible_models':models,
            'compatible_count':len(models),'rejected_container_count':len(rejected),
            'selection':'Exact bone IDs and parent/child/sibling structure match the proven wk400 skeleton',
            'source_archives_unchanged':True,'remaining_validation':'Geometry, textures, animated conversion and native loading'}
    (HERE/'reports/smithy-model-catalog.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Found',len(models),'models with the Magnet Spike skeleton layout; originals unchanged.',flush=True)
if __name__=='__main__':main()
