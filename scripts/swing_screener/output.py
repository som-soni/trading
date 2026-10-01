"""OUTPUT — one row per filtered-universe stock, with every outcome as its
own column (gate pass/fail, watch flags, setup, decision, tradeable,
watchlist candidate...) so the whole universe can be filtered/sorted in a
spreadsheet instead of cross-referencing several files.
"""

from pathlib import Path

import pandas as pd

GATE_CODES = ["M1", "W1", "W2", "T1", "T2", "T3", "T4", "T5", "T6", "D2", "D3", "D4", "D5", "D6", "D7"]
WATCH_CODES = ["X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8"]

DECISION_RANK = {
    "TRADE - HIGH CONFIDENCE": 0,
    "TRADE ON TRIGGER": 1,
    "WATCH - WAIT": 2,
    "WATCH - SECTOR LIMIT": 3,
    "AVOID": 4,
    "NO SETUP": 5,
    "NOT REVIEWED": 6,
}

# column order for the CSV; gate_/watch_ columns are inserted programmatically
_LEAD_COLUMNS = [
    "symbol", "sector", "price",
    "decision", "tradeable", "watchlist_candidate", "decision_before", "reason",
    "uptrend_intact", "first_failed_gate", "has_setup", "setup_tc01", "setup_tc02", "setup_tc04_tag",
]
_TRAIL_COLUMNS = [
    "watch_flags_summary", "strategy_setup", "monthly", "weekly", "candles", "wait_for",
    "sector_filter_note",
    "rs_vs_benchmark", "rs_vs_sector", "rsi", "adx", "pct_vs_sma20", "pct_vs_sma50",
    "pct_below_52wk_high", "h_pct_above_close",
    "entry", "stop", "risk_pct", "target_r", "nearest_overhead",
    "shares", "position_value", "usd_at_risk", "earnings_in",
    "demand_supply", "setup_quality",
]


def universe_report(rows: list[dict], sector_rs: dict[str, float]) -> pd.DataFrame:
    """One row per stock that passed the loose screener filter, grouped by
    sector (strongest sector RS first), sorted within a sector by decision
    rank then setup quality desc. Includes every stock regardless of
    outcome — AVOID/NO SETUP/NOT REVIEWED rows are kept, not dropped —
    so the whole universe is filterable in one place."""
    columns = _LEAD_COLUMNS + [f"gate_{c}" for c in GATE_CODES] + [f"watch_{c}" for c in WATCH_CODES] + _TRAIL_COLUMNS
    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df["_sector_rs"] = df["sector"].map(lambda s: sector_rs.get(s, float("-inf")))
    df["_decision_rank"] = df["decision"].map(lambda d: DECISION_RANK.get(d, 9))
    df["setup_quality"] = df.get("setup_quality", 0).fillna(0)
    df = df.sort_values(
        by=["_sector_rs", "_decision_rank", "setup_quality"],
        ascending=[False, True, False],
    )
    cols = [c for c in columns if c in df.columns]
    return df[cols].reset_index(drop=True)


def sector_summary_lines(sector_rs: dict[str, float], sector_trend: dict[str, str]) -> list[str]:
    ordered = sorted(sector_rs.items(), key=lambda kv: kv[1], reverse=True)
    return [
        f"{sector}: {sector_trend.get(sector, 'n/a')}, RS {rs:+.1f}%"
        for sector, rs in ordered
    ]


def combined_risk_summary(rows: list[dict], account_size: float, currency_symbol: str) -> str:
    trades = [r for r in rows if r.get("decision") == "TRADE - HIGH CONFIDENCE"]
    total_risk = sum(r.get("usd_at_risk") or 0 for r in trades)
    total_position = sum(r.get("position_value") or 0 for r in trades)
    fits = total_position <= account_size
    return (
        f"{len(trades)} TRADE rows: {currency_symbol}{total_risk:,.0f} at risk, "
        f"{currency_symbol}{total_position:,.0f} total position "
        f"({'fits' if fits else 'EXCEEDS'} the {currency_symbol}{account_size:,.0f} account)"
    )
