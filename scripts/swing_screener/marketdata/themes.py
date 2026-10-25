"""Themes: named, editable baskets of stocks that share an investment story across industry groups.

A theme (AI infrastructure, India railways, India defence…) is not a classification — it is a thesis.
analytics/sectors.py tracks each one like a group (equal-weight index, RS rating, breadth, rotation,
leaders) and analytics/group_history.py rebuilds its RS rating on past dates; this module only stores them.

  themes          one row per theme, per market (an equal-weight index cannot mix currencies, so "AI
                  infrastructure" in the US and in India are two themes). Carries the thesis log of the
                  sector playbook (research/sector-analysis-playbook.md §3.2): the thesis, the evidence for
                  and against, what would invalidate it, and a status with its date.
  theme_members   who is in it, with the date each stock joined and left. History counts a stock only
                  from the day it joined, so editing a basket today never rewrites what the theme did.

    PYTHONPATH=. python3 -m swing_screener.marketdata.themes --seed     # create the starter themes (drafts)
"""

import argparse
import datetime as dt

from . import db

STATUSES = ("watching", "confirmed", "active", "closed")
THESIS_FIELDS = ("thesis", "evidence_for", "evidence_against", "invalidation", "notes")

SCHEMA = """
CREATE TABLE IF NOT EXISTS themes (
    id SERIAL PRIMARY KEY,
    market VARCHAR(16) NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'watching',
    status_since DATE NOT NULL DEFAULT CURRENT_DATE,
    opened DATE NOT NULL DEFAULT CURRENT_DATE,
    thesis TEXT, evidence_for TEXT, evidence_against TEXT, invalidation TEXT, notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(), updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (market, name)
);
CREATE TABLE IF NOT EXISTS theme_members (
    theme_id INT NOT NULL REFERENCES themes(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    added DATE NOT NULL DEFAULT CURRENT_DATE,
    removed DATE,
    PRIMARY KEY (theme_id, symbol, added)
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def load(market: str, include_closed: bool = True) -> list[dict]:
    """Every theme in a market with its current members (`members`) and full dated membership (`spans`:
    [(symbol, added, removed or None)])."""
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"""SELECT id, name, status, status_since, opened, {", ".join(THESIS_FIELDS)}, updated_at
                        FROM themes WHERE market=%s ORDER BY name""", (market,))
        cols = ["id", "name", "status", "status_since", "opened", *THESIS_FIELDS, "updated_at"]
        themes = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("""SELECT m.theme_id, m.symbol, m.added, m.removed FROM theme_members m JOIN themes t ON t.id = m.theme_id
                       WHERE t.market=%s ORDER BY m.added, m.symbol""", (market,))
        spans: dict[int, list] = {}
        for tid, sym, added, removed in cur.fetchall():
            spans.setdefault(tid, []).append((sym, added, removed))
    out = []
    for t in themes:
        if t["status"] == "closed" and not include_closed:
            continue
        t["spans"] = spans.get(t["id"], [])
        t["members"] = sorted({s for s, _a, r in t["spans"] if r is None})
        for k in ("status_since", "opened"):
            t[k] = t[k].isoformat() if t[k] else None
        t["updated_at"] = t["updated_at"].isoformat() if t["updated_at"] else None
        out.append(t)
    return out


def members_on(theme: dict, day: dt.date) -> list[str]:
    """The theme's members as they stood on `day` (joined on or before it, not yet removed)."""
    return sorted({s for s, a, r in theme["spans"] if a <= day and (r is None or r > day)})


def first_added(theme: dict) -> dt.date | None:
    return min((a for _s, a, _r in theme["spans"]), default=None)


def get(theme_id: int) -> dict | None:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market FROM themes WHERE id=%s", (theme_id,))
        r = cur.fetchone()
    return next((t for t in load(r[0]) if t["id"] == theme_id), None) if r else None


def create(market: str, name: str, symbols: list[str] | None = None, **fields) -> int:
    init_schema()
    name = (name or "").strip()
    if not name:
        raise ValueError("a theme needs a name")
    with db.get_connection().cursor() as cur:
        cur.execute("INSERT INTO themes (market, name) VALUES (%s, %s) RETURNING id", (market, name))
        tid = cur.fetchone()[0]
    if fields:
        update(tid, **fields)
    if symbols:
        add_members(tid, symbols)
    return tid


def update(theme_id: int, **fields) -> None:
    """Rename, change the status (stamping status_since when it changes) or edit the thesis log."""
    sets, vals = [], []
    if "status" in fields:
        v = fields["status"]
        if v not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        # compared with the OLD status: SET expressions all read the row as it was
        sets += ["status_since = CASE WHEN status IS DISTINCT FROM %s THEN CURRENT_DATE ELSE status_since END", "status = %s"]
        vals += [v, v]
    for k, v in fields.items():
        if k == "status":
            continue
        if k == "name":
            if not (v or "").strip():
                raise ValueError("a theme needs a name")
            v = v.strip()
        elif k not in THESIS_FIELDS and k != "opened":
            raise ValueError(f"unknown field {k}")
        sets.append(f"{k} = %s")
        vals.append(v if v != "" else None)
    if not sets:
        return
    with db.get_connection().cursor() as cur:
        cur.execute(f"UPDATE themes SET {', '.join(sets)}, updated_at = now() WHERE id = %s", (*vals, theme_id))


def add_members(theme_id: int, symbols: list[str], day: dt.date | None = None) -> int:
    """Add stocks from `day` (default today). A stock already in the theme is left as it is."""
    day = day or dt.date.today()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM theme_members WHERE theme_id=%s AND removed IS NULL", (theme_id,))
        have = {r[0] for r in cur.fetchall()}
        new = [s.strip().upper() for s in symbols if s and s.strip() and s.strip().upper() not in have]
        for s in dict.fromkeys(new):
            cur.execute("""INSERT INTO theme_members (theme_id, symbol, added) VALUES (%s, %s, %s)
                           ON CONFLICT (theme_id, symbol, added) DO UPDATE SET removed = NULL""", (theme_id, s, day))
        cur.execute("UPDATE themes SET updated_at=now() WHERE id=%s", (theme_id,))
    return len(set(new))


def remove_members(theme_id: int, symbols: list[str], day: dt.date | None = None) -> int:
    """End a stock's membership on `day` (default today). Its history inside the theme is kept.
    A stock added and removed on the same day never counted, so its row is simply deleted."""
    day = day or dt.date.today()
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM theme_members WHERE theme_id=%s AND symbol = ANY(%s) AND removed IS NULL AND added >= %s",
                    (theme_id, symbols, day))
        n = cur.rowcount
        cur.execute("UPDATE theme_members SET removed=%s WHERE theme_id=%s AND symbol = ANY(%s) AND removed IS NULL",
                    (day, theme_id, symbols))
        n += cur.rowcount
        cur.execute("UPDATE themes SET updated_at=now() WHERE id=%s", (theme_id,))
    return n


def delete(theme_id: int) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM themes WHERE id=%s", (theme_id,))


# The starter themes the sector playbook names (research/sector-taxonomy.md §5). Drafts: status
# "watching", no thesis yet, members a first pass to edit. Symbols missing from stored prices are skipped.
STARTERS = {
    "us": {
        "AI infrastructure": ["NVDA", "AVGO", "AMD", "MRVL", "MU", "TSM", "ANET", "CRDO", "ALAB", "COHR", "SMCI", "DELL",
                              "CLS", "VRT", "ETN", "GEV", "PWR", "CEG", "VST", "TLN"],
    },
    "india": {
        "Power & grid capex": ["POWERGRID.NS", "NTPC.NS", "TATAPOWER.NS", "ADANIENSOL.NS", "ABB.NS", "SIEMENS.NS",
                               "POWERINDIA.NS", "CGPOWER.NS", "BHEL.NS", "KEC.NS", "KPIL.NS", "POLYCAB.NS", "KEI.NS",
                               "APARINDS.NS", "GVT&D.NS", "TARIL.NS", "SUZLON.NS", "INOXWIND.NS"],
        "Railways": ["IRFC.NS", "RVNL.NS", "IRCON.NS", "RAILTEL.NS", "IRCTC.NS", "RITES.NS", "TITAGARH.NS",
                     "TEXRAIL.NS", "JWL.NS", "BEML.NS"],
        "Defence": ["HAL.NS", "BEL.NS", "BDL.NS", "MAZDOCK.NS", "GRSE.NS", "COCHINSHIP.NS", "DATAPATTNS.NS",
                    "ASTRAMICRO.NS", "PARAS.NS", "SOLARINDS.NS", "ZENTEC.NS", "BEML.NS"],
        "Capital markets": ["BSE.NS", "MCX.NS", "CDSL.NS", "CAMS.NS", "KFINTECH.NS", "ANGELONE.NS", "MOTILALOFS.NS",
                            "NUVAMA.NS", "HDFCAMC.NS", "NAM-INDIA.NS", "UTIAMC.NS", "360ONE.NS"],
    },
}


def seed() -> dict:
    """Create any starter theme not yet present, with the members that have stored prices."""
    init_schema()
    made = {}
    for market, themes in STARTERS.items():
        existing = {t["name"] for t in load(market)}
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT DISTINCT symbol FROM prices WHERE market=%s AND symbol = ANY(%s)",
                        (market, sorted({s for syms in themes.values() for s in syms})))
            known = {r[0] for r in cur.fetchall()}
        for name, syms in themes.items():
            if name in existing:
                continue
            have = [s for s in syms if s in known]
            create(market, name, have, notes="Starter theme: a first-pass basket to review. Write the thesis before relying on it.")
            made[f"{market}:{name}"] = {"members": len(have), "skipped": sorted(set(syms) - known)}
    return made


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--seed", action="store_true", help="create the starter themes that do not exist yet")
    a = ap.parse_args()
    if a.seed:
        for k, v in seed().items():
            print(k, v)


if __name__ == "__main__":
    main()
