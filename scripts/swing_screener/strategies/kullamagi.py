"""Kullamägi's breakout — the fastest stocks, bought as they leave a tight rest.

Kristjan Kullamägi (Qullamaggie) trades "extreme momentum stocks. Once they pull back and get tight,
extremely tight, that's usually when volatility returns." This is the daily-bar version the Learn
guide (research/learn-strat-kullamagi.md, §3, §4 and the §8 method note) defines and measures:

  * the stock is fast and has just made a big move (the `big_movers` screen: ADR and prior move);
  * the last REST_BARS sessions are a tight rest that holds above the rising short averages;
  * the session closes above the rest's high: buy that close, stop at that session's low;
  * after PARTIAL_AFTER_BARS sessions in profit, sell a part and move the stop to the entry; the rest
    leaves on the first close below its TRAIL_SMA-day average, or after MAX_HOLD_BARS sessions.

His real entry is intraday (an opening-range breakout with the stop at that range's low). Daily bars
cannot see it, so this buys the close; the caveats say what that costs.

The exit is the backtest's `--exit-mode kullamagi` (backtesting/portfolio_sim.py), which reads this
module's exit constants through a default_factory, so a `--const` variant means what it says.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import indicators as ind
from ..core.context import StockContext
from ..marketdata import corporate_actions
from ..screens import criteria as crit
# the Big movers screen's thresholds, named here so the docs render them and the fingerprint covers them
from ..screens.criteria import (MOVERS_ADR_BARS, MOVERS_HIGH_BARS, MOVERS_LOW_BARS,  # noqa: F401
                                MOVERS_MIN_ADR_PCT, MOVERS_MIN_MOVE_PCT)
from .base import (
    tradable_point_in_time,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .rs_leaders import _market_of
from .trend_pullback import round_tick

# ---- the rest (the setup's structure; evaluate() reads these)
REST_BARS = 10                    # the sessions before the breakout that make up the rest
TIGHT_MAX_ADR = 3.0               # the rest's highest high to lowest low, % of the high, in ADRs (G3)
SUPPORT_FAST = 10                 # the rest surfs one of these rising averages (G4) …
SUPPORT_MID = 20
SUPPORT_SLOW = 50
REST_UNDERCUT_ADR = 0.5           # … no rest close more than this many ADRs below it
PRIOR_CLOSE_SMA = 10              # the session before the breakout closes above this average
REST_MAX_GIVEBACK_PCT = 50.0      # the rest's low gives back at most this % of the prior move (G7)

# ---- market (evaluate() reads these). The index is the first of MARKET_INDEX_LABELS that the
# market's config lists in broad_index_symbols (the Nasdaq-100 ETF, the Nifty 500), else its benchmark.
REQUIRE_MARKET = 1                # 1: G6 is a hard gate; 0: it always passes
MKT_EMA = 20                      # the index closes above its MKT_EMA-day exponential average …
MKT_FAST_EMA = 10                 # … and its MKT_FAST_EMA-day EMA is above that MKT_EMA-day one
MARKET_INDEX_LABELS = ("QQQ", "NIFTY500")

# ---- the stop (classify() reads these, after evaluate())
MAX_STOP_ADR = 1.0                # a stop further than this many ADRs below the entry is not bought
MIN_STOP_PCT = 1.0                # … nor one closer than this %
ENTRY_MIN_ADR_PCT = 0.0           # a buy needs at least this ADR, % (0: off; G1's screen floor still applies)
NOMINAL_TARGET_R = 10             # a far target for the plan's R column only; the backtest has no target

# ---- management (the backtest's `--exit-mode kullamagi` reads these)
PARTIAL_AFTER_BARS = 3            # at the close of this session after the entry, if above the entry …
PARTIAL_DIVISOR = 3               # … sell 1/PARTIAL_DIVISOR of the shares and move the stop to the entry
TRAIL_SMA = 10                    # the rest sells at the first close below the average of this length …
TRAIL_EMA = 0                     # … simple (0) or exponential (1)
MAX_HOLD_BARS = 120               # … or at the close of this session after the entry

S1 = "S1"   # today's close is above the rest's high


class KullamagiStrategy(Strategy):
    selection = "time_series"
    version = "1.4"
    # 1.4 adds an entry-time ADR floor read only by classify() (off by default), so it keeps 1.3's signal scan
    signal_version = "1.3"
    changelog = (
        ("1.4", "2026-11-10",
         "An optional entry floor on the average daily range, ENTRY_MIN_ADR_PCT, applied when the trade is "
         "decided rather than in the scan, so a variant reuses the cached signals. Off by default (0), so the "
         "rules are v1.3's. Added to test Kullamagi's advice that smaller accounts use a 5-6% ADR floor: in "
         "v1.3's US optimise run the trades with the widest stops, which track ADR, earned far more per trade."),
        ("1.3", "2026-11-07",
         "The rest is measured against the stock's own speed, as in the Kullamaggi model book. G3's span limit is "
         "now {TIGHT_MAX_ADR} ADRs instead of a fixed 20%, and G4 asks that the rest surf a rising {SUPPORT_FAST}-, "
         "{SUPPORT_MID}- or {SUPPORT_SLOW}-day average with no close more than {REST_UNDERCUT_ADR} ADR under it, "
         "instead of every low at 97% of the 20-day. Run over the book's 2019-2020 examples, v1.2 bought CVNA's June "
         "2020 breakout but blocked APPS, NVAX, ZM and CODX at their marked buys, on G3 (rests of 25-30% on stocks "
         "moving 10% a day) and G4 (one wick through the 20-day). The constants were set from those marked buys, "
         "which are winners only and sit inside the optimise window."),
        ("1.2", "2026-11-06",
         "An exit switch, off by default: TRAIL_EMA = 1 trails the remainder on an exponential average instead of a "
         "simple one. With the defaults the rules are exactly 1.1's. Added to test the EMA20 trail as a variant: "
         "replaying every trade of the v1.0 optimise runs, a close below the 20-day EMA instead of the 10-day SMA "
         "added R in all six runs (+12 to +64R a run), most of it from a few longer runners."),
        ("1.1", "2026-11-06",
         "Two entry rules from a loss audit of the v1.0 optimise runs (2013-2021, so chosen in-sample): the prior "
         "move must be at least {MOVERS_MIN_MOVE_PCT}% (was 30%, the Big movers screen's M2), and the rest must hold "
         "the upper part of that move, giving back at most {REST_MAX_GIVEBACK_PCT}% of it (new G7). Over the four "
         "audited runs and both base runs, the trades each rule removes had a negative total R in every run, at "
         "every giveback threshold from 40% to 70%; the canonical volume dry-up and range-contraction tests were "
         "checked the same way and did not help, so they are not added."),
        ("1.0", "2026-10-28",
         "v1: the Learn guide's daily-bar version. Big movers (ADR >= {MOVERS_MIN_ADR_PCT}%, prior move >= "
         "{MOVERS_MIN_MOVE_PCT}%), a {REST_BARS}-session rest within 20%, a close above its high bought "
         "at that close with the stop at the day's low; 1/{PARTIAL_DIVISOR} sold after {PARTIAL_AFTER_BARS} sessions in "
         "profit, the rest on a close below the {TRAIL_SMA}-day."),
    )
    key = "kullamagi"
    name = "Kullamägi breakout"
    description = (
        "Momentum breakouts: a stock that has just made a big, fast move rests in a tight range; buy the close "
        "above the range with the stop at that day's low."
    )
    style = "breakout"
    horizon = "swing"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
    screen_key = "big_movers"
    screen_gates = {"G1": "M1", "G2": "M2"}
    watch_codes = ()
    setup_codes = (S1,)
    setup_names = {S1: "Close above a tight rest"}
    gate_titles = {
        "G1": "Fast stock (ADR)", "G2": "Big prior move", "G3": "Tight rest",
        "G4": "Rest surfs a rising average", "G5": "Prior close above the {PRIOR_CLOSE_SMA}-day",
        "G6": "Market uptrend", "G7": "Rest holds the move",
    }
    nominal_target = True
    min_bars = 210

    needs_ctx_extras = True
    extra_columns = ("adr_pct", "prior_move_pct", "rest_high", "rest_low", "rest_span_pct", "rest_span_adr",
                     "support_sma", "giveback_pct", "stop_adr")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = (
        "MAX_STOP_ADR", "MIN_STOP_PCT", "ENTRY_MIN_ADR_PCT", "NOMINAL_TARGET_R",
        "PARTIAL_AFTER_BARS", "PARTIAL_DIVISOR", "TRAIL_SMA", "TRAIL_EMA", "MAX_HOLD_BARS",
    )

    thesis = (
        "The stocks that have just moved most, and that move several percent on an ordinary day, are the only ones "
        "that can return ten times a stop placed at the day's low. When such a stock rests in a tight range, its "
        "sellers are drying up; the close out of the range is the moment it sets off again, and a stop at that "
        "day's low makes being wrong cheap. The edge, if any, is in the rare large winner, paid for by many small "
        "losses."
    )
    how_it_works = (
        "**The idea.** Kullamägi: extreme momentum stocks that pull back and get tight, then break out. This is the "
        "daily-bar version of the Learn guide's rules.",
        "**Qualify (the Big movers screen).** An average daily range of {MOVERS_MIN_ADR_PCT}% or more (G1) and a "
        "big prior move: the {MOVERS_HIGH_BARS}-session high at least {MOVERS_MIN_MOVE_PCT}% above the "
        "{MOVERS_LOW_BARS}-session low (G2).",
        "**The rest.** The {REST_BARS} sessions before today span at most {TIGHT_MAX_ADR} average daily ranges high "
        "to low (G3), so a stock that moves 10% a day may rest wider than one that moves 4%; they surf a rising "
        "{SUPPORT_FAST}-, {SUPPORT_MID}- or {SUPPORT_SLOW}-day average, no close more than {REST_UNDERCUT_ADR} ADR "
        "under it (G4); and yesterday closed above its {PRIOR_CLOSE_SMA}-day average (G5).",
        "**The rest holds the move.** The rest's low gives back at most {REST_MAX_GIVEBACK_PCT}% of the prior move "
        "(G7): a flag near the top of the run, not a pullback that has undone most of it.",
        "**The market.** The index (Nasdaq-100 in the US, Nifty 500 in India) closes above its {MKT_EMA}-day "
        "exponential average, and its {MKT_FAST_EMA}-day EMA is above the {MKT_EMA}-day (G6).",
        "**Signal and buy.** S1: today closes above the rest's high. Buy at that close. The stop is today's low; the "
        "trade is skipped if that is more than {MAX_STOP_ADR} ADR or less than {MIN_STOP_PCT}% below the close, "
        "or if the ADR is under {ENTRY_MIN_ADR_PCT}% (0 = no floor beyond G1).",
        "**Manage.** At the close of session {PARTIAL_AFTER_BARS} after the entry, if the close is above the "
        "entry, sell 1/{PARTIAL_DIVISOR} there and move the stop to the entry. The rest sells at the first close "
        "below the {TRAIL_SMA}-day average, at the stop (or the open, if it gaps through), or after "
        "{MAX_HOLD_BARS} sessions.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: every gate passing, S1, and a stop inside the "
        "limits. Ties between same-day signals go to the stronger 12-1 month momentum.",
    )
    caveats = (
        "**Daily bars, not his entry.** Kullamägi buys intraday, on a break of the opening range, with the stop at "
        "that range's low. That entry is cheaper on a strong day, and its tight stop is where much of his edge may "
        "lie. Daily bars cannot see it: this buys the close of a day that has already moved, with the whole day's "
        "range under it. Results here say nothing either way about the intraday method.",
        "**Survivorship.** The universe is today's stock lists. Fast stocks are exactly the ones that collapse and "
        "are delisted, and a today's-list test leaves them out, flattering the result.",
        "**India price bands not modelled.** A breakout that locks at the upper band cannot be bought at the close, "
        "and a failure that locks at the lower band cannot be sold at the stop. The backtest fills both.",
        "**A stricter liquidity floor than the guide's.** The guide's floors are a close of ₹20 / $5 and a 50-day "
        "average turnover of ₹5 crore / $5m. Every strategy here applies the market's common floor instead, on the "
        "20-day average of close × volume (Minimum liquidity, ₹50 crore / $10m today), which is stricter; the price "
        "floor is not applied to split-adjusted history at all. So the universe is narrower and more liquid than "
        "the guide's event study, and its numbers are not expected to match.",
        "**No 20-session spacing.** The guide's event study counted one event per stock per 20 sessions. The "
        "portfolio backtest instead holds at most one position per stock, and a stock that was stopped out can be "
        "bought again from a new rest, as Kullamägi does.",
        "**The guide's own measurement.** Its daily-bar event study found about break-even in India before costs "
        "and slightly negative in the US, with over half the gains from the best 5% of trades. A few missing "
        "winners decide the result; read the share of P&L from the top trades.",
        "**Two rules were chosen in-sample.** v1.1's prior-move floor ({MOVERS_MIN_MOVE_PCT}%) and G7 came from "
        "auditing the losing trades of v1.0's optimise runs (2013-2021), so an optimise result for v1.1 is partly "
        "fitted to those years; only the verify stage can judge them.",
        "**Fills at the stop.** On a day that does not gap through it, the stop fills at its price. On fast stocks "
        "the real fill is often worse.",
        "**Run it with its exit flags.** `--exit-mode kullamagi --no-target` (the page's backtest command adds "
        "them). Without them the default bracket sells everything at the nominal target.",
        "**The fill session is never checked.** The entry is the breakout session's close, so its stop and exits are "
        "first tested on the next session.",
        "**No results rule.** Kullamägi sells before results unless well in profit; this does not know results "
        "dates and holds through them.",
        corporate_actions.CAVEAT_TRADED,
    )

    status = (
        "v1.4 is v1.3's rules plus an entry ADR floor that is off by default; v1.3's results below stand for it. "
        "Being measured (optimise, in-sample): Kullamagi's sizing and a switch that drops to a quarter size while "
        "the last 20 closed trades lose (--pe --pe-window 20 --pe-pilot 0.25 --pe-no-streak), and "
        "ENTRY_MIN_ADR_PCT=5. All three were chosen from v1.3's US optimise trades. "
        "v1.3 FAILED the pass criterion in the optimise stage (2013-2021, in-sample: its rest constants were set "
        "from the model book's 2019-2020 marked buys). Verify not run. The criterion, set before any v1.3 result and "
        "unchanged from v1.1: the base rules beat the market's benchmark CAGR AND make a positive average R after "
        "costs, in at least one market. US: 5.85% CAGR against 14.01% (excess -8.16 points a year), max drawdown "
        "-41.4%, 1,202 trades, win rate 39.0%, +0.11R a trade; the best 10% of trades made 7 times the book's P&L. "
        "India: 1.81% against 13.54% (excess -11.72), max drawdown -21.4%, 333 trades, 40.2%, +0.12R, top 10% 7 "
        "times. Average R is positive in both markets, but neither beats buy-and-hold. Up-front variants (v1.3, "
        "optimise, in-sample): TIGHT_MAX_ADR=2 US -2.83% (excess -16.84, +0.02R), India -2.74% (-16.28, -0.27R); "
        "TRAIL_EMA=1 with TRAIL_SMA=20 US 6.78% (-7.23, +0.10R, max drawdown -33.4%), India 1.54% (-11.99, "
        "+0.18R, -24.6%). In every arm the median trade is a full -1R stop. "
        "v1.1 rules FAILED the pass criterion in the optimise stage (2013-2021, in-sample; measured by v1.2 runs with "
        "the defaults, which are v1.1's rules). Verify not run. The criterion, set before any v1.1 result: the base rules "
        "beat the market's benchmark CAGR AND make a positive average R after costs, in at least one market. "
        "US: -0.64% CAGR against 14.01% (excess -14.65 points a year), max drawdown -54.2%, 1,104 trades, win rate "
        "36.4%, -0.03R a trade, net P&L negative. India: 1.03% against 13.54% (excess -12.50), max drawdown -27.5%, "
        "347 trades, 36.6%, +0.05R; the best 10% of trades made 11 times the whole book's P&L. "
        "Up-front variants (v1.2, optimise, in-sample; neither passes): TIGHT_MAX_PCT=15 US 0.58% (excess -13.43, "
        "+0.05R, max drawdown -43.6%), India 2.37% (-11.17, +0.13R, -18.8%); TRAIL_EMA=1 with TRAIL_SMA=20 (the "
        "20-day EMA trail, chosen from a replay of the v1.0 optimise trades) US 2.01% (-12.00, +0.08R, -42.4%), "
        "India 1.79% (-11.75, +0.19R, -31.2%). In every arm the median trade is a full -1R stop. "
        "v1.1's two new entry rules were chosen from the v1.0 optimise runs, so those years are in-sample for them. "
        "v1.0 FAILED the same criterion in the optimise stage: US -0.65% CAGR, excess -14.66 points a year, max "
        "drawdown -54.2%, 1,493 trades, win rate 37.4%, +0.05R a trade; India -4.48% CAGR, excess -18.02, max "
        "drawdown -44.6%, 558 trades, 35.5%, -0.11R. Variants (v1.0, optimise): TIGHT_MAX_PCT=15 US 3.23% (excess "
        "-10.78), India -1.09% (-14.63); TRAIL_SMA=20 US -3.25% (-17.26), India -2.46% (-15.99). In both markets the "
        "best 10% of v1.0's trades made more than the whole book."
    )
    gate_docs = {
        "G1": (
            "A fast stock: average daily range of {MOVERS_MIN_ADR_PCT}% or more (the Big movers screen's M1).\n\n"
            "- **ADR:** the mean, over the last {MOVERS_ADR_BARS} sessions including today, of high ÷ low − 1.\n"
            "- **Fails:** a narrower range, or fewer than {MOVERS_ADR_BARS} sessions.\n\n"
            "A stop at the day's low needs a stock that moves several percent a day to have any chance of a "
            "ten-times-risk winner."
        ),
        "G2": (
            "A big prior move (the Big movers screen's M2).\n\n"
            "- **Test:** the highest high of the last {MOVERS_HIGH_BARS} sessions is at least "
            "{MOVERS_MIN_MOVE_PCT}% above the lowest low of the last {MOVERS_LOW_BARS}.\n"
            "- **Fails:** a smaller move, or fewer than {MOVERS_LOW_BARS} sessions.\n\n"
            "Kullamägi only trades the stocks that have already moved most."
        ),
        "G3": (
            "A tight rest.\n\n"
            "- **The rest:** the {REST_BARS} sessions before today.\n"
            "- **Test:** their highest high minus their lowest low, as % of that high, is at most {TIGHT_MAX_ADR} "
            "times today's average daily range (G1's ADR).\n"
            "- **Fails:** a wider range: no close stop is possible from a loose base.\n\n"
            "Tightness is relative to how far the stock moves in a day: the model book's high-momentum rests "
            "span 1.3 to 3.3 ADRs, often 25-30% on a stock that moves 10% a day."
        ),
        "G4": (
            "The rest surfs a rising average.\n\n"
            "- **Averages:** the {SUPPORT_FAST}-, {SUPPORT_MID}- and {SUPPORT_SLOW}-day simple averages of closes.\n"
            "- **Test:** for at least one of them, its value on the rest's last session is above its value on the "
            "rest's first, and every one of the rest's {REST_BARS} closes is at most {REST_UNDERCUT_ADR} ADR below "
            "that session's average (intraday lows may dip further).\n"
            "- **Fails:** no average both rising and held, or not enough history for the slowest.\n\n"
            "Kullamägi: the stock \"starts surfing one of the moving averages ... the 10-day, the 20-day, the "
            "50-day\"; the shakeout wick through an average is part of the setup, a close well under it is not."
        ),
        "G5": (
            "Yesterday closed above its {PRIOR_CLOSE_SMA}-day average.\n\n"
            "- **Test:** the close of the session before today is strictly above that session's "
            "{PRIOR_CLOSE_SMA}-day simple average of closes."
        ),
        "G6": (
            "The market is in a short-term uptrend.\n\n"
            "- **Index:** the Nasdaq-100 (QQQ) in the US, the Nifty 500 in India; a market whose config lists "
            "neither uses its benchmark.\n"
            "- **Test:** today the index closes above its {MKT_EMA}-day exponential average, and its "
            "{MKT_FAST_EMA}-day EMA is above the {MKT_EMA}-day.\n"
            "- **Off switch:** with REQUIRE_MARKET = 0 (now {REQUIRE_MARKET}) the gate always passes.\n\n"
            "In the guide's event study this filter did not help in either market; it is kept because it is his rule."
        ),
        "G7": (
            "The rest holds the upper part of the prior move.\n\n"
            "- **The move:** from L, the lowest low of the {MOVERS_LOW_BARS} sessions before today, to H, the highest "
            "high of the {MOVERS_HIGH_BARS} sessions before today.\n"
            "- **Test:** (H − the rest's lowest low) ÷ (H − L) is at most {REST_MAX_GIVEBACK_PCT}%.\n"
            "- **Fails:** a deeper pullback, or no move (H not above L).\n\n"
            "Kullamägi's flags hold near the top of the run. In the v1.0 optimise runs, breakouts from bases that had "
            "given back more than half the move lost money in every run."
        ),
    }
    watch_docs = {}
    setup_docs = {
        S1: (
            "Today closes above the rest's high.\n\n"
            "- **Pivot:** the highest high of the {REST_BARS} sessions before today (set before today, so no "
            "look-ahead).\n"
            "- **Test:** today's close is strictly above it.\n"
            "- **Signal:** the setup is the entry signal (setup quality 2). A stock that closes above the pivot again "
            "the next day is a new test against a new rest."
        ),
    }
    entry_rules = (
        "Signal. S1 with every gate passing and a stop inside the limits, graded TRADE - HIGH CONFIDENCE.",
        "Order. Buy at the breakout session's close (backtest: a close order filled that session, plus slippage). "
        "This is the daily-bar stand-in for his opening-range entry.",
        "One position per stock (backtest). A signal in a stock already held is ignored.",
    )
    stop_rules = (
        "Where it goes. The breakout session's low, rounded down to the tick. It defines 1R.",
        "How far is too far. More than {MAX_STOP_ADR} × ADR (as a % of the entry) below the entry is WATCH - WAIT "
        "live and not bought in the backtest. So is a stop closer than {MIN_STOP_PCT}%: noise would take it.",
        "How it sells (backtest). The first session whose low touches it sells at the stop, or at the open if it "
        "opened below it.",
        "It moves once. To the entry price, when the partial sale is made (see Exit). Never down.",
    )
    target_rules = (
        "There is no sell order at the target. The target is entry + {NOMINAL_TARGET_R} R, so that the plan has an "
        "R column. The backtest runs with `--no-target`.",
    )
    exit_rules = (
        "Each session after the entry, in this order (backtest, `--exit-mode kullamagi`):",
        "1. The stop: everything left sells at the stop, or at the open if the stock gapped through it.",
        "2. The trail: a close below the {TRAIL_SMA}-day average sells everything left at that close. The average "
        "is simple, or exponential when TRAIL_EMA = 1 (now {TRAIL_EMA}).",
        "3. The partial sale: at the close of session {PARTIAL_AFTER_BARS} after the entry, if that close is "
        "above the entry, 1/{PARTIAL_DIVISOR} of the shares sells there and the stop moves up to the entry. Checked "
        "on that session only.",
        "4. The time limit: whatever is left sells at the close of session {MAX_HOLD_BARS} after the entry.",
        "Live, the screen shows the setup; nothing manages an open position.",
        "No other exits. A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped at Max position "
        "size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots. At most Position cap positions at once. A close order with no free slot is dropped.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "No price floor on split-adjusted history and no results rule.",
        "Market regime. The market test is gate G6; the shared risk-off downgrade is not applied on top of it.",
    )
    regime_note = (
        "No downgrade. The market test is this strategy's own hard gate G6, so a risk-off market is already an "
        "AVOID; the shared market-regime downgrade is not applied on top of it."
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, today closed above the rest's high (S1), the stop is within "
                                 "{MAX_STOP_ADR} ADR and at least {MIN_STOP_PCT}% below the entry, and one share "
                                 "fits the account. The only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Not used.",
        "WATCH_WAIT": "S1 fired but the stop is too far (more than {MAX_STOP_ADR} ADR) or too close (under "
                      "{MIN_STOP_PCT}%), the ADR is under the entry floor ({ENTRY_MIN_ADR_PCT}%, when set), or not "
                      "even one share fits the account.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number.",
    }
    param_docs = (
        ("Minimum ADR", "MOVERS_MIN_ADR_PCT", "G1: the average daily range, %, a stock needs (Big movers screen)."),
        ("ADR window", "MOVERS_ADR_BARS", "Sessions in the average daily range."),
        ("Prior move", "MOVERS_MIN_MOVE_PCT", "G2: how far, %, the recent high must sit above the low."),
        ("Prior-move high window", "MOVERS_HIGH_BARS", "Sessions whose highest high is compared."),
        ("Prior-move low window", "MOVERS_LOW_BARS", "Sessions whose lowest low it is compared with."),
        ("Rest length", "REST_BARS", "Sessions before the breakout that form the rest."),
        ("Rest tightness", "TIGHT_MAX_ADR", "G3: the rest's high-to-low span, % of its high, at most this many ADRs."),
        ("Fast support", "SUPPORT_FAST", "G4: the fastest average the rest may surf."),
        ("Middle support", "SUPPORT_MID", "G4: the middle average."),
        ("Slow support", "SUPPORT_SLOW", "G4: the slowest average."),
        ("Close undercut", "REST_UNDERCUT_ADR", "G4: how far, in ADRs, a rest close may sit below the average."),
        ("Prior-close average", "PRIOR_CLOSE_SMA", "G5: yesterday's close must be above this average."),
        ("Maximum giveback", "REST_MAX_GIVEBACK_PCT", "G7: the share, %, of the prior move the rest's low may give back."),
        ("Market gate", "REQUIRE_MARKET", "1: G6 is a hard gate; 0: it always passes."),
        ("Index EMA", "MKT_EMA", "G6: the index closes above this exponential average."),
        ("Index fast EMA", "MKT_FAST_EMA", "G6: this EMA must be above the slower one."),
        ("Maximum stop", "MAX_STOP_ADR", "A stop further than this many ADRs below the entry is not bought."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Entry ADR floor", "ENTRY_MIN_ADR_PCT", "A stock with a lower ADR, %, is not bought (0: off)."),
        ("Partial after", "PARTIAL_AFTER_BARS", "The session after the entry whose close decides the partial sale."),
        ("Partial size", "PARTIAL_DIVISOR", "1/this of the shares is sold."),
        ("Trailing average", "TRAIL_SMA", "The rest sells at the first close below the average of this length."),
        ("Exponential trail", "TRAIL_EMA", "0: that average is simple; 1: exponential."),
        ("Time limit", "MAX_HOLD_BARS", "Sessions after the entry before what is left is sold."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct", "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "The stop is rounded down to this increment."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--exit-mode kullamagi --no-target --rank-by setup_momentum"

    # ---------- market ----------

    _market_cache: dict = {}

    @classmethod
    def _market_ok(cls, market_key: str):
        """Per date: does the index pass G6? Computed once per market and cached on the class, because every
        symbol on every bar asks the same question of the same series. The averages are causal, so a value
        on a date reads only the index up to it."""
        if market_key not in cls._market_cache:
            from ..config import MARKETS
            from ..marketdata import cache
            cfg = MARKETS[market_key]
            label = next((x for x in MARKET_INDEX_LABELS if x in cfg.broad_index_symbols), None)
            ticker = cfg.broad_index_symbols[label] if label else cfg.benchmark_ticker
            b = cache.load_cached(market_key, ticker)
            if b is None or b.empty:
                cls._market_cache[market_key] = None
            else:
                c = b["close"].astype(float)
                slow, fast = ind.ema(c, MKT_EMA), ind.ema(c, MKT_FAST_EMA)
                cls._market_cache[market_key] = (c > slow) & (fast > slow)
        return cls._market_cache[market_key]

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """The market test is gate G6, so the shared downgrade is not applied on top of it."""
        return False

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        d = ctx.daily
        self.apply_screen(ctx, result)
        ctx.extras["adr_pct"] = crit.adr_pct(d)
        ctx.extras["prior_move_pct"] = crit.prior_move_pct(d)

        n = len(d)
        if n < REST_BARS + max(SUPPORT_SLOW, PRIOR_CLOSE_SMA) + 1:
            for g in ("G3", "G4", "G5"):
                result.fail(g, "insufficient history for the rest")
            g7 = (False, "insufficient history for the rest")
        else:
            rest = d.iloc[-REST_BARS - 1:-1]
            hi, lo = float(rest["high"].max()), float(rest["low"].min())
            span = (hi - lo) / hi * 100 if hi > 0 else float("nan")
            ctx.extras["rest_high"], ctx.extras["rest_low"], ctx.extras["rest_span_pct"] = hi, lo, span
            adr = ctx.extras["adr_pct"]
            span_adr = span / adr if adr else float("nan")
            ctx.extras["rest_span_adr"] = span_adr
            if span_adr <= TIGHT_MAX_ADR:
                result.ok("G3", f"rest spans {span:.1f}% ({span_adr:.1f} ADR)")
            else:
                result.fail("G3", f"rest spans {span:.1f}% ({span_adr:.1f} ADR > {TIGHT_MAX_ADR})")

            closes = d["close"].astype(float)
            rest_closes = closes.iloc[-REST_BARS - 1:-1].to_numpy()
            floor = 1 - REST_UNDERCUT_ADR * adr / 100
            support, worst = 0, []
            for length in (SUPPORT_FAST, SUPPORT_MID, SUPPORT_SLOW):
                avg = closes.iloc[-(REST_BARS + length):].rolling(length).mean().iloc[-REST_BARS - 1:-1].to_numpy()
                ratio = (rest_closes / avg).min()
                worst.append(f"{length}-day {(ratio - 1) * 100 / adr:+.1f} ADR{'' if avg[-1] > avg[0] else ' falling'}")
                if avg[-1] > avg[0] and ratio >= floor:
                    support = length
                    break
            ctx.extras["support_sma"] = support
            if support:
                result.ok("G4", f"surfs the rising {support}-day")
            else:
                result.fail("G4", "no rising average held: " + ", ".join(worst))

            before = d.iloc[:-1]
            move_hi = float(before["high"].iloc[-MOVERS_HIGH_BARS:].max())
            move_lo = float(before["low"].iloc[-MOVERS_LOW_BARS:].min())
            if move_hi > move_lo:
                giveback = (move_hi - lo) / (move_hi - move_lo) * 100
                ctx.extras["giveback_pct"] = giveback
                g7 = ((True, f"rest gave back {giveback:.0f}% of the move") if giveback <= REST_MAX_GIVEBACK_PCT else
                      (False, f"rest gave back {giveback:.0f}% of the move (> {REST_MAX_GIVEBACK_PCT}%)"))
            else:
                g7 = (False, "no prior move")

            prev = d["close"].iloc[-(PRIOR_CLOSE_SMA + 1):-1].astype(float)
            prev_close, prev_avg = float(prev.iloc[-1]), float(prev.mean())
            if prev_close > prev_avg:
                result.ok("G5", "")
            else:
                result.fail("G5", f"prior close at/below its {PRIOR_CLOSE_SMA}-day")

        if REQUIRE_MARKET:
            ok = self._market_ok(_market_of(ctx.symbol))
            if ok is None:
                result.fail("G6", "no index history")
            elif bool(ok.asof(d.index[-1])):
                result.ok("G6", "")
            else:
                result.fail("G6", "index not in a short-term uptrend")
        else:
            result.ok("G6", "market gate off")

        rest_high = ctx.extras.get("rest_high")
        result.setups[S1] = bool(rest_high is not None and ctx.close > rest_high)
        # G7 last: codes follow evaluation order, and it was added after G6 (v1.1)
        (result.ok if g7[0] else result.fail)("G7", g7[1])
        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.setups.get(S1) else 0.0

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return bool(result.setups.get(S1))

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        entry = float(ctx.close)
        stop = round_tick(float(ctx.last["low"]), cfg.tick_size, "down")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        adr = ctx.extras.get("adr_pct")
        ctx.extras["stop_adr"] = (risk / entry * 100 / adr) if adr and adr == adr and entry else float("nan")
        plan = TradePlan(
            plan="KB", setup=S1, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R if risk > 0 else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"close above the rest's high {ctx.extras.get('rest_high', 0):.2f}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        return {"order": "close"}

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID", f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        adr = ctx.extras.get("adr_pct")
        if sizing_result.too_large:
            label, reason = "WATCH_WAIT", "too large for account"
        elif not adr or adr != adr or risk_pct > MAX_STOP_ADR * adr:
            label, reason = "WATCH_WAIT", f"stop {risk_pct:.1f}% away, more than {MAX_STOP_ADR} ADR ({adr or 0:.1f}%)"
        elif risk_pct < MIN_STOP_PCT:
            label, reason = "WATCH_WAIT", f"stop only {risk_pct:.1f}% away (< {MIN_STOP_PCT}%)"
        elif adr < ENTRY_MIN_ADR_PCT:
            label, reason = "WATCH_WAIT", f"ADR {adr:.1f}% under the entry floor ({ENTRY_MIN_ADR_PCT}%)"
        else:
            label, reason = "TRADE_HIGH_CONFIDENCE", f"close above a tight rest; stop {risk_pct:.1f}% away"
        return Decision(LABELS[label], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The rest the close left, and the stop under the breakout day."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        hi, lo = e.get("rest_high"), e.get("rest_low")
        if hi and lo:
            out.append({"shape": "box", "bars": REST_BARS + 1, "to": d, "top": float(hi), "bottom": float(lo),
                        "role": "base", "label": f"the rest — {e.get('rest_span_pct') or 0:.1f}% high to low"})
            out.append({"shape": "level", "bars": REST_BARS + 1, "to": d, "price": float(hi), "role": "pivot",
                        "label": f"rest high {hi:g} — a close above is the buy"})
            out.append({"shape": "note", "at": d, "price": float(hi),
                        "text": f"Kullamägi breakout {d}: ADR {e.get('adr_pct') or 0:.1f}%, prior move "
                                f"{e.get('prior_move_pct') or 0:.0f}%; bought the close, stop at the day's low."})
        return out or super().chart_anatomy(sig)
