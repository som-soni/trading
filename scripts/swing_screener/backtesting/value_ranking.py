"""Value ranking: hold the cheapest liquid stocks on four price ratios, read from point-in-time filings.

Twenty-seven of the thirty-one strategies here are trend or momentum bets, so their losing years tend to
come together. Value -- buying what is cheap against its earnings, book, sales and cash flow -- is the
classic style that tends to do well when momentum does badly (Asness, Moskowitz and Pedersen, "Value and
Momentum Everywhere"). This asks whether a plain value composite, on the same liquid universe and the same
rebalance loop as the momentum baseline, earns near its benchmark with little correlation to momentum.

Reuse, not a second copy:

  * the universe, floors, liquidity pool, fills, costs and rebalance loop are `baseline.run`'s; the value
    composite is a `universe_filter` that turns the eligible pool's scores into value scores, the way
    `quality_momentum` narrows the same pool. The 200-day trend test is switched off (`trend_filter`):
    a value book buys what has fallen, and the trend test would remove exactly those names;
  * the filings are `financials.load` / `financials.load_lines` (both stop at a stage's boundary, asof);
    a quarter counts from its filing date (`fundamental_filter._available`), a statement line
    `LINES_FILING_LAG_DAYS` after its period (`quality_momentum._latest`), ROE is `fundamentals.growth.roe`;
  * prices are split-adjusted, filings are not: market value is the latest quarter's share count times
    the adjusted close times every split after the day that count was reported (`spec.split_factor_after`),
    so a split between the filing and the rebalance cannot halve or double a ratio.

The rules (fixed before the first run, 2026-11-14):

  value     earnings yield (trailing four quarters' net income / market value), book-to-price (latest
            equity / market value), sales-to-price (trailing revenue / market value), free-cash-flow yield
            (latest fiscal year's operating cash flow - capex / market value). Each is ranked as a
            percentile across the eligible pool (higher = cheaper), the ranks averaged; a stock needs at
            least VR_MIN_RATIOS of the ratios that apply to it. Banks and insurers skip sales-to-price and
            free-cash-flow yield, utilities free-cash-flow yield (the ratio does not describe them), so a
            bank needs both of its two and a utility all three of its three. With --sector-neutral every
            ratio applies to every company and is ranked within its sector instead.
  quality   (guard) drop the bottom VR_QUALITY_DROP_PCT% of the valued names by quality: the average of
            the percentile ranks of gross profitability (trailing gross profit / total assets, Novy-Marx)
            and ROE, whichever are stored; a company with neither is dropped.
  momentum  (guard) drop the bottom VR_MOMENTUM_DROP_PCT% of the eligible pool by 12-1 momentum.

Variants (`--variant`): base (no guard, THE DEFAULT), quality, momentum, both. Monthly rebalancing is the
baseline's own `--rebalance ME`.

    PYTHONPATH=. python3 -m swing_screener.backtesting.value_ranking --market us --start 2013-01-01
    PYTHONPATH=. python3 -m swing_screener.backtesting.value_ranking --market us --start 2013-01-01 --variant both
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

logger = logging.getLogger("value_ranking")

# ---------------------------------------------------------------- the strategy's rules
VR_MIN_RATIOS = 3               # a stock needs at least this many of the four ratios (capped at those that apply)
VR_QUALITY_DROP_PCT = 33        # quality guard: drop this bottom share of the valued names, %
VR_MOMENTUM_DROP_PCT = 20       # momentum guard: drop this bottom share of the eligible pool by 12-1 momentum, %
VR_TOP_N = 20                   # names held
VR_STATEMENT_STALE_DAYS = 550   # a fiscal year or balance sheet older than this (about 18 months) is no data

RATIOS = ("earnings_yield", "book_to_price", "sales_to_price", "fcf_yield")
QUALITY = ("gross_profitability", "roe")
UTILITY_SECTORS = {"Utilities"}
# the ratios that do not describe a company of that kind: a bank's revenue is interest earned and its cash
# flow statement moves deposits; a utility's capex is the business, so its free cash flow is negative by design
NOT_APPLICABLE = {"financial": {"sales_to_price", "fcf_yield"}, "utility": {"fcf_yield"}}

VARIANTS = ("base", "quality", "momentum", "both")
DEFAULT_VARIANT = "base"


def _ttm(rows: list[dict], field: str) -> float | None:
    """Sum of `field` over the last four consecutive quarters, else None (a gap or a missing figure)."""
    q = rows[-4:]
    if len(q) < 4 or any(r.get(field) is None for r in q):
        return None
    if any(not 60 <= (q[k + 1]["period_end"] - q[k]["period_end"]).days <= 120 for k in range(3)):
        return None
    return float(sum(r[field] for r in q))


def _latest(periods: dict, d: dt.date) -> dict | None:
    """The newest statement period public on `d` and no older than VR_STATEMENT_STALE_DAYS
    (quality_momentum's reader, with this strategy's own freshness limit)."""
    from .quality_momentum import _latest as latest
    hit = latest(periods, d, VR_STATEMENT_STALE_DAYS)
    return hit[1] if hit else None


def fundamentals_on(rows: list[dict], lines: dict, d: dt.date) -> dict | None:
    """One company's figures public on `d`: TTM net income, revenue and gross profit, equity, free cash flow,
    total assets, ROE, the latest share count and the date that count is on the basis of. None when the
    latest public quarter is stale (over STALE_RESULTS_DAYS old) or none is public."""
    from fundamentals import growth
    from .fundamental_filter import _available
    rows = [r for r in rows if _available(r) <= d]
    if not rows or (d - rows[-1]["period_end"]).days > STALE_RESULTS_DAYS:
        return None
    last = rows[-1]
    bs = _latest(lines.get("BS") or {}, d) or {}
    fy = _latest(lines.get("FY") or {}, d) or {}
    equity = last.get("equity") if last.get("equity") is not None else bs.get("equity")
    fcf = (fy["cfo"] - (fy.get("capex") or 0.0)) if fy.get("cfo") is not None else None
    # SEC restates a quarter's weighted shares for any split before the filing, so the count is on the
    # filing date's basis; NSE's paid-up / face value is the count at the period end
    basis = _available(last) if last.get("source") == "sec_edgar" else last["period_end"]
    return {"net_income": _ttm(rows, "net_income"), "revenue": _ttm(rows, "revenue"),
            "gross_profit": _ttm(rows, "gross_profit"), "equity": equity, "fcf": fcf,
            "total_assets": bs.get("total_assets"), "roe": growth.roe(rows)[0],
            "shares": last.get("shares"), "basis": basis}


def ratios(f: dict, mcap: float | None) -> dict:
    """The four value ratios and the two quality readings from `fundamentals_on` and a market value."""
    out = {k: None for k in (*RATIOS, *QUALITY)}
    if mcap and mcap > 0:
        for k, num in (("earnings_yield", f["net_income"]), ("book_to_price", f["equity"]),
                       ("sales_to_price", f["revenue"]), ("fcf_yield", f["fcf"])):
            out[k] = num / mcap if num is not None else None
    ta = f.get("total_assets")
    out["gross_profitability"] = f["gross_profit"] / ta if f.get("gross_profit") is not None and ta and ta > 0 else None
    out["roe"] = f.get("roe")
    return out


def composite(table: pd.DataFrame, applicable: pd.DataFrame, groups: pd.Series | None) -> pd.Series:
    """Average percentile rank of the applicable ratios (higher = cheaper), for the rows holding at least
    VR_MIN_RATIOS of them (or all of them, when fewer apply). `groups` ranks within each group."""
    vals = table[list(RATIOS)].where(applicable)
    ranks = vals.groupby(groups).rank(pct=True) if groups is not None else vals.rank(pct=True)
    have = vals.notna().sum(axis=1)
    need = applicable.sum(axis=1).clip(upper=VR_MIN_RATIOS)
    return ranks.mean(axis=1)[(have >= need) & (have > 0)]


class ValueFilter:
    """The `universe_filter` baseline.run applies: replaces the eligible pool's momentum scores with the
    value composite (after the momentum guard, which reads them), applies the quality guard, and records
    each rebalance's coverage."""

    def __init__(self, market: str, variant: str = DEFAULT_VARIANT, sector_neutral: bool = False):
        from fundamentals.quality import FIN_SECTORS
        from ..marketdata import financials
        if variant not in VARIANTS:
            raise ValueError(f"--variant must be one of {VARIANTS}")
        self.market, self.variant, self.sector_neutral = market, variant, sector_neutral
        self.quality_guard = variant in ("quality", "both")
        self.momentum_guard = variant in ("momentum", "both")
        self.quarters = financials.load(market)            # honours the stage boundary (asof)
        meta = financials.load_meta(market)
        self.sector = {s: (m.get("profile") or {}).get("sector") for s, m in meta.items()}
        self.kind = {s: ("financial" if self.sector[s] in FIN_SECTORS or m.get("layout") == "bank"
                         else "utility" if self.sector[s] in UTILITY_SECTORS else None)
                     for s, m in meta.items()}
        # statements in another currency than the price (Yahoo's foreign filers) cannot be set against it
        self.foreign = {s for s, m in meta.items() if financials.statement_currency(market, m)}
        self.asked = set(meta)
        self._lines: dict = {}
        self.rows: list[dict] = []
        self.last_table: pd.DataFrame | None = None

    def lines(self, sym: str) -> dict:
        if sym not in self._lines:
            from ..marketdata import financials
            self._lines[sym] = financials.load_lines(self.market, sym) if sym in self.quarters else {}
        return self._lines[sym]

    def _closes(self, d: dt.date, symbols: list) -> dict:
        """Stored (split-adjusted) closes on `d`, one query; `d` is a rebalance session inside the stage."""
        from ..marketdata import asof, db
        end = asof.end_date()
        if end and d > end:
            return {}
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT symbol, close FROM prices WHERE market=%s AND date=%s AND symbol = ANY(%s)",
                        (self.market, d, list(symbols)))
            return {s: float(c) for s, c in cur.fetchall() if c is not None}

    def table(self, d: dt.date, symbols: list) -> pd.DataFrame:
        """Ratios and quality readings for `symbols` on `d`, from what was public then."""
        from .spec import split_factor_after
        figs = {}
        for s in symbols:
            if s in self.foreign:
                continue
            f = fundamentals_on(self.quarters.get(s, []), self.lines(s), d)
            if f is not None and f["shares"] and f["shares"] > 0:
                figs[s] = f
        if not figs:
            return pd.DataFrame(columns=[*RATIOS, *QUALITY])
        closes = self._closes(d, list(figs))
        bases = pd.DatetimeIndex(sorted({pd.Timestamp(f["basis"]) for f in figs.values()}))
        k = split_factor_after(self.market, bases, list(figs))
        out = {}
        for s, f in figs.items():
            px = closes.get(s)
            factor = float(k.at[pd.Timestamp(f["basis"]), s]) if s in k.columns else 1.0
            out[s] = ratios(f, f["shares"] * px * factor if px else None)
        return pd.DataFrame.from_dict(out, orient="index")

    def __call__(self, today, scores: dict) -> dict:
        d = pd.Timestamp(today).date()
        pool = dict(scores)
        if self.momentum_guard and pool:
            pct = pd.Series(pool).rank(pct=True)
            pool = {s: v for s, v in pool.items() if pct[s] > VR_MOMENTUM_DROP_PCT / 100}
        t = self.table(d, list(pool))
        valued = pd.Series(dtype=float)
        if not t.empty:
            if self.sector_neutral:
                applicable = pd.DataFrame(True, index=t.index, columns=list(RATIOS))
                groups = pd.Series({s: self.sector.get(s) or "Unknown" for s in t.index})
            else:
                applicable = pd.DataFrame({r: [r not in NOT_APPLICABLE.get(self.kind.get(s), ()) for s in t.index]
                                           for r in RATIOS}, index=t.index)
                groups = None
            valued = composite(t, applicable, groups)
        kept = valued
        if self.quality_guard and not valued.empty:
            q = t.loc[valued.index, list(QUALITY)].rank(pct=True).mean(axis=1)
            q = q.dropna()
            kept = valued[q.index][q.rank(pct=True) > VR_QUALITY_DROP_PCT / 100]
        self.last_table = t
        self.rows.append({"date": d, "ranked": len(scores), "after_momentum_guard": len(pool),
                          "valued": len(valued), "passed": len(kept),
                          "never_fetched": sum(1 for s in scores if s not in self.asked)})
        return {s: float(v) for s, v in kept.items()}

    def coverage(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["date", "ranked", "after_momentum_guard", "valued", "passed",
                                                "never_fetched"])

    def notes(self) -> list[str]:
        c = self.coverage()
        if c.empty:
            return []
        by_year = c.assign(y=pd.to_datetime(c["date"]).dt.year).groupby("y")[
            ["ranked", "valued", "passed", "never_fetched"]].median()
        yrs = "; ".join(f"{y}: {int(r.valued)}/{int(r.ranked)} valued, {int(r.passed)} eligible, "
                        f"{int(r.never_fetched)} never fetched" for y, r in by_year.iterrows())
        guards = [g for g, on in (("quality", self.quality_guard), ("momentum", self.momentum_guard)) if on]
        return [
            f"VALUE RANKING ({self.variant}{', sector-neutral' if self.sector_neutral else ''}): the eligible pool "
            f"(no 200-day trend test) is ranked on a value composite of {', '.join(RATIOS)} from the filings "
            f"public on each rebalance date; guards: {', '.join(guards) or 'none'}. The 'momentum252' in the run "
            "name is the pool's score before the filter replaces it, not this strategy's ranking.",
            f"Fundamentals coverage, median per rebalance by year (valued of ranked, eligible after guards, never "
            f"fetched): {yrs}.",
        ]


DOC = {
    "key": "value_ranking",
    "name": "Value ranking",
    "description": "The {top_n} cheapest liquid stocks on a composite of earnings yield, book-to-price, "
                   "sales-to-price and free-cash-flow yield, from the filings public on the rebalance date; "
                   "equal weight, rebalanced every quarter-end.",
    "status": (
        "NEW (v1.0, 2026-11-14): NOT YET MEASURED. Optimise-stage runs (in-sample, US, 2013-01-01 to "
        "2021-12-31) are queued for the base composite, each guard on its own and both guards. Pass criteria, "
        "written before any result was read: excess CAGR above 0 against SPY, OR a CAGR within 2 points of "
        "SPY's with a correlation of monthly returns below 0.3 against both momentum_baseline and "
        "quality_momentum over the same window. India is left for a later version: its stored balance sheets "
        "and cash flows start in 2022, so inside the optimise window no Indian stock carries three of the four "
        "ratios."
    ),
    "thesis": "Cheap stocks -- low price against earnings, book value, sales or cash flow -- have earned more "
              "than expensive ones over long histories and across markets (Fama and French; Lakonishok, "
              "Shleifer and Vishny), and value has tended to do well in the years momentum does badly (Asness, "
              "Moskowitz and Pedersen, 'Value and Momentum Everywhere'). Nearly every strategy here is a trend "
              "or momentum bet, so their bad years come together; a value book is judged partly on whether it "
              "earns its keep with returns that do not move with them. A composite of four ratios is steadier "
              "than any one, and the two guards test the standard objections: cheap because the business is "
              "poor (the value trap), and cheap because it is still falling.",
    "how_it_works": (
        "The momentum baseline's universe and loop -- same price and turnover floors, the {liquidity_top} most "
        "liquid names, {cost_bps}bps a side -- with the 200-day trend test off and the ranking replaced: at each "
        "quarter-end the pool is ranked on value and the top {top_n} are held, equal weight.",
        "Four ratios, each from the filings public that day: earnings yield (the last four quarters' net income "
        "over market value), book-to-price (latest equity over market value), sales-to-price (the last four "
        "quarters' revenue over market value) and free-cash-flow yield (the latest fiscal year's operating cash "
        "flow less capex, over market value). Each is turned into a percentile across the pool, higher meaning "
        "cheaper, and the percentiles are averaged.",
        "A company needs at least {VR_MIN_RATIOS} of the ratios that apply to it. Banks and insurers skip "
        "sales-to-price and free-cash-flow yield, utilities free-cash-flow yield. The sector-neutral switch "
        "instead applies all four to everyone and ranks within each sector.",
        "Two guards, each a variant: quality drops the bottom {VR_QUALITY_DROP_PCT}% of the valued names by "
        "gross profitability and ROE; momentum drops the bottom {VR_MOMENTUM_DROP_PCT}% of the pool by 12-1 "
        "momentum. The default (base) uses neither; both uses both.",
        "Each rebalance records how many ranked names could be valued and how many passed, in the run's "
        "report and value_coverage.csv.",
    ),
    "entry_rules": (
        "Universe: the momentum baseline's -- price floor, the market's 20-day turnover floor, the {liquidity_top} "
        "most liquid names, ETFs and funds excluded, at least {lookback} + {skip} sessions of history (the "
        "momentum guard needs them). No 200-day trend test.",
        "Public by then. A quarter counts from its filing date, or {FILING_LAG_DAYS} days after it ended when the "
        "source recorded none; a fiscal year's or balance sheet's lines {LINES_FILING_LAG_DAYS} days after the "
        "period ended. A company whose latest quarter is over {STALE_RESULTS_DAYS} days old, or whose latest "
        "fiscal year or balance sheet is over {VR_STATEMENT_STALE_DAYS} days old, has no data for it.",
        "Market value: the latest quarter's share count times the rebalance close, times every split after the "
        "day that count was reported (stored prices are adjusted for later splits, filings are not). A company "
        "whose statements are in another currency than its price is not valued.",
        "Earnings yield, book-to-price, sales-to-price, free-cash-flow yield: as in How it works; a sum of "
        "quarters needs four consecutive ones. Negative earnings, book or free cash flow give a negative ratio, "
        "which ranks at the expensive end.",
        "Value score: the average percentile of the applicable ratios; at least {VR_MIN_RATIOS} needed, or all of "
        "them when fewer apply (a bank's two, a utility's three).",
        "Quality guard (variants quality and both): quality is the average percentile of gross profitability "
        "(last four quarters' gross profit over total assets) and ROE (net income of the last four quarters over "
        "average equity), whichever are stored; the bottom {VR_QUALITY_DROP_PCT}% of the valued names are "
        "dropped, and so is a company with neither reading.",
        "Momentum guard (variants momentum and both): the bottom {VR_MOMENTUM_DROP_PCT}% of the pool by return "
        "over {lookback} sessions ending {skip} ago are dropped before valuing.",
        "Selection: the top {top_n} value scores, equal weight; traded at the next session's open after the "
        "quarter-end close, {cost_bps}bps a side. With fewer than {top_n} eligible it holds those.",
    ),
    "exit_rules": (
        "Sold at the next open after a quarter-end, less {cost_bps}bps, when no longer in the top {top_n} -- "
        "including when its value score cannot be computed on that date's filings.",
        "Nothing sells between quarter-ends; there is no stop and no target.",
    ),
    "caveats": (
        "**Survivorship bias.** The price universe is today's listed names, so companies delisted during the "
        "window are absent. For a value book this matters more than for momentum: the cheapest names include "
        "the ones that went on to fail, and those are missing, so returns are biased upward.",
        "**Data coverage.** US quarterly figures reach back to 2009-2011 (XBRL phase-in), but gross profit is "
        "stored for under half of the quarters (many companies file no gross-profit line) and the share count "
        "for about 95%; a company without a share count cannot be valued. The coverage CSV counts each "
        "rebalance's valued names. Companies the filings source was never asked about are counted as never "
        "fetched (the financials_backfill job fetches every stock liquid at some month-end since 2013).",
        "**India is not measured in v1.0.** Its quarterly results before 2022 carry almost no equity, and its "
        "balance sheets and cash flows start with fiscal 2022, so within the optimise window (to 2021) no Indian "
        "company has three of the four ratios; the only window with the data is the verify window, which "
        "cannot be tuned in.",
        "**US annual and balance-sheet lines are the latest filed values**, so a restatement is visible earlier "
        "than it was; quarterly figures are as first reported.",
        "**Sector is today's.** Banks, insurers and utilities are recognised from the current company profile.",
        "**Weighted shares, not shares outstanding.** The quarter's diluted weighted share count stands in for "
        "the shares outstanding on the rebalance date; buybacks or issues since then are not seen.",
        "**Ordinary dividends are excluded** on both the strategy and the benchmark, which understates a value "
        "book (higher yield) more than the index.",
    ),
}


class ValueRankingStrategy(PortfolioStrategy):
    """The cheapest liquid stocks on a point-in-time value composite, rebalanced quarterly."""

    key = DOC["key"]
    doc = DOC
    family = "value_ranking"
    version = "1.1"
    changelog = (
        ("1.1", "2026-11-14",
         "The loop it shares with momentum_baseline (1.5): The turnover floor values every session of its 20-day window on today's price basis (corporate_actions.traded_value), from the momentum_baseline India review of 2026-11-14. A credited special dividend or demerger drops the price but not the shares traded before it, so the plain mean of close x volume kept the pre-ex sessions at the pre-ex price for 20 sessions. AURUM (ex-Majesco) went ex a 98.8% special dividend on 2020-12-23 (Rs 717 -> 8.88); on 2020-12-31 the floor read Rs 121 cr a day while the stock traded Rs 8 lakh, in a locked upper circuit. Pre-ex sessions are now scaled by the same ratio as the price, and only for actions up to the session (point in time), as a split already is: AURUM reads Rs 1.4 cr there. A session whose window spans no credited ex-date is unchanged to the bit. In memory on the optimise stage: India unchanged (9.38%, 107 trades); US unchanged too (9.42%, 279 trades). Bumped because the floor's reading changed for every stock in the 20 sessions after a credited action. Bumped by hand: no numeric constant moved."),
        ("1.0", "2026-11-14",
         "First version: top 20 by the average percentile of earnings yield, book-to-price, sales-to-price "
         "and free-cash-flow yield (at least 3 of the applicable ones), from filings public on "
         "the rebalance date; quarter-end rebalance, next-open fills, the baseline's universe and costs, no "
         "200-day trend test. Guards (quality, momentum) and the sector-neutral switch are variants, all fixed "
         "before any run."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"]) + (corporate_actions.CAVEAT_HELD,)
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "quality_value"
    selection = "fundamental"
    style = "value"
    horizon = "positional"
    runner = "value_ranking"

    # the pool is the baseline's; only these differ from it
    top_n = VR_TOP_N
    rebalance = "QE"
    trend_filter = False          # read by baseline.strategy_defaults and the live selection
    lookback = MomentumBaselineStrategy.lookback   # the momentum guard's 12-1, and the history the pool needs
    skip = MomentumBaselineStrategy.skip
    cost_bps = MomentumBaselineStrategy.cost_bps
    liquidity_top = MomentumBaselineStrategy.liquidity_top
    fill = "next_open"

    @classmethod
    def live_filter(cls, market: str) -> "ValueFilter":
        """The filter baseline.current_selection applies to the live ranking: the backtest's own, at its
        default variant, on the filings public on the latest bar."""
        return ValueFilter(market)

    param_docs = (
        ("Holdings", "top_n", "Names held, equal weight."),
        ("Rebalance", "rebalance", "Pandas offset alias; QE is quarter-end (ME, monthly, is a variant)."),
        ("Momentum lookback", "lookback", "Bars of return for the momentum guard's 12-1 (and the history the pool needs)."),
        ("Skip", "skip", "Most recent bars left out of the momentum guard's return."),
        ("Cost per side", "cost_bps", "Basis points per side (the baseline's)."),
        ("Liquidity cutoff", "liquidity_top", "Only the N most liquid names are ranked (the baseline's)."),
        ("Ratios needed", "VR_MIN_RATIOS", "Of the four value ratios, at least this many (capped at those that apply)."),
        ("Quality guard", "VR_QUALITY_DROP_PCT", "Bottom share of valued names dropped by quality, %."),
        ("Momentum guard", "VR_MOMENTUM_DROP_PCT", "Bottom share of the pool dropped by 12-1 momentum, %."),
        ("Statement freshness", "VR_STATEMENT_STALE_DAYS", "A fiscal year or balance sheet older than this is no data."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    """baseline.main with the value filter, plus `--variant` and `--sector-neutral`; writes value_coverage.csv."""
    from pathlib import Path
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--variant", default=DEFAULT_VARIANT, choices=VARIANTS)
    pre.add_argument("--sector-neutral", action="store_true")
    pre.add_argument("--market")   # required by baseline.main's parser, which windows.runner_defaults reads
    known, rest = pre.parse_known_args(argv)
    if known.market:
        rest = ["--market", known.market, *rest]
    if "--strategy" not in rest:
        rest = ["--strategy", ValueRankingStrategy.key, *rest]
    filt = ValueFilter(known.market, known.variant, known.sector_neutral) if known.market else None
    suffix = ("" if known.variant == DEFAULT_VARIANT else f"_{known.variant}") + ("_sector" if known.sector_neutral else "")
    extra = (() if known.variant == DEFAULT_VARIANT else (f"--variant {known.variant}",)) + \
            (("--sector-neutral",) if known.sector_neutral else ())
    r = baseline.main(rest, universe_filter=filt, run_suffix=suffix, reproduce_extra=extra)
    if r:
        filt.coverage().to_csv(Path(r["run_dir"]) / "value_coverage.csv", index=False)
    return r


if __name__ == "__main__":
    main()
