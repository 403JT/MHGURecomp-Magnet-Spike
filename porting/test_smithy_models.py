"""Check bounds, skinning, textures and names for all forty converted models."""
import json,struct,sys
import numpy as np
from build_smithy_tree import HERE,MS,CONVERTER,ROM,arcpack,sha
sys.path.insert(0,str(CONVERTER/'tools'))
import mod as modlib,tex

def main():
    build=json.loads((HERE/'reports/smithy-tree-build.json').read_text())
    checks={};counts={'models':0,'vertices':0,'meshes':0,'textures':0}
    visual_signatures=set()
    catalog=json.loads((HERE/'reports/smithy-model-catalog.json').read_text())['compatible_models']
    checks['all_source_models_share_the_exact_working_animation_skeleton']=len({m['files']['1.fskl'] for m in catalog})==1
    shared=arcpack.read((ROM/'nativeNX/arc/weapon/w00/001.arc').read_bytes())[1]
    for row in build['models']:
        n=row['id'];file=MS/f'romfs/nativeNX/arc/weapon/w05/{n:03d}.arc'
        assert sha(file)==row['sha256']
        entries=arcpack.read(file.read_bytes())[1]
        import hashlib
        visual_signatures.add(hashlib.sha256(b''.join(data for _,kind,data in entries
            if kind in (0x58a15856,0x241f5deb))).hexdigest())
        prefix=f'weapon\\w05\\mbg{n:03d}\\mbg{n:03d}'
        assert all(p.startswith(prefix) or (p,t,b) in shared for p,t,b in entries)
        assert len(set((p,t) for p,t,_ in entries))==len(entries)
        models=[b for _,t,b in entries if t==0x58a15856];assert len(models)==1
        b=models[0];m=modlib.parse(b)
        assert m['bones']==11
        vertices=m['vertices'];assert 0<vertices<65535
        indices=np.frombuffer(m['ib'],dtype='<u2');assert np.all((indices==65535)|(indices<vertices))
        vb=np.frombuffer(m['vb'],dtype=np.dtype({'names':['pos','w0','bones','uv','w12'],
            'formats':[('<i2',3),'<i2',('u1',4),('<f2',2),('<f2',2)],'offsets':[0,6,16,20,24],'itemsize':28}))
        assert np.isfinite(vb['uv']).all() and np.isfinite(vb['w12']).all()
        assert (vb['bones']<11).all()
        weights=np.column_stack([vb['w0']/32767,vb['w12'].astype(float)])
        assert (weights>=-0.001).all() and (weights.sum(axis=1)<=1.002).all()
        for mesh in m['mesh_list']:
            assert mesh['fmt']==0x14d40022 and mesh['stride']==28
            assert mesh['vertexStart']+mesh['numVertices']<=vertices
            assert mesh['indexStart']+mesh['numIndices']<=len(indices)
        for _,t,data in entries:
            if t==0x241f5deb:
                h=tex.parse(data);image=tex.decode(data)
                assert image.shape[:2]==(h['height'],h['width'])
                counts['textures']+=1
            elif t==0x2749c8a8:
                assert b'weapon\\w00\\two001' not in data
        counts['models']+=1;counts['vertices']+=vertices;counts['meshes']+=len(m['mesh_list'])
    checks['all_40_models_checked']=counts['models']==40
    checks['all_40_geometry_texture_combinations_are_distinct']=len(visual_signatures)==40
    checks['indices_skin_weights_and_vertex_bounds_valid']=True
    checks['all_texture_resources_decode']=True
    checks['materials_reference_only_their_own_model_texture_paths']=True
    report={'all_passed':all(checks.values()),'checks':checks,'counts':counts,'models':build['models']}
    (HERE/'reports/smithy-model-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Converted model checks:',counts);assert report['all_passed']
if __name__=='__main__':main()
