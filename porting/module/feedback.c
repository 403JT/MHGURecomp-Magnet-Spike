/* Public Recomp feedback fixes. GPL-3.0-or-later. */
#include "ms.h"

/* GU 1.4 cUIOChatFixedPharase's input update calls 65f914 at 576a5c to
 * obtain the quick-message button mask. Hook after its PC-relative loads,
 * returning an empty mask only to that caller in an online Magnet Spike
 * quest. The weapon's own input words and every other caller are untouched. */
int ms_local_quick_message_c(uint32_t *regs)
{
    if (regs[LR]-MAIN_BASE!=0x576a60) return 0;
    uint8_t *mgr=*(uint8_t **)MAIN(0x1885b58), *p=0;
    for (unsigned i=0;mgr && i<MS_PLAYERS;i++) {
        uint8_t *candidate=FIELD(uint8_t *,mgr,0x1c+4*i);
        if (candidate && MS_IS_LOCAL(candidate)) {p=candidate;break;}
    }
    if (!p || !ms_find(p)) return 0;
    uint8_t *info=FIELD(uint8_t *,p,0x13c4);
    if (!info || info[0x4d4]!=MS_CLASS) return 0;
    void *network=*(void **)MAIN(0x18843f0);
    if (!network || !FN(ms_p_t,0x227ba8)(network)) return 0;
    regs[R0]=0;
    static unsigned n;
    if (n++<8) logf("ms-feedback: multiplayer quick-message shortcut suppressed for Magnet Spike");
    return 1;
}

/* Collision can interrupt a hunter after its input update. Reject stale MS
 * hits in that same pass rather than waiting for the next cleanup tick. */
int ms_local_attack_live_c(uint32_t *regs)
{
    uint32_t caller=regs[LR]-MAIN_BASE;
    if (caller!=0x16ac74 && caller!=0x16b1b8) return 0;
    uint8_t *attack=(uint8_t *)(uintptr_t)regs[R0];
    uint8_t *p=FIELD(uint8_t *,attack,0xc);
    struct ms_state *s=ms_find(p);
    if (!s) return 0;
    unsigned slot=attack==p+0x3020?0:attack==p+0x30d8?1:2;
    if (slot>=2 || !ms_attack_matches(p,s,slot)) return 0;
    uint8_t *mgr=*(uint8_t **)MAIN(0x1885b58);
    unsigned registered=0;
    for (unsigned i=0;mgr && i<MS_PLAYERS;i++) registered|=FIELD(uint8_t *,mgr,0x1c+4*i)==p;
    if (registered) {
        uint8_t *info=FIELD(uint8_t *,p,0x13c4);
        if (!info || info[0x4d4]!=MS_CLASS) return 0;
        if (FIELD(uint16_t,p,0x2506)==0x10 && FIELD(uint16_t,p,0x250a)==s->action) return 0;
    }
    regs[R0]=0;
    return 1;
}
