"""Analyst earnings estimates and their trend, and the earnings surprise history — Yahoo's consensus.

What analysts expect a company to report, and which way that expectation has been moving, is the
best free read on how a result may turn out: estimates raised into a report tend to precede a beat,
cuts a miss, and a company that has beaten for several quarters tends to keep doing it.

Stored in Postgres, for the chart's earnings badges and the Fundamentals page:

  earnings_estimates         one dated snapshot per symbol and period (this quarter, next quarter, this
                             fiscal year, next): EPS and revenue consensus with its range and analyst
                             count, the year-ago figure, EPS consensus now and 7 / 30 / 60 / 90 days ago,
                             and the number of upward and downward revisions over 7 and 30 days. Yahoo
                             itself looks back only 90 days; the weekly snapshots kept here build the
                             longer record (`summary`'s "since").
  earnings_surprises         reported EPS against the consensus, per quarter. Yahoo returns the last four;
                             rows are kept, so the record grows past that.
  earnings_estimates_status  when each symbol was last fetched, and what came back.

Source: Yahoo Finance's earnings-trend and earnings-history data, through yfinance. Coverage is broad
for US stocks and thin for India (often two to seven analysts a quarter); Yahoo sometimes reports a 0
for an old trend point (stored as missing) or a "current" trend figure that disagrees with its own
average (both kept as given; the trend uses the trend columns only, so it compares like with like).
Company guidance is not here: no free source carries it as numbers.

    PYTHONPATH=. python3 -m swing_screener.marketdata.estimates --market us --symbols CRM,NVDA
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import time

from ..config import MARKETS
from . import db

logger = logging.getLogger("estimates")

MAX_AGE_DAYS = 6       # a symbol fetched more recently than this is skipped unless forced (the job is weekly)
YF_PAUSE = 0.3         # seconds between symbols — a polite rate
TREND_FLAT = 0.01      # an EPS consensus move smaller than this (1%) reads as unchanged
SINCE_MIN_DAYS = 100   # "since" (from the stored snapshots) only when it reaches further back than Yahoo's 90 days
REPORT_QUARTER_DAYS = 120   # a report covers the quarter that ended at most this many days before it

PERIODS = ("0q", "+1q", "0y", "+1y")
PERIOD_NAME = {"0q": "This quarter", "+1q": "Next quarter", "0y": "This year", "+1y": "Next year"}
_NUM = ("eps_avg", "eps_low", "eps_high", "eps_year_ago", "eps_growth", "rev_avg", "rev_low", "rev_high", "rev_year_ago",
        "rev_growth", "trend_now", "trend_7d", "trend_30d", "trend_60d", "trend_90d")
_INT = ("eps_analysts", "rev_analysts", "up_7d", "up_30d", "down_7d", "down_30d")

SCHEMA = """
CREATE TABLE IF NOT EXISTS earnings_estimates (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    asof DATE NOT NULL,                     -- the day the snapshot was taken
    period VARCHAR(4) NOT NULL,             -- 0q this quarter | +1q next quarter | 0y this fiscal year | +1y next
    end_date DATE,                          -- the period's end
    eps_avg DOUBLE PRECISION, eps_low DOUBLE PRECISION, eps_high DOUBLE PRECISION,
    eps_year_ago DOUBLE PRECISION, eps_growth DOUBLE PRECISION, eps_analysts INT,
    rev_avg DOUBLE PRECISION, rev_low DOUBLE PRECISION, rev_high DOUBLE PRECISION,
    rev_year_ago DOUBLE PRECISION, rev_growth DOUBLE PRECISION, rev_analysts INT,
    trend_now DOUBLE PRECISION, trend_7d DOUBLE PRECISION, trend_30d DOUBLE PRECISION,
    trend_60d DOUBLE PRECISION, trend_90d DOUBLE PRECISION,   -- EPS consensus now and N days ago
    up_7d INT, up_30d INT, down_7d INT, down_30d INT,           -- analysts revising up / down
    currency VARCHAR(8),
    PRIMARY KEY (market, symbol, asof, period)
);
CREATE TABLE IF NOT EXISTS earnings_surprises (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    quarter DATE NOT NULL,                  -- the quarter's end
    eps_actual DOUBLE PRECISION,
    eps_estimate DOUBLE PRECISION,
    surprise DOUBLE PRECISION,              -- (actual - estimate) / |estimate|, as Yahoo gives it
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, quarter)
);
CREATE TABLE IF NOT EXISTS earnings_estimates_status (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    note TEXT,                              -- what came back, or why it failed
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _raw(v):
    """Yahoo's {"raw": x, "fmt": ...} -> x; a 0 or an empty dict -> None (Yahoo's 'no figure')."""
    if isinstance(v, dict):
        v = v.get("raw")
    if v is None or isinstance(v, (dict, str)):
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    return None if v != v else v


def _nz(v):
    v = _raw(v)
    return None if v == 0 else v


# ------------------------------------------------------------------ fetch

def fetch(symbol: str) -> tuple[list[dict], list[dict]]:
    """(estimate rows, surprise rows) for one symbol from Yahoo; empty lists when it has none."""
    import yfinance as yf
    t = yf.Ticker(symbol)
    rows = []
    try:
        t.eps_trend   # loads Yahoo's earningsTrend module; the raw list keeps each period's end date
        trend = getattr(getattr(t, "_analysis", None), "_earnings_trend", None) or []
    except Exception:  # noqa: BLE001 — Yahoo answers 404 for some listings
        trend = []
    for e in trend:
        if e.get("period") not in PERIODS:
            continue
        ee, re_, et, er = (e.get(k) or {} for k in ("earningsEstimate", "revenueEstimate", "epsTrend", "epsRevisions"))
        try:
            end = dt.date.fromisoformat(str(e.get("endDate"))[:10])
        except ValueError:
            end = None
        rows.append({
            "period": e["period"], "end_date": end,
            "eps_avg": _raw(ee.get("avg")), "eps_low": _raw(ee.get("low")), "eps_high": _raw(ee.get("high")),
            "eps_year_ago": _raw(ee.get("yearAgoEps")), "eps_growth": _raw(ee.get("growth")),
            "eps_analysts": _raw(ee.get("numberOfAnalysts")),
            "rev_avg": _nz(re_.get("avg")), "rev_low": _nz(re_.get("low")), "rev_high": _nz(re_.get("high")),
            "rev_year_ago": _nz(re_.get("yearAgoRevenue")), "rev_growth": _raw(re_.get("growth")),
            "rev_analysts": _raw(re_.get("numberOfAnalysts")),
            "trend_now": _nz(et.get("current")), "trend_7d": _nz(et.get("7daysAgo")), "trend_30d": _nz(et.get("30daysAgo")),
            "trend_60d": _nz(et.get("60daysAgo")), "trend_90d": _nz(et.get("90daysAgo")),
            "up_7d": _raw(er.get("upLast7days")), "up_30d": _raw(er.get("upLast30days")),
            "down_7d": _raw(er.get("downLast7Days")), "down_30d": _raw(er.get("downLast30days")),
            "currency": ee.get("earningsCurrency") or re_.get("revenueCurrency"),
        })
    rows = [r for r in rows if r["eps_avg"] is not None or r["rev_avg"] is not None]
    surprises = []
    try:
        h = t.earnings_history
    except Exception:  # noqa: BLE001
        h = None
    if h is not None and not getattr(h, "empty", True):
        for q, r in h.iterrows():
            a, e = _raw(r.get("epsActual")), _raw(r.get("epsEstimate"))
            if a is None or e is None:
                continue
            surprises.append({"quarter": dt.date.fromisoformat(str(q)[:10]), "eps_actual": a, "eps_estimate": e,
                              "surprise": _raw(r.get("surprisePercent"))})
    return rows, surprises


def _store(market: str, symbol: str, rows: list[dict], surprises: list[dict], note: str) -> None:
    today = dt.date.today()
    cols = ["period", "end_date", *_NUM, *_INT, "currency"]
    with db.get_connection().cursor() as cur:
        for r in rows:
            vals = [int(r[c]) if c in _INT and r[c] is not None else r[c] for c in cols]
            cur.execute(f"""INSERT INTO earnings_estimates (market, symbol, asof, {", ".join(cols)})
                            VALUES (%s,%s,%s,{", ".join(["%s"] * len(cols))})
                            ON CONFLICT (market, symbol, asof, period) DO UPDATE SET
                              {", ".join(f"{c}=EXCLUDED.{c}" for c in cols[1:])}""",
                        (market, symbol, today, *vals))
        for s in surprises:
            cur.execute("""INSERT INTO earnings_surprises (market, symbol, quarter, eps_actual, eps_estimate, surprise)
                           VALUES (%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (market, symbol, quarter) DO UPDATE SET eps_actual=EXCLUDED.eps_actual,
                             eps_estimate=EXCLUDED.eps_estimate, surprise=EXCLUDED.surprise, fetched_at=now()""",
                        (market, symbol, s["quarter"], s["eps_actual"], s["eps_estimate"], s["surprise"]))
        cur.execute("""INSERT INTO earnings_estimates_status (market, symbol, fetched_at, note) VALUES (%s,%s,now(),%s)
                       ON CONFLICT (market, symbol) DO UPDATE SET fetched_at=now(), note=EXCLUDED.note""",
                    (market, symbol, note))


def fetch_symbol(market: str, symbol: str) -> dict:
    """Fetch and store one symbol; a failure is recorded in the status table, never raised."""
    try:
        rows, surprises = fetch(symbol)
        note = f"{len(rows)} periods · {len(surprises)} surprises"
    except Exception as exc:  # noqa: BLE001 — one bad symbol must not stop the batch
        rows, surprises, note = [], [], f"failed ({type(exc).__name__}: {exc})"[:300]
        logger.warning("%s %s: %s", market, symbol, exc)
    _store(market, symbol, rows, surprises, note)
    return {"periods": len(rows), "surprises": len(surprises), "note": note}


def refresh(market: str, symbols: list[str], force: bool = False, progress=None) -> dict:
    """Fetch `symbols`, skipping any fetched within MAX_AGE_DAYS unless forced."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM earnings_estimates_status WHERE market=%s AND fetched_at > now() - %s * interval '1 day'"
                    " AND note NOT LIKE 'failed%%'",
                    (market, MAX_AGE_DAYS))
        fresh = {r[0] for r in cur.fetchall()}
    todo = [s for s in symbols if force or s not in fresh]
    stats = {"requested": len(symbols), "skipped_fresh": len(symbols) - len(todo), "with_estimates": 0, "none": 0, "failed": 0}
    for i, sym in enumerate(todo):
        if progress:
            progress(f"estimates: {i + 1:,}/{len(todo):,} symbols · {stats['with_estimates']:,} with estimates")
        r = fetch_symbol(market, sym)
        stats["failed" if r["note"].startswith("failed") else "with_estimates" if r["periods"] else "none"] += 1
        time.sleep(YF_PAUSE)
    return stats


# ------------------------------------------------------------------ read (the page and the chart)

def _change(now, base):
    return None if now is None or base is None or base == 0 else (now - base) / abs(base)


def _dir(chg):
    return None if chg is None else "up" if chg > TREND_FLAT else "down" if chg < -TREND_FLAT else "flat"


def summary(market: str, symbol: str) -> dict | None:
    """The latest snapshot per period with its trend read, the stored surprise history, and one-line
    reads of both — None when nothing is stored. Every judgement is made here; the page only formats."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('earnings_estimates')")
        if cur.fetchone()[0] is None:
            return None
        cols = ["asof", "period", "end_date", *_NUM, *_INT, "currency"]
        cur.execute(f"""SELECT {", ".join(cols)} FROM earnings_estimates WHERE market=%s AND symbol=%s
                        AND asof = (SELECT max(asof) FROM earnings_estimates WHERE market=%s AND symbol=%s)""",
                    (market, symbol, market, symbol))
        latest = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("""SELECT quarter, eps_actual, eps_estimate, surprise FROM earnings_surprises
                       WHERE market=%s AND symbol=%s ORDER BY quarter DESC""", (market, symbol))
        surprises = [{"quarter": str(q), "actual": a, "estimate": e,
                      "surprise": s if s is not None else _change(a, e),
                      "beat": a > e if a is not None and e is not None else None} for q, a, e, s in cur.fetchall()]
        # the oldest stored snapshot of the same period end, when it reaches past Yahoo's own 90 days
        since = {}
        for r in latest:
            if r["end_date"] is None:
                continue
            cur.execute("""SELECT asof, eps_avg FROM earnings_estimates WHERE market=%s AND symbol=%s AND period=%s
                           AND end_date=%s AND eps_avg IS NOT NULL ORDER BY asof LIMIT 1""",
                        (market, symbol, r["period"], r["end_date"]))
            got = cur.fetchone()
            if got and (r["asof"] - got[0]).days >= SINCE_MIN_DAYS:
                since[r["period"]] = {"asof": str(got[0]), "eps": got[1], "change": _change(r["eps_avg"], got[1])}
        cur.execute("SELECT fetched_at, note FROM earnings_estimates_status WHERE market=%s AND symbol=%s", (market, symbol))
        st = cur.fetchone()
    if not latest and not surprises and not st:
        return None
    order = {p: i for i, p in enumerate(PERIODS)}
    periods = []
    for r in sorted(latest, key=lambda r: order.get(r["period"], 9)):
        chg30, chg90 = _change(r["trend_now"], r["trend_30d"]), _change(r["trend_now"], r["trend_90d"])
        up, down = r["up_30d"], r["down_30d"]
        periods.append({
            **{k: (str(v) if isinstance(v, dt.date) else v) for k, v in r.items()},
            "name": PERIOD_NAME.get(r["period"], r["period"]), "quarter": r["period"].endswith("q"),
            "chg_30d": chg30, "chg_90d": chg90, "dir_30d": _dir(chg30), "dir_90d": _dir(chg90),
            "net_30d": (up or 0) - (down or 0) if up is not None or down is not None else None,
            "since": since.get(r["period"]),
        })
    beats = [s for s in surprises if s["beat"] is not None]
    recent = beats[:4]
    read = []
    q0 = next((p for p in periods if p["period"] == "0q"), None)
    if q0:
        bits = []
        if q0["chg_90d"] is not None:
            word = {"up": "raised", "down": "cut", "flat": "unchanged"}[q0["dir_90d"]]
            bits.append(f"this quarter's EPS consensus {word}" + ("" if q0["dir_90d"] == "flat" else f" {abs(q0['chg_90d']) * 100:.1f}%")
                        + " over 90 days")
        if q0["up_30d"] is not None or q0["down_30d"] is not None:
            bits.append(f"{q0['up_30d'] or 0} analysts revised up and {q0['down_30d'] or 0} down in 30 days")
        if bits:
            read.append("; ".join(bits)[0].upper() + "; ".join(bits)[1:] + ".")
    if recent:
        read.append(f"Beat the consensus in {sum(s['beat'] for s in recent)} of the last {len(recent)} quarters"
                    f" (average surprise {sum(s['surprise'] or 0 for s in recent) / len(recent) * 100:+.0f}%).")
    return {"asof": str(latest[0]["asof"]) if latest else None, "currency": latest[0]["currency"] if latest else None,
            "periods": periods, "surprises": surprises, "read": read,
            "beats": {"beat": sum(s["beat"] for s in recent), "of": len(recent)} if recent else None,
            "fetched_at": st[0].isoformat() if st else None, "note": st[1] if st else None,
            "source": "Yahoo Finance analyst consensus", "flat": TREND_FLAT}


def surprises_by_report(surprises: list[dict], report_dates: list[str]) -> dict[str, dict]:
    """{report date: surprise} — each quarter's surprise goes to the first report after the quarter ended
    (within REPORT_QUARTER_DAYS), so a later or stale report date never re-uses it."""
    days = sorted({dt.date.fromisoformat(d) for d in report_dates})
    out = {}
    for s in surprises:
        q = dt.date.fromisoformat(s["quarter"])
        first = next((d for d in days if q < d and (d - q).days <= REPORT_QUARTER_DAYS), None)
        if first is not None and str(first) not in out:
            out[str(first)] = s
    return out


def period_for_report(periods: list[dict], report_date: str) -> dict | None:
    """The quarterly estimate an upcoming report on `report_date` will be judged against: the quarter
    that ended in the REPORT_QUARTER_DAYS before it (or, before it has ended, the nearest one)."""
    d = dt.date.fromisoformat(report_date)
    qs = [p for p in periods if p["quarter"] and p.get("end_date")]
    done = [p for p in qs if 0 < (d - dt.date.fromisoformat(p["end_date"])).days <= REPORT_QUARTER_DAYS]
    if done:
        return max(done, key=lambda p: p["end_date"])
    return min(qs, key=lambda p: abs((d - dt.date.fromisoformat(p["end_date"])).days), default=None)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--symbols", required=True, help="comma-separated")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(refresh(a.market, [s.strip() for s in a.symbols.split(",") if s.strip()], force=a.force))


if __name__ == "__main__":
    main()
