"""Minervini SEPA: the VCP detector of the written backtest specification (research/minervini-backtest-spec.md),
traded and managed as the SEPA Learn guide describes ("SEPA and the VCP", research/learn-strat-vcp-sepa.md).

Up to 1.7 every rule followed the written spec. Since 1.8 the base, the setups and the entries still do,
while the stop limit, the exits, the market filter, the results blackout, the liquidity floor, progressive
exposure and the low cheat follow the guide (see the changelog). What differs from the retired `minervini`:

- **Base detection** (core/vcp_spec.py) anchors on the base high — the last confirmed swing high no
  later close has exceeded — and measures every contraction from there, with the spec's numbers:
  swing points of `SWING_K` bars each side, a prior advance of `PRIOR_ADVANCE_PCT`%, a base of
  `BASE_MIN_DAYS`–`BASE_MAX_DAYS` sessions, at least `MIN_CONTRACTIONS` contractions whose RESET RULE
  holds (`MIN_FROM_REFERENCE` of them since the last widening, the final one at most
  `FINAL_REF_RATIO` × that widening), a base no deeper than `MAX_BASE_DEPTH_PCT`%, a final tight area of
  at least `TIGHT_MIN_DAYS` sessions within `TIGHT_PCT`%, a pivot in the base's upper zone
  (`UPPER_ZONE`, or within `PIVOT_NEAR_HIGH` of the base high), and
  volume drying up to `DRYUP_RATIO` × its average.
- **MV-01 is the breakout day itself**, judged against the pivot frozen on the day before (the
  breakout bar must not move its own pivot), and confirmed by volume, a close in the upper half of
  the range and a close no more than `BUY_RANGE_PCT`% past the pivot. It is entered at the next
  open (EN-01). **MV-02** is the coil below the pivot, entered by a buy-stop through it (EN-02).
- **Stops** sit `STOP_BUFFER_PCT`% under the tight low and may be no more than `MAX_STOP_PCT`% below the
  fill (checked at the fill, not at the signal). One entry per base.
- **Exits** (the portfolio simulator's `minervini` mode, defaults from the constants below): the stop,
  breakeven at `BREAKEVEN_R`, a part sold into strength (a close `STRENGTH_EXT_PCT`% above the 50-day, or a
  climax run), the rest on a close below the 50-day, and a time stop. The failed-breakout exit is off.

The backtest adds the cross-sectional parts a one-symbol evaluation cannot do: the RS rating (TT-08),
ranking by RS then tightness, the market filter, the base number, and the spec's costs
(backtesting/backtest.py `--spec`).
"""

import dataclasses

import pandas as pd

from ..marketdata import corporate_actions
from ..config.base import MarketConfig
from ..core import vcp_spec
from ..core import swings as sw
from ..core.context import StockContext
from ..screens.criteria import (  # noqa: F401 (doc placeholders)
    MAX_PCT_BELOW_52W_HIGH, MIN_PCT_ABOVE_52W_LOW, RS_MIN_SCORE, RS_MIN_RANK, SMA200_RISING_BARS,
)

#: TT-03 has two levels, and only the first can stop a trade.
#:
#:   minimum   SMA200(t) > SMA200(t - SMA200_RISING_BARS)        -- 21 sessions, about a month
#:   preferred SMA200(t) > SMA200(t - SMA200_RISING_PREF_BARS)   -- 100 sessions, about 4-5 months
#:
#: Minervini asks for a 200-day that has been rising "for at least one month, preferably for 4-5
#: months or longer". The month is the requirement and lives in the SCREEN (criteria C5, the
#: strategy's gate G5); the 4-5 months is a preference about the QUALITY of the trend, which is a
#: trade judgement rather than a qualification, so it belongs here and is a watch flag (W5).
#:
#: Deliberately not a gate. Promoting it would silently replace the stated minimum with 100
#: sessions and reject stocks the Trend Template admits -- the opposite of what "preferably"
#: means. It is recorded so the maturity of the trend is visible on every signal, and so the
#: choice to tighten it later is a one-line change with a measurement behind it.
SMA200_RISING_PREF_BARS = 100
#: W5 as a RULE instead of a note: 1 holds a plan at WATCH (no new buy) while the 200-day has not risen
#: over SMA200_RISING_PREF_BARS sessions -- Minervini's "preferably 4-5 months". Off until it is measured
#: (`--const SMA200_PREF_REQUIRED=1`); `--const SMA200_RISING_PREF_BARS=N` sets how long.
SMA200_PREF_REQUIRED = 0
from .base import LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan, tradable_point_in_time
from .trend_pullback import round_tick

MV01 = "S1"   # MV-01: confirmed breakout through the frozen pivot
MV02 = "S2"   # MV-02: coiled just below the pivot
MV03 = "S3"   # MV-03: low cheat, a shelf in the lower third of the base
MV04 = "S4"   # MV-04: cheat / 3C, a shelf in the middle third of the base
MV05 = "S5"   # MV-05: power play -- an explosive run, then a short tight flag
FLAT = "S6"   # flat base: a shallow, sideways base with no pivot but its own high (1.28)

# ---- section 5: base and VCP (core/vcp_spec.py)
SWING_K = 5
MIN_SWING_PCT = 2.0
PRIOR_ADVANCE_PCT = 30.0
BASE_MIN_DAYS = 15
BASE_MAX_DAYS = 325
MIN_CONTRACTIONS = 2
MAX_CONTRACTIONS = 6         # now a QUALITY FLAG, not a rejection (v2 §3.4): log and flag above this
# VCP-05 is the depth of the BASE now, not of the first contraction (v2 §2.5): 50% is the limit,
# 35% a quality flag. Deeper bases appear in bear markets and still produce leaders.
MAX_BASE_DEPTH_PCT = 50.0
DEEP_BASE_FLAG_PCT = 35.0
# ---- VCP-06, the reset rule. Replaces SHRINK (= 0.80), which required EVERY contraction to be
# smaller than the one before it and so rejected a base for a single deeper pullback early on --
# the case Minervini describes as resetting the count, not failing the base.
WIDEN_TOL = 1.1              # a contraction more than this x the previous one is a widening
MIN_FROM_REFERENCE = 2       # contractions from the most recent widening onward, inclusive
FINAL_REF_RATIO = 0.6        # final contraction / reference contraction, at most
# Every contraction after the reference must also be smaller than the one before it. The final
# ÷ reference ratio alone does not say that: 25, 10, 9, 9.5 has a final at 0.38x its reference
# and a right side quietly getting looser. It also closes the hole the widening tolerance leaves,
# where the DEEPEST pullback is only fractionally deeper than its predecessor (20 then 21) and so
# never counts as a widening.
UNDERCUT_RECOVERY_DAYS = 5   # sessions an undercut has to reclaim the old low; logged, not a gate
# The tight area is the final contraction itself, so this is a MINIMUM age, not a fixed window
# (v2 §4.1). The old TIGHT_DAYS = 10 was a window that could only be right by coincidence.
TIGHT_MIN_DAYS = 5
# 0.67 rather than 2/3: the doc renderer prints a float as it is, so 2/3 reached the page as
# "0.666667 or more of the way up the base range". 0.67 is inside v2's own 0.60-0.75 test range,
# and 0.0033 of a base's range is far below the precision of a pivot's position in it.
UPPER_ZONE = 0.67            # VCP-09: pivot this far up the base range is a standard pivot buy
MAX_CLOSES_BELOW_200 = 10    # VCP-03: sessions below the 200-day allowed inside the base
TIGHT_PCT = 10.0
PIVOT_NEAR_HIGH = 0.90
DRYUP_RATIO = 0.80           # VCP-10: tight-area average volume against its 50-day average …
DRYUP_QUIET_DAYS = 2         # … or this many sessions at or under DRYUP_QUIET_RATIO x it
DRYUP_QUIET_RATIO = 0.5
# ---- MV-05, the power play (v2). The base rules cannot see one and that is not a tuning problem:
# the flag is shorter than BASE_MIN_DAYS, the run is far steeper than any normal prior advance, and
# the averages have not caught up, so the base path rejects it before a contraction is measured.
# Detected separately (core/vcp_spec.detect_power_play) so the two never compete.
PP_RUN_WINDOW = 40           # sessions the run is measured over …
PP_RUN_MULT = 2.0            # … during which price at least doubled, measured AT the flag high
PP_FLAG_MIN_DAYS = 10        # the pause: about 2 …
PP_FLAG_MAX_DAYS = 30        # … to 6 weeks
PP_FLAG_MAX_DEPTH_PCT = 25.0
# ---- S6, the flat base (1.28). "Not all consolidations have tight pivot points. When a flat base
# occurs with no real pivot other than the high of the base, an investor can look to buy as the
# stock moves above the highest price at the top of the base provided that the base corrects no
# more than 10 or 15 percent" -- a base "four to seven weeks in duration" with little volatility
# contraction to measure. Before 1.28 such a base could only fail VCP-04 or VCP-06.
FLAT_MIN_DAYS = 20          # about four weeks …
FLAT_MAX_DAYS = 35          # … to seven
FLAT_MAX_DEPTH_PCT = 15.0   # base high to base low, at most
FLAT_PIVOT_DAYS = 10        # the sessions before the breakout: their low is the stop's reference, and
                            # their volume must pass VCP-10's dry-up test ("every correct pivot point
                            # will develop with a contraction in volume")

# PP-06 (1.27): the flag's tight area must show VCP-10's volume dry-up. Minervini's third power-play
# condition -- "within the base (usually just days before a breakout), volume will contract
# considerably" -- was the one 1.26 did not check. 0 turns it off.
PP_DRYUP = 1
# ---- young listings (1.28). Minervini applies the 200-day test "provided that 200 days of trading
# in the stock has occurred", and several of the book's examples are a stock's first bases after
# its listing (MercadoLibre and New Oriental 2007, Dick's 2003). 1 judges such a stock on the
# history it has: a Trend Template condition whose average or 52-week range needs more sessions
# than exist is waived, or read over the history since listing (`young_template_row`); the base's
# prior advance runs from the low since listing (VcpParams.young_listing); and its RS rating
# compares its return since listing with the market's over the same sessions
# (backtesting/spec.rs_ratings). 0 = such a stock waits for a year of history, as in 1.27.
YOUNG_LISTING = 1
YOUNG_MIN_BARS = 60     # sessions listed before anything is judged: core.context's minimum, past the 50-day

# MV-03/MV-04 (1.27): the cheat shelf must show VCP-10's volume dry-up as well as its tightness.
# Minervini: a valid cheat area "should exhibit a contraction in volume as well as tightness in the
# range of price". Until 1.27 a cheat had no volume test at all, so a base that VCP-10 rejected for
# volume could still be bought through its shelf. 0 = tightness only, as before.
CHEAT_DRYUP = 1

# What each VCP failure code means TODAY, read from core/vcp_spec.detect. One table, used by the
# chart's failed-base titles and by the Candidates tab's stage view. The chart's own copy had gone
# stale -- VCP-05 still said "first pullback too deep" two versions after it became the depth of the
# BASE, and VCP-06 "pullbacks don't shrink" after it became the reset rule.
VCP_RULES = {
    "VCP-01": "no qualifying advance before the base",
    "VCP-02": "no base yet",
    "VCP-03": "trend broke during the base",
    "VCP-04": "too few pullbacks",
    "VCP-05": "base too deep",
    "VCP-06": "volatility hasn't contracted since it last widened",
    "VCP-07": "lower lows",
    "VCP-08": "final tight area not ready",
    "VCP-09": "pivot low in the base (cheat territory)",
    "VCP-10": "no volume dry-up",
}

POWER_PLAY = vcp_spec.PowerPlayParams(
    run_window=PP_RUN_WINDOW, run_mult=PP_RUN_MULT, flag_min_days=PP_FLAG_MIN_DAYS,
    flag_max_days=PP_FLAG_MAX_DAYS, flag_max_depth_pct=PP_FLAG_MAX_DEPTH_PCT,
    tight_pct=TIGHT_PCT, tight_min_days=TIGHT_MIN_DAYS, swing_k=SWING_K,
    dryup=PP_DRYUP, dryup_ratio=DRYUP_RATIO, dryup_quiet_days=DRYUP_QUIET_DAYS,
    dryup_quiet_ratio=DRYUP_QUIET_RATIO,
)

VCP = vcp_spec.VcpParams(
    swing_k=SWING_K, min_swing_pct=MIN_SWING_PCT, prior_advance_pct=PRIOR_ADVANCE_PCT,
    base_min_days=BASE_MIN_DAYS, base_max_days=BASE_MAX_DAYS, min_contractions=MIN_CONTRACTIONS,
    max_contractions=MAX_CONTRACTIONS, max_base_depth_pct=MAX_BASE_DEPTH_PCT,
    deep_base_flag_pct=DEEP_BASE_FLAG_PCT,
    dryup_quiet_days=DRYUP_QUIET_DAYS, dryup_quiet_ratio=DRYUP_QUIET_RATIO,
    widen_tol=WIDEN_TOL, min_from_reference=MIN_FROM_REFERENCE, final_ref_ratio=FINAL_REF_RATIO,
    undercut_recovery_days=UNDERCUT_RECOVERY_DAYS,
    tight_min_days=TIGHT_MIN_DAYS, upper_zone=UPPER_ZONE, max_closes_below_200=MAX_CLOSES_BELOW_200,
    tight_pct=TIGHT_PCT, pivot_near_high=PIVOT_NEAR_HIGH, dryup_ratio=DRYUP_RATIO,
    cheat_dryup=CHEAT_DRYUP, young_listing=YOUNG_LISTING,
)

# ---- section 6: setups
COIL_PCT = 8.0          # MV-02: close within this % below the pivot
VOL_MULT = 1.4          # MV-01a: breakout volume ≥ this × the 50-day average
BUY_RANGE_PCT = 5.0     # MV-01b: close no more than this % above the pivot (and EN-01/EN-02 fills)
UPPER_HALF = 0.5        # MV-01c: close in at least this fraction of the day's range

# ---- section 8: stop
# MV-03, the low cheat. ON since 1.8, because the Learn guide this strategy follows
# lists it as one of the three entries. It was switched off in 1.5 on a measured
# reason that still stands -- India 2010 onward, 25 trades, a 4% win rate and
# -0.515R average, Rs257k of losses against the 3C's Rs213k gain -- so read its
# trades separately. An int rather than a bool so spec_params fingerprints it:
# flipping it has to change the spec_id. `--const LOW_CHEAT_ENABLED=0` turns it off.
LOW_CHEAT_ENABLED = 1

# Block a cheat when the base failed VCP-09 -- its own pivot sits below the upper zone, so the
# stock has not repaired much and the shelf is being bought into a base that is not yet working.
# OFF by default: it was found by slicing the India run that is now being used to judge it, which
# is selection on the thing being measured, so it ships as a sweepable experiment rather than a
# rule. `--const CHEAT_BLOCK_VCP09=1` turns it on. An int, not a bool, so spec_params fingerprints
# it and a variant run cannot overwrite the shipped one.
CHEAT_BLOCK_VCP09 = 0

CHEAT_SHELF_DAYS = 7    # MV-03/MV-04: sessions in the shelf (mirrors VcpParams.cheat_shelf_days)
CHEAT_SHELF_PCT = 8.0   # MV-03/MV-04: widest shelf that counts  (mirrors VcpParams.cheat_shelf_pct)

STOP_BUFFER_PCT = 0.5   # SL-01: stop this % under the tight low
MAX_STOP_PCT = 10.0     # SL-03: skip a fill whose stop is further below it than this (the guide's limit)
# EN-04's limit: how many times one base may be bought. 1 = the shipped rule, a base is barred
# for good after one entry. Minervini re-buys a leader that shook him out, and the ladder makes
# that common here -- EX-03 moves the stop to breakeven at +{BREAKEVEN_R}R, so an ordinary
# pullback ends the trade at zero and, today, ends the base with it. Raising this lets only a
# SHAKEOUT reopen a base (a stop or a breakeven stop, never a trend exit, which says the move is
# over), and the setup still has to re-fire on its own. 2 since 1.27: Minervini's "failure reset" --
# a pivot failure that resets within days -- is one of his own setups ("some of my biggest winners
# were stocks that stopped me out and then reset"), so a shakeout now leaves the base buyable once
# more. `--const MAX_ENTRIES_PER_BASE=1` restores 1.26.
MAX_ENTRIES_PER_BASE = 2
NOMINAL_TARGET_R = 3.0  # reporting only: the exits are rules (and EX-04 sells a third at 3R)
# Minervini's stated minimum reward-to-risk (ChartMill's SEPA write-up and the
# books both give 2:1 as the floor, 3:1 preferred). A rejection threshold, never
# a target floor: a setup projecting less is skipped, not padded.
MIN_STRUCTURAL_R = 2.0
# How far above the BASE HIGH a swing high has to sit before it counts as
# external supply rather than part of the base's own ceiling. A base's ceiling
# is not a single line: `swings.overhead_levels` collects every swing high, and
# a consolidation prints several within a hair of its high (both sides of the
# range, every retest of the pivot). `chart_pattern.overhead_cluster_atr` is the
# same guard for the same reason.
OVERHEAD_CLUSTER_ATR = 1.0

# ---- section 9: exits. ExitPolicy (backtesting/portfolio_sim.py) takes its defaults
# from these, so a --spec run trades exactly these numbers.
# EX-03's trigger: the guide's +2R. (1.6 raised it to 2.5R -- trades exiting on the
# breakeven stop had reached a median 2.75R and realised -0.04R -- and 1.8 puts the
# guide's figure back; `--breakeven-r 2.5` reproduces 1.7.)
BREAKEVEN_R = 2.0
# EX-04's trigger, and the other half of EX-03. Minervini sells into strength and THEN
# raises the stop; this implementation did the raise without the sale, which converts an
# unrealised gain into nothing instead of into cash. 1.6 saw the symptom -- breakeven-stop
# exits had reached a median 2.75R and realised -0.04R -- and moved the threshold, which
# treats a paired rule as a single one. Measured on the 1.22 runs, every breakeven-stop exit
# in both books came from a trade that had reached +2R: 28 of India's 95 such trades and 26
# of the US's 114 ended at a median -0.03R and -0.01R. Banking {STRENGTH_FRAC} at the same
# +2R the stop moves on is the guide's own sequence, so the two fire on one bar.
PARTIAL_R = 2.0
# EX-02, the failed-breakout exit (a close back below the pivot within N sessions).
# OFF: the guide leaves a dip below the pivot to the stop, and dips are normal --
# on stored data about two in three breakouts close back below the pivot within ten
# sessions. In 1.7 this exit closed ~80% of trades for about -0.3R each.
FAIL_DAYS = 0
# EX-02b (1.27), the breakout that fails its 20-day average: a close below the 20-day average within
# this many sessions of the buy sells at the next open. Minervini judges a breakout by the 20-day,
# not by the pivot: "the stock price should hold its 20-day moving average and in most cases should
# not close below it", and a squat that closes below it "lowers the probability of success". He gives
# a squat up to ten days to recover, which is the window. 0 = off.
# OFF since 1.31: at 10 sessions it sold 254 of 581 US and 112 of 225 Indian trades in the 2013-2021
# optimise window for about -0.5R each, and cut the trend-exit winners those trades would have become
# (India 71 -> 50): expectancy -0.10R against -0.04R off (US), +0.05R against +0.20R off (India).
FAIL_SMA20_DAYS = 0
# EX-04, selling into strength: a part of the position once the close is this far
# above the 50-day average, at the next open. Replaces 1.7's "a third at 3R".
STRENGTH_EXT_PCT = 25.0
STRENGTH_FRAC = 0.33   # 1.22: was 1 / 3, which the page rendered as "0.333333 of the position"
# EX-05, a climax run, sells that same part rather than the whole position: the
# guide sells into strength in part and the rest into weakness (EX-06).
CLIMAX_IS_PARTIAL = 1
# EX-06, the close below the 50-day average, no longer needs above-average volume.
TREND_EXIT_NEEDS_VOLUME = 0
# EX-07, the time stop: sold if the high has not reached +1R within this many sessions.
TIME_STOP_DAYS = 15
# EN-02 fills on the close through the pivot; a fill on volume under VOL_MULT x the
# 50-day average is not a valid breakout and is sold at the next open.
LIGHT_VOLUME_EXIT = 1

# ---- section 10 / backtest (backtesting/backtest.py --spec)
# PE-01..PE-04 (progressive exposure), on by default since 1.8 (`--pe` in backtest_args).
# Minervini does not risk a flat fraction every time: he opens small and only pays full
# size once the account is making money, so a losing run costs progressively less. The
# state is read once per session from trades that closed EARLIER, never from the session
# being sized.
PE_WINDOW = 10                  # PE-01: closed trades in the rolling window
PE_WARMUP = 5                   # PE-02: pilot size until this many trades have closed
PE_PILOT_FRAC = 0.5             # PE-02: fraction of the risk budget at pilot size
PE_PRESS_NET_R = 4.0            # PE-04: net R that unlocks the press (only with --pe-press)
MKT_CONFIRM_DAYS = 5            # MKT-01: sessions risk-on must hold before new buys resume

# The market filter (backtesting/spec.py market_ok). 1 = the guide's test, 0 = 1.7's MKT-01.
# The guide's: the benchmark closes above its MKT_INDEX_SMA-day average, AND the share of
# the market's most-traded stocks above their own 50-day average is above
# MKT_BREADTH_MIN_PCT or higher than MKT_BREADTH_RISING_DAYS sessions earlier.
MKT_GUIDE = 1
MKT_INDEX_SMA = 50
MKT_BREADTH_MIN_PCT = 50.0
MKT_BREADTH_RISING_DAYS = 5
# v2's own definition of risk-on adds a slope term: the index above its 50-day average AND that
# average higher than it was MKT_SMA_RISING_DAYS sessions ago. Breadth stays -- it answers a
# different question (how MANY stocks participate, not where one index sits) -- so the gate is
# "above a RISING average, with breadth behind it".
# MEASURED COST: the slope term takes risk-on days from 61.3% to 51.5% (India) and 68.6% to 61.4%
# (US) over 2013 onward -- about ten points of the calendar. That is a real tightening, so it is a
# sweepable parameter: `--const MKT_SMA_RISING_DAYS=0` turns the term off and restores the
# above-the-average-only test.
MKT_SMA_RISING_DAYS = 10
# Leadership (1.32): Minervini reads the market through its leaders, not an index average -- in a
# healthy market more stocks make new 52-week highs than new lows. With MKT_HIGHS_LOWS_DAYS set, the
# filter also needs the new highs over that many sessions to exceed MKT_HIGHS_LOWS_RATIO x the new
# lows (among the 1,000 most-traded stocks, breadth_daily). 0 = off. Off by default until measured:
# applied to 1.31's trades it dropped 2-24 of 490 US trades averaging about 0R (the index and breadth
# terms already block those days) and 17-23 of 199 Indian trades averaging about -0.2R.
MKT_HIGHS_LOWS_DAYS = 0
MKT_HIGHS_LOWS_RATIO = 1.0

MAX_POSITIONS = 8               # PF-02
MAX_OPEN_RISK_PCT = 6.0         # PF-04
MAX_ADV_PCT = 5.0               # SL-06
# No new buy with results due within this many calendar days: live from the earnings
# calendar, in a backtest from an ESTIMATED announcement date unioned with the stored
# filing date (spec.results_blackout -- the gap happens on the announcement, and the
# filing runs weeks behind it).
EARNINGS_BLACKOUT_DAYS = 14

# The guide's liquidity floor. Turnover is the 50-day average volume x the close, which is
# split-invariant, so it applies in backtests too. The price floor is LIVE ONLY: a backtest
# reads split-adjusted history, where a winner's early price is divided by every later split
# (the reason 1.2 dropped the market's own price floor from backtests).
MIN_TURNOVER_INR_CR = 10           # ₹ crore a day
MIN_TURNOVER_USD_M = 20            # $ million a day
LIVE_MIN_PRICE_INR = 100
LIVE_MIN_PRICE_USD = 15

# The guide's fundamentals, as the backtest's `--fundamentals guide` level (off by default:
# stored results cover India only from late 2020). Quarterly EPS growth on the year-ago
# quarter, faster than the quarter before; sales growth; net margin no more than
# FUND_MARGIN_SLACK_PP points below the year-ago quarter's.
FUND_EPS_GROWTH_MIN_PCT = 20.0
FUND_SALES_GROWTH_MIN_PCT = 15.0
FUND_MARGIN_SLACK_PP = 1.0


def _min_turnover(cfg: MarketConfig) -> float:
    return MIN_TURNOVER_INR_CR * 1e7 if cfg.currency_code == "INR" else MIN_TURNOVER_USD_M * 1e6


def _live_min_price(cfg: MarketConfig) -> float:
    return LIVE_MIN_PRICE_INR if cfg.currency_code == "INR" else LIVE_MIN_PRICE_USD


# Keyed on identity, and the entry KEEPS the config it was built from. Nothing else holds a
# MarketConfig for the life of this cache, and once one is collected CPython may hand its id()
# to the next object -- which would return a floor-free copy of a DIFFERENT config. The
# backtest's sweeps build configs that differ only in risk and the position cap
# (backtesting/experiments.py), so a stale hit would carry the wrong risk_pct and be silently
# wrong rather than obviously broken. Keying on cfg.name has the same fault for the same
# reason: those sweep configs all share a name. A WeakKeyDictionary is not available either --
# MarketConfig is a mutable dataclass, so it is unhashable.
_NO_FLOOR: dict[int, tuple[MarketConfig, MarketConfig]] = {}


def _without_liquidity_floor(cfg: MarketConfig) -> MarketConfig:
    """The market config with its own turnover floor removed (the guide's replaces it), built once
    per config: prefilter_mask calls this for every row of every symbol."""
    hit = _NO_FLOOR.get(id(cfg))
    if hit is not None and hit[0] is cfg:
        return hit[1]
    # The identity check above cannot fail while the entry pins its key; it is what makes a
    # future entry that stops pinning degrade to uncached rather than to a wrong config.
    out = dataclasses.replace(cfg, screener=dataclasses.replace(cfg.screener, min_dollar_volume=0))
    _NO_FLOOR[id(cfg)] = (cfg, out)
    return out


def pivot_buy_stop(pivot: float, tick: float) -> float:
    """MV-02's resting buy-stop: just above the pivot. Shared by build_plans and the chart."""
    return round_tick(float(pivot) * 1.001, tick, "up")


def pivot_stop(tight_low: float, tick: float) -> float:
    """SL-01: the stop, STOP_BUFFER_PCT under the tight-area (or shelf) low. Shared by build_plans and the chart."""
    return round_tick(float(tight_low) * (1 - STOP_BUFFER_PCT / 100), tick, "down")


def vcp_measured_move(base_high, depth_pct) -> float:
    """A VCP's measured move: the base high less its deepest low -- the BASE's depth (VCP-05), not its
    first pullback's. Until 1.33 this took the first pullback, on the reasoning that VCP-06 forces each
    contraction to shrink so the first is the deepest; the reset rule broke that (a deeper pullback
    becomes the new reference), and TKO's 2019 base, 5% then 40% then 8%, projected 0.6R instead of
    about 4.8R and was refused. NaN when either is unknown."""
    return float(base_high) * float(depth_pct) / 100 if base_high and depth_pct else float("nan")


def _rr(r_mult, ok: bool) -> str:
    """An R multiple for the card: one decimal, or two when one would round a miss up to the limit
    (1.98R printed as "2.0R" beside "at least 2R" read as a pass)."""
    if not r_mult:
        return "—"
    return f"{r_mult:.2f}R" if not ok and round(r_mult, 1) >= MIN_STRUCTURAL_R else f"{r_mult:.1f}R"


def footprint(base_days, depths) -> str:
    """Minervini's one-line summary of a base: weeks, deepest/final contraction in %, number of
    contractions -- "27W 27/7 3T" for Netflix's 2009 base. Weeks are sessions / 5; just "7W" when the
    base has no measured contractions yet. Shared by the chart and the breakout eval set."""
    weeks = f"{max(1, round((base_days or 0) / 5))}W"
    if not depths:
        return weeks
    pct = lambda x: max(1, round(float(x)))
    return f"{weeks} {pct(max(depths))}/{pct(depths[-1])} {len(depths)}T"


def cheat_cross(prev: dict, prev_close: float, close: float) -> str | None:
    """MV-03 / MV-04: today's close cleared YESTERDAY's cheat shelf (the shelf high is a max over a window
    that includes the current bar, so today's own shelf can never be crossed — MV-01 freezes the pivot
    the same way). Returns MV03 (lower third of the base), MV04 (middle third) or None. Shared by
    evaluate and the chart."""
    if not prev or not prev.get("cheat_ok") or not (prev_close <= prev["cheat_pivot"] < close):
        return None
    if prev["cheat_zone"] == "low":
        return MV03 if LOW_CHEAT_ENABLED else None
    return MV04 if prev["cheat_zone"] == "mid" else None


def base_diagnostics(r: dict, daily: pd.DataFrame) -> dict:
    """What a pass/fail hides about a base, from one `vcp_spec.detect` result: how it contracted, which
    route its pivot passed by, how its volume dried up, its undercuts, its trend through the base and the
    ATR its pullbacks are measured against. Display only -- nothing here decides a trade. Shared by
    evaluate (the screen's row) and bases_live (the chart), so both say the same thing. A value is None
    when the detector stopped before measuring it."""
    out = {"base_reference": None, "pivot_route": None, "pivot_pos": None, "dryup_quiet_days": None,
           "closes_below_200": None, "below_200_share_pct": None, "undercuts": None,
           "undercuts_failed": None, "undercuts_pending": None, "bh_atr_pct": None, "atr_blocks_base": None}
    if not r or r.get("bh") is None:
        return out
    ref, sizes = r.get("reference_i"), r.get("depths") or []
    if ref is not None and ref < len(sizes):
        out["base_reference"] = "clean" if ref == 0 else f"reset at pullback {ref + 1}, {sizes[ref]:.1f}%"
    pos, pivot, bh = r.get("pivot_pos"), r.get("pivot"), r.get("bh")
    if pos is not None and pos == pos and pivot:
        routes = [n for n, ok in (("zone", pos >= UPPER_ZONE), ("near high", pivot >= PIVOT_NEAR_HIGH * bh)) if ok]
        out["pivot_route"], out["pivot_pos"] = " + ".join(routes) or "neither", round(float(pos), 2)
    if r.get("dryup") is not None:
        out["dryup_quiet_days"] = r.get("dryup_quiet_days")
    below, days = r.get("base_closes_below_200"), r.get("base_days")
    if below is not None:
        out["closes_below_200"] = int(below)
        out["below_200_share_pct"] = round(below / days * 100, 1) if days else None
    if r.get("undercuts") is not None:
        out.update(undercuts=r["undercuts"], undercuts_failed=r["undercuts_failed"],
                   undercuts_pending=r.get("undercuts_pending"))
    bd = r.get("bh_date")
    if bd is not None and bd in daily.index and "atr14" in daily.columns:
        a, c = daily.at[bd, "atr14"], daily.at[bd, "close"]
        if pd.notna(a) and c:
            out["bh_atr_pct"] = round(float(a) / float(c) * 100, 2)
            # the pullback floor (VCP-04) meets the tight-area cap (VCP-08): see the VCP-08 rule
            out["atr_blocks_base"] = bool(VCP.zigzag_floor_atr_mult * out["bh_atr_pct"] > TIGHT_PCT)
    return out


def base_notes(r: dict, g: dict) -> str:
    """The diagnostics in one readable line, for the Candidates table. Only what was measured."""
    parts = []
    sizes = r.get("depths") or []
    if sizes:
        parts.append(" → ".join(f"{x:.1f}" for x in sizes) + "%" + (f" ({g['base_reference']})" if g["base_reference"] else ""))
    if g["pivot_route"]:
        parts.append(f"pivot {g['pivot_pos']:.2f} up ({g['pivot_route']})")
    if r.get("dryup") is not None:
        q = g["dryup_quiet_days"]
        parts.append(f"volume {r['dryup']:.2f}×, {q} quiet day{'' if q == 1 else 's'}")
    if g["closes_below_200"]:
        parts.append(f"{g['closes_below_200']} closes under the 200-day ({g['below_200_share_pct']:g}% of the base)")
    if g["undercuts"]:
        st = [f"{n} {w}" for n, w in ((g["undercuts_failed"], "failed"), (g["undercuts_pending"], "pending")) if n]
        parts.append(f"{g['undercuts']} undercut{'s' if g['undercuts'] > 1 else ''}" + (f" ({', '.join(st)})" if st else ", recovered"))
    if g["bh_atr_pct"] is not None:
        parts.append(f"ATR {g['bh_atr_pct']:.1f}% at the high" + (" — too volatile to complete" if g["atr_blocks_base"] else ""))
    return " · ".join(parts)


def cheat_measured_move(base_high, entry: float, depth_pct) -> float:
    """A cheat's objective: it is bought below the old high, so the nearest objective is that high, and the
    base's own measured move (its depth, as `vcp_measured_move`) is projected from there. The depth is
    passed only once the base has reached the contraction step; without it the old high alone is the
    objective. Shared by build_plans and the chart."""
    return float(base_high) - entry + (float(base_high) * float(depth_pct) / 100 if depth_pct else 0.0)


def trend_template_row(cfg: MarketConfig, last) -> tuple[bool, str]:
    """The Trend Template IS the screen, so it belongs here rather than only in the gates:
    expressing it row-wise is what lets the backtest apply it as of each simulated bar instead
    of against today's row.

    Moved verbatim from the retired `minervini` module (2026-10-16), which the spec strategy
    had kept importing for this one method. Its three thresholds are screens/criteria.py
    constants already imported here, so moving it changes no behaviour and no fingerprint.
    """
    ok, why = tradable_point_in_time(cfg, last)
    if not ok:
        return False, why

    close = float(last["close"])
    s50, s150, s200 = last.get("sma50"), last.get("sma150"), last.get("sma200")
    s200_prev = last.get("sma200_21d_ago")
    lo52, hi52 = last.get("low_252"), last.get("high_252")
    rs = last.get("rs_score")
    if any(pd.isna(v) for v in (s50, s150, s200, s200_prev, lo52, hi52, rs)):
        return False, "insufficient history for the trend template"

    if not (close > s50 and close > s150 and close > s200):
        return False, "price below one of the 50/150/200-day averages"
    if not (s50 > s150 > s200):
        return False, "moving averages not stacked 50 > 150 > 200"
    if not s200 > s200_prev:
        return False, "200-day average not rising"
    if lo52 <= 0 or close < lo52 * (1 + MIN_PCT_ABOVE_52W_LOW / 100):
        return False, f"less than {MIN_PCT_ABOVE_52W_LOW:g}% above the 52-week low"
    if hi52 <= 0 or close < hi52 * (1 - MAX_PCT_BELOW_52W_HIGH / 100):
        return False, f"more than {MAX_PCT_BELOW_52W_HIGH:g}% below the 52-week high"
    # The cheap stand-in for TT-08. It floors the SAME weighted score the real 1-99 rating ranks
    # (core.indicators.rs_score), so the scan and the rating cannot disagree about what "strong"
    # means; the rating itself is applied to the collected signals afterwards (filter_min_rs).
    if rs < RS_MIN_SCORE:
        return False, f"RS score {rs:.2f} below {RS_MIN_SCORE}"
    return True, "passed"


_YOUNG_INPUTS = ("sma150", "sma200", "sma200_21d_ago", "low_252", "high_252", "rs_score")


def is_young_row(last, bars: int) -> bool:
    """Whether a row belongs to a young listing: listed at least YOUNG_MIN_BARS sessions, but not long
    enough for every Trend Template input to exist."""
    return bool(YOUNG_LISTING and bars >= YOUNG_MIN_BARS
                and any(pd.isna(last.get(k)) for k in _YOUNG_INPUTS))


def young_template_row(cfg: MarketConfig, last, low_since: float, high_since: float) -> tuple[bool, str]:
    """The Trend Template for a young listing (YOUNG_LISTING), as of one row: every condition whose
    input exists is applied as in `trend_template_row`; an average that needs more sessions than the
    stock has traded is waived; the 52-week range is the range since listing when a year has not
    passed. RS is left to the rating, which rates a young listing on its history since listing."""
    ok, why = tradable_point_in_time(cfg, last)
    if not ok:
        return False, why
    close = float(last["close"])
    s50, s150, s200 = last.get("sma50"), last.get("sma150"), last.get("sma200")
    s200_prev = last.get("sma200_21d_ago")
    if pd.isna(s50):
        return False, "insufficient history for the trend template"
    if not close > s50:
        return False, "price below the 50-day average"
    if pd.notna(s150) and not (close > s150 and s50 > s150):
        return False, "price or the 50-day below the 150-day average"
    if pd.notna(s200) and not (close > s200 and pd.notna(s150) and s150 > s200):
        return False, "price or the 150-day below the 200-day average"
    if pd.notna(s200) and pd.notna(s200_prev) and not s200 > s200_prev:
        return False, "200-day average not rising"
    lo = last.get("low_252") if pd.notna(last.get("low_252")) else low_since
    hi = last.get("high_252") if pd.notna(last.get("high_252")) else high_since
    if lo <= 0 or close < lo * (1 + MIN_PCT_ABOVE_52W_LOW / 100):
        return False, f"less than {MIN_PCT_ABOVE_52W_LOW:g}% above the low since listing"
    if hi <= 0 or close < hi * (1 - MAX_PCT_BELOW_52W_HIGH / 100):
        return False, f"more than {MAX_PCT_BELOW_52W_HIGH:g}% below the high since listing"
    return True, "passed (young listing)"


# The stage cycle's reading of the 30-week line (the 150-day), from the Learn guide on stages (2.2):
# "stopped rising" is the Trend Template's own test applied to the 150-day (no higher than a month ago),
# "falling" is the guide's example rule (more than 0.5% below a month ago). Lowercase on purpose: these
# draw a chart and decide nothing, so they stay out of the strategy's fingerprint (SpecMeta reads
# UPPER-case names).
_stage_slope_bars = 21
_stage_falling_pct = 0.5
# a swing low that can end Stage 2 must be the lowest of this many bars on EACH side (about two weeks):
# the guide's three-bar swing marks every wobble of a healthy advance as a lower low
_stage_swing_bars = 10
# Stage 4 ends for Stage 1 only when the close has held above the 150-day this many bars (or the line
# stops falling): one close above the line in a decline is a bounce, and it used to flip the stage
_stage_hold_bars = 10


def stage_cycle(daily: pd.DataFrame, cfg: MarketConfig, passes: list | None = None) -> list[dict]:
    """Weinstein's four stages over `daily`, as the Learn guide on stages reads them (sections 1-2): one
    line, the 30-week average (the 150-day), and where the price is against it. A state machine, so a
    stage holds until something moves it on and a single bar cannot flip it:

      -> 2 Advancing  the close above a RISING 150-day — Weinstein's own test. The Trend Template is
                      Minervini's later confirmation (its 200-day test lags a V-shaped recovery by
                      months), so it is recorded as `confirmed`, not required
      2 -> 3 Topping  on the first of: a LOWER SWING LOW with the close still UNDER the 150-day when the
                      swing is confirmed (guide 2.3: swings turn before averages; a swing low is the
                      lowest of the {_stage_swing_bars} bars on each side of it, core/swings.swing_low_mask,
                      so it is known that many bars later — and a pullback that has already recovered
                      above a rising line is a Stage 2 pullback, not a top), or the 150-day stopping
                      rising. (Not the 200-day: early in a real Stage 2 it is often still falling.)
      2 or 3 -> 4     when the 150-day is falling and the close is below it
      4 -> 1 Basing   when the close has held above the 150-day for {_stage_hold_bars} bars, or the
                      150-day stops falling
      1 -> 2          a BREAKOUT: the close above the base's high so far, with the price above a rising
                      150-day. Crossing the line back and forth is what a base does, so it takes the
                      breakout to leave it
      1 -> 4          a BREAKDOWN: the close below the base's low so far, with the 150-day falling
      3 -> 2          the close above a rising 150-day AND above the high of the Stage 2 that ended: a
                      top resolves upward only by breaking out of it

    Nothing is marked until the first decisive state (an advance or a decline as above).
    Returns [{"stage" (1-4), "from", "to", "bars", "high", "low", "ongoing", "began" (what started it),
    "gain_pct", "confirmed" (Stage 2 only: the first day in it the Trend Template passed, or None)}],
    oldest first. `passes`: the per-bar (ok, why) from trend_template_row, if already
    computed."""
    if passes is None:
        passes = []
        for _, row in daily.iterrows():
            try:
                passes.append(trend_template_row(cfg, row))
            except Exception:  # noqa: BLE001
                passes.append((False, "insufficient history"))
    close = daily["close"].to_numpy(float)
    s150 = daily["sma150"].to_numpy(float)
    s150_prev = daily["sma150"].shift(_stage_slope_bars).to_numpy(float)
    day = lambda i: str(daily.index[i].date())
    known = lambda *v: all(x == x for x in v)
    low = daily["low"].to_numpy(float)
    swing_low = sw.swing_low_mask(daily["low"], _stage_swing_bars, _stage_swing_bars).to_numpy()
    peak = None            # the high of the last Stage 2, which a Stage 3 must clear to resume
    last_swing = None      # the latest CONFIRMED swing low, for the lower-low test
    runs, cur = [], None   # cur: [stage, start index, what began it]

    def confirmed(a, b):   # the first bar in [a, b) on which the Trend Template passed
        return next((day(k) for k in range(a, b) if passes[k][0]), None)

    def switch(i, stage, why):
        nonlocal cur
        if cur is not None and cur[0] == stage:
            return
        if cur is not None:
            seg = daily.iloc[cur[1]:i]
            runs.append({"stage": cur[0], "from": day(cur[1]), "to": day(i - 1), "bars": i - cur[1],
                         "high": float(seg["high"].max()), "low": float(seg["low"].min()), "ongoing": False,
                         "began": cur[2], "gain_pct": round((close[i - 1] / close[cur[1]] - 1) * 100, 1),
                         "confirmed": confirmed(cur[1], i) if cur[0] == 2 else None})
        cur = [stage, i, why]

    for i in range(len(daily)):
        if not known(close[i], s150[i], s150_prev[i]):
            continue
        # a swing low at i-3 is confirmed on this bar: is it lower than the one before?
        lower_low = False
        j = i - _stage_swing_bars
        if j >= 0 and swing_low[j]:
            lower_low = last_swing is not None and low[j] < last_swing
            last_swing = low[j]
        falling = s150[i] < s150_prev[i] * (1 - _stage_falling_pct / 100) and close[i] < s150[i]
        rising150 = s150[i] > s150_prev[i]
        stage = cur[0] if cur else None
        if close[i] > s150[i] and rising150 and stage in (None, 3, 4) and (stage != 3 or peak is None or close[i] > peak) \
                and stage != 4:
            switch(i, 2, "the price above a rising 150-day" if stage != 3 else "a breakout above the top")
        elif stage == 2:
            ended = ("a lower swing low under the 150-day" if (lower_low and close[i] < s150[i])
                     else "the 150-day stopped rising" if not rising150 else None)
            if ended:
                peak = float(daily["high"].iloc[cur[1]:i + 1].max())
                switch(i, 4 if falling else 3, f"Stage 2 ended: {ended}")
        elif stage == 1:
            base = daily.iloc[cur[1]:i]   # the base so far, before today
            if len(base) and close[i] > float(base["high"].max()) and close[i] > s150[i] and rising150:
                switch(i, 2, "a breakout above the base")
            elif len(base) and falling and close[i] < float(base["low"].min()):
                switch(i, 4, "a breakdown below the base")
        elif falling and stage != 4:
            switch(i, 4, "the 150-day turned down with the price below it")
        elif stage == 4 and i - cur[1] >= _stage_hold_bars and all(close[k] > s150[k] for k in range(i - _stage_hold_bars + 1, i + 1)):
            switch(i, 1, f"the price back above the 150-day for {_stage_hold_bars} bars")
        elif stage == 4 and s150[i] >= s150_prev[i]:
            switch(i, 1, "the 150-day stopped falling")
    if cur is not None:
        seg = daily.iloc[cur[1]:]
        runs.append({"stage": cur[0], "from": day(cur[1]), "to": day(len(daily) - 1), "bars": len(daily) - 1 - cur[1],
                     "high": float(seg["high"].max()), "low": float(seg["low"].min()), "ongoing": True,
                     "began": cur[2], "gain_pct": round((close[-1] / close[cur[1]] - 1) * 100, 1),
                     "confirmed": confirmed(cur[1], len(daily)) if cur[0] == 2 else None})
    return runs


class MinerviniSpecStrategy(Strategy):
    selection = "time_series"
    family = "minervini"
    version = "1.33"
    # signal_version is not pinned: 1.33 adds base_depth_pct to evaluate()'s extras, which build_plans
    # reads, so 1.32's cached signal rows (without it) cannot be carried forward -- the next backtest
    # rescans.
    changelog = (
        ("1.33", "2026-10-30",
         "The target's measured move is the BASE's depth -- its high less its lowest low -- not its first "
         "pullback's. The first pullback stood in for the deepest on the reasoning that VCP-06 makes each "
         "contraction shrink, but the reset rule (1.28) lets a later, deeper pullback become the reference, "
         "and then the target was far too close: TKO's 2018-19 base (5%, 40%, 8%) projected 0.6R instead of "
         "about 4.8R, and the 2:1 minimum refused it. Changes which trades pass that "
         "minimum, for pivot buys and cheats alike. evaluate() now records base_depth_pct, so cached signals "
         "are rescanned."),
        ("1.32", "2026-10-29",
         "The market filter can also require leadership: new 52-week highs outnumbering new lows "
         "(MKT_HIGHS_LOWS_DAYS, MKT_HIGHS_LOWS_RATIO), the way Minervini reads a market through its "
         "leaders rather than an index average. Off by default (MKT_HIGHS_LOWS_DAYS = 0) until a "
         "backtest measures it, so no rule changed; `--const MKT_HIGHS_LOWS_DAYS=10` turns it on."),
        ("1.31", "2026-10-29",
         "EX-02b, the 20-day failure exit added in 1.27, is switched off (FAIL_SMA20_DAYS 10 -> 0). "
         "In the optimise window (2013-2021, in-sample) it sold 254 of 581 US and 112 of 225 Indian "
         "trades at about -0.5R each; it halved the full stop-outs but sold more trades that would "
         "have become trend-exit winners. Off, against on: US expectancy -0.04R vs -0.10R, profit "
         "factor 0.83 vs 0.69, max drawdown -27.5% vs -34.5%; India +0.20R vs +0.05R, 1.18 vs 1.09, "
         "-12.5% vs -15.3%. `--const FAIL_SMA20_DAYS=10` restores it. Exits only, so signal_version "
         "stays 1.30."),
        ("1.30", "2026-10-29",
         "Backtest mechanics, no rule changed: the RS rating's price floor now reads the price a stock "
         "traded at on the day, not its split-adjusted close (backtesting/spec.rs_ratings, "
         "split_factor_after). Stored closes are back-adjusted for every later split, so NFLX's October "
         "2009 close is stored as $0.72 against the ~$50 it traded at, and the $10 floor left exactly the "
         "later multi-baggers unrated -- NFLX until 2013, NVDA until 2020 -- and their signals were "
         "dropped as \"outside the rated universe\". On 2016-06-01 the US rating gains 24 such stocks "
         "(ANET, CMG, CPRT, KLAC ...) and loses 31 that later reverse-split, which really traded under "
         "$10 then."),
        ("1.29", "2026-10-29",
         "Two of the book's setups the code could not take. (1) Young listings: Minervini applies the "
         "200-day test \"provided that 200 days of trading in the stock has occurred\", and several of "
         "his examples are a stock's first bases after listing. With YOUNG_LISTING = 1 a stock listed "
         "60 or more sessions but under a year is judged on the history it has: a Trend Template "
         "average that needs more sessions is waived, the 52-week range is the range since listing, "
         "the base's prior advance runs from the low since listing, and the RS rating compares its "
         "return since listing with the market's over the same sessions (rated stocks' own ratings "
         "unchanged). Signals can now come from a stock's 60th session (min_signal_bars). New "
         "Oriental's Apr 2007 breakout and Dick's Apr 2003 coil, seven and six months after listing, "
         "are now caught: 7 of 11 book examples. (2) S6, the flat base: a 4-7 week base at most 15% "
         "deep with no pivot but its own high, bought on a close through that high with the MV-01 "
         "conviction tests and a volume dry-up over the 10 sessions before, stopped under their low. "
         "YOUNG_LISTING=0 restores (1); S6 has no switch."),
        ("1.28", "2026-10-29",
         "The base detector now finds Minervini's own examples. Run on the charts in Trade Like a "
         "Stock Market Wizard, chapter 10, 1.27 gave the book's signal on 1 of 11; 1.28 gives it on 5 "
         "(tests/test_vcp_book_examples.py lists them and the misses). Three changes. (1) A "
         "contraction (a \"T\") starts only at a rally back into the top quarter of the base "
         "(VcpParams.t_recovery 0.75); smaller bounces belong to the pullback in progress. The "
         "zig-zag alone counted 17 pullbacks in Netflix's 2009 base, which the book writes as "
         "\"27W 27/7 3T\", and VCP-06 then failed it on noise. (2) VCP-06 allows the widening "
         "tolerance (1.1x) between pullbacks, his \"about half, plus or minus a reasonable "
         "amount\": 1.27 failed Cirrus Logic's March 2010 base on 5.4% then 5.7% (strict_shrink). "
         "(3) The base keeps its start when a later high pokes above it without a decisive close -- a "
         "handle over the left lip had made Best Buy's Dec 1997 base 8 sessions old -- and a high "
         "older than 325 sessions no longer anchors a base, which had hidden Deckers' 2006 base "
         "behind its 2004 high (base_keeps_start). On 80 random US stocks, 2014-2021, the share of "
         "stock-days with a complete VCP moved from 0.4% to 0.5%: the detector is not looser, it "
         "measures the base the way the book does. `--vcp t_recovery=0 --vcp base_keeps_start=0 "
         "--vcp strict_shrink=1` restores 1.27's detector."),
        ("1.27", "2026-10-29",
         "Four rules brought into line with Minervini's own description of the method (Trade Like a "
         "Stock Market Wizard, chapter 10), none of them yet measured. (1) A cheat shelf (MV-03, "
         "MV-04) must show VCP-10's volume dry-up as well as tightness (CHEAT_DRYUP): he says a valid "
         "cheat area contracts in volume as well as in price, and until now a base VCP-10 rejected "
         "for volume could still be bought through its shelf -- ESNT's 14 Mar 2017 cheat was one. "
         "(2) A power play's tight area must show the same dry-up (PP-06, PP_DRYUP), his third "
         "power-play condition. (3) The failure reset: EN-04 allows 2 entries per "
         "base, so a stop, a breakeven stop or a failed 20-day no longer bars the base for good -- a pivot that fails "
         "and resets within days is one of his own setups. (4) EX-02b sells on a close below the "
         "20-day average within 10 sessions of the buy: he judges a breakout by "
         "whether it holds the 20-day, and gives a squat about ten days to recover. "
         "`--vcp cheat_dryup=0`, `--const MAX_ENTRIES_PER_BASE=1` and `--const FAIL_SMA20_DAYS=0` "
         "each restore one piece of 1.26."),
        ("1.26", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited "
         "(marketdata/corporate_actions.py). On the ex-date a held position receives the cash and its "
         "entry, stop, target and other levels move down by the payout; before, the stored close fell by "
         "it and the trade booked the payout as a loss, or was stopped out by it. An order resting in the "
         "stock that day is cancelled. Only trades held across such an ex-date move. Stored prices were "
         "also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and "
         "GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py "
         "correct)."),
        ("1.25", "2026-10-24",
         "W5 can become a rule: SMA200_PREF_REQUIRED = 1 holds a plan at WATCH (no new buy) while the "
         "200-day has not risen over {SMA200_RISING_PREF_BARS} sessions, Minervini's preferred 4-5 months "
         "of uptrend; 0 (the default) keeps it a note, so the shipped rules trade as 1.24. Added to "
         "measure it rather than assume it: G5's one month is the stated minimum, and the longer rise "
         "is stated as a preference."),
        ("1.24", "2026-10-22",
         "EN-04 can now allow more than one entry per base, though it still allows "
         "1 -- the switch is off until it is measured. A base was barred for "
         "good after a single entry, which also barred the re-entry a shakeout invites, and the "
         "ladder makes shakeouts common: EX-03 moves the stop to breakeven at +{BREAKEVEN_R}R, so "
         "an ordinary pullback ends the trade at zero and ended the base with it. Minervini "
         "re-buys a leader that shook him out; this implementation could not. Raised, only a stop "
         "or a breakeven stop reopens a base -- never a trend exit, which says the move is over "
         "rather than that the trade was shaken out -- and the setup must still re-fire by "
         "itself. Measured with `--const MAX_ENTRIES_PER_BASE=2`. Detection is untouched and at "
         "the shipped value nothing changes, so the golden harness is identical."),
        ("1.23", "2026-10-22",
         "EX-04 now also sells {STRENGTH_FRAC} at +{PARTIAL_R}R, the point EX-03 moves the stop to "
         "breakeven. The ladder raised the stop without ever banking anything, which converts an "
         "unrealised gain into nothing instead of into cash -- half of the guide's rule, which is "
         "to sell into strength and THEN raise the stop. 1.6 saw the symptom (breakeven-stop exits "
         "had reached a median 2.75R and realised -0.04R) and moved the threshold, treating a "
         "paired rule as a single one. Measured on the 1.22 runs: every breakeven-stop exit in "
         "both books came from a trade that had reached +2R -- 28 of India's 95 such trades and 26 "
         "of the US's 114 -- and they ended at a median -0.03R and -0.01R. The old EX-04 trigger, "
         "a close {STRENGTH_EXT_PCT}% above the 50-day, is unchanged and still fires first when it "
         "comes first; it is simply rare, taking a part off in 14% of Indian and 3.7% of US "
         "trades. Detection is untouched, so the golden harness is identical."),
        ("1.22", "2026-10-21",
         "STRENGTH_FRAC is 0.33 instead of 1/3, so EX-04 reads \"sell 0.33 of the position\" on the "
         "page instead of \"0.333333\" -- the same rounding UPPER_ZONE got in 1.15, for the same "
         "reason. It is a real change, if a negligible one: a part sold into strength (EX-04) or on a "
         "climax (EX-05) is now 33% of the position rather than 33.33%, so the fingerprint moves and "
         "the 1.20/1.21 runs read as made under earlier rules."),
        ("1.21", "2026-10-21",
         "The stage cycle (stage_cycle: the chart's stage bands and the --block-stage3 backtest filter) "
         "no longer leaves Stage 2 on a lower swing low alone: the close must still be under the "
         "150-day when the swing is confirmed, so a pullback that has already recovered above a rising "
         "line stays Stage 2. And Stage 4 ends for Stage 1 only after {_stage_hold_bars} closes above "
         "the line (or the line ceasing to fall), not on one close. Measured on 120 random stocks, "
         "stage runs shorter than 10 bars fell from 649 to 274 (India) and 1,259 to 447 (US); "
         "ANANDRATHI.NS's 31% decline of early 2025, which read as 'Stage 1 basing', reads as Stage 4, "
         "and NVDA's Dec 2025 - Apr 2026 pullback under a line rising 4.7% a month, which read as "
         "Stage 3, reads as Stage 2. No gate, setup or plan changes and the fingerprint does not move "
         "(the stage constants are lower-case by design); the bump is because --block-stage3 runs "
         "under the two versions drop different trades."),
        ("1.20", "2026-10-20",
         "The per-stock stand-in for TT-08 is now a floor on the RS SCORE, not on 12-1 momentum: "
         "RS_MIN_MOM is retired and RS_MIN_SCORE ({RS_MIN_SCORE}) replaces it. "
         "The real gate is an RS rating of {RS_MIN_RANK}+, a percentile of the IBD-style weighted "
         "score -- trailing 3/6/9/12-month returns with the most recent quarter counted twice. The "
         "cheap screen that ran in front of it used 12-1 momentum, which SKIPS the most recent "
         "month, so the two disagreed by construction: the scan discounted exactly the quarter the "
         "rating counts double. Measured over 2012-2026 on names that passed the whole Trend "
         "Template AND rated {RS_MIN_RANK}+, it threw away 8.1% of US and 6.6% of Indian ones -- "
         "RELINFRA.NS at RS 88 with 12-1 momentum of -0.14, AGO at RS 90 with +0.02, both of them "
         "stocks that fell over the year and turned in the last quarter, which is what a Stage 2 "
         "entry is. The new floor cuts 0.8% and 0.5% of them. "
         "It is a floor, not a substitute for the rating: it keeps 96.9% of US and 98.3% of Indian "
         "Trend-Template bars where the old gate kept 84.9% and 88.4%, so the scan reads ~1.1x more "
         "bars and the rating still decides afterwards (filter_min_rs). "
         "The score itself moved to one definition, `core.indicators.rs_score`, which "
         "`backtesting/spec.rs_ratings` and `screens/snapshot` now both call -- the formula had "
         "been written out three times. Verified: the 1-99 ratings are bit-identical across 3,527 "
         "symbol-dates after the consolidation. "
         "In the golden harness the only thing that moves is G8 and the two fields that report it "
         "(first_hard_fail, the prefilter reason), in both directions."),
        ("1.19", "2026-10-19",
         "The results blackout now blocks on an estimated ANNOUNCEMENT date as well as the filing "
         "date. A report breaks a stop by gapping through it, and the gap is on the announcement; "
         "the filing lands a mean 35 days after a Q1-Q3 quarter end but 53 after Q4, while the "
         "announcement lands ~30-37 days out every quarter. Keyed on filings alone, the "
         "{EARNINGS_BLACKOUT_DAYS}-day rule let 56 US trades be bought into a report -- AKAM on "
         "2013-01-28 among them, filed 2013-03-01 but announced 2013-02-06, which gapped it 18.7% "
         "through its stop and turned a 1R risk into -3.0R. "
         "No announcement calendar is stored before 2025-10, so the date is estimated: the quarter "
         "end plus the company's own median reporting lag, read off the volume signature of past "
         "quarters and applied to every quarter alike. It is deliberately NOT the heaviest bar of "
         "the quarter being judged -- that would let a quarter's own reaction decide whether it is "
         "blocked, blocking the ones that gapped and waving through the quiet ones. "
         "Scored against the announcements recorded from 2025-10, the estimate is within a week of "
         "the real date 55% of the time and within a day 47% (keying on the single heaviest bar "
         "manages 43%). That is not accurate enough to REPLACE the filing date, so it is a union: "
         "it can only add blocks, never leak more than before. On the stored US book it blocks 85 "
         "of the 1,081 taken trades where the filing date alone catches 5. "
         "BUMPED BY HAND: the change is in backtest mechanics the strategy relies on, so no "
         "numeric constant of the strategy moved and the fingerprint cannot see it. Detection is "
         "untouched -- the golden harness is identical -- but fewer signals survive, so both "
         "markets need re-running."),
        ("1.18", "2026-10-19",
         "The {MIN_STRUCTURAL_R}:1 minimum is now tested on the price actually paid, not only on the "
         "signal close. An order fills at the NEXT open, and a gap up moves the entry without moving "
         "the stop or the target -- it shortens the reward and lengthens the risk at once -- so a plan "
         "that cleared the minimum on the close could be bought below it. AKAM on 2013-01-28 is the "
         "case: 2.09R on the 41.15 close, filled at 41.29, 1.92R as bought. Measured across the stored "
         "runs, about a sixth of both books executed under the minimum they had to clear (India 60 of "
         "377, US 158 of 951), with a cluster just beneath it. The re-test sits beside the two checks "
         "the simulator already runs against the fill rather than the signal -- 'fill at or below the "
         "stop' and 'stop too far below the fill' -- and the strategy supplies its own number, so a "
         "strategy that sets none is unaffected. "
         "BUMPED BY HAND: no numeric constant moved, so the fingerprint cannot see it. Detection is "
         "untouched and the golden harness is identical across 1,680 snapshots; what changes is which "
         "filled orders survive, so trade counts fall."),
        ("1.17", "2026-10-19",
         "An experiment switch, OFF by default: CHEAT_BLOCK_VCP09. With it set, a cheat entry is "
         "refused on a base whose last failure was VCP-09 -- the pivot sitting in the lower part "
         "of the base rather than near its high. Slicing the Indian run suggested that bucket is "
         "where the cheats lose (38 trades, 7.9% win rate, -17.8R), but that is the same data the "
         "idea came out of, so the default stays 0 and the switch exists to measure it on a market "
         "it was not found in. At 0 the strategy is byte-identical to 1.16 -- the golden harness "
         "is unchanged across 1,680 snapshots -- and because the constant is fingerprinted, a run "
         "with the switch ON carries its own spec id and cannot be mistaken for the shipped rules. "
         "No rule changed; this version number exists so the fingerprint move is recorded."),
        ("1.16", "2026-10-19",
         "A cheat entry now requires the base's own DEPTH, not just its advance, age and trend. "
         "VCP-05 ran inside the contraction section, after the cheat shelf was already recorded, so "
         "MV-03/MV-04 could fire on a base deeper than MAX_BASE_DEPTH_PCT. v2 §MV-03/04 asks a cheat "
         "to clear 'base high, advance, depth, age, trend during base' -- Gate 2 -- and waives only "
         "the CONTRACTION gates, because a cheat is taken while the base is still forming and the "
         "sequence is not finished yet. Depth belongs to the base, so it is checked with the rest "
         "of Gate 2. "
         "Measured on 562 Indian symbols: 32 bases offer a cheat and none now sits on a base over "
         "{MAX_BASE_DEPTH_PCT}% (the funnel is otherwise unchanged, and the golden harness is "
         "identical across 1,680 snapshots) -- so this closes a hole rather than changing today's "
         "behaviour. "
         "BUMPED BY HAND. No numeric constant moved, so the fingerprint cannot see this and the "
         "version gate would not have asked for it."),
        ("1.15", "2026-10-18",
         "Documentation, and one number rounded so it can be read. UPPER_ZONE is 0.67 rather than "
         "2/3: the doc renderer prints a float as it is, so the page said 'the pivot sits 0.666667 "
         "or more of the way up the base range'. It is inside v2's own 0.60-0.75 test range and "
         "0.0033 of a base's range is far below the precision of a pivot's position in it, but it "
         "moves the fingerprint, hence the bump. "
         "A STALE DOC LINE IS FIXED: how_it_works still said the base starts at 'the most recent "
         "confirmed swing high'. v1.11 made it the HIGHEST unexceeded one, and the docstring and "
         "the gate docs were updated then while this line was missed -- exactly the failure "
         "CLAUDE.md warns about, since no test can check prose against behaviour. "
         "The description is a lead again rather than an inventory, 55 words down to 38. It sits "
         "ABOVE the tabs, so it is the only description on Candidates and Backtests, which have no "
         "Overview, and it has to say what the strategy is in a breath. Everything it used to list "
         "is in how_it_works and exit_rules in more detail."),
        ("1.14", "2026-10-18",
         "VCP-06 now also requires every contraction AFTER the reference to be smaller than the one "
         "before it, which the final-over-reference ratio alone does not say: 25, 10, 9, 9.5 has a "
         "final at 0.38x its reference and a right side quietly getting looser. It closes the hole "
         "the widening tolerance leaves, where the deepest pullback is only fractionally deeper than "
         "its predecessor (20 then 21) and so never counts as a widening. VCP-06 rejections 71 -> 74 "
         "on 562 Indian symbols. "
         "'Wide and loose' is now its own drop reason: a sequence that never contracts has nothing to "
         "reset TO, which is a different thing from a base that widened once and has not tightened "
         "again. Both reject; the explanation is what a reader acts on. "
         "UNDERCUTS are recorded (`undercuts`, `undercuts_failed`) and still never rejected. An "
         "undercut that does not close back above the old low within UNDERCUT_RECOVERY_DAYS is the "
         "one that reads as a breakdown rather than a shakeout. Measured: of 381 symbols, 65 bases "
         "carry an undercut and 40 carry one that failed to recover. "
         "MV-05 now carries a `base_id` of its own, the flag high's date. EN-04 (one entry per base) "
         "keys on that field, and a power play has no base -- so it was the one setup that could be "
         "re-entered on the same structure after a stop-out, which is exactly what EN-04 prevents "
         "everywhere else."),
        ("1.13", "2026-10-18",
         "The rest of the v2 list. "
         "VCP-05 is now the depth of the BASE (at most MAX_BASE_DEPTH_PCT, flagged over "
         "DEEP_BASE_FLAG_PCT) instead of the depth of the FIRST CONTRACTION -- v2 §3.4 says the "
         "deepest contraction is covered by base depth, and capping the first one separately "
         "rejected bases whose opening pullback was deep but whose base was not. "
         "VCP-10 gains a second way to pass (v2 §4.4): the tight area's average volume at or under "
         "DRYUP_RATIO (raised 0.70 -> 0.80) x the 50-day, OR DRYUP_QUIET_DAYS sessions at or under "
         "DRYUP_QUIET_RATIO x it. One average can be lifted past a threshold by a single news day "
         "inside an otherwise silent contraction. "
         "The market filter adds v2's slope term: the index above its MKT_INDEX_SMA-day average AND "
         "that average higher than MKT_SMA_RISING_DAYS sessions ago. MEASURED COST: risk-on days "
         "fall from 61.3% to 51.5% (India) and 68.6% to 61.4% (US) over 2013 onward, so it is a "
         "sweepable parameter -- `--const MKT_SMA_RISING_DAYS=0` restores the old test exactly. "
         "MV-05, THE POWER PLAY, is new and is the one shape the base rules could never see: the "
         "flag is shorter than BASE_MIN_DAYS and the averages have not caught up, so VCP-02/VCP-03 "
         "reject it before a contraction is measured. Detected on its own path "
         "(vcp_spec.detect_power_play), bought through the flag's pivot and stopped under its tight "
         "low, with the flag's own range as the measured move -- there is no base depth to project "
         "from. Walking 150 symbols over ~26,000 bars it fires on 18, every one matching the "
         "profile (ADANIGREEN 2020-10-26: run 125%, flag 15 days, depth 14.3%, tight 7.9%). "
         "NOT IMPLEMENTED from v2, and recorded so it is not mistaken for done: v2 relaxes G2-G4 "
         "for MV-05 and G1/G8 for the cheats, which needs PER-SETUP gate sets that StrategyResult "
         "does not have -- `hard_gates_passed` is global. All eight gates therefore apply to every "
         "setup. Measured cost: 13 of the 18 power plays pass G1-G4 anyway, so the relaxation is "
         "worth about 28% of candidates, not all of them. "
         "ALSO DELIBERATELY UNCHANGED: FAIL_DAYS stays 0. v2 lists the failed-breakout exit as a "
         "Guideline to test on and off, and it is off here on a measured result -- about two in "
         "three breakouts close back below the pivot within ten sessions, and in 1.7 this exit "
         "closed ~80% of trades for about -0.3R each. TIME_STOP_DAYS stays 15, inside v2's 15-30 "
         "range. Neither default is reverted without new evidence."),
        ("1.12", "2026-10-18",
         "Three more v2 changes, all at the points where the funnel was narrowest. "
         "(1) VCP-03 no longer requires the full Trend Template at the BASE START, and no longer "
         "demands the moving-average structure on every bar. It now asks whether the long trend "
         "survived the base: the 200-day no lower than at the base start, the 150-day above the "
         "200-day today, and at most MAX_CLOSES_BELOW_200 closes below the 200-day. The base-start "
         "template is recorded as `base_tt` -- Minervini applies the template when he BUYS, which "
         "is the signal day, where all eight gates stay hard. "
         "(2) VCP-08's tight area IS the final contraction -- its own swing high, which is the "
         "pivot, to today -- at least TIGHT_MIN_DAYS old with no maximum. The fixed 10-session "
         "window could only be right by coincidence: a 6-session contraction had four sessions of "
         "the previous decline dragged into its range, and a 20-session one had two thirds cut off. "
         "(3) VCP-09 is now the pivot's POSITION in the base, not its distance from the base high. "
         "At or above UPPER_ZONE of the base range, or within PIVOT_NEAR_HIGH of the high, is the "
         "standard pivot buy; below that is a cheat entry. The old rule rejected an entire named "
         "base shape -- a double bottom's pivot is the middle peak, about 15% below the high in a "
         "30%-deep base, so it never cleared 0.9 x BH. "
         "MEASURED, 562 Indian symbols: VCP-03 rejections 179 -> 158, and bases reaching the "
         "tight-area/pivot/volume gates 15 -> 22. Of the 12 VCP-09 rejections 10 are mid-zone and "
         "2 low-zone -- the cheat cases -- and 5 already carry a qualifying shelf, so they route to "
         "MV-03/MV-04 instead of being lost."),
        ("1.11", "2026-10-18",
         "Two detector changes from the v2 spec, both of which alter which bases exist. "
         "(1) VCP-02, the BASE HIGH, is now the HIGHEST confirmed swing high no close has decisively "
         "exceeded, not the first. The old loop assigned the base high only while it held none, so a "
         "higher swing high forming later -- without a close clearing the old one by more than "
         "bh_break_atr -- could never be adopted. Measured over 20 in-window bases it agreed with the "
         "highest on 14; it now agrees on 20. (Contrary to the v2 note, it was never the 'most recent': "
         "that matched on 1 of 20.) "
         "(2) VCP-06 is now the RESET RULE. It required every contraction to be at most SHRINK=0.80 x "
         "its predecessor, which failed a base for one deeper pullback early on -- the case Minervini "
         "describes as resetting the count. The reference is now the most recent widening (more than "
         "WIDEN_TOL x the previous), the base needs MIN_FROM_REFERENCE contractions from there, and the "
         "final one must be at most FINAL_REF_RATIO x the reference. All four worked examples in the "
         "spec reproduce: 15/25/12/6 passes, 20/10/5/12 is not ready, 20/10/5/12/5 passes, 25/28/24 "
         "fails. VCP-04's upper limit is gone with it -- more than MAX_CONTRACTIONS is now flagged, not "
         "rejected. "
         "MEASURED EFFECT on 562 Indian symbols: VCP-02 rejections 337 -> 297, VCP-04 34 -> 1, and where "
         "NOTHING previously reached the tight-area, pivot or volume gates, 15 now do and 2 bases "
         "complete. The pipeline produced no complete base at all in this sample before."),
        ("1.10", "2026-10-18",
         "TT-03 now records BOTH halves of what Minervini asks for. The rule is a 200-day rising "
         "\"for at least one month, preferably for 4-5 months or longer\": the month was already the "
         "gate (G5, screen criterion C5, SMA200_RISING_BARS=21) and the preference was nowhere. "
         "W5 now flags a signal whose 200-day is rising over 21 sessions but NOT over "
         "SMA200_RISING_PREF_BARS=100, so the maturity of the trend is visible on every signal. "
         "DECISIONS ARE UNCHANGED: W5 is noted and does not downgrade, because the stated "
         "requirement is the month and promoting the preference to a gate would reject stocks the "
         "Trend Template admits. The fingerprint moves because a new numeric constant enters "
         "spec_params, which is why this is a version bump rather than a silent edit; no trade "
         "this strategy would have taken before is affected."),
        ("1.9", "2026-10-16",
         "Gate, watch and setup codes renamed to one scheme shared by every strategy: G1..Gn for the hard "
         "gates, W1..Wn for the watch flags, S1..Sn for the setups. "
         "The old letters meant nothing and collided across strategies: B1-B4 were minervini's WATCH flags "
         "and breakout's GATES, so one string blocked a trade in the first and merely noted something in "
         "the second. The prefix now states the only thing that matters when reading a drop reason -- "
         "whether the code can stop a trade. No rule changed, but the code tuples are part of the "
         "fingerprint, so this moves the spec id and earlier runs stay under their own versions."
         "MV-01..04 become S1..S4, and each setup doc now opens with the MV-0n rule it implements."),
        ("1.8", "2026-10-16",
         "Trade management, filters and defaults now follow the SEPA Learn guide (\"SEPA and the VCP\"); the base, "
         "setups and entries are unchanged. Stop limit 8% -> 10%. Breakeven at +2R (was 2.5R). The failed-breakout "
         "exit (a close below the pivot within 5 sessions) is OFF: it closed ~80% of 1.7's trades for about -0.3R "
         "each, and on stored data about two in three breakouts close back below the pivot within ten sessions "
         "anyway. Selling into strength replaces 'a third at 3R' and the full climax sale: a third is sold at the "
         "next open once the close is 25% above the 50-day or a climax run appears, and the rest goes on the first "
         "close below the 50-day, which no longer needs above-average volume. A time stop sells a trade whose high "
         "has not reached +1R in 15 sessions. A buy-stop (MV-02) that fills on a close with volume under 1.4x "
         "average is sold at the next open. The market filter is the guide's -- the benchmark above its 50-day, "
         "and breadth (stocks above their 50-day) above half or rising over 5 sessions -- in the backtest AND the "
         "live screen, which until now used the shared regime downgrade; breadth history was extended back to "
         "2009 for it. No new buys with results due within 14 days (live: the earnings calendar; backtest: the "
         "stored results' filing dates). Liquidity: 50-day turnover of Rs10 crore / $20m, and live only, a price "
         "of Rs100 / $15. Progressive exposure is on by default (--pe). The low cheat (MV-03) is back on. A "
         "'guide' fundamentals level (EPS +20% and accelerating, sales +15%, margins not falling) is available as "
         "--fundamentals guide, off by default because India's stored results start in late 2020. Every 1.7 rule "
         "is still reachable by flag (--mkt01, --fail-days 5, --breakeven-r 2.5, --partial-r 3, --climax-full, "
         "--trend-volume, --time-stop 0, --results-blackout 0, --const LOW_CHEAT_ENABLED=0). The default backtest "
         "now takes TRADE ON TRIGGER as well as HIGH CONFIDENCE, so the buy-stop and the cheats -- the guide's "
         "main entries -- are traded, not only MV-01. Not yet backtested."),
        ("1.7", "2026-10-15",
         "The market filter is on by default (`--spec` now implies `--market-filter`), because it is the "
         "first change measured here to improve return AND drawdown together: US 2010 onward, 557 trades "
         "to 490, expectancy +0.04R to +0.06R, profit factor 1.04 to 1.10, CAGR 0.65% to 1.34%, max "
         "drawdown -43.5% to -28.6%, for 163 of 1,325 signals blocked. No rule changed, so the fingerprint "
         "is unmoved; this bump marks the baseline every later run should be read against. The 5-session "
         "re-entry delay added in 1.6 stays OFF: it returns most of the gain (CAGR 0.72%, drawdown -31.2%) "
         "by sitting out the start of recoveries. Progressive exposure also stays off by default -- it cut "
         "drawdown to -34.6% on its own, but the market filter does better on both axes and the two "
         "overlap rather than stack (together: drawdown -27.6% but CAGR 0.53%)."),
        ("1.6", "2026-10-12",
         "Progressive exposure, and the market filter made to bite. PE-01..PE-04 size an entry from "
         "the recent record instead of risking a flat 1% every time: a pilot at half risk "
         "while the last 10 closed trades are not net positive, after two losing trades in "
         "a row, or during the first 5; full risk otherwise; an optional press above +4R. "
         "The state is read once per session BEFORE that day's exits, so every input is a trade that "
         "closed earlier -- this is sizing, not prediction. The aim is drawdown, not return. "
         "MKT-01 already blocked new signals, but an order placed while the market was open could "
         "still be resting when it closed and would fill into a market the rule refuses; those are now "
         "cancelled, and --mkt-confirm requires MKT-01 to hold N sessions before risk-on resumes so the "
         "gate does not flap around the 200-day (risk-off still bites at once). EX-03's breakeven trigger "
         "rises to 2.5R: trades exiting on it had reached a median 2.75R while held and "
         "realised -0.04R, so it was turning winners into scratches. Open positions are never forced out "
         "by the filter."),
        ("1.5", "2026-10-10",
         "MV-03, the low cheat, is off by default (LOW_CHEAT_ENABLED). On India 2010 onward with "
         "both entry modes, the three cheats and the pivot buy produced 210 trades: MV-04 made "
         "Rs213,395 over 177 trades at +0.070R, while MV-03 lost Rs257,039 over 25 at -0.515R on a "
         "4% win rate, turning a profitable book into a Rs101,290 loss on its own. Minervini "
         "describes the low cheat as the riskiest of his three in-base entries, used sparingly and "
         "only in stocks he knows well, so this is his own caveat showing up in the data rather "
         "than a surprise. Kept as a switch rather than deleted: 25 trades is a thin basis for "
         "removing an entry outright, and it should be confirmed on US data."),
        ("1.4", "2026-10-10",
         "The cheat entries (MV-03 low cheat, MV-04 \"3C\"). Minervini buys three points inside a "
         "base -- the lower third, the middle third and the pivot at the top -- and this spec only "
         "ever implemented the last, which is why it found nothing in stocks that never complete a "
         "textbook VCP. A cheat is a short shelf with a pivot of its own, and it runs off any base "
         "clearing VCP-01/02/03 rather than a completed VCP, because a cheat is taken while the base "
         "is still FORMING; waiting for completion IS the pivot buy. Its stop is the SHELF low, not "
         "the base low, which is the reason he takes it. Measured over ten leaders in both markets, "
         "2013 onward: valid trade plans 10 -> 74, with cheats appearing in 9 of 10 names including "
         "NVDA, BAJFINANCE, TRENT and SMCI, which produce no full VCP base at all. Median R 2.92 "
         "(MV-04) and 3.34 (MV-03) against 2.45 for the pivot buy, and every cheat plan clears the "
         "2:1 minimum. Whether they MAKE money is a separate question the backtest has to answer."),
        ("1.3", "2026-10-10",
         "The base high is a zone, not a line (VcpParams.bh_break_atr). The spec ends a base "
         "on ANY close above BH, so a leader making new highs can never hold one: VCP-02 then "
         "wants 15 more sessions from a fresh swing high. Across ten leaders in both markets "
         "the detector found 13 bases in 13 years and ZERO volume-confirmed breakouts, with "
         "NVDA (+1554%), CELH, SMCI, BAJFINANCE (+2063%) and TRENT yielding no base at all. "
         "A close must now clear BH by bh_break_atr x ATR to resolve the base, the same "
         "zone-not-line reasoning as chart_pattern.overhead_cluster_atr and this strategy's "
         "own OVERHEAD_CLUSTER_ATR. Measured: 'no base high at all' rejections fall 966 -> 738 "
         "(-24%) and detected breakouts rise 8 -> 11. It is a CORRECTNESS fix and nothing more "
         "-- bases stay at 13 and MV-01 stays at 0, because the freed bars fail VCP-04 (451) "
         "and VCP-06 (521) instead. bh_break_atr=0 reproduces the spec exactly."),
        ("1.2", "2026-10-10",
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
        ("1.1", "2026-10-10",
         "EN-02 now needs a confirming close. The resting buy-stop filled on any intraday "
         "poke through the pivot, with no volume or close test, so it systematically bought "
         "exactly what MV-01 is built to reject -- and EX-02 then sold it at the next open "
         "as a failed breakout. Over India 2010 onward, 9 of 14 trades filled on a bar that "
         "closed BELOW the entry (CDSL filled 956.78, closed 936.90) and 11 of 14 exited "
         "FAILED_BREAKOUT with a median hold of one day, for -0.40R each. The order now fills "
         "only on a bar that closes at or above the pivot, and fills AT that close: the close "
         "is what confirmed it, so paying the intraday stop price would be buying on "
         "information that did not exist at the touch. A poke that closes back below leaves "
         "the order resting -- the base is intact until it closes below the tight low."),
        ("1.0", "2026-10-10",
         "v1 baseline of the Minervini SEPA implementation: Trend Template gates (TT-01-08) with point-in-time RS, the VCP detector (VCP-01-11) segmented by an ATR-scaled zig-zag whose threshold shrinks with the contractions, the MV-01/MV-02 setups, the exit ladder (EX-01-07), a 2:1 minimum reward-to-risk measured from the base's own measured move, and overhead supply binding only at least OVERHEAD_CLUSTER_ATR above the base high. Earlier iteration history is in the git log."),
    )
    key = "minervini"
    name = "Minervini SEPA"
    #: The LEAD, not an inventory. It sits above the tabs, so it is the only description on
    #: Candidates and Backtests, which have no Overview -- it has to say what the strategy is in a
    #: breath. Everything the old 55-word enumeration listed (the Trend Template, the stop limit,
    #: the breakeven, the exits, the market filter, the blackout, progressive exposure) is in
    #: how_it_works and exit_rules in more detail, so nothing is lost by saying it once there.
    description = (
        "Minervini's SEPA as the Learn guide describes it: buy a Stage 2 leader as its volatility "
        "contraction completes — through the pivot, or one of the two cheat entries — with a "
        "capped loss and a managed exit."
    )
    style = "breakout"

    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
    watch_codes = ("W1", "W2", "W3", "W4", "W5")
    setup_codes = (MV01, MV02, MV03, MV04, MV05, FLAT)
    extra_columns = ("pp_pivot", "pp_tight_low", "pp_run_pct", "pp_flag_days",
                     "fundamentals_ok", "revenue_yoy_pct", "earnings_yoy_pct", "gross_margin_change_pp",
                     "pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                     "first_depth_pct", "last_depth_pct", "base_depth_pct", "tightness_pct", "dryup_ratio",
                     "breakout_volume_ratio", "vcp_fail", "rs_score", "base_notes", "base_reference", "pivot_route", "pivot_pos",
                     "dryup_quiet_days", "closes_below_200", "below_200_share_pct", "undercuts",
                     "undercuts_failed", "undercuts_pending", "bh_atr_pct", "atr_blocks_base")
    extra_numeric_columns = ("pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                             "first_depth_pct", "last_depth_pct", "base_depth_pct", "tightness_pct", "dryup_ratio",
                             "breakout_volume_ratio", "rs_score", "pivot_pos", "dryup_quiet_days",
                             "closes_below_200", "below_200_share_pct", "undercuts", "undercuts_failed",
                             "undercuts_pending", "bh_atr_pct")
    needs_ctx_extras = True
    # Read after the scan, never by evaluate(): a `--const` variant moving only these reuses the
    # shipped run's signal rows (base.Strategy.signal_exempt_consts). The detector's constants,
    # the setups' (VOL_MULT, BUY_RANGE_PCT, COIL_PCT, UPPER_HALF, LOW_CHEAT_ENABLED,
    # CHEAT_BLOCK_VCP09) and the watch flags' are not here: a variant on one of them rescans.
    signal_exempt_consts = (
        # the plan: build_plans, signal_meta, classify
        "STOP_BUFFER_PCT", "MAX_STOP_PCT", "MAX_ENTRIES_PER_BASE", "NOMINAL_TARGET_R",
        "MIN_STRUCTURAL_R", "OVERHEAD_CLUSTER_ATR",
        # the exits (portfolio_sim's ExitPolicy)
        "BREAKEVEN_R", "PARTIAL_R", "FAIL_DAYS", "FAIL_SMA20_DAYS", "STRENGTH_EXT_PCT", "STRENGTH_FRAC",
        "CLIMAX_IS_PARTIAL", "TREND_EXIT_NEEDS_VOLUME", "TIME_STOP_DAYS", "LIGHT_VOLUME_EXIT",
        # sizing, the market filter and the book (backtesting/spec.py, --spec)
        "PE_WINDOW", "PE_WARMUP", "PE_PILOT_FRAC", "PE_PRESS_NET_R", "MKT_CONFIRM_DAYS",
        "MKT_GUIDE", "MKT_INDEX_SMA", "MKT_BREADTH_MIN_PCT", "MKT_BREADTH_RISING_DAYS",
        "MKT_SMA_RISING_DAYS", "MKT_HIGHS_LOWS_DAYS", "MKT_HIGHS_LOWS_RATIO", "MAX_POSITIONS", "MAX_OPEN_RISK_PCT", "MAX_ADV_PCT",
        # which bars are scanned (prefilter_row) and the live price floor -- not what a scan records
        "MIN_TURNOVER_INR_CR", "MIN_TURNOVER_USD_M", "LIVE_MIN_PRICE_INR", "LIVE_MIN_PRICE_USD",
        # the --fundamentals filter, applied to signals after the scan
        "FUND_EPS_GROWTH_MIN_PCT", "FUND_SALES_GROWTH_MIN_PCT", "FUND_MARGIN_SLACK_PP",
    )
    # SEPA part 2. The screener fetches current fundamentals for rows that already
    # cleared the screen and annotates them (revenue/earnings YoY, gross-margin
    # change, fundamentals_ok). LIVE ONLY, and deliberately not a gate: the stored
    # figures are a single present-day snapshot -- one fetched_at, no record of when
    # each was published, 9% of the US universe and 6% of India -- so a backtest
    # using them would be reading the future, selecting only firms that still report
    # today, and discarding 90% of the universe for want of data. The flag was set
    # on the legacy minervini and was lost when that strategy was unregistered.
    wants_live_fundamentals = True
    screen_key = "stage2"
    screen_gates = {"G1": "C1", "G2": "C2", "G3": "C3", "G4": "C4", "G5": "C5", "G6": "C6", "G7": "C7", "G8": "C8"}
    min_bars = 300
    # A signal can come before min_bars: a young listing (YOUNG_LISTING) is judged from its 60th
    # session. min_bars stays the history a backtest loads before its start.
    min_signal_bars = YOUNG_MIN_BARS

    thesis = (
        "Minervini's SEPA — buy Stage-2 leaders as a volatility contraction completes, with small, capped "
        "losses against large winners — traded the way the Learn guide \"SEPA and the VCP\" describes it: "
        "the base is found by the written specification's exact rules, and the trade is managed, sized and "
        "filtered by the guide's."
    )
    how_it_works = (
        "**The idea.** Buy a stock that is already a market leader, after it has paused in a base "
        "whose pullbacks keep getting smaller, on the day it breaks out of that base. Shrinking "
        "pullbacks are the volatility contraction pattern (VCP): each sell-off is weaker than the "
        "last, so sellers are running out.",
        "**The steps, in order.** Each has its own section below.\n\n"
        "- **Qualify** (G1–G8): the stock passes the Trend Template.\n"
        "- **Find the base** (VCP-01 to VCP-10): the base checks.\n"
        "- **Pick the setup** (S1–S6): a breakout, a coil under the pivot, two early \"cheat\" buys, "
        "a power play, or a flat base.\n"
        "- **Buy** (Entry), **protect** (Stop), **check the reward** (Target) and **manage** (Exit).\n"
        "- **Size** the position, and skip new buys in the cases under \"When no new trade is taken\".",
        "**Timing.** Every rule is judged on a session's close, using only data up to that close. An "
        "order fills in a later session — at the next open, or on a buy-stop — never on the bar that "
        "produced it (spec section 10).",
        "**Rule ids.** TT-05, VCP-02, EX-04 and the like name the rule in the written backtest spec "
        "(research/minervini-backtest-spec.md), so a rule can be found there and in the code. Where the "
        "code departs from that spec is listed once, under Known caveats.",
    )
    caveats = (
        "**Where the code departs from the written spec.** It follows the spec's revision (v2), the "
        "Learn guide \"SEPA and the VCP\" and, since 1.27, Minervini's own book instead in these "
        "places:\n\n"
        "- **Base:** the base starts at the first unbeaten swing high and its high is the HIGHEST one, "
        "not the most recent (VCP-02); the trend is tested across the base instead of the Trend "
        "Template on the base-high day (VCP-03); pullbacks come from a shrinking zig-zag, a pullback "
        "starts only at a rally into the top of the base, and more than {MAX_CONTRACTIONS} is a flag, "
        "not a limit (VCP-04); depth is the whole base, up to {MAX_BASE_DEPTH_PCT}%, not the first "
        "pullback up to 35% (VCP-05); a deeper pullback resets the count instead of failing the base, "
        "where the spec wants each pullback 0.80 times the last, and a pullback up to {WIDEN_TOL} "
        "times the one before still counts as contracting (VCP-06); the tight area is the last pullback, not a "
        "fixed 10 days (VCP-08); a high pivot in a deep base also passes (VCP-09); volume up to "
        "{DRYUP_RATIO} times, or quiet days, instead of 0.70 times (VCP-10).\n"
        "- **Setups:** the cheats (MV-03, MV-04) and the power play (MV-05) are added, each with a "
        "volume dry-up test (CHEAT_DRYUP, PP-06). The spec's early entry, EN-03, is not implemented.\n"
        "- **Re-entry:** a base may be bought {MAX_ENTRIES_PER_BASE} times after a shakeout (EN-04); "
        "the spec allows one.\n"
        "- **Entry:** the buy-stop needs a close at or above the pivot, where the spec fills on a touch "
        "(EN-02).\n"
        "- **Stop and size:** a {MAX_STOP_PCT}% maximum stop instead of 8% (SL-03); half size until the "
        "record pays (PE) is added; open risk is measured from the lower of the last close and the price "
        "paid, not from the last close (PF-04).\n"
        "- **Target:** the spec has none; the {MIN_STRUCTURAL_R}:1 test and the overhead cap are added.\n"
        "- **Exits:** a part sold {STRENGTH_EXT_PCT}% above the 50-day instead of a third at +3R (EX-04); "
        "a climax sells that part, not everything (EX-05); the 50-day exit needs no volume (EX-06); the "
        "time stop is on at {TIME_STOP_DAYS} sessions instead of off at 20 (EX-07); the failed-breakout "
        "exit is off instead of on at 5 sessions (EX-02), and so is the 20-day failure exit added "
        "beside it (EX-02b); the light-volume exit is added.\n"
        "- **Filters:** the Learn guide's market test instead of MKT-01; the results blackout is added; "
        "higher US turnover and price floors than U-01 and U-02.",
        "**Survivorship bias.** The universe is today's listed stocks; companies delisted since are missing, "
        "which flatters every result.",
        "**Corporate actions.** Prices are adjusted when fetched; a split or bonus after a symbol's last full "
        "fetch shows as a crash until its history is re-fetched (`marketdata.splits`).",
        "**Relative strength** is a ranking against the whole market, so where it is applied depends on what "
        "the caller can see. The daily screen rates the whole market and gates G8 on the real RS rating of "
        "{RS_MIN_RANK}+. A backtest scans one stock at a time, so G8 there is a floor of {RS_MIN_SCORE} on the "
        "stock's own RS score, and `--min-rs` then applies the real rating to the collected signals — the "
        "same threshold, one step later. A single-stock tool keeps only the floor, so it is looser than both.",
        "**Fundamentals (SEPA part 2) are optional in the backtest, off by default.** `--fundamentals guide` "
        "applies the Learn guide's tests (quarterly EPS up {FUND_EPS_GROWTH_MIN_PCT}%+ and faster than the "
        "quarter before, sales up {FUND_SALES_GROWTH_MIN_PCT}%+, net margin no more than "
        "{FUND_MARGIN_SLACK_PP} points below a year earlier); `leader|acceptable|covered` apply the "
        "Fundamentals page's stricter SEPA tests. Each uses the quarterly results public on the signal date "
        "(backtesting/fundamental_filter.py). Stored results start in late 2020 for India and 2009 for the US "
        "and cover part of the universe, so compare against `covered` (any scorable company), not the full run.",
        "**The results blackout** in a backtest blocks on an ESTIMATED announcement date -- the quarter end "
        "plus the company's own median reporting lag, taken from quarters already announced by the signal -- "
        "unioned with the stored filing date it used to key on alone. The gap that breaks a stop happens on the "
        "announcement, and the filing runs weeks behind it: keyed on filings alone, {EARNINGS_BLACKOUT_DAYS}-day "
        "cover let 56 US trades be bought into a report. The estimate is NOT precise -- scored against the "
        "announcements recorded from 2025-10 it is within a week of the real date 55% of the time -- so it is a "
        "union rather than a replacement, which can only add blocks and never leak more than before; the price is "
        "some blocks on the wrong day. Stored quarters start in late 2020 for India and 2009 for the US and cover "
        "part of the universe; a stock with no stored quarter is never blocked, so early Indian years run without it.",
        "**The price floor is live only.** A backtest reads split-adjusted history, where a winner's early price "
        "is divided by every later split, so a price floor there would delete the stocks that rose most.",
        "**The low cheat (MV-03) is on because the guide lists it**, but it lost heavily when measured in 1.5 "
        "(India 2010 onward: 25 trades, a 4% win rate, -0.515R each). Read its trades separately.",
        "**Circuit limits** (C-03, India) are not modelled: a stop on a locked day fills at the next open, "
        "which daily bars cannot tell apart from a gap.",
        "**Base number** counts the bases that produced a breakout since the trend last broke; it is "
        "worked out by the backtest from the signal list, and only reported, not filtered on by default.",
        "EN-03 (buying inside the tight area before any breakout) is not implemented.",
        "The market filter's breadth is the share of the market's 1,000 most-traded stocks above their 50-day "
        "average, rebuilt daily from stored prices back to 2009; today's lists only, like everything else here.",
        "The detector turns a chart-reading judgement into numbers; every threshold is a parameter of the "
        "spec (section 11), most of them marked there as assumptions.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "IN-SAMPLE ONLY, not verified. v1.33 (the target's measured move from the base's depth) is not "
        "backtested yet; the figures below are v1.31's. v1.31 in the optimise stage (2013-2021, the years its rules "
        "were tuned on), under the live variant (CHEAT_BLOCK_VCP09=1, TREND_EXIT_NEEDS_VOLUME=1): "
        "India 199 trades, 34% won, +0.20R a trade, profit factor 1.18, CAGR +1.6%, worst drawdown "
        "-12.5%; US 490 trades, 35% won, -0.04R a trade, profit factor 0.83, CAGR -2.5%, worst "
        "drawdown -27.5%. Neither beats holding the index (excess CAGR about -12% and -16%): most of "
        "the gap is idle cash, but the trades also trail the index held at the same exposure, by "
        "about 3 points a year in India and 6 in the US. India's +0.20R rests on a few "
        "large winners -- one trade (Bajaj Finance, 2016) is +10R. Against v1.26 (+0.38R India, "
        "-0.11R US): the US gained from the 1.28 base detector; India's drop is almost entirely one "
        "+25R trade (Deepak Nitrite, July 2020) that the 1.28 base anchoring reads as a 45%-deep "
        "base from the pre-COVID high rather than a fresh 19% one. Switching each 1.28 detector "
        "change off on its own (2013-2021): restarting the base at a later high helps India only "
        "through that trade and costs the US 0.07R a trade; counting every zig-zag leg as a "
        "contraction lowers both; the strict shrink test changes almost nothing. Not yet run in the "
        "verify stage (2022-today). Earlier versions' figures are in the changelog and in "
        "research/minervini-spec-sensitivity-india.md and -us.md."
    )

    gate_docs = {
        "G1": "TT-05: today's close is above the 50-day simple moving average.",
        "G2": "TT-01, first half: today's close is above the 150-day average.",
        "G3": "TT-01, second half: today's close is above the 200-day average.",
        "G4": "TT-02 and TT-04: the averages are stacked — the 50-day above the 150-day, and the "
              "150-day above the 200-day (so the 50-day is above the 200-day too).",
        "G5": "TT-03: the 200-day average is higher today than {SMA200_RISING_BARS} sessions ago "
              "(about a month).\n\n"
              "The longer rise Minervini prefers — about 4-5 months — is watch flag W5, noted but "
              "never blocking.",
        "G6": "TT-06: today's close is at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low (the "
              "lowest low of the last 252 sessions).",
        "G7": "TT-07: today's close is no more than {MAX_PCT_BELOW_52W_HIGH}% below the 52-week high "
              "(the highest high of the last 252 sessions).",
        "G8": "TT-08: an RS rating of {RS_MIN_RANK} or more. The RS score adds up the stock's gains "
              "over the last 3, 6, 9 and 12 months, counting the latest 3 months twice. The rating "
              "ranks that score across the market from 1 to 99, so {RS_MIN_RANK} means it beat about "
              "{RS_MIN_RANK}% of stocks.\n\n"
              "A ranking needs the whole market, so how the rule is checked depends on where it "
              "runs:\n\n"
              "- **Daily screen:** rates the whole market and applies {RS_MIN_RANK}+ directly.\n"
              "- **Backtest:** the same rule in two steps. Scanning one stock, it requires an RS "
              "score of {RS_MIN_SCORE}+ (a steady 5% a quarter just clears it; a flat stock scores "
              "0). Once all signals are in, it drops those rated under {RS_MIN_RANK} that day.\n"
              "- **Single-stock tools** (chart indicators, `inspect --no-rs-rank`): the "
              "{RS_MIN_SCORE} floor only, so they can pass a stock the screen would reject.\n\n"
              "**Young listings** (YOUNG_LISTING = {YOUNG_LISTING}): a stock listed at least "
              "{YOUNG_MIN_BARS} sessions but under a year has no 12-month score, so its rating "
              "compares its return since listing with every rated stock's return over the same "
              "number of sessions. Its gates G2–G7 follow Minervini's \"provided that 200 days of "
              "trading in the stock has occurred\": an average that needs more sessions than it has "
              "traded is waived, and the 52-week range is the range since listing.",
    }
    watch_docs = {
        "W1": "Light breakout volume (MV-01a): on a day the close crossed the pivot, volume was under "
              "{VOL_MULT} times its 50-day average. That close is not an MV-01 signal and is not bought.",
        "W2": "Extended (MV-01b): on a day the close crossed the pivot, it closed more than {BUY_RANGE_PCT}% "
              "above it. That close is not an MV-01 signal and is not bought.",
        "W3": "Weak close (MV-01c): on a day the close crossed the pivot, it closed in the lower part of the "
              "day's range — under {UPPER_HALF} of the way from the low to the high. That close is not an "
              "MV-01 signal and is not bought.",
        "W4": "Results due within {EARNINGS_BLACKOUT_DAYS} days (from the earnings calendar): a valid plan "
              "is held at WATCH instead of a buy. Not in the written spec; from the Learn guide.",
        "W5": "Young uptrend (TT-03, the preferred half): the 200-day is higher than {SMA200_RISING_BARS} "
              "sessions ago (G5 passed) but not higher than {SMA200_RISING_PREF_BARS} sessions ago, so it "
              "has been rising for less than the 4-5 months Minervini prefers. With SMA200_PREF_REQUIRED = "
              "{SMA200_PREF_REQUIRED} (the default, 0) it is noted only; set to 1 it holds the plan at WATCH, "
              "so no new buy.",
    }
    setup_docs = {
        MV01: "MV-01 pivot breakout: the close crosses the pivot of a finished base, with "
              "conviction.\n\n"
              "- **Finished base:** on yesterday's close the base passed every base check above "
              "(VCP-01 to VCP-10).\n"
              "- **Pivot:** taken from yesterday's chart, so today's own bar cannot move it.\n"
              "- **Breakout:** yesterday's close was at or below the pivot, and today's close is "
              "above it.\n"
              "- **Conviction (MV-01a–c):** volume at least {VOL_MULT} times its 50-day average; a "
              "close at least {UPPER_HALF} of the way from the day's low to its high; and a close no "
              "more than {BUY_RANGE_PCT}% above the pivot. A miss is recorded as W1, W2 or W3, and "
              "the close is not bought.",
        MV02: "MV-02 coiled: a finished base whose close sits just under the pivot, ready to break "
              "out.\n\n"
              "- **Finished base:** on today's close the base passes every base check above.\n"
              "- **Coiled:** today's close is at or below the pivot and no more than {COIL_PCT}% "
              "under it, and today is not an MV-01 breakout.\n\n"
              "Nothing is bought on the signal: a buy-stop waits just above the pivot (see Entry).",
        MV03: "MV-03 low cheat: an early buy from a short, tight shelf in the LOWER third of a base "
              "that is still forming.\n\n"
              "- **Base still forming:** the base passes VCP-02, VCP-01, VCP-03 and VCP-05 (length, "
              "prior advance, trend, depth). The pullback checks after them need not pass yet.\n"
              "- **Shelf:** the last {CHEAT_SHELF_DAYS} sessions up to yesterday, whose high-to-low "
              "range is at most {CHEAT_SHELF_PCT}% of their high, with that high still below the "
              "base high.\n"
              "- **Lower third:** the shelf's high is less than one third of the way from the base "
              "low to the base high.\n"
              "- **Quiet shelf:** the shelf's volume has dried up, by VCP-10's test: its average is "
              "at most {DRYUP_RATIO} times the 50-day average (taken the session before the shelf), "
              "or at least {DRYUP_QUIET_DAYS} of its sessions trade at or under {DRYUP_QUIET_RATIO} "
              "times it. Minervini wants a cheat area to contract in volume as well as in price. "
              "Only while CHEAT_DRYUP is 1 (it is {CHEAT_DRYUP}).\n"
              "- **Trigger:** yesterday's close was at or below the shelf's high, and today's close "
              "is above it. There is no breakout-volume or close-position test.\n\n"
              "The stop goes under the shelf's low, much nearer than the base low — the reason to "
              "buy early. Minervini calls this the riskiest of his three in-base entries. On by "
              "default (LOW_CHEAT_ENABLED = {LOW_CHEAT_ENABLED}). Under the variant the live screen "
              "runs, a cheat is withheld when its base has passed every check up to VCP-08 but fails "
              "VCP-09.",
        MV04: "MV-04 cheat (\"3C\", the cup-completion cheat): the same as MV-03, but the shelf's "
              "high is between one third and two thirds of the way from the base low to the base "
              "high — the stock has recovered part of its decline but not its old high.",
        MV05: "MV-05 power play: a stock that has run up very fast, then paused briefly. No base is "
              "needed.\n\n"
              "- **Flag high:** the most recent confirmed swing high that leaves a pause of "
              "{PP_FLAG_MIN_DAYS}–{PP_FLAG_MAX_DAYS} sessions up to yesterday.\n"
              "- **Run:** that high is at least {PP_RUN_MULT} times the lowest low of the "
              "{PP_RUN_WINDOW} sessions before it.\n"
              "- **Flag:** since the flag high, price has fallen no more than "
              "{PP_FLAG_MAX_DEPTH_PCT}% and has not closed above it.\n"
              "- **Tight area and pivot:** from the highest confirmed swing high inside the flag (or "
              "the flag high, if there is none) to yesterday, covering at least the last "
              "{TIGHT_MIN_DAYS} sessions. Its range is at most {TIGHT_PCT}%; its high is the pivot "
              "and its low the stop's reference.\n"
              "- **Volume dried up (PP-06):** the tight area passes VCP-10's test — average volume at "
              "most {DRYUP_RATIO} times the 50-day average, or at least {DRYUP_QUIET_DAYS} sessions at "
              "or under {DRYUP_QUIET_RATIO} times it. Only while PP_DRYUP is 1 (it is {PP_DRYUP}).\n"
              "- **Trigger:** the same as MV-01's — yesterday's close at or below the pivot, today's "
              "close above it on at least {VOL_MULT} times average volume, at least {UPPER_HALF} of "
              "the way up the day's range, and no more than {BUY_RANGE_PCT}% above the pivot.\n\n"
              "It is looked for separately from bases, because the base checks would reject it: the "
              "pause is usually too short to count as a base, and after so fast a run the long "
              "averages have not caught up.",
        FLAT: "Flat base: a shallow, sideways base with no pivot of its own, bought through its high. "
              "Minervini: when a flat base has \"no real pivot other than the high of the base\", buy "
              "\"as the stock moves above the highest price at the top of the base\".\n\n"
              "- **Base:** yesterday's base passed VCP-01, VCP-02, VCP-03 and VCP-05 but never became a "
              "complete VCP; it is {FLAT_MIN_DAYS}–{FLAT_MAX_DAYS} sessions old (four to seven weeks) "
              "and at most {FLAT_MAX_DEPTH_PCT}% deep.\n"
              "- **Quiet before the breakout:** the {FLAT_PIVOT_DAYS} sessions before today pass "
              "VCP-10's volume test (average at most {DRYUP_RATIO} times the 50-day, or "
              "{DRYUP_QUIET_DAYS} sessions at or under {DRYUP_QUIET_RATIO} times it).\n"
              "- **Trigger:** yesterday's close at or below the base high, today's close above it on "
              "at least {VOL_MULT} times average volume, at least {UPPER_HALF} of the way up the day's "
              "range, and no more than {BUY_RANGE_PCT}% above the high.\n\n"
              "The stop goes under the low of those {FLAT_PIVOT_DAYS} sessions; the objective is the "
              "base's depth added to the price paid. A base that is also a complete VCP is bought as "
              "S1 instead.",
    }
    pattern_title = "The base — VCP checks"
    pattern_intro = (
        "A base is complete when every check below passes. They are listed in the order the code runs "
        "them, so the first one that fails is where a stock is stuck. The terms they use:\n\n"
        "- **Swing high:** a day whose high is the highest of the {SWING_K} sessions on each side of it. "
        "It is only known {SWING_K} sessions later, never on the day.\n"
        "- **Base high:** where the base starts — the highest swing high that no close since has beaten "
        "by more than {VCP.bh_break_atr} ATR. A close beyond that ends the base.\n"
        "- **Base low:** the lowest low since the base high.\n"
        "- **Pullback:** a fall from a high to the next low inside the base, as a % of the high. Also "
        "called a contraction.\n"
        "- **Tight area, pivot, tight low:** the last pullback is the tight area. The high it starts from "
        "is the pivot; its lowest low is the tight low.\n"
        "- **ATR:** average true range over 14 sessions — the stock's typical daily move. Used as a % of "
        "the close on the base-high day."
    )
    pattern_docs = {
        "VCP-02": "**A base exists, of the right length.** The base starts at the first swing high, "
                  "at most {BASE_MAX_DAYS} sessions old, that no close has since cleared by more than "
                  "{VCP.bh_break_atr} ATR; it must be at least {BASE_MIN_DAYS} and at most "
                  "{BASE_MAX_DAYS} sessions old (about 3 to 65 weeks).\n\n"
                  "A later swing high that pokes above it without such a close — a handle edging over "
                  "the left-side high — raises the base high (used for depth, the prior advance and "
                  "the pivot's position) but does not restart the base.",
        "VCP-01": "**Prior advance.** The base high is at least {PRIOR_ADVANCE_PCT}% above the "
                  "lowest low of the {VCP.prior_window} sessions (about six months) before it. A "
                  "stock with less history than that fails.",
        "VCP-03": "**Trend held during the base.** Three checks over the base:\n\n"
                  "- the 200-day average today is no lower than on the base-high day;\n"
                  "- the 150-day is above the 200-day today;\n"
                  "- at most {MAX_CLOSES_BELOW_200} closes were below the 200-day since the base "
                  "high.\n\n"
                  "The full Trend Template is not required on the base-high day; it is checked on "
                  "the signal day instead (G1–G8).",
        "VCP-05": "**Not too deep.** From the base high down to the base low is at most "
                  "{MAX_BASE_DEPTH_PCT}%. Deeper than {DEEP_BASE_FLAG_PCT}% is flagged, not rejected.",
        "VCP-04": "**Enough pullbacks.** At least {MIN_CONTRACTIONS} pullbacks since the base high, "
                  "counting the one still in progress. A turn counts only after price reverses by a "
                  "threshold in both directions:\n\n"
                  "- at first, the larger of {VCP.zigzag_pct}% and {VCP.zigzag_atr_mult} ATR;\n"
                  "- after each pullback, {VCP.zigzag_shrink_ratio} times that pullback's depth, but "
                  "never less than {VCP.zigzag_floor_pct}% or {VCP.zigzag_floor_atr_mult} ATR — so "
                  "the small late pullbacks a VCP ends with can still register.\n\n"
                  "**What counts as a pullback** (Minervini's \"T\"). A new one starts only at a rally "
                  "that gets at least {VCP.t_recovery} of the way from the base's lowest low so far "
                  "back up to its high. A smaller bounce is part of the pullback in progress: a lower "
                  "low after it deepens that pullback, a higher one is ignored.\n\n"
                  "Example: Netflix in 2009 fell from 71.8 to 51.8, bounced to 61 twice, rallied to "
                  "68.1, fell to 56.1, rallied to 68.9 and fell to 63.3. The bounces to 61 reach under "
                  "half of the way back, so the base has three pullbacks — 28%, 18% and 8% — as "
                  "Minervini's own footprint has it (\"27W 27/7 3T\"), not seventeen.\n\n"
                  "Finished pullbacks shallower than {MIN_SWING_PCT}% are dropped. More than "
                  "{MAX_CONTRACTIONS} is flagged, not rejected.",
        "VCP-06": "**Pullbacks contracting.** Pullbacks must have got smaller since the last time "
                  "they got bigger.\n\n"
                  "- **Reference:** the latest pullback more than {WIDEN_TOL} times the one before "
                  "it (a widening). With none, the first pullback.\n"
                  "- From the reference on, inclusive, there are at least {MIN_FROM_REFERENCE} "
                  "pullbacks, each no more than {WIDEN_TOL} times as deep as the one before it, and "
                  "the last no more than {WIDEN_TOL} times the smallest before it — Minervini's "
                  "\"about half, plus or minus a reasonable amount\", so 5.4% then 5.7% still "
                  "counts as contracting.\n"
                  "- The last is at most {FINAL_REF_RATIO} times the reference.\n\n"
                  "Example: 15%, 25%, 12%, 6%. The 25% is a widening, so it is the reference; 12% "
                  "and 6% shrink; 6 ÷ 25 = 0.24. Passes. A base that has just widened and not "
                  "tightened again fails here: it is not ready yet.",
        "VCP-07": "**Higher lows: switched off.** A pullback whose low undercuts an earlier one is "
                  "kept — that is the shakeout. One that does not close back above the earlier low "
                  "within {UNDERCUT_RECOVERY_DAYS} sessions is recorded as a failed undercut, never "
                  "rejected; one whose {UNDERCUT_RECOVERY_DAYS} sessions have not all passed yet is "
                  "pending. The chart's base checklist and the Candidates tab's base notes show the "
                  "count.",
        "VCP-08": "**Tight area ready.** The last pullback — from the pivot to today — is at least "
                  "{TIGHT_MIN_DAYS} sessions old, and the tight low is at most {TIGHT_PCT}% below "
                  "the pivot.\n\n"
                  "A very volatile stock can never pass this. A pullback only counts once it is at least "
                  "{VCP.zigzag_floor_atr_mult} ATR deep (VCP-04), using the ATR on the base-high day. When "
                  "{VCP.zigzag_floor_atr_mult} ATR is more than {TIGHT_PCT}% of the price — an ATR above "
                  "about 6.7% with these settings — no last pullback can be both deep enough to count and "
                  "shallow enough to pass. Measured from 2013, no such base completed: 1% of bases in India "
                  "and 3% in the US.",
        "VCP-09": "**Pivot near the top.** The pivot is at least {UPPER_ZONE} of the way from the "
                  "base low to the base high, or at least {PIVOT_NEAR_HIGH} times the base high. A "
                  "lower pivot is not a pivot buy; the base can still give a cheat (S3, S4).\n\n"
                  "Example: a base from 100 down to 50 with the pivot at 85 is 0.7 of the way up, so "
                  "it passes, though the pivot is only 0.85 times the base high.",
        "VCP-10": "**Volume dried up.** Over the tight area, either average volume is at most "
                  "{DRYUP_RATIO} times the 50-day average, or at least {DRYUP_QUIET_DAYS} sessions "
                  "trade at or under {DRYUP_QUIET_RATIO} times it. The 50-day average is taken the "
                  "day before the tight area began, so the quiet days do not lower their own "
                  "yardstick.",
        "VCP-11": "**Volatility shrink: switched off.** Today's ATR as a % of the close, against the "
                  "same on the base-high day.",
    }
    # The page shows each group as its own section (strategies/base.py). Every fact here was checked
    # against the code that trades it: signal_meta and build_plans above, portfolio_sim's fill checks,
    # _manage_minervini and Exposure, and spec.market_ok / results_blackout.
    entry_rules = (
        "Every buy starts from a signal on a session's close and fills in a later session, so the signal "
        "price and the price paid are never the same. The setups are described under Rules.",
        "Pivot breakout (MV-01, EN-01). Bought at the next session's open. Skipped if that open is "
        "more than {BUY_RANGE_PCT}% above the pivot (too extended to buy) or at or below the tight "
        "low (the setup has already failed).",
        "Coiled below the pivot (MV-02, EN-02). A buy-stop order is placed 0.1% above the pivot and "
        "kept for up to 10 sessions.\n\n"
        "- **Fills** only on a session that CLOSES at or above the pivot, at that close. A session "
        "that pokes through during the day and closes back under it does not fill; the order keeps "
        "waiting.\n"
        "- **Skipped** if the fill would be more than {BUY_RANGE_PCT}% above the pivot.\n"
        "- **Cancelled** by a close below the tight low.",
        "Cheats (MV-03, MV-04). Bought at the next session's open. Skipped if that open is more than "
        "{BUY_RANGE_PCT}% above the shelf's high, or at or below the shelf's low.",
        "Power play (MV-05). Bought at the next session's open. Skipped if that open is more than "
        "{BUY_RANGE_PCT}% above the flag's pivot, or at or below the flag's tight low.",
        "Flat base (S6). Bought at the next session's open. Skipped if that open is more than "
        "{BUY_RANGE_PCT}% above the base high, or at or below the low of the {FLAT_PIVOT_DAYS} "
        "sessions before the breakout.",
        "Up to {MAX_ENTRIES_PER_BASE} entries per base (EN-04), the failure reset. Once a base, or a "
        "power play's flag, has been bought that many times, it is never bought again.\n\n"
        "Only a SHAKEOUT reopens a base — the stop, the breakeven stop, or a failed 20-day "
        "(EX-02b, when switched on) — never a trend exit, "
        "which says the move itself is over rather than that the trade was shaken out of it. The "
        "setup still has to re-fire on its own; this only stops the veto. Minervini keeps a stock "
        "that stopped him out on his list, because a failed pivot can reset within days and "
        "become a better entry than the first. At 1, a base is never bought again after a "
        "stop-out.",
        "Same-day ties (PF-03). When more stocks trigger than there are free slots, the highest RS "
        "rating is bought first, then the smallest tight area (pivot to tight low, as a % of the "
        "pivot).",
        "Every fill must still pass the checks under Stop and Target, tested again on the price actually "
        "paid: a gap at the open moves the buy price but not the stop or the target.",
    )
    stop_rules = (
        "Where it goes (SL-01). {STOP_BUFFER_PCT}% under the tight low — the lowest low of the "
        "base's last pullback. For a cheat it goes under the shelf's low; for a power play under the "
        "flag's tight low. That low is where the setup is proven wrong: a stock that falls back "
        "through it was not ready.",
        "It defines the risk (SL-02). The distance from the price paid to the stop is the trade's "
        "risk, called 1R. Every result is counted in R: +2R is a gain of twice the risk taken, −1R a "
        "full stop-out.",
        "How far is too far (SL-03). If the stop is more than {MAX_STOP_PCT}% below the price paid, "
        "the trade is skipped: the loss would be too large. On the live screen such a setup shows as "
        "WATCH.",
        "How it sells (EX-01). The stop is a standing sell order: it sells during the session the "
        "moment the low touches it. If the stock opens below the stop — after bad news overnight — "
        "it sells at that open, so a gap can cost more than 1R.\n\n"
        "If the stop and a profit level are both touched in one session, the stop is assumed to come "
        "first.",
        "It only ever moves up (EX-03). Once the trade's high has reached +{BREAKEVEN_R}R, the stop "
        "is raised to the price paid plus the round trip's costs, from the next session on. A "
        "reversal can then no longer turn the trade into a loss, short of a gap through the stop. "
        "The stop is never lowered.",
    )
    target_rules = (
        "There is no sell order at the target. Minervini does not sell a whole position at a fixed "
        "price, and neither does this strategy: winners are sold by the rules under Exit. The target is "
        "used for one thing — deciding whether the trade is worth taking.",
        "How it is measured. From the chart, not from the risk.\n\n"
        "- **Pivot buy (MV-01, MV-02):** the base's measured move — its depth, from the base high down to "
        "its lowest low — added to the price paid.\n"
        "- **Cheat (MV-03, MV-04):** bought below the old high, so the target is the base high plus that "
        "same measured move.\n"
        "- **Power play (MV-05):** no base, so the flag's tight area — pivot minus tight low — added to the "
        "price paid.\n"
        "- **Flat base (S6):** the base's depth, high to low, added to the price paid. A base at most "
        "{FLAT_MAX_DEPTH_PCT}% deep projects at most that, so the 2:1 test below rejects most flat bases: "
        "on 60 random US stocks, 2013-2021, all 12 that broke out were refused at 0.3-1.5R.",
        "Overhead supply caps it. An older swing high above the base is where earlier buyers wait to sell, "
        "so the target is lowered to the nearest one. Only a level at least {OVERHEAD_CLUSTER_ATR} ATR above "
        "the base high counts; anything closer is part of the base's own ceiling.",
        "The {MIN_STRUCTURAL_R}:1 test. The reward (price paid to target) must be at least "
        "{MIN_STRUCTURAL_R} times the risk (price paid to stop). Example: buy at 100 with the stop at 94 "
        "risks 6. A target of 115 offers 15, which is 2.5 times 6: taken. A target of 110 offers 10, only "
        "1.7 times: skipped. A setup that falls short is skipped, never padded up.\n\n"
        "It is tested twice: on the signal session's close, and again on the price actually paid. A gap "
        "up raises the price paid without moving the stop or the target, so a setup that passed on the "
        "close can fail at the open.",
    )
    exit_rules = (
        "Each session an open position is checked against these rules, in this order, and the first that "
        "applies acts. Apart from the stop (see Stop), each exit is decided on the session's close and "
        "sold at the next session's open.",
        "Unconfirmed breakout (MV-02 buys only). If the session that filled the buy-stop traded less "
        "than {VOL_MULT} times its 50-day average volume, the breakout was not confirmed: the whole "
        "position is sold.\n\n"
        "This is decided on the close of the session that filled, after the fill — the fill itself "
        "never depends on that session's volume.",
        "EX-04 — sell part into strength. {STRENGTH_FRAC} of the position (about a third) is sold "
        "the first time EITHER trigger fires, once only, and the rest is held for the trend:\n\n"
        "- the trade's high reaches +{PARTIAL_R}R — the same point EX-03 moves the stop to "
        "breakeven, so the gain is banked on the bar the protection goes on;\n"
        "- a close {STRENGTH_EXT_PCT}% or more above the 50-day average.\n\n"
        "The +{PARTIAL_R}R trigger is the half this implementation was missing. Raising the stop "
        "without selling anything turns an unrealised gain into nothing rather than into cash, and "
        "measured on the 1.22 runs every breakeven-stop exit in both books came from a trade that "
        "had already reached +{PARTIAL_R}R.",
        "EX-05 — climax run. Once a close is 25% or more above the price paid, any sign of a buying "
        "climax sells that same part, if EX-04 has not already:\n\n"
        "- the biggest one-day gain since the buy, on the biggest volume since the buy;\n"
        "- 8 or more up closes in the last 10 sessions;\n"
        "- a close 70% or more above the 200-day average;\n"
        "- an open 3% or more above the previous close, once the position is up more than 50%.",
        "EX-06 — the trend ends. The first close below the 50-day average sells everything still "
        "held. This is how most winners end.\n\n"
        "Under the variant the live screen runs, that close must also come on at least the 50-day "
        "average volume.",
        "EX-07 — time stop. If the high has not reached +1R within {TIME_STOP_DAYS} sessions of the "
        "buy, the position is sold: it has tied up money without proving itself.",
        "EX-02b — the breakout fails its 20-day average: switched off (FAIL_SMA20_DAYS = 0). Set to a "
        "number of sessions, a close below the 20-day average within that many sessions of the buy "
        "sells everything at the next open. Minervini judges "
        "a breakout by the 20-day rather than the pivot: once out, it should hold the 20-day and "
        "in most cases not close below it, and a squat (a breakout that closes off its high and "
        "slips back into the base) gets up to about ten days to recover — unless it closes below "
        "the 20-day, which lowers the odds. On stored data it cost more than it saved: at ten "
        "sessions it sold over 40% of trades for about -0.5R each, and cut more future trend-exit "
        "winners than full stops, so expectancy fell in both markets (2013-2021, in-sample).",
        "EX-02 — failed breakout: switched off. A close back below the pivot soon after the buy "
        "would sell here, but Minervini lets a dip below the pivot run to the stop, and on stored "
        "data about two in three breakouts close back under the pivot within ten sessions. "
        "`--fail-days 5` turns it on.",
    )
    sizing_rules = (
        "Each trade risks 1% of the account (SL-04). Shares = 1% of the account ÷ the distance to "
        "the stop, so the loss at the stop is the same whatever the stop's width. Example: a "
        "$100,000 account risks $1,000; buying at $50 with the stop at $47 risks $3 a share, so 333 "
        "shares.",
        "No position over 25% of the account (SL-05); shares are cut to fit.",
        "Half size until the record pays (PE-01 to PE-03). A trade risks {PE_PILOT_FRAC} times the "
        "normal amount — half — during the first {PE_WARMUP} trades, after two losses in a row, or "
        "while the last {PE_WINDOW} closed trades add up to zero or less. Full size returns once "
        "they add up to a gain. Only trades closed on earlier sessions count, so a stop-out this "
        "morning cannot resize a buy this afternoon. The aim is smaller drawdowns, not bigger "
        "returns.",
        "Pressing (PE-04, `--pe-press`, off by default). Once the last {PE_WINDOW} trades are "
        "{PE_PRESS_NET_R}R or more up, a trade risks 1.25 times the normal amount and two extra "
        "positions are allowed.",
        "Portfolio limits.\n\n"
        "- **Positions (PF-02):** at most {MAX_POSITIONS} at once.\n"
        "- **Open risk (PF-04):** what all open positions would lose at their stops adds up to no "
        "more than {MAX_OPEN_RISK_PCT}% of the account. Each position's risk is measured from the "
        "lower of its last close and the price paid down to its stop, so a stop at or above the "
        "price paid counts as no risk.\n"
        "- **Order size (SL-06):** no order over {MAX_ADV_PCT}% of the stock's 50-day average daily "
        "traded value.\n\n"
        "In a backtest `--spec` sets these limits, the same-day ranking and the costs.",
    )
    filter_rules = (
        "The market is unhealthy (the market filter). New buys only while all of these hold:\n\n"
        "- the benchmark index closes above its {MKT_INDEX_SMA}-day average;\n"
        "- that average is higher than {MKT_SMA_RISING_DAYS} sessions ago;\n"
        "- breadth — the share of the 1,000 most-traded stocks above their own 50-day average — is "
        "above {MKT_BREADTH_MIN_PCT}%, or higher than {MKT_BREADTH_RISING_DAYS} sessions ago;\n"
        "- leadership, only when MKT_HIGHS_LOWS_DAYS is set (it is {MKT_HIGHS_LOWS_DAYS}, 0 = off): "
        "over that many sessions, more of those stocks made new 52-week highs than "
        "{MKT_HIGHS_LOWS_RATIO} times the number making new lows.\n\n"
        "When it fails, no new buy is taken and waiting buy-stops are cancelled; positions already "
        "held are kept and managed as usual. The live screen applies the same test.\n\n"
        "`--mkt01` swaps in an older test (the index above its 200-day, and its 50-day above its "
        "200-day); `--mkt-confirm N` makes a recovery wait N sessions before buying resumes.",
        "The uptrend is young — only when SMA200_PREF_REQUIRED is 1 (it is {SMA200_PREF_REQUIRED}). No new "
        "buy while the 200-day average is not higher than {SMA200_RISING_PREF_BARS} sessions ago (about 4-5 "
        "months), even though it passed G5's one-month test. Minervini states the month as the minimum "
        "and the longer rise as a preference, so this stays off until a backtest shows it helps.",
        "Results are due. No new buy with quarterly results due within {EARNINGS_BLACKOUT_DAYS} "
        "days: a results-day gap can jump straight past the stop. Live, the date comes from the "
        "earnings calendar; in a backtest it is estimated from the company's past announcement "
        "timing, and the stored filing date is checked as well.",
        "The stock is too thin. It must trade at least ₹{MIN_TURNOVER_INR_CR} crore or "
        "${MIN_TURNOVER_USD_M} million a day (50-day average of volume × close). The live screen "
        "also wants a price of at least ₹{LIVE_MIN_PRICE_INR} or ${LIVE_MIN_PRICE_USD}.\n\n"
        "The price floor applies to the live screen only: a backtest reads split-adjusted prices, "
        "where a winner's early price is divided by every later split.",
        "There is no room. With {MAX_POSITIONS} positions open, or the open-risk limit used up, a "
        "new signal is passed over; a waiting buy-stop keeps waiting for room until it expires.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "A confirmed breakout (MV-01): every Trend Template gate passes and the stop is "
                                 "within {MAX_STOP_PCT}% of entry. Buy at the next open. Watch flags never cap "
                                 "this strategy's decision.",
        "TRADE_ON_TRIGGER": "A valid plan from any setup other than MV-01: coiled within {COIL_PCT}% below the "
                            "pivot (MV-02), entered only on a session that closes through it; a cheat (MV-03 / "
                            "MV-04) that cleared its shelf on the close, bought at the next open and stopped under "
                            "the shelf low; or a power play (MV-05), bought at the next open and stopped under the "
                            "flag's tight low. The market regime never caps a decision to this tier.",
        "WATCH_WAIT": "A valid plan held back: its stop sits more than {MAX_STOP_PCT}% below entry, results are due "
                      "within {EARNINGS_BLACKOUT_DAYS} days, the 200-day has risen for under "
                      "{SMA200_RISING_PREF_BARS} sessions while SMA200_PREF_REQUIRED is 1, or the market filter "
                      "allows no new buys (see the note below). Worth watching, not buying.",
        "AVOID": "A Trend Template gate failed, or there is no valid entry plan — no breakout, coil or cheat setup, "
                 "or a plan that fails its checks (such as projecting under {MIN_STRUCTURAL_R}:1).",
    }
    regime_note = (
        "When this strategy's own market filter is risk-off (the guide's test above — not the shared market "
        "regime the other strategies use), no new buys: HIGH CONFIDENCE and ON TRIGGER both become WATCH, "
        "with the reason 'market filter: no new buys'. WATCH and AVOID are untouched, so the watchlist of "
        "setting-up bases stays intact for the turn."
    )
    param_docs = (
        ("Swing confirmation", "SWING_K", "Bars either side of a swing point; it is known only this many bars later."),
        ("Base-high break", "VCP.bh_break_atr", "ATRs a close must clear the base high by to end the base (VCP-02)."),
        ("Prior advance", "PRIOR_ADVANCE_PCT", "Rise into the base high from the lowest low of the window before it (VCP-01)."),
        ("Prior-advance window", "VCP.prior_window", "Sessions before the base high that the prior advance is measured over (VCP-01)."),
        ("Base length, minimum", "BASE_MIN_DAYS", "Sessions from the base high (VCP-02)."),
        ("Base length, maximum", "BASE_MAX_DAYS", "About 65 weeks (VCP-02)."),
        ("Contractions, minimum", "MIN_CONTRACTIONS", "VCP-04."),
        ("Contractions, maximum", "MAX_CONTRACTIONS", "VCP-04: more is flagged, not rejected."),
        ("Pullback turn, first", "VCP.zigzag_pct", "VCP-04: % reversal that counts as a turn at the start of the base …"),
        ("Pullback turn, in ATRs", "VCP.zigzag_atr_mult", "… or this many ATRs, whichever is larger."),
        ("Pullback turn, shrink", "VCP.zigzag_shrink_ratio", "VCP-04: after each pullback the turn threshold becomes this × its depth …"),
        ("Pullback turn, floor", "VCP.zigzag_floor_pct", "… but never below this % …"),
        ("Pullback turn, floor in ATRs", "VCP.zigzag_floor_atr_mult", "… or this many ATRs."),
        ("Smallest pullback", "MIN_SWING_PCT", "VCP-04: finished pullbacks shallower than this % are dropped."),
        ("Base depth, deepest", "MAX_BASE_DEPTH_PCT", "Base high to base low, VCP-05."),
        ("Deep-base flag", "DEEP_BASE_FLAG_PCT", "Recorded, never a rejection (VCP-05)."),
        ("Volume dry-up, quiet days", "DRYUP_QUIET_DAYS", "The alternative route past VCP-10."),
        ("Volume dry-up, quiet level", "DRYUP_QUIET_RATIO", "A quiet session is at or under this × the 50-day."),
        ("Widening tolerance", "WIDEN_TOL", "A contraction more than this × the previous one is a widening, "
                                            "and becomes the reset rule's reference (VCP-06)."),
        ("Contractions since the widening", "MIN_FROM_REFERENCE", "Counted from the reference, inclusive (VCP-06)."),
        ("Final ÷ reference", "FINAL_REF_RATIO", "The final contraction against the reference (VCP-06)."),
        ("Undercut recovery", "UNDERCUT_RECOVERY_DAYS", "Sessions an undercut has to reclaim the old low "
                                                        "before it is logged as failed. Never a rejection."),
        ("Tight area, minimum age", "TIGHT_MIN_DAYS", "The final contraction must be at least this old (VCP-08). "
                                                       "There is no maximum; its length is recorded."),
        ("Pivot upper zone", "UPPER_ZONE", "Pivot position in the base range that counts as a pivot buy (VCP-09)."),
        ("Closes below the 200-day", "MAX_CLOSES_BELOW_200", "Allowed inside the base (VCP-03)."),
        ("Tight-area span", "TIGHT_PCT", "Deepest final contraction and widest tight area (VCP-08)."),
        ("Pivot near the base high", "PIVOT_NEAR_HIGH", "The alternative route into the upper zone (VCP-09)."),
        ("Volume dry-up", "DRYUP_RATIO", "Tight-area volume against its 50-day average (VCP-10)."),
        ("Coil distance", "COIL_PCT", "MV-02: how far below the pivot still counts."),
        ("Breakout volume", "VOL_MULT", "MV-01a, and MV-05's breakout."),
        ("Breakout close position", "UPPER_HALF", "MV-01c: the close at least this far from the day's low to its high."),
        ("Power play, run", "PP_RUN_MULT", "MV-05: price multiple at the flag high, over PP_RUN_WINDOW."),
        ("Power play, run window", "PP_RUN_WINDOW", "MV-05: sessions the run is measured over."),
        ("Power play, flag length", "PP_FLAG_MIN_DAYS", "MV-05: shortest pause that counts."),
        ("Power play, flag length max", "PP_FLAG_MAX_DAYS", "MV-05: longest pause that counts."),
        ("Power play, flag depth", "PP_FLAG_MAX_DEPTH_PCT", "MV-05: deepest the flag may fall."),
        ("Flat base, length", "FLAT_MIN_DAYS", "S6: shortest flat base, in sessions."),
        ("Flat base, length max", "FLAT_MAX_DAYS", "S6: longest flat base, in sessions."),
        ("Flat base, depth", "FLAT_MAX_DEPTH_PCT", "S6: deepest a flat base may be, high to low."),
        ("Flat base, pivot area", "FLAT_PIVOT_DAYS", "S6: sessions before the breakout whose volume must dry "
                                                   "up and whose low sets the stop."),
        ("Young listings", "YOUNG_LISTING", "1 = a stock listed under a year is judged on its history so far "
                                            "(averages that do not exist yet are waived); 0 = it waits a year (1.27)."),
        ("Young listing, first session", "YOUNG_MIN_BARS", "Sessions listed before a young listing is judged."),
        ("Power play, dry-up", "PP_DRYUP", "PP-06: 1 = the flag's tight area must pass VCP-10's volume test, 0 = off (1.26)."),
        ("Buy range", "BUY_RANGE_PCT", "MV-01b, and the most a fill may sit above the pivot."),
        ("Stop buffer", "STOP_BUFFER_PCT", "SL-01."),
        ("Maximum stop", "MAX_STOP_PCT", "SL-03, checked at the fill."),
        ("Cheat shelf length", "CHEAT_SHELF_DAYS", "Sessions in the shelf a cheat is bought from (MV-03/MV-04)."),
        ("Cheat shelf tightness", "CHEAT_SHELF_PCT", "Widest shelf, high to low, that counts as a cheat."),
        ("Cheat shelf dry-up", "CHEAT_DRYUP", "MV-03/MV-04: 1 = the shelf must pass VCP-10's volume test, 0 = tightness only (1.26)."),
        ("Minimum reward-to-risk", "MIN_STRUCTURAL_R", "Setups whose measured move projects less are refused — "
                                                 "tested on the signal close and again on the fill."),
        ("Block cheats on VCP-09 bases", "CHEAT_BLOCK_VCP09", "Experiment, off by default: 1 withholds a cheat "
                                                              "when the base's own pivot is below the upper zone."),
        ("Overhead cluster", "OVERHEAD_CLUSTER_ATR", "ATRs above the base high before a swing high caps the target."),
        ("Risk per trade", "cfg.risk_pct", "SL-04: share of equity risked per trade (0.01 = 1%)."),
        ("Largest position", "cfg.max_position_pct", "SL-05: share of equity one position may hold."),
        ("Positions", "MAX_POSITIONS", "PF-02, with --spec."),
        ("Breakeven trigger", "BREAKEVEN_R", "EX-03: R gained before the stop moves to breakeven plus costs."),
        ("Entries per base", "MAX_ENTRIES_PER_BASE", "EN-04: how many times one base may be bought — the failure reset. "
                                                      "Above 1, only a stop, breakeven stop or failed 20-day reopens it."),
        ("Part-sale trigger", "PARTIAL_R", "EX-04: R gained before about a third is sold. Pairs with the "
                                           "breakeven trigger, so the gain is banked as the stop moves up."),
        ("Failed-breakout window", "FAIL_DAYS", "EX-02: sessions after entry in which a close below the pivot sells (0 = off)."),
        ("20-day failure window", "FAIL_SMA20_DAYS", "EX-02b: sessions after entry in which a close below the 20-day average sells (0 = off)."),
        ("Sell into strength", "STRENGTH_EXT_PCT", "EX-04: % above the 50-day at which a part is sold."),
        ("Part sold into strength", "STRENGTH_FRAC", "EX-04 / EX-05: share of the position sold."),
        ("Climax sells a part", "CLIMAX_IS_PARTIAL", "EX-05: 1 = the strength part only, 0 = everything (1.7)."),
        ("Trend exit needs volume", "TREND_EXIT_NEEDS_VOLUME", "EX-06: 1 = only on above-average volume (1.7)."),
        ("Time stop", "TIME_STOP_DAYS", "EX-07: sessions to reach +1R (0 = off)."),
        ("Light-volume fill exit", "LIGHT_VOLUME_EXIT", "EN-02: sell a buy-stop fill on under-average breakout volume (1 = on)."),
        ("Low cheat", "LOW_CHEAT_ENABLED", "MV-03 on (1) or off (0)."),
        ("Results blackout", "EARNINGS_BLACKOUT_DAYS", "Days before results with no new buy."),
        ("Preferred uptrend", "SMA200_RISING_PREF_BARS", "W5: sessions over which the 200-day should have risen."),
        ("Preferred uptrend required", "SMA200_PREF_REQUIRED", "1 = W5 holds the plan at WATCH (no new buy); 0 = noted only."),
        ("Turnover floor, India", "MIN_TURNOVER_INR_CR", "₹ crore a day, 50-day average volume × close."),
        ("Turnover floor, US", "MIN_TURNOVER_USD_M", "$ million a day, 50-day average volume × close."),
        ("Price floor, India (live)", "LIVE_MIN_PRICE_INR", "₹; the live screen only."),
        ("Price floor, US (live)", "LIVE_MIN_PRICE_USD", "$; the live screen only."),
        ("Market filter", "MKT_GUIDE", "1 = the guide's test, 0 = MKT-01 (1.7)."),
        ("Index average", "MKT_INDEX_SMA", "Days in the benchmark's average the close must be above."),
        ("Index average rising over", "MKT_SMA_RISING_DAYS", "Sessions over which that average must have risen (0 = off)."),
        ("Breadth floor", "MKT_BREADTH_MIN_PCT", "% of stocks above their 50-day that counts as healthy."),
        ("Breadth rising over", "MKT_BREADTH_RISING_DAYS", "Sessions over which breadth may instead be rising."),
        ("Leadership window", "MKT_HIGHS_LOWS_DAYS", "Sessions over which new highs must outnumber new lows (0 = off)."),
        ("Leadership ratio", "MKT_HIGHS_LOWS_RATIO", "New highs must exceed this multiple of new lows."),
        ("EPS growth (guide level)", "FUND_EPS_GROWTH_MIN_PCT", "--fundamentals guide: quarterly EPS growth, %."),
        ("Sales growth (guide level)", "FUND_SALES_GROWTH_MIN_PCT", "--fundamentals guide: quarterly sales growth, %."),
        ("Margin slack (guide level)", "FUND_MARGIN_SLACK_PP", "--fundamentals guide: points the margin may fall."),
        ("Exposure window", "PE_WINDOW", "PE-01: closed trades judged for sizing, with --pe."),
        ("Exposure warm-up", "PE_WARMUP", "PE-02: trades sized as pilots at the start of a run, with --pe."),
        ("Pilot fraction", "PE_PILOT_FRAC", "PE-02: share of the risk budget at pilot size, with --pe."),
        ("Press threshold", "PE_PRESS_NET_R", "PE-04: net R over the window that unlocks 1.25x, with --pe-press."),
        ("Risk-on confirmation", "MKT_CONFIRM_DAYS", "MKT-01: sessions risk-on must hold, with --mkt-confirm."),
        ("Open-risk cap", "MAX_OPEN_RISK_PCT", "PF-04, with --spec."),
        ("Liquidity cap", "MAX_ADV_PCT", "SL-06: largest order as a % of 50-day average traded value, with --spec."),
        ("Minimum history", "min_bars", "Bars required before the template can judge a symbol."),
    )
    # No --strategy here: jobs/registry.py already passes "--strategy <key>", and a second
    # one wins on argparse, so naming the key twice broke the moment the key was renamed.
    # Both trade tiers: the guide's default entry is the buy-stop through the pivot (MV-02) and it lists the
    # cheats (MV-03 / MV-04), all graded TRADE ON TRIGGER; MV-01 alone fired 9 times in 16 years in India.
    backtest_args = "--spec --market-filter --pe --accept-labels 'TRADE - HIGH CONFIDENCE,TRADE ON TRIGGER'"
    base_rules = VCP_RULES
    #: PROVISIONAL -- the screen lists candidates under this until a variant beats the baseline,
    #: then this declaration is replaced. Not part of the shipped rules: backtests never apply it.
    live_variant = {
        "name": "Block cheats on VCP-09 bases + EX-06 needs volume",
        "const": {"CHEAT_BLOCK_VCP09": 1, "TREND_EXIT_NEEDS_VOLUME": 1},
        "why": ("Together they beat each one alone in BOTH markets, on profit factor and average R rather "
                "than just total R -- the bar set before the runs. Against the 1.22 baseline: India +85.9R, "
                "PF 1.30 -> 1.85, avgR +0.133 -> +0.414 (volume alone was +78.4R, PF 1.74; the VCP-09 block "
                "alone +13.1R, PF 1.41); US +43.1R, PF 0.79 -> 0.89, avgR -0.081 -> -0.048 (alone: +20.0R / "
                "PF 0.84 and +14.2R / PF 0.82). The cost is drawdown: India's deepest is -25.2% against the "
                "baseline's -19.8%, because waiting for volume holds trades through more dips. The VCP-09 "
                "block decides which stocks are listed; the volume rule only decides when to sell, so it "
                "changes nothing on this list -- it is here so the live rules are named in full. The US is "
                "still a losing book under them. Provisional: replace this when a variant beats it."),
    }

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The guide's turnover floor, then the Trend Template (shared with `minervini`), as of one row.

        The floor replaces the market's own: 50-day average volume x the close, against
        MIN_TURNOVER_INR_CR / MIN_TURNOVER_USD_M. Both factors are split-adjusted the same way, so
        the product is the turnover actually traded on that date."""
        floor = _min_turnover(cfg)
        v50, close = last.get("vol_sma50"), last.get("close")
        if pd.isna(v50) or pd.isna(close) or float(v50) * float(close) < floor:
            return False, f"turnover below {floor:,.0f} a day"
        return trend_template_row(_without_liquidity_floor(cfg), last)

    def passes_prefilter(self, cfg: MarketConfig, enriched_daily) -> tuple[bool, str]:
        """Live screening only (a backtest uses prefilter_mask): the guide's price floor on
        today's real price, then the row test."""
        if enriched_daily is not None and len(enriched_daily):
            floor = _live_min_price(cfg)
            if float(enriched_daily["close"].iloc[-1]) < floor:
                return False, f"price below {floor:g}"
        d = enriched_daily
        if d is not None and len(d) and is_young_row(d.iloc[-1], len(d)):
            ok, why = self.prefilter_row(cfg, d.iloc[-1])
            if ok or why.startswith("turnover"):
                return ok, why
            return young_template_row(_without_liquidity_floor(cfg), d.iloc[-1],
                                      float(d["low"].min()), float(d["high"].max()))
        return super().passes_prefilter(cfg, enriched_daily)

    def prefilter_mask(self, cfg: MarketConfig, enriched_daily) -> "pd.Series":
        """The shared mask, plus a young listing's sessions (YOUNG_LISTING) judged by
        `young_template_row` on the low and high since listing."""
        m = super().prefilter_mask(cfg, enriched_daily)
        d = enriched_daily
        if not YOUNG_LISTING or d is None or d.empty:
            return m
        lo, hi = d["low"].cummin(), d["high"].cummax()
        floor, ycfg = _min_turnover(cfg), _without_liquidity_floor(cfg)
        for i in range(YOUNG_MIN_BARS - 1, min(len(d), 260)):
            row = d.iloc[i]
            if m.iloc[i] or not is_young_row(row, i + 1):
                continue
            v50, close = row.get("vol_sma50"), row.get("close")
            if pd.isna(v50) or pd.isna(close) or float(v50) * float(close) < floor:
                continue
            m.iloc[i] = young_template_row(ycfg, row, float(lo.iloc[i]), float(hi.iloc[i]))[0]
        return m

    def rs_young_min_bars(self) -> int:
        """Sessions after which the RS rating rates a young listing on its history so far."""
        return YOUNG_MIN_BARS if YOUNG_LISTING else 0

    def _young_gates(self, ctx: StockContext, result: StrategyResult) -> None:
        """G2-G8 for a young listing: a condition whose input needs more sessions than the stock has
        traded is waived, or read over the history since listing (the same tests as
        `young_template_row`)."""
        d = ctx.daily
        last, n = d.iloc[-1], len(d)
        c = float(last["close"])
        s50, s150, s200 = last.get("sma50"), last.get("sma150"), last.get("sma200")
        listed = f"waived: listed {n} sessions"
        if pd.isna(s150):
            result.ok("G2", f"{listed}, the 150-day needs 150")
        if pd.isna(s200):
            result.ok("G3", f"{listed}, the 200-day needs 200")
        if pd.isna(s150) or pd.isna(s200):
            ok = (pd.isna(s150) or s50 > s150) and (pd.isna(s150) or pd.isna(s200) or s150 > s200)
            (result.ok if ok else result.fail)("G4", "the averages that exist are stacked" if ok
                                               else "the averages that exist are not stacked")
        if pd.isna(last.get("sma200_21d_ago")):
            result.ok("G5", f"{listed}, a rising 200-day needs {200 + SMA200_RISING_BARS}")
        if pd.isna(last.get("low_252")):
            pct = (c / float(d["low"].min()) - 1) * 100
            (result.ok if pct >= MIN_PCT_ABOVE_52W_LOW else result.fail)(
                "G6", f"{pct:.1f}% above the low since listing")
        if pd.isna(last.get("high_252")):
            pct = (1 - c / float(d["high"].max())) * 100
            (result.ok if pct <= MAX_PCT_BELOW_52W_HIGH else result.fail)(
                "G7", f"{pct:.1f}% below the high since listing")
        if pd.isna(last.get("rs_score")) and not ctx.extras.get("rs_ranked"):
            result.ok("G8", f"young listing: rated on its {n} sessions when the run rates the market")
        result.recompute_first_fail()
        ctx.extras["young_listing_bars"] = n

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """Live: the same market filter the backtest applies (backtesting/spec.py market_ok),
        as of the latest stored session, instead of the shared market-regime downgrade."""
        try:
            from ..backtesting import spec as spec_mod
            ok = spec_mod.market_ok(market_key, guide=bool(MKT_GUIDE))
            br = spec_mod.breadth_pct50(market_key)
        except Exception:      # no benchmark or breadth stored: fall back to the shared regime
            return default
        if not len(ok):
            return default
        if len(br) and (br.index[-1] - ok.index[-1]).days > 4:
            import logging
            logging.getLogger(__name__).warning(
                "minervini market filter: the benchmark's last stored close (%s) is behind breadth (%s); "
                "risk-off is judged as of %s", ok.index[-1].date(), br.index[-1].date(), ok.index[-1].date())
        return not bool(ok.iloc[-1])

    # ---------- evaluation ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        if is_young_row(d.iloc[-1], len(d)):
            self._young_gates(ctx, result)
        e = ctx.extras
        today, prev = vcp_spec.detect(d, VCP), vcp_spec.detect(d.iloc[:-1], VCP)
        last = d.iloc[-1]
        close, high, low, vol = (float(last[k]) for k in ("close", "high", "low", "volume"))
        v50 = float(last["vol_sma50"]) if pd.notna(last.get("vol_sma50")) else float("nan")
        prev_close = float(d["close"].iloc[-2])

        breakout = bool(prev["ok"] and prev_close <= prev["pivot"] < close)
        base = prev if breakout else today
        vol_ratio = vol / v50 if v50 and v50 == v50 else float("nan")
        rng = high - low
        upper = (close - low) / rng if rng > 0 else 1.0
        confirmed = {
            "W1": not (vol_ratio >= VOL_MULT),
            "W2": breakout and close > base["pivot"] * (1 + BUY_RANGE_PCT / 100),
            "W3": upper < UPPER_HALF,
        }
        mv01 = breakout and not any(confirmed.values())
        mv02 = bool(not breakout and today["ok"] and today["pivot"] * (1 - COIL_PCT / 100) <= close <= today["pivot"])
        # The cheat entries. Minervini buys three points in a base -- the low cheat
        # (lower third), the cheat/"3C" (middle third) and the pivot buy at the top
        # -- and only the last was implemented. A cheat is taken while the base is
        # still FORMING, so it runs off any base clearing VCP-01/02/03 rather than a
        # completed VCP, and its stop is the shelf low rather than the base low,
        # which is the whole reason he takes it: the stop is near.
        # yesterday's shelf, not today's: the shelf's high is the max over a window
        # that INCLUDES the current bar, so today's close can never exceed it and the
        # cross would be unsatisfiable. MV-01 freezes the pivot the same way.
        ch = prev if prev.get("cheat_ok") else None
        crossed = cheat_cross(prev, prev_close, close)
        # The experiment above, applied where the setup is decided rather than in the detector:
        # the base and its shelf are still measured and still drawn, only the entry is withheld.
        if CHEAT_BLOCK_VCP09 and prev.get("fail") == "VCP-09":
            if crossed:
                e["cheat_withheld"] = "VCP-09"   # the cheat fired and the variant withheld it
            crossed = None
        mv03, mv04 = crossed == MV03, crossed == MV04
        # MV-05, the power play. Its pivot is frozen on yesterday's bar for the same reason MV-01's
        # is: a pivot taken from a window that includes today can never be crossed by today.
        pp_prev = vcp_spec.detect_power_play(d.iloc[:-1], POWER_PLAY)
        pp_ok = not pp_prev.get("fail") and pp_prev.get("pivot")
        mv05 = bool(pp_ok and prev_close <= pp_prev["pivot"] < close
                    and vol_ratio >= VOL_MULT and upper >= UPPER_HALF
                    and close <= pp_prev["pivot"] * (1 + BUY_RANGE_PCT / 100))
        result.setups[MV01], result.setups[MV02] = mv01, mv02
        result.setups[MV03], result.setups[MV04] = mv03, mv04
        result.setups[MV05] = mv05
        # S6, the flat base: yesterday's base, if it never became a VCP, is shallow and four to seven
        # weeks long, and today closes through its high with the MV-01 conviction tests.
        flat = False
        if (not prev["ok"] and prev.get("bh") and prev["fail"] not in ("VCP-01", "VCP-02", "VCP-03", "VCP-05")
                and prev.get("base_days") is not None and FLAT_MIN_DAYS <= prev["base_days"] <= FLAT_MAX_DAYS
                and prev.get("base_depth_pct") is not None and prev["base_depth_pct"] <= FLAT_MAX_DEPTH_PCT):
            fh = float(prev["bh"])
            area = d.iloc[-1 - FLAT_PIVOT_DAYS:-1]
            dry, quiet = vcp_spec._dryup(d.iloc[:-1], len(d) - 1 - FLAT_PIVOT_DAYS, area["volume"],
                                         DRYUP_QUIET_RATIO)
            e.update(flat_pivot=fh, flat_low=float(area["low"].min()),
                     flat_depth_pct=float(prev["base_depth_pct"]), flat_dryup=float(dry), flat_quiet_days=int(quiet),
                     flat_base_date=str(prev["bh_date"].date()))
            flat = bool(prev_close <= fh < close and vol_ratio >= VOL_MULT and upper >= UPPER_HALF
                        and close <= fh * (1 + BUY_RANGE_PCT / 100)
                        and (dry <= DRYUP_RATIO or quiet >= DRYUP_QUIET_DAYS))
        result.setups[FLAT] = flat
        if pp_ok:
            ctx.extras.update(pp_pivot=pp_prev["pivot"], pp_tight_low=pp_prev["tight_low"],
                              # a STRING, like base_date above: ctx.extras is serialised to JSON
                              # for the signal's meta, and a pandas Timestamp is not serialisable
                              pp_flag_high_date=(str(pp_prev["flag_high_date"].date())
                                                 if pp_prev.get("flag_high_date") is not None else None),
                              pp_run_pct=round(pp_prev["run_pct"], 1) if pp_prev.get("run_pct") else None,
                              pp_flag_days=pp_prev.get("flag_days"))

        for code in ("W1", "W2", "W3"):
            on = bool(breakout and confirmed[code])
            result.watch_flags[code] = on
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = f"volume {vol_ratio:.2f}× its 50-day average"
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = f"{(close / base['pivot'] - 1) * 100:.1f}% above the pivot"
        if result.watch_flags["W3"]:
            result.watch_notes["W3"] = f"closed at {upper * 100:.0f}% of the day's range"
        # W5: the 200-day is rising (G5 already required that) but for less than the preferred
        # 4-5 months. Read from ctx.daily rather than a precomputed column -- `sma200_21d_ago`
        # exists because the SCREEN needs it on every snapshot row, while this is wanted only on
        # the bars a signal reaches, and adding a second shifted column to the shared indicator
        # pipeline for one watch flag would cost every screen run.
        s200_now = last.get("sma200")
        d200 = ctx.daily["sma200"] if "sma200" in ctx.daily else None
        s200_pref = (float(d200.iloc[-1 - SMA200_RISING_PREF_BARS])
                     if d200 is not None and len(d200) > SMA200_RISING_PREF_BARS
                     and pd.notna(d200.iloc[-1 - SMA200_RISING_PREF_BARS]) else float("nan"))
        pref_ok = bool(pd.notna(s200_now) and s200_pref == s200_pref and float(s200_now) > s200_pref)
        # W5 is a refinement of G5, so it only speaks when G5's condition holds: "rising, but not
        # for long enough". On a stock whose 200-day is not rising at all the gate has already
        # rejected it, and raising a flag that reads "rising but under the preferred" would be
        # false on its own terms.
        #
        # Unknown history is also not a warning: a stock without SMA200_RISING_PREF_BARS bars
        # behind its 200-day cannot answer the question, and flagging it would read as "the trend
        # is young" when the truth is "not measurable".
        s200_min = last.get("sma200_21d_ago")
        min_ok = bool(pd.notna(s200_now) and pd.notna(s200_min) and float(s200_now) > float(s200_min))
        result.watch_flags["W5"] = bool(min_ok and s200_pref == s200_pref and not pref_ok)
        if result.watch_flags["W5"]:
            result.watch_notes["W5"] = (f"200-day {float(s200_now):.2f} vs {s200_pref:.2f} "
                                        f"{SMA200_RISING_PREF_BARS} sessions ago — rising for "
                                        f"at least {SMA200_RISING_BARS} but under the preferred "
                                        f"{SMA200_RISING_PREF_BARS}")
        ctx.extras["sma200_rising_pref"] = pref_ok if s200_pref == s200_pref else None

        ed = ctx.earnings_days_away
        result.watch_flags["W4"] = bool(ed is not None and 0 <= ed <= EARNINGS_BLACKOUT_DAYS)
        if result.watch_flags["W4"]:
            result.watch_notes["W4"] = f"earnings in {ed} days"

        depths = base.get("depths") or []
        if ch is not None:
            e.update(cheat_pivot=ch["cheat_pivot"], cheat_low=ch["cheat_low"],
                     cheat_zone=ch["cheat_zone"], cheat_pos=ch["cheat_pos"],
                     cheat_range_pct=ch["cheat_range_pct"], base_low=ch.get("base_low"))
        e.update(
            pivot=base["pivot"], tight_low=base["tight_low"], base_high=base["bh"],
            base_date=str(base["bh_date"].date()) if base["bh_date"] is not None else None,
            base_days=base["base_days"], contractions=len(depths),
            first_depth_pct=depths[0] if depths else None, last_depth_pct=depths[-1] if depths else None,
            base_depth_pct=base.get("base_depth_pct"),
            tightness_pct=base["tight_range_pct"], dryup_ratio=base["dryup"],
            breakout_volume_ratio=vol_ratio if breakout else None,
            vcp_fail=base["fail"], breakout=breakout,
        )
        # display only: what the pass/fail hides about this base (base_diagnostics)
        diag = base_diagnostics(base, d)
        e.update(diag, base_notes=base_notes(base, diag))
        result.recompute_first_fail()
        return result

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """MV-01 is bought at the next open, MV-02 by a resting buy-stop: both place an order today."""
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        if result.setups.get(MV01):
            return 2.0
        if result.setups.get(MV02):
            return 1.0
        # a cheat is a lower-confidence entry than the pivot buy, and the low cheat
        # lower than the 3C -- he describes it as the riskiest of the three
        if result.setups.get(FLAT):
            return 1.0
        return 0.8 if result.setups.get(MV04) else (0.6 if result.setups.get(MV03) else 0.0)

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        cheat = result.setups.get(MV03) or result.setups.get(MV04)
        power = result.setups.get(MV05)
        flat = result.setups.get(FLAT) and not (result.setups.get(MV01) or result.setups.get(MV02))
        if flat:
            # S6: the pivot is the base's own high, the stop under the low of the sessions before the
            # breakout, and the objective the base's depth added to the price paid
            fp, fl, fd = e.get("flat_pivot"), e.get("flat_low"), e.get("flat_depth_pct")
            if not fp or fl is None or pd.isna(fl):
                return PlanChoice(None, None, "missing flat-base pivot")
            cheat = power = False
        # A power play has no base, so its pivot and stop come from the FLAG, not from
        # e["pivot"]/e["tight_low"] -- which are None for it, since the base path rejected it.
        pivot, tl = ((e.get("pp_pivot"), e.get("pp_tight_low")) if power
                     else (e.get("pivot"), e.get("tight_low")))
        # Only the pivot buy needs the FINAL tight area. A cheat is taken while the
        # base is still forming, so that area does not exist yet -- requiring it here
        # rejected 122 of 133 cheats before they reached their own branch.
        if not cheat and not flat and (not pivot or tl is None or pd.isna(tl)):
            return PlanChoice(None, None, "missing pivot / tight low")
        if flat:
            setup, pivot = FLAT, float(fp)
            entry = float(ctx.close)              # confirmed by the close, bought at the next open
            stop = pivot_stop(fl, cfg.tick_size)
        elif cheat and not power:
            # A cheat is bought at its shelf, not the base's pivot, and stopped under
            # the SHELF low. That nearby stop is the entire point of the entry: the
            # base low is far away mid-base, and risking down to it would make the
            # trade worse than the pivot buy rather than better.
            setup = MV03 if result.setups.get(MV03) else MV04
            cp, cl = e.get("cheat_pivot"), e.get("cheat_low")
            if not cp or cl is None or pd.isna(cl):
                return PlanChoice(None, None, "missing cheat shelf")
            pivot = float(cp)
            entry = float(ctx.close)          # confirmed by the close, as EN-02 is since v1.1
            stop = pivot_stop(cl, cfg.tick_size)
        elif power:
            # MV-05 is confirmed on the close like MV-01, and stopped under the flag's tight low.
            setup = MV05
            entry = float(ctx.close)
            stop = pivot_stop(tl, cfg.tick_size)
        else:
            setup = MV01 if result.setups.get(MV01) else MV02
            # MV-01 fills at tomorrow's open, whose best estimate today is the close; MV-02 at the buy-stop
            entry = float(ctx.close) if setup == MV01 else pivot_buy_stop(pivot, cfg.tick_size)
            stop = pivot_stop(tl, cfg.tick_size)
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        # Reward has to come from the CHART, not from the risk. `entry + 3 * risk`
        # restates the formula and reports an R the setup does not offer -- the same
        # trap breakout.py documents. The measured move of a VCP is its own depth:
        # the base high less its deepest low (vcp_measured_move). It is taken only once
        # the base reached the contraction step (first_depth_pct is set).
        bh, first_depth = e.get("base_high"), e.get("first_depth_pct")
        depth = e.get("base_depth_pct") if first_depth is not None else None
        if flat:
            measured_move = float(fp) * float(fd) / 100 if fd is not None else float("nan")
        elif power:
            # No base, so no base-depth measured move. The flag's own range is the only structure
            # the setup offers; beyond that any number would be the risk formula wearing a chart's
            # clothes, which is the trap the comment below describes.
            measured_move = (pivot - tl) if (pivot and tl is not None) else float("nan")
        elif cheat and bh:
            # A cheat is bought below the old high, so the nearest objective is that
            # high; the base's own measured move is projected from there. first_depth
            # is absent when the base never reached the contraction step, in which
            # case the old high alone is the objective.
            measured_move = cheat_measured_move(bh, entry, depth)
        else:
            measured_move = vcp_measured_move(bh, depth)
        target = entry + measured_move if measured_move == measured_move else entry + risk
        # Overhead supply caps the move — but measured from the BASE HIGH, not from
        # entry. The pivot sits below the base high by construction (VCP-09 only
        # requires it within 90%), so everything between them is the consolidation
        # being resolved, not external resistance. Capping at entry made the base's
        # OWN high the ceiling and crushed every projection: TITAN's 2017 setup, a
        # base the strategy actually traded, scored 0.84R instead of 2.28R.
        # ... but `> base_high` is not enough on its own: the levels a hair above
        # the base high ARE the base high, so the cap still landed on the base's
        # own structure. Measured over the 15 India v2.3 breakouts, 8 were capped
        # within 1.5% of their own base high (GODREJPROP at 1697.85 against a
        # 1697.85 base high, THERMAX at 5699.95 against 5699.95), which dropped
        # the median projection from 1.81R to 0.90R and rejected them for an
        # artefact of the base's own definition. Only supply at least
        # OVERHEAD_CLUSTER_ATR above the base high can cap the move.
        ceiling_from = max(entry, float(bh)) if bh else entry
        cluster_edge = ceiling_from + OVERHEAD_CLUSTER_ATR * ctx.atr
        nearest_above = sw.nearest_overhead_above(ceiling_from, ctx.overhead)  # reported, not binding
        binding = min((lvl for lvl in ctx.overhead if lvl >= cluster_edge), default=None)
        if binding is not None and binding < target:
            target = binding
        ctx.extras["overhead_caps_target"] = bool(binding is not None and binding < entry + measured_move) \
            if measured_move == measured_move else None
        structural_r = (target - entry) / risk if risk > 0 else float("nan")
        ctx.extras["structural_r"] = round(structural_r, 2) if structural_r == structural_r else None
        ctx.extras["measured_move"] = round(measured_move, 2) if measured_move == measured_move else None

        # Minervini's stated hard rule: a minimum reward-to-risk of 2:1, ideally 3:1.
        # "If the stock's realistic upside isn't at least twice the distance to your
        # stop, the trade isn't worth taking even if everything else lines up."
        # Rejected here rather than padded up to look acceptable.
        if not (structural_r >= MIN_STRUCTURAL_R):
            return PlanChoice(
                None, None,
                f"projects only {structural_r:.2f}R against the {MIN_STRUCTURAL_R:g}:1 minimum",
            )

        plan = TradePlan(plan="MV", setup=setup, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry,
                         r_multiple=round(structural_r, 2),
                         nearest_overhead_above_entry=nearest_above)
        return PlanChoice(plan, None,
                          f"{setup}: pivot {pivot:.2f}, stop {(entry - stop) / entry * 100:.1f}% "
                          f"below entry, projects {structural_r:.2f}R")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """How the portfolio simulator should place and manage this order (portfolio_sim docstring)."""
        e = ctx.extras
        # A cheat has no FINAL tight area -- its base is still forming -- so its
        # levels are the shelf's. Reading e["pivot"] unconditionally here is the
        # same mistake build_plans made, and it crashed the run rather than
        # degrading, because the cheat path never set those keys.
        if plan.setup in (MV03, MV04):
            pivot, tl = float(e["cheat_pivot"]), float(e["cheat_low"])
        elif plan.setup == MV05:
            pivot, tl = float(e["pp_pivot"]), float(e["pp_tight_low"])
        elif plan.setup == FLAT:
            pivot, tl = float(e["flat_pivot"]), float(e["flat_low"])
        else:
            pivot, tl = float(e["pivot"]), float(e["tight_low"])
        # EN-04 ("one entry per base") keys on `base_id`, and a power play has no base -- so
        # without an id of its own it would be the one setup that could be re-entered on the same
        # structure after a stop-out, which is exactly what EN-04 exists to stop. The flag high's
        # date identifies the flag the way the base start identifies a base.
        base_id = (e.get("pp_flag_high_date") if plan.setup == MV05
                   else e.get("flat_base_date") if plan.setup == FLAT else e.get("base_date"))
        meta = {"pivot": pivot, "tight_low": tl, "max_fill": pivot * (1 + BUY_RANGE_PCT / 100),
                "max_risk_pct": MAX_STOP_PCT / 100, "base_id": base_id,
                "max_entries_per_base": MAX_ENTRIES_PER_BASE,
                "min_structural_r": MIN_STRUCTURAL_R,
                "tightness": e.get("tightness_pct")}
        if plan.setup == MV01:
            meta.update(order="open", min_open=tl)
        elif plan.setup == MV02:
            meta.update(order="stop", cancel_close_below=tl, confirm_close_above=pivot)
            if LIGHT_VOLUME_EXIT:
                # the guide's buy-stop is valid only if the breakout day's volume reaches
                # VOL_MULT x the 50-day average by the close (portfolio_sim, entry day)
                meta["min_breakout_vol"] = VOL_MULT
        else:
            # the shelf was cleared on today's close, so the fill is the next open,
            # as MV-01 does; cancel if it closes back under the shelf low
            meta.update(order="open", min_open=tl)
        return meta

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        q = self.setup_quality(result)
        if not result.hard_gates_passed:
            return Decision(LABELS["AVOID"], LABELS["AVOID"],
                            f"fails trend template gate {result.first_hard_fail}: {result.hard_notes.get(result.first_hard_fail, '')}",
                            0.0, 0.0, q)
        if plan is None or not plan.is_valid:
            return Decision(LABELS["AVOID"], LABELS["AVOID"], "no valid entry plan", 0.0, 0.0, q)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if plan.setup == MV01:
            label, reasons = "TRADE_HIGH_CONFIDENCE", ["confirmed breakout: buy at the next open"]
        elif plan.setup == MV02:
            label, reasons = "TRADE_ON_TRIGGER", ["coiled below the pivot: buy-stop through it"]
        elif plan.setup == FLAT:
            label, reasons = "TRADE_ON_TRIGGER", ["flat base: closed through the base's high, buy at the "
                                                  "next open, stopped under the low of the sessions before"]
        elif plan.setup == MV05:
            # not a cheat: no base, no shelf -- it closed through the flag's pivot, like MV-01
            label, reasons = "TRADE_ON_TRIGGER", ["power play: closed through the flag's pivot, buy at the "
                                                  "next open, stopped under the flag's tight low"]
        else:
            # a cheat is neither coiled nor a buy-stop: it cleared its shelf on the close
            where = "lower" if plan.setup == MV03 else "middle"
            label = "TRADE_ON_TRIGGER"
            reasons = [f"cheat: cleared a shelf in the {where} third of the base, "
                       f"stopped under the shelf low"]
        if risk_pct > MAX_STOP_PCT:
            label = "WATCH_WAIT"
            reasons.append(f"stop {risk_pct:.1f}% below entry exceeds the {MAX_STOP_PCT:g}% maximum")
        if earnings_days_away is not None and 0 <= earnings_days_away <= EARNINGS_BLACKOUT_DAYS:
            label = "WATCH_WAIT"
            reasons.append(f"results due in {earnings_days_away} days: no new buy within {EARNINGS_BLACKOUT_DAYS}")
        if SMA200_PREF_REQUIRED and result.watch_flags.get("W5"):
            label = "WATCH_WAIT"
            reasons.append(f"200-day rising for under {SMA200_RISING_PREF_BARS} sessions: no new buy")
        label_before = label
        if regime_downgrade_active and label in ("TRADE_HIGH_CONFIDENCE", "TRADE_ON_TRIGGER"):
            label = "WATCH_WAIT"
            reasons.append("market filter: no new buys")
        return Decision(LABELS[label_before], LABELS[label], "; ".join(reasons), risk_pct, plan.r_multiple, q)

    def watch_cap(self, result: StrategyResult) -> str:
        return "TRADE_HIGH_CONFIDENCE"

    def report_extras(self, ctx, result, plan) -> dict:
        e = ctx.extras
        pivot = e.get("pivot")

        def r(k, n=2):
            v = e.get(k)
            return round(float(v), n) if v is not None and pd.notna(v) else None
        return {
            "pivot": r("pivot"), "tight_low": r("tight_low"),
            "pct_from_pivot": round((ctx.close / pivot - 1) * 100, 2) if pivot else None,
            "base_high": r("base_high"), "base_days": e.get("base_days"), "contractions": e.get("contractions"),
            "first_depth_pct": r("first_depth_pct", 1), "last_depth_pct": r("last_depth_pct", 1),
            "tightness_pct": r("tightness_pct", 1), "dryup_ratio": r("dryup_ratio"),
            "breakout_volume_ratio": r("breakout_volume_ratio"), "vcp_fail": e.get("vcp_fail"),
            "rs_score": r("rs_score", 3), "cheat_withheld": e.get("cheat_withheld"),
            "base_notes": e.get("base_notes") or None, "base_reference": e.get("base_reference"),
            "pivot_route": e.get("pivot_route"), "pivot_pos": e.get("pivot_pos"),
            "dryup_quiet_days": e.get("dryup_quiet_days"), "closes_below_200": e.get("closes_below_200"),
            "below_200_share_pct": e.get("below_200_share_pct"), "undercuts": e.get("undercuts"),
            "undercuts_failed": e.get("undercuts_failed"), "undercuts_pending": e.get("undercuts_pending"),
            "bh_atr_pct": e.get("bh_atr_pct"), "atr_blocks_base": e.get("atr_blocks_base"),
        }


    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The base box the VCP was anchored to, its pivot and tight-area low, and a note saying
        how the base was identified — all from the signal's own cached extras (see base.py)."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        bh, bd, tl = e.get("base_high"), e.get("base_date"), e.get("tight_low")
        if bh and bd:
            depths = (f"{e['first_depth_pct']:g}% → {e['last_depth_pct']:g}%"
                      if e.get("first_depth_pct") is not None and e.get("last_depth_pct") is not None else "?")
            out.append({"shape": "box", "from": str(bd), "to": d, "top": float(bh),
                        "bottom": float(tl) if tl else float(bh) * (1 - (e.get("first_depth_pct") or 10) / 100),
                        "role": "base", "label": f"base {e.get('base_days', '?')}d · {e.get('contractions', '?')}c {depths}"})
            note = (f"Base: from the high on {bd}, its highest {bh:g}, {e.get('base_days', '?')} sessions. "
                    f"{e.get('contractions', '?')} contractions {depths} (the reset rule needs "
                    f"{MIN_FROM_REFERENCE} since the last widening, the final ≤ {FINAL_REF_RATIO:g}× it). ")
            if e.get("tightness_pct") is not None:
                note += f"Final tight area {e['tightness_pct']:g}% deep"
                note += f", volume {e['dryup_ratio']:g}× the 50-day average (dry-up). " if e.get("dryup_ratio") is not None else ". "
            if e.get("cheat_pivot") and e.get("cheat_zone"):
                out.append({"shape": "box", "bars": CHEAT_SHELF_DAYS, "to": d,
                            "top": float(e["cheat_pivot"]), "bottom": float(e["cheat_low"]),
                            "role": "base", "dash": True,
                            "label": f"cheat shelf · {e['cheat_zone']} third of the base"})
                note += (f"Cheat shelf {e['cheat_low']:g}-{e['cheat_pivot']:g} in the "
                         f"{e['cheat_zone']} third of the base; bought on the close through its "
                         f"high, stopped under its low. ")
            note += (f"VCP rejected: {e['vcp_fail']}." if e.get("vcp_fail")
                     else f"Pivot {e['pivot']:g} — the final contraction's high; a buy-stop goes just above it." if e.get("pivot") else "")
            out.append({"shape": "note", "at": d, "price": float(bh), "text": note})
        if e.get("pivot"):
            out.append({"shape": "level", "from": str(bd) if bd else None, "bars": None if bd else 40, "to": d,
                        "price": float(e["pivot"]), "role": "pivot", "label": f"pivot {e['pivot']:g}"})
        if tl:
            out.append({"shape": "level", "from": str(bd) if bd else None, "bars": None if bd else 40, "to": d,
                        "price": float(tl), "role": "support", "label": f"tight-area low {tl:g} — the stop's anchor"})
        return out or super().chart_anatomy(sig)

    # how far a base got through VCP-03 … VCP-11 (a completed VCP outranks every failure)
    _VCP_RANK = {"VCP-03": 3, "VCP-04": 4, "VCP-05": 5, "VCP-06": 6, "VCP-07": 7, "VCP-08": 8, "VCP-09": 9, "VCP-10": 10, "VCP-11": 11}

    def bases_live(self, daily: pd.DataFrame, cfg: MarketConfig, anchors: list[dict] | None = None) -> list[dict]:
        """Every VCP setup the detector saw over `daily`, for the chart's Trend template indicator:
        `vcp_spec.detect` with this strategy's VCP params, run ON DEMAND bar by bar (each bar sees only
        itself and earlier bars, as in the backtest). Exploration only: what a run traded comes from
        its stored signals (trade-anatomy), since current code may detect differently.

        A base is kept once some bar passed VCP-01 and VCP-02 (a real advance into it, a base of legal
        age); one the trend rule (VCP-03) then rejects is still drawn, as a failed setup saying why.
        Each is drawn from its most developed bar: the bar before the breakout when the VCP completed
        and broke out, else the last bar it was complete, else the bar that got furthest through
        VCP-04 … VCP-11 — except the base still in force on the last bar, which is judged on that bar
        (as today's screen judges it). A base that triggered a cheat entry (MV-03 / MV-04, `cheat_cross`)
        carries its latest one. Returns one dict per setup (see `_setup`).

        `anchors`: a selected backtest run's trades, each {"entry": fill date, "stop": initial stop}. A base
        whose cheat entry the run bought -- a cheat crossed on the bar before the fill, else the base's first
        cheat when it is the closest of its events before the fill, within 21 days -- is drawn as that cheat, judged on the base as it stood the bar before,
        not as a later breakout the run never took."""
        start = 2 * VCP.swing_k + VCP.prior_window
        dets = [None] * len(daily)
        for i in range(start, len(daily)):
            dets[i] = vcp_spec.detect(daily.iloc[: i + 1], VCP)
        close = daily["close"].to_numpy(float)
        bases: dict = {}
        for i in range(start, len(daily)):
            r = dets[i]
            if r["bh_date"] is None or not (r["ok"] or r["fail"] in self._VCP_RANK):
                continue
            b = bases.setdefault(r["bh_date"], {"best": i, "ok": [], "breakout": None, "cheat": None})
            if r["ok"]:
                b["ok"].append(i)
            rank = 99 if r["ok"] else self._VCP_RANK[r["fail"]]
            best = dets[b["best"]]
            if rank >= (99 if best["ok"] else self._VCP_RANK[best["fail"]]):
                b["best"] = i
        # MV-01's breakout: yesterday complete, and today's close through yesterday's frozen pivot.
        # The breakout bar itself may already sit in a new base (the decisive close resets BH), so
        # it is found from the bar before it.
        for i in range(start + 1, len(daily)):
            p = dets[i - 1]
            if p and p["ok"] and close[i - 1] <= p["pivot"] < close[i] and p["bh_date"] in bases \
                    and bases[p["bh_date"]]["breakout"] is None:
                bases[p["bh_date"]]["breakout"] = i
        # MV-03 / MV-04: the FIRST cheat each base triggered, by the strategy's own test.
        #
        # First, not latest. A base often crosses a shelf more than once -- the shelf is re-measured
        # every bar, so each new high gives a new level for a later close to clear -- but EN-04
        # allows one entry per base, so the strategy acts on the first and ignores the rest.
        # Drawing the last one illustrated a trade that never happened and, because its shelf is
        # higher, a worse reward-to-risk: on NAM-INDIA.NS the base crossed on 2024-05-17 (shelf
        # high 588.90, close 593.35, 2.26R -- the trade the run actually took) and again on
        # 2024-05-21 (shelf high 595.50, close 599.80, 1.82R), and the drawing showed the second,
        # which fails the 2R test and so was labelled "trade skipped" beside a trade that was
        # taken.
        for i in range(start + 1, len(daily)):
            p = dets[i - 1]
            if p and p["bh_date"] in bases and bases[p["bh_date"]].get("cheat") is None:
                z = cheat_cross(p, close[i - 1], close[i])
                if z:
                    bases[p["bh_date"]]["cheat"] = (i, z, p)
        last = len(daily) - 1
        live = dets[last]["bh_date"] if last >= start and dets[last]["bh_date"] in bases else None
        fills = [pd.Timestamp(a["entry"]) for a in (anchors or []) if a.get("entry")]
        ts = lambda i: daily.index[i]  # noqa: E731
        # The cheat a run bought is the one crossed on the bar before its fill (signal on the close, bought
        # the next session) -- by the same cheat_cross test, so it can be a later shelf than the base's
        # first: when the first cross was not entered (no slot, refused), EN-04's one entry per base is
        # still unspent, and the run takes a later one.
        signalled: dict = {}
        for f in fills:
            j = int(daily.index.searchsorted(f)) - 1
            p = dets[j - 1] if j - 1 >= start else None
            if p and p["bh_date"] in bases:
                z = cheat_cross(p, close[j - 1], close[j])
                if z:
                    signalled[p["bh_date"]] = (j, z, p)

        def traded_cheat(ch, bo) -> bool:
            """Did a fill come within 21 days after the cheat's cross, with no breakout nearer to it?"""
            for f in fills:
                if ts(ch[0]) < f <= ts(ch[0]) + pd.Timedelta(days=21) and not (bo is not None and ts(ch[0]) < ts(bo) < f):
                    return True
            return False
        out = []
        for key, b in bases.items():
            bo = b["breakout"]
            ch = signalled.get(key) or b["cheat"]
            if ch and fills and (key in signalled or traded_cheat(ch, bo)):
                # the run bought the cheat: draw that trade, from the base as it stood the bar before the cross
                out.append(self._setup(daily, cfg, dets[ch[0] - 1], ch[0] - 1, None, ch, False, traded_cheat=True))
                out[-1]["anchored"] = True
                continue
            now = key == live and bo is None   # still forming today: judge it as today's screen does
            rep = last if now else bo - 1 if bo is not None else b["ok"][-1] if b["ok"] else b["best"]
            out.append(self._setup(daily, cfg, dets[rep], rep, bo, b["cheat"], now))
        return out

    # the VCP rules in the order the detector applies them, the zone of the setup each belongs to,
    # and the name the chart's checklist gives it
    _VCP_CHECKS = (("VCP-01", "uptrend", "Prior uptrend"), ("VCP-03", "uptrend", "Trend intact"),
                   ("VCP-02", "base", "Base length"), ("VCP-05", "base", "Base depth"),
                   ("VCP-04", "base", "Pullbacks"), ("VCP-06", "base", "Pullbacks shrink"),
                   ("VCP-08", "base", "Tight area"), ("VCP-09", "base", "Pivot near high"),
                   ("VCP-10", "base", "Volume dry-up"))
    # the order core/vcp_spec.detect runs them in: a rule after the failing one was never measured, so it
    # must show "not reached" -- with VCP-04 listed before VCP-05 a depth failure showed the pullback
    # count as passed although it was never counted
    _VCP_ORDER = ("VCP-02", "VCP-01", "VCP-03", "VCP-05", "VCP-04", "VCP-06", "VCP-08", "VCP-09", "VCP-10")
    # what a failed rule means, short enough for the setup's header
    _VCP_FAILED = VCP_RULES

    # a correction inside the uptrend deeper than this is flagged on the chart (display only: it decides
    # nothing, and the leading underscore keeps it out of the strategy's fingerprint)
    _UPTREND_FLAG_PCT = 10.0

    def _live_withholds(self, p: dict | None) -> bool:
        """Would the screen's rules withhold a cheat whose base (as detected the bar before it) is `p`?
        The same test as `evaluate` -- read from the module constant, or from the live variant when the
        screen applies one that this process (the chart's) has not."""
        lv = (type(self).live_variant or {}).get("const", {})
        return bool((CHEAT_BLOCK_VCP09 or lv.get("CHEAT_BLOCK_VCP09")) and p and p.get("fail") == "VCP-09")

    def _setup(self, daily: pd.DataFrame, cfg: MarketConfig, r: dict, rep: int, bo: int | None,
               cheat: tuple | None = None, live: bool = False, traded_cheat: bool = False) -> dict:
        """One setup for the chart: a frame around it, and its zones — the uptrend into the base, the
        base and its contractions, the pivot entry of a completed VCP, and the latest cheat entry
        (`cheat`: (bar, MV03 | MV04, yesterday's detection)) — each with its own shapes, its checklist
        rows and a writeup. The entry zones ILLUSTRATE where this strategy's own rules place the trade
        (pivot_buy_stop, pivot_stop, vcp_measured_move, cheat_measured_move, the exit constants); they
        are not backtest results, and the chart replaces them with a run's stored trade when one is
        selected. `live`: the base is still forming, judged on the last bar. `traded_cheat`: a run bought
        `cheat` -- drawn as that cheat even when the base was already a complete VCP, without the pivot
        entry the run never took (EN-04: one entry per base).

        Returns {"from", "base_from", "to", "kind" (vcp | cheat | young | fail), "complete", "fail", "breakout",
        "live", "as_of", "title", "summary", "frame": {from, to, top, bottom}, "zones": [{key, title,
        state, warn?, from, to, line, text, checks, shapes}]}; shapes in the chart_anatomy schema."""
        day = lambda i: str(daily.index[i].date())
        iso = lambda ts: str(pd.Timestamp(ts).date())
        px = lambda v: f"{v:,.2f}" if v >= 1 else f"{v:.4g}"   # a price as the chart's scale shows it
        bh, bd, at = float(r["bh"]), iso(r["bh_date"]), day(rep)
        bh_i = daily.index.get_loc(r["bh_date"])
        end = bo if bo is not None else rep
        base_low = float(daily["low"].iloc[bh_i: rep + 1].min())
        depths, legs, fail, done = r["depths"], r["legs"], r["fail"], bool(r["ok"])
        # A young listing fails VCP-03 only because its averages cannot be computed yet — not a broken
        # trend, and it must not read like one. `ready` is the first bar the template can be judged.
        young = fail == "VCP-03" and not r["base_tt"] and vcp_spec.template_miss(daily.iloc[bh_i]) == vcp_spec.NO_HISTORY
        if young:
            avail = daily[["sma200_21d_ago", "low_252", "high_252"]].notna().all(axis=1)
            ready = avail.idxmax() if avail.any() else None
            ready_txt = (f"it can first be judged on {iso(ready)}, bar {daily.index.get_loc(ready) + 1} of its history"
                         if ready is not None else "it cannot be judged yet")
            young_why = (f"the trend template needs a rising 200-day average, and the base high "
                         f"on {bd} was only bar {bh_i + 1} of the stock's history; {ready_txt}")
        stop_at = self._VCP_ORDER.index(fail) if fail in self._VCP_ORDER else len(self._VCP_ORDER)
        state = lambda code: "pass" if self._VCP_ORDER.index(code) < stop_at else \
            ("young" if young else "fail") if self._VCP_ORDER.index(code) == stop_at else "skip"

        # ---- the checklist rows (a rule after the failing one was never measured: the detector stops there)
        up_days = bh_i - int(daily.index.get_loc(r["prior_low_date"])) if r["prior_low"] else None
        # one decimal, or two where one would hide which side of its limit a value falls (6.88% against
        # a 6.888% limit reads "6.9", which looks like a failure)
        g = base_diagnostics(r, daily)
        near = lambda v, lim: abs(v - lim) < 0.1
        pct = lambda v, lim: f"{v:.2f}" if near(v, lim) else f"{v:.1f}"
        fine = bool(depths) and any(near(b, FINAL_REF_RATIO * a) for a, b in zip(depths, depths[1:]))
        dep = lambda x: f"{x:.2f}" if fine else f"{x:.1f}"
        values = {
            "VCP-01": (f"+{pct(r['prior_advance_pct'], PRIOR_ADVANCE_PCT) if near(r['prior_advance_pct'], PRIOR_ADVANCE_PCT) else format(r['prior_advance_pct'], '.0f')}% in {up_days} days" if up_days is not None else "—",
                       f"at least {PRIOR_ADVANCE_PCT:g}% within {VCP.prior_window} days"),
            "VCP-02": (f"{r['base_days']} days", f"{BASE_MIN_DAYS}–{BASE_MAX_DAYS} days"),
            "VCP-03": ((f"held · {g['closes_below_200']} closes under the 200-day ({g['below_200_share_pct']:g}% of the base)"
                        if g["closes_below_200"] is not None else "held") if fail != "VCP-03"
                       else f"too new: bar {bh_i + 1}" if young else self._vcp_fail_why(r, daily, bh_i, rep),
                       f"the 200-day no lower than at the high, the 150-day above it, at most "
                       f"{MAX_CLOSES_BELOW_200} closes under it"),
            "VCP-04": (f"{len(depths)}" if depths else "—", f"at least {MIN_CONTRACTIONS}"),
            "VCP-05": (f"{r['base_depth_pct']:.1f}% deep" if r.get("base_depth_pct") is not None else "—",
                       f"at most {MAX_BASE_DEPTH_PCT:g}% (over {DEEP_BASE_FLAG_PCT:g}% is flagged)"),
            "VCP-06": (" → ".join(dep(x) for x in depths) + "%"
                       + (f" · {g['base_reference']}" if g["base_reference"] else "") if depths else "—",
                       f"{MIN_FROM_REFERENCE} since the last widening, final ≤ {FINAL_REF_RATIO:g}× it"),
            "VCP-08": (f"{pct(r['tight_range_pct'], TIGHT_PCT)}%" if r["tight_range_pct"] is not None else "—", f"at most {TIGHT_PCT:g}%"),
            "VCP-09": ((f"{g['pivot_pos']:.2f} up the base, " + (f"{(1 - r['pivot'] / bh) * 100:.1f}% under the high"
                                                                 if r["pivot"] <= bh else
                                                                 f"{(r['pivot'] / bh - 1) * 100:.1f}% above the high")
                        + (f" · passes by {g['pivot_route']}" if g["pivot_route"] not in (None, "neither") else ""))
                       if r["pivot"] and g["pivot_pos"] is not None
                       else f"{(1 - r['pivot'] / bh) * 100:.1f}% under" if r["pivot"] else "—",
                       f"upper zone ({UPPER_ZONE:.2f}) or within {(1 - PIVOT_NEAR_HIGH) * 100:.0f}% of the high"),
            "VCP-10": (f"{r['dryup']:.2f}× normal · {g['dryup_quiet_days']} quiet day{'' if g['dryup_quiet_days'] == 1 else 's'}"
                       if r["dryup"] is not None else "—",
                       f"at most {DRYUP_RATIO:g}×, or {DRYUP_QUIET_DAYS} days at {DRYUP_QUIET_RATIO:g}× or less"),
        }
        checks = {z: [] for z in ("uptrend", "base", "entry")}
        for code, zone, name in self._VCP_CHECKS:
            checks[zone].append({"code": code, "name": name, "value": values[code][0], "limit": values[code][1],
                                 "state": state(code)})
        # notes beside the checks: recorded, never a rejection (base_diagnostics)
        if g["undercuts"]:
            st = [f"{n} {w}" for n, w in ((g["undercuts_failed"], "failed"), (g["undercuts_pending"], "pending")) if n]
            checks["base"].append({"code": "note", "name": "Undercuts",
                                   "value": f"{g['undercuts']}" + (f" ({', '.join(st)})" if st else ", recovered"),
                                   "limit": f"a low under an earlier one, reclaimed within {UNDERCUT_RECOVERY_DAYS} sessions",
                                   "state": "warn" if g["undercuts_failed"] else "pass"})
        if g["bh_atr_pct"] is not None:
            floor = max(VCP.zigzag_floor_pct, VCP.zigzag_floor_atr_mult * g["bh_atr_pct"])
            checks["base"].append({"code": "note", "name": "ATR at the high",
                                   "value": f"{g['bh_atr_pct']:.1f}% · pullbacks count from {floor:.1f}%"
                                            + (" — too volatile to complete" if g["atr_blocks_base"] else ""),
                                   "limit": f"a last pullback must be deep enough to count and at most {TIGHT_PCT:g}%",
                                   "state": "warn" if g["atr_blocks_base"] else "pass"})
        # a zone passes only when every rule in it passed; one with rules never reached is "skip"
        # (the "note" rows are diagnostics, not rules: they never decide a zone)
        rules_in = lambda z: [c for c in checks[z] if c["code"] != "note"]
        zstate = lambda z: "fail" if any(c["state"] == "fail" for c in rules_in(z)) else \
            "young" if any(c["state"] == "young" for c in rules_in(z)) else \
            "pass" if all(c["state"] == "pass" for c in rules_in(z)) else "skip"
        zones = []

        # ---- zone 1: the uptrend into the base
        if r["prior_low"]:
            pl, pd_ = float(r["prior_low"]), iso(r["prior_low_date"])
            up_from = pd_
            trend = ("The trend template held on the high's bar, and the 150/200-day structure held through the base."
                     if fail != "VCP-03" else f"But it is too new to judge the trend: {young_why}." if young
                     else f"But the trend was not intact: {self._vcp_fail_why(r, daily, bh_i, rep)}.")
            up_shapes = [{"shape": "line", "from": pd_, "to": bd, "p0": pl, "p1": bh, "role": "uptrend",
                          "arrow": True, "label": f"+{r['prior_advance_pct']:.0f}%"}]
            up_checks, flag, warn, line = list(checks["uptrend"]), "", False, f"+{r['prior_advance_pct']:.0f}% in {up_days} days"
            # VCP-01 measures from the window's lowest low, so a deep correction INSIDE the advance passes
            # unseen: the arrow would draw straight through it. Flag it, and say what the run from it was.
            seg = daily.iloc[daily.index.get_loc(r["prior_low_date"]): bh_i + 1]
            peak = seg["high"].cummax()
            dd = (peak - seg["low"]) / peak * 100
            if len(dd) and float(dd.max()) > self._UPTREND_FLAG_PCT:
                k = int(dd.to_numpy().argmax())
                c_low, c_day = float(seg["low"].iloc[k]), seg.index[k]
                c_peak = float(peak.iloc[k]); c_peak_day = seg["high"].iloc[: k + 1].idxmax()
                since = (bh / c_low - 1) * 100
                warn = True
                line += f" · {dd.max():.0f}% dip inside"
                flag = (f" Note: this advance includes a {dd.max():.1f}% correction, from {px(c_peak)} on "
                        f"{iso(c_peak_day)} to {px(c_low)} on {iso(c_day)}. The rule measures from the lowest low "
                        f"in the window, so it counts the whole move; the run from that correction low into the "
                        f"base is +{since:.1f}%" + (f", under the {PRIOR_ADVANCE_PCT:g}% minimum." if since < PRIOR_ADVANCE_PCT else "."))
                up_shapes.append({"shape": "dots", "role": "flag",
                                  "points": [{"at": iso(c_day), "price": c_low, "label": f"−{dd.max():.0f}% dip"}]})
                up_checks.append({"code": "note", "name": "Dip inside", "value": f"{dd.max():.1f}%, then +{since:.1f}%",
                                  "limit": f"flagged above {self._UPTREND_FLAG_PCT:g}%", "state": "warn"})
            zones.append({"key": "uptrend", "title": "Uptrend", "state": zstate("uptrend"), "warn": warn, "from": pd_, "to": bd,
                          "line": line,
                          "text": (f"The stock rose {r['prior_advance_pct']:.0f}%, from {px(pl)} on {pd_} to {px(bh)} on {bd}, "
                                   f"in {up_days} sessions. A base only matters after a strong advance: at least "
                                   f"{PRIOR_ADVANCE_PCT:g}% within {VCP.prior_window} sessions. {trend}{flag}"),
                          "checks": up_checks, "shapes": up_shapes})
        else:
            up_from = bd

        # ---- zone 2: the base and its contractions
        culprit = None   # the pullback a VCP-05 / VCP-06 failure is about
        if fail == "VCP-05":
            culprit = 0
        elif fail == "VCP-06":
            # the reference the reset rule judged against -- the most recent widening
            culprit = 0
            for k in range(1, len(depths)):
                if depths[k - 1] > 0 and depths[k] > WIDEN_TOL * depths[k - 1]:
                    culprit = k
        # Drawn the way the Learn guide draws a VCP: the candles stay clear. No shading over the base and
        # no zig-zag joining the swings -- both covered the very bars a reader is judging. Each pullback is
        # a marker at its low, named T1, T2 … with its depth (✗ on the one a VCP-05 / VCP-06 failure is
        # about), and the base's footprint ("7W 11/3 2T": weeks, deepest/final pullback, count) is the
        # zone's `tag`, which the chart writes into the zone's caption.
        base_shapes = []
        if legs:
            many = len(depths) > MAX_CONTRACTIONS   # every label would pile up: keep the telling ones
            keep = {0, len(depths) - 1, max(range(len(depths)), key=lambda k: depths[k])} if many and depths else None
            base_shapes.append({"shape": "dots", "role": "contraction", "points": [
                {"at": iso(ld), "price": float(low),
                 "label": (f"T{k + 1} −{depths[k]:.0f}%{' ✗' if k == culprit else ''}"
                           if k < len(depths) and (keep is None or k in keep) else "")}
                for k, (hd, h, ld, low) in enumerate(legs)]})
        tight = ""
        if r["tight_from"] is not None and r["pivot"]:
            tf, pv, tl = iso(r["tight_from"]), float(r["pivot"]), float(r["tight_low"])
            base_shapes.append({"shape": "box", "from": tf, "to": at, "top": pv, "bottom": tl, "role": "tight",
                                "label": ""})
            dry = (f", on volume {r['dryup']:.2f}× its 50-day average (at most {DRYUP_RATIO:g}×): sellers have dried up"
                   if r["dryup"] is not None else "")
            tight = (f" The last stretch is tight: {r['tight_range_pct']:.1f}% from {px(tl)} to {px(pv)} (at most "
                     f"{TIGHT_PCT:g}%){dry}. Its high, {px(pv)}, is the pivot.")
        pulls = (f" It pulled back {len(depths)} times: {' → '.join(dep(x) + '%' for x in depths)}. A VCP needs at "
                 f"least {MIN_CONTRACTIONS} pullbacks inside a base at most {MAX_BASE_DEPTH_PCT:g}% deep, and — since "
                 f"the last one that WIDENED — {MIN_FROM_REFERENCE} more, the last of them at most "
                 f"{FINAL_REF_RATIO:g}× that widening." if depths else "")
        verdict = "" if done or fail in (None, "VCP-03") else f" It failed here: {self._vcp_fail_why(r, daily, bh_i, rep)}."
        zones.append({"key": "base", "title": "Base", "tag": footprint(r["base_days"], depths),
                      "state": zstate("base"), "from": bd, "to": at,
                      "warn": any(c["code"] == "note" and c["state"] == "warn" for c in checks["base"]),
                      "line": f"{r['base_days']} days, {(1 - base_low / bh) * 100:.1f}% deep"
                              + (f", {len(depths)} pullbacks" if depths else ""),
                      "text": (f"{r['base_days']} sessions from the high on {bd}, highest {px(bh)} (a base lasts "
                               f"{BASE_MIN_DAYS}–{BASE_MAX_DAYS}), down to {px(base_low)} at its lowest.{pulls}{tight}{verdict}"),
                      "checks": checks["base"], "shapes": base_shapes})

        # ---- zone 3: the entry — illustrated from the strategy's own rules, for a completed VCP only
        top, bottom = bh, min(base_low, float(r["prior_low"]) if r["prior_low"] else base_low)
        entry_to = at
        if done and not traded_cheat:
            pv, tl = float(r["pivot"]), float(r["tight_low"])
            buy, stop = pivot_buy_stop(pv, cfg.tick_size), pivot_stop(tl, cfg.tick_size)
            risk = buy - stop
            mm = vcp_measured_move(bh, r.get("base_depth_pct") if depths else None)
            target = buy + mm if mm == mm else None
            r_mult = (target - buy) / risk if target and risk > 0 else None
            risk_pct = risk / buy * 100
            e_i = bo if bo is not None else rep
            entry_to = day(min(len(daily) - 1, e_i + TIME_STOP_DAYS))
            e_from = at
            # Short labels, and none on the +2R breakeven line: with a target near 2R the two lines sit on
            # top of each other, and four labels stacked in a narrow entry zone could not be read. The
            # risk, the R multiple and the breakeven rule are in the card's Entry zone.
            levels = [("buy", buy, f"Buy {px(buy)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", buy + BREAKEVEN_R * risk, "")]
            if target:
                levels.append(("target", target, f"Target {px(target)}"))
            shapes = [{"shape": "level", "from": e_from, "to": entry_to, "price": v, "role": role, "label": lab,
                       "dash": role != "buy"} for role, v, lab in levels]
            if bo is not None:
                c = float(daily["close"].iloc[bo])
                shapes.append({"shape": "dots", "points": [{"at": day(bo), "price": c, "label": "breakout"}], "role": "buy"})
            ok_risk, ok_r = risk_pct <= MAX_STOP_PCT, (r_mult or 0) >= MIN_STRUCTURAL_R
            e_checks = [
                {"code": "SL-03", "name": "Risk", "value": f"{risk_pct:.1f}%", "limit": f"at most {MAX_STOP_PCT:g}%",
                 "state": "pass" if ok_risk else "fail"},
                {"code": "R:R", "name": "Reward / risk", "value": _rr(r_mult, ok_r),
                 "limit": f"at least {MIN_STRUCTURAL_R:g}R", "state": "pass" if ok_r else "fail"},
            ]
            skip = [] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit"]
            if not ok_r:
                skip.append(f"it projects {_rr(r_mult, False)}, under the {MIN_STRUCTURAL_R:g}:1 minimum" if r_mult else "no measured move")
            happened = (f" It broke out on {day(bo)}." if bo is not None else " It has not broken out yet.")
            zones.append({"key": "entry", "title": "Entry", "state": "pass" if not skip else "fail", "from": e_from, "to": entry_to,
                          "illustration": True,
                          "line": f"buy {px(buy)} · stop {px(stop)}" + (f" · {_rr(r_mult, ok_r)}" if r_mult else ""),
                          "text": (f"Where this strategy's rules place the trade: an illustration, not a recommendation and "
                                   f"not a backtest result. Buy with a buy-stop just above the pivot, at {px(buy)}; the "
                                   f"breakout counts only on volume of at least {VOL_MULT:g}× the 50-day average. The stop "
                                   f"goes {STOP_BUFFER_PCT:g}% under the tight-area low, at {px(stop)}: a risk of "
                                   f"{risk_pct:.1f}% a share (the strategy skips anything over {MAX_STOP_PCT:g}%)."
                                   + (f" The target is the base's measured move, its high less its lowest low, "
                                      f"projected from the buy: {px(target)}, {_rr(r_mult, ok_r)} (it needs at least "
                                      f"{MIN_STRUCTURAL_R:g}R, before any overhead supply caps it)." if target else "")
                                   + f" Managing it: the stop moves to breakeven at +{BREAKEVEN_R:g}R; a third is sold "
                                     f"once the close is {STRENGTH_EXT_PCT:g}% above the 50-day average; the rest goes on a "
                                     f"close below the 50-day; and it is sold after {TIME_STOP_DAYS} sessions if it never "
                                     f"reached +1R." + happened
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": e_checks, "shapes": shapes})
            top = max(top, target or top, buy + BREAKEVEN_R * risk)
            bottom = min(bottom, stop)

        # ---- the cheat entry (MV-03 / MV-04): bought on a close through a tight shelf while the base is
        # still forming, stopped under the shelf — illustrated, like the pivot entry, from the strategy's rules
        frame_to = entry_to if done else at
        if cheat:
            ci, cz, cp = cheat
            third = "lower" if cz == MV03 else "middle"
            entry = float(daily["close"].iloc[ci])          # confirmed by the close, as the strategy buys it
            stop = pivot_stop(cp["cheat_low"], cfg.tick_size)
            risk = entry - stop
            cd = cp["depths"]
            mm = cheat_measured_move(bh, entry, cp.get("base_depth_pct") if cd else None)
            target, r_mult = entry + mm, (mm / risk if risk > 0 else None)
            risk_pct = risk / entry * 100
            c_from, c_to = day(ci), day(min(len(daily) - 1, ci + TIME_STOP_DAYS))
            shapes = [{"shape": "box", "from": day(max(0, ci - CHEAT_SHELF_DAYS)), "to": day(ci - 1),
                       "top": float(cp["cheat_pivot"]), "bottom": float(cp["cheat_low"]), "role": "tight",
                       "label": ""}]   # the base carries the one label (its footprint); the shelf range is in the card
            levels = [("buy", entry, f"Cheat buy {px(entry)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", entry + BREAKEVEN_R * risk, ""), ("target", target, f"Target {px(target)}")]
            shapes += [{"shape": "level", "from": c_from, "to": c_to, "price": v, "role": role, "label": lab,
                        "dash": role != "buy"} for role, v, lab in levels]
            ok_risk, ok_r = risk_pct <= MAX_STOP_PCT, (r_mult or 0) >= MIN_STRUCTURAL_R
            c_checks = [
                {"code": cz, "name": "Shelf", "value": f"{cp['cheat_range_pct']:.1f}%, {third} third",
                 "limit": f"at most {CHEAT_SHELF_PCT:g}% over {CHEAT_SHELF_DAYS} days, below the high", "state": "pass"},
            ] + ([
                {"code": cz, "name": "Shelf volume",
                 "value": (f"{cp['cheat_dryup']:.2f}x avg, {cp['cheat_quiet_days']} quiet"
                           if cp.get("cheat_dryup") == cp.get("cheat_dryup") and cp.get("cheat_dryup") is not None else "—"),
                 "limit": f"at most {DRYUP_RATIO:g}x, or {DRYUP_QUIET_DAYS} sessions at or under {DRYUP_QUIET_RATIO:g}x",
                 "state": "pass"},
            ] if CHEAT_DRYUP else []) + [
                {"code": "SL-03", "name": "Risk", "value": f"{risk_pct:.1f}%", "limit": f"at most {MAX_STOP_PCT:g}%",
                 "state": "pass" if ok_risk else "fail"},
                {"code": "R:R", "name": "Reward / risk", "value": _rr(r_mult, ok_r),
                 "limit": f"at least {MIN_STRUCTURAL_R:g}R", "state": "pass" if ok_r else "fail"},
            ]
            skip = ([] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit"]) + \
                   ([] if ok_r else [f"it projects {_rr(r_mult, False)}, under the {MIN_STRUCTURAL_R:g}:1 minimum" if r_mult else "no objective"])
            zones.append({"key": "cheat", "title": "Cheat entry", "state": "pass" if not skip else "fail",
                          "from": c_from, "to": c_to, "illustration": True,
                          "line": f"{third} third · buy {px(entry)} · stop {px(stop)}" + (f" · {_rr(r_mult, ok_r)}" if r_mult else ""),
                          "text": (f"Where this strategy's rules place a cheat entry: an illustration, not a recommendation "
                                   f"and not a backtest result. A cheat is bought while the base is still forming, before "
                                   f"the stock has recovered its old high, so its stop is close. On {c_from} the close "
                                   f"cleared a tight shelf ({cp['cheat_range_pct']:.1f}% over {CHEAT_SHELF_DAYS} sessions, "
                                   f"at most {CHEAT_SHELF_PCT:g}%) in the {third} third of the base. The buy is at the next "
                                   f"session's open, estimated here by that close, {px(entry)}. The stop goes {STOP_BUFFER_PCT:g}% under the shelf low, at {px(stop)}: "
                                   f"a risk of {risk_pct:.1f}% (the strategy skips anything over {MAX_STOP_PCT:g}%). The "
                                   f"objective is the old high, {px(bh)}, plus the base's measured move: {px(target)}"
                                   + (f", {_rr(r_mult, ok_r)} (it needs at least {MIN_STRUCTURAL_R:g}R, before any overhead "
                                      f"supply caps it)." if r_mult else ".")
                                   + f" Managing it is the same as any entry: the stop moves to breakeven at "
                                     f"+{BREAKEVEN_R:g}R, a third is sold once the close is {STRENGTH_EXT_PCT:g}% above the "
                                     f"50-day average, the rest on a close below the 50-day, and it is sold after "
                                     f"{TIME_STOP_DAYS} sessions if it never reached +1R."
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": c_checks, "shapes": shapes})
            top = max(top, target, entry + BREAKEVEN_R * risk, float(cp["cheat_pivot"]))
            bottom = min(bottom, stop)
            frame_to = max(frame_to, c_to)

        # ---- the frame, its kind, title and verdict
        kind = "cheat" if traded_cheat and cheat else "vcp" if done else "cheat" if cheat else "young" if young else "fail"
        today = " · today" if live else ""
        if kind == "vcp":
            # "trade skipped" means the strategy takes NOTHING on this base -- so it is read off the
            # entry illustrations, and only when every one of them fails.
            #
            # It used to be `all(zones)`, which let a single failing illustration speak for the whole
            # base. A completed VCP usually projects under 2R at its own pivot (the entry sits at the
            # base high, so the measured move is all that is left above it, while a cheat buys lower
            # and keeps the climb back to the high), so the pivot illustration fails on most bases
            # that the strategy nonetheless trades through the cheat. AKAM's 2013-01 base is the
            # case: structure passes, the pivot entry projects 1.7R and fails, the cheat projects
            # 2.1R and the run bought it -- and the frame still said "trade skipped" over a trade
            # that happened. An illustration's own verdict belongs in its zone text, not on the frame.
            entries = [z for z in zones if z.get("illustration")]
            structure_ok = all(z["state"] == "pass" for z in zones if not z.get("illustration"))
            none_taken = bool(entries) and all(z["state"] == "fail" for z in entries)
            title = ("VCP ✓ · trade skipped" if (none_taken or not structure_ok) else "VCP setup ✓") + today
            summary = (f"A complete VCP. Broke out on {day(bo)}." if bo is not None
                       else "A complete VCP, waiting for a close through the pivot.")
        elif cheat:
            ok = zones[-1]["state"] == "pass"
            # The daily screen runs under the live variant, which may withhold this cheat. Said BESIDE the
            # shipped rules' verdict, not instead of it: a backtest of the shipped rules may have traded
            # this very cheat, and this endpoint cannot tell which run the chart is showing -- turning the
            # cheat into "skipped" here would contradict that run's own trade beside it.
            withheld = ok and self._live_withholds(cheat[2])
            title = f"Cheat entry {'✓' if ok else '· trade skipped'}{' · the live screen withholds it' if withheld else ''}{today}"
            short = f"{len(depths)} pullbacks" if fail == "VCP-04" else self._VCP_FAILED.get(fail, fail)
            summary = (("A complete VCP, bought early through its cheat: on" if done else f"Not a VCP ({short}), but on")
                       + f" {day(cheat[0])} it cleared a tight "
                       f"shelf in the {'lower' if cheat[1] == MV03 else 'middle'} third of the base: a cheat entry."
                       + (f" The daily screen's live variant ({type(self).live_variant['name']}) withholds a cheat on "
                          f"a base that fails VCP-09, so it is not listed as a candidate." if withheld else ""))
        elif young:
            title = f"Too new to judge{today}"
            summary = f"Too new to judge: {young_why}."
        else:
            title = f"✗ {self._VCP_FAILED.get(fail, fail)}{today}"
            if fail == "VCP-04":   # the count says more than "wrong number"
                n, grew = len(depths), sum(b > WIDEN_TOL * a for a, b in zip(depths, depths[1:]))
                title = (f"✗ {n} pullback{'s' if n != 1 else ''}"
                         + (", growing" if n > MAX_CONTRACTIONS and grew * 2 > n - 1 else f" ({MIN_CONTRACTIONS}–{MAX_CONTRACTIONS} in a VCP)")
                         + today)
            summary = f"Not a VCP: {self._vcp_fail_why(r, daily, bh_i, rep)}."
        if live:
            summary = f"Still forming — judged on today's bar, {at}. " + summary
        return {"from": up_from, "base_from": bd, "to": frame_to, "kind": kind, "complete": done, "fail": fail,
                "breakout": day(bo) if bo is not None else None, "live": live, "as_of": at,
                "title": title, "summary": summary,
                # headroom above the highest level: the zone captions sit just inside the frame's top
                # edge, which was exactly the target's price, so "③ Entry" and "Target …" overprinted
                "frame": {"from": up_from, "to": frame_to, "top": top + (top - bottom) * 0.08, "bottom": bottom},
                "zones": zones}

    @staticmethod
    def _vcp_fail_why(r: dict, daily: pd.DataFrame, bh_i: int, rep: int) -> str:
        """The failing VCP rule of a detection, in words with its measured value and its limit."""
        d, f = r["depths"], r["fail"]
        if f == "VCP-03":
            if not r["base_tt"]:
                return (f"the trend template was not met on the high's bar ({daily.index[bh_i].date()}): "
                        f"{vcp_spec.template_miss(daily.iloc[bh_i])}")
            # the same structure test as vcp_spec._trend_held, located on the first bar that broke it
            # VCP-03 now judges the base as a WHOLE (v2 §2.6), so the detector's own reason is
            # the accurate one; naming a single bar would misdescribe a count across the base.
            if r.get("fail_why"):
                return str(r["fail_why"])
            return "the long trend did not hold through the base"
        if f == "VCP-04":
            return (f"{len(d)} pullback{'s' if len(d) != 1 else ''}, where a VCP needs at least "
                    f"{MIN_CONTRACTIONS}")
        if f == "VCP-05":
            if r.get("fail_why"):
                return str(r["fail_why"])
            return f"the base is deeper than {MAX_BASE_DEPTH_PCT:g}%"
        if f == "VCP-06":
            # The reset rule, so the explanation names the REFERENCE -- the last widening -- and
            # says which of its two halves failed. The detector already recorded both; prefer its
            # text when present so the page and the gate can never tell different stories.
            if r.get("fail_why"):
                return str(r["fail_why"])
            ref = 0
            for k in range(1, len(d)):
                if d[k - 1] > 0 and d[k] > WIDEN_TOL * d[k - 1]:
                    ref = k
            since = len(d) - ref
            if since < MIN_FROM_REFERENCE:
                return (f"pullback {ref + 1} ({d[ref]:.1f}%) widened out and only {since} contraction"
                        f"{'s' if since != 1 else ''} followed it, where the reset rule needs "
                        f"{MIN_FROM_REFERENCE}")
            return (f"the final pullback ({d[-1]:.1f}%) is {d[-1] / d[ref]:.2f}× the reference "
                    f"({d[ref]:.1f}%, pullback {ref + 1}, the last one that widened), where the reset "
                    f"rule allows at most {FINAL_REF_RATIO:g}×")
        if f == "VCP-07":
            return "a pullback made a lower low than the one before"
        if f == "VCP-08":
            return (f"the last pullback ({d[-1]:.1f}%) or the tight area ({r['tight_range_pct']:.1f}%) "
                    f"was wider than {TIGHT_PCT:g}%")
        if f == "VCP-09":
            return f"the pivot {r['pivot']:.2f} was more than {(1 - PIVOT_NEAR_HIGH) * 100:.0f}% under the base high"
        if f == "VCP-10":
            return f"tight-area volume was {r['dryup']:.2f}× its 50-day average, above {DRYUP_RATIO:g}× (no dry-up)"
        return "the volatility did not contract"
