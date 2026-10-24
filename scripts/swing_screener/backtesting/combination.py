"""Momentum plus dual momentum, held side by side — the Learn guide on combining strategies, built.

Two registered strategies run as sleeves of one account: `momentum_vol_scaled` (the twenty
strongest stocks by momentum per unit of volatility, inverse-vol weighted) and `dual_momentum`
(the strongest of a few broad assets, or the safe asset when none beats it). Capital is split
between them and put back to the split at every month-end.

Why these two
-------------
The combining guide's warning is that "many that look different are the same bet: several
long-only momentum strategies all lose together in a sell-off." Measured on the stored 2020-on
runs, that is exactly what happens on this shelf: momentum_vol_scaled and momentum_baseline
correlate 0.85 month to month in India and 0.80 in the US, and in the index's worst fifth of
months they fall further than the index does. Dual momentum is the exception -- 0.46 correlated
with momentum_vol_scaled in India, and down 2.5% in those same months against the momentum
book's 7.5%, because its absolute-momentum test moves it into the safe asset when trend breaks.
The guide's rule is to add a second strategy "because it does well when the first does badly";
this is that pairing.

How the sleeves are run
-----------------------
Each sleeve is run through its own registered code and its own documented tunables -- the
momentum sleeve through `baseline.parse_args`/`run_args`, the same path its own runs take -- so
this module restates no strategy rule. It only blends: a sleeve scales linearly with the capital
it is given, so blending daily returns with month-end rebalancing is the same account as two
sub-accounts topped up to their weights each month.

Moving money between sleeves is charged each sleeve's own cost: taking it out of one costs that
sleeve's per-side cost, putting it into the other costs the other's. No new cost assumption.

What it is judged against
-------------------------
A blended benchmark, each sleeve's own declared index at the sleeve's weight -- not the broad
index alone. momentum_vol_scaled declares a small-cap index, and research/selection-vs-drag.md §5
is explicit that judging a small-cap strategy against the broad index counts segment beta as
skill. Measured on the stored runs, that choice moves the full-cycle India excess from +7.04 to
+6.12 points a year; the report states the broad-index figure as well, so neither is hidden.
"""

import argparse
import json
import logging

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache
from ..strategies.base import PortfolioStrategy
from . import baseline, metrics
from . import dual_momentum as dm

logger = logging.getLogger(__name__)

MOMENTUM_SLEEVE = "momentum_vol_scaled"
DUAL_SLEEVE = "dual_momentum"

DOC = {
    "key": "momentum_dual_combo",
    "name": "Momentum + dual momentum",
    "description": (
        "Half the account in the twenty strongest stocks by risk-adjusted momentum, half in dual "
        "momentum's single strongest asset or its safe asset, rebalanced to the split each "
        "month-end."
    ),
    "status": (
        "Built from a measured gap in the shelf rather than from a new signal. On a monthly blend "
        "of the stored runs, half each in the two sleeves beat its own blended benchmark by about "
        "6 points a year over 2010-2026 in India with a shallower drawdown, and lost to the S&P "
        "500 in the US over the same span. Read the India result through its two known risks: "
        "the momentum sleeve is acutely sensitive to trading costs, and its history is inflated "
        "by a modest, unmeasured survivorship effect."
    ),
    "thesis": (
        "Cross-sectional momentum is the one idea on this shelf with a persistent edge in India, "
        "but it is the same bet in every form it takes and it falls harder than the index in a "
        "sell-off. Dual momentum's absolute-momentum test steps out into the safe asset when "
        "trend breaks, so it does well in exactly the months momentum does badly. Holding both "
        "keeps most of the momentum return and cuts the drawdown, which neither does alone."
    ),
    "how_it_works": (
        "A share of {momentum_weight} of the account goes into the momentum sleeve and the rest "
        "into the dual momentum sleeve.",
        "Each sleeve runs its own registered strategy unchanged, with its own documented "
        "settings: the momentum sleeve holds the twenty strongest stocks by momentum per unit of "
        "volatility, weighted by inverse volatility; the dual momentum sleeve holds whichever of "
        "a few broad assets has the strongest trailing return, or its safe asset when none beats "
        "it.",
        "At every month-end close the two sleeves are put back to the split. Money taken out of "
        "a sleeve is charged that sleeve's own per-side trading cost, and money put into the "
        "other is charged that one's.",
    ),
    "caveats": (
        "The momentum sleeve's edge depends heavily on trading costs. Measured on its own runs, "
        "an India result worth +7.87 points a year at 25bps a side fell to +0.79 at 100bps. It "
        "runs here at its own documented 50bps, so a real account paying more than that should "
        "expect less of this result.",
        "The momentum sleeve's history is inflated by survivorship: stocks that were delisted "
        "after collapsing are missing from the stored prices. Research on this shelf judged the "
        "effect modest but did not measure it.",
        "The US does not pass. Over 2010-2026 the blend returned about 9% a year against about "
        "12% for the S&P 500, and neither sleeve beat it alone. It is runnable there; it is not "
        "recommended there.",
        "The combination's own version covers only how it blends. Its sleeves are versioned on "
        "their own, so a change to either sleeve changes this result without changing this "
        "version number -- each run's directory and its provenance file record exactly which "
        "sleeve versions were combined.",
        "A trade's profit and size in the trade list are rescaled to the capital its sleeve held "
        "in this account on the day it was entered. A trade that spans a month-end is resized "
        "at that rebalance in reality, so those figures are close but not exact; the equity "
        "curve itself is exact.",
        "Over 2020 onward the result looks roughly twice as strong as over 2010 onward: one bull "
        "market flatters every momentum strategy on this shelf. Read the longer window.",
    ),
    "entry_rules": (
        "Entries are the sleeves' own: see Volatility-scaled momentum and Dual momentum.",
    ),
    "exit_rules": (
        "Exits are the sleeves' own. The only rule added here is the month-end rebalance between "
        "the two.",
    ),
}


class CombinationStrategy(PortfolioStrategy):
    """momentum_vol_scaled and dual_momentum as two sleeves of one account."""

    key = DOC["key"]
    doc = DOC
    family = "momentum_dual_combo"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-24",
         "First version, from the Learn guide on combining strategies: half the account in "
         "momentum_vol_scaled, half in dual_momentum, rebalanced to the split each month-end and "
         "charged each sleeve's own cost for money moved between them. Chosen because the two are "
         "the shelf's least correlated pair among strategies with an edge, and dual momentum "
         "holds up in the months momentum falls hardest. Judged against a blended benchmark of "
         "each sleeve's own declared index, not the broad index alone."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = DOC["how_it_works"]
    caveats = DOC["caveats"]

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "trend"
    runner = "combination"           # the module whose main() backtests it

    momentum_weight = 0.5
    rebalance = "ME"
    backtest_start = "2020-01-01"

    param_docs = (
        ("Momentum weight", "momentum_weight", "Share of the account in the momentum sleeve; the rest is in dual momentum."),
        ("Rebalance", "rebalance", "When the sleeves are put back to the split. ME is month-end."),
    )


def _close(market: str, ticker: str) -> pd.Series | None:
    raw = cache.load_cached(market, ticker)
    return raw["close"].astype(float) if raw is not None and not raw.empty else None


def _blended_benchmark(market: str, idx: pd.DatetimeIndex, weight: float, rebalance: str):
    """Each sleeve's declared index at the sleeve's weight, rebalanced like the account.

    Returned as a synthetic close series so metrics.benchmark_stats can read it like any index.
    """
    from ..strategies import portfolio_strategies
    cfg = MARKETS[market]
    key = (getattr(portfolio_strategies()[MOMENTUM_SLEEVE], "benchmark_key", None) or {}).get(market)
    a_ticker = cfg.broad_index_symbols.get(key) if key else None
    a = _close(market, a_ticker) if a_ticker else None
    b = _close(market, cfg.benchmark_ticker)
    if a is None or b is None:
        return None, None
    ra = a.reindex(idx).ffill().pct_change().fillna(0.0)
    rb = b.reindex(idx).ffill().pct_change().fillna(0.0)
    month_ends = set(idx.to_series().resample(rebalance).last().dropna())
    wa, level, out = weight, 1.0, []
    for t in idx:
        level *= 1 + wa * ra[t] + (1 - wa) * rb[t]
        wa = wa * (1 + ra[t]) / (1 + wa * ra[t] + (1 - wa) * rb[t])   # drift with the month
        if t in month_ends:
            wa = weight
        out.append(level)
    name = f"{int(round(weight * 100))}% {key} + {int(round((1 - weight) * 100))}% {cfg.benchmark_symbol}"
    return pd.Series(out, index=idx) * float(b.reindex(idx).ffill().iloc[0]), name


def run(market: str, start: str, momentum_weight: float = CombinationStrategy.momentum_weight,
        rebalance: str = CombinationStrategy.rebalance) -> dict:
    from ..strategies import portfolio_strategies
    p = portfolio_strategies()
    dms = p[DUAL_SLEEVE]

    # ---- the sleeves, each through its own registered code and tunables
    margs = baseline.parse_args(["--strategy", MOMENTUM_SLEEVE, "--market", market, "--start", start])
    tdf_a, _perf_a, eq_a, pos_a = baseline.run_args(margs)
    tdf_b, eq_b, pos_b, _px, _costs_b = dm.run(market, start, dms.lookback_months, dms.rebalance, dms.cost_bps)

    # ---- one calendar. A sleeve not yet invested on a date sits in cash, so it is flat there.
    idx = eq_a.index.union(eq_b.index)
    idx = idx[idx >= pd.Timestamp(start)]
    a = eq_a.reindex(idx).ffill().bfill()
    b = eq_b.reindex(idx).ffill().bfill()
    ra, rb = a.pct_change().fillna(0.0), b.pct_change().fillna(0.0)

    # each sleeve's own per-side cost, exactly as it ran -- not a new assumption
    cost_a, cost_b = float(margs.cost_bps), float(dms.cost_bps)
    month_ends = set(idx.to_series().resample(rebalance).last().dropna())
    initial = float(a.iloc[0])
    ca, cb = momentum_weight * initial, (1 - momentum_weight) * initial
    equity, share_a, share_b, rebal_rows, costs = [], [], [], [], 0.0
    for t in idx:
        ca *= 1 + ra[t]
        cb *= 1 + rb[t]
        if t in month_ends:
            total = ca + cb
            target_a = momentum_weight * total
            moved = abs(ca - target_a)
            # out of one sleeve at its cost, into the other at its own
            cost = moved * (cost_a + cost_b) / 1e4
            costs += cost
            if moved:
                rebal_rows.append({"date": t.date(), "momentum_before": round(ca / total, 4),
                                   "moved": round(moved, 2), "cost": round(cost, 2),
                                   "direction": "to dual" if ca > target_a else "to momentum"})
            total -= cost
            ca, cb = momentum_weight * total, (1 - momentum_weight) * total
        equity.append(ca + cb)
        share_a.append(ca)
        share_b.append(cb)
    eq = pd.Series(equity, index=idx)
    cap_a, cap_b = pd.Series(share_a, index=idx), pd.Series(share_b, index=idx)

    # ---- trades, rescaled to the capital their sleeve held here when they were entered
    def rescale(tdf: pd.DataFrame, cap: pd.Series, standalone: pd.Series, sleeve: str) -> pd.DataFrame:
        if tdf is None or tdf.empty:
            return pd.DataFrame()
        t = tdf.copy()
        when = pd.to_datetime(t["entry_date"])
        k = (cap.reindex(when, method="ffill").values / standalone.reindex(when, method="ffill").values)
        for c in ("pnl", "notional", "costs", "shares"):
            if c in t:
                t[c] = t[c].astype(float) * k
        t.insert(0, "sleeve", sleeve)
        return t

    tdf = pd.concat([rescale(tdf_a, cap_a, a, MOMENTUM_SLEEVE), rescale(tdf_b, cap_b, b, DUAL_SLEEVE)],
                    ignore_index=True)
    if len(tdf):
        tdf = tdf.sort_values("entry_date", kind="stable").reset_index(drop=True)

    pos = pos_a.reindex(idx).ffill().fillna(0) + pos_b.reindex(idx).ffill().fillna(0)
    bench, bench_name = _blended_benchmark(market, idx, momentum_weight, rebalance)
    return {
        "eq": eq, "pos": pos, "trades": tdf, "rebalances": pd.DataFrame(rebal_rows), "costs": costs,
        "bench": bench, "bench_name": bench_name, "broad": _close(market, MARKETS[market].benchmark_ticker),
        "max_positions": int(margs.top_n) + 1,
        "sleeves": {MOMENTUM_SLEEVE: p[MOMENTUM_SLEEVE].spec_id(), DUAL_SLEEVE: dms.spec_id()},
        "sleeve_costs_bps": {MOMENTUM_SLEEVE: cost_a, DUAL_SLEEVE: cost_b},
    }


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    from ..strategies import portfolio_strategies
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Momentum + dual momentum, as two sleeves of one account")
    ap.add_argument("--strategy", default=CombinationStrategy.key)
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--momentum-weight", type=float, default=CombinationStrategy.momentum_weight)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    if not 0.0 <= a.momentum_weight <= 1.0:
        ap.error("--momentum-weight is a share between 0 and 1")

    cfg = MARKETS[a.market]
    r = run(a.market, a.start, a.momentum_weight)
    eq, pos, tdf = r["eq"], r["pos"], r["trades"]
    bc = r["bench"] if r["bench"] is not None else (
        r["broad"].reindex(eq.index).ffill() if r["broad"] is not None else None)

    broad_excess = None
    if r["broad"] is not None:
        bb = r["broad"].reindex(eq.index).ffill().dropna()
        yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
        cagr = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100
        bcagr = ((bb.iloc[-1] / bb.iloc[0]) ** (1 / yrs) - 1) * 100
        broad_excess = cagr - bcagr

    notes = [
        "A COMBINATION of two registered strategies, each run unchanged through its own code: "
        f"{a.momentum_weight:.0%} {MOMENTUM_SLEEVE}, {1 - a.momentum_weight:.0%} {DUAL_SLEEVE}, "
        "rebalanced to the split each month-end.",
        f"Sleeve versions: {MOMENTUM_SLEEVE} {r['sleeves'][MOMENTUM_SLEEVE]}, "
        f"{DUAL_SLEEVE} {r['sleeves'][DUAL_SLEEVE]}.",
        f"Benchmark: {r['bench_name'] or cfg.benchmark_symbol} -- each sleeve's own declared index at "
        "the sleeve's weight, so the momentum sleeve's small-cap beta is not counted as skill.",
        (f"Against {cfg.benchmark_symbol} alone the excess is {broad_excess:+.2f} points a year."
         if broad_excess is not None else "The broad index was not available for a second comparison."),
        f"Moving money between sleeves cost {r['costs']:,.0f} over {len(r['rebalances'])} rebalances, "
        f"charged at each sleeve's own per-side cost ({r['sleeve_costs_bps'][MOMENTUM_SLEEVE]:g}bps "
        f"momentum, {r['sleeve_costs_bps'][DUAL_SLEEVE]:g}bps dual).",
        "Trade P&L and size are rescaled to the capital each sleeve held here on the entry date; "
        "the equity curve is exact.",
    ]
    perf = metrics.compute(equity=eq, positions_open=pos, trades=tdf, max_open_positions=r["max_positions"],
                           costs_paid=r["costs"], bench_close=bc, notes=notes)
    perf.benchmark_name = r["bench_name"] or f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"

    spec = portfolio_strategies()[a.strategy].spec_id()
    # sleeve versions by NUMBER only: a full `_vX-hash` here would be the first match for ingest's
    # spec-id pattern and file this run under a sleeve's version instead of its own
    sv = "_".join(f"{k.split('_')[0][:4]}{v.split('-')[0].lstrip('v')}" for k, v in r["sleeves"].items())
    name = f"{a.start}_combo{int(round(a.momentum_weight * 100))}_{sv}_{spec}"
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    r["rebalances"].to_csv(out / "rebalances.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": pos,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    (out / "provenance.json").write_text(json.dumps({
        "strategy": a.strategy, "spec_id": spec, "market": a.market, "start": a.start,
        "momentum_weight": a.momentum_weight, "sleeves": r["sleeves"],
        "sleeve_costs_bps": r["sleeve_costs_bps"], "benchmark": r["bench_name"],
        "broad_index_excess_cagr": broad_excess,
    }, indent=2))
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, r["max_positions"]))
    try:
        from . import report as report_mod
        md = report_mod.write_report(out, f"{cfg.name} — momentum + dual momentum, {a.start} onward", perf, eq,
                                     pos, tdf, cfg.currency_symbol, r["max_positions"], bc,
                                     f"python3 -m swing_screener.backtesting.combination --market {a.market} "
                                     f"--start {a.start}")
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
