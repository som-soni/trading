"""Bearish RSI divergence: price makes a higher swing high while RSI makes a lower one -- the advance going on with
less momentum behind it. One rule, here, for the chart's conflict check (web/server.py `/api/conflicts`); not a
chart indicator and never a trade rule.

A swing high is a bar whose high is the highest of SWING_BARS bars either side. The last two swing highs within
LOOKBACK bars are compared: the later one higher in price by at least MIN_PRICE_PCT, its RSI(RSI_LEN) lower by at
least MIN_RSI_DROP points. Read as of one bar, from bars up to it only -- a swing high needs SWING_BARS bars after
it, so the newest one it can see is that many bars old.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SWING_BARS = 5        # bars either side of a swing high
LOOKBACK = 60         # how far back the two swing highs may be
RSI_LEN = 14
MIN_PRICE_PCT = 0.5   # the later high at least this % above the earlier
MIN_RSI_DROP = 3.0    # its RSI at least this many points lower


def rsi(close: pd.Series, n: int = RSI_LEN) -> pd.Series:
    """Wilder's RSI."""
    d = close.diff()
    up, dn = d.clip(lower=0), (-d).clip(lower=0)
    au = up.ewm(alpha=1 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + au / ad.replace(0, np.nan))


def bearish(daily: pd.DataFrame) -> dict | None:
    """The divergence as of `daily`'s last bar, or None: {from, to, price_from, price_to, rsi_from, rsi_to}."""
    if len(daily) < LOOKBACK + SWING_BARS + RSI_LEN:
        return None
    h = daily["high"].to_numpy(float)
    r = rsi(daily["close"]).to_numpy(float)
    n = len(h)
    lo = max(SWING_BARS, n - LOOKBACK)
    highs = [i for i in range(lo, n - SWING_BARS)
             if h[i] == h[i - SWING_BARS:i + SWING_BARS + 1].max() and not np.isnan(r[i])]
    if len(highs) < 2:
        return None
    a, b = highs[-2], highs[-1]
    if h[b] >= h[a] * (1 + MIN_PRICE_PCT / 100) and r[b] <= r[a] - MIN_RSI_DROP:
        d = daily.index
        return {"from": str(d[a].date()), "to": str(d[b].date()), "price_from": float(h[a]), "price_to": float(h[b]),
                "rsi_from": round(float(r[a]), 1), "rsi_to": round(float(r[b]), 1)}
    return None
