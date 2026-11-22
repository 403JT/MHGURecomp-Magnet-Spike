/* Regression entry points around the real weapon code, executed as ARM under
 * Unicorn. No game executable or game-data bytes are embedded in the tests. */
#ifndef MS_TEST_SOURCE
#define MS_TEST_SOURCE "ms_act.c"
#endif
#include MS_TEST_SOURCE

uint32_t g_main_base = 0x200000;
/* These tests isolate target validity; owned monster restraint has its own
 * suite executing the real pin.c implementation. */
int ms_monster_pin_begin(uint8_t *p,uint8_t *m) {(void)p;(void)m;return 1;}
int ms_monster_pin_valid(uint8_t *p,uint8_t *m) {(void)p;(void)m;return 1;}
void ms_monster_pin_end(uint8_t *p) {(void)p;}
void logf(const char *fmt, ...) { (void)fmt; }
void __aeabi_memclr4(void *p, uint32_t n)
{
    volatile uint8_t *out = p;
    while (n--) *out++ = 0;
}

int test_pointer(uint32_t p) { return fxw_ok(p); }
int test_owned(void *p, uint32_t id) { return fx_mine(p, id); }
uint32_t test_shot_id(void) { const uint32_t q[] = {MS_FXQ_SHOT}; return ms_fxq[q[0]].id; }
void test_carrier(struct ms_carrier *c, void *h, uint32_t id)
{
    for (uint32_t i = 0; i < sizeof *c; i++) ((uint8_t *)c)[i] = 0;
    c->h[0] = h; c->id[0] = (uint16_t)id;
}
void test_follow(uint8_t *p, struct ms_carrier *c, float *position)
{
    fx_follow(p, MS_FXQ_SHOT, position, 0, c, 1e9f, 0.5f);
}
void test_stop(struct ms_carrier *c) { fx_stop(c, "regression"); }
int test_marker(uint8_t *p, uint8_t *m, float *out)
{
    struct ms_state s = {0}; s.p = p; s.mk_mon = m;
    return marker(&s, out);
}
int test_pin_start(uint8_t *p, uint8_t *m)
{
    struct ms_state s = {0}; s.p = p; s.pin_pending = m;
    pin_start(p, &s);
    return s.pin_mon == 0 && s.pin_pending == 0;
}
int test_pin_tick(uint8_t *p, uint8_t *m)
{
    struct ms_state s = {0}; s.p = p; s.pin_mon = m;
    return pin_tick(p, &s, 0.5f, 99);
}
