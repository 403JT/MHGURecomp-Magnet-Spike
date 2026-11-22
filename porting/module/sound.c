/* Local Frontier sound routing. GPL-3.0-or-later, as the standalone module.
 * GU 1.4 call interfaces/queue layout verified against its native sound helpers.
 * Only class 5 uses these IDs and resource names. */
#include "ms.h"

struct ms_sound_event {
    uint16_t mot, frame, bank, req[4], weight[4];
};
struct ms_code_sound {
    uint16_t mot,frame,action;
    uint8_t gate,req,joint;
    int16_t offset[3];
};
#ifndef MS_SOUND_DATA
#define MS_SOUND_DATA "ms_sound_data.inc"
#endif
#include MS_SOUND_DATA
#define MS_SOUND_MODEL_ID 0x10a00u
#define MS_SOUND_CLASS_ID 0x10a01u

int ms_local_sound_file(uint32_t *regs)
{
    if (regs[R1] != MS_CLASS) return 0;
    regs[R0] = regs[R3] == 1 ? MS_SOUND_MODEL_ID : regs[R3] == 0 ? MS_SOUND_CLASS_ID : 0;
    logf("ms-sound: resolve slot-kind %u -> file %x", regs[R3], regs[R0]);
    return 1;
}

int ms_local_file_id_c(uint32_t *regs)
{
#ifdef MS_GS_TREE
    extern int ms_tree_file_id(uint32_t *);
    if (ms_tree_file_id(regs)) return 1;
#endif
    uint32_t id = regs[R1];
    if (id != MS_SOUND_MODEL_ID && id != MS_SOUND_CLASS_ID) return 0;
    void *mgr = *(void **)MAIN(0x2126a64);
    if (!mgr) { regs[R0] = 0; return 1; }
    typedef void *(*find_t)(void *, uint32_t, uint32_t, uint32_t);
    find_t find = (*(find_t **)mgr)[0x38 / 4];
    uint32_t hash = id == MS_SOUND_MODEL_ID ? MS_SOUND_MODEL_HASH : MS_SOUND_CLASS_HASH;
    regs[R0] = (uint32_t)find(mgr, (uint32_t)find, hash, 0x1bcc4966);
    logf("ms-sound: file %x loaded %x", id, regs[R0]);
    return 1;
}

/* This is the bounded native 0x4efb98 position-request enqueue, with an explicit
 * request-slot selection. Native helpers hard-code slot 0 (monster/common); a
 * hunter's model/class live in slots 2/4. Resource refcount and queue consumption
 * stay with the engine. Full queue drops the cue, never overwrites a live entry. */
int ms_sound_post_at(uint8_t *p, unsigned slot, unsigned request, const float *pos)
{
    if (!p || !pos || (slot != 2 && slot != 4) || request == 0xffff) return 0;
    typedef void *(*get_t)(void *, unsigned);
    void *resource = FN(get_t, 0x4d5e14)(p + 0x111c, slot);
    uint8_t *mgr = *(uint8_t **)MAIN(0x1896f5c);
    if (!mgr || !resource) return 0;
    typedef int (*area_t)(void *, unsigned);
    unsigned area = FIELD(uint8_t, p, 0x1054);
    if (FN(area_t, 0x4df890)(mgr, area) != 1) return 0;
    uint8_t *q = mgr + 0xec;
    unsigned k;
    for (k = 0; k < 64 && q[k * 0x24]; k++);
    if (k == 64) return 0;
    q += k * 0x24;
    q[0] = 1; q[1] = 0; q[2] = 8; q[3] = 1;
    FIELD(float, q, 4) = pos[0];
    FIELD(float, q, 8) = pos[1];
    FIELD(float, q, 12) = pos[2];
    FIELD(uint32_t, q, 0x10) = request;
    FIELD(void *, q, 0x14) = p;
    FIELD(uint32_t, q, 0x18) = 0;
    FIELD(void *, q, 0x1c) = p;
    FIELD(void *, q, 0x20) = resource;
    FN(void (*)(void *), 0x887648)(resource);
    static unsigned logged;
    if (logged++ < 400) logf("ms-sound: post slot %u request %u motion %u frame %d", slot, request,
                           CUR_MOTION(p), (int)MS_FRAME(p));
    return 1;
}

int ms_sound_post(uint8_t *p, unsigned slot, unsigned request)
{
    return ms_sound_post_at(p,slot,request,p?(const float *)(p+0x40):0);
}

static int sound_joint(uint8_t *p,unsigned req,unsigned joint,const int16_t *off)
{
    const uint8_t *ids=FIELD(const uint8_t *,p,0x498),*js=FIELD(const uint8_t *,p,0x494);
    if (!ids || !js || joint==255 || ids[joint]==255) return ms_sound_post(p,4,512+req);
    const float *m=(const float *)(js+0xa0*ids[joint]+0x10);
    float q[3];
    for (int i=0;i<3;i++) q[i]=m[12+i]+m[i]*off[0]+m[4+i]*off[1]+m[8+i]*off[2];
    return ms_sound_post_at(p,4,512+req,q);
}

void ms_sound_guarded(uint8_t *p,struct ms_state *s)
{
    if (s->action!=14 || s->gc_hits>=2) return;
    const int16_t off[3]={30,0,-100};
    ms_sound_post(p,4,512+12);
    if (!s->snd_fx13) {sound_joint(p,13,8,off);s->snd_fx13=1;}
    s->snd_guard_delay=4; /* second guard hand effect at source frame 4 */
}

/* GU 0x1802cc: collision audio (defender, target, collision record, world point).
 * Record +0x70 is the attacking hunter; +6 is GU's hit tier, +0x55 the hit kind.
 * GU's three successful-hit tiers 2/3/4 select the three source volume steps.
 * Tiers 0/1 and nonstandard kinds retain native handling until mapped.
 * Source MHF 0x10930570 / 0x10930610: Cutting = 32..34; Impact = 29..31.
 * Replacing the physical branch avoids double hits. Its auxiliary elemental/
 * status branch at 0x180c84 still runs with the original arguments. */
int ms_local_hit_sound_c(uint32_t *regs)
{
    uint8_t *hit = (uint8_t *)regs[R2];
    if (!hit) return 0;
    uint8_t *p = FIELD(uint8_t *,hit,0x70);
    struct ms_state *s = ms_find(p);
    if (!s) return 0;
    uint8_t *info = FIELD(uint8_t *,p,0x13c4);
    if ((uintptr_t)info < MS_HEAP_POINTER_MIN || (uintptr_t)info >= MS_HEAP_POINTER_END || info[0x4d4] != MS_CLASS) return 0;
    unsigned tier = hit[6], kind = hit[0x55];
    static unsigned logs;
    if (logs++ < 120) logf("ms-sound: collision kind %u tier %u mode %u action %u",kind,tier,s->mode,s->action);
    if (kind > 2 || tier < 2 || tier > 4 || !regs[R3]) return 0;
    unsigned mode = s->mode != 0;
    unsigned req = 512 + (mode ? 29 : 32) + tier - 2;
    if (!ms_sound_post_at(p,4,req,(const float *)regs[R3])) return 0;
    if (s->mag[mode] == 1) ms_sound_post_at(p,4,512+35,(const float *)regs[R3]);
    typedef void (*aux_t)(void *,void *,void *,const float *);
    FN(aux_t,0x180c84)((void *)regs[R0],(void *)regs[R1],hit,(const float *)regs[R3]);
    return 1;
}

void ms_sound_tick(uint8_t *p, struct ms_state *s, float tk)
{
    s->snd_fx13=0;
    if (s->snd_guard_delay>0 && (s->snd_guard_delay-=2*tk)<=0) {
        const int16_t off[3]={40,0,100};
        sound_joint(p,13,8,off);s->snd_fx13=1;s->snd_guard_delay=0;
    }
    uint32_t m = CUR_MOTION(p);
    float f = MS_FRAME(p);
    /* GU hit-stop can move a playing motion backwards by one frame. That is
     * not a new loop and must not replay every earlier sound in the attack. */
    if (m != s->snd_mot || f + 2.0f < s->snd_frame) {
        s->snd_mot = m;
        s->snd_floor = ms_motion_start(p,m);
        s->snd_done[0] = s->snd_done[1] = 0;
        s->snd_code_done=0;
        int lo = 0, hi = MS_NSOUNDS;
        while (lo < hi) { int mid = (lo + hi) / 2; if (ms_sounds[mid].mot + 5000u < m) lo = mid + 1; else hi = mid; }
        s->snd_first = (uint16_t)lo;
        lo=0;hi=MS_NCODE_SOUNDS;
        while (lo<hi) {int mid=(lo+hi)/2;if (ms_code_sounds[mid].mot+5000u<m) lo=mid+1;else hi=mid;}
        s->snd_code_first=(uint16_t)lo;
    }
    s->snd_frame = f;
    if (m < 5000 || m >= 6000) return;
    for (unsigned k = 0; k < 64 && s->snd_first + k < MS_NSOUNDS; k++) {
        const struct ms_sound_event *e = &ms_sounds[s->snd_first + k];
        if (e->mot + 5000u != m) break;
        if (s->snd_done[k / 32] & (1u << (k % 32))) continue;
        if ((float)e->frame<s->snd_floor) {s->snd_done[k/32]|=1u<<(k%32);continue;}
        if (!MS_REACHED(p, (float)e->frame)) continue;
        s->snd_done[k / 32] |= 1u << (k % 32);
        unsigned total = 0, req = e->req[0];
        for (int j = 0; j < 4; j++) total += e->weight[j];
        if (total) {
            /* Independent PRNG: cue variation must not advance GU's combat RNG.
             * Preserve all four source weights, including a silent outcome. */
            if (!s->snd_rng) s->snd_rng = (uint32_t)(uintptr_t)p ^ 0x9e3779b9u;
            uint32_t x = s->snd_rng;
            x ^= x << 13; x ^= x >> 17; x ^= x << 5; s->snd_rng = x;
            unsigned pick = x % total;
            for (int j = 0; j < 4; j++) {
                if (pick < e->weight[j]) { req = e->req[j]; break; }
                pick -= e->weight[j];
            }
        }
        ms_sound_post(p, e->bank, req);
        if (req==512+13) s->snd_fx13=1;
    }
    for (unsigned k=0;k<32 && s->snd_code_first+k<MS_NCODE_SOUNDS;k++) {
        const struct ms_code_sound *e=&ms_code_sounds[s->snd_code_first+k];
        if (e->mot+5000u!=m) break;
        if (s->snd_code_done&(1u<<k)) continue;
        if ((float)e->frame<s->snd_floor) {s->snd_code_done|=1u<<k;continue;}
        if (e->action!=65535 && e->action!=s->action) continue;
        int mag=s->mag[s->mode!=0]==1;
        if ((e->gate==1 && !mag) || (e->gate==2 && mag)) continue;
        if (!MS_REACHED(p,(float)e->frame)) continue;
        s->snd_code_done|=1u<<k;
        if (e->req==13 && s->snd_fx13) continue;
        sound_joint(p,e->req,e->joint,e->offset);
        if (e->req==13) s->snd_fx13=1;
    }
}
