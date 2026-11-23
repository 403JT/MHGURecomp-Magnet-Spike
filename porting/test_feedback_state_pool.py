"""Real ARM state ownership while a full four-hunter roster changes objects."""
import json
from test_feedback_recovery import compile_test,Recovery
from test_runtime import BASE,HEAP,PLAYER
from build_module import HERE


def exercise(binary):
    e=Recovery(binary)
    manager=HEAP+0x380000
    e.w32(BASE+0x1885b58,manager)
    roster=[PLAYER+i*0x10000 for i in range(4)]
    stamps={p:100+i for i,p in enumerate(roster)}
    for i,p in enumerate(roster):
        e.w32(manager+0x1c+4*i,p)
        e.call('test_feedback_stamp',p,stamps[p])
    checks={}
    for n in range(40):
        slot=3 if n<2 else n%4
        newcomer=HEAP+0x100000+n*0x4000
        stamp=1000+n
        # The factory may see the replacement before sPlayer swaps its roster
        # pointer. This pending object must not evict any registered hunter.
        e.call('test_feedback_stamp',newcomer,stamp)
        checks[f'{n}_construction_preserves_four_registered_hunters']=all(
            e.call('test_feedback_stamp_read',p)==stamps[p] for p in roster)
        roster[slot]=newcomer;stamps[newcomer]=stamp
        e.w32(manager+0x1c+4*slot,newcomer)
        # Reading/updating another hunter must not reset the newcomer's latches.
        for p in roster:
            e.call('test_feedback_stamp',p,stamps[p])
        checks[f'{n}_all_active_owners_keep_independent_latches']=all(
            e.call('test_feedback_stamp_read',p)==stamps[p] for p in roster)
    return checks


def main():
    baseline=exercise(compile_test(True));fixed=exercise(compile_test())
    report={'baseline':baseline,'fixed':fixed,'all_passed':all(fixed.values()),
        'baseline_defect_reproduced':not all(baseline.values()),'roster_replacements':40,
        'scope':'Actual compiled ms_of/ms_find with native four-slot manager layout; construction precedes roster registration'}
    (HERE/'reports/feedback-state-pool-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'baseline_failed':sum(not v for v in baseline.values()),
        'fixed_failed':sum(not v for v in fixed.values()),'all_passed':report['all_passed']}))
    assert report['baseline_defect_reproduced']
    assert report['all_passed']


if __name__=='__main__':main()
