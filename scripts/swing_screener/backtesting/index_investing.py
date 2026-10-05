"""Index-investing backtests — Families A-D, one command.

    python3 -m swing_screener.marketdata.index_data --refresh     # once
    python3 -m swing_screener.backtesting.index_investing --market us
    python3 -m swing_screener.backtesting.index_investing --market india --family A

Each family loads its OWN window, because `align()` intersects calendars
and one late-starting sleeve would otherwise truncate everything: pulling
GLD (2004) into the trend-overlay test would throw away 24 years of the
S&P's history to answer a question that never needed gold. The window for
every table is printed with it.

The suite deliberately reports after-tax figures beside pre-tax ones. In
India a monthly-rebalanced book pays 20% STCG on every realised gain while
a buy-and-hold book pays nothing until it sells, so a pre-tax-only
comparison of rebalancing cadences is not a conservative estimate — it is
the wrong ranking.
"""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core.charts import (
    GRID, INK, INK_2, MUTED, NEG, POS, SERIES_BENCHMARK, SERIES_STRATEGY,
    _save, _style,
)
from ..paths import run_dir
from . import index_accumulate as acc
from . import index_allocate as alloc
from . import index_stats as stats
from .index_core import TaxModel, load_context

logger = logging.getLogger("index_investing")


@dataclass
class _Decomposition:
    """How much of the day-of-month ordering is simply time in the market."""

    corr: float
    observed_spread: float
    residual_spread: float
    null_spread: float

    def details(self) -> list[str]:
        return [
            f"correlation with the time-in-market prediction: **{self.corr:.3f}** "
            f"(r² = {self.corr ** 2:.2f})",
            f"spread before removing it **{self.observed_spread:.4f}**, after "
            f"**{self.residual_spread:.4f}**, randomised-day null "
            f"**{self.null_spread:.4f}**",
        ]

    def verdict(self) -> str:
        """Reading of whether the day ordering is mechanical, noise, or real.

        A NEGATIVE correlation is not a weaker version of a positive one: it
        means the observed ordering runs against the only mechanism known to
        produce one, so the ranking is noise large enough to swamp that
        mechanism — a different conclusion from "mostly explained", and the
        one the 29-year Sensex window actually gives.
        """
        inside = self.residual_spread <= self.null_spread
        null_clause = (
            f"inside the randomised-day null ({self.null_spread:.4f})" if inside
            else f"still above the randomised-day null ({self.null_spread:.4f})"
        )
        if self.corr <= 0:
            return (
                f"NOISE DOMINATES — the day ordering runs AGAINST the time-in-market "
                f"prediction (r = {self.corr:.3f}). Contributing earlier in the month "
                f"does buy more market exposure, but here the noise ({self.observed_spread:.4f} "
                f"spread) is several times that mechanical effect, so the ranking is "
                f"not measuring either one. Residual spread {self.residual_spread:.4f}, "
                f"{null_clause}."
            )
        share = self.corr ** 2 * 100
        verb = "shrinks" if self.residual_spread < self.observed_spread else "leaves"
        return (
            f"{share:.0f}% of the variation across contribution days is explained by "
            f"being invested longer (r = {self.corr:.3f}) rather than by any calendar "
            f"effect. Removing it {verb} the best-to-worst spread "
            f"{'from' if verb == 'shrinks' else 'at'} {self.observed_spread:.4f} "
            f"{'to ' if verb == 'shrinks' else ''}{self.residual_spread:.4f}, "
            f"{null_clause}."
        )

# Index funds and ETFs, not single stocks: the cost is the bid-ask spread
# plus (in India) brokerage, NOT the 25bps/side the stock strategies pay.
# Expense ratios are already inside the series.
DEFAULT_COST_BPS = {"us": 2.0, "india": 10.0}

# Contribution size for Family A. Arbitrary and irrelevant to the ranking —
# every variant contributes the same, and the metrics are per-unit.
ANNUAL_CONTRIB = {"us": 12_000.0, "india": 600_000.0}
LUMP = {"us": 100_000.0, "india": 2_000_000.0}

EQUITY = {"us": "SP500_TR", "india": "NIFTY50_TR"}
LONG_EQUITY = {"us": "SP500_PRICE_LONG", "india": "SENSEX"}


def _tax(market: str, enabled: bool) -> TaxModel:
    if not enabled:
        return TaxModel.none()
    return TaxModel.india() if market == "india" else TaxModel.us()


def alloc_row(
    ctx, label: str, builder, initial: float, cost_bps: float,
    market: str, taxed: bool, **kw,
) -> tuple[dict, pd.Series]:
    """One allocation strategy, run twice: pre-tax and after-tax.

    Two runs rather than one because a taxed run pays its bill out of the
    book as it goes, so that run's equity curve IS the after-tax curve — its
    CAGR cannot also serve as the pre-tax number. Reporting both honestly
    means simulating both.
    """
    # `band` is the simulator's threshold-rebalancing tolerance, not a
    # builder argument — pull it out before the builder sees it
    band = kw.pop("band", 0.0)
    targets, cadence = builder(ctx, **kw)
    res = alloc.simulate(ctx, targets, initial, cost_bps, TaxModel.none(),
                         cadence, band=band, name=label)
    row = stats.summarize_allocation(label, res).row()
    if taxed:
        res_t = alloc.simulate(ctx, targets, initial, cost_bps, _tax(market, True),
                               cadence, band=band, name=label)
        s_t = stats.summarize_allocation(label, res_t)
        row["after_tax_cagr"] = round(s_t.after_tax_cagr_pct, 2)
        row["tax_drag_pp"] = round(row["cagr_pct"] - s_t.after_tax_cagr_pct, 2)
        row["tax_paid"] = round(s_t.tax_paid + s_t.terminal_tax, 0)
    return row, res.equity


def acc_row(
    ctx, asset: str, label: str, sched: pd.Series, cost_bps: float,
    market: str, taxed: bool, **kw,
) -> tuple[dict, float]:
    """One accumulation variant, pre-tax and after-tax. Returns (row, multiple)."""
    res = acc.simulate(ctx, asset, sched, cost_bps, TaxModel.none(), **kw)
    s = stats.summarize_accumulation(label, res)
    row = s.row()
    if taxed:
        res_t = acc.simulate(ctx, asset, sched, cost_bps, _tax(market, True), **kw)
        s_t = stats.summarize_accumulation(label, res_t)
        row["after_tax_xirr"] = round(s_t.after_tax_xirr_pct, 3)
        row["tax_paid"] = round(s_t.tax_paid + s_t.terminal_tax, 0)
    return row, s.multiple


# ---------------------------------------------------------------- Family A


def family_a(market: str, cost_bps: float, taxed: bool, quick: bool) -> dict:
    """Accumulation timing: day-of-month, day-of-week, frequency, deployment."""
    amount = ANNUAL_CONTRIB[market]
    tables: dict[str, pd.DataFrame] = {}
    extra: dict[str, object] = {}

    windows = [("clean TR", EQUITY[market], None)]
    if market == "india":
        # Both India windows, per the design decision: 17y of clean total
        # return, and 29y of price index carrying a calibrated dividend.
        windows.append(("long (calibrated dividend)", "SENSEX", None))

    for wlabel, asset, start in windows:
        ctx = load_context(market, [asset], start=start)
        tag = f"{asset} [{wlabel}] {ctx.index[0].date()}..{ctx.index[-1].date()}"
        logger.info("Family A — %s", tag)

        # --- A1: day of month ---
        rows, observed = [], {}
        for day in [*range(1, 29), "first", "last"]:
            sched, label = acc.schedule(ctx.index, "dom", amount, day=day)
            row, mult = acc_row(ctx, asset, label, sched, cost_bps, market, taxed,
                                deploy="immediate")
            rows.append({"day": str(day), **row})
            observed[str(day)] = mult
        tables[f"A1 day-of-month — {tag}"] = pd.DataFrame(rows).sort_values(
            "multiple", ascending=False
        )

        # The null: the same schedule with a RANDOM day each month. Without
        # this the table above is 30 draws with the maximum reported.
        # Pre-tax on both sides: the tax bill does not depend on which day of
        # the month the money went in, so taxing the null would add noise
        # without changing what is being tested.
        draws = acc.random_day_draws(
            ctx, asset, amount, cost_bps, TaxModel.none(),
            draws=40 if quick else 200,
        )
        band = stats.placebo_band(observed, draws, n_variants=len(observed))
        extra[f"A1 placebo — {tag}"] = band

        # --- A1b: is the day-of-month ordering just time in the market? ---
        # Contributing on the 1st rather than the 28th invests each
        # instalment ~27 days earlier. At the Nifty's own drift that is worth
        # roughly 0.8% per instalment, which is the same size as the whole
        # observed day-of-month spread. So before calling it a calendar
        # anomaly, the spread has to be compared against what being invested
        # longer explains on its own.
        drift = float(ctx.prices[asset].pct_change().mean())
        dec_rows = []
        last_day = ctx.index[-1]
        for day in range(1, 29):
            sched, _ = acc.schedule(ctx.index, "dom", amount, day=day)
            avg_days = float(np.mean([(last_day - d).days for d in sched.index]))
            dec_rows.append({"day": day, "multiple": observed[str(day)],
                             "avg_days_invested": round(avg_days, 1)})
        dec = pd.DataFrame(dec_rows)
        base = dec[dec.day == 28].iloc[0]
        dec["extra_days"] = (dec.avg_days_invested - base.avg_days_invested).round(1)
        dec["observed_gain"] = (dec.multiple - base.multiple).round(4)
        dec["predicted_gain"] = (
            base.multiple * (1 + drift) ** (dec.extra_days * 252 / 365) - base.multiple
        ).round(4)
        dec["residual"] = (dec.observed_gain - dec.predicted_gain).round(4)
        corr = float(dec.observed_gain.corr(dec.predicted_gain))
        dec["multiple"] = dec["multiple"].round(4)
        tables[f"A1b time-in-market decomposition — {tag}"] = dec
        extra[f"A1b note — {tag}"] = _Decomposition(
            corr=corr,
            observed_spread=float(dec.multiple.max() - dec.multiple.min()),
            residual_spread=float(dec.residual.max() - dec.residual.min()),
            null_spread=band.spread_p95_null,
        )

        # --- A2: turn-of-month, grouped for power ---
        # 30 one-day tests have almost no power; two grouped windows do.
        tom_rows = []
        for glabel, days in (
            ("turn of month (last, 1, 2, 3)", ["last", 1, 2, 3]),
            ("mid-month (13-16)", [13, 14, 15, 16]),
            ("late month (22-25)", [22, 23, 24, 25]),
        ):
            mults = [observed[str(d)] for d in days if str(d) in observed]
            tom_rows.append({
                "window": glabel, "n_days": len(mults),
                "mean_multiple": round(sum(mults) / len(mults), 4),
                "best": round(max(mults), 4), "worst": round(min(mults), 4),
            })
        tables[f"A2 turn-of-month grouped — {tag}"] = pd.DataFrame(tom_rows)

        # --- A3: day of week (weekly contributions) ---
        rows = []
        for wd in range(5):
            sched, label = acc.schedule(ctx.index, "dow", amount, weekday=wd)
            row, _ = acc_row(ctx, asset, label, sched, cost_bps, market, taxed,
                             deploy="immediate")
            rows.append(row)
        tables[f"A3 day-of-week — {tag}"] = pd.DataFrame(rows).sort_values(
            "multiple", ascending=False
        )

        # --- A4: contribution frequency, same annual amount ---
        rows = []
        for freq in ("D", "W-FRI", "SME", "ME", "QE", "YE"):
            sched, label = acc.schedule(ctx.index, "freq", amount, freq=freq)
            row, _ = acc_row(ctx, asset, label, sched, cost_bps, market, taxed,
                             deploy="immediate")
            rows.append(row)
        tables[f"A4 frequency — {tag}"] = pd.DataFrame(rows)

        # --- A6/A7/A9/A8/A10: deployment rules, all on day 1 ---
        base_sched, _ = acc.schedule(ctx.index, "dom", amount, day=1)
        rows = []
        variants = [
            ("immediate (baseline)", dict(deploy="immediate")),
            ("dip: deploy at -5% from peak", dict(deploy="dip", dip_threshold=0.05)),
            ("dip: deploy at -10%", dict(deploy="dip", dip_threshold=0.10)),
            ("dip: deploy at -15%", dict(deploy="dip", dip_threshold=0.15)),
            ("dip: deploy at -20%", dict(deploy="dip", dip_threshold=0.20)),
            ("invest only above 200DMA", dict(deploy="trend_on", ma_window=200)),
            ("0.5x above / 2x below 200DMA", dict(deploy="trend_double", ma_window=200)),
            ("value averaging (10% path)", dict(deploy="value_avg", growth=0.10)),
            ("PERFECT hindsight monthly low", dict(deploy="hindsight")),
        ]
        for label, kw in variants:
            row, _ = acc_row(ctx, asset, label, base_sched, cost_bps, market, taxed, **kw)
            rows.append({"rule": label, **row})
        # A10 control: saving more, timing unchanged
        for step in (0.05, 0.10):
            sched, label = acc.schedule(ctx.index, "step_up", amount, day=1, step=step)
            row, _ = acc_row(ctx, asset, label, sched, cost_bps, market, taxed,
                             deploy="immediate")
            rows.append({"rule": label, **row})
        tables[f"A6-A10 deployment rules — {tag}"] = pd.DataFrame(rows)

        # --- A5: lump sum vs DCA over N months, every start month ---
        # A FIXED horizon per start date. Running each start through to today
        # instead would mix a 46-year hold with a 5-year one and the win rate
        # would mean nothing in particular.
        horizon = 10
        rows = []
        for n in (3, 6, 12, 24):
            wins, diffs = 0, []
            starts = pd.date_range(
                ctx.index[0], ctx.index[-1] - pd.DateOffset(years=horizon),
                freq="YS" if quick else "QS",
            )
            for st in starts:
                sub = ctx.slice(start=st, end=st + pd.DateOffset(years=horizon))
                if len(sub.index) < 252 * (horizon - 1):
                    continue
                lump_sched, _ = acc.schedule(sub.index, "lump", 0.0, amount=LUMP[market])
                # pre-tax: neither arm realises a gain before the end, so tax
                # would scale both identically and cancel in the ratio
                r_lump = acc.simulate(sub, asset, lump_sched, cost_bps,
                                      TaxModel.none(), "immediate")
                r_dca = acc.simulate(sub, asset, lump_sched, cost_bps,
                                     TaxModel.none(), "spread", spread_months=n)
                a = float(r_lump.equity.iloc[-1]); b = float(r_dca.equity.iloc[-1])
                diffs.append((a / b - 1) * 100)
                wins += a > b
            if diffs:
                rows.append({
                    "dca_months": n, "start_dates": len(diffs),
                    "lump_sum_win_rate_pct": round(100 * wins / len(diffs), 1),
                    "median_lump_advantage_pct": round(float(pd.Series(diffs).median()), 2),
                    "worst_lump_outcome_pct": round(float(min(diffs)), 2),
                    "best_lump_outcome_pct": round(float(max(diffs)), 2),
                })
        tables[f"A5 lump sum vs DCA ({horizon}y holds) — {tag}"] = pd.DataFrame(rows)

    return {"tables": tables, "extra": extra}


# ---------------------------------------------------------------- Family B


def family_b(market: str, cost_bps: float, taxed: bool, quick: bool) -> dict:
    """Lump-sum timing overlays."""
    initial = LUMP[market]
    tables, curves = {}, {}

    eq = EQUITY[market]
    ctx = load_context(market, [eq])
    tag = f"{eq} {ctx.index[0].date()}..{ctx.index[-1].date()}"
    rows = []

    def add(label, builder, ctx_=None, **kw):
        row, eqc = alloc_row(ctx_ or ctx, label, builder, initial, cost_bps,
                             market, taxed, **kw)
        rows.append(row)
        curves[label] = eqc

    add("buy & hold", alloc.buy_hold, asset=eq)
    for months in (6, 8, 10, 12):
        add(f"{months}-month SMA -> cash", alloc.trend_overlay,
            asset=eq, kind="sma10", months=months)
    add("200-DMA daily -> cash", alloc.trend_overlay, asset=eq, kind="dma", window=200)
    add("50/200 golden cross", alloc.trend_overlay, asset=eq, kind="golden")
    add("12-month absolute momentum", alloc.trend_overlay, asset=eq,
        kind="absmom", lookback=252)
    add("dual momentum vs cash", alloc.trend_overlay, asset=eq, kind="dualmom")
    for target in (0.10, 0.12, 0.15):
        add(f"vol target {target * 100:.0f}%", alloc.vol_targeted, asset=eq, target=target)
    nov_apr = (11, 12, 1, 2, 3, 4)
    add("Nov-Apr only (sell in May)", alloc.seasonal_only, asset=eq, months=nov_apr)
    for th in (0.10, 0.20, 0.30):
        add(f"wait for -{th * 100:.0f}% then buy", alloc.dip_entry, asset=eq, threshold=th)

    tables[f"B overlays — {tag}"] = pd.DataFrame(rows)

    # --- the "-> bonds" variant needs a bond sleeve, hence a later window ---
    bond_key = "BONDS" if market == "us" else "CASH_FUND"
    ctx_b = load_context(market, [eq, bond_key])
    tag_b = f"{eq}+{bond_key} {ctx_b.index[0].date()}..{ctx_b.index[-1].date()}"
    rows_b = []
    for label, builder, kw in (
        ("buy & hold", alloc.buy_hold, dict(asset=eq)),
        ("10-month SMA -> cash", alloc.trend_overlay, dict(asset=eq, kind="sma10")),
        (f"10-month SMA -> {bond_key}", alloc.trend_overlay,
         dict(asset=eq, kind="sma10", safe=bond_key)),
    ):
        row, _ = alloc_row(ctx_b, label, builder, initial, cost_bps, market, taxed, **kw)
        rows_b.append(row)
    tables[f"B2 safe-asset choice — {tag_b}"] = pd.DataFrame(rows_b)

    # --- the long price-only window: does any of this survive a century? ---
    long_key = LONG_EQUITY[market]
    ctx_l = load_context(market, [long_key])
    tag_l = f"{long_key} {ctx_l.index[0].date()}..{ctx_l.index[-1].date()}"
    rows_l = []
    for label, kw in (
        ("buy & hold", dict(builder=alloc.buy_hold, asset=long_key)),
        ("10-month SMA -> cash", dict(builder=alloc.trend_overlay, asset=long_key,
                                      kind="sma10")),
        ("200-DMA daily -> cash", dict(builder=alloc.trend_overlay, asset=long_key,
                                       kind="dma", window=200)),
        ("Nov-Apr only", dict(builder=alloc.seasonal_only, asset=long_key,
                              months=nov_apr)),
        # The dip-entry variants belong here specifically: on the 1980 window
        # "wait for -20%" beats buy & hold, but it spends 1980-82 in T-bills
        # yielding 14-16%, which is a property of that start date rather than
        # of the rule. A century-long window is where that claim gets tested.
        ("wait for -10% then buy", dict(builder=alloc.dip_entry, asset=long_key,
                                        threshold=0.10)),
        ("wait for -20% then buy", dict(builder=alloc.dip_entry, asset=long_key,
                                        threshold=0.20)),
        ("wait for -30% then buy", dict(builder=alloc.dip_entry, asset=long_key,
                                        threshold=0.30)),
    ):
        builder = kw.pop("builder")
        row, _ = alloc_row(ctx_l, label, builder, initial, cost_bps, market, taxed, **kw)
        rows_l.append(row)
    tables[f"B long window — {tag_l}"] = pd.DataFrame(rows_l)

    # --- sub-period split: trend following is insurance, so show the premium
    # and the payout separately rather than averaging them into one CAGR ---
    sub_rows = []
    decades = _decades(ctx_l.index)
    for lo, hi in decades:
        c = ctx_l.slice(start=lo, end=hi)
        if len(c.index) < 400:
            continue
        bh_t, _ = alloc.buy_hold(c, long_key)
        tr_t, _ = alloc.trend_overlay(c, asset=long_key, kind="sma10")
        bh = stats.summarize_allocation("bh", alloc.simulate(
            c, bh_t, initial, cost_bps, TaxModel.none(), "never"))
        tr = stats.summarize_allocation("tr", alloc.simulate(
            c, tr_t, initial, cost_bps, TaxModel.none(), "never"))
        sub_rows.append({
            "period": f"{lo.date()}..{hi.date()}",
            "buyhold_cagr": round(bh.cagr_pct, 2), "buyhold_dd": round(bh.max_dd_pct, 1),
            "timed_cagr": round(tr.cagr_pct, 2), "timed_dd": round(tr.max_dd_pct, 1),
            "timed_minus_bh": round(tr.cagr_pct - bh.cagr_pct, 2),
        })
    tables[f"B sub-periods (10-month rule, pre-tax) — {long_key}"] = pd.DataFrame(sub_rows)

    return {"tables": tables, "curves": curves}


def _decades(index: pd.DatetimeIndex) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    out = []
    start = pd.Timestamp(year=(index[0].year // 10) * 10, month=1, day=1)
    while start < index[-1]:
        end = start + pd.DateOffset(years=10) - pd.Timedelta(days=1)
        out.append((max(start, index[0]), min(end, index[-1])))
        start += pd.DateOffset(years=10)
    return out


# ---------------------------------------------------------------- Family C


def family_c(market: str, cost_bps: float, taxed: bool, quick: bool) -> dict:
    """Static allocation and rebalancing cadence."""
    initial = LUMP[market]
    tables, curves = {}, {}

    eq = EQUITY[market]
    bond = "BONDS" if market == "us" else "CASH_FUND"
    gold = "GOLD"
    ctx = load_context(market, [eq, bond, gold])
    tag = f"{eq}/{bond}/{gold} {ctx.index[0].date()}..{ctx.index[-1].date()}"

    rows = []

    def add(label, weights, cadence, band=0.0):
        row, eqc = alloc_row(ctx, label, alloc.static_mix, initial, cost_bps,
                             market, taxed, weights=weights, rebalance=cadence,
                             band=band)
        rows.append(row)
        curves[label] = eqc

    add("100% equity", {eq: 1.0}, "never")
    for w in (0.8, 0.6, 0.5):
        add(f"{w * 100:.0f}/{100 - w * 100:.0f} equity/bond (annual)",
            {eq: w, bond: 1 - w}, "YE")
    add("70/30 equity/gold (annual)", {eq: 0.7, gold: 0.3}, "YE")
    add("60/40 equity/gold (annual)", {eq: 0.6, gold: 0.4}, "YE")
    add("50/30/20 equity/bond/gold (annual)", {eq: 0.5, bond: 0.3, gold: 0.2}, "YE")
    tables[f"C1-C2 static mixes — {tag}"] = pd.DataFrame(rows)

    # --- C3: cadence on ONE mix, so cadence is the only thing varying ---
    rows = []
    mix = {eq: 0.6, bond: 0.2, gold: 0.2}
    for label, cadence, band in (
        ("never rebalanced (drift)", "never", 0.0),
        ("monthly", "ME", 0.0),
        ("quarterly", "QE", 0.0),
        ("annual", "YE", 0.0),
        ("annual, 5% band", "YE", 0.05),
        ("monthly, 5% band", "ME", 0.05),
    ):
        row, _ = alloc_row(ctx, label, alloc.static_mix, initial, cost_bps, market,
                           taxed, weights=mix, rebalance=cadence, band=band)
        rows.append({"cadence": label, **row})
    tables[f"C3 rebalancing cadence (60/20/20) — {tag}"] = pd.DataFrame(rows)

    # --- C5: multi-index equal weight vs the single cap-weighted index ---
    sleeves = (["SP500_TR", "NASDAQ100", "RUSSELL2000"] if market == "us"
               else ["NIFTY50_TR", "NEXT50", "MIDCAP"])
    ctx5 = load_context(market, sleeves)
    rows = []
    for label, weights in (
        (f"{sleeves[0]} alone", {sleeves[0]: 1.0}),
        ("equal weight, annual rebalance", {s: 1 / len(sleeves) for s in sleeves}),
    ):
        row, _ = alloc_row(ctx5, label, alloc.static_mix, initial, cost_bps, market,
                           taxed, weights=weights, rebalance="YE")
        rows.append(row)
    tables[f"C5 index breadth — {'/'.join(sleeves)} "
           f"{ctx5.index[0].date()}..{ctx5.index[-1].date()}"] = pd.DataFrame(rows)

    # --- C4: the cross-market split (India only: real INR-denominated US ETF) ---
    if market == "india":
        ctx4 = load_context("india", ["NIFTY50_TR", "US_IN_INR"])
        rows = []
        for w in (1.0, 0.7, 0.5, 0.0):
            label = f"{w * 100:.0f}% India / {100 - w * 100:.0f}% US (INR)"
            row, _ = alloc_row(ctx4, label, alloc.static_mix, initial, cost_bps,
                               market, taxed,
                               weights={"NIFTY50_TR": w, "US_IN_INR": 1 - w},
                               rebalance="YE")
            rows.append(row)
        tables[f"C4 India/US split — MON100 in INR "
               f"{ctx4.index[0].date()}..{ctx4.index[-1].date()}"] = pd.DataFrame(rows)

    return {"tables": tables, "curves": curves}


# ---------------------------------------------------------------- Family D


def family_d(market: str, cost_bps: float, taxed: bool, quick: bool) -> dict:
    """Rotation across index sleeves."""
    initial = LUMP[market]
    tables, curves = {}, {}

    if market == "us":
        sleeves = ["SP500_TR", "NASDAQ100", "RUSSELL2000", "GOLD", "BONDS"]
        gem = ["SP500_TR", "INTL", "BONDS"]
    else:
        sleeves = ["NIFTY50_TR", "NEXT50", "MIDCAP", "GOLD", "CASH_FUND"]
        gem = ["NIFTY50_TR", "US_IN_INR", "CASH_FUND"]

    ctx = load_context(market, sleeves)
    tag = f"{len(sleeves)} sleeves {ctx.index[0].date()}..{ctx.index[-1].date()}"
    rows = []

    def add(label, builder, ctx_, **kw):
        row, eqc = alloc_row(ctx_, label, builder, initial, cost_bps, market,
                             taxed, **kw)
        rows.append(row)
        curves[label] = eqc

    add("equity buy & hold", alloc.buy_hold, ctx, asset=sleeves[0])
    for n in (1, 2, 3):
        add(f"top {n} of {len(sleeves)}, 12mo, abs. gate", alloc.rotation, ctx,
            sleeves=sleeves, lookback=252, top_n=n, absolute=True)
    add(f"top 1 of {len(sleeves)}, 6mo, abs. gate", alloc.rotation, ctx,
        sleeves=sleeves, lookback=126, top_n=1, absolute=True)
    add(f"top 1 of {len(sleeves)}, 12mo, NO abs. gate", alloc.rotation, ctx,
        sleeves=sleeves, lookback=252, top_n=1, absolute=False)
    add("inverse-vol all sleeves (quarterly)", alloc.inverse_vol_mix, ctx,
        sleeves=sleeves)
    tables[f"D rotation — {tag}"] = pd.DataFrame(rows)

    ctx_g = load_context(market, gem)
    rows_g = []
    for label, builder, kw in (
        ("equity buy & hold", alloc.buy_hold, dict(asset=gem[0])),
        ("GEM: top 1 of 3, 12mo + abs. gate", alloc.rotation,
         dict(sleeves=gem, lookback=252, top_n=1, absolute=True)),
        ("equal weight 3 sleeves (annual)", alloc.static_mix,
         dict(weights={s: 1 / 3 for s in gem}, rebalance="YE")),
    ):
        row, _ = alloc_row(ctx_g, label, builder, initial, cost_bps, market, taxed, **kw)
        rows_g.append(row)
    tables[f"D1 dual momentum (GEM) — {'/'.join(gem)} "
           f"{ctx_g.index[0].date()}..{ctx_g.index[-1].date()}"] = pd.DataFrame(rows_g)

    return {"tables": tables, "curves": curves}


# ---------------------------------------------------------------- output


# Six hues that stay distinguishable under deuteranopia and protanopia. The
# repo's two-colour strategy/benchmark pair only works for two series; a
# six-line chart drawn from it repeats blue and red, which is how two
# different strategies end up looking like the same one.
CATEGORICAL = [
    SERIES_STRATEGY,   # blue
    SERIES_BENCHMARK,  # orange
    "#1b9e77",         # teal
    "#7b5ea7",         # purple
    "#a6761d",         # ochre
    "#4c9f70",         # sage
]


def chart_curves(curves: dict[str, pd.Series], out: Path, currency: str,
                 title: str, top: int = 6) -> Path:
    """Equity curves on a log axis.

    Log, because over 46 years a linear axis compresses the first two
    decades into a flat line and the eye reads "nothing happened until
    2000". On a log axis equal vertical distances are equal *returns*,
    which is what is being compared.

    Buy & hold is always drawn, in a fixed recessive style, however it
    ranks: it is the thing every other line has to beat, so it should look
    the same in every chart rather than changing colour with its rank.
    """
    _style()
    fig, ax = plt.subplots(figsize=(9.5, 4.6))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)

    bench_key = next((k for k in curves if k.endswith("buy & hold")), None)
    ranked = sorted(
        ((k, v) for k, v in curves.items() if k != bench_key),
        key=lambda kv: -float(kv[1].iloc[-1]),
    )
    keep = ranked[: max(1, top - 2)]
    if ranked and ranked[-1] not in keep:
        keep.append(ranked[-1])

    if bench_key:
        b = curves[bench_key]
        ax.plot(b.index, b.values, lw=1.6, color=INK_2, ls="--", zorder=4,
                label=f"{bench_key}  {currency}{float(b.iloc[-1]):,.0f}")
    for i, (label, eq) in enumerate(keep):
        ax.plot(eq.index, eq.values, lw=1.3, color=CATEGORICAL[i % len(CATEGORICAL)],
                label=f"{label}  {currency}{float(eq.iloc[-1]):,.0f}", zorder=3)

    ax.set_yscale("log")
    ax.set_title(title, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    return _save(fig, out)


def chart_day_of_month(table: pd.DataFrame, band, out: Path, title: str) -> Path:
    """Day-of-month terminal multiples against the randomised-day null.

    The shaded band is the point: bars inside it are indistinguishable from
    picking a day at random, and almost always every bar is inside it.
    """
    _style()
    df = table[table["day"].str.isdigit()].copy()
    df["day_i"] = df["day"].astype(int)
    df = df.sort_values("day_i")
    fig, ax = plt.subplots(figsize=(9.5, 3.6))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)
    ax.axhspan(band.p05, band.p95, color=GRID, zorder=1,
               label="random-day null, 5-95th pct")
    ax.axhline(band.p50, color=MUTED, lw=1, zorder=2, label="random-day median")
    colours = [POS if v >= band.p50 else NEG for v in df["multiple"]]
    ax.bar(df["day_i"], df["multiple"], color=colours, zorder=3, width=0.72)
    lo = min(float(df["multiple"].min()), band.p05)
    hi = max(float(df["multiple"].max()), band.p95)
    pad = (hi - lo) * 0.25 or 0.01
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_xlabel("calendar day of contribution")
    ax.set_ylabel("terminal / contributed")
    ax.set_title(title, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8)
    return _save(fig, out)


def _slug(text: str) -> str:
    keep = [c if (c.isalnum() or c in "-_.") else "_" for c in str(text)]
    out = "".join(keep)
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")[:60] or "x"


def _md_table(df: pd.DataFrame) -> str:
    """Markdown table without pulling in `tabulate` for one call.

    Numeric columns are right-aligned so a column of returns can be scanned
    down rather than read across.
    """
    if df is None or df.empty:
        return "_(no rows)_\n"

    def cell(v) -> str:
        if v is None or (isinstance(v, float) and v != v):
            return "—"
        if isinstance(v, float):
            # values arrive already rounded by `row()`; print them as they
            # are rather than forcing a width that drops the 4th decimal the
            # day-of-month multiples are actually decided on
            txt = f"{v:,.4f}".rstrip("0").rstrip(".")
            return txt or "0"
        if isinstance(v, (int,)) and not isinstance(v, bool):
            return f"{v:,}"
        return str(v)

    cols = list(df.columns)
    body = [[cell(v) for v in row] for row in df.itertuples(index=False)]
    numeric = [
        pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
        for c in cols
    ]
    widths = [
        max(len(str(c)), *(len(r[i]) for r in body)) if body else len(str(c))
        for i, c in enumerate(cols)
    ]
    head = "| " + " | ".join(str(c).ljust(widths[i]) for i, c in enumerate(cols)) + " |"
    rule = "| " + " | ".join(
        ("-" * (widths[i] - 1) + ":") if numeric[i] else ("-" * widths[i])
        for i in range(len(cols))
    ) + " |"
    lines = [head, rule]
    for r in body:
        lines.append("| " + " | ".join(
            r[i].rjust(widths[i]) if numeric[i] else r[i].ljust(widths[i])
            for i in range(len(cols))
        ) + " |")
    return "\n".join(lines) + "\n"


def write_report(
    out: Path, market: str, results: dict, cost_bps: float, taxed: bool,
    command: str,
) -> Path:
    cfg = MARKETS[market]
    md: list[str] = [
        f"# {cfg.name} — index investing backtests",
        "",
        f"Cost {cost_bps:g}bps per side on top of each series' expense ratio. "
        f"Tax: **{'on' if taxed else 'off'}**"
        + (f" ({_tax(market, True).label})." if taxed else " (pre-tax only).")
        + " Dividends are INCLUDED throughout (total-return series).",
        "",
    ]

    figs = out / "figures"
    for family, payload in results.items():
        md += [f"## Family {family}", ""]
        for title, note in (payload.get("extra") or {}).items():
            md += [f"### {title}", "", "```", note.verdict(), "```", ""]
            md += [f"- {line}" for line in note.details()] + [""]
        for title, df in payload["tables"].items():
            md += [f"### {title}", "", _md_table(df), ""]
            fname = _slug(title) + ".csv"
            df.to_csv(out / fname, index=False)

    # charts
    md += ["## Charts", ""]
    for family, payload in results.items():
        curves = payload.get("curves")
        if curves:
            p = chart_curves(curves, figs / f"family_{family}_equity.png",
                             cfg.currency_symbol, f"Family {family} — equity (log scale)")
            md += [f"![Family {family}](figures/{p.name})", ""]
            # saved so the chart can be redrawn without re-simulating, the
            # same way report.py re-renders a stock backtest from its CSVs
            pd.DataFrame(curves).to_csv(out / f"equity_family_{family}.csv")
        for title, band in (payload.get("extra") or {}).items():
            if not hasattr(band, "p05"):
                continue   # a decomposition note, not a placebo band
            # Match the band to ITS OWN window's table. India runs two
            # windows, so picking the first "A1" table would chart the same
            # data twice under two different captions.
            window = title.split("—", 1)[-1].strip()
            key = next(
                (k for k in payload["tables"]
                 if k.startswith("A1") and k.split("—", 1)[-1].strip() == window),
                None,
            )
            if not key:
                continue
            p = chart_day_of_month(
                payload["tables"][key], band,
                figs / f"day_of_month_{_slug(window)}.png",
                f"Terminal wealth per unit contributed, by contribution day — {window}",
            )
            md += [f"![{title}](figures/{p.name})", ""]

    md += [
        "## Caveats",
        "",
        "- **Survivorship-bias free.** Unlike the stock-level backtests here, an "
        "index series has no selection step, so none of the usual universe bias "
        "applies. Index *reconstitution* is inside the index's own return.",
        "- **Dividends included** via total-return series; price-only indices carry "
        "an empirically calibrated accrual (see `index_data.py`), which is stated "
        "per run in the series caveats.",
        "- **Cash earns a real rate** (T-bill for the US, realised liquid-fund yield "
        "for India). Every waiting strategy is credited with that interest.",
        "- **Loss carry-forward is not modelled**, so taxed runs overstate the bill "
        "for strategies that book losses and gains in different years.",
        "- **Expense ratios are charged daily**; fund-level tracking error is not "
        "modelled beyond what the ETF series already contain.",
        "- **One path.** Even 46 years is a single realisation. Sub-period tables are "
        "there because a ranking that only holds on the full window is a fit to it.",
        "",
        "## Reproduce",
        "",
        "```bash",
        command,
        "```",
        "",
    ]
    path = out / "report.md"
    path.write_text("\n".join(md))
    return path


FAMILIES = {"A": family_a, "B": family_b, "C": family_c, "D": family_d}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Index-investing backtests (Families A-D)")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--family", nargs="*", default=list(FAMILIES),
                    choices=list(FAMILIES), help="which families to run")
    ap.add_argument("--cost-bps", type=float, default=None,
                    help="per side, on top of each series' expense ratio")
    ap.add_argument("--no-tax", action="store_true",
                    help="pre-tax only (default reports both pre- and after-tax)")
    ap.add_argument("--quick", action="store_true",
                    help="fewer placebo draws and coarser A5 start grid")
    ap.add_argument("--run", default=None, help="run directory name")
    args = ap.parse_args()

    cost = DEFAULT_COST_BPS[args.market] if args.cost_bps is None else args.cost_bps
    taxed = not args.no_tax

    results = {}
    for fam in args.family:
        logger.info("=== Family %s (%s) ===", fam, args.market)
        results[fam] = FAMILIES[fam](args.market, cost, taxed, args.quick)

    name = args.run or (
        f"{'-'.join(args.family)}_{cost:g}bps" + ("_taxed" if taxed else "_pretax")
    )
    out = run_dir(args.market, "index_investing", name)
    cmd = (
        f"PYTHONPATH=. python3 -m swing_screener.backtesting.index_investing "
        f"--market {args.market} --family {' '.join(args.family)} --cost-bps {cost:g}"
        + (" --no-tax" if not taxed else "") + (" --quick" if args.quick else "")
    )
    path = write_report(out, args.market, results, cost, taxed, cmd)

    for fam, payload in results.items():
        for title, df in payload["tables"].items():
            print(f"\n=== {title} ===")
            print(df.to_string(index=False))
        for title, band in (payload.get("extra") or {}).items():
            print(f"\n=== {title} ===\n{band.verdict()}")
    print(f"\nReport -> {path}")


if __name__ == "__main__":
    main()
