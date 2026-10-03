"""Universe-level filters that aren't strategy opinions.

The technical pre-filter moved onto the Strategy (`passes_prefilter`) —
a mean-reversion strategy wants a different one than a trend strategy.
What's left here is market-structural: a market-cap floor applies to every
strategy equally because it's about what you're willing to trade at all,
not about what the chart is doing.
"""


def passes_market_cap(min_cap_cr: float, market_cap_cr: float | None) -> bool:
    if market_cap_cr is None:
        return True  # unknown — don't silently exclude, flag upstream instead
    return market_cap_cr >= min_cap_cr
