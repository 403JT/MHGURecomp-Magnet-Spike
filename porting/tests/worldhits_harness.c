#include "ms.h"
uint32_t g_main_base=0x200000;
static struct ms_state states[MS_PLAYERS];
struct ms_state *ms_find(uint8_t *p)
{
    if(!p)return 0;
    for(unsigned i=0;i<MS_PLAYERS;i++)if(states[i].p==p)return &states[i];
    return 0;
}
void logf(const char *fmt,...) {(void)fmt;}
void fixture_owner(unsigned i,uint8_t *p) {if(i<MS_PLAYERS)states[i].p=p;}
void fixture_arm(uint8_t *p,unsigned slot,unsigned hit,int world)
{
    struct ms_state *s=ms_find(p);if(s && slot<2)s->armed[slot]=(uint16_t)hit;
    ms_world_hit_armed(p,slot,hit,world);
}
void fixture_change_hit(uint8_t *p,unsigned slot,unsigned hit)
{
    struct ms_state *s=ms_find(p);if(s && slot<2)s->armed[slot]=(uint16_t)hit;
}
