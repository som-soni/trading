"""Rebalance orders for a ranking strategy against the positions you actually hold.

The strategy's book comes from `baseline.current_selection` -- the selection and weights its backtest
uses -- so the orders cannot drift from the measured rules. What this module adds is the account:
the shares you hold in each stock and your cash, stored in Postgres (`book_positions`,
`book_cash`), so the page can say SELL / BUY / ADD / TRIM / HOLD per stock instead of leaving the
difference to be worked out by hand.

The account is valued at the latest stored closes, each target is sized as the backtest sizes it --
whole shares, `int(account value x weight / price)` -- and costs are estimated at the strategy's own
per-side cost. A reading of the rules as of the last close, not a recommendation: the strategy trades
only at a month-end close.
"""

from __future__ import annotations

import pandas as pd

from ..config import MARKETS
from ..marketdata import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS book_positions (
    book TEXT NOT NULL,          -- the strategy key the positions are run under
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    shares DOUBLE PRECISION NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (book, market, symbol)
);
CREATE TABLE IF NOT EXISTS book_cash (
    book TEXT NOT NULL,
    market TEXT NOT NULL,
    cash DOUBLE PRECISION NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (book, market)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def normalise_symbol(market: str, symbol: str) -> str:
    """`laurus labs` is not a symbol, but `LAURUSLABS` is `LAURUSLABS.NS` in India: upper-case it and
    add the market's ticker suffix when it is missing."""
    sym = symbol.strip().upper()
    suffix = MARKETS[market].symbol_suffix
    return sym if not suffix or sym.endswith(suffix) else sym + suffix


def get_positions(book: str, market: str) -> dict:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, shares, updated_at FROM book_positions WHERE book=%s AND market=%s "
                    "ORDER BY symbol", (book, market))
        rows = cur.fetchall()
        cur.execute("SELECT cash, updated_at FROM book_cash WHERE book=%s AND market=%s", (book, market))
        c = cur.fetchone()
    stamps = [r[2] for r in rows] + ([c[1]] if c else [])
    return {"book": book, "market": market, "positions": {r[0]: float(r[1]) for r in rows},
            "cash": float(c[0]) if c else 0.0,
            "updated_at": max(stamps).isoformat() if stamps else None}


def set_positions(book: str, market: str, positions: dict, cash: float) -> dict:
    """Replace the whole account: the positions you hold now, and your cash. A symbol at zero shares
    is dropped."""
    clean = {}
    for sym, sh in positions.items():
        sh = float(sh)
        if sh < 0:
            raise ValueError(f"{sym}: shares cannot be negative")
        if sh > 0:
            clean[normalise_symbol(market, sym)] = clean.get(normalise_symbol(market, sym), 0.0) + sh
    if cash < 0:
        raise ValueError("cash cannot be negative")
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM book_positions WHERE book=%s AND market=%s", (book, market))
        for sym, sh in clean.items():
            cur.execute("INSERT INTO book_positions (book, market, symbol, shares) VALUES (%s,%s,%s,%s)",
                        (book, market, sym, sh))
        cur.execute("INSERT INTO book_cash (book, market, cash) VALUES (%s,%s,%s) ON CONFLICT (book, market) "
                    "DO UPDATE SET cash = EXCLUDED.cash, updated_at = now()", (book, market, float(cash)))
    return get_positions(book, market)


def _last_closes(market: str, symbols: list, as_of: str | None) -> dict:
    """The latest stored close on or before `as_of` for each symbol -- for a holding the ranking does
    not list (it left the book), whose price the selection does not carry."""
    if not symbols:
        return {}
    with db.get_connection().cursor() as cur:
        cur.execute(
            "SELECT DISTINCT ON (symbol) symbol, close FROM prices WHERE market=%s AND symbol = ANY(%s)"
            + (" AND date <= %s" if as_of else "") + " ORDER BY symbol, date DESC",
            (market, symbols, as_of) if as_of else (market, symbols))
        return {s: float(c) for s, c in cur.fetchall() if c is not None}


def orders(book: str, market: str) -> dict:
    """The trades that turn the positions you hold into the strategy's book on the latest close."""
    from ..strategies import portfolio_strategies
    from . import baseline

    cls = portfolio_strategies()[book]
    sel = baseline.current_selection(market, book)
    acct = get_positions(book, market)
    held = acct["positions"]
    target_rows = [r for r in sel.get("rows", []) if r.get("held") and r.get("weight_pct") is not None]
    price = {r["symbol"]: r["close"] for r in sel.get("rows", [])}
    missing = [s for s in held if s not in price]
    price.update(_last_closes(market, missing, sel.get("as_of")))

    unpriced = [s for s in held if s not in price]
    value_held = sum(sh * price[s] for s, sh in held.items() if s in price)
    account = acct["cash"] + value_held
    tot = sum(r["weight_pct"] for r in target_rows) or 1.0

    rows = []
    for r in target_rows:
        s, p = r["symbol"], r["close"]
        w = r["weight_pct"] / tot
        want = int(account * w // p) if p and account > 0 else 0
        rows.append({"symbol": s, "weight_pct": round(w * 100, 2), "price": p,
                     "held": held.get(s, 0.0), "target": want})
    for s, sh in held.items():
        if s not in {r["symbol"] for r in target_rows}:
            rows.append({"symbol": s, "weight_pct": 0.0, "price": price.get(s), "held": sh, "target": 0})
    cost = float(getattr(cls, "cost_bps", 0.0)) / 10_000
    for r in rows:
        d = r["target"] - r["held"]
        r["change"] = d
        r["action"] = ("SELL ALL" if r["target"] == 0 and r["held"] > 0 else
                       "BUY" if r["held"] == 0 and r["target"] > 0 else
                       "ADD" if d > 0 else "TRIM" if d < 0 else "HOLD")
        r["amount"] = round(d * r["price"], 2) if r["price"] else None
    order = {"SELL ALL": 0, "TRIM": 1, "BUY": 2, "ADD": 3, "HOLD": 4}
    rows.sort(key=lambda r: (order[r["action"]], -abs(r["amount"] or 0)))
    sells = -sum(r["amount"] for r in rows if r["amount"] and r["amount"] < 0)
    buys = sum(r["amount"] for r in rows if r["amount"] and r["amount"] > 0)
    as_of = pd.Timestamp(sel["as_of"]) if sel.get("as_of") else None
    return {
        "book": book, "market": market, "as_of": sel.get("as_of"), "spec_id": sel.get("spec_id"),
        "is_month_end": bool(as_of is not None and as_of == as_of + pd.offsets.BMonthEnd(0)),
        "regime": sel.get("regime"), "account_value": round(account, 2), "cash": acct["cash"],
        "positions_updated_at": acct["updated_at"], "unpriced": unpriced,
        "sells": round(sells, 2), "buys": round(buys, 2),
        "cash_after": round(acct["cash"] + sells - buys, 2),
        "est_costs": round((sells + buys) * cost, 2), "cost_bps": float(getattr(cls, "cost_bps", 0.0)),
        "rows": rows,
    }
