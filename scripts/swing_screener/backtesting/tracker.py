"""Open-position tracker: each open signal trade, managed by its strategy's own exit on stored bars.

Live, a signal strategy only shows new setups (Today's setups). Once you have bought one, its exit --
a trailing stop, a close below an average, a Darvas box, a weekly line -- is positional: it depends on
every bar since the entry. This module replays those bars through the SAME code the backtest manages a
position with (`portfolio_sim.exit_frames`, `manage_entry_bar`, `manage_exit`), under the policy the
strategy was measured with (`backtest.exit_policy_for`, from its `backtest_args`), and stores where the
position stands after the latest close:

    hold            nothing fired; the stop is where it was
    stop_raised     the stop moved up on the latest session -- move your stop order
    partial         the exit ladder sold part of the position on the latest session
    exit_next_open  a close-based exit fired (or one is queued for the open): sell at the next open
    sell_stop_armed the ma_low exit is armed: the latest session closed below the line, so the next one
                    sells if it trades under that session's low -- rest a sell-stop there for one session
    stopped         the stop or target was reached intraday: your resting order filled, or sell at the open

An open signal trade is a book's holding whose opening BUY carries an `initial_stop` (recorded when a
setup is "taken"; ledger.py). The `positions` job (jobs/registry.py, screening layer, after `prices`)
refreshes the table daily, inside `cache.offline()`: stored data only. It never decides a trade -- it
reads the rules you entered under -- and it never places an order.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

import pandas as pd

from ..config import MARKETS
from ..marketdata import db
from . import portfolio_sim as ps

SCHEMA = """
CREATE TABLE IF NOT EXISTS position_status (
    trade_id BIGINT PRIMARY KEY REFERENCES book_trades(id) ON DELETE CASCADE,   -- the opening BUY
    book TEXT NOT NULL,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    as_of DATE NOT NULL,              -- the last stored session the exit was run through
    entry_date DATE NOT NULL,
    entry_price DOUBLE PRECISION NOT NULL,
    shares DOUBLE PRECISION NOT NULL,
    initial_stop DOUBLE PRECISION NOT NULL,
    stop DOUBLE PRECISION,            -- the stop for the next session
    status TEXT NOT NULL,
    reason TEXT,                      -- the exit's own name (STOP, TREND_EXIT, CLIMAX ...)
    exit_date DATE,
    exit_price DOUBLE PRECISION,
    last_close DOUBLE PRECISION,
    r_now DOUBLE PRECISION,           -- (last close - entry) / (entry - initial stop)
    dist_pct DOUBLE PRECISION,        -- (last close - stop) / last close, percent
    policy TEXT,                      -- the exit policy's label
    stops JSONB,                      -- [[date, stop]] after each session
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- the shares the exit leaves open after the latest session: below `shares` when the ladder sold part
ALTER TABLE position_status ADD COLUMN IF NOT EXISTS open_shares DOUBLE PRECISION;
"""

STATUS_TEXT = {
    "hold": "Hold",
    "stop_raised": "Stop raised — move your stop order",
    "partial": "Sell part at the next open",
    "exit_next_open": "Exit triggered — sell at the next open",
    "sell_stop_armed": "Closed below the line — rest a sell-stop at today's low for the next session",
    "stopped": "Stop reached — sell at the open unless your stop order filled",
}


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


@dataclass
class Opening:
    """An open signal trade as the ledger records it."""
    trade_id: int
    book: str
    market: str
    symbol: str
    entry_date: pd.Timestamp
    entry_price: float
    shares: float
    initial_stop: float
    target: float
    setup: str
    meta: dict


def track(df: pd.DataFrame, policy: "ps.ExitPolicy", cfg, *, symbol: str, entry_date, entry_price: float,
          initial_stop: float, shares: float, target: float = math.inf, meta: dict | None = None,
          fee_rate: float = 0.0, entry_at: int = ps.INTRADAY, setup: str = "", frame: pd.DataFrame | None = None) -> dict:
    """Replay `df` (enriched daily bars) from `entry_date` through the strategy's exit, exactly as
    `simulate` manages a held position, and say where the position stands after the last bar.

    `entry_at` is the moment of the fill: INTRADAY (a buy-stop, or a buy at the open -- the rest of the
    entry bar can still reach the stop, as in the backtest) or AT_CLOSE (a close order: the entry bar is
    not tested). Fills here are the raw levels: your own fills carry the slippage and costs.

    `frame`: `df` already through `ps.exit_frames` for this policy -- a caller replaying many entries in one
    stock (the chart's setup outcomes, strategies/setup_outcomes.py) builds it once."""
    entry_date = pd.Timestamp(entry_date)
    if frame is None:
        frame = ps.exit_frames({symbol: df}, policy)[symbol]
    bars = frame.loc[frame.index >= entry_date]
    pos = ps.PortfolioTrade(symbol=symbol, setup=setup, decision="TAKEN", entry_date=entry_date,
                            entry_price=float(entry_price), stop=float(initial_stop),
                            initial_stop=float(initial_stop), target=float(target if target else math.inf),
                            shares=int(shares) if float(shares).is_integer() else shares, meta=dict(meta or {}))
    exit_ = {}
    partials = []

    def sell(p, raw, n, today, *, at, slot=False):
        p.sold_value += raw * n
        p.open_shares = p.held - n
        partials.append({"date": str(pd.Timestamp(today).date()), "shares": n, "price": float(raw), "at": at})
        return raw

    def close_out(sym, p, raw, reason, today, *, at):
        n = p.held
        sell(p, raw, n, today, at=at, slot=True)
        partials.pop()
        p.exit_date, p.exit_reason = today, reason
        p.exit_price = p.sold_value / p.shares if p.partial_shares else raw
        exit_.update(date=str(pd.Timestamp(today).date()), reason=reason, price=float(raw), at=at)

    stops = []
    last = None
    prev_stop = pos.stop
    for today, bar in bars.iterrows():
        prev_stop = pos.stop
        if today == entry_date:
            ps.manage_entry_bar(symbol, pos, frame, bar, today, policy, entry_at, close_out, sell, fee_rate, cfg)
        else:
            ps.manage_exit(symbol, pos, frame, bar, today, policy, close_out, sell, fee_rate, cfg)
        last = (today, bar)
        stops.append([str(today.date()), round(float(pos.stop), 4)])
        if exit_:
            break
    if last is None:
        return {"status": "hold", "stop": float(initial_stop), "as_of": None, "stops": [], "policy": policy.label(),
                "last_close": None, "r_now": None, "dist_pct": None, "exit": None, "partials": [],
                "open_shares": float(shares), "note": "no stored bar on or after the entry date yet"}
    today, bar = last
    close = float(bar["close"])
    risk = float(entry_price) - float(initial_stop)
    on_last = [x for x in partials if x["date"] == str(today.date())]
    if exit_:
        status = "exit_next_open" if exit_["at"] == ps.AT_CLOSE else "stopped"
    elif pos.queued_exit:
        status, exit_ = "exit_next_open", {"date": None, "reason": pos.queued_exit, "price": None, "at": ps.AT_OPEN}
    elif on_last:
        status = "partial"
    elif _ma_low_armed(policy, bar):
        status = "sell_stop_armed"
    elif pos.stop > prev_stop + 1e-9:
        status = "stop_raised"
    else:
        status = "hold"
    stop = None if exit_ and status != "exit_next_open" else float(pos.stop)
    if status == "sell_stop_armed":     # the order to rest for tomorrow is the higher of the two
        stop = max(stop, float(bar["low"]))
    return {"status": status, "stop": stop, "as_of": str(today.date()), "stops": stops, "policy": policy.label(),
            "last_close": close, "r_now": (close - float(entry_price)) / risk if risk > 0 else None,
            "dist_pct": (close - stop) / close * 100 if stop is not None and close else None,
            "exit": exit_ or None, "partials": partials, "open_shares": float(pos.held)}


def _ma_low_armed(policy: "ps.ExitPolicy", bar) -> bool:
    """The ma_low exit's armed state after `bar`, the latest session: it closed below `ma_col`, so the next
    session sells under its low (`portfolio_sim._ma_low_level` reads this same bar as `prev` tomorrow)."""
    if policy.mode != "ma_low":
        return False
    ma = bar.get(policy.ma_col, float("nan"))
    return ma == ma and float(bar["close"]) < float(ma)


# ------------------------------------------------------------------ the ledger's open signal trades

def openings(book: str, market: str) -> list[Opening]:
    """The book's open signal trades: each held symbol whose position was opened by a BUY carrying an
    initial stop. The entry is that BUY; the shares and average cost are the ledger's now."""
    from . import ledger
    rows = ledger.trades(book, market)
    h = ledger.holdings(rows)
    out = []
    for sym, n in h["positions"].items():
        since = h["since"].get(sym) or ""
        first = next((r for r in rows if r["symbol"] == sym and r["side"] == "BUY" and r["trade_date"] >= since
                      and r["initial_stop"] is not None), None)
        if first is None:
            continue
        out.append(Opening(trade_id=first["id"], book=book, market=market, symbol=sym,
                           entry_date=pd.Timestamp(first["trade_date"]),
                           entry_price=float(h["avg_cost"].get(sym) or first["price"]), shares=n,
                           initial_stop=float(first["initial_stop"]),
                           target=float(first["target"]) if first["target"] else math.inf,
                           setup=first["setup"] or first["entry_rule"] or "", meta=first.get("meta") or {}))
    return out


def fee_rate_for(strategy_key: str, market: str) -> float:
    """The per-side cost the strategy's backtest charges, which its breakeven stop includes: the spec's
    costs for a `--spec` strategy, none otherwise (as `run_portfolio_backtest` does)."""
    import shlex
    from . import spec as spec_mod
    from ..strategies import get_strategy
    if "--spec" in shlex.split(get_strategy(strategy_key).backtest_args or ""):
        return spec_mod.COST_BPS[market] / 10_000.0
    return 0.0


def refresh(market: str, books: list[str] | None = None) -> dict:
    """Re-run every open signal trade of the market's signal-strategy books through its exit, on stored
    bars, and store the result. Rows of trades no longer open are removed."""
    from ..core import indicators as ind
    from ..marketdata import cache
    from ..strategies import _REGISTRY
    from .backtest import exit_policy_for

    from . import paper
    init_schema()
    paper.init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT DISTINCT book FROM book_trades WHERE market=%s AND initial_stop IS NOT NULL", (market,))
        names = [r[0] for r in cur.fetchall()]
    strat = {b: paper.strategy_of(b, market) for b in names}
    names = [b for b in names if strat[b] in _REGISTRY and (books is None or b in books)]
    cfg = MARKETS[market]
    stats = {"books": 0, "positions": 0, **{k: 0 for k in STATUS_TEXT}, "no_bars": 0}
    keep = []
    for book in names:
        opens = openings(book, market)
        if not opens:
            continue
        stats["books"] += 1
        policy, fee = exit_policy_for(strat[book], market), fee_rate_for(strat[book], market)
        for o in opens:
            raw = cache.load_cached(market, o.symbol)
            if raw is None or raw.empty:
                stats["no_bars"] += 1
                continue
            df = ind.enrich_daily(raw)
            at = ps.AT_CLOSE if (o.meta or {}).get("order") == "close" else ps.INTRADAY
            r = track(df, policy, cfg, symbol=o.symbol, entry_date=o.entry_date, entry_price=o.entry_price,
                      initial_stop=o.initial_stop, shares=o.shares, target=o.target, meta=o.meta,
                      fee_rate=fee, entry_at=at, setup=o.setup)
            if r["as_of"] is None:
                stats["no_bars"] += 1
                continue
            stats["positions"] += 1
            stats[r["status"]] += 1
            keep.append(o.trade_id)
            ex = r["exit"] or {}
            with db.get_connection().cursor() as cur:
                cur.execute("""
                    INSERT INTO position_status (trade_id, book, market, symbol, as_of, entry_date, entry_price, shares,
                        initial_stop, stop, status, reason, exit_date, exit_price, last_close, r_now, dist_pct, policy,
                        stops, open_shares, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now())
                    ON CONFLICT (trade_id) DO UPDATE SET as_of=EXCLUDED.as_of, entry_date=EXCLUDED.entry_date,
                        entry_price=EXCLUDED.entry_price, shares=EXCLUDED.shares, initial_stop=EXCLUDED.initial_stop,
                        stop=EXCLUDED.stop, status=EXCLUDED.status, reason=EXCLUDED.reason, exit_date=EXCLUDED.exit_date,
                        exit_price=EXCLUDED.exit_price, last_close=EXCLUDED.last_close, r_now=EXCLUDED.r_now,
                        dist_pct=EXCLUDED.dist_pct, policy=EXCLUDED.policy, stops=EXCLUDED.stops,
                        open_shares=EXCLUDED.open_shares, updated_at=now()""",
                            (o.trade_id, book, market, o.symbol, r["as_of"], o.entry_date.date(), o.entry_price,
                             o.shares, o.initial_stop, r["stop"], r["status"], ex.get("reason"), ex.get("date"),
                             ex.get("price"), r["last_close"], r["r_now"], r["dist_pct"], r["policy"],
                             json.dumps(r["stops"][-60:]), r["open_shares"]))
    with db.get_connection().cursor() as cur:   # trades no longer open, in the books this run covered
        cur.execute("DELETE FROM position_status WHERE market=%s AND NOT (trade_id = ANY(%s))"
                    + (" AND book = ANY(%s)" if books is not None else ""),
                    (market, keep, books) if books is not None else (market, keep))
    return stats


def statuses(market: str) -> list[dict]:
    """The stored status of every open signal trade in the market, for the Today page."""
    init_schema()
    cols = ("trade_id", "book", "symbol", "as_of", "entry_date", "entry_price", "shares", "initial_stop", "stop",
            "status", "reason", "exit_date", "exit_price", "last_close", "r_now", "dist_pct", "policy", "open_shares",
            "updated_at")
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {', '.join(cols)} FROM position_status WHERE market=%s ORDER BY book, symbol", (market,))
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    for r in rows:
        for k in ("as_of", "entry_date", "exit_date", "updated_at"):
            r[k] = r[k].isoformat() if r[k] else None
        r["status_text"] = STATUS_TEXT.get(r["status"], r["status"])
    return rows
