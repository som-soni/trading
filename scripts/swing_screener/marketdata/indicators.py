"""Growth, inflation, consumption, housing and credit indicators — the macro numbers behind the
business cycle, as opposed to the policy rates and market-priced series already covered by
`rates.py` and `macro.py`.

Stored in `index_series` (one row per series per date, FRED's native daily/weekly/monthly/quarterly
cadence — no resampling) under the market each one describes, fetched from FRED's free, key-less
CSV endpoint (`rates.fred()`, the same helper `rates.py` uses for US yields):

    us     CPI (CPIAUCSL), real GDP (GDPC1), industrial production (INDPRO), retail sales
           (RSAFS, and its staples/discretionary split RSDBS/RSGMS), light-vehicle sales
           (TOTALSA), durable goods orders (DGORDER), housing starts and permits (HOUST,
           PERMIT), the 30-year mortgage rate (MORTGAGE30US), bank credit (TOTLL) and the Baa
           corporate credit spread (BAA10Y)
    india  CPI (INDCPIALLMINMEI) and industrial production (INDPROINDMISMEI), both OECD's India
           mirror of MOSPI releases; GDP (INDGDPRQPSMEI, already a YoY growth rate, not a level)

India vehicle sales (SIAM/FADA), the unemployment rate (PLFS/CMIE), and sector-level series
(housing starts, mortgage rates, bank credit growth) have no free, machine-readable release — PDF
or press-release only, fortnightly bulletins, or paywalled — so they are not here. `summary()`
reports them as absent rather than guessing at a number.

FRED's OECD mirror of an India series can lag the live MOSPI/SIAM release by weeks; `summary()`
always reports the as-of date of the last stored point so staleness is visible rather than
hidden behind a number.

    PYTHONPATH=. python3 -m swing_screener.marketdata.indicators            # refresh both markets
    PYTHONPATH=. python3 -m swing_screener.marketdata.indicators --list     # what is stored
"""

import argparse
import datetime as dt
import logging
from dataclasses import dataclass

import pandas as pd

from . import db
from .rates import fred

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Indicator:
    key: str          # series name in index_series
    label: str
    short: str        # the card's tile label
    category: str     # "inflation" | "growth" | "consumption" | "housing" | "credit"
    unit: str         # unit of the stored level (not the derived YoY%, which is always "%")
    freq: str         # "daily" | "weekly" | "monthly" | "quarterly" — periods/year, for the YoY calc
    yoy: bool         # derive and report YoY% from the stored level; False when the level is itself
                      # a rate or spread, already in percent, that a trader reads as a level, not growth
    source_id: str    # FRED series id
    why: str          # what it tells a trader, for the app


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
        Indicator("IN_CPI", "India CPI, all items", "India CPI", "inflation", "index (2015=100, NSA)", "monthly", True,
                  "INDCPIALLMINMEI", "India's food-heavy inflation basket; drives RBI policy and real returns."),
        Indicator("IN_GDP", "India real GDP growth", "India real GDP", "growth", "%", "quarterly", False,
                  "INDGDPRQPSMEI", "Already a year-on-year growth rate. Quarterly and arrives with a longer lag than the US figure."),
        Indicator("IN_INDPROD", "India industrial production", "India industrial production", "growth", "index (2015=100)", "monthly", True,
                  "INDPROINDMISMEI", "A monthly stand-in for the IIP release; OECD's mirror can lag MOSPI's own by weeks."),
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


def refresh(market: str) -> dict:
    """Fetch and store the market's indicators. -> {"written": {key: rows}, "failed": {key: error}}."""
    from . import index_data
    index_data.init_schema()
    written, failed = {}, {}
    for ind in INDICATORS.get(market, []):
        try:
            written[ind.key] = _upsert(market, ind.key, fred(ind.source_id))
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
                    "unit": unit, "freq": ind.freq, "yoy": ind.yoy, "why": ind.why,
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
