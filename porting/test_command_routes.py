"""Check common movement/roll routes against original GU command resources."""
import importlib.util,json
from build_cancel_windows import generate
from build_module import HERE,MS

def main():
    generate()
    import msbuild,xfs
    gs=msbuild.gu_arc('player/quest/w00_m0.arc');commands=msbuild.Commands(gs)
    before=HERE/'backups/parity2-before-cancel-windows/msbuild.py'
    spec=importlib.util.spec_from_file_location('old_command_routes',before)
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    checks={}
    def route(builder,inp,nxt):
        return builder.cancel_commands(commands,None,dict(input=inp,next=nxt,cond=0),0)
    def record(path):return xfs.parse(commands.files[path])
    legacy_walk=route(old,1,40)[0];legacy_roll=route(old,0,202)
    roll=route(msbuild,0,202);walk=route(msbuild,1,40)
    checks['legacy_stick_cancel_points_to_a_roll_action']=record(legacy_walk)['act_st']==1 and record(legacy_walk)['act_no']==6
    checks['stick_cancel_uses_original_drawn_movement_request']=len(walk)==1 and record(walk[0])['act_st']==2 and record(walk[0])['act_no']==0
    checks['roll_cancel_uses_original_neutral_roll_request']=len(roll)==1 and record(roll[0])['act_st']==1 and record(roll[0])['act_no']==6
    checks['both_source_shared_roll_selectors_keep_the_roll_route']=route(msbuild,0,203)==roll
    checks['roll_route_no_longer_uses_stock_side_evade_requests']=not set(roll)&set(legacy_roll)
    checks['common_requests_remain_byte_identical_to_original_GU']=all(commands.files[p]==gs[p][1] for p in roll+walk)
    report={'checks':checks,'all_passed':all(checks.values()),
            'scope':'Original GU request headers and bytes; old converter route reproduced; live movement/roll behavior checked separately'}
    (HERE/'reports/command-route-regression.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2));assert report['all_passed']
if __name__=='__main__':main()
