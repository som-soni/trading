"""Sector rotation — hold the strongest few sectors, move when leadership changes.

The Learn guide "Sector rotation" as a rule: rank the market's sector indices by trailing return
each month and hold the top few, equal-weighted. Ranking is by RELATIVE STRENGTH, not by a
business-cycle model -- a cycle model needs a call on which phase the economy is in, which is a
forecast, not a rule.

The guide is blunt that the edge is small: with nine to twelve choices there is little to rank,
and it reports no US edge over 1999-2026. This implementation exists to measure that here rather
than to assume it.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from ..strategies.base import PortfolioStrategy
from . import metrics, rotation

logger = logging.getLogger(__name__)

#: A sector series must have this many bars to be ranked at all -- enough for the lookback plus a
#: margin. India lists sector ETFs late, so several only become eligible part-way through a run.
MIN_BARS = 300


def load_sectors(market: str) -> tuple:
    """(prices, {ticker: sector name}) for the sector series this market actually has."""
    cfg = MARKETS[market]
    cols, labels = {}, {}
    for sector, tkr in sorted(cfg.sector_index_map.items()):
        d = cache.load_cached(market, tkr)
        if d is None or len(d) < MIN_BARS:
            logger.info("%s: %s (%s) skipped — %d bars", market, sector, tkr, 0 if d is None else len(d))
            continue
        cols[tkr] = d["close"].astype(float)
        labels[tkr] = sector
    if not cols:
        raise ValueError(f"no usable sector series for {market}")
    return pd.DataFrame(cols).sort_index().ffill(), labels


def run(market: str, start: str, top_n: int = 3, lookback_days: int = 126,
        rebalance: str = "ME", cost_bps: float = 10.0, market_filter: bool = False):
    cfg = MARKETS[market]
    px, labels = load_sectors(market)
    bench = cache.load_cached(market, cfg.benchmark_ticker)
    bench_close = bench["close"].astype(float).reindex(px.index).ffill() if bench is not None else None
    bench_sma = bench_close.rolling(200).mean() if bench_close is not None else None

    def pick(d, r, _px):
        # A sector only ranks once it has the history to be ranked: without this a newly listed
        # ETF enters the top with a return measured over a handful of bars.
        ok = [c for c in px.columns if pd.notna(r.get(c)) and px[c].loc[:d].notna().sum() >= MIN_BARS]
        if market_filter and bench_close is not None:
            b, m = bench_close.get(d), bench_sma.get(d)
            if pd.notna(b) and pd.notna(m) and b < m:
                return []          # risk-off: hold nothing
        return sorted(ok, key=lambda c: r[c], reverse=True)[:top_n]

    tdf, eq, held, costs = rotation.simulate(px, pick, start, rebalance, cost_bps,
                                             float(cfg.account_size), lookback_days)
    if len(tdf):
        tdf = tdf.assign(sector=tdf.symbol.map(labels))
    return tdf, eq, held, costs, labels


SR_DOC = {
    "key": "sector_rotation",
    "name": "Sector rotation",
    "description": "Each month-end hold the {top_n} sectors with the best {lookback_days}-session (about "
                   "six-month) return, equal-weighted.",
    "status": (
        "MEASURED, and it lands where the guide said it would. India beats modestly and the US does not, on "
        "BOTH windows -- which is the useful part, because unlike dual momentum the answer does not depend on "
        "the window. From 2020: India 15.91% CAGR against the Nifty 500's 12.63% (+3.28), drawdown -29.1% "
        "against -38.3%, Sharpe 0.90 against 0.78; US 10.73% against SPY's 13.41% (-2.68), Sharpe 0.61 against "
        "0.73. From 2010: India +2.95 (13.12%, drawdown -35.5%, Sharpe 0.78 against 0.68), US -2.81 (9.22%, "
        "Sharpe 0.60 against 0.75). "
        "So the edge such as it is, is India-only and about 3 points, earned mostly by avoiding the weakest "
        "sectors rather than by catching the strongest -- and it comes with a materially better drawdown in "
        "both windows, which is the more interesting half. The US result reproduces the guide's own finding of "
        "no edge, over a different period and a different sector set, which is worth more than a single test. "
        "Note India ranks only two to five sectors before 2021 and up to 11 later as ETFs list, so its opportunity "
        "set grows mid-run."
    ),
    "thesis": "Leadership rotates between parts of the market and persists for months at a time — energy in "
              "2021-22, Indian IT in 2020-21 — so owning the sectors that have led should beat owning all of "
              "them. The same momentum idea as ranking stocks, over a much smaller set of choices, ranked by "
              "relative strength alone rather than by a business-cycle call.",
    "how_it_works": (
        "Once a month, on the last stored session of the month: rank the market's sector series by trailing "
        "{lookback_days}-session (about six-month) return and hold the top {top_n} at equal weight until the "
        "next month-end. Every trade is at that session's close. Entry and Exit give each test exactly.",
        "The sectors, US: the eleven SPDR sector ETFs (XLC, XLY, XLP, XLE, XLF, XLV, XLI, XLB, XLRE, XLK, XLU).",
        "The sectors, India: three NSE sector indices (Bank, IT, Pharma) and eight sector ETFs (PSU Bank, "
        "Private Bank, Auto, FMCG, Metal, Infra, Energy, Consumption).",
        "No stop, no target and, by default, no market filter: the ranking is the whole rule, and a sector "
        "leaves the book when it leaves the top {top_n} at a month-end.",
    ),
    "caveats": (
        "**The guide expects little here, and says so.** Nine to twelve choices is very little to rank, and it "
        "reports no US edge over 1999-2026. This is built to measure that, not to assume otherwise.",
        "**India's sector coverage is thin and late.** All 11 mapped series are stored, but most list late: the "
        "Pharma index from 2011, Consumption 2014, Private Bank 2019, FMCG 2021, Auto 2022, and Energy, Infra "
        "and Metal only in mid-2024. With the {MIN_BARS}-session history rule, an India run from 2010 ranks two "
        "sectors at first, three until 2013 -- so with a top {top_n} it held every rankable sector and selected "
        "nothing -- four or five until 2021, six to eight until late 2025, and all 11 only after that. A "
        "changing opportunity set, not a fixed one. The US ranks 9 in 2010, 10 from about 2017 and 11 from "
        "late 2019.",
        "**Three India sectors are indices, not funds.** Bank, IT and Pharma are NSE price indices, which cannot "
        "be bought directly; holding them assumes a fund that tracks them for no more than {cost_bps}bps a side.",
        "**Sector definitions are the index provider's.** NSE's sectoral indices and the SPDR sectors do not "
        "carve the market the same way, so the two markets are not running the same strategy.",
        "**Dividends are left out** of the sectors and of the benchmark (SPY, Nifty 500) alike: stored prices "
        "are closes without dividends.",
        "**Sector ETFs carry their own costs**, which are not modelled beyond {cost_bps}bps a side.",
    ),
    "entry_rules": (
        "Which sectors can be ranked. A series is used only if it has at least {MIN_BARS} stored sessions, and "
        "it is ranked on a month-end only once it has {MIN_BARS} sessions of prices up to that date, so a newly "
        "listed sector ETF cannot enter the top on a return measured over a handful of days.",
        "Trailing return. Close on the month-end session ÷ close {lookback_days} sessions earlier − 1, counted "
        "on the sectors' combined calendar -- about six months. No month is skipped. A series that did not "
        "trade on a day carries its last price.",
        "Selection. The {top_n} highest trailing returns are held. Any return qualifies, including a negative "
        "one: there is no absolute-momentum test. With {top_n} or fewer rankable sectors, all of them are held.",
        "Weighting. Equal: at every month-end the whole book -- cash plus holdings at their last price -- is "
        "divided by the number of sectors held, and each holding is bought or sold to that value, in fractional "
        "units. A change smaller than 0.01% of the book is skipped.",
        "Fill and cost. At the month-end session's close. {cost_bps}bps of the traded value is charged on every "
        "sale and every purchase, including the monthly resizing. Fees are paid after the book is sized, so "
        "cash can sit slightly below zero, by the fees.",
        "When it holds cash. Before the first month-end on or after the start date, and with `--market-filter` "
        "(off by default): when the benchmark (SPY, Nifty 500) closes strictly below its 200-day average on the "
        "month-end session, everything is sold and nothing is held until a month-end on which it is not below.",
    ),
    "exit_rules": (
        "Sold in full at a month-end close, less {cost_bps}bps, when the sector is no longer in the top "
        "{top_n} -- or, with `--market-filter` on, when the benchmark closes below its 200-day average.",
        "Resized at each month-end to the equal weight while it stays in the top {top_n}, so a winner is trimmed "
        "and a laggard topped up.",
        "Nothing else sells it: no stop, no target, and no trade between month-ends. Whatever is held at the end "
        "of a test is valued at the final close, with no exit cost.",
    ),
}


class SectorRotationStrategy(PortfolioStrategy):
    """Relative-strength sector rotation, as the Learn guide describes it."""

    key = SR_DOC["key"]
    doc = SR_DOC
    family = "sector_rotation"
    version = "1.0"
    changelog = (("1.0", "2026-10-17", "First version: rank the market's sector indices by 6-month return each "
                                       "month-end and hold the top 3, equal-weighted."),)
    name = SR_DOC["name"]
    description = SR_DOC["description"]
    status = SR_DOC["status"]
    thesis = SR_DOC["thesis"]
    how_it_works = tuple(SR_DOC["how_it_works"])
    caveats = tuple(SR_DOC["caveats"])

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "trend"
    runner = "sector_rotation"

    top_n = 3
    lookback_days = 126
    rebalance = "ME"
    cost_bps = 10.0

    param_docs = (
        ("Sectors held", "top_n", "How many sectors are held at a time."),
        ("Lookback", "lookback_days", "Bars of trailing return used to rank (about six months)."),
        ("Rebalance", "rebalance", "Pandas offset alias; ME is month-end."),
        ("Cost per side", "cost_bps", "Basis points charged on each side of a switch."),
        ("Minimum history", "MIN_BARS", "Bars a sector needs before it can be ranked."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Sector rotation")
    ap.add_argument("--strategy", default="sector_rotation")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--top-n", type=int, default=SectorRotationStrategy.top_n)
    ap.add_argument("--lookback-days", type=int, default=SectorRotationStrategy.lookback_days)
    ap.add_argument("--cost-bps", type=float, default=SectorRotationStrategy.cost_bps)
    ap.add_argument("--market-filter", action="store_true", help="hold nothing while the benchmark is below its 200-day")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    tdf, eq, held, costs, labels = run(a.market, a.start, a.top_n, a.lookback_days,
                                       SectorRotationStrategy.rebalance, a.cost_bps, a.market_filter)
    b = cache.load_cached(a.market, cfg.benchmark_ticker)
    bc = b["close"].astype(float).reindex(eq.index).ffill() if b is not None else None
    notes = [
        f"Ranked {len(labels)} sector series: {', '.join(sorted(labels.values()))}.",
        "An ALLOCATION rule over sector indices: it holds whole sectors, so its 'trades' are switches and its "
        "trade statistics are not comparable to a stock strategy's.",
        f"Costs: {a.cost_bps:g}bps per side of a switch; sector-fund expenses are not modelled.",
    ] + (["Market filter: nothing is held while the benchmark closes below its 200-day average."] if a.market_filter else [])
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=a.top_n,
                           costs_paid=costs, bench_close=bc, notes=notes)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"
    name = (f"{a.start}_sectors-top{a.top_n}_{a.lookback_days}d_{a.cost_bps:g}bps"
            + ("_mkt" if a.market_filter else "") + f"_{SectorRotationStrategy.spec_id()}")
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, a.top_n))
    try:
        from . import report as report_mod
        md = report_mod.write_report(out, f"{cfg.name} — sector rotation, {a.start} onward", perf, eq, held, tdf,
                                     cfg.currency_symbol, a.top_n, bc,
                                     f"python3 -m swing_screener.backtesting.sector_rotation --market {a.market} --start {a.start}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
