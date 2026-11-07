"""The VCP contraction gauge: per-session readings of how coiled a stock is.

A volatility contraction pattern is several conditions tightening together. Three of them can be read on
every bar without finding the pattern's swings, so a chart can show them as numbers instead of a shape to
judge by eye. Each reading is a window of WINDOW sessions ending on that bar -- nothing after it -- and each
threshold is the Minervini strategy's own constant (strategies/minervini_spec.py), imported, never restated:

    tight  the window's range, high to low, as % of its high                      <= TIGHT_PCT
    dry    its average volume / the 50-day average on the bar before it           <= DRYUP_RATIO
    near   its high / the highest high of the last BASE_MAX_DAYS sessions         >= PIVOT_NEAR_HIGH

A session meeting all three is "coiled". A "breakout" is a close above the previous session's window high
on volume >= VOL_MULT x its 50-day average (today included), the session after a coiled one.

`reading` is the one definition. The chart's indicator (`gauge`, /api/contraction) and the coil-breakout
strategy (strategies/minervini_coil.py) both call it, so what the chart shows is what the backtest traded on.

These are readings, not the Minervini strategy. They cannot see what makes a base a VCP -- successively
smaller pullbacks, found from the base's swing points -- which its own detector does (core/vcp_spec.py).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

WINDOW = 10   # sessions per reading: twice the strategy's TIGHT_MIN_DAYS, the shortest tight area it accepts
VOL_AVG = 50  # the volume baseline's length, the strategy's 50-day average


def rules() -> dict:
    """The strategy constants the readings are judged by (read on each call, so a change shows at once)."""
    from ..strategies import minervini_spec as mv
    return {"TIGHT_PCT": mv.TIGHT_PCT, "DRYUP_RATIO": mv.DRYUP_RATIO, "PIVOT_NEAR_HIGH": mv.PIVOT_NEAR_HIGH,
            "VOL_MULT": mv.VOL_MULT, "BASE_MAX_DAYS": mv.BASE_MAX_DAYS, "TIGHT_MIN_DAYS": mv.TIGHT_MIN_DAYS}


def reading(h: np.ndarray, l: np.ndarray, v: np.ndarray, i: int, window: int, r: dict) -> dict | None:
    """The readings on bar `i` of the high/low/volume arrays, or None with too little history."""
    w = max(int(window), int(r["TIGHT_MIN_DAYS"]))
    if i < w + VOL_AVG - 1 or i >= len(h):
        return None
    a = i - w + 1
    hi, lo = float(h[a:i + 1].max()), float(l[a:i + 1].min())
    # the 50-day baseline from the bar BEFORE the window, as the strategy takes it (core/vcp_spec._dryup):
    # the window's own quiet days must not drag down the average they are judged against
    base = float(v[a - VOL_AVG:a].mean())
    top = float(h[max(0, i - int(r["BASE_MAX_DAYS"]) + 1):i + 1].max())
    if not (hi > 0 and base > 0 and top > 0):
        return None
    out = {"hi": hi, "lo": lo, "tight": (hi - lo) / hi * 100, "dry": float(v[a:i + 1].mean()) / base, "near": hi / top}
    out["coiled"] = out["tight"] <= r["TIGHT_PCT"] and out["dry"] <= r["DRYUP_RATIO"] and out["near"] >= r["PIVOT_NEAR_HIGH"]
    return out


def breakout(h, l, c, v, i: int, window: int, r: dict) -> dict | None:
    """The coil a breakout on bar `i` came out of (its readings on bar i-1), or None if bar `i` is no breakout:
    bar i-1 coiled, bar i closed above its window high on at least VOL_MULT x the 50-day volume."""
    prev = reading(h, l, v, i - 1, window, r)
    if not prev or not prev["coiled"] or i < VOL_AVG - 1:
        return None
    v50 = float(v[i - VOL_AVG + 1:i + 1].mean())
    if not (c[i] > prev["hi"] and v50 > 0 and v[i] >= r["VOL_MULT"] * v50):
        return None
    return {**prev, "vol_ratio": float(v[i]) / v50}


def gauge(d: pd.DataFrame, window: int = WINDOW) -> pd.DataFrame:
    """Every bar's readings for daily bars `d` (high/low/close/volume, oldest first), for the chart."""
    r = rules()
    h, l, c, v = (d[k].to_numpy(float) for k in ("high", "low", "close", "volume"))
    rows = []
    for i in range(len(d)):
        x = reading(h, l, v, i, window, r)
        rows.append((x["tight"], x["dry"], x["near"], x["coiled"]) if x else (np.nan, np.nan, np.nan, False))
    out = pd.DataFrame(rows, index=d.index, columns=["tight", "dry", "near", "coiled"])
    out["breakout"] = [breakout(h, l, c, v, i, window, r) is not None for i in range(len(d))]
    return out
