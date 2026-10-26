"""A recorded stray run is fixed once, and re-applying it changes nothing (marketdata/splits.py).

PSUBNKBEES.NS carries two bars the source serves at a tenth of the price (2019-12-19/20). They are
recorded by hand as a `stray_run`, and `correct` re-applies recorded runs after a re-fetch -- so the
off-scale test must fire on the broken bars and NOT on bars already put back, or every scheduled run
would multiply them by ten again.

Synthetic bars; no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_stray_runs
"""

import sys

import pandas as pd

from swing_screener.marketdata.splits import _rescale, offscale_run

FAILS: list[str] = []
IDX = pd.bdate_range("2019-12-09", periods=14)
RUN = [IDX[6], IDX[7]]


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _broken() -> pd.DataFrame:
    close = [28.0, 27.9, 28.3, 28.1, 27.7, 27.6, 2.77, 2.83, 27.8, 27.75, 27.6, 28.3, 27.7, 27.8]
    vol = [20_000] * 14
    vol[6], vol[7] = 903_290, 354_850
    return pd.DataFrame({"open": close, "high": [c * 1.01 for c in close], "low": [c * 0.99 for c in close],
                         "close": close, "volume": vol}, index=IDX)


def main() -> int:
    print("a recorded stray run is found while broken, and left alone once fixed")
    df = _broken()

    m = offscale_run(df, RUN, 0.1)
    check("both broken bars are flagged", list(df.index[m]) == RUN, str(list(df.index[m])))

    fixed = _rescale(df, m, 1 / 0.1)
    check("rescaled onto the neighbours' scale", abs(fixed.loc[RUN[0], "close"] - 27.7) < 0.01
          and abs(fixed.loc[RUN[1], "close"] - 28.3) < 0.01, str(fixed.loc[RUN, "close"].tolist()))
    check("volume divided by the same factor", fixed.loc[RUN[0], "volume"] == 90_329,
          str(fixed.loc[RUN[0], "volume"]))

    again = offscale_run(fixed, RUN, 0.1)
    check("re-applying to fixed bars flags nothing (idempotent)", not again.any(), str(list(fixed.index[again])))

    check("a date outside the history flags nothing",
          not offscale_run(df, [pd.Timestamp("2018-01-01")], 0.1).any())
    check("a recorded date that is on scale is not touched",
          not offscale_run(df, [IDX[3]], 0.1).any())

    print(f"\n{'OK — recorded stray runs are fixed once.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
