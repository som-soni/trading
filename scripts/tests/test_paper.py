"""Paper books: the forward record's arithmetic and the rebalance fill.

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


def main() -> int:
    test_equity_curve()
    test_fill_rebalance()
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'paper books add up'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
