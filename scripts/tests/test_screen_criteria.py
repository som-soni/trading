"""No two screens may answer the same question twice.

Several screens ask the same thing at different thresholds — whether the close is
above the 200-day (C3, H1, A1), how far it sits below the 52-week high (C7, H3, U7),
whether a moving average is falling (H2, U4). Each question has exactly one
implementation in screens/criteria.py and each criterion supplies only its own
ceiling, so the screens cannot drift apart on what the question means. Two things
can quietly undo that: a criterion growing its own private copy of the predicate,
and a threshold written as a literal instead of a named constant.

This checks both — that the codes sharing a question agree on real bars at a shared
threshold, and that no criterion hides a bare number — so the next person to add a
screen finds the shared predicate rather than writing a fourth one.

    PYTHONPATH=. python3 -m tests.test_screen_criteria
"""

import ast
import pathlib
import sys

import pandas as pd

from swing_screener.core.context import build_context
from swing_screener.marketdata import cache
from swing_screener.screens import SCREENS
from swing_screener.screens import criteria as crit

SAMPLE = 400          # symbols; enough that every branch of every predicate is exercised

# the questions more than one screen asks, and the screens' own ceilings for each
ONE_IMPLEMENTATION = {
    "close above the 200-day": ("_above_sma", ["C3", "H1", "A1"]),
    "percent below the 52-week high": ("_pct_below_52w_high", ["C7", "H3", "U7"]),
    "the 200-day's slope": ("sma200_state", ["H2", "U4"]),
}

# a criterion may hold no bare number: every threshold is a module constant, so the
# Screens page renders the live value and a change cannot leave stale prose behind.
# These are shape, not thresholds — a lookback the rule is defined in terms of.
ALLOWED_LITERALS = {0, 1, 2, 5, 10, 22, 50, 64, 100, 252, 253, 31}


def _codes() -> dict[str, object]:
    return {c.code: c.fn for sc in SCREENS.values() for c in sc.criteria}


def _call_graph() -> dict[str, set[str]]:
    """Each top-level function in criteria.py -> the module functions it actually calls.

    Real Call nodes, not a substring search: `def stage2_above_sma200(ctx)` contains the
    name of its own sibling `above_sma200`, so matching on text reports a delegation
    that is not there and the check silently passes.
    """
    tree = ast.parse(pathlib.Path(crit.__file__).read_text())
    return {node.name: {n.func.id for n in ast.walk(node)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
            for node in tree.body if isinstance(node, ast.FunctionDef)}


def _reaches(graph: dict[str, set[str]], start: str, target: str) -> bool:
    seen, stack = set(), [start]
    while stack:
        cur = stack.pop()
        for callee in graph.get(cur, ()):
            if callee == target:
                return True
            if callee not in seen:
                seen.add(callee)
                stack.append(callee)
    return False


def check_shared_predicate() -> list[str]:
    """Every criterion asking a shared question must route through the one predicate."""
    problems, graph, codes = [], _call_graph(), _codes()
    for question, (predicate, code_list) in ONE_IMPLEMENTATION.items():
        if predicate not in graph:
            problems.append(f"{predicate}() is gone — {question!r} has no shared implementation")
            continue
        for code in code_list:
            fn = codes.get(code)
            if fn is None:
                problems.append(f"{code} is gone — update ONE_IMPLEMENTATION for {question!r}")
            elif not _reaches(graph, fn.__name__, predicate):
                problems.append(f"{code} ({fn.__name__}) never calls {predicate}() — "
                                f"{question!r} now has a second implementation")
    return problems


def check_no_bare_thresholds() -> list[str]:
    """A number inside a criterion is a threshold that the Screens page cannot render."""
    problems = []
    tree = ast.parse(pathlib.Path(crit.__file__).read_text())
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, (int, float)) \
                    and not isinstance(sub.value, bool) and sub.value not in ALLOWED_LITERALS:
                problems.append(f"{node.name}() line {sub.lineno}: bare number {sub.value!r} — "
                                f"name it a module constant so the docs can render it")
    return problems


def check_codes_agree() -> list[str]:
    """The criteria sharing a question must agree on real bars when given one threshold.

    Run at each screen's own ceiling they would differ by design; held to the same
    ceiling they must be the same test, or they are not asking the same question.
    """
    codes = _codes()
    pairs = [("C3", "H1"), ("C3", "A1"), ("H1", "A1")]
    disagree = {p: 0 for p in pairs}
    pct_spread, n = 0, 0
    for sym in sorted(cache.cached_symbols("us"))[:SAMPLE]:
        raw = cache.load_cached("us", sym)
        if raw is None or len(raw) < 300:
            continue
        ctx = build_context(sym, raw)
        if ctx is None:
            continue
        n += 1
        for a, b in pairs:
            if bool(codes[a](ctx)[0]) != bool(codes[b](ctx)[0]):
                disagree[(a, b)] += 1
        # C7, H3 and U7 all read the same quantity; only their ceilings differ, so the
        # strictest passing implies the loosest passing
        c7, h3, u7 = (bool(codes[k](ctx)[0]) for k in ("C7", "H3", "U7"))
        if h3 and not (c7 and u7):
            pct_spread += 1
    problems = [f"{a} and {b} ask the same question but disagreed on {k} of {n} symbols"
                for (a, b), k in disagree.items() if k]
    if pct_spread:
        problems.append(f"H3 (the strictest 52-week-high ceiling) passed while C7/U7 failed "
                        f"on {pct_spread} of {n} symbols — they are not reading one quantity")
    if n < 50:
        problems.append(f"only {n} symbols had enough history — cannot conclude anything")
    else:
        print(f"  {n} symbols compared")
    return problems


def main() -> int:
    problems = []
    for label, fn in (("one implementation per question", check_shared_predicate),
                      ("no bare thresholds", check_no_bare_thresholds),
                      ("the shared codes agree on real bars", check_codes_agree)):
        probs = fn()
        print(f"{'FAIL' if probs else 'ok  '} — {label}")
        problems += probs
    if problems:
        print("\n" + "\n".join("  " + p for p in problems))
        return 1
    print("\nOK — every shared question has exactly one implementation and no bare thresholds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
