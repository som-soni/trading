"""Minervini coil breakout — the Minervini SEPA strategy with the contraction gauge as its setup.

An experiment, asked as one question: does the VCP need its swing structure, or is "tight, quiet and near the
high, then a breakout on volume" enough? Everything around the setup is Minervini's, reused rather than
restated: the Trend Template screen and its gates (`stage2`), the prefilter (`MinerviniSpecStrategy`'s turnover
floor and young-listing rule), the stop (`pivot_stop`, SL-01), the stop limit (SL-03), the buy range, one entry
per base, and in the backtest `--spec` -- Minervini's exits, ranking, position count, open-risk cap and costs.

Only the setup is different. Instead of the VCP detector (core/vcp_spec.py: a base, its successively smaller
pullbacks, a final tight area), S1 is the gauge's breakout (core/contraction.py, the chart's "VCP contraction
gauge"): the previous session coiled -- its last WINDOW sessions within TIGHT_PCT high to low, on at most
DRYUP_RATIO of the 50-day volume, their high within (1 - PIVOT_NEAR_HIGH) of the BASE_MAX_DAYS-session high --
and today's close cleared that window's high on at least VOL_MULT x the 50-day volume. The chart and the
backtest call the same function.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import contraction as con
from ..core.contraction import WINDOW  # noqa: F401 (fingerprint and doc placeholder: the gauge's window)
from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import DOWNGRADE_MAP, LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan
from .minervini_spec import (  # noqa: F401 (the rules reused, by name: fingerprinted and quoted in the docs)
    BASE_MAX_DAYS, BUY_RANGE_PCT, DRYUP_RATIO, MAX_ENTRIES_PER_BASE, MAX_PCT_BELOW_52W_HIGH, MAX_STOP_PCT,
    MIN_PCT_ABOVE_52W_LOW, PIVOT_NEAR_HIGH, RS_MIN_RANK, RS_MIN_SCORE, SMA200_RISING_BARS, STOP_BUFFER_PCT,
    TIGHT_MIN_DAYS, TIGHT_PCT, VOL_MULT, YOUNG_LISTING, YOUNG_MIN_BARS,
    MinerviniSpecStrategy, pivot_stop,
)

NOMINAL_TARGET_R = 3   # a far target for the plan's R column only; under --spec the backtest has no target

S1 = "S1"   # a breakout from a coil today

_MV = MinerviniSpecStrategy()   # its prefilter, reused as is


class MinerviniCoilStrategy(Strategy):
    selection = "time_series"
    version = "1.1"
    # 1.1 moves only rules applied after the scan (the stop cap at the fill, an exit, the market filter).
    signal_version = "1.0"
    changelog = (
        ("1.1", "2026-11-11",
         "Follows minervini 1.64's shared rules, which this strategy imports: MAX_STOP_PCT 8 (was 10), the trend "
         "exit moving to the 150-day once a trade reaches +3R (EX-06), and the market filter's segment test (the "
         "small- and mid-cap index up over 63 sessions). Measured on minervini's trades, not on this strategy's. "
         "All after the scan, so signal_version stays 1.0."),
        ("1.0", "2026-11-07",
         "v1: the Minervini SEPA strategy's screen, gates, stop, exits and portfolio rules, with the contraction "
         "gauge's breakout (core/contraction.py) as the only setup in place of the VCP detector."),
    )
    key = "minervini_coil"
    name = "Minervini coil breakout"
    variant_of = "minervini"
    description = ("Minervini's Trend Template and exits, entered on a breakout from a coil -- a tight, quiet "
                   "stretch near the high -- measured by the contraction gauge instead of the VCP's swings.")
    style = "breakout"
    horizon = "swing"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")
    screen_key = "stage2"
    screen_gates = {"G1": "C1", "G2": "C2", "G3": "C3", "G4": "C4", "G5": "C5", "G6": "C6", "G7": "C7", "G8": "C8"}
    watch_codes = ()
    setup_codes = (S1,)
    setup_names = {S1: "Coil breakout"}
    nominal_target = True
    min_bars = 300

    needs_ctx_extras = True
    extra_columns = ("coil_high", "coil_low", "coil_tight", "coil_dry", "coil_near", "breakout_volume_ratio",
                     "rs_score", "coil_from")
    extra_numeric_columns = ("coil_high", "coil_low", "coil_tight", "coil_dry", "coil_near",
                             "breakout_volume_ratio", "rs_score")
    signal_exempt_consts = ("MAX_STOP_PCT", "STOP_BUFFER_PCT", "BUY_RANGE_PCT", "MAX_ENTRIES_PER_BASE",
                            "NOMINAL_TARGET_R")

    thesis = (
        "Minervini's VCP says supply dries up as a leader's pullbacks shrink, until a small push clears the "
        "pivot. The part that can be measured on any bar -- a tight range, light volume, a price near the high "
        "-- may carry most of that, without the swing structure. If it does, the setup is simpler and fires more "
        "often; if not, the shrinking pullbacks are where the edge is."
    )
    how_it_works = (
        "**The idea.** The Minervini SEPA strategy with one part swapped: the setup is the contraction gauge's "
        "breakout instead of a detected VCP. Everything else is Minervini's.",
        "**Qualify.** Minervini's prefilter and the Trend Template, G1-G8 (the Stage 2 screen), all hard.",
        "**Coiled.** On the session before the breakout, its last {WINDOW} sessions ranged no more than "
        "{TIGHT_PCT}% from high to low, averaged no more than {DRYUP_RATIO}x the 50-day volume taken before "
        "them, and their high was at least {PIVOT_NEAR_HIGH} x the highest high of the last {BASE_MAX_DAYS} "
        "sessions.",
        "**Signal.** S1: today's close is above that window's high on at least {VOL_MULT}x the 50-day volume.",
        "**Buy.** At the next session's open, if it opens between the coil's low and {BUY_RANGE_PCT}% above its "
        "high. The stop is {STOP_BUFFER_PCT}% under the coil's low, and the trade is skipped if that is more "
        "than {MAX_STOP_PCT}% under the price paid.",
        "**Sell.** Minervini's exits, unchanged (`--spec`): see the Minervini SEPA strategy's Exit rules.",
    )
    caveats = (
        "**Not yet measured.** See Status.",
        "**It cannot see a VCP.** The gauge reads one window; it has no idea whether the pullbacks before it "
        "shrank, how deep the base was or where its pivot sits. That is the point of the experiment, and the "
        "reason it may buy plain consolidations Minervini would not.",
        "**A window, not a base.** The coil is always the last {WINDOW} sessions, so its high and low are that "
        "window's, not a base's swing points. A tight area longer than the window is judged on its last "
        "{WINDOW} sessions only.",
        "**Shared rules move together.** The thresholds are Minervini's own constants, imported: tuning "
        "TIGHT_PCT for Minervini moves this strategy too (its fingerprint follows, so the version gate notices).",
        "**Run it with its flags.** `--spec --market-filter --pe` (the page's backtest command adds them); "
        "without --spec the default bracket exit would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "Not yet measured. Pass criterion, set before any result: in the optimise stage (2013-2021), beat the "
        "market's benchmark CAGR with a max drawdown no worse than the benchmark's plus 10 points and a positive "
        "average R in at least one market; and, to be worth keeping beside Minervini SEPA, a higher CAGR or a "
        "higher average R than its optimise run in that market."
    )
    gate_docs = {k: v for k, v in MinerviniSpecStrategy.gate_docs.items() if k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8")}
    watch_docs = {}
    setup_docs = {
        S1: (
            "A close out of a coil, on volume.\n\n"
            "- **Coiled (previous session):** its last {WINDOW} sessions' range is at most {TIGHT_PCT}% of their "
            "high; their average volume is at most {DRYUP_RATIO}x the 50-day average on the session before "
            "them; their high is at least {PIVOT_NEAR_HIGH} x the highest high of the last {BASE_MAX_DAYS} "
            "sessions.\n"
            "- **Breakout (today):** the close is above that window's high and the volume is at least "
            "{VOL_MULT}x the 50-day average (today included).\n"
            "- **One definition:** `core/contraction.py`, which the chart's contraction gauge draws."
        ),
    }
    entry_rules = (
        "Signal. S1 with G1-G8 passing, graded TRADE - HIGH CONFIDENCE.",
        "Order. Buy at the next session's open, that session only; not if it opens under the coil's low or more "
        "than {BUY_RANGE_PCT}% above its high.",
        "One entry per coil. A coil (its window's first date) is bought at most {MAX_ENTRIES_PER_BASE} times.",
        "Stop test at the fill (backtest). A stop more than {MAX_STOP_PCT}% under the price paid skips the order.",
    )
    stop_rules = (
        "Where it goes. {STOP_BUFFER_PCT}% under the coil's low, rounded down to the tick (Minervini's SL-01, "
        "the same function).",
        "It defines 1R. The distance from the price paid to the stop is the trade's risk.",
        "How it moves. As Minervini's exits move it (`--spec`).",
    )
    target_rules = (
        "No sell order at a target under `--spec`. The plan's target is entry + {NOMINAL_TARGET_R}R, for the R "
        "column only.",
    )
    exit_rules = (
        "Minervini's exits, unchanged: `--spec` runs `--exit-mode minervini` (EX-01..EX-07 of "
        "research/minervini-backtest-spec.md). The Minervini SEPA strategy's page describes each.",
        "A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Minervini's, under `--spec`: risk-based shares, its position count, open-risk cap and traded-value "
        "cap, and progressive exposure with `--pe`.",
    )
    filter_rules = (
        "Minervini's prefilter: its turnover floor and young-listing rule, then the Trend Template.",
        "Too little history. At least {min_bars} daily bars.",
        "Market regime and results blackout. As Minervini's under `--spec --market-filter`.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "G1-G8 pass, S1 fired today, and one share fits the account. The tier the "
                                 "backtest buys.",
        "TRADE_ON_TRIGGER": "Only a HIGH CONFIDENCE lowered by a risk-off market.",
        "WATCH_WAIT": "Not even one share fits the account, or a TRADE ON TRIGGER lowered by a risk-off market.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number. No breakout today means no plan.",
    }
    param_docs = (
        ("Window", "WINDOW", "Sessions in each reading (the gauge's, core/contraction.py)."),
        ("Tight range", "TIGHT_PCT", "Minervini's: the coil's range, high to low, at most this % of its high."),
        ("Volume dry-up", "DRYUP_RATIO", "Minervini's: the coil's average volume against the 50-day, at most."),
        ("Near the high", "PIVOT_NEAR_HIGH", "Minervini's: the coil's high against the base-length high, at least."),
        ("Base length", "BASE_MAX_DAYS", "Minervini's: the sessions the high is measured over."),
        ("Breakout volume", "VOL_MULT", "Minervini's: the breakout day's volume against the 50-day, at least."),
        ("Stop buffer", "STOP_BUFFER_PCT", "Minervini's SL-01: the stop sits this % under the coil's low."),
        ("Maximum stop", "MAX_STOP_PCT", "Minervini's SL-03: a fill whose stop is further below is skipped."),
        ("Buy range", "BUY_RANGE_PCT", "Minervini's: no fill more than this % above the coil's high."),
        ("Entries per base", "MAX_ENTRIES_PER_BASE", "Minervini's EN-04, per coil here."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × risk, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
    )
    backtest_args = "--spec --market-filter --pe"

    # ---------- screen: Minervini's ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        return _MV.prefilter_row(cfg, last)

    def passes_prefilter(self, cfg: MarketConfig, enriched_daily) -> tuple[bool, str]:
        return _MV.passes_prefilter(cfg, enriched_daily)

    def prefilter_mask(self, cfg: MarketConfig, enriched_daily) -> "pd.Series":
        return _MV.prefilter_mask(cfg, enriched_daily)

    # ---------- gates and setup ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        d = ctx.daily
        h, l, c, v = (d[k].to_numpy(float) for k in ("high", "low", "close", "volume"))
        i, r = len(d) - 1, con.rules()
        bo = con.breakout(h, l, c, v, i, WINDOW, r)
        now = con.reading(h, l, v, i, WINDOW, r)
        e = ctx.extras
        e["rs_score"] = float(d["rs_score"].iloc[-1]) if "rs_score" in d and d["rs_score"].iloc[-1] == d["rs_score"].iloc[-1] else None
        src = bo or now
        if src:
            e.update(coil_high=src["hi"], coil_low=src["lo"], coil_tight=src["tight"], coil_dry=src["dry"], coil_near=src["near"])
            # the coil's first session, which identifies it for "one entry per coil" (the breakout's coil ended yesterday)
            e["coil_from"] = str(d.index[max(0, i - (1 if bo else 0) - WINDOW + 1)].date())
        e["breakout_volume_ratio"] = bo["vol_ratio"] if bo else None
        result.setups[S1] = bo is not None
        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.setups.get(S1) else 0.0

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return bool(result.setups.get(S1))

    # ---------- entry ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no breakout from a coil today")
        e = ctx.extras
        hi, lo = e.get("coil_high"), e.get("coil_low")
        if not hi or not lo:
            return PlanChoice(None, None, "no coil readings")
        entry = float(ctx.close)
        stop = pivot_stop(float(lo), cfg.tick_size)
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(plan="COIL", setup=S1, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry,
                         r_multiple=NOMINAL_TARGET_R if risk > 0 else float("nan"), nearest_overhead_above_entry=None)
        return PlanChoice(plan, None, f"closed above the coil's high {hi:.2f} on {e.get('breakout_volume_ratio') or 0:.1f}x volume")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        e = ctx.extras
        hi, lo = float(e["coil_high"]), float(e["coil_low"])
        return {"order": "open", "min_open": lo, "pivot": hi, "tight_low": lo, "max_fill": hi * (1 + BUY_RANGE_PCT / 100),
                "max_risk_pct": MAX_STOP_PCT / 100, "base_id": e.get("coil_from"),
                "max_entries_per_base": MAX_ENTRIES_PER_BASE, "tightness": e.get("coil_tight")}

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
            label, reasons = "WATCH_WAIT", ["too large for account"]
        else:
            label, reasons = "TRADE_HIGH_CONFIDENCE", ["breakout from a coil"]
        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons), risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda x: round(float(x), 3) if x is not None and x == x else None
        return {"coil_high": r(e.get("coil_high")), "coil_low": r(e.get("coil_low")), "coil_tight": r(e.get("coil_tight")),
                "coil_dry": r(e.get("coil_dry")), "coil_near": r(e.get("coil_near")),
                "breakout_volume_ratio": r(e.get("breakout_volume_ratio")), "rs_score": r(e.get("rs_score")),
                "coil_from": e.get("coil_from")}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The coil the trade broke out of: its window as a box, its high (the breakout level) and its low (the stop's)."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        if not e.get("coil_high") or not e.get("coil_low") or not e.get("coil_from"):
            return super().chart_anatomy(sig)
        hi, lo = float(e["coil_high"]), float(e["coil_low"])
        return [
            {"shape": "box", "from": e["coil_from"], "to": d, "top": hi, "bottom": lo, "role": "base",
             "label": f"coil · {e.get('coil_tight') or 0:.1f}% range · {e.get('coil_dry') or 0:.2f}x volume"},
            {"shape": "level", "bars": 5, "to": d, "price": hi, "role": "pivot", "label": f"coil high {hi:g} — the close cleared it"},
            {"shape": "level", "bars": 5, "to": d, "price": lo, "role": "stop", "label": f"coil low {lo:g} — the stop sits under it"},
        ]
