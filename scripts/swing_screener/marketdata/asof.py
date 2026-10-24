"""A date boundary every backtest read honours — what keeps a hold-out held out.

Inside `with asof.boundary(end, label):` the loaders a backtest reads through return nothing dated
after `end`: prices (`cache.load_cached`, `load_many_cached`, `load_cached_with_indicators`), stored
index series (`index_data.load`, and `total_return_index` / `cash_rate_series` built on it),
quarterly results (`financials.load`), group RS history (`group_history.load`), and the series the
two portfolio runners read directly (`fno_income`, `pead`).

So a run inside an optimisation window cannot see the years kept back to verify it -- not through a
price, an indicator, a universe filter or a "latest" lookup -- and no runner has to remember to stop:
its calendar simply ends where its data does. Enforcing it here rather than per runner is the point.
Nine runners each taking an `end` argument is nine chances to forget one; one boundary in the data
layer is none. tests/test_backtest_stages.py fails if any of those loaders reads past it.

`label` is the stage the boundary belongs to (`backtesting/windows.py`). `paths.run_dir` appends it to
every run directory made inside the boundary, so a windowed run never overwrites a full one, and
ingest can file the run under its stage.

Outside a boundary nothing changes: every loader behaves exactly as before.
"""

import contextlib

import pandas as pd

_END: pd.Timestamp | None = None
_LABEL: str | None = None


@contextlib.contextmanager
def boundary(end, label: str | None = None):
    """Read nothing dated after `end` (None = no end) and tag run directories with `label`."""
    global _END, _LABEL
    prev = (_END, _LABEL)
    _END = pd.Timestamp(end).normalize() if end is not None else None
    _LABEL = label
    try:
        yield
    finally:
        _END, _LABEL = prev


def end() -> pd.Timestamp | None:
    return _END


def end_date():
    """The boundary as a date, for SQL parameters; None when there is none."""
    return _END.date() if _END is not None else None


def label() -> str | None:
    return _LABEL


def clip(obj):
    """Drop rows dated after the boundary from a date-indexed frame or series."""
    if _END is None or obj is None:
        return obj
    return obj.loc[obj.index <= _END]
