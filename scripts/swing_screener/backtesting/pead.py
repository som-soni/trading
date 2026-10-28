"""Post-earnings announcement drift — the first EVENT-DRIVEN mechanism measured here.

Ball and Brown (1968) found that prices keep moving in the direction of an earnings surprise for
weeks after it is announced, and Bernard and Thomas (1989, 1990) standardised the measurement.
This is the oldest documented anomaly in the list and the only one in this repository whose signal
comes from a FILING rather than from prices.

The Learn guide states the expected answer up front -- "in large US stocks the drift has mostly
disappeared since the 2000s", visible in India on a short sample -- so this is a test of a
prediction, not an open search.

WHERE THE SURPRISE COMES FROM. `quarterly_results` carries a `filed` date, which is the
announcement date and the only reason this is backtestable at all: 77,067 US filings from 2009
across 1,641 symbols, and 7,149 Indian ones from 2021 across 408. The India sample is thin and the
window short; the US one is the real test.

YEAR-AGO FIGURES COME FROM A SELF-JOIN, not from the `net_income_prior` column, for two reasons.
India's copy of that column is 100% NULL (0 of 7,155 rows) so it cannot serve both markets. And
where the US does have it, it disagrees with the self-join on 3.8% of pairs (2,671 of 70,596),
because `net_income_prior` is the comparative figure AS RESTATED in the current filing while the
self-join returns what was actually published a year ago. The originally published number is the
point-in-time correct one, and it is the one available in both markets.

THE SEASON RANK IS AN EXPANDING WINDOW, DELIBERATELY. The guide asks for growth "in the top fifth
of all companies reporting that season", but a company's rank against the full season is not
knowable when it reports -- most of the season has not reported yet. Ranking against the whole
season would be lookahead of exactly the kind that makes a backtest unreproducible in life. This
ranks against the filings already IN that season, so the first few filings of a season are ranked
against a small sample and the last are ranked against nearly all of it. That is the information a
trader actually has.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import asof
from ..marketdata import cache, corporate_actions, db
from ..strategies.base import PortfolioStrategy
from . import metrics, spec

logger = logging.getLogger("backtest")

# ---- the surprise (guide §3)
MIN_YOY_GROWTH = 25.0        # percent, year on year, on net profit
MIN_REVENUE_GROWTH = 10.0    # so the profit rise is not only cost cuts or one-offs
MIN_ACCELERATION = 0.0       # this quarter's YoY growth must exceed last quarter's
SEASON_RANK_TOP = 20.0       # percent: growth must be in the top fifth of the season so far
MIN_QUARTERS = 8             # of results history, for SUE's denominator

# ---- the price reaction
REACTION_DAYS = 2            # close before the results to the close after
MIN_REACTION = 0.0           # percent, against the index: the market must agree
MAX_REACTION = 20.0          # above this it is an episodic pivot, a different setup

# ---- the trade
HOLD_SESSIONS = 60           # the drift window Bernard and Thomas measured
MAX_POSITIONS = 15
POSITION_PCT = 8.0           # <= 10% of capital each, per the guide
STOP_ON_REACTION_LOW = True  # a close below the reaction-day low rejects the surprise

_EVENT_SQL = """
WITH q AS (
    SELECT market, symbol, period_end, filed, net_income, revenue, eps
      FROM quarterly_results
     WHERE market = %s AND filed IS NOT NULL
)
SELECT a.symbol, a.filed, a.period_end,
       a.net_income, y.net_income  AS ni_year_ago,
       a.revenue,    y.revenue     AS rev_year_ago,
       a.eps,        y.eps         AS eps_year_ago
  FROM q a
  JOIN q y
    ON y.symbol = a.symbol
   AND y.period_end BETWEEN a.period_end - INTERVAL '400 days'
                        AND a.period_end - INTERVAL '330 days'
 ORDER BY a.filed, a.symbol
"""


def load_events(market: str) -> pd.DataFrame:
    """One row per filing, with the year-ago comparatives joined on.

    `filed` is the announcement date. Everything downstream keys off it rather than off
    `period_end`, because the market cannot react to a quarter until it is published -- and the
    gap between the two runs 30-60 days, which is longer than the drift window being traded.
    """
    con = db.get_connection()
    ev = pd.read_sql(_EVENT_SQL, con, params=(market,))
    if ev.empty:
        return ev
    ev["filed"] = pd.to_datetime(ev["filed"])
    ev["period_end"] = pd.to_datetime(ev["period_end"])
    if asof.end() is not None:   # a backtest stage's boundary: a filing after it has not happened
        ev = ev[ev["filed"] <= asof.end()]

    # A growth rate off a loss is not a growth rate: the guide requires the year-ago profit to be
    # positive, and without that filter a swing from -1cr to +1cr reads as -200% and a swing from
    # +1cr to -1cr reads the same, which is worse than useless for ranking.
    ev = ev[(ev["ni_year_ago"] > 0) & ev["net_income"].notna()].copy()
    ev["yoy"] = (ev["net_income"] / ev["ni_year_ago"] - 1) * 100
    ev["rev_growth"] = ((ev["revenue"] / ev["rev_year_ago"] - 1) * 100).where(
        ev["rev_year_ago"] > 0)
    ev = ev.sort_values(["symbol", "period_end"])
    ev["accel"] = ev.groupby("symbol")["yoy"].diff()
    ev["quarters"] = ev.groupby("symbol").cumcount() + 1

    # SUE: the EPS change divided by its own standard deviation over the trailing 8 quarters --
    # Bernard and Thomas's measure. Shifted so the current quarter is not inside its own
    # denominator, which would shrink every large surprise toward zero.
    ev["eps_chg"] = ev["eps"] - ev["eps_year_ago"]
    sd = (ev.groupby("symbol")["eps_chg"]
            .transform(lambda s: s.shift().rolling(MIN_QUARTERS, min_periods=4).std()))
    ev["sue"] = ev["eps_chg"] / sd.replace(0, pd.NA)

    # Season rank, expanding WITHIN the season (see the module docstring: ranking against the full
    # season is lookahead). The season is the period_end, so all filings for the same quarter are
    # ranked against each other in the order they were filed.
    ev = ev.sort_values(["period_end", "filed", "symbol"])
    ev["season_pct"] = (ev.groupby("period_end")["yoy"]
                          .transform(lambda s: s.expanding().rank(pct=True) * 100))
    return ev.sort_values(["filed", "symbol"]).reset_index(drop=True)


def load_event_prices(market: str, symbols) -> dict:
    """Full OHLCV per symbol, for the symbols that actually have filings.

    Not `baseline.load_prices`: that returns close/turnover/SMA200 frames and this strategy needs
    the reaction day's LOW for its stop. Loading per symbol is affordable here precisely because
    the filing table is small -- 1,394 US names rather than the 5,000-name tape.

    `tr_close` is the close back-adjusted for credited special dividends and demergers: the reaction
    is measured on it, so an ex-date inside the window is not read as the market's verdict.
    """
    out = {}
    symbols = list(symbols)
    cr = corporate_actions.credits(market, symbols)
    by = {s: g for s, g in cr.groupby("symbol")} if len(cr) else {}
    for s in symbols:
        d = cache.load_cached(market, s)
        if d is None or len(d) < 60:
            continue
        out[s] = d.assign(tr_close=corporate_actions.back_adjust_ohlc(d[["close"]], by.get(s))["close"])
    return out


def run(market: str, start: str, hold_sessions: int = HOLD_SESSIONS,
        max_positions: int = MAX_POSITIONS, position_pct: float = POSITION_PCT,
        min_yoy: float = MIN_YOY_GROWTH, season_top: float = SEASON_RANK_TOP,
        cost_bps: float = 10.0, use_stop: bool = STOP_ON_REACTION_LOW,
        preloaded: tuple | None = None):
    """Walk the filing calendar, buy the confirmed surprises, hold for the drift window."""
    cfg = MARKETS[market]
    start_ts = pd.Timestamp(start)

    if preloaded is not None:
        ev, prices, bench = preloaded
    else:
        ev = load_events(market)
        prices = load_event_prices(market, sorted(ev["symbol"].unique()))
        braw = cache.load_cached(market, cfg.benchmark_ticker)
        bench = braw["close"].astype(float) if braw is not None else None
    if ev.empty or not prices:
        raise SystemExit(f"{market}: no filings with prices")

    floor_price = cfg.screener.min_price
    liq_floor = cfg.screener.min_dollar_volume

    # The trading calendar is the benchmark's, so a symbol that did not trade on a session cannot
    # silently shift the holding clock: HOLD_SESSIONS counts market sessions, not the symbol's own.
    cal = bench.index if bench is not None else next(iter(prices.values())).index
    cal = pd.DatetimeIndex([d for d in cal if d >= start_ts - pd.Timedelta(days=400)])
    pos_of = {d: i for i, d in enumerate(cal)}
    # The price floor reads the price traded on the buy day. The stored close is back-adjusted for
    # every later split, so a $10 floor on it dropped the later multi-baggers' early filings.
    # Every entry date is a calendar session (pos_of), so the factor frame is indexed on `cal`.
    split_k = spec.split_factor_after(market, cal, list(prices)) if floor_price and len(cal) else None

    # qualify each filing ONCE, up front: the decision uses only that filing's own row plus
    # prices up to the entry bar, so there is nothing to recompute per day.
    cand: dict = {}
    dropped = {"filters": 0, "no_bar": 0, "reaction": 0, "liquidity": 0}
    for r in ev.itertuples():
        if not (r.yoy >= min_yoy and (r.season_pct or 0) >= 100 - season_top
                and (r.accel or -1) > MIN_ACCELERATION
                and (r.rev_growth or -1) >= MIN_REVENUE_GROWTH):
            dropped["filters"] += 1
            continue
        df = prices.get(r.symbol)
        if df is None:
            dropped["no_bar"] += 1
            continue
        # the reaction window: the close BEFORE the filing to the close REACTION_DAYS after
        idx = df.index
        after = idx[idx >= r.filed]
        before = idx[idx < r.filed]
        if len(after) < REACTION_DAYS + 1 or len(before) < 1:
            dropped["no_bar"] += 1
            continue
        d_prev, d_react = before[-1], after[min(REACTION_DAYS - 1, len(after) - 1)]
        tc = df["tr_close"] if "tr_close" in df else df["close"]   # ratio only: no future action leaks
        p0, p1 = float(tc.loc[d_prev]), float(tc.loc[d_react])
        if p0 <= 0 or p1 != p1:
            dropped["no_bar"] += 1
            continue
        stock_ret = (p1 / p0 - 1) * 100
        if bench is not None:
            b = bench.reindex(idx).ffill()
            bret = (float(b.loc[d_react]) / float(b.loc[d_prev]) - 1) * 100
        else:
            bret = 0.0
        reaction = stock_ret - bret
        if not (MIN_REACTION < reaction <= MAX_REACTION):
            dropped["reaction"] += 1
            continue
        # entry is the session AFTER the reaction window closes
        later = idx[idx > d_react]
        if not len(later):
            dropped["no_bar"] += 1
            continue
        d_entry = later[0]
        if d_entry < start_ts or d_entry not in pos_of:
            continue
        entry_px = float(df.loc[d_entry, "close"])
        traded_px = entry_px * (float(split_k.at[d_entry, r.symbol])
                                if split_k is not None and r.symbol in split_k.columns else 1.0)
        if entry_px != entry_px or traded_px < floor_price:
            dropped["liquidity"] += 1
            continue
        turnover = float(df["close"].mul(df["volume"]).rolling(20).mean().loc[d_entry])
        if turnover != turnover or turnover < liq_floor:
            dropped["liquidity"] += 1
            continue
        cand.setdefault(d_entry, []).append({
            "symbol": r.symbol, "yoy": r.yoy, "sue": r.sue, "reaction": reaction,
            "price": entry_px, "stop": float(df.loc[d_react, "low"]),
            "filed": r.filed, "period_end": r.period_end,
        })

    # the next filing date per symbol, so a position can be closed before it reports again
    next_filing = {}
    for sym, g in ev.groupby("symbol"):
        next_filing[sym] = sorted(g["filed"].tolist())

    cash = float(cfg.account_size)
    open_pos: dict[str, dict] = {}
    trades, equity, cash_log, held_log, costs_total = [], [], [], [], 0.0

    def px_on(sym, d):
        df = prices[sym]
        hit = df.index[df.index <= d]
        return float(df.loc[hit[-1], "close"]) if len(hit) else float("nan")

    # a special dividend or demerger while held: the cash, and the stop moved down by it
    credits = corporate_actions.Credits.for_market(market, list(prices))
    credit_after = start_ts - pd.Timedelta(days=1)

    for i, d in enumerate(cal):
        if d < start_ts:
            continue
        for sym, c in credits.on(d, credit_after, open_pos).items():
            p = open_pos[sym]
            cash += p["units"] * c
            p["credited"] += p["units"] * c
            p["stop"] -= c
        credit_after = d
        # ---- exits first, so freed capital can be redeployed the same session
        for sym in list(open_pos):
            p = open_pos[sym]
            price = px_on(sym, d)
            if price != price:
                continue
            nxt = [f for f in next_filing.get(sym, []) if f > p["filed"]]
            reason = None
            if use_stop and price < p["stop"]:
                reason = "STOP"
            elif nxt and d >= nxt[0]:
                reason = "NEXT_RESULTS"
            elif i - p["i"] >= hold_sessions:
                reason = "DRIFT_WINDOW"
            if reason is None:
                continue
            gross = p["units"] * price
            fee = gross * cost_bps / 10_000
            cash += gross - fee
            costs_total += fee
            trades.append({
                "symbol": sym, "entry_date": p["date"], "entry_price": round(p["price"], 4),
                "exit_date": d, "exit_price": round(price, 4), "shares": round(p["units"], 4),
                "exit_reason": reason, "pnl": round(gross - fee - p["cost"] + p["credited"], 2),
                "credited": round(p["credited"], 2),
                "notional": round(p["cost"], 2), "costs": round(fee + p["fee"], 2),
                "holding_days": (d - p["date"]).days,
                "r_multiple": round((gross - fee + p["credited"]) / p["cost"] - 1, 4),
            })
            del open_pos[sym]

        # ---- entries: strongest surprise first when several land the same session
        todays = [c for c in cand.get(d, []) if c["symbol"] not in open_pos]
        todays.sort(key=lambda c: (-(c["sue"] if c["sue"] == c["sue"] else 0), -c["yoy"]))
        for c in todays:
            if len(open_pos) >= max_positions:
                break
            book = cash + sum(p["units"] * px_on(s, d) for s, p in open_pos.items())
            spend = min(book * position_pct / 100, cash)
            if spend <= 0:
                break
            fee = spend * cost_bps / 10_000
            cash -= spend
            costs_total += fee
            open_pos[c["symbol"]] = {
                "units": (spend - fee) / c["price"], "price": c["price"], "date": d,
                "cost": spend - fee, "fee": fee, "i": i, "stop": c["stop"], "filed": c["filed"], "credited": 0.0}

        val = cash + sum(p["units"] * px_on(s, d) for s, p in open_pos.items())
        equity.append((d, val))
        cash_log.append((d, cash))
        held_log.append((d, len(open_pos)))

    eq = pd.Series(dict(equity)).sort_index()
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(cash_log)).sort_index(), costs_total, dropped, len(cand))


PEAD_DOC = {
    "key": "pead",
    "name": "Post-earnings drift",
    "description": "Buy a confirmed earnings surprise -- profit growth of at least {MIN_YOY_GROWTH}% year on year, "
                   "accelerating, revenue up at least {MIN_REVENUE_GROWTH}%, in the top {SEASON_RANK_TOP}% of the season so far, and the market "
                   "agreeing over the first {REACTION_DAYS} sessions -- and hold for {HOLD_SESSIONS} sessions.",
    "status": (
        "THE PUBLISHED PREDICTION IS CONFIRMED, AND THE STRATEGY STILL FAILS. The Learn guide states the "
        "expected answer before any code existed: the drift has mostly disappeared in large US stocks since "
        "the 2000s, and was visible in India on a short sample. Both halves reproduce. "
        "US from 2010 (57,072 filings, 1,394 symbols): CAGR 3.73% against SPY's 12.04%, 1,548 trades, "
        "27.6% win rate, average +0.72% per trade, 60% invested, SELECTION -1.44. The drift is gone, which "
        "is what Ball and Brown's finding looks like 58 years after publication. "
        "India from 2022 reads +6.48 selection and THAT NUMBER IS NOT USABLE -- see the caveat on the "
        "universe. Measured against the set it actually trades rather than against the Nifty 500, it is "
        "deeply negative: the strategy returned 7.78% while an equal-weight BUY AND HOLD of its own "
        "eligible universe returned 31.49% over the same window. It underperformed doing nothing with the "
        "same stocks by more than 23 points a year. "
        "The shape is honest in both markets and worth knowing: a LOW WIN RATE with POSITIVE SKEW -- 27.6% "
        "US and 29.6% India -- so the few large drifts carry it, which is the opposite of the mean-reversion "
        "profile and makes small samples especially untrustworthy. "
        "Note it never loses much either: max drawdown -30.1% US and -12.4% India, against SPY's own -34%. "
        "This is a weak signal, not a dangerous one."
    ),
    # Every rule below was checked against run() and load_events() above. There is no spec with row
    # ids; the Learn guide research/learn-strat-pead.md §3 is the specification, cited by section.
    "thesis": "Ball and Brown (1968) found prices keep drifting in the direction of an earnings surprise for "
              "weeks afterwards, and Bernard and Thomas (1989) argued investors under-react because they do "
              "not fully grasp that quarterly earnings are serially correlated -- a good quarter predicts the "
              "next one more strongly than people price in. The trade is the oldest documented anomaly in "
              "the Learn module and the only one here whose signal comes from a filing rather than a price.",
    "how_it_works": (
        "The idea. Buy a company whose quarterly profit jumped, ranked near the top of its season, after "
        "the market has confirmed the news, and hold it through the weeks of drift that follow. The rules "
        "are the testable form of the Learn guide on post-earnings drift (its section 3). There is no spec "
        "with row ids, so each rule names the guide rule it implements and says where it differs.",
        "Step 1 — the surprise (Entry: the filing). Each stored quarterly filing is tested once, on four "
        "numbers from the company's own results: profit growth, its season rank, its acceleration and "
        "revenue growth.",
        "Step 2 — the market agrees (Entry: the reaction). Over the first sessions after the filing the "
        "stock must beat the index, but not by too much.",
        "Step 3 — the buy (Entry: the buy). At the close of the next session, a fixed {POSITION_PCT}% of the "
        "account, strongest surprise first.",
        "Step 4 — the sale (Exit). A close below the reaction low, the next filing, or {HOLD_SESSIONS} "
        "market sessions, whichever comes first. Every sale is at a close.",
        "Data. The event is the FILING DATE, not the quarter end: the market cannot react to a quarter "
        "until it is published, and the gap between the two runs 30-60 days. In the US it is the date the "
        "quarter's figures were first filed with the SEC (the 10-Q, or the annual 10-K for a fourth "
        "quarter); in India, the date of the results filing on NSE. Analysts' forecasts are not used.",
        "Running it. `python3 -m swing_screener.backtesting.pead --market us --start 2010-01-01`. The "
        "options are the holding period, the number of positions, the position size, the minimum growth, "
        "the season rank and the cost per side.",
    ),
    "entry_rules": (
        "The filing: profit growth. Net profit is at least {MIN_YOY_GROWTH}% above the same quarter a year "
        "earlier.\n\n"
        "- **Year-ago quarter:** the company's stored quarter that ended 330 to 400 days before this one, "
        "as it was first published then (not the restated figure in the new filing).\n"
        "- **Year-ago profit:** must be above zero. A filing with a year-ago loss, or no year-ago quarter, "
        "is never tested.\n\n"
        "**Guide (§3 Setup):** the same.",
        "The filing: season rank. The growth is in the top {SEASON_RANK_TOP}% of its season so far.\n\n"
        "- **Season:** every stored filing for a quarter ending on the same date.\n"
        "- **So far:** the filing is ranked by growth among that season's filings made on or before its "
        "own date (same-day filers in alphabetical order). The first filer of a season ranks top by "
        "definition, so it always passes.\n\n"
        "**Guide (§3 Setup):** top fifth of all companies reporting that season. Differs: the full season "
        "is not known on the day a company reports, so ranking against it would be lookahead.",
        "The filing: acceleration. This quarter's growth is more than {MIN_ACCELERATION} points above the "
        "growth of the company's previous stored quarter (the previous one that had a year-ago quarter "
        "with a profit). A company with no such previous quarter fails.\n\n"
        "**Guide (§3 Setup):** acceleration above zero — the same.",
        "The filing: revenue growth. Revenue is at least {MIN_REVENUE_GROWTH}% above the same quarter a year "
        "earlier, so the profit rise is not only cost cuts or one-off gains. A filing with no positive "
        "year-ago revenue fails.\n\n"
        "**Guide (§3 Setup):** the same.",
        "The reaction. The stock beats the benchmark index by more than {MIN_REACTION}% and at most "
        "{MAX_REACTION}%.\n\n"
        "- **Span:** from the close of the last session before the filing date to the close "
        "{REACTION_DAYS} sessions later, counting the first session on or after the filing date as the "
        "first.\n"
        "- **Measure:** the stock's return minus the index's return over the same span, in % points.\n"
        "- **Ceiling:** a bigger jump is an episodic pivot, which the Earnings gaps strategy trades.\n\n"
        "**Guide (§3 Setup and Entry):** the same.",
        "The buy. At the close of the session after the reaction span — the third session counting the "
        "filing day. There is no trigger and no limit order: the event has already happened.\n\n"
        "**Guide (§3 Entry):** the close of the second session after the results — the same session.",
        "Tradable on the buy day. The close must be at or above the market's price floor -- read as the price "
        "traded that day, the stored close multiplied back by every later split -- and the 20-day "
        "average traded value (close × volume) at or above its liquidity floor — the screener's floors "
        "($10 and $10 million in the US; no price floor and ₹50 crore in India, as configured in October "
        "2026).\n\n"
        "**Guide (§3 Universe):** $5 or ₹50 and $5 million or ₹5 crore. Differs: the market's own floors "
        "are used, and they are higher.",
        "Size. Each buy spends {POSITION_PCT}% of the account (cash plus open positions at the day's close), "
        "or the cash left if that is less. Fractional shares are allowed. It is not sized from the stop, so "
        "the amount lost at the stop varies from trade to trade.\n\n"
        "**Guide (§3 Position size):** either risk 0.5% per trade sized from the stop, or equal weights of "
        "at most 10% with no stop. Differs: this mixes the two — equal weights, and a stop as well.",
        "Positions and ties. At most {MAX_POSITIONS} positions, one per company. When more filings "
        "qualify on a session than there are free slots, the largest standardised surprise (SUE) is "
        "bought first, then the highest growth; the rest are dropped, not kept for later.\n\n"
        "- **SUE:** the change in EPS against the same quarter a year earlier, divided by the standard "
        "deviation of that change over the previous {MIN_QUARTERS} quarters (at least 4 needed; with "
        "fewer it counts as 0). It only ranks; it is not a filter.\n\n"
        "**Guide (§3 Setup):** SUE is one of the three surprise measures. The guide's minimum of "
        "{MIN_QUARTERS} quarters of history is not enforced.",
        "Costs. {cost_bps} basis points of the amount traded, on each side. No slippage is added on top.",
    ),
    "exit_rules": (
        "Each session after the buy, the position is checked at the close against these rules, in this "
        "order, and the first that applies sells everything at that close. Exits are settled before the "
        "day's buys, so cash freed by a sale can be spent the same session.",
        "Stop. A close below the low of the last session of the reaction span (the session before the "
        "buy). It is not a standing order: nothing sells during the day, and the sale is at the close, "
        "which can be well below the stop.\n\n"
        "**Guide (§3 Initial stop):** a close below the reaction-day low — the same.",
        "Next results. The close of the first session on or after the company's next stored filing date. "
        "That is the filing day itself, not the day before, so the results' own reaction is held whenever "
        "it comes before that close — a release before or during the session, or, in the US, a press "
        "release days before the SEC filing. Only filings that have a year-ago quarter with a profit are "
        "in that list, so a next filing without one is missed.\n\n"
        "**Guide (§3 Exits):** just before the next results date. Differs: the sale comes on, not "
        "before, the filing date (see Caveats).",
        "Drift window. After {HOLD_SESSIONS} sessions, counted in the benchmark's trading sessions rather "
        "than the stock's own, so a halted or thin stock cannot stretch its holding period.\n\n"
        "**Guide (§3 Exits):** the same.",
        "No target, and no rank exit. The thesis is a drift over weeks, so the clock is the exit. The "
        "guide's rank exit — sell if the next quarter's growth falls out of the top two-fifths — is not "
        "implemented. A position open when the backtest ends is valued at its last close.",
    ),
    "caveats": (
        "**THE UNIVERSE IS SELECTED ON OUTCOME, and this is the most serious defect in any result here.** "
        "Filings exist only for companies the `financials` job fetched, and that job's list is the most "
        "liquid names BY TODAY'S TURNOVER plus EVERY STOCK PASSING THE TREND TEMPLATE IN THE LATEST "
        "SNAPSHOT -- that is, every stock currently in an uptrend. Both criteria are evaluated on today's "
        "data, so a backtest restricted to that set knows which stocks went on to trend. The size of the "
        "contamination is measurable: an equal-weight buy-and-hold of the Indian eligible universe returned "
        "31.49% a year from 2022 against the Nifty 500's 8.22%, a premium of +23.27 with no stock selection "
        "whatsoever. The US set is a wider slice over a longer window and its premium is +1.71, so the US "
        "result is far less affected -- which is the one to read.",
        "**In the US the event date can lag the news.** The stored date is the SEC filing of the quarter's "
        "figures, which comes on or after the results press release and, for a fourth quarter (the annual "
        "10-K), can come weeks after it. On those events the reaction span measures days after the market "
        "has already reacted, and the next-results exit sells after the next release's reaction. India's "
        "dates are the exchange filing, which is the announcement.",
        "**The next-results exit does not avoid the results gap.** It sells at the close of the filing day, "
        "so whenever the results come out before that close the position holds through their reaction. "
        "The guide's intent is to sell before.",
        "**The 'R' figures in this strategy's reports are returns, not risk multiples.** A trade's R is its "
        "profit divided by the amount invested (0.05 = 5%), because positions are sized as a share of the "
        "account, not from the stop.",
        "**India's sample is too short and too narrow to conclude anything.** Filing dates begin in 2021, "
        "giving 4.8 years, 387 symbols and 203 trades, in a single strong mid-cap regime.",
        "**Low win rate with positive skew means the confidence interval is wide.** Under 30% of trades "
        "make money in both markets, so the result rests on the few largest drifts. Anything built on this "
        "should be judged on many more events than are available here.",
        "**Restatements are deliberately ignored.** Year-ago figures come from what was published a year "
        "ago, not from the current filing's restated comparative. The two disagree on 3.8% of US pairs "
        "(2,671 of 70,596); the originally published number is the one a trader had, and it is the only one "
        "India stores at all.",
        "**Analyst estimates exist but are not usable here.** The fetch keeps four quarters of consensus and "
        "surprise per company, which is enough for a live view and nowhere near enough for a backtest, so "
        "surprise is measured from the company's own history instead -- as the guide specifies.",
    ),
}


class PeadStrategy(PortfolioStrategy):
    """Post-earnings announcement drift, as the Learn guide states it.

    Registered despite failing, because this is the only EVENT-DRIVEN mechanism measured here and a
    negative result on the oldest documented anomaly in the list is worth keeping visible.
    """

    key = PEAD_DOC["key"]
    doc = PEAD_DOC
    family = "pead"
    version = "1.3"
    changelog = (
        ("1.3", "2026-10-29",
         "The price floor on the buy day reads the price traded then. The US $10 price floor reads the price the stock traded at that day: the stored close multiplied back by every later split Yahoo records (backtesting/spec.traded_close, the RS rating's fix in 1d16854). Stored closes are back-adjusted for every later split, so the floor had dropped the later multi-baggers from their early years -- NFLX's October 2009 close is stored as $0.72 against the ~$50 it traded at, NVDA read under $10 until mid-2020. On 2016-06-30 the US floor admits 2,092 stocks instead of 2,382: 47 that later split (NVDA, CMG, ANET, CPRT ...) come in, 337 that later reverse-split, and so really traded under $10, go out. India has no price floor and is unchanged."),
        ("1.2", "2026-10-26",
         "The reaction window reads total return: the stock's move over the first sessions after a "
         "filing is measured on closes back-adjusted for credited special dividends and demergers "
         "(corporate_actions.back_adjust), so an ex-date inside the window is not taken for the market's "
         "verdict on the results. Fills, the stop and turnover still read traded prices."),
        ("1.1", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited (marketdata/corporate_actions.py). On the ex-date a held position receives the cash, where the stored close only falls by it -- AURUM's 98% special dividend on 2020-12-23 was booked as a -98% loss, about 10% of the India vol-scaled book. Ordinary dividends stay out of strategy and benchmark. Stored prices were also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py correct)."),
        ("1.0", "2026-10-18",
                  "First version. Validated against the guide's worked example before being measured: "
                  "Polycab's June 2023 quarter reads +81.69% year on year against the guide's +81.7%, "
                  "the March quarter +30.56% against +30.6%, and the acceleration +51.13 points against "
                  "+51. Surprise is computed from a self-join to the company's own year-ago filing rather "
                  "than from net_income_prior, which India stores as 100% NULL and which disagrees with "
                  "the self-join on 3.8% of US pairs because it carries restatements."),)
    name = PEAD_DOC["name"]
    description = PEAD_DOC["description"]
    status = PEAD_DOC["status"]
    thesis = PEAD_DOC["thesis"]
    how_it_works = tuple(PEAD_DOC["how_it_works"])
    caveats = tuple(PEAD_DOC["caveats"]) + (corporate_actions.CAVEAT_HELD,)
    entry_rules = tuple(PEAD_DOC["entry_rules"])
    exit_rules = tuple(PEAD_DOC["exit_rules"])

    behaviour = "event_driven"
    #: Ranked against the other companies reporting the same season, so cross-sectional -- but the
    #: pool is one season's filings rather than the whole tape on a date.
    selection = "cross_sectional"
    style = "breakout"
    runner = "pead"

    hold_sessions = HOLD_SESSIONS
    max_positions = MAX_POSITIONS
    position_pct = POSITION_PCT
    min_yoy = MIN_YOY_GROWTH
    season_top = SEASON_RANK_TOP
    cost_bps = 10.0
    #: US only for the headline: India's filing dates start in 2021 and its universe premium is
    #: +23 points, so the India run is published as a diagnostic rather than as a result.

    param_docs = (
        ("Holding period", "hold_sessions", "Market sessions held before the time exit."),
        ("Positions", "max_positions", "Concurrent holdings; the guide suggests 10-20."),
        ("Position size", "position_pct", "Percent of the book per holding, at most 10%."),
        ("Minimum growth", "min_yoy", "Year-on-year net profit growth required."),
        ("Season rank", "season_top", "Growth must be in this top percent of the season so far."),
        ("Cost per side", "cost_bps", "Basis points per side."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Post-earnings announcement drift")
    ap.add_argument("--strategy", default="pead")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--hold-sessions", type=int, default=PeadStrategy.hold_sessions,
                    help="drift window: market sessions a position is held before the time exit")
    ap.add_argument("--max-positions", type=int, default=PeadStrategy.max_positions,
                    help="most positions held at once, one per company")
    ap.add_argument("--position-pct", type=float, default=PeadStrategy.position_pct,
                    help="percent of the account (cash plus positions) spent on each buy")
    ap.add_argument("--min-yoy", type=float, default=PeadStrategy.min_yoy,
                    help="minimum net-profit growth, %% over the same quarter a year earlier")
    ap.add_argument("--season-top", type=float, default=PeadStrategy.season_top,
                    help="growth must rank in this top %% of the filings for the same quarter so far")
    ap.add_argument("--cost-bps", type=float, default=PeadStrategy.cost_bps,
                    help="cost per side, basis points of the amount traded")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    tdf, eq, held, csh, costs, dropped, days = run(
        a.market, a.start, hold_sessions=a.hold_sessions, max_positions=a.max_positions,
        position_pct=a.position_pct, min_yoy=a.min_yoy, season_top=a.season_top,
        cost_bps=a.cost_bps)

    braw = cache.load_cached(a.market, cfg.benchmark_ticker)
    bc = braw["close"].astype(float).reindex(eq.index).ffill() if braw is not None else None

    # The universe control, computed and REPORTED rather than left to the reader: this strategy's
    # eligible set is selected on today's liquidity and today's trend, so the benchmark it should
    # be judged against is a buy-and-hold of that set, not the broad index. See the caveats.
    ev = load_events(a.market)
    uni = sorted(ev["symbol"].unique())
    cols = {}
    for s in uni:
        d = cache.load_cached(a.market, s)
        if d is not None and len(d) > 60:
            cols[s] = d["close"].astype(float)
    upx = pd.DataFrame(cols).sort_index().ffill().loc[eq.index[0]:eq.index[-1]]
    yrs = max((upx.index[-1] - upx.index[0]).days / 365.25, 1e-9)
    firsts = upx.apply(lambda c: c.dropna().iloc[0] if c.notna().any() else float("nan"))
    basket = upx.div(firsts, axis=1).mean(axis=1)
    uni_cagr = ((basket.iloc[-1] / basket.iloc[0]) ** (1 / yrs) - 1) * 100

    notes = [
        f"{len(ev):,} filings for {len(uni)} companies; {days:,} sessions produced at least one entry. "
        f"Dropped: {dropped['filters']:,} failed the fundamental filters, {dropped['reaction']:,} the price "
        f"reaction, {dropped['liquidity']:,} the price/turnover floors, {dropped['no_bar']:,} had no usable bar.",
        f"UNIVERSE CONTROL: an equal-weight buy-and-hold of these {len(uni)} companies returned "
        f"{uni_cagr:.2f}% a year over the same dates. That is the honest comparison -- the filing universe is "
        "the most liquid names by TODAY'S turnover plus every stock currently passing the Trend Template, so "
        "it is selected on outcome and a broad-index benchmark flatters this strategy.",
        "The event is the FILING date from the company's own results, and year-ago figures come from its "
        "filing a year earlier rather than from the current filing's restated comparative.",
        "The season rank is an expanding window within the season: a company's rank against the FULL season "
        "is not knowable on the day it reports.",
        f"Costs: {a.cost_bps:g}bps per side. Ordinary dividends are excluded on both the strategy and the benchmark; "
        "special dividends and demergers are credited to a holder.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf,
                           max_open_positions=a.max_positions, costs_paid=costs,
                           bench_close=bc, cash=csh, notes=notes)
    if bc is not None:
        for k, v in metrics.benchmark_stats(bc).items():
            setattr(perf, k, v)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"

    name = (f"{a.start}_hold{a.hold_sessions}_top{a.max_positions}x{a.position_pct:g}pct"
            f"_yoy{a.min_yoy:g}_season{a.season_top:g}_{a.cost_bps:g}bps_{PeadStrategy.spec_id()}")
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, a.max_positions))
    print(f"\nUNIVERSE CONTROL: equal-weight buy-and-hold of the {len(uni)} eligible companies "
          f"= {uni_cagr:.2f}% CAGR vs this strategy's {perf.cagr_pct:.2f}%")
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — post-earnings drift, {a.start} onward",
            perf, eq, held, tdf, cfg.currency_symbol, a.max_positions, bc,
            f"python3 -m swing_screener.backtesting.pead --market {a.market} --start {a.start}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
