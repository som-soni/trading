"""Base and volatility-contraction detection as specified in research/minervini-backtest-spec.md, §5.

`detect(daily, p)` looks at an enriched daily frame ending on the bar being judged (day t) — never later
bars — and returns the base and whether its volatility contraction is complete (VCP-01 … VCP-10), with
the first rule that fails. Every number is a field of `VcpParams` (the spec's §11 parameters).
VCP-03 covers both halves of the spec's base-period trend rule: the full template (TT-01 … TT-07)
on BH's bar, and TT-01 … TT-04 on every bar from BH to day t.

Swing points (§3): a bar is a swing high if its high is the highest of the k bars before and the k bars
after it. A swing at bar i is therefore only known at the close of bar i + k; the rolling window used
here needs all k later bars, so the newest k bars of the frame can never be swing points — no
look-ahead. Contractions shallower than `min_swing_pct` are wiggles and are dropped (the last, open
contraction is kept: the tightness rules judge it instead).

Base high (BH): walking forward, a confirmed swing high starts a base; a later CLOSE above it discards
that base, and the next confirmed swing high starts a new one. BH is the high of the base in force on
day t. Contraction i runs from swing high H_i (H_1 = BH) to the lowest low before the next swing high
(the last one runs to day t): depth d_i = (H_i - L_i) / H_i.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class VcpParams:
    swing_k: int = 5                 # swing points: k bars each side  [assumption]
    min_swing_pct: float = 2.0       # contractions shallower than this are wiggles  [assumption]
    prior_advance_pct: float = 30.0  # VCP-01: BH this far above the lowest low of the prior 126 bars
    prior_window: int = 126
    base_min_days: int = 15          # VCP-02: about 3 weeks …
    base_max_days: int = 325         # … to 65 weeks
    min_contractions: int = 2        # VCP-04
    max_contractions: int = 6
    max_first_depth_pct: float = 35.0   # VCP-05
    shrink: float = 0.80             # VCP-06: each contraction ≤ shrink × the previous
    higher_lows: bool = False        # VCP-07 (optional)
    tight_days: int = 10             # VCP-08: the final tight area
    tight_pct: float = 10.0          # VCP-08: its range, and the final contraction, at most this deep
    pivot_near_high: float = 0.90    # VCP-09: pivot ≥ this × BH
    dryup_ratio: float = 0.70        # VCP-10: tight-area volume ≤ this × its 50-day average
    atr_shrink: float = 0.0          # VCP-11 (optional, 0 = off): ATR/close now ≤ this × ATR/close on BH's bar
    lookback: int = 460              # bars examined (base max + prior window + swing confirmation)


def _swings(series: pd.Series, k: int, how: str) -> np.ndarray:
    roll = series.rolling(2 * k + 1, center=True, min_periods=2 * k + 1)
    ext = roll.max() if how == "max" else roll.min()
    return (series == ext).to_numpy()


def _template_ok(row) -> bool:
    """TT-01 … TT-07 on one enriched row (TT-08, RS, is applied cross-sectionally by the backtest)."""
    try:
        c, s50, s150, s200 = float(row["close"]), float(row["sma50"]), float(row["sma150"]), float(row["sma200"])
        s200p, lo, hi = float(row["sma200_21d_ago"]), float(row["low_252"]), float(row["high_252"])
    except (KeyError, TypeError, ValueError):
        return False
    if any(v != v for v in (c, s50, s150, s200, s200p, lo, hi)):
        return False
    return (c > s150 and c > s200 and s150 > s200 and s200 > s200p and s50 > s150 and s50 > s200 and c > s50
            and c >= 1.30 * lo and c >= 0.75 * hi)


def _trend_held(d: pd.DataFrame) -> bool:
    """TT-01 … TT-04 on every bar of the base (TT-05 may lapse in an early, deep contraction)."""
    try:
        c, s50, s150, s200, s200p = (d[k] for k in ("close", "sma50", "sma150", "sma200", "sma200_21d_ago"))
    except KeyError:
        return False
    ok = (c > s150) & (c > s200) & (s150 > s200) & (s200 > s200p) & (s50 > s150) & (s50 > s200)
    return bool(ok.all())


def detect(daily: pd.DataFrame, p: VcpParams = VcpParams()) -> dict:
    """The base in force on the last bar of `daily`, and whether its VCP is complete.

    Returns {"ok", "fail" (first failing rule id, or None), "bh", "bh_date", "base_days", "prior_advance_pct",
    "depths", "lows", "pivot", "tight_low", "tight_range_pct", "dryup", "base_tt"}."""
    out = {"ok": False, "fail": None, "bh": None, "bh_date": None, "base_days": None, "prior_advance_pct": None,
           "depths": [], "lows": [], "pivot": None, "tight_low": None, "tight_range_pct": None, "dryup": None, "base_tt": None}
    d = daily.iloc[-p.lookback:]
    n = len(d)
    if n < 2 * p.swing_k + p.base_min_days + 5:
        out["fail"] = "VCP-02"
        return out
    high, low, close = d["high"].to_numpy(float), d["low"].to_numpy(float), d["close"].to_numpy(float)
    is_hi = _swings(d["high"], p.swing_k, "max")

    # ---- step 1: the base high in force on day t
    bh_i = None
    for j in range(n):
        if bh_i is not None and close[j] > high[bh_i]:
            bh_i = None                                   # a close above BH: that base is gone
        if bh_i is None and is_hi[j]:
            bh_i = j
    if bh_i is None:
        out["fail"] = "VCP-02"
        return out
    t = n - 1
    out.update(bh=float(high[bh_i]), bh_date=d.index[bh_i], base_days=t - bh_i)
    if not (p.base_min_days <= t - bh_i <= p.base_max_days):
        out["fail"] = "VCP-02"
        return out
    prior = low[max(0, bh_i - p.prior_window): bh_i]
    adv = (high[bh_i] / prior.min() - 1) * 100 if len(prior) and prior.min() > 0 else float("nan")
    out["prior_advance_pct"] = adv
    if not (adv >= p.prior_advance_pct):
        out["fail"] = "VCP-01"
        return out
    out["base_tt"] = _template_ok(d.iloc[bh_i])
    if not out["base_tt"] or not _trend_held(d.iloc[bh_i:]):
        out["fail"] = "VCP-03"
        return out

    # ---- step 2: the contractions
    his = [bh_i] + [j for j in range(bh_i + 1, n) if is_hi[j]]
    legs = []
    for a, b in zip(his, his[1:] + [n]):
        seg = low[a + 1: b] if b > a + 1 else low[a: a + 1]
        if not len(seg):
            continue
        h, l = high[a], float(seg.min())
        legs.append((h, l, (h - l) / h * 100 if h > 0 else float("nan")))
    # wiggles out, but keep the last (open) contraction — the tightness rules judge it
    legs = [g for k, g in enumerate(legs) if g[2] >= p.min_swing_pct or k == len(legs) - 1]
    out["depths"] = [round(g[2], 2) for g in legs]
    out["lows"] = [g[1] for g in legs]
    if not (p.min_contractions <= len(legs) <= p.max_contractions):
        out["fail"] = "VCP-04"
        return out
    if legs[0][2] > p.max_first_depth_pct:
        out["fail"] = "VCP-05"
        return out
    if any(b[2] > p.shrink * a[2] for a, b in zip(legs, legs[1:])):
        out["fail"] = "VCP-06"
        return out
    if p.higher_lows and any(b[1] < a[1] for a, b in zip(legs, legs[1:])):
        out["fail"] = "VCP-07"
        return out

    # ---- step 3: the final tight area and volume
    ta = d.iloc[-p.tight_days:]
    pivot, tl = float(ta["high"].max()), float(ta["low"].min())
    rng = (pivot - tl) / pivot * 100 if pivot > 0 else float("nan")
    out.update(pivot=pivot, tight_low=tl, tight_range_pct=rng)
    if not (legs[-1][2] <= p.tight_pct and rng <= p.tight_pct):
        out["fail"] = "VCP-08"
        return out
    if pivot < p.pivot_near_high * high[bh_i]:
        out["fail"] = "VCP-09"
        return out
    v50 = float(d["vol_sma50"].iloc[-1]) if "vol_sma50" in d else float("nan")
    dry = float(ta["volume"].mean()) / v50 if v50 and v50 == v50 else float("nan")
    out["dryup"] = dry
    if not (dry <= p.dryup_ratio):
        out["fail"] = "VCP-10"
        return out
    if p.atr_shrink and "atr14" in d:
        a_now, a_bh = float(d["atr14"].iloc[-1]) / close[-1], float(d["atr14"].iloc[bh_i]) / close[bh_i]
        if not (a_now <= p.atr_shrink * a_bh):
            out["fail"] = "VCP-11"
            return out
    out["ok"] = True
    return out
