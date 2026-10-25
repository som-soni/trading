"""Fortnightly FPI net equity investment by sector, India only — NSDL's FPI Monitor.

NSDL publishes one static HTML report per fortnight (the 15th and month-end) back to January 2012:
"Fortnightly Sector-wise FPI Investment data". There is no API and no predictable URL — file names
carry typos and mix "Jun"/"June", "Jul"/"July" — so the report list is read from NSDL's own selection
page (its `ddlfortnighly` <select>), and each report's date is taken from its own last "AUC as on
<date>" header, never from the file name or the option label (which are wrong in places, e.g. the
Feb 28 2023 report is listed as "Feb 28, 2022").

Each report's table has blocks: AUC at the previous fortnight, net investment for the previous
fortnight (absent before 2013), net investment for THIS fortnight, AUC now — each in ₹ crore and
US$ million, split Equity / Debt / Hybrid / Mutual Funds / AIF. Stored is this fortnight's net
**Equity** column in ₹ crore (direct equity; mutual-fund-unit equity is a separate column, left out).
Sector names are kept as NSDL prints them (footnote digits stripped); NSDL changed taxonomy over the
years (about 35 BSE-based sectors through 2020, 24 NSE-style ones since), so old and new names do
not line up and are not mapped onto each other. Sub-rows ("2a Banks") and the Grand Total are skipped.

FPI only: NSDL tracks foreign portfolio investors' custody holdings; no public source splits
domestic institutions' (DII) flows by sector.

NSDL's server resets connections that send a generic or library-default User-Agent, so requests
identify this app honestly. A report that fails to fetch or parse is logged and skipped, never fatal
(the same tolerance as the RBI scrape in rates.py); it is tried again on the next run.

Stored in its own table `fpi_sector_flows` (2-D data, so not `index_series`).

    PYTHONPATH=. python3 -m swing_screener.marketdata.fpi_sectors            # backfill missing, re-read latest
    PYTHONPATH=. python3 -m swing_screener.marketdata.fpi_sectors --list     # what is stored
"""

import argparse
import datetime as dt
import io
import logging
import re
import time

import pandas as pd

from . import db

logger = logging.getLogger(__name__)

MARKET = "india"        # NSDL's FPI Monitor covers Indian securities only
NSDL_BASE = "https://www.fpi.nsdl.co.in/web/"
SELECTION = NSDL_BASE + "Reports/FPI_Fortnightly_Selection.aspx"
HEADERS = {"User-Agent": "swing-screener/1.0 (personal research)"}
TIMEOUT = 30
REREAD_LATEST = 2       # re-read the newest reports on every run: NSDL occasionally revises a fortnight
PAUSE_S = 0.5           # between report fetches during a backfill — a static site, but no need to hammer it

SCHEMA = """
CREATE TABLE IF NOT EXISTS fpi_sector_flows (
    fortnight_end DATE NOT NULL,
    sector TEXT NOT NULL,
    equity_net NUMERIC,          -- net FPI equity investment that fortnight, ₹ crore
    source TEXT NOT NULL,        -- the NSDL report's file name: which reports are already stored
    PRIMARY KEY (fortnight_end, sector)
);
CREATE INDEX IF NOT EXISTS fpi_sector_flows_source ON fpi_sector_flows (source);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _get(url: str) -> str:
    import requests
    r = requests.get(url, timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    if r.content[:2] in (b"\xff\xfe", b"\xfe\xff"):   # some 2015-2019 reports are saved as UTF-16
        return r.content.decode("utf-16")
    return r.text


def reports() -> list[tuple[str, str]]:
    """Every report NSDL lists, newest first. -> [(url, option label)]."""
    html = _get(SELECTION)
    opts = re.findall(r'<option[^>]*value="([^"]*StaticReports[^"]*)"[^>]*>([^<]*)</option>', html)
    return [(NSDL_BASE + v.lstrip("~/"), re.sub(r"\s+", " ", label).strip()) for v, label in opts]


def _num(v) -> float | None:
    s = str(v).replace(",", "").replace("\xa0", "").strip()
    if s in ("", "-", "nan", "NaN"):
        return None
    if s.startswith("(") and s.endswith(")"):
        s = "-" + s[1:-1]
    try:
        return float(s)
    except ValueError:
        return None


def parse(html: str) -> tuple[dt.date, dict[str, float]]:
    """One report -> (fortnight end, {sector: net equity ₹ crore}). Raises ValueError if the layout is not recognised."""
    df = pd.read_html(io.StringIO(html), header=None)[0]
    # header rows run down to the one that labels the sector column
    hdr_end = next((i for i in range(min(8, len(df))) if str(df.iat[i, 1]).strip().lower() == "sectors"), None)
    if hdr_end is None:
        raise ValueError("no 'Sectors' header row")
    # the block row ("AUC as on …", "Net Investment …") is usually the first, but some reports lead with a blank row
    top = next((i for i in range(hdr_end) if df.iloc[i].astype(str).str.contains("AUC as on").any()), 0)
    block = [re.sub(r"\s+", " ", str(x)).strip() for x in df.iloc[top]]
    ccy = [re.sub(r"\s+", " ", str(x)).strip().upper() for x in df.iloc[top + 1]]
    sub = [re.sub(r"\s+", " ", str(x)).strip() for x in df.iloc[hdr_end]]
    aucs = [b for b in block if b.startswith("AUC as on")]
    if not aucs:
        raise ValueError("no 'AUC as on' header")
    end = pd.to_datetime(aucs[-1].removeprefix("AUC as on").strip()).date()
    nets = [b for b in dict.fromkeys(block) if b.startswith("Net Investment")]
    if not nets:
        raise ValueError("no 'Net Investment' block")
    col = next((j for j in range(len(block)) if block[j] == nets[-1] and "INR" in ccy[j] and sub[j] == "Equity"), None)
    if col is None:
        raise ValueError(f"no INR Equity column under '{nets[-1]}'")
    out: dict[str, float] = {}
    for i in range(hdr_end + 1, len(df)):
        if not re.fullmatch(r"\d+", str(df.iat[i, 0]).strip()):
            continue    # sub-rows ("2a", "32 b"), the Grand Total, footnotes
        name = re.sub(r"\d+$", "", re.sub(r"\s+", " ", str(df.iat[i, 1]))).strip()
        v = _num(df.iat[i, col])
        if name and v is not None:
            out[name] = v
    if not out:
        raise ValueError("no sector rows")
    return end, out


def fetch(url: str) -> tuple[dt.date, dict[str, float]]:
    """One fortnight's report -> (fortnight end, {sector: net equity ₹ crore})."""
    return parse(_get(url))


def _stored_sources() -> set[str]:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT DISTINCT source FROM fpi_sector_flows")
        return {s for (s,) in cur.fetchall()}


def refresh(market: str = "india", progress=None) -> dict:
    """Fetch every listed report not yet stored, and re-read the newest few.
    -> {"written": fortnights stored, "rows": sector rows, "newest": date|None, "failed": {report: error}}."""
    out = {"written": 0, "rows": 0, "newest": None, "failed": {}}
    if market != MARKET:
        return out
    init_schema()
    try:
        listed = reports()
    except Exception as e:  # noqa: BLE001 — a scraped page: a failed run is recorded, not fatal
        logger.warning("fpi_sectors: report list failed: %s", e)
        out["failed"]["list"] = str(e)[:200]
        return out
    have = _stored_sources()
    todo = [(u, lbl) for k, (u, lbl) in enumerate(listed) if k < REREAD_LATEST or u.rsplit("/", 1)[-1] not in have]
    for n, (url, label) in enumerate(todo):
        name = url.rsplit("/", 1)[-1]
        if progress:
            progress(f"reading NSDL reports: {n + 1:,}/{len(todo):,}", done=n, total=len(todo))
        try:
            end, got = fetch(url)
        except Exception as e:  # noqa: BLE001
            logger.warning("fpi_sectors: %s (%s) failed: %s", name, label, e)
            out["failed"][name] = str(e)[:200]
            continue
        with db.get_connection().cursor() as cur:  # replace the fortnight whole: a revised report may rename a sector
            cur.execute("DELETE FROM fpi_sector_flows WHERE fortnight_end = %s OR source = %s", (end, name))
        db.execute_values("INSERT INTO fpi_sector_flows (fortnight_end, sector, equity_net, source) VALUES %s",
                          [(end, s, round(v, 2), name) for s, v in got.items()])
        out["written"] += 1
        out["rows"] += len(got)
        out["newest"] = max(out["newest"] or end, end)
        logger.info("fpi_sectors: %s -> %s, %d sectors", name, end, len(got))
        if n + 1 < len(todo):
            time.sleep(PAUSE_S)
    return out


def summary(fortnights: int = 24) -> dict:
    """The last `fortnights` fortnights as a sector x fortnight matrix of net equity ₹ crore, rows sorted
    by the cumulative last 12 months (24 fortnights) — largest inflow first. Sectors are those in the
    newest report (NSDL's current taxonomy); a cell is None where that sector had no row."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT to_regclass('fpi_sector_flows')")
        if cur.fetchone()[0] is None:
            return {"fortnights": [], "sectors": [], "values": [], "cum12m": [], "asof": None}
        cur.execute("SELECT DISTINCT fortnight_end FROM fpi_sector_flows ORDER BY fortnight_end DESC LIMIT %s",
                    (max(fortnights, 24),))
        ends = sorted(d for (d,) in cur.fetchall())
        if not ends:
            return {"fortnights": [], "sectors": [], "values": [], "cum12m": [], "asof": None}
        cur.execute("SELECT fortnight_end, sector, equity_net FROM fpi_sector_flows WHERE fortnight_end >= %s", (ends[0],))
        rows = cur.fetchall()
    df = pd.DataFrame(rows, columns=["d", "sector", "v"])
    df["v"] = df["v"].astype(float)
    m = df.pivot(index="sector", columns="d", values="v")
    m = m.loc[m[ends[-1]].notna()]                    # current taxonomy only
    cum = m[ends[-24:]].sum(axis=1, min_count=1)      # last 12 months = 24 fortnights
    m = m.loc[cum.sort_values(ascending=False).index]
    shown = ends[-fortnights:]
    return {"fortnights": [str(d) for d in shown], "sectors": list(m.index),
            "values": [[None if pd.isna(v) else round(float(v), 2) for v in m.loc[s, shown]] for s in m.index],
            "cum12m": [round(float(cum[s]), 2) for s in m.index],
            "cum_from": str(ends[-24:][0]), "asof": str(ends[-1])}


def main() -> None:
    ap = argparse.ArgumentParser(description="Refresh NSDL fortnightly sector-wise FPI net equity investment (India)")
    ap.add_argument("--list", action="store_true", help="print what is stored instead of fetching")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.list:
        init_schema()
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT min(fortnight_end), max(fortnight_end), count(DISTINCT fortnight_end), count(*) FROM fpi_sector_flows")
            lo, hi, n, rows = cur.fetchone()
        print(f"india  fpi_sector_flows  {n} fortnights  {rows} rows  {lo} -> {hi}")
        s = summary()
        for name, c, v in zip(s["sectors"], s["cum12m"], s["values"]):
            print(f"  {name:40s} 12m {c:>12,.0f} cr   latest {v[-1] if v[-1] is not None else float('nan'):>10,.0f}")
    else:
        r = refresh()
        print({**r, "failed": len(r["failed"])})
        for k, e in r["failed"].items():
            print(f"  failed {k}: {e}")


if __name__ == "__main__":
    main()
