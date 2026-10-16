"""Minervini SEPA: the VCP detector of the written backtest specification (research/minervini-backtest-spec.md),
traded and managed as the SEPA Learn guide describes ("SEPA and the VCP", research/learn-strat-vcp-sepa.md).

Up to 1.7 every rule followed the written spec. Since 1.8 the base, the setups and the entries still do,
while the stop limit, the exits, the market filter, the results blackout, the liquidity floor, progressive
exposure and the low cheat follow the guide (see the changelog). What differs from the retired `minervini`:

- **Base detection** (core/vcp_spec.py) anchors on the base high — the last confirmed swing high no
  later close has exceeded — and measures every contraction from there, with the spec's numbers:
  swing points of `SWING_K` bars each side, a prior advance of `PRIOR_ADVANCE_PCT`%, a base of
  `BASE_MIN_DAYS`–`BASE_MAX_DAYS` sessions, `MIN_CONTRACTIONS`–`MAX_CONTRACTIONS` contractions each at
  most `SHRINK` × the one before, the first no deeper than `MAX_FIRST_DEPTH_PCT`%, a final tight area of
  `TIGHT_DAYS` sessions within `TIGHT_PCT`%, a pivot within `PIVOT_NEAR_HIGH` of the base high, and
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

from ..config.base import MarketConfig
from ..core import vcp_spec
from ..core import swings as sw
from ..core.context import StockContext
from ..screens.criteria import (  # noqa: F401 (doc placeholders)
    MAX_PCT_BELOW_52W_HIGH, MIN_PCT_ABOVE_52W_LOW, RS_MIN_MOM, RS_MIN_RANK, SMA200_RISING_BARS,
)
from .base import LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan, tradable_point_in_time
from .trend_pullback import round_tick

MV01 = "S1"   # MV-01: confirmed breakout through the frozen pivot
MV02 = "S2"   # MV-02: coiled just below the pivot
MV03 = "S3"   # MV-03: low cheat, a shelf in the lower third of the base
MV04 = "S4"   # MV-04: cheat / 3C, a shelf in the middle third of the base

# ---- section 5: base and VCP (core/vcp_spec.py)
SWING_K = 5
MIN_SWING_PCT = 2.0
PRIOR_ADVANCE_PCT = 30.0
BASE_MIN_DAYS = 15
BASE_MAX_DAYS = 325
MIN_CONTRACTIONS = 2
MAX_CONTRACTIONS = 6
MAX_FIRST_DEPTH_PCT = 35.0
SHRINK = 0.80
TIGHT_DAYS = 10
TIGHT_PCT = 10.0
PIVOT_NEAR_HIGH = 0.90
DRYUP_RATIO = 0.70
VCP = vcp_spec.VcpParams(
    swing_k=SWING_K, min_swing_pct=MIN_SWING_PCT, prior_advance_pct=PRIOR_ADVANCE_PCT,
    base_min_days=BASE_MIN_DAYS, base_max_days=BASE_MAX_DAYS, min_contractions=MIN_CONTRACTIONS,
    max_contractions=MAX_CONTRACTIONS, max_first_depth_pct=MAX_FIRST_DEPTH_PCT, shrink=SHRINK,
    tight_days=TIGHT_DAYS, tight_pct=TIGHT_PCT, pivot_near_high=PIVOT_NEAR_HIGH, dryup_ratio=DRYUP_RATIO,
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

CHEAT_SHELF_DAYS = 7    # MV-03/MV-04: sessions in the shelf (mirrors VcpParams.cheat_shelf_days)
CHEAT_SHELF_PCT = 8.0   # MV-03/MV-04: widest shelf that counts  (mirrors VcpParams.cheat_shelf_pct)

STOP_BUFFER_PCT = 0.5   # SL-01: stop this % under the tight low
MAX_STOP_PCT = 10.0     # SL-03: skip a fill whose stop is further below it than this (the guide's limit)
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
# EX-02, the failed-breakout exit (a close back below the pivot within N sessions).
# OFF: the guide leaves a dip below the pivot to the stop, and dips are normal --
# on stored data about two in three breakouts close back below the pivot within ten
# sessions. In 1.7 this exit closed ~80% of trades for about -0.3R each.
FAIL_DAYS = 0
# EX-04, selling into strength: a part of the position once the close is this far
# above the 50-day average, at the next open. Replaces 1.7's "a third at 3R".
STRENGTH_EXT_PCT = 25.0
STRENGTH_FRAC = 1 / 3
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

MAX_POSITIONS = 8               # PF-02
MAX_OPEN_RISK_PCT = 6.0         # PF-04
MAX_ADV_PCT = 5.0               # SL-06
# No new buy with results due within this many calendar days: live from the earnings
# calendar, in a backtest from the stored results' filing dates (spec.results_blackout).
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


def vcp_measured_move(base_high, first_depth_pct) -> float:
    """A VCP's measured move: the base high less its deepest low, which (VCP-06 forces each
    contraction to shrink) is the first contraction's low. NaN when either is unknown."""
    return float(base_high) * float(first_depth_pct) / 100 if base_high and first_depth_pct else float("nan")


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
    mom = last.get("mom_12_1")
    if any(pd.isna(v) for v in (s50, s150, s200, s200_prev, lo52, hi52, mom)):
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
    if mom < RS_MIN_MOM:
        return False, f"12-1 momentum {mom:.2f} below {RS_MIN_MOM}"
    return True, "passed"


class MinerviniSpecStrategy(Strategy):
    selection = "time_series"
    family = "minervini"
    version = "1.9"
    changelog = (
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
    description = (
        "Minervini's SEPA as the Learn guide describes it: the Trend Template, a base-high anchored VCP, "
        "breakouts and buy-stops through the pivot plus the two cheat entries, a 10% stop limit, breakeven "
        "at 2R, a third sold into strength and the rest on a 50-day break, the guide's market filter, a "
        "results blackout and progressive exposure."
    )
    style = "breakout"

    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
    watch_codes = ("W1", "W2", "W3", "W4")
    setup_codes = (MV01, MV02, MV03, MV04)
    extra_columns = ("fundamentals_ok", "revenue_yoy_pct", "earnings_yoy_pct", "gross_margin_change_pp",
                     "pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                     "first_depth_pct", "last_depth_pct", "tightness_pct", "dryup_ratio", "breakout_volume_ratio",
                     "vcp_fail", "rs_mom")
    extra_numeric_columns = ("pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                             "first_depth_pct", "last_depth_pct", "tightness_pct", "dryup_ratio",
                             "breakout_volume_ratio", "rs_mom")
    needs_ctx_extras = True
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

    thesis = (
        "Minervini's SEPA — buy Stage-2 leaders as a volatility contraction completes, with small, capped "
        "losses against large winners — traded the way the Learn guide \"SEPA and the VCP\" describes it: "
        "the base is found by the written specification's exact rules, and the trade is managed, sized and "
        "filtered by the guide's."
    )
    how_it_works = (
        "Gates G1–G8 are the Trend Template (the Stage 2 screen's criteria): price above the 50/150/200-day "
        "averages, the averages stacked, the 200-day rising over {SMA200_RISING_BARS} sessions, at least "
        "{MIN_PCT_ABOVE_52W_LOW}% above the 52-week low and within {MAX_PCT_BELOW_52W_HIGH}% of the high, and "
        "an RS rating of {RS_MIN_RANK}+ across the market. A backtest applies that rating to the signals it "
        "collected rather than inside the per-bar scan, which cannot rank one symbol.",
        "The base starts at the base high: the most recent confirmed swing high ({SWING_K} bars either side, "
        "known only {SWING_K} bars later) that no close has exceeded since. It must follow a {PRIOR_ADVANCE_PCT}% "
        "advance, last {BASE_MIN_DAYS}–{BASE_MAX_DAYS} sessions, start with the full template in force, and keep "
        "the long averages in order every day of it.",
        "Contractions run from each swing high to the lowest low before the next. There must be "
        "{MIN_CONTRACTIONS}–{MAX_CONTRACTIONS}, the first no deeper than {MAX_FIRST_DEPTH_PCT}% and each at most "
        "{SHRINK} × the one before. Wiggles under {MIN_SWING_PCT}% are ignored.",
        "The final tight area is the last {TIGHT_DAYS} sessions: its high is the pivot, its low the tight low. "
        "It must span at most {TIGHT_PCT}%, the pivot must be within {PIVOT_NEAR_HIGH} of the base high, and its "
        "volume must have dried up to {DRYUP_RATIO} × the 50-day average.",
        "MV-02 (coiled): the base is complete and the close is within {COIL_PCT}% below the pivot. A buy-stop "
        "rests just above the pivot.",
        "MV-01 (breakout): the base was complete yesterday, yesterday's close was at or below yesterday's "
        "pivot and today's close is above it — on at least {VOL_MULT} × average volume, in the upper half of "
        "the day's range, and no more than {BUY_RANGE_PCT}% past the pivot. Bought at the next open.",
        "MV-03 / MV-04 (the low cheat and the \"3C\"): a short, tight shelf in the lower or middle third of "
        "a base that is still forming, bought on the close through the shelf's high and stopped under its low.",
        "Liquidity: 50-day average turnover of at least ₹{MIN_TURNOVER_INR_CR} crore or ${MIN_TURNOVER_USD_M} "
        "million a day; on the live screen also a price of at least ₹{LIVE_MIN_PRICE_INR} or "
        "${LIVE_MIN_PRICE_USD}. No new buy with results due within {EARNINGS_BLACKOUT_DAYS} days, or while "
        "the market filter is risk-off.",
    )
    caveats = (
        "**Survivorship bias.** The universe is today's listed stocks; companies delisted since are missing, "
        "which flatters every result.",
        "**Corporate actions.** Prices are adjusted when fetched; a split or bonus after a symbol's last full "
        "fetch shows as a crash until its history is re-fetched (`marketdata.splits`).",
        "**Relative strength** is cross-sectional, so where it is applied depends on what the caller can see. "
        "The daily screening run rates the whole market and gates G8 on the true RS rating of {RS_MIN_RANK}+. "
        "A backtest cannot do that inside a per-bar scan of one symbol, so G8 falls back to 12-1 month momentum "
        "of {RS_MIN_MOM}+ there and `--min-rs` applies the real rating to the collected signals — the same "
        "threshold, one step later. A single-symbol tool keeps the stand-in and is therefore looser than both.",
        "**Fundamentals (SEPA part 2) are optional in the backtest, off by default.** `--fundamentals guide` "
        "applies the Learn guide's tests (quarterly EPS up {FUND_EPS_GROWTH_MIN_PCT}%+ and faster than the "
        "quarter before, sales up {FUND_SALES_GROWTH_MIN_PCT}%+, net margin no more than "
        "{FUND_MARGIN_SLACK_PP} points below a year earlier); `leader|acceptable|covered` apply the "
        "Fundamentals page's stricter SEPA tests. Each uses the quarterly results public on the signal date "
        "(backtesting/fundamental_filter.py). Stored results start in late 2020 for India and 2009 for the US "
        "and cover part of the universe, so compare against `covered` (any scorable company), not the full run.",
        "**The results blackout** in a backtest uses the stored results' filing dates (India from late 2020, "
        "the US from 2009, part of the universe); a stock with no stored date near the signal is never blocked, "
        "so early Indian years run without it.",
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
    )
    status = (
        "1.8 (the Learn guide's management and filters, default backtest_args, 2010 onward): India 474 trades, "
        "+0.13R, profit factor 1.17, CAGR 1.49% against the index's 10.2%, max drawdown -17.5% (in sample to 2019 "
        "2.10% CAGR, after 0.59%). US 1,035 trades, -0.01R, profit factor 0.98, CAGR -0.29% against 12.1%, max "
        "drawdown -45.3%. So better than 1.7 in India (+0.13R against -0.03R) and worse in the US (1.7 with MKT-01: "
        "+0.06R, CAGR 1.34%, drawdown -28.6%). The 3C cheat (MV-04) is 80-88% of the trades; the low cheat (MV-03) "
        "lost again in India (74 trades, -0.12R) and broke even in the US; the pivot buys are too few to judge (19 "
        "and 35 MV-02, one MV-01). Stops cost most of the gross: India's 77 stop-outs lost Rs1.26m against Rs1.65m "
        "made on trend exits. Not yet isolated: whether the US shortfall comes from the guide's market filter -- "
        "open on fewer days than MKT-01 (67.5% against 77.0% since 2010) and agreeing with it on only 70% of "
        "days -- or from the other changes; a `--mkt01` run would separate them. "
        "Everything below measures 1.7's rules. No demonstrated edge (India, 2010 onward, `--spec`). Confirmed breakouts (EN-01): 9 trades in 16 years, "
        "CAGR −0.1% — the spec's base rules almost never complete on Indian daily data. Buy-stops (EN-02): 114 trades, "
        "expectancy −0.03R, profit factor 0.86, CAGR 0.1% against the index's ~12%, max drawdown −8.6%; the "
        "failed-breakout exit closes ~80% of trades for −0.3R each. No parameter at either end of the spec's test "
        "ranges, and no failed-breakout window, gives an edge that holds both in and out of sample "
        "(research/minervini-spec-sensitivity-india.md). US, same rules: EN-01 26 trades, −0.14R; EN-02 526 trades, "
        "−0.02R, CAGR −0.8% (index ~13%), max drawdown −30% — +0.05R to 2019, −0.12R since; the stricter variants that "
        "help in sample all turn negative after 2019 (research/minervini-spec-sensitivity-us.md). "
        "Adding the SEPA fundamentals point in time (`--fundamentals`, buy-stops, 2022-07 onward) did not help: "
        "against the `covered` control, LEADER-only fell from +0.28R to +0.27R per trade in India (7 trades) and "
        "from +0.02R to −0.40R in the US (19 trades), with CAGR shrinking as trades vanished. With US filings "
        "back to 2009, the 2010-onward grid (v1.6) agrees: `covered` +0.03R over 487 trades, `acceptable` -0.10R "
        "(115), `leader` +0.04R (24 — +0.58R to 2019, -0.72R since), against +0.04R unfiltered. "
        "The one rule that did pay is MKT-01 (`--market-filter`, now on by default): US 2010 onward, it "
        "blocked 163 of 1,325 signals and took 557 trades to 490, expectancy +0.04R to +0.06R, profit "
        "factor 1.04 to 1.10, P&L $5,137 to $11,198, CAGR 0.65% to 1.34%, max drawdown −43.5% to −28.6% "
        "— still short of the index, but the first change measured here to improve return and drawdown "
        "together. `--mkt-confirm 5` gives most of that back (CAGR 0.72%, drawdown −31.2%), so the "
        "re-entry delay is off by default."
    )

    gate_docs = {
        "G1": "TT-05: close above the 50-day average.",
        "G2": "TT-01: close above the 150-day average.",
        "G3": "TT-01: close above the 200-day average.",
        "G4": "TT-02 and TT-04: the 50-day above the 150-day above the 200-day.",
        "G5": "TT-03: the 200-day higher than {SMA200_RISING_BARS} sessions ago.",
        "G6": "TT-06: close at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low.",
        "G7": "TT-07: close within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.",
        "G8": "TT-08: an RS rating of {RS_MIN_RANK}+ (1-99 across the market) whenever the caller has rated "
              "the whole market — the daily screening run does. A one-symbol evaluation cannot rank, so "
              "`inspect --no-rs-rank` and the chart indicators fall back to 12-1 month momentum of "
              "{RS_MIN_MOM}+; a backtest also falls back here and applies the rating to the signals instead.",
    }
    watch_docs = {
        "W1": "Closed through the pivot on light volume — under {VOL_MULT} × the 50-day average (MV-01a), "
              "so not a confirmed breakout.",
        "W2": "Closed more than {BUY_RANGE_PCT}% past the pivot (MV-01b): extended beyond the buy range.",
        "W3": "Closed through the pivot but in the lower half of the day's range (MV-01c).",
        "W4": "Results are due within {EARNINGS_BLACKOUT_DAYS} days: no new buy (the plan is held at WATCH).",
    }
    setup_docs = {
        MV01: "MV-01 breakout: yesterday's base was complete, and today's close went through yesterday's pivot "
              "on volume, in the upper half of the range, within {BUY_RANGE_PCT}% of the pivot.",
        MV02: "MV-02 coiled: the base is complete and the close is within {COIL_PCT}% below the pivot.",
        MV03: "MV-03 low cheat (on since 1.8, {LOW_CHEAT_ENABLED}; `--const LOW_CHEAT_ENABLED=0` turns it off): "
              "a shelf of {CHEAT_SHELF_DAYS} sessions spanning no more than "
              "{CHEAT_SHELF_PCT}% sits in the LOWER third of a base that has cleared VCP-01/02/03, and "
              "today's close went through its high. Taken while the base is still forming, so the stop "
              "is the shelf low rather than the base low. Minervini calls this the riskiest of his "
              "three in-base entries and uses it mainly in stocks he already knows.",
        MV04: "MV-04 cheat (\"3C\"): the same shelf in the MIDDLE third of the base — the cup-completion "
              "cheat, entered as the base recovers but before it reaches its old high.",
    }
    entry_rules = (
        "MV-01 (EN-01): buy at the next session's open; skip it if that open is more than {BUY_RANGE_PCT}% "
        "above the pivot or at or below the tight low.",
        "MV-02 (EN-02): a buy-stop at the pivot plus 0.1%, resting for up to 10 sessions. It fills only on a "
        "session that CLOSES at or above the pivot, and fills at that close (or the stop price if the close is "
        "below it); a session that pokes through the pivot and closes back below leaves the order resting. It is "
        "skipped if the fill would be more than {BUY_RANGE_PCT}% above the pivot, and cancelled by a close below "
        "the tight low. A fill on a close whose volume is under {VOL_MULT} × the 50-day average is not a valid "
        "breakout: it is sold at the next open.",
        "Stop: {STOP_BUFFER_PCT}% under the tight low. A fill whose stop is more than {MAX_STOP_PCT}% below "
        "it is skipped. Size: 1% of equity at risk, capped at the market's position limit, and halved by "
        "progressive exposure while the recent record is not paying (see the exits).",
        "MV-03 / MV-04 (cheats): bought at the close of the session that clears the shelf high, stopped "
        "{STOP_BUFFER_PCT}% under the SHELF low rather than the base low — a nearby stop is the reason "
        "the entry exists. The objective is the base high plus the base's measured move from there.",
        "One entry per base: a base already traded is not entered again.",
        "Target: the base's measured move — its first (deepest) contraction projected from entry — "
        "capped by overhead supply at least {OVERHEAD_CLUSTER_ATR} ATR above the base high. A setup "
        "projecting under {MIN_STRUCTURAL_R}R on that basis is refused rather than padded up to it. "
        "{NOMINAL_TARGET_R}R remains the nominal figure used for sizing and reporting.",
    )
    exit_rules = (
        "In priority order, each session: EX-01 the stop (filled at the open if it gapped through); EX-03 "
        "once the high reaches {BREAKEVEN_R}R, the stop rises to breakeven plus costs; EX-04 selling into "
        "strength — once the close is {STRENGTH_EXT_PCT}% or more above the 50-day average, {STRENGTH_FRAC} of "
        "the position is sold at the next open; EX-05 a climax run once up 25% (the biggest up day on the "
        "biggest volume since entry, 8 of 10 up closes, 70% above the 200-day, or a 3% gap after a 50% gain) "
        "sells that same part if it has not been sold; EX-06 the rest goes on the first close below the 50-day "
        "average, at the next open; EX-07 a trade whose high has not reached +1R within {TIME_STOP_DAYS} "
        "sessions is sold at the next open.",
        "EX-02, the failed-breakout exit (a close back below the pivot within a few sessions), is off "
        "({FAIL_DAYS} sessions): the guide leaves a dip below the pivot to the stop. `--fail-days 5` restores it.",
        "Backtest: `--exit-mode minervini` in the portfolio simulator; the spec's run adds `--spec`, which "
        "sets {MAX_POSITIONS} positions, a {MAX_OPEN_RISK_PCT}% open-risk cap, a {MAX_ADV_PCT}% liquidity cap, "
        "RS ranking and the spec's costs.",
        "Sizing (PE-01 … PE-04, `--pe`, on by default since 1.8): an entry risks half the normal fraction "
        "while the last "
        "{PE_WINDOW} closed trades are not net positive, after two losing trades in a row, or during the "
        "first {PE_WARMUP} trades of the run, and the full fraction otherwise. `--pe-press` additionally "
        "allows 1.25x and two extra positions once the window is {PE_PRESS_NET_R}R up. The rule is read "
        "once per session from trades that closed on EARLIER sessions, so a stop-out this morning cannot "
        "resize an entry this afternoon. It aims at drawdown, not return.",
        "Market filter (`--market-filter`, the guide's since 1.8): new buys only while the benchmark closes "
        "above its {MKT_INDEX_SMA}-day average AND breadth — the share of the most-traded stocks above their "
        "own 50-day — is above {MKT_BREADTH_MIN_PCT}% or higher than {MKT_BREADTH_RISING_DAYS} sessions "
        "earlier. In risk-off no new entry is taken and any resting buy-stop is cancelled; open positions are "
        "never forced out. The live screen applies the same test. `--mkt01` restores 1.7's MKT-01 (the "
        "benchmark above its 200-day and its 50-day above its 200-day), the one 1.7 rule measured to help. "
        "`--mkt-confirm` makes risk-on wait that many sessions; it is off by default because, measured on "
        "MKT-01 at {MKT_CONFIRM_DAYS} sessions, it sat out the first days of recoveries.",
        "Results blackout (`--results-blackout`, {EARNINGS_BLACKOUT_DAYS} days by default with `--spec`): "
        "no new buy with results due within that many days.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "A confirmed breakout (MV-01): every Trend Template gate passes and the stop is "
                                 "within {MAX_STOP_PCT}% of entry. Buy at the next open. Watch flags never cap "
                                 "this strategy's decision.",
        "TRADE_ON_TRIGGER": "A valid plan that is not a confirmed breakout: either coiled within {COIL_PCT}% below "
                            "the pivot (MV-02), entered only if price trades through it on a resting buy-stop, or a "
                            "cheat (MV-03 / MV-04) that cleared its shelf on the close, bought at the next open and "
                            "stopped under the shelf low. The market regime never caps a decision to this tier.",
        "WATCH_WAIT": "A valid plan held back: its stop sits more than {MAX_STOP_PCT}% below entry, results are due "
                      "within {EARNINGS_BLACKOUT_DAYS} days, or the market filter allows no new buys (see the note "
                      "below). Worth watching, not buying.",
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
        ("Prior advance", "PRIOR_ADVANCE_PCT", "Rise into the base high from the low of the 126 sessions before (VCP-01)."),
        ("Base length, minimum", "BASE_MIN_DAYS", "Sessions from the base high (VCP-02)."),
        ("Base length, maximum", "BASE_MAX_DAYS", "About 65 weeks (VCP-02)."),
        ("Contractions, minimum", "MIN_CONTRACTIONS", "VCP-04."),
        ("Contractions, maximum", "MAX_CONTRACTIONS", "VCP-04."),
        ("First contraction, deepest", "MAX_FIRST_DEPTH_PCT", "VCP-05."),
        ("Shrink factor", "SHRINK", "Each contraction at most this × the previous (VCP-06)."),
        ("Tight area", "TIGHT_DAYS", "Sessions in the final tight area (VCP-08)."),
        ("Tight-area span", "TIGHT_PCT", "Deepest final contraction and widest tight area (VCP-08)."),
        ("Pivot near the base high", "PIVOT_NEAR_HIGH", "VCP-09."),
        ("Volume dry-up", "DRYUP_RATIO", "Tight-area volume against its 50-day average (VCP-10)."),
        ("Coil distance", "COIL_PCT", "MV-02: how far below the pivot still counts."),
        ("Breakout volume", "VOL_MULT", "MV-01a."),
        ("Buy range", "BUY_RANGE_PCT", "MV-01b, and the most a fill may sit above the pivot."),
        ("Stop buffer", "STOP_BUFFER_PCT", "SL-01."),
        ("Maximum stop", "MAX_STOP_PCT", "SL-03, checked at the fill."),
        ("Cheat shelf length", "CHEAT_SHELF_DAYS", "Sessions in the shelf a cheat is bought from (MV-03/MV-04)."),
        ("Cheat shelf tightness", "CHEAT_SHELF_PCT", "Widest shelf, high to low, that counts as a cheat."),
        ("Minimum reward-to-risk", "MIN_STRUCTURAL_R", "Setups whose measured move projects less are refused."),
        ("Overhead cluster", "OVERHEAD_CLUSTER_ATR", "ATRs above the base high before a swing high caps the target."),
        ("Positions", "MAX_POSITIONS", "PF-02, with --spec."),
        ("Breakeven trigger", "BREAKEVEN_R", "EX-03: R gained before the stop moves to breakeven plus costs."),
        ("Failed-breakout window", "FAIL_DAYS", "EX-02: sessions after entry in which a close below the pivot sells (0 = off)."),
        ("Sell into strength", "STRENGTH_EXT_PCT", "EX-04: % above the 50-day at which a part is sold."),
        ("Part sold into strength", "STRENGTH_FRAC", "EX-04 / EX-05: share of the position sold."),
        ("Climax sells a part", "CLIMAX_IS_PARTIAL", "EX-05: 1 = the strength part only, 0 = everything (1.7)."),
        ("Trend exit needs volume", "TREND_EXIT_NEEDS_VOLUME", "EX-06: 1 = only on above-average volume (1.7)."),
        ("Time stop", "TIME_STOP_DAYS", "EX-07: sessions to reach +1R (0 = off)."),
        ("Light-volume fill exit", "LIGHT_VOLUME_EXIT", "EN-02: sell a buy-stop fill on under-average breakout volume (1 = on)."),
        ("Low cheat", "LOW_CHEAT_ENABLED", "MV-03 on (1) or off (0)."),
        ("Results blackout", "EARNINGS_BLACKOUT_DAYS", "Days before results with no new buy."),
        ("Turnover floor, India", "MIN_TURNOVER_INR_CR", "₹ crore a day, 50-day average volume × close."),
        ("Turnover floor, US", "MIN_TURNOVER_USD_M", "$ million a day, 50-day average volume × close."),
        ("Price floor, India (live)", "LIVE_MIN_PRICE_INR", "₹; the live screen only."),
        ("Price floor, US (live)", "LIVE_MIN_PRICE_USD", "$; the live screen only."),
        ("Market filter", "MKT_GUIDE", "1 = the guide's test, 0 = MKT-01 (1.7)."),
        ("Index average", "MKT_INDEX_SMA", "Days in the benchmark's average the close must be above."),
        ("Breadth floor", "MKT_BREADTH_MIN_PCT", "% of stocks above their 50-day that counts as healthy."),
        ("Breadth rising over", "MKT_BREADTH_RISING_DAYS", "Sessions over which breadth may instead be rising."),
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
        return super().passes_prefilter(cfg, enriched_daily)

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
        cheat_cross = bool(ch and prev_close <= ch["cheat_pivot"] < close)
        mv03 = bool(LOW_CHEAT_ENABLED and cheat_cross and ch["cheat_zone"] == "low")
        mv04 = bool(cheat_cross and ch["cheat_zone"] == "mid")
        result.setups[MV01], result.setups[MV02] = mv01, mv02
        result.setups[MV03], result.setups[MV04] = mv03, mv04

        for code in ("W1", "W2", "W3"):
            on = bool(breakout and confirmed[code])
            result.watch_flags[code] = on
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = f"volume {vol_ratio:.2f}× its 50-day average"
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = f"{(close / base['pivot'] - 1) * 100:.1f}% above the pivot"
        if result.watch_flags["W3"]:
            result.watch_notes["W3"] = f"closed at {upper * 100:.0f}% of the day's range"
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
            tightness_pct=base["tight_range_pct"], dryup_ratio=base["dryup"],
            breakout_volume_ratio=vol_ratio if breakout else None,
            vcp_fail=base["fail"], breakout=breakout,
        )
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
        return 0.8 if result.setups.get(MV04) else (0.6 if result.setups.get(MV03) else 0.0)

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        cheat = result.setups.get(MV03) or result.setups.get(MV04)
        pivot, tl = e.get("pivot"), e.get("tight_low")
        # Only the pivot buy needs the FINAL tight area. A cheat is taken while the
        # base is still forming, so that area does not exist yet -- requiring it here
        # rejected 122 of 133 cheats before they reached their own branch.
        if not cheat and (not pivot or tl is None or pd.isna(tl)):
            return PlanChoice(None, None, "missing pivot / tight low")
        if cheat:
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
        # the base high less its deepest low, which (because VCP-06 forces each
        # contraction to shrink) is the first contraction's low.
        bh, first_depth = e.get("base_high"), e.get("first_depth_pct")
        if cheat and bh:
            # A cheat is bought below the old high, so the nearest objective is that
            # high; the base's own measured move is projected from there. first_depth
            # is absent when the base never reached the contraction step, in which
            # case the old high alone is the objective.
            measured_move = float(bh) - entry + (float(bh) * float(first_depth) / 100
                                                 if first_depth else 0.0)
        else:
            measured_move = vcp_measured_move(bh, first_depth)
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
        else:
            pivot, tl = float(e["pivot"]), float(e["tight_low"])
        meta = {"pivot": pivot, "tight_low": tl, "max_fill": pivot * (1 + BUY_RANGE_PCT / 100),
                "max_risk_pct": MAX_STOP_PCT / 100, "base_id": e.get("base_date"),
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
            "rs_mom": r("rs_mom", 3),
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
            note = (f"Base: highest high {bh:g} on {bd}, {e.get('base_days', '?')} sessions. "
                    f"{e.get('contractions', '?')} contractions shrinking {depths} (each must be ≤ {SHRINK:g}× the one before). ")
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

    def bases_live(self, daily: pd.DataFrame, cfg: MarketConfig) -> list[dict]:
        """Every VCP setup the detector saw over `daily`, for the chart's Trend template indicator:
        `vcp_spec.detect` with this strategy's VCP params, run ON DEMAND bar by bar (each bar sees only
        itself and earlier bars, as in the backtest). Exploration only: what a run traded comes from
        its stored signals (trade-anatomy), since current code may detect differently.

        A base is kept once some bar passed VCP-01 and VCP-02 (a real advance into it, a base of legal
        age); one the trend rule (VCP-03) then rejects is still drawn, as a failed setup saying why.
        Each is drawn from its most developed bar: the bar before the breakout when the VCP completed
        and broke out, else the last bar it was complete, else the bar that got furthest through
        VCP-04 … VCP-11. Returns one dict per setup (see `_setup`)."""
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
            b = bases.setdefault(r["bh_date"], {"best": i, "ok": [], "breakout": None})
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
        out = []
        for b in bases.values():
            bo = b["breakout"]
            rep = bo - 1 if bo is not None else b["ok"][-1] if b["ok"] else b["best"]
            out.append(self._setup(daily, cfg, dets[rep], rep, bo))
        return out

    # the VCP rules in the order the detector applies them, the zone of the setup each belongs to,
    # and the name the chart's checklist gives it
    _VCP_CHECKS = (("VCP-01", "uptrend", "Prior uptrend"), ("VCP-03", "uptrend", "Trend intact"),
                   ("VCP-02", "base", "Base length"), ("VCP-04", "base", "Pullbacks"),
                   ("VCP-05", "base", "First pullback"), ("VCP-06", "base", "Pullbacks shrink"),
                   ("VCP-08", "base", "Tight area"), ("VCP-09", "base", "Pivot near high"),
                   ("VCP-10", "base", "Volume dry-up"))
    _VCP_ORDER = ("VCP-01", "VCP-02", "VCP-03", "VCP-04", "VCP-05", "VCP-06", "VCP-08", "VCP-09", "VCP-10")
    # what a failed rule means, short enough for the setup's header
    _VCP_FAILED = {"VCP-03": "trend not intact", "VCP-04": "wrong number of pullbacks", "VCP-05": "first pullback too deep",
                   "VCP-06": "pullbacks don't shrink", "VCP-07": "lower lows", "VCP-08": "not tight enough",
                   "VCP-09": "pivot too far below the high", "VCP-10": "no volume dry-up", "VCP-11": "volatility didn't contract"}

    def _setup(self, daily: pd.DataFrame, cfg: MarketConfig, r: dict, rep: int, bo: int | None) -> dict:
        """One setup for the chart: a frame around it, and three zones — the uptrend into the base, the
        base and its contractions, and (for a completed VCP) the entry — each with its own shapes, its
        checklist rows and a writeup. The entry zone ILLUSTRATES where this strategy's own rules place
        the trade (pivot_buy_stop, pivot_stop, vcp_measured_move, the exit constants); it is not a
        backtest result, and the chart replaces it with a run's stored trade when one is selected.

        Returns {"from", "base_from", "to", "complete", "fail", "breakout", "title", "summary",
        "frame": {from, to, top, bottom}, "zones": [{key, title, state, from, to, line, text, checks,
        shapes}]}; shapes in the chart_anatomy schema."""
        day = lambda i: str(daily.index[i].date())
        iso = lambda ts: str(pd.Timestamp(ts).date())
        px = lambda v: f"{v:,.2f}" if v >= 1 else f"{v:.4g}"   # a price as the chart's scale shows it
        bh, bd, at = float(r["bh"]), iso(r["bh_date"]), day(rep)
        bh_i = daily.index.get_loc(r["bh_date"])
        end = bo if bo is not None else rep
        base_low = float(daily["low"].iloc[bh_i: rep + 1].min())
        depths, legs, fail, done = r["depths"], r["legs"], r["fail"], bool(r["ok"])
        stop_at = self._VCP_ORDER.index(fail) if fail in self._VCP_ORDER else len(self._VCP_ORDER)
        state = lambda code: "pass" if self._VCP_ORDER.index(code) < stop_at else \
            "fail" if self._VCP_ORDER.index(code) == stop_at else "skip"

        # ---- the checklist rows (a rule after the failing one was never measured: the detector stops there)
        up_days = bh_i - int(daily.index.get_loc(r["prior_low_date"])) if r["prior_low"] else None
        values = {
            "VCP-01": (f"+{r['prior_advance_pct']:.0f}% in {up_days} days" if up_days is not None else "—",
                       f"at least {PRIOR_ADVANCE_PCT:g}% within {VCP.prior_window} days"),
            "VCP-02": (f"{r['base_days']} days", f"{BASE_MIN_DAYS}–{BASE_MAX_DAYS} days"),
            "VCP-03": ("held" if fail != "VCP-03" else self._vcp_fail_why(r, daily, bh_i, rep),
                       "trend template on the high's bar, the 150/200-day structure after"),
            "VCP-04": (f"{len(depths)}" if depths else "—", f"{MIN_CONTRACTIONS}–{MAX_CONTRACTIONS}"),
            "VCP-05": (f"{depths[0]:.1f}%" if depths else "—", f"at most {MAX_FIRST_DEPTH_PCT:g}%"),
            "VCP-06": (" → ".join(f"{x:.1f}" for x in depths) + "%" if depths else "—", f"each at most {SHRINK:g}× the last"),
            "VCP-08": (f"{r['tight_range_pct']:.1f}%" if r["tight_range_pct"] is not None else "—", f"at most {TIGHT_PCT:g}%"),
            "VCP-09": (f"{(1 - r['pivot'] / bh) * 100:.1f}% under" if r["pivot"] else "—",
                       f"within {(1 - PIVOT_NEAR_HIGH) * 100:.0f}% of the high"),
            "VCP-10": (f"{r['dryup']:.2f}× normal" if r["dryup"] is not None else "—", f"at most {DRYUP_RATIO:g}×"),
        }
        checks = {z: [] for z in ("uptrend", "base", "entry")}
        for code, zone, name in self._VCP_CHECKS:
            checks[zone].append({"code": code, "name": name, "value": values[code][0], "limit": values[code][1],
                                 "state": state(code)})
        # a zone passes only when every rule in it passed; one with rules never reached is "skip"
        zstate = lambda z: "fail" if any(c["state"] == "fail" for c in checks[z]) else \
            "pass" if all(c["state"] == "pass" for c in checks[z]) else "skip"
        zones = []

        # ---- zone 1: the uptrend into the base
        if r["prior_low"]:
            pl, pd_ = float(r["prior_low"]), iso(r["prior_low_date"])
            up_from = pd_
            trend = ("The trend template held on the high's bar, and the 150/200-day structure held through the base."
                     if fail != "VCP-03" else f"But the trend was not intact: {self._vcp_fail_why(r, daily, bh_i, rep)}.")
            zones.append({"key": "uptrend", "title": "Uptrend", "state": zstate("uptrend"), "from": pd_, "to": bd,
                          "line": f"+{r['prior_advance_pct']:.0f}% in {up_days} days",
                          "text": (f"The stock rose {r['prior_advance_pct']:.0f}%, from {px(pl)} on {pd_} to {px(bh)} on {bd}, "
                                   f"in {up_days} sessions. A base only matters after a strong advance: at least "
                                   f"{PRIOR_ADVANCE_PCT:g}% within {VCP.prior_window} sessions. {trend}"),
                          "checks": checks["uptrend"],
                          "shapes": [{"shape": "line", "from": pd_, "to": bd, "p0": pl, "p1": bh, "role": "uptrend",
                                      "arrow": True, "label": f"+{r['prior_advance_pct']:.0f}%"}]})
        else:
            up_from = bd

        # ---- zone 2: the base and its contractions
        culprit = None   # the pullback a VCP-05 / VCP-06 failure is about
        if fail == "VCP-05":
            culprit = 0
        elif fail == "VCP-06":
            culprit = next(k for k in range(1, len(depths)) if depths[k] > SHRINK * depths[k - 1])
        base_shapes = [{"shape": "box", "from": bd, "to": at, "top": bh, "bottom": base_low, "role": "base", "shade": True,
                        "label": ""}]
        if legs:
            pts = []
            for k, (hd, h, ld, low) in enumerate(legs):
                mark = " ✗" if k == culprit else ""
                pts += [{"at": iso(hd), "price": float(h), "label": ""},
                        {"at": iso(ld), "price": float(low),
                         "label": f"{k + 1}{mark} · −{depths[k]:.1f}%" if k < len(depths) else ""}]
            base_shapes.append({"shape": "path", "from": bd, "to": at, "points": pts, "role": "contraction", "label": ""})
        tight = ""
        if r["tight_from"] is not None and r["pivot"]:
            tf, pv, tl = iso(r["tight_from"]), float(r["pivot"]), float(r["tight_low"])
            base_shapes.append({"shape": "box", "from": tf, "to": at, "top": pv, "bottom": tl, "role": "tight",
                                "label": f"tight {r['tight_range_pct']:.1f}%"})
            dry = (f", on volume {r['dryup']:.2f}× its 50-day average (at most {DRYUP_RATIO:g}×): sellers have dried up"
                   if r["dryup"] is not None else "")
            tight = (f" The last stretch is tight: {r['tight_range_pct']:.1f}% from {px(tl)} to {px(pv)} (at most "
                     f"{TIGHT_PCT:g}%){dry}. Its high, {px(pv)}, is the pivot.")
        pulls = (f" It pulled back {len(depths)} times: {' → '.join(f'{x:.1f}%' for x in depths)}. A VCP has "
                 f"{MIN_CONTRACTIONS}–{MAX_CONTRACTIONS} pullbacks, the first at most {MAX_FIRST_DEPTH_PCT:g}% deep, each "
                 f"at most {SHRINK:g}× the one before." if depths else "")
        verdict = "" if done or fail in (None, "VCP-03") else f" It failed here: {self._vcp_fail_why(r, daily, bh_i, rep)}."
        zones.append({"key": "base", "title": "Base", "state": zstate("base"), "from": bd, "to": at,
                      "line": f"{r['base_days']} days, {(1 - base_low / bh) * 100:.1f}% deep"
                              + (f", {len(depths)} pullbacks" if depths else ""),
                      "text": (f"{r['base_days']} sessions from the high of {px(bh)} on {bd} (a base lasts "
                               f"{BASE_MIN_DAYS}–{BASE_MAX_DAYS}), down to {px(base_low)} at its lowest.{pulls}{tight}{verdict}"),
                      "checks": checks["base"], "shapes": base_shapes})

        # ---- zone 3: the entry — illustrated from the strategy's own rules, for a completed VCP only
        top, bottom = bh, min(base_low, float(r["prior_low"]) if r["prior_low"] else base_low)
        entry_to = at
        if done:
            pv, tl = float(r["pivot"]), float(r["tight_low"])
            buy, stop = pivot_buy_stop(pv, cfg.tick_size), pivot_stop(tl, cfg.tick_size)
            risk = buy - stop
            mm = vcp_measured_move(bh, depths[0] if depths else None)
            target = buy + mm if mm == mm else None
            r_mult = (target - buy) / risk if target and risk > 0 else None
            risk_pct = risk / buy * 100
            e_i = bo if bo is not None else rep
            entry_to = day(min(len(daily) - 1, e_i + TIME_STOP_DAYS))
            e_from = at
            levels = [("buy", buy, f"Buy above {px(buy)}"), ("stop", stop, f"Stop {px(stop)} (−{risk_pct:.1f}%)"),
                      ("breakeven", buy + BREAKEVEN_R * risk, f"+{BREAKEVEN_R:g}R {px(buy + BREAKEVEN_R * risk)} · stop to breakeven")]
            if target:
                levels.append(("target", target, f"Target {px(target)} · {r_mult:.1f}R"))
            shapes = [{"shape": "level", "from": e_from, "to": entry_to, "price": v, "role": role, "label": lab,
                       "dash": role != "buy"} for role, v, lab in levels]
            if bo is not None:
                c = float(daily["close"].iloc[bo])
                shapes.append({"shape": "dots", "points": [{"at": day(bo), "price": c, "label": "breakout"}], "role": "buy"})
            ok_risk, ok_r = risk_pct <= MAX_STOP_PCT, (r_mult or 0) >= MIN_STRUCTURAL_R
            e_checks = [
                {"code": "SL-03", "name": "Risk", "value": f"{risk_pct:.1f}%", "limit": f"at most {MAX_STOP_PCT:g}%",
                 "state": "pass" if ok_risk else "fail"},
                {"code": "R:R", "name": "Reward / risk", "value": f"{r_mult:.1f}R" if r_mult else "—",
                 "limit": f"at least {MIN_STRUCTURAL_R:g}R", "state": "pass" if ok_r else "fail"},
            ]
            skip = [] if ok_risk else [f"risk is {risk_pct:.1f}%, over the {MAX_STOP_PCT:g}% limit"]
            if not ok_r:
                skip.append(f"it projects {r_mult:.1f}R, under the {MIN_STRUCTURAL_R:g}:1 minimum" if r_mult else "no measured move")
            happened = (f" It broke out on {day(bo)}." if bo is not None else " It has not broken out yet.")
            zones.append({"key": "entry", "title": "Entry", "state": "pass" if not skip else "fail", "from": e_from, "to": entry_to,
                          "illustration": True,
                          "line": f"buy {px(buy)} · stop {px(stop)}" + (f" · {r_mult:.1f}R" if r_mult else ""),
                          "text": (f"Where this strategy's rules place the trade: an illustration, not a recommendation and "
                                   f"not a backtest result. Buy with a buy-stop just above the pivot, at {px(buy)}; the "
                                   f"breakout counts only on volume of at least {VOL_MULT:g}× the 50-day average. The stop "
                                   f"goes {STOP_BUFFER_PCT:g}% under the tight-area low, at {px(stop)}: a risk of "
                                   f"{risk_pct:.1f}% a share (the strategy skips anything over {MAX_STOP_PCT:g}%)."
                                   + (f" The target is the base's measured move, its high less its first pullback's low, "
                                      f"projected from the buy: {px(target)}, {r_mult:.1f}R (it needs at least "
                                      f"{MIN_STRUCTURAL_R:g}R, before any overhead supply caps it)." if target else "")
                                   + f" Managing it: the stop moves to breakeven at +{BREAKEVEN_R:g}R; a third is sold "
                                     f"once the close is {STRENGTH_EXT_PCT:g}% above the 50-day average; the rest goes on a "
                                     f"close below the 50-day; and it is sold after {TIME_STOP_DAYS} sessions if it never "
                                     f"reached +1R." + happened
                                   + (f" The strategy would skip it: {' and '.join(skip)}." if skip else "")),
                          "checks": e_checks, "shapes": shapes})
            top = max(top, target or top, buy + BREAKEVEN_R * risk)
            bottom = min(bottom, stop)

        # ---- the frame, its title and the verdict
        if done:
            title = "VCP setup ✓" if all(z["state"] == "pass" for z in zones) else "VCP ✓ · trade skipped"
            summary = (f"A complete VCP. Broke out on {day(bo)}." if bo is not None
                       else "A complete VCP, waiting for a close through the pivot.")
        else:
            title = f"✗ {self._VCP_FAILED.get(fail, fail)}"
            summary = f"Not a VCP: {self._vcp_fail_why(r, daily, bh_i, rep)}."
        frame_to = entry_to if done else at
        return {"from": up_from, "base_from": bd, "to": frame_to, "complete": done, "fail": fail,
                "breakout": day(bo) if bo is not None else None, "title": title, "summary": summary,
                "frame": {"from": up_from, "to": frame_to, "top": top, "bottom": bottom}, "zones": zones}

    @staticmethod
    def _vcp_fail_why(r: dict, daily: pd.DataFrame, bh_i: int, rep: int) -> str:
        """The failing VCP rule of a detection, in words with its measured value and its limit."""
        d, f = r["depths"], r["fail"]
        if f == "VCP-03":
            if not r["base_tt"]:
                return (f"the trend template was not met on the high's bar ({daily.index[bh_i].date()}): "
                        f"{vcp_spec.template_miss(daily.iloc[bh_i])}")
            # the same structure test as vcp_spec._trend_held, located on the first bar that broke it
            for i in range(bh_i, rep + 1):
                row = daily.iloc[i]
                for bad, what in ((not row["sma150"] > row["sma200"], "the 150-day fell under the 200-day"),
                                  (not row["sma200"] > row["sma200_21d_ago"], "the 200-day turned down"),
                                  (not row["close"] > VCP.base_sma200_floor * row["sma200"],
                                   f"the close fell more than {(1 - VCP.base_sma200_floor) * 100:.0f}% under the 200-day")):
                    if bad:
                        return f"{what} on {daily.index[i].date()}, inside the base"
            return "the trend structure broke inside the base"
        if f == "VCP-04":
            return f"{len(d)} pullbacks, where a VCP has {MIN_CONTRACTIONS}–{MAX_CONTRACTIONS}"
        if f == "VCP-05":
            return f"the first pullback was {d[0]:.1f}% deep, more than {MAX_FIRST_DEPTH_PCT:g}%"
        if f == "VCP-06":
            k = next(k for k in range(1, len(d)) if d[k] > SHRINK * d[k - 1])
            return f"pullback {k + 1} ({d[k]:.1f}%) was not smaller than {SHRINK:g}× pullback {k} ({d[k - 1]:.1f}%)"
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
