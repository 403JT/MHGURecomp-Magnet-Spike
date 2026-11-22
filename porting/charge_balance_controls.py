"""Cue-based Triple Strike test controls; uses only normal button events."""
class ChargeController:
    def __init__(self,weapon,rotation,log_start):
        assert weapon=='ms-impact' and rotation=='charged'
        self.cursor=log_start;self.stage=0;self.next_at=3.;self.entered_at=0.
        self.releases=0;self.missed=0;self.overcharges=0

    def reset(self,send,elapsed,missed=False):
        send('release A');self.stage=0;self.next_at=elapsed+.5
        if missed:self.missed+=1

    def tick(self,send,text,elapsed):
        chunk=text[self.cursor:]
        if self.stage==0 and elapsed>=self.next_at:
            self.cursor=len(text);send('A 24');self.stage=1;self.entered_at=elapsed
        elif self.stage==1 and '16/32 step 1 ' in chunk:
            # Keep the second press across the hitstop/input polling interval.
            send('A 24 30');self.stage=2
        elif self.stage==1 and elapsed-self.entered_at>6:
            self.reset(send,elapsed,True)
        elif self.stage==2 and '16/33 step 1 ' in chunk:
            send('A 6000 35');self.stage=3
        elif self.stage==2 and 'action 32 done' in chunk:
            self.reset(send,elapsed,True)
        elif self.stage==3 and 'Triple Strike charged' in chunk:
            send('release A');self.releases+=1;self.stage=4
        elif self.stage==3 and 'action 33 done' in chunk:
            self.reset(send,elapsed,True)
        elif self.stage==4 and ('action 35 done' in chunk or 'action 36 done' in chunk):
            if 'Triple Strike overcharged' in chunk:self.overcharges+=1
            self.reset(send,elapsed)

    def summary(self):
        return {'rotation':'charged','cue_timed_charge_releases':self.releases,
            'missed_charge_entries':self.missed,'overcharges':self.overcharges,
            'input_method':'Normal A presses/holds; release at logged charge cue, no action/state edits'}
