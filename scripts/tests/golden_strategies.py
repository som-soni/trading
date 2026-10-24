"""Behaviour-preservation harness for EVERY strategy, on frozen data.

Covers all registered strategies, with each symbol's history cut at AS_OF so
that the daily price load cannot change the snapshot. (It replaced an older
trend-pullback-only harness that read live prices and drifted daily.) Record
before a refactor, check after:

    PYTHONPATH=. python3 -m tests.golden_strategies --write
    PYTHONPATH=. python3 -m tests.golden_strategies --check

A clean check means every strategy produced exactly the same pre-filter result,
gates, flags, setups, entry signal, plan, sizing and decision for every sampled
symbol in both markets.

The sampled symbols are stored in the baseline (`_symbols`) and a check re-uses
that exact list: re-sampling from the universe file on every check made any
universe update swap most of the sample and fail the check with no behaviour
change at all.
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


def _sample(market: str, symbols: list[str] | None = None) -> dict[str, pd.DataFrame]:
    """The market's sample: `symbols` (the baseline's own list) when given, else SAMPLE_PER_MARKET drawn
    from the universe with SEED."""
    if symbols is not None:
        out = {}
        for sym in symbols:
            raw = cache.load_cached(market, sym)
            if raw is not None:
                out[sym] = raw[raw.index <= AS_OF]
        return dict(sorted(out.items()))
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


def build(symbols: dict | None = None) -> dict:
    """Every strategy × sampled symbol snapshot, plus the sample itself under `_symbols`."""
    from swing_screener.strategies import get_strategy, list_strategies
    out: dict = {"_symbols": {}}
    for market, cfg in MARKETS.items():
        sample = _sample(market, (symbols or {}).get(market))
        out["_symbols"][market] = list(sample)
        for key in list_strategies():
            strat = get_strategy(key)
            out[f"{market}/{key}"] = {s: _snap(strat, cfg, s, raw) for s, raw in sample.items()}
        print(f"{market}: {len(sample)} symbols × {len(list_strategies())} strategies")
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--resample", action="store_true",
                    help="with --write: draw a fresh sample from the universe instead of keeping the baseline's")
    a = ap.parse_args()
    stored = json.loads(BASELINE_PATH.read_text()) if BASELINE_PATH.exists() else None
    base = None if a.write else stored
    if base is not None and "_symbols" not in base:
        raise SystemExit("The baseline predates stored samples — record it again with --write.")
    # --write keeps the baseline's own sample too. Re-recording is for new VALUES on the same
    # stocks; drawing afresh from the universe file swapped most of the sample whenever the
    # universe had been refreshed since the last write -- the trap the check side was fixed for,
    # left open on this side -- so a two-row behaviour change (chart_pattern 1.13, two double
    # bottoms) re-recorded as a 26,000-line diff over a different 120 stocks a market, and the
    # check that followed passed against itself. --resample draws afresh, on purpose.
    keep = None if (a.write and a.resample) else (stored or {}).get("_symbols")
    snap = json.loads(json.dumps(build(keep), sort_keys=True, default=str))
    if a.write:
        BASELINE_PATH.write_text(json.dumps(snap, indent=1, sort_keys=True))
        print(f"Wrote {BASELINE_PATH}")
        return
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
    print(f"IDENTICAL — {sum(len(v) for k, v in snap.items() if k != '_symbols')} strategy × symbol snapshots match the baseline.")


if __name__ == "__main__":
    main()
