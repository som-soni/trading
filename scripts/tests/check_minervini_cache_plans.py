"""Minervini: a signal-cache hit must build the same plan as a fresh scan.

The backtest's cache-hit path rebuilds a StockContext from the stored `backtest_signals` row
(`backtest._cached_ctx`): 70 daily bars and no weekly frame. Anything `build_plans` reads from the
price frames therefore differs between the two paths. Up to 1.38 the overhead supply that caps the
target was read that way, so SSNC 2017-04-18 was refused fresh (0.85R) and bought from the cache
(2.03R). This replays the review's cases both ways, without touching the database's signal rows;
`--sweep` also compares every setup bar of those symbols, 2013-2021:

    PYTHONPATH=. .venv/bin/python -m tests.check_minervini_cache_plans [--sweep]
"""

import json
import sys

import pandas as pd

from swing_screener.backtesting import backtest as bt
from swing_screener.config import MARKETS
from swing_screener.core import context as ctx_mod
from swing_screener.marketdata import cache
from swing_screener.strategies import get_strategy

# (market, symbol, signal date): the cases the 31 Oct 2026 review found disagreeing under 1.38
CASES = (
    ("us", "SSNC", "2017-04-18"),
    ("us", "IONS", "2017-07-07"),
    ("us", "LAZ", "2017-07-21"),
    ("us", "FRT", "2021-09-09"),
)


def _plan(strategy, ctx, result, cfg):
    choice = strategy.build_plans(ctx, result, cfg)
    p = choice.chosen
    return (None, choice.reason) if p is None else ((round(p.entry, 4), round(p.stop, 4), round(p.target, 4),
                                                     p.r_multiple), choice.reason)


def compare(market: str, symbol: str, date: str, raw=None, frames=None) -> tuple[bool | None, str]:
    """(True when both paths agree, None when the bar has no setup, the line to print)."""
    strategy, cfg, day = get_strategy("minervini"), MARKETS[market], pd.Timestamp(date)
    if raw is None:
        raw = cache.load_cached(market, symbol)
        raw = raw[raw.index <= day]
    ctx = ctx_mod.build_context(symbol, raw, earnings_days_away=None,
                                frames=frames or ctx_mod.prepare_frames(raw), as_of=day)
    result = strategy.evaluate(ctx)
    if not (result.hard_gates_passed and result.has_setup):
        return None, f"{symbol} {date}: no setup fresh ({result.first_hard_fail})"
    # the row the backtest writes right after evaluate(), read back the way a cache hit reads it
    row = bt._signal_row(market, strategy, symbol, day, ctx, result)
    vals = dict(zip(bt._SIGNAL_FIELDS, row[4:-1]))
    for k in ("hard_gates", "setups", "overhead_levels", "watch_flags", "watch_notes", "extras"):
        vals[k] = json.loads(vals[k])
    cached_result = bt._cached_result(strategy, vals)
    if cached_result is None:
        return False, f"{symbol} {date}: the stored row cannot stand in for a scan"
    cached_ctx = bt._cached_ctx(market, symbol, day, vals, tail=True)
    fresh, cached = _plan(strategy, ctx, result, cfg), _plan(strategy, cached_ctx, cached_result, cfg)
    same = fresh[0] == cached[0]
    return same, f"{symbol} {date}: fresh {fresh[0] or fresh[1]} | cache {cached[0] or cached[1]}"


def sweep(market: str, symbol: str, start="2013-01-01", end="2021-12-31") -> tuple[int, int]:
    """(setup bars compared, bars that disagree) over every bar of `symbol` in the window."""
    raw = cache.load_cached(market, symbol)
    raw = raw[raw.index <= pd.Timestamp(end)]
    frames, n, bad = ctx_mod.prepare_frames(raw), 0, 0
    for day in raw.index[260:][raw.index[260:] >= pd.Timestamp(start)]:   # a year of history first
        try:
            same, line = compare(market, symbol, str(day.date()), raw, frames)
        except Exception:  # noqa: BLE001 -- a bar the context cannot be built for is not a comparison
            continue
        if same is None:
            continue
        n += 1
        if not same:
            bad += 1
            print("DIFF  " + line)
    return n, bad


def main() -> None:
    bad = 0
    for case in CASES:
        same, line = compare(*case)
        print(("ok    " if same else "DIFF  ") + line)
        bad += not same
    if "--sweep" in sys.argv:
        for market, symbol, _ in CASES:
            n, b = sweep(market, symbol)
            print(f"sweep {symbol}: {n} setup bars, {b} disagree")
            bad += b
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
