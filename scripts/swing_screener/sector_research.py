"""Sector research: long-form sector and theme analyses, kept as dated versions in Postgres.

Each analysis (Defence, Semiconductors, Banks & financials…) is one row in `sector_research`; every time it is
written or extended, the whole document is stored again as a new row in `sector_research_versions`, dated by
the day its data is as of. Nothing is overwritten, so you can reopen what the research said on any past date
and compare it with today. The web app's Library › Sector research page lists the analyses with the age of
their latest version, flags one as due for review once it is older than REVIEW_AFTER_DAYS, and shows any
version with its contents.

The text is Markdown — typically exported from the shared doc the research was written in (its link is kept
as `source_url`, the place to keep extending it).

    PYTHONPATH=. python3 -m swing_screener.sector_research --import defence.md --slug defence \\
        --sector "Defence" --markets india,us,europe --as-of 2026-10-30 \\
        --source https://claude.ai/artifact/… --note "First version"
    PYTHONPATH=. python3 -m swing_screener.sector_research --list
    PYTHONPATH=. python3 -m swing_screener.sector_research --export out/      # latest version of each, as .md
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
    body TEXT NOT NULL,                  -- Markdown
    source_url TEXT NOT NULL DEFAULT '', -- the live doc it was exported from
    note TEXT NOT NULL DEFAULT '',       -- what this version changed
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sector_research_versions_rid ON sector_research_versions (research_id, as_of DESC, id DESC);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _title_of(body: str, fallback: str) -> str:
    m = re.search(r"^#\s+(.+)$", body, re.M)
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
                note: str = "", title: str | None = None) -> dict:
    """Store `body` as a new version of the analysis `slug` (created on first use). Returns the version."""
    init_schema()
    slug = _slug(slug)
    markets = [m.strip().lower() for m in (markets or []) if m and m.strip()]
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO sector_research (slug, sector, markets) VALUES (%s, %s, %s)
                       ON CONFLICT (slug) DO UPDATE SET sector = EXCLUDED.sector,
                         markets = CASE WHEN cardinality(EXCLUDED.markets) > 0 THEN EXCLUDED.markets
                                        ELSE sector_research.markets END,
                         updated_at = now()
                       RETURNING id""", (slug, sector.strip(), markets))
        rid = cur.fetchone()[0]
        cur.execute("""INSERT INTO sector_research_versions (research_id, as_of, title, body, source_url, note)
                       VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                    (rid, as_of, title or _title_of(body, sector), body, source_url.strip(), note.strip()))
        vid = cur.fetchone()[0]
    return get(slug, vid)


def list_all(today: dt.date | None = None) -> list[dict]:
    """Every analysis with its versions (newest first, without bodies) and the review state of the latest."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id, slug, sector, markets, created_at FROM sector_research ORDER BY sector")
        rows = cur.fetchall()
        cur.execute("""SELECT id, research_id, as_of, title, source_url, note, created_at, length(body)
                       FROM sector_research_versions ORDER BY as_of DESC, id DESC""")
        versions: dict[int, list] = {}
        for vid, rid, as_of, title, src, note, created, size in cur.fetchall():
            versions.setdefault(rid, []).append({"id": vid, "as_of": as_of.isoformat(), "title": title,
                                                 "source_url": src, "note": note, "chars": size,
                                                 "created_at": created.isoformat()})
    out = []
    for rid, slug, sector, markets, created in rows:
        vs = versions.get(rid, [])
        if not vs:
            continue
        latest = vs[0]
        out.append({"slug": slug, "sector": sector, "markets": list(markets or []), "created_at": created.isoformat(),
                    "title": latest["title"], "as_of": latest["as_of"], "source_url": latest["source_url"],
                    **_review(dt.date.fromisoformat(latest["as_of"]), today), "versions": vs})
    return out


def get(slug: str, version_id: int | None = None, today: dt.date | None = None) -> dict | None:
    """One version of an analysis with its body (the latest unless `version_id` is given), plus the list of
    all its versions so the page can offer them."""
    item = next((x for x in list_all(today) if x["slug"] == slug), None)
    if not item:
        return None
    vid = version_id or item["versions"][0]["id"]
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT v.id, v.as_of, v.title, v.body, v.source_url, v.note, v.created_at
                       FROM sector_research_versions v JOIN sector_research r ON r.id = v.research_id
                       WHERE r.slug = %s AND v.id = %s""", (slug, vid))
        r = cur.fetchone()
    if not r:
        return None
    vid, as_of, title, body, src, note, created = r
    return {**item, "version": {"id": vid, "as_of": as_of.isoformat(), "title": title, "body": _for_reading(body),
                                "source_url": src, "note": note, "created_at": created.isoformat(),
                                "latest": vid == item["versions"][0]["id"], **_review(as_of, today)}}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--import", dest="imp", metavar="FILE", help="store a Markdown file as a new version")
    ap.add_argument("--slug", help="the analysis' key, e.g. defence (defaults to the sector name)")
    ap.add_argument("--sector", help="the sector's display name, e.g. 'Defence'")
    ap.add_argument("--markets", default="", help="comma-separated markets covered, e.g. india,us,europe")
    ap.add_argument("--as-of", help="the day the version's data is as of (YYYY-MM-DD; default today)")
    ap.add_argument("--source", default="", help="link to the live doc it was exported from")
    ap.add_argument("--note", default="", help="what this version changed")
    ap.add_argument("--list", action="store_true", help="list the analyses and their versions")
    ap.add_argument("--export", metavar="DIR", help="write the latest version of each analysis as <slug>.md")
    a = ap.parse_args()
    if a.imp:
        if not a.sector:
            ap.error("--import needs --sector")
        body = Path(a.imp).read_text()
        as_of = dt.date.fromisoformat(a.as_of) if a.as_of else dt.date.today()
        v = add_version(a.slug or a.sector, a.sector, body, as_of, a.markets.split(","), a.source, a.note)
        print(f"stored {v['slug']} v{len(v['versions'])} as of {as_of} ({len(body):,} chars): {v['version']['title']}")
    if a.list:
        for x in list_all():
            flag = "  REVIEW DUE" if x["review_due"] else ""
            print(f"{x['slug']:<28} {x['sector']:<34} latest {x['as_of']} ({len(x['versions'])} versions){flag}")
            for v in x["versions"]:
                print(f"    #{v['id']:<5} {v['as_of']}  {v['note'] or v['title']}")
    if a.export:
        out = Path(a.export)
        out.mkdir(parents=True, exist_ok=True)
        for x in list_all():
            (out / f"{x['slug']}.md").write_text(get(x["slug"])["version"]["body"])
            print(f"wrote {out / (x['slug'] + '.md')}")
    if not (a.imp or a.list or a.export):
        ap.print_help()


if __name__ == "__main__":
    main()
