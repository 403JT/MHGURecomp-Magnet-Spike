/* Execute real standalone code with bounded native GS fixtures. */
#include "../module/smithy.c"
uint32_t g_main_base=0x200000;
void logf(const char *fmt,...) {(void)fmt;}
uint32_t test_name(uint8_t *r,unsigned lv) {return (uint32_t)w_name_lv(r,lv);}
uint32_t test_type(void) {return box_type();}
