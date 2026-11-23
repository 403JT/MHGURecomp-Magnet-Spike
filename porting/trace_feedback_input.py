"""Trace native GU input dispatch for local and remote synthetic hunters."""
import json
from unicorn import arm_const as A
from test_runtime import Emulator, BASE, HEAP, PLAYER, compile_test
from build_module import HERE


class Dispatch(Emulator):
    def __init__(self, binary, local):
        super().__init__(binary)
        self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.symbols['native_input']=BASE+0x27c97c
        self.visits=[]
        vt=HEAP+0x200000
        self.w32(PLAYER,vt)
        self.w32(PLAYER+0x13c4,HEAP+0x210000)
        self.uc.mem_write(HEAP+0x2104d4,b'\5')
        self.uc.mem_write(PLAYER+0x13cc,bytes([local]))
        for slot in range(556):self.w32(vt+slot*4,BASE+0x10000+slot*4)

    def engine(self,u,address,size,arg):
        off=address-BASE
        if 0x27c97c<=off<0x27ca28:return
        self.visits.append({'vtable_slot':(off-0x10000)//4} if 0x10000<=off<0x10000+556*4
                           else {'native_call':hex(off)})
        u.reg_write(A.UC_ARM_REG_R0,1 if off==0x10000+138*4 else 0)
        u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))


def main():
    binary=compile_test()
    rows=[]
    for local in (0,1):
        e=Dispatch(binary,local)
        e.call('native_input',PLAYER)
        rows.append({'local_flag':local,'calls':e.visits,
                     'local_input_copy_dispatched':any(v.get('vtable_slot')==138 for v in e.visits)})
    (HERE/'reports/feedback-native-input.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(rows))
    assert not rows[0]['local_input_copy_dispatched'] and rows[1]['local_input_copy_dispatched']


if __name__=='__main__':main()
