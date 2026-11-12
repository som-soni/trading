"""Override a strategy's numeric module constants for this process.

One mechanism behind both `backtest --const NAME=VALUE` and a strategy's declared `live_variant`
(which the daily screen applies). Overriding a module constant moves the strategy's fingerprint,
so whatever runs under an override carries its own spec id and cannot pass for the shipped rules.

The danger is an override that moves the constant -- and the fingerprint with it -- but not the
behaviour, so a run of the shipped rules goes out under a variant's label and reads as a clean
result. There are three ways that happens, and each is refused here rather than allowed to pass:

  1. The value was BAKED into an object when the strategy's module was imported:
     `VCP = VcpParams(max_base_depth_pct=MAX_BASE_DEPTH_PCT, ...)`. The object keeps the old value.
     This happened: `--const MAX_BASE_DEPTH_PCT=25` forked the spec id and left the detector at 50%;
     it was caught before the run started. `backtest --vcp max_base_depth_pct=25` is the override
     that reaches it.
  2. The constant is IMPORTED into the strategy's module from another one
     (`from ..screens.criteria import RS_MIN_SCORE`). Overriding the copy here leaves the defining
     module's own uses on the old value, so half the strategy moves and half does not.
  3. Another module that is ALREADY imported read it into a class body or a module-level object:
     `ExitPolicy.trend_volume = bool(_ms.TREND_EXIT_NEEDS_VOLUME)` in portfolio_sim. The backtest
     imports portfolio_sim lazily, after its overrides, which is the only reason exit-rule overrides
     have worked; this check is what keeps that true if the import order ever changes.

Only module level and class bodies count as "at import time" -- a function body reads the module
global when it runs, and sees the override.
"""

import ast
import contextlib
import importlib
import inspect
import sys

_TREES: dict = {}


def _tree(mod):
    name = mod.__name__
    if name not in _TREES:
        try:
            _TREES[name] = ast.parse(inspect.getsource(mod))
        except (OSError, TypeError, SyntaxError):
            _TREES[name] = None
    return _TREES[name]


def _read_at_import(tree, name: str, as_attribute: bool) -> str | None:
    """Where `tree` reads `name` while its module is being imported: a module-level statement or a
    class body, never a function body. As a bare name (this module's own constant) or as an
    attribute (`_ms.NAME`, another module's). Returns a short location, or None."""
    def walk(node):
        # a lambda's body runs when it is CALLED (`field(default_factory=lambda: _ms.PARTIAL_R)` reads the
        # constant each time an ExitPolicy is built), so it is not an import-time read
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.Lambda):
                continue
            yield child
            yield from walk(child)

    def hit(stmt) -> bool:
        for n in (stmt, *walk(stmt)):
            if as_attribute and isinstance(n, ast.Attribute) and n.attr == name and isinstance(n.ctx, ast.Load):
                return True
            if not as_attribute and isinstance(n, ast.Name) and n.id == name and isinstance(n.ctx, ast.Load):
                return True
        return False

    def label(stmt, prefix: str) -> str:
        t = stmt.targets[0] if isinstance(stmt, ast.Assign) else getattr(stmt, "target", None)
        return prefix + (t.id if isinstance(t, ast.Name) else "<statement>")

    def scan(body, prefix: str) -> str | None:
        for st in body:
            if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if isinstance(st, ast.ClassDef):
                found = scan(st.body, f"{prefix}{st.name}.")
                if found:
                    return found
                continue
            if hit(st):
                return label(st, prefix)
        return None

    return scan(tree.body, "") if tree is not None else None


def _refusal(mod, name: str) -> str | None:
    tree = _tree(mod)
    if tree is not None:
        for st in tree.body:
            if isinstance(st, ast.ImportFrom) and any((a.asname or a.name) == name for a in st.names):
                return (f"{name} is imported into {mod.__name__} from {st.module}; overriding the copy here would "
                        f"leave {st.module}'s own uses of it on the old value")
        where = _read_at_import(tree, name, as_attribute=False)
        if where:
            return (f"{name} is baked into {where} when {mod.__name__} is imported, so the override would move "
                    f"the fingerprint but not the behaviour"
                    + (" -- use `backtest --vcp <field>=VALUE` for a VcpParams field" if where.startswith("VCP") else ""))
    for mname, other in list(sys.modules.items()):
        if other is mod or other is None or not mname.startswith("swing_screener."):
            continue
        where = _read_at_import(_tree(other), name, as_attribute=True)
        if where:
            return (f"{name} was already read into {mname}.{where} when that module was imported, before this "
                    f"override -- import it later, or the override will not reach it")
    return None


def apply_consts(strategy_key: str, consts: dict) -> dict:
    """Set numeric module constants of a strategy for this process. Returns {NAME: new value}.
    Raises ValueError for an unknown or non-numeric constant, or one the override cannot reach."""
    from . import get_strategy
    mod = importlib.import_module(type(get_strategy(strategy_key)).__module__)
    applied = {}
    for k, v in consts.items():
        k = str(k).strip()
        cur = getattr(mod, k, None)
        if not k.isupper() or not isinstance(cur, (int, float)) or isinstance(cur, bool):
            raise ValueError(f"{strategy_key} has no numeric constant {k!r}")
        why = _refusal(mod, k)
        if why:
            raise ValueError(why)
        setattr(mod, k, type(cur)(float(v)))
        applied[k] = getattr(mod, k)
    return applied


def split_signal_exempt(strategy_key: str, consts: dict) -> tuple[dict, dict]:
    """(overrides the signal scan reads, overrides it never reads) -- the second part is the
    strategy's `signal_exempt_consts`. Applying the first alone gives the run whose cached
    signal rows the full variant can reuse (backtest.seed_signal_cache)."""
    from . import get_strategy
    exempt = set(getattr(get_strategy(strategy_key), "signal_exempt_consts", ()))
    scan = {k: v for k, v in consts.items() if str(k).strip() not in exempt}
    return scan, {k: v for k, v in consts.items() if k not in scan}


def apply_live_variant(strategy_key: str) -> dict | None:
    """Apply the strategy's declared `live_variant`, if it has one. Returns what was applied --
    {"name", "const", "spec_id", "why"} -- for the caller to record beside its output, or None."""
    from . import get_strategy
    lv = getattr(type(get_strategy(strategy_key)), "live_variant", None)
    if not lv or not lv.get("const"):
        return None
    applied = apply_consts(strategy_key, lv["const"])
    return {"name": lv.get("name", ""), "const": applied, "why": lv.get("why", ""),
            "spec_id": get_strategy(strategy_key).spec_id()}


def apply_market_consts(strategy_key: str, market: str, skip=()) -> dict:
    """Apply the strategy's declared rules for `market` (`market_consts`), except names in `skip` (an explicit
    `--const` wins). Returns {NAME: value} applied, or {} when the market has none. For a process that runs
    one market only: the change is process-wide, like every override here."""
    from . import get_strategy
    mc = (getattr(type(get_strategy(strategy_key)), "market_consts", None) or {}).get(market) or {}
    skip = {str(k).strip() for k in skip}
    consts = {k: v for k, v in (mc.get("const") or {}).items() if k not in skip}
    return apply_consts(strategy_key, consts) if consts else {}


@contextlib.contextmanager
def market_rules(strategy_key: str, market: str, skip=(), apply: bool = True):
    """Apply the strategy's rules for `market` for the duration of the block, then restore the module's
    constants -- including any the block itself overrode in the meantime (backtest.main applies the
    market's rules and --const again). The job runner screens and backtests several markets in ONE
    process, so the US rules must not still be in force when India runs. Yields {NAME: value} applied."""
    import importlib
    from . import get_strategy
    mod = importlib.import_module(type(get_strategy(strategy_key)).__module__)
    saved = {k: v for k, v in vars(mod).items()
             if k.isupper() and isinstance(v, (int, float)) and not isinstance(v, bool)}
    try:
        yield apply_market_consts(strategy_key, market, skip=skip) if apply else {}
    finally:
        for k, v in saved.items():
            setattr(mod, k, v)


def market_spec_id(strategy_key: str, market: str, skip=()) -> str:
    """The spec id a run of `market` will carry under that market's rules, without leaving them applied."""
    from . import get_strategy
    with market_rules(strategy_key, market, skip=skip):
        return get_strategy(strategy_key).spec_id()


def market_spec_ids(strategy_key: str) -> dict:
    """{market: spec id under that market's declared rules} -- for a process that serves every market (the
    web server), where the shared rules must stay in force."""
    from . import get_strategy
    return {m: market_spec_id(strategy_key, m)
            for m in (getattr(type(get_strategy(strategy_key)), "market_consts", None) or {})}
