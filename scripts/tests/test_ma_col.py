"""An exit that reads a moving average refuses one the price frames do not carry.

`bar.get(missing)` is NaN, every comparison with NaN is False, and the exit then never fires --
silently. `--ma-col sma10` ran a whole earnings_gaps backtest that way (no daily 10-day average is
computed): zero trend exits, one position held 3,262 days, reported as the best variant.

Synthetic bars, no database and no cached prices.

    PYTHONPATH=. .venv/bin/python -m tests.test_ma_col
"""

import sys

import pandas as pd

from swing_screener.backtesting.portfolio_sim import ExitPolicy, MA_COL_MODES, Signal, check_ma_col, simulate
from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind

FAILS: list[str] = []


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _frame() -> pd.DataFrame:
    idx = pd.bdate_range("2021-01-04", periods=260)
    c = pd.Series([100.0 + i * 0.1 for i in range(len(idx))], index=idx)
    raw = pd.DataFrame({"open": c, "high": c * 1.01, "low": c * 0.99, "close": c, "volume": 1e6})
    return ind.enrich_daily(raw)


def _refuses(policy: ExitPolicy, frames: dict) -> str | None:
    try:
        check_ma_col(policy, frames)
    except ValueError as exc:
        return str(exc)
    return None


def main() -> int:
    df = _frame()
    frames = {"TEST": df}
    print("the exit's average must exist on the daily frames")

    err = _refuses(ExitPolicy(mode="ma", ma_col="sma10"), frames)
    check("ma mode refuses sma10, which daily frames do not carry", err is not None)
    if err:
        check("...and names the averages that do exist", "sma20" in err and "ema10" in err, err)

    for mode in sorted(MA_COL_MODES):
        check(f"{mode} accepts sma50, which they do", _refuses(ExitPolicy(mode=mode, ma_col="sma50"), frames) is None)

    check("a mode that does not read ma_col ignores it",
          _refuses(ExitPolicy(mode="bracket", ma_col="sma10"), frames) is None)

    # the guard runs inside simulate itself, so no caller can bypass it
    sig = Signal(date=df.index[220], symbol="TEST", setup="S1", entry=float(df["close"].iloc[220]) * 1.01,
                 stop=float(df["close"].iloc[220]) * 0.9, target=float(df["close"].iloc[220]) * 2,
                 decision="TRADE - HIGH CONFIDENCE")
    try:
        simulate([sig], frames, MARKETS["us"], start=df.index[200],
                 exit_policy=ExitPolicy(mode="ma", ma_col="sma10", use_target=False))
        check("simulate refuses an exit with a missing average", False, "it ran")
    except ValueError:
        check("simulate refuses an exit with a missing average", True)

    print(f"\n{'OK — an exit cannot read an average that is not there.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
