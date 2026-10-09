"""Notes: your own Markdown notes and journal, stored in Postgres (`notes`).

Each note has a title, a Markdown body, tags, optional linked stocks ({market, symbol}) and a pinned
flag. The web app's Research › Notes page lists, searches and edits them (autosaving), and the chart's
details panel shows the notes linked to the stock on screen.

    PYTHONPATH=. python3 -m swing_screener.notes --export notes_export/   # every note as a .md file
"""

import argparse
import json
import re
from pathlib import Path

from .marketdata import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    id SERIAL PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    tags TEXT[] NOT NULL DEFAULT '{}',
    symbols JSONB NOT NULL DEFAULT '[]',     -- [{"market": "us", "symbol": "AAPL"}, ...]
    pinned BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS notes_updated ON notes (updated_at DESC);
CREATE INDEX IF NOT EXISTS notes_symbols ON notes USING gin (symbols);
"""
_COLS = "id, title, body, tags, symbols, pinned, created_at, updated_at"


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _row(r, full: bool = True) -> dict:
    nid, title, body, tags, symbols, pinned, created, updated = r
    out = {"id": nid, "title": title, "tags": list(tags or []), "symbols": symbols or [], "pinned": pinned,
           "created_at": created.isoformat(), "updated_at": updated.isoformat()}
    if full:
        out["body"] = body
    else:  # list view: a one-line snippet of the body, Markdown stripped
        text = re.sub(r"[#>*_`\[\]()|-]+", " ", body or "")
        out["snippet"] = " ".join(text.split())[:160]
    return out


def _clean_tags(tags) -> list[str]:
    seen, out = set(), []
    for t in tags or []:
        t = str(t).strip().lstrip("#").lower()
        if t and t not in seen:
            seen.add(t)
            out.append(t[:40])
    return out


def _clean_symbols(symbols) -> list[dict]:
    seen, out = set(), []
    for s in symbols or []:
        m, sym = str(s.get("market", "")).strip(), str(s.get("symbol", "")).strip().upper()
        if m in ("us", "india") and sym and (m, sym) not in seen:
            seen.add((m, sym))
            out.append({"market": m, "symbol": sym})
    return out


def search(q: str = "", tag: str | None = None, market: str | None = None, symbol: str | None = None) -> list[dict]:
    init_schema()
    sql, args = f"SELECT {_COLS} FROM notes WHERE true", []
    if q:
        sql += " AND (title ILIKE %s OR body ILIKE %s OR array_to_string(tags, ' ') ILIKE %s OR symbols::text ILIKE %s)"
        args += [f"%{q}%"] * 4
    if tag:
        sql += " AND %s = ANY(tags)"
        args.append(tag.lower())
    if symbol:
        sql += " AND symbols @> %s::jsonb"
        args.append(json.dumps([{"market": market, "symbol": symbol.upper()}] if market else [{"symbol": symbol.upper()}]))
    with db.get_connection().cursor() as cur:
        cur.execute(sql + " ORDER BY pinned DESC, updated_at DESC", args)
        return [_row(r, full=False) for r in cur.fetchall()]


def get(nid: int) -> dict | None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM notes WHERE id=%s", (nid,))
        r = cur.fetchone()
    return _row(r) if r else None


def create(title: str = "", body: str = "", tags=None, symbols=None, pinned: bool = False) -> dict:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"""INSERT INTO notes (title, body, tags, symbols, pinned) VALUES (%s, %s, %s, %s, %s) RETURNING {_COLS}""",
                    (title.strip(), body, _clean_tags(tags), json.dumps(_clean_symbols(symbols)), pinned))
        return _row(cur.fetchone())


def update(nid: int, **fields) -> dict | None:
    sets, args = [], []
    for k, v in fields.items():
        if v is None:
            continue
        if k == "title":
            sets.append("title=%s"); args.append(v.strip())
        elif k == "body":
            sets.append("body=%s"); args.append(v)
        elif k == "tags":
            sets.append("tags=%s"); args.append(_clean_tags(v))
        elif k == "symbols":
            sets.append("symbols=%s"); args.append(json.dumps(_clean_symbols(v)))
        elif k == "pinned":
            sets.append("pinned=%s"); args.append(bool(v))
    if not sets:
        return get(nid)
    with db.get_connection().cursor() as cur:
        cur.execute(f"UPDATE notes SET {', '.join(sets)}, updated_at=now() WHERE id=%s RETURNING {_COLS}", (*args, nid))
        r = cur.fetchone()
    return _row(r) if r else None


def delete(nid: int) -> dict | None:
    """Delete and return the note (so the caller can offer Undo by re-creating it)."""
    n = get(nid)
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id=%s", (nid,))
    return n


def tags() -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT t, count(*) FROM notes, unnest(tags) t GROUP BY t ORDER BY count(*) DESC, t")
        return [{"tag": t, "count": n} for t, n in cur.fetchall()]


def export(out_dir: Path) -> int:
    """Write every note as Markdown (front matter: tags, stocks, dates) — a portable copy outside the database."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for s in search():
        note = get(s["id"])
        slug = re.sub(r"[^a-z0-9]+", "-", (note["title"] or f"note-{note['id']}").lower()).strip("-")[:60]
        front = [f"title: {note['title']}", f"tags: [{', '.join(note['tags'])}]",
                 f"stocks: [{', '.join(x['market'] + ':' + x['symbol'] for x in note['symbols'])}]",
                 f"created: {note['created_at']}", f"updated: {note['updated_at']}"]
        (out_dir / f"{note['id']:04d}-{slug}.md").write_text("---\n" + "\n".join(front) + "\n---\n\n" + note["body"])
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", type=Path, required=True, help="directory to write the notes into")
    a = ap.parse_args()
    print(f"{export(a.export)} notes written to {a.export}")


if __name__ == "__main__":
    main()
