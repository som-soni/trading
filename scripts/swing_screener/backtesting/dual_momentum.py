"""Dual momentum — hold the strongest asset, step aside when none beats cash.

Antonacci's rule, as the Learn guide "Dual momentum" describes it. Two checks each month:

* RELATIVE momentum — which of a handful of broad assets has the best trailing return;
* ABSOLUTE momentum — has that winner beaten cash? If not, hold the safe asset instead.

Deliberately NOT built on `portfolio_sim` or `baseline.run`. Both rank a universe of STOCKS and
hold many of them; this holds exactly one asset-class series at a time, chosen from four or five.
Forcing it into either would have meant a universe of fake one-symbol "stocks" and a position
sizer with nothing to size. It reuses `metrics` for the report, so a run reads and ingests like
every other backtest.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import index_data
from ..strategies.base import PortfolioStrategy
from . import metrics

logger = logging.getLogger(__name__)

#: The choices per market: (series key, label). The safe asset is `SAFE` and is never ranked --
#: it is where the rule goes when nothing clears it.
ASSETS = {
    "india": [("NIFTY50_TR", "Nifty 50 (total return)"), ("MIDCAP", "Nifty Midcap"),
              ("GOLD", "Gold"), ("US_IN_INR", "US equities in rupees")],
    "us": [("SP500_TR", "S&P 500 (total return)"), ("NASDAQ100", "Nasdaq 100"),
           ("INTL", "Developed ex-US"), ("GOLD", "Gold")],
}
SAFE = {"india": ("CASH_FUND", "Liquid fund"), "us": ("BONDS", "Treasuries (7-10y)")}


def load_assets(market: str, keys: list[str]) -> pd.DataFrame:
    """Close series for the named assets, aligned on their common calendar."""
    cols = {}
    for k in keys:
        try:
            s = index_data.load(market, k)
        except Exception as e:   # noqa: BLE001 -- a missing series is a config problem, not a crash
            logger.warning("%s:%s unavailable (%s)", market, k, e)
            continue
        if s is not None and len(s):
            cols[k] = s.astype(float)
    if not cols:
        raise ValueError(f"no asset series available for {market}")
    return pd.DataFrame(cols).sort_index().ffill()


def run(market: str, start: str, lookback_months: int = 12, rebalance: str = "ME",
        cost_bps: float = 10.0, assets: list | None = None):
    """Walk month-ends, hold one asset, and record every switch as a trade."""
    cfg = MARKETS[market]
    choices = assets or [k for k, _ in ASSETS[market]]
    safe_key, safe_label = SAFE[market]
    px = load_assets(market, [*choices, safe_key])
    choices = [c for c in choices if c in px.columns]
    if safe_key not in px.columns:
        raise ValueError(f"{market}: safe asset {safe_key} is not stored")

    start_ts = pd.Timestamp(start)
    # The lookback is READ in trading days so the signal uses only bars that exist; a calendar
    # offset silently reaches past a market holiday into a day with no price.
    look = int(lookback_months * 21)
    ret = px / px.shift(look) - 1.0
    rebal = pd.DatetimeIndex([d for d in px.index if d >= start_ts]).to_series().resample(rebalance).last().dropna()
    rebal = [d for d in rebal if d in px.index]

    equity, held, units = [], None, 0.0
    cash = float(cfg.account_size)
    trades, entry = [], None
    costs_total = 0.0
    for d in px.index[px.index >= start_ts]:
        if d in rebal:
            r = ret.loc[d]
            ranked = [c for c in choices if pd.notna(r.get(c))]
            best = max(ranked, key=lambda c: r[c]) if ranked else None
            safe_r = r.get(safe_key, 0.0)
            # ABSOLUTE momentum: the winner must beat the safe asset, or the rule holds the safe one
            target = best if (best is not None and pd.notna(safe_r) and r[best] > safe_r) else safe_key
            if target != held:
                if held is not None:
                    gross = units * float(px.loc[d, held])
                    fee = gross * cost_bps / 10_000
                    cash, costs_total = gross - fee, costs_total + fee
                    trades.append({"symbol": held, "entry_date": entry[0], "entry_price": round(entry[1], 4),
                                   "exit_date": d, "exit_price": round(float(px.loc[d, held]), 4),
                                   "shares": round(units, 4), "exit_reason": "ROTATE",
                                   "pnl": round(gross - fee - entry[2], 2), "notional": round(entry[2], 2),
                                   "costs": round(fee, 2), "holding_days": (d - entry[0]).days,
                                   "r_multiple": round((gross - fee) / entry[2] - 1, 4)})
                price = float(px.loc[d, target])
                fee = cash * cost_bps / 10_000
                cash -= fee
                costs_total += fee
                units, held, entry = cash / price, target, (d, price, cash)
                cash = 0.0
        equity.append((d, units * float(px.loc[d, held]) if held else cash))

    eq = pd.Series(dict(equity)).sort_index()
    if held is not None:
        d = eq.index[-1]
        gross = units * float(px.loc[d, held])
        trades.append({"symbol": held, "entry_date": entry[0], "entry_price": round(entry[1], 4),
                       "exit_date": d, "exit_price": round(float(px.loc[d, held]), 4),
                       "shares": round(units, 4), "exit_reason": "OPEN",
                       "pnl": round(gross - entry[2], 2), "notional": round(entry[2], 2), "costs": 0.0,
                       "holding_days": (d - entry[0]).days, "r_multiple": round(gross / entry[2] - 1, 4)})
    tdf = pd.DataFrame(trades)
    pos = pd.Series(1, index=eq.index)
    return tdf, eq, pos, px, costs_total


DM_DOC = {
    "key": "dual_momentum",
    "name": "Dual momentum",
    "description": "Each month hold the strongest of a few broad assets — but only if it beats cash; "
                   "otherwise hold the safe asset.",
    "status": (
        "MEASURED, AND THE WINDOW DECIDES IT. From 2020 it beats both markets with less drawdown: India 23.94% "
        "CAGR against the Nifty 500's 12.63% (+11.3), max drawdown -24.4% against -38.3%, Sharpe 1.06 against "
        "0.76; US 19.77% against SPY's 13.41% (+6.4), -32.6% against -34.1%, Sharpe 0.92 against 0.73. That is "
        "the only strategy here to beat BOTH indices on return and drawdown together. "
        "From 2010 it mostly goes away: India +3.72 excess with the same -37.7% drawdown and Sharpe 0.70 against "
        "0.68, and the US LOSES at -1.41 excess with a worse drawdown (-36.1% against -34.1%) and a worse Sharpe "
        "(0.63 against 0.75). So the 2020 figures are a regime, not an edge: that window holds gold's run and the "
        "post-COVID recovery, and it excludes the 2010s, when the absolute check cost money in a market that "
        "never had a long bear. Read the 2010 numbers as the expectation and the 2020 ones as what a good "
        "stretch looks like. 58 switches in India and 55 in the US since 2010, so the cost assumption matters."
    ),
    "thesis": "Trends persist across whole asset classes for the same reasons they persist in stocks — slow "
              "reaction to news, and investors who chase performance. Relative momentum says which asset to own; "
              "absolute momentum says whether to own anything at all, which is what sidesteps a long bear market.",
    "how_it_works": (
        "On each month-end, measure every choice's trailing {lookback_months}-month return.",
        "RELATIVE momentum: the strongest of them is the candidate.",
        "ABSOLUTE momentum: that candidate is held only if its return beats the safe asset's. If it does not, "
        "the safe asset is held instead — this is the check that steps aside in a long decline.",
        "One asset is held at a time, in full. Nothing is ranked within an asset and no stock is picked.",
    ),
    "caveats": (
        "**It is an allocation rule, not a trading strategy.** It holds whole markets, so it cannot be compared "
        "to a stock-picking strategy's trade statistics; its 'trades' are switches.",
        "**It whipsaws in fast falls.** The 12-month signal turns only after a crash, so a V-shaped recovery sells "
        "near the low and buys back higher. India in March 2020 is the example.",
        "**It needs a safe asset that is actually safe.** In 2022 US Treasuries fell with equities, so the rule "
        "rotated into something that also lost.",
        "**The asset menu is a choice, not a law.** These four per market are what is stored; a different menu "
        "gives a different strategy, and the result should not be read as 'dual momentum works'.",
        "Series are total-return where one is stored (NIFTY50_TR, SP500_TR) and price-only otherwise, so gold and "
        "international returns exclude nothing but equity dividends are included unevenly across the menu.",
    ),
    "entry_rules": (
        "Bought at the month-end close of the session the rule switches, in full.",
        "No stop, no target, no position sizing: one asset, 100% of capital.",
    ),
    "exit_rules": (
        "Sold at the next month-end on which another asset ranks higher, or the winner stops beating the safe asset.",
        "{cost_bps}bps is charged on each side of a switch.",
    ),
}


class DualMomentumStrategy(PortfolioStrategy):
    """Antonacci's dual momentum over a small asset menu, as the Learn guide describes it."""

    key = DM_DOC["key"]
    doc = DM_DOC
    family = "dual_momentum"
    version = "1.0"
    changelog = (("1.0", "2026-10-17", "First version: relative plus absolute momentum over four stored asset "
                                       "series per market, with a liquid fund (India) or Treasuries (US) as the "
                                       "safe asset."),)
    name = DM_DOC["name"]
    description = DM_DOC["description"]
    status = DM_DOC["status"]
    thesis = DM_DOC["thesis"]
    how_it_works = tuple(DM_DOC["how_it_works"])
    caveats = tuple(DM_DOC["caveats"])

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "trend"
    runner = "dual_momentum"          # the module whose main() backtests it

    lookback_months = 12
    rebalance = "ME"
    cost_bps = 10.0
    backtest_start = "2010-01-01"

    param_docs = (
        ("Lookback", "lookback_months", "Months of trailing return used for both checks."),
        ("Rebalance", "rebalance", "Pandas offset alias; ME is month-end."),
        ("Cost per side", "cost_bps", "Basis points charged on each side of a switch."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Dual momentum asset rotation")
    ap.add_argument("--strategy", default="dual_momentum")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--lookback-months", type=int, default=DualMomentumStrategy.lookback_months)
    ap.add_argument("--cost-bps", type=float, default=DualMomentumStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    tdf, eq, pos, px, costs = run(a.market, a.start, a.lookback_months,
                                  DualMomentumStrategy.rebalance, a.cost_bps)
    from ..marketdata import cache
    b = cache.load_cached(a.market, cfg.benchmark_ticker)
    bc = b["close"].astype(float).reindex(eq.index).ffill() if b is not None else None
    notes = [
        "An ALLOCATION rule: it holds one whole asset at a time, so its 'trades' are switches and its "
        "trade statistics are not comparable to a stock strategy's.",
        f"Assets: {', '.join(l for _, l in ASSETS[a.market])}; safe asset {SAFE[a.market][1]}.",
        f"Costs: {a.cost_bps:g}bps per side of a switch. Series are total-return where one is stored.",
    ]
    perf = metrics.compute(equity=eq, positions_open=pos, trades=tdf, max_open_positions=1,
                           costs_paid=costs, bench_close=bc, notes=notes)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"
    name = f"{a.start}_dualmom{a.lookback_months}m_{a.cost_bps:g}bps_{DualMomentumStrategy.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": pos,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 1))
    try:
        from . import report as report_mod
        md = report_mod.write_report(out, f"{cfg.name} — dual momentum, {a.start} onward", perf, eq, pos, tdf,
                                     cfg.currency_symbol, 1, bc,
                                     f"python3 -m swing_screener.backtesting.dual_momentum --market {a.market} --start {a.start}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
