"""Daily wrapper: runs both markets, auto-refreshes a stale universe list,
isolates failures (one market crashing doesn't block the other), logs to
both console and a dated file, and prints one cross-market summary at the
end instead of two separate scrolls of output.

Usage:
    python3 -m swing_screener.daily
    python3 -m swing_screener.daily --markets us
    python3 -m swing_screener.daily --refresh-stale-days 3
    python3 -m swing_screener.daily --refresh-stale-days -1   # never auto-refresh

Scheduling (macOS cron, run at 7am local time daily):
    0 7 * * * cd /Users/admin/Workspace/trading/scripts && .venv/bin/python3 -m swing_screener.daily >> logs/cron.log 2>&1
"""

import argparse
import logging
import sys
import traceback
from pathlib import Path

import pandas as pd

from . import pipeline, universe
from .config import MARKETS

LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
REFRESH_FNS = {
    "us": universe.fetch_us_universe_from_nasdaqtrader,
    "india": universe.fetch_india_universe_from_yfinance_screener,
}

logger = logging.getLogger("daily")


def _setup_logging() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"daily_{pd.Timestamp.today().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logging.getLogger().addHandler(file_handler)
    return log_path


def _maybe_refresh_universe(market: str, refresh_stale_days: float) -> None:
    if refresh_stale_days < 0:
        return
    age = universe.universe_age_days(market)
    if age is None:
        logger.info("%s: no universe file yet, fetching one now", market)
        REFRESH_FNS[market]()
    elif age > refresh_stale_days:
        logger.info("%s: universe is %.1f days old (> %s), refreshing", market, age, refresh_stale_days)
        REFRESH_FNS[market]()
    else:
        logger.info("%s: universe is %.1f days old, reusing it", market, age)


def run_daily(markets: list[str], refresh_stale_days: float = 7) -> int:
    log_path = _setup_logging()
    logger.info("=== Daily run starting: markets=%s ===", markets)

    reports: dict[str, pd.DataFrame] = {}
    failures: dict[str, str] = {}

    for market in markets:
        print(f"\n{'=' * 60}\n{MARKETS[market].name.upper()}\n{'=' * 60}")
        try:
            _maybe_refresh_universe(market, refresh_stale_days)
            reports[market] = pipeline.run(market, refresh_universe=False)
        except Exception as e:
            logger.exception("%s run failed", market)
            failures[market] = f"{type(e).__name__}: {e}"
            print(f"\n*** {market.upper()} FAILED: {e} ***")
            print(traceback.format_exc())

    _print_cross_market_summary(reports, failures)
    logger.info("=== Daily run finished. Log: %s ===", log_path)
    print(f"\nFull log: {log_path}")

    return 1 if failures else 0


def _print_cross_market_summary(reports: dict[str, pd.DataFrame], failures: dict[str, str]) -> None:
    print(f"\n{'=' * 60}\nCROSS-MARKET SUMMARY\n{'=' * 60}")

    if failures:
        print("Failed markets (see log for full traceback):")
        for market, msg in failures.items():
            print(f"  {market}: {msg}")

    combined = pd.concat(
        [df.assign(market=m) for m, df in reports.items() if df is not None and not df.empty],
        ignore_index=True,
    ) if reports else pd.DataFrame()

    if combined.empty:
        print("\nNo tradeable candidates across either market.")
        return

    tradeable = combined[combined["tradeable"] == True]  # noqa: E712 (nullable bool)
    print(f"\n{len(tradeable)} tradeable candidate(s) across {len(reports)} market(s):")
    if not tradeable.empty:
        cols = ["market", "symbol", "sector", "decision", "strategy_setup", "entry", "stop", "target_r", "risk_pct"]
        cols = [c for c in cols if c in tradeable.columns]
        ranked = tradeable.sort_values(
            by=["decision", "setup_quality"], ascending=[True, False]
        )
        print(ranked[cols].to_string(index=False))

    watchlist = combined[combined["watchlist_candidate"] == True]  # noqa: E712
    if not watchlist.empty:
        print(f"\n{len(watchlist)} watchlist candidate(s) (trend fine, timing not yet right):")
        cols = [c for c in ["market", "symbol", "sector", "wait_for"] if c in watchlist.columns]
        print(watchlist[cols].to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run both markets' pipelines for a morning review")
    parser.add_argument(
        "--markets", default="us,india", help="comma-separated subset of: " + ",".join(MARKETS.keys())
    )
    parser.add_argument(
        "--refresh-stale-days", type=float, default=7,
        help="auto-refresh a market's universe list if older than this many days "
        "(default 7; use a negative number to disable auto-refresh entirely)",
    )
    args = parser.parse_args()
    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    for m in markets:
        if m not in MARKETS:
            parser.error(f"unknown market '{m}', choose from {list(MARKETS.keys())}")

    sys.exit(run_daily(markets, args.refresh_stale_days))


if __name__ == "__main__":
    main()
