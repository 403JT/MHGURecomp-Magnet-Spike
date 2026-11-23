"""Verify the normal release differs from alpha.2 only by the two fixes."""
import json
import re
import subprocess
from build_module import HERE,MS,UPMOD,OUT,TOOLCHAIN,sha
from feedback_session import files


def main():
    baseline=HERE/'backups/before-sprint-roll-1'
    folder=HERE/'work/roll-draw-release-scope';folder.mkdir(exist_ok=True)
    checks={}
    current=files(HERE/'output/magnet-spike-experimental')
    old=files(baseline/'payload')
    checks['same_payload_paths']=current.keys()==old.keys() and len(current)==56
    checks['only_module_binary_changed']=[p for p in current if current[p]!=old.get(p)]==['exefs/subsdk1']
    checks['normal_build_has_no_diagnostic_define']='MS_FREEZE_DIAGNOSTICS' not in json.loads((OUT/'module-status.json').read_text())['defines']
    checks['normal_elf_has_no_freeze_logging_strings']=b'ms-freeze:' not in (OUT/'magnet-spike.elf').read_bytes()
    flags=['--target=armv7a-none-eabihf','-E','-P','-DMS_RECOMP','-DMS_GS_TREE','-DMS_SLICE','-DMS_BALANCE',
           '-I',str(MS/'module'),'-I',str(MS/'gen'),'-I',str(UPMOD),'-I',str(OUT)]
    def preprocess(source):
        result=subprocess.run([str(TOOLCHAIN/'clang.exe'),*flags,str(source)],capture_output=True,text=True)
        if result.returncode:raise RuntimeError('Source-scope preprocessing failed')
        # No preprocessed tables are printed or packaged. Token comparison
        # ignores formatting while preserving string contents and operators.
        return re.findall(r'"(?:\\.|[^"\\])*"|\w+|[^\s]',result.stdout)
    for name in ('ms_act.c','ms_class.c'):
        text=(MS/'module'/name).read_text(encoding='utf-8')
        if name=='ms_act.c':
            assert text.count('if (ms_drawn(p) && (held & r))')==1
            text=text.replace('if (ms_drawn(p) && (held & r))','if (held & r)')
            line='    int guard_draw = no == 112 && !ms_drawn(p);\n'
            assert text.count(line)==1 and text.count(' || guard_draw')==1
            text=text.replace(line,'').replace(' || guard_draw','')
        else:
            lines=('    static const uint16_t s_guard_draw[3] = {0x10,112,0};\n'
                   '    if ((k==2 || k==4) && FIELD(uint16_t,p,0x2506)!=4) return s_guard_draw;\n')
            assert text.count(lines)==1;text=text.replace(lines,'')
        restored=folder/name;restored.write_text(text,encoding='utf-8')
        checks[name+'_matches_alpha2_after_reverting_only_two_fixes']=preprocess(restored)==preprocess(baseline/'module'/name)
    checks['all_other_weapon_module_sources_preserved']=all(sha(p)==sha(baseline/'module'/p.name)
        for p in (MS/'module').iterdir() if p.is_file() and p.name not in ('ms_act.c','ms_class.c'))
    checks['all_local_module_sources_preserved']=all(sha(p)==sha(baseline/'local-module'/p.name)
        for p in (HERE/'module').iterdir() if p.is_file())
    report={'all_passed':all(checks.values()),'checks':checks,'payload_files':current,
            'scope':'Default Recomp build; optional diagnostic branches preprocessed out; only sprint-roll and guard-draw code changes remain'}
    (HERE/'reports/roll-draw-release-scope.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'all_passed':report['all_passed'],'checks':checks}));assert report['all_passed']


if __name__=='__main__':main()
