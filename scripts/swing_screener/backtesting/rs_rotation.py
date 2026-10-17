"""RS leaders, held as a portfolio instead of traded as swings.

WHY THIS EXISTS. `strategies/rs_leaders.py` has the only positive SELECTION number among the
per-symbol strategies in both markets (+1.40 India, +0.27 US: the strategy against the index held
at the strategy's own exposure). It still loses to buy-and-hold by ~9 CAGR points, because it is
invested 17-19% of the time and the idle cash gives back ~10. The decomposition says the signal is
not the problem; the deployment is. See `research/selection-vs-drag.md`.

So this asks the signal's question with the drag removed: hold the leaders when the market is in a
confirmed recovery, hold the INDEX the rest of the time, never cash. Fully invested by
construction, so there is no drag to lose and the headline excess IS the selection number.

WHAT IS AND IS NOT SHARED. The recovery state machine is imported from `rs_leaders` -- it is the
same rule, not a copy, so tuning the correction thresholds moves both. Eligibility (turnover
floor, above the 200-day, price floor) is `baseline.eligible_scores`, the same function the
momentum book and its live view use. The accounting is `rotation.simulate`. What this module adds
is only the DECISION: which of the two books to hold, and which names go in the first one.

What it deliberately does NOT reuse is the per-stock entry: no pivot, no breakout trigger, no
stop, no target. Those are what make the swing version sit in cash, and testing whether the
selection survives without them is the entire point.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from ..strategies.base import PortfolioStrategy
from ..strategies.rs_leaders import RsLeadersStrategy
from . import baseline, metrics, rotation

logger = logging.getLogger("backtest")

BENCH_COL = "__INDEX__"          # the benchmark as a holdable column, so "risk off" is still invested
TRADING_DAYS = baseline.TRADING_DAYS


def load_frame(market: str, min_bars: int) -> tuple:
    """(close+index frame, dollar volume, SMA200, benchmark close).

    The benchmark is appended to the price frame as a column so `rotation.simulate` can hold it
    like any other series. It is excluded from the candidate ranking by name, not by filtering
    the universe, so it can never be picked as a "leader".
    """
    px, dv, sma200 = baseline.load_prices(market, min_bars=min_bars)
    cfg = MARKETS[market]
    raw = cache.load_cached(market, cfg.benchmark_ticker)
    if raw is None or raw.empty:
        raise SystemExit(f"no stored prices for the {market} benchmark {cfg.benchmark_ticker}")
    bench = raw["close"].astype(float)
    px = px.copy()
    px[BENCH_COL] = bench.reindex(px.index).ffill()
    return px, dv, sma200, bench


def run(market: str, start: str, top_n: int = 10, lookback: int = TRADING_DAYS,
        skip: int = 21, rebalance: str = "ME", rank: str = "rs_range",
        cost_bps: float = 50.0, min_dollar_volume: float | None = None,
        liquidity_rank_top: int | None = None, recovery_gate: bool = True,
        preloaded: tuple | None = None):
    """Hold the top `top_n` leaders while the market is in a confirmed recovery, else the index.

    `recovery_gate=False` holds the leaders on EVERY rebalance instead. That is the control, and it
    is the only way to attribute a result: with the gate on, three things are being tested at once
    (the RS ranking, the recovery timing, and the absence of per-trade entries), and a bad number
    says nothing about which. Turning the gate off isolates the timing.
    """
    cfg = MARKETS[market]
    liq_floor = cfg.screener.min_dollar_volume if min_dollar_volume is None else min_dollar_volume

    px, dv, sma200, bench = preloaded if preloaded is not None else load_frame(
        market, min_bars=lookback + skip + 2)
    candidates = [c for c in px.columns if c != BENCH_COL]

    # The SAME state machine the swing strategy gates on -- imported, not restated.
    recovery = RsLeadersStrategy._recovery_days(market) or set()
    scores = baseline.score_matrix(px[candidates], rank, lookback, skip, benchmark=bench)

    chosen: dict = {}

    def pick(d, _ret, _px):
        if recovery_gate and d not in recovery:
            return [BENCH_COL]
        mom = baseline.eligible_scores(
            candidates, px.loc[d],
            dv.loc[d] if d in dv.index else None,
            sma200.loc[d] if d in sma200.index else None,
            scores.loc[d] if d in scores.index else None,
            floor_price=cfg.screener.min_price, liq_floor=liq_floor,
            trend_filter=True, liquidity_rank_top=liquidity_rank_top,
        )
        held = sorted(mom, key=mom.get, reverse=True)[:top_n]
        # An armed recovery with nothing eligible is still risk-on; hold the index rather than
        # cash, so this strategy never has a drag term to hide behind.
        chosen[d] = held
        return held or [BENCH_COL]

    tdf, eq, pos, costs = rotation.simulate(
        px, pick, start=start, rebalance=rebalance, cost_bps=cost_bps,
        account_size=cfg.account_size, lookback_days=lookback)

    rebals = rotation.rebalance_dates(px.index, pd.Timestamp(start), rebalance)
    in_rec = sum(1 for d in rebals if d in recovery)
    notes = [
        (f"Fully invested by construction: leaders on {in_rec} of {len(rebals)} rebalance dates "
         f"({in_rec / max(len(rebals), 1):.0%}), the index on the rest. There is no cash position, "
         "so the excess CAGR below IS the selection number -- no drag term."
         if recovery_gate else
         "CONTROL RUN: the recovery gate is OFF, so the leaders are held on every rebalance date. "
         "Compare against the gated run to attribute the result to the timing rather than the rank."),
        f"Ranked on '{rank}' over {lookback} bars skipping {skip}; eligibility is a "
        f"{liq_floor:,.0f} turnover floor plus above the 200-day average.",
        "The recovery condition is imported from the rs_leaders swing strategy, so both read the "
        "same market state.",
        "SURVIVORSHIP BIAS: the universe is today's listed names.",
        f"Costs modelled: {cost_bps:.0f}bps per side on each rebalance.",
    ]
    perf = metrics.compute(eq, pos, tdf, top_n, costs_paid=costs,
                           bench_close=bench.reindex(eq.index).ffill(), notes=notes)
    for k, v in metrics.benchmark_stats(bench.reindex(eq.index).ffill()).items():
        setattr(perf, k, v)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"
    return tdf, perf, eq, pos
