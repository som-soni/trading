"""Strategy registry.

Add a strategy by writing one module in this package and registering it
below. Nothing in the pipeline, backtest, reporting or storage layers
needs to change.

KNOWN DEFECTS in trend_pullback, found during the post-build review and
deliberately NOT fixed during the extraction so that the refactor stayed
behaviour-identical against the trend-pullback golden harness of the time (since
retired; tests/golden_strategies.py now covers every strategy). Fix them as separate,
individually verifiable changes:

  1. Plan B ignores overhead resistance. `_build_plan(which="B")` sets the
     trigger to H without the resistance walk-up Plan A does, so it can
     place an entry directly beneath resistance — violating the strategy's
     own stated rule ("never place an entry below an overhead level that
     sits within 3% above it"). Measured on 500 cached US symbols: 37 of
     72 live setups (51%) produced a Plan B entry sitting under resistance
     within 3%.
  2. TradePlan with non-positive or NaN risk is not rejected. Every
     downstream comparison (`risk_pct > 8`, `r_mult < 2`, `r_mult >= 2`)
     is False against NaN, so such a plan falls through to TRADE ON
     TRIGGER instead of being discarded. `TradePlan.is_valid` exists for
     this but nothing calls it yet.
  3. TC-02's 10-bar window is defined two different ways: the resumption
     signal uses bars [-11:-1] (excluding today) while the stop/target and
     the S-05 setup test use [-10:] (including today).
  4. `earnings_block_15` uses `< 15` while the D2 hard gate uses `<= 10`
     for the same "within N trading days" phrasing — one of the two is
     off by one.
  5. The sector filter ranks TRADE and TRADE ON TRIGGER names together on
     setup quality alone, so a not-yet-triggered setup can displace one
     that has already fired.
"""

from .base import (
    CAP_ORDER,
    DOWNGRADE_MAP,
    LABELS,
    BEHAVIOURS,
    HORIZONS,
    SELECTION,
    STYLES,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .breakout import BreakoutStrategy
from .chart_pattern import ChartPatternCupStrategy, ChartPatternStrategy
from .chart_pattern_spec import ChartPatternSpecStrategy
from .darvas import DarvasStrategy
from .donchian import DonchianStrategy
from .earnings_gaps import EarningsGapStrategy
from .kell_cycle import KellCycleStrategy
from .kullamagi import KullamagiStrategy
from .minervini_coil import MinerviniCoilStrategy
from .minervini_spec import MinerviniSpecStrategy
from .momentum_burst import MomentumBurstStrategy
from .rs_leaders import RsLeadersStrategy
from .stage_analysis import StageAnalysisStrategy
from .trend_pullback import TrendPullbackStrategy

_REGISTRY: dict[str, Strategy] = {}


def register(strategy: Strategy) -> Strategy:
    _REGISTRY[strategy.key] = strategy
    return strategy


register(TrendPullbackStrategy())
register(DonchianStrategy())
register(DarvasStrategy())
register(EarningsGapStrategy())
register(BreakoutStrategy())
register(ChartPatternSpecStrategy())
register(MinerviniSpecStrategy())
register(MinerviniCoilStrategy())   # a variant: Minervini with the contraction gauge's breakout as its setup
register(RsLeadersStrategy())
register(StageAnalysisStrategy())
register(KullamagiStrategy())
register(MomentumBurstStrategy())
register(KellCycleStrategy())

# Superseded implementations, deliberately NOT registered: each covered the same
# idea as the `_spec` strategy above it, which is built to the written detection
# specification and is a superset of what it replaced. Two entries per idea meant
# two strategies sharing a family and a version number, distinguishable only by
# fingerprint, which is not something a result can be mapped to.
#
#   ChartPatternStrategy     -> ChartPatternSpecStrategy (7 patterns -> 12)
#   ChartPatternCupStrategy  -> ChartPatternSpecStrategy (cup only -> 12)
#
# These two stay imported because they are still CALLED: screening/find_pattern.py
# builds a ChartPatternStrategy directly, since its detector vocabulary is the one
# that tool reports in.
#
# Retired 2026-11-13, by the owner's decision after the strategy family reviews
# (research/strategy-review-summary.md, "Retire now"): each showed no edge in the optimise stage
# (2013-2021) after its trials, and its method has no strong documented record that a more faithful
# version could recover. Unregistered, so the screener, the close routine, backtests and the
# Strategies page no longer run or list them; their past runs stay in report_runs. The modules stay
# for their history and because supertrend's ATR_PERIOD / MULTIPLIER still parameterise the
# `--exit-mode supertrend` exit (backtesting/portfolio_sim.py). Re-registering one is a decision,
# with a new optimise baseline first.
#
#   EmaPullbackStrategy       (ema_pullback)       -- Sharpe 0.13 US / -0.06 India; the setup did worse than its own screen
#   SupertrendStrategy        (supertrend)         -- US picks at the 3rd percentile of random entries; traded signals
#                                                     did worse than skipped ones in both markets
#   Ema100TrendStrategy       (ema100_trend)       -- weekly + daily 100 EMA trade (video notes), built faithfully:
#                                                     excess -5.05 points US / -10.02 India
#   DeliveryBreakoutStrategy  (delivery_breakout)  -- India delivery-% breakout: 106 trades, -0.02R, 15th percentile
#                                                     of random entries
#
# MinerviniStrategy was deleted (2026-10-16). It looked unused, but minervini_spec
# imported it for one method -- `prefilter_row`, the row-wise Trend Template that
# decides which symbols a backtest evaluates at all -- so 624 lines were being kept
# alive by 29. That method now lives in minervini_spec itself; the rest is in
# `git log -- strategies/minervini.py`, and its measured results are in the git
# history of its `status`.

def portfolio_strategies() -> dict:
    """Registry of PORTFOLIO strategies, keyed like `_REGISTRY` but holding
    classes rather than instances.

    Kept separate from `_REGISTRY` on purpose: the screener and backtester
    iterate that registry calling `prefilter_row` and `evaluate`, which a
    portfolio strategy has no business implementing. Listing one there would
    make it a `--strategy` choice that crashes on use.

    Imported lazily because `backtesting.baseline` imports from this package,
    so a module-level import would be circular.
    """
    from ..backtesting.baseline import MomentumBaselineStrategy, VolScaledMomentumStrategy
    from ..backtesting.boucher_bonds_gold import BoucherBondsGoldStrategy
    from ..backtesting.boucher_stocks import BoucherStocksStrategy
    from ..backtesting.combination import CombinationStrategy
    from ..backtesting.dual_momentum import DualMomentumStrategy
    from ..backtesting.etf_swing import EtfSwingStrategy
    from ..backtesting.fno_income import FnoIncomeStrategy
    from ..backtesting.ma_trend import MaTrendStrategy
    from ..backtesting.masonson_tqqq import MasonsonTqqqStrategy
    from ..backtesting.mean_reversion import MeanReversionStrategy
    from ..backtesting.parabolic_short import ParabolicShortStrategy
    from ..backtesting.pead import PeadStrategy
    from ..backtesting.quality_momentum import QualityMomentumStrategy
    from ..backtesting.sector_rotation import SectorRotationStrategy
    from ..backtesting.stage4_shorts import Stage4ShortsStrategy
    from ..backtesting.turtle_trend import TurtleTrendStrategy

    return {c.key: c for c in (MomentumBaselineStrategy, VolScaledMomentumStrategy,
                                DualMomentumStrategy, SectorRotationStrategy,
                                MeanReversionStrategy, PeadStrategy, FnoIncomeStrategy,
                                MaTrendStrategy, CombinationStrategy, QualityMomentumStrategy,
                                Stage4ShortsStrategy, TurtleTrendStrategy, EtfSwingStrategy,
                                ParabolicShortStrategy, MasonsonTqqqStrategy,
                                BoucherStocksStrategy, BoucherBondsGoldStrategy)}


def all_specs() -> dict:
    """Everything that carries a version: per-symbol and portfolio alike."""
    out = {k: type(v) for k, v in _REGISTRY.items()}
    out.update(portfolio_strategies())
    return out


DEFAULT_STRATEGY = TrendPullbackStrategy.key


def get_strategy(key: str) -> Strategy:
    if key not in _REGISTRY:
        raise KeyError(f"unknown strategy '{key}'; available: {sorted(_REGISTRY)}")
    return _REGISTRY[key]


def list_strategies() -> list[str]:
    return sorted(_REGISTRY)


def describe_strategies() -> str:
    """One line per registered strategy, safe to embed in argparse `help=`.

    Percent signs are doubled because argparse runs every help string through
    %-formatting: a description ending "...loss near 7%." makes the following
    newline look like a format specifier and argparse raises
    `ValueError: unsupported format character`, which breaks `--help` for
    EVERY command that lists strategies. Escaping here rather than in each
    description keeps the requirement out of strategy prose, where no author
    would think to look for it.
    """
    return "\n".join(
        f"  {s.key:<16} {s.name} — {type(s).render_doc(s.description)}".replace("%", "%%")
        for s in sorted(_REGISTRY.values(), key=lambda s: s.key)
    )


__all__ = [
    "CAP_ORDER", "DOWNGRADE_MAP", "BEHAVIOURS", "HORIZONS", "LABELS", "SELECTION", "STYLES",
    "Decision", "PlanChoice", "Strategy", "StrategyResult", "TradePlan",
    "TrendPullbackStrategy", "BreakoutStrategy", "DonchianStrategy", "EarningsGapStrategy",
    "ChartPatternStrategy", "ChartPatternCupStrategy", "ChartPatternSpecStrategy",
    "MinerviniSpecStrategy", "StageAnalysisStrategy", "KullamagiStrategy",
    "MomentumBurstStrategy", "KellCycleStrategy",
    "portfolio_strategies", "all_specs",
    "register", "get_strategy", "list_strategies", "describe_strategies",
    "DEFAULT_STRATEGY",
]
