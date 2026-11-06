"""The trade ledger: what each book bought and sold, from which its holdings are derived.

A *book* is the money you run under one strategy in one market (`book` is the strategy key, as on
the Holdings tab). Until the ledger, the account was a snapshot (`book_positions`, `book_cash`) that
each save replaced, so nothing recorded how the book got there. Now every change is a row of
`book_trades`, and the holdings are the opening balance plus every trade since:

    side   shares  price  amount  what it does
    OPEN   n       cost?  --      an opening position (a book's starting snapshot); cash unchanged
    BUY    n       p      --      shares += n; cash -= n x p + costs
    SELL   n       p      --      shares -= n; cash += n x p - costs
    CASH   --      --     a       cash += a (a deposit, a withdrawal, or the opening cash)

`book_rebalances` records a rebalance as it was computed when you confirmed it -- the target book and
the orders -- and the trades that execute it carry its id, so a month's orders can later be read
against what was actually done. It stays OPEN while you execute it: each order line is pending,
partly filled, filled (from the linked trades, `progress`) or skipped (you chose not to trade it),
and you complete it once you have reviewed what is left. A new ranking never edits it.

The snapshot tables are kept in step after every write (`_sync_snapshot`), so anything reading them
still sees the current holdings; the readers in this repo go through `holdings_of`. A book that has a
snapshot and no ledger rows yet is migrated once, as an opening balance (`migrate_snapshots`).

Nothing here talks to a broker. A Kite pull (broker/kite.py, read-only) is compared with the ledger
and shown as *proposed* fills; only the ones you confirm are recorded.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import date, datetime

import pandas as pd

from ..config import MARKETS
from ..marketdata import db

SIDES = ("OPEN", "BUY", "SELL", "CASH")
SOURCES = ("manual", "kite", "paper")
EPS = 1e-9   # a share count this close to zero is zero (fractional shares from a float sum)

SCHEMA = """
CREATE TABLE IF NOT EXISTS book_rebalances (
    id BIGSERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    market TEXT NOT NULL,
    as_of DATE NOT NULL,            -- the close the targets were computed on
    spec_id TEXT,                   -- the strategy's rules then (v<version>-<fingerprint>)
    targets JSONB NOT NULL,         -- [{symbol, weight_pct, shares, price}]
    orders JSONB NOT NULL,          -- the order rows as the page showed them
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS book_rebalances_book ON book_rebalances (book, market, as_of);
CREATE TABLE IF NOT EXISTS book_trades (
    id BIGSERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    market TEXT NOT NULL,
    trade_date DATE NOT NULL,
    symbol TEXT,                    -- NULL for a CASH row
    side TEXT NOT NULL CHECK (side IN ('OPEN', 'BUY', 'SELL', 'CASH')),
    shares DOUBLE PRECISION NOT NULL DEFAULT 0,
    price DOUBLE PRECISION,         -- per share; NULL on an OPEN row whose cost is unknown
    amount DOUBLE PRECISION,        -- CASH rows: signed cash in (+) or out (-)
    costs DOUBLE PRECISION NOT NULL DEFAULT 0,
    rebalance_id BIGINT REFERENCES book_rebalances(id) ON DELETE SET NULL,
    source TEXT NOT NULL CHECK (source IN ('manual', 'kite', 'paper')),
    entry_rule TEXT,                -- signal trades: the strategy's setup code / entry rule
    setup TEXT,                     -- signal trades: the setup's own label
    initial_stop DOUBLE PRECISION,  -- signal trades: the stop accepted at entry (R is measured from it)
    target DOUBLE PRECISION,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS book_trades_book ON book_trades (book, market, trade_date, id);
-- signal trades: the levels the strategy's exit reads (a Darvas box, a pivot), as its signal carried them
ALTER TABLE book_trades ADD COLUMN IF NOT EXISTS meta JSONB;
-- a rebalance is open until you complete it; an order line you chose not to trade is skipped, not dropped
ALTER TABLE book_rebalances ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ;
ALTER TABLE book_rebalances ADD COLUMN IF NOT EXISTS skipped JSONB NOT NULL DEFAULT '[]';
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)
    migrate_snapshots()


@contextmanager
def _tx():
    """One transaction on the pooled (autocommit) connection: every row of a save lands, or none."""
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute("BEGIN")
        try:
            yield cur
        except BaseException:
            cur.execute("ROLLBACK")
            raise
        cur.execute("COMMIT")


def market_today(market: str) -> date:
    """Today on the market's own clock -- the default trade date."""
    return pd.Timestamp.now(tz=MARKETS[market].tz).date()


# ------------------------------------------------------------------ arithmetic (no database)

def holdings(trades: list[dict]) -> dict:
    """The book that `trades` (in order) leave: shares and average cost per symbol, cash, and the
    realised P&L of every sale. Pure arithmetic, so it is tested without a database.

    Average cost is the share-weighted price paid (an OPEN row without a price makes it unknown until
    the position is closed out); a sale realises (price - average cost) x shares - costs and leaves
    the average where it was."""
    shares: dict[str, float] = {}
    cost: dict[str, float | None] = {}
    first: dict[str, str] = {}
    cash = realised = costs = 0.0
    for t in trades:
        side, sym = t["side"], t.get("symbol")
        n, px, fee = float(t.get("shares") or 0), t.get("price"), float(t.get("costs") or 0)
        costs += fee
        if side == "CASH":
            cash += float(t.get("amount") or 0)
            continue
        if side not in SIDES or not sym:
            raise ValueError(f"not a ledger row: {t}")
        have = shares.get(sym, 0.0)
        if side in ("OPEN", "BUY"):
            if have <= EPS:
                cost[sym], first[sym] = (float(px) if px is not None else None), str(t.get("trade_date") or "")
            elif cost.get(sym) is not None and px is not None:
                cost[sym] = (cost[sym] * have + float(px) * n) / (have + n)
            else:
                cost[sym] = None
            shares[sym] = have + n
            if side == "BUY":
                cash -= n * float(px) + fee
            else:
                cash -= fee
        else:  # SELL
            if n > have + EPS:
                raise ValueError(f"{sym}: selling {n:g} shares, but the book holds {have:g}")
            cash += n * float(px) - fee
            if cost.get(sym) is not None:
                realised += (float(px) - cost[sym]) * n - fee
            shares[sym] = have - n
        if shares[sym] <= EPS:
            shares.pop(sym), cost.pop(sym, None), first.pop(sym, None)
    return {"positions": dict(sorted(shares.items())), "avg_cost": cost, "since": first,
            "cash": cash, "realised": realised, "costs": costs}


def diff_trades(held: dict, cash: float, want: dict, want_cash: float | None, prices: dict) -> list[dict]:
    """The trades that turn `held` (symbol -> shares) and `cash` into `want` and `want_cash`.

    Each difference is a BUY or SELL at `prices[symbol]` (the latest close, or the broker's last
    price: an estimate the user may correct before confirming). The cash those trades would move is
    then reconciled to `want_cash` with one CASH row, so the book ends exactly where the user says it
    is. `want_cash` None leaves the cash to the trades."""
    out = []
    for sym in sorted(set(held) | set(want)):
        d = float(want.get(sym, 0)) - float(held.get(sym, 0))
        if abs(d) <= EPS:
            continue
        out.append({"side": "BUY" if d > 0 else "SELL", "symbol": sym, "shares": abs(d),
                    "price": prices.get(sym), "costs": 0.0})
    if want_cash is not None:
        moved = sum((-1 if t["side"] == "BUY" else 1) * t["shares"] * (t["price"] or 0) for t in out)
        gap = float(want_cash) - (float(cash) + moved)
        if abs(gap) > 0.005:
            out.append({"side": "CASH", "symbol": None, "shares": 0, "price": None, "amount": round(gap, 2),
                        "costs": 0.0, "note": "cash reconciliation: the cash you entered, less what the trades "
                                              "above would have moved"})
    return out


# ------------------------------------------------------------------ storage

_COLS = ("id", "trade_date", "symbol", "side", "shares", "price", "amount", "costs", "rebalance_id", "source",
         "entry_rule", "setup", "initial_stop", "target", "note", "created_at", "meta")


def trades(book: str, market: str) -> list[dict]:
    """Every ledger row of the book, oldest first."""
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {', '.join(_COLS)} FROM book_trades WHERE book=%s AND market=%s "
                    "ORDER BY trade_date, id", (book, market))
        rows = [dict(zip(_COLS, r)) for r in cur.fetchall()]
    for r in rows:
        r["trade_date"] = r["trade_date"].isoformat()
        r["created_at"] = r["created_at"].isoformat()
    return rows


def holdings_of(book: str, market: str) -> dict:
    """The book's holdings now, from its ledger, in the shape `rebalance.get_positions` has always
    returned (plus average cost and realised P&L)."""
    rows = trades(book, market)
    h = holdings(rows)
    return {"book": book, "market": market, "positions": h["positions"], "cash": h["cash"],
            "avg_cost": h["avg_cost"], "since": h["since"], "realised": h["realised"], "costs": h["costs"],
            "trades": len(rows), "updated_at": max((r["created_at"] for r in rows), default=None)}


def _clean(market: str, t: dict, source: str, default_date) -> dict:
    from .rebalance import normalise_symbol
    side = str(t.get("side", "")).upper()
    if side not in SIDES:
        raise ValueError(f"side must be one of {SIDES}, not {t.get('side')!r}")
    src = t.get("source") or source
    if src not in SOURCES:
        raise ValueError(f"source must be one of {SOURCES}")
    out = {"side": side, "source": src, "trade_date": str(t.get("trade_date") or default_date),
           "costs": float(t.get("costs") or 0), "note": t.get("note") or None,
           "rebalance_id": t.get("rebalance_id") or None, "entry_rule": t.get("entry_rule") or None,
           "setup": t.get("setup") or None,
           "initial_stop": float(t["initial_stop"]) if t.get("initial_stop") not in (None, "") else None,
           "target": float(t["target"]) if t.get("target") not in (None, "") else None,
           "meta": t.get("meta") or None}
    datetime.strptime(out["trade_date"], "%Y-%m-%d")   # a date, or ValueError
    if out["costs"] < 0:
        raise ValueError("costs cannot be negative")
    if side == "CASH":
        out.update(symbol=None, shares=0.0, price=None, amount=float(t.get("amount") or 0))
        return out
    sym = str(t.get("symbol") or "").strip()
    if not sym:
        raise ValueError(f"a {side} needs a symbol")
    n = float(t.get("shares") or 0)
    if n <= 0:
        raise ValueError(f"{sym}: shares must be positive")
    px = t.get("price")
    if px in (None, "") and side != "OPEN":
        raise ValueError(f"{sym}: a {side} needs a price")
    px = float(px) if px not in (None, "") else None
    if px is not None and px <= 0:
        raise ValueError(f"{sym}: price must be positive")
    # a paper book's dual momentum leg holds the asset series itself (NDX_INR, CASH_FUND), not a ticker
    from .paper import _asset_keys
    keep = src == "paper" and sym in _asset_keys(market)
    out.update(symbol=sym if keep else normalise_symbol(market, sym), shares=n, price=px, amount=None)
    return out


def record(book: str, market: str, rows: list[dict], source: str = "manual") -> list[int]:
    """Append trades to the book, in one transaction, after checking they leave no short position.
    Returns the new rows' ids."""
    if not rows:
        return []
    today = market_today(market)
    clean = [_clean(market, t, source, today) for t in rows]
    with _tx() as cur:
        cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"book:{book}:{market}",))
        existing = trades(book, market)
        merged = sorted(existing + clean, key=lambda r: (r["trade_date"], r.get("id") or float("inf")))
        holdings(merged)      # raises on a sale of shares the book does not hold
        ids = []
        for t in clean:
            cur.execute(
                "INSERT INTO book_trades (book, market, trade_date, symbol, side, shares, price, amount, costs, "
                "rebalance_id, source, entry_rule, setup, initial_stop, target, note, meta) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (book, market, t["trade_date"], t["symbol"], t["side"], t["shares"], t["price"], t["amount"],
                 t["costs"], t["rebalance_id"], t["source"], t["entry_rule"], t["setup"], t["initial_stop"],
                 t["target"], t["note"], json.dumps(t["meta"]) if t["meta"] else None))
            ids.append(cur.fetchone()[0])
    _sync_snapshot(book, market)
    return ids


def delete_trade(book: str, market: str, trade_id: int) -> bool:
    """Remove one mistaken row, if what remains still adds up (no sale of shares never held)."""
    rest = [t for t in trades(book, market) if t["id"] != trade_id]
    holdings(rest)
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM book_trades WHERE id=%s AND book=%s AND market=%s", (trade_id, book, market))
        gone = cur.rowcount > 0
    _sync_snapshot(book, market)
    return gone


def _sync_snapshot(book: str, market: str) -> None:
    """Write the derived holdings back to `book_positions` / `book_cash`, so the snapshot never
    disagrees with the ledger."""
    h = holdings(trades(book, market))
    with _tx() as cur:
        cur.execute("DELETE FROM book_positions WHERE book=%s AND market=%s", (book, market))
        for sym, sh in h["positions"].items():
            cur.execute("INSERT INTO book_positions (book, market, symbol, shares) VALUES (%s,%s,%s,%s)",
                        (book, market, sym, sh))
        cur.execute("INSERT INTO book_cash (book, market, cash) VALUES (%s,%s,%s) ON CONFLICT (book, market) "
                    "DO UPDATE SET cash = EXCLUDED.cash, updated_at = now()", (book, market, h["cash"]))


def opening_rows(positions: dict, cash: float, on: str) -> list[dict]:
    """A snapshot as the ledger's opening balance: one OPEN row per position (cost unknown) and the
    cash as one CASH row -- even at zero, so the book reads as migrated."""
    note = f"opening balance: the account as saved on {on}, before the ledger"
    return ([{"side": "OPEN", "symbol": s, "shares": float(n), "price": None, "trade_date": on, "note": note}
             for s, n in sorted(positions.items()) if float(n) > EPS]
            + [{"side": "CASH", "amount": float(cash), "trade_date": on, "note": note}])


def migrate_snapshots() -> list[tuple]:
    """Each book with a `book_positions` / `book_cash` snapshot and no ledger rows gets the snapshot as
    its opening balance, dated the day it was saved. Idempotent: a migrated book has ledger rows."""
    with db.get_connection().cursor() as cur:
        cur.execute("""
            SELECT b.book, b.market FROM (SELECT book, market FROM book_cash
                                          UNION SELECT book, market FROM book_positions) b
            WHERE NOT EXISTS (SELECT 1 FROM book_trades t WHERE t.book=b.book AND t.market=b.market)""")
        todo = cur.fetchall()
    done = []
    for book, market in todo:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT symbol, shares, updated_at FROM book_positions WHERE book=%s AND market=%s",
                        (book, market))
            pos = cur.fetchall()
            cur.execute("SELECT cash, updated_at FROM book_cash WHERE book=%s AND market=%s", (book, market))
            c = cur.fetchone()
        stamps = [r[2] for r in pos] + ([c[1]] if c else [])
        on = max(stamps).astimezone().date().isoformat() if stamps else market_today(market).isoformat()
        record(book, market, opening_rows({r[0]: r[1] for r in pos}, float(c[0]) if c else 0.0, on))
        done.append((book, market))
    return done


# ------------------------------------------------------------------ rebalances

def save_rebalance(book: str, market: str, as_of: str, spec_id: str | None, targets: list, orders: list,
                   note: str | None = None) -> int:
    with db.get_connection().cursor() as cur:
        cur.execute("INSERT INTO book_rebalances (book, market, as_of, spec_id, targets, orders, note) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (book, market, as_of, spec_id, json.dumps(targets), json.dumps(orders), note))
        return cur.fetchone()[0]


def progress(orders: list[dict], trades_: list[dict], rebalance_id: int, skipped=()) -> list[dict]:
    """Each order line of a rebalance against the trades linked to it (`rebalance_id`): how much of the
    ordered change is filled, and its state -- pending, partial, filled, skipped (you chose not to trade
    it) or hold (no change ordered). Pure arithmetic, so it is tested without a database.

    A BUY / ADD line is filled by BUY rows of its symbol, a SELL ALL / TRIM line by SELL rows; a fill
    beyond the ordered size counts as filled (the extra shows in `filled`)."""
    skipped = set(skipped or ())
    out = []
    for o in orders:
        change = float(o.get("change") or 0)
        side = "BUY" if change > 0 else "SELL" if change < 0 else None
        fills = [t for t in trades_ if side and t.get("rebalance_id") == rebalance_id
                 and t.get("symbol") == o.get("symbol") and t.get("side") == side]
        filled = sum(float(t.get("shares") or 0) for t in fills)
        paid = sum(float(t.get("shares") or 0) * float(t.get("price") or 0) for t in fills)
        want = abs(change)
        if side is None:
            state = "hold"
        elif o.get("symbol") in skipped:
            state = "skipped"
        elif filled >= want - EPS:
            state = "filled"
        else:
            state = "partial" if filled > EPS else "pending"
        out.append({**o, "side": side, "ordered": want, "filled": filled,
                    "fill_price": paid / filled if filled > EPS else None,
                    "remaining": max(0.0, want - filled), "state": state})
    return out


def rebalances(book: str, market: str, limit: int = 24) -> list[dict]:
    """The book's confirmed rebalances, newest first, each with what was traded against it."""
    with db.get_connection().cursor() as cur:
        cur.execute("""
            SELECT r.id, r.as_of, r.spec_id, r.targets, r.orders, r.note, r.created_at, r.completed_at, r.skipped,
                   count(t.id), coalesce(sum(CASE WHEN t.side='BUY' THEN t.shares*t.price END), 0),
                   coalesce(sum(CASE WHEN t.side='SELL' THEN t.shares*t.price END), 0)
            FROM book_rebalances r LEFT JOIN book_trades t ON t.rebalance_id = r.id
            WHERE r.book=%s AND r.market=%s GROUP BY r.id ORDER BY r.as_of DESC, r.id DESC LIMIT %s""",
                    (book, market, limit))
        rows = cur.fetchall()
    return [{"id": r[0], "as_of": r[1].isoformat(), "spec_id": r[2], "targets": r[3], "orders": r[4],
             "note": r[5], "created_at": r[6].isoformat(), "completed_at": r[7].isoformat() if r[7] else None,
             "skipped": r[8] or [], "trades": r[9], "bought": r[10], "sold": r[11]}
            for r in rows]


def open_rebalance(book: str, market: str) -> dict | None:
    """The newest rebalance not yet completed, with each order line's progress -- or None."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id FROM book_rebalances WHERE book=%s AND market=%s AND completed_at IS NULL "
                    "ORDER BY as_of DESC, id DESC LIMIT 1", (book, market))
        r = cur.fetchone()
    if not r:
        return None
    reb = next(x for x in rebalances(book, market, limit=200) if x["id"] == r[0])
    reb["lines"] = progress(reb["orders"], trades(book, market), reb["id"], reb["skipped"])
    return reb


def _rebalance_of(cur, book: str, market: str, rid: int) -> tuple:
    cur.execute("SELECT skipped, completed_at FROM book_rebalances WHERE id=%s AND book=%s AND market=%s",
                (rid, book, market))
    r = cur.fetchone()
    if not r:
        raise LookupError("no such rebalance in this book")
    return r


def set_skipped(book: str, market: str, rid: int, symbol: str, skipped: bool) -> list:
    """Mark an order line of an open rebalance as one you chose not to trade (or undo that)."""
    with _tx() as cur:
        have, done = _rebalance_of(cur, book, market, rid)
        if done:
            raise ValueError("this rebalance is completed")
        now = sorted((set(have or []) | {symbol}) if skipped else (set(have or []) - {symbol}))
        cur.execute("UPDATE book_rebalances SET skipped=%s WHERE id=%s", (json.dumps(now), rid))
    return now


def complete(book: str, market: str, rid: int, note: str | None = None) -> None:
    """Close a rebalance: you have reviewed what was filled, partly filled or skipped. Its record stays."""
    with _tx() as cur:
        _rebalance_of(cur, book, market, rid)
        cur.execute("UPDATE book_rebalances SET completed_at=now(), note=coalesce(%s, note) WHERE id=%s",
                    (note, rid))
