"""Strategy registry.

Add a strategy by writing one module in this package and registering it
below. Nothing in the pipeline, backtest, reporting or storage layers
needs to change.

KNOWN DEFECTS in trend_pullback, found during the post-build review and
deliberately NOT fixed during the extraction so that the refactor stayed
behaviour-identical against tests/golden_baseline.py. Fix them as separate,
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
from .donchian import DonchianStrategy
from .minervini import MinerviniStrategy
from .minervini_spec import MinerviniSpecStrategy
from .trend_pullback import TrendPullbackStrategy

_REGISTRY: dict[str, Strategy] = {}


def register(strategy: Strategy) -> Strategy:
    _REGISTRY[strategy.key] = strategy
    return strategy


register(TrendPullbackStrategy())
register(DonchianStrategy())
register(BreakoutStrategy())
register(ChartPatternSpecStrategy())
register(MinerviniSpecStrategy())

# Superseded implementations, deliberately NOT registered: each covered the same
# idea as the `_spec` strategy above it, which is built to the written detection
# specification and is a superset of what it replaced. Two entries per idea meant
# two strategies sharing a family and a version number, distinguishable only by
# fingerprint, which is not something a result can be mapped to.
#
#   ChartPatternStrategy     -> ChartPatternSpecStrategy (7 patterns -> 12)
#   ChartPatternCupStrategy  -> ChartPatternSpecStrategy (cup only -> 12)
#   MinerviniStrategy        -> MinerviniSpecStrategy    (same screen, gates and
#                               setups; the spec version is the one under active
#                               development)
#
# The modules are still in the tree, so re-registering one is a single line. Their
# measured results are in the git history of their `status` attributes.

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
    from ..backtesting.baseline import MomentumBaselineStrategy

    return {MomentumBaselineStrategy.key: MomentumBaselineStrategy}


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
        f"  {s.key:<16} {s.name} — {s.description}".replace("%", "%%")
        for s in sorted(_REGISTRY.values(), key=lambda s: s.key)
    )


__all__ = [
    "CAP_ORDER", "DOWNGRADE_MAP", "BEHAVIOURS", "LABELS", "SELECTION", "STYLES",
    "Decision", "PlanChoice", "Strategy", "StrategyResult", "TradePlan",
    "TrendPullbackStrategy", "BreakoutStrategy", "DonchianStrategy",
    "ChartPatternStrategy", "ChartPatternCupStrategy", "ChartPatternSpecStrategy",
    "MinerviniStrategy", "MinerviniSpecStrategy",
    "portfolio_strategies", "all_specs",
    "register", "get_strategy", "list_strategies", "describe_strategies",
    "DEFAULT_STRATEGY",
]
