"""Postgres connection + schema. Replaces the parquet price cache and the
DuckDB run-history file — one queryable store instead of three different
storage mechanisms, per the explicit ask: easy to inspect/query directly
with psql or pgAdmin, not locked inside opaque binary files.

Connection config comes from standard libpq env vars (PGHOST, PGPORT,
PGUSER, PGPASSWORD, PGDATABASE), loaded from scripts/.env (gitignored —
never commit credentials). psycopg2 picks these up automatically; the
dotenv load just makes `scripts/.env` the place you edit instead of your
shell profile.
"""

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_connection = None  # module-level singleton; this is a single-threaded batch script


def get_connection():
    global _connection
    if _connection is None or _connection.closed:
        _connection = psycopg2.connect()  # reads PGHOST/PGPORT/PGUSER/PGPASSWORD/PGDATABASE
        _connection.autocommit = True
    return _connection


SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    date DATE NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    sma20 DOUBLE PRECISION,
    sma50 DOUBLE PRECISION,
    sma100 DOUBLE PRECISION,
    sma200 DOUBLE PRECISION,
    ema20 DOUBLE PRECISION,
    rsi14 DOUBLE PRECISION,
    rsi_ma DOUBLE PRECISION,
    atr14 DOUBLE PRECISION,
    atr_pct DOUBLE PRECISION,
    adx14 DOUBLE PRECISION,
    vol_sma50 DOUBLE PRECISION,
    dollar_vol_sma20 DOUBLE PRECISION,
    high_252 DOUBLE PRECISION,
    -- deliberately NOT keyed by strategy: prices and indicators are facts
    -- about the market, shared by every strategy
    PRIMARY KEY (market, symbol, date)
);

CREATE TABLE IF NOT EXISTS universe_history (
    run_id VARCHAR(32) NOT NULL,
    market VARCHAR(16) NOT NULL,
    strategy VARCHAR(32) NOT NULL DEFAULT 'trend_pullback',
    symbol VARCHAR(32) NOT NULL,
    sector VARCHAR(64),
    decision VARCHAR(32),
    price DOUBLE PRECISION,
    tradeable BOOLEAN,
    reason TEXT,
    full_row JSONB NOT NULL,
    PRIMARY KEY (run_id, market, strategy, symbol)
);
CREATE INDEX IF NOT EXISTS idx_universe_history_lookup
    ON universe_history (market, strategy, symbol, run_id);

CREATE TABLE IF NOT EXISTS backtest_signals (
    market VARCHAR(16) NOT NULL,
    strategy VARCHAR(32) NOT NULL DEFAULT 'trend_pullback',
    symbol VARCHAR(32) NOT NULL,
    date DATE NOT NULL,
    hard_gates_passed BOOLEAN NOT NULL,
    first_failed_gate VARCHAR(8),
    has_setup BOOLEAN NOT NULL,
    -- open JSONB rather than one column per setup code, so a new strategy's
    -- setup vocabulary doesn't need a migration
    setups JSONB,
    h_value DOUBLE PRECISION,
    h_index DATE,
    l_value DOUBLE PRECISION,
    p_value DOUBLE PRECISION,
    prior_swing_low DOUBLE PRECISION,
    overhead_levels JSONB,
    watch_flags JSONB,
    watch_notes JSONB,
    PRIMARY KEY (market, strategy, symbol, date)
);
"""


def _legacy_setup_col_to_code(column: str) -> str:
    """setup_tc04 -> TC-04, setup_tc01 -> TC-01."""
    suffix = column.removeprefix("setup_tc")
    return f"TC-{suffix.zfill(2)}"


def _migrate_backtest_signals(cur) -> None:
    """Upgrade pre-JSONB backtest_signals tables (per-setup boolean columns)
    to the strategy-agnostic `setups` column the backtest writer expects."""
    cur.execute(
        """
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'backtest_signals'
        """
    )
    cols = {row[0] for row in cur.fetchall()}
    if not cols:
        return

    if "strategy" not in cols:
        cur.execute(
            "ALTER TABLE backtest_signals "
            "ADD COLUMN strategy VARCHAR(32) NOT NULL DEFAULT 'trend_pullback'"
        )

    if "setups" not in cols:
        cur.execute("ALTER TABLE backtest_signals ADD COLUMN setups JSONB")

    legacy_cols = sorted(
        c for c in cols if re.fullmatch(r"setup_tc\d+", c)
    )
    if legacy_cols:
        build_args = ", ".join(
            f"'{_legacy_setup_col_to_code(col)}', COALESCE({col}, false)"
            for col in legacy_cols
        )
        cur.execute(
            f"""
            UPDATE backtest_signals
            SET setups = COALESCE(setups, '{{}}'::jsonb)
                || jsonb_build_object({build_args})
            """
        )
        for col in legacy_cols:
            cur.execute(f"ALTER TABLE backtest_signals DROP COLUMN {col}")
        logger.info(
            "Migrated backtest_signals: dropped legacy setup columns (%s)",
            ", ".join(legacy_cols),
        )


def init_schema() -> None:
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
        _migrate_backtest_signals(cur)
    logger.info("Schema ready (prices, universe_history, backtest_signals)")


def execute_values(query: str, rows: list[tuple]) -> None:
    """Bulk insert/upsert helper — one round trip instead of one per row."""
    if not rows:
        return
    conn = get_connection()
    with conn.cursor() as cur:
        psycopg2.extras.execute_values(cur, query, rows)


def py_value(v):
    """Convert a pandas/numpy scalar (NaN, pd.NA, np.float64, np.bool_...)
    into something psycopg2/json can actually serialize. psycopg2 doesn't
    adapt numpy types by default, and json.dumps chokes on both NaN-as-float
    semantics and numpy scalar types."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, np.generic):
        return v.item()
    return v


def rows_to_df(rows: list[tuple], columns: list[str]) -> pd.DataFrame:
    """Cursor.fetchall() results -> DataFrame, without routing through
    pandas.read_sql (which warns about non-SQLAlchemy connections)."""
    return pd.DataFrame(rows, columns=columns)
