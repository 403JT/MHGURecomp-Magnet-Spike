/* Standalone Magnet Spike adapter. GPL-3.0-or-later, as the upstream module.
 * No monster registry, quest additions, or unrelated hooks. */
#include "ms.h"

void module_init(void)
{
    if (FIELD(uint32_t, (void *)MAIN_BASE, 0x56ef50) != 0xe92d41f0u) {
        logf("ms-local: incompatible main module base");
        return;
    }
    ms_init();
    logf("ms-local: experimental Magnet Spike module initialized");
}

int ms_local_text_c(uint32_t *regs)
{
    uint8_t *msg = (uint8_t *)regs[R4];
    if (msg) ms_text_loaded(msg, FIELD(const char *, msg, 0x8c), 0);
    return 0;
}
