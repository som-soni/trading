"""The instructions the books give on a real position: one synthetic case for each way they were wrong.

The 8 Nov 2026 review found that the ledger, the open-position tracker and paper books would give wrong
instructions once a real position existed. Each case below is one of those findings, on hand-made bars:

    split        ledger rows are read on the stored bars' scale (a row before a split's ex-date holds the
                 ratio times its shares at its prices divided by it), and a paper fill goes back to the day's
    meta         a taken setup keeps the strategy's own `signal_meta` (the run row's `order`), so a close order
                 is tracked from the close (a kullamagi buy whose entry bar dipped under the stop holds, as in
                 the backtest)
    replay       the exit is replayed from the shares the position was opened with: a step of the ladder
                 already sold is not asked for again, and a small remainder is not a lasting "Stop reached"
    statuses     a target fill reads `target`, a step queued for the next open reads `partial_queued`
    idempotent   a confirm repeated with the same request id returns the rebalance it stored; a second is
                 refused while one is open; a take refuses a stop at or above the fill

(Paper entries resting as the backtest's order, the review's other finding, are covered since 2026-11-14 by
signal paper books replaying their live orders through `portfolio_sim.simulate`.)

Then MTUM, 4:1 on 5 Nov 2026, on the stored bars: a position bought before the split holds, where its
unadjusted rows read "stopped" on the entry day.

The database cases run in temporary tables (pg_temp) that shadow the books' tables on this connection
only; nothing is written to the real ones.

    PYTHONPATH=. .venv/bin/python -m tests.test_book_instructions
"""

import math
import sys
import warnings

import numpy as np
import pandas as pd

from swing_screener.backtesting import ledger, paper, tracker
from swing_screener.backtesting import portfolio_sim as ps
from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind

warnings.filterwarnings("ignore")
FAILS: list[str] = []
CFG = MARKETS["india"]


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def frame(close, *, spread=0.01, start="2024-01-01", volume=1e5) -> pd.DataFrame:
    c = np.asarray(close, dtype=float)
    idx = pd.bdate_range(start, periods=len(c))
    return ind.enrich_daily(pd.DataFrame({"open": c, "high": c * (1 + spread), "low": c * (1 - spread), "close": c,
                                          "volume": volume}, index=idx))


# ------------------------------------------------------------------ split

def test_split() -> None:
    print("split: ledger rows on the stored bars' scale")
    rows = [{"side": "CASH", "amount": 10_000, "trade_date": "2026-10-01"},
            {"id": 1, "side": "BUY", "symbol": "MTUM", "shares": 10, "price": 300.0, "costs": 1.0,
             "trade_date": "2026-10-28", "initial_stop": 280.0, "target": 360.0,
             "meta": {"pivot": 296.0, "min_breakout_vol": 1.5, "base_id": "x"}},
            {"id": 2, "side": "SELL", "symbol": "MTUM", "shares": 8, "price": 70.0, "trade_date": "2026-11-06"}]
    k = {("MTUM", "2026-10-28"): 4.0}
    adj = ledger.split_adjust(rows, k)
    b = adj[1]
    check("a buy before a 4:1 holds four times the shares at a quarter of the prices",
          b["shares"] == 40 and b["price"] == 75 and b["initial_stop"] == 70 and b["target"] == 90, str(b))
    check("its meta's price levels move with it; ratios and ids do not",
          b["meta"] == {"pivot": 74.0, "min_breakout_vol": 1.5, "base_id": "x"}, str(b["meta"]))
    check("a row after the ex-date and a cash row are untouched", adj[2] is rows[2] and adj[0] is rows[0])
    check("the rows passed in are not changed", rows[1]["shares"] == 10 and rows[1]["meta"]["pivot"] == 296.0)
    h = ledger.holdings(adj)
    check("the book holds 32 shares after selling 8 of the 40, not a short sale",
          h["positions"] == {"MTUM": 32.0} and math.isclose(h["avg_cost"]["MTUM"], 75.0), str(h["positions"]))
    try:
        ledger.holdings(rows)
        check("read unadjusted, the same rows would sell 8 of 10 and leave 2", ledger.holdings(rows)["positions"]["MTUM"] == 2)
    except ValueError as e:
        check("read unadjusted, the same rows would sell 8 of 10", False, str(e))
    back = ledger.split_adjust(adj, k, invert=True)[1]
    check("invert puts a stored-scale row back on the day's own prices",
          math.isclose(back["shares"], 10) and math.isclose(back["price"], 300) and math.isclose(back["meta"]["pivot"], 296))


# ------------------------------------------------------------------ meta (close order)

def test_close_order() -> None:
    print("meta: a close order is tracked from its close")
    up = np.linspace(100, 120, 40)
    df = frame(up)
    d = df.index[20]
    c = float(df.loc[d, "close"])
    df.loc[d, "low"] = c * 0.9                 # the entry session dipped under the stop before the close
    stop = c * 0.95
    pol = ps.ExitPolicy(mode="kullamagi", use_target=False)
    at_close = tracker.track(df, pol, CFG, symbol="X", entry_date=d, entry_price=c, initial_stop=stop, shares=10,
                             entry_at=ps.AT_CLOSE)
    intraday = tracker.track(df, pol, CFG, symbol="X", entry_date=d, entry_price=c, initial_stop=stop, shares=10)
    check("bought at the close (signal_meta order=close): the earlier dip does not stop it",
          at_close["status"] != "stopped", at_close["status"])
    check("without the meta the same buy reads stopped on its entry day",
          intraday["status"] == "stopped" and intraday["exit"]["date"] == str(d.date()), intraday["status"])


# ------------------------------------------------------------------ replay from the opening shares

def test_replay() -> None:
    print("replay: from the shares the position was opened with")
    c = np.r_[np.full(30, 100.0), np.linspace(100, 112, 10), np.full(10, 112.0)]
    df = frame(c, spread=0.005)
    entry_d = df.index[25]
    pol = ps.ExitPolicy(mode="bracket", use_target=False, partial_at_target=0.5)
    kw = dict(symbol="X", entry_date=entry_d, entry_price=100.0, initial_stop=95.0, target=110.0)
    full = tracker.track(df, pol, CFG, shares=10, **kw)
    sold = [p for p in full["partials"]]
    check("the ladder sells half at the target", len(sold) == 1 and sold[0]["shares"] == 5 and full["open_shares"] == 5,
          str(sold))
    fixed = tracker.track(df, pol, CFG, shares=10, held=5, **kw)
    check("half recorded as sold: the replay from 10 shares asks for nothing more",
          fixed["status"] in ("hold", "stop_raised") and fixed["open_shares"] == 5, fixed["status"])
    owed = tracker.track(df, pol, CFG, shares=10, held=10, **kw)
    check("half not yet recorded: it reads partial, whenever the ladder sold it", owed["status"] == "partial",
          owed["status"])
    old = tracker.track(df, pol, CFG, shares=5, **kw)
    check("(replayed on the 5 left, as before, the ladder sells half of them again)",
          len(old["partials"]) == 1 and old["partials"][0]["shares"] == 2, str(old["partials"]))
    tiny = tracker.track(df, pol, CFG, shares=1, **kw)
    check("(and a 1-share remainder exits whole at the target, a lasting exit)", tiny["exit"] is not None
          and tiny["exit"]["reason"] == "TARGET", str(tiny["exit"]))
    fixed1 = tracker.track(df, pol, CFG, shares=2, held=1, **kw)
    check("opened with 2, 1 sold: the remainder holds", fixed1["exit"] is None and fixed1["status"] in ("hold", "stop_raised"),
          fixed1["status"])
    # openings: the shares bought since the book last held none, and the ledger's holding now
    rows = [{"id": 1, "side": "BUY", "symbol": "X", "shares": 4, "price": 50, "trade_date": "2024-01-02", "initial_stop": 45},
            {"id": 2, "side": "SELL", "symbol": "X", "shares": 4, "price": 55, "trade_date": "2024-01-10"},
            {"id": 3, "side": "BUY", "symbol": "X", "shares": 10, "price": 100, "trade_date": "2024-02-01", "initial_stop": 95},
            {"id": 4, "side": "SELL", "symbol": "X", "shares": 5, "price": 110, "trade_date": "2024-02-20"}]
    ep = tracker._episode(rows, "X")
    check("the position's rows start after the last time it was flat", [r["id"] for r in ep] == [3, 4], str(ep))


# ------------------------------------------------------------------ statuses

def test_statuses() -> None:
    print("statuses: a target, and a step queued for the next open")
    c = np.r_[np.full(30, 100.0), np.linspace(100, 112, 10)]
    df = frame(c, spread=0.005)
    pol = ps.ExitPolicy(mode="bracket", use_target=True)
    r = tracker.track(df, pol, CFG, symbol="X", entry_date=df.index[25], entry_price=100.0, initial_stop=95.0,
                      shares=10, target=110.0)
    check("a target reached reads 'target', not 'stopped'", r["status"] == "target" and r["exit"]["reason"] == "TARGET",
          f"{r['status']} {r['exit']}")
    check("the target has its own text", "Target" in tracker.STATUS_TEXT["target"])
    mv = ps.ExitPolicy(mode="minervini", use_target=False, partial_r=0)     # the strength sale only
    base = np.full(80, 100.0)
    c = np.r_[base, 100 * (1 + mv.strength_ext) * 1.05]
    df = frame(c, spread=0.002)
    r = tracker.track(df, mv, CFG, symbol="X", entry_date=df.index[70], entry_price=100.0, initial_stop=93.0,
                      shares=100, meta={"pivot": 100.0})
    want = int(100 * mv.partial_frac)
    check("a close far above the average queues the strength sale: 'partial_queued', not 'hold'",
          r["status"] == "partial_queued" and r["queued_shares"] == want, f"{r['status']} {r.get('queued_shares')}")
    nxt = pd.concat([df, df.iloc[[-1]].set_axis([df.index[-1] + pd.offsets.BDay()])])
    r2 = tracker.track(nxt, mv, CFG, symbol="X", entry_date=df.index[70], entry_price=100.0, initial_stop=93.0,
                       shares=100, meta={"pivot": 100.0})
    check("…and the next session's replay sells exactly that part at the open",
          [p["shares"] for p in r2["partials"]] == [want] and r2["partials"][0]["at"] == ps.AT_OPEN, str(r2["partials"]))


# ------------------------------------------------------------------ database cases, in pg_temp

TEMP = ["book_rebalances", "book_trades", "book_positions", "book_cash", "books", "paper_orders", "universe_history"]


def _temp_tables(cur) -> None:
    from swing_screener.backtesting import rebalance
    for sql in (rebalance.SCHEMA, ledger.SCHEMA, paper.SCHEMA):
        cur.execute(sql.replace("CREATE TABLE IF NOT EXISTS", "CREATE TEMP TABLE IF NOT EXISTS"))
    cur.execute("CREATE TEMP TABLE IF NOT EXISTS universe_history (run_id TEXT, market TEXT, strategy TEXT, symbol TEXT, "
                "sector TEXT, decision TEXT, price DOUBLE PRECISION, tradeable BOOLEAN, reason TEXT, full_row JSONB)")
    for t in TEMP:
        cur.execute("SELECT n.nspname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE c.oid = to_regclass(%s)", (t,))
        where = (cur.fetchone() or [""])[0]
        if not where.startswith("pg_temp"):
            raise RuntimeError(f"{t} resolves to {where}, not a temporary table: refusing to write")


def test_database() -> None:
    from swing_screener.marketdata import cache, db
    from fastapi import HTTPException
    from swing_screener.web import server
    print("database: MTUM's replay, the take route, idempotent confirms (temporary tables)")
    try:
        conn = db.get_connection()
    except Exception as e:  # noqa: BLE001
        check("a database to run the stored-data cases on", False, str(e))
        return
    with conn.cursor() as cur:
        _temp_tables(cur)
        for t in TEMP:
            cur.execute(f"DELETE FROM pg_temp.{t}")

    # MTUM: 4:1 on 2026-11-05. Bought on 28 Oct at about four times the stored close, with a stop well below.
    bars = cache.load_cached("us", "MTUM")
    d = pd.Timestamp("2026-10-28")
    if bars is None or d not in bars.index or bars.index[-1] < pd.Timestamp("2026-11-05"):
        check("MTUM's stored bars cover 28 Oct to 5 Nov 2026", False)
    else:
        traded = 4 * float(bars.loc[d, "close"])
        ledger.record("etf_swing", "us", [{"side": "CASH", "amount": 50_000, "trade_date": "2026-10-27"},
                                          {"side": "BUY", "symbol": "MTUM", "shares": 10, "price": traded,
                                           "trade_date": "2026-10-28", "initial_stop": traded * 0.8}])
        h = ledger.holdings_of("etf_swing", "us")
        check("the ledger reads 40 MTUM after its 4:1, at a quarter of the price paid",
              h["positions"] == {"MTUM": 40.0} and math.isclose(h["avg_cost"]["MTUM"], traded / 4), str(h["positions"]))
        raw = ledger.trades("etf_swing", "us")
        check("the ledger list still shows the trade as made", raw[-1]["shares"] == 10 and math.isclose(raw[-1]["price"], traded))
        (o,) = tracker.openings("etf_swing", "us")
        df = ind.enrich_daily(bars)
        pol = ps.ExitPolicy(mode="bracket", use_target=False)
        r = tracker.track(df, pol, MARKETS["us"], symbol="MTUM", entry_date=o.entry_date, entry_price=o.entry_price,
                          initial_stop=o.initial_stop, shares=o.opening_shares, held=o.shares)
        check("MTUM's replay holds through the split", r["status"] == "hold" and r["as_of"] >= "2026-11-05"
              and math.isclose(r["stop"], traded * 0.8 / 4), f"{r['status']} {r['exit']} stop {r['stop']}")
        bad = tracker.track(df, pol, MARKETS["us"], symbol="MTUM", entry_date=d, entry_price=traded,
                            initial_stop=traded * 0.8, shares=10)
        check("(its unadjusted row reads stopped on the entry day)", bad["status"] == "stopped"
              and bad["exit"]["date"] == "2026-10-28", f"{bad['status']} {bad['exit']}")
        # a paper fill read off the stored bars goes back to the day's scale
        ledger.record("etf_swing", "us", [{"side": "SELL", "symbol": "MTUM", "shares": 20, "price": traded / 4,
                                           "trade_date": "2026-10-29"}], source="paper", stored_scale=True)
        last = ledger.trades("etf_swing", "us")[-1]
        check("a stored-scale fill before the split is stored as the day's trade (5 at four times the price)",
              math.isclose(last["shares"], 5) and math.isclose(last["price"], traded), str(last))
        check("…and the book reads 20 left", ledger.holdings_of("etf_swing", "us")["positions"] == {"MTUM": 20.0})

    # the take route keeps the run row's order meta (the strategy's signal_meta), and refuses a stop at or above the fill
    import json
    with conn.cursor() as cur:
        cur.execute("INSERT INTO pg_temp.universe_history (run_id, market, strategy, symbol, tradeable, full_row) "
                    "VALUES ('2026-11-06_200000', 'india', 'kullamagi', 'SHYAMMETL.NS', true, %s)",
                    (json.dumps({"symbol": "SHYAMMETL.NS", "tradeable": True, "entry": 800.0, "stop": 760.0, "target_r": 3,
                                 "decision": "TRADE - HIGH CONFIDENCE", "strategy_setup": "S1",
                                 "order": {"meta": {"order": "close", "_queued": True}}}),))
    got = server.take_setup("india", {"strategy": "kullamagi", "symbol": "SHYAMMETL", "shares": 10, "price": 800,
                                      "trade_date": "2026-11-06", "refresh": False})
    (row,) = [t for t in ledger.trades("kullamagi", "india") if t["id"] == got["trade_id"]]
    check("a taken setup's trade carries the signal's meta (order: close)", row["meta"] == {"order": "close"}, str(row["meta"]))
    try:
        server.take_setup("india", {"strategy": "kullamagi", "symbol": "SHYAMMETL", "shares": 10, "price": 750,
                                    "initial_stop": 760, "refresh": False})
        check("a take with the stop above the fill is refused", False)
    except HTTPException as e:
        check("a take with the stop above the fill is refused", e.status_code == 400, str(e.detail))

    # confirms: a repeated request returns its rebalance; a second one waits for the first to be completed
    a = ledger.save_rebalance("momentum_dual_combo", "india", "2026-10-30", "v1", [], [], request_id="req-1", one_open=True)
    b = ledger.save_rebalance("momentum_dual_combo", "india", "2026-10-30", "v1", [], [], request_id="req-1", one_open=True)
    check("the same request id stores one rebalance", a == b, f"{a} {b}")
    try:
        ledger.save_rebalance("momentum_dual_combo", "india", "2026-10-30", "v1", [], [], request_id="req-2", one_open=True)
        check("a second rebalance is refused while one is open", False)
    except ValueError:
        check("a second rebalance is refused while one is open", True)
    stub = {"capital": 100.0, "as_of": "2026-10-30", "spec_id": "v1", "orders": [], "other": []}
    real = server._combo
    server._combo = lambda market, capital: stub
    try:
        again = server.combo_confirm("india", {"request_id": "req-1"})
        check("the combination's confirm, repeated, returns the stored rebalance", again["id"] == a and again["repeat"],
              str(again))
        try:
            server.combo_confirm("india", {"request_id": "req-3"})
            check("the combination's confirm refuses a new rebalance while one is open", False)
        except HTTPException as e:
            check("the combination's confirm refuses a new rebalance while one is open", e.status_code == 409, str(e.detail))
        ledger.complete("momentum_dual_combo", "india", a)
        c = server.combo_confirm("india", {"request_id": "req-3"})
        check("once completed, the next confirm stores a new one", c["id"] != a and not c["repeat"], str(c))
    finally:
        server._combo = real
        with conn.cursor() as cur:
            for t in TEMP:
                cur.execute(f"DROP TABLE IF EXISTS pg_temp.{t} CASCADE")


def main() -> int:
    test_split()
    test_close_order()
    test_replay()
    test_statuses()
    test_database()
    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'the books give the instructions the backtest would'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
