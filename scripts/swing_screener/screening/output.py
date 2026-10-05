"""OUTPUT — one row per filtered-universe stock, with every outcome as its
own column (gate pass/fail, watch flags, setup, decision, tradeable...) so
the whole universe can be filtered/sorted in a spreadsheet instead of
cross-referencing several files.

Column sets are derived from the active Strategy rather than hardcoded, so
a new strategy's gates/flags/setups show up as columns automatically.
"""

import pandas as pd

DECISION_RANK = {
    "TRADE - HIGH CONFIDENCE": 0,
    "TRADE ON TRIGGER": 1,
    "WATCH - WAIT": 2,
    "WATCH - SECTOR LIMIT": 3,
    "AVOID": 4,
    "NO SETUP": 5,
    "NOT REVIEWED": 6,
}

_LEAD_COLUMNS = [
    # `chart` is a link straight to the symbol's chart: every candidate has to
    # be looked at before it is traded, and retyping tickers is the friction.
    "strategy", "symbol", "chart", "sector", "price",
    "decision", "tradeable", "watchlist_candidate", "decision_before", "reason",
    "uptrend_intact", "first_failed_gate", "has_setup",
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

_BASE_BOOL_COLUMNS = ["tradeable", "watchlist_candidate", "uptrend_intact", "has_setup"]
_NUMERIC_COLUMNS = [
    "price", "rs_vs_benchmark", "rs_vs_sector", "rsi", "adx", "pct_vs_sma20",
    "pct_vs_sma50", "pct_below_52wk_high", "h_pct_above_close",
    "entry", "stop", "risk_pct", "target_r", "nearest_overhead",
    "shares", "position_value", "usd_at_risk", "earnings_in", "setup_quality",
]


def column_order(strategy) -> list[str]:
    return (
        _LEAD_COLUMNS
        + [f"setup_{c}" for c in strategy.setup_codes]
        + [f"gate_{c}" for c in strategy.gate_codes]
        + [f"watch_{c}" for c in strategy.watch_codes]
        + _TRAIL_COLUMNS
        + list(getattr(strategy, "extra_columns", ()))
    )


def _enforce_dtypes(df: pd.DataFrame, strategy) -> pd.DataFrame:
    """Force explicit nullable dtypes so the schema is identical run to run
    regardless of which rows happen to be present. Without this, a run that
    contains no 'insufficient history' rows infers a non-nullable bool for
    the gate_/watch_ columns, and the next run that does contain one fails
    to insert against the stored schema."""
    bool_cols = (
        _BASE_BOOL_COLUMNS
        + [f"setup_{c}" for c in strategy.setup_codes]
        + [f"gate_{c}" for c in strategy.gate_codes]
        + [f"watch_{c}" for c in strategy.watch_codes]
    )
    for col in bool_cols:
        if col in df.columns:
            df[col] = df[col].astype("boolean")
    for col in getattr(strategy, "extra_numeric_columns", ()):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
    for col in _NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Float64")
    return df


def universe_report(rows: list[dict], sector_rs: dict[str, float], strategy) -> pd.DataFrame:
    """One row per stock that passed the pre-filter, grouped by sector
    (strongest sector RS first), sorted within a sector by decision rank
    then setup quality desc. Every stock is kept regardless of outcome —
    AVOID/NO SETUP/NOT REVIEWED rows are not dropped — so the whole
    universe is filterable in one place."""
    columns = column_order(strategy)
    if not rows:
        return pd.DataFrame(columns=columns)

    df = pd.DataFrame(rows)
    df = _enforce_dtypes(df, strategy)
    df["_sector_rs"] = df["sector"].map(lambda s: sector_rs.get(s, float("-inf")))
    df["_decision_rank"] = df["decision"].map(lambda d: DECISION_RANK.get(d, 9))
    if "setup_quality" in df.columns:
        df["setup_quality"] = df["setup_quality"].fillna(0)
    df = df.sort_values(
        by=["_sector_rs", "_decision_rank", "setup_quality"],
        ascending=[False, True, False],
    )
    return df[[c for c in columns if c in df.columns]].reset_index(drop=True)


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
