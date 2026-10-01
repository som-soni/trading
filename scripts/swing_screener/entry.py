"""ENTRY RULES — trigger/entry/stop/target, Plan A (pullback) vs Plan B
(breakout), and the 'signal present' test used by STEP 6.

Limitation vs. the prompt: the prompt has a rule for the case where the
live/incomplete bar has already traded through the trigger intraday ('say
so but don't change the decision until a close confirms it'). This script
is EOD/batch — DATA RULE already drops the incomplete bar — so that
specific intraday check has no data to run on here. If you later add an
intraday quote check, that's where it plugs in.
"""

import math
from dataclasses import dataclass

from .gates import GateResult, StockContext
from . import swings as sw


def round_tick(value: float, tick: float, direction: str) -> float:
    if tick <= 0:
        return value
    if direction == "up":
        return math.ceil(round(value / tick, 6)) * tick
    return math.floor(round(value / tick, 6)) * tick


@dataclass
class TradePlan:
    plan: str  # "A" (pullback) or "B" (breakout)
    setup: str  # "TC-01" or "TC-02"
    entry: float
    stop: float
    target: float
    risk_per_share: float
    reward_per_share: float
    r_multiple: float
    nearest_overhead_above_entry: float | None


def active_setup(result: GateResult) -> str | None:
    """If both TC-01 and TC-02 are valid, TC-01 sets the stop and target."""
    if result.setup_tc01:
        return "TC-01"
    if result.setup_tc02:
        return "TC-02"
    return None


def resumption_signal(ctx: StockContext, setup: str) -> bool:
    d = ctx.daily
    close = ctx.close
    sma20 = d["sma20"].iloc[-1]
    if sma20 != sma20:  # NaN
        return False
    if setup == "TC-02":
        ref_high = d["high"].iloc[-11:-1].max()
    else:
        ref_high = d["high"].iloc[-2]
    return bool(close > ref_high and close > sma20)


def signal_present(ctx: StockContext, result: GateResult) -> bool:
    """'Signal present' for TRADE - HIGH CONFIDENCE: resumption fired on the
    last completed bar AND no overhead level (including H) lies within 3%
    above the close."""
    setup = active_setup(result)
    if setup is None:
        return False
    sig = resumption_signal(ctx, setup)
    near = sw.levels_within_pct_above(ctx.close, ctx.overhead, 3.0)
    return bool(sig and not near)


def _compute_trigger(ctx: StockContext, result: GateResult, setup: str) -> float:
    d = ctx.daily
    last_high = float(d["high"].iloc[-1])
    if setup == "TC-02":
        ref = max(last_high, float(d["high"].iloc[-11:-1].max()))
    else:
        ref = last_high

    trigger = ref
    if result.watch_flags.get("X2"):
        sma50 = d["sma50"].iloc[-1]
        if sma50 == sma50:  # not NaN
            trigger = max(trigger, float(sma50) * 1.001)

    # widen while any overhead level sits within 3% above the entry
    for _ in range(50):  # hard cap, overhead list is finite
        entry_candidate = trigger * 1.001
        near = sw.levels_within_pct_above(entry_candidate, ctx.overhead, 3.0)
        if not near:
            break
        highest = max(near)
        if highest <= trigger:
            break
        trigger = highest
    return trigger


def _stop_target(ctx: StockContext, setup: str) -> tuple[float, float]:
    d = ctx.daily
    atr14 = float(d["atr14"].iloc[-1])
    if setup == "TC-01":
        stop = ctx.p_value - 0.1 * atr14
        impulse = ctx.h_value - ctx.l_value
        target = ctx.p_value + impulse
    else:
        low_10 = float(d["low"].iloc[-10:].min())
        high_10 = float(d["high"].iloc[-10:].max())
        range_10 = high_10 - low_10
        stop = low_10 - 0.1 * atr14
        target = high_10 + 2 * range_10
    return stop, target


def build_plan(
    ctx: StockContext, result: GateResult, tick_size: float, which: str = "A"
) -> TradePlan | None:
    setup = active_setup(result)
    if setup is None:
        return None

    raw_stop, raw_target = _stop_target(ctx, setup)

    if which == "A":
        trigger = _compute_trigger(ctx, result, setup)
    else:  # Plan B "breakout": entry = H + 0.1%, same stop
        trigger = ctx.h_value

    entry = round_tick(trigger * 1.001, tick_size, "up")
    stop = round_tick(raw_stop, tick_size, "down")

    nearest_above = sw.nearest_overhead_above(entry, ctx.overhead)
    target = raw_target
    if nearest_above is not None and nearest_above < target:
        target = nearest_above

    risk_per_share = entry - stop
    reward_per_share = target - entry
    r_multiple = reward_per_share / risk_per_share if risk_per_share > 0 else float("nan")

    return TradePlan(
        plan=which,
        setup=setup,
        entry=entry,
        stop=stop,
        target=target,
        risk_per_share=risk_per_share,
        reward_per_share=reward_per_share,
        r_multiple=r_multiple,
        nearest_overhead_above_entry=nearest_above,
    )


def choose_plan(
    ctx: StockContext, result: GateResult, tick_size: float
) -> tuple[TradePlan | None, TradePlan | None, str]:
    """Evaluate both plans, return (chosen, other, reason). Plan B is
    preferred over Plan A only when Plan A's target is capped below 2R;
    with X7 (late move), Plan A is preferred regardless."""
    plan_a = build_plan(ctx, result, tick_size, "A")
    if plan_a is None:
        return None, None, "no active setup"

    plan_b = build_plan(ctx, result, tick_size, "B")

    if result.watch_flags.get("X7"):
        return plan_a, plan_b, "X7 late move: Plan A (pullback) preferred"

    if plan_a.r_multiple < 2 and plan_b is not None and plan_b.r_multiple >= 2:
        return plan_b, plan_a, "Plan A capped below 2R, Plan B (breakout) used instead"

    return plan_a, plan_b, "Plan A (pullback)"
