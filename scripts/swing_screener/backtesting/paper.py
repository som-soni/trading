"""Paper books: each strategy's forward record, traded on the ledger without money.

A paper book is a book (`books.paper`) whose ledger the `paper` job fills by itself, with simulated
trades at the next session's open after each decision, charged the strategy's own cost per side. It is
the clean test the backtest stages cannot give for rules refined on history (CLAUDE.md, "Every year up to
October 2026 informed some earlier decision"): every decision is made on a close before the price it
fills at exists.

    portfolio strategies   on the last session of each month (and on the day the book starts) the job
                           stores the targets as a rebalance -- the strategy's own selection, from what
                           the paper book holds -- and fills it at the next session's open: sell what
                           left, then size each target to its weight of the account valued at that open,
                           as the backtest's `fill=next_open` does (baseline.run's `execute`)
    signal strategies      each tradeable setup of the strategy's run on a session becomes an entry at
                           the next session's open, sized by the market's risk per trade on the setup's
                           stop; the open-position tracker (tracker.py) manages it, and an exit it reports
                           fills at the stop (a stop reached intraday) or at the next open (a close-based
                           exit). Partial sales of an exit ladder are not paper-traded: the position exits
                           whole.

Pending decisions wait in `paper_orders` until the session they fill on is stored. The paper book's
ledger rows carry source `paper`; the account form and Kite never touch a paper book.
"""

from __future__ import annotations

import json
import math
from datetime import date

import pandas as pd

from ..config import MARKETS
from ..marketdata import db
from . import ledger

PAPER_SUFFIX = "@paper"

SCHEMA = """
CREATE TABLE IF NOT EXISTS books (
    book TEXT NOT NULL,
    market TEXT NOT NULL,
    strategy TEXT NOT NULL,          -- the strategy the book runs
    paper BOOLEAN NOT NULL DEFAULT false,
    started DATE,
    capital DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (book, market)
);
CREATE TABLE IF NOT EXISTS paper_orders (
    id BIGSERIAL PRIMARY KEY,
    book TEXT NOT NULL,
    market TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('entry', 'exit', 'rebalance')),
    symbol TEXT,
    signal_date DATE NOT NULL,       -- the close the decision was made on; it fills at the next open
    stop DOUBLE PRECISION,
    target DOUBLE PRECISION,
    setup TEXT,
    entry_rule TEXT,
    meta JSONB,
    rebalance_id BIGINT REFERENCES book_rebalances(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'filled', 'skipped')),
    filled_date DATE,
    note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS paper_orders_book ON paper_orders (book, market, status);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def strategy_of(book: str, market: str) -> str:
    """The strategy a book runs: its `books` row, or the book's own name (a real book is named for its
    strategy)."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT strategy FROM books WHERE book=%s AND market=%s", (book, market))
        r = cur.fetchone()
    return r[0] if r else book


def paper_books(market: str) -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT book, strategy, started, capital FROM books WHERE market=%s AND paper ORDER BY strategy",
                    (market,))
        return [{"book": b, "strategy": s, "started": d.isoformat() if d else None, "capital": c}
                for b, s, d, c in cur.fetchall()]


def is_paper(book: str, market: str) -> bool:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT paper FROM books WHERE book=%s AND market=%s", (book, market))
        r = cur.fetchone()
    return bool(r and r[0])


def kind_of(strategy: str) -> str:
    from ..strategies import _REGISTRY, portfolio_strategies
    if strategy in _REGISTRY:
        return "signal"
    if strategy in ("momentum_dual_combo", "dual_momentum", "ma_trend"):
        return strategy
    cls = portfolio_strategies().get(strategy)
    if cls is not None and hasattr(cls, "lookback") and getattr(cls, "live_selection", True) is not False:
        return "ranking"
    raise ValueError(f"{strategy} cannot be paper-traded yet: it has no live selection")


# ------------------------------------------------------------------ prices

def sessions(market: str) -> pd.DatetimeIndex:
    """The market's stored sessions: the benchmark's dates."""
    from ..marketdata import cache
    b = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    return pd.DatetimeIndex(b.index) if b is not None else pd.DatetimeIndex([])


def _asset_keys(market: str) -> set:
    from . import dual_momentum as dm
    return {k for k, _ in dm.ASSETS[market]} | {dm.SAFE[market][0]}


def bars(market: str, symbol: str) -> pd.DataFrame | None:
    """open / close for a stock, or for one of dual momentum's assets (an index level, priced as its
    backtest prices it: no open, so it fills at the session's close level)."""
    from ..marketdata import cache
    if symbol in _asset_keys(market):
        from . import dual_momentum as dm
        s = dm.load_assets(market, [symbol])[symbol]
        return pd.DataFrame({"open": s, "close": s})
    d = cache.load_cached(market, symbol)
    return None if d is None or d.empty else d[["open", "close"]].astype(float)


def _price_on(market: str, symbol: str, day: pd.Timestamp, field: str = "open", cache_: dict | None = None):
    cache_ = {} if cache_ is None else cache_
    if symbol not in cache_:
        cache_[symbol] = bars(market, symbol)
    d = cache_[symbol]
    if d is None:
        return None
    if day in d.index and pd.notna(d.at[day, field]):
        return float(d.at[day, field])
    before = d.loc[:day, "close"].dropna()
    return float(before.iloc[-1]) if len(before) else None


# ------------------------------------------------------------------ books

def create(strategy: str, market: str, capital: float | None = None) -> dict:
    """Start a paper book for `strategy`: its capital as the opening cash, started on the latest stored
    session. A portfolio strategy's first rebalance is decided on that close."""
    init_schema()
    kind_of(strategy)             # refuses a strategy with no live selection
    book = strategy + PAPER_SUFFIX
    cap = float(capital or MARKETS[market].account_size)
    if cap <= 0:
        raise ValueError("capital must be positive")
    day = sessions(market)[-1].date()
    with db.get_connection().cursor() as cur:
        cur.execute("INSERT INTO books (book, market, strategy, paper, started, capital) VALUES (%s,%s,%s,true,%s,%s) "
                    "ON CONFLICT (book, market) DO NOTHING RETURNING book", (book, market, strategy, day, cap))
        if cur.fetchone() is None:
            raise ValueError(f"{strategy} already has a paper book in {market}")
    ledger.record(book, market, [{"side": "CASH", "amount": cap, "trade_date": day.isoformat(),
                                  "note": "paper book: starting capital"}], source="paper")
    return {"book": book, "market": market, "strategy": strategy, "started": day.isoformat(), "capital": cap}


# ------------------------------------------------------------------ decisions

def _targets(strategy: str, market: str, held: dict) -> tuple[str, str | None, dict]:
    """(as_of, spec_id, symbol -> weight) the strategy's own live selection points at on the latest close,
    starting from what the paper book holds."""
    from ..strategies import portfolio_strategies
    k = kind_of(strategy)
    if k == "ranking":
        from . import baseline
        sel = baseline.current_selection(market, strategy, held_now=set(held))
        rows = [r for r in sel.get("rows", []) if r.get("held") and r.get("weight_pct")]
        tot = sum(r["weight_pct"] for r in rows) or 1.0
        return sel.get("as_of"), sel.get("spec_id"), {r["symbol"]: r["weight_pct"] / tot for r in rows}
    if k == "ma_trend":
        from . import ma_trend
        sel = ma_trend.current_selection(market, upto=sessions(market)[-1])
        return sel["as_of"], sel["spec_id"], sel["weights"]
    if k == "dual_momentum":
        from . import dual_momentum as dm
        cls = portfolio_strategies()["dual_momentum"]
        p = dm.current_pick(market, cls.lookback_months)
        return p["as_of"], cls.spec_id(), {p["pick"]: 1.0}
    from . import combination
    o = combination.current_orders(market, None, holdings=held)
    w = {}
    for x in o["orders"]:
        w[x["symbol"]] = w.get(x["symbol"], 0.0) + x["account_pct"] / 100
    return o["as_of"], o["spec_id"], w


def _cost_bps(strategy: str, market: str, symbol: str) -> float:
    """The strategy's own cost per side. The combination charges each sleeve's: the dual sleeve's on its
    asset, the momentum sleeve's on a stock."""
    from ..strategies import portfolio_strategies
    ps_ = portfolio_strategies()
    if strategy == "momentum_dual_combo":
        from . import combination
        sleeve = combination.DUAL_SLEEVE if symbol in _asset_keys(market) else combination.MOMENTUM_SLEEVE
        return float(getattr(ps_[sleeve], "cost_bps", 0.0))
    if strategy in ps_:
        return float(getattr(ps_[strategy], "cost_bps", 0.0))
    from .tracker import fee_rate_for
    return fee_rate_for(strategy, market) * 10_000 + MARKETS[market].slippage_bps


def _pending(book: str, market: str) -> list[dict]:
    cols = ("id", "kind", "symbol", "signal_date", "stop", "target", "setup", "entry_rule", "meta", "rebalance_id")
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {', '.join(cols)} FROM paper_orders WHERE book=%s AND market=%s AND status='pending' "
                    "ORDER BY signal_date, id", (book, market))
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def _order(book, market, kind, signal_date, **kw) -> int:
    with db.get_connection().cursor() as cur:
        cur.execute("INSERT INTO paper_orders (book, market, kind, symbol, signal_date, stop, target, setup, entry_rule, "
                    "meta, rebalance_id, note) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                    (book, market, kind, kw.get("symbol"), signal_date, kw.get("stop"), kw.get("target"), kw.get("setup"),
                     kw.get("entry_rule"), json.dumps(kw["meta"]) if kw.get("meta") else None, kw.get("rebalance_id"),
                     kw.get("note")))
        return cur.fetchone()[0]


def _close_order(order_id: int, status: str, day, note: str | None = None) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE paper_orders SET status=%s, filled_date=%s, note=coalesce(%s, note) WHERE id=%s",
                    (status, day, note, order_id))


def _next_session(sess: pd.DatetimeIndex, d) -> pd.Timestamp | None:
    i = sess.searchsorted(pd.Timestamp(d), side="right")
    return sess[i] if i < len(sess) else None


def fill_rebalance(book: str, market: str, strategy: str, weights: dict, day: pd.Timestamp, rid: int | None,
                   px_cache: dict) -> list[dict]:
    """The trades that put the paper book on `weights` at `day`'s open, as the backtest's next-open fill does:
    everything that left the book is sold, then each target is sized to its weight of the account valued
    at that open, in whole shares. Sells come first, so their cash pays for the buys."""
    acct = ledger.holdings_of(book, market)
    held, cash = dict(acct["positions"]), acct["cash"]
    px = {s: _price_on(market, s, day, "open", px_cache) for s in set(held) | set(weights)}
    equity = cash + sum(n * (px[s] or 0.0) for s, n in held.items())
    rows = []
    want = {s: (int(equity * w // px[s]) if px.get(s) else None) for s, w in weights.items()}
    for s, n in sorted(held.items()):
        target = want.get(s, 0)
        if target is None or not px.get(s) or target >= n:
            continue
        sh = n - target
        rows.append({"side": "SELL", "symbol": s, "shares": sh, "price": px[s],
                     "costs": round(sh * px[s] * _cost_bps(strategy, market, s) / 10_000, 4)})
        cash += sh * px[s] - rows[-1]["costs"]
    for s, target in sorted(want.items()):
        n = held.get(s, 0.0)
        if target is None or target <= n:
            continue
        p, bps = px[s], _cost_bps(strategy, market, s)
        sh = min(target - n, int(cash // (p * (1 + bps / 10_000)))) if p else 0
        if sh < 1:
            continue
        rows.append({"side": "BUY", "symbol": s, "shares": sh, "price": p, "costs": round(sh * p * bps / 10_000, 4)})
        cash -= sh * p + rows[-1]["costs"]
    for r in rows:
        r.update(trade_date=day.date().isoformat(), rebalance_id=rid, note=f"paper: rebalance #{rid} at the open")
    return rows


def step(book: str, market: str, today: date | None = None) -> dict:
    """One day of a paper book: fill what is pending at the sessions now stored, then record what the
    strategy decides on the latest close. Idempotent: a decision is stored once per close, a fill once."""
    from . import tracker
    init_schema()
    strategy = strategy_of(book, market)
    kind = kind_of(strategy)
    sess = sessions(market)
    latest = sess[-1]
    px_cache: dict = {}
    done = {"filled": 0, "skipped": 0, "decided": 0}

    # ---- 1. fills: each pending order at the first session after its decision, once that is stored
    for o in _pending(book, market):
        day = _next_session(sess, o["signal_date"])
        if day is None:
            continue
        if o["kind"] == "rebalance":
            with db.get_connection().cursor() as cur:
                cur.execute("SELECT targets FROM book_rebalances WHERE id=%s", (o["rebalance_id"],))
                tg = cur.fetchone()[0]
            weights = {t["symbol"]: t["weight_pct"] / 100 for t in tg}
            rows = fill_rebalance(book, market, strategy, weights, day, o["rebalance_id"], px_cache)
            ledger.record(book, market, rows, source="paper")
            _close_order(o["id"], "filled", day.date())
            done["filled"] += 1
            continue
        acct = ledger.holdings_of(book, market)
        if o["kind"] == "exit":
            n = acct["positions"].get(o["symbol"], 0)
            p = _price_on(market, o["symbol"], day, "open", px_cache)
            if n and p:
                ledger.record(book, market, [{"side": "SELL", "symbol": o["symbol"], "shares": n, "price": p,
                                              "costs": round(n * p * _cost_bps(strategy, market, o["symbol"]) / 10_000, 4),
                                              "trade_date": day.date().isoformat(), "note": f"paper: {o['setup']} at the open"}],
                              source="paper")
            _close_order(o["id"], "filled" if n else "skipped", day.date())
            done["filled" if n else "skipped"] += 1
            continue
        # entry: the next open, sized on the setup's stop by the market's risk per trade
        cfg = MARKETS[market]
        p = _price_on(market, o["symbol"], day, "open", px_cache)
        why = None
        if not p:
            why = "no open stored"
        elif o["stop"] is None or p <= o["stop"]:
            why = "opened at or below the stop"
        elif o["target"] and p >= o["target"]:
            why = "opened past the target"
        elif o["symbol"] in acct["positions"]:
            why = "already held"
        elif len(acct["positions"]) >= cfg.max_open_positions:
            why = "all position slots full"
        sh = 0
        if why is None:
            marks = {s: _price_on(market, s, day, "open", px_cache) or 0.0 for s in acct["positions"]}
            equity = acct["cash"] + sum(n * marks[s] for s, n in acct["positions"].items())
            bps = _cost_bps(strategy, market, o["symbol"])
            sh = int(equity * cfg.risk_pct // (p - o["stop"]))
            sh = min(sh, int(equity * cfg.max_position_pct // p), int(acct["cash"] // (p * (1 + bps / 10_000))))
            if sh < 1:
                why = "not enough cash"
        if why:
            _close_order(o["id"], "skipped", day.date(), why)
            done["skipped"] += 1
            continue
        ledger.record(book, market, [{"side": "BUY", "symbol": o["symbol"], "shares": sh, "price": p,
                                      "costs": round(sh * p * bps / 10_000, 4), "trade_date": day.date().isoformat(),
                                      "initial_stop": o["stop"], "target": o["target"], "setup": o["setup"],
                                      "entry_rule": o["entry_rule"], "meta": o["meta"],
                                      "note": f"paper: {o['setup'] or 'setup'} of {o['signal_date']} at the open"}],
                      source="paper")
        _close_order(o["id"], "filled", day.date())
        done["filled"] += 1

    # ---- 2. decisions on the latest close
    pending_syms = {(o["kind"], o["symbol"]) for o in _pending(book, market)}
    if kind != "signal":
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT max(as_of) FROM book_rebalances WHERE book=%s AND market=%s", (book, market))
            last = cur.fetchone()[0]
        # the strategy trades on the last session of each month: the next weekday is in a new month
        month_end = (latest + pd.offsets.BDay(1)).month != latest.month
        # a month-end the job missed (or a holiday on the month's last weekday) is decided late, on the
        # first close after it, rather than skipped for a month
        missed = last is not None and (pd.Timestamp(last).to_period("M") < latest.to_period("M") - 1
                                       or (pd.Timestamp(last).to_period("M") == latest.to_period("M") - 1
                                           and pd.Timestamp(last) + pd.offsets.BDay(1) < latest.replace(day=1)))
        if last is None or (month_end and last < latest.date()) or missed:
            held = ledger.holdings_of(book, market)["positions"]
            # decide on the calendar's latest session: stock prices for a session are often stored before
            # the index series the calendar reads, and a selection dated a session ahead never matched
            # `latest`, so the decision was dropped every day (vol-scaled and quality momentum sat in cash
            # from 2026-11-09)
            from ..marketdata import asof
            with asof.boundary(latest, "paper decision"):
                as_of, spec_id, weights = _targets(strategy, market, held)
            if as_of == latest.date().isoformat():
                tg = [{"symbol": s, "weight_pct": round(w * 100, 4)} for s, w in sorted(weights.items())]
                rid = ledger.save_rebalance(book, market, as_of, spec_id, tg, [], note="paper")
                _order(book, market, "rebalance", as_of, rebalance_id=rid, note="fills at the next open")
                done["decided"] += 1
        return done

    # signal strategy: the tracker's exits, then the latest run's tradeable setups
    tracker.refresh(market, books=[book])
    for st in tracker.statuses(market):
        if st["book"] != book or st["status"] not in ("stopped", "exit_next_open"):
            continue
        sym, n = st["symbol"], ledger.holdings_of(book, market)["positions"].get(st["symbol"], 0)
        if not n or ("exit", sym) in pending_syms:
            continue
        if st["status"] == "stopped" and st["exit_date"] and st["exit_price"]:
            ledger.record(book, market, [{"side": "SELL", "symbol": sym, "shares": n, "price": st["exit_price"],
                                          "costs": round(n * st["exit_price"] * _cost_bps(strategy, market, sym) / 10_000, 4),
                                          "trade_date": st["exit_date"], "note": f"paper: {st['reason']} at the stop"}],
                          source="paper")
            continue
        _order(book, market, "exit", st["exit_date"] or st["as_of"], symbol=sym, setup=st["reason"],
               note="sells at the next open")
        done["decided"] += 1
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(run_id) FROM universe_history WHERE market=%s AND strategy=%s", (market, strategy))
        run = cur.fetchone()[0]
        if not run:
            return done
        cur.execute("SELECT symbol, full_row FROM universe_history WHERE market=%s AND strategy=%s AND run_id=%s",
                    (market, strategy, run))
        rows = cur.fetchall()
        cur.execute("SELECT count(*) FROM paper_orders WHERE book=%s AND market=%s AND meta->>'run'=%s",
                    (book, market, run))
        seen = cur.fetchone()[0]
    run_day = pd.Timestamp(run[:10])
    signal_day = sess[sess <= run_day][-1] if (sess <= run_day).any() else None
    started = _started(book, market)
    if seen or signal_day is None or (started and signal_day.date() < started):
        return done
    held = ledger.holdings_of(book, market)["positions"]
    for sym, fr in rows:
        if fr.get("tradeable") is not True or sym in held or ("entry", sym) in pending_syms:
            continue
        stop, entry, tr = fr.get("stop"), fr.get("entry"), fr.get("target_r")
        if not stop:
            continue
        target = float(entry) + float(tr) * (float(entry) - float(stop)) if entry and tr and float(entry) > float(stop) else None
        meta = {"run": run, **{v: fr[k] for k, v in (("box_top", "box_top"), ("box_bottom", "box_bottom"),
                                                     ("pivot", "pivot"), ("box_top_date", "setup_start")) if fr.get(k)}}
        _order(book, market, "entry", signal_day.date(), symbol=sym, stop=float(stop), target=target,
               setup=fr.get("decision"), entry_rule=fr.get("strategy_setup"), meta=meta, note="buys at the next open")
        done["decided"] += 1
    return done


def _started(book: str, market: str):
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT started FROM books WHERE book=%s AND market=%s", (book, market))
        r = cur.fetchone()
    return r[0] if r else None


def run(market: str) -> dict:
    """Every paper book of the market, one day forward."""
    out = {}
    for b in paper_books(market):
        out[b["book"]] = step(b["book"], market)
    return out


# ------------------------------------------------------------------ the forward record

def equity_curve(trades: list[dict], closes: pd.DataFrame) -> pd.Series:
    """The book's value each session: the cash and shares its ledger held at that session's end, at the
    session's closes (the last close carried over a gap). Pure arithmetic, so it is tested on its own."""
    if closes.empty:
        return pd.Series(dtype=float)
    idx = closes.index
    cash = pd.Series(0.0, index=idx)
    shares = pd.DataFrame(0.0, index=idx, columns=closes.columns)
    for t in trades:
        d = pd.Timestamp(t["trade_date"])
        on = idx >= d
        if not on.any():
            continue
        fee = float(t.get("costs") or 0)
        if t["side"] == "CASH":
            cash[on] += float(t.get("amount") or 0)
        elif t["side"] in ("BUY", "OPEN"):
            shares.loc[on, t["symbol"]] += float(t["shares"])
            cash[on] -= (float(t["shares"]) * float(t["price"]) if t["side"] == "BUY" else 0.0) + fee
        elif t["side"] == "SELL":
            shares.loc[on, t["symbol"]] -= float(t["shares"])
            cash[on] += float(t["shares"]) * float(t["price"]) - fee
    return cash + (shares * closes.ffill().fillna(0.0)).sum(axis=1)


def record(book: str, market: str) -> dict:
    """The paper book's forward record: its value each session from the start against the benchmark rebased
    to the same capital, every trade, and the decisions still pending."""
    from ..marketdata import cache
    rows = ledger.trades(book, market)
    started = _started(book, market)
    if not rows or started is None:
        return {"book": book, "market": market, "equity": [], "benchmark": [], "trades": [], "pending": []}
    sess = sessions(market)
    idx = sess[sess >= pd.Timestamp(started)]
    syms = sorted({t["symbol"] for t in rows if t["symbol"]})
    closes = pd.DataFrame(index=idx)
    got = {s: bars(market, s) for s in syms}
    full = pd.DataFrame({s: d["close"] for s, d in got.items() if d is not None})
    if not full.empty:
        closes = full.reindex(full.index.union(idx)).ffill().reindex(idx)
    eq = equity_curve(rows, closes) if len(idx) else pd.Series(dtype=float)
    cap = float(sum(t["amount"] or 0 for t in rows if t["side"] == "CASH"))
    b = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    bench = b["close"].astype(float).reindex(idx).ffill() if b is not None else pd.Series(dtype=float)
    bench = bench / bench.iloc[0] * cap if len(bench) and bench.iloc[0] else bench
    dd = float((eq / eq.cummax() - 1).min() * 100) if len(eq) else None
    return {"book": book, "market": market, "strategy": strategy_of(book, market), "started": started.isoformat(),
            "capital": cap, "as_of": idx[-1].date().isoformat() if len(idx) else None,
            "equity": [[d.date().isoformat(), round(float(v), 2)] for d, v in eq.items()],
            "benchmark": [[d.date().isoformat(), round(float(v), 2)] for d, v in bench.items() if pd.notna(v)],
            "benchmark_name": MARKETS[market].benchmark_ticker,
            "return_pct": round((float(eq.iloc[-1]) / cap - 1) * 100, 2) if len(eq) and cap else None,
            "benchmark_pct": round((float(bench.iloc[-1]) / cap - 1) * 100, 2) if len(bench) and cap else None,
            "max_drawdown_pct": round(dd, 2) if dd is not None and not math.isnan(dd) else None,
            "trades": rows[::-1], "account": ledger.holdings_of(book, market), "pending": _pending(book, market)}
