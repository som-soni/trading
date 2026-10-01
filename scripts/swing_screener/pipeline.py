"""CLI orchestrator. Wires together: universe -> cached price pull ->
loosened screener filter -> indicators -> gate/flag engine -> entry plan
-> sizing -> decision -> sector filter -> output.

Usage:
    python -m swing_screener.pipeline --market us
    python -m swing_screener.pipeline --market india --refresh-universe
"""

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

from . import cache, universe, indicators as ind, screener, gates, entry, demand_supply as ds_mod
from . import regime as regime_mod, sizing, decision, output as out_mod, earnings, patterns, history
from .config import MARKETS
from .providers import YFinanceProvider

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pipeline")

# yfinance logs a full ERROR line per symbol for every delisting/network
# hiccup — against a 10k+ ticker universe that's mostly noise, and we
# already catch + count these failures ourselves (see "Pulled X/Y symbols
# (Z failed)"). Quiet it down to just what we handle explicitly.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

LOOKBACK_DAYS = 560  # ~2.2 years of daily bars: covers 252-bar lookbacks + buffer
REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


def _watch_flag_summary(result: gates.GateResult) -> str:
    active = [code for code, on in result.watch_flags.items() if on]
    return ",".join(active) if active else "-"


def _empty_universe_row(sym: str, sector: str, decision_label: str, reason: str) -> dict:
    """A row for a stock that never got far enough to compute gates (e.g.
    insufficient history) — same columns as a fully-reviewed row, just
    mostly blank, so it still sorts/filters correctly in the single CSV."""
    row = {
        "symbol": sym, "sector": sector, "price": None,
        "decision": decision_label, "tradeable": False, "watchlist_candidate": False,
        "decision_before": decision_label, "reason": reason,
        "uptrend_intact": None, "first_failed_gate": reason, "has_setup": False,
        "setup_tc01": False, "setup_tc02": False, "setup_tc04_tag": False,
        "watch_flags_summary": "-", "wait_for": "", "setup_quality": 0,
    }
    for code in out_mod.GATE_CODES:
        row[f"gate_{code}"] = None
    for code in out_mod.WATCH_CODES:
        row[f"watch_{code}"] = None
    return row


def run(market_key: str, refresh_universe: bool = False, limit: int | None = None) -> None:
    cfg = MARKETS[market_key]
    provider = YFinanceProvider()
    cache_dir = cache.DEFAULT_CACHE_DIR

    if refresh_universe and market_key == "us":
        universe.fetch_us_universe_from_nasdaqtrader()
    elif refresh_universe and market_key == "india":
        universe.fetch_india_universe_from_yfinance_screener()

    tickers = universe.load_universe(market_key)
    if limit:
        tickers = tickers[:limit]
    logger.info("Universe: %d tickers", len(tickers))

    # STEP 1 inputs: broad indices (+ weekly) and VIX
    index_symbols = list(cfg.broad_index_symbols.values())
    index_daily_raw, idx_failed = cache.get_many_bars(
        provider, cache_dir, market_key, index_symbols, LOOKBACK_DAYS
    )
    index_daily = {s: ind.enrich_daily(df) for s, df in index_daily_raw.items()}
    index_weekly = {
        s: ind.enrich_weekly(ind.resample_weekly(df)) for s, df in index_daily_raw.items()
    }

    vix_df = cache.get_bars(provider, cache_dir, market_key, cfg.vol_index_symbol, 30)
    vix_value = float(vix_df["close"].iloc[-1]) if vix_df is not None and not vix_df.empty else None

    # STEP 2: pull + loosely filter the universe
    logger.info("Pulling price data for universe (cached incrementally)...")
    bars_by_symbol, pull_failed = cache.get_many_bars(
        provider, cache_dir, market_key, tickers, LOOKBACK_DAYS
    )
    logger.info("Pulled %d/%d symbols (%d failed)", len(bars_by_symbol), len(tickers), len(pull_failed))

    enriched_by_symbol: dict[str, pd.DataFrame] = {
        s: ind.enrich_daily(df) for s, df in bars_by_symbol.items()
    }

    filtered: list[str] = []
    screener_fail_reason: dict[str, str] = {}
    for sym, edf in enriched_by_symbol.items():
        ok, why = screener.passes_loose_filter(cfg, edf)
        if ok:
            filtered.append(sym)
        else:
            screener_fail_reason[sym] = why
    logger.info("Screener filter: %d/%d pass", len(filtered), len(enriched_by_symbol))

    if market_key == "india":
        from .config.india import INDIA_MIN_MARKET_CAP_CR

        caps = universe.get_market_caps_cr(filtered)
        before = len(filtered)
        filtered = [
            s for s in filtered if screener.passes_market_cap(INDIA_MIN_MARKET_CAP_CR, caps.get(s))
        ]
        logger.info("Market-cap floor (>=INR %s cr): %d/%d pass", INDIA_MIN_MARKET_CAP_CR, len(filtered), before)

    sectors_raw = universe.get_sectors(market_key, filtered)
    sectors = {
        sym: cfg.sector_alias_map.get(sec, sec) for sym, sec in sectors_raw.items()
    }

    # Sector regime — one per sector represented among filtered stocks
    sectors_present = sorted(set(sectors.values()))
    benchmark_symbol = cfg.broad_index_symbols.get(cfg.benchmark_symbol, cfg.benchmark_symbol)
    benchmark_daily = index_daily.get(benchmark_symbol)
    if benchmark_daily is None:
        benchmark_daily = index_daily.get(cfg.benchmark_symbol)

    sector_index_syms = [
        cfg.sector_index_map[s] for s in sectors_present if s in cfg.sector_index_map
    ]
    sector_bars_raw, sector_failed = cache.get_many_bars(
        provider, cache_dir, market_key, sector_index_syms, LOOKBACK_DAYS
    )
    sector_regimes = {}
    for sector in sectors_present:
        sym = cfg.sector_index_map.get(sector)
        if not sym:
            logger.warning("No sector index mapped for sector '%s'", sector)
            continue
        raw = sector_bars_raw.get(sym)
        enriched = ind.enrich_daily(raw) if raw is not None else None
        sr = regime_mod.compute_sector_regime(sector, enriched, benchmark_daily, sym)
        if sr:
            sector_regimes[sector] = sr

    # downgrade rule uses the first two broad indices (SPY/QQQ for US,
    # NIFTY50/NIFTY500 for India) per STEP 1
    downgrade_syms = list(cfg.broad_index_symbols.values())[:2]
    market_regime = regime_mod.compute_market_regime(
        index_daily, index_weekly, vix_value, cfg.vol_threshold, enriched_by_symbol, downgrade_syms
    )

    logger.info("Looking up earnings dates for %d filtered tickers...", len(filtered))
    earnings_map = earnings.load_earnings_days_away(market_key, filtered)

    # STEP 3-6 per filtered stock — every stock that passed the loose
    # screener gets exactly one row, whatever the outcome (AVOID, NO
    # SETUP, WATCH, TRADE...), so the whole universe lands in one table.
    all_rows: list[dict] = []

    for sym in filtered:
        raw = bars_by_symbol[sym]
        sector = sectors.get(sym, "Unknown")
        ctx = gates.build_context(sym, raw, earnings_map.get(sym))
        if ctx is None:
            all_rows.append(_empty_universe_row(sym, sector, "NOT REVIEWED", "insufficient history"))
            continue

        result = gates.compute_gates(ctx)
        last = ctx.daily.iloc[-1]

        rs_vs_benchmark = None
        rs_vs_sector = None
        ret_3m = (
            ctx.daily["close"].iloc[-1] / ctx.daily["close"].iloc[-64] - 1
            if len(ctx.daily) >= 64 else None
        )
        if ret_3m is not None and benchmark_daily is not None and len(benchmark_daily) >= 64:
            bench_ret_3m = benchmark_daily["close"].iloc[-1] / benchmark_daily["close"].iloc[-64] - 1
            rs_vs_benchmark = (ret_3m - bench_ret_3m) * 100
        sector_r = sector_regimes.get(sector)
        sector_sym = sector_r.index_symbol if sector_r else None
        sector_daily = sector_bars_raw.get(sector_sym) if sector_sym else None
        if ret_3m is not None and sector_daily is not None and len(sector_daily) >= 64:
            sector_ret_3m = sector_daily["close"].iloc[-1] / sector_daily["close"].iloc[-64] - 1
            rs_vs_sector = (ret_3m - sector_ret_3m) * 100

        # fields available for EVERY stock, regardless of setup/decision
        row = {
            "symbol": sym,
            "sector": sector,
            "price": round(float(last["close"]), 2),
            "uptrend_intact": result.hard_gates_passed,
            "first_failed_gate": result.first_hard_fail or "",
            "has_setup": result.has_setup,
            "setup_tc01": result.setup_tc01,
            "setup_tc02": result.setup_tc02,
            "setup_tc04_tag": result.setup_tc04,
            "watch_flags_summary": _watch_flag_summary(result),
            "monthly": "up" if result.hard_gates.get("M1") else "down",
            "weekly": "up" if result.hard_gates.get("W1") and result.hard_gates.get("W2") else "down",
            "rs_vs_benchmark": round(rs_vs_benchmark, 1) if rs_vs_benchmark is not None else None,
            "rs_vs_sector": round(rs_vs_sector, 1) if rs_vs_sector is not None else None,
            "rsi": round(float(last["rsi14"]), 1) if pd.notna(last["rsi14"]) else None,
            "adx": round(float(last["adx14"]), 1) if pd.notna(last["adx14"]) else None,
            "pct_vs_sma20": round(ind.pct_distance(ctx.close, float(last["sma20"])), 1) if pd.notna(last["sma20"]) else None,
            "pct_vs_sma50": round(ind.pct_distance(ctx.close, float(last["sma50"])), 1) if pd.notna(last["sma50"]) else None,
            "pct_below_52wk_high": round(ind.pct_distance(ctx.close, float(last["high_252"])), 1) if pd.notna(last["high_252"]) else None,
            "h_pct_above_close": round(ind.pct_distance(ctx.h_value, ctx.close), 1),
            "earnings_in": earnings_map.get(sym),  # None (not a string) when lookup failed/missing — keeps the column numeric
            "candles": patterns.summarize(
                ctx.daily, float(last["sma20"]), float(last["sma50"]), ctx.h_value
            ),
            "wait_for": "",
            "setup_quality": 0,
        }
        for code in out_mod.GATE_CODES:
            row[f"gate_{code}"] = result.hard_gates.get(code)
        for code in out_mod.WATCH_CODES:
            row[f"watch_{code}"] = result.watch_flags.get(code, False)

        if not result.hard_gates_passed:
            row.update({
                "decision": "AVOID", "decision_before": "AVOID", "tradeable": False,
                "watchlist_candidate": False, "strategy_setup": "",
                "reason": f"fails {result.first_hard_fail}: {result.hard_notes.get(result.first_hard_fail, '')}",
            })
            all_rows.append(row)
            continue

        if not result.has_setup:
            row.update({
                "decision": "NO SETUP", "decision_before": "NO SETUP", "tradeable": False,
                "watchlist_candidate": False, "strategy_setup": "",
                "reason": "uptrend intact, but no TC-01/TC-02 pattern right now",
            })
            all_rows.append(row)
            continue

        plan, other_plan, plan_reason = entry.choose_plan(ctx, result, cfg.tick_size)
        if plan is None:  # shouldn't happen given has_setup, but stay defensive
            row.update({
                "decision": "NO SETUP", "decision_before": "NO SETUP", "tradeable": False,
                "watchlist_candidate": False, "strategy_setup": "", "reason": "no trade plan computed",
            })
            all_rows.append(row)
            continue

        ds_result = ds_mod.compute(ctx)
        sz = sizing.size_position(cfg, plan.entry, plan.stop, market_regime.high_vol)
        dec = decision.classify(
            ctx, result, plan, sz, ds_result, earnings_map.get(sym), market_regime.downgrade_active
        )

        row.update({
            "strategy_setup": f"{plan.setup} Plan {plan.plan} ({plan_reason})",
            "entry": round(plan.entry, 2),
            "stop": round(plan.stop, 2),
            "risk_pct": round(dec.risk_pct, 1) if dec.risk_pct == dec.risk_pct else None,
            "target_r": round(dec.r_multiple, 2) if dec.r_multiple == dec.r_multiple else None,
            "nearest_overhead": round(plan.nearest_overhead_above_entry, 2) if plan.nearest_overhead_above_entry else None,
            "shares": sz.shares,
            "position_value": round(sz.position_value, 2),
            "usd_at_risk": round(sz.actual_risk_amount, 2),
            "demand_supply": f"{ds_result.verdict} ({ds_result.supports_demand_text})",
            "decision": dec.label_after,
            "decision_before": dec.label_before,
            "reason": dec.reason,
            "setup_quality": dec.setup_quality,
            "tradeable": dec.label_after in ("TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER"),
            "watchlist_candidate": (
                dec.label_after == "WATCH - WAIT"
                and any(result.watch_flags.get(c) for c in ("X1", "X2", "X4", "X8"))
            ),
        })
        if row["watchlist_candidate"]:
            row["wait_for"] = dec.reason
        all_rows.append(row)

    reviewed_rows = [r for r in all_rows if r["decision"] not in ("AVOID", "NO SETUP", "NOT REVIEWED")]

    # sector RS used to order the decision table (sector regime 3mo RS)
    sector_rs = {
        s: (sr.return_3m_vs_benchmark or 0.0) for s, sr in sector_regimes.items()
    }
    sector_trend = {
        s: ("up" if sr.above_sma50 and sr.sma50_rising else "weak") for s, sr in sector_regimes.items()
    }

    decision.apply_sector_filter(reviewed_rows, cfg.sector_limit_per_sector)  # mutates in place
    combined = out_mod.combined_risk_summary(all_rows, cfg.account_size, cfg.currency_symbol)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report = out_mod.universe_report(all_rows, sector_rs)
    report_path = REPORT_DIR / f"{market_key}_universe.csv"
    report.to_csv(report_path, index=False)

    # history: skip for --limit test runs so partial universes don't
    # pollute run-over-run comparisons
    run_id = None
    if not limit:
        run_id = history.new_run_id()
        snapshot_path = history.record_run(market_key, run_id, report)
        print(f"Wrote: {snapshot_path} (history snapshot)")

    print(f"\n=== {cfg.name} market regime ===")
    print(
        f"VIX {vix_value}, high_vol={market_regime.high_vol}, "
        f"breadth>SMA20 {market_regime.breadth_above_sma20_pct:.0f}%, "
        f">SMA50 {market_regime.breadth_above_sma50_pct:.0f}%, "
        f"downgrade_active={market_regime.downgrade_active}"
    )
    print(
        f"\nUniverse: {len(tickers)} tickers, {len(filtered)} pass screener, "
        f"{len(all_rows)} rows in report"
    )
    print("\nSector regime:")
    for line in out_mod.sector_summary_lines(sector_rs, sector_trend):
        print(f"  {line}")
    print("\nDecision breakdown:")
    for label, count in report["decision"].value_counts().items():
        print(f"  {label}: {count}")
    print(f"\n{combined}")
    print(f"\nWrote: {report_path}")
    print(
        "Filter the 'decision'/'tradeable'/'watchlist_candidate'/'uptrend_intact' "
        "columns in a spreadsheet to slice it however you want."
    )
    if not report.empty:
        print("\nTop of report:")
        print(report.head(15).to_string(index=False))

    if run_id:
        prior_runs = [r for r in history.list_run_ids(market_key) if r != run_id]
        if prior_runs:
            print()
            history.print_diff(market_key, prior_runs[-1], run_id)
        else:
            print("\n(first recorded run for this market — nothing to diff against yet)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Swing-trade screener pipeline")
    parser.add_argument("--market", choices=list(MARKETS.keys()), required=True)
    parser.add_argument("--refresh-universe", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="debug: cap universe size")
    args = parser.parse_args()
    run(args.market, refresh_universe=args.refresh_universe, limit=args.limit)


if __name__ == "__main__":
    sys.exit(main())
