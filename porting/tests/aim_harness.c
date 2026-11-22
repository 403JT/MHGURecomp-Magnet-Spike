/* Execute the real aim update against GU's original input reader. */
#ifndef MS_TEST_SOURCE
#define MS_TEST_SOURCE "ms_act.c"
#endif
#include MS_TEST_SOURCE
uint32_t g_main_base = 0x200000;
void test_aim(uint8_t *p, float *angles)
{
    struct ms_state s = {0};
    s.aim_yaw = angles[0]; s.aim_pitch = angles[1];
    aim_look(p, &s);
    angles[0] = s.aim_yaw; angles[1] = s.aim_pitch;
}
void __aeabi_memclr4(void *p, uint32_t n)
{
    volatile uint8_t *v = p;
    while (n--) *v++ = 0;
}
void __aeabi_memclr8(void *p, uint32_t n) { __aeabi_memclr4(p, n); }
#ifndef MS_TEST_LEGACY
static struct ms_state aim_state;
struct ms_state *ms_of(uint8_t *p) { (void)p; return &aim_state; }
void test_aim_frame(uint8_t *p, float *out)
{
    aim_frame(p, out, FIELD(uint16_t,p,0xfec), MS_AIM_PITCH(p));
}
void test_aim_callback(uint8_t *p, float *out) { ms_aim_cam(p, out, 0); }
void test_aim_callback_view(uint8_t *p, float *out, uint32_t yaw, int32_t pitch)
{
    aim_state.aim_view = 1; aim_state.aim_yaw = (float)yaw;
    aim_state.aim_pitch = (float)pitch;
    ms_aim_cam(p, out, 0);
    aim_state.aim_view = 0;
}
#endif
