# Freeze status for alpha.5

The reproduced action-153 stall in Double Slash's late X+A follow-up is fixed
by restoring its motion length, without adding a runtime watchdog. See
[MOTION_FIXES.md](MOTION_FIXES.md) and release-validation.json. Ordinary input
tests on the combined build entered and completed the follow-up twice.

The user video lacks a matching game log, so it is not established that it
shows this exact path. Other freeze causes and the parry report remain
unconfirmed. Extra freeze tracing is disabled in this release. A report should
include the mod/runtime versions, hunting style, input sequence and game log
when available.
