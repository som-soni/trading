"""Draw a pattern, then check the detector finds it.

`core/chart_patterns.py` is pure geometry over an OHLCV frame, so unlike the
golden-baseline harness this needs no database and no market data: each case
builds a synthetic chart with one pattern carved into it and asserts the
matching detector fires with sane geometry.

Three things are checked beyond "does it fire":

  * **no pivot leakage** — spiking the LAST bar's high must not move any
    pivot. If it does, every pattern breaks out by construction and a
    backtest of the strategy is worthless;
  * **the noise floor** — how often a pure random walk produces each shape.
    Not zero, and for three of them not far off their rate in the real
    market, which is the most decision-relevant fact in this module;
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


def cup_no_handle() -> pd.DataFrame:
    """A cup whose price is still pinned to the rim — no handle yet."""
    return frame(np.concatenate([
        ramp(40, 100, 210), ramp(100, 76, 30),
        75 + 1.0 * np.sin(np.linspace(0, np.pi, 25)),
        ramp(76, 99.5, 30),
        99.5 + rng.uniform(-0.4, 0.2, 6),   # six flat bars at the rim
        [99.6],
    ]))


def double_top() -> pd.DataFrame:
    """Two peaks at one level, then a break of the neckline that holds."""
    return frame(np.concatenate([
        ramp(40, 100, 250),                 # advance into the first peak
        ramp(100, 84, 20), ramp(84, 99, 20),  # trough, then the second peak
        ramp(99, 80, 25), [79.0],           # roll over, through the neckline
    ]))


def head_shoulders_top() -> pd.DataFrame:
    """Left shoulder, higher head, right shoulder, then the neckline goes."""
    return frame(np.concatenate([
        ramp(40, 92, 245),
        ramp(92, 80, 12),                   # left shoulder done
        ramp(80, 100, 15), ramp(100, 80, 15),   # the head
        ramp(80, 91, 12), ramp(91, 77, 18),     # right shoulder, then down
        [76.0],
    ]))


CASES = (
    ("cup-and-handle, broken out", cup_handle(True), cp.CUP),
    ("cup-and-handle, still coiled", cup_handle(False), cp.CUP),
    ("flat base", flat_base(), cp.FLAT),
    ("bull flag", bull_flag(), cp.FLAG),
    ("double bottom", double_bottom(), cp.DBOT),
    ("ascending triangle", ascending_triangle(), cp.ATRI),
    ("volatility contraction", vcp(), cp.VCP),
    ("cup without handle", cup_no_handle(), cp.CUPNH),
)

# Bearish structures. They must NEVER come back from `detect_patterns`, which
# feeds entry logic — only from `detect_topping`.
TOPPING_CASES = (
    ("double top", double_top(), cp.DTOP),
    ("head and shoulders top", head_shoulders_top(), cp.HSTOP),
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
              f"move={hit.measured_move:.2f} q={hit.quality:.2f} "
              f"conf={hit.confidence}")
        if not hit.stop_ref < hit.pivot:
            failures.append(f"{label}: stop {hit.stop_ref} not below pivot {hit.pivot}")
        if not hit.measured_move > 0:
            failures.append(f"{label}: non-positive measured move")
        if not 0.0 <= hit.quality <= 1.0:
            failures.append(f"{label}: quality {hit.quality} outside 0-1")
        # a chart drawn to the textbook should grade as one; if it does not,
        # either the drawing or the ideal bounds are wrong
        if want == cp.CUP and hit.confidence != "textbook":
            failures.append(
                f"{label}: a deliberately textbook cup graded "
                f"'{hit.confidence}' ({hit.flaw_text})"
            )

    for label, df, want in TOPPING_CASES:
        tops = {m.code: m for m in cp.detect_topping(df)}
        hit = tops.get(want)
        if hit is None:
            failures.append(f"{label}: expected {want}, got {sorted(tops) or 'nothing'}")
            print(f"FAIL  {label:<30} expected {want}, got {sorted(tops) or 'nothing'}")
        else:
            print(f"ok    {label:<30} {want} neckline={hit.pivot:.2f} "
                  f"q={hit.quality:.2f} | {hit.note}")
            if not hit.is_bearish:
                failures.append(f"{label}: {want} is not marked bearish")
        # the entry path must never see a topping structure
        leaked = [m.code for m in cp.detect_patterns(df) if m.is_bearish]
        if leaked:
            failures.append(f"{label}: bearish {leaked} leaked into detect_patterns()")

    # The current bar may not define a pivot: see the module docstring.
    spiked = cup_handle(True).copy()
    spiked.iloc[-1, spiked.columns.get_loc("high")] = 500.0
    leaked = {m.code: m.pivot for m in cp.detect_patterns(spiked) if m.pivot > 120}
    if leaked:
        failures.append(f"a 500.00 spike on the last bar leaked into pivots: {leaked}")
    print(f"ok    {'last-bar spike ignored':<30} "
          f"pivots unchanged ({len(leaked)} leaked)")

    # --- how often does NOISE produce these shapes? ---
    #
    # This is the detectors' false-positive floor, and the most important
    # number in the file. A pattern that a random walk produces as readily as
    # a stock does cannot carry information, however famous its name: the
    # measured rates below say VCP, DBOT and FLAT are nearly as common in
    # noise as in the market (a live scan of 519 liquid US names put VCP at
    # 27%, DBOT 27%, FLAT 11%), while CUP is genuinely rare in both.
    #
    # Measured 2026-10-04 over these 150 seeded walks: 75% showed at least one
    # pattern — VCP 44.0%, FLAT 31.3%, DBOT 30.7%, FLAG 11.3%, ATRI 8.7%,
    # CUPNH 4.7%, CUP 0.7%. The ceilings below are regression guards a few
    # points above that, NOT targets: loosening a detector fails here loudly.
    TRIALS = 150
    CEILINGS = {"CUP": 0.05, "CUPNH": 0.08, "ATRI": 0.12, "FLAG": 0.15,
                "FLAT": 0.33, "DBOT": 0.38, "VCP": 0.45}
    noise_rng = np.random.default_rng(2024)
    hits, per_code = 0, {}
    for _ in range(TRIALS):
        walk = 100 * np.exp(np.cumsum(noise_rng.normal(0.0003, 0.018, 420)))
        n = len(walk)
        noise_df = pd.DataFrame(
            {
                "open": walk,
                "high": walk * (1 + noise_rng.uniform(0.001, 0.006, n)),
                "low": walk * (1 - noise_rng.uniform(0.001, 0.006, n)),
                "close": walk,
                "volume": noise_rng.lognormal(13.8, 0.35, n),
            },
            index=pd.bdate_range("2019-01-02", periods=n),
        )
        codes = {m.code for m in cp.detect_patterns(noise_df)}
        hits += bool(codes)
        for code in codes:
            per_code[code] = per_code.get(code, 0) + 1

    print(f"\n      random-walk false positives over {TRIALS} walks: "
          f"{hits / TRIALS * 100:.0f}% show at least one pattern")
    for code, n_hit in sorted(per_code.items(), key=lambda kv: -kv[1]):
        rate = n_hit / TRIALS
        ceiling = CEILINGS.get(code, 0.20)
        mark = "ok   " if rate <= ceiling else "OVER "
        print(f"      {mark} {code:<6} {rate * 100:5.1f}%  (ceiling {ceiling * 100:.0f}%)")
        if rate > ceiling:
            failures.append(
                f"{code} fires on {rate * 100:.0f}% of random walks, over its "
                f"{ceiling * 100:.0f}% ceiling — it has been loosened"
            )
    if hits / TRIALS > 0.80:
        failures.append(
            f"{hits / TRIALS * 100:.0f}% of random walks match something; the "
            f"detector set as a whole has lost what selectivity it had"
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
    print(f"All {len(CASES) + len(TOPPING_CASES)} patterns detected, no pivot "
          f"leakage, every detector inside its noise ceiling.")


if __name__ == "__main__":
    main()
