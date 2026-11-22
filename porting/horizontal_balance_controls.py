"""Sustain Impact horizontals through normal transform and follow-up inputs."""
import re


class HorizontalController:
    def __init__(self,weapon,rotation,log_start):
        assert weapon=='ms-impact' and rotation=='horizontal'
        self.cursor=log_start;self.started=False;self.last_frame=-1;self.followups=0
        self.last_action=None;self.chord_retry=False;self.retries=0;self.recoveries=0
        self.entered_horizontal=False;self.recovering=False

    def tick(self,send,text,elapsed):
        if not self.started and elapsed>=3:
            send('A 24');self.started=True
        rows=re.findall(r'\[moves\] (\d+) pl [0-9a-f]+ is ([0-9a-f]{4}):(\d+)',text[self.cursor:])
        if not rows:return
        frame=int(rows[-1][0]);category=int(rows[-1][1],16);action=int(rows[-1][2])
        if frame==self.last_frame:
            states=re.findall(r'\[balance\] state frame (\d+)',text[self.cursor:])
            if category==16 and action==25 and not self.chord_retry and states and int(states[-1])-frame>=70:
                send('A 12\nX 10 2');self.chord_retry=True;self.retries+=1
            return
        self.last_frame=frame
        if category==1 and action==0 and self.entered_horizontal and not self.recovering and self.last_action is not None:
            # A missed normal chord must not leave the test idling forever.
            # Recover using normal mode switch and the same horizontal entry.
            send('MINUS 12\nA 24 80' if self.last_action not in (6,8) else 'A 24 15')
            self.last_action=None;self.recoveries+=1;self.recovering=True
            return
        if category!=16:return
        if self.recovering and action not in (6,8):return
        if action in (6,8):self.recovering=False
        if action in (6,8,120,24,25,28):self.entered_horizontal=True
        self.last_action=action;self.chord_retry=False
        if action in (6,8):send('MINUS 24 42')
        elif action in (120,24):send('A 24 40');self.followups+=1
        # Separate the two physical button edges by two presentation frames;
        # GU occasionally discards a perfectly simultaneous simulated chord.
        elif action==25:send('A 12 40\nX 10 42');self.followups+=1
        # The buffer starts at motion40. A presentation-frame35 press can
        # arrive at motion34 after hitstop and be discarded; enter later.
        elif action==28:send('A 24 55');self.followups+=1

    def summary(self):
        return {'rotation':'horizontal','horizontal_followups':self.followups,
            'chord_retries':self.retries,'normal_input_recoveries':self.recoveries,
            'input_method':'Normal Cutting horizontal -> transform -> Impact H2/Overhead/H1 follow-ups'}
