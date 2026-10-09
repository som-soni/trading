"""Group RS ratings as they stood on past dates — for studies that ask whether group strength matters.

The Sectors page (analytics/sectors.py) rates each industry group and sub-industry 1–99 on its relative
return (40% 3-month, 20% each 6/9/12-month) against the typical stock, from an equal-weight index of its
liquid members. Its daily table (`sector_daily`) only goes back to when it started running, so this
module rebuilds the same rating for any past date from stored prices, using only prices up to that date:

  * members: the group's stocks that were liquid on that date (the Sectors page's MIN_VALUE / MIN_PRICE),
    a group needing MIN_MEMBERS of them;
  * index: daily returns clipped at ±DAILY_CLIP, averaged across members, compounded;
  * rating: relative return at 63/126/189/252 sessions vs the equal-weight index of every liquid stock,
    weighted RS_WEIGHTS, ranked 1–99 across groups (the Sectors page's own `_rs_score` / `_rank`).

Membership uses today's classification (industry group and sub-industry) — a company rarely changes
business, so the look-ahead is small, but it is not zero.

Stored in `group_rs_history` (market, date, level, grp, rs, n). `ensure(market, dates)` computes the
dates not stored yet.

    PYTHONPATH=. python3 -m swing_screener.analytics.group_history --market us --check
"""

import argparse
import logging
import time

import numpy as np
import pandas as pd

from ..marketdata import db, industries, subindustries
from . import sectors as sect
from .breadth import eligible

logger = logging.getLogger(__name__)
WINDOW = max(b for b, _ in sect.RS_WEIGHTS)          # 252 sessions

SCHEMA = """
CREATE TABLE IF NOT EXISTS group_rs_history (
    market VARCHAR(16) NOT NULL, date DATE NOT NULL, level TEXT NOT NULL, grp TEXT NOT NULL,
    rs INT, n INT, PRIMARY KEY (market, date, level, grp)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def load(market: str, dates: list | None = None) -> dict:
    """{date: {"industry": {grp: rs}, "sub": {grp: rs}}} for the stored dates (or the given ones)."""
    init_schema()
    with db.get_connection().cursor() as cur:
        if dates:
            cur.execute("SELECT date, level, grp, rs FROM group_rs_history WHERE market=%s AND date = ANY(%s)", (market, list(dates)))
        else:
            cur.execute("SELECT date, level, grp, rs FROM group_rs_history WHERE market=%s", (market,))
        out: dict = {}
        for d, lvl, g, rs in cur.fetchall():
            out.setdefault(d, {"industry": {}, "sub": {}}).setdefault(lvl, {})[g] = rs
    return out


def compute(market: str, dates: list) -> dict:
    """The ratings on each date (sessions only; a date without prices is skipped)."""
    t0 = time.time()
    dates = sorted(pd.Timestamp(d) for d in dates)
    ind = industries.load(market)
    subs = {s: subindustries.label(i, sub) for s, (i, sub) in subindustries.load(market).items() if sub != "other"}
    syms = [s for s in eligible(market) if s in ind]
    since = dates[0] - pd.Timedelta(days=int(WINDOW * 1.6) + 30)
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, close, dollar_vol_sma20 FROM prices
                       WHERE market=%s AND symbol = ANY(%s) AND date >= %s AND date <= %s AND close > 0""",
                    (market, syms, since.date(), dates[-1].date()))
        raw = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "close", "dv"])
    raw["date"] = pd.to_datetime(raw["date"])
    close = raw.pivot(index="date", columns="symbol", values="close").sort_index()
    dv = raw.pivot(index="date", columns="symbol", values="dv").reindex(close.index)
    # a session = a day most stocks traded (drops holidays with a few stray rows)
    n = close.notna().sum(axis=1)
    close = close[n >= 0.5 * n.rolling(20, min_periods=1).median()]
    dv = dv.reindex(close.index)
    rets = close.ffill(limit=3).pct_change(fill_method=None).clip(-sect.DAILY_CLIP, sect.DAILY_CLIP)
    logger.info("group history %s: %d sessions × %d stocks loaded (%.0fs)", market, len(close), close.shape[1], time.time() - t0)

    out = {}
    for d in dates:
        if d not in close.index:
            continue
        i = close.index.get_loc(d)
        if i < WINDOW:
            continue
        c, v = close.iloc[i], dv.iloc[i]
        liquid = c.index[(c >= sect.MIN_PRICE[market]) & (v.fillna(0) >= sect.MIN_VALUE[market])]
        win = rets.iloc[i - WINDOW: i + 1]
        mkt_idx = (1 + win[liquid].mean(axis=1).fillna(0)).cumprod()
        res = {}
        for level, key in (("industry", lambda s: ind[s][1]), ("sub", lambda s: subs.get(s))):
            groups: dict = {}
            for s in liquid:
                g = key(s)
                if g:
                    groups.setdefault(g, []).append(s)
            scores, sizes = {}, {}
            for g, members in groups.items():
                if len(members) < sect.MIN_MEMBERS:
                    continue
                gidx = (1 + win[members].mean(axis=1).fillna(0)).cumprod()
                rel = {b: sect._ret(gidx, b) - sect._ret(mkt_idx, b) for b, _ in sect.RS_WEIGHTS if sect._ret(gidx, b) is not None}
                scores[g], sizes[g] = sect._rs_score(rel), len(members)
            ranks = sect._rank(scores)
            res[level] = {g: (ranks.get(g), sizes[g]) for g in scores}
        out[d.date()] = res
    logger.info("group history %s: %d dates rated in %.0fs", market, len(out), time.time() - t0)
    return out


def ensure(market: str, dates: list) -> dict:
    """Ratings for these dates, computing and storing any not stored yet."""
    init_schema()
    have = load(market, dates)
    todo = [d for d in dates if d not in have]
    if todo:
        new = compute(market, todo)
        rows = [(market, d, lvl, g, rs, n) for d, levels in new.items() for lvl, groups in levels.items() for g, (rs, n) in groups.items()]
        if rows:
            db.execute_values("""INSERT INTO group_rs_history (market, date, level, grp, rs, n) VALUES %s
                                 ON CONFLICT (market, date, level, grp) DO UPDATE SET rs=EXCLUDED.rs, n=EXCLUDED.n""", rows)
        have = load(market, dates)
    return have


def check(market: str) -> dict:
    """How close the rebuilt rating is to the Sectors page's own, on the latest day both have."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM sector_daily WHERE market=%s", (market,))
        d = cur.fetchone()[0]
        cur.execute("SELECT level, grp, rs FROM sector_daily WHERE market=%s AND date=%s AND level IN ('industry','sub')", (market, d))
        actual = {(lvl, g): rs for lvl, g, rs in cur.fetchall()}
    rebuilt = compute(market, [d]).get(d, {})
    pairs = [(actual[(lvl, g)], rs) for lvl, groups in rebuilt.items() for g, (rs, _n) in groups.items() if (lvl, g) in actual and rs is not None]
    a, b = np.array(pairs, dtype=float).T if pairs else (np.array([]), np.array([]))
    corr = float(pd.Series(a).rank().corr(pd.Series(b).rank())) if len(a) > 2 else None   # Spearman: Pearson on ranks
    return {"date": str(d), "groups": len(pairs), "spearman": round(corr, 3) if corr is not None else None,
            "mean_abs_diff": round(float(np.abs(a - b).mean()), 1) if len(a) else None}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=["us", "india"])
    ap.add_argument("--check", action="store_true", help="compare the rebuilt rating with the Sectors page's on its latest day")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.check:
        print(check(a.market))


if __name__ == "__main__":
    main()
