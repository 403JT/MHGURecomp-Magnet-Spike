"""Correlate observed smithy UI with native saved equipment/material changes.

Reads disposable saves only; never edits them. Game data remains private.
The required screenshots were inspected during the live UI session.
"""
import argparse,collections,json,re,struct
from PIL import Image
from prepare_frontier import HERE,sha
from prepare_test_profile import BOX,WORN,ENTRY,BOX_COUNT,SLOT_SIZE,FILE_SIZE
from build_smithy_tree import audit

SHOTS=['gs-baseline','ms-category','ms-before-forge','ms-forge-confirm','ms-forged',
    'ms-upgrade-box','ms-upgrade-level','ms-upgrade-materials','upgrade-quantity',
    'upgrade-paid-check','ms-levelup-confirm','ms-level2','ms-branch-materials',
    'ms-branch-confirm','ms-branched','save-menu']

def slot(data):
    assert len(data)==FILE_SIZE
    n=data[0x2b];assert n<3 and data[0x28+n]
    base=0x24+struct.unpack_from('<I',data,0x34+4*n)[0]
    assert 0x40<=base<=len(data)-SLOT_SIZE
    return base

def equipment(data,base):return [data[base+BOX+i*ENTRY:base+BOX+(i+1)*ENTRY] for i in range(BOX_COUNT)]
def item_counts(data,base):
    counts=collections.Counter()
    for offset,n in ((0x278,2300),(0x27bf,32)):
        stream=int.from_bytes(data[base+offset:base+offset+(19*n+7)//8],'little')
        for i in range(n):
            word=(stream>>(19*i))&0x7ffff;ident=word&4095
            if ident:counts[ident]+=(word>>12)&127
    return counts

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--reload',required=True);a=p.parse_args()
    path=HERE/'runs'/a.run;reload=HERE/'runs'/a.reload
    run=json.loads((path/'run.json').read_text());again=json.loads((reload/'run.json').read_text())
    source=(HERE/'test-profile/save/save_0/system').read_bytes()
    saved=(path/'save/save_0/system').read_bytes();reloaded=(reload/'save/save_0/system').read_bytes()
    base=slot(source);assert slot(saved)==base
    old=equipment(source,base);new=equipment(saved,base)
    tables,models,mapping,_=audit();first=tables['base'][0][1]
    children=[first[24+2*k] for k in range(5) if first[23+2*k]==2]
    assert len(children)==1;child=children[0]
    added=[i for i,(x,y) in enumerate(zip(old,new)) if not any(x) and any(y)]
    assert len(added)==1
    index=added[0];kind,ident=struct.unpack_from('<HH',new[index]);level=((kind>>5)&31)+1
    original_preserved=all(x==y for x,y in zip(old,new) if any(x))
    expected=collections.Counter()
    create=next(r for r in tables['create'][0] if struct.unpack_from('<HH',r)==(1,1))
    process=next(r for r in tables['process'][0] if struct.unpack_from('<HH',r)==(child,1))
    for j in range(4):
        item=struct.unpack_from('<H',create,6+4*j)[0]
        if item:expected[item]-=create[8+4*j]
        item=struct.unpack_from('<H',process,4+3*j)[0]
        if item:expected[item]-=process[6+3*j]
    # Observed normal provision choice: one Machalite Ore, worth four Ore LV1
    # points. It is also the third material in this branch's original GS row.
    provision=struct.unpack_from('<H',process,10)[0];expected[provision]-=1
    for data,start in ((create,26),(process,20)):
        for j in range(3):
            item,num=struct.unpack_from('<HH',data,start+4*j)
            if item:expected[item]+=num
    old_items=item_counts(source,base);new_items=item_counts(saved,base)
    changed={n:new_items[n]-old_items[n] for n in old_items.keys()|new_items.keys() if new_items[n]!=old_items[n]}
    expected={n:q for n,q in expected.items() if q}
    # UI before/after money readings are independently present in screenshots.
    # Native save duplicates this balance: character-select summary +0x24 and
    # player inventory +0x280f. Both copies changed by exactly the observed sum.
    money_locations=[i for i in range(base,base+SLOT_SIZE-3)
        if source[i:i+4]==struct.pack('<I',215351) and saved[i:i+4]==struct.pack('<I',210876)]
    log=(reload/'log.txt').read_text(encoding='utf-8',errors='replace')
    loaded=[int(v,16) for v in re.findall(r'ms-tree: model '+str(mapping[child])+r' resource ([0-9a-f]+)',log)]
    def valid_png(p):
        try:
            with Image.open(p) as im:im.verify()
            with Image.open(p) as im:im.load();return im.size==(1280,720)
        except (OSError,ValueError):return False
    checks={
        'all_required_ui_screenshots_complete_and_valid':all(valid_png(path/'shots'/f'{n}.png') for n in SHOTS)
            and valid_png(reload/'shots/reloaded-equipment.png'),
        'separate_type_12_weapon_forged_upgraded_and_branched':kind&31==12 and ident==child and level==1,
        'every_original_equipment_entry_including_great_swords_preserved':original_preserved,
        'newly_crafted_branched_weapon_is_equipped':struct.unpack_from('<H',saved,base+WORN)[0]==index,
        'materials_provision_and_returned_scraps_match_original_gs_rows':changed==expected,
        'native_money_spent_matches_1275_plus_1700_plus_1500':set(money_locations)=={base+0x24,base+0x280f},
        'native_save_reloaded_byte_identically':saved==reloaded,
        'independent_extended_model_loaded_after_restart':mapping[child]>7 and any(loaded),
        'both_sessions_use_the_exact_same_candidate':run['mod_files']==again['mod_files'],
        'both_sessions_muted':run['output_muted'] and again['output_muted'],
        'forge_session_exited_cleanly_without_changing_source_saves':run.get('exit_code')==0 and run.get('source_saves_unchanged'),
        'reload_session_exited_cleanly_without_changing_source_saves':again.get('exit_code')==0 and again.get('source_saves_unchanged')}
    report={'all_passed':all(checks.values()),'checks':checks,'mod_files':run['mod_files'],
        'reload_run':a.reload,'saved_system_sha256':sha(path/'save/save_0/system'),
        'new_box_index':index,'saved_type':kind&31,'saved_id':ident,'saved_level':level,
        'extended_model':mapping[child],'money_spent':4475,
        'ui_scope':'Observed forge/equip, ore provision, level 2 and branch confirmations; original GS list retained. Preview framing still needs work.',
        'persistence_evidence':'Native saved equipment, materials and balances plus a fresh reloaded Equipment screen. The generic exit/title image is not persistence evidence.',
        'unused_exit_capture':{'path':str(path/'shots/saved-return.png'),
            'valid':valid_png(path/'shots/saved-return.png'),'used_as_evidence':False},
        'screenshots':{n:sha(path/'shots'/f'{n}.png') for n in SHOTS}}
    (path/'smithy-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Smithy save/reload checks:',sum(bool(v) for v in checks.values()),'/',len(checks))
    if not report['all_passed']:print('Failed checks:',[k for k,v in checks.items() if not v])
    assert report['all_passed']
if __name__=='__main__':main()
