"""The point-in-time fundamentals universe (backtesting/fundamentals_universe.py): every stock a backtest
could have ranked has been asked about by the filings source, so a fundamentals-filtered backtest is not
reading today's fetch list into the past. Needs the database.

A market whose `financials_backfill` job has never finished is reported and skipped: the gap is the
known look-ahead until the job runs. After it has run, a stock still never fetched is a failure --
the job's list and this one disagree, or a fetch was lost.

    PYTHONPATH=. python3 -m tests.test_fundamentals_universe
"""

import sys

from jobs.registry import _last_ok
from swing_screener.backtesting import fundamentals_universe as fu
from swing_screener.config import MARKETS
from swing_screener.marketdata import universe


def test_floor_is_the_lowest():
    """The set uses the lowest floor any backtest ranks above, so it covers every strategy's pool."""
    from swing_screener.strategies import portfolio_strategies
    for m in MARKETS:
        floor = fu.turnover_floor(m)
        assert floor <= MARKETS[m].screener.min_dollar_volume
        for cls in portfolio_strategies().values():
            if hasattr(cls, "min_turnover_for") and cls.min_turnover_for(m):
                assert floor <= cls.min_turnover_for(m), (m, cls.key)


def check_fetched() -> list[str]:
    failures = []
    for m in MARKETS:
        syms = fu.symbols(m)
        gone = fu.never_fetched(m, syms)
        print(f"{m}: {len(syms):,} stocks liquid at some month-end since {universe.LIQUID_EVER_SINCE}, "
              f"{len(gone):,} never fetched")
        if not _last_ok("financials_backfill", m):
            print(f"  skipped: financials_backfill has not finished for {m} yet")
        elif gone:
            failures.append(f"{m}: {len(gone)} never fetched after the backfill, e.g. {sorted(gone)[:10]}")
    return failures


if __name__ == "__main__":
    test_floor_is_the_lowest()
    print("ok test_floor_is_the_lowest")
    bad = check_fetched()
    for b in bad:
        print("FAIL", b)
    sys.exit(1 if bad else 0)
