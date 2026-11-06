"""The Breakout watch screen asks what the breakout anticipation study measured, and nothing else.

No database, no network: synthetic prices. It must hold that the snapshot's windowed pivot_55 /
rs_line_high / obv_high (screens/snapshot.py `_leads`) equal core/indicators' prior_high / at_prior_high /
obv on the full series -- the form analytics/breakout_study.py computes the signals in; that the preset
names only snapshot fields and known markets; and that the study reads the screen's own thresholds.

    PYTHONPATH=. .venv/bin/python -m tests.test_breakout_watch
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.analytics import breakout_study as bs
from swing_screener.config import MARKETS
from swing_screener.core import indicators as ind
from swing_screener.screens import definitions as sdef
from swing_screener.screens import snapshot as sn

FAILS: list[str] = []


def check(what: str, ok: bool, detail="") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}{'' if ok else f'   {detail}'}")
    if not ok:
        FAILS.append(what)


def main() -> None:
    rng = np.random.default_rng(3)
    idx = pd.bdate_range("2020-01-01", periods=700)
    c = pd.Series(100 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, len(idx)))), idx)
    df = pd.DataFrame({"open": c.shift(1).fillna(c.iloc[0]), "high": c * 1.01, "low": c * 0.99, "close": c,
                       "volume": rng.integers(1e5, 1e6, len(idx)).astype(float)}, index=idx)
    bench = pd.Series(3000 * np.exp(np.cumsum(rng.normal(0.0003, 0.01, len(idx)))), idx)
    full = {"pivot_55": ind.prior_high(df["high"], sn.PIVOT_BARS),
            "rs_line_high": ind.at_prior_high(df["close"] / bench, sn.LEAD_HIGH_BARS),
            "obv_high": ind.at_prior_high(ind.obv(df["close"], df["volume"]), sn.LEAD_HIGH_BARS)}
    print("snapshot fields equal the study's full-series signals")
    bad = []
    for i in range(sn.PIVOT_BARS + 2, len(df)):
        got = sn._leads(df, i, bench)
        for k, s in full.items():
            want = float(s.iloc[i]) if k == "pivot_55" else bool(s.iloc[i])
            if (abs(got[k] - want) > 1e-9) if k == "pivot_55" else (got[k] != want):
                bad.append((idx[i].date(), k, got[k], want))
    check("pivot_55, rs_line_high and obv_high agree on every bar", not bad, bad[:3])
    check("some bars are new highs (the test is not vacuous)", full["rs_line_high"].sum() > 10 and full["obv_high"].sum() > 10)

    print("the preset")
    p = sdef.presets()["breakout_watch"]
    fields = {x["field"] for x in p["conditions"]} | {x["ref"] for x in p["conditions"] if x.get("ref")}
    check("every condition names a snapshot field", fields <= set(sn.FIELD_KEYS), fields - set(sn.FIELD_KEYS))
    check("its markets are configured markets", set(p["markets"]) <= set(MARKETS), p["markets"])
    check("the study's candidate rule reads the screen's constants",
          bs.NEAR_PIVOT == 1 - sdef.BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT / 100 and bs.NEAR_HIGH == sdef.BREAKOUT_WATCH_MIN_FRAC_OF_52W_HIGH)
    check("the screen is the study's frozen US rule A",
          bs.FROZEN["us"]["A_greedy"] == ["R2_rs_new_high_first", "V4_obv_at_55d_high", "K4_group_rs_70"])

    print(f"\n{'FAILED: ' + ', '.join(FAILS) if FAILS else 'OK — Breakout watch screens exactly what the study measured'}")
    sys.exit(1 if FAILS else 0)


if __name__ == "__main__":
    main()
