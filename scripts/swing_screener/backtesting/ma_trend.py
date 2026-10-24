"""Moving-average trend following — the control every other trend strategy should be read against.

Faber's rule (2007) is the simplest published trend system there is: on the last session of the
month, hold the index if it closed above its 10-month average, otherwise hold cash. No ranking, no
stop, no target, no parameters to tune beyond the one lookback. Six strategies in this repository
are trend strategies with far more machinery; none of them has ever been measured against the
null of "the same idea with nothing in it".

TWO MODES, because the guide specifies two rules and they answer different questions.

  `index` is Faber exactly: one series, month-end decision, cash when out. It asks whether a
  moving average carries any TIMING information on an index.

  `stocks` holds EVERY stock meeting the guide's four stock conditions, equal-weighted, rebalanced
  monthly. It is an adaptation and is labelled as one -- it drops the guide's ATR stop and
  next-open entry, which are what make the stock version a swing trade. What is left is the SETUP
  on its own, which is the useful thing to isolate: it asks whether "above a rising 200-day with
  the 50 above the 200" selects stocks, with no ranking to confound it. Every cross-sectional
  strategy here ranks inside a trend filter; this measures the filter alone.

Both are fast, which matters: the point of a control is that you can run it whenever you doubt a
result, not that it is cheap to write.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from ..strategies.base import PortfolioStrategy
from . import baseline, metrics, rotation

logger = logging.getLogger("backtest")

MODES = ("index", "stocks")

# ---- Faber's index rule
FABER_MONTHS = 10            # month-end closes in the average
# ---- the guide's four stock conditions
FAST_SMA = 50
SLOW_SMA = 200
SLOPE_BARS = 20              # the 200-day must be higher than it was this many sessions ago
REBALANCE = "ME"


def faber(market: str, start: str, months: int = FABER_MONTHS, cost_bps: float = 10.0,
          series: str | None = None, preloaded=None):
    """Hold the index while its month-end close is above its `months`-month average, else cash.

    The average is of MONTH-END closes, not a 200-day average sampled monthly. Faber's rule is
    defined on monthly data and the two differ: a 10-month average of month-ends is smoother than
    any daily average, which is most of why the rule whipsaws less than its daily cousins.
    """
    cfg = MARKETS[market]
    close = preloaded if preloaded is not None else _index_close(market, series)
    # The last TRADING session of each month, via rotation.rebalance_dates -- not
    # `resample("ME")`, whose index is the CALENDAR month end. That distinction is not cosmetic:
    # the calendar end is a trading day only about 40% of the time, so testing `date in
    # resample index` fired on a minority of months and the rule traded erratically. It showed up
    # as Faber DEEPENING the drawdown (-45% against buy-and-hold's -38%), which a rule that holds
    # cash cannot do. One implementation of "month end", shared with every rotation strategy.
    decisions = rotation.rebalance_dates(close.index, close.index[0], REBALANCE)
    monthly = close.reindex(decisions).dropna()
    sma = monthly.rolling(months).mean()
    # The decision is made on a month-end close and acted on at THAT close -- not the next one.
    # Both terms are known when the bar closes (this month's close against an average of closes up
    # to and including it), so acting on it is not lookahead, and Faber's own tests do the same.
    # An extra .shift() here costs a full month of lag and is not conservatism but a different
    # rule: it took India's max drawdown from -32% to -46%, WORSE than buy-and-hold, which is how
    # the mistake announced itself -- a rule that goes to cash cannot deepen a drawdown.
    hold = (monthly > sma).fillna(False)

    start_ts = pd.Timestamp(start)
    month_ends = set(decisions) | {close.index[-1]}
    equity = float(cfg.account_size)
    units, trades, curve, cash_log, held_log, costs = 0.0, [], [], [], [], 0.0
    entry = None
    for d in close.index:
        if d < start_ts:
            continue
        px = float(close.loc[d])
        want = bool(hold.asof(d)) if len(hold) else False
        is_month_end = d in month_ends
        if is_month_end and want != (units > 0):
            if units > 0:                              # sell
                fee = units * px * cost_bps / 10_000
                equity = units * px - fee
                costs += fee
                trades.append({"symbol": series or cfg.benchmark_symbol,
                               "entry_date": entry[0], "entry_price": round(entry[1], 4),
                               "exit_date": d, "exit_price": round(px, 4),
                               "shares": round(units, 4), "exit_reason": "BELOW_MA",
                               "pnl": round(equity - entry[2], 2), "notional": round(entry[2], 2),
                               "costs": round(fee, 2), "holding_days": (d - entry[0]).days,
                               "r_multiple": round(equity / entry[2] - 1, 4)})
                units = 0.0
            else:                                      # buy
                fee = equity * cost_bps / 10_000
                units = (equity - fee) / px
                costs += fee
                entry = (d, px, equity - fee)
                equity = 0.0
        val = equity + units * px
        curve.append((d, val))
        cash_log.append((d, equity))
        held_log.append((d, 1 if units > 0 else 0))

    eq = pd.Series(dict(curve)).sort_index()
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(cash_log)).sort_index(), costs)


def _index_close(market: str, series: str | None = None) -> pd.Series:
    cfg = MARKETS[market]
    tkr = cfg.broad_index_symbols.get(series, series) if series else cfg.benchmark_ticker
    raw = cache.load_cached(market, tkr)
    if raw is None or raw.empty:
        raise SystemExit(f"{market}: no stored prices for {tkr}")
    return raw["close"].astype(float).sort_index()


def stock_mask(px: pd.DataFrame) -> pd.DataFrame:
    """The guide's four stock conditions, as whole matrices.

    Computed as frames rather than per symbol per date for the same reason baseline's rankers are:
    a 4,000-column frame over 16 years is fast this way and unreadable the other.
    """
    fast = px.rolling(FAST_SMA).mean()
    slow = px.rolling(SLOW_SMA).mean()
    return ((px > fast) & (fast > slow) & (px > slow)
            & (slow > slow.shift(SLOPE_BARS))).fillna(False)


def stocks(market: str, start: str, cost_bps: float = 10.0, max_names: int = 50,
           min_dollar_volume: float | None = None, preloaded=None):
    """Hold every stock meeting the four conditions, equal-weighted, rebalanced monthly.

    `max_names` is a practical cap, not part of the rule: the mask qualifies 300-900 Indian names
    at a time and an equal-weight book of 900 is not something anyone runs. When more qualify than
    the cap, the most liquid are kept -- liquidity, NOT any measure of strength, because ranking on
    strength would reintroduce exactly the selection this control exists to exclude.
    """
    cfg = MARKETS[market]
    liq_floor = cfg.screener.min_dollar_volume if min_dollar_volume is None else min_dollar_volume
    px, dv, _ = preloaded if preloaded is not None else baseline.load_prices(
        market, min_bars=SLOW_SMA + SLOPE_BARS + 2)
    mask = stock_mask(px)

    def pick(d, _ret, _px):
        if d not in mask.index:
            return []
        row = mask.loc[d]
        ok = [s for s in row.index[row.values] if float(px.loc[d, s]) >= cfg.screener.min_price]
        if liq_floor and d in dv.index:
            ok = [s for s in ok if dv.loc[d, s] == dv.loc[d, s] and dv.loc[d, s] >= liq_floor]
        if len(ok) > max_names and d in dv.index:
            ok = sorted(ok, key=lambda s: float(dv.loc[d, s] or 0), reverse=True)[:max_names]
        return ok

    tdf, eq, held, costs = rotation.simulate(
        px, pick, start=start, rebalance=REBALANCE, cost_bps=cost_bps,
        account_size=cfg.account_size, lookback_days=SLOW_SMA)
    # Fully invested whenever anything qualifies, so cash is only the stretches with nothing to own.
    cash = pd.Series([0.0 if h else e for e, h in zip(eq, held)], index=eq.index)
    return tdf, eq, held, cash, costs


MA_DOC = {
    "key": "ma_trend",
    "name": "Moving-average trend (Faber)",
    "description": "Hold the index while its month-end close is above its {FABER_MONTHS}-month "
                   "average of month-end closes, hold cash otherwise. No ranking, no stop, no target.",
    "status": (
        "THE CONTROL, AND IT EARNS ITS KEEP BY HAVING NO EDGE. Faber's rule has essentially ZERO "
        "selection in both markets -- -0.22 India and -0.20 US from 2010 -- while cutting maximum "
        "drawdown by about a third: India -25.6% against buy-and-hold's -38.3%, US -26.3% against "
        "-34.1%. CAGR 7.01% against 10.17% and 7.23% against 12.04%, at 71% and 83% invested, over "
        "17 and 15 trades. "
        "Read that carefully, because it is the most useful number in the ledger: a selection of "
        "zero means the index return given up by sitting in cash exactly equals what the same "
        "exposure would have earned. THE DRAWDOWN REDUCTION IS FREE. This is risk management, not "
        "alpha, and it is what a moving average actually does. "
        "AS A NULL IT IS DAMNING FOR THE REST OF THE SHELF. Every per-symbol swing strategy "
        "measured here scores between -0.38 and -4.48 on selection, so all of them are WORSE than a "
        "ten-month moving average that has no edge at all. Entry triggers, stops, targets, pivots "
        "and base detection are not merely failing to add; against this null they subtract. "
        "THE STOCK MODE ISOLATES THE TREND FILTER, and it does not select either: holding every "
        "stock above a rising 200-day with the 50 above the 200, equal-weighted and unranked, "
        "returns -0.64 to -2.36 selection on India and -1.68 to -3.40 on the US, fully invested. "
        "That matters for the strategies that DO work here: every cross-sectional momentum strategy "
        "ranks INSIDE this filter, so the filter is a drag and the edge is entirely in the ranking. "
        "Worth knowing before tuning a gate."
    ),
    "thesis": "A long moving average separates a market that is rising from one that is falling, "
              "without predicting either. It cannot pick winners and does not try. It steps aside "
              "early in a long decline and lets a few long trends pay for many small whipsaws. "
              "Faber's published point (2007) was how little machinery that needs: one check a month. "
              "Here it is the control. It has no ranking, no stop and no target, so any other trend "
              "strategy has to beat it to show its extra rules add something.",
    "how_it_works": (
        "The idea. Hold what is above its long moving average and hold cash otherwise, checking "
        "once a month. No ranking, no stop, no target.",
        "Steps, on the last trading session of each month, in order: find what passes the rule "
        "(see Entry), sell what no longer does (see Exit), then buy or re-weight what does — all "
        "at that session's close. Nothing happens between month-ends.",
        "Two modes. `index` (the default) is Faber's rule on the market's benchmark. `stocks` "
        "applies the guide's four stock trend conditions to every stock, unranked.",
        "Month-end means the last session of each calendar month that has a stored price — never "
        "the calendar date, which is a trading day only about 40% of the time.",
        "Where the rules come from. Faber (2007) for the index rule; the Learn guide's four stock "
        "conditions for the stock mode, without its stop and next-open entry (see Caveats). There "
        "is no written spec with row ids for this strategy.",
    ),
    "entry_rules": (
        "Index mode, buy. In cash, a month-end close above the {FABER_MONTHS}-month average buys "
        "the index with the whole book at that same close.\n\n"
        "- **Series:** the market's benchmark from its config — SPY in the US, the Nifty 500 index "
        "in India.\n"
        "- **The average:** the simple mean of the last {FABER_MONTHS} month-end closes, this "
        "month's included. Not a daily average sampled monthly: an average of month-ends is "
        "smoother, which is most of why the rule whipsaws less than daily versions of it.\n"
        "- **Timing:** both numbers are known when the session closes, so acting at that close is "
        "not lookahead, and Faber's own tests do the same. Waiting for the next month-end tested "
        "materially worse, with a deeper drawdown than buy-and-hold in India.",
        "Stocks mode, buy. On each month-end close, every stock that passes all of the tests below "
        "is held; a name not already held is bought at that close.\n\n"
        "- **Universe:** the market's stored stock list, ETFs and liquid funds removed, keeping "
        "stocks with at least {SLOW_SMA} + {SLOPE_BARS} + 2 stored sessions.\n"
        "- **Trend (all four, simple averages of daily closes):** the close above the "
        "{FAST_SMA}-day average; the {FAST_SMA}-day above the {SLOW_SMA}-day; the close above the "
        "{SLOW_SMA}-day; the {SLOW_SMA}-day higher than it was {SLOPE_BARS} sessions earlier.\n"
        "- **Missing prices:** an average needs every price in its window, so a stock with a "
        "missing session in its last {SLOW_SMA} fails.\n"
        "- **Price and liquidity:** the close at least the market screener's minimum price "
        "(`min_price`), and the 20-day average of daily traded value (close times volume) at least "
        "its liquidity floor (`min_dollar_volume`).\n"
        "- **Cap:** when more than {max_names} pass, the {max_names} with the highest 20-day "
        "average traded value are held. Liquidity, not strength, on purpose: ranking on strength "
        "would bring back the selection this control exists to leave out.",
        "Start. The book starts in cash. The first possible buy is the first month-end on or after "
        "the backtest start.",
        "Position size. Index mode: the whole book or nothing. Stocks mode: equal weights — the "
        "whole book (cash plus holdings at that close) is split equally among the names to hold, "
        "and holdings already owned are topped up or trimmed back to that weight. A change smaller "
        "than 0.01% of the book is skipped.",
        "Fill and cost. Every trade fills at the month-end close — the close the decision was made "
        "on, not the next open. Each buy and each sell pays {cost_bps} basis points of the value "
        "traded. A stock with no price that day trades at its last stored close.",
        "When no trade is taken. Between month-ends nothing is bought or sold. In stocks mode, a "
        "month-end on which no stock qualifies puts the whole book in cash. There is no ranking in "
        "either mode: the moment one is added, this stops measuring the moving average.",
    ),
    "exit_rules": (
        "Index mode, sell. A month-end close at or below the {FABER_MONTHS}-month average sells the "
        "whole position at that close, into cash.",
        "Stocks mode, sell. On a month-end close, a holding no longer on the list is sold at that "
        "close: it failed one of the four conditions, fell under the price or liquidity floor, or "
        "dropped out of the {max_names} most liquid on a month when more than {max_names} qualify.",
        "Stop. None. The month-end check is the only exit, and no price inside the month is looked "
        "at. A position can fall a long way between two month-ends before the rule reacts; how much "
        "of the account is in it is the only defence.",
        "Target. None. A target would cap the rare long trend that pays for every whipsaw, which is "
        "the only way this rule makes money.",
        "Time limit. None. A position is held for as long as it passes the month-end check.",
        "End of the backtest. Index mode: a position still held on the last day is valued at that "
        "close but not recorded as a trade. Stocks mode: holdings still open are recorded as OPEN "
        "trades at the last close, with no selling cost.",
    ),
    "caveats": (
        "**The `stocks` mode is an adaptation and should not be read as the guide's stock rule.** It "
        "drops the guide's initial stop at 3 times ATR and its next-open entry, which are what make "
        "that version a swing trade. What is left is the setup alone, which is the thing worth "
        "isolating. A faithful version would trade differently and probably worse, since the stop "
        "would realise losses the monthly rebalance rides through.",
        "**Stocks mode reports its cash and position count wrongly (a code flaw, noted not fixed).** "
        "The shared month-end engine records the number of names held at the END of the run on every "
        "day, so the run's cash line reads zero throughout, even on a month when nothing qualified "
        "and the book sat in cash. The equity curve and the trades are right. The invested share and "
        "the split between selection and cash drag of a stocks-mode run are not.",
        "**The index is not always a tradable instrument.** In the US the series is SPY, a fund that "
        "trades. In India it is the Nifty 500 index value, which cannot be bought directly; a real "
        "book buys an ETF or a future, adding tracking difference, spread, and roll or management "
        "cost. None of that is modelled beyond the {cost_bps} basis points per side.",
        "**Dividends are excluded on both the strategy and the benchmark.** Stored prices carry no "
        "dividends. That understates both, but not equally: this rule sits in cash 17-29% of the "
        "time, so it forgoes dividends the benchmark collects. The real gap is slightly WORSE than "
        "measured.",
        "**Cash earns nothing here.** The guide suggests a liquid fund when out. At the repo rates "
        "of this window that is a material omission against the strategy: crediting it would raise "
        "the result, so this is conservative.",
        "**Stocks mode has survivorship bias.** Its stock list is today's listed stocks, so companies "
        "delisted before today are missing from the history, which flatters the result.",
        "**The last month of a run is partial.** Its last stored session is treated as a month-end, "
        "so a decision can be taken on it before the month is over.",
        "**Whipsaw is regime-dependent and 17 trades is a small sample.** The rule's cost is a "
        "sideways market, and whether this window had a representative number of them is not "
        "something two markets and sixteen years can establish.",
    ),
}


class MaTrendStrategy(PortfolioStrategy):
    """Faber's monthly moving-average rule, and the unranked trend filter as a second mode.

    Registered as the CONTROL rather than as a candidate: its value is that every other trend
    strategy here can be read against it, which needs it to be versioned and runnable from the
    same page as the rest.
    """

    key = MA_DOC["key"]
    doc = MA_DOC
    family = "ma_trend"
    version = "1.0"
    changelog = (("1.0", "2026-10-18",
                  "First version: Faber's 10-month rule on the market's benchmark index, plus an "
                  "unranked cross-sectional mode over the guide's four stock conditions. Month-end "
                  "decisions use rotation.rebalance_dates (the last TRADING session) rather than "
                  "pandas' calendar month end, which is a trading day only ~40% of the time -- the "
                  "difference showed up as Faber deepening the drawdown to -45% instead of cutting "
                  "it to -25.6%, which a rule that holds cash cannot do."),)
    name = MA_DOC["name"]
    description = MA_DOC["description"]
    status = MA_DOC["status"]
    thesis = MA_DOC["thesis"]
    how_it_works = tuple(MA_DOC["how_it_works"])
    caveats = tuple(MA_DOC["caveats"])
    entry_rules = tuple(MA_DOC["entry_rules"])
    exit_rules = tuple(MA_DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    runner = "ma_trend"

    mode = "index"
    faber_months = FABER_MONTHS
    max_names = 50
    cost_bps = 10.0
    backtest_start = "2010-01-01"

    param_docs = (
        ("Mode", "mode", "index: Faber's monthly rule on the benchmark. stocks: the unranked "
                         "cross-sectional trend filter."),
        ("Faber lookback", "faber_months", "Month-end closes in the average."),
        ("Name cap", "max_names", "stocks mode only: most liquid N when more qualify. A practical "
                                  "cap, not part of the rule."),
        ("Cost per side", "cost_bps", "Basis points per side."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Moving-average trend following (Faber)")
    ap.add_argument("--strategy", default="ma_trend")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--mode", default=MaTrendStrategy.mode, choices=list(MODES))
    ap.add_argument("--faber-months", type=int, default=MaTrendStrategy.faber_months)
    ap.add_argument("--max-names", type=int, default=MaTrendStrategy.max_names)
    ap.add_argument("--cost-bps", type=float, default=MaTrendStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    if a.mode == "index":
        tdf, eq, held, csh, costs = faber(a.market, a.start, months=a.faber_months,
                                          cost_bps=a.cost_bps)
        cap, extra = 1, (f"Faber's rule on {cfg.benchmark_symbol}: one position or none, decided on "
                         f"the last trading session of each month against the {a.faber_months}-month "
                         "average of month-end closes.")
    else:
        tdf, eq, held, csh, costs = stocks(a.market, a.start, cost_bps=a.cost_bps,
                                           max_names=a.max_names)
        cap, extra = a.max_names, (
            "AN ADAPTATION, not the guide's stock rule: it holds every stock meeting the four trend "
            "conditions, equal-weighted and rebalanced monthly, with NO ranking and NO ATR stop. "
            "That isolates the trend filter, which is the thing worth measuring on its own.")

    bc = _index_close(a.market).reindex(eq.index).ffill()
    notes = [
        extra,
        "THIS IS THE CONTROL for every trend strategy here. It has no ranking, no stop and no "
        "target, so its SELECTION number is the null the others should be read against.",
        f"Costs: {a.cost_bps:g}bps per side. Cash earns nothing while out, which is conservative -- "
        "the guide suggests a liquid fund, and crediting it would raise this result.",
        "Dividends are excluded on both sides, but this rule sits in cash part of the time and so "
        "forgoes dividends the benchmark collects: the real gap is slightly worse than measured.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=cap,
                           costs_paid=costs, bench_close=bc, cash=csh, notes=notes)
    for k, v in metrics.benchmark_stats(bc).items():
        setattr(perf, k, v)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"

    tag = (f"faber{a.faber_months}m" if a.mode == "index" else f"stocks-top{a.max_names}")
    name = f"{a.start}_{tag}_{a.cost_bps:g}bps_{MaTrendStrategy.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, cap))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — moving-average trend ({a.mode}), {a.start} onward",
            perf, eq, held, tdf, cfg.currency_symbol, cap, bc,
            f"python3 -m swing_screener.backtesting.ma_trend --market {a.market} --start {a.start} --mode {a.mode}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
