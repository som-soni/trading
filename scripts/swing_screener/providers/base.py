import datetime as dt
from abc import ABC, abstractmethod
from contextlib import contextmanager
from contextvars import ContextVar

import pandas as pd


class DataProvider(ABC):
    """Pluggable price-data source. Implementations must return a
    date-indexed DataFrame with columns: open, high, low, close, volume
    (all float/int, ascending date order, one row per completed trading day).
    """

    @abstractmethod
    def get_daily_bars(
        self, symbol: str, lookback_days: int, start_after: "pd.Timestamp | None" = None
    ) -> pd.DataFrame:
        """Return daily OHLCV bars for `symbol`, ending at the last COMPLETED
        bar (no in-progress/live bar).

        If `start_after` is given, implementations SHOULD fetch only bars
        after that date (incremental pull); if they can't do that cheaply,
        falling back to a full `lookback_days` pull and letting the caller
        trim is acceptable — cache.py handles both cases.
        """
        raise NotImplementedError

    def get_many_daily_bars(
        self, symbols: list[str], lookback_days: int
    ) -> dict[str, pd.DataFrame]:
        """Default sequential implementation; providers may override with a
        batched/parallel call. Symbols that fail are omitted from the result
        (caller is responsible for reporting them as 'Not reviewed')."""
        out: dict[str, pd.DataFrame] = {}
        for sym in symbols:
            try:
                df = self.get_daily_bars(sym, lookback_days)
                if df is not None and not df.empty:
                    out[sym] = df
            except Exception:
                continue
        return out


# DATA RULE: completed bars only. Which session is the newest completed one depends on the exchange's
# clock, not this machine's, and a provider is not told the market — so the caller that knows it (the
# cache layer, `cache.market_sessions`) says so here, and providers drop any bar dated after it. Unset,
# today's bar counts as in progress (the machine's date), which is only right when the machine sits in
# the exchange's time zone.
_complete_through: ContextVar[dt.date | None] = ContextVar("complete_through", default=None)


@contextmanager
def complete_through(day: dt.date):
    """Inside the block, bars dated up to `day` are complete and later ones are in progress."""
    token = _complete_through.set(day)
    try:
        yield
    finally:
        _complete_through.reset(token)


def last_complete_session() -> dt.date:
    """The newest bar date a provider may return (see `complete_through`)."""
    return _complete_through.get() or dt.date.today() - dt.timedelta(days=1)
