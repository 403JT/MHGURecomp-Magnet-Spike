"""Local instruction-level inspection for the sound port. Never emits file bytes."""
import argparse
import struct
import capstone
from prepare_frontier import CLIENT,HERE

def image(kind):
    if kind=='gu':
        return (HERE/'work/gu_main/mem.bin').read_bytes(),0,capstone.Cs(capstone.CS_ARCH_ARM,capstone.CS_MODE_ARM)
    raw=(CLIENT/'mhfo-hd.dll').read_bytes()
    pe=struct.unpack_from('<I',raw,0x3c)[0]
    sections,optsize=struct.unpack_from('<H12xH',raw,pe+6)
    op=pe+24
    base=struct.unpack_from('<I',raw,op+28)[0]
    size=struct.unpack_from('<I',raw,op+56)[0]
    data=bytearray(size)
    for i in range(sections):
        off=op+optsize+i*40
        va,n,src=struct.unpack_from('<III',raw,off+12)
        data[va:va+n]=raw[src:src+n]
    return data,base,capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32)

def main():
    p=argparse.ArgumentParser();p.add_argument('kind',choices=['gu','mhf']);p.add_argument('address',type=lambda s:int(s,16));p.add_argument('--size',type=lambda s:int(s,16),default=0x100);p.add_argument('--xrefs',action='store_true');args=p.parse_args()
    data,base,dis=image(args.kind)
    if args.xrefs:
        found=[]
        if args.kind=='mhf':
            for off in range(len(data)-5):
                if data[off]==0xe8 and base+off+5+struct.unpack_from('<i',data,off+1)[0]==args.address:found.append(hex(base+off))
        else:
            for off in range(0,min(len(data),0x1400000)-4,4):
                word=struct.unpack_from('<I',data,off)[0]
                if word>>24!=0xeb:continue
                imm=word&0xffffff
                if imm&(1<<23):imm-=1<<24
                if off+8+imm*4==args.address:found.append(hex(off))
        print('Call sites:',', '.join(found));return
    for i in dis.disasm(bytes(data[args.address-base:args.address-base+args.size]),args.address):
        print(f'{i.address:x} {i.mnemonic} {i.op_str}')

if __name__=='__main__':main()
