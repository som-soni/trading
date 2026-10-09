"""Behaviour-preservation harness for EVERY strategy, on frozen data.

Like `golden_baseline.py` (trend pullback only), but covering all registered
strategies, and with each symbol's history cut at AS_OF so that the daily price
load cannot change the snapshot. Record before a refactor, check after:

    PYTHONPATH=. python3 -m tests.golden_strategies --write
    PYTHONPATH=. python3 -m tests.golden_strategies --check

A clean check means every strategy produced exactly the same pre-filter result,
gates, flags, setups, entry signal, plan, sizing and decision for every sampled
symbol in both markets.
"""

import argparse
import json
import random
from pathlib import Path

import pandas as pd

from swing_screener.config import MARKETS
from swing_screener.marketdata import cache, universe

BASELINE_PATH = Path(__file__).resolve().parent / "golden_strategies.json"
SAMPLE_PER_MARKET = 120
SEED = 4321
AS_OF = pd.Timestamp("2026-09-30")


def _r(x, n=6):
    try:
        return None if x is None or x != x else round(float(x), n)
    except (TypeError, ValueError):
        return str(x)


def _sample(market: str) -> dict[str, pd.DataFrame]:
    tickers = sorted(universe.load_universe(market))
    random.Random(SEED).shuffle(tickers)
    out = {}
    for sym in tickers:
        if len(out) >= SAMPLE_PER_MARKET:
            break
        raw = cache.load_cached(market, sym)
        if raw is None:
            continue
        raw = raw[raw.index <= AS_OF]
        if len(raw) >= 300:
            out[sym] = raw
    return dict(sorted(out.items()))


def _snap(strategy, cfg, symbol: str, raw: pd.DataFrame) -> dict:
    from swing_screener.core import context as ctx_mod, indicators as ind, sizing
    enriched = ind.enrich_daily(raw)
    ok, why = strategy.passes_prefilter(cfg, enriched)
    snap = {"prefilter": [bool(ok), why]}
    ctx = ctx_mod.build_context(symbol, raw)
    if ctx is None:
        snap["context"] = None
        return snap
    res = strategy.evaluate(ctx)
    snap.update({
        "hard_gates": {k: bool(v) for k, v in sorted(res.hard_gates.items())},
        "first_hard_fail": res.first_hard_fail,
        "watch_flags": {k: bool(v) for k, v in sorted(res.watch_flags.items())},
        "setups": {k: bool(v) for k, v in sorted(res.setups.items())},
        "watch_cap": strategy.watch_cap(res),
        "signal": bool(strategy.entry_signal_fired(ctx, res)),
    })
    if res.has_setup:
        choice = strategy.build_plans(ctx, res, cfg)
        p = choice.chosen
        if p is not None:
            snap["plan"] = {"which": p.plan, "setup": p.setup, "entry": _r(p.entry), "stop": _r(p.stop), "target": _r(p.target),
                            "r": _r(p.r_multiple), "reason": choice.reason}
            sz = sizing.size_position(cfg, p.entry, p.stop, False)
            dec = strategy.classify(ctx, res, p, sz, None, False)
            snap["decision"] = {"label": dec.label_before, "reason": dec.reason, "quality": _r(dec.setup_quality)}
    return snap


def build() -> dict:
    from swing_screener.strategies import get_strategy, list_strategies
    out: dict = {}
    for market, cfg in MARKETS.items():
        sample = _sample(market)
        for key in list_strategies():
            strat = get_strategy(key)
            out[f"{market}/{key}"] = {s: _snap(strat, cfg, s, raw) for s, raw in sample.items()}
        print(f"{market}: {len(sample)} symbols × {len(list_strategies())} strategies")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    snap = json.loads(json.dumps(build(), sort_keys=True, default=str))
    if a.write:
        BASELINE_PATH.write_text(json.dumps(snap, indent=1, sort_keys=True))
        print(f"Wrote {BASELINE_PATH}")
        return
    base = json.loads(BASELINE_PATH.read_text())
    diffs = []
    for group in sorted(set(base) | set(snap)):
        b, c = base.get(group, {}), snap.get(group, {})
        for sym in sorted(set(b) | set(c)):
            if b.get(sym) != c.get(sym):
                for k in sorted(set(b.get(sym) or {}) | set(c.get(sym) or {})):
                    if (b.get(sym) or {}).get(k) != (c.get(sym) or {}).get(k):
                        diffs.append(f"{group}/{sym}.{k}: {(b.get(sym) or {}).get(k)!r} -> {(c.get(sym) or {}).get(k)!r}")
    if diffs:
        print(f"BEHAVIOUR CHANGED — {len(diffs)} difference(s):")
        for d in diffs[:80]:
            print("  " + d)
        raise SystemExit(1)
    print(f"IDENTICAL — {sum(len(v) for v in snap.values())} strategy × symbol snapshots match the baseline.")


if __name__ == "__main__":
    main()
