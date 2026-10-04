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
deep, handle no more than a third of the cup, flat base under 15% over five
weeks or more, flag retracing under 40% of its pole, each VCP contraction
tighter than the last). They are NOT tuned on this repository's data and no
pattern here has been backtested. Treat a match as a hypothesis.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

# pattern codes — these double as a strategy's setup codes, so keep them
# short, uppercase and stable (they become report column names)
CUP = "CUP"    # cup-and-handle
DBOT = "DBOT"  # double bottom (W)
FLAT = "FLAT"  # flat base / Darvas box
FLAG = "FLAG"  # bull flag (incl. high tight flag)
ATRI = "ATRI"  # ascending triangle
VCP = "VCP"    # volatility contraction pattern

ALL_CODES: tuple[str, ...] = (CUP, DBOT, FLAT, FLAG, ATRI, VCP)

PATTERN_NAMES = {
    CUP: "cup-and-handle",
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

    @property
    def name(self) -> str:
        return PATTERN_NAMES.get(self.code, self.code)

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
MIN_HANDLE_BARS, MAX_HANDLE_BARS = 3, 40


def detect_cup_handle(
    h: np.ndarray, l: np.ndarray, c: np.ndarray, v: np.ndarray, end_hi: int, end_all: int
) -> PatternMatch | None:
    """O'Neil's cup-and-handle: a rounded 12-50% correction that recovers to
    within ~10% of its left rim, then a shallow drift (the handle) in the
    upper half of the cup. The pivot is the right rim."""
    best: PatternMatch | None = None
    window_start = max(0, end_hi - MAX_CUP_BARS)

    # the left rim is a confirmed swing high old enough for a cup to have
    # formed to the right of it
    for lp in _confirmed_pivots(h, 5, "max", window_start, end_hi - MIN_CUP_BARS):
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

        # handle: everything after the right rim
        handle_len = end_all - rp
        if not (MIN_HANDLE_BARS <= handle_len <= MAX_HANDLE_BARS):
            continue
        handle_low = float(l[rp + 1 : end_all + 1].min())
        handle_depth = (rh - handle_low) / rh
        # a handle is shallow, sits in the upper half of the cup, and never
        # retraces more than a third of it
        if handle_depth > 0.15 or handle_depth > depth / 3:
            continue
        if handle_low < lh - 0.5 * (lh - bl):
            continue

        cup_vol = _mean(v[lp : rp + 1])
        handle_vol = _mean(v[rp + 1 : end_all + 1])
        dry_up = handle_vol / cup_vol if cup_vol and cup_vol == cup_vol else float("nan")

        quality = float(
            np.mean([
                _band_score(depth, 0.15, 0.35),              # classic depth
                _clip01(1 - abs(rh - lh) / lh / 0.10),       # rim symmetry
                _clip01(1 - handle_depth / 0.15),            # tight handle
                _band_score(cup_len, 35, 150),               # 7-30 weeks
                _clip01(1.3 - dry_up) if dry_up == dry_up else 0.5,  # volume dry-up
                _clip01(rounded / max(1, 0.35 * cup_len)),   # roundness
            ])
        )
        note = (
            f"cup {depth * 100:.0f}% deep over {cup_len} bars, "
            f"handle {handle_depth * 100:.1f}% over {handle_len}"
        )
        if dry_up == dry_up:
            note += f", handle volume {dry_up:.2f}x cup"
        match = PatternMatch(
            code=CUP, pivot=rh, stop_ref=handle_low,
            measured_move=lh - bl,  # project the cup depth off the rim
            base_low=bl, base_high=max(lh, rh), start_pos=lp, end_pos=end_all,
            depth_pct=depth * 100, length_bars=end_all - lp,
            quality=quality, note=note,
        )
        if best is None or match.quality > best.quality:
            best = match
    return best


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


# ------------------------------------------------------------- entry point

_DETECTORS = (
    detect_cup_handle,
    detect_double_bottom,
    detect_flat_base,
    detect_bull_flag,
    detect_ascending_triangle,
    detect_vcp,
)


def detect_patterns(daily: pd.DataFrame) -> list[PatternMatch]:
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
    for detector in _DETECTORS:
        try:
            match = detector(h, l, c, v, end_hi, end_all)
        except (IndexError, ValueError, ZeroDivisionError):
            match = None
        if match is not None and match.pivot > 0 and match.measured_move > 0:
            found.append(match)
    return sorted(found, key=lambda m: m.quality, reverse=True)
