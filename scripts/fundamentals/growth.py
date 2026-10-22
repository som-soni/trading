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
put on today's share basis. Per-share figures (EPS, trailing EPS, annual EPS) are put on today's basis
from the filings themselves (`split_factors`): a split or bonus is read where the share count — stored, or
implied by the EPS — jumps by a split ratio, and for SEC filings the year-ago EPS each filing restates
confirms or vetoes it. Price history is stored split-adjusted, so it cannot say when a split happened.

    PYTHONPATH=. python3 -m fundamentals.growth --market us
    PYTHONPATH=. python3 -m fundamentals.growth --market india --symbols RELIANCE.NS
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import math

from swing_screener.config import MARKETS
from swing_screener.marketdata import db, financials

logger = logging.getLogger(__name__)

ANNUAL_YEARS = 3              # annual EPS growth is measured over this many fiscal years
STALE_RESULTS_DAYS = 200      # latest results older than this are flagged stale (the company stopped filing?)
GROWTH_READINGS = 8           # quarterly growth readings kept per company
SERIES_QUARTERS = 12          # quarters kept for the page's charts
SURPRISE_MATCH_DAYS = 45      # an earnings-history row belongs to the latest quarter when this close to its end

# share-count jumps read as a split or bonus issue (new shares / old): n-for-1 splits (Apple 7:1, O'Reilly
# 15:1, Booking 25:1, Chipotle 50:1 ...), a:b bonuses ((a+b)/b) and reverse splits; small ratios (1:5
# bonus = 1.2) are left out — an issue of shares can do that
SPLIT_NS = (2, 3, 4, 5, 6, 7, 8, 10, 12, 15, 20, 25, 30, 40, 50)
SHARE_MULTIPLES = sorted({*(float(n) for n in SPLIT_NS), 1.25, 4 / 3, 1.5, 5 / 3, 2.5, *(1 / n for n in SPLIT_NS)})
SHARE_MULTIPLE_TOL = 0.015     # small ratios: share issues and buybacks move the count a little too ...
SHARE_MULTIPLE_TOL_BIG = 0.05  # ... a 2x-or-more jump is unmistakable even with a few % of drift
BIG_SPLIT = 1.8                # a multiple at least this far from 1 (either way) is a "big" split
# The share basis of a quarter's EPS is read from three things (`split_factors`):
#   * SEC: the filing's own year-ago EPS against that quarter's EPS as first reported — the company
#     restating its past on the new basis. Comparatives are rounded and can be restated, hence the wider
#     tolerance (plus the cent rounding of small EPS); within COMPARATIVE_TOL of 1 they rule out any split
#     in that year, within COMPARATIVE_SAME a big one;
#   * the share count implied by the EPS itself (net income / EPS) — the EPS's own basis; EPS is rounded
#     to cents, so only from |EPS| >= IMPLIED_MIN_EPS, and only where it holds its level (IMPLIED_STEADY)
#     on the quarters either side, so one misfiled net income is not read as two splits;
#   * the stored share count (`shares`): enough on its own for NSE and yfinance, which carry no
#     comparative; for SEC a big jump in it is not taken when the filing shows a year-ago EPS without the
#     split, or none at all (a reverse merger: a new reporting entity).
COMPARATIVE_TOL = 0.08
EPS_ROUNDING = 0.005           # EPS is filed to the cent
COMPARATIVE_MAX_ERR = 0.05     # a comparative this uncertain from rounding (EPS of a few cents) cannot place a split
COMPARATIVE_SAME = (0.67, 1.5)
IMPLIED_MIN_EPS = 0.2
IMPLIED_STEADY = (0.8, 1.25)


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
        "US: EPS is put on today's share basis where a split shows in the filings — a jump at a split ratio in the share "
        "count (or in the count the EPS implies), confirmed by the year-ago EPS each filing restates on its new basis.",
        "One-off gains and charges are not removed. Check the filing behind a big number.",
        "Foreign companies whose statements (from Yahoo) are in another currency than their share price — TSMC in "
        "Taiwan dollars, Novo in Danish kroner — show growth and margins, but no P/E, book value or dividend yield: "
        "those would need exchange rates.",
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


def _big(x: float) -> bool:
    return max(x, 1 / x) >= BIG_SPLIT


def _snap(r: float | None, tol_big: float = SHARE_MULTIPLE_TOL_BIG, big_only: bool = False) -> float | None:
    """The split/bonus multiple a ratio of share counts sits at, 1.0 for no split, None when unknown."""
    if r is None or r <= 0:
        return None
    hits = [x for x in SHARE_MULTIPLES if (not big_only or _big(x))
            and abs(r / x - 1) <= (tol_big if max(x, 1 / x) >= 2 else SHARE_MULTIPLE_TOL)]
    return min(hits, key=lambda x: abs(math.log(r / x))) if hits else 1.0


def _implied(r: dict) -> float | None:
    """Shares implied by the EPS (net income / EPS): the EPS's own share basis."""
    e, n = r.get("eps"), r.get("net_income")
    if not e or not n or abs(e) < IMPLIED_MIN_EPS or (e > 0) != (n > 0):
        return None
    return n / e


def _comparative(rows: list[dict], k: int) -> tuple[float, int, float] | None:
    """SEC: row k's filing restates the year-ago quarter's EPS on its own basis; that quarter's EPS as first
    reported over it is the split multiple (new shares / old) between the two filings.
    (multiple, the year-ago row, its rounding error: EPS is filed to the cent)"""
    p = rows[k].get("eps_prior")
    j = _year_before(rows, k) if p else None
    e = rows[j].get("eps") if j is not None else None
    if not e or (e > 0) != (p > 0):
        return None
    return e / p, j, EPS_ROUNDING / abs(e) + EPS_ROUNDING / abs(p)


def split_factors(rows: list[dict]) -> list[float]:
    """Per row (oldest first), the split/bonus multiple between it and the newest row: EPS on today's
    share basis = eps / factor.

    Walking forward, a split is placed at a quarter whose share count (stored, or implied by its EPS) has
    jumped by a split or bonus ratio since the previous quarter with that evidence. For SEC filings the
    year-ago EPS each filing restates decides: it confirms a jump (or places one the counts cannot see),
    and vetoes a jump it does not show; a big jump in the count where the filing has no year-ago EPS (a
    reverse merger) is not taken. Rows with no
    evidence keep the older basis. See the constants above for the tolerances."""
    n = len(rows)
    sh = [r["shares"] if (r.get("shares") or 0) > 0 else None for r in rows]
    imp = [_implied(r) for r in rows]
    m = [1.0] * n      # m[k]: the multiple (new shares / old) between rows k-1 and k

    def prev(vals, k):
        return next((i for i in range(k - 1, -1, -1) if vals[i] is not None), None)

    def nxt(vals, k):
        return next((i for i in range(k + 1, n) if vals[i] is not None), None)

    def between(i, k):
        """The multiple already placed after row i up to (not including) row k."""
        p = 1.0
        for r in range(i + 1, k):
            p *= m[r]
        return p

    def jump(vals, k):
        """The ratio of row k's count to the previous one's, less the splits already placed between."""
        i = prev(vals, k)
        return vals[k] / vals[i] / between(i, k) if vals[k] is not None and i is not None else None

    def steady(vals, k, after=True):
        """The jump at row k is not one quarter's misfiled count: on either side the count holds its level,
        or moves by another split ratio (two splits in a row) — but not straight back (x, then 1/x)."""
        i, b = prev(vals, k), nxt(vals, k)
        a = prev(vals, i) if i is not None else None
        here = vals[k] / vals[i]

        def ok(x, y):
            r = x / y
            if IMPLIED_STEADY[0] <= r <= IMPLIED_STEADY[1]:
                return True
            return _snap(r) not in (None, 1.0) and abs(math.log(r * here)) > math.log(IMPLIED_STEADY[1])

        return (a is None or ok(vals[i], vals[a])) and (ok(vals[b], vals[k]) if b is not None else not after)

    def comparative(k):
        """Row k's comparative multiple, less the splits already placed inside its year, and its rounding error."""
        c = _comparative(rows, k) if k >= 0 else None
        return (c[0] / between(c[1], k), c[2]) if c else (None, None)

    def big_split(c, err):
        if c is None or err > COMPARATIVE_MAX_ERR or COMPARATIVE_SAME[0] <= c <= COMPARATIVE_SAME[1]:
            return None
        return _snap(c, COMPARATIVE_TOL + err, big_only=True)

    imp_led: dict = {}   # row -> multiple placed from the EPS's own count before the share count moved
    for k in range(1, n):
        r_sh, r_imp = jump(sh, k), jump(imp, k)
        c, err = comparative(k)
        x_sh = _snap(r_sh)
        agrees = x_sh not in (None, 1.0) and c is not None and abs(c / x_sh - 1) <= COMPARATIVE_TOL + err
        if x_sh not in (None, 1.0) and not agrees:
            if not (_big(x_sh) or prev(sh, k) == k - 1):
                x_sh = None   # a small ratio across a gap in the counts says little: issues add up too
            elif not steady(sh, k, after=False):
                x_sh = None   # a count that keeps jumping about is misfiled, not split
        # the EPS's own count: 1.0 when it held its level, a big multiple when it jumped by one and holds
        # the new level, else None (unknown — its net income or EPS is too noisy to say)
        if r_imp is None:
            x_imp = None
        elif IMPLIED_STEADY[0] <= r_imp <= IMPLIED_STEADY[1]:
            x_imp = 1.0
        else:
            x_imp = _snap(r_imp, big_only=True)
            x_imp = x_imp if x_imp != 1.0 and steady(imp, k) else None
        x_c = big_split(c, err)
        if x_c not in (None, 1.0):
            # the filing shows a big split within the year: here, if a count jumps here (the same way, at
            # least half of it in log terms), or if no count can say and the previous filing did not show it
            here = any(r is not None and (r > 1) == (x_c > 1) and abs(math.log(r)) >= abs(math.log(x_c)) / 2 for r in (r_sh, r_imp))
            if here or (r_sh is None and r_imp is None and big_split(*comparative(k - 1)) != x_c):
                # a count that sits at a big split ratio the same way is more precise than a comparative
                # (rounded, sometimes restated for other reasons too)
                m[k] = next((x for x in (x_sh, x_imp) if x is not None and _big(x) and (x > 1) == (x_c > 1)), x_c)
            continue
        # the EPS's own count leads: filings put EPS on the new basis as soon as the split is known (Ind AS 33
        # / ASC 260 adjust retroactively), often a quarter before the period-end share capital shows it
        led = x_imp not in (None, 1.0) and x_sh in (None, 1.0)
        x = x_imp if led else x_sh if x_sh is not None else x_imp
        if x in (None, 1.0):
            continue
        if x_imp == 1.0 and _big(x):
            continue      # the EPS's own share count held steady: a misfiled share count
        if not led and _big(x) and x_imp is None and any(imp_led.get(r) == x for r in (k - 1, k - 2)):
            continue      # the share count catching up with a split already placed from the EPS
        if c is not None and ((err <= COMPARATIVE_TOL / 2 and abs(c - 1) <= COMPARATIVE_TOL)
                              or (_big(x) and COMPARATIVE_SAME[0] <= c <= COMPARATIVE_SAME[1])):
            continue      # the restated year-ago EPS shows no such split
        if (_big(x) and x_imp != x and rows[k].get("source") == "sec_edgar" and rows[k].get("eps") is not None
                and rows[k].get("eps_prior") is None):
            continue      # a big jump in the count with no year-ago figure in the filing: a new reporting entity
        m[k] = x
        if led:
            imp_led[k] = x
    f = [1.0] * n
    for k in range(n - 2, -1, -1):
        f[k] = f[k + 1] * m[k + 1]
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
    from . import canslim, sepa
    return [sepa, canslim]


def criteria() -> dict:
    return {**DOC, "views": [v.criteria() for v in views()]}


# ---------------------------------------------------------------- storage + batch

SCHEMA = """
CREATE TABLE IF NOT EXISTS fundamental_scores (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metrics JSONB NOT NULL,              -- growth.metrics(): the shared numbers
    views JSONB NOT NULL,                -- per strategy view: {"sepa": {...}, "canslim": {...}} each {verdict, code33, passed, scored, tests}
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
