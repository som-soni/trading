from abc import ABC, abstractmethod

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
