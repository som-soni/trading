"""Screens as conditions over the stock snapshot — the built-in ones and the ones you create.

A screen definition is a list of conditions, all of which must hold:

    {"field": "close", "op": ">", "value": 10}                      a field against a number
    {"field": "close", "op": ">=", "ref": "high_252", "mult": 0.85}  a field against another field × factor
    {"field": "weekly_uptrend", "op": "is", "value": true}          a yes/no field
    {"field": "sector", "op": "in", "value": ["Technology"]}        a text field against a list

Evaluated with pandas over a snapshot (screens/snapshot.py): a query, not a job. Missing values never
pass (a stock without a 200-day average is not "above" it).

The built-in screens are generated from the same constants as their coded criteria (screens/criteria.py),
and tests/test_screen_definitions.py proves each returns exactly the stocks its coded criteria pass.
Your own screens are stored in Postgres (`user_screens`).
"""

import json

import numpy as np
import pandas as pd

from ..marketdata import db
from . import criteria as c

OPS = (">", ">=", "<", "<=", "=", "!=", "is", "in")


def builtin() -> dict[str, dict]:
    T = {"field": "tradable", "op": "is", "value": True}
    return {
        "stage2": {"name": "Stage 2 — Trend Template", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma50"},
            {"field": "close", "op": ">", "ref": "sma150"},
            {"field": "close", "op": ">", "ref": "sma200"},
            {"field": "sma50", "op": ">", "ref": "sma150"},
            {"field": "sma150", "op": ">", "ref": "sma200"},
            {"field": "sma200", "op": ">", "ref": "sma200_21d_ago"},
            {"field": "pct_above_low", "op": ">=", "value": c.MIN_PCT_ABOVE_52W_LOW},
            {"field": "pct_below_high", "op": "<=", "value": c.MAX_PCT_BELOW_52W_HIGH},
            {"field": "rs_rank", "op": ">=", "value": c.RS_MIN_RANK},
        ]},
        "uptrend": {"name": "Established uptrend", "conditions": [
            T,
            {"field": "weekly_uptrend", "op": "is", "value": True},
            {"field": "weekly_ma_aligned", "op": "is", "value": True},
            {"field": "holding_50d", "op": "is", "value": True},
            {"field": "mas_not_falling", "op": "is", "value": True},
            {"field": "higher_swing_lows", "op": "is", "value": True},
            {"field": "momentum_positive", "op": "is", "value": True},
            {"field": "close", "op": ">=", "ref": "high_252", "mult": 0.75},
            {"field": "trend_not_fading", "op": "is", "value": True},
        ]},
        "near_highs": {"name": "Near highs, rising 200-day", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma200"},
            {"field": "sma200_not_falling", "op": "is", "value": True},
            {"field": "close", "op": ">=", "ref": "high_252", "mult": c.NEAR_HIGH_MIN_FRAC},
        ]},
        "above_200": {"name": "Above the 200-day", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma200"},
        ]},
    }


# Presets: built-in screens defined by conditions alone (no coded twin in screens/criteria.py — the
# strategies do not use them). Thresholds are constants so the text below stays true.
LEADER_GROUP_RS = 80     # the peer group's RS rating (Sectors page)
LEADER_MIN_RS = 70       # the stock's own RS rank
# No "top N in its group" condition: the group-strength study (research/group-strength-study.md) found the
# stock's rank inside its group added nothing in either market — the group's strength is what matters.


def presets() -> dict[str, dict]:
    return {
        "leaders": {
            "name": "Strong stocks in leading groups",
            "description": f"Strong stocks (RS {LEADER_MIN_RS}+) in the strongest peer groups (group RS {LEADER_GROUP_RS}+), in an uptrend.",
            "thesis": ("Big winners tend to come from the groups leading the market (O'Neil, Minervini): a strong stock in a weak group "
                       "usually lags. In our five-year study, stocks in strong groups beat those in weak groups in both markets "
                       "(clearly so in India), while a stock's rank inside its group added nothing — so this screen asks for a strong "
                       "group and a strong stock, not for the group's #1. The peer group is the stock's sub-industry where its industry "
                       "group is split and the sub-industry has enough tradable stocks, else its industry group; its RS rating comes "
                       "from the Sectors page."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "peer_rs", "op": ">=", "value": LEADER_GROUP_RS},
                {"field": "rs_rank", "op": ">=", "value": LEADER_MIN_RS},
                {"field": "close", "op": ">", "ref": "sma50"},
                {"field": "close", "op": ">", "ref": "sma200"},
            ]},
    }


def mask(df: pd.DataFrame, conditions: list[dict]) -> pd.Series:
    """Boolean Series: the rows that satisfy every condition."""
    m = pd.Series(True, index=df.index)
    for cond in conditions:
        f, op = cond["field"], cond["op"]
        if f not in df.columns:
            raise ValueError(f"unknown field {f!r}")
        x = df[f]
        if op == "is":
            want = bool(cond.get("value", True))
            m &= x.fillna(not want).astype(bool) == want
            continue
        if op == "in":
            m &= x.isin(list(cond.get("value") or []))
            continue
        if "ref" in cond and cond["ref"]:
            if cond["ref"] not in df.columns:
                raise ValueError(f"unknown field {cond['ref']!r}")
            y = df[cond["ref"]]
            if pd.api.types.is_numeric_dtype(y) or y.dropna().map(lambda v: isinstance(v, (int, float))).all():
                y = y.astype(float)
                mult = cond.get("mult")
                if mult not in (None, "", 1, 1.0):
                    y = y * float(mult)
            else:                                   # two text fields (e.g. peer group vs industry group): = / != only
                if op not in ("=", "!="):
                    raise ValueError(f"{f!r} and {cond['ref']!r} are text: compare them with = or ≠")
                same = (x.astype(str) == y.astype(str)) & x.notna() & y.notna()
                m &= same if op == "=" else (~same & x.notna() & y.notna())
                continue
        else:
            y = cond.get("value")
            if y is None:
                raise ValueError(f"condition on {f!r} needs a value or a field to compare with")
            y = float(y) if not isinstance(y, str) else y
        xv = x.astype(float) if not isinstance(y, str) else x
        res = {">": xv > y, ">=": xv >= y, "<": xv < y, "<=": xv <= y, "=": xv == y, "!=": (xv != y) & xv.notna()}.get(op)
        if res is None:
            raise ValueError(f"unknown operator {op!r}")
        m &= res.fillna(False).astype(bool)
    return m


def describe(cond: dict, labels: dict) -> str:
    """A condition in words: 'Close > SMA 50', 'Close ≥ 52-week high × 0.85'."""
    f = labels.get(cond["field"], cond["field"])
    op = {">=": "≥", "<=": "≤", "!=": "≠", "is": "is", "in": "in"}.get(cond["op"], cond["op"])
    if cond["op"] == "is":
        return f if cond.get("value", True) else f"not {f}"
    if cond["op"] == "in":
        return f"{f} in {', '.join(map(str, cond.get('value') or []))}"
    if cond.get("ref"):
        mult = cond.get("mult")
        return f"{f} {op} {labels.get(cond['ref'], cond['ref'])}" + (f" × {mult:g}" if mult not in (None, "", 1, 1.0) else "")
    return f"{f} {op} {cond.get('value')}"


# ------------------------------------------------------------------ your own screens

SCHEMA = """
CREATE TABLE IF NOT EXISTS user_screens (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    description TEXT NOT NULL DEFAULT '',
    conditions JSONB NOT NULL,
    sort_by TEXT,
    columns JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def _row(r) -> dict:
    return {"id": r[0], "name": r[1], "description": r[2], "conditions": r[3], "sort_by": r[4], "columns": r[5],
            "created_at": r[6].isoformat(), "updated_at": r[7].isoformat()}


_COLS = "id, name, description, conditions, sort_by, columns, created_at, updated_at"


def list_user() -> list[dict]:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM user_screens ORDER BY name")
        return [_row(r) for r in cur.fetchall()]


def get_user(sid: int) -> dict | None:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM user_screens WHERE id=%s", (sid,))
        r = cur.fetchone()
    return _row(r) if r else None


def save_user(name: str, conditions: list, description: str = "", sort_by: str | None = None, columns=None, sid: int | None = None) -> dict:
    init_schema()
    name = name.strip()
    if not name:
        raise ValueError("a screen needs a name")
    for cond in conditions:
        if cond.get("op") not in OPS:
            raise ValueError(f"unknown operator {cond.get('op')!r}")
    with db.get_connection().cursor() as cur:
        if sid:
            cur.execute(f"""UPDATE user_screens SET name=%s, description=%s, conditions=%s, sort_by=%s, columns=%s, updated_at=now()
                            WHERE id=%s RETURNING {_COLS}""", (name, description, json.dumps(conditions), sort_by, json.dumps(columns), sid))
        else:
            cur.execute(f"""INSERT INTO user_screens (name, description, conditions, sort_by, columns) VALUES (%s,%s,%s,%s,%s)
                            RETURNING {_COLS}""", (name, description, json.dumps(conditions), sort_by, json.dumps(columns)))
        return _row(cur.fetchone())


def delete_user(sid: int) -> None:
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM user_screens WHERE id=%s", (sid,))
