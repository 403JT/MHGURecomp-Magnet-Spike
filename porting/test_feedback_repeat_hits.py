"""Real attack-event latch and native frame predicate across roster replacement."""
import json
import struct
from unicorn import arm_const as A
from test_feedback_recovery import compile_test,Recovery
from test_runtime import BASE,HEAP,PLAYER
from build_module import HERE


class Swing(Recovery):
    def __init__(self,b):
        super().__init__(b);self.arms=[]
        self.uc.mem_write(BASE,(HERE/'work/gu_main/mem.bin').read_bytes())
    def engine(self,u,address,size,arg):
        off=address-BASE
        if 0x280e4c<=off<=0x280f20:return
        if off==0x2b7240:
            self.arms.append({'player':u.reg_read(A.UC_ARM_REG_R0),
                'slot':u.reg_read(A.UC_ARM_REG_R1),'hit':u.reg_read(A.UC_ARM_REG_R2)})
            u.reg_write(A.UC_ARM_REG_PC,u.reg_read(A.UC_ARM_REG_LR));return
        return super().engine(u,address,size,arg)


def exercise(binary):
    e=Swing(binary);manager=HEAP+0x380000
    e.w32(BASE+0x1885b58,manager)
    roster=[PLAYER+i*0x10000 for i in range(4)]
    for i,p in enumerate(roster):
        e.w32(manager+0x1c+4*i,p);e.call('test_feedback_stamp',p,100+i)
    e.call('test_feedback_swing_begin',PLAYER)
    e.call('test_feedback_act',PLAYER)
    first=len(e.arms)
    newcomer=HEAP+0x100000
    e.call('test_feedback_stamp',newcomer,1000)
    e.w32(manager+0x28,newcomer)
    for _ in range(12):
        e.call('test_feedback_act',PLAYER)
        e.call('test_feedback_stamp',newcomer,1000)
    return {'first_update_arms':first,'arms_after_roster_change':len(e.arms),
            'animation_not_restarted':not e.neutrals}


def main():
    old=compile_test(True);new=compile_test()
    baseline=exercise(old);fixed=exercise(new)
    checks={'old_same_animation_rearms_hit':baseline['arms_after_roster_change']>baseline['first_update_arms']>0,
        'fixed_attack_arms_once':fixed['first_update_arms']==fixed['arms_after_roster_change']==1,
        'animation_not_restarted':baseline['animation_not_restarted'] and fixed['animation_not_restarted']}
    softlocks=[]
    for binary in (old,new):
        e=Swing(binary);manager=HEAP+0x380000
        e.w32(BASE+0x1885b58,manager)
        for i in range(4):
            p=PLAYER+i*0x10000;e.w32(manager+0x1c+4*i,p)
            e.call('test_feedback_stamp',p,100+i)
        e.call('test_feedback_begin',PLAYER,10,1,100)
        e.call('test_feedback_act',PLAYER)
        newcomer=HEAP+0x100000
        e.call('test_feedback_stamp',newcomer,1000);e.w32(manager+0x28,newcomer)
        e.uc.mem_write(PLAYER+0x14d0,struct.pack('<f',170))
        for _ in range(30):
            if not e.neutrals.get(PLAYER):e.call('test_feedback_act',PLAYER)
            e.call('test_feedback_stamp',newcomer,1000)
        softlocks.append(e.neutrals.get(PLAYER,0))
    checks['old_local_finisher_softlocks_when_state_is_evicted']=softlocks[0]==0
    checks['fixed_local_finisher_exits_after_roster_change']=softlocks[1]==1
    report={'baseline':baseline,'fixed':fixed,'checks':checks,'all_passed':all(checks.values()),
        'scope':'Actual ms_act/event/arm and ms_of code with native GU frame predicate; external arming call counted, not simulated damage'}
    (HERE/'reports/feedback-repeat-hit-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))
    assert report['all_passed'],checks


if __name__=='__main__':main()
