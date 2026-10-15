"""The source's placeholder quotes are dropped from a price history, and nothing else is
(swing_screener/marketdata/frozen.py `drop_frozen`).

No database: synthetic histories.

    PYTHONPATH=. .venv/bin/python -m tests.test_frozen
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.marketdata.frozen import FROZEN_MIN_BARS, FROZEN_RESET_BARS, drop_frozen

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}" + (f"  — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS.append(what)


def traded(n: int, start: float, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    c = start * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    return pd.DataFrame({"open": c * 0.995, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e5})


def flat(n: int, px: float, volume=0.0) -> pd.DataFrame:
    return pd.DataFrame({"open": px, "high": px, "low": px, "close": px, "volume": [volume] * n})


def history(*parts: pd.DataFrame) -> pd.DataFrame:
    df = pd.concat(parts, ignore_index=True)
    df.index = pd.bdate_range("2002-01-01", periods=len(df))
    return df


def main() -> int:
    df = history(traded(300, 50))
    check("a traded history is untouched", drop_frozen(df).equals(df))

    df = history(traded(100, 50), flat(FROZEN_MIN_BARS - 1, 40.0), traded(100, 40, 1))
    check("a short flat zero-volume spell (a thin stock) is kept", len(drop_frozen(df)) == len(df))

    df = history(traded(100, 50), flat(FROZEN_MIN_BARS, 40.0), traded(100, 40, 1))
    out = drop_frozen(df)
    check("a month-long frozen run is dropped, the history either side kept", len(out) == 200 and out.index[0] == df.index[0])

    df = history(traded(100, 6), flat(FROZEN_RESET_BARS, 4.97), traded(200, 250, 1))
    out = drop_frozen(df)
    check("after a year-long frozen run the history restarts where trading resumes (GVT&D)",
          len(out) == 200 and out["close"].iloc[0] > 200)

    df = history(traded(300, 80), flat(FROZEN_RESET_BARS + 50, 70.0))
    out = drop_frozen(df)
    check("a stock suspended now loses only its frozen bars", len(out) == 300)

    df = history(traded(100, 50), flat(FROZEN_MIN_BARS + 5, 40.0, volume=500), traded(100, 40, 1))
    check("flat bars that traded are kept (a liquid fund's steady price)", len(drop_frozen(df)) == len(df))

    steps = pd.concat([flat(15, 40.0), flat(15, 41.0)], ignore_index=True)
    df = history(traded(100, 50), steps, traded(100, 41, 1))
    check("a run is one unchanged price: two shorter flat spells are not one run", len(drop_frozen(df)) == len(df))

    half = FROZEN_MIN_BARS // 2 + 1
    df = history(traded(100, 50), flat(half, 9.0), flat(FROZEN_MIN_BARS, 40.0), flat(half, 9.0), traded(100, 9, 1))
    out = drop_frozen(df)
    check("frozen bars joined by removing a run between them are removed too (one pass is final)",
          len(out) == 200 and drop_frozen(out).equals(out))

    print("\nOK" if not FAILS else f"\n{len(FAILS)} failed")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
