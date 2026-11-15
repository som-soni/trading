"""NR7 / inside-day breakout -- Toby Crabel's narrow-range expansion (Day Trading with Short Term Price
Patterns and Opening Range Breakout, 1990).

Crabel's observation: a session whose range contracts to the narrowest of the last several tends to be
followed by a session of range expansion. He traded the break of the narrow day in either direction;
this is the long half:

  * the close is above the 200-day (the long half needs the long-term uptrend);
  * S1 NR7: today's range (high - low) is no wider than any of the NR_BARS - 1 sessions before it;
  * S2 ID/NR4: today is an inside day (high at or under yesterday's high, low at or over yesterday's low)
    whose range is no wider than any of the NR4_BARS - 1 sessions before it;
  * a buy-stop at today's high for the next session only; the stop is today's low.

Crabel holds the expansion for a day or two. Here: no target and a time limit of HOLD_BARS sessions
(`backtest_args`).
"""

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .swing_base import PASS_RULE, SwingSetupStrategy

NR_BARS = 7              # S1: today's range is the narrowest of this many sessions, today included
NR4_BARS = 4             # S2: an inside day whose range is the narrowest of this many sessions, today included
MIN_STOP_PCT = 0.5       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 8.0       # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)
HOLD_BARS = 3            # backtest_args: sold at the close of this session after the entry

S1 = "S1"
S2 = "S2"


class Nr7BreakoutStrategy(SwingSetupStrategy):
    key = "nr7_breakout"
    name = "NR7 / inside-day breakout"
    description = ("Crabel's narrow-range expansion: after the narrowest session of the last seven (or an inside "
                   "day that is the narrowest of four), buy the break of its high the next session.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: Crabel's NR7 and ID/NR4 as the long half, above the 200-day -- today's range the narrowest of "
         "{NR_BARS} sessions, or an inside day the narrowest of {NR4_BARS}; a next-session buy-stop at today's "
         "high, stop at today's low, sold at the close of session {HOLD_BARS}."),
    )
    behaviour = "trend_momentum"
    style = "squeeze"
    gate_codes = ("G1",)
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    setup_codes = (S1, S2)
    setup_names = {S1: "NR7", S2: "ID/NR4"}
    gate_titles = {"G1": "Above the 200-day"}
    order = ""
    expiry_bdays = 1
    plan_code = "NR"
    extra_columns = ("range_today", "range_min_prior7", "range_min_prior4", "inside_day", "level_entry",
                     "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "Volatility alternates: a session whose range contracts to the narrowest of the recent past tends to be "
        "followed by one whose range expands, and a break of the narrow day's high or low tends to run in that "
        "direction for a day or two. Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range "
        "Breakout* (1990), tabulated this for the NR7 and the inside day that is also an NR4. The catalogue "
        "grades it C (the book's own tables on futures, little independent replication on stocks), "
        "credibility 2."
    )
    how_it_works = (
        "**Universe and trend (G1).** Every liquid stock whose close is above its 200-day average. Crabel trades "
        "the break in both directions; this is the long half only, and a long-only break of a narrow day needs "
        "the long-term uptrend behind it, so the Above the 200-day screen's A1 is a hard gate.",
        "**S1 NR7.** Today's range (high − low) is no wider than any of the {NR_BARS} − 1 sessions before it: the "
        "narrowest of the last {NR_BARS}, today included (a tie counts).",
        "**S2 ID/NR4.** Today is an inside day -- its high at or under yesterday's high and its low at or over "
        "yesterday's low -- and its range is no wider than any of the {NR4_BARS} − 1 sessions before it.",
        "**The order.** Either setup places a buy-stop at today's high for the next session only. It fills when "
        "that session trades through the high, at the open if it gaps above.",
        "**Stop and exit.** The stop is today's low. No target: the position is sold at the stop or at the close "
        "of session {HOLD_BARS} after the entry.",
    )
    caveats = (
        "**Long half only.** Crabel sells the break of the narrow day's low as readily as he buys the break of "
        "its high; only the buy side is tested, inside the 200-day uptrend.",
        "**Daily bars, not the opening range.** Crabel's entries are often an opening-range breakout on the "
        "session after the narrow day; here the order is simply a buy-stop at the narrow day's high.",
        "**The exit is a stand-in.** Crabel exits within a day or two, often at the close of the entry day; the "
        "{HOLD_BARS}-session time limit with the narrow day's low as the stop is this backtest's version.",
        "**Tight stops meet costs.** A narrow day makes a small R; a stop closer than {MIN_STOP_PCT}% below the "
        "entry is not bought, but costs still weigh more on this setup than on most.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (squeeze group, grade C, "
              "credibility 2); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("The close is above the 200-day simple average (the Above the 200-day screen's A1).\n\n"
               "- **Fails:** a close at or below it, or no 200-day yet."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("NR7.\n\n- **Test:** today's high − low is at most the smallest high − low of the {NR_BARS} − 1 "
             "sessions before today.\n- **Signal:** a buy-stop at today's high for the next session; the stop is "
             "today's low."),
        S2: ("ID/NR4.\n\n- **Test:** today's high is at or under yesterday's high, today's low at or over "
             "yesterday's low, and today's high − low is at most the smallest of the {NR4_BARS} − 1 sessions "
             "before today.\n- **Signal:** as S1."),
    }
    entry_rules = (
        "Signal. G1 and S1 or S2 on today's close, with a stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below "
        "the entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop at today's high for the next session only (backtest: fills when that session's high "
        "reaches it, at the open if it gaps above).",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Today's (the narrow day's) low, rounded down to the tick. It defines 1R and "
                  "does not move.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--no-target --time-stop-bars {HOLD_BARS}`, the bracket exit "
        "mode):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("NR7 window", "NR_BARS", "S1: sessions, today included, whose narrowest range today must be."),
        ("NR4 window", "NR4_BARS", "S2: sessions, today included, whose narrowest range the inside day must be."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (--time-stop-bars)."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = f"--no-target --time-stop-bars {HOLD_BARS} --rank-by setup_momentum --min-fill 0.5"

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        d, e = ctx.daily, ctx.extras
        n = max(NR_BARS, NR4_BARS)
        if len(d) < n:
            return
        hi = d["high"].astype(float).to_numpy()[-n:]
        lo = d["low"].astype(float).to_numpy()[-n:]
        rng = hi - lo
        today = float(rng[-1])
        min7 = float(rng[-NR_BARS:-1].min())
        min4 = float(rng[-NR4_BARS:-1].min())
        inside = bool(hi[-1] <= hi[-2] and lo[-1] >= lo[-2])
        e.update(range_today=today, range_min_prior7=min7, range_min_prior4=min4, inside_day=int(inside),
                 level_entry=float(hi[-1]), level_stop=float(lo[-1]))
        result.setups[S1] = bool(today <= min7)
        result.setups[S2] = bool(inside and today <= min4)

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"{', '.join(self.setup_names[s] for s in result.active_setups)}: buy the break of today's high "
            f"{e['level_entry']:.2f}")
