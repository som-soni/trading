"""Fundamentals: the quarterly-results parsers (marketdata/financials.py), the shared metrics
(fundamentals/growth.py) and the Minervini SEPA view (fundamentals/sepa.py), on hand-made filings.
No network, no database.

    PYTHONPATH=. python3 -m tests.test_fundamentals
"""

import datetime as dt

from fundamentals import growth, sepa
from swing_screener.marketdata import financials as q

D = dt.date


def _fact(start, end, val, accn, filed, form="10-Q", fy=2024, fp="Q1"):
    return {"start": start, "end": end, "val": val, "accn": accn, "filed": filed, "form": form, "fy": fy, "fp": fp}


# a fiscal year ending in December: Q1-Q3 from 10-Qs (each with its year-ago comparative), Q4 only in the 10-K
FACTS = [
    _fact("2024-01-01", "2024-03-31", 10, "q1", "2024-05-01"), _fact("2023-01-01", "2023-03-31", 8, "q1", "2024-05-01"),
    _fact("2024-04-01", "2024-06-30", 12, "q2", "2024-08-01", fp="Q2"), _fact("2023-04-01", "2023-06-30", 9, "q2", "2024-08-01", fp="Q2"),
    _fact("2024-07-01", "2024-09-30", 14, "q3", "2024-11-01", fp="Q3"), _fact("2023-07-01", "2023-09-30", 10, "q3", "2024-11-01", fp="Q3"),
    _fact("2024-01-01", "2024-09-30", 36, "q3", "2024-11-01", fp="Q3"), _fact("2023-01-01", "2023-09-30", 27, "q3", "2024-11-01", fp="Q3"),
    _fact("2024-01-01", "2024-12-31", 52, "k", "2025-02-15", form="10-K", fp="FY"),
    _fact("2023-01-01", "2023-12-31", 38, "k", "2025-02-15", form="10-K", fp="FY"),
    # a later 10-Q restates Q1 2024 as its comparative: the first report must win
    _fact("2024-01-01", "2024-03-31", 11, "q1b", "2025-05-01", fy=2025), _fact("2025-01-01", "2025-03-31", 13, "q1b", "2025-05-01", fy=2025),
]


def test_sec_quarters_first_report_and_comparatives():
    out = q.sec_quarters(FACTS)
    assert out[D(2024, 3, 31)]["val"] == 10 and out[D(2024, 3, 31)]["prior"] == 8      # as first reported
    assert out[D(2025, 3, 31)]["val"] == 13 and out[D(2025, 3, 31)]["prior"] == 11     # comparative from the same filing
    assert out[D(2024, 9, 30)]["prior"] == 10


def test_sec_derived_q4():
    q4 = q.sec_quarters(FACTS)[D(2024, 12, 31)]
    assert q4["derived"] and q4["val"] == 52 - 36 and q4["prior"] == 38 - 27, q4
    assert q4["start"] == D(2024, 10, 1) and q4["fiscal"] == "FY2024 Q4"


def test_sec_derived_q4_eps_survives_a_split():
    # a 2:1 split between the Q3 10-Q (EPS on the old shares) and the 10-K (restated to the new):
    # full year - nine months would mix the two; the net-income share of the year does not
    eps = [_fact("2024-01-01", "2024-09-30", 3.0, "q3", "2024-11-01"), _fact("2023-01-01", "2023-09-30", 2.0, "q3", "2024-11-01"),
           _fact("2024-01-01", "2024-12-31", 2.0, "k", "2025-02-15", form="10-K"), _fact("2023-01-01", "2023-12-31", 1.4, "k", "2025-02-15", form="10-K")]
    ni = [_fact("2024-01-01", "2024-09-30", 300, "q3", "2024-11-01"), _fact("2023-01-01", "2023-09-30", 200, "q3", "2024-11-01"),
          _fact("2024-01-01", "2024-12-31", 400, "k", "2025-02-15", form="10-K"), _fact("2023-01-01", "2023-12-31", 280, "k", "2025-02-15", form="10-K")]
    js = {"facts": {"us-gaap": {"EarningsPerShareDiluted": {"units": {"USD/shares": eps}}, "NetIncomeLoss": {"units": {"USD": ni}}}}}
    row = next(r for r in q.parse_sec(js) if r["period_end"] == D(2024, 12, 31))
    assert abs(row["eps"] - 2.0 * 100 / 400) < 1e-9, row["eps"]        # not 2.0 - 3.0 = -1.0
    assert abs(row["eps_prior"] - 1.4 * 80 / 280) < 1e-9
    assert row["eps_fy"] == 2.0 and row["net_income_fy"] == 400


XBRL = b"""<?xml version="1.0" encoding="UTF-8"?>
<xbrli:xbrl xmlns:xbrli="http://www.xbrl.org/2003/instance" xmlns:in-capmkt="http://example/in-capmkt">
<xbrli:context id="OneD"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:context id="FourD"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:startDate>2026-01-01</xbrli:startDate><xbrli:endDate>2026-03-31</xbrli:endDate></xbrli:period></xbrli:context>
<xbrli:context id="OneI"><xbrli:entity><xbrli:identifier scheme="x">1</xbrli:identifier></xbrli:entity>
  <xbrli:period><xbrli:instant>2026-03-31</xbrli:instant></xbrli:period></xbrli:context>
<in-capmkt:DateOfStartOfReportingPeriod contextRef="OneD">2026-01-01</in-capmkt:DateOfStartOfReportingPeriod>
<in-capmkt:DateOfEndOfReportingPeriod contextRef="OneD">2026-03-31</in-capmkt:DateOfEndOfReportingPeriod>
<in-capmkt:DateOfStartOfReportingPeriod contextRef="FourD">2025-04-01</in-capmkt:DateOfStartOfReportingPeriod>
<in-capmkt:DateOfEndOfReportingPeriod contextRef="FourD">2026-03-31</in-capmkt:DateOfEndOfReportingPeriod>
<in-capmkt:RevenueFromOperations contextRef="OneD">1000</in-capmkt:RevenueFromOperations>
<in-capmkt:ProfitLossForPeriod contextRef="OneD">120</in-capmkt:ProfitLossForPeriod>
<in-capmkt:ProfitOrLossAttributableToOwnersOfParent contextRef="OneD">100</in-capmkt:ProfitOrLossAttributableToOwnersOfParent>
<in-capmkt:DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations contextRef="OneD">0</in-capmkt:DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations>
<in-capmkt:DilutedEarningsLossPerShareFromContinuingOperations contextRef="OneD">2.5</in-capmkt:DilutedEarningsLossPerShareFromContinuingOperations>
<in-capmkt:PaidUpValueOfEquityShareCapital contextRef="OneD">400</in-capmkt:PaidUpValueOfEquityShareCapital>
<in-capmkt:FaceValueOfEquityShareCapital contextRef="OneD">10</in-capmkt:FaceValueOfEquityShareCapital>
<in-capmkt:ProfitOrLossAttributableToOwnersOfParent contextRef="FourD">380</in-capmkt:ProfitOrLossAttributableToOwnersOfParent>
<in-capmkt:DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations contextRef="FourD">9.5</in-capmkt:DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations>
<in-capmkt:EquityAttributableToOwnersOfParent contextRef="OneI">2000</in-capmkt:EquityAttributableToOwnersOfParent>
</xbrli:xbrl>"""


def test_parse_nse_xbrl():
    r = q.parse_nse_xbrl(XBRL)
    assert r["period_end"] == D(2026, 3, 31) and r["period_start"] == D(2026, 1, 1)
    assert r["revenue"] == 1000 and r["net_income"] == 100          # attributable to owners, not total profit
    assert r["eps"] == 2.5                                         # the zero in the main tag is skipped
    assert r["shares"] == 40 and r["equity"] == 2000
    # the full-year context is defined with the quarter's dates; the stated period wins
    assert r["eps_fy"] == 9.5 and r["net_income_fy"] == 380


def test_parse_nse_undefined_context():
    # a banking document: OneD is referenced, never defined, and only its end date is stated
    doc = b"""<x:xbrl xmlns:x="http://www.xbrl.org/2003/instance" xmlns:b="http://example/b">
      <b:DateOfEndOfReportingPeriod contextRef="OneD">2023-09-30</b:DateOfEndOfReportingPeriod>
      <b:InterestEarned contextRef="OneD">750</b:InterestEarned>
      <b:ProfitLossForThePeriod contextRef="OneD">170</b:ProfitLossForThePeriod>
      <b:DilutedEarningsPerShareAfterExtraordinaryItems contextRef="OneD">22.1</b:DilutedEarningsPerShareAfterExtraordinaryItems></x:xbrl>"""
    r = q.parse_nse_xbrl(doc)
    assert r["period_end"] == D(2023, 9, 30) and r["revenue"] == 750 and r["net_income"] == 170 and r["eps"] == 22.1


def test_choose_filings_one_basis():
    f = lambda end, basis, filed="2024-01-01": {"end": D(*end), "basis": basis, "filed": D.fromisoformat(filed), "url": f"{end}{basis}{filed}"}  # noqa: E731
    fs = [f((2024, 3, 31), "consolidated"), f((2024, 3, 31), "standalone"), f((2023, 12, 31), "consolidated"),
          f((2023, 12, 31), "consolidated", "2024-02-01"), f((2023, 9, 30), "standalone"), f((2023, 6, 30), "consolidated")]
    basis, chosen = q.choose_filings(fs)
    assert basis == "consolidated"                                 # 3 of 4 quarters
    assert [c["end"] for c in chosen] == [D(2024, 3, 31), D(2023, 12, 31), D(2023, 6, 30)]   # never mixed in
    assert chosen[1]["filed"] == D(2024, 2, 1)                     # a revision wins


def test_due():
    t = dt.datetime
    today = D(2026, 10, 11)
    assert q.due(None, today)
    assert not q.due((t(2026, 10, 1), "ok", D(2026, 6, 30)), D(2026, 10, 5))   # the next quarter's results not due yet
    assert q.due((t(2026, 10, 1), "ok", D(2026, 6, 30)), today)                # due from 06-30 + 91 + 10 days, 10 days since the last look
    assert not q.due((t(2026, 10, 10), "ok", D(2026, 6, 30)), today)           # ... but looked yesterday
    assert q.due((t(2026, 9, 1), "ok", D(2026, 9, 30)), today)                 # older than MAX_AGE_DAYS
    assert not q.due((t(2026, 9, 20), "none", None), today) and q.due((t(2026, 9, 1), "none", None), today)


def _quarters(eps: list, rev: list, ni: list | None = None, shares: list | None = None, start=D(2022, 3, 31)) -> list[dict]:
    rows, end = [], start
    for k, (e, r) in enumerate(zip(eps, rev)):
        rows.append(q._row(period_end=end, eps=e, revenue=r, net_income=(ni[k] if ni else e * 10), shares=(shares[k] if shares else 10.0),
                           source="nse"))
        m = end.month + 3
        end = (D(end.year + (m > 12), (m - 1) % 12 + 1, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return rows


def test_sec_eps_scale_slips():
    """A filing that tags EPS at the wrong scale (HAL Q2 2021: 260000 for $0.26) is divided back, against
    net income / shares and the company's other quarters; a correct EPS beside a broken share count is kept."""
    assert q.eps_scale(260000, 227e6, 890e6) == 1e6
    assert q.eps_scale(260, 227e6, 890e6) == 1e3
    assert q.eps_scale(0.26, 227e6, 890e6) == 1
    assert q.eps_scale(660000, 370e6, 112e6) == 1e6        # slip and a later 5:1 split basis together
    assert q.eps_scale(20.0, 1e9, 1e9) == 1                # a 20:1 split mismatch is not a scale slip
    assert q.eps_scale(7000, 10e9) == 1                    # a genuinely large EPS (Berkshire A-like)
    row = lambda eps, ni, sh: {"eps": eps, "net_income": ni, "shares": sh, "eps_prior": None, "eps_fy": None}
    rows = q._fix_eps_scale([row(0.30, 260e6, 890e6), row(260000, 227e6, 890e6), row(0.25, 220e6, 890e6),
                                      row(-0.2, -180e6, 890e6), row(215634000, -117e6, 215634000)])
    assert [r["eps"] for r in rows] == [0.30, 0.26, 0.25, -0.2, None]   # rescaled; a share count in the EPS field dropped
    nse = q._fix_eps_scale([row(2.74, 154e6, 2.8e13), row(3.1, 170e6, 5.6e7), row(2.9, 160e6, 5.6e7)])
    assert [r["eps"] for r in nse] == [2.74, 3.1, 2.9]               # a mis-scaled share count leaves the EPS alone


def test_nse_slips():
    """NSE filings: a quarter entered in lakh is scaled back; an impossible share count and a net income of 0 (or
    from the wrong line) beside a normal EPS are blanked, never guessed."""
    import datetime as _dt
    def nse(m, rev, ni, eps, sh):
        return {"period_end": _dt.date(2024, m, 28), "source": "nse", "revenue": rev, "net_income": ni, "eps": eps, "shares": sh}
    rows = [nse(1, 2000e7, 150e7, 1.6, 94e7), nse(2, 2100e7, 160e7, 1.7, 94e7), nse(3, 29.5e7, 2.4e7, 2.57, 0.94e7),
            nse(4, 2200e7, 0.0, 1.8, 94e7), nse(5, 2300e7, 16e7, 1.9, 94e7), nse(6, 2250e7, 170e7, 1.8, 1e7),
            nse(7, 2400e7, 180e7, 1.9, 94e7)]
    fixed = q._fix_nse([dict(r) for r in rows])
    assert abs(fixed[2]["revenue"] - 2950e7) < 1 and abs(fixed[2]["shares"] - 94e7) < 1 and fixed[2]["eps"] == 2.57   # lakh slip x100
    assert fixed[3]["net_income"] is None                                    # 0 beside a real EPS: not reported
    assert fixed[4]["net_income"] is None                                    # 10x off its EPS x shares: wrong line
    assert fixed[5]["shares"] is None and fixed[5]["net_income"] == 170e7    # a placeholder count of 1 crore
    assert [r["revenue"] for r in fixed[:2]] == [2000e7, 2100e7] and fixed[6]["net_income"] == 180e7
    us = [{**r, "source": "sec_edgar"} for r in rows]
    assert q._fix_nse([dict(r) for r in us]) == us                           # NSE rows only


def test_split_factors():
    shares = [100, 101, 202, 203, 204, 280]                 # 1:1 bonus, then a 37% share issue
    eps = [1.0, 1.0, 0.5, 0.5, 0.5, 0.4]
    rows = _quarters(eps, [1] * 6, ni=[e * s for e, s in zip(eps, shares)], shares=shares)
    f = growth.split_factors(rows)
    assert f == [2.0, 2.0, 1.0, 1.0, 1.0, 1.0], f
    # a misfiled share count in one quarter, while the count the EPS implies holds steady, is no split
    shares = [100, 100, 700, 100, 100]
    rows = _quarters([1.0] * 5, [1] * 5, ni=[100.0] * 5, shares=shares)
    assert growth.split_factors(rows) == [1.0] * 5


def _sec(eps, ni, shares, prior=None, start=D(2022, 3, 31)):
    rows = _quarters(eps, [100] * len(eps), ni=ni, shares=shares, start=start)
    for r, p in zip(rows, prior or [None] * len(rows)):
        r.update(source="sec_edgar", eps_prior=p)
    return rows


def test_split_ratios_beyond_the_common_ones():
    # Chipotle-style 50:1 and Apple-style 7:1 (the share count jumps 6.88x: diluted weighted shares drift)
    f = growth.split_factors(_quarters([5, 5, 0.1, 0.1], [1] * 4, ni=[150, 150, 150, 150], shares=[30, 30, 1500, 1500]))
    assert f == [50.0, 50.0, 1.0, 1.0], f
    f = growth.split_factors(_quarters([7, 7, 1, 1], [1] * 4, ni=[6160, 6160, 6055, 6100], shares=[880, 880, 6055, 6100]))
    assert f == [7.0, 7.0, 1.0, 1.0], f


def test_split_from_implied_shares_when_the_count_is_missing():
    # Alphabet-style 20:1 with no stored share count: net income / EPS jumps 20x and holds there
    rows = _quarters([25, 26, 27, 1.3, 1.4, 1.5], [1] * 6, ni=[25 * 680, 26 * 680, 27 * 680, 1.3 * 13600, 1.4 * 13600, 1.5 * 13600],
                     shares=[None] * 6)
    f = growth.split_factors(rows)
    assert f == [20.0, 20.0, 20.0, 1.0, 1.0, 1.0], f
    # one quarter with a misfiled net income is not two splits
    rows = _quarters([2, 2, 2, 2, 2], [1] * 5, ni=[200, 200, 2000, 200, 200], shares=[None] * 5)
    assert growth.split_factors(rows) == [1.0] * 5


def test_sec_comparative_confirms_and_vetoes():
    # a 25:1 split: the filing after it restates the year-ago EPS (12.5 -> 0.5) — the share count agrees
    eps = [10, 11, 12, 12.5, 0.48, 0.5]
    rows = _sec(eps, [e * 40 for e in eps[:4]] + [e * 1000 for e in eps[4:]], [40, 40, 40, 40, 1000, 1000],
                prior=[None, None, None, None, 10 / 25, 11 / 25])
    assert growth.split_factors(rows) == [25.0] * 4 + [1.0] * 2
    # a merger that doubles the count: the restated year-ago EPS is unchanged, so it is not a split
    eps = [1.0, 1.0, 1.0, 1.0, 1.1, 1.1]
    rows = _sec(eps, [e * 100 for e in eps[:4]] + [e * 200 for e in eps[4:]], [100, 100, 100, 100, 200, 200],
                prior=[None, None, None, None, 1.0, 1.0])
    assert growth.split_factors(rows) == [1.0] * 6
    # a reverse merger: the count jumps 50x, the EPS is too small to imply a count and the filing has no
    # comparative — for SEC a big jump in the stored count alone is not a split
    rows = _sec([0.1, 0.1, -0.1, -0.1], [10, 10, -500, -500], [100, 100, 5000, 5000])
    assert growth.split_factors(rows) == [1.0] * 4
    # a 1:3 reverse split filed together with a share issue: the count moves 0.4x, the comparative 1/3
    eps = [1.0, 1.0, 1.0, 1.0, 2.5, 2.5]
    rows = _sec(eps, [100] * 4 + [100, 100], [100, 100, 100, 100, 40, 40], prior=[None] * 4 + [3.0, 3.0])
    assert growth.split_factors(rows) == [1 / 3] * 4 + [1.0] * 2
    # growth from the filing's own comparative is untouched by the factors
    g = growth.growth_series(_sec([10, 11, 12, 12.5, 0.48, 0.5], [400, 440, 480, 500, 480, 500], [40, 40, 40, 40, 1000, 1000],
                                  prior=[None, None, None, None, 0.4, 0.44]))
    assert abs(g[4]["eps_g"] - 0.2) < 1e-9 and abs(g[4]["eps_adj"] - 0.48) < 1e-9 and abs(g[0]["eps_adj"] - 0.4) < 1e-9


def test_growth_uses_split_adjusted_year_ago_eps():
    # EPS halves at a 1:1 bonus in the fifth quarter; real growth is 20%
    rows = _quarters([1.0, 1.0, 1.0, 1.0, 0.6, 0.6], [100] * 4 + [120] * 2, ni=[10, 10, 10, 10, 12, 12], shares=[10, 10, 10, 10, 20, 20])
    g = growth.growth_series(rows)
    assert abs(g[4]["eps_g"] - 0.2) < 1e-9 and abs(g[4]["rev_g"] - 0.2) < 1e-9


def test_leader_and_code33():
    # 12 quarters: EPS and sales growth accelerating, margins widening
    eps = [1.0, 1.0, 1.0, 1.0, 1.2, 1.3, 1.45, 1.6, 1.6, 1.85, 2.2, 2.7]
    rev = [10.0, 10.0, 10.0, 10.0, 12.0, 12.4, 13.0, 13.6, 14.6, 15.4, 16.9, 18.7]
    rows = _quarters(eps, rev, ni=[e * 1.0 for e in eps])
    r = sepa.score(rows, today=rows[-1]["period_end"] + dt.timedelta(days=30))
    t = {k: v["status"] for k, v in r["tests"].items()}
    assert t["F1"] == t["F2"] == t["F3"] == t["F4"] == t["F8"] == "pass", r["tests"]
    assert r["verdict"] == "LEADER" and r["code33"], r


def test_slowdown_is_flagged():
    eps = [1.0, 1.0, 1.0, 1.0, 2.0, 1.8, 1.6, 1.4]                 # growth 100%, 80%, 60%, 40%: slowing
    rows = _quarters(eps, [10, 10, 10, 10, 13, 13, 13, 13])
    r = sepa.score(rows, today=rows[-1]["period_end"] + dt.timedelta(days=30))
    assert r["tests"]["F8"]["status"] == "fail" and r["verdict"] == "WEAK", r["tests"]


def test_growth_from_a_loss_is_not_measured():
    rows = _quarters([-1.0, 1, 1, 1, 0.5], [10, 10, 10, 10, 12])
    r = sepa.score(rows, today=rows[-1]["period_end"] + dt.timedelta(days=30))
    assert r["tests"]["F1"]["status"] == "fail" and "loss" in r["tests"]["F1"]["detail"]
    assert r["verdict"] == "NO DATA"                               # one reading is not enough


def test_recovery_readings():
    # loss-making year-ago quarters, then EPS beats each one: -0.5 > -1.0, 0.2 > -0.8, 0.4 > -0.3
    rows = _quarters([-1.0, -0.8, -0.3, 0.1, -0.5, 0.2, 0.4], [10, 10, 10, 10, 10, 10.5, 11.5])
    m = growth.metrics(rows, today=rows[-1]["period_end"] + dt.timedelta(days=30))
    assert m["eps_turned_positive"] is True and m["eps_improving_q"] == 3, m
    assert m["sales_accelerating"] is True                          # sales growth 0%, 5%, 15%: rising
    # profitable a year ago too: not a turnaround, though EPS improved
    m = growth.metrics(_quarters([1.0, 1, 1, 1, 1.2], [10] * 5), today=D(2023, 6, 30))
    assert m["eps_turned_positive"] is False and m["eps_improving_q"] == 1 and m["sales_accelerating"] is None
    # no year-ago quarter: unknown, not "no"
    m = growth.metrics(_quarters([1.0, 1.2], [10, 11]), today=D(2022, 9, 30))
    assert m["eps_turned_positive"] is None and m["eps_improving_q"] is None


def test_metrics_are_strategy_neutral():
    rows = _quarters([1.0, 1.0, 1.0, 1.0, 1.5], [10, 10, 10, 10, 13])
    m = growth.metrics(rows, today=rows[-1]["period_end"] + dt.timedelta(days=30))
    assert abs(m["eps_g"][0] - 0.5) < 1e-9 and abs(m["rev_g"][0] - 0.3) < 1e-9 and not m["stale"]
    assert "verdict" not in m                                     # judging is the views' job


def test_annual_from_fiscal_years():
    rows = _quarters([1.0] * 16, [10.0] * 16)
    for k, fy in zip((3, 7, 11, 15), (4.0, 6.0, 9.0, 13.5)):       # the Q4 rows carry the full year
        rows[k]["eps_fy"] = fy
    r = sepa.score(rows, today=rows[-1]["period_end"] + dt.timedelta(days=30))
    assert r["tests"]["F5"]["status"] == "pass" and abs(r["tests"]["F5"]["value"] - 0.5) < 1e-9, r["tests"]["F5"]


def test_nse_lines_industrial():
    v = {"RevenueFromOperations": "1000", "Expenses": "800", "FinanceCosts": "30", "DepreciationDepletionAndAmortisationExpense": "70",
         "OtherIncome": "20", "ProfitBeforeTax": "220", "TaxExpense": "55", "ProfitOrLossAttributableToOwnersOfParent": "160",
         "DilutedEarningsLossPerShareFromContinuingAndDiscontinuedOperations": "4.0"}
    pl = q._nse_pl(v, bank=False)
    # screener's operating profit: sales less expenses other than interest and depreciation
    assert pl["expenses"] == 700 and pl["operating_profit"] == 300 and pl["interest"] == 30 and pl["net_profit"] == 160
    bs = q._nse_bs({"EquityAndLiabilities": "5000", "Equity": "2200", "EquityAttributableToOwnersOfParent": "2000",
                    "BorrowingsNoncurrent": "600", "BorrowingsCurrent": "400", "PropertyPlantAndEquipment": "1500",
                    "CapitalWorkInProgress": "300", "NoncurrentInvestments": "200", "Assets": "5000"}, bank=False)
    assert bs["borrowings"] == 1000 and bs["other_liabilities"] == 5000 - 2200 - 1000 and bs["other_assets"] == 5000 - 1500 - 300 - 200


def test_nse_lines_bank():
    v = {"InterestEarned": "900", "InterestExpended": "450", "OperatingExpenses": "300", "ProvisionsOtherThanTaxAndContingencies": "50",
         "OtherIncome": "250", "ProfitLossFromOrdinaryActivitiesBeforeTax": "350", "ProfitLossForThePeriod": "260"}
    pl = q._nse_pl(v, bank=True)
    assert pl["sales"] == 900 and pl["expenses"] == 350 and pl["operating_profit"] == 100 and pl["pbt"] == 350


def test_nse_profit_skips_zero_placeholder():
    # Titan, standalone, Sep-2018: the owners-of-parent line is a 0 placeholder, the profit is in ProfitLossForPeriod
    v = {"ProfitOrLossAttributableToOwnersOfParent": "0.00", "ProfitLossForPeriod": "3143800000.00"}
    assert q._nse_profit(v) == 3143800000.0 and q._nse_pl(v, bank=False)["net_profit"] == 3143800000.0
    assert q._nse_profit({"ProfitOrLossAttributableToOwnersOfParent": "-50", "ProfitLossForPeriod": "-60"}) == -50.0
    assert q._nse_profit({"ProfitOrLossAttributableToOwnersOfParent": "0", "ProfitLossForPeriod": "0"}) == 0.0
    assert q._nse_profit({}) is None


def test_parse_nse_html():
    # an NSE results page from before XBRL: figures in lakh, banks' interest earned as revenue, a 0 EPS left blank
    page = """<table><tr><td>Period Ended</td><td>31-Dec-2013</td></tr>
      <tr><td>Description</td><td>Amount(Rs. in lakhs)</td></tr>
      <tr><td>(a) Net sales/income from operations (Net of excise duty)</td><td>10352081.00</td></tr>
      <tr><td>Total income from operations (net) ( a + b)</td><td>10352081.00</td></tr>
      <tr><td>Profit / (Loss) from ordinary activities before finance costs and exceptional items</td><td>778444.00</td></tr>
      <tr><td>Profit / (Loss) from ordinary activities before tax</td><td>699246.00</td></tr>
      <tr><td>Net Profit / (Loss) for the period</td><td>551083.00</td></tr>
      <tr><td>Face Value (in Rs.)</td><td>10.00</td></tr><tr><td>Paid-up equity share capital</td><td>323125.00</td></tr>
      <tr><td>(a) Basic</td><td>17.07</td></tr><tr><td>(b) Diluted</td><td>0.00</td></tr></table>"""
    r = q.parse_nse_html(page)
    assert str(r["period_end"]) == "2013-12-31" and r["revenue"] == 10352081e5 and r["pretax_income"] == 699246e5
    assert r["net_income"] == 551083e5 and r["shares"] == 323125e5 / 10 and r["eps"] == 17.07, r
    bank = q.parse_nse_html("<tr><td>Amount(Rs. in crores)</td></tr><tr><td>Interest Earned</td><td>1,239.5</td></tr>"
                            "<tr><td>Net Profit (+) / Loss (-) for the period</td><td>(12.5)</td></tr>")
    assert bank["revenue"] == 1239.5e7 and bank["net_income"] == -12.5e7


def test_parse_shareholding():
    doc = b"""<x><s:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="ShareholdingOfPromoterAndPromoterGroup_ContextI">0.5048</s:ShareholdingAsAPercentageOfTotalNumberOfShares>
      <s:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="InstitutionsForeign_ContextI">0.172</s:ShareholdingAsAPercentageOfTotalNumberOfShares>
      <s:ShareholdingAsAPercentageOfTotalNumberOfShares contextRef="InstitutionsDomestic_ContextI">0.2119</s:ShareholdingAsAPercentageOfTotalNumberOfShares>
      <s:NumberOfShareholders contextRef="ShareholdingPattern_ContextI">4651863</s:NumberOfShareholders></x>"""
    r = q.parse_shp_xbrl(doc)
    assert r["promoters"] == 0.5048 and r["fii"] == 0.172 and r["dii"] == 0.2119 and r["shareholders"] == 4651863 and r["public"] is None


def test_company_tables():
    from fundamentals import company
    t = company._table([D(2024, 3, 31), D(2025, 3, 31)], {D(2025, 3, 31): {"sales": 10.0}}, company.PL, {})
    assert t["columns"] == ["2025-03-31"] and [r["key"] for r in t["rows"]] == ["sales"]   # empty periods and rows dropped
    assert abs(company._cagr(121, 100, 2) - 0.1) < 1e-9 and company._cagr(100, -5, 2) is None
    p = company._with_derived({"sales": 200, "operating_profit": 50, "pbt": 40, "tax": 10, "net_profit": 30, "dividends_paid": -6,
                               "cfo": 70, "capex": -20})
    assert p["opm"] == 0.25 and p["tax_pct"] == 0.25 and p["dividend_payout"] == 0.2 and p["fcf"] == 50


def test_criteria_render():
    g = growth.criteria()
    assert g["name"] == "Fundamentals" and [v["key"] for v in g["views"]] == ["sepa", "canslim"]
    assert all("{" not in t for t in g["how_it_works"])
    c = sepa.criteria()
    assert len(c["tests"]) == len(sepa.TESTS) and all("{" not in t["text"] for t in c["tests"])
    assert "25%" in c["tests"][0]["text"]


def test_canslim():
    from fundamentals import canslim
    c = canslim.criteria()
    assert len(c["tests"]) == len(canslim.TESTS) and all("{" not in t["text"] for t in c["tests"])
    m = {"quarters": 12, "eps_g": [0.40, 0.30, 0.28, 0.26], "rev_g": [0.25, 0.22, 0.20, 0.18], "latest_has_prior": True,
         "eps_annual": [4.0, 3.0, 2.2, 1.6], "eps_annual_basis": "fiscal years", "roe": 0.25, "roe_source": "filings", "stale": False}
    good = {"price": 95, "high_52w": 100, "updown": 1.3, "rs_rank": 90, "inst_now": 0.40, "inst_prev": 0.38,
            "market": {"index": "SPY", "above_sma": True, "dist_days": 2}}
    assert canslim.evaluate(m, good)["verdict"] == "QUALIFIES"
    # the earnings pass but the market is in distribution: wait
    assert canslim.evaluate(m, {**good, "market": {"index": "SPY", "above_sma": True, "dist_days": 6}})["verdict"] == "EARNINGS PASS"
    # without a context (the batch), only C and A are scored: never QUALIFIES
    r = canslim.evaluate(m)
    assert r["verdict"] == "EARNINGS PASS" and r["tests"]["N"]["status"] == "na"
    # one year below 25% fails A1 (each year, not the average)
    assert canslim.evaluate({**m, "eps_annual": [4.0, 3.5, 2.2, 1.6]}, good)["verdict"] == "WEAK"
    # 20% below the high fails N
    assert canslim.evaluate(m, {**good, "price": 80})["tests"]["N"]["status"] == "fail"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
