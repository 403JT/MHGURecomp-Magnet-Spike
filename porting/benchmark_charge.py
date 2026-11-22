"""Run the controlled benchmark with robust normal-input charge timing."""
import json
import balance_route_controls
from charge_balance_controls import ChargeController
from prepare_frontier import HERE,sha
import benchmark_balance


def main():
    balance_route_controls.Controller=ChargeController
    import sys
    if '--weapon' not in sys.argv:sys.argv+=['--weapon','ms-impact']
    if '--rotation' not in sys.argv:sys.argv+=['--rotation','charged']
    label=sys.argv[sys.argv.index('--label')+1]
    try:benchmark_balance.main()
    finally:
        p=HERE/'runs'/label/'balance-run.json'
        if p.exists():
            data=json.loads(p.read_text(encoding='utf-8'))
            data['charge_driver_sha256']=sha(HERE/'charge_balance_controls.py')
            p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
