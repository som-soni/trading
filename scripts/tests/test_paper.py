"""Paper books: the forward record's arithmetic and the rebalance fill.

A signal strategy's paper book replays its live orders through the backtest's simulator (`paper.replay`,
`paper._step_signal`): checked on synthetic bars that a buy-stop which never triggers is never bought (until
2026-11-14 every tradeable row was bought at the next open), that one which triggers fills at its trigger, and
that a second day writes only the new fills.

`paper.equity_curve` is the forward record's equity line -- the ledger's cash and shares at each session's
end, at that session's closes -- and `paper.fill_rebalance` is how a paper book trades a month's targets at
the next open: sell what left the book, then size each target to its weight of the account valued at that
open, in whole shares, the strategy's cost per side, sells before buys. Both are checked on hand-made
numbers, with the ledger and prices stubbed.

    PYTHONPATH=. .venv/bin/python -m tests.test_paper
"""

import math
import sys

import pandas as pd

from swing_screener.backtesting import ledger, paper

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def test_equity_curve() -> None:
    print("the equity line")
    idx = pd.bdate_range("2026-11-02", periods=5)
    closes = pd.DataFrame({"A": [100, 110, 120, 130, 140], "B": [50, 50, float("nan"), 55, 60]}, index=idx, dtype=float)
    trades = [{"side": "CASH", "amount": 10_000, "trade_date": "2026-11-02"},
              {"side": "BUY", "symbol": "A", "shares": 10, "price": 105, "costs": 5, "trade_date": "2026-11-03"},
              {"side": "BUY", "symbol": "B", "shares": 20, "price": 50, "costs": 0, "trade_date": "2026-11-03"},
              {"side": "SELL", "symbol": "A", "shares": 10, "price": 125, "costs": 5, "trade_date": "2026-11-05"}]
    eq = paper.equity_curve(trades, closes)
    want = [10_000,
            10_000 - 1050 - 5 - 1000 + 10 * 110 + 20 * 50,
            10_000 - 1050 - 5 - 1000 + 10 * 120 + 20 * 50,     # B has no close: its last one carries
            10_000 - 1050 - 5 - 1000 + 1250 - 5 + 20 * 55,
            10_000 - 1050 - 5 - 1000 + 1250 - 5 + 20 * 60]
    check("cash plus shares at each close, from each trade's date", all(math.isclose(a, b) for a, b in zip(eq, want)),
          f"{list(eq)} vs {want}")
    check("the curve agrees with the ledger's cash at the end",
          math.isclose(eq.iloc[-1] - 20 * 60, ledger.holdings(trades)["cash"]))


def test_fill_rebalance() -> None:
    print("the rebalance fill at the next open")
    acct = {"positions": {"OLD": 100.0, "KEEP": 50.0}, "cash": 1_000.0}
    opens = {"OLD": 20.0, "KEEP": 40.0, "NEW": 30.0}
    orig = (ledger.holdings_of, paper._price_on, paper._cost_bps)
    try:
        ledger.holdings_of = lambda b, m: acct
        paper._price_on = lambda m, s, d, f="open", c=None: opens.get(s)
        paper._cost_bps = lambda st, m, s: 10.0
        rows = paper.fill_rebalance("b", "india", "s", {"KEEP": 0.5, "NEW": 0.5}, pd.Timestamp("2026-11-03"), 7, {})
    finally:
        ledger.holdings_of, paper._price_on, paper._cost_bps = orig
    equity = 1_000 + 100 * 20 + 50 * 40                           # 5,000 at the open
    got = {(r["side"], r["symbol"]): r["shares"] for r in rows}
    check("what left the book is sold whole", got.get(("SELL", "OLD")) == 100.0, str(got))
    check("a kept name is resized to its weight", got.get(("BUY", "KEEP")) == int(equity * 0.5 // 40) - 50, str(got))
    check("a new name is bought to its weight, as cash allows", ("BUY", "NEW") in got
          and got[("BUY", "NEW")] <= int(equity * 0.5 // 30), str(got))
    check("sells come before buys", [r["side"] for r in rows].index("SELL") < [r["side"] for r in rows].index("BUY"))
    check("costs are the strategy's per side on the notional",
          all(math.isclose(r["costs"], round(r["shares"] * r["price"] * 10 / 10_000, 4)) for r in rows))
    after = ledger.holdings([{"side": "CASH", "amount": 1_000}, {"side": "OPEN", "symbol": "OLD", "shares": 100},
                             {"side": "OPEN", "symbol": "KEEP", "shares": 50}] + rows)
    check("the book never goes short of cash", after["cash"] >= -1e-9, str(after["cash"]))
    check("every fill carries the rebalance id and the open's date",
          all(r["rebalance_id"] == 7 and r["trade_date"] == "2026-11-03" for r in rows))


def test_ma_trend_selection() -> None:
    """The ma_trend paper book's monthly decision is the backtest's: at every month-end, the share of
    sleeves holding equals the share `faber` holds on the same series, cut at that close."""
    print("the ma_trend live selection")
    import numpy as np
    from swing_screener.backtesting import ma_trend as mt, rotation
    idx = pd.bdate_range("2012-01-02", "2020-12-31")
    rng = np.random.default_rng(7)
    close = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0002, 0.012, len(idx)))), index=idx)
    zero = pd.Series(0.0, index=idx)
    held = {n: mt.faber("us", "2013-06-01", months=n, preloaded=close, capital=1.0, cash_rate=zero, quote=close)[2]
            for n in mt.FABER_LOOKBACKS}
    ends = rotation.rebalance_dates(idx, pd.Timestamp("2013-06-01"), mt.REBALANCE)
    bad = [d for d in ends
           if abs(sum(mt.current_selection("us", close=close, upto=d)["weights"].values())
                  - sum(int(held[n].loc[d]) for n in mt.FABER_LOOKBACKS) / len(mt.FABER_LOOKBACKS)) > 1e-9]
    check(f"the share held matches faber at all {len(ends)} month-ends", not bad, str(bad[:3]))
    states = {round(sum(mt.current_selection("us", close=close, upto=d)["weights"].values()), 2) for d in ends}
    check("the synthetic path exercises partial holdings, not only all-in and all-out",
          len(states - {0.0, 1.0}) > 0, str(states))


def test_signal_book_replays_the_backtest_orders() -> None:
    print("a signal book trades its strategy's own orders")
    import dataclasses
    from swing_screener.backtesting import backtest, portfolio_sim, tracker
    from swing_screener.backtesting.portfolio_sim import ExitPolicy, Signal
    from swing_screener.config import MARKETS
    from swing_screener.marketdata import cache, corporate_actions
    idx = pd.bdate_range("2026-11-02", periods=8)

    def frame(rows):
        df = pd.DataFrame(rows, columns=["open", "high", "low", "close"], index=idx[:len(rows)], dtype=float)
        df["volume"] = 1e6
        return df
    bars = {  # A: a buy-stop at 101 the price never reaches; B: one it crosses on the second session
        "A": frame([(98, 99, 97, 98.5)] * 8),
        "B": frame([(98, 99, 97, 98.5), (99, 102, 98.5, 101.5)] + [(101.5, 103, 101, 102.5)] * 6),
    }
    meta = {"order": "stop", "pivot": 101.0, "tight_low": 95.0, "max_fill": 106.0, "max_risk_pct": 0.10,
            "base_id": "b"}
    sigs = [Signal(date=idx[0], symbol=s, setup="S8", entry=101.0, stop=95.0, target=float("nan"),
                   decision="TRADE ON TRIGGER", quality=1.0, meta=dict(meta)) for s in ("A", "B")]
    cfg = dataclasses.replace(MARKETS["india"], slippage_bps=0.0, commission_per_order=0.0)
    store: list = []
    upto = {"n": 5}
    orig = (paper._started, paper._capital, paper._live_signals, paper._pending, cache.load_cached,
            backtest.sim_settings_for, corporate_actions.Credits.for_market, ledger.trades, ledger.record,
            tracker.refresh)
    try:
        paper._started = lambda b, m: idx[0].date()
        paper._capital = lambda b, m: 1_000_000.0
        paper._live_signals = lambda m, st, sess, started: list(sigs)
        paper._pending = lambda b, m: []
        cache.load_cached = lambda m, s: bars[s].iloc[:upto["n"]]
        backtest.sim_settings_for = lambda st, m: {"cfg": cfg, "rank_by": "setup", "spec_costs": False,
                                                   "simulate": {"exit_policy": ExitPolicy(mode="minervini", use_target=False)}}
        corporate_actions.Credits.for_market = classmethod(lambda cls, m, syms=None: None)
        ledger.trades = lambda b, m: [dict(r, source="paper") for r in store]
        ledger.record = lambda b, m, rows, source="manual": store.extend(rows) or []
        tracker.refresh = lambda m, books=None: {}
        d1 = paper._step_signal("x@paper", "india", "minervini", idx[:5], {"filled": 0, "skipped": 0, "decided": 0})
        buys = [r for r in store if r["side"] == "BUY"]
        check("the untriggered buy-stop is never bought", not any(r["symbol"] == "A" for r in buys), str(buys))
        check("the triggered one fills at its trigger, on the session it triggered",
              [(r["symbol"], r["trade_date"], r["price"]) for r in buys] == [("B", idx[1].date().isoformat(), 101.0)],
              str(buys))
        check("the buy carries its stop for the tracker", buys and buys[0].get("initial_stop") == 95.0, str(buys))
        n1 = len(store)
        upto["n"] = 8
        d2 = paper._step_signal("x@paper", "india", "minervini", idx, {"filled": 0, "skipped": 0, "decided": 0})
        check("a later day writes only new fills, never the old ones again",
              len([r for r in store if r["side"] == "BUY"]) == 1 and d2["diverged"] == 0 and len(store) >= n1,
              f"{store} {d1} {d2}")
    finally:
        (paper._started, paper._capital, paper._live_signals, paper._pending, cache.load_cached,
         backtest.sim_settings_for, corporate_actions.Credits.for_market, ledger.trades, ledger.record,
         tracker.refresh) = orig
    _ = portfolio_sim  # imported for the patch targets' modules to be loaded


def main() -> int:
    test_equity_curve()
    test_fill_rebalance()
    test_ma_trend_selection()
    test_signal_book_replays_the_backtest_orders()
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'paper books add up'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
