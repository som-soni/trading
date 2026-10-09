"""Screens: which stocks are worth looking at — qualification only, no entry, no stop, no decision.

A screen is a named set of criteria (screens/criteria.py) applied to every stock above a common
tradability floor (price, liquidity, history). Its output is the list of qualifying stocks with each
criterion's result — "potentially tradeable", not trades.

Strategies (strategies/) draw their candidates from a screen (`Strategy.screen_key`) and add what makes a
trading system: setups, entry/stop/target, exits, sizing. Strategies are backtested; screens are
evaluated by a forward-return study.

    stage2       Minervini's Trend Template (Stage 2 uptrend)            -> Minervini SEPA
    uptrend      Established uptrend: weekly + daily trend structure     -> Trend pullback
    near_highs   Above a rising 200-day, within 15% of the 52-week high  -> Breakout, Chart pattern
    above_200    Above the 200-day average (long-term trend only)        -> Donchian
"""

from .base import Criterion, Screen, ScreenResult
from . import criteria as c

_SCREENS = [
    Screen(
        key="stage2", name="Stage 2 — Trend Template",
        description="Stocks in a confirmed Stage 2 uptrend by Minervini's eight Trend Template criteria.",
        thesis="Big winners almost always come from a Stage 2 uptrend: price above rising long-term averages stacked in "
               "order, well off the lows, near the highs, and stronger than most of the market. Minervini will not look "
               "at a stock that fails any of them.",
        criteria=(
            Criterion("C1", c.tt_above_sma50, "Close above the 50-day moving average."),
            Criterion("C2", c.tt_above_sma150, "Close above the 150-day moving average."),
            Criterion("C3", c.tt_above_sma200, "Close above the 200-day moving average."),
            Criterion("C4", c.tt_stacked, "Averages stacked for a Stage 2 advance: 50-day above 150-day above 200-day."),
            Criterion("C5", c.tt_sma200_rising, "The 200-day is higher than {SMA200_RISING_BARS} sessions ago — rising for at least a month."),
            Criterion("C6", c.tt_off_low, "Close at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low."),
            Criterion("C7", c.tt_near_high, "Close within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high."),
            Criterion("C8", c.tt_rs, "Relative strength: an RS rank of {RS_MIN_RANK}+ (1–99 across the market, recent quarter "
                                     "weighted double) when the whole market is screened; a single stock or a backtest uses "
                                     "12-1 month momentum of {RS_MIN_MOM}+ as the stand-in."),
        ),
        rank_rs=True,
    ),
    Screen(
        key="uptrend", name="Established uptrend",
        description="Stocks in an orderly uptrend on both the weekly and daily charts, near their highs, with the trend not fading.",
        thesis="Pullbacks and continuation bases only work inside a trend that is already established: the weekly chart "
               "trending up, the daily averages in order and rising, higher swing lows, positive momentum and price "
               "near the highs.",
        criteria=(
            Criterion("U1", c.weekly_above_rising_ema30, "Weekly close above a rising 30-week EMA."),
            Criterion("U2", c.weekly_sma20_above_sma50, "Weekly 20-week average above the 50-week."),
            Criterion("U3", c.daily_structure, "Daily 50-day above the 200-day, and price has not broken down through the 50-day "
                                               "(more than 2 ATR below it, or 5 closes in a row under it)."),
            Criterion("U4", c.averages_not_falling, "Neither the 50-day nor the 200-day is falling."),
            Criterion("U5", c.higher_swing_lows, "Higher swing lows over the last ~50 sessions."),
            Criterion("U6", c.momentum_12_1_positive, "Positive 12-1 month momentum (the close a month ago above the close a year ago)."),
            Criterion("U7", c.within_25pct_of_high, "Close within 25% of the 52-week high."),
            Criterion("U8", c.trend_not_fading, "Trend not fading: not both a negative 3-month return and a flat or falling 50-day."),
        ),
    ),
    Screen(
        key="near_highs", name="Near highs, rising 200-day",
        description="Stocks above a rising 200-day average and within 15% of their 52-week high — where breakouts happen.",
        thesis="Breakouts and classical bases that work are continuation patterns: they complete near the highs, above a "
               "long-term average that is not falling. The same shapes in a downtrend are bear-market rallies.",
        criteria=(
            Criterion("H1", c.above_sma200, "Close above the 200-day moving average."),
            Criterion("H2", c.sma200_not_falling, "The 200-day is not falling (not more than {SMA200_FALLING_PCT}% below its value "
                                                  "{SMA200_SLOPE_BARS} sessions ago)."),
            Criterion("H3", c.near_52w_high, "Close within 15% of the 52-week high."),
        ),
    ),
    Screen(
        key="above_200", name="Above the 200-day",
        description="Stocks above their 200-day average — the long-term trend filter alone.",
        thesis="The broadest trend filter: long-only systems that let their own entry signal define the trend (a channel "
               "breakout) still avoid buying under the 200-day.",
        criteria=(Criterion("A1", c.above_sma200, "Close above the 200-day moving average."),),
    ),
]
SCREENS: dict[str, Screen] = {s.key: s for s in _SCREENS}


def get_screen(key: str) -> Screen:
    return SCREENS[key]


def list_screens() -> list[str]:
    return list(SCREENS)
