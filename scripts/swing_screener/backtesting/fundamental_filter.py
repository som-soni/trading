"""SEPA part 2 in a backtest: Minervini's fundamental tests, applied point in time to each signal.

The Fundamentals page judges today's numbers (`fundamentals/sepa.py` over `fundamentals/growth.py`).
This applies the same tests to the results a trader could have read ON THE SIGNAL DATE:

  * a stored quarter counts only once it was public — its filing date (`quarterly_results.filed`), or,
    when the source recorded none, FILING_LAG_DAYS after the quarter ended;
  * growth, margins, annual EPS and ROE are recomputed from those quarters alone, with no Quality-page
    ROE fallback (that is today's figure);
  * F7 (beat the consensus estimate) is never available: estimates are not stored point in time. The
    LEADER verdict does not need it, and F6 may be unavailable without failing.

Levels (`--fundamentals`):
  covered     keep signals whose company can be scored on that date (any verdict but NO DATA) — the
              CONTROL: fundamental history exists for only part of the universe, and only from 2021, so
              "has good fundamentals" must be compared with "is in the covered set", not with everything;
  acceptable  verdict ACCEPTABLE or LEADER;
  leader      verdict LEADER.

Each kept signal carries its verdict in meta["sepa"], so trades can be broken down by it.
"""

import datetime as dt
import logging
from dataclasses import replace

import pandas as pd

logger = logging.getLogger(__name__)

LEVELS = ("covered", "acceptable", "leader")
PASSING = {"covered": {"WEAK", "ACCEPTABLE", "LEADER"}, "acceptable": {"ACCEPTABLE", "LEADER"}, "leader": {"LEADER"}}
FILING_LAG_DAYS = 60     # a quarter without a recorded filing date is treated as public this long after it ended


def _available(row: dict) -> dt.date:
    f = row.get("filed")
    if f is not None:
        return f.date() if isinstance(f, dt.datetime) else f
    return row["period_end"] + dt.timedelta(days=FILING_LAG_DAYS)


def verdicts(market: str, signals: list) -> dict:
    """{(symbol, date): verdict} for every signal, from the quarters public on that date."""
    from fundamentals import growth, sepa
    from ..marketdata import financials
    syms = sorted({s.symbol for s in signals})
    data = financials.load(market, syms)
    cache: dict = {}          # (symbol, quarters known) -> (verdict, latest quarter end)
    out = {}
    for s in signals:
        d = pd.Timestamp(s.date).date()
        rows = sorted((r for r in data.get(s.symbol, []) if _available(r) <= d), key=lambda r: r["period_end"])
        if not rows:
            out[(s.symbol, s.date)] = "NO DATA"
            continue
        key = (s.symbol, len(rows))
        if key not in cache:
            latest_end = rows[-1]["period_end"]
            m = growth.metrics(rows, None, today=latest_end, roe_fallback=None)   # staleness is judged below
            cache[key] = (sepa.evaluate(m)["verdict"], latest_end)
        verdict, latest_end = cache[key]
        if (d - latest_end).days > growth.STALE_RESULTS_DAYS:
            verdict = "NO DATA"        # the company had stopped filing, as of that date
        out[(s.symbol, s.date)] = verdict
    return out


def filter_signals(signals: list, market: str, level: str) -> tuple[list, dict]:
    if level not in LEVELS:
        raise ValueError(f"--fundamentals must be one of {LEVELS}")
    v = verdicts(market, signals)
    kept, counts = [], {}
    for s in signals:
        x = v[(s.symbol, s.date)]
        counts[x] = counts.get(x, 0) + 1
        if x in PASSING[level]:
            kept.append(replace(s, meta={**s.meta, "sepa": x}))
    logger.info("Fundamentals (%s): kept %d of %d signals; verdicts %s", level, len(kept), len(signals), counts)
    return kept, {"level": level, "kept": len(kept), "of": len(signals), "verdicts": counts}
