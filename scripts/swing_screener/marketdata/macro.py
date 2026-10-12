"""Macro series to read beside the market: rates, the dollar, oil, metals, credit.

These are levels to WATCH, not series to invest in, so they differ from `index_data` on purpose:
raw daily closes (no dividend adjustment), and no outlier repair or positivity filter — WTI really
did settle at -37.63 on 2020-04-20, and VIX-like spikes are the point, not artefacts. They land in
the same `index_series` table under the market each one informs most, so each market's `indexes`
job refreshes its own few:

    us     US10Y, US5Y (yields, %), DXY, WTI, GOLD_FUT, COPPER, HYG (high-yield credit)
    india  BRENT (India imports most of its oil); USD/INR and India VIX are already stored by
           index_data and the Breadth page

Yahoo has no India 10-year government bond yield, so it is not here.

    PYTHONPATH=. python3 -m swing_screener.marketdata.macro            # refresh both markets
    PYTHONPATH=. python3 -m swing_screener.marketdata.macro --list     # what is stored
"""

import argparse
import logging
import warnings
from dataclasses import dataclass

import pandas as pd

from . import db

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Macro:
    key: str        # series name in index_series
    ticker: str     # Yahoo symbol
    label: str
    unit: str       # "%" for a yield, else what the price is quoted in
    why: str        # what it tells a trader, for the app
    short: str = ""  # the strip's tile label (label when empty)


SERIES: dict[str, list[Macro]] = {
    "us": [
        Macro("US10Y", "^TNX", "US 10-year Treasury yield", "%",
              "Rising long yields pressure growth-stock valuations; sharp jumps often come with selling.", short="US 10Y yield"),
        Macro("US5Y", "^FVX", "US 5-year Treasury yield", "%",
              "Moves with where the market expects the Fed to take rates over the next few years.", short="US 5Y yield"),
        Macro("DXY", "DX-Y.NYB", "US Dollar Index", "index",
              "A strong dollar weighs on emerging markets (India included) and on US multinationals.", short="Dollar index"),
        Macro("WTI", "CL=F", "WTI crude oil", "$/bbl",
              "Energy stocks, inflation expectations, consumer spending.", short="WTI crude"),
        Macro("GOLD_FUT", "GC=F", "Gold", "$/oz",
              "Fear and hedging demand; falls when real yields rise.", short="Gold"),
        Macro("COPPER", "HG=F", "Copper", "$/lb",
              "A rough read on global industrial growth; metals and miners.", short="Copper"),
        Macro("HYG", "HYG", "High-yield corporate bonds (HYG)", "$",
              "Credit risk appetite: HYG falling while stocks rise is an early warning.", short="HY credit (HYG)"),
    ],
    "india": [
        Macro("BRENT", "BZ=F", "Brent crude oil", "$/bbl",
              "India imports most of its oil: dearer crude widens the deficit, weakens the rupee and "
              "lifts inflation. Oil marketers, paints, aviation, tyres.", short="Brent crude"),
    ],
}


# Read-only extras the strip shows but this module does not fetch (index_data stores them).
EXTRA = {
    ("india", "USDINR"): Macro("USDINR", "INR=X", "US dollar in rupees", "₹",
                               "A weaker rupee usually comes with foreign selling of Indian stocks; it helps IT "
                               "exporters and hurts importers.", short="USD/INR"),
}

# What each market's macro strip shows, in order: (stored market, series). India's includes the US 10-year
# and the dollar, which drive foreign flows into India.
STRIP: dict[str, list[tuple[str, str]]] = {
    "us": [("us", "US10Y"), ("us", "US5Y"), ("us", "DXY"), ("us", "WTI"), ("us", "GOLD_FUT"), ("us", "COPPER"),
           ("us", "HYG")],
    "india": [("india", "BRENT"), ("india", "USDINR"), ("us", "US10Y"), ("us", "DXY"), ("us", "GOLD_FUT")],
}


def _meta(market: str, key: str) -> Macro | None:
    return next((m for m in SERIES.get(market, []) if m.key == key), None) or EXTRA.get((market, key))


def fetch(m: Macro) -> pd.Series:
    """Full daily history of one series, raw closes."""
    import yfinance as yf

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.Ticker(m.ticker).history(period="max", interval="1d", auto_adjust=False)
    if raw is None or raw.empty:
        raise ValueError(f"{m.ticker}: no data returned")
    s = raw["Close"].dropna()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s[~s.index.duplicated(keep="last")].sort_index()


def refresh(market: str) -> dict[str, int]:
    """Fetch and upsert each of the market's macro series. -> {key: rows stored (0 = failed)}."""
    from . import index_data
    index_data.init_schema()
    out = {}
    for m in SERIES.get(market, []):
        try:
            s = fetch(m)
            db.execute_values(
                "INSERT INTO index_series (market, series, date, close) VALUES %s "
                "ON CONFLICT (market, series, date) DO UPDATE SET close = EXCLUDED.close",
                [(market, m.key, d.date(), float(c)) for d, c in s.items()])
            out[m.key] = len(s)
        except Exception as exc:  # noqa: BLE001 — one missing series must not stop the rest
            logger.warning("macro %s (%s) failed: %s", m.key, m.ticker, exc)
            out[m.key] = 0
    return out


def latest(market: str, spark_days: int = 63) -> list[dict]:
    """The market's strip (STRIP): each series' last close, its 1-day and 1-month change — in basis points
    for a yield, percent otherwise — and the last `spark_days` closes for a sparkline. Unstored series are left out."""
    rows = []
    with db.get_connection().cursor() as cur:
        for mk, key in STRIP.get(market, []):
            m = _meta(mk, key)
            if m is None:
                continue
            cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s ORDER BY date DESC LIMIT %s",
                        (mk, key, max(spark_days, 22)))
            got = cur.fetchall()
            if not got:
                continue
            last_d, last = got[0]
            prev = got[1][1] if len(got) > 1 else None
            month = got[21][1] if len(got) > 21 else None
            bp = m.unit == "%"   # a yield's move is quoted in basis points; a price's in percent

            def chg(a):
                if a is None:
                    return None
                return (last - a) * 100 if bp else ((last / a - 1) * 100 if a else None)
            rows.append({"key": key, "market": mk, "label": m.label, "short": m.short or m.label, "unit": m.unit, "why": m.why, "date": str(last_d),
                         "close": last, "d1": chg(prev), "m1": chg(month), "change_unit": "bp" if bp else "%",
                         "spark": [c for _, c in reversed(got[:spark_days])]})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh the macro series (rates, dollar, oil, metals, credit)")
    ap.add_argument("--market", choices=list(SERIES), help="one market (default: both)")
    ap.add_argument("--list", action="store_true", help="print what is stored instead of fetching")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for mk in [a.market] if a.market else list(SERIES):
        if a.list:
            for r in latest(mk):
                if r["market"] != mk:
                    continue
                d1 = f"{r['d1']:+.2f}{r['change_unit']}" if r["d1"] is not None else "—"
                print(f"{mk:6s} {r['key']:9s} {r['close']:>10.2f} {r['unit']:6s} {d1:>9s}  {r['date']}  {r['label']}")
        else:
            print(mk, refresh(mk))


if __name__ == "__main__":
    main()
