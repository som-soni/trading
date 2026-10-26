"""SUPPORT AND RESISTANCE ZONES — horizontal levels drawn by one written procedure.

The chart's Support & Resistance indicator draws what this module returns (/api/sr-levels); the rules
live here only, never in JavaScript. The procedure, top to bottom:

1. **Timeframe stack.** Start on the higher timeframe ({STACK}), then add the chart's own timeframe.
   Each looks back far enough to show several major swings ({TF}).
2. **Turning points that earned it.** A swing high / low is a bar beyond its neighbours on both sides
   (`swing` bars each side). It counts only if price then moved away clearly: a close at least
   {MIN_REACTION_ATR} ATR from the extreme within `reaction` bars. A lone giant spike bar (range over
   {SPIKE_ATR} ATR) with no second reaction draws no level.
3. **Cluster, then draw each zone from the structure.** Reactions spread over more than {SPLIT_ATR} ATR are
   separate levels (the sorted turning prices are split at their widest gaps until each group fits). A
   zone spans what price did there — from the wick extremes to the body cluster (the median body edge of
   the turning bars); a lone wick — more than {OUTLIER_ATR} ATR from its neighbour and twice as far as the
   rest are wide — is ignored and is not a touch (evenly spread turns have none).
   Height is never stretched or trimmed to an ATR band. Touches are distinct visits: a new one counts
   only after price closed {DEPART_ATR} ATR outside the zone. The reference line is where the reactions
   concentrate (their median turning price), not the midpoint.
4. **Refine the higher timeframe with the finer one.** A weekly zone is redrawn from the daily turning
   points inside it over its own (weekly) look-back (finer structure; a weekly bar's body sits far from its
   wick), keeping its weekly standing and starting at its first visit — or, when price has crossed the whole
   box again and again, as the separate daily reaction
   clusters inside it that price still respects. If price has also lived inside the box ({CONGESTION_SHARE:.0%}+
   of bars), the box is returned as a **congestion band**: context, not a level. A daily zone at least
   {OVERLAP_SHARE:.0%} inside a higher-timeframe zone is left to it; one that merely overlaps it is kept.
5. **Usable on the chart you are reading.** A zone taller than {WIDE_ATR} ATR of the chart's timeframe
   is split at its widest internal gap, when each part stands on its own (two visits, or one strong
   rejection); a part that no longer earns a level is retired; a zone that cannot be split is flagged
   wide. Same-role zones less than {MERGE_GAP_ATR} ATR
   apart become one zone with both reference lines — only if the result is not too tall to use.
   Height ÷ the ATR of the zone's own timeframe is reported as the check.
6. **Role from where price is now.** Below price: support. Above: resistance. Price inside, or within
   {AT_PRICE_ATR} daily ATR of it ("at price", the same distance on every chart): a **pivot** — support while price holds above it, resistance
   once it closes below. A zone price has closed inside on {CONGESTION_SHARE:.0%}+ of the bars since it
   formed is a **congestion zone**: an area price lives in, not a clean ceiling or floor. A zone whose first reaction
   was the opposite role is marked as reversed ("Support (was resistance)").
7. **Grade it** — one point per factor (`FACTORS`); a zone needs {MIN_SCORE} points, and two reactions
   or one strong one. {STRONG_SCORE}+ is strong. {WORN_TOUCHES}+ visits is flagged worn. A zone price has
   crossed {STALE_CROSSES}+ times since its last reaction is dropped.
8. **Few, near and earned.** Key levels lie within {RELEVANCE_ATR} ATR of price (chart timeframe) and
   score {KEY_MIN_SCORE}+ (a daily one with two visits): any pivot, the nearest qualifying zone each side,
   then the best of the rest by score — up to {MAX_KEY} in all, {MAX_PER_SIDE} a side, none if none
   qualifies. Price more than {GAP_ATR} ATR from its nearest key zone promotes the best graded zone in the
   gap, or marks the next round number. Same-role zones that overlap or nearly touch become one zone (the
   coarser timeframe's, each visit once) before key levels are chosen — unless it would be taller than
   {CAP_ATR} ATR, when overlapping ones keep the better; zones of different roles never merge. A zone still
   taller than {CAP_ATR} ATR of its own timeframe is cut back to its body side, keeping the visits that came
   to it (none left: no level). Weekly / monthly zones beyond the window whose 3+
   reactions span {LONG_TERM_SPAN_YEARS}+ years, within a factor of {LONG_TERM_RANGE} of price, are returned as
   long-term levels, the best {LONG_TERM_PER_SIDE} a side. The 52-week (and, near price, all-time) high
   and low are marked as provisional levels: a fresh extreme has no confirmed swing yet.
9. **Context lines**: the previous period's high and low; at an all-time high, where no resistance
   exists, the next round number above (never an invented level). With earnings within
   {EARNINGS_WARN_SESSIONS} sessions the chart says so: a report often carries price straight through
   nearby levels.

Levels describe where price reacted; they make no trade decision.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd

from . import indicators as ind
from . import swings as sw

TF = {   # per timeframe: look-back, swing strength, bars to judge the reaction, "recent", bar average for volume
    "M": {"years": 20, "swing": 2, "reaction": 2, "recent": 24, "vol": 12},
    "W": {"years": 5, "swing": 3, "reaction": 3, "recent": 52, "vol": 20},
    "D": {"years": 1.5, "swing": 5, "reaction": 5, "recent": 126, "vol": 20},
}
STACK = {"D": ("W", "D"), "W": ("M", "W"), "M": (None, "M")}   # chart timeframe -> (higher, own); monthly is the top
NAMES = {"M": "monthly", "W": "weekly", "D": "daily"}
ATR_BARS = 14
MIN_REACTION_ATR = 1.0      # a turning point counts when price closed this far away within `reaction` bars
STRONG_REJECTION_ATR = 2.0  # ... and is a strong rejection at this distance
SPIKE_ATR = 3.0             # a bar wider than this is a spike: alone, it draws no level
SPLIT_ATR = 1.0             # reaction extremes spread wider than this are separate levels
WIDE_ATR = 1.0              # taller than this (the chart timeframe's ATR) is too tall to use: split, else flagged
DEPART_ATR = 0.5            # a new visit: price closed at least this far outside the zone since the last reaction
MERGE_GAP_ATR = 0.5         # two same-role zones closer than this are one area, with two reference levels
OUTLIER_ATR = 0.5           # a lone wick this far beyond the rest is ignored
VOLUME_HIGH = 1.5           # reaction volume vs the prior bars' average, for the volume point
MIN_SCORE = 3               # points to keep a zone ...
STRONG_SCORE = 5            # ... and to call it strong
WORN_TOUCHES = 5            # visits at which a level is more likely to break than hold
STALE_CROSSES = 3           # closes through a zone since its last reaction that retire it
MAX_PER_SIDE = 4            # key zones each side of price, at most ...
MAX_KEY = 7                 # ... and in all (pivots included) — not a quota: a side may have none
KEY_MIN_SCORE = 4           # a key zone scores at least this; a daily one also needs two visits
RELEVANCE_ATR = {"D": 8, "W": 6, "M": 5}   # key zones lie within this many ATR of price (chart timeframe)
GAP_ATR = 3                 # price this far from its nearest key zone: promote a hidden level in the gap
CAP_ATR = 1.0               # a zone still taller than this (its own timeframe's ATR) is cut back to its body side
OVERLAP_SHARE = 0.5         # a chart-timeframe zone at least this much inside a higher-timeframe one is left to it
LONG_TERM_PER_SIDE = 3      # long-term levels beyond the relevance window, shown muted, each side ...
LONG_TERM_SPAN_YEARS = 1.5  # ... a weekly / monthly zone whose reactions span at least this long ...
LONG_TERM_RANGE = 2.0       # ... within this factor of price (half to double it): a 2006 low at a hundredth of it says nothing
ATH_NEAR_PCT = 3.0          # within this of the all-time high: no historical resistance above
AT_PRICE_ATR = 0.25         # a zone within this of the close (chart timeframe's ATR) is "at price": a pivot
CONGESTION_SHARE = 0.3      # price closed inside the zone on at least this share of bars since it formed: congestion
EARNINGS_WARN_SESSIONS = 10 # earnings this close: levels near price are less reliable through the report

FACTORS = {
    "timeframe": "Found on the weekly or monthly chart",
    "rejection": f"Strong rejection — price closed {STRONG_REJECTION_ATR} ATR away within a few bars",
    "reversal": "Role reversal — acted as both support and resistance",
    "touches": "Two or more distinct visits",
    "volume": f"High volume on a reaction — at least {VOLUME_HIGH}× the prior bars' average",
    "confluence": "Confluence — a round number or the 50- or 200-bar average inside the zone",
    "recency": "Recent — a reaction within the last year or so of bars",
}


def bars(daily: pd.DataFrame, tf: str) -> pd.DataFrame:
    """`daily` as `tf` bars, each dated by its last real session (as the chart dates them)."""
    daily = daily[~((daily["volume"] <= 0) & (daily["high"] <= daily["low"]))]   # holiday prints
    if tf == "D":
        return daily
    rule = "W-FRI" if tf == "W" else "ME"
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    last = daily.index.to_series().resample(rule).last()
    out = daily.resample(rule).agg(agg).dropna(subset=["close"])
    out.index = pd.DatetimeIndex(last.reindex(out.index).values)
    return out


def round_step(price: float) -> float:
    """The round-number spacing for a price: a tenth of it, rounded down to 1 or 5 times a power of ten
    (1,389 -> 100; 226 -> 10; 75 -> 5)."""
    raw = price / 10
    p = 10 ** math.floor(math.log10(raw))
    step = 5 * p if raw >= 5 * p else p
    return step


def _turning_points(df: pd.DataFrame, tf: str) -> list[dict]:
    c = TF[tf]
    o, h, l, cl, v = (df[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    atr = ind.atr(df, ATR_BARS).to_numpy(float)
    hi = sw.swing_high_mask(df["high"], c["swing"], c["swing"]).to_numpy()
    lo = sw.swing_low_mask(df["low"], c["swing"], c["swing"]).to_numpy()
    vavg = pd.Series(v).rolling(c["vol"]).mean().shift(1).to_numpy(float)
    dates = [d.date().isoformat() for d in df.index]
    out = []
    for i in range(len(df)):
        a = atr[i]
        if not (a == a and a > 0) or not (hi[i] or lo[i]):
            continue
        after = cl[i + 1:i + 1 + c["reaction"]]
        if not len(after):
            continue
        for kind in ("H", "L") if hi[i] and lo[i] else (("H",) if hi[i] else ("L",)):
            w = h[i] if kind == "H" else l[i]
            b = max(o[i], cl[i]) if kind == "H" else min(o[i], cl[i])
            move = (w - after.min()) if kind == "H" else (after.max() - w)
            vr = [v[k] / vavg[k] for k in range(i, min(len(v), i + 2)) if vavg[k] == vavg[k] and vavg[k] > 0]
            out.append({"i": i, "date": dates[i], "kind": kind, "wick": float(w), "body": float(b),
                        "reaction_atr": float(move / a), "spike": bool((h[i] - l[i]) / a >= SPIKE_ATR),
                        "volume": float(max(vr)) if vr else None})
    return [p for p in out if p["reaction_atr"] >= MIN_REACTION_ATR]


def _edges(g: list[dict], u: float) -> tuple[float, float, list[dict]]:
    """A zone from the structure of its turning points: the wick extremes (a lone wick beyond the rest
    dropped) and the median body edge. Nothing is stretched or trimmed. Returns the edges and the turning
    points kept — a dropped spike is not a touch either.

    A lone wick stands apart from a cluster: more than OUTLIER_ATR from its neighbour, and more than twice
    as far as the rest are wide. Evenly spread turning points have none (dropping both ends of three such
    points once left a zone of one price), and at least two points always stay."""
    pts = sorted(g, key=lambda p: p["wick"])

    def gap(end: int) -> float:
        return pts[1]["wick"] - pts[0]["wick"] if end == 0 else pts[-1]["wick"] - pts[-2]["wick"]
    for end in sorted((0, -1), key=gap, reverse=True) if len(pts) >= 3 else ():
        if len(pts) < 3:
            break
        rest = pts[1:] if end == 0 else pts[:-1]
        if gap(end) > OUTLIER_ATR * u and gap(end) > 2 * (rest[-1]["wick"] - rest[0]["wick"]):
            pts = rest
    body = float(np.median([p["body"] for p in pts]))
    return min(pts[0]["wick"], body), max(pts[-1]["wick"], body), pts


def _visits(touches: list[dict], cl: np.ndarray, lo: float, hi: float, u: float) -> list[dict]:
    """Distinct approaches, not every turning point of one long stay: consecutive reactions are one visit
    unless price closed at least DEPART_ATR outside the zone between them. Each visit is represented by
    its strongest reaction."""
    out: list[list[dict]] = []
    for p in sorted(touches, key=lambda p: p["i"]):
        if out:
            between = cl[out[-1][-1]["i"] + 1:p["i"]]
            left = len(between) and ((between > hi + DEPART_ATR * u).any() or (between < lo - DEPART_ATR * u).any())
            if not left:
                out[-1].append(p)
                continue
        out.append([p])
    return [max(v, key=lambda p: p["reaction_atr"]) for v in out]


@dataclass
class _Frame:
    """One timeframe's bars and the measures every zone drawn on them needs."""
    tf: str
    df: pd.DataFrame
    close: float                      # the chart's last close (role and distance are judged against it)
    conf: list[float]                 # moving averages, for the confluence point
    cl: np.ndarray = field(init=False)
    ap: float = field(init=False)     # ATR as a share of price
    pts: list[dict] = field(init=False)
    first: int = field(init=False)    # first bar of the look-back
    all_pts: list[dict] = field(init=False)   # every turning point, look-back or not (for refining a coarser zone)

    def __post_init__(self):
        self.cl = self.df["close"].to_numpy(float)
        self.ap = float(ind.atr(self.df, ATR_BARS).iloc[-1]) / float(self.df["close"].iloc[-1])
        cut = self.df.index[-1] - pd.DateOffset(months=int(TF[self.tf]["years"] * 12))
        self.first = int(np.searchsorted(self.df.index.values, np.datetime64(cut)))
        self.all_pts = _turning_points(self.df, self.tf)
        self.pts = [p for p in self.all_pts if p["i"] >= self.first]

    def since(self, date: pd.Timestamp) -> list[dict]:
        """Turning points on these bars from `date` on — a coarser zone is refined over its own look-back
        (five years of daily points for a weekly zone), not this frame's shorter one."""
        i = int(np.searchsorted(self.df.index.values, np.datetime64(date)))
        return [p for p in self.all_pts if p["i"] >= i]

    def unit(self, price: float) -> float:
        """One ATR at `price` (ATR as a share of price, applied at the zone's own level: a stock that went
        from 30 to 2,000 must not get 200-point zones down at 30)."""
        return self.ap * price


def _zone(pts: list[dict], fr: _Frame, tf: str, accept: bool = True) -> dict | None:
    """One zone from turning points `pts` on frame `fr`, standing as a `tf` level: its edges, visits, role,
    grade. None when it does not earn a level (or, with `accept`, does not pass the grade)."""
    if not pts:
        return None
    u = fr.unit(float(np.median([p["wick"] for p in pts])))
    lo, hi, kept = _edges(pts, u)
    visits = _visits(kept, fr.cl, lo, hi, u)
    last_i = max(p["i"] for p in kept)
    side = [1 if x > hi else -1 if x < lo else 0 for x in fr.cl[last_i + 1:]]
    nz = [x for x in side if x]
    if sum(1 for a, b in zip(nz, nz[1:]) if a != b) >= STALE_CROSSES:
        return None   # crossed again and again since it last mattered
    strong = any(p["reaction_atr"] >= STRONG_REJECTION_ATR for p in kept)
    nv = len(visits)
    step = round_step(fr.close)
    rnd = math.floor(hi / step) * step
    factors = {
        "timeframe": tf in ("W", "M"),
        "rejection": strong,
        "reversal": len({p["kind"] for p in kept}) == 2,
        # two or more distinct visits; WORN_TOUCHES+ is flagged worn on its own (not also stripped of this point:
        # a ceiling tested five times over three years is a major level, not a weak one)
        "touches": nv >= 2,
        "volume": any((p["volume"] or 0) >= VOLUME_HIGH for p in kept),
        "confluence": rnd >= lo or any(lo <= x <= hi for x in fr.conf),
        "recency": last_i >= len(fr.df) - TF[fr.tf]["recent"],
    }
    score = sum(factors.values())
    if accept and (not (nv >= 2 or strong) or (nv == 1 and kept[0]["spike"]) or score < MIN_SCORE):
        return None
    ref = float(min(hi, max(lo, np.median([p["wick"] for p in visits]))))
    z = {"tf": tf, "top": float(hi), "bottom": float(lo), "refs": [ref],
         "score": int(score), "of": len(FACTORS), "strong": score >= STRONG_SCORE, "worn": nv >= WORN_TOUCHES,
         "factors": factors, "round": float(rnd) if rnd >= lo else None,
         "touches": [{"date": p["date"], "price": p["wick"], "kind": p["kind"], "reaction_atr": round(p["reaction_atr"], 2)}
                     for p in visits],
         "from": visits[0]["date"], "first_kind": visits[0]["kind"], "_pts": kept, "_fr": fr}
    _place(z, fr.close)
    return z


def _place(z: dict, close: float, near: float = 0.0) -> None:
    """Role from where price is now; the alert line at the near edge; reversed when it began the other way.
    Within `near` of the zone counts as at it: a support a few cents under the close says nothing."""
    if close > z["top"] + near:
        z["role"], z["line"] = "support", z["top"]
    elif close < z["bottom"] - near:
        z["role"], z["line"] = "resistance", z["bottom"]
    else:
        z["role"] = "pivot"
        # its key line near the price: the nearer edge when price sits just outside ("at price"); inside,
        # the nearest of its reference lines and edges — never a line far from where price is
        inside = z["bottom"] <= close <= z["top"]
        cands = z["refs"] + [z["top"], z["bottom"]] if inside else [z["top"], z["bottom"]]
        z["line"] = min(cands, key=lambda x: abs(x - close))
    z["inside"] = z["bottom"] <= close <= z["top"]
    z["at_price"] = z["role"] == "pivot" and not z["inside"]
    formed = "resistance" if z["first_kind"] == "H" else "support"
    z["flipped"] = z["role"] != "pivot" and formed != z["role"]


def _split_wide(z: dict, chart: _Frame) -> list[dict]:
    """A zone too tall to use on the chart being read is split at its widest internal gap, when each part
    stands on its own (two turning points, or one strong rejection) and passes the grade; recursively."""
    if z["top"] - z["bottom"] <= WIDE_ATR * chart.unit(z["refs"][0]):
        return [z]
    pts = sorted(z["_pts"], key=lambda p: p["wick"])
    if len(pts) >= 2:
        k = max(range(1, len(pts)), key=lambda j: pts[j]["wick"] - pts[j - 1]["wick"])
        parts = [pts[:k], pts[k:]]
        if all(len(g) >= 2 or any(p["reaction_atr"] >= STRONG_REJECTION_ATR for p in g) for g in parts):
            # a part that no longer earns a level (crossed again and again since, or too weak) is retired;
            # the parts that stand are kept
            made = [m for g in parts if (m := _zone(g, z["_fr"], z["tf"]))]
            if made:
                return [y for m in made for y in _split_wide(m, chart)]
    z["wide"] = True
    return [z]


def _merge(zones: list[dict], chart: _Frame) -> list[dict]:
    """Same-role zones closer than MERGE_GAP_ATR are one area — one zone keeping both reference lines —
    unless the result would be too tall to use on the chart being read."""
    out: list[dict] = []
    for z in sorted(zones, key=lambda z: z["bottom"]):
        prev = out[-1] if out else None
        if (prev and prev["role"] == z["role"] and prev["_fr"] is z["_fr"] and prev["tf"] == z["tf"]
                and z["bottom"] - prev["top"] < MERGE_GAP_ATR * z["_fr"].unit(z["bottom"])
                and max(prev["top"], z["top"]) - prev["bottom"] <= WIDE_ATR * chart.unit(z["bottom"])):
            m = _zone(prev["_pts"] + z["_pts"], z["_fr"], z["tf"], accept=False)
            if m:
                m["refs"] = sorted(prev["refs"] + z["refs"])
                m["merged"] = True   # it starts at its own first visit (`_zone` set it from the joint visits)
                _place(m, chart.close)
                out[-1] = m
                continue
        out.append(z)
    return out


def _cap(z: dict, unit: Callable[[float], float]) -> bool:
    """A zone still taller than CAP_ATR of its own timeframe (`unit(price)` = one ATR there) is cut back to
    its body side — the wick side is trimmed (for a mixed zone, the side away from price). Its visits are
    the ones that came to the zone as cut: a high at or above its bottom, a low at or below its top (a
    wick that went through it and back still visited it; a turning point now wholly outside did not), so
    its start, visit count, grade and height are re-read from them. False when no visit is left: the cut
    zone has no evidence and is not a level."""
    u = unit(z["reference"])
    if z["top"] - z["bottom"] <= CAP_ATR * u:
        return True
    kinds = [t["kind"] for t in z["touches"]]
    trim_top = kinds.count("H") > kinds.count("L") if kinds.count("H") != kinds.count("L") else z["role"] == "support"
    ref = z["reference"]
    for _ in range(4):   # the reference moves into the cut zone, and one ATR is measured there
        if trim_top:
            z["top"] = z["bottom"] + CAP_ATR * u
        else:
            z["bottom"] = z["top"] - CAP_ATR * u
        u = unit(min(z["top"], max(z["bottom"], ref)))
    tol = 0.1 * u
    came = [t for t in z["touches"] if (t["price"] >= z["bottom"] - tol if t["kind"] == "H" else t["price"] <= z["top"] + tol)]
    if not came:
        return False
    z["touches"], z["from"] = came, came[0]["date"]
    z["factors"]["touches"] = len(came) >= 2
    z["score"] = sum(z["factors"].values())
    z["strong"], z["worn"] = z["score"] >= STRONG_SCORE, len(came) >= WORN_TOUCHES
    z["refs"] = [min(z["top"], max(z["bottom"], x)) for x in z["refs"]]
    z["reference"] = min(z["top"], max(z["bottom"], z["reference"]))
    z["height_atr"] = round((z["top"] - z["bottom"]) / unit(z["reference"]), 2)
    z["capped"] = True
    return True


def _refine(z: dict, fine: _Frame) -> list[dict]:
    """A higher-timeframe zone redrawn from the finer timeframe's turning points inside it — finer edges,
    distinct visits on the finer bars, the first fine reaction as its start. It keeps its own timeframe's
    standing. A weekly zone is always refined with daily bars, whichever chart is open, so the same
    weekly level reads the same on both. The finer points are taken over the zone's own look-back: a
    weekly zone of four bottoms since 2020 redrawn from only the last eighteen months of daily points
    kept one of them."""
    fr = z["_fr"]
    pool = fine.since(fr.df.index[min(fr.first, len(fr.df) - 1)])
    inside = sorted((p for p in pool if z["bottom"] <= p["wick"] <= z["top"]), key=lambda p: p["wick"])
    r = _zone(inside, fine, z["tf"], accept=False) if len(inside) >= 2 else None
    if r:
        parts = [r]
    elif len(inside) >= 2:
        # The whole box is not respected on the finer bars — price has crossed it again and again, which
        # is what congestion looks like. Redraw it as the separate reaction clusters inside it instead;
        # each is kept only if price still respects it (a lone point needs a strong rejection).
        groups, cur = [], [inside[0]]
        for p in inside[1:]:
            if p["wick"] - cur[0]["wick"] > SPLIT_ATR * fine.unit(cur[0]["wick"]):
                groups.append(cur)
                cur = []
            cur.append(p)
        groups.append(cur)
        parts = [m for g in groups
                 if (len(g) >= 2 or any(p["reaction_atr"] >= STRONG_REJECTION_ATR for p in g))
                 and (m := _zone(g, fine, z["tf"], accept=False))]
    else:
        parts = []
    if not r and len(inside) >= 2:
        z["_crossed"] = True   # the box itself is not respected: a candidate congestion band (levels() decides)
    if not parts:
        return [z]   # nothing finer stands: the higher-timeframe box stays, as drawn
    for m in parts:
        # it starts at its own first visit: a coarse visit that falls outside the finer box is not one of it
        m["from"] = m["touches"][0]["date"]
        m["factors"]["timeframe"] = True
        m["score"] = sum(m["factors"].values())
        m["strong"] = m["score"] >= STRONG_SCORE
        m["refined"] = True
    return parts


def _zones_for(fr: _Frame) -> list[dict]:
    """Every graded zone on one timeframe's own turning points."""
    pts = sorted(fr.pts, key=lambda p: p["wick"])

    def split(g: list[dict]) -> list[list[dict]]:
        # split at the widest gap until each group spans at most SPLIT_ATR (growing groups upward from
        # the lowest price instead lets a group swallow the next point merely because it fits)
        if len(g) < 2 or g[-1]["wick"] - g[0]["wick"] <= SPLIT_ATR * fr.unit(g[0]["wick"]):
            return [g]
        k = max(range(1, len(g)), key=lambda j: g[j]["wick"] - g[j - 1]["wick"])
        return split(g[:k]) + split(g[k:])
    return [z for g in (split(pts) if pts else []) if (z := _zone(g, fr, fr.tf))]


def _period_lines(daily: pd.DataFrame, tf: str) -> list[dict]:
    """The previous completed period's high and low: week and month on a daily chart, month and year on
    a weekly one."""
    units = (("W", "week"), ("M", "month")) if tf == "D" else (("M", "month"), ("Y", "year"))
    out = []
    for rule, name in units:
        g = daily.resample({"W": "W-FRI", "M": "ME", "Y": "YE"}[rule]).agg({"high": "max", "low": "min"}).dropna()
        if len(g) < 2:
            continue
        prev = g.iloc[-2]
        start = str(g.index[-2].date())
        out.append({"kind": f"prev_{name}_high", "price": float(prev["high"]), "label": f"previous {name}'s high", "from": start})
        out.append({"kind": f"prev_{name}_low", "price": float(prev["low"]), "label": f"previous {name}'s low", "from": start})
    return out


def levels(daily: pd.DataFrame, tf: str = "D") -> dict:
    """Support and resistance for a chart of timeframe `tf` ("D", "W" or "M"), from stored daily bars."""
    higher, own = STACK[tf]
    odf = bars(daily, own)
    close = float(odf["close"].iloc[-1])
    conf = [float(x) for x in (ind.sma(odf["close"], 50).iloc[-1], ind.sma(odf["close"], 200).iloc[-1]) if x == x]
    frames: dict[str, _Frame] = {}

    def frame(t: str) -> _Frame:
        if t not in frames:
            frames[t] = _Frame(t, odf if t == own else bars(daily, t), close, conf)
        return frames[t]
    own_fr, day_fr = frame(own), frame("D")
    hi_fr = frame(higher) if higher else None
    finer = {"M": frame("W"), "W": day_fr}   # what refines a zone of each timeframe: the next one down
    boxes: list[dict] = []   # higher-timeframe boxes price keeps crossing: congestion candidates

    def ref(zs: list[dict]) -> list[dict]:
        out = []
        for z in zs:
            parts = _refine(z, finer[z["tf"]]) if finer.get(z["tf"]) else [z]
            if z.get("_crossed"):
                boxes.append(z)
            out += parts
        return out
    top = [y for z in _merge(ref(_zones_for(hi_fr)), own_fr) for y in _split_wide(z, own_fr)] if hi_fr else []
    def within_higher(z: dict) -> bool:
        """Most of the zone lies inside a (split) higher-timeframe zone: the higher one already says it. A
        sliver of overlap does not — a four-visit daily zone sharing its top two points with a two-visit
        weekly one is the better-evidenced level, and dropping it hid it."""
        h_ = z["top"] - z["bottom"]
        for h in top:
            ov = min(z["top"], h["top"]) - max(z["bottom"], h["bottom"])
            if ov >= 0 and (ov >= OVERLAP_SHARE * h_ if h_ > 0 else True):
                return True
        return False
    low = [z for z in ref(_zones_for(own_fr)) if not within_higher(z)]   # in the gaps the higher zones leave
    allz = top + [y for z in _merge(low, own_fr) for y in _split_wide(z, own_fr)]
    # final roles against the chart's own volatility; congestion where price has lived inside the zone
    cl, dates = own_fr.cl, [d.date().isoformat() for d in odf.index]

    def lived(z: dict) -> float:
        since = cl[next((i for i, d in enumerate(dates) if d >= z["from"]), len(cl)):]
        return round(float(((since >= z["bottom"]) & (since <= z["top"])).mean()), 2) if len(since) >= 10 else 0.0
    for z in allz:
        _place(z, close, AT_PRICE_ATR * day_fr.unit(close))   # daily ATR on every chart: one answer to "at price"
        z["time_inside"] = lived(z)
        z["congestion"] = z["time_inside"] >= CONGESTION_SHARE
    # Congestion bands: a higher-timeframe box price keeps crossing and has lived inside — drawn as context,
    # not as a level (no role, no grade). Its edges are what matter: a break out of it is the event.
    congestion = []
    for b in boxes:
        share = lived(b)
        if share >= CONGESTION_SHARE:
            congestion.append({"tf": b["tf"], "top": b["top"], "bottom": b["bottom"], "from": b["from"],
                               "time_inside": share, "inside": b["bottom"] <= close <= b["top"]})
    for z in allz:   # the check: height ÷ the ATR of the zone's own timeframe
        fr = frame(z["tf"])
        z["reference"] = z["refs"][0] if len(z["refs"]) == 1 else (z["top"] + z["bottom"]) / 2
        z["height_atr"] = round((z["top"] - z["bottom"]) / fr.unit(z["reference"]), 2)
        z["atr_tf"] = z["tf"]
        z.setdefault("wide", False)
    # Cap: a zone still taller than CAP_ATR of its own timeframe after splitting (a lone spike bar, say)
    # is cut back to its body side (`_cap`); one left with no visit is dropped
    allz = [z for z in allz if _cap(z, frame(z["tf"]).unit)]
    for z in allz:
        _place(z, close, AT_PRICE_ATR * day_fr.unit(close))
    lines = list(_period_lines(daily, tf))
    note = None
    unit = own_fr.unit(close)
    dist = lambda z: abs(z["line"] - close)  # noqa: E731
    # One area, one zone. Same-role zones that overlap or nearly touch (a daily zone half inside a weekly one,
    # say) become one zone standing as the coarser timeframe, each visit listed once, measured again — unless
    # that zone would be taller than CAP_ATR, when overlapping ones keep the better (score, then timeframe)
    # and merely adjacent ones stay apart. Zones of different roles are never merged: the better one is kept.
    # Run before key levels are chosen (so one area takes one slot) and again after (a promoted zone).
    rank = {"D": 0, "W": 1, "M": 2}

    def merge_keys(zs: list[dict], across_roles: bool = True) -> list[dict]:
        better = lambda a, b: a if (a["score"], rank[a["tf"]], -dist(a)) >= (b["score"], rank[b["tf"]], -dist(b)) else b  # noqa: E731
        out: list[dict] = []
        for z in sorted(zs, key=lambda z: z["bottom"]):
            prev = out[-1] if out else None
            if prev and z["bottom"] - prev["top"] < 0.25 * unit:
                overlap = z["bottom"] < prev["top"]
                if prev["role"] == z["role"]:
                    tf_ = prev["tf"] if rank[prev["tf"]] >= rank[z["tf"]] else z["tf"]
                    top_, bottom_ = max(prev["top"], z["top"]), prev["bottom"]
                    refs = sorted(prev["refs"] + z["refs"])
                    ref_ = refs[0] if len(refs) == 1 else (top_ + bottom_) / 2
                    if top_ - bottom_ <= CAP_ATR * frame(tf_).unit(ref_) * 1.0001:
                        seen, visits = set(), []
                        for t in sorted(prev["touches"] + z["touches"], key=lambda t: t["date"]):
                            if (t["date"], t["kind"]) not in seen:
                                seen.add((t["date"], t["kind"]))
                                visits.append(t)
                        m = dict(prev, tf=tf_, atr_tf=tf_, top=top_, refs=refs, reference=ref_, touches=visits,
                                 score=max(prev["score"], z["score"]), worn=len(visits) >= WORN_TOUCHES, merged=True,
                                 promoted=bool(prev.get("promoted") and z.get("promoted")),
                                 height_atr=round((top_ - bottom_) / frame(tf_).unit(ref_), 2), **{"from": visits[0]["date"]})
                        m["strong"] = m["score"] >= STRONG_SCORE
                        _place(m, close, AT_PRICE_ATR * day_fr.unit(close))
                        out[-1] = m
                        continue
                    if not overlap:
                        out.append(z)
                        continue
                if across_roles or prev["role"] == z["role"]:
                    out[-1] = better(prev, z)
                    continue
            out.append(z)
        return out
    allz = merge_keys(allz, across_roles=False)
    # Key levels — proximity first, not a fixed quota. Only zones within the relevance window qualify,
    # with a score of at least KEY_MIN_SCORE (a daily zone also needs two visits). Any pivot first, then
    # the nearest qualifying zone each side, then the best of the rest by score, up to MAX_KEY in all and
    # MAX_PER_SIDE a side. A side may show none.
    window = RELEVANCE_ATR.get(own, 8) * unit
    near = [z for z in allz if dist(z) <= window]
    good = [z for z in near if z["score"] >= KEY_MIN_SCORE and (z["tf"] != "D" or len(z["touches"]) >= 2)]
    pick = [z for z in near if z["role"] == "pivot"]
    for role in ("support", "resistance"):
        side = sorted((z for z in good if z["role"] == role), key=dist)
        if side:
            pick.append(side[0])
    for z in sorted(good, key=lambda z: (-z["score"], dist(z))):
        if len(pick) >= MAX_KEY:
            break
        if z not in pick and sum(1 for y in pick if y["role"] == z["role"]) < MAX_PER_SIDE:
            pick.append(z)
    # Gap rule: price more than GAP_ATR from its nearest key zone on a side — promote a graded zone inside
    # that gap: one of this chart's hidden zones or a cluster from the timeframe below (a weekly chart's
    # newest structure is still forming on the daily bars); the nearest that scores KEY_MIN_SCORE, else the
    # nearest graded one. With none, mark the next round number there instead (clearly as such).
    below = {"W": "D", "M": "W"}.get(own)
    lower = []
    if below:
        for z in ref(_zones_for(frame(below))):   # refined like any zone of that timeframe: one weekly level, one answer
            _place(z, close, AT_PRICE_ATR * day_fr.unit(close))
            z["reference"] = z["refs"][0]
            z["height_atr"] = round((z["top"] - z["bottom"]) / frame(below).unit(z["reference"]), 2)
            z.update(atr_tf=z["tf"], wide=False, time_inside=0.0, congestion=False)
            if _cap(z, frame(below).unit):   # promoted onto the chart: no taller than any other zone on it
                _place(z, close, AT_PRICE_ATR * day_fr.unit(close))
                lower.append(z)
    for role, sgn in (("support", -1), ("resistance", 1)):
        side = [z for z in pick if z["role"] == role]
        gap_to = min((dist(z) for z in side), default=window)
        if gap_to <= GAP_ATR * unit:
            continue
        inside = [z for z in near + lower if z["role"] == role and z not in pick and dist(z) < gap_to]
        if inside:
            strong = [z for z in inside if z["score"] >= KEY_MIN_SCORE]
            best = min(strong or inside, key=dist)
            best["promoted"] = True
            pick.append(best)
        else:
            step = round_step(close)
            rn = (math.floor(close / step) + (1 if sgn > 0 else 0)) * step
            if rn == close:
                rn += sgn * step
            if abs(rn - close) < gap_to:
                lines.append({"kind": "round", "price": float(rn), "from": str(odf.index[-1].date()),
                              "label": f"round number — no {role} within {GAP_ATR} ATR"})
    pick = sorted(merge_keys(pick), key=lambda z: -z["top"])
    others = sorted((z for z in allz if z not in pick and not any(z["bottom"] < y["top"] and z["top"] > y["bottom"] for y in pick)),
                    key=lambda z: -z["top"])
    # Long-term levels: a weekly or monthly zone price has reacted at over years (first to last reaction at
    # least LONG_TERM_SPAN_YEARS apart, 3+ visits) beyond the relevance window. Not a key level — price is far
    # from it — but the ceiling or floor a long move runs into. The best graded LONG_TERM_PER_SIDE a side are
    # returned on their own, to be drawn muted.
    def span_years(z: dict) -> float:
        ds = [pd.Timestamp(t["date"]) for t in z["touches"]]
        return (max(ds) - min(ds)).days / 365.25 if ds else 0.0
    longterm = []
    for role in ("support", "resistance"):
        far = [z for z in others if z["role"] == role and z["tf"] in ("W", "M") and dist(z) > window
               and len(z["touches"]) >= 3 and span_years(z) >= LONG_TERM_SPAN_YEARS
               and close / LONG_TERM_RANGE <= z["line"] <= close * LONG_TERM_RANGE]
        longterm += sorted(far, key=lambda z: (-z["score"], -len(z["touches"])))[:LONG_TERM_PER_SIDE]
    others = [z for z in others if z not in longterm]
    # Provisional extremes: a fresh high or low has no confirmed swing yet (that needs bars after it), so
    # the 52-week high and low are always marked, and the all-time high and low when within the window —
    # unless a key zone already covers them
    covered = lambda x: any(z["bottom"] - 0.003 * close <= x <= z["top"] + 0.003 * close for z in pick)  # noqa: E731
    yr = daily[daily.index > daily.index[-1] - pd.DateOffset(years=1)]
    for kind, price, label, always in (("hi52", float(yr["high"].max()), "52-week high (provisional)", True),
                                       ("lo52", float(yr["low"].min()), "52-week low (provisional)", True),
                                       ("ath", float(daily["high"].max()), "all-time high (provisional)", False),
                                       ("atl", float(daily["low"].min()), "all-time low (provisional)", False)):
        if covered(price) or (not always and abs(price - close) > window):
            continue
        if kind in ("ath", "atl") and any(l["price"] == price for l in lines):
            continue
        lines.append({"kind": "extreme", "price": price, "label": label, "from": str(odf.index[-1].date())})
    if not any(z["role"] == "resistance" for z in pick) and close >= float(daily["high"].max()) * (1 - ATH_NEAR_PCT / 100):
        step = round_step(close)
        lines.append({"kind": "round_above", "price": float((math.floor(close / step) + 1) * step),
                      "label": "next round number — no historical resistance above", "from": str(odf.index[-1].date())})
        note = "at an all-time high: no historical resistance above"
    clean = lambda z: {k: v for k, v in z.items() if not k.startswith("_")}  # noqa: E731
    return {"tf": tf, "stack": [higher, own], "close": close, "zones": [clean(z) for z in pick], "congestion": congestion,
            "longterm": [clean(z) for z in sorted(longterm, key=lambda z: -z["top"])],
            "others": [clean(z) for z in others], "lines": lines, "factors": FACTORS, "note": note,
            "considered": len(allz)}
