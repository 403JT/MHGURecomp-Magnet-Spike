"""Compiled world-hit ownership/cache paths plus GU's original shape-cache writer."""
import json,struct,math
from test_runtime import Emulator,BASE,HEAP,PLAYER
from build_module import HERE,OUT,MS,UPMOD,run,symbols

REGS,SHAPE,RECORDS,CACHE=HEAP+0x250000,HEAP+0x251000,HEAP+0x260000,HEAP+0x270000
EXPORTS=['fixture_owner','fixture_arm','fixture_change_hit','ms_world_hits_reset','ms_local_world_shape_c']

def compile_test():
    folder=OUT/'worldhit-regression';folder.mkdir(exist_ok=True)
    flags=['--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-DMS_RECOMP','-I',MS/'module','-I',UPMOD]
    objs=[]
    for src in (HERE/'tests/worldhits_harness.c',HERE/'module/worldhits.c'):
        obj=folder/(src.stem+'.o');run('clang',*flags,'-c',src,'-o',obj);objs.append(obj)
    elf=folder/'worldhits.elf'
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',EXPORTS[0],*[v for n in EXPORTS for v in ('-u',n)],'-o',elf,*objs)
    b=elf.read_bytes();return b,symbols(b)

class WorldEmulator(Emulator):
    def __init__(self,b):
        super().__init__(b);self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
        self.symbols['native_cache']=BASE+0x1706a8
        self.call('fixture_owner',0,PLAYER)
        for slot in range(2):
            atk=PLAYER+0x3020+slot*0xb8
            for off in (0xc,0x70):self.w32(atk+off,PLAYER)
            self.w32(atk+0x84,RECORDS)
    def engine(self,u,address,size,_):
        if BASE+0x1706a8<=address<=BASE+0x170734:return
        return super().engine(u,address,size,_)
    def shape(self,values,slot=0,record=0,kind=2,attack=None,index=0):
        self.uc.mem_write(SHAPE,struct.pack('<9f',*values))
        regs=[kind,11,22,33,PLAYER+0x3020+slot*0xb8 if attack is None else attack,55,66,77]
        self.uc.mem_write(REGS,struct.pack('<8I',*regs));before=bytes(self.uc.mem_read(REGS,32))
        self.call('ms_local_world_shape_c',REGS,RECORDS+record,SHAPE,index)
        assert bytes(self.uc.mem_read(REGS,32))==before,'Callback changed interrupted registers'
        return struct.unpack('<9f',self.uc.mem_read(SHAPE,36))

def main():
    binary=compile_test();e=WorldEmulator(binary);checks={}
    initial=(10,20,30,111,40,50,60,222,7)
    moved=(310,420,530,333,640,750,860,444,9)
    meaningful=(0,1,2,4,5,6,8)
    e.call('fixture_arm',PLAYER,0,133,1)
    checks['first_world_shape_is_unchanged']=e.shape(initial)==initial
    actual=e.shape(moved)
    checks['endpoints_and_radius_stay_at_spawn']=all(actual[i]==initial[i] for i in meaningful)
    checks['padding_is_not_overwritten']=actual[3]==moved[3] and actual[7]==moved[7]
    fixed=True
    for k in range(60):
        values=tuple(float(v+k*100) if i in meaningful else float(v) for i,v in enumerate(moved))
        e.shape(values);e.w32(CACHE+0x2830,0);e.call('native_cache',CACHE,2,SHAPE)
        got=struct.unpack('<7f',e.uc.mem_read(CACHE+0x2034,28))
        fixed &= got==(7,10,20,30,40,50,60)
    checks['60_original_native_cache_writes_stay_fixed']=fixed
    e.call('fixture_arm',PLAYER,1,134,1);e.shape(moved,slot=1)
    checks['two_attack_slots_are_independent']=e.shape(initial,slot=1)[0]==moved[0] and e.shape(moved)[0]==initial[0]
    e.call('fixture_arm',PLAYER,0,133,1)
    checks['rearming_same_hit_resets_the_anchor']=e.shape(moved)==moved
    e.call('fixture_arm',PLAYER,0,1,0)
    checks['ordinary_attack_keeps_current_geometry']=e.shape(initial)==initial
    e.shape(moved);e.w32(CACHE+0x2830,0);e.call('native_cache',CACHE,2,SHAPE)
    checks['baseline_native_cache_follows_unanchored_geometry']=struct.unpack('<f',e.uc.mem_read(CACHE+0x2038,4))[0]==moved[0]
    checks['unregistered_attack_is_untouched']=e.shape(initial,attack=1)==initial
    e.call('fixture_arm',PLAYER,0,133,1)
    e.shape(initial,record=44,index=1)
    checks['shape_records_have_independent_anchors']=e.shape(moved,record=44,index=1)[0]==initial[0] and e.shape(moved)[0]==moved[0]
    checks['invalid_index_or_record_is_untouched']=all(e.shape(initial,index=v)==initial for v in (4,99)) and e.shape(initial,record=1)==initial
    checks['invalid_native_shape_type_is_untouched']=e.shape(initial,kind=0)==initial
    e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial)
    checks['type_mismatch_is_not_reinterpreted']=e.shape(moved,kind=1)==moved
    e.call('fixture_change_hit',PLAYER,0,9)
    checks['native_slot_reuse_invalidates_cache']=e.shape(moved)==moved
    e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial);e.w32(PLAYER+0x3020+0x84,RECORDS+0x1000)
    checks['descriptor_reuse_invalidates_cache']=e.shape(moved)==moved
    e.w32(PLAYER+0x3020+0x84,RECORDS)
    e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial);e.w32(PLAYER+0x3020+0x88,1)
    checks['shape_set_change_invalidates_cache']=e.shape(moved)==moved;e.w32(PLAYER+0x3020+0x88,0)
    e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial)
    checks['record_identity_change_invalidates_cache']=e.shape(moved,record=44)==moved
    for off,label in ((0xc,'transform_owner'),(0x70,'damage_owner')):
        e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial);e.w32(PLAYER+0x3020+off,PLAYER+0x8000)
        checks[label+'_change_invalidates_cache']=e.shape(moved)==moved
        e.w32(PLAYER+0x3020+off,PLAYER)
    e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial);e.call('ms_world_hits_reset',PLAYER)
    checks['hunter_reset_releases_anchors']=e.shape(moved)==moved
    e.call('fixture_arm',PLAYER,0,133,1);e.shape(initial);e.call('fixture_owner',0,0)
    checks['removed_hunter_is_ignored']=e.shape(moved)==moved
    e.call('fixture_owner',0,PLAYER);e.call('fixture_arm',PLAYER,0,133,1)
    nan=(float('nan'),*initial[1:]);e.shape(nan)
    checks['invalid_initial_geometry_is_not_cached']=e.shape(moved)==moved
    e.call('fixture_arm',PLAYER,0,133,1)
    sphere=(1,2,3,111,float('nan'),float('nan'),float('nan'),222,4)
    e.shape(sphere,kind=1);got=e.shape(moved,kind=1)
    checks['sphere_ignores_unused_second_endpoint']=all(got[i]==sphere[i] for i in (0,1,2,8)) and got[4:7]==moved[4:7]
    e.call('fixture_arm',PLAYER,5,133,1)
    checks['invalid_slot_is_safe']=True
    report={'checks':checks,'all_passed':all(checks.values()),
        'scope':'Compiled world-hit callback and lifetime ownership; original GU 1706a8 weapon cache writer; synthetic objects'}
    (HERE/'reports/worldhit-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
