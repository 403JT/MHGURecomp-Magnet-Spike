#ifndef MS_TEST_CLASS_SOURCE
#define MS_TEST_CLASS_SOURCE "ms_class.c"
#endif
#include MS_TEST_CLASS_SOURCE
uint32_t g_main_base=0x200000;
void logf(const char *fmt,...) {(void)fmt;}
void test_draw_route(uint8_t *p,unsigned index,uint16_t *out)
{
    const uint16_t *row=indirect(p,index);
    for (unsigned i=0;i<3;i++) out[i]=row[i];
}
