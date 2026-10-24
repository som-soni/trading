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
from ..marketdata import cache, index_data
from ..strategies.base import PortfolioStrategy
from . import baseline, metrics, rotation

logger = logging.getLogger("backtest")

MODES = ("index", "stocks")

# ---- Faber's index rule
FABER_MONTHS = 10            # Faber's own lookback: month-end closes in the average
# 2.0 holds four sleeves, one per lookback, instead of choosing one. Measured over 1981-2026 (US)
# and 2010-2026 (both markets), no single lookback won every window -- 6 won some, 12 others --
# so picking the best of them is fitting a window; holding all of them is not. Spelled as three
# numbers rather than a tuple so the docs can render them and the fingerprint can see them.
FABER_LOOKBACK_MIN = 6
FABER_LOOKBACK_MAX = 12
FABER_LOOKBACK_STEP = 2
FABER_LOOKBACKS = tuple(range(FABER_LOOKBACK_MIN, FABER_LOOKBACK_MAX + 1, FABER_LOOKBACK_STEP))
# ---- the guide's four stock conditions
FAST_SMA = 50
SLOW_SMA = 200
SLOPE_BARS = 20              # the 200-day must be higher than it was this many sessions ago
REBALANCE = "ME"


def holdable(market: str, series: str | None = None) -> tuple[pd.Series, list[str]]:
    """The benchmark as something that can be HELD: dividends in, expense ratio out.

    Through index_data.total_return_index, so this rule and every index strategy make a price index
    holdable the same way -- in the US the adjusted SPY net of its expense ratio, in India the Nifty
    500 price index plus the calibrated dividend accrual (a lower bound; see INDIA_DIV_YIELD).
    """
    return index_data.total_return_index(market, series or MARKETS[market].benchmark_symbol)


def faber(market: str, start: str, months: int = FABER_MONTHS, cost_bps: float = 10.0,
          series: str | None = None, preloaded=None, capital: float | None = None,
          cash_rate: pd.Series | None = None, quote: pd.Series | None = None):
    """Hold the index while its month-end close is above its `months`-month average, else cash.

    The average is of MONTH-END closes, not a 200-day average sampled monthly. Faber's rule is
    defined on monthly data and the two differ: a 10-month average of month-ends is smoother than
    any daily average, which is most of why the rule whipsaws less than its daily cousins.

    Out of the market the money earns the cash rate (index_data.cash_rate_series). 1.0 left it at
    zero, which no account does and which charged this rule for every month it stepped aside --
    the very months it exists for. `capital` lets ensemble() run it as one sleeve of the book.

    Returns are earned on the total-return series, but the recorded fill prices come from `quote`,
    the price series the chart draws: a total-return level sits below the traded price by every
    dividend since the series began (SPY's 2020-01-31 close was ~321; its total-return level here
    is ~286), and the chart pins each buy marker AT the recorded price. Shares are restated at the
    quote so shares x price is the money spent; P&L still includes the dividends received.
    """
    cfg = MARKETS[market]
    close = preloaded if preloaded is not None else holdable(market, series)[0]
    if cash_rate is None:
        cash_rate = index_data.cash_rate_series(market, close.index)[0]
    if quote is None and preloaded is None:
        quote = _index_close(market, series or cfg.benchmark_symbol)
    shown = (lambda d, held_px: float(quote.asof(d))) if quote is not None else (lambda d, held_px: held_px)
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
    equity = float(cfg.account_size if capital is None else capital)
    units, trades, curve, cash_log, held_log, costs = 0.0, [], [], [], [], 0.0
    entry, prev = None, None
    for d in close.index:
        if d < start_ts:
            continue
        # Interest on idle cash for the CALENDAR days since the last session, at rate/365 --
        # index_core's accrual rule: per-bar rate/252 pays only ~69% of the real interest.
        if units == 0 and equity > 0 and prev is not None:
            r = float(cash_rate.get(d, float("nan")))
            if r == r and r > 0:
                equity *= (1.0 + r / 365.0) ** (d - prev).days
        prev = d
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
                               "exit_date": d, "exit_price": round(shown(d, px), 4),
                               "shares": round(entry[2] / entry[1], 4), "exit_reason": "BELOW_MA",
                               "pnl": round(equity - entry[2], 2), "notional": round(entry[2], 2),
                               "costs": round(fee, 2), "holding_days": (d - entry[0]).days,
                               "r_multiple": round(equity / entry[2] - 1, 4)})
                units = 0.0
            else:                                      # buy
                fee = equity * cost_bps / 10_000
                units = (equity - fee) / px
                costs += fee
                entry = (d, shown(d, px), equity - fee)
                equity = 0.0
        val = equity + units * px
        curve.append((d, val))
        cash_log.append((d, equity))
        held_log.append((d, 1 if units > 0 else 0))

    eq = pd.Series(dict(curve)).sort_index()
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(cash_log)).sort_index(), costs)


def ensemble(market: str, start: str, lookbacks: tuple = FABER_LOOKBACKS, cost_bps: float = 10.0):
    """Faber's rule once per lookback, each on an equal share of the book, summed.

    Independent sleeves rather than one fractional position rebalanced monthly: each sleeve's round
    trips are exact and sum to its own curve, and the sleeves are allowed to drift. Measured against
    rebalancing back to equal weight every month, the two agree to within 0.1pp of CAGR in both
    markets from 2010 and from 2020.
    """
    cfg = MARKETS[market]
    close, caveats = holdable(market)
    rate, rate_notes = index_data.cash_rate_series(market, close.index)
    share = float(cfg.account_size) / len(lookbacks)
    quote = _index_close(market, MARKETS[market].benchmark_symbol)
    parts = [faber(market, start, months=n, cost_bps=cost_bps, preloaded=close, capital=share,
                   cash_rate=rate, quote=quote) for n in lookbacks]
    trades = [p[0].assign(setup=f"{n}m") for n, p in zip(lookbacks, parts) if len(p[0])]
    tdf = pd.concat(trades, ignore_index=True) if trades else pd.DataFrame()
    eq, held, cash = (sum(p[i] for p in parts) for i in (1, 2, 3))
    return tdf, eq, held, cash, sum(p[4] for p in parts), caveats + rate_notes


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
    "description": "Hold the index in equal sleeves, each invested while the month-end close is "
                   "above its own average and earning the cash rate otherwise. No ranking, no stop, "
                   "no target.",
    "status": (
        "2.0 CORRECTS TWO ERRORS IN 1.0 AND STOPS CHOOSING A LOOKBACK. 1.0 -- one 10-month rule, cash "
        "earning nothing, price on both sides -- had essentially zero selection (-0.22 India, -0.20 "
        "US from 2010) and served as the shelf's null. 2.0 credits the cash rate, holds and "
        "benchmarks total return, and splits the book across four lookbacks. "
        "On the same data from 2010 that lifts CAGR from 7.22% to 9.75% in the US and from 7.00% to "
        "9.94% in India, and cuts the maximum drawdown to -19.7% and -17.9% against buy-and-hold's "
        "-33.7% and -38.2%. "
        "IT STILL TRAILS BUY-AND-HOLD'S RETURN, in every window measured: 13.91% and 10.82% from "
        "2010, 14.89% and 12.94% from 2020. A timing rule on the index can only beat holding it by "
        "being out during declines, and these windows had few to avoid. What it buys is the same "
        "risk-adjusted return at half the drawdown: its Sharpe matches buy-and-hold's in three of "
        "four windows (0.72 against 0.76 in the US from 2010 is the exception). "
        "It is no longer the bare 10-month null; `--lookbacks 10` still runs Faber's single rule, "
        "with the cash and dividend corrections."
    ),
    "thesis": "A long moving average separates a market that is rising from one that is falling, "
              "without predicting either. It cannot pick winners and does not try. It steps aside "
              "early in a long decline and lets a few long trends pay for many small whipsaws. "
              "Faber's published point (2007) was how little machinery that needs: one check a month. "
              "Here it is the control. It has no ranking, no stop and no target, so any other trend "
              "strategy has to beat it to show its extra rules add something. 2.0 holds several "
              "lookbacks at once rather than one, because which lookback wins depends on the window "
              "and choosing the winner afterwards is fitting it.",
    "how_it_works": (
        "The idea. Hold what is above its long moving average and hold cash otherwise, checking "
        "once a month. No ranking, no stop, no target. In index mode the book is split into one "
        "sleeve per lookback -- every {FABER_LOOKBACK_STEP} months from {FABER_LOOKBACK_MIN} to "
        "{FABER_LOOKBACK_MAX} -- and each sleeve runs the rule on its own average.",
        "Steps, on the last trading session of each month, in order: find what passes the rule "
        "(see Entry), sell what no longer does (see Exit), then buy or re-weight what does — all "
        "at that session's close. Nothing happens between month-ends.",
        "Two modes. `index` (the default) is Faber's rule on the market's benchmark, held as total "
        "return, with idle cash earning the cash rate. `stocks` applies the guide's four stock "
        "trend conditions to every stock, unranked, and is unchanged from 1.0.",
        "Month-end means the last session of each calendar month that has a stored price — never "
        "the calendar date, which is a trading day only about 40% of the time.",
        "Where the rules come from. Faber (2007) for the index rule; the Learn guide's four stock "
        "conditions for the stock mode, without its stop and next-open entry (see Caveats). There "
        "is no written spec with row ids for this strategy.",
    ),
    "entry_rules": (
        "Index mode, buy. Each sleeve that is in cash buys the index with its own money at a "
        "month-end close above its average.\n\n"
        "- **Sleeves:** one per lookback, every {FABER_LOOKBACK_STEP} months from "
        "{FABER_LOOKBACK_MIN} to {FABER_LOOKBACK_MAX}, each starting with an equal share of the "
        "book. They are not rebalanced back to equal weight afterwards; each compounds on its own.\n"
        "- **Series:** the market's benchmark from its config, made holdable -- in the US the SPY "
        "fund with dividends reinvested and its expense ratio charged, in India the Nifty 500 index "
        "plus a calibrated dividend accrual, since no Nifty 500 total-return series is stored.\n"
        "- **The average:** the simple mean of the sleeve's last N month-end closes, this month's "
        "included. Not a daily average sampled monthly: an average of month-ends is smoother, which "
        "is most of why the rule whipsaws less than daily versions of it.\n"
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
        "Position size. Index mode: each sleeve holds all of its own money in the index or all of "
        "it in cash, so the book is invested in steps of one sleeve. Stocks mode: equal weights — the "
        "whole book (cash plus holdings at that close) is split equally among the names to hold, "
        "and holdings already owned are topped up or trimmed back to that weight. A change smaller "
        "than 0.01% of the book is skipped.",
        "Fill and cost. Every trade fills at the month-end close — the close the decision was made "
        "on, not the next open. Each buy and each sell pays {cost_bps} basis points of the value "
        "traded. A stock with no price that day trades at its last stored close.",
        "Cash. In index mode, money not in the index earns the market's cash rate -- the 13-week "
        "Treasury bill yield in the US, a liquid fund's realised yield in India -- accrued for every "
        "calendar day it is idle.",
        "When no trade is taken. Between month-ends nothing is bought or sold. In stocks mode, a "
        "month-end on which no stock qualifies puts the whole book in cash. There is no ranking in "
        "either mode: the moment one is added, this stops measuring the moving average.",
    ),
    "exit_rules": (
        "Index mode, sell. A month-end close at or below a sleeve's own average sells that sleeve "
        "at that close, into cash. Each sleeve exits on its own average, so the book steps out of "
        "the market one sleeve at a time -- the shortest lookback first, in a decline.",
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
        "**The index is not always a tradable instrument.** In the US the series is SPY, a fund "
        "that trades. In India it is the Nifty 500 index value, which cannot be bought directly; a "
        "real book buys an ETF or a future, adding tracking difference, spread, and roll or "
        "management cost. None of that is modelled beyond the {cost_bps} basis points per side.",
        "**India's dividends are an estimate.** No Nifty 500 total-return series is stored, so the "
        "index takes the flat dividend accrual calibrated on the Nifty 50 (0.83% a year). It is a "
        "lower bound -- the published Nifty 50 yield has run 1.1-1.4% -- and it is applied to the "
        "strategy and to buy-and-hold alike, so it moves both the same way.",
        "**Cash earns its rate in index mode only.** Stocks mode still earns nothing on idle cash "
        "and is price-only on both sides, as in 1.0; its cash line is unreliable (see above), so "
        "crediting interest on it would be crediting a number that is wrong.",
        "**The lookback set is a choice too.** Four sleeves remove the bet on any one lookback, not "
        "the bet on the set. Measured over sets from (3, 6, 9, 12) to (4 ... 14), the result moved "
        "little and every set beat the single 10-month rule from 2010 in both markets -- the gain "
        "comes from averaging, not from these four. It was still measured on the same data the "
        "rule is now shown on.",
        "**Stocks mode has survivorship bias.** Its stock list is today's listed stocks, so companies "
        "delisted before today are missing from the history, which flatters the result.",
        "**The last month of a run is partial.** Its last stored session is treated as a month-end, "
        "so a decision can be taken on it before the month is over.",
        "**Whipsaw is regime-dependent and the sample is small.** Each sleeve trades a few dozen "
        "times at most. The rule's cost is a sideways market, and whether these windows held a "
        "representative number of them is not something two markets and sixteen years can "
        "establish.",
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
    version = "2.0"
    changelog = (("2.0", "2026-10-24",
                  "Two corrections and one change of rule. Cash now earns the market's cash rate "
                  "while out (index_data.cash_rate_series, accrued per calendar day): 1.0 left it at "
                  "zero, which charged the rule for every month it stepped aside -- the months it "
                  "exists for. The index is held, and benchmarked, as total return "
                  "(index_data.total_return_index): 1.0 used prices on both sides, symmetric but "
                  "wrong once cash earns interest, since it would credit one side with income and "
                  "deny the other its dividends. And index mode now holds one sleeve per lookback "
                  "-- every FABER_LOOKBACK_STEP months from FABER_LOOKBACK_MIN to FABER_LOOKBACK_MAX "
                  "-- instead of the single 10-month rule: across 1981-2026 (US) and 2010-2026 (both "
                  "markets) no single lookback won every window, and every lookback set tried beat "
                  "the single rule from 2010 in both markets. Validated against an independent "
                  "harness to three decimals before shipping. From 2010: CAGR 7.22% -> 9.75% (US), "
                  "7.00% -> 9.94% (India); max drawdown -26.3% -> -19.7% and -25.6% -> -17.9%. "
                  "Still below buy-and-hold's return in every window measured. Stocks mode is "
                  "unchanged."),
                 ("1.0", "2026-10-18",
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
    max_names = 50
    cost_bps = 10.0

    param_docs = (
        ("Mode", "mode", "index: Faber's monthly rule on the benchmark. stocks: the unranked "
                         "cross-sectional trend filter."),
        ("Shortest lookback", "FABER_LOOKBACK_MIN", "index mode: month-end closes in the shortest "
                                                     "sleeve's average."),
        ("Longest lookback", "FABER_LOOKBACK_MAX", "index mode: month-end closes in the longest."),
        ("Lookback step", "FABER_LOOKBACK_STEP", "index mode: months between sleeves, so "
                                                 "{FABER_LOOKBACK_MIN}..{FABER_LOOKBACK_MAX} in "
                                                 "steps of {FABER_LOOKBACK_STEP}."),
        ("Faber's lookback", "FABER_MONTHS", "Faber's published single lookback; `--lookbacks "
                                             "{FABER_MONTHS}` runs that rule alone."),
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
    ap.add_argument("--lookbacks", default=",".join(str(n) for n in FABER_LOOKBACKS),
                    help="index mode: month-end averages, one sleeve each (default %(default)s); "
                         "'10' is Faber's original single rule")
    ap.add_argument("--max-names", type=int, default=MaTrendStrategy.max_names)
    ap.add_argument("--cost-bps", type=float, default=MaTrendStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    if a.mode == "index":
        lookbacks = tuple(int(x) for x in a.lookbacks.split(",") if x.strip())
        tdf, eq, held, csh, costs, data_notes = ensemble(a.market, a.start, lookbacks, a.cost_bps)
        cap = len(lookbacks)
        months = ", ".join(str(n) for n in lookbacks)
        extra = (f"Faber's rule on {cfg.benchmark_symbol} in {cap} equal sleeves, one per lookback "
                 f"({months} months): each sleeve holds the index while the month-end close is above "
                 "its own average of month-end closes, and earns the cash rate otherwise. Decided on "
                 "the last trading session of each month."
                 if cap > 1 else
                 f"Faber's original rule on {cfg.benchmark_symbol}: one position or none, decided on "
                 f"the last trading session of each month against the {months}-month average.")
        # the benchmark is held the same way the strategy holds the index -- dividends in, expense
        # out -- or the comparison credits one side with income the other is denied
        bc = holdable(a.market)[0].reindex(eq.index).ffill()
        notes_cost = (f"Costs: {a.cost_bps:g}bps per side. Out of the market each sleeve earns the "
                      "cash rate; both the strategy and the benchmark are total return.")
    else:
        tdf, eq, held, csh, costs = stocks(a.market, a.start, cost_bps=a.cost_bps,
                                           max_names=a.max_names)
        cap, extra = a.max_names, (
            "AN ADAPTATION, not the guide's stock rule: it holds every stock meeting the four trend "
            "conditions, equal-weighted and rebalanced monthly, with NO ranking and NO ATR stop. "
            "That isolates the trend filter, which is the thing worth measuring on its own.")
        # stocks are stored as prices, so the benchmark stays a price index too: symmetric
        bc = _index_close(a.market).reindex(eq.index).ffill()
        data_notes = []
        notes_cost = (f"Costs: {a.cost_bps:g}bps per side. Stocks mode is unchanged from 1.0: cash "
                      "earns nothing, and both sides are price only.")

    notes = [
        extra,
        "No ranking, no stop and no target: a timing rule on the index, which can beat holding it "
        "only by being out during declines.",
        notes_cost,
        *data_notes,
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=cap,
                           costs_paid=costs, bench_close=bc, cash=csh, notes=notes)
    for k, v in metrics.benchmark_stats(bc).items():
        setattr(perf, k, v)
    perf.benchmark_name = (f"{cfg.benchmark_symbol} total return" if a.mode == "index"
                           else f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})")

    tag = (f"faber{'-'.join(str(n) for n in lookbacks)}m-tr" if a.mode == "index"
           else f"stocks-top{a.max_names}")
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
            f"python3 -m swing_screener.backtesting.ma_trend --market {a.market} --start {a.start} --mode {a.mode}"
            + (f" --lookbacks {a.lookbacks}" if a.mode == "index" else ""))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
