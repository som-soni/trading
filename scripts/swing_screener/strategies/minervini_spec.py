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

import numpy as np
import pandas as pd

from ..marketdata import corporate_actions
from ..config.base import MarketConfig
from ..core import vcp_spec
from ..core import indicators as ind
from ..core import swings as sw
from ..core.context import _periods_as_of
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
NEAR = "S7"   # near miss (1.38): an MV-01 breakout of a base that missed ONE graded rule by a small margin
FLAT_COIL = "S8"  # flat base coiled (1.48): a resting buy-stop at a flat base's high, as MV-02 is for a VCP
SHAKE = "S9"  # shakeout (1.50): a base's recent lows undercut on volume and reclaimed, then a close through its high

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
TIGHT_NOISE_PCT = 6.0        # 1.49: a pullback this shallow is noise in a tight area, never a widening (vcp_spec)
MIN_FROM_REFERENCE = 2       # contractions from the most recent widening onward, inclusive
FINAL_REF_RATIO = 0.6        # final contraction / reference contraction, at most
# ---- 1.38, the near miss (S7). Minervini weighs a base's rules together; the strategy requires every one,
# and most of his own book examples (tests/minervini_book_cases.py) miss one or two by a little. A base
# that fails exactly ONE of these graded rules, by no more than its margin, and then breaks out with every
# MV-01 test passed -- or a full VCP whose breakout volume alone falls short, by no more than its margin --
# is bought as S7, a separate setup so its trades are read apart from S1's. 0 turns S7 off.
NEAR_MISS = 1
NEAR_FINAL_REF_RATIO = 0.75  # VCP-06: final / reference contraction (strict: FINAL_REF_RATIO)
NEAR_TIGHT_MIN_DAYS = 2      # VCP-08: sessions in the final contraction (strict: TIGHT_MIN_DAYS)
NEAR_TIGHT_PCT = 12.0        # VCP-08: depth of the final contraction and its range (strict: TIGHT_PCT)
NEAR_DRYUP_RATIO = 1.0       # VCP-10: tight-area volume x its 50-day (strict: DRYUP_RATIO)
NEAR_VOL_MULT = 1.2          # MV-01a: breakout volume x its 50-day (strict: VOL_MULT)
# The final tight area found at the right edge of the base when the zig-zag missed it (vcp_spec
# `_right_edge_tight_area`): RDN's Dec 2012 handle after a 33% cup. 0 = 1.37's reading.
TIGHT_AREA_ROUTE = 1
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
# PP-05, the width of the flag's tight area (its last swing high to today). 1.36: held to the flag's own
# depth limit instead of a VCP's TIGHT_PCT (10%). The Learn guide's power play is a flag "correcting no more
# than 20-25%" with volume contracting before the breakout -- it sets no 10% tight area, and that test
# refused the guide's own example (VKTX, January 2024: a 14% flag, its tight area 13.4%). The volume test
# (PP-06) still applies.
PP_TIGHT_PCT = 25.0
# 1.37: a power play's pivot is the flag's high (PowerPlayParams.pivot_at_flag_high), not the high of its last
# tight stretch: the guide buys "as the price clears the flag's high", and the flag ends (PP-04) on that same
# close. 0 = the tight-area high (1.36).
PP_PIVOT_FLAG_HIGH = 1
# ---- S6, the flat base (1.28). "Not all consolidations have tight pivot points. When a flat base
# occurs with no real pivot other than the high of the base, an investor can look to buy as the
# stock moves above the highest price at the top of the base provided that the base corrects no
# more than 10 or 15 percent" -- a base "four to seven weeks in duration" with little volatility
# contraction to measure. Before 1.28 such a base could only fail VCP-04 or VCP-06.
FLAT_MIN_DAYS = 20          # about four weeks …
FLAT_MAX_DAYS = 35          # … to seven
FLAT_MAX_DEPTH_PCT = 15.0   # base high to base low, at most
FLAT_PIVOT_DAYS = 10        # the sessions before the breakout: their volume must pass VCP-10's dry-up
                            # test ("every correct pivot point will develop with a contraction in volume")
# 1.47: the stop goes under the low of the last FLAT_STOP_DAYS sessions before the breakout -- the tight
# pivot area -- not all FLAT_PIVOT_DAYS. Ten sessions reached back into the base's last pullback: NTPC's
# 3 Sep 2007 breakout (pivot 147.17) took its stop under the 22 Aug low (130.08), 16.2% under the buy,
# where the tight week before it (136-141) puts it 12.3% under (8.1% at the pivot).
FLAT_STOP_DAYS = 5
# 1.48: S8, the flat base's buy-stop. S6 waits for a close through the base's high and buys the next open, so a
# strong breakout day is paid for at its close: NTPC closed 4.95% past its pivot on 3 Sep 2007, which with the
# stop under the tight week made the risk 12.3%, over MAX_STOP_PCT -- at the pivot it is 8.1%. Minervini buys
# AT the pivot. S8 places that order the way MV-02 does for a VCP: on a session when today's base qualifies as a
# flat base and the close sits within COIL_PCT below its high, a buy-stop just above the high, stopped under
# the low of the last FLAT_STOP_DAYS sessions. 0 = off (1.47).
FLAT_COIL_ON = 1
# 1.50, S9: the shakeout. A base that sheds its weak holders in one sharp drop under its recent lows, on heavy
# volume, recovers them within days, and then closes through its high is one Minervini buys -- the flush IS the
# supply leaving, so the quiet tight area a VCP needs (VCP-08, VCP-10) is not asked of it. Papa John's, Feb-Mar
# 2013: its Jan-Feb tight area failed the dry-up (1.17x) into the results, the results gap (27 Feb) cut 13% to
# 24.94 under the area's lows on 7.8x volume, 4 Mar recovered them and 5 Mar closed 29.24 through the base's
# 28.66 high on 3.1x -- every VCP rule refused it (VCP-06 'widened', then VCP-08 'one session old').
# The shakeout: one of the last SHAKEOUT_LOOKBACK_LEGS contractions whose low undercuts the lows of the
# SHAKEOUT_PRIOR_LEGS before it, on at least SHAKEOUT_VOL x the 50-day volume, with a close back above those
# lows within SHAKEOUT_RECOVER_DAYS, at most SHAKEOUT_WINDOW sessions before the breakout. The breakout: MV-01's
# tests through the base's highest high; the stop under the breakout session's low. 0 = off.
SHAKEOUT_ON = 1
SHAKEOUT_LOOKBACK_LEGS = 3
SHAKEOUT_PRIOR_LEGS = 2
SHAKEOUT_VOL = 1.5
SHAKEOUT_RECOVER_DAYS = 5
SHAKEOUT_WINDOW = 15

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
# 1.35: a fall deeper than MAX_BASE_DEPTH_PCT below a high is a Stage 4 decline, not a base, so that high
# cannot anchor one and the base count starts again from the highs after the low (VcpParams.
# deep_decline_resets). TNDM's 2018 recovery bases were held inside a 90%-deep "base" from its March 2017
# high and never judged. 0 = an old unbeaten high anchors whatever lies below it (1.34).
DEEP_DECLINE_RESETS = 1
# 1.56, research switch (off): a base in which the long trend broke -- more than MAX_CLOSES_BELOW_200 closes under the
# 200-day -- and then recovered restarts at the highs after its last close below the 200-day (VcpParams.
# trend_break_resets). eBay's 7-week base of Dec 2002 (Think & Trade Like a Champion fig. 7-4) sat under its unbeaten
# Dec 2001 high, was read as one 13-month base failing VCP-03, and never judged; with it on, S8 fills on 2003-01-06,
# Minervini's own breakout day. It is baked into VCP at import, so a variant runs with `--vcp trend_break_resets=1`.
TREND_BREAK_RESETS = 0
YOUNG_MIN_BARS = 60     # sessions listed before anything is judged: core.context's minimum, past the 50-day

# MV-03/MV-04 (1.27): the cheat shelf must show VCP-10's volume dry-up as well as its tightness.
# Minervini: a valid cheat area "should exhibit a contraction in volume as well as tightness in the
# range of price". Until 1.27 a cheat had no volume test at all, so a base that VCP-10 rejected for
# volume could still be bought through its shelf. 0 = tightness only, as before.
CHEAT_DRYUP = 1

# MV-03/MV-04 (1.34): a cheat follows Minervini's 3C SEQUENCE -- a decline, a low, a first rally,
# then the pause -- as the Learn guide teaches it ("do not try to buy the low of a downtrend"; the low
# cheat is "the same, in the lower third"). The base's low must be set before the shelf, the shelf must
# hold above it, and the rally between them must win back at least CHEAT_RALLY_FRAC of the decline
# from the base high (the guide's "a third to a half", its lower end). Until 1.34 any tight spot in
# the lower third counted, including the bottom of a slide: AXSM's 2026-09 "low cheat" was a 7-day
# shelf 1% above a low set the session before it, and stopped out 8 sessions later. 0 = no test.
CHEAT_RALLY_FRAC = 0.33
# ...and the shelf's volume must CONTRACT: its average at most CHEAT_VOL_CONTRACT x the sessions just
# before it (the rally from the low, at least CHEAT_VOL_LOOKBACK of them). CHEAT_DRYUP compares the
# shelf with the 50-day average, which a decline on light volume passes throughout (AXSM's shelf ran
# 0.64x the 50-day, no quieter than the week before it). [assumption: 0.9; 0 = no test]
CHEAT_VOL_CONTRACT = 0.9
CHEAT_VOL_LOOKBACK = 10

# 1.42: a session with no volume and no range (open = high = low = close, 0 shares) is a hole the data
# source filled with the previous price. The detectors leave it out (vcp_spec.without_dead_bars) instead of
# counting it as a quiet day: ADANIPORTS.NS's 2015-08-12 bar alone aged its final contraction to the five
# sessions VCP-08 needs and pulled the tight area's volume under VCP-10's limit. 0 = it counts (1.41).
SKIP_DEAD_BARS = 1

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
    tight_pct=PP_TIGHT_PCT, tight_min_days=TIGHT_MIN_DAYS, swing_k=SWING_K,
    dryup=PP_DRYUP, dryup_ratio=DRYUP_RATIO, dryup_quiet_days=DRYUP_QUIET_DAYS,
    dryup_quiet_ratio=DRYUP_QUIET_RATIO,
    pivot_at_flag_high=PP_PIVOT_FLAG_HIGH, skip_dead_bars=SKIP_DEAD_BARS,
)

VCP = vcp_spec.VcpParams(
    swing_k=SWING_K, min_swing_pct=MIN_SWING_PCT, prior_advance_pct=PRIOR_ADVANCE_PCT,
    base_min_days=BASE_MIN_DAYS, base_max_days=BASE_MAX_DAYS, min_contractions=MIN_CONTRACTIONS,
    max_contractions=MAX_CONTRACTIONS, max_base_depth_pct=MAX_BASE_DEPTH_PCT,
    deep_base_flag_pct=DEEP_BASE_FLAG_PCT,
    dryup_quiet_days=DRYUP_QUIET_DAYS, dryup_quiet_ratio=DRYUP_QUIET_RATIO,
    widen_tol=WIDEN_TOL, min_from_reference=MIN_FROM_REFERENCE, final_ref_ratio=FINAL_REF_RATIO,
    tight_noise_pct=TIGHT_NOISE_PCT,
    undercut_recovery_days=UNDERCUT_RECOVERY_DAYS,
    tight_min_days=TIGHT_MIN_DAYS, upper_zone=UPPER_ZONE, max_closes_below_200=MAX_CLOSES_BELOW_200,
    tight_pct=TIGHT_PCT, pivot_near_high=PIVOT_NEAR_HIGH, dryup_ratio=DRYUP_RATIO,
    cheat_dryup=CHEAT_DRYUP, young_listing=YOUNG_LISTING, deep_decline_resets=DEEP_DECLINE_RESETS,
    trend_break_resets=TREND_BREAK_RESETS,
    cheat_rally_frac=CHEAT_RALLY_FRAC, cheat_vol_contract=CHEAT_VOL_CONTRACT, cheat_vol_lookback=CHEAT_VOL_LOOKBACK,
    tight_area_route=TIGHT_AREA_ROUTE, skip_dead_bars=SKIP_DEAD_BARS,
    near_final_ref_ratio=NEAR_FINAL_REF_RATIO if NEAR_MISS else 0.0,
    near_tight_min_days=NEAR_TIGHT_MIN_DAYS if NEAR_MISS else 0,
    near_tight_pct=NEAR_TIGHT_PCT if NEAR_MISS else 0.0,
    near_dryup_ratio=NEAR_DRYUP_RATIO if NEAR_MISS else 0.0,
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
# SL-03 for a power play (1.36). Its stop goes under a flag of up to PP_FLAG_MAX_DEPTH_PCT, so 12-20% is
# normal, and 10% refused nearly every one -- the Learn guide's own example (VKTX, 14%) says "trade it
# smaller, or wait for a tighter entry". Positions are sized by their risk, so a wider stop is already a
# smaller position.
PP_MAX_STOP_PCT = 20.0
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
# 1.43: whether that 2:1 is tested against a projected price target at all. Minervini sets no price
# target: his reward-to-risk is a property of his RESULTS -- average gain against average loss, kept at
# 2:1 or better by cutting losses short (the stop, at most MAX_STOP_PCT) and riding winners on sell rules
# (into strength, then a close below the 50-day). The measured move -- the base's depth projected from the
# buy, capped by overhead supply -- is a classical chart-pattern convention this code added (the written
# spec has no target either), and as a gate it refused most pivot buys, whose projection is the one part
# of the base left above the buy. 0 = no projected target and no 2:1 test: the plan's target is the
# +PARTIAL_R mark where the stop goes to breakeven and a third is sold, a reference nothing sells at.
# 1 = the measured move, capped, must project MIN_STRUCTURAL_R (1.42).
MEASURED_MOVE_RR = 0
# How far above the BASE HIGH a swing high has to sit before it counts as
# external supply rather than part of the base's own ceiling. A base's ceiling
# is not a single line: `swings.overhead_levels` collects every swing high, and
# a consolidation prints several within a hair of its high (both sides of the
# range, every retest of the pivot). `chart_pattern.overhead_cluster_atr` is the
# same guard for the same reason.
OVERHEAD_CLUSTER_ATR = 1.0
# 1.38: how many years back overhead supply is counted when it caps the target. 0 = the shared levels
# (`swings.overhead_levels`: weekly swing highs over 5 years and monthly ones over all history, 1.37). Old
# peaks capped the measured move of Minervini's own buys -- Lululemon Nov 2010 under its 2008 high (6.1R ->
# 1.4R at the pivot), Best Buy Dec 1997 under 1993 (2.7R -> 0.6R), Stryker Jan 1995 under 1992 -- supply
# years old that he bought through. N keeps the daily swing highs of the last year and the weekly ones of
# the last N years.
OVERHEAD_YEARS = 2
# 1.38: the price step a stop or buy-stop is rounded to is at most this % of the price. A split-adjusted
# history prints a 1982 Wal-Mart at 0.117 and a 2009 Netflix at 0.72, where a one-cent tick moved the stop
# by 1-2% of the price and read as risk the trade never had. 0 = the market's tick as it is (1.37).
TICK_MAX_PCT = 0.2

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
# EX-04 by trade type (1.46, research switch; 0 = every trade, 1.45). Minervini's webinar (§7) sells
# part of a trade into strength when it is a trade, and holds a true leader for the trend. With it set,
# the +PARTIAL_R part is taken only from a company whose results on the trade's own date (the SEPA
# verdict every trade records, backtesting/fundamental_filter.py) fail the growth tests; an ACCEPTABLE
# or LEADER company skips it and holds to the trend exit. 1 = a company with no scorable results takes
# the partial (unknown is not a leader); 2 = it skips it too, so only WEAK takes the partial.
PARTIAL_BY_SEPA = 0
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
# 1.57, research switches for EX-06 (off = 1.56): Netflix's Oct 2009 breakout, Minervini's own fig. 7-5 trade, was
# sold on its first close under the 50-day (17 Dec 2009) at +1.55R, four months before it doubled and 21 before it
# was up 500%. TREND_EXIT_CLOSES: that many consecutive closes below the average to sell (1 = the first).
# TREND_LOOSE_R / TREND_LOOSE_SMA: once the trade's high has reached TREND_LOOSE_R x its risk, the exit watches the
# TREND_LOOSE_SMA-day average instead of the 50-day, giving a proven winner room (0 = off).
TREND_EXIT_CLOSES = 1
TREND_LOOSE_R = 0.0
TREND_LOOSE_SMA = 100
# 1.58, research switch (off): Minervini's follow-up buy, 'add and reduce'. While a position is held, a breakout
# (S1, S2, S7, S8) of a NEW base with its pivot above the average cost adds ADD_ON_NEW_BASE of the first buy at the
# next open (refused above the new base's buy range), at most ADD_MAX times; the stop on the whole position rises
# only as far as keeps its open risk at the first trade's. Apple 2004 (Think & Trade Like a Champion fig. 7-9) marks two follow-up
# buys; the backtest skipped every signal in a held stock ('already holding this symbol'). 0 = off.
ADD_ON_NEW_BASE = 0.0
ADD_MAX = 2
# EX-07, the time stop: sold if the high has not reached +1R within this many sessions.
TIME_STOP_DAYS = 15
# EN-02 fills on the close through the pivot; a fill on volume under VOL_MULT x the
# 50-day average is not a valid breakout and is sold at the next open.
LIGHT_VOLUME_EXIT = 1   # 1.55: back on -- 1.54 held light fills and failed verify (changelog)
# 1.51: MV-02 fills AT the close through the pivot, so that close's volume is known when it fills: under
# VOL_MULT x the 50-day it does not fill and the order keeps resting (1). 0 = fill it and let
# LIGHT_VOLUME_EXIT sell it at the next open, as before -- 517 of 574 S2 fills in the 1.46 US run did that.
S2_FILL_NEEDS_VOLUME = 1

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
# 1.59, research switch (off): the segment's trend. The market's small- and mid-cap index (MarketConfig.segment_symbol:
# Nifty Smallcap 250, IWM) must be up more than MKT_SEGMENT_MOM_MIN_PCT% over MKT_SEGMENT_MOM_DAYS sessions for new
# buys. Measured on the 2013-2021 trades of three runs (2026-11-10), the segment's 3-month return was the one entry-
# time measure whose buckets ordered R in both markets: Indian trades taken with it at or under 0 lost 11-13R in
# all. The benchmark (Nifty 500, SPY) can rise while the segment falls -- India 2018. 0 = off.
MKT_SEGMENT_MOM_DAYS = 0
MKT_SEGMENT_MOM_MIN_PCT = 0.0
# 1.59, research switch: 0 drops the benchmark-above-a-rising-average and breadth tests, so the gate is the segment
# test alone (with MKT_SEGMENT_MOM_DAYS set) or open (without). 1 = as before.
MKT_INDEX_TEST = 1
MKT_HIGHS_LOWS_RATIO = 1.0
# The bottoming pilot (1.46, research switches; 0 = the binary gate of 1.45). Minervini's bear-market
# webinar (research/creator-mark-minervini.md §2.1-2.3, §6): the best setups come at and just before the
# market low, so probe small there rather than wait out the whole recovery. With MKT_PILOT set, a
# session the gate calls risk-off still takes new buys, at PE_PILOT_FRAC of the risk budget, once a
# bottoming signal is present; full size returns only when the test above holds.
#   1 = an O'Neil follow-through day on the benchmark: day MKT_FTD_MIN_DAY or later of a rally from the
#       lowest close of the last MKT_FTD_LOW_DAYS sessions, up MKT_FTD_MIN_GAIN_PCT% or more on volume
#       above the previous session's; in force until a close below that low or until the gate turns on.
#   2 = breadth turning up: the share of the most-traded stocks above their 50-day average higher than
#       MKT_PILOT_BREADTH_DAYS sessions earlier.
MKT_PILOT = 0
MKT_FTD_LOW_DAYS = 50
MKT_FTD_MIN_DAY = 4
MKT_FTD_MIN_GAIN_PCT = 1.0
MKT_PILOT_BREADTH_DAYS = 10
# The control for the pilot (1.46): 0 opens the gate on every session, i.e. no market filter at all,
# so a variant can be compared with the filter off without leaving the job queue. 1 = the filter.
MKT_FILTER = 1

MAX_POSITIONS = 8               # PF-02
MAX_OPEN_RISK_PCT = 6.0         # PF-04
MAX_ADV_PCT = 5.0               # SL-06
# No new buy with results due within this many calendar days: live from the earnings
# calendar, in a backtest from the recorded results ANNOUNCEMENTS (spec.results_blackout:
# NSE broadcasts and board meetings, SEC 8-K Item 2.02), a company with none falling back
# to its filing dates -- the gap happens on the announcement, and the filing runs weeks behind it.
EARNINGS_BLACKOUT_DAYS = 14
# 1.51: 1 = the backtest's blackout keys on recorded announcements (filing dates only where a company
# has none); 0 = filing dates for every company, as before (a research control). Read after the scan.
RESULTS_BY_ANNOUNCEMENT = 1
# 1.52: 1 = a quarter is announced once, on its earliest record -- NSE's XBRL broadcast of results already
# out at the board meeting lands weeks later and is not a second announcement; 0 = every record counts, as
# in 1.51 (India then read ~7 dates per company-year). Read after the scan.
RESULTS_FIRST_PER_QUARTER = 1

# The guide's liquidity floor. Turnover is the 50-day average volume x the close, which is
# split-invariant, so it applies in backtests too. The price floor is LIVE ONLY: a backtest
# reads split-adjusted history, where a winner's early price is divided by every later split
# (the reason 1.2 dropped the market's own price floor from backtests).
MIN_TURNOVER_INR_CR = 10           # ₹ crore a day
MIN_TURNOVER_USD_M = 20            # $ million a day
# 1.45: the floor scales with the market. A fixed ₹10 crore is a 2026 number: in 2010 the whole Indian market traded
# a tenth of today's turnover, and the floor shut out most of its leaders -- BAJFINANCE.NS's 2010-07-05 breakout,
# ₹4.1 crore a day, among them. Now the floor is a share of the day's market turnover (breadth_daily.turnover: the
# 1,000 most-traded stocks' 20-day average close x volume), in basis points, set so it equals the fixed floor in
# late 2026 (₹1.05 lakh crore and $631 billion a day): ₹10 crore and $20 million then, about ₹1 crore in 2010 and
# $3.8 million in 2013. Before the series starts the first stored day's turnover is used; with none stored, the
# fixed floors above. 0 = the fixed floors (1.44).
SCALE_TURNOVER_FLOOR = 1
TURNOVER_FLOOR_BP_INR = 1.0
TURNOVER_FLOOR_BP_USD = 0.32
LIVE_MIN_PRICE_INR = 100
LIVE_MIN_PRICE_USD = 15

# The guide's fundamentals, as the backtest's `--fundamentals guide` level (off by default:
# stored results cover India only from late 2020). Quarterly EPS growth on the year-ago
# quarter, faster than the quarter before; sales growth; net margin no more than
# FUND_MARGIN_SLACK_PP points below the year-ago quarter's.
FUND_EPS_GROWTH_MIN_PCT = 20.0
FUND_SALES_GROWTH_MIN_PCT = 15.0
FUND_MARGIN_SLACK_PP = 1.0


_TURNOVER: dict = {}   # (market, the stage's end) -> (dates as int64, turnover): the series the floor scales with


def _market_turnover(cfg: MarketConfig):
    """The market's turnover series (backtesting/spec.market_turnover), as arrays, cached per market and stage
    boundary -- it is read once per session of every symbol a backtest screens."""
    from ..config import MARKETS
    from ..marketdata import asof
    mkt = next((k for k, c in MARKETS.items() if c.name == cfg.name), None)
    key = (mkt, asof.end())
    if key not in _TURNOVER:
        try:
            from ..backtesting import spec as spec_mod
            s = spec_mod.market_turnover(mkt) if mkt else pd.Series(dtype=float)
        except Exception:      # no table yet: the fixed floor
            s = pd.Series(dtype=float)
        _TURNOVER[key] = (s.index.to_numpy("datetime64[ns]").astype("int64"), s.to_numpy(float)) if len(s) else None
    return _TURNOVER[key]


def _min_turnover(cfg: MarketConfig, date=None) -> float:
    """The turnover floor on `date`: TURNOVER_FLOOR_BP_* of that day's market turnover (SCALE_TURNOVER_FLOOR), else
    the fixed MIN_TURNOVER_INR_CR / MIN_TURNOVER_USD_M."""
    inr = cfg.currency_code == "INR"
    fixed = MIN_TURNOVER_INR_CR * 1e7 if inr else MIN_TURNOVER_USD_M * 1e6
    if not SCALE_TURNOVER_FLOOR or not hasattr(date, "year"):     # a row without a date: the fixed floor
        return fixed
    got = _market_turnover(cfg)
    if got is None:
        return fixed
    t, v = got
    i = max(0, int(np.searchsorted(t, pd.Timestamp(date).value, side="right")) - 1)
    return (TURNOVER_FLOOR_BP_INR if inr else TURNOVER_FLOOR_BP_USD) / 1e4 * float(v[i])


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


def _tick(price: float, tick: float) -> float:
    """The step to round a level at `price` to: the market's tick, no coarser than TICK_MAX_PCT of the price."""
    return min(tick, float(price) * TICK_MAX_PCT / 100) if TICK_MAX_PCT and price > 0 else tick


def pivot_buy_stop(pivot: float, tick: float) -> float:
    """MV-02's resting buy-stop: just above the pivot. Shared by build_plans and the chart."""
    return round_tick(float(pivot) * 1.001, _tick(pivot, tick), "up")


def pivot_stop(tight_low: float, tick: float) -> float:
    """SL-01: the stop, STOP_BUFFER_PCT under the tight-area (or shelf) low. Shared by build_plans and the chart."""
    return round_tick(float(tight_low) * (1 - STOP_BUFFER_PCT / 100), _tick(tight_low, tick), "down")


def vcp_measured_move(base_high, depth_pct) -> float:
    """A VCP's measured move: the base high less its deepest low -- the BASE's depth (VCP-05), not its
    first pullback's. Until 1.33 this took the first pullback, on the reasoning that VCP-06 forces each
    contraction to shrink so the first is the deepest; the reset rule broke that (a deeper pullback
    becomes the new reference), and TKO's 2019 base, 5% then 40% then 8%, projected 0.6R instead of
    about 4.8R and was refused. NaN when either is unknown."""
    return float(base_high) * float(depth_pct) / 100 if base_high and depth_pct else float("nan")


def overhead_binding(entry: float, base_high, atr: float, overhead) -> float | None:
    """The overhead level that caps a target (build_plans), or None: the lowest of `overhead` at least
    OVERHEAD_CLUSTER_ATR ATRs above the base high (or the entry, when higher) -- closer levels are the base's
    own ceiling. The target is lowered to it when it sits below. Shared by build_plans and the chart."""
    ceiling_from = max(entry, float(base_high)) if base_high else entry
    edge = ceiling_from + OVERHEAD_CLUSTER_ATR * atr
    return min((lvl for lvl in overhead if lvl >= edge), default=None)


# The chart's entry zones under MEASURED_MOVE_RR = 0, where no target is drawn.
_NO_TARGET = (" There is no price target: Minervini sets none. His reward-to-risk is kept in the results -- "
              "losses cut at the stop, winners held until a sell rule fires -- not projected from the chart.")


def overhead_at(daily: pd.DataFrame):
    """For the chart: a function of a bar index giving the overhead levels evaluate() records on that bar
    (`plan_overhead`; with OVERHEAD_YEARS = 0 the context's own levels) -- from `daily` up to the bar and the
    weeks (and months) resampled as of it, as build_context resamples them. Cached per bar."""
    raw = daily[["open", "high", "low", "close", "volume"]]
    wk, mo, cache = ind.resample_weekly(raw), ind.resample_monthly(raw), {}

    def at(i: int) -> list[float]:
        if i not in cache:
            d, ts = daily.iloc[: i + 1], daily.index[i]
            h, _ = sw.current_swing_high(d)
            w = _periods_as_of(raw, wk, ts)
            cache[i] = (sw.overhead_levels(d, w, None, h, weekly_bars=52 * OVERHEAD_YEARS) if OVERHEAD_YEARS
                        else sw.overhead_levels(d, w, _periods_as_of(raw, mo, ts), h))
        return cache[i]
    return at


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


def shakeout(base: dict, daily: pd.DataFrame) -> dict | None:
    """S9's shakeout in `base` (a `vcp_spec.detect` result on the last bar of `daily`), or None: among the last
    SHAKEOUT_LOOKBACK_LEGS contractions, the latest whose low undercuts the lows of the SHAKEOUT_PRIOR_LEGS before
    it, on at least SHAKEOUT_VOL x the 50-day volume (the session before as its baseline), with a close back above
    those lows within SHAKEOUT_RECOVER_DAYS sessions, its low at most SHAKEOUT_WINDOW sessions before the last bar.
    Shared by evaluate and the chart."""
    legs = base.get("legs") or []
    n = len(daily)
    for k in range(len(legs) - 1, max(SHAKEOUT_PRIOR_LEGS, len(legs) - SHAKEOUT_LOOKBACK_LEGS) - 1, -1):
        prior_low = min(float(g[3]) for g in legs[k - SHAKEOUT_PRIOR_LEGS:k])
        lo_date, lo = legs[k][2], float(legs[k][3])
        if lo >= prior_low or lo_date not in daily.index:
            continue
        i = daily.index.get_loc(lo_date)
        if n - 1 - i > SHAKEOUT_WINDOW or i < 1:
            continue
        v50 = float(daily["vol_sma50"].iloc[i - 1]) if "vol_sma50" in daily else float("nan")
        if not (v50 == v50 and v50 > 0 and float(daily["volume"].iloc[i]) >= SHAKEOUT_VOL * v50):
            continue
        rec = daily["close"].iloc[i + 1: i + 1 + SHAKEOUT_RECOVER_DAYS]
        if not bool((rec > prior_low).any()):
            continue
        return {"low": lo, "date": lo_date, "prior_low": prior_low,
                "vol_ratio": float(daily["volume"].iloc[i]) / v50}
    return None


def flat_base(base: dict, d: pd.DataFrame) -> dict | None:
    """S6 / S8's flat base in `base` (a `vcp_spec.detect` result on the last bar of `d`), or None: a base that never
    became a VCP but passes the base's own qualifications (VCP-01, 02, 03, 05), FLAT_MIN_DAYS to FLAT_MAX_DAYS
    sessions long and at most FLAT_MAX_DEPTH_PCT deep. Its pivot is the base's high; `low` is the low of the last
    FLAT_STOP_DAYS sessions (the stop's anchor); `dried` is VCP-10's dry-up test on the last FLAT_PIVOT_DAYS
    sessions. Shared by evaluate (S6 on yesterday's base, S8 on today's) and the chart."""
    if (base["ok"] or not base.get("bh") or base["fail"] in ("VCP-01", "VCP-02", "VCP-03", "VCP-05")
            or base.get("base_days") is None or not FLAT_MIN_DAYS <= base["base_days"] <= FLAT_MAX_DAYS
            or base.get("base_depth_pct") is None or base["base_depth_pct"] > FLAT_MAX_DEPTH_PCT):
        return None
    dry, quiet = vcp_spec._dryup(d, len(d) - FLAT_PIVOT_DAYS, d["volume"].iloc[-FLAT_PIVOT_DAYS:], DRYUP_QUIET_RATIO)
    return {"pivot": float(base["bh"]), "low": float(d["low"].iloc[-FLAT_STOP_DAYS:].min()),
            "depth": float(base["base_depth_pct"]), "dry": float(dry), "quiet": int(quiet),
            "dried": bool(dry <= DRYUP_RATIO or quiet >= DRYUP_QUIET_DAYS), "base_date": str(base["bh_date"].date())}


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


def entry_misses(close: float, high: float, low: float, vol: float, v50: float, pivot: float | None) -> tuple:
    """MV-01's conviction tests on a session that closed through `pivot`: W1 volume under VOL_MULT x its 50-day
    average, W2 a close more than BUY_RANGE_PCT past the pivot, W3 a close under UPPER_HALF of the day's range.
    Returns ({code: missed}, volume ratio, close position in the range). Shared by evaluate (MV-01, MV-05) and
    the chart, so a breakout the chart marks is one the strategy would have bought."""
    vol_ratio = vol / v50 if v50 and v50 == v50 else float("nan")
    rng = high - low
    upper = (close - low) / rng if rng > 0 else 1.0
    return ({"W1": not (vol_ratio >= VOL_MULT),
             "W2": bool(pivot) and close > pivot * (1 + BUY_RANGE_PCT / 100),
             "W3": upper < UPPER_HALF}, vol_ratio, upper)


def entry_misses_text(miss: dict, vol_ratio: float, upper: float, close: float, pivot: float) -> str:
    """The failed MV-01 tests of `entry_misses`, in words."""
    out = []
    if miss["W1"]:
        out.append(f"volume {vol_ratio:.2f}x its 50-day average (needs {VOL_MULT:g}x)")
    if miss["W2"]:
        out.append(f"closed {(close / pivot - 1) * 100:.1f}% past the pivot (at most {BUY_RANGE_PCT:g}%)")
    if miss["W3"]:
        out.append(f"closed at {upper * 100:.0f}% of the day's range (needs {UPPER_HALF * 100:.0f}%)")
    return " and ".join(out)


def max_stop_pct(setup: str | None) -> float:
    """SL-03's limit for a setup: PP_MAX_STOP_PCT for a power play, MAX_STOP_PCT for the rest."""
    return PP_MAX_STOP_PCT if setup == MV05 else MAX_STOP_PCT


def power_measured_move(flag_high, run_pct) -> float:
    """A power play's objective: the size of the run into the flag -- the flagpole, from the run's low to the
    flag's high -- projected from the buy, as a high tight flag's measured move is. Until 1.36 the objective was
    the flag's tight range, the same distance the stop sits below it, so a power play could never project 2R
    and the 2:1 minimum refused every one. NaN when either is unknown. Shared by build_plans and the chart."""
    if not flag_high or not run_pct:
        return float("nan")
    run = float(run_pct) / 100
    return float(flag_high) * run / (1 + run)


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
# The base count (spec section 5, "Base count"), a rule since 1.44. Minervini buys the early bases of a Stage 2
# advance: by the fourth the trend is old and most who want the stock own it (the Learn guide's "4th+"). One
# function counts (`base_number`), on the price alone, as of the session it is asked about, so the backtest, the
# daily screen and the chart number a base the same way:
# - an advance lasts until TT-01 to TT-04 fail BASE_COUNT_RESET_DAYS sessions in a row (the spec's rule);
# - a base is a pullback of at least BASE_COUNT_MIN_DEPTH_PCT from a high, cleared by a close above that high at
#   least BASE_COUNT_MIN_DAYS sessions later -- the stock broke out of it, bought or not (a shorter or shallower
#   pause is part of the advance);
# - it counts only if its high is at least BASE_COUNT_STEP_PCT above the last base counted (a shelf just above
#   the last base is the same stage), and a base whose low undercuts the last counted base's low starts the
#   count again (O'Neil's practice, which Minervini follows here) [assumption: all four numbers].
# The spec counts MV-01 signals instead, which undercounts: few breakouts pass MV-01's volume and close tests,
# and NVDA's 2015-2018 advance read as "1st base" for all twelve of its setups.
BASE_COUNT_RESET_DAYS = 20
BASE_COUNT_MIN_DEPTH_PCT = 10.0
BASE_COUNT_MIN_DAYS = 25
BASE_COUNT_STEP_PCT = 10.0
# The rule: a base past this number of its advance is refused (build_plans). 0 = recorded, never refused (1.43).
MAX_BASE_COUNT = 3


def advances(daily: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """The Stage 2 advance each bar belongs to, for the base count: (start, origin) per bar, -1 outside one.

    An advance starts on the first bar where TT-01 to TT-04 hold (the close above the 150- and 200-day, the
    150-day above the 200-day, the 200-day rising for a month, the 50-day above both) and lasts until they
    have failed BASE_COUNT_RESET_DAYS sessions in a row; a shorter lapse -- a deep pullback inside a base --
    does not end it. `origin` is where the run of failures before it began (0 at the start of the data):
    the advance's low is the lowest low from there, the bottom it rose from."""
    c, s50, s150, s200 = (daily[k].to_numpy(float) for k in ("close", "sma50", "sma150", "sma200"))
    s200p = daily["sma200_21d_ago"].to_numpy(float)
    with np.errstate(invalid="ignore"):
        ok = (c > s150) & (c > s200) & (s150 > s200) & (s200 > s200p) & (s50 > s150) & (s50 > s200)
    start, origin = np.full(len(c), -1), np.full(len(c), -1)
    cur = run_from = None          # the advance in force; where the current run of failing bars began
    origin_from = 0
    for i in range(len(c)):
        if ok[i]:
            if cur is None:
                cur, origin_from = i, (run_from if run_from is not None else 0)
            run_from = None
        else:
            run_from = i if run_from is None else run_from
            if cur is not None and i - run_from + 1 >= BASE_COUNT_RESET_DAYS:
                cur = None
        if cur is not None:
            start[i], origin[i] = cur, origin_from
    return start, origin


def base_number(daily: pd.DataFrame, bh_i: int, adv: tuple | None = None) -> dict:
    """The base count (see BASE_COUNT_*) of the base whose high is bar `bh_i`, from `daily` up to that bar only:
    {"n": its number in the advance (None outside one), "start": the advance's first bar, "low_i": the advance's
    low, "earlier": the dates of the closes that cleared the earlier bases counted}. `adv`: `advances(daily)`, if
    already computed (it is causal, so the full-frame arrays are the same up to `bh_i`)."""
    start, origin = adv if adv is not None else advances(daily.iloc[: bh_i + 1])
    s = int(start[bh_i])
    if s < 0:
        return {"n": None}
    hi, lo, cl = (daily[k].to_numpy(float) for k in ("high", "low", "close"))
    counted: list = []                 # (high, low, the bar whose close cleared it) since the count last restarted
    peak, peak_i, trough = hi[s], s, lo[s]
    for j in range(s + 1, bh_i + 1):
        deep = (peak - trough) / peak * 100 >= BASE_COUNT_MIN_DEPTH_PCT    # a base has formed under `peak`
        if deep and cl[j] > peak:
            if j - peak_i >= BASE_COUNT_MIN_DAYS:
                if counted and trough < counted[-1][1]:
                    counted = []       # it undercut the last base counted: the count starts again
                if not counted or peak >= counted[-1][0] * (1 + BASE_COUNT_STEP_PCT / 100):
                    counted.append((peak, trough, j))
            peak, peak_i, trough = hi[j], j, lo[j]
        elif hi[j] > peak and not deep:
            peak, peak_i, trough = hi[j], j, lo[j]     # still advancing: a new high, not a base yet
        else:
            trough = min(trough, lo[j])      # inside a base, an intraday poke above its high does not end it
    o = int(origin[bh_i])
    return {"n": len(counted) + 1, "start": s, "low_i": o + int(lo[o: bh_i + 1].argmin()),
            "earlier": [str(daily.index[j].date()) for _, _, j in counted]}


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


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
    version = "1.59"
    # 1.52 changed only the results blackout, which filters signals after evaluate(): the scan is 1.51's.
    signal_version = "1.51"
    changelog = (
        ("1.59", "2026-11-10",
         "Adds MKT_SEGMENT_MOM_DAYS, MKT_SEGMENT_MOM_MIN_PCT and MKT_INDEX_TEST, research switches, OFF so no rule changes: the market "
         "filter can also require the small- and mid-cap index (Nifty Smallcap 250, IWM) to be up over a window. Of "
         "the entry-time measures tried on three runs' 2013-2021 trades, the segment's 3-month return was the one that "
         "ordered R in both markets; the benchmark can rise while the segment falls (India 2018). Read after the scan, "
         "signal-exempt; signal_version stays 1.51."),
        ("1.58", "2026-11-10",
         "Adds ADD_ON_NEW_BASE and ADD_MAX, a research switch, OFF so no rule changes: Minervini's follow-up buy. While "
         "held, a breakout (S1, S2, S7, S8) of a new base above the average cost adds a fraction of the first buy at the "
         "next open, the stop on the whole position raised so its risk stays the first trade's. From the Apple 2004 "
         "case (fig. 7-9), whose follow-up buys the backtest skipped as 'already holding this symbol'. Post-scan and "
         "signal-exempt; signal_version stays 1.51."),
        ("1.57", "2026-11-09",
         "Adds three EX-06 research switches, all OFF so no rule changes: TREND_EXIT_CLOSES (closes in a row below the "
         "50-day to sell), TREND_LOOSE_R and TREND_LOOSE_SMA (a slower average once the trade has reached that many R). "
         "From Minervini's Netflix 2009 case, which the strategy bought on his day and sold at +1.55R on the first "
         "close below the 50-day. Post-scan only and signal-exempt, so variants reuse the scan; signal_version stays 1.51."),
        ("1.56", "2026-11-09",
         "Adds TREND_BREAK_RESETS (VcpParams.trend_break_resets), a research switch, OFF: no rule changes. With it on, "
         "a base the long trend broke inside restarts after its last close below the 200-day, so a recent base under "
         "an old unbeaten high is judged on its own (eBay, Dec 2002, Minervini's fig. 7-4: S8 fills on his breakout day, "
         "2003-01-06). The new field moves the fingerprint and the signal id, so the next run rescans once; "
         "signal_version stays 1.51 because the scan is unchanged while the switch is off."),
        ("1.55", "2026-11-07",
         "LIGHT_VOLUME_EXIT is back on, as 1.54's criterion required: 1.54 failed verify (2022 to today, once). "
         "US -1.33% CAGR, failing CAGR above 0, though above the 1.53 rules' -4.40%; India 2.18%, failing "
         "'above the 1.53 rules' (2.27%). The rules are 1.53's; signal_version stays 1.51."),
        ("1.54", "2026-11-07",
         "LIGHT_VOLUME_EXIT is off: a buy-stop that fills on light breakout volume is no longer sold at the next "
         "open but held to the stop and the normal exits. Optimise stage (2013-2021, in-sample), 1.53 with the "
         "switch off against 1.52 plain: US +2.76% CAGR vs -3.32%, max drawdown -19.5% vs -40.4%, 7 of 9 years "
         "better -- four of its five largest winners (CSGP 2013 +16.2R, AEIS 2016 +10.1R) were sold the day after "
         "entry for light volume in 1.52; India +5.83% vs +3.71%, but only 2021 is better (+65.6% that year) and "
         "drawdown is deeper. S2's own fill rule (S2_FILL_NEEDS_VOLUME) still applies. The candidate is verified "
         "once against the criterion in `status`. After the scan, so signal_version stays 1.51."),
        ("1.53", "2026-11-06",
         "S2_FILL_NEEDS_VOLUME is its own switch. 1.51 set it only while LIGHT_VOLUME_EXIT was on, so a "
         "LIGHT_VOLUME_EXIT=0 variant also let S2 fill on light closes: in the US optimise run 188 of its 201 S2 "
         "trades were such fills, and the variant measured two changes as one. The defaults (both on) trade "
         "exactly as 1.52; only a variant that turns one switch off differs. After the scan, so signal_version "
         "stays 1.51."),
        ("1.52", "2026-11-06",
         "The results blackout counts a quarter once, on its earliest record (RESULTS_FIRST_PER_QUARTER). An Indian "
         "company publishes results at its board meeting, and NSE's XBRL broadcast of the same quarter often lands "
         "weeks later -- SIL.NS approved its March 2018 results on 2018-05-29, broadcast 2018-06-27 -- so 1.51 read "
         "about 7 announcements per company-year in India and blocked the fortnight just after results as if they "
         "were due: 17 trades of the 1.51 India optimise run. India now reads 3.9 per company-year, the US 3.8 "
         "(a second 8-K 2.02 in a quarter is the same results). After the scan, so signal_version stays 1.51."),
        ("1.51", "2026-11-05",
         "Two execution fixes from the audit of the 1.46 US optimise run's 870 losing trades "
         "(research/audit-minervini-run2077.md), both after the scan. (1) The results blackout keys on the "
         "recorded results ANNOUNCEMENTS -- the US from each 8-K with Item 2.02, India from NSE's broadcasts "
         "and board meetings -- instead of the 10-Q / 10-K filing, which lands weeks after the release; 110 "
         "trades of that run were bought within 14 days before a recorded announcement and averaged -0.08R "
         "(RESULTS_BY_ANNOUNCEMENT). The text that said the blackout used an estimated announcement date was "
         "wrong: the estimate had been tried and dropped, and the code keyed on filings alone. (2) An MV-02 "
         "buy-stop no longer fills on a close through the pivot whose volume is under VOL_MULT: the fill is at "
         "that close, so its volume is known, and 517 of 574 S2 fills were sold at the next open for it "
         "(S2_FILL_NEEDS_VOLUME). Both switches are signal-exempt, so their variants reuse the scan."),
        ("1.50", "2026-11-05",
         "S9, the shakeout (SHAKEOUT_*): a base whose recent lows are undercut in one sharp drop on heavy volume, "
         "won back within days, then closed through on MV-01's tests is bought, without the VCP's dry-up and tight "
         "area. Papa John's, March 2013: the results gap cut under its Jan-Feb lows on 7.8x volume, the stock won "
         "them back in three sessions and closed through its 28.66 high on 3.1x on 5 Mar; the VCP rules read it as "
         "widened, then too young. Adds a setup to evaluate(); cached signals are rescanned."),
        ("1.49", "2026-11-04",
         "VCP-06: a pullback no deeper than TIGHT_NOISE_PCT is noise inside a tight area -- it can neither be a "
         "widening nor break 'each smaller than the last'. Laurus Labs, April 2026: after 19% and 15%, dips of 3.3, "
         "4.7 and 5.0% inside one shelf read as a widening (4.7 > 1.1 x 3.3) and the base failed the day before a "
         "2.8x-volume breakout; it now reads 19/15/5 and is judged by the dry-up test (it fails, at 1.10x). A "
         "loosening right side such as 25, 10, 6, 9 still fails. Changes the detector, so cached signals are "
         "rescanned."),
        ("1.48", "2026-11-04",
         "S8, the flat base's buy-stop (FLAT_COIL_ON): when today's base passes S6's base tests and the close sits "
         "within COIL_PCT below its high, a resting buy-stop goes just above the high -- MV-02 for a flat base -- "
         "stopped under the last FLAT_STOP_DAYS sessions' low. S6 pays the breakout day's close: NTPC's 3 Sep 2007 "
         "breakout closed 4.95% past its pivot and the risk came to 12.3%, over MAX_STOP_PCT; bought at the pivot "
         "it is 8.1%. Adds a setup to evaluate(), so cached signals are rescanned."),
        ("1.47", "2026-11-04",
         "The flat base (S6) takes its stop under the low of the last FLAT_STOP_DAYS sessions before the "
         "breakout, the tight pivot area, instead of all FLAT_PIVOT_DAYS (which still judge the volume dry-up). "
         "Ten sessions reached back into the base's last pullback: NTPC's 3 Sep 2007 breakout set its stop "
         "16.2% under the buy, under a low from twelve days before; the tight week before the breakout puts it "
         "12.3% under. Changes evaluate()'s flat_low, so cached signals are rescanned."),
        ("1.46", "2026-11-04",
         "Three research switches, all off, so no rule changed: a run with them at 0 trades exactly as 1.45. "
         "From Minervini's bear-market webinar (research/creator-mark-minervini.md): MKT_PILOT makes the market "
         "filter three-state -- while it is risk-off, new buys at PE_PILOT_FRAC of the risk budget on a bottoming "
         "signal (1 = an O'Neil follow-through day on the benchmark, 2 = breadth turning up), full size only once "
         "the filter's own test holds; PARTIAL_BY_SEPA takes the +{PARTIAL_R}R part only from companies whose "
         "results on the trade's date fail SEPA's growth tests, so a leader holds to the trend exit; MKT_FILTER = 0 "
         "turns the filter off, the control the comparison needs. Measured in research/minervini-bottoming-gate.md. "
         "signal_version stays 1.45: nothing evaluate() reads changed."),
        ("1.45", "2026-11-04",
         "The turnover floor scales with the market (SCALE_TURNOVER_FLOOR). A fixed ₹10 crore / $20 million a day "
         "is a 2026 number: in 2010 the Indian market traded a tenth of today's turnover, and the floor shut out most "
         "of its leaders (BAJFINANCE.NS's 2010-07-05 breakout traded ₹4.1 crore a day). The floor is now "
         "TURNOVER_FLOOR_BP_INR / _USD basis points of the day's market turnover (breadth_daily.turnover, the "
         "1,000 most-traded stocks' 20-day average close x volume), set to equal the fixed floor in late 2026: "
         "about ₹1 crore in 2010, $3.8 million in 2013. Point in time: each session's floor reads that session's "
         "market turnover only. `--const SCALE_TURNOVER_FLOOR=0` restores 1.44."),
        ("1.44", "2026-11-04",
         "The base count is a rule (MAX_BASE_COUNT = 3). Minervini buys the early bases of a Stage 2 advance: by "
         "the fourth the trend is old and most who want the stock own it. evaluate() records each setup's base "
         "number in its advance (base_number, BASE_COUNT_*: an advance lasts until TT-01 to TT-04 fail 20 sessions "
         "in a row; a base is a pullback of 10%+ cleared by a close above its high 25+ sessions later, counted "
         "when its high is 10%+ above the last base counted; an undercut of that base's low restarts the count), "
         "and build_plans refuses a base past the third. The spec's own count (MV-01 signals) numbered all twelve "
         "of NVDA's 2015-2018 setups the first. `--const MAX_BASE_COUNT=0` records the number but refuses nothing. "
         "The chart numbers bases with the same function."),
        ("1.43", "2026-11-04",
         "No projected price target (MEASURED_MOVE_RR = 0). Minervini sets none: his reward-to-risk is a "
         "property of results -- average gain against average loss, kept at 2:1 or better by a stop of at most "
         "MAX_STOP_PCT and sell rules that let winners run -- not a level projected from the chart. Until 1.43 the "
         "base's measured move, capped by overhead supply, had to project MIN_STRUCTURAL_R, at the signal and "
         "again at the fill: a classical chart-pattern convention the written spec does not have, which refused "
         "most pivot buys (their measured move is the one part of the base left above the buy). The plan's "
         "target is now the +PARTIAL_R mark, where the stop goes to breakeven and a third is sold; no exit sells "
         "at it, and none ever did. The measured move is still recorded. `--const MEASURED_MOVE_RR=1` restores "
         "1.42. signal_version stays 1.42: evaluate() is unchanged."),
        ("1.42", "2026-11-03",
         "The detectors leave out dead sessions -- no volume and no range, a hole the data source filled with "
         "the previous price (SKIP_DEAD_BARS). Counted, such a bar aged a final contraction by a session it never "
         "traded and lowered the tight area's volume: ADANIPORTS.NS's 2015-08-12 bar (331.80 four times, 0 "
         "shares) alone made its base pass VCP-08 and VCP-10. `--vcp skip_dead_bars=0` restores 1.41. The chart "
         "now also judges every close through a pivot as evaluate does -- a refused crossing no longer hides a "
         "later one -- and refuses a crossing on a session that fails the Trend Template, naming why."),
        ("1.41", "2026-10-31",
         "A fresh scan and a signal-cache hit built different plans. build_plans read the overhead supply that "
         "caps the target from the price frames, and a cache hit rebuilds its context from 70 daily bars and no "
         "weekly frame, so it saw almost none of it: SSNC 2017-04-18 was refused fresh at 0.85R and bought from "
         "the cache at 2.03R (IONS 2017-07-07, LAZ 2017-07-21 and FRT 2021-09-09 likewise). evaluate() now "
         "records the levels (plan_overhead) and build_plans reads only those, so both paths agree "
         "(tests/check_minervini_cache_plans.py); OVERHEAD_YEARS leaves signal_exempt_consts, since the scan "
         "reads it. No rule changed: a 1.38 run that rescanned every bar traded as 1.41 does, and a 1.38 run "
         "served partly from the cache took setups the rules refuse."),
        ("1.40", "2026-10-31",
         "Two point-in-time clips in the backtest's signal filters (from the 25 Oct accuracy review, merged "
         "now). The results blackout read filing dates past the stage's end, so a signal in the last "
         "{EARNINGS_BLACKOUT_DAYS} days of an optimise run could be blocked by a filing the stage must not "
         "see; it now reads filings up to the boundary only. And the market filter let a signal through on a "
         "date before the benchmark's first stored session (NaN read as risk-on); that is now risk-off -- no "
         "stored stage starts that early, so this one cannot move a result. Optimise runs are stale for "
         "signals near the stage's end; nothing else moves. Both filters run after evaluate(), so "
         "signal_version stays 1.38."),
        ("1.39", "2026-10-31",
         "Backtest mechanics, no rule changed (backtesting/portfolio_sim, REVIEW-2026-10-31 item 7): a "
         "fill now sees only what had happened by its own moment in the session. An exit frees its "
         "slot and cash only for a fill at or after it, so a position sold at a session's close, or by "
         "a stop during it, no longer pays for a buy that filled at that session's open. Fills are "
         "sized, and the open-risk cap (PF-04) is measured, from the other positions' previous closes, "
         "not from the fill session's close. Waiting buy-stops are cancelled on the previous session's "
         "market filter, not on the fill session's own close, and a session with no filter reading yet "
         "is risk-off (bool(NaN) had read it as open). The stop on an EN-01 fill's own session is "
         "still not tested (the ladder runs only its close-based rules that session). signal_version "
         "stays at 1.38: only the simulator changed, so the cached signal rows still describe this "
         "scan. Results move, so stored runs of earlier versions are not comparable."),
        ("1.38", "2026-10-30",
         "Two changes from Minervini's own chart examples (tests/minervini_book_cases.py), where 1.37 caught 11 "
         "of 35 buy points. (1) The final tight area is also looked for at the right edge of the base "
         "(TIGHT_AREA_ROUTE): after a deep cup on a volatile stock the zig-zag's turn threshold hid a 7% handle "
         "(Radian, Dec 2012), and lowering it everywhere split Netflix 2009's final 8% contraction in two. "
         "(2) S7, the near miss: a base that fails exactly one graded rule -- the final/reference ratio, the "
         "tight area's age or depth, its volume dry-up -- by no more than a NEAR_* margin, or a full VCP whose "
         "breakout volume alone is short, is bought like MV-01 as its own setup, so its trades are measured "
         "apart. The book set goes to 13 of 35 (MercadoLibre Dec 2007, Isis Dec 2013) with no pinned example "
         "lost and no setup-to-avoid bought; with NEAR_MISS and TIGHT_AREA_ROUTE at 0 every snapshot of the "
         "golden harness matches 1.37. (3) The plan: overhead supply that caps the target counts only the last "
         "OVERHEAD_YEARS years -- peaks from years before capped Minervini's own Lululemon (2010), Best Buy "
         "(1997) and Stryker (1995) buys under 2R -- and a stop or buy-stop is rounded to a step no coarser than "
         "TICK_MAX_PCT of the price, since a one-cent tick on a split-adjusted 0.12 price moved the stop by 1-2%."),
        ("1.37", "2026-10-30",
         "A power play's pivot is the flag's high (PP_PIVOT_FLAG_HIGH), as the Learn guide buys it and as PP-04 "
         "already ends the flag, instead of the high of the flag's last tight stretch. The two disagreed: ENPH's "
         "August 2020 flag ended on a close above its high (76.75) that sat under the tight-area pivot (78.53), "
         "so no breakout was ever judged; TSLA's June 2020 breakout was 3.2% past its flag high but 6.5% past "
         "the tight-area high, outside the 5% buy range. Found by the breakout eval set. Changes which power "
         "plays fire; cached signals are rescanned."),
        ("1.36", "2026-10-30",
         "A power play's target is the run into the flag (the flagpole, from the run's low to the flag's "
         "high) projected from the buy. It was the flag's tight range -- the same distance as the stop below "
         "it -- so a power play projected under 1R and the 2:1 minimum refused every one: MV-05 could fire "
         "but never trade. And PP-05, the flag's tight area, is held to the flag's own 25% limit "
         "(PP_TIGHT_PCT) instead of a VCP's 10%: the Learn guide sets no such test, and it refused the guide's "
         "own example (VKTX, January 2024, a 13.4% tight area). A power play's stop may sit up to "
         "PP_MAX_STOP_PCT (20%) below the buy instead of 10%, since it goes under a flag of up to 25% and "
         "10% refused nearly every one; the position is sized by its risk. evaluate() now records "
         "pp_flag_high, so cached signals are rescanned."),
        ("1.35", "2026-10-30",
         "A high with a fall of more than MAX_BASE_DEPTH_PCT (50%) below it no longer anchors a base "
         "(DEEP_DECLINE_RESETS): that fall is a Stage 4 decline, and the base count starts again from the "
         "highs after its low. Before, an unbeaten high up to 65 weeks old held every later bar inside one "
         "bottomless base that failed VCP-03, so a turnaround's new Stage 2 bases were never judged -- TNDM's "
         "March and June 2018 bases, before a 25-fold run, sat inside a 90%-deep base from its March 2017 "
         "high. Found by the breakout eval set (backtesting/breakout_eval.py). Changes which bases the scan "
         "sees, so cached signals are rescanned."),
        ("1.34", "2026-10-30",
         "A cheat (MV-03 / MV-04) follows the 3C sequence the Learn guide teaches, and its shelf's volume "
         "must contract. Two new detector tests: (1) a turn before the shelf -- the base's low set before "
         "it, the shelf holding above that low, and a rally off the low that won back at least "
         "CHEAT_RALLY_FRAC of the decline; (2) the shelf's average volume at most CHEAT_VOL_CONTRACT x the "
         "sessions before it, not only quiet against the 50-day. Found on AXSM: a 2026-09 low cheat bought "
         "a tight spot at the bottom of a slide, 1% above a low set the session before, on volume no "
         "quieter than the week before; it was stopped out 8 sessions later. Changes which cheats are "
         "taken; pivot buys, flat bases and power plays are untouched. Cached signals are rescanned."),
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
    horizon = "swing"

    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
    watch_codes = ("W1", "W2", "W3", "W4", "W5")
    setup_codes = (MV01, MV02, MV03, MV04, MV05, FLAT, NEAR, FLAT_COIL, SHAKE)
    extra_columns = ("pp_pivot", "pp_tight_low", "pp_run_pct", "pp_flag_days", "pp_flag_high",
                     "fundamentals_ok", "revenue_yoy_pct", "earnings_yoy_pct", "gross_margin_change_pp",
                     "pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                     "first_depth_pct", "last_depth_pct", "base_depth_pct", "tightness_pct", "dryup_ratio",
                     "breakout_volume_ratio", "vcp_fail", "rs_score", "base_notes", "base_reference", "pivot_route", "pivot_pos",
                     "dryup_quiet_days", "closes_below_200", "below_200_share_pct", "undercuts",
                     "undercuts_failed", "undercuts_pending", "bh_atr_pct", "atr_blocks_base", "base_number")
    extra_numeric_columns = ("pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                             "first_depth_pct", "last_depth_pct", "base_depth_pct", "tightness_pct", "dryup_ratio",
                             "breakout_volume_ratio", "rs_score", "pivot_pos", "dryup_quiet_days",
                             "closes_below_200", "below_200_share_pct", "undercuts", "undercuts_failed",
                             "undercuts_pending", "bh_atr_pct", "base_number")
    needs_ctx_extras = True
    # Read after the scan, never by evaluate(): a `--const` variant moving only these reuses the
    # shipped run's signal rows (base.Strategy.signal_exempt_consts). The detector's constants,
    # the setups' (VOL_MULT, BUY_RANGE_PCT, COIL_PCT, UPPER_HALF, LOW_CHEAT_ENABLED,
    # CHEAT_BLOCK_VCP09) and the watch flags' are not here: a variant on one of them rescans.
    signal_exempt_consts = (
        # the plan: build_plans, signal_meta, classify
        "STOP_BUFFER_PCT", "MAX_STOP_PCT", "PP_MAX_STOP_PCT", "MAX_ENTRIES_PER_BASE", "NOMINAL_TARGET_R",
        "MIN_STRUCTURAL_R", "MEASURED_MOVE_RR", "MAX_BASE_COUNT", "OVERHEAD_CLUSTER_ATR", "TICK_MAX_PCT",
        # the exits (portfolio_sim's ExitPolicy)
        "BREAKEVEN_R", "PARTIAL_R", "PARTIAL_BY_SEPA", "FAIL_DAYS", "FAIL_SMA20_DAYS", "STRENGTH_EXT_PCT", "STRENGTH_FRAC",
        "CLIMAX_IS_PARTIAL", "TREND_EXIT_NEEDS_VOLUME", "TREND_EXIT_CLOSES", "TREND_LOOSE_R", "TREND_LOOSE_SMA",
        "ADD_ON_NEW_BASE", "ADD_MAX",
        "TIME_STOP_DAYS", "LIGHT_VOLUME_EXIT",
        "S2_FILL_NEEDS_VOLUME", "RESULTS_BY_ANNOUNCEMENT", "RESULTS_FIRST_PER_QUARTER",
        # sizing, the market filter and the book (backtesting/spec.py, --spec)
        "PE_WINDOW", "PE_WARMUP", "PE_PILOT_FRAC", "PE_PRESS_NET_R", "MKT_CONFIRM_DAYS",
        "MKT_GUIDE", "MKT_INDEX_SMA", "MKT_BREADTH_MIN_PCT", "MKT_BREADTH_RISING_DAYS",
        "MKT_SMA_RISING_DAYS", "MKT_HIGHS_LOWS_DAYS", "MKT_HIGHS_LOWS_RATIO", "MKT_SEGMENT_MOM_DAYS", "MKT_SEGMENT_MOM_MIN_PCT", "MKT_INDEX_TEST", "MKT_PILOT", "MKT_FTD_LOW_DAYS",
        "MKT_FTD_MIN_DAY", "MKT_FTD_MIN_GAIN_PCT", "MKT_PILOT_BREADTH_DAYS", "MKT_FILTER", "MAX_POSITIONS", "MAX_OPEN_RISK_PCT", "MAX_ADV_PCT",
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
        "- **Pick the setup** (S1–S9): a breakout, a coil under the pivot, two early \"cheat\" buys, "
        "a power play, a flat base (bought through its high, or coiled under it), a near miss, or a shakeout.\n"
        "- **Buy** (Entry), **protect** (Stop), **no price target** (Target) and **manage** (Exit).\n"
        "- **Size** the position, and skip new buys in the cases under \"When no new trade is taken\".",
        "**Timing.** Every rule is judged on a session's close, using only data up to that close. An "
        "order fills in a later session — at the next open, or on a buy-stop — never on the bar that "
        "produced it (spec section 10).",
        "**Rule ids.** TT-05, VCP-02, EX-04 and the like name the rule in the written backtest spec "
        "(research/minervini-backtest-spec.md), so a rule can be found there and in the code. Where the "
        "code departs from that spec is listed once, under Known caveats.",
    )
    caveats = (
        "**Dead sessions are left out** (1.42, SKIP_DEAD_BARS). A stored session with no volume and no range "
        "is a hole in the price data, not a quiet day, so the base and power-play detectors drop it before "
        "measuring. The averages and the 50-day volume baseline still include it, so a stock with many such "
        "holes reads slightly quieter than it traded.",
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
        "- **Target:** none, as in the spec and in Minervini (since 1.43). Until 1.42 a measured-move target "
        "had to project {MIN_STRUCTURAL_R}:1 (MEASURED_MOVE_RR).\n"
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
        "**The results blackout** in a backtest blocks on the recorded results ANNOUNCEMENTS (1.51): in the US "
        "each 8-K with Item 2.02, filed the day results go out; in India NSE's broadcast of each results filing "
        "and the board meeting that approved them; both back to 2005. A company with none recorded falls back to "
        "its 10-Q / 10-K or NSE filing date, which lands weeks after the announcement (a mean 35 days after a "
        "Q1-Q3 quarter end in the US, 53 after Q4), so the blackout still leaks for those companies -- a foreign "
        "issuer filing 6-Ks, a symbol with no SEC CIK. Before 1.51 every company keyed on filings, and in the "
        "1.46 US optimise run 110 trades were bought within {EARNINGS_BLACKOUT_DAYS} days before a recorded 8-K "
        "2.02 (Morgan Stanley on 2014-01-15, results on the 17th). An 8-K 2.02 also covers a mid-quarter update "
        "or pre-announcement, which blocks a buy too. A stock with neither date is never blocked.",
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
        "v1.55 has 1.53's rules: v1.54 (LIGHT_VOLUME_EXIT off) FAILED verify, 2022-01-01 to 2026-11-07, run once "
        "per market. US: -1.33% CAGR (the 1.53 rules -4.40%), Sharpe -0.05, max drawdown -26.6%, 342 trades -- "
        "fails CAGR above 0. India: 2.18% (the 1.53 rules 2.27%), Sharpe 0.28, max drawdown -25.7%, 210 trades "
        "-- fails 'above the 1.53 rules'. Neither version beats holding the index over those years (excess "
        "CAGR: US -10.65 / -13.72 points, India -6.97 / -6.88). Those years are now seen: a rule changed "
        "because of them is tuned on them. The criterion, as written before the runs: "
        "v1.54 (LIGHT_VOLUME_EXIT off). Criterion written 2026-11-07, before the verify runs "
        "(2022-01-01 to today), each market once: v1.54 passes only if, in BOTH the US and India, (1) CAGR is "
        "above 0, (2) CAGR is above the same-window run of the 1.53 rules (`--const LIGHT_VOLUME_EXIT=1`), and "
        "(3) it makes at least 50 trades. A fail in either market fails the version, and the next version "
        "restores the 1.53 exit. The figures behind choosing it are in-sample (optimise stage, 2013-2021): US "
        "+2.76% CAGR vs -3.32% for 1.52, India +5.83% vs +3.71% (India's gain is 2021 alone). Five candidates "
        "were compared on those years (S8 off, S9 off, both, the light-volume exit off, and 1.52), so the "
        "chosen one's in-sample margin is optimistic. Older figures follow. "
        "IN-SAMPLE ONLY, not verified; verify not run. v1.41 (fresh and cached scans build one plan, with 1.39's simulator and 1.40's filter fixes) has no run "
        "yet. Its rules are 1.38's, but a 1.38 run could serve a bar from the signal cache, where the plan saw "
        "almost no overhead supply and took setups the rules refuse (SSNC 2017-04-18 at 2.03R instead of 0.85R), "
        "so re-run at 1.41 before reading 1.38's figures as the rules' result. v1.38, optimise stage (2013-2021, "
        "in-sample), live variant (CHEAT_BLOCK_VCP09=1, TREND_EXIT_NEEDS_VOLUME=1): India 6.73% CAGR, excess "
        "-6.81 points a year, max drawdown -15.2%, Sharpe 0.75; US -3.42% CAGR, excess -17.43, max drawdown "
        "-35.5%. Neither beats holding the index. The last runs of the rules as configured, no variant "
        "(optimise stage): v1.36 India -0.34% CAGR, excess -13.88; v1.34 US -4.81%, excess -18.82. Older "
        "versions, optimise stage, live variant: v1.31 India 199 trades, 34% won, +0.20R a trade, profit factor "
        "1.18, CAGR +1.6%, worst drawdown -12.5%; US 490 trades, 35% won, -0.04R a trade, profit factor 0.83, "
        "CAGR -2.5%, worst drawdown -27.5% -- India's +0.20R rests on a few large winners (Bajaj Finance, 2016, "
        "is +10R). No pass criterion for a verify run has been written yet. Earlier versions' figures are in "
        "the changelog and in research/minervini-spec-sensitivity-india.md and -us.md."
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
              "lowest low of the last 252 sessions). That is the figure in *Trade Like a Stock Market Wizard*; "
              "*Think & Trade Like a Champion* gives 25%.",
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
              "- **A turn first:** the shelf comes after the base has made its low, rallied and paused "
              "— never at the bottom of a decline. The base's lowest low is set before the shelf, the "
              "shelf's low holds above it, and the rally between them won back at least "
              "{CHEAT_RALLY_FRAC} of the fall from the base high to that low. Off when CHEAT_RALLY_FRAC "
              "is 0.\n"
              "- **Volume contracts into the shelf:** the shelf's average volume is at most "
              "{CHEAT_VOL_CONTRACT} times the average of the sessions before it (the rally from the "
              "low, at least {CHEAT_VOL_LOOKBACK} sessions). Being quiet against the 50-day average is "
              "not enough: a decline on light volume is quiet throughout. Off when CHEAT_VOL_CONTRACT "
              "is 0.\n"
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
              "- **Tight area:** from the highest confirmed swing high inside the flag (or "
              "the flag high, if there is none) to yesterday, covering at least the last "
              "{TIGHT_MIN_DAYS} sessions. Its range is at most {PP_TIGHT_PCT}% (the flag's own limit); "
              "its low is the stop's reference.\n"
              "- **Pivot:** the flag high (PP_PIVOT_FLAG_HIGH is {PP_PIVOT_FLAG_HIGH}; 0 uses the tight "
              "area's high). The close that clears it both ends the flag and is the breakout.\n"
              "- **Volume dried up (PP-06):** the tight area passes VCP-10's test — average volume at "
              "most {DRYUP_RATIO} times the 50-day average, or at least {DRYUP_QUIET_DAYS} sessions at "
              "or under {DRYUP_QUIET_RATIO} times it. Only while PP_DRYUP is 1 (it is {PP_DRYUP}).\n"
              "- **Trigger:** the same as MV-01's — yesterday's close at or below the pivot, today's "
              "close above it on at least {VOL_MULT} times average volume, at least {UPPER_HALF} of "
              "the way up the day's range, and no more than {BUY_RANGE_PCT}% above the pivot.\n\n"
              "It is looked for separately from bases, because the base checks would reject it: the "
              "pause is usually too short to count as a base, and after so fast a run the long "
              "averages have not caught up.",
        NEAR: "Near miss: the MV-01 breakout of a base that missed ONE rule, narrowly. Minervini weighs a "
              "base's rules together, and most of his own published examples miss one or two of this "
              "strategy's thresholds by a little; S7 buys those, as a separate setup so its results are read "
              "apart from S1's.\n\n"
              "- **One near miss, no more:** either the base failed exactly one of these and by no more than "
              "the margin -- the final contraction at most {NEAR_FINAL_REF_RATIO} times the reference "
              "(strict {FINAL_REF_RATIO}); the tight area at least {NEAR_TIGHT_MIN_DAYS} sessions old (strict "
              "{TIGHT_MIN_DAYS}) and at most {NEAR_TIGHT_PCT}% deep (strict {TIGHT_PCT}%); its volume at most "
              "{NEAR_DRYUP_RATIO} times the 50-day (strict {DRYUP_RATIO}) -- and passed every other rule; or "
              "the base is a full VCP and only the breakout volume fell short, at least {NEAR_VOL_MULT} times "
              "the 50-day (strict {VOL_MULT}).\n"
              "- **The breakout:** otherwise exactly MV-01 -- a close through yesterday's pivot, within "
              "{BUY_RANGE_PCT}% of it and in the upper part of the day's range, bought at the next open and "
              "stopped under the tight area's low.\n\n"
              "Off with NEAR_MISS = 0.",
        SHAKE: "Shakeout: a base that flushes its weak holders in one sharp drop under its recent lows, on heavy "
               "volume, wins those lows back within days and closes through its high. The flush is the supply "
               "leaving, so the quiet tight area a VCP needs is not asked of it.\n\n"
               "- **The base:** passes VCP-01, VCP-02, VCP-03 and VCP-05 (an advance into it, a legal age, the trend "
               "held, not too deep).\n"
               "- **The shakeout:** one of its last {SHAKEOUT_LOOKBACK_LEGS} pullbacks ends under the lows of the "
               "{SHAKEOUT_PRIOR_LEGS} pullbacks before it, on at least {SHAKEOUT_VOL} times the 50-day average "
               "volume; a close back above those lows comes within {SHAKEOUT_RECOVER_DAYS} sessions; the shakeout's "
               "low is at most {SHAKEOUT_WINDOW} sessions before the breakout.\n"
               "- **The breakout:** today closes through the base's highest high with MV-01's tests (at least "
               "{VOL_MULT} times average volume, in the upper part of the day's range, at most {BUY_RANGE_PCT}% past "
               "it). Bought at the next open, stopped under today's low.\n\n"
               "Off with SHAKEOUT_ON = 0.",
        FLAT_COIL: "Flat base coiled: the flat base (S6) bought AT its high with a resting buy-stop, as MV-02 "
                   "is for a VCP, instead of after a close through it. Today's base passes S6's base tests "
                   "({FLAT_MIN_DAYS}–{FLAT_MAX_DAYS} sessions, at most {FLAT_MAX_DEPTH_PCT}% deep, the last "
                   "{FLAT_PIVOT_DAYS} sessions quiet) and the close sits within {COIL_PCT}% below the base's high. "
                   "The buy-stop goes just above the high; the stop under the low of the last {FLAT_STOP_DAYS} "
                   "sessions. Unlike MV-02 it fills during the day, at the buy-stop (or the open, on a gap "
                   "through it), so it pays the pivot rather than the breakout day's close; a fill on less than "
                   "{VOL_MULT} times average volume is sold at the next open, and the order is cancelled on a "
                   "close under the stop's reference. Off with FLAT_COIL_ON = 0.",
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
              "The stop goes under the low of the last {FLAT_STOP_DAYS} of those sessions, the tight "
              "pivot area; the objective is the "
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
        "Early bases only (1.44, MAX_BASE_COUNT). A Stage 2 advance builds a series of bases, and Minervini "
        "buys the early ones: by the fourth the trend is old and most who want the stock already own it. Each "
        "setup's base is numbered in its advance, and a base numbered past {MAX_BASE_COUNT} is refused -- "
        "whatever the setup. How it is counted, as of the signal session: the advance lasts until TT-01 to TT-04 "
        "have failed {BASE_COUNT_RESET_DAYS} sessions in a row; an earlier base counts once a close cleared its "
        "high, at least {BASE_COUNT_MIN_DAYS} sessions after it and after a pullback of at least "
        "{BASE_COUNT_MIN_DEPTH_PCT}%, when its high is at least {BASE_COUNT_STEP_PCT}% above the last base "
        "counted; a base that undercuts the last counted base's low starts the count again. A power play has no "
        "base and is not numbered.",
        "Pivot breakout (MV-01, EN-01). Bought at the next session's open. Skipped if that open is "
        "more than {BUY_RANGE_PCT}% above the pivot (too extended to buy) or at or below the tight "
        "low (the setup has already failed).",
        "Coiled below the pivot (MV-02, EN-02). A buy-stop order is placed 0.1% above the pivot and "
        "kept for up to 10 sessions.\n\n"
        "- **Fills** only on a session that CLOSES at or above the pivot on at least {VOL_MULT} times "
        "its 50-day average volume, at that close (the volume half while S2_FILL_NEEDS_VOLUME is "
        "{S2_FILL_NEEDS_VOLUME}). A session that pokes through during the day and closes back under it, "
        "or closes above it on lighter volume, does not fill; the order keeps waiting.\n"
        "- **Skipped** if the fill would be more than {BUY_RANGE_PCT}% above the pivot.\n"
        "- **Cancelled** by a close below the tight low.",
        "Cheats (MV-03, MV-04). Bought at the next session's open. Skipped if that open is more than "
        "{BUY_RANGE_PCT}% above the shelf's high, or at or below the shelf's low.",
        "Power play (MV-05). Bought at the next session's open. Skipped if that open is more than "
        "{BUY_RANGE_PCT}% above the flag's pivot, or at or below the flag's tight low.",
        "Shakeout (S9). Bought at the next session's open after the close through the base's high. Skipped if "
        "that open is more than {BUY_RANGE_PCT}% above the high, or at or below the breakout session's low.",
        "Flat base coiled (S8). A buy-stop 0.1% above the base's high, kept for up to 10 sessions. It "
        "fills during the day at the buy-stop, or at the open if the stock gaps through it -- not at the "
        "close, as MV-02 does -- and is sold at the next open if that day's volume is under {VOL_MULT} times "
        "average. Cancelled by a close below the low of the last {FLAT_STOP_DAYS} sessions.",
        "Flat base (S6). Bought at the next session's open. Skipped if that open is more than "
        "{BUY_RANGE_PCT}% above the base high, or at or below the low of the {FLAT_STOP_DAYS} "
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
        "Follow-up buys (a research switch, off: ADD_ON_NEW_BASE is {ADD_ON_NEW_BASE}). Minervini adds to a winner "
        "as it builds each new base. With the switch on, a breakout (S1, S2, S7 or S8) of a new base in a stock "
        "already held, its pivot above the average cost, adds ADD_ON_NEW_BASE of the first buy at the next open "
        "(refused above the new base's buy range), at most {ADD_MAX} times. The stop on the whole position rises "
        "only as far as keeps its risk at the first trade's: the profit pays for the add. Off, a "
        "signal in a stock already held is skipped.",
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
        "the trade is skipped: the loss would be too large. A power play allows {PP_MAX_STOP_PCT}%: its "
        "stop sits under a flag of up to {PP_FLAG_MAX_DEPTH_PCT}%, and the position is sized by its risk, "
        "so a wider stop buys fewer shares. On the live screen such a setup shows as WATCH.",
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
        "There is no price target. Minervini sets none: he does not project how far a stock will go. His "
        "reward-to-risk is a property of his results -- the average gain against the average loss, kept at 2:1 "
        "or better by two things the rules do: a loss is cut at the stop, at most {MAX_STOP_PCT}% below the buy, "
        "and a winner is held until a sell rule under Exit fires. Winners are never sold at a fixed price.",
        "The first managed step stands in for a target in the trade record: +{PARTIAL_R}R, where the stop "
        "moves to breakeven and a third is sold. Nothing else reads it.",
        "The base's measured move -- its depth, high to low, projected from the buy -- is still measured and "
        "shown, for study. Until 1.42 it was a rule (MEASURED_MOVE_RR = 1): capped by the nearest older swing "
        "high at least {OVERHEAD_CLUSTER_ATR} ATR above the base high, it had to project at least "
        "{MIN_STRUCTURAL_R} times the risk, at the signal and again on the price paid. That is a classical "
        "chart-pattern convention, not Minervini's, and it refused most pivot buys: the measured move is the one "
        "part of the base left above a buy at the top of it.",
    )
    exit_rules = (
        "Each session an open position is checked against these rules, in this order, and the first that "
        "applies acts. Apart from the stop (see Stop), each exit is decided on the session's close and "
        "sold at the next session's open.",
        "Unconfirmed breakout (buy-stop fills, S2 and S8), while LIGHT_VOLUME_EXIT is on -- it is "
        "{LIGHT_VOLUME_EXIT} (on; 1.54 turned it off, failed verify, and 1.55 turned it back on). When on: if the session that filled the buy-stop traded less "
        "than {VOL_MULT} times its 50-day average volume, the breakout was not confirmed and the whole "
        "position is sold at the next open. Off, such a fill is held to the stop and the exits below.\n\n"
        "S2's fill itself needs that volume since 1.51 (S2_FILL_NEEDS_VOLUME), whichever way this is set.",
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
        "held. This is how most winners end. Two research switches, both off: TREND_EXIT_CLOSES "
        "({TREND_EXIT_CLOSES} now) asks for that many closes in a row below it, and TREND_LOOSE_R "
        "({TREND_LOOSE_R} now; 0 = off) moves the line to the {TREND_LOOSE_SMA}-day average once the trade's high "
        "has reached that many R.\n\n"
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
        "When it fails, no new buy is taken and waiting buy-stops are cancelled before the next session "
        "opens (the test reads a close, so it cannot cancel a buy that filled earlier that session); positions already "
        "held are kept and managed as usual. The live screen applies the same test.\n\n"
        "`--mkt01` swaps in an older test (the index above its 200-day, and its 50-day above its "
        "200-day); `--mkt-confirm N` makes a recovery wait N sessions before buying resumes.",
        "The uptrend is young — only when SMA200_PREF_REQUIRED is 1 (it is {SMA200_PREF_REQUIRED}). No new "
        "buy while the 200-day average is not higher than {SMA200_RISING_PREF_BARS} sessions ago (about 4-5 "
        "months), even though it passed G5's one-month test. Minervini states the month as the minimum "
        "and the longer rise as a preference, so this stays off until a backtest shows it helps.",
        "Results are due. No new buy with quarterly results due within {EARNINGS_BLACKOUT_DAYS} "
        "days: a results-day gap can jump straight past the stop. Live, the date comes from the "
        "earnings calendar; in a backtest from the recorded results announcements (RESULTS_BY_ANNOUNCEMENT "
        "is {RESULTS_BY_ANNOUNCEMENT}), or the filing date for a company with none recorded. A quarter counts "
        "once, on its earliest record (RESULTS_FIRST_PER_QUARTER is {RESULTS_FIRST_PER_QUARTER}): a filing "
        "broadcast weeks after the board meeting is not a second announcement.",
        "The stock is too thin. It must trade at least {TURNOVER_FLOOR_BP_INR} basis points (India) or "
        "{TURNOVER_FLOOR_BP_USD} (US) of the whole market's daily turnover (50-day average of volume × close). "
        "The floor grows with the market: set to ₹{MIN_TURNOVER_INR_CR} crore and ${MIN_TURNOVER_USD_M} million "
        "a day in late 2026, it was about ₹1 crore in 2010 and $3.8 million in 2013, when the whole market "
        "traded a fraction of today's turnover (since 1.45; a fixed floor shut out most early leaders). The live screen "
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
                            "the shelf low; a power play (MV-05), bought at the next open and stopped under the "
                            "flag's tight low; or a flat base (S6), flat-base coil (S8), shakeout (S9) or near miss "
                            "(S7), each as its setup describes. The market regime never caps a decision to this tier.",
        "WATCH_WAIT": "A valid plan held back: its stop sits more than {MAX_STOP_PCT}% below entry, results are due "
                      "within {EARNINGS_BLACKOUT_DAYS} days, the 200-day has risen for under "
                      "{SMA200_RISING_PREF_BARS} sessions while SMA200_PREF_REQUIRED is 1, or the market filter "
                      "allows no new buys (see the note below). Worth watching, not buying.",
        "AVOID": "A Trend Template gate failed, or there is no valid entry plan — no breakout, coil or cheat setup, "
                 "or a plan that fails its checks (such as a stop more than {MAX_STOP_PCT}% below the buy).",
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
        ("Deep decline resets the base", "DEEP_DECLINE_RESETS", "1 = a high with a fall of more than "
         "{MAX_BASE_DEPTH_PCT}% below it cannot anchor a base: that is a Stage 4 decline, and the base count "
         "starts again from the highs after its low."),
        ("Trend break resets the base", "TREND_BREAK_RESETS", "1 = a base with more than {MAX_CLOSES_BELOW_200} "
         "closes below the 200-day restarts at the highs after its last close below it, so a recent base under an "
         "old, unbeaten high is judged on its own. 0 (now) = the highest unbeaten high anchors the base, however "
         "the trend fared inside it. A research switch: run it as a variant with --vcp trend_break_resets=1."),
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
        ("Power play, pivot at the flag high", "PP_PIVOT_FLAG_HIGH", "1 = MV-05 buys through the flag's high, "
         "where the flag also ends (PP-04); 0 = through the high of its last tight stretch."),
        ("Power play, tight area", "PP_TIGHT_PCT", "MV-05: widest the flag's last stretch may be (PP-05); the "
         "flag's own limit, not a VCP's {TIGHT_PCT}%."),
        ("Overhead supply, years", "OVERHEAD_YEARS", "Years of swing highs that can cap the target (MEASURED_MOVE_RR = 1 only); 0 = weekly "
         "highs over 5 years and monthly ones over all history (1.37)."),
        ("Tick, largest step", "TICK_MAX_PCT", "A stop or buy-stop is rounded to the market's tick, no coarser "
         "than this % of the price (split-adjusted history); 0 = the tick as it is."),
        ("Tight-area noise", "TIGHT_NOISE_PCT", "VCP-06: a pullback this shallow is noise inside a tight area; it "
         "can neither widen the base nor fail the shrink test. 0 = every pullback counts (1.48)."),
        ("Near miss", "NEAR_MISS", "1 = S7 buys a breakout from a base that missed one rule narrowly; 0 = off."),
        ("Near miss, final ratio", "NEAR_FINAL_REF_RATIO", "S7: VCP-06's final / reference contraction, at most."),
        ("Near miss, tight-area age", "NEAR_TIGHT_MIN_DAYS", "S7: VCP-08's sessions in the final contraction, at least."),
        ("Near miss, tight-area depth", "NEAR_TIGHT_PCT", "S7: VCP-08's final contraction and range, at most this %."),
        ("Near miss, dry-up", "NEAR_DRYUP_RATIO", "S7: VCP-10's tight-area volume x its 50-day, at most."),
        ("Near miss, breakout volume", "NEAR_VOL_MULT", "S7: a full VCP's breakout volume x its 50-day, at least."),
        ("Tight area at the right edge", "TIGHT_AREA_ROUTE", "1 = a final tight area the zig-zag missed is found at "
         "the right edge of the base, once the right side is back in its top quarter; 0 = 1.37's reading."),
        ("Flat base, length", "FLAT_MIN_DAYS", "S6: shortest flat base, in sessions."),
        ("Flat base, length max", "FLAT_MAX_DAYS", "S6: longest flat base, in sessions."),
        ("Flat base, depth", "FLAT_MAX_DEPTH_PCT", "S6: deepest a flat base may be, high to low."),
        ("Flat base, pivot area", "FLAT_PIVOT_DAYS", "S6: sessions before the breakout whose volume must dry "
                                                   "up."),
        ("Flat base, stop area", "FLAT_STOP_DAYS", "S6/S8: sessions before the breakout whose low sets the stop."),
        ("Flat base buy-stop", "FLAT_COIL_ON", "1 = S8 rests a buy-stop at a coiled flat base's high; 0 = off."),
        ("Shakeout", "SHAKEOUT_ON", "1 = S9 buys a base's breakout after a shakeout; 0 = off."),
        ("Shakeout, pullbacks looked at", "SHAKEOUT_LOOKBACK_LEGS", "S9: the last this many pullbacks may hold the shakeout."),
        ("Shakeout, lows undercut", "SHAKEOUT_PRIOR_LEGS", "S9: the shakeout's low is under the lows of this many pullbacks before it."),
        ("Shakeout, volume", "SHAKEOUT_VOL", "S9: the shakeout's volume, at least this x the 50-day average."),
        ("Shakeout, recovery", "SHAKEOUT_RECOVER_DAYS", "S9: sessions within which a close wins those lows back."),
        ("Shakeout, window", "SHAKEOUT_WINDOW", "S9: sessions from the shakeout's low to the breakout, at most."),
        ("Young listings", "YOUNG_LISTING", "1 = a stock listed under a year is judged on its history so far "
                                            "(averages that do not exist yet are waived); 0 = it waits a year (1.27)."),
        ("Young listing, first session", "YOUNG_MIN_BARS", "Sessions listed before a young listing is judged."),
        ("Power play, dry-up", "PP_DRYUP", "PP-06: 1 = the flag's tight area must pass VCP-10's volume test, 0 = off (1.26)."),
        ("Buy range", "BUY_RANGE_PCT", "MV-01b, and the most a fill may sit above the pivot."),
        ("Stop buffer", "STOP_BUFFER_PCT", "SL-01."),
        ("Maximum stop", "MAX_STOP_PCT", "SL-03, checked at the fill."),
        ("Maximum stop, power play", "PP_MAX_STOP_PCT", "SL-03 for MV-05: its stop sits under a flag of up "
         "to {PP_FLAG_MAX_DEPTH_PCT}%."),
        ("Cheat shelf length", "CHEAT_SHELF_DAYS", "Sessions in the shelf a cheat is bought from (MV-03/MV-04)."),
        ("Cheat shelf tightness", "CHEAT_SHELF_PCT", "Widest shelf, high to low, that counts as a cheat."),
        ("Cheat shelf dry-up", "CHEAT_DRYUP", "MV-03/MV-04: 1 = the shelf must pass VCP-10's volume test, 0 = tightness only (1.26)."),
        ("Cheat: rally before the shelf", "CHEAT_RALLY_FRAC", "MV-03/MV-04 (1.34): the share of the decline the rally off the base low must win back before the shelf, which must hold above that low. 0 = no sequence test (1.33)."),
        ("Cheat: volume contraction", "CHEAT_VOL_CONTRACT", "MV-03/MV-04 (1.34): the shelf's average volume as a multiple of the sessions before it, at most. 0 = no contraction test (1.33)."),
        ("Cheat: volume lead-in", "CHEAT_VOL_LOOKBACK", "Sessions before the shelf, at least, that its volume is compared with (the rally from the low when longer)."),
        ("Skip dead sessions", "SKIP_DEAD_BARS", "1.42: 1 = the base and power-play detectors leave out a session with no volume and no range (a data hole filled with the previous price) instead of counting it as a quiet day. 0 = it counts (1.41)."),
        ("Latest base bought", "MAX_BASE_COUNT", "1.44: a base numbered past this in its Stage 2 advance is refused. 0 = numbered, never refused (1.43)."),
        ("Base count: reset", "BASE_COUNT_RESET_DAYS", "Sessions in a row TT-01 to TT-04 must fail to end an advance and restart the count."),
        ("Base count: depth", "BASE_COUNT_MIN_DEPTH_PCT", "Smallest pullback from a high that counts as a base."),
        ("Base count: length", "BASE_COUNT_MIN_DAYS", "Fewest sessions from a base's high to the close that clears it."),
        ("Base count: step", "BASE_COUNT_STEP_PCT", "How far above the last counted base a base's high must be to count as a new one."),
        ("Measured-move target", "MEASURED_MOVE_RR", "1.43: 0 = no projected target and no reward-to-risk test, as "
         "Minervini trades (the stop and the sell rules keep gains larger than losses); 1 = the measured move, capped "
         "by overhead supply, must project MIN_STRUCTURAL_R (1.42)."),
        ("Minimum reward-to-risk", "MIN_STRUCTURAL_R", "Only with MEASURED_MOVE_RR = 1: setups whose measured move projects less are refused — "
                                                 "tested on the signal close and again on the fill."),
        ("Block cheats on VCP-09 bases", "CHEAT_BLOCK_VCP09", "Experiment, off by default: 1 withholds a cheat "
                                                              "when the base's own pivot is below the upper zone."),
        ("Overhead cluster", "OVERHEAD_CLUSTER_ATR", "ATRs above the base high before a swing high caps the target (MEASURED_MOVE_RR = 1 only)."),
        ("Risk per trade", "cfg.risk_pct", "SL-04: share of equity risked per trade (0.01 = 1%)."),
        ("Largest position", "cfg.max_position_pct", "SL-05: share of equity one position may hold."),
        ("Positions", "MAX_POSITIONS", "PF-02, with --spec."),
        ("Breakeven trigger", "BREAKEVEN_R", "EX-03: R gained before the stop moves to breakeven plus costs."),
        ("Entries per base", "MAX_ENTRIES_PER_BASE", "EN-04: how many times one base may be bought — the failure reset. "
                                                      "Above 1, only a stop, breakeven stop or failed 20-day reopens it."),
        ("Part-sale trigger", "PARTIAL_R", "EX-04: R gained before about a third is sold. Pairs with the "
                                           "breakeven trigger, so the gain is banked as the stop moves up."),
        ("Part-sale by trade type", "PARTIAL_BY_SEPA", "EX-04, research switch (0 = every trade): the +R part only from a "
                                                       "company failing SEPA's growth tests on the trade's date; 1 = "
                                                       "ACCEPTABLE / LEADER hold to the trend exit, 2 = NO DATA holds too."),
        ("Failed-breakout window", "FAIL_DAYS", "EX-02: sessions after entry in which a close below the pivot sells (0 = off)."),
        ("20-day failure window", "FAIL_SMA20_DAYS", "EX-02b: sessions after entry in which a close below the 20-day average sells (0 = off)."),
        ("Sell into strength", "STRENGTH_EXT_PCT", "EX-04: % above the 50-day at which a part is sold."),
        ("Part sold into strength", "STRENGTH_FRAC", "EX-04 / EX-05: share of the position sold."),
        ("Climax sells a part", "CLIMAX_IS_PARTIAL", "EX-05: 1 = the strength part only, 0 = everything (1.7)."),
        ("Trend exit needs volume", "TREND_EXIT_NEEDS_VOLUME", "EX-06: 1 = only on above-average volume (1.7)."),
        ("Trend exit closes", "TREND_EXIT_CLOSES", "EX-06: consecutive closes below the 50-day that sell (1 = the first)."),
        ("Loose trend exit after", "TREND_LOOSE_R", "EX-06: once the high reaches this many R, watch the "
         "{TREND_LOOSE_SMA}-day average instead of the 50-day (0 = off)."),
        ("Loose trend exit average", "TREND_LOOSE_SMA", "EX-06: the slower average TREND_LOOSE_R switches to, in sessions."),
        ("Follow-up buy size", "ADD_ON_NEW_BASE", "While held, a breakout of a new base adds this fraction of the first "
         "buy, the stop raised so the position's risk stays the first trade's (0 = off; a research switch)."),
        ("Follow-up buys, most", "ADD_MAX", "Adds at most this many follow-up buys to one position."),
        ("Time stop", "TIME_STOP_DAYS", "EX-07: sessions to reach +1R (0 = off)."),
        ("Light-volume fill exit", "LIGHT_VOLUME_EXIT", "EN-02: sell a buy-stop fill on under-average breakout volume (1 = on)."),
        ("S2 fill needs volume", "S2_FILL_NEEDS_VOLUME", "1.51: an MV-02 close through the pivot on under VOL_MULT x volume does not fill (1); 0 = it fills, and LIGHT_VOLUME_EXIT, while on, sells it at the next open. Independent of LIGHT_VOLUME_EXIT since 1.53."),
        ("Low cheat", "LOW_CHEAT_ENABLED", "MV-03 on (1) or off (0)."),
        ("Results blackout", "EARNINGS_BLACKOUT_DAYS", "Days before results with no new buy."),
        ("Blackout on announcements", "RESULTS_BY_ANNOUNCEMENT", "1.51: the backtest's blackout keys on recorded results announcements (1) or on filing dates only (0)."),
        ("One announcement per quarter", "RESULTS_FIRST_PER_QUARTER", "1.52: a quarter's earliest record is its announcement (1); 0 = every record counts, as in 1.51."),
        ("Preferred uptrend", "SMA200_RISING_PREF_BARS", "W5: sessions over which the 200-day should have risen."),
        ("Preferred uptrend required", "SMA200_PREF_REQUIRED", "1 = W5 holds the plan at WATCH (no new buy); 0 = noted only."),
        ("Turnover floor scales", "SCALE_TURNOVER_FLOOR", "1.45: 1 = the floor is a share of the day's market turnover (the 1,000 most-traded stocks); 0 = the fixed floors below (1.44)."),
        ("Turnover floor, India", "TURNOVER_FLOOR_BP_INR", "Basis points of India's daily market turnover a stock must trade (50-day average volume × close)."),
        ("Turnover floor, US", "TURNOVER_FLOOR_BP_USD", "Basis points of the US daily market turnover a stock must trade."),
        ("Fixed floor, India", "MIN_TURNOVER_INR_CR", "₹ crore a day: the floor with SCALE_TURNOVER_FLOOR = 0, or no market turnover stored; the scaled floor's late-2026 value."),
        ("Fixed floor, US", "MIN_TURNOVER_USD_M", "$ million a day: as the India row."),
        ("Price floor, India (live)", "LIVE_MIN_PRICE_INR", "₹; the live screen only."),
        ("Price floor, US (live)", "LIVE_MIN_PRICE_USD", "$; the live screen only."),
        ("Market filter", "MKT_GUIDE", "1 = the guide's test, 0 = MKT-01 (1.7)."),
        ("Index average", "MKT_INDEX_SMA", "Days in the benchmark's average the close must be above."),
        ("Index average rising over", "MKT_SMA_RISING_DAYS", "Sessions over which that average must have risen (0 = off)."),
        ("Breadth floor", "MKT_BREADTH_MIN_PCT", "% of stocks above their 50-day that counts as healthy."),
        ("Breadth rising over", "MKT_BREADTH_RISING_DAYS", "Sessions over which breadth may instead be rising."),
        ("Leadership window", "MKT_HIGHS_LOWS_DAYS", "Sessions over which new highs must outnumber new lows (0 = off)."),
        ("Leadership ratio", "MKT_HIGHS_LOWS_RATIO", "New highs must exceed this multiple of new lows."),
        ("Segment trend window", "MKT_SEGMENT_MOM_DAYS", "Market filter: the small- and mid-cap index must be up over this "
         "many sessions for new buys (0 = off; a research switch)."),
        ("Segment trend, least", "MKT_SEGMENT_MOM_MIN_PCT", "Market filter: by more than this %."),
        ("Benchmark and breadth tests", "MKT_INDEX_TEST", "Market filter: 1 = the benchmark above its rising average and the "
         "breadth test apply; 0 = they are dropped (a research switch, to test the segment trend alone)."),
        ("Bottoming pilot", "MKT_PILOT", "Research switch (0 = off): while risk-off, buy at the pilot fraction on a "
                                         "bottoming signal; 1 = a follow-through day, 2 = breadth turning up."),
        ("Follow-through: low window", "MKT_FTD_LOW_DAYS", "MKT_PILOT 1: sessions whose lowest close starts a rally attempt."),
        ("Follow-through: earliest day", "MKT_FTD_MIN_DAY", "MKT_PILOT 1: first day of the attempt that can follow through."),
        ("Follow-through: gain", "MKT_FTD_MIN_GAIN_PCT", "MKT_PILOT 1: % the benchmark must close up, on volume above the day before."),
        ("Breadth turning up over", "MKT_PILOT_BREADTH_DAYS", "MKT_PILOT 2: sessions over which breadth must have risen."),
        ("Market filter on", "MKT_FILTER", "Research control: 0 opens every session (no market filter), 1 = the filter."),
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

        The floor replaces the market's own: 50-day average volume x the close, against the floor on the row's
        date (`_min_turnover`: a share of that day's market turnover). Both factors are split-adjusted the same
        way, so the product is the turnover actually traded on that date."""
        floor = _min_turnover(cfg, getattr(last, "name", None))
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
        ycfg = _without_liquidity_floor(cfg)
        for i in range(YOUNG_MIN_BARS - 1, min(len(d), 260)):
            row = d.iloc[i]
            if m.iloc[i] or not is_young_row(row, i + 1):
                continue
            v50, close = row.get("vol_sma50"), row.get("close")
            if pd.isna(v50) or pd.isna(close) or float(v50) * float(close) < _min_turnover(cfg, row.name):
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
        # S7: a base that missed one graded rule narrowly (vcp_spec `near`), breaking out the same way
        near_break = bool(NEAR_MISS and prev.get("near_ok") and prev.get("pivot")
                          and prev_close <= prev["pivot"] < close)
        base = prev if (breakout or near_break) else today
        miss, vol_ratio, upper = entry_misses(close, high, low, vol, v50, base["pivot"] if (breakout or near_break) else None)
        confirmed = {"W1": miss["W1"], "W2": breakout and miss["W2"], "W3": miss["W3"]}
        mv01 = breakout and not any(confirmed.values())
        near, near_why = False, None
        if near_break and not any(miss.values()):
            near, near_why = True, f"{prev['near']['rule']}: {prev['near']['why']}"
        elif (NEAR_MISS and breakout and confirmed["W1"] and not confirmed["W2"] and not confirmed["W3"]
              and vol_ratio >= NEAR_VOL_MULT):
            near, near_why = True, (f"MV-01a: breakout volume {vol_ratio:.2f}x its 50-day average "
                                    f"(needs {VOL_MULT:g}x)")
        if near_why:
            e["near_miss"] = near_why
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
        result.setups[NEAR] = near
        # S6, the flat base: yesterday's base, if it never became a VCP, is shallow and four to seven
        # weeks long, and today closes through its high with the MV-01 conviction tests.
        flat = False
        fb = flat_base(prev, d.iloc[:-1])
        if fb is not None:
            fh = fb["pivot"]
            e.update(flat_pivot=fh, flat_low=fb["low"], flat_depth_pct=fb["depth"], flat_dryup=fb["dry"],
                     flat_quiet_days=fb["quiet"], flat_base_date=fb["base_date"])
            flat = bool(prev_close <= fh < close and vol_ratio >= VOL_MULT and upper >= UPPER_HALF
                        and close <= fh * (1 + BUY_RANGE_PCT / 100) and fb["dried"])
        result.setups[FLAT] = flat
        # S8: today's base qualifies as a flat base (the S6 tests, on today's bar instead of yesterday's) and the
        # close sits within COIL_PCT below its high: a buy-stop above the high, as MV-02 rests above a VCP's pivot
        flat_coil = False
        fc = flat_base(today, d) if FLAT_COIL_ON and not flat and not mv01 and not mv02 else None
        if fc is not None and fc["pivot"] * (1 - COIL_PCT / 100) <= close <= fc["pivot"] and fc["dried"]:
            flat_coil = True
            e.update(flat_pivot=fc["pivot"], flat_low=fc["low"], flat_depth_pct=fc["depth"], flat_dryup=fc["dry"],
                     flat_quiet_days=fc["quiet"], flat_base_date=fc["base_date"])
        result.setups[FLAT_COIL] = flat_coil
        # S9: yesterday's base had a shakeout (undercut on volume, reclaimed), and today closes through the base's
        # highest high with MV-01's tests -- the dry-up and tight area of a VCP are not asked of it
        shake = False
        if (SHAKEOUT_ON and not (mv01 or near or flat) and prev.get("bh") and prev.get("bh_date") is not None
                and prev["fail"] not in ("VCP-01", "VCP-02", "VCP-03", "VCP-05")):
            so = shakeout(prev, d.iloc[:-1])
            if so is not None and prev["bh_date"] in d.index:
                b0 = d.index.get_loc(prev["bh_date"])
                sp = float(d["high"].iloc[b0:-1].max())     # the base's highest high, through yesterday
                m, _, _ = entry_misses(close, high, low, vol, v50, sp)
                if prev_close <= sp < close and not any(m.values()):
                    shake = True
                    e.update(shake_pivot=sp, shake_low=low, shake_base_date=str(prev["bh_date"].date()),
                             shake_date=str(so["date"].date()), shake_undercut_low=so["low"],
                             shake_vol_ratio=round(so["vol_ratio"], 2))
        result.setups[SHAKE] = shake
        if pp_ok:
            ctx.extras.update(pp_pivot=pp_prev["pivot"], pp_tight_low=pp_prev["tight_low"],
                              # a STRING, like base_date above: ctx.extras is serialised to JSON
                              # for the signal's meta, and a pandas Timestamp is not serialisable
                              pp_flag_high_date=(str(pp_prev["flag_high_date"].date())
                                                 if pp_prev.get("flag_high_date") is not None else None),
                              pp_run_pct=round(pp_prev["run_pct"], 1) if pp_prev.get("run_pct") else None,
                              pp_flag_days=pp_prev.get("flag_days"), pp_flag_high=pp_prev.get("flag_high"))

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
        # 1.41: the overhead supply that caps the target (build_plans) is read here, from the full daily and
        # weekly frames, and stored with the signal. A signal-cache hit rebuilds the context from 70 daily bars
        # and no weekly frame (backtest._cached_ctx), so reading the frames in build_plans gave a cache hit a
        # different plan from a fresh scan -- SSNC 2017-04-18 refused fresh at 0.85R, bought from the cache at
        # 2.03R. Only on a bar that reaches the plan, so the row stays small everywhere else.
        if OVERHEAD_YEARS and result.hard_gates_passed and result.has_setup:
            e["plan_overhead"] = sw.overhead_levels(d, ctx.weekly, None, ctx.h_value,
                                                    weekly_bars=52 * OVERHEAD_YEARS)
        # 1.44, the base count (base_number), as of this session, on the bars that reach the plan: the base's
        # number in its Stage 2 advance, for the VCP base and the flat base. Here, not in build_plans, for the
        # reason plan_overhead is: a signal-cache hit rebuilds the context from 70 bars, too few to see the advance.
        if result.hard_gates_passed and result.has_setup:
            for k, col in (("base_date", "base_number"), ("flat_base_date", "flat_base_number"),
                           ("shake_base_date", "shake_base_number")):
                if e.get(k) and pd.Timestamp(e[k]) in d.index:
                    e[col] = base_number(d, int(d.index.get_loc(pd.Timestamp(e[k]))))["n"]
        return result

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """MV-01 is bought at the next open, MV-02 by a resting buy-stop: both place an order today."""
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        if result.setups.get(MV01):
            return 2.0
        if result.setups.get(MV02) or result.setups.get(NEAR):
            return 1.0
        # a cheat is a lower-confidence entry than the pivot buy, and the low cheat
        # lower than the 3C -- he describes it as the riskiest of the three
        if result.setups.get(FLAT) or result.setups.get(FLAT_COIL) or result.setups.get(SHAKE):
            return 1.0
        return 0.8 if result.setups.get(MV04) else (0.6 if result.setups.get(MV03) else 0.0)

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        cheat = result.setups.get(MV03) or result.setups.get(MV04)
        power = result.setups.get(MV05)
        flat = (result.setups.get(FLAT) or result.setups.get(FLAT_COIL)) and not (
            result.setups.get(MV01) or result.setups.get(MV02) or result.setups.get(NEAR))
        if flat:
            # S6: the pivot is the base's own high, the stop under the low of the sessions before the
            # breakout, and the objective the base's depth added to the price paid
            fp, fl, fd = e.get("flat_pivot"), e.get("flat_low"), e.get("flat_depth_pct")
            if not fp or fl is None or pd.isna(fl):
                return PlanChoice(None, None, "missing flat-base pivot")
            cheat = power = False
        shake = bool(result.setups.get(SHAKE)) and not (flat or result.setups.get(MV01) or result.setups.get(MV02)
                                                         or result.setups.get(NEAR))
        if shake:
            cheat = power = False
        # A power play has no base, so its pivot and stop come from the FLAG, not from
        # e["pivot"]/e["tight_low"] -- which are None for it, since the base path rejected it.
        pivot, tl = ((e.get("pp_pivot"), e.get("pp_tight_low")) if power
                     else (e.get("pivot"), e.get("tight_low")))
        # Only the pivot buy needs the FINAL tight area. A cheat is taken while the
        # base is still forming, so that area does not exist yet -- requiring it here
        # rejected 122 of 133 cheats before they reached their own branch.
        if not cheat and not flat and not shake and (not pivot or tl is None or pd.isna(tl)):
            return PlanChoice(None, None, "missing pivot / tight low")
        if flat:
            setup, pivot = (FLAT, float(fp)) if result.setups.get(FLAT) else (FLAT_COIL, float(fp))
            # S6 is confirmed by the close and bought at the next open; S8 rests a buy-stop at the high
            entry = float(ctx.close) if setup == FLAT else pivot_buy_stop(pivot, cfg.tick_size)
            stop = pivot_stop(fl, cfg.tick_size)
        elif shake:
            # S9: the base's highest high is the pivot; bought at the next open after the close through it, and
            # stopped under the breakout session's low (the shakeout's own low is far below the buy)
            setup, pivot = SHAKE, float(e["shake_pivot"])
            entry = float(ctx.close)
            stop = pivot_stop(e["shake_low"], cfg.tick_size)
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
            setup = MV01 if result.setups.get(MV01) else NEAR if result.setups.get(NEAR) else MV02
            # MV-01 (and S7, the same breakout) fills at tomorrow's open, whose best estimate today is the
            # close; MV-02 at the buy-stop
            entry = float(ctx.close) if setup in (MV01, NEAR) else pivot_buy_stop(pivot, cfg.tick_size)
            stop = pivot_stop(tl, cfg.tick_size)
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        # the base count (1.44): a late-stage base is refused. A power play has no base, so no number.
        n = (None if power else e.get("flat_base_number") if flat else e.get("shake_base_number") if shake
             else e.get("base_number"))
        if MAX_BASE_COUNT and n and n > MAX_BASE_COUNT:
            return PlanChoice(None, None, f"late-stage base: the {_ordinal(n)} of its advance "
                                          f"(at most the {_ordinal(MAX_BASE_COUNT)})")
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
            # No base, so no base-depth measured move: the run into the flag is the structure, and its
            # size projected from the buy is the objective (power_measured_move). The flag's tight range,
            # used until 1.36, is the stop's own distance, so it could never clear 2R.
            measured_move = power_measured_move(e.get("pp_flag_high"), e.get("pp_run_pct"))
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
        # the levels evaluate() stored (plan_overhead), never the frames: a cache hit has no weekly frame
        overhead = e.get("plan_overhead") if OVERHEAD_YEARS else ctx.overhead
        if overhead is None:
            if MEASURED_MOVE_RR:
                return PlanChoice(None, None, "missing overhead levels")
            overhead = []
        nearest_above = sw.nearest_overhead_above(ceiling_from, overhead)  # reported, not binding
        binding = overhead_binding(entry, bh, ctx.atr, overhead)
        if binding is not None and binding < target:
            target = binding
        ctx.extras["overhead_caps_target"] = bool(binding is not None and binding < entry + measured_move) \
            if measured_move == measured_move else None
        structural_r = (target - entry) / risk if risk > 0 else float("nan")
        ctx.extras["structural_r"] = round(structural_r, 2) if structural_r == structural_r else None
        ctx.extras["measured_move"] = round(measured_move, 2) if measured_move == measured_move else None

        # MEASURED_MOVE_RR = 1 (1.42): the measured move, capped by overhead supply, must project at least
        # MIN_STRUCTURAL_R -- a setup projecting less is skipped, never padded up. 0 (Minervini): no projected
        # target; the measured move is still recorded (extras) for study, but decides nothing.
        if MEASURED_MOVE_RR and not (structural_r >= MIN_STRUCTURAL_R):
            return PlanChoice(
                None, None,
                f"projects only {structural_r:.2f}R against the {MIN_STRUCTURAL_R:g}:1 minimum",
            )
        if not MEASURED_MOVE_RR:
            target = entry + PARTIAL_R * risk     # the first managed step (EX-03/EX-04), not a sell order

        plan = TradePlan(plan="MV", setup=setup, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry,
                         r_multiple=round((target - entry) / risk, 2),
                         nearest_overhead_above_entry=nearest_above)
        return PlanChoice(plan, None,
                          f"{setup}: pivot {pivot:.2f}, stop {(entry - stop) / entry * 100:.1f}% "
                          f"below entry, " + (f"projects {structural_r:.2f}R" if MEASURED_MOVE_RR else
                                              f"measured move {structural_r:.2f}R (not a gate)"))

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
        elif plan.setup in (FLAT, FLAT_COIL):
            pivot, tl = float(e["flat_pivot"]), float(e["flat_low"])
        elif plan.setup == SHAKE:
            pivot, tl = float(e["shake_pivot"]), float(e["shake_low"])
        else:
            pivot, tl = float(e["pivot"]), float(e["tight_low"])
        # EN-04 ("one entry per base") keys on `base_id`, and a power play has no base -- so
        # without an id of its own it would be the one setup that could be re-entered on the same
        # structure after a stop-out, which is exactly what EN-04 exists to stop. The flag high's
        # date identifies the flag the way the base start identifies a base.
        base_id = (e.get("pp_flag_high_date") if plan.setup == MV05
                   else e.get("flat_base_date") if plan.setup in (FLAT, FLAT_COIL) else e.get("shake_base_date") if plan.setup == SHAKE else e.get("base_date"))
        meta = {"pivot": pivot, "tight_low": tl, "max_fill": pivot * (1 + BUY_RANGE_PCT / 100),
                "max_risk_pct": max_stop_pct(plan.setup) / 100, "base_id": base_id,
                "max_entries_per_base": MAX_ENTRIES_PER_BASE,
                "min_structural_r": MIN_STRUCTURAL_R if MEASURED_MOVE_RR else None,
                "tightness": e.get("tightness_pct")}
        if plan.setup == MV01:
            meta.update(order="open", min_open=tl)
        elif plan.setup == FLAT_COIL:
            # S8 fills INTRADAY at the buy-stop (or the open, on a gap through it): buying at the pivot is its
            # whole point. MV-02 waits for the close instead because a poke-through that closes back under the
            # pivot was a fast loser (India, 9 of 14); S8 is a setup of its own so the two can be compared, and
            # a fill on light breakout volume is still sold at the next open.
            meta.update(order="stop", cancel_close_below=tl)
            if LIGHT_VOLUME_EXIT:
                meta["min_breakout_vol"] = VOL_MULT
        elif plan.setup == MV02:
            meta.update(order="stop", cancel_close_below=tl, confirm_close_above=pivot)
            if LIGHT_VOLUME_EXIT:
                # the guide's buy-stop is valid only if the breakout day's volume reaches
                # VOL_MULT x the 50-day average by the close (portfolio_sim, entry day)
                meta["min_breakout_vol"] = VOL_MULT
            if S2_FILL_NEEDS_VOLUME:
                # 1.51: the fill IS that close, so a light one does not fill and the order keeps resting.
                # Its own switch, not nested under LIGHT_VOLUME_EXIT: a LIGHT_VOLUME_EXIT=0 variant
                # otherwise also let S2 fill on light closes, and measured two changes as one.
                meta["fill_min_vol"] = VOL_MULT
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
        elif plan.setup == FLAT_COIL:
            label, reasons = "TRADE_ON_TRIGGER", ["flat base coiled under its high: buy-stop through it, "
                                                  "stopped under the low of the last sessions"]
        elif plan.setup == SHAKE:
            label, reasons = "TRADE_ON_TRIGGER", [f"shakeout: undercut on {ctx.extras.get('shake_date')} and reclaimed, "
                                                  "closed through the base's high; buy at the next open, stopped "
                                                  "under today's low"]
        elif plan.setup == NEAR:
            label, reasons = "TRADE_ON_TRIGGER", [f"near miss: a breakout like MV-01 out of a base that missed "
                                                  f"one rule narrowly ({ctx.extras.get('near_miss')}); buy at "
                                                  "the next open"]
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
        if risk_pct > max_stop_pct(plan.setup):
            label = "WATCH_WAIT"
            reasons.append(f"stop {risk_pct:.1f}% below entry exceeds the {max_stop_pct(plan.setup):g}% maximum")
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
        # from the session the strategy first judges a stock: a young listing at YOUNG_MIN_BARS (the detector waives
        # the history it lacks), else once VCP-01's advance can be measured. Drawn from the later point only, a new
        # listing's first months showed nothing the strategy traded in them (DMART.NS, bought 2017-07-04, listed
        # that March)
        start = min(2 * VCP.swing_k + VCP.prior_window, YOUNG_MIN_BARS if YOUNG_LISTING else 10 ** 9)
        ov = overhead_at(daily)
        dets = [None] * len(daily)
        for i in range(start, len(daily)):
            dets[i] = vcp_spec.detect(daily.iloc[: i + 1], VCP)
        close = daily["close"].to_numpy(float)
        bases: dict = {}
        for i in range(start, len(daily)):
            r = dets[i]
            if r["bh_date"] is None or not (r["ok"] or r["fail"] in self._VCP_RANK):
                continue
            # A base whose pivot is already under the close is not one a breakout can still come from: the
            # price went through while the detector measured an older base, and the breakout's high is not
            # a confirmed swing yet. ADANIPORTS.NS closed 4.4% through its pivot on 2015-08-14, read against
            # the base from 2015-01-09; for the next three sessions the detector measured the same pivot
            # from a 2015-05-22 high, and that base was drawn as a VCP still waiting for it.
            if r.get("pivot") and close[i] > r["pivot"]:
                continue
            b = bases.setdefault(r["bh_date"], {"best": i, "ok": [], "breakout": None, "cheat": None})
            done = r["ok"] or (NEAR_MISS and r.get("near_ok"))      # S7: a near miss is drawn as complete
            if done:
                b["ok"].append(i)
            rank = 99 if done else self._VCP_RANK[r["fail"]]
            best = dets[b["best"]]
            if rank >= (99 if (best["ok"] or (NEAR_MISS and best.get("near_ok"))) else self._VCP_RANK[best["fail"]]):
                b["best"] = i
        # MV-01's breakout: yesterday complete, and today's close through yesterday's frozen pivot.
        # The breakout bar itself may already sit in a new base (the decisive close resets BH), so
        # it is found from the bar before it.
        #
        # Only a crossing that passes MV-01's own tests (entry_misses) is the breakout; one that fails them
        # is recorded as `crossed` with why, so the chart never marks "broke out" on a session the strategy
        # would not have bought. TSLA's June 2020 power play was drawn as broken out on a close 6.5% past its
        # pivot on 0.91x volume. The setup is still judged from the bar before the crossing.
        #
        # A refused crossing does not use the base up: evaluate judges every close through the pivot afresh,
        # so a later one may still be bought, and only a crossing the strategy would buy ends the search.
        # ADANIPORTS.NS's January 2015 base crossed on 2015-02-27 on 1.13x volume (refused) and again on
        # 2015-08-14, which was never judged. And MV-01 is decided only on a bar that passes the screen --
        # the Trend Template, as the strategy's prefilter applies it on the signal bar -- so a crossing on a
        # bar that fails it is refused, naming why (that 2015-08-14 close: 50-day under the 150-day).
        hi_, lo_, vo_ = (daily[k].to_numpy(float) for k in ("high", "low", "volume"))
        v50_ = daily["vol_sma50"].to_numpy(float) if "vol_sma50" in daily else np.full(len(daily), np.nan)
        for i in range(start + 1, len(daily)):
            p = dets[i - 1]
            near_base = bool(p and NEAR_MISS and p.get("near_ok"))
            b = bases.get(p["bh_date"]) if p else None
            if b is not None and (p["ok"] or near_base) and close[i - 1] <= p["pivot"] < close[i] \
                    and (b["breakout"] is None or b.get("missed")):
                miss, vr, up = entry_misses(close[i], hi_[i], lo_[i], vo_[i], v50_[i], p["pivot"])
                screen = self._screen_miss(cfg, daily, i)
                b["breakout"], b["screen"] = i, screen
                b.pop("near", None)
                if screen:
                    b["missed"] = f"the stock failed the strategy's screen that session -- {screen}"
                    continue
                # S7, as evaluate decides it: a near-miss base with every MV-01 test passed, or a full VCP
                # whose breakout volume alone is short by no more than NEAR_VOL_MULT
                vol_near = (NEAR_MISS and p["ok"] and miss["W1"] and not miss["W2"] and not miss["W3"]
                            and vr >= NEAR_VOL_MULT)
                if vol_near:
                    bases[p["bh_date"]]["near"] = (f"MV-01a: breakout volume {vr:.2f}x its 50-day average "
                                                   f"(needs {VOL_MULT:g}x)")
                    bases[p["bh_date"]]["missed"] = None
                else:
                    if near_base:
                        bases[p["bh_date"]]["near"] = f"{p['near']['rule']}: {p['near']['why']}"
                    bases[p["bh_date"]]["missed"] = (entry_misses_text(miss, vr, up, close[i], p["pivot"])
                                                     if any(miss.values()) else None)
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
        #
        # And first on a session that passes the screen: evaluate never sees a session the prefilter drops,
        # so a cross there is refused without spending the base's entry, and a later cross may be bought.
        # The refused one is kept only while no other turns up, so the card can say why it was skipped.
        for i in range(start + 1, len(daily)):
            p = dets[i - 1]
            b = bases.get(p["bh_date"]) if p else None
            if b is not None and (b.get("cheat") is None or b.get("cheat_refused")):
                z = cheat_cross(p, close[i - 1], close[i])
                if z:
                    refused = self._screen_miss(cfg, daily, i) is not None
                    if b.get("cheat") is None or not refused:
                        b["cheat"], b["cheat_refused"] = (i, z, p), refused
        # A cheat the strategy REFUSED: a close through yesterday's shelf high, in the lower (when LOW_CHEAT_ENABLED)
        # or middle third and below the base high, on a shelf that failed one of its own tests. Never a trade: it is
        # drawn as a note on its base (`_cheat_refused`), so the chart shows the pattern was seen and which rule
        # stopped it. Minervini's own AMZN 3-C of 2002-10-10 was invisible here: the base read only "not a VCP".
        # Only after the turn a cheat needs (a higher low, then a rally of CHEAT_RALLY_FRAC of the decline): before
        # it, a close through a shelf is a bounce in a falling base, not a cheat attempt (AMZN's June 2002 bounce
        # failed all four tests). Every attempt is kept, the latest three drawn -- one alone hid the rest: AMZN's
        # base tried on 9 Sep 2002, missing only the width (8.2% against 8%), and on 10 Oct, the one Minervini
        # bought, missing three. An attempt is the first close of a run (consecutive up days each clear a new shelf
        # high). Only on a base no cheat was taken from, and drawn only on a base with no entry of its own.
        for i in range(start + 1, len(daily)):
            p = dets[i - 1]
            b = bases.get(p["bh_date"]) if p else None
            if b is None or b.get("cheat") is not None or p.get("cheat_ok") or not p.get("cheat_misses"):
                continue
            zone, piv = p.get("cheat_zone"), p.get("cheat_pivot")
            turned = p.get("cheat_higher_low") and (p.get("cheat_rally") or 0) >= CHEAT_RALLY_FRAC
            if turned and piv is not None and piv < p["bh"] \
                    and (zone == "mid" or (zone == "low" and LOW_CHEAT_ENABLED)) and close[i - 1] <= piv < close[i]:
                # a run of up days crosses a new shelf high every session: the first of the run is the attempt
                if b.get("cheat_miss_at") != i - 1:
                    b.setdefault("cheat_miss", []).append((i, p))
                b["cheat_miss_at"] = i
        last = len(daily) - 1
        live = dets[last]["bh_date"] if last >= start and dets[last]["bh_date"] in bases else None
        fills = [pd.Timestamp(a["entry"]) for a in (anchors or []) if a.get("entry")]
        ts = lambda i: daily.index[i]  # noqa: E731
        # The cheat a run bought is the one crossed on the bar before its fill (signal on the close, bought
        # the next session) -- by the same cheat_cross test, so it can be a later shelf than the base's
        # first: when the first cross was not entered (no slot, refused), EN-04's one entry per base is
        # still unspent, and the run takes a later one.
        # S9 and the flat base (S6 / S8) are drawn by their own passes. A run's fill one of them explains -- its
        # date AND its initial stop (`_run_bought`) -- is theirs: no cheat claims it below, and it is not drawn
        # again as a base judged on its signal bar (INFY.NS 2020-09-15, an S8 fill, was also claimed by a cheat
        # crossed the session before it).
        out = self._shakeouts(daily, cfg, dets, start, anchors or []) + self._flats(daily, cfg, dets, start, anchors or [])
        own_fills = {s["_fill"] for s in out if s.get("_fill") is not None}
        for s in out:
            s.pop("_fill", None)
        fills = [f for f in fills if f not in own_fills]
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
        # The base count, as the strategy counts it (`base_number`, as of each base's high)
        adv = advances(daily)

        def count_of(key) -> dict | None:
            return None if key is None else base_number(daily, int(daily.index.get_loc(key)), adv)

        for key, b in bases.items():
            bo = b["breakout"]
            ch = signalled.get(key) or b["cheat"]
            if ch and fills and (key in signalled or traded_cheat(ch, bo)):
                # the run bought the cheat: draw that trade, from the base as it stood the bar before the cross
                out.append(self._setup(daily, cfg, dets[ch[0] - 1], ch[0] - 1, None, ch, False, traded_cheat=True, ov=ov,
                                       count=count_of(key)))
                out[-1]["anchored"] = True
                continue
            so = self._cheat_stop_out(daily, cfg, ch, bo) if ch else None
            now = key == live and bo is None   # still forming today: judge it as today's screen does
            bought = None
            if so is not None:
                bought = self._setup(daily, cfg, dets[ch[0] - 1], ch[0] - 1, None, ch, False, traded_cheat=True, ov=ov,
                                     count=count_of(key))
                if not bought["title"].startswith("Cheat entry · stopped out"):
                    bought = None   # a cheat the strategy would skip (risk, R) was never bought: nothing stopped out
            if bought is not None:
                # The cheat was bought and stopped out. That trade is its own setup, drawn as the base stood
                # the bar before the cheat and ending at the stop-out -- not judged on today's bar, where the
                # decline after the stop reads as a broken trend and a base far too deep, beside a cheat whose
                # checks were all taken before it (AXSM, 2026-09). What the base did after is a second setup,
                # only when there is one: EN-04 lets a shakeout re-open it (MAX_ENTRIES_PER_BASE), through a
                # later cheat or the breakout, and a base still forming is judged today as usual.
                out.append(bought)
                again = None
                for i in range(so + 1, len(daily)):
                    p = dets[i - 1]
                    z = cheat_cross(p, close[i - 1], close[i]) if p and p["bh_date"] == key else None
                    if z:
                        again = (i, z, p)
                        break
                if again is None and bo is None and not now:
                    continue
                ch = again
            rep = last if now else bo - 1 if bo is not None else b["ok"][-1] if b["ok"] else b["best"]
            out.append(self._setup(daily, cfg, dets[rep], rep, bo, ch, now, missed=b.get("missed"), near=b.get("near"), ov=ov,
                                   count=count_of(key)))
            # only on a base that gives no entry of its own: beside a VCP's buy or a cheat it only adds noise
            if ch is None and b.get("cheat_miss") and not any(z["key"] in ("entry", "cheat") for z in out[-1]["zones"]):
                for n, (i, p) in enumerate(b["cheat_miss"][-3:]):
                    self._cheat_refused(out[-1], daily, i, p, n)
        out += self._power_plays(daily, cfg)
        # A drawn breakout (S1, S2, S7, a power play) the selected run bought: the fill the session after it (at the
        # open) or on it (S2's buy-stop, filled on the close through), with the run's initial stop (`_run_bought`).
        # Until this, only a cheat was tied to the run's trade, so a run's near-miss or power-play fill drew beside
        # a base judged on its signal bar and the chart picked that one (DDD 2013-05-31, CRK 2018-07-12).
        explained = set(own_fills)
        for s_ in out:
            if s_.get("anchored") or not s_.get("breakout") or not anchors:
                continue
            st = next((sh["price"] for z in s_.get("zones", []) for sh in z.get("shapes", [])
                       if sh.get("shape") == "level" and sh.get("role") == "stop"), None)
            k = int(daily.index.get_loc(pd.Timestamp(s_["breakout"])))
            hit = next((i for i in (k + 1, k) if st is not None and self._run_bought(daily, anchors, i, st)), None)
            if hit is not None:
                s_["anchored"] = True
                explained.add(daily.index[hit])
        for s_ in out:
            if s_.get("anchored") and s_.get("kind") not in ("fail", "young"):
                explained.update(f for f in fills if s_["base_from"] <= str(f.date()) <= s_["to"])
        # A run's fill that today's rules see no entry for -- no cheat crossed the bar before it, no breakout
        # just before it: a run of an older version bought what these rules no longer take. Drawn as the base
        # stood on the signal bar, so the trade sits in the setup it was bought from rather than in the base
        # as it looked months later (ANANDRATHI.NS, a 1.22 cheat bought 2025-12-26, drew inside a base judged
        # in March 2026, its entry zone and shelf nowhere near the buy).
        for f in fills:
            j = int(daily.index.searchsorted(f)) - 1          # the signal bar: the session before the fill
            if j < start or j >= len(daily):
                continue
            if f in explained:
                continue
            # an MV-02 buy-stop placed days before the fill, from a base complete then and re-measured since
            # (DELTACORP.NS: placed 2013-12-03 under a 93.95 pivot, it poked through twice and closed back, then
            # filled on 2013-12-13's close, by when the base read as failing VCP-06): the bar that placed it
            from ..backtesting.portfolio_sim import PENDING_EXPIRY_BDAYS
            placed = next((i for i in range(j, max(start, j - PENDING_EXPIRY_BDAYS) - 1, -1)
                           if (dets[i]["ok"] or (NEAR_MISS and dets[i].get("near_ok"))) and dets[i].get("tight_low")
                           and self._run_bought(daily, anchors, j + 1, pivot_stop(dets[i]["tight_low"], cfg.tick_size))), None)
            if placed is not None:
                s_ = self._setup(daily, cfg, dets[placed], placed, None, None, False, ov=ov, count=count_of(dets[placed]["bh_date"]))
                s_["anchored"] = True
                s_["summary"] = (f"Drawn as the base stood on {ts(placed).date()}, when the buy-stop the selected run filled "
                                 f"on {f.date()} was placed. " + s_["summary"])
                fill_to = str(ts(min(len(daily) - 1, j + 1 + TIME_STOP_DAYS)).date())
                s_["to"] = max(s_["to"], fill_to)
                s_["frame"]["to"] = max(s_["frame"]["to"], fill_to)
                out.append(s_)
                continue
            p = dets[j]
            # a breakout's close resets the base it broke out of (MV-01 is judged from the bar before), so a signal
            # bar showing no base yet is drawn as the base stood the session before it
            if p["fail"] in ("VCP-01", "VCP-02") and j - 1 >= start and dets[j - 1]["fail"] not in ("VCP-01", "VCP-02"):
                j, p = j - 1, dets[j - 1]
            key = p["bh_date"]
            if key is None or key in signalled:
                continue
            bo = bases.get(key, {}).get("breakout")
            if bo is not None and 0 <= j - bo <= 3:           # the breakout itself: drawn by the base
                continue
            s_ = self._setup(daily, cfg, p, j, None, None, False, ov=ov, count=count_of(key))
            s_["anchored"] = True
            s_["summary"] = (f"Drawn as the base stood on {ts(j).date()}, the session before the selected run "
                             f"bought it; today's rules: " + s_["summary"][0].lower() + s_["summary"][1:])
            fill_to = str(ts(min(len(daily) - 1, j + 1 + TIME_STOP_DAYS)).date())
            s_["to"] = max(s_["to"], fill_to)
            s_["frame"]["to"] = max(s_["frame"]["to"], fill_to)
            out.append(s_)
        return sorted(out, key=lambda x: x["base_from"] or x["from"])

    @staticmethod
    def _run_bought(daily: pd.DataFrame, anchors: list, fill_i: int, stop: float) -> bool:
        """Did the selected run fill on bar `fill_i` with this initial stop (within 0.5%, the chart eval's
        tolerance)? A fill date alone is not enough: two setups can fill on one session, and the run's stop
        says which order it was (an S8 placed days earlier, or an S6 or S9 confirmed the session before)."""
        if fill_i >= len(daily):
            return False
        f = daily.index[fill_i]
        for a in anchors:
            if a.get("entry") and pd.Timestamp(a["entry"]) == f:
                st = a.get("stop")
                if st is None or (st and abs(float(stop) / float(st) - 1) <= 0.005):
                    return True
        return False

    def _shakeouts(self, daily: pd.DataFrame, cfg: MarketConfig, dets: list, start: int, anchors: list) -> list[dict]:
        """S9 on the chart: each base's shakeout breakout, by evaluate's own test -- the bar before has a
        `shakeout` (an undercut of earlier pullback lows on volume, won back), and this bar closes through the
        base's highest high passing MV-01's `entry_misses`, on a session that passes the screen. `dets` are
        bases_live's per-bar detections (evaluate's `prev` is the same detect on the bar before). The first
        crossing a base's shakeout makes that the strategy would buy ends that base's search, as EN-04's one
        entry does; a refused one is kept only while no other turns up, so the card can say why. A crossing
        that is also MV-01's or S7's breakout is that setup's, drawn by the base, as evaluate gives them
        precedence (S6, the flat base, is not re-tested here). Each carries `_signal`, its bar, for bases_live."""
        if not SHAKEOUT_ON:
            return []
        close, hi_, lo_, vo_ = (daily[k].to_numpy(float) for k in ("close", "high", "low", "volume"))
        v50_ = daily["vol_sma50"].to_numpy(float) if "vol_sma50" in daily else np.full(len(daily), np.nan)
        def test(i: int) -> dict | None:
            """S9 on bar i, or None: the shakeout breakout as evaluate decides it, `missed` saying why it is refused."""
            p = dets[i - 1]
            if not (p and p.get("bh") and p.get("bh_date") is not None) or p["fail"] in ("VCP-01", "VCP-02", "VCP-03", "VCP-05"):
                return None
            if (p["ok"] or (NEAR_MISS and p.get("near_ok"))) and p.get("pivot") and close[i - 1] <= p["pivot"] < close[i]:
                return None
            b0 = int(daily.index.get_loc(p["bh_date"]))
            sp = float(hi_[b0:i].max())            # the base's highest high, through the bar before
            if not (close[i - 1] <= sp < close[i]):
                return None
            so = shakeout(p, daily.iloc[:i])
            if so is None:
                return None
            miss, vr, up = entry_misses(close[i], hi_[i], lo_[i], vo_[i], v50_[i], sp)
            screen = self._screen_miss(cfg, daily, i)
            missed = (f"the stock failed the strategy's screen that session -- {screen}" if screen
                      else entry_misses_text(miss, vr, up, close[i], sp) if any(miss.values()) else None)
            return {"key": p["bh_date"], "i": i, "b0": b0, "sp": sp, "so": so, "missed": missed}

        found: dict = {}
        for i in range(start + 1, len(daily)):
            p = dets[i - 1]
            got = found.get(p["bh_date"]) if p else None
            if got is not None and not got["missed"]:
                continue
            g = test(i)
            if g is not None and (got is None or not g["missed"]):
                found[g["key"]] = g
        # a run's S9 fill on a later crossing than the base's first (the run skipped the first for a reason of
        # its own): the crossing the session before the fill, when its stop is the run's
        for a in anchors:
            k = int(daily.index.searchsorted(pd.Timestamp(a["entry"]))) if a.get("entry") else -1
            if not (start + 1 < k < len(daily)) or daily.index[k] != pd.Timestamp(a["entry"]):
                continue
            g = test(k - 1)
            if g is not None and not g["missed"] and \
                    self._run_bought(daily, anchors, k, pivot_stop(float(lo_[k - 1]), cfg.tick_size)):
                found[g["key"]] = g
        out = []
        for g in found.values():
            traded = self._run_bought(daily, anchors, g["i"] + 1, pivot_stop(float(daily["low"].iloc[g["i"]]), cfg.tick_size))
            s = self._shake_setup(daily, cfg, g["b0"], g["i"], g["sp"], g["so"], g["missed"])
            s["anchored"] = traded
            s["_fill"] = daily.index[g["i"] + 1] if traded else None
            out.append(s)
        return out

    def _shake_setup(self, daily: pd.DataFrame, cfg: MarketConfig, b0: int, i: int, sp: float, so: dict,
                     missed: str | None) -> dict:
        """One S9 for the chart, in `_setup`'s shape: the base from its high, the shakeout under the earlier
        lows and its recovery, and the entry build_plans places -- bought at the next open after the close
        through the base's high, stopped under that session's low (`pivot_stop`): an illustration, as for a VCP."""
        idx = daily.index
        day = lambda k: str(idx[k].date())   # noqa: E731
        px = lambda v: f"{v:,.2f}"           # noqa: E731
        close, lows = daily["close"].to_numpy(float), daily["low"].to_numpy(float)
        lo_i = int(idx.get_loc(so["date"]))
        rec = next((k for k in range(lo_i + 1, min(len(daily), lo_i + 1 + SHAKEOUT_RECOVER_DAYS)) if close[k] > so["prior_low"]), lo_i)
        under = (so["prior_low"] - so["low"]) / so["prior_low"] * 100
        depth = (sp - float(lows[b0:i].min())) / sp * 100
        buy, stop = float(close[i]), pivot_stop(float(lows[i]), cfg.tick_size)
        risk = buy - stop
        risk_pct = risk / buy * 100 if buy > 0 else float("nan")
        ok_risk = risk > 0 and risk_pct <= MAX_STOP_PCT
        entry_to = day(min(len(daily) - 1, i + 1 + TIME_STOP_DAYS))
        tick = lambda c: {"code": c[0], "name": c[1], "value": c[2], "limit": c[3], "state": c[4]}  # noqa: E731
        skip = [] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit"]
        zones = [
            {"key": "base", "title": "Base", "tag": f"{max(1, round((i - b0) / 5))}W {depth:.0f}%", "state": "pass",
             "from": day(b0), "to": day(i - 1), "line": f"{i - b0} sessions, {depth:.1f}% deep",
             "text": (f"The base, from its high on {day(b0)}. Its highest high through the session before the breakout, "
                      f"{px(sp)}, is S9's pivot. A shakeout is bought without the VCP's contractions, dry-up and tight "
                      f"area; it needs the base's own qualifications (VCP-01, 02, 03 and 05)."),
             "shapes": [{"shape": "level", "from": day(b0), "to": day(i), "price": sp, "role": "pivot",
                         "label": f"base high {px(sp)}"}]},
            {"key": "shakeout", "title": "Shakeout", "state": "pass", "from": day(lo_i), "to": day(rec),
             "line": f"{under:.1f}% under the earlier lows on {so['vol_ratio']:.1f}x volume",
             "text": (f"On {day(lo_i)} the price fell to {px(so['low'])}, {under:.1f}% under the lows of the "
                      f"{SHAKEOUT_PRIOR_LEGS} pullbacks before it ({px(so['prior_low'])}), on {so['vol_ratio']:.1f}x "
                      f"the 50-day volume -- at least {SHAKEOUT_VOL:g}x -- and closed back above them on {day(rec)}, "
                      f"within {SHAKEOUT_RECOVER_DAYS} sessions: the weak holders were flushed out."),
             "checks": [tick(("S9", "Undercut volume", f"{so['vol_ratio']:.2f}x", f"at least {SHAKEOUT_VOL:g}x", "pass")),
                        tick(("S9", "Won back", f"{rec - lo_i} sessions", f"within {SHAKEOUT_RECOVER_DAYS}", "pass")),
                        tick(("S9", "Shakeout to breakout", f"{i - lo_i} sessions", f"at most {SHAKEOUT_WINDOW}", "pass"))],
             "shapes": [{"shape": "level", "from": day(max(b0, lo_i - 15)), "to": day(rec), "price": so["prior_low"],
                         "role": "dim", "dash": True, "label": f"earlier lows {px(so['prior_low'])}"},
                        {"shape": "dots", "role": "flag",
                         "points": [{"at": day(lo_i), "price": so["low"], "label": f"shakeout −{under:.1f}%"}]}]},
        ]
        if not missed:
            levels = [("buy", buy, f"Buy {px(buy)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", buy + BREAKEVEN_R * risk, f"+{BREAKEVEN_R:g}R")]
            zones.append({"key": "entry", "title": "Entry", "state": "pass" if not skip else "fail", "from": day(i),
                          "to": entry_to, "illustration": True, "skip": skip,
                          "line": f"buy {px(buy)} · stop {px(stop)}",
                          "text": (f"Where this strategy's rules place the trade: an illustration, not a recommendation and "
                                   f"not a backtest result. On {day(i)} the close went through {px(sp)} with MV-01's tests "
                                   f"(volume at least {VOL_MULT:g}x, within {BUY_RANGE_PCT:g}% of the pivot, in the upper "
                                   f"part of the day's range); the buy is the next open, about that close, and the stop goes "
                                   f"{STOP_BUFFER_PCT:g}% under the breakout session's low, at {px(stop)}: a risk of "
                                   f"{risk_pct:.1f}%. The shakeout's own low is far below the buy." + _NO_TARGET
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": [tick(("SL-03", "Risk", f"{risk_pct:.1f}%", f"at most {MAX_STOP_PCT:g}%",
                                           "pass" if ok_risk else "fail"))],
                          "shapes": [{"shape": "level", "from": day(i), "to": entry_to, "price": v, "role": role,
                                      "label": lab, "dash": role != "buy"} for role, v, lab in levels]})
        title = "Shakeout ✓" + (" · trade skipped" if skip and not missed else " · no valid breakout" if missed else "")
        summary = (f"A shakeout: on {day(lo_i)} the base undercut its earlier lows by {under:.1f}% on {so['vol_ratio']:.1f}x "
                   f"volume and won them back. "
                   + (f"It crossed the base's high on {day(i)}, but the strategy would not have bought: {missed}." if missed
                      else f"Broke out on {day(i)}, but the strategy would skip it: {' and '.join(skip)}." if skip
                      else f"Broke out through the base's high on {day(i)}."))
        top = max(sp, buy + BREAKEVEN_R * risk if not missed and risk > 0 else sp)
        bottom = min(so["low"], stop if not missed else so["low"])
        frame_to = entry_to if not missed else day(i)
        return {"from": day(b0), "base_from": day(b0), "to": frame_to, "kind": "shake" if not missed else "fail",
                "complete": not missed, "fail": None, "base_number": None,
                "breakout": day(i) if not missed else None, "crossed": day(i) if missed else None, "live": False,
                "as_of": day(i), "title": title, "summary": summary,
                "frame": {"from": day(b0), "to": frame_to, "top": top + (top - bottom) * 0.08, "bottom": bottom},
                "zones": zones}

    def _flats(self, daily: pd.DataFrame, cfg: MarketConfig, dets: list, start: int, anchors: list) -> list[dict]:
        """S6 and S8, the flat base, on the chart: per base, by evaluate's own tests (`flat_base` on the base as it
        stood) and the simulator's order handling. S6: the bar before qualifies and this bar closes through the
        base's high passing MV-01's `entry_misses`, on a session that passes the screen -- bought at the next open.
        S8 (FLAT_COIL_ON): today's base qualifies and the close sits within COIL_PCT under its high -- a buy-stop
        above the high rests up to PENDING_EXPIRY_BDAYS sessions, filled by the first session that trades through
        it, cancelled by a low through the stop or a close under the flat low; while it rests, later signals are
        ignored. A fill whose session's volume is under VOL_MULT x the 50-day is sold at the next open
        (LIGHT_VOLUME_EXIT). Each base keeps its first filled S8 order, else its first S6 breakout, else the first
        refused crossing; a run's fill anchors to the order that made it (`_run_bought`: its date and initial stop),
        searched back through the resting window when the run's order was a later one -- the run can skip an earlier
        signal for a reason of its own (no free slot, the market filter, the results blackout). Each carries `_fill`
        for bases_live."""
        from ..backtesting.portfolio_sim import PENDING_EXPIRY_BDAYS
        close, hi_, lo_, vo_ = (daily[k].to_numpy(float) for k in ("close", "high", "low", "volume"))
        v50_ = daily["vol_sma50"].to_numpy(float) if "vol_sma50" in daily else np.full(len(daily), np.nan)
        found: dict = {}      # base date -> what to draw
        order = None          # the resting S8 buy-stop
        for i in range(start + 1, len(daily)):
            # the resting order, as the simulator handles it on this session
            if order is not None:
                if i > order["expires"]:
                    order = None
                elif hi_[i] >= order["buy"]:
                    order["fill"] = i
                    order["light"] = bool(LIGHT_VOLUME_EXIT and v50_[i] == v50_[i] and v50_[i] > 0
                                          and vo_[i] < VOL_MULT * v50_[i])
                    if order["key"] not in found:
                        found[order["key"]] = order
                    order = None
                elif lo_[i] <= order["stop"] or close[i] < order["fb"]["low"]:
                    order = None
            # S6 on this bar: yesterday's base, today's close through its high
            p = dets[i - 1]
            fb = flat_base(p, daily.iloc[:i]) if p else None
            if fb is not None and not (NEAR_MISS and p.get("near_ok")) and close[i - 1] <= fb["pivot"] < close[i]:
                key = p["bh_date"]
                g = found.get(key)
                bought = self._run_bought(daily, anchors, i + 1, pivot_stop(fb["low"], cfg.tick_size))
                if g is None or (g["kind"] == FLAT and g["missed"]) or bought:
                    miss, vr, up = entry_misses(close[i], hi_[i], lo_[i], vo_[i], v50_[i], fb["pivot"])
                    screen = self._screen_miss(cfg, daily, i)
                    missed = (f"the stock failed the strategy's screen that session -- {screen}" if screen
                              else entry_misses_text(miss, vr, up, close[i], fb["pivot"]) if any(miss.values())
                              else None if fb["dried"] else "no volume dry-up in the sessions before it (VCP-10)")
                    if g is None or bought or not missed:
                        found[key] = {"kind": FLAT, "key": key, "fb": fb, "sig": i, "fill": i + 1 if not missed else None,
                                      "missed": missed, "buy": float(close[i]), "stop": pivot_stop(fb["low"], cfg.tick_size),
                                      "run": bought}
                continue
            # S8 on this bar: today's base, coiled under its high, places the buy-stop
            t = dets[i]
            if not FLAT_COIL_ON or order is not None or not t:
                continue
            fc = flat_base(t, daily.iloc[: i + 1])
            if (fc is not None and fc["pivot"] * (1 - COIL_PCT / 100) <= close[i] <= fc["pivot"] and fc["dried"]
                    and self._screen_miss(cfg, daily, i) is None):
                order = {"kind": FLAT_COIL, "key": t["bh_date"], "fb": fc, "sig": i, "fill": None, "missed": None,
                         "buy": pivot_buy_stop(fc["pivot"], cfg.tick_size), "stop": pivot_stop(fc["low"], cfg.tick_size),
                         "expires": i + PENDING_EXPIRY_BDAYS}
        # a run's S8 fill this replay did not explain: the coil day within the resting window whose order it was
        explained = {g["fill"] for g in found.values() if g.get("fill") is not None
                     and self._run_bought(daily, anchors, g["fill"], g["stop"])}
        for a in anchors:
            k = int(daily.index.searchsorted(pd.Timestamp(a["entry"]))) if a.get("entry") else -1
            if not FLAT_COIL_ON or k <= start or k >= len(daily) or daily.index[k] != pd.Timestamp(a["entry"]) or k in explained:
                continue
            for j in range(k - 1, max(start, k - 1 - PENDING_EXPIRY_BDAYS), -1):
                t = dets[j]
                fc = flat_base(t, daily.iloc[: j + 1]) if t else None
                if fc is None or not (fc["pivot"] * (1 - COIL_PCT / 100) <= close[j] <= fc["pivot"] and fc["dried"]):
                    continue
                buy, stop = pivot_buy_stop(fc["pivot"], cfg.tick_size), pivot_stop(fc["low"], cfg.tick_size)
                if hi_[k] >= buy and self._run_bought(daily, anchors, k, stop):
                    found[t["bh_date"]] = {"kind": FLAT_COIL, "key": t["bh_date"], "fb": fc, "sig": j, "fill": k,
                                           "missed": None, "buy": buy, "stop": stop, "expires": j + PENDING_EXPIRY_BDAYS,
                                           "light": bool(LIGHT_VOLUME_EXIT and v50_[k] == v50_[k] and v50_[k] > 0
                                                         and vo_[k] < VOL_MULT * v50_[k])}
                    explained.add(k)
                    break
        out = []
        for g in found.values():
            s = self._flat_setup(daily, cfg, g)
            run = g.get("fill") is not None and self._run_bought(daily, anchors, g["fill"], g["stop"])
            s["anchored"] = run
            s["_fill"] = daily.index[g["fill"]] if run else None
            out.append(s)
        return out

    def _flat_setup(self, daily: pd.DataFrame, cfg: MarketConfig, g: dict) -> dict:
        """One flat base for the chart, in `_setup`'s shape: the base under its high, the pivot area whose low
        anchors the stop, and the entry build_plans places -- S6 at the next open after the close through the
        high, S8 a buy-stop just above it -- stopped under the pivot area (`pivot_stop`): an illustration."""
        from ..backtesting.portfolio_sim import PENDING_EXPIRY_BDAYS
        idx = daily.index
        day = lambda k: str(idx[k].date())   # noqa: E731
        px = lambda v: f"{v:,.2f}"           # noqa: E731
        fb, sig, coil = g["fb"], g["sig"], g["kind"] == FLAT_COIL
        b0 = int(idx.get_loc(pd.Timestamp(fb["base_date"])))
        last = sig if coil else sig - 1               # the bar the base was judged on
        lows = daily["low"].to_numpy(float)
        base_low = float(lows[b0: last + 1].min())
        a0 = last - FLAT_STOP_DAYS + 1                # the pivot area: the stop's sessions
        buy, stop = g["buy"], g["stop"]
        risk = buy - stop
        risk_pct = risk / buy * 100 if buy > 0 else float("nan")
        ok_risk = risk > 0 and risk_pct <= MAX_STOP_PCT
        fill = g.get("fill")
        end = min(len(daily) - 1, (fill if fill is not None else sig) + TIME_STOP_DAYS)
        entry_to = day(end)
        tick = lambda c: {"code": c[0], "name": c[1], "value": c[2], "limit": c[3], "state": c[4]}  # noqa: E731
        dry_txt = f"{fb['dry']:.2f}x avg, {fb['quiet']} quiet"
        zones = [
            {"key": "base", "title": "Flat base", "tag": f"{max(1, round((last - b0) / 5))}W {fb['depth']:.0f}%",
             "state": "pass", "from": day(b0), "to": day(last), "line": f"{last - b0} sessions, {fb['depth']:.1f}% deep",
             "text": (f"A flat base: from its high of {px(fb['pivot'])} on {day(b0)}, {last - b0} sessions long and "
                      f"{fb['depth']:.1f}% deep, with no tight pivot to measure. Minervini buys it as it moves above the "
                      f"base's high, provided the base is {FLAT_MIN_DAYS}-{FLAT_MAX_DAYS} sessions and corrects no more "
                      f"than {FLAT_MAX_DEPTH_PCT:g}%; it must still pass the base's own qualifications (VCP-01, 02, 03, 05)."),
             "checks": [tick(("S6", "Length", f"{last - b0} sessions", f"{FLAT_MIN_DAYS}-{FLAT_MAX_DAYS}", "pass")),
                        tick(("S6", "Depth", f"{fb['depth']:.1f}%", f"at most {FLAT_MAX_DEPTH_PCT:g}%", "pass")),
                        tick(("VCP-10", "Volume dry-up", dry_txt,
                              f"at most {DRYUP_RATIO:g}x, or {DRYUP_QUIET_DAYS} quiet sessions over the last {FLAT_PIVOT_DAYS}",
                              "pass" if fb["dried"] else "fail"))],
             "shapes": [{"shape": "box", "from": day(b0), "to": day(last), "top": fb["pivot"], "bottom": base_low,
                         "role": "base", "label": ""},
                        {"shape": "level", "from": day(b0), "to": day(min(len(daily) - 1, last + 1)), "price": fb["pivot"],
                         "role": "pivot", "label": f"base high {px(fb['pivot'])}"}]},
            {"key": "tight", "title": "Pivot area", "state": "pass", "from": day(a0), "to": day(last),
             "line": f"low {px(fb['low'])}, the stop's anchor",
             "text": (f"The last {FLAT_STOP_DAYS} sessions before the {'order' if coil else 'breakout'}: their low, "
                      f"{px(fb['low'])}, anchors the stop, {STOP_BUFFER_PCT:g}% under it."),
             "shapes": [{"shape": "box", "from": day(a0), "to": day(last), "top": float(daily['high'].iloc[a0: last + 1].max()),
                         "bottom": fb["low"], "role": "tight", "label": ""}]},
        ]
        skip = [] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit"]
        light = coil and g.get("light")
        if not g["missed"]:
            levels = [("buy", buy, f"Buy {px(buy)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", buy + BREAKEVEN_R * risk, f"+{BREAKEVEN_R:g}R")]
            how = (f"On {day(sig)} the close sat within {COIL_PCT:g}% under the base's high, so a buy-stop goes just above "
                   f"it, at {px(buy)}, resting up to {PENDING_EXPIRY_BDAYS} sessions"
                   + (f"; it filled on {day(fill)}" if fill is not None else "; it never filled")
                   + (f", on volume under {VOL_MULT:g}x the 50-day, so the strategy sells at the next open: "
                      f"an unconfirmed breakout (LIGHT_VOLUME_EXIT)" if light else "") + "."
                   if coil else
                   f"On {day(sig)} the close went through the base's high with MV-01's tests (volume at least {VOL_MULT:g}x, "
                   f"within {BUY_RANGE_PCT:g}% of the high, in the upper part of the day's range); the buy is the next open, "
                   f"about that close.")
            zones.append({"key": "entry", "title": "Entry", "state": "pass" if not skip and not light else "fail",
                          "from": day(sig), "to": entry_to, "illustration": True, "skip": skip,
                          "line": f"buy {px(buy)} · stop {px(stop)}" + (" · light-volume fill" if light else ""),
                          "text": (f"Where this strategy's rules place the trade: an illustration, not a recommendation and "
                                   f"not a backtest result. {how} The stop goes {STOP_BUFFER_PCT:g}% under the pivot area's "
                                   f"low, at {px(stop)}: a risk of {risk_pct:.1f}%." + _NO_TARGET
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": [tick(("SL-03", "Risk", f"{risk_pct:.1f}%", f"at most {MAX_STOP_PCT:g}%",
                                           "pass" if ok_risk else "fail"))],
                          "shapes": [{"shape": "level", "from": day(sig), "to": entry_to, "price": v, "role": role,
                                      "label": lab, "dash": role != "buy"} for role, v, lab in levels]})
        name = "Flat base S8" if coil else "Flat base S6"
        title = (f"{name} ✓" + (" · no valid breakout" if g["missed"] else " · trade skipped" if skip
                                else " · light-volume fill, sold next open" if light
                                else " · order unfilled" if coil and fill is None else ""))
        summary = (f"A flat base, {fb['depth']:.1f}% deep over {last - b0} sessions. "
                   + (f"It crossed its high on {day(sig)}, but the strategy would not have bought: {g['missed']}." if g["missed"]
                      else f"A buy-stop rested above its high from {day(sig)}"
                           + (f" and filled on {day(fill)}" + (" on light volume, sold the next open" if light else "") if fill is not None
                              else ", unfilled") + "." if coil
                      else f"Broke out through its high on {day(sig)}."))
        top = max(fb["pivot"], buy + BREAKEVEN_R * risk if not g["missed"] and risk > 0 else fb["pivot"])
        bottom = min(base_low, stop if not g["missed"] else base_low)
        frame_to = entry_to if not g["missed"] else day(sig)
        done = not g["missed"]
        return {"from": day(b0), "base_from": day(b0), "to": frame_to, "kind": "flat" if done else "fail",
                "complete": done, "fail": None, "base_number": None,
                "breakout": day(fill if coil and fill is not None else sig) if done and (fill is not None or not coil) else None,
                "crossed": day(sig) if g["missed"] else None, "live": False, "as_of": day(last),
                "title": title, "summary": summary,
                "frame": {"from": day(b0), "to": frame_to, "top": top + (top - bottom) * 0.08, "bottom": bottom},
                "zones": zones}

    @staticmethod
    def _target_checks(px, target, uncapped, capped: bool, r_mult, ok_r: bool) -> list[dict]:
        """MEASURED_MOVE_RR = 1: the entry zone's overhead and reward-to-risk rows, as build_plans tests them."""
        return [
            {"code": "OH", "name": "Overhead supply",
             "value": (f"caps the target at {px(target)} (measured move to {px(uncapped)})" if capped
                       else "none in the way") if target else "—",
             "limit": f"swing highs at least {OVERHEAD_CLUSTER_ATR:g} ATR above the base high",
             "state": "warn" if capped else "pass"},
            {"code": "R:R", "name": "Reward / risk", "value": _rr(r_mult, ok_r),
             "limit": f"at least {MIN_STRUCTURAL_R:g}R", "state": "pass" if ok_r else "fail"},
        ]

    @staticmethod
    def _measured_move_note(px, uncapped, cap, risk: float, entry: float) -> list[dict]:
        """MEASURED_MOVE_RR = 0: the measured move as a note -- recorded for study, deciding nothing."""
        if not uncapped or uncapped != uncapped or risk <= 0:
            return []
        to = cap if cap is not None else uncapped
        return [{"code": "note", "name": "Measured move",
                 "value": f"{px(uncapped)}, {(uncapped - entry) / risk:.1f}R"
                          + (f" · an older swing high at {px(cap)} ({(to - entry) / risk:.1f}R)" if cap is not None else ""),
                 "limit": "not a rule: Minervini sets no price target", "state": "pass"}]

    @staticmethod
    def _skip_why(zones: list[dict]) -> str:
        """Why a base that broke out is still "trade skipped", for its summary: each entry illustration's own skip
        reasons (named by entry when there are several), else the structure zones that failed."""
        entries = [z for z in zones if z.get("illustration") and z.get("skip")]
        if entries:
            same = all(z["skip"] == entries[0]["skip"] for z in entries)   # one reason for every entry: said once
            parts = [("" if same else f"the {z['title'].lower()}: ") + " and ".join(z["skip"])
                     for z in (entries[:1] if same else entries)]
            return "the strategy would skip it: " + "; ".join(parts)
        failed = [z["title"].lower() for z in zones if not z.get("illustration") and z.get("state") == "fail"]
        return "the strategy would skip it: " + (", ".join(failed) + " failed" if failed else "no entry passes")

    @staticmethod
    def _refusal(missed: str) -> str:
        """A crossing the strategy would not buy, in a title: a breakout that failed MV-01's own tests is no valid
        breakout; one refused because the stock failed the screen that day still broke out."""
        if "screen" not in missed:
            return "no valid breakout"
        return "broke out, too illiquid" if "illiquid" in missed else "broke out outside the Trend Template"

    def _screen_miss(self, cfg: MarketConfig, daily: pd.DataFrame, i: int) -> str | None:
        """Why bar `i` fails the strategy's screen (prefilter_row: the turnover floor, then the Trend
        Template), or None when it passes. A young listing is judged by its own gates, not the template, so
        it is never refused here."""
        row = daily.iloc[i]
        if is_young_row(row, i + 1):
            return None
        ok, why = self.prefilter_row(cfg, row)
        if ok:
            return None
        if why.startswith("turnover below"):
            # the liquidity floor, not the trend: say so, with the turnover the stock actually had
            floor, traded = _min_turnover(cfg, row.name), float(row["vol_sma50"]) * float(row["close"])
            unit, div = ("crore", 1e7) if cfg.currency_code == "INR" else ("million", 1e6)
            # a scaled floor is no round number: one more decimal until the two figures read apart
            # (SOLARINDS.NS 2013-01-29 read "₹1.0 crore ... under the ₹1 crore floor")
            nd = next((k for k in (1, 2, 3) if round(traded / div, k) < round(floor / div, k)), 3)
            return (f"too illiquid: {cfg.currency_symbol}{traded / div:,.{nd}f} "
                    f"{unit} a day traded (50-day average), under the {cfg.currency_symbol}{floor / div:,.{nd}f} {unit} floor")
        return f"outside the Trend Template: {why}"

    def _power_plays(self, daily: pd.DataFrame, cfg: MarketConfig) -> list[dict]:
        """MV-05 on the chart: every power-play shape the detector measured -- a run of at least
        POWER_PLAY.run_mult x into a flag -- whether or not the flag then qualified. The base path
        never sees one (the flag is shorter than a base, the run steeper than any prior advance), so
        before these were drawn a power play the rules refused was simply invisible: AXSM's January
        2019 run (+457%) into a flag that fell 29.3% against the 25% limit showed only failed bases.
        Each is judged on its most developed bar: the bar before the breakout when it completed,
        else its last bar."""
        pp = POWER_PLAY
        need = pp.run_window + pp.flag_max_days + pp.swing_k + 2
        win = need + 60      # history each bar's detection reads (enough for the 50-day volume average)
        close = daily["close"].to_numpy(float)
        dets = [None] * len(daily)
        groups: dict = {}
        for i in range(need, len(daily)):
            r = vcp_spec.detect_power_play(daily.iloc[max(0, i - win): i + 1], pp)
            dets[i] = r
            if r["fail"] in (None, "PP-03", "PP-05", "PP-06") and r.get("flag_high_date") is not None:
                g = groups.setdefault(r["flag_high_date"], {"ok": [], "last": i, "breakout": None})
                g["last"] = i
                if r["fail"] is None:
                    g["ok"].append(i)
        hi_, lo_, vo_ = (daily[k].to_numpy(float) for k in ("high", "low", "volume"))
        v50_ = daily["vol_sma50"].to_numpy(float) if "vol_sma50" in daily else np.full(len(daily), np.nan)
        for i in range(need + 1, len(daily)):
            p = dets[i - 1]
            if p and p["fail"] is None and p.get("pivot") and close[i - 1] <= p["pivot"] < close[i] \
                    and groups.get(p["flag_high_date"], {}).get("breakout", 0) is None:
                miss, vr, up = entry_misses(close[i], hi_[i], lo_[i], vo_[i], v50_[i], p["pivot"])
                groups[p["flag_high_date"]]["breakout"] = i
                groups[p["flag_high_date"]]["missed"] = (entry_misses_text(miss, vr, up, close[i], p["pivot"])
                                                         if any(miss.values()) else None)
        last = len(daily) - 1
        out = []
        for g in groups.values():
            bo = g["breakout"]
            rep = bo - 1 if bo is not None else g["ok"][-1] if g["ok"] else g["last"]
            # a "flag" far past the limit is a collapse, not a near miss: drawing it only clutters
            if (dets[rep].get("flag_depth_pct") or 0) > self._PP_DRAW_DEPTH_X * pp.flag_max_depth_pct:
                continue
            out.append(self._power_setup(daily, cfg, dets[rep], rep, bo, rep == last, g.get("missed")))
        return out

    def _power_setup(self, daily: pd.DataFrame, cfg: MarketConfig, r: dict, rep: int, bo: int | None,
                     live: bool, missed: str | None = None) -> dict:
        """One power play for the chart, in `_setup`'s shape: the run, the flag, and -- when the flag
        qualified -- the entry its rules would place (an illustration, as for a VCP)."""
        pp, idx = POWER_PLAY, daily.index
        iso = lambda t: str(pd.Timestamp(t).date())   # noqa: E731
        day = lambda i: iso(idx[i])                   # noqa: E731
        px = lambda v: f"{v:,.2f}"                    # noqa: E731
        fh_i = int(idx.get_loc(r["flag_high_date"]))
        fh = float(r["flag_high"])
        lows = daily["low"].to_numpy(float)
        w0 = max(0, fh_i - pp.run_window)
        rl_i = w0 + int(lows[w0:fh_i].argmin())
        run_low = float(lows[rl_i])
        seg = lows[fh_i: rep + 1]
        fl_i = fh_i + int(seg.argmin())
        flag_low = float(seg.min())
        depth = (fh - flag_low) / fh * 100
        flag_days = rep - fh_i
        fail, at = r["fail"], day(rep)
        ok = fail is None
        tick = lambda c: {"code": c[0], "name": c[1], "value": c[2], "limit": c[3], "state": c[4]}  # noqa: E731
        run_checks = [tick(("PP-02", "Run", f"+{r['run_pct']:.0f}% in {fh_i - rl_i} sessions",
                            f"at least +{(pp.run_mult - 1) * 100:.0f}% within {pp.run_window}", "pass"))]
        flag_checks = [
            tick(("PP-01", "Flag length", f"{flag_days} sessions", f"{pp.flag_min_days}-{pp.flag_max_days}", "pass")),
            tick(("PP-03", "Flag depth", f"{depth:.1f}%", f"at most {pp.flag_max_depth_pct:g}%",
                  "fail" if fail == "PP-03" else "pass")),
            tick(("PP-05", "Tight area", f"{r['tight_range_pct']:.1f}%" if r.get("tight_range_pct") is not None else "—",
                  f"at most {pp.tight_pct:g}%", "fail" if fail == "PP-05" else "pass" if r.get("tight_range_pct") is not None else "skip")),
            tick(("PP-06", "Volume dry-up",
                  f"{r['dryup']:.2f}x avg, {r['dryup_quiet_days']} quiet" if r.get("dryup") is not None else "—",
                  f"at most {pp.dryup_ratio:g}x, or {pp.dryup_quiet_days} sessions at or under {pp.dryup_quiet_ratio:g}x",
                  "fail" if fail == "PP-06" else "pass" if r.get("dryup") is not None else "skip")),
        ]
        zones = [
            {"key": "uptrend", "title": "Run", "state": "pass", "from": day(rl_i), "to": day(fh_i),
             "line": f"+{r['run_pct']:.0f}% in {fh_i - rl_i} sessions",
             "text": (f"The run: from {px(run_low)} on {day(rl_i)} to {px(fh)} on {day(fh_i)}, +{r['run_pct']:.0f}% in "
                      f"{fh_i - rl_i} sessions. A power play needs the price at least "
                      f"{pp.run_mult:g}x within {pp.run_window} sessions, measured at the flag's high."),
             "checks": run_checks,
             "shapes": [{"shape": "line", "from": day(rl_i), "to": day(fh_i), "p0": run_low, "p1": fh,
                         "role": "uptrend", "arrow": True, "label": f"+{r['run_pct']:.0f}%"}]},
            {"key": "base", "title": "Flag", "tag": f"{max(1, round(flag_days / 5))}W {depth:.0f}% flag",
             "state": "fail" if fail else "pass", "from": day(fh_i), "to": at,
             "line": f"{flag_days} sessions, {depth:.1f}% deep",
             "text": (f"The flag: from the high of {px(fh)} on {day(fh_i)} down to {px(flag_low)}, {depth:.1f}% deep over "
                      f"{flag_days} sessions. Minervini's flag goes sideways and corrects no more than "
                      f"{pp.flag_max_depth_pct:g}%, for {pp.flag_min_days}-{pp.flag_max_days} sessions, with volume "
                      f"contracting just before the breakout." + (f" It failed: {r['fail_why']}." if fail else "")),
             "checks": flag_checks,
             "shapes": [{"shape": "dots", "role": "contraction",
                         "points": [{"at": day(fl_i), "price": flag_low, "label": f"−{depth:.0f}%{' ✗' if fail == 'PP-03' else ''}"}]}]},
        ]
        top, bottom, frame_to = fh, min(run_low, flag_low), at
        if ok:
            pv, tl = float(r["pivot"]), float(r["tight_low"])
            buy, stop = pivot_buy_stop(pv, cfg.tick_size), pivot_stop(tl, cfg.tick_size)
            risk = buy - stop
            target = buy + power_measured_move(fh, r["run_pct"])   # build_plans' MV-05 objective: the flagpole
            r_mult = (target - buy) / risk if risk > 0 else None
            risk_pct = risk / buy * 100
            ok_risk, ok_r = risk_pct <= PP_MAX_STOP_PCT, (not MEASURED_MOVE_RR) or (r_mult or 0) >= MIN_STRUCTURAL_R
            entry_to = day(min(len(daily) - 1, (bo if bo is not None else rep) + TIME_STOP_DAYS))
            levels = [("buy", buy, f"Buy {px(buy)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", buy + BREAKEVEN_R * risk, "" if MEASURED_MOVE_RR else f"+{BREAKEVEN_R:g}R")]
            if MEASURED_MOVE_RR:
                levels.append(("target", target, f"Target {px(target)}"))
            shapes = [{"shape": "box", "from": day(int(idx.get_indexer([pd.Timestamp(at)])[0]) - pp.tight_min_days + 1),
                       "to": at, "top": pv, "bottom": tl, "role": "tight", "label": ""}]
            shapes += [{"shape": "level", "from": at, "to": entry_to, "price": v, "role": role, "label": lab,
                        "dash": role != "buy"} for role, v, lab in levels]
            skip = ([] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {PP_MAX_STOP_PCT:g}% limit"]) + \
                   ([] if ok_r else [f"it projects {_rr(r_mult, False)}, under the {MIN_STRUCTURAL_R:g}:1 minimum"])
            zones.append({"key": "entry", "title": "Entry", "state": "pass" if not skip else "fail", "from": at,
                          "to": entry_to, "illustration": True, "skip": skip,
                          "line": f"buy {px(buy)} · stop {px(stop)}" + (f" · {_rr(r_mult, ok_r)}" if MEASURED_MOVE_RR else ""),
                          "text": (f"Where this strategy's rules place the trade: an illustration, not a recommendation and "
                                   f"not a backtest result. Buy through the flag's pivot, {px(pv)}, on a close with volume "
                                   f"of at least {VOL_MULT:g}x the 50-day average; the stop goes {STOP_BUFFER_PCT:g}% under "
                                   f"the tight low, at {px(stop)}: a risk of {risk_pct:.1f}%."
                                   + (f" The objective is the run into the flag projected from the buy, {px(target)}, "
                                      f"{_rr(r_mult, ok_r)}." if MEASURED_MOVE_RR else _NO_TARGET)
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": [tick(("SL-03", "Risk", f"{risk_pct:.1f}%", f"at most {PP_MAX_STOP_PCT:g}%", "pass" if ok_risk else "fail"))]
                                    + ([tick(("R:R", "Reward / risk", _rr(r_mult, ok_r), f"at least {MIN_STRUCTURAL_R:g}R", "pass" if ok_r else "fail"))]
                                       if MEASURED_MOVE_RR else self._measured_move_note(px, target, None, risk, buy)),
                          "shapes": shapes})
            top, bottom, frame_to = max(top, target if MEASURED_MOVE_RR else top, buy + BREAKEVEN_R * risk), min(bottom, stop), entry_to
            title = "Power play ✓" + (" · trade skipped" if skip else " · no valid breakout" if missed else "")
            summary = (f"A power play: +{r['run_pct']:.0f}% into a {depth:.1f}% flag. "
                       + (f"It crossed the pivot on {day(bo)}, but the strategy would not have bought: {missed}."
                          if bo is not None and missed
                          else f"Broke out on {day(bo)}, but the strategy would skip it: {' and '.join(skip)}."
                          if bo is not None and skip
                          else f"Broke out on {day(bo)}." if bo is not None else "Waiting for a close through the pivot."))
        else:
            short = {"PP-03": f"flag fell {depth:.0f}% (max {pp.flag_max_depth_pct:g}%)",
                     "PP-05": "flag's tight area too wide", "PP-06": "no volume dry-up in the flag"}.get(fail, fail)
            title = f"Power play ✗ · {short}"
            summary = f"Power-play shaped, but it does not qualify: {r['fail_why']}."
        if live:
            title += " · today"
            summary = f"Still forming — judged on today's bar, {at}. " + summary
        return {"from": day(rl_i), "base_from": day(fh_i), "to": frame_to, "kind": "vcp" if ok else "fail",
                "complete": ok, "fail": fail, "breakout": day(bo) if bo is not None and not missed else None,
                "crossed": day(bo) if bo is not None and missed else None, "live": live,
                "as_of": at, "title": title, "summary": summary,
                "frame": {"from": day(rl_i), "to": frame_to, "top": top + (top - bottom) * 0.08, "bottom": bottom},
                "zones": zones}

    @staticmethod
    def _cheat_stop_out(daily: pd.DataFrame, cfg: MarketConfig, cheat: tuple, bo: int | None) -> int | None:
        """The bar a cheat entry's stop (under its shelf low, `pivot_stop`) was hit, if before the base broke
        out (`bo`) or up to the last bar; None while it holds. Display only: the chart's drawing ends there."""
        ci, _, cp = cheat
        stop = pivot_stop(cp["cheat_low"], cfg.tick_size)
        end = bo if bo is not None and bo > ci else len(daily)
        low = daily["low"].to_numpy(float)
        hit = next((j for j in range(ci + 1, end) if low[j] <= stop), None)
        return hit

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
    # a failed power-play flag is drawn only up to this multiple of PP-03's limit (display only)
    _PP_DRAW_DEPTH_X = 1.5

    def _live_withholds(self, p: dict | None) -> bool:
        """Would the screen's rules withhold a cheat whose base (as detected the bar before it) is `p`?
        The same test as `evaluate` -- read from the module constant, or from the live variant when the
        screen applies one that this process (the chart's) has not."""
        lv = (type(self).live_variant or {}).get("const", {})
        return bool((CHEAT_BLOCK_VCP09 or lv.get("CHEAT_BLOCK_VCP09")) and p and p.get("fail") == "VCP-09")

    def _setup(self, daily: pd.DataFrame, cfg: MarketConfig, r: dict, rep: int, bo: int | None,
               cheat: tuple | None = None, live: bool = False, traded_cheat: bool = False,
               missed: str | None = None, near: str | None = None, ov=None, count: dict | None = None) -> dict:
        """One setup for the chart: a frame around it, and its zones — the uptrend into the base, the
        base and its contractions, the pivot entry of a completed VCP, and the latest cheat entry
        (`cheat`: (bar, MV03 | MV04, yesterday's detection)) — each with its own shapes, its checklist
        rows and a writeup. The entry zones ILLUSTRATE where this strategy's own rules place the trade
        (pivot_buy_stop, pivot_stop, vcp_measured_move, cheat_measured_move, the exit constants); they
        are not backtest results, and the chart replaces them with a run's stored trade when one is
        selected. The targets are capped by overhead supply as build_plans caps them (`overhead_binding`, on
        the levels `ov` -- `overhead_at` -- gives for the signal bar). `live`: the base is still forming, judged on the last bar. `traded_cheat`: a run bought
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
        # S7: a base that missed one rule narrowly is drawn as complete, in its own colour, naming the miss
        if NEAR_MISS and not done and r.get("near_ok"):
            done = True
            near = near or f"{r['near']['rule']}: {r['near']['why']}"
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
        close_to = lambda v, lim: abs(v - lim) < 0.1
        pct = lambda v, lim: f"{v:.2f}" if close_to(v, lim) else f"{v:.1f}"
        fine = bool(depths) and any(close_to(b, FINAL_REF_RATIO * a) for a, b in zip(depths, depths[1:]))
        dep = lambda x: f"{x:.2f}" if fine else f"{x:.1f}"
        values = {
            "VCP-01": (f"+{pct(r['prior_advance_pct'], PRIOR_ADVANCE_PCT) if close_to(r['prior_advance_pct'], PRIOR_ADVANCE_PCT) else format(r['prior_advance_pct'], '.0f')}% in {up_days} days" if up_days is not None else "—",
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
        cnt = count if count and count.get("n") else None
        focus_from = bd      # where the setup's frame starts: the move into the base (VCP-01's leg)
        if r["prior_low"]:
            pl, pd_ = float(r["prior_low"]), iso(r["prior_low_date"])
            up_from = focus_from = pd_
            trend = ("The trend template held on the high's bar, and the 150/200-day structure held through the base."
                     if fail != "VCP-03" else f"But it is too new to judge the trend: {young_why}." if young
                     else f"But the trend was not intact: {self._vcp_fail_why(r, daily, bh_i, rep)}.")
            # The whole Stage 2 advance the base sits in (`advances`), from its low to the base high, numbered by
            # the base count -- not just VCP-01's leg (the lowest low of the last {prior_window} sessions), which
            # starts somewhere different for every base of one advance and read as a new uptrend each time.
            # VCP-01's own measure stays the zone's first check row.
            a_i = cnt["low_i"] if cnt else None
            a_low, a_day = (float(daily["low"].iloc[a_i]), day(a_i)) if cnt else (pl, pd_)
            gain = (bh / a_low - 1) * 100 if a_low > 0 else 0.0
            up_from = min(a_day, pd_)
            nth = f"{_ordinal(cnt['n'])} base" if cnt else ""
            up_shapes = [{"shape": "line", "from": a_day, "to": bd, "p0": a_low, "p1": bh, "role": "uptrend",
                          "arrow": True, "label": f"+{gain:.0f}%" + (f" · {nth}" if cnt else "")}]
            up_checks, flag, warn = list(checks["uptrend"]), "", False
            line = (f"+{gain:.0f}% since {a_day} · {nth}" if cnt else f"+{r['prior_advance_pct']:.0f}% in {up_days} days")
            late = bool(cnt and MAX_BASE_COUNT and cnt["n"] > MAX_BASE_COUNT)
            if cnt:
                e_ = cnt["earlier"]
                up_checks.append({"code": "note", "name": "Base count",
                                  "value": f"{nth} of the advance since {day(cnt['start'])}"
                                           + (f" (earlier breakouts {', '.join(e_)})" if e_ else ""),
                                  "limit": (f"at most the {_ordinal(MAX_BASE_COUNT)}" if MAX_BASE_COUNT else "recorded")
                                           + f"; the count restarts once TT-01–TT-04 fail {BASE_COUNT_RESET_DAYS} sessions in a row",
                                  "state": "fail" if late else "pass"})
                warn = late
                advance = (f"The Stage 2 advance: from {px(a_low)} on {a_day} to the base high, {px(bh)} on {bd}, "
                           f"+{gain:.0f}%. This is its {nth}"
                           + (f": {len(e_)} earlier base{'s' if len(e_) != 1 else ''} of it broke out ({', '.join(e_)})."
                              if e_ else ": no earlier base of it has broken out.")
                           + f" Minervini favours the first and second bases of an advance; later ones are "
                             f"late-stage -- the trend is old, and most who want the stock already own it"
                           + (f". The strategy buys at most the {_ordinal(MAX_BASE_COUNT)} base"
                              + (": this one is refused. " if late else ". ") if MAX_BASE_COUNT else ". "))
            elif count is not None:
                up_checks.append({"code": "note", "name": "Base count", "value": "outside a Stage 2 advance",
                                  "limit": f"TT-01–TT-04 failed {BASE_COUNT_RESET_DAYS}+ sessions in a row at the high",
                                  "state": "warn"})
                warn = True
                advance = (f"The base high is outside a Stage 2 advance: the trend structure (TT-01–TT-04) had "
                           f"failed {BASE_COUNT_RESET_DAYS} sessions in a row, so the base count has restarted. ")
            else:
                advance = ""
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
            zones.append({"key": "uptrend", "title": "Uptrend", "state": zstate("uptrend"), "warn": warn, "from": focus_from, "to": bd,
                          "line": line,
                          "text": (advance + f"The base rule (VCP-01) measures the move into the base: "
                                   f"+{r['prior_advance_pct']:.0f}%, from {px(pl)} on {pd_}, in {up_days} sessions. A "
                                   f"base only matters after a strong advance: at least {PRIOR_ADVANCE_PCT:g}% within "
                                   f"{VCP.prior_window} sessions. {trend}{flag}"),
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
        screen = None
        if done and not traded_cheat:
            pv, tl = float(r["pivot"]), float(r["tight_low"])
            buy, stop = pivot_buy_stop(pv, cfg.tick_size), pivot_stop(tl, cfg.tick_size)
            risk = buy - stop
            mm = vcp_measured_move(bh, r.get("base_depth_pct") if depths else None)
            target = buy + mm if mm == mm else None
            e_i = bo if bo is not None else rep
            # overhead supply, as build_plans caps it on the signal bar (the breakout, or this bar while waiting),
            # from build_plans' own entry: the breakout's close (MV-01, bought at the next open), else the buy-stop
            # (MV-02). From the drawn buy instead, ADANIPORTS.NS's 2015-08-14 breakout was capped by its own high.
            ov = ov or overhead_at(daily)
            plan_entry = float(daily["close"].iloc[bo]) if bo is not None else buy
            cap = overhead_binding(plan_entry, bh, float(daily["atr14"].iloc[e_i]), ov(e_i)) if target else None
            capped = cap is not None and cap < target
            uncapped, target = target, (cap if capped else target)
            r_mult = (target - buy) / risk if target and risk > 0 else None
            risk_pct = risk / buy * 100
            entry_to = day(min(len(daily) - 1, e_i + TIME_STOP_DAYS))
            e_from = at
            # Short labels, and none on the +2R breakeven line: with a target near 2R the two lines sit on
            # top of each other, and four labels stacked in a narrow entry zone could not be read. The
            # risk, the R multiple and the breakeven rule are in the card's Entry zone.
            # MEASURED_MOVE_RR = 0 (Minervini): no target line; the +BREAKEVEN_R line, where the stop moves up
            # and a third is sold, is the first managed step and carries the label instead
            levels = [("buy", buy, f"Buy {px(buy)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", buy + BREAKEVEN_R * risk, "" if MEASURED_MOVE_RR else f"+{BREAKEVEN_R:g}R")]
            if target and MEASURED_MOVE_RR:
                levels.append(("target", target, f"Target {px(target)}"))
            shapes = [{"shape": "level", "from": e_from, "to": entry_to, "price": v, "role": role, "label": lab,
                       "dash": role != "buy"} for role, v, lab in levels]
            if bo is not None:
                c = float(daily["close"].iloc[bo])
                shapes.append({"shape": "dots", "points": [{"at": day(bo), "price": c,
                                                            "label": "crossed ✗" if missed else "breakout"}],
                               "role": "stop" if missed else "buy"})
            ok_risk, ok_r = risk_pct <= MAX_STOP_PCT, (not MEASURED_MOVE_RR) or (r_mult or 0) >= MIN_STRUCTURAL_R
            # the screen on the breakout bar (or, still waiting, on this one): MV-01 is bought only on a bar
            # that passes it, so a VCP outside the Trend Template is no setup yet whatever its shape
            screen = self._screen_miss(cfg, daily, e_i)
            e_checks = [
                {"code": "TT", "name": "Screen", "value": f"fails on {day(e_i)}: {screen}" if screen
                 else f"held on {day(e_i)}", "limit": "passes on the breakout session",
                 "state": "fail" if screen and bo is not None else "warn" if screen else "pass"},
                {"code": "SL-03", "name": "Risk", "value": f"{risk_pct:.1f}%", "limit": f"at most {MAX_STOP_PCT:g}%",
                 "state": "pass" if ok_risk else "fail"},
            ] + (self._target_checks(px, target, uncapped, capped, r_mult, ok_r) if MEASURED_MOVE_RR
                 else self._measured_move_note(px, uncapped, cap if capped else None, risk, buy))
            skip = [f"the stock failed the strategy's screen on the breakout, {day(bo)} -- {screen}"] if screen and bo is not None else []
            if not ok_risk:
                skip.append(f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit")
            if cnt and MAX_BASE_COUNT and cnt["n"] > MAX_BASE_COUNT:
                skip.append(f"it is the {_ordinal(cnt['n'])} base of its advance (at most the {_ordinal(MAX_BASE_COUNT)})")
            if not ok_r:
                skip.append(f"it projects {_rr(r_mult, False)}, under the {MIN_STRUCTURAL_R:g}:1 minimum" if r_mult else "no measured move")
            happened = (f" It broke out on {day(bo)}." if bo is not None else " It has not broken out yet."
                        + (f" The stock fails the strategy's screen on {day(e_i)} -- {screen} -- and the strategy buys "
                           f"a breakout only on a session that passes it." if screen else ""))
            zones.append({"key": "entry", "title": "Entry", "state": "pass" if not skip else "fail", "from": e_from, "to": entry_to,
                          "illustration": True, "skip": skip,
                          "line": f"buy {px(buy)} · stop {px(stop)}" + (f" · {_rr(r_mult, ok_r)}" if r_mult and MEASURED_MOVE_RR else ""),
                          "text": (f"Where this strategy's rules place the trade: an illustration, not a recommendation and "
                                   f"not a backtest result. Buy with a buy-stop just above the pivot, at {px(buy)}; the "
                                   f"breakout counts only on volume of at least {VOL_MULT:g}× the 50-day average. The stop "
                                   f"goes {STOP_BUFFER_PCT:g}% under the tight-area low, at {px(stop)}: a risk of "
                                   f"{risk_pct:.1f}% a share (the strategy skips anything over {MAX_STOP_PCT:g}%)."
                                   + ("" if MEASURED_MOVE_RR else _NO_TARGET)
                                   + (f" The target is the base's measured move, its high less its lowest low, "
                                      f"projected from the buy" + (
                                          f" -- {px(uncapped)} -- capped by overhead supply: an older swing high at "
                                          f"{px(target)}, at least {OVERHEAD_CLUSTER_ATR:g} ATR above the base high, "
                                          f"where earlier buyers wait to sell. Target {px(target)}" if capped else
                                          f": {px(target)}, with no older swing high in the way")
                                      + f", {_rr(r_mult, ok_r)} (it needs at least {MIN_STRUCTURAL_R:g}R)." if target and MEASURED_MOVE_RR else "")
                                   + f" Managing it: the stop moves to breakeven at +{BREAKEVEN_R:g}R; a third is sold "
                                     f"at +{PARTIAL_R:g}R or once the close is {STRENGTH_EXT_PCT:g}% above the 50-day average, "
                                     f"whichever comes first; the rest goes on a close below the 50-day; and it is sold after {TIME_STOP_DAYS} sessions if it never "
                                     f"reached +1R." + happened
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": e_checks, "shapes": shapes})
            top = max(top, (target or top) if MEASURED_MOVE_RR else top, buy + BREAKEVEN_R * risk)
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
            ov = ov or overhead_at(daily)
            c_cap = overhead_binding(entry, bh, float(daily["atr14"].iloc[ci]), ov(ci))
            c_capped = c_cap is not None and c_cap < entry + mm
            c_uncapped, target = entry + mm, (c_cap if c_capped else entry + mm)
            r_mult = (target - entry) / risk if risk > 0 else None
            risk_pct = risk / entry * 100
            stopped = self._cheat_stop_out(daily, cfg, cheat, bo)
            c_from, c_to = day(ci), day(stopped if stopped is not None else min(len(daily) - 1, ci + TIME_STOP_DAYS))
            shapes = [{"shape": "box", "from": day(max(0, ci - CHEAT_SHELF_DAYS)), "to": day(ci - 1),
                       "top": float(cp["cheat_pivot"]), "bottom": float(cp["cheat_low"]), "role": "tight",
                       "label": ""}]   # the base carries the one label (its footprint); the shelf range is in the card
            levels = [("buy", entry, f"Cheat buy {px(entry)}"), ("stop", stop, f"Stop {px(stop)}"),
                      ("breakeven", entry + BREAKEVEN_R * risk, "" if MEASURED_MOVE_RR else f"+{BREAKEVEN_R:g}R")]
            if MEASURED_MOVE_RR:
                levels.append(("target", target, f"Target {px(target)}"))
            shapes += [{"shape": "level", "from": c_from, "to": c_to, "price": v, "role": role, "label": lab,
                        "dash": role != "buy"} for role, v, lab in levels]
            ok_risk, ok_r = risk_pct <= MAX_STOP_PCT, (not MEASURED_MOVE_RR) or (r_mult or 0) >= MIN_STRUCTURAL_R
            c_screen = self._screen_miss(cfg, daily, ci)   # the cheat is bought only on a session that passes it
            c_checks = [
                {"code": "TT", "name": "Screen", "value": f"fails on {c_from}: {c_screen}" if c_screen
                 else f"held on {c_from}", "limit": "passes on the cheat's session",
                 "state": "fail" if c_screen else "pass"},
                {"code": cz, "name": "Shelf", "value": f"{cp['cheat_range_pct']:.1f}%, {third} third",
                 "limit": f"at most {CHEAT_SHELF_PCT:g}% over {CHEAT_SHELF_DAYS} days, below the high", "state": "pass"},
            ] + ([
                {"code": cz, "name": "Shelf volume",
                 "value": (f"{cp['cheat_dryup']:.2f}x avg, {cp['cheat_quiet_days']} quiet"
                           if cp.get("cheat_dryup") == cp.get("cheat_dryup") and cp.get("cheat_dryup") is not None else "—"),
                 "limit": f"at most {DRYUP_RATIO:g}x, or {DRYUP_QUIET_DAYS} sessions at or under {DRYUP_QUIET_RATIO:g}x",
                 "state": "pass"},
            ] if CHEAT_DRYUP else []) + ([
                {"code": cz, "name": "Turn before the shelf",
                 "value": (f"rally won back {cp['cheat_rally'] * 100:.0f}%" + ("" if cp.get("cheat_higher_low") else ", no higher low")
                           if cp.get("cheat_rally") is not None and cp["cheat_rally"] == cp["cheat_rally"] else "—"),
                 "limit": f"a higher low, then a rally of at least {CHEAT_RALLY_FRAC * 100:.0f}% of the decline", "state": "pass"},
            ] if CHEAT_RALLY_FRAC else []) + ([
                {"code": cz, "name": "Volume contraction",
                 "value": (f"{cp['cheat_vol_vs_lead']:.2f}x the sessions before"
                           if cp.get("cheat_vol_vs_lead") is not None and cp["cheat_vol_vs_lead"] == cp["cheat_vol_vs_lead"] else "—"),
                 "limit": f"at most {CHEAT_VOL_CONTRACT:g}x", "state": "pass"},
            ] if CHEAT_VOL_CONTRACT else []) + [
                {"code": "SL-03", "name": "Risk", "value": f"{risk_pct:.1f}%", "limit": f"at most {MAX_STOP_PCT:g}%",
                 "state": "pass" if ok_risk else "fail"},
            ] + (self._target_checks(px, target, c_uncapped, c_capped, r_mult, ok_r) if MEASURED_MOVE_RR
                 else self._measured_move_note(px, c_uncapped, c_cap if c_capped else None, risk, entry))
            skip = ([f"the stock fails the strategy's screen on {c_from} -- {c_screen}"] if c_screen else []) + \
                   ([] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit"]) + \
                   ([] if ok_r else [f"it projects {_rr(r_mult, False)}, under the {MIN_STRUCTURAL_R:g}:1 minimum" if r_mult else "no objective"]) + \
                   ([f"it is the {_ordinal(cnt['n'])} base of its advance (at most the {_ordinal(MAX_BASE_COUNT)})"]
                    if cnt and MAX_BASE_COUNT and cnt["n"] > MAX_BASE_COUNT else [])
            zones.append({"key": "cheat", "title": "Cheat entry", "state": "pass" if not skip else "fail",
                          "from": c_from, "to": c_to, "illustration": True, "skip": skip,
                          "line": f"{third} third · buy {px(entry)} · stop {px(stop)}" + (f" · {_rr(r_mult, ok_r)}" if r_mult and MEASURED_MOVE_RR else ""),
                          "text": (f"Where this strategy's rules place a cheat entry: an illustration, not a recommendation "
                                   f"and not a backtest result. A cheat is bought while the base is still forming, before "
                                   f"the stock has recovered its old high, so its stop is close. On {c_from} the close "
                                   f"cleared a tight shelf ({cp['cheat_range_pct']:.1f}% over {CHEAT_SHELF_DAYS} sessions, "
                                   f"at most {CHEAT_SHELF_PCT:g}%) in the {third} third of the base. The buy is at the next "
                                   f"session's open, estimated here by that close, {px(entry)}. The stop goes {STOP_BUFFER_PCT:g}% under the shelf low, at {px(stop)}: "
                                   f"a risk of {risk_pct:.1f}% (the strategy skips anything over {MAX_STOP_PCT:g}%)."
                                   + ((f" The objective is the old high, {px(bh)}, plus the base's measured move"
                                       + (f" -- {px(c_uncapped)} -- capped by an older swing high at {px(target)}, at least "
                                          f"{OVERHEAD_CLUSTER_ATR:g} ATR above the base high: {px(target)}" if c_capped
                                          else f": {px(target)}")
                                       + (f", {_rr(r_mult, ok_r)} (it needs at least {MIN_STRUCTURAL_R:g}R)." if r_mult else "."))
                                      if MEASURED_MOVE_RR else _NO_TARGET)
                                   + f" Managing it is the same as any entry: the stop moves to breakeven at "
                                     f"+{BREAKEVEN_R:g}R, a third is sold at +{PARTIAL_R:g}R or once the close is "
                                     f"{STRENGTH_EXT_PCT:g}% above the 50-day average, the rest on a close below the 50-day, and it is sold after "
                                     f"{TIME_STOP_DAYS} sessions if it never reached +1R."
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": c_checks, "shapes": shapes})
            top = max(top, target if MEASURED_MOVE_RR else top, entry + BREAKEVEN_R * risk, float(cp["cheat_pivot"]))
            bottom = min(bottom, stop)
            frame_to = max(frame_to, c_to)

        # ---- the frame, its kind, title and verdict
        kind = "cheat" if traded_cheat and cheat else "vcp" if done else "cheat" if cheat else "young" if young else "fail"
        if kind == "vcp" and near:
            kind = "near"
        today = " · today" if live else ""
        if kind == "near":
            entries = [z for z in zones if z.get("illustration")]
            none_taken = bool(entries) and all(z["state"] == "fail" for z in entries)
            rule = near.split(":")[0]
            screened = bool(missed) and "screen" in missed and all(
                "screen" in s for z in entries for s in z.get("skip") or [])
            title = (f"Near miss ✓ · {rule}" + (f" · {self._refusal(missed)}" if screened else " · trade skipped" if none_taken else
                                                 f" · {self._refusal(missed)}" if missed else "")) + today
            summary = (f"Missed one rule narrowly ({near}) and passed the rest: S7 buys its breakout like a "
                       f"VCP's, as a setup of its own." + (f" It crossed the pivot on {day(bo)}, but the strategy "
                                                         f"would not have bought: {missed}." if bo is not None and missed
                                                         else f" Broke out on {day(bo)}, but {self._skip_why(zones)}."
                                                         if bo is not None and none_taken
                                                         else f" Broke out on {day(bo)}." if bo is not None
                                                         else " Waiting for a close through the pivot."))
        elif kind == "vcp":
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
            screened = bool(missed) and "screen" in missed and structure_ok and all(
                "screen" in s for z in entries for s in z.get("skip") or [])
            title = (f"VCP ✓ · {self._refusal(missed)}" if screened
                     else "VCP ✓ · trade skipped" if (none_taken or not structure_ok)
                     else f"VCP ✓ · {self._refusal(missed)}" if missed
                     else f"VCP ✓ · {'too illiquid' if 'illiquid' in screen else 'outside the Trend Template'}"
                     if screen and bo is None else "VCP setup ✓") + today
            summary = (f"A complete VCP. It crossed the pivot on {day(bo)}, but the strategy would not have bought: "
                       f"{missed}." if bo is not None and missed
                       else f"A complete VCP. Broke out on {day(bo)}, but {self._skip_why(zones)}."
                       if bo is not None and (none_taken or not structure_ok)
                       else f"A complete VCP. Broke out on {day(bo)}." if bo is not None
                       else f"A complete VCP, but the stock fails the strategy's screen on {at} -- {screen}: no buy "
                            f"until it passes on the breakout session." if screen
                       else "A complete VCP, waiting for a close through the pivot.")
        elif cheat:
            ok = zones[-1]["state"] == "pass"
            # The daily screen runs under the live variant, which may withhold this cheat. Said BESIDE the
            # shipped rules' verdict, not instead of it: a backtest of the shipped rules may have traded
            # this very cheat, and this endpoint cannot tell which run the chart is showing -- turning the
            # cheat into "skipped" here would contradict that run's own trade beside it.
            withheld = ok and self._live_withholds(cheat[2])
            title = f"Cheat entry {'✓' if ok else '· trade skipped'}{' · the live screen withholds it' if withheld else ''}{today}"
            if ok and stopped is not None:
                title = f"Cheat entry · stopped out {day(stopped)}"
            short = f"{len(depths)} pullback{'' if len(depths) == 1 else 's'}" if fail == "VCP-04" else self._VCP_FAILED.get(fail, fail)
            summary = (("A complete VCP, bought early through its cheat: on" if done else f"Not a VCP ({short}), but on")
                       + f" {day(cheat[0])} it cleared a tight "
                       f"shelf in the {'lower' if cheat[1] == MV03 else 'middle'} third of the base: a cheat entry."
                       + (f" The daily screen's live variant ({type(self).live_variant['name']}) withholds a cheat on "
                          f"a base that fails VCP-09, so it is not listed as a candidate." if withheld else "")
                       + (f" On {day(stopped)} the price came back through the stop: the trade was stopped out. The base "
                          f"can be bought again only if a setup fires on it once more (EN-04: up to "
                          f"{MAX_ENTRIES_PER_BASE} entries per base after a shakeout)." if ok and stopped is not None else ""))
        elif young:
            title = f"Too new to judge{today}"
            summary = f"Too new to judge: {young_why}."
        else:
            # the shape first, then why it does not qualify: "Base ✗ · …" beside "Power play ✗ · …"
            title = f"Base ✗ · {self._VCP_FAILED.get(fail, fail)}{today}"
            if fail == "VCP-04":   # the count says more than "wrong number"
                n, grew = len(depths), sum(b > WIDEN_TOL * a for a, b in zip(depths, depths[1:]))
                title = (f"Base ✗ · {n} pullback{'s' if n != 1 else ''}"
                         + (", growing" if n > MAX_CONTRACTIONS and grew * 2 > n - 1 else f" ({MIN_CONTRACTIONS}–{MAX_CONTRACTIONS} in a VCP)")
                         + today)
            summary = f"Not a VCP: {self._vcp_fail_why(r, daily, bh_i, rep)}."
        # the base count on the title of a base the strategy could buy from (a failed base has no setup to number)
        if cnt and kind in ("vcp", "near", "cheat"):
            tag = f" · {_ordinal(cnt['n'])} base" + (" (late)" if MAX_BASE_COUNT and cnt["n"] > MAX_BASE_COUNT else "")
            title = title[: -len(today)] + tag + today if today and title.endswith(today) else title + tag
        if live:
            summary = f"Still forming — judged on today's bar, {at}. " + summary
        # The setup -- its frame, its lane pill, a click's zoom -- spans the base and the move into it (VCP-01's
        # leg). Only the Uptrend arrow runs back to the advance's low: framing the whole advance drew a box and a
        # lane bar over years of chart for every late base, and with many bases the lanes were unreadable.
        return {"from": focus_from, "base_from": bd, "to": frame_to, "kind": kind, "complete": done, "fail": fail,
                "base_number": cnt["n"] if cnt else None,
                "breakout": day(bo) if bo is not None and not missed else None,
                "crossed": day(bo) if bo is not None and missed else None, "live": live, "as_of": at,
                "title": title, "summary": summary,
                # headroom above the highest level: the zone captions sit just inside the frame's top
                # edge, which was exactly the target's price, so "③ Entry" and "Target …" overprinted
                "frame": {"from": focus_from, "to": frame_to, "top": top + (top - bottom) * 0.08, "bottom": bottom},
                "advance_from": up_from,
                "zones": zones}

    @staticmethod
    def _cheat_refused(setup: dict, daily: pd.DataFrame, i: int, p: dict, n: int = 0) -> None:
        """Add to a base's `setup` (from `_setup`) the cheat the strategy refused on bar `i`: a close through the shelf
        `p` (yesterday's detection) measured, whose shelf failed `p["cheat_misses"]`. A zone with the shelf's checks
        and a box round the shelf, the reason in the title and summary. Never an entry: no buy, stop or target."""
        day = lambda k: str(daily.index[k].date())  # noqa: E731
        name = "3-C" if p["cheat_zone"] == "mid" else "Low cheat"
        third = "middle" if p["cheat_zone"] == "mid" else "lower"
        s_from, s_to = max(0, i - CHEAT_SHELF_DAYS), i - 1
        num = lambda v: v is not None and v == v  # noqa: E731
        checks = [
            {"code": "MV-03/04", "name": "Shelf width", "value": f"{p['cheat_range_pct']:.1f}%",
             "limit": f"at most {CHEAT_SHELF_PCT:g}% over {CHEAT_SHELF_DAYS} sessions",
             "state": "pass" if p["cheat_range_pct"] <= CHEAT_SHELF_PCT else "fail"},
        ] + ([
            {"code": "MV-03/04", "name": "Shelf volume",
             "value": f"{p['cheat_dryup']:.2f}x avg, {p['cheat_quiet_days']} quiet" if num(p.get("cheat_dryup")) else "—",
             "limit": f"at most {DRYUP_RATIO:g}x, or {DRYUP_QUIET_DAYS} sessions at or under {DRYUP_QUIET_RATIO:g}x",
             "state": "pass" if num(p.get("cheat_dryup")) and (p["cheat_dryup"] <= DRYUP_RATIO
                                                              or p["cheat_quiet_days"] >= DRYUP_QUIET_DAYS) else "fail"},
        ] if CHEAT_DRYUP else []) + ([
            {"code": "MV-03/04", "name": "Turn before the shelf",
             "value": (f"rally won back {p['cheat_rally'] * 100:.0f}%" + ("" if p.get("cheat_higher_low") else ", no higher low")
                       if num(p.get("cheat_rally")) else "—"),
             "limit": f"a higher low, then a rally of at least {CHEAT_RALLY_FRAC * 100:.0f}% of the decline",
             "state": "pass" if p.get("cheat_higher_low") and (p.get("cheat_rally") or 0) >= CHEAT_RALLY_FRAC else "fail"},
        ] if CHEAT_RALLY_FRAC else []) + ([
            {"code": "MV-03/04", "name": "Volume contraction",
             "value": f"{p['cheat_vol_vs_lead']:.2f}x the sessions before" if num(p.get("cheat_vol_vs_lead")) else "—",
             "limit": f"at most {CHEAT_VOL_CONTRACT:g}x",
             "state": "pass" if num(p.get("cheat_vol_vs_lead")) and p["cheat_vol_vs_lead"] <= CHEAT_VOL_CONTRACT else "fail"},
        ] if CHEAT_VOL_CONTRACT else [])
        why = "; ".join(p["cheat_misses"])
        setup["zones"].append({
            "key": f"cheat_miss{n}", "title": f"{name} refused", "state": "fail", "from": day(s_from), "to": day(i),
            "line": f"shelf {p['cheat_low']:.2f}–{p['cheat_pivot']:.2f} · crossed {day(i)}",
            "text": (f"A cheat the strategy saw and refused. On {day(i)} the close ({float(daily['close'].iloc[i]):.2f}) "
                     f"cleared the high of a shelf in the {third} third of the base ({p['cheat_pivot']:.2f}, the "
                     f"{CHEAT_SHELF_DAYS} sessions to {day(s_to)}) -- the {name} entry -- but the shelf failed its tests: "
                     f"{why}. No trade: the strategy buys a cheat only when every test passes."),
            "checks": checks,
            "shapes": [{"shape": "box", "from": day(s_from), "to": day(s_to), "top": p["cheat_pivot"],
                        "bottom": p["cheat_low"], "role": "stop", "dash": True, "label": f"{name} shelf ✗"}],
        })
        setup.setdefault("cheat_refused", []).append({"date": day(i), "zone": p["cheat_zone"], "shelf_high": p["cheat_pivot"],
                                                      "shelf_low": p["cheat_low"], "misses": list(p["cheat_misses"])})
        t, today, tag = setup["title"], " · today", f" · {name} ✗"
        if tag not in t:
            setup["title"] = (t[: -len(today)] + tag + today) if t.endswith(today) else t + tag
        setup["summary"] += (f" On {day(i)} the close cleared a {name} shelf in the {third} third of the base, but the "
                             f"strategy refused it: {why}.")

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
