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
from .snapshot import BASE_MAX_DAYS, STAGE2_DAYS_WINDOW

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
            {"field": "close", "op": ">=", "ref": "high_252", "mult": c.UPTREND_MIN_FRAC_OF_52W_HIGH},
            {"field": "trend_not_fading", "op": "is", "value": True},
        ]},
        "near_highs": {"name": "Near highs, rising 200-day", "conditions": [
            T,
            {"field": "close", "op": ">", "ref": "sma200"},
            {"field": "sma200_not_falling", "op": "is", "value": True},
            {"field": "close", "op": ">=", "ref": "high_252", "mult": c.NEAR_HIGHS_MIN_FRAC_OF_52W_HIGH},
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


EARLY_STAGE2_MAX_DAYS = 40   # Trend Template held on at most this many of the last ~6 months' sessions (snapshot.STAGE2_DAYS_WINDOW)

LONG_BASE_MIN_DAYS = 120          # sessions in the base (about six months)
LONG_BASE_MAX_DEPTH_PCT = 30.0    # the base's high-to-low depth; no looser than snapshot.BASE_MAX_DEPTH_PCT, where base_days stops
LONG_BASE_MAX_PCT_BELOW_HIGH = 10.0  # the close this close to the top of the base
LONG_BASE_MIN_QUALITY = 60        # Quality score (fundamentals/quality.py), present-only


def presets() -> dict[str, dict]:
    stage2 = builtin()["stage2"]["conditions"]
    return {
        "minervini_leaders": {
            "name": "Minervini leaders in Stage 2",
            "description": "Stage-2 stocks (the Trend Template) whose quarterly results pass Minervini's fundamental tests (verdict LEADER).",
            "thesis": ("Minervini's SEPA wants both halves: a stock already in a Stage-2 uptrend, and a business whose earnings and sales "
                       "are growing strongly and accelerating, with expanding margins. The verdict comes from the Fundamentals page "
                       "(fundamentals/sepa.py): EPS growth, EPS acceleration, sales growth, margins and no slowdown must pass, and "
                       "annual EPS growth and ROE must not fail. Present-only: it is not available for past snapshots, so it cannot be studied."),
            "conditions": [*stage2, {"field": "sepa_verdict", "op": "in", "value": ["LEADER"]}]},
        "early_stage2": {
            "name": "Early Stage 2",
            "description": f"Stocks that pass the full Trend Template today but held it on no more than {EARLY_STAGE2_MAX_DAYS} of "
                           f"the last {STAGE2_DAYS_WINDOW} sessions — new to Stage 2, or back in it after a correction. "
                           "A list for finding them, not a stronger screen: in the study they did no better than the Trend Template.",
            "thesis": ("Weinstein and Minervini both prefer a stock as it leaves its Stage 1 base and turns into Stage 2, with the "
                       "advance ahead of it rather than months behind. This screen is the Trend Template plus how long it has "
                       "been in force: few sessions out of the last six months means the stock entered Stage 2 recently, or "
                       "re-entered after a correction — the field cannot tell the two apart. The month-end study (2021–2026) "
                       "does not support the preference. In the US the fresher the stock the weaker its forward returns: at "
                       "this cutoff it lagged the full Trend Template at 1, 3 and 6 months, and stocks in it longer did best. "
                       "In India it beat the Trend Template at 3 and 6 months but lagged at 1 month, on about 15 stocks a "
                       "month, which is too few to call; neither market showed a higher hit rate. Use it to see who just "
                       "turned up, and judge the setup on its own."),
            "conditions": [*stage2, {"field": "stage2_days", "op": "<=", "value": EARLY_STAGE2_MAX_DAYS}]},
        "long_base_quality": {
            "name": "Long base, quality business",
            "description": f"Quality businesses (quality score {LONG_BASE_MIN_QUALITY}+) that have moved sideways for "
                           f"{LONG_BASE_MIN_DAYS}+ sessions inside a range no deeper than {LONG_BASE_MAX_DEPTH_PCT:g}%, with the "
                           f"close within {LONG_BASE_MAX_PCT_BELOW_HIGH:g}% of the range's top and its pullbacks contracting.",
            "thesis": ("A sound business whose stock has gone nowhere for months is often a base being built, not a broken stock: "
                       "Weinstein's Stage 1 and O'Neil's long flat bases end when supply is used up and the price clears the top "
                       "of the range, and the longer the base the bigger the move it can launch. Three things say the base is "
                       "mature: the price is back near its ceiling, each pullback inside it is shallower than the last (sellers "
                       "drying up, Minervini's volatility contraction), and the 200-day has stopped falling — flat is allowed, so "
                       "a Stage 1 base qualifies before the average turns up. The quality score keeps it to businesses worth "
                       f"owning. The base is the longest run of up to {BASE_MAX_DAYS} sessions inside the depth limit, so its "
                       "depth sits near that limit. The price half is point in time and can be studied; the quality score is "
                       "present-only, so the study tests only the base."),
            "conditions": [
                {"field": "tradable", "op": "is", "value": True},
                {"field": "base_days", "op": ">=", "value": LONG_BASE_MIN_DAYS},
                {"field": "base_depth_pct", "op": "<=", "value": LONG_BASE_MAX_DEPTH_PCT},
                {"field": "pct_below_base_high", "op": "<=", "value": LONG_BASE_MAX_PCT_BELOW_HIGH},
                {"field": "range_contracting", "op": "is", "value": True},
                {"field": "sma200_not_falling", "op": "is", "value": True},
                {"field": "quality", "op": ">=", "value": LONG_BASE_MIN_QUALITY},
            ]},
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
