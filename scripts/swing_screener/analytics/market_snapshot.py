"""Market snapshot: the daily market review's readings, one value per market, session, subject and field.

The stock snapshot (screens/snapshot.py) is a catalog of fields per stock that screens are conditions over.
This is its twin for the market: a catalog of readings per market that the review's rules will be conditions
over. A rule -- from any source -- is then data over these fields, not a new tool; a new idea that needs a
reading the catalog lacks adds a FIELD, documented here, and every rule and study can use it.

It holds READINGS, never decisions. "The index closed 2.4% under its 9-day EMA" is a reading; "no new shorts
until the retest" is a rule, and lives with the rules.

Subjects:
  <label>        each review instrument: the market's `broad_index_symbols` plus `review_symbols` (config)
  market         market-wide: breadth (from breadth_daily), the volatility index, the strategies' market gate
  <a>/<b>        each `breadth_pairs` ratio line (cap-weighted over broader): where the selling is

Point in time: every value is computed from data up to and including its session (causal averages; weekly
EMAs through the last COMPLETED week), so a stored day reads exactly as it would have that evening, and a
full recompute leaves past values unchanged -- tests.test_market_snapshot checks it. The gate and the
follow-through flag are the strategies' own (`backtesting/spec.py` `market_ok`, `follow_through`), so the
review and the backtests read one definition.

Stored long -- (market, date, subject, field, value) -- so a new field or instrument is a catalog entry, not a
schema change.

    PYTHONPATH=. python3 -m swing_screener.analytics.market_snapshot --market us          # catch up
    PYTHONPATH=. python3 -m swing_screener.analytics.market_snapshot --market india --full # rewrite all history
"""

from __future__ import annotations

import argparse
import logging
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..core.demand_supply import accumulation_distribution_days
from ..marketdata import cache, db

logger = logging.getLogger(__name__)

EMA_FAST = 9               # the short averages a stretch is measured from
EMA_SLOW = 21
WEEKLY_EMAS = (9, 21, 50)  # the higher-timeframe levels, on weekly closes
SMA_MID = 50
SMA_LONG = 200
SLOPE_BARS = 20            # an average's slope: its change over this many sessions
HIGH_BARS = 252            # the 52-week high
DIST_WINDOW = 25           # distribution days are counted over this many sessions
RATIO_BARS = 21            # a ratio line's change: over about a month
RATIO_SMA = 50
REWRITE_DAYS = 10          # a routine run rewrites the last few stored sessions (late corrections to prices)

SCHEMA = """
CREATE TABLE IF NOT EXISTS market_snapshot (
    market VARCHAR(16) NOT NULL,
    date DATE NOT NULL,
    subject VARCHAR(48) NOT NULL,     -- an instrument label, 'market', or a ratio pair 'A/B'
    field VARCHAR(32) NOT NULL,
    value DOUBLE PRECISION,
    PRIMARY KEY (market, date, subject, field)
);
CREATE INDEX IF NOT EXISTS market_snapshot_series ON market_snapshot (market, subject, field, date);
"""


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    scope: str        # instrument | market | pair
    unit: str         # pct | num | count | flag | level
    doc: str


FIELDS = [
    Field("close", "Close", "instrument", "level", "The session's close."),
    Field("chg_pct", "Day change", "instrument", "pct", "Change from the previous close."),
    Field("vs_ema9_pct", f"vs {EMA_FAST}-day EMA", "instrument", "pct",
          f"Close against its {EMA_FAST}-day exponential average; negative = below it. The stretch reading."),
    Field("vs_ema21_pct", f"vs {EMA_SLOW}-day EMA", "instrument", "pct", f"Close against its {EMA_SLOW}-day exponential average."),
    Field("high_vs_ema9_pct", f"High vs {EMA_FAST}-day EMA", "instrument", "pct",
          f"The session's high against its {EMA_FAST}-day EMA: zero or above after a stretch down means the high reached "
          "the average — a retest."),
    Field("vs_sma50_pct", f"vs {SMA_MID}-day", "instrument", "pct", f"Close against its {SMA_MID}-day simple average."),
    Field("vs_sma200_pct", f"vs {SMA_LONG}-day", "instrument", "pct", f"Close against its {SMA_LONG}-day simple average."),
    Field("sma50_slope_pct", f"{SMA_MID}-day slope", "instrument", "pct",
          f"The {SMA_MID}-day average against its value {SLOPE_BARS} sessions earlier."),
    Field("sma200_slope_pct", f"{SMA_LONG}-day slope", "instrument", "pct",
          f"The {SMA_LONG}-day average against its value {SLOPE_BARS} sessions earlier."),
    *[Field(f"vs_wema{n}_pct", f"vs weekly {n} EMA", "instrument", "pct",
            f"Close against the {n}-week EMA of weekly closes, through the last completed week.") for n in WEEKLY_EMAS],
    Field("below_high_pct", "Below 52-week high", "instrument", "pct",
          f"How far the close is under the highest high of the last {HIGH_BARS} sessions (0 = at the high)."),
    Field("dist_days", "Distribution days", "instrument", "count",
          f"Sessions in the last {DIST_WINDOW} closing down 0.2% or more on higher volume than the session before "
          "(core/demand_supply.py). Empty where the instrument's volume is not stored."),
    Field("vol_ratio", "Volume vs 50-day", "instrument", "num", "The session's volume over its 50-day average. Empty without volume."),
    Field("breadth_n", "Stocks counted", "market", "count", "The most-traded stocks breadth is measured on (analytics/breadth.py)."),
    Field("adv_pct", "Advancers", "market", "pct", "Share of those stocks that closed up."),
    Field("above50_pct", "Above 50-day", "market", "pct", "Share closing above their own 50-day average."),
    Field("above5_pct", "Above 5-day", "market", "pct", "Share closing above their own 5-day average."),
    Field("highs", "New highs", "market", "count", "Stocks making a new 52-week high."),
    Field("lows", "New lows", "market", "count", "Stocks making a new 52-week low."),
    Field("up4", "Up 4%+", "market", "count", "Stocks up 4% or more on the day."),
    Field("dn4", "Down 4%+", "market", "count", "Stocks down 4% or more on the day."),
    Field("vol_index", "Volatility index", "market", "level", "The market's volatility index (config `vol_index_symbol`)."),
    Field("vol_index_over", "Volatility vs threshold", "market", "num",
          "The volatility index minus the market's high-volatility threshold (config `vol_threshold`); positive = above it."),
    Field("gate", "Strategies' market gate", "market", "num",
          "The strategies' market filter on the benchmark (backtesting/spec.py `market_ok`, the Minervini guide's test): "
          "1 = risk on, 0 = risk off, a fraction = pilot size while bottoming."),
    Field("ftd", "Follow-through in force", "market", "flag",
          "1 while an O'Neil follow-through day on the benchmark is in force (backtesting/spec.py `follow_through`)."),
    Field("ratio", "Ratio", "pair", "level", "The first instrument's close over the second's."),
    Field("ratio_chg_pct", "Ratio, 1-month change", "pair", "pct",
          f"The ratio's change over {RATIO_BARS} sessions; negative = the broader index is gaining on the cap-weighted one."),
    Field("ratio_vs_sma_pct", f"Ratio vs its {RATIO_SMA}-day", "pair", "pct", f"The ratio against its own {RATIO_SMA}-day average."),
]
FIELD_KEYS = {f.key for f in FIELDS}


def init_schema() -> None:
    with db.get_connection().cursor() as cur:
        cur.execute(SCHEMA)


def instruments(market: str) -> dict[str, str]:
    """label -> ticker: the market's broad indexes, then its review extras."""
    cfg = MARKETS[market]
    return {**cfg.broad_index_symbols, **cfg.review_symbols}


def _pct(a: pd.Series, b: pd.Series) -> pd.Series:
    return (a / b - 1.0) * 100.0


def _weekly_ema(daily: pd.DataFrame, n: int) -> pd.Series:
    """Per session: the n-week EMA of weekly closes through the last week completed BEFORE the session's week."""
    w = ind.ema(ind.resample_weekly(daily)["close"], n).shift(1)
    week_end = daily.index.to_period("W-FRI").end_time.normalize()   # each session's W-FRI week label
    return pd.Series(w.reindex(week_end).to_numpy(), index=daily.index)


def _dist_days(daily: pd.DataFrame) -> pd.Series:
    """accumulation_distribution_days' distribution count on each session's trailing window; NaN when a
    session in the window has no volume."""
    vol = daily["volume"].fillna(0).to_numpy(float)
    out = np.full(len(daily), np.nan)
    for i in range(DIST_WINDOW, len(daily)):
        if (vol[i - DIST_WINDOW: i + 1] > 0).all():
            out[i] = accumulation_distribution_days(daily.iloc[i - DIST_WINDOW: i + 1], DIST_WINDOW)[1]
    return pd.Series(out, index=daily.index)


def instrument_fields(daily: pd.DataFrame) -> pd.DataFrame:
    """date x instrument field, from one instrument's daily OHLCV. Causal: row d reads rows <= d only."""
    c, h = daily["close"].astype(float), daily["high"].astype(float)
    e9, e21 = ind.ema(c, EMA_FAST), ind.ema(c, EMA_SLOW)
    s50, s200 = ind.sma(c, SMA_MID), ind.sma(c, SMA_LONG)
    has_vol = daily["volume"].fillna(0) > 0
    v = daily["volume"].astype(float).where(has_vol)
    out = pd.DataFrame({
        "close": c,
        "chg_pct": _pct(c, c.shift(1)),
        "vs_ema9_pct": _pct(c, e9),
        "vs_ema21_pct": _pct(c, e21),
        "high_vs_ema9_pct": _pct(h, e9),
        "vs_sma50_pct": _pct(c, s50),
        "vs_sma200_pct": _pct(c, s200),
        "sma50_slope_pct": _pct(s50, s50.shift(SLOPE_BARS)),
        "sma200_slope_pct": _pct(s200, s200.shift(SLOPE_BARS)),
        "below_high_pct": (1.0 - c / h.rolling(HIGH_BARS, min_periods=HIGH_BARS).max()) * 100.0,
        "dist_days": _dist_days(daily),
        "vol_ratio": v / v.rolling(50, min_periods=50).mean(),
    }, index=daily.index)
    for n in WEEKLY_EMAS:
        out[f"vs_wema{n}_pct"] = _pct(c, _weekly_ema(daily, n))
    return out


def market_fields(market: str, bench: pd.DataFrame) -> pd.DataFrame:
    """date x market field: breadth, the volatility index, and the strategies' market gate."""
    from ..backtesting import spec
    cfg = MARKETS[market]
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, n, adv, above5, above50, highs, lows, up4, dn4 FROM breadth_daily "
                    "WHERE market=%s AND n > 0 ORDER BY date", (market,))
        rows = cur.fetchall()
    br = pd.DataFrame(rows, columns=["date", "n", "adv", "above5", "above50", "highs", "lows", "up4", "dn4"])
    br.index = pd.DatetimeIndex(br.pop("date"))
    br = br.astype(float)
    out = pd.DataFrame({
        "breadth_n": br["n"], "adv_pct": 100 * br["adv"] / br["n"], "above50_pct": 100 * br["above50"] / br["n"],
        "above5_pct": 100 * br["above5"] / br["n"], "highs": br["highs"], "lows": br["lows"],
        "up4": br["up4"], "dn4": br["dn4"],
    }).reindex(bench.index.union(br.index))
    vix = cache.load_cached(market, cfg.vol_index_symbol)
    if vix is not None and len(vix):
        out["vol_index"] = vix["close"].astype(float).reindex(out.index)
        out["vol_index_over"] = out["vol_index"] - float(cfg.vol_threshold)
    gate = spec.market_ok(market, guide=True).astype(float)
    out["gate"] = gate.reindex(out.index)
    full = gate >= 1.0
    out["ftd"] = spec.follow_through(bench["close"].astype(float), bench["volume"].astype(float).fillna(0.0),
                                     full).astype(float).reindex(out.index)
    return out


def pair_fields(a: pd.DataFrame, b: pd.DataFrame) -> pd.DataFrame:
    r = (a["close"].astype(float) / b["close"].astype(float)).dropna()
    return pd.DataFrame({"ratio": r, "ratio_chg_pct": _pct(r, r.shift(RATIO_BARS)),
                         "ratio_vs_sma_pct": _pct(r, ind.sma(r, RATIO_SMA))})


def compute(market: str) -> dict[str, pd.DataFrame]:
    """subject -> date x field, over all stored history."""
    cfg = MARKETS[market]
    frames, out = {}, {}
    for label, ticker in instruments(market).items():
        d = cache.load_cached(market, ticker)
        if d is None or len(d) < SMA_LONG:
            logger.warning("market snapshot %s: no usable prices for %s (%s)", market, label, ticker)
            continue
        frames[label] = d
        out[label] = instrument_fields(d)
    bench = frames.get(cfg.benchmark_symbol)
    if bench is None:
        bench = cache.load_cached(market, cfg.benchmark_ticker)
    out["market"] = market_fields(market, bench)
    for a, b in cfg.breadth_pairs:
        if a in frames and b in frames:
            out[f"{a}/{b}"] = pair_fields(frames[a], frames[b])
    return out


def run(market: str, full: bool = False) -> dict:
    """Compute and store; a routine run writes from REWRITE_DAYS before the last stored session."""
    init_schema()
    t0 = time.time()
    since = None
    if not full:
        with db.get_connection().cursor() as cur:
            cur.execute("SELECT DISTINCT date FROM market_snapshot WHERE market=%s ORDER BY date DESC LIMIT %s",
                        (market, REWRITE_DAYS))
            ds = [r[0] for r in cur.fetchall()]
        since = pd.Timestamp(ds[-1]) if ds else None
    rows = []
    for subject, df in compute(market).items():
        if since is not None:
            df = df[df.index >= since]
        vals = df.to_numpy(float)
        for i, j in zip(*np.nonzero(np.isfinite(vals))):
            rows.append((market, df.index[i].date(), subject, df.columns[j], float(vals[i, j])))
    db.execute_values("INSERT INTO market_snapshot (market, date, subject, field, value) VALUES %s "
                      "ON CONFLICT (market, date, subject, field) DO UPDATE SET value = EXCLUDED.value", rows)
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM market_snapshot WHERE market=%s", (market,))
        last = cur.fetchone()[0]
    logger.info("market snapshot %s: %d values in %.1fs, latest %s", market, len(rows), time.time() - t0, last)
    return {"values": len(rows), "latest": last, "since": since.date() if since is not None else None}


def read(market: str, date=None) -> dict:
    """One session's readings: {date, subjects: {subject: {field: value}}} -- the latest session (on or before
    `date`) with the benchmark's close, so a day only some sources have reached is never shown half filled."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT max(date) FROM market_snapshot WHERE market=%s AND subject=%s AND field='close' "
                    "AND (%s::date IS NULL OR date <= %s::date)", (market, MARKETS[market].benchmark_symbol, date, date))
        d = cur.fetchone()[0]
        if d is None:
            return {"market": market, "date": None, "subjects": {}}
        cur.execute("SELECT subject, field, value FROM market_snapshot WHERE market=%s AND date=%s", (market, d))
        subjects: dict[str, dict] = {}
        for s, f, v in cur.fetchall():
            subjects.setdefault(s, {})[f] = v
    return {"market": market, "date": d.isoformat(), "subjects": subjects}


def series(market: str, subject: str, field: str) -> list[tuple]:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, value FROM market_snapshot WHERE market=%s AND subject=%s AND field=%s ORDER BY date",
                    (market, subject, field))
        return cur.fetchall()


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--market", required=True, choices=sorted(MARKETS))
    ap.add_argument("--full", action="store_true", help="rewrite all history")
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    print(run(a.market, full=a.full))


if __name__ == "__main__":
    main()
