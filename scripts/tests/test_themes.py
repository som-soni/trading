"""Themes: a theme is rated exactly like a group, on the industry groups' scale, with dated membership.

    PYTHONPATH=. python3 -m tests.test_themes
"""

import datetime as dt

import numpy as np
import pandas as pd

from swing_screener.analytics import sectors as sect
from swing_screener.marketdata import themes as themes_mod


def _base(n_days: int = 300, seed: int = 1) -> dict:
    """A synthetic market: six stocks' daily returns, the equal-weight market index and their member rows."""
    rng = np.random.default_rng(seed)
    days = pd.bdate_range("2025-01-01", periods=n_days)
    syms = ["A", "B", "C", "D", "E", "F"]
    rets = pd.DataFrame(rng.normal(0.0005, 0.02, (n_days, len(syms))), index=days, columns=syms)
    mkt_idx = (1 + rets.mean(axis=1)).cumprod()
    ind = {s: ("Tech" if s in "ABC" else "Energy", "Software" if s in "ABC" else "Oil", 1e9) for s in syms}
    members = {}
    for s in syms:
        idx = (1 + rets[s]).cumprod()
        rel = {b: sect._ret(idx, b) - sect._ret(mkt_idx, b) for b, _ in sect.RS_WEIGHTS if sect._ret(idx, b) is not None}
        members[s] = {"symbol": s, "cap": 1e9, "rs_score": sect._rs_score(rel), "above50": True, "above200": False,
                      "new_high": False, "new_low": False, **{h: sect._ret(idx, b) for h, b in sect.HORIZONS.items()}}
    return {"rets": rets, "mkt_idx": mkt_idx, "ind": ind, "members": members}


def test_theme_index_is_an_equal_weight_basket():
    base = _base()
    syms = ["A", "D", "F"]
    row, score, _prev = sect._group_row(base, "T", syms, "theme")
    by_hand = (1 + base["rets"][syms].mean(axis=1)).cumprod()
    for h, b in sect.HORIZONS.items():
        want = float(by_hand.iloc[-1] / by_hand.iloc[-1 - b] - 1)
        assert abs(row["ew"][h] - want) < 1e-12, (h, row["ew"][h], want)
    assert row["n"] == 3 and row["sector"] is None and row["industry"] is None


def test_theme_rows_rate_on_the_industry_scale():
    base = _base()
    data = {"_base": {**base, "industry_scores": [-0.2, -0.1, 0.0, 0.1, 0.2], "industry_prev_scores": [0.0]}}
    theme = {"id": 1, "name": "T", "members": ["A", "B", "C", "ZZZ"], "status": "watching", "status_since": None, "opened": None}
    [row] = sect.theme_rows(data, [theme])
    _r, score, _p = sect._group_row(base, "T", ["A", "B", "C"], "theme")
    assert row["rs"] == sect.rate_against(score, [-0.2, -0.1, 0.0, 0.1, 0.2])
    assert row["n"] == 3 and row["size"] == 4 and row["unlisted"] == ["ZZZ"]   # ZZZ: not in the liquid set
    assert row["signals"] is not None


def test_too_few_liquid_members_is_unrated_not_dropped():
    base = _base()
    data = {"_base": {**base, "industry_scores": [0.0], "industry_prev_scores": [0.0]}}
    [row] = sect.theme_rows(data, [{"id": 2, "name": "Thin", "members": ["A", "Q"], "status": "watching",
                                    "status_since": None, "opened": None}])
    assert row["rs"] is None and row["n"] == 1 and row["signals"] is None


def test_rate_against_is_a_percentile_on_the_reference():
    ref = list(np.linspace(-1, 1, 101))
    assert sect.rate_against(5.0, ref) == 99 and sect.rate_against(-5.0, ref) == 1
    assert 49 <= sect.rate_against(0.0, ref) <= 51
    assert sect.rate_against(None, ref) is None and sect.rate_against(0.1, []) is None


def test_membership_is_point_in_time():
    d = dt.date
    theme = {"spans": [("A", d(2026, 1, 1), None), ("B", d(2026, 2, 1), d(2026, 3, 1)), ("C", d(2026, 3, 1), None)],
             "members": ["A", "C"]}
    assert themes_mod.members_on(theme, d(2025, 12, 31)) == []
    assert themes_mod.members_on(theme, d(2026, 2, 15)) == ["A", "B"]
    assert themes_mod.members_on(theme, d(2026, 3, 1)) == ["A", "C"]      # B left on 1 March, C joined the same day
    assert themes_mod.first_added(theme) == d(2026, 1, 1)


def test_store_round_trip():
    """Create, edit, re-member and delete a theme in the database, leaving nothing behind."""
    name = "__test_theme__"
    for t in themes_mod.load("us"):
        if t["name"] == name:
            themes_mod.delete(t["id"])
    tid = themes_mod.create("us", name, ["AAA", "BBB"])
    try:
        themes_mod.update(tid, thesis="why", status="confirmed")
        t = themes_mod.get(tid)
        assert t["thesis"] == "why" and t["status"] == "confirmed" and t["members"] == ["AAA", "BBB"]
        themes_mod.remove_members(tid, ["AAA"])                     # added today, removed today: never counted
        assert themes_mod.get(tid)["spans"] == [("BBB", dt.date.today(), None)]
        try:
            themes_mod.update(tid, status="nonsense")
            raise AssertionError("a bad status was accepted")
        except ValueError:
            pass
    finally:
        themes_mod.delete(tid)
    assert all(t["name"] != name for t in themes_mod.load("us"))


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
