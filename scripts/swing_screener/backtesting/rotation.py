"""The engine both asset-rotation strategies share: hold a set of series, rebalance on a calendar.

Dual momentum holds one asset with a safe fallback; sector rotation holds the strongest few. The
DECISION differs and the accounting does not, so the accounting lives here once -- entry and exit
prices, costs on each side of a switch, the equity curve and a trade row per holding period.

This is not `portfolio_sim`. That one holds STOCKS with stops, targets, position sizing and a
cash constraint; none of which exists here, where a rebalance replaces the whole book by
construction and a "trade" is a holding period in one series.
"""
from __future__ import annotations

import pandas as pd


def rebalance_dates(index: pd.DatetimeIndex, start: pd.Timestamp, rule: str) -> list:
    """The last stored session of each period — never a calendar date that may be a holiday."""
    idx = pd.DatetimeIndex([d for d in index if d >= start])
    if not len(idx):
        return []
    last = idx.to_series().resample(rule).last().dropna()
    return [d for d in last if d in index]


def simulate(px: pd.DataFrame, pick, start: str, rebalance: str = "ME",
             cost_bps: float = 10.0, account_size: float = 1_000_000.0,
             lookback_days: int = 252, credits=None, exit_check=None):
    """Walk the calendar holding whatever `pick` returns.

    `pick(date, returns, px)` -> list of column names to hold, equal-weighted. An empty list means
    hold nothing (cash). Returns are trailing `lookback_days` simple returns, passed in rather than
    recomputed per strategy so both see the same definition.

    `credits` (marketdata.corporate_actions.Credits), for a frame of stocks: a holding receives the
    cash of a special dividend or demerger on its ex-date, where the stored close only falls.

    `exit_check(date, held)` -> holdings to sell at that session's close, BETWEEN rebalances (a
    trailing exit such as a close below an average). The money waits in cash for the next rebalance.
    None, the default, trades only on rebalance dates.
    """
    start_ts = pd.Timestamp(start)
    ret = px / px.shift(lookback_days) - 1.0
    rebals = set(rebalance_dates(px.index, start_ts, rebalance))

    # MARK TO THE LAST KNOWN PRICE, never to nothing. `value()` used to skip a holding whose price
    # was NaN on the day, which values it at ZERO rather than at its last trade -- so an interior
    # gap in the series made part of the book disappear and reappear. With a handful of index
    # series that was invisible; across a stock cross-section it is not. India's frame carries
    # 56,738 interior NaNs, and on 2010-02-06 every symbol was NaN at once, so the whole book
    # vanished for one session and the equity curve printed bare cash -- a one-day -100% spike
    # that set the reported max drawdown for every run through this engine.
    #
    # ffill only fills AFTER a series' first observation, so a pre-listing NaN still blocks a pick
    # (it stays NaN in `ret`, and `pick` reads the raw frame). Execution prices come from here too:
    # trading at the last known price is what a real book does, and it is strictly better than the
    # alternative, which was multiplying by NaN and poisoning cash permanently.
    pxv = px.ffill()

    cash = float(account_size)
    units: dict[str, float] = {}
    # per holding period: entry date, cash paid (buys with costs), cash got back (trims net of
    # costs), units bought, costs. A rebalance resizes a holding that stays in the target, so
    # a trade row from the first fill alone misstated its P&L while equity, read from cash,
    # stayed right.
    entry: dict[str, dict] = {}
    trades, equity, held, costs_total = [], [], [], 0.0

    credited: dict[str, float] = {}   # special dividends / demergers received over the holding period

    def row(s, d, price, u, fee, reason) -> dict:
        e = entry.pop(s)
        cr = credited.pop(s, 0.0)
        return {"symbol": s, "entry_date": e["date"],
                "entry_price": round(e["paid"] / e["bought"], 4) if e["bought"] else round(price, 4),
                "exit_date": d, "exit_price": round(price, 4), "shares": round(e["bought"], 4),
                "exit_reason": reason, "pnl": round(u * price - fee + e["got"] + cr - e["paid"], 2),
                **({"credited": round(cr, 2)} if credits is not None else {}),
                "notional": round(e["paid"], 2), "costs": round(e["costs"] + fee, 2),
                "holding_days": (d - e["date"]).days,
                "r_multiple": round((u * price - fee + e["got"] + cr) / e["paid"] - 1, 4)}

    def value(d) -> float:
        return cash + sum(u * float(pxv.loc[d, s]) for s, u in units.items()
                          if pd.notna(pxv.loc[d, s]))

    credit_after = None
    for d in px.index[px.index >= start_ts]:
        if credits is not None:
            for s, c in credits.on(d, credit_after, units).items():
                cash += units[s] * c
                credited[s] = credited.get(s, 0.0) + units[s] * c
            credit_after = d
        if d not in rebals and exit_check is not None and units:
            for s in [s for s in (exit_check(d, list(units)) or []) if s in units]:
                price = float(pxv.loc[d, s])
                gross = units[s] * price
                fee = gross * cost_bps / 10_000
                cash += gross - fee
                costs_total += fee
                trades.append(row(s, d, price, units[s], fee, "EXIT_RULE"))
                del units[s]
        if d in rebals:
            target = list(pick(d, ret.loc[d], px) or [])
            # sell what is no longer wanted, at this session's close
            for s in [s for s in units if s not in target]:
                price = float(pxv.loc[d, s])
                gross = units[s] * price
                fee = gross * cost_bps / 10_000
                cash += gross - fee
                costs_total += fee
                trades.append(row(s, d, price, units[s], fee, "ROTATE"))
                del units[s]
            if target:
                # equal weight across the target, rebuilt from the whole book so weights stay level
                total = value(d)
                per = total / len(target)
                for s in target:
                    price = float(pxv.loc[d, s])
                    want = per / price
                    have = units.get(s, 0.0)
                    delta = want - have
                    if abs(delta * price) < total * 1e-4:     # ignore dust
                        continue
                    fee = abs(delta) * price * cost_bps / 10_000
                    cash -= delta * price + fee
                    costs_total += fee
                    units[s] = want
                    e = entry.setdefault(s, {"date": d, "paid": 0.0, "got": 0.0,
                                             "bought": 0.0, "costs": 0.0})
                    if delta > 0:
                        e["paid"] += delta * price + fee
                        e["bought"] += delta
                    else:
                        e["got"] += -delta * price - fee
                    e["costs"] += fee
        equity.append((d, value(d)))
        held.append(len(units))

    eq = pd.Series(dict(equity)).sort_index()
    if units:
        d = eq.index[-1]
        for s, u in units.items():
            trades.append(row(s, d, float(pxv.loc[d, s]), u, 0.0, "OPEN"))
    tdf = pd.DataFrame(trades)
    # holdings per SESSION -- exposure and the cash series read it, so a constant (the final
    # count repeated, as it was) showed 100% exposure through every risk-off stretch
    held = pd.Series(held, index=[d for d, _ in equity]).sort_index()
    return tdf, eq, held, costs_total
