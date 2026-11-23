"""Local native-code references; emits addresses, never game bytes or code."""
import argparse
from collections import deque
import hashlib
import json
import re
import struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
from prepare_frontier import HERE


def references():
    data=(HERE/'work/gu_main/mem.bin').read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    cache=HERE/'work/feedback-native-pcrefs.json'
    if cache.exists():
        result=json.loads(cache.read_text(encoding='utf-8'))
        if result['source_sha256']==digest:return result['references']
    dis=Cs(CS_ARCH_ARM,CS_MODE_ARM);dis.skipdata=True
    history=deque(maxlen=12);out=[]
    word=lambda at:struct.unpack_from('<I',data,at)[0] if 0<=at<=len(data)-4 else None
    for address,size,op,args in dis.disasm_lite(data[:0x13f1dec],0):
        add=re.fullmatch(r'(\w+), pc, (\w+)',args) if op=='add' else None
        load=re.fullmatch(r'(\w+), \[pc, (\w+)\]',args) if op=='ldr' else None
        match=add or load
        if match:
            reg=match[2]
            for previous,oldop,oldargs in reversed(history):
                literal=re.fullmatch(re.escape(reg)+r', \[pc(?:, #(-?(?:0x[0-9a-f]+|\d+)))?\]',oldargs)
                if oldop=='ldr' and literal:
                    value=word(previous+8+int(literal[1] or '0',0))
                    if value is not None:
                        target=(address+8+value)&0xffffffff
                        resolved=word(target) if load else target
                        if resolved is not None:out.append([address,resolved,target if load else None])
                    break
                if oldargs.split(',')[0]==reg and oldop not in ('cmp','cmn','tst','str','strb','strh','push'):
                    break
        history.append((address,op,args))
    cache.write_text(json.dumps({'source_sha256':digest,'references':out}),encoding='utf-8')
    return out


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target',type=lambda v:int(v,16))
    parser.add_argument('--span',type=lambda v:int(v,16),default=1)
    args=parser.parse_args()
    refs=references()
    found=[{'site':hex(a),'target':hex(t),'slot':hex(s) if s is not None else None}
           for a,t,s in refs if args.target<=t<args.target+args.span]
    print(json.dumps({'reference_count':len(refs),'matches':found}))


if __name__=='__main__':main()
