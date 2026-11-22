"""Build opt-in kill instrumentation as a separate executable, preserving the launcher."""
import json,os,shlex,shutil,subprocess
from prepare_frontier import HERE,ROOT,sha


def main():
    root=ROOT/'MHGURecomp-master';out=HERE/'output/benchmark-runtime';out.mkdir(exist_ok=True)
    tool=root/'obj/toolchain/ucrt64/bin';env=dict(os.environ);env['PATH']=str(tool)+os.pathsep+env.get('PATH','')
    original=sha(root/'build/mhgurecomp.exe')
    lines=(root/'obj/runtime-build.log').read_text(errors='replace').splitlines()
    compiles=[]
    for source,name in [('runtime/hle/dummy.c','dummy'),('runtime/net/hitsync.c','hitsync'),('runtime/host_input.c','host_input')]:
        compile=next(shlex.split(s) for s in lines if s.startswith('clang ') and source+' ' in s)
        compile[0]=str(tool/'clang.exe');compile[compile.index('-o')+1]=str(out/(name+'.o'))
        compiles.append(compile)
    link=next(shlex.split(s) for s in (root/'obj/link-build.log').read_text(errors='replace').splitlines() if s.startswith('clang++ '))
    link[0]=str(tool/'clang++.exe');link[link.index('-o')+1]=str(out/'mhgurecomp.exe')
    link=[str(out/'dummy.o') if a=='obj/rt/hle/dummy.o' else a for a in link]
    link=[str(out/'hitsync.o') if a=='obj/rt/net/hitsync.o' else a for a in link]
    link=[str(out/'host_input.o') if a=='obj/rt/host_input.o' else a for a in link]
    link=[('-Wl,--out-implib,'+str(out/'mhgurecomp.dll.a')) if a.startswith('-Wl,--out-implib,') else a for a in link]
    log=[]
    for args in (*compiles,link):
        r=subprocess.run(args,cwd=root,env=env,capture_output=True,text=True);log.append(r.stdout+r.stderr)
        (out/'build.log').write_text('\n'.join(log),encoding='utf-8')
        if r.returncode:raise RuntimeError('Benchmark runtime build failed; see '+str(out/'build.log'))
    for f in (root/'build').glob('*.dll'):shutil.copyfile(f,out/f.name)
    assert sha(root/'build/mhgurecomp.exe')==original
    report={'original_executable_unchanged':True,'original_sha256':original,'benchmark_sha256':sha(out/'mhgurecomp.exe'),
        'source_sha256':sha(root/'runtime/hle/dummy.c'),'opt_in':'MHGU_DUMMY plus MHGU_BALANCE_KILL=1',
        'behavior':'Native HP/damage; held target motion; separate executable used only by balance fixtures'}
    (HERE/'reports/balance-runtime-build.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Built separate benchmark runtime; original launcher executable unchanged.')


if __name__=='__main__':main()
