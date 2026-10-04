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


def _chart_sector_strength(
    sector_regimes: dict, candidate_counts: dict[str, int], out: Path
) -> Path | None:
    """Sector index performance vs the benchmark, with the sectors we actually
    have candidates in emphasised.

    This is the picture behind the hypothesis that a stock in a leading sector
    has better odds: if the candidates cluster in the left (lagging) half, the
    screen is finding strength in weak neighbourhoods, which is worth knowing
    before sizing them."""
    rows = [
        (sec, sr.return_3m_vs_benchmark)
        for sec, sr in sector_regimes.items()
        if sr.return_3m_vs_benchmark is not None
    ]
    if not rows:
        return None
    rows.sort(key=lambda kv: kv[1])
    labels = [f"{s}  ({candidate_counts.get(s, 0)})" for s, _ in rows]
    values = [v for _, v in rows]

    charts._style()
    fig, ax = charts.plt.subplots(figsize=(7.6, max(2.6, 0.36 * len(rows) + 1.2)))
    ax.grid(True, axis="x", zorder=0)
    ax.set_axisbelow(True)
    # emphasis, not a third colour scale: sectors holding candidates carry the
    # diverging sign colour, the rest recede to muted
    colours = [
        (POS if v >= 0 else NEG) if candidate_counts.get(s, 0) else MUTED
        for (s, v) in rows
    ]
    ax.barh(labels, values, height=0.64, color=colours,
            edgecolor=SURFACE, linewidth=1.0, zorder=3)
    ax.axvline(0, color=AXIS, linewidth=0.9, zorder=4)
    ax.set_xlabel("3-month return vs benchmark (%)")
    ax.set_title("Sector strength — (n) = candidates found there")
    return charts._save(fig, out)


def _sector_section(
    sector_regimes: dict, report_df: pd.DataFrame
) -> tuple[list[str], dict[str, int]]:
    """Sector table plus the per-sector candidate counts the chart needs."""
    live = report_df[
        report_df["decision"].isin(
            ["TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER", "WATCH - WAIT"]
        )
    ] if "decision" in report_df else report_df.iloc[0:0]
    counts = live["sector"].fillna("Unknown").value_counts().to_dict() if "sector" in live else {}

    if not sector_regimes:
        return [], counts

    L = ["## Sector performance", ""]
    # be explicit when sector coverage is partial — otherwise a reader takes
    # "3 sectors" as the market's structure rather than a data limitation
    sectors_seen = set(report_df["sector"].dropna().unique()) if "sector" in report_df else set()
    uncovered = len(sectors_seen - set(sector_regimes) - {"Unknown"})
    if uncovered:
        L.append(
            f"> Coverage is partial: {len(sector_regimes)} sector "
            f"{'index has' if len(sector_regimes) == 1 else 'indices have'} usable "
            f"history, while {uncovered} further sector(s) appear in the universe "
            "with no index available. Read the table as a sample, not the whole market."
        )
        L.append("")
    L.append("| sector | index | 3m vs benchmark | above SMA50 | SMA50 rising | candidates |")
    L.append("|---|---|---|---|---|---|")
    ordered = sorted(
        sector_regimes.items(),
        key=lambda kv: (kv[1].return_3m_vs_benchmark is None, -(kv[1].return_3m_vs_benchmark or 0)),
    )
    for sec, sr in ordered:
        rs = sr.return_3m_vs_benchmark
        L.append(
            f"| {sec} | `{sr.index_symbol}` "
            f"| {'—' if rs is None else f'{rs:+.1f}%'} "
            f"| {'yes' if sr.above_sma50 else 'no'} "
            f"| {'yes' if sr.sma50_rising else 'no'} "
            f"| {counts.get(sec, 0)} |"
        )
    L.append("")

    # does the day's evidence support the leading-sector hypothesis?
    with_c = {s: sr.return_3m_vs_benchmark for s, sr in sector_regimes.items()
              if counts.get(s, 0) and sr.return_3m_vs_benchmark is not None}
    if with_c:
        lead = sum(1 for v in with_c.values() if v > 0)
        L.append(
            f"> {lead} of {len(with_c)} sectors holding candidates are "
            f"**outperforming** the benchmark over 3 months. "
            + (
                "Candidates are concentrated in leading sectors today."
                if lead > len(with_c) / 2
                else "Most candidates sit in **lagging** sectors today — worth "
                "weighing before sizing them equally."
            )
        )
        L.append("")
    return L, counts


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
    regime_note: str = "", diff_text: str = "", sector_regimes: dict | None = None,
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
    sec_lines, sec_counts = _sector_section(sector_regimes or {}, report_df)
    if sec_lines:
        L += sec_lines
        f_sec_str = _chart_sector_strength(
            sector_regimes or {}, sec_counts, figs / "sector_strength.png"
        )
        if f_sec_str is not None:
            L.append(f"![Sector index performance versus the benchmark]"
                     f"(figures/{f_sec_str.name})")
            L.append("")

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


def _strategy_section(key: str, by_market: dict, L: list[str]) -> tuple[int, int]:
    """One strategy's section. Returns (tradeable, watch) counts."""
    from ..strategies import get_strategy

    try:
        strat = get_strategy(key)
        title, explain = strat.name, strat.explain()
    except Exception:
        title, explain = key, ""

    live = {m: df for m, df in by_market.items() if df is not None and not df.empty}
    n_trade = sum(int((df.get("tradeable") == True).sum()) for df in live.values())  # noqa: E712
    n_watch = sum(
        int((df.get("watchlist_candidate") == True).sum()) for df in live.values()  # noqa: E712
    )

    L.append(f"## {title}")
    L.append("")
    L.append(f"`{key}` — **{n_trade} tradeable**, **{n_watch} on watch**")
    L.append("")
    if explain:
        L.append("<details><summary>How this strategy works</summary>")
        L.append("")
        L.append(explain)
        L.append("</details>")
        L.append("")

    if not live:
        L.append("_No results for this strategy._")
        L.append("")
        return n_trade, n_watch

    # per-market line
    L.append("| market | surveyed | tradeable | watch | regime | detail |")
    L.append("|---|---|---|---|---|---|")
    for m, df in live.items():
        a = df.attrs
        link = "—"
        if a.get("screen_dir"):
            from ..paths import REPORTS_DIR

            try:
                rel = Path(a["screen_dir"]).relative_to(REPORTS_DIR)
                link = f"[report](../../{rel}/report.md)"
            except ValueError:
                pass
        L.append(
            f"| {a.get('market_name', m)} | {a.get('surveyed', len(df))} "
            f"| {int((df.get('tradeable') == True).sum())} "  # noqa: E712
            f"| {int((df.get('watchlist_candidate') == True).sum())} "  # noqa: E712
            f"| {a.get('regime_note', '—')} | {link} |"
        )
    L.append("")

    # candidates across markets
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
        L.append("### Candidates")
        L.append("")
        L.append("| market | symbol | sector | price | entry | vs price | stop "
                 "| risk % | R | decision |")
        L.append("|---|---|---|---|---|---|---|---|---|---|")
        for _, r in allt.iterrows():
            c = r.get("ccy", "")
            px, entry = r.get("price"), r.get("entry")
            gap = ("—" if not (isinstance(px, (int, float)) and isinstance(entry, (int, float))
                               and px) else f"{(entry / px - 1) * 100:+.1f}%")
            L.append(
                f"| {r.get('market','')} | {r.get('symbol','')} | {r.get('sector','')} "
                f"| {c}{_fmt(px)} | {c}{_fmt(entry)} | {gap} | {c}{_fmt(r.get('stop'))} "
                f"| {_fmt(r.get('risk_pct'))} | {_fmt(r.get('target_r'))} "
                f"| {r.get('decision','')} |"
            )
        L.append("")
        L.append(
            "> Entries are resting **buy-stop** orders placed ABOVE the current "
            "price — the trade only happens if price rises through the trigger, "
            "and the order expires unfilled after 10 business days. `vs price` is "
            "how far it has to move first."
        )
        L.append("")
    else:
        L.append("### Candidates")
        L.append("")
        L.append("_None today._ The gate stack passes roughly 5% of symbol-days, "
                 "so this is the normal outcome.")
        L.append("")

    # watchlist
    wrows = []
    for m, df in live.items():
        w = df[df.get("watchlist_candidate") == True]  # noqa: E712
        if not w.empty:
            w = w.copy()
            w["market"] = df.attrs.get("market_name", m)
            wrows.append(w)
    if wrows:
        allw = pd.concat(wrows, ignore_index=True)
        L.append(f"### Watchlist — {len(allw)} name(s)")
        L.append("")
        L.append("| market | symbol | sector | waiting for |")
        L.append("|---|---|---|---|")
        for _, r in allw.iterrows():
            L.append(f"| {r.get('market','')} | {r.get('symbol','')} "
                     f"| {r.get('sector','')} | {r.get('wait_for','')} |")
        L.append("")

    # sector view
    sec_blocks: list[str] = []
    for m, df in live.items():
        regs = df.attrs.get("sector_regimes") or {}
        if not regs:
            continue
        name = df.attrs.get("market_name", m)
        _, counts = _sector_section(regs, df)
        ranked = sorted(
            ((sec, sr.return_3m_vs_benchmark) for sec, sr in regs.items()
             if sr.return_3m_vs_benchmark is not None),
            key=lambda kv: -kv[1],
        )
        if not ranked:
            continue
        sec_blocks.append(f"**{name}**")
        sec_blocks.append("")
        if len(ranked) < 6:
            sec_blocks.append("- Ranked: " + ", ".join(f"{s} ({v:+.1f}%)" for s, v in ranked))
        else:
            sec_blocks.append("- Leading: " + ", ".join(f"{s} ({v:+.1f}%)" for s, v in ranked[:3]))
            sec_blocks.append("- Lagging: " + ", ".join(f"{s} ({v:+.1f}%)" for s, v in ranked[-3:]))
        rs = dict(ranked)
        held = {s: c for s, c in counts.items() if c}
        total = sum(held.values())
        in_lead = sum(c for s, c in held.items() if rs.get(s, 0) > 0)
        in_lag = sum(c for s, c in held.items() if s in rs and rs[s] <= 0)
        unc = total - in_lead - in_lag
        if total:
            parts = [f"**{in_lead} of {total}** candidates sit in an outperforming sector"]
            if in_lag:
                parts.append(f"{in_lag} in a lagging one")
            if unc:
                parts.append(f"{unc} in sectors with no index available")
            sec_blocks.append("- " + ", ".join(parts))
        sec_blocks.append("")
    if sec_blocks:
        L.append("### Sector performance")
        L.append("")
        L += sec_blocks

    return n_trade, n_watch


def write_combined(
    out_dir: Path, by_strategy: dict, failures: dict[str, str], run_date: str,
) -> Path:
    """One cross-market, cross-strategy review.

    `by_strategy` is {strategy_key: {market: report_df}}. Each strategy gets
    its own section with an explanation of what it looks for, because a list
    of tickers with no statement of the thesis behind them is unreadable by
    anyone who did not write the strategy.
    """
    out_dir = Path(out_dir)
    figs = out_dir / "figures"
    L: list[str] = [f"# Daily review — {run_date}", ""]

    if failures:
        L.append("> **Some runs failed.**")
        for m, msg in failures.items():
            L.append(f"> - `{m}`: {msg}")
        L.append("")

    # contents, with the headline counts
    L.append("| strategy | tradeable | on watch |")
    L.append("|---|---|---|")
    counts: dict[str, tuple[int, int]] = {}
    body: list[str] = []
    for key, by_market in by_strategy.items():
        section: list[str] = []
        counts[key] = _strategy_section(key, by_market, section)
        body += section
    for key, (t, w) in counts.items():
        L.append(f"| [{key}](#{key.replace('_', '-')}) | {t} | {w} |")
    L.append("")
    L += body

    # cross-strategy: what blocked the universe, per market (same every run)
    first = next((bm for bm in by_strategy.values() if bm), {})
    live = {df.attrs.get("market_name", m): df for m, df in first.items()
            if df is not None and not df.empty}
    f = _chart_blocking_gates_by_market(live, figs / "blocking_gates.png") if live else None
    if f is not None:
        L.append("## What blocked the rest")
        L.append("")
        L.append(f"![Hardest-binding gate per market, as a share of symbols surveyed]"
                 f"(figures/{f.name})")
        L.append("")

    changed = []
    for key, by_market in by_strategy.items():
        for m, df in by_market.items():
            if df is None or df.empty or not df.attrs.get("diff_text"):
                continue
            changed.append((f"{df.attrs.get('market_name', m)} · {key}",
                            df.attrs["diff_text"]))
    if changed:
        L.append("## Changed since the previous run")
        L.append("")
        for label, text in changed:
            L.append(f"**{label}**")
            L.append("")
            L.append("```")
            L.append(text.rstrip())
            L.append("```")
            L.append("")

    L.append("---")
    L.append("")
    L.append("Generated by `swing_screener.screening.daily`. A screen, not advice — "
             "see [`research/`](../../../research/) for whether any of these "
             "strategies has a demonstrated edge.")

    out_dir.mkdir(parents=True, exist_ok=True)
    md = out_dir / "report.md"
    md.write_text("\n".join(L))
    logger.info("Combined report: %s", md)
    return md
