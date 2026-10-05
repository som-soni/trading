"""Classical chart-pattern geometry — the bases that precede a breakout.

Six patterns from the breakout literature are detected here: the
cup-and-handle and double bottom (O'Neil, *How to Make Money in Stocks*),
the flat base / Darvas box (Darvas, *How I Made $2,000,000*), the bull flag
and its high-tight variant, the ascending triangle, and the
volatility-contraction pattern (Minervini, *Trade Like a Stock Market
Wizard*).

This module is deliberately OPINION-FREE. A detector answers exactly one
question — "as of this bar, is this base present on the chart, and where is
its pivot?" — and returns geometry: the pivot to clear, the structural low a
stop belongs under, the measured move the pattern projects, how deep and how
long it is, and a 0-1 quality score. Whether any of that is tradeable (trend
context, liquidity, extension, risk, earnings) belongs to a Strategy, not
here. That split is what lets several strategies reuse the same geometry.

Point-in-time discipline
------------------------
Every detector takes the frame's LAST row as "now" and reads nothing beyond
it, so it can be applied to a sliced frame inside a backtest. One asymmetry
is deliberate and load-bearing:

  * levels that define a PIVOT are computed from bars up to index -2,
    excluding the current bar;
  * levels that define a STOP (lows) and volume may use the current bar.

Without that, the breakout bar's own high defines the pivot it is supposedly
breaking, so every pattern "breaks out" by construction and a backtest of it
is meaningless. The current bar's low is different: it is known at the close
and a stop placed under it is honest.

Thresholds
----------
The numbers are the conventional ones from the sources above (cup 12-50%
deep, handle 5-20 bars drifting down no more than a third of the cup on
declining volume, flat base under 15% over five weeks or more, flag retracing
under 40% of its pole, each VCP contraction tighter than the last). They are NOT tuned on this repository's data and no
pattern here has been backtested. Treat a match as a hypothesis.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

# pattern codes — these double as a strategy's setup codes, so keep them
# short, uppercase and stable (they become report column names)
CUP = "CUP"      # cup-and-handle
CUPNH = "CUPNH"  # cup without a handle (yet)
DBOT = "DBOT"    # double bottom (W)
FLAT = "FLAT"    # flat base / Darvas box
FLAG = "FLAG"    # bull flag (incl. high tight flag)
ATRI = "ATRI"    # ascending triangle
VCP = "VCP"      # volatility contraction pattern

# Topping structures. These are NOT entries: the book here is long-only, so a
# top cannot be sold short. They exist to VETO a long and to mark an exit —
# a breakout bought inside a confirmed top is the trade this screener would
# otherwise keep taking.
DTOP = "DTOP"    # double top (M)
HSTOP = "HSTOP"  # head and shoulders top

BULLISH_CODES: tuple[str, ...] = (CUP, CUPNH, DBOT, FLAT, FLAG, ATRI, VCP)
TOPPING_CODES: tuple[str, ...] = (DTOP, HSTOP)
ALL_CODES: tuple[str, ...] = BULLISH_CODES + TOPPING_CODES

PATTERN_NAMES = {
    CUP: "cup-and-handle",
    CUPNH: "cup without handle",
    DTOP: "double top",
    HSTOP: "head and shoulders top",
    DBOT: "double bottom",
    FLAT: "flat base",
    FLAG: "bull flag",
    ATRI: "ascending triangle",
    VCP: "volatility contraction",
}

# Enough history for the longest base (250 bars) plus room for the pole/prior
# advance a few detectors look back at.
MIN_BARS = 300


@dataclass(frozen=True)
class Flaw:
    """One way a match departs from the textbook description.

    A detector's bounds are what it will ACCEPT; the textbook describes what
    is IDEAL, and the gap between the two is most of what a human sees when
    they say "that's a cup but the handle hasn't formed". Recording the gap
    keeps the loose matches in the report — they are real structures worth
    watching — without letting them read as equals of a clean one.
    """

    severity: str  # "major" | "minor"
    text: str


@dataclass(frozen=True)
class PatternMatch:
    """One pattern found on one chart, as of the frame's last bar."""

    code: str
    pivot: float          # the resistance a breakout must clear
    stop_ref: float       # structural low the stop belongs under
    measured_move: float  # what the pattern projects above the pivot
    base_low: float
    base_high: float
    start_pos: int        # integer positions into the frame passed in
    end_pos: int
    depth_pct: float      # base depth, % of the base high
    length_bars: int
    quality: float        # 0-1, higher is a cleaner example of the pattern
    note: str
    # None means this detector does not assess textbook deviations yet; an
    # empty tuple means it does and found none. Only CUP implements it so far.
    flaws: tuple[Flaw, ...] | None = None

    @property
    def name(self) -> str:
        return PATTERN_NAMES.get(self.code, self.code)

    @property
    def is_bearish(self) -> bool:
        """A topping structure. It never becomes a setup — see TOPPING_CODES."""
        return self.code in TOPPING_CODES

    @property
    def major_flaws(self) -> int:
        return sum(1 for f in (self.flaws or ()) if f.severity == "major")

    @property
    def minor_flaws(self) -> int:
        return sum(1 for f in (self.flaws or ()) if f.severity == "minor")

    @property
    def confidence(self) -> str:
        """How close this is to the textbook description — NOT a probability
        and not a forecast. A `low` match is still a real structure; it is
        further from the pattern whose statistics are being claimed."""
        if self.flaws is None:
            return "unassessed"
        if self.major_flaws >= 2 or self.minor_flaws >= 4:
            return "low"
        if self.major_flaws or self.minor_flaws >= 2:
            return "moderate"
        return "textbook"

    @property
    def flaw_text(self) -> str:
        return "; ".join(f.text for f in (self.flaws or ()))

    @property
    def target(self) -> float:
        return self.pivot + self.measured_move


# ---------------------------------------------------------------- helpers


def _clip01(x: float) -> float:
    if x != x:  # NaN
        return 0.0
    return float(min(1.0, max(0.0, x)))


def _band_score(x: float, lo: float, hi: float) -> float:
    """1.0 inside [lo, hi], tapering to 0 across the same width outside it.
    Used so "ideal depth is 20-35%" doesn't become a cliff at 35.0%."""
    if x != x:
        return 0.0
    if lo <= x <= hi:
        return 1.0
    width = max(hi - lo, 1e-9)
    if x < lo:
        return _clip01(1 - (lo - x) / width)
    return _clip01(1 - (x - hi) / width)


def _confirmed_pivots(
    values: np.ndarray, width: int, how: str, lo: int, hi: int
) -> list[int]:
    """Positions i in [lo, hi] where values[i] is the extreme of its
    +/-`width` neighbourhood.

    A fractal pivot is only CONFIRMED once `width` bars have printed to its
    right, so the search stops `width` bars short of `hi`. Detectors that
    need the most recent (unconfirmable) extreme use a plain argmin/argmax
    over a range instead — see the cup's handle low.
    """
    out: list[int] = []
    n = len(values)
    start = max(lo, width)
    stop = min(hi, n - 1 - width)
    for i in range(start, stop + 1):
        seg = values[i - width : i + width + 1]
        if how == "max":
            if values[i] >= seg.max():
                out.append(i)
        elif values[i] <= seg.min():
            out.append(i)
    return out


def _mean(a: np.ndarray) -> float:
    return float(a.mean()) if a.size else float("nan")


# ------------------------------------------------------------ cup & handle

MIN_CUP_BARS, MAX_CUP_BARS = 25, 250
# O'Neil's handle is one to four weeks of DOWNWARD DRIFT on DECLINING volume.
# The first version of this detector tested only "a dip of up to 15% that
# stays in the cup's upper half, over 3 to 40 bars", which accepted three
# things that are not handles, all of them found in one live scan:
#   * a rejection at the rim — META hit 779.82 and lost 8.5% in 6 sessions
#     (1.42%/bar) on 1.15x volume; MCX.NS fell 8.3% in 4 (2.07%/bar);
#   * a drift far too long to be a handle — EHC 37 bars, EMBJ 38;
#   * a flat pause at resistance — TECH, 0.5% deep over 8 bars, which is a
#     flat base (and `FLAT` already detects it).
# Each bound below exists to exclude one of those.
MIN_HANDLE_BARS, MAX_HANDLE_BARS = 5, 20
MIN_HANDLE_DEPTH, MAX_HANDLE_DEPTH = 0.02, 0.15
# a handle drifts; faster than this is a rejection being mislabelled
MAX_HANDLE_DRIFT_PER_BAR = 0.012

# The bounds above are what the detector ACCEPTS. These are what O'Neil calls
# IDEAL, and a match outside them is reported with the deviation named rather
# than dropped — a 48% cup is a real structure, it is just not the structure
# whose statistics the pattern's reputation rests on.
IDEAL_CUP_DEPTH = (0.12, 0.33)
IDEAL_CUP_BARS = (35, 325)          # ~7 to 65 weeks
IDEAL_HANDLE_BARS = (8, 20)         # ~2 to 4 weeks
IDEAL_HANDLE_DEPTH = (0.05, 0.12)
RIM_RECOVERY_TOL = 0.03             # right rim within 3% of the left
STRONG_DRY_UP = 0.80                # handle volume this far below the cup's


def _cup_flaws(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, *, depth: float, cup_len: int,
    lh: float, rh: float, bl: float, bp: int, rp: int, handle_depth: float,
    handle_len: int, handle_low: float, dry_up: float, skip_handle: bool = False,
) -> tuple[Flaw, ...]:
    """Every way this cup departs from O'Neil's description, in plain words.

    A `major` flaw is one that changes what the structure IS (a cup that
    never recovered to its rim, a V where a U is claimed); a `minor` one
    changes how good an example it is. The caller decides what to do with
    them — nothing here rejects a match.
    """
    out: list[Flaw] = []

    lo, hi = IDEAL_CUP_DEPTH
    if depth > hi:
        out.append(Flaw(
            "major" if depth > 0.40 else "minor",
            f"cup is {depth * 100:.0f}% deep, beyond the textbook "
            f"{lo * 100:.0f}-{hi * 100:.0f}% — a deep base is a damaged one, "
            f"and the measured move off it is the least reliable part",
        ))
    elif depth < lo:
        out.append(Flaw("minor", f"cup only {depth * 100:.0f}% deep, shallower "
                                 f"than the textbook {lo * 100:.0f}%"))

    # has the right side actually come back to the rim?
    shortfall = (lh - rh) / lh
    if shortfall > RIM_RECOVERY_TOL:
        out.append(Flaw(
            "major",
            f"right rim {rh:.2f} is {shortfall * 100:.1f}% below the left rim "
            f"{lh:.2f} — the cup has not recovered to its own rim, so what "
            f"looks like a handle may still be part of the right side",
        ))

    # U or V? how much of the advance off the low came in its final fifth
    tail = max(3, int(0.2 * max(rp - bp, 1)))
    advance = rh - bl
    if advance > 0 and rp - tail > bp:
        late = (rh - float(c[rp - tail])) / advance
        if late > 0.5:
            out.append(Flaw(
                "major",
                f"{late * 100:.0f}% of the climb off the low came in the last "
                f"{tail} bars — a V-shaped right side, not the rounded one the "
                f"pattern describes",
            ))

    lo_b, hi_b = IDEAL_CUP_BARS
    if cup_len < lo_b:
        out.append(Flaw("minor", f"cup spans {cup_len} bars, under the textbook "
                                 f"{lo_b} (~7 weeks)"))

    if skip_handle:
        # CUPNH has no handle by definition; flagging its absence would be
        # flagging the pattern for being itself
        return tuple(out)

    lo_h, hi_h = IDEAL_HANDLE_BARS
    if handle_len < lo_h:
        out.append(Flaw("minor", f"handle is only {handle_len} bars — handles "
                                 f"usually take {lo_h}-{hi_h} (2-4 weeks), so "
                                 f"this one may still be forming"))

    lo_d, hi_d = IDEAL_HANDLE_DEPTH
    if handle_depth > hi_d:
        out.append(Flaw("minor", f"handle is {handle_depth * 100:.1f}% deep vs "
                                 f"the usual {lo_d * 100:.0f}-{hi_d * 100:.0f}%"))

    # O'Neil wants the handle in the upper third, not merely the upper half
    upper_third = lh - (lh - bl) / 3
    if handle_low < upper_third:
        out.append(Flaw("minor", f"handle low {handle_low:.2f} sits below the "
                                 f"cup's upper third ({upper_third:.2f})"))

    if dry_up == dry_up and dry_up > STRONG_DRY_UP:
        out.append(Flaw("minor", f"handle volume is {dry_up:.2f}x the cup's — "
                                 f"below it, but not the marked dry-up the "
                                 f"pattern wants"))
    return tuple(out)


@dataclass(frozen=True)
class _Cup:
    """The cup BODY — everything except the handle.

    Factored out because `CUP` and `CUPNH` are the same structure read at two
    different moments: before a handle has formed, and after.
    """

    lp: int
    bp: int
    rp: int
    lh: float
    bl: float
    rh: float
    depth: float
    cup_len: int
    rounded: int


def _find_cup(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, end_hi: int, end_all: int
) -> _Cup | None:
    """The cup anchored to the highest qualifying prior peak, or None."""
    window_start = max(0, end_hi - MAX_CUP_BARS)

    # The left rim is a confirmed swing high old enough for a cup to have
    # formed to the right of it. Where SEVERAL qualify, take the HIGHEST —
    # the cup is a correction from a prior peak, and the peak is the rim.
    #
    # Keeping the best-SCORING candidate instead (the first version) quietly
    # reported the most flattering reading of every chart: PLTR's prior peak
    # is 207.52 on 2025-11-03, but anchoring to a later 187.28 swing high
    # scored better (a 43% cup with the right rim 4% ABOVE its left, rather
    # than a 49% cup still 6% BELOW it), so that is what it published. The
    # depth and rim-recovery bounds still apply, so a too-deep anchor is
    # rejected rather than flattered.
    candidates = _confirmed_pivots(h, 5, "max", window_start, end_hi - MIN_CUP_BARS)
    for lp in sorted(candidates, key=lambda i: h[i], reverse=True):
        lh = float(h[lp])
        if lh <= 0:
            continue
        # cup bottom: the lowest low since the left rim (today's low counts —
        # it only ever deepens the cup, it never creates the pivot)
        seg = l[lp + 1 : end_all + 1]
        if seg.size < 16:
            continue
        bp = lp + 1 + int(np.argmin(seg))
        bl = float(l[bp])
        depth = (lh - bl) / lh
        if not (0.12 <= depth <= 0.50):
            continue
        if bp - lp < 8 or end_hi - bp < 8:
            continue

        # right rim: the highest high since the bottom, excluding today
        rseg = h[bp + 1 : end_hi + 1]
        if rseg.size == 0:
            continue
        rp = bp + 1 + int(np.argmax(rseg))
        rh = float(h[rp])
        # the cup has to have come back to its rim (else it never completed),
        # and must not already have run away above it (that is an extended
        # breakout, not a base)
        if rh < lh * 0.90 or rh > lh * 1.05:
            continue

        cup_len = rp - lp
        if not (MIN_CUP_BARS <= cup_len <= MAX_CUP_BARS):
            continue
        # neither side may be a near-vertical wall: a V is not a cup
        if (bp - lp) < 0.20 * cup_len or (rp - bp) < 0.20 * cup_len:
            continue
        # roundness: time actually spent near the lows
        low_third = bl + 0.33 * (lh - bl)
        rounded = int((l[lp : rp + 1] <= low_third).sum())
        if rounded < max(3, int(0.12 * cup_len)):
            continue

        # Candidates are walked highest-rim-first, so the first body that
        # qualifies IS the prior peak's cup; nothing lower can be a more
        # faithful anchor, and falling through to one would re-introduce the
        # flattery this ordering exists to remove.
        return _Cup(lp=lp, bp=bp, rp=rp, lh=lh, bl=bl, rh=rh,
                    depth=depth, cup_len=cup_len, rounded=rounded)
    return None


def detect_cup_handle(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """O'Neil's cup-and-handle: a rounded 12-50% correction that recovers
    toward its left rim, then a shallow drift (the handle) in the upper half
    of the cup, on declining volume. The pivot is the right rim."""
    cup = _find_cup(h, l, c, end_hi, end_all)
    if cup is None:
        return None
    rp, rh, lh, bl = cup.rp, cup.rh, cup.lh, cup.bl

    handle_len = end_all - rp
    if not (MIN_HANDLE_BARS <= handle_len <= MAX_HANDLE_BARS):
        return None
    handle_low = float(l[rp + 1 : end_all + 1].min())
    handle_depth = (rh - handle_low) / rh
    # a handle is shallow, sits in the upper half of the cup, and never
    # retraces more than a third of it
    if not (MIN_HANDLE_DEPTH <= handle_depth <= MAX_HANDLE_DEPTH):
        return None
    if handle_depth > cup.depth / 3:
        return None
    if handle_low < lh - 0.5 * (lh - bl):
        return None
    # drift, not a plunge
    if handle_depth / handle_len > MAX_HANDLE_DRIFT_PER_BAR:
        return None

    cup_vol = _mean(v[cup.lp : rp + 1])
    handle_vol = _mean(v[rp + 1 : end_all + 1])
    dry_up = handle_vol / cup_vol if cup_vol and cup_vol == cup_vol else float("nan")
    # Volume drying up in the handle is not a bonus, it is the mechanism the
    # pattern claims: supply exhausting before the breakout. A handle on
    # heavier volume than the cup is distribution wearing the shape.
    if not (dry_up == dry_up) or dry_up >= 1.0:
        return None

    quality = float(
        np.mean([
            _band_score(cup.depth, 0.15, 0.35),            # classic depth
            _clip01(1 - abs(rh - lh) / lh / 0.10),         # rim symmetry
            _clip01(1 - handle_depth / MAX_HANDLE_DEPTH),  # tight handle
            _band_score(cup.cup_len, 35, 150),             # 7-30 weeks
            _clip01((1.0 - dry_up) / 0.4),                 # how hard volume dried
            _clip01(cup.rounded / max(1, 0.35 * cup.cup_len)),  # roundness
        ])
    )
    note = (
        f"cup {cup.depth * 100:.0f}% deep over {cup.cup_len} bars, "
        f"handle {handle_depth * 100:.1f}% over {handle_len}, "
        f"handle volume {dry_up:.2f}x cup"
    )
    return PatternMatch(
        code=CUP, pivot=rh, stop_ref=handle_low,
        measured_move=lh - bl,  # project the cup depth off the rim
        base_low=bl, base_high=max(lh, rh), start_pos=cup.lp, end_pos=end_all,
        depth_pct=cup.depth * 100, length_bars=end_all - cup.lp,
        quality=quality, note=note,
        flaws=_cup_flaws(
            h, l, c, depth=cup.depth, cup_len=cup.cup_len, lh=lh, rh=rh, bl=bl,
            bp=cup.bp, rp=rp, handle_depth=handle_depth, handle_len=handle_len,
            handle_low=handle_low, dry_up=dry_up,
        ),
    )


def detect_cup_no_handle(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """The same cup, read before a handle exists.

    O'Neil counts the cup-without-handle as its own base: price returns to the
    rim and breaks out directly, with no shakeout first. He treats it as the
    weaker of the two, which is why it is a separate code rather than a
    loosening of CUP.

    This fires ONLY when price is still pinned to the rim — the pullback since
    is too short or too shallow to be a handle. A deep or fast drop off the
    rim is a REJECTION, and deliberately matches nothing: that distinction is
    the whole reason the handle bounds were tightened.
    """
    cup = _find_cup(h, l, c, end_hi, end_all)
    if cup is None:
        return None
    rp, rh, lh, bl = cup.rp, cup.rh, cup.lh, cup.bl

    since_rim = end_all - rp
    low_since = float(l[rp + 1 : end_all + 1].min()) if since_rim >= 1 else float(l[rp])
    pullback = (rh - low_since) / rh
    # a handle that qualifies belongs to CUP; the two codes never both fire
    forming = since_rim < MIN_HANDLE_BARS or pullback < MIN_HANDLE_DEPTH
    if not forming:
        return None
    # ...but "no handle" must mean price is STILL AT the rim, not that it fell
    # away from it too fast to count
    if pullback > MIN_HANDLE_DEPTH * 2 or float(c[end_all]) < rh * 0.93:
        return None
    # the right side must have genuinely reached the rim: with no handle to
    # form, a cup still 10% short of its rim is just an unfinished advance
    if rh < lh * 0.97:
        return None

    base_low = min(low_since, float(l[max(rp - 5, cup.bp) : end_all + 1].min()))
    quality = float(
        np.mean([
            _band_score(cup.depth, 0.15, 0.35),
            _clip01(1 - abs(rh - lh) / lh / 0.10),
            _band_score(cup.cup_len, 35, 150),
            _clip01(cup.rounded / max(1, 0.35 * cup.cup_len)),
            0.7,  # a cup without a handle is the weaker variant, by definition
        ])
    )
    flaws = _cup_flaws(
        h, l, c, depth=cup.depth, cup_len=cup.cup_len, lh=lh, rh=rh, bl=bl,
        bp=cup.bp, rp=rp, handle_depth=pullback, handle_len=max(since_rim, 1),
        handle_low=low_since, dry_up=float("nan"), skip_handle=True,
    )
    return PatternMatch(
        code=CUPNH, pivot=rh, stop_ref=base_low,
        measured_move=lh - bl,
        base_low=bl, base_high=max(lh, rh), start_pos=cup.lp, end_pos=end_all,
        depth_pct=cup.depth * 100, length_bars=end_all - cup.lp,
        quality=quality,
        note=(
            f"cup {cup.depth * 100:.0f}% deep over {cup.cup_len} bars, no handle "
            f"yet — {since_rim} bars since the rim, {pullback * 100:.1f}% off it"
        ),
        flaws=flaws,
    )


# ----------------------------------------------------------- double bottom


def detect_double_bottom(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """Two lows at a similar level separated by a rally of 8% or more; the
    pivot is the middle peak. O'Neil prefers the second low to undercut the
    first (it shakes out the weak holders), which scores higher here."""
    best: PatternMatch | None = None
    lows = _confirmed_pivots(l, 5, "min", max(0, end_hi - 250), end_hi - 10)
    for a in range(len(lows)):
        i = lows[a]
        for b in range(a + 1, len(lows)):
            j = lows[b]
            span = j - i
            if not (15 <= span <= 160) or end_all - j < 5:
                continue
            li, lj = float(l[i]), float(l[j])
            if li <= 0 or abs(lj - li) / li > 0.05:
                continue  # the two lows must be at a comparable level
            mseg = h[i + 1 : j]
            if mseg.size == 0:
                continue
            mp = i + 1 + int(np.argmax(mseg))
            mh = float(h[mp])
            base_low = min(li, lj)
            if mh < base_low * 1.08:
                continue  # no real rally between the lows: just a flat range
            # the pivot must still be intact — nothing since the second low
            # may have cleared the middle peak by more than 3%
            after = h[j + 1 : end_hi + 1]
            if after.size and float(after.max()) > mh * 1.03:
                continue
            # ...and the second low must have HELD. Without this, any
            # oscillation qualifies: on a random walk this detector was
            # scoring 0.89 purely on the symmetry of two arbitrary lows.
            if float(l[j + 1 : end_all + 1].min()) < lj * 0.98:
                continue
            # the recovery leg can't drag on forever; past that the structure
            # is a year-old range, not a base being completed now
            if end_all - j > 80:
                continue
            # a double bottom is a CORRECTION of a prior advance, so there has
            # to be an advance to correct: a high at least 15% above the lows
            # within the 80 bars before the first one
            prior = h[max(0, i - 80) : i]
            if prior.size == 0 or float(prior.max()) < base_low * 1.15:
                continue

            depth = (mh - base_low) / mh
            undercut = lj < li  # the preferred shakeout
            hold_margin = float(l[j + 1 : end_all + 1].min()) / lj - 1
            quality = float(
                np.mean([
                    _clip01(1 - abs(lj - li) / li / 0.05),   # level symmetry
                    _band_score(depth, 0.12, 0.35),
                    _band_score(span, 25, 120),
                    1.0 if undercut else 0.6,
                    _band_score(hold_margin, 0.01, 0.10),    # the low held cleanly
                    _clip01((_mean(v[j - 3 : j + 1]) / _mean(v[i - 3 : i + 1])) * -1 + 1.6)
                    if _mean(v[i - 3 : i + 1]) else 0.5,     # drier second low
                ])
            )
            # The pivot is the highest high since the first low (excluding
            # today), which is usually the middle peak but not always: a push
            # 1-2% above it leaves the real resistance there, and quoting the
            # peak instead understates the level to clear.
            pivot = max(mh, float(after.max())) if after.size else mh
            match = PatternMatch(
                code=DBOT, pivot=pivot, stop_ref=lj,
                measured_move=mh - base_low,
                base_low=base_low, base_high=mh, start_pos=i, end_pos=end_all,
                depth_pct=depth * 100, length_bars=end_all - i,
                quality=quality,
                note=(
                    f"lows {li:.2f}/{lj:.2f} {span} bars apart"
                    f"{' (2nd undercuts)' if undercut else ''}, "
                    f"middle peak {mh:.2f}"
                ),
            )
            if best is None or match.quality > best.quality:
                best = match
    return best


# ------------------------------------------------------- flat base / Darvas

FLAT_LENGTHS = (25, 35, 45, 65)
MAX_FLAT_DEPTH = 0.15
MIN_PRIOR_ADVANCE = 0.20


def detect_flat_base(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """Darvas' box: after an advance of 20% or more, price goes sideways in a
    range shallower than 15% for five weeks or longer. The pivot is the box
    top. The measured move is the PRIOR ADVANCE, not the box height — a box
    is too shallow to project a worthwhile target on its own."""
    best: PatternMatch | None = None
    for box_len in FLAT_LENGTHS:
        s = end_hi - box_len + 1
        if s - 40 < 0:
            continue
        box_high = float(h[s : end_hi + 1].max())
        box_low = float(l[s : end_all + 1].min())
        if box_high <= 0:
            continue
        depth = (box_high - box_low) / box_high
        if depth > MAX_FLAT_DEPTH:
            continue
        # the box must cap an advance, not a decline
        pole_low = float(l[max(0, s - 60) : s].min())
        if pole_low <= 0:
            continue
        advance = (box_high - pole_low) / pole_low
        if advance < MIN_PRIOR_ADVANCE:
            continue
        # price sitting in the lower part of the box is a failing base, not a
        # flat one
        if float(c[end_all]) < box_low + 0.4 * (box_high - box_low):
            continue

        first_half = _mean(v[s : s + box_len // 2])
        second_half = _mean(v[s + box_len // 2 : end_all + 1])
        dry_up = second_half / first_half if first_half else float("nan")
        quality = float(
            np.mean([
                _clip01(1 - depth / MAX_FLAT_DEPTH),       # tighter is better
                _band_score(box_len, 35, 65),
                _band_score(advance, 0.25, 1.00),
                _clip01(1.3 - dry_up) if dry_up == dry_up else 0.5,
            ])
        )
        match = PatternMatch(
            code=FLAT, pivot=box_high, stop_ref=box_low,
            measured_move=box_high - pole_low,  # project the prior advance
            base_low=box_low, base_high=box_high, start_pos=s, end_pos=end_all,
            depth_pct=depth * 100, length_bars=box_len,
            quality=quality,
            note=(
                f"{box_len}-bar box {depth * 100:.1f}% deep after a "
                f"{advance * 100:.0f}% advance"
            ),
        )
        if best is None or match.quality > best.quality:
            best = match
    return best


# ------------------------------------------------------------- bull flag

FLAG_POLE_WINDOW = 45
MIN_FLAG_BARS, MAX_FLAG_BARS = 4, 35
MIN_POLE_GAIN = 0.20
MAX_FLAG_RETRACE = 0.40


def detect_bull_flag(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """A sharp advance (the pole) followed by a shallow, tight pause (the
    flag). The pivot is the pole high. A gain above 80% retracing less than a
    quarter is the 'high tight flag' — rare, and the strongest variant in
    O'Neil's work."""
    start = max(0, end_hi - FLAG_POLE_WINDOW)
    seg = h[start : end_hi + 1]
    if seg.size == 0:
        return None
    pole_end = start + int(np.argmax(seg))
    flag_len = end_all - pole_end
    if not (MIN_FLAG_BARS <= flag_len <= MAX_FLAG_BARS):
        return None
    ph = float(h[pole_end])
    pole_start = max(0, pole_end - 40)
    lseg = l[pole_start : pole_end + 1]
    if lseg.size == 0:
        return None
    ps = pole_start + int(np.argmin(lseg))
    pl = float(l[ps])
    if pl <= 0 or pole_end - ps < 3:
        return None
    pole_height = ph - pl
    gain = pole_height / pl
    if gain < MIN_POLE_GAIN:
        return None

    flag_low = float(l[pole_end + 1 : end_all + 1].min())
    retrace = (ph - flag_low) / pole_height if pole_height > 0 else float("nan")
    if not (retrace == retrace) or retrace > MAX_FLAG_RETRACE:
        return None

    # a flag contracts; a widening range after a pole is distribution
    half = pole_end + 1 + flag_len // 2
    r1 = _mean(h[pole_end + 1 : half] - l[pole_end + 1 : half])
    r2 = _mean(h[half : end_all + 1] - l[half : end_all + 1])
    contracting = r2 < r1 if (r1 == r1 and r2 == r2 and r1) else False

    high_tight = gain >= 0.80 and retrace <= 0.25
    pole_vol = _mean(v[ps : pole_end + 1])
    flag_vol = _mean(v[pole_end + 1 : end_all + 1])
    dry_up = flag_vol / pole_vol if pole_vol else float("nan")

    quality = float(
        np.mean([
            _band_score(gain, 0.30, 1.50),
            _clip01(1 - retrace / MAX_FLAG_RETRACE),
            _band_score(flag_len, 5, 20),
            1.0 if contracting else 0.5,
            _clip01(1.3 - dry_up) if dry_up == dry_up else 0.5,
            1.0 if high_tight else 0.7,
        ])
    )
    note = (
        f"{'high tight flag: ' if high_tight else ''}"
        f"{gain * 100:.0f}% pole in {pole_end - ps} bars, "
        f"flag retraced {retrace * 100:.0f}% over {flag_len}"
    )
    return PatternMatch(
        code=FLAG, pivot=ph, stop_ref=flag_low,
        measured_move=pole_height,  # flags project their pole
        base_low=flag_low, base_high=ph, start_pos=ps, end_pos=end_all,
        depth_pct=(ph - flag_low) / ph * 100, length_bars=end_all - ps,
        quality=quality, note=note,
    )


# ------------------------------------------------------ ascending triangle


def detect_ascending_triangle(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """Flat resistance tested twice or more against rising lows. The pivot is
    the resistance; the measured move is the triangle at its widest."""
    start = max(0, end_hi - 120)
    highs = _confirmed_pivots(h, 4, "max", start, end_hi)
    lows = _confirmed_pivots(l, 4, "min", start, end_hi)
    if len(highs) < 2 or len(lows) < 2:
        return None

    # Three touches, not two. With two, any pullback inside an uptrend
    # qualifies: on a 400-symbol US sweep the two-touch version matched 25
    # charts, most of them plain uptrends with one pause (DE's "triangle" had
    # lows rising 565 to 665 under a single retest).
    top_candidates = highs[-3:]
    if len(top_candidates) < 3:
        return None
    tops = [float(h[p]) for p in top_candidates]
    resistance = max(tops)
    # "flat" means every tested high is within 3% of the highest
    if min(tops) < resistance * 0.97:
        return None

    structure_start = min(top_candidates[0], lows[0])
    span = end_hi - structure_start
    if span < 25:
        return None
    rising = [p for p in lows if p >= structure_start]
    if len(rising) < 2:
        return None
    first_low, last_low = float(l[rising[0]]), float(l[rising[-1]])
    if last_low <= first_low * 1.01:
        return None  # lows must actually rise
    # the apex must still be ahead: price through resistance by >3% is a
    # completed (and probably extended) breakout, not a triangle
    after = h[top_candidates[-1] + 1 : end_hi + 1]
    if after.size and float(after.max()) > resistance * 1.03:
        return None

    height = resistance - first_low
    if height <= 0:
        return None
    # the triangle must have been a triangle: a real gap to close at the left
    # edge, and lows that have since closed most of it without passing the apex
    if height / resistance < 0.06:
        return None
    convergence = 1 - (resistance - last_low) / height  # 0 at the base, 1 at the apex
    if not (0.40 <= convergence <= 0.92):
        return None
    quality = float(
        np.mean([
            _clip01(1 - (resistance - min(tops)) / resistance / 0.03),  # flatness
            _band_score(span, 30, 100),
            _band_score(convergence, 0.5, 0.85),
            _band_score(height / resistance, 0.08, 0.30),
        ])
    )
    pivot = resistance
    if after.size:
        pivot = max(pivot, float(after.max()))
    return PatternMatch(
        code=ATRI, pivot=pivot, stop_ref=last_low,
        measured_move=height,
        base_low=first_low, base_high=resistance,
        start_pos=structure_start, end_pos=end_all,
        depth_pct=height / resistance * 100, length_bars=span,
        quality=quality,
        note=(
            f"{len(top_candidates)} highs within 3% of {resistance:.2f}, "
            f"lows rising {first_low:.2f} to {last_low:.2f}"
        ),
    )


# --------------------------------------------- volatility contraction (VCP)

MIN_CONTRACTIONS = 2
MAX_LAST_CONTRACTION = 0.12
TIGHTENING_RATIO = 0.80


def detect_vcp(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """Minervini's VCP: a sequence of pullbacks, each materially tighter than
    the one before (e.g. 25% then 15% then 8%), on drying volume. The pivot
    is the high of the final, tightest contraction."""
    start = max(0, end_hi - 140)
    pivots = sorted(
        [(p, "H") for p in _confirmed_pivots(h, 4, "max", start, end_hi)]
        + [(p, "L") for p in _confirmed_pivots(l, 4, "min", start, end_hi)]
    )
    if len(pivots) < 3:
        return None

    # walk the pivot list keeping a strict H,L,H,L... alternation; where two
    # of a kind run together keep the more extreme one
    chain: list[tuple[int, str]] = []
    for pos, kind in pivots:
        if chain and chain[-1][1] == kind:
            prev_pos = chain[-1][0]
            better = (
                h[pos] > h[prev_pos] if kind == "H" else l[pos] < l[prev_pos]
            )
            if better:
                chain[-1] = (pos, kind)
            continue
        chain.append((pos, kind))
    while chain and chain[0][1] == "L":
        chain.pop(0)
    if len(chain) < 3:
        return None

    contractions: list[tuple[int, int, float]] = []  # (high_pos, low_pos, depth)
    for idx in range(0, len(chain) - 1, 2):
        hp, hk = chain[idx]
        lp, lk = chain[idx + 1]
        if hk != "H" or lk != "L":
            break
        top = float(h[hp])
        if top <= 0:
            break
        contractions.append((hp, lp, (top - float(l[lp])) / top))
    if len(contractions) < MIN_CONTRACTIONS:
        return None

    # keep only the tail of the sequence that is strictly tightening
    kept = [contractions[-1]]
    for prev in reversed(contractions[:-1]):
        if kept[0][2] <= prev[2] * TIGHTENING_RATIO:
            kept.insert(0, prev)
        else:
            break
    if len(kept) < MIN_CONTRACTIONS:
        return None
    if kept[-1][2] > MAX_LAST_CONTRACTION:
        return None

    first_high_pos, _, first_depth = kept[0]
    last_high_pos, last_low_pos, last_depth = kept[-1]
    # the pivot is the final contraction's high, or any higher high printed
    # since its low (still excluding today's bar)
    after = h[last_low_pos + 1 : end_hi + 1]
    pivot = float(h[last_high_pos])
    if after.size:
        pivot = max(pivot, float(after.max()))
    base_low = float(l[min(p[1] for p in kept) : end_all + 1].min())
    base_high = float(h[first_high_pos])
    if base_high <= 0 or pivot <= 0:
        return None

    early_vol = _mean(v[first_high_pos : kept[0][1] + 1])
    late_vol = _mean(v[last_high_pos : end_all + 1])
    dry_up = late_vol / early_vol if early_vol else float("nan")
    quality = float(
        np.mean([
            _clip01(1 - last_depth / MAX_LAST_CONTRACTION),
            _band_score(len(kept), 3, 4),
            _clip01(1 - last_depth / max(first_depth, 1e-9) / TIGHTENING_RATIO),
            _clip01(1.3 - dry_up) if dry_up == dry_up else 0.5,
        ])
    )
    seq = " to ".join(f"{d * 100:.0f}%" for _, _, d in kept)
    return PatternMatch(
        code=VCP, pivot=pivot, stop_ref=float(l[last_low_pos]),
        measured_move=base_high - base_low,
        base_low=base_low, base_high=base_high,
        start_pos=first_high_pos, end_pos=end_all,
        depth_pct=(base_high - base_low) / base_high * 100,
        length_bars=end_all - first_high_pos,
        quality=quality,
        note=f"{len(kept)} contractions, {seq}"
        + (f", volume {dry_up:.2f}x" if dry_up == dry_up else ""),
    )


# ------------------------------------------------- topping structures

# A top is only a top once the market agrees: two highs at a level with price
# still pressed against them is RESISTANCE (and often an ascending triangle),
# not a reversal. What separates them is the trough between the peaks — the
# neckline. Until it breaks, the structure is forming; after it breaks, the
# pattern has done what it describes.
MIN_TOP_SEPARATION, MAX_TOP_SEPARATION = 15, 160
TOP_LEVEL_TOL = 0.03      # the two peaks count as "equal" within this
MIN_NECK_DEPTH = 0.08     # the trough must be a real decline, not a pause


# A top is only worth vetoing on while it is LIVE. Three ways one dies, all
# of them seen in the first live run of these detectors:
#   * price takes out the last peak      -> it was resistance, not a top
#     (PLTR: "confirmed H&S, head 207.52" while price sat at 188 having
#      already cleared the 187.28 right shoulder);
#   * the neckline break fails and price recovers above it
#     (DOCU: "confirmed, neckline 63.50" with price back at 69.01);
#   * the whole structure is simply old
#     (TECH: a neckline of 48.25 against a 72.40 price).
MAX_TOP_AGE = 90          # bars since the last peak
TOP_ROLLOVER = 0.95       # a forming top must have turned down this far


def _top_state(
    h: np.ndarray, c: np.ndarray, *, last_peak_pos: int, last_peak: float,
    neckline: float, end_hi: int, end_all: int,
) -> str | None:
    """'confirmed', 'forming', or None when the structure is dead."""
    if end_all - last_peak_pos > MAX_TOP_AGE:
        return None
    after_h = h[last_peak_pos + 1 : end_hi + 1]
    if after_h.size and float(after_h.max()) > last_peak * 1.01:
        return None  # the level broke: this was resistance, not a reversal
    after_c = c[last_peak_pos + 1 : end_all + 1]
    if after_c.size == 0:
        return None
    broke = float(after_c.min()) < neckline
    close = float(c[end_all])
    if broke:
        # a break that price has since recovered is a FAILED top, which is a
        # bullish event — vetoing a long on it would be exactly backwards
        return "confirmed" if close < neckline else None
    # Not yet broken: only a veto once price has actually rolled over, which
    # has to mean MORE than "it pulled back". A cup's left and right rims ARE
    # two peaks at one level with a trough between them — GILD's cup matched
    # its own geometry as a "forming double top" — so until price has given
    # back half the distance from the peak to the neckline, the decline is
    # indistinguishable from a handle and calling it a top is overreach.
    midpoint = neckline + (last_peak - neckline) / 2
    return "forming" if close < min(last_peak * TOP_ROLLOVER, midpoint) else None


def detect_double_top(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """Two peaks at the same level with a meaningful trough between them.

    Bearish, so the fields carry their mirrored meaning: `pivot` is the
    NECKLINE (the level whose break confirms the top), `stop_ref` is the peak,
    and `measured_move` is the projected decline, not a target above.
    """
    highs = _confirmed_pivots(h, 5, "max", max(0, end_hi - 250), end_hi - 5)
    best: PatternMatch | None = None
    for a in range(len(highs)):
        i = highs[a]
        for b in range(a + 1, len(highs)):
            j = highs[b]
            span = j - i
            if not (MIN_TOP_SEPARATION <= span <= MAX_TOP_SEPARATION):
                continue
            hi_, hj = float(h[i]), float(h[j])
            top = max(hi_, hj)
            if top <= 0 or abs(hj - hi_) / hi_ > TOP_LEVEL_TOL:
                continue
            tseg = l[i + 1 : j]
            if tseg.size == 0:
                continue
            tp = i + 1 + int(np.argmin(tseg))
            neck = float(l[tp])
            if (top - neck) / top < MIN_NECK_DEPTH:
                continue
            status = _top_state(
                h, c, last_peak_pos=j, last_peak=float(h[j]), neckline=neck,
                end_hi=end_hi, end_all=end_all,
            )
            if status is None:
                continue
            quality = float(
                np.mean([
                    _clip01(1 - abs(hj - hi_) / hi_ / TOP_LEVEL_TOL),  # level match
                    _band_score((top - neck) / top, 0.10, 0.30),
                    _band_score(span, 20, 120),
                    1.0 if status == "confirmed" else 0.6,
                ])
            )
            match = PatternMatch(
                code=DTOP, pivot=neck, stop_ref=top,
                measured_move=top - neck,  # projected DOWN from the neckline
                base_low=neck, base_high=top, start_pos=i, end_pos=end_all,
                depth_pct=(top - neck) / top * 100, length_bars=end_all - i,
                quality=quality,
                note=(
                    f"{status}: peaks {hi_:.2f}/{hj:.2f} {span} bars apart, "
                    f"neckline {neck:.2f}"
                ),
            )
            if best is None or match.quality > best.quality:
                best = match
    return best


def detect_head_shoulders_top(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """Three peaks, the middle one highest, shoulders roughly level.

    Same mirrored field meanings as `detect_double_top`. The neckline is taken
    as the LOWER of the two troughs — the conservative reading, since that is
    the level a close must break for the pattern to have completed on any
    drawing of it.
    """
    highs = _confirmed_pivots(h, 5, "max", max(0, end_hi - 250), end_hi - 5)
    if len(highs) < 3:
        return None
    best: PatternMatch | None = None
    for a in range(len(highs) - 2):
        for b in range(a + 1, len(highs) - 1):
            for d in range(b + 1, len(highs)):
                ls, hd, rs = highs[a], highs[b], highs[d]
                lsh, head, rsh = float(h[ls]), float(h[hd]), float(h[rs])
                if head <= 0 or rs - ls > MAX_TOP_SEPARATION * 2:
                    continue
                # the head must stand clear of both shoulders, but not so far
                # that they are not shoulders at all: GILD matched with
                # shoulders 18% under its head, which is a spike with two
                # unrelated bumps beside it
                if lsh > head * 0.97 or rsh > head * 0.97:
                    continue
                if lsh < head * 0.85 or rsh < head * 0.85:
                    continue
                # ...and the shoulders must be roughly level with each other
                if abs(rsh - lsh) / lsh > 0.05:
                    continue
                t1 = l[ls + 1 : hd]
                t2 = l[hd + 1 : rs]
                if t1.size == 0 or t2.size == 0:
                    continue
                neck = min(float(t1.min()), float(t2.min()))
                if (head - neck) / head < MIN_NECK_DEPTH:
                    continue
                status = _top_state(
                    h, c, last_peak_pos=rs, last_peak=rsh, neckline=neck,
                    end_hi=end_hi, end_all=end_all,
                )
                if status is None:
                    continue
                quality = float(
                    np.mean([
                        _clip01(1 - abs(rsh - lsh) / lsh / 0.05),   # shoulder symmetry
                        _clip01((head - max(lsh, rsh)) / head / 0.08),  # head clearance
                        _band_score((head - neck) / head, 0.10, 0.35),
                        1.0 if status == "confirmed" else 0.6,
                    ])
                )
                match = PatternMatch(
                    code=HSTOP, pivot=neck, stop_ref=head,
                    measured_move=head - neck,
                    base_low=neck, base_high=head, start_pos=ls, end_pos=end_all,
                    depth_pct=(head - neck) / head * 100, length_bars=end_all - ls,
                    quality=quality,
                    note=(
                        f"{status}: shoulders {lsh:.2f}/{rsh:.2f}, head {head:.2f}, "
                        f"neckline {neck:.2f}"
                    ),
                )
                if best is None or match.quality > best.quality:
                    best = match
    return best


# ------------------------------------------------------------- entry point

_DETECTORS = (
    detect_cup_handle,
    detect_cup_no_handle,
    detect_double_bottom,
    detect_flat_base,
    detect_bull_flag,
    detect_ascending_triangle,
    detect_vcp,
)


_TOPPING_DETECTORS = (
    detect_double_top,
    detect_head_shoulders_top,
)


def detect_topping(daily: pd.DataFrame) -> list[PatternMatch]:
    """Topping structures only — for vetoing a long or marking an exit.

    Kept behind its own call so a bearish match can never reach code that
    builds entries: `detect_patterns` returns bullish bases unless explicitly
    asked otherwise.
    """
    return [m for m in detect_patterns(daily, include_topping=True) if m.is_bearish]


def detect_patterns(
    daily: pd.DataFrame, *, include_topping: bool = False
) -> list[PatternMatch]:
    """Every pattern present as of `daily`'s last bar, best quality first.

    Several patterns can describe the same chart (a VCP is often also a
    cup-and-handle); all matches are returned so a report can show what was
    seen, and the caller picks which one to trade.
    """
    if daily is None or len(daily) < MIN_BARS:
        return []
    h = daily["high"].to_numpy(dtype=float)
    l = daily["low"].to_numpy(dtype=float)
    c = daily["close"].to_numpy(dtype=float)
    v = daily["volume"].to_numpy(dtype=float)
    if not np.isfinite(h[-30:]).all() or not np.isfinite(l[-30:]).all():
        return []

    end_all = len(daily) - 1   # today: usable for lows and volume
    end_hi = end_all - 1       # last bar allowed to define a pivot

    found: list[PatternMatch] = []
    for detector in (_DETECTORS + (_TOPPING_DETECTORS if include_topping else ())):
        try:
            match = detector(h, l, c, v, end_hi, end_all)
        except (IndexError, ValueError, ZeroDivisionError):
            match = None
        if match is not None and match.pivot > 0 and match.measured_move > 0:
            found.append(match)
    return sorted(found, key=lambda m: m.quality, reverse=True)
