"""Screens as conditions over the stock snapshot — the built-in ones and the ones you create.

A screen definition is a list of conditions, all of which must hold:

    {"field": "close", "op": ">", "value": 10}                      a field against a number
    {"field": "close", "op": ">=", "ref": "high_252", "mult": 0.85}  a field against another field × factor
    {"field": "weekly_uptrend", "op": "is", "value": true}          a yes/no field
    {"field": "sector", "op": "in", "value": ["Technology"]}        a text field against a list

Evaluated with pandas over a snapshot (screens/snapshot.py): a query, not a job. Missing values never
pass (a stock without a 200-day average is not "above" it).

The built-in screens are generated from the same constants as their coded criteria (screens/criteria.py),
and tests/test_screen_definitions.py proves each returns exactly the stocks its coded criteria pass.
Your own screens are stored in Postgres (`user_screens`).
"""

import json

import numpy as np
import pandas as pd

from ..marketdata import db
from . import criteria as c
from .snapshot import (BASE_MAX_DAYS, HIGH_BARS, LEAD_HIGH_BARS, MDD_BARS, PIVOT_BARS, R2Y_BARS, RANGE_PRIOR_BARS,
                       RANGE_RECENT_BARS, STAGE2_DAYS_WINDOW, VOLUME_RECENT_BARS)

OPS = (">", ">=", "<", "<=", "=", "!=", "is", "in")


def builtin() -> dict[str, dict]:
    T = {"field": "tradable", "op": "is", "value": True}
    return {
        "stage2": {"name": "Stage 2 — Trend Template", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma50"},
            {"field": "close", "op": ">", "ref": "sma150"},
            {"field": "close", "op": ">", "ref": "sma200"},
            {"field": "sma50", "op": ">", "ref": "sma150"},
            {"field": "sma150", "op": ">", "ref": "sma200"},
            {"field": "sma200", "op": ">", "ref": "sma200_21d_ago"},
            {"field": "pct_above_low", "op": ">=", "value": c.MIN_PCT_ABOVE_52W_LOW},
            {"field": "pct_below_high", "op": "<=", "value": c.MAX_PCT_BELOW_52W_HIGH},
            {"field": "rs_rank", "op": ">=", "value": c.RS_MIN_RANK},
        ]},
        "uptrend": {"name": "Established uptrend", "conditions": [
            T,
            {"field": "weekly_uptrend", "op": "is", "value": True},
            {"field": "weekly_ma_aligned", "op": "is", "value": True},
            {"field": "holding_50d", "op": "is", "value": True},
            {"field": "mas_not_falling", "op": "is", "value": True},
            {"field": "higher_swing_lows", "op": "is", "value": True},
            {"field": "momentum_positive", "op": "is", "value": True},
            {"field": "close", "op": ">=", "ref": "high_252", "mult": c.UPTREND_MIN_FRAC_OF_52W_HIGH},
            {"field": "trend_not_fading", "op": "is", "value": True},
        ]},
        "near_highs": {"name": "Near highs, rising 200-day", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma200"},
            {"field": "sma200_not_falling", "op": "is", "value": True},
            {"field": "close", "op": ">=", "ref": "high_252", "mult": c.NEAR_HIGHS_MIN_FRAC_OF_52W_HIGH},
        ]},
        "above_200": {"name": "Above the 200-day", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma200"},
        ]},
        "big_movers": {"name": "Big movers", "conditions": [
            T,
            {"field": "adr_pct", "op": ">=", "value": c.MOVERS_MIN_ADR_PCT},
            {"field": "prior_move_pct", "op": ">=", "value": c.MOVERS_MIN_MOVE_PCT},
        ]},
    }


# Presets: built-in screens defined by conditions alone (no coded twin in screens/criteria.py — the
# strategies do not use them). Thresholds are constants so the text below stays true.
LEADER_GROUP_RS = 80     # the peer group's RS rating (Sectors page)
LEADER_MIN_RS = 70       # the stock's own RS rank
# No "top N in its group" condition: the group-strength study (research/group-strength-study.md) found the
# stock's rank inside its group added nothing in either market — the group's strength is what matters.


EARLY_STAGE2_MAX_DAYS = 40   # Trend Template held on at most this many of the last ~6 months' sessions (snapshot.STAGE2_DAYS_WINDOW)
MATURE_SMA200_MIN_DAYS = 84  # the 200-day has passed the Trend Template's rising test (C5) this many sessions running: about four months

LONG_BASE_MIN_DAYS = 120          # sessions in the base (about six months)
LONG_BASE_MAX_DEPTH_PCT = 30.0    # the base's high-to-low depth; no looser than snapshot.BASE_MAX_DEPTH_PCT, where base_days stops
LONG_BASE_MAX_PCT_BELOW_HIGH = 10.0  # the close this close to the top of the base
LONG_BASE_MIN_QUALITY = 60        # Quality score (fundamentals/quality.py), present-only

# Forming a base: a Stage 2 stock resting under its high. Base length and depth follow Minervini's published
# ranges (a base of about 5 weeks or more; corrections deeper than about 35% are suspect outside a bear market);
# the range and volume cutoffs are this screen's own, set so it returns a watchlist rather than hundreds.
BASE_FORMING_MIN_DAYS = 25               # sessions without a new 52-week high: about five weeks
BASE_FORMING_MAX_DEPTH_PCT = 35.0        # the correction from that high, at its deepest
BASE_FORMING_MIN_DEPTH_PCT = 5.0         # … and at least this: a stock that barely moves for weeks is pinned to a takeover price
BASE_FORMING_MAX_PCT_BELOW_HIGH = 15.0   # the close back in the upper part of the base
BASE_FORMING_MAX_RANGE_RATIO = 0.6       # the latest range at most this fraction of the one before it
BASE_FORMING_MAX_VOLUME_RATIO = 1.0      # recent volume under the 50-day average

BEAR_LEADER_MIN_REL_RETURN = 30.0   # rel_r2y: beat the market benchmark by this many points over two years
BEAR_LEADER_MAX_DRAWDOWN = 35.0      # mdd_2y no deeper than this: it held up through the decline
BEAR_LEADER_MAX_PCT_BELOW_HIGH = 25.0  # still near its 52-week high, not a past winner fading
BEAR_LEADER_MIN_RS = 80              # still a leader today
BEAR_LEADER_MIN_ROE = 15.0           # fundamentals (present-only): trailing-twelve-month ROE, %
BEAR_LEADER_MIN_EPS_GROWTH = 20.0    # latest quarter's EPS vs a year earlier, %
BEAR_LEADER_MIN_SALES_GROWTH = 15.0  # latest quarter's sales vs a year earlier, %

# Growth and recovery: two screens, not one with an "or" — screen conditions are all ANDed. Fundamentals
# are present-only (screens/snapshot.py), so neither can be studied on past snapshots.
GROWTH_VERDICTS = ["LEADER", "ACCEPTABLE"]   # fundamentals/sepa.py verdicts that count as growing
RECOVERY_MIN_IMPROVING_QUARTERS = 2  # EPS above the year-ago quarter for at least this many quarters running
RECOVERY_MIN_SALES_GROWTH = 10.0     # latest quarter's sales vs a year earlier, %: the profit is not cost cuts alone


# Breakout watch: the rule the breakout anticipation study froze on 2017-2021 and checked once on 2022-2026
# (research/breakout-anticipation-study.md, analytics/breakout_study.py). Change a number here and the study's
# figures no longer describe the screen: re-run the study, not just the screen.
BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT = 5.0    # the close at most this far under the 55-session pivot (and not above it)
BREAKOUT_WATCH_MIN_FRAC_OF_52W_HIGH = 0.90  # the close within 10% of the 52-week high
BREAKOUT_WATCH_MIN_GROUP_RS = 70            # the industry group's RS rating
# Only where it held out of sample: in India the same rule scored a lift of ~1.0 on 2022-2026.
BREAKOUT_WATCH_MARKETS = ("us",)


def presets() -> dict[str, dict]:
    stage2 = builtin()["stage2"]["conditions"]
    return {
        "early_stage2": {
            "name": "Stage 2 — just started",
            "description": f"Stocks that pass the full Trend Template today but held it on no more than {EARLY_STAGE2_MAX_DAYS} of "
                           f"the last {STAGE2_DAYS_WINDOW} sessions — new to Stage 2, or back in it after a correction. "
                           "A list for finding them, not a stronger screen: in the study they did no better than the Trend Template.",
            "thesis": ("Weinstein and Minervini both prefer a stock as it leaves its Stage 1 base and turns into Stage 2, with the "
                       "advance ahead of it rather than months behind. This screen is the Trend Template plus how long it has "
                       "been in force: few sessions out of the last six months means the stock entered Stage 2 recently, or "
                       "re-entered after a correction — the field cannot tell the two apart. The month-end study (2021–2026) "
                       "does not support the preference. In the US the fresher the stock the weaker its forward returns: at "
                       "this cutoff it lagged the full Trend Template at 1, 3 and 6 months, and stocks in it longer did best. "
                       "In India it beat the Trend Template at 3 and 6 months but lagged at 1 month, on about 15 stocks a "
                       "month, which is too few to call; neither market showed a higher hit rate. Use it to see who just "
                       "turned up, and judge the setup on its own."),
            "conditions": [*stage2, {"field": "stage2_days", "op": "<=", "value": EARLY_STAGE2_MAX_DAYS}]},
        "stage2_mature_sma200": {
            "name": "Stage 2 — mature 200-day",
            "description": (f"The full Trend Template, with the 200-day rising for at least {MATURE_SMA200_MIN_DAYS} sessions in a row "
                            f"(about four months), not just higher than {c.SMA200_RISING_BARS} sessions ago."),
            "thesis": ("Minervini's Trend Template asks for a 200-day that has been trending up for at least a month, and prefers four "
                       "to five months or longer. He reads the line by eye and gives no formula. The built-in Stage 2 screen tests the "
                       f"minimum: the 200-day higher than {c.SMA200_RISING_BARS} sessions ago. Comparing only two endpoints months "
                       "apart would let a line that rolled over or bottomed in a V pass, so this screen counts how many sessions in "
                       "a row that one-month test has held (the field 200-day rising for). A line that fell for about a month resets "
                       "the count. A flat line drifting up very slowly still counts: neither Minervini nor Weinstein gives a slope "
                       "that separates flat from rising. Weinstein prefers the opposite end — buying as the 30-week line turns up — "
                       "which is the Stage 2 — just started screen. Not yet studied."),
            "conditions": [*stage2, {"field": "sma200_rising_days", "op": ">=", "value": MATURE_SMA200_MIN_DAYS}]},
        "base_forming": {
            "name": "Base — forming in Stage 2",
            "description": (f"Stocks above a rising 200-day (and the 150-day above it) that have gone {BASE_FORMING_MIN_DAYS}+ "
                            f"sessions without a new 52-week high, corrected {BASE_FORMING_MIN_DEPTH_PCT:g}–"
                            f"{BASE_FORMING_MAX_DEPTH_PCT:g}% from it "
                            f"and sit within {BASE_FORMING_MAX_PCT_BELOW_HIGH:g}% of it, with the last {RANGE_RECENT_BARS} "
                            f"sessions' range at most {BASE_FORMING_MAX_RANGE_RATIO:g}× the {RANGE_PRIOR_BARS} before and "
                            "volume under its 50-day average. A watchlist of bases still forming, not a buy signal."),
            "thesis": ("Minervini and Weinstein buy a Stage 2 stock as it leaves a base, so the work is to have the base on a "
                       "watchlist before it ends. A base starts at a high the stock has not beaten since; Minervini's run from "
                       "about five weeks to over a year, and a correction much deeper than about a third is suspect outside a "
                       f"bear market. A correction under {BASE_FORMING_MIN_DEPTH_PCT:g}% is left out: a stock that sits at "
                       "one price for weeks is usually waiting on a takeover, not building a base. As a base matures the swings narrow and volume dries up: sellers are running out. This "
                       "screen approximates that from the daily snapshot. The base is measured from the 52-week high, so it "
                       f"stops at {HIGH_BARS - 1} sessions. Tightening is the latest {RANGE_RECENT_BARS} sessions' high-to-low "
                       f"range against the {RANGE_PRIOR_BARS} before them, and dry-up is {VOLUME_RECENT_BARS}-session volume "
                       "against the 50-day. It is not a detected VCP or flat base: no strategy's detector runs, there is no "
                       "pivot, and a stock rolling over can pass on a quiet fortnight. Read each chart. The breakout "
                       "anticipation study found volatility contraction and volume dry-up did not raise the odds of a "
                       "breakout on their own, so this finds candidates, it does not rank them. Not yet studied."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "close", "op": ">", "ref": "sma200"},
                {"field": "close", "op": ">", "ref": "sma150"},
                {"field": "sma150", "op": ">", "ref": "sma200"},
                {"field": "sma200", "op": ">", "ref": "sma200_21d_ago"},
                {"field": "days_since_52w_high", "op": ">=", "value": BASE_FORMING_MIN_DAYS},
                {"field": "depth_since_52w_high_pct", "op": ">=", "value": BASE_FORMING_MIN_DEPTH_PCT},
                {"field": "depth_since_52w_high_pct", "op": "<=", "value": BASE_FORMING_MAX_DEPTH_PCT},
                {"field": "pct_below_high", "op": "<=", "value": BASE_FORMING_MAX_PCT_BELOW_HIGH},
                {"field": "range_ratio", "op": "<=", "value": BASE_FORMING_MAX_RANGE_RATIO},
                {"field": "volume_ratio", "op": "<", "value": BASE_FORMING_MAX_VOLUME_RATIO},
            ],
            "columns": ["days_since_52w_high", "depth_since_52w_high_pct", "pct_below_high", "range_ratio", "volume_ratio"]},
        "long_base_quality": {
            "name": "Base — long, quality business",
            "description": f"Quality businesses (quality score {LONG_BASE_MIN_QUALITY}+) that have moved sideways for "
                           f"{LONG_BASE_MIN_DAYS}+ sessions inside a range no deeper than {LONG_BASE_MAX_DEPTH_PCT:g}%, with the "
                           f"close within {LONG_BASE_MAX_PCT_BELOW_HIGH:g}% of the range's top and its pullbacks contracting.",
            "thesis": ("A sound business whose stock has gone nowhere for months is often a base being built, not a broken stock: "
                       "Weinstein's Stage 1 and O'Neil's long flat bases end when supply is used up and the price clears the top "
                       "of the range, and the longer the base the bigger the move it can launch. Three things say the base is "
                       "mature: the price is back near its ceiling, each pullback inside it is shallower than the last (sellers "
                       "drying up, Minervini's volatility contraction), and the 200-day has stopped falling — flat is allowed, so "
                       "a Stage 1 base qualifies before the average turns up. The quality score keeps it to businesses worth "
                       f"owning. The base is the longest run of up to {BASE_MAX_DAYS} sessions inside the depth limit, so its "
                       "depth sits near that limit. The price half is point in time and can be studied; the quality score is "
                       "present-only, so the study tests only the base."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "base_days", "op": ">=", "value": LONG_BASE_MIN_DAYS},
                {"field": "base_depth_pct", "op": "<=", "value": LONG_BASE_MAX_DEPTH_PCT},
                {"field": "pct_below_base_high", "op": "<=", "value": LONG_BASE_MAX_PCT_BELOW_HIGH},
                {"field": "range_contracting", "op": "is", "value": True},
                {"field": "sma200_not_falling", "op": "is", "value": True},
                {"field": "quality", "op": ">=", "value": LONG_BASE_MIN_QUALITY},
            ]},
        "leaders": {
            "name": "Leaders — in leading groups",
            "description": f"Strong stocks (RS {LEADER_MIN_RS}+) in the strongest peer groups (group RS {LEADER_GROUP_RS}+), in an uptrend.",
            "thesis": ("Big winners tend to come from the groups leading the market (O'Neil, Minervini): a strong stock in a weak group "
                       "usually lags. In our five-year study, stocks in strong groups beat those in weak groups in both markets "
                       "(clearly so in India), while a stock's rank inside its group added nothing — so this screen asks for a strong "
                       "group and a strong stock, not for the group's #1. The peer group is the stock's sub-industry where its industry "
                       "group is split and the sub-industry has enough tradable stocks, else its industry group; its RS rating comes "
                       "from the Sectors page."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "peer_rs", "op": ">=", "value": LEADER_GROUP_RS},
                {"field": "rs_rank", "op": ">=", "value": LEADER_MIN_RS},
                {"field": "close", "op": ">", "ref": "sma50"},
                {"field": "close", "op": ">", "ref": "sma200"},
            ]},
        "bear_market_leaders": {
            "name": "Leaders — in a bear market",
            "description": f"Stocks that beat the market by {BEAR_LEADER_MIN_REL_RETURN:g}+ points over two years without falling more "
                           f"than {BEAR_LEADER_MAX_DRAWDOWN:g}% from a peak, still within {BEAR_LEADER_MAX_PCT_BELOW_HIGH:g}% of the "
                           f"52-week high and above the 200-day, RS {BEAR_LEADER_MIN_RS}+, with ROE {BEAR_LEADER_MIN_ROE:g}%+, EPS "
                           f"growth {BEAR_LEADER_MIN_EPS_GROWTH:g}%+ and sales growth {BEAR_LEADER_MIN_SALES_GROWTH:g}%+.",
            "thesis": ("Minervini and O'Neil both watch which stocks hold up while the market falls or goes nowhere: the ones that "
                       "keep near their highs as the index corrects are being accumulated, and they tend to lead when the market "
                       "turns. This screen asks it three ways. Relative return: the stock beat the market benchmark over the "
                       f"last {R2Y_BARS} sessions (swap rel_r2y for rel_r12m or rel_r3y to change the window). Resilience: its "
                       f"deepest fall from a peak over the last {MDD_BARS} sessions stayed shallow, so it did not get there by "
                       "crashing and rebounding. Leadership now: near its highs, above the 200-day, a high RS rank. Fundamentals "
                       "keep it to growing, profitable businesses; read the list by sector to find each group's leaders. The "
                       "price half is point in time and can be studied; the fundamentals are present-only, so the study tests "
                       "only the price half. A strong two-year return can come from one re-rating, so check the drawdown and "
                       "results beside it."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "rel_r2y", "op": ">=", "value": BEAR_LEADER_MIN_REL_RETURN},
                {"field": "mdd_2y", "op": ">=", "value": -BEAR_LEADER_MAX_DRAWDOWN},
                {"field": "pct_below_high", "op": "<=", "value": BEAR_LEADER_MAX_PCT_BELOW_HIGH},
                {"field": "close", "op": ">", "ref": "sma200"},
                {"field": "rs_rank", "op": ">=", "value": BEAR_LEADER_MIN_RS},
                {"field": "roe", "op": ">=", "value": BEAR_LEADER_MIN_ROE},
                {"field": "eps_growth_q", "op": ">=", "value": BEAR_LEADER_MIN_EPS_GROWTH},
                {"field": "sales_growth_q", "op": ">=", "value": BEAR_LEADER_MIN_SALES_GROWTH},
            ],
            "columns": ["rel_r2y", "r2y", "mdd_2y", "rel_r12m"], "sort_by": "rel_r2y"},
        "growth_leaders": {
            "name": "Leaders — growth in Stage 2",
            "description": f"Quarterly results that pass Minervini's growth tests (SEPA verdict {' or '.join(GROWTH_VERDICTS)}), "
                           "with the stock in Stage 2 (the full Trend Template). Its twin for turnarounds is Fundamentals — recoveries.",
            "thesis": ("Minervini's fundamentals ask for strong, accelerating earnings and sales growth, measured against the same "
                       "quarter a year earlier so seasonality cancels. LEADER passes every test (EPS and sales growth, EPS "
                       "acceleration, margins, no slowdown); ACCEPTABLE passes growth and no slowdown without all the "
                       "confirmation. The price half is the full Trend Template: Minervini's SEPA wants both a Stage-2 uptrend and "
                       "a growing business, and a growing business under a falling average is a different trade. Filter the "
                       "verdict condition to LEADER alone for his strictest version. Growth from a loss cannot be measured, so a company coming out of losses never "
                       "appears here: see Fundamentals — recoveries. Present-only: the verdict exists only for the latest snapshot, so the "
                       "screen cannot be studied."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                *stage2[1:],
                {"field": "sepa_verdict", "op": "in", "value": GROWTH_VERDICTS},
            ],
            "columns": ["sepa_verdict", "eps_growth_q", "sales_growth_q", "sepa_code33"], "sort_by": "eps_growth_q"},
        "recoveries": {
            "name": "Fundamentals — recoveries",
            "description": f"Turnarounds: a profit in the latest quarter after a loss a year earlier, EPS above the year-ago quarter "
                           f"for {RECOVERY_MIN_IMPROVING_QUARTERS}+ quarters running, sales up {RECOVERY_MIN_SALES_GROWTH:g}%+, "
                           "and the stock above its 200-day average.",
            "thesis": ("Growth tests skip a company coming out of losses: a rate of growth from a loss is not defined. Minervini "
                       "takes such turnarounds case by case, and what he looks for is that the recovery is real: more than one "
                       "quarter of improvement, and sales growing so the profit is not cost cuts alone. So the screen asks for a "
                       "year-ago loss turned into a profit, a run of quarters each beating its year-ago quarter (losses included), "
                       "and sales growth. The 200-day keeps it to recoveries the market has started to believe; one below a "
                       "falling average is a value bet, not a momentum trade. Sales growth accelerating is a field of its own for "
                       "a stricter version. Present-only: the quarterly results exist only for the latest snapshot, so the screen "
                       "cannot be studied. One-off gains are not removed: check the filing behind a sudden profit."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "eps_turned_positive", "op": "is", "value": True},
                {"field": "eps_improving_q", "op": ">=", "value": RECOVERY_MIN_IMPROVING_QUARTERS},
                {"field": "sales_growth_q", "op": ">=", "value": RECOVERY_MIN_SALES_GROWTH},
                {"field": "close", "op": ">", "ref": "sma200"},
            ],
            "columns": ["eps_improving_q", "sales_growth_q", "sales_accelerating"], "sort_by": "sales_growth_q"},
        "breakout_watch": {
            "name": "Breakout watch — RS and OBV leading",
            "markets": list(BREAKOUT_WATCH_MARKETS),
            "description": f"Stocks in a base just under resistance (within {BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT:g}% of the "
                           f"{PIVOT_BARS}-session pivot, above a rising 200-day) whose RS line and on-balance volume are already "
                           f"at new {LEAD_HIGH_BARS}-session highs, in an industry group rated {BREAKOUT_WATCH_MIN_GROUP_RS}+. "
                           "US only. A watchlist, not a buy signal: about 1 in 7 became a real breakout within four weeks.",
            "thesis": ("A stock that is about to break out often shows it first in what price has not done yet: it is already "
                       "beating the market (its RS line makes a new high before the price clears its pivot), volume is "
                       "flowing in on its up days (on-balance volume at a new high), and its group is strong. The breakout "
                       "anticipation study tested 29 such pre-breakout signals against a control set of failed breakouts and "
                       "bases that never broke. These three held up; volatility contraction, volume dry-up, shallow bases and "
                       "moving-average compression did not. On weekly samples 2022-2026, a rule fixed on 2017-2021, 13.9% of "
                       "these stocks broke out above the pivot on 1.5x volume and followed through (a close 2 ATR higher "
                       "before one half an ATR under the pivot) within four weeks, against 8.5% of all stocks in the same "
                       "position. It raises the "
                       "odds that a breakout happens, not that it works: follow-through stayed at about 36-40%. In India it "
                       "added nothing out of sample, so the screen is not offered there. Alerts are logged each session "
                       "(the breakout_watch job) and scored forward by the study."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "close", "op": ">", "ref": "sma200"},
                {"field": "sma200_not_falling", "op": "is", "value": True},
                {"field": "close", "op": "<", "ref": "pivot_55"},
                {"field": "close", "op": ">=", "ref": "pivot_55", "mult": 1 - BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT / 100},
                {"field": "close", "op": ">=", "ref": "high_252", "mult": BREAKOUT_WATCH_MIN_FRAC_OF_52W_HIGH},
                {"field": "rs_line_high", "op": "is", "value": True},
                {"field": "obv_high", "op": "is", "value": True},
                {"field": "group_rs", "op": ">=", "value": BREAKOUT_WATCH_MIN_GROUP_RS},
            ],
            "columns": ["pivot_55", "group_rs", "rs_rank"], "sort_by": "group_rs"},
    }


def mask(df: pd.DataFrame, conditions: list[dict]) -> pd.Series:
    """Boolean Series: the rows that satisfy every condition."""
    m = pd.Series(True, index=df.index)
    for cond in conditions:
        f, op = cond["field"], cond["op"]
        if f not in df.columns:
            raise ValueError(f"unknown field {f!r}")
        x = df[f]
        if op == "is":
            want = bool(cond.get("value", True))
            m &= x.fillna(not want).astype(bool) == want
            continue
        if op == "in":
            m &= x.isin(list(cond.get("value") or []))
            continue
        if "ref" in cond and cond["ref"]:
            if cond["ref"] not in df.columns:
                raise ValueError(f"unknown field {cond['ref']!r}")
            y = df[cond["ref"]]
            if pd.api.types.is_numeric_dtype(y) or y.dropna().map(lambda v: isinstance(v, (int, float))).all():
                y = y.astype(float)
                mult = cond.get("mult")
                if mult not in (None, "", 1, 1.0):
                    y = y * float(mult)
            else:                                   # two text fields (e.g. peer group vs industry group): = / != only
                if op not in ("=", "!="):
                    raise ValueError(f"{f!r} and {cond['ref']!r} are text: compare them with = or ≠")
                same = (x.astype(str) == y.astype(str)) & x.notna() & y.notna()
                m &= same if op == "=" else (~same & x.notna() & y.notna())
                continue
        else:
            y = cond.get("value")
            if y is None:
                raise ValueError(f"condition on {f!r} needs a value or a field to compare with")
            y = float(y) if not isinstance(y, str) else y
        xv = x.astype(float) if not isinstance(y, str) else x
        res = {">": xv > y, ">=": xv >= y, "<": xv < y, "<=": xv <= y, "=": xv == y, "!=": (xv != y) & xv.notna()}.get(op)
        if res is None:
            raise ValueError(f"unknown operator {op!r}")
        m &= res.fillna(False).astype(bool)
    return m


def describe(cond: dict, labels: dict) -> str:
    """A condition in words: 'Close > SMA 50', 'Close ≥ 52-week high × 0.85'."""
    f = labels.get(cond["field"], cond["field"])
    op = {">=": "≥", "<=": "≤", "!=": "≠", "is": "is", "in": "in"}.get(cond["op"], cond["op"])
    if cond["op"] == "is":
        return f if cond.get("value", True) else f"not {f}"
    if cond["op"] == "in":
        return f"{f} in {', '.join(map(str, cond.get('value') or []))}"
    if cond.get("ref"):
        mult = cond.get("mult")
        return f"{f} {op} {labels.get(cond['ref'], cond['ref'])}" + (f" × {mult:g}" if mult not in (None, "", 1, 1.0) else "")
    return f"{f} {op} {cond.get('value')}"


# ------------------------------------------------------------------ your own screens

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_screens (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    conditions JSONB NOT NULL,
    sort_by TEXT,
    columns JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _row(r) -> dict:
    return {"id": r[0], "name": r[1], "description": r[2], "conditions": r[3], "sort_by": r[4], "columns": r[5],
            "created_at": r[6].isoformat(), "updated_at": r[7].isoformat()}


_COLS = "id, name, description, conditions, sort_by, columns, created_at, updated_at"


def list_user() -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM user_screens ORDER BY name")
        return [_row(r) for r in cur.fetchall()]


def get_user(sid: int) -> dict | None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM user_screens WHERE id=%s", (sid,))
        r = cur.fetchone()
    return _row(r) if r else None


def save_user(name: str, conditions: list, description: str = "", sort_by: str | None = None, columns=None, sid: int | None = None) -> dict:
    init_schema()
    name = name.strip()
    if not name:
        raise ValueError("a screen needs a name")
    for cond in conditions:
        if cond.get("op") not in OPS:
            raise ValueError(f"unknown operator {cond.get('op')!r}")
    with db.get_connection().cursor() as cur:
        if sid:
            cur.execute(f"""UPDATE user_screens SET name=%s, description=%s, conditions=%s, sort_by=%s, columns=%s, updated_at=now()
                            WHERE id=%s RETURNING {_COLS}""", (name, description, json.dumps(conditions), sort_by, json.dumps(columns), sid))
        else:
            cur.execute(f"""INSERT INTO user_screens (name, description, conditions, sort_by, columns) VALUES (%s,%s,%s,%s,%s)
                            RETURNING {_COLS}""", (name, description, json.dumps(conditions), sort_by, json.dumps(columns)))
        return _row(cur.fetchone())


def delete_user(sid: int) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM user_screens WHERE id=%s", (sid,))
