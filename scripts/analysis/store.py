"""Saved analyses, in Postgres (`stock_analyses`).

One row is one stock read through the framework on one day:

  evidence   the checks' results and the pillar summary as they stood (frozen when the analysis is
             finished, refreshed while it is a draft), with the framework version they were made under
  answers    {question code: {rating: good / ok / bad, note}} — and {pillar key: {note}} for a pillar's notes
  verdict    {decision, conviction, thesis, invalidation, review_on}
  status     'draft' while you work on it (the page autosaves), 'final' once you finish it

A stock keeps every analysis, newest first; a new one starts from the last one's answers and verdict, so
re-analysing after the next results means revising, not starting over.
"""

from __future__ import annotations

import json

from swing_screener.marketdata import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_analyses (
    id SERIAL PRIMARY KEY,
    market TEXT NOT NULL,
    symbol TEXT NOT NULL,
    framework_version TEXT NOT NULL,
    asof DATE,                                   -- the snapshot day the evidence was read on
    evidence JSONB NOT NULL DEFAULT '{}',        -- {results: {code: {status, value, detail}}, summary: {...}}
    answers JSONB NOT NULL DEFAULT '{}',         -- {code: {rating, note}}
    verdict JSONB NOT NULL DEFAULT '{}',         -- {decision, conviction, thesis, invalidation, review_on}
    status TEXT NOT NULL DEFAULT 'draft',        -- 'draft' | 'final'
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS stock_analyses_stock ON stock_analyses (market, symbol, created_at DESC);
"""
_COLS = "id, market, symbol, framework_version, asof, evidence, answers, verdict, status, created_at, updated_at, finished_at"
STATUSES = ("draft", "final")


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _row(r, full: bool = True) -> dict:
    (aid, market, symbol, ver, asof, evidence, answers, verdict, status, created, updated, finished) = r
    out = {"id": aid, "market": market, "symbol": symbol, "framework_version": ver, "asof": str(asof) if asof else None,
           "verdict": verdict or {}, "status": status, "created_at": created.isoformat(), "updated_at": updated.isoformat(),
           "finished_at": finished.isoformat() if finished else None,
           "score": ((evidence or {}).get("summary") or {}).get("score")}
    if full:
        out.update(evidence=evidence or {}, answers=answers or {})
    else:
        out["answered"] = sum(1 for a in (answers or {}).values() if (a or {}).get("rating") or (a or {}).get("note"))
    return out


def list_for(market: str, symbol: str) -> list[dict]:
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM stock_analyses WHERE market=%s AND symbol=%s ORDER BY created_at DESC", (market, symbol))
        return [_row(r, full=False) for r in cur.fetchall()]


def list_all(limit: int = 500) -> list[dict]:
    """The latest analysis of every stock, newest first."""
    with db.get_connection().cursor() as cur:
        cur.execute(f"""SELECT {_COLS} FROM (SELECT DISTINCT ON (market, symbol) {_COLS} FROM stock_analyses
                        ORDER BY market, symbol, created_at DESC) x ORDER BY updated_at DESC LIMIT %s""", (limit,))
        rows = [_row(r, full=False) for r in cur.fetchall()]
        cur.execute("SELECT market, symbol, count(*) FROM stock_analyses GROUP BY 1, 2")
        n = {(m, s): c for m, s, c in cur.fetchall()}
    for r in rows:
        r["count"] = n.get((r["market"], r["symbol"]), 1)
    return rows


def get(aid: int) -> dict | None:
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM stock_analyses WHERE id=%s", (aid,))
        r = cur.fetchone()
    return _row(r) if r else None


def create(market: str, symbol: str, version: str, asof: str | None, evidence: dict) -> dict:
    """A new draft, starting from the stock's previous analysis's answers and verdict."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT answers, verdict FROM stock_analyses WHERE market=%s AND symbol=%s ORDER BY created_at DESC LIMIT 1",
                    (market, symbol))
        prev = cur.fetchone()
        answers, verdict = (prev[0], prev[1]) if prev else ({}, {})
        cur.execute(f"""INSERT INTO stock_analyses (market, symbol, framework_version, asof, evidence, answers, verdict)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING {_COLS}""",
                    (market, symbol, version, asof, json.dumps(evidence, default=str), json.dumps(answers), json.dumps(verdict)))
        return _row(cur.fetchone())


def update(aid: int, answers: dict | None = None, verdict: dict | None = None, status: str | None = None,
           evidence: dict | None = None, version: str | None = None, asof: str | None = None) -> dict | None:
    """Save answers / verdict; `status='final'` finishes it (the evidence is no longer refreshed)."""
    if status is not None and status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    sets, args = ["updated_at = now()"], []
    for col, val in (("answers", answers), ("verdict", verdict), ("evidence", evidence)):
        if val is not None:
            sets.append(f"{col} = %s")
            args.append(json.dumps(val, default=str))
    if version is not None:
        sets.append("framework_version = %s")
        args.append(version)
    if asof is not None:
        sets.append("asof = %s")
        args.append(asof)
    if status is not None:
        sets.append("status = %s")
        args.append(status)
        sets.append("finished_at = " + ("now()" if status == "final" else "NULL"))
    with db.get_connection().cursor() as cur:
        cur.execute(f"UPDATE stock_analyses SET {', '.join(sets)} WHERE id=%s RETURNING {_COLS}", (*args, aid))
        r = cur.fetchone()
    return _row(r) if r else None


def delete(aid: int) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM stock_analyses WHERE id=%s", (aid,))
