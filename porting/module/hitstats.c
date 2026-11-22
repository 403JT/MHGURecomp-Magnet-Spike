/* GPL-3.0-or-later. Source KO after GU's attack constructor has run.
 * 0x168a64 clamps HDP byte 0x22 as signed; 0x173040 instead reads the live
 * attack +0x56 as unsigned, then 0x173894 applies KO through 0x9db54.
 * Writing the live byte retains the source's 190-KO hit without truncation.
 * The native KO-skill predicate (0x2b762c) is reapplied once to the source
 * value. Its 1.1 multiplier is retained; the byte cap extends to 255 so a
 * 190-KO source attack is not reduced to 127 when a KO skill is present.
 * No direct monster buildup, threshold, exhaust, or HP edits. */
#include "ms.h"
#ifndef MS_HITSTATS_DATA
#define MS_HITSTATS_DATA "ms_hitstats_data.inc"
#endif
#include MS_HITSTATS_DATA
#ifdef MS_BALANCE
#include "ms_balance_data.inc"
#if MS_BALANCE_HIT_COUNT != MS_NHIT_STATS
#error Balance and KO hit mappings must have identical bounds
#endif
#endif
void ms_apply_hit_stats(uint8_t *p,unsigned slot,unsigned hit)
{
    if (!p || slot>=2 || hit>=MS_NHIT_STATS) return;
    unsigned ko=ms_hit_ko[hit];
#ifdef MS_BALANCE
    ko=ms_balance_ko[hit];
#endif
    typedef int (*gate_t)(void *);
    if (ko && !FN(gate_t,0x27b918)(p) &&
        (MS_HAS_SKILL(p,0xac) || MS_HAS_SKILL(p,0x109) || MS_HAS_SKILL(p,0x132) ||
         FN(ms_evlvl_t,0x2864d4)(p,0x28)==1)) {
        ko=(unsigned)((float)ko*1.1f);
        if (ko>255) ko=255;
    }
    FIELD(uint8_t,p+0x3020+slot*0xb8,0x56)=(uint8_t)ko;
#ifdef MS_BALANCE
    // Native construction has completed. Change only its two damage-power
    // fields; timing, element flags, shapes and ownership remain native.
    if (hit<MS_BALANCE_HIT_COUNT) {
        uint8_t *attack=p+0x3020+slot*0xb8;
        unsigned mv=ms_balance_mv[hit];
        FIELD(uint16_t,attack,0x38)=(uint16_t)(mv>250?250:mv);
        FIELD(uint16_t,attack,0x9c)=(uint16_t)mv;
    }
#endif
}
