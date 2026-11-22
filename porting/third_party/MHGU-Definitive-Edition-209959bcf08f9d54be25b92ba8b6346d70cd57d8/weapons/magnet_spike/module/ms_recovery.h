/* Additional GU combo-end commitment, in 1/60-second game frames.
 * The command builder reads these entries too; keep this as the single policy.
 * Earlier attacks, charge holds, guard reactions and movement are not finishers. */
#pragma once
#define MS_RECOVERY_POLICY(X) \
    X(4, 18)   /* Cutting vertical combo final hit */ \
    X(10, 18)  /* Cutting horizontal third */ \
    X(26, 30)  /* Impact Suplex */ \
    X(28, 24)  /* Impact overhead */ \
    X(29, 24)  /* Impact down swipe */ \
    X(35, 30)  /* Triple Strike charged release */ \
    X(36, 30)  /* Triple Strike weak release */ \
    X(60, 18)  /* Cutting aerial landing */ \
    X(74, 24)  /* Impact aerial landing */ \
    X(105, 30) /* Cutting pin finisher */ \
    X(157, 30) /* Impact pin finisher */

static inline unsigned ms_recovery_frames(unsigned action)
{
    switch(action) {
#define MS_RECOVERY_CASE(action, frames) case action: return frames;
        MS_RECOVERY_POLICY(MS_RECOVERY_CASE)
#undef MS_RECOVERY_CASE
    default: return 0;
    }
}
