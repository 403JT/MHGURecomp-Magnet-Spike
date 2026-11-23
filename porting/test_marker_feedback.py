"""Real ARM marker/task lifecycle: remote updates and no local double tick."""
import json
import struct
from unicorn import arm_const as A
from test_damage_feedback import Damage
from test_runtime import BASE,HEAP,PLAYER
from build_module import HERE,MS,UPMOD,OUT,run,symbols


def compile_test(baseline=False):
    folder=OUT/'regression';folder.mkdir(exist_ok=True)
    tag='marker-feedback-old' if baseline else 'marker-feedback'
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-DMS_GS_TREE',
        '-I',MS/'module','-I',MS/'gen','-I',UPMOD,'-I',OUT]
    if baseline:flags+=['-DMS_TEST_SOURCE="'+(HERE/'backups/before-feedback-2/module/ms_act.c').as_posix()+'"']
    objects=[]
    for i,p in enumerate([HERE/'tests/marker_feedback_harness.c',MS/'module/ms_class.c']):
        obj=folder/(tag+f'-{i}.o');run('clang',*flags,'-c',p,'-o',obj);objects.append(obj)
    exports=['test_marker_begin','test_marker_id','test_marker_life','test_marker_layout',
             'test_damage_after_update','test_damage_tick']
    elf=folder/(tag+'.elf')
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',exports[0],*[v for n in exports for v in ('-u',n)],'-o',elf,*objects)
    b=elf.read_bytes();return b,symbols(b)


class Marker(Damage):
    def __init__(self,b):
        super().__init__(b);self.moves=[]
    def engine(self,u,address,size,arg):
        if address==BASE+0x32a45c:
            self.moves.append(struct.unpack('<3f',u.mem_read(u.reg_read(A.UC_ARM_REG_R1),12)))
        return super().engine(u,address,size,arg)


def exercise(binary):
    checks={}
    for local in (0,1):
        for dt in (.5,1,2):
            e=Marker(binary);m,r,ids,js,h=[HEAP+v for v in (0x40000,0x60000,0x80000,0xa0000,0x1000)]
            e.monster=m;e.w32(BASE+0x1851fe0,HEAP+0x30000)
            e.w32(m+0x1428,r);e.w32(r+0x370,1000)
            e.uc.mem_write(m+0x1054,b'\1');e.uc.mem_write(PLAYER+0x1054,b'\1')
            e.w32(m+0x498,ids);e.w32(m+0x494,js);e.uc.mem_write(ids+3,b'\0')
            e.uc.mem_write(js+0x10,struct.pack('<16f',1,0,0,0,0,1,0,0,0,0,1,0,100,200,300,1))
            e.proxy(h,e.call('test_marker_id'));e.call('test_marker_begin',PLAYER,m,h)
            e.uc.mem_write(PLAYER+0x13cc,bytes([local]));e.w32(PLAYER+0x1c,struct.unpack('<I',struct.pack('<f',dt))[0])
            # Keep motion under repost threshold and stay within its current proxy.
            for i in range(10):
                e.uc.mem_write(js+0x40,struct.pack('<3f',100+i,200+i,300+i))
                if local:e.call('test_damage_tick',PLAYER,int(dt*50))
                before=len(e.moves);life=e.call('test_marker_life',PLAYER)
                e.call('test_damage_after_update',PLAYER)
                prefix=f'{local}_{dt}_{i}'
                checks[prefix+'_updates_once']=len(e.moves)==before+(0 if local else 1)
                expected_life=life-(0 if local else int(dt*50))
                checks[prefix+'_timer_once']=e.call('test_marker_life',PLAYER)==expected_life
                checks[prefix+'_follows_bone']=bool(e.moves) and e.moves[-1]==(104+i,205+i,306+i)
            # A remote marker must also disappear at normal lifecycle ends.
            if not local:
                e.w32(r+0x370,0);e.call('test_damage_after_update',PLAYER)
                checks[f'{dt}_remote_death_stops_effect']=e.calls['stop']==1
                e.call('test_damage_after_update',PLAYER)
                checks[f'{dt}_remote_death_stop_is_not_repeated']=e.calls['stop']==1
    for end in ('other_area','removed','expired','reused_proxy'):
        e=Marker(binary);m,r,h=HEAP+0x40000,HEAP+0x60000,HEAP+0x1000
        e.monster=m;e.w32(m+0x1428,r);e.w32(r+0x370,1000)
        e.uc.mem_write(m+0x1054,b'\1');e.uc.mem_write(PLAYER+0x1054,b'\1')
        e.proxy(h,e.call('test_marker_id'));e.call('test_marker_begin',PLAYER,m,h)
        e.uc.mem_write(PLAYER+0x13cc,b'\0')
        if end=='other_area':e.uc.mem_write(m+0x1054,b'\2')
        if end=='removed':e.monster=0
        if end=='reused_proxy':
            e.proxy(h,e.call('test_marker_id')+1);e.w32(r+0x370,0)
        for _ in range(201 if end=='expired' else 1):e.call('test_damage_after_update',PLAYER)
        checks['remote_'+end+'_effect_cleanup']=e.calls['stop']==(0 if end=='reused_proxy' else 1)
    return checks


def main():
    old=exercise(compile_test(True));fixed=exercise(compile_test())
    report={'baseline':old,'fixed':fixed,'all_passed':all(fixed.values()),
        'baseline_defect_reproduced':not all(old.values()),
        'scope':'Real ARM marker/tick/after-update; native effect posts/moves provided by bounded fixtures'}
    (HERE/'reports/marker-feedback-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    failed=[k for k,v in fixed.items() if not v]
    print(json.dumps({'checks':len(fixed),'baseline_failures':sum(not v for v in old.values()),'failed':failed,'all_passed':report['all_passed']}))
    assert report['all_passed'] and report['baseline_defect_reproduced'],failed


if __name__=='__main__':main()
