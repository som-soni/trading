"""Fundamentals from quarterly results: growth, margins, returns — the same numbers for every strategy.

Reads what `marketdata/financials.py` stores (SEC filings for the US, NSE filings for India, yfinance
as the fallback) and works out, per company, the figures the web app's **Fundamentals** page shows:
year-over-year EPS and sales growth per quarter, net margin against a year earlier, annual EPS
growth, return on equity and the latest earnings surprise. It reads stored data only; the
`financials` job downloads.

Strategy-specific judgements sit on top of these metrics as VIEWS — each a module with `key`,
`criteria()` and `evaluate(metrics)` — so a strategy adds its own reading of the fundamentals without
touching the shared numbers. Today there is one: `fundamentals/sepa.py`, Minervini's SEPA tests.

Growth is year over year (a quarter against the same quarter a year earlier) so seasonality cancels.
Where the filing itself carries the year-ago figure (SEC) that comparative is used, so both numbers are
on one share basis; otherwise (NSE, yfinance) the stored quarter a year earlier is used and its EPS is
put on today's share basis when the share count jumped by a split or bonus-issue ratio.

    PYTHONPATH=. python3 -m fundamentals.growth --market us
    PYTHONPATH=. python3 -m fundamentals.growth --market india --symbols RELIANCE.NS
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging

from swing_screener.config import MARKETS
from swing_screener.marketdata import db, financials

logger = logging.getLogger(__name__)

ANNUAL_YEARS = 3              # annual EPS growth is measured over this many fiscal years
STALE_RESULTS_DAYS = 200      # latest results older than this are flagged stale (the company stopped filing?)
GROWTH_READINGS = 8           # quarterly growth readings kept per company
SERIES_QUARTERS = 12          # quarters kept for the page's charts
SURPRISE_MATCH_DAYS = 45      # an earnings-history row belongs to the latest quarter when this close to its end

# share-count jumps read as a split or bonus issue (new shares / old): n-for-1 splits, a:b bonuses
# ((a+b)/b) and reverse splits; small ratios (1:5 bonus = 1.2) are left out — an issue of shares can do that
SHARE_MULTIPLES = sorted({*(float(n) for n in (2, 3, 4, 5, 6, 8, 10, 20)), 1.25, 4 / 3, 1.5, 5 / 3, 2.5,
                          *(1 / n for n in (2, 3, 4, 5, 8, 10, 20))})
SHARE_MULTIPLE_TOL = 0.015     # small ratios: share issues and buybacks move the count a little too ...
SHARE_MULTIPLE_TOL_BIG = 0.05  # ... a 2x-or-more jump is unmistakable even with a few % of drift


def _fmt(text: str) -> str:
    return text.format(**{k: v for k, v in globals().items() if k.isupper()})


DOC = {
    "key": "fundamentals",
    "name": "Fundamentals",
    "description": "Quarterly earnings, sales and margin growth from the companies' own filings — for every strategy.",
    "how_it_works": (
        "An offline job stores up to five years of quarterly results: SEC filings (10-Q / 10-K) for the US, NSE results "
        "filings for India, with yfinance as the fallback for anything those have nothing for.",
        "Each quarter is compared with the same quarter a year earlier, so seasonality cancels.",
        _fmt("Annual EPS growth is a yearly rate over the last {ANNUAL_YEARS} fiscal years (the Q4 filing's full-year EPS), "
             "or over trailing-twelve-month EPS where fiscal years are missing."),
        "Return on equity is trailing-twelve-month net income over average equity from the filings, else the Quality page's "
        "annual average. The earnings surprise is the latest quarter's EPS against Yahoo's consensus estimate.",
        "The technical side (Trend Template, RS rank) comes from the day's stock snapshot.",
        "Strategy sections (Minervini SEPA) judge these same numbers by their own rules.",
    ),
    "caveats": (
        "US Q4 is not filed on its own: it is the full year minus the first nine months, so its EPS is approximate.",
        "Growth from a loss (or a zero) is not measurable and is left blank.",
        "India: consolidated results where the company files them for most quarters, else standalone. Indian filings "
        "carry no year-ago figures, so EPS is put on today's share basis from the share count when it jumps by a split "
        "or bonus ratio; a large share issue at such a ratio would be misread.",
        "One-off gains and charges are not removed. Check the filing behind a big number.",
        "Estimates are Yahoo's consensus, and its 'actual' EPS can be an adjusted figure rather than the filed one.",
        "Not investment advice: a screening aid over filings that can be restated.",
    ),
}


# ---------------------------------------------------------------- the maths (pure functions, tested)

def _g(cur, prior) -> float | None:
    """Growth, or None when the base is not positive (growth from a loss is not measurable)."""
    if cur is None or prior is None or prior <= 0:
        return None
    return cur / prior - 1


def split_factors(rows: list[dict]) -> list[float]:
    """Per row (oldest first), the split/bonus multiple between it and the newest row: EPS on today's
    share basis = eps / factor. Only share-count jumps at a split or bonus ratio count."""
    f = [1.0] * len(rows)
    for i in range(len(rows) - 2, -1, -1):
        a, b = rows[i].get("shares"), rows[i + 1].get("shares")
        m = 1.0
        if a and b and a > 0 and b > 0:
            r = b / a
            hit = next((x for x in SHARE_MULTIPLES
                        if abs(r / x - 1) <= (SHARE_MULTIPLE_TOL_BIG if max(x, 1 / x) >= 2 else SHARE_MULTIPLE_TOL)), None)
            m = hit or 1.0
        f[i] = f[i + 1] * m
    return f


def _year_before(rows: list[dict], i: int) -> int | None:
    end = rows[i]["period_end"]
    for j in range(i - 1, -1, -1):
        if financials.YEAR_APART[0] <= (end - rows[j]["period_end"]).days <= financials.YEAR_APART[1]:
            return j
    return None


def growth_series(rows: list[dict]) -> list[dict]:
    """Per quarter (oldest first): EPS growth, sales growth, net margin and its year-ago value."""
    fac = split_factors(rows)
    out = []
    for i, r in enumerate(rows):
        j = _year_before(rows, i)
        p = rows[j] if j is not None else {}
        eps_prior = r.get("eps_prior")
        if eps_prior is None and p.get("eps") is not None:
            eps_prior = p["eps"] / fac[j] * fac[i]       # the year-ago EPS on this quarter's share basis
        rev_prior = r.get("revenue_prior") if r.get("revenue_prior") is not None else p.get("revenue")
        ni_prior = r.get("net_income_prior") if r.get("net_income_prior") is not None else p.get("net_income")
        rev, ni = r.get("revenue"), r.get("net_income")
        out.append({
            "end": r["period_end"], "fiscal": r.get("fiscal"), "derived": bool(r.get("derived")),
            "eps": r.get("eps"), "eps_prior": eps_prior, "eps_g": _g(r.get("eps"), eps_prior),
            "rev": rev, "rev_prior": rev_prior, "rev_g": _g(rev, rev_prior),
            "margin": ni / rev if ni is not None and rev and rev > 0 else None,
            "margin_prior": ni_prior / rev_prior if ni_prior is not None and rev_prior and rev_prior > 0 else None,
            "eps_adj": r["eps"] / fac[i] if r.get("eps") is not None else None,
        })
    return out


def ttm(series: list[dict], back: int) -> float | None:
    """Trailing-twelve-month EPS (today's share basis) ending `back` quarters before the latest."""
    n = len(series)
    idx = list(range(n - 1 - back, n - 5 - back, -1))
    if idx[-1] < 0:
        return None
    q = [series[k] for k in idx]
    if any(x["eps_adj"] is None for x in q):
        return None
    if any(not 60 <= (q[k]["end"] - q[k + 1]["end"]).days <= 120 for k in range(3)):
        return None    # a gap: not four consecutive quarters
    return sum(x["eps_adj"] for x in q)


def annual_eps(rows: list[dict], series: list[dict]) -> tuple[list | None, str | None]:
    """EPS for the last ANNUAL_YEARS + 1 years, newest first, on today's share basis: fiscal years (the
    Q4 filing's full-year EPS), else trailing twelve months. (None, None) when neither is complete."""
    fac = split_factors(rows)
    fy = [(r["period_end"], r["eps_fy"] / fac[i]) for i, r in enumerate(rows) if r.get("eps_fy") is not None]
    if fy:
        chain = [fy[-1]]
        for d, v in reversed(fy[:-1]):
            if len(chain) <= ANNUAL_YEARS and financials.YEAR_APART[0] <= (chain[-1][0] - d).days <= financials.YEAR_APART[1]:
                chain.append((d, v))
        if len(chain) == ANNUAL_YEARS + 1:
            return [v for _, v in chain], "fiscal years"
    t = [ttm(series, 4 * k) for k in range(ANNUAL_YEARS + 1)]
    return (t, "trailing twelve months") if all(x is not None for x in t) else (None, None)


def roe(rows: list[dict], fallback: float | None = None) -> tuple[float | None, str | None]:
    """TTM net income over average equity (the latest filed and the one about a year before it)."""
    ni4 = [r.get("net_income") for r in rows[-4:]]
    if len(rows) >= 4 and all(x is not None for x in ni4) and 270 <= (rows[-1]["period_end"] - rows[-4]["period_end"]).days <= 290:
        eq = [(r["period_end"], r["equity"]) for r in rows if r.get("equity")]
        if eq and (rows[-1]["period_end"] - eq[-1][0]).days <= 200:
            year_ago = next((e for d, e in reversed(eq) if 300 <= (eq[-1][0] - d).days <= 430), None)
            avg = (eq[-1][1] + year_ago) / 2 if year_ago else eq[-1][1]
            if avg > 0:
                return sum(ni4) / avg, "filings"
    if fallback is not None:
        return fallback, "annual average (Quality page)"
    return None, None


def metrics(rows: list[dict], meta: dict | None = None, today: dt.date | None = None, roe_fallback: float | None = None) -> dict:
    """One company's quarters (oldest first) -> the shared fundamentals. Lists are newest first."""
    meta, today = meta or {}, today or dt.date.today()
    if not rows:
        return {"quarters": 0}
    s = growth_series(rows)
    new = list(reversed(s))
    latest = new[0]
    years, basis = annual_eps(rows, s)
    cagr = None
    if years and all(x > 0 for x in years):
        cagr = (years[0] / years[-1]) ** (1 / ANNUAL_YEARS) - 1
    r, r_src = roe(rows, roe_fallback)
    sur = [x for x in meta.get("surprises") or [] if x.get("quarter")]
    last = max(sur, key=lambda x: x["quarter"]) if sur else None
    return {
        "quarters": len(rows), "latest_end": latest["end"], "latest_fiscal": latest["fiscal"],
        "latest_filed": rows[-1].get("filed"), "stale": (today - latest["end"]).days > STALE_RESULTS_DAYS,
        "eps_g": [x["eps_g"] for x in new[:GROWTH_READINGS]], "rev_g": [x["rev_g"] for x in new[:GROWTH_READINGS]],
        "margins": [x["margin"] for x in new[:GROWTH_READINGS]], "latest_has_prior": latest["eps_prior"] is not None,
        "margin": latest["margin"], "margin_prior": latest["margin_prior"],
        "eps_ttm": ttm(s, 0), "eps_annual": years, "eps_annual_basis": basis, "eps_cagr": cagr, "roe": r, "roe_source": r_src,
        "surprise": last,
        "surprise_current": bool(last and abs((dt.date.fromisoformat(last["quarter"]) - latest["end"]).days) <= SURPRISE_MATCH_DAYS),
        "split_adjusted": any(f != 1.0 for f in split_factors(rows)),
        "source": rows[-1].get("source"), "basis": rows[-1].get("basis"), "name": meta.get("name"),
        "series": [{k: x[k] for k in ("end", "fiscal", "derived", "eps", "eps_g", "rev", "rev_g", "margin")} for x in s[-SERIES_QUARTERS:]],
    }


# ---------------------------------------------------------------- strategy views

def views() -> list:
    """The strategy sections shown on the Fundamentals page, each judging the shared metrics."""
    from . import sepa
    return [sepa]


def criteria() -> dict:
    return {**DOC, "views": [v.criteria() for v in views()]}


# ---------------------------------------------------------------- storage + batch

SCHEMA = """
CREATE TABLE IF NOT EXISTS fundamental_scores (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metrics JSONB NOT NULL,              -- growth.metrics(): the shared numbers
    views JSONB NOT NULL,                -- per strategy view: {"sepa": {verdict, code33, passed, scored, tests}}
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    financials.init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _roe_fallbacks(market: str) -> dict:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('quality_scores') IS NOT NULL")
        if not cur.fetchone()[0]:
            return {}
        cur.execute("SELECT symbol, (metrics->>'roe_avg')::float FROM quality_scores WHERE market=%s AND metrics->>'roe_avg' IS NOT NULL",
                    (market,))
        return dict(cur.fetchall())


def run(market: str, symbols: list[str] | None = None) -> dict:
    """Compute every company with stored quarters (or just `symbols`); replaces the market's rows."""
    init_schema()
    data, meta, fallback = financials.load(market, symbols), financials.load_meta(market), _roe_fallbacks(market)
    vs = views()
    out, counts = [], {}
    for sym, rows in data.items():
        m = metrics(rows, meta.get(sym), roe_fallback=fallback.get(sym))
        judged = {v.key: v.evaluate(m) for v in vs}
        for v in vs:
            for k, n in v.counts(judged[v.key]).items():
                counts[k] = counts.get(k, 0) + n
        out.append((market, sym, json.dumps(m, default=str), json.dumps(judged, default=str)))
    with db.get_connection().cursor() as cur:
        if symbols is None:
            cur.execute("DELETE FROM fundamental_scores WHERE market=%s", (market,))
        else:
            cur.execute("DELETE FROM fundamental_scores WHERE market=%s AND symbol = ANY(%s)", (market, list(symbols)))
    db.execute_values("INSERT INTO fundamental_scores (market, symbol, metrics, views) VALUES %s", out)
    return {"companies": len(out), **counts}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--symbols", default=None, help="comma separated (default: every company with stored quarters)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(run(a.market, [s.strip().upper() for s in a.symbols.split(",")] if a.symbols else None))


if __name__ == "__main__":
    main()
