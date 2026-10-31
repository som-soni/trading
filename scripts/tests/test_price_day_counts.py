"""`price_day_counts` must always equal a count of `prices` by (market, date).

Freshness reads per-day row counts from that table instead of counting `prices` (15-20 s:
recently rewritten rows cost a heap fetch each). Triggers keep it current, so it is only
right if they count exactly what every writer does: the upsert that rewrites a symbol's
history (an update must not count), the append that skips stored dates, the stray and
frozen-bar deletes, and a truncate. A day whose rows are all deleted must disappear, not
stay at 0 — freshness would read it as a partly loaded day.

This runs `freshness.DAY_COUNTS_SCHEMA` against temporary tables on its own connection,
so it never touches the real `prices`.

    PYTHONPATH=. .venv/bin/python -m tests.test_price_day_counts
"""

import sys

import psycopg2
import psycopg2.extras

from swing_screener.marketdata import freshness   # importing marketdata.db loads scripts/.env for connect()


def main() -> int:
    conn = psycopg2.connect()   # its own session: the temp tables and functions vanish with it
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("SET search_path = pg_temp, public")   # `prices` / `price_day_counts` resolve to the temp tables
    cur.execute("""CREATE TEMP TABLE prices (market VARCHAR(16), symbol VARCHAR(32), date DATE, close DOUBLE PRECISION,
                                            PRIMARY KEY (market, symbol, date))""")
    sql = freshness.DAY_COUNTS_SCHEMA.replace("CREATE TABLE", "CREATE TEMP TABLE")
    for fn in ("price_day_counts_add", "price_day_counts_sub", "price_day_counts_clear"):
        sql = sql.replace(f"FUNCTION {fn}()", f"FUNCTION pg_temp.{fn}()")   # a temp function is only found qualified
    cur.execute(sql)

    bad = []

    def check(step: str) -> None:
        cur.execute("SELECT market, date, n_rows FROM price_day_counts ORDER BY 1, 2")
        got = cur.fetchall()
        cur.execute("SELECT market, date, count(*) FROM prices GROUP BY 1, 2 ORDER BY 1, 2")
        want = cur.fetchall()
        if got != want:
            bad.append(f"after {step}: price_day_counts {got} != prices {want}")

    upsert = ("INSERT INTO prices VALUES %s ON CONFLICT (market, symbol, date) DO UPDATE SET close = EXCLUDED.close")
    rows = [(m, s, f"2026-10-{d:02d}", 1.0) for m in ("us", "india") for s in ("A", "B", "C") for d in (1, 2, 5)]
    psycopg2.extras.execute_values(cur, upsert, rows)
    check("first load")
    # a symbol's history rewritten (updates) plus one new day (insert), as save_cached does
    psycopg2.extras.execute_values(cur, upsert, [("us", "A", f"2026-10-{d:02d}", 2.0) for d in (1, 2, 5, 6)])
    check("upsert of a stored history")
    # append_bars: stored dates skipped
    psycopg2.extras.execute_values(cur, "INSERT INTO prices VALUES %s ON CONFLICT (market, symbol, date) DO NOTHING",
                                   [("us", "B", "2026-10-05", 9.0), ("us", "B", "2026-10-06", 9.0)])
    check("insert that skips stored dates")
    cur.execute("DELETE FROM prices WHERE market='us' AND symbol='A' AND date = ANY(%s::date[])", (["2026-10-01", "2026-10-02"],))
    check("delete of some bars")
    cur.execute("DELETE FROM prices WHERE market='india' AND date='2026-10-05'")
    check("delete of a whole day")
    cur.execute("SELECT count(*) FROM price_day_counts WHERE n_rows <= 0")
    if cur.fetchone()[0]:
        bad.append("a day with no rows left stays in price_day_counts")
    cur.execute("TRUNCATE prices")
    check("truncate")
    conn.close()

    # the reader prefers the table only where it exists
    if not isinstance(freshness._has_day_counts(), bool):
        bad.append("_has_day_counts() does not answer True/False")

    for b in bad:
        print("FAIL", b)
    print("ok" if not bad else f"{len(bad)} failure(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
