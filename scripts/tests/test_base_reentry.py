"""EN-04: a base may be bought again after a SHAKEOUT, and only then.

A base used to be barred for good after one entry, which also barred the re-entry a shakeout
invites. That matters because the exit ladder manufactures shakeouts: EX-03 moves the stop to
breakeven at +2R, so an ordinary pullback ends the trade at zero -- and ended the base with it.

`max_entries_per_base` (meta, default 1) says how many attempts a strategy allows, and
`RE_ENTRY_AFTER` says which endings reopen a base: a stop or a breakeven stop, never a trend
exit, which says the move itself is over.

Synthetic bars, no database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_base_reentry
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS

FAILS: list[str] = []
IDX = pd.bdate_range("2021-01-04", periods=24)


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _prices() -> pd.DataFrame:
    """Flat at 100, a dip to 92 on day 6 that takes out a 95 stop, flat at 100 again."""
    close = [100.0] * len(IDX)
    low = [99.0] * len(IDX)
    close[6], low[6] = 93.0, 92.0
    return pd.DataFrame({"open": close, "high": [c * 1.005 for c in close],
                         "low": low, "close": close, "volume": [5e6] * len(IDX)}, index=IDX)


def _signal(day: int, base_id: str, cap: int) -> Signal:
    return Signal(date=IDX[day], symbol="TEST", setup="S4", entry=100.0, stop=95.0, target=130.0,
                  decision="TRADE - HIGH CONFIDENCE",
                  meta={"order": "open", "base_id": base_id, "max_entries_per_base": cap})


def _won() -> pd.DataFrame:
    """Flat at 100, then through the 130 target on day 6 -- a finished move, not a shakeout."""
    close = [100.0] * len(IDX)
    close[6] = 135.0
    return pd.DataFrame({"open": close, "high": [c * 1.005 for c in close],
                         "low": [c * 0.99 for c in close], "close": close,
                         "volume": [5e6] * len(IDX)}, index=IDX)


def _run(cap: int, same_base: bool = True, frame=None):
    sigs = [_signal(0, "BASE-A", cap), _signal(12, "BASE-A" if same_base else "BASE-B", cap)]
    return simulate(sigs, {"TEST": frame if frame is not None else _prices()}, MARKETS["us"],
                    start=IDX[0], end=IDX[-1], max_positions=5,
                    exit_policy=ExitPolicy(mode="bracket"))


def main() -> int:
    print("a base reopens after a shakeout, and only up to its limit")

    one = _run(cap=1)
    check("with the shipped limit of 1, the base is bought once", len(one.trades) == 1,
          f"{len(one.trades)} trades")
    if one.trades:
        check("...and that one trade was stopped out", one.trades[0].exit_reason == "STOP",
              one.trades[0].exit_reason)

    two = _run(cap=2)
    check("with a limit of 2, the shaken-out base is bought again", len(two.trades) == 2,
          f"{len(two.trades)} trades")

    three = _run(cap=3)
    check("a limit of 3 does not invent a third signal", len(three.trades) == 2,
          f"{len(three.trades)} trades")

    # the discriminating case: a base whose trade FINISHED does not reopen, limit or no limit
    won = _run(cap=2, frame=_won())
    check("a base that hit its target is NOT bought again, even with a limit of 2",
          len(won.trades) == 1, f"{len(won.trades)} trades, exits={[t.exit_reason for t in won.trades]}")
    if won.trades:
        check("...and that exit really was a finish, not a shakeout",
              won.trades[0].exit_reason not in ("STOP", "BREAKEVEN_STOP"), won.trades[0].exit_reason)

    other = _run(cap=1, same_base=False)
    check("a DIFFERENT base is never blocked by the first", len(other.trades) == 2,
          f"{len(other.trades)} trades")

    print(f"\n{'OK — EN-04 reopens a base only after a shakeout.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
