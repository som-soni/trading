"""Oliver Kell's cycle of price action, found bar by bar (research/kell-cycle-spec.md, draft 1).

One causal pass over a stock's daily bars: the phase each session is in, and the levels a trade
on it would use. The rules are the spec's section 2, with the section-4 changes that make draft 1:

  RX  reversal extension   close at least `ext_down_atr` ATR under the 20-EMA
  WP  wedge pop            within `pop_lookback` sessions of an RX or of `down_days` closes under both
                           EMAs, and the cycle not already in an uptrend: a close above both EMAs and the
                           highest high of the prior `pop_high_days` sessions, on volume >= `pop_vol` x
                           its 50-day average. Stop: the pop day's low
  CB  EMA crossback        in an uptrend (today and yesterday), yesterday's low came within
                           `cross_touch_atr` ATR of the 20-EMA (or under it) and yesterday closed at or
                           above it; today closes above yesterday's high. Stop: yesterday's low.
                           `cb_first`: the first CB after a WP or BB in this cycle (draft 1, change 1)
  BB  base-n-break         in an uptrend, the prior `base_min_days` sessions span at most
                           `base_max_width` high to low; today closes above that high (yesterday did
                           not), on volume >= `break_vol` x. Stop: the base low
  EX  exhaustion           in an uptrend, a close at least `exh_atr` ATR above the 10-EMA, or a gap up of
                           `gap_atr` ATR or more when yesterday already closed `gap_prior_atr` ATR above it
  BK  EMA break            after an uptrend (draft 1, change 2), `break_mode` 1: a close under the 20-EMA
                           by at least `break_atr` ATR; 2: a close under the most recent crossback's low
                           (before any crossback in the cycle, the latest WP / BB stop; with neither, rule 1)

An uptrend session has EMA10 > EMA20 on each of the last `up_cross_days` sessions (draft 1, change 4),
EMA20 above its value `up_slope_days` sessions earlier, and the close above the 50-day average. The cycle
is "in an uptrend" from the first such session (or a WP) until a BK.

`leg` counts the WP, BB and CB events: a new advance starts at each, and the exhaustion sale is made
once per leg. Every value on bar i reads bars up to i only, so scanning a prefix gives the prefix of the
full scan (`Scanner` relies on it to advance incrementally). No trade decisions here: the strategy
(strategies/kell_cycle.py) and the backtest's `--exit-mode kell` read these columns.
"""

from collections import OrderedDict
from dataclasses import dataclass

import pandas as pd

# the enriched daily columns the scan reads (core/indicators.enrich_daily)
COLUMNS = ("open", "high", "low", "close", "volume", "ema10", "ema20", "sma50", "atr14", "vol_sma50")
FLAGS = ("rx", "wp", "cb", "cb_first", "bb", "ex", "bk", "up", "in_up")
LEVELS = ("wp_stop", "cb_stop", "bb_stop", "bb_top", "break_ref")
NAN = float("nan")


@dataclass(frozen=True)
class CycleParams:
    """Every number the scan uses. No defaults: the strategy passes its own module constants, so they
    are the ones the fingerprint covers and `--const` moves."""
    ext_down_atr: float
    down_days: int
    pop_lookback: int
    pop_high_days: int
    pop_vol: float
    cross_touch_atr: float
    base_min_days: int
    base_max_width: float
    break_vol: float
    exh_atr: float
    gap_atr: float
    gap_prior_atr: float
    up_slope_days: int
    up_cross_days: int
    break_mode: int
    break_atr: float


class Scanner:
    """The scan's state after bar n-1, and every bar's output so far. `advance` continues it."""

    def __init__(self, p: CycleParams):
        self.p = p
        self.n = 0
        self.out = {k: [] for k in FLAGS + LEVELS + ("leg",)}
        # cycle state
        self.in_up = False
        self.anchor = -1          # the last RX, or the last session ending `down_days` closes under both EMAs
        self.had_leg = False      # a WP or BB since the last BK (the first CB after one is an entry)
        self.cb_since = 0         # CBs since the last WP / BB
        self.leg = 0
        self.cb_low = NAN         # the most recent CB's stop in this cycle
        self.entry_low = NAN      # the most recent WP / BB stop in this cycle
        self.dates = None
        self.first_date = None

    def _push(self, **v) -> None:
        for k in self.out:
            self.out[k].append(v.get(k, 0 if k in FLAGS else NAN) if k != "leg" else self.leg)

    def advance(self, a: dict, n: int) -> None:
        """Process bars self.n .. n-1 of the column arrays `a` (COLUMNS -> numpy)."""
        p = self.p
        o, h, l, c, v = a["open"], a["high"], a["low"], a["close"], a["volume"]
        e10, e20, s50, at, v50 = a["ema10"], a["ema20"], a["sma50"], a["atr14"], a["vol_sma50"]
        warm = max(p.up_slope_days, p.up_cross_days, p.down_days, p.pop_high_days, p.base_min_days) + 1
        for i in range(self.n, n):
            ci, ai = c[i], at[i]
            if i < warm or not (ai == ai and e20[i] == e20[i] and e10[i] == e10[i] and s50[i] == s50[i]
                                and e20[i - p.up_slope_days] == e20[i - p.up_slope_days] and ai > 0):
                self._push(in_up=int(self.in_up))
                continue
            row = {}
            up = (e20[i] > e20[i - p.up_slope_days] and ci > s50[i]
                  and all(e10[j] > e20[j] for j in range(i - p.up_cross_days + 1, i + 1)))
            row["up"] = int(up)
            if ci <= e20[i] - p.ext_down_atr * ai:
                row["rx"] = 1
                self.anchor = i
            if all(c[j] < e20[j] and c[j] < e10[j] for j in range(i - p.down_days, i)):
                self.anchor = i
            vol_ok = v50[i] == v50[i] and v50[i] > 0
            if (self.anchor >= 0 and i - self.anchor <= p.pop_lookback and not self.in_up
                    and ci > e10[i] and ci > e20[i] and ci > max(h[i - p.pop_high_days:i])
                    and vol_ok and v[i] >= p.pop_vol * v50[i]):
                row.update(wp=1, wp_stop=float(l[i]))
                self.in_up, self.anchor, self.had_leg, self.cb_since = True, -1, True, 0
                self.leg += 1
                self.entry_low = float(l[i])
                row.update(in_up=1, break_ref=self._ref())
                self._push(**row)
                continue
            if up:
                self.in_up = True
                j = i - 1
                up_prev = (e20[j] > e20[j - p.up_slope_days] and c[j] > s50[j]
                           and all(e10[k] > e20[k] for k in range(j - p.up_cross_days + 1, j + 1)))
                cb = (up_prev and l[j] <= e20[j] + p.cross_touch_atr * at[j] and c[j] >= e20[j] and ci > h[j])
                lo_b, hi_b = float(min(l[i - p.base_min_days:i])), float(max(h[i - p.base_min_days:i]))
                bb = (lo_b > 0 and hi_b / lo_b - 1 <= p.base_max_width and ci > hi_b and c[i - 1] <= hi_b
                      and vol_ok and v[i] >= p.break_vol * v50[i])
                if (ci >= e10[i] + p.exh_atr * ai
                        or (o[i] - h[j] >= p.gap_atr * ai and c[j] >= e10[j] + p.gap_prior_atr * at[j])):
                    row["ex"] = 1
                if cb:
                    row.update(cb=1, cb_first=int(self.had_leg and self.cb_since == 0), cb_stop=float(l[j]))
                    self.cb_since += 1
                    self.cb_low = float(l[j])
                    self.leg += 1
                if bb:
                    row.update(bb=1, bb_stop=lo_b, bb_top=hi_b)
                    self.had_leg, self.cb_since = True, 0
                    self.entry_low = lo_b
                    if not cb:
                        self.leg += 1
            if self.in_up and not row.get("cb") and not row.get("bb"):
                ref = self._ref()
                if p.break_mode == 2 and ref == ref:
                    brk = ci < ref
                else:
                    brk = ci < e20[i] - p.break_atr * ai
                if brk:
                    row["bk"] = 1
                    self.in_up, self.had_leg, self.cb_since = False, False, 0
                    self.cb_low = self.entry_low = NAN
            row.update(in_up=int(self.in_up), break_ref=self._ref())
            self._push(**row)
        self.n = n

    def _ref(self) -> float:
        return self.cb_low if self.cb_low == self.cb_low else self.entry_low

    def row(self, i: int) -> dict:
        return {k: self.out[k][i] for k in self.out}


def _arrays(df: pd.DataFrame) -> dict:
    return {k: df[k].to_numpy(dtype=float) for k in COLUMNS}


def scan(df: pd.DataFrame, p: CycleParams) -> pd.DataFrame:
    """Every session's phase flags and levels, as a frame on df's index (df: enrich_daily output)."""
    s = Scanner(p)
    if len(df):
        s.advance(_arrays(df), len(df))
    out = pd.DataFrame(s.out, index=df.index)
    for k in FLAGS:
        out[k] = out[k].astype(bool)
    return out


# Incremental scans by symbol, for the per-bar strategy evaluation: a backtest asks for session after
# session of the same stock, each a longer prefix of one frame, so the scan continues where it stopped
# instead of starting over (it is causal, so the answer is the same). Bounded, oldest dropped.
_CACHE: "OrderedDict[tuple, Scanner]" = OrderedDict()
_CACHE_MAX = 64


def last(symbol: str, daily: pd.DataFrame, p: CycleParams) -> dict:
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
        s.advance(_arrays(daily), n)
    return s.row(n - 1)


def pop_count(df: pd.DataFrame, p: CycleParams) -> int:
    """How many wedge pops the scan finds in df -- the volume diagnostic (spec section 4) runs it at
    several `pop_vol` values."""
    return int(scan(df, p)["wp"].sum()) if len(df) else 0
