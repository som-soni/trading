"""Sector research: long-form sector and theme analyses, kept as dated versions in Postgres.

Each analysis (Defence, Semiconductors, Banks & financials…) is one row in `sector_research`; every time it is
written or extended, the whole document is stored again as a new row in `sector_research_versions`, dated by
the day its data is as of. Nothing is overwritten, so you can reopen what the research said on any past date
and compare it with today.

Two desks share the store:

  long-term    Library › Sector research: the slow sector theses. The page lists them with the age of their
               latest version and flags one as due for review once it is older than REVIEW_AFTER_DAYS.
  trade-desk   Trade desk › Scans & reports: the snapshots made while choosing trades — which sectors are strong, the
               stocks in them, a sector write-up. The page groups them by the day their data is as of
               (`by_date`), so each day reads as one research session you can reopen later.

A version is Markdown (`format` md — typically exported from the shared doc the research was written in, whose
link is kept as `source_url`) or a self-contained HTML page (`format` html). An HTML page is served as its own
document (`page_html`) and shown in a sandboxed frame, so its charts, sorting and filters keep working; it is a
frozen record of what the page showed that day, never recomputed.

    PYTHONPATH=. python3 -m swing_screener.sector_research --import defence.md --slug defence \\
        --sector "Defence" --markets india,us,europe --as-of 2026-10-30 \\
        --source https://claude.ai/artifact/… --note "First version"
    PYTHONPATH=. python3 -m swing_screener.sector_research --import pharma.html --slug india-pharma \\
        --sector "Pharma" --desk trade-desk --kind sector-report --markets india --as-of 2026-11-09 \\
        --note "Sector strength review"
    PYTHONPATH=. python3 -m swing_screener.sector_research --list
    PYTHONPATH=. python3 -m swing_screener.sector_research --export out/      # latest version of each
"""

import argparse
import datetime as dt
import re
from pathlib import Path

from .marketdata import db

# a sector view goes stale: drivers, valuations and policy move within a quarter or two
REVIEW_AFTER_DAYS = 90

SCHEMA = """
CREATE TABLE IF NOT EXISTS sector_research (
    id SERIAL PRIMARY KEY,
    slug TEXT NOT NULL UNIQUE,
    sector TEXT NOT NULL,
    markets TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS sector_research_versions (
    id SERIAL PRIMARY KEY,
    research_id INTEGER NOT NULL REFERENCES sector_research(id) ON DELETE CASCADE,
    as_of DATE NOT NULL,                 -- the day the version's data is as of
    title TEXT NOT NULL,
    body TEXT NOT NULL,                  -- Markdown, or an HTML page (format)
    source_url TEXT NOT NULL DEFAULT '', -- the live doc it was exported from
    note TEXT NOT NULL DEFAULT '',       -- what this version changed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sector_research_versions_rid ON sector_research_versions (research_id, as_of DESC, id DESC);
ALTER TABLE sector_research ADD COLUMN IF NOT EXISTS desk TEXT NOT NULL DEFAULT 'long-term';
ALTER TABLE sector_research ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'sector-report';
ALTER TABLE sector_research_versions ADD COLUMN IF NOT EXISTS format TEXT NOT NULL DEFAULT 'md';
"""

DESKS = ("long-term", "trade-desk")
# what an entry is; a trade-desk day lists its entries in this order
KINDS = {"stock-list": "Stock list", "sector-report": "Sector report", "note": "Note"}
FORMATS = ("md", "html")


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _title_of(body: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", body, re.M) or re.search(r"<title>(.*?)</title>", body, re.I | re.S)
    return m.group(1).strip() if m else fallback


# a chart in the shared doc exports to Markdown as only its caption: "&#91;embedded content: <caption>\]"
_EMBED = re.compile(r"&#91;embedded content:\s*(.*?)\s*\\?\]")


def _for_reading(body: str) -> str:
    """The stored Markdown as the page shows it: each chart the export dropped becomes a line pointing to the
    live doc, which still has it. The stored text itself is left exactly as exported."""
    return _EMBED.sub(lambda m: f"> **Chart — in the live doc:** {m.group(1)}", body)


def _review(as_of: dt.date, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    due = as_of + dt.timedelta(days=REVIEW_AFTER_DAYS)
    return {"age_days": (today - as_of).days, "review_by": due.isoformat(), "review_due": today >= due}


def add_version(slug: str, sector: str, body: str, as_of: dt.date, markets=None, source_url: str = "",
                note: str = "", title: str | None = None, desk: str = "long-term", kind: str = "sector-report",
                fmt: str = "md") -> dict:
    """Store `body` as a new version of the analysis `slug` (created on first use). Returns the version."""
    if desk not in DESKS:
        raise ValueError(f"desk must be one of {DESKS}")
    if kind not in KINDS:
        raise ValueError(f"kind must be one of {tuple(KINDS)}")
    if fmt not in FORMATS:
        raise ValueError(f"format must be one of {FORMATS}")
    init_schema()
    slug = _slug(slug)
    markets = [m.strip().lower() for m in (markets or []) if m and m.strip()]
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO sector_research (slug, sector, markets, desk, kind) VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (slug) DO UPDATE SET sector = EXCLUDED.sector, desk = EXCLUDED.desk, kind = EXCLUDED.kind,
                         markets = CASE WHEN cardinality(EXCLUDED.markets) > 0 THEN EXCLUDED.markets
                                        ELSE sector_research.markets END,
                         updated_at = now()
                       RETURNING id""", (slug, sector.strip(), markets, desk, kind))
        rid = cur.fetchone()[0]
        cur.execute("""INSERT INTO sector_research_versions (research_id, as_of, title, body, source_url, note, format)
                       VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id""",
                    (rid, as_of, title or _title_of(body, sector), body, source_url.strip(), note.strip(), fmt))
        vid = cur.fetchone()[0]
    return get(slug, vid)


def list_all(today: dt.date | None = None, desk: str | None = None) -> list[dict]:
    """Every analysis with its versions (newest first, without bodies) and the review state of the latest;
    only one desk's when `desk` is given."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id, slug, sector, markets, created_at, desk, kind FROM sector_research "
                    "WHERE %s::text IS NULL OR desk = %s ORDER BY sector", (desk, desk))
        rows = cur.fetchall()
        cur.execute("""SELECT id, research_id, as_of, title, source_url, note, created_at, length(body), format
                       FROM sector_research_versions ORDER BY as_of DESC, id DESC""")
        versions: dict[int, list] = {}
        for vid, rid, as_of, title, src, note, created, size, fmt in cur.fetchall():
            versions.setdefault(rid, []).append({"id": vid, "as_of": as_of.isoformat(), "title": title,
                                                 "source_url": src, "note": note, "chars": size, "format": fmt,
                                                 "created_at": created.isoformat()})
    out = []
    for rid, slug, sector, markets, created, dsk, kind in rows:
        vs = versions.get(rid, [])
        if not vs:
            continue
        latest = vs[0]
        out.append({"slug": slug, "sector": sector, "markets": list(markets or []), "created_at": created.isoformat(),
                    "desk": dsk, "kind": kind, "kind_label": KINDS.get(kind, kind), "format": latest["format"],
                    "title": latest["title"], "as_of": latest["as_of"], "source_url": latest["source_url"],
                    **_review(dt.date.fromisoformat(latest["as_of"]), today), "versions": vs})
    return out


def get(slug: str, version_id: int | None = None, today: dt.date | None = None) -> dict | None:
    """One version of an analysis with its body (the latest unless `version_id` is given), plus the list of
    all its versions so the page can offer them. An HTML version's body is not inlined: see page_html."""
    item = next((x for x in list_all(today) if x["slug"] == slug), None)
    if not item:
        return None
    vid = version_id or item["versions"][0]["id"]
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT v.id, v.as_of, v.title, v.body, v.source_url, v.note, v.created_at, v.format
                       FROM sector_research_versions v JOIN sector_research r ON r.id = v.research_id
                       WHERE r.slug = %s AND v.id = %s""", (slug, vid))
        r = cur.fetchone()
    if not r:
        return None
    vid, as_of, title, body, src, note, created, fmt = r
    return {**item, "version": {"id": vid, "as_of": as_of.isoformat(), "title": title, "format": fmt,
                                "body": _for_reading(body) if fmt == "md" else "",
                                "source_url": src, "note": note, "created_at": created.isoformat(),
                                "latest": vid == item["versions"][0]["id"], **_review(as_of, today)}}


def by_date(desk: str = "trade-desk", today: dt.date | None = None) -> list[dict]:
    """The desk's versions grouped by data date, newest first. Each day lists every entry stored for it (stock
    lists first, then sector reports, then notes), so a day reads as one research session. An entry stored
    again on a later day shows under that day as well, and its earlier versions stay under theirs. Stored
    more than once for the same day (a correction, charts added), the day shows its newest version; the
    others stay reachable from the page's version picker."""
    order = list(KINDS)
    days: dict[str, list] = {}
    for x in list_all(today, desk):
        seen = set()
        for v in x["versions"]:            # newest first, so the first one per day wins
            if v["as_of"] in seen:
                continue
            seen.add(v["as_of"])
            days.setdefault(v["as_of"], []).append({
                "slug": x["slug"], "sector": x["sector"], "markets": x["markets"], "kind": x["kind"],
                "kind_label": x["kind_label"], "version_id": v["id"], "title": v["title"], "note": v["note"],
                "format": v["format"], "source_url": v["source_url"], "latest": v["id"] == x["versions"][0]["id"],
                "versions": len(x["versions"])})
    out = []
    for day in sorted(days, reverse=True):
        es = sorted(days[day], key=lambda e: (order.index(e["kind"]) if e["kind"] in order else len(order), e["sector"]))
        notes = sorted({e["note"] for e in es if e["note"]})
        out.append({"as_of": day, "notes": notes, "entries": es, **_review(dt.date.fromisoformat(day), today)})
    return out


# the document an HTML version is served in when the stored page is a fragment (it starts at its <title>)
_PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>:root{{color-scheme:light dark}}body{{margin:0;font:14px system-ui,-apple-system,sans-serif}}img{{max-width:100%}}[hidden]{{display:none!important}}</style>
</head><body>
{body}
<script>
// The page is shown as the srcdoc of a sandboxed frame, where an in-page link ("#section", "#src-3") resolves
// against the portal's own address instead of the page; scroll to the target here instead.
document.addEventListener("click", function (e) {{
  var a = e.target.closest && e.target.closest('a[href^="#"]');
  if (!a) return;
  var t = document.getElementById(decodeURIComponent(a.getAttribute("href").slice(1)));
  if (t) {{ e.preventDefault(); t.scrollIntoView({{ block: "start" }}); }}
}});
</script>
</body></html>"""


def page_html(slug: str, version_id: int | None = None) -> str | None:
    """An HTML version as a complete document, or None if there is no such HTML version."""
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT v.body, v.format FROM sector_research_versions v JOIN sector_research r ON r.id = v.research_id
                       WHERE r.slug = %s AND (v.id = %s OR (%s::int IS NULL AND v.id = (
                           SELECT id FROM sector_research_versions WHERE research_id = r.id ORDER BY as_of DESC, id DESC LIMIT 1)))""",
                    (_slug(slug), version_id, version_id))
        r = cur.fetchone()
    if not r or r[1] != "html":
        return None
    body = r[0]
    return body if re.match(r"\s*<!doctype", body, re.I) else _PAGE.format(body=body)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--import", dest="imp", metavar="FILE", help="store a Markdown or HTML file as a new version")
    ap.add_argument("--slug", help="the analysis' key, e.g. defence (defaults to the sector name)")
    ap.add_argument("--sector", help="the sector's display name, e.g. 'Defence'")
    ap.add_argument("--markets", default="", help="comma-separated markets covered, e.g. india,us,europe")
    ap.add_argument("--as-of", help="the day the version's data is as of (YYYY-MM-DD; default today)")
    ap.add_argument("--source", default="", help="link to the live doc it was exported from")
    ap.add_argument("--note", default="", help="what this version changed")
    ap.add_argument("--title", help="the version's title (default: the file's first heading or <title>)")
    ap.add_argument("--desk", default="long-term", choices=DESKS, help="long-term (Sector research) or trade-desk (Trade desk › Scans & reports)")
    ap.add_argument("--kind", default="sector-report", choices=tuple(KINDS), help="what the entry is")
    ap.add_argument("--format", choices=FORMATS, help="md or html (default: from the file's extension)")
    ap.add_argument("--list", action="store_true", help="list the analyses and their versions")
    ap.add_argument("--export", metavar="DIR", help="write the latest version of each analysis as <slug>.md / .html")
    a = ap.parse_args()
    if a.imp:
        if not a.sector:
            ap.error("--import needs --sector")
        body = Path(a.imp).read_text()
        as_of = dt.date.fromisoformat(a.as_of) if a.as_of else dt.date.today()
        fmt = a.format or ("html" if Path(a.imp).suffix.lower() in (".html", ".htm") else "md")
        v = add_version(a.slug or a.sector, a.sector, body, as_of, a.markets.split(","), a.source, a.note,
                        title=a.title, desk=a.desk, kind=a.kind, fmt=fmt)
        print(f"stored {v['slug']} v{len(v['versions'])} ({a.desk}, {fmt}) as of {as_of} ({len(body):,} chars): {v['version']['title']}")
    if a.list:
        for x in list_all():
            flag = "  REVIEW DUE" if x["review_due"] and x["desk"] == "long-term" else ""
            print(f"{x['slug']:<28} {x['sector']:<30} {x['desk']:<10} {x['kind']:<13} latest {x['as_of']} ({len(x['versions'])} versions){flag}")
            for v in x["versions"]:
                print(f"    #{v['id']:<5} {v['as_of']}  {v['format']:<4} {v['note'] or v['title']}")
    if a.export:
        out = Path(a.export)
        out.mkdir(parents=True, exist_ok=True)
        for x in list_all():
            ext = "html" if x["format"] == "html" else "md"
            body = page_html(x["slug"]) if ext == "html" else get(x["slug"])["version"]["body"]
            (out / f"{x['slug']}.{ext}").write_text(body)
            print(f"wrote {out / (x['slug'] + '.' + ext)}")
    if not (a.imp or a.list or a.export):
        ap.print_help()


if __name__ == "__main__":
    main()
