"""STEP 6 — decision classification and the sector filter. Reads the
outputs of gates.py, entry.py, demand_supply.py and sizing.py and applies
the TRADE / TRADE ON TRIGGER / WATCH - WAIT / AVOID rules exactly as
written in the prompts, including the watch-flag caps and the
market-regime downgrade.
"""

from dataclasses import dataclass

from .gates import GateResult, StockContext
from .entry import TradePlan, signal_present
from .demand_supply import DemandSupplyResult
from .sizing import SizingResult

DOWNGRADE_MAP = {
    "TRADE_HIGH_CONFIDENCE": "TRADE_ON_TRIGGER",
    "TRADE_ON_TRIGGER": "WATCH_WAIT",
    "WATCH_WAIT": "AVOID",
    "AVOID": "AVOID",
}

LABELS = {
    "TRADE_HIGH_CONFIDENCE": "TRADE - HIGH CONFIDENCE",
    "TRADE_ON_TRIGGER": "TRADE ON TRIGGER",
    "WATCH_WAIT": "WATCH - WAIT",
    "AVOID": "AVOID",
}


@dataclass
class Decision:
    label_before: str
    label_after: str
    reason: str
    risk_pct: float
    r_multiple: float
    setup_quality: float


def setup_quality_score(result: GateResult) -> float:
    score = 2.0 if result.setup_tc01 else (1.0 if result.setup_tc02 else 0.0)
    if result.setup_tc04:
        score += 0.5
    if result.watch_flags.get("X3"):
        score += 1.0
    if result.watch_flags.get("X4") and result.watch_notes.get("X4") == "drift":
        score -= 1.0
    if result.watch_flags.get("X5") and result.watch_notes.get("X5") == "drift":
        score -= 1.0
    if result.watch_flags.get("X6") and result.watch_notes.get("X6") == "momentum fading toward SMA50":
        score -= 1.0
    return score


def classify(
    ctx: StockContext,
    result: GateResult,
    plan: TradePlan,
    sizing: SizingResult,
    ds: DemandSupplyResult,
    earnings_days_away: int | None,
    regime_downgrade_active: bool,
) -> Decision:
    if not result.hard_gates_passed:
        code = result.first_hard_fail
        reason = f"fails hard gate {code}: {result.hard_notes.get(code, '')}"
        return Decision("AVOID", "AVOID", reason, float("nan"), float("nan"), 0.0)

    risk_pct = plan.risk_per_share / plan.entry * 100 if plan.entry else float("nan")
    r_mult = plan.r_multiple
    sig = signal_present(ctx, result)
    cap = result.watch_cap
    supply_blocks = ds.verdict == "Supply in control"
    earnings_block_15 = earnings_days_away is not None and earnings_days_away < 15

    reasons: list[str] = []

    if sizing.too_large:
        label = "WATCH_WAIT"
        reasons.append("too large for account")
    elif risk_pct > 8 or r_mult < 2:
        label = "WATCH_WAIT"
        if risk_pct > 8:
            reasons.append(f"stop {risk_pct:.1f}% > 8%")
        if r_mult < 2:
            reasons.append(f"target {r_mult:.2f}R < 2R")
    elif supply_blocks:
        label = "WATCH_WAIT"
        reasons.append(f"demand/supply: {ds.verdict} ({ds.supports_demand_text})")
    elif cap == "WATCH_WAIT":
        label = "WATCH_WAIT"
        reasons.append(result.watch_notes.get("X1", "extended (X1)"))
    elif (
        sig
        and cap == "TRADE_HIGH_CONFIDENCE"
        and risk_pct <= 7
        and r_mult >= 2
        and not earnings_block_15
    ):
        label = "TRADE_HIGH_CONFIDENCE"
        reasons.append(f"{result.setup_tc01 and 'TC-01' or 'TC-02'} signal fired, {r_mult:.2f}R")
    else:
        label = "TRADE_ON_TRIGGER"
        if not sig:
            reasons.append("entry trigger not yet fired")
        if cap == "TRADE_ON_TRIGGER":
            capping = [
                code for code in ("X2", "X4", "X8", "X9")
                if result.watch_flags.get(code)
                and (code != "X4" or result.watch_notes.get("X4") == "drift")
            ]
            reasons.append(f"capped by watch flag ({'/'.join(capping)})")
        if earnings_block_15 and label != "WATCH_WAIT":
            reasons.append(f"earnings in {earnings_days_away}d (blocks HIGH CONFIDENCE)")

    label_after = DOWNGRADE_MAP[label] if regime_downgrade_active else label
    if regime_downgrade_active:
        reasons.append("market-regime downgrade applied")

    return Decision(
        label_before=LABELS[label],
        label_after=LABELS[label_after],
        reason="; ".join(reasons) if reasons else "",
        risk_pct=risk_pct,
        r_multiple=r_mult,
        setup_quality=setup_quality_score(result),
    )


@dataclass
class SectorFilterOutcome:
    symbol: str
    kept: bool
    note: str


def apply_sector_filter(
    rows: list[dict], sector_limit: int = 3
) -> list[dict]:
    """`rows` are dicts with at least: symbol, sector, decision (after
    regime), setup_quality, target_r (R-multiple), rs_vs_benchmark. Mutates
    and returns the list with 'decision', 'tradeable' and
    'sector_filter_note' updated for anything bumped by the per-sector cap."""
    by_sector: dict[str, list[dict]] = {}
    for row in rows:
        if row["decision"] in ("TRADE - HIGH CONFIDENCE", "TRADE ON TRIGGER"):
            by_sector.setdefault(row["sector"], []).append(row)

    for sector, sector_rows in by_sector.items():
        ranked = sorted(
            sector_rows,
            key=lambda r: (
                -(r.get("setup_quality") or 0),
                -(r.get("target_r") or 0),
                -(r.get("rs_vs_benchmark") or 0),
            ),
        )
        keepers = {r["symbol"] for r in ranked[:sector_limit]}
        replacements = [r["symbol"] for r in ranked[:sector_limit]]
        for row in ranked[sector_limit:]:
            row["decision"] = "WATCH - SECTOR LIMIT"
            row["tradeable"] = False
            row["sector_filter_note"] = (
                f"sector cap ({sector_limit}); stronger names: {', '.join(replacements)}"
            )

    return rows
