"""NSE's daily derivatives bhavcopy: every F&O contract that traded, with its settle price.

Stage 1 of research/fno-scope.md. This module only FETCHES AND RECONCILES; nothing prices a
position off it yet, deliberately — an options backtest that reads a stale settle, a wrong
lot size or a missed expiry change produces a confident number, and because the payoff is
non-linear there is no equity-style sanity check to catch it. So the ingest has to be
trustworthy before anything is built on top.

Two archive layouts, and they overlap:

  * legacy (to mid-2024): INSTRUMENT, SYMBOL, EXPIRY_DT, STRIKE_PR, OPTION_TYP, OHLC,
    SETTLE_PR, CONTRACTS, VAL_INLAKH, OPEN_INT, CHG_IN_OI, TIMESTAMP
  * UDiFF (2024 onward): TradDt, FinInstrmTp, TckrSymb, XpryDt, StrkPric, OptnTp, OpnPric,
    HghPric, LwPric, ClsPric, SttlmPric, OpnIntrst, ChngInOpnIntrst, TtlTradgVol, TtlTrfVal

Both are normalised to one row shape here. The overlap is the point: `reconcile()` reads the
same day from both and compares, so the switchover is checked rather than assumed.

Why SETTLE and not CLOSE. Most contracts do not trade on a given day -- 5,246 of 7,407 index
options on 2024-06-14 -- and their OHLC is not blank, it is STALE: open/high/low come through
as 0.00 while `close` carries a last-traded price from whenever the strike last changed hands.
On that day a deep in-the-money BANKNIFTY 39500CE showed close 8,462.85 against settle
10,540.30, when intrinsic value alone was about 10,400. The close was simply old.

The exchange marks every contract daily whether or not it traded, and that is `settle`. Any
backtest must price off it. `close` is kept only to show when a contract last traded, and
`contracts` (the day's volume) is what says whether the price is live.

Scope, per the decisions in the scope note: India only (US options history is not free),
2012 onward, and INDEX derivatives first (FUTIDX/OPTIDX) — index options are ~4,000-7,500
rows a day against 31,000-47,000 for everything, and stock options are thin outside the top
names, where a backtest flatters itself. `--all-instruments` keeps the rest.

    PYTHONPATH=. python3 -m swing_screener.marketdata.derivatives --market india --days 5
    PYTHONPATH=. python3 -m swing_screener.marketdata.derivatives --market india --reconcile 2024-06-14
"""

import argparse
import datetime as dt
import io
import logging
import time
import zipfile

import pandas as pd
import requests

from . import db

logger = logging.getLogger("derivatives")

NSE_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
          "(KHTML, like Gecko) Chrome/129.0 Safari/537.36")
ARCHIVE = "https://nsearchives.nseindia.com"
NSE_PAUSE = 0.4               # be a good citizen on a public archive
INDEX_INSTRUMENTS = ("FUTIDX", "OPTIDX")
FIRST_DAY = dt.date(2012, 1, 1)   # the equity backtests start in 2010; 2012 halves the ingest

SCHEMA = """
CREATE TABLE IF NOT EXISTS derivatives_bhav (
    market VARCHAR(16) NOT NULL,
    trade_date DATE NOT NULL,
    instrument VARCHAR(8) NOT NULL,      -- FUTIDX | OPTIDX | FUTSTK | OPTSTK
    symbol VARCHAR(32) NOT NULL,         -- the UNDERLYING (NIFTY, BANKNIFTY, RELIANCE...)
    expiry DATE NOT NULL,
    strike DOUBLE PRECISION NOT NULL,    -- 0 for futures
    option_type VARCHAR(2) NOT NULL,     -- CE | PE | XX (futures)
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,              -- STALE when contracts=0: a last-traded price, not today's mark
    settle DOUBLE PRECISION,             -- what a position is actually marked at
    contracts BIGINT,
    value_lakh DOUBLE PRECISION,
    open_interest BIGINT,
    chg_open_interest BIGINT,
    source VARCHAR(8) NOT NULL,          -- legacy | udiff: which layout it was read from
    PRIMARY KEY (market, trade_date, instrument, symbol, expiry, strike, option_type)
);
CREATE INDEX IF NOT EXISTS derivatives_bhav_sym ON derivatives_bhav (market, symbol, expiry, trade_date);
"""

_COLS = ("market", "trade_date", "instrument", "symbol", "expiry", "strike", "option_type",
         "open", "high", "low", "close", "settle", "contracts", "value_lakh",
         "open_interest", "chg_open_interest", "source")


def init_schema() -> None:
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(SCHEMA)
        conn.commit()


# ------------------------------------------------------------------ fetching

_session: requests.Session | None = None


def _sess() -> requests.Session:
    """NSE rejects clients without a browser session; one warm-up sets the cookies."""
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({"User-Agent": NSE_UA, "Accept-Language": "en-US,en;q=0.9",
                          "Referer": "https://www.nseindia.com/"})
        try:
            s.get("https://www.nseindia.com/", timeout=20)
        except requests.RequestException as exc:      # the archive often answers anyway
            logger.debug("NSE warm-up failed (%s); trying the archive regardless", exc)
        _session = s
    return _session


def legacy_url(d: dt.date) -> str:
    mon = d.strftime("%b").upper()
    return f"{ARCHIVE}/content/historical/DERIVATIVES/{d.year}/{mon}/fo{d.day:02d}{mon}{d.year}bhav.csv.zip"


def udiff_url(d: dt.date) -> str:
    return f"{ARCHIVE}/content/fo/BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"


def _download(url: str) -> pd.DataFrame | None:
    """The zip's single CSV, or None when the day has no file (weekend, holiday, not published)."""
    time.sleep(NSE_PAUSE)
    try:
        r = _sess().get(url, timeout=60)
    except requests.RequestException as exc:
        logger.warning("%s: %s", url.rsplit("/", 1)[-1], exc)
        return None
    if not r.ok or len(r.content) < 2000:        # a 404 page is a few KB of HTML
        return None
    try:
        z = zipfile.ZipFile(io.BytesIO(r.content))
        return pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
    except (zipfile.BadZipFile, ValueError) as exc:
        logger.warning("%s: unreadable (%s)", url.rsplit("/", 1)[-1], exc)
        return None


def _num(v) -> float | None:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return None if f != f else f


def _norm_legacy(df: pd.DataFrame, market: str, d: dt.date) -> list[tuple]:
    df = df.rename(columns=lambda c: str(c).strip())
    out = []
    for r in df.to_dict("records"):
        inst = str(r.get("INSTRUMENT", "")).strip()
        if not inst:
            continue
        out.append((market, d, inst, str(r.get("SYMBOL", "")).strip(),
                    pd.to_datetime(r.get("EXPIRY_DT"), dayfirst=True, errors="coerce").date(),
                    _num(r.get("STRIKE_PR")) or 0.0, str(r.get("OPTION_TYP", "XX")).strip() or "XX",
                    _num(r.get("OPEN")), _num(r.get("HIGH")), _num(r.get("LOW")), _num(r.get("CLOSE")),
                    _num(r.get("SETTLE_PR")), int(_num(r.get("CONTRACTS")) or 0),
                    _num(r.get("VAL_INLAKH")), int(_num(r.get("OPEN_INT")) or 0),
                    int(_num(r.get("CHG_IN_OI")) or 0), "legacy"))
    return out


# UDiFF names the instrument types differently: STF/IDF futures, STO/IDO options.
_UDIFF_INSTRUMENT = {("STF", "XX"): "FUTSTK", ("IDF", "XX"): "FUTIDX",
                     ("STO", "CE"): "OPTSTK", ("STO", "PE"): "OPTSTK",
                     ("IDO", "CE"): "OPTIDX", ("IDO", "PE"): "OPTIDX"}


def _norm_udiff(df: pd.DataFrame, market: str, d: dt.date) -> list[tuple]:
    df = df.rename(columns=lambda c: str(c).strip())
    out = []
    for r in df.to_dict("records"):
        tp = str(r.get("FinInstrmTp", "")).strip()
        # A futures row leaves OptnTp empty, which pandas reads as NaN -- and NaN is TRUTHY,
        # so `x or "XX"` keeps the NaN and str() makes it the literal "nan". That silently
        # dropped every index future from mid-2024 on, which is precisely the series the
        # futures work needs. reconcile() caught it: 15 rows in legacy, 0 in udiff.
        raw_opt = r.get("OptnTp")
        opt = "XX" if raw_opt is None or pd.isna(raw_opt) or not str(raw_opt).strip() else str(raw_opt).strip()
        inst = _UDIFF_INSTRUMENT.get((tp, opt))
        if inst is None:
            continue                  # index/commodity types outside the F&O scope
        out.append((market, d, inst, str(r.get("TckrSymb", "")).strip(),
                    pd.to_datetime(r.get("XpryDt"), errors="coerce").date(),
                    _num(r.get("StrkPric")) or 0.0, opt,
                    _num(r.get("OpnPric")), _num(r.get("HghPric")), _num(r.get("LwPric")),
                    _num(r.get("ClsPric")), _num(r.get("SttlmPric")),
                    int(_num(r.get("TtlTradgVol")) or 0), _num(r.get("TtlTrfVal")),
                    int(_num(r.get("OpnIntrst")) or 0), int(_num(r.get("ChngInOpnIntrst")) or 0),
                    "udiff"))
    return out


def fetch_day(market: str, d: dt.date, prefer: str = "auto") -> list[tuple]:
    """One session's contracts, normalised. [] when the day has no file.

    `prefer` picks which layout to try first; "auto" uses the date, since the archives
    cross over in mid-2024, and falls back to the other if the expected one is missing.
    """
    order = [(udiff_url(d), _norm_udiff, "udiff"), (legacy_url(d), _norm_legacy, "legacy")]
    if prefer == "legacy" or (prefer == "auto" and d < dt.date(2024, 7, 1)):
        order.reverse()
    if prefer in ("legacy", "udiff"):
        order = [x for x in order if x[2] == prefer]
    for url, norm, _name in order:
        df = _download(url)
        if df is not None and not df.empty:
            return norm(df, market, d)
    return []


def store(rows: list[tuple]) -> int:
    if not rows:
        return 0
    db.execute_values(
        f"INSERT INTO derivatives_bhav ({', '.join(_COLS)}) VALUES %s "
        "ON CONFLICT (market, trade_date, instrument, symbol, expiry, strike, option_type) DO UPDATE SET "
        "open=EXCLUDED.open, high=EXCLUDED.high, low=EXCLUDED.low, close=EXCLUDED.close, "
        "settle=EXCLUDED.settle, contracts=EXCLUDED.contracts, value_lakh=EXCLUDED.value_lakh, "
        "open_interest=EXCLUDED.open_interest, chg_open_interest=EXCLUDED.chg_open_interest, "
        "source=EXCLUDED.source",
        rows)
    return len(rows)


def ingest(market: str = "india", start: dt.date | None = None, end: dt.date | None = None,
           instruments: tuple = INDEX_INSTRUMENTS, prefer: str = "auto") -> dict:
    """Fetch and store every session in the range. Skips days already stored."""
    init_schema()
    start = start or FIRST_DAY
    end = end or dt.date.today()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT DISTINCT trade_date FROM derivatives_bhav WHERE market=%s AND trade_date BETWEEN %s AND %s",
                    (market, start, end))
        have = {r[0] for r in cur.fetchall()}
    days = [d.date() for d in pd.bdate_range(start, end) if d.date() not in have]
    stored = blank = 0
    for i, d in enumerate(days, 1):
        rows = fetch_day(market, d, prefer)
        if instruments:
            rows = [r for r in rows if r[2] in instruments]
        if not rows:
            blank += 1
        else:
            stored += store(rows)
        if i % 50 == 0:
            logger.info("[%d/%d] %s: %d rows stored so far, %d days with no file", i, len(days), d, stored, blank)
    logger.info("%s %s..%s: %d rows from %d sessions (%d days had no file)",
                market, start, end, stored, len(days) - blank, blank)
    return {"rows": stored, "sessions": len(days) - blank, "no_file": blank}


# ------------------------------------------------------------------ verification

def reconcile(market: str, d: dt.date, instruments: tuple = INDEX_INSTRUMENTS) -> dict:
    """Read one day from BOTH layouts and compare, where the archives overlap.

    The whole ingest rests on the two layouts meaning the same thing. Mid-2024 is published
    in both, so this is checkable rather than a matter of trust: the same contracts, and the
    same settle for each.
    """
    legacy = {r[2:7]: r for r in fetch_day(market, d, "legacy") if not instruments or r[2] in instruments}
    udiff = {r[2:7]: r for r in fetch_day(market, d, "udiff") if not instruments or r[2] in instruments}
    if not legacy or not udiff:
        return {"date": d, "comparable": False,
                "note": f"only {'legacy' if legacy else 'udiff' if udiff else 'neither'} is published for {d}"}
    both = legacy.keys() & udiff.keys()
    settle_differs = [k for k in both
                      if (legacy[k][11] is None) != (udiff[k][11] is None)
                      or (legacy[k][11] is not None and abs(legacy[k][11] - udiff[k][11]) > 0.011)]
    oi_differs = [k for k in both if legacy[k][14] != udiff[k][14]]
    return {"date": d, "comparable": True, "legacy_rows": len(legacy), "udiff_rows": len(udiff),
            "in_both": len(both), "only_legacy": len(legacy - udiff.keys()),
            "only_udiff": len(udiff.keys() - legacy.keys()),
            "settle_differs": len(settle_differs), "open_interest_differs": len(oi_differs),
            "examples": [str(k) for k in settle_differs[:3]]}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", default="india")
    ap.add_argument("--start", default=None, help="YYYY-MM-DD (default 2012-01-01)")
    ap.add_argument("--end", default=None)
    ap.add_argument("--days", type=int, default=None, help="just the last N calendar days")
    ap.add_argument("--all-instruments", action="store_true",
                    help="keep stock futures and options too (about 7x the rows)")
    ap.add_argument("--reconcile", default=None, metavar="YYYY-MM-DD",
                    help="compare the two archive layouts for one day and print the result")
    a = ap.parse_args()
    if a.reconcile:
        out = reconcile(a.market, dt.date.fromisoformat(a.reconcile),
                        () if a.all_instruments else INDEX_INSTRUMENTS)
        for k, v in out.items():
            print(f"  {k}: {v}")
        return
    end = dt.date.fromisoformat(a.end) if a.end else dt.date.today()
    start = dt.date.fromisoformat(a.start) if a.start else (end - dt.timedelta(days=a.days) if a.days else FIRST_DAY)
    out = ingest(a.market, start, end, () if a.all_instruments else INDEX_INSTRUMENTS)
    print(f"  {out}")


if __name__ == "__main__":
    main()
