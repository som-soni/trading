"""India index history from the index providers themselves, for the indices Yahoo does not carry.

Yahoo has no series at all for Nifty Midcap 150, Smallcap 100, Microcap 250, Total Market, Oil & Gas,
Consumer Durables, India Defence, BSE MidCap or BSE SmallCap, and only the last bar or two for Nifty
Private Bank, Healthcare, Media, Services Sector and Commodities (checked Oct 2026). The index owners
publish full daily history:

* **NSE Indices** (niftyindices.com, the Historical Data report): `POST /BackPage/getHistoricaldatatabletoString`
  with a `cinfo` string naming the index and a `DD-Mon-YYYY` date range. It wants browser-like headers
  (a desktop User-Agent, the report page as Referer). The page limits a request to one year, but the
  endpoint does not: one request returns an index's whole history, from Apr 2005 for most indices
  (Jan 2004 for Smallcap 100 and Commodities, Jun 1999 for Services Sector, Apr 2018 for India Defence).
  The oldest years carry a close only (open, high and low come back as "-"); those bars store the
  close in all four fields.
* **BSE** (api.bseindia.com, the Index Archive page): `GET /BseIndiaAPI/api/IndexArchDailyPAR/w` with the
  index *code* (`BSEMID`, `BSESML`), `DD/MM/YYYY` dates and the bseindia.com Referer — without them the
  CDN answers "Access Denied". History starts Apr 2003; since Jan 2026 BSE publishes the close only
  (open = high = low = close), so recent BSE bars have no range.

Neither source has a volume for an index; it is stored as 0, as Yahoo's NSE indices are.

The tickers are this app's own, prefixed by source (`NSE:`, `BSE:`) like `AMFI:` series in
`index_series`, so a Yahoo symbol can never be mistaken for one. `RoutedProvider` sends those to this
module and everything else to Yahoo; the daily `prices` refresh and `backfill` both use it, and
`instruments.py` / the market config decide which of these indices are stored.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import time

import pandas as pd
import requests

from ..providers import DataProvider, YFinanceProvider
from ..providers.yfinance_provider import _COLUMNS, _drop_incomplete_bar

logger = logging.getLogger(__name__)

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
       "Chrome/129.0 Safari/537.36")
NSE_URL = "https://www.niftyindices.com/BackPage/getHistoricaldatatabletoString"
NSE_HEADERS = {"User-Agent": _UA, "Accept": "application/json, text/javascript, */*; q=0.01",
               "Content-Type": "application/json; charset=utf-8", "X-Requested-With": "XMLHttpRequest",
               "Origin": "https://www.niftyindices.com", "Referer": "https://www.niftyindices.com/reports/historical-data"}
BSE_URL = "https://api.bseindia.com/BseIndiaAPI/api/IndexArchDailyPAR/w"
BSE_HEADERS = {"User-Agent": _UA, "Accept": "application/json, text/plain, */*",
               "Origin": "https://www.bseindia.com", "Referer": "https://www.bseindia.com/"}
FIRST_DATE = dt.date(1990, 1, 1)   # before any index here starts: a "max" request asks from this date
TIMEOUT_S = 120

# ticker -> (the "trading" name niftyindices.com's IndexMapping.json gives the index, its long name).
# The endpoint wants both: `name` is the trading name upper-cased, `indexName` the long name.
NSE_INDICES = {
    "NSE:NIFTY_MIDCAP_150": ("NIFTY MIDCAP 150", "Nifty Midcap 150"),
    "NSE:NIFTY_SMALLCAP_100": ("NIFTY SMLCAP 100", "Nifty Smallcap 100"),
    "NSE:NIFTY_MICROCAP_250": ("NIFTY MICROCAP250", "Nifty Microcap 250"),
    "NSE:NIFTY_TOTAL_MARKET": ("NIFTY TOTAL MKT", "Nifty Total Market"),
    "NSE:NIFTY_PRIVATE_BANK": ("NIFTY PVT BANK", "Nifty Private Bank"),
    "NSE:NIFTY_HEALTHCARE": ("NIFTY HEALTHCARE", "Nifty Healthcare"),
    "NSE:NIFTY_MEDIA": ("NIFTY MEDIA", "Nifty Media"),
    "NSE:NIFTY_OIL_GAS": ("NIFTY OIL AND GAS", "Nifty Oil & Gas"),
    "NSE:NIFTY_CONSUMER_DURABLES": ("NIFTY CONSR DURBL", "Nifty Consumer Durables"),
    "NSE:NIFTY_SERVICES_SECTOR": ("NIFTY SERV SECTOR", "Nifty Services Sector"),
    "NSE:NIFTY_COMMODITIES": ("NIFTY COMMODITIES", "Nifty Commodities"),
    "NSE:NIFTY_INDIA_DEFENCE": ("NIFTY IND DEFENCE", "Nifty India Defence"),
}
# ticker -> BSE's index code (its FillddlIndex list)
BSE_INDICES = {
    "BSE:MIDCAP": "BSEMID",
    "BSE:SMALLCAP": "BSESML",
}


def is_official(symbol: str) -> bool:
    return symbol in NSE_INDICES or symbol in BSE_INDICES


def _frame(dates, o, h, l, c) -> pd.DataFrame:
    df = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=pd.DatetimeIndex(dates).normalize())
    df = df.apply(pd.to_numeric, errors="coerce")
    for col in ("open", "high", "low"):        # close-only years: the close stands in for the range
        df[col] = df[col].where(df[col] > 0, df["close"])
    df["volume"] = 0
    df = df.dropna(subset=["close"])
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return _drop_incomplete_bar(df[_COLUMNS])


def fetch_nse(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    name, long_name = NSE_INDICES[symbol]
    cinfo = "{'name':'%s','startDate':'%s','endDate':'%s','indexName':'%s'}" % (
        name, start.strftime("%d-%b-%Y"), end.strftime("%d-%b-%Y"), long_name)
    r = requests.post(NSE_URL, headers=NSE_HEADERS, data=json.dumps({"cinfo": cinfo}), timeout=TIMEOUT_S)
    r.raise_for_status()
    if not r.text.lstrip().startswith(("[", "{")):   # now and then the site answers with its HTML shell; retried
        raise ValueError(f"niftyindices.com sent a page, not data ({len(r.text)} bytes)")
    rows = r.json()
    if isinstance(rows, dict):                 # the old ASP.NET form wrapped the list as {"d": "<json>"}
        rows = json.loads(rows.get("d") or "[]")
    if not rows:
        return pd.DataFrame(columns=_COLUMNS)
    num = lambda k: [str(x.get(k, "")).replace(",", "") for x in rows]  # noqa: E731
    dates = pd.to_datetime([x["HistoricalDate"] for x in rows], format="%d %b %Y")
    return _frame(dates, num("OPEN"), num("HIGH"), num("LOW"), num("CLOSE"))


def fetch_bse(symbol: str, start: dt.date, end: dt.date) -> pd.DataFrame:
    params = {"fmdt": start.strftime("%d/%m/%Y"), "index": BSE_INDICES[symbol], "period": "D",
              "todt": end.strftime("%d/%m/%Y")}
    r = requests.get(BSE_URL, headers=BSE_HEADERS, params=params, timeout=TIMEOUT_S)
    r.raise_for_status()
    rows = r.json().get("Table") or []
    if not rows:
        return pd.DataFrame(columns=_COLUMNS)
    col = lambda k: [x.get(k) for x in rows]  # noqa: E731
    return _frame(pd.to_datetime(col("tdate")), col("I_open"), col("I_high"), col("I_low"), col("I_close"))


def fetch(symbol: str, start: dt.date, end: dt.date | None = None) -> pd.DataFrame:
    end = end or dt.date.today()
    return (fetch_nse if symbol in NSE_INDICES else fetch_bse)(symbol, start, end)


class OfficialIndexProvider(DataProvider):
    """Daily bars for the `NSE:` / `BSE:` tickers. Each symbol is one request, whatever the range."""

    def __init__(self, retries: int = 3, pause_sec: float = 1.0):
        self.retries = retries
        self.pause_sec = pause_sec

    def get_daily_bars(self, symbol: str, lookback_days: int, start_after: pd.Timestamp | None = None,
                       period: str | None = None) -> pd.DataFrame:
        if period == "max":
            start = FIRST_DATE
        elif start_after is not None:
            start = (start_after + pd.Timedelta(days=1)).date()
        else:  # calendar days, padded for weekends and holidays like the Yahoo provider
            start = dt.date.today() - dt.timedelta(days=max(lookback_days + 30, 400))
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                return fetch(symbol, start)
            except Exception as e:  # noqa: BLE001 - retried, then surfaced
                last_err = e
                logger.warning("%s: attempt %d failed: %s", symbol, attempt + 1, e)
                time.sleep(self.pause_sec * (attempt + 1) * 5)
        raise last_err

    def get_many_daily_bars(self, symbols: list[str], lookback_days: int, period: str | None = None,
                            **_: object) -> dict[str, pd.DataFrame]:
        out: dict[str, pd.DataFrame] = {}
        for sym in dict.fromkeys(symbols):
            try:
                df = self.get_daily_bars(sym, lookback_days, period=period)
            except Exception as e:  # noqa: BLE001 - a dead source shows as a failed symbol in the run log
                logger.warning("%s: no data from the index provider (%s)", sym, e)
                continue
            if not df.empty:
                out[sym] = df
            time.sleep(self.pause_sec)
        return out


class RoutedProvider(DataProvider):
    """Yahoo for everything except the `NSE:` / `BSE:` index tickers, which go to their index provider.
    Keyword arguments (Yahoo's `period`, `threads`, `fallback`, `batch_size`) pass through; the index
    provider honours `period="max"` and ignores the rest."""

    def __init__(self, yahoo: YFinanceProvider | None = None, official: OfficialIndexProvider | None = None):
        self.yahoo = yahoo or YFinanceProvider()
        self.official = official or OfficialIndexProvider()

    def get_daily_bars(self, symbol: str, lookback_days: int, start_after: pd.Timestamp | None = None) -> pd.DataFrame:
        src = self.official if is_official(symbol) else self.yahoo
        return src.get_daily_bars(symbol, lookback_days, start_after)

    def get_many_daily_bars(self, symbols: list[str], lookback_days: int, **kw) -> dict[str, pd.DataFrame]:
        ours = [s for s in symbols if is_official(s)]
        rest = [s for s in symbols if not is_official(s)]
        out = self.yahoo.get_many_daily_bars(rest, lookback_days, **kw) if rest else {}
        if ours:
            out.update(self.official.get_many_daily_bars(ours, lookback_days, period=kw.get("period")))
        return out
