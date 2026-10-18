"""Do support / resistance zones hold more often than chance? — a re-runnable measurement of core/sr_levels.py.

Every `step`-th session of every liquid stock, zones are drawn from the price history up to that day
(`sr_levels.levels`, the chart's own rules, nothing ahead of it). For each displayed zone we wait up to
`wait` sessions for price to reach its near edge. The visit HOLDS if price closes `target` ATR back away
from the near edge before it closes `fail` ATR beyond the far edge, within `horizon` sessions.

The baseline is a placebo with the same geometry: the same distances, in ATRs, from the close of a random
day in the same stock, judged by the same test. Held minus placebo is the measured edge; it is reported
per market, side, timeframe of the zone, grade and visit count, so a change to the rules can be judged.

This is a measurement, not a gate: it does not fail a build. (A rule tuned until it beats a placebo by a
fixed margin on one sample is a rule fitted to that sample.)

Run from scripts/ (8 workers, ~25 min for both markets at step 126):
    PYTHONPATH=. .venv/bin/python -m swing_screener.analytics.level_study --market us india --tf D
    ... --target 0.75 --fail 0.75      # a lenient bounce test
Caveats: today's stock lists only (survivorship), no costs, overlapping windows.
"""

from __future__ import annotations

import argparse
from multiprocessing import Pool

import numpy as np
import pandas as pd

from ..core import indicators as ind
from ..core import sr_levels as sr
from ..marketdata import cache

LIQUID = {"india": (20, 5e7), "us": (5, 5e6)}   # min close, min 50-day average turnover (₹5 crore / $5 million)


def _outcome(h, l, c, start, s, line, far, tgt, wait, horizon):
    """First touch of `line` within `wait` bars of `start`; then hold (close beyond tgt) or fail (close
    beyond far). None when the zone was never reached or the window ran out."""
    n = len(c)
    for t in range(start, min(n, start + wait)):
        if not (l[t] <= line if s > 0 else h[t] >= line):
            continue
        for j in range(t, min(n, t + horizon + 1)):
            if s * (c[j] - far) < 0:
                return "fail"
            if s * (c[j] - tgt) >= 0:
                return "hold"
        return "open" if t + horizon < n else None
    return None


def _one(args):
    market, sym, o = args
    try:
        d = cache.load_cached(market, sym)
        if d is None or len(d) < 800:
            return []
        d = d[~((d.volume <= 0) & (d.high <= d.low))]
        h, l, c = (d[k].to_numpy(float) for k in ("high", "low", "close"))
        atr = ind.atr(d, 14).to_numpy(float)
        turn = (d.close * d.volume).rolling(50).mean().to_numpy(float)
        mc, mt = LIQUID[market]
        rng = np.random.default_rng(abs(hash((market, sym))) % 2**32)
        i0 = max(600, int(np.searchsorted(d.index.values, np.datetime64(o["start"]))))
        out = []
        for i in range(i0, len(d) - o["horizon"] - o["wait"], o["step"]):
            if c[i] < mc or not (turn[i] >= mt) or not (atr[i] > 0):
                continue
            L = sr.levels(d.iloc[:i + 1], o["tf"])
            for z in L["zones"]:
                if z["role"] == "pivot":
                    continue
                s = 1 if z["role"] == "support" else -1
                far = z["bottom"] if s > 0 else z["top"]
                tgt = z["line"] + s * o["target"] * atr[i]
                far_x = far - s * o["fail"] * atr[i]   # the failure line: `fail` ATR beyond the far edge
                res = _outcome(h, l, c, i + 1, s, z["line"], far_x, tgt, o["wait"], o["horizon"])
                if res is None:
                    continue
                r = int(rng.integers(600, len(d) - o["horizon"] - o["wait"]))
                k = atr[r] / atr[i] if atr[r] > 0 else None
                pres = None
                if k:
                    pres = _outcome(h, l, c, r + 1, s, c[r] - (c[i] - z["line"]) * k, c[r] - (c[i] - far_x) * k,
                                    c[r] - (c[i] - tgt) * k, o["wait"], o["horizon"])
                out.append({"market": market, "side": z["role"], "zone_tf": z["tf"], "score": z["score"],
                            "visits": len(z["touches"]), "promoted": bool(z.get("promoted")),
                            "held": res, "placebo": pres})
        return out
    except Exception:  # noqa: BLE001 — one bad symbol must not stop the study
        return []


def run(markets=("us", "india"), tf="D", step=126, wait=63, horizon=60, target=2.0, fail=0.0,
        start="2012-01-01", workers=8, limit=None) -> pd.DataFrame:
    o = {"tf": tf, "step": step, "wait": wait, "horizon": horizon, "target": target, "fail": fail, "start": start}
    jobs = [(m, s, o) for m in markets for s in sorted(cache.cached_symbols(m))[:limit]]
    with Pool(workers) as p:
        rows = [r for part in p.imap_unordered(_one, jobs, chunksize=4) for r in part]
    return pd.DataFrame(rows)


def summary(df: pd.DataFrame, by=("market", "side")) -> pd.DataFrame:
    d = df[df.placebo.notna() & df.held.isin(["hold", "fail", "open"])]
    g = d.groupby(list(by), observed=True)
    t = pd.DataFrame({"visits": g.size(),
                      "held_%": g.held.apply(lambda x: (x == "hold").mean() * 100),
                      "placebo_%": g.placebo.apply(lambda x: (x == "hold").mean() * 100)})
    t["edge_pts"] = t["held_%"] - t["placebo_%"]
    return t.round(1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", nargs="+", default=["us", "india"])
    ap.add_argument("--tf", default="D", choices=["D", "W", "M"])
    ap.add_argument("--step", type=int, default=126)
    ap.add_argument("--target", type=float, default=2.0, help="ATR back away from the near edge that counts as a hold")
    ap.add_argument("--fail", type=float, default=0.0, help="ATR beyond the far edge that counts as a failure")
    ap.add_argument("--limit", type=int, default=None, help="first N symbols per market (a quick look)")
    ap.add_argument("--csv", default=None, help="write the per-visit rows here")
    a = ap.parse_args()
    df = run(a.market, a.tf, a.step, target=a.target, fail=a.fail, limit=a.limit)
    if a.csv:
        df.to_csv(a.csv, index=False)
    print(f"{len(df)} visits")
    for by in (("market", "side"), ("market", "zone_tf"), ("market", "score"), ("market", "promoted")):
        print(summary(df, by), "\n")
