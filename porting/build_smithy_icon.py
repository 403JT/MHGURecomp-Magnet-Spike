"""Build the new type's icon atlas from a source-model silhouette.

Only two verified empty cells and one ARC texture resource change. This targets
the isolated mod, never a user's installed UI mod or the original RomFS.
"""
import json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFilter
from build_smithy_tree import HERE,MS,ROM,CONVERTER,arcpack,sha
sys.path[:0]=[str(MS/'tools'),str(CONVERTER/'tools')]
import tex,fmod

def silhouette(size):
    meshes=fmod.parse((HERE/'work/smithy_models/wk400/0.fmod').read_bytes())
    pts=np.concatenate([np.array(m['pos']) for m in meshes])
    axes=np.argsort(np.ptp(pts,axis=0))[-2:]
    low=pts[:,axes].min(0);extent=np.ptp(pts[:,axes],axis=0)
    scale=(size-6)/max(extent)
    shift=(size-extent*scale)/2
    mask=Image.new('L',(size,size));draw=ImageDraw.Draw(mask)
    for m in meshes:
        p=(np.array(m['pos'])[:,axes]-low)*scale+shift
        p[:,1]=size-p[:,1]
        for a,b,c,_ in fmod.triangles(m):draw.polygon([tuple(p[x]) for x in (a,b,c)],fill=255)
    # Crisp dark outline and neutral fill; native UI supplies rarity tint.
    outline=mask.filter(ImageFilter.MaxFilter(3))
    image=Image.new('RGBA',(size,size));image.paste((30,30,30,255),(0,0),outline)
    image.paste((235,235,235,255),(0,0),mask)
    return np.array(image)

def main():
    rel='nativeNX/eng/arc/resident_eng.arc';original=(ROM/rel).read_bytes()
    entries=arcpack.read(original)[1]
    suffix='GUI\\99_texture\\HD_cmn_icon_GSM_NOMIP'
    found=[i for i,(n,_,_) in enumerate(entries) if n.endswith(suffix)]
    assert len(found)==1
    i=found[0];name,kind,data=entries[i];h=tex.parse(data)
    assert tex.FMT_GU[h['fmt']]=='rgba8' and h['mips']==1
    old=np.array(tex.decode(data));image=old.copy();scale=old.shape[1]//256
    assert old.shape[:2]==(512*scale,256*scale)
    changed=np.zeros(old.shape[:2],bool)
    for x,y,n in ((184,48,16),(208,32,24)):
        x*=scale;y*=scale;n*=scale
        assert old[y:y+n,x:x+n,3].max()<=8,'Atlas cell occupied'
        image[y:y+n,x:x+n]=silhouette(n);changed[y:y+n,x:x+n]=True
    encoded=tex.encode_gu(image,'rgba8',mips=1);decoded=np.array(tex.decode(encoded))
    assert np.array_equal(old[~changed],decoded[~changed])
    entries[i]=(name,kind,encoded)
    result=arcpack.build(entries);check=arcpack.read(result)[1]
    original_entries=arcpack.read(original)[1]
    assert all(check[k]==e for k,e in enumerate(original_entries) if k!=i)
    path=MS/'romfs'/rel;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(result)
    preview=HERE/'reports/smithy-icon.png';Image.fromarray(silhouette(96)).save(preview)
    report={'atlas_resource_count':len(entries),'changed_resource_count':1,'other_resources_identical':True,
        'pixels_outside_two_empty_cells_identical':True,'source_arc_sha256':sha(ROM/rel),
        'output_arc_sha256':sha(path),'language':'English','icon_id':121,
        'source':'Procedural silhouette of Frontier wk400 geometry'}
    (HERE/'reports/smithy-icon-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Built isolated equipment icon: two empty cells; all other resources and pixels unchanged.')
if __name__=='__main__':main()
