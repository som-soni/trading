"""Markdown backtest reports with charts.

A terminal summary scrolls away and an ASCII curve can't show you the shape of
a four-year drawdown. This renders the same `Performance` object plus the trade
list into a markdown file with PNG charts beside it, so a run can be read,
diffed in git, and shared.

    # render from a completed run's CSVs (no re-run needed)
    python3 -m swing_screener.backtesting.report --list
    python3 -m swing_screener.backtesting.report \\
        --market india --strategy momentum_baseline --run 2013-01-01_top20_mom252_ME_25bps

`backtest.py` and `baseline.py` call `write_report` directly at the end of a
run, so a fresh run produces its markdown automatically.

Chart conventions follow one palette, applied by the job each colour does:
two categorical hues for the strategy-vs-benchmark identity comparison, and a
diverging blue/red pair wherever the data has a sign (annual returns, R
distribution). Grid and axes are recessive hairlines; marks are thin; only
endpoints carry direct labels. The palette is validated for colour-vision
deficiency rather than eyeballed.
"""

import argparse
import logging
from dataclasses import asdict
from pathlib import Path

import matplotlib.ticker
import matplotlib.pyplot as plt
import pandas as pd

from ..marketdata import cache

from . import metrics  # noqa: E402
from ..config import MARKETS  # noqa: E402

logger = logging.getLogger("report")

from ..paths import REPORTS_DIR as REPORT_DIR, run_dir  # noqa: F401

from ..core.charts import (  # noqa: F401
    SURFACE, INK, INK_2, MUTED, GRID, AXIS,
    SERIES_STRATEGY, SERIES_BENCHMARK, POS, NEG, NEUTRAL,
    _style, _save,
)



def _money(v: float, sym: str) -> str:
    return f"{sym}{v:,.0f}"


# ---------------------------------------------------------------- charts


def chart_equity(
    equity: pd.Series, bench_close: pd.Series | None, out: Path, currency: str
) -> Path:
    """Strategy vs benchmark, both in account currency on ONE axis.

    The benchmark is rebased to the strategy's starting equity so the two are
    directly comparable — never a second y-scale."""
    _style()
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)

    ax.plot(equity.index, equity.values, color=SERIES_STRATEGY,
            label="Strategy", zorder=3)
    series = [("Strategy", equity, SERIES_STRATEGY)]
    if bench_close is not None and len(bench_close.dropna()) > 1:
        b = bench_close.dropna()
        rebased = b / b.iloc[0] * float(equity.iloc[0])
        ax.plot(rebased.index, rebased.values, color=SERIES_BENCHMARK,
                label="Benchmark (buy & hold)", zorder=2)
        series.append(("Benchmark", rebased, SERIES_BENCHMARK))

    # direct-label the endpoints only — never a number on every point
    for name, s, colour in series:
        ax.annotate(
            _money(float(s.iloc[-1]), currency),
            xy=(s.index[-1], float(s.iloc[-1])),
            xytext=(6, 0), textcoords="offset points",
            color=colour, fontsize=8.5, va="center", weight="bold",
        )

    ax.axhline(float(equity.iloc[0]), color=AXIS, linewidth=0.8, zorder=1)
    ax.yaxis.set_major_formatter(
        matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
    )
    ax.set_ylabel(f"Equity ({currency})")
    ax.set_title("Equity curve")
    if len(series) > 1:
        ax.legend(loc="upper left", labelcolor=INK_2)
    ax.margins(x=0.06)
    return _save(fig, out)


def chart_drawdown(equity: pd.Series, out: Path) -> Path:
    """Depth below the running peak. One series, so no legend — the title names it."""
    _style()
    dd = metrics.drawdown_series(equity) * 100
    fig, ax = plt.subplots(figsize=(9, 2.4))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)
    ax.fill_between(dd.index, dd.values, 0, color=NEG, alpha=0.18, linewidth=0, zorder=2)
    ax.plot(dd.index, dd.values, color=NEG, linewidth=1.4, zorder=3)
    worst = float(dd.min())
    worst_at = dd.idxmin()
    ax.annotate(
        f"{worst:.1f}%", xy=(worst_at, worst), xytext=(6, 4),
        textcoords="offset points", color=NEG, fontsize=8.5, weight="bold",
    )
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown from prior peak")
    ax.margins(x=0.06)
    return _save(fig, out)


def chart_annual_returns(
    equity: pd.Series, bench_close: pd.Series | None, out: Path
) -> Path:
    """Calendar-year returns. The data has a sign, so the colour is diverging:
    cool arm for gains, warm for losses, with a neutral zero rule."""
    _style()
    yr_end = equity.resample("YE").last()
    start = pd.Series([float(equity.iloc[0])], index=[equity.index[0]])
    strat = pd.concat([start, yr_end]).pct_change().dropna() * 100
    strat.index = [d.year for d in strat.index]

    bench = None
    if bench_close is not None and len(bench_close.dropna()) > 1:
        b = bench_close.dropna()
        b_end = b.resample("YE").last()
        b0 = pd.Series([float(b.iloc[0])], index=[b.index[0]])
        bench = pd.concat([b0, b_end]).pct_change().dropna() * 100
        bench.index = [d.year for d in bench.index]
        bench = bench.reindex(strat.index)

    fig, ax = plt.subplots(figsize=(9, 3.4))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)
    x = range(len(strat))
    width = 0.38 if bench is not None else 0.62

    # Identity encoding, NOT diverging: this chart compares two entities, and
    # each keeps the colour it has in the equity chart. Colouring the strategy
    # bars by sign instead would put two colour jobs in one chart and
    # contradict its own legend — the sign is already carried by the zero rule.
    if bench is not None:
        ax.bar([i - width / 2 for i in x], strat.values, width=width,
               color=SERIES_STRATEGY, edgecolor=SURFACE, linewidth=1.2,
               zorder=3, label="Strategy")
        ax.bar([i + width / 2 for i in x], bench.values, width=width,
               color=SERIES_BENCHMARK, edgecolor=SURFACE, linewidth=1.2,
               zorder=2, label="Benchmark")
        ax.legend(loc="lower left", labelcolor=INK_2)
    else:
        # single entity: now sign IS the message, so diverging is correct
        ax.bar(list(x), strat.values, width=width,
               color=[POS if v >= 0 else NEG for v in strat.values],
               edgecolor=SURFACE, linewidth=1.2, zorder=3)
    ax.axhline(0, color=AXIS, linewidth=0.9, zorder=4)
    ax.set_xticks(list(x))
    ax.set_xticklabels([str(y) for y in strat.index], rotation=0)
    ax.set_ylabel("Return (%)")
    ax.set_title("Calendar-year returns")
    return _save(fig, out)


def chart_r_distribution(trades: pd.DataFrame, out: Path) -> Path:
    """Where the outcomes actually land. Diverging again — losses vs gains."""
    _style()
    r = pd.to_numeric(trades.get("r_multiple"), errors="coerce").dropna()
    if r.empty:
        return None
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)
    lo, hi = float(r.min()), float(r.max())
    bins = pd.interval_range(start=min(lo, -2), end=max(hi, 3), freq=0.5)
    counts, edges = pd.cut(r, bins=[b.left for b in bins] + [bins[-1].right],
                           include_lowest=True).value_counts().sort_index(), None
    centres = [iv.mid for iv in counts.index]
    colours = [POS if c >= 0 else NEG for c in centres]
    ax.bar(centres, counts.values, width=0.44, color=colours,
           edgecolor=SURFACE, linewidth=1.0, zorder=3)
    ax.axvline(0, color=AXIS, linewidth=0.9, zorder=4)
    ax.set_xlabel("R-multiple (realised / risk at entry)")
    ax.set_ylabel("Trades")
    ax.set_title("Outcome distribution")
    return _save(fig, out)


def chart_exposure(positions: pd.Series, out: Path, cap: int) -> Path:
    """How much of the account was actually working. A strategy at 56% exposure
    against a compounding index is handicapped before any trade is judged."""
    _style()
    fig, ax = plt.subplots(figsize=(9, 2.2))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)
    ax.fill_between(positions.index, positions.values, 0,
                    color=SERIES_STRATEGY, alpha=0.18, linewidth=0, zorder=2)
    ax.plot(positions.index, positions.values, color=SERIES_STRATEGY,
            linewidth=1.2, zorder=3)
    if cap:
        ax.axhline(cap, color=AXIS, linewidth=0.9, zorder=1)
        ax.annotate(f"cap {cap}", xy=(positions.index[0], cap), xytext=(2, 3),
                    textcoords="offset points", color=MUTED, fontsize=8)
    ax.set_ylabel("Open positions")
    ax.set_title("Positions held")
    ax.margins(x=0.06)
    return _save(fig, out)


# ---------------------------------------------------------------- markdown


def _verdict(p: metrics.Performance) -> str:
    if p.benchmark_cagr_pct is None:
        return "No benchmark available for this market, so there is no comparison to doing nothing."
    excess = p.cagr_pct - p.benchmark_cagr_pct
    dd_better = p.max_drawdown_pct > p.benchmark_max_dd_pct  # both negative
    if excess > 0 and (p.sharpe or 0) > (p.benchmark_sharpe or 0):
        return (
            f"**Beat the benchmark on both return and risk-adjusted return** "
            f"({excess:+.2f}% excess CAGR, Sharpe {p.sharpe:.2f} vs {p.benchmark_sharpe:.2f})."
        )
    if excess > 0:
        return (
            f"**Beat the benchmark on return but not risk-adjusted** "
            f"({excess:+.2f}% excess CAGR, Sharpe {p.sharpe:.2f} vs {p.benchmark_sharpe:.2f}"
            f"{', though drawdown was shallower' if dd_better else ''})."
        )
    return (
        f"**Did not beat buy-and-hold** ({excess:+.2f}% excess CAGR). "
        + (
            f"Drawdown was shallower than the benchmark "
            f"({p.max_drawdown_pct:.1f}% vs {p.benchmark_max_dd_pct:.1f}%), so the "
            "gates reduced risk — they also reduced return by more."
            if dd_better else
            f"Drawdown was also worse ({p.max_drawdown_pct:.1f}% vs "
            f"{p.benchmark_max_dd_pct:.1f}%)."
        )
    )


def _fmt(x, nd=2, suffix=""):
    if x is None or x != x:
        return "n/a"
    return f"{x:,.{nd}f}{suffix}"


def write_report(
    out_dir: Path,
    title: str,
    perf: metrics.Performance,
    equity: pd.Series,
    positions: pd.Series,
    trades: pd.DataFrame,
    currency: str,
    cap: int,
    bench_close: pd.Series | None = None,
    command: str = "",
    extra_sections: list[tuple[str, str]] | None = None,
) -> Path:
    """Render one run to markdown with charts. Returns the .md path."""
    # one directory per run: report.md, trades.csv, equity.csv and figures/
    # together, so a run's artefacts are found by browsing rather than grepping
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_md = out_dir / "report.md"
    figs = out_dir / "figures"
    rel = lambda p: f"figures/{p.name}"  # noqa: E731

    f_eq = chart_equity(equity, bench_close, figs / "equity.png", currency)
    f_dd = chart_drawdown(equity, figs / "drawdown.png")
    f_yr = chart_annual_returns(equity, bench_close, figs / "annual_returns.png")
    f_rd = chart_r_distribution(trades, figs / "r_distribution.png")
    f_ex = chart_exposure(positions, figs / "exposure.png", cap) if len(positions) else None

    L: list[str] = []
    L.append(f"# {title}")
    L.append("")
    L.append(f"*{perf.start.date()} → {perf.end.date()} · {perf.years:.2f} years*")
    L.append("")
    L.append(_verdict(perf))
    L.append("")

    # headline numbers as a table, not a chart — the numbers ARE the chart here
    L.append("## Headline")
    L.append("")
    L.append("| | Strategy | Benchmark (buy & hold) |")
    L.append("|---|---|---|")
    bm = lambda v, nd=2, s="": (_fmt(v, nd, s) if v is not None else "—")  # noqa: E731
    L.append(f"| Equity | {_money(perf.starting_equity, currency)} → "
             f"**{_money(perf.ending_equity, currency)}** | — |")
    L.append(f"| Total return | **{_fmt(perf.total_return_pct, 2, '%')}** | "
             f"{bm(perf.benchmark_return_pct, 2, '%')} |")
    L.append(f"| CAGR | **{_fmt(perf.cagr_pct, 2, '%')}** | {bm(perf.benchmark_cagr_pct, 2, '%')} |")
    L.append(f"| Max drawdown | {_fmt(perf.max_drawdown_pct, 2, '%')} | "
             f"{bm(perf.benchmark_max_dd_pct, 2, '%')} |")
    L.append(f"| Sharpe | {_fmt(perf.sharpe)} | {bm(perf.benchmark_sharpe)} |")
    L.append(f"| Sortino | {_fmt(perf.sortino)} | — |")
    L.append(f"| Calmar | {_fmt(perf.calmar)} | "
             + (f"{abs(perf.benchmark_cagr_pct / perf.benchmark_max_dd_pct):.3f} |"
                if perf.benchmark_cagr_pct is not None and perf.benchmark_max_dd_pct else "— |"))
    L.append(f"| Exposure | {_fmt(perf.exposure_pct, 1, '%')} of days | 100% |")
    if perf.benchmark_cagr_pct is not None:
        L.append(f"| **Excess CAGR** | **{_fmt(perf.cagr_pct - perf.benchmark_cagr_pct, 2, '%')}** | — |")
    L.append("")
    L.append(f"Longest stretch below a prior peak: **{perf.max_drawdown_days} days**. "
             f"Annualised volatility {_fmt(perf.ann_volatility_pct, 2, '%')}. "
             f"Turnover {_fmt(perf.turnover_annual)}× of average equity per year. "
             f"Costs paid {_money(perf.costs_paid, currency)}.")
    L.append("")

    L.append("## Equity curve")
    L.append("")
    L.append(f"![Equity curve: strategy versus buy-and-hold benchmark]({rel(f_eq)})")
    L.append("")
    L.append(f"![Drawdown from prior peak]({rel(f_dd)})")
    L.append("")

    L.append("## Returns by year")
    L.append("")
    L.append(f"![Calendar-year returns, strategy versus benchmark]({rel(f_yr)})")
    L.append("")

    # trade statistics
    L.append("## Trades")
    L.append("")
    L.append(f"| | |")
    L.append("|---|---|")
    L.append(f"| Trades | {perf.trades} |")
    L.append(f"| Win rate | {_fmt(perf.win_rate_pct, 1, '%')} |")
    L.append(f"| Avg R per trade | {_fmt(perf.avg_r, 3)} |")
    L.append(f"| Profit factor | {_fmt(perf.profit_factor)} |")
    L.append(f"| Avg positions held | {_fmt(perf.avg_positions, 1)} (peak {perf.max_positions}, cap {cap}) |")
    L.append("")
    if f_rd is not None:
        L.append(f"![Distribution of realised R-multiples]({rel(f_rd)})")
        L.append("")
    if f_ex is not None:
        L.append(f"![Open positions over time against the position cap]({rel(f_ex)})")
        L.append("")

    if len(trades) and "exit_reason" in trades:
        L.append("### By exit reason")
        L.append("")
        g = trades.groupby("exit_reason").agg(
            trades=("pnl", "size"), total_pnl=("pnl", "sum"),
            avg_R=("r_multiple", "mean"), median_days=("holding_days", "median"),
        ).round(2).sort_values("trades", ascending=False)
        L.append("| exit | trades | total P&L | avg R | median days |")
        L.append("|---|---|---|---|---|")
        for reason, row in g.iterrows():
            L.append(f"| {reason} | {int(row.trades)} | {_money(row.total_pnl, currency)} "
                     f"| {row.avg_R:+.2f} | {row.median_days:.0f} |")
        L.append("")

        for label, frame, asc in [("Best", trades.nlargest(10, "pnl"), False),
                                  ("Worst", trades.nsmallest(10, "pnl"), True)]:
            L.append(f"### {label} 10 trades")
            L.append("")
            L.append("| symbol | entry | exit | reason | P&L | R | days |")
            L.append("|---|---|---|---|---|---|---|")
            for _, t in frame.iterrows():
                L.append(
                    f"| {t.get('symbol','')} | {t.get('entry_date','')} | {t.get('exit_date','')} "
                    f"| {t.get('exit_reason','')} | {_money(float(t.get('pnl', 0)), currency)} "
                    f"| {float(t.get('r_multiple', float('nan'))):+.2f} | {t.get('holding_days','')} |"
                )
            L.append("")

    for heading, body in (extra_sections or []):
        L.append(f"## {heading}")
        L.append("")
        L.append(body)
        L.append("")

    if perf.notes:
        L.append("## Caveats")
        L.append("")
        for n in perf.notes:
            L.append(f"- {n}")
        L.append("")

    if command:
        L.append("## Reproduce")
        L.append("")
        L.append("```bash")
        L.append(command)
        L.append("```")
        L.append("")

    out_md.write_text("\n".join(L))
    logger.info("wrote %s", out_md)
    return out_md


# ------------------------------------------------- rebuild from saved CSVs


def from_saved(
    market: str, strategy: str, run: str, cap: int | None = None,
    command: str = "", title: str | None = None,
) -> Path:
    """Render a report for a run that already happened.

    Rebuilds the `Performance` object from the trades.csv / equity.csv a
    previous run wrote into its own directory, so a finished backtest can be
    turned into a report without paying for the simulation again."""
    cfg = MARKETS[market]
    d = run_dir(market, strategy, run, create=False)
    eq_path, tr_path = d / "equity.csv", d / "trades.csv"
    if not eq_path.exists():
        raise FileNotFoundError(eq_path)
    if not tr_path.exists():
        raise FileNotFoundError(tr_path)

    eq_df = pd.read_csv(eq_path, index_col=0, parse_dates=True)
    equity = eq_df["equity"].dropna()
    positions = (
        eq_df["positions_open"] if "positions_open" in eq_df else pd.Series(dtype=float)
    )
    trades = pd.read_csv(tr_path)
    costs = float(trades["costs"].sum()) if "costs" in trades else 0.0

    bench_raw = cache.load_cached(market, cfg.benchmark_ticker)
    bench_close = (
        bench_raw["close"].reindex(equity.index).ffill()
        if bench_raw is not None and not bench_raw.empty else None
    )
    effective_cap = cap or (int(positions.max()) if len(positions) else 0)

    notes = [
        "SURVIVORSHIP BIAS: the universe is today's listed names, so companies "
        "delisted or acquired during the window are absent entirely. This flatters "
        "results and cannot be fixed without point-in-time constituent data.",
        "Dividends are excluded on both the strategy and the benchmark, so absolute "
        "returns understate reality for each.",
        "Rendered from a previous run's saved CSVs; the simulation was not re-run.",
    ]
    perf = metrics.compute(
        equity=equity, positions_open=positions, trades=trades,
        max_open_positions=effective_cap, costs_paid=costs,
        bench_close=bench_close, notes=notes,
    )
    nice = title or f"{cfg.name} — {strategy} — {run}"
    return write_report(
        d, nice, perf, equity, positions, trades,
        cfg.currency_symbol, effective_cap, bench_close, command,
    )


def list_runs() -> list[tuple[str, str, str]]:
    """(market, strategy, run) for every directory holding a complete run."""
    out = []
    for eq in REPORT_DIR.glob("*/*/*/equity.csv"):
        d = eq.parent
        if (d / "trades.csv").exists():
            out.append((d.parent.parent.name, d.parent.name, d.name))
    return sorted(out)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Render a backtest run as markdown with charts")
    ap.add_argument("--market", choices=list(MARKETS.keys()))
    ap.add_argument("--strategy", help="strategy directory name, e.g. trend_pullback")
    ap.add_argument("--run", help="run directory name, e.g. 2013-01-01_bracket-withTarget")
    ap.add_argument("--all", action="store_true", help="render every run found")
    ap.add_argument("--list", action="store_true", help="list renderable runs and exit")
    ap.add_argument("--cap", type=int, default=None)
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    if args.list:
        for m, s_, r in list_runs():
            print(f"  --market {m} --strategy {s_} --run {r}")
        return
    if args.all:
        for m, s_, r in list_runs():
            try:
                print("->", from_saved(m, s_, r))
            except Exception as e:
                print(f"  skipped {m}/{s_}/{r}: {type(e).__name__}: {e}")
        return
    if not (args.market and args.strategy and args.run):
        ap.error("need --market, --strategy and --run (or --all / --list)")
    print("->", from_saved(args.market, args.strategy, args.run,
                           cap=args.cap, title=args.title))


if __name__ == "__main__":
    main()
