"""Launch the isolated profile hidden; runtime's own quickhunt/control API drives it."""
import json
import os
import subprocess
import argparse
import shutil
from prepare_test_profile import PROFILE
from prepare_frontier import HERE, ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--retry', action='store_true')
    parser.add_argument('--quest', default='town')
    args = parser.parse_args()
    if (HERE / 'smoke-process.json').exists() and not args.retry:
        raise RuntimeError('A previous smoke-process record exists; inspect it before another launch')
    if args.quest != 'town' and not args.quest.isdigit():
        raise ValueError('Quest must be town or a numeric quest ID')
    if (PROFILE / 'log.txt').exists():
        shutil.copyfile(PROFILE / 'log.txt', HERE / 'previous-runtime.log')
    (PROFILE / 'control.txt').write_text('', encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if not k.startswith('MHGU_')}
    env.update({'MHGU_HOME': str(PROFILE), 'MHGU_DATA_DIR': str(ROOT / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
                'MHGU_SAVE_DIR': str(PROFILE / 'save'), 'MHGU_CONFIG': str(PROFILE / 'mhgurecomp.ini'),
                'MHGU_MODS_DIR': str(PROFILE / 'mods'), 'MHGU_HIDDEN': '1', 'MHGU_QUICKHUNT': args.quest,
                'MHGU_AUDIO_GAIN': '0',
                'MHGU_LOG_MOVES': '1',
                'MHGU_LDN_SERVER': 'Off', 'MHGU_CONTROL': str(PROFILE / 'control.txt')})
    output = (PROFILE / 'console.log').open('wb')
    process = subprocess.Popen([str(ROOT / 'MHGURecomp-master/build/mhgurecomp.exe')], cwd=PROFILE, env=env,
                               stdout=output, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
    output.close()
    record = {'pid': process.pid, 'profile': str(PROFILE), 'test': 'isolated hidden startup', 'quest': args.quest,
              'output_muted':True}
    (HERE / 'smoke-process.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record))
    result = process.wait()
    record['exit_code'] = result
    (HERE / 'smoke-process.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print('Runtime exit code:', result, flush=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
