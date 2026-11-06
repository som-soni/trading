"""Rebalance orders for a ranking strategy against the positions you actually hold.

The strategy's book comes from `baseline.current_selection` -- the selection and weights its backtest
uses -- so the orders cannot drift from the measured rules. What this module adds is the account:
the shares you hold in each stock and your cash, derived from the book's trade ledger
(`ledger.py`, `book_trades`; `book_positions` / `book_cash` are kept as its snapshot), so the page
can say SELL / BUY / ADD / TRIM / HOLD per stock instead of leaving the difference to be worked out
by hand.

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


def normalise_symbol(market: str, symbol: str) -> str:
    """`laurus labs` is not a symbol, but `LAURUSLABS` is `LAURUSLABS.NS` in India: upper-case it and
    add the market's ticker suffix when it is missing."""
    sym = symbol.strip().upper()
    suffix = MARKETS[market].symbol_suffix
    return sym if not suffix or sym.endswith(suffix) else sym + suffix


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)
    from . import ledger
    ledger.init_schema()


def get_positions(book: str, market: str) -> dict:
    """The account the orders start from: the book's holdings derived from its ledger
    (`ledger.holdings_of` -- opening balance plus every trade since)."""
    from . import ledger
    return ledger.holdings_of(book, market)


def _clean_positions(market: str, positions: dict, cash: float) -> dict:
    clean = {}
    for sym, sh in positions.items():
        sh = float(sh)
        if sh < 0:
            raise ValueError(f"{sym}: shares cannot be negative")
        if sh > 0:
            clean[normalise_symbol(market, sym)] = clean.get(normalise_symbol(market, sym), 0.0) + sh
    if cash < 0:
        raise ValueError("cash cannot be negative")
    return clean


def propose_positions(book: str, market: str, positions: dict, cash: float | None,
                      prices: dict | None = None) -> dict:
    """What saving `positions` and `cash` as the account would record: the BUY / SELL for each
    difference from the ledger's holdings, priced at `prices` (a broker's last price) or else the
    latest stored close, and one CASH row reconciling the cash. Nothing is written."""
    from . import ledger
    clean = _clean_positions(market, positions, cash or 0.0)
    acct = ledger.holdings_of(book, market)
    syms = sorted(set(clean) | set(acct["positions"]))
    px = {s: float(p) for s, p in ((normalise_symbol(market, k), v) for k, v in (prices or {}).items()) if p}
    broker = set(px)
    px.update(_last_closes(market, [s for s in syms if s not in px], None))
    rows = ledger.diff_trades(acct["positions"], acct["cash"], clean, cash, px)
    for r in rows:
        if r["side"] != "CASH":
            r["price_from"] = "broker" if r["symbol"] in broker else "close"
    return {"book": book, "market": market, "account": acct, "trades": rows,
            "unpriced": [r["symbol"] for r in rows if r["side"] != "CASH" and not r["price"]]}


def set_positions(book: str, market: str, positions: dict, cash: float, trade_date: str | None = None) -> dict:
    """Save the account as you hold it now. The difference from the ledger is RECORDED as manual
    trades at the latest closes (and a cash reconciliation), not overwritten: the ledger keeps how
    the book got here. A symbol at zero shares is sold out of the book."""
    from . import ledger
    p = propose_positions(book, market, positions, cash)
    if p["unpriced"]:
        raise ValueError(f"no stored price for {', '.join(p['unpriced'])}: check the symbol, or record the "
                         "trade with its price")
    for r in p["trades"]:
        r.pop("price_from", None)
        r["trade_date"] = trade_date
        r.setdefault("note", "account saved: the difference, at the latest close")
    ledger.record(book, market, p["trades"], source="manual")
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


# how deep the ranking returned with the orders goes: the page's Candidates view, and the rank of a
# held stock that fell out of the book (its SELL reason). A view parameter; the strategy never reads it.
RANKING_ROWS = 200


def orders(book: str, market: str) -> dict:
    """The trades that turn the positions you hold into the strategy's book on the latest close."""
    from ..strategies import portfolio_strategies
    from . import baseline

    cls = portfolio_strategies()[book]
    acct = get_positions(book, market)
    held = acct["positions"]
    # the decision starts from what you actually hold (with a rank buffer, a held stock ranked between
    # top_n and hold_rank is kept); the replayed model book comes back beside it as `model_held`
    sel = baseline.current_selection(market, book, limit=RANKING_ROWS, held_now=set(held))
    target_rows = [r for r in sel.get("rows", []) if r.get("held") and r.get("weight_pct") is not None]
    price = {r["symbol"]: r["close"] for r in sel.get("rows", [])}
    rank = {r["symbol"]: r["rank"] for r in sel.get("rows", [])}
    model = set(sel.get("model_held") or [])
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
        r["rank"], r["in_model"] = rank.get(r["symbol"]), r["symbol"] in model
        d = r["target"] - r["held"]
        r["change"] = d
        r["action"] = ("SELL ALL" if r["target"] == 0 and r["held"] > 0 else
                       "BUY" if r["held"] == 0 and r["target"] > 0 else
                       "ADD" if d > 0 else "TRIM" if d < 0 else "HOLD")
        r["amount"] = round(d * r["price"], 2) if r["price"] else None
        r["reason"] = _reason(r, sel.get("hold_rank") or cls.top_n, sel.get("regime"))
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
        "hold_rank": sel.get("hold_rank"), "replayed_rebalances": sel.get("replayed_rebalances"),
        "drift": drift(set(held), model), "next_rebalance": next_rebalance(sel.get("as_of")),
        "top_n": getattr(cls, "top_n", None), "eligible": sel.get("eligible"),
        # the whole ranking the orders came from, so the page's Candidates view needs no second ranking
        "ranking": [{k: r[k] for k in ("rank", "symbol", "score", "close", "turnover")} for r in sel.get("rows", [])],
        "rows": rows,
    }


def _reason(r: dict, keep_within: int, regime: dict | None) -> str:
    """Why an order line says what it says, in the words of the rule that decided it."""
    rank, w = r.get("rank"), r.get("weight_pct")
    if r["action"] == "SELL ALL":
        if regime and not regime.get("on"):
            return "market filter off: the strategy holds cash"
        return (f"rank {rank}, outside the top {keep_within} it keeps" if rank
                else "no longer ranked (fails the liquidity, price or trend filter)")
    if r["action"] == "BUY":
        return f"new in the book at rank {rank}, target weight {w:g}%"
    if r["action"] in ("ADD", "TRIM"):
        return f"target weight {w:g}% is {r['target']:g} shares; you hold {r['held']:g}"
    return f"rank {rank}, target weight {w:g}%: no change" if rank else "no change"


def next_rebalance(as_of: str | None) -> str | None:
    """The last weekday of the month after `as_of`'s close (the month's own when `as_of` is not its last
    session): the strategy decides at the close of each month's last session. A weekday, not a holiday
    calendar, so the page says "on or before"."""
    if not as_of:
        return None
    d = pd.Timestamp(as_of)
    end = d + pd.offsets.BMonthEnd(0)
    if end <= d:
        end = d + pd.offsets.BMonthEnd(1)
    return end.date().isoformat()


def drift(held: set, model: set) -> dict:
    """Where your holdings and the model book (the strategy replayed from an empty book) part."""
    return {"model_only": sorted(model - held), "held_only": sorted(held - model)}


def confirm(book: str, market: str) -> dict:
    """Store the rebalance as computed now -- its targets and orders -- so the trades that execute it
    can be linked to it (`book_trades.rebalance_id`) and read against it later."""
    from . import ledger
    if ledger.open_rebalance(book, market):
        raise ValueError("a rebalance is still open: complete it before starting the next")
    o = orders(book, market)
    targets = [{"symbol": r["symbol"], "weight_pct": r["weight_pct"], "shares": r["target"], "price": r["price"]}
               for r in o["rows"] if r["target"] > 0]
    rid = ledger.save_rebalance(book, market, o["as_of"], o["spec_id"], targets, o["rows"])
    return {"id": rid, "orders": o}
