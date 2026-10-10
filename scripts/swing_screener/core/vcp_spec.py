"""Base and volatility-contraction detection as specified in research/minervini-backtest-spec.md, §5.

`detect(daily, p)` looks at an enriched daily frame ending on the bar being judged (day t) — never later
bars — and returns the base and whether its volatility contraction is complete (VCP-01 … VCP-10), with
the first rule that fails. Every number is a field of `VcpParams` (the spec's §11 parameters).
VCP-03 covers both halves of the spec's base-period trend rule: the full template (TT-01 … TT-07)
on BH's bar, and TT-01 … TT-04 on every bar from BH to day t.

Swing points (§3) locate the BASE HIGH only: a bar is a swing high if its high is the highest of the
k bars before and the k bars after it, so a swing at bar i is known only at the close of bar i + k and
the newest k bars can never be swing points — no look-ahead.

Contractions are NOT segmented by those swings. They come from a zig-zag (`_zigzag`) that requires a
real reversal in both directions, because a two-day bounce used to start a new leg and split one
pullback into two. Its threshold starts at `max(zigzag_pct, zigzag_atr_mult x ATR%)` and then shrinks
to `zigzag_shrink_ratio` x the depth just measured — a VCP's late contractions are far smaller than
its first, and one fixed threshold cannot see both — never falling below a floor of
`max(zigzag_floor_pct, zigzag_floor_atr_mult x ATR%)`, since a reversal smaller than an ATR is
indistinguishable from a single bar.

The base-period trend rule checks the moving-average STRUCTURE every day plus a close above
`base_sma200_floor` x SMA200; requiring close > SMA150 daily contradicted VCP-05, which permits a
first contraction of up to 35%. The full template still applies on BH's bar and on the signal day.

The tight area runs from the last confirmed zig-zag low to day t, capped at `tight_days`, and its
volume baseline is taken from the bar BEFORE it so the quiet days do not lower their own benchmark.

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
    zigzag_atr_mult: float = 1.5     # the zig-zag threshold is at least this many ATRs. A FIXED
                                     # percentage cannot work across stocks: MU's median ATR is
                                     # 3.79% of close, so a 3% threshold sits below one day's
                                     # normal range and turns daily noise into legs -- it found a
                                     # median of 12 contractions in MU's bases where VCP-04 allows
                                     # 6. A floor of one ATR is the minimum that can distinguish a
                                     # reversal from a single bar; 1.5 leaves headroom.
                                     # NOT YET VALIDATED UNIVERSE-WIDE.  [assumption]
    zigzag_shrink_ratio: float = 0.35  # after each contraction the threshold drops to this
                                     # fraction of the depth just measured. ONE threshold for
                                     # the whole base cannot see a VCP: it has to be wide
                                     # enough for the first contraction (20%+) and is then far
                                     # too wide for the 3-5% ones that define the pattern, so
                                     # the later legs never confirm and VCP-04 rejects a
                                     # textbook base for having too few.  [assumption]
    zigzag_floor_pct: float = 1.5    # …but never below this, or noise becomes legs again
    zigzag_floor_atr_mult: float = 1.5    # …or this many ATRs, whichever is larger. The SAME
                                     # volatility floor the initial threshold respects: a
                                     # "reversal" smaller than one ATR is indistinguishable
                                     # from a single bar wherever it occurs in the base. At the
                                     # 0.75 first suggested (2.84% on MU, under its 3.79% ATR)
                                     # the shrinking threshold put the median leg count at 13
                                     # against VCP-04's limit of 6; at 1.5 it is back to 6.
    zigzag_pct: float = 3.0          # a leg turns only after a reversal this large, in BOTH
                                     # directions. Segmenting on swing highs alone split one
                                     # pullback into two whenever a 2-3 day bounce made a new
                                     # swing high: 100 -> 92 -> 94 -> 80 read as 8% then 15%,
                                     # so the "second" leg was deeper and VCP-06 rejected a
                                     # genuine 20% contraction.  [assumption]
    base_sma200_floor: float = 0.97  # VCP-03 during the base: the close may dip this far below
                                     # the 200-day. Requiring close > SMA150 every day
                                     # contradicted VCP-05, which permits a first contraction of
                                     # up to 35% -- a 25-35% pullback routinely breaks the
                                     # 150-day in a healthy Stage 2 name.  [assumption]
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


def _zigzag(high: np.ndarray, low: np.ndarray, first_pct: float,
            floor_pct: float, ratio: float) -> list[tuple[int, float, str]]:
    """Alternating (index, price, 'H'/'L') pivots, starting from a KNOWN high at bar 0,
    with a reversal threshold that shrinks as the contractions do.

    Two things this gets right that a fixed threshold does not:

    * **The threshold tracks the pattern.** A VCP contracts 20%, then 8%, then 3%. One
      threshold wide enough to confirm the first is far too wide for the last, so the
      small late contractions never produce a pivot and the base looks like a single
      long leg. After each confirmed low the next threshold becomes `ratio` x the depth
      just measured, floored so noise cannot creep back in.
    * **It starts on the right foot.** Beginning with direction unset and both
      candidates on bar 0 let a wide BH bar confirm an 'L' first, which was then
      discarded — and the next 'H' was a later, LOWER bar, so the first contraction was
      measured from the wrong place and VCP-05/VCP-06 saw the wrong depth. BH is known,
      so it is seeded as the first high and the search starts looking for a low.

    Uses only bars up to the one being judged: a pivot is appended when the reversal
    confirms it, never retroactively from later data.
    """
    if not len(high):
        return []
    piv: list[tuple[int, float, str]] = [(0, float(high[0]), "H")]
    hi_i = lo_i = 0
    direction, thr = -1, first_pct
    for j in range(1, len(high)):
        if direction > 0 and high[j] >= high[hi_i]:
            hi_i = j
        if direction < 0 and low[j] <= low[lo_i]:
            lo_i = j
        if direction > 0 and low[j] <= high[hi_i] * (1 - thr / 100):
            piv.append((hi_i, float(high[hi_i]), "H"))
            direction, lo_i = -1, j
        elif direction < 0 and high[j] >= low[lo_i] * (1 + thr / 100):
            piv.append((lo_i, float(low[lo_i]), "L"))
            prev_high = piv[-2][1]
            depth = (prev_high - low[lo_i]) / prev_high * 100 if prev_high > 0 else 0.0
            direction, hi_i = 1, j
            thr = max(floor_pct, ratio * depth)
    return piv


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


def _trend_held(d: pd.DataFrame, floor: float = 0.97) -> bool:
    """The long-term structure must hold through the base — not the full template.

    Requiring the close above the 150-day on EVERY bar contradicted VCP-05, which allows a
    first contraction of up to 35%: a pullback that deep routinely takes price under the
    150-day for weeks in a perfectly healthy Stage 2 stock, so the two rules together
    rejected most of the deeper bases Minervini accepts. What has to hold daily is the
    moving-average structure; the full template is still checked on BH's bar and on the
    signal day.
    """
    try:
        c, s150, s200, s200p = (d[k] for k in ("close", "sma150", "sma200", "sma200_21d_ago"))
    except KeyError:
        return False
    ok = (s150 > s200) & (s200 > s200p) & (c > floor * s200)
    return bool(ok.all())


def detect(daily: pd.DataFrame, p: VcpParams = VcpParams()) -> dict:
    """The base in force on the last bar of `daily`, and whether its VCP is complete.

    Returns {"ok", "fail" (first failing rule id, or None), "bh", "bh_date", "base_days", "prior_advance_pct",
    "depths", "lows", "pivot", "tight_low", "tight_range_pct", "dryup", "base_tt"}."""
    out = {"ok": False, "fail": None, "bh": None, "bh_date": None, "base_days": None, "prior_advance_pct": None,
           "depths": [], "lows": [], "pivot": None, "tight_low": None, "tight_range_pct": None, "dryup": None, "base_tt": None, "zigzag_pct_used": None}
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
    if len(prior) < p.prior_window:
        out["fail"] = "VCP-01"          # not enough history to judge the prior advance
        return out
    adv = (high[bh_i] / prior.min() - 1) * 100 if len(prior) and prior.min() > 0 else float("nan")
    out["prior_advance_pct"] = adv
    if not (adv >= p.prior_advance_pct):
        out["fail"] = "VCP-01"
        return out
    out["base_tt"] = _template_ok(d.iloc[bh_i])
    if not out["base_tt"] or not _trend_held(d.iloc[bh_i:], p.base_sma200_floor):
        out["fail"] = "VCP-03"
        return out

    # ---- step 2: the contractions, segmented by zig-zag
    # A leg turns only after a `zigzag_pct` reversal in BOTH directions. Segmenting on swing
    # highs alone made every 2-3 day bounce start a new contraction, which split one real
    # pullback into two and left the "second" deeper than the "first" -- so VCP-06 rejected
    # bases that had contracted perfectly well.
    # scale the reversal threshold to the stock: a fixed percentage is noise on a volatile
    # name and a wall on a quiet one
    zz = p.zigzag_pct
    atr_pct = float("nan")
    if "atr14" in d and close[bh_i]:
        atr_pct = float(d["atr14"].iloc[bh_i]) / float(close[bh_i]) * 100
    if p.zigzag_atr_mult and atr_pct == atr_pct:
        zz = max(zz, p.zigzag_atr_mult * atr_pct)
    floor = p.zigzag_floor_pct
    if p.zigzag_floor_atr_mult and atr_pct == atr_pct:
        floor = max(floor, p.zigzag_floor_atr_mult * atr_pct)
    out["zigzag_pct_used"] = round(zz, 2)
    # seeded with BH as the first high, so no leading-L cleanup is needed
    piv = [(i + bh_i, v, k) for i, v, k in
           _zigzag(high[bh_i:], low[bh_i:], zz, floor, p.zigzag_shrink_ratio)]

    legs, last_low_i = [], None
    for a, b in zip(piv, piv[1:]):
        if a[2] == "H" and b[2] == "L":
            h, l = a[1], b[1]
            legs.append((h, l, (h - l) / h * 100 if h > 0 else float("nan")))
            last_low_i = b[0]
    # the final, still-open leg: from the last confirmed high to the lowest low since
    if piv[-1][2] == "H":
        seg = low[piv[-1][0]:]
        if len(seg):
            h, l = piv[-1][1], float(seg.min())
            legs.append((h, l, (h - l) / h * 100 if h > 0 else float("nan")))
    if not legs:
        out["fail"] = "VCP-04"
        return out
    # the zig-zag already requires a real move in both directions, so a surviving leg is not
    # a wiggle; the filter stays only for thresholds set above zigzag_pct
    # No wiggle filter: the zig-zag's reversal threshold already decided what counts as a
    # leg, and a second fixed cut could only delete legs it had judged real — which was
    # how the first contraction sometimes stopped starting at BH, so VCP-05 measured the
    # wrong one. `min_swing_pct` is kept only for callers that want a stricter floor.
    if p.min_swing_pct > p.zigzag_floor_pct:
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
    # The tight area is the bars since the last confirmed zig-zag low, capped at
    # `tight_days`. A fixed 10-bar window pulled part of the previous decline in whenever
    # the final contraction was shorter than that, failing the range check on a stock that
    # had in fact tightened.
    ta_start = n - p.tight_days
    if last_low_i is not None:
        ta_start = max(ta_start, min(last_low_i, n - 3))
    ta = d.iloc[ta_start:]
    pivot, tl = float(ta["high"].max()), float(ta["low"].min())
    rng = (pivot - tl) / pivot * 100 if pivot > 0 else float("nan")
    out.update(pivot=pivot, tight_low=tl, tight_range_pct=rng)
    if not (legs[-1][2] <= p.tight_pct and rng <= p.tight_pct):
        out["fail"] = "VCP-08"
        return out
    if pivot < p.pivot_near_high * high[bh_i]:
        out["fail"] = "VCP-09"
        return out
    # Baseline from the bar BEFORE the tight area: the last bar's 50-day average already
    # includes the quiet tight-area days, which drags it down and makes the dry-up test
    # easier to pass than intended.
    v_i = max(0, ta_start - 1)
    v50 = float(d["vol_sma50"].iloc[v_i]) if "vol_sma50" in d else float("nan")
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
