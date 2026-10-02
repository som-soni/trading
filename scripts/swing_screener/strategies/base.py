"""The Strategy contract.

A strategy owns every *opinion* in the system: which pre-filter a symbol
must pass, which conditions disqualify it, which conditions merely cap
confidence, what a tradeable pattern looks like, where entry/stop/target
go, and how all of that collapses into one decision label.

Everything a strategy does NOT own — OHLCV loading, indicators, swing
structure, position sizing, market/sector regime, reporting, history,
backtest mechanics — lives outside and is shared. That split is the point:
adding a breakout or mean-reversion strategy should mean writing one new
file in this package, not touching the pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..config.base import MarketConfig
from ..context import StockContext

# Decision tiers, least to most permissive. Used to resolve "if several
# caps apply, use the lowest".
CAP_ORDER = ["AVOID", "WATCH_WAIT", "TRADE_ON_TRIGGER", "TRADE_HIGH_CONFIDENCE"]

LABELS = {
    "TRADE_HIGH_CONFIDENCE": "TRADE - HIGH CONFIDENCE",
    "TRADE_ON_TRIGGER": "TRADE ON TRIGGER",
    "WATCH_WAIT": "WATCH - WAIT",
    "AVOID": "AVOID",
}

DOWNGRADE_MAP = {
    "TRADE_HIGH_CONFIDENCE": "TRADE_ON_TRIGGER",
    "TRADE_ON_TRIGGER": "WATCH_WAIT",
    "WATCH_WAIT": "AVOID",
    "AVOID": "AVOID",
}


@dataclass
class StrategyResult:
    """Outcome of evaluating one symbol against one strategy.

    `setups` is an open dict rather than named booleans so a strategy can
    declare whatever pattern vocabulary it wants (TC-01/TC-02 for trend
    pullback, BO-01 for breakout, MR-01 for mean reversion...) without
    this class changing.
    """

    hard_gates: dict[str, bool] = field(default_factory=dict)
    hard_notes: dict[str, str] = field(default_factory=dict)
    first_hard_fail: str | None = None
    watch_flags: dict[str, bool] = field(default_factory=dict)
    watch_notes: dict[str, str] = field(default_factory=dict)
    setups: dict[str, bool] = field(default_factory=dict)
    # which keys in `setups` make a symbol entry-eligible (vs informational tags)
    entry_setup_codes: tuple[str, ...] = ()

    @property
    def hard_gates_passed(self) -> bool:
        return self.first_hard_fail is None

    @property
    def has_setup(self) -> bool:
        return any(self.setups.get(code) for code in self.entry_setup_codes)

    @property
    def active_setups(self) -> list[str]:
        return [c for c in self.entry_setup_codes if self.setups.get(c)]

    @property
    def active_watch_flags(self) -> list[str]:
        return [code for code, on in self.watch_flags.items() if on]

    def fail(self, code: str, note: str = "") -> None:
        self.hard_gates[code] = False
        if note:
            self.hard_notes[code] = note
        if self.first_hard_fail is None:
            self.first_hard_fail = code

    def ok(self, code: str, note: str = "") -> None:
        self.hard_gates[code] = True
        if note:
            self.hard_notes[code] = note

    def recompute_first_fail(self) -> None:
        """Gates evaluated out of order (e.g. one that depends on setups)
        can leave `first_hard_fail` stale — call this after the last one."""
        self.first_hard_fail = next(
            (code for code, passed in self.hard_gates.items() if not passed), None
        )


@dataclass
class TradePlan:
    plan: str  # strategy-defined variant label, e.g. "A" (pullback) / "B" (breakout)
    setup: str
    entry: float
    stop: float
    target: float
    risk_per_share: float
    reward_per_share: float
    r_multiple: float
    nearest_overhead_above_entry: float | None

    @property
    def is_valid(self) -> bool:
        """Guards the NaN/degenerate case: a plan whose risk isn't a
        positive real number must never reach sizing or a decision, because
        every downstream comparison against NaN silently evaluates False
        and the plan sails through checks it should fail."""
        r = self.risk_per_share
        return r == r and r > 0 and self.entry == self.entry and self.stop == self.stop


@dataclass
class PlanChoice:
    chosen: TradePlan | None
    alternate: TradePlan | None
    reason: str


@dataclass
class Decision:
    label_before: str
    label_after: str
    reason: str
    risk_pct: float
    r_multiple: float
    setup_quality: float


class Strategy(ABC):
    """Implement this to add a strategy. See trend_pullback.py for the
    reference implementation and breakout.py for a second, deliberately
    different one (different gates, different setup vocabulary, different
    entry geometry) that exercises the seam."""

    key: str = ""
    name: str = ""
    description: str = ""
    # column codes the report should emit, in order
    gate_codes: tuple[str, ...] = ()
    watch_codes: tuple[str, ...] = ()
    setup_codes: tuple[str, ...] = ()
    # minimum daily bars before this strategy will evaluate a symbol
    min_bars: int = 260

    @abstractmethod
    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The screen, evaluated against ONE enriched daily row.

        This is the primitive: because every indicator in `enrich_daily` is
        backward-looking, a row carries the full as-of-that-date picture.
        Expressing the screen row-wise is what lets the backtest apply it
        point-in-time (the row for the bar being simulated) instead of
        against today's row, which would leak the present into the past.
        Return (passed, reason_if_failed)."""

    def passes_prefilter(self, cfg: MarketConfig, enriched_daily) -> tuple[bool, str]:
        """Screen a symbol as of the LAST row of `enriched_daily` — i.e. "now"
        for a live run, or as-of a date if the frame is sliced to it."""
        if enriched_daily is None or len(enriched_daily) < 210:
            return False, "insufficient history (<210 daily bars)"
        return self.prefilter_row(cfg, enriched_daily.iloc[-1])

    def prefilter_mask(self, cfg: MarketConfig, enriched_daily) -> "pd.Series":
        """Boolean Series over `enriched_daily.index`: would this symbol have
        been screened in on each date? Enriching once and testing rows is
        equivalent to re-enriching each slice (verified), and ~400x cheaper."""
        import pandas as pd

        if enriched_daily is None or enriched_daily.empty:
            return pd.Series(dtype=bool)
        flags = [
            (i >= 209) and self.prefilter_row(cfg, row)[0]
            for i, (_, row) in enumerate(enriched_daily.iterrows())
        ]
        return pd.Series(flags, index=enriched_daily.index, dtype=bool)

    @abstractmethod
    def evaluate(self, ctx: StockContext) -> StrategyResult:
        """Hard gates, watch flags and setup detection for one symbol."""

    @abstractmethod
    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        """Entry/stop/target. May return several variants; `chosen` is the
        one the rest of the system acts on."""

    @abstractmethod
    def classify(
        self,
        ctx: StockContext,
        result: StrategyResult,
        plan: TradePlan,
        sizing_result,
        earnings_days_away: int | None,
        regime_downgrade_active: bool,
    ) -> Decision:
        """Collapse gates + flags + plan + sizing into one decision label."""

    @abstractmethod
    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """Has the entry condition already triggered on the last completed
        bar? Drives both the live HIGH-CONFIDENCE tier and backtest entry."""

    def watch_cap(self, result: StrategyResult) -> str:
        """Most restrictive tier the active watch flags allow. Default: no
        cap — override to implement flag-driven caps."""
        return "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        """Ranking score used by the sector filter and report ordering."""
        return 1.0 if result.has_setup else 0.0

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        """Strategy-specific columns to merge into the report row."""
        return {}

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"<Strategy {self.key}>"
