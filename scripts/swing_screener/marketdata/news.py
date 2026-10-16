"""Per-stock news and key events, from free sources that need no API key.

Stored in Postgres for the web app's chart panel (News & events) and its event markers:

  stock_news    headlines and exchange announcements, newest first
  stock_events  dated events: earnings and results, ex-dividend, splits and bonuses, board
                meetings, material filings (8-K), analyst rating changes

Sources, per market (`MarketConfig.quarterly_source` picks the filings feed):

  Google News RSS  headlines for both markets: a search for the company's name and the market's
                   news term ("Apple stock", "Reliance Industries share") in the market's edition
                   (`news_locale`). Keyless and broad; a headline is kept only when it names the
                   company or the ticker, which drops most search noise. yfinance's own news feed
                   is empty for every symbol at the time of writing, and Yahoo's RSS is gone.
  SEC EDGAR        US: 8-K filings from data.sec.gov submissions — each one a material event
                   (results, acquisitions, officer changes, restatements), labelled by item code.
                   Uses the SEC_USER_AGENT the financials job already needs.
  NSE              India: corporate announcements (Regulation 30 disclosures), corporate actions
                   (dividends, splits, bonuses with their ex-dates) and board meetings (results
                   dates), through the browser session marketdata/financials.py keeps for NSE.
  yfinance         both: the next earnings date with its EPS estimate and the ex-dividend date
                   (`Ticker.calendar`); US dividends and splits; US analyst rating changes.

    PYTHONPATH=. python3 -m swing_screener.marketdata.news --market us --symbols AAPL,NVDA
"""

import argparse
import datetime as dt
import hashlib
import json
import logging
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime

import requests

from ..config import MARKETS
from . import db

logger = logging.getLogger("news")

NEWS_DAYS = 30           # headlines searched and shown from this many days back
EVENT_DAYS = 365         # past events kept for the panel and the chart's markers
KEEP_NEWS_DAYS = 120     # older headlines are pruned
MAX_AGE_HOURS = 12       # a symbol fetched more recently than this is skipped unless forced
MAX_HEADLINES = 40       # per symbol per fetch
GOOGLE_PAUSE = 1.0       # seconds between Google News requests — a polite rate, not a quota
SEC_PAUSE = 0.15         # SEC asks for at most 10 requests a second
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/126 Safari/537.36"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_news (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    uid TEXT NOT NULL,                      -- hash of the link: the same story fetched twice is one row
    published_at TIMESTAMPTZ,
    title TEXT NOT NULL,
    source TEXT,
    url TEXT,
    kind VARCHAR(16) NOT NULL DEFAULT 'news',   -- news | announcement
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, uid)
);
CREATE INDEX IF NOT EXISTS stock_news_recent ON stock_news (market, symbol, published_at DESC);
CREATE TABLE IF NOT EXISTS stock_events (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    date DATE NOT NULL,
    kind VARCHAR(24) NOT NULL,              -- earnings | results | dividend | split | bonus | board_meeting | filing | rating
    title TEXT NOT NULL,
    detail JSONB,
    url TEXT,
    source TEXT,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, date, kind, title)
);
CREATE TABLE IF NOT EXISTS stock_news_status (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    note TEXT,                              -- what each source returned, or why it failed
    PRIMARY KEY (market, symbol)
);
"""

# 8-K item codes -> what happened (Form 8-K general instructions). 9.01 is the exhibit list.
SEC_ITEMS = {
    "1.01": "Material agreement", "1.02": "Material agreement terminated", "1.03": "Bankruptcy",
    "1.05": "Cybersecurity incident", "2.01": "Acquisition or disposal completed",
    "2.02": "Results of operations", "2.03": "New debt obligation", "2.04": "Debt acceleration",
    "2.05": "Restructuring costs", "2.06": "Impairment", "3.01": "Delisting notice",
    "3.02": "Unregistered share sale", "3.03": "Shareholder rights modified", "4.01": "Auditor change",
    "4.02": "Prior financials no longer reliable", "5.01": "Change in control",
    "5.02": "Director or officer change", "5.03": "Charter or bylaws amended", "5.07": "Shareholder vote",
    "7.01": "Regulation FD disclosure", "8.01": "Other material event",
}
_NAME_SUFFIX = re.compile(r"[,.]?\s+(inc|incorporated|corp|corporation|co|company|ltd|limited|plc|holdings?|"
                          r"group|n\.?v|s\.?a|ag|llc|lp|class [a-c]|the)\.?$", re.I)


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _short_name(name: str | None, symbol: str) -> str:
    """'Apple Inc.' -> 'Apple', 'Reliance Industries Limited' -> 'Reliance Industries'."""
    s = (name or "").strip()
    for _ in range(3):
        s = _NAME_SUFFIX.sub("", s).strip(" ,.")
    return s or symbol.split(".")[0]


def _uid(*parts: str) -> str:
    return hashlib.sha1("|".join(parts).encode()).hexdigest()[:24]


# ------------------------------------------------------------------ headlines

def google_news(market: str, symbol: str, name: str | None) -> list[dict]:
    """Recent headlines naming the company or its ticker (Google News RSS, keyless)."""
    cfg = MARKETS[market]
    short, ticker = _short_name(name, symbol), symbol.split(".")[0]
    q = urllib.parse.quote(f'"{short}" {cfg.news_term} when:{NEWS_DAYS}d')
    r = requests.get(f"https://news.google.com/rss/search?q={q}&{cfg.news_locale}", headers=_UA, timeout=20)
    r.raise_for_status()
    # the company's first word catches "Apple's", "Reliance-Jio"; the ticker catches "AAPL stock"
    keys = {short.lower(), short.split()[0].lower(), ticker.lower()}
    out = []
    for it in ET.fromstring(r.content).findall(".//item"):
        title, src = (it.findtext("title") or "").strip(), (it.findtext("source") or "").strip()
        if src and title.endswith(f" - {src}"):
            title = title[: -len(src) - 3].strip()
        low = title.lower()
        if not title or not any(re.search(rf"\b{re.escape(k)}\b", low) for k in keys if len(k) > 1):
            continue
        try:
            when = parsedate_to_datetime(it.findtext("pubDate"))
        except (TypeError, ValueError):
            when = None
        link = it.findtext("link") or ""
        out.append({"uid": _uid(link or title), "published_at": when, "title": title, "source": src,
                    "url": link, "kind": "news"})
    out.sort(key=lambda x: x["published_at"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc), reverse=True)
    # one story syndicated to several outlets (Motley Fool → Yahoo, Globe and Mail) is one headline
    seen, kept = set(), []
    for x in out:
        key = title_key(x["title"])
        if key not in seen:
            seen.add(key)
            kept.append(x)
    return kept[:MAX_HEADLINES]


def title_key(title: str) -> str:
    """A headline reduced to its words, so syndicated copies of one story compare equal."""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


# ------------------------------------------------------------------ filings and exchange disclosures

def sec_events(symbol: str, next_earnings: dt.date | None = None) -> list[dict]:
    """US: 8-K filings of the last EVENT_DAYS days, one event per filing, labelled by item.

    Item 2.02 ("results of operations") is not only the quarterly report: some companies also file
    it for mid-quarter updates (AbbVie's charges pre-announced early each quarter), so a 2.02 is the
    earnings release (`results`, an E marker on the chart) only when it is the last one filed between
    a quarter's end and that quarter's 10-Q / 10-K. After the latest 10-Q / 10-K, the newest 2.02
    counts unless `next_earnings` (Yahoo's expected date) is still ahead of it. Any other 2.02 is a
    `filing` titled "Results update"."""
    from . import financials as fin
    cik = fin._sec_cik(symbol)
    if cik is None:
        return []
    r = requests.get(f"https://data.sec.gov/submissions/CIK{cik:010d}.json", headers=fin._sec_headers(), timeout=30)
    time.sleep(SEC_PAUSE)
    r.raise_for_status()
    f = r.json().get("filings", {}).get("recent", {})
    since = dt.date.today() - dt.timedelta(days=EVENT_DAYS)
    out, periodic = [], []   # periodic: (period end, filing date) of each 10-Q / 10-K, newest first
    for i, form in enumerate(f.get("form", [])):
        day = dt.date.fromisoformat(f["filingDate"][i])
        if form in ("10-Q", "10-K") and f.get("reportDate", [""] * (i + 1))[i]:
            periodic.append((dt.date.fromisoformat(f["reportDate"][i]), day))
        if form not in ("8-K", "8-K/A") or day < since:
            continue   # periodic filings older than the window still bound the window's first quarter
        items = [x.strip() for x in (f.get("items", [""] * (i + 1))[i] or "").split(",") if x.strip()]
        labels = [SEC_ITEMS[x] for x in items if x in SEC_ITEMS]
        acc = f["accessionNumber"][i].replace("-", "")
        out.append({"date": day, "kind": "filing", "items": items, "labels": labels, "amended": form.endswith("/A"),
                    "detail": {"form": form, "items": items}, "source": "SEC 8-K",
                    "url": f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/{f['primaryDocument'][i]}"})
    results = [e for e in out if "2.02" in e["items"] and not e["amended"]]   # newest first
    releases = set()
    for end, filed in periodic:
        hit = next((e for e in results if end < e["date"] <= filed), None)
        if hit:
            releases.add(id(hit))
    last_filed = periodic[0][1] if periodic else dt.date.min
    trailing = next((e for e in results if e["date"] > last_filed), None)
    if trailing and not (next_earnings and next_earnings > trailing["date"]):
        releases.add(id(trailing))
    for e in out:
        if id(e) in releases:
            e["kind"] = "results"
        elif "2.02" in e["items"]:
            e["labels"] = ["Results update" if x == SEC_ITEMS["2.02"] else x for x in e["labels"]]
        e["title"] = (" · ".join(e.pop("labels")) or "Current report") + (" (amended)" if e.pop("amended") else "")
        del e["items"]
    return out


def _nse_day(s: str | None) -> dt.date | None:
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y"):
        try:
            return dt.datetime.strptime((s or "").strip(), fmt).date()
        except ValueError:
            continue
    return None


def nse_feed(symbol: str) -> tuple[list[dict], list[dict]]:
    """India: (announcements as headlines, events) — Regulation 30 disclosures, corporate actions,
    board meetings — through the NSE browser session the financials job keeps."""
    from . import financials as fin
    code = symbol.removesuffix(".NS")
    since = dt.date.today() - dt.timedelta(days=EVENT_DAYS)
    news, events = [], []

    def rows(path):
        d = fin._nse.get(fin.NSE + path, index="equities", symbol=code).json()
        return d.get("data", []) if isinstance(d, dict) else (d or [])

    news_since = dt.date.today() - dt.timedelta(days=NEWS_DAYS * 2)
    for a in rows("/api/corporate-announcements")[:200]:
        stamp = (a.get("an_dt") or a.get("sort_date") or "").strip()
        day = _nse_day(stamp)
        if day is None or day < news_since:
            continue
        subject, text = (a.get("desc") or "").strip(), " ".join((a.get("attchmntText") or "").split())
        if subject.lower() in ("trading window", "copy of newspaper publication"):
            continue   # routine filings, not news
        try:
            when = dt.datetime.strptime(stamp, "%d-%b-%Y %H:%M:%S").replace(tzinfo=dt.timezone(dt.timedelta(hours=5, minutes=30)))
        except ValueError:
            when = dt.datetime.combine(day, dt.time(), tzinfo=dt.timezone.utc)
        title = subject + (f": {text[:180]}" if text else "")
        news.append({"uid": _uid(a.get("attchmntFile") or title, stamp), "published_at": when, "title": title,
                     "source": "NSE announcement", "url": a.get("attchmntFile"), "kind": "announcement"})
    for a in rows("/api/corporates-corporateActions"):
        day, subj = _nse_day(a.get("exDate")), (a.get("subject") or "").strip()
        if day is None or day < since or not subj:
            continue
        low = subj.lower()
        kind = "bonus" if "bonus" in low else "split" if "split" in low or "sub-division" in low else \
            "dividend" if "dividend" in low else "action"
        events.append({"date": day, "kind": kind, "title": f"Ex-date: {subj}", "detail": {"record_date": a.get("recDate")},
                       "source": "NSE corporate action", "url": None})
    for b in rows("/api/corporate-board-meetings"):
        day, purpose = _nse_day(b.get("bm_date")), (b.get("bm_purpose") or "").strip()
        if day is None or day < since or purpose.lower() == "board meeting intimation":
            continue   # the intimation is the notice of a meeting listed separately with its purpose
        results = "result" in purpose.lower()
        events.append({"date": day, "kind": "results" if results else "board_meeting",
                       "title": f"Board meeting: {purpose}" if purpose else "Board meeting",
                       "detail": {"description": (b.get("bm_desc") or "")[:300]}, "source": "NSE board meeting", "url": None})
    return news, events


# ------------------------------------------------------------------ yfinance

def yf_events(symbol: str, with_actions: bool, with_ratings: bool) -> list[dict]:
    """The next earnings date (and its EPS estimate) and ex-dividend date; optionally past dividends
    and splits, and analyst rating changes."""
    import yfinance as yf
    t = yf.Ticker(symbol)
    out = []
    since = dt.date.today() - dt.timedelta(days=EVENT_DAYS)
    cal = {}
    try:
        cal = t.calendar or {}
    except Exception:  # noqa: BLE001 — Yahoo answers 404 for some listings; the rest still loads
        pass
    for day in (cal.get("Earnings Date") or [])[:1]:
        est = cal.get("Earnings Average")
        out.append({"date": day, "kind": "earnings", "title": "Earnings report (expected)",
                    "detail": {"eps_estimate": est, "eps_low": cal.get("Earnings Low"), "eps_high": cal.get("Earnings High")},
                    "source": "Yahoo calendar", "url": None})
    ex = cal.get("Ex-Dividend Date")
    if with_actions and isinstance(ex, dt.date) and ex >= dt.date.today():   # a past one is in `actions` below
        out.append({"date": ex, "kind": "dividend", "title": "Ex-dividend date (upcoming)",
                    "detail": {"pay_date": str(cal.get("Dividend Date") or "")}, "source": "Yahoo calendar", "url": None})
    if with_actions:
        try:
            acts = t.actions
        except Exception:  # noqa: BLE001
            acts = None
        if acts is not None and len(acts):
            for ts, row in acts.iterrows():
                day = ts.date()
                if day < since:
                    continue
                if row.get("Dividends"):
                    out.append({"date": day, "kind": "dividend", "title": f"Ex-dividend: {row['Dividends']:g} per share",
                                "detail": {"amount": float(row["Dividends"])}, "source": "Yahoo", "url": None})
                if row.get("Stock Splits"):
                    out.append({"date": day, "kind": "split", "title": f"Stock split {row['Stock Splits']:g}:1",
                                "detail": {"ratio": float(row["Stock Splits"])}, "source": "Yahoo", "url": None})
    if with_ratings:
        try:
            ud = t.upgrades_downgrades
        except Exception:  # noqa: BLE001
            ud = None
        if ud is not None and len(ud):
            recent = ud[ud.index >= dt.datetime.combine(dt.date.today() - dt.timedelta(days=120), dt.time())]
            for ts, row in recent.head(25).iterrows():
                action = {"up": "upgrades", "down": "downgrades", "init": "initiates", "main": "maintains",
                          "reit": "reiterates"}.get(str(row.get("Action", "")).lower(), str(row.get("Action", "")))
                grade = row.get("ToGrade") or ""
                prev = row.get("FromGrade") or ""
                pt = row.get("currentPriceTarget")
                title = f"{row.get('Firm', 'Analyst')} {action}: {prev + ' → ' if prev and prev != grade else ''}{grade}".strip()
                if pt == pt and pt:   # not NaN
                    title += f" · target {pt:g}"
                out.append({"date": ts.date(), "kind": "rating", "title": title,
                            "detail": {"firm": row.get("Firm"), "action": row.get("Action")}, "source": "Yahoo", "url": None})
    return out


# ------------------------------------------------------------------ store

def _store(market: str, symbol: str, news: list[dict], events: list[dict], note: str,
           refetched: list[str] = ()) -> None:
    with db.get_connection().cursor() as cur:
        for n in news:
            cur.execute("""INSERT INTO stock_news (market, symbol, uid, published_at, title, source, url, kind)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (market, symbol, uid) DO UPDATE SET title=EXCLUDED.title, fetched_at=now()""",
                        (market, symbol, n["uid"], n["published_at"], n["title"][:500], n["source"], n["url"], n["kind"]))
        # events are re-read in full each fetch: an expected earnings date moves, so replace this
        # symbol's upcoming ones rather than keep both the old and the new date
        cur.execute("DELETE FROM stock_events WHERE market=%s AND symbol=%s AND date >= CURRENT_DATE", (market, symbol))
        # a source in `refetched` returned its whole window: its stored rows there are replaced too, so
        # a filing re-labelled (a 2.02 that turned out to be an update, not the release) loses its old row
        if refetched:
            cur.execute("DELETE FROM stock_events WHERE market=%s AND symbol=%s AND source = ANY(%s) AND date >= %s",
                        (market, symbol, list(refetched), dt.date.today() - dt.timedelta(days=EVENT_DAYS)))
        for e in events:
            cur.execute("""INSERT INTO stock_events (market, symbol, date, kind, title, detail, url, source)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (market, symbol, date, kind, title) DO UPDATE SET
                             detail=EXCLUDED.detail, url=EXCLUDED.url, source=EXCLUDED.source, fetched_at=now()""",
                        (market, symbol, e["date"], e["kind"], e["title"][:300], json.dumps(e.get("detail"), default=str),
                         e.get("url"), e.get("source")))
        cur.execute("DELETE FROM stock_news WHERE market=%s AND symbol=%s AND published_at < now() - %s * interval '1 day'",
                    (market, symbol, KEEP_NEWS_DAYS))
        cur.execute("""INSERT INTO stock_news_status (market, symbol, fetched_at, note) VALUES (%s,%s,now(),%s)
                       ON CONFLICT (market, symbol) DO UPDATE SET fetched_at=now(), note=EXCLUDED.note""",
                    (market, symbol, note))


def fetch_symbol(market: str, symbol: str, name: str | None = None) -> dict:
    """Every source for one symbol; a source that fails is noted, never fatal for the others."""
    cfg = MARKETS[market]
    news, events, notes = [], [], []

    def attempt(label, fn):
        try:
            got = fn()
            notes.append(f"{label} ok")
            return got
        except Exception as exc:  # noqa: BLE001 — one dead source must not blank the panel
            notes.append(f"{label} failed ({type(exc).__name__})")
            logger.warning("%s %s: %s failed: %s", market, symbol, label, exc)
            return None

    got = attempt("Google News", lambda: google_news(market, symbol, name))
    news += got or []
    time.sleep(GOOGLE_PAUSE)
    # NSE already lists the dividends and splits with their ex-dates; Yahoo's are for the rest
    yahoo = attempt("Yahoo", lambda: yf_events(symbol, with_actions=cfg.quarterly_source != "nse",
                                                with_ratings=cfg.quarterly_source == "sec_edgar")) or []
    refetched = []   # sources re-read in full, whose stored rows in the window are replaced
    if cfg.quarterly_source == "sec_edgar":
        # Yahoo's expected date tells a mid-quarter 2.02 update from the quarter's release (sec_events)
        upcoming = next((e["date"] for e in yahoo if e["kind"] == "earnings"), None)
        got = attempt("SEC", lambda: sec_events(symbol, upcoming))
        if got is not None:
            events += got
            refetched.append("SEC 8-K")
    elif cfg.quarterly_source == "nse":
        got = attempt("NSE", lambda: nse_feed(symbol))
        if got:
            news += got[0]
            events += got[1]
    events += yahoo
    _store(market, symbol, news, events, " · ".join(notes), refetched)
    return {"news": len(news), "events": len(events), "note": " · ".join(notes)}


def refresh(market: str, symbols: list[str], force: bool = False, progress=None) -> dict:
    """Fetch news and events for `symbols`, skipping any fetched within MAX_AGE_HOURS unless forced."""
    from . import names as names_mod
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM stock_news_status WHERE market=%s AND fetched_at > now() - %s * interval '1 hour'",
                    (market, MAX_AGE_HOURS))
        fresh = {r[0] for r in cur.fetchall()}
    todo = [s for s in symbols if force or s not in fresh]
    try:
        names = names_mod.load(market)
    except Exception:  # noqa: BLE001 — names make a better query, but the ticker alone still works
        names = {}
    done, failed, n_news, n_events = 0, 0, 0, 0
    for i, sym in enumerate(todo):
        if progress:
            progress(f"news & events: {i + 1:,}/{len(todo):,} symbols · {n_news:,} headlines · {n_events:,} events")
        try:
            r = fetch_symbol(market, sym, names_mod.lookup(names, sym))
            done += 1
            n_news += r["news"]
            n_events += r["events"]
        except Exception as exc:  # noqa: BLE001
            failed += 1
            logger.warning("%s %s: %s", market, sym, exc)
    return {"requested": len(symbols), "skipped_fresh": len(symbols) - len(todo), "fetched": done,
            "failed": failed, "headlines": n_news, "events": n_events}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--symbols", required=True, help="comma-separated")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    print(refresh(a.market, [s.strip() for s in a.symbols.split(",") if s.strip()], force=a.force))


if __name__ == "__main__":
    main()
