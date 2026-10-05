"""Catalogue every sustained uptrend in a market — the raw material a strategy
is trying to capture.

Every backtest in this repo answers "did my rules make money". This answers the
prior question: **what was there to catch?** It finds, for each symbol, the
discrete up-runs of at least `min_gain` percent, so you can ask how many there
were, how long they lasted, how deep the shakeouts inside them went, and what
a holding period would have to be to survive one.

That last point is why this exists. The strategies here hold for a median of
21-59 days; if the typical 25%+ run takes 200 days and gives back 12% along the
way, no amount of entry tuning will help, because the exit leaves before the
move finishes.

How a run is defined
--------------------
A zigzag on closing prices, which is the standard way to segment a series into
alternating swings without fitting anything:

- in an UP leg, the peak keeps updating; the leg ends when the close falls
  `retrace` percent below that peak
- in a DOWN leg, the trough keeps updating; the leg ends when the close rises
  `retrace` percent above that trough

An up-run is then trough -> peak, and is reported when its gain is at least
`min_gain`. `retrace` is the one real parameter: it sets how much noise a run
is allowed to contain before it counts as over. At 15% a run survives an
ordinary correction; at 5% nearly every wiggle ends one.

Closes are used rather than intraday highs/lows deliberately -- a single
spiky print should not start or end a trend.

    python3 -m swing_screener.backtesting.uptrend_runs --market us --years 10
    python3 -m swing_screener.backtesting.uptrend_runs --market india --years 10 \\
        --min-gain 25 --retrace 15
"""

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, universe
from ..paths import REPORTS_DIR

logger = logging.getLogger("uptrend_runs")


def find_runs(
    close: pd.Series, min_gain: float = 25.0, retrace: float = 15.0
) -> list[dict]:
    """Up-runs of at least `min_gain`%, as (start, end, gain, depth) records."""
    if close is None or len(close) < 30:
        return []
    c = close.dropna()
    if c.empty:
        return []

    runs: list[dict] = []
    up = True                      # assume the first leg is up; a wrong guess
    piv_i, piv_v = 0, float(c.iloc[0])   # self-corrects on the first reversal
    ext_i, ext_v = 0, float(c.iloc[0])

    for i in range(1, len(c)):
        v = float(c.iloc[i])
        if up:
            if v > ext_v:
                ext_i, ext_v = i, v
            elif ext_v > 0 and (ext_v - v) / ext_v * 100 >= retrace:
                # the up leg is over: record it if it was big enough
                gain = (ext_v - piv_v) / piv_v * 100 if piv_v > 0 else 0.0
                if gain >= min_gain:
                    runs.append(_record(c, piv_i, ext_i, piv_v, ext_v, gain))
                up = False
                piv_i, piv_v = ext_i, ext_v
                ext_i, ext_v = i, v
        else:
            if v < ext_v:
                ext_i, ext_v = i, v
            elif ext_v > 0 and (v - ext_v) / ext_v * 100 >= retrace:
                up = True
                piv_i, piv_v = ext_i, ext_v
                ext_i, ext_v = i, v

    # a run still in progress at the end of the data is real and worth seeing
    if up and piv_v > 0:
        gain = (ext_v - piv_v) / piv_v * 100
        if gain >= min_gain:
            r = _record(c, piv_i, ext_i, piv_v, ext_v, gain)
            r["ongoing"] = True
            runs.append(r)
    return runs


def _record(c: pd.Series, i0: int, i1: int, v0: float, v1: float, gain: float) -> dict:
    """One run, plus the worst pullback INSIDE it — the number that decides
    whether a stop or a trailing exit would have survived the move."""
    seg = c.iloc[i0 : i1 + 1]
    running_max = seg.cummax()
    dd = ((seg - running_max) / running_max * 100).min()
    days = int((c.index[i1] - c.index[i0]).days)
    return {
        "start": c.index[i0], "end": c.index[i1],
        "start_price": round(v0, 2), "end_price": round(v1, 2),
        "gain_pct": round(gain, 1),
        "days": days,
        "bars": int(i1 - i0),
        # pace of the advance. A +40% run over 30 days and the same gain over
        # 400 days are different opportunities, and sorting on gain alone
        # hides that. Guarded against a zero-length span.
        "gain_per_day": round(gain / max(days, 1), 3),
        "worst_pullback_pct": round(float(dd), 1),
        "ongoing": False,
    }


def scan(
    market: str, years: int = 10, min_gain: float = 25.0, retrace: float = 15.0,
    min_dollar_volume: float | None = None, limit: int | None = None,
    since: str | None = None,
) -> pd.DataFrame:
    cfg = MARKETS[market]
    if min_dollar_volume is None:
        min_dollar_volume = cfg.screener.min_dollar_volume
    sectors = universe.load_sector_cache(market)
    syms = sorted(universe.load_universe(market))
    if limit:
        syms = syms[:limit]
    start = pd.Timestamp.today().normalize() - pd.DateOffset(years=years)
    since_ts = pd.Timestamp(since) if since else None

    rows, skipped_illiquid, skipped_short = [], 0, 0
    for n, sym in enumerate(syms, 1):
        px = cache.load_cached(market, sym)
        if px is None or px.empty:
            skipped_short += 1
            continue
        w = px[px.index >= start]
        if len(w) < 250:
            skipped_short += 1
            continue
        # a 25% run in an untradeable microcap is not an opportunity
        if min_dollar_volume:
            dv = float((w["close"] * w["volume"]).median())
            if dv < min_dollar_volume:
                skipped_illiquid += 1
                continue
        for r in find_runs(w["close"], min_gain, retrace):
            # filter on when the run STARTED, not when it ended: a run that
            # began in 2018 and peaked in 2021 is a pre-2020 setup
            if since_ts is not None and r["start"] < since_ts:
                continue
            r["symbol"] = sym
            r["sector"] = sectors.get(sym, "")
            r["median_dollar_volume"] = round(float((w["close"] * w["volume"]).median()))
            rows.append(r)
        if n % 500 == 0:
            logger.info("scanned %d/%d symbols, %d runs so far", n, len(syms), len(rows))

    logger.info("skipped: %d illiquid, %d too little history", skipped_illiquid, skipped_short)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    cols = ["symbol", "sector", "start", "end", "gain_pct", "days",
            "gain_per_day", "worst_pullback_pct", "bars",
            "start_price", "end_price", "median_dollar_volume", "ongoing"]
    return df[cols].sort_values("gain_pct", ascending=False).reset_index(drop=True)


def summarise(df: pd.DataFrame, market: str) -> str:
    cfg = MARKETS[market]
    if df.empty:
        return "no runs found"
    L = [f"{cfg.name}: {len(df):,} runs across {df.symbol.nunique():,} symbols", ""]
    q = df.gain_pct.describe(percentiles=[.25, .5, .75, .9, .99])
    L.append(f"  gain%        median {q['50%']:.0f}   75th {q['75%']:.0f}   "
             f"90th {q['90%']:.0f}   99th {q['99%']:.0f}   max {q['max']:.0f}")
    d = df.days.describe(percentiles=[.25, .5, .75, .9])
    L.append(f"  duration(d)  median {d['50%']:.0f}   25th {d['25%']:.0f}   "
             f"75th {d['75%']:.0f}   90th {d['90%']:.0f}")
    p = df.worst_pullback_pct.describe(percentiles=[.25, .5, .75])
    L.append(f"  worst pullback INSIDE the run: median {p['50%']:.1f}%   "
             f"25th {p['25%']:.1f}%   75th {p['75%']:.1f}%")
    L.append("")
    L.append(f"  runs per symbol: median {df.groupby('symbol').size().median():.0f}")
    L.append(f"  still running now: {int(df.ongoing.sum()):,}")
    return "\n".join(L)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--years", type=int, default=10)
    ap.add_argument("--min-gain", type=float, default=25.0)
    ap.add_argument("--retrace", type=float, default=15.0,
                    help="percent pullback from the peak that ends a run")
    ap.add_argument("--min-dollar-volume", type=float, default=None,
                    help="default: the market's screener threshold")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--since", default=None,
                    help="only runs that STARTED on/after this date, e.g. 2020-01-01")
    args = ap.parse_args()

    df = scan(args.market, args.years, args.min_gain, args.retrace,
              args.min_dollar_volume, args.limit, args.since)
    if df.empty:
        print("No runs found.")
        return
    # the liquidity floor and retrace threshold BELONG in the filename: they
    # change which symbols and which runs appear, so leaving them out means two
    # different scans silently overwrite each other
    dv = args.min_dollar_volume if args.min_dollar_volume is not None else MARKETS[args.market].screener.min_dollar_volume
    out = REPORTS_DIR / (
        f"uptrend_runs_{args.market}_{args.min_gain:g}pct"
        f"_retrace{args.retrace:g}_dv{dv/1e6:g}m"
        + (f"_since{args.since}" if args.since else f"_{args.years}y") + ".csv"
    )
    df.to_csv(out, index=False)
    print()
    print(summarise(df, args.market))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
