"""List the stocks that actually ran — one row per stock, year by year.

`uptrend_runs.py` catalogues individual MOVES. This answers the companion
question: *which names* produced them, and how often. It is reference data for
pattern-hunting, not a strategy.

Two definitions of "a 25% run in a year" are reported side by side, because
they disagree and the disagreement is informative:

- **calendar-year return** — easy to reason about and to cross-reference
  against news, but it misses a move that straddles a year boundary. A stock
  that rose 60% from July to June shows as two unremarkable years.
- **best rolling 252-day gain** — the largest advance over any one-year window
  in the period. This is the honest reading of "a 25%+ run in a year", and it
  is always at least as large as the best calendar year.

Columns are chosen so the table can be sorted or filtered directly:
`years_ge_25` for consistency, `best_252d_gain_pct` for magnitude,
`max_drawdown_pct` for what holding it demanded, and `median_dollar_volume`
for whether it was tradeable at size.

    python3 -m swing_screener.backtesting.strong_stocks --market us --years 10
    python3 -m swing_screener.backtesting.strong_stocks --market india --years 10 \\
        --min-dollar-volume 100000000
"""

import argparse
import logging

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, universe
from ..paths import REPORTS_DIR

logger = logging.getLogger("strong_stocks")

THRESHOLD_PCT = 25.0


def _year_returns(close: pd.Series) -> dict[int, float]:
    """Calendar-year % return. A partial first or last year is still reported
    -- it is a real return over a real period, just a shorter one."""
    out: dict[int, float] = {}
    for year, seg in close.groupby(close.index.year):
        if len(seg) < 2:
            continue
        out[int(year)] = (float(seg.iloc[-1]) / float(seg.iloc[0]) - 1) * 100
    return out


def _best_rolling(close: pd.Series, window: int = 252) -> tuple[float, pd.Timestamp | None]:
    """Largest gain over any `window`-bar span, and the date it ended.

    Computed as close / rolling-min-of-trailing-close, which measures the move
    from the lowest point within the window rather than from exactly N bars
    ago -- the latter understates a run that began mid-window.
    """
    if len(close) < 20:
        return (float("nan"), None)
    w = min(window, len(close))
    trailing_min = close.rolling(w, min_periods=2).min()
    gain = (close / trailing_min - 1) * 100
    if gain.isna().all():
        return (float("nan"), None)
    i = int(np.nanargmax(gain.values))
    return (float(gain.iloc[i]), gain.index[i])


def scan(
    market: str, years: int = 10, threshold: float = THRESHOLD_PCT,
    min_dollar_volume: float | None = None, limit: int | None = None,
) -> pd.DataFrame:
    cfg = MARKETS[market]
    if min_dollar_volume is None:
        min_dollar_volume = cfg.screener.min_dollar_volume
    sectors = universe.load_sector_cache(market)
    syms = sorted(universe.load_universe(market))
    if limit:
        syms = syms[:limit]
    start = pd.Timestamp.today().normalize() - pd.DateOffset(years=years)

    rows, skipped = [], {"illiquid": 0, "short": 0}
    for n, sym in enumerate(syms, 1):
        px = cache.load_cached(market, sym)
        if px is None or px.empty:
            skipped["short"] += 1
            continue
        w = px[px.index >= start]
        if len(w) < 250:
            skipped["short"] += 1
            continue
        dv = float((w["close"] * w["volume"]).median())
        if min_dollar_volume and dv < min_dollar_volume:
            skipped["illiquid"] += 1
            continue

        c = w["close"].dropna()
        yr = _year_returns(c)
        best_gain, best_end = _best_rolling(c)
        peak = c.cummax()
        max_dd = float(((c - peak) / peak * 100).min())
        total = (float(c.iloc[-1]) / float(c.iloc[0]) - 1) * 100

        rec = {
            "symbol": sym,
            "sector": sectors.get(sym, ""),
            "years_ge_25": sum(1 for v in yr.values() if v >= threshold),
            "years_measured": len(yr),
            "best_252d_gain_pct": round(best_gain, 1),
            "best_252d_ended": best_end.date() if best_end is not None else None,
            "best_calendar_year_pct": round(max(yr.values()), 1) if yr else None,
            "total_return_pct": round(total, 1),
            "max_drawdown_pct": round(max_dd, 1),
            "median_dollar_volume": round(dv),
        }
        for year, v in sorted(yr.items()):
            rec[f"y{year}"] = round(v, 1)
        rows.append(rec)
        if n % 500 == 0:
            logger.info("scanned %d/%d symbols, %d kept", n, len(syms), len(rows))

    logger.info("skipped: %d illiquid, %d too little history",
                skipped["illiquid"], skipped["short"])
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    year_cols = sorted([c for c in df.columns if c.startswith("y2")])
    lead = ["symbol", "sector", "years_ge_25", "years_measured",
            "best_252d_gain_pct", "best_252d_ended", "best_calendar_year_pct",
            "total_return_pct", "max_drawdown_pct", "median_dollar_volume"]
    return (df[lead + year_cols]
            .sort_values(["years_ge_25", "best_252d_gain_pct"], ascending=False)
            .reset_index(drop=True))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--threshold", type=float, default=THRESHOLD_PCT)
    ap.add_argument("--min-dollar-volume", type=float, default=None)
    ap.add_argument("--limit", type=int, default=None)
    args = ap.parse_args()

    df = scan(args.market, args.years, args.threshold,
              args.min_dollar_volume, args.limit)
    if df.empty:
        print("No stocks matched.")
        return

    dv = (args.min_dollar_volume if args.min_dollar_volume is not None
          else MARKETS[args.market].screener.min_dollar_volume)
    out = REPORTS_DIR / (f"strong_stocks_{args.market}_{args.years}y"
                         f"_{args.threshold:g}pct_dv{dv/1e6:g}m.csv")
    df.to_csv(out, index=False)

    hit = df[df.years_ge_25 > 0]
    print()
    print(f"{MARKETS[args.market].name}: {len(df):,} tradeable stocks with "
          f"{args.years}y of history")
    print(f"  {len(hit):,} ({len(hit)/len(df)*100:.0f}%) had at least one "
          f"calendar year of >= {args.threshold:g}%")
    print(f"  {(df.best_252d_gain_pct >= args.threshold).sum():,} had a "
          f">= {args.threshold:g}% gain over SOME 252-day window")
    print()
    print("  stocks by number of qualifying calendar years:")
    for k, v in df.years_ge_25.value_counts().sort_index(ascending=False).items():
        print(f"    {k} year(s): {v:,}")
    print()
    print("  top 15 by consistency, then size of best run:")
    show = ["symbol", "sector", "years_ge_25", "best_252d_gain_pct",
            "total_return_pct", "max_drawdown_pct"]
    print(df[show].head(15).to_string(index=False))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
