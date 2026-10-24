"""Three studies of gaps a single stock suggested -- CRWD's 2026 run, which no strategy here traded in time.

Tracing why CRWD's +120% year produced no timely trade found three rules that might be costing trades
across the whole universe, not just in one stock. One stock is an anecdote; these measure each rule
on every liquid stock, so the answer is "the rule is earning its keep" or "it is a real gap", not a
fit to the one example that raised the question.

1. TREND LAG -- every trend gate here (close above the 200-day, the 50 above the 200, the Trend
   Template's 50 > 150 > 200 stack) repairs slowly after a fall, so a V-shaped recovery is invisible
   during its strongest phase. Events: a stock that fell 30%+ from its 52-week high and closed below
   its 200-day, then closes back ABOVE the 200-day. Compare what happens from that reclaim with what
   happens from the day the averages stack -- the day a Trend-Template strategy would first admit it.

2. STOP WIDTH -- breakout and chart_pattern refuse a stop more than 8% below entry, stage_analysis
   one more than 15%, earnings_gaps one more than 1.5 ATR. Big winners are disproportionately
   volatile, so a fixed cap may exclude exactly them. Events: a breakout to a new 55-day high above
   the 200-day on 1.5x volume, with the natural stop under the last 10 sessions' low. Bucket by how
   wide that stop is, and measure each bucket in R.

3. VOLUME vs SIZE -- breakout, stage and earnings-gap rules ask for 1.5-3x average volume, and a
   heavily traded stock rarely triples its average. Events: up days of 8% or more. Measure relative
   volume by liquidity quintile, and forward return by relative volume within each size band.

All three run inside the OPTIMISE stage (backtesting/windows.py): they exist to inform rule changes,
so they may not see the verify years. The data boundary stops every price read at the stage's end,
and forward windows that would cross it are not counted.

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.gap_studies --market us
"""

import argparse
import json
import logging
import warnings

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, universe
from ..paths import REPORTS_DIR
from . import windows

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

START = "2013-01-01"            # events from here; earlier bars only warm the averages up
DRAWDOWN = 0.30                 # study 1: the fall that arms a reclaim
STACK_WITHIN = 252              # study 1: sessions allowed for the averages to stack
BREAKOUT_BARS = 55              # study 2: a new high over this many sessions
BREAKOUT_VOL = 1.5              # study 2: and this multiple of the 50-day volume
STOP_LOOKBACK = 10              # study 2: the natural stop sits under this many sessions' low
HOLD = 60                       # study 2: sessions a trade is held when the stop is not hit
COOLDOWN = 20                   # study 2: a breakout counts once; new highs on the following days are the same event
BIG_DAY = 0.08                  # study 3: an up day this large
HORIZONS = (20, 60, 120)
STOP_BUCKETS = [0, 0.05, 0.08, 0.12, 0.15, 1.0]


def _frames(market: str, symbols: list[str], chunk: int = 250):
    for i in range(0, len(symbols), chunk):
        for sym, df in cache.load_many_cached(market, symbols[i:i + chunk]).items():
            if df is not None and len(df) >= 320:
                yield sym, df


def _fwd(close: np.ndarray, t: int, h: int) -> float:
    return close[t + h] / close[t] - 1 if t + h < len(close) else np.nan


def study_symbol(df: pd.DataFrame, bench: pd.Series, floor: float, start: pd.Timestamp) -> dict:
    c, h, l, o, v = (df[k].to_numpy(float) for k in ("close", "high", "low", "open", "volume"))
    s = pd.Series(c, index=df.index)
    sma50, sma150, sma200 = (s.rolling(n).mean().to_numpy() for n in (50, 150, 200))
    hi252 = pd.Series(h).rolling(252).max().to_numpy()
    hi55 = pd.Series(h).rolling(BREAKOUT_BARS).max().shift(1).to_numpy()
    lo10 = pd.Series(l).rolling(STOP_LOOKBACK).min().to_numpy()
    vol50 = pd.Series(v).rolling(50).mean().to_numpy()
    dv20 = pd.Series(c * v).rolling(20).mean().to_numpy()
    tr = np.maximum(h - l, np.maximum(abs(h - np.roll(c, 1)), abs(l - np.roll(c, 1))))
    atr14 = pd.Series(tr).rolling(14).mean().to_numpy()
    b = bench.reindex(df.index).ffill().to_numpy(float)
    first = int(np.searchsorted(df.index.values, np.datetime64(start)))
    out = {"reclaim": [], "breakout": [], "bigday": []}

    # ---- 1. trend lag
    armed = False
    for t in range(max(first, 252), len(c)):
        if np.isnan(sma200[t]) or np.isnan(hi252[t]):
            continue
        if c[t] / hi252[t] - 1 <= -DRAWDOWN and c[t] < sma200[t]:
            armed = True
            continue
        if armed and c[t] > sma200[t] and c[t - 1] <= sma200[t - 1] and dv20[t] >= floor:
            armed = False
            stack = next((k for k in range(t, min(len(c), t + STACK_WITHIN))
                          if c[k] > sma50[k] > sma150[k] > sma200[k]), None)
            fail = bool(np.nanmin(c[t + 1:t + 21] - sma200[t + 1:t + 21]) < 0) if t + 21 <= len(c) else None
            ev = {"fail20": fail, "lag": (stack - t) if stack is not None else None,
                  "before_stack": (c[stack] / c[t] - 1) if stack is not None else None}
            for hz in HORIZONS:
                ev[f"r{hz}"] = _fwd(c, t, hz)
                ev[f"x{hz}"] = ev[f"r{hz}"] - _fwd(b, t, hz)
                if stack is not None:
                    ev[f"s{hz}"] = _fwd(c, stack, hz)
                    ev[f"sx{hz}"] = ev[f"s{hz}"] - _fwd(b, stack, hz)
            out["reclaim"].append(ev)

    # ---- 2. stop width (and 3's volume for the same breakouts)
    last_bo = -10 ** 9
    for t in range(max(first, 252), len(c) - 1):
        if (np.isnan(hi55[t]) or np.isnan(sma200[t]) or c[t] <= hi55[t] or c[t] <= sma200[t]
                or dv20[t] < floor or not vol50[t]):
            continue
        if t - last_bo < COOLDOWN:
            continue
        last_bo = t
        rv = v[t] / vol50[t]
        risk = c[t] - lo10[t]
        if risk <= 0 or np.isnan(risk):
            continue
        stop, R, k = lo10[t], np.nan, None
        for k in range(t + 1, min(len(c), t + 1 + HOLD)):
            if l[k] <= stop:
                fill = o[k] if o[k] < stop else stop       # a gap through the stop fills at the open
                R = (fill - c[t]) / risk
                break
        else:
            if t + HOLD < len(c):
                R = (c[t + HOLD] - c[t]) / risk
        if np.isnan(R):
            continue
        out["breakout"].append({"stop_pct": risk / c[t], "atr_mult": risk / atr14[t] if atr14[t] else np.nan,
                                "R": R, "rv": rv, "r60": _fwd(c, t, 60), "dv": dv20[t]})

    # ---- 3. big up days
    for t in range(max(first, 252), len(c)):
        if t < 1 or not vol50[t] or dv20[t] < floor or c[t] / c[t - 1] - 1 < BIG_DAY:
            continue
        r60 = _fwd(c, t, 60)
        out["bigday"].append({"rv": v[t] / vol50[t], "dv": dv20[t], "r60": r60,
                              "x60": r60 - _fwd(b, t, 60) if not np.isnan(r60) else np.nan})
    return out


def run(market: str) -> dict:
    cfg = MARKETS[market]
    stage, start, end = windows.resolve("optimise")
    events = {"reclaim": [], "breakout": [], "bigday": []}
    with cache.offline(), windows.active(stage, start, end):
        bench = cache.load_cached(market, cfg.benchmark_ticker)["close"]
        syms = universe.load_universe(market)
        logger.info("%s: %d symbols, window %s -> %s", market, len(syms), START, end)
        for n, (sym, df) in enumerate(_frames(market, syms)):
            try:
                r = study_symbol(df, bench, cfg.screener.min_dollar_volume, pd.Timestamp(START))
            except Exception as exc:   # noqa: BLE001 -- one bad series must not end the study
                logger.debug("%s skipped: %s", sym, exc)
                continue
            for k in events:
                events[k].extend(r[k])
            if n and n % 500 == 0:
                logger.info("  %d symbols", n)
    return {k: pd.DataFrame(v) for k, v in events.items()}


def summarise(market: str, ev: dict) -> dict:
    res = {"market": market, "window": f"{START} -> {windows.STAGES['optimise'].end}"}
    rc = ev["reclaim"].dropna(subset=["r120"])
    if len(rc):
        st = rc.dropna(subset=["lag"])
        res["trend_lag"] = {
            "events": int(len(rc)), "stacked_within_a_year": float(len(st) / len(rc)),
            "median_sessions_to_stack": float(st["lag"].median()) if len(st) else None,
            "median_gain_before_stack": float(st["before_stack"].median()) if len(st) else None,
            "fell_back_below_200d_within_20": float(rc["fail20"].mean()),
            "from_reclaim": {f"x{h}": float(rc[f"x{h}"].mean()) for h in HORIZONS},
            "from_stack": {f"x{h}": float(st[f"sx{h}"].dropna().mean()) for h in HORIZONS} if len(st) else None,
            "reclaim_hit_rate_x120": float((rc["x120"] > 0).mean()),
            "stack_hit_rate_x120": float((st["sx120"].dropna() > 0).mean()) if len(st) else None,
        }
    bo = ev["breakout"]
    if len(bo):
        bo["bucket"] = pd.cut(bo["stop_pct"], STOP_BUCKETS, labels=["<5%", "5-8%", "8-12%", "12-15%", ">15%"])
        g = bo.groupby("bucket", observed=False)
        res["stop_width"] = {str(k): {"n": int(len(x)), "avg_R": float(x["R"].mean()), "win": float((x["R"] > 0).mean()),
                                      "PF": float(x.loc[x.R > 0, "R"].sum() / -x.loc[x.R < 0, "R"].sum()) if (x.R < 0).any() else None,
                                      "big_winners_3R": float((x["R"] >= 3).mean()), "fwd60": float(x["r60"].mean())}
                             for k, x in g}
        bo["atr_bucket"] = pd.cut(bo["atr_mult"], [0, 1.5, 2.5, 4, 100], labels=["<=1.5 ATR", "1.5-2.5", "2.5-4", ">4"])
        res["stop_width_atr"] = {str(k): {"n": int(len(x)), "avg_R": float(x["R"].mean()), "fwd60": float(x["r60"].mean())}
                                 for k, x in bo.groupby("atr_bucket", observed=False)}
    bd = ev["bigday"].dropna(subset=["x60"])
    if len(bd):
        bd["size"] = pd.qcut(bd["dv"], 5, labels=["Q1 smallest", "Q2", "Q3", "Q4", "Q5 largest"])
        res["volume_by_size"] = {str(k): {"n": int(len(x)), "median_rv": float(x["rv"].median()),
                                          "share_ge_1_5": float((x["rv"] >= 1.5).mean()),
                                          "share_ge_3": float((x["rv"] >= 3).mean())}
                                 for k, x in bd.groupby("size", observed=False)}
        bd["rvb"] = pd.cut(bd["rv"], [0, 1.5, 3, 1e9], labels=["<1.5x", "1.5-3x", ">=3x"])
        bd["band"] = pd.qcut(bd["dv"], 3, labels=["small", "mid", "large"])
        res["volume_predicts_within_size"] = {
            f"{band}/{rvb}": {"n": int(len(x)), "x60": float(x["x60"].mean())}
            for (band, rvb), x in bd.groupby(["band", "rvb"], observed=False) if len(x)}
    return res


def main(argv: list[str] | None = None) -> dict:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    a = ap.parse_args(argv)
    res = summarise(a.market, run(a.market))
    out = REPORTS_DIR / a.market / "_research"
    out.mkdir(parents=True, exist_ok=True)
    (out / "gap_studies.json").write_text(json.dumps(res, indent=1, default=float))
    print(json.dumps(res, indent=1, default=lambda x: round(float(x), 4)))
    return res


if __name__ == "__main__":
    main()
