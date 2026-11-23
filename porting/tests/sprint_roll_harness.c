/* Full real input translator; native common input bits are preseeded as GU
 * supplies them before dispatch. No game data embedded in this fixture. */
#include "feedback_harness.c"
void ms_sound_tick(uint8_t *p,struct ms_state *s,float tk) {(void)p;(void)s;(void)tk;}
int ms_weapon_element(uint32_t id,uint32_t *t,uint32_t *v) {(void)id;(void)t;(void)v;return 0;}
static unsigned fixture_drawn;
static uint32_t fixture_vt[556];
static int drawn(uint8_t *p) {(void)p;return fixture_drawn;}
static int stat(uint8_t *p,unsigned n) {(void)p;(void)n;return 0;}
void test_sprint_begin(uint8_t *p,unsigned is_drawn,unsigned gauge,unsigned mode)
{
    struct ms_state *s=ms_of(p);ms_reset(s);
    fixture_drawn=is_drawn;
    fixture_vt[0x178/4]=(uint32_t)(uintptr_t)drawn;
    fixture_vt[0x15c/4]=(uint32_t)(uintptr_t)stat;
    *(uint32_t **)p=fixture_vt;
    s->gauge=(int)gauge;s->mode=(uint8_t)mode;
    FIELD(uint8_t,p,0x13cc)=1;FIELD(float,p,0x1c)=1;
    FIELD(uint16_t,p,0x2506)=2;FIELD(uint16_t,p,0x250a)=is_drawn?0:2;
    FIELD(float,p,0x13e0)=900;
}
void test_sprint_input(uint8_t *p) {ms_input(p);}
