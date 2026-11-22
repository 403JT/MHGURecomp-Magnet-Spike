#include "ms.h"
uint32_t g_main_base=0x200000;
void logf(const char *fmt,...) {(void)fmt;}
static struct ms_state state;
struct ms_state *ms_find(uint8_t *p) {return p==state.p?&state:0;}
void test_pin_bind(uint8_t *p,uint8_t *m) {state.p=p;state.pin_mon=m;state.flags=0;}
uint32_t test_pin_target(void) {return (uint32_t)state.pin_mon;}
#include "../module/pin.c"
