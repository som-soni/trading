"""The fast per-symbol context path must be identical to the slow one.

build_context is called once per qualifying bar on a growing slice of the same
history, so it re-derives the daily, weekly and monthly frames every time --
quadratic, and ~89% of a scan. `prepare_frames` does that work once and
build_context(frames=..., as_of=...) slices it.

"Identical" is the whole claim, so it is checked rather than argued: every
StockContext field, plus the full contents of the weekly and monthly frames,
against a context built the slow way from the truncated history.

Two traps this is really guarding:

  * resample labels a period by its END (W-FRI, ME). Slicing the full resample
    at a Wednesday drops that week entirely, where the truncated frame would
    have a partial week -- and ctx.monthly's last row is read directly by
    trend_pullback, ctx.weekly by screens/criteria.
  * history_months is len(monthly). Slicing loses the current partial month, so
    it comes from a precomputed per-bar month count instead.

    PYTHONPATH=. .venv/bin/python -m tests.test_context_frames
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.core import context as ctx_mod
from swing_screener.marketdata import cache

SYMBOLS = {"india": ["SBIN.NS", "TITAN.NS", "COALINDIA.NS"], "us": ["MU", "AAPL"]}
EVERY = 37  # a prime stride, so sampled dates land on every weekday and month position


def _frames_equal(a: pd.DataFrame, b: pd.DataFrame) -> str | None:
    if list(a.index) != list(b.index):
        if len(a) != len(b):
            return f"different length: {len(a)} vs {len(b)}"
        return "different index"
    for col in ("open", "high", "low", "close", "volume"):
        if col not in a.columns or col not in b.columns:
            continue
        x, y = a[col].to_numpy(dtype=float), b[col].to_numpy(dtype=float)
        if not np.allclose(x, y, rtol=1e-9, atol=1e-9, equal_nan=True):
            return f"column {col} differs"
    return None


def _check_symbol(market: str, symbol: str) -> tuple[int, list[str]]:
    raw = cache.load_cached(market, symbol)
    if raw is None or len(raw) < 400:
        return 0, []
    frames = ctx_mod.prepare_frames(raw)
    dates = list(raw.index[300::EVERY])
    bad: list[str] = []
    for d in dates:
        slow = ctx_mod.build_context(symbol, raw.loc[:d])
        fast = ctx_mod.build_context(symbol, raw, frames=frames, as_of=d)
        if (slow is None) != (fast is None):
            bad.append(f"{symbol} {d.date()}: one path returned None, the other did not")
            continue
        if slow is None:
            continue
        for field in ("h_value", "l_value", "p_value", "prior_swing_low", "history_months"):
            x, y = getattr(slow, field), getattr(fast, field)
            same = (x == y) or (
                isinstance(x, float) and isinstance(y, float)
                and np.isclose(x, y, rtol=1e-9, atol=1e-9, equal_nan=True)
            )
            if not same:
                bad.append(f"{symbol} {d.date()}: {field} {x!r} vs {y!r}")
        if str(slow.h_index) != str(fast.h_index):
            bad.append(f"{symbol} {d.date()}: h_index {slow.h_index} vs {fast.h_index}")
        if slow.overhead != fast.overhead:
            bad.append(f"{symbol} {d.date()}: overhead levels differ")
        if len(slow.daily) != len(fast.daily):
            bad.append(f"{symbol} {d.date()}: daily length {len(slow.daily)} vs {len(fast.daily)}")
        for name, sf, ff in (("weekly", slow.weekly, fast.weekly), ("monthly", slow.monthly, fast.monthly)):
            why = _frames_equal(sf, ff)
            if why:
                bad.append(f"{symbol} {d.date()}: {name} {why}")
        # the last row of each is read directly downstream (trend_pullback, criteria)
        for name, sf, ff in (("weekly", slow.weekly, fast.weekly), ("monthly", slow.monthly, fast.monthly)):
            if len(sf) and len(ff) and "sma10" in sf.columns and "sma10" in ff.columns:
                x, y = sf["sma10"].iloc[-1], ff["sma10"].iloc[-1]
                if not np.isclose(float(x), float(y), rtol=1e-9, atol=1e-9, equal_nan=True):
                    bad.append(f"{symbol} {d.date()}: {name} last sma10 {x} vs {y}")
    return len(dates), bad


def main() -> int:
    total, problems, checked = 0, [], []
    for market, syms in SYMBOLS.items():
        for sym in syms:
            try:
                n, bad = _check_symbol(market, sym)
            except Exception as exc:  # noqa: BLE001 - a missing cache must not look like a pass
                problems.append(f"{sym}: raised {type(exc).__name__}: {exc}")
                continue
            if n:
                checked.append(f"{sym} ({n} dates)")
                total += n
            problems.extend(bad)

    if not total:
        print("FAIL — no cached symbols to compare against; this test proved nothing")
        return 1
    if problems:
        print(f"FAIL — the fast context path differs from the slow one ({len(problems)} problems):")
        for p in problems[:25]:
            print("  " + p)
        if len(problems) > 25:
            print(f"  ... and {len(problems) - 25} more")
        return 1
    print(f"OK — fast and slow context paths identical over {total} dates: {', '.join(checked)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
