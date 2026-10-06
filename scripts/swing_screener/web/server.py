"""Read-only web viewer: price charts, screening results, backtest reports.

Everything is served from Postgres — prices from `prices`/`index_series`,
screening history from `universe_history`, reports from the tables that
`web.ingest` fills. Strategies are still run offline from the scripts; this
process never executes one.

    python3 -m swing_screener.web            # http://127.0.0.1:8000
"""

import json
import re
import threading
from functools import lru_cache
from pathlib import Path

import pandas as pd
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import paths
from ..marketdata import freshness
from ..marketdata import names as names_mod
from ..marketdata.db import get_connection, py_value
from fundamentals import quality as qual  # long-term investing package (scripts/fundamentals)
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
    qual.init_schema()
    wl.sync_latest()  # pick up screener runs made while the watchlist didn't exist
    threading.Thread(target=_prewarm_sectors, daemon=True).start()
    names_mod.init_schema()
    missing = [m for m in ("us", "india") if not names_mod.load(m)]
    if missing:  # first run: fetch company names in the background (a few seconds; the UI shows tickers meanwhile)
        threading.Thread(target=lambda: [names_mod.refresh(m) for m in missing], daemon=True).start()


# --------------------------------------------------------------- symbols

_names_cache: dict[str, tuple[float, dict]] = {}


def _names(market: str) -> dict[str, str]:
    """symbol -> company name (marketdata/names.py), re-read every few minutes."""
    import time
    hit = _names_cache.get(market)
    if not hit or time.time() - hit[0] > 300 or not hit[1]:
        hit = (time.time(), names_mod.load(market))
        _names_cache[market] = hit
    return hit[1]


def _name(market: str, symbol: str) -> str | None:
    return names_mod.lookup(_names(market), symbol)


@lru_cache(maxsize=1)
def _universe() -> dict[str, list[dict]]:
    """Symbol list per market from the universe files + sector caches (no
    DISTINCT scan over 20M price rows)."""
    out = {}
    for market in ("us", "india"):
        f = paths.DATA_DIR / f"universe_{market}.csv"
        syms = pd.read_csv(f, keep_default_na=False)["ticker"].astype(str).str.strip().tolist() if f.exists() else []  # "NA" is a ticker
        syms = [x for x in syms if x]
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
def symbols(market: str | None = None, q_: str = Query("", alias="q"), limit: int = 40):
    """Symbol search across every market (or one, with `market`), by ticker or company name. Matching
    ignores the exchange suffix, so "RELIANCE" finds RELIANCE.NS and "apple" finds AAPL; exact tickers
    come first, then ticker prefixes, then names starting with the text, then the rest."""
    needle = q_.strip().upper()
    base = lambda s: s.upper().removesuffix(".NS")
    by_name = len(needle) >= 2
    hits = []
    for m in ([market] if market else ["us", "india"]):
        names = _names(m)
        for r in _universe().get(m, []):
            nm = names_mod.lookup(names, r["symbol"]) or ""
            if needle in r["symbol"].upper() or (by_name and needle in nm.upper()):
                hits.append({**r, "name": nm or None, "market": m, "type": "stock"})
        for s in _indices().get(m, []):
            nm = names.get(s) or ""
            if needle in s.upper() or (by_name and needle in nm.upper()):
                hits.append({"symbol": s, "name": nm or None, "sector": "index series", "market": m, "type": "index"})

    def rank(r):
        b, nm = base(r["symbol"]), (r["name"] or "").upper()
        return (b != needle, not b.startswith(needle), not (nm.startswith(needle) or f" {needle}" in nm),
                r["type"] != "stock", len(r["symbol"]))
    hits.sort(key=rank)
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
        last_day = df.index.to_series().resample(rule).last()  # the period's last real trading day
        df = df.resample(rule).agg(agg).dropna(subset=["close"])
        # label each bar with that day, not the calendar period end (which can lie in the future:
        # October's bar must not read "31 Oct" when the data stops on 1 Oct)
        df.index = pd.DatetimeIndex(last_day.loc[df.index].values)

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
    return {"latest": latest, "history": history, "name": _name(market, symbol)}


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
        return _with_name_col(market, cols, [[r.get(c) for c in cols] for r in records])
    t = q("SELECT columns, rows FROM report_tables WHERE run_id=%s AND name='candidates'", (id,))
    if not t:
        raise HTTPException(404)
    return _with_name_col(market, t[0][0], t[0][1])


def _with_name_col(market: str, cols: list, rows: list) -> dict:
    """Insert a company-name column right after the symbol column."""
    if "symbol" not in cols or "name" in cols:
        return {"columns": cols, "rows": rows}
    i = cols.index("symbol")
    return {"columns": [*cols[:i + 1], "name", *cols[i + 1:]],
            "rows": [[*r[:i + 1], _name(market, r[i]), *r[i + 1:]] for r in rows]}


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

_STRATEGY_SOURCES = [Path(paths.PACKAGE_DIR / "strategies"), Path(paths.PACKAGE_DIR / "backtesting" / "baseline.py"),
                     Path(paths.SCRIPTS_DIR / "fundamentals" / "quality.py")]
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
        for extra in ("swing_screener.backtesting.baseline", "fundamentals.quality"):
            if extra in sys.modules:
                importlib.reload(sys.modules[extra])
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


# ------------------------------------------------------------ market breadth
# Daily breadth is computed offline into breadth_daily (analytics/breadth.py). When newer prices exist,
# the page starts a top-up in a separate process (so it never blocks a request) and serves what is stored.

import subprocess
import sys
import numpy as np

from ..analytics import breadth as br

_breadth_jobs: dict[str, subprocess.Popen] = {}
_sector_cache: dict[tuple, dict] = {}


def _breadth_topup(market: str) -> bool:
    """Start a background top-up when prices are newer than the stored breadth. Returns True while running."""
    job = _breadth_jobs.get(market)
    if job and job.poll() is None:
        return True
    last_price = q("SELECT max(date) FROM prices WHERE market=%s", (market,))[0][0]
    last_br = q("SELECT max(date) FROM breadth_daily WHERE market=%s", (market,))[0][0]
    if last_br is None or (last_price and last_price > last_br and (job is None or job.returncode is not None)):
        if job is not None and job.returncode is not None and last_br is not None and last_price > last_br:
            # a finished top-up that still leaves the newest day out means that day is a partial load
            # (e.g. a holiday with stray rows) — don't relaunch forever
            return False
        env = {**__import__("os").environ, "PYTHONPATH": str(paths.SCRIPTS_DIR)}
        _breadth_jobs[market] = subprocess.Popen([sys.executable, "-m", "jobs", "run", "breadth", "--market", market],
                                                 cwd=str(paths.SCRIPTS_DIR), env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    return False


def _pct_rank(hist: pd.Series, v) -> float | None:
    """Share of history (0-100) strictly below v."""
    h = hist.dropna()
    if v is None or (isinstance(v, float) and np.isnan(v)) or h.empty:
        return None
    return float((h < v).mean() * 100)


def _sectors(market: str) -> dict:
    """Sector leadership from the most-traded stocks: 3M / 1M change vs the average stock, % above
    the 50-day average now and 1W / 1M / 3M ago, and 52-week highs / lows over the last two weeks."""
    last = q("SELECT max(date) FROM breadth_daily WHERE market=%s", (market,))[0][0]
    key = (market, last)
    if key in _sector_cache:
        return _sector_cache[key]
    elig = br.eligible(market)
    top = q("""SELECT symbol FROM (SELECT DISTINCT ON (symbol) symbol, dollar_vol_sma20 FROM prices
               WHERE market=%s AND symbol = ANY(%s) AND date BETWEEN %s::date - 10 AND %s AND dollar_vol_sma20 IS NOT NULL
               ORDER BY symbol, date DESC) l ORDER BY dollar_vol_sma20 DESC LIMIT %s""", (market, elig, last, last, br.BREADTH_N))
    syms = [r[0] for r in top]
    rows = q("SELECT symbol, date, close, high, low, sma50 FROM prices WHERE market=%s AND symbol = ANY(%s) AND date BETWEEN %s::date - 400 AND %s ORDER BY symbol, date",
             (market, syms, last, last))
    df = pd.DataFrame(rows, columns=["symbol", "date", "close", "high", "low", "sma50"])
    sec = {}
    for m_, s_, x in q("SELECT market, symbol, sector FROM symbol_kind WHERE market=%s AND sector IS NOT NULL", (market,)):
        sec[s_] = x
    for r in _universe().get(market, []):
        if r["sector"] and r["sector"] != "Unknown":
            sec.setdefault(r["symbol"], r["sector"])
    if q("SELECT to_regclass('quality_scores') IS NOT NULL")[0][0]:
        for s_, x in q("SELECT symbol, metrics->>'sector' FROM quality_scores WHERE market=%s", (market,)):
            if x:
                sec.setdefault(s_, x)
    per = []
    for sym, g in df.groupby("symbol", sort=False):
        c, h, lo, s50 = g.close.to_numpy(float), g.high.to_numpy(float), g.low.to_numpy(float), g.sma50.to_numpy(float)
        if len(c) < 64:
            continue
        hi252 = pd.Series(h).rolling(252, min_periods=200).max().to_numpy()
        lo252 = pd.Series(lo).rolling(252, min_periods=200).min().to_numpy()
        above = lambda k: bool(c[-1 - k] > s50[-1 - k]) if not np.isnan(s50[-1 - k]) else None
        per.append({"symbol": sym, "sector": sec.get(sym), "r3m": c[-1] / c[-64] - 1, "r1m": c[-1] / c[-22] - 1,
                    "a0": above(0), "a1w": above(5), "a1m": above(21), "a3m": above(63),
                    "highs": bool(np.nansum(h[-10:] >= hi252[-10:])), "lows": bool(np.nansum(lo[-10:] <= lo252[-10:]))})
    p = pd.DataFrame(per)
    med3, med1 = p.r3m.median(), p.r1m.median()
    s = p[p.sector.notna() & (p.sector.astype(str).str.strip() != "") & (p.sector != "Unknown")]
    out, uptrend = [], {"now": 0, "1w": 0, "1m": 0, "3m": 0}
    for name, g in s.groupby("sector"):
        share = {k: g[col].mean() for k, col in (("now", "a0"), ("1w", "a1w"), ("1m", "a1m"), ("3m", "a3m"))}
        for k, v in share.items():
            uptrend[k] += bool(v > 0.5)
        out.append({"sector": name, "stocks": len(g), "r3m_vs": g.r3m.median() - med3, "r1m_vs": g.r1m.median() - med1,
                    "above50": share["now"], "highs": int(g.highs.sum()), "lows": int(g.lows.sum()),
                    "members": [{"symbol": r.symbol, "r3m": r.r3m, "r1m": r.r1m, "above50": r.a0}
                                for r in g.sort_values("r3m", ascending=False).itertuples()]})
    out.sort(key=lambda x: -x["r3m_vs"])
    res = {"sectors": out, "uptrend": uptrend, "n_sectors": len(out), "covered": int(len(s)), "total": int(len(p))}
    _sector_cache.clear()
    _sector_cache[key] = res
    return res


def _dedupe_events(events: list) -> list:
    """Newest first; a "weakest/strongest since" reading repeated on consecutive days is reported once (its latest)."""
    seen, out = set(), []
    for day, text in sorted(events, key=lambda e: e[0], reverse=True):
        kind = text.split(" fell to ")[0].split(" rose to ")[0] if (" the weakest since " in text or " the strongest since " in text) else text
        if kind in seen:
            continue
        seen.add(kind)
        out.append({"date": day.date().isoformat(), "text": text})
    return out


@app.get("/api/breadth")
def breadth_page(market: str = "india"):
    if market not in br.INDEXES:
        raise HTTPException(400, "market must be us or india")
    br.init_schema()
    updating = _breadth_topup(market)
    rows = q("SELECT date, n, adv, dec, up4, dn4, highs, lows, above5, above50, up25m, dn25m, up50m, dn50m FROM breadth_daily "
             "WHERE market=%s ORDER BY date", (market,))
    if not rows:
        return {"market": market, "empty": True, "updating": updating,
                "command": f"python3 -m swing_screener.analytics.breadth --market {market} --full" + (" --classify" if market == "india" else "")}
    d = pd.DataFrame(rows, columns=["date", "n", "adv", "dec", "up4", "dn4", "highs", "lows", "above5", "above50", "up25m", "dn25m", "up50m", "dn50m"])
    d["date"] = pd.to_datetime(d["date"])
    d = d.set_index("date")
    d["pct5"], d["pct50"] = d.above5 / d.n * 100, d.above50 / d.n * 100
    d["hl"], d["ad"] = d.highs - d.lows, d.adv - d.dec
    for col in ("hl", "ad", "highs", "lows", "adv", "dec"):
        d[col + "10"] = d[col].rolling(10).mean()

    # index levels, their 50-day average, and the volatility index
    idx = {}
    for k, _, label in br.INDEXES[market]:
        r = q("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date >= '2013-01-01' ORDER BY date", (market, k))
        if r:
            s_ = pd.Series([x[1] for x in r], index=pd.to_datetime([x[0] for x in r]))
            # end on the breadth day, so every card on the page describes the same session
            idx[k] = {"label": label, "s": s_[s_.index <= d.index[-1]]}
    main_key = br.INDEXES[market][0][0]
    vk, _, vlabel = br.VOL_INDEX[market]
    vr = q("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date >= '2013-01-01' ORDER BY date", (market, vk))
    vix = pd.Series([x[1] for x in vr], index=pd.to_datetime([x[0] for x in vr])) if vr else None
    if vix is not None:
        vix = vix[vix.index <= d.index[-1]]

    since = d.index >= pd.Timestamp(br.HISTORY_START)
    H = d[since]
    T = d.iloc[-1]
    ago = {"1 week ago": 5, "1 month ago": 21, "3 months ago": 63}
    back = lambda col, k: (None if len(d) <= k else float(d[col].iloc[-1 - k]))

    def rank_text(p, low_word, high_word):
        if p is None:
            return ""
        return f"Only {round(p)} in 100 days since 2015 were {low_word}." if p < 50 else f"Only {round(100 - p)} in 100 days since 2015 were {high_word}."

    cards = []
    main = idx.get(main_key)
    if main:
        s_ = main["s"]; vs = s_ / s_.rolling(50).mean() - 1
        hist = vs[vs.index >= pd.Timestamp(br.HISTORY_START)]
        p = _pct_rank(hist, vs.iloc[-1])
        cards.append({"key": "index50", "title": f"{main['label']} against its 50 DMA?", "value": f"{vs.iloc[-1] * 100:+.1f}%", "pct": p,
                      "text": rank_text(p, "further below", "further above"),
                      "compare": {"cols": ["vs 50 DMA"], "rows": [[k, f"{vs.iloc[-1 - n] * 100:+.1f}%"] for k, n in ago.items() if len(vs) > n]}})
    p_hl = _pct_rank(H.hl10, T.hl10)
    cards.append({"key": "hl", "title": "Stocks at a 52w high or low?", "value": f"{int(T.highs)} highs · {int(T.lows)} lows", "pct": p_hl,
                  "text": f"Typical day over the last 2 weeks: {T.highs10:.0f} highs, {T.lows10:.0f} lows. "
                          + rank_text(p_hl, "weaker", "stronger").replace("days", "two-week stretches"),
                  "compare": {"cols": ["Highs", "Lows"], "rows": [[k, int(back("highs", n) or 0), int(back("lows", n) or 0)] for k, n in ago.items()]}})
    p5, p50 = _pct_rank(H.pct5, T.pct5), _pct_rank(H.pct50, T.pct50)
    cards.append({"key": "dma", "title": "Stocks above their 5 & 50 DMA?", "value": f"{T.pct5:.0f}% · {T.pct50:.0f}%", "sub": "5 DMA · 50 DMA",
                  "pct": p50, "text": f"Only {round(p50 if p50 < 50 else 100 - p50)} in 100 days since 2015 had "
                                      f"{'fewer' if p50 < 50 else 'more'} above the 50-day average. For the 5-day: only "
                                      f"{round(p5 if p5 < 50 else 100 - p5)} in 100 had {'fewer' if p5 < 50 else 'more'}.",
                  "compare": {"cols": ["5 DMA", "50 DMA"], "rows": [[k, f"{back('pct5', n):.0f}%", f"{back('pct50', n):.0f}%"] for k, n in ago.items() if len(d) > n]}})
    p_ad = _pct_rank(H.ad10, T.ad10)
    cards.append({"key": "ad", "title": "Stocks rising or falling?", "value": f"{int(T.adv)} up · {int(T.dec)} down", "pct": p_ad,
                  "text": f"Typical day over the last 2 weeks: {T.adv10:.0f} up, {T.dec10:.0f} down. "
                          + rank_text(p_ad, "weaker", "stronger").replace("days", "two-week stretches"),
                  "compare": {"cols": ["Up", "Down"], "rows": [[k, int(back("adv", n) or 0), int(back("dec", n) or 0)] for k, n in ago.items()]}})
    try:
        sx = _sectors(market)
    except Exception as exc:  # noqa: BLE001 — the rest of the page still works without sectors
        sx = {"sectors": [], "error": str(exc), "uptrend": {}, "n_sectors": 0}
    if sx["sectors"]:
        lead, lag = sx["sectors"][0], sx["sectors"][-1]
        up = sx["uptrend"]
        cards.append({"key": "sectors", "title": "Leading sectors, last 3 months?", "value": f"{lead['r3m_vs'] * 100:+.0f}% {lead['sector']} · {lag['r3m_vs'] * 100:+.0f}% {lag['sector']}",
                      "pct": up["now"] / sx["n_sectors"] * 100,
                      "text": f"{up['now']} of {sx['n_sectors']} sectors have most of their stocks above the 50 DMA.",
                      "compare": {"cols": ["In uptrends"], "rows": [[k, f"{up[kk]} of {sx['n_sectors']}"] for k, kk in (("1 week ago", "1w"), ("1 month ago", "1m"), ("3 months ago", "3m"))]}})
    vol = None
    if main is not None and vix is not None and len(vix) > 30:
        ret = np.log(main["s"]).diff()
        actual = ret.rolling(20).std() * np.sqrt(252) * 100
        both = pd.concat([vix.rename("exp"), actual.rename("act")], axis=1).dropna()
        both["ratio"] = both.exp / both.act
        bh = both[both.index >= pd.Timestamp(br.HISTORY_START)]
        b = both.iloc[-1]
        p = _pct_rank(bh.ratio, b.ratio)
        cards.append({"key": "options", "title": "Options: expected vs actual?", "value": f"{b.exp:.1f} expected · {b.act:.1f} actual", "pct": p,
                      "text": f"Options price about ±{b.exp / np.sqrt(12):.1f}% over a month; the index has been moving about ±{b.act / np.sqrt(12):.1f}%. "
                              f"Only {round(100 - p if p >= 50 else p)} in 100 days since 2015 had {'dearer' if p >= 50 else 'cheaper'} options.",
                      "compare": {"cols": ["Expected", "Actual"], "rows": [[k, f"{both.exp.iloc[-1 - n]:.1f}", f"{both.act.iloc[-1 - n]:.1f}"] for k, n in ago.items() if len(both) > n]}})
        vol = both

    # what changed in the last 5 sessions: threshold crossings and multi-month extremes
    events = []
    for i in range(max(1, len(d) - 5), len(d)):
        day, cur, prev = d.index[i], d.iloc[i], d.iloc[i - 1]
        if prev.pct50 >= 30 > cur.pct50:
            events.append((day, "Stocks above their 50-day average fell below 30%: a washout."))
        if prev.pct50 < 30 <= cur.pct50:
            events.append((day, "Stocks above their 50-day average rose above 30%, out of washout territory."))
        if prev.pct50 <= 70 < cur.pct50:
            events.append((day, "Stocks above their 50-day average rose above 70%: broad strength."))
        for col, name in (("hl10", "One-year highs minus lows (10-day average)"), ("ad10", "Rising minus falling stocks (10-day average)")):
            past = d[col].iloc[:i]
            lower, higher = past[past <= cur[col]], past[past >= cur[col]]
            if len(past) and not lower.empty and (day - lower.index[-1]).days > 90:
                events.append((day, f"{name} fell to {cur[col]:.0f}, the weakest since {lower.index[-1]:%-d %b %Y}."))
            elif len(past) and not higher.empty and (day - higher.index[-1]).days > 90:
                events.append((day, f"{name} rose to {cur[col]:.0f}, the strongest since {higher.index[-1]:%-d %b %Y}."))
        if main is not None and day in main["s"].index:
            s_ = main["s"]; ma = s_.rolling(50).mean()
            j = s_.index.get_loc(day)
            if j > 0 and (s_.iloc[j] > ma.iloc[j]) != (s_.iloc[j - 1] > ma.iloc[j - 1]) and not np.isnan(ma.iloc[j - 1]):
                events.append((day, f"{main['label']} crossed {'above' if s_.iloc[j] > ma.iloc[j] else 'below'} its 50-day average."))

    # last 30 days table, and the 20th/80th percentiles each column is shaded against
    tbl_cols = ["adv", "dec", "up4", "dn4", "highs", "lows", "pct5", "pct50", "up25m", "dn25m", "up50m", "dn50m"]
    bands = {c: [float(H[c].quantile(0.2)), float(H[c].quantile(0.8))] for c in tbl_cols}
    last30 = []
    for day, r in d.tail(30).iloc[::-1].iterrows():
        row = {"date": day.date().isoformat(), **{c: (None if pd.isna(r[c]) else float(r[c])) for c in tbl_cols}}
        for k, v in idx.items():
            s_ = v["s"]
            if day in s_.index:
                j = s_.index.get_loc(day)
                row[k] = {"close": float(s_.iloc[j]), "day": float(s_.iloc[j] / s_.iloc[j - 1] - 1) if j else None,
                          "month": float(s_.iloc[j] / s_.iloc[j - 21] - 1) if j >= 21 else None}
        if vol is not None and day in vol.index:
            row["vol"] = {k: float(vol.loc[day, k]) for k in ("exp", "act", "ratio")}
        last30.append(row)

    ser = lambda s_: [{"time": t.date().isoformat(), "value": round(float(v), 4)} for t, v in s_.dropna().items()]
    charts = {"hl": ser(d.hl), "hl10": ser(d.hl10), "pct50": ser(d.pct50), "ad10": ser(d.ad10)}
    for k, v in idx.items():
        charts[k] = ser(v["s"][v["s"].index >= d.index[0]])
    head = {k: {"label": v["label"], "close": float(v["s"].iloc[-1]), "day": float(v["s"].iloc[-1] / v["s"].iloc[-2] - 1),
                "from_high": float(v["s"].iloc[-1] / v["s"].iloc[-252:].max() - 1), "date": v["s"].index[-1].date().isoformat()} for k, v in idx.items()}
    return {"market": market, "date": d.index[-1].date().isoformat(), "updating": updating, "n": int(T.n), "breadth_n": br.BREADTH_N,
            "indexes": head, "index_keys": [k for k, _, _ in br.INDEXES[market] if k in idx], "vol_label": vlabel,
            "cards": cards, "events": _dedupe_events(events),
            "sectors": sx, "last30": last30, "bands": bands, "charts": charts}


# --------------------------------------------------------- quality tracker
# Fundamentals are fetched and scored offline (fundamentals/quality.py); this only views them and manages
# your tracked list. Valuation and timing are recomputed here from the latest close on every request.

def _last_prices(keys: list[tuple]) -> dict:
    if not keys:
        return {}
    rows = q("""SELECT DISTINCT ON (market, symbol) market, symbol, date, close, sma200, high_252, rsi14
                FROM prices WHERE (market, symbol) IN %s ORDER BY market, symbol, date DESC""", (tuple(keys),))
    return {(m, s): {"date": d.isoformat(), "close": c, "sma200": a, "high_252": h, "rsi14": r} for m, s, d, c, a, h, r in rows}


@app.get("/api/quality")
def quality(market: str | None = None, symbol: str | None = None):
    where, args = ("WHERE market=%s", (market,)) if market else ("", ())
    if market and symbol:
        where, args = "WHERE market=%s AND symbol=%s", (market, symbol)
    scored = {(m, s): (sc, t, mt, c) for m, s, sc, t, mt, c in
              q(f"SELECT market, symbol, quality_score, tests, metrics, computed_at FROM quality_scores {where}", args)}
    watch = {(m, s): (n, tp, a) for m, s, n, tp, a in q(f"SELECT market, symbol, note, target_price, added_at FROM quality_watch {where}", args)}
    errors = dict(((m, s), e) for m, s, e in q(f"SELECT market, symbol, error FROM fundamentals_raw {where} {'AND' if where else 'WHERE'} error IS NOT NULL", args))
    keys = sorted(set(scored) | set(watch))
    prices = _last_prices(keys)
    sectors = {(m, r["symbol"]): r["sector"] for m, rs in _universe().items() for r in rs}
    out = []
    for k in keys:
        sc, tests, m, computed = scored.get(k, (None, None, None, None))
        note, target, added = watch.get(k, (None, None, None))
        a = qual.assess(m, prices.get(k), target) if m else None
        p = prices.get(k) or {}
        row = {"market": k[0], "symbol": k[1], "tracked": k in watch, "note": note, "target": target,
               "added_at": added.isoformat() if added else None, "close": p.get("close"), "price_date": p.get("date"),
               "quality": sc, "tests": tests, "computed_at": computed.isoformat() if computed else None,
               "name": (m or {}).get("name"), "sector": (m or {}).get("sector") or sectors.get(k),
               "error": errors.get(k)}
        if m:
            row.update({x: m.get(x) for x in ("roic_avg", "roe_avg", "rev_cagr", "eps_cagr", "op_margin", "fcf_conversion",
                                               "net_debt_ebitda", "net_cash", "f_score", "financial", "n_years", "fiscal_end", "pe_hist_median")})
            row.update({x: a.get(x) for x in ("zone", "value", "votes", "timing", "flags", "high_quality", "pe", "fcf_yield", "pe_vs_own", "peg",
                                               "drawdown", "vs_200dma", "rsi", "at_your_price")})
        else:  # tracked but not scored yet: price-only signals
            close, hi, sma = p.get("close"), p.get("high_252"), p.get("sma200")
            row.update(drawdown=close / hi - 1 if close and hi else None, vs_200dma=close / sma - 1 if close and sma else None,
                       rsi=p.get("rsi14"), at_your_price=bool(target and close and close <= target))
        out.append(row)
    return out


@app.get("/api/quality/criteria")
def quality_criteria():
    return qual.criteria()


@app.post("/api/quality/watch")
def quality_track(market: str = Body(...), symbol: str = Body(...), note: str | None = Body(None), target: float | None = Body(None)):
    symbol = symbol.strip().upper()
    if market not in ("us", "india"):
        raise HTTPException(400, "market must be us or india")
    if not _known_symbol(market, symbol):
        raise HTTPException(404, f"{symbol} is not a known {market.upper()} symbol"
                                 + (" — India symbols end in .NS" if market == "india" and not symbol.endswith(".NS") else ""))
    qual.init_schema()
    with get_connection().cursor() as cur:
        cur.execute("""INSERT INTO quality_watch (market, symbol, note, target_price) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (market, symbol) DO UPDATE SET note=COALESCE(EXCLUDED.note, quality_watch.note),
                       target_price=COALESCE(EXCLUDED.target_price, quality_watch.target_price)""",
                    (market, symbol, note or None, target))
    return {"ok": True, "symbol": symbol}


@app.put("/api/quality/watch")
def quality_update(market: str = Body(...), symbol: str = Body(...), note: str | None = Body(None), target: float | None = Body(None)):
    with get_connection().cursor() as cur:
        cur.execute("UPDATE quality_watch SET note=%s, target_price=%s WHERE market=%s AND symbol=%s", (note or None, target, market, symbol))
    return {"ok": True}


@app.delete("/api/quality/watch")
def quality_untrack(market: str, symbol: str):
    with get_connection().cursor() as cur:
        cur.execute("DELETE FROM quality_watch WHERE market=%s AND symbol=%s", (market, symbol))
    return {"ok": True}


# ------------------------------------------------------------- movers

# A few always-traded names give the market's trading calendar in milliseconds (a date scan over every
# symbol takes seconds), and skip holiday dates that carry only a few stray rows.
_ANCHORS = {"us": ("SPY", "AAPL", "MSFT", "JPM", "XOM"),
            "india": ("RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ICICIBANK.NS")}
MOVER_PERIODS = {"1D": 1, "1W": 5, "1M": 21, "3M": 63, "6M": 126, "YTD": None, "1Y": 252}
# "Liquid" universe: at least this average daily traded value over 20 days, and this share price —
# filters out the illiquid penny names that otherwise dominate any gainers list.
MOVER_LIQUID = {"us": {"value": 10e6, "price": 5.0}, "india": {"value": 10e7, "price": 20.0}}
_MOVER_BENCH = {"us": ("SPX", "S&P 500"), "india": ("NIFTY50", "Nifty 50")}
_day_rows: dict[tuple, dict] = {}


def _recent_counts(market: str) -> dict:
    return freshness.recent_counts(market)


def _sessions(market: str, complete: bool = True) -> list:
    """Complete trading days (marketdata/freshness.py: a partly loaded or stray-holiday day is dropped)."""
    return freshness.sessions(market, complete)


def _rows_on(market: str, d) -> dict:
    """symbol -> (close, volume, vol_sma50, dollar_vol_sma20) on one date (cached: a past day never changes)."""
    key = (market, d)
    if key not in _day_rows:
        if len(_day_rows) > 40:
            _day_rows.clear()
        _day_rows[key] = {sym: (c, v, vs, dv) for sym, c, v, vs, dv in q(
            "SELECT symbol, close, volume, vol_sma50, dollar_vol_sma20 FROM prices WHERE market=%s AND date=%s AND close > 0",
            (market, d))}
    return _day_rows[key]


@lru_cache(maxsize=4)
def _equities(market: str, _day) -> set:
    return set(br.eligible(market))  # common stocks only (no ETFs / funds); refreshed when the data date changes


def _bench_change(market: str, d0, d1):
    series, label = _MOVER_BENCH[market]
    at = lambda d: q("SELECT close FROM index_series WHERE market=%s AND series=%s AND date<=%s ORDER BY date DESC LIMIT 1",
                     (market, series, d))
    a, b = at(d0), at(d1)
    return {"label": label, "pct": (b[0][0] / a[0][0] - 1) * 100 if a and b and a[0][0] else None}


@app.get("/api/movers")
def movers(market: str = "us", period: str = "1D", universe: str = "liquid", limit: int = 25):
    """Top gainers and losers over a period, from the latest trading day in the database."""
    if market not in _ANCHORS or period not in MOVER_PERIODS:
        raise HTTPException(400, "bad market or period")
    days = _sessions(market)
    if len(days) < 2:
        return {"market": market, "empty": True}
    d1 = days[-1]  # _sessions already skips a partly loaded day
    n = MOVER_PERIODS[period]
    d0 = max([d for d in days if d.year < d1.year], default=days[0]) if n is None else days[max(0, len(days) - 1 - n)]
    now, then = _rows_on(market, d1), _rows_on(market, d0)
    eq, liq = _equities(market, d1), MOVER_LIQUID[market]
    sectors = {sym: sec for sym, sec in q("SELECT symbol, sector FROM symbol_kind WHERE market=%s AND sector NOT IN ('', 'Unknown')", (market,))}
    sectors.update({r["symbol"]: r["sector"] for r in _universe().get(market, []) if r["sector"] not in (None, "", "Unknown")})
    rows = []
    for sym, (c, v, vs, dv) in now.items():
        if sym not in eq or sym not in then or not then[sym][0]:
            continue
        if universe == "liquid" and ((dv or 0) < liq["value"] or c < liq["price"]):
            continue
        rows.append({"symbol": sym, "name": _name(market, sym), "sector": sectors.get(sym), "last": c, "chg": c - then[sym][0],
                     "pct": (c / then[sym][0] - 1) * 100, "volume": v, "rel_vol": v / vs if v and vs else None,
                     "value": c * v if v else None, "avg_value": dv})
    rows.sort(key=lambda r: r["pct"], reverse=True)
    adv = sum(r["pct"] > 0 for r in rows)
    dec = sum(r["pct"] < 0 for r in rows)
    return {"market": market, "period": period, "universe": universe, "date": d1.isoformat(), "from": d0.isoformat(),
            "count": len(rows), "adv": adv, "dec": dec, "unch": len(rows) - adv - dec,
            "liquid": liq, "bench": _bench_change(market, d0, d1),
            "gainers": [r for r in rows[:limit] if r["pct"] > 0],
            "losers": [r for r in reversed(rows[-limit:]) if r["pct"] < 0]}


# ------------------------------------------------------------- sectors

from ..analytics import sectors as sect

_sector_cache: dict[str, dict] = {}        # market -> {"key": latest session, "data": compute() result}
_sector_lock = threading.Lock()


def _sector_data(market: str, wait: bool = True) -> tuple[dict | None, bool]:
    """(analysis, updating). Recomputed when a newer trading day lands; a stale result is served
    while the new one computes in the background (it takes ~10 s)."""
    days = _sessions(market)
    key = days[-1].isoformat() if days else None
    hit = _sector_cache.get(market)
    if hit and hit["key"] == key:
        return hit["data"], False

    def run():
        with _sector_lock:
            if _sector_cache.get(market, {}).get("key") == key:
                return
            _sector_cache[market] = {"key": key, "data": sect.compute(market)}
    if hit and not wait:
        threading.Thread(target=run, daemon=True).start()
        return hit["data"], True
    run()
    return _sector_cache[market]["data"], False


def _prewarm_sectors() -> None:
    for m in ("us", "india"):
        try:
            _sector_data(m)
        except Exception as exc:  # noqa: BLE001 - the page computes on demand instead
            print(f"sectors prewarm {m}: {exc}")


@app.get("/api/sectors")
def sectors_api(market: str = "us", level: str = "industry"):
    if level not in ("industry", "sector"):
        raise HTTPException(400, "level must be industry or sector")
    data, updating = _sector_data(market, wait=market not in _sector_cache)
    if data.get("empty"):
        return data
    members = data["members"]
    groups = [{**{k: v for k, v in g.items() if k not in ("series", "members")},
               "leaders": [{"symbol": s, "name": members[s]["name"]} for s in g["members"][:3]]} for g in data[level]]
    return {k: data[k] for k in ("market", "date", "stocks", "doc", "market_ret", "bench")} | {
        "level": level, "groups": groups, "updating": updating}


@app.get("/api/sectors/group")
def sector_group(market: str, level: str, group: str):
    data, _ = _sector_data(market, wait=market not in _sector_cache)
    g = next((x for x in data.get(level, []) if x["group"] == group), None)
    if not g:
        raise HTTPException(404, f"no {level} '{group}' in {market}")
    members = data["members"]
    sub = [x for x in data["industry"] if x["sector"] == group] if level == "sector" else []
    return {"market": market, "date": data["date"], "level": level, "doc": data["doc"], "market_ret": data["market_ret"],
            "group": {k: v for k, v in g.items() if k != "members"},
            "members": [members[s] for s in g["members"]],
            "industries": [{k: v for k, v in x.items() if k not in ("series", "members")} for x in sub]}


# ------------------------------------------------------------- data status

from . import status as status_mod

_status_cache: dict = {}


def _price_day(market: str):
    """(latest complete session, (newer partial day, rows) or None, rows on the complete day)."""
    days = _sessions(market)
    if not days:
        return None, None, 0
    counts = _recent_counts(market)
    newer = sorted(d for d in counts if d > days[-1])
    partial = (newer[-1], counts[newer[-1]]) if newer else None
    return days[-1], partial, counts.get(days[-1]) or len(_rows_on(market, days[-1]))


@app.get("/api/status")
def status_api():
    import time
    hit = _status_cache.get("fresh")
    if not hit or time.time() - hit[0] > 60:  # freshness is cheap but not free: recompute at most once a minute
        hit = (time.time(), status_mod.freshness(q, _price_day))
        _status_cache["fresh"] = hit
    fresh = hit[1]
    runs = status_mod.runs(q, 40)
    overview = status_mod.jobs_overview(q)
    # the run shown in detail: a running one, else the most recent pipeline run, else the most recent run
    pipes = [p["last"] for p in overview["pipelines"] if p["last"]]
    running = [r for r in runs if r["status"] == "running"]
    daily = running[0] if running else max(pipes, key=lambda r: r["started_at"]) if pipes else (runs[0] if runs else None)
    worst = max((i["status"] for m in ("us", "india") for i in fresh[m]["items"] if i["key"] in ("prices", "breadth", "screening")),
                key=["ok", "warn", "missing", "stale"].index, default="ok")
    return {"now": __import__("datetime").datetime.now().astimezone().isoformat(), "freshness": fresh, "runs": runs,
            "latest_daily": status_mod.run_detail(q, daily["id"]) if daily else None,
            "jobs": overview["jobs"], "pipelines": overview["pipelines"],
            "running": [r["id"] for r in running], "overall": worst,
            "command": f"cd {paths.SCRIPTS_DIR} && PYTHONPATH=. .venv/bin/python -m jobs run daily --strategies all",
            "schedule_command": f"cd {paths.SCRIPTS_DIR} && PYTHONPATH=. .venv/bin/python -m jobs schedule"}


@app.get("/api/status/run/{rid}")
def status_run(rid: int):
    r = status_mod.run_detail(q, rid)
    if not r:
        raise HTTPException(404)
    return r


# ------------------------------------------------------------- watchlist

def _known_symbol(market: str, symbol: str) -> bool:
    if any(r["symbol"] == symbol for r in _universe().get(market, [])) or symbol in _indices().get(market, []):
        return True
    return bool(q("SELECT 1 FROM prices WHERE market=%s AND symbol=%s LIMIT 1", (market, symbol)))


def _with_prices(items: list[dict]) -> list[dict]:
    """Add last close, day change and sector to watchlist rows (stocks from prices, index series as fallback)."""
    if not items:
        return []
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
        e["name"] = _name(e["market"], e["symbol"])
        if e.get("added_at") is not None and not isinstance(e["added_at"], str):
            e["added_at"] = e["added_at"].isoformat()
    return items


def _resolve(symbol: str, market: str | None) -> tuple[str, str]:
    """(market, SYMBOL) for a typed symbol: as given if the market is known, else the exact match in
    either market — "RELIANCE" resolves to india / RELIANCE.NS."""
    sym = symbol.strip().upper()
    if market:
        if not _known_symbol(market, sym):
            raise HTTPException(404, f"{sym} is not a known {market.upper()} symbol")
        return market, sym
    for m, cand in (("india", sym if sym.endswith(".NS") else None), ("us", sym), ("india", sym + ".NS")):
        if cand and _known_symbol(m, cand):
            return m, cand
    raise HTTPException(404, f"{sym} is not a known symbol in either market")


SCREENER_LIST = "screener"  # the built-in, screener-fed list


@app.get("/api/watchlists")
def watchlists():
    picks = wl.entries()
    return [*wl.lists(), {"id": SCREENER_LIST, "name": "Screener picks", "count": len(picks), "builtin": True}]


@app.post("/api/watchlists")
def watchlist_create(name: str = Body(..., embed=True)):
    try:
        return {"id": wl.create_list(name), "name": name.strip()}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.put("/api/watchlists/{lid}")
def watchlist_rename(lid: int, name: str = Body(..., embed=True)):
    try:
        wl.rename_list(lid, name)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return {"ok": True}


@app.delete("/api/watchlists/{lid}")
def watchlist_delete(lid: int):
    wl.delete_list(lid)
    return {"ok": True}


@app.get("/api/watchlists/membership")
def watchlist_membership(market: str, symbol: str):
    return {"lists": wl.membership(market, symbol)}


@app.get("/api/watchlists/{lid}/items")
def watchlist_items(lid: str):
    if lid == SCREENER_LIST:
        return _with_prices([{**e, "added_at": e["added_at"]} for e in wl.entries()])
    return _with_prices(wl.items(int(lid)))


@app.post("/api/watchlists/{lid}/items")
def watchlist_item_add(lid: int, symbol: str = Body(...), market: str | None = Body(None), note: str | None = Body(None)):
    m, sym = _resolve(symbol, market)
    wl.add_item(lid, m, sym, note)
    return {"ok": True, "market": m, "symbol": sym}


@app.put("/api/watchlists/{lid}/items")
def watchlist_item_note(lid: int, market: str = Body(...), symbol: str = Body(...), note: str | None = Body(None)):
    wl.set_item_note(lid, market, symbol, note)
    return {"ok": True}


@app.delete("/api/watchlists/{lid}/items")
def watchlist_item_remove(lid: str, market: str, symbol: str):
    if lid == SCREENER_LIST:
        wl.dismiss(market, symbol)  # hidden until it drops off the screen and is flagged again
    else:
        wl.remove_item(int(lid), market, symbol)
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
