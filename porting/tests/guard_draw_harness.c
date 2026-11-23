#include "feedback_harness.c"
static unsigned fixture_drawn;
static uint32_t fixture_vt[556];
static int is_drawn(uint8_t *p) {(void)p;return fixture_drawn;}
void test_guard_draw_start(uint8_t *p,unsigned no,unsigned drawn)
{
    struct ms_state *s=ms_of(p);ms_reset(s);fixture_drawn=drawn;
    fixture_vt[0x178/4]=(uint32_t)(uintptr_t)is_drawn;
    fixture_vt[0x46c/4]=MAIN(0x282a48);
    *(uint32_t **)p=fixture_vt;
    action_start(p,s,find(no));
}
unsigned test_guard_draw_mode(uint8_t *p) {return ms_of(p)->mode;}
