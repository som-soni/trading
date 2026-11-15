"""Holy Grail -- Raschke & Connors's first pullback to the 20-day EMA in a strong trend (Street Smarts, 1995).

A strong trend (ADX above 30) that pulls back to its 20-period exponential average for the first time tends to
resume. On daily bars:

  * the 20-day EMA is rising (above its value EMA_RISE_BARS sessions ago) -- ADX alone has no direction;
  * ADX(14) is above ADX_MIN;
  * today's low touches the 20-day EMA, and none of the TOUCH_LOOKBACK sessions before today did;
  * a buy-stop at today's high for expiry_bdays sessions; the stop is today's low; the target the highest
    high of the last TARGET_BARS sessions (the recent swing high).
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

EMA_RISE_BARS = 5        # G1: the 20-day EMA is above its value this many sessions ago
ADX_MIN = 30             # G2: ADX(14) above this
TOUCH_LOOKBACK = 10      # S1: no low touched the 20-day EMA in this many sessions before today
TARGET_BARS = 20         # target: the highest high of this many sessions, today included
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 10.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the target when the swing high is not above the entry

S1 = "S1"


class HolyGrailStrategy(SwingSetupStrategy):
    key = "holy_grail"
    name = "Holy Grail"
    description = ("Raschke & Connors's first pullback in a strong trend: ADX above 30, a rising 20-day EMA, and "
                   "the first touch of that EMA in two weeks, bought through the touch day's high.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the Holy Grail as Street Smarts states it on daily bars -- ADX(14) above {ADX_MIN}, the 20-day EMA "
         "rising over {EMA_RISE_BARS} sessions, the first low touching it in {TOUCH_LOOKBACK} sessions; a buy-stop "
         "at the touch day's high, stop at its low, target the {TARGET_BARS}-session high."),
    )
    behaviour = "trend_momentum"
    style = "pullback"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "First pullback to the 20-day EMA"}
    gate_titles = {"G1": "20-day EMA rising", "G2": "ADX above {ADX_MIN}"}
    order = ""
    expiry_bdays = 2
    plan_code = "HG"
    extra_columns = ("ema20", "ema20_rise_pct", "adx14", "level_entry", "level_stop", "level_target")
    extra_numeric_columns = extra_columns

    thesis = (
        "A strong trend that pulls back for the first time usually meets buyers who missed the first leg; the "
        "20-day exponential average is where such a pullback typically finds them. ADX measures the trend's "
        "strength, so a reading above {ADX_MIN} picks trends worth buying into, and the first touch is the one "
        "least likely to mark a trend that is already tiring. Raschke & Connors, *Street Smarts* (1995). The "
        "catalogue grades it D (no published test beyond the book's examples), credibility 2."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. The book has no 200-day rule, so none is added; the Above the 200-day "
        "screen supplies the universe only, with no gate taken from it.",
        "**The trend (G1, G2).** The 20-day EMA is above its value {EMA_RISE_BARS} sessions ago (G1: the trend is "
        "up -- ADX alone has no direction), and ADX(14) is above {ADX_MIN} (G2: the trend is strong).",
        "**The first pullback (S1).** Today's low is at or below the 20-day EMA, and none of the {TOUCH_LOOKBACK} "
        "sessions before today had a low at or below its own EMA value.",
        "**The order.** A buy-stop at today's high for {expiry_bdays} sessions. It fills only if the trend "
        "resumes; a gap above fills at the open.",
        "**Stop and target.** The stop is today's low. The target is the highest high of the last {TARGET_BARS} "
        "sessions, today included (the recent swing high); when that is not above the entry, entry + "
        "{NOMINAL_TARGET_R} R. The backtest sells at whichever is hit first.",
    )
    caveats = (
        "**The book's ADX is also rising.** Raschke wants ADX above 30 *and* rising; the rising EMA is used for "
        "direction here instead, as the spec decided, and ADX's own slope is not tested.",
        "**Touch, not close.** The book buys when price trades back above the prior bar's high after touching the "
        "EMA; the touch day's high is used as that bar, so the order goes in the session after the touch.",
        "**Target is a stand-in.** The book takes profit at the recent swing high and trails the rest; the "
        "{TARGET_BARS}-session high is a mechanical swing high, and there is no trail.",
        "**Survivorship.** The universe is today's stock lists; strong trends that ended in a delisting are missing.",
        "**Run it with its flags** (`backtest_args`).",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (pullback group, grade D, "
              "credibility 2); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The 20-day EMA is rising.\n\n- **Test:** today's 20-day EMA is above its value {EMA_RISE_BARS} "
               "sessions ago.\n- **Fails:** it is flat or falling, or too little history."),
        "G2": ("The trend is strong.\n\n- **Test:** ADX(14) is above {ADX_MIN}.\n- **Fails:** it is at or below, "
               "or undefined."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("The first pullback to the 20-day EMA.\n\n- **Test:** today's low is at or below today's 20-day EMA, "
             "and no low in the {TOUCH_LOOKBACK} sessions before today was at or below that session's EMA.\n"
             "- **Signal:** a buy-stop at today's high for {expiry_bdays} sessions; the stop is today's low."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at today's high for {expiry_bdays} sessions (backtest: fills when a session's high "
        "reaches it, at the open if it gaps above; cancelled if the stop is hit first).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Today's (the touch day's) low, rounded down to the tick. It defines 1R; it does "
                  "not move.",)
    target_rules = ("The highest high of the last {TARGET_BARS} sessions, today included; entry + "
                    "{NOMINAL_TARGET_R} R when that is not above the entry.",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket: `--rank-by setup_momentum --min-fill 0.5`, "
        "no exit flags):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, at its price or at the open if the stock gaps over it.",
    )
    param_docs = (
        ("EMA rise", "EMA_RISE_BARS", "G1: sessions back the 20-day EMA must be above."),
        ("ADX floor", "ADX_MIN", "G2: ADX(14) must be above this."),
        ("First-touch window", "TOUCH_LOOKBACK", "S1: sessions before today with no touch of the 20-day EMA."),
        ("Swing-high window", "TARGET_BARS", "Target: the highest high of this many sessions, today included."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R when the swing high is not above the entry."),
        ("Order expiry", "expiry_bdays", "Sessions the buy-stop rests."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = "--rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        n = max(EMA_RISE_BARS, TOUCH_LOOKBACK, TARGET_BARS) + 1
        if len(d) < n:
            result.fail("G1", "insufficient history")
            return
        ema = d["ema20"].to_numpy(float)[-n:]
        lows = d["low"].to_numpy(float)[-n:]
        highs = d["high"].to_numpy(float)[-n:]
        adx = float(d["adx14"].iloc[-1])
        today_low, today_high = float(lows[-1]), float(highs[-1])
        target = float(highs[-TARGET_BARS:].max())
        rise = (ema[-1] / ema[-1 - EMA_RISE_BARS] - 1) * 100
        e.update(ema20=float(ema[-1]), ema20_rise_pct=rise, adx14=adx, level_entry=today_high,
                 level_stop=today_low, level_target=target)
        if ema[-1] > ema[-1 - EMA_RISE_BARS]:
            result.ok("G1", f"20-day EMA up {rise:.2f}% over {EMA_RISE_BARS} sessions")
        else:
            result.fail("G1", "20-day EMA not rising")
        if adx == adx and adx > ADX_MIN:
            result.ok("G2", f"ADX {adx:.1f}")
        else:
            result.fail("G2", f"ADX {adx:.1f} (<= {ADX_MIN})")
        prior_touch = bool((lows[-1 - TOUCH_LOOKBACK:-1] <= ema[-1 - TOUCH_LOOKBACK:-1]).any())
        result.setups[S1] = bool(today_low <= ema[-1] and not prior_touch)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], e["level_target"], (
            f"first touch of the 20-day EMA {e['ema20']:.2f} with ADX {e['adx14']:.1f}; buy through today's high")
