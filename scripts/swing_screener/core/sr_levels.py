"""SUPPORT AND RESISTANCE ZONES — horizontal levels drawn by one written procedure.

The chart's Support & Resistance indicator draws what this module returns (/api/sr-levels); the rules
live here only, never in JavaScript. The procedure, top to bottom:

1. **Timeframe stack.** Start on the higher timeframe ({STACK}), then add the chart's own timeframe.
   Each looks back far enough to show several major swings ({TF}).
2. **Turning points that earned it.** A swing high / low is a bar beyond its neighbours on both sides
   (`swing` bars each side). It counts only if price then moved away clearly: a close at least
   {MIN_REACTION_ATR} ATR from the extreme within `reaction` bars. A lone giant spike bar (range over
   {SPIKE_ATR} ATR) with no second reaction draws no level.
3. **Cluster, then draw a zone.** Turning points whose extremes lie within {MAX_ZONE_ATR} ATR of each
   other are one area (the sorted turning prices are split at their widest gaps until each group fits). The zone spans the wick cluster and the body cluster (the median body edge of
   the turning bars); a single wick sticking out more than {OUTLIER_ATR} ATR past the rest is ignored.
   Width is held between {MIN_ZONE_ATR} and {MAX_ZONE_ATR} ATR — wider is trimmed on the far side. ATR is
   taken as a share of price and applied at the zone's own price level.
4. **Grade it** — one point per factor (`FACTORS`); a zone needs {MIN_SCORE} points, and two reactions
   or one strong one. {STRONG_SCORE}+ is strong. A zone tested {WORN_TOUCHES}+ times is flagged worn:
   each test uses up orders, so it is more likely to break.
5. **Keep it after a break**, relabelled: a zone price has closed through takes the opposite role
   (role reversal). A zone price has crossed {STALE_CROSSES}+ times since its last reaction is
   dropped: the market no longer respects it.
6. **Few and near.** The higher timeframe wins where zones overlap; a lower-timeframe zone is kept only
   in the gaps, and a higher-timeframe zone takes its touches and start date from the chart timeframe's
   reactions inside it (refining it). At most {MAX_PER_SIDE} zones each side of price, best graded
   first, then nearest, are the key levels; the others that passed the grade are returned too.
7. **Context lines**: the previous period's high and low; at an all-time high, where no resistance
   exists, the next round number above (never an invented level).

Levels describe where price reacted; they make no trade decision.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import indicators as ind
from . import swings as sw

TF = {   # per timeframe: look-back, swing strength, bars to judge the reaction, "recent", bar average for volume
    "M": {"years": 10, "swing": 2, "reaction": 2, "recent": 24, "vol": 12},
    "W": {"years": 5, "swing": 3, "reaction": 3, "recent": 52, "vol": 20},
    "D": {"years": 1.5, "swing": 5, "reaction": 5, "recent": 126, "vol": 20},
}
STACK = {"D": ("W", "D"), "W": ("M", "W")}   # chart timeframe -> (higher, own)
ATR_BARS = 14
MIN_REACTION_ATR = 1.0      # a turning point counts when price closed this far away within `reaction` bars
STRONG_REJECTION_ATR = 2.0  # ... and is a strong rejection at this distance
SPIKE_ATR = 3.0             # a bar wider than this is a spike: alone, it draws no level
MIN_ZONE_ATR = 0.25         # zone width, in ATR of its timeframe
MAX_ZONE_ATR = 1.0
OUTLIER_ATR = 0.5           # a lone wick this far beyond the rest is ignored
VOLUME_HIGH = 1.5           # reaction volume vs the prior bars' average, for the volume point
MIN_SCORE = 3               # points to keep a zone ...
STRONG_SCORE = 5            # ... and to call it strong
WORN_TOUCHES = 5            # tests at which a level is more likely to break than hold
STALE_CROSSES = 3           # closes through a zone since its last reaction that retire it
MAX_PER_SIDE = 3            # zones kept each side of price
ATH_NEAR_PCT = 3.0          # within this of the all-time high: no historical resistance above

FACTORS = {
    "timeframe": "Found on the higher timeframe",
    "rejection": f"Strong rejection — price closed {STRONG_REJECTION_ATR} ATR away within a few bars",
    "reversal": "Role reversal — acted as both support and resistance",
    "touches": f"Two to {WORN_TOUCHES - 1} clean reactions",
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


def _zones_for(df: pd.DataFrame, tf: str, higher: bool, confluence: list[float]) -> list[dict]:
    c = TF[tf]
    if len(df) < ATR_BARS + 2 * c["swing"] + 2:
        return []
    atr_now = float(ind.atr(df, ATR_BARS).iloc[-1])
    close = float(df["close"].iloc[-1])
    # ATR as a share of price, applied at each zone's own price: a stock that went from 30 to 2,000
    # must not get 200-point zones down at 30
    ap = atr_now / close
    unit = lambda price: ap * price  # noqa: E731
    cut = df.index[-1] - pd.DateOffset(months=int(c["years"] * 12))
    first = int(np.searchsorted(df.index.values, np.datetime64(cut)))
    pts = sorted((p for p in _turning_points(df, tf) if p["i"] >= first), key=lambda p: p["wick"])
    cl = df["close"].to_numpy(float)
    n = len(df)
    # Cluster on the turning price by splitting at the widest gap until every group spans at most
    # MAX_ZONE_ATR. (Growing groups upward from the lowest price instead lets a group swallow the
    # next point merely because it fits, and breaks a natural cluster in two.)
    def split(g: list[dict]) -> list[list[dict]]:
        if len(g) < 2 or g[-1]["wick"] - g[0]["wick"] <= MAX_ZONE_ATR * unit(g[0]["wick"]):
            return [g]
        k = max(range(1, len(g)), key=lambda j: g[j]["wick"] - g[j - 1]["wick"])
        return split(g[:k]) + split(g[k:])
    groups = split(pts) if pts else []
    step = round_step(close)
    out = []
    for g in groups:
        wicks = sorted(p["wick"] for p in g)
        u = unit(float(np.median(wicks)))
        if len(wicks) >= 3:   # a lone spike wick sticking out beyond the rest is not the level
            if wicks[1] - wicks[0] > OUTLIER_ATR * u:
                wicks = wicks[1:]
            if wicks[-1] - wicks[-2] > OUTLIER_ATR * u:
                wicks = wicks[:-1]
        body = float(np.median([p["body"] for p in g]))
        lo_, hi_ = min(wicks[0], body), max(wicks[-1], body)
        mid = (lo_ + hi_) / 2
        role = "support" if close > mid else "resistance"
        if hi_ - lo_ > MAX_ZONE_ATR * u:   # trim the far side: the near edge is the one price meets
            if role == "support":
                lo_ = hi_ - MAX_ZONE_ATR * u
            else:
                hi_ = lo_ + MAX_ZONE_ATR * u
        if hi_ - lo_ < MIN_ZONE_ATR * u:
            pad = (MIN_ZONE_ATR * u - (hi_ - lo_)) / 2
            lo_, hi_ = lo_ - pad, hi_ + pad
        touches = sorted(g, key=lambda p: p["i"])
        last_i = touches[-1]["i"]
        # closes through the zone since its last reaction: a side change of the close, ignoring bars inside
        side = [1 if x > hi_ else -1 if x < lo_ else 0 for x in cl[last_i + 1:]]
        nz = [s for s in side if s]
        crosses = sum(1 for a, b in zip(nz, nz[1:]) if a != b)
        if crosses >= STALE_CROSSES:
            continue
        kinds = {p["kind"] for p in g}
        strong = any(p["reaction_atr"] >= STRONG_REJECTION_ATR for p in g)
        nt = len(g)
        has_round = math.floor(hi_ / step) * step >= lo_
        factors = {
            "timeframe": higher,
            "rejection": strong,
            "reversal": len(kinds) == 2,
            "touches": 2 <= nt < WORN_TOUCHES,
            "volume": any((p["volume"] or 0) >= VOLUME_HIGH for p in g),
            "confluence": has_round or any(lo_ <= x <= hi_ for x in confluence),
            "recency": last_i >= n - c["recent"],
        }
        score = sum(factors.values())
        if not (nt >= 2 or strong) or (nt == 1 and g[0]["spike"]) or score < MIN_SCORE:
            continue
        # its role now, and whether that is the reverse of how it formed
        formed = "resistance" if kinds == {"H"} else "support" if kinds == {"L"} else None
        inside = lo_ <= close <= hi_
        out.append({
            "tf": tf, "role": role, "top": float(hi_), "bottom": float(lo_),
            "line": float(hi_ if role == "support" else lo_),   # the edge price reaches first
            "inside": bool(inside), "flipped": bool(formed and formed != role),
            "score": int(score), "of": len(FACTORS), "strong": score >= STRONG_SCORE,
            "worn": nt >= WORN_TOUCHES, "factors": factors, "round": float(math.floor(hi_ / step) * step) if has_round else None,
            "touches": [{"date": p["date"], "price": p["wick"], "kind": p["kind"],
                         "reaction_atr": round(p["reaction_atr"], 2)} for p in touches],
            "from": touches[0]["date"], "atr": u,
        })
    return out


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
    """Support and resistance for a chart of timeframe `tf` ("D" or "W"), from stored daily bars."""
    higher, own = STACK[tf]
    frames = {t: bars(daily, t) for t in (higher, own)}
    df = frames[own]
    close = float(df["close"].iloc[-1])
    period = _period_lines(daily, tf)
    sma = [float(x) for x in (ind.sma(df["close"], 50).iloc[-1], ind.sma(df["close"], 200).iloc[-1]) if x == x]
    conf = sma   # the scoring table's confluence: round numbers (per zone) and the moving averages
    top = _zones_for(frames[higher], higher, True, conf)
    # Refine each higher-timeframe zone with the chart timeframe's turning points inside it: its band
    # stays (a weekly level is as wide as a weekly bar), but its touches and start come from the
    # daily reactions — a weekly zone otherwise "starts" at its first weekly swing, months after the
    # daily chart first turned there.
    own_pts = _turning_points(df, own)
    first_w = frames[higher].index[-1] - pd.DateOffset(months=int(TF[higher]["years"] * 12))
    for z in top:
        inside = sorted((p for p in own_pts if z["bottom"] <= p["wick"] <= z["top"] and df.index[p["i"]] >= first_w),
                        key=lambda p: p["i"])
        if len(inside) >= 2:
            z["touches"] = [{"date": p["date"], "price": p["wick"], "kind": p["kind"],
                             "reaction_atr": round(p["reaction_atr"], 2)} for p in inside]
            z["from"] = min(z["from"], inside[0]["date"])
            z["worn"] = len(inside) >= WORN_TOUCHES
            z["refined"] = True
    low = [z for z in _zones_for(df, own, False, conf)
           if not any(z["bottom"] <= h["top"] and z["top"] >= h["bottom"] for h in top)]   # higher timeframe wins
    allz = top + low
    pick = []
    for role in ("support", "resistance"):
        side = [z for z in allz if z["role"] == role]
        side.sort(key=lambda z: (-z["score"], abs(z["line"] - close)))
        pick += side[:MAX_PER_SIDE]
    pick.sort(key=lambda z: -z["top"])
    # the rest that passed the grade, for a chart that asks to see every graded level (drawn faint)
    others = sorted((z for z in allz if z not in pick), key=lambda z: -z["top"])
    lines = list(period)
    ath = float(daily["high"].max())
    note = None
    if not any(z["role"] == "resistance" for z in pick) and close >= ath * (1 - ATH_NEAR_PCT / 100):
        step = round_step(close)
        nxt = (math.floor(close / step) + 1) * step
        lines.append({"kind": "round_above", "price": float(nxt), "label": "next round number — no historical resistance above",
                      "from": str(df.index[-1].date())})
        note = "at an all-time high: no historical resistance above"
    return {"tf": tf, "stack": [higher, own], "close": close, "zones": pick, "others": others, "lines": lines,
            "factors": FACTORS, "note": note,
            "considered": len(allz)}
