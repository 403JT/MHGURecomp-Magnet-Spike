/* Execute the production cursor/view functions with bounded actor fixtures. */
#include "ms_act.c"
uint32_t g_main_base = 0x200000;
static struct ms_state test_state;
static int last_reticle;
struct ms_state *ms_of(uint8_t *p) { (void)p; return &test_state; }
void logf(const char *format, ...) { (void)format; }
void ms_reticle(int frame) { last_reticle = frame; }
void test_aim_reset(uint8_t *p)
{
    for (unsigned i = 0; i < sizeof test_state; i++) ((uint8_t *)&test_state)[i] = 0;
    test_state.p = p;
    test_state.aim_yaw = 1000;
    test_state.aim_pitch = 500;
    last_reticle = 9;
}
void test_aim_flags(uint8_t *p, uint32_t flags, uint32_t local)
{
    test_state.flags = flags;
    FIELD(uint32_t, p, 0x13cc) = local;
}
void test_aim_view(uint8_t *p) { aim_view(p, &test_state); }
void test_aim_read(float *out)
{
    out[0] = test_state.aim_yaw; out[1] = test_state.aim_pitch;
    out[2] = test_state.aim_view; out[3] = last_reticle;
}
