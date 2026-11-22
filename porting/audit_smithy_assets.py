"""Prove smithy additions preserve every installed gameplay/sound asset."""
import json
from build_smithy_tree import HERE,MS,audit,sha

def files(path):return {str(p.relative_to(path)):sha(p) for p in path.rglob('*') if p.is_file()}

def main():
    before=files(HERE/'backups/before-smithy-tree/mod');after=files(HERE/'output/magnet-spike-experimental')
    changed=[n for n,h in before.items() if after.get(n)!=h]
    added=sorted(set(after)-set(before));removed=sorted(set(before)-set(after))
    allowed={n for n in before if n.startswith('exefs\\')}
    expected={f'romfs\\nativeNX\\arc\\weapon\\w05\\{n:03d}.arc' for n in range(2,41)}
    expected.add('romfs\\nativeNX\\eng\\arc\\resident_eng.arc')
    tables,_,_,_=audit()
    report={'checks':{'no_installed_asset_removed':not removed,
        'only_module_and_patch_changed_among_prior_files':set(changed)==allowed,
        'only_39_models_and_one_icon_atlas_added':set(added)==expected,
        'original_gs_tables_match_tree_audit':{k:v[1] for k,v in tables.items()}==json.loads((HERE/'reports/smithy-tree-build.json').read_text())['source_table_hashes']},
        'file_count':len(after),'changed_file_count':len(changed),'added_file_count':len(added),
        'unchanged_prior_asset_count':len(before)-len(changed),'mod_files':after}
    report['all_passed']=all(report['checks'].values())
    (HERE/'reports/smithy-asset-audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Smithy asset preservation:',report['all_passed'],'files:',len(after),'prior assets unchanged:',report['unchanged_prior_asset_count'])
    assert report['all_passed']
if __name__=='__main__':main()
