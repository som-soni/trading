"""Manual query/debug tool for a single stock: pulls (or reuses cached)
bars, runs the full strategy evaluation for it, and prints every gate,
watch flag, the trade plan, sizing and decision. Answers "why did/didn't
this stock show up?" without re-running the whole universe.

Usage:
    python3 -m swing_screener.screening.inspect --market india --symbol RELIANCE.NS
    python3 -m swing_screener.screening.inspect --market us --symbol AAPL --strategy breakout
    python3 -m swing_screener.screening.inspect --market us --symbol AAPL --fresh
"""

import argparse

from ..marketdata import cache, earnings

from ..core import context as ctx_mod, indicators as ind, patterns, sizing
from ..config import MARKETS
from .pipeline import LOOKBACK_DAYS
from ..providers import YFinanceProvider
from ..strategies import DEFAULT_STRATEGY, get_strategy, list_strategies


def inspect(market_key: str, symbol: str, fresh: bool = False, strategy_key: str = DEFAULT_STRATEGY) -> None:
    cfg = MARKETS[market_key]
    strategy = get_strategy(strategy_key)
    provider = YFinanceProvider()

    if fresh:
        raw = provider.get_daily_bars(symbol, LOOKBACK_DAYS)
        if raw is not None and not raw.empty:
            cache.save_cached(market_key, symbol, raw)
    else:
        raw = cache.get_bars(provider, market_key, symbol, LOOKBACK_DAYS)

    if raw is None or raw.empty:
        print(f"No data for {symbol}")
        return

    print(f"=== {symbol} ({market_key}) | strategy: {strategy.key} — {strategy.name} ===")
    print(f"{len(raw)} daily bars, {raw.index[0].date()} -> {raw.index[-1].date()}")
    print(raw.tail(5))

    enriched = ind.enrich_daily(raw)
    ok, why = strategy.passes_prefilter(cfg, enriched)
    print(f"\npre-filter: {'PASS' if ok else 'FAIL — ' + why}")

    earnings_map = earnings.load_earnings_days_away(market_key, [symbol])
    ctx = ctx_mod.build_context(symbol, raw, earnings_map.get(symbol))
    if ctx is None:
        print("\nInsufficient history to build a context")
        return

    print(f"\nclose={ctx.close:.2f}  H={ctx.h_value:.2f}  L={ctx.l_value:.2f}  P={ctx.p_value:.2f}")
    print(f"prior structural swing low: {ctx.prior_swing_low}")
    near = [lvl for lvl in ctx.overhead if ctx.close < lvl <= ctx.close * 1.03]
    print(f"overhead levels within 3% above: {near}")
    print(f"earnings in: {earnings_map.get(symbol, 'unknown')} trading days")

    result = strategy.evaluate(ctx)
    print("\n--- hard gates ---")
    for code, passed in result.hard_gates.items():
        note = result.hard_notes.get(code, "")
        print(f"  {code}: {'PASS' if passed else 'FAIL'}" + (f"  ({note})" if note else ""))
    print(f"  first_hard_fail: {result.first_hard_fail}")

    print("\n--- setups ---")
    for code in strategy.setup_codes:
        print(f"  {code}: {bool(result.setups.get(code))}")

    print("\n--- watch flags ---")
    for code in strategy.watch_codes:
        if result.watch_flags.get(code):
            print(f"  {code}: {result.watch_notes.get(code, 'active')}")
    print(f"  cap: {strategy.watch_cap(result)}")
    print(f"  entry signal fired: {strategy.entry_signal_fired(ctx, result)}")

    if not result.hard_gates_passed or not result.has_setup:
        print("\n(stops here — needs all hard gates passing AND an active setup)")
        return

    choice = strategy.build_plans(ctx, result, cfg)
    print(f"\n--- entry plan ---\n  {choice.chosen}\n  reason: {choice.reason}")
    if choice.alternate:
        print(f"  alternate: {choice.alternate}")

    sz = sizing.size_position(cfg, choice.chosen.entry, choice.chosen.stop, vix_above_threshold=False)
    print(f"\n--- sizing ---\n  {sz}")

    dec = strategy.classify(ctx, result, choice.chosen, sz, earnings_map.get(symbol), False)
    print(f"\n--- decision (regime downgrade not applied here) ---\n  {dec}")

    extras = strategy.report_extras(ctx, result, choice.chosen)
    if extras:
        print("\n--- strategy extras ---")
        for k, v in extras.items():
            print(f"  {k}: {v}")

    last = ctx.daily.iloc[-1]
    print(
        "\n--- candles ---\n  "
        + patterns.summarize(ctx.daily, float(last["sma20"]), float(last["sma50"]), ctx.h_value)
    )
    print(f"  {patterns.weekly_candle_note(ctx.weekly)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect one stock's full gate/decision breakdown")
    parser.add_argument("--market", choices=list(MARKETS.keys()), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--strategy", default=DEFAULT_STRATEGY, choices=list_strategies())
    parser.add_argument("--fresh", action="store_true", help="bypass cache, pull fresh data")
    args = parser.parse_args()
    inspect(args.market, args.symbol, args.fresh, args.strategy)


if __name__ == "__main__":
    main()
