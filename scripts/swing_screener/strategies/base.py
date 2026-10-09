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
from ..core.context import StockContext

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

# Trading-style families, in display order — the Strategies page groups its
# sidebar by these. Every strategy declares one via `Strategy.style`;
# docs.check() (and so tests/test_strategy_docs.py) rejects anything else.
STYLES = {
    "pullback": "Pullback / continuation",
    "breakout": "Breakout from a base",
    "trend": "Trend following",
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
    # extra report columns this strategy's report_extras() returns, and which
    # of them are numeric. Declared here so output.py never needs to know any
    # strategy's specifics — previously breakout_pivot/pct_from_pivot were
    # hardcoded into the shared column list, and anything not hardcoded was
    # silently dropped from the report.
    # True when build_plans() reads values that evaluate() stashed on
    # ctx.extras. Such a strategy cannot use a cached signal that predates
    # extras being persisted — it must recompute that bar.
    needs_ctx_extras: bool = False
    extra_columns: tuple[str, ...] = ()
    extra_numeric_columns: tuple[str, ...] = ()
    # True when the LIVE screener should attach current fundamentals to the
    # rows that passed. Deliberately screener-only: those figures are the
    # current restatement with no as-of history, so a backtest reading them
    # would be ranking a 2015 stock by a 2026 margin. See
    # marketdata/fundamentals.py.
    wants_live_fundamentals: bool = False

    # ---- the screen this strategy draws its candidates from (screens/) -----------------------
    # `screen_gates` maps this strategy's gate code -> the screen criterion it applies, in order.
    # Those gates ARE the screen's criteria (same code path, screens/criteria.py); the strategy's
    # other gates are its own trade rules. `apply_screen` records them on the result.
    screen_key: str = ""
    screen_gates: dict[str, str] = {}
    # minimum daily bars before this strategy will evaluate a symbol
    min_bars: int = 260

    # --- identity and versioning ---
    # `family` is the high-level strategy a reader thinks in terms of
    # ("minervini"); `version` distinguishes rule sets within it. Keeping them
    # apart is what stops the strategy list growing every time a threshold
    # moves: families stay few, versions accumulate underneath.
    #
    # The rule this enforces: CHANGING A TUNABLE REQUIRES A VERSION BUMP.
    # `strategies/versions.py --check` fails when a fingerprint moves without
    # one, because the alternative is what happened before — Minervini's VCP
    # threshold went 12% -> 10% in place and every earlier run became
    # irreproducible with nothing recording that it had changed.
    # `family` groups successive VERSIONS of one strategy: minervini v1 (built
    # from prose) and v2 (built to the written spec) are the same strategy
    # refined, not two strategies. `variant_of` means something different --
    # a sibling experiment rather than a successor, like chart_pattern_cup,
    # which restricts its parent's detectors instead of replacing them.
    family: str = ""
    version: str = "1.0"
    # (version, ISO date, what changed and why) — newest first
    changelog: tuple[tuple[str, str, str], ...] = ()

    @classmethod
    def family_name(cls) -> str:
        """The high-level strategy this belongs to: an explicit `family` wins,
        otherwise a variant reports its parent, otherwise the key stands
        alone."""
        return cls.family or cls.variant_of or cls.key

    @classmethod
    def spec_params(cls) -> dict:
        """Every numeric tunable that defines this version's behaviour.

        Reuses `doc_namespace()` — the same values the documentation
        substitutes into `{NAME}` placeholders — so the fingerprint cannot
        drift from what the published spec says. A parameter that is not
        documented is also not fingerprinted, which is the right incentive.
        """
        params: dict = {
            k: v for k, v in cls.doc_namespace().items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        # Numbers alone are not the whole rule set. `chart_pattern_cup`
        # differs from its parent only by which detectors it admits -- same
        # module, so identical constants and, on numbers alone, an identical
        # fingerprint. The declared code vocabularies change behaviour and
        # must be part of the identity.
        for attr in ("gate_codes", "watch_codes", "setup_codes",
                     "allowed_codes", "entry_setup_codes"):
            codes = getattr(cls, attr, None)
            if codes:
                params[attr] = list(codes)
        # and the key, so two unrelated strategies can never collide
        params["_key"] = cls.key
        return params

    @classmethod
    def fingerprint(cls) -> str:
        """Short, stable hash of the tunables. Two runs with the same
        fingerprint were produced by the same rule set."""
        import hashlib
        import json

        blob = json.dumps(cls.spec_params(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:8]

    @classmethod
    def spec_id(cls) -> str:
        """`v2.0-73e82535` — goes into run directory names so a result can
        always be traced back to the exact parameters that produced it."""
        return f"v{cls.version}-{cls.fingerprint()}"

    # --- classification, for the Strategies page sidebar ---
    # `style` is the trading-style family this strategy belongs to (a key of
    # STYLES above); `variant_of` names the registered strategy this one is a
    # restriction or re-reading of, and nests it under that parent in the
    # sidebar. docs.check() enforces both: style must be a STYLES key, and a
    # variant must point at an existing non-variant parent of the same style.
    style: str = ""
    variant_of: str = ""

    # --- self-description, for reports ---
    # A report that lists symbols without saying what the strategy was looking
    # for is unreadable by anyone who didn't write it (including you, later).
    thesis: str = ""              # one sentence: what edge is being claimed
    how_it_works: tuple[str, ...] = ()   # the mechanics, in plain language
    caveats: tuple[str, ...] = ()        # what is known to be wrong or untested

    # --- full reference documentation (the web app's Strategy page) ---
    # This page is GENERATED from these attributes, so it cannot drift from
    # the code — and tests/test_strategy_docs.py fails if a code in
    # gate_codes / watch_codes / setup_codes has no entry here, if an entry
    # documents a code that no longer exists, or if a placeholder is broken.
    #
    # Text may embed `{NAME}` placeholders naming a module-level constant of
    # the strategy's own module (e.g. "stop more than {MAX_STOP_PCT}% below
    # entry"); the page substitutes the live value, so changing a threshold
    # updates the explanation automatically. Use `{{` / `}}` for literal braces.
    status: str = ""                       # one line: validated? edge? e.g. "No demonstrated edge"
    gate_docs: dict[str, str] = {}         # hard gate code -> what it requires (failing = AVOID)
    watch_docs: dict[str, str] = {}        # watch flag code -> what it flags (caps the decision)
    setup_docs: dict[str, str] = {}        # setup code -> the pattern it recognises
    entry_rules: tuple[str, ...] = ()      # how entry, stop and target are placed
    exit_rules: tuple[str, ...] = ()       # how a trade ends, live and in the backtest
    # (label, source, meaning): source is a module constant name, or
    # "cfg.<field>" / "cfg.screener.<field>" for a per-market MarketConfig value
    param_docs: tuple[tuple[str, str, str], ...] = ()
    # the backtest invocation that measures the strategy with its REAL exit
    # policy (run from scripts/ with PYTHONPATH=.); empty = default bracket exit
    backtest_args: str = ""

    @classmethod
    def doc_namespace(cls) -> dict:
        """Values `{NAME}` placeholders (and param_docs sources) can refer to:
        the module's UPPER_CASE constants, plus the class's own numeric
        tunables (e.g. `entry_channel`, `min_structural_r`), inherited ones included."""
        import sys
        mod = sys.modules[cls.__module__]
        ns = {k: v for k, v in vars(mod).items() if k.isupper() and isinstance(v, (int, float, str, tuple))}
        for k in dir(cls):
            v = getattr(cls, k, None)
            if not k.startswith("_") and isinstance(v, (int, float)) and not isinstance(v, bool):
                ns.setdefault(k, v)
        return ns

    @classmethod
    def render_doc(cls, text: str) -> str:
        """Substitute `{NAME}` placeholders with the live constant values."""
        ns = {k: (f"{v:g}" if isinstance(v, float) else v) for k, v in cls.doc_namespace().items()}
        return text.format_map(ns)

    @classmethod
    def explain(cls) -> str:
        """Markdown block describing the strategy for a report."""
        out: list[str] = []
        r = cls.render_doc  # `{NAME}` placeholders -> live values, same as the web page
        if cls.thesis:
            out += [f"**Thesis.** {r(cls.thesis)}", ""]
        if cls.how_it_works:
            out += ["**How it works**", ""]
            out += [f"{i}. {r(step)}" for i, step in enumerate(cls.how_it_works, 1)]
            out.append("")
        if cls.caveats:
            out += ["**Known caveats**", ""]
            out += [f"- {r(c)}" for c in cls.caveats]
            out.append("")
        return "\n".join(out)

    @abstractmethod
    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The screen, evaluated against ONE enriched daily row.

        This is the primitive: because every indicator in `enrich_daily` is
        backward-looking, a row carries the full as-of-that-date picture.
        Expressing the screen row-wise is what lets the backtest apply it
        point-in-time (the row for the bar being simulated) instead of
        against today's row, which would leak the present into the past.
        Return (passed, reason_if_failed)."""

    def apply_screen(self, ctx, result: "StrategyResult") -> None:
        """Evaluate the screen's criteria and record them under this strategy's gate codes."""
        from ..screens import get_screen
        screen = get_screen(self.screen_key)
        for gate, crit in self.screen_gates.items():
            ok, note = screen.criterion(crit)(ctx)
            if ok:
                result.ok(gate, note)
            else:
                result.fail(gate, note)

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

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """Order details for the portfolio simulator (backtesting/portfolio_sim.py, "Spec mode"):
        an open-price order, a buy range, a per-base id, a maximum stop at the fill. Must read only
        ctx.extras and the plan (a cached signal has no full price history). Default: none — a
        resting buy-stop at plan.entry, as for every strategy that does not override this."""
        return {}

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"<Strategy {self.key}>"
