"""Undercut and reclaim, found bar by bar (research/undercut-reclaim-spec.md, draft 0).

One causal pass over a stock's daily bars. On each session it asks:

  base      the `base_bars` sessions ending `undercut_window` sessions before today: support = their lowest
            low, pivot = their highest high, pivot / support - 1 at most `base_max_pct` %, and support
            tested -- at least `min_touches` swing lows (lowest of the 2 bars either side) within
            `touch_pct` % of it, at least `swing_sep` sessions apart
  undercut  the `undercut_window` sessions before today: their lowest low is under support, by at most
            `undercut_max_atr` ATR
  hold      no close from the undercut window's start to today is under the `hold_col` line by more than
            `hold_atr` ATR (the stand-in for the weekly 21-EMA; spec section 3)
  S1        reclaim: all of the above, yesterday closed at or under support and today closes above it, and
            no S1 in the previous `rearm_bars` sessions (one per base). Stop: the undercut low
  S2        within `s2_window` sessions after an S1: H = the highest high from the S1 session to yesterday,
            with at least one session after it; the higher low = the lowest low since H, above the undercut
            low; today closes above H. One per S1. Stop: the higher low
  BO        the comparison entry: within `bo_window` sessions after an S1, the first close above that
            base's pivot. Stop: the undercut low

A close under the undercut low ends an S1's S2 and BO watch. Every value on bar i reads bars up to i only,
so a prefix's scan is the prefix of the full scan (`last` relies on it). No trade decisions here: the
strategy (strategies/undercut_reclaim.py) reads these columns.
"""

from collections import OrderedDict
from dataclasses import dataclass

import numpy as np
import pandas as pd

# the enriched daily columns the scan reads (core/indicators.enrich_daily)
COLUMNS = ("high", "low", "close", "atr14")   # plus the hold line, `Params.hold_col`
FLAGS = ("s1", "s2", "bo")
LEVELS = ("support", "pivot", "undercut_low", "s1_stop", "s2_stop", "bo_stop", "touches")
NAN = float("nan")


@dataclass(frozen=True)
class Params:
    """Every number the scan uses. No defaults: the strategy passes its own module constants, so they are
    the ones the fingerprint covers and `--const` moves."""
    base_bars: int
    undercut_window: int
    base_max_pct: float
    min_touches: int
    touch_pct: float
    swing_sep: int
    undercut_max_atr: float
    hold_col: str           # the enrich_daily column the undercut must hold (e.g. "ema100")
    hold_atr: float
    rearm_bars: int
    s2_window: int
    bo_window: int


def touches(lows: np.ndarray, support: float, touch_pct: float, swing_sep: int) -> int:
    """Swing lows (the lowest of the 2 bars either side, ties allowed) within `touch_pct` % of `support`,
    counted at least `swing_sep` bars apart."""
    n, last, lim = 0, -10 ** 9, support * (1 + touch_pct / 100)
    for i in range(len(lows)):
        if lows[i] <= lim and lows[i] <= lows[max(0, i - 2):i + 3].min() and i - last >= swing_sep:
            n += 1
            last = i
    return n


class Scanner:
    """The scan's state after bar n-1, and every bar's output so far. `advance` continues it."""

    def __init__(self, p: Params):
        self.p = p
        self.n = 0
        self.out = {k: [] for k in FLAGS + LEVELS}
        self.last_s1 = -10 ** 9
        self.k = -1                 # the bar of the S1 being watched (-1: none)
        self.u = NAN                # its undercut low
        self.pivot = NAN            # its base's pivot
        self.s2_open = self.bo_open = False
        self.dates = self.closes = None
        self.first_date = None

    def _push(self, row: dict) -> None:
        for k in self.out:
            self.out[k].append(row.get(k, 0 if k in FLAGS else NAN))

    def advance(self, a: dict, n: int) -> None:
        """Process bars self.n .. n-1 of the column arrays `a` (COLUMNS -> numpy)."""
        p = self.p
        h, l, c, e100, at = a["high"], a["low"], a["close"], a["hold"], a["atr14"]
        warm = p.base_bars + p.undercut_window + 2
        for i in range(self.n, n):
            row: dict = {}
            if i < warm or not (at[i] == at[i] and at[i] > 0 and e100[i] == e100[i]):
                self._push(row)
                continue
            # ---- the S1 being watched: S2, the comparison breakout, or its end
            if self.k >= 0:
                row.update(undercut_low=self.u, pivot=self.pivot)
                if c[i] < self.u:
                    self.k, self.s2_open, self.bo_open = -1, False, False
                else:
                    if self.s2_open:
                        if i - self.k > p.s2_window:
                            self.s2_open = False
                        else:
                            seg = h[self.k:i]
                            m = self.k + len(seg) - 1 - int(np.argmax(seg[::-1]))   # the last bar at the high
                            if m < i - 1:
                                hl = float(l[m + 1:i].min())
                                if hl > self.u and c[i] > seg.max():
                                    row.update(s2=1, s2_stop=hl)
                                    self.s2_open = False
                    if self.bo_open:
                        if i - self.k > p.bo_window:
                            self.bo_open = False
                        elif c[i] > self.pivot:
                            row.update(bo=1, bo_stop=self.u)
                            self.bo_open = False
                    if not (self.s2_open or self.bo_open):
                        self.k = -1
            # ---- S1: a base, an undercut of its support, the trend held, the reclaim today
            b1 = i - p.undercut_window
            b0 = b1 - p.base_bars
            s, piv = float(l[b0:b1].min()), float(h[b0:b1].max())
            if (s > 0 and (piv / s - 1) * 100 <= p.base_max_pct and c[i] > s and c[i - 1] <= s
                    and i - self.last_s1 > p.rearm_bars):
                ul = float(l[b1:i].min())
                if (ul < s and s - ul <= p.undercut_max_atr * at[i]
                        and not (c[b1:i + 1] < e100[b1:i + 1] - p.hold_atr * at[b1:i + 1]).any()):
                    t = touches(l[b0:b1], s, p.touch_pct, p.swing_sep)
                    if t >= p.min_touches:
                        row.update(s1=1, s1_stop=ul, support=s, pivot=piv, undercut_low=ul, touches=t)
                        self.last_s1, self.k, self.u, self.pivot = i, i, ul, piv
                        self.s2_open = self.bo_open = True
            self._push(row)
        self.n = n

    def row(self, i: int) -> dict:
        return {k: self.out[k][i] for k in self.out}


def _arrays(df: pd.DataFrame, p: Params) -> dict:
    if p.hold_col not in df.columns:
        raise KeyError(f"undercut_reclaim reads {p.hold_col!r}, which the daily frame does not carry")
    a = {k: df[k].to_numpy(dtype=float) for k in COLUMNS}
    a["hold"] = df[p.hold_col].to_numpy(dtype=float)
    return a


def scan(df: pd.DataFrame, p: Params) -> pd.DataFrame:
    """Every session's flags and levels, as a frame on df's index (df: enrich_daily output)."""
    s = Scanner(p)
    if len(df):
        s.advance(_arrays(df, p), len(df))
    out = pd.DataFrame(s.out, index=df.index)
    for k in FLAGS:
        out[k] = out[k].astype(bool)
    return out


# Incremental scans by symbol, for the per-bar strategy evaluation: a backtest asks for session after session
# of the same stock, each a longer prefix of one frame, so the scan continues where it stopped (it is causal,
# so the answer is the same). Bounded, oldest dropped. The same scheme as core/kell_cycle.py.
_CACHE: "OrderedDict[tuple, Scanner]" = OrderedDict()
_CACHE_MAX = 64


def last(symbol: str, daily: pd.DataFrame, p: Params) -> dict:
    """The scan's output on the last bar of `daily`, reusing an earlier scan of the same frame."""
    n = len(daily)
    if n == 0:
        return {}
    key = (symbol, p)
    s = _CACHE.get(key)
    idx = daily.index
    ok = False
    if s is not None and s.n > 0 and s.first_date == idx[0]:
        j = min(n, s.n) - 1     # the last bar both have: the same session, the same close
        ok = idx[j] == s.dates[j] and daily["close"].iat[j] == s.closes[j]
    if not ok:
        s = Scanner(p)
        s.first_date, s.dates, s.closes = idx[0], [], []
        _CACHE[key] = s
        while len(_CACHE) > _CACHE_MAX:
            _CACHE.popitem(last=False)
    else:
        _CACHE.move_to_end(key)
    if n > s.n:
        tail = daily.iloc[s.n:]
        s.dates.extend(tail.index)
        s.closes.extend(tail["close"].to_numpy(dtype=float).tolist())
        s.advance(_arrays(daily, p), n)
    return s.row(n - 1)
