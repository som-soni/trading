"""Re-record a strategy's golden trade-setup cases (golden_trade_setups.json) from a backtest run.

A golden case pins one real trade of a run on the strategy's then-current rules -- its fill date, fill price and
initial stop, with the run id and spec_id -- so tests/eval_trade_setups.py can check the chart's Trade setups
layer draws that trade where the run made it. When the rules change (a new spec_id) old cases drift; this
replaces the strategy's cases in one market with a seeded sample of a run of the CURRENT spec_id. It refuses a
run of any other spec_id (record from the rules the layer now draws), and leaves every other case untouched,
including the reviewed symbols kept for other strategies.

Run from scripts/:

    PYTHONPATH=. .venv/bin/python -m tests.record_golden_trade_setups --strategy minervini --market us
    PYTHONPATH=. .venv/bin/python -m tests.record_golden_trade_setups --strategy minervini --market india --run 1100 --dry-run
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


def current_run(strategy: str, market: str, spec_id: str) -> int | None:
    """The latest staged backtest of this strategy and market on `spec_id` with no --const/--vcp override (a
    variant trades rules the layer does not draw), the optimise stage first."""
    rows = q("SELECT id FROM report_runs WHERE strategy=%s AND market=%s AND spec_id=%s AND stage IS NOT NULL "
             "AND (overrides IS NULL OR overrides::text IN ('{}', 'null')) "
             "ORDER BY (stage = 'optimise') DESC, id DESC LIMIT 1", (strategy, market, spec_id))
    return rows[0][0] if rows else None


def sample(run: int, strategy: str, market: str, spec_id: str, n: int, seed: int) -> list[dict]:
    t = report_table(run, "trades", None)
    cols = t["columns"]
    rows = [dict(zip(cols, r)) for r in t["rows"]]
    rows = [r for r in rows if r.get("entry_date") and r.get("entry_price") and (r.get("initial_stop") or r.get("stop"))]
    rows.sort(key=lambda r: (str(r["entry_date"]), r["symbol"]))
    random.Random(seed).shuffle(rows)
    out = []
    for r in rows[:n]:
        out.append({"strategy": strategy, "market": market, "symbol": r["symbol"], "entry": str(r["entry_date"])[:10],
                    "price": round(float(r["entry_price"]), 4),
                    "stop": round(float(r.get("initial_stop") or r["stop"]), 4), "run": run, "spec_id": spec_id})
    return sorted(out, key=lambda c: (c["entry"], c["symbol"]))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strategy", required=True)
    ap.add_argument("--market", required=True)
    ap.add_argument("--run", type=int, help="a run id (default: the latest plain run of the current spec_id)")
    ap.add_argument("-n", type=int, default=N)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--dry-run", action="store_true", help="print the cases, write nothing")
    a = ap.parse_args()
    spec = get_strategy(a.strategy).spec_id()
    run = a.run or current_run(a.strategy, a.market, spec)
    if run is None:
        print(f"no {a.market} run of {a.strategy} on {spec} yet: queue one, or pass --run")
        return 1
    got = q("SELECT spec_id FROM report_runs WHERE id=%s", (run,))
    if a.run and (not got or got[0][0] != spec):
        print(f"run {run} is {got[0][0] if got else 'unknown'}, not the current {spec}: its trades are not what the "
              f"layer now draws")
        if not a.dry_run:
            return 1
    cases = sample(run, a.strategy, a.market, got[0][0] if got else spec, a.n, a.seed)
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
