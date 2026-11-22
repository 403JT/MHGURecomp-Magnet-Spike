"""Run the existing ARM/codec regressions and new damage/level-field checks."""
import argparse,json,re,subprocess,sys
from prepare_frontier import HERE,ROOT,sha


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prefix',default='balance')
    args=parser.parse_args();assert re.fullmatch('[a-z0-9_-]+',args.prefix)
    mod=HERE/'output/magnet-spike-experimental'
    def files():return {str(f.relative_to(mod)):sha(f) for f in mod.rglob('*') if f.is_file()}
    expected=files();path=HERE/'reports'/f'{args.prefix}-static-pipeline.json'
    if path.exists():raise RuntimeError('Static evidence already exists')
    report={'mod_files':expected,'steps':[],'all_passed':False}
    names=['runtime','hooks','moveset','sounds','pin','command_windows','hitstats','native_hitstats',
        'aim','worldhits','worldhook','hit_layout','cancel_windows','cancel_hook','command_routes','audio_codec','smithy_tree','balance']
    for name in names:
        assert files()==expected
        r=subprocess.run([sys.executable,str(HERE/f'test_{name}.py')],cwd=ROOT,capture_output=True,text=True)
        out=HERE/'reports'/f'{args.prefix}-check-{name}.txt';out.write_text(r.stdout+r.stderr,encoding='utf-8')
        report['steps'].append({'suite':name,'passed':r.returncode==0,'output':str(out)})
        path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
        if r.returncode:raise RuntimeError('Static check failed: '+str(out))
    report['all_passed']=True;path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('All18 ARM/static/codec suites passed.')


if __name__=='__main__':main()
