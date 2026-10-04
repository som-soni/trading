"""Draw a pattern, then check the detector finds it.

`core/chart_patterns.py` is pure geometry over an OHLCV frame, so unlike the
golden-baseline harness this needs no database and no market data: each case
builds a synthetic chart with one pattern carved into it and asserts the
matching detector fires with sane geometry.

Three things are checked beyond "does it fire":

  * **no pivot leakage** — spiking the LAST bar's high must not move any
    pivot. If it does, every pattern breaks out by construction and a
    backtest of the strategy is worthless;
  * **no detection on noise** — a pure random walk should produce nothing;
  * **geometry sanity** — stop below pivot, positive measured move.

Run: `PYTHONPATH=. python3 -m tests.test_chart_patterns`
"""

import sys

import numpy as np
import pandas as pd

from swing_screener.core import chart_patterns as cp

rng = np.random.default_rng(11)


def frame(close: np.ndarray, vol: np.ndarray | None = None) -> pd.DataFrame:
    """OHLCV around a close path, with small wicks and flat volume."""
    n = len(close)
    return pd.DataFrame(
        {
            "open": close + rng.normal(0, 0.002, n) * close,
            "high": close + rng.uniform(0.001, 0.006, n) * close,
            "low": close - rng.uniform(0.001, 0.006, n) * close,
            "close": close,
            "volume": vol if vol is not None else np.full(n, 1_000_000.0),
        },
        index=pd.bdate_range("2019-01-02", periods=n),
    )


def ramp(a: float, b: float, n: int) -> np.ndarray:
    return np.linspace(a, b, n, endpoint=False)


# --- the charts ------------------------------------------------------------


def cup_handle(breakout: bool) -> pd.DataFrame:
    close = np.concatenate([
        ramp(40, 100, 210),                              # advance to the left rim
        ramp(100, 76, 30),                               # left side of the cup
        75 + 1.0 * np.sin(np.linspace(0, np.pi, 25)),    # rounded bottom
        ramp(76, 99, 30),                                # right side
        ramp(99, 93, 10),                                # the handle drifts down
        [100.5] if breakout else [96.0],
    ])
    vol = np.concatenate([
        np.full(210, 1e6), np.full(30, 1.2e6), np.full(25, 0.7e6),
        np.full(30, 1.1e6), np.full(10, 0.5e6),          # handle dries up
        [3e6] if breakout else [0.5e6],
    ])
    return frame(close, vol)


def flat_base() -> pd.DataFrame:
    return frame(np.concatenate([
        ramp(40, 100, 245),                  # the prior advance
        100 + rng.uniform(-6, 0.5, 60),      # a shallow box under the high
        [101.0],
    ]))


def bull_flag() -> pd.DataFrame:
    return frame(np.concatenate([
        ramp(40, 70, 270), ramp(70, 100, 25), ramp(100, 92, 12), [96.0],
    ]))


def double_bottom() -> pd.DataFrame:
    return frame(np.concatenate([
        ramp(40, 100, 200),                               # advance to correct
        ramp(100, 72, 25), ramp(72, 90, 25),              # first low, middle peak
        ramp(90, 71, 25), ramp(71, 88, 25), [89.5],       # second low, recovery
    ]))


def ascending_triangle() -> pd.DataFrame:
    legs = []
    for lo, nxt in ((86, 91), (91, 95), (95, 97)):        # lows close the gap
        legs += [ramp(lo, 100, 12), ramp(100, nxt, 12)]   # against flat 100
    return frame(np.concatenate([ramp(40, 90, 240), *legs, [99.0]]))


def vcp() -> pd.DataFrame:
    close = np.concatenate([
        ramp(40, 100, 235),
        ramp(100, 78, 15), ramp(78, 99, 15),   # -22%
        ramp(99, 88, 12), ramp(88, 98, 12),    # -11%
        ramp(98, 93, 8), ramp(93, 97.5, 8),    # -5%
        [97.8],
    ])
    vol = np.concatenate([
        np.full(235, 1e6), np.full(30, 1.4e6), np.full(24, 1.0e6),
        np.full(16, 0.6e6), [0.6e6],
    ])
    return frame(close, vol)


CASES = (
    ("cup-and-handle, broken out", cup_handle(True), cp.CUP),
    ("cup-and-handle, still coiled", cup_handle(False), cp.CUP),
    ("flat base", flat_base(), cp.FLAT),
    ("bull flag", bull_flag(), cp.FLAG),
    ("double bottom", double_bottom(), cp.DBOT),
    ("ascending triangle", ascending_triangle(), cp.ATRI),
    ("volatility contraction", vcp(), cp.VCP),
)


def main() -> None:
    failures: list[str] = []

    for label, df, want in CASES:
        matches = {m.code: m for m in cp.detect_patterns(df)}
        hit = matches.get(want)
        if hit is None:
            failures.append(f"{label}: expected {want}, got {sorted(matches) or 'nothing'}")
            print(f"FAIL  {label:<30} expected {want}, got {sorted(matches) or 'nothing'}")
            continue
        print(f"ok    {label:<30} {want} pivot={hit.pivot:.2f} stop={hit.stop_ref:.2f} "
              f"move={hit.measured_move:.2f} q={hit.quality:.2f}")
        if not hit.stop_ref < hit.pivot:
            failures.append(f"{label}: stop {hit.stop_ref} not below pivot {hit.pivot}")
        if not hit.measured_move > 0:
            failures.append(f"{label}: non-positive measured move")
        if not 0.0 <= hit.quality <= 1.0:
            failures.append(f"{label}: quality {hit.quality} outside 0-1")

    # The current bar may not define a pivot: see the module docstring.
    spiked = cup_handle(True).copy()
    spiked.iloc[-1, spiked.columns.get_loc("high")] = 500.0
    leaked = {m.code: m.pivot for m in cp.detect_patterns(spiked) if m.pivot > 120}
    if leaked:
        failures.append(f"a 500.00 spike on the last bar leaked into pivots: {leaked}")
    print(f"ok    {'last-bar spike ignored':<30} "
          f"pivots unchanged ({len(leaked)} leaked)")

    # Noise should not produce patterns.
    walk = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, 400)))
    noise = cp.detect_patterns(frame(walk))
    print(f"ok    {'random walk':<30} "
          f"{[(m.code, round(m.quality, 2)) for m in noise] or 'nothing detected'}")
    if noise:
        failures.append(
            "random walk produced " + ", ".join(f"{m.code} q={m.quality:.2f}" for m in noise)
        )

    # A frame too short for the longest base must return nothing, not raise.
    if cp.detect_patterns(frame(ramp(10, 20, cp.MIN_BARS - 1))):
        failures.append("detected a pattern on a frame shorter than MIN_BARS")

    print()
    if failures:
        print(f"{len(failures)} FAILURE(S):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    print(f"All {len(CASES)} patterns detected; no leakage, no false positive on noise.")


if __name__ == "__main__":
    main()
