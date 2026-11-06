"""The open-position tracker manages a live position exactly as the backtest would.

`tracker.track` replays a position's bars through `portfolio_sim.manage_entry_bar` / `manage_exit` --
the functions `simulate` itself calls -- so a position tracked live cannot be managed by a different
rule from the one the strategy was measured with. This checks it on the same bars: for each exit mode,
many single-signal portfolios are simulated, and every trade `simulate` makes is tracked from its fill.
A closed trade must exit on the same session, for the same reason, at the same price; one still open at
the end must carry the same stop. The status a live reader sees is checked on hand-made bars.

Synthetic bars, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_position_tracker
"""

import math
import sys
import warnings

import numpy as np
import pandas as pd

from swing_screener.backtesting import portfolio_sim as ps
from swing_screener.backtesting import tracker
from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind

warnings.filterwarnings("ignore")
FAILS: list[str] = []
CFG = MARKETS["india"]


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def bars(seed: int, n: int = 700) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-01", periods=n)
    c = 100 * np.exp(np.cumsum(rng.normal(0.0008, 0.02, n)))
    o = c * np.exp(rng.normal(0, 0.006, n))
    hi = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 0.01, n)))
    lo = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 0.01, n)))
    vol = rng.integers(50_000, 500_000, n).astype(float)
    return ind.enrich_daily(pd.DataFrame({"open": o, "high": hi, "low": lo, "close": c, "volume": vol}, index=idx))


POLICIES = [
    ps.ExitPolicy(mode="bracket"),
    ps.ExitPolicy(mode="bracket", use_target=False, be_r=1.5, time_stop_bars=30, partial_at_target=0.5),
    ps.ExitPolicy(mode="trail_atr", use_target=False),
    ps.ExitPolicy(mode="trail_pct", use_target=False),
    ps.ExitPolicy(mode="ma", use_target=False, ma_col="sma50"),
    ps.ExitPolicy(mode="weekly_ma", use_target=False),
    ps.ExitPolicy(mode="donchian", use_target=False),
    ps.ExitPolicy(mode="supertrend", use_target=False),
    ps.ExitPolicy(mode="kullamagi", use_target=False),
    ps.ExitPolicy(mode="darvas", use_target=False),
    ps.ExitPolicy(mode="minervini", use_target=False),
]


def test_matches_simulate() -> None:
    print("the tracker's exit is simulate's, on the same bars")
    for policy in POLICIES:
        n_closed = n_open = bad = 0
        for seed in range(12):
            df = bars(seed)
            for k, d in enumerate(df.index[260:640:40]):
                c = float(df.loc[d, "close"])
                meta = {"pivot": c * 1.01} if policy.mode == "minervini" else {}
                sig = ps.Signal(date=d, symbol="X", setup="S1", entry=c * 1.01, stop=c * 0.93, target=c * 1.3,
                                decision="TRADE", meta=meta)
                end = df.index[min(len(df) - 1, df.index.get_loc(d) + 90 + 7 * k)]
                res = ps.simulate([sig], {"X": df}, CFG, df.index[0], end=end, exit_policy=policy,
                                  slippage_bps=0.0, cost_bps=0.0)
                for t in res.trades:
                    r = tracker.track(df.loc[:end], policy, CFG, symbol="X", entry_date=t.entry_date,
                                      entry_price=t.entry_price, initial_stop=t.initial_stop, shares=t.shares,
                                      target=t.target, meta=meta, fee_rate=0.0)
                    if t.exit_reason == "OPEN":
                        n_open += 1
                        same = r["exit"] is None or (r["status"] == "exit_next_open" and r["exit"]["date"] is None)
                        same = same and math.isclose(r["stop"] or 0, t.stop, rel_tol=1e-9)
                    else:
                        n_closed += 1
                        ex = r["exit"] or {}
                        same = (ex.get("date") == str(t.exit_date.date()) and ex.get("reason") == t.exit_reason
                                and (t.partial_shares or math.isclose(ex.get("price") or 0, t.exit_price, rel_tol=1e-9)))
                    if not same:
                        bad += 1
                        if bad <= 2:
                            print(f"      {policy.label()} seed {seed} {t.entry_date.date()}: sim {t.exit_reason} "
                                  f"{t.exit_date.date() if t.exit_date is not None else ''} stop {t.stop:.4f} / "
                                  f"tracker {r['status']} {r['exit']} stop {r['stop']}")
        check(f"{policy.label()}: {n_closed} exits and {n_open} open stops agree", bad == 0 and n_closed + n_open > 20,
              f"{bad} differ")


def test_status() -> None:
    print("the status a reader sees")
    idx = pd.bdate_range("2024-01-01", periods=80)
    up = np.linspace(100, 140, 80)
    df = ind.enrich_daily(pd.DataFrame({"open": up, "high": up * 1.01, "low": up * 0.99, "close": up,
                                        "volume": 1e5}, index=idx))
    trail = ps.ExitPolicy(mode="trail_pct", use_target=False, trail_pct=0.05)
    r = tracker.track(df, trail, CFG, symbol="X", entry_date=idx[10], entry_price=up[10], initial_stop=up[10] * 0.9,
                      shares=10)
    check("a rising trail on the last session reads 'stop_raised'", r["status"] == "stop_raised", r["status"])
    check("the stop sits the trail below the highest high", math.isclose(r["stop"], up[-1] * 1.01 * 0.95), str(r["stop"]))
    check("R so far is from the initial stop", math.isclose(r["r_now"], (up[-1] - up[10]) / (up[10] * 0.1)), str(r["r_now"]))
    flat = ps.ExitPolicy(mode="bracket", use_target=False)
    r = tracker.track(df, flat, CFG, symbol="X", entry_date=idx[10], entry_price=up[10], initial_stop=up[10] * 0.9,
                      shares=10)
    check("a fixed stop that is not reached reads 'hold'", r["status"] == "hold" and r["stop"] == up[10] * 0.9, r["status"])
    down = df.copy()
    down.loc[idx[-1], ["open", "high", "low", "close"]] = [down["close"].iloc[-2], down["close"].iloc[-2],
                                                           down["sma20"].iloc[-1] * 0.95, down["sma20"].iloc[-1] * 0.96]
    ma = ps.ExitPolicy(mode="ma", use_target=False, ma_col="sma20")
    r = tracker.track(down, ma, CFG, symbol="X", entry_date=idx[30], entry_price=up[30], initial_stop=up[30] * 0.8,
                      shares=10)
    check("a close below the average reads 'exit_next_open'", r["status"] == "exit_next_open"
          and r["exit"]["reason"] == "TREND_EXIT", f"{r['status']} {r['exit']}")
    r = tracker.track(down, flat, CFG, symbol="X", entry_date=idx[30], entry_price=up[30],
                      initial_stop=float(down["low"].iloc[-1]) + 1, shares=10)
    check("an intraday stop reads 'stopped'", r["status"] == "stopped" and r["exit"]["reason"] == "STOP",
          f"{r['status']} {r['exit']}")


def main() -> int:
    test_matches_simulate()
    test_status()
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'the tracker manages a position as simulate does'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
