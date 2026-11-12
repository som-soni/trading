"""Saved chart layouts: a named set of the chart's indicators (and its Trade setups layer), stored in Postgres
(`chart_layouts`) so a layout is the same on every browser. The chart's Layouts menu saves the current
indicators under a name and applies a saved one; two starter layouts ship in code (STARTERS), not as rows.

A layout's `studies` is the chart's own study list (studies.js: [{type, params, colors, hidden}]), stored as
given -- the browser gives each study a fresh id when it applies one.
"""

from __future__ import annotations

import json

from .marketdata import db

SCHEMA = """
CREATE TABLE IF NOT EXISTS chart_layouts (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    studies JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

# Starter layouts, offered beside your own: the averages and setups a Minervini reader watches, and a momentum
# reader's faster averages, relative volume and RSI with the Momentum burst setups
STARTERS = [
    {"name": "Minervini view", "starter": True, "studies": [
        {"type": "sma", "params": {"length": 50}}, {"type": "sma", "params": {"length": 150}},
        {"type": "sma", "params": {"length": 200}}, {"type": "vol"}, {"type": "trendbands"},
        {"type": "setups_minervini"}]},
    {"name": "Momentum view", "starter": True, "studies": [
        {"type": "ema", "params": {"length": 10}}, {"type": "ema", "params": {"length": 21}}, {"type": "vol"},
        {"type": "rvol"}, {"type": "rsi"}, {"type": "setups_momentum_burst"}]},
]
MAX_STUDIES = 40


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _clean(studies) -> list[dict]:
    if not isinstance(studies, list):
        raise ValueError("studies must be a list")
    out = []
    for s in studies[:MAX_STUDIES]:
        if not isinstance(s, dict) or not isinstance(s.get("type"), str):
            raise ValueError("each study needs a type")
        out.append({"type": s["type"], "params": s.get("params") or {}, "colors": s.get("colors") or {},
                    "hidden": bool(s.get("hidden"))})
    return out


def listing() -> list[dict]:
    """The starter layouts, then yours (by name)."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT id, name, studies, updated_at FROM chart_layouts ORDER BY lower(name)")
        rows = [{"id": i, "name": n, "studies": st, "updated_at": u.isoformat()} for i, n, st, u in cur.fetchall()]
    return STARTERS + rows


def save(name: str, studies) -> dict:
    """Save `studies` as layout `name` (replacing a layout of that name)."""
    name = (name or "").strip()[:60]
    if not name:
        raise ValueError("a layout needs a name")
    if any(s["name"].lower() == name.lower() for s in STARTERS):
        raise ValueError(f"“{name}” is a starter layout: save yours under another name")
    with db.get_connection().cursor() as cur:
        cur.execute("""INSERT INTO chart_layouts (name, studies) VALUES (%s, %s)
                       ON CONFLICT (name) DO UPDATE SET studies = EXCLUDED.studies, updated_at = now()
                       RETURNING id""", (name, json.dumps(_clean(studies))))
        return {"id": cur.fetchone()[0], "name": name}


def delete(lid: int) -> bool:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM chart_layouts WHERE id = %s", (lid,))
        return cur.rowcount > 0
