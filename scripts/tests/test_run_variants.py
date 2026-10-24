"""A run that changed a strategy's settings never stands in for the strategy.

A `--bt` passthrough (a turnover floor, a rank buffer, an index overlay) moves no fingerprint, so
an experiment shares the spec_id of the real thing, and the Strategies page headlined a $100m-floor
experiment as the US result. The job step now records each run's overrides
(`backtesting/windows.overrides`), ingest stores them, and `web.server.run_variant` marks the run.
This pins the definition, because getting it wrong is silent either way: too loose and experiments
headline again, too strict and every run looks like one and the page empties.

No database.

    PYTHONPATH=. .venv/bin/python -m tests.test_run_variants
"""

import sys

from swing_screener.backtesting import windows as w
from swing_screener.web.server import run_variant

FAILS: list[str] = []
MINERVINI_ARGS = "--spec --market-filter --pe --accept-labels 'TRADE - HIGH CONFIDENCE,TRADE ON TRIGGER'"


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def main() -> int:
    print("what counts as an override")
    check("a plain staged run has none",
          w.overrides({"strategies": ["x"], "stage": "optimise", "start": "2013-01-01"}) == {})
    check("a --bt rule passthrough is one",
          w.overrides({"bt": ["--min-turnover 100000000"]}) == {"bt": ["--min-turnover 100000000"]})
    check("--workers is speed, not a rule", w.overrides({"bt": ["--workers 6"]}) == {})
    check("--workers=6 inside a mixed passthrough is dropped, the rule kept",
          w.overrides({"bt": ["--workers=6 --hold-rank 30"]}) == {"bt": ["--hold-rank 30"]})
    check("a --const is one", w.overrides({"const": ["BREAKEVEN_R=0"]}) == {"const": ["BREAKEVEN_R=0"]})
    check("restating the strategy's own --accept-labels is not one",
          w.overrides({"accept_labels": "TRADE - HIGH CONFIDENCE,TRADE ON TRIGGER"}, MINERVINI_ARGS) == {})
    check("a DIFFERENT --accept-labels is one",
          w.overrides({"accept_labels": "TRADE ON TRIGGER"}, MINERVINI_ARGS) != {})
    check("restating the strategy's own boolean flags is not one",
          w.overrides({"market_filter": True, "pe": True}, MINERVINI_ARGS) == {})
    check("a passthrough that repeats one of its args keeps only the new part",
          w.overrides({"bt": ["--spec --max-base 2"]}, MINERVINI_ARGS) == {"bt": ["--max-base 2"]})
    check("verify's signature ignores speed flags",
          w.signature({"bt": ["--workers 6"]}) == w.signature({}))

    print("what the page treats as a variant")
    cur = "v1.2-006f8206"
    check("recorded overrides make a variant", run_variant(cur, {"bt": ["--hold-rank 30"]}, cur)["variant"])
    check("recorded empty overrides do not", not run_variant(cur, {}, cur)["variant"])
    check("unrecorded, on the current fingerprint, is the strategy", not run_variant(cur, None, cur)["variant"])
    check("unrecorded, current version but another fingerprint, is a variant (a --const outside the queue)",
          run_variant("v1.2-deadbeef", None, cur)["variant"])
    check("an OLDER version is stale, not a variant", not run_variant("v1.1-deadbeef", None, cur)["variant"])
    check("a variant says what it changed",
          run_variant(cur, {"bt": ["--min-turnover 100000000"]}, cur)["overrides"] == ["--min-turnover 100000000"])

    print(f"\n{'OK — experiments are told apart from the strategy as configured.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
