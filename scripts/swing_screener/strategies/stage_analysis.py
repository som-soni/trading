"""Stage analysis — Weinstein's Stage 2 breakout, on weekly bars.

Stan Weinstein's method sorts every stock into four stages with one line, the 30-week moving
average: Stage 1 a sideways base, Stage 2 an advance above a rising line, Stage 3 a flattening
top, Stage 4 a decline. This buys the Stage 1-to-2 transition and holds while the weekly close
stays above the line.

The stage itself comes from `stage_series`, a state machine with memory: a stage persists until
the weekly close has been on the other side of the line for CONFIRM_WEEKS weeks, and a flat line
reads as Stage 1 or Stage 3 according to what came before it — the one question a pointwise
slope-and-side read can never answer. The chart's Stage analysis indicator and the market/sector
gates all draw from this same function, so there is exactly one implementation of the rule.

THE ONLY WEEKLY STRATEGY HERE. Everything else in this package decides on daily bars. That is not
a detail: a weekly close ignores four days of noise, so the same idea on daily bars is a different
and much twitchier rule. `StockContext` already carries resampled weekly bars, so the strategy
reads `ctx.weekly` and its daily sibling only for the entry price.

The 30-week average is a SIMPLE average of weekly closes. `ctx.weekly` already carries `ema30`,
which is a 30-week exponential average serving a different screen's criterion; Weinstein's line is
the simple one and substituting the exponential would change both the stage boundaries and the
exit.

WHAT IT SHARES. Its universe gates come from the `near_highs` screen, evaluated by that screen's
own criteria -- above the 200-day, 200-day not falling, near the 52-week high -- which is as close
as the daily screens come to "above a rising 30-week line, breaking out near highs". The weekly
conditions that have no screen equivalent are the strategy's own gates G4 onward.
"""
from __future__ import annotations

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import (LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan,
                   tradable_point_in_time)
from .trend_pullback import round_tick

STG01 = "S1"   # the Stage 1 -> Stage 2 breakout

# ---- the line, and the stages it defines
MA_WEEKS = 30                 # Weinstein's 30-week simple average of weekly closes
SLOPE_WEEKS = 4               # the line is compared with its own value this many weeks ago
#: The flat band: the line is "rising" when it is more than this far above its value SLOPE_WEEKS ago,
#: "falling" when more than this far below, "flat" between -- the Learn guide's own rule (0.5% over
#: about a month), and the same reading the daily stage cycle uses. v2.0 sized the band to the
#: stock's WEEKLY-RETURN volatility instead, which was the wrong quantity: a 30-week average moves
#: far less in 4 weeks than the closes do in 1, so the band swallowed real slopes (see the changelog).
FLAT_BAND_PCT = 0.5
CONFIRM_WEEKS = 3             # weeks a transition's condition must hold before the stage changes
#: A Stage 1 base must be at least this old before a close above its high counts as the breakout into
#: Stage 2 (when the line is merely flat; above a RISING line is Stage 2 on its own, Weinstein's rule).
#: Two weeks above a flat line is a bounce, and it used to read as a new Stage 2.
STAGE1_MIN_WEEKS = 6

# ---- the Stage 1 base and the breakout
BASE_MIN_WEEKS = 12           # sideways for at least this long
#: A base is a CONTAINED range, so it needs a depth limit. Without one, "sideways" was tested as
#: "the weekly close is below the highest high of the last 26 weeks", which is almost always true
#: -- so every stock reported a base the full 104-week cap, BASE_MIN_WEEKS never bound, and the
#: base low used for the stop was the lowest low of two years, which pinned every stop to the
#: MAX_STOP_PCT floor. Weinstein's bases are shallow; 30% is generous for one.
BASE_MAX_DEPTH_PCT = 30.0
BASE_MAX_WEEKS = 104          # stop looking back beyond this
MANSFIELD_WEEKS = 52          # the stock/index ratio against its own average: the RS zero line
MANSFIELD_RISE_WEEKS = 4      # "improving from negative" is judged over this many weeks
VOL_MULT = 2.0                # breakout week's volume against the previous weeks' average
VOL_WEEKS = 4                 # the guide compares the breakout week with the previous four

# ---- the trade
MAX_STOP_PCT = 15.0           # skip or shrink if the structural stop is further than this
BASE_TARGET_MULT = 1.0        # nominal target: the base's own height above the breakout


def _market_of(symbol: str) -> str:
    """Which market a symbol belongs to, from the configured ticker suffixes.

    Shared reasoning with rs_leaders: StockContext carries no market, and the index-level stage
    check needs one. Read from MARKETS so a new country stays a config entry (CLAUDE.md).
    """
    from ..config import MARKETS
    best, blank = None, None
    for k, cfg in MARKETS.items():
        sfx = getattr(cfg, "symbol_suffix", "") or ""
        if not sfx:
            blank = k
        elif symbol.upper().endswith(sfx.upper()):
            best = k
    return best or blank or "us"


def ma30(weekly: pd.DataFrame) -> pd.Series:
    return weekly["close"].rolling(MA_WEEKS).mean()


def _slope_and_band(weekly: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """Per week: the line's percent change over SLOPE_WEEKS, and the flat band that judges it.

    Weinstein's stages turn on the line's SLOPE, not on price relative to it, so this is the one
    measurement the whole method rests on. A band is required: a line that is dead flat in reality
    wanders by fractions of a percent, and calling that "rising" would put every basing stock in
    Stage 2. The band is FLAT_BAND_PCT, fixed (returned as a series so the callers' per-week shape is
    unchanged); the slope series is causal.
    """
    line = ma30(weekly)
    chg = (line / line.shift(SLOPE_WEEKS) - 1) * 100
    return chg, pd.Series(FLAT_BAND_PCT, index=weekly.index, dtype=float)


def line_state(weekly: pd.DataFrame) -> tuple[str, float]:
    """("rising" | "flat" | "falling", percent change) of the 30-week line over SLOPE_WEEKS."""
    chg, band = _slope_and_band(weekly)
    if not len(chg) or pd.isna(chg.iloc[-1]):
        return "flat", float("nan")
    c = float(chg.iloc[-1])
    b = float(band.iloc[-1]) if pd.notna(band.iloc[-1]) else FLAT_BAND_PCT
    return ("rising" if c > b else "falling" if c < -b else "flat"), c


def stage_series(weekly: pd.DataFrame) -> pd.Series:
    """Weinstein's stage per weekly bar, as a state machine with memory (0 = not yet decidable).

    A pointwise read (slope x side-of-the-line) cannot tell Stage 1 from Stage 3 -- both are a
    flat line -- and flickers whenever the close wobbles around it. With memory, both problems
    disappear by construction: a flat line is Stage 3 only when an ADVANCE came before it, and
    every transition needs its condition to hold for CONFIRM_WEEKS consecutive weeks, counted from
    the last transition (so every stage lasts at least that long). The slope state has HYSTERESIS:
    once "rising" it stays rising until the line is no higher than SLOPE_WEEKS ago, once "falling"
    until it is no lower -- a line wobbling about the FLAT_BAND_PCT edge no longer toggles the stage.
    Transitions:

      1 -> 2  the close above the line for C weeks and EITHER the line rising for C weeks (above a
              rising line is Stage 2, Weinstein's own test) OR, under a line that is merely not
              falling, the close above the base's own high with the base at least STAGE1_MIN_WEEKS
              old (the breakout; a two-week bounce above a flat line is not one)
      1 -> 4  close below the line with the line falling (a base that failed)
      2 -> 3  the line stops rising after having risen this Stage 2, or the close holds below it
      2 -> 1  the close holds below a line that never rose -- a failed breakout, back to the base
      2 -> 4  close below with the line falling (a fast break skips the top)
      3 -> 2  the line rises again with the close above it AND above the Stage 2's own high: a top
              resolves upward only by breaking out of it
      3 -> 4  the close holds below a FALLING line; below a line that merely went flat, the top
              resolves into a new base instead (3 -> 1)
      4 -> 1  the line stops falling with the close back above it. Never straight to 2: the base
              comes first, and its breakout is judged by the 1 -> 2 rule
    """
    n = len(weekly)
    vals = [0] * n
    if n <= MA_WEEKS + SLOPE_WEEKS:
        return pd.Series(vals, index=weekly.index, dtype=int)
    chg, band = _slope_and_band(weekly)
    close, lv, high = weekly["close"].tolist(), ma30(weekly).tolist(), weekly["high"].tolist()
    cv, bv = chg.tolist(), band.tolist()
    C = CONFIRM_WEEKS
    stage, st = 0, "flat"
    above_w = below_w = 0        # consecutive weeks of the close on one side of the line
    rising_w = falling_w = 0     # consecutive weeks of the slope state itself
    not_rising_w = not_falling_w = 0
    rose2 = False                # did the line actually rise during this Stage 2?
    peak = base_high = None      # the Stage 2's high so far; the Stage 1's high so far
    age = 0                      # weeks in the current stage
    for i in range(MA_WEEKS + SLOPE_WEEKS, n):
        if lv[i] != lv[i] or cv[i] != cv[i]:   # NaN: carry the last stage
            vals[i] = stage
            continue
        b = bv[i] if bv[i] == bv[i] else FLAT_BAND_PCT
        if st == "rising" and cv[i] > 0:
            pass
        elif st == "falling" and cv[i] < 0:
            pass
        else:
            st = "rising" if cv[i] > b else "falling" if cv[i] < -b else "flat"
        above_w, below_w = (above_w + 1, 0) if close[i] > lv[i] else (0, below_w + 1)
        rising_w = rising_w + 1 if st == "rising" else 0
        falling_w = falling_w + 1 if st == "falling" else 0
        not_rising_w = 0 if st == "rising" else not_rising_w + 1
        not_falling_w = 0 if st == "falling" else not_falling_w + 1
        up = above_w >= C and not_falling_w >= C
        prev = stage
        if stage == 0:   # seed: the pointwise read, before there is history to remember
            above = close[i] > lv[i]
            stage = (2 if above else 1) if st == "rising" else \
                    ((3 if above else 4) if st == "falling" else (3 if above else 1))
            rose2 = stage == 2 and st == "rising"
            peak = base_high = high[i]
        elif stage == 1:
            if up and (rising_w >= C or (age >= STAGE1_MIN_WEEKS and close[i] > base_high)):
                stage, rose2 = 2, False
            elif below_w >= C and falling_w >= C:
                stage = 4
            else:
                base_high = max(base_high, high[i])
        elif stage == 2:
            rose2 = rose2 or rising_w >= C
            peak = max(peak, high[i])
            if below_w >= C and falling_w >= C: stage = 4
            elif below_w >= C: stage = 3 if rose2 else 1
            elif rose2 and not_rising_w >= C: stage = 3
        elif stage == 3:
            if rising_w >= C and above_w >= C and close[i] > peak: stage, rose2 = 2, True
            elif below_w >= C and falling_w >= C: stage = 4
            elif below_w >= C and not_falling_w >= C: stage = 1
        else:  # stage 4
            if not_falling_w >= C and close[i] > lv[i]: stage = 1
        if stage != prev:
            age = 0
            above_w = below_w = rising_w = falling_w = not_rising_w = not_falling_w = 0
            if stage == 1: base_high = high[i]
            if stage == 2: peak = high[i]
        else:
            age += 1
        vals[i] = stage
    return pd.Series(vals, index=weekly.index, dtype=int)


def stage_of(weekly: pd.DataFrame) -> int:
    """The current stage: the last value of `stage_series`. 0 when undecidable."""
    s = stage_series(weekly)
    return int(s.iloc[-1]) if len(s) else 0


class StageAnalysisStrategy(Strategy):
    """Weinstein's Stage 2 breakout, bought on the weekly bar and held above the 30-week line."""

    key = "stage_analysis"
    name = "Stage analysis"
    description = ("Buy the weekly breakout from a Stage 1 base into Stage 2 -- above the base's "
                   "own high and a {MA_WEEKS}-week average that is no longer declining, on "
                   "{VOL_MULT}x volume -- and hold while the weekly close stays above the line.")
    family = "stage_analysis"
    version = "2.1"
    changelog = (("2.1", "2026-10-21",
                  "The flat band is a FIXED {FLAT_BAND_PCT}% over {SLOPE_WEEKS} weeks -- the Learn "
                  "guide's own rule and the daily stage cycle's -- instead of 0.6 x "
                  "the stock's weekly-return stdev. That band measured the wrong quantity: a "
                  "{MA_WEEKS}-week average moves far less in {SLOPE_WEEKS} weeks than the closes do in "
                  "one, so for a volatile stock the band (1.6-3%) swallowed real slopes. Measured over "
                  "160 random stocks, the line read 'flat' on 43-46% of all weeks, and on a quarter of "
                  "all weeks it had moved more than 1% yet still read flat. The visible result was "
                  "Stage 3 called during breakouts (ANANDRATHI.NS, April 2026, the line up 2.3%) and no "
                  "Stage 4 through a 31% decline (the same stock, February-June 2025, the line down "
                  "1.7%). With the fixed band: weeks in Stage 4 rise from 21% to 37% of the sample and "
                  "Stage 1 falls from 25% to 12%, the Stage 2 share is unchanged (48%), and the guide's "
                  "own TRENT narrative now reproduces (Stage 4 from March 2025, where the old band put "
                  "it only in April-June). G5 and the W2 Stage 3 warning read the same slope, so both "
                  "move with it. "
                  "The machine itself was then de-flickered, with the same stock as the witness: "
                  "between July 2024 and June 2025 -- one top and one decline -- it called nine stage "
                  "changes, several two weeks long. Four mechanical causes, four rules: the slope state "
                  "has HYSTERESIS (rising stays rising until the line is no higher than "
                  "{SLOPE_WEEKS} weeks ago, not merely inside the band); the week counters reset at "
                  "every transition, so each stage lasts at least {CONFIRM_WEEKS} weeks (raised from "
                  "2); Stage 4 never goes straight to Stage 2 -- a bounce above a flat line was "
                  "being read as a new advance -- it goes to Stage 1 when the close is back above a "
                  "line that stopped falling, and leaves it only above a RISING line or by closing "
                  "above the base's own high once the base is {STAGE1_MIN_WEEKS} weeks old; and a "
                  "Stage 3 resolves upward only above the Stage 2's own peak. Measured over the same "
                  "160 stocks: stage runs shorter than 6 weeks 4,366 -> 2,388, stage changes per 100 "
                  "weeks 7.9 -> 5.6, with the Stage 2 share steady at 41-42%. ANANDRATHI.NS reads "
                  "Stage 4 April-July 2025 then one Stage 2 from August 2025; TRENT one Stage 4 from "
                  "March 2025 to August 2026. G7, G8 and W2 read the machine, so all three move; the "
                  "fingerprint moves with CONFIRM_WEEKS and STAGE1_MIN_WEEKS."),
                 ("2.0", "2026-10-21",
                  "The stage became a STATE MACHINE (stage_series): a stage persists until the "
                  "weekly close holds the other side of the line for {CONFIRM_WEEKS} weeks, so a "
                  "flat line reads as Stage 1 or Stage 3 by what came before it instead of by "
                  "which side the close happens to sit on, and the label no longer flickers. The "
                  "flat band was sized to each stock's own weekly volatility "
                  "(0.6 x the 26-week stdev, clamped to 0.5-3%) instead of a fixed 1% -- reverted "
                  "to a fixed band in 2.1, see above. Gates moved "
                  "to the book: G5 passes when the line is NOT FALLING (the guide's investor "
                  "rule) rather than only when rising; G6 is Mansfield relative strength (the "
                  "stock/index ratio against its own {MANSFIELD_WEEKS}-week zero line, positive "
                  "or improving) rather than a 13-week return race; resistance is the detected "
                  "base's own high rather than a fixed 26-week lookback; breakout volume is "
                  "judged against the previous {VOL_WEEKS} weeks per the guide, not 10; and a "
                  "new gate G8 keeps hands off stocks whose SECTOR index is in Stage 4. Also "
                  "fixes a LOOKAHEAD: mid-week, the benchmark ratio and the market-stage lookup "
                  "joined on the running week's Friday label and so read the index's Friday "
                  "close days early; both now use completed weeks only."),
                 ("1.0", "2026-10-18",
                  "First version. The stage model was validated against the guide's own Trent "
                  "narrative before any trade logic existed: Stage 2 from August 2023 through "
                  "October 2024 (close 2,049 -> 7,128) and Stage 4 by March 2025, matching the "
                  "guide's '1,500 to more than 7,000, held until October 2024'. "
                  "TWO DEFECTS WERE FOUND AND FIXED BEFORE THIS SHIPPED, recorded because both are "
                  "the kind that produce plausible-looking output rather than an error. (1) "
                  "'Sideways for {BASE_MIN_WEEKS} weeks' was first implemented as 'the weekly close "
                  "is below the highest high of the last 26 weeks', which is almost "
                  "always true -- so every stock reported a base at the full {BASE_MAX_WEEKS}-week "
                  "cap, BASE_MIN_WEEKS never bound, and the base low used for the stop was the "
                  "lowest low of two years, pinning every stop to the {MAX_STOP_PCT}% floor. A base "
                  "needs a DEPTH limit, so it is now the longest window within "
                  "{BASE_MAX_DEPTH_PCT}%. (2) classify() had the wrong signature and decision_docs "
                  "used label codes that do not exist. "
                  "W3 was then checked for discrimination, since an always-on watch flag would make "
                  "TRADE_HIGH_CONFIDENCE unreachable: over 834 symbol-dates the structural stop "
                  "sits a median 11.1% below entry and is within {MAX_STOP_PCT}% on 75% of the 170 "
                  "setups found, so it filters rather than blocks. 149 of those 170 were armed "
                  "bases rather than completed breakouts."),)

    style = "breakout"
    behaviour = "trend_momentum"
    selection = "time_series"

    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2", "G3": "H3"}
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
    gate_titles = {
        "G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
        "G4": "Weekly close above the 30-week line", "G5": "30-week line not falling",
        "G6": "Mansfield RS positive or improving", "G7": "Market not in Stage 4",
        "G8": "Sector not in Stage 4",
    }
    watch_codes = ("W1", "W2", "W3")
    setup_codes = (STG01,)
    setup_names = {STG01: "Stage 2 breakout"}
    #: 60 weeks of weekly bars, which the guide requires for the line and the 52-week range, plus
    #: the daily history needed to resample them. The Mansfield zero line wants more
    #: ({MANSFIELD_WEEKS} weeks of ratio history on top of its own average) and G6 simply passes
    #: with a note until there is enough.
    min_bars = 330
    needs_ctx_extras = True
    extra_columns = ("stage", "line_slope_pct", "resistance", "base_weeks", "base_depth_pct",
                     "vol_ratio", "ma30", "mansfield_pct")
    #: `broke_out` is carried in extras but is a BOOL, so it is not a numeric column.
    extra_numeric_columns = extra_columns

    thesis = (
        "A stock spends most of its life going nowhere, and the 30-week line sorts the going-nowhere "
        "from the going-somewhere without predicting either. The transition out of a base is where "
        "the money is made, because that is when the holders who have been selling into every rally "
        "finally run out and institutions have to pay up for stock. Weekly bars are the point, not a "
        "convenience: they discard the four days of noise that make the same idea unusable daily."
    )
    how_it_works = (
        "Everything is decided on WEEKLY bars -- a week's high, low, Friday close and total volume. "
        "The {MA_WEEKS}-week simple average of weekly closes is the only line used.",
        "The stage is a STATE MACHINE, not a one-bar reading: it starts from the line's slope over "
        "{SLOPE_WEEKS} weeks and the close's side of the line, then a stage persists until a "
        "transition's condition has held for {CONFIRM_WEEKS} weeks. That memory is what tells a "
        "Stage 1 base from a Stage 3 top -- both are a flat line; what differs is what came before. "
        "Leaving a base for Stage 2 takes a rising line, or a close above the base's own high once "
        "it is {STAGE1_MIN_WEEKS} weeks old; a top resolves upward only above its own peak; a "
        "decline ends in a base, never straight in a new advance.",
        "The line is 'rising' when it is more than {FLAT_BAND_PCT}% above its value {SLOPE_WEEKS} "
        "weeks ago, 'falling' when more than {FLAT_BAND_PCT}% below, and flat between -- the same "
        "reading as the Learn guide's rule and the daily stage cycle.",
        "The base is the LONGEST window of at least {BASE_MIN_WEEKS} weeks whose high-to-low depth "
        "is within {BASE_MAX_DEPTH_PCT}% -- a contained range -- and resistance is that base's OWN "
        "high, the top of the zone the breakout must clear.",
        "The breakout week closes above that resistance, above a {MA_WEEKS}-week line that is no "
        "longer declining (the guide's investor rule -- rising is better and the gate note says "
        "which), with volume at least {VOL_MULT}x the average of the previous {VOL_WEEKS} weeks, "
        "and Mansfield relative strength -- the stock/index ratio against its own "
        "{MANSFIELD_WEEKS}-week zero line -- positive or at least improving over "
        "{MANSFIELD_RISE_WEEKS} weeks.",
        "Weinstein's forest-before-trees rule, both layers: no new buys while the market index "
        "(G7) or the stock's own sector index (G8) is in Stage 4.",
        "The stop is just below the higher of the {MA_WEEKS}-week line and the base's low. If that "
        "is more than {MAX_STOP_PCT}% away the trade is flagged rather than silently resized.",
    )
    caveats = (
        "**The first stage in a history is a guess.** The state machine remembers what came "
        "before, but the very first classifiable week has nothing to remember and is seeded from "
        "the one-bar reading -- so the opening stage of a short history (a recent IPO) carries "
        "the old flat-line ambiguity until the first real transition.",
        "**Weekly bars mean weekly reaction.** The exit is a weekly close below the line, so a "
        "stock can fall for four sessions before the rule looks. Weinstein placed real stop orders "
        "for exactly this reason; this strategy's stop is held between weekly decisions, which is "
        "closer to his practice than a weekly-only exit would be.",
        "**The screen gates are daily and the strategy's are weekly.** G1-G3 come from the "
        "`near_highs` screen on daily bars, which is the closest available proxy for Weinstein's "
        "universe and is not the same thing as his conditions. A stock can pass a daily 200-day "
        "test and fail the weekly 30-week one.",
        "**The sector gate leans on today's classification and a partial map.** A stock's sector "
        "comes from the current industry table (no history is kept), several sectors have no "
        "index proxy, and some proxies' history starts late -- in all of those cases G8 simply "
        "passes with a note rather than guessing.",
        "**Two stage readings exist in this app and they can disagree.** The Minervini chart "
        "layer's stage bands read the DAILY 150-day line as a stand-in; this strategy and the "
        "Stage analysis indicator read the true weekly {MA_WEEKS}-week line. Different clocks, "
        "occasionally different answers -- by design, not by accident.",
        "**Overhead supply is noted, not enforced.** The guide says to avoid stocks with a band of "
        "trapped buyers just above the breakout. The plan reports the nearest overhead level so it "
        "is visible, but no gate rejects on it.",
    )
    status = (
        "NOT YET MEASURED. The stage model is validated against the guide's Trent narrative "
        "(Stage 2 from August 2023 through October 2024, close 2,049 to 7,128; Stage 4 by March "
        "2025) but no backtest has been run, so there is no result to report and nothing here "
        "should be read as one. Expect it to resemble the other per-symbol swing strategies: all "
        "six measured so far have NEGATIVE selection, between -0.38 and -4.48, which is worse than "
        "a 10-month moving average with no edge at all (see `ma_trend`). The reason to measure this "
        "one anyway is that it is the only WEEKLY strategy here, and weekly decisions are the one "
        "structural difference none of the others test."
    )
    gate_docs = {
        "G1": "H1: the close is above its 200-day average.",
        "G2": "H2: the 200-day average is not falling.",
        "G3": "H3: the close is within the screen's distance of its 52-week high.",
        "G4": "The weekly close is above the {MA_WEEKS}-week simple average of weekly closes.",
        "G5": "That average is NOT FALLING over {SLOPE_WEEKS} weeks: no more than {FLAT_BAND_PCT}% "
              "below its value then. The guide's investor rule: the line must no longer be declining "
              "at the breakout; rising (more than {FLAT_BAND_PCT}% above) is better, and the note "
              "says which this is.",
        "G6": "Mansfield relative strength: the stock/index ratio of weekly closes against its own "
              "{MANSFIELD_WEEKS}-week average (the zero line). Positive passes; negative passes "
              "only if it has improved over the last {MANSFIELD_RISE_WEEKS} weeks. Judged on "
              "completed weeks only, so a mid-week read cannot borrow the index's Friday close.",
        "G7": "Forest before trees: the market's own index is not in Stage 4.",
        "G8": "The same test one layer down: the stock's SECTOR index is not in Stage 4. Passes "
              "with a note when no sector index is mapped or stored.",
    }
    watch_docs = {
        "W1": "The breakout week's volume was below {VOL_MULT}x the previous {VOL_WEEKS} weeks' "
              "average. Weinstein treated volume as confirmation, so this is noted but never blocks.",
        "W2": "Stage 3 warning: the stage machine reads this stock as Stage 3 -- the {MA_WEEKS}-week "
              "line flattened after an advance, which is where a top forms.",
        "W3": "The structural stop sits more than {MAX_STOP_PCT}% below the entry, so the position "
              "has to be cut rather than taken at normal size.",
    }
    setup_docs = {
        STG01: "The weekly close clears the base's own high for the first time, with the "
               "{MA_WEEKS}-week line no longer declining beneath it and the base at least "
               "{BASE_MIN_WEEKS} weeks old.",
    }
    entry_rules = (
        "Bought at the close of the breakout week. The guide's alternative is the next session's "
        "open; on weekly bars the difference is one session of drift and it is not modelled.",
        "All eight gates must pass and the setup must fire in the same week. A breakout that happens "
        "while the market is in Stage 4 is not taken.",
        "No pyramiding and no half-position-on-the-pullback variant: the guide offers it, and adding "
        "it would mean two entry prices per trade, which the plan has no way to express.",
    )
    exit_rules = (
        "A weekly close below the {MA_WEEKS}-week average -- the main exit, and the one that defines "
        "the method. Everything is held through intra-week noise above the line.",
        "Or the stop, just below the higher of the line at entry and the base's low, which is held "
        "continuously rather than checked weekly.",
        "No profit target. The target shown on the plan is the base's own height projected above the "
        "breakout and is REPORTING ONLY -- the guide sets no target and the trend ends the trade.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes and the week closed above the base's own high "
                                 "on at least {VOL_MULT}x volume.",
        "TRADE_ON_TRIGGER": "A valid Stage 1 base with the {MA_WEEKS}-week line no longer "
                            "declining beneath it, but its high not yet cleared: a buy stop rests "
                            "just above it. This is the guide's variant for anyone watching daily.",
        "WATCH_WAIT": "A valid setup held back -- the breakout came on light volume, the stage "
                      "machine reads Stage 3, or the structural stop is more than "
                      "{MAX_STOP_PCT}% away.",
        "AVOID": "A gate failed, or there is no base to trade.",
    }
    param_docs = (
        ("The line", "MA_WEEKS", "Weeks in the simple average of weekly closes."),
        ("Slope window", "SLOPE_WEEKS", "Weeks over which the line's slope is measured."),
        ("Flat band", "FLAT_BAND_PCT", "The line is rising / falling when it has moved more than this "
                                       "percent over the slope window; flat between."),
        ("Confirmation", "CONFIRM_WEEKS", "Weeks a transition's condition must hold before the stage "
                                          "changes -- and so the least a stage can last."),
        ("Base age", "STAGE1_MIN_WEEKS", "Weeks a Stage 1 base must be old before a close above its "
                                         "high counts as the breakout (under a flat line)."),
        ("Base length", "BASE_MIN_WEEKS", "Minimum weeks of sideways movement before a breakout counts."),
        ("Base depth", "BASE_MAX_DEPTH_PCT", "Maximum high-to-low depth for a window to count as a base."),
        ("RS zero line", "MANSFIELD_WEEKS", "Weeks in the stock/index ratio's own average."),
        ("RS improvement", "MANSFIELD_RISE_WEEKS", "Weeks over which a negative Mansfield reading "
                                                   "must have improved to pass."),
        ("Volume", "VOL_MULT", "Breakout week's volume against the previous weeks' average."),
        ("Volume window", "VOL_WEEKS", "Weeks in that average, per the guide."),
        ("Maximum stop", "MAX_STOP_PCT", "Beyond this the position is flagged for resizing."),
    )
    backtest_args = "--exit-mode ma --no-target"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The daily proxy for Weinstein's universe, as of one row.

        Daily because the backtest's pre-filter walks daily rows and a row carries no weekly
        history. The weekly conditions are gates G4-G6, applied in `evaluate` where the full
        weekly frame exists.
        """
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        close, s200 = last.get("close"), last.get("sma200")
        if any(pd.isna(v) for v in (close, s200)):
            return False, "insufficient history"
        if float(close) <= float(s200):
            return False, "close is not above the 200-day"
        return True, "passed"

    # ---------- the market's own stage ----------

    _mkt_stage: dict = {}

    @classmethod
    def _market_stage_weeks(cls, market_key: str):
        """{week-ending date: stage} for the market index, computed once per market.

        Cached on the class for the same reason rs_leaders caches its recovery window: every
        symbol on every bar asks the identical question of the identical series, and recomputing
        it per row dominated the scan. The stages come from `stage_series` -- the same state
        machine that judges every stock -- never a second copy of the rule.
        """
        if market_key in cls._mkt_stage:
            return cls._mkt_stage[market_key]
        from ..config import MARKETS
        from ..core import indicators as ind
        from ..marketdata import cache
        b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
        if b is None or b.empty:
            cls._mkt_stage[market_key] = None
            return None
        st = stage_series(ind.resample_weekly(b))
        cls._mkt_stage[market_key] = {d: int(v) for d, v in st.items() if v}
        return cls._mkt_stage[market_key]

    # ---------- the sector's own stage (forest before trees, the sector layer) ----------

    _sector_tickers: dict = {}   # market -> {symbol: sector-index ticker or None}
    _sector_stage: dict = {}     # (market, ticker) -> {week-ending date: stage} or None

    @classmethod
    def _sector_ticker(cls, market_key: str, symbol: str):
        """The index/ETF that stands for this stock's sector, or None when unmapped.

        The classification is TODAY'S (`symbol_industry` keeps no history), a known
        simplification: a stock's sector rarely changes, its index does.
        """
        if market_key not in cls._sector_tickers:
            from ..config import MARKETS
            from ..marketdata import industries
            cfg = MARKETS[market_key]
            cls._sector_tickers[market_key] = {
                s: cfg.sector_index_map.get(cfg.sector_alias_map.get(sec, sec))
                for s, (sec, _industry, _cap) in industries.load(market_key).items()
            }
        return cls._sector_tickers[market_key].get(symbol)

    @classmethod
    def _sector_stage_weeks(cls, market_key: str, ticker: str):
        key = (market_key, ticker)
        if key not in cls._sector_stage:
            from ..core import indicators as ind
            from ..marketdata import cache
            b = cache.load_cached(market_key, ticker)
            if b is None or b.empty:
                cls._sector_stage[key] = None
            else:
                st = stage_series(ind.resample_weekly(b))
                cls._sector_stage[key] = {d: int(v) for d, v in st.items() if v} or None
        return cls._sector_stage[key]

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """Live: no new buys while the market index is itself in Stage 4."""
        stages = self._market_stage_weeks(market_key)
        if not stages:
            return default
        last_week = max(stages)
        return stages[last_week] == 4

    # ---------- evaluation ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        wk = ctx.weekly
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)

        if len(wk) < MA_WEEKS + SLOPE_WEEKS + 1:
            for g in ("G4", "G5", "G6", "G7", "G8"):
                result.fail(g, "insufficient weekly history")
            result.recompute_first_fail()
            return result

        # Mid-week, the last weekly bar is this week IN PROGRESS: built from daily bars up to the
        # as-of date but labelled with its Friday. The stock's own partial bar is fine (it holds
        # no future data), but anything joined by LABEL -- the benchmark ratio, the market's and
        # sector's stage-by-week dicts -- must use completed weeks only, or a Tuesday evaluation
        # would read the index's Friday close.
        as_of = ctx.daily.index[-1]
        done = wk.loc[wk.index <= as_of]
        line = ma30(wk)
        lv = float(line.iloc[-1]) if pd.notna(line.iloc[-1]) else float("nan")
        wclose = float(wk["close"].iloc[-1])
        state, slope = line_state(wk)

        if lv != lv:
            result.fail("G4", "30-week average not available")
        elif wclose > lv:
            result.ok("G4", f"weekly close {wclose:.2f} above the 30-week line {lv:.2f}")
        else:
            result.fail("G4", f"weekly close {wclose:.2f} is below the 30-week line {lv:.2f}")

        # The guide's investor rule is "no longer declining": flat passes, rising is better,
        # and the note says which one this is.
        if state != "falling":
            result.ok("G5", f"30-week line {state} ({slope:+.2f}% over {SLOPE_WEEKS} weeks)")
        else:
            result.fail("G5", f"30-week line is falling ({slope:+.2f}% over {SLOPE_WEEKS} weeks)")

        # Mansfield relative strength: the stock/index ratio against its own 52-week average
        # (the zero line). Positive, or at least improving from negative, passes.
        mkt = _market_of(ctx.symbol)
        bench_wk = self._bench_weekly(mkt)
        ratio = None
        if bench_wk is not None:
            b = bench_wk["close"].reindex(done.index).ffill()
            ratio = (done["close"] / b).dropna()
        if bench_wk is None:
            result.ok("G6", "no benchmark stored — relative strength not checked")
        elif ratio is None or len(ratio) <= MANSFIELD_WEEKS + MANSFIELD_RISE_WEEKS:
            result.ok("G6", "insufficient weekly history for the RS zero line — not checked")
        else:
            zero = ratio.rolling(MANSFIELD_WEEKS).mean()
            m = (ratio / zero - 1) * 100
            m_now, m_then = float(m.iloc[-1]), float(m.iloc[-1 - MANSFIELD_RISE_WEEKS])
            ctx.extras["mansfield_pct"] = round(m_now, 2)
            if m_now > 0:
                result.ok("G6", f"Mansfield RS {m_now:+.1f}% above its {MANSFIELD_WEEKS}-week zero line")
            elif m_now > m_then:
                result.ok("G6", f"Mansfield RS negative ({m_now:+.1f}%) but improving "
                                f"({m_then:+.1f}% {MANSFIELD_RISE_WEEKS} weeks ago)")
            else:
                result.fail("G6", f"Mansfield RS {m_now:+.1f}% below its zero line and not improving "
                                  f"({m_then:+.1f}% {MANSFIELD_RISE_WEEKS} weeks ago)")

        stages = self._market_stage_weeks(mkt)
        if not stages:
            result.ok("G7", "no benchmark stored — market stage not checked")
        else:
            prior = [d for d in stages if d <= as_of]
            mstage = stages[max(prior)] if prior else 0
            if mstage == 4:
                result.fail("G7", "the market index is in Stage 4")
            else:
                result.ok("G7", f"market index in Stage {mstage or 'unknown'}")

        tick = self._sector_ticker(mkt, ctx.symbol)
        sstages = self._sector_stage_weeks(mkt, tick) if tick else None
        if not sstages:
            result.ok("G8", "no sector index stored — sector stage not checked")
        else:
            prior = [d for d in sstages if d <= as_of]
            sstage = sstages[max(prior)] if prior else 0
            if sstage == 4:
                result.fail("G8", f"sector index {tick} is in Stage 4")
            else:
                result.ok("G8", f"sector index {tick} in Stage {sstage or 'unknown'}")

        # ---- the base, its resistance, and the breakout week
        hist = wk.iloc[:-1]
        # The LONGEST contained range ending last week: walk back from the cap and take the first
        # window whose high-to-low depth is within BASE_MAX_DEPTH_PCT. Longest rather than
        # shortest, because a 40-week base is a stronger setup than a 12-week one and taking the
        # shortest qualifying window would report every long base as a minimal one. Resistance is
        # that base's OWN high -- the top of the zone the breakout must clear -- not a fixed
        # lookback, which could reach past the base into an old spike high.
        base_weeks, base_depth, resistance = 0, float("nan"), float("nan")
        for n in range(min(len(hist), BASE_MAX_WEEKS), BASE_MIN_WEEKS - 1, -1):
            w = hist.iloc[-n:]
            hi, lo = float(w["high"].max()), float(w["low"].min())
            if hi > 0 and (hi - lo) / hi * 100 <= BASE_MAX_DEPTH_PCT:
                base_weeks, base_depth, resistance = n, (hi - lo) / hi * 100, hi
                break
        vol = float(wk["volume"].iloc[-1])
        vbase = (float(hist["volume"].iloc[-VOL_WEEKS:].mean())
                 if len(hist) >= VOL_WEEKS else float("nan"))
        vol_ratio = vol / vbase if vbase == vbase and vbase else float("nan")
        prev_close = float(hist["close"].iloc[-1]) if len(hist) else float("nan")

        # Two states, one setup. `broke` is the week that cleared resistance; `armed` is a valid
        # base with the line no longer declining beneath it and resistance still overhead, which
        # is the guide's own variant for anyone watching daily ("buy on the day the price clears
        # resistance, with a buy stop just above it"). Both are the same setup at different
        # moments, which is what the TRADE_ON_TRIGGER label exists for.
        base_ok = bool(resistance == resistance and base_weeks >= BASE_MIN_WEEKS
                       and wclose > lv and state != "falling")
        broke = bool(base_ok and prev_close <= resistance < wclose)
        armed = bool(base_ok and not broke and wclose <= resistance)
        stage_now = stage_of(done)
        result.setups[STG01] = broke or armed
        result.watch_flags["W1"] = bool(broke and not (vol_ratio >= VOL_MULT))
        result.watch_flags["W2"] = stage_now == 3
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = f"volume {vol_ratio:.2f}x the {VOL_WEEKS}-week average"
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = f"Stage 3: the 30-week line flattened after the advance ({slope:+.2f}%)"

        ctx.extras.update(
            broke_out=bool(broke),
            stage=stage_now or None,
            line_slope_pct=round(slope, 2) if slope == slope else None,
            resistance=round(resistance, 2) if resistance == resistance else None,
            base_weeks=base_weeks or None,
            base_depth_pct=round(base_depth, 2) if base_depth == base_depth else None,
            vol_ratio=round(vol_ratio, 2) if vol_ratio == vol_ratio else None,
            ma30=round(lv, 2) if lv == lv else None,
        )
        result.recompute_first_fail()
        return result

    _bench_wk: dict = {}

    @classmethod
    def _bench_weekly(cls, market_key: str):
        if market_key not in cls._bench_wk:
            from ..config import MARKETS
            from ..core import indicators as ind
            from ..marketdata import cache
            b = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
            cls._bench_wk[market_key] = ind.resample_weekly(b) if b is not None and len(b) else None
        return cls._bench_wk[market_key]

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        return 1.0 if result.setups.get(STG01) else 0.0

    # ---------- plan ----------

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """For the chart's Trade setups layer (strategies/live_setups.py), the weekly structure the
        setup was judged on, from the same windows evaluate() reads: the {MA_WEEKS}-week line over the
        base (zone 1, with the gates that test it), the Stage 1 base -- the longest window of at least
        {BASE_MIN_WEEKS} weeks within {BASE_MAX_DEPTH_PCT}% -- and its own high, the resistance the
        breakout week has to close above. Drawing only: no rule reads it."""
        wk, e = ctx.weekly, ctx.extras
        day = lambda ts: str(pd.Timestamp(ts).date())
        last_day = day(ctx.daily.index[-1])
        out: list[dict] = []
        n, res = e.get("base_weeks"), e.get("resistance")
        hist = wk.iloc[:-1]
        # the line: weekly points over the base and through the current week, ending on the last
        # session (a week's label is its Friday, which can lie ahead of the data mid-week)
        span = ma30(wk).iloc[-((n or BASE_MIN_WEEKS) + 1):].dropna()
        if len(span) >= 2:
            pts = [{"at": day(t), "price": float(v), "label": ""} for t, v in span.iloc[:-1].items()]
            state, slope = line_state(wk)
            pts.append({"at": last_day, "price": float(span.iloc[-1]), "label": f"30-week line {state} ({slope:+.1f}%)"})
            out.append({"shape": "path", "from": pts[0]["at"], "to": last_day, "points": pts, "role": "uptrend",
                        "label": f"{MA_WEEKS}-week line"})
        if n and res and len(hist) >= n:
            w = hist.iloc[-n:]
            start = day(pd.Timestamp(w.index[0]) - pd.Timedelta(days=4))   # the week's Monday, not its Friday label
            lo = float(w["low"].min())
            out.append({"shape": "box", "from": start, "to": day(w.index[-1]), "top": float(res), "bottom": lo, "role": "base",
                        "label": f"Stage 1 base · {n} weeks · {(res - lo) / res * 100:.0f}% deep"})
            out.append({"shape": "level", "from": start, "to": last_day, "price": float(res), "role": "pivot",
                        "label": f"resistance {res:,.2f} · the base's high"})
        return out

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no Stage 2 breakout this week")
        e = ctx.extras
        line, resistance = e.get("ma30"), e.get("resistance")
        if line is None or resistance is None:
            return PlanChoice(None, None, "missing 30-week line / resistance")
        # A completed breakout is bought at the close; an armed base rests a buy stop one tick
        # above resistance, so the trade only happens if the market actually clears it.
        if e.get("broke_out"):
            entry = float(ctx.close)
        else:
            entry = round_tick(float(resistance) + cfg.tick_size, cfg.tick_size, "up")
        n = int(e.get("base_weeks") or BASE_MIN_WEEKS)
        base_low = float(ctx.weekly["low"].iloc[-(n + 1):-1].min())
        # "Just below the HIGHER of the line and the base's low" -- the higher, because a stop under
        # the base low when the line sits above it gives away far more than the method intends.
        structural = max(float(line), base_low)
        floor_ = entry * (1 - MAX_STOP_PCT / 100)
        result.watch_flags["W3"] = bool(structural < floor_)
        stop = round_tick(max(structural, floor_), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        # REPORTING ONLY: the guide sets no target, so this is the base's own height projected
        # above the breakout -- a conventional measured move, never a rule this strategy acts on.
        base_height = max(float(resistance) - base_low, risk)
        target = entry + base_height * BASE_TARGET_MULT
        r = (target - entry) / risk
        ctx.extras["structural_r"] = round(r, 2)
        from ..core import swings as sw
        plan = TradePlan(plan="STG", setup=STG01, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry, r_multiple=round(r, 2),
                         nearest_overhead_above_entry=sw.nearest_overhead_above(entry, ctx.overhead))
        return PlanChoice(plan, None,
                          f"resistance {resistance:.2f}, stop {(entry - stop) / entry * 100:.1f}% "
                          f"below entry ({'line' if float(line) >= base_low else 'base low'})")

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away,
                 regime_downgrade_active) -> Decision:
        q = self.setup_quality(result)
        if not result.hard_gates_passed:
            return Decision(LABELS["AVOID"], LABELS["AVOID"],
                            f"fails {result.first_hard_fail}: "
                            f"{result.hard_notes.get(result.first_hard_fail, '')}", 0.0, 0.0, q)
        if plan is None or not plan.is_valid:
            return Decision(LABELS["AVOID"], LABELS["AVOID"], "no valid entry plan", 0.0, 0.0, q)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if ctx.extras.get("broke_out"):
            label, reasons = "TRADE_HIGH_CONFIDENCE", ["Stage 2 breakout above the base's high"]
        else:
            label, reasons = "TRADE_ON_TRIGGER", ["valid base, buy stop above its high"]
        if result.watch_flags.get("W1"):
            label = "WATCH_WAIT"; reasons.append("breakout volume below the threshold")
        if result.watch_flags.get("W2"):
            label = "WATCH_WAIT"; reasons.append("Stage 3: the line flattened after the advance")
        if result.watch_flags.get("W3"):
            label = "WATCH_WAIT"; reasons.append(f"structural stop more than {MAX_STOP_PCT:g}% away")
        before = label
        # Weinstein's forest-before-trees rule again, this time at the portfolio level: the gate
        # G7 check is point-in-time on the signal week, and this is the live downgrade.
        if regime_downgrade_active and label.startswith("TRADE"):
            label = "WATCH_WAIT"; reasons.append("market not in an uptrend: no new buys")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons), risk_pct,
                        plan.r_multiple, q)

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        e = ctx.extras
        return {
            "stage": e.get("stage"), "line_slope_pct": e.get("line_slope_pct"),
            "resistance": e.get("resistance"), "base_weeks": e.get("base_weeks"),
            "vol_ratio": e.get("vol_ratio"), "ma30": e.get("ma30"),
            "base_depth_pct": e.get("base_depth_pct"),
            "structural_r": e.get("structural_r"),
        }
