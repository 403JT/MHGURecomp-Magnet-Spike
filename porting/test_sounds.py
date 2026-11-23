"""Execute real ARM sound routing with synthetic cues and bounded sound objects."""
import json
import struct
from unicorn import arm_const as A
from test_runtime import Emulator, BASE, HEAP, PLAYER, RET
from build_module import run, symbols, MS, UPMOD, HERE, OUT

MGR, RESOURCE = HEAP+0x50000, HEAP+0x60000
EXPORTS=['ms_sound_post','ms_sound_post_at','ms_local_hit_sound_c','ms_local_sound_file','ms_local_file_id_c',
         'test_sound_tick','test_sound_reset','test_sound_bind']
EXPORTS+=['test_code_state','test_sound_guard','test_sound_segment']

def compile_test(target='recomp'):
    if target not in ('recomp', 'ryujinx'):
        raise ValueError('Unknown sound runtime target')
    tag = 'sound' if target == 'recomp' else 'sound-ryujinx'
    obj, elf = OUT/('regression/' + tag + '.o'), OUT/('regression/' + tag + '.elf')
    run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-ffunction-sections','-fdata-sections',
        *(['-DMS_RECOMP'] if target == 'recomp' else []),
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-I',MS/'module','-I',UPMOD,
        '-I',HERE/'tests','-c',HERE/'tests/sound_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e',EXPORTS[0],*[x for name in EXPORTS for x in ('-u',name)],'-o',elf,obj)
    data=elf.read_bytes();return data,symbols(data)

class AudioEmulator(Emulator):
    def __init__(self,binary):
        super().__init__(binary)
        self.resource=RESOURCE;self.area_ok=True;self.refcounts=0;self.motion=5010;self.frame=0.;self.blend=False
        self.w32(BASE+0x1896f5c,MGR)
        self.aux_calls=[]
        self.uc.mem_write(PLAYER+0x1054,b'\x02')
        self.uc.mem_write(PLAYER+0x40,struct.pack('<3f',10,20,30))

    def engine(self,u,address,size,_):
        off=address-BASE;r0=0
        if off==0x4d5e14: r0=self.resource
        elif off==0x4df890:r0=int(self.area_ok)
        elif off==0x887648:self.refcounts+=1
        elif off==0x53a058:r0=self.motion
        elif off==0x180c84:self.aux_calls.append(tuple(u.reg_read(r) for r in (A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3)))
        elif off==0x280e4c:
            target=struct.unpack('<f',struct.pack('<I',u.reg_read(A.UC_ARM_REG_S0)))[0]
            r0=int(not self.blend and self.frame>=target)
        else:raise AssertionError(f'Unexpected engine call {off:x}')
        u.reg_write(A.UC_ARM_REG_R0,r0);u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR))

    def call_sound(self,name,*args):
        u=self.uc
        u.reg_write(A.UC_ARM_REG_SP,0x7100fff0);u.reg_write(A.UC_ARM_REG_LR,RET)
        for reg,value in zip((A.UC_ARM_REG_R0,A.UC_ARM_REG_R1,A.UC_ARM_REG_R2,A.UC_ARM_REG_R3),args):u.reg_write(reg,value)
        u.emu_start(self.symbols[name],RET,count=100000)
        assert u.reg_read(A.UC_ARM_REG_PC)==RET
        return u.reg_read(A.UC_ARM_REG_R0)

    def queue(self):return bytes(self.uc.mem_read(MGR+0xec,64*0x24))
    def clear(self):self.uc.mem_write(MGR+0xec,bytes(64*0x24))
    def requests(self):return [struct.unpack_from('<I',self.queue(),i*0x24+0x10)[0] for i in range(64) if self.queue()[i*0x24]]
    def tick(self,f):
        self.frame=f;self.uc.mem_write(PLAYER+0x4fc,struct.pack('<f',f));self.call_sound('test_sound_tick',PLAYER)

def main():
    e=AudioEmulator(compile_test());checks={}
    regs=HEAP+0x70000
    original=[11,0,33,1,55,66,77,88]
    e.uc.mem_write(regs,struct.pack('<8I',*original))
    checks['other_classes_keep_native_resolver']=e.call_sound('ms_local_sound_file',regs)==0 and bytes(e.uc.mem_read(regs,32))==struct.pack('<8I',*original)
    for kind,ident in ((0,0x10a01),(1,0x10a00),(2,0)):
        original[1]=5;original[3]=kind;e.uc.mem_write(regs,struct.pack('<8I',*original))
        checks[f'class5_resolver_{kind}']=e.call_sound('ms_local_sound_file',regs)==1 and struct.unpack('<I',e.uc.mem_read(regs,4))[0]==ident
    original[1]=123;e.uc.mem_write(regs,struct.pack('<8I',*original))
    checks['unrelated_file_ids_keep_native_lookup']=e.call_sound('ms_local_file_id_c',regs)==0
    checks['enqueue_and_refcount']=e.call_sound('ms_sound_post',PLAYER,4,519)==1 and e.requests()==[519] and e.refcounts==1
    checks['position_and_owner']=struct.unpack('<3f',e.queue()[4:16])==(10.,20.,30.) and struct.unpack_from('<I',e.queue(),0x14)[0]==PLAYER
    e.clear();e.resource=0
    checks['missing_bank_is_noop']=e.call_sound('ms_sound_post',PLAYER,4,519)==0 and not e.requests()
    e.resource=RESOURCE;e.area_ok=False
    checks['inactive_area_is_noop']=e.call_sound('ms_sound_post',PLAYER,4,519)==0 and not e.requests()
    e.area_ok=True
    for i in range(64):assert e.call_sound('ms_sound_post',PLAYER,2,513)==1
    old=e.queue();refs=e.refcounts
    checks['full_queue_does_not_overwrite']=e.call_sound('ms_sound_post',PLAYER,4,519)==0 and e.queue()==old and e.refcounts==refs
    e.clear();e.tick(0);e.tick(0);e.tick(4)
    checks['frozen_frame_posts_once']=e.requests()==[513]
    e.tick(12);requests=e.requests()
    checks['skipped_frames_keep_cues']=requests[-1]==523 and len(requests) in (2,3)
    e.tick(12);checks['completed_cues_do_not_repeat']=e.requests()==requests
    for f in (11.,12.,11.,12.):e.tick(f)
    checks['hitstop_one_frame_rewind_does_not_replay']=e.requests()==requests
    e.clear();e.tick(0);checks['loop_rewind_rearms']=e.requests()==[513]
    e.clear();e.motion=5020;e.tick(2);e.tick(4)
    checks['motion_change_rearms']=e.requests()==[514]
    e.clear();e.motion=5010;e.blend=True;e.tick(0)
    checks['blending_defers_cues']=not e.requests()
    e.blend=False;e.tick(0);checks['cue_plays_after_blend']=e.requests()==[513]
    e.clear();e.motion=10;e.tick(100);checks['other_banks_are_silent']=not e.requests()
    e.call_sound('test_sound_reset');e.call_sound('test_sound_segment',8)
    e.clear();e.motion=5010;e.tick(12)
    checks['seek_does_not_replay_cues_before_segment']=e.requests()==[523]
    e.clear();e.tick(16);e.tick(8);e.tick(12)
    checks['loop_keeps_segment_sound_boundary']=e.requests()==[523]
    e.call_sound('test_sound_reset')
    counts={521:0,522:0,65535:0}
    e.motion=5010
    for i in range(1000):
        e.clear();e.tick(0);e.tick(5);req=e.requests();counts[req[-1] if len(req)>1 else 65535]+=1
    checks['weighted_choices_include_silence']=all(150<counts[k]<350 for k in (521,65535)) and 400<counts[522]<600
    # Real collision callback: normal tiers in both modes, precise contact point,
    # one native auxiliary branch, and no native physical branch on handled hits.
    info,hit,point=HEAP+0x80000,HEAP+0x90000,HEAP+0xa0000
    e.w32(PLAYER+0x13c4,info);e.uc.mem_write(info+0x4d4,b'\x05')
    e.w32(hit+0x70,PLAYER);e.uc.mem_write(point,struct.pack('<3f',101,202,303))
    original=[HEAP+0xb0000,HEAP+0xc0000,hit,point,0,0,0,123]
    def hit_call(mode,tier,kind=0,mag=0):
        e.clear();e.aux_calls.clear();e.call_sound('test_sound_bind',PLAYER,mode,mag)
        e.uc.mem_write(hit+6,bytes([tier]));e.uc.mem_write(hit+0x55,bytes([kind]))
        e.uc.mem_write(regs,struct.pack('<8I',*original))
        return e.call_sound('ms_local_hit_sound_c',regs)
    for mode,base in ((0,544),(1,541)):
        for tier in (2,3,4):
            handled=hit_call(mode,tier,2 if mode else 0)
            checks[f'hit_mode_{mode}_tier_{tier}']=handled==1 and e.requests()==[base+tier-2] and e.aux_calls==[tuple(original[:4])]
    checks['collision_contact_position']=struct.unpack('<3f',e.queue()[4:16])==(101.,202.,303.)
    checks['collision_registers_unchanged']=bytes(e.uc.mem_read(regs,32))==struct.pack('<8I',*original)
    checks['magnetised_hit_adds_layer']=hit_call(1,3,2,1)==1 and e.requests()==[542,547]
    for kind,tier in ((0,0),(0,1),(0,5),(3,3),(14,3)):
        checks[f'unmapped_collision_{kind}_{tier}_native']=hit_call(0,tier,kind)==0 and not e.requests() and not e.aux_calls
    e.resource=0
    checks['missing_hit_bank_keeps_native']=hit_call(0,2)==0 and not e.aux_calls
    e.resource=RESOURCE;e.uc.mem_write(info+0x4d4,b'\0')
    checks['other_weapon_hits_keep_native']=hit_call(0,2)==0 and not e.requests() and not e.aux_calls
    e.call_sound('test_sound_reset');e.clear();e.motion=5030
    ids,js=HEAP+0xd0000,HEAP+0xd1000
    e.w32(PLAYER+0x498,ids);e.w32(PLAYER+0x494,js)
    e.uc.mem_write(ids,b'\xff'*256);e.uc.mem_write(ids+8,b'\0');e.uc.mem_write(ids+12,b'\1')
    matrix=[1.,0.,0.,0.,0.,1.,0.,0.,0.,0.,1.,0.,1000.,2000.,3000.,1.]
    e.uc.mem_write(js+0x10,struct.pack('<16f',*matrix));e.uc.mem_write(js+0xb0,struct.pack('<16f',*matrix))
    e.call_sound('test_code_state',7,0,0);e.tick(3)
    checks['code_cue_respects_magnet_gate']=not e.requests()
    e.call_sound('test_code_state',7,0,1);e.tick(3)
    checks['effect13_once_per_update']=e.requests()==[525]
    checks['hand_effect_sound_transform']=struct.unpack('<3f',e.queue()[4:16])==(1010.,2000.,3020.)
    e.tick(3);checks['effect13_frozen_frame_does_not_repeat']=e.requests()==[525]
    e.tick(6);checks['effect13_next_source_frame_plays']=e.requests()==[525,525]
    e.clear();e.call_sound('test_code_state',7,0,0);e.tick(8)
    checks['code_cue_respects_action_gate']=not e.requests()
    e.call_sound('test_code_state',8,0,0);e.tick(8)
    checks['code_cue_plays_matching_action']=e.requests()==[538]
    e.clear();e.motion=5040;e.tick(2)
    checks['pin_beat_cue_plays']=e.requests()==[539]
    e.call_sound('test_sound_reset');e.clear();e.motion=10
    e.call_sound('test_sound_guard',PLAYER,14,1)
    checks['first_guard_hit_sound']=e.requests()==[524,525]
    for _ in range(3):e.tick(0)
    checks['guard_second_effect_waits']=e.requests()==[524,525]
    e.tick(0);checks['guard_second_effect_plays_at_frame4']=e.requests()==[524,525,525]
    for _ in range(4):e.tick(0)
    checks['guard_delayed_sound_is_single_shot']=e.requests()==[524,525,525]
    e.clear();e.call_sound('test_sound_guard',PLAYER,14,2)
    checks['later_guard_hits_do_not_restart_first_hit_task']=not e.requests()
    e.call_sound('test_sound_guard',PLAYER,112,1)
    checks['impact_guard_uses_own_native_sequence']=not e.requests()
    report={'checks':checks,'weighted_outcomes':counts,'all_passed':all(checks.values())}
    (HERE/'reports/sound-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));return int(not report['all_passed'])

if __name__=='__main__':raise SystemExit(main())
