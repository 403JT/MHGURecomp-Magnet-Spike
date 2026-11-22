"""Replay the observed smithy transactions on an already-running disposable town.

Every checkpoint is captured; independent native save comparison determines
success. This driver never edits a save or touches a user's live profile.
"""
import argparse,time
from PIL import Image
from prepare_frontier import HERE,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True)
    p.add_argument('--skip-dialogue',action='store_true',help='Start after visually confirming the forge category menu')
    a=p.parse_args()
    folder=HERE/'runs'/a.run
    if not folder.resolve().is_relative_to((HERE/'runs').resolve()):raise ValueError('Invalid disposable run')
    control=folder/'control.txt';log_path=folder/'log.txt'
    def send(s):
        with control.open('a',encoding='utf-8') as f:f.write(s+'\n')
    def step(commands,shot=None,wait=1.8):
        send(commands);time.sleep(wait)
        if shot:
            target=folder/'shots'/f'{shot}.png'
            if target.exists():raise RuntimeError('Checkpoint already exists')
            send('shot '+shot);deadline=time.monotonic()+20
            complete=False
            while time.monotonic()<deadline:
                try:
                    with Image.open(target) as im:im.verify()
                    with Image.open(target) as im:im.load();assert im.size==(1280,720)
                    complete=True;break
                except (OSError,ValueError,AssertionError):time.sleep(.1)
            if not complete:raise RuntimeError('Checkpoint did not finish encoding: '+shot)
            print('Captured',shot,flush=True)
    deadline=time.monotonic()+110
    while time.monotonic()<deadline:
        text=log_path.read_text(encoding='utf-8',errors='replace') if log_path.exists() else ''
        if 'set 0001:1000 param 2' in text:break
        time.sleep(.2)
    else:raise RuntimeError('Observed smithy approach did not enter the dialogue')
    if not a.skip_dialogue:
        time.sleep(2)
        step('\n'.join(f'A 5 {n*140}' for n in range(9)),wait=21)
    step('A 4','gs-baseline')
    step('B 4\nRIGHT 4 25\nRIGHT 4 50','ms-category')
    step('A 4','ms-before-forge')
    step('A 4','ms-forge-confirm')
    step('A 4','ms-forged')
    step('LEFT 4\nA 4 25\nB 4 120\nB 4 160',wait=3.6)
    step('DOWN 4\nDOWN 4 25\nA 4 50')
    step('DOWN 4\nDOWN 4 25\nRIGHT 4 50\nRIGHT 4 75','ms-upgrade-box',wait=2.2)
    step('A 4','ms-upgrade-level')
    step('A 4','ms-upgrade-materials')
    step('DOWN 4\nDOWN 4 25\nA 4 50','upgrade-quantity')
    step('A 4','upgrade-paid-check')
    step('A 4','ms-levelup-confirm')
    step('A 4','ms-level2')
    step('DOWN 4','ms-branch-materials')
    step('A 4','ms-branch-confirm')
    step('A 4','ms-branched')
    step('B 4\nB 4 30\nB 4 60\nB 4 120\nPLUS 4 190','save-menu',wait=4.3)
    step('RIGHT 4')
    step('UP 4\nA 4 30')
    step('LEFT 4\nA 4 30')
    before=sha(folder/'save/save_0/system')
    step('A 4','saved-return',wait=4)
    if sha(folder/'save/save_0/system')==before:raise RuntimeError('Native save did not change')
    send('sdlquit')
    print('Replay ended; native save verification is still required.',flush=True)
if __name__=='__main__':main()
