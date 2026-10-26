"""Every setup code must produce a plan and a meta without raising.

Twice now a cheat has crashed a run because a function SIBLING to the one I
changed assumed the pivot-buy's fields existed: build_plans wanted the final
tight area, then signal_meta did. Both read e["pivot"] unconditionally, and a
cheat has no final tight area because its base is still forming. Neither
degraded -- they raised, 5 symbols into a 902-symbol run.

This walks real history until it has seen every setup code at least once, and
puts each through build_plans and signal_meta.

A setup that reaches build_plans but never gets a plan (rejected by the 2:1
minimum every time) cannot reach signal_meta on real data. It is reported, not
failed: build_plans ran for it, and the note says signal_meta did not. The power
play (S5) is that case today -- its measured move is the flag's own range, which
is never more than its risk, so it projects at most 1R.

    PYTHONPATH=. .venv/bin/python -m tests.test_setup_plans
"""

import sys

import pandas as pd

from swing_screener.config import MARKETS
from swing_screener.core import context as ctx_mod
from swing_screener.marketdata import cache
from swing_screener.strategies import get_strategy

# NVDA/AVGO/LLY/BAJFINANCE give the cheats; the India names below are ones the
# volume-confirmed breakout (MV-01) is known to fire on, which is rare enough
# that a basket chosen for cheats alone never exercises it.
SYMBOLS = [("us", "NVDA"), ("us", "AVGO"), ("us", "LLY"), ("india", "BAJFINANCE.NS"),
           ("india", "TITAN.NS"), ("india", "COALINDIA.NS"), ("india", "CDSL.NS"),
           ("india", "TATAINVEST.NS"),
           # power plays (MV-05) that pass the hard gates: KRNT 2020-06-30, IRB 2020-08-19
           ("us", "KRNT"), ("india", "IRB.NS")]


def main() -> int:
    strat = get_strategy("minervini")
    # MV-03 is disabled by default (see its changelog entry), but the code path
    # still has to work -- that is exactly the kind of branch that rots unseen.
    import swing_screener.strategies.minervini_spec as ms
    ms.LOW_CHEAT_ENABLED = 1
    seen, built, no_plan, problems = {}, {}, {}, []
    for market, sym in SYMBOLS:
        cfg = MARKETS[market]
        raw = cache.load_cached(market, sym)
        if raw is None:
            continue
        frames = ctx_mod.prepare_frames(raw)
        mask = strat.prefilter_mask(cfg, frames.daily)
        for d in [x for x in raw.index if x >= pd.Timestamp("2013-01-01") and bool(mask.get(x, False))]:
            ctx = ctx_mod.build_context(sym, raw, frames=frames, as_of=d)
            if ctx is None:
                continue
            try:
                res = strat.evaluate(ctx)
            except Exception as exc:                                  # noqa: BLE001
                problems.append(f"{sym} {d.date()}: evaluate raised {type(exc).__name__}: {exc}")
                continue
            if not res.hard_gates_passed or not res.has_setup:
                continue
            code = next((c for c in strat.setup_codes if res.setups.get(c)), None)
            try:
                choice = strat.build_plans(ctx, res, cfg)
            except Exception as exc:                                  # noqa: BLE001
                problems.append(f"{sym} {d.date()} {code}: build_plans raised {type(exc).__name__}: {exc}")
                continue
            built[code] = built.get(code, 0) + 1
            plan = choice.chosen
            if plan is None:
                no_plan[code] = choice.reason
                continue
            try:
                meta = strat.signal_meta(ctx, res, plan)
            except Exception as exc:                                  # noqa: BLE001
                problems.append(f"{sym} {d.date()} {code}: signal_meta raised {type(exc).__name__}: {exc}")
                continue
            for key in ("pivot", "tight_low", "max_fill", "base_id"):
                if key not in meta:
                    problems.append(f"{sym} {d.date()} {code}: meta is missing {key!r}")
            if plan.stop >= plan.entry:
                problems.append(f"{sym} {d.date()} {code}: stop {plan.stop} is not below entry {plan.entry}")
            seen[code] = seen.get(code, 0) + 1

    missing = [c for c in strat.setup_codes if c not in built]
    if missing:
        problems.append(f"never exercised, so this test proved nothing for them: {missing}")
    planless = [c for c in strat.setup_codes if c in built and c not in seen]
    if problems:
        print("FAIL — setup/plan/meta:")
        for p in problems[:20]:
            print("  " + p)
        return 1
    print("OK — every setup code ran through build_plans; plan and meta built for: "
          + ", ".join(f"{c} x{n}" for c, n in sorted(seen.items())))
    for c in planless:
        print(f"NOTE — {c} reached build_plans {built[c]} times but never got a plan, so signal_meta is "
              f"untested for it (last reason: {no_plan[c]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
