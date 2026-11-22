"""Bound renderer-cache storage for disposable runs; retain all test evidence."""
import shutil
from prepare_frontier import HERE

FILES=('programs.bin','programs.src','vk_pipelines.bin','pipelines.bin')

def checked(cache):
    cache=cache.absolute()
    root=(HERE/'runs').resolve()
    if cache.name!='cache' or cache.is_symlink() or cache.is_junction() or not cache.resolve().is_relative_to(root):
        raise ValueError('Renderer cache operation outside a disposable run')
    return cache

def seed(cache):
    cache=checked(cache);source=HERE/'test-profile/cache'
    size=sum((source/n).stat().st_size for n in FILES if (source/n).is_file())
    if shutil.disk_usage(HERE).free<size+512*1024*1024:
        raise OSError('Insufficient free space for a disposable renderer cache and test reserve')
    cache.mkdir(parents=True,exist_ok=True)
    for n in FILES:
        if (source/n).is_file():shutil.copyfile(source/n,cache/n)

def retire(cache):
    cache=checked(cache);count=size=0
    for n in FILES:
        p=cache/n
        if not p.exists():continue
        if p.is_symlink() or p.is_junction() or not p.resolve().is_relative_to(cache.resolve()):
            raise ValueError('Unexpected linked renderer cache file')
        size+=p.stat().st_size;p.unlink();count+=1
    return {'retired_file_count':count,'retired_bytes':size,'evidence_files_untouched':True}
