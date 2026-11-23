"""Muted official-runtime fixtures for public-release feedback regressions.

All writes are confined to a new disposable session. Memory samples are local
diagnostics, never source/release contents. Real hunter saves are only copied.
"""
import json
import os
import re
import shutil
import struct
import subprocess
import time

from prepare_frontier import HERE, ROOT, sha


def files(root):
    return {p.relative_to(root).as_posix(): sha(p) for p in root.rglob('*') if p.is_file()}


class Session:
    def __init__(self, label, baseline=False, quest=101, live=False, instrumented=False, payload_root=None, dummy_distance=None, reaction_fixture=False, save_setup=None):
        if not re.fullmatch('[a-z0-9_-]+', label):
            raise ValueError('Invalid evidence label')
        self.folder = HERE / 'runs' / label
        if self.folder.exists():
            raise RuntimeError('Session evidence already exists')
        self.source = HERE / 'test-profile/save/save_0'
        self.source_hashes = {n: sha(self.source / n) for n in ('system', 'system_backup')}
        save = self.folder / 'save/save_0'
        save.mkdir(parents=True)
        for name in self.source_hashes:
            shutil.copyfile(self.source / name, save / name)
        # Optional test-only setup receives the newly created disposable save
        # directory. Original saves remain read-only and are hashed on exit.
        fixture = save_setup(save) if save_setup else None
        payload = payload_root if payload_root is not None else (
            HERE / 'backups/before-feedback-1/public-payload' if baseline
            else HERE / 'output/magnet-spike-experimental')
        self.payload = files(payload)
        shutil.copytree(payload, self.folder / 'mods/Magnet-Spike')
        config = self.folder / 'mhgurecomp.ini'
        config.write_text('[Display]\nMode = Windowed\nResolution = 1280x720\n'
                          '[Application]\nConfirmExit = Off\n[Audio]\nVolume = 0\n', encoding='utf-8')
        self.control = self.folder / 'control.txt'
        self.control.write_text('fps 60\n', encoding='utf-8')
        exe = (ROOT / 'MHGURecomp-master/build/mhgurecomp.exe' if instrumented else
               HERE / 'release-validation/runtime-0.18.0/Windows-MHGURecomp/mhgurecomp.exe')
        expected_exe = ('d8cb5f527abba7ab8a92ba70f8d45fe5d9219b518409bf6d9afbb034c4af7fce' if instrumented else
                        '286be3af1fe5aee7649bb548c33d550b8d52e97f931eafc9db6d6c030d6571b7')
        if sha(exe) != expected_exe:
            raise RuntimeError('Unexpected test runtime')
        env = {k: v for k, v in os.environ.items() if not k.startswith('MHGU_')}
        env.update(MHGU_HOME=str(self.folder), MHGU_SAVE_DIR=str(self.folder / 'save'),
            MHGU_MODS_DIR=str(self.folder / 'mods'), MHGU_CONFIG=str(config),
            MHGU_DATA_DIR=str(ROOT / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data'),
            MHGU_HIDDEN='1', MHGU_AUDIO_GAIN='0', MHGU_PAD_PATH='__feedback_fixture__',
            MHGU_CONTROL=str(self.control), MHGU_LOG_MOVES='1', MHGU_LDN_SERVER='Off',
            MHGU_QUICKHUNT=str(quest))
        if live:
            env.update(MHGU_SUMMON='240', MHGU_SUMMON_FREE='1')
        if reaction_fixture:
            if not live or not instrumented:
                raise ValueError('Reaction fixture requires the isolated live-monster instrumented runtime')
            env.update(MHGU_SUMMON_FREE='0', MHGU_EMTRACE='1')
        if dummy_distance is not None:
            if live:raise ValueError('Dummy fixture cannot also request a free live monster')
            env.update(MHGU_DUMMY=str(dummy_distance),MHGU_DUMMY_FACE='1')
        self.report = {'runtime': 'instrumented Recomp' if instrumented else 'official Windows MHGURecomp 0.18.0',
            'runtime_sha256': expected_exe, 'baseline': baseline,
            'live_monster': live,
            'reaction_fixture_hunter_held_with_test_hp': reaction_fixture,
            'dummy_distance_cm':dummy_distance,
            'payload_files': self.payload, 'muted': True, 'source_saves_unchanged': None,
            'exit_code': None, 'failure': None, 'cases': []}
        if fixture is not None:
            self.report['save_fixture'] = fixture
        self.samples = 0
        with (self.folder / 'console.log').open('wb') as out:
            self.process = subprocess.Popen([str(exe)], cwd=self.folder, env=env,
                stdout=out, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        self.write()

    def log(self):
        path = self.folder / 'log.txt'
        return path.read_text(errors='replace') if path.exists() else ''

    def send(self, text):
        with self.control.open('a', encoding='utf-8') as f:
            f.write(text + '\n')

    def wait(self, predicate, timeout=15):
        until = time.monotonic() + timeout
        while self.process.poll() is None and time.monotonic() < until:
            if 'FATAL:' in self.log():
                raise RuntimeError('Native fatal')
            value = predicate()
            if value:
                return value
            time.sleep(.05)
        raise RuntimeError('Native feedback fixture condition timed out')

    def ready(self):
        self.wait(lambda: 'msport: hunter stats:' in self.log(), 180)
        self.player = int(re.findall(r'msport: class 5 object ([0-9a-f]+)', self.log())[-1], 16)
        time.sleep(7)
        self.send('X 8')
        self.wait(lambda: 'weapon in hand (joint' in self.log(), 20)
        time.sleep(2)

    def memory(self, offset, size):
        self.samples += 1
        path = self.folder / f'memory-{self.samples}.bin'
        self.send(f'memsave {self.player + offset:x} {size:x} {path.name}')
        self.wait(lambda: path.exists() and path.stat().st_size == size, 10)
        return path.read_bytes()

    def state(self):
        action = self.memory(0x2506, 6)
        animation = self.memory(0x4b0, 0x60)
        phase = self.memory(5, 1)[0]
        return {'category': struct.unpack_from('<H', action)[0],
            'action': struct.unpack_from('<H', action, 4)[0], 'step': phase,
            'motion_flags': animation[6], 'motion_end_flag': bool(animation[6] & 4),
            'frame': struct.unpack_from('<f', animation, 0x4c)[0],
            'end_frame': struct.unpack_from('<f', animation, 0x54)[0],
            'speed': struct.unpack_from('<f', animation, 0x5c)[0],
            'blend': struct.unpack_from('<f', animation, 0x44)[0]}

    def write(self):
        (self.folder / 'feedback-native.json').write_text(json.dumps(self.report, indent=2) + '\n', encoding='utf-8')

    def close(self):
        if self.process.poll() is None:
            self.send('sdlquit')
            try:
                self.process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                self.process.wait(timeout=10)
                self.report['failure'] = self.report['failure'] or 'Normal exit timed out'
        self.report.update(exit_code=self.process.returncode,
            source_saves_unchanged=all(sha(self.source / n) == v for n, v in self.source_hashes.items()),
            fatal='FATAL:' in self.log(),
            tested_payload_unchanged=files(self.folder / 'mods/Magnet-Spike') == self.payload)
        self.write()
