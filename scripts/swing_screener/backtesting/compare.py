"""Backtest several strategies on one window and compare them side by side.

`backtest.py` runs one strategy per invocation and writes its own report, which
is right for depth and useless for the question that actually matters: is this
strategy better than the alternatives, and better than doing nothing? This runs
each in turn, overlays their equity curves on one axis, and ranks them on
excess CAGR against the same benchmark.

    python3 -m swing_screener.backtesting.compare --market us --start 2013-01-01 \\
        --strategies all --sample 500

Each strategy still writes its own detailed run directory; this adds a
comparison on top. Signals are cached per strategy in Postgres, so re-running a
comparison after the first pass is fast.
"""

import argparse
import logging
from pathlib import Path

import pandas as pd

from ..core import charts
from ..core.charts import AXIS, INK_2, MUTED, SURFACE
from ..config import MARKETS
from ..marketdata import cache
from ..paths import REPORTS_DIR
from ..strategies import list_strategies
from . import metrics
from .backtest import run_portfolio_backtest

logger = logging.getLogger("compare")

# categorical slots, assigned in fixed order and never cycled
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"]


def _chart_equity_overlay(
    curves: dict[str, pd.Series], bench: pd.Series | None, out: Path, currency: str
) -> Path:
    """Every strategy plus the benchmark on ONE axis, all rebased to the same
    starting capital — never a second y-scale."""
    charts._style()
    fig, ax = charts.plt.subplots(figsize=(9.5, 4.6))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)

    base = next(iter(curves.values())).iloc[0] if curves else 100.0
    if bench is not None and len(bench.dropna()) > 1:
        b = bench.dropna()
        reb = b / b.iloc[0] * float(base)
        ax.plot(reb.index, reb.values, color=MUTED, linewidth=1.6, zorder=2,
                label="Benchmark (buy & hold)")
        ax.annotate(f"{currency}{reb.iloc[-1]:,.0f}", xy=(reb.index[-1], reb.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", color=MUTED,
                    fontsize=8.5, va="center", weight="bold")
    for i, (name, eq) in enumerate(curves.items()):
        colour = SERIES[i % len(SERIES)]
        ax.plot(eq.index, eq.values, color=colour, zorder=3, label=name)
        ax.annotate(f"{currency}{eq.iloc[-1]:,.0f}", xy=(eq.index[-1], eq.iloc[-1]),
                    xytext=(6, 0), textcoords="offset points", color=colour,
                    fontsize=8.5, va="center", weight="bold")

    ax.axhline(float(base), color=AXIS, linewidth=0.8, zorder=1)
    ax.yaxis.set_major_formatter(
        charts.matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}")
    )
    ax.set_ylabel(f"Equity ({currency})")
    ax.set_title("Equity curves — same window, same capital, same costs")
    ax.legend(loc="upper left", labelcolor=INK_2)
    ax.margins(x=0.08)
    return charts._save(fig, out)


def _chart_drawdowns(curves: dict[str, pd.Series], out: Path) -> Path:
    """Drawdown is the number that decides whether a strategy is holdable."""
    charts._style()
    fig, ax = charts.plt.subplots(figsize=(9.5, 2.8))
    ax.grid(True, axis="y", zorder=0)
    ax.set_axisbelow(True)
    for i, (name, eq) in enumerate(curves.items()):
        dd = metrics.drawdown_series(eq) * 100
        ax.plot(dd.index, dd.values, color=SERIES[i % len(SERIES)], linewidth=1.4,
                zorder=3, label=name)
    ax.set_ylabel("Drawdown (%)")
    ax.set_title("Drawdown from prior peak")
    ax.legend(loc="lower left", labelcolor=INK_2)
    ax.margins(x=0.08)
    return charts._save(fig, out)


def run(
    market: str, start: str, strategy_keys: list[str], sample: int | None = None,
    max_positions: int | None = None, accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
) -> Path:
    cfg = MARKETS[market]
    results: dict[str, tuple] = {}
    failures: dict[str, str] = {}

    for key in strategy_keys:
        logger.info("=== backtesting %s ===", key)
        try:
            tdf, perf, result = run_portfolio_backtest(
                market, start, strategy_key=key, sample=sample,
                max_positions=max_positions, accept_labels=accept_labels,
            )
            results[key] = (tdf, perf, result)
        except Exception as e:
            logger.exception("%s failed", key)
            failures[key] = f"{type(e).__name__}: {e}"

    if not results:
        raise RuntimeError(f"every strategy failed: {failures}")

    out_dir = REPORTS_DIR / "comparisons" / f"{market}_{start}"
    figs = out_dir / "figures"
    curves = {k: r[2].equity for k, r in results.items()}
    bench_raw = cache.load_cached(market, cfg.benchmark_ticker)
    first_eq = next(iter(curves.values()))
    bench = (bench_raw["close"].reindex(first_eq.index).ffill()
             if bench_raw is not None and not bench_raw.empty else None)

    f_eq = _chart_equity_overlay(curves, bench, figs / "equity.png", cfg.currency_symbol)
    f_dd = _chart_drawdowns(curves, figs / "drawdown.png")

    L: list[str] = [f"# Strategy comparison — {cfg.name}", ""]
    L.append(f"*{start} onward · {len(results)} strategies · "
             f"{'full universe' if not sample else f'{sample}-symbol seeded sample'}*")
    L.append("")
    if failures:
        L.append("> **Some strategies failed to run.**")
        for k, msg in failures.items():
            L.append(f"> - `{k}`: {msg}")
        L.append("")

    # ranked on excess CAGR — the only column that answers "is this worth running"
    rows = []
    for key, (tdf, perf, _) in results.items():
        rows.append({
            "strategy": key,
            "CAGR%": round(perf.cagr_pct, 2),
            "maxDD%": round(perf.max_drawdown_pct, 1),
            "Sharpe": round(perf.sharpe, 2),
            "Sortino": round(perf.sortino, 2),
            "Calmar": round(perf.calmar, 2),
            "excess%": (round(perf.cagr_pct - perf.benchmark_cagr_pct, 2)
                        if perf.benchmark_cagr_pct is not None else None),
            "expo%": round(perf.exposure_pct, 0),
            "trades": perf.trades,
            "win%": round(perf.win_rate_pct, 1),
            "PF": round(perf.profit_factor, 2),
        })
    df = pd.DataFrame(rows).sort_values("excess%", ascending=False, na_position="last")

    L.append("| strategy | CAGR% | maxDD% | Sharpe | Sortino | Calmar | excess% | expo% | trades | win% | PF |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for _, r in df.iterrows():
        L.append(
            f"| **{r['strategy']}** | {r['CAGR%']} | {r['maxDD%']} | {r['Sharpe']} "
            f"| {r['Sortino']} | {r['Calmar']} | {r['excess%']} | {r['expo%']:.0f} "
            f"| {r['trades']} | {r['win%']} | {r['PF']} |"
        )
    any_perf = next(iter(results.values()))[1]
    if any_perf.benchmark_cagr_pct is not None:
        L.append(f"| _{cfg.benchmark_symbol} buy & hold_ | {any_perf.benchmark_cagr_pct:.2f} "
                 f"| {any_perf.benchmark_max_dd_pct:.1f} | {any_perf.benchmark_sharpe:.2f} "
                 f"| — | {abs(any_perf.benchmark_cagr_pct / any_perf.benchmark_max_dd_pct):.3f} "
                 f"| — | 100 | — | — | — |")
    L.append("")
    L.append("`excess%` is CAGR minus the benchmark's. A strategy that raises CAGR "
             "while raising drawdown by more has not improved anything — read "
             "Calmar alongside it.")
    L.append("")

    L.append("## Equity curves")
    L.append("")
    L.append(f"![Equity curve per strategy against the benchmark](figures/{f_eq.name})")
    L.append("")
    L.append(f"![Drawdown per strategy](figures/{f_dd.name})")
    L.append("")

    L.append("## Per-strategy detail")
    L.append("")
    for key in results:
        L.append(f"- `{key}` — see its own run directory under "
                 f"`reports/{market}/{key}/`")
    L.append("")

    if any_perf.notes:
        L.append("## Caveats")
        L.append("")
        for n in any_perf.notes:
            L.append(f"- {n}")
        L.append("")

    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "report.md"
    md.write_text("\n".join(L))
    df.to_csv(out_dir / "comparison.csv", index=False)
    logger.info("Comparison: %s", md)
    print()
    print(df.to_string(index=False))
    print(f"\nComparison -> {md}")
    return md


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Backtest several strategies and compare")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--strategies", default="all",
                    help="comma-separated, or 'all'. Available: " + ",".join(list_strategies()))
    ap.add_argument("--sample", type=int, default=None,
                    help="seeded random subset of N candidates (same subset per strategy)")
    ap.add_argument("--max-positions", type=int, default=None)
    ap.add_argument("--accept-labels", default="TRADE - HIGH CONFIDENCE")
    args = ap.parse_args()

    keys = (list_strategies() if args.strategies.strip() == "all"
            else [k.strip() for k in args.strategies.split(",") if k.strip()])
    for k in keys:
        if k not in list_strategies():
            ap.error(f"unknown strategy '{k}', choose from {list_strategies()}")

    run(args.market, args.start, keys, sample=args.sample,
        max_positions=args.max_positions,
        accept_labels=tuple(x.strip() for x in args.accept_labels.split(",") if x.strip()))


if __name__ == "__main__":
    main()
