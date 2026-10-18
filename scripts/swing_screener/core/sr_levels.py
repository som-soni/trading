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
   the turning bars); a lone wick more than {OUTLIER_ATR} ATR past the rest is ignored and is not a touch.
   Height is never stretched or trimmed to an ATR band. Touches are distinct visits: a new one counts
   only after price closed {DEPART_ATR} ATR outside the zone. The reference line is where the reactions
   concentrate (their median turning price), not the midpoint.
4. **Refine the higher timeframe with the finer one.** A weekly zone is redrawn from the daily turning
   points inside it (finer structure; a weekly bar's body sits far from its wick), keeping its weekly
   standing — or, when price has crossed the whole box again and again, as the separate daily reaction
   clusters inside it that price still respects. If price has also lived inside the box ({CONGESTION_SHARE:.0%}+
   of bars), the box is returned as a **congestion band**: context, not a level; a daily zone is kept only in the gaps between higher-timeframe zones.
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
8. **Few and near.** Key levels: any pivot, plus the nearest {MAX_PER_SIDE} graded zones each side (the
   better grade breaking a tie). The others that passed the grade are returned too.
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
MAX_PER_SIDE = 3            # zones kept each side of price
ATH_NEAR_PCT = 3.0          # within this of the all-time high: no historical resistance above
AT_PRICE_ATR = 0.25         # a zone within this of the close (chart timeframe's ATR) is "at price": a pivot
CONGESTION_SHARE = 0.3      # price closed inside the zone on at least this share of bars since it formed: congestion
EARNINGS_WARN_SESSIONS = 10 # earnings this close: levels near price are less reliable through the report

FACTORS = {
    "timeframe": "Found on the weekly or monthly chart",
    "rejection": f"Strong rejection — price closed {STRONG_REJECTION_ATR} ATR away within a few bars",
    "reversal": "Role reversal — acted as both support and resistance",
    "touches": f"Two to {WORN_TOUCHES - 1} distinct visits",
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
    """A zone from the structure of its turning points: the wick extremes (a lone wick more than
    OUTLIER_ATR beyond the rest dropped) and the median body edge. Nothing is stretched or trimmed.
    Returns the edges and the turning points kept — a dropped spike is not a touch either."""
    pts = sorted(g, key=lambda p: p["wick"])
    if len(pts) >= 3:
        if pts[1]["wick"] - pts[0]["wick"] > OUTLIER_ATR * u:
            pts = pts[1:]
        if pts[-1]["wick"] - pts[-2]["wick"] > OUTLIER_ATR * u:
            pts = pts[:-1]
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

    def __post_init__(self):
        self.cl = self.df["close"].to_numpy(float)
        self.ap = float(ind.atr(self.df, ATR_BARS).iloc[-1]) / float(self.df["close"].iloc[-1])
        cut = self.df.index[-1] - pd.DateOffset(months=int(TF[self.tf]["years"] * 12))
        self.first = int(np.searchsorted(self.df.index.values, np.datetime64(cut)))
        self.pts = [p for p in _turning_points(self.df, self.tf) if p["i"] >= self.first]

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
        "touches": 2 <= nv < WORN_TOUCHES,
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
                m["from"] = min(prev["from"], z["from"])
                m["merged"] = True
                _place(m, chart.close)
                out[-1] = m
                continue
        out.append(z)
    return out


def _refine(z: dict, fine: _Frame) -> list[dict]:
    """A higher-timeframe zone redrawn from the finer timeframe's turning points inside it — finer edges,
    distinct visits on the finer bars, the first fine reaction as its start. It keeps its own timeframe's
    standing. A weekly zone is always refined with daily bars, whichever chart is open, so the same
    weekly level reads the same on both."""
    inside = sorted((p for p in fine.pts if z["bottom"] <= p["wick"] <= z["top"]), key=lambda p: p["wick"])
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
        m["from"] = min(m["from"], z["from"])
        m["factors"]["timeframe"] = True
        m["score"] = sum(m["factors"].values())
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
    low = [z for z in ref(_zones_for(own_fr))   # in the gaps the (split) higher zones leave
           if not any(z["bottom"] <= h["top"] and z["top"] >= h["bottom"] for h in top)]
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
    # key levels: any pivot (price is in it), plus the nearest graded zones each side
    pick = [z for z in allz if z["role"] == "pivot"]
    for role in ("support", "resistance"):
        side = sorted((z for z in allz if z["role"] == role), key=lambda z: (abs(z["line"] - close), -z["score"]))
        pick += side[:MAX_PER_SIDE]
    pick.sort(key=lambda z: -z["top"])
    others = sorted((z for z in allz if z not in pick), key=lambda z: -z["top"])
    lines = list(_period_lines(daily, tf))
    note = None
    if not any(z["role"] == "resistance" for z in pick) and close >= float(daily["high"].max()) * (1 - ATH_NEAR_PCT / 100):
        step = round_step(close)
        lines.append({"kind": "round_above", "price": float((math.floor(close / step) + 1) * step),
                      "label": "next round number — no historical resistance above", "from": str(odf.index[-1].date())})
        note = "at an all-time high: no historical resistance above"
    clean = lambda z: {k: v for k, v in z.items() if not k.startswith("_")}  # noqa: E731
    return {"tf": tf, "stack": [higher, own], "close": close, "zones": [clean(z) for z in pick], "congestion": congestion,
            "others": [clean(z) for z in others], "lines": lines, "factors": FACTORS, "note": note,
            "considered": len(allz)}
