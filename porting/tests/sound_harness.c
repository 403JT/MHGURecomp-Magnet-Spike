#include "ms.h"
uint32_t g_main_base = 0x200000;
void logf(const char *fmt, ...) { (void)fmt; }
#define MS_SOUND_DATA "sound_fixture.inc"
#include "../module/sound.c"
static struct ms_state state;
static unsigned segment_start;
float ms_motion_start(uint8_t *p,uint32_t m) {(void)p;(void)m;return (float)segment_start;}
void test_sound_segment(unsigned f) {segment_start=f;}
struct ms_state *ms_find(uint8_t *p) { return p && p == state.p ? &state : 0; }
void test_sound_bind(uint8_t *p, unsigned mode, unsigned mag) {
    state.p=p; state.mode=mode; state.mag[0]=state.mag[1]=0; state.mag[mode!=0]=mag;
}
void test_sound_tick(uint8_t *p) { ms_sound_tick(p, &state,0.5f); }
void test_code_state(unsigned action,unsigned mode,unsigned mag) {
    state.action=action;state.mode=mode;state.mag[0]=state.mag[1]=0;state.mag[mode!=0]=mag;
}
void test_sound_guard(uint8_t *p,unsigned action,unsigned hits) {
    state.action=action;state.gc_hits=hits;ms_sound_guarded(p,&state);
}
void test_sound_reset(void) {
    segment_start=0;
    unsigned char *b = (unsigned char *)&state;
    for (unsigned i=0; i<sizeof state; i++) b[i]=0;
}
