"""Behaviour-preservation harness for refactors.

Captures the full gate/flag/setup/plan/decision output for a fixed sample
of real cached symbols into a JSON file. Run it BEFORE a refactor to
record a baseline, then again AFTER to diff — any unintended behaviour
change shows up as a field-level difference instead of being discovered
later in a backtest.

    python3 -m tests.golden_baseline --write    # record baseline
    python3 -m tests.golden_baseline --check    # compare against baseline
"""

import argparse
import json
import random
from pathlib import Path

from swing_screener.marketdata import cache, universe
from swing_screener.config import MARKETS

BASELINE_PATH = Path(__file__).resolve().parent / "golden_baseline.json"
SAMPLE_PER_MARKET = 150
SEED = 1234


def _sample_symbols(market: str, n: int) -> list[str]:
    # sort BEFORE shuffling: a seeded shuffle depends on the input order, so
    # sampling straight off the universe file silently picks a different set
    # whenever that file is refreshed, making an old baseline incomparable
    tickers = sorted(universe.load_universe(market))
    rng = random.Random(SEED)
    rng.shuffle(tickers)
    out = []
    for sym in tickers:
        if len(out) >= n:
            break
        raw = cache.load_cached(market, sym)
        if raw is not None and len(raw) >= 260:
            out.append(sym)
    return sorted(out)


def _snapshot_symbol(market: str, symbol: str, strategy_key: str = "trend_pullback") -> dict | None:
    """Everything a refactor could plausibly change, flattened.

    Key names are frozen deliberately (setup_tc01 etc.) so a baseline
    recorded before the strategy extraction still compares cleanly against
    one recorded after it."""
    from swing_screener.core import context as ctx_mod, demand_supply as ds_mod, sizing
    from swing_screener.strategies import get_strategy

    cfg = MARKETS[market]
    strategy = get_strategy(strategy_key)
    raw = cache.load_cached(market, symbol)
    ctx = ctx_mod.build_context(symbol, raw)
    if ctx is None:
        return {"symbol": symbol, "context": None}

    result = strategy.evaluate(ctx)
    snap = {
        "symbol": symbol,
        "close": round(ctx.close, 6),
        "h_value": round(ctx.h_value, 6),
        "l_value": round(ctx.l_value, 6),
        "p_value": round(ctx.p_value, 6),
        "prior_swing_low": round(ctx.prior_swing_low, 6) if ctx.prior_swing_low is not None else None,
        "overhead_count": len(ctx.overhead),
        "overhead_head": [round(x, 6) for x in ctx.overhead[:10]],
        "hard_gates": dict(sorted(result.hard_gates.items())),
        "first_hard_fail": result.first_hard_fail,
        "watch_flags": {k: bool(v) for k, v in sorted(result.watch_flags.items())},
        "watch_notes": dict(sorted(result.watch_notes.items())),
        "setup_tc01": result.setups.get("TC-01", False),
        "setup_tc02": result.setups.get("TC-02", False),
        "setup_tc04": result.setups.get("TC-04", False),
        "watch_cap": strategy.watch_cap(result),
        "signal_present": strategy.entry_signal_fired(ctx, result),
    }

    if result.has_setup:
        choice = strategy.build_plans(ctx, result, cfg)
        plan, reason = choice.chosen, choice.reason
        if plan is not None:
            snap["plan"] = {
                "which": plan.plan, "setup": plan.setup,
                "entry": round(plan.entry, 6), "stop": round(plan.stop, 6),
                "target": round(plan.target, 6),
                "r_multiple": round(plan.r_multiple, 6) if plan.r_multiple == plan.r_multiple else None,
                "reason": reason,
            }
            ds = ds_mod.compute(ctx)
            snap["demand_supply"] = {"verdict": ds.verdict, "score": ds.score}
            sz = sizing.size_position(cfg, plan.entry, plan.stop, False)
            snap["sizing"] = {"shares": sz.shares, "too_large": sz.too_large}
            dec = strategy.classify(ctx, result, plan, sz, None, False)
            snap["decision"] = {
                "label": dec.label_before,
                "reason": dec.reason,
                "setup_quality": dec.setup_quality,
            }
    return snap


def build_snapshot() -> dict:
    out: dict = {}
    for market in MARKETS:
        syms = _sample_symbols(market, SAMPLE_PER_MARKET)
        out[market] = [_snapshot_symbol(market, s) for s in syms]
        print(f"{market}: snapshotted {len(out[market])} symbols")
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    snap = build_snapshot()

    if args.write:
        BASELINE_PATH.write_text(json.dumps(snap, indent=2, sort_keys=True, default=str))
        print(f"Wrote baseline to {BASELINE_PATH}")
        return

    if args.check:
        if not BASELINE_PATH.exists():
            print("No baseline recorded yet — run with --write first.")
            return
        baseline = json.loads(BASELINE_PATH.read_text())
        current = json.loads(json.dumps(snap, sort_keys=True, default=str))
        diffs = []
        for market in sorted(set(baseline) | set(current)):
            b_by_sym = {r["symbol"]: r for r in baseline.get(market, [])}
            c_by_sym = {r["symbol"]: r for r in current.get(market, [])}
            for sym in sorted(set(b_by_sym) | set(c_by_sym)):
                b, c = b_by_sym.get(sym), c_by_sym.get(sym)
                if b != c:
                    for key in sorted(set(b or {}) | set(c or {})):
                        if (b or {}).get(key) != (c or {}).get(key):
                            diffs.append(f"{market}/{sym}.{key}: {(b or {}).get(key)!r} -> {(c or {}).get(key)!r}")
        if diffs:
            print(f"BEHAVIOUR CHANGED — {len(diffs)} field difference(s):")
            for d in diffs[:60]:
                print(f"  {d}")
            if len(diffs) > 60:
                print(f"  ... and {len(diffs) - 60} more")
        else:
            print("IDENTICAL — no behaviour change across the sampled universe.")


if __name__ == "__main__":
    main()
