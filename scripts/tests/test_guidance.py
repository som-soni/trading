"""Company guidance parser (marketdata/guidance.py): the outlook section and the figures read from it.

Each case is a short outlook in a form seen in real US results releases — bullets after a lead-in, prose,
a GAAP / non-GAAP table, quarter and year columns, dated guidance versions, ranges, tolerances, growth
ranges in words — and what the parser must read from it. No network.

    PYTHONPATH=. .venv/bin/python -m tests.test_guidance
"""

from swing_screener.marketdata import guidance as g


def items(text):
    sec = g.outlook_section(text)
    assert sec, f"no outlook section found in:\n{text[:200]}"
    return [i for i in g.parse(sec) if i["unit"]]


def find(its, metric, kind=None, basis="any", unit=None):
    hits = [i for i in its if i["metric"] == metric and (kind is None or i["period_kind"] == kind)
            and (basis == "any" or i["basis"] == basis) and (unit is None or i["unit"] == unit)]
    assert hits, f"no {metric}/{kind}/{basis}/{unit} in {[(i['metric'], i['period_kind'], i['basis'], i['unit']) for i in its]}"
    return hits[0]


def close(a, b):
    return abs(a - b) <= 1e-9 * max(1, abs(b))


def test_bullets_after_lead_in():
    its = items("Financial Outlook\nFor the first quarter of fiscal 2027, the company expects:\n"
                "• Revenue of $935 million to $939 million, approximately 19% year-over-year growth.\n"
                "• Non-GAAP net income per share of approximately $1.15 to $1.16, assuming 170 million shares.\n"
                "For the full year fiscal 2027, the company expects:\n"
                "• Revenue of approximately $3.908 billion to $3.938 billion, growth of 16.6% to 17.5%.\n"
                "• Non-GAAP gross margin of approximately 80%\nConference Call\nThe company will host a call.")
    r = find(its, "revenue", "Q")
    assert close(r["low"], 935e6) and close(r["high"], 939e6) and r["fiscal_quarter"] == 1 and r["fiscal_year"] == 2027
    e = find(its, "eps", "Q")
    assert e["basis"] == "non_gaap" and close(e["low"], 1.15) and close(e["high"], 1.16)
    y = find(its, "revenue", "FY")
    assert close(y["low"], 3.908e9) and y["fiscal_year"] == 2027
    m = find(its, "gross_margin", "FY")
    assert m["unit"] == "pct" and close(m["low"], 0.80)
    assert not any("call" in i["text"].lower() for i in its), "the section must end at Conference Call"


def test_tolerances():
    its = items("Outlook\nNVIDIA's outlook for the third quarter of fiscal 2027 is as follows:\n"
                "• Revenue is expected to be $108.0 billion, plus or minus 2%.\n"
                "• GAAP and non-GAAP gross margins are expected to be 74.0%, plus or minus 50 basis points.")
    r = find(its, "revenue", "Q")
    assert close(r["low"], 105.84e9) and close(r["high"], 110.16e9)
    m = find(its, "gross_margin", "Q")
    assert m["basis"] == "both" and close(m["low"], 0.735) and close(m["high"], 0.745)


def test_gaap_non_gaap_table():
    its = items("Business Outlook\nThe following table presents Micron's guidance for the first quarter of 2027:\n"
                "FQ1-27 | GAAP (1) Outlook | Non-GAAP (2) Outlook\n"
                "Revenue | $61.5 billion ± $1.5 billion | $61.5 billion ± $1.5 billion\n"
                "Diluted earnings per share | $37.84 ± $1.00 | $38.15 ± $1.00")
    assert close(find(its, "eps", basis="gaap")["low"], 36.84)
    n = find(its, "eps", basis="non_gaap")
    assert close(n["low"], 37.15) and close(n["high"], 39.15) and n["fiscal_quarter"] == 1 and n["fiscal_year"] == 2027
    assert close(find(its, "revenue")["low"], 60e9)


def test_quarter_and_year_columns_in_millions():
    its = items("Financial Outlook\nCrowdStrike is providing the following guidance (in millions, except per share):\n"
                "Q3 FY27 Guidance | Full Year FY27 Guidance\n"
                "Total revenue | $1,523.2 - $1,529.2 million | $5,991.1 - $6,011.1 million\n"
                "Non-GAAP net income per share, diluted | $0.31 | $1.25 - $1.26")
    q, y = find(its, "revenue", "Q"), find(its, "revenue", "FY")
    assert close(q["low"], 1523.2e6) and close(y["high"], 6011.1e6) and y["fiscal_year"] == 2027
    assert close(find(its, "eps", "FY")["high"], 1.26), "EPS must not take the table's 'in millions'"


def test_latest_guidance_version():
    its = items("Guidance\nThe following guidance reflects the Company's expectations as of August 20, 2026.\n"
                "Fiscal year 2027\n"
                "Consolidated metric | Original from 2.19.2026 | As of 5.21.2026 | As of 8.20.2026\n"
                "Net sales (cc) | Increase 3.5% to 4.5% | Unchanged | Increase 4.0% to 5.0%\n"
                "Adj. EPS | $2.75 to $2.85 | Unchanged | $2.80 to $2.87")
    e = find(its, "eps", "FY")
    assert close(e["low"], 2.80) and close(e["high"], 2.87) and e["basis"] == "non_gaap" and e["fiscal_year"] == 2027
    s = find(its, "revenue", "FY", unit="growth")
    assert close(s["low"], 0.04) and close(s["high"], 0.05)


def test_two_periods_in_one_sentence_and_words():
    its = items("Outlook\nThe company expects the following.\n"
                "Adjusted EPS is expected to be $0.62 to $0.64 for Q3 and $2.80 to $2.87 for FY27.\n"
                "Organic net sales are expected to range between down 1.5 percent and up 0.5 percent.\n"
                "Adjusted operating profit is expected to be down 13 percent to down 8 percent in constant currency.")
    q, y = find(its, "eps", "Q"), find(its, "eps", "FY")
    assert close(q["high"], 0.64) and close(y["low"], 2.80) and y["fiscal_year"] == 2027
    s = find(its, "revenue", unit="growth")
    assert close(s["low"], -0.015) and close(s["high"], 0.005) and not g.headline_revenue(s["metric_label"])
    o = find(its, "operating_income", unit="growth")
    assert close(o["low"], -0.13) and close(o["high"], -0.08)


def test_results_are_not_guidance():
    its = items("Outlook\nFor the third quarter of 2026, the Company expects net revenue to be in the range of "
                "$2.290 billion to $2.320 billion.\nSecond-quarter revenue was $89.0 billion, up 18% from the previous quarter.\n"
                "Net sales | 3,998 | 4,273 | -6%\nOperating margin | 13.2% | 13.6%")
    assert len([i for i in its if i["metric"] == "revenue"]) == 1, its
    assert not any(i["metric"] == "operating_margin" for i in its), "a results table row was read as guidance"


def test_no_guidance_in_release():
    assert g.outlook_section("Business Outlook\nMicrosoft will provide forward-looking guidance in connection with this "
                             "quarterly earnings announcement on its earnings conference call and webcast.") == ""
    assert g.outlook_section("Apple reported revenue of $102 billion.\nRevenue grew 8%.") == ""


def test_headline_revenue():
    assert g.headline_revenue("Revenue") and g.headline_revenue("Total revenues") and g.headline_revenue("Net sales (cc)")
    assert g.headline_revenue("Revenue growth")
    assert not g.headline_revenue("Cloud revenue") and not g.headline_revenue("Annual recurring revenue")


def main():
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)


if __name__ == "__main__":
    main()
