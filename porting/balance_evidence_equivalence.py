"""Prove an earlier native run used unchanged code, assets and active hit powers.

Only the fixed-size live MV array may differ between the two modules. Every
armed or collided hit in the retained run must have identical normal/Magnetise
power. Code, KO data, level-stat scaling, patches and all assets must be byte
identical. A changed active move therefore requires a fresh native run.
"""
import json,re,struct,sys
from pathlib import Path
from prepare_frontier import HERE,CONVERTER,sha


def prove(run,folder,target,expected):
    if run['mod_files']==expected:return {'exact_files':True}
    old=folder/'mods/magnet-spike-experimental'
    nso_key=str(Path('exefs/subsdk1'))
    if set(run['mod_files'])!=set(expected):return None
    if any(v!=expected[k] for k,v in run['mod_files'].items() if k!=nso_key):return None
    if any(sha(old/k)!=v for k,v in run['mod_files'].items()):return None
    sys.path.insert(0,str(CONVERTER/'tools'));import nso
    try:
        left,left_segs,left_bss=nso.flat((old/'exefs/subsdk1').read_bytes())
        right,right_segs,right_bss=nso.flat((target/'exefs/subsdk1').read_bytes())
    except (AssertionError,ValueError,struct.error):return None
    if len(left)!=len(right) or left_bss!=right_bss:return None
    if [(x[0],x[1]) for x in left_segs]!=[(x[0],x[1]) for x in right_segs]:return None
    symbols=json.loads((HERE/'output/symbols.json').read_text(encoding='utf-8'))
    start=symbols['ms_balance_mv'];count=281;end=start+2*count
    if not 0<=start<end<=len(left):return None
    if left[:start]!=right[:start] or left[end:]!=right[end:]:return None
    text=(folder/'log.txt').read_text(errors='replace')
    hits={int(v) for v in re.findall(r'msport: (?:armed hit|hit) (\d+)\b',text)}
    if not hits or not all(0<=h<count for h in hits):return None
    # Check both banks even if only one form of Magnetise was active that run.
    both=hits|{h+140 if 0<h<=140 else h-140 for h in hits if h}
    if any(left[start+2*h:start+2*h+2]!=right[start+2*h:start+2*h+2] for h in both):return None
    return {'exact_files':False,'source_module_sha256':sha(old/'exefs/subsdk1'),
        'target_module_sha256':sha(target/'exefs/subsdk1'),
        'only_MV_array_differs':True,'all_code_KO_stats_patches_assets_identical':True,
        'all_armed_and_collided_hit_ids_unchanged':sorted(hits),
        'normal_and_Magnetise_powers_verified':True,
        'scope':'Retained native measurement of byte-identical code/assets and unchanged active hit powers; not a native run of the new module hash.'}
