"""The built-in screens, written as conditions over the snapshot, must return exactly the stocks that their
coded criteria (screens/criteria.py — the code the strategies use) pass.

    PYTHONPATH=. python3 -m tests.test_screen_definitions            # both markets, latest snapshot
"""

import sys
from types import SimpleNamespace

import pandas as pd

from swing_screener.core import indicators as ind
from swing_screener.marketdata import cache
from swing_screener.screens import SCREENS, definitions, snapshot
from swing_screener.screens import criteria as crit


def check(market: str) -> list[str]:
    snap = snapshot.load(market)
    if snap.empty:
        return [f"{market}: no snapshot — run: python -m jobs run screens --market {market}"]
    d = pd.Timestamp(snap.attrs["date"])
    tradable = snap[snap["tradable"]]
    rank = dict(zip(snap["symbol"], snap["rs_rank"]))
    with cache.offline():
        bars = cache.load_many_cached(market, list(tradable["symbol"]), since=d - pd.Timedelta(days=snapshot.LOOKBACK_DAYS))
    coded: dict[str, set] = {k: set() for k in SCREENS}
    for sym, raw in bars.items():
        raw = raw[raw.index <= d]
        daily = ind.enrich_daily(raw)
        ctx = SimpleNamespace(daily=daily, weekly=ind.enrich_weekly(ind.resample_weekly(raw)), last=daily.iloc[-1],
                              close=float(daily["close"].iloc[-1]), extras={})
        for key, sc in SCREENS.items():
            crits = sc.criteria[:-1] if sc.rank_rs else sc.criteria
            ok = all(cr.fn(ctx)[0] for cr in crits)
            if sc.rank_rs:
                r = rank.get(sym)
                ok = ok and r is not None and r == r and r >= crit.RS_MIN_RANK
            if ok:
                coded[key].add(sym)
    problems = []
    for key, defn in definitions.builtin().items():
        got = set(snap.loc[definitions.mask(snap, defn["conditions"]), "symbol"])
        if got != coded[key]:
            problems.append(f"{market}/{key}: conditions give {len(got)}, criteria give {len(coded[key])}; "
                            f"only by conditions {sorted(got - coded[key])[:8]}, only by criteria {sorted(coded[key] - got)[:8]}")
        else:
            print(f"{market}/{key}: {len(got)} stocks — identical")
    return problems


if __name__ == "__main__":
    probs = [p for m in ("us", "india") for p in check(m)]
    print("\n".join(probs) or "OK — every built-in screen's conditions match its coded criteria exactly")
    sys.exit(1 if probs else 0)
