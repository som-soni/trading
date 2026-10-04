"""Daily wrapper: runs both markets, auto-refreshes a stale universe list,
isolates failures (one market crashing doesn't block the other), logs to
both console and a dated file, and prints one cross-market summary at the
end instead of two separate scrolls of output.

Usage:
    python3 -m swing_screener.screening.daily
    python3 -m swing_screener.screening.daily --markets us
    python3 -m swing_screener.screening.daily --refresh-stale-days 3
    python3 -m swing_screener.screening.daily --refresh-stale-days -1   # never auto-refresh

Scheduling (macOS cron, run at 7am local time daily):
    0 7 * * * cd /Users/admin/Workspace/trading/scripts && .venv/bin/python3 -m swing_screener.screening.daily >> logs/cron.log 2>&1
"""

import argparse
import logging
import sys
import traceback
from pathlib import Path

import pandas as pd

from . import pipeline

from ..marketdata import universe
from ..config import MARKETS
from ..strategies import DEFAULT_STRATEGY, list_strategies

from ..paths import LOGS_DIR as LOG_DIR  # noqa: F401
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


def run_daily(
    markets: list[str], refresh_stale_days: float = 7,
    strategy_keys: list[str] | None = None,
) -> int:
    strategy_keys = strategy_keys or [DEFAULT_STRATEGY]
    log_path = _setup_logging()
    logger.info(
        "=== Daily run starting: markets=%s strategies=%s ===", markets, strategy_keys
    )

    # {strategy: {market: report_df}} — the report sections by strategy, and a
    # failure in one strategy/market pair must not stop the others
    reports: dict[str, dict[str, pd.DataFrame]] = {k: {} for k in strategy_keys}
    failures: dict[str, str] = {}

    for market in markets:
        print(f"\n{'=' * 60}\n{MARKETS[market].name.upper()}\n{'=' * 60}")
        try:
            _maybe_refresh_universe(market, refresh_stale_days)
        except Exception as e:
            logger.exception("%s universe refresh failed", market)
            failures[market] = f"universe refresh: {type(e).__name__}: {e}"
        for key in strategy_keys:
            print(f"\n--- strategy: {key} ---")
            try:
                reports[key][market] = pipeline.run(
                    market, refresh_universe=False, strategy_key=key
                )
            except Exception as e:
                logger.exception("%s/%s run failed", market, key)
                failures[f"{market}/{key}"] = f"{type(e).__name__}: {e}"
                print(f"\n*** {market.upper()}/{key} FAILED: {e} ***")
                print(traceback.format_exc())

    for key, by_market in reports.items():
        _print_cross_market_summary(by_market, failures, key)

    # one consolidated page across markets, alongside the per-market reports
    try:
        import datetime as _dt

        from ..paths import REPORTS_DIR
        from . import candidates_report

        combined_dir = REPORTS_DIR / "daily" / str(_dt.date.today())
        md = candidates_report.write_combined(
            combined_dir, reports, failures, str(_dt.date.today())
        )
        print(f"\nConsolidated report: {md}")
    except Exception as e:
        logger.warning("combined report not generated (%s: %s)", type(e).__name__, e)
    logger.info("=== Daily run finished. Log: %s ===", log_path)
    print(f"\nFull log: {log_path}")

    return 1 if failures else 0


def _print_cross_market_summary(
    reports: dict[str, pd.DataFrame], failures: dict[str, str], strategy_key: str = ""
) -> None:
    label = f"CROSS-MARKET SUMMARY — {strategy_key}" if strategy_key else "CROSS-MARKET SUMMARY"
    print(f"\n{'=' * 60}\n{label}\n{'=' * 60}")

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
        "--strategies", default=DEFAULT_STRATEGY,
        help="comma-separated strategies to run for every market, each getting its "
        "own section in the report. Use 'all' for every registered strategy. "
        "Available: " + ",".join(list_strategies()),
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

    keys = (list_strategies() if args.strategies.strip() == "all"
            else [k.strip() for k in args.strategies.split(",") if k.strip()])
    for k in keys:
        if k not in list_strategies():
            parser.error(f"unknown strategy '{k}', choose from {list_strategies()}")

    sys.exit(run_daily(markets, args.refresh_stale_days, keys))


if __name__ == "__main__":
    main()
