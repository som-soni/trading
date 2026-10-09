"""Shared pattern machinery (§2, §3) and the cup with handle (§4), as specified
in research/chart-pattern-spec.md.

This module is written to that spec the way `vcp_spec.py` is written to the
Minervini one: every check carries the spec's rule id, every number is a field
of `PatternParams` (the spec's §12), and a detection reports the FIRST rule it
failed, so "why is there no cup here" is answerable without a debugger.

It does not replace `chart_patterns.py`. That module predates the spec and
differs in method — no fitted trendlines, fixed rather than ATR-scaled
tolerances, no prior-trend context, no pattern state. The two will coexist
until the spec version covers enough patterns to retire it; nothing imports
this one yet.

Point-in-time
-------------
`daily` ends on the bar being judged (day t) and nothing reads past it. Two
consequences the spec calls out as its top pitfalls (§13):

  * a swing at bar i is only known at the close of bar i + k, so the newest k
    bars can never be swing points;
  * the trigger T is frozen from day t-1. If the breakout bar's own high could
    raise the level it is breaking, every pattern breaks out by construction.

Levels that define a STOP may use day t's low: it is known at the close.

Two things found while building it
----------------------------------
**CH-09's lower bound is unreachable.** C has to be a confirmed major swing
high, and at k_major = 8 that takes 8 bars to confirm, so the handle is never
shorter than 8 days — CH-09 allows 5. Handles of 5 to 7 days cannot be
detected at the major scale no matter what the rule says. Either C should be
found at the minor scale (k = 3, matching "handles" in §2.1's own list of
minor-scale patterns), or CH-09's floor should be k_major. Left as the spec
has it, and flagged here, rather than quietly resolved.

**Five rules cannot fire at the default parameters**, all for the same
reason: §2.1's 3% minimum swing size and §2.2's 3% tolerance are large
relative to the thresholds later sections set, so a chart that would break
those rules loses the swings that make it detectable first.

| rule | wants | blocked by |
|---|---|---|
| CH-09 | a handle as short as 5 days | k_major = 8 needs 8 bars to confirm C |
| HS-06 | a shoulder within 3% of the neckline | the 3% minimum swing puts it further |
| TR-04 | a duration limit | every anchor is tried, so a long triangle yields a short sub-window that passes |
| TR-07 | an initial height of 6% | 3% swings plus TR-02's five touches force it higher |
| FL-04 | two fitted lines in a 5-20 bar pause | a pause shallow enough for FL-02 oscillates under 3% |

None is a coding error and none is quietly worked around: each is tested by
moving the blocking parameter, so the rule is proven wired, and the defaults
are left as the spec wrote them. Lowering `min_swing_pct` to ~1.5% would make
HS-06, TR-07 and FL-04 live; CH-09 and TR-04 need the spec itself changed.

**HS-06 is unreachable at the default parameters.** It wants a shoulder
within 3% of the neckline, but §2.1's minimum swing size already forces the
dip from a shoulder to its neighbouring neckline point to be at least 3%, and
HS-05 caps how far the extended line can travel to close that gap (0.3% per
day). The rule can only bite if `min_swing_pct` is lowered or `hs_min_shoulder`
raised. Same family of problem as CH-09 below: two §2 defaults quietly
determine whether a §6 rule can ever fire.

**"The FIRST major swing high after B satisfying CH-03" needs §11's tracker.**
Read literally on a single day t, it anchors the handle at whatever lip came
first: GILD's first qualifying lip is 16 months old, so its handle measured
334 days and every cup on the chart failed CH-09. Evaluating one bar at a
time, `_cup_from` tries every qualifying lip in time order and keeps the
first that completes. With the §11 tracker that loop would not exist.

What is NOT here
----------------
§11's cross-day scanner — the tracked-instance store, keyed by (stock, type,
anchor date), that lets a pattern persist as `forming` for weeks. `advance()`
below implements every state transition in §3.1 over a frame, which is enough
to compute §3.3 outcomes in a backtest, but the detectors are still called
fresh per bar rather than updated in place.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

# ------------------------------------------------------------------ §12

@dataclass(frozen=True)
class PatternParams:
    """Every tunable number in the spec, §12. Defaults are the spec's."""

    # §2.1 swing points
    k_minor: int = 3
    k_major: int = 8
    min_swing_pct: float = 3.0
    atr_mult: float = 1.5
    # §2.2 price tolerance
    tol_pct: float = 3.0
    tol_atr_mult: float = 0.75
    # §2.3 trendlines (TL-05)
    flat_slope: float = 0.0005            # fraction per day
    # §2.4 prior trend (PT-01, PT-02)
    prior_move: float = 20.0
    prior_window: int = 120
    # §3.2 breakout
    bo_buffer: float = 0.005              # BO-01
    bo_vol: float = 1.4                   # BO-02
    max_wait: int = 20                    # BO-04
    fail_days: int = 10                   # BO-05
    horizon: int = 60                     # §3.3
    # §4 cup with handle
    cup_prior_move: float = 30.0          # CH-01 (O'Neil)
    cup_depth: tuple[float, float] = (12.0, 33.0)   # CH-02 (O'Neil)
    right_lip: tuple[float, float] = (0.85, 1.03)   # CH-03
    cup_days: tuple[int, int] = (35, 325)           # CH-04 (O'Neil)
    round_frac: float = 0.15              # CH-05
    round_min_days: int = 5               # CH-05
    side_frac: float = 0.25               # CH-06
    handle_half: float = 0.5              # CH-07 (O'Neil)
    handle_depth: tuple[float, float] = (3.0, 12.0)  # CH-08 (O'Neil)
    handle_days: tuple[int, int] = (5, 25)           # CH-09 (O'Neil)
    handle_vol: float = 0.8               # CH-11
    # §5 double and triple bottoms / tops
    db_prior_move: float = 20.0           # DB-01, DT-01
    db_min_peak: float = 10.0             # DB-03, DT-03
    # DB-03/DT-03 have NO upper bound in the spec, so a spike between two
    # lows qualifies as a W: AEVA screened as a live double bottom with lows
    # at 13.51 and 13.90 either side of a 28.42 peak — a middle swing 110%
    # above the bottoms. 0 keeps the spec's behaviour; set it to test a cap.
    db_max_peak: float = 0.0              # not in the spec
    db_days: tuple[int, int] = (20, 150)  # DB-04, DT-04
    db_second_volume: bool = False        # DB-05, off by default
    oneil_undercut: tuple[float, float] = (0.0, 5.0)  # O'Neil's W variant
    # §6 head and shoulders
    hs_prior_move: float = 20.0           # HS-01
    hs_min_head: float = 3.0              # HS-02
    hs_shoulder_tol_mult: float = 2.0     # HS-03
    hs_time_ratio: tuple[float, float] = (0.5, 2.0)   # HS-04
    hs_max_neck_slope: float = 0.003      # HS-05, fraction per day
    hs_min_shoulder: float = 3.0          # HS-06
    hs_days: tuple[int, int] = (20, 250)  # HS-07
    hs_volume: bool = False               # HS-08, off by default
    # §7 triangles (shared with §10 wedges)
    tr_scale_days: int = 40               # TR-01: minor swings under this, major over
    tr_min_touches_side: int = 2          # TR-02
    tr_min_touches: int = 5               # TR-02
    tr_days: tuple[int, int] = (15, 200)  # TR-04
    tr_apex_zone: tuple[float, float] = (0.50, 0.80)  # TR-05
    tr_volume: bool = True                # TR-06, required by the spec
    tr_min_height: float = 6.0            # TR-07, % of price
    sym_slope_ratio: float = 2.0          # §7.2 symmetrical: slopes within 2x
    # §8.1 rectangle
    rc_min_touches_side: int = 2          # RC-02
    rc_min_touches: int = 4               # RC-02
    rc_height: tuple[float, float] = (5.0, 25.0)      # RC-03
    rc_days: tuple[int, int] = (20, 250)  # RC-04
    # §8.2 flat base
    fb_prior_move: float = 20.0           # FB-01 (O'Neil)
    fb_max_depth: float = 15.0            # FB-02 (O'Neil)
    fb_days: tuple[int, int] = (25, 120)  # FB-03, and the window search range
    fb_near_high: float = 0.95            # FB-04
    fb_volume: bool = False               # FB-05, off by default
    # §9 flags and pennants
    pole_gain: float = 15.0               # FP-01
    pole_days: int = 15                   # FP-02
    pole_rv: float = 1.3                  # FP-03
    flag_days: tuple[int, int] = (5, 20)  # FL-01
    flag_retrace: float = 50.0            # FL-02
    flag_slope_ratio: float = 2.0         # FL-04, roughly parallel
    htf_gain: float = 100.0               # HTF-01 (O'Neil)
    htf_pole_days: tuple[int, int] = (20, 40)   # HTF-02
    htf_depth: float = 25.0               # HTF-03
    htf_flag_days: tuple[int, int] = (15, 25)   # HTF-04
    lookback: int = 520                   # bars examined: cup max + prior window + k


# ------------------------------------------------------- §2.1 swing points

@dataclass(frozen=True)
class Swing:
    pos: int
    kind: str      # "H" or "L"
    price: float


def _fractals(series: pd.Series, k: int, how: str) -> np.ndarray:
    """Confirmed only: the centred window needs k later bars, so the newest k
    bars are never swing points (§13 pitfall 1)."""
    roll = series.rolling(2 * k + 1, center=True, min_periods=2 * k + 1)
    ext = roll.max() if how == "max" else roll.min()
    return (series == ext).to_numpy()


def _alternate(points: list[Swing], high: np.ndarray, low: np.ndarray) -> list[Swing]:
    """§2.1 rule 1: keep the higher of two consecutive highs, the lower of two
    consecutive lows."""
    out: list[Swing] = []
    for s in points:
        if out and out[-1].kind == s.kind:
            keep = s.price > out[-1].price if s.kind == "H" else s.price < out[-1].price
            if keep:
                out[-1] = s
            continue
        out.append(s)
    return out


def swings(daily: pd.DataFrame, k: int, p: PatternParams = PatternParams()) -> list[Swing]:
    """Confirmed swing points at scale `k`, alternating and de-wiggled (§2.1).

    The minimum-size filter and the alternation rule interact: dropping a
    wiggle can leave two highs adjacent, which then have to be merged, which
    can expose another wiggle. Both run to a fixed point rather than once.
    """
    high = daily["high"].to_numpy(float)
    low = daily["low"].to_numpy(float)
    close = daily["close"].to_numpy(float)
    atr = (daily["atr14"].to_numpy(float) if "atr14" in daily
           else np.full(len(daily), np.nan))

    is_h, is_l = _fractals(daily["high"], k, "max"), _fractals(daily["low"], k, "min")
    pts = [Swing(i, "H", float(high[i])) for i in range(len(daily)) if is_h[i]]
    pts += [Swing(i, "L", float(low[i])) for i in range(len(daily)) if is_l[i]]
    pts.sort(key=lambda s: (s.pos, s.kind))

    def min_move(i: int) -> float:
        """max(min_swing_pct, atr_mult x ATR14/close) at the swing's own bar."""
        base = p.min_swing_pct / 100
        a = atr[i] if i < len(atr) else np.nan
        c = close[i] if i < len(close) else np.nan
        if a == a and c == c and c:
            return max(base, p.atr_mult * a / c)
        return base

    cur = _alternate(pts, high, low)
    while True:
        kept = [cur[0]] if cur else []
        for s in cur[1:]:
            prev = kept[-1]
            move = abs(s.price - prev.price) / prev.price if prev.price else 0.0
            if move < min_move(s.pos):
                continue  # a wiggle, not a swing
            kept.append(s)
        merged = _alternate(kept, high, low)
        if len(merged) == len(cur) and all(a.pos == b.pos for a, b in zip(merged, cur)):
            return merged
        cur = merged


# --------------------------------------------------- §2.2 price tolerance

def tol(close: float, atr14: float, p: PatternParams = PatternParams()) -> float:
    """max(tol_pct, tol_atr_mult x ATR14/close), as a fraction."""
    base = p.tol_pct / 100
    if atr14 == atr14 and close:
        return max(base, p.tol_atr_mult * atr14 / close)
    return base


def about_equal(p1: float, p2: float, t: float) -> bool:
    """§2.2: |p1 - p2| / mean(p1, p2) <= tol."""
    mid = (p1 + p2) / 2
    return bool(mid and abs(p1 - p2) / mid <= t)


# ------------------------------------------------------- §2.3 trendlines

@dataclass(frozen=True)
class Line:
    slope: float      # price per bar
    intercept: float  # price at x = 0

    def at(self, x: float) -> float:
        return self.slope * x + self.intercept

    def pct_slope(self, mid_x: float) -> float:
        """TL-04: slope as a fraction per day, against the line's value at the
        pattern's midpoint."""
        mid = self.at(mid_x)
        return self.slope / mid if mid else float("nan")

    def is_flat(self, mid_x: float, p: PatternParams = PatternParams()) -> bool:
        """TL-05."""
        s = self.pct_slope(mid_x)
        return bool(s == s and abs(s) <= p.flat_slope)


def fit_line(points: list[tuple[int, float]]) -> Line | None:
    """TL-01: least squares through at least two points."""
    if len(points) < 2:
        return None
    x = np.array([q[0] for q in points], dtype=float)
    y = np.array([q[1] for q in points], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return Line(float(slope), float(intercept))


def touches(line: Line, points: list[Swing], t: float) -> int:
    """TL-02: swing points within `t` of the line."""
    n = 0
    for s in points:
        v = line.at(s.pos)
        if v and abs(s.price - v) / v <= t:
            n += 1
    return n


def contained(
    upper: Line, lower: Line, close: np.ndarray, lo: int, hi: int, t: float
) -> bool:
    """TL-03: no close beyond either line by more than `t`, before the
    breakout."""
    for i in range(lo, hi + 1):
        u, d = upper.at(i), lower.at(i)
        if u and close[i] > u * (1 + t):
            return False
        if d and close[i] < d * (1 - t):
            return False
    return True


# ------------------------------------------------------ §2.4 prior trend

def prior_uptrend(
    low: np.ndarray, a_pos: int, a_price: float, p: PatternParams, move: float | None = None
) -> tuple[bool, float]:
    """PT-01. Returns (passed, the advance actually measured, in %)."""
    seg = low[max(0, a_pos - p.prior_window): a_pos]
    if seg.size == 0 or seg.min() <= 0:
        return False, float("nan")
    adv = (a_price / float(seg.min()) - 1) * 100
    return adv >= (p.prior_move if move is None else move), adv


def prior_downtrend(
    high: np.ndarray, a_pos: int, a_price: float, p: PatternParams, move: float | None = None
) -> tuple[bool, float]:
    """PT-02. Returns (passed, the decline actually measured, in %)."""
    seg = high[max(0, a_pos - p.prior_window): a_pos]
    if seg.size == 0 or seg.max() <= 0 or a_price <= 0:
        return False, float("nan")
    dec = (1 - a_price / float(seg.max())) * 100
    return dec >= (p.prior_move if move is None else move), dec


# ---------------------------------------------------------- §2.5 volume

def vol50(volume: np.ndarray, start_pos: int) -> float:
    """The 50-day average volume measured on the day BEFORE the pattern
    starts, so the pattern's own volume cannot move its own baseline."""
    seg = volume[max(0, start_pos - 50): start_pos]
    return float(seg.mean()) if seg.size else float("nan")


def rv(volume: np.ndarray, t_pos: int, v50: float) -> float:
    """Relative volume, RV(t) = volume(t) / VOL50."""
    return float(volume[t_pos]) / v50 if v50 and v50 == v50 else float("nan")


def log_volume_slope(volume: np.ndarray, lo: int, hi: int) -> float:
    """"Volume declines through the pattern" = this is negative."""
    seg = volume[lo: hi + 1]
    seg = seg[seg > 0]
    if seg.size < 3:
        return float("nan")
    x = np.arange(seg.size, dtype=float)
    return float(np.polyfit(x, np.log(seg), 1)[0])


# ------------------------------------------------------------ §3 states

FORMING, COMPLETE, CONFIRMED, FAILED, VOID = (
    "forming", "complete", "confirmed", "failed", "void")

BULLISH, BEARISH = "bullish", "bearish"


@dataclass(frozen=True)
class Levels:
    """§3: the trigger, the invalidation level and the height."""

    trigger: float
    invalidation: float
    height: float
    direction: str = BULLISH

    @property
    def target(self) -> float:
        """BO-06: bullish T + H, bearish T - H."""
        return (self.trigger + self.height if self.direction == BULLISH
                else self.trigger - self.height)


def broke_out(close_t: float, rv_t: float, lv: Levels, p: PatternParams) -> bool:
    """BO-01 and BO-02. The volume rule is bullish-only: the spec switches it
    off for bearish breakouts, which often happen without a surge."""
    if lv.direction == BULLISH:
        if not close_t > lv.trigger * (1 + p.bo_buffer):
            return False
        return bool(rv_t == rv_t and rv_t >= p.bo_vol)
    return bool(close_t < lv.trigger * (1 - p.bo_buffer))


def voided(close_t: float, lv: Levels) -> bool:
    """BO-03: a close beyond X."""
    return bool(close_t < lv.invalidation if lv.direction == BULLISH
                else close_t > lv.invalidation)


def expired(bars_since_complete: int, p: PatternParams) -> bool:
    """BO-04."""
    return bars_since_complete > p.max_wait


def broke_back(close: np.ndarray, bo_pos: int, t_pos: int, lv: Levels,
               t: float, p: PatternParams) -> bool:
    """BO-05: within fail_days of the breakout, a close back through T by more
    than tol."""
    if t_pos - bo_pos > p.fail_days:
        return False
    c = float(close[t_pos])
    return bool(c < lv.trigger * (1 - t) if lv.direction == BULLISH
                else c > lv.trigger * (1 + t))


@dataclass
class Outcome:
    """§3.3, measured over `horizon` bars after the breakout."""

    hit_target: bool = False
    hit_day: int | None = None
    mfe: float = float("nan")
    mae: float = float("nan")
    throwback: bool = False
    failed: bool = False
    ret_5: float = float("nan")
    ret_20: float = float("nan")
    ret_60: float = float("nan")


def outcomes(daily: pd.DataFrame, bo_pos: int, lv: Levels,
             p: PatternParams = PatternParams(), t: float = 0.03) -> Outcome:
    """Record §3.3 for a confirmed breakout at `bo_pos`.

    Partial windows are reported, not padded: a breakout 20 bars from the end
    of the data gets ret_5 and ret_20 and leaves ret_60 as NaN, so a truncated
    sample never masquerades as a flat one.
    """
    close = daily["close"].to_numpy(float)
    high, low = daily["high"].to_numpy(float), daily["low"].to_numpy(float)
    n = len(daily)
    entry = float(close[bo_pos])
    end = min(n - 1, bo_pos + p.horizon)
    out = Outcome()
    if bo_pos >= n - 1 or entry <= 0:
        return out

    fwd_h, fwd_l = high[bo_pos + 1: end + 1], low[bo_pos + 1: end + 1]
    if fwd_h.size:
        bull = lv.direction == BULLISH
        out.mfe = (float(fwd_h.max()) / entry - 1) * 100 if bull else (1 - float(fwd_l.min()) / entry) * 100
        out.mae = (float(fwd_l.min()) / entry - 1) * 100 if bull else (1 - float(fwd_h.max()) / entry) * 100
        reached = (fwd_h >= lv.target) if bull else (fwd_l <= lv.target)
        if reached.any():
            out.hit_target = True
            out.hit_day = int(np.argmax(reached)) + 1
        back = (fwd_l <= lv.trigger * (1 + t)) if bull else (fwd_h >= lv.trigger * (1 - t))
        out.throwback = bool(back.any())
        fail_end = min(end, bo_pos + p.fail_days)
        for i in range(bo_pos + 1, fail_end + 1):
            if broke_back(close, bo_pos, i, lv, t, p):
                out.failed = True
                break
    for days, attr in ((5, "ret_5"), (20, "ret_20"), (60, "ret_60")):
        j = bo_pos + days
        if j <= n - 1:
            setattr(out, attr, (float(close[j]) / entry - 1) * 100)
    return out


# ----------------------------------------------- §4 cup with handle

# evaluated in this order, so "first failing rule" means the earliest one
CUP_RULES = ("CH-01", "CH-02", "CH-03", "CH-04", "CH-05", "CH-06",
             "CH-07", "CH-08", "CH-09", "CH-10", "CH-11")


def _blank_cup() -> dict:
    return {"ok": False, "fail": None, "points": {}, "levels": None,
            "metrics": {}, "state": None, "breakout_pos": None}


def detect_cups(daily: pd.DataFrame, p: PatternParams = PatternParams(),
                *, require_handle: bool = True) -> list[dict]:
    """Every cup anchored at a distinct left lip A, as of the last bar (§4).

    The spec tracks one instance per anchor date (§11), so this returns a list
    rather than picking a winner. `detect_cup` wraps it for callers that want
    one.
    """
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n = len(d)
    if n < p.cup_days[0] + 2 * p.k_major + 5:
        return []
    high, low, close = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    volume = d["volume"].to_numpy(float)
    atr_t = float(d["atr14"].iloc[-1]) if "atr14" in d else float("nan")
    t_pos = n - 1
    t_hi = t_pos - 1          # §13 pitfall 2: the trigger is frozen at t-1
    majors = swings(d, p.k_major, p)

    found: list[dict] = []
    for a in (s for s in majors if s.kind == "H"):
        res = _cup_from(a, d, majors, high, low, close, volume, atr_t, t_pos, t_hi, p,
                        require_handle=require_handle)
        if res is not None:
            found.append(res)
    return found


def _cup_from(a: Swing, d: pd.DataFrame, majors: list[Swing], high, low, close,
              volume, atr_t, t_pos: int, t_hi: int, p: PatternParams, *,
              require_handle: bool) -> dict | None:
    """One anchor: CH-01 to CH-02 once, then every qualifying right lip.

    The spec says C is "the FIRST major swing high after B that satisfies
    CH-03", which is unambiguous for §11's forward tracker — the instance is
    born when that lip prints and its handle grows day by day until CH-09
    expires it. Evaluating a single day t retrospectively, taking the first
    lip anchors the handle at whatever lip happened to come first: GILD's
    first qualifying lip is 16 months old, so the "handle" measured 334 days
    and every cup on the chart failed CH-09.

    So every qualifying lip is tried, in time order, and the first that
    completes wins. With §11's tracker this loop would not exist.
    """
    out = _blank_cup()
    idx = d.index
    A = a.price
    out["points"]["A"] = {"pos": a.pos, "price": A, "date": idx[a.pos]}
    if A <= 0 or a.pos >= t_hi:
        return None

    # CH-01: prior uptrend into A
    ok, adv = prior_uptrend(low, a.pos, A, p, move=p.cup_prior_move)
    out["metrics"]["prior_advance_pct"] = adv
    if not ok:
        out["fail"] = "CH-01"
        return out

    # B: the lowest low between A and C. C is not known yet, so take the
    # lowest low since A; if a lower low turns up after C, CH-07 rejects it.
    seg = low[a.pos + 1: t_pos + 1]
    if seg.size < 2:
        return None
    b_pos = a.pos + 1 + int(np.argmin(seg))
    B = float(low[b_pos])
    out["points"]["B"] = {"pos": b_pos, "price": B, "date": idx[b_pos]}

    # CH-02: cup depth
    depth = (A - B) / A * 100
    out["metrics"]["depth_pct"] = depth
    if not (p.cup_depth[0] <= depth <= p.cup_depth[1]):
        out["fail"] = "CH-02"
        return out

    # CH-03: right lips near the left lip
    lo_lip, hi_lip = p.right_lip[0] * A, p.right_lip[1] * A
    lips = [s for s in majors if s.kind == "H" and b_pos < s.pos <= t_hi
            and lo_lip <= s.price <= hi_lip]
    if not lips:
        out["fail"] = "CH-03"
        return out

    attempts = []
    for c_swing in lips:
        r = _cup_with_lip(out, c_swing, d, high, low, close, volume, atr_t,
                          a, b_pos, B, t_pos, t_hi, p, require_handle=require_handle)
        if r["ok"]:
            return r
        attempts.append(r)
    return max(attempts, key=lambda r: CUP_RULES.index(r["fail"])
               if r["fail"] in CUP_RULES else -1)


def _cup_with_lip(base: dict, c_swing: Swing, d: pd.DataFrame, high, low, close,
                  volume, atr_t, a: Swing, b_pos: int, B: float, t_pos: int,
                  t_hi: int, p: PatternParams, *, require_handle: bool) -> dict:
    """CH-04 to CH-11 for one (A, B, C)."""
    out = {"ok": False, "fail": None, "points": dict(base["points"]),
           "levels": None, "metrics": dict(base["metrics"]),
           "state": None, "breakout_pos": None}
    idx = d.index
    A = a.price
    c_pos, C = c_swing.pos, c_swing.price
    out["points"]["C"] = {"pos": c_pos, "price": C, "date": idx[c_pos]}

    # CH-04: cup duration
    cup_len = c_pos - a.pos
    out["metrics"]["cup_days"] = cup_len
    if not (p.cup_days[0] <= cup_len <= p.cup_days[1]):
        out["fail"] = "CH-04"
        return out

    # CH-05: rounded, not a V
    third = B + (max(A, C) - B) / 3
    rounded = int((low[a.pos: c_pos + 1] <= third).sum())
    need = max(p.round_min_days, int(p.round_frac * cup_len))
    out["metrics"]["rounded_days"], out["metrics"]["rounded_needed"] = rounded, need
    if rounded < need:
        out["fail"] = "CH-05"
        return out

    # CH-06: balanced sides
    if (b_pos - a.pos) < p.side_frac * cup_len or (c_pos - b_pos) < p.side_frac * cup_len:
        out["fail"] = "CH-06"
        return out

    H = max(A, C) - B
    if not require_handle:
        # the spec's cup-without-handle variant: drop CH-07..CH-11, T = C
        return _cup_state(out, Levels(trigger=C, invalidation=B, height=H),
                          close, volume, a.pos, t_pos, p)

    # D: the lowest low after C (day t's low counts — it is known at the close)
    hseg = low[c_pos + 1: t_pos + 1]
    if hseg.size == 0:
        out["fail"] = "CH-09"
        return out
    d_pos = c_pos + 1 + int(np.argmin(hseg))
    D = float(low[d_pos])
    out["points"]["D"] = {"pos": d_pos, "price": D, "date": idx[d_pos]}

    # CH-07: handle in the upper half of the cup
    if D < B + p.handle_half * (A - B):
        out["fail"] = "CH-07"
        return out

    # CH-08: handle depth
    hd = (C - D) / C * 100
    out["metrics"]["handle_depth_pct"] = hd
    if not (p.handle_depth[0] <= hd <= p.handle_depth[1]):
        out["fail"] = "CH-08"
        return out

    # CH-09: handle duration
    hlen = t_pos - c_pos
    out["metrics"]["handle_days"] = hlen
    if not (p.handle_days[0] <= hlen <= p.handle_days[1]):
        out["fail"] = "CH-09"
        return out

    # CH-10: the handle drifts down or sideways
    line = fit_line([(i, float(close[i])) for i in range(c_pos + 1, t_pos + 1)])
    slope = line.slope if line else float("nan")
    out["metrics"]["handle_close_slope"] = slope
    if not (slope == slope and slope <= 0):
        out["fail"] = "CH-10"
        return out

    # CH-11: volume dries up in the handle, against VOL50 at the pattern's start
    v50 = vol50(volume, a.pos)
    hvol = float(volume[c_pos + 1: t_pos + 1].mean())
    ratio = hvol / v50 if v50 and v50 == v50 else float("nan")
    out["metrics"]["handle_vol_ratio"] = ratio
    if not (ratio == ratio and ratio <= p.handle_vol):
        out["fail"] = "CH-11"
        return out

    # T is the handle's highest high, frozen at t-1 (§13 pitfall 2)
    T = float(high[c_pos + 1: t_hi + 1].max()) if t_hi > c_pos else C
    out["metrics"]["tol"] = tol(float(close[t_pos]), atr_t, p)
    return _cup_state(out, Levels(trigger=T, invalidation=D, height=H),
                      close, volume, a.pos, t_pos, p)


def _cup_state(out: dict, lv: Levels, close, volume, start_pos: int,
               t_pos: int, p: PatternParams) -> dict:
    """A cup re-completes every bar — D is the lowest low after C *including*
    day t — so BO-04's expiry clock never starts and the only question at t is
    whether today's close broke out. Doubles and head-and-shoulders complete
    once, in the past, and need the full `state_at` walk."""
    out["levels"] = lv
    fired = broke_out(float(close[t_pos]), rv(volume, t_pos, vol50(volume, start_pos)), lv, p)
    out["state"] = CONFIRMED if fired else COMPLETE
    out["breakout_pos"] = t_pos if fired else None
    out["metrics"]["bars_since_breakout"] = 0 if fired else None
    out["metrics"]["is_live"] = True
    out["ok"] = True
    return out


def detect_cup(daily: pd.DataFrame, p: PatternParams = PatternParams(),
               *, require_handle: bool = True) -> dict:
    """One cup: the qualifying one with the highest left lip, else the
    near-miss that got furthest through CH-01..CH-11.

    Where several cups qualify, the highest A wins: the cup is a correction
    from a prior peak, and anchoring anywhere else reports a shallower,
    flattering version of the same chart.
    """
    cands = detect_cups(daily, p, require_handle=require_handle)
    ok = [c for c in cands if c["ok"]]
    if ok:
        return max(ok, key=lambda c: c["points"]["A"]["price"])
    if not cands:
        return _blank_cup()
    return max(cands, key=lambda c: CUP_RULES.index(c["fail"]) if c["fail"] in CUP_RULES else -1)


# --------------------------------------------- §3 state, without §11

def state_at(daily: pd.DataFrame, lv: Levels, completed_pos: int,
             p: PatternParams, t: float) -> tuple[str, int | None]:
    """Walk §3.2 forward from completion to day t.

    §11's tracker would do this incrementally; run over a frame it gives the
    same answer and makes BO-04 usable without a store. That matters more
    than it sounds: without expiry, a detector evaluated on one bar happily
    reports a double bottom whose second low printed three years ago as
    "complete, waiting for a breakout".
    """
    close = daily["close"].to_numpy(float)
    volume = daily["volume"].to_numpy(float)
    v50 = vol50(volume, completed_pos)
    t_pos = len(daily) - 1
    for i in range(completed_pos, t_pos + 1):
        c = float(close[i])
        if voided(c, lv):                                          # BO-03
            return VOID, None
        if broke_out(c, rv(volume, i, v50), lv, p):                # BO-01, BO-02
            for j in range(i + 1, t_pos + 1):                      # BO-05
                if broke_back(close, i, j, lv, t, p):
                    return FAILED, i
            return CONFIRMED, i
        if expired(i - completed_pos, p):                          # BO-04
            return VOID, None
    return COMPLETE, None


def _runs(points: list[Swing], n: int, first: str) -> list[list[Swing]]:
    """Every run of `n` consecutive swings starting with kind `first`.

    The spec's "five consecutive major-scale swing points" is literal: after
    §2.1's alternation and de-wiggling, a head and shoulders IS a consecutive
    H,L,H,L,H and a double bottom a consecutive L,H,L. Walking the filtered
    list is what makes that true — raw fractals would need nested loops and
    would admit shapes with unrelated swings buried inside them.
    """
    out = []
    for i in range(len(points) - n + 1):
        run = points[i: i + n]
        if run[0].kind == first:
            out.append(run)
    return out


def _result(points: dict) -> dict:
    return {"ok": False, "fail": None, "points": points, "levels": None,
            "metrics": {}, "state": None, "breakout_pos": None}


def _finish(out: dict, daily: pd.DataFrame, lv: Levels, last_pos: int,
            k: int, p: PatternParams, t_frac: float) -> dict:
    """Attach levels and the §3 state. A pattern completes when its last key
    point is CONFIRMED, which is k bars after it prints."""
    out["levels"] = lv
    completed = min(last_pos + k, len(daily) - 1)
    out["metrics"]["completed_pos"] = completed
    out["state"], out["breakout_pos"] = state_at(daily, lv, completed, p, t_frac)
    # §11 records outcomes "until the horizon ends", so a confirmed pattern
    # older than that has finished its life: it is history, not a signal. The
    # spec names no terminal state for it, so the age is exposed rather than
    # invented — on 372 US names, 123 of 134 double tops were confirmations
    # from the past, and a screener that ignores this reports all of them.
    t_pos = len(daily) - 1
    out["metrics"]["bars_since_breakout"] = (
        t_pos - out["breakout_pos"] if out["breakout_pos"] is not None else None)
    out["metrics"]["is_live"] = out["state"] == COMPLETE or (
        out["breakout_pos"] is not None and t_pos - out["breakout_pos"] <= p.horizon)
    out["ok"] = out["state"] in (COMPLETE, CONFIRMED)
    if not out["ok"]:
        out["fail"] = "BO-03" if out["state"] == VOID else "BO-05"
    return out


# ------------------------------------- §5 double bottoms and tops

DB_RULES = ("DB-01", "DB-02", "DB-03", "DB-04", "DB-05")
DT_RULES = ("DT-01", "DT-02", "DT-03", "DT-04")


def detect_doubles(daily: pd.DataFrame, p: PatternParams = PatternParams(), *,
                   direction: str = BULLISH, oneil_w: bool = False) -> list[dict]:
    """§5.1 double bottom (W) and §5.2 double top (M).

    `oneil_w` swaps in O'Neil's continuation variant: a prior UPTREND into B
    (PT-01 in place of DB-01) and a second low 0-5% BELOW the first in place
    of DB-02's "about equal", because he reads the undercut as the shakeout
    that makes the base work.
    """
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n = len(d)
    k = p.k_major
    if n < p.db_days[0] + 2 * k + 5:
        return []
    high, low, close = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    volume = d["volume"].to_numpy(float)
    atr_t = float(d["atr14"].iloc[-1]) if "atr14" in d else float("nan")
    t_frac = tol(float(close[-1]), atr_t, p)
    bull = direction == BULLISH
    rules = DB_RULES if bull else DT_RULES
    idx = d.index

    found: list[dict] = []
    for run in _runs(swings(d, k, p), 3, "L" if bull else "H"):
        b, c_pt, dd = run
        B, C, D = b.price, c_pt.price, dd.price
        out = _result({
            "B": {"pos": b.pos, "price": B, "date": idx[b.pos]},
            "C": {"pos": c_pt.pos, "price": C, "date": idx[c_pt.pos]},
            "D": {"pos": dd.pos, "price": D, "date": idx[dd.pos]},
        })

        # DB-01 / DT-01: context
        if bull and not oneil_w:
            ok, moved = prior_downtrend(high, b.pos, B, p, move=p.db_prior_move)
        elif bull:
            # O'Neil's W is a continuation base, so PT-01 is measured into the
            # HIGH BEFORE B — the top of the advance the base is correcting —
            # not into B itself, which is the bottom of it.
            lo_i = max(0, b.pos - p.prior_window)
            window = high[lo_i: b.pos]
            hp = lo_i + int(np.argmax(window)) if window.size else b.pos
            ok, moved = prior_uptrend(low, hp, float(high[hp]), p,
                                      move=p.db_prior_move)
        else:
            ok, moved = prior_uptrend(low, b.pos, B, p, move=p.db_prior_move)
        out["metrics"]["prior_move_pct"] = moved
        if not ok:
            out["fail"] = rules[0]
            found.append(out)
            continue

        # DB-02 / DT-02: the two extremes are level
        if oneil_w:
            under = (B - D) / B * 100 if B else float("nan")
            out["metrics"]["undercut_pct"] = under
            if not (p.oneil_undercut[0] <= under <= p.oneil_undercut[1]):
                out["fail"] = rules[1]
                found.append(out)
                continue
        elif not about_equal(B, D, t_frac):
            out["fail"] = rules[1]
            found.append(out)
            continue

        # DB-03 / DT-03: the middle swing is a real move, not a pause
        if bull:
            extreme = min(B, D)
            size = (C - extreme) / extreme * 100 if extreme else float("nan")
        else:
            extreme = max(B, D)
            size = (extreme - C) / extreme * 100 if extreme else float("nan")
        out["metrics"]["middle_pct"] = size
        if not (size >= p.db_min_peak) or (p.db_max_peak and size > p.db_max_peak):
            out["fail"] = rules[2]
            found.append(out)
            continue

        # DB-04 / DT-04: separation
        span = dd.pos - b.pos
        out["metrics"]["separation_days"] = span
        if not (p.db_days[0] <= span <= p.db_days[1]):
            out["fail"] = rules[3]
            found.append(out)
            continue

        # DB-05: optional lighter volume at the second bottom
        if bull and p.db_second_volume:
            v_b = float(volume[max(0, b.pos - 2): b.pos + 3].mean())
            v_d = float(volume[max(0, dd.pos - 2): dd.pos + 3].mean())
            out["metrics"]["second_vol_ratio"] = v_d / v_b if v_b else float("nan")
            if not (v_b and v_d < v_b):
                out["fail"] = "DB-05"
                found.append(out)
                continue

        lv = (Levels(trigger=C, invalidation=extreme * (1 - t_frac), height=C - extreme)
              if bull else
              Levels(trigger=C, invalidation=extreme * (1 + t_frac),
                     height=extreme - C, direction=BEARISH))
        found.append(_finish(out, d, lv, dd.pos, k, p, t_frac))
    return found


def _pick(cands: list[dict], rules: tuple[str, ...]) -> dict:
    """The most recent complete candidate, else the furthest near-miss.

    Recency, not size: a reversal that completed last week is the one being
    traded, while the biggest one on the chart may have resolved years ago.
    """
    ok = [c for c in cands if c["ok"]]
    if ok:
        return max(ok, key=lambda c: max(q["pos"] for q in c["points"].values()))
    if not cands:
        return _result({})
    return max(cands, key=lambda c: (rules.index(c["fail"]) if c["fail"] in rules else -1,
                                     max(q["pos"] for q in c["points"].values())))


def detect_double_bottom(daily: pd.DataFrame, p: PatternParams = PatternParams(),
                         *, oneil_w: bool = False) -> dict:
    return _pick(detect_doubles(daily, p, direction=BULLISH, oneil_w=oneil_w), DB_RULES)


def detect_double_top(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    return _pick(detect_doubles(daily, p, direction=BEARISH), DT_RULES)


def detect_triples(daily: pd.DataFrame, p: PatternParams = PatternParams(), *,
                   direction: str = BULLISH) -> list[dict]:
    """§5: "the same pattern with a third swing point". All three extremes
    equal within tol; T is the higher of the two middle peaks for a triple
    bottom, the lower of the two middle troughs for a triple top."""
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n, k = len(d), p.k_major
    if n < p.db_days[0] + 2 * k + 5:
        return []
    high, low, close = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    atr_t = float(d["atr14"].iloc[-1]) if "atr14" in d else float("nan")
    t_frac = tol(float(close[-1]), atr_t, p)
    bull = direction == BULLISH
    rules = DB_RULES if bull else DT_RULES
    idx = d.index

    found: list[dict] = []
    for run in _runs(swings(d, k, p), 5, "L" if bull else "H"):
        e1, m1, e2, m2, e3 = run
        out = _result({name: {"pos": s.pos, "price": s.price, "date": idx[s.pos]}
                       for name, s in zip(("B1", "P1", "B2", "P2", "B3"), run)})
        if bull:
            ok, moved = prior_downtrend(high, e1.pos, e1.price, p, move=p.db_prior_move)
        else:
            ok, moved = prior_uptrend(low, e1.pos, e1.price, p, move=p.db_prior_move)
        out["metrics"]["prior_move_pct"] = moved
        if not ok:
            out["fail"] = rules[0]
            found.append(out)
            continue
        extremes = [e1.price, e2.price, e3.price]
        if not all(about_equal(a, b, t_frac) for a in extremes for b in extremes):
            out["fail"] = rules[1]
            found.append(out)
            continue
        extreme = min(extremes) if bull else max(extremes)
        trigger = max(m1.price, m2.price) if bull else min(m1.price, m2.price)
        size = ((trigger - extreme) / extreme * 100 if bull
                else (extreme - trigger) / extreme * 100)
        out["metrics"]["middle_pct"] = size
        if not (size >= p.db_min_peak):
            out["fail"] = rules[2]
            found.append(out)
            continue
        span = e3.pos - e1.pos
        out["metrics"]["separation_days"] = span
        if not (p.db_days[0] <= span <= p.db_days[1] * 2):
            out["fail"] = rules[3]
            found.append(out)
            continue
        lv = (Levels(trigger=trigger, invalidation=extreme * (1 - t_frac),
                     height=trigger - extreme) if bull else
              Levels(trigger=trigger, invalidation=extreme * (1 + t_frac),
                     height=extreme - trigger, direction=BEARISH))
        found.append(_finish(out, d, lv, e3.pos, k, p, t_frac))
    return found


def detect_triple_bottom(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    return _pick(detect_triples(daily, p, direction=BULLISH), DB_RULES)


def detect_triple_top(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    return _pick(detect_triples(daily, p, direction=BEARISH), DT_RULES)


# --------------------------------------------- §6 head and shoulders

HS_RULES = ("HS-01", "HS-02", "HS-03", "HS-04", "HS-05", "HS-06", "HS-07", "HS-08")


def detect_hs(daily: pd.DataFrame, p: PatternParams = PatternParams(), *,
              inverse: bool = False) -> list[dict]:
    """§6.1 head and shoulders top, and §6.2 its inverse.

    Five consecutive major swings. The neckline is the line through N1 and N2
    extended right, so unlike every other pattern here the trigger MOVES: T is
    neck(t), re-evaluated each bar. The value stored on the result is neck at
    day t.
    """
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n, k = len(d), p.k_major
    if n < p.hs_days[0] + 2 * k + 5:
        return []
    high, low, close = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    volume = d["volume"].to_numpy(float)
    atr_t = float(d["atr14"].iloc[-1]) if "atr14" in d else float("nan")
    t_frac = tol(float(close[-1]), atr_t, p)
    t_pos = n - 1
    idx = d.index
    top = not inverse

    found: list[dict] = []
    for run in _runs(swings(d, k, p), 5, "H" if top else "L"):
        ls, n1, hd, n2, rs = run
        out = _result({name: {"pos": s.pos, "price": s.price, "date": idx[s.pos]}
                       for name, s in zip(("LS", "N1", "HD", "N2", "RS"), run)})

        # HS-01: context
        if top:
            ok, moved = prior_uptrend(low, ls.pos, ls.price, p, move=p.hs_prior_move)
        else:
            ok, moved = prior_downtrend(high, ls.pos, ls.price, p, move=p.hs_prior_move)
        out["metrics"]["prior_move_pct"] = moved
        if not ok:
            out["fail"] = "HS-01"
            found.append(out)
            continue

        # HS-02: the head stands clear of both shoulders
        shoulder = max(ls.price, rs.price) if top else min(ls.price, rs.price)
        clear = ((hd.price / shoulder - 1) * 100 if top
                 else (1 - hd.price / shoulder) * 100)
        out["metrics"]["head_clearance_pct"] = clear
        if not (clear >= p.hs_min_head):
            out["fail"] = "HS-02"
            found.append(out)
            continue

        # HS-03: the shoulders are level with each other
        if not about_equal(ls.price, rs.price, p.hs_shoulder_tol_mult * t_frac):
            out["fail"] = "HS-03"
            found.append(out)
            continue

        # HS-04: and similar in time
        left_days, right_days = hd.pos - ls.pos, rs.pos - hd.pos
        ratio = right_days / left_days if left_days else float("nan")
        out["metrics"]["time_ratio"] = ratio
        if not (p.hs_time_ratio[0] <= ratio <= p.hs_time_ratio[1]):
            out["fail"] = "HS-04"
            found.append(out)
            continue

        # HS-05: the neckline is not too steep
        neck = fit_line([(n1.pos, n1.price), (n2.pos, n2.price)])
        if neck is None:
            out["fail"] = "HS-05"
            found.append(out)
            continue
        slope = neck.pct_slope((n1.pos + n2.pos) / 2)
        out["metrics"]["neck_slope"] = slope
        if not (slope == slope and abs(slope) <= p.hs_max_neck_slope):
            out["fail"] = "HS-05"
            found.append(out)
            continue

        # HS-06: the shoulders stand out from the neckline
        gaps = []
        for s in (ls, rs):
            base = neck.at(s.pos)
            gaps.append(((s.price / base - 1) * 100 if top
                         else (1 - s.price / base) * 100) if base else float("nan"))
        out["metrics"]["shoulder_gaps_pct"] = [round(g, 2) for g in gaps]
        if not all(g == g and g >= p.hs_min_shoulder for g in gaps):
            out["fail"] = "HS-06"
            found.append(out)
            continue

        # HS-07: duration
        span = rs.pos - ls.pos
        out["metrics"]["span_days"] = span
        if not (p.hs_days[0] <= span <= p.hs_days[1]):
            out["fail"] = "HS-07"
            found.append(out)
            continue

        # HS-08: optional classic volume
        if p.hs_volume:
            into_head = float(volume[n1.pos: hd.pos + 1].mean())
            into_ls = float(volume[max(0, ls.pos - (hd.pos - n1.pos)): ls.pos + 1].mean())
            out["metrics"]["head_vol_ratio"] = (into_head / into_ls if into_ls
                                                else float("nan"))
            if not (into_ls and into_head < into_ls):
                out["fail"] = "HS-08"
                found.append(out)
                continue

        neck_t = neck.at(t_pos)
        neck_hd = neck.at(hd.pos)
        height = hd.price - neck_hd if top else neck_hd - hd.price
        lv = Levels(trigger=neck_t, invalidation=rs.price, height=height,
                    direction=BEARISH if top else BULLISH)
        out["metrics"]["neck_at_t"] = neck_t
        found.append(_finish(out, d, lv, rs.pos, k, p, t_frac))
    return found


def detect_head_shoulders(daily: pd.DataFrame, p: PatternParams = PatternParams(),
                          *, inverse: bool = False) -> dict:
    return _pick(detect_hs(daily, p, inverse=inverse), HS_RULES)


# ================================================== §7-§10 boundary patterns
#
# Triangles, rectangles and wedges are ONE geometry read three ways: two lines
# fitted to the swings inside a window, then classified by their slopes. §11's
# overlap rule 2 says the classes are mutually exclusive, so the classifier
# below is the single place that decides, and each detector filters its own
# kinds out of the same search.
#
# Unlike a double bottom, a boundary pattern has no last key point — its lines
# are refitted on every bar, so like the cup it re-completes each day and its
# state is judged at t rather than walked forward from a completion date.

ASCENDING, DESCENDING, SYMMETRICAL = "ascending", "descending", "symmetrical"
RECTANGLE, RISING_WEDGE, FALLING_WEDGE = "rectangle", "rising_wedge", "falling_wedge"

TRIANGLE_KINDS = (ASCENDING, DESCENDING, SYMMETRICAL)
WEDGE_KINDS = (RISING_WEDGE, FALLING_WEDGE)

TR_RULES = ("TR-01", "TR-02", "TR-03", "TR-04", "TR-05", "TR-06", "TR-07")
RC_RULES = ("RC-01", "RC-02", "RC-03", "RC-04")
FB_RULES = ("FB-01", "FB-02", "FB-03", "FB-04", "FB-05")
FL_RULES = ("FP-01", "FP-02", "FP-03", "FL-01", "FL-02", "FL-03", "FL-04")
HTF_RULES = ("HTF-01", "HTF-02", "HTF-03", "HTF-04")


def apex(upper: Line, lower: Line) -> float | None:
    """Where the two lines meet, in bar positions. None when parallel."""
    gap = upper.slope - lower.slope
    if abs(gap) < 1e-12:
        return None
    return (lower.intercept - upper.intercept) / gap


def classify_lines(upper: Line, lower: Line, mid_x: float,
                   p: PatternParams = PatternParams()) -> str | None:
    """§7.2, §8.1 and §10 in one place, because the classes are exclusive.

    Returns None for a pair that is none of them — an expanding formation
    (lines diverging in opposite directions), which the spec does not cover.
    """
    su, sl = upper.pct_slope(mid_x), lower.pct_slope(mid_x)
    if su != su or sl != sl:
        return None
    flat_u, flat_l = abs(su) <= p.flat_slope, abs(sl) <= p.flat_slope
    if flat_u and flat_l:
        return RECTANGLE
    if flat_u and sl > 0:
        return ASCENDING
    if flat_l and su < 0:
        return DESCENDING
    if su < 0 and sl > 0:
        # symmetrical only when the two sides converge at a similar rate
        if abs(su) <= p.sym_slope_ratio * abs(sl) and abs(sl) <= p.sym_slope_ratio * abs(su):
            return SYMMETRICAL
        return None
    if su > 0 and sl > 0:
        return RISING_WEDGE if sl > su else None       # WG-02: lower rises faster
    if su < 0 and sl < 0:
        return FALLING_WEDGE if su < sl else None      # WG-02: upper falls faster
    return None


def _channel(d: pd.DataFrame, pts: list[Swing], start: int, t_hi: int,
             t_frac: float) -> tuple[Line, Line, int, int] | None:
    """Fit TL-01's two lines to the swings in [start, t_hi]."""
    highs = [(s.pos, s.price) for s in pts if s.kind == "H" and start <= s.pos <= t_hi]
    lows = [(s.pos, s.price) for s in pts if s.kind == "L" and start <= s.pos <= t_hi]
    if len(highs) < 2 or len(lows) < 2:
        return None
    upper, lower = fit_line(highs), fit_line(lows)
    if upper is None or lower is None:
        return None
    swings_in = [s for s in pts if start <= s.pos <= t_hi]
    tu = touches(upper, [s for s in swings_in if s.kind == "H"], t_frac)
    tl = touches(lower, [s for s in swings_in if s.kind == "L"], t_frac)
    return upper, lower, tu, tl


def detect_boundaries(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> list[dict]:
    """Every triangle, rectangle and wedge visible on the last bar (§7, §8.1, §10).

    The spec defines S as "the first swing point touching either line", which
    is circular — the lines depend on which points are in the window. Resolved
    the usual way: pick a window, fit to every swing inside it, then report S
    as the earliest swing that actually touches a line.
    """
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n = len(d)
    if n < p.tr_days[0] + 2 * p.k_minor + 5:
        return []
    close = d["close"].to_numpy(float)
    volume = d["volume"].to_numpy(float)
    atr_t = float(d["atr14"].iloc[-1]) if "atr14" in d else float("nan")
    t_pos, t_hi = n - 1, n - 2
    t_frac = tol(float(close[-1]), atr_t, p)
    idx = d.index

    found: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for k in (p.k_minor, p.k_major):
        pts = swings(d, k, p)
        for anchor in pts:
            dur = t_pos - anchor.pos
            if not (p.tr_days[0] <= dur <= max(p.tr_days[1], p.rc_days[1])):
                continue
            # TR-01: the scale follows the pattern's length
            if (dur < p.tr_scale_days) != (k == p.k_minor):
                continue
            fit = _channel(d, pts, anchor.pos, t_hi, t_frac)
            if fit is None:
                continue
            upper, lower, tu, tl = fit
            mid = (anchor.pos + t_pos) / 2
            kind = classify_lines(upper, lower, mid, p)
            if kind is None or (kind, anchor.pos) in seen:
                continue
            seen.add((kind, anchor.pos))
            out = _result({"S": {"pos": anchor.pos, "price": anchor.price,
                                 "date": idx[anchor.pos]}})
            out["kind"] = kind
            res = _boundary_rules(out, d, kind, upper, lower, anchor.pos, tu, tl,
                                  close, volume, t_pos, t_hi, mid, t_frac, p)
            found.append(res)
    return found


def _boundary_rules(out: dict, d: pd.DataFrame, kind: str, upper: Line, lower: Line,
                    s_pos: int, tu: int, tl: int, close, volume, t_pos: int,
                    t_hi: int, mid: float, t_frac: float, p: PatternParams) -> dict:
    """TR-01..TR-07 for triangles and wedges, RC-01..RC-04 for rectangles."""
    rect = kind == RECTANGLE
    rules = RC_RULES if rect else TR_RULES
    dur = t_pos - s_pos
    out["metrics"].update({
        "duration_days": dur, "touches_upper": tu, "touches_lower": tl,
        "upper_slope": upper.pct_slope(mid), "lower_slope": lower.pct_slope(mid),
    })

    # TL-03 / TR-01: price stays inside the lines before the breakout
    if not contained(upper, lower, close, s_pos, t_hi, t_frac):
        out["fail"] = "TL-03"
        return out

    # TR-02 / RC-02: enough touches
    need_side = p.rc_min_touches_side if rect else p.tr_min_touches_side
    need_all = p.rc_min_touches if rect else p.tr_min_touches
    if tu < need_side or tl < need_side or tu + tl < need_all:
        out["fail"] = rules[1]
        return out

    height0 = upper.at(s_pos) - lower.at(s_pos)
    out["metrics"]["height_pct"] = height0 / close[t_pos] * 100 if close[t_pos] else float("nan")

    if rect:
        # RC-03: range height, measured on the flat lines
        rng = height0 / lower.at(s_pos) * 100 if lower.at(s_pos) else float("nan")
        out["metrics"]["range_pct"] = rng
        if not (p.rc_height[0] <= rng <= p.rc_height[1]):
            out["fail"] = "RC-03"
            return out
        if not (p.rc_days[0] <= dur <= p.rc_days[1]):
            out["fail"] = "RC-04"
            return out
        lv = Levels(trigger=upper.at(t_pos), invalidation=lower.at(t_pos),
                    height=height0)
        return _boundary_state(out, lv, close, volume, s_pos, t_pos, p)

    # TR-03: the lines converge, with the apex still ahead
    x = apex(upper, lower)
    out["metrics"]["apex_pos"] = x
    if x is None or x <= t_pos:
        out["fail"] = "TR-03"
        return out

    # TR-04: duration
    if not (p.tr_days[0] <= dur <= p.tr_days[1]):
        out["fail"] = "TR-04"
        return out

    # TR-05: how far through the triangle price has travelled
    progress = (t_pos - s_pos) / (x - s_pos) if x > s_pos else float("nan")
    out["metrics"]["apex_progress"] = progress
    if not (progress == progress) or progress > p.tr_apex_zone[1]:
        out["fail"] = "TR-05"          # X: 80% of the way with no breakout
        return out

    # TR-06: volume declines through the pattern
    slope = log_volume_slope(volume, s_pos, t_pos)
    out["metrics"]["log_volume_slope"] = slope
    if p.tr_volume and not (slope == slope and slope < 0):
        out["fail"] = "TR-06"
        return out

    # TR-07: the pattern is big enough to be worth trading
    if not (out["metrics"]["height_pct"] >= p.tr_min_height):
        out["fail"] = "TR-07"
        return out

    # §7.3 / §10: a triangle records both directions; a wedge leads with its bias
    if kind == RISING_WEDGE:
        lv = Levels(trigger=lower.at(t_pos), invalidation=upper.at(t_pos),
                    height=height0, direction=BEARISH)
    elif kind == FALLING_WEDGE:
        lv = Levels(trigger=upper.at(t_pos), invalidation=lower.at(t_pos),
                    height=height0)
    elif kind == DESCENDING:
        lv = Levels(trigger=lower.at(t_pos), invalidation=upper.at(t_pos),
                    height=height0, direction=BEARISH)
    else:
        lv = Levels(trigger=upper.at(t_pos), invalidation=lower.at(t_pos),
                    height=height0)
    out["metrics"]["trigger_other_way"] = (lower.at(t_pos) if lv.direction == BULLISH
                                           else upper.at(t_pos))
    return _boundary_state(out, lv, close, volume, s_pos, t_pos, p)


def _boundary_state(out: dict, lv: Levels, close, volume, s_pos: int, t_pos: int,
                    p: PatternParams) -> dict:
    """Judged at t: the lines move every bar, so there is no completion date
    to run BO-04's clock from — TR-05's apex zone plays that role instead."""
    out["levels"] = lv
    fired = broke_out(float(close[t_pos]), rv(volume, t_pos, vol50(volume, s_pos)), lv, p)
    out["state"] = CONFIRMED if fired else COMPLETE
    out["breakout_pos"] = t_pos if fired else None
    out["metrics"]["bars_since_breakout"] = 0 if fired else None
    out["metrics"]["is_live"] = True
    out["ok"] = True
    return out


def _pick_kinds(cands: list[dict], kinds: tuple[str, ...], rules: tuple[str, ...]) -> dict:
    """Of one family, the complete one with the most touches; else the
    furthest near-miss."""
    mine = [c for c in cands if c.get("kind") in kinds]
    ok = [c for c in mine if c["ok"]]
    if ok:
        return max(ok, key=lambda c: (c["metrics"]["touches_upper"]
                                      + c["metrics"]["touches_lower"],
                                      c["metrics"]["duration_days"]))
    if not mine:
        return _result({})
    return max(mine, key=lambda c: rules.index(c["fail"]) if c["fail"] in rules else -1)


def detect_triangle(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    return _pick_kinds(detect_boundaries(daily, p), TRIANGLE_KINDS, TR_RULES)


def detect_wedge(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    return _pick_kinds(detect_boundaries(daily, p), WEDGE_KINDS, TR_RULES)


def detect_rectangle(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    return _pick_kinds(detect_boundaries(daily, p), (RECTANGLE,), RC_RULES)


# ------------------------------------------------------- §8.2 flat base

def detect_flat_base(daily: pd.DataFrame, p: PatternParams = PatternParams()) -> dict:
    """§8.2. The window is the LONGEST N in fb_days for which FB-02 still
    holds, so the whole base is measured rather than its last few weeks."""
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n = len(d)
    high, low, close = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    volume = d["volume"].to_numpy(float)
    t_pos = n - 1
    out = _result({})
    if n < p.fb_days[0] + p.prior_window // 2:
        out["fail"] = "FB-03"
        return out

    best_n = None
    for N in range(min(p.fb_days[1], n - 2), p.fb_days[0] - 1, -1):
        w_hi = float(high[n - N:].max())
        w_lo = float(low[n - N:].min())
        if w_hi > 0 and (w_hi - w_lo) / w_hi * 100 <= p.fb_max_depth:
            best_n = N
            break
    if best_n is None:
        out["fail"] = "FB-02"
        return out

    start = n - best_n
    w_hi, w_lo = float(high[start:].max()), float(low[start:].min())
    out["points"] = {"S": {"pos": start, "price": w_hi, "date": d.index[start]}}
    out["metrics"].update({
        "window_days": best_n,
        "depth_pct": (w_hi - w_lo) / w_hi * 100,
    })

    # FB-01: the advance the base is resting on
    ok, adv = prior_uptrend(low, start, float(close[start]), p, move=p.fb_prior_move)
    out["metrics"]["prior_advance_pct"] = adv
    if not ok:
        out["fail"] = "FB-01"
        return out
    if best_n < p.fb_days[0]:
        out["fail"] = "FB-03"
        return out

    # FB-04: the base sits near the highs
    hi52 = (float(d["high_252"].iloc[-1]) if "high_252" in d
            else float(high[max(0, n - 252):].max()))
    out["metrics"]["pct_of_52w_high"] = w_hi / hi52 * 100 if hi52 else float("nan")
    if not (hi52 and w_hi >= p.fb_near_high * hi52):
        out["fail"] = "FB-04"
        return out

    # FB-05: optional dry-up over the last ten days
    if p.fb_volume:
        v50 = vol50(volume, start)
        ratio = float(volume[-10:].mean()) / v50 if v50 and v50 == v50 else float("nan")
        out["metrics"]["dryup"] = ratio
        if not (ratio == ratio and ratio <= 0.8):
            out["fail"] = "FB-05"
            return out

    lv = Levels(trigger=w_hi, invalidation=w_lo, height=w_hi - w_lo)
    return _boundary_state(out, lv, close, volume, start, t_pos, p)


# --------------------------------------------- §9 flags, pennants, HTF

def detect_flag(daily: pd.DataFrame, p: PatternParams = PatternParams(), *,
                high_tight: bool = False) -> dict:
    """§9.1 pole plus §9.2 flag or pennant, or §9.3 the high tight flag.

    FL-04 needs two fitted lines inside a pause of 5-20 bars. At k_minor = 3 a
    confirmed swing needs 3 bars either side, so a short flag often holds
    fewer than the two swings per line TL-01 requires; those report FL-04 and
    are counted, not silently dropped.
    """
    d = daily.iloc[-p.lookback:] if len(daily) > p.lookback else daily
    n = len(d)
    high, low, close = (d[c].to_numpy(float) for c in ("high", "low", "close"))
    volume = d["volume"].to_numpy(float)
    t_pos, t_hi = n - 1, n - 2
    atr_t = float(d["atr14"].iloc[-1]) if "atr14" in d else float("nan")
    t_frac = tol(float(close[-1]), atr_t, p)
    idx = d.index
    rules = HTF_RULES if high_tight else FL_RULES
    flag_window = p.htf_flag_days if high_tight else p.flag_days
    out = _result({})

    best = None
    for flag_len in range(flag_window[0], flag_window[1] + 1):
        p1_pos = t_pos - flag_len
        if p1_pos <= p.pole_days + 2:
            continue
        # P1 is the highest high at the end of the move; nothing in the pause
        # may exceed it, or the pole has not ended
        if high[p1_pos + 1: t_hi + 1].size and float(high[p1_pos + 1: t_hi + 1].max()) > high[p1_pos]:
            continue
        # P0 is "the lowest low before the move" (§9.1), searched over twice
        # FP-02's limit. Bounding the search BY that limit instead made FP-02
        # unreachable: a 30-day advance was simply measured over its last 15
        # days, so it failed FP-01 on a shrunken gain rather than FP-02 on its
        # duration, and no chart could ever trip the duration rule.
        span = p.htf_pole_days[1] if high_tight else 2 * p.pole_days
        lo_i = max(0, p1_pos - span)
        p0_pos = lo_i + int(np.argmin(low[lo_i: p1_pos + 1]))
        gain = (high[p1_pos] / low[p0_pos] - 1) * 100 if low[p0_pos] else float("nan")
        if best is None or gain > best[0]:
            best = (gain, p0_pos, p1_pos, flag_len)
    if best is None:
        out["fail"] = rules[0]
        return out

    gain, p0_pos, p1_pos, flag_len = best
    P0, P1 = float(low[p0_pos]), float(high[p1_pos])
    out["points"] = {"P0": {"pos": p0_pos, "price": P0, "date": idx[p0_pos]},
                     "P1": {"pos": p1_pos, "price": P1, "date": idx[p1_pos]}}
    out["metrics"].update({"pole_gain_pct": gain, "pole_days": p1_pos - p0_pos,
                           "flag_days": flag_len})

    # FP-01 / HTF-01: the pole
    need_gain = p.htf_gain if high_tight else p.pole_gain
    if not (gain == gain and gain >= need_gain):
        out["fail"] = rules[0]
        return out
    # FP-02 / HTF-02: and how fast it ran
    pole_days = p1_pos - p0_pos
    if high_tight:
        if not (p.htf_pole_days[0] <= pole_days <= p.htf_pole_days[1]):
            out["fail"] = "HTF-02"
            return out
    elif pole_days > p.pole_days:
        out["fail"] = "FP-02"
        return out

    flag_low = float(low[p1_pos + 1:].min())
    out["points"]["X"] = {"pos": p1_pos + 1 + int(np.argmin(low[p1_pos + 1:])),
                          "price": flag_low, "date": idx[p1_pos + 1 + int(np.argmin(low[p1_pos + 1:]))]}

    if high_tight:
        # HTF-03: flag depth, measured off P1 rather than off the pole
        depth = (P1 - flag_low) / P1 * 100
        out["metrics"]["flag_depth_pct"] = depth
        if not (depth <= p.htf_depth):
            out["fail"] = "HTF-03"
            return out
        # HTF-04 is the flag_window the search already honoured; H is unused,
        # because the textbook gives no measured target for this one
        T = float(high[p1_pos: t_hi + 1].max())
        lv = Levels(trigger=T, invalidation=flag_low, height=0.0)
        return _boundary_state(out, lv, close, volume, p0_pos, t_pos, p)

    # FP-03: the pole came on real volume
    v50 = vol50(volume, p0_pos)
    pole_rv = float(volume[p0_pos: p1_pos + 1].mean()) / v50 if v50 and v50 == v50 else float("nan")
    out["metrics"]["pole_rv"] = pole_rv
    if not (pole_rv == pole_rv and pole_rv >= p.pole_rv):
        out["fail"] = "FP-03"
        return out

    # FL-02: a shallow retracement of the pole
    retrace = (P1 - flag_low) / (P1 - P0) * 100 if P1 > P0 else float("nan")
    out["metrics"]["retrace_pct"] = retrace
    if not (retrace == retrace and retrace <= p.flag_retrace):
        out["fail"] = "FL-02"
        return out

    # FL-03: volume declines through the pause
    slope = log_volume_slope(volume, p1_pos + 1, t_pos)
    out["metrics"]["log_volume_slope"] = slope
    if not (slope == slope and slope < 0):
        out["fail"] = "FL-03"
        return out

    # FL-04: a channel (flag) or a converging pair (pennant)
    pts = swings(d, p.k_minor, p)
    fit = _channel(d, pts, p1_pos, t_hi, t_frac)
    if fit is None:
        out["fail"] = "FL-04"
        return out
    upper, lower, tu, tl = fit
    mid = (p1_pos + t_pos) / 2
    su, sl = upper.pct_slope(mid), lower.pct_slope(mid)
    out["metrics"].update({"upper_slope": su, "lower_slope": sl,
                           "touches_upper": tu, "touches_lower": tl})
    x = apex(upper, lower)
    is_pennant = su < 0 < sl and x is not None and x > t_pos
    is_flag = (su <= p.flat_slope and sl <= p.flat_slope
               and abs(su) <= p.flag_slope_ratio * abs(sl) + 1e-12
               and abs(sl) <= p.flag_slope_ratio * abs(su) + 1e-12)
    if not (is_flag or is_pennant):
        out["fail"] = "FL-04"
        return out
    out["kind"] = "pennant" if is_pennant else "flag"

    lv = Levels(trigger=upper.at(t_pos), invalidation=flag_low, height=P1 - P0)
    return _boundary_state(out, lv, close, volume, p0_pos, t_pos, p)


# ============================================ §11 the scanner and overlaps
#
# Everything above answers "what is on this chart today". §11 is the part
# that remembers: a pattern is an INSTANCE, keyed by (symbol, type, anchor
# date), that is born when its geometry first passes, updated as later bars
# move its levels, and closed when it breaks out, expires or is invalidated.
#
# Why it matters beyond bookkeeping: without it, BO-04 (expiry) and BO-05
# (failure) have no clock, §3.3's outcomes have nothing to attach to, and the
# same cup re-detected on forty consecutive bars counts as forty patterns in
# any statistics you compute.
#
# A GAP IN §5, found by screening with it: DB-03 and DT-03 require the middle
# swing to be at least 10% from the bottoms and set no ceiling, so two lows
# either side of a spike satisfy the rule. `db_max_peak` exists to test a cap
# and is off by default, because the spec does not have one.
#
# A GAP IN §11's OVERLAP RULES, found by running it. Rule 1 keys an instance
# by (symbol, type, anchor), and rule 3 resolves named pairs across families
# (flat base over rectangle, HTF over flag). Neither covers TWO INSTANCES OF
# THE SAME TYPE whose anchors differ but which describe one event: six
# symbols over 120 days produced SU rising wedges anchored 2025-12-17 and
# 2026-04-07 that both "broke out" on 2026-05-27 with identical excursions,
# and GILD produced two more on 2026-09-09. Counted naively that is four
# breakouts from two. Deduplicating on (type, breakout date) before computing
# statistics is left to the caller, and `rows()` carries both columns so it
# can be done; the spec gives no rule for it.
#
# NOT implemented: FORMING. The spec's first state is "some key points exist,
# but not all", which needs each detector to report partial structure — a cup
# with A and B but no C yet. The detectors here answer only at day t, so an
# instance enters the store at COMPLETE. `Instance.advance()` and the state
# constants handle FORMING if a future detector ever emits it; nothing does.

ANCHOR_KEYS = ("A", "B", "LS", "S", "P0", "B1")


def anchor_of(result: dict) -> pd.Timestamp | None:
    """§11's identity: the pattern's first key point."""
    for key in ANCHOR_KEYS:
        if key in result.get("points", {}):
            return result["points"][key]["date"]
    return None


# (type name, how to get every candidate of that type)
SCAN_DETECTORS: tuple[tuple[str, object], ...] = (
    ("cup", lambda d, p: detect_cups(d, p)),
    ("cup_no_handle", lambda d, p: detect_cups(d, p, require_handle=False)),
    ("double_bottom", lambda d, p: detect_doubles(d, p, direction=BULLISH)),
    ("double_top", lambda d, p: detect_doubles(d, p, direction=BEARISH)),
    ("triple_bottom", lambda d, p: detect_triples(d, p, direction=BULLISH)),
    ("triple_top", lambda d, p: detect_triples(d, p, direction=BEARISH)),
    ("hs_top", lambda d, p: detect_hs(d, p)),
    ("hs_inverse", lambda d, p: detect_hs(d, p, inverse=True)),
    ("boundary", lambda d, p: detect_boundaries(d, p)),
    ("flat_base", lambda d, p: [detect_flat_base(d, p)]),
    ("flag", lambda d, p: [detect_flag(d, p)]),
    ("high_tight_flag", lambda d, p: [detect_flag(d, p, high_tight=True)]),
)

# §11 overlap rule 3, "most specific wins within a family": (winner, loser).
# The loser is kept and marked, never deleted — the spec wants the overlap
# visible so the combination can be studied, not silently resolved.
SUPERSEDES: tuple[tuple[str, str], ...] = (
    ("high_tight_flag", "flag"),   # same pole, the rarer reading wins
    ("cup", "cup_no_handle"),      # the same base once its handle has formed
    ("flat_base", "rectangle"),    # same days after an uptrend
)


def min_scan_bars(p: PatternParams = PatternParams()) -> int:
    """The shortest frame worth scanning: §2.4's prior window, the shortest
    pattern, and the bars a swing needs to confirm. Each detector guards its
    own longer minimum, so the scanner's floor only has to admit the smallest
    one — a fixed 320 silently refused every chart under 15 months.
    """
    return p.prior_window + p.db_days[0] + 2 * p.k_major + 5


@dataclass
class Instance:
    """One tracked pattern (§3.1, §11)."""

    symbol: str
    type: str
    anchor: pd.Timestamp
    state: str = COMPLETE
    levels: Levels | None = None
    points: dict = None
    metrics: dict = None
    first_seen: pd.Timestamp | None = None
    last_seen: pd.Timestamp | None = None
    completed_on: pd.Timestamp | None = None
    breakout_on: pd.Timestamp | None = None
    breakout_pos: int | None = None
    outcome: Outcome | None = None
    outcome_final: bool = False
    secondary_to: str | None = None

    @property
    def key(self) -> tuple[str, str, pd.Timestamp]:
        return (self.symbol, self.type, self.anchor)

    @property
    def is_open(self) -> bool:
        return self.state in (FORMING, COMPLETE)


class PatternScanner:
    """§11's loop, for one universe.

    Feed it `scan_day(symbol, daily)` where `daily` ENDS on the bar being
    judged. It updates the instances it already holds for that symbol before
    looking for new ones, which is the order the spec gives and the reason the
    same pattern is not counted twice.
    """

    def __init__(self, p: PatternParams = PatternParams()):
        self.p = p
        self.instances: dict[tuple[str, str, pd.Timestamp], Instance] = {}

    # ---- step 2: update what is already tracked -------------------------

    def _update_tracked(self, symbol: str, daily: pd.DataFrame,
                        fresh: dict[tuple[str, pd.Timestamp], dict]) -> None:
        t_pos = len(daily) - 1
        today = daily.index[t_pos]
        close = daily["close"].to_numpy(float)
        volume = daily["volume"].to_numpy(float)
        atr_t = float(daily["atr14"].iloc[-1]) if "atr14" in daily else float("nan")
        t_frac = tol(float(close[-1]), atr_t, self.p)

        for inst in [i for i in self.instances.values() if i.symbol == symbol]:
            if inst.outcome_final:
                continue
            inst.last_seen = today
            match = fresh.get((inst.type, inst.anchor))

            if inst.is_open:
                if match is None or not match["ok"]:
                    inst.state = VOID            # geometry_ok(t) failed
                    continue
                # update_points(t): the levels move as the pattern develops
                inst.levels = match["levels"]
                inst.points, inst.metrics = match["points"], match["metrics"]
                c = float(close[t_pos])
                if voided(c, inst.levels):                              # BO-03
                    inst.state = VOID
                elif broke_out(c, rv(volume, t_pos, vol50(volume, max(0, t_pos - 60))),
                               inst.levels, self.p):                     # BO-01/02
                    inst.state, inst.breakout_on = CONFIRMED, today
                    inst.breakout_pos = t_pos
                elif inst.completed_on is not None and expired(
                        _bars_between(daily, inst.completed_on, today), self.p):
                    inst.state = VOID                                    # BO-04
                continue

            if inst.state == CONFIRMED and inst.breakout_pos is not None:
                bo = _pos_of(daily, inst.breakout_on)
                if bo is None:
                    continue
                if broke_back(close, bo, t_pos, inst.levels, t_frac, self.p):
                    inst.state = FAILED                                  # BO-05
                inst.outcome = outcomes(daily, bo, inst.levels, self.p, t_frac)
                if t_pos - bo >= self.p.horizon:
                    inst.outcome_final = True                            # §3.3

    # ---- step 3: look for new patterns ----------------------------------

    def scan_day(self, symbol: str, daily: pd.DataFrame) -> list[Instance]:
        """Run one (stock, day). `daily` must end on day t."""
        if daily is None or len(daily) < min_scan_bars(self.p):
            return []
        today = daily.index[-1]
        fresh: dict[tuple[str, pd.Timestamp], dict] = {}
        for type_name, detect in SCAN_DETECTORS:
            for res in detect(daily, self.p):
                if not res or not res.get("points"):
                    continue
                anchor = anchor_of(res)
                if anchor is None:
                    continue
                # a boundary pattern's type IS its slope class (overlap rule 2)
                name = res.get("kind") if type_name == "boundary" else type_name
                if type_name == "flag" and res.get("kind"):
                    name = res["kind"]
                if name:
                    fresh[(name, anchor)] = res

        self._update_tracked(symbol, daily, fresh)

        for (name, anchor), res in fresh.items():
            key = (symbol, name, anchor)
            if key in self.instances or not res["ok"]:
                continue                      # rule 1: one instance per anchor
            self.instances[key] = Instance(
                symbol=symbol, type=name, anchor=anchor,
                state=res["state"], levels=res["levels"],
                points=res["points"], metrics=res["metrics"],
                first_seen=today, last_seen=today, completed_on=today,
                breakout_on=today if res["state"] == CONFIRMED else None,
                breakout_pos=res.get("breakout_pos"),
            )

        live = [i for i in self.instances.values()
                if i.symbol == symbol and i.last_seen == today]
        _apply_overlaps(live)
        return live

    def scan_history(self, symbol: str, daily: pd.DataFrame,
                     start: pd.Timestamp | None = None) -> list[Instance]:
        """§11's outer loop over days, for one symbol.

        Honest about the cost: every bar re-runs all twelve detectors on an
        expanding slice, ~40ms each, so a 250-bar window is ~10s per symbol.
        That is the price of the spec's own anti-look-ahead rule — the frame
        handed to day t cannot contain bar t+1.
        """
        for i in range(min_scan_bars(self.p), len(daily) + 1):
            frame_t = daily.iloc[:i]
            if start is not None and frame_t.index[-1] < start:
                continue
            self.scan_day(symbol, frame_t)
        return [i for i in self.instances.values() if i.symbol == symbol]

    def rows(self) -> pd.DataFrame:
        """Every instance as a row — the research table §3.3 feeds."""
        recs = []
        for i in self.instances.values():
            o = i.outcome
            recs.append({
                "symbol": i.symbol, "type": i.type, "anchor": i.anchor,
                "state": i.state, "first_seen": i.first_seen,
                "breakout_on": i.breakout_on, "secondary_to": i.secondary_to,
                "trigger": i.levels.trigger if i.levels else None,
                "target": i.levels.target if i.levels else None,
                "direction": i.levels.direction if i.levels else None,
                "hit_target": o.hit_target if o else None,
                "mfe": o.mfe if o else None, "mae": o.mae if o else None,
                "throwback": o.throwback if o else None,
                "ret_5": o.ret_5 if o else None, "ret_20": o.ret_20 if o else None,
                "ret_60": o.ret_60 if o else None,
            })
        return pd.DataFrame(recs)


def _pos_of(daily: pd.DataFrame, when: pd.Timestamp | None) -> int | None:
    if when is None:
        return None
    idx = daily.index.get_indexer([when])
    return int(idx[0]) if idx[0] >= 0 else None


def _bars_between(daily: pd.DataFrame, a: pd.Timestamp, b: pd.Timestamp) -> int:
    pa, pb = _pos_of(daily, a), _pos_of(daily, b)
    return (pb - pa) if (pa is not None and pb is not None) else 0


def _apply_overlaps(live: list[Instance]) -> None:
    """§11 rule 3. The loser keeps its row and gains `secondary_to`, so a
    breakout is counted once per label and the overlap stays visible."""
    by_type: dict[str, list[Instance]] = {}
    for i in live:
        by_type.setdefault(i.type, []).append(i)
        i.secondary_to = None
    for winner, loser in SUPERSEDES:
        if winner in by_type and loser in by_type:
            for i in by_type[loser]:
                i.secondary_to = winner
