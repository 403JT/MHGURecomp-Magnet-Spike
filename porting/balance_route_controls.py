"""Normal-input alternate rotations and a pin/QTE controller for damage benchmarks."""


def alternate(weapon,rotation,original):
    if rotation in ('base','magnetise'):return original
    setup=[(60,4,'MINUS')] if weapon=='ms-impact' else []
    if rotation=='pin':return 600,[],setup
    if rotation=='horizontal':
        if weapon=='ms-cut':return 260,[(0,4,'A'),(60,4,'A'),(120,4,'A'),(185,4,'X+A')],setup
        # Enter through the Cutting horizontal transform, then loop Impact
        # H2 -> Overhead -> H1. Native sheathed chords need separate coverage.
        return 180,[(0,8,'A'),(60,8,'X+A'),(120,8,'A')],[(150,8,'A'),(200,8,'MINUS')]
    if rotation=='basic':return 115,[(0,4,'X')],setup
    if rotation=='charged':
        if weapon!='ms-impact':raise ValueError('Charged rotation requires Impact')
        return 600,[],setup
    if rotation=='shock':
        if weapon!='ms-impact':raise ValueError('Shock rotation requires Impact')
        return 240,[(0,30,'R'),(6,4,'A'),(45,4,'X')],setup
    raise ValueError('Unknown rotation')


class Controller:
    def __init__(self,weapon,rotation,log_start):
        self.weapon=weapon;self.rotation=rotation;self.cursor=log_start
        self.stage=0;self.next_at=3.0;self.cycles=0;self.qtes=0;self.magnetise_sent=False
        self.full_charge_releases=0;self.overcharges=0
        self.missed_charge_entries=0

    def tick(self,send,text,elapsed):
        chunk=text[self.cursor:]
        if self.rotation=='charged':
            if self.stage==0 and elapsed>=self.next_at:
                self.cursor=len(text);send('A 8');self.stage=1
            elif self.stage==1 and '16/32 step 1 ' in chunk:
                send('A 8 25');self.stage=2
            elif self.stage==2 and '16/33 step 1 ' in chunk:
                # Buffer before the native go window. Motion time can advance
                # faster than presentation frames and hitstop varies by part.
                send('A 6000 35');self.stage=3
            elif self.stage==3 and 'Triple Strike charged' in chunk:
                send('release A');self.full_charge_releases+=1;self.stage=4
            elif self.stage==3 and 'action 33 done' in chunk:
                send('release A');self.missed_charge_entries+=1
                self.next_at=elapsed+.5;self.stage=0
            elif self.stage==4 and ('action 35 done' in chunk or 'action 36 done' in chunk):
                if 'Triple Strike overcharged' in chunk:self.overcharges+=1
                self.next_at=elapsed+.5;self.stage=0
            return
        if self.rotation=='magnetise':
            mode='Impact' if self.weapon=='ms-impact' else 'Cutting'
            if not self.magnetise_sent and f'msport: {mode} Magnetise ready' in chunk:
                send('R 18\nMINUS 4 6');self.magnetise_sent=True
            return
        if self.rotation!='pin':return
        impact=self.weapon=='ms-impact'
        if self.stage==0 and elapsed>=self.next_at:
            self.cursor=len(text);send('R 220\nX 8 6');self.stage=1
        elif self.stage==1:
            expected='16/39 step 2 ' if impact else '16/11 step 1 '
            if expected in chunk:
                delay=30 if impact else 55
                send(f'X 8 {delay}\nA 8 {delay}');self.stage=2
        elif self.stage==2 and 'msport: state action 16/99 ' in chunk:
            send('\n'.join(('X' if n%2==0 else 'A')+' 2 '+str(n*6) for n in range(24)))
            self.qtes+=1;self.stage=3
        elif self.stage==3 and 'ms-pin: released monster' in chunk:
            self.cycles+=1;self.next_at=elapsed+1.5;self.stage=0

    def summary(self):
        return {'rotation':self.rotation,'pin_cycles_released':self.cycles,
            'qte_input_batches':self.qtes,'magnetise_input_sent':self.magnetise_sent,
            'cue_timed_charge_releases':self.full_charge_releases,'overcharges':self.overcharges,
            'missed_charge_entries':self.missed_charge_entries}
