"""Short-horizon mean reversion on INDEX series — RSI(2), Bollinger, Double 7s.

The first mechanism in this repository that is not momentum. Everything measured so far buys
strength and holds it; this buys a few days of selling inside a longer uptrend and holds for days.
That makes it worth measuring even if it loses: an uncorrelated loser is more informative than a
correlated one, and `research/selection-vs-drag.md` has nothing in this family to compare against.

WHY INDICES AND NOT STOCKS. The Learn guide is explicit, and the reason is structural: an index
cannot fall apart on one company's news, so its dips are market-wide selling that tends to
reverse, while a single stock's dip can be a permanent repricing. Connors tested it on indices.
Running it per-stock would be testing a different claim than the one the literature makes.

The published basis is short-term reversal -- Jegadeesh (1990) and Lehmann (1990) found that what
fell over a week tended to rebound, and Nagel (2012) reads the rebound as payment for supplying
liquidity when many people sell at once. The trend filter is what separates a pause from a
decline.

THREE VARIANTS, ONE MECHANISM. They differ only in how "oversold" is measured -- RSI(2) below a
threshold, a close below the lower Bollinger band, or a close at a 7-day low. Sharing the engine
means the comparison is of the measure and nothing else; three modules would have made any
difference between them partly an implementation difference.

IN CASH WHEN FLAT, deliberately. This is a timing strategy and the guide sizes it at 20-50% of
capital per signal with no leverage, so cash is the faithful reading. It will therefore show a
large DRAG and a small headline; the number to read is SELECTION (the index held at this
strategy's own exposure), which is what the decomposition in metrics.deployment_stats exists for.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from ..strategies.base import PortfolioStrategy
from . import metrics

logger = logging.getLogger("backtest")

MIN_BARS = 300

# ---- the measure of "oversold" (guide §3 and §5)
RSI_LENGTH = 2              # Connors shortened the usual 14 to 2
RSI_ENTRY = 5.0             # below this is "three or more lower closes, the last ones large"
RSI_EXIT = 70.0             # alternative target
BB_LENGTH = 20              # Bollinger middle band
BB_SD = 2.0                 # bands at this many standard deviations
LOW_DAYS = 7                # Double 7s: a close at a 7-day low, out at a 7-day high

# ---- the trend filter, the exit and the time stop
TREND_SMA = 200             # only buy above this average
EXIT_SMA = 5                # sell on the first close above this average
MAX_HOLD = 10               # sessions, if nothing else has happened
CATASTROPHE = True          # also sell on a close back below the trend average

MEASURES = ("rsi2", "bollinger", "double7")
RANKS = ("rsi", "vol")            # which firing series is bought first when slots are short
TRENDS = ("above200", "off")      # whether a signal needs the close above the 200-day
VOL_RANK_BARS = 20                # realized volatility window for rank="vol"


def wilder_rsi(close: pd.Series, length: int = RSI_LENGTH) -> pd.Series:
    """RSI by Wilder's smoothing, which is what the guide specifies.

    Wilder's average is an EMA with alpha = 1/length, NOT a simple mean of the last `length`
    moves; at length 2 the two differ enough to move the signal count materially, so the method
    is part of the rule rather than an implementation detail.
    """
    d = close.diff()
    up = d.clip(lower=0.0)
    down = (-d).clip(lower=0.0)
    au = up.ewm(alpha=1 / length, adjust=False).mean()
    ad = down.ewm(alpha=1 / length, adjust=False).mean()
    rs = au / ad.replace(0.0, pd.NA)
    out = 100 - 100 / (1 + rs)
    return out.where(ad != 0, 100.0)          # no down-moves at all is RSI 100, not NaN


def load_indices(market: str) -> dict:
    """{label: close} for every broad and sector index this market has stored.

    Both families, because the guide's universe is "index ETFs or index futures (Nifty 50, Nifty
    Bank, S&P 500, Nasdaq 100)" -- Nifty Bank is a sector series here, so restricting to the broad
    map would drop half the named universe.
    """
    cfg = MARKETS[market]
    out = {}
    for label, tkr in {**(cfg.broad_index_symbols or {}),
                       **{k: v for k, v in (cfg.sector_index_map or {}).items()}}.items():
        d = cache.load_cached(market, tkr)
        if d is None or len(d) < MIN_BARS:
            continue
        out[f"{label} ({tkr})"] = d["close"].astype(float).sort_index()
    if not out:
        raise ValueError(f"no usable index series for {market}")
    return out


def oversold_signals(close: pd.Series, measure: str, rsi_entry: float = RSI_ENTRY,
                     trend: str = "above200") -> tuple:
    """(entry mask, exit mask) for one series -- the only thing the three variants disagree on.

    trend="off" drops the 200-day filter AND the catastrophe exit together: below the 200-day the
    catastrophe exit would fire on the first bar, so keeping it would quietly reinstate the filter.
    Measured on US index series since 2000, the filter does the opposite of its purpose in bear
    years -- early in a decline the index is still above its 200-day, so it keeps the first dips
    of a top (2008: -2.06% a trade, 2022: -1.13%) and discards the capitulation dips below it
    (+1.34%, +0.63%).
    """
    if trend not in TRENDS:
        raise ValueError(f"unknown trend '{trend}', choose from {TRENDS}")
    sma_trend = close.rolling(TREND_SMA).mean()
    sma_exit = close.rolling(EXIT_SMA).mean()
    uptrend = (close > sma_trend) if trend == "above200" else pd.Series(True, index=close.index)

    if measure == "rsi2":
        r = wilder_rsi(close, RSI_LENGTH)
        entry = uptrend & (r < rsi_entry)
        exit_ = (close > sma_exit) | (r > RSI_EXIT)
    elif measure == "bollinger":
        mid = close.rolling(BB_LENGTH).mean()
        sd = close.rolling(BB_LENGTH).std()
        entry = uptrend & (close < mid - BB_SD * sd)
        exit_ = close > mid                      # the band's middle, not the 5-day
    elif measure == "double7":
        entry = uptrend & (close <= close.rolling(LOW_DAYS).min())
        exit_ = close >= close.rolling(LOW_DAYS).max()
    else:
        raise ValueError(f"unknown measure '{measure}', choose from {MEASURES}")

    if CATASTROPHE and trend == "above200":
        exit_ = exit_ | (close < sma_trend)
    return entry.fillna(False), exit_.fillna(False)


def run(market: str, start: str, measure: str = "rsi2", rsi_entry: float = RSI_ENTRY,
        position_pct: float = 25.0, max_positions: int = 2, cost_bps: float = 10.0,
        max_hold: int = MAX_HOLD, preloaded: dict | None = None,
        rank: str = "rsi", trend: str = "above200"):
    """Event-driven, not calendar-driven: a signal can fire on any session.

    Neither existing engine fits, and bending one would have cost more than the 60 lines here.
    `portfolio_sim` is built around a TradePlan with a trigger, a stop and a target, and this
    trade has none of the three -- it buys at the close on the signal bar and leaves on a moving
    average or a clock. `rotation.simulate` only acts on rebalance dates, which would delay every
    entry by up to a month and destroy a trade whose median hold is a few days.
    """
    cfg = MARKETS[market]
    series = preloaded if preloaded is not None else load_indices(market)
    start_ts = pd.Timestamp(start)

    if rank not in RANKS:
        raise ValueError(f"unknown rank '{rank}', choose from {RANKS}")
    sigs = {name: oversold_signals(c, measure, rsi_entry, trend) for name, c in series.items()}
    rsi = {name: wilder_rsi(c) for name, c in series.items()} if measure == "rsi2" else {}
    # point-in-time realized volatility, for rank="vol" (data up to and including the signal close)
    vol = {name: c.pct_change().rolling(VOL_RANK_BARS).std() for name, c in series.items()}
    dates = sorted({d for c in series.values() for d in c.index if d >= start_ts})

    cash = float(cfg.account_size)
    open_pos: dict[str, dict] = {}
    trades, equity, cash_log, held_log, costs_total = [], [], [], [], 0.0

    def mark(name, d):
        c = series[name]
        hit = c.loc[:d]
        return float(hit.iloc[-1]) if len(hit) else float("nan")

    for d in dates:
        # ---- exits first, so capital freed today can be redeployed today
        for name in list(open_pos):
            pos = open_pos[name]
            entry_mask, exit_mask = sigs[name]
            if d not in series[name].index:
                continue
            pos["bars"] += 1
            leave = bool(exit_mask.get(d, False)) or pos["bars"] >= max_hold
            if not leave:
                continue
            price = mark(name, d)
            gross = pos["units"] * price
            fee = gross * cost_bps / 10_000
            cash += gross - fee
            costs_total += fee
            trades.append({
                "symbol": name, "entry_date": pos["date"], "entry_price": round(pos["price"], 4),
                "exit_date": d, "exit_price": round(price, 4), "shares": round(pos["units"], 4),
                "exit_reason": "TIME_STOP" if pos["bars"] >= max_hold else "MEAN_REVERTED",
                "pnl": round(gross - fee - pos["cost"], 2), "notional": round(pos["cost"], 2),
                "costs": round(fee + pos["fee"], 2), "holding_days": (d - pos["date"]).days,
                "r_multiple": round((gross - fee) / pos["cost"] - 1, 4),
            })
            del open_pos[name]

        # ---- entries: when several fire together, which is bought first.
        # rank="rsi" (the shipped rule) takes the most oversold. But RSI(2) counts consecutive down
        # closes, not how hard a series will rebound: defensive sectors drift down in small steps,
        # reach extreme readings easily and bounce least, so the US run held XLU (-0.09% a trade
        # since 2000) 50 times and QQQ (+1.18%) 32. rank="vol" takes the most volatile series by
        # its own trailing volatility, a point-in-time stand-in for beta.
        if len(open_pos) < max_positions:
            firing = [n for n, (e, _) in sigs.items()
                      if n not in open_pos and d in series[n].index and bool(e.get(d, False))]
            if rank == "vol":
                firing.sort(key=lambda n: -float(vol[n].get(d, 0.0) or 0.0))
            else:
                firing.sort(key=lambda n: float(rsi[n].get(d, 50.0)) if rsi else 0.0)
            for name in firing[: max_positions - len(open_pos)]:
                price = mark(name, d)
                if price != price or price <= 0:
                    continue
                book = cash + sum(p["units"] * mark(n, d) for n, p in open_pos.items())
                spend = min(book * position_pct / 100, cash)
                if spend <= 0:
                    continue
                fee = spend * cost_bps / 10_000
                units = (spend - fee) / price
                cash -= spend
                costs_total += fee
                open_pos[name] = {"units": units, "price": price, "date": d,
                                  "cost": spend - fee, "fee": fee, "bars": 0}

        # Record equity, CASH and position count on the same pass. The cash series is not
        # bookkeeping: `metrics.deployment_stats` needs it to split the headline into selection
        # and drag, and for a strategy that is flat most of the time the drag term is the whole
        # story. Reconstructing it afterwards would mean re-deriving the loop's own state.
        equity.append((d, cash + sum(p["units"] * mark(n, d) for n, p in open_pos.items())))
        cash_log.append((d, cash))
        held_log.append((d, len(open_pos)))

    eq = pd.Series(dict(equity)).sort_index()
    cash_series = pd.Series(dict(cash_log)).sort_index()
    held = pd.Series(dict(held_log)).sort_index()
    return pd.DataFrame(trades), eq, held, cash_series, costs_total, series


MR_DOC = {
    "key": "mean_reversion",
    "name": "Index mean reversion (RSI 2)",
    "description": "Buy a broad or sector index when its 2-day RSI closes below "
                   "{RSI_ENTRY} while it is above its {TREND_SMA}-day average; sell on the first close "
                   "above the {EXIT_SMA}-day average, or after {MAX_HOLD} sessions.",
    "status": (
        "OPTIMISE STAGE (2013-2021), 1.1: still fails, and neither new option rescues it. Baseline "
        "selection -1.12 in the US (CAGR 0.50%, 10% invested, max drawdown -8.7%); per trade "
        "+0.27% in India and +0.17% in the US. RANK VOL changes almost nothing (US selection -1.04, "
        "+0.18% a trade): the ranking only acts when more series fire than there are slots, which "
        "is rare. TREND OFF is worse -- US selection -1.76 and drawdown -27.0% -- because the "
        "capitulation dips it admits paid in 2008 and 2022, and both fall outside this window; "
        "inside it the bear phases (2015-16, late 2018) lost below the 200-day. Both together: US "
        "-1.26, drawdown -20.7%. India agrees, re-run on corrected prices: baseline selection -1.51 "
        "(+0.27% a trade), rank vol -1.47, trend off -2.09 with drawdown -24.3%, both -1.55. The first "
        "India trend-off runs reported +14% CAGR from one +902.6% trade on two PSUBNKBEES.NS bars stored "
        "at a tenth of their price (2019-12-19/20); those bars are corrected in stored prices and the "
        "runs replaced. Not every ETF series is tradable at this size: CONSUMBEES.NS traded 2-2,223 units "
        "a day in 2015, so its largest trade here (+17.8%, 2015-04-30) is a print no 25% position could "
        "have filled -- there is no liquidity check on the series. "
        "Both options came from a study over 2000-2026 data, so the verify window is "
        "already in-sample for them and a verify run would not be a clean test.\n\n"
        "LEGACY (before stages, mixed windows -- reference only): "
        "MEASURED AND IT FAILS, in both markets and in every variant tried -- and it is the first "
        "NON-MOMENTUM mechanism in this repository, which is why it is kept rather than deleted. "
        "India from 2010: CAGR 0.16% against the Nifty 500's 10.17%. US from 2010: 0.58% against "
        "SPY's 12.04%. Those headlines are mostly cash, so read SELECTION instead -- the index held "
        "at this strategy's own exposure -- and it is NEGATIVE in both: -1.30 India, -1.10 US, at "
        "8.1% and 9.7% invested. The signal does not pick; it is not merely under-deployed. "
        "The WIN RATE IS THE TRAP, and it is why this rule is popular: 62.8% of 403 Indian trades "
        "and 66.3% of 508 US trades made money, median hold 4 sessions, average +0.13% and +0.20% "
        "gross per trade. A rule can win two trades in three and still lose to doing nothing when "
        "the wins are a fifth of a percent and the rare loss is not stopped. "
        "ALL THREE MEASURES FAIL, so this is the mechanism and not one indicator: across 12 runs "
        "(3 measures x 2 position caps x 2 markets) selection is negative in all 12. Best was "
        "RSI(2) holding one position at a time (-1.02 India, -0.93 US); worst was Double 7s holding "
        "three (-3.75, -5.16), which is also the variant that stays invested longest -- more "
        "exposure to a signal with no edge simply loses more. "
        "The 2020 window does not rescue it: -1.16 India and -1.63 US, so unlike every momentum "
        "strategy here this one is not a window artefact. It is just flat. "
        "What this measures honestly is the SHORT-TERM REVERSAL premium net of costs on tradable "
        "index series, which is a real published effect (Jegadeesh 1990, Lehmann 1990) that at "
        "{cost_bps}bps a side and a 4-day hold does not survive contact with execution."
    ),
    "thesis": "When many holders sell at once, whoever buys from them is paid a small premium for "
              "supplying liquidity (Nagel 2012). A few sharp down days inside a longer uptrend are "
              "more often that kind of selling than the start of a decline, and what fell over a "
              "week has tended to rebound (Jegadeesh 1990, Lehmann 1990). The trend filter is what "
              "separates a pause from a repricing. The short hold is what keeps it a liquidity trade "
              "rather than a bet on direction.",
    "how_it_works": (
        "The idea. Buy an index after a few days of sharp selling inside an uptrend, and sell as "
        "soon as it bounces — usually within days.",
        "Steps, each session, in order: check open positions for an exit and sell at the close "
        "(see Exit); then buy new signals at that same close (see Entry). Money freed by a sale "
        "can buy a new signal at the same close.",
        "Three measures of oversold, chosen with `measure` (default {measure}): RSI(2), Bollinger "
        "and Double 7s. Everything else is shared — trend filter, sizing, trend exit, time limit — "
        "so comparing them compares the indicator and nothing else.",
        "Flat most of the time, holding cash that earns nothing.",
        "Where the rules come from. Connors' RSI(2) rule as the Learn guide states it, on index "
        "series because that is where the effect was published. There is no written spec with row "
        "ids for this strategy.",
    ),
    "entry_rules": (
        "Universe. Index series only: every broad and sector series in the market's config with at "
        "least {MIN_BARS} stored sessions.\n\n"
        "- **US:** funds — SPY, QQQ, IWM and the sector SPDR funds.\n"
        "- **India:** the Nifty 50, Nifty 500, Midcap 150 and Smallcap 250 and the Bank, IT and "
        "Pharma indices, plus a sector ETF where the config has no sector index.\n"
        "- **Why not stocks:** an index cannot fall apart on one company's news, so its dips are "
        "market-wide selling that tends to reverse; a single stock's dip can be a permanent "
        "repricing.",
        "Buy signal. On a session's close, the close above its {TREND_SMA}-day simple average AND "
        "the chosen measure says oversold.\n\n"
        "- **RSI(2), the default:** Wilder's RSI over {RSI_LENGTH} closes below {rsi_entry}. The "
        "average up-move and average down-move are each smoothed with a weight of 1/{RSI_LENGTH} on "
        "the newest move, and RSI = 100 − 100 / (1 + average up ÷ average down); it reads 100 when "
        "there were no down-moves. Below {rsi_entry} usually takes several lower closes in a row, "
        "the last ones large.\n"
        "- **Bollinger:** the close below the lower band — the {BB_LENGTH}-day simple average minus "
        "{BB_SD} times the standard deviation of the same {BB_LENGTH} closes.\n"
        "- **Double 7s:** the close is the lowest close of the last {LOW_DAYS} sessions, that day "
        "included (a tie counts).",
        "Fill. Bought at that same session's close — the close the signal was computed on. There is "
        "no next-open fill, no trigger and no limit price.",
        "Position size. Each buy spends {position_pct}% of the book (cash plus open positions at "
        "that close), or all the remaining cash if less is left. The cost comes out of that amount.",
        "How many at once. At most {max_positions} positions, one per index. When more indices "
        "signal than there are free places, RSI(2) buys the lowest RSI first; Bollinger and Double "
        "7s take them in the config's order (broad indices, then sectors).",
        "Stop. None. Connors tested stops and reported that they reduced returns. The price of "
        "leaving them out is a rare large loss: a position is held through any fall until one of "
        "the exits fires.",
        "Cost. {cost_bps} basis points of the value traded, on each buy and each sell. On a trade "
        "averaging +0.13% gross that is comparable to the whole edge.",
        "When no trade is taken. No signal, every place full, or the index already held. An index "
        "sold at a session's close can be bought again at that same close if it signals again.",
    ),
    "exit_rules": (
        "Exits are checked on each close of that index from the session after the buy, and sell "
        "the whole position at that close. The first that applies acts.",
        "Mean reverted — the bounce the trade was waiting for. Most trades end here.\n\n"
        "- **RSI(2):** the close above the simple average of the last {EXIT_SMA} closes (that day "
        "included), or the {RSI_LENGTH}-day RSI above {RSI_EXIT}.\n"
        "- **Bollinger:** the close above the middle band, the {BB_LENGTH}-day simple average. This "
        "measure has no {EXIT_SMA}-day exit.\n"
        "- **Double 7s:** the close is the highest close of the last {LOW_DAYS} sessions, that day "
        "included.",
        "Trend broken, all three measures. The close below its {TREND_SMA}-day average: the filter "
        "that justified the trade has failed.",
        "Time limit. Sold at the close of the {max_hold}th session after the buy, counted in that "
        "index's own sessions, whatever else has happened. The measured median hold is 4 sessions, "
        "so the clock rarely binds.",
        "Target. No fixed price. The mean-reversion exits above are the target, and each is decided "
        "on a close.",
    ),
    "caveats": (
        "**The win rate invites over-confidence.** Two trades in three make money and the strategy "
        "still loses to doing nothing. Any variant of this rule should be judged on average return "
        "per trade against costs, never on hit rate.",
        "**No stop means the loss distribution has a tail this backtest may understate.** The rule "
        "exits on a close above an average or on a clock, so a fast decline is held for up to "
        "{max_hold} sessions. February 2020 is the archetype: still above the {TREND_SMA}-day "
        "average, signals firing, and the fall continuing.",
        "**Not every series is a tradable instrument, and none includes dividends.** The US series "
        "are funds and trade; India's broad and main sector series are index values, which cannot "
        "be bought directly. A real book buys an ETF or a future, adding tracking difference, "
        "bid-ask and (for futures) roll and margin. None of that is modelled, so the result is "
        "optimistic by an unquantified amount on top of the {cost_bps} basis points charged.",
        "**Sector indices are included, and that is a judgement call.** The guide's named universe "
        "includes Nifty Bank, which is a sector series, so restricting to broad indices would drop "
        "half of it. Sector indices are less diversified, so the 'cannot fall apart on one "
        "company's news' argument is weaker for them than for the broad ones.",
        "**Survivorship does not apply.** These are index series, which are maintained rather than "
        "selected, so this is one of the few results here with no survivorship discount.",
    ),
}


class MeanReversionStrategy(PortfolioStrategy):
    """Connors' RSI(2) rule on index series, as the Learn guide states it.

    The default `measure` is RSI(2) because that is the published rule. Bollinger and Double 7s
    are selectable and were measured (see `status`); they are variants of the same mechanism, not
    separate strategies, and giving each its own key would have implied three independent results
    where there is one.
    """

    key = MR_DOC["key"]
    doc = MR_DOC
    family = "mean_reversion"
    version = "1.1"
    changelog = (("1.1", "2026-10-24",
                  "Two options, both off by default so the shipped run is unchanged. `rank vol` buys the "
                  "most volatile firing series first instead of the most oversold: RSI(2) depth counts "
                  "down closes rather than predicting the rebound, and the US run held its worst series "
                  "most (XLU -0.09% a trade since 2000, 50 times; QQQ +1.18%, 32), with high-beta series "
                  "beating low-beta ones in both halves of 2000-2026. `trend off` drops the 200-day filter "
                  "and the catastrophe exit together: in 2008 and 2022 the trades it kept lost (-2.06%, "
                  "-1.13%) and the ones it discarded won (+1.34%, +0.63%). Indian index series show no "
                  "edge in any regime once two corrupt PSUBNKBEES.NS bars are masked."),
                 ("1.0", "2026-10-18",
                  "First version: Connors' RSI(2) with the 200-day trend filter, the 5-day exit and a "
                  "10-session time stop, on every stored broad and sector index. Validated against the "
                  "guide's own worked example before being measured -- RSI(2) 4.1 on the Nifty 50 on "
                  "2024-05-30 and 4.6 on 2026-01-08, signal frequency 9.1/yr on the Nifty 50 and 5.9/yr "
                  "on SPY against the guide's stated 6-9, and the May 2024 trade reproduced to the "
                  "paisa (22,488.65 -> 23,263.90)."),)
    name = MR_DOC["name"]
    description = MR_DOC["description"]
    status = MR_DOC["status"]
    thesis = MR_DOC["thesis"]
    how_it_works = tuple(MR_DOC["how_it_works"])
    caveats = tuple(MR_DOC["caveats"])
    entry_rules = tuple(MR_DOC["entry_rules"])
    exit_rules = tuple(MR_DOC["exit_rules"])

    behaviour = "mean_reversion"
    #: Judged against its OWN history (is this index oversold relative to itself), never ranked
    #: against peers -- several indices can signal on the same day and none is compared to another.
    selection = "time_series"
    #: `pullback` from the existing taxonomy rather than a new "reversion" style: the guide's own
    #: subtitle is "buying short, sharp dips in an uptrend", which is what pullback already means
    #: here. A new style would be a UI vocabulary change for one strategy.
    style = "pullback"
    runner = "mean_reversion"         # the module whose main() backtests it

    # tunables -- these ARE the strategy
    measure = "rsi2"
    rsi_entry = RSI_ENTRY
    position_pct = 25.0
    max_positions = 2
    max_hold = MAX_HOLD
    cost_bps = 10.0
    rank = "rsi"
    trend = "above200"

    param_docs = (
        ("Oversold measure", "measure", "rsi2 | bollinger | double7. All three were measured and all "
                                        "three have negative selection; see the status."),
        ("RSI entry", "rsi_entry", "The 2-day RSI must close below this. 10 roughly doubles the signals."),
        ("Position size", "position_pct", "Percent of the book committed per signal."),
        ("Concurrent positions", "max_positions", "How many index positions may be open at once."),
        ("Maximum hold", "max_hold", "Sessions before the time stop sells regardless."),
        ("Cost per side", "cost_bps", "Basis points per side. Comparable to the whole edge -- see the caveats."),
        ("Ranking", "rank", "rsi | vol. Which firing series is bought first when slots are short: the most "
                            "oversold (shipped) or the most volatile, a point-in-time stand-in for beta."),
        ("Trend filter", "trend", "above200 | off. Off drops the 200-day entry filter and the catastrophe "
                                  "exit together, so signals below the 200-day count."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Short-horizon mean reversion on index series")
    ap.add_argument("--strategy", default="mean_reversion")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--measure", default=MeanReversionStrategy.measure, choices=list(MEASURES))
    ap.add_argument("--rsi-entry", type=float, default=MeanReversionStrategy.rsi_entry)
    ap.add_argument("--position-pct", type=float, default=MeanReversionStrategy.position_pct)
    ap.add_argument("--max-positions", type=int, default=MeanReversionStrategy.max_positions)
    ap.add_argument("--max-hold", type=int, default=MeanReversionStrategy.max_hold)
    ap.add_argument("--cost-bps", type=float, default=MeanReversionStrategy.cost_bps)
    ap.add_argument("--rank", default=MeanReversionStrategy.rank, choices=list(RANKS))
    ap.add_argument("--trend", default=MeanReversionStrategy.trend, choices=list(TRENDS))
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    tdf, eq, held, csh, costs, series = run(
        a.market, a.start, measure=a.measure, rsi_entry=a.rsi_entry,
        position_pct=a.position_pct, max_positions=a.max_positions,
        cost_bps=a.cost_bps, max_hold=a.max_hold, rank=a.rank, trend=a.trend)

    b = cache.load_cached(a.market, cfg.benchmark_ticker)
    bc = b["close"].astype(float).reindex(eq.index).ffill() if b is not None else None
    notes = [
        f"A TIMING rule on {len(series)} index series, not a stock selection: there is no universe to "
        "pick from and no survivorship discount, because indices are maintained rather than selected.",
        (f"Measure '{a.measure}'; entry needs the close above its {TREND_SMA}-day average. Exit on the "
         f"first close above the {EXIT_SMA}-day average, RSI above {RSI_EXIT}, a close back below the "
         f"{TREND_SMA}-day average, or {a.max_hold} sessions." if a.trend == "above200" else
         f"Measure '{a.measure}' with NO trend filter: signals below the {TREND_SMA}-day count, and the "
         f"catastrophe exit is off with it. Exit on the first close above the {EXIT_SMA}-day average, "
         f"RSI above {RSI_EXIT}, or {a.max_hold} sessions."),
        ("When several series fire at once the most oversold is bought first." if a.rank == "rsi" else
         f"When several series fire at once the most volatile ({VOL_RANK_BARS}-day realized) is bought first."),
        f"{a.position_pct:g}% of the book per signal, at most {a.max_positions} at once, cash otherwise -- "
        "which is why the headline is small and the SELECTION line below is the one to read.",
        "Index series are PRICE series and not tradable instruments; a real book buys an ETF or a future, "
        f"adding tracking difference, spread and roll on top of the {a.cost_bps:g}bps charged here.",
        "No stop: a fast decline is held for up to the time stop. February 2020 is the archetype.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf,
                           max_open_positions=a.max_positions, costs_paid=costs,
                           bench_close=bc, cash=csh, notes=notes)
    if bc is not None:
        for k, v in metrics.benchmark_stats(bc).items():
            setattr(perf, k, v)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"

    variant = ("" if a.rank == "rsi" else f"_rank{a.rank}") + ("" if a.trend == "above200" else f"_trend{a.trend}")
    name = (f"{a.start}_{a.measure}_rsi{a.rsi_entry:g}_pos{a.max_positions}x{a.position_pct:g}pct"
            f"_{a.cost_bps:g}bps{variant}_{MeanReversionStrategy.spec_id()}")
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    # `cash` is written because the drag decomposition needs it and this strategy is flat ~90% of
    # the time: without the column the Backtests page can only show a headline that is mostly cash.
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, a.max_positions))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — index mean reversion ({a.measure}), {a.start} onward",
            perf, eq, held, tdf, cfg.currency_symbol, a.max_positions, bc,
            f"python3 -m swing_screener.backtesting.mean_reversion --market {a.market} --start {a.start}"
            + (f" --rank {a.rank}" if a.rank != "rsi" else "") + (f" --trend {a.trend}" if a.trend != "above200" else ""))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
