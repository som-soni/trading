"""Failed-breakout short -- sell a breakout that closes back inside its base within a few sessions.

THE SETUP. A common swing rule ("from failed moves come fast moves"): a stock closes above the top of a
base, then within a few sessions closes back under it. The buyers of the breakout are now trapped above
the market, and their stops sit just below; the short sells into that. It is the short-side mirror of
Turtle Soup (`strategies/turtle_soup.py`), and the catalogue (research/strategy-catalog-swing.md §3.12)
grades it D, credibility 1: practitioner rule, no published test.

On daily bars:

  * the base is the BASE_BARS sessions before the breakout; its top (the pivot) is their highest high, and
    it is no more than BASE_MAX_DEPTH_PCT% above their lowest low (a base, not a crash);
  * the breakout: a close above the pivot on one of the FAIL_WINDOW sessions before today;
  * the failure, today: the first close back under the pivot since the breakout, on a red candle (close
    under the open);
  * short at today's close; the stop is the highest high since the breakout; the target TARGET_R x the
    risk below the entry; covered at the close of session TIME_STOP if neither is hit.

WHY ITS OWN RUNNER. The per-symbol engine is long-only; this runs on the generic short book
(`short_book.simulate`), which the next short setup can reuse. US only: Indian cash shares cannot be held
short overnight, and a stock-futures version is a different instrument (see the caveats).
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, corporate_actions, universe
from ..strategies.base import PortfolioStrategy
from ..strategies.swing_base import PASS_RULE
from . import metrics
from .short_book import ShortRules, index_at_exposure, simulate, stats

logger = logging.getLogger("backtest")

MARKET = "us"          # the markets this runner backtests (docs.baseline_doc reads it)
MIN_BARS = 120
LIQ_BARS = 20

# ---- the setup
BASE_BARS = 20             # the base: this many sessions before the breakout
BASE_MAX_DEPTH_PCT = 25.0  # the pivot at most this % above the base's lowest low
FAIL_WINDOW = 3            # the breakout close came on one of this many sessions before today
MIN_STOP_PCT = 1.0         # skip when the failed high is less than this % above the close
MAX_STOP_PCT = 12.0        # or more than this %

# ---- the exits
TARGET_R = 2.0             # cover at entry - this x (stop - entry)
TIME_STOP = 10             # sessions; covered at that close

# ---- size and costs (a liquid, easy-to-borrow US stock)
RISK_PCT = 0.5
MAX_POSITION_PCT = 20.0
MAX_OPEN_RISK_PCT = 3.0
MAX_POSITIONS = 10
COST_BPS = 10.0
BORROW_PCT = 1.0           # a year: general-collateral borrow for a liquid stock
DIVIDEND_PCT = 1.5         # a year, paid while short

# ---- the pass criterion, fixed before any result (see `status`)


def symbol_frame(df: pd.DataFrame, cr: pd.DataFrame | None = None) -> pd.DataFrame:
    """Per bar, causal: the signal and its stop. The most recent qualifying breakout (smallest k) wins."""
    d = df[["open", "high", "low", "close", "volume"]].astype(float)
    out = d.copy()
    out["liq"] = corporate_actions.traded_value(d["close"], d["volume"], cr, LIQ_BARS)
    pivot = d["high"].shift(1).rolling(BASE_BARS, min_periods=BASE_BARS).max()
    base_low = d["low"].shift(1).rolling(BASE_BARS, min_periods=BASE_BARS).min()
    depth_ok = (pivot / base_low - 1) * 100 <= BASE_MAX_DEPTH_PCT
    red = d["close"] < d["open"]
    sig = pd.Series(False, index=d.index)
    piv_used = pd.Series(float("nan"), index=d.index)
    stop = pd.Series(float("nan"), index=d.index)
    age = pd.Series(float("nan"), index=d.index)
    for k in range(FAIL_WINDOW, 0, -1):          # k = 1 last, so the most recent breakout overwrites
        pk = pivot.shift(k)
        brk = (d["close"].shift(k) > pk) & depth_ok.shift(k, fill_value=False)
        # every close since the breakout held above the pivot; today's is the first back under it
        held = pd.Series(True, index=d.index)
        for j in range(1, k):
            held &= d["close"].shift(j) >= pk
        hit = brk & held & (d["close"] < pk) & red
        sig = sig | hit
        piv_used = piv_used.where(~hit, pk)
        stop = stop.where(~hit, d["high"].rolling(k + 1).max())
        age = age.where(~hit, float(k))
    out["sig"] = sig.fillna(False)
    out["pivot"], out["stop"], out["bars_since_breakout"] = piv_used, stop, age
    return out


def prepare(market: str) -> dict:
    if market != MARKET:
        raise SystemExit(f"{market}: failed_breakout_short runs on the US only (no overnight cash shorts in India)")
    cfg = MARKETS[market]
    braw = cache.load_cached(market, cfg.benchmark_ticker)
    if braw is None:
        raise SystemExit(f"{market}: no stored benchmark {cfg.benchmark_ticker}")
    skip = universe.non_stock_symbols(market)
    tickers = [t for t in universe.load_universe(market) if t not in skip and t != cfg.benchmark_ticker]
    frames = {}
    for i in range(0, len(tickers), 400):
        for sym, d in cache.load_many_cached(market, tickers[i:i + 400]).items():
            if d is None or len(d) < MIN_BARS:
                continue
            try:
                f = symbol_frame(d, corporate_actions.credits_for(market, sym, d))
            except Exception as e:   # noqa: BLE001 -- one malformed history must not end the run
                logger.warning("%s: skipped (%s)", sym, e)
                continue
            if f["sig"].any():
                frames[sym] = f
        logger.info("%s: %d/%d symbols read, %d with a failed breakout", market, min(i + 400, len(tickers)),
                    len(tickers), len(frames))
    return {"market": market, "bench": braw["close"].astype(float), "frames": frames, "n_universe": len(tickers),
            "credits": corporate_actions.Credits.for_market(market, list(frames))}


FILTERS = ("liquidity", "stop_narrow", "stop_wide")


def candidates(prep: dict, start: pd.Timestamp) -> tuple[dict, dict]:
    """{signal date: [candidate, ...]} and the count each filter refused. Rank: how far the close fell back
    under the pivot, %, deepest first."""
    floor = MARKETS[prep["market"]].screener.min_dollar_volume or 0
    out: dict = {}
    dropped = {k: 0 for k in FILTERS}
    for sym, f in prep["frames"].items():
        for d in f.index[f["sig"].values & (f.index >= start)]:
            r = f.loc[d]
            if not (r["liq"] >= floor):
                dropped["liquidity"] += 1
                continue
            close, stop = float(r["close"]), float(r["stop"])
            pct = (stop / close - 1) * 100
            if pct < MIN_STOP_PCT:
                dropped["stop_narrow"] += 1
                continue
            if pct > MAX_STOP_PCT:
                dropped["stop_wide"] += 1
                continue
            back = (float(r["pivot"]) / close - 1) * 100
            out.setdefault(d, []).append({
                "symbol": sym, "stop": stop, "target": close - TARGET_R * (stop - close), "setup": "FAILED_BO",
                "rank": back, "pivot": round(float(r["pivot"]), 4), "back_under_pct": round(back, 2),
                "bars_since_breakout": int(r["bars_since_breakout"])})
    return out, dropped


def rules(borrow_pct: float = BORROW_PCT) -> ShortRules:
    return ShortRules(risk_pct=RISK_PCT, max_position_pct=MAX_POSITION_PCT, max_open_risk_pct=MAX_OPEN_RISK_PCT,
                      max_positions=MAX_POSITIONS, cost_bps=COST_BPS, borrow_pct=borrow_pct,
                      dividend_pct=DIVIDEND_PCT, time_stop=TIME_STOP)


DOC = {
    "key": "failed_breakout_short",
    "name": "Failed-breakout short",
    "description": "Short a stock whose breakout above a {BASE_BARS}-session base closes back inside it within "
                   "{FAIL_WINDOW} sessions; stop at the failed high, cover at {TARGET_R}R or after {TIME_STOP} "
                   "sessions. US only.",
    "status": ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (short-side group, grade D, "
               "credibility 1), on the new generic short book (backtesting/short_book.py); optimise-stage run "
               "queued for the US. " + PASS_RULE),
    "thesis": (
        "A breakout that closes back inside its base within days has failed: the buyers who paid up are trapped "
        "above the price, their stops sit just under the base's top, and the absence of follow-through says "
        "supply was waiting there. Practitioners short that failure ('from failed moves come fast moves'); it "
        "is the short-side mirror of Raschke & Connors's Turtle Soup. The catalogue grades it D, credibility 1: "
        "a common rule with no published test. It is here as the short-side counterpart to the breakout family "
        "-- it should pay exactly when breakouts fail."
    ),
    "how_it_works": (
        "**Universe.** Every US stock above the market's liquidity floor (the 20-day average of close × volume), "
        "ETFs and funds out. No trend or market filter.",
        "**The base.** The {BASE_BARS} sessions before the breakout. Its top, the pivot, is their highest high, "
        "and it is at most {BASE_MAX_DEPTH_PCT}% above their lowest low.",
        "**The breakout.** A close above the pivot on one of the {FAIL_WINDOW} sessions before today, and every "
        "close since then still at or above it.",
        "**The failure (the signal).** Today closes back under the pivot, on a red candle (close under the open). "
        "The most recent breakout counts when several qualify.",
        "**The trade.** Short at today's close, {COST_BPS} basis points a side. The stop is the highest high "
        "since the breakout; a stop less than {MIN_STOP_PCT}% or more than {MAX_STOP_PCT}% above the close is "
        "not traded. Same-day signals are taken deepest-back-under-the-pivot first.",
        "**Covers.** Each later session: the stop (at the stop, or the open if the stock gaps above it), then "
        "the target, the entry minus {TARGET_R} × the risk (at the target, or the open on a gap below), then "
        "the close of session {TIME_STOP}.",
        "**Size.** {RISK_PCT}% of equity at risk to the stop, at most {MAX_POSITION_PCT}% of equity in one "
        "short, {MAX_OPEN_RISK_PCT}% open risk across the book, {MAX_POSITIONS} shorts and no leverage.",
    ),
    "entry_rules": (
        "Short at the close of the first session back under the pivot (a red candle), within {FAIL_WINDOW} "
        "sessions of a close above a {BASE_BARS}-session base's top.",
    ),
    "exit_rules": (
        "Covered at the stop (the highest high since the breakout), at the open if it gaps above.",
        "Covered at the target, entry − {TARGET_R} × (stop − entry), at the open if it gaps below.",
        "Otherwise covered at the close of session {TIME_STOP} after the entry.",
    ),
    "caveats": (
        "**US only.** Indian cash shares cannot be held short overnight; a short there needs a stock future, "
        "which only the larger names have.",
        "**Borrow is an assumption.** {BORROW_PCT}% a year is general-collateral borrow for a liquid stock. "
        "Hard-to-borrow names cost far more, and a locate can be unavailable; neither is modelled. Rerun with "
        "`--borrow-pct` to see the sensitivity.",
        "**Dividends** are charged at a flat {DIVIDEND_PCT}% a year while short; a special dividend or demerger "
        "is paid in full on its ex-date.",
        "**No interest on short proceeds**, which a real account earns on part of them.",
        "**The close is both signal and fill.** The failure is only certain at the close, and the short sells "
        "that close; in practice that is a market-on-close order on an estimate.",
        "**Survivorship.** Today's stock lists: the stocks that failed and went on to delist are missing, which "
        "flatters a long book and hurts a short book.",
    ),
}


class FailedBreakoutShortStrategy(PortfolioStrategy):
    """Short a breakout that closes back inside its base (US)."""

    key = DOC["key"]
    doc = DOC
    family = "failed_breakout_short"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "First version, on the new generic short book: a close back under a {BASE_BARS}-session base's top within "
         "{FAIL_WINDOW} sessions of breaking out, on a red candle; short the close, stop at the failed high, "
         "cover at {TARGET_R}R or session {TIME_STOP}. US only."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "mean_reversion"
    selection = "time_series"
    style = "short"
    horizon = "swing"
    runner = "failed_breakout_short"

    param_docs = (
        ("Base length", "BASE_BARS", "Sessions before the breakout whose highest high is the pivot."),
        ("Base depth", "BASE_MAX_DEPTH_PCT", "The pivot at most this % above the base's lowest low."),
        ("Failure window", "FAIL_WINDOW", "Sessions after the breakout close in which the failure must come."),
        ("Minimum stop", "MIN_STOP_PCT", "Skip when the failed high is under this % above the close."),
        ("Maximum stop", "MAX_STOP_PCT", "Skip when it is over this %."),
        ("Target", "TARGET_R", "Cover at entry minus this × the risk."),
        ("Time stop", "TIME_STOP", "Sessions before the short is covered at the close."),
        ("Risk per short", "RISK_PCT", "Percent of equity between the entry and the stop."),
        ("Max position", "MAX_POSITION_PCT", "One short's notional, % of equity."),
        ("Max open risk", "MAX_OPEN_RISK_PCT", "All shorts' open risk together, % of equity."),
        ("Max shorts", "MAX_POSITIONS", "Shorts open at once."),
        ("Cost per side", "COST_BPS", "Basis points on each sale and cover."),
        ("Borrow", "BORROW_PCT", "Percent a year of the short's value (`--borrow-pct`)."),
        ("Dividends", "DIVIDEND_PCT", "Percent a year of the short's value, paid while short."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Failed-breakout short")
    ap.add_argument("--strategy", default="failed_breakout_short")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--borrow-pct", type=float, default=BORROW_PCT, help="borrow fee, %% a year")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    cfg = MARKETS[a.market]

    prep = prepare(a.market)
    sig, dropped = candidates(prep, pd.Timestamp(a.start))
    tdf, eq, held, gross, costs, skipped = simulate(a.market, a.start, sig, prep["frames"], prep["bench"].index,
                                                    rules(a.borrow_pct), prep["credits"])
    bc = prep["bench"].reindex(eq.index).ffill()
    st, st_idx = stats(eq), stats(index_at_exposure(prep["bench"], gross))
    closed = tdf[tdf["exit_reason"] != "OPEN"] if len(tdf) else tdf
    reasons = closed["exit_reason"].value_counts().to_dict() if len(closed) else {}
    notes = [
        f"SHORT BOOK, borrow {a.borrow_pct:g}% a year. {len(prep['frames']):,} of {prep['n_universe']:,} stocks "
        f"ever signalled; {sum(len(v) for v in sig.values()):,} candidates on {len(sig):,} sessions. Refused by a "
        f"filter: {dropped}; not taken: {skipped}.",
        f"Average short exposure {gross.mean():.1f}% of equity (max {gross.max():.1f}%); "
        f"{(held > 0).mean() * 100:.0f}% of sessions hold any short.",
        f"Index held long at the same exposure: CAGR {st_idx['cagr']:+.2f}%, max DD {st_idx['max_dd']:.1f}% "
        f"(book: CAGR {st['cagr']:+.2f}%, max DD {st['max_dd']:.1f}%, Sharpe {st['sharpe']:.2f}).",
        f"Exit reasons: {reasons}. Average R {closed['r_multiple'].mean():+.3f} over {len(closed)} closed shorts."
        if len(closed) else "No closed shorts.",
        "No interest is credited on short proceeds; locates are assumed available.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=MAX_POSITIONS,
                           costs_paid=costs, bench_close=bc, cash=None, notes=notes)
    for k, v in metrics.benchmark_stats(bc).items():
        setattr(perf, k, v)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"
    name = f"{a.start}_borrow{a.borrow_pct:g}_risk{RISK_PCT:g}_{FailedBreakoutShortStrategy.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held, "gross_short_pct": gross,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, MAX_POSITIONS))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — Failed-breakout short, {a.start} onward, borrow {a.borrow_pct:g}%", perf, eq, held,
            tdf, cfg.currency_symbol, MAX_POSITIONS, bc,
            f"python3 -m swing_screener.backtesting.failed_breakout_short --market {a.market} --start {a.start}"
            + (f" --borrow-pct {a.borrow_pct:g}" if a.borrow_pct != BORROW_PCT else ""))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
