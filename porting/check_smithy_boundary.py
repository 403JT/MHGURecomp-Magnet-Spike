"""After the immutable batch, verify the highest equipment ID without repeating passed cases."""
import argparse,json,subprocess,sys,time
from prepare_frontier import HERE,ROOT
from validate_smithy_build import files

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--batch',default='smithy18-batch.json');args=parser.parse_args()
    expected=files();batch=(HERE/'reports'/args.batch).resolve();deadline=time.monotonic()+3600
    if not batch.is_relative_to((HERE/'reports').resolve()):raise ValueError('Invalid batch path')
    while time.monotonic()<deadline:
        data=json.loads(batch.read_text(encoding='utf-8'))
        if data['mod_files']!=expected:raise RuntimeError('Candidate changed')
        if any(s['status']=='failed' for s in data['steps']):raise RuntimeError('Batch failed; boundary test not launched')
        if data['all_passed']:break
        time.sleep(1)
    else:raise RuntimeError('Batch did not finish within the bounded wait')
    print('Checking highest weapon ID after retained successful cases.',flush=True)
    result=subprocess.run([sys.executable,str(HERE/'test_equipment_runtime.py'),'--prefix','smithy19',
        '--continue-from','smithy12-equipment-runtime.json'],cwd=ROOT,capture_output=True,text=True)
    (HERE/'reports/smithy19-boundary-console.txt').write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError('Boundary test failed; see smithy19-boundary-console.txt')
    print('All14 native equipment cases passed, including highest ID136.',flush=True)
if __name__=='__main__':main()
