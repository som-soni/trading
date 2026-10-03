"""Markdown report for one screener run — the thing you actually read.

The pipeline's CSV has 60+ columns and one row per surviving symbol, which is
right for filtering in a spreadsheet and wrong for a morning read. This turns
the same data into: what to trade today, what to watch, what changed since the
last run, and — on the common day when nothing qualifies — *why* the whole
universe was rejected, which is the question a zero-candidate day actually
raises.

Written automatically at the end of every `pipeline.run`.
"""

import logging
from pathlib import Path

import pandas as pd

from ..core import charts
from ..core.charts import AXIS, GRID, MUTED, NEG, POS, SERIES_STRATEGY, SURFACE

logger = logging.getLogger(__name__)

# the gate vocabulary is strategy-specific; these are only for prose
GATE_MEANING = {
    "W1": "weekly close not above a rising 30-week EMA",
    "W2": "weekly SMA20 below SMA50",
    "T1": "SMA50 below SMA200, or price broke down through SMA50",
    "T2": "SMA50 or SMA200 falling",
    "T3": "no higher swing lows over ~50 bars",
    "T4": "12-1 month momentum negative",
    "T5": "more than 25% below the 52-week high",
    "T6": "3-month return negative with a flat/falling SMA50",
    "D2": "earnings within 10 trading days",
    "D3": "pullback volume exceeded impulse volume",
    "D4": "closed below the prior structural swing low",
    "D5": "overhead resistance within 3%",
    "D6": "ATR above 8% of price",
    "D7": "unheld gap over 8% in the last 10 bars",
}


def _gate_label(code: str, width: int = 40) -> str:
    """Gate code plus a short gloss, cut at a word boundary.

    A label sliced mid-word ("rising 30-wee") reads as a rendering bug rather
    than an abbreviation."""
    text = GATE_MEANING.get(code, "")
    if len(text) > width:
        text = text[:width].rsplit(" ", 1)[0] + "…"
    return f"{code}  {text}" if text else code


def _chart_gate_failures(df: pd.DataFrame, out: Path) -> Path | None:
    """Why the universe was rejected. On a zero-candidate day this is the
    only chart that answers anything."""
    col = "first_failed_gate"
    if col not in df:
        return None
    # Rows that passed every gate carry no failed-gate value. They arrive as
    # NaN/None/"" depending on whether the frame came from memory or a CSV
    # round-trip, so filter on the string form rather than trusting dropna().
    codes = df[col].astype("string").str.strip()
    codes = codes[codes.notna() & (codes != "") & (codes.str.lower() != "nan")]
    if codes.empty:
        return None
    counts = codes.value_counts().head(12).sort_values()
    charts._style()
    fig, ax = charts.plt.subplots(figsize=(7.2, max(2.4, 0.32 * len(counts) + 1)))
    ax.grid(True, axis="x", zorder=0)
    ax.set_axisbelow(True)
    ax.barh(
        [_gate_label(g) for g in counts.index],
        counts.values, height=0.62, color=SERIES_STRATEGY,
        edgecolor=SURFACE, linewidth=1.0, zorder=3,
    )
    for i, v in enumerate(counts.values):
        ax.annotate(f"{v:,}", xy=(v, i), xytext=(4, 0), textcoords="offset points",
                    va="center", color=MUTED, fontsize=8)
    ax.set_xlabel("symbols rejected")
    ax.set_title("First gate that rejected each symbol")
    return charts._save(fig, out)


def _chart_sector_mix(df: pd.DataFrame, out: Path) -> Path | None:
    """Where the surviving names sit. Concentration in one sector is a risk
    the decision column alone does not show."""
    live = df[df["decision"].isin(["TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER",
                                   "WATCH - WAIT"])]
    if live.empty or "sector" not in live:
        return None
    counts = live["sector"].fillna("Unknown").value_counts().head(12).sort_values()
    charts._style()
    fig, ax = charts.plt.subplots(figsize=(7.2, max(2.2, 0.32 * len(counts) + 1)))
    ax.grid(True, axis="x", zorder=0)
    ax.set_axisbelow(True)
    ax.barh(counts.index, counts.values, height=0.62, color=SERIES_STRATEGY,
            edgecolor=SURFACE, linewidth=1.0, zorder=3)
    for i, v in enumerate(counts.values):
        ax.annotate(f"{v}", xy=(v, i), xytext=(4, 0), textcoords="offset points",
                    va="center", color=MUTED, fontsize=8)
    ax.set_xlabel("symbols")
    ax.set_title("Surviving candidates by sector")
    return charts._save(fig, out)


def _fmt(v, nd=2):
    if v is None or (isinstance(v, float) and v != v):
        return "—"
    if isinstance(v, (int, float)):
        return f"{v:,.{nd}f}"
    return str(v)


def _table(rows: pd.DataFrame, cols: list[tuple[str, str]], currency: str) -> list[str]:
    present = [(c, h) for c, h in cols if c in rows.columns]
    out = ["| " + " | ".join(h for _, h in present) + " |",
           "|" + "---|" * len(present)]
    for _, r in rows.iterrows():
        cells = []
        for c, _ in present:
            v = r.get(c)
            if c in ("price", "entry", "stop"):
                cells.append(f"{currency}{_fmt(v)}")
            elif c in ("risk_pct", "target_r", "setup_quality", "rsi", "adx"):
                cells.append(_fmt(v))
            else:
                cells.append("—" if pd.isna(v) else str(v))
        out.append("| " + " | ".join(cells) + " |")
    return out


def write(
    out_dir: Path, market_name: str, strategy_name: str, strategy_key: str,
    report_df: pd.DataFrame, currency: str, run_id: str,
    regime_note: str = "", diff_text: str = "",
) -> Path:
    """Render one screener run. Returns the markdown path."""
    out_dir = Path(out_dir)
    figs = out_dir / "figures"
    L: list[str] = []

    tradeable = report_df[report_df.get("tradeable") == True]  # noqa: E712
    watch = report_df[report_df.get("watchlist_candidate") == True]  # noqa: E712
    counts = report_df["decision"].value_counts() if "decision" in report_df else pd.Series(dtype=int)

    L.append(f"# {market_name} — {strategy_name}")
    L.append("")
    L.append(f"*Run {run_id} · {len(report_df)} symbols surveyed*")
    L.append("")
    if regime_note:
        L.append(regime_note)
        L.append("")

    # headline
    if len(tradeable):
        L.append(f"## {len(tradeable)} tradeable candidate(s)")
    else:
        L.append("## No tradeable candidates today")
        L.append("")
        L.append(
            "That is the normal outcome, not a failure — the gate stack passes "
            "roughly 5% of symbol-days. The breakdown below shows what blocked "
            "the rest."
        )
    L.append("")

    if len(tradeable):
        L.append("### What to trade")
        L.append("")
        cols = [("symbol", "symbol"), ("sector", "sector"), ("price", "price"),
                ("strategy_setup", "setup"), ("entry", "entry"), ("stop", "stop"),
                ("risk_pct", "risk %"), ("target_r", "R"), ("shares", "shares"),
                ("decision", "decision"), ("reason", "why")]
        ranked = tradeable.sort_values(
            by=[c for c in ["decision", "setup_quality"] if c in tradeable.columns],
            ascending=[True, False][: len(
                [c for c in ["decision", "setup_quality"] if c in tradeable.columns])],
        )
        L += _table(ranked, cols, currency)
        L.append("")
        if "sector" in ranked:
            by_sec = ranked["sector"].fillna("Unknown").value_counts()
            top = by_sec.index[0]
            if by_sec.iloc[0] > max(2, len(ranked) // 2):
                L.append(
                    f"> **Concentration check:** {by_sec.iloc[0]} of {len(ranked)} "
                    f"candidates are in {top}. Sizing them equally would make this "
                    "a sector bet rather than a stock selection."
                )
                L.append("")

    if len(watch):
        L.append(f"### Watchlist — {len(watch)} name(s): trend intact, timing not yet right")
        L.append("")
        L += _table(
            watch.sort_values("setup_quality", ascending=False)
            if "setup_quality" in watch else watch,
            [("symbol", "symbol"), ("sector", "sector"), ("price", "price"),
             ("wait_for", "waiting for"), ("watch_flags_summary", "flags"),
             ("h_pct_above_close", "% to H")],
            currency,
        )
        L.append("")

    # decision mix
    if len(counts):
        L.append("## Decision mix")
        L.append("")
        L.append("| decision | symbols |")
        L.append("|---|---|")
        for k, v in counts.items():
            L.append(f"| {k} | {v} |")
        L.append("")

    # what blocked everything
    f_gate = _chart_gate_failures(report_df, figs / "gate_failures.png")
    if f_gate is not None:
        L.append("## What blocked the rest")
        L.append("")
        L.append(f"![Count of symbols rejected by each gate](figures/{f_gate.name})")
        L.append("")
        top_fails = report_df["first_failed_gate"].dropna().value_counts().head(5)
        if len(top_fails):
            total = int(top_fails.sum())
            lead = top_fails.index[0]
            L.append(
                f"`{lead}` ({GATE_MEANING.get(lead, 'see strategy')}) rejected "
                f"{top_fails.iloc[0]:,} symbols on its own; the top five account for "
                f"{total:,}."
            )
            L.append("")

    f_sec = _chart_sector_mix(report_df, figs / "sector_mix.png")
    if f_sec is not None:
        L.append(f"![Surviving candidates grouped by sector](figures/{f_sec.name})")
        L.append("")

    if diff_text:
        L.append("## Changed since the previous run")
        L.append("")
        L.append("```")
        L.append(diff_text.rstrip())
        L.append("```")
        L.append("")

    L.append("## Files")
    L.append("")
    L.append("- `candidates.csv` — every surviving symbol with all gates, flags and "
             "metrics as columns; filter it in a spreadsheet")
    L.append("")
    L.append("---")
    L.append("")
    L.append(
        "Generated by `swing_screener.screening.pipeline`. This is a screen, not "
        "advice — see [`research/`](../../../../research/) for whether this strategy "
        "has any demonstrated edge."
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "report.md"
    md.write_text("\n".join(L))
    logger.info("Report: %s", md)
    return md


# ---------------------------------------------------------------- combined


def _chart_blocking_gates_by_market(
    frames: dict[str, pd.DataFrame], out: Path
) -> Path | None:
    """Which gate blocks most, per market, as a share of symbols surveyed.

    Counts alone aren't comparable when one universe is 5,400 names and the
    other 3,400, so this normalises — the question is which constraint binds
    hardest in each market, not which market is bigger."""
    series = {}
    for name, df in frames.items():
        if "first_failed_gate" not in df or df.empty:
            continue
        codes = df["first_failed_gate"].astype("string").str.strip()
        codes = codes[codes.notna() & (codes != "") & (codes.str.lower() != "nan")]
        if codes.empty:
            continue
        series[name] = codes.value_counts() / len(df) * 100
    if not series:
        return None

    top = sorted(
        {g for s in series.values() for g in s.index},
        key=lambda g: -max(s.get(g, 0) for s in series.values()),
    )[:8][::-1]

    charts._style()
    fig, ax = charts.plt.subplots(figsize=(7.6, max(2.6, 0.42 * len(top) + 1.2)))
    ax.grid(True, axis="x", zorder=0)
    ax.set_axisbelow(True)
    colours = [SERIES_STRATEGY, charts.SERIES_BENCHMARK, charts.MUTED]
    n = len(series)
    height = 0.8 / max(n, 1)
    for i, (name, s) in enumerate(series.items()):
        offsets = [y + (i - (n - 1) / 2) * height for y in range(len(top))]
        ax.barh(offsets, [s.get(g, 0) for g in top], height=height * 0.9,
                color=colours[i % len(colours)], edgecolor=SURFACE, linewidth=1.0,
                zorder=3, label=name)
    ax.set_yticks(range(len(top)))
    ax.set_yticklabels([_gate_label(g, 34) for g in top])
    ax.set_xlabel("% of symbols surveyed")
    ax.set_title("Hardest-binding gate, by market")
    if n > 1:
        ax.legend(loc="lower right", labelcolor=charts.INK_2)
    return charts._save(fig, out)


def write_combined(
    out_dir: Path, frames: dict[str, pd.DataFrame], failures: dict[str, str],
    run_date: str,
) -> Path:
    """One cross-market review. The per-market reports stay as the detail;
    this is the single page to read in the morning."""
    out_dir = Path(out_dir)
    figs = out_dir / "figures"
    L: list[str] = []

    L.append(f"# Daily review — {run_date}")
    L.append("")

    live = {m: df for m, df in frames.items() if df is not None and not df.empty}
    total_trade = sum(int((df.get("tradeable") == True).sum()) for df in live.values())  # noqa: E712
    total_watch = sum(
        int((df.get("watchlist_candidate") == True).sum()) for df in live.values()  # noqa: E712
    )

    if failures:
        L.append("> **Some markets failed to run.**")
        for m, msg in failures.items():
            L.append(f"> - `{m}`: {msg}")
        L.append("")

    L.append(f"**{total_trade} tradeable** · **{total_watch} on watch** across "
             f"{len(live)} market(s).")
    L.append("")

    # per-market summary
    L.append("| market | surveyed | tradeable | watch | regime | detail |")
    L.append("|---|---|---|---|---|---|")
    for m, df in live.items():
        a = df.attrs
        # this file lives at reports/daily/<date>/, so "../.." is reports/ —
        # the per-market path must be relative to REPORTS_DIR, not the repo root
        link = "—"
        if a.get("screen_dir"):
            from ..paths import REPORTS_DIR

            try:
                rel = Path(a["screen_dir"]).relative_to(REPORTS_DIR)
                link = f"[report](../../{rel}/report.md)"
            except ValueError:
                link = "—"
        L.append(
            f"| {a.get('market_name', m)} | {a.get('surveyed', len(df))} "
            f"| {int((df.get('tradeable') == True).sum())} "  # noqa: E712
            f"| {int((df.get('watchlist_candidate') == True).sum())} "  # noqa: E712
            f"| {a.get('regime_note', '—')} | {link} |"
        )
    L.append("")

    # the actual candidates, across markets
    rows = []
    for m, df in live.items():
        t = df[df.get("tradeable") == True]  # noqa: E712
        if not t.empty:
            t = t.copy()
            t["market"] = df.attrs.get("market_name", m)
            t["ccy"] = df.attrs.get("currency", "")
            rows.append(t)
    if rows:
        allt = pd.concat(rows, ignore_index=True)
        sort_cols = [c for c in ["decision", "setup_quality"] if c in allt.columns]
        if sort_cols:
            allt = allt.sort_values(sort_cols, ascending=[True, False][: len(sort_cols)])
        L.append("## What to trade today")
        L.append("")
        L.append("| market | symbol | sector | price | setup | entry | stop | risk % | R | decision |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in allt.iterrows():
            c = r.get("ccy", "")
            L.append(
                f"| {r.get('market','')} | {r.get('symbol','')} | {r.get('sector','')} "
                f"| {c}{_fmt(r.get('price'))} | {r.get('strategy_setup','')} "
                f"| {c}{_fmt(r.get('entry'))} | {c}{_fmt(r.get('stop'))} "
                f"| {_fmt(r.get('risk_pct'))} | {_fmt(r.get('target_r'))} "
                f"| {r.get('decision','')} |"
            )
        L.append("")
        if "decision" in allt and (allt["decision"] == "TRADE ON TRIGGER").all():
            L.append(
                "> Every candidate today is **TRADE ON TRIGGER**, the tier measured "
                "to carry no predictive information (25.1% vs 29.7% win rate across "
                "484 trades). Treat the label as descriptive, not as a ranking."
            )
            L.append("")
    else:
        L.append("## No tradeable candidates in any market")
        L.append("")
        L.append("Normal — the gate stack passes roughly 5% of symbol-days.")
        L.append("")

    # watchlist across markets
    wrows = []
    for m, df in live.items():
        w = df[df.get("watchlist_candidate") == True]  # noqa: E712
        if not w.empty:
            w = w.copy()
            w["market"] = df.attrs.get("market_name", m)
            wrows.append(w)
    if wrows:
        allw = pd.concat(wrows, ignore_index=True)
        L.append(f"## Watchlist — {len(allw)} name(s)")
        L.append("")
        L.append("| market | symbol | sector | waiting for |")
        L.append("|---|---|---|---|")
        for _, r in allw.iterrows():
            L.append(f"| {r.get('market','')} | {r.get('symbol','')} "
                     f"| {r.get('sector','')} | {r.get('wait_for','')} |")
        L.append("")

    f = _chart_blocking_gates_by_market(
        {df.attrs.get("market_name", m): df for m, df in live.items()},
        figs / "blocking_gates.png",
    )
    if f is not None:
        L.append("## What blocked the rest")
        L.append("")
        L.append(f"![Hardest-binding gate per market, as a share of symbols surveyed]"
                 f"(figures/{f.name})")
        L.append("")

    changed = {m: df.attrs.get("diff_text", "") for m, df in live.items()
               if df.attrs.get("diff_text")}
    if changed:
        L.append("## Changed since the previous run")
        L.append("")
        for m, text in changed.items():
            L.append(f"**{live[m].attrs.get('market_name', m)}**")
            L.append("")
            L.append("```")
            L.append(text.rstrip())
            L.append("```")
            L.append("")

    L.append("---")
    L.append("")
    L.append("Generated by `swing_screener.screening.daily`. A screen, not advice — "
             "see [`research/`](../../../research/) for whether this strategy has any "
             "demonstrated edge.")

    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "report.md"
    md.write_text("\n".join(L))
    logger.info("Combined report: %s", md)
    return md
