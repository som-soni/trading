"""CLI orchestrator. Wires together: universe -> cached price pull ->
loosened screener filter -> indicators -> gate/flag engine -> entry plan
-> sizing -> decision -> sector filter -> output.

Usage:
    python -m swing_screener.screening.pipeline --market us
    python -m swing_screener.screening.pipeline --market india --refresh-universe
"""

import argparse
import datetime as _dt
import logging
import time
import sys
from pathlib import Path

import pandas as pd

from ..marketdata import cache, universe

from ..core import indicators as ind, context as ctx_mod
from ..core import regime as regime_mod, sizing, patterns
from . import portfolio, output as out_mod, history
from ..marketdata import earnings
from ..config import MARKETS
from ..providers import YFinanceProvider
from ..strategies import DEFAULT_STRATEGY, describe_strategies, get_strategy, list_strategies

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("pipeline")

# yfinance logs a full ERROR line per symbol for every delisting/network
# hiccup — against a 10k+ ticker universe that's mostly noise, and we
# already catch + count these failures ourselves (see "Pulled X/Y symbols
# (Z failed)"). Quiet it down to just what we handle explicitly.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

LOOKBACK_DAYS = 560  # ~2.2 years of daily bars: covers 252-bar lookbacks + buffer
from ..paths import REPORTS_DIR as REPORT_DIR  # noqa: F401


def _watch_flag_summary(result) -> str:
    active = [code for code, on in result.watch_flags.items() if on]
    return ",".join(active) if active else "-"


def _empty_universe_row(strategy, sym: str, sector: str, decision_label: str, reason: str) -> dict:
    """A row for a stock that never got far enough to compute gates (e.g.
    insufficient history) — same columns as a fully-reviewed row, just
    mostly blank, so it still sorts/filters correctly in the single CSV."""
    row = {
        "strategy": strategy.key, "symbol": sym, "sector": sector, "price": None,
        "decision": decision_label, "tradeable": False, "watchlist_candidate": False,
        "decision_before": decision_label, "reason": reason,
        "uptrend_intact": None, "first_failed_gate": reason, "has_setup": False,
        "watch_flags_summary": "-", "wait_for": "", "setup_quality": 0,
    }
    for code in strategy.setup_codes:
        row[f"setup_{code}"] = False
    for code in strategy.gate_codes:
        row[f"gate_{code}"] = None
    for code in strategy.watch_codes:
        row[f"watch_{code}"] = None
    return row


def run(
    market_key: str,
    refresh_universe: bool = False,
    limit: int | None = None,
    strategy_key: str = DEFAULT_STRATEGY,
) -> pd.DataFrame:
    cfg = MARKETS[market_key]
    strategy = get_strategy(strategy_key)
    provider = YFinanceProvider()
    logger.info("Strategy: %s (%s)", strategy.key, strategy.name)

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
        provider, market_key, index_symbols, LOOKBACK_DAYS
    )
    index_daily = {s: ind.enrich_daily(df) for s, df in index_daily_raw.items()}
    index_weekly = {
        s: ind.enrich_weekly(ind.resample_weekly(df)) for s, df in index_daily_raw.items()
    }

    vix_df = cache.get_bars(provider, market_key, cfg.vol_index_symbol, 30)
    vix_value = float(vix_df["close"].iloc[-1]) if vix_df is not None and not vix_df.empty else None

    # STEP 2: pull + loosely filter the universe
    logger.info("Pulling price data for universe (cached incrementally)...")
    bars_by_symbol, pull_failed = cache.get_many_bars(
        provider, market_key, tickers, LOOKBACK_DAYS
    )
    logger.info("Pulled %d/%d symbols (%d failed)", len(bars_by_symbol), len(tickers), len(pull_failed))

    logger.info("Computing indicators for %d symbols...", len(bars_by_symbol))
    enriched_by_symbol: dict[str, pd.DataFrame] = {}
    _t0 = time.time()
    _step = max(1, len(bars_by_symbol) // 10)
    for _i, (s_, df_) in enumerate(bars_by_symbol.items(), 1):
        enriched_by_symbol[s_] = ind.enrich_daily(df_)
        if _i % _step == 0 or _i == len(bars_by_symbol):
            logger.info("  indicators %d/%d (%.0f/s)", _i, len(bars_by_symbol),
                        _i / max(time.time() - _t0, 1e-9))

    filtered: list[str] = []
    screener_fail_reason: dict[str, str] = {}
    for sym, edf in enriched_by_symbol.items():
        ok, why = strategy.passes_prefilter(cfg, edf)
        if ok:
            filtered.append(sym)
        else:
            screener_fail_reason[sym] = why
    logger.info("Pre-filter (%s): %d/%d pass", strategy.key, len(filtered), len(enriched_by_symbol))

    if market_key == "india":
        from ..config.india import INDIA_MIN_MARKET_CAP_CR
        from . import screener

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
        provider, market_key, sector_index_syms, LOOKBACK_DAYS
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

    logger.info("Evaluating %d filtered symbols (gates, setups, plans)...", len(filtered))
    _t0 = time.time()
    _step = max(1, len(filtered) // 10)
    for _i, sym in enumerate(filtered, 1):
        if _i % _step == 0 or _i == len(filtered):
            _rate = _i / max(time.time() - _t0, 1e-9)
            logger.info("  evaluated %d/%d (%.0f/s, ETA %.0f s)", _i, len(filtered),
                        _rate, (len(filtered) - _i) / max(_rate, 1e-9))
        raw = bars_by_symbol[sym]
        sector = sectors.get(sym, "Unknown")
        ctx = ctx_mod.build_context(sym, raw, earnings_map.get(sym))
        if ctx is None:
            all_rows.append(_empty_universe_row(strategy, sym, sector, "NOT REVIEWED", "insufficient history"))
            continue

        result = strategy.evaluate(ctx)
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
            "strategy": strategy.key,
            "symbol": sym,
            "sector": sector,
            "price": round(float(last["close"]), 2),
            "uptrend_intact": result.hard_gates_passed,
            "first_failed_gate": result.first_hard_fail or "",
            "has_setup": result.has_setup,
            "watch_flags_summary": _watch_flag_summary(result),
            "rs_vs_benchmark": round(rs_vs_benchmark, 1) if rs_vs_benchmark is not None else None,
            "rs_vs_sector": round(rs_vs_sector, 1) if rs_vs_sector is not None else None,
            "rsi": round(float(last["rsi14"]), 1) if pd.notna(last["rsi14"]) else None,
            "adx": round(float(last["adx14"]), 1) if pd.notna(last["adx14"]) else None,
            "pct_vs_sma20": round(ind.pct_distance(ctx.close, float(last["sma20"])), 1) if pd.notna(last["sma20"]) else None,
            "pct_vs_sma50": round(ind.pct_distance(ctx.close, float(last["sma50"])), 1) if pd.notna(last["sma50"]) else None,
            "pct_below_52wk_high": round(ind.pct_distance(ctx.close, float(last["high_252"])), 1) if pd.notna(last["high_252"]) else None,
            "earnings_in": earnings_map.get(sym),  # None (not a string) when lookup failed/missing — keeps the column numeric
            "candles": patterns.summarize(
                ctx.daily, float(last["sma20"]), float(last["sma50"]), ctx.h_value
            ),
            "wait_for": "",
            "setup_quality": 0,
        }
        for code in strategy.setup_codes:
            row[f"setup_{code}"] = bool(result.setups.get(code))
        for code in strategy.gate_codes:
            row[f"gate_{code}"] = result.hard_gates.get(code)
        for code in strategy.watch_codes:
            row[f"watch_{code}"] = result.watch_flags.get(code, False)
        row.update(strategy.report_extras(ctx, result, None))

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
                "reason": f"gates pass, but no {strategy.key} setup right now",
            })
            all_rows.append(row)
            continue

        choice = strategy.build_plans(ctx, result, cfg)
        plan, plan_reason = choice.chosen, choice.reason
        if plan is None:  # shouldn't happen given has_setup, but stay defensive
            row.update({
                "decision": "NO SETUP", "decision_before": "NO SETUP", "tradeable": False,
                "watchlist_candidate": False, "strategy_setup": "", "reason": "no trade plan computed",
            })
            all_rows.append(row)
            continue

        sz = sizing.size_position(cfg, plan.entry, plan.stop, market_regime.high_vol)
        dec = strategy.classify(
            ctx, result, plan, sz, earnings_map.get(sym), market_regime.downgrade_active
        )

        row.update({
            "strategy_setup": f"{plan.setup} / {plan.plan} ({plan_reason})",
            "entry": round(plan.entry, 2),
            "stop": round(plan.stop, 2),
            "risk_pct": round(dec.risk_pct, 1) if dec.risk_pct == dec.risk_pct else None,
            "target_r": round(dec.r_multiple, 2) if dec.r_multiple == dec.r_multiple else None,
            "nearest_overhead": round(plan.nearest_overhead_above_entry, 2) if plan.nearest_overhead_above_entry else None,
            "shares": sz.shares,
            "position_value": round(sz.position_value, 2),
            "usd_at_risk": round(sz.actual_risk_amount, 2),
            "decision": dec.label_after,
            "decision_before": dec.label_before,
            "reason": dec.reason,
            "setup_quality": dec.setup_quality,
            "tradeable": dec.label_after in ("TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER"),
            "watchlist_candidate": (
                dec.label_after == "WATCH - WAIT" and bool(result.active_watch_flags)
            ),
        })
        row.update(strategy.report_extras(ctx, result, plan))
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

    portfolio.apply_sector_filter(reviewed_rows, cfg.sector_limit_per_sector)  # mutates in place
    combined = out_mod.combined_risk_summary(all_rows, cfg.account_size, cfg.currency_symbol)

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    from ..paths import run_dir
    report = out_mod.universe_report(all_rows, sector_rs, strategy)
    # Screener output goes into the same per-run tree the backtests use, so a
    # day's candidates, its CSV and its charts sit together instead of in a
    # flat pile. The stable top-level CSV is kept as a convenience symlink
    # target for anything that reads "the latest" by a fixed path.
    screen_dir = run_dir(market_key, strategy.key, f"screener/{_dt.date.today()}")
    report_path = screen_dir / "candidates.csv"
    report.to_csv(report_path, index=False)
    latest_csv = REPORT_DIR / f"{market_key}_{strategy.key}_universe.csv"
    report.to_csv(latest_csv, index=False)

    # history: skip for --limit test runs so partial universes don't
    # pollute run-over-run comparisons
    run_id = None
    diff_text = ""
    if not limit:
        run_id = history.new_run_id()
        snapshot_path = history.record_run(market_key, run_id, report, strategy_key=strategy.key)
        print(f"Wrote: {snapshot_path} (history snapshot)")

    print(f"\n=== {cfg.name} market regime | strategy: {strategy.key} ===")
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
            import contextlib, io as _io

            _buf = _io.StringIO()
            with contextlib.redirect_stdout(_buf):
                history.print_diff(market_key, prior_runs[-1], run_id)
            diff_text = _buf.getvalue()
            print(diff_text)
        else:
            print("\n(first recorded run for this market — nothing to diff against yet)")

    _vix_txt = f"{vix_value:.1f}" if isinstance(vix_value, (int, float)) else str(vix_value)
    try:
        from . import candidates_report

        md = candidates_report.write(
            screen_dir, cfg.name, strategy.name, strategy.key, report,
            cfg.currency_symbol, run_id or str(_dt.date.today()),
            regime_note=(
                f"Market regime — VIX {_vix_txt}, high_vol={market_regime.high_vol}, "
                f"breadth >SMA20 {market_regime.breadth_above_sma20_pct:.0f}%, "
                f">SMA50 {market_regime.breadth_above_sma50_pct:.0f}%"
                + (", **downgrade active**" if market_regime.downgrade_active else "")
            ),
            diff_text=diff_text,
        )
        print(f"Report: {md}")
    except Exception as e:  # a chart failure must never lose the run's CSV
        logger.warning("markdown report not generated (%s: %s)", type(e).__name__, e)

    # Metadata for the cross-market consolidated report. `attrs` travels with
    # the frame in-process, so daily.py gets this without re-reading files or
    # pipeline.run() changing its return type.
    report.attrs.update({
        "market_key": market_key,
        "market_name": cfg.name,
        "strategy_key": strategy.key,
        "strategy_name": strategy.name,
        "currency": cfg.currency_symbol,
        "run_id": run_id or str(_dt.date.today()),
        "screen_dir": str(screen_dir),
        "regime_note": (
            f"VIX {_vix_txt}, breadth >SMA20 "
            f"{market_regime.breadth_above_sma20_pct:.0f}%, >SMA50 "
            f"{market_regime.breadth_above_sma50_pct:.0f}%"
            + (", **downgrade active**" if market_regime.downgrade_active else "")
        ),
        "diff_text": diff_text,
        "surveyed": len(report),
        "universe_size": len(tickers),
    })

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Swing-trade screener pipeline")
    parser.add_argument("--market", choices=list(MARKETS.keys()), required=True)
    parser.add_argument("--refresh-universe", action="store_true")
    parser.add_argument("--limit", type=int, default=None, help="debug: cap universe size")
    parser.add_argument(
        "--strategy", default=DEFAULT_STRATEGY, choices=list_strategies(),
        help="which strategy to run:\n" + describe_strategies(),
    )
    args = parser.parse_args()
    run(
        args.market,
        refresh_universe=args.refresh_universe,
        limit=args.limit,
        strategy_key=args.strategy,
    )


if __name__ == "__main__":
    sys.exit(main())
