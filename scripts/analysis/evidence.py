"""Gather what the framework's checks read for one stock — stored data only, never a download.

  company     the Fundamentals page's build (fundamentals/company.py): statements, ratios, growth, peers,
              shareholding, estimates and the strategy views (Minervini SEPA's F2 / F8 feed check G5)
  metrics     the shared quarterly metrics (fundamentals/growth.py) — EPS / sales growth, ROE, turnarounds
  snap        the stock's row of the day's snapshot (screens/snapshot.py): trend, RS, peer group, risk
  frame       that row as a one-row DataFrame, for the built-in screens' conditions
  quality     the Quality page's score, tests and live valuation (fundamentals/quality.py assess)
  estimates   analysts' consensus and surprise history (marketdata/estimates.py summary)
"""

from __future__ import annotations

import datetime as dt

from fundamentals import company, growth
from fundamentals import quality as qual
from swing_screener.marketdata import db, financials


def _clean(v):
    return None if isinstance(v, float) and v != v else v


def _quality(market: str, symbol: str, srow: dict) -> dict | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('quality_scores') IS NOT NULL")
        if not cur.fetchone()[0]:
            return None
        cur.execute("SELECT quality_score, tests, metrics FROM quality_scores WHERE market=%s AND symbol=%s", (market, symbol))
        r = cur.fetchone()
    if not r or not r[2]:
        return None
    score, tests, m = r
    price = {k: srow.get(k) for k in ("close", "sma200", "high_252", "rsi14")} if srow.get("close") else None
    return {"score": score, "tests": tests, "metrics": m, "assess": qual.assess(m, price)}


def _metrics(market: str, symbol: str) -> dict:
    scored = company._scores(market, [symbol]).get(symbol)
    if scored:
        return scored[0]
    return growth.metrics(financials.load(market, [symbol]).get(symbol, []), financials.load_meta(market).get(symbol) or {})


def gather(market: str, symbol: str, snap=None) -> dict:
    """Everything evaluate() reads. `snap`: the day's snapshot DataFrame (the server passes its cached one)."""
    if snap is None:
        from swing_screener.screens import snapshot
        try:
            snap = snapshot.load(market)
        except Exception:  # noqa: BLE001 — no snapshot yet: the trend and risk checks read n/a
            snap = None
    frame, srow = None, {}
    if snap is not None and len(snap) and symbol in set(snap["symbol"]):
        frame = snap[snap["symbol"] == symbol].reset_index(drop=True)
        srow = {k: _clean(v) for k, v in frame.iloc[0].to_dict().items()}
    co = company.build(market, symbol, snap)
    views = {v["key"]: v.get("result") for v in co.get("views") or []}
    asof = snap.attrs.get("date") if snap is not None else None
    return {
        "market": market, "symbol": symbol, "name": co.get("name"), "bank": co.get("layout") == "bank",
        "asof": str(asof) if asof else dt.date.today().isoformat(),
        "company": co, "metrics": _metrics(market, symbol), "snap": srow, "frame": frame,
        "quality": _quality(market, symbol, srow), "estimates": co.get("estimates"), "views": views,
    }


# ---------------------------------------------------------------- entry timing (entry.py), as of one session

OUTCOME_SESSIONS = (5, 21, 63)  # what the price did after the as-of day, for a past (saved) entry analysis ...
OUTCOME_PATH_SESSIONS = 252     # ... and its bars for up to this many sessions, to replay your plan against


def _weekly(raw):
    agg = {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    return raw.resample("W-FRI").agg(agg).dropna(subset=["close"])


GROUP_TREND_SESSIONS = 21     # the group's RS "a month earlier": this many stored ratings back


def _group_rs(market: str, grp: str, day) -> dict:
    """The group's RS rating on (or just before) `day`, and GROUP_TREND_SESSIONS ratings earlier."""
    level = "sub" if " › " in grp else "industry"
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT date, rs FROM group_rs_history WHERE market=%s AND level=%s AND grp=%s AND date <= %s
                       ORDER BY date DESC LIMIT %s""", (market, level, grp, day, GROUP_TREND_SESSIONS + 1))
        rows = cur.fetchall()
    if not rows:
        return {}
    out = {"rs": float(rows[0][1]), "rs_date": str(rows[0][0])}
    if len(rows) > GROUP_TREND_SESSIONS:
        out.update(rs_then=float(rows[-1][1]), then=str(rows[-1][0]))
    return out


def _next_results(market: str, symbol: str, after) -> "dt.date | None":
    """The first stored results filing after `after` (quarterly_results.filed) — a past day's next report."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT min(filed) FROM quarterly_results WHERE market=%s AND symbol=%s AND filed > %s", (market, symbol, after))
        r = cur.fetchone()
    return r[0] if r else None


def gather_entry(market: str, symbol: str, date=None, snap_loader=None) -> dict:
    """What the entry checks read, as of the last session on or before `date` (default: the latest stored).

    Everything about the stock itself is recomputed from its stored bars up to that session — the snapshot's
    own row function (screens/snapshot.py `_row`), the Weinstein stage machine, the chart-pattern detectors,
    support and resistance (core/sr_levels.py) — so a past date reads only what was known then. What needs
    the whole market on one day (RS rank, the group's RS rating) comes from the latest snapshot on or before
    it, and says which. `snap_loader(market, date)`: the server's cached snapshot loader."""
    import pandas as pd

    from fundamentals import canslim
    from swing_screener.backtesting import spec
    from swing_screener.config import MARKETS
    from swing_screener.core import demand_supply as dsup
    from swing_screener.core import indicators as ind
    from swing_screener.core import sr_levels as srl
    from swing_screener.marketdata import cache
    from swing_screener.screens import snapshot
    from swing_screener.strategies import get_strategy
    from swing_screener.strategies import stage_analysis as sa

    cfg = MARKETS[market]
    load = snap_loader or (lambda m, d: snapshot.load(m, d))
    raw_all = cache.load_cached(market, symbol)
    if raw_all is None or raw_all.empty:
        return {"market": market, "symbol": symbol, "error": "no prices stored for this symbol"}
    raw_all = raw_all.sort_index()
    raw = raw_all[raw_all.index <= pd.Timestamp(date)] if date else raw_all
    if len(raw) < snapshot.MIN_SNAPSHOT_BARS:
        return {"market": market, "symbol": symbol, "error": f"needs {snapshot.MIN_SNAPSHOT_BARS} sessions of history before the date"}
    asof = raw.index[-1]
    daily = ind.enrich_daily(raw)
    bench = snapshot._bench(market, asof - pd.Timedelta(days=snapshot.LOOKBACK_DAYS + 10))
    bench = bench[bench.index <= asof]
    row = {k: _clean(v) for k, v in snapshot._row(cfg, symbol, raw, daily, len(daily) - 1, bench).items()}
    b3 = snapshot._bench_ret(bench, daily.index[-64], asof) if len(daily) > 64 else None
    row["rel_r3m"] = row["r3m"] - b3 if row.get("r3m") is not None and b3 is not None else None

    # the stock's group, by today's classification (the latest snapshot), rated as it stood on the date:
    # group_rs_history (analytics/group_history.py) is the Sectors page's rating rebuilt point in time
    xs, group = {}, {}
    sds = snapshot.dates(market)
    if sds:
        today = load(market, sds[-1])
        me = today[today["symbol"] == symbol]
        if len(me):
            r = {k: _clean(v) for k, v in me.iloc[0].to_dict().items()}
            xs = {k: r.get(k) for k in ("peer_group", "sector", "industry", "earnings_days", "market_cap_usd")}
            xs["earnings_from"] = str(sds[-1])
            pg = r.get("peer_group")
            if pg:
                members = list(today[(today["peer_group"] == pg) & (today["tradable"] == True)]["symbol"])  # noqa: E712
                group = {"name": pg, "members": members, **_group_rs(market, pg, asof.date())}
                # the members' breadth on the date, from their own bars
                bars = cache.load_many_cached(market, members, since=asof - pd.Timedelta(days=120))
                above = []
                for b_ in bars.values():
                    b_ = b_[b_.index <= asof]["close"]
                    if len(b_) >= 50:
                        above.append(bool(b_.iloc[-1] > b_.iloc[-50:].mean()))
                group.update(n=len(above), above50=sum(above) / len(above) if above else None)
    # RS rank and the stock's place among its group's members: the latest snapshot on or before the date
    past = [d for d in sds if d <= asof.date()]
    if past:
        snap = load(market, past[-1])
        me = snap[snap["symbol"] == symbol]
        xs["rs_rank"] = _clean(me.iloc[0]["rs_rank"]) if len(me) else None
        xs["snapshot_date"] = str(past[-1])
        if group.get("members") and xs["rs_rank"] is not None:
            rs = snap[snap["symbol"].isin(group["members"])]["rs_rank"].dropna()
            xs["peer_rank"], xs["peer_count"] = int((rs > xs["rs_rank"]).sum()) + 1, int(len(rs))
    frame = pd.DataFrame([{**row, **{k: xs.get(k) for k in ("rs_rank",)}}])

    # the market: the strategies' own buy gates (backtesting/spec.py market_ok), breadth, distribution days
    def at(series):
        s = series[series.index <= asof]
        return s.iloc[-1] if len(s) else None
    mk = {"gate": at(spec.market_ok(market, guide=True)), "trend": at(spec.market_ok(market))}
    br = spec.breadth_pct50(market)
    br = br[br.index <= asof]
    if len(br):
        mk["breadth"] = float(br.iloc[-1])
        mk["breadth_then"] = float(br.iloc[-11]) if len(br) > 10 else None
    bd = cache.load_cached(market, cfg.benchmark_ticker)
    if bd is not None and len(bd):
        bd = bd[bd.index <= asof]
        mk["dist_days"] = dsup.accumulation_distribution_days(bd, canslim.DIST_SESSIONS)[1]
        mk["index_from_high"] = float(bd["close"].iloc[-1] / bd["high"].iloc[-252:].max() - 1)
        mk["index"] = cfg.benchmark_symbol

    # the chart: Weinstein's stage (weekly), live patterns, support and resistance, volume
    wk = _weekly(raw)
    stage = None
    if len(wk) > sa.MA_WEEKS + sa.SLOPE_WEEKS:
        st = sa.stage_series(wk)
        stage = {"stage": int(st.iloc[-1]) or None, "line": sa.line_state(wk)[0]}
    try:
        patterns = get_strategy("chart_pattern").detect_live(daily, market, symbol)
    except Exception:  # noqa: BLE001 — a detector failing on odd data must not blank the analysis
        patterns = []
    patterns = [{k: v for k, v in p.items() if k != "shapes"} for p in patterns]
    sr = srl.levels(raw, "D")
    close = float(daily["close"].iloc[-1])
    zones = [z for z in sr.get("zones") or [] if not z.get("congestion")]
    sup = sorted((z for z in zones if z["role"] in ("support", "pivot") and z["bottom"] < close), key=lambda z: -z["top"])
    res = sorted((z for z in zones if z["role"] in ("resistance", "pivot") and z["top"] > close and z["bottom"] > close * 1.001),
                 key=lambda z: z["bottom"])
    vol = {"updown": dsup.up_down_volume_ratio(raw, canslim.UPDOWN_SESSIONS),
           "recent": float(raw["volume"].iloc[-10:].mean()), "avg50": _clean(float(daily["vol_sma50"].iloc[-1]))}

    # the next results: the stored date when the as-of is the snapshot's day, else the next filing after it
    nxt = None
    if xs.get("earnings_days") is not None and xs.get("earnings_from") == str(asof.date()):
        nxt = int(xs["earnings_days"])
    else:
        f = _next_results(market, symbol, asof.date())
        nxt = (f - asof.date()).days if f else None

    # what happened after (a past as-of only)
    after = raw_all[raw_all.index > asof]
    outcome = None
    if len(after):
        outcome = {"last_date": str(after.index[-1].date()), "last": float(after["close"].iloc[-1]),
                   "high": float(after["high"].max()), "low": float(after["low"].min()),
                   "returns": {n: float(after["close"].iloc[n - 1] / close - 1) for n in OUTCOME_SESSIONS if len(after) >= n},
                   "path": [[str(t.date()), float(h), float(lo), float(c)] for t, h, lo, c in
                            after[["high", "low", "close"]].iloc[:OUTCOME_PATH_SESSIONS].itertuples()]}
    return {"market": market, "symbol": symbol, "asof": str(asof.date()), "latest": str(raw_all.index[-1].date()),
            "close": close, "atr": _clean(float(daily["atr14"].iloc[-1])), "row": row, "frame": frame, "xs": xs, "group": group,
            "market_state": mk, "stage": stage, "patterns": patterns, "support": sup[:3], "resistance": res[:3], "volume": vol,
            "results_in_days": nxt, "outcome": outcome, "currency": cfg.currency_symbol}
