"""STEP 5 — position sizing. Direct transcription:
shares = floor(risk / (entry - stop)); if shares*entry > max position, use
floor(max_position / entry) and report the actual amount at risk; if
shares < 1, mark 'Too large for account'.
"""

import math
from dataclasses import dataclass

from .config.base import MarketConfig


@dataclass
class SizingResult:
    risk_amount: float
    shares: int
    position_value: float
    actual_risk_amount: float
    too_large: bool


def size_position(
    cfg: MarketConfig, entry: float, stop: float, vix_above_threshold: bool
) -> SizingResult:
    risk_amount = cfg.account_size * (
        cfg.risk_pct_high_vol if vix_above_threshold else cfg.risk_pct
    )
    risk_per_share = entry - stop
    if risk_per_share <= 0 or entry <= 0:
        return SizingResult(risk_amount, 0, 0.0, 0.0, True)

    shares = math.floor(risk_amount / risk_per_share)
    position_value = shares * entry
    max_position = cfg.account_size * cfg.max_position_pct

    if position_value > max_position:
        shares = math.floor(max_position / entry)
        position_value = shares * entry

    actual_risk = shares * risk_per_share
    too_large = shares < 1

    return SizingResult(
        risk_amount=risk_amount,
        shares=shares,
        position_value=position_value,
        actual_risk_amount=actual_risk,
        too_large=too_large,
    )
