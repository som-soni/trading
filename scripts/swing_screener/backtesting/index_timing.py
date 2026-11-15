"""Timing the market index on a held-session rule -- the runner for turn of the month, pre-holiday and IBS.

Both effects say the same kind of thing: index returns are not spread evenly over the calendar, and a few
predictable sessions earn a disproportionate share. Lakonishok & Smidt (1988), on ninety years of the Dow,
found the four sessions around the turn of a month and the session before a holiday earned far more than
an ordinary day; Ariel (1987, 1990) found the same in value- and equal-weighted indices.

THE ENGINE. A day-by-day book on one series -- the market's benchmark (SPY; the Nifty 500 in India) --
fully invested on the sessions a strategy's `held` rule marks and in cash on every other. A run of held
sessions is one trade: bought at the close of the session before the first, sold at the close of the last,
`cost_bps` a side. Neither existing engine fits: `portfolio_sim` needs a stop and a trigger, `rotation`
acts only on rebalance dates.

IBS (`ibs_reversion.py`) is not a calendar effect but has the same shape -- a rule that says, at each close,
whether to own the index over the next session -- so it runs here too, from the series' highs and lows.

The strategies are thin classes in their own modules (`turn_of_month.py`, `pre_holiday.py`,
`ibs_reversion.py`) carrying their constants and documentation; each names this module as its `runner`,
and its `effect` picks the function that marks its sessions (`held_for`). Index series only: the result is read beside the index held at the same
exposure (metrics' SELECTION line), because a book in cash four days in five starts far behind on CAGR.
"""
from __future__ import annotations

import argparse
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from . import metrics

logger = logging.getLogger("backtest")


def session_calendar(index: pd.DatetimeIndex) -> pd.DataFrame:
    """Per session: its position from the month's start (1 = first session) and from its end (-1 = last
    session), and whether a weekday holiday falls between it and the next session.

    The month boundaries and the holiday test read the session list, which includes the next session.
    That is not hindsight: exchanges publish their holiday calendars a year ahead, so on any session the
    next trading day is known. At the last stored session the next is unknown, so it is marked neither
    a month end nor a pre-holiday (no signal on the final bar)."""
    idx = pd.DatetimeIndex(index).sort_values()
    s = pd.Series(range(len(idx)), index=idx)
    month = idx.to_period("M")
    from_start = s.groupby(month).cumcount() + 1
    from_end = -(s.groupby(month).cumcount(ascending=False) + 1)
    nxt = pd.Series(idx, index=idx).shift(-1)
    gap_weekdays = [
        (len(pd.bdate_range(d + pd.Timedelta(days=1), n - pd.Timedelta(days=1))) if n == n else 0)
        for d, n in zip(idx, nxt)
    ]
    out = pd.DataFrame({"from_start": from_start.to_numpy(), "from_end": from_end.to_numpy(),
                        "pre_holiday": [g > 0 for g in gap_weekdays]}, index=idx)
    # the final stored session: the next is unknown, so its month-end position is too
    if len(idx):
        out.iloc[-1, out.columns.get_loc("from_end")] = 0
        out.iloc[-1, out.columns.get_loc("pre_holiday")] = False
    return out


def held_turn_of_month(cal: pd.DataFrame, days_before: int, days_after: int) -> pd.Series:
    """Held over the last `days_before` sessions of a month and the first `days_after` of the next."""
    return (cal["from_end"].between(-days_before, -1) | cal["from_start"].between(1, days_after)).astype(bool)


def held_pre_holiday(cal: pd.DataFrame, days_before: int = 1) -> pd.Series:
    """Held over the `days_before` sessions ending with each session that precedes a weekday holiday."""
    pre = cal["pre_holiday"].astype(bool)
    out = pre.copy()
    for k in range(1, days_before):
        out |= pre.shift(-k, fill_value=False)
    return out


def held_ibs(bars: pd.DataFrame, entry: float, max_hold: int) -> pd.Series:
    """IBS reversion: at a close whose internal bar strength (close - low) / (high - low) is below `entry`,
    buy; sell at the first later close above the previous session's high, or at the close of session
    `max_hold` after the buy. Session d is marked held when the book owns the index over d's return, so a
    buy at d's close marks d+1. A session with no range (high = low) has no IBS and never signals."""
    h, l, c = (bars[k].astype(float).to_numpy() for k in ("high", "low", "close"))
    rng = h - l
    out = [False] * len(c)
    holding, bars_held = False, 0
    for i in range(len(c)):
        if holding:
            bars_held += 1
            if (i > 0 and c[i] > h[i - 1]) or bars_held >= max_hold:
                holding = False
        elif rng[i] > 0 and (c[i] - l[i]) / rng[i] < entry:
            holding, bars_held = True, 0
        if holding and i + 1 < len(c):
            out[i + 1] = True
    return pd.Series(out, index=bars.index)


def held_for(key: str, cal: pd.DataFrame, bars: pd.DataFrame | None = None) -> pd.Series:
    from ..strategies import portfolio_strategies
    cls = portfolio_strategies()[key]
    if cls.effect == "turn_of_month":
        return held_turn_of_month(cal, cls.days_before, cls.days_after)
    if cls.effect == "pre_holiday":
        return held_pre_holiday(cal, cls.days_before)
    if cls.effect == "ibs":
        return held_ibs(bars, cls.ibs_entry, cls.max_hold)
    raise ValueError(f"{key}: unknown timing rule {cls.effect!r}")


def run(market: str, start: str, held: pd.Series, close: pd.Series, cost_bps: float):
    """(trades, equity, positions_open, cash, costs) for a book holding `close` on the `held` sessions.

    Session d is held when the book owns the index over d's close-to-close return, so a run of held
    sessions starting at d is bought at the close of the session before d."""
    cfg = MARKETS[market]
    start_ts = pd.Timestamp(start)
    close = close.dropna().sort_index()
    held = held.reindex(close.index, fill_value=False).astype(bool)
    dates = close.index[close.index >= start_ts]
    cash, units, costs = float(cfg.account_size), 0.0, 0.0
    pos: dict | None = None
    trades, eq, n_open, cash_log = [], [], [], []
    for i, d in enumerate(dates):
        px = float(close.loc[d])
        # the decision at today's close: hold over the NEXT session?
        nxt = dates[i + 1] if i + 1 < len(dates) else None
        want = bool(held.loc[nxt]) if nxt is not None else False
        if units and not want:
            gross = units * px
            fee = gross * cost_bps / 10_000
            cash += gross - fee
            costs += fee
            trades.append({
                "symbol": close.name or "index", "entry_date": pos["date"], "entry_price": round(pos["price"], 4),
                "exit_date": d, "exit_price": round(px, 4), "shares": round(units, 6),
                "exit_reason": "RULE_EXIT", "pnl": round(gross - fee - pos["cost"], 2),
                "notional": round(pos["cost"], 2), "costs": round(fee + pos["fee"], 2),
                "holding_days": (d - pos["date"]).days,
                "r_multiple": round((gross - fee) / pos["cost"] - 1, 6),
            })
            units, pos = 0.0, None
        elif not units and want:
            fee = cash * cost_bps / 10_000 / (1 + cost_bps / 10_000)
            spend = cash - fee
            units = spend / px
            pos = {"date": d, "price": px, "cost": cash, "fee": fee}
            costs += fee
            cash = 0.0
        eq.append(cash + units * px)
        n_open.append(1 if units else 0)
        cash_log.append(cash)
    if units and pos is not None:   # still held at the last bar: marked there, recorded as open
        px = float(close.loc[dates[-1]])
        trades.append({
            "symbol": close.name or "index", "entry_date": pos["date"], "entry_price": round(pos["price"], 4),
            "exit_date": dates[-1], "exit_price": round(px, 4), "shares": round(units, 6),
            "exit_reason": "END", "pnl": round(units * px - pos["cost"], 2), "notional": round(pos["cost"], 2),
            "costs": round(pos["fee"], 2), "holding_days": (dates[-1] - pos["date"]).days,
            "r_multiple": round(units * px / pos["cost"] - 1, 6),
        })
    idx = pd.DatetimeIndex(dates)
    return (pd.DataFrame(trades), pd.Series(eq, index=idx), pd.Series(n_open, index=idx),
            pd.Series(cash_log, index=idx), costs)


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    from ..strategies import portfolio_strategies
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--strategy", default="turn_of_month")
    known, _ = pre.parse_known_args(argv)
    cls = portfolio_strategies()[known.strategy]
    ap = argparse.ArgumentParser(description="Timing the market index on a held-session rule")
    ap.add_argument("--strategy", default="turn_of_month", choices=sorted(HELD_RULES))
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--cost-bps", type=float, default=cls.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[a.market]
    raw = cache.load_cached(a.market, cfg.benchmark_ticker)
    if raw is None or raw.empty:
        raise ValueError(f"no stored {cfg.benchmark_ticker} for {a.market}")
    raw = raw.sort_index()
    close = raw["close"].astype(float).rename(cfg.benchmark_symbol)
    cal = session_calendar(close.index)
    held = held_for(a.strategy, cal, raw)
    tdf, eq, n_open, csh, costs = run(a.market, a.start, held, close, a.cost_bps)
    bc = close.reindex(eq.index).ffill()
    exposure = float(n_open.mean()) if len(n_open) else 0.0
    notes = [
        f"A TIMING rule on one series, {cfg.benchmark_symbol} ({cfg.benchmark_ticker}): fully invested on the "
        f"sessions it marks, in cash (earning nothing) otherwise -- in the market {exposure:.0%} of sessions.",
        cls.render_doc(cls.run_note),
        f"{a.cost_bps:g} basis points a side on each entry and exit. Read the SELECTION line: the headline "
        "CAGR is mostly cash drag by design.",
        "Index price series, no dividends on either side.",
    ]
    perf = metrics.compute(equity=eq, positions_open=n_open, trades=tdf, max_open_positions=1,
                           costs_paid=costs, bench_close=bc, cash=csh, notes=notes)
    for k, v in metrics.benchmark_stats(bc).items():
        setattr(perf, k, v)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"
    name = f"{a.start}_{a.strategy}_{a.cost_bps:g}bps_{cls.spec_id()}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": n_open,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 1))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — {cls.name}, {a.start} onward", perf, eq, n_open, tdf, cfg.currency_symbol, 1, bc,
            f"python3 -m swing_screener.backtesting.index_timing --strategy {a.strategy} --market {a.market} "
            f"--start {a.start}" + (f" --cost-bps {a.cost_bps:g}" if a.cost_bps != cls.cost_bps else ""))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


#: the strategies this runner backtests (each class carries its `effect` and that rule's settings)
HELD_RULES = ("turn_of_month", "pre_holiday", "ibs_reversion")


if __name__ == "__main__":
    main()
