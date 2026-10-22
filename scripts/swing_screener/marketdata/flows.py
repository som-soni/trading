"""Daily net institutional equity flows: FII/FPI and DII cash-market buying and selling, India only.

NSE publishes this as JSON — not FRED or yfinance like every other module here, an undocumented but
currently reachable endpoint: a plain HTTP GET with a browser-like User-Agent, no login or session
cookie needed (confirmed working without ever visiting the homepage for a session cookie first).
Unlike rates.py's RBI scrape (a long-stable, simple page) this is closer to the NSE pages known for
anti-bot protection that have changed or broken before without notice, so a failed day is logged and
skipped, never treated as fatal — the same spirit as every other scraped (non-API) source here.

Stored in `index_series` as the day's NET value only (buy minus sell, ₹ crore) — FII_NET and DII_NET —
since that is what a trader actually watches; gross buy/sell are in `fetch()`'s return but not stored.

    PYTHONPATH=. python3 -m swing_screener.marketdata.flows            # refresh today's reading
    PYTHONPATH=. python3 -m swing_screener.marketdata.flows --list     # what is stored
"""

import argparse
import datetime as dt
import logging

import pandas as pd

from . import db

logger = logging.getLogger(__name__)

NSE_FII_DII = "https://www.nseindia.com/api/fiidiiTradeReact"
TIMEOUT = 30

# NSE's own "category" label in the response -> the key we store it under in index_series
SERIES = {"FII/FPI": "FII_NET", "DII": "DII_NET"}
LABELS = {
    "FII_NET": ("FII / FPI", "Foreign investors' daily net cash-market buying (+) or selling (-). A "
                "sustained sell streak usually comes with a weaker rupee and pressure on large caps."),
    "DII_NET": ("DII", "Domestic funds' and insurers' daily net cash-market buying (+) or selling (-). "
                "DII buying has repeatedly cushioned FII selling since 2022 — read the two together."),
}


def fetch() -> dict[str, tuple[dt.date, float, float, float]]:
    """Today's provisional net flow for FII/FPI and DII. -> {key: (date, buy, sell, net)}, all ₹ crore."""
    import requests
    r = requests.get(NSE_FII_DII, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    out = {}
    for row in r.json():
        key = SERIES.get(row.get("category"))
        if key is None:
            continue
        d = dt.datetime.strptime(row["date"], "%d-%b-%Y").date()
        out[key] = (d, float(row["buyValue"]), float(row["sellValue"]), float(row["netValue"]))
    return out


def refresh(market: str = "india") -> dict:
    """Fetch and store today's FII/DII net flow. -> {"written": {key: rows}, "failed": {key: error}}."""
    if market != "india":
        return {"written": {}, "failed": {}}
    from . import index_data
    index_data.init_schema()
    written: dict[str, int] = {}
    failed: dict[str, str] = {}
    try:
        got = fetch()
    except Exception as e:  # noqa: BLE001 — an unofficial endpoint: a failed day must not fail the job
        logger.warning("flows: fetch failed: %s", e)
        got = {}
        for key in SERIES.values():
            failed[key] = str(e)[:200]
    for key, (d, _buy, _sell, net) in got.items():
        db.execute_values("INSERT INTO index_series (market, series, date, close) VALUES %s "
                          "ON CONFLICT (market, series, date) DO UPDATE SET close = EXCLUDED.close",
                          [("india", key, d, round(net, 2))])
        written[key] = 1
    for key in SERIES.values():
        if key not in got and key not in failed:
            failed[key] = "not in NSE's response"
    return {"written": written, "failed": failed}


def history(key: str) -> pd.Series:
    """A stored flow's full history (net ₹cr)."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM index_series WHERE market='india' AND series=%s ORDER BY date", (key,))
        got = cur.fetchall()
    return pd.Series([float(c) for _, c in got], index=pd.to_datetime([d for d, _ in got]), dtype=float)


def summary() -> list[dict]:
    """Each stored flow: last value, its date, the running 5-day and 20-day sums (the number a trader
    actually watches — a single day's net is noisy), and full history as [date, value] points for a chart."""
    out = []
    for key, (label, why) in LABELS.items():
        s = history(key)
        if s.empty:
            continue
        out.append({"key": key, "label": label, "why": why,
                    "date": str(s.index[-1].date()), "value": float(s.iloc[-1]),
                    "sum5": float(s.tail(5).sum()), "sum20": float(s.tail(20).sum()),
                    "points": [[d.strftime("%Y-%m-%d"), round(float(v), 2)] for d, v in s.items()]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh FII/DII daily net institutional equity flows (India)")
    ap.add_argument("--list", action="store_true", help="print what is stored instead of fetching")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.list:
        for x in summary():
            print(f"india  {x['key']:10s} {x['value']:>10.1f} cr  5d {x['sum5']:>10.1f}  20d {x['sum20']:>10.1f}  {x['date']}  {x['label']}")
    else:
        print(refresh())


if __name__ == "__main__":
    main()
