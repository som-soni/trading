import datetime as dt
import time

import pandas as pd
import yfinance as yf

from .base import DataProvider

_COLUMNS = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=_COLUMNS)
    df = df.rename(columns=str.lower)
    df = df[[c for c in _COLUMNS if c in df.columns]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df.dropna(subset=["close"])


def _drop_incomplete_bar(df: pd.DataFrame) -> pd.DataFrame:
    """DATA RULE: work on completed bars only. yfinance includes the
    in-progress session as the last row while the market is open; drop it
    if the last bar's date is today."""
    if df.empty:
        return df
    today = pd.Timestamp(dt.date.today())
    if df.index[-1] >= today:
        return df.iloc[:-1]
    return df


class YFinanceProvider(DataProvider):
    def __init__(self, retries: int = 2, pause_sec: float = 0.5):
        self.retries = retries
        self.pause_sec = pause_sec

    def get_daily_bars(
        self, symbol: str, lookback_days: int, start_after: "pd.Timestamp | None" = None
    ) -> pd.DataFrame:
        last_err = None
        for attempt in range(self.retries + 1):
            try:
                if start_after is not None:
                    raw = yf.Ticker(symbol).history(
                        start=(start_after + pd.Timedelta(days=1)).date(),
                        interval="1d",
                        auto_adjust=False,
                    )
                else:
                    period_days = max(lookback_days + 30, 400)  # pad weekends/holidays
                    raw = yf.Ticker(symbol).history(
                        period=f"{period_days}d", interval="1d", auto_adjust=False
                    )
                df = _drop_incomplete_bar(_normalize(raw))
                if not df.empty or start_after is not None:
                    return df
            except Exception as e:  # noqa: BLE001 - surfaced via last_err
                last_err = e
            time.sleep(self.pause_sec)
        if last_err:
            raise last_err
        return pd.DataFrame(columns=_COLUMNS)

    def get_many_daily_bars(
        self, symbols: list[str], lookback_days: int, batch_size: int = 50
    ) -> dict[str, pd.DataFrame]:
        period_days = max(lookback_days + 30, 400)
        out: dict[str, pd.DataFrame] = {}
        symbols = list(dict.fromkeys(symbols))  # de-dupe, preserve order
        for i in range(0, len(symbols), batch_size):
            chunk = symbols[i : i + batch_size]
            try:
                raw = yf.download(
                    chunk,
                    period=f"{period_days}d",
                    interval="1d",
                    group_by="ticker",
                    auto_adjust=False,
                    threads=True,
                    progress=False,
                )
            except Exception:
                raw = None
            for sym in chunk:
                df = pd.DataFrame(columns=_COLUMNS)
                try:
                    if raw is not None and isinstance(raw.columns, pd.MultiIndex):
                        if sym in raw.columns.get_level_values(0):
                            df = _normalize(raw[sym])
                    elif raw is not None and len(chunk) == 1:
                        df = _normalize(raw)
                except Exception:
                    df = pd.DataFrame(columns=_COLUMNS)
                df = _drop_incomplete_bar(df)
                if df.empty:
                    # per-symbol fallback/retry
                    try:
                        df = self.get_daily_bars(sym, lookback_days)
                    except Exception:
                        continue
                if not df.empty:
                    out[sym] = df
            time.sleep(self.pause_sec)
        return out
