"""Stock-analysis frameworks (scripts/analysis/framework.py — the company; entry.py — the entry): the
documentation contract and the checks, on hand-made evidence. No database.

    PYTHONPATH=. python3 -m tests.test_analysis
"""

import re

import pandas as pd

from analysis import entry
from analysis import framework as fw

CODES = [c[0] for c in fw.CHECKS_DOC]


def _table(columns, rows):
    return {"columns": columns, "rows": [{"key": k, "values": v} for k, v in rows.items()]}


FY = ["2022-03-31", "2023-03-31", "2024-03-31", "2025-03-31"]


def _evidence(**over):
    """A healthy growing industrial company, every source present."""
    co = {
        "quarters": {"columns": ["2025-06-30"], "rows": []},
        "growth": {"sales": [["3 years", 0.20]], "profit": [["3 years", 0.25]]},
        "ratios_top": {"roce": 0.25, "debt_to_equity": 0.2, "pe": 20.0, "price": 100.0},
        "profit_loss": _table([*FY, "TTM"], {
            "opm": [0.18, 0.19, 0.20, 0.21, 0.22], "pbt": [100, 120, 140, 160, 170], "interest": [5, 5, 5, 5, 5],
            "other_income": [5, 5, 5, 5, 6], "exceptional": [0, 0, 0, 0, -2], "tax_pct": [0.25] * 5,
            "net_profit": [75, 90, 105, 120, 128]}),
        "cash_flow": _table(FY, {"cfo": [80, 95, 110, 125], "fcf": [20, 30, 40, 50]}),
        "ratios": _table(FY, {"debtor_days": [40, 42, 41, 40], "inventory_days": [60, 58, 55, 50]}),
        "shareholding": [{"period_end": f"2025-0{i}-30", "promoters": 0.5, "fii": 0.2 + i / 100, "dii": 0.1} for i in range(1, 6)],
        "peers": [{"pe": p, "self": False} for p in (25, 30, 35)],
        "latest": {"end": "2025-06-30", "stale": False},
    }
    ev = {
        "bank": False, "company": co,
        "metrics": {"rev_g": [0.25], "eps_g": [0.30], "eps_improving_q": 5, "roe": 0.22},
        "snap": {"market_cap_usd": 12.0, "rs_rank": 85, "peer_rs": 75, "peer_rank": 2, "peer_count": 9, "peer_group": "X",
                 "rel_r12m": 12.0, "r12m": 30.0, "atr_pct": 2.5, "mdd_2y": -20.0, "tradable": True, "earnings_days": 40,
                 "weekly_uptrend": True},
        "frame": None,
        "quality": {"score": 80, "tests": {"no_dilution": True}, "metrics": {"share_cagr": 0.0},
                    "assess": {"votes": {"pe_vs_own": 0, "peg": 1, "fcf_yield": -1}, "pe_vs_own": 0.05, "peg": 0.8, "fcf_yield": 0.02}},
        "views": {"sepa": {"tests": {"F2": {"status": "pass", "detail": "2 of 3 rose"}, "F8": {"status": "pass"}}}},
        "estimates": {"periods": [{"period": "0y", "name": "This year", "chg_90d": 0.05, "dir_90d": "up"},
                                  {"period": "+1y", "eps_growth": 0.2, "eps_analysts": 10}],
                      "surprises": [{"beat": True}] * 3 + [{"beat": False}]},
    }
    ev.update(over)
    return ev


def test_docs_contract():
    assert len(set(CODES)) == len(CODES), "duplicate check code"
    assert {c[1] for c in fw.CHECKS_DOC} <= set(fw.PILLAR_KEYS)
    assert {q[1] for q in fw.QUESTIONS} <= set(fw.PILLAR_KEYS)
    assert set(fw.RED_FLAGS) <= set(CODES)
    for k in fw.PILLAR_KEYS:   # every pillar has data to read and a question for you
        assert any(c[1] == k for c in fw.CHECKS_DOC) and any(q[1] == k for q in fw.QUESTIONS), k
    for code, _p, _l, rule, _w, kind in fw.CHECKS_DOC:
        assert kind in ("pct", "pp", "pct_raw", "pp_raw", "num", "x", "days", "text"), code
        text = fw._fmt(rule)       # every {PLACEHOLDER} names a live constant
        assert "{" not in text, (code, text)
        # thresholds are constants, never literals in the rule text (the version and day counts aside)
        assert not re.search(r"\d%", re.sub(r"\{[^}]*\}", "", rule)), (code, "a literal percentage — name a constant")
    c = fw.criteria()
    assert c["version"] == fw.VERSION and c["changelog"][0]["version"] == fw.VERSION, "bump CHANGELOG with VERSION"
    assert sum(len(p["checks"]) for p in c["pillars"]) == len(CODES)


def test_every_check_answers_even_with_no_data():
    for ev in ({}, {"bank": True}, _evidence()):
        res = fw.evaluate(ev)
        assert set(res) == set(CODES)
        for code, r in res.items():
            assert r["status"] in ("good", "ok", "bad", "na", "info"), (code, r)


def test_healthy_company():
    res = fw.evaluate(_evidence())
    st = {k: v["status"] for k, v in res.items()}
    for code in ("G1", "G2", "G3", "G4", "G5", "G6", "P1", "P2", "P3", "P4", "H1", "H2", "H3", "H4", "E2", "E3", "E4", "E6",
                 "X1", "X3", "O1", "O2", "V2", "V4", "T2", "T3", "T4", "R1", "R2", "R3", "R4", "R5"):
        assert st[code] == "good", (code, res[code])
    assert st["E1"] == "good"                     # cfo 330 / profit 315 over 3 years
    assert st["V1"] == "ok" and st["V3"] == "bad"  # the Quality page's votes, as cast
    assert st["X2"] == "good"                     # 3 of 4 beats
    assert st["T1"] == "na" and st["T5"] == "na"  # no snapshot frame
    sm = fw.summarise(res)
    assert sm["pillars"]["growth"]["rating"] == "Strong" and sm["flags"] == []
    assert sm["pillars"]["business"]["rating"] is None   # information only


def test_warning_signs():
    ev = _evidence()
    ev["company"]["ratios"] = _table(FY, {"debtor_days": [40, 42, 60, 75], "inventory_days": [5, 6, 8, 9]})
    ev["company"]["cash_flow"] = _table(FY, {"cfo": [20, 20, 20, 20], "fcf": [-5, -5, 10, -5]})
    ev["company"]["shareholding"] = [{"period_end": f"2025-0{i}-30", "promoters": 0.55 - i / 100, "fii": 0.2, "dii": 0.1} for i in range(1, 6)]
    ev["views"] = {"sepa": {"tests": {"F2": {"status": "fail"}, "F8": {"status": "fail"}}}}
    res = fw.evaluate(ev)
    assert res["E1"]["status"] == "bad"           # cash 60 vs profit 315
    assert res["E2"]["status"] == "bad"           # debtor days 42 -> 75
    assert res["E3"]["status"] == "good"          # inventory days small throughout: immaterial
    assert res["H3"]["status"] == "bad"           # free cash flow positive 1 of 4 years
    assert res["O1"]["status"] == "bad"           # promoters down 4 points
    assert res["G5"]["status"] == "bad"
    assert {f["code"] for f in fw.summarise(res)["flags"]} == {"E1", "E2", "O1"}


def test_bank_skips_industrial_checks():
    res = fw.evaluate(_evidence(bank=True))
    for code in ("P2", "P3", "H1", "H2", "H3", "E1", "E2", "E3", "E4"):
        assert res[code]["status"] == "na", code


def test_trend_reads_the_screens_own_conditions():
    # a stock that passes every Stage 2 condition but RS rank (the built-in screen's own rule)
    row = {"tradable": True, "close": 110.0, "sma50": 105.0, "sma150": 100.0, "sma200": 95.0, "sma200_21d_ago": 90.0,
           "pct_above_low": 60.0, "pct_below_high": 5.0, "rs_rank": 50.0, "weekly_uptrend": True, "weekly_ma_aligned": True,
           "holding_50d": True, "mas_not_falling": True, "higher_swing_lows": True, "momentum_positive": True,
           "high_252": 115.0, "trend_not_fading": True}
    res = fw.evaluate(_evidence(frame=pd.DataFrame([row]), snap={**_evidence()["snap"], **row}))
    assert res["T1"]["status"] == "ok" and "RS rank" in res["T1"]["detail"]
    assert res["T5"]["status"] == "good"


def test_summary_maths():
    res = {"G1": {"status": "good"}, "G2": {"status": "ok"}, "G3": {"status": "bad"}, "P1": {"status": "good"},
           "H1": {"status": "na"}}
    sm = fw.summarise(res)
    assert sm["pillars"]["growth"]["score"] == 0.5 and sm["pillars"]["growth"]["rating"] == "Mixed"
    assert sm["pillars"]["profitability"]["rating"] == "Thin"     # one scored check
    assert sm["pillars"]["health"]["rating"] == "No data"
    assert sm["score"] == 50 and sm["rated"] == 1


# ---------------------------------------------------------------- the entry framework

def _entry_evidence(**over):
    """A leader in a strong group, at its pivot, in a healthy market."""
    row = {"tradable": True, "close": 100.0, "sma50": 95.0, "sma150": 88.0, "sma200": 85.0, "sma200_21d_ago": 80.0,
           "pct_above_low": 70.0, "pct_below_high": 2.0, "pct_vs_sma50": 5.3, "r3m": 25.0, "rel_r3m": 15.0,
           "base_days": 40, "base_depth_pct": 18.0, "pct_below_base_high": 2.0, "range_contracting": True, "atr_pct": 2.5}
    ev = {
        "close": 100.0, "atr": 2.5, "row": row, "frame": pd.DataFrame([{**row, "rs_rank": 92}]),
        "xs": {"rs_rank": 92, "peer_rank": 1, "peer_count": 10, "snapshot_date": "2026-10-23"},
        "group": {"name": "X", "rs": 85, "rs_then": 70, "then": "2026-09-23", "rs_date": "2026-10-23", "n": 10, "above50": 0.8},
        "market_state": {"gate": True, "trend": True, "breadth": 65.0, "breadth_then": 55.0, "dist_days": 1,
                         "index_from_high": -0.02, "index": "SPY"},
        "stage": {"stage": 2, "line": "rising"},
        "patterns": [{"code": "FBASE", "name": "Flat base", "direction": "bullish", "state": "complete", "tradeable": True,
                      "trigger": 102.0, "invalidation": 94.0, "target": 120.0}],
        "support": [{"role": "support", "tf": "D", "bottom": 95.0, "top": 97.0, "strong": True}],
        "resistance": [],
        "volume": {"updown": 1.6, "recent": 700.0, "avg50": 1000.0},
        "results_in_days": 40,
    }
    ev.update(over)
    return ev


ENTRY_CODES = [c[0] for c in entry.CHECKS_DOC]


def test_entry_docs_contract():
    assert len(set(ENTRY_CODES)) == len(ENTRY_CODES)
    assert {c[1] for c in entry.CHECKS_DOC} <= set(entry.PILLAR_KEYS) and {q[1] for q in entry.QUESTIONS} <= set(entry.PILLAR_KEYS)
    assert set(entry.RED_FLAGS) <= set(ENTRY_CODES)
    for k in entry.PILLAR_KEYS:
        assert any(c[1] == k for c in entry.CHECKS_DOC) and any(q[1] == k for q in entry.QUESTIONS), k
    for code, _p, _l, rule, _w, kind in entry.CHECKS_DOC:
        assert kind in ("pct", "pp", "pct_raw", "pp_raw", "num", "x", "days", "text"), code
        assert "{" not in entry._fmt(rule), code
        assert not re.search(r"\d%", re.sub(r"\{[^}]*\}", "", rule)), (code, "a literal percentage — name a constant")
    c = entry.criteria()
    assert c["version"] == entry.VERSION and c["changelog"][0]["version"] == entry.VERSION
    assert {p["key"] for p in c["plan"]} >= {"decision", "entry", "stop", "target"}


def test_entry_every_check_answers():
    for ev in ({}, _entry_evidence()):
        res = entry.evaluate(ev)
        assert set(res) == set(ENTRY_CODES)
        assert all(r["status"] in ("good", "ok", "bad", "na") for r in res.values())


def test_entry_ideal_setup():
    res = entry.evaluate(_entry_evidence())
    bad = {k: v for k, v in res.items() if v["status"] != "good"}
    assert not bad, bad
    sm = entry.summarise(res)
    assert sm["score"] == 100 and sm["flags"] == []


def test_entry_warning_signs():
    ev = _entry_evidence(
        market_state={"gate": False, "trend": True, "breadth": 30.0, "dist_days": 6, "index_from_high": -0.12},
        stage={"stage": 4, "line": "falling"}, results_in_days=3,
        patterns=[{"name": "Head and shoulders top", "direction": "bearish"}],
        support=[{"role": "support", "tf": "W", "bottom": 80.0, "top": 82.0}],
        resistance=[{"role": "resistance", "tf": "D", "bottom": 104.0, "top": 106.0}],
    )
    ev["row"] = {**ev["row"], "pct_vs_sma50": 30.0, "pct_below_base_high": 25.0}
    res = entry.evaluate(ev)
    for code in ("M1", "M3", "M4", "M5", "T2", "P3", "L1", "L2", "L3", "L4", "R1"):
        assert res[code]["status"] == "bad", (code, res[code])
    assert {f["code"] for f in entry.summarise(res)["flags"]} == {"M1", "T2", "L1", "L2", "R1"}


def test_entry_levels_on_the_right_side():
    ev = _entry_evidence()
    ev["row"] = {**ev["row"], "sma50": 103.0}       # a 50-day above the close is no stop
    lv = entry.levels(ev)
    assert all(x["price"] < 100 for x in lv if x["kind"] == "stop")
    assert all(x["price"] > 100 for x in lv if x["kind"] == "target")
    assert any(x["label"].startswith("Base high") and abs(x["price"] - 100 / 0.98) < 1e-9 for x in lv)
    assert not any(x["label"] == "50-day average" for x in lv)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
