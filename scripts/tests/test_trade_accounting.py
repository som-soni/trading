"""Trade rows add up to the equity curve, in the runners that keep their own books.

The equity curve reads cash, so it can be right while every trade row is wrong -- and win rate,
profit factor and average R are computed from the rows. The check that catches that is an
identity: over a run, the trades' P&L must sum to the change in equity. It held in none of the
three runners below (October 2026 review):

  * `baseline.run` and `rotation.simulate` re-weight the book each rebalance, topping a laggard up
    and trimming a winner, but a trade row was built from the FIRST fill alone;
  * `pead.run` let a second filing by the same company on the same session overwrite a live
    position, so its cash was spent twice and the first position vanished from equity.

Also checked: `rotation.simulate` reports holdings per session (it returned the final count
repeated, so exposure read 100% through every risk-off stretch).

Synthetic prices; `baseline.run` reads the stored benchmark (as test_rank_buffer does).

    PYTHONPATH=. .venv/bin/python -m tests.test_trade_accounting
"""

import sys
import warnings

import numpy as np
import pandas as pd

from swing_screener.backtesting import baseline as bl
from swing_screener.backtesting import pead, rotation
from swing_screener.config import MARKETS
from swing_screener.marketdata import cache

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _walk(n: int, idx: pd.DatetimeIndex, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    r = rng.normal(rng.normal(0.0004, 0.0004, n), rng.uniform(0.01, 0.03, n), (len(idx), n))
    return pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                        columns=[f"S{i:03d}" for i in range(n)])


def _adds_up(tdf: pd.DataFrame, eq: pd.Series, start_equity: float, label: str) -> None:
    pnl = float(tdf["pnl"].sum()) if len(tdf) else 0.0
    change = float(eq.iloc[-1]) - start_equity
    tol = 0.01 * max(len(tdf), 1) + 1e-6 * start_equity       # rows are rounded to the cent
    check(f"{label}: trade P&L sums to the change in equity", abs(pnl - change) <= tol,
          f"trades {pnl:,.2f} vs equity {change:,.2f} ({len(tdf)} trades)")


def test_baseline() -> None:
    print("baseline.run (momentum_baseline, momentum_vol_scaled, quality_momentum)")
    idx = pd.bdate_range("2017-01-02", "2022-12-30")
    px = _walk(40, idx, 7)
    pre = (px, px * 1e6, px.rolling(200, min_periods=200).mean())
    for label, kw in (("whole shares, inverse vol", dict(weighting="inverse_vol")),
                      ("fractional, equal weight", dict(fractional=True))):
        with cache.offline():
            tdf, _perf, eq, _pos = bl.run(
                market="us", start="2019-01-01", top_n=8, cost_bps=25.0, min_dollar_volume=1.0,
                liquidity_rank_top=None, min_price=1.0, trend_filter=False, preloaded=pre, **kw)
        _adds_up(tdf, eq, float(MARKETS["us"].account_size), label)
        closed = tdf[tdf["exit_reason"] != "OPEN"]
        check(f"{label}: entry price x shares bought is the notional",
              bool(np.allclose(closed["entry_price"] * closed["shares"], closed["notional"],
                               rtol=1e-3, atol=0.05)))


def test_rotation() -> None:
    print("rotation.simulate (sector_rotation, ma_trend stocks)")
    idx = pd.bdate_range("2018-01-01", "2021-12-31")
    px = _walk(5, idx, 3)
    rebals = rotation.rebalance_dates(px.index, pd.Timestamp("2019-01-01"), "ME")
    off = set(rebals[3::4])          # every fourth month-end: risk-off, hold nothing

    def pick(d, r, _px):
        if d in off:
            return []
        ok = [c for c in r.index if pd.notna(r[c])]
        return sorted(ok, key=lambda c: r[c], reverse=True)[:3]

    tdf, eq, held, _costs = rotation.simulate(px, pick, "2019-01-01", "ME", cost_bps=20.0,
                                              account_size=1_000_000.0, lookback_days=63)
    _adds_up(tdf, eq, 1_000_000.0, "rotation")
    check("held is reported per session", held.index.equals(eq.index), "index differs from equity's")
    check("nothing held before the first rebalance", int(held[held.index < rebals[0]].max()) == 0)
    flat_after = [held.loc[d] for d in off]
    check("nothing held after a risk-off rebalance", all(h == 0 for h in flat_after), str(flat_after))
    check("three held after a risk-on rebalance", int(held.loc[rebals[0]]) == 3, str(held.loc[rebals[0]]))
    exposure = float((held > 0).mean()) * 100
    check("exposure counts the flat stretches", 60 < exposure < 85, f"{exposure:.1f}%")


def test_pead_same_day_filings() -> None:
    print("pead.run")
    cal = pd.bdate_range("2020-01-01", "2020-12-31")
    bench = pd.Series(100.0, index=cal)
    close = pd.Series(50.0, index=cal)
    filed = pd.Timestamp("2020-03-02")
    close[cal >= filed] = 52.0                       # +4% against a flat index: the market agrees
    close[cal >= pd.Timestamp("2020-04-01")] = 55.0
    df = pd.DataFrame({"open": close, "high": close, "low": close * 0.99, "close": close,
                       "volume": 1e6})
    row = dict(symbol="AAA", filed=filed, period_end=pd.Timestamp("2019-12-31"), yoy=60.0,
               season_pct=100.0, accel=10.0, rev_growth=30.0, sue=2.0)
    # one company, two filings on the same day (an amendment): both qualify for the same buy
    ev = pd.DataFrame([row, dict(row, sue=1.0)])
    tdf, eq, held, cash, _c, _d, n = pead.run("us", "2020-01-01", cost_bps=0.0,
                                              preloaded=(ev, {"AAA": df}, bench))
    check("both filings qualified (the case is exercised)", n == 1 and len(ev) == 2, f"{n} entry sessions")
    check("one company is bought once", int(held.max()) == 1 and len(tdf) == 1,
          f"max held {int(held.max())}, {len(tdf)} trades")
    _adds_up(tdf, eq, float(MARKETS["us"].account_size), "pead")


def main() -> int:
    for t in (test_baseline, test_rotation, test_pead_same_day_filings):
        t()
    print(f"\n{'OK — every trade row adds up to the equity it moved.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    sys.exit(main())
