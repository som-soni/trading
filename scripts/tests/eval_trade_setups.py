"""Trade setups on the chart (the Trade setups layer): a golden set of backtest trades and invariants.

The chart draws a selected run's trades through each strategy's setups layer — `Strategy.setups_live`
(strategies/live_setups.py) for most, `MinerviniSpecStrategy.bases_live` for Minervini — anchored on the
run's trades: (fill date, initial stop). This checks that, for a trade a backtest actually made, the layer
draws the setup the run traded, where the run traded it.

1. **Golden set** (`golden_trade_setups.json`). Real trades from current-version backtest runs, with the
   run's own record pinned in the file (fill date, fill price, initial stop), so the case does not depend on
   the database. For each, the layer — fed only that trade as its anchor, on stored prices cut `AFTER_DAYS`
   past the fill — must return a setup that
   - covers the fill date (the one the chart picks: judged on the traded bar if any), and is of an
     expected kind (`pass`; Minervini's `vcp` / `cheat`), not drawn as skipped;
   - draws its stop at the run's initial stop (within `stop_tol_pct`, default 0.5%);
   - draws its buy at or below the fill, within `buy_tol_pct` (default 0.5%): a buy-stop fills at its level
     or above it (a gap, or an order that waited for a free slot), never below. The stop match is what
     pins the bar; this catches a buy drawn above where the run actually bought. A strategy that buys at
     the next open (`AT_OPEN`) may fill on either side: within 5% of its buy;
   - carries the expected setup name when the case gives one (`title` substring).
   A case may carry `known` (why the layer does not draw it yet): reported as KNOWN, never failing.

2. **Invariants**, on every setup the golden runs return: the frame contains its zones; a setup's
   from <= to; an entry zone draws buy > stop and target > buy; every box has top >= bottom.

Run from scripts/ (a few minutes; one process per case):

    PYTHONPATH=. .venv/bin/python -m tests.eval_trade_setups
    PYTHONPATH=. .venv/bin/python -m tests.eval_trade_setups --case breakout-us-AAPL-2019-06-04 -v
"""

from __future__ import annotations

import argparse
import json
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind
from swing_screener.marketdata import cache
from swing_screener.strategies import get_strategy

GOLDEN = Path(__file__).resolve().parent / "golden_trade_setups.json"
BEFORE_YEARS = 4     # history before the fill the layer sees (warm-up for the 200-day and the 52-week tests)
AFTER_DAYS = 90      # bars after the fill, so an episode can run on past the trade as it does on the chart
KINDS = {"minervini": ["vcp", "cheat"]}   # a traded setup's kind, where a strategy's layer names its own
AT_OPEN = {"rs_leaders", "minervini"}   # bought at the next open (a market order), not a buy-stop: the fill may be below the buy


def case_id(c: dict) -> str:
    return f"{c['strategy']}-{c['market']}-{c['symbol']}-{c['entry']}"


def levels(setup: dict) -> dict:
    """The setup's entry-zone levels by role (buy, stop, target), first drawn of each."""
    out = {}
    for z in setup.get("zones", []):
        for sh in z.get("shapes", []):
            if sh.get("shape") == "level" and sh.get("role") in ("buy", "stop", "target"):
                out.setdefault(sh["role"], float(sh["price"]))
    return out


def setups_for(c: dict) -> list[dict]:
    strat = get_strategy(c["strategy"])
    cfg = MARKETS[c["market"]]
    raw = cache.load_cached(c["market"], c["symbol"])
    if raw is None or raw.empty:
        raise RuntimeError(f"no prices stored for {c['symbol']}")
    fill = pd.Timestamp(c["entry"])
    raw = raw[(raw.index >= fill - pd.DateOffset(years=BEFORE_YEARS)) & (raw.index <= fill + pd.Timedelta(days=AFTER_DAYS))]
    anchors = [{"entry": c["entry"], "stop": c["stop"], "price": c["price"]}]
    if hasattr(strat, "bases_live"):
        return strat.bases_live(ind.enrich_daily(raw), cfg, anchors)
    return strat.setups_live(raw, cfg, c["symbol"], 2, anchors)


def invariants(s: dict) -> list[str]:
    bad = []
    f = s.get("frame") or {}
    if s["base_from"] > s["to"]:
        bad.append(f"from {s['base_from']} after to {s['to']}")
    for z in s.get("zones", []):
        if f and (z.get("from", f["from"]) < f["from"] or z.get("to", f["to"]) > f["to"]):
            bad.append(f"zone {z.get('title', '?')} {z.get('from')}..{z.get('to')} outside frame {f['from']}..{f['to']}")
        for sh in z.get("shapes", []):
            if sh.get("shape") == "box" and float(sh["top"]) < float(sh["bottom"]):
                bad.append(f"box top {sh['top']} below bottom {sh['bottom']}")
    lv = levels(s)
    if "buy" in lv and "stop" in lv and not lv["buy"] > lv["stop"]:
        bad.append(f"buy {lv['buy']:.2f} not above stop {lv['stop']:.2f}")
    if "buy" in lv and "target" in lv and not lv["target"] > lv["buy"]:
        bad.append(f"target {lv['target']:.2f} not above buy {lv['buy']:.2f}")
    return bad


def check(c: dict) -> dict:
    out = {"id": case_id(c), "fails": [], "invariants": [], "known": c.get("known"), "got": None}
    try:
        S = setups_for(c)
    except Exception as e:  # noqa: BLE001 — reported as the case's failure
        out["fails"].append(f"error: {e!r}"[:200])
        return out
    for s in S:
        out["invariants"] += [f"{s.get('title', '?')} {s['base_from']}: {b}" for b in invariants(s)]
    cover = [s for s in S if s["base_from"] <= c["entry"] <= s["to"]]
    kinds = c.get("kinds", KINDS.get(c["strategy"], ["pass"]))
    good = [s for s in cover if s["kind"] in kinds]
    # as the chart picks it (studies.js ownerMap): the setup judged on the traded bar, else the latest passing
    own = next((s for s in cover if s.get("anchored")), None) or (good or cover or [None])[-1]
    if own is None:
        out["fails"].append(f"no setup covers the fill {c['entry']} ({len(S)} setups)")
        return out
    lv = levels(own)
    out["got"] = {"kind": own["kind"], "title": own.get("title"), "from": own["base_from"], "to": own["to"], **lv}
    if own["kind"] not in kinds:
        out["fails"].append(f"kind {own['kind']}, expected one of {kinds}")
    elif "skipped" in (own.get("title") or ""):
        out["fails"].append(f"drawn as {own['title']!r}, but the run traded it")
    if "stop" not in lv:
        out["fails"].append("no stop drawn")
    elif abs(lv["stop"] / c["stop"] - 1) * 100 > c.get("stop_tol_pct", 0.5):
        out["fails"].append(f"stop {lv['stop']:.2f} vs run's initial stop {c['stop']:.2f}")
    if "buy" not in lv:
        out["fails"].append("no buy drawn")
    elif (abs(lv["buy"] / c["price"] - 1) * 100 > c.get("buy_tol_pct", 5.0) if c["strategy"] in AT_OPEN
          else (lv["buy"] / c["price"] - 1) * 100 > c.get("buy_tol_pct", 0.5)):
        out["fails"].append(f"buy {lv['buy']:.2f} vs fill {c['price']:.2f}")
    if c.get("title") and c["title"].lower() not in (own.get("title") or "").lower():
        out["fails"].append(f"title {own.get('title')!r}, expected {c['title']!r}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--case", help="one case id (strategy-market-symbol-entry)")
    ap.add_argument("--strategy", help="only this strategy's cases")
    ap.add_argument("-v", action="store_true", help="print what each case drew")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    cases = json.loads(GOLDEN.read_text())["cases"]
    cases = [c for c in cases if (not a.case or case_id(c) == a.case) and (not a.strategy or c["strategy"] == a.strategy)]
    with Pool(a.workers) as p:
        res = p.map(check, cases)
    failed = known = bad_inv = 0
    by: dict = {}
    for c, r in zip(cases, res):
        st = by.setdefault(c["strategy"], [0, 0])
        st[1] += 1
        if r["invariants"]:
            bad_inv += 1
            for b in r["invariants"]:
                print(f"INVARIANT {r['id']}: {b}")
        if r["fails"] and r["known"]:
            known += 1
            print(f"KNOWN     {r['id']}: {'; '.join(r['fails'])}  ({r['known']})")
        elif r["fails"]:
            failed += 1
            print(f"FAIL      {r['id']}: {'; '.join(r['fails'])}")
        else:
            st[0] += 1
        if a.v:
            print(f"          drew {r['got']}")
    for k, (ok, n) in sorted(by.items()):
        print(f"{k:16s} {ok}/{n}")
    print(f"{len(cases)} cases: {len(cases) - failed - known} pass, {failed} fail, {known} known; "
          f"{bad_inv} with invariant breaks")
    return 1 if failed or bad_inv else 0


if __name__ == "__main__":
    sys.exit(main())
