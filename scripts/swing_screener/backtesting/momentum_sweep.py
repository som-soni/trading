"""Re-choose the stock-ranking momentum variant the way momentum_vol_scaled was first chosen.

Why this exists
---------------
momentum_vol_scaled (vol_scaled / top 20 / inverse_vol) was picked in October 2026 from an
18-variant sweep, judged on its WORST half-period excess over its segment index rather than on
full-window CAGR, and then walk-forward tested -- choosing a variant each year from trailing data
only and chaining the picks forward (research/selection-vs-drag.md §4b). Neither step was ever
committed as code, so neither could be repeated when the ground moved. It moved twice: v1.1 took
ETFs and liquid funds out of the universe, after which the walk-forward kept only 58% of the
hindsight pick's excess instead of 86%, and v1.2 added a rank buffer the sweep never saw.

What it does
------------
Runs every variant in GRID through `baseline.run` on prices loaded once, then reports, per variant:
full-window excess over the strategy's segment index (compounded, CAGR minus the index's CAGR over
the same days), excess in each half of the window either side of SPLIT, the worse of the two,
rolling 36-month excess, drawdown and turnover; and, across variants, a walk-forward that picks
the best trailing-WF_TRAIL_YEARS variant at each year-end and holds it for the next year.

Choose on `worst_half`, then read the walk-forward: a variant that wins only one half is a regime
bet, and a walk-forward far below the hindsight pick says the choice was luck.

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.momentum_sweep --market india
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging
import sys
import time
from pathlib import Path

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from . import baseline as bl

logger = logging.getLogger(__name__)

STRATEGY = "momentum_vol_scaled"      # its universe, costs and segment index are the sweep's frame
SPLIT = pd.Timestamp("2019-01-01")    # the original sweep's half-period cut
WF_TRAIL_YEARS = 3                    # trailing window a walk-forward pick is scored on
ROLL_MONTHS = 36

GRID = {
    "rank": ("momentum", "vol_scaled", "residual"),
    "top_n": (20, 50),
    "weighting": ("equal", "inverse_vol"),
    "buffer": (False, True),          # True = hold_rank of 1.5 x top_n
}


def variants() -> list[dict]:
    keys = list(GRID)
    out = []
    for combo in itertools.product(*GRID.values()):
        v = dict(zip(keys, combo))
        v["hold_rank"] = int(v["top_n"] * 1.5) if v.pop("buffer") else None
        v["name"] = (f"{v['rank']}/top{v['top_n']}/{v['weighting']}"
                     + (f"/hold{v['hold_rank']}" if v["hold_rank"] else ""))
        out.append(v)
    return out


def _cagr(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 2 or s.iloc[0] <= 0:
        return float("nan")
    years = (s.index[-1] - s.index[0]).days / 365.25
    return ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100 if years > 0 else float("nan")


def _excess(eq: pd.Series, bench: pd.Series, lo=None, hi=None) -> float:
    e, b = eq.loc[lo:hi], bench.reindex(eq.index).ffill().loc[lo:hi]
    return _cagr(e) - _cagr(b)


def segment_benchmark(market: str) -> tuple[str, pd.Series]:
    """The strategy's declared segment index, resolved exactly as baseline.main resolves it."""
    from ..strategies import portfolio_strategies
    cls = portfolio_strategies()[STRATEGY]
    cfg = MARKETS[market]
    key = (getattr(cls, "benchmark_key", None) or {}).get(market)
    ticker = cfg.broad_index_symbols.get(key) if key else None
    raw = cache.load_cached(market, ticker) if ticker else None
    if raw is None:
        ticker, raw = cfg.benchmark_ticker, cache.load_cached(market, cfg.benchmark_ticker)
    return ticker, raw["close"].astype(float)


def sweep(market: str, start: str, preloaded=None) -> dict:
    from ..strategies import portfolio_strategies
    cls = portfolio_strategies()[STRATEGY]
    ticker, bench = segment_benchmark(market)
    if preloaded is None:
        preloaded = bl.load_prices(market, min_bars=cls.lookback + cls.skip + 2)
    curves, rows = {}, []
    for v in variants():
        t0 = time.time()
        tdf, perf, eq, _ = bl.run(
            market=market, start=start, top_n=v["top_n"], lookback=cls.lookback, skip=cls.skip,
            rebalance=cls.rebalance, cost_bps=cls.cost_bps, liquidity_rank_top=(cls.liquidity_top or None),
            min_dollar_volume=cls.min_turnover_for(market), rank=v["rank"], weighting=v["weighting"],
            vol_window=cls.vol_window, hold_rank=v["hold_rank"], preloaded=preloaded,
        )
        eq = eq.astype(float)
        curves[v["name"]] = eq
        years = (eq.index[-1] - eq.index[0]).days / 365.25
        dd = (eq / eq.cummax() - 1).min() * 100
        row = {"variant": v["name"], "excess": _excess(eq, bench), "cagr": _cagr(eq),
               "max_dd": dd, "turnover_x": len(tdf) / max(years, 1e-9) / v["top_n"],
               "sharpe": getattr(perf, "sharpe", float("nan"))}
        if eq.index[0] < SPLIT < eq.index[-1]:
            row["excess_before"] = _excess(eq, bench, hi=SPLIT - pd.Timedelta(days=1))
            row["excess_after"] = _excess(eq, bench, lo=SPLIT)
            row["worst_half"] = min(row["excess_before"], row["excess_after"])
        roll = _rolling_excess(eq, bench)
        if len(roll):
            row.update(roll_median=float(roll.median()), roll_worst=float(roll.min()),
                       roll_positive=float((roll > 0).mean() * 100))
        rows.append(row)
        logger.info("%-40s excess %+6.2f  (%.0fs)", v["name"], row["excess"], time.time() - t0)
    return {"market": market, "start": start, "benchmark": ticker, "rows": rows,
            "walk_forward": walk_forward(curves, bench)}


def _rolling_excess(eq: pd.Series, bench: pd.Series) -> pd.Series:
    """Compounded 36-month excess, sampled quarter-end."""
    q = eq.resample("QE").last()
    b = bench.reindex(eq.index).ffill().resample("QE").last()
    n = ROLL_MONTHS // 3
    out = {}
    for i in range(n, len(q)):
        e = (q.iloc[i] / q.iloc[i - n]) ** (12 / ROLL_MONTHS) - 1
        bb = (b.iloc[i] / b.iloc[i - n]) ** (12 / ROLL_MONTHS) - 1
        out[q.index[i]] = (e - bb) * 100
    return pd.Series(out)


def walk_forward(curves: dict, bench: pd.Series) -> dict:
    """At each year-end pick the best trailing-WF_TRAIL_YEARS variant, hold it the next year.

    Uses only each variant's equity UP TO the pick date to choose, then that variant's return over
    the following year. Compared, over exactly the same years, with the variant that is best over
    the whole window -- the hindsight pick. The ratio is how much of the hindsight result a
    procedure that cannot see the future keeps.
    """
    first = min(c.index[0] for c in curves.values())
    last = max(c.index[-1] for c in curves.values())
    ends = [pd.Timestamp(f"{y}-12-31") for y in range(first.year + WF_TRAIL_YEARS, last.year)]
    b = bench.reindex(sorted(set().union(*[c.index for c in curves.values()]))).ffill()
    growth_wf = growth_b = 1.0
    picks = []
    for y_end in ends:
        lo = y_end - pd.DateOffset(years=WF_TRAIL_YEARS)
        trail = {k: _excess(c, b, lo=lo, hi=y_end) for k, c in curves.items()}
        trail = {k: v for k, v in trail.items() if v == v}
        if not trail:
            continue
        pick = max(trail, key=trail.get)
        nxt_hi = min(y_end + pd.DateOffset(years=1), last)
        c = curves[pick].loc[y_end:nxt_hi]
        bb = b.loc[y_end:nxt_hi]
        if len(c) < 2:
            continue
        growth_wf *= c.iloc[-1] / c.iloc[0]
        growth_b *= bb.iloc[-1] / bb.iloc[0]
        picks.append({"year": y_end.year + 1, "pick": pick, "trailing_excess": round(trail[pick], 2)})
    if not picks:
        return {}
    wf_lo = pd.Timestamp(f"{picks[0]['year']}-01-01") - pd.Timedelta(days=1)
    wf_hi = min(pd.Timestamp(f"{picks[-1]['year']}-12-31"), last)
    years = (wf_hi - wf_lo).days / 365.25
    wf_ex = ((growth_wf ** (1 / years)) - (growth_b ** (1 / years))) * 100
    hind = {k: _excess(c, b, lo=wf_lo, hi=wf_hi) for k, c in curves.items()}
    best = max(hind, key=hind.get)
    return {"years": f"{picks[0]['year']}-{picks[-1]['year']}", "walk_forward_excess": round(wf_ex, 2),
            "hindsight_pick": best, "hindsight_excess": round(hind[best], 2),
            "retention_pct": round(wf_ex / hind[best] * 100, 0) if hind[best] > 0 else None,
            "picks": picks}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--start", action="append", default=None,
                    help="window start; repeatable -- each start is a separate set of runs (default 2010-01-01)")
    ap.add_argument("--out", default=None, help="write the results as JSON here")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    from ..strategies import portfolio_strategies
    cls = portfolio_strategies()[STRATEGY]
    starts = args.start or ["2010-01-01"]
    with cache.offline():
        pre = bl.load_prices(args.market, min_bars=cls.lookback + cls.skip + 2)
        results = [sweep(args.market, s, preloaded=pre) for s in starts]
    for r in results:
        print(f"\n=== {r['market']} from {r['start']}  vs {r['benchmark']} ===")
        df = pd.DataFrame(r["rows"]).set_index("variant")
        key = "worst_half" if "worst_half" in df else "excess"
        print(df.sort_values(key, ascending=False).round(2).to_string())
        wf = r["walk_forward"]
        if wf:
            print(f"\nwalk-forward {wf['years']}: {wf['walk_forward_excess']:+.2f} vs hindsight "
                  f"{wf['hindsight_pick']} {wf['hindsight_excess']:+.2f}  (keeps {wf['retention_pct']}%)")
            for p in wf["picks"]:
                print(f"   {p['year']}: {p['pick']}  (trailing {p['trailing_excess']:+.2f})")
    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
