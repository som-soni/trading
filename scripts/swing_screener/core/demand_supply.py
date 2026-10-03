"""DEMAND / SUPPLY COMMENTARY — the point-scoring verdict is an exact
transcription of the prompt. The demand/supply ZONE picks ('the breakout
level the stock came from', 'any high-volume down bar') are judgment calls
in the prompt itself, so they're implemented here as reasonable proxies:
breakout level -> prior structural swing low; high-volume down bar ->
volume > 1.5x the 50-day average, which isn't pinned to a number in the
prompt either.
"""

from dataclasses import dataclass

import pandas as pd

from .context import StockContext
from . import swings as sw


@dataclass
class DemandSupplyResult:
    up_down_ratio: float
    accumulation_days: int
    distribution_days: int
    pullback_vs_impulse_vol: float
    vol_5d_vs_50d: float
    demand_zone: float | None
    supply_zone: float | None
    supply_distance_pct: float | None
    verdict: str
    score: int

    @property
    def supports_demand_text(self) -> str:
        return f"U/D {self.up_down_ratio:.2f}, {self.accumulation_days} acc vs {self.distribution_days} dist"


def up_down_volume_ratio(daily: pd.DataFrame, n: int = 50) -> float:
    tail = daily.iloc[-(n + 1) :].copy()
    tail["chg"] = tail["close"].pct_change()
    tail = tail.iloc[1:]
    up_vol = tail.loc[tail["chg"] > 0, "volume"].sum()
    down_vol = tail.loc[tail["chg"] < 0, "volume"].sum()
    return float(up_vol / down_vol) if down_vol > 0 else float("inf")


def accumulation_distribution_days(daily: pd.DataFrame, n: int = 25) -> tuple[int, int]:
    tail = daily.iloc[-(n + 1) :].copy()
    tail["chg_pct"] = tail["close"].pct_change() * 100
    tail["vol_prev"] = tail["volume"].shift(1)
    tail = tail.iloc[1:]
    acc = int(((tail["chg_pct"] >= 0.2) & (tail["volume"] > tail["vol_prev"])).sum())
    dist = int(((tail["chg_pct"] <= -0.2) & (tail["volume"] > tail["vol_prev"])).sum())
    return acc, dist


def pullback_vs_impulse_volume(daily: pd.DataFrame, h_index: pd.Timestamp) -> float:
    pos = daily.index.get_loc(h_index)
    after_h = daily["volume"].iloc[pos + 1 :]
    start = max(0, pos - 40)
    segment = daily.iloc[start:pos]
    if segment.empty or after_h.empty:
        return float("nan")
    l_pos = daily.index.get_loc(segment["low"].idxmin())
    impulse = daily["volume"].iloc[l_pos : pos + 1]
    if impulse.empty or impulse.mean() == 0:
        return float("nan")
    return float(after_h.mean() / impulse.mean())


def vol_5d_vs_50d(daily: pd.DataFrame) -> float:
    v5 = daily["volume"].iloc[-5:].mean()
    v50 = daily["vol_sma50"].iloc[-1]
    return float(v5 / v50) if pd.notna(v50) and v50 else float("nan")


def demand_zone(ctx: StockContext) -> float | None:
    d = ctx.daily
    candidates = [
        ctx.p_value,
        ctx.prior_swing_low,
        float(d["sma20"].iloc[-1]) if pd.notna(d["sma20"].iloc[-1]) else None,
        float(d["sma50"].iloc[-1]) if pd.notna(d["sma50"].iloc[-1]) else None,
    ]
    below = [c for c in candidates if c is not None and c == c and c < ctx.close]
    return max(below) if below else None


def supply_zone(ctx: StockContext) -> float | None:
    nearest = sw.nearest_overhead_above(ctx.close, ctx.overhead)
    d = ctx.daily.iloc[-60:]
    vol_sma50 = ctx.daily["vol_sma50"].reindex(d.index)
    down_bars = d[
        (d["close"] < d["open"]) & (d["volume"] > vol_sma50 * 1.5) & (d["low"] > ctx.close)
    ]
    alt = float(down_bars["low"].min()) if not down_bars.empty else None
    candidates = [v for v in [nearest, alt] if v is not None]
    return min(candidates) if candidates else None


def compute(ctx: StockContext) -> DemandSupplyResult:
    d = ctx.daily
    ud = up_down_volume_ratio(d, 50)
    acc, dist = accumulation_distribution_days(d, 25)
    pb_ratio = pullback_vs_impulse_volume(d, ctx.h_index)
    v5v50 = vol_5d_vs_50d(d)

    score = 0
    if ud >= 1.2:
        score += 1
    if ud < 0.8:
        score -= 1
    if acc > dist + 1:
        score += 1
    if dist > acc + 1:
        score -= 1
    if pb_ratio == pb_ratio and pb_ratio < 0.8:
        score += 1
    if pb_ratio == pb_ratio and pb_ratio > 1.1:
        score -= 1

    if score >= 2:
        label = "Demand in control"
    elif score <= -2:
        label = "Supply in control"
    else:
        label = "Balanced"

    dz = demand_zone(ctx)
    sz = supply_zone(ctx)
    sz_dist = (sz / ctx.close - 1) * 100 if sz else None

    return DemandSupplyResult(
        up_down_ratio=ud,
        accumulation_days=acc,
        distribution_days=dist,
        pullback_vs_impulse_vol=pb_ratio,
        vol_5d_vs_50d=v5v50,
        demand_zone=dz,
        supply_zone=sz,
        supply_distance_pct=sz_dist,
        verdict=label,
        score=score,
    )
