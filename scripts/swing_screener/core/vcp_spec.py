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

The base-period trend rule (VCP-03) asks whether the long trend survived the base, not whether the
averages stayed perfectly stacked: the 200-day no lower than at the base start, the 150-day above
the 200-day today, and at most `max_closes_below_200` closes below the 200-day across the base.
The full Trend Template is NOT required at the base start -- it is recorded as `base_tt` -- because
Minervini applies it when he buys, and it is still a hard gate on the signal day.

The tight area IS the final contraction -- its own swing high (the pivot) to day t, at least
`tight_min_days` long with no maximum -- and its volume baseline is taken from the bar BEFORE it so
the quiet days do not lower their own benchmark.

Where the pivot sits in the base decides the setup (VCP-09): at or above `upper_zone` of the base
range, or within `pivot_near_high` of the base high, is the standard pivot buy; lower than that is
a cheat entry, which has its own shelf and its own stop.

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
    # How decisively a close must clear the base high before the base counts as
    # resolved. The spec (line 86) ends a base on ANY close above BH, which makes
    # a base impossible to hold in the stocks this strategy targets: a leader
    # making new highs resets the base, and VCP-02 then wants 15 more sessions
    # from the new swing high. 88% of VCP-02's rejections are "no base" or "base
    # too young", and the detector finds 0 bases in NVDA, CELH, SMCI, BAJFINANCE
    # and TRENT across 13 years. A base's ceiling is a zone, not a line -- the
    # same reasoning as chart_pattern.overhead_cluster_atr and the overhead cap
    # in minervini_spec -- so a marginal poke leaves the base intact and only a
    # decisive close resolves it. 0 reproduces the spec exactly.
    bh_break_atr: float = 1.0        # ATRs above BH a close must clear  [assumption]
    # The "cheat" entries. Minervini describes three entry points inside a base --
    # the low cheat (lower third), the cheat or "3C" (middle third) and the pivot
    # buy at the top -- and this spec only ever implemented the last. A cheat is a
    # short shelf with a pivot of its own, bought before the stock has recovered to
    # its old high, which is why its stop is nearby: the shelf low, not the base
    # low. These are measured on any base that clears VCP-01/02/03, because a cheat
    # is taken while the base is still FORMING -- waiting for the full VCP to
    # complete is the pivot buy, by definition.
    cheat_shelf_days: int = 7        # bars in the shelf  [assumption]
    cheat_shelf_pct: float = 8.0     # shelf high-to-low range, % of the high  [assumption]
    bh_break_pct: float = 2.0        # fallback when ATR is unavailable  [assumption]
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
    # VCP-03, the trend through the base (v2 §2.6). Minervini is strict that the stock stays in
    # Stage 2; he is NOT strict that the averages stay perfectly stacked every day. The previous
    # version required the full Trend Template on the base-start bar AND, on every bar of the
    # base, 150 > 200, a rising 200-day and a close within `base_sma200_floor` of it. That is
    # stricter than the method and made VCP-03 the second-largest rejector (32% of a 562-symbol
    # sample). v2 replaces it with three checks on the base as a whole:
    max_closes_below_200: int = 10   # sessions below the 200-day during the base, at most
    #: The template at the base start is now LOGGED (out["base_tt"]), not required -- Minervini
    #: applies it when he buys, which is the signal day, where it is still a hard gate.
    prior_advance_pct: float = 30.0  # VCP-01: BH this far above the lowest low of the prior 126 bars
    prior_window: int = 126
    base_min_days: int = 15          # VCP-02: about 3 weeks …
    base_max_days: int = 325         # … to 65 weeks
    # ---- the reset rule (v2 §3.3). Volatility must have contracted since the last time it
    # EXPANDED; the base does not need every pullback to be smaller than the one before it.
    #
    # The previous test was `every contraction <= shrink x its predecessor`, which rejects a base
    # for one deeper pullback early on -- the case Minervini describes as the count RESETTING, not
    # the base failing. 15%, 25%, 12%, 6% failed outright; now the 25% is the reference and the
    # 12%, 6% that follow are what the base is judged on.
    widen_tol: float = 1.1           # a contraction > this x the previous one is a WIDENING
    min_from_reference: int = 2      # VCP-06: contractions from the reference onward, inclusive
    final_ref_ratio: float = 0.6     # VCP-06: final contraction / reference contraction, at most
    min_contractions: int = 2        # VCP-04
    #: No longer a rejection: v2 §3.4 logs the count and flags more than this. A base with seven
    #: contractions is unusual, not invalid, and rejecting on it threw away the information.
    max_contractions: int = 6        # flag above this; see out["many_contractions"]
    # VCP-05 is now BASE DEPTH, not the first contraction's depth (v2 §2.5). Most of Minervini's
    # bases correct 10-35%, but deeper ones appear in bear markets and still produce leaders, so
    # 35% is a quality flag and 50% is the limit. The first contraction is no longer capped on its
    # own: §3.4 says the deepest contraction is "covered by base depth".
    max_base_depth_pct: float = 50.0    # VCP-05: (base high - base low) / base high
    deep_base_flag_pct: float = 35.0    # recorded as out["deep_base"], never a rejection
    higher_lows: bool = False        # VCP-07 (optional)
    tight_min_days: int = 5          # VCP-08: the final contraction must be at least this old
    upper_zone: float = 2 / 3        # VCP-09: pivot position in the base that counts as "upper"
    tight_pct: float = 10.0          # VCP-08: its range, and the final contraction, at most this deep
    pivot_near_high: float = 0.90    # VCP-09: pivot ≥ this × BH
    dryup_quiet_days: int = 2        # VCP-10, the alternative: this many very quiet sessions …
    dryup_quiet_ratio: float = 0.5   # … each at or under this x the 50-day average
    dryup_ratio: float = 0.80        # VCP-10: tight-area volume ≤ this × its 50-day average
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


# template_miss's answer when the averages are not computable yet (a young listing): callers can tell
# "too new to judge" from a trend that failed
NO_HISTORY = "not enough history for the averages"


def template_miss(row) -> str | None:
    """TT-01 … TT-07 on one enriched row (TT-08, RS, is applied cross-sectionally by the backtest): the
    first check that fails, in words, or None when the template holds."""
    try:
        c, s50, s150, s200 = float(row["close"]), float(row["sma50"]), float(row["sma150"]), float(row["sma200"])
        s200p, lo, hi = float(row["sma200_21d_ago"]), float(row["low_252"]), float(row["high_252"])
    except (KeyError, TypeError, ValueError):
        return NO_HISTORY
    if any(v != v for v in (c, s50, s150, s200, s200p, lo, hi)):
        return NO_HISTORY
    for ok, what in ((c > s150 and c > s200, "close under the 150- or 200-day"),
                     (s150 > s200, "150-day under the 200-day"),
                     (s200 > s200p, "200-day not rising over a month"),
                     (s50 > s150 and s50 > s200, "50-day under the 150- or 200-day"),
                     (c > s50, "close under the 50-day"),
                     (c >= 1.30 * lo, "close less than 30% above the 52-week low"),
                     (c >= 0.75 * hi, "close more than 25% under the 52-week high")):
        if not ok:
            return what
    return None


def _template_ok(row) -> bool:
    """TT-01 … TT-07 on one enriched row (see `template_miss`)."""
    return template_miss(row) is None


def detect(daily: pd.DataFrame, p: VcpParams = VcpParams()) -> dict:
    """The base in force on the last bar of `daily`, and whether its VCP is complete.

    Returns {"ok", "fail" (first failing rule id, or None), "bh", "bh_date", "base_days", "prior_advance_pct",
    "depths", "lows", "pivot", "tight_low", "tight_range_pct", "dryup", "base_tt"}, plus where things are, for
    drawing only: "prior_low"/"prior_low_date" (the low VCP-01 measures the advance from), "legs" (each
    contraction as (high date, high, low date, low)) and "tight_from" (the tight area's first bar)."""
    out = {"ok": False, "fail": None, "bh": None, "bh_date": None, "base_days": None, "prior_advance_pct": None,
           "depths": [], "lows": [], "pivot": None, "tight_low": None, "tight_range_pct": None, "dryup": None, "base_tt": None, "zigzag_pct_used": None,
           "base_low": None, "cheat_ok": False, "cheat_pivot": None, "cheat_low": None,
           "cheat_range_pct": None, "cheat_pos": None, "cheat_zone": None,
           "pivot_pos": None, "pivot_zone": None, "tight_days_actual": None,
           "base_closes_below_200": None, "fail_why": None, "base_depth_pct": None,
           "deep_base": None, "dryup_quiet_days": None,
           "prior_low": None, "prior_low_date": None, "legs": [], "tight_from": None}
    d = daily.iloc[-p.lookback:]
    n = len(d)
    if n < 2 * p.swing_k + p.base_min_days + 5:
        out["fail"] = "VCP-02"
        return out
    high, low, close = d["high"].to_numpy(float), d["low"].to_numpy(float), d["close"].to_numpy(float)
    is_hi = _swings(d["high"], p.swing_k, "max")

    # ---- step 1: the base high in force on day t
    #
    # VCP-02 (v2 §2.2): the base high is the HIGHEST confirmed swing high that no close has
    # decisively exceeded since it formed -- the left-side high -- not the first such high.
    #
    # The previous version assigned `bh_i` only while it was None, so it held the FIRST
    # unexceeded swing high and could never upgrade to a higher one that formed later without a
    # decisive close in between. Measured over 20 in-window bases it agreed with the highest on
    # 14 and missed on 6, every miss being a later, HIGHER swing high that the `bh_break_atr`
    # margin had kept from resolving the base. Those 6 started the base at a lower high, which
    # moves the pivot, the depth and the prior advance with it.
    #
    # (It was never the "most recent" high, which is the failure mode the v2 note describes:
    # chosen == latest on 1 of 20, and that base had a single candidate.)
    #
    # Unexceeded is judged on a CLOSE, with the same decisiveness margin as before: an intraday
    # poke above the base high does not end the base, only a close clearing it by more than
    # `bh_break_atr` ATRs (or `bh_break_pct`, when ATR is unavailable).
    atr = d["atr14"].to_numpy(float) if "atr14" in d.columns else np.full(n, np.nan)
    t = n - 1
    bh_i = None
    for j in range(n):
        # A swing high is only usable once confirmed, `swing_k` bars after it forms.
        if not is_hi[j] or j + p.swing_k > t:
            continue
        if bh_i is not None and high[j] <= high[bh_i]:
            continue                      # cannot raise the base high; nothing to check
        hj = high[j]
        later = close[j + 1:]
        if len(later):
            marg = np.where(np.isnan(atr[j + 1:]), hj * p.bh_break_pct / 100,
                            p.bh_break_atr * atr[j + 1:])
            if bool(np.any(later > hj + marg)):
                continue                  # a close resolved it: this high no longer caps a base
        bh_i = j
    if bh_i is None:
        out["fail"] = "VCP-02"
        return out
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
    if len(prior):
        k = int(prior.argmin())
        out["prior_low"], out["prior_low_date"] = float(prior[k]), d.index[max(0, bh_i - p.prior_window) + k]
    if not (adv >= p.prior_advance_pct):
        out["fail"] = "VCP-01"
        return out
    # VCP-03 (v2 §2.6): the base-start template is recorded, never required; what must hold is
    # that the long trend did not break while the base formed.
    # Needed by VCP-05 (base depth) and VCP-09 (pivot position), so it is computed once here.
    base_low = float(low[bh_i:].min())
    out["base_low"] = base_low
    out["base_tt"] = _template_ok(d.iloc[bh_i])
    base = d.iloc[bh_i:]
    try:
        s200_now, s200_then = float(base["sma200"].iloc[-1]), float(base["sma200"].iloc[0])
        s150_now = float(base["sma150"].iloc[-1])
        below = int((base["close"] < base["sma200"]).sum())
    except (KeyError, IndexError, ValueError):
        out["fail"] = "VCP-03"
        out["fail_why"] = "not enough moving-average history across the base"
        return out
    out["base_closes_below_200"] = below
    if not (s200_now >= s200_then):
        out["fail"] = "VCP-03"
        out["fail_why"] = "the 200-day is lower now than when the base started"
        return out
    if not (s150_now > s200_now):
        out["fail"] = "VCP-03"
        out["fail_why"] = "the 150-day is not above the 200-day"
        return out
    if below > p.max_closes_below_200:
        out["fail"] = "VCP-03"
        out["fail_why"] = (f"{below} closes below the 200-day inside the base, "
                           f"more than {p.max_closes_below_200}")
        return out

    # ---- the cheat shelf, recorded for ANY legitimate base (VCP-01/02/03), whether
    # or not the contraction gates below ever pass. Where the shelf sits in the base
    # is what separates a low cheat from a cheat from the pivot buy.
    span = high[bh_i] - base_low
    sh = d.iloc[-p.cheat_shelf_days:]
    sh_hi, sh_lo = float(sh["high"].max()), float(sh["low"].min())
    sh_rng = (sh_hi - sh_lo) / sh_hi * 100 if sh_hi > 0 else float("nan")
    out["cheat_pivot"], out["cheat_low"], out["cheat_range_pct"] = sh_hi, sh_lo, sh_rng
    pos = (sh_hi - base_low) / span if span > 0 else float("nan")
    out["cheat_pos"] = pos
    out["cheat_zone"] = (None if pos != pos else
                         "low" if pos < 1 / 3 else "mid" if pos < 2 / 3 else "high")
    # a shelf must be tight, and must sit BELOW the base high -- at or above it the
    # stock has recovered its old high and the entry is the pivot buy, not a cheat
    out["cheat_ok"] = bool(sh_rng == sh_rng and sh_rng <= p.cheat_shelf_pct
                           and sh_hi < high[bh_i] and len(sh) >= p.cheat_shelf_days)

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
            legs.append((h, l, (h - l) / h * 100 if h > 0 else float("nan"), a[0], b[0]))
            last_low_i = b[0]
    # the final, still-open leg: from the last confirmed high to the lowest low since
    if piv[-1][2] == "H":
        seg = low[piv[-1][0]:]
        if len(seg):
            h, l = piv[-1][1], float(seg.min())
            legs.append((h, l, (h - l) / h * 100 if h > 0 else float("nan"), piv[-1][0], piv[-1][0] + int(seg.argmin())))
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
    out["legs"] = [(d.index[g[3]], g[0], d.index[g[4]], g[1]) for g in legs]
    if len(legs) < p.min_contractions:
        out["fail"] = "VCP-04"
        return out
    out["many_contractions"] = len(legs) > p.max_contractions
    # VCP-05: the depth of the BASE, measured from its high to its lowest low since.
    base_depth = (high[bh_i] - base_low) / high[bh_i] * 100 if high[bh_i] > 0 else float("nan")
    out["base_depth_pct"] = base_depth
    out["deep_base"] = bool(base_depth == base_depth and base_depth > p.deep_base_flag_pct)
    if base_depth == base_depth and base_depth > p.max_base_depth_pct:
        out["fail"] = "VCP-05"
        out["fail_why"] = (f"the base is {base_depth:.1f}% deep, more than "
                           f"{p.max_base_depth_pct:g}%")
        return out

    # ---- VCP-06, the reset rule (v2 §3.3-3.4)
    #
    # The REFERENCE is the most recent widening -- a contraction more than `widen_tol` times the
    # one before it. With none, it is the first contraction from the base high. Everything before
    # the reference is ignored for this test (it still counts toward base depth), because a
    # deeper pullback resets the count rather than invalidating the base.
    sizes = [g[2] for g in legs]
    ref = 0
    for k in range(1, len(sizes)):
        if sizes[k - 1] > 0 and sizes[k] > p.widen_tol * sizes[k - 1]:
            ref = k
    out["reference_i"], out["reference_pct"] = ref, sizes[ref]
    out["from_reference"] = len(sizes) - ref
    out["final_ref_ratio"] = (sizes[-1] / sizes[ref]) if sizes[ref] > 0 else float("nan")
    # A widening with nothing after it is not a failure, it is a base that is NOT READY: the
    # stock has just widened out and has not tightened again yet. It fails the same gate, and
    # the reason says which of the two it is.
    if out["from_reference"] < p.min_from_reference:
        out["fail"] = "VCP-06"
        out["fail_why"] = ("widened out and has not contracted again yet"
                           if ref == len(sizes) - 1 else "too few contractions since the last widening")
        return out
    if not (out["final_ref_ratio"] <= p.final_ref_ratio):
        out["fail"] = "VCP-06"
        out["fail_why"] = (f"final contraction {sizes[-1]:.1f}% is "
                           f"{out['final_ref_ratio']:.2f}x the reference {sizes[ref]:.1f}% "
                           f"(needs <= {p.final_ref_ratio})")
        return out
    if p.higher_lows and any(b[1] < a[1] for a, b in zip(legs, legs[1:])):
        out["fail"] = "VCP-07"
        return out

    # ---- step 3: the final tight area and volume
    # The tight area is the FINAL CONTRACTION itself (v2 §4.1): from its own swing high -- which
    # is the pivot -- to the current bar. It replaces a window fixed at `tight_days`, which could
    # only ever be right by coincidence: a final contraction of 6 sessions had four sessions of
    # the previous decline dragged into its range, and one of 20 had two thirds of itself cut off.
    # There is no maximum any more; the length is recorded instead.
    ta_start = legs[-1][3]
    ta = d.iloc[ta_start:]
    out["tight_from"], out["tight_days_actual"] = d.index[ta_start], n - ta_start
    pivot, tl = float(legs[-1][0]), float(legs[-1][1])
    rng = (pivot - tl) / pivot * 100 if pivot > 0 else float("nan")
    out.update(pivot=pivot, tight_low=tl, tight_range_pct=rng)
    if n - ta_start < p.tight_min_days:
        out["fail"] = "VCP-08"
        out["fail_why"] = (f"the final contraction is only {n - ta_start} session(s) old, "
                           f"under the {p.tight_min_days} a tight area needs")
        return out
    if not (legs[-1][2] <= p.tight_pct and rng <= p.tight_pct):
        out["fail"] = "VCP-08"
        return out

    # VCP-09 (v2 §4.3): where the pivot sits INSIDE the base decides which setup applies, so the
    # gate for the standard pivot buy is "upper zone", not "within 10% of the base high". The old
    # test rejected an entire named base shape: a double bottom's pivot is the middle peak, which
    # in a 30%-deep base sits about 15% below the base high and so never cleared 0.9 x BH. The
    # "or" keeps every base the old rule accepted.
    span = high[bh_i] - base_low
    pos = (pivot - base_low) / span if span > 0 else float("nan")
    out["pivot_pos"] = pos
    out["pivot_zone"] = (None if pos != pos else
                         "low" if pos < 1 / 3 else "mid" if pos < p.upper_zone else "high")
    if not (pos >= p.upper_zone or pivot >= p.pivot_near_high * high[bh_i]):
        out["fail"] = "VCP-09"
        out["fail_why"] = (f"the pivot sits {pos:.2f} of the way up the base "
                           f"({pos * 100:.0f}%), below the upper zone at {p.upper_zone:g} — "
                           f"a {out['pivot_zone']}-zone pivot is a cheat entry, not a pivot buy")
        return out
    # Baseline from the bar BEFORE the tight area: the last bar's 50-day average already
    # includes the quiet tight-area days, which drags it down and makes the dry-up test
    # easier to pass than intended.
    v_i = max(0, ta_start - 1)
    v50 = float(d["vol_sma50"].iloc[v_i]) if "vol_sma50" in d else float("nan")
    dry = float(ta["volume"].mean()) / v50 if v50 and v50 == v50 else float("nan")
    quiet = int((ta["volume"] <= p.dryup_quiet_ratio * v50).sum()) if v50 and v50 == v50 else 0
    out["dryup"], out["dryup_quiet_days"] = dry, quiet
    # Two ways to pass (v2 §4.4): the tight area's AVERAGE volume is down, or it contains enough
    # of the very quiet days Minervini points to. One average can be lifted past the threshold by
    # a single news day inside an otherwise silent contraction, which is the case the second test
    # is there to keep.
    if not (dry <= p.dryup_ratio or quiet >= p.dryup_quiet_days):
        out["fail"] = "VCP-10"
        out["fail_why"] = (f"volume averaged {dry:.2f}x its 50-day (needs <= {p.dryup_ratio:g}) "
                           f"with {quiet} session(s) at or under {p.dryup_quiet_ratio:g}x "
                           f"(needs {p.dryup_quiet_days})")
        return out
    if p.atr_shrink and "atr14" in d:
        a_now, a_bh = float(d["atr14"].iloc[-1]) / close[-1], float(d["atr14"].iloc[bh_i]) / close[bh_i]
        if not (a_now <= p.atr_shrink * a_bh):
            out["fail"] = "VCP-11"
            return out
    out["ok"] = True
    return out


# --------------------------------------------------------------------- power play (MV-05)
#
# The standard base rules cannot see a power play, and that is not a tuning problem: the flag is
# shorter than `base_min_days`, the run before it is far steeper than a normal prior advance, and
# the moving averages have not caught up, so VCP-02 and VCP-03 reject it before any contraction is
# measured. Minervini treats it as a special case (v2 "MV-05"), so it is detected separately and
# never competes with the base path.
#
# What makes it a power play rather than a stock that merely went up: the RUN is measured to the
# flag high, not to today, so a stock that doubled and then kept running does not qualify on a
# flag that never formed; and the flag must be a real pause -- short, shallow, and ending in a
# tight area like any other pivot.

@dataclass(frozen=True)
class PowerPlayParams:
    run_window: int = 40          # sessions the run is measured over …
    run_mult: float = 2.0         # … during which price at least doubled, at the flag high
    flag_min_days: int = 10       # the pause, about 2 …
    flag_max_days: int = 30       # … to 6 weeks
    flag_max_depth_pct: float = 25.0   # how far the flag may fall from the flag high
    tight_pct: float = 10.0       # the final tight area, as elsewhere
    tight_min_days: int = 5
    swing_k: int = 5


def detect_power_play(d: pd.DataFrame, p: "PowerPlayParams | None" = None) -> dict:
    """The explosive run and the tight flag that follows it, judged on day t.

    Returns the same shape as `detect`: `fail` is None when the setup is complete, and every
    measured value is recorded whether it passed or not.
    """
    p = p or PowerPlayParams()
    out = {"fail": None, "fail_why": None, "run_pct": None, "flag_high": None, "flag_high_date": None,
           "flag_days": None, "flag_depth_pct": None, "pivot": None, "tight_low": None,
           "tight_range_pct": None}
    need = p.run_window + p.flag_max_days + p.swing_k + 2
    if len(d) < need:
        out["fail"] = "PP-00"
        out["fail_why"] = f"needs {need} sessions of history"
        return out
    high, low, close = (d[k].to_numpy(float) for k in ("high", "low", "close"))
    n = len(d)
    t = n - 1
    is_hi = _swings(d["high"], p.swing_k, "max")

    # The flag high is the most recent CONFIRMED swing high that leaves a flag of a usable length.
    cand = [j for j in range(n - p.flag_min_days - 1, max(0, n - p.flag_max_days - 1) - 1, -1)
            if 0 <= j < n and is_hi[j] and j + p.swing_k <= t]
    if not cand:
        out["fail"] = "PP-01"
        out["fail_why"] = "no confirmed swing high leaving a flag of 10-30 sessions"
        return out
    fh_i = max(cand, key=lambda j: high[j])
    out["flag_high"], out["flag_high_date"] = float(high[fh_i]), d.index[fh_i]
    out["flag_days"] = t - fh_i

    # The RUN, measured AT the flag high: price there against the lowest low of the window before.
    lo_window = low[max(0, fh_i - p.run_window):fh_i]
    if not len(lo_window) or lo_window.min() <= 0:
        out["fail"] = "PP-02"
        out["fail_why"] = "no usable low before the flag high"
        return out
    run = float(high[fh_i] / lo_window.min())
    out["run_pct"] = (run - 1) * 100
    if run < p.run_mult:
        out["fail"] = "PP-02"
        out["fail_why"] = (f"the run into the flag was {(run - 1) * 100:.0f}%, under the "
                           f"{(p.run_mult - 1) * 100:.0f}% a power play needs")
        return out

    flag_low = float(low[fh_i:].min())
    depth = (high[fh_i] - flag_low) / high[fh_i] * 100
    out["flag_depth_pct"] = depth
    if depth > p.flag_max_depth_pct:
        out["fail"] = "PP-03"
        out["fail_why"] = f"the flag fell {depth:.1f}%, more than {p.flag_max_depth_pct:g}%"
        return out

    # A close above the flag high means the pause is over and this is no longer a setup.
    if float(close[fh_i + 1:].max() if fh_i + 1 <= t else -1) > high[fh_i]:
        out["fail"] = "PP-04"
        out["fail_why"] = "price already closed above the flag high"
        return out

    # The tight area: the last confirmed swing high inside the flag, or the flag high itself.
    inner = [j for j in range(fh_i + 1, t + 1) if is_hi[j] and j + p.swing_k <= t]
    ta_i = max(inner, key=lambda j: high[j]) if inner else fh_i
    ta_i = min(ta_i, t - p.tight_min_days) if t - ta_i < p.tight_min_days else ta_i
    pivot = float(high[ta_i:].max())
    tl = float(low[ta_i:].min())
    rng = (pivot - tl) / pivot * 100 if pivot > 0 else float("nan")
    out.update(pivot=pivot, tight_low=tl, tight_range_pct=rng)
    if not (rng <= p.tight_pct):
        out["fail"] = "PP-05"
        out["fail_why"] = f"the flag's tight area spans {rng:.1f}%, more than {p.tight_pct:g}%"
        return out
    return out
