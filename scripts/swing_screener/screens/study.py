"""Screen study: did stocks that passed a screen go on to beat the other tradable stocks?

Screens have no entries or exits, so they are not backtested; they are judged by forward returns. Any
screen — built-in, yours, or conditions not yet saved — is studied on demand over the month-end
snapshots (screens/snapshot.py keeps every month's last session; `--backfill` builds the history):
on each month-end the conditions are applied to that day's snapshot (point in time), and the
qualifiers' returns to the month-end 1, 3 and 6 months later are compared with the average tradable
stock's over the same window.

Reported per horizon: average return of qualifiers vs all tradable stocks (excess), the hit rate (share
of qualifiers beating the median tradable stock), the share of dates the qualifiers won, and the
typical number of qualifiers; plus each date, for the chart.

History snapshots have no present-only fields. Sector, industry and sub-industry are filled from the
latest snapshot (a company rarely changes industry, so the look-ahead is small). Group strength — group
RS and the peer-group fields — is rebuilt for each month-end from prices up to that day
(analytics/group_history.py), so screens on it can be studied. Market cap, quality and days to earnings
describe only the present and cannot be studied.

Caveats: survivorship — stocks delisted since are missing, which flatters every group alike but most the
weakest; returns are close-to-close with no costs; overlapping 3/6-month windows are not independent.

    PYTHONPATH=. python3 -m swing_screener.screens.study --market india            # every built-in screen
"""

import argparse
import json
import logging
import time

import numpy as np
import pandas as pd

from ..config import MARKETS
from . import definitions, snapshot

logger = logging.getLogger(__name__)
HORIZONS = {"1M": 1, "3M": 3, "6M": 6}            # months ahead (month-end to month-end)
MIN_DATES = 12                                    # month-ends with a 1-month outcome needed before a study is shown
CLASSIFICATION = ("sector", "industry", "sub_industry")
GROUP_FIELDS = ("group_rs", "peer_group", "peer_rs", "peer_rank", "peer_count")    # rebuilt point in time
UNSTUDIABLE = tuple(k for k in snapshot.PRESENT_ONLY if k not in CLASSIFICATION and k not in GROUP_FIELDS)

_hist: dict = {}
_cache: dict = {}


def month_end_dates(market: str) -> list:
    """The snapshots that close a month (the current month's latest session is not one yet)."""
    ds = snapshot.dates(market)
    by = {}
    for x in ds:
        by[(x.year, x.month)] = x
    today = ds[-1] if ds else None
    return sorted(v for k, v in by.items() if today is None or k != (today.year, today.month))


def history(market: str) -> dict:
    """{month-end: snapshot DataFrame}, classification filled from the latest snapshot. Cached until the files change."""
    ds = month_end_dates(market)
    latest = snapshot.dates(market)[-1] if ds else None
    key = (market, tuple(ds), latest, tuple(snapshot._path(market, d).stat().st_mtime for d in ds[-1:]))
    if _hist.get(market, (None,))[0] != key:
        cls = snapshot.load(market, latest).set_index("symbol")[list(CLASSIFICATION)] if latest else None
        from ..analytics import group_history
        ratings = group_history.ensure(market, ds)      # group RS as it stood on each month-end
        snaps = {}
        for d in ds:
            df = snapshot.load(market, d)
            if cls is not None:
                for k in CLASSIFICATION:
                    df[k] = df["symbol"].map(cls[k])
                r = ratings.get(d, {})
                df["group_rs"] = df["industry"].map(r.get("industry", {}))
                snapshot.add_peers(df, r.get("industry", {}), r.get("sub", {}))
            snaps[d] = df
        _hist[market] = (key, snaps)
        _cache.clear()
    return _hist[market][1]


def study(market: str, conditions: list) -> dict:
    """Forward returns of the stocks passing `conditions` on each month-end vs all tradable stocks."""
    bad = sorted({c.get("field") for c in conditions} & set(UNSTUDIABLE))
    if bad:
        labels = {k: l for k, l, *_ in snapshot.FIELDS}
        return {"error": f"{', '.join(labels.get(b, b) for b in bad)} describe only the present, so a screen using them "
                         f"cannot be studied over past dates."}
    snaps = history(market)
    ck = (market, json.dumps(conditions, sort_keys=True))
    if ck in _cache:
        return _cache[ck]
    ds = sorted(snaps)
    close = {d: snaps[d].set_index("symbol")["close"] for d in ds}
    per_date, rows = [], {h: [] for h in HORIZONS}
    for i, d in enumerate(ds):
        df = snaps[d]
        q = definitions.mask(df, conditions)
        trad = df["tradable"].astype(bool)
        entry = {"date": d.isoformat(), "qualifiers": int(q.sum()), "tradable": int(trad.sum())}
        for h, k in HORIZONS.items():
            if i + k >= len(ds) or (ds[i + k].year * 12 + ds[i + k].month) - (d.year * 12 + d.month) != k:
                continue                                  # no snapshot exactly k months later (a gap in the history)
            fwd = (close[ds[i + k]].reindex(df["symbol"]).to_numpy() / df["close"].to_numpy() - 1) * 100
            fwd = pd.Series(fwd, index=df.index)
            uni = fwd[trad].dropna()
            if uni.empty:
                continue
            qs = fwd[q].dropna()
            entry[h] = {"q": float(qs.mean()) if len(qs) else None, "u": float(uni.mean())}
            if len(qs):
                rows[h].append((d, float(qs.mean()), float(uni.mean()), int((qs > uni.median()).sum()), len(qs)))
        per_date.append(entry)
    summary = []
    for h, xs in rows.items():
        if not xs:
            continue
        qm = np.array([x[1] for x in xs])
        um = np.array([x[2] for x in xs])
        summary.append({"horizon": h, "dates": len(xs), "mean": float(qm.mean()), "universe": float(um.mean()),
                        "excess": float((qm - um).mean()), "hit_rate": sum(x[3] for x in xs) / sum(x[4] for x in xs),
                        "pct_dates_beating": float((qm > um).mean()), "avg_qualifiers": float(np.mean([x[4] for x in xs])),
                        "first": xs[0][0].isoformat(), "last": xs[-1][0].isoformat()})
    n1 = next((s["dates"] for s in summary if s["horizon"] == "1M"), 0)
    out = {"market": market, "month_ends": len(ds), "summary": summary, "series": per_date}
    if n1 < MIN_DATES:
        out = {"empty": True, "month_ends": len(ds), "summary": summary, "series": per_date,
               "command": f"PYTHONPATH=. python3 -m swing_screener.screens.snapshot --market {market} --backfill 5"}
    _cache[ck] = out
    return out


def compare(market: str, horizon: str = "6M") -> list[dict]:
    """The built-in screens' excess at one horizon, for the 'against the other screens' bars."""
    out = []
    for key, d in definitions.builtin().items():
        s = study(market, d["conditions"])
        for x in s.get("summary", []):
            if x["horizon"] == horizon:
                out.append({"screen": key, "name": d["name"], "excess": x["excess"]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    t0 = time.time()
    for key, d in definitions.builtin().items():
        s = study(a.market, d["conditions"])
        print(key, {x["horizon"]: f"{x['excess']:+.2f}% hit {x['hit_rate']:.0%} ({x['dates']} dates, ~{x['avg_qualifiers']:.0f})"
                    for x in s.get("summary", [])} or s)
    print(f"{time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
