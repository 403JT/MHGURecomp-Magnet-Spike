"""Prepare the separate type-12 smithy tree; original game data stays read-only.

Records are shared read-only at runtime with GS, except cloned base records.
Generated local configuration contains counts/model routing, never recipes.
"""
import argparse, contextlib, hashlib, io, json, os, struct, sys, zlib
from prepare_frontier import HERE, ROOT, CONVERTER, WORK, sha

MS = CONVERTER/'weapons/magnet_spike'
ROM = ROOT/'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs'
os.environ['GU_ROMFS'] = str(ROM)
sys.path[:0] = [str(CONVERTER/'tools'), str(MS/'tools')]
import arcpack

def entries(rel):
    return arcpack.read((ROM/rel).read_bytes())[1]

def table(ents, suffix, stride):
    found=[data for name,_,data in ents if name.endswith(suffix)]
    if len(found)!=1: raise ValueError('Expected one '+suffix)
    data=found[0]; n=struct.unpack_from('<I',data,4)[0]
    if len(data)!=8+n*stride: raise ValueError('Unexpected table layout '+suffix)
    return [data[8+i*stride:8+(i+1)*stride] for i in range(n)],hashlib.sha256(data).hexdigest()

def audit():
    resident=entries('nativeNX/loc/arc/resident.arc')
    smithy=entries('nativeNX/arc/facility/blacksmith.arc')
    tables={}
    for key,ents,suffix,stride in [('base',resident,'weapon00BaseData',33),
        ('level',resident,'weapon00LevelData',15),('create',smithy,'weaponCreateW00',38),
        ('process',smithy,'weaponProcessW00',32)]:
        tables[key]=table(ents,suffix,stride)
    base=tables['base'][0]; levels=tables['level'][0]
    assert len(base)==137 and len(levels)==959
    assert all(struct.unpack_from('<I',r)[0]==i for i,r in enumerate(base))
    assert all(struct.unpack_from('<I',r)[0]==i for i,r in enumerate(levels))
    # Row identities/derive IDs must fit unchanged within the independent type.
    assert all(r[4]<len(base) and 1<=r[5]<=base[r[4]][9]+base[r[4]][10] for r in levels)
    assert all(r[24+2*j]<len(base) for r in base for j in range(5))
    model_ids=[m['source_model'] for m in json.loads((HERE/'reports/smithy-model-catalog.json').read_text())['compatible_models']]
    assert len(model_ids)==40
    # Preserve the already shipped 001..007 identities. New model IDs only grow.
    source_models=[400,595,606,414,415,404,407]
    source_models += [m for m in model_ids if m not in source_models]
    appearances={}; mapping=[]
    for i,r in enumerate(base):
        original_model=struct.unpack_from('<H',r,4)[0]
        if i==0: mapping.append(1); continue
        if original_model not in appearances: appearances[original_model]=len(appearances)%len(source_models)+1
        mapping.append(appearances[original_model])
    # Reuse is allowed across families, but a branch to a genuinely different
    # source appearance must visibly change. Work per source model so shared
    # GS appearances remain shared, and never renumber the shipped model IDs.
    groups={i:struct.unpack_from('<H',r,4)[0] for i,r in enumerate(base)}
    neighbors={g:set() for g in appearances}
    edges=[]
    for i,r in enumerate(base[1:],1):
        for j in range(5):
            child=r[24+2*j]
            if child and groups[i]!=groups[child]:
                neighbors[groups[i]].add(groups[child]);neighbors[groups[child]].add(groups[i])
                edges.append((groups[i],groups[child]))
    for parent,child in edges:
        if appearances[parent]!=appearances[child]:continue
        forbidden={appearances[n] for n in neighbors[child]}
        current=appearances[child]
        appearances[child]=next((current-2-k)%len(source_models)+1 for k in range(len(source_models))
            if (current-2-k)%len(source_models)+1 not in forbidden)
    mapping=[1]+[appearances[groups[i]] for i in range(1,len(base))]
    assert all(appearances[a]!=appearances[b] for a,b in edges)
    assert len(set(mapping[1:]))==len(source_models)
    return tables,source_models,mapping,len(appearances)

def generate(models=False):
    tables,source_models,mapping,appearances=audit()
    out=HERE/'output';out.mkdir(exist_ok=True)
    text=['/* Generated local counts and model routing; originals remain read-only. */']
    for key,(rows,_) in tables.items():text.append(f'#define MS_TREE_{key.upper()}_COUNT {len(rows)}u')
    text += [f'#define MS_TREE_MODEL_COUNT {len(source_models)}u',
        'static const uint8_t ms_tree_models[MS_TREE_BASE_COUNT] = {'+','.join(map(str,mapping))+'};',
        'static const uint32_t ms_tree_model_hashes[MS_TREE_MODEL_COUNT] = {']
    for n in range(1,len(source_models)+1):
        path=f'weapon\\w05\\mbg{n:03d}\\mbg{n:03d}'
        text.append(f'    0x{zlib.crc32(path.encode())^0xffffffff:08x}u,')
    text+=['};','']
    (out/'smithy_tree.inc').write_text('\n'.join(text),encoding='utf-8')
    conversions=[]
    if models:
        import fmod2gu
        work=WORK/'smithy_conversion';work.mkdir(exist_ok=True)
        template=work/'gs_template.arc'
        template.write_bytes((ROM/'nativeNX/arc/weapon/w00/001.arc').read_bytes())
        dest=MS/'romfs/nativeNX/arc/weapon/w05';dest.mkdir(parents=True,exist_ok=True)
        catalog={m['source_model']:m for m in json.loads((HERE/'reports/smithy-model-catalog.json').read_text())['compatible_models']}
        for n,source in enumerate(source_models,1):
            folder=HERE/'work/smithy_models'/f'wk{source:03d}'
            for name,digest in catalog[source]['files'].items():
                if sha(folder/name)!=digest:raise RuntimeError('Source model changed')
            target=dest/f'{n:03d}.arc';temp=work/f'{n:03d}.arc'
            # Converter diagnostics contain no data tables, but keep them local.
            with (work/f'{n:03d}.log').open('w',encoding='utf-8') as log,contextlib.redirect_stdout(log):
                fmod2gu.build_arc(str(folder),str(template),str(temp))
            old='weapon\\w00\\two001\\two001';new=f'weapon\\w05\\mbg{n:03d}\\mbg{n:03d}'
            converted=[]
            for path,kind,data in arcpack.read(temp.read_bytes())[1]:
                if kind==fmod2gu.T_MRL:data=data.replace(old.encode(),new.encode())
                converted.append((path.replace(old,new),kind,data))
            target.write_bytes(arcpack.build(converted))
            conversions.append({'id':n,'frontier_model':source,'sha256':sha(target),'resources':len(converted)})
            print(f'Converted model {n}/{len(source_models)}',flush=True)
    report={'counts':{k:len(v[0]) for k,v in tables.items()},
        'source_table_hashes':{k:v[1] for k,v in tables.items()},
        'source_appearance_count':appearances,'converted_model_count':len(source_models),
        'model_assignment':{'weapon_ids':len(mapping)-1,'all_models_used':len(set(mapping[1:]))==40,
            'same_gs_model_keeps_same_spike_model':True,'shipped_models_1_to_7_preserved':True,
            'branches_to_different_gs_appearances_change_model':True},
        'policy':'Independent type 12; same numeric IDs as type 7. Exact GS stats, levels, recipes and upgrade links.',
        'models':conversions,'configuration_sha256':sha(out/'smithy_tree.inc')}
    path=HERE/'reports/smithy-tree-build.json'
    if not models and path.exists():report['models']=json.loads(path.read_text()).get('models',[])
    path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Smithy counts:',report['counts'],'Frontier models:',len(source_models),'GS appearances:',appearances)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--models',action='store_true');args=p.parse_args()
    generate(args.models)
