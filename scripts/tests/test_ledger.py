"""The trade ledger's arithmetic: holdings are the opening balance plus every trade since.

`ledger.holdings` is the one function every reader of a book's account goes through (the Holdings
tab, the rebalance orders, the position tracker, the paper books), so it is checked here on its own:
shares, average cost, cash and realised P&L from a sequence of rows; a sale of shares never held is
refused; the account form's difference (`diff_trades`) lands the book exactly where the user says it
is; a snapshot migrated as an opening balance (`opening_rows`) reads back as that snapshot; a
rebalance's order lines read as pending / partial / filled / skipped from the trades linked to it
(`progress`); and the Portfolio tab's return takes deposits out (`book_view.chained`).

Pure arithmetic, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_ledger
"""

import sys

import pandas as pd

from swing_screener.backtesting import book_view, ledger

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def close(a, b, tol=1e-6) -> bool:
    return a is not None and b is not None and abs(a - b) <= tol


def test_holdings() -> None:
    print("holdings from trades")
    rows = [
        {"side": "CASH", "amount": 100_000, "trade_date": "2026-01-01"},
        {"side": "BUY", "symbol": "A", "shares": 100, "price": 200, "costs": 10, "trade_date": "2026-01-02"},
        {"side": "BUY", "symbol": "A", "shares": 100, "price": 300, "costs": 15, "trade_date": "2026-02-02"},
        {"side": "BUY", "symbol": "B", "shares": 50, "price": 100, "costs": 5, "trade_date": "2026-02-02"},
        {"side": "SELL", "symbol": "A", "shares": 50, "price": 400, "costs": 20, "trade_date": "2026-03-02"},
    ]
    h = ledger.holdings(rows)
    check("shares add and subtract", h["positions"] == {"A": 150.0, "B": 50.0}, str(h["positions"]))
    check("average cost is share-weighted (A: 250)", close(h["avg_cost"]["A"], 250.0), str(h["avg_cost"]))
    check("a sale leaves the average cost alone", close(h["avg_cost"]["A"], 250.0))
    want_cash = 100_000 - 20_000 - 10 - 30_000 - 15 - 5_000 - 5 + 20_000 - 20
    check("cash = deposits - buys - costs + sells", close(h["cash"], want_cash), f"{h['cash']} vs {want_cash}")
    check("realised = (sale - average cost) x shares - costs", close(h["realised"], (400 - 250) * 50 - 20),
          str(h["realised"]))
    check("costs are summed", close(h["costs"], 50.0))
    check("first entry date is kept", h["since"]["A"] == "2026-01-02", str(h["since"]))

    h2 = ledger.holdings(rows + [{"side": "SELL", "symbol": "B", "shares": 50, "price": 90, "costs": 0}])
    check("a position sold to zero leaves the book", "B" not in h2["positions"] and "B" not in h2["avg_cost"])

    h3 = ledger.holdings(rows + [{"side": "SELL", "symbol": "B", "shares": 50, "price": 90},
                                  {"side": "BUY", "symbol": "B", "shares": 10, "price": 120}])
    check("re-entry after a full exit starts a fresh average cost", close(h3["avg_cost"]["B"], 120.0))

    try:
        ledger.holdings(rows + [{"side": "SELL", "symbol": "B", "shares": 51, "price": 90}])
        check("selling more than held is refused", False, "no error")
    except ValueError:
        check("selling more than held is refused", True)
    try:
        ledger.holdings([{"side": "SELL", "symbol": "Z", "shares": 1, "price": 1}])
        check("selling a stock never held is refused", False, "no error")
    except ValueError:
        check("selling a stock never held is refused", True)

    h4 = ledger.holdings([{"side": "OPEN", "symbol": "C", "shares": 10, "price": None},
                          {"side": "BUY", "symbol": "C", "shares": 10, "price": 50}])
    check("an OPEN row without a cost leaves the average unknown", h4["avg_cost"]["C"] is None)
    check("an OPEN row does not move cash", close(h4["cash"], -500.0), str(h4["cash"]))


def test_diff() -> None:
    print("the account form's difference")
    held, cash = {"A": 150.0, "B": 50.0}, 64_950.0
    want, want_cash = {"A": 100.0, "C": 20.0}, 70_000.0
    prices = {"A": 410.0, "B": 95.0, "C": 500.0}
    rows = ledger.diff_trades(held, cash, want, want_cash, prices)
    sides = {(r["side"], r["symbol"]): r["shares"] for r in rows if r["side"] != "CASH"}
    check("a trim is a SELL of the difference", sides.get(("SELL", "A")) == 50.0, str(sides))
    check("a stock left out is sold whole", sides.get(("SELL", "B")) == 50.0, str(sides))
    check("a new stock is a BUY", sides.get(("BUY", "C")) == 20.0, str(sides))
    after = ledger.holdings([{"side": "CASH", "amount": cash}]
                            + [{"side": "BUY", "symbol": s, "shares": n, "price": 1} for s, n in held.items()]
                            + [{"side": "CASH", "amount": sum(held.values())}]       # undo the dummy cost
                            + rows)
    check("recording the difference lands the book on the entered positions", after["positions"] == want,
          str(after["positions"]))
    check("... and on the entered cash", close(after["cash"], want_cash), f"{after['cash']}")
    check("no change, no rows", ledger.diff_trades(held, cash, dict(held), cash, prices) == [])
    no_cash = ledger.diff_trades(held, cash, want, None, prices)
    check("cash left to the trades adds no CASH row", all(r["side"] != "CASH" for r in no_cash))


def test_opening_balance() -> None:
    print("a snapshot migrated as the opening balance")
    snap, cash = {"LAURUSLABS.NS": 34, "SBC.NS": 1038}, 12_345.5
    rows = ledger.opening_rows(snap, cash, "2026-11-03")
    h = ledger.holdings(rows)
    check("positions read back as the snapshot", h["positions"] == {k: float(v) for k, v in snap.items()},
          str(h["positions"]))
    check("cash reads back as the snapshot", close(h["cash"], cash))
    check("every row is dated the day the snapshot was saved", all(r["trade_date"] == "2026-11-03" for r in rows))
    empty = ledger.opening_rows({}, 0.0, "2026-11-03")
    check("an empty account still gets a row (so it reads as migrated)", len(empty) == 1 and empty[0]["side"] == "CASH")


def test_progress() -> None:
    print("a rebalance's order lines against the trades linked to it")
    orders = [{"symbol": "A", "action": "BUY", "change": 100}, {"symbol": "B", "action": "SELL ALL", "change": -50},
              {"symbol": "C", "action": "TRIM", "change": -10}, {"symbol": "D", "action": "HOLD", "change": 0},
              {"symbol": "E", "action": "ADD", "change": 20}]
    trades = [{"rebalance_id": 7, "symbol": "A", "side": "BUY", "shares": 60},
              {"rebalance_id": 7, "symbol": "B", "side": "SELL", "shares": 50},
              {"rebalance_id": 8, "symbol": "C", "side": "SELL", "shares": 10},     # another rebalance's fill
              {"rebalance_id": 7, "symbol": "E", "side": "SELL", "shares": 5}]      # the wrong side
    st = {r["symbol"]: r for r in ledger.progress(orders, trades, 7, skipped=["E"])}
    check("part of a buy is partial, with what remains", st["A"]["state"] == "partial" and st["A"]["remaining"] == 40, st["A"])
    check("a whole sale is filled", st["B"]["state"] == "filled", st["B"])
    check("a fill linked to another rebalance does not count", st["C"]["state"] == "pending", st["C"])
    check("no change ordered reads as hold", st["D"]["state"] == "hold" and st["D"]["side"] is None, st["D"])
    check("a skipped line reads as skipped", st["E"]["state"] == "skipped", st["E"])


def test_chained_return() -> None:
    print("the book's return with deposits taken out")
    idx = pd.date_range("2026-01-01", periods=4)
    eq = pd.Series([100.0, 110.0, 310.0, 279.0], index=idx)      # +10%, then a 200 deposit, then -10%
    flow = pd.Series([100.0, 0.0, 200.0, 0.0], index=idx)
    ix = book_view.chained(eq, flow)
    check("a deposit is not a gain", abs(ix.iloc[2] - 1.10) < 1e-9, ix.tolist())
    check("returns chain across it", abs(ix.iloc[3] - 0.99) < 1e-9, ix.tolist())
    trades = [{"side": "CASH", "amount": 100, "trade_date": "2026-01-01"},
              {"side": "OPEN", "symbol": "X", "shares": 2, "price": None, "trade_date": "2026-01-03"},
              {"side": "BUY", "symbol": "X", "shares": 1, "price": 50, "trade_date": "2026-01-02"}]
    closes = pd.DataFrame({"X": [40.0, 50.0, 60.0, 70.0]}, index=idx)
    fl = book_view.flows(trades, closes)
    check("cash in and shares brought in are flows; a buy is not", fl.tolist() == [100.0, 0.0, 120.0, 0.0], fl.tolist())


def main() -> int:
    test_holdings()
    test_diff()
    test_opening_balance()
    test_progress()
    test_chained_return()
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'all ledger checks pass'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
