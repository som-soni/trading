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

from .. import paths

logger = logging.getLogger(__name__)

# .env lives beside the code (scripts/) or at the repo root; try both so a
# module moving between sub-packages can never silently lose the credentials
for _env in (paths.SCRIPTS_DIR / ".env", paths.REPO_ROOT / ".env"):
    if _env.exists():
        load_dotenv(_env)
        break

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
-- "latest session" and per-day questions (max(date), sessions, breadth) without scanning every row
CREATE INDEX IF NOT EXISTS prices_market_date ON prices (market, date);

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
    -- the FULL pass/fail vector, not just the first failure. Without it you
    -- can only see which gate bound first in evaluation order, which
    -- undercounts every gate evaluated later and makes true ablation
    -- ("what if gate X were removed?") impossible without a full re-run.
    hard_gates JSONB,
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
    -- strategy-specific values stashed on StockContext.extras during
    -- evaluate(). Without these a cache hit rebuilds a context missing the
    -- very numbers build_plans() needs (donchian's channel_high, breakout's
    -- pivot), and the strategy silently produces zero signals.
    extras JSONB,
    -- the strategy version+fingerprint that produced this row. Without it a cached
    -- signal outlives the rules that made it: changing the VCP detector left 1.37M rows
    -- keyed only by strategy name, so the next backtest silently replayed the OLD
    -- detections and the fix appeared to do nothing. It is part of the KEY: each
    -- version's evaluation of a bar is its own row, so backtesting a new version
    -- leaves the old run's record — what that run actually traded on — intact.
    spec_id VARCHAR(32) NOT NULL DEFAULT '',
    PRIMARY KEY (market, strategy, symbol, date, spec_id)
);
ALTER TABLE backtest_signals ADD COLUMN IF NOT EXISTS spec_id VARCHAR(32);
"""

# Tables created before the key included spec_id are moved over by ensure_signal_key().
_SIGNAL_KEY_INDEX = "backtest_signals_key_spec"


def _pid_alive(pid: int) -> bool:
    import os
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def signal_key_has_spec(cur) -> bool:
    """Whether backtest_signals' primary key includes spec_id (one row per version per bar)."""
    cur.execute("""SELECT pg_get_constraintdef(oid) FROM pg_constraint
                   WHERE conrelid = 'backtest_signals'::regclass AND contype = 'p'""")
    row = cur.fetchone()
    return bool(row and "spec_id" in row[0])


def signal_conflict_target() -> str:
    """The ON CONFLICT target matching the table's CURRENT key — read per call, so a writer
    keeps working across the key change below rather than caching a stale answer."""
    with get_connection().cursor() as cur:
        has = signal_key_has_spec(cur)
    return "(market, strategy, symbol, date, spec_id)" if has else "(market, strategy, symbol, date)"


def ensure_signal_key() -> None:
    """Move backtest_signals onto the (…, date, spec_id) key, without blocking writers for
    longer than a constraint swap. The unique index is built CONCURRENTLY (writes continue,
    minutes on a large table); the swap itself is a catalog change.

    Only call this where no process can still be writing with the OLD key: a writer whose
    ON CONFLICT names (market, strategy, symbol, date) fails once that key is gone. The job
    worker runs one job at a time, so a backtest calling this at its start is such a place —
    any older backtest has finished. Idempotent: a no-op once the key includes spec_id."""
    conn = get_connection()
    with conn.cursor() as cur:
        if signal_key_has_spec(cur):
            return
        cur.execute("""SELECT i.indisvalid FROM pg_class c JOIN pg_index i ON i.indexrelid = c.oid
                       WHERE c.relname = %s""", (_SIGNAL_KEY_INDEX,))
        row = cur.fetchone()
        if row is not None and not row[0]:   # a concurrent build that was interrupted
            cur.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {_SIGNAL_KEY_INDEX}")
            row = None
        if row is None:
            logger.info("Building the versioned signal-cache key (concurrently; a few minutes)...")
            cur.execute(f"""CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS {_SIGNAL_KEY_INDEX}
                            ON backtest_signals (market, strategy, symbol, date, spec_id)""")
        # another backtest still running (one started from a terminal while the queue's ran, or
        # one launched before this code existed) may write with the old key: leave the swap to
        # the next backtest rather than crash it
        import os, socket   # noqa: E401
        try:
            cur.execute("""SELECT pid FROM job_runs WHERE status='running' AND job LIKE '%%backtest%%'
                             AND host=%s AND pid <> %s""", (socket.gethostname(), os.getpid()))
            others = [p for (p,) in cur.fetchall() if p and _pid_alive(p)]
        except Exception:  # noqa: BLE001 — no run log yet: nothing else is recorded as running
            others = []
        if others:
            logger.info("Signal-cache key swap deferred: backtest pid(s) %s still running", others)
            return
        cur.execute("UPDATE backtest_signals SET spec_id = '' WHERE spec_id IS NULL")
        # a primary key needs spec_id NOT NULL, and proving that by itself scans the whole table
        # under an exclusive lock; a validated CHECK lets SET NOT NULL skip the scan (PG 12+),
        # and VALIDATE runs under a lock that lets writes continue
        cur.execute("""DO $$ BEGIN
                         ALTER TABLE backtest_signals ADD CONSTRAINT backtest_signals_spec_nn
                           CHECK (spec_id IS NOT NULL) NOT VALID;
                       EXCEPTION WHEN duplicate_object THEN NULL; END $$""")
        cur.execute("ALTER TABLE backtest_signals VALIDATE CONSTRAINT backtest_signals_spec_nn")
        cur.execute("BEGIN")
        try:
            cur.execute("ALTER TABLE backtest_signals ALTER COLUMN spec_id SET DEFAULT ''")
            cur.execute("ALTER TABLE backtest_signals ALTER COLUMN spec_id SET NOT NULL")
            cur.execute("ALTER TABLE backtest_signals DROP CONSTRAINT IF EXISTS backtest_signals_pkey")
            cur.execute(f"ALTER TABLE backtest_signals ADD CONSTRAINT backtest_signals_pkey "
                        f"PRIMARY KEY USING INDEX {_SIGNAL_KEY_INDEX}")
            cur.execute("ALTER TABLE backtest_signals DROP CONSTRAINT backtest_signals_spec_nn")
            cur.execute("COMMIT")
        except Exception:
            cur.execute("ROLLBACK")
            raise
    logger.info("Signal cache is now keyed by version: each version's rows are kept")


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
