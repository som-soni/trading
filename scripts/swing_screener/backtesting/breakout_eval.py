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
* and within the set's `fwd_sessions` sessions some close is at least its `gain_pct`% above it, the highest
  of them no sooner than `MIN_SESSIONS_TO_PEAK` sessions after the breakout.

The breakout date only marks where the move became visible: it is often NOT a buy point (NKTR's
29 Sep 2017 close cleared a 60-session range halfway up the right side of a seven-month base). The
reviewer records the valid entry, if there was one, as `review_entry_date` and `review_pivot`, and the
detector is judged on whether it signals within a few sessions of that entry.

The peak is the highest close in that window; the next case for the same stock can start only
after it, so one move is one case. Breakouts and peaks both fall inside the set's window (`SETS`), in the
years of the optimise stage: the 2022+ verify years are never read, so tuning the detector on
these labels leaves the verify window clean (`backtesting/windows.py`).

Run, from scripts/:
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --build
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --list
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --label ID LABEL \
        [--entry YYYY-MM-DD --pivot PRICE --footprint "32W 30/9 3T" --notes ...]
    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.breakout_eval --score [--set ...|--all]

Scoring (`score`) reads only reviewed cases. One that qualifies (`yes` / `borderline`) is caught when the
strategy gives a buy setup within `SCORE_BEFORE` sessions before or `SCORE_AFTER` after the reviewed entry; one
that does not (`no`) is a false buy when a buy setup fires within `NO_BUY_BEFORE` sessions before the scan's
breakout or `SCORE_AFTER` after it.
"""

from __future__ import annotations

import argparse
import warnings

import pandas as pd

from ..marketdata import asof, cache, db, names
from ..strategies import minervini_spec as ms

MARKET = "us"
# Each set is a window of the optimise stage, so labels never touch the verify years. The first was the last
# five years; most of it (97 of 118 moves) is the 2020-21 COVID market -- pandemic, SPAC, crypto and meme
# squeezes, which mostly answer "no setup" -- so 2013-2016 adds the normal markets the strategy is built for.
# Together with the first set's 2017-2019 cases, the two cover 2013-2019 without overlapping.
# The bar for "a big move" is the set's own: doubling within three months found 118 moves in 2017-2021 but 6 in
# 2013-2016, whose leaders climbed for months rather than weeks; +75% within six months finds 58 there.
SETS = {
    "us-2017-2021-x2": {"window": ("2017-01-01", "2021-12-31"), "gain_pct": 100.0, "fwd_sessions": 63},
    "us-2013-2016-x75": {"window": ("2013-01-01", "2016-12-31"), "gain_pct": 75.0, "fwd_sessions": 126},
}
EVAL_SET = "us-2017-2021-x2"   # the default set
# COVID-period cases in the first set reviewed one by one: established, liquid leaders, a test of how the rules
# behave in a news-driven, heavy-volume market. The rest of that period is not reviewed case by case.
COVID_SAMPLE = ("TSLA", "ENPH", "DOCU", "FVRR", "APPN", "SNAP", "AMBA", "CELH", "LAD", "TWST", "MSTR")
SCORE_BEFORE, SCORE_AFTER = 5, 3   # sessions around the reviewed entry that count as the strategy's buy
NO_BUY_BEFORE = 20                  # sessions before a `no` case's breakout in which a buy is a false buy
BUY_SETUPS = (ms.MV01, ms.MV03, ms.MV04, ms.MV05, ms.FLAT, ms.NEAR)   # a buy: breakout, cheats, power play, flat, near miss
RANGE_SESSIONS = 60       # the breakout close clears the highest high of this many sessions before it
MIN_PRICE = 5.0
MIN_SESSIONS_TO_PEAK = 10  # a move that tops out inside two weeks is a news spike, not a trend
HISTORY_DAYS = 400        # calendar days read before the window, for the range and the turnover average

# A review answers two separate questions. `review_label` is the SHAPE the move came out of; whether that
# setup QUALIFIES as a SEPA entry under the Learn guide's rules is `review_qualifies` -- AXSM's January 2019
# run and flag is power-play shaped, but its flag fell 29% against the guide's 20-25%, so it does not. The
# detector is scored against the second: it should fire on "yes" and stay quiet on "no".
QUALIFIES = ("yes", "no", "borderline")

# What a reviewer can call a case's shape, following the Learn guide on the VCP.
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
    review_qualifies VARCHAR(12),
    review_entry_date DATE,
    review_pivot DOUBLE PRECISION,
    review_footprint VARCHAR(32),
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    UNIQUE (eval_set, market, symbol, breakout_date)
);
ALTER TABLE breakout_eval_cases ADD COLUMN IF NOT EXISTS review_entry_date DATE;
ALTER TABLE breakout_eval_cases ADD COLUMN IF NOT EXISTS review_pivot DOUBLE PRECISION;
ALTER TABLE breakout_eval_cases ADD COLUMN IF NOT EXISTS review_qualifies VARCHAR(12);
"""


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def scan(frames: dict[str, pd.DataFrame], eval_set: str = EVAL_SET) -> list[dict]:
    cfg = SETS[eval_set]
    (start, end), gain, fwd = (pd.Timestamp(x) for x in cfg["window"]), cfg["gain_pct"], cfg["fwd_sessions"]
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
                seg = c[j + 1: j + 1 + fwd]
                k = j + 1 + int(seg.argmax())
                if seg.max() >= (1 + gain / 100) * c[j] and k - j >= MIN_SESSIONS_TO_PEAK:
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


def build(eval_set: str = EVAL_SET) -> int:
    """Scan the set's window and upsert the cases. A rebuild keeps every review already made."""
    init_schema()
    window = SETS[eval_set]["window"]
    since = pd.Timestamp(window[0]) - pd.Timedelta(days=HISTORY_DAYS)
    syms = sorted(cache.cached_symbols(MARKET) & _equities())
    cases = []
    with asof.boundary(window[1]):
        for i in range(0, len(syms), 500):
            cases += scan(cache.load_many_cached(MARKET, syms[i:i + 500], since=since), eval_set)
    cases = _dedupe(cases)
    cols = ["symbol", "breakout_date", "breakout_close", "range_high", "range_depth_pct",
            "turnover_m", "peak_date", "peak_close", "gain_pct", "sessions_to_peak"]
    db.execute_values(
        f"INSERT INTO breakout_eval_cases (eval_set, market, {', '.join(cols)}) VALUES %s "
        "ON CONFLICT (eval_set, market, symbol, breakout_date) DO UPDATE SET "
        + ", ".join(f"{c} = EXCLUDED.{c}" for c in cols[2:]),
        [(eval_set, MARKET, *(c[k] for k in cols)) for c in cases])
    keep = [(c["symbol"], c["breakout_date"]) for c in cases]
    with db.get_connection().cursor() as cur:   # cases the definition no longer finds, unless reviewed
        cur.execute("SELECT id, symbol, breakout_date FROM breakout_eval_cases "
                    "WHERE eval_set=%s AND review_label IS NULL", (eval_set,))
        gone = [r[0] for r in cur.fetchall() if (r[1], r[2]) not in set(keep)]
        if gone:
            cur.execute("DELETE FROM breakout_eval_cases WHERE id = ANY(%s)", (gone,))
    return len(cases)


def cases(eval_set: str = EVAL_SET) -> pd.DataFrame:
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT * FROM breakout_eval_cases WHERE eval_set=%s ORDER BY breakout_date, symbol",
                    (eval_set,))
        cols = [c.name for c in cur.description]
        return pd.DataFrame(cur.fetchall(), columns=cols)


def label(case_id: int, value: str, footprint: str | None = None, notes: str | None = None,
          entry: str | None = None, pivot: float | None = None, qualifies: str | None = None) -> None:
    if value not in LABELS:
        raise SystemExit(f"label must be one of {', '.join(LABELS)}")
    if qualifies is not None and qualifies not in QUALIFIES:
        raise SystemExit(f"qualifies must be one of {', '.join(QUALIFIES)}")
    init_schema()
    with db.get_connection().cursor() as cur:
        cur.execute("UPDATE breakout_eval_cases SET review_label=%s, review_footprint=COALESCE(%s, review_footprint), "
                    "review_notes=COALESCE(%s, review_notes), review_entry_date=COALESCE(%s, review_entry_date), "
                    "review_pivot=COALESCE(%s, review_pivot), review_qualifies=COALESCE(%s, review_qualifies), "
                    "reviewed_at=now() WHERE id=%s",
                    (value, footprint, notes, entry, pivot, qualifies, case_id))


def buys_over(strategy, symbol: str, lo, hi, frames: dict, market: str = MARKET):
    """`strategy.evaluate` on every stored session from `lo` to `hi`, each seeing only its own and earlier bars:
    [(date, active setups, first hard fail, the detector's rejection, tradable)], or None when no prices are
    stored. `tradable` (sessions with a setup only, else None): the gates pass and the plan clears the limits
    the backtest applies at the fill -- risk within the setup's max_stop_pct, and at least MIN_STRUCTURAL_R --
    measured on the signal close."""
    from ..core import context as ctx_mod
    if symbol not in frames:
        raw = cache.load_cached(market, symbol)
        if raw is None or raw.empty:
            frames[symbol] = None
        else:
            raw.columns = [c.lower() for c in raw.columns]
            frames[symbol] = (raw, ctx_mod.prepare_frames(raw))
    if frames[symbol] is None:
        return None
    raw, f = frames[symbol]
    days = f.daily.loc[lo:hi].index
    if len(days) == 0:
        return None
    out = []
    for day in days:
        ctx = ctx_mod.build_context(symbol, raw, earnings_days_away=None, frames=f, as_of=day)
        if ctx is None:
            out.append((day, [], "history", None))
            continue
        r = strategy.evaluate(ctx)
        tradable = None
        if r.active_setups:
            pc = strategy.build_plans(ctx, r, _cfg(market))
            pl = pc.chosen if pc else None
            tradable = bool(r.hard_gates_passed and pl is not None and pl.entry > 0
                            and (pl.entry - pl.stop) / pl.entry <= ms.max_stop_pct(pl.setup) / 100
                            and (pl.r_multiple or 0) >= ms.MIN_STRUCTURAL_R)
        out.append((day, r.active_setups, r.first_hard_fail, ctx.extras.get("vcp_fail"), tradable))
    return out


def _cfg(market: str):
    from ..config import MARKETS
    return MARKETS[market] if isinstance(MARKETS, dict) else next(m for m in MARKETS if m.name == market)


def score(eval_sets, verbose: bool = False) -> dict:
    """The strategy against the reviewed cases: qualifying entries caught, and false buys on `no` cases."""
    from ..strategies import get_strategy
    st = get_strategy("minervini")
    frames: dict = {}
    tally = {"caught": 0, "setup only": 0, "missed": 0, "held": 0, "bought": 0}
    for es in eval_sets:
        df = cases(es)
        df = df[df["review_qualifies"].notna()]
        for _, c in df.iterrows():
            q = c["review_qualifies"]
            if q in ("yes", "borderline"):
                if c["review_entry_date"] is None or pd.isna(c["review_entry_date"]):
                    continue
                anchor = pd.Timestamp(c["review_entry_date"])
                before = SCORE_BEFORE
            else:
                anchor = pd.Timestamp(c["breakout_date"])
                before = NO_BUY_BEFORE
            rows = buys_over(st, c["symbol"], anchor - pd.Timedelta(days=int(before * 1.6) + 4),
                             anchor + pd.Timedelta(days=int(SCORE_AFTER * 1.6) + 4), frames)
            if rows is None:
                continue
            idx = [d for d, *_ in rows]
            k = next((i for i, d in enumerate(idx) if d >= anchor), len(idx) - 1)
            rows = rows[max(0, k - before): k + SCORE_AFTER + 1]
            hits = [(d, [s for s in got if s in BUY_SETUPS], t) for d, got, _, _, t in rows
                    if any(s in BUY_SETUPS for s in got)]
            if q in ("yes", "borderline"):
                key = "caught" if any(t for *_, t in hits) else "setup only" if hits else "missed"
            else:
                key = "bought" if hits else "held"
            tally[key] += 1
            if verbose or key in ("missed", "bought", "setup only"):
                why = (f"{hits[0][0].date()} {','.join(hits[0][1])}" if hits else
                       ", ".join(sorted({f"{g or '-'}/{v or '-'}" for _, _, g, v, _ in rows}))[:80])
                print(f"{key:<7} #{c['id']:<4} {c['symbol']:<5} {q:<10} {anchor.date()} {c['review_label']:<10} {why}")
    print(f"qualifying entries traded {tally['caught']} of {tally['caught'] + tally['setup only'] + tally['missed']} "
          f"({tally['setup only']} more with a setup the plan limits refuse); "
          f"'no' cases bought {tally['bought']} of {tally['bought'] + tally['held']}")
    return tally


def main() -> None:
    warnings.filterwarnings("ignore")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--set", default=EVAL_SET, choices=list(SETS))
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--label", nargs=2, metavar=("ID", "LABEL"))
    ap.add_argument("--footprint")
    ap.add_argument("--notes")
    ap.add_argument("--entry", help="the valid entry session, YYYY-MM-DD")
    ap.add_argument("--pivot", type=float, help="the buy point that entry crossed")
    ap.add_argument("--qualifies", choices=QUALIFIES, help="does the setup qualify under the Learn guide's rules")
    ap.add_argument("--score", action="store_true", help="score the strategy against the reviewed cases")
    ap.add_argument("--all", action="store_true", help="with --score: every set")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    if a.score:
        score(list(SETS) if a.all else [a.set], a.verbose)
        return
    if a.build:
        print(f"{build(a.set)} cases in {a.set}")
    if a.label:
        label(int(a.label[0]), a.label[1], a.footprint, a.notes, a.entry, a.pivot, a.qualifies)
    if a.list or not (a.build or a.label):
        df = cases(a.set)
        nm = names.load(MARKET)
        df.insert(3, "name", [(names.lookup(nm, s) or "")[:28] for s in df["symbol"]])
        with pd.option_context("display.max_rows", None, "display.width", 200):
            print(df[["id", "symbol", "name", "breakout_date", "breakout_close", "peak_date",
                      "gain_pct", "sessions_to_peak", "range_depth_pct", "review_label", "review_qualifies"]]
                  .round(1).to_string(index=False))


if __name__ == "__main__":
    main()
