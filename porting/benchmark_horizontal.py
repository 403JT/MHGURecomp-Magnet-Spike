"""Run sustained normal-input Impact horizontals in the native kill fixture."""
import json,sys
import balance_route_controls
from horizontal_balance_controls import HorizontalController
from prepare_frontier import HERE,sha
import benchmark_balance


def main():
    balance_route_controls.Controller=HorizontalController
    balance_route_controls.alternate=lambda weapon,rotation,original:(600,[],[])
    if '--weapon' not in sys.argv:sys.argv+=['--weapon','ms-impact']
    if '--rotation' not in sys.argv:sys.argv+=['--rotation','horizontal']
    label=sys.argv[sys.argv.index('--label')+1]
    try:benchmark_balance.main()
    finally:
        p=HERE/'runs'/label/'balance-run.json'
        if p.exists():
            data=json.loads(p.read_text(encoding='utf-8'))
            data['horizontal_driver_sha256']=sha(HERE/'horizontal_balance_controls.py')
            p.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
