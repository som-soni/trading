"""Every strategy must stay fully documented.

The web app's Strategy page is generated from each strategy's own class
attributes (thesis, how_it_works, caveats, status, gate_docs, watch_docs,
setup_docs, entry_rules, exit_rules, param_docs) and from
`backtesting.baseline.DOC`. This test fails when that documentation falls out
of step with the code:

  * a gate / watch flag / setup code with no description (new rule added,
    docs not updated);
  * a description for a code that no longer exists (rule removed or renamed);
  * a `{NAME}` placeholder naming a constant that was renamed or deleted;
  * a parameter row pointing at a constant or config field that is gone;
  * an empty section;
  * a status that quotes a % or R figure without naming the stage it comes from (optimise /
    in-sample, verify / out-of-sample, full, or legacy): an in-sample number reads exactly like a
    verified one.

It needs no database or market data, so run it after every strategy change:

    PYTHONPATH=. python3 -m tests.test_strategy_docs
"""

import re
import sys

from swing_screener.strategies import docs

FIGURE = re.compile(r"[-+]?\d+(?:\.\d+)?\s*%|[-+]?\d+(?:\.\d+)?R\b")
STAGE_WORD = re.compile(r"optimi[sz]e|verify|verified|in-sample|out-of-sample|legacy|full stage|full period",
                        re.IGNORECASE)


def unstaged_status(key: str, status: str) -> list[str]:
    """A status that quotes a % or R figure must name a stage somewhere in it (CLAUDE.md: name the stage
    every figure comes from)."""
    fig = FIGURE.search(status or "")
    if fig and not STAGE_WORD.search(status):
        return [f"{key}: status quotes {fig.group(0).strip()!r} but names no stage (optimise / in-sample, "
                f"verify / out-of-sample, full, legacy)"]
    return []


def main() -> None:
    problems = docs.check()
    for k in docs.keys():  # every page must also build end to end
        try:
            problems += unstaged_status(k, docs.strategy_doc(k).get("status") or "")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{k}: page fails to build: {exc!r}")
    # the check itself: a figure with no stage fails, the same figure with one passes
    assert unstaged_status("t", "returned 1.75% CAGR") and not unstaged_status("t", "optimise stage: 1.75% CAGR")
    if problems:
        print(f"FAIL — {len(problems)} documentation problem(s):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"OK — {len(docs.keys())} strategies fully documented")


if __name__ == "__main__":
    main()
