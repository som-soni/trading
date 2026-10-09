"""Sector and industry-group analysis: which groups are leading, and who leads them.

For every Yahoo sector and industry (marketdata/industries.py) in a market:

  - Returns over 1W–12M, equal-weight (the typical member) and cap-weight
    (the big names), and the same relative to the market — the equal-weight
    average of every stock in the analysis, so a group's edge is measured
    against the typical stock, not against a handful of mega-caps.
  - RS rating 1–99: an IBD-style composite of relative return
    (40% 3M, 20% each 6M / 9M / 12M), ranked across groups, plus its change
    over the last month — a rising rating flags a group coming into favour.
  - Breadth inside the group: % of members above their 50- and 200-day
    averages, members at new 52-week highs vs lows, % up over 3 months —
    a move carried by many members is sturdier than one carried by a few.
  - Relative Rotation Graph co-ordinates (weekly): RS-Ratio (is the group's
    relative strength above its recent average?) and RS-Momentum (is that
    improving?), giving the Leading / Weakening / Lagging / Improving quadrant
    and an 8-week tail.
  - Every member, ranked by the same RS composite, with distance from its
    52-week high, trend and quality score — the leaders inside the group.

Three levels: sector (11), industry group (Yahoo, ~145) and, for large mixed
groups, sub-industry (marketdata/subindustries.py: curated + rules).

Only common stocks trading at least MIN_VALUE a day (20-day average) above
MIN_PRICE count, and groups need MIN_MEMBERS of them. The web app's Sectors
page shows this; `doc()` is the page's "how to read it" text, rendered from
the constants below so it cannot drift from the code.

    PYTHONPATH=. python3 -m swing_screener.analytics.sectors --market us   # print the industry ranking
"""

import argparse
import datetime as dt
import logging
import time

import numpy as np
import pandas as pd

from ..marketdata import db, industries, names
from . import breadth as br

logger = logging.getLogger(__name__)

MIN_VALUE = {"us": 2e6, "india": 2e7}       # average daily traded value, 20 days ($2M / ₹2 Cr)
MIN_PRICE = {"us": 3.0, "india": 10.0}
MIN_MEMBERS = 3
HORIZONS = {"1W": 5, "1M": 21, "3M": 63, "6M": 126, "12M": 252}
RS_WEIGHTS = ((63, 0.4), (126, 0.2), (189, 0.2), (252, 0.2))   # (bars, weight) of the RS composite
RS_CHANGE_BARS = 21          # the RS rating is compared with this many bars ago
RRG_WEEKS = 10               # RS-Ratio: weekly relative strength vs its average over this many weeks
RRG_MOM_WEEKS = 4            # RS-Momentum: RS-Ratio vs its value this many weeks ago
RRG_TAIL = 8                 # weeks of tail on the rotation graph
DAILY_CLIP = 0.5             # a single-day member return beyond ±50% is clipped (spin-offs, bad prints)
COMPLETE_SHARE = 0.8         # a session needs this share of a normal day's rows to count as loaded
LOOKBACK_DAYS = 560          # calendar days of history loaded (12M returns + RRG warm-up)
BENCH_INDEX = {"us": ("SPX", "S&P 500"), "india": ("NIFTY500", "Nifty 500")}
_ANCHORS = {"us": ("SPY", "AAPL", "MSFT", "JPM", "XOM"),
            "india": ("RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "ICICIBANK.NS")}


def doc(market: str) -> dict:
    cur = "₹" if market == "india" else "$"
    val = f"₹{MIN_VALUE[market] / 1e7:g} Cr" if market == "india" else f"${MIN_VALUE[market] / 1e6:g}M"
    w = ", ".join(f"{int(wt * 100)}% {b // 21}M" for b, wt in RS_WEIGHTS)
    return {
        "universe": f"Common stocks trading at least {val} a day (20-day average) at {cur}{MIN_PRICE[market]:g} or more, "
                    f"grouped by Yahoo's sector / industry; groups need {MIN_MEMBERS}+ such members.",
        "returns": "Equal-weight (EW) return is the average member's return — what the typical stock in the group did. "
                   "Cap-weight (CW) is weighted by market cap — what the big names did. EW well above CW means broad "
                   "participation; CW well above EW means a few giants are carrying the group.",
        "relative": "Relative returns are against the market's typical stock (the equal-weight average of every stock "
                    f"analysed), so a group is judged against the field, not against a few mega-caps. The "
                    f"{BENCH_INDEX[market][1]} return is shown for reference.",
        "rs": f"RS rating (1–99) ranks groups on relative return weighted {w}, like IBD's group ranks. "
              f"Δ is the change versus {RS_CHANGE_BARS} trading days ago — a sharply rising rating often marks "
              "a group coming into favour before it reaches the top.",
        "breadth": "Breadth: % of members above their 50- and 200-day averages, and members at a new 52-week closing "
                   "high vs low. Leadership that keeps broadening is sturdier than a rally carried by two or three names.",
        "rrg": f"Rotation graph (weekly): RS-Ratio = 100 × relative strength ÷ its {RRG_WEEKS}-week average (right of 100: "
               f"relative strength is in an uptrend); RS-Momentum = 100 × RS-Ratio ÷ its value {RRG_MOM_WEEKS} weeks ago "
               "(above 100: improving). Groups tend to rotate clockwise: Improving → Leading → Weakening → Lagging. "
               f"Tails show the last {RRG_TAIL} weeks.",
        "caveats": "Classification is Yahoo's and current — a company that changed business is grouped by what it is "
                   "today. Daily member returns beyond ±50% are clipped, so a spin-off or bad print cannot swing a group. "
                   "Stocks that were delisted are missing, which flatters weak groups' history (survivorship bias).",
    }


def _sessions(market: str, since: dt.date) -> list:
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT date FROM prices WHERE market=%s AND symbol = ANY(%s) AND date >= %s
                       GROUP BY date HAVING count(*) >= 3 ORDER BY date""", (market, list(_ANCHORS[market]), since))
        return [r[0] for r in cur.fetchall()]


def _bench(market: str, since) -> pd.Series:
    series, _ = BENCH_INDEX[market]
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date >= %s ORDER BY date",
                    (market, series, since))
        rows = cur.fetchall()
    return pd.Series({d: c for d, c in rows}, dtype=float)


def _quality(market: str) -> dict:
    try:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT DISTINCT ON (symbol) symbol, quality_score FROM quality_scores WHERE market=%s "
                        "ORDER BY symbol, computed_at DESC", (market,))
            return dict(cur.fetchall())
    except Exception:  # noqa: BLE001 - quality tracker not set up
        return {}


def _ret(idx: pd.Series, bars: int) -> float | None:
    if len(idx) <= bars or not idx.iloc[-1 - bars]:
        return None
    return float(idx.iloc[-1] / idx.iloc[-1 - bars] - 1)


def _rs_score(rel: dict) -> float | None:
    parts = [(rel.get(b), w) for b, w in RS_WEIGHTS if rel.get(b) is not None]
    if not parts:
        return None
    return sum(v * w for v, w in parts) / sum(w for _, w in parts)


def _rank(scores: dict) -> dict:
    """{key: score} -> {key: 1..99 percentile rank}"""
    valid = {k: v for k, v in scores.items() if v is not None and np.isfinite(v)}
    if not valid:
        return {}
    s = pd.Series(valid).rank(pct=True)
    return {k: int(round(1 + 98 * (p - 1 / len(s)) / max(1e-9, 1 - 1 / len(s)))) if len(s) > 1 else 50 for k, p in s.items()}


def _rrg(rs: pd.Series) -> list[dict]:
    """Weekly RS line -> tail of {ratio, mom} points (oldest first)."""
    wk = rs.iloc[::-1].iloc[::5].iloc[::-1]  # every 5th session counting back from the latest
    ratio = 100 * wk / wk.rolling(RRG_WEEKS).mean()
    mom = 100 * ratio / ratio.shift(RRG_MOM_WEEKS)
    pts = pd.DataFrame({"ratio": ratio, "mom": mom}).dropna().tail(RRG_TAIL)
    return [{"date": d.isoformat(), "ratio": round(float(r.ratio), 3), "mom": round(float(r.mom), 3)} for d, r in pts.iterrows()]


def quadrant(p: dict | None) -> str | None:
    if not p:
        return None
    return ("Leading" if p["mom"] >= 100 else "Weakening") if p["ratio"] >= 100 else ("Improving" if p["mom"] >= 100 else "Lagging")


def compute(market: str) -> dict:
    t0 = time.time()
    ind = industries.load(market)
    if not ind:
        return {"market": market, "empty": True,
                "command": f"python3 -m swing_screener.marketdata.industries --market {market}"}
    since = dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)
    days = _sessions(market, since)
    eligible = [s for s in br.eligible(market) if s in ind]
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, close, sma50, sma200, dollar_vol_sma20 FROM prices
                       WHERE market=%s AND symbol = ANY(%s) AND date >= %s AND close > 0""", (market, eligible, since))
        raw = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "close", "sma50", "sma200", "dv"])
    raw = raw[raw["date"].isin(set(days))]
    # a day with fewer than COMPLETE_SHARE of a normal day's rows is not a session: a load still
    # in progress (the daily update running) or a holiday with a few stray rows
    counts = raw.groupby("date").size().reindex(days).fillna(0)
    normal = counts.iloc[-21:-1].median() if len(counts) > 21 else counts.max()
    days = [d for d in days if counts[d] >= COMPLETE_SHARE * normal]  # also drops holidays with stray rows
    raw = raw[raw["date"] <= days[-1]]
    close = raw.pivot(index="date", columns="symbol", values="close").reindex(days).sort_index()
    last = raw.sort_values("date").groupby("symbol").tail(1).set_index("symbol")
    d1 = close.index[-1]
    last = last[last["date"] == d1]  # traded on the latest session
    liquid = last[(last["dv"].fillna(0) >= MIN_VALUE[market]) & (last["close"] >= MIN_PRICE[market])].index
    close = close[list(liquid)].ffill(limit=3)

    rets = close.pct_change(fill_method=None).clip(-DAILY_CLIP, DAILY_CLIP)
    mkt_idx = (1 + rets.mean(axis=1).fillna(0)).cumprod()
    bench = _bench(market, since)

    # ---- members
    nm, qual = names.load(market), _quality(market)
    from ..marketdata import subindustries
    subs = subindustries.load(market)
    hi252 = close.rolling(252, min_periods=200).max().iloc[-1]
    lo252 = close.rolling(252, min_periods=200).min().iloc[-1]
    members = {}
    for sym in close.columns:
        px = close[sym].dropna()
        if len(px) < 30:
            continue
        idx = (1 + rets[sym].fillna(0)).cumprod()
        rel = {b: (_ret(idx, b) - _ret(mkt_idx, b)) for b, _ in RS_WEIGHTS if _ret(idx, b) is not None}
        sec, indus, cap = ind[sym]
        lr = last.loc[sym]
        members[sym] = {
            "symbol": sym, "name": names.lookup(nm, sym), "sector": sec, "industry": indus, "cap": cap,
            "sub": subs[sym][1] if sym in subs else None,
            "last": float(px.iloc[-1]), **{h: _ret(idx, b) for h, b in HORIZONS.items()},
            "rs_score": _rs_score(rel),
            "from_high": float(px.iloc[-1] / hi252[sym] - 1) if pd.notna(hi252.get(sym)) else None,
            "above50": bool(lr["close"] > lr["sma50"]) if pd.notna(lr["sma50"]) else None,
            "above200": bool(lr["close"] > lr["sma200"]) if pd.notna(lr["sma200"]) else None,
            "new_high": bool(pd.notna(hi252.get(sym)) and px.iloc[-1] >= hi252[sym]),
            "new_low": bool(pd.notna(lo252.get(sym)) and px.iloc[-1] <= lo252[sym]),
            "quality": qual.get(sym),
        }
    m_rank = _rank({s: m["rs_score"] for s, m in members.items()})
    for s, m in members.items():
        m["rs"] = m_rank.get(s)

    # ---- groups, at both levels
    out = {"market": market, "date": d1.isoformat(), "stocks": len(members), "doc": doc(market),
           "market_ret": {h: _ret(mkt_idx, b) for h, b in HORIZONS.items()},
           "bench": {"label": BENCH_INDEX[market][1],
                     **{h: _ret(bench[bench.index <= d1], b) for h, b in HORIZONS.items()}} if len(bench) else None}
    for level in ("industry", "sector", "sub"):
        groups = {}
        for sym, m in members.items():
            if level == "sub":
                if sym in subs and subs[sym][1] != "other":  # leftovers are not a group: not ranked
                    groups.setdefault(subindustries.label(*subs[sym]), []).append(sym)
            else:
                groups.setdefault(ind[sym][1 if level == "industry" else 0], []).append(sym)
        rows, scores, prev_scores = {}, {}, {}
        for g, syms in groups.items():
            if len(syms) < MIN_MEMBERS:
                continue
            gidx = (1 + rets[syms].mean(axis=1).fillna(0)).cumprod()
            rs_line = gidx / mkt_idx
            rel = {b: _ret(gidx, b) - _ret(mkt_idx, b) for b, _ in RS_WEIGHTS if _ret(gidx, b) is not None}
            prev = {b: _ret(gidx.iloc[:-RS_CHANGE_BARS], b) - _ret(mkt_idx.iloc[:-RS_CHANGE_BARS], b)
                    for b, _ in RS_WEIGHTS if _ret(gidx.iloc[:-RS_CHANGE_BARS], b) is not None}
            scores[g], prev_scores[g] = _rs_score(rel), _rs_score(prev)
            ms = [members[s] for s in syms]
            caps = np.array([m["cap"] or 0 for m in ms], dtype=float)
            cw = {}
            for h in HORIZONS:
                v = np.array([m[h] if m[h] is not None else np.nan for m in ms])
                ok = ~np.isnan(v) & (caps > 0)
                cw[h] = float((v[ok] * caps[ok]).sum() / caps[ok].sum()) if ok.any() else None
            frac = lambda k: (sum(1 for m in ms if m[k]) / sum(1 for m in ms if m[k] is not None)) if any(m[k] is not None for m in ms) else None
            rrg = _rrg(rs_line)
            spark = rs_line.iloc[::-1].iloc[::5].iloc[::-1].tail(27)
            rows[g] = {
                "group": g, "sector": ind[syms[0]][0], "n": len(syms),
                "industry": ind[syms[0]][1] if level != "sector" else None,
                "ew": {h: _ret(gidx, b) for h, b in HORIZONS.items()},
                "rel": {h: (_ret(gidx, b) - _ret(mkt_idx, b)) if _ret(gidx, b) is not None else None for h, b in HORIZONS.items()},
                "cw": cw,
                "above50": frac("above50"), "above200": frac("above200"),
                "highs": sum(m["new_high"] for m in ms), "lows": sum(m["new_low"] for m in ms),
                "up3m": (sum(1 for m in ms if (m["3M"] or 0) > 0) / len(ms)),
                "rrg": rrg, "quadrant": quadrant(rrg[-1] if rrg else None),
                "spark": [round(float(v / spark.iloc[0]), 4) for v in spark],
                "members": [s for s in sorted(syms, key=lambda s: -(members[s]["rs_score"] if members[s]["rs_score"] is not None else -9))],
                # daily group index and RS line over the last year, for the group chart
                "series": [{"time": d.isoformat(), "group": round(float(gv), 5), "market": round(float(mv), 5)}
                           for d, gv, mv in zip(gidx.index[-260:], gidx.iloc[-260:], mkt_idx.iloc[-260:])],
            }
        rank, prev_rank = _rank(scores), _rank(prev_scores)
        for g, r in rows.items():
            r["rs"], r["rs_prev"] = rank.get(g), prev_rank.get(g)
        out[level] = sorted(rows.values(), key=lambda r: -(r["rs"] or 0))
    out["members"] = members
    logger.info("sectors %s: %d stocks, %d industries, %d sectors in %.1fs", market, len(members),
                len(out["industry"]), len(out["sector"]), time.time() - t0)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", choices=["us", "india"], default="us")
    ap.add_argument("--level", choices=["industry", "sector"], default="industry")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    r = compute(a.market)
    if r.get("empty"):
        raise SystemExit(f"No industry data yet — run: {r['command']}")
    pc = lambda v: "" if v is None else f"{v * 100:+.1f}%"
    print(f"{a.market.upper()} {a.level} groups, {r['date']} — {r['stocks']} stocks")
    for g in r[a.level]:
        print(f"{g['rs'] or '':>3} {(g['rs'] or 0) - (g['rs_prev'] or 0):+4d}  {g['group'][:40]:40s} n={g['n']:<4d} "
              f"3M {pc(g['ew']['3M']):>7} 12M {pc(g['ew']['12M']):>8}  >50d {(g['above50'] or 0) * 100:3.0f}%  {g['quadrant'] or ''}")


if __name__ == "__main__":
    main()
