"""Complete the latest sessions from an exchange's official end-of-day file.

The price provider (Yahoo) publishes many Indian stocks' daily bars late: the 18:30 IST run regularly ends
with the day only partly loaded (23 Oct 2026: 1,318 of ~3,350 stocks, still short the next morning), so
breadth, sectors and screens sat a session behind. NSE publishes its cash-market bhavcopy the same evening:
every security that traded, with open, high, low, close and volume, in one file. After the provider pull,
`fill` takes the recent sessions the store has only partly, reads that day's file and adds the bars the
provider has not delivered yet. A bar the provider already stored is never overwritten, and the provider's
next pull starts after the filled date.

The file's prices are as traded. The provider's history is adjusted for later splits and bonuses, so the
two agree for the latest bar (checked: RELIANCE 23 Oct 2026 identical in OHLC and volume); on the ex-date of
a split the new bar is on the new scale, which `marketdata/splits.py` repairs as it does for the provider.

Sources (MarketConfig.eod_file):
  nse_cm   NSE's UDiFF cash-market bhavcopy (nsearchives.nseindia.com/content/cm/), equity series.

    PYTHONPATH=. python3 -m swing_screener.marketdata.eod_files --market india            # fill what is missing
    PYTHONPATH=. python3 -m swing_screener.marketdata.eod_files --market india --day 2026-10-23
"""

import argparse
import datetime as dt
import logging

import pandas as pd

from ..config import MARKETS
from . import cache, db, freshness, universe

logger = logging.getLogger(__name__)

LOOKBACK_DAYS = 10        # calendar days back from the expected session that are checked for gaps
# NSE equity series that are ordinary listed shares (EQ main board, BE/BZ trade-for-trade, SM/ST SME)
NSE_SERIES = ("EQ", "BE", "BZ", "SM", "ST")


def nse_cm_url(d: dt.date) -> str:
    from .derivatives import ARCHIVE
    return f"{ARCHIVE}/content/cm/BhavCopy_NSE_CM_0_0_0_{d:%Y%m%d}_F_0000.csv.zip"


def nse_cm_day(d: dt.date, suffix: str = ".NS") -> pd.DataFrame:
    """One session's equity bars from NSE's bhavcopy, indexed by the stored symbol. Empty when the day has
    no file yet (not published, a holiday, a weekend)."""
    from .derivatives import _download
    df = _download(nse_cm_url(d))
    if df is None or df.empty:
        return pd.DataFrame()
    df = df.rename(columns=lambda c: str(c).strip())
    df = df[df["SctySrs"].astype(str).str.strip().isin(NSE_SERIES)]
    df = df[pd.to_datetime(df["TradDt"]).dt.date == d]
    # one row per symbol; EQ first if a symbol is listed in two series that day
    df = df.assign(_eq=df["SctySrs"].astype(str).str.strip() != "EQ").sort_values("_eq").drop_duplicates("TckrSymb")
    out = pd.DataFrame({
        "open": pd.to_numeric(df["OpnPric"], errors="coerce").values,
        "high": pd.to_numeric(df["HghPric"], errors="coerce").values,
        "low": pd.to_numeric(df["LwPric"], errors="coerce").values,
        "close": pd.to_numeric(df["ClsPric"], errors="coerce").values,
        "volume": pd.to_numeric(df["TtlTradgVol"], errors="coerce").values,
    }, index=(df["TckrSymb"].astype(str).str.strip() + suffix).values)
    return out.dropna(subset=["open", "high", "low", "close"])


def _missing_days(market: str, symbols: set[str]) -> list[dt.date]:
    """Weekdays from LOOKBACK_DAYS before the expected session up to it whose stored bars cover less of the
    universe than a normal session does."""
    expected = freshness.expected_session(market)
    start = expected - dt.timedelta(days=LOOKBACK_DAYS)
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT date, count(*) FROM prices WHERE market=%s AND date BETWEEN %s AND %s AND symbol = ANY(%s)
                       GROUP BY date""", (market, start - dt.timedelta(days=30), expected, list(symbols)))
        counts = dict(cur.fetchall())
    full = sorted(counts.values())[-10:]
    normal = full[len(full) // 2] if full else len(symbols)
    days = [start + dt.timedelta(days=i) for i in range((expected - start).days + 1)]
    return [d for d in days if d.weekday() < 5 and counts.get(d, 0) < freshness.COMPLETE_SHARE * normal]


def fill(market: str, days: list[dt.date] | None = None) -> dict:
    """Add the bars the provider has not delivered for recent, partly loaded sessions. Returns a summary."""
    cfg = MARKETS[market]
    if cfg.eod_file != "nse_cm":
        return {"source": None, "days": [], "added": 0}
    symbols = set(universe.load_universe(market))
    days = days if days is not None else _missing_days(market, symbols)
    added, done, absent = 0, [], []
    for d in days:
        bars = nse_cm_day(d, cfg.symbol_suffix)
        if bars.empty:
            absent.append(d.isoformat())
            continue
        bars = bars[bars.index.isin(symbols)]
        new = {sym: pd.DataFrame([row], index=pd.DatetimeIndex([pd.Timestamp(d)], name="Date"))
               for sym, row in bars.iterrows()}
        n = 0
        syms = list(new)
        for i in range(0, len(syms), 400):
            n += cache.append_bars(market, {s: new[s] for s in syms[i:i + 400]})
        added += n
        done.append({"day": d.isoformat(), "in_file": len(bars), "added": n})
        logger.info("%s %s: %d stocks in the file, %d bars added", cfg.eod_file, d, len(bars), n)
    return {"source": cfg.eod_file, "days": done, "absent": absent, "added": added}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--day", action="append", help="YYYY-MM-DD (repeatable); default: every partly loaded recent session")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    days = [dt.date.fromisoformat(x) for x in a.day] if a.day else None
    print(fill(a.market, days))


if __name__ == "__main__":
    main()
