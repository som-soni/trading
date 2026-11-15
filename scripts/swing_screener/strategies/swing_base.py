"""Shared plumbing for the swing-catalogue setups (research/strategy-catalog-swing.md).

The catalogue lists some twenty public swing setups that had never been tested here. Each is a small
rule -- a bar pattern, a level, an order -- on top of the same machinery: the liquidity floor, a plan
with an entry, a stop and a nominal target, the one-tier decision, the backtest's order types. Writing
that machinery twenty times would make twenty places for it to drift, so it lives here once and each
setup's module (strategies/<key>.py) holds only what makes it that setup: its detector (`detect`), its
levels (`levels`), its constants and its documentation.

Not a registered strategy and not a contract change: every subclass is an ordinary `Strategy`
(strategies/base.py), registered in strategies/__init__.py, fingerprinted on its OWN module's
constants. The three every subclass module must define, because `classify` and `build_plans` read them
from the subclass's module (so a `--const` override, which patches that module, reaches them):

    MIN_STOP_PCT       a stop closer than this % below the entry is not bought (WATCH - WAIT)
    MAX_STOP_PCT       a stop further than this % below the entry is not bought (WATCH - WAIT)
    NOMINAL_TARGET_R   the plan's target when the setup names none, in R (the R column only, when the
                       backtest runs with --no-target)

How an order is placed is a class attribute, `order`: "close" buys the signal session's close, "open"
the next session's open, "" a resting buy-stop at the plan's entry for `expiry_bdays` sessions (the
simulator's default window when None).
"""

import sys

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan, tradable_point_in_time
from .trend_pullback import round_tick

# A catalogue setup's status before its first run: the pass rule is written now, before any result.
PASS_RULE = ("Pass criterion, fixed before any run and judged per market: in the optimise stage (2013-2021) the "
             "rules beat the market's benchmark CAGR (positive excess) AND make a positive average R after costs. "
             "A market that passes may go to one verify run; one that fails does not.")
# The same rule for a ranking or timing book, which has no per-trade R: excess CAGR, and a max drawdown no
# deeper than the benchmark's by more than 5 points.
PASS_RULE_PORTFOLIO = ("Pass criterion, fixed before any run and judged per market: in the optimise stage (2013-2021) "
                       "positive excess CAGR over the benchmark AND a max drawdown no more than 5 points deeper than "
                       "the benchmark's. A market that passes may go to one verify run; one that fails does not.")


class SwingSetupStrategy(Strategy):
    """A catalogue setup: subclasses implement `detect` and `levels` and document themselves."""

    selection = "time_series"
    horizon = "swing"
    nominal_target = True
    min_bars = 210
    order: str = ""                 # "close" | "open" | "" (resting buy-stop at the plan's entry)
    expiry_bdays: int | None = None
    plan_code: str = "SW"
    needs_ctx_extras = True

    # ---- the shared rule texts; {MIN_STOP_PCT} etc. resolve against the subclass's own module
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped at Max position "
        "size × equity.",
        "Cash. A fill the cash allows less than half its planned shares is skipped (`--min-fill 0.5`).",
        "Slots. At most Position cap positions at once; same-day signals are ranked by 12-1 momentum "
        "(`--rank-by setup_momentum`).",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "No price floor on split-adjusted history and no results rule.",
        "No market filter: the published setup has none, so none is added.",
    )
    regime_note = ("No downgrade. The published setup has no market filter, so the shared risk-off downgrade is "
                   "not applied either: the backtest measures the setup as published.")
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, a setup fired, the stop is between {MIN_STOP_PCT}% and "
                                 "{MAX_STOP_PCT}% below the entry, and one share fits the account. The only tier "
                                 "the backtest buys.",
        "TRADE_ON_TRIGGER": "Not used.",
        "WATCH_WAIT": "A setup fired but the stop is closer than {MIN_STOP_PCT}% or further than {MAX_STOP_PCT}%, "
                      "or not even one share fits the account.",
        "AVOID": "A gate failed, no setup fired, or the plan's risk is not a positive number.",
    }

    # ---------- the subclass's module constants ----------

    def _k(self, name: str):
        return getattr(sys.modules[type(self).__module__], name)

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- detection ----------

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        """Record this setup's own gates (result.ok / result.fail), watch flags and setups."""
        raise NotImplementedError

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        self.detect(ctx, result)
        for code in self.setup_codes:
            result.setups.setdefault(code, False)
        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.has_setup else 0.0

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return result.has_setup

    # ---------- the plan ----------

    def levels(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> tuple:
        """(entry, stop, target or None, reason). The stop is rounded down to the tick here."""
        raise NotImplementedError

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        entry, stop, target, why = self.levels(ctx, result, cfg)
        entry = float(entry)
        stop = round_tick(float(stop), cfg.tick_size, "down")
        risk = entry - stop
        if target is None or not (target == target) or target <= entry:
            target = entry + self._k("NOMINAL_TARGET_R") * risk
        plan = TradePlan(
            plan=self.plan_code, setup=result.active_setups[0], entry=entry, stop=stop, target=float(target),
            risk_per_share=risk, reward_per_share=float(target) - entry,
            r_multiple=(float(target) - entry) / risk if risk > 0 else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, why)

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        meta: dict = {}
        if self.order:
            meta["order"] = self.order
        if self.expiry_bdays:
            meta["expiry_bdays"] = int(self.expiry_bdays)
        return meta

    # ---------- decision ----------

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        return False

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID", f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        lo, hi = self._k("MIN_STOP_PCT"), self._k("MAX_STOP_PCT")
        if sizing_result.too_large:
            label, reason = "WATCH_WAIT", "too large for account"
        elif risk_pct < lo:
            label, reason = "WATCH_WAIT", f"stop only {risk_pct:.1f}% away (< {lo}%)"
        elif risk_pct > hi:
            label, reason = "WATCH_WAIT", f"stop {risk_pct:.1f}% away (> {hi}%)"
        else:
            label = "TRADE_HIGH_CONFIDENCE"
            reason = f"{', '.join(result.active_setups)}; stop {risk_pct:.1f}% away"
        return Decision(LABELS[label], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    # ---------- report and chart ----------

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras

        def r(v):
            try:
                return round(float(v), 4) if v is not None and v == v else None
            except (TypeError, ValueError):
                return None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """A note naming the setup and the measured values evaluate() stored, plus the default levels."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        active = [k for k, v in (sig.get("setups") or {}).items() if v]
        if not active:
            return super().chart_anatomy(sig)
        names = [self.setup_names.get(a, a) for a in active]
        vals = [f"{k} {float(e[k]):.4g}" for k in self.extra_columns
                if isinstance(e.get(k), (int, float)) and e.get(k) == e.get(k)][:4]
        out = [{"shape": "note", "at": d,
                "text": f"{self.name} {d}: {', '.join(names)}" + (" · " + ", ".join(vals) if vals else "")}]
        for key, label, role in (("level_entry", "entry level", "pivot"), ("level_stop", "stop level", "stop"),
                                 ("level_target", "target level", "target")):
            v = e.get(key)
            if isinstance(v, (int, float)) and v == v:
                out.append({"shape": "level", "bars": 20, "to": d, "price": float(v), "label": label, "role": role})
        return out
