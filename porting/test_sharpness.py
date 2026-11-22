"""Run GU's native sharpness getter, skills and restoration against all GS levels.

Native code and source tables are read locally and never exported. Only counts,
pass/fail findings, and hashes enter the report. Unrelated resource services and
sound notifications use bounded fixtures; sharpness arithmetic stays native.
"""
import json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
from unicorn import arm_const as A
from build_module import HERE
from build_smithy_tree import audit,entries,table
from prepare_frontier import sha
from hunt_session import files

H,STACK,RET=0xc000000,0x71000000,0x70000000
BASE,LEVEL,ENTRY,STATS,KIRE,PLAYER,VT=[H+x for x in (0x1000,0x2000,0x3000,0x10000,0x20000,0x30000,0x40000)]
SITE=0xdb91c


def ips_records(path):
    b=path.read_bytes();assert b[:5]==b'IPS32' and b[-4:]==b'EEOF'
    out={};at=5
    while at<len(b)-4:
        addr,size=struct.unpack_from('>IH',b,at);at+=6
        assert size and addr>=0x100 and addr-0x100 not in out
        out[addr-0x100]=b[at:at+size];at+=size
    assert at==len(b)-4
    return out


class NativeSharpness:
    def __init__(self,image,kire,patched):
        self.u=u=Uc(UC_ARCH_ARM,UC_MODE_ARM);u.ctl_set_cpu_model(A.UC_CPU_ARM_MAX)
        u.mem_map(0,0x2600000);u.mem_write(0,image)
        for at,n in ((H,0x100000),(STACK,0x10000),(RET,4096)):u.mem_map(at,n)
        u.reg_write(A.UC_ARM_REG_C1_C0_2,0xf<<20);u.reg_write(A.UC_ARM_REG_FPEXC,0x40000000)
        if patched:u.mem_write(SITE,patched)
        self.kire=kire;self.ty=7;self.skills={};self.getter_calls=0
        self.w32(PLAYER,VT);self.w32(VT+0x1fc,RET+0x100);self.w32(VT+0x3ac,RET+0x104)
        u.hook_add(UC_HOOK_CODE,self.engine)

    def w32(self,p,v):self.u.mem_write(p,struct.pack('<I',v))
    def r32(self,p):return struct.unpack('<I',self.u.mem_read(p,4))[0]
    def engine(self,u,pc,size,_):
        result=None
        if pc in (0x13c208,0x13eef8):
            assert u.reg_read(A.UC_ARM_REG_R1)==self.ty
            result=BASE
        elif pc==0xf6cf4:result=self.ty # native GS type constant / cloned MS getType
        elif pc==0x13ed08:
            assert u.reg_read(A.UC_ARM_REG_R1)==self.ty
            assert u.reg_read(A.UC_ARM_REG_R2)==self.index
            result=LEVEL;self.getter_calls+=1
        elif pc==0x13f290:
            idx=u.reg_read(A.UC_ARM_REG_R1);assert idx<len(self.kire)
            u.mem_write(KIRE,b'\0'*4+self.kire[idx]);result=KIRE
        elif pc==0xe0da0:result=int(u.reg_read(A.UC_ARM_REG_R1) in self.skills)
        elif pc==0x13efd7c:
            u.mem_write(u.reg_read(A.UC_ARM_REG_R0),bytes(u.reg_read(A.UC_ARM_REG_R1)))
            result=0
        elif pc==0x27bcd0:result=1 # quest hunter
        elif pc==0x27b918:result=0 # not Prowler
        elif pc==0x27c7ec:result=0 # established melee-class predicate
        elif pc==0x29cdfc:
            u.reg_write(A.UC_ARM_REG_R0,LEVEL)
            u.reg_write(A.UC_ARM_REG_R1,self.r32(PLAYER+0x2774))
            u.reg_write(A.UC_ARM_REG_PC,0xf4794);return
        elif pc==RET+0x100:result=self.r32(PLAYER+0x13f0)
        elif pc==RET+0x104:result=0 # colour-change sound notification
        if result is not None:
            u.reg_write(A.UC_ARM_REG_R0,result)
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))

    def call(self,pc,*args):
        u=self.u
        for r,v in zip((A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3),args):u.reg_write(r,v)
        u.reg_write(A.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(A.UC_ARM_REG_LR,RET)
        u.emu_start(pc,RET,count=100000)
        assert u.reg_read(A.UC_ARM_REG_PC)==RET,hex(u.reg_read(A.UC_ARM_REG_PC))
        return u.reg_read(A.UC_ARM_REG_R0)

    def fixture(self,base,row,ty):
        self.ty=ty;self.index=struct.unpack_from('<I',row)[0]
        first=self.index-(row[5]-1)
        b=bytearray(40);struct.pack_into('<I',b,0,0x173791c)
        b[4:23]=base[:19];b[24:28]=base[19:23]
        for j in range(5):b[28+j]=base[23+j*2];b[33+j]=base[24+j*2]
        struct.pack_into('<H',b,38,first);self.u.mem_write(BASE,bytes(b))
        self.u.mem_write(LEVEL,struct.pack('<I',0x1737c24)+row+b'\0')
        self.u.mem_write(ENTRY,bytes(44));self.u.mem_write(ENTRY+4,struct.pack('<HH',ty|((row[5]-1)<<5),row[4]))

    def stat(self,base_value,bonus):
        self.u.mem_write(STATS,bytes(0x400))
        self.u.mem_write(STATS+0x150,struct.pack('<h',base_value))
        self.skills={0x53} if bonus==2 else {0x54} if bonus==1 else set()
        self.call(0xe1eec,STATS,0,0)
        return struct.unpack('<h',self.u.mem_read(STATS+0x338,2))[0]


def main():
    tables,*_=audit();base=tables['base'][0];rows=tables['level'][0]
    kire,_=table(entries('nativeNX/loc/arc/resident.arc'),'kireajiData',14)
    image=(HERE/'work/gu_main/mem.bin').read_bytes()
    mod=HERE/'output/magnet-spike-experimental'
    patches=ips_records(next((mod/'exefs').glob('*.ips')))
    before=ips_records(next((HERE/'test-profile/mods/magnet-spike-experimental/exefs').glob('*.ips')))
    # The previous installed build may already be this fix when rechecking.
    before.pop(SITE,None)
    baseline=json.loads((HERE/'backups/before-sharpness-1/baseline.json').read_text())
    candidate=files(mod)
    changed=[n for n,v in candidate.items() if baseline['candidate_files'].get(n)!=v]
    checks={
        'only_one_added_IPS_record':{k:v for k,v in patches.items() if k!=SITE}==before and SITE in patches,
        'mask_adds_only_equipment_type_12':int.from_bytes(patches[SITE],'little') ^ struct.unpack_from('<I',image,SITE)[0]==0x10000,
        'module_and_all_assets_byte_identical':changed==['exefs\\FB08F1D20FD1204FE7070672777F869B.ips'],
    }
    old=NativeSharpness(image,kire,None);new=NativeSharpness(image,kire,patches[SITE])
    getter_ok=legacy_ok=skills_ok=colours_ok=restore_ok=True;legacy_cases=0
    colour_counts={};restoration_cases=0
    for row in rows:
        b=base[row[4]];expected=row[7]
        old.fixture(b,row,7);gs=old.call(0xdb900,ENTRY)
        old.fixture(b,row,12);bad=old.call(0xdb900,ENTRY)
        new.fixture(b,row,12);got=new.call(0xdb900,ENTRY)
        getter_ok &= gs==got==expected
        legacy_ok &= bad==0
        legacy_cases+=int(expected!=0)
        for bonus in (0,1,2):
            stat=new.stat(got,bonus);skills_ok &= stat==min(12,expected+bonus)
            maximum=min(450,150+25*stat)
            colour=new.call(0xf4794,LEVEL,maximum)
            thresholds=struct.unpack('<7H',kire[row[6]])
            want=next(i for i,n in enumerate(thresholds) if n>=maximum)
            colours_ok &= colour==want
            if bonus==0:colour_counts[colour]=colour_counts.get(colour,0)+1
            # GU's actual whetstone amount is +100. Start at red sharpness in
            # this bounded native fixture, restore repeatedly, then test cap.
            new.w32(PLAYER+0x2774,1);new.w32(PLAYER+0x2778,maximum)
            new.w32(PLAYER+0x13f0,new.call(0xf4794,LEVEL,1))
            current=1
            for _ in range(6):
                new.call(0x2ad288,PLAYER,100,0)
                current=min(maximum,current+100)
                restore_ok &= new.r32(PLAYER+0x2774)==current
                restore_ok &= new.r32(PLAYER+0x13f0)==new.call(0xf4794,LEVEL,current)
                restoration_cases+=1
            restore_ok &= new.r32(PLAYER+0x2774)==maximum
    unrelated=True
    for ty in range(32):
        if ty==12:continue
        for e in (old,new):e.fixture(base[1],rows[11],ty)
        unrelated &= old.call(0xdb900,ENTRY)==new.call(0xdb900,ENTRY)
    checks.update(all_959_native_GS_and_MS_sharpness_levels_match=bool(getter_ok),
        old_getter_reproduces_zero_sharpness_level=bool(legacy_ok and legacy_cases),
        Handicraft_0_1_2_native_calculation_and_cap=bool(skills_ok),
        all_native_colours_match_the_original_GS_bars=bool(colours_ok),
        native_whetstone_recovers_from_red_to_full_without_overfill=bool(restore_ok),
        every_other_equipment_type_keeps_original_result=bool(unrelated))
    report={'revision':'sharpness-1','all_passed':all(checks.values()),'checks':checks,
        'levels_checked':len(rows),'old_nonzero_level_regressions_reproduced':legacy_cases,
        'skill_cases':len(rows)*3,'native_whetstone_calls':restoration_cases,
        'top_colour_counts':colour_counts,'mod_files':candidate,
        'IPS_sha256':sha(next((mod/'exefs').glob('*.ips'))),
        'scope':'Original GU ARM getters, Handicraft calculation, colour lookup and whetstone restoration. Synthetic bounded equipment/hunter fixtures; native game validation separate.'}
    (HERE/'reports/sharpness-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Sharpness checks:',sum(checks.values()),'/',len(checks),'levels:',len(rows),'whetstone calls:',restoration_cases,flush=True)
    assert report['all_passed'],checks


if __name__=='__main__':main()
