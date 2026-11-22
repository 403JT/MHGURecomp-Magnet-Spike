"""Reject changed attack paths while accepting strictly identical active paths."""
import json
from prepare_frontier import HERE
from audit_balance_preservation import files
from balance_evidence_equivalence import prove


def main():
    target=HERE/'output/magnet-spike-experimental';expected=files(target);checks={}
    for label,valid in [('balance8-cut-base',True),('balance8-cut-horizontal',True),
            ('balance11-impact-basic',True),('balance11-cut-pin',True),('balance11-impact-pin',True),
            ('balance11-impact-shock',True),('balance12-charge-cue',False),('balance12-horizontal-cue',False),
            ('balance3-ms-cut',False)]:
        folder=HERE/'runs'/label;run=json.loads((folder/'balance-run.json').read_text())
        checks[label]=bool(prove(run,folder,target,expected))==valid
    result={'all_passed':all(checks.values()),'checks':checks,'mod_files':expected,
        'scope':'Read-only positive and negative checks: changed active MVs or any differing code/assets cannot reuse old native timing evidence.'}
    (HERE/'reports/balance-equivalence-regression.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('Binary evidence equivalence:',sum(checks.values()),'/',len(checks));assert result['all_passed'],checks


if __name__=='__main__':main()
