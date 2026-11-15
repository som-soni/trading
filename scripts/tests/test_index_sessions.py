"""An index a session behind the stocks: kept out of the cache and the movers' change.

India's evening run (19:26 IST, 6 Nov 2026) stored 6 Nov for 3,344 stocks but not for ^CRSLDX or any other
index: the provider dropped every bar dated on or after the machine's date, and the machine sits in IST.
Two things followed from it, each checked here on hand-made data:

  * the provider keeps a bar once its exchange's session is complete (`providers.base.complete_through`,
    set per market by `cache.market_sessions` from `freshness.expected_session`), and still drops an
    in-progress one -- including a US bar fetched after midnight IST;
  * Movers reports the index's change as unknown, not 0.00%, when the index ends before the stocks' day.

    PYTHONPATH=. .venv/bin/python -m tests.test_index_sessions
"""

import datetime as dt
import sys

import pandas as pd

from swing_screener.marketdata import cache, freshness
from swing_screener.providers.base import complete_through, last_complete_session
from swing_screener.providers.yfinance_provider import _drop_incomplete_bar

FAILS: list[str] = []
UTC = dt.timezone.utc


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _bars(*days: str) -> pd.DataFrame:
    idx = pd.DatetimeIndex(pd.to_datetime(list(days)))
    return pd.DataFrame({"open": 1.0, "high": 1.0, "low": 1.0, "close": 1.0, "volume": 0}, index=idx)


def test_provider() -> None:
    print("the provider keeps a bar once its exchange's session is complete")
    df = _bars("2026-11-05", "2026-11-06")
    # 19:26 IST on Friday 6 Nov: NSE closed at 15:30, past the 17:00 data cutoff
    evening = dt.datetime(2026, 11, 6, 13, 56, tzinfo=UTC)
    with complete_through(freshness.expected_session("india", evening)):
        kept = _drop_incomplete_bar(df)
    check("India's evening run keeps the day's bar", kept.index[-1] == pd.Timestamp("2026-11-06"), str(kept.index[-1]))
    # 13:30 IST the same day: the session is still open
    with complete_through(freshness.expected_session("india", dt.datetime(2026, 11, 6, 8, 0, tzinfo=UTC))):
        kept = _drop_incomplete_bar(df)
    check("an India run during the session drops it", kept.index[-1] == pd.Timestamp("2026-11-05"), str(kept.index[-1]))
    # 00:30 IST on 7 Nov is 14:00 in New York on 6 Nov: the US session is in progress
    with complete_through(freshness.expected_session("us", dt.datetime(2026, 11, 6, 19, 0, tzinfo=UTC))):
        kept = _drop_incomplete_bar(df)
    check("a US fetch after midnight IST drops the in-progress US bar", kept.index[-1] == pd.Timestamp("2026-11-05"),
          str(kept.index[-1]))
    with complete_through(freshness.expected_session("us", dt.datetime(2026, 11, 6, 23, 0, tzinfo=UTC))):
        kept = _drop_incomplete_bar(df)
    check("a US fetch after the close keeps it", kept.index[-1] == pd.Timestamp("2026-11-06"), str(kept.index[-1]))
    check("outside a market's block, today's bar is in progress (the machine's date)",
          last_complete_session() == dt.date.today() - dt.timedelta(days=1), str(last_complete_session()))
    for m in ("us", "india"):
        with cache.market_sessions(m):
            got = last_complete_session()
        check(f"cache.market_sessions({m!r}) is the market's expected session", got == freshness.expected_session(m),
              f"{got} vs {freshness.expected_session(m)}")
    # the index provider (niftyindices.com) uses the same rule
    from swing_screener.marketdata.official_indices import _frame
    with complete_through(freshness.expected_session("india", evening)):
        f = _frame(pd.to_datetime(["2026-11-05", "2026-11-06"]), [1, 1], [1, 1], [1, 1], [1, 1])
    check("the official index provider keeps it too", f.index[-1] == pd.Timestamp("2026-11-06"), str(f.index[-1]))


def test_movers_bench() -> None:
    print("Movers: the index's change is unknown when it ends before the stocks' day")
    from swing_screener.web import server
    series = {dt.date(2026, 11, 4): 100.0, dt.date(2026, 11, 5): 101.0}

    def q(sql, params):
        d = params[-1]
        rows = [(c, day) for day, c in sorted(series.items()) if day <= d]
        return [rows[-1]] if rows else []
    real_q = server.q
    server.q = q
    try:
        stale = server._bench_change("india", dt.date(2026, 11, 5), dt.date(2026, 11, 6))
        series[dt.date(2026, 11, 6)] = 102.01
        fresh = server._bench_change("india", dt.date(2026, 11, 5), dt.date(2026, 11, 6))
    finally:
        server.q = real_q
    check("an index ending 5 Nov gives no change for 6 Nov (not 0.00%)", stale["pct"] is None, str(stale))
    check("and says where it ends", stale["date"] == "2026-11-05", str(stale))
    check("an index with 6 Nov gives its change", fresh["pct"] is not None and abs(fresh["pct"] - 1.0) < 1e-9, str(fresh))


def main() -> int:
    test_provider()
    test_movers_bench()
    print(f"\n{'OK — an index a session behind is never read as the stocks’ day.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
