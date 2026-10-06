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
    python3 -m swing_screener.marketdata.backfill --market india --max   # everything the source has

`--max` asks for each symbol's full history (US large caps go back to the
1980s, Indian ones to the late 1990s / 2000s), gently: small batches, no
parallel burst, and a pause-and-retry when the source rate-limits. Each
finished symbol is recorded in `backfill_progress`, so a re-run resumes where
it stopped instead of starting over.

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


PROGRESS_SCHEMA = """
CREATE TABLE IF NOT EXISTS backfill_progress (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, mode VARCHAR(16) NOT NULL,
    done_at TIMESTAMPTZ NOT NULL DEFAULT now(), first_date DATE, bars INT,
    PRIMARY KEY (market, symbol, mode)
);
"""


def backfill_max(market: str, batch_size: int = 20, pause: float = 2.0) -> dict:
    """Fetch the full available history of every universe symbol (and the indices the
    pipeline needs), resuming from `backfill_progress`."""
    from . import db
    cfg = MARKETS[market]
    with db.get_connection().cursor() as cur:
        cur.execute(PROGRESS_SCHEMA)
        cur.execute("SELECT symbol FROM backfill_progress WHERE market=%s AND mode='max'", (market,))
        done = {r[0] for r in cur.fetchall()}
    extras = [cfg.benchmark_ticker, *cfg.broad_index_symbols.values(), *cfg.sector_index_map.values()]
    todo = [s for s in dict.fromkeys([*universe.load_universe(market), *[e for e in extras if e]]) if s not in done]
    logger.info("%s: %d symbols to fetch at full history (%d already done)", market, len(todo), len(done))
    provider = YFinanceProvider(pause_sec=pause)
    stats = {"requested": len(todo), "fetched": 0, "empty": 0, "bars": 0}
    t0 = time.time()
    for i in range(0, len(todo), batch_size):
        chunk = todo[i : i + batch_size]
        got = {}
        for attempt, wait in enumerate((0, 60, 300)):
            time.sleep(wait)
            try:
                got = provider.get_many_daily_bars(chunk, 0, batch_size=batch_size, period="max", threads=False, fallback=False)
            except Exception as e:  # noqa: BLE001
                logger.warning("batch %d attempt %d failed: %s", i // batch_size, attempt + 1, e)
                got = {}
            if got:
                break
            # a whole batch empty is almost always a rate limit, not 20 dead tickers: back off and retry
            logger.warning("batch %d returned nothing (rate-limited?) — waiting before retry", i // batch_size)
        rows = []
        for sym in chunk:
            df = got.get(sym)
            if df is not None and not df.empty:
                cache.save_cached(market, sym, df)
                stats["fetched"] += 1
                stats["bars"] += len(df)
                rows.append((market, sym, "max", df.index[0].date(), len(df)))
            elif got:  # the batch worked, this symbol simply has no data (delisted / bad ticker): don't retry it forever
                stats["empty"] += 1
                rows.append((market, sym, "max", None, 0))
        if rows:
            db.execute_values("INSERT INTO backfill_progress (market, symbol, mode, first_date, bars) VALUES %s "
                              "ON CONFLICT (market, symbol, mode) DO UPDATE SET done_at=now(), first_date=EXCLUDED.first_date, bars=EXCLUDED.bars", rows)
        n = min(i + batch_size, len(todo))
        rate = n / max(time.time() - t0, 1e-9)
        logger.info("%s: %d/%d symbols, %d saved, %d empty, %.2f sym/s, ETA %.0f min",
                    market, n, len(todo), stats["fetched"], stats["empty"], rate, (len(todo) - n) / rate / 60 if rate else float("nan"))
    logger.info("%s: done in %.1f min — %d saved, %d empty, %.1fM bars", market, (time.time() - t0) / 60,
                stats["fetched"], stats["empty"], stats["bars"] / 1e6)
    return stats


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
    ap.add_argument("--max", action="store_true", help="fetch each symbol's FULL available history (resumable)")
    args = ap.parse_args()

    if args.max:
        backfill_max(args.market)
        return

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
