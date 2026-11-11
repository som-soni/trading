"""Oliver Kell's cycle of price action -- draft 1 of research/kell-cycle-spec.md.

Kell trades the same leading growth stocks as Minervini, but reads each leader's trend as a repeating cycle
around its 10- and 20-day exponential averages and buys at several points in it: the wedge pop off a
sell-off, the first crossback to the rising averages, and the base-n-break. He sells a part into
exhaustion and the rest when the 20-day average breaks, then buys the leader again when the cycle restarts.

  * candidates: Minervini's Trend Template (the `stage2` screen, G1-G8), so a comparison with the minervini
    strategy isolates the entry and exit rules; SCREEN_LOOSE = 1 swaps it for the spec's looser variant;
  * the phases are core/kell_cycle.py's causal scan, with the numbers below;
  * entries: S1 wedge pop, S2 the first crossback after a WP or BB, S3 base-n-break, each bought at the
    signal session's close, sized so its stop risks the account's risk per trade. S4, a later crossback, only
    adds to a position already held;
  * management is the backtest's `--exit-mode kell` (backtesting/portfolio_sim.py): each tranche's own stop,
    1/EX_SELL_DIVISOR sold at the first exhaustion of a leg, the rest at the EMA break.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import kell_cycle as kc
from ..core.context import StockContext
# the Trend Template's thresholds, named here so the docs render them and the fingerprint covers them
from ..screens.criteria import (MAX_PCT_BELOW_52W_HIGH, MIN_PCT_ABOVE_52W_LOW,  # noqa: F401
                                RS_MIN_RANK, RS_MIN_SCORE, SMA200_RISING_BARS)
from .base import DOWNGRADE_MAP, LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan
from .minervini_spec import YOUNG_MIN_BARS, MinerviniSpecStrategy, _min_turnover
from .trend_pullback import round_tick

# ---- the cycle (evaluate() reads these, through _params(); spec section 2, draft-1 changes in section 4)
EXT_DOWN_ATR = 2.5        # RX: a close at least this many ATR under the 20-EMA
DOWN_DAYS = 5             # ... or this many closes in a row under both EMAs, also a WP's starting point
POP_LOOKBACK = 30         # WP: within this many sessions of that starting point
POP_HIGH_DAYS = 5         # WP: a close above the highest high of this many prior sessions
POP_VOL = 1.3             # WP: on volume at least this multiple of its 50-day average
CROSS_TOUCH_ATR = 0.5     # CB: yesterday's low within this many ATR of the 20-EMA (or under it)
BASE_MIN_DAYS = 10        # BB: the prior this-many sessions ...
BASE_MAX_WIDTH_PCT = 15.0  # ... span at most this % high to low
BREAK_VOL = 1.4           # BB: on volume at least this multiple of its 50-day average
EXH_ATR = 3.0             # EX: a close at least this many ATR above the 10-EMA ...
GAP_ATR = 1.0             # ... or a gap up of this many ATR ...
GAP_PRIOR_ATR = 2.0       # ... after a close already this many ATR above the 10-EMA
UP_SLOPE_DAYS = 5         # uptrend: the 20-EMA above its value this many sessions earlier
UP_CROSS_DAYS = 5         # uptrend: the 10-EMA above the 20-EMA on each of the last this-many sessions (draft 1)
BREAK_MODE = 1            # BK: 1 a close under the 20-EMA by BREAK_ATR ATR; 2 a close under the latest crossback's low
BREAK_ATR = 0.5

# ---- the screen (prefilter_row and evaluate() read these)
SCREEN_LOOSE = 0          # 1: RS and within LOOSE_MAX_PCT_BELOW_52W_HIGH of the high, instead of the whole template
LOOSE_MAX_PCT_BELOW_52W_HIGH = 35.0

# ---- after the scan (build_plans / classify / the backtest's --exit-mode kell read these)
MAX_STOP_PCT = 8.0        # a BB's stop (the base low) is raised to at most this % under the entry
MIN_STOP_ATR = 0.0        # research switch (0 = off): a one-bar stop (S1, S2, S4) at least this many ATR under the entry
NOMINAL_TARGET_R = 10     # a far target for the plan's R column only; the backtest has no target
EX_SELL_DIVISOR = 3       # the exhaustion sale: 1/this of the shares held, once per leg

S1, S2, S3, S4 = "S1", "S2", "S3", "S4"
ADD_ONLY = (S4,)

# the volume thresholds the wedge-pop diagnostic counts pops at (spec section 4; reported, never tuned)
POP_VOL_DIAGNOSTIC = (1.0, 1.3, 1.6)

_MV = MinerviniSpecStrategy()


def _params() -> kc.CycleParams:
    """The scan's numbers, read at call time, so a `--const` override is the one used."""
    return kc.CycleParams(
        ext_down_atr=EXT_DOWN_ATR, down_days=DOWN_DAYS, pop_lookback=POP_LOOKBACK, pop_high_days=POP_HIGH_DAYS,
        pop_vol=POP_VOL, cross_touch_atr=CROSS_TOUCH_ATR, base_min_days=BASE_MIN_DAYS,
        base_max_width=BASE_MAX_WIDTH_PCT / 100, break_vol=BREAK_VOL, exh_atr=EXH_ATR, gap_atr=GAP_ATR,
        gap_prior_atr=GAP_PRIOR_ATR, up_slope_days=UP_SLOPE_DAYS, up_cross_days=UP_CROSS_DAYS,
        break_mode=BREAK_MODE, break_atr=BREAK_ATR)


def cycle_frame(df: pd.DataFrame) -> pd.DataFrame:
    """The whole frame's phases (backtesting/portfolio_sim.py's `--exit-mode kell` reads EX, BK and leg)."""
    return kc.scan(df, _params())


class KellCycleStrategy(Strategy):
    key = "kell_cycle"
    name = "Kell cycle of price action"
    version = "1.2"
    # 1.1 changes only the market filter, 1.2 only the stop: both after the scan.
    signal_version = "1.0"
    changelog = (
        ("1.2", "2026-11-11",
         "A research switch, off by default: MIN_STOP_ATR (now {MIN_STOP_ATR}) moves a one-bar stop (S1, S2, S4) "
         "down to at least that many ATR under the entry when the bar's low is closer. The 1.1 optimise runs "
         "stopped out 49% of US trades against 37% in India, with S1 stops a median 0.97 ATR wide in the US and 1.46 "
         "in India; the variant tests 1.5 ATR. Plan only, so signal_version stays 1.0."),
        ("1.1", "2026-11-11",
         "The market filter is the minervini strategy's test, and its 1.64 adds the segment's trend: no new buy "
         "unless the small- and mid-cap index (Nifty Smallcap 250, IWM) is up over 63 sessions. Measured on "
         "minervini's trades, not on this strategy's. After the scan, so signal_version stays 1.0."),
        ("1.0", "2026-11-10",
         "Draft 1 of research/kell-cycle-spec.md: the draft-0 phase definitions with the four changes the chart check "
         "settled. Only the first crossback after a wedge pop or base-n-break is an entry (later ones add to a position "
         "held); the EMA break is a close {BREAK_ATR} ATR under the 20-EMA (BREAK_MODE 1) or under the latest "
         "crossback's low (BREAK_MODE 2); exhaustion sells 1/{EX_SELL_DIVISOR} once per leg; the uptrend test needs "
         "the 10-EMA above the 20-EMA for {UP_CROSS_DAYS} sessions. No backtest informed any number."),
    )
    description = (
        "Leaders in a Trend Template uptrend, bought at three points of Kell's cycle around the 10- and 20-day EMAs "
        "(wedge pop, first crossback, base-n-break), part sold into exhaustion, the rest at the EMA break."
    )
    style = "trend"
    horizon = "swing"
    selection = "time_series"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
    screen_key = "stage2"
    screen_gates = {"G1": "C1", "G2": "C2", "G3": "C3", "G4": "C4", "G5": "C5", "G6": "C6", "G7": "C7", "G8": "C8"}
    watch_codes = ()
    setup_codes = (S1, S2, S3, S4)
    setup_names = {S1: "Wedge pop", S2: "First EMA crossback", S3: "Base-n-break", S4: "Later crossback (add only)"}
    gate_titles = {
        "G1": "Above the 50-day", "G2": "Above the 150-day", "G3": "Above the 200-day", "G4": "Averages stacked",
        "G5": "200-day rising", "G6": "Off the 52-week low", "G7": "Near the 52-week high", "G8": "Relative strength",
    }
    nominal_target = True
    min_bars = 300
    min_signal_bars = YOUNG_MIN_BARS
    needs_ctx_extras = True
    extra_columns = ("kell_leg", "wp_stop", "cb_stop", "bb_stop", "bb_top", "break_ref")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = ("MAX_STOP_PCT", "MIN_STOP_ATR", "NOMINAL_TARGET_R", "EX_SELL_DIVISOR")

    thesis = (
        "A leading stock's advance is not one move but a cycle that repeats: it is stretched down and sellers tire, "
        "it pops back over its short averages, pulls back to them, rests and breaks out, runs until it is stretched "
        "up, and breaks its averages. Buying the early points of each cycle with the stop under that day's low makes "
        "the position large for its risk exactly where being wrong is cheapest; selling part into the stretch and "
        "the rest at the break keeps most of the leg; and buying the leader again when the cycle restarts keeps the "
        "account in the stocks that are working."
    )
    how_it_works = (
        "**The idea.** Oliver Kell, the 2020 US Investing Championship winner, as fixed in research/kell-cycle-spec.md "
        "(draft 1). The rules are first guesses at his words, set before any backtest.",
        "**Qualify.** Minervini's Trend Template, the same candidates as the minervini strategy (G1-G8). With "
        "SCREEN_LOOSE = 1 (now {SCREEN_LOOSE}) only the relative strength (G8) and a close within "
        "{LOOSE_MAX_PCT_BELOW_52W_HIGH}% of the 52-week high (G7) are asked, because a wedge pop can come before the "
        "slow averages line up.",
        "**The cycle.** One pass over the daily bars finds six phases around the 10- and 20-day EMAs: reversal "
        "extension, wedge pop, crossback, base-n-break, exhaustion and EMA break (the phase table above).",
        "**Buy.** A wedge pop (S1), the first crossback after a wedge pop or base-n-break (S2), or a base-n-break (S3) "
        "on a session that passes every gate, at that session's close. Each is sized so that its own stop risks the "
        "account's risk per trade.",
        "**Add.** In a stock already held, any of those, or a later crossback (S4), adds a tranche with its own stop, "
        "sized the same way, while every earlier tranche is in profit and the position is under its full size "
        "(Max position size of equity).",
        "**Sell.** Each tranche at its own stop; 1/{EX_SELL_DIVISOR} of what is held at the first exhaustion of each "
        "leg; everything left at the EMA break. A stock sold at a break is bought again at its next wedge pop or "
        "base-n-break.",
        "**Portfolio rules.** The backtest runs with the minervini strategy's portfolio rules (`--spec`): its costs, "
        "positions, RS rating of {RS_MIN_RANK}+, ranking, caps and market filter, without its results blackout.",
    )
    pattern_title = "The cycle's phases"
    pattern_intro = (
        "Bars are daily. EMA10 and EMA20 are exponential averages of the close; ATR is the 14-day Wilder ATR. An "
        "**uptrend** session has the 10-EMA above the 20-EMA on each of the last {UP_CROSS_DAYS} sessions, the 20-EMA "
        "above its value {UP_SLOPE_DAYS} sessions earlier, and the close above the 50-day simple average. The cycle is "
        "*in an uptrend* from the first such session, or a wedge pop, until an EMA break. A **leg** starts at each "
        "wedge pop, crossback and base-n-break."
    )
    pattern_docs = {
        "RX": "Reversal extension: a close at least {EXT_DOWN_ATR} ATR under the 20-EMA. Marks where a wedge pop may "
              "start; never a trade.",
        "WP": "Wedge pop: within {POP_LOOKBACK} sessions of an RX or of {DOWN_DAYS} closes in a row under both EMAs, "
              "and the cycle not in an uptrend, a close above both EMAs and above the highest high of the prior "
              "{POP_HIGH_DAYS} sessions, on volume at least {POP_VOL} × its 50-day average. Stop: that day's low.",
        "CB": "EMA crossback: today and yesterday are uptrend sessions; yesterday's low came within {CROSS_TOUCH_ATR} "
              "ATR of the 20-EMA (or under it) and yesterday closed at or above it; today closes above yesterday's "
              "high. Stop: yesterday's low. Only the first after a WP or BB in the cycle is an entry.",
        "BB": "Base-n-break: in an uptrend, the prior {BASE_MIN_DAYS} sessions span at most {BASE_MAX_WIDTH_PCT}% "
              "high to low, yesterday closed at or under their high and today closes above it, on volume at least "
              "{BREAK_VOL} × its 50-day average. Stop: the base low, raised to {MAX_STOP_PCT}% under the entry if "
              "it is further.",
        "EX": "Exhaustion: in an uptrend, a close at least {EXH_ATR} ATR above the 10-EMA, or a gap up (open above "
              "yesterday's high) of {GAP_ATR} ATR or more after a close already {GAP_PRIOR_ATR} ATR above it.",
        "BK": "EMA break: while the cycle is in an uptrend. BREAK_MODE 1 (now {BREAK_MODE}): a close under the "
              "20-EMA by at least {BREAK_ATR} ATR. BREAK_MODE 2: a close under the most recent crossback's low "
              "(before any crossback, under the latest WP or BB stop). Ends the cycle's uptrend.",
    }
    caveats = (
        "**Draft definitions.** Every number is a first guess at Kell's words, fixed before any backtest (spec "
        "section 2), with four changes from a check by eye on five famous leaders (section 4). Those leaders were "
        "chosen after the fact.",
        "**Daily bars, not his entries.** Kell buys during the session and uses intraday stops. This buys the close of "
        "a session that has already moved.",
        "**The leader was picked first.** Candidates must pass the Trend Template, which lags at a turn; a wedge pop "
        "off a deep low often comes before it. SCREEN_LOOSE = 1 tests a looser screen.",
        "**Survivorship.** The universe is today's stock lists, which leave out the leaders that collapsed.",
        "**One trade row per position.** Adds and partial sales are folded into one trade: its R is the profit over "
        "the sum of every tranche's risk at its fill.",
        "**Fills at the stop.** On a day that does not gap through a stop, it fills at its price.",
        "**No results rule.** Kell's handling of results dates is not coded; positions are held through them.",
        "**Run it with its flags.** `--spec --exit-mode kell --no-target --market-filter --results-blackout 0` (the "
        "page's backtest command adds them).",
    )
    status = (
        "Draft 1, built 2026-11-10. First optimise-stage runs of 1.0 (2013-2021, in-sample): India 15.3% CAGR, "
        "-35.2% max drawdown, +0.27R a trade; US 2.3%, -24.1%, +0.00R; neither market passed all three criteria. "
        "The US stopped out 49% of trades (India 37%); the MIN_STOP_ATR variant is queued. Pass "
        "criteria (spec section 6, fixed before any run): expectancy at least +0.30R a trade in India and above zero "
        "in the US; a higher CAGR than the minervini strategy's best like-for-like run in each market at a maximum "
        "drawdown no more than 5 points deeper; with the best 5% of trades removed, expectancy above zero in India."
    )
    gate_docs = {
        "G1": "Trend Template C1: the close is above the 50-day moving average.",
        "G2": "Trend Template C2: the close is above the 150-day moving average.",
        "G3": "Trend Template C3: the close is above the 200-day moving average.",
        "G4": "Trend Template C4: the 50-day average is above the 150-day, which is above the 200-day.",
        "G5": "Trend Template C5: the 200-day average is higher than {SMA200_RISING_BARS} sessions ago.",
        "G6": "Trend Template C6: the close is at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low.",
        "G7": (
            "Trend Template C7: the close is within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.\n\n"
            "- **Loose screen:** with SCREEN_LOOSE = 1 (now {SCREEN_LOOSE}), within "
            "{LOOSE_MAX_PCT_BELOW_52W_HIGH}% instead, and G1-G6 are not asked."
        ),
        "G8": (
            "Trend Template C8: relative strength.\n\n"
            "- **In the scan:** the weighted RS score is at least {RS_MIN_SCORE}.\n"
            "- **In the backtest:** the signal's stock must also rate {RS_MIN_RANK}+ (1-99 across the market) on "
            "the signal date (`--spec`)."
        ),
    }
    watch_docs = {}
    setup_docs = {
        S1: (
            "Wedge pop: today is a WP (phase table).\n\n"
            "- **Stop:** today's low; with MIN_STOP_ATR above 0 (now {MIN_STOP_ATR}), at least that many ATR under the entry.\n"
            "- **Entry:** a new position, or an add to one held."
        ),
        S2: (
            "The first EMA crossback after a wedge pop or base-n-break: today is a CB, and no CB has come since the "
            "cycle's latest WP or BB.\n\n"
            "- **Stop:** yesterday's low; with MIN_STOP_ATR above 0 (now {MIN_STOP_ATR}), at least that many ATR under the entry.\n"
            "- **Entry:** a new position, or an add to one held."
        ),
        S3: (
            "Base-n-break: today is a BB (phase table).\n\n"
            "- **Stop:** the base low, but no more than {MAX_STOP_PCT}% under the entry.\n"
            "- **Entry:** a new position, or an add to one held."
        ),
        S4: (
            "A later crossback: today is a CB that is not the first since the cycle's latest WP or BB, or comes in a "
            "cycle with no WP or BB yet.\n\n"
            "- **Stop:** yesterday's low; with MIN_STOP_ATR above 0 (now {MIN_STOP_ATR}), at least that many ATR under the entry.\n"
            "- **Only an add.** It never opens a position."
        ),
    }
    entry_rules = (
        "Signal. S1, S2, S3 or S4 on a session that passes G1-G8, graded TRADE - HIGH CONFIDENCE. When several fire on "
        "one session the plan takes the first of S1, S2, S3, S4.",
        "Order. Buy at that session's close (backtest: a close order, filled that session, plus slippage). S4 only adds.",
        "Add (backtest). A signal in a stock already held, on a later session, buys another tranche at that close when "
        "every earlier tranche was bought below it and the position's value is under Max position size × equity.",
        "Market. No new buy or add on a session the market filter is risk-off (`--market-filter`, the minervini "
        "strategy's test under `--spec`).",
    )
    stop_rules = (
        "Where it goes. S1: the pop day's low. S2 and S4: the low of the session before the crossback. With "
        "MIN_STOP_ATR above 0 (now {MIN_STOP_ATR}), S1, S2 and S4 stops sit at least that many ATR under the entry. "
        "S3: the base low, raised to {MAX_STOP_PCT}% under the entry if further. Rounded down to the tick; it defines that "
        "tranche's 1R.",
        "Each tranche keeps its own stop (backtest). The first session whose low touches it sells that tranche at the "
        "stop, or at the open if it opened below it. Stops never move.",
    )
    target_rules = (
        "There is no sell order at the target. The target is entry + {NOMINAL_TARGET_R} R, so that the plan has an "
        "R column. The backtest runs with `--no-target`.",
    )
    exit_rules = (
        "Each session after the entry, in this order (backtest, `--exit-mode kell`):",
        "1. The stops: each tranche whose stop is touched sells (see Stop).",
        "2. The EMA break: a BK session sells everything left at its close.",
        "3. The exhaustion sale: on the first EX session of a leg, 1/{EX_SELL_DIVISOR} of the shares held sells at "
        "the close, taken from every tranche alike. Once per leg.",
        "No other exits. A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based, per tranche. Shares = (equity × Risk per trade) ÷ (price paid − that tranche's stop), rounded "
        "down, and the whole position capped at Max position size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots and caps. The minervini strategy's position count and open-risk cap (`--spec`); an add that would breach "
        "the open-risk cap is skipped.",
    )
    filter_rules = (
        "Liquidity and history: the minervini strategy's turnover floor and young-listing rule, so the candidates are "
        "its own.",
    )
    param_docs = (
        ("Reversal stretch", "EXT_DOWN_ATR", "RX: ATRs under the 20-EMA."),
        ("Down closes", "DOWN_DAYS", "Closes in a row under both EMAs that also start a wedge-pop window."),
        ("Pop window", "POP_LOOKBACK", "WP: sessions after an RX or down run in which a pop counts."),
        ("Pop high", "POP_HIGH_DAYS", "WP: the close clears the highest high of this many prior sessions."),
        ("Pop volume", "POP_VOL", "WP: volume multiple of the 50-day average."),
        ("Crossback touch", "CROSS_TOUCH_ATR", "CB: how close, in ATR, yesterday's low came to the 20-EMA."),
        ("Base length", "BASE_MIN_DAYS", "BB: sessions in the base."),
        ("Base width", "BASE_MAX_WIDTH_PCT", "BB: the base's high-to-low span, %, at most."),
        ("Breakout volume", "BREAK_VOL", "BB: volume multiple of the 50-day average."),
        ("Exhaustion stretch", "EXH_ATR", "EX: ATRs above the 10-EMA."),
        ("Exhaustion gap", "GAP_ATR", "EX: a gap up of this many ATR ..."),
        ("Gap after stretch", "GAP_PRIOR_ATR", "EX: ... after a close this many ATR above the 10-EMA."),
        ("Uptrend slope", "UP_SLOPE_DAYS", "Uptrend: the 20-EMA above its value this many sessions earlier."),
        ("Uptrend cross", "UP_CROSS_DAYS", "Uptrend: sessions the 10-EMA has been above the 20-EMA."),
        ("Break mode", "BREAK_MODE", "BK: 1 a close under the 20-EMA by Break depth; 2 under the latest crossback's low."),
        ("Break depth", "BREAK_ATR", "BK (mode 1): ATRs under the 20-EMA."),
        ("Loose screen", "SCREEN_LOOSE", "1: RS and within Loose high distance of the high only (G7, G8)."),
        ("Loose high distance", "LOOSE_MAX_PCT_BELOW_52W_HIGH", "G7 with the loose screen: % below the 52-week high."),
        ("Maximum BB stop", "MAX_STOP_PCT", "S3: the stop is at most this % under the entry."),
        ("Minimum one-bar stop", "MIN_STOP_ATR", "S1, S2, S4: the stop is at least this many ATR under the entry "
         "(0 = off, the bar's low as it is). A research switch."),
        ("Exhaustion sale", "EX_SELL_DIVISOR", "1/this of the shares sells at a leg's first exhaustion."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a backtest loads before its start."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity each tranche risks between its price and its stop."),
        ("Max position size", "cfg.max_position_pct", "A position's full size, as a fraction of equity."),
        ("Tick size", "cfg.tick_size", "Stops are rounded down to this increment."),
    )
    backtest_args = "--spec --exit-mode kell --no-target --market-filter --results-blackout 0"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        if not SCREEN_LOOSE:
            return _MV.prefilter_row(cfg, last)
        floor = _min_turnover(cfg, getattr(last, "name", None))
        v50, close, hi, rs = last.get("vol_sma50"), last.get("close"), last.get("high_252"), last.get("rs_score")
        if any(pd.isna(x) for x in (v50, close, hi, rs)):
            return False, "insufficient history"
        if float(v50) * float(close) < floor:
            return False, f"turnover below {floor:,.0f} a day"
        if hi <= 0 or close < hi * (1 - LOOSE_MAX_PCT_BELOW_52W_HIGH / 100):
            return False, f"more than {LOOSE_MAX_PCT_BELOW_52W_HIGH:g}% below the 52-week high"
        if rs < RS_MIN_SCORE:
            return False, f"RS score {rs:.2f} below {RS_MIN_SCORE}"
        return True, "passed"

    def passes_prefilter(self, cfg: MarketConfig, enriched_daily) -> tuple[bool, str]:
        if not SCREEN_LOOSE:
            return _MV.passes_prefilter(cfg, enriched_daily)
        return super().passes_prefilter(cfg, enriched_daily)

    def prefilter_mask(self, cfg: MarketConfig, enriched_daily) -> "pd.Series":
        if not SCREEN_LOOSE:
            return _MV.prefilter_mask(cfg, enriched_daily)
        return super().prefilter_mask(cfg, enriched_daily)

    def rs_young_min_bars(self) -> int:
        return _MV.rs_young_min_bars()

    def apply_screen(self, ctx, result: StrategyResult) -> None:
        if not SCREEN_LOOSE:
            return super().apply_screen(ctx, result)
        from ..screens import criteria as crit
        for g in ("G1", "G2", "G3", "G4", "G5", "G6"):
            result.ok(g, "loose screen: not asked")
        pct = crit._pct_below_52w_high(ctx)
        ctx.extras["pct_below_52w_high"] = pct
        (result.ok if pct <= LOOSE_MAX_PCT_BELOW_52W_HIGH else result.fail)("G7", f"{pct:.1f}% below the 52-week high")
        ok, note = crit.stage2_rs(ctx)
        (result.ok if ok else result.fail)("G8", note)

    # ---------- gates and setups ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        row = kc.last(ctx.symbol, ctx.daily, _params())
        cb, first = bool(row.get("cb")), bool(row.get("cb_first"))
        result.setups[S1] = bool(row.get("wp"))
        result.setups[S2] = cb and first
        result.setups[S3] = bool(row.get("bb"))
        result.setups[S4] = cb and not first
        e = ctx.extras
        e["kell_leg"] = row.get("leg")
        for k in ("wp_stop", "cb_stop", "bb_stop", "bb_top", "break_ref"):
            v = row.get(k)
            e[k] = float(v) if v is not None and v == v else None
        result.recompute_first_fail()
        return result

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.has_setup else 0.0

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        setup = next((c for c in self.setup_codes if result.setups.get(c)), None)
        if setup is None:
            return PlanChoice(None, None, "no active setup")
        entry = float(ctx.close)
        e = ctx.extras
        level = {S1: e.get("wp_stop"), S2: e.get("cb_stop"), S3: e.get("bb_stop"), S4: e.get("cb_stop")}[setup]
        if level is None:
            return PlanChoice(None, None, f"{setup}: no stop level recorded")
        if setup == S3:
            level = max(float(level), entry * (1 - MAX_STOP_PCT / 100))
        elif MIN_STOP_ATR > 0:
            level = min(float(level), entry - MIN_STOP_ATR * ctx.atr)
        stop = round_tick(float(level), cfg.tick_size, "down")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(plan="K", setup=setup, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry,
                         r_multiple=NOMINAL_TARGET_R if risk > 0 else float("nan"),
                         nearest_overhead_above_entry=None)
        return PlanChoice(plan, None, f"{self.setup_names[setup]}; stop {stop:g}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        return {"order": "close", "add_only": plan.setup in ADD_ONLY, "kell_leg": ctx.extras.get("kell_leg")}

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
        if sizing_result.too_large:
            label, reason = "WATCH_WAIT", "too large for account"
        else:
            label, reason = "TRADE_HIGH_CONFIDENCE", f"{self.setup_names[plan.setup]}; stop {risk_pct:.1f}% away"
        before = label
        if regime_downgrade_active:
            label = DOWNGRADE_MAP[label]
            reason += "; market-regime downgrade applied"
        return Decision(LABELS[before], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The stop each active setup used, and which cycle phase fired."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        active = [k for k, v in (sig.get("setups") or {}).items() if v]
        out: list[dict] = []
        for code, key in ((S1, "wp_stop"), (S2, "cb_stop"), (S3, "bb_stop"), (S4, "cb_stop")):
            if code in active and e.get(key):
                out.append({"shape": "level", "bars": 10, "to": d, "price": float(e[key]), "role": "stop",
                            "label": f"{self.setup_names[code]} stop {float(e[key]):g}"})
                break
        if e.get("bb_top") and S3 in active:
            out.append({"shape": "box", "bars": BASE_MIN_DAYS + 1, "to": d, "top": float(e["bb_top"]),
                        "bottom": float(e.get("bb_stop") or e["bb_top"]), "role": "base", "label": "the base"})
        if active:
            out.append({"shape": "note", "at": d, "text": f"Kell cycle {d}: " + ", ".join(
                self.setup_names.get(c, c) for c in active) + f" (leg {e.get('kell_leg')})"})
        return out or super().chart_anatomy(sig)
