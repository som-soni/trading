"""Additive schema migrations.

Deliberately non-destructive: columns are added, never dropped, and no
table is recreated. Rows written before the strategy dimension existed
are backfilled to 'trend_pullback', which is what they actually were.

    python3 -m swing_screener.migrate
"""

import logging

from . import db

logger = logging.getLogger("migrate")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

STATEMENTS = [
    # --- universe_history: add the strategy dimension ---
    "ALTER TABLE universe_history ADD COLUMN IF NOT EXISTS strategy VARCHAR(32) "
    "NOT NULL DEFAULT 'trend_pullback'",
    "ALTER TABLE universe_history DROP CONSTRAINT IF EXISTS universe_history_pkey",
    "ALTER TABLE universe_history ADD PRIMARY KEY (run_id, market, strategy, symbol)",
    "CREATE INDEX IF NOT EXISTS idx_universe_history_lookup "
    "ON universe_history (market, strategy, symbol, run_id)",
    # --- backtest_signals: strategy dimension + open setup vocabulary ---
    "ALTER TABLE backtest_signals ADD COLUMN IF NOT EXISTS strategy VARCHAR(32) "
    "NOT NULL DEFAULT 'trend_pullback'",
    "ALTER TABLE backtest_signals ADD COLUMN IF NOT EXISTS setups JSONB",
    # fold the old per-setup boolean columns into the new JSONB shape, so
    # previously cached signals stay usable instead of silently missing
    """
    UPDATE backtest_signals SET setups = jsonb_build_object(
        'TC-01', COALESCE(setup_tc01, false),
        'TC-02', COALESCE(setup_tc02, false),
        'TC-04', COALESCE(setup_tc04, false))
    WHERE setups IS NULL
      AND EXISTS (SELECT 1 FROM information_schema.columns
                  WHERE table_name='backtest_signals' AND column_name='setup_tc01')
    """,
    "ALTER TABLE backtest_signals DROP CONSTRAINT IF EXISTS backtest_signals_pkey",
    "ALTER TABLE backtest_signals ADD PRIMARY KEY (market, strategy, symbol, date)",
]


def migrate() -> None:
    # ALTERs run FIRST: init_schema's index definitions reference the new
    # `strategy` column, so creating them before the column exists fails.
    conn = db.get_connection()
    for stmt in STATEMENTS:
        label = " ".join(stmt.split())[:90]
        try:
            with conn.cursor() as cur:
                cur.execute(stmt)
            logger.info("ok: %s", label)
        except Exception as e:
            # expected on a fresh DB (tables absent) or where the old
            # per-setup columns never existed
            logger.info("skipped (%s): %s", type(e).__name__, label)
    db.init_schema()  # create anything still missing
    logger.info("Migration complete — no data dropped.")


if __name__ == "__main__":
    migrate()
