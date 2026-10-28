"""Quality momentum: the momentum baseline, ranked only among businesses that pass a quality test.

The one edge measured here is cross-sectional momentum in India. The question this asks is whether
better SELECTION improves it: each month-end, before the top N are taken, the ranked pool drops
companies whose filings -- only those public on that date -- show a weak business.

It is the baseline and nothing else. The ranking, the rebalance, the sizing, the costs and the
universe are `momentum_baseline`'s, run by the same loop (`baseline.run` with a `universe_filter`),
and the tunables are read off `MomentumBaselineStrategy`, so the filter is the only difference
between the two and the baseline is the control.

The four tests, each from code that already exists:

  * ROE        trailing-twelve-month net income over average equity, `fundamentals.growth.roe`;
  * sales      trailing-twelve-month revenue against the year-ago twelve months, from
               `fundamentals.growth.growth_series` (each quarter's year-ago figure as first published);
  * debt       (borrowings - cash) / equity on the latest balance sheet (skipped for banks/insurers);
  * cash       latest fiscal year's operating cash flow positive and free cash flow (operating cash
               flow - capex) at least QM_FCF_CONVERSION_MIN of net profit (skipped for banks/insurers).

Point in time: a quarter counts from its filing date, or `fundamental_filter.FILING_LAG_DAYS` after it
ended when none was recorded (`fundamental_filter._available`); a fiscal year's statement lines carry
no date and count `financials.LINES_FILING_LAG_DAYS` after the period ended. Missing data is NOT
eligible. Every rebalance records how many ranked names had the data and how many passed
(`quality_coverage.csv` beside the report), because thin coverage can make the filter look good or bad
by accident.

Variants (`--variant`), fixed before any run and not to be added to after one:

  quality       the strategy: the thresholds below;
  covered       the CONTROL for coverage: data for every test is required, no threshold is applied --
                "has filings" is itself a selection (bigger, older, better-documented companies);
  strict        every threshold one notch tighter (the STRICT_* constants);
  filings_only  ROE and sales only -- the two tests the quarterly filings answer, which in the US reach
                back to 2011, while statement lines (debt, cash flow) start in 2016;
  filings_covered  the coverage control for filings_only (ROE and sales data required, nothing judged).
                ADDED AFTER the first four had run, when they showed coverage itself carries a look-ahead
                bias (see the caveats); a control, not a threshold, so it can only weaken the case.

    PYTHONPATH=. python3 -m swing_screener.backtesting.quality_momentum --market us --start 2013-01-01
    PYTHONPATH=. python3 -m swing_screener.backtesting.quality_momentum --market us --start 2013-01-01 --variant covered
"""

import argparse
import datetime as dt
import logging

import pandas as pd

from fundamentals.growth import STALE_RESULTS_DAYS
from ..marketdata import corporate_actions
from ..marketdata.financials import LINES_FILING_LAG_DAYS
from ..strategies.base import PortfolioStrategy
from . import baseline
from .baseline import MomentumBaselineStrategy
from .fundamental_filter import FILING_LAG_DAYS

logger = logging.getLogger("quality_momentum")

# ---------------------------------------------------------------- the strategy's thresholds
QM_ROE_MIN_PCT = 12               # trailing ROE at least this, %
QM_NET_DEBT_EQUITY_MAX = 1.0      # (borrowings - cash) / equity at most this; net cash always passes
QM_FCF_CONVERSION_MIN_PCT = 0     # free cash flow / net profit at least this, %: 0 = free cash flow positive
QM_SALES_GROWTH_MIN_PCT = 0       # TTM sales vs the year-ago TTM, %: 0 = no shrinking sales

# ---------------------------------------------------------------- the strict variant (experiment only)
STRICT_ROE_MIN_PCT = 15
STRICT_NET_DEBT_EQUITY_MAX = 0.5
STRICT_FCF_CONVERSION_MIN_PCT = 80   # the Quality tracker's cash-conversion bar
STRICT_SALES_GROWTH_MIN_PCT = 5

# ---------------------------------------------------------------- data freshness (mechanics)
QM_STATEMENT_STALE_DAYS = 550     # a fiscal year or balance sheet older than this (about 18 months) is no data

VARIANTS = ("quality", "covered", "strict", "filings_only", "filings_covered")


def thresholds(variant: str) -> dict:
    """{test: threshold or None}; None = data required but not judged; a test left out is not applied."""
    if variant == "quality":
        return {"roe": QM_ROE_MIN_PCT / 100, "sales": QM_SALES_GROWTH_MIN_PCT / 100,
                "debt": QM_NET_DEBT_EQUITY_MAX, "cash": QM_FCF_CONVERSION_MIN_PCT / 100}
    if variant == "strict":
        return {"roe": STRICT_ROE_MIN_PCT / 100, "sales": STRICT_SALES_GROWTH_MIN_PCT / 100,
                "debt": STRICT_NET_DEBT_EQUITY_MAX, "cash": STRICT_FCF_CONVERSION_MIN_PCT / 100}
    if variant == "covered":
        return {"roe": None, "sales": None, "debt": None, "cash": None}
    if variant == "filings_only":
        return {"roe": QM_ROE_MIN_PCT / 100, "sales": QM_SALES_GROWTH_MIN_PCT / 100}
    if variant == "filings_covered":
        return {"roe": None, "sales": None}
    raise ValueError(f"--variant must be one of {VARIANTS}")


def _ttm_sales_growth(series: list[dict]) -> float | None:
    """Last four consecutive quarters' revenue over the same four a year earlier, minus one."""
    q = series[-4:]
    if len(q) < 4 or any(x["rev"] is None or x["rev_prior"] is None for x in q):
        return None
    if any(not 60 <= (q[k + 1]["end"] - q[k]["end"]).days <= 120 for k in range(3)):
        return None    # a gap: not four consecutive quarters
    prior = sum(x["rev_prior"] for x in q)
    return sum(x["rev"] for x in q) / prior - 1 if prior > 0 else None


def _latest(periods: dict, d: dt.date) -> tuple[dt.date, dict] | None:
    """The newest statement period public on `d` and not stale."""
    known = [e for e in periods if e + dt.timedelta(days=LINES_FILING_LAG_DAYS) <= d]
    if not known:
        return None
    e = max(known)
    return (e, periods[e]) if (d - e).days <= QM_STATEMENT_STALE_DAYS else None


def measure(rows: list[dict], lines: dict, d: dt.date, financial: bool) -> dict:
    """The four quality readings for one company on date `d`, from what was public by then.

    `rows` are its quarters (`financials.load`), `lines` its statement lines (`financials.load_lines`).
    A reading is None when the data for it is missing. Banks and insurers get no debt or cash reading:
    deposits are a bank's raw material, not leverage, and its cash flow statement does not mean the
    same thing (the Quality tracker skips the same tests for them).
    """
    from fundamentals import growth
    from .fundamental_filter import _available
    out = {"roe": None, "sales": None, "debt": None, "cash": None}
    rows = [r for r in rows if _available(r) <= d]
    if not rows or (d - rows[-1]["period_end"]).days > STALE_RESULTS_DAYS:
        return out
    out["roe"] = growth.roe(rows)[0]
    out["sales"] = _ttm_sales_growth(growth.growth_series(rows))
    if financial:
        return out
    bs = _latest(lines.get("BS") or {}, d)
    if bs and bs[1].get("equity") is not None:
        b = bs[1]
        # A filed balance sheet with no borrowings (or cash) line reports none: a debt-free company files
        # no debt concept. The balance sheet itself -- its equity -- is what has to be there.
        net_debt = (b.get("borrowings") or 0.0) - (b.get("cash") or 0.0)
        eq = b["equity"]
        out["debt"] = net_debt / eq if eq > 0 else (float("-inf") if net_debt <= 0 else float("inf"))
    fy = _latest(lines.get("FY") or {}, d)
    if fy and fy[1].get("cfo") is not None and fy[1].get("net_profit") is not None:
        f = fy[1]
        fcf = f["cfo"] - (f.get("capex") or 0.0)   # the same reading of an absent line as above
        # A loss year or burnt cash reads as -inf: there is no conversion of a profit to speak of.
        out["cash"] = fcf / f["net_profit"] if f["cfo"] > 0 and f["net_profit"] > 0 else float("-inf")
    return out


def passes(m: dict, limits: dict, financial: bool) -> tuple[bool, bool]:
    """(covered, passed) for one company's readings against a variant's thresholds."""
    need = [k for k in limits if not (financial and k in ("debt", "cash"))]
    if any(m[k] is None for k in need):
        return False, False
    ok = True
    for k in need:
        lim = limits[k]
        if lim is None:
            continue
        ok &= (m[k] <= lim) if k == "debt" else (m[k] >= lim)
    return True, ok


class QualityFilter:
    """The `universe_filter` baseline.run applies: drops ranked names that fail on the filings public
    on the rebalance date, and records the coverage of every rebalance."""

    def __init__(self, market: str, variant: str = "quality"):
        from fundamentals.quality import FIN_SECTORS
        from ..marketdata import financials
        self.market, self.variant, self.limits = market, variant, thresholds(variant)
        self.quarters = financials.load(market)            # honours the stage boundary (asof)
        meta = financials.load_meta(market)
        self.financial = {s: ((m.get("profile") or {}).get("sector") in FIN_SECTORS or m.get("layout") == "bank")
                          for s, m in meta.items()}
        self._lines: dict = {}
        self.rows: list[dict] = []

    def lines(self, sym: str) -> dict:
        if sym not in self._lines:
            from ..marketdata import financials
            self._lines[sym] = financials.load_lines(self.market, sym) if sym in self.quarters else {}
        return self._lines[sym]

    def __call__(self, today, scores: dict) -> dict:
        d = pd.Timestamp(today).date()
        kept, covered = {}, 0
        for s, v in scores.items():
            fin = self.financial.get(s, False)
            m = measure(self.quarters.get(s, []), self.lines(s), d, fin)
            c, ok = passes(m, self.limits, fin)
            covered += c
            if ok:
                kept[s] = v
        self.rows.append({"date": d, "ranked": len(scores), "covered": covered, "passed": len(kept)})
        return kept

    def coverage(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["date", "ranked", "covered", "passed"])

    def notes(self) -> list[str]:
        c = self.coverage()
        if c.empty:
            return []
        first = c[c["passed"] > 0]["date"].min() if (c["passed"] > 0).any() else None
        by_year = c.assign(y=pd.to_datetime(c["date"]).dt.year).groupby("y")[["ranked", "covered", "passed"]].median()
        yrs = "; ".join(f"{y}: {int(r.covered)}/{int(r.ranked)} covered, {int(r.passed)} pass"
                        for y, r in by_year.iterrows())
        return [
            f"QUALITY FILTER ({self.variant}): each month-end the ranked pool keeps only companies whose "
            f"filings public on that date pass {', '.join(self.limits)}; missing data is not eligible.",
            f"Fundamentals coverage, median per rebalance by year (covered of ranked, passing): {yrs}.",
            ("First rebalance with any passing name: " + str(first) + ". Before it the book holds cash."
             if first is not None else "No rebalance had a passing name: the book held cash throughout."),
        ]


DOC = {
    "key": "quality_momentum",
    "name": "Quality momentum",
    "description": "The momentum baseline, ranked only among companies whose filings public on the "
                   "rebalance date show ROE of at least {QM_ROE_MIN_PCT}%, modest net debt, positive free "
                   "cash flow and no shrinking sales; top {top_n}, rebalanced every month-end.",
    "status": (
        "FAILS IN THE OPTIMISE STAGE (US); UNTESTABLE THERE (India). Optimise only (2013-01-01 to "
        "2021-12-31); not verified. "
        "The clean control is the covered variant, not momentum_baseline: the stored fundamentals are "
        "fetched for TODAY's liquid and Stage-2 stocks, so requiring them drops the momentum names that "
        "later collapsed -- a look-ahead that favours every filtered run over the baseline (see the "
        "caveats). Covered shares that bias; the gap between it and this strategy is the quality test's "
        "own effect. "
        "US, 2017-04-01 to 2021-12-31 (the full test can judge non-financial companies only from 2017, when "
        "stored balance sheets and cash flows begin): this strategy 14.86% CAGR, max drawdown -41.5%; the "
        "covered control 29.85%, -50.1%; momentum_baseline 9.17%, -57.2%; SPY 15.95%, -34.1% "
        "(excess -1.09). Against the covered control the test costs 15.0 points a year for 8.6 points less "
        "drawdown: it removes the strongest names (CELH, NTLA, MRNA, GME among them). The strict variant is "
        "no better (14.61%, -47.3%). Its +5.69 over the baseline is the look-ahead, not the test. "
        "US, 2013 to 2021, ROE and sales only (filings_only): 14.51%, -42.1%, against momentum_baseline's "
        "-2.11%, -79.9% and SPY's 14.01%; its coverage control (filings_covered) decides what that means. "
        "India: stored filings begin in 2021, so no rebalance in the window had a covered name and the book "
        "held cash -- no evidence either way. "
        "PASS CRITERION FOR A FUTURE VERIFY RUN, fixed before it is run (2022-01-01 to today, once, variant "
        "`quality` and its covered control, defaults unchanged): in EACH market, CAGR at least 2 points a "
        "year above the covered control in the same window AND max drawdown no deeper than the covered "
        "control's; reported beside momentum_baseline (and momentum_vol_scaled in India) for context only, "
        "since those comparisons carry the look-ahead. Failing any part is a fail, and is reported as one. "
        "On the optimise evidence the US is expected to fail; spending the India verify run is the user's call."
    ),
    "thesis": "Momentum buys whatever rose most, and some of what rises most is a weak business carried by "
              "a story -- losses, debt, shrinking sales. Those are the names most likely to give a rally back. "
              "Quality and momentum are documented separately as rewarded traits (Asness, Frazzini and "
              "Pedersen's 'Quality minus junk' for the first), and requiring both asks for a strong trend in a "
              "business that can carry it. If selection is what limits the baseline, dropping the junk "
              "before ranking should lift return or cut drawdown; if it does neither, the baseline's edge "
              "does not come from the names a quality screen would remove.",
    "how_it_works": (
        "Exactly the momentum baseline -- same universe, floors, 200-day trend test, {lookback}-session "
        "momentum skipping {skip}, top {top_n} equal-weighted, {cost_bps}bps a side, month-end rebalance -- "
        "with one step added: before the top {top_n} are taken, the ranked pool drops every company that "
        "fails the quality test on the filings public that day.",
        "The test, from the latest public filings: trailing-twelve-month ROE at least {QM_ROE_MIN_PCT}%; "
        "trailing-twelve-month sales at least the year-ago twelve months (growth at least "
        "{QM_SALES_GROWTH_MIN_PCT}%); net debt at most {QM_NET_DEBT_EQUITY_MAX}x equity (net cash always "
        "passes); and in the latest fiscal year positive operating cash flow, with free cash flow at least "
        "{QM_FCF_CONVERSION_MIN_PCT}% of net profit -- that is, positive. Banks and insurers take the ROE and "
        "sales tests only.",
        "A company with no data for a test is not eligible. Each rebalance records how many ranked names "
        "had the data and how many passed, in the run's report and quality_coverage.csv.",
        "Four variants were fixed before any run, as experiments on this one: covered (data required, no "
        "threshold -- the control for having filings at all), strict (ROE {STRICT_ROE_MIN_PCT}%, net debt "
        "{STRICT_NET_DEBT_EQUITY_MAX}x equity, free cash flow {STRICT_FCF_CONVERSION_MIN_PCT}% of profit, "
        "sales growth {STRICT_SALES_GROWTH_MIN_PCT}%) and filings_only (ROE and sales only). A fifth, "
        "filings_covered (ROE and sales data required, nothing judged), was added after those ran, as "
        "filings_only's coverage control.",
    ),
    "entry_rules": (
        "Everything the momentum baseline requires on the month-end session: universe, price and turnover "
        "floors, close above the 200-day average, the {liquidity_top}-name liquid pool, a 12-1 momentum "
        "score. See momentum_baseline's Entry.",
        "Public by then. A quarter counts from its filing date, or {FILING_LAG_DAYS} days after it ended when "
        "the source recorded none. A fiscal year's or balance sheet's lines carry no date and count "
        "{LINES_FILING_LAG_DAYS} days after the period ended. A company whose latest quarter is over "
        "{STALE_RESULTS_DAYS} days old, or whose latest fiscal year or "
        "balance sheet is over {QM_STATEMENT_STALE_DAYS} days old, has no data.",
        "ROE. Net income of the last four quarters over average equity (latest and about a year before), "
        "at least {QM_ROE_MIN_PCT}%. Needs four quarters spanning about nine months and a positive equity.",
        "Sales. Revenue of the last four consecutive quarters over the same quarters' year-ago revenue as "
        "first published, minus one, at least {QM_SALES_GROWTH_MIN_PCT}%.",
        "Debt (not banks or insurers). (Borrowings - cash) / equity on the latest public balance sheet, at "
        "most {QM_NET_DEBT_EQUITY_MAX}. A balance sheet with no borrowings or cash line counts it as zero; "
        "the balance sheet's equity must be there. Negative equity fails unless the company has net cash.",
        "Cash (not banks or insurers). Latest public fiscal year: operating cash flow positive, net profit "
        "positive, and (operating cash flow - capex) / net profit at least {QM_FCF_CONVERSION_MIN_PCT}%. No "
        "capex line counts as zero.",
        "Banks and insurers: the company's sector is Financial Services, or it files the bank layout.",
        "Selection, weighting, fills and costs: as the momentum baseline, over the names that pass. With "
        "fewer than {top_n} passing it holds only those; with none it holds cash.",
    ),
    "exit_rules": (
        "As the momentum baseline: sold at a month-end close, less {cost_bps}bps, when not in the new top "
        "{top_n} -- which now includes failing the quality test on that month-end's public filings.",
        "Nothing sells between month-ends; there is no stop and no target.",
    ),
    "caveats": (
        "**Having fundamentals is a look-ahead filter.** Stored filings exist for the companies the "
        "financials job fetches: today's most liquid tradable stocks plus today's Stage-2 stocks. A 2020 "
        "momentum name that collapsed and is illiquid now was never fetched, so it is 'missing data' and "
        "never eligible -- in the US 2017-2021 run, 72 of the 102 names the baseline held and the covered "
        "control did not had no filings fetched at all. That lifts every variant above momentum_baseline "
        "for reasons a trader could not have known. Judge the test against the covered control, which "
        "carries the same bias; a comparison with the baseline overstates it.",
        "**India has no stored filings before 2021.** The optimise window therefore contains no India test "
        "at all: the book is in cash until the first covered rebalance. The verify window (2022 on) is the "
        "first and only look, so its pass criterion is written in Status before it is run.",
        "**US statement lines start in 2016.** Quarterly results reach back to 2011, but balance sheets and "
        "cash flows only to fiscal 2016. Before early 2017 the only companies the full test can judge are "
        "banks and insurers, which skip the debt and cash tests -- so a run from 2013 holds a book of banks "
        "for its first four years, which is not this strategy. The full test is compared with the baseline "
        "from 2017-04-01; the filings_only variant covers 2013 on.",
        "**Coverage is a selection of its own.** Companies with filings on record are larger and older "
        "than the tape. The covered variant -- data required, nothing judged -- separates that effect from "
        "the quality test's; a result that the covered control matches is not the filter's.",
        "**US annual and balance-sheet lines are the latest filed values**, so a later restatement is "
        "visible earlier than it was. Quarterly figures are as first reported.",
        "**Sector is today's.** Banks and insurers are recognised from the current company profile, not "
        "the one at the time.",
        "**Survivorship bias and dividends** apply exactly as for the momentum baseline, and so does its US "
        "price floor, read as the price traded that day (v1.3).",
    ),
}


class QualityMomentumStrategy(PortfolioStrategy):
    """The momentum baseline with a point-in-time quality filter on the ranked pool."""

    key = DOC["key"]
    doc = DOC
    family = "quality_momentum"
    version = "1.3"
    changelog = (
        ("1.3", "2026-10-29",
         "The momentum baseline's pool, which this filters, changes with it. The US $10 price floor reads the price the stock traded at that day: the stored close multiplied back by every later split Yahoo records (backtesting/spec.traded_close, the RS rating's fix in 1d16854). Stored closes are back-adjusted for every later split, so the floor had dropped the later multi-baggers from their early years -- NFLX's October 2009 close is stored as $0.72 against the ~$50 it traded at, NVDA read under $10 until mid-2020. On 2016-06-30 the US floor admits 2,092 stocks instead of 2,382: 47 that later split (NVDA, CMG, ANET, CPRT ...) come in, 337 that later reverse-split, and so really traded under $10, go out. India has no price floor and is unchanged."),
        ("1.2", "2026-10-26",
         "Signals read total return: the momentum ranking, volatility weights and the 200-day trend test "
         "now use closes back-adjusted for the special dividends and demergers a holder is credited "
         "(corporate_actions.back_adjust). On traded prices a demerged parent read as a crash for a year "
         "-- out of the ranking, failing the trend test, and given a huge volatility. Fills, valuation, "
         "the price floor and turnover still read traded prices. Ratios only, so no action after the "
         "signal date can leak into it."),
        ("1.1", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited (marketdata/corporate_actions.py). On the ex-date a held position receives the cash, where the stored close only falls by it -- AURUM's 98% special dividend on 2020-12-23 was booked as a -98% loss, about 10% of the India vol-scaled book. Ordinary dividends stay out of strategy and benchmark. Stored prices were also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py correct)."),
        ("1.0", "2026-10-25",
         "First version: momentum_baseline's rules unchanged, the ranked pool narrowed each month-end "
         "to companies passing ROE, sales, net debt and free-cash-flow tests on the filings public that "
         "day. Thresholds and the three experiment variants were fixed before any run."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"]) + (corporate_actions.CAVEAT_HELD,)
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "trend"
    runner = "quality_momentum"
    live_selection = False       # baseline.current_selection would show the ranking without the filter

    # the baseline's tunables, read off it: the filter must be the only difference from the control
    top_n = MomentumBaselineStrategy.top_n
    lookback = MomentumBaselineStrategy.lookback
    skip = MomentumBaselineStrategy.skip
    cost_bps = MomentumBaselineStrategy.cost_bps
    liquidity_top = MomentumBaselineStrategy.liquidity_top

    param_docs = (
        ("Holdings", "top_n", "Names held at a time (the baseline's)."),
        ("Momentum lookback", "lookback", "Bars of return used to rank (the baseline's 12 months)."),
        ("Skip", "skip", "Most recent bars excluded (the baseline's 12-1 convention)."),
        ("Cost per side", "cost_bps", "Basis points per side (the baseline's)."),
        ("Liquidity cutoff", "liquidity_top", "Only the N most liquid names are ranked (the baseline's)."),
        ("ROE floor", "QM_ROE_MIN_PCT", "Trailing-twelve-month return on average equity, %, at least."),
        ("Sales growth", "QM_SALES_GROWTH_MIN_PCT", "Trailing-twelve-month sales growth, %, at least; 0 = not shrinking."),
        ("Net debt / equity", "QM_NET_DEBT_EQUITY_MAX", "At most; net cash always passes. Not for banks."),
        ("Free cash flow / profit", "QM_FCF_CONVERSION_MIN_PCT", "Latest fiscal year, %, at least; 0 = positive. Not for banks."),
        ("Statement freshness", "QM_STATEMENT_STALE_DAYS", "A fiscal year or balance sheet older than this is no data."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    """baseline.main with the quality filter, plus `--variant`; writes quality_coverage.csv."""
    from pathlib import Path
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--variant", default="quality", choices=VARIANTS)
    pre.add_argument("--market", required=True)
    known, rest = pre.parse_known_args(argv)
    rest = ["--market", known.market, *rest]
    if "--strategy" not in rest:
        rest = ["--strategy", QualityMomentumStrategy.key, *rest]
    filt = QualityFilter(known.market, known.variant)
    r = baseline.main(rest, universe_filter=filt,
                      run_suffix="" if known.variant == "quality" else f"_{known.variant}",
                      reproduce_extra=() if known.variant == "quality" else (f"--variant {known.variant}",))
    if r:
        filt.coverage().to_csv(Path(r["run_dir"]) / "quality_coverage.csv", index=False)
    return r


if __name__ == "__main__":
    main()
