"""Special dividends and demergers credited to a holder; real collapses left as losses.

Reads the stored `corporate_actions` and `prices` (run the corporate_actions job first) for the cases that
found the problem, then checks the runners' crediting on hand-made bars.

    PYTHONPATH=. python3 -m tests.test_corporate_actions
"""

import dataclasses

import pandas as pd

from swing_screener.backtesting import rotation
from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal, simulate
from swing_screener.config import MARKETS
from swing_screener.marketdata import asof, corporate_actions as ca, db

CFG = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0, risk_pct=0.01,
                          max_position_pct=1.0, account_size=1_000_000)


def _credit(df, symbol, day):
    hit = df[(df["symbol"] == symbol) & (df["date"] == pd.Timestamp(day))]
    return hit.iloc[0] if len(hit) else None


def test_aurum_special_dividend_is_credited():
    # 717.20 -> 8.88 on 2020-12-23: a dividend of nearly the whole price, not a loss
    c = _credit(ca.credits("india", ["AURUM.NS"]), "AURUM.NS", "2020-12-23")
    assert c is not None, "AURUM.NS 2020-12-23 not credited"
    assert c["kind"] == "special_dividend" and 700 < c["cash"] < 715 and c["pct"] > 0.95, dict(c)


def test_yesbank_collapse_is_not_credited():
    # 36.80 -> 16.15 on 2020-03-06: the moratorium, a real loss
    cr = ca.credits("india", ["YESBANK.NS"])
    assert _credit(cr, "YESBANK.NS", "2020-03-06") is None, cr.tail()
    assert not len(cr[(cr["date"] >= "2020-02-01") & (cr["date"] <= "2020-04-30")]), cr.tail()
    with db.get_connection().cursor() as cur:   # and the bar itself is untouched by any correction
        cur.execute("SELECT close FROM prices WHERE market='india' AND symbol='YESBANK.NS' AND date='2020-03-06'")
        assert abs(cur.fetchone()[0] - 16.15) < 0.01


def test_demergers_are_credited_at_the_open_gap():
    cr = ca.credits("india", ["MASTEK.NS", "RAYMOND.NS"])
    for sym, day in (("MASTEK.NS", "2015-06-12"), ("RAYMOND.NS", "2025-05-14")):
        c = _credit(cr, sym, day)
        assert c is not None and c["kind"] == "demerger", (sym, day)
        assert abs(c["cash"] - (c["prev_close"] - c["open"])) < 1e-6


def test_loader_stops_at_the_stage_boundary():
    with asof.boundary("2021-12-31", "optimise"):
        cr = ca.credits("india", ["AURUM.NS", "VEDL.NS"])
        acts = ca.load("india", ["VEDL.NS"])
    assert _credit(cr, "AURUM.NS", "2020-12-23") is not None
    assert cr["date"].max() <= pd.Timestamp("2021-12-31"), cr["date"].max()
    assert acts["ex_date"].max() <= pd.Timestamp("2021-12-31")
    assert _credit(ca.credits("india", ["VEDL.NS"]), "VEDL.NS", "2026-04-30") is not None


def test_unadjusted_split_is_corrected():
    # Yahoo left MOTILALOFS's June 2024 split unadjusted before 1 January 2024: 1240.85 -> 315.01
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM prices WHERE market='india' AND symbol='MOTILALOFS.NS' "
                    "AND date BETWEEN '2023-12-28' AND '2024-01-02' ORDER BY date")
        closes = [c for _, c in cur.fetchall()]
    assert max(closes) / min(closes) < 1.2, closes


def _credits(symbol, day, cash):
    return ca.Credits(pd.DataFrame([{"symbol": symbol, "date": pd.Timestamp(day), "kind": "special_dividend",
                                     "cash": cash}]))


def test_rotation_holder_is_flat_across_the_payout():
    idx = pd.bdate_range("2020-01-01", periods=60)
    px = pd.DataFrame({"X": [100.0] * 40 + [2.0] * 20}, index=idx)   # pays 98 on idx[40]
    pick = lambda d, r, p: ["X"]   # noqa: E731
    _t, eq, _h, _c = rotation.simulate(px, pick, start=str(idx[0].date()), cost_bps=0.0, account_size=1000.0,
                                       lookback_days=1, credits=_credits("X", idx[40], 98.0))
    assert abs(eq.iloc[-1] - 1000.0) < 1e-6, eq.iloc[-1]
    _t, eq0, _h, _c = rotation.simulate(px, pick, start=str(idx[0].date()), cost_bps=0.0, account_size=1000.0,
                                        lookback_days=1)
    assert eq0.iloc[-1] < 30, eq0.iloc[-1]   # without the credit: the -98% the backtest used to book


def test_simulator_moves_levels_and_pays_cash():
    idx = pd.bdate_range("2024-01-01", periods=8)
    bars = [(99, 101, 98, 100)] * 3 + [(50, 51, 49, 50)] * 5   # pays 50 on idx[3]
    df = pd.DataFrame([dict(open=o, high=h, low=l, close=c, volume=1000.0) for o, h, l, c in bars], index=idx)
    sig = Signal(date=idx[0], symbol="X", setup="S1", entry=99.0, stop=90.0, target=150.0,
                 decision="TRADE - HIGH CONFIDENCE", quality=1.0, meta={"order": "open"})
    r = simulate([sig], {"X": df}, CFG, idx[0], exit_policy=ExitPolicy(), credits=_credits("X", idx[3], 50.0))
    t = r.trades[0]
    # not stopped by the payout; the stop and entry moved down by it, so pnl is the 1-point gain plus nothing lost
    assert t.exit_reason == "OPEN" and abs(t.stop - 40.0) < 1e-9 and abs(t.entry_price - 49.0) < 1e-9, t
    assert abs(t.credited - 50.0 * t.shares) < 1e-6 and abs(t.pnl - 1.0 * t.shares) < 1e-6, (t.pnl, t.shares)
    assert abs(r.equity.iloc[-1] - (CFG.account_size + t.pnl)) < 1e-6
    r0 = simulate([sig], {"X": df}, CFG, idx[0], exit_policy=ExitPolicy())
    assert r0.trades[0].exit_reason == "STOP", r0.trades[0].exit_reason   # the old behaviour


def test_back_adjust_has_no_look_ahead():
    # a ratio read at t is the same whether or not an action dated after t is in the data
    idx = pd.bdate_range("2020-01-01", periods=300)
    px = pd.DataFrame({"X": [100.0 + i * 0.1 for i in range(250)] + [40.0 + i * 0.1 for i in range(50)]}, index=idx)
    cr = pd.DataFrame([{"symbol": "X", "date": idx[250], "kind": "demerger", "cash": 84.9, "prev_close": 124.9}])
    tr = ca.back_adjust(px, cr)
    before = idx[:250]
    ratio_tr = (tr.loc[before, "X"] / tr.loc[before, "X"].shift(20)).dropna()
    ratio_px = (px.loc[before, "X"] / px.loc[before, "X"].shift(20)).dropna()
    assert (ratio_tr - ratio_px).abs().max() < 1e-12
    # across the ex-date it is the holder's total return, not the -48% the traded close shows
    assert abs(tr["X"].iloc[255] / tr["X"].iloc[245] - 1) < 0.02, tr["X"].iloc[[245, 255]]
    # and a level put back on its own bar's scale equals the traded price
    k = ca.pit_scale(px["X"], tr["X"])
    assert ((tr["X"] * k - px["X"]).abs() < 1e-9).all()


def test_demerged_parent_keeps_its_momentum_rank():
    # ABREL demerged on 2019-10-11 (882 -> 390). With the 12-1 skip month the ex-date reaches the
    # ranking at the November month-end: on traded prices it fell to the bottom decile, on total
    # return it stays where it was.
    from swing_screener.backtesting import baseline
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM prices WHERE market='india' AND date='2019-09-30' AND dollar_vol_sma20 > 1e8")
        syms = [s for (s,) in cur.fetchall()]
        cur.execute("SELECT symbol, date, close FROM prices WHERE market='india' AND symbol = ANY(%s) "
                    "AND date BETWEEN '2018-06-01' AND '2019-11-30'", (syms,))
        px = pd.DataFrame(cur.fetchall(), columns=["s", "d", "c"]).pivot(index="d", columns="s", values="c")
    px.index = pd.to_datetime(px.index)
    with asof.boundary("2021-12-31", "optimise"):
        tr = ca.back_adjust(px, ca.credits("india", syms))

    def pct(frame, day):
        row = baseline.score_matrix(frame, "momentum", 252, 21).loc[day].dropna()
        return row.rank(pct=True)["ABREL.NS"] * 100

    before = pct(tr, "2019-09-30")
    assert abs(pct(tr, "2019-11-29") - before) < 15, (before, pct(tr, "2019-11-29"))
    assert pct(px, "2019-11-29") < 20     # the defect this fixes


def test_stage4_levels_are_point_in_time():
    # a short book's stop computed before an ex-date must not change when the action is added
    from swing_screener.backtesting.stage4_shorts import symbol_frame
    idx = pd.bdate_range("2019-01-01", periods=400)
    close = pd.Series([200 - i * 0.2 for i in range(300)] + [60 - i * 0.05 for i in range(100)], index=idx)
    df = pd.DataFrame({"open": close, "high": close * 1.01, "low": close * 0.99, "close": close, "volume": 1e6})
    bench = pd.Series(100.0, index=idx)
    cr = pd.DataFrame([{"symbol": "X", "date": idx[300], "kind": "demerger", "cash": 80.2,
                        "prev_close": float(close.iloc[299])}])
    with_action, without = symbol_frame(df, bench, cr), symbol_frame(df, bench, None)
    cols = ["stop_a", "stop_b", "line", "sma50", "atr", "close"]
    a, b = with_action.loc[idx[:300], cols], without.loc[idx[:300], cols]
    assert ((a - b).abs().fillna(0) < 1e-6).all().all()
    # after it, the demerger is not a fresh breakdown: no 52-week-low signal on the ex-date
    assert not bool(with_action.loc[idx[300], "sig_a"])


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
