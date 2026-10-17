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
             lookback_days: int = 252):
    """Walk the calendar holding whatever `pick` returns.

    `pick(date, returns, px)` -> list of column names to hold, equal-weighted. An empty list means
    hold nothing (cash). Returns are trailing `lookback_days` simple returns, passed in rather than
    recomputed per strategy so both see the same definition.
    """
    start_ts = pd.Timestamp(start)
    ret = px / px.shift(lookback_days) - 1.0
    rebals = set(rebalance_dates(px.index, start_ts, rebalance))

    cash = float(account_size)
    units: dict[str, float] = {}
    entry: dict[str, tuple] = {}
    trades, equity, costs_total = [], [], 0.0

    def value(d) -> float:
        return cash + sum(u * float(px.loc[d, s]) for s, u in units.items() if pd.notna(px.loc[d, s]))

    for d in px.index[px.index >= start_ts]:
        if d in rebals:
            target = list(pick(d, ret.loc[d], px) or [])
            # sell what is no longer wanted, at this session's close
            for s in [s for s in units if s not in target]:
                price = float(px.loc[d, s])
                gross = units[s] * price
                fee = gross * cost_bps / 10_000
                cash += gross - fee
                costs_total += fee
                e_date, e_price, e_cost = entry.pop(s)
                trades.append({"symbol": s, "entry_date": e_date, "entry_price": round(e_price, 4),
                               "exit_date": d, "exit_price": round(price, 4), "shares": round(units[s], 4),
                               "exit_reason": "ROTATE", "pnl": round(gross - fee - e_cost, 2),
                               "notional": round(e_cost, 2), "costs": round(fee, 2),
                               "holding_days": (d - e_date).days,
                               "r_multiple": round((gross - fee) / e_cost - 1, 4)})
                del units[s]
            if target:
                # equal weight across the target, rebuilt from the whole book so weights stay level
                total = value(d)
                per = total / len(target)
                for s in target:
                    price = float(px.loc[d, s])
                    want = per / price
                    have = units.get(s, 0.0)
                    delta = want - have
                    if abs(delta * price) < total * 1e-4:     # ignore dust
                        continue
                    fee = abs(delta) * price * cost_bps / 10_000
                    cash -= delta * price + fee
                    costs_total += fee
                    units[s] = want
                    if s not in entry:
                        entry[s] = (d, price, want * price)
        equity.append((d, value(d)))

    eq = pd.Series(dict(equity)).sort_index()
    if units:
        d = eq.index[-1]
        for s, u in units.items():
            price = float(px.loc[d, s])
            e_date, e_price, e_cost = entry[s]
            trades.append({"symbol": s, "entry_date": e_date, "entry_price": round(e_price, 4),
                           "exit_date": d, "exit_price": round(price, 4), "shares": round(u, 4),
                           "exit_reason": "OPEN", "pnl": round(u * price - e_cost, 2),
                           "notional": round(e_cost, 2), "costs": 0.0,
                           "holding_days": (d - e_date).days,
                           "r_multiple": round(u * price / e_cost - 1, 4)})
    tdf = pd.DataFrame(trades)
    held = pd.Series([len(units) or 1] * len(eq), index=eq.index)
    return tdf, eq, held, costs_total
