#include "damage_feedback_harness.c"
#include <stddef.h>
unsigned test_marker_layout(unsigned k)
{
    switch(k) {
    case 0:return sizeof(struct ms_state);
    case 1:return offsetof(struct ms_state,mk_c);
    case 2:return offsetof(struct ms_state,mk_local);
    case 3:return offsetof(struct ms_state,mk_joint);
    case 4:return offsetof(struct ms_state,mk_t);
    default:return 0;
    }
}
void test_marker_begin(uint8_t *p,uint8_t *m,void *proxy)
{
    test_damage_begin(p,0,0);
    struct ms_state *s=ms_of(p);
    s->mk_mon=m;s->mk_joint=3;s->mk_t=100;
    s->mk_local[0]=4;s->mk_local[1]=5;s->mk_local[2]=6;
    s->mk_c.h[0]=proxy;
    s->mk_c.at[0]=104;s->mk_c.at[1]=205;s->mk_c.at[2]=306;
    const unsigned q[]={MS_FXQ_MARKER};
    s->mk_c.id[0]=ms_fxq[q[0]].id;
}
unsigned test_marker_id(void) {const unsigned q[]={MS_FXQ_MARKER};return ms_fxq[q[0]].id;}
unsigned test_marker_life(uint8_t *p) {return (unsigned)(ms_of(p)->mk_t*100);}
