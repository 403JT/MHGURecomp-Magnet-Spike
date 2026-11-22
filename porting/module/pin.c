/* Owned magnetic restraint for the standalone single-player port.
 * GPL-3.0-or-later. GU adaptation: pause the monster's current action/pose while
 * retaining HP/status processing and collision reception. No trap resistance,
 * paralysis buildup, or monster vtable is modified. */
#include "ms.h"

struct pin_lock {
    uint8_t *owner,*monster,*record;
    uint16_t id,serial;
    float pos[3],velocity[3],acceleration[3],vertical,rate;
    uint16_t yaw;
    uint8_t deferred;
    uint32_t cat,no,mode;
};
static struct pin_lock locks[MS_PLAYERS];

static int player_live(uint8_t *p)
{
    uint8_t *mgr=*(uint8_t **)MAIN(0x1885b58);
    if (!p || !mgr) return 0;
    for (unsigned i=0;i<4;i++) if (FIELD(uint8_t *,mgr,0x1c+4*i)==p) return 1;
    return 0;
}

static int monster_live(const struct pin_lock *l)
{
    uint8_t *mgr=*(uint8_t **)MAIN(0x1851fe0);
    if (!l->monster || !mgr) return 0;
    typedef void *(*get_t)(void *,unsigned);
    for (unsigned i=0;i<10;i++) if (FN(get_t,0x5ceb4)(mgr,i)==l->monster) {
        uint8_t *r=FIELD(uint8_t *,l->monster,0x1428);
        return r==l->record && FIELD(uint16_t,l->monster,0xb5f0)==l->id &&
               FIELD(uint16_t,r,0x1b6)==l->serial;
    }
    return 0;
}

static void release(struct pin_lock *l,int notify)
{
    if (!l->owner) return;
    struct pin_lock old;
    volatile uint8_t *dst=(volatile uint8_t *)&old;
    const volatile uint8_t *src=(const volatile uint8_t *)l;
    for (unsigned i=0;i<sizeof old;i++) dst[i]=src[i];
    l->owner=0;l->monster=0; /* clear ownership before calling any hooked engine path */
    uint8_t *m=old.monster,*r=old.record;
    if (monster_live(&old)) {
      if (FIELD(float,r,0x398)==0) {
        typedef void (*rate_t)(void *,float);
        FN(rate_t,0xb0870)(m,old.rate);
      }
      if (FIELD(int32_t,r,0x370)>0 && !old.deferred) {
        for (unsigned i=0;i<3;i++) {
            FIELD(float,r,0x10+4*i)=old.velocity[i];
            FIELD(float,r,0x20+4*i)=old.acceleration[i];
        }
        FIELD(float,r,0x5c)=old.vertical;
      }
      if (old.deferred && FIELD(int32_t,r,0x370)>0) {
        typedef void (*act_t)(void *,unsigned,unsigned,unsigned,unsigned);
        FN(act_t,0x76154)(m,old.cat,old.no,old.mode,0);
      }
    }
    if (notify && player_live(old.owner)) {
        struct ms_state *s=ms_find(old.owner);
        if (s && s->pin_mon==m) {
            s->pin_mon=0;s->flags&=~0x10u;
            unsigned cat=FIELD(uint16_t,old.owner,0x2506),no=FIELD(uint16_t,old.owner,0x250a);
            if (FIELD(int16_t,old.owner,0x13d6)>0 && cat==0x10 && (no==98 || no==99))
                MS_SET_ACTION(old.owner,0x10,(s->flags&0x8000)?156:100,0);
        }
    }
    logf("ms-pin: released monster %x (deferred %u)",(uint32_t)m,old.deferred);
}

void ms_monster_pin_end(uint8_t *p)
{
    for (unsigned i=0;i<MS_PLAYERS;i++) if (locks[i].owner==p) release(&locks[i],0);
}

static int valid(struct pin_lock *l)
{
    if (!player_live(l->owner) || !monster_live(l)) return 0;
    uint8_t *p=l->owner,*m=l->monster,*info=FIELD(uint8_t *,p,0x13c4);
    struct ms_state *s=ms_find(p);
    if (!s || s->pin_mon!=m || !info || info[0x4d4]!=MS_CLASS || FIELD(int32_t,l->record,0x370)<=0 ||
        FIELD(int16_t,p,0x13d6)<=0) return 0;
    if (FIELD(uint8_t,p,0x1054)!=FIELD(uint8_t,m,0x1054)) return 0;
    unsigned cat=FIELD(uint16_t,p,0x2506),no=FIELD(uint16_t,p,0x250a);
    return cat==0x10 && (no==98 || no==99 || no==105 || no==157);
}

int ms_monster_pin_begin(uint8_t *p,uint8_t *m)
{
    if (!player_live(p) || !m) return 0;
    struct pin_lock *free=0;
    for (unsigned i=0;i<MS_PLAYERS;i++) {
        if (locks[i].owner==p) release(&locks[i],0);
        if (locks[i].monster==m) return 0;
        if (!locks[i].owner) free=&locks[i];
    }
    if (!free) return 0;
    /* Establish membership before reading the supplied monster pointer. */
    uint8_t *mgr=*(uint8_t **)MAIN(0x1851fe0);int found=0;
    typedef void *(*get_t)(void *,unsigned);
    if (mgr) for (unsigned i=0;i<10;i++) if (FN(get_t,0x5ceb4)(mgr,i)==m) found=1;
    if (!found || FIELD(uint8_t,m,0xb5f7)) return 0;
    uint8_t *r=FIELD(uint8_t *,m,0x1428);
    if (!r || FIELD(int32_t,r,0x370)<=0 || FIELD(uint8_t,m,0x1054)!=FIELD(uint8_t,p,0x1054)) return 0;
    free->owner=p;free->monster=m;free->record=r;free->deferred=0;
    free->id=FIELD(uint16_t,m,0xb5f0);free->serial=FIELD(uint16_t,r,0x1b6);
    free->rate=FIELD(float,r,0x398);free->vertical=FIELD(float,r,0x5c);
    free->yaw=FIELD(uint16_t,r,0x54);
    for (unsigned i=0;i<3;i++) free->pos[i]=FIELD(float,r,0x40+4*i);
    for (unsigned i=0;i<3;i++) {
        free->velocity[i]=FIELD(float,r,0x10+4*i);
        free->acceleration[i]=FIELD(float,r,0x20+4*i);
    }
    logf("ms-pin: restrained monster %x owner %x",(uint32_t)m,(uint32_t)p);
    return 1;
}

int ms_monster_pin_valid(uint8_t *p,uint8_t *m)
{
    for (unsigned i=0;i<MS_PLAYERS;i++) if (locks[i].owner==p && locks[i].monster==m) {
        if (valid(&locks[i])) return 1;
        release(&locks[i],1);return 0;
    }
    return 0;
}

static struct pin_lock *held(uint8_t *m)
{
    for (unsigned i=0;i<MS_PLAYERS;i++) if (locks[i].owner && locks[i].monster==m) {
        if (valid(&locks[i])) return &locks[i];
        release(&locks[i],1);return 0;
    }
    return 0;
}

static void enforce(struct pin_lock *l)
{
    typedef void (*stop_t)(void *);
    typedef void (*flag_t)(void *,unsigned);
    typedef void (*rate_t)(void *,float);
    FN(stop_t,0x7bdd4)(l->monster);
    FN(flag_t,0x7e048)(l->monster,0);FN(flag_t,0x7e048)(l->monster,1);
    for (unsigned k=0;k<3;k++) {
        FIELD(float,l->record,0x40+4*k)=l->pos[k];
        FIELD(float,l->monster,0x40+4*k)=l->pos[k];
    }
    FIELD(uint16_t,l->record,0x54)=l->yaw;
    FIELD(float,l->record,0x5c)=0;
    FN(rate_t,0xb0870)(l->monster,0);
}

int ms_local_pin_ai_c(uint32_t *regs)
{
    struct pin_lock *l=held((uint8_t *)regs[R0]);
    if (!l) return 0;
    enforce(l);
    regs[R0]=0;return 1;
}

int ms_local_pin_action_c(uint32_t *regs)
{
    struct pin_lock *l=held((uint8_t *)regs[R0]);
    if (!l) return 0;
    if (regs[R1]==11 || regs[R1]==14) {release(l,1);return 0;}
    if (regs[R1]==10) {l->deferred=1;l->cat=regs[R1];l->no=regs[R2];l->mode=regs[R3];}
    return 1;
}

int ms_local_pin_update_c(uint32_t *regs)
{
    (void)regs;
    for (unsigned i=0;i<MS_PLAYERS;i++) if (locks[i].owner) {
        struct pin_lock *l=&locks[i];
        if (!valid(l)) {release(l,1);continue;}
        enforce(l);
    }
    return 0;
}
