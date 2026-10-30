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

from swing_screener.core import context as ctx_mod
from swing_screener.marketdata import cache
from swing_screener.strategies import get_strategy

from tests.minervini_book_cases import BUY, CASES


def _frames(sym: str, frames: dict):
    if sym not in frames:
        raw = cache.load_cached("us", sym)
        if raw is None or raw.empty:
            frames[sym] = None
        else:
            raw.columns = [c.lower() for c in raw.columns]
            frames[sym] = (raw, ctx_mod.prepare_frames(raw))
    return frames[sym]


def _window(strategy, case: dict, frames: dict):
    """Every session of the case's window: [(date, setups, first_hard_fail, vcp_fail)], or None (no data)."""
    fr = _frames(case["symbol"], frames)
    if fr is None:
        return None
    raw, f = fr
    lo, hi = case["window"]
    days = f.daily.loc[lo:hi].index
    if len(days) == 0:                                       # the window sits outside the stored history
        return None
    out = []
    for day in days:
        ctx = ctx_mod.build_context(case["symbol"], raw, earnings_days_away=None, frames=f, as_of=day)
        if ctx is None:
            out.append((day, [], "history", None))
            continue
        r = strategy.evaluate(ctx)
        out.append((day, r.active_setups, r.first_hard_fail, ctx.extras.get("vcp_fail")))
    return out


def _why(rows) -> str:
    """The commonest refusal over a window: the gate, and the detector's rule when it rejected the base."""
    c = Counter(f"{g or '-'}/{v or '-'}" for _, s, g, v in rows)
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
        hits = [(d, [s for s in got if s in want]) for d, got, _, _ in rows if any(s in want for s in got)]
        if kind == "buy":
            ok = bool(hits)
            tag = "ok  " if ok else ("FAIL" if case.get("pinned") else "miss")
            score["buy caught" if ok else "buy missed"] += 1
            detail = (f"{hits[0][0].date()} {','.join(hits[0][1])}" if ok else _why(rows))
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
    print(f"\nbuy points caught {score['buy caught']} of {b}; setups to avoid held {score['no_buy held']} of {n}; "
          f"{score['no data']} without stored prices; {score['sell']} climax tops not scored yet")
    if newly:
        print(f"caught but not pinned: {', '.join(newly)}")
    if failures:
        print(f"FAILED (pinned): {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
