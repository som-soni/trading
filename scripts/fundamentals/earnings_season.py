"""The earnings-season scoreboard: how the season's results add up, per market and quarter — the Earnings page.

Reads only what `marketdata/financials.py` stores (`quarterly_results`) and the market caps of
`marketdata/industries.py` (`symbol_industry`); nothing is downloaded here.

  quarter    a calendar quarter. A US fiscal quarter ends on its own date (a 52/53-week year ends on
             27 Sep, a retailer's on 31 Jul), so each stored quarter counts in the calendar quarter whose
             end is NEAREST its period end (a tie goes to the earlier one).
  reported   companies with a stored row for the quarter, against those with one for the quarter before —
             "116 / 592" is how far the season has got among the companies the app tracks.
  basis      yoy: against the same quarter a year earlier — the comparative printed in the same filing
             (`*_prior`, point in time and on one basis) where the source gives one (SEC), else the stored
             row four quarters back (NSE files no comparative). qoq: against the stored row one quarter back.
  aggregate  per metric, only companies with both the current figure and its base: sum / sum − 1. A few
             giants dominate a sum, so the MEDIAN company's change is reported beside it, and how many grew.
             A company's own change is undefined when its base is zero or a loss (shown in words instead).
             A metric a company does not file (banks have no gross profit; NSE results carry none at all)
             is missing, never zero — it simply drops out of that metric's count.
  trend      the same aggregates for every listed quarter, oldest first, for the page's trend chart. The companies
             are TODAY's tracked set, so older quarters leave out companies since dropped or delisted (survivorship).
  buckets    all, then large / mid / small caps by TODAY's market cap (`MarketConfig.cap_classes`). Index
             membership (Nifty 50, S&P 500) is not stored, so there is no index bucket. A company with no
             stored market cap counts in "all" only.

Companies whose statements are in another currency than the market's (Yahoo-sourced ADRs: TSMC in TWD)
are left out — their amounts cannot be summed with the others.

The universe is the companies whose financials the app fetches (screened and watchlisted stocks), not
every listed company: the response says how many, and the page says so.
"""

from __future__ import annotations

import datetime as dt
import statistics
import time

from swing_screener.config import MARKETS
from swing_screener.marketdata import db, financials, names as names_mod

METRICS = (("revenue", "Revenue"), ("gross_profit", "Gross profit"), ("net_income", "Net profit"))
QUARTERS_LISTED = 20      # quarters offered in the picker and drawn in the trend chart (five years), newest first
SEASON_DONE = 0.9         # a quarter is "in progress" until this share of the previous quarter's reporters have reported ...
RESULTS_WINDOW_DAYS = 100 # ... and only while results can still be due (NSE: 45 days, 60 for Q4; SEC 10-Q 40-45, 10-K 60-90)
THIN_BASE = 0.5           # trend: a quarter where fewer than this share of reporters have a comparable base is a gap, not a point
                          # (the oldest stored quarters have no year-ago row: their few survivors are not the season)
CACHE_SECONDS = 600       # the stored quarters are re-read this often (the financials job adds a few a day)
MIN_COMPANIES = 5         # fewer companies than this with a metric: no aggregate (two filers of gross profit are not "India Inc")

_cache: dict[str, tuple[float, dict]] = {}


def quarter_of(d: dt.date) -> dt.date:
    """The calendar quarter end nearest `d` (ties to the earlier)."""
    ends = []
    for y in (d.year - 1, d.year, d.year + 1):
        ends += [dt.date(y, 3, 31), dt.date(y, 6, 30), dt.date(y, 9, 30), dt.date(y, 12, 31)]
    return min(ends, key=lambda e: (abs((e - d).days), e))


def shift(q: dt.date, n: int) -> dt.date:
    """The quarter end `n` quarters after `q` (negative: before)."""
    i = q.year * 4 + (q.month - 1) // 3 + n
    y, k = divmod(i, 4)
    return dt.date(y, 3 * k + 3, (31, 30, 30, 31)[k])


def _cap_classes(market: str) -> tuple[dict[str, str], dict[str, float]]:
    """symbol -> "large" | "mid" | "small" by today's market cap, and symbol -> market cap."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, market_cap FROM symbol_industry WHERE market=%s AND market_cap > 0 ORDER BY market_cap DESC", (market,))
        caps = cur.fetchall()
    rule = MARKETS[market].cap_classes
    out: dict[str, str] = {}
    if rule:
        kind, large, mid = rule
        for rank, (sym, cap) in enumerate(caps, 1):
            v = rank if kind == "rank" else -cap
            lo, hi = (large, mid) if kind == "rank" else (-large, -mid)
            out[sym] = "large" if v <= lo else "mid" if v <= hi else "small"
    return out, dict(caps)


def _prepare(market: str) -> dict:
    """symbol -> {quarter: row}, the cap classes and the names, re-read every CACHE_SECONDS."""
    hit = _cache.get(market)
    if hit and time.time() - hit[0] < CACHE_SECONDS:
        return hit[1]
    meta = financials.load_meta(market)
    foreign = {s for s, m in meta.items() if financials.statement_currency(market, m)}
    by_sym: dict[str, dict] = {}
    for sym, rows in financials.load(market).items():
        if sym in foreign:
            continue
        qs: dict = {}
        for r in rows:            # oldest first: a later row in the same calendar quarter replaces an earlier one
            qs[quarter_of(r["period_end"])] = r
        by_sym[sym] = qs
    cls, caps = _cap_classes(market)
    data = {"rows": by_sym, "cls": cls, "caps": caps, "names": names_mod.load(market), "foreign": len(foreign)}
    _cache[market] = (time.time(), data)
    return data


def _change(cur, base):
    """(fractional change, words) — the change is None where it means nothing (a zero or loss base)."""
    if cur is None or base is None:
        return None, None
    if base > 0:
        return cur / base - 1, None
    if base == 0:
        return None, None
    return None, ("loss to profit" if cur > 0 else "loss narrowed" if cur > base else "loss widened")


def _aggregate(pairs: list[tuple[float, float, float | None]]) -> dict:
    """pairs: (current, base, own change) of every company with both figures."""
    if not pairs:
        return {"n": 0, "current": None, "base": None, "change": None, "median": None, "grew": 0, "measured": 0}
    cur, base = sum(p[0] for p in pairs), sum(p[1] for p in pairs)
    own = [p[2] for p in pairs if p[2] is not None]
    return {"n": len(pairs), "current": cur, "base": base,
            # a sum that was a loss (or zero) has no meaningful growth rate
            "change": cur / base - 1 if base > 0 and len(pairs) >= MIN_COMPANIES else None,
            "median": statistics.median(own) if len(own) >= MIN_COMPANIES else None,
            "grew": sum(1 for p in pairs if p[0] > p[1]), "measured": len(own)}


BUCKETS = (("all", "All"), ("large", "Large cap"), ("mid", "Mid cap"), ("small", "Small cap"))


def _quarter(data: dict, market: str, q: dt.date, basis: str) -> tuple[list[dict], list[dict]]:
    """One quarter: (every reporting company with its figures and changes, the buckets' aggregates)."""
    rows, cls = data["rows"], data["cls"]
    prev = shift(q, -1)
    base_q = shift(q, -4) if basis == "yoy" else prev
    companies, pairs = [], {b: {m: [] for m, _ in METRICS} for b, _ in BUCKETS}
    for sym, qs in rows.items():
        r = qs.get(q)
        if not r:
            continue
        b_row = qs.get(base_q) or {}
        rec = {"symbol": sym, "name": names_mod.lookup(data["names"], sym), "cap_class": cls.get(sym),
               "market_cap": data["caps"].get(sym), "period_end": r["period_end"].isoformat(),
               "filed": r["filed"].isoformat() if r.get("filed") else None}
        for m, _ in METRICS:
            cur = r.get(m)
            base = (r.get(f"{m}_prior") if basis == "yoy" else None)
            if base is None:
                base = b_row.get(m)
            chg, words = _change(cur, base)
            rec[m], rec[f"{m}_base"], rec[f"{m}_chg"], rec[f"{m}_note"] = cur, base, chg, words
            if cur is not None and base is not None:
                for b in ("all", cls.get(sym)):
                    if b:
                        pairs[b][m].append((cur, base, chg))
        companies.append(rec)

    def reported(qq, b):
        return sum(1 for s, qs in rows.items() if qq in qs and (b == "all" or cls.get(s) == b))

    buckets = []
    for b, label in BUCKETS:
        if b != "all" and not MARKETS[market].cap_classes:
            continue
        buckets.append({"key": b, "label": label, "reported": reported(q, b), "reported_prev": reported(prev, b),
                        "metrics": {m: _aggregate(pairs[b][m]) for m, _ in METRICS}})
    return companies, buckets


def scoreboard(market: str, quarter: dt.date | None = None, basis: str = "yoy") -> dict:
    data = _prepare(market)
    rows = data["rows"]
    count: dict = {}
    for qs in rows.values():
        for q in qs:
            count[q] = count.get(q, 0) + 1
    # a calendar quarter needs a few reporters to be a quarter at all (a lone odd fiscal year is not)
    listed = sorted((q for q, n in count.items() if n >= 5), reverse=True)[:QUARTERS_LISTED]
    if not listed:
        return {"market": market, "empty": True}
    q = quarter_of(quarter) if quarter else listed[0]
    prev = shift(q, -1)
    base_q = shift(q, -4) if basis == "yoy" else prev
    companies, buckets = _quarter(data, market, q, basis)
    companies.sort(key=lambda c: -(c.get("market_cap") or 0))

    # the trend: every listed quarter's aggregates, oldest first. A quarter whose season is still running
    # (fewer reporters than SEASON_DONE of the quarter before) is flagged, since its figures will move.
    trend = []
    for x in sorted(listed):
        _, bs = _quarter(data, market, x, basis)
        a = bs[0]
        open_ = dt.date.today() <= x + dt.timedelta(days=RESULTS_WINDOW_DAYS)
        trend.append({"quarter": x.isoformat(), "in_progress": open_ and a["reported"] < SEASON_DONE * a["reported_prev"],
                      "buckets": {b["key"]: {"reported": b["reported"], "reported_prev": b["reported_prev"],
                                             "metrics": {m: {k: v[k] for k in ("change", "median", "n", "grew")} for m, v in b["metrics"].items()}}
                                  for b in bs}})
    cfg = MARKETS[market]
    return {
        "market": market, "quarter": q.isoformat(), "basis": basis, "base_quarter": base_q.isoformat(),
        "prev_quarter": prev.isoformat(),
        "quarters": [{"quarter": x.isoformat(), "reported": count[x]} for x in listed],
        "metrics": [{"key": m, "label": t} for m, t in METRICS],
        "buckets": buckets, "companies": companies, "trend": trend,
        "universe": len(rows), "no_cap": sum(1 for c in companies if not c["cap_class"]),
        "foreign_excluded": data["foreign"], "cap_note": cfg.cap_note, "min_companies": MIN_COMPANIES,
        "season_done": SEASON_DONE, "thin_base": THIN_BASE, "money_unit": cfg.money_unit, "money_divisor": cfg.money_divisor,
    }
