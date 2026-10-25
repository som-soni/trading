"""Market-regime switch for the monthly portfolio runners: at a rebalance, is the market "on"?

One shared rule, honoured by `baseline.run(regime=...)` (momentum_baseline, momentum_vol_scaled and
any ranking strategy the baseline runner backtests). While the regime is OFF at a rebalance the
book holds no stocks and its cash earns the stored cash rate (index_data.cash_rate_series); the
next rebalance with the regime ON buys again. Default is off (`regime=None`), so a strategy's own
runs do not change.

    index_sma  the benchmark's close is above its INDEX_SMA_DAYS-day simple average
    breadth    at least BREADTH_MIN_PCT % of the liquid universe closes above its own 200-day average
    both       both of the above

Point in time: each test reads only closes up to and including the rebalance session, the same
close the runner trades at -- exactly as the per-stock 200-day trend filter already does. The
thresholds were fixed before any run (the Learn guide's 200-day trend rule; 40% as the breadth
floor), not tuned. The constants live HERE, not in baseline.py, so adding the option moves no
strategy's fingerprint; a strategy that adopts a regime by default must bump its version.

Breadth caveat: the universe is today's listed names (the runner's survivorship bias), so the
share above the 200-day is somewhat flattered in bad years -- delisted losers are missing.
"""

import pandas as pd

KINDS = ("index_sma", "breadth", "both")

INDEX_SMA_DAYS = 200        # (a) benchmark close vs its N-day simple average
BREADTH_MIN_PCT = 40.0      # (b) floor on the % of liquid names above their own 200-day average


def breadth_pct200(px: pd.DataFrame, sma200: pd.DataFrame, dv: pd.DataFrame,
                   liq_floor: float | None) -> pd.Series:
    """Per date: % of names closing above their own 200-day average, among those with a 200-day
    average and (when `liq_floor` is given) 20-day average turnover at or above it."""
    have = px.notna() & sma200.notna()
    if liq_floor:
        have &= dv.reindex_like(px) >= liq_floor
    above = (px > sma200) & have
    n = have.sum(axis=1)
    return (100.0 * above.sum(axis=1) / n.where(n > 0)).astype(float)


def regime_on(kind: str, index: pd.DatetimeIndex, *, bench_px: pd.Series | None,
              px: pd.DataFrame, sma200: pd.DataFrame, dv: pd.DataFrame,
              liq_floor: float | None) -> pd.Series:
    """Boolean per date in `index`: True = the market is on. A date a test cannot judge (too little
    history) counts as on for that test, so missing data never manufactures a cash month."""
    if kind not in KINDS:
        raise ValueError(f"regime must be one of {KINDS}, not {kind!r}")
    ok = pd.Series(True, index=index)
    if kind in ("index_sma", "both"):
        if bench_px is None or bench_px.empty:
            raise ValueError("the index_sma regime needs a benchmark series")
        c = bench_px.astype(float)
        sma = c.rolling(INDEX_SMA_DAYS, min_periods=INDEX_SMA_DAYS).mean()
        # asof: a date the benchmark did not print reads its last close, never a later one
        above = (c > sma).where(sma.notna())
        ok &= above.reindex(index, method="ffill").fillna(True).astype(bool)
    if kind in ("breadth", "both"):
        br = breadth_pct200(px, sma200, dv, liq_floor).reindex(index)
        ok &= (br >= BREADTH_MIN_PCT).where(br.notna(), True).astype(bool)
    return ok
