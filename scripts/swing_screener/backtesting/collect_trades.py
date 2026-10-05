"""Consolidate every backtest's trades into one reviewable CSV.

Each run writes its own `reports/<market>/<strategy>/<run>/trades.csv`, which is
right for depth and useless for "show me every trade this repo has produced, so
I can sort and filter it in one place". This assembles that file.

Why it carries a `run` column
-----------------------------
The previous consolidated file was built by hand and recorded only
market/strategy. It silently went stale: it held the 500-symbol SAMPLE donchian
runs (313 India / 328 US trades) long after full-universe runs had superseded
them, and nothing in the file said so. Sample runs are upward-biased whenever
the position cap binds, so mixing them with full-universe runs in one table
quietly compares incomparable things.

Every row now names the run it came from, and by default only ONE run per
(market, strategy) is included -- the preferred one, chosen by the rules in
`_rank_run`. `--all-runs` includes every run instead, for comparing variants.

    python3 -m swing_screener.backtesting.collect_trades
    python3 -m swing_screener.backtesting.collect_trades --all-runs
    python3 -m swing_screener.backtesting.collect_trades --strategy minervini
"""

import argparse
import logging
import re

import pandas as pd

from ..config import MARKETS
from ..paths import REPORTS_DIR

logger = logging.getLogger("collect_trades")

OUT_NAME = "all_trades.csv"
LEAD = ["market", "strategy", "run"]


def _rank_run(run: str) -> tuple:
    """Sort key picking the most authoritative run for a strategy.

    Lower is better. The order encodes what makes a run trustworthy:
      1. the LONGEST window wins first. A short window is the more severe
         defect: the methodology here holds that nothing is trustworthy on
         ~2 years of data, so a 1.75-year full-universe run tells you less
         than a 13.75-year sampled one. Ranking full-universe above window
         length picked US trend_pullback's 29-trade 2025 run over its
         301-trade 2013 run.
      2. then full universe over any `_sampleN` run (sampling thins slot
         competition and flatters the result -- measured: India donchian
         14.97% on 500 symbols vs 7.34% on the full 1,064)
      3. then a baseline over a parameter variant (`_rank*`, `_risk*`,
         `_cap*`), because the variant is an experiment, not the headline
      4. then alphabetical, for determinism
    """
    # an earlier start date means a longer window, so sort ascending on it
    m = re.match(r"(\d{4}-\d{2}-\d{2})", run)
    start = m.group(1) if m else "9999-99-99"
    sampled = 1 if re.search(r"_sample\d+", run) else 0
    variant = 1 if re.search(r"_(rank|risk|cap)[A-Za-z0-9.]+", run) else 0
    return (start, sampled, variant, run)


def discover(market: str | None = None, strategy: str | None = None) -> list[dict]:
    """Every run directory that holds a trades.csv."""
    found: list[dict] = []
    for path in sorted(REPORTS_DIR.glob("*/*/**/trades.csv")):
        rel = path.relative_to(REPORTS_DIR).parts
        if len(rel) < 3:
            continue
        mkt, strat, run = rel[0], rel[1], "/".join(rel[2:-1])
        if mkt not in MARKETS:
            continue  # e.g. reports/comparisons/, reports/_history/
        if market and mkt != market:
            continue
        if strategy and strat != strategy:
            continue
        found.append({"market": mkt, "strategy": strat, "run": run, "path": path})
    return found


def build(
    market: str | None = None, strategy: str | None = None, all_runs: bool = False
) -> pd.DataFrame:
    runs = discover(market, strategy)
    if not runs:
        return pd.DataFrame()

    if not all_runs:
        best: dict[tuple[str, str], dict] = {}
        for r in runs:
            key = (r["market"], r["strategy"])
            if key not in best or _rank_run(r["run"]) < _rank_run(best[key]["run"]):
                best[key] = r
        chosen = list(best.values())
        for r in runs:
            if r not in chosen:
                logger.info("skipping superseded run: %s/%s/%s",
                            r["market"], r["strategy"], r["run"])
        runs = chosen

    frames = []
    for r in runs:
        try:
            df = pd.read_csv(r["path"])
        except Exception as e:  # noqa: BLE001
            logger.warning("could not read %s: %s", r["path"], e)
            continue
        if df.empty:
            logger.info("no trades in %s/%s/%s", r["market"], r["strategy"], r["run"])
            continue
        df.insert(0, "run", r["run"])
        df.insert(0, "strategy", r["strategy"])
        df.insert(0, "market", r["market"])
        df["ccy"] = MARKETS[r["market"]].currency_symbol
        frames.append(df)
        logger.info("%-6s %-18s %-44s %5d trades",
                    r["market"], r["strategy"], r["run"], len(df))

    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    # stable, readable ordering: newest entries last within a strategy
    sort_cols = [c for c in ("market", "strategy", "entry_date") if c in out.columns]
    if sort_cols:
        out = out.sort_values(sort_cols).reset_index(drop=True)
    cols = LEAD + [c for c in out.columns if c not in LEAD]
    return out[cols]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", choices=list(MARKETS.keys()), default=None)
    ap.add_argument("--strategy", default=None)
    ap.add_argument("--all-runs", action="store_true",
                    help="include every run, not just the preferred one per strategy")
    ap.add_argument("--out", default=None, help=f"output path (default: reports/{OUT_NAME})")
    args = ap.parse_args()

    df = build(args.market, args.strategy, args.all_runs)
    if df.empty:
        print("No trades found.")
        return

    out = args.out or (REPORTS_DIR / OUT_NAME)
    df.to_csv(out, index=False)

    print()
    summary = (df.groupby(["market", "strategy", "run"])
                 .agg(trades=("symbol", "size"),
                      win_rate=("pnl", lambda s: round((s > 0).mean() * 100, 1)),
                      total_pnl=("pnl", lambda s: round(s.sum())),
                      avg_R=("r_multiple", lambda s: round(s.mean(), 3)))
                 .reset_index())
    print(summary.to_string(index=False))
    print(f"\n{len(df)} trades -> {out}")
    if not args.all_runs:
        print("Preferred run per strategy only (full universe over samples, "
              "baseline over variants). Use --all-runs to include every run.")


if __name__ == "__main__":
    main()
