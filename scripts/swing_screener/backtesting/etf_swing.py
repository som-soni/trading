"""ETF swing — the swing-trading system from "The Long & The Short" (Ep. 44), run on liquid ETFs.

The series' last idea: run the same swing system on a basket of exchange-traded funds instead of stocks --
gold, silver, index and overseas ETFs -- for less single-company risk and access to other asset classes
(research/swing-trading-video-series.md). The system is the one it builds for stocks:

  * entry: a close above the highest high of the prior ENTRY_DAYS sessions (the N-day breakout);
  * the scan: candidates ranked by their RANK_DAYS-session return, the strongest first (the series' "top
    performers over the past week");
  * the book: MAX_POSITIONS slots of ALLOC_PCT each, one in, one out -- a slot is refilled only when a
    position exits;
  * the exit: the first close below the TRAIL_EMA-day exponential average, at that close (the series'
    moving-average trail; it is also the stop);
  * only liquid ETFs: a 50-day average traded value of at least MIN_VALUE in the market's currency.

Universe: the market's tracked ETFs listed in ETF_UNIVERSE (each must also be in marketdata/instruments.py
or the sector map, so the daily refresh keeps it current). Prices are read through `cache`, so a backtest
stage's boundary applies (marketdata/asof.py).
"""
from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from ..strategies.base import PortfolioStrategy
from . import metrics

logger = logging.getLogger(__name__)

ETF_UNIVERSE = {
    "india": ("GOLDBEES.NS", "SILVERBEES.NS", "NIFTYBEES.NS", "JUNIORBEES.NS", "MID150BEES.NS", "BANKBEES.NS",
              "PSUBNKBEES.NS", "ITBEES.NS", "PHARMABEES.NS", "AUTOBEES.NS", "CPSEETF.NS", "MON100.NS",
              "MAFANG.NS", "MASPTOP50.NS", "HNGSNGBEES.NS"),
    "us": ("SPY", "QQQ", "IWM", "MDY", "EFA", "EEM", "TLT", "IEF", "GLD", "SLV", "USO", "DBC", "SMH",
           "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB"),
}
ENTRY_DAYS = 21            # the N-day breakout: a close above the prior N sessions' highest high
RANK_DAYS = 5              # candidates ranked by this many sessions' return (the series' one-week scan)
MAX_POSITIONS = 5          # slots
ALLOC_PCT = 20.0           # % of equity per slot
TRAIL_EMA = 21             # exit on the first close below this exponential average
MIN_BARS = 120             # sessions of history an ETF needs before it can signal
MIN_VALUE = {"india": 5e7, "us": 2e7}    # 50-day average traded value: ₹5 crore / $20 million a day
COST_BPS = 10.0            # per side: spread, slippage and brokerage on a liquid ETF


def load(market: str) -> dict[str, pd.DataFrame]:
    out = {}
    for sym in ETF_UNIVERSE.get(market, ()):
        d = cache.load_cached(market, sym)
        if d is None or len(d) < MIN_BARS:
            logger.info("%s: %s skipped — %d bars", market, sym, 0 if d is None else len(d))
            continue
        d = d.astype(float).copy()
        d["hh"] = d["high"].shift(1).rolling(ENTRY_DAYS).max()
        d["ema"] = d["close"].ewm(span=TRAIL_EMA, adjust=False).mean()
        d["ret_rank"] = d["close"] / d["close"].shift(RANK_DAYS) - 1
        d["value50"] = (d["close"] * d["volume"]).rolling(50, min_periods=40).mean()
        d["n"] = np.arange(1, len(d) + 1)
        out[sym] = d
    if not out:
        raise SystemExit(f"{market}: no ETF in ETF_UNIVERSE has stored prices — fetch them first "
                         f"(python -m jobs enqueue prices --market {market} --symbols ... --days 6500)")
    return out


def run(market: str, start: str, account: float):
    """Walk the calendar: exits at the close, then entries at the close into free slots."""
    frames = load(market)
    days = sorted({d for df in frames.values() for d in df.index if d >= pd.Timestamp(start)})
    cash, pos, trades, eq, held = float(account), {}, [], [], []
    fee = COST_BPS / 10_000
    floor = MIN_VALUE.get(market, 0)
    for d in days:
        # 1. exits: a close below the trailing average sells at that close
        for sym in list(pos):
            df = frames[sym]
            if d not in df.index:
                continue
            r = df.loc[d]
            if r["close"] < r["ema"]:
                p = pos.pop(sym)
                gross = p["shares"] * r["close"]
                cost = gross * fee
                cash += gross - cost
                risk = p["shares"] * max(p["entry"] - p["stop0"], 1e-9)
                pnl = gross - cost - p["cost"]
                trades.append({"symbol": sym, "entry_date": p["date"], "entry_price": round(p["entry"], 4),
                               "exit_date": d, "exit_price": round(float(r["close"]), 4), "shares": p["shares"],
                               "exit_reason": "TREND_EXIT", "pnl": round(pnl, 2), "notional": round(p["cost"], 2),
                               "costs": round(cost + p["fee"], 2), "holding_days": (d - p["date"]).days,
                               "r_multiple": round(pnl / risk, 4)})
        # 2. entries: N-day breakouts among liquid ETFs not held, the strongest RANK_DAYS return first
        free = MAX_POSITIONS - len(pos)
        if free > 0:
            cands = []
            for sym, df in frames.items():
                if sym in pos or d not in df.index:
                    continue
                r = df.loc[d]
                if (r["n"] >= MIN_BARS and pd.notna(r["hh"]) and r["close"] > r["hh"] and r["close"] > r["ema"]
                        and (r["value50"] if pd.notna(r["value50"]) else 0) >= floor):
                    cands.append((float(r["ret_rank"]) if pd.notna(r["ret_rank"]) else -9, sym, r))
            equity = cash + sum(p["shares"] * float(frames[s]["close"].asof(d)) for s, p in pos.items())
            for _rk, sym, r in sorted(cands, key=lambda x: -x[0])[:free]:
                px = float(r["close"])
                budget = min(equity * ALLOC_PCT / 100, cash / (1 + fee))
                shares = int(budget // px)
                if shares < 1:
                    continue
                c = shares * px
                cash -= c * (1 + fee)
                pos[sym] = {"date": d, "entry": px, "shares": shares, "cost": c * (1 + fee), "fee": c * fee,
                            "stop0": float(r["ema"])}
        # 3. mark to market
        eq.append(cash + sum(p["shares"] * float(frames[s]["close"].asof(d)) for s, p in pos.items()))
        held.append(len(pos))
    idx = pd.DatetimeIndex(days)
    for sym, p in pos.items():   # still open at the end: valued at the last close, no exit cost
        last = float(frames[sym]["close"].asof(idx[-1]))
        trades.append({"symbol": sym, "entry_date": p["date"], "entry_price": round(p["entry"], 4), "exit_date": idx[-1],
                       "exit_price": round(last, 4), "shares": p["shares"], "exit_reason": "OPEN",
                       "pnl": round(p["shares"] * last - p["cost"], 2), "notional": round(p["cost"], 2),
                       "costs": round(p["fee"], 2), "holding_days": (idx[-1] - p["date"]).days,
                       "r_multiple": round((p["shares"] * last - p["cost"]) / (p["shares"] * max(p["entry"] - p["stop0"], 1e-9)), 4)})
    return pd.DataFrame(trades), pd.Series(eq, index=idx), pd.Series(held, index=idx), sorted(frames)


DOC = {
    "key": "etf_swing",
    "name": "ETF swing",
    "description": "The swing system of 'The Long & The Short' (Ep. 44) on liquid ETFs: buy a close above the "
                   "{ENTRY_DAYS}-day high, the strongest {RANK_DAYS}-day performers first, {MAX_POSITIONS} slots of "
                   "{ALLOC_PCT}% each, out on a close below the {TRAIL_EMA}-day EMA.",
    "status": "Not yet backtested. Built to measure the series' ETF variant; judge it on the optimise stage first.",
    "thesis": "The series' last idea: the same swing system on a basket of ETFs instead of stocks, for less "
              "single-company risk (no gaps on one company's news) and access to gold, silver and overseas "
              "equity. If breakouts in trending assets persist, a book of the strongest breaking-out ETFs, held "
              "until the trend breaks, should beat simply holding the index, with a smoother equity curve.",
    "how_it_works": (
        "Each session, after the close: first the exits, then the entries, both at that close.",
        "Exit: a held ETF that closes below its {TRAIL_EMA}-day exponential average is sold. That trailing average "
        "is also the stop; there is no target and no time limit.",
        "Entry: an ETF not held that closes above the highest high of the prior {ENTRY_DAYS} sessions, above its "
        "{TRAIL_EMA}-day average, with at least {MIN_BARS} sessions of history and a 50-day average traded value of "
        "at least ₹5 crore (India) or $20 million (US).",
        "Slots: at most {MAX_POSITIONS} positions, each bought with {ALLOC_PCT}% of equity (or the cash left). When "
        "more ETFs qualify than slots are free, the strongest {RANK_DAYS}-session return wins: the series' "
        "one-week scan. A full book takes nothing new until a position exits — one in, one out.",
        "Universe, India: gold, silver, Nifty 50, Next 50, Midcap 150, Bank, PSU Bank, IT, Pharma, Auto, CPSE, "
        "Nasdaq 100, FANG+, S&P 500 Top 50 and Hang Seng ETFs. US: SPY, QQQ, IWM, MDY, EFA, EEM, TLT, IEF, GLD, "
        "SLV, USO, DBC, SMH and the nine sector SPDRs.",
    ),
    "caveats": (
        "**The one-week ranking runs against published evidence.** Returns over one week to one month tend to "
        "reverse (the short-term reversal effect); momentum works over 3–12 months. It is kept because it is the "
        "series' rule and this strategy exists to measure that rule; RANK_DAYS is the knob to test.",
        "**Several India ETFs are young or were only fetched in October 2026**: an ETF joins the book only after "
        "{MIN_BARS} stored sessions, so the India opportunity set grows through a run.",
        "**Prices exclude distributions**, which matters little for gold, silver and growth index ETFs and a "
        "little more for bond and dividend-heavy funds.",
        "**Costs are {COST_BPS}bps a side**; expense ratios and tracking error are not modelled.",
        "**Fills are at the signal close**, which assumes an order placed in the last minutes of the session.",
    ),
    "entry_rules": (
        "All at the close of session t: close > the highest high of sessions t-{ENTRY_DAYS}..t-1; close > the "
        "{TRAIL_EMA}-day EMA; at least {MIN_BARS} sessions stored; 50-day average traded value ≥ the floor.",
        "Ranked by close ÷ close {RANK_DAYS} sessions earlier − 1, highest first, into the free slots.",
        "Size: {ALLOC_PCT}% of equity (cash plus holdings at the close), whole units, less {COST_BPS}bps.",
    ),
    "exit_rules": (
        "Sold in full at the close of the first session that closes below the {TRAIL_EMA}-day EMA, less {COST_BPS}bps.",
        "R is measured against the distance from the entry to the EMA on the entry day — the initial trailing level.",
        "Still open at the end of a test: valued at the final close, with no exit cost.",
    ),
}


class EtfSwingStrategy(PortfolioStrategy):
    """The series' swing system on ETFs."""

    key = DOC["key"]
    doc = DOC
    family = "etf_swing"
    version = "1.0"
    changelog = (("1.0", "2026-10-28", "First version: the swing system of 'The Long & The Short' Ep. 44 on liquid "
                                       "ETFs — a 21-day breakout, ranked by one-week return, five 20% slots, out on a "
                                       "close below the 21-day EMA."),)
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    runner = "etf_swing"

    param_docs = (
        ("Breakout", "ENTRY_DAYS", "Sessions whose highest high a close must clear."),
        ("Ranking", "RANK_DAYS", "Sessions of return the candidates are ranked by."),
        ("Slots", "MAX_POSITIONS", "Positions held at most."),
        ("Allocation", "ALLOC_PCT", "% of equity per position."),
        ("Trail", "TRAIL_EMA", "Days in the exponential average whose break sells."),
        ("Minimum history", "MIN_BARS", "Sessions an ETF needs before it can signal."),
        ("Cost per side", "COST_BPS", "Basis points charged on each buy and sell."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="ETF swing")
    ap.add_argument("--strategy", default="etf_swing")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    cfg = MARKETS[a.market]
    tdf, eq, held, used = run(a.market, a.start, float(cfg.account_size))
    b = cache.load_cached(a.market, cfg.benchmark_ticker)
    bc = b["close"].astype(float).reindex(eq.index).ffill() if b is not None else None
    notes = [f"ETFs with stored prices: {', '.join(s.replace('.NS', '') for s in used)}.",
             f"A {ENTRY_DAYS}-day breakout, ranked by {RANK_DAYS}-day return, {MAX_POSITIONS} slots of {ALLOC_PCT:g}%, "
             f"out on a close below the {TRAIL_EMA}-day EMA; {COST_BPS:g}bps a side."]
    costs = float(tdf["costs"].sum()) if len(tdf) else 0.0
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=MAX_POSITIONS,
                           costs_paid=costs, bench_close=bc, notes=notes)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"
    name = f"{a.start}_etf-swing-{ENTRY_DAYS}d-rank{RANK_DAYS}-ema{TRAIL_EMA}_{EtfSwingStrategy.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, MAX_POSITIONS))
    try:
        from . import report as report_mod
        md = report_mod.write_report(out, f"{cfg.name} — ETF swing, {a.start} onward", perf, eq, held, tdf,
                                     cfg.currency_symbol, MAX_POSITIONS, bc,
                                     f"python3 -m swing_screener.backtesting.etf_swing --market {a.market} --start {a.start}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
