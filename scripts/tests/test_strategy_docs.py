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
  * an empty section.

It needs no database or market data, so run it after every strategy change:

    PYTHONPATH=. python3 -m tests.test_strategy_docs
"""

import sys

from swing_screener.strategies import docs


def main() -> None:
    problems = docs.check()
    for k in docs.keys():  # every page must also build end to end
        try:
            docs.strategy_doc(k)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"{k}: page fails to build: {exc!r}")
    if problems:
        print(f"FAIL — {len(problems)} documentation problem(s):")
        for p in problems:
            print("  -", p)
        sys.exit(1)
    print(f"OK — {len(docs.keys())} strategies fully documented")


if __name__ == "__main__":
    main()
