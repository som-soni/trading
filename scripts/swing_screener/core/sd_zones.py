"""SUPPLY AND DEMAND ZONES — the base a decisive move left from, drawn by one stated rule.

The chart's Supply & demand zones indicator draws what this module returns (/api/sd-zones); the
rules live here only, never in JavaScript. A zone is found from price alone and judged afterwards:

1. **Departure first.** A move of 1–{DEPART_MAX_BARS} bars that closes beyond the base and carries
   the close at least {DEPART_MIN_ATR} ATR past the base's near edge, every bar closing further on
   (limited overlap), each bar's close-to-close gain averaging at least {DEPART_MIN_BODY:.0%} of
   its true range (substantial bodies; a gap counts as progress).
2. **Trace it back to the base** — the compact pause right before it: walking back from the
   departure, bars no wider than {BASE_BAR_MAX_ATR} ATR each unless their body is at most
   {BASE_BAR_MAX_BODY:.0%} of their range (an indecision bar), the whole pause no wider than
   {BASE_MAX_ATR} ATR, at most {BASE_MAX_BARS} bars. No such pause, no zone: a messy origin is
   skipped, never stretched to fit.
3. **One boundary convention.** Demand: proximal (upper) edge = the highest candle body in the base,
   distal (lower) edge = its lowest wick. Supply: proximal = the lowest body, distal = the highest wick.
4. **Extend it right** until a daily close beyond the distal edge (plus {INVALIDATE_BUFFER_ATR} ATR)
   — the failure rule, fixed before any retest. Each return into the zone after price has left it is
   recorded as a test, with whether a wick went through the distal edge and the close came back.
   Tested {WORN_TESTS}+ times, a zone is flagged **worn**: its orders are spent, and it behaves as a
   plain support or resistance level rather than a fresh zone.
5. **One area, one zone.** A new zone overlapping a same-kind zone that is still active is the same
   area seen again (a base built during a retest): the two are merged into one zone, its edges the
   union, its tests counted once.

The name says what came before the base: a drop or a rally over the last {LEGIN_BARS} bars, or over
the last {LEGIN_LONG_BARS} when the shorter leg is too small to tell — always DBR / RBR / RBD / DBD.

The quality checklist (`checks`) is the record of what was examined — compact base, strong departure
(≥ {STRONG_DEPART_ATR} ATR), a break of nearby structure, relative volume on the departure
(≥ {RVOL_HIGH}× the prior {RVOL_BARS} bars), and the larger trend — not a validated score. A zone is a
hypothesis to watch, never a buy or sell signal; it makes no trade decision (entry, stop, size).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import indicators as ind

ATR_BARS = 14
DEPART_MAX_BARS = 3          # a departure is one to three bars
DEPART_MIN_ATR = 2.0         # how far past the base's near edge the departure must close, in ATR
DEPART_MIN_BODY = 0.5        # the departure bars' average close-to-close gain as a share of their true range
STRONG_DEPART_ATR = 3.0      # checklist: a strong departure
BASE_MAX_BARS = 6            # the base: at most this many bars
BASE_BAR_MAX_ATR = 1.0       # each base bar no wider than this ...
BASE_BAR_MAX_BODY = 0.5      # ... unless its body is at most this share of its range (an indecision bar)
BASE_MAX_ATR = 1.5           # the whole base no wider than this
COMPACT_BASE_BARS = 3        # checklist: a compact base is this many bars or fewer ...
COMPACT_BASE_ATR = 1.0       # ... and no wider than this
RVOL_BARS = 20               # relative volume = departure volume / the average of the prior RVOL_BARS bars
RVOL_HIGH = 1.5              # checklist: volume expanded on the departure (descriptive, not a validity bar)
STRUCTURE_BARS = 20          # checklist: the departure closed beyond the highest high / lowest low of these bars
LEGIN_BARS = 10              # the move into the base, for the DBR / RBR / RBD / DBD name ...
LEGIN_MIN_ATR = 1.0          # ... a leg-in smaller than this looks further back (LEGIN_LONG_BARS) for its direction
LEGIN_LONG_BARS = 30
WORN_TESTS = 4               # tested this often, a zone's orders are spent: flagged worn — a plain level now
RELEVANCE_ATR = {"D": 8, "W": 6}   # the default view shows zones within this many ATR of price
INVALIDATE_BUFFER_ATR = 0.0  # failure: a close beyond the distal edge by more than this
TREND_BARS = {"D": 200, "W": 40}      # the larger trend: this moving average, on that timeframe ...
TREND_SLOPE_BARS = {"D": 21, "W": 5}  # ... rising (demand) or falling (supply) over this many bars

CHECKS = {
    "compact": f"Compact base — {COMPACT_BASE_BARS} bars or fewer, no wider than {COMPACT_BASE_ATR} ATR",
    "strong": f"Strong departure — at least {STRONG_DEPART_ATR} ATR past the base",
    "structure": f"Broke nearby structure — closed beyond the {STRUCTURE_BARS}-bar high (demand) or low (supply)",
    "volume": f"Volume expanded on the departure — at least {RVOL_HIGH}× the prior {RVOL_BARS} bars",
    "trend": "With the larger trend — price on the trend's side of a rising (demand) or falling (supply) long average",
}

_NAMES = {("demand", "down"): "Drop–base–rally", ("demand", "up"): "Rally–base–rally",
          ("supply", "up"): "Rally–base–drop", ("supply", "down"): "Drop–base–drop"}
_CODES = {("demand", "down"): "DBR", ("demand", "up"): "RBR", ("supply", "up"): "RBD", ("supply", "down"): "DBD"}


def _base(o, h, l, c, end: int, atr: float) -> int | None:
    """The first bar of the compact pause ending at `end`, walking back; None when even `end` alone is too wide."""
    start, hi, lo = None, -np.inf, np.inf
    for k in range(end, max(-1, end - BASE_MAX_BARS), -1):
        rng = h[k] - l[k]
        # a pause bar is narrow, or an indecision bar (a small body, whatever its wicks): a wide bar
        # with a full body is a move of its own, not part of the pause
        if rng > BASE_BAR_MAX_ATR * atr and abs(c[k] - o[k]) > BASE_BAR_MAX_BODY * rng:
            break
        hi2, lo2 = max(hi, h[k]), min(lo, l[k])
        if hi2 - lo2 > BASE_MAX_ATR * atr:
            break
        start, hi, lo = k, hi2, lo2
    return start


def _departure(o, h, l, c, j: int, sign: int, proximal: float, edge: float, atr: float) -> int | None:
    """The last bar of a departure starting at j (sign +1 up, -1 down), or None. `edge` is the base's
    far side the first bar must close beyond (its high for demand, its low for supply). Each bar's
    progress is its close-to-close move over its true range, so a gap counts as the decisive move it is."""
    n = len(c)
    if sign * (c[j] - edge) <= 0:
        return None
    shares = []
    for k in range(j, min(n, j + DEPART_MAX_BARS)):
        if sign * (c[k] - c[k - 1]) <= 0:
            return None
        tr = max(h[k], c[k - 1]) - min(l[k], c[k - 1])
        shares.append(abs(c[k] - c[k - 1]) / tr if tr > 0 else 0.0)
        if sign * (c[k] - proximal) >= DEPART_MIN_ATR * atr and np.mean(shares) >= DEPART_MIN_BODY:
            return k
    return None


def zones(daily: pd.DataFrame, tf: str = "D", years: float | None = None) -> list[dict]:
    """Every supply and demand zone in `daily` (OHLCV, date index, any timeframe labelled by `tf`),
    oldest first, each with its life to the last bar: its tests and, if it failed, when."""
    # a holiday print (no volume, no range) is not a session: it is neither a pause nor a move
    daily = daily[~((daily["volume"] <= 0) & (daily["high"] <= daily["low"]))]
    if len(daily) < ATR_BARS + LEGIN_BARS + 2:
        return []
    o, h, l, c, v = (daily[k].to_numpy(float) for k in ("open", "high", "low", "close", "volume"))
    dates = [d.date().isoformat() for d in daily.index]
    atr_s = ind.atr(daily, ATR_BARS).to_numpy(float)
    tb, sb = TREND_BARS.get(tf, 200), TREND_SLOPE_BARS.get(tf, 21)
    trend = ind.sma(daily["close"], tb).to_numpy(float)
    vavg = pd.Series(v).rolling(RVOL_BARS).mean().shift(1).to_numpy(float)
    n = len(c)
    first = 0
    if years:
        cut = daily.index[-1] - pd.DateOffset(years=years)
        first = int(np.searchsorted(daily.index.values, np.datetime64(cut)))
    out, j, blocked = [], max(ATR_BARS + 1, first), -1
    raw: list[tuple] = []   # per zone in `out`: (base start, departure start, departure end, ATR) — to re-run a merge
    while j < n:
        atr = atr_s[j - 1]
        found = None
        if atr == atr and atr > 0:
            b0 = _base(o, h, l, c, j - 1, atr)
            if b0 is not None and b0 > blocked:
                bh, bl = h[b0:j], l[b0:j]
                tops, bots = np.maximum(o[b0:j], c[b0:j]), np.minimum(o[b0:j], c[b0:j])
                for kind, sign in (("demand", 1), ("supply", -1)):
                    prox = float(tops.max()) if sign > 0 else float(bots.min())
                    dist = float(bl.min()) if sign > 0 else float(bh.max())
                    e = _departure(o, h, l, c, j, sign, prox, float(bh.max()) if sign > 0 else float(bl.min()), atr)
                    if e is not None:
                        found = (kind, sign, b0, e, prox, dist)
                        break
        if found is None:
            j += 1
            continue
        kind, sign, b0, e, prox, dist = found
        z = _zone(kind, sign, b0, j, e, prox, dist, atr, o, h, l, c, v, vavg, trend, sb, dates, tf)
        # One area, one zone: a base built inside a same-kind zone that is still active is that zone seen
        # again. Merge into the earlier one — edges the union, its life (tests, failure) re-run once.
        lo, hi = min(prox, dist), max(prox, dist)
        host = next((k for k in range(len(out) - 1, -1, -1)
                     if out[k]["kind"] == kind and (out[k]["failed"] is None or out[k]["failed"] > z["base_from"])
                     and min(out[k]["proximal"], out[k]["distal"]) <= hi and max(out[k]["proximal"], out[k]["distal"]) >= lo), None)
        if host is not None:
            hz, args = out[host], raw[host]
            mprox = max(hz["proximal"], prox) if sign > 0 else min(hz["proximal"], prox)
            mdist = min(hz["distal"], dist) if sign > 0 else max(hz["distal"], dist)
            m = _zone(kind, sign, args[0], args[1], args[2], mprox, mdist, args[3], o, h, l, c, v, vavg, trend, sb, dates, tf)
            m["merged"] = hz.get("merged", []) + [z["base_from"]]
            out[host] = m
        else:
            out.append(z)
            raw.append((b0, j, e, atr))
        blocked, j = e, e + 1   # the next base cannot reach back into this departure
    return out


def _zone(kind, sign, b0, j, e, prox, dist, atr, o, h, l, c, v, vavg, trend, sb, dates, tf) -> dict:
    n = len(c)
    width = abs(prox - dist)
    travel = sign * (max(c[j:e + 1]) if sign > 0 else min(c[j:e + 1])) - sign * prox
    # the leg into the base: over LEGIN_BARS, or LEGIN_LONG_BARS when that is too small to tell
    lead = c[b0 - 1] - c[max(0, b0 - 1 - LEGIN_BARS)] if b0 > 0 else 0.0
    if abs(lead) < LEGIN_MIN_ATR * atr and b0 > 0:
        lead = c[b0 - 1] - c[max(0, b0 - 1 - LEGIN_LONG_BARS)]
    leg = "up" if lead > 0 else "down"
    s0 = max(0, j - STRUCTURE_BARS)
    ref = h[s0:j].max() if sign > 0 else l[s0:j].min()
    far = c[j:e + 1].max() if sign > 0 else c[j:e + 1].min()
    rv = [v[k] / vavg[k] for k in range(j, e + 1) if vavg[k] == vavg[k] and vavg[k] > 0]
    rvol = float(max(rv)) if rv else None
    t_now, t_was = trend[e], trend[e - sb] if e - sb >= 0 else np.nan
    with_trend = None
    if t_now == t_now and t_was == t_was:
        with_trend = bool(sign * (c[e] - t_now) > 0 and sign * (t_now - t_was) > 0)
    gap = bool(sign * (o[j] - (h[b0:j].max() if sign > 0 else l[b0:j].min())) > 0)
    checks = {
        "compact": bool(j - b0 <= COMPACT_BASE_BARS and width <= COMPACT_BASE_ATR * atr),
        "strong": bool(travel >= STRONG_DEPART_ATR * atr),
        "structure": bool(sign * (far - ref) > 0),
        "volume": None if rvol is None else bool(rvol >= RVOL_HIGH),
        "trend": with_trend,
    }
    # its life after the departure: tests (a return into the zone after leaving it) and failure
    tests, inside, failed = [], False, None
    buf = INVALIDATE_BUFFER_ATR * atr
    for t in range(e + 1, n):
        if sign * (c[t] - dist) < -buf:
            failed = dates[t]
            break
        touched = (l[t] <= prox) if sign > 0 else (h[t] >= prox)
        if touched and not inside:
            pierced = (l[t] < dist) if sign > 0 else (h[t] > dist)
            tests.append({"date": dates[t], "price": float(l[t] if sign > 0 else h[t]),
                          "close": float(c[t]), "wick_through": bool(pierced),
                          "rvol": float(v[t] / vavg[t]) if vavg[t] == vavg[t] and vavg[t] > 0 else None})
        inside = touched
    status = "failed" if failed else ("tested" if tests else "fresh")
    passed = sum(1 for x in checks.values() if x)
    return {
        "kind": kind, "code": _CODES[(kind, leg)], "name": _NAMES[(kind, leg)], "tf": tf,
        "base_from": dates[b0], "base_to": dates[j - 1], "base_bars": j - b0,
        "depart_from": dates[j], "depart_to": dates[e],
        "proximal": float(prox), "distal": float(dist), "width_atr": float(width / atr), "atr": float(atr),
        "departure_atr": float(travel / atr), "rvol": rvol, "gap": gap,
        "checks": checks, "passed": passed, "of": len(checks),
        "tests": tests, "status": status, "failed": failed, "worn": len(tests) >= WORN_TESTS,
        "until": failed or dates[n - 1],
    }
