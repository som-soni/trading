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
    signal strategies      each session's live run stores every tradeable setup as the order its backtest
                           would place (`order` in the run's rows: levels, buy-stop or open order, buy
                           range, stop cap, expiry -- screening/pipeline.py). Each day the job replays
                           those orders through the backtest's own simulator (`portfolio_sim.simulate`
                           with the strategy's `backtest_args`: exits, slots, open-risk cap, progressive
                           exposure, costs, the market filter's cancels) from the book's start, and writes
                           the fills that are new to the ledger -- buys, partial sales and exits alike.
                           Until 2026-11-14 every tradeable row was bought at the next open at a flat 1%
                           risk with the market's 10 slots, so a buy-stop setup (most of minervini's) was
                           bought whether or not it triggered, and the record did not test the strategy
                           that was backtested (Minervini review B3).

Pending decisions wait in `paper_orders` until the session they fill on is stored. The paper book's
ledger rows carry source `paper`; the account form and Kite never touch a paper book.
"""

from __future__ import annotations

import json
import math
from datetime import date

import pandas as pd

from ..config import MARKETS
from ..marketdata import corporate_actions, db
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
    strategy decides on the latest close. Idempotent: a decision is stored once per close, a fill once.
    A signal strategy's book replays its live orders instead (`_step_signal`)."""
    init_schema()
    strategy = strategy_of(book, market)
    kind = kind_of(strategy)
    sess = sessions(market)
    latest = sess[-1]
    px_cache: dict = {}
    done = {"filled": 0, "skipped": 0, "decided": 0}

    if kind == "signal":
        return _step_signal(book, market, strategy, sess, done)

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
    # ---- 2. decisions on the latest close
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


def _live_signals(market: str, strategy: str, sess: pd.DatetimeIndex, started) -> list:
    """The orders the strategy's live runs placed since the book started, as backtest Signals: each session's
    latest run, its rows the live screen called tradeable (or demoted only for the live list's per-sector cap,
    which no backtest applies), each with the order the backtest would place (`order`, screening/pipeline.py).
    A row without `order` (a run before 2026-11-14) cannot be replayed and is left out."""
    from .portfolio_sim import Signal
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT run_id, symbol, full_row FROM universe_history WHERE market=%s AND strategy=%s "
                    "AND run_id >= %s ORDER BY run_id", (market, strategy, started.isoformat()))
        rows = cur.fetchall()
    by_day: dict = {}
    for run, sym, fr in rows:
        run_day = pd.Timestamp(run[:10])
        before = sess[sess <= run_day]
        if not len(before) or before[-1].date() < started:
            continue
        by_day.setdefault(before[-1], {}).setdefault(run, []).append((sym, fr))
    out = []
    for day, runs in sorted(by_day.items()):
        for sym, fr in runs[max(runs)]:           # the session's latest run
            o = fr.get("order")
            if not o or not (fr.get("tradeable") is True or fr.get("decision") == "WATCH - SECTOR LIMIT"):
                continue
            meta = dict(o.get("meta") or {})
            if o.get("rs") is not None:
                meta["rs"] = int(o["rs"])        # as filter_min_rs stamps it, for the RS ranking
            out.append(Signal(date=day, symbol=sym, setup=o["setup"], entry=float(o["entry"]), stop=float(o["stop"]),
                              target=float(o["target"]) if o.get("target") is not None else float("nan"),
                              decision=o.get("decision") or fr.get("decision"), quality=float(o.get("quality") or 0),
                              meta=meta))
    return out


def replay(book: str, market: str, strategy: str, sess: pd.DatetimeIndex | None = None):
    """The paper book's trading as the strategy's backtest would have done it: its live orders since the book
    started, through `portfolio_sim.simulate` with the strategy's own settings (backtest.sim_settings_for) and
    the book's capital, on stored bars to the latest session. None when there is nothing to replay."""
    import dataclasses
    from ..core import indicators as ind
    from ..marketdata import cache, corporate_actions
    from ..strategies.variants import market_rules
    from . import spec as spec_mod
    from .backtest import rerank_signals, sim_settings_for
    from .portfolio_sim import simulate
    sess = sessions(market) if sess is None else sess
    started = _started(book, market)
    if started is None or not len(sess):
        return None
    signals = _live_signals(market, strategy, sess, started)
    if not signals:
        return None
    cap = _capital(book, market)
    with market_rules(strategy, market):
        st = sim_settings_for(strategy, market)
        cfg = dataclasses.replace(st["cfg"], account_size=float(cap or st["cfg"].account_size))
        prices = {}
        for sym in sorted({s.symbol for s in signals}):
            raw = cache.load_cached(market, sym)
            if raw is not None and not raw.empty:
                prices[sym] = ind.enrich_daily(raw, corporate_actions.credits_for(market, sym, raw))   # as the backtest
        signals = [s for s in signals if s.symbol in prices]
        if not signals:
            return None
        if st["spec_costs"]:
            signals = spec_mod.annotate_costs(signals, prices, market)
        if st["rank_by"] == "rs":
            signals = spec_mod.rank_rs_then_tightness(signals)
        elif st["rank_by"] != "setup":
            signals = rerank_signals(signals, prices, st["rank_by"])
        start = sess[sess >= pd.Timestamp(started)][0]
        credits = corporate_actions.Credits.for_market(market, list(prices))
        return simulate(signals, prices, cfg, start, end=sess[-1], credits=credits, **st["simulate"])


def _step_signal(book: str, market: str, strategy: str, sess: pd.DatetimeIndex, done: dict) -> dict:
    """A signal strategy's paper day: replay its live orders (`replay`) and write the fills the ledger does not
    have yet. The replay is deterministic on stored data, so each day repeats the earlier fills and adds the
    new session's; a recorded fill the replay no longer makes (a revised bar, a re-run screen) is reported as
    `diverged`, never rewritten -- the ledger is a record."""
    from collections import Counter
    from . import tracker
    for o in _pending(book, market):         # the old next-open entries: superseded by the replay
        if o["kind"] in ("entry", "exit"):
            _close_order(o["id"], "skipped", None, "superseded: signal books replay the backtest's order rules")
    res = replay(book, market, strategy, sess)
    done.update(diverged=0)
    if res is None:
        return done
    have = Counter((r["trade_date"], r["symbol"], r["side"], round(float(r["shares"]), 6))
                   for r in ledger.trades(book, market) if r["source"] == "paper" and r["side"] in ("BUY", "SELL"))
    first = {}                               # (symbol, entry date) -> the trade, for a buy's levels
    for t in res.trades:
        first[(t.symbol, pd.Timestamp(t.entry_date).date().isoformat())] = t
    rows, seen = [], Counter()
    for day, sym, side, n, px, costs, _at in res.fills:
        d = pd.Timestamp(day).date().isoformat()
        key = (d, sym, side, round(float(n), 6))
        seen[key] += 1
        if seen[key] <= have.get(key, 0):
            continue                          # already in the ledger
        row = {"side": side, "symbol": sym, "shares": int(n), "price": round(float(px), 6),
               "costs": round(float(costs), 4), "trade_date": d}
        t = first.get((sym, d)) if side == "BUY" else None
        if t is not None:
            row.update(initial_stop=float(t.initial_stop), setup=t.setup, entry_rule=t.setup,
                       target=float(t.target) if t.target == t.target else None,
                       meta={k: v for k, v in t.meta.items() if not str(k).startswith("_")
                             and isinstance(v, (str, int, float, bool, type(None)))},
                       note=f"paper: {t.setup} of {pd.Timestamp(t.signal_date).date() if t.signal_date is not None else '?'}")
        else:
            row["note"] = f"paper: {side.lower()}"
        rows.append(row)
    done["diverged"] = sum(max(0, n - seen.get(k, 0)) for k, n in have.items())
    if rows:
        ledger.record(book, market, rows, source="paper")
        done["filled"] += len(rows)
    tracker.refresh(market, books=[book])     # the open positions' status, for the Trade desk
    return done


def _capital(book: str, market: str):
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT capital FROM books WHERE book=%s AND market=%s", (book, market))
        r = cur.fetchone()
    return r[0] if r else None


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
    # the strategy's own benchmark, as its backtest is judged (baseline.benchmark_for); the calendar
    # (`sessions`) stays on the market's benchmark
    from .baseline import benchmark_for
    btk, bname = benchmark_for(strategy_of(book, market), market)
    b = cache.load_cached(market, btk)
    bench = b["close"].astype(float).reindex(idx).ffill() if b is not None else pd.Series(dtype=float)
    bench = bench / bench.iloc[0] * cap if len(bench) and bench.iloc[0] else bench
    dd = float((eq / eq.cummax() - 1).min() * 100) if len(eq) else None
    return {"book": book, "market": market, "strategy": strategy_of(book, market), "started": started.isoformat(),
            "capital": cap, "as_of": idx[-1].date().isoformat() if len(idx) else None,
            "equity": [[d.date().isoformat(), round(float(v), 2)] for d, v in eq.items()],
            "benchmark": [[d.date().isoformat(), round(float(v), 2)] for d, v in bench.items() if pd.notna(v)],
            "benchmark_name": f"{bname} ({btk})",
            "return_pct": round((float(eq.iloc[-1]) / cap - 1) * 100, 2) if len(eq) and cap else None,
            "benchmark_pct": round((float(bench.iloc[-1]) / cap - 1) * 100, 2) if len(bench) and cap else None,
            "max_drawdown_pct": round(dd, 2) if dd is not None and not math.isnan(dd) else None,
            "trades": rows[::-1], "account": ledger.holdings_of(book, market), "pending": _pending(book, market)}
