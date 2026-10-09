"""Post-market analysis: what happened in a market on one trading day, kept for every day.

Computed from stored data only (after the `prices`, `breadth`, `sectors` and `screen` jobs) and
saved as one JSON document per market per day in `postmarket_daily`, so any past day can be
re-read exactly as it was reported. Sections:

  tone        a rule-based read of the day from six signals (TONE_RULES)
  indexes     benchmark closes and day change, vs their 50/200-day averages and 52-week high; volatility index
  breadth     advancers/decliners, big movers, new highs/lows, % above the 50-day — vs the previous day
              and the 10-day average (from breadth_daily)
  sectors     equal-weight day return of every sector and industry group; RS-rating movers and rotation
              changes from the stored sector ranking (sector_daily)
  movers      top gainers and losers among liquid stocks
  volume      unusual volume: liquid stocks trading UNUSUAL_RVOL x their 50-day average volume and moving
              UNUSUAL_MOVE or more
  highs_lows  new 52-week highs and lows among liquid stocks
  watchlists  every name on your watchlists and the screener's picks: day move, volume, 50-day crossings,
              new highs/lows, earnings soon
  screener    per strategy: candidates new and dropped versus the previous run
  earnings    watched and screened names reporting in the next EARNINGS_DAYS days

    PYTHONPATH=. python3 -m swing_screener.analytics.postmarket --market india            # latest session
    PYTHONPATH=. python3 -m swing_screener.analytics.postmarket --market us --days 30     # backfill 30 sessions
    PYTHONPATH=. python3 -m swing_screener.analytics.postmarket --market us --date 2026-10-02 --force
"""

import argparse
import datetime as dt
import json
import logging
import time

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import db, freshness, industries, names
from . import breadth as br

logger = logging.getLogger(__name__)

LIQUID_VALUE = {"us": 10e6, "india": 10e7}   # 20-day average traded value ($10M / ₹10 Cr) for the stock lists
LIQUID_PRICE = {"us": 5.0, "india": 20.0}
TOP_N = 10                  # gainers / losers / unusual volume rows
LIST_N = 15                 # new highs / lows rows
UNUSUAL_RVOL = 2.5          # volume vs its 50-day average
UNUSUAL_MOVE = 0.02         # and a day move of at least 2%
MIN_MEMBERS = 3             # a sector / industry needs this many liquid stocks for a day return
DAILY_CLIP = 0.5            # a member's day return beyond ±50% is clipped (splits, spin-offs, bad prints)
EARNINGS_DAYS = 10          # "earnings soon": reporting within this many calendar days
HL_BARS = 252               # 52-week high / low window (sessions before the day)
TONE_RULES = [
    ("index_50", "Benchmark closed above its 50-day average"),
    ("index_200", "Benchmark closed above its 200-day average"),
    ("adv_dec", "More stocks rose than fell"),
    ("highs_lows", "More new 52-week highs than lows"),
    ("above50", "Half or more of stocks above their 50-day average"),
    ("vol_down", "Volatility index fell (fear easing)"),
]
# what the page says when a signal is not met: the statement that is actually true, read as bearish
TONE_RULES_NOT = {
    "index_50": "Benchmark closed below its 50-day average",
    "index_200": "Benchmark closed below its 200-day average",
    "adv_dec": "More stocks fell than rose (or as many)",
    "highs_lows": "As many or more new 52-week lows than highs",
    "above50": "Fewer than half of stocks above their 50-day average",
    "vol_down": "Volatility index rose or held (fear not easing)",
}
TONE = ((5, "Strong"), (4, "Positive"), (2, "Mixed"), (1, "Weak"), (0, "Negative"))   # (min signals, label)

SCHEMA = """
CREATE TABLE IF NOT EXISTS postmarket_daily (
    market VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    payload JSONB NOT NULL,
    PRIMARY KEY (market, date)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _q(sql: str, params: tuple = ()) -> list:
    with db.get_connection().cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def doc(market: str) -> dict:
    val = f"₹{LIQUID_VALUE[market] / 1e7:g} Cr" if market == "india" else f"${LIQUID_VALUE[market] / 1e6:g}M"
    cur = "₹" if market == "india" else "$"
    return {
        "tone": "Market tone counts how many of six signals were bullish: " + "; ".join(t for _, t in TONE_RULES)
                + ". " + ", ".join(f"{n}+ = {lbl}" for n, lbl in TONE) + ".",
        "liquid": f"Stock lists cover common stocks trading at least {val} a day (20-day average) at {cur}{LIQUID_PRICE[market]:g} or more.",
        "volume": f"Unusual volume: at least {UNUSUAL_RVOL:g}× the 50-day average volume with a move of {UNUSUAL_MOVE:.0%} or more — "
                  "often institutions buying (up) or selling (down).",
        "sectors": f"Sector and industry moves are equal-weight averages of their liquid members (groups of {MIN_MEMBERS}+). "
                   "RS-rating changes compare the stored sector ranking with about a week earlier.",
        "highs_lows": f"New highs / lows: the day's high (low) beyond the previous {HL_BARS} sessions' range.",
    }


# ------------------------------------------------------------------ pieces

def _day(market: str, d) -> pd.DataFrame:
    rows = _q("""SELECT symbol, open, high, low, close, volume, vol_sma50, dollar_vol_sma20, sma50, sma200
                 FROM prices WHERE market=%s AND date=%s AND close > 0""", (market, d))
    return pd.DataFrame(rows, columns=["symbol", "open", "high", "low", "close", "volume", "vol50", "dv20", "sma50", "sma200"]).set_index("symbol")


def _indexes(market: str, d) -> list[dict]:
    out = []
    for key, _, label in [*br.INDEXES[market], br.VOL_INDEX[market]]:
        rows = _q("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date <= %s ORDER BY date DESC LIMIT 260",
                  (market, key, d))
        if len(rows) < 2:
            continue
        s = pd.Series([c for _, c in reversed(rows)], index=[x for x, _ in reversed(rows)], dtype=float)
        last, prev = float(s.iloc[-1]), float(s.iloc[-2])
        sma50 = float(s.tail(50).mean()) if len(s) >= 50 else None
        sma200 = float(s.tail(200).mean()) if len(s) >= 200 else None
        out.append({"key": key, "label": label, "vol": key == br.VOL_INDEX[market][0], "date": s.index[-1].isoformat(),
                    "close": last, "chg": last - prev, "pct": (last / prev - 1) * 100,
                    "above50": None if sma50 is None else last > sma50, "above200": None if sma200 is None else last > sma200,
                    "vs50": None if not sma50 else (last / sma50 - 1) * 100, "from_high": (last / float(s.max()) - 1) * 100})
    return out


def _breadth(market: str, d) -> dict | None:
    rows = _q("""SELECT date, n, adv, dec, up4, dn4, highs, lows, above5, above50 FROM breadth_daily
                 WHERE market=%s AND date <= %s ORDER BY date DESC LIMIT 11""", (market, d))
    if not rows or rows[0][0] != d:
        return None
    cols = ["date", "n", "adv", "dec", "up4", "dn4", "highs", "lows", "above5", "above50"]
    df = pd.DataFrame(rows, columns=cols)
    cur, prev = df.iloc[0], (df.iloc[1] if len(df) > 1 else None)
    avg10 = df.iloc[1:11][cols[1:]].mean() if len(df) > 1 else None
    pick = lambda r: None if r is None else {k: (float(r[k]) if r[k] is not None else None) for k in cols[1:]}
    return {"today": pick(cur), "prev": pick(prev), "prev_date": prev["date"].isoformat() if prev is not None else None,
            "avg10": pick(avg10)}


def _group_moves(day: pd.DataFrame, ind: dict) -> dict:
    moves = {"sector": {}, "industry": {}}
    for sym, r in day.iterrows():
        if sym not in ind:
            continue
        sec, indus, _ = ind[sym]
        for level, g in (("sector", sec), ("industry", indus)):
            moves[level].setdefault(g, []).append(r["pct_c"])
    out = {}
    for level, groups in moves.items():
        rows = [{"group": g, "n": len(v), "pct": float(np.mean(v)), "up": sum(x > 0 for x in v) / len(v)}
                for g, v in groups.items() if len(v) >= MIN_MEMBERS]
        out[level] = sorted(rows, key=lambda x: -x["pct"])
    for r in out["industry"]:
        r["sector"] = next((ind[s][0] for s in ind if ind[s][1] == r["group"]), None)
    return out


def _sector_rs(market: str, d) -> dict | None:
    """RS-rating movers and rotation changes from the stored daily ranking (sector_daily), when it exists."""
    try:
        days = [r[0] for r in _q("SELECT DISTINCT date FROM sector_daily WHERE market=%s AND date <= %s ORDER BY date DESC LIMIT 6",
                                 (market, d))]
    except Exception:  # noqa: BLE001 - table not created yet
        return None
    if not days or days[0] != d:
        return None
    now = {(lv, g): (rs, q) for lv, g, rs, q in _q("SELECT level, grp, rs, quadrant FROM sector_daily WHERE market=%s AND date=%s", (market, d))}
    out = {"date": d.isoformat(), "compared_with": None, "rs_up": [], "rs_down": [], "quadrant_changes": []}
    if len(days) < 2:
        return out
    then_d, prev_d = days[-1], days[1]
    then = {(lv, g): rs for lv, g, rs, _ in _q("SELECT level, grp, rs, quadrant FROM sector_daily WHERE market=%s AND date=%s", (market, then_d))}
    prevq = {(lv, g): q for lv, g, _, q in _q("SELECT level, grp, rs, quadrant FROM sector_daily WHERE market=%s AND date=%s", (market, prev_d))}
    deltas = [{"level": lv, "group": g, "rs": rs, "delta": rs - then[(lv, g)]} for (lv, g), (rs, _) in now.items()
              if lv == "industry" and rs is not None and then.get((lv, g)) is not None]
    out["compared_with"] = then_d.isoformat()
    out["rs_up"] = sorted([x for x in deltas if x["delta"] > 0], key=lambda x: -x["delta"])[:8]
    out["rs_down"] = sorted([x for x in deltas if x["delta"] < 0], key=lambda x: x["delta"])[:8]
    out["quadrant_changes"] = sorted([{"level": lv, "group": g, "from": prevq[(lv, g)], "to": q, "rs": rs}
                                      for (lv, g), (rs, q) in now.items() if prevq.get((lv, g)) and q and prevq[(lv, g)] != q],
                                     key=lambda x: (x["level"] != "sector", x["to"] not in ("Leading", "Improving"), -(x["rs"] or 0)))
    return out


def _row(sym: str, r, nm: dict, ind: dict) -> dict:
    return {"symbol": sym, "name": names.lookup(nm, sym), "sector": (ind.get(sym) or (None,))[0],
            "close": float(r["close"]), "pct": float(r["pct"]) * 100, "rvol": None if pd.isna(r["rvol"]) else float(r["rvol"]),
            "value": float(r["close"] * r["volume"]) if pd.notna(r["volume"]) else None}


def _screener(market: str, d, next_d) -> list[dict]:
    """Per strategy: the run that screened `d`'s prices vs the run before it."""
    out = []
    lo, hi = d.isoformat(), (next_d.isoformat() if next_d else "9999")
    for (strategy,) in _q("SELECT DISTINCT strategy FROM universe_history WHERE market=%s ORDER BY 1", (market,)):
        run = _q("""SELECT max(run_id) FROM universe_history WHERE market=%s AND strategy=%s AND run_id >= %s AND run_id < %s""",
                 (market, strategy, lo, hi))[0][0]
        if not run:
            continue
        prev = _q("SELECT max(run_id) FROM universe_history WHERE market=%s AND strategy=%s AND run_id < %s", (market, strategy, run))[0][0]

        def sets(rid):
            if not rid:
                return {}, {}
            rows = _q("SELECT symbol, full_row FROM universe_history WHERE market=%s AND strategy=%s AND run_id=%s", (market, strategy, rid))
            trade = {s: fr for s, fr in rows if fr.get("tradeable") is True}
            watch = {s: fr for s, fr in rows if fr.get("watchlist_candidate") is True}
            return trade, watch
        t1, w1 = sets(run)
        t0, w0 = sets(prev)
        brief = lambda fr: {"decision": fr.get("decision"), "entry": fr.get("entry"), "stop": fr.get("stop"), "setup": fr.get("strategy_setup")}
        out.append({"strategy": strategy, "run": run, "prev_run": prev, "tradeable": len(t1), "watch": len(w1),
                    "new_tradeable": [{"symbol": s, **brief(t1[s])} for s in sorted(set(t1) - set(t0))],
                    "dropped_tradeable": sorted(set(t0) - set(t1)),
                    "new_watch": sorted(set(w1) - set(w0)), "dropped_watch": sorted(set(w0) - set(w1))})
    return out


def _earnings(market: str) -> dict:
    from ..marketdata.earnings import earnings_cache_path
    p = earnings_cache_path(market)
    if not p.exists():
        return {}
    df = pd.read_csv(p, keep_default_na=False)
    out = {}
    for s, e in zip(df["symbol"], df["next_earnings_date"]):
        try:
            out[str(s)] = dt.date.fromisoformat(str(e)[:10])
        except ValueError:
            pass
    return out


# ------------------------------------------------------------------ compute

def compute(market: str, d: dt.date | None = None) -> dict:
    t0 = time.time()
    days = freshness.sessions(market)
    if d is None:
        d = days[-1]
    if d not in days:
        raise ValueError(f"{d} is not a complete {market} session")
    i = days.index(d)
    p = days[i - 1]
    next_d = days[i + 1] if i + 1 < len(days) else None
    today, prev = _day(market, d), _day(market, p)
    common = today.index.intersection(prev.index)
    today = today.loc[common].copy()
    today["pct"] = today["close"] / prev.loc[common, "close"] - 1   # real move, for the lists
    today["pct_c"] = today["pct"].clip(-DAILY_CLIP, DAILY_CLIP)     # clipped, for group averages
    today["rvol"] = today["volume"] / today["vol50"].replace(0, np.nan)
    eligible = set(br.eligible(market))
    ind, nm = industries.load(market), names.load(market)
    stocks = today[today.index.isin(eligible)]
    liquid = stocks[(stocks["dv20"].fillna(0) >= LIQUID_VALUE[market]) & (stocks["close"] >= LIQUID_PRICE[market])]

    # 52-week range before the day
    since = days[max(0, i - HL_BARS)]
    hl = pd.DataFrame(_q("""SELECT symbol, max(high), min(low), count(*) FROM prices WHERE market=%s AND symbol = ANY(%s)
                            AND date >= %s AND date < %s GROUP BY symbol""", (market, list(liquid.index), since, d)),
                      columns=["symbol", "hi", "lo", "n"]).set_index("symbol")
    hl = hl[hl["n"] >= 200]
    lq = liquid.join(hl, how="left")
    new_hi = lq[lq["high"] > lq["hi"]]
    new_lo = lq[lq["low"] < lq["lo"]]
    row = lambda s: _row(s, lq.loc[s], nm, ind)

    indexes = _indexes(market, d)
    bread = _breadth(market, d)
    bench = next((x for x in indexes if not x["vol"]), None)
    vol = next((x for x in indexes if x["vol"]), None)
    bt = (bread or {}).get("today") or {}
    signals = {
        "index_50": bench["above50"] if bench else None, "index_200": bench["above200"] if bench else None,
        "adv_dec": (bt["adv"] > bt["dec"]) if bt else None, "highs_lows": (bt["highs"] > bt["lows"]) if bt else None,
        "above50": (bt["above50"] >= bt["n"] / 2) if bt else None, "vol_down": (vol["chg"] < 0) if vol else None,
    }
    score = sum(1 for v in signals.values() if v)
    tone = next(lbl for n, lbl in TONE if score >= n)

    wl_syms: dict[str, list] = {}
    from ..screening import watchlist
    for lst in watchlist.lists():
        for it in watchlist.items(lst["id"]):
            if it["market"] == market:
                wl_syms.setdefault(it["symbol"], []).append(lst["name"])
    for e in watchlist.entries(market):
        wl_syms.setdefault(e["symbol"], []).append("Screener picks")
    earn = _earnings(market)
    wl = []
    for s, lists in wl_syms.items():
        if s not in today.index:
            continue
        r, pr = today.loc[s], prev.loc[s]
        cross = None
        if pd.notna(r["sma50"]) and pd.notna(pr["sma50"]):
            if pr["close"] <= pr["sma50"] and r["close"] > r["sma50"]:
                cross = "up"
            elif pr["close"] >= pr["sma50"] and r["close"] < r["sma50"]:
                cross = "down"
        e = earn.get(s)
        wl.append({**_row(s, r, nm, ind), "lists": lists, "cross50": cross,
                   "above50": bool(r["close"] > r["sma50"]) if pd.notna(r["sma50"]) else None,
                   "new_high": s in new_hi.index, "new_low": s in new_lo.index,
                   "earnings": e.isoformat() if e and d < e <= d + dt.timedelta(days=EARNINGS_DAYS) else None})
    wl.sort(key=lambda x: -abs(x["pct"]))

    screener = _screener(market, d, next_d)
    soon = set(wl_syms) | {x["symbol"] for s in screener for x in s["new_tradeable"]} | {
        s for (s,) in _q("""SELECT DISTINCT h.symbol FROM universe_history h JOIN (SELECT strategy, max(run_id) r FROM universe_history
                            WHERE market=%s AND run_id < %s GROUP BY strategy) l ON l.strategy=h.strategy AND l.r=h.run_id
                            WHERE h.market=%s AND ((h.full_row->>'tradeable')::boolean OR (h.full_row->>'watchlist_candidate')::boolean)""",
                         (market, (next_d or d + dt.timedelta(days=5)).isoformat(), market))}
    earnings = sorted([{"symbol": s, "name": names.lookup(nm, s), "date": earn[s].isoformat(), "days": (earn[s] - d).days,
                        "watched": s in wl_syms}
                       for s in soon if s in earn and d < earn[s] <= d + dt.timedelta(days=EARNINGS_DAYS)], key=lambda x: x["date"])

    gainers = liquid.sort_values("pct", ascending=False)
    unusual = liquid[(liquid["rvol"] >= UNUSUAL_RVOL) & (liquid["pct"].abs() >= UNUSUAL_MOVE)].sort_values("rvol", ascending=False)
    payload = {
        "market": market, "market_name": MARKETS[market].name, "date": d.isoformat(), "prev_date": p.isoformat(),
        "generated_at": dt.datetime.now().astimezone().isoformat(), "doc": doc(market),
        "counts": {"stocks": int(len(stocks)), "liquid": int(len(liquid)), "up": int((stocks["pct"] > 0).sum()),
                   "down": int((stocks["pct"] < 0).sum()), "new_highs": int(len(new_hi)), "new_lows": int(len(new_lo))},
        "tone": {"label": tone, "score": score, "of": len(TONE_RULES),
                 "signals": [{"key": k, "text": t, "text_not": TONE_RULES_NOT[k], "ok": signals[k]} for k, t in TONE_RULES]},
        "indexes": indexes, "breadth": bread,
        "sectors": _group_moves(liquid, ind), "sector_rs": _sector_rs(market, d),
        "movers": {"gainers": [row(s) for s in gainers.index[:TOP_N] if lq.loc[s, "pct"] > 0],
                   "losers": [row(s) for s in gainers.index[::-1][:TOP_N] if lq.loc[s, "pct"] < 0]},
        "volume": {"up": [row(s) for s in unusual.index if lq.loc[s, "pct"] > 0][:TOP_N],
                   "down": [row(s) for s in unusual.index if lq.loc[s, "pct"] < 0][:TOP_N]},
        "highs_lows": {"highs": [row(s) for s in new_hi.sort_values("dv20", ascending=False).index[:LIST_N]],
                       "lows": [row(s) for s in new_lo.sort_values("dv20", ascending=False).index[:LIST_N]]},
        "watchlists": wl, "screener": screener, "earnings": earnings,
    }
    logger.info("postmarket %s %s: tone %s (%d/%d), %d liquid stocks, %.1fs", market, d, tone, score, len(TONE_RULES), len(liquid), time.time() - t0)
    return payload


def save(payload: dict) -> None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO postmarket_daily (market, date, payload) VALUES (%s, %s, %s)
                       ON CONFLICT (market, date) DO UPDATE SET payload=EXCLUDED.payload, generated_at=now()""",
                    (payload["market"], payload["date"], json.dumps(payload, default=str)))


def run(market: str, days: int = 1, date: dt.date | None = None, force: bool = False) -> list[str]:
    """Analyse the latest session (or `date`), plus up to `days - 1` earlier ones; existing days are kept unless `force`."""
    init_schema()
    sessions = freshness.sessions(market)
    targets = [date] if date else sessions[-days:]
    have = {r[0] for r in _q("SELECT date FROM postmarket_daily WHERE market=%s", (market,))}
    done = []
    for d in targets:
        if d in have and not force and d != sessions[-1]:
            continue
        save(compute(market, d))
        done.append(d.isoformat())
    return done


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--date", type=dt.date.fromisoformat)
    ap.add_argument("--days", type=int, default=1, help="also analyse this many latest sessions (backfill)")
    ap.add_argument("--force", action="store_true", help="recompute days already stored")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(run(a.market, a.days, a.date, a.force))


if __name__ == "__main__":
    main()
