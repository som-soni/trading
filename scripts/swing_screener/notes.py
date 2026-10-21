"""Notes: your own Markdown notes and journal, stored in Postgres (`notes`).

Each note has a title, a Markdown body, tags, optional linked stocks ({market, symbol}) and a pinned
flag, plus a `kind` ("note" / "journal" / "book") and, for book notes, a free-text `book` name. The
web app's Library › Notes page lists, searches and edits them (autosaving), and the chart's details
panel shows the notes linked to the stock on screen. Pasted/dropped images are stored as rows in
Postgres (`note_attachments`), not on the filesystem, and referenced from the body as ordinary
Markdown images.

    PYTHONPATH=. python3 -m swing_screener.notes --export notes_export/   # every note as a .md file
    PYTHONPATH=. python3 -m swing_screener.notes --export out/ --kind book --book "Trade Like a Stock Market Wizard"
"""

import argparse
import json
import re
import uuid
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
ALTER TABLE notes ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'note';  -- 'note' | 'journal' | 'book'
ALTER TABLE notes ADD COLUMN IF NOT EXISTS book TEXT NOT NULL DEFAULT '';      -- book name, for kind='book'
CREATE INDEX IF NOT EXISTS notes_kind ON notes (kind);
CREATE TABLE IF NOT EXISTS note_attachments (
    id SERIAL PRIMARY KEY,
    note_id INTEGER NOT NULL REFERENCES notes(id) ON DELETE CASCADE,
    filename TEXT NOT NULL,          -- random; appears in the Markdown image URL
    content_type TEXT NOT NULL,
    data BYTEA NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS note_attachments_note_filename ON note_attachments (note_id, filename);
"""
_COLS = "id, title, body, tags, symbols, pinned, kind, book, created_at, updated_at"

KINDS = ("note", "journal", "book")

ATTACHMENT_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/gif": "gif", "image/webp": "webp"}
ATTACHMENT_MAX_BYTES = 8 * 1024 * 1024


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _row(r, full: bool = True) -> dict:
    nid, title, body, tags, symbols, pinned, kind, book, created, updated = r
    out = {"id": nid, "title": title, "tags": list(tags or []), "symbols": symbols or [], "pinned": pinned,
           "kind": kind, "book": book,
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


def _clean_kind(kind) -> str:
    kind = str(kind or "").strip().lower()
    return kind if kind in KINDS else "note"


def _clean_symbols(symbols) -> list[dict]:
    seen, out = set(), []
    for s in symbols or []:
        m, sym = str(s.get("market", "")).strip(), str(s.get("symbol", "")).strip().upper()
        if m in ("us", "india") and sym and (m, sym) not in seen:
            seen.add((m, sym))
            out.append({"market": m, "symbol": sym})
    return out


def search(q: str = "", tag: str | None = None, market: str | None = None, symbol: str | None = None,
           kind: str | None = None, book: str | None = None) -> list[dict]:
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
    if kind:
        sql += " AND kind = %s"
        args.append(_clean_kind(kind))
    if book:
        sql += " AND book = %s"
        args.append(book)
    order = "created_at DESC" if kind == "journal" else "pinned DESC, updated_at DESC"
    with db.get_connection().cursor() as cur:
        cur.execute(f"{sql} ORDER BY {order}", args)
        return [_row(r, full=False) for r in cur.fetchall()]


def get(nid: int) -> dict | None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM notes WHERE id=%s", (nid,))
        r = cur.fetchone()
    return _row(r) if r else None


def create(title: str = "", body: str = "", tags=None, symbols=None, pinned: bool = False,
           kind: str = "note", book: str = "") -> dict:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"""INSERT INTO notes (title, body, tags, symbols, pinned, kind, book)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING {_COLS}""",
                    (title.strip(), body, _clean_tags(tags), json.dumps(_clean_symbols(symbols)), pinned,
                     _clean_kind(kind), book.strip()))
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
        elif k == "kind":
            sets.append("kind=%s"); args.append(_clean_kind(v))
        elif k == "book":
            sets.append("book=%s"); args.append(v.strip())
    if not sets:
        return get(nid)
    with db.get_connection().cursor() as cur:
        cur.execute(f"UPDATE notes SET {', '.join(sets)}, updated_at=now() WHERE id=%s RETURNING {_COLS}", (*args, nid))
        r = cur.fetchone()
    return _row(r) if r else None


def delete(nid: int) -> dict | None:
    """Delete and return the note (so the caller can offer Undo by re-creating it). Its attachment
    rows go too, via ON DELETE CASCADE."""
    n = get(nid)
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM notes WHERE id=%s", (nid,))
    return n


def tags() -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT t, count(*) FROM notes, unnest(tags) t GROUP BY t ORDER BY count(*) DESC, t")
        return [{"tag": t, "count": n} for t, n in cur.fetchall()]


def books() -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT book, count(*) FROM notes WHERE book != '' GROUP BY book ORDER BY book")
        return [{"book": b, "count": n} for b, n in cur.fetchall()]


def save_attachment(nid: int, content_type: str, data: bytes) -> dict:
    """Validate and store an uploaded image for note `nid` as a row in Postgres; returns {filename, url}."""
    ext = ATTACHMENT_TYPES.get(content_type)
    if not ext:
        raise ValueError(f"unsupported image type {content_type!r}")
    if len(data) > ATTACHMENT_MAX_BYTES:
        raise ValueError(f"image exceeds {ATTACHMENT_MAX_BYTES // (1024 * 1024)}MB")
    init_schema()
    filename = f"{uuid.uuid4().hex}.{ext}"
    with db.get_connection().cursor() as cur:
        cur.execute("INSERT INTO note_attachments (note_id, filename, content_type, data) VALUES (%s, %s, %s, %s)",
                    (nid, filename, content_type, data))
    return {"filename": filename, "url": f"/api/notes/{nid}/attachments/{filename}"}


def get_attachment(nid: int, filename: str) -> dict | None:
    """Fetch a stored attachment's bytes and content type."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT content_type, data FROM note_attachments WHERE note_id=%s AND filename=%s", (nid, filename))
        r = cur.fetchone()
    return {"content_type": r[0], "data": bytes(r[1])} if r else None


def export(out_dir: Path, kind: str | None = None, book: str | None = None) -> int:
    """Write matching notes as Markdown (front matter: tags, stocks, dates) — a portable copy outside the database."""
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for s in search(kind=kind, book=book):
        note = get(s["id"])
        slug = re.sub(r"[^a-z0-9]+", "-", (note["title"] or f"note-{note['id']}").lower()).strip("-")[:60]
        front = [f"title: {note['title']}", f"kind: {note['kind']}", f"book: {note['book']}",
                 f"tags: [{', '.join(note['tags'])}]",
                 f"stocks: [{', '.join(x['market'] + ':' + x['symbol'] for x in note['symbols'])}]",
                 f"created: {note['created_at']}", f"updated: {note['updated_at']}"]
        (out_dir / f"{note['id']:04d}-{slug}.md").write_text("---\n" + "\n".join(front) + "\n---\n\n" + note["body"])
        n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--export", type=Path, required=True, help="directory to write the notes into")
    ap.add_argument("--kind", choices=KINDS, help="only notes of this kind")
    ap.add_argument("--book", help="only notes with this exact book name (kind=book)")
    a = ap.parse_args()
    print(f"{export(a.export, kind=a.kind, book=a.book)} notes written to {a.export}")


if __name__ == "__main__":
    main()
