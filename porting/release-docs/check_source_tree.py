"""Check a publication tree without importing tools or reading game inputs."""
from pathlib import Path
import sys

FORBIDDEN_DIRS={'.venv','__pycache__','dump','gen','romfs','out','output','work',
    'runs','backups','ryuroot','test-profile','release-validation','node_modules','target'}
FORBIDDEN_SUFFIXES={'.arc','.bin','.nso','.ips','.zip','.7z','.nsp','.xci','.exe',
    '.dll','.wav','.png','.tex','.keys','.env','.pkl','.pyc','.jpg','.mp4'}


def check(root):
    failures=[];count=0
    for p in root.rglob('*'):
        rel=p.relative_to(root)
        if '.git' in rel.parts:continue
        if any(x.lower() in FORBIDDEN_DIRS for x in rel.parts):
            failures.append(str(rel));continue
        if p.is_symlink():failures.append(str(rel));continue
        if not p.is_file():continue
        count+=1
        if p.suffix.lower() in FORBIDDEN_SUFFIXES or p.name in {'system','system_backup'} or p.name.startswith('subsdk'):
            failures.append(str(rel))
    if failures:raise RuntimeError('Publication tree contains forbidden paths: '+', '.join(failures[:12]))
    return count


if __name__=='__main__':
    print('Source-only files checked:',check(Path(sys.argv[1]).resolve() if len(sys.argv)>1 else Path(__file__).resolve().parent))
