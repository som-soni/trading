"""Families B, C and D — what to do with capital already invested.

Every strategy here reduces to the same object: a frame of TARGET WEIGHTS,
one row per trading day, one column per sleeve, already lagged by
`index_signals`. Weights summing to less than 1 leave the remainder in
cash, earning the cash rate.

Expressing a trend overlay, a 60/40 mix and a momentum rotation in one
shape is what makes them comparable — the alternative is three simulators
with three sets of quiet assumptions about costs and timing, which is how
"strategy A beats strategy B" turns out to mean "simulator A is kinder
than simulator B".

Rebalancing fires on a cadence (`ME`/`QE`/`YE`/`never`) **and** whenever
the target weights change, so a signal flip is acted on the day it happens
rather than waiting for the next calendar date.
"""

import numpy as np
import pandas as pd

from . import index_core as core
from . import index_signals as sig
from .index_core import Book, Context, Result, TaxModel


def simulate(
    ctx: Context,
    targets: pd.DataFrame,
    initial: float,
    cost_bps: float,
    tax: TaxModel,
    rebalance: str = "never",
    band: float = 0.0,
    name: str = "",
) -> Result:
    """Run one target-weight frame through the book."""
    targets = targets.reindex(ctx.index).fillna(0.0).clip(lower=0.0)
    over = targets.sum(axis=1)
    if (over > 1.0 + 1e-9).any():
        # No leverage anywhere in this suite: scale back rather than borrow,
        # because a borrowing cost model would be a separate assumption.
        targets = targets.div(over.where(over > 1.0, 1.0), axis=0)

    cadence: set = set()
    if rebalance and rebalance != "never":
        ser = pd.Series(ctx.index, index=ctx.index)
        cadence = set(ser.resample(rebalance).last().dropna())

    book = Book(initial, cost_bps, tax)
    eq_rows, cash_rows, exp_rows = [], [], []
    applied: pd.Series | None = None
    dates = ctx.index

    prev_day = None
    for i, today in enumerate(dates):
        book.accrue(
            float(ctx.cash_rate.loc[today]),
            days=1 if prev_day is None else max((today - prev_day).days, 0),
        )
        prev_day = today
        prices = ctx.px(today)
        equity = book.equity(prices)

        want = targets.loc[today]
        changed = applied is None or not np.allclose(
            want.values, applied.values, atol=1e-9
        )
        if changed or today in cadence:
            core.rebalance_to(
                book, today, want.to_dict(), prices, equity,
                band=0.0 if changed else band,
                reason="SIGNAL" if changed else "REBALANCE",
            )
            applied = want

        nxt = dates[i + 1] if i + 1 < len(dates) else None
        if tax.enabled and tax.is_fy_end(today, nxt):
            book.settle_fiscal_year(today, prices)

        held = book.holdings_value(prices)
        eq_rows.append(book.cash + held)
        cash_rows.append(book.cash)
        exp_rows.append(held / (book.cash + held) if (book.cash + held) > 0 else 0.0)

    last = dates[-1]
    final_px = ctx.px(last)
    terminal = book.terminal_tax(last, final_px)

    eq = pd.Series(eq_rows, index=dates, name="equity")
    notes = list(ctx.caveats)
    if tax.enabled:
        notes.append(
            f"Tax: {tax.label}. Realised gains taxed at each fiscal year end; the "
            f"terminal unrealised gain is also settled so a buy-and-hold book does "
            f"not get free deferral. Loss carry-forward is NOT modelled, which "
            f"overstates tax for strategies that book losses and gains in different years."
        )
    return Result(
        equity=eq, cash=pd.Series(cash_rows, index=dates),
        exposure=pd.Series(exp_rows, index=dates),
        weights=targets, trades=core.trades_frame(book.trades),
        costs_paid=book.costs_paid, tax_paid=book.tax_paid,
        terminal_tax=terminal, caveats=notes, meta={"name": name},
    )


# --- strategy builders ---------------------------------------------------
#
# Each returns (target_weight_frame, rebalance_cadence). Nothing here reads
# a price it should not: the signals are lagged in index_signals.


def buy_hold(ctx: Context, asset: str) -> tuple[pd.DataFrame, str]:
    return pd.DataFrame({asset: 1.0}, index=ctx.index), "never"


def static_mix(ctx: Context, weights: dict[str, float], rebalance: str) -> tuple[pd.DataFrame, str]:
    return pd.DataFrame(
        {a: w for a, w in weights.items()}, index=ctx.index
    ), rebalance


def trend_overlay(
    ctx: Context, asset: str, kind: str = "sma10", safe: str | None = None, **kw
) -> tuple[pd.DataFrame, str]:
    """Hold `asset` while its trend signal is on, else `safe` (or cash)."""
    px = ctx.prices[asset]
    if kind == "sma10":
        on = sig.sma_overlay(px, months=kw.get("months", 10))
    elif kind == "dma":
        on = sig.dma_cross(px, window=kw.get("window", 200))
    elif kind == "golden":
        on = sig.golden_cross(px, kw.get("fast", 50), kw.get("slow", 200))
    elif kind == "absmom":
        on = sig.abs_momentum(px, kw.get("lookback", 252), kw.get("skip", 0))
    elif kind == "dualmom":
        on = sig.excess_momentum(px, ctx.cash_rate, kw.get("lookback", 252))
    else:
        raise ValueError(f"unknown overlay '{kind}'")

    frame = pd.DataFrame(0.0, index=ctx.index, columns=sorted({asset, safe} - {None}))
    frame[asset] = on.reindex(ctx.index).fillna(False).astype(float)
    if safe:
        frame[safe] = 1.0 - frame[asset]
    return frame, "never"


def vol_targeted(ctx: Context, asset: str, target: float, window: int = 63) -> tuple[pd.DataFrame, str]:
    w = sig.vol_target_weight(ctx.prices[asset], target, window)
    # Round to 5% steps so the book is not rebalanced every single day by a
    # 0.3% drift in realised vol — the untruncated version pays costs daily
    # and measures the cost model more than the idea.
    w = (w * 20).round() / 20
    return pd.DataFrame({asset: w.reindex(ctx.index).fillna(0.0)}), "never"


def seasonal_only(ctx: Context, asset: str, months: tuple[int, ...]) -> tuple[pd.DataFrame, str]:
    on = sig.seasonal(ctx.index, months)
    return pd.DataFrame({asset: on.astype(float)}, index=ctx.index), "never"


def dip_entry(ctx: Context, asset: str, threshold: float) -> tuple[pd.DataFrame, str]:
    """Family B7 — sit in cash until the index is `threshold` below its peak.

    Once in, stay in. This is the "waiting for a better entry" strategy as
    people actually run it, not a repeated trade.
    """
    dd = sig.drawdown_from_peak(ctx.prices[asset])
    triggered = (dd >= threshold).cummax()
    return pd.DataFrame({asset: triggered.astype(float)}, index=ctx.index), "never"


def rotation(
    ctx: Context, sleeves: list[str], lookback: int = 252, top_n: int = 1,
    absolute: bool = True, cadence: str = "ME",
) -> tuple[pd.DataFrame, str]:
    """Family D — hold the top `top_n` sleeves by trailing return.

    With `absolute`, a sleeve must also beat cash to be held, which is
    Antonacci's dual-momentum construction: relative momentum picks what to
    own, absolute momentum decides whether to own anything at all.
    """
    scores = sig.rank_momentum({s: ctx.prices[s] for s in sleeves}, lookback)
    cash_leg = (
        (1 + ctx.cash_rate.fillna(0) / 252)
        .rolling(lookback, min_periods=lookback).apply(np.prod, raw=True) - 1
    ).shift(1)

    frame = pd.DataFrame(0.0, index=ctx.index, columns=sleeves)
    # Decide on cadence ends only, then hold until the next one — a daily
    # argmax on a 12-month lookback churns on ties that mean nothing.
    ser = pd.Series(ctx.index, index=ctx.index)
    decision_days = sorted(set(ser.resample(cadence).last().dropna()))
    current: dict[str, float] = {}
    for today in ctx.index:
        if today in decision_days:
            row = scores.loc[today].dropna()
            if absolute:
                bar = cash_leg.get(today, 0.0)
                row = row[row > (bar if bar == bar else 0.0)]
            picks = list(row.sort_values(ascending=False).index[:top_n])
            current = {p: 1.0 / len(picks) for p in picks} if picks else {}
        for a, w in current.items():
            frame.loc[today, a] = w
    return frame, "never"


def inverse_vol_mix(
    ctx: Context, sleeves: list[str], window: int = 63, cadence: str = "QE"
) -> tuple[pd.DataFrame, str]:
    """Family D3 — weight sleeves inversely to their own volatility."""
    rv = pd.DataFrame(
        {s: ctx.prices[s].pct_change().rolling(window, min_periods=window // 2).std()
         for s in sleeves}
    ).shift(1)
    inv = (1.0 / rv.replace(0, np.nan))
    frame = inv.div(inv.sum(axis=1), axis=0).reindex(ctx.index).ffill().fillna(0.0)
    return frame, cadence
