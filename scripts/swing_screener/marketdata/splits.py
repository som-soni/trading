"""Find and repair splits and bonus issues the incremental price refresh cannot see.

Prices are stored adjusted as the source returned them when fetched. The daily refresh only appends
new bars, so when a stock splits (or, in India, issues bonus shares) after its last full fetch, the new
bars are on the post-split scale and the stored ones are not: the history shows a false 50–80% crash
that stops every position out and breaks every indicator (spec section 2, condition 2).

`detect` scans the stored bars for split-shaped gaps: a one-day move whose open AND close both sit near
a split or bonus ratio (1:2, 1:1 bonus, 2:1 bonus, 5:1, …, and reverse splits). A real crash rarely
lands on such a ratio at both the open and the close; a split almost always does. Gaps on or before the
symbol's last full fetch are left alone: the source's own history is already adjusted there, so a gap it
still shows is (most likely) a real move — or an error in the source itself, which re-fetching cannot
fix; `source_suspects` lists those whose volume also moved the way a split's does, so a backtest can say
how many of its trades span one.

`repair` re-fetches the full history of each suspect, which brings the whole series onto the current
scale, drops the strategies' cached signals for it (they were computed on the broken series), and
records the check in `split_checks` so a gap that survives a re-fetch (a real move) is not re-fetched
again.

    PYTHONPATH=. python3 -m swing_screener.marketdata.splits --market india            # report suspects
    PYTHONPATH=. python3 -m swing_screener.marketdata.splits --market india --repair   # and re-fetch them
"""

import argparse
import logging
import math

import pandas as pd

from . import cache, db

logger = logging.getLogger(__name__)

# price ratio (new / old) a split or bonus produces: n-for-1 splits, a:b bonus issues, and reverse splits
_SPLITS = [1 / n for n in (2, 3, 4, 5, 6, 8, 10, 15, 20, 25, 50)]
_BONUS = [b / (a + b) for a, b in ((1, 1), (1, 2), (2, 1), (1, 3), (3, 1), (1, 4), (4, 1), (1, 5), (3, 2), (2, 3), (1, 10))]
_REVERSE = [float(n) for n in (2, 3, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50, 100)]
# only ratios a normal day cannot produce: a 1:4 or 1:5 bonus (0.8, 0.83) looks exactly like India's 20% circuit
RATIOS = sorted(set(round(r, 6) for r in _SPLITS + _BONUS + _REVERSE if r <= 0.67 or r >= 2))
OPEN_TOL = 0.03        # the open within 3% of the ratio …
CLOSE_TOL = 0.10       # … and the close within a normal day's move of it
MIN_MOVE = 0.35        # only moves of at least 35% (log scale) are considered
VOL_CONFIRM = (0.5, 2.0)   # a split scales volume by 1/ratio: 20-day median volume after/before × ratio in this band

SCHEMA = """
CREATE TABLE IF NOT EXISTS split_checks (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, date DATE NOT NULL,
    ratio DOUBLE PRECISION, checked_at TIMESTAMPTZ NOT NULL DEFAULT now(), still_there BOOLEAN,
    PRIMARY KEY (market, symbol, date)
);
"""


def _nearest(x: float) -> float | None:
    """The split/bonus ratio within OPEN_TOL of x (log distance), if any."""
    if not x or x <= 0 or x != x:
        return None
    best = min(RATIOS, key=lambda r: abs(math.log(x / r)))
    return best if abs(math.log(x / best)) <= OPEN_TOL else None


def detect(market: str, symbols: list[str] | None = None, all_dates: bool = False) -> pd.DataFrame:
    """Split-shaped gaps: symbol, date, prev_close, open, close, ratio, last_full_fetch.
    Only gaps after the symbol's last full fetch, unless `all_dates`."""
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute(f"""
            SELECT symbol, date, prev, open, close FROM (
                SELECT symbol, date, open, close, lag(close) OVER (PARTITION BY symbol ORDER BY date) AS prev
                FROM prices WHERE market=%s {"AND symbol = ANY(%s)" if symbols else ""}) x
            WHERE prev > 0 AND close > 0 AND open > 0 AND abs(ln(close / prev)) >= %s""",
                    (market, symbols, MIN_MOVE) if symbols else (market, MIN_MOVE))
        rows = cur.fetchall()
        cur.execute("SELECT symbol, done_at FROM backfill_progress WHERE market=%s AND mode='max'", (market,))
        fetched = {s: pd.Timestamp(d).tz_convert(None).normalize() for s, d in cur.fetchall()}
        cur.execute("SELECT symbol, date FROM split_checks WHERE market=%s AND still_there", (market,))
        known_real = {(s, d) for s, d in cur.fetchall()}
    out = []
    for sym, d, prev, o, c in rows:
        r = _nearest(o / prev)
        if r is None or abs(math.log((c / prev) / r)) > CLOSE_TOL or (sym, d) in known_real:
            continue
        last = fetched.get(sym)
        if not all_dates and last is not None and pd.Timestamp(d) <= last:
            continue
        out.append({"symbol": sym, "date": d, "prev_close": prev, "open": o, "close": c, "ratio": r,
                    "last_full_fetch": last.date() if last is not None else None})
    df = pd.DataFrame(out, columns=["symbol", "date", "prev_close", "open", "close", "ratio", "last_full_fetch"])
    return df.sort_values(["date", "symbol"]).reset_index(drop=True)


def source_suspects(market: str) -> pd.DataFrame:
    """Split-shaped gaps still present in the source's own history, whose volume also changed the way a
    split's does (a lasting move by about 1/ratio) — data errors more likely than real moves. Used to
    report how many backtest trades span one (they cannot be repaired by re-fetching)."""
    d = detect(market, all_dates=True)
    if d.empty:
        return d
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, date, volume FROM prices WHERE market=%s AND symbol = ANY(%s) ORDER BY symbol, date",
                    (market, sorted(set(d["symbol"]))))
        px = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "volume"])
    vols = {s: x.set_index("date")["volume"].astype(float) for s, x in px.groupby("symbol")}
    keep = []
    for r in d.itertuples():
        v = vols[r.symbol]
        i = v.index.get_loc(r.date)
        before, after = v.iloc[max(0, i - 20): i].median(), v.iloc[i: i + 20].median()
        keep.append(bool(before and before == before and VOL_CONFIRM[0] <= after / before * r.ratio <= VOL_CONFIRM[1]))
    return d[keep].reset_index(drop=True)


def repair(market: str, suspects: pd.DataFrame, pause: float = 1.0) -> dict:
    """Re-fetch the full history of every suspect symbol; drop its cached strategy signals."""
    from ..providers import YFinanceProvider
    syms = sorted(set(suspects["symbol"]))
    if not syms:
        return {"symbols": 0, "fixed": 0, "still_there": 0}
    provider = YFinanceProvider(pause_sec=pause)
    fixed = 0
    for i in range(0, len(syms), 20):
        chunk = syms[i: i + 20]
        got = provider.get_many_daily_bars(chunk, 0, batch_size=20, period="max", threads=False, fallback=False)
        rows = []
        for sym in chunk:
            df = got.get(sym)
            if df is None or df.empty:
                continue
            cache.save_cached(market, sym, df)
            fixed += 1
            rows.append((market, sym, "max", df.index[0].date(), len(df)))
        if rows:
            db.execute_values("INSERT INTO backfill_progress (market, symbol, mode, first_date, bars) VALUES %s "
                              "ON CONFLICT (market, symbol, mode) DO UPDATE SET done_at=now(), first_date=EXCLUDED.first_date, bars=EXCLUDED.bars", rows)
    with db.get_connection().cursor() as cur:
        cur.execute("DELETE FROM backtest_signals WHERE market=%s AND symbol = ANY(%s)", (market, syms))
    # what is still there after a full re-fetch is the source's own history: a real move (or its error)
    after = detect(market, syms, all_dates=True)
    still = {(r.symbol, r.date) for r in after.itertuples()}
    db.execute_values("""INSERT INTO split_checks (market, symbol, date, ratio, still_there) VALUES %s
                         ON CONFLICT (market, symbol, date) DO UPDATE SET checked_at=now(), still_there=EXCLUDED.still_there""",
                      [(market, r.symbol, r.date, r.ratio, (r.symbol, r.date) in still) for r in suspects.itertuples()])
    n_still = sum((r.symbol, r.date) in still for r in suspects.itertuples())
    logger.info("%s: %d symbols re-fetched; %d of %d gaps gone, %d still there (real moves)",
                market, fixed, len(suspects) - n_still, len(suspects), n_still)
    return {"symbols": len(syms), "fixed": fixed, "gaps": len(suspects), "still_there": n_still}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=["us", "india"])
    ap.add_argument("--repair", action="store_true", help="re-fetch the full history of every suspect")
    ap.add_argument("--all-dates", action="store_true", help="also list gaps before each symbol's last full fetch")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    s = detect(a.market, all_dates=a.all_dates)
    print(s.to_string(index=False) if len(s) else "no split-shaped gaps after the last full fetch")
    if a.repair and len(s):
        print(repair(a.market, s))


if __name__ == "__main__":
    main()
