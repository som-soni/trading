"""Family A — recurring contributions, and when to make them.

This is the SIP question: a fixed amount arrives every month, and the only
choice is what day to buy and whether to hold any of it back. CAGR cannot
score it — contribute more in later years and the equity curve's CAGR falls
although nothing about the strategy changed — so everything here is judged
on XIRR and on terminal wealth per unit contributed, with total
contributions held identical across variants by construction.

Two guards keep the comparisons honest:

* **Same money, same dates.** Every variant contributes the same amount on
  the same schedule; only the *deployment* rule differs. A variant that
  held cash is credited with the interest that cash earned.

* **One deliberate cheat, clearly labelled.** `hindsight` buys each month's
  lowest close, which is impossible. It is included because it bounds the
  entire question: if perfect monthly timing only adds 40bps, no real rule
  can add more, and every other variant in the family can be read against
  that ceiling.
"""

import calendar

import numpy as np
import pandas as pd

from . import index_core as core
from . import index_signals as sig
from .index_core import Book, Context, Result, TaxModel

DAY_LABELS = {"first": "first trading day", "last": "last trading day"}


# --- contribution schedules ---------------------------------------------


def monthly_dates(index: pd.DatetimeIndex, day) -> list[pd.Timestamp]:
    """Trading day for each month given a calendar-day preference.

    `day` is 1-28, "first", or "last". A chosen day that is a weekend or
    holiday rolls FORWARD to the next trading day in the same month —
    which is what a real mandate does, and what makes days 29-31 ambiguous
    enough to exclude from the sweep.
    """
    out: list[pd.Timestamp] = []
    by_month = pd.Series(index, index=index).groupby([index.year, index.month])
    for _, days in by_month:
        days = list(days)
        if day == "first":
            out.append(days[0])
        elif day == "last":
            out.append(days[-1])
        else:
            target = int(day)
            last_dom = calendar.monthrange(days[0].year, days[0].month)[1]
            target = min(target, last_dom)
            pick = next((d for d in days if d.day >= target), days[-1])
            out.append(pick)
    return out


def weekly_dates(index: pd.DatetimeIndex, weekday: int) -> list[pd.Timestamp]:
    """One trading day per ISO week: the first on or after `weekday` (0=Mon)."""
    out: list[pd.Timestamp] = []
    for _, days in pd.Series(index, index=index).groupby(
        [index.isocalendar().year, index.isocalendar().week]
    ):
        days = list(days)
        pick = next((d for d in days if d.weekday() >= weekday), days[-1])
        out.append(pick)
    return out


def periodic_dates(index: pd.DatetimeIndex, freq: str) -> list[pd.Timestamp]:
    """Last trading day of each period for a pandas offset alias."""
    ser = pd.Series(index, index=index)
    return list(ser.resample(freq).last().dropna())


def schedule(
    index: pd.DatetimeIndex, kind: str, annual_amount: float, **kw
) -> tuple[pd.Series, str]:
    """(date -> amount, label). Total annual contribution is held constant
    across every frequency so A4 compares timing, not savings rate."""
    if kind == "dom":
        day = kw["day"]
        dates = monthly_dates(index, day)
        label = f"monthly, {DAY_LABELS.get(day, f'day {day}')}"
        per = annual_amount / 12
    elif kind == "dow":
        wd = kw["weekday"]
        dates = weekly_dates(index, wd)
        label = f"weekly, {calendar.day_name[wd]}"
        per = annual_amount / 52
    elif kind == "freq":
        freq = kw["freq"]
        if freq == "D":
            dates = list(index)
            per = annual_amount / 252
        else:
            dates = periodic_dates(index, freq)
            per_year = {"W-FRI": 52, "SME": 24, "ME": 12, "QE": 4, "YE": 1}[freq]
            per = annual_amount / per_year
        label = f"every {freq}"
    elif kind == "lump":
        dates = [index[0]]
        per = kw["amount"]
        label = "lump sum"
    elif kind == "step_up":
        # same first-year rate, raised `step` each year — the control that
        # shows how little any timing choice matters next to saving more
        dates = monthly_dates(index, kw.get("day", 1))
        step = kw.get("step", 0.10)
        base = annual_amount / 12
        amounts = {}
        y0 = dates[0].year
        for d in dates:
            amounts[d] = base * (1 + step) ** (d.year - y0)
        return pd.Series(amounts).sort_index(), f"monthly, +{step * 100:.0f}%/yr step-up"
    else:
        raise ValueError(f"unknown schedule '{kind}'")
    return pd.Series(per, index=pd.DatetimeIndex(dates)).sort_index(), label


# --- the accumulator -----------------------------------------------------


def simulate(
    ctx: Context,
    asset: str,
    contributions: pd.Series,
    cost_bps: float,
    tax: TaxModel,
    deploy: str = "immediate",
    dip_threshold: float = 0.10,
    ma_window: int = 200,
    spread_months: int = 12,
    growth: float = 0.10,
    name: str = "",
) -> Result:
    """Run one contribution schedule under one deployment rule.

    `deploy`:
      immediate     buy on the day the money arrives
      spread        a lump split into `spread_months` monthly instalments
      dip           hold cash; deploy the lot once the index is
                    `dip_threshold` below its running peak (repeatable)
      trend_on      hold cash while price is below its `ma_window` MA
      trend_double  buy 0.5x above the MA, 2x below (from the banked rest)
      value_avg     Edleson: top the book up to a compounding target path
      hindsight     buy at each month's LOWEST close — impossible, included
                    as the ceiling on what any timing rule could achieve
    """
    px = ctx.prices[asset]
    dates = ctx.index
    contributions = contributions.reindex(dates).fillna(0.0)

    dd = sig.drawdown_from_peak(px)
    above_ma = sig.dma_cross(px, ma_window)

    # hindsight: the lowest close in each month, known only afterwards
    low_day: set = set()
    if deploy == "hindsight":
        for _, days in pd.Series(dates, index=dates).groupby([dates.year, dates.month]):
            month_px = px.reindex(list(days))
            low_day.add(month_px.idxmin())

    # value averaging needs the target path in advance
    target_path = None
    if deploy == "value_avg":
        monthly_r = (1 + growth) ** (1 / 12) - 1
        target, acc = {}, 0.0
        k = 0
        for d in dates:
            if contributions.loc[d] > 0:
                k += 1
                acc = acc * (1 + monthly_r) ** 1 + contributions.loc[d]
                target[d] = acc
        target_path = pd.Series(target)

    spread_remaining = 0.0
    spread_dates: list = []
    if deploy == "spread":
        total = float(contributions.sum())
        spread_dates = monthly_dates(dates, "first")[:spread_months]
        spread_remaining = total

    book = Book(0.0, cost_bps, tax)
    eq_rows, cash_rows, exp_rows = [], [], []
    cashflows: list[tuple[pd.Timestamp, float]] = []
    contributed = 0.0

    prev_day = None
    for i, today in enumerate(dates):
        book.accrue(
            float(ctx.cash_rate.loc[today]),
            days=1 if prev_day is None else max((today - prev_day).days, 0),
        )
        prev_day = today
        price = float(px.loc[today]) if px.loc[today] == px.loc[today] else None

        amt = float(contributions.loc[today])
        if amt > 0:
            book.cash += amt
            contributed += amt
            cashflows.append((today, amt))

        if price:
            if deploy == "immediate":
                if amt > 0:
                    book.buy(today, asset, book.cash, price, "SIP")

            elif deploy == "spread":
                if today in spread_dates and spread_remaining > 0:
                    slice_amt = min(book.cash, spread_remaining / max(
                        len([d for d in spread_dates if d >= today]), 1))
                    book.buy(today, asset, slice_amt, price, "DCA_SLICE")
                    spread_remaining -= slice_amt

            elif deploy == "dip":
                if float(dd.loc[today]) >= dip_threshold and book.cash > 0:
                    book.buy(today, asset, book.cash, price, "DIP")

            elif deploy == "trend_on":
                if bool(above_ma.loc[today]) and book.cash > 0:
                    book.buy(today, asset, book.cash, price, "TREND_ON")

            elif deploy == "trend_double":
                if amt > 0:
                    want = amt * (0.5 if bool(above_ma.loc[today]) else 2.0)
                    book.buy(today, asset, min(want, book.cash), price, "TREND_SIZED")

            elif deploy == "value_avg":
                if target_path is not None and today in target_path.index:
                    want = float(target_path.loc[today])
                    have = book.shares(asset) * price
                    gap = want - have
                    if gap > 0:
                        book.buy(today, asset, min(gap, book.cash), price, "VA_BUY")
                    elif gap < -1e-9:
                        # Edleson sells when ahead of the path. The proceeds
                        # stay in the book as cash, so the investor's own
                        # outlay is unchanged and XIRR stays comparable.
                        book.sell_value(today, asset, -gap, price, "VA_SELL")

            elif deploy == "hindsight":
                if today in low_day and book.cash > 0:
                    book.buy(today, asset, book.cash, price, "HINDSIGHT_LOW")

            else:
                raise ValueError(f"unknown deploy rule '{deploy}'")

        nxt = dates[i + 1] if i + 1 < len(dates) else None
        if tax.enabled and tax.is_fy_end(today, nxt):
            book.settle_fiscal_year(today, ctx.px(today))

        held = book.holdings_value(ctx.px(today))
        total_v = book.cash + held
        eq_rows.append(total_v)
        cash_rows.append(book.cash)
        exp_rows.append(held / total_v if total_v > 0 else 0.0)

    last = dates[-1]
    terminal = book.terminal_tax(last, ctx.px(last))

    notes = list(ctx.caveats)
    if deploy == "hindsight":
        notes.append(
            "LOOKAHEAD BY DESIGN: buys each month's lowest close, which cannot be "
            "known in advance. Read it as the ceiling on monthly timing, not a strategy."
        )
    if tax.enabled:
        notes.append(f"Tax: {tax.label}, incl. terminal unrealised gain.")

    return Result(
        equity=pd.Series(eq_rows, index=dates, name="equity"),
        cash=pd.Series(cash_rows, index=dates),
        exposure=pd.Series(exp_rows, index=dates),
        weights=pd.DataFrame({asset: pd.Series(exp_rows, index=dates)}),
        trades=core.trades_frame(book.trades),
        cashflows=cashflows, contributed=contributed,
        costs_paid=book.costs_paid, tax_paid=book.tax_paid,
        terminal_tax=terminal, caveats=notes, meta={"name": name, "deploy": deploy},
    )


def random_day_draws(
    ctx: Context, asset: str, annual_amount: float, cost_bps: float,
    tax: TaxModel, draws: int = 200, seed: int = 11,
) -> list[float]:
    """The null for A1: contribute on a RANDOM trading day each month.

    This is what "no day-of-month effect" actually looks like as a
    distribution. Comparing the best of 30 fixed days against it is the
    only way to tell a real effect from the maximum of 30 noisy draws.
    """
    rng = np.random.default_rng(seed)
    months = [
        list(days) for _, days in
        pd.Series(ctx.index, index=ctx.index).groupby([ctx.index.year, ctx.index.month])
    ]
    out: list[float] = []
    for _ in range(draws):
        picks = [m[rng.integers(0, len(m))] for m in months]
        sched = pd.Series(annual_amount / 12, index=pd.DatetimeIndex(sorted(picks)))
        res = simulate(ctx, asset, sched, cost_bps, tax, deploy="immediate")
        out.append(float(res.equity.iloc[-1]) / float(res.contributed))
    return out
