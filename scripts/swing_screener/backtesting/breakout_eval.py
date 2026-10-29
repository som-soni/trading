"""The breakout eval set: big moves found from the outcome backwards, for judging the VCP detector.

The book examples (`tests/test_vcp_book_examples.py`) start from a pattern and ask whether the
detector sees it. This starts from the other end: every stock that went up a lot, whatever came
before it, so a person can look at each chart and say what base -- if any -- it came out of. Only
then is the detector scored against those labels (`--score`), which is why the scan stores no
detector output and the review list does not show it.

A case is a BREAKOUT that became a big move:

* the close clears the highest high of the previous `RANGE_SESSIONS` sessions (it left a range),
* a stock, not a fund or note (`_equities`),
* the close is at least `MIN_PRICE` and the 50-day average turnover at least the Minervini
  strategy's liquidity floor, so the move was tradable,
* and within `FWD_SESSIONS` sessions some close is at least `MIN_GAIN_PCT`% above it, the highest
  of them no sooner than `MIN_SESSIONS_TO_PEAK` sessions after the breakout.

The breakout date only marks where the move became visible: it is often NOT a buy point (NKTR's
29 Sep 2017 close cleared a 60-session range halfway up the right side of a seven-month base). The
reviewer records the valid entry, if there was one, as `review_entry_date` and `review_pivot`, and the
detector is judged on whether it signals within a few sessions of that entry.

The peak is the highest close in that window; the next case for the same stock can start only
after it, so one move is one case. Breakouts and peaks both fall inside `WINDOW`, the last five
years of the optimise stage: the 2022+ verify years are never read, so tuning the detector on
these labels leaves the verify window clean (`backtesting/windows.py`).

Run, from scripts/:
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --build
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --list
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --label ID LABEL \
        [--entry YYYY-MM-DD --pivot PRICE --footprint "32W 30/9 3T" --notes ...]
"""

from __future__ import annotations

import argparse
import warnings

import pandas as pd

from ..marketdata import asof, cache, db, names
from ..strategies import minervini_spec as ms

EVAL_SET = "us-2017-2021-x2"
MARKET = "us"
WINDOW = ("2017-01-01", "2021-12-31")   # the last five years of the optimise stage
RANGE_SESSIONS = 60       # the breakout close clears the highest high of this many sessions before it
FWD_SESSIONS = 63         # about three months to …
MIN_GAIN_PCT = 100.0      # … at least double
MIN_PRICE = 5.0
MIN_SESSIONS_TO_PEAK = 10  # a move that tops out inside two weeks is a news spike, not a trend
HISTORY_DAYS = 400        # calendar days read before the window, for the range and the turnover average

# What a reviewer can call a case, following the Learn guide on the VCP.
LABELS = {
    "vcp": "a VCP: pullbacks that shrink, volume drying up, a tight area near the top of the base",
    "base": "a base that is not a VCP: cup, flat base, double bottom … without shrinking pullbacks",
    "cheat": "bought inside the base: a shelf below the base high (low cheat, 3C)",
    "power_play": "an explosive run, then a short tight flag",
    "v": "a straight-V recovery or a move from nothing: no base to buy",
    "gap": "a news gap (earnings, takeover, approval) with no setup before it",
    "bad_data": "the move is a price error, a split or a corporate action",
    "unsure": "looked at, no call yet",
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS breakout_eval_cases (
    id SERIAL PRIMARY KEY,
    eval_set VARCHAR(32) NOT NULL,
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    breakout_date DATE NOT NULL,
    breakout_close DOUBLE PRECISION,
    range_high DOUBLE PRECISION,
    range_depth_pct DOUBLE PRECISION,
    turnover_m DOUBLE PRECISION,
    peak_date DATE,
    peak_close DOUBLE PRECISION,
    gain_pct DOUBLE PRECISION,
    sessions_to_peak INTEGER,
    review_label VARCHAR(16),
    review_entry_date DATE,
    review_pivot DOUBLE PRECISION,
    review_footprint VARCHAR(32),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    UNIQUE (eval_set, market, symbol, breakout_date)
);
ALTER TABLE breakout_eval_cases ADD COLUMN IF NOT EXISTS review_entry_date DATE;
ALTER TABLE breakout_eval_cases ADD COLUMN IF NOT EXISTS review_pivot DOUBLE PRECISION;
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def scan(frames: dict[str, pd.DataFrame]) -> list[dict]:
    start, end = pd.Timestamp(WINDOW[0]), pd.Timestamp(WINDOW[1])
    floor = ms.MIN_TURNOVER_USD_M * 1e6
    out = []
    for sym, d in frames.items():
        d = d[d.index <= end]
        if len(d) <= RANGE_SESSIONS + 1:
            continue
        c, v = d["close"].to_numpy(float), d["volume"].to_numpy(float)
        prior_hi = d["high"].shift(1).rolling(RANGE_SESSIONS).max().to_numpy()
        prior_lo = d["low"].shift(1).rolling(RANGE_SESSIONS).min().to_numpy()
        turn = pd.Series(c * v, index=d.index).rolling(50).mean().to_numpy()
        j = RANGE_SESSIONS
        while j < len(c) - 1:
            if (d.index[j] >= start and c[j] > prior_hi[j] and c[j] >= MIN_PRICE
                    and turn[j] >= floor):
                seg = c[j + 1: j + 1 + FWD_SESSIONS]
                k = j + 1 + int(seg.argmax())
                if seg.max() >= (1 + MIN_GAIN_PCT / 100) * c[j] and k - j >= MIN_SESSIONS_TO_PEAK:
                    out.append(dict(
                        symbol=sym, breakout_date=d.index[j].date(), breakout_close=float(c[j]),
                        range_high=float(prior_hi[j]),
                        range_depth_pct=float((prior_hi[j] - prior_lo[j]) / prior_hi[j] * 100),
                        turnover_m=float(turn[j] / 1e6), peak_date=d.index[k].date(),
                        peak_close=float(c[k]), gain_pct=float((c[k] / c[j] - 1) * 100),
                        sessions_to_peak=k - j))
                    j = k + 1
                    continue
            j += 1
    return out


def _dedupe(found: list[dict]) -> list[dict]:
    """One listing stored under two tickers (a renamed company kept under both) is one case."""
    seen, out = set(), []
    for c in sorted(found, key=lambda c: c["symbol"]):
        key = (c["breakout_date"], round(c["breakout_close"], 4), round(c["peak_close"], 4))
        if key not in seen:
            seen.add(key)
            out.append(c)
    return out


def _equities() -> set[str]:
    """Symbols with an industry row: `symbol_industry` is filled only for quoteType EQUITY, so a fund
    or an exchange-traded note (VXX, which `universe.non_stock_symbols`' name keywords miss) has none."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol FROM symbol_industry WHERE market=%s AND industry IS NOT NULL", (MARKET,))
        return {r[0] for r in cur.fetchall()}


def build() -> int:
    """Scan the window and upsert the cases. A rebuild keeps every review already made."""
    init_schema()
    since = pd.Timestamp(WINDOW[0]) - pd.Timedelta(days=HISTORY_DAYS)
    syms = sorted(cache.cached_symbols(MARKET) & _equities())
    cases = []
    with asof.boundary(WINDOW[1]):
        for i in range(0, len(syms), 500):
            cases += scan(cache.load_many_cached(MARKET, syms[i:i + 500], since=since))
    cases = _dedupe(cases)
    cols = ["symbol", "breakout_date", "breakout_close", "range_high", "range_depth_pct",
            "turnover_m", "peak_date", "peak_close", "gain_pct", "sessions_to_peak"]
    db.execute_values(
        f"INSERT INTO breakout_eval_cases (eval_set, market, {', '.join(cols)}) VALUES %s "
        "ON CONFLICT (eval_set, market, symbol, breakout_date) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in cols[2:]),
        [(EVAL_SET, MARKET, *(c[k] for k in cols)) for c in cases])
    keep = [(c["symbol"], c["breakout_date"]) for c in cases]
    with db.get_connection().cursor() as cur:   # cases the definition no longer finds, unless reviewed
        cur.execute("SELECT id, symbol, breakout_date FROM breakout_eval_cases "
                    "WHERE eval_set=%s AND review_label IS NULL", (EVAL_SET,))
        gone = [r[0] for r in cur.fetchall() if (r[1], r[2]) not in set(keep)]
        if gone:
            cur.execute("DELETE FROM breakout_eval_cases WHERE id = ANY(%s)", (gone,))
    return len(cases)


def cases() -> pd.DataFrame:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT * FROM breakout_eval_cases WHERE eval_set=%s ORDER BY breakout_date, symbol",
                    (EVAL_SET,))
        cols = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def label(case_id: int, value: str, footprint: str | None = None, notes: str | None = None,
          entry: str | None = None, pivot: float | None = None) -> None:
    if value not in LABELS:
        raise SystemExit(f"label must be one of {', '.join(LABELS)}")
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE breakout_eval_cases SET review_label=%s, review_footprint=COALESCE(%s, review_footprint), "
                    "review_notes=COALESCE(%s, review_notes), review_entry_date=COALESCE(%s, review_entry_date), "
                    "review_pivot=COALESCE(%s, review_pivot), reviewed_at=now() WHERE id=%s",
                    (value, footprint, notes, entry, pivot, case_id))


def main() -> None:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--label", nargs=2, metavar=("ID", "LABEL"))
    ap.add_argument("--footprint")
    ap.add_argument("--notes")
    ap.add_argument("--entry", help="the valid entry session, YYYY-MM-DD")
    ap.add_argument("--pivot", type=float, help="the buy point that entry crossed")
    a = ap.parse_args()
    if a.build:
        print(f"{build()} cases in {EVAL_SET}")
    if a.label:
        label(int(a.label[0]), a.label[1], a.footprint, a.notes, a.entry, a.pivot)
    if a.list or not (a.build or a.label):
        df = cases()
        nm = names.load(MARKET)
        df.insert(3, "name", [(names.lookup(nm, s) or "")[:28] for s in df["symbol"]])
        with pd.option_context("display.max_rows", None, "display.width", 200):
            print(df[["id", "symbol", "name", "breakout_date", "breakout_close", "peak_date",
                      "gain_pct", "sessions_to_peak", "range_depth_pct", "review_label"]]
                  .round(1).to_string(index=False))


if __name__ == "__main__":
    main()
