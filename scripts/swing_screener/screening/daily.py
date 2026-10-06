"""Daily run — now the `daily` pipeline of the jobs layer (scripts/jobs/).

Kept so existing commands and cron entries keep working; it runs

    python -m jobs run daily [--market ...] [--strategies ...]

per market: universe list (when stale) -> prices -> index & VIX series ->
market breadth -> sector ranking -> one screening step per strategy (stored
prices only); then the consolidated report and loading reports into the web
viewer. Every step is recorded in the run log and shown on the web app's Data
status page. Pull data alone with `python -m jobs run prices`; see
`python -m jobs list` for every job.

Usage:
    python3 -m swing_screener.screening.daily
    python3 -m swing_screener.screening.daily --markets us --strategies all
"""

import argparse
import logging
import sys

import pandas as pd

from ..config import MARKETS
from ..strategies import DEFAULT_STRATEGY, list_strategies

logger = logging.getLogger("daily")


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
    parser = argparse.ArgumentParser(description="The daily pipeline (python -m jobs run daily)")
    parser.add_argument(
        "--markets", default="us,india", help="comma-separated subset of: " + ",".join(MARKETS.keys())
    )
    parser.add_argument(
        "--strategies", default=DEFAULT_STRATEGY,
        help="comma-separated strategies to screen, or 'all'. Available: " + ",".join(list_strategies()),
    )
    parser.add_argument(
        "--refresh-stale-days", type=float, default=7,
        help="re-fetch a market's universe list when older than this many days (negative: never)",
    )
    parser.add_argument("--no-ingest", action="store_true", help="skip loading reports into the web viewer")
    args = parser.parse_args()
    markets = [m.strip() for m in args.markets.split(",") if m.strip()]
    for m in markets:
        if m not in MARKETS:
            parser.error(f"unknown market '{m}', choose from {list(MARKETS.keys())}")
    keys = ["all"] if args.strategies.strip() == "all" else [k.strip() for k in args.strategies.split(",") if k.strip()]
    for k in keys:
        if k != "all" and k not in list_strategies():
            parser.error(f"unknown strategy '{k}', choose from {list_strategies()}")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from jobs import registry
    from jobs.runner import run
    if args.no_ingest:
        registry.PIPELINES["daily"]["jobs"] = [j for j in registry.PIPELINES["daily"]["jobs"] if j != "ingest"]
    sys.exit(run(["daily"], markets, {"strategies": keys, "universe_days": args.refresh_stale_days}))


if __name__ == "__main__":
    main()
