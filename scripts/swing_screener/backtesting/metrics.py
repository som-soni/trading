"""Performance statistics computed from a daily equity curve.

A trade blotter with a win rate says almost nothing about whether a system
is worth running: it ignores how much capital was tied up to earn the
return, how much drawdown you had to sit through, and whether simply
holding the index would have done better. These are the figures an equity
backtest is normally judged on.

Everything here is derived from the equity curve plus the trade list, so it
applies to any strategy that produces those two things.
"""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass
class Performance:
    start: pd.Timestamp
    end: pd.Timestamp
    years: float
    starting_equity: float
    ending_equity: float
    total_return_pct: float
    cagr_pct: float
    max_drawdown_pct: float
    max_drawdown_days: int
    ann_volatility_pct: float
    sharpe: float
    sortino: float
    calmar: float
    exposure_pct: float
    avg_positions: float
    max_positions: int
    turnover_annual: float
    trades: int
    win_rate_pct: float
    avg_r: float
    profit_factor: float
    expectancy_r: float
    costs_paid: float
    benchmark_return_pct: float | None = None
    benchmark_cagr_pct: float | None = None
    benchmark_max_dd_pct: float | None = None
    benchmark_sharpe: float | None = None
    notes: list[str] = field(default_factory=list)


def drawdown_series(equity: pd.Series) -> pd.Series:
    return equity / equity.cummax() - 1.0


def max_drawdown(equity: pd.Series) -> tuple[float, int]:
    """Worst peak-to-trough decline, and the longest stretch spent below a
    prior peak (the part that actually tests whether you'd keep going)."""
    if equity.empty:
        return 0.0, 0
    dd = drawdown_series(equity)
    worst = float(dd.min()) * 100

    under = dd < -1e-12
    longest = run = 0
    for flag in under:
        run = run + 1 if flag else 0
        longest = max(longest, run)
    return worst, longest


def _annualised(daily_returns: pd.Series) -> tuple[float, float, float]:
    """(ann. volatility %, Sharpe, Sortino) at a 0% risk-free rate.

    Sortino uses downside deviation about zero; if there are no down days
    it is undefined rather than infinite, so NaN is returned."""
    r = daily_returns.dropna()
    if len(r) < 2:
        return float("nan"), float("nan"), float("nan")
    sd = float(r.std(ddof=1))
    ann_vol = sd * np.sqrt(TRADING_DAYS) * 100
    mean = float(r.mean())
    sharpe = (mean / sd) * np.sqrt(TRADING_DAYS) if sd > 0 else float("nan")
    downside = r[r < 0]
    dsd = float(np.sqrt((downside**2).mean())) if len(downside) else float("nan")
    sortino = (mean / dsd) * np.sqrt(TRADING_DAYS) if dsd and dsd == dsd else float("nan")
    return ann_vol, sharpe, sortino


def benchmark_stats(bench_close: pd.Series) -> dict:
    """Buy-and-hold stats for the benchmark over the same dates, so the
    strategy is judged against the alternative of doing nothing."""
    b = bench_close.dropna()
    if len(b) < 2:
        return {}
    years = max((b.index[-1] - b.index[0]).days / 365.25, 1e-9)
    total = (b.iloc[-1] / b.iloc[0] - 1) * 100
    cagr = ((b.iloc[-1] / b.iloc[0]) ** (1 / years) - 1) * 100
    dd, _ = max_drawdown(b)
    _, sharpe, _ = _annualised(b.pct_change())
    return {
        "benchmark_return_pct": float(total),
        "benchmark_cagr_pct": float(cagr),
        "benchmark_max_dd_pct": float(dd),
        "benchmark_sharpe": float(sharpe),
    }


def compute(
    equity: pd.Series,
    positions_open: pd.Series,
    trades: pd.DataFrame,
    max_open_positions: int,
    costs_paid: float = 0.0,
    bench_close: pd.Series | None = None,
    notes: list[str] | None = None,
) -> Performance:
    """`equity` and `positions_open` are daily series on the same index.
    `trades` needs r_multiple, pnl and notional columns."""
    equity = equity.dropna()
    if equity.empty:
        raise ValueError("empty equity curve")

    years = max((equity.index[-1] - equity.index[0]).days / 365.25, 1e-9)
    total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
    cagr = ((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) * 100
    dd, dd_days = max_drawdown(equity)
    ann_vol, sharpe, sortino = _annualised(equity.pct_change())
    calmar = (cagr / abs(dd)) if dd else float("nan")

    # Exposure: share of days holding anything, which is what makes a
    # return comparable to buy-and-hold's 100% exposure.
    exposure = float((positions_open > 0).mean()) * 100 if len(positions_open) else float("nan")

    # Turnover: capital deployed per year relative to average equity.
    notional = float(trades["notional"].sum()) if "notional" in trades and len(trades) else 0.0
    turnover = (notional / years) / float(equity.mean()) if len(equity) else float("nan")

    closed = trades[trades["exit_reason"] != "OPEN"] if len(trades) else trades
    if len(closed):
        wins = closed[closed["pnl"] > 0]["pnl"].sum()
        losses = -closed[closed["pnl"] < 0]["pnl"].sum()
        pf = float(wins / losses) if losses > 0 else float("inf")
        # keyed off realised P&L: R can be undefined for policies that move
        # the stop, and a NaN R would silently count as a loss
        win_rate = float((closed["pnl"] > 0).mean()) * 100
        avg_r = float(closed["r_multiple"].mean())
    else:
        pf, win_rate, avg_r = float("nan"), float("nan"), float("nan")

    perf = Performance(
        start=equity.index[0], end=equity.index[-1], years=years,
        starting_equity=float(equity.iloc[0]), ending_equity=float(equity.iloc[-1]),
        total_return_pct=float(total_return), cagr_pct=float(cagr),
        max_drawdown_pct=float(dd), max_drawdown_days=int(dd_days),
        ann_volatility_pct=float(ann_vol), sharpe=float(sharpe), sortino=float(sortino),
        calmar=float(calmar), exposure_pct=exposure,
        avg_positions=float(positions_open.mean()) if len(positions_open) else float("nan"),
        max_positions=int(positions_open.max()) if len(positions_open) else 0,
        turnover_annual=float(turnover), trades=int(len(trades)),
        win_rate_pct=win_rate, avg_r=avg_r, profit_factor=pf, expectancy_r=avg_r,
        costs_paid=float(costs_paid), notes=list(notes or []),
    )
    if bench_close is not None:
        for k, v in benchmark_stats(bench_close).items():
            setattr(perf, k, v)
    return perf


def format_report(p: Performance, currency: str, cap: int) -> str:
    def f(x, nd=2):
        return "n/a" if x != x else f"{x:,.{nd}f}"

    lines = [
        "=" * 68,
        "PORTFOLIO PERFORMANCE",
        "=" * 68,
        f"Period            {p.start.date()} -> {p.end.date()}  ({p.years:.2f} years)",
        f"Equity            {currency}{p.starting_equity:,.0f} -> {currency}{p.ending_equity:,.0f}",
        f"Total return      {f(p.total_return_pct)}%",
        f"CAGR              {f(p.cagr_pct)}%",
        "",
        f"Max drawdown      {f(p.max_drawdown_pct)}%   (longest {p.max_drawdown_days} days below a prior peak)",
        f"Ann. volatility   {f(p.ann_volatility_pct)}%",
        f"Sharpe            {f(p.sharpe)}        (0% risk-free)",
        f"Sortino           {f(p.sortino)}",
        f"Calmar            {f(p.calmar)}",
        "",
        f"Exposure          {f(p.exposure_pct,1)}% of days holding at least one position",
        f"Positions         avg {f(p.avg_positions,1)}, peak {p.max_positions} (cap {cap})",
        f"Turnover          {f(p.turnover_annual)}x of average equity per year",
        f"Costs paid        {currency}{p.costs_paid:,.2f}",
        "",
        f"Trades            {p.trades}   win rate {f(p.win_rate_pct,1)}%",
        f"Avg R / trade     {f(p.avg_r,3)}        profit factor {f(p.profit_factor)}",
    ]
    if p.benchmark_return_pct is not None:
        lines += [
            "",
            "-" * 68,
            "VS BUY-AND-HOLD BENCHMARK (same dates, 100% exposure)",
            "-" * 68,
            f"Benchmark return  {f(p.benchmark_return_pct)}%   CAGR {f(p.benchmark_cagr_pct)}%",
            f"Benchmark max DD  {f(p.benchmark_max_dd_pct)}%   Sharpe {f(p.benchmark_sharpe)}",
            f"Excess CAGR       {f(p.cagr_pct - p.benchmark_cagr_pct)}%  <- the number that decides "
            "whether this beats doing nothing",
        ]
    if p.notes:
        lines += ["", "-" * 68, "CAVEATS", "-" * 68] + [f"  * {n}" for n in p.notes]
    lines.append("=" * 68)
    return "\n".join(lines)


def format_equity_curve(
    equity: pd.Series, bench_close: pd.Series | None = None,
    width: int = 64, height: int = 15,
) -> str:
    """ASCII equity curve with the benchmark rebased to the same start, plus
    a drawdown panel beneath it.

    A terminal chart is not decoration: the shape of the curve answers
    questions a summary row cannot -- whether the return came from one lucky
    stretch, how long the flat periods ran, and whether the strategy tracked
    or diverged from simply holding the index."""
    eq = equity.dropna()
    if len(eq) < 2:
        return "(equity curve too short to plot)"

    # resample to the plot width so each column is a time bucket
    idx = pd.Series(range(len(eq)), index=eq.index)
    buckets = (idx * width // len(eq)).clip(upper=width - 1)
    strat = eq.groupby(buckets).last()

    series = {"strategy": strat}
    if bench_close is not None and len(bench_close.dropna()) > 1:
        b = bench_close.dropna()
        rebased = b / b.iloc[0] * eq.iloc[0]
        series["benchmark"] = rebased.groupby(
            (pd.Series(range(len(rebased)), index=rebased.index) * width // len(rebased))
            .clip(upper=width - 1)
        ).last()

    lo = min(float(s.min()) for s in series.values())
    hi = max(float(s.max()) for s in series.values())
    if hi <= lo:
        hi = lo + 1.0

    grid = [[" "] * width for _ in range(height)]
    marks = {"strategy": "#", "benchmark": "."}
    for name, s in series.items():
        ch = marks[name]
        for col, val in s.items():
            row = int((hi - float(val)) / (hi - lo) * (height - 1))
            row = max(0, min(height - 1, row))
            if grid[row][col] == " " or ch == "#":
                grid[row][col] = ch

    out = ["EQUITY CURVE   # strategy" + ("   . benchmark (rebased)" if len(series) > 1 else "")]
    for r, line in enumerate(grid):
        label = f"{hi - (hi - lo) * r / (height - 1):>12,.0f} |"
        out.append(label + "".join(line))
    out.append(" " * 13 + "+" + "-" * width)
    out.append(" " * 14 + f"{eq.index[0].date()}" + " " * (width - 21) + f"{eq.index[-1].date()}")

    dd = drawdown_series(eq) * 100
    dd_b = dd.groupby(buckets).min()
    dd_floor = float(dd_b.min())
    if dd_floor < -1e-9:
        dd_h = 5
        out.append("")
        out.append(f"DRAWDOWN  (worst {dd_floor:.1f}%)")
        for r in range(dd_h):
            top = dd_floor * r / dd_h
            bottom = dd_floor * (r + 1) / dd_h
            row = "".join(
                "#" if float(v) <= bottom or (float(v) <= top and float(v) > bottom) else " "
                for v in dd_b.reindex(range(width)).fillna(0)
            )
            out.append(f"{top:>12,.1f}%|" + row)
    return "\n".join(out)
