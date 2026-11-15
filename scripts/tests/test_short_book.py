"""The generic short book (backtesting/short_book.py) and the failed-breakout signal, on synthetic bars.

Checked: a short gains when the price falls and covers at its target; a gap up through the stop covers at
the open, not the stop; the time limit covers at that close; carry and costs come out of P&L; R is P&L over
the risk to the stop; and the failed-breakout signal fires on the first red close back under the pivot,
with the failed high as its stop, and never on a breakout that held.

    PYTHONPATH=. .venv/bin/python -m tests.test_short_book
"""

import sys

import pandas as pd

from swing_screener.backtesting import failed_breakout_short as fbs
from swing_screener.backtesting.short_book import ShortRules, simulate

FAILS: list[str] = []


def check(what, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def bars(rows, start="2020-01-01"):
    idx = pd.bdate_range(start, periods=len(rows))
    return pd.DataFrame(rows, index=idx, columns=["open", "high", "low", "close", "volume"]).astype(float)


def book(f, signal_day, stop, target=None, time_stop=10, cost=0.0, carry=0.0):
    rules = ShortRules(risk_pct=1.0, max_position_pct=100, max_open_risk_pct=100, cost_bps=cost,
                       borrow_pct=carry, dividend_pct=0.0, time_stop=time_stop)
    sig = {f.index[signal_day]: [{"symbol": "X", "stop": stop, "target": target, "setup": "T"}]}
    return simulate("us", str(f.index[0].date()), sig, {"X": f}, f.index, rules)


def simulator():
    print("short book")
    # sell 100 at the close of day 0; day 2 trades down to the 90 target
    f = bars([(100, 101, 99, 100, 1e6), (99, 100, 95, 96, 1e6), (95, 96, 88, 89, 1e6), (89, 90, 88, 89, 1e6)])
    t = book(f, 0, stop=105, target=90)[0].iloc[0]
    check("covers at the target when the low reaches it", t["exit_reason"] == "TARGET" and t["exit_price"] == 90,
          t.to_dict())
    check("P&L and R of a winning short", abs(t["pnl"] - t["shares"] * 10) < 1e-6 and abs(t["r_multiple"] - 2) < 1e-6,
          t.to_dict())
    # a gap up through the stop fills at the open
    f = bars([(100, 101, 99, 100, 1e6), (108, 110, 107, 109, 1e6), (109, 110, 108, 109, 1e6)])
    t = book(f, 0, stop=105)[0].iloc[0]
    check("a gap above the stop covers at the open", t["exit_reason"] == "STOP" and t["exit_price"] == 108, t.to_dict())
    check("a gap loss is worse than -1R", t["r_multiple"] < -1, t["r_multiple"])
    # the time limit
    f = bars([(100, 101, 99, 100, 1e6)] + [(100, 101, 99, 99, 1e6)] * 5)
    t = book(f, 0, stop=105, time_stop=3)[0].iloc[0]
    check("covers at the close of the time-limit session", t["exit_reason"] == "TIME" and t["sessions"] == 3,
          t.to_dict())
    # costs and carry reduce P&L
    gross = book(f, 0, stop=105, time_stop=3)[0].iloc[0]["pnl"]
    net = book(f, 0, stop=105, time_stop=3, cost=10, carry=50)[0].iloc[0]
    check("costs and borrow come out of P&L", net["pnl"] < gross and net["costs"] > 0 and net["carry"] > 0,
          (gross, net.to_dict()))


def signal():
    print("failed-breakout signal")
    base = [(100, 104, 96, 100, 1e6)] * (fbs.BASE_BARS + 2)      # a flat base: pivot 104
    brk = [(103, 107, 102, 106, 1e6)]                             # day B closes above the pivot
    fail = [(105, 106, 101, 102, 1e6)]                            # next day: red, back under 104
    f = fbs.symbol_frame(bars(base + brk + fail))
    last = f.iloc[-1]
    check("fires on the first red close back under the pivot", bool(last["sig"]), last.to_dict())
    check("its stop is the failed high", last["stop"] == 107 and last["pivot"] == 104, last.to_dict())
    held = fbs.symbol_frame(bars(base + brk + [(106, 108, 105, 107, 1e6)]))
    check("no signal when the breakout holds", not held["sig"].any())
    green = fbs.symbol_frame(bars(base + brk + [(101, 103, 100, 102.5, 1e6)]))
    check("no signal on a green candle back under", not bool(green["sig"].iloc[-1]))


def main() -> int:
    simulator()
    signal()
    print(f"\n{'FAIL' if FAILS else 'OK'} — {len(FAILS)} failure(s)" if FAILS else "\nOK — the short book adds up")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
