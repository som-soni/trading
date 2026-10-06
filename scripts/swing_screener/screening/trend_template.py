"""Minervini's Trend Template — the Stage 2 qualifier, run over a whole market.

This is the eight-criteria filter from *Trade Like a Stock Market Wizard*
(ch. 5), applied to every symbol in a market. It is deliberately NOT a trading
strategy: there is no entry, no stop and no target. It answers one question —
*which stocks are in a confirmed Stage 2 uptrend right now?* — which is the
qualifier Minervini applies before he will look at a stock at all.

The eight criteria, verbatim in effect:

    1. price above both the 150-day and 200-day moving averages
    2. the 150-day is above the 200-day
    3. the 200-day is trending up for at least 1 month (4-5 preferred)
    4. the 50-day is above both the 150-day and the 200-day
    5. price is above the 50-day
    6. price is at least 30% above the 52-week low
    7. price is within 25% of the 52-week high
    8. relative strength ranking of at least 70 (80s-90s preferred)

Why this exists separately from `strategies/minervini.py`
--------------------------------------------------------
The strategy applies the same eight gates per symbol and then waits for a
volatility-contraction entry. But criterion 8 is a RANKING — "stronger than
70% of all stocks" — and a strategy evaluates one symbol at a time with no
view of the cross-section, so there it had to be approximated by an absolute
momentum floor. A screener sees the entire universe in one pass, so here
criterion 8 is computed properly, as a 1-99 percentile over everything that
had enough history.

On the RS rating
----------------
IBD's exact formula is proprietary. The widely-used approximation, and the one
here, weights recent performance double:

    raw = 2*(3-month return) + (6-month) + (9-month) + (12-month)

then percentile-ranks `raw` across the market into 1-99. Treat the number as
"this stock's strength relative to this universe", not as a reproduction of
IBD's published figure -- a different universe gives a different rank for the
same stock.

    python3 -m swing_screener.screening.trend_template --market us
    python3 -m swing_screener.screening.trend_template --market india --min-rs 80
    python3 -m swing_screener.screening.trend_template --market us --all   # keep failures too
"""

import argparse
import datetime as _dt
import logging

import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, universe
from ..paths import REPORTS_DIR, run_dir
from ..providers import YFinanceProvider

logger = logging.getLogger("trend_template")

LOOKBACK_DAYS = 420
MIN_BARS = 252                  # a 52-week high/low needs a 52-week window
SMA200_RISING_BARS = 21         # criterion 3, the 1-month minimum
SMA200_RISING_PREFERRED = 105   # "4-5 months", flagged but not required
MIN_PCT_ABOVE_52W_LOW = 30.0    # criterion 6
MAX_PCT_BELOW_52W_HIGH = 25.0   # criterion 7
DEFAULT_MIN_RS = 70             # criterion 8

CRITERIA = {
    "C1": "price above both the 150-day and 200-day moving averages",
    "C2": "150-day moving average above the 200-day",
    "C3": f"200-day trending up for at least {SMA200_RISING_BARS} sessions",
    "C4": "50-day above both the 150-day and the 200-day",
    "C5": "price above the 50-day moving average",
    "C6": f"price at least {MIN_PCT_ABOVE_52W_LOW:g}% above the 52-week low",
    "C7": f"price within {MAX_PCT_BELOW_52W_HIGH:g}% of the 52-week high",
    "C8": f"relative strength rank of at least {DEFAULT_MIN_RS}",
}


def rs_raw(close: pd.Series) -> float | None:
    """IBD-style weighted performance, recent quarter double-weighted."""
    if len(close) < MIN_BARS:
        return None
    c = close.astype(float)

    def ret(n: int) -> float | None:
        if len(c) <= n:
            return None
        past = float(c.iloc[-n - 1])
        return None if past <= 0 else float(c.iloc[-1]) / past - 1.0

    q1, q2, q3, q4 = ret(63), ret(126), ret(189), ret(252)
    if q1 is None or q4 is None:
        return None
    # missing middle quarters fall back to the annual figure rather than being
    # dropped, so a stock is not advantaged by having less history
    q2 = q4 if q2 is None else q2
    q3 = q4 if q3 is None else q3
    return 2.0 * q1 + q2 + q3 + q4


def evaluate(enriched: pd.DataFrame) -> dict | None:
    """Criteria 1-7 for one symbol. C8 needs the cross-section, so it is added
    later by `screen()` once every symbol's raw RS is known."""
    if enriched is None or len(enriched) < MIN_BARS:
        return None
    last = enriched.iloc[-1]
    close = float(last["close"])
    s50, s150, s200 = last.get("sma50"), last.get("sma150"), last.get("sma200")
    s200_prev, lo52, hi52 = last.get("sma200_21d_ago"), last.get("low_252"), last.get("high_252")
    if any(pd.isna(v) for v in (s50, s150, s200, s200_prev, lo52, hi52)):
        return None
    s50, s150, s200 = float(s50), float(s150), float(s200)
    s200_prev, lo52, hi52 = float(s200_prev), float(lo52), float(hi52)

    sma200_series = enriched["sma200"].dropna()
    rising_preferred = (
        len(sma200_series) > SMA200_RISING_PREFERRED
        and s200 > float(sma200_series.iloc[-SMA200_RISING_PREFERRED - 1])
    )
    pct_above_low = (close / lo52 - 1) * 100 if lo52 > 0 else float("nan")
    pct_below_high = (1 - close / hi52) * 100 if hi52 > 0 else float("nan")

    return {
        "close": round(close, 2),
        "C1": bool(close > s150 and close > s200),
        "C2": bool(s150 > s200),
        "C3": bool(s200 > s200_prev),
        "C4": bool(s50 > s150 and s50 > s200),
        "C5": bool(close > s50),
        "C6": bool(pct_above_low >= MIN_PCT_ABOVE_52W_LOW),
        "C7": bool(pct_below_high <= MAX_PCT_BELOW_52W_HIGH),
        "sma50": round(s50, 2), "sma150": round(s150, 2), "sma200": round(s200, 2),
        "pct_above_52w_low": round(pct_above_low, 1),
        "pct_below_52w_high": round(pct_below_high, 1),
        "sma200_rising_4_5mo": bool(rising_preferred),
        "_rs_raw": rs_raw(enriched["close"]),
    }


def screen(market: str, min_rs: int = DEFAULT_MIN_RS, limit: int | None = None,
           refresh: bool = True) -> pd.DataFrame:
    cfg = MARKETS[market]
    sectors = universe.load_sector_cache(market)
    tickers = sorted(universe.load_universe(market))
    if limit:
        tickers = tickers[:limit]

    if refresh:
        logger.info("Pulling price data for %d symbols...", len(tickers))
        bars, failed = cache.get_many_bars(YFinanceProvider(), market, tickers, LOOKBACK_DAYS)
        logger.info("Pulled %d symbols (%d failed)", len(bars), len(failed))
    else:
        bars = {}
        for t in tickers:
            df = cache.load_cached(market, t)
            if df is not None and not df.empty:
                bars[t] = df
        logger.info("Loaded %d symbols from cache (no refresh)", len(bars))

    rows = []
    for i, (sym, raw) in enumerate(bars.items(), 1):
        rec = evaluate(ind.enrich_daily(raw))
        if rec is None:
            continue
        rec["symbol"] = sym
        rec["sector"] = sectors.get(sym, "Unknown")
        rows.append(rec)
        if i % 1000 == 0:
            logger.info("  evaluated %d/%d", i, len(bars))
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    # --- criterion 8: the cross-sectional part, which is the point of a screener
    ranked = df["_rs_raw"].rank(pct=True) * 99
    df["rs_rank"] = ranked.round().clip(lower=1, upper=99).astype("Int64")
    df["C8"] = df["rs_rank"].ge(min_rs).fillna(False)
    df["criteria_passed"] = df[[f"C{i}" for i in range(1, 9)]].sum(axis=1)
    df["stage2"] = df["criteria_passed"].eq(8)

    cols = (["symbol", "sector", "close", "stage2", "criteria_passed", "rs_rank"]
            + [f"C{i}" for i in range(1, 9)]
            + ["pct_above_52w_low", "pct_below_52w_high", "sma200_rising_4_5mo",
               "sma50", "sma150", "sma200"])
    return (df[cols]
            .sort_values(["stage2", "rs_rank"], ascending=False)
            .reset_index(drop=True))


def _report(df: pd.DataFrame, market: str, min_rs: int) -> str:
    cfg = MARKETS[market]
    passed = df[df.stage2]
    L = [f"# {cfg.name} — Minervini Trend Template", "",
         f"*{_dt.date.today()} · {len(df):,} symbols evaluated*", "",
         f"**{len(passed):,} stocks ({len(passed)/max(len(df),1)*100:.1f}%) meet all "
         f"eight criteria** and are in a confirmed Stage 2 uptrend.", "",
         "A stock must meet all eight to qualify — Minervini treats the template "
         "as a gate, not a score, and will not consider a stock that fails it "
         "however compelling the fundamentals.", ""]

    L.append("## Where the universe falls out")
    L.append("")
    L.append("| criterion | requirement | passing |")
    L.append("|---|---|---|")
    for code, text in CRITERIA.items():
        n = int(df[code].sum())
        L.append(f"| {code} | {text} | {n:,} ({n/max(len(df),1)*100:.0f}%) |")
    L.append("")

    if not passed.empty:
        L.append(f"## Qualifying stocks (RS rank ≥ {min_rs}), strongest first")
        L.append("")
        L.append("| symbol | sector | close | RS | % above 52w low | % below 52w high | 200d rising 4-5mo |")
        L.append("|---|---|---|---|---|---|---|")
        for _, r in passed.head(60).iterrows():
            L.append(f"| **{r['symbol']}** | {r['sector']} | {r['close']:,.2f} "
                     f"| {r['rs_rank']} | {r['pct_above_52w_low']:.0f}% "
                     f"| {r['pct_below_52w_high']:.0f}% "
                     f"| {'yes' if r['sma200_rising_4_5mo'] else 'no'} |")
        if len(passed) > 60:
            L.append("")
            L.append(f"*{len(passed) - 60:,} more in the CSV.*")
        L.append("")
        by_sector = passed.groupby("sector").size().sort_values(ascending=False)
        L.append("## Qualifying stocks by sector")
        L.append("")
        L.append("| sector | stocks |")
        L.append("|---|---|")
        for s, n in by_sector.items():
            L.append(f"| {s} | {n} |")
        L.append("")

    L.append("## Notes")
    L.append("")
    L.append(f"- The RS rank is a 1-99 percentile of `2x(3mo) + (6mo) + (9mo) + "
             f"(12mo)` return across these {len(df):,} symbols. IBD's exact "
             "formula is proprietary, so this is the standard approximation — "
             "and it is relative to THIS universe, not to IBD's.")
    L.append(f"- Criterion 3 requires the 200-day to have risen over "
             f"{SMA200_RISING_BARS} sessions. Minervini prefers 4-5 months; the "
             "`sma200_rising_4_5mo` column flags which stocks clear that higher bar.")
    L.append("- This is a qualifier, not a trade signal. It says a stock is in a "
             "Stage 2 uptrend, not that today is a low-risk entry.")
    return "\n".join(L)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Minervini Trend Template screener")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--min-rs", type=int, default=DEFAULT_MIN_RS,
                    help=f"minimum relative strength rank, 1-99 (default {DEFAULT_MIN_RS})")
    ap.add_argument("--all", action="store_true",
                    help="keep every symbol in the CSV, not just those passing all eight")
    ap.add_argument("--no-refresh", action="store_true",
                    help="use cached prices only, skipping the network pull")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-ingest", action="store_true",
                    help="skip updating the viewer database after the run")
    args = ap.parse_args()

    df = screen(args.market, args.min_rs, args.limit, refresh=not args.no_refresh)
    if df.empty:
        print("No symbols could be evaluated.")
        return

    out_dir = run_dir(args.market, "trend_template", f"screener/{_dt.date.today()}")
    (out_dir / "report.md").write_text(_report(df, args.market, args.min_rs))
    (df if args.all else df[df.stage2]).to_csv(out_dir / "candidates.csv", index=False)
    latest = REPORTS_DIR / f"{args.market}_trend_template.csv"
    (df if args.all else df[df.stage2]).to_csv(latest, index=False)

    passed = df[df.stage2]
    print()
    print(f"{MARKETS[args.market].name}: {len(df):,} evaluated, "
          f"{len(passed):,} pass all eight ({len(passed)/len(df)*100:.1f}%)")
    print()
    for code, text in CRITERIA.items():
        n = int(df[code].sum())
        print(f"  {code}  {n:5,} ({n/len(df)*100:5.1f}%)  {text}")
    if not passed.empty:
        print()
        show = ["symbol", "sector", "close", "rs_rank",
                "pct_above_52w_low", "pct_below_52w_high"]
        print(passed[show].head(20).to_string(index=False))
    print(f"\n-> {out_dir / 'candidates.csv'}")
    print(f"-> {out_dir / 'report.md'}")

    if not args.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()


if __name__ == "__main__":
    main()
