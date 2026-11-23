/* Real per-hunter state pool and action handlers; synthetic engine objects. */
#ifndef MS_TEST_SOURCE
#define MS_TEST_SOURCE "ms_act.c"
#endif
#include MS_TEST_SOURCE
uint32_t g_main_base=0x200000;
void logf(const char *fmt,...) {(void)fmt;}
void __aeabi_memclr4(void *p,uint32_t n) {volatile uint8_t *q=p;while(n--)*q++=0;}
void ms_apply_hit_stats(uint8_t *p,unsigned slot,unsigned hit) {(void)p;(void)slot;(void)hit;}
void ms_world_hit_armed(uint8_t *p,unsigned slot,unsigned hit,int world) {(void)p;(void)slot;(void)hit;(void)world;}
void ms_world_hits_reset(uint8_t *p) {(void)p;}
void ms_cancel_windows_reset(uint8_t *p) {(void)p;}
int ms_monster_pin_begin(uint8_t *p,uint8_t *m) {(void)p;(void)m;return 1;}
int ms_monster_pin_valid(uint8_t *p,uint8_t *m) {(void)p;(void)m;return 1;}
void ms_monster_pin_end(uint8_t *p) {(void)p;}
int ms_sound_post(uint8_t *p,unsigned slot,unsigned request) {(void)p;(void)slot;(void)request;return 1;}

void test_feedback_begin(uint8_t *p,unsigned no,unsigned local,unsigned dt100)
{
    struct ms_state *s=ms_of(p);
    ms_reset(s);
    s->action=(uint16_t)no;s->fired=s->code_fired=~0u;
    FIELD(uint16_t,p,0x2506)=0x10;FIELD(uint16_t,p,0x250a)=(uint16_t)no;
    FIELD(uint8_t,p,5)=find(no)->nsteps;
    FIELD(uint8_t,p,0x4b6)=4;
    FIELD(uint8_t,p,0x13cc)=(uint8_t)local;
    FIELD(float,p,0x1c)=(float)dt100*0.01f;
}

void test_feedback_act(uint8_t *p)
{
    /* The native local input path precedes the action handler; remote hunters
     * only run the action. Keep the original local clock update in this test. */
    if (FIELD(uint8_t,p,0x13cc)&1) recovery_clock(p,ms_of(p));
    ms_act(p);
}

unsigned test_feedback_clock(uint8_t *p) {return (unsigned)(ms_of(p)->action_clock*100+.5f);}
unsigned test_feedback_pending(uint8_t *p) {return ms_of(p)->recovery_end>0;}
void test_feedback_stamp(uint8_t *p,unsigned stamp)
{
    struct ms_state *s=ms_of(p);s->fired=stamp;s->gauge=(int32_t)stamp;
}
unsigned test_feedback_stamp_read(uint8_t *p)
{
    struct ms_state *s=ms_find(p);
    return s && s->fired==(unsigned)s->gauge ? s->fired : 0;
}
void test_feedback_swing_begin(uint8_t *p)
{
    struct ms_state *s=ms_of(p);ms_reset(s);s->action=0;
    FIELD(uint16_t,p,0x2506)=0x10;FIELD(uint16_t,p,0x250a)=0;
    FIELD(uint8_t,p,5)=1;FIELD(uint8_t,p,0x13cc)=1;
    FIELD(uint8_t,p,0x4b6)=0;
    FIELD(float,p,0x4fc)=40;FIELD(float,p,0x14d0)=40;
    FIELD(float,p,0x14d4)=1;FIELD(float,p,0x504)=200;
    FIELD(float,p,0x1c)=1;
}
