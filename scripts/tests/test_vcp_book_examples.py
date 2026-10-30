"""Minervini's own chart examples, scored against the `minervini` strategy.

The cases live in `tests/minervini_book_cases.py` (the permanent eval set: figure, symbol, dates,
what the book shows). For each case the strategy's `evaluate` runs on every session in the case's
window, on stored prices, each session seeing only itself and earlier bars:

- a "buy" case is caught when some session gives one of its setups (S1 breakout, S3/S4 cheat,
  S5 power play, S6 flat base; S2, the coil, only where a case asks for it);
- a "no_buy" case passes when no session gives a buy setup;
- a "sell" case (climax tops, for the exit rules) is listed, not scored yet.

This checks the detector and the gates, not the liquidity floor applied before them: several book
examples traded under MIN_TURNOVER_USD_M in their own year's dollars, so a backtest would not have
seen them.

Pinned cases are asserted (a miss fails the run); the rest are scored and printed, so a change that
catches one shows as an improvement. A case whose symbol has no stored prices is listed as "no data".

Run: `PYTHONPATH=. .venv/bin/python -m tests.test_vcp_book_examples` (add `-v` for each case's reason,
`--only ID_SUBSTRING` to run some).
"""

import sys
import warnings
from collections import Counter

from swing_screener.backtesting.breakout_eval import buys_over
from swing_screener.strategies import get_strategy

from tests.minervini_book_cases import BUY, CASES


def _window(strategy, case: dict, frames: dict):
    """Every session of the case's window (`buys_over`), or None (no stored prices there)."""
    return buys_over(strategy, case["symbol"], case["window"][0], case["window"][1], frames)


def _why(rows) -> str:
    """The commonest refusal over a window: the gate, and the detector's rule when it rejected the base."""
    c = Counter(f"{g or '-'}/{v or '-'}" for _, s, g, v, _ in rows)
    return ", ".join(f"{k} ×{n}" for k, n in c.most_common(2))


def main() -> None:
    warnings.filterwarnings("ignore")
    verbose = "-v" in sys.argv
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    st = get_strategy("minervini")
    frames: dict = {}
    score = Counter()
    failures, newly = [], []
    for case in CASES:
        if only and only not in case["id"]:
            continue
        kind, cid = case["kind"], case["id"]
        head = f"{cid:<26} {case['symbol']:<5} {case['window'][0]}"
        if kind == "sell":
            score["sell"] += 1
            if verbose:
                print(f"sell  {head} — {case['note']} (exit rules; not scored yet)")
            continue
        rows = _window(st, case, frames)
        if rows is None:
            score["no data"] += 1
            print(f"----  {head} — no stored prices for this window")
            continue
        want = case.get("setups", BUY)
        hits = [(d, [s for s in got if s in want], t) for d, got, _, _, t in rows if any(s in want for s in got)]
        if kind == "buy":
            ok = bool(hits)
            traded = any(t for *_, t in hits) or "S2" in want      # a coil is a resting order, not judged here
            tag = ("ok  " if traded else "plan") if ok else ("FAIL" if case.get("pinned") else "miss")
            score["buy caught" if ok else "buy missed"] += 1
            score["buy traded"] += bool(ok and traded)
            detail = (f"{hits[0][0].date()} {','.join(hits[0][1])}"
                      + ("" if traded else " (setup only: the plan's risk or R refuses it)") if ok else _why(rows))
            if ok and not case.get("pinned"):
                newly.append(cid)
        else:                                                # no_buy
            ok = not hits
            tag = "ok  " if ok else ("FAIL" if case.get("pinned") else "BUY ")
            score["no_buy held" if ok else "no_buy bought"] += 1
            detail = "no buy" if ok else f"bought {hits[0][0].date()} {','.join(hits[0][1])}"
        if not ok and case.get("pinned"):
            failures.append(cid)
        print(f"{tag}  {head} — {detail}")
        if verbose:
            print(f"      {case['note']}" + (f"\n      known: {case['why']}" if case.get("why") else ""))
    b = score["buy caught"] + score["buy missed"]
    n = score["no_buy held"] + score["no_buy bought"]
    print(f"\nbuy points caught {score['buy caught']} of {b} ({score['buy traded']} the plan would trade); "
          f"setups to avoid held {score['no_buy held']} of {n}; "
          f"{score['no data']} without stored prices; {score['sell']} climax tops not scored yet")
    if newly:
        print(f"caught but not pinned: {', '.join(newly)}")
    if failures:
        print(f"FAILED (pinned): {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
