/* Logging-only observer: no native engine or game data in this fixture. */
#include "ms_act.c"
uint32_t g_main_base=0x200000;
static struct ms_state owners[MS_PLAYERS+1];
static unsigned lines;
struct ms_state *ms_find(uint8_t *p)
{
    unsigned index=((uint32_t)(uintptr_t)p-0x0c010000u)/0x10000u;
    if (index>=MS_PLAYERS+1) return 0;
    owners[index].p=p;
    return &owners[index];
}
void logf(const char *fmt,...) {(void)fmt;lines++;}
void test_freeze_trace(uint8_t *p) {trace(p);}
unsigned test_freeze_lines(void) {return lines;}
