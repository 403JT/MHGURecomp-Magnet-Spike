#include "ms.h"
uint32_t g_main_base=0x200000;
#define MS_NHIT_STATS 7
static const unsigned char ms_hit_ko[]={0,190,25,255,190,25,255};
#define MS_HITSTATS_DATA "hitstats_fixture.inc"
#include "../module/hitstats.c"
