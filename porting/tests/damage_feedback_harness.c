#include "feedback_harness.c"
void ms_sound_tick(uint8_t *p,struct ms_state *st,float tk) {(void)p;(void)st;(void)tk;}
static uint32_t test_vt[556];
static int drawn(uint8_t *p) {(void)p;return 1;}
void test_damage_begin(uint8_t *p,unsigned no,unsigned shock)
{
    struct ms_state *st=ms_of(p);ms_reset(st);st->action=(uint16_t)no;st->shock_on=(uint8_t)shock;
    test_vt[0x178/4]=(uint32_t)(uintptr_t)drawn;*(uint32_t **)p=test_vt;
    FIELD(uint16_t,p,0x2506)=0x10;FIELD(uint16_t,p,0x250a)=(uint16_t)no;
    FIELD(uint8_t,p,0x13cc)=1;FIELD(float,p,0x1c)=1;
}
void test_damage_arm(uint8_t *p,unsigned hit) {arm(p,ms_of(p),hit);}
void test_damage_tick(uint8_t *p,unsigned hundredths) {tick(p,ms_of(p),(float)hundredths*0.01f);}
unsigned test_damage_pending(uint8_t *p) {return ms_of(p)->shock_on;}
void test_damage_after_update(uint8_t *p) {ms_after_update(p);}
