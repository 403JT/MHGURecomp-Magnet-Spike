/* Real action physics and pin input handling, with synthetic guest objects. */
#ifndef MS_TEST_SOURCE
#define MS_TEST_SOURCE "ms_act.c"
#endif
#include MS_TEST_SOURCE
uint32_t g_main_base=0x200000;
void ms_apply_hit_stats(uint8_t *p,unsigned slot,unsigned hit) {(void)p;(void)slot;(void)hit;}
void ms_world_hit_armed(uint8_t *p,unsigned slot,unsigned hit,int world) {(void)p;(void)slot;(void)hit;(void)world;}
void ms_cancel_windows_reset(uint8_t *p) {(void)p;}
void logf(const char *fmt,...) {(void)fmt;}
void __aeabi_memclr4(void *p,uint32_t n) {volatile uint8_t *q=p;while(n--)*q++=0;}
int ms_monster_pin_begin(uint8_t *p,uint8_t *m) {(void)p;(void)m;return 1;}
int ms_monster_pin_valid(uint8_t *p,uint8_t *m) {(void)p;(void)m;return 1;}
void ms_monster_pin_end(uint8_t *p) {(void)p;}
int ms_sound_post(uint8_t *p,unsigned slot,unsigned request) {(void)p;(void)slot;(void)request;return 1;}
static struct ms_state s;
struct ms_state *ms_of(uint8_t *p) {(void)p;return &s;}
static unsigned frame;
void test_flight_begin(uint8_t *p,unsigned no) {
    __aeabi_memclr4(&s,sizeof s);s.p=p;s.action=no;frame=0;
}
int test_flight_step(uint8_t *p) {
    const struct ms_action *a=find(s.action);
    /* Use the converted source action's actual flight events and their times. */
    for(unsigned i=0;i<a->nevents;i++) {
        const struct ms_event *e=&ms_events[a->ev0+i];
        if(e->step || (s.fired&(1u<<i)))continue;
        if(e->id!=1 && e->id!=25 && e->id!=28 && e->id!=30 && e->id!=31)continue;
        if(e->when==0 || (e->when==1 && frame>=e->frame))event(p,&s,e,i);
    }
    s.grav_t+=0.5f;frame++;
    return s.air?fall(p,&s,0.5f):0;
}
void test_qte_begin(uint8_t *p,uint8_t *m,unsigned impact) {
    __aeabi_memclr4(&s,sizeof s);s.p=p;s.pin_mon=m;s.pin_hold=90;s.flags=impact?0x8000:0;
}
int test_qte_step(uint8_t *p) {return pin_tick(p,&s,0.5f,99);}
unsigned test_qte_points(void) {return (unsigned)s.qte;}
unsigned test_pin_hit(uint8_t *p,uint8_t *m) {
    __aeabi_memclr4(&s,sizeof s);s.p=p;s.action=97;
    ms_on_hit(p,p+0x3020,m,1);
    return s.pin_pending==m;
}
