"""Progressive exposure (PE-01…PE-04) and the market filter's bite (MKT-01 / PF-06).

Both change how much is bought and when, from state that accumulates across sessions, so
both can go subtly wrong in the same way: by using information from the session they are
deciding. The checks that matter are therefore as much about WHEN the state is read as
about the arithmetic.

    PYTHONPATH=. .venv/bin/python -m tests.test_exposure_regime
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import Exposure, ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS


def _bars(closes, start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(closes))
    return pd.DataFrame({"open": closes, "high": [c * 1.01 for c in closes],
                         "low": [c * 0.99 for c in closes], "close": closes,
                         "volume": [5_000_000] * len(closes)}, index=idx)


def _sig(date, sym, **meta):
    return Signal(date=date, symbol=sym, setup="MV-01", entry=100.0, stop=90.0, target=130.0,
                  decision="TRADE - HIGH CONFIDENCE", quality=2.0, meta={"order": "open", **meta})


def main() -> int:
    bad = []
    cfg = MARKETS["us"]

    # ---- PE-02 / PE-03: the arithmetic, straight off the rule text
    def st(rs, **kw):
        class T:
            def __init__(self, r): self.r_multiple = r
        return Exposure(enabled=True, **kw).state([T(r) for r in rs])

    cases = [
        ([], 0.5, "warm-up is a pilot"),
        ([1.0] * 4, 0.5, "still inside the warm-up"),
        ([3.0, 2.0, 4.0, 1.0, 2.0, -1.0, -1.0], 0.5, "two losses in a row is a pilot"),
        ([-1.0, -1.0, 0.5, -1.0, 0.2, 1.0], 0.5, "net R not positive is a pilot"),
        ([3.0, -1.0, 2.0, -1.0, 1.0, 2.0], 1.0, "net R positive and no double loss is full size"),
    ]
    for rs, want, why in cases:
        got, _slots, _ = st(rs)
        if got != want:
            bad.append(f"PE: {why} — expected x{want}, got x{got}")

    # PE-04 is off unless asked for, and then adds slots too
    if st([3.0, 2.0, 1.0, -1.0, 2.0, 1.0])[0] != 1.0:
        bad.append("PE-04 must be off unless press_net_r is set")
    mult, slots, _ = st([3.0, 2.0, 1.0, -1.0, 2.0, 1.0], press_net_r=4.0)
    if (mult, slots) != (1.25, 2):
        bad.append(f"PE-04 press gave x{mult} +{slots} slots, expected x1.25 +2")

    # PE-01: only the window counts, so an old disaster outside it stops mattering
    old_loss = [-15.0] + [1.0] * 10   # last 10 are +10R; all 11 are -5R
    if st(old_loss, window=10)[0] != 1.0:
        bad.append("PE-01: a loss older than the window must not hold sizing at pilot")
    if st(old_loss, window=20)[0] != 0.5:
        bad.append("PE-01: a loss inside a wider window must still hold sizing at pilot")

    # ---- the pilot really does buy less, end to end
    rising = [100, 100, 104, 108, 112, 116, 120, 124, 128, 132]
    df = _bars(rising)
    sig = _sig(df.index[0], "T")
    flat = simulate([sig], {"T": df}, cfg, df.index[0], exit_policy=ExitPolicy(mode="bracket", use_target=False))
    pilot = simulate([sig], {"T": df}, cfg, df.index[0], exit_policy=ExitPolicy(mode="bracket", use_target=False),
                     exposure=Exposure(enabled=True, warmup=5))
    if not flat.trades or not pilot.trades:
        print("FAIL — the fixture opened no trade"); return 1
    if not (0 < pilot.trades[0].shares < flat.trades[0].shares):
        bad.append(f"a pilot entry bought {pilot.trades[0].shares}, not fewer than the flat {flat.trades[0].shares}")
    # halving the risk halves the size, so R is unchanged — that is the point of sizing in R
    if abs(pilot.trades[0].r_multiple - flat.trades[0].r_multiple) > 1e-6:
        bad.append("sizing changed the trade's R, which means it changed the trade, not just the size")

    # ---- MKT-01: a resting order must not fill into a risk-off session
    df2 = _bars([100, 100, 104, 108, 112, 116, 120, 124, 128, 132])
    stop_sig = _sig(df2.index[0], "T", order="stop", entry=101.0)
    on = pd.Series(True, index=df2.index)
    off = on.copy(); off.iloc[1:] = False          # risk-off from the session after the signal
    with_on = simulate([stop_sig], {"T": df2}, cfg, df2.index[0], exit_policy=ExitPolicy(mode="bracket", use_target=False), regime_ok=on)
    with_off = simulate([stop_sig], {"T": df2}, cfg, df2.index[0], exit_policy=ExitPolicy(mode="bracket", use_target=False), regime_ok=off)
    if not with_on.trades:
        bad.append("the regime fixture never fills even in risk-on; it proves nothing")
    if with_off.trades:
        bad.append("a resting order filled during risk-off — PF-06 cancels it instead")

    # ---- the filter must never force an exit
    held = simulate([_sig(df2.index[0], "T")], {"T": df2}, cfg, df2.index[0],
                    exit_policy=ExitPolicy(mode="bracket", use_target=False), regime_ok=off)
    if held.trades and held.trades[0].exit_reason == "REGIME":
        bad.append("the market filter closed a position; it gates entries only")

    if bad:
        print("FAIL — exposure / regime:")
        for x in bad:
            print("  " + x)
        return 1
    print(f"OK — PE sizing follows the rule and leaves R untouched; a resting order is "
          f"cancelled in risk-off ({flat.trades[0].shares} shares flat vs {pilot.trades[0].shares} pilot)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
