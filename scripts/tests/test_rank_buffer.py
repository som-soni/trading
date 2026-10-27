"""The rank buffer: buy into the top N, hold until a name ranks outside `hold_rank`.

`baseline.buffered_target` is the rule, and both the backtest (`run`) and the live holdings view
(`current_selection`) call it, so there is one implementation to test. Off (`None`, or any value
not above top N) it must be exactly the old top-N rule -- the check that a switched-off feature
changes nothing -- and on, it must keep held names inside the band, drop them outside it or when
they stop being eligible, and fill free slots best first.

Synthetic data, no database.

    PYTHONPATH=. .venv/bin/python -m tests.test_rank_buffer
"""

import sys
import warnings

import numpy as np
import pandas as pd

from swing_screener.backtesting import baseline as bl
from swing_screener.marketdata import cache

FAILS: list[str] = []
RANKED = [f"R{i:02d}" for i in range(1, 61)]      # R01 is the best, R60 the worst


def check(what: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def _synth(n: int = 80, seed: int = 11):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2017-01-02", "2024-12-31")
    r = rng.normal(rng.normal(0.0004, 0.0004, n), rng.uniform(0.01, 0.03, n), (len(idx), n))
    px = pd.DataFrame(100 * np.exp(np.cumsum(r, axis=0)), index=idx,
                      columns=[f"S{i:03d}" for i in range(n)])
    # (close, dollar volume, SMA200, total-return close): no corporate actions here, so the
    # total-return series is the close itself (run() takes it since 3ae8aa3)
    return px, px * 1e6, px.rolling(200, min_periods=200).mean(), px


def _run(hold_rank):
    kw = dict(market="us", start="2019-01-01", top_n=20, rank="vol_scaled", weighting="inverse_vol",
              cost_bps=50.0, min_dollar_volume=1.0, liquidity_rank_top=None, min_price=1.0)
    with cache.offline():
        tdf, perf, eq, _ = bl.run(preloaded=_synth(), hold_rank=hold_rank, **kw)
    return tdf, eq


def main() -> int:
    bt = bl.buffered_target
    print("the rule")
    check("off (None) is the plain top N", bt(RANKED, [], 20, None) == RANKED[:20])
    check("a band not above top N is the plain top N", bt(RANKED, RANKED[30:40], 20, 20) == RANKED[:20])

    held = ["R25", "R35", "R05"]
    got = bt(RANKED, held, 20, 30)
    check("a held name inside the band is kept", "R25" in got, str(got))
    check("a held name outside the band is dropped", "R35" not in got, str(got))
    check("the book is still top_n long", len(got) == 20, f"{len(got)} names")
    check("no name appears twice", len(set(got)) == len(got))
    check("free slots go to the best names not held",
          set(got) == {"R25", "R05"} | set([s for s in RANKED if s not in held][:18]), str(sorted(got)))

    ineligible = bt([s for s in RANKED if s != "R25"], ["R25"], 20, 30)
    check("a held name that is no longer eligible is dropped", "R25" not in ineligible)
    check("fewer candidates than slots holds them all", bt(RANKED[:7], [], 20, 30) == RANKED[:7])

    print("the backtest")
    t0, e0 = _run(None)
    t20, e20 = _run(20)
    check("run() with the buffer off is identical to a band of top_n",
          len(t0) == len(t20) and np.allclose(e0.values, e20.values), f"{len(t0)} vs {len(t20)} trades")
    t40, _ = _run(40)
    check("a buffer trades less", len(t40) < len(t0), f"{len(t40)} vs {len(t0)} trades")

    print(f"\n{'OK — the rank buffer holds inside its band and is inert when off.' if not FAILS else f'{len(FAILS)} FAILURE(S)'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    warnings.filterwarnings("ignore")
    sys.exit(main())
