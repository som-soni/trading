"""Controlled A/B experiments over one signal set.

Every variant here is simulated against the SAME collected signals and the
same price data, so the only thing that differs is the one knob under test.
Re-running the full scan per variant would let scan-level differences (and
any cache churn) leak into the comparison.

    python3 -m swing_screener.backtesting.experiments --market us --start 2012-01-01 --exits
    python3 -m swing_screener.backtesting.experiments --market us --start 2012-01-01 --caps

`--exits` answers the question the 2-year run raised: does a fixed
measured-move target cap the right tail that trend-following depends on?
`--caps` shows how sensitive the result is to how many positions you are
willing to hold at once.
"""

import argparse
import dataclasses
import logging

import pandas as pd

from ..marketdata import cache

from . import metrics
from .backtest import (
    _point_in_time_candidates,
    collect_portfolio_signals,
    refresh_deep_history,
    REPORT_DIR,
)
from ..config import MARKETS
from .portfolio_sim import ExitPolicy, simulate, trades_to_df
from ..strategies import DEFAULT_STRATEGY, get_strategy, list_strategies

logger = logging.getLogger("experiments")


EXIT_VARIANTS = [
    ExitPolicy(mode="bracket", use_target=True),
    ExitPolicy(mode="trail_atr", use_target=True, atr_mult=3.0),
    ExitPolicy(mode="trail_atr", use_target=False, atr_mult=3.0),
    ExitPolicy(mode="trail_atr", use_target=False, atr_mult=5.0),
    ExitPolicy(mode="ma", use_target=False, ma_col="sma50"),
    ExitPolicy(mode="ma", use_target=False, ma_col="sma20"),
    ExitPolicy(mode="donchian", use_target=False, donchian_bars=50),
    ExitPolicy(mode="donchian", use_target=False, donchian_bars=20),
]


def _row(label: str, perf, result) -> dict:
    closed = [t for t in result.trades if t.exit_reason != "OPEN"]
    holds = [t.holding_days for t in closed]
    return {
        "variant": label,
        "CAGR%": round(perf.cagr_pct, 2),
        "maxDD%": round(perf.max_drawdown_pct, 2),
        "Sharpe": round(perf.sharpe, 2),
        "Sortino": round(perf.sortino, 2),
        "Calmar": round(perf.calmar, 2),
        "excessCAGR%": (
            round(perf.cagr_pct - perf.benchmark_cagr_pct, 2)
            if perf.benchmark_cagr_pct is not None else None
        ),
        "expo%": round(perf.exposure_pct, 1),
        "trades": perf.trades,
        "win%": round(perf.win_rate_pct, 1),
        "avgR": round(perf.avg_r, 3),
        "medHoldDays": int(pd.Series(holds).median()) if holds else 0,
        "turnover": round(perf.turnover_annual, 2),
    }


def run(
    market: str, start: str, strategy_key: str = DEFAULT_STRATEGY,
    limit: int | None = None, deep_lookback_days: int = 4000,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
    which: str = "exits", max_positions: int | None = None,
    refresh: bool = False, sample: int | None = None,
    exit_policy: ExitPolicy | None = None,
) -> pd.DataFrame:
    cfg = MARKETS[market]
    strategy = get_strategy(strategy_key)
    start_ts = pd.Timestamp(start)

    candidates = _point_in_time_candidates(cfg, strategy, market, start_ts)
    # same seeded subset as the main run, so results are comparable
    if sample:
        from .backtest import sample_candidates
        candidates = sample_candidates(candidates, sample)
    elif limit:
        candidates = candidates[:limit]

    deep_data = {}
    if refresh:
        from ..providers import YFinanceProvider
        deep_data = refresh_deep_history(
            YFinanceProvider(), market, candidates, deep_lookback_days,
            start=start_ts, warmup_bars=strategy.min_bars,
        )

    signals, prices = collect_portfolio_signals(
        market, cfg, strategy, start_ts, candidates, deep_data,
        accept_labels=accept_labels,
    )

    bench_raw = cache.load_cached(market, cfg.benchmark_ticker)
    rows = []

    if which == "exits":
        variants = [(v.label(), v, max_positions, cfg) for v in EXIT_VARIANTS]
    elif which == "sizing":
        # Does the book have room to hold the slots it claims? With 10 slots
        # and a 25% notional cap the stated limits sum to 250% of capital, so
        # the account runs out of cash at 8 positions and declines everything
        # after. Vary risk and the notional cap together: risk sets the size a
        # signal asks for, the cap sets the ceiling, and only the pair decides
        # how many positions actually fit.
        base = exit_policy or ExitPolicy()
        variants = [
            (f"risk={r:.1%} cap={c:.0%} {base.label()}", base, max_positions,
             dataclasses.replace(cfg, risk_pct=r, max_position_pct=c))
            for r, c in ((0.010, 0.25), (0.010, 0.15), (0.010, 0.10),
                         (0.005, 0.25), (0.005, 0.10))
        ]
    else:
        base = exit_policy or ExitPolicy()
        variants = [(f"cap={c}", base, c, cfg) for c in (5, 10, 20, 30, 50)]

    for label, policy, cap, vcfg in variants:
        logger.info("simulating variant: %s", label)
        result = simulate(
            signals, prices, vcfg, start_ts, max_positions=cap, exit_policy=policy
        )
        tdf = trades_to_df(result.trades)
        bench_close = (
            bench_raw["close"].reindex(result.equity.index).ffill()
            if bench_raw is not None and not bench_raw.empty else None
        )
        perf = metrics.compute(
            equity=result.equity, positions_open=result.positions_open, trades=tdf,
            max_open_positions=cap or vcfg.max_open_positions,
            costs_paid=result.costs_paid, bench_close=bench_close,
        )
        rows.append(_row(label, perf, result))

    df = pd.DataFrame(rows)
    return df


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Controlled A/B experiments on one signal set")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--strategy", default=DEFAULT_STRATEGY, choices=list_strategies())
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--sample", type=int, default=None, help="seeded random subset (comparable across runs)")
    ap.add_argument("--max-positions", type=int, default=None)
    ap.add_argument("--accept-labels", default="TRADE - HIGH CONFIDENCE")
    ap.add_argument("--refresh", action="store_true", help="deep-refresh candidates first")
    ap.add_argument("--deep-lookback-days", type=int, default=4000)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--exits", action="store_true", help="compare exit policies")
    g.add_argument("--caps", action="store_true", help="compare position caps")
    g.add_argument("--sizing", action="store_true",
                   help="compare risk-per-trade and notional-cap pairs")
    # The sizing and cap sweeps hold the exit policy fixed while varying one
    # other thing, so that policy must be the strategy's real one -- donchian
    # measured with bracket+target exits is not donchian.
    ap.add_argument("--exit-mode", default="bracket",
                    choices=["bracket", "trail_atr", "ma", "donchian"])
    ap.add_argument("--no-target", action="store_true")
    ap.add_argument("--atr-mult", type=float, default=3.0)
    ap.add_argument("--ma-col", default="sma50")
    ap.add_argument("--donchian-bars", type=int, default=50)
    args = ap.parse_args()

    df = run(
        args.market, args.start, strategy_key=args.strategy, limit=args.limit,
        deep_lookback_days=args.deep_lookback_days,
        accept_labels=tuple(x.strip() for x in args.accept_labels.split(",") if x.strip()),
        which=("exits" if args.exits else "sizing" if args.sizing else "caps"),
        exit_policy=ExitPolicy(
            mode=args.exit_mode, use_target=not args.no_target,
            atr_mult=args.atr_mult, ma_col=args.ma_col,
            donchian_bars=args.donchian_bars,
        ),
        max_positions=args.max_positions, refresh=args.refresh, sample=args.sample,
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    kind = "exits" if args.exits else "sizing" if args.sizing else "caps"
    out = REPORT_DIR / f"{args.market}_{args.strategy}_experiment_{kind}_{args.start}.csv"
    df.to_csv(out, index=False)
    print()
    print(df.to_string(index=False))
    print(f"\n-> {out}")
    print(
        "\nRead 'excessCAGR%' first: a variant that raises CAGR while raising maxDD "
        "by more has not improved anything."
    )


if __name__ == "__main__":
    main()
