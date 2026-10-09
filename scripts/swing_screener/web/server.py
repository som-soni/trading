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
from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from .. import paths
from ..config import MARKETS
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
    threading.Thread(target=lambda: [(_names(m), _liquidity(m)) for m in tuple(MARKETS)], daemon=True).start()  # first search is instant
    names_mod.init_schema()
    missing = [m for m in tuple(MARKETS) if not names_mod.load(m)]
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
    for market in tuple(MARKETS):
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


@app.get("/api/markets")
def markets_api():
    """The markets the app knows (config/MARKETS): the web app builds its market selector, badges and
    currency formatting from this, so adding a country needs no UI change."""
    from ..config import MARKETS
    return [{"key": k, "name": c.name, "exchange": c.exchange, "badge": c.badge or c.name, "flag": c.flag,
             "currency": c.currency_symbol, "suffix": c.symbol_suffix, "tz": c.tz} for k, c in MARKETS.items()]


_liq_cache: dict = {}


def _liquidity(market: str) -> dict[str, float]:
    """symbol -> percentile (0-1) of 20-day traded value in the latest stock snapshot; ranks search hits."""
    from ..screens import snapshot
    ds = snapshot.dates(market)
    if not ds:
        return {}
    if _liq_cache.get(market, (None,))[0] != ds[-1]:
        df = snapshot.load(market, ds[-1])
        _liq_cache[market] = (ds[-1], dict(zip(df["symbol"], df["value20"].rank(pct=True).fillna(0))))
    return _liq_cache[market][1]


@app.get("/api/symbols")
def symbols(market: str | None = None, q_: str = Query("", alias="q"), limit: int = 40):
    """Symbol search across every market (or one, with `market`), by ticker or company name. Matching
    ignores the exchange suffix, so "RELIANCE" finds RELIANCE.NS and "apple" finds AAPL; exact tickers
    come first, then ticker prefixes, then names starting with the text, then the rest."""
    needle = q_.strip().upper()
    base = lambda s: s.upper().removesuffix(".NS")
    by_name = len(needle) >= 2
    hits = []
    for m in ([market] if market else list(MARKETS)):
        names = _names(m)
        for r in _universe().get(m, []):
            nm = names_mod.lookup(names, r["symbol"]) or ""
            if needle in r["symbol"].upper() or (by_name and needle in nm.upper()):
                hits.append({**r, "name": nm or None, "market": m, "type": "stock"})
        for s in _indices().get(m, []):
            nm = names.get(s) or ""
            if needle in s.upper() or (by_name and needle in nm.upper()):
                hits.append({"symbol": s, "name": nm or None, "sector": "index series", "market": m, "type": "index"})

    liq = {m: _liquidity(m) for m in (list(MARKETS) if not market else [market])}

    def rank(r):
        """exact ticker; then a ticker or company name starting with the text; then a word in the name
        starting with it; then the rest — within each, the most traded first (so "micro" puts Microsoft
        above a micro-cap), indices after stocks."""
        b, nm = base(r["symbol"]), (r["name"] or "").upper()
        return (b != needle, not (b.startswith(needle) or nm.startswith(needle)), f" {needle}" not in nm,
                r["type"] != "stock", -liq.get(r["market"], {}).get(r["symbol"], 0), len(r["symbol"]))
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
    return {"latest": latest, "history": history, "name": _name(market, symbol), "classification": _classification(market, symbol)}


_class_cache: dict[str, tuple[float, dict, dict]] = {}


def _classification(market: str, symbol: str) -> dict | None:
    """sector › industry group › sub-industry of one stock (cached; the tables change monthly)."""
    import time
    from ..marketdata import industries as ind_mod, subindustries
    hit = _class_cache.get(market)
    if not hit or time.time() - hit[0] > 600:
        hit = (time.time(), ind_mod.load(market), subindustries.load(market))
        _class_cache[market] = hit
    ind, sub = hit[1].get(symbol), hit[2].get(symbol)
    if not ind:
        return None
    return {"sector": ind[0], "industry": ind[1], "sub": sub[1] if sub and sub[1] != "other" else None,
            "sub_key": subindustries.label(*sub) if sub and sub[1] != "other" else None}


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


def _peers(market: str) -> dict[str, dict]:
    """symbol -> {peer_group, peer_rs, peer_rank, peer_count} from the latest stock snapshot — the context
    every list shows (leader of a leading group, or not)."""
    df = _snap(market)
    if df is None or "peer_group" not in df.columns:
        return {}
    num = lambda v: None if v is None or v != v else int(v)
    return {s: {"peer_group": g if isinstance(g, str) else None, "peer_rs": num(r), "peer_rank": num(k), "peer_count": num(n)}
            for s, g, r, k, n in zip(df["symbol"], df["peer_group"], df["peer_rs"], df["peer_rank"], df["peer_count"])}


def _with_peer_cols(market: str, t: dict) -> dict:
    """Append peer group / group RS / rank-in-group columns to a strategy table."""
    cols, rows = t["columns"], t["rows"]
    if "symbol" not in cols or "peer_group" in cols:
        return t
    si, P = cols.index("symbol"), _peers(market)
    return {"columns": [*cols, "peer_group", "group_rs", "peer_rank"],
            "rows": [[*r, *(lambda p: [p.get("peer_group"), p.get("peer_rs"), p.get("peer_rank")])(P.get(r[si], {}))] for r in rows]}


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
        return _with_peer_cols(market, _with_name_col(market, cols, [[r.get(c) for c in cols] for r in records]))
    t = q("SELECT columns, rows FROM report_tables WHERE run_id=%s AND name='candidates'", (id,))
    if not t:
        raise HTTPException(404)
    return _with_peer_cols(market, _with_name_col(market, t[0][0], t[0][1]))


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
                    "screen_name": (d.get("screen") or {}).get("name"),
                    "style_label": d.get("style_label") or "", "style_rank": d.get("style_rank", 99),
                    "variant_of": (d.get("variant_of") or {}).get("key"),
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
_breadth_tried: dict = {}     # market -> the price day a top-up was last asked for
_sector_cache: dict[tuple, dict] = {}


def _breadth_topup(market: str) -> bool:
    """Ask for a breadth top-up when prices are newer than the stored breadth. Returns True while one is
    queued or running. Goes through the job queue (so it never collides with a running pipeline); when no
    worker is running it starts the job directly, as before."""
    jq = _jq()
    busy = [x for x in [jq.items(0)["running"], *jq.items(0)["queued"]] if x and "breadth" in x["targets"] and x["market"] in (market, "all")]
    if busy:
        return True
    job = _breadth_jobs.get(market)
    if job and job.poll() is None:
        return True
    last_price = q("SELECT max(date) FROM prices WHERE market=%s", (market,))[0][0]
    last_br = q("SELECT max(date) FROM breadth_daily WHERE market=%s", (market,))[0][0]
    if last_br is None or (last_price and last_price > last_br):
        tried = _breadth_tried.get(market)
        if tried == last_price:
            # a finished top-up that still leaves the newest day out means that day is a partial load
            # (e.g. a holiday with stray rows) — don't ask again for the same day
            return False
        _breadth_tried[market] = last_price
        if jq.worker_status()["alive"]:
            jq.enqueue(["breadth"], market, {}, requested_by="breadth page", skip_if_running=True)
        else:
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
    # the last 30 days only: the latest bar is in there, and the (market, date) index keeps it fast
    rows = q("""SELECT DISTINCT ON (market, symbol) market, symbol, date, close, sma200, high_252, rsi14
                FROM prices WHERE (market, symbol) IN %s AND date >= current_date - 30 ORDER BY market, symbol, date DESC""", (tuple(keys),))
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
    if market not in tuple(MARKETS):
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
    P = _peers(market)
    sectors.update({r["symbol"]: r["sector"] for r in _universe().get(market, []) if r["sector"] not in (None, "", "Unknown")})
    rows = []
    for sym, (c, v, vs, dv) in now.items():
        if sym not in eq or sym not in then or not then[sym][0]:
            continue
        if universe == "liquid" and ((dv or 0) < liq["value"] or c < liq["price"]):
            continue
        rows.append({"symbol": sym, "name": _name(market, sym), "sector": sectors.get(sym), "last": c, "chg": c - then[sym][0],
                     "pct": (c / then[sym][0] - 1) * 100, "volume": v, "rel_vol": v / vs if v and vs else None,
                     "value": c * v if v else None, "avg_value": dv, **P.get(sym, {})})
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
    for m in tuple(MARKETS):
        try:
            _sector_data(m)
        except Exception as exc:  # noqa: BLE001 - the page computes on demand instead
            print(f"sectors prewarm {m}: {exc}")


@app.get("/api/sectors")
def sectors_api(market: str = "us", level: str = "industry"):
    if level not in ("industry", "sector", "sub"):
        raise HTTPException(400, "level must be sector, industry or sub")
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
    # the level below: a sector's industry groups, an industry group's sub-industries
    child_level = {"sector": "industry", "industry": "sub"}.get(level)
    key = "sector" if level == "sector" else "industry"
    children = [x for x in data.get(child_level, []) if x[key] == group] if child_level else []
    return {"market": market, "date": data["date"], "level": level, "doc": data["doc"], "market_ret": data["market_ret"],
            "group": {k: v for k, v in g.items() if k != "members"},
            "members": [members[s] for s in g["members"]], "child_level": child_level,
            "children": [{k: v for k, v in x.items() if k not in ("series", "members")} for x in children]}


# ------------------------------------------------------------- screens & today's setups

def _latest_strategy_rows(market: str) -> dict:
    """strategy -> (run_id, rows) of each strategy's latest screening run in universe_history."""
    out = {}
    for strategy, run in q("SELECT strategy, max(run_id) FROM universe_history WHERE market=%s GROUP BY strategy", (market,)):
        rows = q("SELECT symbol, full_row FROM universe_history WHERE market=%s AND strategy=%s AND run_id=%s", (market, strategy, run))
        out[strategy] = (run, rows)
    return out


def _setups_by_symbol(market: str) -> dict:
    """symbol -> [{strategy, decision, setup, entry, stop}] for names a strategy marks tradeable or on watch."""
    from ..strategies import _REGISTRY
    out: dict[str, list] = {}
    for strategy, (run, rows) in _latest_strategy_rows(market).items():
        if strategy not in _REGISTRY:
            continue
        for sym, fr in rows:
            if fr.get("tradeable") is True or fr.get("watchlist_candidate") is True:
                out.setdefault(sym, []).append({"strategy": strategy, "decision": fr.get("decision"), "setup": fr.get("strategy_setup"),
                                                "entry": fr.get("entry"), "stop": fr.get("stop"), "tradeable": fr.get("tradeable") is True})
    return out


_snap_cache: dict = {}


def _snap(market: str, d=None):
    """A snapshot (screens/snapshot.py) as a DataFrame, cached in memory by (market, date)."""
    from ..screens import snapshot
    ds = snapshot.dates(market)
    if not ds:
        return None
    d = pd.Timestamp(d).date() if d else ds[-1]
    if d not in ds:
        raise HTTPException(404, f"no snapshot for {market} {d}")
    key = (market, d, snapshot._path(market, d).stat().st_mtime)
    if key not in _snap_cache:
        if len(_snap_cache) > 80:
            _snap_cache.clear()
        df = snapshot.load(market, d)
        if d != ds[-1]:   # past snapshots carry no classification: show today's (a company rarely changes industry)
            latest = snapshot.load(market, ds[-1]).set_index("symbol")
            for k in ("sector", "industry", "sub_industry"):
                if k in df.columns and df[k].isna().all():
                    df[k] = df["symbol"].map(latest[k])
        _snap_cache[key] = df
    return _snap_cache[key]


def _screen_def(key: str) -> dict:
    """A built-in screen ('stage2') or one of yours ('u12'): name, description, conditions, docs."""
    from ..screens import definitions
    from ..strategies import docs as sdocs
    if key in definitions.builtin():
        d = sdocs.screen_doc(key)
        return {"key": key, "builtin": True, "name": d["name"], "description": d["description"], "thesis": d["thesis"],
                "criteria": d["criteria"], "used_by": d["used_by"], "conditions": definitions.builtin()[key]["conditions"], "sort_by": "rs_rank"}
    if key in definitions.presets():
        p = definitions.presets()[key]
        return {"key": key, "builtin": True, "preset": True, "name": p["name"], "description": p["description"], "thesis": p["thesis"],
                "criteria": None, "used_by": [], "conditions": p["conditions"], "sort_by": "rs_rank"}
    if key.startswith("u") and key[1:].isdigit():
        u = definitions.get_user(int(key[1:]))
        if u:
            return {"key": key, "builtin": False, "id": u["id"], "name": u["name"], "description": u["description"], "conditions": u["conditions"],
                    "sort_by": u["sort_by"] or "rs_rank", "columns": u["columns"], "used_by": []}
    raise HTTPException(404, f"unknown screen {key}")


def _query(market: str, conditions: list, d=None, sort_by: str = "rs_rank", limit: int = 1000) -> dict:
    from ..screens import definitions, snapshot
    df = _snap(market, d)
    if df is None:
        return {"empty": True, "command": f"python -m jobs run screens --market {market}"}
    try:
        m = definitions.mask(df, conditions)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    hit = df[m]
    if sort_by in hit.columns:
        hit = hit.sort_values(sort_by, ascending=False, na_position="last")
    day = df.attrs["date"]
    ds = snapshot.dates(market)
    prev_d = max((x for x in ds if x < day), default=None)
    prev = set(_snap(market, prev_d).loc[lambda x: definitions.mask(x, conditions), "symbol"]) if prev_d else None
    setups = _setups_by_symbol(market) if day == ds[-1] else {}
    rows = []
    for rec in hit.head(limit).to_dict("records"):
        rec = {k: (None if isinstance(v, float) and v != v else v) for k, v in rec.items()}
        rec["name"] = _name(market, rec["symbol"])
        rec["new"] = prev is not None and rec["symbol"] not in prev
        rec["setups"] = setups.get(rec["symbol"], [])
        rows.append(rec)
    return {"market": market, "date": day.isoformat(), "dates": [x.isoformat() for x in reversed(ds)], "count": int(m.sum()),
            "universe": len(df), "tradable": int(df["tradable"].sum()), "prev_date": prev_d.isoformat() if prev_d else None,
            "dropped": sorted(prev - set(hit["symbol"])) if prev is not None else [], "rows": rows}


@app.get("/api/screen-fields")
def screen_fields(market: str = "us"):
    """The fields a screen can test, and for text fields (sector, industry…) the values present in the market's latest snapshot."""
    from ..screens import definitions, snapshot
    df = _snap(market)
    text = [k for k, _l, _g, kd, _d in snapshot.FIELDS if kd == "text"]
    values = {k: sorted(df[k].dropna().astype(str).unique().tolist()) for k in text if df is not None and k in df.columns}
    return {"fields": [{"key": k, "label": l, "group": g, "kind": kd, "description": d} for k, l, g, kd, d in snapshot.FIELDS],
            "ops": list(definitions.OPS), "values": values}


@app.get("/api/screens")
def screens_api(market: str = "us"):
    """Every screen — built-in and yours — with today's count, the change since the previous session and the top names."""
    from ..screens import definitions
    df = _snap(market)
    items = [{"key": k, "builtin": True, **{x: v for x, v in _screen_def(k).items() if x in ("name", "description", "used_by")},
              "conditions": v["conditions"]} for k, v in definitions.builtin().items()]
    items += [{"key": k, "builtin": True, "preset": True, "name": v["name"], "description": v["description"], "used_by": [],
               "conditions": v["conditions"]} for k, v in definitions.presets().items()]
    items += [{"key": f"u{u['id']}", "builtin": False, "name": u["name"], "description": u["description"], "conditions": u["conditions"], "used_by": []}
              for u in definitions.list_user()]
    if df is None:
        return {"market": market, "date": None, "screens": items, "command": f"python -m jobs run screens --market {market}"}
    from ..screens import snapshot
    ds = snapshot.dates(market)
    prev = _snap(market, ds[-2]) if len(ds) > 1 else None
    for it in items:
        try:
            m = definitions.mask(df, it["conditions"])
            it["count"] = int(m.sum())
            it["prev_count"] = int(definitions.mask(prev, it["conditions"]).sum()) if prev is not None else None
            top = df[m].sort_values("rs_rank", ascending=False).head(10)
            it["top"] = [{"symbol": s_, "name": _name(market, s_), "rs": None if r != r else int(r)} for s_, r in zip(top["symbol"], top["rs_rank"])]
        except ValueError as exc:
            it["error"] = str(exc)
    return {"market": market, "date": df.attrs["date"].isoformat(), "tradable": int(df["tradable"].sum()), "universe": len(df), "screens": items}


@app.get("/api/screens/{key}")
def screen_api(key: str, market: str = "us", date: str | None = None):
    d = _screen_def(key)
    return {"def": d, **_query(market, d["conditions"], date, d.get("sort_by") or "rs_rank")}


def _study(market: str, conditions: list) -> dict:
    from ..screens import study
    try:
        r = study.study(market, conditions)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if r.get("summary") and not r.get("empty"):
        r["compare"] = study.compare(market)
    return r


@app.get("/api/screens/{key}/study")
def screen_study_api(key: str, market: str = "us"):
    """Forward returns of the screen's qualifiers on each month-end vs all tradable stocks (screens/study.py)."""
    return _study(market, _screen_def(key)["conditions"])


@app.post("/api/screens/study")
def screen_study_draft(spec: dict = Body(...)):
    return _study(spec.get("market") or "us", spec.get("conditions") or [])


@app.post("/api/screens/query")
def screen_query(spec: dict = Body(...)):
    """Run unsaved conditions (the screen builder's live preview)."""
    return _query(spec.get("market") or "us", spec.get("conditions") or [], spec.get("date"), spec.get("sort_by") or "rs_rank", int(spec.get("limit") or 1000))


@app.post("/api/screens")
def screen_save(spec: dict = Body(...)):
    from ..screens import definitions
    try:
        u = definitions.save_user(spec.get("name", ""), spec.get("conditions") or [], spec.get("description", ""), spec.get("sort_by"),
                                  spec.get("columns"), spec.get("id"))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except Exception as exc:  # noqa: BLE001 - e.g. the name is taken
        raise HTTPException(400, "a screen with that name already exists" if "unique" in str(exc).lower() else str(exc))
    return {"key": f"u{u['id']}", **u}


@app.delete("/api/screens/{key}")
def screen_delete(key: str):
    from ..screens import definitions
    if not (key.startswith("u") and key[1:].isdigit()):
        raise HTTPException(400, "built-in screens cannot be deleted")
    definitions.delete_user(int(key[1:]))
    return {"ok": True}


def _class_cache_load(market: str):
    """(symbol -> (sector, industry, cap), symbol -> (industry, sub)), cached like _classification."""
    _classification(market, "")
    hit = _class_cache[market]
    return hit[1], hit[2]


@app.get("/api/setups")
def setups_api(market: str = "us"):
    """Today's setups: every strategy's tradeable and on-watch names from its latest run."""
    from ..strategies import _REGISTRY
    from ..strategies import docs as sdocs
    out, runs, P = [], [], _peers(market)
    for strategy, (run, rows) in sorted(_latest_strategy_rows(market).items()):
        if strategy not in _REGISTRY:
            continue
        doc = sdocs.strategy_doc(strategy)
        picks = [(sym, fr) for sym, fr in rows if fr.get("tradeable") is True or fr.get("watchlist_candidate") is True]
        runs.append({"strategy": strategy, "name": doc["name"], "run": run, "screened": len(rows),
                     "tradeable": sum(1 for _, fr in picks if fr.get("tradeable") is True), "watch": sum(1 for _, fr in picks if fr.get("tradeable") is not True),
                     "screen": doc["screen"]["name"] if doc.get("screen") else None})
        for sym, fr in picks:
            out.append({"strategy": strategy, "strategy_name": doc["name"], "symbol": sym, "name": _name(market, sym),
                        "tradeable": fr.get("tradeable") is True, "decision": fr.get("decision"), "setup": fr.get("strategy_setup"),
                        "price": fr.get("price"), "entry": fr.get("entry"), "stop": fr.get("stop"), "risk_pct": fr.get("risk_pct"),
                        "target_r": fr.get("target_r"), "quality": fr.get("setup_quality"), "sector": fr.get("sector"),
                        "wait_for": fr.get("wait_for"), "run": run, **P.get(sym, {})})
    return {"market": market, "runs": runs, "rows": out}


# ------------------------------------------------------------- run jobs from the web app

# The web app views data; jobs produce it. Run / Resume / Stop / schedules go through the job queue
# (jobs/queue.py); one worker (`python -m jobs worker`) runs it — the same `python -m jobs run ...` the
# terminal would — and the run log records every run, so the Data status page follows it live.
# Changing anything is allowed only from this machine.
_LOCAL = {"127.0.0.1", "::1", "localhost"}


def _jq():
    from jobs import queue
    return queue


def _job_running() -> dict | None:
    """The run in progress, if any: the queue's running item, or any run the run log shows as alive."""
    it = _jq().items(0)["running"]
    if it:
        return {"item": it["id"], "cmd": it["command"].replace("python -m jobs run ", ""), "started": it["started_at"], "from_queue": True}
    for r in status_mod.runs(q, 10):
        if r["status"] == "running":
            return {"run_id": r["id"], "cmd": r["job"], "started": r["started_at"], "from_queue": False}
    return None


def _require_local(request: Request) -> None:
    if (request.client.host if request.client else None) not in _LOCAL:
        raise HTTPException(403, "jobs can only be started from the machine running the web app")


@app.post("/api/jobs/run")
def jobs_run(request: Request, spec: dict = Body(...)):
    """Queue a run. spec: targets, market, strategies ('all' or [..]), from, force."""
    _require_local(request)
    from jobs.registry import JOBS, PIPELINES
    targets = [t for t in spec.get("targets") or [] if t in JOBS or t in PIPELINES]
    if not targets or len(targets) != len(spec.get("targets") or []):
        raise HTTPException(400, f"unknown job or pipeline in {spec.get('targets')}")
    market = spec.get("market") or "all"
    if market not in ("all", *MARKETS):
        raise HTTPException(400, f"unknown market {market}")
    st = spec.get("strategies")
    opts = {"strategies": (["all"] if st == "all" else st) or None, "from": spec.get("from"), "force": bool(spec.get("force"))}
    jq = _jq()
    it = jq.enqueue(targets, market, opts, requested_by="you")
    return {"ok": True, "item": it["id"], "duplicate": bool(it.get("duplicate")), "position": jq.position(it["id"]),
            "command": it["command"], "worker": jq.worker_status()}


@app.post("/api/jobs/stop")
def jobs_stop(request: Request, spec: dict = Body(default={})):
    """Stop the running queue item (or the one given); the run log then shows it as stopped."""
    _require_local(request)
    jq = _jq()
    iid = (spec or {}).get("item") or (jq.items(0)["running"] or {}).get("id")
    if not iid:
        raise HTTPException(409, "nothing from the queue is running")
    return {"ok": True, "result": jq.cancel(int(iid))}


@app.get("/api/queue")
def queue_api():
    jq = _jq()
    return {**jq.items(15), "worker": jq.worker_status()}


@app.post("/api/queue/{iid}/cancel")
def queue_cancel(request: Request, iid: int):
    _require_local(request)
    return {"result": _jq().cancel(iid)}


@app.post("/api/queue/{iid}/front")
def queue_front(request: Request, iid: int):
    _require_local(request)
    _jq().to_front(iid)
    return {"ok": True}


@app.post("/api/worker/start")
def worker_start(request: Request):
    """Start a worker in the background (it survives a server restart). Prefer the launchd agent, which also
    restarts it after a crash or a reboot: python -m jobs worker --install"""
    _require_local(request)
    jq = _jq()
    if jq.worker_status()["alive"]:
        return {"ok": True, "already": True}
    import datetime as _dt
    import os
    out = paths.LOGS_DIR / "worker.log"
    out.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "PYTHONPATH": str(paths.SCRIPTS_DIR)}
    with open(out, "a") as f:
        f.write(f"\n--- started from the web app {_dt.datetime.now():%Y-%m-%d %H:%M:%S} ---\n")
        f.flush()
        subprocess.Popen([sys.executable, "-m", "jobs", "worker"], cwd=str(paths.SCRIPTS_DIR), env=env, stdout=f,
                         stderr=subprocess.STDOUT, start_new_session=True)
    return {"ok": True}


@app.get("/api/schedules")
def schedules_api():
    from jobs.registry import JOBS, PIPELINES
    from ..strategies import list_strategies
    jq = _jq()
    last = {}
    for r in q("""SELECT DISTINCT ON (schedule_id) schedule_id, id, status, finished_at, run_id FROM job_queue
                  WHERE schedule_id IS NOT NULL ORDER BY schedule_id, id DESC"""):
        last[r[0]] = {"item": r[1], "status": r[2], "finished_at": r[3].isoformat() if r[3] else None, "run_id": r[4]}
    return {"schedules": [{**x, "last": last.get(x["id"]), "command": "python -m jobs " + " ".join(jq.command_for(x["targets"], x["market"], x["opts"]))}
                          for x in jq.schedules()],
            "targets": {"pipelines": [{"name": k, "summary": v["summary"], "jobs": [j if isinstance(j, str) else j[0] for j in v["jobs"]]} for k, v in PIPELINES.items()],
                        "jobs": [{"name": j.name, "summary": j.summary, "per_market": j.per_market} for j in JOBS.values()]},
            "strategies": list_strategies(), "worker": jq.worker_status(),
            "tz": __import__("datetime").datetime.now().astimezone().tzname()}


@app.post("/api/schedules")
def schedule_save(request: Request, spec: dict = Body(...)):
    _require_local(request)
    from jobs.registry import JOBS, PIPELINES
    if not spec.get("targets") or any(t not in JOBS and t not in PIPELINES for t in spec["targets"]):
        raise HTTPException(400, "choose what to run")
    try:
        return _jq().save_schedule(spec)
    except (ValueError, AssertionError) as exc:
        raise HTTPException(400, str(exc) or "invalid schedule")


@app.post("/api/schedules/{sid}/enabled")
def schedule_enabled(request: Request, sid: int, spec: dict = Body(...)):
    _require_local(request)
    _jq().set_enabled(sid, bool(spec.get("enabled")))
    return {"ok": True}


@app.post("/api/schedules/{sid}/run")
def schedule_run_now(request: Request, sid: int):
    _require_local(request)
    jq = _jq()
    s = next((x for x in jq.schedules() if x["id"] == sid), None)
    if not s:
        raise HTTPException(404)
    it = jq.enqueue(s["targets"], s["market"], s["opts"], requested_by="you", schedule_id=sid)
    return {"item": it["id"], "duplicate": bool(it.get("duplicate")), "position": jq.position(it["id"])}


@app.delete("/api/schedules/{sid}")
def schedule_delete(request: Request, sid: int):
    _require_local(request)
    _jq().delete_schedule(sid)
    return {"ok": True}


# ------------------------------------------------------------- sub-industries (review & edit)

@app.get("/api/subindustries")
def subindustries_api(market: str = "us"):
    """Every industry group with tradable members: its members' sub-industry, where the label came from, and
    their official code — for Library → Sub-industries."""
    from ..marketdata import classcodes, industries as ind_mod, subindustries as sub_mod
    from ..screens import snapshot
    ind, detail = ind_mod.load(market), sub_mod.load_detail(market)
    try:
        codes = classcodes.load(market)
    except Exception:  # noqa: BLE001
        codes = {}
    snap = snapshot.load(market)
    trad = set(snap.loc[snap["tradable"], "symbol"]) if not snap.empty else set()
    cap = dict(zip(snap["symbol"], snap["market_cap_usd"])) if "market_cap_usd" in snap else {}
    groups: dict[str, dict] = {}
    for sym, (sec, indus, _c) in ind.items():
        if sym not in trad:
            continue
        g = groups.setdefault(indus, {"industry": indus, "sector": sec, "members": []})
        d = detail.get(sym)
        mc = cap.get(sym)
        g["members"].append({"symbol": sym, "name": _name(market, sym), "cap": None if mc is None or mc != mc else round(float(mc), 2),
                             "sub": d[1] if d else None, "source": d[2] if d else None, "code": (codes.get(sym) or {}).get("code")})
    out = []
    for g in groups.values():
        g["members"].sort(key=lambda x: -(x["cap"] or 0))
        g["split"] = any(m["sub"] for m in g["members"])
        g["subs"] = sorted({m["sub"] for m in g["members"] if m["sub"] and m["sub"] != "other"})
        g["open"] = sum(1 for m in g["members"] if m["source"] in ("other", "suggested"))
        out.append(g)
    out.sort(key=lambda g: (g["sector"] or "", g["industry"]))
    split_members = [m for g in out if g["split"] for m in g["members"]]
    return {"market": market, "groups": out,
            "coverage": {"tradable": len(trad), "in_split_groups": len(split_members),
                         "labelled": sum(1 for m in split_members if m["source"] not in ("other",)),
                         "reviewed": sum(1 for m in split_members if m["source"] in ("you", "curated", "rule")),
                         "suggested": sum(1 for m in split_members if m["source"] == "suggested"),
                         "other": sum(1 for m in split_members if m["source"] == "other")},
            "scheme": {"us": "Nasdaq industry (SIC-based)", "india": "BSE industry"}.get(market, "")}


@app.post("/api/subindustries")
def subindustries_set(request: Request, spec: dict = Body(...)):
    """Label stocks (spec: market, symbols, sub — null/empty reverts them to the automatic label)."""
    _require_local(request)
    from ..marketdata import industries as ind_mod, subindustries as sub_mod
    market = spec.get("market") or "us"
    ind = ind_mod.load(market)
    n = 0
    for sym in spec.get("symbols") or []:
        if sym in ind:
            sub_mod.set_label(market, sym, ind[sym][1], (spec.get("sub") or "").strip() or None)
            n += 1
    _class_cache.pop(market, None)   # the chart details pick up the new label
    return {"ok": True, "changed": n}


# ------------------------------------------------------------- chart drawings
# The drawing layer's items are opaque client JSON; the server only keys them by
# market+symbol so annotations survive browsers and machines (see chart_drawings.py).

from .. import chart_drawings as draw_mod


@app.get("/api/drawings/{market}/{symbol}")
def drawings_get(market: str, symbol: str):
    if market not in MARKETS:
        raise HTTPException(404, f"unknown market {market}")
    return draw_mod.get(market, symbol.upper())


@app.put("/api/drawings/{market}/{symbol}")
def drawings_put(market: str, symbol: str, body: dict = Body(...)):
    if market not in MARKETS:
        raise HTTPException(404, f"unknown market {market}")
    items = body.get("items")
    if not isinstance(items, list):
        raise HTTPException(422, "items must be a list")
    return draw_mod.put(market, symbol.upper(), items)


# ------------------------------------------------------------- notes

from .. import notes as notes_mod


@app.get("/api/notes")
def notes_list(q: str = "", tag: str | None = None, market: str | None = None, symbol: str | None = None):
    return {"notes": notes_mod.search(q.strip(), tag, market, symbol), "tags": notes_mod.tags()}


@app.get("/api/notes/{nid}")
def notes_get(nid: int):
    n = notes_mod.get(nid)
    if not n:
        raise HTTPException(404, "note not found")
    return n


@app.post("/api/notes")
def notes_create(note: dict = Body(...)):
    return notes_mod.create(note.get("title", ""), note.get("body", ""), note.get("tags"), note.get("symbols"), bool(note.get("pinned")))


@app.put("/api/notes/{nid}")
def notes_update(nid: int, note: dict = Body(...)):
    n = notes_mod.update(nid, **{k: note.get(k) for k in ("title", "body", "tags", "symbols", "pinned")})
    if not n:
        raise HTTPException(404, "note not found")
    return n


@app.delete("/api/notes/{nid}")
def notes_delete(nid: int):
    n = notes_mod.delete(nid)
    if not n:
        raise HTTPException(404, "note not found")
    return n


# ------------------------------------------------------------- TODO list

TODO_PATH = paths.REPO_ROOT / "TODO.md"
_TASK = re.compile(r"^(\s*[-*] \[)([ xX])(\].*)$")


@app.get("/api/todo")
def todo_get():
    """TODO.md at the repository root, read live (so edits made in an editor show at once)."""
    text = TODO_PATH.read_text() if TODO_PATH.exists() else "# TODO\n\n## Inbox\n"
    return {"markdown": text, "path": str(TODO_PATH.relative_to(paths.REPO_ROOT))}


@app.post("/api/todo")
def todo_add(text: str = Body(..., embed=True)):
    """Append an item under '## Inbox' (created if missing)."""
    item = " ".join(text.split())
    if not item:
        raise HTTPException(400, "empty item")
    md = TODO_PATH.read_text() if TODO_PATH.exists() else "# TODO\n"
    lines = md.splitlines()
    line = f"- [ ] {item} _(added {__import__('datetime').date.today().isoformat()})_"
    try:
        i = next(k for k, l in enumerate(lines) if l.strip().lower() == "## inbox")
        j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")), len(lines))
        while j > i + 1 and not lines[j - 1].strip():
            j -= 1
        lines.insert(j, line)
        if j == i + 1:
            lines.insert(i + 1, "")
    except StopIteration:
        lines += ["", "## Inbox", "", line]
    TODO_PATH.write_text("\n".join(lines).rstrip() + "\n")
    return {"ok": True}


@app.post("/api/todo/toggle")
def todo_toggle(index: int = Body(...), line: str = Body(...)):
    """Tick / untick the index-th task line, if it still reads as the client saw it."""
    lines = TODO_PATH.read_text().splitlines()
    tasks = [k for k, l in enumerate(lines) if _TASK.match(l)]
    if index >= len(tasks) or lines[tasks[index]].strip() != line.strip():
        raise HTTPException(409, "TODO.md changed since it was loaded — reload the page")
    m = _TASK.match(lines[tasks[index]])
    lines[tasks[index]] = m.group(1) + (" " if m.group(2) in "xX" else "x") + m.group(3)
    TODO_PATH.write_text("\n".join(lines) + "\n")
    return {"ok": True}


# ------------------------------------------------------------- post-market

@app.get("/api/postmarket")
def postmarket_api(market: str = "us", date: str | None = None):
    """One day's post-market analysis (analytics/postmarket.py) and the stored history's tone timeline."""
    from ..analytics import postmarket as pm
    pm.init_schema()
    hist = q("""SELECT date, payload->'tone'->>'label', (payload->'tone'->>'score')::int,
                       (payload->'counts'->>'up')::int, (payload->'counts'->>'down')::int
                FROM postmarket_daily WHERE market=%s ORDER BY date DESC LIMIT 400""", (market,))
    if not hist:
        return {"market": market, "empty": True, "command": f"python -m jobs run postmarket --market {market} --days 60"}
    d = date or hist[0][0].isoformat()
    row = q("SELECT payload, generated_at FROM postmarket_daily WHERE market=%s AND date=%s", (market, d))
    if not row:
        raise HTTPException(404, f"no post-market analysis stored for {market} {d}")
    payload = row[0][0]
    for sig in (payload.get("tone") or {}).get("signals", []):   # stored before the bearish wording existed
        sig.setdefault("text_not", pm.TONE_RULES_NOT.get(sig.get("key"), "Not met: " + sig.get("text", "")))
    return {"payload": payload, "generated_at": row[0][1].isoformat(),
            "history": [{"date": h[0].isoformat(), "tone": h[1], "score": h[2], "up": h[3], "down": h[4]} for h in hist]}


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
    worst = max((i["status"] for m in tuple(MARKETS) for i in fresh[m]["items"] if i["key"] in ("prices", "breadth", "screening")),
                key=["ok", "warn", "missing", "stale"].index, default="ok")
    return {"now": __import__("datetime").datetime.now().astimezone().isoformat(), "freshness": fresh, "runs": runs,
            "latest_daily": status_mod.run_detail(q, daily["id"]) if daily else None,
            "jobs": overview["jobs"], "pipelines": overview["pipelines"],
            "running": [r["id"] for r in running], "overall": worst,
            "job_running": _job_running(), "queue": _jq().items(8), "worker": _jq().worker_status(),
            "command": f"cd {paths.SCRIPTS_DIR} && PYTHONPATH=. .venv/bin/python -m jobs run daily",
            "worker_command": f"cd {paths.SCRIPTS_DIR} && PYTHONPATH=. .venv/bin/python -m jobs worker --install"}


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
    peers: dict = {}
    for e in items:
        closes = last.get((e["market"], e["symbol"]), [])
        e["last"] = closes[0] if closes else None
        e["change_pct"] = (closes[0] / closes[1] - 1) * 100 if len(closes) > 1 and closes[1] else None
        e["sector"] = sectors.get((e["market"], e["symbol"]))
        e["name"] = _name(e["market"], e["symbol"])
        e.update(peers.setdefault(e["market"], _peers(e["market"])).get(e["symbol"], {}))
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
