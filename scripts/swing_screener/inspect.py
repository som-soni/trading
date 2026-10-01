"""Manual query/debug tool for a single stock: pulls (or reuses cached)
bars, runs the full STEP 3-6 pipeline for it, and prints every gate,
watch flag, the trade plan, demand/supply verdict, sizing, and decision.
Useful for "why did/didn't this stock show up in the decision table?"
without re-running the whole universe.

Usage:
    python3 -m swing_screener.inspect --market india --symbol RELIANCE.NS
    python3 -m swing_screener.inspect --market us --symbol AAPL --fresh
"""

import argparse

import pandas as pd

from . import cache, gates, entry, demand_supply as ds_mod, sizing, decision, patterns, earnings
from .config import MARKETS
from .providers import YFinanceProvider
from .pipeline import LOOKBACK_DAYS


def inspect(market_key: str, symbol: str, fresh: bool = False) -> None:
    cfg = MARKETS[market_key]
    provider = YFinanceProvider()

    if fresh:
        raw = provider.get_daily_bars(symbol, LOOKBACK_DAYS)
        if raw is not None and not raw.empty:
            cache.save_cached(cache.DEFAULT_CACHE_DIR, market_key, symbol, raw)
    else:
        raw = cache.get_bars(provider, cache.DEFAULT_CACHE_DIR, market_key, symbol, LOOKBACK_DAYS)

    if raw is None or raw.empty:
        print(f"No data for {symbol}")
        return

    print(f"=== {symbol} ({market_key}) ===")
    print(f"{len(raw)} daily bars, {raw.index[0].date()} -> {raw.index[-1].date()}")
    print(raw.tail(5))

    earnings_map = earnings.load_earnings_days_away(market_key, [symbol])
    ctx = gates.build_context(symbol, raw, earnings_map.get(symbol))
    if ctx is None:
        print("\nInsufficient history to compute gates (<60 bars)")
        return

    print(f"\nclose={ctx.close:.2f}  H={ctx.h_value:.2f}  L={ctx.l_value:.2f}  P={ctx.p_value:.2f}")
    print(f"prior structural swing low: {ctx.prior_swing_low}")
    print(f"overhead levels within 3% above: {[l for l in ctx.overhead if ctx.close < l <= ctx.close*1.03]}")
    print(f"earnings in: {earnings_map.get(symbol, 'unknown')} trading days")

    result = gates.compute_gates(ctx)
    print("\n--- hard gates ---")
    for code, ok in result.hard_gates.items():
        note = result.hard_notes.get(code, "")
        print(f"  {code}: {'PASS' if ok else 'FAIL'}" + (f"  ({note})" if note else ""))
    print(f"  first_hard_fail: {result.first_hard_fail}")

    print("\n--- setup gates ---")
    print(f"  TC-01: {result.setup_tc01}   TC-02: {result.setup_tc02}   TC-04 tag: {result.setup_tc04}")

    print("\n--- watch flags ---")
    for code, active in result.watch_flags.items():
        if active:
            print(f"  {code}: {result.watch_notes.get(code, 'active')}")
    print(f"  cap: {result.watch_cap}")

    if not result.hard_gates_passed or not result.has_setup:
        print("\n(stops here — no hard-gate pass + active setup, so no trade plan/decision)")
        return

    plan, other, reason = entry.choose_plan(ctx, result, cfg.tick_size)
    print(f"\n--- entry plan ---\n  {plan}\n  reason: {reason}")
    if other:
        print(f"  other plan: {other}")

    ds_result = ds_mod.compute(ctx)
    print(f"\n--- demand/supply ---\n  {ds_result}")

    sz = sizing.size_position(cfg, plan.entry, plan.stop, vix_above_threshold=False)
    print(f"\n--- sizing ---\n  {sz}")

    dec = decision.classify(ctx, result, plan, sz, ds_result, earnings_map.get(symbol), regime_downgrade_active=False)
    print(f"\n--- decision (regime downgrade not applied here) ---\n  {dec}")

    last = ctx.daily.iloc[-1]
    print(f"\n--- candles ---\n  {patterns.summarize(ctx.daily, float(last['sma20']), float(last['sma50']), ctx.h_value)}")
    print(f"  weekly: {patterns.weekly_candle_note(ctx.weekly)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect one stock's full gate/decision breakdown")
    parser.add_argument("--market", choices=list(MARKETS.keys()), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--fresh", action="store_true", help="bypass cache, pull fresh data")
    args = parser.parse_args()
    inspect(args.market, args.symbol, args.fresh)


if __name__ == "__main__":
    main()
