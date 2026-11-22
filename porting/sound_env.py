"""Paths and readers for local-only Magnet Spike sound conversion."""
import os
import sys
from prepare_frontier import CLIENT, CONVERTER, HERE, OUT, ROOT

os.environ['GU_ROMFS'] = str(ROOT / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data/romfs')
os.environ['GU_EXEFS'] = str(ROOT / 'MHGURecomp.0.14.0/Windows-MHGURecomp/data/exefs')
os.environ['GU_CODE'] = str(HERE / 'work/gu_main')
sys.path[:0] = [str(CONVERTER / 'tools'), str(CONVERTER / 'weapons/magnet_spike/tools')]
import paths
sys.path.append(paths.GU_PY)
import arcpack
import mhfsnd
import snd4u2gu as snd
from romfs import RomFS

def entries(relative):
    return arcpack.read(RomFS(paths.GU_ROMFS).read('/nativeNX/arc/' + relative))[1]
