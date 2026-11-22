"""Separate long-lived carrier refresh from an effect that cannot finish building."""
import re

def lifetime_checks(text):
    ages=[int(n) for n in re.findall(r'ended by itself: re-posted\) after (\d+) ticks',text)]
    total=text.count('ended by itself: re-posted')
    return {'effect_reposts':total,
            'effect_refresh_ages_ticks':ages,
            # A persistent marker's particle run ends at 150 source ticks; it
            # is deliberately refreshed. Keep a conservative boundary: every
            # observed natural refresh must have lived at least 149 ticks.
            # Unknown/malformed log records fail closed.
            'premature_effect_reposts':sum(n<149 for n in ages)+total-len(ages)}
