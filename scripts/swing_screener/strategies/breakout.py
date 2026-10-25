"""Breakout strategy — a second, deliberately different implementation.

Its purpose is twofold: it's a usable strategy, and it proves the Strategy
seam is real. It shares none of trend_pullback's gate vocabulary, setup
codes, entry geometry or watch flags — it only consumes the same shared
StockContext and emits the same StrategyResult/TradePlan/Decision types.
If adding this had required editing pipeline.py, backtest.py, output.py or
the storage layer, the abstraction would have been fake.

Thesis: buy a decisive, volume-confirmed break to new highs out of a tight
consolidation, rather than buying weakness inside a trend.

NOT yet validated against market data — the gate thresholds here are
reasonable defaults, not tuned or backtested numbers. Run it through
backtest.py before trusting it.
"""

import pandas as pd

from ..marketdata import corporate_actions
from ..core import swings as sw
from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import (
    tradable_point_in_time,
    CAP_ORDER,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .trend_pullback import round_tick

BO01 = "S1"   # BO-01  # new-high breakout from consolidation
BO02 = "S2"   # BO-02  # pre-breakout coil, sitting just under the pivot

CONSOLIDATION_BARS = 20
BREAKOUT_LOOKBACK = 55
# Named, not bare, so a variant can move them (`--const`) and the page shows the live value. They
# were literals in evaluate/classify until 1.4, which is why no backtest could test a wider stop.
VOL_MULT = 1.5                 # S1: the breakout close's volume against its 50-day average
HIGH_CONF_MAX_STOP_PCT = 7.0   # a stop this far below entry or less can be TRADE - HIGH CONFIDENCE
MAX_STOP_PCT = 8.0             # beyond this the plan is WATCH - WAIT


class BreakoutStrategy(Strategy):
    selection = "time_series"
    version = "1.5"
    changelog = (
        ("1.5", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited "
         "(marketdata/corporate_actions.py). On the ex-date a held position receives the cash and its "
         "entry, stop, target and other levels move down by the payout; before, the stored close fell by "
         "it and the trade booked the payout as a loss, or was stopped out by it. An order resting in the "
         "stock that day is cancelled. Only trades held across such an ex-date move. Stored prices were "
         "also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and "
         "GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py "
         "correct)."),
        ("1.4", "2026-10-24",
         "No rule changed. The breakout volume multiple and the two stop caps -- the "
         "{HIGH_CONF_MAX_STOP_PCT}% that keeps a trade HIGH CONFIDENCE (and so the cap a backtest "
         "really applies) and the {MAX_STOP_PCT}% beyond which it is WATCH -- were bare numbers in "
         "the code, so no variant could move them and the page could not show them live. They are "
         "named constants now. Done to test wider caps: measured over 2013-2021 "
         "(research/crwd-gap-studies.md), breakouts with stops of 12-15% earned more per unit of "
         "risk than those under 8%, in both markets."),
        ("1.3", "2026-10-24",
         "Same-day ties now go to the stronger stock rather than the earlier letter. Every accepted signal "
         "scores the same setup quality, so when more triggered than there was cash for, the tie fell "
         "through to Python's stable sort -- the scan order, alphabetical. The backtest now keeps the "
         "strategy's score and breaks only exact ties by 12-1 momentum (`--rank-by setup_momentum`). "
         "Bumped by hand: backtest_args is not a numeric constant."),
        ("1.2", "2026-10-16",
         "Gate, watch and setup codes renamed to one scheme shared by every strategy: G1..Gn for the hard "
         "gates, W1..Wn for the watch flags, S1..Sn for the setups. "
         "The old letters meant nothing and collided across strategies: B1-B4 were minervini's WATCH flags "
         "and breakout's GATES, so one string blocked a trade in the first and merely noted something in "
         "the second. The prefix now states the only thing that matters when reading a drop reason -- "
         "whether the code can stop a trade. No rule changed, but the code tuples are part of the "
         "fingerprint, so this moves the spec id and earlier runs stay under their own versions."
         "BO-01/02 become S1/S2 and XB1-XB3 become W1-W3; the setup docs cite BO-0n."),
        ("1.1", "2026-10-10",
         "The point-in-time pre-filter no longer applies cfg.screener.min_price. The floor keeps "
         "live screening out of penny stocks, but a backtest reads it against SPLIT-ADJUSTED "
         "history, so it deleted the early years of exactly the stocks that went up most -- "
         "splitting is what winners do. NVDA traded about $15 in 2013 on $126m a day, 12x the "
         "liquidity floor; stored back-adjusted through a 4:1 and a 10:1 split that is $0.39, "
         "under the $10 US floor, so NVDA did not qualify until 2020-07-08 and SMCI not until "
         "2023. Liquidity is now carried by min_dollar_volume alone, which is split-invariant "
         "(close falls by the split factor, volume rises by it). Live screening keeps the price "
         "floor in screens/base.py, where today's price really is today's price. On NVDA this "
         "takes evaluable bars from 815 to 1,841 of 3,464; India is unaffected (min_price=0)."),
        ("1.0", "2026-10-10",
         "v1 baseline of the volume-confirmed breakout strategy."),
    )
    key = "breakout"
    name = "Volume breakout"
    description = (
        "Long breakouts to new {BREAKOUT_LOOKBACK}-day highs out of a tight consolidation, "
        "confirmed by expanding volume."
    )
    style = "breakout"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2"}
    watch_codes = ("W1", "W2", "W3")
    setup_codes = (BO01, BO02)
    setup_names = {BO01: "Breakout", BO02: "Coil"}
    # short names for the chart's checklist; the rules themselves are gate_docs
    gate_titles = {"G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
                   "G4": "Tight {CONSOLIDATION_BARS}-bar base", "G5": "Not extended above the 20-day",
                   "G6": "Volatility sane", "G7": "No earnings within 10 days"}
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("breakout_pivot", "pct_from_pivot", "structural_r")
    extra_numeric_columns = ("breakout_pivot", "pct_from_pivot", "structural_r")

    # Minimum reward the consolidation must actually project, measured off the
    # base height. Nothing pads a setup up to this — it is a rejection
    # threshold, not a target floor.
    min_structural_r: float = 2.0

    thesis = (
        "A decisive, volume-confirmed break to new highs out of a tight "
        "consolidation continues, so buy strength rather than weakness."
    )
    # Overview only; the exact tests are in the gate/watch/setup docs and the rule groups below.
    # Every fact here was checked against prefilter_row / evaluate / build_plans / classify above,
    # the pipeline's pre-filter and backtesting/portfolio_sim.py (resting buy-stop, bracket exit).
    how_it_works = (
        "**The idea.** Buy a close through the {BREAKOUT_LOOKBACK}-day high on heavy volume, out of a "
        "tight {CONSOLIDATION_BARS}-session base, near the 52-week high, and hold for the base's "
        "measured move.",
        "**Qualify.** A pre-filter (liquidity, trend, volatility, near the highs), then seven hard "
        "gates G1-G7. See Gates and When no new trade is taken.",
        "**Signal.** S1, a close above the pivot on more than {VOL_MULT} times average volume. S2 only marks "
        "a close coiled within 3% under the pivot. See Setups.",
        "**Buy.** A buy-stop 0.1% above the breakout session's high, filled on a later session that "
        "trades through it. See Entry.",
        "**Stop and target.** The stop is never more than 2 ATR under the entry; the target is the "
        "base's height added to the entry, cut to the nearest overhead swing high, and must be at "
        "least {min_structural_r}R away. In the backtest both are fixed sell orders. See Stop, "
        "Target and Exit.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: S1 with all seven gates, no W1 or "
        "W3, a stop no more than {HIGH_CONF_MAX_STOP_PCT}% below the entry and at least 2R. It has no earnings calendar and "
        "no market-regime downgrade.",
        "**Where the rules come from.** Classic volume-breakout practice, with untuned thresholds. "
        "There is no written spec with row ids: BO-01 and BO-02 are the setups' names from before the "
        "S1/S2 codes, and are not the chart-pattern spec's rows of the same id.",
    )
    caveats = (
        "**NOT VALIDATED.** The thresholds are untuned defaults; see Status for the measured result. "
        "Treat what it produces as a hypothesis to test, not a signal to act on.",
        "**The stop is never under the base.** The price paid is above the base's high, so a stop "
        "under the base risks more than the base's height and can never project {min_structural_r}R. "
        "Every plan that passes therefore has the 2-ATR stop, inside the base. 'Stop below the "
        "consolidation' is the rule's intent, not what any traded plan gets.",
        "**R lands between {min_structural_r} and 3.** With the 2-ATR stop, the {min_structural_r}R "
        "test needs a base at least {min_structural_r} × 2 ATR tall, and G4 allows at most 6 ATR.",
        "**W2 can never fire.** It needs S1, and S1 already requires volume above {VOL_MULT} times average, "
        "so 'a breakout on below-average volume' is impossible. Its WATCH cap and quality cut never "
        "act.",
        "**Overhead lowers R.** When an overhead level lowers the target, the R column is smaller than "
        "`structural_r` (what the base alone projects), and the {min_structural_r}R test uses the "
        "lowered R.",
        "**The reward test is not repeated at the fill.** A gap up at the next open raises the price "
        "paid without moving the stop or the target, so a trade can be bought at under 2R. It is "
        "skipped only when the fill is at or above the target.",
        "**The fill session is never checked.** In the backtest the stop and target are first tested "
        "on the session after the fill. A session that triggers the buy and then trades through the "
        "stop is held overnight, and survives if the next session stays above the stop: kinder than "
        "a real stop order.",
        "**Ties go to the stronger stock.** Every signal the backtest accepts scores the same setup "
        "quality, 2, so when more trigger on one day than there is cash to buy them all, something else "
        "has to choose. Before 1.3 it was the order the market was scanned in -- alphabetical. Now the "
        "strategy's own score still decides, and 12-1 month momentum only breaks the tie "
        "(`--rank-by setup_momentum`). The competition is for cash, not slots: on the 1.1 US run 314 "
        "signals were turned away for want of cash against 705 trades, and 10 for a full book.",
        "**No price floor anywhere.** Version 1.1 removed `cfg.screener.min_price` from the "
        "point-in-time pre-filter. The daily screen calls that same pre-filter, so it applies no "
        "price floor either; only the Screens page's snapshot does.",
        corporate_actions.CAVEAT_TRADED,
    )

    # --- full reference documentation (generated Strategy page) ---
    # Numbers are `{NAME}` placeholders of the module constants and `min_structural_r`; a literal is
    # written where the code uses a literal.
    status = (
        "Not validated, no demonstrated edge: thresholds are untuned defaults. Full US backtest "
        "from 2013 (v1.1, bracket exits, measured 2026-10-12 after the cost fix): 2.15% CAGR "
        "against SPY's 12.8%, max drawdown -29.7%. India not yet run at full size."
    )
    gate_docs = {
        "G1": "Close above the 200-day average (the Near-highs screen's H1).\n\n"
              "- **Test:** today's close is strictly above today's 200-day simple moving average of closes.\n"
              "- **Fails:** a close at or below it, or no average yet. The pre-filter applies the same "
              "test first.",
        "G2": "The 200-day average is not falling (the Near-highs screen's H2).\n\n"
              "- **Falling:** today's 200-day average is more than 0.5% below its value 20 sessions ago.\n"
              "- **Passes:** rising or flat (down 0.5% or less), and when either value is missing.",
        "G3": "Close within 5% of the 52-week high.\n\n"
              "- **52-week high:** the highest high of the last 252 sessions, today included.\n"
              "- **Test:** close ≥ 0.95 × that high.\n"
              "- **Fails:** a lower close, or no 52-week high.\n\n"
              "Tighter than the Near-highs screen's own limit (H3), which this strategy does not apply.",
        "G4": "The {CONSOLIDATION_BARS} sessions before today form a tight base: their range is at most "
              "6 ATR.\n\n"
              "- **Range:** the highest high minus the lowest low of the {CONSOLIDATION_BARS} sessions "
              "before today. Today is excluded.\n"
              "- **Test:** range ≤ 6 × ATR14, with ATR14 (the 14-day Wilder average true range) as of "
              "today.\n"
              "- **Fails:** a wider range, fewer than {CONSOLIDATION_BARS} earlier sessions, or a missing "
              "or zero ATR.\n\n"
              "The same window sets the stop and the target (see Stop and Target).",
        "G5": "Close no more than 4 ATR above the 20-day average.\n\n"
              "- **Test:** close − 20-day simple moving average ≤ 4 × ATR14. Exactly 4 ATR passes.\n"
              "- **Passes:** when the average or ATR is missing.\n\n"
              "W1 flags anything more than 2.5 ATR above it, which already keeps a plan from HIGH "
              "CONFIDENCE.",
        "G6": "ATR14 is at most 8% of the close.\n\n"
              "- **Test:** ATR14 ÷ close × 100 ≤ 8.\n"
              "- **Passes:** when ATR% is missing. The pre-filter separately requires it above the "
              "Minimum ATR%.",
        "G7": "No results due within 10 business days.\n\n"
              "- **Test:** fails when the next earnings date is 10 or fewer business days away (0 = "
              "today).\n"
              "- **Passes:** when no date is known.\n"
              "- **Backtest:** there is no historical earnings calendar, so it always passes.\n\n"
              "Live, results 11 to 15 business days away still keep a plan from HIGH CONFIDENCE.",
    }
    watch_docs = {
        "W1": "Extended: the close is more than 2.5 ATR above the 20-day average.\n\n"
              "- **Test:** close − 20-day simple moving average > 2.5 × ATR14.\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER and cuts setup quality by 0.5. The "
              "note gives the 20-day average as a pullback level.\n\n"
              "The backtest buys only TRADE - HIGH CONFIDENCE, so it never trades a W1 stock.",
        "W2": "A breakout (S1) on below-average volume. It can never fire.\n\n"
              "- **Test:** S1 is active and today's volume is below its 50-day average.\n"
              "- **Why never:** S1 itself requires volume above 1.5 × that average.\n"
              "- **Effect, if it did:** WATCH - WAIT, and setup quality cut by 1.",
        "W3": "Overbought: RSI14 is above 80.\n\n"
              "- **Test:** the 14-day Wilder RSI of closes > 80, on any day.\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER, so the backtest never trades it. No "
              "effect on setup quality.",
    }
    setup_docs = {
        "S1": "BO-01 breakout: today's close is above the {BREAKOUT_LOOKBACK}-session pivot on more than "
              "{VOL_MULT} times average volume.\n\n"
              "- **Pivot:** the highest high of the {BREAKOUT_LOOKBACK} sessions before today. Today's "
              "bar is excluded.\n"
              "- **Breakout:** close > pivot, strictly.\n"
              "- **Volume:** today's volume > 1.5 × the 50-day average volume (an average that "
              "includes today).\n"
              "- **Signal:** the setup is the entry signal. Only S1 can reach TRADE - HIGH CONFIDENCE, "
              "and only S1 is bought by the backtest (setup quality 2).\n\n"
              "It fires on every such close, not only the first.",
        "S2": "BO-02 coil: today's close is within 3% below the pivot, not through it yet.\n\n"
              "- **Test:** 0.97 × pivot ≤ close ≤ pivot. No volume test.\n"
              "- **Signal:** none yet. It builds a plan, but the best decision is TRADE ON TRIGGER "
              "(setup quality 1). The backtest never buys it.",
    }
    entry_rules = (
        "Signal. An S1 breakout graded TRADE - HIGH CONFIDENCE. Live, an S2 coil or a capped S1 is "
        "TRADE ON TRIGGER: the same order, placed by the trader.",
        "Order. A buy-stop 0.1% above the higher of today's high and the {BREAKOUT_LOOKBACK}-session "
        "pivot, rounded up to the tick. For S1 today's high is already above the pivot, so the order "
        "sits 0.1% above the breakout session's high: the stock must trade above that high again.",
        "Fill (backtest). On the first later session whose high reaches the entry, at the higher of "
        "the entry and that session's open, plus slippage. It never fills on the signal session.",
        "Expiry and cancel (backtest). An unfilled order rests for up to 10 business days. It is "
        "cancelled if a session's low reaches the stop while its high stays under the entry, and "
        "skipped if the fill would be at or above the target.",
        "One position per stock (backtest). A signal in a stock already held, or with an order "
        "already resting, is ignored.",
        "No re-test at the fill. The stop-distance and reward tests use the planned entry. A gap up at "
        "the open raises the price paid but moves neither the stop nor the target.",
    )
    stop_rules = (
        "Where it goes. The higher of two prices, rounded down to the tick: 0.1 ATR under the lowest "
        "low of the {CONSOLIDATION_BARS} sessions before today (under the base), and 2 ATR under the "
        "entry. It is never more than 2 ATR below the entry.",
        "Which one binds. In every plan that passes the {min_structural_r}R test it is the 2-ATR stop, "
        "inside the base (see Caveats).",
        "It defines 1R. The distance from the price paid to the stop is the trade's risk, 1R. Results "
        "are counted in R.",
        "How far is too far. A stop more than {MAX_STOP_PCT}% below the entry is WATCH - WAIT. More than {HIGH_CONF_MAX_STOP_PCT}% keeps "
        "it from HIGH CONFIDENCE, so the backtest only buys stops of {HIGH_CONF_MAX_STOP_PCT}% or less: ATR14 at most about "
        "3.5% of the entry.",
        "How it sells (backtest). A standing sell order: the first session whose low touches the stop "
        "sells at the stop, or at the open if it opened below it. A gap can therefore lose more than "
        "1R. The stop wins a same-session tie with the target.",
        "It never moves. No trailing and no breakeven.",
    )
    target_rules = (
        "A real sell order. The backtest uses the bracket exit: the first session whose high reaches "
        "the target sells the whole position, at the target or at the open if it opened above it.",
        "How it is measured. Entry + the base's height: the highest high minus the lowest low of the "
        "{CONSOLIDATION_BARS} sessions before today. There is no floor and no padding.",
        "Overhead supply caps it. If a swing high sits above the entry and below that target, the "
        "target is lowered to the nearest one. A swing high is a high not exceeded within 3 sessions "
        "either side on the daily chart (last 252 sessions), 3 weeks either side on the weekly chart "
        "(last 260 weeks), or 2 months either side on the monthly chart (all history).",
        "The {min_structural_r}R test. (target − entry) ÷ (entry − stop) must be at least "
        "{min_structural_r}, after any overhead cut; below it the plan is WATCH - WAIT. HIGH "
        "CONFIDENCE checks again against a fixed 2 written into the decision, so lowering "
        "{min_structural_r} would not lower that bar. `structural_r` reports the base's own "
        "projection, before the cut.",
    )
    exit_rules = (
        "A fixed bracket (backtest). Each session after the fill, the stop is checked first, then the "
        "target; the first one touched sells everything. Neither moves.",
        "No other exits. No time stop, breakeven, trailing stop or partial sale. A position still open "
        "when the backtest ends is marked at the last close.",
        "Live, nothing manages an open position. The plan's stop and target are for the trader to "
        "place.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down. Example: "
        "$100,000 at 1% risks $1,000; paying $50 with the stop at $47 risks $3 a share, so 333 shares.",
        "Capped. The position may not be worth more than Max position size × equity. With 1% risk and "
        "a 25% cap, any stop closer than 4% below the price paid hits the cap, and the trade then "
        "risks less than 1%.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can instead of skipping.",
        "Backtest and live. The backtest sizes from current equity at the fill. The live screen sizes "
        "from the configured account size, at the lower high-volatility risk when the volatility "
        "index is above the market's threshold. A plan that cannot buy even one share is WATCH - WAIT.",
        "Slots. At most Max open positions at once. A triggered order with no free slot keeps resting "
        "until it expires, and may fill later at a higher open.",
    )
    filter_rules = (
        "Pre-filter. A stock is evaluated only if the 20-day average of close × volume is at least "
        "the Minimum liquidity, the close is above the 200-day average, ATR14 is more than the Minimum "
        "ATR% of the close, the close is at least 80% of the 52-week high, and it has at least "
        "{min_bars} daily bars. Live and in the backtest.",
        "No price floor. Neither the daily screen nor the backtest applies the Minimum price (see "
        "Caveats). India's daily screen also drops companies below the India config's minimum market "
        "cap.",
        "Results due. Live, results 10 or fewer business days away make the stock AVOID (G7), and 11 "
        "to 15 days away cap it at TRADE ON TRIGGER. The backtest has no earnings calendar and applies "
        "neither.",
        "Market regime. Live, a risk-off market lowers every decision one tier, so nothing is HIGH "
        "CONFIDENCE. The backtest does not apply it.",
        "Already in the stock, or no room. See Entry and Position size.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "All seven gates pass, S1 fired, neither W1 nor W3 is raised, the stop is "
                                 "no more than {HIGH_CONF_MAX_STOP_PCT}% below the entry, the plan offers at least 2R, no results "
                                 "are due within 15 business days and one share fits the account. The "
                                 "only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "A plan that passes the stop and reward tests but is not HIGH CONFIDENCE: an "
                            "S2 coil (buy only on the break), a W1 or W3 cap, a stop between {HIGH_CONF_MAX_STOP_PCT}% and {MAX_STOP_PCT}% "
                            "below the entry, results 11 to 15 business days away, or a HIGH CONFIDENCE "
                            "lowered by a risk-off market.",
        "WATCH_WAIT": "The stop is more than {MAX_STOP_PCT}% below the entry, the plan offers under "
                      "{min_structural_r}R, not even one share fits the account, or a TRADE ON TRIGGER "
                      "lowered by a risk-off market.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number, or a WATCH - WAIT lowered "
                 "by a risk-off market. A stock that passes every gate with no setup shows as NO SETUP "
                 "instead.",
    }
    regime_note = (
        "Live only. When the market is risk-off (the first two broad indices in the market's config "
        "both close at or below their 50-day average), every decision drops one tier (HIGH CONFIDENCE "
        "→ ON TRIGGER → WATCH → AVOID) and the reason says 'market-regime downgrade applied'. The "
        "backtest does not apply it."
    )
    param_docs = (
        ("Base length", "CONSOLIDATION_BARS",
         "Sessions before today that must form the tight base (G4), and whose low and height set the "
         "stop and the target."),
        ("Pivot lookback", "BREAKOUT_LOOKBACK",
         "Sessions before today whose highest high is the pivot for S1, S2 and the entry."),
        ("Minimum reward", "min_structural_r",
         "The target must be at least this many R from the entry, after any overhead cut, or the "
         "plan is WATCH - WAIT."),
        ("Minimum history", "min_bars",
         "Daily bars a stock needs before it is evaluated."),
        ("Minimum price", "cfg.screener.min_price",
         "Not applied by this strategy: the daily screen and the backtest both use the point-in-time "
         "pre-filter, which skips it. Only the Screens page's snapshot applies it."),
        ("Minimum ATR%", "cfg.screener.atr_pct_min",
         "Pre-filter: ATR14 as a % of the close must be above this, so very quiet stocks are skipped."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct",
         "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct",
         "Cap on one position's value as a fraction of equity."),
        ("Tick size", "cfg.tick_size",
         "The entry is rounded up and the stop rounded down to this increment."),
        ("Max open positions", "cfg.max_open_positions",
         "Backtest slots; a triggered order with no free slot keeps resting until it expires."),
        ("Slippage", "cfg.slippage_bps",
         "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--rank-by setup_momentum"

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last["sma200"]) or last["close"] <= last["sma200"]:
            return False, "close <= SMA200"
        if pd.isna(last["atr_pct"]) or last["atr_pct"] <= cfg.screener.atr_pct_min:
            return False, f"ATR% <= {cfg.screener.atr_pct_min}"
        if pd.isna(last["high_252"]) or last["close"] < last["high_252"] * 0.80:
            return False, "more than 20% below the 52-week high"
        return True, "passed"

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=(BO01, BO02))
        close, atr14 = ctx.close, ctx.atr
        high_252 = d["high_252"].iloc[-1]

        # B1-B2: the Near-highs screen's H1 (above the 200-day) and H2 (200-day not falling);
        # B3 below is this strategy's own, tighter, near-the-high rule
        self.apply_screen(ctx, result)

        # B3: at or near the highs — breakouts are bought at highs, not mid-range
        if pd.isna(high_252):
            result.fail("G3", "insufficient history for 52-week high")
        elif close >= high_252 * 0.95:
            result.ok("G3")
        else:
            result.fail("G3", "more than 5% below the 52-week high")

        # B4: a real consolidation preceded this — the prior N bars were tight
        prior = d.iloc[-(CONSOLIDATION_BARS + 1) : -1]
        if len(prior) < CONSOLIDATION_BARS or pd.isna(atr14) or not atr14:
            result.fail("G4", "insufficient bars to measure the consolidation")
        else:
            rng = float(prior["high"].max() - prior["low"].min())
            if rng <= 6 * atr14:
                result.ok("G4", f"{CONSOLIDATION_BARS}-bar range {rng / atr14:.1f} ATR")
            else:
                result.fail("G4", f"pre-breakout range {rng / atr14:.1f} ATR > 6 ATR (no tight base)")

        # B5: not already extended beyond a sane entry
        sma20 = d["sma20"].iloc[-1]
        if pd.notna(sma20) and pd.notna(atr14) and atr14 and (close - sma20) > 4 * atr14:
            result.fail("G5", "more than 4 ATR above SMA20")
        else:
            result.ok("G5")

        # B6: volatility sane
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > 8:
            result.fail("G6", f"ATR% {atr_pct:.1f} > 8%")
        else:
            result.ok("G6")

        # B7: earnings not imminent
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= 10:
            result.fail("G7", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("G7")

        self._compute_setups(ctx, result)
        result.recompute_first_fail()
        self._compute_watch_flags(ctx, result)
        return result

    def _compute_setups(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        close = ctx.close
        pivot = float(d["high"].iloc[-(BREAKOUT_LOOKBACK + 1) : -1].max())
        vol = float(d["volume"].iloc[-1])
        vol_sma50 = d["vol_sma50"].iloc[-1]
        vol_ok = pd.notna(vol_sma50) and vol_sma50 and vol > VOL_MULT * vol_sma50

        # BO-01: closed above the pivot today, on expanding volume
        result.setups[BO01] = bool(close > pivot and vol_ok)
        # BO-02: coiled just under the pivot, not through it yet
        result.setups[BO02] = bool(pivot * 0.97 <= close <= pivot)
        ctx.extras["breakout_pivot"] = pivot

    def _compute_watch_flags(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        close, atr14 = ctx.close, ctx.atr
        sma20 = d["sma20"].iloc[-1]
        rsi14 = d["rsi14"].iloc[-1]
        vol_sma50 = d["vol_sma50"].iloc[-1]

        # XB1: extended from the mean — breakout already ran
        result.watch_flags["W1"] = bool(
            pd.notna(sma20) and pd.notna(atr14) and atr14 and (close - sma20) > 2.5 * atr14
        )
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = f"extended; pullback target ~{sma20:.2f}"

        # XB2: breakout without volume confirmation — the classic failure mode
        vol = float(d["volume"].iloc[-1])
        thin = pd.notna(vol_sma50) and vol_sma50 and vol < vol_sma50
        result.watch_flags["W2"] = bool(thin and result.setups.get(BO01))
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = "breakout on below-average volume"

        # XB3: overbought
        result.watch_flags["W3"] = bool(pd.notna(rsi14) and rsi14 > 80)

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("W1"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("W2"):
            caps.append("WATCH_WAIT")
        if result.watch_flags.get("W3"):
            caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        score = 2.0 if result.setups.get(BO01) else (1.0 if result.setups.get(BO02) else 0.0)
        if result.watch_flags.get("W2"):
            score -= 1.0
        if result.watch_flags.get("W1"):
            score -= 0.5
        return score

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """For a breakout the signal IS the setup: BO-01 means today's close
        already cleared the pivot on volume."""
        return bool(result.setups.get(BO01))

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")

        d = ctx.daily
        atr14 = ctx.atr
        pivot = ctx.extras.get("breakout_pivot")
        if pivot is None or pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing pivot/ATR")

        setup = BO01 if result.setups.get(BO01) else BO02
        trigger = max(float(d["high"].iloc[-1]), pivot)
        entry = round_tick(trigger * 1.001, cfg.tick_size, "up")

        # stop below the consolidation, but never wider than 2 ATR
        base_low = float(d["low"].iloc[-(CONSOLIDATION_BARS + 1) : -1].min())
        stop = round_tick(max(base_low - 0.1 * atr14, entry - 2 * atr14), cfg.tick_size, "down")

        risk = entry - stop
        # Measured move: project the consolidation height off the pivot.
        #
        # The 2.5R floor below is an ASSUMPTION, not a measurement. Whenever the
        # base is shorter than 2.5R the floor binds and every candidate reports
        # "2.50R" — which looks like an assessment of opportunity but is the
        # formula restating itself. Both numbers are kept so a reader can tell
        # which one is real: `structural_r` is what the chart actually offers.
        base_high = float(d["high"].iloc[-(CONSOLIDATION_BARS + 1) : -1].max())
        measured_move = base_high - base_low
        structural_r = measured_move / risk if risk > 0 else float("nan")
        # The target is the measured move, full stop. A floor (this previously
        # used max(measured_move, 2.5 * risk)) reports reward the chart does
        # not offer: 12 of 14 live candidates showed "2.50R" while projecting
        # 1.40-2.38R. Setups that project less than `min_structural_r` are
        # rejected in classify() rather than padded up to look acceptable.
        target = entry + measured_move
        ctx.extras["structural_r"] = structural_r

        nearest_above = sw.nearest_overhead_above(entry, ctx.overhead)
        if nearest_above is not None and nearest_above < target:
            target = nearest_above

        r_multiple = (target - entry) / risk if risk > 0 else float("nan")
        plan = TradePlan(
            plan="BO", setup=setup, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=r_multiple, nearest_overhead_above_entry=nearest_above,
        )
        return PlanChoice(plan, None, f"{setup} breakout above {pivot:.2f}")

    def classify(
        self,
        ctx: StockContext,
        result: StrategyResult,
        plan: TradePlan,
        sizing_result,
        earnings_days_away: int | None,
        regime_downgrade_active: bool,
    ) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision(
                "AVOID", "AVOID",
                f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                float("nan"), float("nan"), 0.0,
            )

        if not plan.is_valid:
            return Decision(
                "AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                float("nan"), float("nan"), 0.0,
            )

        risk_pct = plan.risk_per_share / plan.entry * 100
        r_mult = plan.r_multiple
        cap = self.watch_cap(result)
        fired = self.entry_signal_fired(ctx, result)
        earnings_block = earnings_days_away is not None and earnings_days_away <= 15
        reasons: list[str] = []

        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        elif risk_pct > MAX_STOP_PCT or r_mult < self.min_structural_r:
            label = "WATCH_WAIT"
            if risk_pct > MAX_STOP_PCT:
                reasons.append(f"stop {risk_pct:.1f}% > {MAX_STOP_PCT:g}%")
            if r_mult < self.min_structural_r:
                reasons.append(
                    f"base projects {r_mult:.2f}R < {self.min_structural_r:g}R "
                    "— not enough reward for the risk"
                )
        elif cap == "WATCH_WAIT":
            label = "WATCH_WAIT"
            reasons.append(result.watch_notes.get("W2", "capped by watch flag"))
        elif fired and cap == "TRADE_HIGH_CONFIDENCE" and risk_pct <= HIGH_CONF_MAX_STOP_PCT and r_mult >= 2 and not earnings_block:
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(f"{plan.setup} fired on volume, {r_mult:.2f}R")
        else:
            label = "TRADE_ON_TRIGGER"
            if not fired:
                reasons.append("coiled under the pivot, breakout not yet confirmed")
            if cap == "TRADE_ON_TRIGGER":
                active = [c for c in ("W1", "W3") if result.watch_flags.get(c)]
                reasons.append(f"capped by watch flag ({'/'.join(active)})")
            if earnings_block:
                reasons.append(f"earnings in {earnings_days_away}d (blocks HIGH CONFIDENCE)")

        label_after = DOWNGRADE_MAP[label] if regime_downgrade_active else label
        if regime_downgrade_active:
            reasons.append("market-regime downgrade applied")

        return Decision(
            label_before=LABELS[label],
            label_after=LABELS[label_after],
            reason="; ".join(reasons) if reasons else "",
            risk_pct=risk_pct,
            r_multiple=r_mult,
            setup_quality=self.setup_quality(result),
        )

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        pivot = ctx.extras.get("breakout_pivot")
        sr = ctx.extras.get("structural_r")
        return {
            "breakout_pivot": round(pivot, 2) if pivot else None,
            "pct_from_pivot": round((ctx.close / pivot - 1) * 100, 2) if pivot else None,
            # what the base projects — now identical to target_r, kept because
            # it names the thing explicitly
            "structural_r": round(sr, 2) if isinstance(sr, float) and sr == sr else None,
        }

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """For the chart's Trade setups layer, the breakout's whole structure from the live context: the
        advance within the pivot's {BREAKOUT_LOOKBACK}-day window (zone 1), the {CONSOLIDATION_BARS}-bar
        base G4 measures, and the {BREAKOUT_LOOKBACK}-day pivot the close has to clear — the same
        windows evaluate() and build_plans() read, so the boxes are exactly what was judged."""
        d = ctx.daily
        day = lambda ts: str(pd.Timestamp(ts).date())
        out: list[dict] = []
        # the advance into the setup: over the pivot's own window, from its lowest low to the high after it
        span = d.iloc[-(BREAKOUT_LOOKBACK + 1):]
        if len(span) > CONSOLIDATION_BARS:
            lo_day = span["low"].idxmin()
            run = span.loc[lo_day:]
            hi_day = run["high"].idxmax()
            lo, hi = float(span["low"].min()), float(run["high"].max())
            if hi_day > lo_day and lo > 0:
                days = len(span.loc[lo_day:hi_day]) - 1
                out.append({"shape": "line", "from": day(lo_day), "to": day(hi_day), "p0": lo, "p1": hi,
                            "role": "uptrend", "arrow": True, "label": f"+{(hi / lo - 1) * 100:.0f}% in {days} days"})
        prior = d.iloc[-(CONSOLIDATION_BARS + 1): -1]
        if len(prior) == CONSOLIDATION_BARS:
            top, bot = float(prior["high"].max()), float(prior["low"].min())
            atr = float(ctx.atr) if ctx.atr == ctx.atr and ctx.atr else None
            out.append({"shape": "box", "from": day(prior.index[0]), "to": day(prior.index[-1]), "top": top, "bottom": bot,
                        "role": "base", "label": f"base {CONSOLIDATION_BARS} bars" + (f" · {(top - bot) / atr:.1f} ATR" if atr else "")})
        win = d.iloc[-(BREAKOUT_LOOKBACK + 1): -1]
        pivot = ctx.extras.get("breakout_pivot")
        if pivot and len(win):
            out.append({"shape": "level", "from": day(win["high"].idxmax()), "to": day(d.index[-1]), "price": float(pivot),
                        "role": "pivot", "label": f"pivot {pivot:,.2f} · {BREAKOUT_LOOKBACK}-day high"})
        return out

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The 55-day-high pivot the breakout had to clear, plus the shared default (resistance,
        swing low, setup note). The consolidation itself has no stored geometry, so the pivot and
        the note carry the story."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out = super().chart_anatomy(sig)
        if e.get("breakout_pivot"):
            out.append({"shape": "level", "bars": 55, "to": d, "price": float(e["breakout_pivot"]),
                        "role": "pivot", "label": f"pivot {e['breakout_pivot']:g} — highest high of the last 55 days"})
            out.append({"shape": "note", "at": d, "price": float(e["breakout_pivot"]),
                        "text": f"BO setup {d}: new 55-day high out of a tight consolidation; the trigger needs "
                                f"expanding volume. Structural R {e.get('structural_r', '?')} (what the base projects)."})
        return out
