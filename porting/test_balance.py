"""Run actual compiled live-hit balancing over every hit and both native slots."""
import json,struct
from build_module import HERE,OUT,MS,UPMOD,run,symbols
from build_balance import generate
from build_hitstats import generate as generate_ko
from test_hitstats import HitStatsEmulator
from test_runtime import PLAYER


def main():
    data=generate();generate_ko()
    dest=OUT/'regression';dest.mkdir(exist_ok=True)
    obj,elf=dest/'balance_hit.o',dest/'balance_hit.elf'
    run('clang','--target=armv7a-none-eabihf','-mcpu=cortex-a57','-marm','-mfloat-abi=hard',
        '-ffreestanding','-fno-builtin','-nostdlib','-O2','-DMS_RECOMP','-DMS_BALANCE',
        '-ffunction-sections','-fdata-sections','-fno-unwind-tables','-fno-asynchronous-unwind-tables',
        '-I',MS/'module','-I',UPMOD,'-I',OUT,'-c',HERE/'tests/balance_hit_harness.c','-o',obj)
    run('ld.lld','-m','armelf_linux_eabi','-static','--gc-sections','--image-base=0x10000',
        '-e','ms_apply_hit_stats','-o',elf,obj)
    b=elf.read_bytes();e=HitStatsEmulator((b,symbols(b)));checks={}
    expected={0:0};base=data['source_hit_count']
    for r in data['hits']:expected[r['hit']]=r['balanced_mv'];expected[r['hit']+base]=r['magnetised_mv']
    original=bytes([0xa5])*0x170;power=adjacent=ko=True;atk=PLAYER+0x3020
    ko_values=[0]*data['hit_count']
    for r in data['hits']:ko_values[r['hit']]=ko_values[r['hit']+base]=r['balanced_ko']
    for slot in (0,1):
        at=slot*0xb8
        for hit,mv in expected.items():
            e.uc.mem_write(atk,original);e.call('ms_apply_hit_stats',PLAYER,slot,hit)
            actual=bytes(e.uc.mem_read(atk,len(original)))
            power &= struct.unpack_from('<H',actual,at+0x38)[0]==min(mv,250)
            power &= struct.unpack_from('<H',actual,at+0x9c)[0]==mv
            allowed={at+i for i in (0x38,0x39,0x56,0x9c,0x9d)}
            adjacent &= all(actual[i]==v for i,v in enumerate(original) if i not in allowed)
            ko &= actual[at+0x56]==ko_values[hit]
    checks['all_281_hits_and_both_slots_use_policy_motion_values']=bool(power)
    checks['only_power_full_mv_and_existing_KO_fields_are_written']=bool(adjacent)
    checks['all_live_KO_values_follow_explicit_policy']=bool(ko)
    e.uc.mem_write(atk,original)
    for slot,hit,owner in ((2,1,PLAYER),(0,281,PLAYER),(0,0xffffffff,PLAYER),(0,1,0)):
        e.call('ms_apply_hit_stats',owner,slot,hit)
    checks['invalid_inputs_are_noops']=bytes(e.uc.mem_read(atk,len(original)))==original
    pins=[r for r in data['hits'] if r['group']=='pin_finisher']
    checks['both_pin_finishers_have_equal_reduced_damage_budgets']=len(pins)==4 and sum(r['balanced_mv'] for r in pins if r['action']==105)==sum(r['balanced_mv'] for r in pins if r['action']==157)<1200
    charge={a:sum(r['balanced_mv'] for r in data['hits'] if r['action']==a) for a in (35,36)}
    checks['correct_charge_is_stronger_than_early_or_overcharge']=charge[35]>charge[36]>0
    checks['Magnetise_keeps_ten_percent_bonus_without_double_scaling']=all(r['magnetised_mv']==r['balanced_mv']*110//100 for r in data['hits'])
    checks['all_positive_source_attacks_remain_positive']=all(r['balanced_mv']>=1 for r in data['hits'])
    # Damage aliases across alternative lead-ins stay consistent.
    aliases={}
    for r in data['hits']:
        override=data['policy'].get('action_motion_percent',{}).get(str(r['action']))
        aliases.setdefault((r['source_key'],override),set()).add((r['balanced_mv'],r['balanced_ko']))
    checks['source_aliases_consistent_except_explicit_action_policy']=all(len(v)==1 for v in aliases.values())
    overrides=data['policy'].get('action_motion_percent',{})
    checks['explicit_action_overrides_apply_without_changing_KO_or_other_aliases']=all(
        r['applied_motion_percent']==overrides[str(r['action'])] and
        r['balanced_ko']==data['policy'].get('source_ko_overrides',{}).get(r['source_key'],r['source_ko'])
        for r in data['hits'] if str(r['action']) in overrides)
    charged=next(r for r in data['hits'] if r['action']==35)
    skill_ok=True
    for skill in (0xac,0x109,0x132,0x28):
        e.skill=skill;e.call('ms_apply_hit_stats',PLAYER,0,charged['hit'])
        skill_ok &= e.uc.mem_read(atk+0x56,1)[0]==min(255,int(charged['balanced_ko']*1.1))
    e.blocked=True;e.call('ms_apply_hit_stats',PLAYER,0,charged['hit'])
    skill_ok &= e.uc.mem_read(atk+0x56,1)[0]==charged['balanced_ko']
    checks['native_KO_skills_apply_once_to_balanced_value_and_keep_eligibility_gate']=bool(skill_ok)
    report={'checks':checks,'all_passed':all(checks.values()),'policy_sha256':data['policy_sha256'],
        'hit_slot_cases':2*len(expected),'scope':'Compiled ARM damage/KO field writes; lifetime, shapes and ownership preserved'}
    (HERE/'reports/balance-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print('Balance ARM checks:',sum(checks.values()),'/',len(checks));assert report['all_passed']


if __name__=='__main__':main()
