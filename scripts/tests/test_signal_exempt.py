"""A strategy's `signal_exempt_consts` must be constants its signal scan cannot read.

A `--const` variant that moves only exempt constants shares the shipped run's `signal_id` and
starts from its cached signal rows (backtesting/backtest.py `seed_signal_cache`). That is only
honest if those rows are what the variant would have computed: a cached row records
build_context() + evaluate(), so no exempt constant may be read by evaluate() or anything it
calls. An exemption that is wrong reuses rows the variant's own rules would not have written,
and the variant's report reads as a measurement of them.

Checked statically, per strategy, for every exempt NAME:
  - it is a numeric module constant the fingerprint covers (`spec_params`), not a dataclass field;
  - its module does not read it at import (it would be baked into an object evaluate() uses);
  - no function evaluate() reaches -- in the strategy's module or strategies/base.py, by a bare
    call or through self/cls -- names it, as a bare name or as `self.NAME`;
  - no module the strategy's module imports at module level (core/, screens/, ...) reads it as
    an attribute of another module (`_ms.NAME`).

Also: a pinned `signal_version` (a version bump that kept the scan, so the next run carries the
cached rows forward -- backtest._signal_peers) names a released version, not a later one.

Run:  PYTHONPATH=. .venv/bin/python -m tests.test_signal_exempt
"""

import ast
import importlib
import importlib.util
import inspect
import sys

from swing_screener.strategies import get_strategy, list_strategies
from swing_screener.strategies import base as base_mod

ROOTS = ("evaluate",)


def _tree(mod):
    try:
        return ast.parse(inspect.getsource(mod))
    except (OSError, TypeError):
        return None


def _functions(tree) -> dict:
    out: dict = {}
    for st in tree.body:
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.setdefault(st.name, []).append(st)
        elif isinstance(st, ast.ClassDef):
            for b in st.body:
                if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.setdefault(b.name, []).append(b)
    return out


def _callees(fn) -> set:
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Call):
            f = n.func
            if isinstance(f, ast.Name):
                out.add(f.id)
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in ("self", "cls"):
                out.add(f.attr)
    return out


def _reads(fn) -> set:
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.add(n.id)
        elif isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and n.value.id in ("self", "cls"):
            out.add(n.attr)
    return out


def _scan_reads(mod) -> tuple[set, set]:
    """(names read by every function evaluate() reaches, the functions reached)."""
    funcs = _functions(_tree(mod))
    for k, v in _functions(_tree(base_mod)).items():
        funcs.setdefault(k, []).extend(v)
    seen, todo = set(), list(ROOTS)
    while todo:
        f = todo.pop()
        if f in seen or f not in funcs:
            continue
        seen.add(f)
        for node in funcs[f]:
            todo.extend(_callees(node))
    reads = set()
    for f in seen:
        for node in funcs[f]:
            reads |= _reads(node)
    return reads, seen


def _imported_modules(mod) -> list:
    """swing_screener modules `mod` imports at module level (not the lazy imports in functions)."""
    out, pkg = [], mod.__name__.rpartition(".")[0]
    for st in _tree(mod).body:
        if isinstance(st, ast.ImportFrom):
            base = importlib.util.resolve_name("." * st.level + (st.module or ""), pkg) if st.level else st.module
            names = [base] + [f"{base}.{a.name}" for a in st.names]
        elif isinstance(st, ast.Import):
            names = [a.name for a in st.names]
        else:
            continue
        for n in names:
            m = sys.modules.get(n)
            if m is not None and n.startswith("swing_screener.") and inspect.ismodule(m):
                out.append(m)
    return out


def _attribute_reads(mod, name: str) -> bool:
    tree = _tree(mod)
    return tree is not None and any(
        isinstance(n, ast.Attribute) and n.attr == name and isinstance(n.ctx, ast.Load)
        and not (isinstance(n.value, ast.Name) and n.value.id in ("self", "cls"))
        for n in ast.walk(tree))


def check(key: str) -> list[str]:
    from swing_screener.strategies.variants import _read_at_import

    strat = get_strategy(key)
    exempt = tuple(getattr(strat, "signal_exempt_consts", ()))
    if not exempt:
        return []
    mod = sys.modules[type(strat).__module__]
    params = type(strat).spec_params()
    reads, reached = _scan_reads(mod)
    others = _imported_modules(mod)
    problems = []
    if len(set(exempt)) != len(exempt):
        problems.append(f"{key}: signal_exempt_consts lists a name twice")
    for name in exempt:
        if name not in params or "." in name:
            problems.append(f"{key}: {name} is not a fingerprinted module constant")
            continue
        where = _read_at_import(_tree(mod), name, as_attribute=False)
        if where:
            problems.append(f"{key}: {name} is read at import, into {where}")
        if name in reads:
            fns = sorted(f for f in reached if any(name in _reads(n) for n in _functions(_tree(mod)).get(f, [])))
            problems.append(f"{key}: {name} is read on the scan path (evaluate reaches {', '.join(fns) or 'base.py'})")
        for other in others:
            if _attribute_reads(other, name):
                problems.append(f"{key}: {name} is read as an attribute in {other.__name__}, which the scan imports")
    if type(strat).signal_id() == "" or type(strat).spec_id() == type(strat).signal_id():
        problems.append(f"{key}: signal_id is not distinct from spec_id")
    return problems


def check_signal_version(key: str) -> list[str]:
    """A pinned `signal_version` names a released version no later than the current one (a typo would
    match no cached rows -- harmless -- but a later version would carry rows the code never wrote)."""
    cls = type(get_strategy(key))
    sv = getattr(cls, "signal_version", None)
    if not sv:
        return []
    released = [v for v, *_ in (getattr(cls, "changelog", None) or ())] + [cls.version]
    if sv not in released:
        return [f"{key}: signal_version {sv!r} is not a version in its changelog"]
    num = lambda v: tuple(int(x) for x in v.split("."))
    if num(sv) > num(cls.version):
        return [f"{key}: signal_version {sv} is later than version {cls.version}"]
    return []


def main() -> int:
    problems, checked = [], []
    for key in list_strategies():
        problems += check_signal_version(key)
        strat = get_strategy(key)
        if getattr(strat, "signal_exempt_consts", ()):
            checked.append(f"{key} ({len(strat.signal_exempt_consts)} exempt)")
            problems += check(key)
    if problems:
        print("FAIL — an exempt constant can reach the signal scan:\n")
        for p in problems:
            print(" ", p)
        return 1
    print("OK — no exempt constant is read by the signal scan:", ", ".join(checked) or "none declared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
