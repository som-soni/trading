"""Interest rates: each market's policy rate, its bill yields and its bond yields, with long history.

Stored in `index_series` (one row per series per date, the value in percent) under the market it
describes, so a trend can be read back for decades. The `rates` job refreshes them daily; a run only
writes a value that is new or has changed, and logs what moved.

    us     FRED (St. Louis Fed), daily, full history, re-read whole each run so revisions land:
           the effective Fed funds rate and the Fed's target range, the 3-month bill, and the 2-, 10-
           and 30-year Treasury constant-maturity yields.
    india  RBI's homepage "current rates" box, read daily: the policy repo rate, the 91/182/364-day
           T-bill cut-offs at the last auction, and the 5-, 10- and 30-year G-sec benchmark yields.
           RBI publishes no free machine-readable history, so:
             - the repo rate's history is REPO_CHANGES below, a hand-kept list of every change since
               2004 checked against RBI's policy announcements; the daily read extends it, and a run
               that sees a rate different from the last stored one records the change;
             - the 10-year yield's history before the daily reads is FRED's monthly series (OECD,
               from 2011), kept as its own series (IN_GSEC_10Y_M) so monthly averages never interleave
               with daily closes; `history()` joins the two;
             - T-bill and the other G-sec yields build up from the first daily read.

Yahoo's ^TNX / ^FVX (US10Y / US5Y in macro.py) stay as they are: they update the same evening, while
FRED's constant-maturity yields arrive a day later. They agree to a basis point or two.

    PYTHONPATH=. python3 -m swing_screener.marketdata.rates               # refresh every market
    PYTHONPATH=. python3 -m swing_screener.marketdata.rates --list        # what is stored
"""

import argparse
import datetime as dt
import html
import io
import logging
import re
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import pandas as pd

from . import db

logger = logging.getLogger(__name__)

FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}"
RBI_HOME = "https://www.rbi.org.in/"
TIMEOUT = 60
GSEC_TOLERANCE_YEARS = 2     # a listed G-sec stands for a tenor when its maturity is within this many years of it


@dataclass(frozen=True)
class Rate:
    key: str          # series name in index_series
    label: str
    short: str        # the table's / legend's label
    kind: str         # "policy" | "bill" | "bond"
    tenor: float      # years (0 for a policy rate); orders the table and the curve
    source: str       # "fred" | "rbi"
    source_id: str = ""   # FRED series id, or the RBI box's item
    step: bool = False    # a set rate (policy): drawn as steps, quoted with the date it last changed
    show: bool = True     # drawn on the chart by default (the rest are one click away in its legend)


RATES: dict[str, list[Rate]] = {
    "us": [
        Rate("US_FEDFUNDS", "Effective federal funds rate", "Fed funds (effective)", "policy", 0, "fred", "DFF", show=False),
        Rate("US_FED_UPPER", "Fed funds target range, upper bound", "Fed target (upper)", "policy", 0, "fred", "DFEDTARU", step=True),
        Rate("US_FED_LOWER", "Fed funds target range, lower bound", "Fed target (lower)", "policy", 0, "fred", "DFEDTARL", step=True, show=False),
        Rate("US_TBILL_3M", "3-month Treasury bill", "3-month T-bill", "bill", 0.25, "fred", "DGS3MO"),
        Rate("US_UST_2Y", "2-year Treasury yield", "2-year Treasury", "bond", 2, "fred", "DGS2"),
        Rate("US_UST_10Y", "10-year Treasury yield", "10-year Treasury", "bond", 10, "fred", "DGS10"),
        Rate("US_UST_30Y", "30-year Treasury yield", "30-year Treasury", "bond", 30, "fred", "DGS30", show=False),
    ],
    "india": [
        Rate("IN_REPO", "RBI policy repo rate", "RBI repo rate", "policy", 0, "rbi", "Policy Repo Rate", step=True),
        Rate("IN_TBILL_91D", "91-day T-bill (last auction cut-off)", "91-day T-bill", "bill", 0.25, "rbi", "91"),
        Rate("IN_TBILL_182D", "182-day T-bill (last auction cut-off)", "182-day T-bill", "bill", 0.5, "rbi", "182", show=False),
        Rate("IN_TBILL_364D", "364-day T-bill (last auction cut-off)", "364-day T-bill", "bill", 1, "rbi", "364", show=False),
        Rate("IN_GSEC_5Y", "5-year G-sec benchmark yield", "5-year G-sec", "bond", 5, "rbi", "5", show=False),
        Rate("IN_GSEC_10Y", "10-year G-sec benchmark yield", "10-year G-sec", "bond", 10, "rbi", "10"),
        Rate("IN_GSEC_30Y", "30-year G-sec benchmark yield", "30-year G-sec", "bond", 30, "rbi", "30", show=False),
    ],
}

# history joined in front of a series by `history()`: (market, series) -> (backfill series, FRED id)
BACKFILL = {("india", "IN_GSEC_10Y"): ("IN_GSEC_10Y_M", "INDIRLTLT01STM")}

# Every change to RBI's policy repo rate since 2004: (date effective, new rate %). Each row checked against
# RBI's own press release or policy statement and the effective-date column of RBI's Handbook of Statistics
# (policy rates table); where a release says "with immediate effect" and the Handbook gives the next day,
# the Handbook's date is used. Before 29 Oct 2004 RBI used the opposite names, so the first row (6% from
# 29 Mar 2004) is the rate then called "reverse repo" — the rate RBI lends at, today's repo rate. Popular
# third-party tables of this history omit the 2011 hikes and the 2012-13 cuts; do not copy from them. Add a
# row when the MPC changes the rate — the daily read records it anyway, but this list is what a rebuilt
# database starts from.
REPO_CHANGES: list[tuple[str, float]] = [
    ("2004-03-29", 6.00),
    ("2005-10-26", 6.25),
    ("2006-01-24", 6.50),
    ("2006-06-08", 6.75),
    ("2006-07-25", 7.00),
    ("2006-10-31", 7.25),
    ("2007-01-31", 7.50),
    ("2007-03-31", 7.75),
    ("2008-06-12", 8.00),
    ("2008-06-25", 8.50),
    ("2008-07-30", 9.00),
    ("2008-10-20", 8.00),
    ("2008-11-03", 7.50),
    ("2008-12-08", 6.50),
    ("2009-01-05", 5.50),
    ("2009-03-05", 5.00),
    ("2009-04-21", 4.75),
    ("2010-03-19", 5.00),
    ("2010-04-20", 5.25),
    ("2010-07-02", 5.50),
    ("2010-07-27", 5.75),
    ("2010-09-16", 6.00),
    ("2010-11-02", 6.25),
    ("2011-01-25", 6.50),
    ("2011-03-17", 6.75),
    ("2011-05-03", 7.25),
    ("2011-06-16", 7.50),
    ("2011-07-26", 8.00),
    ("2011-09-16", 8.25),
    ("2011-10-25", 8.50),
    ("2012-04-17", 8.00),
    ("2013-01-29", 7.75),
    ("2013-03-19", 7.50),
    ("2013-05-03", 7.25),
    ("2013-09-20", 7.50),
    ("2013-10-29", 7.75),
    ("2014-01-28", 8.00),
    ("2015-01-15", 7.75),
    ("2015-03-04", 7.50),
    ("2015-06-02", 7.25),
    ("2015-09-29", 6.75),
    ("2016-04-05", 6.50),
    ("2016-10-04", 6.25),
    ("2017-08-02", 6.00),
    ("2018-06-06", 6.25),
    ("2018-08-01", 6.50),
    ("2019-02-07", 6.25),
    ("2019-04-04", 6.00),
    ("2019-06-06", 5.75),
    ("2019-08-07", 5.40),
    ("2019-10-04", 5.15),
    ("2020-03-27", 4.40),
    ("2020-05-22", 4.00),
    ("2022-05-04", 4.40),
    ("2022-06-08", 4.90),
    ("2022-08-05", 5.40),
    ("2022-09-30", 5.90),
    ("2022-12-07", 6.25),
    ("2023-02-08", 6.50),
    ("2025-02-07", 6.25),
    ("2025-04-09", 6.00),
    ("2025-06-06", 5.50),
    ("2025-12-05", 5.25),
    ("2026-10-07", 5.50),
]


def _upsert(market: str, key: str, s: pd.Series) -> int:
    """Write the series' values that are new or different from what is stored. -> rows written."""
    s = s.dropna().round(4)   # stored to 4 decimals, so compare at 4 decimals
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


def _last(market: str, key: str, before: dt.date | None = None) -> tuple[dt.date, float] | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s AND date < %s "
                    "ORDER BY date DESC LIMIT 1", (market, key, before or dt.date(9999, 1, 1)))
        r = cur.fetchone()
    return (r[0], float(r[1])) if r else None


def fred(series_id: str) -> pd.Series:
    """A FRED series' full history (FRED writes "." for a holiday)."""
    import requests
    r = requests.get(FRED_CSV.format(id=series_id), timeout=TIMEOUT)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if df.shape[1] < 2:
        raise ValueError(f"FRED {series_id}: unexpected response")
    s = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    s.index = pd.to_datetime(df.iloc[:, 0])
    return s.dropna().sort_index()


def rbi_current() -> dict:
    """Parse RBI's homepage rates box. -> {"policy": {name: %}, "tbill": {days: %}, "gsec": [(coupon, maturity
    year, yield %)], "as_on": date of the market rates}."""
    import requests
    r = requests.get(RBI_HOME, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S)
    t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t)))
    policy = {m.group(1).strip(): float(m.group(2)) for m in
              re.finditer(r"(Policy Repo Rate|Standing Deposit Facility Rate|Marginal Standing Facility Rate|Bank Rate) : (\d+\.\d+)%", t)}
    tbill = {m.group(1): float(m.group(2)) for m in re.finditer(r"(\d{2,3}) day T-bills : (\d+\.\d+)%", t)}
    gsec = [(float(m.group(1)), int(m.group(2)), float(m.group(3))) for m in
            re.finditer(r"(\d+\.\d+)% GS (\d{4}) : (\d+\.\d+)%", t)]
    on = re.search(r"# as on (\w+ \d{1,2}, \d{4})", t) or re.search(r"as on (\w+ \d{1,2}, \d{4})", t)
    as_on = dt.datetime.strptime(on.group(1), "%B %d, %Y").date() if on else None
    if "Policy Repo Rate" not in policy:
        raise ValueError("RBI homepage: policy repo rate not found (page layout changed?)")
    return {"policy": policy, "tbill": tbill, "gsec": gsec, "as_on": as_on}


def _gsec_for(gsec: list, tenor: float, year: int) -> float | None:
    """The listed benchmark whose maturity is nearest `tenor` years away (within GSEC_TOLERANCE_YEARS)."""
    best = min(gsec, key=lambda g: abs(g[1] - year - tenor), default=None)
    return best[2] if best and abs(best[1] - year - tenor) <= GSEC_TOLERANCE_YEARS else None


def _step_series(changes: list[tuple[str, float]], end: dt.date) -> pd.Series:
    """A set rate as a business-day series from its first change to `end`."""
    if not changes:
        return pd.Series(dtype=float)
    ch = pd.Series([v for _, v in changes], index=pd.to_datetime([d for d, _ in changes])).sort_index()
    days = pd.bdate_range(ch.index[0], end)
    return ch.reindex(ch.index.union(days)).ffill().reindex(days)


def _record(market: str, key: str, value: float, on: dt.date, changes: list) -> int:
    """A daily RBI read: fill business days since the last stored value with that value (a rate holds until
    it is seen to change), then store today's. Logs a change."""
    last = _last(market, key, before=on)
    n = 0
    if last:
        gap = pd.bdate_range(last[0] + dt.timedelta(days=1), on - dt.timedelta(days=1))
        n += _upsert(market, key, pd.Series(last[1], index=gap))
        if abs(last[1] - value) > 1e-6:
            changes.append(f"{key} {last[1]:g}% → {value:g}% (last stored {last[0]})")
    return n + _upsert(market, key, pd.Series([value], index=pd.to_datetime([on])))


def refresh(market: str) -> dict:
    """Fetch and store the market's rates. -> {"written": {key: rows}, "failed": {key: error}, "changes": [text]}."""
    from . import index_data
    index_data.init_schema()
    written, failed, changes = {}, {}, []
    rates = RATES.get(market, [])
    for r in [r for r in rates if r.source == "fred"]:
        try:
            s = fred(r.source_id)
            last = _last(market, r.key)
            written[r.key] = _upsert(market, r.key, s)
            if r.step and last and abs(float(s.iloc[-1]) - last[1]) > 1e-6:
                changes.append(f"{r.key} {last[1]:g}% → {float(s.iloc[-1]):g}%")
        except Exception as e:  # noqa: BLE001 — one series failing must not stop the rest
            failed[r.key] = str(e)[:200]
            logger.warning("rates %s %s: %s", market, r.key, e)
    for (mk, key), (bkey, fid) in BACKFILL.items():
        if mk == market:
            try:
                written[bkey] = _upsert(market, bkey, fred(fid))
            except Exception as e:  # noqa: BLE001
                failed[bkey] = str(e)[:200]
    rbi = [r for r in rates if r.source == "rbi"]
    if rbi:
        today = dt.datetime.now(ZoneInfo("Asia/Kolkata")).date()
        repo = next((r for r in rbi if r.key == "IN_REPO"), None)
        if repo and REPO_CHANGES:
            # the hand-kept list is authoritative up to its last change (so a correction lands); after that the
            # daily reads carry the rate forward
            last_change = max(pd.Timestamp(d) for d, _ in REPO_CHANGES).date()
            written[repo.key] = _upsert(market, repo.key, _step_series(REPO_CHANGES, last_change))
        try:
            cur = rbi_current()
            on = cur["as_on"] or today
            for r in rbi:
                if r.kind == "policy":
                    v, d = cur["policy"].get(r.source_id), today
                elif r.kind == "bill":
                    v, d = cur["tbill"].get(r.source_id), on
                else:
                    v, d = _gsec_for(cur["gsec"], r.tenor, on.year), on
                if v is None:
                    failed[r.key] = "not on RBI's homepage"
                    continue
                written[r.key] = written.get(r.key, 0) + _record(market, r.key, v, d, changes)
        except Exception as e:  # noqa: BLE001
            for r in rbi:
                failed.setdefault(r.key, str(e)[:200])
            logger.warning("rates %s RBI: %s", market, e)
    for c in changes:
        logger.info("rates %s: %s", market, c)
    return {"written": written, "failed": failed, "changes": changes}


def history(market: str, key: str) -> pd.Series:
    """A stored rate's full history, with its BACKFILL joined in front of its first stored value."""
    def load(k):
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT date, close FROM index_series WHERE market=%s AND series=%s ORDER BY date", (market, k))
            got = cur.fetchall()
        return pd.Series([float(c) for _, c in got], index=pd.to_datetime([d for d, _ in got]), dtype=float)
    s = load(key)
    if (market, key) in BACKFILL:
        b = load(BACKFILL[(market, key)][0])
        s = pd.concat([b[b.index < s.index.min()] if len(s) else b, s])
    return s


def _change(s: pd.Series, days: int) -> float | None:
    """Change in basis points over `days` calendar days (the value on or before then)."""
    if s.empty:
        return None
    then = s[s.index <= s.index[-1] - pd.Timedelta(days=days)]
    return None if then.empty else float((s.iloc[-1] - then.iloc[-1]) * 100)


def summary(market: str) -> list[dict]:
    """Each stored rate: last value and date, 1-month / 1-year / 5-year changes (bp), when a set rate last
    changed, and its history for a chart as WEEKLY points — each week's last value, labelled with the week's
    Friday (today for the week in progress). One grid for every series, because the chart spaces points by
    count, not by date: mixing weekly and daily stretches the daily stretch, and series with weekend values
    (Fed funds) would add points the others lack."""
    today = pd.Timestamp(dt.date.today())
    out = []
    for r in RATES.get(market, []):
        s = history(market, r.key)
        if s.empty:
            continue
        weekly = s.resample("W-FRI").last().dropna()
        weekly.index = weekly.index.where(weekly.index <= today, today)
        since = None
        if r.step:
            moved = s[s.diff().fillna(0).abs() > 1e-6]
            if len(moved):
                since = {"date": str(moved.index[-1].date()), "from": float(s[s.index < moved.index[-1]].iloc[-1]),
                         "to": float(moved.iloc[-1])}
        out.append({"key": r.key, "label": r.label, "short": r.short, "kind": r.kind, "tenor": r.tenor, "step": r.step,
                    "show": r.show, "source": "FRED" if r.source == "fred" else "RBI", "first": str(s.index[0].date()),
                    "date": str(s.index[-1].date()), "value": float(s.iloc[-1]),
                    "m1": _change(s, 30), "y1": _change(s, 365), "y5": _change(s, 5 * 365), "since": since,
                    "points": [[d.strftime("%Y-%m-%d"), round(float(v), 4)] for d, v in weekly.items()]})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh policy rates and bill / bond yields")
    ap.add_argument("--market", choices=list(RATES), help="one market (default: all)")
    ap.add_argument("--list", action="store_true", help="print what is stored instead of fetching")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for mk in [a.market] if a.market else list(RATES):
        if a.list:
            for x in summary(mk):
                m1 = f"{x['m1']:+.0f}bp" if x["m1"] is not None else "—"
                print(f"{mk:6s} {x['key']:14s} {x['value']:6.2f}%  {m1:>7s}  {x['first']} → {x['date']}  {x['label']}")
        else:
            print(mk, refresh(mk))


if __name__ == "__main__":
    main()
