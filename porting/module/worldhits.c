/* Freeze Magnetic Shock's collision geometry in world space after spawning.
 * GU 1.4: 1696fc builds weapon shapes through 16dddc; 169828 receives
 * type R0, attack R4, record R6, index R7 and float[9] output R9. 1706a8 copies
 * endpoints [0..2]/[4..6] and radius [8] into the native collision cache.
 * Only registered Shock slots are changed. Native damage/hit ownership stays.
 * MHF 1004d650 computes each new spot from the hunter at that spawn; its
 * posted attack then owns the world point. Future pulses remain independent. */
#include "ms.h"

#define WORLD_SHAPES 4
struct world_slot {
    uint8_t *attack;
    const uint8_t *resource,*record[WORLD_SHAPES];
    unsigned shape_set;
    unsigned hit;
    uint8_t mask, moved, type[WORLD_SHAPES];
    float geometry[WORLD_SHAPES][7];
};
struct world_owner { uint8_t *p; struct world_slot slots[2]; };
static struct world_owner owners[MS_PLAYERS];
static const unsigned offsets[7]={0,1,2,4,5,6,8};

void ms_world_hits_reset(uint8_t *p)
{
    for (unsigned i=0;i<MS_PLAYERS;i++) if (owners[i].p==p) {
        owners[i].p=0;owners[i].slots[0].hit=owners[i].slots[1].hit=0;
    }
}

void ms_world_hit_armed(uint8_t *p,unsigned slot,unsigned hit,int world)
{
    if (!p || slot>=2) return;
    struct world_owner *owner=0,*free_=0;
    for (unsigned i=0;i<MS_PLAYERS;i++) {
        if (owners[i].p==p) {owner=&owners[i];break;}
        if (!free_ && (!owners[i].p || !ms_find(owners[i].p))) free_=&owners[i];
    }
    if (!world) {if(owner)owner->slots[slot].hit=0;return;}
    if (!owner) {
        if (!free_) return;
        owner=free_;owner->p=p;owner->slots[0].hit=owner->slots[1].hit=0;
    }
    struct world_slot *s=&owner->slots[slot];
    s->attack=p+0x3020+slot*0xb8;
    s->resource=FIELD(const uint8_t *,s->attack,0x84);
    s->shape_set=FIELD(unsigned,s->attack,0x88);
    s->hit=s->resource?hit:0;s->mask=0;s->moved=0;
}

int ms_local_world_shape_c(uint32_t *regs,const uint8_t *record,float *shape,unsigned index)
{
    unsigned type=regs[R0];
    if ((type!=1 && type!=2) || !shape || ((uintptr_t)shape&3) ||
        !record || ((uintptr_t)record&3) || index>=WORLD_SHAPES) return 0;
    uint8_t *attack=(uint8_t *)(uintptr_t)regs[R4];
    for (unsigned i=0;i<MS_PLAYERS;i++) for(unsigned slot=0;slot<2;slot++) {
        struct world_owner *owner=&owners[i];struct world_slot *s=&owner->slots[slot];
        if (!s->hit || s->attack!=attack) continue;
        struct ms_state *state=ms_find(owner->p);
        if (!state || state->armed[slot]!=s->hit ||
            FIELD(uint8_t *,attack,0xc)!=owner->p || FIELD(uint8_t *,attack,0x70)!=owner->p ||
            FIELD(const uint8_t *,attack,0x84)!=s->resource ||
            FIELD(unsigned,attack,0x88)!=s->shape_set) {s->hit=0;return 0;}
        unsigned bit=1u<<index;
        if (!(s->mask&bit)) {
            for(unsigned j=0;j<7;j++) {
                if(type==1 && j>=3 && j<=5)continue; /* sphere has no second endpoint */
                float v=shape[offsets[j]];
                if (!(v>=-1e8f && v<=1e8f) || (j==6 && v<0)) return 0;
            }
            for(unsigned j=0;j<7;j++)if(type!=1 || j<3 || j==6)s->geometry[index][j]=shape[offsets[j]];
            s->record[index]=record;s->type[index]=(uint8_t)type;s->mask|=bit;
            static unsigned n;
            if(n++<64)logf("ms-world: anchored hit %u slot %u shape %u type %u at %d %d %d radius %d",
                s->hit,slot,index,type,(int)shape[0],(int)shape[1],(int)shape[2],(int)shape[8]);
        } else if (s->record[index]!=record) {s->hit=0;return 0;}
        else if (s->type[index]==type) {
            float dx=shape[0]-s->geometry[index][0],dy=shape[1]-s->geometry[index][1],dz=shape[2]-s->geometry[index][2];
            if (!(s->moved&bit) && dx*dx+dy*dy+dz*dz>1) {
                s->moved|=bit;static unsigned n;
                if(n++<64)logf("ms-world: retained hit %u slot %u shape %u after transform moved %d %d %d",
                    s->hit,slot,index,(int)dx,(int)dy,(int)dz);
            }
            for(unsigned j=0;j<7;j++)if(type!=1 || j<3 || j==6)shape[offsets[j]]=s->geometry[index][j];
        }
        return 0;
    }
    return 0;
}
