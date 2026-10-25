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

Two errors survive a re-fetch because they are in the source's own history, and `correct` fixes them in
place (recorded in `price_corrections`, and re-applied after a later re-fetch brings them back):

  * an UNADJUSTED SPLIT: Yahoo sometimes adjusts a split only back to the start of its year, so the
    bars before 1 January stay on the old scale (MOTILALOFS 2024-01-01 for its June 2024 split, GPIL,
    PARAS). A split-shaped gap is rescaled only when a split or bonus of the same ratio is stored in
    `corporate_actions` within SPLIT_MATCH_DAYS of it and the volume moved the way a split's does --
    a real crash has no such record, so YESBANK 2020-03-06 and the like are never touched. The bars
    before the gap are multiplied by the ratio (volume divided), as a correct source would have.
  * a STRAY BAR: one bar off the scale of both neighbours by a split ratio, the neighbours agreeing
    with each other -- a zero-volume placeholder at a tenth of the price on a holiday (CCAVENUE 2026),
    or a Diwali muhurat session the source left unadjusted (INDIAMART 2019-10-27, before its 2023
    bonus). An untraded one is deleted. A traded one is rescaled onto its neighbours' scale only when a
    split or bonus of that ratio is stored after it; otherwise it may be a real print in an illiquid
    stock (RAJRILTD trades at 5 and 10 on alternate days) and is left alone.

    PYTHONPATH=. python3 -m swing_screener.marketdata.splits --market india            # report suspects
    PYTHONPATH=. python3 -m swing_screener.marketdata.splits --market india --repair   # and re-fetch them
    PYTHONPATH=. python3 -m swing_screener.marketdata.splits --market india --correct  # fix source errors
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

SPLIT_MATCH_DAYS = 366     # a stored split/bonus this close to an unadjusted gap corroborates it
STRAY_RATIOS = [r for r in RATIOS if r <= 0.5 or r >= 2]   # a stray bar's offset: never a plausible day's move
STRAY_NEIGHBOUR_TOL = 0.15  # a stray bar's neighbours agree within this (log) -- the bar alone is off

SCHEMA = """
CREATE TABLE IF NOT EXISTS split_checks (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, date DATE NOT NULL,
    ratio DOUBLE PRECISION, checked_at TIMESTAMPTZ NOT NULL DEFAULT now(), still_there BOOLEAN,
    PRIMARY KEY (market, symbol, date)
);
CREATE TABLE IF NOT EXISTS price_corrections (
    market VARCHAR(16) NOT NULL, symbol VARCHAR(32) NOT NULL, date DATE NOT NULL,
    kind VARCHAR(16) NOT NULL,          -- rescale_before | stray_bar
    ratio DOUBLE PRECISION NOT NULL,    -- the gap's price ratio (new / old scale)
    reason TEXT, applied_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (market, symbol, date, kind)
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


def _split_factors(market: str, symbols: list[str]) -> dict[str, list[tuple]]:
    """{symbol: [(ex_date, price ratio)]} from every stored split, bonus and face-value split."""
    from . import corporate_actions as ca
    acts = ca.load(market, symbols, kinds=("split", "bonus", "face_split"))
    out: dict[str, list[tuple]] = {}
    for r in acts.itertuples():
        if r.value and r.value > 0:
            out.setdefault(r.symbol, []).append((r.ex_date, 1.0 / float(r.value)))
    return out


def _lasting(market: str, symbol: str, date, ratio: float, bars: int = 10) -> bool:
    """The median close of the `bars` sessions from `date` sits at `ratio` of the median of the `bars`
    before it: a change of scale, not a one-bar excursion or a move that reversed."""
    with db.get_connection().cursor() as cur:
        cur.execute("""(SELECT close, false FROM prices WHERE market=%s AND symbol=%s AND date < %s ORDER BY date DESC LIMIT %s)
                       UNION ALL
                       (SELECT close, true FROM prices WHERE market=%s AND symbol=%s AND date >= %s ORDER BY date LIMIT %s)""",
                    (market, symbol, date, bars, market, symbol, date, bars))
        rows = cur.fetchall()
    before = pd.Series([c for c, a in rows if not a], dtype=float).median()
    after = pd.Series([c for c, a in rows if a], dtype=float).median()
    return bool(before > 0 and after > 0 and abs(math.log(after / before / ratio)) <= CLOSE_TOL)


def unadjusted_gaps(market: str) -> pd.DataFrame:
    """Split-shaped gaps in the source's own history (volume-confirmed, `source_suspects`) that a stored
    split or bonus of the same ratio, within SPLIT_MATCH_DAYS, says are an adjustment the source left
    out -- and that last (`_lasting`), so the far side of a stray bar is never taken for one."""
    sus = source_suspects(market)
    if sus.empty:
        return sus.assign(action=[])
    facts = _split_factors(market, sorted(set(sus["symbol"])))
    keep, why = [], []
    for r in sus.itertuples():
        d = pd.Timestamp(r.date)
        hit = [(ex, f) for ex, f in facts.get(r.symbol, [])
               if abs((ex - d).days) <= SPLIT_MATCH_DAYS and abs(math.log(r.ratio / f)) <= OPEN_TOL]
        hit = hit if hit and _lasting(market, r.symbol, r.date, r.ratio) else []
        keep.append(bool(hit))
        why.append(f"split/bonus of ratio {hit[0][1]:.4g} stored for {hit[0][0].date()}" if hit else "")
    out = sus.assign(action=why)
    return out[keep].reset_index(drop=True)


def stray_bars(market: str) -> pd.DataFrame:
    """Single bars off the scale of both neighbours by a split ratio, the neighbours agreeing, that are
    safe to fix: untraded ones, and traded ones a later stored split or bonus of that ratio explains."""
    with db.get_connection().cursor() as cur:
        cur.execute("""
            SELECT symbol, date, prev, open, close, nxt, volume FROM (
                SELECT symbol, date, open, close, volume,
                       lag(close) OVER w AS prev, lead(open) OVER w AS nxt
                FROM prices WHERE market=%s WINDOW w AS (PARTITION BY symbol ORDER BY date)) x
            WHERE prev > 0 AND nxt > 0 AND close > 0 AND open > 0
              AND abs(ln(close / prev)) >= %s AND abs(ln(nxt / prev)) <= %s""",
                    (market, MIN_MOVE, STRAY_NEIGHBOUR_TOL))
        rows = cur.fetchall()
    out = []
    for sym, d, prev, o, c, nxt, vol in rows:
        r = min(STRAY_RATIOS, key=lambda x: abs(math.log((c / prev) / x)))
        if abs(math.log((c / prev) / r)) > OPEN_TOL or abs(math.log((o / prev) / r)) > CLOSE_TOL:
            continue
        out.append({"symbol": sym, "date": d, "prev_close": prev, "open": o, "close": c, "next_open": nxt,
                    "volume": vol, "ratio": r})
    df = pd.DataFrame(out, columns=["symbol", "date", "prev_close", "open", "close", "next_open", "volume", "ratio"])
    traded = df[df["volume"].fillna(0) > 0]
    facts = _split_factors(market, sorted(set(traded["symbol"]))) if len(traded) else {}
    ok = [not v or any(ex > pd.Timestamp(d) and abs(math.log(r / f)) <= OPEN_TOL
                       for ex, f in facts.get(sym, []) for r in [1.0 / ratio])
          for sym, d, v, ratio in zip(df["symbol"], df["date"], df["volume"].fillna(0), df["ratio"])]
    return df[ok].reset_index(drop=True)


def _rescale(df: pd.DataFrame, mask, ratio: float) -> pd.DataFrame:
    df = df.copy()
    for c in ("open", "high", "low", "close"):
        df.loc[mask, c] = df.loc[mask, c] * ratio
    df.loc[mask, "volume"] = (df.loc[mask, "volume"] / ratio).round()
    return df


def correct(market: str, apply: bool = True) -> dict:
    """Fix the two source errors a re-fetch cannot (module docstring): rescale the history before each
    corroborated unadjusted split, and put each stray bar back on its neighbours' scale (or delete it if
    it did not trade). Recorded in `price_corrections`; each symbol's cached signals are dropped."""
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)
    strays = stray_bars(market)
    if not apply:
        return {"unadjusted": unadjusted_gaps(market), "stray": strays}
    touched, rows = set(), []
    deleted = 0
    for r in strays.itertuples():
        if not r.volume:
            with db.get_connection().cursor() as cur:
                cur.execute("DELETE FROM prices WHERE market=%s AND symbol=%s AND date=%s", (market, r.symbol, r.date))
            deleted += 1
            why = "untraded bar off its neighbours' scale: deleted"
        else:
            df = cache.load_cached(market, r.symbol)
            if df is None:
                continue
            cache.save_cached(market, r.symbol, _rescale(df, df.index == pd.Timestamp(r.date), 1.0 / r.ratio))
            why = "traded bar off its neighbours' scale: rescaled onto it"
        rows.append((market, r.symbol, r.date, "stray_bar", r.ratio, why))
        touched.add(r.symbol)
    # the far side of a stray bar looked like a gap too; only what is left after fixing them is real
    gaps = unadjusted_gaps(market)
    for r in gaps.itertuples():
        df = cache.load_cached(market, r.symbol)
        if df is None:
            continue
        cache.save_cached(market, r.symbol, _rescale(df, df.index < pd.Timestamp(r.date), r.ratio))
        rows.append((market, r.symbol, r.date, "rescale_before", r.ratio, r.action))
        touched.add(r.symbol)
    if rows:
        db.execute_values("""INSERT INTO price_corrections (market, symbol, date, kind, ratio, reason) VALUES %s
                             ON CONFLICT (market, symbol, date, kind) DO UPDATE SET applied_at=now(), ratio=EXCLUDED.ratio,
                             reason=EXCLUDED.reason""", rows)
        with db.get_connection().cursor() as cur:
            cur.execute("DELETE FROM backtest_signals WHERE market=%s AND symbol = ANY(%s)", (market, sorted(touched)))
    logger.info("%s: %d unadjusted split(s) rescaled, %d stray bar(s) fixed (%d deleted)",
                market, len(gaps), len(strays), deleted)
    return {"unadjusted": len(gaps), "stray": len(strays), "deleted": deleted, "symbols": len(touched)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=["us", "india"])
    ap.add_argument("--repair", action="store_true", help="re-fetch the full history of every suspect")
    ap.add_argument("--all-dates", action="store_true", help="also list gaps before each symbol's last full fetch")
    ap.add_argument("--correct", action="store_true", help="fix unadjusted splits and stray bars in the source's history")
    ap.add_argument("--dry-run", action="store_true", help="with --correct: list them, change nothing")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    if a.correct:
        r = correct(a.market, apply=not a.dry_run)
        if a.dry_run:
            pd.set_option("display.width", 220)
            for k, v in r.items():
                print(f"{k}: {len(v)}\n{v.to_string(index=False) if len(v) else ''}")
        else:
            print(r)
        return
    s = detect(a.market, all_dates=a.all_dates)
    print(s.to_string(index=False) if len(s) else "no split-shaped gaps after the last full fetch")
    if a.repair and len(s):
        print(repair(a.market, s))


if __name__ == "__main__":
    main()
