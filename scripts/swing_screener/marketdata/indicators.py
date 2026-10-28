"""Growth, inflation, consumption, housing and credit indicators — the macro numbers behind the
business cycle, as opposed to the policy rates and market-priced series already covered by
`rates.py` and `macro.py`.

Stored in `index_series` (one row per series per date, the source's native daily/weekly/monthly/
quarterly cadence — no resampling) under the market each one describes. Each indicator names its
`source`:

    fred       FRED's free, key-less CSV endpoint (`rates.fred()`, the helper `rates.py` uses):
               us     CPI (CPIAUCSL), real GDP (GDPC1), industrial production (INDPRO), retail
                      sales (RSAFS, and its staples/discretionary split RSDBS/RSGMS), light-vehicle
                      sales (TOTALSA), durable goods orders (DGORDER), housing starts and permits
                      (HOUST, PERMIT), the 30-year mortgage rate (MORTGAGE30US), bank credit (TOTLL)
                      and the Baa corporate credit spread (BAA10Y)
               india  real GDP growth (INDGDPRQPSMEI) and real private consumption growth
                      (NAEXKP02INQ659S) — both already YoY rates
    mospi_iip  MoSPI's own IIP API (api.mospi.gov.in, JSON, no key): the general index and the
               use-based consumer durables / non-durables groups, as MoSPI's published YoY growth.
               Replaces FRED's OECD mirror of the IIP, which stopped at Jan-2023.
    mospi_cpi  MoSPI's CPI API: all-India combined headline inflation (YoY %), as MoSPI publishes it —
               the 2012-base series (getCPIIndex, Jan-2011 to Dec-2025, one call with state_code=99,
               sector_code=3, group_code=0) and the 2024-base series (getCPIData, from Jan-2026, one
               call per month by year and month_code). Joined on the published rate, so the two bases
               need no splicing; the newer base wins where both have a month. Replaces FRED's OECD
               mirror (INDCPIALLMINMEI), which stopped at Mar-2025; its old index levels stay stored
               under IN_CPI.
    vahan      the Vahan dashboard's all-India new vehicle registrations per month — an
               undocumented JSON endpoint that answers a plain GET; a failed day is skipped.

Still missing for India, because no free machine-readable release exists (PDF or press release
only, behind bot protection, or paywalled): segment-wise vehicle sales (SIAM/FADA), retail sales,
GST collections, consumer confidence (RBI, behind a session gateway), unemployment (PLFS/CMIE),
housing and bank-credit series. `summary()` reports a series it has no data for as absent rather
than guessing at a number.

A mirror can lag the original release (FRED's OECD copy of India CPI stops at Mar-2025);
`summary()` always reports the as-of date of the last stored point so staleness is visible rather
than hidden behind a number.

    PYTHONPATH=. python3 -m swing_screener.marketdata.indicators            # refresh both markets
    PYTHONPATH=. python3 -m swing_screener.marketdata.indicators --list     # what is stored
"""

import argparse
import datetime as dt
import logging
import re
import ssl
from dataclasses import dataclass

import pandas as pd

from . import db
from .rates import fred

logger = logging.getLogger(__name__)

TIMEOUT = 60
MOSPI_IIP = "https://api.mospi.gov.in/api/iip/getIIPData"
MOSPI_BASES = ("2011-12", "2022-23")   # oldest first: a later base's growth rate wins where both have a month
MOSPI_CPI_OLD = "https://api.mospi.gov.in/api/cpi/getCPIIndex"     # 2012 base, to Dec-2025
MOSPI_CPI_NEW = "https://api.mospi.gov.in/api/cpi/getCPIData"      # 2024 base, from Jan-2026
MOSPI_CPI_NEW_FROM = dt.date(2026, 1, 1)
VAHAN = ("https://analytics.parivahan.gov.in/analytics/publicdashboard/vahandashboard/"
         "durationWiseRegistrationTable")
VAHAN_FROM = 2019   # the dashboard reaches back decades, but states joined Vahan over time; earlier is noise
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                            "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"}


@dataclass(frozen=True)
class Indicator:
    key: str          # series name in index_series
    label: str
    short: str        # the card's tile label
    category: str     # "inflation" | "growth" | "consumption" | "housing" | "credit"
    unit: str         # unit of the stored level (not the derived YoY%, which is always "%")
    freq: str         # "daily" | "weekly" | "monthly" | "quarterly" — periods/year, for the YoY calc
    yoy: bool         # derive and report YoY% from the stored level; False when the stored value is
                      # already a rate, a spread or a growth rate, read as it is
    source_id: str    # FRED series id; MoSPI IIP category ("General", "Consumer Durables", ...); unused for vahan
    why: str          # what it tells a trader, for the app
    source: str = "fred"   # "fred" | "mospi_iip" | "mospi_cpi" | "vahan" — see the module docstring
    growth: bool = False   # the stored value already IS a year-on-year growth rate (yoy is then False)


INDICATORS: dict[str, list[Indicator]] = {
    "us": [
        Indicator("US_CPI", "US CPI, all items", "US CPI", "inflation", "index (1982-84=100)", "monthly", True,
                  "CPIAUCSL", "Headline inflation the Fed targets policy against; faster CPI growth pressures rate cuts away."),
        Indicator("US_GDP", "US real GDP", "US real GDP", "growth", "index ($bn, chained)", "quarterly", True,
                  "GDPC1", "The scorecard for the whole economy — quarterly and revised, so it confirms a turn late."),
        Indicator("US_INDPRO", "US industrial production", "US industrial production", "growth", "index (2017=100)", "monthly", True,
                  "INDPRO", "A monthly, coincident read on factory-sector output — faster to arrive than GDP."),
        Indicator("US_DURABLE_GOODS", "US durable goods orders", "US durable goods", "growth", "index ($M)", "monthly", True,
                  "DGORDER", "New orders for goods meant to last 3+ years — a forward look at capex and industrial demand (industrials, materials)."),
        Indicator("US_RETAIL", "US retail & food services sales", "US retail sales", "consumption", "$M", "monthly", True,
                  "RSAFS", "What US households are actually spending, before it shows up in company earnings."),
        Indicator("US_RETAIL_STAPLES", "US retail sales: food & beverage stores", "US staples retail", "consumption", "$M", "monthly", True,
                  "RSDBS", "The steadier, less discretionary slice of retail spending (grocery and beverage stores) — a read on consumer staples demand specifically."),
        Indicator("US_RETAIL_DISCRETIONARY", "US retail sales: general merchandise stores", "US discretionary retail", "consumption", "$M", "monthly", True,
                  "RSGMS", "The more discretionary slice of retail spending — a read on consumer discretionary demand specifically."),
        Indicator("US_VEHICLE_SALES", "US light-vehicle sales (SAAR)", "US vehicle sales", "consumption", "M units (SAAR)", "monthly", False,
                  "TOTALSA", "Big-ticket discretionary spending; sensitive to rates, confidence and supply shocks (chips in 2021-22)."),
        Indicator("US_HOUSING_STARTS", "US housing starts", "US housing starts", "housing", "K units (SAAR)", "monthly", True,
                  "HOUST", "New home construction begins — feeds homebuilders, building materials and durable-goods demand."),
        Indicator("US_BUILDING_PERMITS", "US building permits", "US building permits", "housing", "K units (SAAR)", "monthly", True,
                  "PERMIT", "Permits lead starts by weeks to months — a cleaner read on builders' near-term intentions, less noisy than starts."),
        Indicator("US_MORTGAGE_30Y", "US 30-year fixed mortgage rate", "US 30Y mortgage rate", "housing", "%", "weekly", False,
                  "MORTGAGE30US", "The cost of a home loan; housing activity and homebuilder stocks are unusually sensitive to this rate, not just the Fed funds rate."),
        Indicator("US_BANK_CREDIT", "US bank loans and leases", "US bank credit", "credit", "index ($bn)", "weekly", True,
                  "TOTLL", "Total credit extended by US banks; a slowdown here tightens financial conditions economy-wide, ahead of the effect showing up elsewhere."),
        Indicator("US_CREDIT_SPREAD", "US Baa corporate yield spread over 10-year Treasury", "US credit spread (Baa)", "credit", "%", "daily", False,
                  "BAA10Y", "Widens when lenders demand more to hold lower-grade corporate debt — an early stress signal for financials and credit-sensitive sectors."),
    ],
    "india": [
        # a new key, not IN_CPI: that one holds the old FRED mirror's index levels, these are inflation rates
        Indicator("IN_CPI_YOY", "India CPI inflation, all-India combined (YoY)", "India CPI", "inflation", "%", "monthly", False,
                  "General", "India's food-heavy inflation basket; drives RBI policy and real returns. MoSPI's published "
                  "headline rate, about two weeks after the month.", source="mospi_cpi", growth=True),
        Indicator("IN_GDP", "India real GDP growth", "India real GDP", "growth", "%", "quarterly", False,
                  "INDGDPRQPSMEI", "Already a year-on-year growth rate. Quarterly and arrives with a longer lag than the US figure.", growth=True),
        # a new key, not IN_INDPROD: that one holds the old FRED mirror's index levels, these are growth rates
        Indicator("IN_IIP", "India industrial production (IIP), YoY growth", "India IIP", "growth", "%", "monthly", False,
                  "General", "MoSPI's monthly factory, mining and power output index — the release markets react to, about six weeks after the month.",
                  source="mospi_iip", growth=True),
        Indicator("IN_IIP_DURABLES", "India IIP: consumer durables, YoY growth", "India consumer durables output", "consumption", "%", "monthly", False,
                  "Consumer Durables", "Output of cars, two-wheelers, appliances, phones — urban and discretionary demand, read from the factory side.",
                  source="mospi_iip", growth=True),
        Indicator("IN_IIP_NONDURABLES", "India IIP: consumer non-durables, YoY growth", "India consumer non-durables output", "consumption", "%", "monthly", False,
                  "Consumer Non-durables", "Output of food, personal care and other everyday goods — the staples/FMCG and rural-demand read.",
                  source="mospi_iip", growth=True),
        Indicator("IN_VEHICLE_REG", "India new vehicle registrations (Vahan)", "India vehicle registrations", "consumption", "registrations", "monthly", True,
                  "", "Every new vehicle registered nationwide, out within days of the month — the freshest consumption read India has. "
                      "Earlier years undercount as states joined Vahan, so growth before 2024 is overstated; the festive season "
                      "(Oct/Nov) moves between months, so compare year on year.",
                  source="vahan"),
        Indicator("IN_PFCE", "India real private consumption growth", "India private consumption", "consumption", "%", "quarterly", False,
                  "NAEXKP02INQ659S", "Household spending in the national accounts, adjusted for prices — about 55-60% of India's GDP. Quarterly and late, so it confirms a trend rather than calls it.", growth=True),
    ],
}

PERIODS_PER_YEAR = {"daily": 365, "weekly": 52, "monthly": 12, "quarterly": 4}


def _meta(market: str, key: str) -> Indicator | None:
    return next((x for x in INDICATORS.get(market, []) if x.key == key), None)


def _upsert(market: str, key: str, s: pd.Series) -> int:
    """Write the series' values that are new or different from what is stored. -> rows written."""
    s = s.dropna().round(4)
    if s.empty:
        return 0
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date >= %s",
                    (market, key, s.index.min().date()))
        have = {d: float(c) for d, c in cur.fetchall()}
    rows = [(market, key, d.date(), float(v)) for d, v in s.items()
            if have.get(d.date()) is None or abs(have[d.date()] - v) > 1e-6]
    if rows:
        db.execute_values("INSERT INTO index_series (market, series, date, close) VALUES %s "
                          "ON CONFLICT (market, series, date) DO UPDATE SET close = EXCLUDED.close", rows)
    return len(rows)


def _mospi_session():
    """A requests session that can talk to api.mospi.gov.in: its server only completes the TLS handshake
    with legacy renegotiation, which OpenSSL 3 refuses by default. Allowed for that one host only, and
    certificate verification stays on — a read-only GET of public statistics, nothing sent but the query."""
    import requests
    from requests.adapters import HTTPAdapter

    class _LegacyRenegotiation(HTTPAdapter):
        def init_poolmanager(self, *a, **kw):
            ctx = ssl.create_default_context()
            ctx.options |= getattr(ssl, "OP_LEGACY_SERVER_CONNECT", 0x4)
            kw["ssl_context"] = ctx
            return super().init_poolmanager(*a, **kw)

    s = requests.Session()
    s.mount("https://api.mospi.gov.in", _LegacyRenegotiation())
    return s


def mospi_iip(category: str) -> pd.Series:
    """MoSPI's published IIP year-on-year growth (%) for one category — "General", or a use-based group
    such as "Consumer Durables" — monthly, indexed by each month's first day. The growth rate is used
    rather than the index so the 2011-12 and 2022-23 bases join without a level break; the newer base
    wins where both have a month."""
    s = _mospi_session()
    typ = "General" if category == "General" else "Use-based category"
    got: dict[pd.Timestamp, float] = {}
    for base in MOSPI_BASES:
        page = 1
        while True:
            r = s.get(MOSPI_IIP, params={"base_year": base, "type": typ, "frequency": "Monthly", "limit": 200,
                                         "page": page, "Format": "JSON"}, headers=BROWSER_UA, timeout=TIMEOUT)
            r.raise_for_status()
            j = r.json()
            for x in j.get("data") or []:
                if x.get("category") != category or x.get("growth_rate") in (None, ""):
                    continue
                d = dt.datetime.strptime(f"{x['year']} {x['month']}", "%Y %B")
                got[pd.Timestamp(d)] = float(x["growth_rate"])
            if page >= (j.get("meta_data") or {}).get("totalPages", 1):
                break
            page += 1
    if not got:
        raise ValueError(f"MoSPI IIP {category}: no data returned")
    return pd.Series(got).sort_index()


def mospi_cpi() -> pd.Series:
    """MoSPI's all-India combined CPI inflation (YoY %), monthly, indexed by each month's first day: the
    2012-base series to Dec-2025, then the 2024-base series (the newer base wins where both have a month)."""
    s = _mospi_session()
    got: dict[pd.Timestamp, float] = {}
    page = 1
    while True:                         # the API caps a page at 200 rows
        r = s.get(MOSPI_CPI_OLD, params={"base_year": "2012", "state_code": "99", "sector_code": "3", "group_code": "0",
                                         "limit": 200, "page": page, "Format": "JSON"}, headers=BROWSER_UA, timeout=TIMEOUT)
        r.raise_for_status()
        j = r.json()
        for x in j.get("data") or []:
            if x.get("inflation") in (None, "") or x.get("state") != "All India" or x.get("sector") != "Combined":
                continue
            got[pd.Timestamp(dt.datetime.strptime(f"{x['year']} {x['month']}", "%Y %B"))] = float(x["inflation"])
        if page >= (j.get("meta_data") or {}).get("totalPages", 1):
            break
        page += 1
    # the 2024 base filters only by year and month: one small call per month, newest last, until a month is empty
    d, this_month = MOSPI_CPI_NEW_FROM, dt.date.today().replace(day=1)
    while d <= this_month:
        r = s.get(MOSPI_CPI_NEW, params={"base_year": "2024", "year": str(d.year), "month_code": str(d.month),
                                         "limit": 10, "Format": "JSON"}, headers=BROWSER_UA, timeout=TIMEOUT)
        r.raise_for_status()
        row = next((x for x in r.json().get("data") or [] if x.get("state") == "All India" and x.get("sector") == "Combined"
                    and x.get("division") == "CPI (General)" and x.get("inflation") not in (None, "")), None)
        if row is None:
            break                       # not published yet
        got[pd.Timestamp(d)] = float(row["inflation"])
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    if not got:
        raise ValueError("MoSPI CPI: no data returned")
    return pd.Series(got).sort_index()


def vahan_registrations() -> pd.Series:
    """All-India new vehicle registrations per month from the Vahan dashboard, from VAHAN_FROM, completed
    months only (the running month is partial). The response also carries placeholder rows (odd years,
    zero counts) that are skipped."""
    import requests
    # The endpoint returns its whole history whatever range is asked for, but answers some fromYear values
    # with a 500 (2019 did, consistently, while 2015 and 2025 worked) — so ask for a range known to work,
    # with a fallback, and filter to VAHAN_FROM here.
    year = dt.date.today().year
    r = None
    for from_year in (year - 1, 2015):
        params = {"calendarType": 3, "stateCode": -1, "rtoCode": -1, "fromYear": from_year, "toYear": year,
                  "timePeriod": 2, "fitnessCheck": 0, "vehicleType": "", "archiveTypeAC": "ACTIVE_COMPLIANT",
                  "archiveTypeANC": "ACTIVE_NON_COMPLIANT", "archiveTypePA": "", "archiveTypeTA": "", "archiveTypeNA": ""}
        r = requests.get(VAHAN, params=params, headers=BROWSER_UA, timeout=TIMEOUT)
        if r.ok:
            break
    r.raise_for_status()
    this_month = dt.date.today().replace(day=1)
    got: dict[pd.Timestamp, float] = {}
    for x in r.json():
        m = re.fullmatch(r"(\d{4})-([A-Za-z]+)", x.get("yearAsString") or "")
        n = x.get("registeredVehicleCount") or 0
        if not m or n <= 0:
            continue
        d = dt.datetime.strptime(f"{m[1]} {m[2]}", "%Y %B").date()
        if d.year >= VAHAN_FROM and d < this_month:
            got[pd.Timestamp(d)] = float(n)
    if not got:
        raise ValueError("Vahan: no monthly registrations returned")
    return pd.Series(got).sort_index()


def _fetch(ind: Indicator) -> pd.Series:
    if ind.source == "mospi_iip":
        return mospi_iip(ind.source_id)
    if ind.source == "mospi_cpi":
        return mospi_cpi()
    if ind.source == "vahan":
        return vahan_registrations()
    return fred(ind.source_id)


def refresh(market: str) -> dict:
    """Fetch and store the market's indicators. -> {"written": {key: rows}, "failed": {key: error}}."""
    from . import index_data
    index_data.init_schema()
    written, failed = {}, {}
    for ind in INDICATORS.get(market, []):
        try:
            written[ind.key] = _upsert(market, ind.key, _fetch(ind))
        except Exception as e:  # noqa: BLE001 — one series failing must not stop the rest
            failed[ind.key] = str(e)[:200]
            logger.warning("indicators %s %s: %s", market, ind.key, e)
    return {"written": written, "failed": failed}


def history(market: str, key: str) -> pd.Series:
    """A stored indicator's full history (the raw level, or rate when `yoy` is False)."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s ORDER BY date", (market, key))
        got = cur.fetchall()
    return pd.Series([float(c) for _, c in got], index=pd.to_datetime([d for d, _ in got]), dtype=float)


def _change(s: pd.Series, days: int, pct: bool) -> float | None:
    """Change over `days` calendar days (the value on or before then): a percent change for a level, or a
    plain point difference for a series already shown in percent (a point change reads better than a
    percent change of a percent, e.g. CPI YoY 3.0% -> 3.3% is "+0.3pp", not "+10%")."""
    if s.empty:
        return None
    then = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
    if then.empty:
        return None
    return float((s.iloc[-1] / then.iloc[-1] - 1) * 100) if pct and then.iloc[-1] else float(s.iloc[-1] - then.iloc[-1])


def summary(market: str) -> list[dict]:
    """Each stored indicator: last value (its YoY% when `yoy` is set, else the stored rate itself), its
    as-of date, 1-month / 1-year change (percent for a level, points for a series already shown in
    percent), and its history as [date, value] points for a chart — YoY% points when `yoy` is set, the
    stored level/rate otherwise."""
    out = []
    for ind in INDICATORS.get(market, []):
        s = history(market, ind.key)
        if s.empty:
            continue
        shown = s.pct_change(PERIODS_PER_YEAR[ind.freq]).dropna() * 100 if ind.yoy else s
        if shown.empty:
            continue
        unit = "%" if ind.yoy else ind.unit
        pct = unit != "%"
        out.append({"key": ind.key, "label": ind.label, "short": ind.short, "category": ind.category,
                    "unit": unit, "freq": ind.freq, "yoy": ind.yoy or ind.growth, "why": ind.why,
                    "date": str(shown.index[-1].date()), "value": float(shown.iloc[-1]),
                    "m1": _change(shown, 30, pct), "y1": _change(shown, 365, pct),
                    "points": [[d.strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in shown.items()]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh growth, inflation and consumption indicators")
    ap.add_argument("--market", choices=list(INDICATORS), help="one market (default: all)")
    ap.add_argument("--list", action="store_true", help="print what is stored instead of fetching")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for mk in [a.market] if a.market else list(INDICATORS):
        if a.list:
            for x in summary(mk):
                m1 = f"{x['m1']:+.1f}" if x["m1"] is not None else "—"
                print(f"{mk:6s} {x['key']:14s} {x['value']:10.2f} {x['unit']:18s} {m1:>7s}  {x['date']}  {x['label']}")
        else:
            print(mk, refresh(mk))


if __name__ == "__main__":
    main()
