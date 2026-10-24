"""Mutual fund NAVs — India from AMFI, the US from a curated list — with their own tables.

A fund has one price a day (its NAV), struck after the close, never traded through a book:
no open/high/low, no volume. So it is kept out of `prices`, whose every reader expects bars,
in two tables of its own:

    funds      (market, code)        name, fund house, category, plan, option, ISIN
    fund_nav   (market, code, date)  nav, dist

`nav` is the published NAV, unadjusted. `dist` is the cash paid per unit with that ex-date
(US dividends plus capital gains) — so a total return is nav plus reinvested dist, and an
India growth plan, which reinvests internally, always has dist 0.

India: every open-ended scheme's DIRECT plan, GROWTH option — one series per scheme, none of
the regular-plan or IDCW variants. Two sources:
  - the daily delta from AMFI, official: its history endpoint returns every fund house at once,
    so it is one request, from a few days before the last stored date (a missed day fills itself in).
    AMFI only serves dates from 1 April 2023 (earlier requests redirect to its website), so it
    cannot supply the history;
  - each scheme's history, once, from mfapi.in — an unofficial archive of AMFI's daily NAVs. It
    matched AMFI's own file on every overlapping NAV checked (121 of 121, 40 schemes). History
    starts at the scheme's launch, or January 2013 when direct plans began.
A scheme is new to the store when the delta first sees it, so only schemes listed today get
history: one closed or merged before then is missing (survivorship, as for stocks).

US: no free bulk NAV source exists, so `US_FUNDS` names the funds (Yahoo, by ticker); a fund with
no stored NAVs gets its full history, then a delta.

`fund_history` records each scheme whose history is stored, so the first run does the whole
backfill and an interrupted one resumes where it stopped.

    python3 -m swing_screener.marketdata.funds --market india          # delta, plus any missing history
    python3 -m swing_screener.marketdata.funds --market us --status
"""

from __future__ import annotations

import argparse
import datetime as dt
import logging
import re
import time
import warnings

import pandas as pd

from . import db

logger = logging.getLogger("funds")

SCHEMA = """
CREATE TABLE IF NOT EXISTS funds (
    market VARCHAR(16) NOT NULL,
    code VARCHAR(32) NOT NULL,          -- AMFI scheme code (India) / ticker (US)
    name TEXT NOT NULL,
    fund_house TEXT,
    category TEXT,
    plan TEXT,
    option TEXT,
    isin VARCHAR(16),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, code)
);
CREATE TABLE IF NOT EXISTS fund_nav (
    market VARCHAR(16) NOT NULL,
    code VARCHAR(32) NOT NULL,
    date DATE NOT NULL,
    nav DOUBLE PRECISION NOT NULL,      -- the published NAV, unadjusted
    dist DOUBLE PRECISION NOT NULL DEFAULT 0,   -- cash paid per unit with this ex-date
    PRIMARY KEY (market, code, date)
);
CREATE TABLE IF NOT EXISTS fund_history (
    market VARCHAR(16) NOT NULL,
    code VARCHAR(32) NOT NULL,          -- a scheme whose history has been fetched
    source TEXT NOT NULL,
    first_date DATE,
    rows INT NOT NULL,
    done_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, code)
);
"""

DELTA_OVERLAP_DAYS = 10     # a delta starts this far before the last stored date: a missed run heals itself


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


# ------------------------------------------------------------------ India: AMFI

AMFI_HISTORY = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
AMFI_EARLIEST = pd.Timestamp("2023-04-01")  # AMFI redirects any request for an earlier date (checked Oct 2026)
MFAPI = "https://api.mfapi.in/mf/{code}"
_CATEGORY = re.compile(r"^(Open Ended Schemes|Close Ended Schemes|Interval Fund Schemes)\s*\((.*)\)\s*$")


def _direct_growth(plan: str, option: str) -> bool:
    # "Unclaimed Redemption / Brokerage ... Growth" rows hold money owed to investors, not a fund
    o = option.lower()
    return ("direct" in plan.lower() and "growth" in o
            and not any(w in o for w in ("idcw", "dividend", "bonus", "unclaimed")))


def _amfi_get(start: pd.Timestamp, end: pd.Timestamp) -> str:
    """AMFI's NAV history text for every fund house. Anything but the NAV file is a failure: a date
    before AMFI_EARLIEST comes back as a redirect to AMFI's website, which must never read as an
    empty but successful answer."""
    import requests
    if start < AMFI_EARLIEST:
        raise ValueError(f"AMFI serves NAV history from {AMFI_EARLIEST.date()} only, not {start.date()}")
    params = {"mf": "", "tp": 1, "frmdt": start.strftime("%d-%b-%Y"), "todt": end.strftime("%d-%b-%Y")}
    for attempt, wait in enumerate((0, 30, 120)):
        time.sleep(wait)
        try:
            r = requests.get(AMFI_HISTORY, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=300,
                             allow_redirects=False)
            if r.status_code != 200 or not r.text.lstrip().startswith("Scheme Code"):
                raise RuntimeError(f"not a NAV file (HTTP {r.status_code}"
                                   + (f", redirected to {r.headers.get('Location')}" if r.is_redirect else "") + ")")
            return r.text
        except Exception as exc:  # noqa: BLE001 — AMFI is slow and occasionally times out: retry, then give up
            logger.warning("AMFI %s..%s attempt %d failed: %s", start.date(), end.date(), attempt + 1, exc)
    raise RuntimeError(f"AMFI NAV history {start.date()}..{end.date()} could not be fetched")


def parse_amfi(text: str) -> tuple[dict, list]:
    """AMFI's NAV history text -> ({code: (name, house, category, plan, option, isin)}, [(code, date, nav)]),
    direct-plan growth options only. The file interleaves category lines ("Open Ended Schemes ( ... )"),
    fund-house lines and `code;name;plan;option;isin;isin;nav;date` rows."""
    meta, navs = {}, []
    category = house = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("Scheme Code"):
            continue
        f = line.split(";")
        if len(f) == 8 and f[0].isdigit():
            if not _direct_growth(f[2], f[3]):
                continue
            try:
                d, nav = dt.datetime.strptime(f[7].strip(), "%d-%b-%Y").date(), float(f[6])
            except ValueError:
                continue                    # "N.A." or a malformed row
            if nav <= 0:
                continue
            meta[f[0]] = (f[1].strip(), house, category, f[2].strip(), f[3].strip(), (f[4] or f[5]).strip() or None)
            navs.append((f[0], d, nav))
        elif ";" not in line:
            m = _CATEGORY.match(line)
            if m:
                category = m.group(2).strip()
            else:
                house = line
    return meta, navs


def _store(market: str, meta: dict, navs: list) -> int:
    if meta:
        db.execute_values(
            """INSERT INTO funds (market, code, name, fund_house, category, plan, option, isin) VALUES %s
               ON CONFLICT (market, code) DO UPDATE SET name=EXCLUDED.name, fund_house=COALESCE(EXCLUDED.fund_house, funds.fund_house),
                 category=COALESCE(EXCLUDED.category, funds.category), plan=EXCLUDED.plan, option=EXCLUDED.option,
                 isin=COALESCE(EXCLUDED.isin, funds.isin), updated_at=now()""",
            [(market, c, *v) for c, v in meta.items()])
    if navs:
        # one row per (code, date): AMFI occasionally repeats a row within a window
        rows = list({(c, d): (market, c, d, nav, dist) for c, d, nav, dist in navs}.values())
        db.execute_values("""INSERT INTO fund_nav (market, code, date, nav, dist) VALUES %s
                             ON CONFLICT (market, code, date) DO UPDATE SET nav=EXCLUDED.nav, dist=EXCLUDED.dist""", rows)
        return len(rows)
    return 0


def _last_date(market: str) -> pd.Timestamp | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM fund_nav WHERE market=%s", (market,))
        d = cur.fetchone()[0]
    return pd.Timestamp(d) if d else None


def _mfapi_get(code: str) -> list | None:
    """One scheme's whole NAV history from mfapi.in as [(date, nav)], or None when it could not be fetched
    (so the scheme is retried next run). An unknown scheme is an empty list."""
    import requests
    for attempt, wait in enumerate((0, 10, 60)):
        time.sleep(wait)
        try:
            r = requests.get(MFAPI.format(code=code), timeout=60)
            r.raise_for_status()
            out = []
            for x in r.json().get("data") or []:
                try:
                    d, nav = dt.datetime.strptime(x["date"], "%d-%m-%Y").date(), float(x["nav"])
                except (KeyError, TypeError, ValueError):
                    continue
                if nav > 0:
                    out.append((d, nav))
            return out
        except Exception as exc:  # noqa: BLE001 — retry, then leave the scheme for the next run
            logger.warning("mfapi %s attempt %d failed: %s", code, attempt + 1, exc)
    return None


def _india_history(progress=None) -> int:
    """Each stored scheme's history before what the delta covers, once (fund_history records it). Rows on or
    after AMFI_EARLIEST are left to AMFI, the official source, where it already has them."""
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT f.code FROM funds f LEFT JOIN fund_history h ON h.market=f.market AND h.code=f.code
                       WHERE f.market='india' AND h.code IS NULL ORDER BY f.code""")
        todo = [r[0] for r in cur.fetchall()]
        # per scheme, where its AMFI rows begin: a scheme without history has only delta rows so far
        cur.execute("SELECT code, min(date) FROM fund_nav WHERE market='india' AND code = ANY(%s) GROUP BY code", (todo,))
        amfi_from = dict(cur.fetchall())
    if not todo:
        return 0
    logger.info("india: fetching NAV history for %d scheme(s) from mfapi.in", len(todo))
    total = failed = 0
    for i, code in enumerate(todo):
        hist = _mfapi_get(code)
        if hist is None:
            failed += 1
            continue
        keep_before = amfi_from.get(code) or dt.date.today()
        n = _store("india", {}, [(code, d, nav, 0.0) for d, nav in hist if d < keep_before])
        db.execute_values("""INSERT INTO fund_history (market, code, source, first_date, rows) VALUES %s
                             ON CONFLICT (market, code) DO UPDATE SET source=EXCLUDED.source, first_date=EXCLUDED.first_date,
                               rows=EXCLUDED.rows, done_at=now()""",
                          [("india", code, "mfapi.in", min(d for d, _ in hist) if hist else None, n)])
        total += n
        if progress:
            progress(f"fetching NAV history: {i + 1:,}/{len(todo):,} schemes · {total:,} NAVs"
                     + (f" · {failed} failed" if failed else ""), done=i + 1, total=len(todo))
        time.sleep(0.05)   # an unofficial, free service: stay gentle
    logger.info("india: history for %d schemes, %d NAVs, %d failed (retried next run)", len(todo) - failed, total, failed)
    return total


def _india_delta() -> tuple[int, int]:
    """(schemes seen, rows written) for the days since the last stored date."""
    today = pd.Timestamp.today().normalize()
    last = _last_date("india")
    start = (last - pd.Timedelta(days=DELTA_OVERLAP_DAYS)) if last is not None else today - pd.Timedelta(days=31)
    start = max(start, AMFI_EARLIEST)
    meta, navs = parse_amfi(_amfi_get(start, today))
    return len(meta), _store("india", meta, [(c, d, nav, 0.0) for c, d, nav in navs])


# ------------------------------------------------------------------ US: a curated list, from Yahoo

US_FUNDS: list[tuple[str, str, str, str]] = [   # (ticker, name, fund house, category)
    ("VFIAX", "Vanguard 500 Index Admiral", "Vanguard", "Large blend index"),
    ("VTSAX", "Vanguard Total Stock Market Index Admiral", "Vanguard", "Total market index"),
    ("VTSMX", "Vanguard Total Stock Market Index Investor", "Vanguard", "Total market index"),
    ("VTIAX", "Vanguard Total International Stock Index Admiral", "Vanguard", "International index"),
    ("VIMAX", "Vanguard Mid-Cap Index Admiral", "Vanguard", "Mid-cap index"),
    ("VSMAX", "Vanguard Small-Cap Index Admiral", "Vanguard", "Small-cap index"),
    ("VBTLX", "Vanguard Total Bond Market Index Admiral", "Vanguard", "Bond index"),
    ("VBIAX", "Vanguard Balanced Index Admiral", "Vanguard", "Balanced index"),
    ("VGSLX", "Vanguard Real Estate Index Admiral", "Vanguard", "Real estate index"),
    ("VWELX", "Vanguard Wellington Investor", "Vanguard", "Balanced"),
    ("VWINX", "Vanguard Wellesley Income Investor", "Vanguard", "Conservative allocation"),
    ("VDIGX", "Vanguard Dividend Growth Investor", "Vanguard", "Large blend"),
    ("VPMCX", "Vanguard PRIMECAP Investor", "Vanguard", "Large growth"),
    ("VGHCX", "Vanguard Health Care Investor", "Vanguard", "Health care"),
    ("VFORX", "Vanguard Target Retirement 2040", "Vanguard", "Target date"),
    ("VFIFX", "Vanguard Target Retirement 2050", "Vanguard", "Target date"),
    ("VTTSX", "Vanguard Target Retirement 2060", "Vanguard", "Target date"),
    ("FXAIX", "Fidelity 500 Index", "Fidelity", "Large blend index"),
    ("FSKAX", "Fidelity Total Market Index", "Fidelity", "Total market index"),
    ("FTIHX", "Fidelity Total International Index", "Fidelity", "International index"),
    ("FXNAX", "Fidelity US Bond Index", "Fidelity", "Bond index"),
    ("FCNTX", "Fidelity Contrafund", "Fidelity", "Large growth"),
    ("FBGRX", "Fidelity Blue Chip Growth", "Fidelity", "Large growth"),
    ("FMAGX", "Fidelity Magellan", "Fidelity", "Large growth"),
    ("FLPSX", "Fidelity Low-Priced Stock", "Fidelity", "Mid-cap value"),
    ("FDGRX", "Fidelity Growth Company", "Fidelity", "Large growth"),
    ("FBALX", "Fidelity Balanced", "Fidelity", "Balanced"),
    ("FSELX", "Fidelity Select Semiconductors", "Fidelity", "Technology"),
    ("FSPHX", "Fidelity Select Health Care", "Fidelity", "Health care"),
    ("FSCSX", "Fidelity Select Software & IT Services", "Fidelity", "Technology"),
    ("SWPPX", "Schwab S&P 500 Index", "Schwab", "Large blend index"),
    ("SWTSX", "Schwab Total Stock Market Index", "Schwab", "Total market index"),
    ("SWISX", "Schwab International Index", "Schwab", "International index"),
    ("SWAGX", "Schwab US Aggregate Bond Index", "Schwab", "Bond index"),
    ("AGTHX", "American Funds Growth Fund of America A", "American Funds", "Large growth"),
    ("AIVSX", "American Funds Investment Company of America A", "American Funds", "Large blend"),
    ("AWSHX", "American Funds Washington Mutual A", "American Funds", "Large value"),
    ("ANWPX", "American Funds New Perspective A", "American Funds", "Global"),
    ("AEPGX", "American Funds EuroPacific Growth A", "American Funds", "International growth"),
    ("NEWFX", "American Funds New World A", "American Funds", "Emerging markets"),
    ("ABALX", "American Funds American Balanced A", "American Funds", "Balanced"),
    ("CAIBX", "American Funds Capital Income Builder A", "American Funds", "Global allocation"),
    ("AMCPX", "American Funds AMCAP A", "American Funds", "Large growth"),
    ("ANCFX", "American Funds Fundamental Investors A", "American Funds", "Large blend"),
    ("PRGFX", "T. Rowe Price Growth Stock", "T. Rowe Price", "Large growth"),
    ("TRBCX", "T. Rowe Price Blue Chip Growth", "T. Rowe Price", "Large growth"),
    ("PRNHX", "T. Rowe Price New Horizons", "T. Rowe Price", "Small/mid growth"),
    ("PRWCX", "T. Rowe Price Capital Appreciation", "T. Rowe Price", "Moderate allocation"),
    ("DODGX", "Dodge & Cox Stock", "Dodge & Cox", "Large value"),
    ("DODFX", "Dodge & Cox International Stock", "Dodge & Cox", "International value"),
    ("DODIX", "Dodge & Cox Income", "Dodge & Cox", "Bond"),
    ("PTTRX", "PIMCO Total Return Institutional", "PIMCO", "Bond"),
    ("PIMIX", "PIMCO Income Institutional", "PIMCO", "Multisector bond"),
]


def _us_fetch(ticker: str, start: pd.Timestamp | None) -> pd.DataFrame:
    import yfinance as yf
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        t = yf.Ticker(ticker)
        df = (t.history(period="max", interval="1d", auto_adjust=False, actions=True) if start is None else
              t.history(start=start.strftime("%Y-%m-%d"), interval="1d", auto_adjust=False, actions=True))
    if df is None or df.empty:
        return pd.DataFrame()
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    dist = df.get("Dividends", 0) + df.get("Capital Gains", 0)
    out = pd.DataFrame({"nav": df["Close"], "dist": dist}).dropna(subset=["nav"])
    return out[out["nav"] > 0]


def _us_refresh() -> tuple[int, int, list]:
    """(funds updated, rows written, failed tickers). A fund with no stored NAVs gets its full history."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT code, max(date) FROM fund_nav WHERE market='us' GROUP BY code")
        last = {c: pd.Timestamp(d) for c, d in cur.fetchall()}
    _store("us", {t: (n, h, c, None, None, None) for t, n, h, c in US_FUNDS}, [])
    ok, rows, failed = 0, 0, []
    for ticker, *_ in US_FUNDS:
        start = last[ticker] - pd.Timedelta(days=DELTA_OVERLAP_DAYS) if ticker in last else None
        try:
            df = _us_fetch(ticker, start)
        except Exception as exc:  # noqa: BLE001 — one fund failing must not stop the rest
            logger.warning("us fund %s failed: %s", ticker, exc)
            df = pd.DataFrame()
        if df.empty:
            failed.append(ticker)
            continue
        rows += _store("us", {}, [(ticker, d.date(), float(r.nav), float(r.dist or 0.0)) for d, r in df.iterrows()])
        ok += 1
    return ok, rows, failed


# ------------------------------------------------------------------ the job's entry point

def refresh(market: str, progress=None) -> dict:
    """`progress(text, done=, total=)` is called during a backfill (the job passes its run-log step's)."""
    init_schema()
    t0 = time.time()
    if market == "india":
        # the delta first: it is what lists the schemes, and history is then fetched for any listed without it
        schemes, written = _india_delta()
        backfilled = _india_history(progress=progress)
        out = {"funds": schemes, "written": written + backfilled, "backfilled": backfilled, "failed": []}
    elif market == "us":
        n, written, failed = _us_refresh()
        out = {"funds": n, "written": written, "backfilled": 0, "failed": failed}
    else:
        raise ValueError(f"no fund source for market {market!r}")
    out["newest"] = _last_date(market)
    out["elapsed_s"] = round(time.time() - t0, 1)
    return out


def status(market: str) -> dict:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT count(*), count(DISTINCT code), min(date), max(date) FROM fund_nav WHERE market=%s""", (market,))
        rows, funds, first, last = cur.fetchone()
        cur.execute("SELECT count(*), count(*) FILTER (WHERE rows = 0) FROM fund_history WHERE market=%s", (market,))
        hist, empty = cur.fetchone()
    return {"rows": rows, "funds": funds, "first": first, "last": last, "with_history": hist, "history_empty": empty}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=["india", "us"])
    ap.add_argument("--status", action="store_true", help="print what is stored and exit")
    a = ap.parse_args()
    if not a.status:
        print(refresh(a.market))
    print(status(a.market))


if __name__ == "__main__":
    main()
