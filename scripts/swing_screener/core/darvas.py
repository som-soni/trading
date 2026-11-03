"""Darvas boxes, detected with his confirmation rules (research/learn-strat-darvas.md, section 3).

One implementation for every reader: the darvas strategy's entry (strategies/darvas.py) and the
darvas exit mode's trailing stop (backtesting/portfolio_sim.py) both call `scan`.

    top      a session whose high is the highest of the last `lookback` sessions (itself included),
             and the next `top_confirm` sessions' highs are all lower. Known on the last of those.
    bottom   the lowest low after the top, once `bottom_confirm` sessions in a row have not gone
             below it (an equal low holds it), while no high went above the top.
    restart  a high above the top before the bottom is confirmed: no box. The search starts again,
             and the session that broke out may itself be the next top.
    done     the session that confirms the bottom. A box exists from that session on, never before.

The scan walks the bars forward once and reads nothing after the bar it is on, so it is causal: the
boxes found on `bars[:n]` are exactly the boxes found on the full history whose `done_i` is below n
(tests/test_darvas_exit.py checks it). That is what lets a backtest scan a symbol once and read each
day's boxes off the result, and what lets `scan` resume from a saved state when the history grows.

No depth filter here: the entry refuses a deep box (MAX_BOX_DEPTH_PCT), but a deep box still raises
a trailing stop, as the guide's Bharat Electronics example shows.
"""

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass(frozen=True)
class Box:
    top_i: int        # bar of the box top
    top: float
    bottom_i: int     # bar of the box bottom
    bottom: float
    done_i: int       # bar that confirmed the bottom: the box is complete from its close

    @property
    def depth_pct(self) -> float:
        return (self.top - self.bottom) / self.top * 100 if self.top else math.nan


@dataclass
class ScanState:
    """Where a scan stopped, so a longer history with the same prefix can continue from it."""
    t: int = 0                  # next bar to read
    seeking: str = "top"        # "top" | "bottom"
    min_k: int = 0              # earliest bar a new top may sit on
    top_i: int = -1
    top: float = math.nan
    low_i: int = -1             # lowest low since the top, while seeking the bottom
    low: float = math.nan
    boxes: list = field(default_factory=list)


def scan(high: np.ndarray, low: np.ndarray, lookback: int, top_confirm: int, bottom_confirm: int,
         state: ScanState | None = None) -> ScanState:
    """Every complete box in `high` / `low`, oldest first, in `state.boxes`.

    With `state` (a previous scan of a PREFIX of these same bars), only the new bars are read and
    `state` is updated in place. The caller is responsible for the prefix being the same bars."""
    st = state if state is not None else ScanState()
    n = len(high)
    for t in range(st.t, n):
        if st.seeking == "top":
            k = t - top_confirm
            if k >= max(st.min_k, lookback - 1):
                hk = high[k]
                if hk >= np.nanmax(high[k - lookback + 1: k + 1]) and bool((high[k + 1: t + 1] < hk).all()):
                    st.seeking, st.top_i, st.top = "bottom", k, float(hk)
                    seg = low[k + 1: t + 1]
                    j = int(np.argmin(seg))          # first occurrence: an equal low later holds it
                    st.low_i, st.low = k + 1 + j, float(seg[j])
                    # the top's confirming bars are below the top by definition; fall through to
                    # test the bottom on this same bar
        elif st.seeking == "bottom":
            if high[t] > st.top:
                # broke out before the bottom was confirmed: no box, and this bar may be the next top
                st.seeking, st.min_k = "top", t
                continue
            if low[t] < st.low:
                st.low_i, st.low = t, float(low[t])
        if st.seeking == "bottom" and t - st.low_i >= bottom_confirm:
            st.boxes.append(Box(st.top_i, st.top, st.low_i, st.low, t))
            st.seeking, st.min_k = "top", t + 1
    st.t = max(st.t, n)
    return st


def boxes(high, low, lookback: int, top_confirm: int, bottom_confirm: int) -> list[Box]:
    """Every complete box, oldest first: a fresh `scan`."""
    return scan(np.asarray(high, dtype=float), np.asarray(low, dtype=float),
                lookback, top_confirm, bottom_confirm).boxes
