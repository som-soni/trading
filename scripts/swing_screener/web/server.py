"""Read-only web viewer: price charts, screening results, backtest reports.

Everything is served from Postgres — prices from `prices`/`index_series`,
screening history from `universe_history`, reports from the tables that
`web.ingest` fills. Strategies are still run offline from the scripts; this
process never executes one.

    python3 -m swing_screener.web            # http://127.0.0.1:8000
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import paths
from ..marketdata.db import get_connection, py_value
from ..screening import watchlist as wl
from ..strategies import docs as _strat_docs_initial  # noqa: F401  (loaded once; see _strategy_docs)
from . import ingest as ingest_mod

STATIC = Path(__file__).parent / "static"
app = FastAPI(title="Trading viewer")


def q(sql: str, params: tuple = ()) -> list[tuple]:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@app.on_event("startup")
def _startup() -> None:
    ingest_mod.init_schema()
    wl.sync_latest()  # pick up screener runs made while the watchlist didn't exist


# --------------------------------------------------------------- symbols

@lru_cache(maxsize=1)
def _universe() -> dict[str, list[dict]]:
    """Symbol list per market from the universe files + sector caches (no
    DISTINCT scan over 20M price rows)."""
    out = {}
    for market in ("us", "india"):
        f = paths.DATA_DIR / f"universe_{market}.csv"
        syms = pd.read_csv(f)["ticker"].dropna().astype(str).tolist() if f.exists() else []
        sec = {}
        sf = paths.DATA_DIR / f"sector_cache_{market}.csv"
        if sf.exists():
            sec = dict(pd.read_csv(sf).dropna().itertuples(index=False, name=None))
        out[market] = [{"symbol": s, "sector": sec.get(s)} for s in syms]
    return out


@lru_cache(maxsize=1)
def _indices() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {"us": [], "india": []}
    for market, series in q("SELECT DISTINCT market, series FROM index_series ORDER BY 1,2"):
        out.setdefault(market, []).append(series)
    return out


@app.get("/api/symbols")
def symbols(market: str, q_: str = Query("", alias="q"), limit: int = 40):
    needle = q_.strip().upper()
    hits = []
    if market in _universe():
        for r in _universe()[market]:
            if needle in r["symbol"].upper():
                hits.append({**r, "type": "stock"})
    for s in _indices().get(market, []):
        if needle in s.upper():
            hits.append({"symbol": s, "sector": "index series", "type": "index"})
    # exact and prefix matches first
    hits.sort(key=lambda r: (not r["symbol"].upper().startswith(needle), len(r["symbol"])))
    return hits[:limit]


# ---------------------------------------------------------------- prices

def _series(values: pd.Series, dates) -> list[dict]:
    return [{"time": d, "value": round(float(v), 4)} for d, v in zip(dates, values) if pd.notna(v)]


@app.get("/api/prices")
def prices(market: str, symbol: str, tf: str = "D", bars: int = 600):
    if tf not in ("D", "W", "M"):
        raise HTTPException(400, "tf must be D, W or M")
    rows = q(
        "SELECT date, open, high, low, close, volume FROM prices "
        "WHERE market=%s AND symbol=%s ORDER BY date",
        (market, symbol),
    )
    ohlc = bool(rows)
    if rows:
        df = pd.DataFrame(rows, columns=["date", "open", "high", "low", "close", "volume"])
    else:
        rows = q("SELECT date, close FROM index_series WHERE market=%s AND series=%s ORDER BY date",
                 (market, symbol))
        if not rows:
            raise HTTPException(404, f"no price data for {symbol}")
        df = pd.DataFrame(rows, columns=["date", "close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").astype(float)
    if tf != "D":
        rule = "W-FRI" if tf == "W" else "ME"
        agg = {"close": "last"}
        if ohlc:
            agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        df = df.resample(rule).agg(agg).dropna(subset=["close"])

    df = df.tail(bars)
    dates = [d.strftime("%Y-%m-%d") for d in df.index]
    out = {
        "symbol": symbol, "market": market, "tf": tf, "ohlc": ohlc,
    }
    if ohlc:
        out["candles"] = [
            {"time": d, "open": o, "high": h, "low": l, "close": c}
            for d, o, h, l, c in zip(dates, df.open.round(4), df.high.round(4),
                                     df.low.round(4), df.close.round(4))
        ]
        out["volume"] = [{"time": d, "value": float(v) if v == v else 0.0, "up": bool(c >= o)}
                         for d, v, o, c in zip(dates, df.volume, df.open, df.close)]
    else:
        out["line"] = _series(df["close"], dates)
    return out


@app.get("/api/symbol-context")
def symbol_context(market: str, symbol: str):
    """Everything the screener has said about a symbol: latest plan per
    strategy (entry/stop/target levels for the chart) and the decision trail."""
    rows = q(
        "SELECT run_id, strategy, decision, price, reason, full_row FROM universe_history "
        "WHERE market=%s AND symbol=%s ORDER BY run_id DESC LIMIT 60",
        (market, symbol),
    )
    history = [{"run_id": r[0], "strategy": r[1], "decision": r[2], "price": r[3], "reason": r[4]}
               for r in rows]
    latest, seen = [], set()
    for r in rows:
        if r[1] in seen:
            continue
        seen.add(r[1])
        fr = r[5]
        latest.append({"run_id": r[0], "strategy": r[1], "decision": r[2],
                       **{k: fr.get(k) for k in ("entry", "stop", "target_r", "setup_quality",
                                                 "strategy_setup", "sector")}})
    # screener candidate tables from ingested runs (covers strategies the
    # pipeline did not write to universe_history, e.g. chart_pattern)
    for rid, strat, name in q(
        "SELECT r.id, r.strategy, r.run_name FROM report_runs r "
        "WHERE r.kind='screener' AND r.market=%s ORDER BY r.run_name DESC", (market,)
    ):
        if strat in seen:
            continue
        t = q("SELECT columns, rows FROM report_tables WHERE run_id=%s AND name='candidates'", (rid,))
        if not t:
            continue
        cols, data = t[0]
        if "symbol" not in cols:
            continue
        for row in data:
            rec = dict(zip(cols, row))
            if rec.get("symbol") == symbol:
                seen.add(strat)
                latest.append({"run_id": name, "strategy": strat, "decision": rec.get("decision"),
                               **{k: rec.get(k) for k in ("entry", "stop", "target_r", "setup_quality",
                                                          "strategy_setup", "sector")}})
    return {"latest": latest, "history": history}


# ------------------------------------------------------------- screening

@app.get("/api/screening/runs")
def screening_runs(market: str | None = None):
    """Screener runs, newest first, from both sources: every pipeline run in
    universe_history and every ingested screener report."""
    runs = []
    sql = "SELECT market, strategy, run_id, count(*), count(*) FILTER (WHERE tradeable) " \
          "FROM universe_history"
    args: tuple = ()
    if market:
        sql += " WHERE market=%s"
        args = (market,)
    for m, s, rid, n, t in q(sql + " GROUP BY 1,2,3 ORDER BY 3 DESC", args):
        runs.append({"source": "history", "market": m, "strategy": s, "run": rid,
                     "rows": n, "tradeable": t})
    sql = "SELECT id, market, strategy, run_name FROM report_runs WHERE kind='screener'"
    if market:
        sql += " AND market=%s"
    for rid, m, s, name in q(sql + " ORDER BY run_name DESC", args):
        runs.append({"source": "report", "id": rid, "market": m, "strategy": s, "run": name})
    return runs


@app.get("/api/screening/table")
def screening_table(source: str, market: str, strategy: str, run: str, id: int | None = None):
    if source == "history":
        rows = q(
            "SELECT full_row FROM universe_history WHERE market=%s AND strategy=%s AND run_id=%s",
            (market, strategy, run),
        )
        if not rows:
            raise HTTPException(404)
        records = [r[0] for r in rows]
        cols = list(records[0].keys())
        return {"columns": cols, "rows": [[r.get(c) for c in cols] for r in records]}
    t = q("SELECT columns, rows FROM report_tables WHERE run_id=%s AND name='candidates'", (id,))
    if not t:
        raise HTTPException(404)
    return {"columns": t[0][0], "rows": t[0][1]}


# --------------------------------------------------------------- reports

@app.get("/api/reports")
def reports(kind: str | None = None, market: str | None = None):
    sql = ("SELECT id, kind, market, strategy, run_name, title, summary, generated_at "
           "FROM report_runs WHERE true")
    args: list = []
    if kind:
        sql += " AND kind=%s"
        args.append(kind)
    if market:
        sql += " AND market IN (%s,'all')"
        args.append(market)
    return [
        {"id": r[0], "kind": r[1], "market": r[2], "strategy": r[3], "run": r[4],
         "title": r[5], "summary": r[6], "generated_at": r[7].isoformat() if r[7] else None}
        for r in q(sql + " ORDER BY market, strategy, run_name DESC", tuple(args))
    ]


@app.get("/api/reports/{rid}")
def report(rid: int):
    r = q("SELECT id, kind, market, strategy, run_name, title, markdown, summary "
          "FROM report_runs WHERE id=%s", (rid,))
    if not r:
        raise HTTPException(404)
    r = r[0]
    # point figure links at the API so the markdown renders unchanged
    md = re.sub(r"\]\((?:\./)?figures/([^)\s]+)\)",
                lambda m: f"](/api/reports/{rid}/figures/{m.group(1)})", r[6])
    tables = [{"name": n, "rows": c}
              for n, c in q("SELECT name, jsonb_array_length(rows) FROM report_tables "
                            "WHERE run_id=%s ORDER BY name", (rid,))]
    return {"id": r[0], "kind": r[1], "market": r[2], "strategy": r[3], "run": r[4],
            "title": r[5], "markdown": md, "summary": r[7], "tables": tables}


@app.get("/api/reports/{rid}/figures/{name}")
def figure(rid: int, name: str):
    r = q("SELECT data FROM report_figures WHERE run_id=%s AND name=%s", (rid, name))
    if not r:
        raise HTTPException(404)
    return Response(bytes(r[0][0]), media_type="image/png",
                    headers={"Cache-Control": "max-age=300"})


@app.get("/api/reports/{rid}/tables/{name}")
def report_table(rid: int, name: str, symbol: str | None = None):
    r = q("SELECT columns, rows FROM report_tables WHERE run_id=%s AND name=%s", (rid, name))
    if not r:
        raise HTTPException(404)
    cols, rows = r[0]
    if symbol and "symbol" in cols:
        i = cols.index("symbol")
        rows = [x for x in rows if x[i] == symbol]
    return {"columns": cols, "rows": rows}


@app.get("/api/trade-runs")
def trade_runs(market: str, symbol: str):
    """Backtest runs that traded this symbol, for the chart's trade overlay."""
    out = []
    for rid, strat, name, cols, rows in q(
        "SELECT r.id, r.strategy, r.run_name, t.columns, t.rows FROM report_runs r "
        "JOIN report_tables t ON t.run_id=r.id AND t.name='trades' "
        "WHERE r.kind='backtest' AND r.market=%s ORDER BY r.strategy, r.run_name DESC", (market,)
    ):
        if "symbol" not in cols:
            continue
        i = cols.index("symbol")
        n = sum(1 for x in rows if x[i] == symbol)
        if n:
            out.append({"id": rid, "strategy": strat, "run": name, "trades": n})
    return out


# ------------------------------------------------------------ strategies
# Pages are generated from the strategy classes themselves (strategies/docs.py),
# so they always describe the code the server is running.

_STRATEGY_SOURCES = [Path(paths.PACKAGE_DIR / "strategies"), Path(paths.PACKAGE_DIR / "backtesting" / "baseline.py")]
_strat_state = {"sig": None, "docs": _strat_docs_initial, "error": None}


def _strategy_signature() -> tuple:
    files = []
    for src in _STRATEGY_SOURCES:
        files += sorted(src.glob("*.py")) if src.is_dir() else [src]
    return tuple((f.name, f.stat().st_mtime_ns) for f in files if f.exists())


def _strategy_docs():
    """The strategies module, reloaded whenever a strategy file is added or edited — so a new or
    changed strategy shows on the Strategies page without restarting the server. If the code is
    mid-edit and fails to import, keep serving the last good version and report the error."""
    import importlib
    import sys
    sig = _strategy_signature()
    if sig == _strat_state["sig"]:
        return _strat_state["docs"]
    try:
        pkg = "swing_screener.strategies"
        importlib.invalidate_caches()
        # reload every strategy module (new files are imported by the package's own reload),
        # then the registry package, then the page builder that reads the registry
        for name in sorted(n for n in list(sys.modules) if n.startswith(pkg + ".") and n != pkg + ".docs"):
            importlib.reload(sys.modules[name])
        importlib.reload(sys.modules[pkg])
        if "swing_screener.backtesting.baseline" in sys.modules:
            importlib.reload(sys.modules["swing_screener.backtesting.baseline"])
        _strat_state["docs"] = importlib.reload(sys.modules[pkg + ".docs"])
        _strat_state["error"] = None
    except Exception as exc:  # noqa: BLE001
        _strat_state["error"] = f"{type(exc).__name__}: {exc}"
        print(f"WARNING: strategy code changed but failed to reload, serving the previous version: {_strat_state['error']}")
    _strat_state["sig"] = sig
    return _strat_state["docs"]


def _latest_screens(strategy: str | None = None) -> list[dict]:
    sql = """SELECT u.market, u.strategy, u.run_id, count(*),
                    count(*) FILTER (WHERE u.tradeable),
                    count(*) FILTER (WHERE (u.full_row->>'watchlist_candidate')::boolean)
             FROM universe_history u
             JOIN (SELECT market, strategy, max(run_id) run_id FROM universe_history GROUP BY 1, 2) l USING (market, strategy, run_id)"""
    args: tuple = ()
    if strategy:
        sql += " WHERE u.strategy=%s"
        args = (strategy,)
    return [{"market": m, "strategy": st, "run": r, "rows": n, "tradeable": t, "watch": w}
            for m, st, r, n, t, w in q(sql + " GROUP BY 1, 2, 3 ORDER BY 1", args)]


@app.get("/api/strategies")
def strategies():
    bt = dict(q("SELECT strategy, count(*) FROM report_runs WHERE kind='backtest' GROUP BY 1"))
    screens = _latest_screens()
    out = []
    strat_docs = _strategy_docs()
    for k in strat_docs.keys():
        d = strat_docs.strategy_doc(k)
        out.append({"key": k, "name": d["name"], "kind": d["kind"], "status": d["status"], "description": d["description"],
                    "backtests": bt.get(k, 0), "screens": [x for x in screens if x["strategy"] == k]})
    return out


@app.get("/api/strategies/{key}")
def strategy(key: str):
    strat_docs = _strategy_docs()
    if key not in strat_docs.keys():
        raise HTTPException(404, f"unknown strategy {key}")
    d = strat_docs.strategy_doc(key)
    d["backtests"] = [{"id": i, "market": m, "run": r, "summary": s, "generated_at": g.isoformat() if g else None}
                      for i, m, r, s, g in q("SELECT id, market, run_name, summary, generated_at FROM report_runs "
                                             "WHERE strategy=%s AND kind='backtest' ORDER BY generated_at DESC NULLS LAST", (key,))]
    d["screens"] = _latest_screens(key)
    return d


# ------------------------------------------------------------- watchlist

def _known_symbol(market: str, symbol: str) -> bool:
    if any(r["symbol"] == symbol for r in _universe().get(market, [])) or symbol in _indices().get(market, []):
        return True
    return bool(q("SELECT 1 FROM prices WHERE market=%s AND symbol=%s LIMIT 1", (market, symbol)))


@app.get("/api/watchlist")
def watchlist(market: str | None = None):
    items = wl.entries(market)
    if not items:
        return []
    # last two closes per name in one query (stocks from prices, index series as a fallback)
    keys = [(e["market"], e["symbol"]) for e in items]
    last: dict[tuple, list] = {}
    for m, sym, close in q(
        """SELECT market, symbol, close FROM (
             SELECT market, symbol, date, close, row_number() OVER (PARTITION BY market, symbol ORDER BY date DESC) rn
             FROM prices WHERE (market, symbol) IN %s AND date > now() - interval '30 days') t
           WHERE rn <= 2 ORDER BY market, symbol, date DESC""", (tuple(keys),)):
        last.setdefault((m, sym), []).append(close)
    missing = [k for k in keys if k not in last]
    if missing:
        for m, sym, close in q(
            """SELECT market, series, close FROM (
                 SELECT market, series, date, close, row_number() OVER (PARTITION BY market, series ORDER BY date DESC) rn
                 FROM index_series WHERE (market, series) IN %s) t WHERE rn <= 2 ORDER BY market, series, date DESC""",
                (tuple(missing),)):
            last.setdefault((m, sym), []).append(close)
    sectors = {(m, r["symbol"]): r["sector"] for m, rs in _universe().items() for r in rs}
    for e in items:
        closes = last.get((e["market"], e["symbol"]), [])
        e["last"] = closes[0] if closes else None
        e["change_pct"] = (closes[0] / closes[1] - 1) * 100 if len(closes) > 1 and closes[1] else None
        e["sector"] = sectors.get((e["market"], e["symbol"]))
        e["added_at"] = e["added_at"].isoformat()
    return items


@app.post("/api/watchlist")
def watchlist_add(market: str = Body(...), symbol: str = Body(...), note: str | None = Body(None)):
    symbol = symbol.strip().upper()
    if market not in ("us", "india"):
        raise HTTPException(400, "market must be us or india")
    if not _known_symbol(market, symbol):
        raise HTTPException(404, f"{symbol} is not a known {market.upper()} symbol"
                                 + (" — India symbols end in .NS" if market == "india" and not symbol.endswith(".NS") else ""))
    wl.add(market, symbol, note)
    return {"ok": True, "symbol": symbol}


@app.delete("/api/watchlist")
def watchlist_remove(market: str, symbol: str):
    wl.remove(market, symbol)
    return {"ok": True}


@app.put("/api/watchlist/note")
def watchlist_note(market: str = Body(...), symbol: str = Body(...), note: str | None = Body(None)):
    wl.set_note(market, symbol, note)
    return {"ok": True}


@app.post("/api/ingest")
def run_ingest(force: bool = False):
    _indices.cache_clear()
    wl.sync_latest()
    return ingest_mod.ingest(force=force)


# ---------------------------------------------------------------- static

app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.middleware("http")
async def _revalidate_static(request, call_next):
    """Make the browser check with the server before reusing a cached asset
    (cheap: StaticFiles answers 304 via ETag). Without this, a reload after an
    update can run new HTML against a stale app.js / style.css."""
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache"
    return response


@app.get("/")
def index():
    # stamp every local asset URL with its mtime, so an update is a new URL
    html = (STATIC / "index.html").read_text()
    html = re.sub(
        r'(/static/[\w./-]+\.(?:js|css))',
        lambda m: f"{m.group(1)}?v={int((STATIC / m.group(1)[len('/static/'):]).stat().st_mtime)}",
        html,
    )
    return Response(html, media_type="text/html", headers={"Cache-Control": "no-cache"})
