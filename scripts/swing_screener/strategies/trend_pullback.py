"""Trend-continuation strategy — the original system, ported behind the
Strategy interface with its logic unchanged.

Buys pullbacks (TC-01) and tight continuation bases (TC-02) inside an
already-established uptrend. Hard gates (W/T/D) decide whether the uptrend
is real; watch flags (X1-X9) cap confidence without disqualifying.

This file is a faithful move of the former gates.py / entry.py /
decision.classify / screener.passes_loose_filter — the logic was not
rewritten during the extraction, so a recorded golden baseline stays
byte-identical across the refactor. Known defects found during review are
listed in the module docstring of strategies/__init__.py rather than
silently fixed here, so the refactor and the fixes stay separable.
"""

import math

import pandas as pd

from ..core import indicators as ind
from ..core import swings as sw
from ..core import demand_supply as ds_mod
from ..config.base import MarketConfig
from ..core.context import StockContext
from ..screens import criteria
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

TC01 = "S1"   # TC-01
TC02 = "S2"   # TC-02
TC04 = "S4"   # TC-04, numbering kept so old runs still map


def round_tick(value: float, tick: float, direction: str) -> float:
    if tick <= 0:
        return value
    if direction == "up":
        return math.ceil(round(value / tick, 6)) * tick
    return math.floor(round(value / tick, 6)) * tick


class TrendPullbackStrategy(Strategy):
    selection = "time_series"
    version = "1.2"
    changelog = (
        ("1.2", "2026-10-16",
         "Gate, watch and setup codes renamed to one scheme shared by every strategy: G1..Gn for the hard "
         "gates, W1..Wn for the watch flags, S1..Sn for the setups. "
         "The old letters meant nothing and collided across strategies: B1-B4 were minervini's WATCH flags "
         "and breakout's GATES, so one string blocked a trade in the first and merely noted something in "
         "the second. The prefix now states the only thing that matters when reading a drop reason -- "
         "whether the code can stop a trade. No rule changed, but the code tuples are part of the "
         "fingerprint, so this moves the spec id and earlier runs stay under their own versions."
         "The W/T/D gate grouping (weekly, trend, daily) flattens to G1..G14 in evaluation order, so "
         "that grouping now lives only in the docs. TC-01/02/04 become S1/S2/S4 -- the gap is kept "
         "deliberately, so an old run's TC-04 still maps to one setup."),
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
         "v1 baseline of the trend-pullback / continuation strategy."),
    )
    key = "trend_pullback"
    name = "Trend pullback"
    description = (
        "Long pullbacks (TC-01) and tight continuation bases (TC-02) within an "
        "established uptrend, entered on a resumption signal above resistance."
    )
    style = "pullback"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "G12", "G13", "G14")
    screen_key = "uptrend"
    screen_gates = {"G1": "U1", "G2": "U2", "G3": "U3", "G4": "U4", "G5": "U5", "G6": "U6", "G7": "U7", "G8": "U8"}
    watch_codes = ("W1", "W2", "W3", "W4", "W5", "W6", "W7", "W8", "W9")
    setup_codes = (TC01, TC02, TC04)
    setup_names = {TC01: "Pullback", TC02: "Tight base", TC04: "Near the highs"}
    # short names for the chart's checklist; the rules themselves are gate_docs
    gate_titles = {"G1": "Weekly close above the 30-week EMA", "G2": "Weekly 20 above 50", "G3": "Daily 50 above 200",
                   "G4": "Averages not falling", "G5": "Higher swing lows", "G6": "12-1 momentum positive",
                   "G7": "Within 25% of the 52-week high", "G8": "3-month strength", "G9": "No earnings within 10 days",
                   "G10": "Pullback not on rising volume", "G11": "Above the prior swing low",
                   "G12": "No overhead resistance in the way", "G13": "Volatility sane", "G14": "No big gaps"}
    min_bars = 260

    thesis = (
        "A stock already in an established uptrend that pulls back a measured amount, or pauses in a "
        "tight range on light volume, tends to resume the trend. So buy the resumption, not the dip: a "
        "buy-stop above today's high once the stock has closed back up, a stop just under the pullback's "
        "low, and a measured-move target."
    )
    how_it_works = (
        "**The idea.** Wait for a stock in an established uptrend to pull back or pause, then buy only "
        "once it starts up again. The rules come from the strategy's original rule set; each entry below "
        "ends with the rule id it implements there (see the last step).",
        "**1. Pre-screen.** A stock is looked at on a session only when it is liquid enough, its 50-day "
        "average is above its 200-day, and its ADX14 and ATR14 clear the market's minimums (Parameters). "
        "The backtest also needs {min_bars} daily bars.",
        "**2. Gates G1-G14** (Rules). All must pass or the decision is AVOID. G1-G8 are the Established "
        "uptrend screen's criteria U1-U8; G9-G14 are this strategy's own hazards.",
        "**3. Setups** (Rules). {TC01} (a measured pullback) or {TC02} (a tight base) must be present; "
        "the swing points and setup checks they use are in the table above them.",
        "**4. Signal and plan** (Entry, Stop, Target). Today's close must resume upward; the plan is a "
        "buy-stop above today's high, a stop under the setup's low and a measured-move target.",
        "**5. Decision** (Decisions). The plan must risk at most {max_stop_atr_trade} ATR14 and "
        "{max_stop_pct_trade}% of the price, offer at least 2R, and have no watch flag capping it, to be "
        "TRADE - HIGH CONFIDENCE — the only tier the backtest buys.",
        "**6. Exit** (Exit). A fixed bracket: the stop and the target are real orders and never move.",
        "**Timing.** Everything is judged on a session's close. The buy can fill no earlier than the next "
        "session, by buy-stop, and the order waits up to 10 business days.",
        "**Rule ids.** Codes were renamed in v1.2. In the original rule set the gates G1-G2 were W1-W2 "
        "(weekly), G3-G8 were T1-T6 (trend) and G9-G14 were D2-D7 (daily); the watch flags W1-W9 were "
        "X1-X9; the setups {TC01}, {TC02}, {TC04} are TC-01, TC-02, TC-04, with setup checks S-01 to S-05.",
    )
    caveats = (
        "**No demonstrated edge.** The portfolio backtest from 2013 trailed its index by roughly 9 to 11 "
        "points of CAGR a year in both markets (figures in Status); seven alternative exit policies did "
        "not rescue it.",
        "**The tiers do not discriminate.** TRADE - HIGH CONFIDENCE performed no better than TRADE ON "
        "TRIGGER across 484 trades.",
        "**The fixed target caps the upside.** On Micron's 2025 run it would have exited at +36% against "
        "a +484% move.",
        "**Plan B manufactures its R (known defect 1).** It is used exactly when Plan A fails the 2R test. "
        "Its buy level is H with no resistance walk-up, so it can sit just under resistance; and when "
        "Plan A's walk-up has already moved past H, Plan B buys lower, which is where its extra R comes "
        "from.",
        "**Earnings are not backtested.** G9 and the 14-day HIGH CONFIDENCE test need a point-in-time "
        "earnings calendar the backtest does not have, so backtest trades can be held through reports the "
        "live screen would have avoided.",
        "**Two earnings windows (known defect 4).** G9 blocks at 10 or fewer trading days and HIGH "
        "CONFIDENCE at 14 or fewer, for what was written as one rule.",
        "**{TC02}'s window is defined two ways (known defect 3).** The setup checks, the stop and the "
        "target use the last 10 sessions including today; the resumption signal uses the 10 sessions "
        "before today.",
        "**The live sector limit ignores the tier (known defect 5).** It ranks on setup quality, so a "
        "TRADE ON TRIGGER name can push a HIGH CONFIDENCE one in the same sector down to WATCH - SECTOR "
        "LIMIT.",
        "**The fill is not re-checked.** The stop-width and 2R tests use the planned buy level. A "
        "gap up at the fill raises the price paid without moving the stop or the target, so a filled "
        "trade can risk more, and offer less than 2R, than the plan said.",
    )

    # ---------- full reference documentation (Strategy details page) ----------
    # Most thresholds below are bare literals inside evaluate() / _compute_watch_flags() / the
    # swing helpers (core/swings.py) / the uptrend screen (screens/criteria.py), or class
    # attributes (max_stop_*), not constants of this module, so most are written out as numbers.
    # Keep them in sync by hand; adding a module constant here would move the fingerprint.
    status = (
        "No demonstrated edge: portfolio backtest from 2013 with bracket exits (v1.1, "
        "measured 2026-10-13/14 after the cost fix) returned 1.75% CAGR in the US (SPY 12.8%, "
        "max drawdown -46.5%) and 2.30% in India (index 11.7%, max drawdown -32.1%); seven "
        "alternative exit policies did not rescue it."
    )
    gate_docs = {
        "G1": "Weekly close above a 30-week EMA that is itself rising.\n\n"
              "- **Test:** the latest weekly close (this week's bar so far) is above the 30-week "
              "exponential average of weekly closes, and that average is higher than one week "
              "earlier.\n"
              "- **History:** fails with fewer than 31 weekly bars.\n\n"
              "Screen criterion U1.",
        "G2": "Weekly 20-week average above the 50-week average.\n\n"
              "- **Test:** the simple average of the last 20 weekly closes is strictly above that of "
              "the last 50.\n"
              "- **History:** fails with fewer than 50 weekly bars.\n\n"
              "Screen criterion U2.",
        "G3": "Daily 50-day average above the 200-day, and price has not broken down through the "
              "50-day.\n\n"
              "- **Order:** the 50-day simple average is strictly above the 200-day.\n"
              "- **No breakdown:** the close is not more than 2 ATR14 below the 50-day, and the last "
              "5 closes are not all below their day's 50-day.\n"
              "- **History:** fails while the 50-day, the 200-day or ATR14 has no value.\n\n"
              "A close slightly under the 50-day still passes; it raises W2 instead. Screen "
              "criterion U3.",
        "G4": "Neither the 50-day nor the 200-day average is falling.\n\n"
              "- **50-day falling:** more than 1% below its value 10 sessions ago.\n"
              "- **200-day falling:** more than 0.5% below its value 20 sessions ago.\n\n"
              "A flat average passes; a flat 50-day raises W4. Screen criterion U4.",
        "G5": "Higher swing lows over the last 50 sessions.\n\n"
              "- **Two swing lows:** among the swing lows confirmed inside the last 50 sessions (a "
              "low that is the lowest of the 3 sessions either side), the latest is strictly higher "
              "than the one before it.\n"
              "- **Fewer than two:** the lowest low of the last 25 sessions must be above the lowest "
              "low of the 25 before.\n\n"
              "Screen criterion U5.",
        "G6": "Positive 12-1 month momentum: the close 21 sessions ago is above the close 252 "
              "sessions ago.\n\n"
              "- **History:** fails with fewer than 253 daily bars.\n\n"
              "Screen criterion U6.",
        "G7": "Close no more than 25% below the 52-week high.\n\n"
              "- **Test:** the close is at least 75% of the highest high of the last 252 sessions.\n"
              "- **History:** fails while there is no 52-week high (fewer than 20 sessions).\n\n"
              "Screen criterion U7 (its ceiling is the screen's UPTREND_MAX_PCT_BELOW_52W_HIGH).",
        "G8": "Trend not fading: fails only when the 3-month return is negative AND the 50-day "
              "average is flat or falling.\n\n"
              "- **3-month return:** today's close against the close 63 sessions ago.\n"
              "- **Flat or falling:** the 50-day is not higher than 10 sessions ago.\n"
              "- **History:** fails with fewer than 64 daily bars.\n\n"
              "Screen criterion U8.",
        "G9": "No earnings report due within 10 trading days.\n\n"
              "- **Test:** fails when the next earnings date is 10 or fewer trading days away.\n"
              "- **Unknown date:** passes.\n"
              "- **Backtest:** never applied — there is no point-in-time earnings calendar.\n\n"
              "TRADE - HIGH CONFIDENCE uses a different window, 14 trading days (known defect 4).",
        "G10": "The pullback is not on rising volume.\n\n"
               "- **Pullback volume:** the average daily volume of the sessions after H.\n"
               "- **Advance volume:** the average daily volume from L through H, both sessions "
               "included.\n"
               "- **Test:** fails when the pullback average is higher than the advance average. "
               "Passes when H is today (no pullback yet).\n\n"
               "H and L are defined above the setups. {TC01} repeats this test as its check S-04.",
        "G11": "Close not below the prior structural swing low.\n\n"
               "- **Prior swing low:** the last confirmed swing low before H (see the table above "
               "the setups).\n"
               "- **Test:** fails when today's close is below it; passes when there is none.",
        "G12": "No resistance within 3% above the close, unless the only such level is H and a setup "
               "is present.\n\n"
               "- **Resistance levels:** listed in the table above the setups — recent daily, weekly "
               "and monthly swing highs, plus H.\n"
               "- **Within 3%:** a level above the close and no higher than close × 1.03. Levels "
               "already below the close do not count.\n"
               "- **Exception:** when H is the only level in that band, the gate passes if {TC01} or "
               "{TC02} is present — H is the high the setup exists to break.",
        "G13": "Not too volatile: ATR14 no more than 8% of the close.\n\n"
               "- **Test:** fails when ATR14 ÷ close × 100 is above 8. Passes when ATR14 has no "
               "value.",
        "G14": "No unfilled large gap in the last 10 sessions.\n\n"
               "- **Gap:** a session that opened more than 8% above or below the previous close.\n"
               "- **Test:** fails when any of the last 10 sessions gapped and today's close is below "
               "the close just before that gap. So a gap up fails once price falls back under where "
               "it gapped from, and a gap down fails until price has closed back above it.",
    }
    watch_docs = {
        "W1": "Extended: the close is more than 2.5 ATR14 above the 20-day average, or RSI14 is "
              "above 75.\n\n"
              "- **Effect:** caps the decision at WATCH - WAIT; the note gives the 20-day as the "
              "level to wait for.",
        "W2": "The close is below the 50-day average while G3 still passes.\n\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER, and lifts Plan A's level to at "
              "least 0.1% above the 50-day, so its buy-stop sits at least about 0.2% above it.",
        "W3": "Positive: the close is within 1 ATR14 of a rising 50-day average.\n\n"
              "- **Rising:** the 50-day is higher than 10 sessions ago.\n"
              "- **Effect:** adds 1 to setup quality (the ranking score); no cap.",
        "W4": "The 50-day average is flat: not higher than 10 sessions ago, and not more than 1% "
              "lower.\n\n"
              "- **Base:** the last 10 sessions span at most 4.5 ATR14 (highest high minus lowest "
              "low) and the close is at least 90% of the 52-week high. No effect.\n"
              "- **Drift:** anything else. Caps the decision at TRADE ON TRIGGER and subtracts 1 "
              "from setup quality.",
        "W5": "Weak trend strength: ADX14 is at least 15 and below 20.\n\n"
              "- **Base or drift:** judged as in W4. Drift subtracts 1 from setup quality; base has "
              "no effect.\n"
              "- **Never caps** the decision. The pre-screen already wants ADX14 above the market's "
              "minimum (Parameters), so the flag covers the band from that minimum up to 20.",
        "W6": "ADX14 is lower than it was 5 sessions ago.\n\n"
              "- **Healthy pause:** the close is at least 95% of H. No effect.\n"
              "- **Momentum fading:** the close is more than 5% below H and nearer the 50-day than "
              "it was 5 sessions ago. Subtracts 1 from setup quality.\n"
              "- **Otherwise:** noted as falling with no clear fade. No effect.\n\n"
              "Never caps the decision.",
        "W7": "Late move: ADX14 above 40 while W1 (extended) is set.\n\n"
              "- **Effect:** forces Plan A (no switch to Plan B). W1 already caps the decision at "
              "WATCH - WAIT.",
        "W8": "Weak momentum: RSI14 below 40 while the close is above the 50-day average.\n\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER.",
        "W9": "Monthly structure not yet confirmed: the stock is recovering rather than in an "
              "established monthly uptrend.\n\n"
              "- **Raised when any of:** the latest monthly close (this month so far) is not above "
              "its 10-month average; the highest high of the last 12 months is not above that of the "
              "12 months before; the lowest low of the last 12 months is not above that of the 12 "
              "months before.\n"
              "- **History:** never raised with fewer than 24 months.\n"
              "- **Effect:** caps the decision at TRADE ON TRIGGER.\n\n"
              "It was a hard gate in the original rules; as a gate it rejected a genuine recovery as "
              "hard as an ongoing downtrend.",
    }
    pattern_title = "Swing points and setup checks"
    pattern_intro = (
        "The setups and the plan are measured from a few prices on the daily chart:\n\n"
        "- **H:** the highest high of the last 20 sessions, today included — the high the pullback "
        "started from, and the level a resumption has to clear.\n"
        "- **L:** the lowest low of the 40 sessions before H — where the advance into H began.\n"
        "- **P:** the lowest low of the sessions after H — the pullback low (H's own low when H is "
        "today).\n"
        "- **Prior swing low:** the last confirmed swing low before H: a session whose low is the lowest "
        "of the 3 sessions either side.\n"
        "- **Resistance levels:** every daily swing high of the last 252 sessions and weekly swing high "
        "of the last 260 weeks (highest of the 3 bars either side), every monthly swing high in the "
        "whole history (highest of the 2 months either side), and H. A swing high needs its 3 (or 2) "
        "later bars before it counts.\n\n"
        "The setups combine these checks, in this order:"
    )
    pattern_docs = {
        "S-01": "Depth ({TC01}): the drop from H to P is 30% to 60% of the advance H − L, or 1 to 3 ATR14. "
                "Either passes.",
        "S-02": "Recent high ({TC01}): H was set 3 to 10 sessions before today.",
        "S-03": "Structure held: the low is above the prior swing low — P for {TC01}, the lowest low of "
                "the last 10 sessions for {TC02}. Passes when there is no prior swing low.",
        "S-04": "Quiet pullback ({TC01}): not on rising volume — the same test as gate G10.",
        "S-05": "Tight and quiet ({TC02}): the last 10 sessions, today included, span at most 4.5 ATR14 "
                "(highest high minus lowest low), and the 5-day average volume is below the 50-day "
                "average volume.",
    }
    setup_docs = {
        TC01: "Pullback: the stock has pulled back from a high set 3-10 sessions ago by a measured "
              "amount, on no more volume than the advance, and held its structure.\n\n"
              "- **Checks:** S-01 depth, S-02 recent high, S-03 above the prior swing low, S-04 "
              "quiet pullback (table above). All four must pass.\n"
              "- **Priority:** when {TC02} is also present, {TC01} sets the stop and the target.\n\n"
              "Entry-eligible.",
        TC02: "Tight base: the last 10 sessions have traded in a narrow range on below-average "
              "volume, above the prior swing low.\n\n"
              "- **Checks:** S-05 tight and quiet, S-03 above the prior swing low (table above).\n"
              "- **No depth or timing test:** unlike {TC01}, it does not ask how far below H the "
              "base sits or how recent H is.\n\n"
              "Entry-eligible. Its 10-session window is known defect 3.",
        TC04: "Near the highs: the close is within 2% of the 55-session high or of the 52-week "
              "high.\n\n"
              "- **Test:** the close is at least 98% of the highest high of the last 55 sessions, or "
              "of the last 252.\n"
              "- **Effect:** adds 0.5 to setup quality. Never an entry on its own.\n\n"
              "Numbered S4, not S3, so an old run's TC-04 still maps to one setup.",
    }
    entry_rules = (
        "**When a buy is placed.** All 14 gates pass, {TC01} or {TC02} is present, the resumption signal "
        "fired on today's close, and the plan is TRADE - HIGH CONFIDENCE (Decisions). The backtest places "
        "an order only then; a TRADE ON TRIGGER plan is listed by the live screen but not traded.",
        "**Resumption signal.** Today's close is above the 20-day average and above the prior high: "
        "yesterday's high for {TC01}, the highest high of the 10 sessions before today for {TC02}. It also "
        "wants no resistance level within 3% above the close that is more than {own_level_tol_pct}% above "
        "H; once G12 has passed that cannot happen, so G12 is the resistance test in practice.",
        "**Plan A buy level.** Start from today's high ({TC01}) or the highest high of the last 11 "
        "sessions, today included ({TC02}); with W2, lift it to at least 0.1% above the 50-day. Then walk "
        "it up: while a resistance level lies more than 0.1% and no more than about 3.1% above it (above "
        "level × 1.001, up to level × 1.001 × 1.03), move to the highest such level. The buy-stop is 0.1% "
        "above the result, rounded up to the tick.",
        "**Plan B buy level.** 0.1% above H, rounded up to the tick, with no walk-up — so it can sit just "
        "under resistance (known defect 1).",
        "**Which plan.** With W7, always Plan A. Otherwise Plan B when Plan A offers less than 2R and Plan "
        "B at least 2R; else Plan A. Both use the setup's stop and target rules; only the buy level "
        "differs.",
        "**How it fills.** By buy-stop, never on the signal session. From the next session the order "
        "fills on the first session whose high reaches it, at the buy-stop price, or at that session's "
        "open if the stock opens above it (a gap fills worse). Slippage is added to the fill.",
        "**How long it waits.** Up to 10 business days after the signal. In the backtest the order is "
        "cancelled sooner if a session's low reaches the stop while its high stays under the buy level, "
        "and skipped if the fill would be at or above the target. Live, the screen only lists the level; "
        "placing and cancelling the order is the trader's.",
        "**One at a time.** While an order rests or a position is open in a stock, new signals in that "
        "stock are ignored.",
    )
    stop_rules = (
        "**Where it goes.** {TC01}: the pullback low P minus 0.1 ATR14. {TC02}: the lowest low of the last "
        "10 sessions, today included, minus 0.1 ATR14. Rounded down to the tick; the same stop serves Plan "
        "A and Plan B.",
        "**It defines the risk.** Buy level minus stop is the risk per share, 1R. Reward and results are "
        "counted in R.",
        "**How wide it may be.** For TRADE - HIGH CONFIDENCE, the only tier the backtest buys, the risk must "
        "be at most {max_stop_atr_trade} ATR14 and at most {max_stop_pct_trade}% of the buy level. Beyond "
        "{max_stop_atr_wait} ATR14 or {max_stop_pct_wait}% the plan is WATCH - WAIT; in between it is TRADE "
        "ON TRIGGER. Both limits are tested on the planned buy level, not on the fill.",
        "**How it sells.** A standing sell-stop: the first session whose low touches it sells at the stop. "
        "If the stock opens below the stop it sells at that open, so a gap can lose more than 1R. If one "
        "session touches both the stop and the target, the stop is assumed to come first.",
        "**Not on the fill day.** In the portfolio backtest the stop and the target are watched from the "
        "session after the buy fills; a drop through the stop on the fill session itself is not sold that day.",
        "**It never moves.** No breakeven move and no trailing stop.",
    )
    target_rules = (
        "**A real sell order.** In the backtest the target is a resting sell order: the first session "
        "whose high reaches it sells at the target, or at the open if the stock opens above it.",
        "**How it is measured.** {TC01}: P + (H − L), the advance from L to H added again from the "
        "pullback low. {TC02}: the 10-session high plus twice the 10-session range (high minus low, today "
        "included).",
        "**Resistance caps it.** If a resistance level (the table above the setups, H included) lies above "
        "the buy level, the target is lowered to the nearest one. A Plan A buy below H therefore has its "
        "target cut to H, which is often what sends the plan to Plan B.",
        "**The 2R test.** The reward (target − buy level) must be at least 2 times the risk (buy level − "
        "stop); under 2R the plan is WATCH - WAIT and is not traded. Example: buy at 100 with the stop at 95 "
        "risks 5; a target of 110 offers 10, exactly 2R, and passes; 108 offers 1.6R and fails.",
        "**Not re-tested at the fill.** A gap up at the fill raises the price paid without moving the "
        "target, so a filled trade can offer less than 2R. It is skipped only if the fill is at or above "
        "the target.",
    )
    exit_rules = (
        "**Only the stop and the target.** The trade ends when one of them is hit (Stop, Target). Both are "
        "fixed when the plan is made.",
        "**No other exit.** No trailing stop, no time stop, no breakeven move, no sale on a trend break or "
        "on a watch flag. The backtest command adds no exit flags: it runs the default --exit-mode "
        "bracket.",
        "**End of the test.** A position still open on the last day is marked at that day's close (exit "
        "reason OPEN).",
        "**Live.** The screen does not manage open trades; the plan's stop and target are the orders to "
        "place with the buy.",
    )
    sizing_rules = (
        "**Live size.** Risk amount = account size × risk per trade (the high-volatility rate instead when "
        "the market's volatility index is above its threshold). Shares = risk amount ÷ (buy level − stop), "
        "rounded down, then cut so the position is no more than the max position size of the account. "
        "All four values are in Parameters.",
        "**Too large.** If that leaves less than one share, the plan is WATCH - WAIT (\"too large for "
        "account\") and is not traded.",
        "**Backtest size.** The same arithmetic on current equity (cash plus open positions at their last "
        "close) and on the actual fill price including slippage, always at the normal risk rate. If cash is "
        "short it buys what cash allows rather than skipping.",
        "**Costs.** Slippage per side, in basis points, is built into every fill price; the commission per "
        "order is charged on the buy and on the sell (Parameters).",
    )
    filter_rules = (
        "**Earnings due (live only).** Results within 10 trading days fail G9 (AVOID); within 14 they block "
        "TRADE - HIGH CONFIDENCE. The backtest applies neither.",
        "**Supply in control.** The decision is WATCH - WAIT when the demand/supply score is −2 or lower, "
        "live and in the backtest.\n\n"
        "- **Up/down volume, 50 sessions:** volume on up closes ÷ volume on down closes; 1.2 or more adds "
        "1, under 0.8 subtracts 1.\n"
        "- **Accumulation vs distribution, 25 sessions:** a close up (or down) at least 0.2% on higher "
        "volume than the session before; more than one extra accumulation day adds 1, more than one extra "
        "distribution day subtracts 1.\n"
        "- **Pullback vs advance volume:** G10's two averages as a ratio; under 0.8 adds 1, over 1.1 "
        "subtracts 1.",
        "**Market regime (live only).** When the market is risk-off every decision drops one tier (see the "
        "regime note). The backtest does not apply it.",
        "**Sector limit (live only).** At most the per-sector limit of TRADE and TRADE ON TRIGGER names per "
        "sector, ranked by setup quality, then R, then relative strength; the rest become WATCH - SECTOR "
        "LIMIT.",
        "**No free slot (backtest).** With the max open positions held, a triggered order does not fill; it "
        "keeps resting until a slot frees or it expires. When several orders trigger on one session, the "
        "higher setup quality fills first.\n\n"
        "- **Setup quality:** 2 for {TC01} (else 1 for {TC02}), +0.5 for {TC04}, +1 for W3, and −1 each "
        "for W4 drift, W5 drift and W6 momentum fading.",
        "**Pre-screen.** A stock that fails the pre-screen on a session (How it works, step 1) is not "
        "evaluated that session at all.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, {TC01} or {TC02} is present, the resumption signal fired "
                                 "on today's close, no watch flag caps it (W1, W2, W4 drift, W8, W9), the stop "
                                 "is within {max_stop_atr_trade} ATR14 and {max_stop_pct_trade}% of the buy "
                                 "level, the target offers at least 2R, at least one share fits the account, "
                                 "supply is not in control, and no earnings are due within 14 trading days. "
                                 "The only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Gates pass and no WATCH condition applies, but one HIGH CONFIDENCE condition is "
                            "missing: the resumption signal has not fired; W2, W4 drift, W8 or W9 caps it; "
                            "the stop is wider than {max_stop_atr_trade} ATR14 or {max_stop_pct_trade}% (but "
                            "within {max_stop_atr_wait} ATR14 and {max_stop_pct_wait}%); or earnings are 11 "
                            "to 14 trading days away. Also a HIGH CONFIDENCE plan dropped one tier by a "
                            "risk-off market.",
        "WATCH_WAIT": "Gates pass and a setup exists, but the first of these that applies holds it: less "
                      "than one share at the planned size; a stop wider than {max_stop_atr_wait} ATR14 or "
                      "{max_stop_pct_wait}% of the buy level, or a target under 2R; demand/supply reads "
                      "Supply in control; W1 (extended). Also a TRADE ON TRIGGER plan dropped one tier by a "
                      "risk-off market.",
        "AVOID": "A hard gate failed; the reason names the first failing gate. Also a WATCH - WAIT plan "
                 "dropped one tier by a risk-off market. When the gates pass but neither {TC01} nor {TC02} "
                 "is present, the live screen shows NO SETUP instead.",
    }
    param_docs = (
        ("Minimum price", "cfg.screener.min_price",
         "Not applied by this strategy since v1.1, live or in the backtest: on split-adjusted history it "
         "removed the early years of the biggest winners. Only the Screens pages' stock snapshot uses it."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-screen: the 20-day average of close × volume must be at least this, in the market's currency."),
        ("Minimum ADX", "cfg.screener.adx_min",
         "Pre-screen: ADX14 must be strictly above this."),
        ("Minimum ATR %", "cfg.screener.atr_pct_min",
         "Pre-screen: ATR14 as % of the close must be strictly above this."),
        ("Tick size", "cfg.tick_size",
         "The buy level is rounded up and the stop rounded down to this increment."),
        ("Account size", "cfg.account_size",
         "Live sizing, and the backtest's starting equity."),
        ("Risk per trade", "cfg.risk_pct",
         "Fraction of the account (backtest: of current equity) lost if the stop is hit; sets the share count."),
        ("Risk per trade, high volatility", "cfg.risk_pct_high_vol",
         "Live only: used instead of the risk per trade when the volatility index is above the threshold below."),
        ("Volatility threshold", "cfg.vol_threshold",
         "Live: the volatility-index level above which the high-volatility risk rate applies."),
        ("Max position size", "cfg.max_position_pct",
         "Notional cap per position as a fraction of the account (backtest: of equity); can shrink the size."),
        ("Max open positions", "cfg.max_open_positions",
         "Backtest: at most this many positions at once; an order that triggers with no free slot keeps "
         "waiting until it expires."),
        ("Per-sector limit", "cfg.sector_limit_per_sector",
         "Live: at most this many tradeable names kept per sector (ranked by setup quality); the rest become WATCH - SECTOR LIMIT."),
        ("Slippage", "cfg.slippage_bps",
         "Backtest: cost per side in basis points of notional, built into the fill prices."),
        ("Commission", "cfg.commission_per_order",
         "Backtest: charged per order, on the buy and on the sell, in the market's currency."),
    )
    backtest_args = ""

    # ---------- pre-filter ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last["sma50"]) or pd.isna(last["sma200"]) or last["sma50"] <= last["sma200"]:
            return False, "SMA50 <= SMA200"
        if pd.isna(last["adx14"]) or last["adx14"] <= cfg.screener.adx_min:
            return False, f"ADX14 <= {cfg.screener.adx_min}"
        if pd.isna(last["atr_pct"]) or last["atr_pct"] <= cfg.screener.atr_pct_min:
            return False, f"ATR% <= {cfg.screener.atr_pct_min}"
        return True, "passed"

    # ---------- gates / flags / setups ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=(TC01, TC02))
        close = ctx.close

        # M1 (monthly structure) was a hard gate until review showed it
        # penalises a genuine recent recovery as hard as an ongoing
        # downtrend — it is now watch flag W9 below.

        # W1-W2, T1-T6: the Established-uptrend screen's criteria U1-U8 (screens/criteria.py)
        self.apply_screen(ctx, result)

        # D1 retired — extension is now watch flag W1
        result.ok("D1", "retired, see W1")

        # D2: earnings within 10 trading days
        if ctx.earnings_days_away is not None and ctx.earnings_days_away <= 10:
            result.fail("G9", f"earnings in {ctx.earnings_days_away} trading days")
        else:
            result.ok("G9")

        # D3: pullback on rising volume
        if sw.pullback_on_rising_volume(d, ctx.h_index, ctx.l_value):
            result.fail("G10", "pullback volume higher than impulse volume")
        else:
            result.ok("G10")

        # D4: close below the prior structural swing low
        if ctx.prior_swing_low is not None and close < ctx.prior_swing_low:
            result.fail("G11", "close below prior structural swing low")
        else:
            result.ok("G11")

        # D5 needs the setup result, so compute the inputs now and decide below
        near_levels = sw.levels_within_pct_above(close, ctx.overhead, 3.0)
        only_h = near_levels == [round(ctx.h_value, 4)] or (
            len(near_levels) == 1 and abs(near_levels[0] - ctx.h_value) < 1e-6
        )

        # D6: ATR14 above 8% of price
        atr_pct = d["atr_pct"].iloc[-1]
        if pd.notna(atr_pct) and atr_pct > 8:
            result.fail("G13", f"ATR% {atr_pct:.1f} > 8%")
        else:
            result.ok("G13")

        # D7: unheld gap >8% in the last 10 bars
        if sw.gap_not_held(d, 10, 8.0):
            result.fail("G14", "unheld gap >8% in the last 10 bars")
        else:
            result.ok("G14")

        self._compute_setups(ctx, result)

        if near_levels and not (only_h and (result.setups[TC01] or result.setups[TC02])):
            result.fail("G12", f"overhead level(s) within 3%: {near_levels}")
        else:
            result.ok("G12")

        result.recompute_first_fail()
        self._compute_watch_flags(ctx, result)
        return result

    def _compute_setups(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        atr14 = d["atr14"].iloc[-1]
        close = ctx.close
        h, l, p = ctx.h_value, ctx.l_value, ctx.p_value
        bars_since_h = (len(d) - 1) - d.index.get_loc(ctx.h_index)

        impulse = h - l
        depth_price = h - p
        pct_depth = depth_price / impulse if impulse > 0 else float("nan")
        atr_depth = depth_price / atr14 if atr14 and not pd.isna(atr14) else float("nan")

        s01 = (0.30 <= pct_depth <= 0.60) or (1 <= atr_depth <= 3)
        s02 = 3 <= bars_since_h <= 10
        s03_tc01 = ctx.prior_swing_low is None or p > ctx.prior_swing_low
        s04 = not sw.pullback_on_rising_volume(d, ctx.h_index, ctx.l_value)
        result.setups[TC01] = bool(s01 and s02 and s03_tc01 and s04)

        low_10 = d["low"].iloc[-10:].min()
        high_10 = d["high"].iloc[-10:].max()
        s03_tc02 = ctx.prior_swing_low is None or low_10 > ctx.prior_swing_low
        range_10 = high_10 - low_10
        vol_5d = d["volume"].iloc[-5:].mean()
        vol_sma50 = d["vol_sma50"].iloc[-1]
        s05 = (
            atr14
            and not pd.isna(atr14)
            and range_10 <= 4.5 * atr14
            and pd.notna(vol_sma50)
            and vol_5d < vol_sma50
        )
        result.setups[TC02] = bool(s03_tc02 and s05)

        high_55 = d["high"].iloc[-55:].max()
        high_252 = d["high_252"].iloc[-1]
        result.setups[TC04] = bool(
            close >= high_55 * 0.98 or (pd.notna(high_252) and close >= high_252 * 0.98)
        )

    def _compute_watch_flags(self, ctx: StockContext, result: StrategyResult) -> None:
        d = ctx.daily
        close = ctx.close
        sma20 = d["sma20"].iloc[-1]
        sma50 = d["sma50"].iloc[-1]
        atr14 = d["atr14"].iloc[-1]
        rsi14 = d["rsi14"].iloc[-1]
        adx14 = d["adx14"].iloc[-1]

        # X1: extended
        extended = False
        if pd.notna(sma20) and pd.notna(atr14) and atr14:
            extended = (close - sma20) > 2.5 * atr14
        if pd.notna(rsi14) and rsi14 > 75:
            extended = True
        result.watch_flags["W1"] = bool(extended)
        if extended:
            target = sma20 if pd.notna(sma20) else None
            result.watch_notes["W1"] = (
                f"extended; pullback target ~{target:.2f}" if target else "extended"
            )

        # X2: below SMA50 but within T1's tolerance
        below_50 = pd.notna(sma50) and close < sma50 and result.hard_gates.get("G3", False)
        result.watch_flags["W2"] = bool(below_50)

        # X3: at a rising SMA50 (positive flag)
        sma50_state = criteria.sma50_state(ctx)
        at_rising_50 = (
            pd.notna(sma50)
            and pd.notna(atr14)
            and atr14
            and abs(close - sma50) <= atr14
            and sma50_state == "rising"
        )
        result.watch_flags["W3"] = bool(at_rising_50)

        # X4: flat SMA50 -> base or drift
        flat_50 = sma50_state == "flat"
        result.watch_flags["W4"] = bool(flat_50)
        if flat_50:
            result.watch_notes["W4"] = sw.base_or_drift(d, atr14, d["high_252"].iloc[-1])

        # X5: low ADX (15-20) -> base or drift
        low_adx = pd.notna(adx14) and 15 <= adx14 < 20
        result.watch_flags["W5"] = bool(low_adx)
        if low_adx:
            result.watch_notes["W5"] = sw.base_or_drift(d, atr14, d["high_252"].iloc[-1])

        # X6: ADX falling
        adx_falling = ind.is_falling(d["adx14"], 5, 0.0)
        result.watch_flags["W6"] = bool(adx_falling)
        if adx_falling:
            if close >= ctx.h_value * 0.95:
                result.watch_notes["W6"] = "healthy pause near H"
            else:
                dist_now = abs(close - sma50) if pd.notna(sma50) else float("nan")
                sma50_5ago = d["sma50"].iloc[-6] if len(d) > 5 else float("nan")
                close_5ago = d["close"].iloc[-6] if len(d) > 5 else float("nan")
                dist_5ago = (
                    abs(close_5ago - sma50_5ago)
                    if pd.notna(sma50_5ago) and pd.notna(close_5ago)
                    else float("nan")
                )
                fading = pd.notna(dist_now) and pd.notna(dist_5ago) and dist_now < dist_5ago
                result.watch_notes["W6"] = (
                    "momentum fading toward SMA50" if fading else "falling, no clear fade"
                )

        # X7: late move — ADX>40 together with X1
        result.watch_flags["W7"] = bool(
            pd.notna(adx14) and adx14 > 40 and result.watch_flags["W1"]
        )

        # X8: weak momentum — RSI<40 while close above SMA50
        result.watch_flags["W8"] = bool(
            pd.notna(rsi14) and rsi14 < 40 and pd.notna(sma50) and close > sma50
        )

        # X9: monthly structure not yet confirmed (former hard gate M1)
        m = ctx.monthly
        if ctx.history_months < 24 or len(m) < 24 or pd.isna(m["sma10"].iloc[-1]):
            result.watch_flags["W9"] = False
        else:
            above_sma10 = m["close"].iloc[-1] > m["sma10"].iloc[-1]
            last12_high = m["high"].iloc[-12:].max()
            prior12_high = m["high"].iloc[-24:-12].max()
            last12_low = m["low"].iloc[-12:].min()
            prior12_low = m["low"].iloc[-24:-12].min()
            reasons = []
            if not above_sma10:
                reasons.append("monthly close below 10mo SMA")
            if last12_high <= prior12_high:
                reasons.append(f"high not above prior year ({last12_high:.2f} vs {prior12_high:.2f})")
            if last12_low <= prior12_low:
                reasons.append(f"low not above prior year ({last12_low:.2f} vs {prior12_low:.2f})")
            result.watch_flags["W9"] = bool(reasons)
            if reasons:
                result.watch_notes["W9"] = (
                    "monthly structure not yet confirmed: " + "; ".join(reasons)
                )

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("W1"):
            caps.append("WATCH_WAIT")
        if result.watch_flags.get("W2"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("W4") and result.watch_notes.get("W4") == "drift":
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("W8"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("W9"):
            caps.append("TRADE_ON_TRIGGER")
        if not caps:
            return "TRADE_HIGH_CONFIDENCE"
        return min(caps, key=CAP_ORDER.index)

    def setup_quality(self, result: StrategyResult) -> float:
        score = 2.0 if result.setups.get(TC01) else (1.0 if result.setups.get(TC02) else 0.0)
        if result.setups.get(TC04):
            score += 0.5
        if result.watch_flags.get("W3"):
            score += 1.0
        if result.watch_flags.get("W4") and result.watch_notes.get("W4") == "drift":
            score -= 1.0
        if result.watch_flags.get("W5") and result.watch_notes.get("W5") == "drift":
            score -= 1.0
        if (
            result.watch_flags.get("W6")
            and result.watch_notes.get("W6") == "momentum fading toward SMA50"
        ):
            score -= 1.0
        return score

    # ---------- entry geometry ----------

    def active_setup(self, result: StrategyResult) -> str | None:
        """If both TC-01 and TC-02 are valid, TC-01 sets the stop and target."""
        if result.setups.get(TC01):
            return TC01
        if result.setups.get(TC02):
            return TC02
        return None

    def _resumption_signal(self, ctx: StockContext, setup: str) -> bool:
        d = ctx.daily
        sma20 = d["sma20"].iloc[-1]
        if sma20 != sma20:  # NaN
            return False
        ref_high = d["high"].iloc[-11:-1].max() if setup == TC02 else d["high"].iloc[-2]
        return bool(ctx.close > ref_high and ctx.close > sma20)

    # H -- the high the pullback started from -- is itself in ctx.overhead,
    # but H is the level this setup exists to break THROUGH. Counting it as
    # resistance is a catch-22: the closer price gets to triggering, the more
    # certainly the signal is suppressed. Measured over 2025-26, 31 of 31
    # otherwise-valid momentum entries were blocked, and in all 31 the
    # blocking level WAS H. Only genuine structure above H should block.
    own_level_tol_pct: float = 0.5

    # Stop distance is capped in ATRs, not in percent of price.
    #
    # The old caps (<=7% for TRADE, >8% -> WATCH_WAIT) were a volatility
    # filter wearing a risk label: because stop = P - 0.1*ATR and entry sits
    # near H, risk% is essentially the pullback depth, so a high-ATR stock
    # mechanically fails them no matter how well-placed the stop is. Measured
    # over 2025-26, 10 of 11 surviving momentum signals died on risk%>7 --
    # yet in ATR terms (0.84-2.91 ATR for trades actually taken) the rejects
    # sat in the SAME range: MU 2.53, TSM 2.36, AMD 1.93 ATR, tighter than
    # accepted trades like SAP 2.91 or CMI 2.80.
    #
    # Dollar risk per trade is already controlled by position sizing, which
    # buys fewer shares as the stop widens -- so admitting a wider percentage
    # stop does not increase risk taken; it only stops discarding volatile
    # leaders. Thresholds come from that measured range: 3.0 just above the
    # widest stop the system actually traded, 3.5 as the hard ceiling.
    max_stop_atr_trade: float = 3.0
    max_stop_atr_wait: float = 3.5

    # The ATR cap alone is NOT sufficient. It asks "is the stop sane for this
    # stock's volatility" -- a different question from "is the 2R target
    # reachable in a swing-trade timeframe". Measured cases where they
    # diverge: SWVL sat at 2.05 ATR but 27.5% of price, so with R>=2 enforced
    # the target needs a 55% move; ITGR was 4.5% of price but 13.5 ATR, a
    # stop absurdly wide for its own volatility. Both caps are therefore
    # kept, each guarding its own failure mode.
    #
    # 12% follows from the timeframe: a stop of X% needs a >=2X% move to pay
    # 2R, and ~24% is the top of what a multi-week swing plausibly delivers.
    # It admits the volatile leaders this strategy was wrongly excluding
    # (AMD 7.2%, TSM 7.6-9.1%, AVGO 8.5%, MU 10.9%) while still rejecting
    # SNDK 20.9%, MRVL 18.4% and SWVL 27.5%.
    max_stop_pct_trade: float = 12.0
    max_stop_pct_wait: float = 15.0

    def stop_atr_multiple(self, ctx: StockContext, plan: TradePlan) -> float:
        """Stop distance expressed in current ATRs (NaN if ATR unavailable)."""
        atr14 = float(ctx.daily["atr14"].iloc[-1])
        if not atr14 or atr14 != atr14:
            return float("nan")
        return plan.risk_per_share / atr14

    def blocking_overhead(self, ctx: StockContext) -> list[float]:
        """Overhead levels close enough above price to veto an entry,
        excluding the setup's own origin high."""
        near = sw.levels_within_pct_above(ctx.close, ctx.overhead, 3.0)
        ceiling = ctx.h_value * (1 + self.own_level_tol_pct / 100)
        return [lv for lv in near if lv > ceiling]

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        setup = self.active_setup(result)
        if setup is None:
            return False
        blocked = self.blocking_overhead(ctx)
        return bool(self._resumption_signal(ctx, setup) and not blocked)

    def _compute_trigger(self, ctx: StockContext, result: StrategyResult, setup: str) -> float:
        d = ctx.daily
        last_high = float(d["high"].iloc[-1])
        ref = max(last_high, float(d["high"].iloc[-11:-1].max())) if setup == TC02 else last_high

        trigger = ref
        if result.watch_flags.get("W2"):
            sma50 = d["sma50"].iloc[-1]
            if sma50 == sma50:
                trigger = max(trigger, float(sma50) * 1.001)

        for _ in range(50):  # hard cap; overhead list is finite
            near = sw.levels_within_pct_above(trigger * 1.001, ctx.overhead, 3.0)
            if not near:
                break
            highest = max(near)
            if highest <= trigger:
                break
            trigger = highest
        return trigger

    def _stop_target(self, ctx: StockContext, setup: str) -> tuple[float, float]:
        d = ctx.daily
        atr14 = float(d["atr14"].iloc[-1])
        if setup == TC01:
            return ctx.p_value - 0.1 * atr14, ctx.p_value + (ctx.h_value - ctx.l_value)
        low_10 = float(d["low"].iloc[-10:].min())
        high_10 = float(d["high"].iloc[-10:].max())
        return low_10 - 0.1 * atr14, high_10 + 2 * (high_10 - low_10)

    def _build_plan(
        self, ctx: StockContext, result: StrategyResult, tick_size: float, which: str
    ) -> TradePlan | None:
        setup = self.active_setup(result)
        if setup is None:
            return None

        raw_stop, raw_target = self._stop_target(ctx, setup)
        trigger = (
            self._compute_trigger(ctx, result, setup) if which == "A" else ctx.h_value
        )

        entry = round_tick(trigger * 1.001, tick_size, "up")
        stop = round_tick(raw_stop, tick_size, "down")

        nearest_above = sw.nearest_overhead_above(entry, ctx.overhead)
        target = raw_target
        if nearest_above is not None and nearest_above < target:
            target = nearest_above

        risk_per_share = entry - stop
        reward_per_share = target - entry
        r_multiple = reward_per_share / risk_per_share if risk_per_share > 0 else float("nan")

        return TradePlan(
            plan=which, setup=setup, entry=entry, stop=stop, target=target,
            risk_per_share=risk_per_share, reward_per_share=reward_per_share,
            r_multiple=r_multiple, nearest_overhead_above_entry=nearest_above,
        )

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        plan_a = self._build_plan(ctx, result, cfg.tick_size, "A")
        if plan_a is None:
            return PlanChoice(None, None, "no active setup")
        plan_b = self._build_plan(ctx, result, cfg.tick_size, "B")

        if result.watch_flags.get("W7"):
            return PlanChoice(plan_a, plan_b, "X7 late move: Plan A (pullback) preferred")
        if plan_a.r_multiple < 2 and plan_b is not None and plan_b.r_multiple >= 2:
            return PlanChoice(plan_b, plan_a, "Plan A capped below 2R, Plan B (breakout) used instead")
        return PlanChoice(plan_a, plan_b, "Plan A (pullback)")

    # ---------- decision ----------

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
            reason = f"fails hard gate {code}: {result.hard_notes.get(code, '')}"
            return Decision("AVOID", "AVOID", reason, float("nan"), float("nan"), 0.0)

        ds = ds_mod.compute(ctx)
        risk_pct = plan.risk_per_share / plan.entry * 100 if plan.entry else float("nan")
        stop_atr = self.stop_atr_multiple(ctx, plan)
        r_mult = plan.r_multiple
        sig = self.entry_signal_fired(ctx, result)
        cap = self.watch_cap(result)
        supply_blocks = ds.verdict == "Supply in control"
        earnings_block_15 = earnings_days_away is not None and earnings_days_away < 15

        reasons: list[str] = []

        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        elif (
            stop_atr > self.max_stop_atr_wait
            or risk_pct > self.max_stop_pct_wait
            or r_mult < 2
        ):
            label = "WATCH_WAIT"
            if stop_atr > self.max_stop_atr_wait:
                reasons.append(
                    f"stop {stop_atr:.2f} ATR > {self.max_stop_atr_wait} ATR "
                    f"({risk_pct:.1f}% of price)"
                )
            if risk_pct > self.max_stop_pct_wait:
                reasons.append(f"stop {risk_pct:.1f}% > {self.max_stop_pct_wait}% of price")
            if r_mult < 2:
                reasons.append(f"target {r_mult:.2f}R < 2R")
        elif supply_blocks:
            label = "WATCH_WAIT"
            reasons.append(f"demand/supply: {ds.verdict} ({ds.supports_demand_text})")
        elif cap == "WATCH_WAIT":
            label = "WATCH_WAIT"
            reasons.append(result.watch_notes.get("W1", "extended (X1)"))
        elif (
            sig
            and cap == "TRADE_HIGH_CONFIDENCE"
            and stop_atr <= self.max_stop_atr_trade
            and risk_pct <= self.max_stop_pct_trade
            and r_mult >= 2
            and not earnings_block_15
        ):
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(f"{plan.setup} signal fired, {r_mult:.2f}R")
        else:
            label = "TRADE_ON_TRIGGER"
            if not sig:
                reasons.append("entry trigger not yet fired")
            if cap == "TRADE_ON_TRIGGER":
                capping = [
                    code for code in ("W2", "W4", "W8", "W9")
                    if result.watch_flags.get(code)
                    and (code != "W4" or result.watch_notes.get("W4") == "drift")
                ]
                reasons.append(f"capped by watch flag ({'/'.join(capping)})")
            if earnings_block_15:
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
        ds = ds_mod.compute(ctx)
        return {
            "demand_supply": f"{ds.verdict} ({ds.supports_demand_text})",
            "h_pct_above_close": round(ind.pct_distance(ctx.h_value, ctx.close), 1),
            "monthly": "recovering" if result.watch_flags.get("W9") else "up",
            "weekly": (
                "up"
                if result.hard_gates.get("G1") and result.hard_gates.get("G2")
                else "down"
            ),
        }

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """For the chart's Trade setups layer: the advance L -> H (zone 1), the pullback H -> P against
        the 30-60% retracement band TC-01 tests, H as the resumption level, the prior swing low the stop
        belongs under, and TC-02's tight 10-bar base when that is the setup. L and P are located by
        their values from the shared swing code (impulse_low, pullback_low), never re-derived."""
        d = ctx.daily
        day = lambda ts: str(pd.Timestamp(ts).date())
        h, l, pv, hi_day = ctx.h_value, ctx.l_value, ctx.p_value, ctx.h_index
        if hi_day is None or not h or not l:
            return self.chart_anatomy(sig)
        before, after = d.loc[:hi_day], d.loc[hi_day:]
        l_hits = before.index[before["low"] == l]
        p_hits = after.index[after["low"] == pv]
        out: list[dict] = []
        impulse = h - l
        if len(l_hits) and impulse > 0:
            out.append({"shape": "line", "from": day(l_hits[-1]), "to": day(hi_day), "p0": float(l), "p1": float(h),
                        "role": "uptrend", "arrow": True, "label": f"+{impulse / l * 100:.0f}% advance"})
        if len(p_hits) and impulse > 0 and pv < h:
            depth = (h - pv) / impulse
            out.append({"shape": "line", "from": day(hi_day), "to": day(p_hits[0]), "p0": float(h), "p1": float(pv),
                        "role": "contraction", "label": f"pullback {depth:.0%} of the advance"})
            out.append({"shape": "box", "from": day(hi_day), "to": day(d.index[-1]), "top": float(h - 0.30 * impulse),
                        "bottom": float(h - 0.60 * impulse), "role": "tight", "label": "30-60% retracement"})
        out.append({"shape": "level", "from": day(hi_day), "to": day(d.index[-1]), "price": float(h), "role": "pivot",
                    "label": f"H {h:,.2f} — the resumption level"})
        if ctx.prior_swing_low:
            out.append({"shape": "level", "bars": 60, "to": day(d.index[-1]), "price": float(ctx.prior_swing_low),
                        "role": "support", "label": "prior swing low — the stop belongs under it"})
        if result.setups.get(TC02):
            last = d.iloc[-10:]
            out.append({"shape": "box", "from": day(last.index[0]), "to": day(last.index[-1]), "top": float(last["high"].max()),
                        "bottom": float(last["low"].min()), "role": "base", "label": "tight 10-bar base"})
        return out

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The default anatomy (H resistance, prior swing low) is already this strategy's story;
        add which pullback setup fired and the watch context."""
        out = super().chart_anatomy(sig)
        active = [k for k, v in (sig.get("setups") or {}).items() if v]
        names = {"TC-01": "pullback to support in an uptrend", "TC-02": "tight continuation base",
                 "TC-04": "higher-low reversal"}
        if active:
            what = "; ".join(f"{c} — {names.get(c, c)}" for c in active)
            out = [s for s in out if s["shape"] != "note"]
            out.append({"shape": "note", "at": str(sig["date"]), "price": sig.get("h_value"),
                        "text": f"Setup {what}. Entry goes above the resumption level H {sig.get('h_value'):.2f}; "
                                f"the stop belongs under the prior swing low."})
        return out
