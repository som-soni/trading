"""Bring the local price cache up to date — and nothing else.

Refreshing prices already happens, but only as a side effect of running a
screener, which is backwards in two ways: you cannot get current data without
also producing a report you may not want, and every screener pays the pull
again. On a 3,400-name universe the pull is roughly 685 seconds against 14
seconds of indicator work, so it is ~98% of a screener's runtime.

Splitting it out lets a morning look like:

    python3 -m swing_screener.marketdata.refresh --market india
    python3 -m swing_screener.marketdata.refresh --market us
    python3 -m swing_screener.screening.daily --strategies all --no-refresh

where the slow part runs once instead of once per market per strategy.

This is the DAILY TAIL, not history. It asks each symbol's provider only for
bars after the last cached date (see `cache.get_bars`), so a second run on the
same day is nearly free. For deep history — a new universe, or extending
further back — use `marketdata.backfill`, which is a different job.
"""

import argparse
import logging
import time

import pandas as pd

from ..config import MARKETS
from ..providers import YFinanceProvider
from . import cache, universe

logger = logging.getLogger("refresh")

# enough to recompute every indicator the screeners need (200-day average plus
# a 52-week window, with headroom for holidays)
DEFAULT_LOOKBACK_DAYS = 420


def refresh(
    market: str, symbols: list[str] | None = None,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS, batch_size: int = 50,
    force: bool = False,
) -> dict:
    tickers = symbols if symbols else sorted(universe.load_universe(market))
    logger.info("Refreshing %d %s symbols (lookback %d days)...",
                len(tickers), market, lookback_days)

    t0 = time.time()
    bars, failed = cache.get_many_bars(
        YFinanceProvider(), market, tickers, lookback_days,
        batch_size=batch_size, force=force,
    )
    elapsed = time.time() - t0

    # report the freshness actually achieved, not just the count: a symbol that
    # silently stopped updating looks identical to a fresh one in a bare total
    latest: dict[str, pd.Timestamp] = {}
    for sym, df in bars.items():
        if df is not None and not df.empty:
            latest[sym] = df.index[-1]
    newest = max(latest.values()) if latest else None
    stale = (
        [s for s, d in latest.items() if (newest - d).days > 5] if newest else []
    )
    return {
        "market": market, "requested": len(tickers), "updated": len(bars),
        "failed": failed, "elapsed_s": round(elapsed, 1),
        "newest_bar": newest, "stale": stale,
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(
        description="Pull the latest daily bars into the local cache")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--symbols", default=None,
                    help="comma-separated subset, e.g. NVDA,MU (default: whole universe)")
    ap.add_argument("--lookback-days", type=int, default=DEFAULT_LOOKBACK_DAYS)
    ap.add_argument("--batch-size", type=int, default=50)
    ap.add_argument("--force", action="store_true",
                    help="re-fetch every symbol's tail even if it looks current")
    ap.add_argument("--quiet-stale", action="store_true",
                    help="do not list symbols whose newest bar lags the market")
    args = ap.parse_args()

    syms = ([s.strip() for s in args.symbols.split(",") if s.strip()]
            if args.symbols else None)
    from .. import runlog
    with runlog.track("prices", market=args.market, label=f"{MARKETS[args.market].name} prices") as st:
        r = refresh(args.market, syms, args.lookback_days, args.batch_size, args.force)
        newest = r["newest_bar"].date().isoformat() if r["newest_bar"] is not None else "none"
        st.detail = (f"{r['updated']:,} / {r['requested']:,} symbols · newest bar {newest} · "
                     f"{len(r['failed'])} failed · {len(r['stale'])} lagging · {r['elapsed_s']:.0f}s")

    print()
    print(f"{MARKETS[args.market].name}: {r['updated']:,}/{r['requested']:,} symbols "
          f"updated in {r['elapsed_s']:.0f}s")
    if r["newest_bar"] is not None:
        print(f"  newest bar in the cache: {r['newest_bar'].date()}")
    if r["failed"]:
        print(f"  {len(r['failed'])} failed: "
              f"{', '.join(r['failed'][:10])}{' ...' if len(r['failed']) > 10 else ''}")
    if r["stale"] and not args.quiet_stale:
        # worth surfacing: these are usually delisted, suspended or renamed,
        # and they quietly rot in a universe file until someone looks
        print(f"  {len(r['stale'])} symbols lag the newest bar by >5 days "
              f"(likely delisted or renamed):")
        print(f"    {', '.join(sorted(r['stale'])[:20])}"
              f"{' ...' if len(r['stale']) > 20 else ''}")
    print()
    print("Screeners can now run against warm data, e.g.:")
    print(f"  python3 -m swing_screener.screening.trend_template "
          f"--market {args.market} --no-refresh")


if __name__ == "__main__":
    main()
