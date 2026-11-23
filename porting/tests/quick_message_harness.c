#include "feedback.c"
uint32_t g_main_base=0x200000;
void logf(const char *fmt,...) {(void)fmt;}
static struct ms_state owner;
static unsigned known;
void test_quick_owner(uint8_t *p,unsigned on) {owner.p=p;known=on;}
struct ms_state *ms_find(uint8_t *p) {return known && owner.p==p ? &owner : 0;}
