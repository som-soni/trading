"""Gap fill -- the practitioner fade of an opening gap down ("gaps get filled").

A widespread trading-floor rule with no single author: a stock that opens well below the previous
session's whole range tends to trade back up into it. Daily bars cannot see the open of the gap day as
an order to fade, so this version waits for the session to finish:

  * today opens at least GAP_MIN_PCT % below yesterday's LOW (a true gap down, not just a lower open);
  * today closes in the upper part of its own range and still below yesterday's low (the gap held, but
    buyers took the session back from its low);
  * buy that close; the stop is today's low, the target is yesterday's low (the gap filled).

A flag (never blocking) marks a gap on news-sized volume. No news data is stored, so volume is the proxy.
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

GAP_MIN_PCT = 2.0           # G1: today's open is at least this % below yesterday's low
CLOSE_MIN_RANGE_POS = 0.5   # S1: (close - low) / (high - low) at least this
NEWS_VOL_MULT = 2.0         # W1: today's volume above this multiple of its 50-day average
MIN_STOP_PCT = 0.5          # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 10.0         # nor one further than this %
NOMINAL_TARGET_R = 1        # the target when yesterday's low is not above the entry (never, by S1)
HOLD_BARS = 5               # backtest_args: sold at the close of this session after the entry

S1 = "S1"
W1 = "W1"


class GapFillStrategy(SwingSetupStrategy):
    key = "gap_fill"
    name = "Gap fill"
    description = ("The practitioner fade of a gap down: a stock that opens below yesterday's whole range and "
                   "recovers into the upper half of its own is bought at the close, for a return into the gap.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the gap-fill fade on daily bars -- an open at least {GAP_MIN_PCT}% under yesterday's low, a close "
         "in the top part of the session's range (at least {CLOSE_MIN_RANGE_POS} of it) still under that low; "
         "bought at the close, stopped at the session's low, target yesterday's low, {HOLD_BARS}-session limit."),
    )
    behaviour = "mean_reversion"
    style = "fade"
    gate_codes = ("G1",)
    screen_key = "above_200"
    screen_gates: dict = {}
    watch_codes = (W1,)
    setup_codes = (S1,)
    setup_names = {S1: "Gap held, close recovered"}
    gate_titles = {"G1": "Gap down {GAP_MIN_PCT}%+ under yesterday's low"}
    order = "close"
    expiry_bdays = None
    plan_code = "GF"
    extra_columns = ("gap_pct", "close_pos", "vol_vs_avg", "level_entry", "level_stop", "level_target")
    extra_numeric_columns = extra_columns

    thesis = (
        "\"Gaps get filled\" is one of the most repeated rules on any trading floor: an opening gap is an "
        "overreaction made before the session has traded, and once the first sellers are done price drifts back "
        "into the range it jumped. It has no single author and no published test that supports it as a rule; the "
        "catalogue grades it D, credibility 1. It is here because it is so widely believed: a measured result "
        "either way is worth having, and it adds a short-hold fade to the catalogue."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. The practitioner rule has no trend filter, so none is added; the Above "
        "the 200-day screen supplies the universe only, with no gate taken from it.",
        "**The gap (G1).** Today opened at least {GAP_MIN_PCT}% below yesterday's low: a true gap down, below "
        "yesterday's whole range, not merely an open under yesterday's close.",
        "**The setup (S1).** Today closed in the upper part of its range -- (close − low) ÷ (high − low) at least "
        "{CLOSE_MIN_RANGE_POS} -- and still below yesterday's low, so the gap is still open and there is room to "
        "fill it.",
        "**News-sized volume (W1, flag only).** Today's volume is above {NEWS_VOL_MULT} × its 50-day average "
        "(the average includes today). No news data is stored, so volume stands in for \"a news gap\"; the flag "
        "never blocks a trade.",
        "**Entry, stop and target.** Bought at today's close. The stop is today's low; the target is yesterday's "
        "low, where the gap is filled. Sold at the close of session {HOLD_BARS} after the entry if neither is hit.",
    )
    caveats = (
        "**A later, different entry.** The practitioner fade buys the open of the gap day. Daily bars only know "
        "the gap at the open, and cannot say when the session's low came, so this buys that session's close once "
        "the gap has held and the close has recovered -- part of the move a floor trader would fade is already "
        "gone, and the stop (the day's low) is known.",
        "**No news data.** Practitioners fade \"no-news\" gaps and respect news gaps; this run cannot tell them "
        "apart. W1 marks the high-volume ones so a reader can compare.",
        "**Survivorship.** The universe is today's stock lists; companies whose gap down was the start of a "
        "collapse into delisting are missing, which flatters a buy-the-gap rule.",
        "**Run it with its exit flags** (`backtest_args`): the target is yesterday's low and the time limit "
        "{HOLD_BARS} sessions.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (fade group, grade D, credibility "
              "1); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("A true gap down.\n\n- **Test:** today's open is at least {GAP_MIN_PCT}% below yesterday's low.\n"
               "- **Fails:** the open is inside or above yesterday's range, or less than {GAP_MIN_PCT}% under it."),
    }
    watch_docs = {
        W1: ("A news-sized gap.\n\n- **Test:** today's volume is above {NEWS_VOL_MULT} × its 50-day average volume "
             "(the average includes today).\n- **Never blocks:** no news data is stored; the flag lets a reader "
             "compare high-volume gaps, likelier news, with the rest."),
    }
    setup_docs = {
        S1: ("The gap held and the close recovered.\n\n- **Test:** (close − low) ÷ (high − low) is at least "
             "{CLOSE_MIN_RANGE_POS}, and today's close is below yesterday's low.\n- **Signal:** buy today's "
             "close; stop at today's low; target yesterday's low."),
    }
    entry_rules = (
        "Signal. G1 and S1 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below the "
        "entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at the signal session's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Today's (the gap day's) low, rounded down to the tick. It defines 1R. It does "
                  "not move.",)
    target_rules = ("Yesterday's low: the price at which the gap is filled. Should it ever not be above the entry, "
                    "entry + {NOMINAL_TARGET_R} R is used instead (S1 makes that impossible).",)
    exit_rules = (
        "Each session after the entry (backtest, the default bracket with `--time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The target, yesterday's low, at its price or at the open if the stock gaps above it.",
        "3. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Gap", "GAP_MIN_PCT", "G1: % today's open must be below yesterday's low, at least."),
        ("Close in range", "CLOSE_MIN_RANGE_POS", "S1: (close − low) ÷ (high − low), at least."),
        ("News volume", "NEWS_VOL_MULT", "W1: today's volume above this × its 50-day average."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (--time-stop-bars)."),
        ("Nominal target", "NOMINAL_TARGET_R", "Fallback target = entry + this × R."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = f"--time-stop-bars {HOLD_BARS} --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        if len(d) < 2:
            result.fail("G1", "insufficient history")
            return
        last = d.iloc[-1]
        prev_low = float(d["low"].iloc[-2])
        o, hi, lo, close = (float(last["open"]), float(last["high"]), float(last["low"]), float(last["close"]))
        gap_pct = (1 - o / prev_low) * 100 if prev_low > 0 else float("nan")
        pos = (close - lo) / (hi - lo) if hi > lo else float("nan")
        avg = last.get("vol_sma50")
        vol_vs_avg = float(last["volume"]) / float(avg) if avg and avg == avg else float("nan")
        e.update(gap_pct=gap_pct, close_pos=pos, vol_vs_avg=vol_vs_avg,
                 level_entry=close, level_stop=lo, level_target=prev_low)
        if gap_pct >= GAP_MIN_PCT:
            result.ok("G1", f"opened {gap_pct:.1f}% under yesterday's low {prev_low:.2f}")
        else:
            result.fail("G1", f"no {GAP_MIN_PCT}% gap under yesterday's low")
        news = bool(vol_vs_avg > NEWS_VOL_MULT)     # NaN compares False
        result.watch_flags[W1] = news
        if news:
            result.watch_notes[W1] = f"volume {vol_vs_avg:.1f}× its 50-day average"
        result.setups[S1] = bool(pos >= CLOSE_MIN_RANGE_POS and close < prev_low)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], e["level_target"], (
            f"gap of {e['gap_pct']:.1f}% held; target the fill at {e['level_target']:.2f}")
