"""Minervini's SEPA fundamentals: a strategy view over the shared metrics of `fundamentals/growth.py`.

Mark Minervini buys stocks already in a Stage-2 uptrend (the Trend Template) whose earnings, sales
and margins show the kind of growth institutions pay up for — strong, and ideally ACCELERATING. This
module only JUDGES: it takes the numbers every strategy sees (growth.metrics) and applies his eight
tests, a verdict and the "Code 33" badge. The Fundamentals page shows it as the Minervini section.

Every threshold is a module constant and the page renders the rules from them, so changing a number
here changes the explanation with it.

Not investment advice: these are screening rules of thumb over filings that can be restated.
"""

from __future__ import annotations

import datetime as dt

from .growth import ANNUAL_YEARS, metrics as _metrics, rising as _rising  # noqa: F401 — ANNUAL_YEARS is a {placeholder} in TESTS

key = "sepa"

# ---------------------------------------------------------------- thresholds
EPS_Q_GROWTH_MIN = 0.25       # F1: latest quarter's EPS growth vs a year ago
ACCEL_WINDOW = 3              # F2: look at the last N changes in the EPS growth rate ...
ACCEL_MIN_RISES = 2           # ... and want at least this many of them to be increases
SALES_Q_GROWTH_MIN = 0.20     # F3: latest quarter's sales growth ...
SALES_ACCEL_QUARTERS = 3      # ... or sales growth rising for this many quarters in a row
ANNUAL_EPS_CAGR_MIN = 0.25    # F5: annual EPS growth over ANNUAL_YEARS (growth.py), with no loss-making year
ROE_MIN = 0.17                # F6: trailing-twelve-month return on equity
DECEL_DROP_MIN = 0.15         # F8: EPS growth slowed two quarters running, by at least this many points in all
CODE33_QUARTERS = 3           # "Code 33": EPS growth, sales growth and net margin all rising for N quarters
MIN_GROWTH_READINGS = 2       # fewer EPS growth readings (of the last 4) than this = not scored

TESTS = (
    ("F1", "EPS growth", "Latest quarter's EPS up at least {EPS_Q_GROWTH_MIN:.0%} on the same quarter a year earlier"),
    ("F2", "EPS accelerating", "EPS growth rate rose in at least {ACCEL_MIN_RISES} of the last {ACCEL_WINDOW} quarters"),
    ("F3", "Sales growth", "Latest quarter's sales up at least {SALES_Q_GROWTH_MIN:.0%} a year, or sales growth rising "
                           "{SALES_ACCEL_QUARTERS} quarters in a row"),
    ("F4", "Margins expanding", "Net margin in the latest quarter above the same quarter a year earlier"),
    ("F5", "Annual EPS growth", "Annual EPS up at least {ANNUAL_EPS_CAGR_MIN:.0%} a year over the last {ANNUAL_YEARS} fiscal years "
                                "(trailing twelve months where those are missing), with no loss-making year"),
    ("F6", "Return on equity", "Trailing-twelve-month return on equity at least {ROE_MIN:.0%}"),
    ("F7", "Beat estimates", "Latest quarter's EPS above the analysts' consensus estimate"),
    ("F8", "No slowdown", "EPS growth has not slowed two quarters running by {DECEL_DROP_MIN:.0%} points or more "
                          "(Minervini's warning sign)"),
)
LEADER_REQUIRES = ("F1", "F2", "F3", "F4", "F8")     # must pass
LEADER_NOT_FAILING = ("F5", "F6")                    # must pass or be unavailable
ACCEPTABLE_REQUIRES = ("F1", "F3", "F8")


def _fmt(text: str) -> str:
    return text.format(**{k: v for k, v in globals().items() if k.isupper()})


DOC = {
    "key": key,
    "name": "Minervini SEPA",
    "strategy": "minervini",
    "description": "Part 2 of Minervini's Specific Entry Point Analysis: strong and accelerating earnings, sales and margins.",
    "thesis": "The biggest winners are usually companies whose earnings and sales are growing fast and accelerating, "
              "with expanding margins — Minervini looks for that behind a stock already in a Stage-2 uptrend.",
    "verdicts": (
        "LEADER — F1, F2, F3, F4 and F8 pass, and F5 and F6 pass or are unavailable.",
        "ACCEPTABLE — F1, F3 and F8 pass: strong growth, not (yet) all the confirmation.",
        "WEAK — anything else.",
        _fmt("NO DATA — fewer than {MIN_GROWTH_READINGS} of the last four quarters have an EPS growth reading, or the "
             "latest results are stale."),
        _fmt("CODE 33 — EPS growth, sales growth and net margin all rising for {CODE33_QUARTERS} quarters in a row "
             "(Minervini's strongest fundamental signal)."),
    ),
    "caveats": (
        "Growth from a loss is not measurable, so it does not pass F1 — Minervini treats turnarounds case by case.",
        "One-off gains and charges are not removed; Minervini would look through them.",
        "Backtests can apply these tests point in time (`--fundamentals`, from the results public on each signal's date), "
        "from 2022 onward only — stored filings start in 2021 — and without F7, whose estimates are not stored historically.",
    ),
}


def criteria() -> dict:
    return {**DOC, "tests": [{"key": k, "label": label, "text": _fmt(t)} for k, label, t in TESTS]}


def evaluate(m: dict) -> dict:
    """growth.metrics() -> {verdict, code33, passed, scored, tests}."""
    if not m.get("quarters"):
        return {"verdict": "NO DATA", "code33": False, "passed": 0, "scored": 0, "tests": {}}
    eg, sg = m["eps_g"], m["rev_g"]
    tests: dict[str, dict] = {}

    def put(k, ok, value=None, detail=""):
        tests[k] = {"status": "na" if ok is None else "pass" if ok else "fail", "value": value, "detail": detail}

    # F1
    if eg[0] is None:
        put("F1", False if m["latest_has_prior"] else None, None,
            "the year-ago quarter was a loss" if m["latest_has_prior"] else "no year-ago quarter")
    else:
        put("F1", eg[0] >= EPS_Q_GROWTH_MIN, eg[0])
    # F2: changes in the growth rate, newest first
    ch = [eg[k] - eg[k + 1] if eg[k] is not None and eg[k + 1] is not None else None for k in range(min(ACCEL_WINDOW, len(eg) - 1))]
    if len(ch) < ACCEL_WINDOW or any(c is None for c in ch):
        put("F2", None, None, f"needs {ACCEL_WINDOW + 1} quarters of EPS growth")
    else:
        rises = sum(c > 0 for c in ch)
        put("F2", rises >= ACCEL_MIN_RISES, rises, f"{rises} of {ACCEL_WINDOW} rose")
    # F3
    acc = _rising(sg, SALES_ACCEL_QUARTERS)
    if sg[0] is None:
        put("F3", None, None, "no year-ago quarter")
    else:
        put("F3", sg[0] >= SALES_Q_GROWTH_MIN or bool(acc), sg[0], "growth rising" if acc and sg[0] < SALES_Q_GROWTH_MIN else "")
    # F4
    mg, mp = m["margin"], m["margin_prior"]
    put("F4", None if mg is None or mp is None else mg > mp, None if mg is None or mp is None else mg - mp)
    # F5
    years, basis = m["eps_annual"], m["eps_annual_basis"]
    if years is None:
        put("F5", None, None, f"needs {ANNUAL_YEARS + 1} fiscal years (or {4 * (ANNUAL_YEARS + 1)} consecutive quarters)")
    elif m["eps_cagr"] is None:
        put("F5", False, None, f"a loss-making year ({basis})")
    else:
        put("F5", m["eps_cagr"] >= ANNUAL_EPS_CAGR_MIN, m["eps_cagr"], basis)
    # F6
    r = m["roe"]
    put("F6", None if r is None else r >= ROE_MIN, r, "" if r is None else f"from {m['roe_source']}")
    # F7
    last = m["surprise"]
    if last and m["surprise_current"]:
        put("F7", last["actual"] > last["estimate"], last.get("surprise"), f"{last['actual']:g} vs {last['estimate']:.2f} expected")
    else:
        put("F7", None, None, "no estimate for the latest quarter")
    # F8: two straight slowdowns adding up to DECEL_DROP_MIN
    if len(eg) < 3 or any(x is None for x in eg[:3]):
        put("F8", None, None, "needs 3 quarters of EPS growth")
    else:
        slowing = eg[0] < eg[1] < eg[2] and eg[2] - eg[0] >= DECEL_DROP_MIN
        put("F8", not slowing, eg[0] - eg[2], "slowing two quarters running" if slowing else "")

    code33 = bool(_rising(eg, CODE33_QUARTERS) and _rising(sg, CODE33_QUARTERS) and _rising(m["margins"], CODE33_QUARTERS))
    st = {k: v["status"] for k, v in tests.items()}
    if sum(x is not None for x in eg[:4]) < MIN_GROWTH_READINGS or m["stale"]:
        verdict = "NO DATA"
    elif all(st[k] == "pass" for k in LEADER_REQUIRES) and all(st[k] != "fail" for k in LEADER_NOT_FAILING):
        verdict = "LEADER"
    elif all(st[k] == "pass" for k in ACCEPTABLE_REQUIRES):
        verdict = "ACCEPTABLE"
    else:
        verdict = "WEAK"
    return {"verdict": verdict, "code33": code33, "passed": sum(v == "pass" for v in st.values()),
            "scored": sum(v != "na" for v in st.values()), "tests": tests}


def counts(r: dict) -> dict:
    """What growth.run() reports for this view."""
    return {f"sepa_{r['verdict'].lower().replace(' ', '_')}": 1, "sepa_code33": int(r["code33"])}


def score(rows: list[dict], meta: dict | None = None, today: dt.date | None = None, roe_fallback: float | None = None) -> dict:
    """Convenience: quarters -> metrics -> this view's verdict."""
    return evaluate(_metrics(rows, meta, today, roe_fallback))
