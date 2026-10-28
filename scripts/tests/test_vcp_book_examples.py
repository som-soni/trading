"""Minervini's own VCP examples, pinned on stored prices.

*Trade Like a Stock Market Wizard*, chapter 10, shows each setup on a real chart with the date he
bought. These cases check that the `minervini` strategy gives the same signal on that date: the
buy itself (S1, a close through the pivot) or the coil before it (S2, a buy-stop waiting above the
pivot). A detector that catches none of the book's own examples is not a VCP detector, whatever
its rules say; 1.27 caught 1 of them.

KNOWN_MISSES lists examples the current rules do not catch, and why. They are printed, not
asserted, so a change that catches one shows up as an improvement rather than as a failure. Move a
case into CASES once it is caught on purpose.

Skipped (not failed) for a symbol with no stored prices.

Run: `PYTHONPATH=. .venv/bin/python -m tests.test_vcp_book_examples`
"""

import sys
import warnings

from swing_screener.core import context as ctx_mod
from swing_screener.marketdata import cache
from swing_screener.strategies import get_strategy

# (symbol, session, setup the strategy must give, what the book shows)
CASES = [
    ("NFLX", "2009-10-15", "S1", "Fig 10.31: out of a 27-week base, footprint 27W 27/7 3T"),
    ("LULU", "2010-11-05", "S1", "Fig 10.40: bought as it emerged from a double bottom"),
    ("CRUS", "2010-03-29", "S2", "Fig 10.34: coiled the day before the 30 Mar 2010 buy at $8.09"),
    ("BBY", "1997-12-01", "S1", "Fig 10.62: lowest volume the day before the breakout"),
    ("SYK", "1995-01-05", "S1", "Fig 10.44: bought as it emerged from a VCP in January 1995"),
]

# (symbol, around, what the book shows, why the rules miss it)
KNOWN_MISSES = [
    ("MGA", "2011-01-03", "Fig 10.15: the 'correct buy point' after a compressed right side",
     "VCP-06: the final contraction is 0.71x the one before (3.9% after 5.5%), over the 0.6 limit"),
    ("AMSC", "2003-12-29", "Fig 10.29: a classic VCP, up 60% in 17 days",
     "the right side rallied 71% of the way back up the base before its handle, under the 75% that "
     "starts a new contraction (t_recovery); counted, the handle is 15% deep, over VCP-08's 10%"),
    ("AXON", "2004-01-09", "Fig 10.60: TASR's power play (the ticker is now AXON)",
     "MV-05 is detected, but the breakout closed 5.6% above the pivot, over BUY_RANGE_PCT; he buys "
     "intraday as it crosses the pivot"),
    ("MELI", "2007-12-03", "Fig 10.28 / 10.55: a base reset after the IPO",
     "G2/G3: under 200 sessions listed, so no 150- or 200-day average yet"),
    ("EDU", "2007-04-16", "Fig 10.32: footprint 8W 22/2 3T", "G2/G3: under 200 sessions listed"),
    ("DKS", "2003-04-01", "Fig 10.64: a technical buy point after positive guidance",
     "G2: under 200 sessions listed"),
]


def _setups(strategy, sym: str, day: str, frames: dict) -> tuple[list, str | None]:
    if sym not in frames:
        raw = cache.load_cached("us", sym)
        if raw is None or raw.empty:
            frames[sym] = None
        else:
            raw.columns = [c.lower() for c in raw.columns]
            frames[sym] = (raw, ctx_mod.prepare_frames(raw))
    if frames[sym] is None:
        return None, None
    raw, fr = frames[sym]
    as_of = fr.daily.loc[:day].index[-1]
    ctx = ctx_mod.build_context(sym, raw, earnings_days_away=None, frames=fr, as_of=as_of)
    if ctx is None:
        return [], "not enough history"
    r = strategy.evaluate(ctx)
    return r.active_setups, r.first_hard_fail


def main() -> None:
    warnings.filterwarnings("ignore")
    st = get_strategy("minervini")
    frames: dict = {}
    failures, ran = [], 0
    for sym, day, want, what in CASES:
        got, gate = _setups(st, sym, day, frames)
        if got is None:
            print(f"skip  {sym} {day} — no stored prices")
            continue
        ran += 1
        ok = want in got
        print(f"{'ok  ' if ok else 'FAIL'}  {sym} {day} {want} — {what}"
              + ("" if ok else f"   (got {got or 'nothing'}{f', gate {gate}' if gate else ''})"))
        if not ok:
            failures.append(sym)
    caught = 0
    for sym, day, what, why in KNOWN_MISSES:
        got, _ = _setups(st, sym, day, frames)
        if got:
            caught += 1
            print(f"NEW   {sym} {day} now gives {got} — {what}; move it to CASES")
        else:
            print(f"miss  {sym} {day} — {why}")
    total = ran + len(KNOWN_MISSES)
    print(f"\n{ran - len(failures)} of {total} book examples caught"
          + (f", {caught} known miss(es) now caught" if caught else ""))
    if failures:
        print(f"FAILED: {', '.join(failures)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
