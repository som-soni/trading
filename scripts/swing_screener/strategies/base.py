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

import pandas as pd
from dataclasses import dataclass, field

from ..config.base import MarketConfig
from ..core.context import StockContext

# What a risk-off market regime does to a decision, for the Strategy page. This is the
# default -- every strategy that classifies with DOWNGRADE_MAP on every tier -- and a
# strategy whose classify() treats the regime differently overrides `regime_note`.
REGIME_NOTE = ("When the market regime is risk-off, every decision is downgraded one tier "
               "(HIGH CONFIDENCE → ON TRIGGER → WATCH → AVOID); the reason column then says "
               "'market-regime downgrade applied'.")

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
    "event": "Event / catalyst",
}

# The market behaviour a strategy tries to exploit — the standard first cut
# practitioners make, and the one that says what KIND of bet is being placed.
# Groups with nothing in them yet are listed deliberately: every strategy in
# this repo is a trend/momentum bet, so without the empty rows the sidebar
# would imply the space had been explored when one idea has been tried eight
# ways. They are the map of what is still untested.
BEHAVIOURS = {
    "trend_momentum": "Trend / momentum",
    "mean_reversion": "Mean reversion",
    "relative_value": "Relative value / pairs",
    "event_driven": "Event-driven",
    "carry": "Carry / income",
    "quality_value": "Quality / value",
}

# Within a behaviour, HOW candidates are chosen. The split between ranking
# stocks against each other and judging each against its own history is a
# standard distinction (Jegadeesh & Titman 1993 vs Moskowitz, Ooi & Pedersen
# 2012), and this repo reproduces it cleanly: the cross-sectional strategy
# beats its index in both markets (+6.23% India, +2.59% US) and every
# time-series one loses. Ranking competing signals by 12-1 momentum also beat
# a seeded random control by +7.78pp CAGR (India) and +4.28pp (US) on
# identical signals, while the strategies' own setup scores scored within
# ~1pp of random.
SELECTION = {
    "cross_sectional": "Cross-sectional (ranked against peers)",
    "time_series": "Time-series (judged against its own history)",
    "fundamental": "Fundamental screen",
}


class _DocFields:
    """A settings dataclass seen from a doc placeholder: `{VCP.tight_pct}` renders like a module
    constant does (a float through :g), so "10" rather than "10.0"."""

    def __init__(self, obj):
        self._obj = obj

    def __getattr__(self, name):
        v = getattr(self._obj, name)
        return f"{v:g}" if isinstance(v, float) else v


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


class SpecMeta:
    """Identity, versioning and documentation — everything that describes a
    strategy without saying how it picks stocks.

    Extracted so a PORTFOLIO strategy can carry the same version metadata as a
    per-symbol one. `momentum_baseline` ranks the universe and rebalances; it
    has no `prefilter_row` or `evaluate` and never will, so inheriting the
    per-symbol contract would have meant stub methods that exist only to raise.
    The metadata is genuinely shared; the selection mechanism is not.
    """

    key: str = ""
    name: str = ""
    description: str = ""
    status: str = ""
    thesis: str = ""
    how_it_works: tuple = ()
    caveats: tuple = ()
    param_docs: tuple = ()
    family: str = ""
    version: str = "1.0"
    changelog: tuple = ()
    variant_of: str = ""
    style: str = ""
    selection: str = "time_series"
    behaviour: str = "trend_momentum"

    @classmethod
    def family_name(cls) -> str:
        return cls.family or cls.variant_of or cls.key

    @classmethod
    def doc_namespace(cls) -> dict:
        import sys
        mod = sys.modules[cls.__module__]
        ns = {k: v for k, v in vars(mod).items()
              if k.isupper() and isinstance(v, (int, float, str, tuple))}
        # Numeric attributes, plus SHORT string ones -- a portfolio strategy's configuration is
        # partly words ("ME", "vol_scaled", "inverse_vol") and those deserve the same live
        # rendering as its numbers, or the page restates them by hand and they drift. The prose
        # fields are excluded: they are the documentation, not values to interpolate into it, and
        # {name} expanding to the whole status text would be nonsense.
        _PROSE = {"name", "description", "status", "thesis", "key", "family", "version"}
        for k in dir(cls):
            v = getattr(cls, k, None)
            if k.startswith("_") or k in _PROSE:
                continue
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                ns.setdefault(k, v)
            elif isinstance(v, str) and len(v) <= 32:
                ns.setdefault(k, v)
        return ns

    @classmethod
    def render_doc(cls, text: str) -> str:
        ns = {k: (f"{v:g}" if isinstance(v, float) else v)
              for k, v in cls.doc_namespace().items()}
        # A module-level settings object (minervini_spec's `VCP = VcpParams(...)`) is reachable as
        # `{VCP.zigzag_pct}`, so a rule can quote a detector setting the module never names as its
        # own constant. Rendering only: doc_namespace, which the fingerprint reads, is unchanged.
        import dataclasses as _dc
        import sys
        mod = sys.modules.get(cls.__module__)
        for k, v in (vars(mod).items() if mod else ()):
            if k.isupper() and _dc.is_dataclass(v) and not isinstance(v, type):
                ns.setdefault(k, _DocFields(v))
        return text.format_map(ns)

    @classmethod
    def spec_params(cls) -> dict:
        params: dict = {
            k: v for k, v in cls.doc_namespace().items()
            if isinstance(v, (int, float)) and not isinstance(v, bool)
        }
        for attr in ("gate_codes", "watch_codes", "setup_codes",
                     "allowed_codes", "entry_setup_codes"):
            codes = getattr(cls, attr, None)
            if codes:
                params[attr] = list(codes)
        # A strategy whose rules live in a dataclass defined in ANOTHER module was only
        # fingerprinted on the fields it happened to override via its own module constants.
        # minervini_spec builds `VCP = VcpParams(...)` from its constants, so changing a
        # VcpParams DEFAULT altered the detector's behaviour and the version gate passed —
        # exactly the silent drift this is supposed to prevent. Expand any module-level
        # dataclass instance into its numeric fields.
        import dataclasses as _dc
        import sys

        mod = sys.modules.get(cls.__module__)
        for name, val in sorted(vars(mod).items() if mod else []):
            if name.startswith("_") or not _dc.is_dataclass(val) or isinstance(val, type):
                continue
            for f in _dc.fields(val):
                v = getattr(val, f.name, None)
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    params[f"{name}.{f.name}"] = v
        params["_key"] = cls.key
        return params

    @classmethod
    def fingerprint(cls) -> str:
        import hashlib
        import json

        blob = json.dumps(cls.spec_params(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()[:8]

    @classmethod
    def spec_id(cls) -> str:
        return f"v{cls.version}-{cls.fingerprint()}"

    @classmethod
    def signal_id(cls) -> str:
        """What a cached signal row depends on: the version and every tunable except
        `signal_exempt_consts`. Two spec ids with one signal id record identical rows. Never a
        run's identity -- runs, the version gate and the Strategies page stay on spec_id."""
        import hashlib
        import json

        exempt = set(getattr(cls, "signal_exempt_consts", ()))
        params = {k: v for k, v in cls.spec_params().items() if k not in exempt}
        blob = json.dumps(params, sort_keys=True, separators=(",", ":"))
        return f"v{getattr(cls, 'signal_version', None) or cls.version}-s{hashlib.sha256(blob.encode()).hexdigest()[:8]}"


class PortfolioStrategy(SpecMeta):
    """A strategy that selects by ranking the whole universe and rebalancing,
    rather than screening one symbol at a time. Carries the same versioning
    and documentation as a per-symbol Strategy, and none of its contract."""

    kind: str = "portfolio"
    selection: str = "cross_sectional"


def tradable_point_in_time(cfg, last) -> tuple[bool, str]:
    """The liquidity floor a backtest may apply as of a past bar.

    Deliberately NOT the price floor. `cfg.screener.min_price` exists to keep
    live screening out of penny stocks, and on today's quote it does that. In a
    backtest it is read against SPLIT-ADJUSTED history, where a winner's early
    price is divided by every split it has done since -- so the filter deletes
    exactly the stocks that went up the most, over exactly the years they went
    up. NVDA traded about $15 in 2013 on $126m a day, 12x the liquidity floor;
    stored back-adjusted through a 4:1 and a 10:1 split that is $0.39, under the
    $10 floor, and NVDA does not clear it until 2020-07-08. SMCI not until 2023.

    Dollar volume is split-invariant -- close falls by the split factor and
    volume rises by it, so the product is unchanged -- so it carries the whole
    liquidity test here. Live screening keeps the price floor, in
    screens/base.py's `tradable`, where today's price really is today's price.
    """
    if cfg.screener.min_dollar_volume:
        dv = last.get("dollar_vol_sma20")
        if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
            return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
    return True, "passed"


class Strategy(SpecMeta, ABC):
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
    # setup code -> what it is in words, for the backtest trades panel (a trade's `setup` is
    # the code); a code missing here is shown as the bare code
    setup_names: dict[str, str] = {}
    # gate code -> a short name for the chart's checklist (the full rule stays in gate_docs); may use
    # {NAME} placeholders like the docs. A code missing here is shown as the bare code.
    gate_titles: dict[str, str] = {}
    # True when TradePlan.target is only a number for sizing and the real exit is a rule (a trailing
    # channel, a moving average): the chart's Trade setups layer then labels it nominal, not "target"
    nominal_target: bool = False
    # extra report columns this strategy's report_extras() returns, and which
    # of them are numeric. Declared here so output.py never needs to know any
    # strategy's specifics — previously breakout_pivot/pct_from_pivot were
    # hardcoded into the shared column list, and anything not hardcoded was
    # silently dropped from the report.
    # True when build_plans() reads values that evaluate() stashed on
    # ctx.extras. Such a strategy cannot use a cached signal that predates
    # extras being persisted — it must recompute that bar.
    needs_ctx_extras: bool = False
    # Module constants that evaluate() never reads -- the exits, the stop and target placement,
    # sizing, the portfolio rules, the prefilter's floors. A `backtest_signals` row records only
    # build_context() + evaluate(), so it is the same whatever these are set to: a `--const`
    # variant that moves only these may start from the rows of the run without them
    # (`signal_id`, backtest.seed_signal_cache) instead of rescanning the universe. Still part of
    # spec_params / spec_id: the variant is a different strategy and is grouped as one.
    # tests/test_signal_exempt.py checks that evaluate() cannot reach any of them.
    signal_exempt_consts: tuple[str, ...] = ()
    # The version whose signal scan this one keeps, when a version bump changed only what happens
    # AFTER evaluate() (exits, stop/target placement, sizing, plan rules) -- left unset, it is
    # `version`, so every bump starts a fresh scan. Pin it to the previous version on such a bump and
    # signal_id stays put, so the next backtest carries the cached signal rows forward
    # (backtest._signal_peers) instead of rescanning the universe for hours. Never pin it
    # across a change to build_context(), evaluate() or the detectors: the carried rows would replay
    # the old detections. tests/test_signal_exempt.py checks it names a version in the changelog.
    signal_version: str | None = None
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
    # the first session a signal may come on, when earlier than min_bars (None = min_bars); min_bars
    # stays the history a backtest loads before its start. See `signal_floor`. None, not 0: a
    # numeric class attribute enters every strategy's fingerprint, and an unused default must not.
    min_signal_bars: int | None = None

    def signal_floor(self) -> int:
        """Bars a symbol needs before it can give a signal."""
        return self.min_signal_bars or self.min_bars

    def rs_young_min_bars(self) -> int:
        """Sessions after which the RS rating rates a listing younger than a year on its history so
        far; 0 = it stays unrated until it has a year (backtesting/spec.rs_ratings)."""
        return 0
    # What classify() does when `regime_downgrade_active` (a risk-off market), in words, for
    # the Strategy page -- including the reason text it appends. Defaults to the shared
    # one-tier downgrade; override it when classify() does anything else, and change it in
    # the same change as that code. `{NAME}` placeholders render like the other docs.
    regime_note: str = REGIME_NOTE
    # Decision label code ("TRADE_ON_TRIGGER", ...) -> what that tier means for THIS strategy,
    # replacing the shared text in strategies/docs.py DECISIONS for the Strategy page's
    # Decisions table. Override a tier only when classify() reaches it differently from the
    # shared description; `{NAME}` placeholders render like the other docs.
    decision_docs: dict[str, str] = {}

    # --- how a trade is entered and left, for the Strategy page ---
    # `entry_rules` / `exit_rules`: one rule per item, `{NAME}` placeholders like the other docs.
    # `backtest_args`: the flags its real exit policy needs, appended to the page's backtest command.
    # The exit is the backtest's: `--exit-mode` (bracket | trail_atr | ma | donchian | minervini) in
    # backtesting/portfolio_sim.py, plus opt-in trade management for every mode but minervini
    # (ExitPolicy.be_r / time_stop_bars / time_stop_mult / partial_at_target):
    #   --breakeven-r X        stop to entry + round-trip costs once the HIGH reaches entry + X·R,
    #                          from the next session (exit reason BREAKEVEN)
    #   --time-stop-bars N     sold at the close of the Nth session after entry (TIME)
    #   --time-stop-mult X     … X × the setup's duration in bars, when signal_meta() supplies
    #                          meta["setup_start"] (else the --time-stop-bars count)
    #   --partial-at-target F  F of the shares sold at the target; the rest trails --atr-mult × ATR14
    #                          under its highest close (TRAIL_STOP)
    # A strategy that adopts any of them puts the flags in `backtest_args` and the rule in
    # `exit_rules`, and bumps its version (its backtested behaviour changed).
    entry_rules: tuple = ()
    exit_rules: tuple = ()
    # Optional finer split, for a strategy whose trade has more parts than "in" and "out". When
    # `stop_rules` or `target_rules` is set, the page gives each group its own section -- Entry,
    # Stop, Target, Exit, Position size, When no new trade is taken -- instead of one "Entry,
    # stop and target" list, and `entry_rules` / `exit_rules` then hold only the buy and the sell.
    stop_rules: tuple = ()
    target_rules: tuple = ()
    sizing_rules: tuple = ()
    filter_rules: tuple = ()
    backtest_args: str = ""
    # The variant the DAILY SCREEN runs under: {"name", "const": {NAME: value}, "why"}, applied by
    # strategies/variants.apply_live_variant in the screening process only -- backtests measure the
    # shipped rules plus their own explicit flags, never this. It exists so a variant that is
    # winning its A/B can list today's candidates before it has earned a place in the shipped rules,
    # and be swapped for a better one by editing this one declaration. Every screening row records
    # the variant and spec id it was produced under, so the Candidates tab says which rules it shows.
    live_variant: dict | None = None
    # Human labels for the codes of the strategy's structure check (e.g. VCP-02 -> "no base yet"),
    # so the Candidates tab can say where a qualifying stock is stuck without a second copy in JS.
    base_rules: dict | None = None
    # A strategy whose setups sit on a detected pattern (a base, a cup) lists the pattern's own
    # checks here, in the order they are evaluated: {check code: rule}. The Strategy page shows them
    # as a table between the gates and the setups, under `pattern_title`, after `pattern_intro`
    # (the terms the checks use). `{NAME}` placeholders render like the other docs.
    pattern_title: str = ""
    pattern_intro: str = ""
    pattern_docs: dict = {}

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

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """Live screening: is the market risk-off for THIS strategy's new buys? `default` is the
        shared market-regime downgrade; a strategy whose backtest runs its own market filter
        overrides this so the live screen applies the same test."""
        return default

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

    def cached_signal_ok(self, extras: dict) -> bool:
        """Whether a cached `backtest_signals` row (same spec_id) is still complete enough to
        reuse. Override when the strategy starts recording a new extra that changes no rule —
        so no version bump — and a row written before it should be recomputed, not reused."""
        return True

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The structure this strategy saw at one signal, as shapes for the chart's trade-debug
        overlay (web: Backtest trades → the trades panel). `sig` is one `backtest_signals` row as a
        dict plus its market and symbol — the exact record written when the backtest evaluated that bar (date, hard_gates,
        setups, h_value/h_index, prior_swing_low, watch_notes, extras, all parsed) — so the overlay
        shows what the run actually traded on, never a re-detection that current code might change.

        Shapes (dates are ISO strings; `bars` may replace `from` when only a bar count is known):
          {"shape": "box",   "from"|"bars", "to", "top", "bottom", "label", "role", "dash"?}
          {"shape": "level", "from"|"bars", "to", "price", "label", "role", "dash"?}
          {"shape": "line",  "from", "to", "p0", "p1", "label", "role", "dash"?}   # a sloped line
          {"shape": "path",  "from", "to", "points": [{"at", "price", "label"}], "label", "role"}
                                                       # swing points joined in order, each labelled
                                                       # (a point with label "" is a curve vertex)
          {"shape": "dots",  "points": [{"at", "price", "label"?}], "label", "role"}   # markers, e.g. line touches
          {"shape": "note",  "at", "price"?, "text"}   # the WHY — rendered as a callout + panel text
        Roles (the chart's colour key): base, pivot, stop, target, support, level.

        Default: the resistance the entry had to clear (H), the prior swing low, and a note naming
        the active setups. Override to draw the strategy's own anatomy — the base, the contractions,
        the pattern — and to say how it was identified."""
        d = str(sig["date"])
        out: list[dict] = []
        if sig.get("h_value") and sig.get("h_index"):
            out.append({"shape": "level", "from": str(sig["h_index"]), "to": d, "price": sig["h_value"],
                        "label": f"H {sig['h_value']:.2f} — the resistance the entry had to clear", "role": "pivot"})
        if sig.get("prior_swing_low"):
            out.append({"shape": "level", "bars": 60, "to": d, "price": sig["prior_swing_low"],
                        "label": "prior swing low — structural support", "role": "support"})
        active = [k for k, v in (sig.get("setups") or {}).items() if v]
        if active:
            notes = [str(v) for v in (sig.get("watch_notes") or {}).values() if v][:2]
            out.append({"shape": "note", "at": d, "price": sig.get("h_value"),
                        "text": f"Setup {', '.join(active)} on {d}" + (" · " + " · ".join(notes) if notes else "")})
        return out

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """The structure of one setup bar for the chart's Trade setups layer (strategies/live_setups.py):
        shapes in the chart_anatomy schema, built from the live context. A shape with role "uptrend" is
        drawn in the setup's first zone, the rest in its second. Default: this strategy's own
        chart_anatomy of the same bar. Override to draw from the context what a stored signal row
        cannot carry (a consolidation's extent, the advance into it)."""
        return self.chart_anatomy(sig)

    def setups_live(self, raw_daily, cfg: MarketConfig, symbol: str, years: int | None = 5,
                    anchors: list[dict] | None = None) -> list[dict]:
        """Every setup episode over the last `years` of `raw_daily`, run on demand through this
        strategy's own evaluate / build_plans / classify (see strategies/live_setups.py). Exploration
        only: what a run traded comes from its stored signals. `anchors` (a selected run's trades, as
        {"entry": fill date, "stop": initial stop}) makes an episode holding one be judged on the bar it traded."""
        from . import live_setups
        return live_setups.scan(self, raw_daily, cfg, symbol, years, anchors)

    def __repr__(self) -> str:  # pragma: no cover - debug convenience
        return f"<Strategy {self.key}>"
