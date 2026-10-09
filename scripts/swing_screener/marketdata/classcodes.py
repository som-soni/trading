"""Official industry codes per stock — the raw material for sub-industries (marketdata/subindustries.py).

    India   BSE's classification (the exchanges' common 4-level scheme: sector › industry › …), whose finest
            level, "Industry", has ~140 values such as "Heavy Electrical Equipment", "Civil Construction",
            "Private Sector Bank". One request per company to BSE's public company-header API, matched to our
            NSE symbol through BSE's scrip list (by NSE symbol, else ISIN). Paced at ~3 requests a second.
    US      Nasdaq's stock-screener industry (~150 values, SIC-based: "Semiconductors",
            "Military/Government/Technical", "Major Banks"...). One request for every listed stock.

Stored in `symbol_codes` (market, symbol, scheme, code, label, detail, fetched_at). A code older than
MAX_AGE_DAYS is fetched again; classifications rarely change, so a monthly job keeps this current at
little cost (only new listings and stale codes are fetched).

    PYTHONPATH=. python3 -m swing_screener.marketdata.classcodes --market india
"""

import argparse
import json
import logging
import time

import requests

from . import db

logger = logging.getLogger(__name__)
MAX_AGE_DAYS = 90
PACE_S = 0.3
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
       "Accept": "application/json, text/plain, */*"}
_BSE = {**_UA, "Referer": "https://www.bseindia.com/", "Origin": "https://www.bseindia.com"}
BSE_LIST = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Scripcode=&industry=&segment=Equity&status=Active"
BSE_HEADER = "https://api.bseindia.com/BseIndiaAPI/api/ComHeadernew/w?quotetype=EQ&scripcode={code}&seriesid="
NASDAQ_SCREENER = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&download=true"
SCHEME = {"india": "bse", "us": "nasdaq"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS symbol_codes (
    market VARCHAR(16) NOT NULL, symbol TEXT NOT NULL, scheme TEXT NOT NULL,
    code TEXT, label TEXT, detail JSONB, fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, scheme)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def load(market: str) -> dict[str, dict]:
    """symbol -> {"code", "label", "detail"} for the market's scheme."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, code, label, detail FROM symbol_codes WHERE market=%s AND scheme=%s", (market, SCHEME[market]))
        return {s: {"code": c, "label": l, "detail": d or {}} for s, c, l, d in cur.fetchall()}


def _save(market: str, rows: list[tuple]) -> None:
    if rows:
        db.execute_values("""INSERT INTO symbol_codes (market, symbol, scheme, code, label, detail) VALUES %s
                             ON CONFLICT (market, symbol, scheme) DO UPDATE SET code=EXCLUDED.code, label=EXCLUDED.label,
                             detail=EXCLUDED.detail, fetched_at=now()""",
                          [(market, s, SCHEME[market], c, l, json.dumps(d)) for s, c, l, d in rows])


def _fresh(market: str) -> set:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM symbol_codes WHERE market=%s AND scheme=%s AND fetched_at > now() - %s * interval '1 day' AND code IS NOT NULL",
                    (market, SCHEME[market], MAX_AGE_DAYS))
        return {r[0] for r in cur.fetchall()}


def refresh_us(symbols: list[str] | None = None) -> dict:
    """Nasdaq's industry for every US stock (one request)."""
    init_schema()
    r = requests.get(NASDAQ_SCREENER, headers=_UA, timeout=90)
    r.raise_for_status()
    rows = r.json()["data"]["rows"]
    want = set(symbols) if symbols else None
    out = []
    for x in rows:
        s = (x.get("symbol") or "").strip().replace("/", "-").replace(".", "-")
        if not s or (want is not None and s not in want) or not (x.get("industry") or "").strip():
            continue
        out.append((s, x["industry"].strip(), x["industry"].strip(), {"sector": (x.get("sector") or "").strip()}))
    _save("us", out)
    return {"fetched": len(out), "requests": 1}


def refresh_india(symbols: list[str], force: bool = False, limit: int | None = None) -> dict:
    """BSE's industry for the given NSE symbols (SYMBOL.NS) not fetched in the last MAX_AGE_DAYS."""
    init_schema()
    todo = [s for s in symbols if force or s not in _fresh("india")]
    if limit:
        todo = todo[:limit]
    if not todo:
        return {"fetched": 0, "requests": 0, "unmatched": 0}
    sess = requests.Session()
    lst = sess.get(BSE_LIST, headers=_BSE, timeout=90).json()
    by_id = {str(x.get("scrip_id") or "").upper(): x for x in lst}
    by_isin = {x.get("ISIN_NUMBER"): x for x in lst if x.get("ISIN_NUMBER")}
    isin = _india_isins()
    rows, unmatched, n, t0 = [], [], 0, time.time()
    for s in todo:
        base = s.removesuffix(".NS").upper()
        x = by_id.get(base) or by_isin.get(isin.get(s))
        if not x:
            unmatched.append(s)
            continue
        try:
            d = sess.get(BSE_HEADER.format(code=x["SCRIP_CD"]), headers=_BSE, timeout=30).json()
            n += 1
            if d.get("Industry"):
                rows.append((s, d["Industry"].strip(), d["Industry"].strip(),
                             {"industry_new": d.get("IndustryNew"), "sector": d.get("Sector"), "bse_code": x["SCRIP_CD"]}))
        except Exception as exc:  # noqa: BLE001 - one company failing must not stop the rest
            logger.warning("classcodes india %s: %s", s, exc)
        if len(rows) >= 100:
            _save("india", rows); rows = []
        if n and n % 200 == 0:
            logger.info("  classcodes india: %d/%d (%.0fs)", n, len(todo), time.time() - t0)
        time.sleep(PACE_S)
    _save("india", rows)
    return {"fetched": n, "requests": n + 1, "unmatched": len(unmatched)}


def _india_isins() -> dict:
    """NSE symbol -> ISIN, where we know it (for matching to BSE when the tickers differ)."""
    try:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT symbol, isin FROM symbol_names WHERE market='india' AND isin IS NOT NULL")
            return dict(cur.fetchall())
    except Exception:  # noqa: BLE001 - no ISIN column: match by symbol only
        db.get_connection().rollback() if not db.get_connection().autocommit else None
        return {}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(SCHEME))
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.market == "us":
        print(refresh_us())
    else:
        from ..screens import snapshot
        print(refresh_india(list(snapshot.load("india")["symbol"]), a.force, a.limit))


if __name__ == "__main__":
    main()
