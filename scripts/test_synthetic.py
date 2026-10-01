"""Quick smoke test of the entry/sizing/decision/demand-supply code paths
using synthetic OHLCV data engineered to pass the hard gates and form a
TC-01 pullback setup. Not a proper test suite — just a fast way to
exercise code that real market data didn't happen to reach in the small
manual smoke test.
"""

import numpy as np
import pandas as pd

from swing_screener import gates, entry, demand_supply as ds_mod, sizing, decision
from swing_screener.config import US_CONFIG

np.random.seed(7)
n = 500
dates = pd.bdate_range("2023-01-02", periods=n)

# Strong steady uptrend with a recent shallow pullback that has started to
# resume — should pass M1/W1/W2/T1-T6 and form a TC-01 setup.
base = 100 + np.cumsum(np.random.normal(0.25, 1.0, n))
base = np.maximum(base, 10)

# carve a clean impulse + pullback + resumption into the last 30 bars
base[-30:-10] = base[-31] + np.linspace(0, 20, 20)  # impulse up
base[-10:-2] = base[-11] - np.linspace(0, 8, 8)  # pullback ~40% of impulse
base[-2:] = base[-3] + np.linspace(1, 3, 2)  # resumption bar closes higher

close = base
high = close + np.random.uniform(0.3, 1.2, n)
low = close - np.random.uniform(0.3, 1.2, n)
open_ = close + np.random.uniform(-0.5, 0.5, n)
volume = np.random.randint(1_000_000, 3_000_000, n).astype(float)
volume[-10:-2] *= 0.6  # contracting volume on the pullback

df = pd.DataFrame(
    {"open": open_, "high": high, "low": low, "close": close, "volume": volume},
    index=dates,
)
df["high"] = df[["open", "high", "close"]].max(axis=1)
df["low"] = df[["open", "low", "close"]].min(axis=1)

ctx = gates.build_context("SYN", df, earnings_days_away=None)
assert ctx is not None, "context build failed"
print(f"H={ctx.h_value:.2f} L={ctx.l_value:.2f} P={ctx.p_value:.2f} "
      f"prior_swing_low={ctx.prior_swing_low}")

result = gates.compute_gates(ctx)
print("hard gates:", result.hard_gates)
print("first_hard_fail:", result.first_hard_fail)
print("setup TC-01/TC-02/TC-04:", result.setup_tc01, result.setup_tc02, result.setup_tc04)
print("watch flags:", {k: v for k, v in result.watch_flags.items() if v})

if result.hard_gates_passed and result.has_setup:
    plan, other, reason = entry.choose_plan(ctx, result, US_CONFIG.tick_size)
    print(f"\nplan: {plan}")
    print(f"reason: {reason}")

    ds_result = ds_mod.compute(ctx)
    print(f"\ndemand/supply: {ds_result}")

    sz = sizing.size_position(US_CONFIG, plan.entry, plan.stop, vix_above_threshold=False)
    print(f"\nsizing: {sz}")

    dec = decision.classify(ctx, result, plan, sz, ds_result, None, regime_downgrade_active=False)
    print(f"\ndecision: {dec}")

    from swing_screener import patterns
    last = ctx.daily.iloc[-1]
    print(
        "\ncandles:",
        patterns.summarize(ctx.daily, float(last["sma20"]), float(last["sma50"]), ctx.h_value),
    )
    print("\nOK — full reviewed-stock code path executed without error")
else:
    print("\nSynthetic data did not pass hard gates / form a setup — adjust the fixture")
