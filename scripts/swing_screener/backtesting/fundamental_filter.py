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
  leader      verdict LEADER;
  guide       the SEPA Learn guide's tests, with the minervini strategy's FUND_* thresholds: quarterly
              EPS growth on the year-ago quarter at least FUND_EPS_GROWTH_MIN_PCT% and faster than the
              quarter before, sales growth at least FUND_SALES_GROWTH_MIN_PCT%, and net margin no more
              than FUND_MARGIN_SLACK_PP points below the year-ago quarter's. Any of those unknown fails.

Each kept signal carries its verdict in meta["sepa"], so trades can be broken down by it.
"""

import datetime as dt
import logging
from dataclasses import replace

import pandas as pd

logger = logging.getLogger(__name__)

LEVELS = ("covered", "acceptable", "leader", "guide")
PASSING = {"covered": {"WEAK", "ACCEPTABLE", "LEADER"}, "acceptable": {"ACCEPTABLE", "LEADER"}, "leader": {"LEADER"},
           "guide": {"GUIDE PASS"}}


def guide_verdict(m: dict) -> str:
    """The SEPA guide's fundamentals on one company's metrics (fundamentals/growth.py): GUIDE PASS / GUIDE FAIL."""
    from ..strategies import minervini_spec as ms
    eg, sg = m.get("eps_g") or [], m.get("rev_g") or []
    if len(eg) < 2 or eg[0] is None or eg[1] is None or not sg or sg[0] is None:
        return "GUIDE FAIL"
    mg, mp = m.get("margin"), m.get("margin_prior")
    ok = (eg[0] >= ms.FUND_EPS_GROWTH_MIN_PCT / 100 and eg[0] > eg[1]
          and sg[0] >= ms.FUND_SALES_GROWTH_MIN_PCT / 100
          and mg is not None and mp is not None and mg >= mp - ms.FUND_MARGIN_SLACK_PP / 100)
    return "GUIDE PASS" if ok else "GUIDE FAIL"
FILING_LAG_DAYS = 60     # a quarter without a recorded filing date is treated as public this long after it ended


def _available(row: dict) -> dt.date:
    f = row.get("filed")
    if f is not None:
        return f.date() if isinstance(f, dt.datetime) else f
    return row["period_end"] + dt.timedelta(days=FILING_LAG_DAYS)


def verdicts(market: str, signals: list, level: str = "leader") -> dict:
    """{(symbol, date): verdict} for every signal, from the quarters public on that date. The verdict
    is the SEPA page's, or with level "guide", GUIDE PASS / GUIDE FAIL."""
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
            v = sepa.evaluate(m)["verdict"]
            if level == "guide" and v != "NO DATA":
                v = guide_verdict(m)
            cache[key] = (v, latest_end)
        verdict, latest_end = cache[key]
        if (d - latest_end).days > growth.STALE_RESULTS_DAYS:
            verdict = "NO DATA"        # the company had stopped filing, as of that date
        out[(s.symbol, s.date)] = verdict
    return out


def annotate_signals(signals: list, market: str) -> tuple[list, dict]:
    """Attach each signal's SEPA verdict as meta["sepa"] and drop nothing.

    The same point-in-time judgement `filter_signals` uses, recorded rather than acted on, so every
    trade in a run carries the fundamentals its company showed ON ITS SIGNAL DATE and the report can
    be read by verdict without the fundamentals gate changing which trades were taken. Today's score
    would be the wrong number against a trade from 2013: this is the one a trader could have read.
    """
    v = verdicts(market, signals)
    counts: dict = {}
    for s in signals:
        x = v[(s.symbol, s.date)]
        counts[x] = counts.get(x, 0) + 1
    return ([replace(s, meta={**s.meta, "sepa": v[(s.symbol, s.date)]}) for s in signals],
            {"verdicts": counts, "of": len(signals)})


def filter_signals(signals: list, market: str, level: str) -> tuple[list, dict]:
    if level not in LEVELS:
        raise ValueError(f"--fundamentals must be one of {LEVELS}")
    v = verdicts(market, signals, level)
    kept, counts = [], {}
    for s in signals:
        x = v[(s.symbol, s.date)]
        counts[x] = counts.get(x, 0) + 1
        if x in PASSING[level]:
            kept.append(replace(s, meta={**s.meta, "sepa": x}))
    logger.info("Fundamentals (%s): kept %d of %d signals; verdicts %s", level, len(kept), len(signals), counts)
    return kept, {"level": level, "kept": len(kept), "of": len(signals), "verdicts": counts}
