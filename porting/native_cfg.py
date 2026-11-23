"""Collect bounded ARM function addresses without emitting native game code."""
import re
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM


def instruction_addresses(data, *functions):
    dis = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    allowed = set()
    for fn in functions:
        todo, seen = [fn], set()
        while todo:
            address = todo.pop()
            while address not in seen and fn <= address < fn + 0x1000:
                ins = next(dis.disasm(data[address:address + 4], address), None)
                if ins is None: break
                seen.add(address)
                op, operands = ins.mnemonic, ins.op_str
                if re.fullmatch(r'b(?:eq|ne|hs|lo|mi|pl|vs|vc|hi|ls|ge|lt|gt|le)?', op):
                    todo.append(int(operands.removeprefix('#'), 0))
                    if op == 'b': break
                if op.startswith(('bx', 'pop', 'ldm')) and ('lr' in operands if op.startswith('bx') else 'pc' in operands):
                    if op in ('bx', 'pop', 'ldm', 'ldmia'): break
                address += 4
        allowed.update(seen)
    return allowed
