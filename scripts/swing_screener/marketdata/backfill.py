"""Universe-wide long-history backfill.

Why this is needed
------------------
The incremental cache only ever extends the tail; it will not fetch MORE
history before an existing start date. Every backtest so far therefore ran
on ~2 years of data — a single bull market. A trend-following system earns
its keep by sidestepping bear markets, so testing it only across a rising
tape measures the one environment where it is structurally handicapped (it
sits partly in cash while the index compounds). Judging the strategy needs
a window containing 2015-16, Q4 2018, the 2020 crash and the 2022 bear.

    python3 -m swing_screener.marketdata.backfill --market us --years 16
    python3 -m swing_screener.marketdata.backfill --market us --years 16 --only-short

Checkpoints after every batch, so an interrupted run resumes cheaply
rather than restarting the whole fetch.

A caveat this does NOT fix, and makes worse: the ticker list is today's
listed names. Reaching further back means a larger share of the companies
that existed then are missing, because they were delisted or acquired.
Returns are biased upward as a result. Only point-in-time constituent data
fixes it; the bias is reported in every backtest's caveat block.
"""

import argparse
import logging
import time

import pandas as pd

from . import cache, universe
from ..config import MARKETS
from ..providers import YFinanceProvider

logger = logging.getLogger("backfill")

TRADING_DAYS_PER_YEAR = 252


def backfill_market(
    market: str, years: float = 16.0, batch_size: int = 50,
    only_short: bool = False, min_existing_bars: int | None = None,
) -> dict:
    """Fetch `years` of daily history for every symbol in the universe.

    `only_short` skips symbols whose cache already holds at least
    `min_existing_bars` (default: 95% of the requested span), so a re-run
    after an interruption only fetches what is actually missing."""
    cfg = MARKETS[market]
    want_bars = int(years * TRADING_DAYS_PER_YEAR)
    threshold = min_existing_bars if min_existing_bars is not None else int(want_bars * 0.95)

    tickers = universe.load_universe(market)
    # The benchmark, broad indices AND sector indices are all needed: the
    # sector ones drive the sector-regime table in every daily report, and
    # omitting them here left 10 of India's 12 sector indices with no data
    # while their tickers were perfectly valid.
    extras = [
        cfg.benchmark_ticker,
        *cfg.broad_index_symbols.values(),
        *cfg.sector_index_map.values(),
    ]
    todo = list(dict.fromkeys([*tickers, *[e for e in extras if e]]))

    if only_short:
        keep = []
        for sym in todo:
            existing = cache.load_cached(market, sym)
            if existing is None or len(existing) < threshold:
                keep.append(sym)
        logger.info(
            "%s: %d/%d symbols need deeper history (have < %d bars)",
            market, len(keep), len(todo), threshold,
        )
        todo = keep

    provider = YFinanceProvider()
    stats = {"requested": len(todo), "fetched": 0, "failed": 0, "bars": 0}
    t0 = time.time()

    for i in range(0, len(todo), batch_size):
        chunk = todo[i : i + batch_size]
        try:
            got = provider.get_many_daily_bars(chunk, lookback_days=want_bars, batch_size=batch_size)
        except Exception as e:
            logger.warning("batch %d failed entirely (%s); continuing", i // batch_size, e)
            stats["failed"] += len(chunk)
            continue

        for sym, df in got.items():
            if df is None or df.empty:
                continue
            # checkpoint per symbol: an interrupted run keeps everything
            # already written instead of discarding the batch
            cache.save_cached(market, sym, df)
            stats["fetched"] += 1
            stats["bars"] += len(df)
        stats["failed"] += len(chunk) - len(got)

        done = min(i + batch_size, len(todo))
        rate = done / max(time.time() - t0, 1e-9)
        eta = (len(todo) - done) / rate if rate > 0 else float("nan")
        logger.info(
            "%s: %d/%d symbols, %d saved, %.1f sym/s, ETA %.0f min",
            market, done, len(todo), stats["fetched"], rate, eta / 60,
        )

    logger.info(
        "%s: done in %.1f min — %d saved, %d failed, %.1fM bars",
        market, (time.time() - t0) / 60, stats["fetched"], stats["failed"],
        stats["bars"] / 1e6,
    )
    return stats


def coverage_report(market: str) -> pd.DataFrame:
    """How much history the cache actually holds, so a backtest window can
    be chosen from fact rather than hope."""
    tickers = universe.load_universe(market)
    rows = []
    for sym in tickers:
        d = cache.load_cached(market, sym)
        if d is None or d.empty:
            rows.append({"symbol": sym, "bars": 0, "first": None, "last": None})
        else:
            rows.append({
                "symbol": sym, "bars": len(d),
                "first": d.index[0].date(), "last": d.index[-1].date(),
            })
    return pd.DataFrame(rows)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Backfill long daily history for a whole universe")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--years", type=float, default=16.0)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument(
        "--only-short", action="store_true",
        help="skip symbols that already have (nearly) the requested history — "
        "use this to resume an interrupted backfill",
    )
    ap.add_argument("--report", action="store_true", help="print coverage and exit")
    args = ap.parse_args()

    if args.report:
        df = coverage_report(args.market)
        print(f"symbols: {len(df)}")
        print(f"with no data: {(df.bars == 0).sum()}")
        print(df.bars.describe().to_string())
        if (df.bars > 0).any():
            print("\nearliest bar per decile of history length:")
            print(df[df.bars > 0].sort_values("bars").iloc[:: max(1, len(df) // 10)][
                ["symbol", "bars", "first", "last"]
            ].to_string(index=False))
        return

    backfill_market(
        args.market, years=args.years, batch_size=args.batch_size,
        only_short=args.only_short,
    )


if __name__ == "__main__":
    main()
