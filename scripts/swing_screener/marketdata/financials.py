"""Company financials from the filings — the data layer behind the Fundamentals (company) page.

Per company, from the market's official filings (`MarketConfig.quarterly_source`):

  * quarterly results rows (`quarterly_results`): revenue, net income, EPS ... with their year-ago
    comparatives — what `fundamentals/growth.py` measures growth and acceleration from;
  * every statement line (`financial_lines`), screener.in style: the quarterly and annual P&L
    (sales, expenses, operating profit, other income, interest, depreciation, profit before tax, tax,
    net profit, EPS), the balance sheet at each year end (and the latest half / quarter), and the
    annual cash flow;
  * India: the shareholding pattern each quarter (`shareholding`: promoters, FII, DII, government, public);
  * a profile (Yahoo: description, website, dividend yield, holders) and the earnings surprises, in
    `quarterly_fetch.meta`.

Sources:

  sec_edgar  US. SEC XBRL "company facts" (data.sec.gov): every 10-Q/10-K figure with its filing
             date. Free, no key; SEC asks for a contact in the User-Agent (SEC_USER_AGENT in
             scripts/.env) and at most 10 requests a second.
             * Q4 is not filed on its own: it is the 10-K's full year minus the Q3 10-Q's nine months
               (`derived`). EPS done this way is approximate (weighted shares differ by period).
             * Each quarter keeps the value AS FIRST REPORTED, and its year-ago comparative is taken
               from that SAME filing (`*_prior`) — so a growth rate is point-in-time and on one share
               basis even across a split. Annual and balance-sheet lines take the latest filed value
               (restated), as a company page shows them.
  nse        India. NSE results filings: the legacy feed (to Dec 2024) and SEBI's Integrated Filing
             (from 2025), one XBRL document per quarter per basis — the quarter, and in a Q4 document
             the full year, the year-end balance sheet and (since about FY2020) the cash flow.
             Consolidated when the company files it for most quarters, else standalone — never mixed
             within a company. Banks file a different layout (interest earned, deposits, advances) and
             are mapped onto the same lines. Parsed documents are cached (`nse_documents`), so a
             document is downloaded once. nseindia.com rejects clients without a browser session, so
             requests go through one; if NSE changes its API the fetch fails loudly and the yfinance
             fallback is used.
  yfinance   the fallback for a company the source has nothing for (foreign filers on 20-F, ADRs,
             NSE gaps): ~5 quarters and 4 years, enough for growth but not acceleration.

Re-fetching is cheap: a company is re-checked when a new quarter's results could be out (quarter end
+ 91 + RESULTS_GRACE_DAYS) at most every RECHECK_DAYS, else every MAX_AGE_DAYS.

    PYTHONPATH=. python3 -m swing_screener.marketdata.financials --market us --symbols NVDA,AAPL
    PYTHONPATH=. python3 -m swing_screener.marketdata.financials --market india --symbols RELIANCE.NS --force

Results ANNOUNCEMENTS (`results_announcements`), India only: the moment NSE published each quarter's
results, from both feeds, back to 2005. The quarter rows above start where NSE's XBRL documents do (about
2017, and LOOKBACK_QUARTERS keeps five years), but NSE lists every older filing too -- with no XBRL document,
only a link to an HTML page of figures, and its broadcast time. That time is all an event strategy needs
to tie a price reaction to the news (`strategies/earnings_gaps.py`), and before it was stored India had no
announcement history before 2020, so the 2013-2021 optimise window had almost nothing to tie a reaction to.
The US has no equivalent: SEC filing dates land on or after the announcement, not at it.

Backtests read these point in time: `load` and `load_lines` honour a stage's boundary (`asof`), and
`backtesting/fundamental_filter.py`, `pead.py` and `quality_momentum.py` judge each date only on what
was public by then.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import os
import time
from collections import defaultdict

import requests

from . import db
from . import asof
from ..config import MARKETS
from ..paths import DATA_DIR

logger = logging.getLogger(__name__)

FIELDS = ("revenue", "net_income", "eps", "gross_profit", "operating_income", "pretax_income")
# How many quarters to keep, per source, because the two cost completely different things.
# EDGAR returns a company's WHOLE XBRL history in one `companyfacts` response, so depth is
# free -- we were downloading seventeen years of a company and discarding twelve. NSE has no
# bulk endpoint: `choose_filings` downloads one XBRL document per quarter, so every extra
# quarter is another request, and its legacy feed only reaches back about seven years anyway.
SEC_LOOKBACK_QUARTERS = 68    # ~17 years: XBRL was phased in over 2009-2011, so this is the practical floor
LOOKBACK_QUARTERS = 20        # NSE: five years of quarters; the 3-year annual test needs 16
ANNUAL_YEARS_BACK = 10        # annual P&L / balance sheet / cash flow kept for this many fiscal years
SHP_DETAIL_QUARTERS = 4       # India: the detailed shareholding filing (FII / DII split, ~0.5 MB each) for this many
                              # quarters at the first fetch; one new quarter at a time after that
MAX_AGE_DAYS = 30             # re-check every company at least this often
RECHECK_DAYS = 3              # ... and this often while a new quarter's results are due
RESULTS_GRACE_DAYS = 10       # a new quarter is "due" from the next quarter end + this many days
NOT_FOUND_RETRY_DAYS = 30     # nothing at the source (fund, ETF, unlisted filer): look again after this
LINES_FILING_LAG_DAYS = 90    # a statement line has no filing date: treat it as public this long after its period
                              # ended (10-K / NSE annual results come within 60-90 days of the year end)
SEC_PAUSE = 0.15              # SEC allows 10 requests/s
NSE_PAUSE = 0.35
YF_PAUSE = 0.3

_PRIOR = [f"{f}_prior" for f in FIELDS]
COLUMNS = ["period_end", "period_start", "fiscal", "source", "basis", "filed", "derived",
           *[c for f in FIELDS for c in (f, f"{f}_prior")], "equity", "shares", "doc_url", "eps_fy", "net_income_fy"]

SCHEMA = f"""
CREATE TABLE IF NOT EXISTS quarterly_results (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, period_end DATE NOT NULL,
    period_start DATE, fiscal VARCHAR(16), source VARCHAR(16) NOT NULL, basis VARCHAR(16),
    filed DATE,                          -- first reported (SEC) / filed (NSE); null from yfinance
    derived BOOLEAN NOT NULL DEFAULT false,   -- SEC Q4 = full year - nine months
    {", ".join(f"{c} DOUBLE PRECISION" for f in FIELDS for c in (f, f + "_prior"))},
    equity DOUBLE PRECISION,             -- shareholders' equity at period end, where filed
    shares DOUBLE PRECISION,             -- diluted weighted shares (SEC, yfinance) / paid-up / face value (NSE)
    doc_url TEXT,
    PRIMARY KEY (market, symbol, period_end)
);
-- on the row of a fiscal year's last quarter: that full year's EPS and net income (10-K / NSE Q4 filing)
ALTER TABLE quarterly_results ADD COLUMN IF NOT EXISTS eps_fy DOUBLE PRECISION;
ALTER TABLE quarterly_results ADD COLUMN IF NOT EXISTS net_income_fy DOUBLE PRECISION;
CREATE TABLE IF NOT EXISTS financial_lines (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    period_type VARCHAR(2) NOT NULL,     -- Q (a quarter's P&L) | FY (a fiscal year's P&L and cash flow) | BS (balance sheet on that date)
    period_end DATE NOT NULL, line VARCHAR(32) NOT NULL,   -- LINES
    value DOUBLE PRECISION, source VARCHAR(16),
    PRIMARY KEY (market, symbol, period_type, period_end, line)
);
CREATE TABLE IF NOT EXISTS shareholding (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, period_end DATE NOT NULL,
    promoters DOUBLE PRECISION, fii DOUBLE PRECISION, dii DOUBLE PRECISION, government DOUBLE PRECISION,
    public DOUBLE PRECISION, shareholders BIGINT,     -- percentages as fractions; FII/DII only where the detail was read
    PRIMARY KEY (market, symbol, period_end)
);
CREATE TABLE IF NOT EXISTS nse_documents (
    url TEXT PRIMARY KEY, kind VARCHAR(8) NOT NULL, parser INT NOT NULL,
    parsed JSONB, fetched_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS results_announcements (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, period_end DATE NOT NULL,
    basis VARCHAR(16) NOT NULL,           -- consolidated | standalone
    announced_at TIMESTAMP NOT NULL,      -- exchange local time the results were broadcast
    source VARCHAR(24) NOT NULL,          -- nse_legacy | nse_integrated
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, period_end, basis, announced_at)
);
CREATE TABLE IF NOT EXISTS quarterly_fetch (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    source VARCHAR(16), status VARCHAR(8) NOT NULL,   -- ok | none | error
    quarters INT, latest_end DATE, error TEXT,
    meta JSONB,                          -- name, basis, layout, cik, earnings surprises, profile
    PRIMARY KEY (market, symbol)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _d(s) -> dt.date | None:
    return dt.date.fromisoformat(str(s)[:10]) if s else None


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


# The statement lines every source is mapped onto (financial_lines.line), by statement.
LINES = {
    "pl": ("sales", "expenses", "operating_profit", "other_income", "interest", "depreciation", "exceptional", "pbt", "tax",
           "net_profit", "eps", "dividend_ps", "face_value", "shares"),
    "bs": ("equity_capital", "reserves", "equity", "minority", "deposits", "borrowings", "other_liabilities", "total_liabilities",
           "fixed_assets", "cwip", "investments", "advances", "cash", "receivables", "inventory", "other_assets", "total_assets",
           "shares"),
    "cf": ("cfo", "cfi", "cff", "net_cash", "capex", "dividends_paid"),
}


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _sum(*vals):
    """Sum of the values that are present (None when none are)."""
    xs = [v for v in vals if v is not None]
    return sum(xs) if xs else None


def _row(**kw) -> dict:
    r = {c: None for c in COLUMNS}
    r["derived"] = False
    r.update(kw)
    return r


# ------------------------------------------------------------------ SEC EDGAR (US)

SEC_CONCEPTS = {
    "revenue": ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "RevenueFromContractWithCustomerIncludingAssessedTax",
                "SalesRevenueNet", "SalesRevenueGoodsNet", "SalesRevenueServicesNet", "RevenuesNetOfInterestExpense",
                "InterestAndDividendIncomeOperating"),
    "net_income": ("NetIncomeLoss", "NetIncomeLossAvailableToCommonStockholdersBasic", "ProfitLoss"),
    "eps": ("EarningsPerShareDiluted", "EarningsPerShareBasicAndDiluted", "EarningsPerShareBasic"),
    "gross_profit": ("GrossProfit",),
    "operating_income": ("OperatingIncomeLoss",),
    "pretax_income": ("IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
                      "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments"),
}
SEC_SHARES = ("WeightedAverageNumberOfDilutedSharesOutstanding", "WeightedAverageNumberOfShareOutstandingBasicAndDiluted")
SEC_EQUITY = ("StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")
SEC_FORMS = ("10-Q", "10-K", "10-QT", "10-KT")
QUARTER_DAYS, NINE_MONTH_DAYS, YEAR_DAYS = (80, 100), (250, 290), (350, 380)
YEAR_APART = (355, 375)       # the same quarter a year earlier (52/53-week years drift by a few days)


def _sec_headers() -> dict:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        raise RuntimeError("SEC_USER_AGENT is not set: add `SEC_USER_AGENT=<name> <email>` to scripts/.env")
    return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}


_ciks: dict | None = None


def _sec_ciks() -> dict:
    """Ticker -> CIK from SEC's own list, cached in data/ for a week."""
    global _ciks
    if _ciks is not None:
        return _ciks
    path = DATA_DIR / "sec_company_tickers.json"
    if not path.exists() or time.time() - path.stat().st_mtime > 7 * 86400:
        r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=_sec_headers(), timeout=30)
        r.raise_for_status()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path.write_bytes(r.content)
    _ciks = {str(v["ticker"]).upper(): int(v["cik_str"]) for v in json.loads(path.read_text()).values()}
    return _ciks


def _sec_cik(symbol: str) -> int | None:
    ciks, s = _sec_ciks(), symbol.upper()
    for k in (s, s.replace(".", "-"), s.replace("-", "."), s.replace("-", "")):
        if k in ciks:
            return ciks[k]
    return None


def _days(f) -> int | None:
    return (f["_end"] - f["_start"]).days if f.get("_start") else None


def _in(n, rng) -> bool:
    return n is not None and rng[0] <= n <= rng[1]


def _year_apart(a: dt.date, b: dt.date) -> bool:
    return _in((a - b).days, YEAR_APART)


def sec_quarters(facts: list[dict], additive: bool = True) -> dict:
    """One XBRL concept's facts -> {quarter end: {val, prior, filed, start, derived, fiscal}}.

    A quarter is the 3-month fact as FIRST reported, with its year-ago comparative from the same
    filing. A missing Q4 is the 10-K's full year minus the Q3 10-Q's nine months (both from one
    fiscal year's first reports), and its comparative is the prior full year minus the prior nine
    months from those same two filings. With additive=False (share counts) a missing Q4 takes the
    full-year value instead.
    """
    fs = []
    for f in facts:
        if str(f.get("form", "")).split("/")[0] not in SEC_FORMS or f.get("val") is None:
            continue
        f = dict(f, _end=_d(f["end"]), _start=_d(f.get("start")), _filed=_d(f["filed"]))
        fs.append(f)
    by_accn = defaultdict(list)
    for f in fs:
        by_accn[f["accn"]].append(f)

    def fiscal(f, fp=None):
        return f"FY{f.get('fy')} {fp or f.get('fp')}" if f.get("fy") else None

    out: dict = {}
    nine: dict = {}   # (start, end) of a nine-month fact -> (filed, val, prior val) as first reported
    for accn, group in by_accn.items():
        qs = [f for f in group if _in(_days(f), QUARTER_DAYS)]
        if qs:
            end = max(f["_end"] for f in qs)
            cur = min((f for f in qs if f["_end"] == end), key=lambda f: f["_filed"])
            prior = next((f["val"] for f in qs if _year_apart(end, f["_end"])), None)
            if end not in out or cur["_filed"] < out[end]["filed"]:
                out[end] = {"val": float(cur["val"]), "prior": _num(prior), "filed": cur["_filed"], "start": cur["_start"],
                            "derived": False, "fiscal": fiscal(cur)}
        ns = [f for f in group if _in(_days(f), NINE_MONTH_DAYS)]
        if ns:
            end = max(f["_end"] for f in ns)
            cur = next(f for f in ns if f["_end"] == end)
            prior = next((f for f in ns if _year_apart(end, f["_end"])), None)
            key = (cur["_start"], end)
            if key not in nine or cur["_filed"] < nine[key][0]:
                nine[key] = (cur["_filed"], float(cur["val"]), (prior["_start"], prior["_end"], float(prior["val"])) if prior else None)
    years = defaultdict(list)
    for accn, group in by_accn.items():
        ys = [f for f in group if _in(_days(f), YEAR_DAYS)]
        if ys:
            end = max(f["_end"] for f in ys)
            years[end].append((min(f["_filed"] for f in ys if f["_end"] == end), accn, ys, end))
    for end, cands in years.items():
        if end in out:
            continue
        filed, accn, ys, _ = min(cands)
        fy = next(f for f in ys if f["_end"] == end)
        if not additive:
            out[end] = {"val": float(fy["val"]), "prior": None, "filed": filed, "start": None, "derived": True,
                        "fiscal": fiscal(fy, "Q4")}
            continue
        n_key = next(((s, e) for (s, e) in nine if s == fy["_start"] and _in((end - e).days, QUARTER_DAYS)), None)
        if n_key is None:
            continue
        _, n_val, n_prior = nine[n_key]
        prior = None
        fy_prev = next((f for f in ys if _year_apart(end, f["_end"])), None)
        if fy_prev is not None and n_prior is not None and n_prior[0] == fy_prev["_start"]:
            prior = float(fy_prev["val"]) - n_prior[2]
        out[end] = {"val": float(fy["val"]) - n_val, "prior": prior, "filed": filed, "start": n_key[1] + dt.timedelta(days=1),
                    "derived": True, "fiscal": fiscal(fy, "Q4"),
                    "fy": float(fy["val"]), "fy_prior": float(fy_prev["val"]) if fy_prev is not None else None}
    return out


def _sec_units(concept: dict, *prefer) -> list:
    units = concept.get("units", {})
    for u in prefer:
        if u in units:
            return units[u]
    return next(iter(units.values()), [])


def parse_sec(facts_json: dict) -> list[dict]:
    """Company facts -> quarter rows, newest last."""
    gaap = facts_json.get("facts", {}).get("us-gaap", {})
    per_field: dict[str, dict] = {}
    for field, names in SEC_CONCEPTS.items():
        merged: dict = {}
        for name in names:   # per quarter, the first concept (in priority order) that has it
            if name in gaap:
                units = ("USD/shares",) if field == "eps" else ("USD",)
                for end, v in sec_quarters(_sec_units(gaap[name], *units)).items():
                    merged.setdefault(end, v)
        per_field[field] = merged
    shares: dict = {}
    for name in SEC_SHARES:
        if name in gaap:
            for end, v in sec_quarters(_sec_units(gaap[name], "shares"), additive=False).items():
                shares.setdefault(end, v["val"])
    equity: dict = {}
    for name in SEC_EQUITY:
        if name in gaap:
            for f in _sec_units(gaap[name], "USD"):
                if not f.get("start") and str(f.get("form", "")).split("/")[0] in SEC_FORMS:
                    equity.setdefault(_d(f["end"]), float(f["val"]))
    # A derived Q4 EPS (full year - nine months) mixes share bases when a split falls between the Q3 10-Q
    # and the 10-K. Take the full year's EPS in proportion to Q4's share of the year's net income instead:
    # one filing, one share basis (and its comparative from the same 10-K).
    eps, ni = per_field["eps"], per_field["net_income"]
    for end, e in eps.items():
        n = ni.get(end)
        if e["derived"] and n and n.get("derived") and e.get("fy") is not None and n.get("fy"):
            e["val"] = e["fy"] * n["val"] / n["fy"]
            e["prior"] = (e["fy_prior"] * n["prior"] / n["fy_prior"]
                          if e.get("fy_prior") is not None and n.get("prior") is not None and n.get("fy_prior") else None)
    full_year: dict = {"eps": {}, "net_income": {}}   # fiscal year end -> the year's value as first reported in a 10-K
    for field in full_year:
        for name in SEC_CONCEPTS[field]:
            if name in gaap:
                for f in _sec_units(gaap[name], "USD/shares" if field == "eps" else "USD"):
                    if str(f.get("form", "")).startswith("10-K") and f.get("start") and _in((_d(f["end"]) - _d(f["start"])).days, YEAR_DAYS):
                        end, filed = _d(f["end"]), _d(f["filed"])
                        if end not in full_year[field] or filed < full_year[field][end][0]:
                            full_year[field][end] = (filed, float(f["val"]))
                if full_year[field]:
                    break
    ends = sorted(set(per_field["revenue"]) | set(per_field["net_income"]) | set(per_field["eps"]))[-SEC_LOOKBACK_QUARTERS:]
    rows = []
    for end in ends:
        base = next((per_field[f][end] for f in ("eps", "net_income", "revenue") if end in per_field[f]))
        r = _row(period_end=end, period_start=base["start"], fiscal=base["fiscal"], source="sec_edgar", basis="consolidated",
                 filed=min(per_field[f][end]["filed"] for f in FIELDS if end in per_field[f]),
                 derived=any(per_field[f][end]["derived"] for f in FIELDS if end in per_field[f]),
                 equity=equity.get(end), shares=shares.get(end),
                 eps_fy=full_year["eps"].get(end, (None, None))[1], net_income_fy=full_year["net_income"].get(end, (None, None))[1])
        for f in FIELDS:
            if end in per_field[f]:
                r[f], r[f + "_prior"] = per_field[f][end]["val"], per_field[f][end]["prior"]
        rows.append(r)
    return rows


SEC_PL = {
    "sales": SEC_CONCEPTS["revenue"],
    "operating_profit": ("OperatingIncomeLoss",),
    "other_income": ("NonoperatingIncomeExpense", "OtherNonoperatingIncomeExpense"),
    "interest": ("InterestExpense", "InterestExpenseNonoperating", "InterestExpenseDebt"),
    "depreciation": ("DepreciationDepletionAndAmortization", "DepreciationAndAmortization", "DepreciationAmortizationAndAccretionNet",
                     "Depreciation"),
    "pbt": SEC_CONCEPTS["pretax_income"],
    "tax": ("IncomeTaxExpenseBenefit",),
    "net_profit": SEC_CONCEPTS["net_income"],
    "eps": SEC_CONCEPTS["eps"],
    "dividend_ps": ("CommonStockDividendsPerShareDeclared", "CommonStockDividendsPerShareCashPaid"),
}
SEC_BS = {
    "equity": ("StockholdersEquity",), "minority": ("MinorityInterest",),
    "capital": ("CommonStocksIncludingAdditionalPaidInCapital",), "common": ("CommonStockValue",), "apic": ("AdditionalPaidInCapitalCommonStock", "AdditionalPaidInCapital"),
    "lt_debt": ("LongTermDebt", "LongTermDebtAndCapitalLeaseObligations"), "lt_debt_nc": ("LongTermDebtNoncurrent", "LongTermDebtAndCapitalLeaseObligationsNoncurrent"),
    "lt_debt_c": ("LongTermDebtCurrent", "LongTermDebtAndCapitalLeaseObligationsCurrent"),
    "st_debt": ("ShortTermBorrowings",), "cp": ("CommercialPaper",),
    "total_assets": ("Assets",), "liabilities_and_equity": ("LiabilitiesAndStockholdersEquity",),
    "fixed_assets": ("PropertyPlantAndEquipmentNet", "PropertyPlantAndEquipmentAndFinanceLeaseRightOfUseAssetAfterAccumulatedDepreciationAndAmortization"),
    "lt_inv": ("LongTermInvestments", "MarketableSecuritiesNoncurrent"), "st_inv": ("ShortTermInvestments", "MarketableSecuritiesCurrent"),
    "cash": ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents"),
    "receivables": ("AccountsReceivableNetCurrent", "ReceivablesNetCurrent"), "inventory": ("InventoryNet",),
}
SEC_CF = {
    "cfo": ("NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"),
    "cfi": ("NetCashProvidedByUsedInInvestingActivities", "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations"),
    "cff": ("NetCashProvidedByUsedInFinancingActivities", "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations"),
    "net_cash": ("CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
                 "CashAndCashEquivalentsPeriodIncreaseDecrease"),
    "capex": ("PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"),
    "dividends_paid": ("PaymentsOfDividends", "PaymentsOfDividendsCommonStock"),
}


def _unit_for(line: str) -> tuple:
    return ("USD/shares",) if line in ("eps", "dividend_ps") else ("USD",)


def _sec_fy(gaap: dict, names: tuple, units: tuple, first: bool = False) -> dict:
    """Fiscal-year values from 10-Ks, the latest filed per year end (as the company now presents them) —
    or with first=True as first reported (per-share figures: on the share count of that year's 10-K, so a
    later split is corrected once, from the share counts); per year, the first concept in priority order."""
    out: dict = {}
    for name in names:
        if name not in gaap:
            continue
        best: dict = {}
        for f in _sec_units(gaap[name], *units):
            if not str(f.get("form", "")).startswith("10-K") or not f.get("start") or f.get("val") is None:
                continue
            end, start = _d(f["end"]), _d(f["start"])
            newer = end not in best or (_d(f["filed"]) < best[end][0] if first else _d(f["filed"]) >= best[end][0])
            if _in((end - start).days, YEAR_DAYS) and newer:
                best[end] = (_d(f["filed"]), float(f["val"]))
        for end, (_, v) in best.items():
            out.setdefault(end, v)
    return out


def _sec_inst(gaap: dict, names: tuple, units: tuple = ("USD",)) -> dict:
    """Balance-sheet values per date (10-K / 10-Q), the latest filed; first concept in priority order."""
    out: dict = {}
    for name in names:
        if name not in gaap:
            continue
        best: dict = {}
        for f in _sec_units(gaap[name], *units):
            if f.get("start") or f.get("val") is None or str(f.get("form", "")).split("/")[0] not in SEC_FORMS:
                continue
            end = _d(f["end"])
            if end not in best or _d(f["filed"]) >= best[end][0]:
                best[end] = (_d(f["filed"]), float(f["val"]))
        for end, (_, v) in best.items():
            out.setdefault(end, v)
    return out


def _sec_q(gaap: dict, names: tuple, units: tuple) -> dict:
    out: dict = {}
    for name in names:
        if name in gaap:
            for end, v in sec_quarters(_sec_units(gaap[name], *units)).items():
                out.setdefault(end, v["val"])
    return out


def sec_lines(facts_json: dict, rows: list[dict]) -> tuple[list[tuple], str]:
    """Company facts -> statement lines [(period_type, period_end, line, value)] and the layout name.
    `rows`: parse_sec's quarters, whose sales / profit / EPS the quarterly P&L reuses (as first reported)."""
    gaap = facts_json.get("facts", {}).get("us-gaap", {})
    out: list[tuple] = []
    # quarters
    qends = [r["period_end"] for r in rows]
    q = {line: _sec_q(gaap, names, _unit_for(line)) for line, names in SEC_PL.items()
         if line in ("other_income", "interest", "depreciation", "tax")}
    for r in rows:
        e = r["period_end"]
        vals = {"sales": r["revenue"], "net_profit": r["net_income"], "eps": r["eps"], "pbt": r["pretax_income"],
                "operating_profit": r["operating_income"], **{k: v.get(e) for k, v in q.items()}}
        if vals["sales"] is not None and vals["operating_profit"] is not None:
            vals["expenses"] = vals["sales"] - vals["operating_profit"]
        out += [("Q", e, k, v) for k, v in _clean(vals).items()]
    # fiscal years
    fy = {line: _sec_fy(gaap, names, _unit_for(line), first=line in ("eps", "dividend_ps")) for line, names in {**SEC_PL, **SEC_CF}.items()}
    fy_ends = sorted({e for line in ("sales", "net_profit") for e in fy[line]})[-ANNUAL_YEARS_BACK:]
    for e in fy_ends:
        vals = {line: fy[line].get(e) for line in fy}
        if vals["sales"] is not None and vals["operating_profit"] is not None:
            vals["expenses"] = vals["sales"] - vals["operating_profit"]
        out += [("FY", e, k, v) for k, v in _clean(vals).items()]
    # balance sheets: each year end, and the latest quarter end if newer
    bs = {k: _sec_inst(gaap, names) for k, names in SEC_BS.items()}
    shares = _sec_inst(facts_json.get("facts", {}).get("dei", {}), ("EntityCommonStockSharesOutstanding",), ("shares",))
    dates = [e for e in fy_ends if e in bs["total_assets"]]
    latest = max(bs["total_assets"], default=None)
    if latest and qends and latest >= max(qends) - dt.timedelta(days=10) and latest not in dates:
        dates.append(latest)
    for e in dates:
        g = {k: v.get(e) for k, v in bs.items()}
        borrowings = _sum(g["lt_debt"] if g["lt_debt"] is not None else _sum(g["lt_debt_nc"], g["lt_debt_c"]), g["st_debt"], g["cp"])
        capital = g["capital"] if g["capital"] is not None else _sum(g["common"], g["apic"])
        total = g["total_assets"] if g["total_assets"] is not None else g["liabilities_and_equity"]
        inv = _sum(g["lt_inv"], g["st_inv"])
        sh = next((v for d, v in sorted(shares.items(), reverse=True) if d >= e - dt.timedelta(days=10) and d <= e + dt.timedelta(days=120)), None)
        vals = {
            "equity": g["equity"], "minority": g["minority"], "equity_capital": capital,
            "reserves": g["equity"] - capital if g["equity"] is not None and capital is not None else None,
            "borrowings": borrowings, "total_liabilities": total, "total_assets": total,
            "other_liabilities": total - _sum(g["equity"], g["minority"], borrowings) if total is not None and g["equity"] is not None else None,
            "fixed_assets": g["fixed_assets"], "investments": inv, "cash": g["cash"], "receivables": g["receivables"], "inventory": g["inventory"],
            "other_assets": total - (_sum(g["fixed_assets"], inv) or 0) if total is not None else None, "shares": sh,
        }
        out += [("BS", e, k, v) for k, v in _clean(vals).items()]
    return out, "us"


def fetch_sec(symbol: str) -> tuple[list[dict], dict]:
    cik = _sec_cik(symbol)
    if cik is None:
        return [], {"note": "not an SEC filer"}
    r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json", headers=_sec_headers(), timeout=60)
    time.sleep(SEC_PAUSE)
    if r.status_code == 404:
        return [], {"cik": cik, "note": "no XBRL facts"}
    r.raise_for_status()
    js = r.json()
    rows = parse_sec(js)
    lines, layout = sec_lines(js, rows) if rows else ([], None)
    return rows, {"cik": cik, "name": js.get("entityName"), "layout": layout, "lines": lines,
                  **({} if rows else {"note": "no quarterly 10-Q facts (a foreign filer on 20-F/40-F?)"})}


# ------------------------------------------------------------------ NSE (India)

NSE = "https://www.nseindia.com"
NSE_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
NSE_TAGS = {
    "revenue": ("RevenueFromOperations", "InterestEarned", "Income"),
    "net_income": ("ProfitOrLossAttributableToOwnersOfParent", "ProfitLossAfterTaxesMinorityInterestAndShareOfProfitLossOfAssociates",
                   "ProfitLossForPeriod", "ProfitLossForThePeriod"),
    "eps": ("DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations", "DilutedEarningsPerShareAfterExtraordinaryItems",
            "DilutedEarningsLossPerShareFromContinuingOperations", "DilutedEarningsPerShareBeforeExtraordinaryItems",
            "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations", "BasicEarningsPerShareAfterExtraordinaryItems"),
    "pretax_income": ("ProfitBeforeTax", "ProfitLossFromOrdinaryActivitiesBeforeTax"),
}


def _nse_eps(vals: dict) -> float | None:
    """One period's EPS: the first non-zero of NSE_TAGS["eps"] — except that some companies with no discontinued
    operations file their continuing EPS in the discontinued-operations tags too, so the "continuing and
    discontinued" total they file is twice the real one (Maruti, quarter and year to Mar-2024: 251.42 and 858.02
    for 125.71 and 429.01). When the discontinued EPS repeats the continuing one, the document's own discontinued
    profit is nil and the total is their sum, the continuing EPS is the answer."""
    eps = next((x for x in (_num(vals.get(t)) for t in NSE_TAGS["eps"]) if x), None)
    for kind in ("Diluted", "Basic"):
        cont = _num(vals.get(f"{kind}EarningsLossPerShareFromContinuingOperations"))
        disc = _num(vals.get(f"{kind}EarningsLossPerShareFromDiscontinuedOperations"))
        if cont and disc == cont and eps is not None and abs(eps - 2 * cont) <= 0.01 * abs(cont) \
                and not _num(vals.get("ProfitLossFromDiscontinuedOperationsAfterTax")):
            return cont
    return eps
NSE_EQUITY = ("EquityAttributableToOwnersOfParent", "Equity", "TotalEquity")
CONSOLIDATED_SHARE = 0.75     # consolidated when filed for at least this share of the recent quarters
NSE_PARSER_VERSION = 7        # bump when parse_nse_xbrl changes: stored documents are then parsed again


class _NseSession:
    def __init__(self):
        self.s = None

    def _warm(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": NSE_UA, "Accept-Language": "en-US,en;q=0.9", "Referer": NSE + "/"})
        try:   # sets the cookies the API checks; the page itself may answer 403
            self.s.get(NSE + "/companies-listing/corporate-filings-financial-results", timeout=20)
        except requests.RequestException:
            pass

    def get(self, url: str, **params):
        for attempt in range(3):
            if self.s is None:
                self._warm()
            try:
                r = self.s.get(url, params=params or None, timeout=30, headers={"Accept": "application/json, */*"})
            except requests.RequestException:
                r = None
            time.sleep(NSE_PAUSE)
            if r is not None and r.status_code == 200:
                return r
            self.s = None   # new session (fresh cookies) and retry
            time.sleep(1 + 2 * attempt)
        raise RuntimeError(f"NSE request failed: {url} {params} -> {getattr(r, 'status_code', 'no response')}")


_nse = _NseSession()


def _nse_date(s: str, fmt: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(str(s).strip().title(), fmt).date()
    except ValueError:
        return None


def nse_filings(sym: str) -> list[dict]:
    """Every quarterly results filing NSE lists for one company, both feeds: {end, start, basis, filed, url}."""
    out = []
    legacy = _nse.get(NSE + "/api/corporates-financial-results", index="equities", symbol=sym, period="Quarterly").json() or []
    for r in legacy:
        if str(r.get("cumulative", "")).lower().startswith("cumulative") or not str(r.get("xbrl", "")).endswith(".xml"):
            continue
        out.append({"end": _nse_date(r.get("toDate"), "%d-%b-%Y"), "start": _nse_date(r.get("fromDate"), "%d-%b-%Y"),
                    "basis": "consolidated" if r.get("consolidated") == "Consolidated" else "standalone",
                    "filed": _nse_date(str(r.get("filingDate", ""))[:11], "%d-%b-%Y"), "url": r["xbrl"]})
    page, seen = 1, 0
    while True:
        js = _nse.get(NSE + "/api/integrated-filing-results", index="equities", symbol=sym,
                      type="Integrated Filing- Financials", period_ended="all", page=page).json() or {}
        data = js.get("data") or []
        for r in data:
            if not str(r.get("xbrl", "")).endswith(".xml"):
                continue
            out.append({"end": _nse_date(r.get("qe_Date"), "%d-%b-%Y"), "start": None,
                        "basis": "consolidated" if r.get("consolidated") == "Consolidated" else "standalone",
                        "filed": _nse_date(str(r.get("broadcast_Date", ""))[:11], "%d-%b-%Y"), "url": r["xbrl"]})
        seen += len(data)
        if not data or seen >= int(js.get("totalCount") or 0) or page >= 10:
            break
        page += 1
    return [f for f in out if f["end"]]


def _nse_ts(s) -> dt.datetime | None:
    """An NSE broadcast time: '07-Aug-2026 18:43:09', or without seconds, or a bare date."""
    s = str(s or "").strip()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M", "%d-%b-%Y"):
        try:
            return dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def nse_announcements(sym: str) -> list[dict]:
    """Every quarterly results announcement NSE lists for one company, XBRL or not: {end, basis, at, source}.

    Unlike `nse_filings` this keeps the rows with no XBRL document -- every filing before about 2017 -- because
    only the broadcast time is wanted. A revised filing is a second row for the same quarter; the earliest is
    the announcement.
    """
    out = []
    legacy = _nse.get(NSE + "/api/corporates-financial-results", index="equities", symbol=sym, period="Quarterly").json() or []
    for r in legacy:
        if str(r.get("cumulative", "")).lower().startswith("cumulative"):
            continue
        end = _nse_date(r.get("toDate"), "%d-%b-%Y")
        at = _nse_ts(r.get("broadCastDate")) or _nse_ts(r.get("filingDate"))
        if end and at:
            out.append({"end": end, "at": at, "source": "nse_legacy",
                        "basis": "consolidated" if r.get("consolidated") == "Consolidated" else "standalone"})
    page, seen = 1, 0
    while True:
        js = _nse.get(NSE + "/api/integrated-filing-results", index="equities", symbol=sym,
                      type="Integrated Filing- Financials", period_ended="all", page=page).json() or {}
        data = js.get("data") or []
        for r in data:
            end, at = _nse_date(r.get("qe_Date"), "%d-%b-%Y"), _nse_ts(r.get("broadcast_Date"))
            if end and at:
                out.append({"end": end, "at": at, "source": "nse_integrated",
                            "basis": "consolidated" if r.get("consolidated") == "Consolidated" else "standalone"})
        seen += len(data)
        if not data or seen >= int(js.get("totalCount") or 0) or page >= 10:
            break
        page += 1
    return out


def refresh_announcements(market: str, symbols: list[str], progress=None) -> dict:
    """Fetch and store every results announcement for these companies (`results_announcements`).

    Only where the market's results source lists announcements (`MarketConfig.quarterly_source` 'nse').
    A company NSE does not know (an ETF, a delisted name) simply stores nothing.
    """
    if getattr(MARKETS[market], "quarterly_source", None) != "nse":
        return {"companies": 0, "skipped": f"{market}: its results source lists no announcement times"}
    init_schema()
    stored = companies_with = errors = 0
    for i, sym in enumerate(symbols):
        try:
            rows = nse_announcements(_bare(sym, market))
        except Exception as exc:   # noqa: BLE001 -- one company's failure must not stop the backfill
            errors += 1
            logger.warning("announcements %s: %s", sym, exc)
            rows = []
        if rows:
            db.execute_values("""INSERT INTO results_announcements (market, symbol, period_end, basis, announced_at, source)
                                 VALUES %s ON CONFLICT DO NOTHING""",
                              [(market, sym, r["end"], r["basis"], r["at"], r["source"]) for r in rows])
            stored += len(rows)
            companies_with += 1
        if progress:
            progress(i + 1, len(symbols))
    return {"companies": len(symbols), "with_announcements": companies_with, "announcements": stored, "errors": errors}


def announcements(market: str) -> dict:
    """{symbol: sorted announcement dates} -- when each company published each quarter's results.

    Point in time: inside a backtest stage only announcements on or before its boundary are returned.
    Empty for a market with no announcement source, so a caller falls back to whatever else it has.
    """
    sql, args = "SELECT symbol, announced_at FROM results_announcements WHERE market=%s", (market,)
    if asof.end_date():
        sql, args = sql + " AND announced_at::date <= %s", args + (asof.end_date(),)
    try:
        with db.get_connection().cursor() as cur:
            cur.execute(sql, args)
            rows = cur.fetchall()
    except Exception:   # noqa: BLE001 -- the table does not exist until the first refresh
        return {}
    out: dict = {}
    for sym, at in rows:
        out.setdefault(sym, set()).add(dt.date(at.year, at.month, at.day))
    return {sym: sorted(v) for sym, v in out.items()}


def choose_filings(filings: list[dict]) -> tuple[str | None, list[dict]]:
    """One basis for the whole company, then one filing per quarter (the latest, so a revision wins)."""
    ends = sorted({f["end"] for f in filings}, reverse=True)[:12]
    if not ends:
        return None, []
    cons = {f["end"] for f in filings if f["basis"] == "consolidated"}
    basis = "consolidated" if sum(e in cons for e in ends) >= CONSOLIDATED_SHARE * len(ends) else "standalone"
    best: dict = {}
    for f in filings:
        if f["basis"] == basis and (f["end"] not in best or (f["filed"] or dt.date.min) >= (best[f["end"]]["filed"] or dt.date.min)):
            best[f["end"]] = f
    return basis, [best[e] for e in sorted(best, reverse=True)[:LOOKBACK_QUARTERS]]


def _nse_get(v: dict):
    return lambda *names: next((_num(v[x]) for x in names if _num(v.get(x)) is not None), None)


def _nse_pl(v: dict, bank: bool) -> dict:
    """One period's P&L in the NSE layout -> LINES["pl"]. Operating profit is screener.in's: sales less
    operating expenses, before other income, interest and depreciation (banks: interest earned less
    interest expended and operating expenses and provisions)."""
    n = _nse_get(v)
    if bank:
        sales, interest = n("InterestEarned"), n("InterestExpended")
        opex, prov = n("OperatingExpenses"), n("ProvisionsOtherThanTaxAndContingencies")
        expenses = _sum(opex, prov) if opex is not None else None
        op = sales - interest - expenses if None not in (sales, interest, expenses) else None
        dep = None
    else:
        sales, total, interest = n("RevenueFromOperations"), n("Expenses"), n("FinanceCosts")
        dep = n("DepreciationDepletionAndAmortisationExpense")
        expenses = total - (interest or 0) - (dep or 0) if total is not None else None
        op = sales - expenses if sales is not None and expenses is not None else None
    eps = _nse_eps(v)
    return _clean({"sales": sales, "expenses": expenses, "operating_profit": op, "other_income": n("OtherIncome"),
                   "interest": interest, "depreciation": dep, "exceptional": n("ExceptionalItemsBeforeTax", "ExceptionalItems"),
                   "pbt": n("ProfitBeforeTax", "ProfitLossFromOrdinaryActivitiesBeforeTax"), "tax": n("TaxExpense"),
                   "net_profit": n(*NSE_TAGS["net_income"]), "eps": eps, "face_value": n("FaceValueOfEquityShareCapital")})


def _nse_bs(v: dict, bank: bool) -> dict:
    n = _nse_get(v)
    if bank:
        cap, res = n("Capital"), n("ReservesAndSurplus")
        total = n("CapitalAndLiabilities", "Assets")
        return _clean({"equity_capital": cap, "reserves": res, "equity": _sum(cap, res), "deposits": n("Deposits"),
                       "borrowings": n("Borrowings"), "other_liabilities": n("OtherLiabilitiesAndProvisions"), "total_liabilities": total,
                       "fixed_assets": n("FixedAssets"), "investments": n("Investments"), "advances": n("Advances"),
                       "cash": _sum(n("CashAndBalancesWithReserveBankOfIndia"), n("BalancesWithBanksAndMoneyAtCallAndShortNotice")),
                       "other_assets": n("OtherAssets"), "total_assets": n("Assets", "CapitalAndLiabilities")})
    total = n("EquityAndLiabilities", "Assets")
    equity_all = n("Equity")
    borrowings = _sum(n("BorrowingsNoncurrent"), n("BorrowingsCurrent"))
    fixed = _sum(n("PropertyPlantAndEquipment"), n("Goodwill"), n("OtherIntangibleAssets"), n("InvestmentProperty"))
    cwip = _sum(n("CapitalWorkInProgress"), n("IntangibleAssetsUnderDevelopment"))
    inv = _sum(n("NoncurrentInvestments"), n("CurrentInvestments"), n("InvestmentsAccountedForUsingEquityMethod"))
    return _clean({
        "equity_capital": n("EquityShareCapital"), "reserves": n("OtherEquity"),
        "equity": n("EquityAttributableToOwnersOfParent", "Equity"), "minority": n("NonControllingInterest"),
        "borrowings": borrowings,
        "other_liabilities": total - (equity_all or 0) - (borrowings or 0) if total is not None and equity_all is not None else None,
        "total_liabilities": total, "fixed_assets": fixed, "cwip": cwip, "investments": inv,
        "cash": _sum(n("CashAndCashEquivalents"), n("BankBalanceOtherThanCashAndCashEquivalents")),
        "receivables": _sum(n("TradeReceivablesCurrent"), n("TradeReceivablesNoncurrent")), "inventory": n("Inventories"),
        "other_assets": total - (fixed or 0) - (cwip or 0) - (inv or 0) if total is not None and fixed is not None else None,
        "total_assets": n("Assets", "EquityAndLiabilities")})


def _nse_cf(v: dict) -> dict:
    n = _nse_get(v)
    return _clean({"cfo": n("CashFlowsFromUsedInOperatingActivities"), "cfi": n("CashFlowsFromUsedInInvestingActivities"),
                   "cff": n("CashFlowsFromUsedInFinancingActivities"), "net_cash": n("IncreaseDecreaseInCashAndCashEquivalents"),
                   "capex": _sum(n("PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"),
                                 n("PurchaseOfTangibleAssetsClassifiedAsInvestingActivities"),
                                 n("PurchaseOfIntangibleAssetsClassifiedAsInvestingActivities")),
                   "dividends_paid": n("DividendsPaidClassifiedAsFinancingActivities")})


def parse_nse_xbrl(content: bytes) -> dict | None:
    """One NSE results document -> the quarter's figures ({period_start, period_end, revenue, ...}), or None."""
    from lxml import etree
    root = etree.fromstring(content, etree.XMLParser(resolve_entities=False, no_network=True, huge_tree=True))
    local = lambda el: etree.QName(el).localname  # noqa: E731
    ctxs = {}
    for c in root.iter("{*}context"):
        start = c.find(".//{*}startDate")
        end = c.find(".//{*}endDate")
        inst = c.find(".//{*}instant")
        dims = c.find(".//{*}segment") is not None or c.find(".//{*}scenario") is not None
        ctxs[c.get("id")] = (_d(start.text) if start is not None else None, _d(end.text) if end is not None else _d(inst.text) if inst is not None else None,
                             start is None, dims)
    # Each document also states its periods as facts, and those win: older NSE documents reference contexts
    # they never define, or define the full-year context with the quarter's dates.
    stated: dict = defaultdict(dict)
    for el in root.iter("{*}DateOfStartOfReportingPeriod", "{*}DateOfEndOfReportingPeriod"):
        stated[el.get("contextRef")][local(el)[6:11]] = _d(el.text)
    for cid, p in stated.items():
        if p.get("Start") and p.get("EndOf"):
            ctxs[cid] = (p["Start"], p["EndOf"], False, ctxs.get(cid, (0, 0, 0, False))[3])
        elif cid not in ctxs and cid == "OneD" and p.get("EndOf"):   # banking documents state only the end; OneD is the quarter
            ctxs[cid] = (p["EndOf"] - dt.timedelta(days=90), p["EndOf"], False, False)
        elif cid not in ctxs and cid == "FourD" and p.get("EndOf") and p["EndOf"].month == 3:
            # ... and FourD the year to date, which in a March document is the full year (Indian banks' year ends in March)
            ctxs[cid] = (p["EndOf"].replace(year=p["EndOf"].year - 1) + dt.timedelta(days=1), p["EndOf"], False, False)
    quarter = [(cid, s, e) for cid, (s, e, is_inst, dims) in ctxs.items()
               if not is_inst and not dims and s and e and _in((e - s).days, QUARTER_DAYS)]
    if not quarter:
        return None
    q_end = max(e for _, _, e in quarter)
    qids = {cid for cid, _, e in quarter if e == q_end}
    yids = {cid for cid, (s, e, is_inst, dims) in ctxs.items()      # the full year, in a Q4 document
            if not is_inst and not dims and s and e == q_end and _in((e - s).days, YEAR_DAYS)}
    iids = {cid for cid, (s, e, is_inst, dims) in ctxs.items() if is_inst and not dims and e == q_end}
    qv, iv, yv = {}, {}, {}
    for el in root.iter():
        if not isinstance(el.tag, str):
            continue
        ref = el.get("contextRef")
        if ref in qids:
            qv.setdefault(local(el), el.text)
        elif ref in iids:
            iv.setdefault(local(el), el.text)
        elif ref in yids:
            yv.setdefault(local(el), el.text)
    pick = lambda vals, names: next((_num(vals[n]) for n in names if _num(vals.get(n)) is not None), None)  # noqa: E731
    out = {"period_start": min(s for _, s, e in quarter if e == q_end), "period_end": q_end}
    for f, names in NSE_TAGS.items():
        out[f] = pick(qv, names)
    paid, face = _num(qv.get("PaidUpValueOfEquityShareCapital")), _num(qv.get("FaceValueOfEquityShareCapital"))
    out["shares"] = paid / face if paid and face else None
    # some documents carry 0 in the main EPS tag and the figure in another; failing all, net income / shares
    eps = _nse_eps(qv)
    if eps is None and out["net_income"] is not None and out["shares"]:
        eps = out["net_income"] / out["shares"]
    out["eps"] = eps if eps is not None else out["eps"]
    out["net_income_fy"] = pick(yv, NSE_TAGS["net_income"]) if yv else None
    out["eps_fy"] = _nse_eps(yv) if yv else None
    out["equity"] = pick(iv, NSE_EQUITY)
    bank = "InterestEarned" in qv and "RevenueFromOperations" not in qv
    out["layout"] = "bank" if bank else "industrial"
    bs = _nse_bs(iv, bank)
    if out["shares"]:
        bs["shares"] = out["shares"]
    fy = {**_nse_pl(yv, bank), **_nse_cf(yv)} if yv else {}
    if fy and out["shares"]:
        fy["shares"] = out["shares"]          # the year's share count, for putting its EPS on today's basis
    out["lines"] = {"Q": _nse_pl(qv, bank), "FY": fy,
                    "BS": bs if bs.get("total_assets") or bs.get("total_liabilities") else {}}
    return out


def _cache_get(url: str, kind: str, parser: int) -> dict | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT parsed FROM nse_documents WHERE url=%s AND kind=%s AND parser=%s", (url, kind, parser))
        r = cur.fetchone()
    return r[0] if r else None


def _cache_put(url: str, kind: str, parser: int, parsed: dict | None) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO nse_documents (url, kind, parser, parsed) VALUES (%s, %s, %s, %s)
                       ON CONFLICT (url) DO UPDATE SET kind=EXCLUDED.kind, parser=EXCLUDED.parser, parsed=EXCLUDED.parsed, fetched_at=now()""",
                    (url, kind, parser, json.dumps(parsed, default=str) if parsed is not None else None))


def _nse_doc(url: str, reparse: bool) -> dict | None:
    """One results document, parsed — from the cache unless `reparse` (or it was parsed by an older parser)."""
    if not reparse:
        hit = _cache_get(url, "results", NSE_PARSER_VERSION)
        if hit is not None:
            return {**hit, "period_start": _d(hit.get("period_start")), "period_end": _d(hit.get("period_end"))}
    try:
        parsed = parse_nse_xbrl(_nse.get(url).content)
    except Exception as exc:  # noqa: BLE001 — one unreadable document must not lose the company
        logger.debug("%s unreadable: %s", url, exc)
        parsed = None
    if parsed:
        _cache_put(url, "results", NSE_PARSER_VERSION, parsed)
    return parsed


def _bare(symbol: str, market: str = "india") -> str:
    sfx = MARKETS[market].symbol_suffix
    return symbol[: -len(sfx)] if sfx and symbol.endswith(sfx) else symbol


def fetch_nse(symbol: str, reparse: bool = False) -> tuple[list[dict], dict]:
    """Quarter rows and statement lines from NSE: the last LOOKBACK_QUARTERS quarters, plus the year-end
    (Q4) documents back to ANNUAL_YEARS_BACK years for the annual P&L, balance sheet and cash flow."""
    filings = nse_filings(_bare(symbol))
    basis, chosen = choose_filings(filings)
    if not chosen:
        return [], {"note": "no quarterly results filed on NSE"}
    parsed, failed = {}, 0
    for f in chosen:
        p = _nse_doc(f["url"], reparse)
        if p:
            parsed[f["url"]] = (f, p)
        else:
            failed += 1
    # the fiscal year ends where a document carries a full year; older year-end documents for the annual tables
    fy_month = next((p["period_end"].month for f, p in parsed.values() if p.get("lines", {}).get("FY")), 3)
    window = {f["end"] for f in chosen}
    older = sorted({f["end"] for f in filings if f["basis"] == basis and f["end"].month == fy_month and f["end"] not in window}, reverse=True)
    keep = ANNUAL_YEARS_BACK - sum(1 for e in window if e.month == fy_month)
    for end in older[:max(0, keep)]:
        f = max((x for x in filings if x["basis"] == basis and x["end"] == end), key=lambda x: x["filed"] or dt.date.min)
        p = _nse_doc(f["url"], reparse)
        if p:
            parsed[f["url"]] = (f, p)
    rows, lines, layout = [], [], None
    for f, p in sorted(parsed.values(), key=lambda fp: fp[1]["period_end"]):
        layout = p.get("layout") or layout
        if f["end"] in window:
            rows.append(_row(**{k: p.get(k) for k in ("period_start", "period_end", *FIELDS, "equity", "shares", "eps_fy", "net_income_fy")},
                             source="nse", basis=basis, filed=f["filed"], doc_url=f["url"]))
        for ptype, vals in (p.get("lines") or {}).items():
            if ptype == "Q" and f["end"] not in window:
                continue
            lines += [(ptype, p["period_end"], k, v) for k, v in vals.items()]
    rows = list({r["period_end"]: r for r in rows}.values())
    return rows, {"basis": basis, "layout": layout, "lines": lines, "parser": NSE_PARSER_VERSION,
                  **({"unreadable_documents": failed} if failed else {})}


# ------------------------------------------------------------------ shareholding (India)

SHP_PARSER_VERSION = 1
SHP_CONTEXTS = {"promoters": "ShareholdingOfPromoterAndPromoterGroup", "fii": "InstitutionsForeign",
                "dii": "InstitutionsDomestic", "government": "Governments", "public": "PublicShareholding"}


def parse_shp_xbrl(content: bytes) -> dict:
    """A shareholding-pattern document -> {promoters, fii, dii, government, public, shareholders} (fractions)."""
    import re
    t = content.decode("utf-8", errors="replace")
    out = {}
    for key, ctx in SHP_CONTEXTS.items():
        m = re.search(r'ShareholdingAsAPercentageOfTotalNumberOfShares\b[^>]*contextRef="%s_ContextI"[^>]*>([^<]+)<' % ctx, t)
        out[key] = _num(m.group(1)) if m else None
    m = re.search(r'NumberOfShareholders\b[^>]*contextRef="ShareholdingPattern_ContextI"[^>]*>([^<]+)<', t)
    out["shareholders"] = int(float(m.group(1))) if m and _num(m.group(1)) is not None else None
    return out


def fetch_shareholding(symbol: str, known: set, reparse: bool = False) -> list[dict]:
    """Every quarter NSE lists (promoter / public share from the list itself), with the FII / DII split read
    from the detailed filing for the latest SHP_DETAIL_QUARTERS quarters and any quarter not stored before
    (`known`: the quarters already stored). Parsed filings are cached, so a quarter is downloaded once."""
    master = _nse.get(NSE + "/api/corporate-share-holdings-master", index="equities", symbol=_bare(symbol)).json() or []
    rows = {}
    for r in master:
        end = _nse_date(r.get("date"), "%d-%b-%Y")
        if not end:
            continue
        pr, pub = _num(r.get("pr_and_prgrp")), _num(r.get("public_val"))
        rows[end] = {"period_end": end, "promoters": pr / 100 if pr is not None else None, "public": pub / 100 if pub is not None else None,
                     "url": r.get("xbrl") if str(r.get("xbrl", "")).endswith(".xml") else None}
    recent = sorted(rows, reverse=True)
    for i, end in enumerate(recent):
        r = rows[end]
        if not r["url"] or not (i < SHP_DETAIL_QUARTERS or (known and end not in known)):
            continue                                  # the latest few, and any quarter new since the last fetch
        hit = None if reparse else _cache_get(r["url"], "shp", SHP_PARSER_VERSION)
        if hit is None:
            try:
                hit = parse_shp_xbrl(_nse.get(r["url"]).content)
            except Exception as exc:  # noqa: BLE001
                logger.debug("%s shareholding unreadable: %s", symbol, exc)
                continue
            _cache_put(r["url"], "shp", SHP_PARSER_VERSION, hit)
        r.update({k: v for k, v in hit.items() if v is not None})
    return [{k: v for k, v in r.items() if k != "url"} for r in rows.values()]


# ------------------------------------------------------------------ profile (Yahoo)

def fetch_profile(symbol: str) -> dict:
    """Description, website, dividend yield and holders — what the filings do not say. {} when Yahoo has none."""
    import yfinance as yf
    t = yf.Ticker(symbol)
    try:
        info = t.info or {}
    except Exception:  # noqa: BLE001
        info = {}
    finally:
        time.sleep(YF_PAUSE)
    keep = ("longName", "sector", "industry", "website", "fullTimeEmployees", "currency", "financialCurrency",
            "trailingAnnualDividendYield", "dividendYield", "bookValue", "sharesOutstanding", "marketCap",
            "heldPercentInsiders", "heldPercentInstitutions")
    out = {k: info.get(k) for k in keep if info.get(k) is not None}
    if info.get("longBusinessSummary"):
        out["about"] = str(info["longBusinessSummary"])[:2000]
    return out


# ------------------------------------------------------------------ yfinance (fallback) + surprises

YF_ROWS = {"revenue": ("Total Revenue", "Operating Revenue"), "net_income": ("Net Income Common Stockholders", "Net Income"),
           "eps": ("Diluted EPS", "Basic EPS"), "gross_profit": ("Gross Profit",), "operating_income": ("Operating Income",),
           "pretax_income": ("Pretax Income",)}


def fetch_yf(symbol: str) -> tuple[list[dict], dict]:
    import yfinance as yf
    t = yf.Ticker(symbol)
    inc = t.quarterly_income_stmt
    time.sleep(YF_PAUSE)
    if inc is None or inc.empty:
        return [], {"note": "no quarterly statements on Yahoo"}
    bal = t.quarterly_balance_sheet
    rows = []
    for col in sorted(inc.columns):
        def val(names, frame=inc, c=col):
            for n in names:
                if frame is not None and n in frame.index:
                    v = _num(frame.at[n, c]) if c in frame.columns else None
                    if v is not None:
                        return v
            return None
        r = _row(period_end=col.date(), source="yfinance", basis="as reported",
                 equity=val(("Stockholders Equity", "Common Stock Equity"), bal), shares=val(("Diluted Average Shares",)))
        for f, names in YF_ROWS.items():
            r[f] = val(names)
        if r["revenue"] is not None or r["eps"] is not None:
            rows.append(r)
    return rows, {"layout": "us" if not symbol.endswith(MARKETS["india"].symbol_suffix) else "industrial", "lines": yf_lines(t, rows)}


YF_PL = {"sales": ("Total Revenue", "Operating Revenue"), "operating_profit": ("Operating Income",), "interest": ("Interest Expense",),
         "depreciation": ("Reconciled Depreciation",), "pbt": ("Pretax Income",), "tax": ("Tax Provision",),
         "net_profit": ("Net Income Common Stockholders", "Net Income"), "eps": ("Diluted EPS", "Basic EPS"),
         "other_income": ("Other Non Operating Income Expenses",)}
YF_BS = {"equity": ("Stockholders Equity", "Common Stock Equity"), "minority": ("Minority Interest",), "borrowings": ("Total Debt",),
         "total_assets": ("Total Assets",), "fixed_assets": ("Net PPE",), "investments": ("Investments And Advances",),
         "cash": ("Cash And Cash Equivalents",), "receivables": ("Accounts Receivable",), "inventory": ("Inventory",),
         "equity_capital": ("Capital Stock",), "shares": ("Ordinary Shares Number", "Share Issued")}
YF_CF = {"cfo": ("Operating Cash Flow",), "cfi": ("Investing Cash Flow",), "cff": ("Financing Cash Flow",), "net_cash": ("Changes In Cash",),
         "capex": ("Capital Expenditure",), "dividends_paid": ("Cash Dividends Paid", "Common Stock Dividend Paid")}


def yf_lines(t, rows: list[dict]) -> list[tuple]:
    """Yahoo's statements -> lines: the quarters already read, and its ~4 years of annual statements."""
    def frame_lines(frame, mapping, ptype, sign=None):
        out = []
        if frame is None or getattr(frame, "empty", True):
            return out
        for col in frame.columns:
            for line, names in mapping.items():
                v = next((_num(frame.at[n, col]) for n in names if n in frame.index and _num(frame.at[n, col]) is not None), None)
                if v is not None:
                    out.append((ptype, col.date(), line, abs(v) if line in (sign or ()) else v))
        return out
    lines = []
    for r in rows:
        vals = {"sales": r["revenue"], "net_profit": r["net_income"], "eps": r["eps"], "pbt": r["pretax_income"], "operating_profit": r["operating_income"]}
        if vals["sales"] is not None and vals["operating_profit"] is not None:
            vals["expenses"] = vals["sales"] - vals["operating_profit"]
        lines += [("Q", r["period_end"], k, v) for k, v in _clean(vals).items()]
    try:
        lines += frame_lines(t.income_stmt, YF_PL, "FY") + frame_lines(t.cashflow, YF_CF, "FY", sign=("capex", "dividends_paid"))
        lines += frame_lines(t.balance_sheet, YF_BS, "BS")
    except Exception as exc:  # noqa: BLE001 — the annual statements are a bonus on top of the quarters
        logger.debug("yfinance annual statements: %s", exc)
    fy = defaultdict(dict)
    for ptype, e, line, v in lines:
        if ptype == "FY":
            fy[e][line] = v
    for e, d in fy.items():
        if d.get("sales") is not None and d.get("operating_profit") is not None:
            lines.append(("FY", e, "expenses", d["sales"] - d["operating_profit"]))
    return lines


def fetch_surprises(symbol: str) -> list[dict]:
    """yfinance earnings history: EPS actual vs consensus, ~4 quarters ([] when Yahoo has none)."""
    import yfinance as yf
    try:
        h = yf.Ticker(symbol).get_earnings_history()
    except Exception:  # noqa: BLE001
        return []
    finally:
        time.sleep(YF_PAUSE)
    if h is None or getattr(h, "empty", True):
        return []
    out = []
    for q, r in h.iterrows():
        a, e = _num(r.get("epsActual")), _num(r.get("epsEstimate"))
        if a is not None and e is not None:
            out.append({"quarter": str(q)[:10], "actual": a, "estimate": e, "surprise": _num(r.get("surprisePercent"))})
    return out


# ------------------------------------------------------------------ storage + batch

def _state(market: str) -> dict:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, fetched_at, status, latest_end FROM quarterly_fetch WHERE market=%s", (market,))
        return {s: (f, st, le) for s, f, st, le in cur.fetchall()}


def due(state: tuple | None, today: dt.date | None = None) -> bool:
    """Whether a company should be fetched now (see the module docstring)."""
    if state is None:
        return True
    fetched, status, latest = state
    today = today or dt.date.today()
    age = (today - fetched.date()).days
    if status == "none":
        return age >= NOT_FOUND_RETRY_DAYS
    if status == "error":
        return age >= 1
    if age >= MAX_AGE_DAYS:
        return True
    return bool(latest and today >= latest + dt.timedelta(days=91 + RESULTS_GRACE_DAYS) and age >= RECHECK_DAYS)


def no_data(market: str) -> set:
    """Symbols the sources had nothing for at the last look (funds, ETFs, ...)."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM quarterly_fetch WHERE market=%s AND status='none'", (market,))
        return {r[0] for r in cur.fetchall()}


def _store(market: str, symbol: str, rows: list[dict], status: str, source: str | None, meta: dict,
           error: str | None = None, shp: list[dict] | None = None) -> None:
    lines = meta.pop("lines", None) or []
    with db.get_connection().cursor() as cur:
        if status != "error":   # a failed fetch keeps what was stored before
            cur.execute("DELETE FROM quarterly_results WHERE market=%s AND symbol=%s", (market, symbol))
            cur.execute("DELETE FROM financial_lines WHERE market=%s AND symbol=%s", (market, symbol))
        cur.execute("""INSERT INTO quarterly_fetch (market, symbol, fetched_at, source, status, quarters, latest_end, error, meta)
                       VALUES (%s, %s, now(), %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (market, symbol) DO UPDATE SET fetched_at=now(), source=COALESCE(EXCLUDED.source, quarterly_fetch.source),
                       status=EXCLUDED.status, quarters=COALESCE(EXCLUDED.quarters, quarterly_fetch.quarters),
                       latest_end=COALESCE(EXCLUDED.latest_end, quarterly_fetch.latest_end), error=EXCLUDED.error,
                       meta=COALESCE(EXCLUDED.meta, quarterly_fetch.meta)""",
                    (market, symbol, source, status, len(rows) if status != "error" else None,
                     max((r["period_end"] for r in rows), default=None), error, json.dumps(meta, default=str) if status != "error" else None))
        if shp:
            cur.execute("DELETE FROM shareholding WHERE market=%s AND symbol=%s", (market, symbol))
    if rows and status != "error":
        db.execute_values(f"INSERT INTO quarterly_results (market, symbol, {', '.join(COLUMNS)}) VALUES %s",
                          [(market, symbol, *[r[c] for c in COLUMNS]) for r in rows])
        uniq = {(pt, e, line): v for pt, e, line, v in lines if v is not None}
        db.execute_values("INSERT INTO financial_lines (market, symbol, period_type, period_end, line, value, source) VALUES %s",
                          [(market, symbol, pt, e, line, v, source) for (pt, e, line), v in uniq.items()])
    if shp:
        db.execute_values("""INSERT INTO shareholding (market, symbol, period_end, promoters, fii, dii, government, public, shareholders)
                             VALUES %s""", [(market, symbol, r["period_end"], r.get("promoters"), r.get("fii"), r.get("dii"),
                                             r.get("government"), r.get("public"), r.get("shareholders")) for r in shp])


def _shp_known(market: str, symbol: str) -> set:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT period_end FROM shareholding WHERE market=%s AND symbol=%s", (market, symbol))
        return {r[0] for r in cur.fetchall()}


def fetch_one(market: str, symbol: str, reparse: bool = False) -> tuple[str, int]:
    """Fetch and store one company: statements, profile, earnings surprises, shareholding. Returns (status, quarters)."""
    source = MARKETS[market].quarterly_source
    try:
        rows, meta = ([], {})
        if source == "sec_edgar":
            rows, meta = fetch_sec(symbol)
        elif source == "nse":
            rows, meta = fetch_nse(symbol, reparse)
        used = source if rows else None
        if not rows:
            yrows, ymeta = fetch_yf(symbol)
            if yrows:
                rows, used = yrows, "yfinance"
                meta = {**meta, **ymeta, "fallback_reason": meta.get("note")}
        shp = None
        if rows:
            meta["surprises"] = fetch_surprises(symbol)
            meta["profile"] = fetch_profile(symbol)
            if source == "nse":
                try:
                    shp = fetch_shareholding(symbol, _shp_known(market, symbol), reparse)
                except Exception as exc:  # noqa: BLE001 — the statements still count
                    logger.warning("%s %s shareholding: %s", market, symbol, exc)
        status = "ok" if rows else "none"
        _store(market, symbol, rows, status, used, meta, shp=shp)
        return status, len(rows)
    except Exception as exc:  # noqa: BLE001 — one bad company must not stop the batch
        _store(market, symbol, [], "error", None, {}, f"{type(exc).__name__}: {exc}"[:500])
        logger.warning("%s %s: %s", market, symbol, exc)
        return "error", 0


def run(market: str, symbols: list[str], force: bool = False) -> dict:
    init_schema()
    state = _state(market)
    todo = [s for s in symbols if force or due(state.get(s))]
    stats = {"fetched": 0, "no_data": 0, "failed": 0, "fresh": len(symbols) - len(todo)}
    for i, sym in enumerate(todo, 1):
        status, n = fetch_one(market, sym)   # documents come from the cache, keyed by parser version
        stats[{"ok": "fetched", "none": "no_data", "error": "failed"}[status]] += 1
        logger.info("[%d/%d] %s %s %s, %d quarters", i, len(todo), market, sym, status, n)
    return stats


# Some companies' own XBRL tags EPS with the wrong scale: Halliburton filed its Q2 2021 diluted EPS as 260000
# for $0.26, and EDGAR publishes it as filed. A per-share figure off by a factor of 1,000 or 1,000,000 is
# caught against the EPS the same period's net income and share count imply, and divided back — but only when
# the figure is also far out of line with the company's own EPS in its other periods and the corrected one fits
# them: NSE rows with a mis-scaled share count or a wrong net income must not have their (correct) EPS
# "fixed". Stored rows keep what the filing says; `load` and `load_lines` correct it on the way out, so no
# re-download is needed.
EPS_SCALE_FACTORS = (1e6, 1e3)          # the scale slips seen in filings (thousands, millions)
EPS_SCALE_TOL = 3.0                     # EPS / implied EPS within ×/÷ this of 1,000 counts as the thousands slip
EPS_SCALE_MILLION_MIN = 1e4             # ... and anything past this as the millions slip: a split between the EPS's
                                        # share basis and the stored count moves the ratio by up to 50, never 10,000
EPS_SCALE_MIN_SHARES = 1e6              # without a share count: fewer implied shares than this is not a listed company
EPS_SCALE_MIN_ABS = 1000.0              # ... and only an EPS this large is checked that way
EPS_SCALE_OUTLIER = 30.0                # a slip is this many times the company's median |EPS|; the corrected one within it
EPS_IMPOSSIBLE_SHARES = 1000            # an outlier EPS that implies fewer shares than this is not an EPS at all (some
                                        # filings put the share count in the EPS concept): it is dropped, not rescaled


def eps_scale(eps, net_income, shares=None) -> float:
    """The factor a per-share figure was mis-scaled by (1 when it looks right): EPS against net income ÷
    shares when the share count is known, else against the share count it implies."""
    if not eps or not net_income:
        return 1.0
    if shares and shares > 0:
        ratio = abs(eps) / abs(net_income / shares)
        if ratio >= EPS_SCALE_MILLION_MIN:
            return 1e6
        return 1e3 if 1e3 / EPS_SCALE_TOL <= ratio <= 1e3 * EPS_SCALE_TOL else 1.0
    if abs(eps) >= EPS_SCALE_MIN_ABS:
        implied = abs(net_income / eps)
        if implied < EPS_SCALE_MIN_SHARES / EPS_SCALE_FACTORS[-1]:
            return next((k for k in sorted(EPS_SCALE_FACTORS) if implied * k >= EPS_SCALE_MIN_SHARES), 1.0)
    return 1.0


def _median_abs(vals) -> float | None:
    v = sorted(abs(x) for x in vals if x)
    return v[len(v) // 2] if v else None


def _rescaled(v, net_income, shares, typical: float | None):
    """v divided back by its scale slip — only when it is an outlier against `typical` (the company's median
    |EPS|) and the corrected value is not."""
    if not typical or abs(v) < EPS_SCALE_OUTLIER * typical:
        return v
    k = eps_scale(v, net_income, shares)
    if k != 1 and abs(v) / k <= EPS_SCALE_OUTLIER * typical:
        return v / k
    if net_income and abs(net_income / v) < EPS_IMPOSSIBLE_SHARES:
        return None
    return v


def _fix_eps_scale(rows: list[dict]) -> list[dict]:
    """One company's quarters, with EPS scale slips divided back (see `eps_scale`)."""
    typical = _median_abs(r.get("eps") for r in rows)
    typical_fy = _median_abs(r.get("eps_fy") for r in rows)
    for r in rows:
        for e, n, t in (("eps", "net_income", typical), ("eps_prior", "net_income_prior", typical), ("eps_fy", "net_income_fy", typical_fy)):
            if r.get(e) is not None:
                r[e] = _rescaled(r[e], r.get(n), r.get("shares"), t)
    return rows


# NSE filings carry their own slips, which the parser reads faithfully: a quarter whose every amount was entered in
# lakh (IRCON Mar-2022, LIC Housing Dec-2021, PFC Dec-2023: revenue, profit and paid-up capital all 100x too small,
# EPS right), a share count that is not one (Kaynes: trillions), and a net income taken from the wrong line (Maruti
# Sep-2022, Zydus Mar-2024, Solar Industries Sep-2024: far from the company's usual profit and from its own EPS x
# shares, EPS normal). Many more quarters carry a net income of exactly 0 beside a real EPS: the filing had no
# figure, and 0 would read as a zero profit margin. Each is judged against the company's other quarters and
# corrected on the way out: the unit slip scaled back (amounts and share count alike), the impossible share count,
# the zero and the stray net income left blank rather than guessed. The reference share count is the one net income
# / EPS implies (median over the quarters that have both), since the stored counts are what goes wrong.
# Stored rows keep what the filing says.
NSE_UNIT_SLIP_MIN = 30.0      # revenue and share count both this many times below the company's median: a unit slip ...
NSE_UNIT_SLIP_TOL = 0.5       # ... the two off by the same power of ten (log10 within this), the factor a power of ten (±0.15)
NSE_SHARES_OUTLIER = 30.0     # a share count this far from the median (no split or bonus is that big) is not a count
NSE_PROFIT_OUTLIER = 5.0      # net income this far from the company's median |net income| ...
NSE_PROFIT_VS_EPS = 3.0       # ... and this far from its own EPS x shares, with EPS itself normal, is from the wrong line
NSE_EPS_NORMAL = 5.0          # "EPS normal": within this of the company's median |EPS|
NSE_PER_SHARE = ("eps", "eps_prior", "eps_fy", "face_value", "dividend_ps")
NSE_AMOUNTS = ("revenue", "revenue_prior", "net_income", "net_income_prior", "gross_profit", "gross_profit_prior",
               "operating_income", "operating_income_prior", "pretax_income", "pretax_income_prior", "equity", "net_income_fy")


def _log10(x) -> float:
    import math
    return math.log10(x)


def nse_slips(rows: list[dict]) -> dict:
    """One company's NSE quarters -> {period_end: {"scale": k} | {"shares": None} | {"net_income": None}, ...}:
    the corrections `_fix_nse` applies (see the note above)."""
    nse = [r for r in rows if r.get("source") == "nse"]
    med = lambda k: _median_abs(r.get(k) for r in nse)  # noqa: E731
    m_rev, m_ni, m_eps = med("revenue"), med("net_income"), med("eps")
    m_sh = _median_abs(r["net_income"] / r["eps"] for r in nse if r.get("net_income") and r.get("eps")) or med("shares")
    out: dict = {}
    for r in nse:
        fix: dict = {}
        rev, sh, ni, eps = r.get("revenue"), r.get("shares"), r.get("net_income"), r.get("eps")
        eps_normal = eps is not None and m_eps and abs(eps) <= NSE_EPS_NORMAL * m_eps and abs(eps) >= m_eps / NSE_EPS_NORMAL
        if rev and sh and m_rev and m_sh and rev > 0 and sh > 0 and m_sh / sh >= NSE_UNIT_SLIP_MIN and m_rev / rev >= NSE_UNIT_SLIP_MIN:
            ls, lr = _log10(m_sh / sh), _log10(m_rev / rev)
            if abs(ls - lr) <= NSE_UNIT_SLIP_TOL and abs(ls - round(ls)) <= 0.15 and eps_normal:
                fix["scale"] = 10.0 ** round(ls)
        k = fix.get("scale", 1.0)
        if "scale" not in fix and sh and m_sh and (sh / m_sh >= NSE_SHARES_OUTLIER or m_sh / sh >= NSE_SHARES_OUTLIER):
            fix["shares"] = None
        shares_ok = None if "shares" in fix else (sh * k if sh else None)
        if ni == 0 and eps:
            fix["net_income"] = None
        elif ni is not None and m_ni and eps_normal and (shares_ok or m_sh):
            ni_k, ref = ni * k, eps * (shares_ok or m_sh)
            far_from_usual = abs(ni_k) >= NSE_PROFIT_OUTLIER * m_ni or abs(ni_k) <= m_ni / NSE_PROFIT_OUTLIER
            far_from_eps = ref and (ni_k == 0 or (ni_k / ref) <= 0 or max(ni_k / ref, ref / ni_k) >= NSE_PROFIT_VS_EPS)
            if far_from_usual and far_from_eps:
                fix["net_income"] = None
        if fix:
            out[r["period_end"]] = fix
    return out


def _fix_nse(rows: list[dict]) -> list[dict]:
    slips = nse_slips(rows)
    for r in rows:
        fix = slips.get(r["period_end"]) if r.get("source") == "nse" else None
        if not fix:
            continue
        k = fix.get("scale")
        if k:
            for f in NSE_AMOUNTS:
                if r.get(f) is not None:
                    r[f] = r[f] * k
            if r.get("shares"):
                r["shares"] = r["shares"] * k
        for f in ("shares", "net_income"):
            if f in fix:
                r[f] = None
    return rows


def load(market: str, symbols: list[str] | None = None) -> dict[str, list[dict]]:
    """Stored quarters per symbol, oldest first (EPS scale slips corrected: `eps_scale`)."""
    sql = f"SELECT symbol, {', '.join(COLUMNS)} FROM quarterly_results WHERE market=%s"
    args: tuple = (market,)
    if symbols is not None:
        sql, args = sql + " AND symbol = ANY(%s)", (market, list(symbols))
    if asof.end_date():
        # a backtest stage's boundary: a quarter exists from the day it was FILED, so a period
        # that ended inside the window but was filed after it is not yet known
        sql, args = (sql + " AND COALESCE(filed, period_end) <= %s", args + (asof.end_date(),))
    out: dict = defaultdict(list)
    with db.get_connection().cursor() as cur:
        cur.execute(sql + " ORDER BY symbol, period_end", args)
        for r in cur.fetchall():
            out[r[0]].append(dict(zip(COLUMNS, r[1:])))
    return {sym: _fix_eps_scale(_fix_nse(rows)) for sym, rows in out.items()}


def _nse_slips_raw(market: str, symbol: str) -> dict:
    """`nse_slips` over the company's stored quarters as filed (before any correction)."""
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {', '.join(COLUMNS)} FROM quarterly_results WHERE market=%s AND symbol=%s ORDER BY period_end", (market, symbol))
        return nse_slips([dict(zip(COLUMNS, r)) for r in cur.fetchall()])


def load_lines(market: str, symbol: str) -> dict:
    """{period_type: {period_end: {line: value}}} for one company (EPS scale slips corrected: `eps_scale`,
    against the quarter's stored share count where there is one).

    Inside a backtest stage's boundary (`asof`) a period is known only LINES_FILING_LAG_DAYS after it
    ended: the lines carry no filing date, so a year that closed inside the window but was reported
    after it is left out."""
    out: dict = defaultdict(lambda: defaultdict(dict))
    sql, args = "SELECT period_type, period_end, line, value FROM financial_lines WHERE market=%s AND symbol=%s", (market, symbol)
    if asof.end_date():
        sql, args = sql + " AND period_end <= %s", args + (asof.end_date() - dt.timedelta(days=LINES_FILING_LAG_DAYS),)
    with db.get_connection().cursor() as cur:
        cur.execute(sql, args)
        for pt, e, line, v in cur.fetchall():
            out[pt][e][line] = v
        cur.execute("SELECT period_end, shares FROM quarterly_results WHERE market=%s AND symbol=%s", (market, symbol))
        shares = dict(cur.fetchall())
    slips = _nse_slips_raw(market, symbol)
    for pt, periods in out.items():
        for e, lines in periods.items():
            fix = slips.get(e)
            if not fix:
                continue
            if fix.get("scale"):          # the whole filing was in lakh: its quarter, its full year and its balance sheet
                for line in list(lines):
                    if line not in NSE_PER_SHARE and lines[line] is not None:
                        lines[line] = lines[line] * fix["scale"]
            if pt == "Q" and "net_income" in fix:
                lines["net_profit"] = None
    for periods in out.values():
        typical = _median_abs(lines.get("eps") for lines in periods.values())
        for e, lines in periods.items():
            if lines.get("eps") is not None:
                lines["eps"] = _rescaled(lines["eps"], lines.get("net_profit"), shares.get(e), typical)
    return {pt: dict(v) for pt, v in out.items()}


def load_shareholding(market: str, symbol: str) -> list[dict]:
    cols = ("period_end", "promoters", "fii", "dii", "government", "public", "shareholders")
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {', '.join(cols)} FROM shareholding WHERE market=%s AND symbol=%s ORDER BY period_end", (market, symbol))
        return [dict(zip(cols, r)) for r in cur.fetchall()]


def statement_currency(market: str, meta: dict | None) -> str | None:
    """The currency a company's stored statements are in, when it is not its share price's — else None.
    SEC and NSE filings are in the market's own currency; Yahoo's statements are in the company's reporting
    currency (TSMC in TWD, Novo in DKK, ICICI in INR) while its US listing trades in dollars. Such figures
    cannot be set against the price (P/E, book value, dividend yield) without exchange rates, so the app
    does not value them — the rule the Quality screen already applies (fundamentals/quality.py)."""
    meta = meta or {}
    if meta.get("source") != "yfinance":
        return None
    p = meta.get("profile") or {}
    fin, price = p.get("financialCurrency"), p.get("currency") or MARKETS[market].currency_code
    return fin if fin and price and fin != price else None


def load_meta(market: str) -> dict[str, dict]:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, source, status, fetched_at, meta, error FROM quarterly_fetch WHERE market=%s", (market,))
        return {s: {"source": src, "status": st, "fetched_at": f, "error": e, **(m or {})} for s, src, st, f, m, e in cur.fetchall()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--symbols", required=True, help="comma separated (the scheduled job picks its own list)")
    ap.add_argument("--force", action="store_true", help="fetch even when stored results are fresh (parsed documents still come from the cache)")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(run(a.market, [s.strip().upper() for s in a.symbols.split(",") if s.strip()], a.force))


if __name__ == "__main__":
    main()
