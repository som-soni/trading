"""Re-record a strategy's golden trade-setup cases (golden_trade_setups.json) from a backtest run.

A golden case pins one real trade of a run on the strategy's then-current rules -- its fill date, fill price and
initial stop, with the run id and spec_id -- so tests/eval_trade_setups.py can check the chart's Trade setups
layer draws that trade where the run made it. When the rules change (a new spec_id) old cases drift; this
replaces the strategy's cases in one market with a seeded sample of a run of the CURRENT rules: the current
spec_id, or a run of the version the strategy pins as its `signal_version` -- a version bump that changed only
what happens after the scan keeps the scan, and the layer draws the scan (minervini 1.52 changed only the results
blackout; its 1.51 runs are what the layer draws). It refuses a run of any other spec_id, and leaves every other
case untouched, including the reviewed symbols kept for other strategies.

`--per-setup K` samples K trades of each setup instead of N at random: a plain sample of a run dominated by one
setup leaves the rare ones untested (the first Minervini set had no power play, flat base or shakeout).

Run from scripts/:

    PYTHONPATH=. .venv/bin/python -m tests.record_golden_trade_setups --strategy minervini --market us
    PYTHONPATH=. .venv/bin/python -m tests.record_golden_trade_setups --strategy minervini --market india --run 1100 --dry-run
    PYTHONPATH=. .venv/bin/python -m tests.record_golden_trade_setups --strategy minervini --market us --per-setup 3
"""

from __future__ import annotations

import argparse
import json
import random
import sys

from swing_screener.strategies import get_strategy
from swing_screener.web.server import q, report_table

from .eval_trade_setups import GOLDEN, case_id

N = 21        # cases per strategy and market, as the first Minervini set
SEED = 7


def drawable(strat, spec_id: str | None) -> bool:
    """Is a run of `spec_id` on the rules the layer now draws: the current spec_id, or the version the strategy
    pins as its signal_version (the scan unchanged since)?"""
    pin = getattr(strat, "signal_version", None)
    return bool(spec_id) and (spec_id == strat.spec_id() or (pin is not None and pin != strat.version
                                                               and spec_id.split("-")[0] == f"v{pin}"))


def current_run(strat, strategy: str, market: str) -> int | None:
    """The latest staged backtest of this strategy and market on drawable rules (`drawable`) with no --const/--vcp
    override (a variant trades rules the layer does not draw): the current spec_id first, the optimise stage first."""
    rows = q("SELECT id, spec_id FROM report_runs WHERE strategy=%s AND market=%s AND stage IS NOT NULL "
             "AND (overrides IS NULL OR overrides::text IN ('{}', 'null')) "
             "ORDER BY (spec_id = %s) DESC, (stage = 'optimise') DESC, id DESC", (strategy, market, strat.spec_id()))
    return next((r[0] for r in rows if drawable(strat, r[1])), None)


def sample(run: int, strategy: str, market: str, spec_id: str, n: int, seed: int, per_setup: int = 0) -> list[dict]:
    t = report_table(run, "trades", None)
    cols = t["columns"]
    rows = [dict(zip(cols, r)) for r in t["rows"]]
    rows = [r for r in rows if r.get("entry_date") and r.get("entry_price") and (r.get("initial_stop") or r.get("stop"))]
    rows.sort(key=lambda r: (str(r["entry_date"]), r["symbol"]))
    random.Random(seed).shuffle(rows)
    if per_setup:
        by: dict = {}
        for r in rows:
            by.setdefault(r.get("setup"), []).append(r)
        rows = [r for k in sorted(by, key=str) for r in by[k][:per_setup]]
    else:
        rows = rows[:n]
    out = []
    for r in rows:
        out.append({"strategy": strategy, "market": market, "symbol": r["symbol"], "entry": str(r["entry_date"])[:10],
                    "price": round(float(r["entry_price"]), 4),
                    "stop": round(float(r.get("initial_stop") or r["stop"]), 4), "run": run, "spec_id": spec_id,
                    **({"setup": r["setup"]} if r.get("setup") else {})})
    return sorted(out, key=lambda c: (c["entry"], c["symbol"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--run", type=int, help="a run id (default: the latest plain run of the current spec_id)")
    ap.add_argument("-n", type=int, default=N)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--per-setup", type=int, default=0, help="sample this many trades of each setup instead of -n")
    ap.add_argument("--dry-run", action="store_true", help="print the cases, write nothing")
    a = ap.parse_args()
    strat = get_strategy(a.strategy)
    spec = strat.spec_id()
    run = a.run or current_run(strat, a.strategy, a.market)
    if run is None:
        print(f"no {a.market} run of {a.strategy} on {spec} yet: queue one, or pass --run")
        return 1
    got = q("SELECT spec_id FROM report_runs WHERE id=%s", (run,))
    if a.run and (not got or not drawable(strat, got[0][0])):
        print(f"run {run} is {got[0][0] if got else 'unknown'}, not the current {spec} (or its signal_version): its "
              f"trades are not what the layer now draws")
        if not a.dry_run:
            return 1
    cases = sample(run, a.strategy, a.market, got[0][0] if got else spec, a.n, a.seed, a.per_setup)
    data = json.loads(GOLDEN.read_text())
    kept = [c for c in data["cases"] if not (c["strategy"] == a.strategy and c["market"] == a.market)]
    print(f"run {run}: {len(cases)} cases replace {len(data['cases']) - len(kept)} for {a.strategy} {a.market}")
    for c in cases:
        print(f"  {case_id(c)}  fill {c['price']}  stop {c['stop']}")
    if a.dry_run:
        return 0
    data["cases"] = kept + cases
    GOLDEN.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
