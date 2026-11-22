/* MHF 10a68110 latches each cancel's four predicates independently; 10a68090
 * checks step, kind, loop and frame. GU's three frame fields cannot represent
 * loop-qualified ends. Only generated scoped
 * tables use these hooks; all other calls retain the original GU implementation.
 * Native 281388 callers: 2ea984 input range, 2eb298 transition range.
 * R8 is command row index. Source buffer/go close times must be identical. */
#include "ms.h"
struct window_time { uint16_t step; uint8_t kind; int8_t cond; uint16_t frame,loop; };
struct window_rule { struct window_time time[4]; };
struct window_table { uint16_t action,table,first; uint8_t step,nrules,nrows; uint16_t row_first; uint8_t recovery; };
#include "cancel_windows.inc"
struct window_owner { uint8_t *p; uint16_t action,log_loop; int log_bucket,log_step; uint32_t passed[4],log_bits[4];
    float ready[4][32]; uint8_t recovery_logged; };
static struct window_owner owners[MS_PLAYERS];

void ms_cancel_windows_reset(uint8_t *p)
{
    for(unsigned i=0;i<MS_PLAYERS;i++)if(owners[i].p==p)owners[i].p=0;
}

static int time_passed(uint8_t *p,const struct ms_state *s,const struct window_time *t)
{
    unsigned step=FIELD(uint8_t,p,5);
    if(step>t->step+1u)return 1;
    if(step<t->step+1u)return 0;
    if(t->kind==1)return 1;
    if(t->kind==2)return 0;
    /* Positive time-condition fields are rejected by the source binder. */
    if(s->loops>t->loop)return 1;
    if(s->loops<t->loop)return 0;
    return MS_REACHED(p,(float)t->frame);
}

static int gate(uint8_t *p,unsigned row,unsigned phase,int *out)
{
    struct ms_state *s=ms_find(p);
    if(!s || FIELD(uint16_t,p,0x2506)!=0x10 || FIELD(uint16_t,p,0x250a)!=s->action)return 0;
    uint8_t *info=FIELD(uint8_t *,p,0x13c4);
    if(!info || info[0x4d4]!=MS_CLASS || FN(ms_p_t,0x27b918)(p))return 0;
    const struct window_table *t=0;
    for(unsigned i=0;i<sizeof window_tables/sizeof *window_tables;i++) {
        const struct window_table *q=&window_tables[i];
        if(q->action==s->action && q->step+1u==FIELD(uint8_t,p,5) && q->table==FIELD(uint32_t,p,0x24ac)) {t=q;break;}
    }
    if(!t || row>=t->nrows)return 0;
    struct window_owner *owner=0,*free_=0;
    for(unsigned i=0;i<MS_PLAYERS;i++) {
        if(owners[i].p==p)owner=&owners[i];
        if(!free_ && (!owners[i].p || !ms_find(owners[i].p)))free_=&owners[i];
    }
    if(!owner) {
        if(!free_)return 0;
        owner=free_;owner->p=p;owner->action=s->action;
        owner->log_bucket=owner->log_step=-1;owner->log_loop=0xffff;
        owner->recovery_logged=0;
        for(unsigned i=0;i<4;i++) {owner->passed[i]=0;owner->log_bits[i]=~0u;}
    }
    if(owner->action!=s->action)return 0; /* action_start must reset before reuse */
    for(unsigned i=0;i<t->nrules;i++)for(unsigned j=0;j<4;j++) {
        uint32_t bit=1u<<i;
        if(!(owner->passed[j]&bit) && time_passed(p,s,&window_rules[t->first+i].time[j])) {
            owner->passed[j]|=bit;
            /* Buffer immediately, then move its close and both transition
             * boundaries together. The game clock keeps advancing when the
             * animation reaches its last frame or is paused by hitstop. */
            owner->ready[j][i]=s->action_clock+(j?t->recovery:0);
            if(j==2 && t->recovery && !owner->recovery_logged) {
                owner->recovery_logged=1;
                static unsigned n;
                if(n++<160)logf("ms-recovery: command action %u row %u delay %u clock %d ready %d",
                    s->action,i,t->recovery,(int)s->action_clock,(int)owner->ready[j][i]);
            }
        }
    }
    int bucket=(int)MS_FRAME(p)/10;
    int changed=0;
    for(unsigned i=0;i<4;i++)changed|=owner->passed[i]!=owner->log_bits[i];
    if(bucket!=owner->log_bucket || owner->log_step!=t->step || owner->log_loop!=s->loops || changed) {
        static unsigned n;
        if(n++<160)logf("ms-window: action %u step %u loop %u frame %d",s->action,t->step,s->loops,(int)MS_FRAME(p));
        owner->log_bucket=bucket;owner->log_step=t->step;owner->log_loop=s->loops;
        for(unsigned i=0;i<4;i++)owner->log_bits[i]=owner->passed[i];
    }
    unsigned rule=window_rows[t->row_first+row],open=phase==2?2:0,close=open+1;
    uint32_t bit=1u<<rule;
    unsigned opened=!!(owner->passed[open]&bit) && s->action_clock>=owner->ready[open][rule];
    unsigned closed=!!(owner->passed[close]&bit) && s->action_clock>=owner->ready[close][rule];
    *out=opened && !closed;
    return 1;
}

int ms_local_cancel_range_c(uint32_t *regs,unsigned row)
{
    uint32_t caller=regs[LR]-g_main_base;
    if(caller!=0x2ea984 && caller!=0x2eb298)return 0;
    int value;
    if(!gate((uint8_t *)(uintptr_t)regs[R0],row,caller==0x2eb298?2:0,&value))return 0;
    uint8_t *p=(uint8_t *)(uintptr_t)regs[R0];
    if(caller==0x2ea984 && row==0 && (FIELD(uint16_t,p,0x13f8)&0x80)) {
        static unsigned n;
        if(n++<16)logf("ms-window: roll input frame %d loop %u",(int)MS_FRAME(p),ms_find(p)->loops);
    }
    regs[R0]=(uint32_t)value;
    return 1;
}

