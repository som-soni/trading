"""Masonson's TQQQ timing — hold a 3x Nasdaq 100 fund only while the index is in an uptrend.

From Les Masonson's Tradeline interview ("The TQQQ Trading Strategy of a 47+ Years Trader"; creator
note research/creator-les-masonson.md). He names the parts of the workshop strategy he is building
(70:20-74:40) but not their settings, and warns against overfitting them, so every rule here is a
SWITCH with a textbook setting fixed before the first run (see the 1.0 changelog entry):

    trend filter   the index closes above its 200-day average -- "no longs below it" (68:35)
    MACD           the histogram is above zero (12, 26, 9; his intraday 6, 13, 5 as a variant)
    RSI extreme    RSI(7) closed below 30 within the last few sessions -- a buy after a drop
    Keltner        a close below the lower 2-ATR band within the last few sessions
    breadth        under 20% of Nasdaq 100 members above their 50-day within the last few sessions
    exit           a close below the 20-day EMA (he names 8, 10 and 20; 20 is the loosest)

Signals are read on the close of the Nasdaq 100 index (^NDX) and filled at the next session's open.

THE INSTRUMENT IS SYNTHETIC. TQQQ lists in February 2010, so a 2013 start has it but the 2000-2012
stress test does not. `synthetic()` builds a daily-reset 3x series from ^NDX: each day 3x the
index's return, less the expense ratio and the cost of borrowing the other 2x at the T-bill rate.
`tracking()` checks it against the real fund's total return where both exist.

Comparisons, each a `--mode`: the synthetic 3x held throughout, QQQ held throughout (also the
benchmark of every run), and his long-term rule -- buy the 3x after it has fallen 25% from its high
and hold (55:02).
"""
from __future__ import annotations

import argparse
import contextlib
import logging

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import asof, cache, index_data, index_members
from ..strategies.base import PortfolioStrategy
from . import metrics

logger = logging.getLogger("backtest")

MARKET = "us"
INDEX_TICKER = "^NDX"           # the Nasdaq 100 price index, stored from 1985
QQQ_SERIES = "NASDAQ100"        # index_data: QQQ, dividend-adjusted, from 1999 -- the benchmark
SYMBOL = "TQQQ*"                # the trades' symbol: the asterisk marks the series as synthetic

MODES = ("timing", "hold3x", "holdqqq", "dd25")

# ---- the instrument
LEVERAGE = 3
EXPENSE_RATIO = 0.0095          # TQQQ's published expense ratio, a year
FINANCING_MULT = LEVERAGE - 1   # the fund borrows (leverage - 1) x its assets, at the T-bill rate
SESSIONS_PER_YEAR = 252

# ---- the rules (1.0: textbook settings, fixed before the first run)
TREND_SMA = 200
MACD_FAST, MACD_SLOW, MACD_SIGNAL = 12, 26, 9
MACD_FAST_ALT, MACD_SLOW_ALT, MACD_SIGNAL_ALT = 6, 13, 5      # his intraday screen (11:04)
RSI_BARS = 7                    # "I changed the reading to seven" (10:55)
RSI_EXTREME = 30
KELTNER_EMA = 20
KELTNER_ATR = 10
KELTNER_MULT = 2                # the 2-ATR band; he also draws a 3-ATR one
BREADTH_SMA = 50
BREADTH_EXTREME_PCT = 20
BREADTH_MIN_MEMBERS = 30        # fewer members with prices than this: no breadth reading that day
EXTREME_WINDOW = 10             # an extreme stays live for this many sessions, waiting for the reversal
EXIT_EMA = 20
EXIT_EMA_TIGHT = 8              # the tightest he names (15:12); --exit-ema runs it
DRAWDOWN_BUY_PCT = 25           # the long-term rule: buy after this fall from the high (55:02)


# ------------------------------------------------------------------ the instrument

def index_bars() -> pd.DataFrame:
    raw = cache.load_cached(MARKET, INDEX_TICKER)
    if raw is None or raw.empty:
        raise SystemExit(f"{MARKET}: no stored prices for {INDEX_TICKER}")
    df = raw[["open", "high", "low", "close"]].astype(float).sort_index()
    df = df[df["close"] > 0]
    # an open the source left empty or at zero is read as no gap: the whole day's move is intraday
    bad = ~(df["open"] > 0)
    df.loc[bad, "open"] = df["close"].shift(1)[bad]
    return df.dropna(subset=["close"])


def synthetic(bars: pd.DataFrame, leverage: float = LEVERAGE, expense: float = EXPENSE_RATIO,
              rate: pd.Series | None = None) -> pd.DataFrame:
    """A daily-reset leveraged series from the index's bars: open and close, base 100.

    close_t = close_{t-1} x (1 + L x r_t - (expense + (L - 1) x rate_t) / 252), r_t the index's
    close-to-close return. The open applies L x the overnight gap to the previous close, so a fill
    at the open pays the leveraged gap. `rate` is the annual T-bill rate per session (decimal).
    """
    c, o = bars["close"], bars["open"]
    r = c.pct_change().fillna(0.0)
    if rate is None:
        rate = index_data.cash_rate_series(MARKET, bars.index)[0]
    fee = (expense + (leverage - 1) * rate.reindex(bars.index).ffill().fillna(0.0)) / SESSIONS_PER_YEAR
    ret = (leverage * r - fee).clip(lower=-0.99)
    ret.iloc[0] = 0.0
    close = 100.0 * (1.0 + ret).cumprod()
    gap = (o / c.shift(1) - 1.0).fillna(0.0)
    opn = (close.shift(1) * (1.0 + leverage * gap).clip(lower=0.01)).fillna(close)
    return pd.DataFrame({"open": opn, "close": close})


def tracking(leverage: int = LEVERAGE, key: str = "TQQQ", expense: float = EXPENSE_RATIO) -> dict:
    """The synthetic series against the real fund's total return, over every session both have."""
    real = index_data.load(MARKET, key)
    syn = synthetic(index_bars(), leverage, expense)["close"]
    both = pd.concat([syn, real], axis=1, keys=["syn", "real"]).dropna()
    rs, rr = both["syn"].pct_change().dropna(), both["real"].pct_change().dropna()
    years = (both.index[-1] - both.index[0]).days / 365.25

    def cagr(s):
        return ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100

    return {"series": key, "from": both.index[0].date(), "to": both.index[-1].date(), "years": round(years, 1),
            "synthetic_cagr_pct": round(cagr(both["syn"]), 2), "real_cagr_pct": round(cagr(both["real"]), 2),
            "cagr_gap_pct": round(cagr(both["syn"]) - cagr(both["real"]), 2),
            "tracking_error_pct": round(float((rs - rr).std() * np.sqrt(SESSIONS_PER_YEAR) * 100), 2),
            "daily_corr": round(float(rs.corr(rr)), 4),
            "synthetic_max_dd_pct": round(float(metrics.drawdown_series(both["syn"]).min() * 100), 1),
            "real_max_dd_pct": round(float(metrics.drawdown_series(both["real"]).min() * 100), 1)}


# ------------------------------------------------------------------ the rules

def breadth(index: pd.DatetimeIndex) -> tuple[pd.Series, int]:
    """% of TODAY's Nasdaq 100 members closing above their own 50-day average, per session.

    NaN on a session with fewer than BREADTH_MIN_MEMBERS members priced (and 50 sessions old).
    """
    members, _on = index_members.load(MARKET, "NASDAQ100")
    bars = cache.load_many_cached(MARKET, members)
    closes = pd.DataFrame({s: d["close"].astype(float) for s, d in bars.items() if d is not None and len(d)})
    closes = closes.sort_index().reindex(index.union(closes.index)).ffill(limit=5).reindex(index)
    sma = closes.rolling(BREADTH_SMA, min_periods=BREADTH_SMA).mean()
    valid = sma.notna() & closes.notna()
    above = (closes > sma) & valid
    n = valid.sum(axis=1)
    pct = (above.sum(axis=1) / n.replace(0, np.nan) * 100).where(n >= BREADTH_MIN_MEMBERS)
    return pct, int(closes.shape[1])


def signals(bars: pd.DataFrame, syn: pd.DataFrame, *, trend: bool = True, trend_on: str = "index",
            macd: str | None = None, rsi: bool = False, keltner: bool = False, use_breadth: bool = False,
            exit_ema: int = EXIT_EMA) -> tuple[pd.Series, pd.Series, pd.DataFrame]:
    """(enter, exit_reason, readings) per session, all known at that session's close.

    enter: every switched-on state condition holds, the close is above the exit EMA, and -- when any
    extreme is switched on -- one of them fired within the last EXTREME_WINDOW sessions.
    exit_reason: "" or why a holder sells at the next open (the first rule that fires, in order).
    """
    c = bars["close"]
    ema_x = ind.ema(c, exit_ema)
    tc = syn["close"] if trend_on == "3x" else c
    sma = ind.sma(tc, TREND_SMA)
    readings = pd.DataFrame({"close": c, f"ema{exit_ema}": ema_x, f"sma{TREND_SMA}": sma})

    state = c > ema_x
    if trend:
        state &= tc > sma
    if macd:
        f, s, g = ((MACD_FAST, MACD_SLOW, MACD_SIGNAL) if macd == "std"
                   else (MACD_FAST_ALT, MACD_SLOW_ALT, MACD_SIGNAL_ALT))
        line = ind.ema(c, f) - ind.ema(c, s)
        hist = line - ind.ema(line, g)
        readings["macd_hist"] = hist
        state &= hist > 0

    extremes = []
    if rsi:
        readings["rsi"] = ind.rsi(c, RSI_BARS)
        extremes.append(readings["rsi"] < RSI_EXTREME)
    if keltner:
        lower = ind.ema(c, KELTNER_EMA) - KELTNER_MULT * ind.atr(bars, KELTNER_ATR)
        readings["keltner_lower"] = lower
        extremes.append(c < lower)
    if use_breadth:
        readings["breadth_pct"] = breadth(bars.index)[0]
        extremes.append(readings["breadth_pct"] < BREADTH_EXTREME_PCT)
    if extremes:
        fired = pd.concat(extremes, axis=1).fillna(False).any(axis=1)
        readings["extreme"] = fired
        state &= fired.astype(int).rolling(EXTREME_WINDOW, min_periods=1).max().astype(bool)

    reason = pd.Series("", index=c.index)
    below_ema = (c < ema_x).fillna(False)
    reason[below_ema] = f"BELOW_EMA{exit_ema}"
    if trend:
        below_trend = (tc < sma).fillna(False)
        reason[below_trend] = f"BELOW_SMA{TREND_SMA}"   # the trend rule wins when both fire
    return state.fillna(False), reason, readings


# ------------------------------------------------------------------ the book

def simulate(inst: pd.DataFrame, want: pd.Series, reason: pd.Series, start: str, cost_bps: float,
             capital: float, cash_rate: pd.Series, symbol: str = SYMBOL):
    """Hold `inst` (open, close) from the open after a close on which `want` turns on, until the open
    after a close with a `reason`. All in or all out, fractional units; cash earns `cash_rate`."""
    start_ts = pd.Timestamp(start)
    days = inst.index[inst.index >= start_ts]
    cash, units, prev = float(capital), 0.0, None
    entry = None
    trades, curve, held, cash_log, costs = [], [], [], [], 0.0
    prior = inst.index[inst.index < start_ts]
    pending = None
    if len(prior):
        d0 = prior[-1]
        pending = "buy" if bool(want.get(d0, False)) else None
    for d in days:
        if units == 0 and prev is not None:
            r = float(cash_rate.get(d, float("nan")))
            if r == r and r > 0:
                cash *= (1.0 + r / 365.0) ** (d - prev).days
        prev = d
        o, c = float(inst.at[d, "open"]), float(inst.at[d, "close"])
        if pending == "buy" and units == 0:
            fee = cash * cost_bps / 10_000
            units, costs = (cash - fee) / o, costs + fee
            entry = (d, o, cash)
            cash = 0.0
        elif pending and pending != "buy" and units > 0:
            gross = units * o
            fee = gross * cost_bps / 10_000
            cash, costs = gross - fee, costs + fee
            trades.append(_row(symbol, entry, d, o, units, cash, fee, pending))
            units, entry = 0.0, None
        pending = None
        if units == 0 and bool(want.get(d, False)):
            pending = "buy"
        elif units > 0 and reason.get(d, ""):
            pending = reason.get(d)
        curve.append((d, cash + units * c))
        held.append((d, 1 if units > 0 else 0))
        cash_log.append((d, cash))
    eq = pd.Series(dict(curve)).sort_index()
    if units > 0:
        d = eq.index[-1]
        trades.append(_row(symbol, entry, d, float(inst.at[d, "close"]), units, units * float(inst.at[d, "close"]),
                           0.0, "OPEN"))
    return (pd.DataFrame(trades), eq, pd.Series(dict(held)).sort_index(),
            pd.Series(dict(cash_log)).sort_index(), costs)


def _row(symbol, entry, d, price, units, proceeds, fee, why) -> dict:
    ed, ep, paid = entry
    return {"symbol": symbol, "entry_date": ed, "entry_price": round(ep, 4), "exit_date": d,
            "exit_price": round(price, 4), "shares": round(units, 4), "exit_reason": why,
            "pnl": round(proceeds - paid, 2), "notional": round(paid, 2), "costs": round(fee, 2),
            "holding_days": (d - ed).days, "r_multiple": round(proceeds / paid - 1, 4)}


def run(start: str, mode: str = "timing", cost_bps: float = 5.0, **rules):
    cfg = MARKETS[MARKET]
    bars = index_bars()
    rate, rate_notes = index_data.cash_rate_series(MARKET, bars.index)
    syn = synthetic(bars, rate=rate)
    qqq = index_data.load(MARKET, QQQ_SERIES).reindex(bars.index).ffill()
    never = pd.Series("", index=bars.index)
    readings = pd.DataFrame()
    if mode == "timing":
        want, reason, readings = signals(bars, syn, **rules)
        inst = syn
    elif mode == "hold3x":
        want, reason, inst = pd.Series(True, index=bars.index), never, syn
    elif mode == "holdqqq":
        # QQQ is stored as a dividend-adjusted close only: its "open" is the previous close, so the
        # holding earns the first session's return like the 3x comparisons do
        inst = pd.DataFrame({"open": qqq.shift(1), "close": qqq}).dropna()
        want, reason = pd.Series(True, index=inst.index), never
    elif mode == "dd25":
        s = syn["close"][syn.index >= pd.Timestamp(start)]
        dd = (s / s.cummax() - 1.0) * 100
        hit = dd <= -DRAWDOWN_BUY_PCT
        want = (hit.cummax() if len(hit) else hit).reindex(bars.index).fillna(False)
        reason, inst = never, syn
    else:
        raise ValueError(f"unknown mode {mode!r}")
    tdf, eq, held, csh, costs = simulate(inst, want, reason, start, cost_bps, float(cfg.account_size), rate,
                                         symbol="QQQ" if mode == "holdqqq" else SYMBOL)
    return tdf, eq, held, csh, costs, qqq, syn, readings, rate_notes


# ------------------------------------------------------------------ docs

MT_DOC = {
    "key": "masonson_tqqq",
    "name": "Masonson TQQQ timing",
    "description": "Hold a synthetic 3x Nasdaq 100 fund while the index closes above its {TREND_SMA}-day average "
                   "and its {EXIT_EMA}-day EMA; T-bills otherwise. Les Masonson's rule set, each part a switch.",
    "status": (
        "MEASURED, OPTIMISE STAGE ONLY (2013-2021, IN-SAMPLE) -- AND IT FAILS ITS OWN TEST. The pass rule was "
        "written before any run: excess CAGR over QQQ buy-and-hold above zero, a max drawdown no deeper than "
        "QQQ's, at least twenty round trips. QQQ returned 23.01% a year with a -28.6% drawdown; the synthetic "
        "3x held throughout returned 57.32% with -69.9%. The default (200-day trend, exit below the 20-day EMA) "
        "made 21.13% with -55.5% over 139 trades, 68% invested, a median hold of 8 days: it fails on both "
        "return and drawdown, the drawdown coming from 2015-16 chop, not a crash. No switch passes. Closest: "
        "every extreme switch together (MACD 12,26,9 + RSI + Keltner + breadth) made 17.33% with -28.2% over 27 "
        "trades, 22% invested -- QQQ's drawdown at three-quarters of its return; without the trend filter "
        "25.70% (+2.69) but -50.8%. Tighter exits (8- or 10-day EMA) and the 200-day on the 3x series were "
        "worse; breadth alone traded five times. Context only, never a verdict -- 2000-2012 with today's "
        "settings: QQQ -2.40% a year (-83%), the 3x held -36.06% (-99.98%: wiped out, as he says), the default "
        "-12.40% (-90%), the combined set +3.31% (-34%, 34 trades). Not verified: nothing here has a verify "
        "run, and none should be spent until a version passes the optimise rule."
    ),
    "thesis": (
        "A 3x daily fund compounds the index's trend and is destroyed by its declines and chop: three 10% down "
        "days need a 37% gain to recover (Masonson, 51:53), and held through 2000-2009 it would have been "
        "wiped out. So hold it only while the index is in an uptrend and step aside when it breaks, keeping "
        "most of the leveraged run-up and missing most of the leveraged crash. His workshop rule adds "
        "oversold extremes (RSI, Keltner, breadth) as the moment to get back in, and the MACD histogram as a "
        "momentum check."
    ),
    "how_it_works": (
        "Every session, on the Nasdaq 100 index's close (^NDX): if the close is above its {EXIT_EMA}-day EMA and "
        "above its {TREND_SMA}-day average, hold the 3x fund from the next open. Sell at the next open after a "
        "close below either. Otherwise the money earns the 13-week T-bill rate.",
        "Four switches add his other indicators, off by default: `--macd std` (histogram of MACD "
        "{MACD_FAST},{MACD_SLOW},{MACD_SIGNAL} above zero) or `--macd fast` ({MACD_FAST_ALT},{MACD_SLOW_ALT},"
        "{MACD_SIGNAL_ALT}, his intraday setting); `--rsi` (RSI({RSI_BARS}) closed below {RSI_EXTREME}); "
        "`--keltner` (a close below the {KELTNER_EMA}-day EMA less {KELTNER_MULT} x ATR({KELTNER_ATR})); "
        "`--breadth` (under {BREADTH_EXTREME_PCT}% of Nasdaq 100 members above their {BREADTH_SMA}-day). The "
        "three extremes are alternatives: with any of them on, an entry also needs one of them to have fired "
        "in the last {EXTREME_WINDOW} sessions. `--no-trend` drops the {TREND_SMA}-day rule, `--trend-on 3x` "
        "reads it on the 3x series instead of the index, `--exit-ema N` moves the exit average.",
        "The fund is SYNTHETIC: {LEVERAGE}x the index's daily return, less TQQQ's expense ratio ({EXPENSE_RATIO} "
        "a year) and the T-bill rate on the {FINANCING_MULT}x of assets it borrows. The real TQQQ lists only in 2010.",
        "Comparisons, as `--mode`: `hold3x` holds the synthetic fund throughout; `holdqqq` holds QQQ (total "
        "return) throughout; `dd25` is his long-term rule -- buy the 3x once it has fallen {DRAWDOWN_BUY_PCT}% "
        "from its high since the start, then hold. Every run's benchmark is QQQ total return.",
    ),
    "caveats": (
        "**The fund is synthetic.** Built from the ^NDX PRICE index, so it carries no dividends (QQQ's are "
        "about 0.6% a year, about 1.8% at 3x), and the financing is the T-bill rate with no swap spread. The "
        "real TQQQ's total return is stored to check it (`tracking()`): over every session both have, "
        "2010-02-11 to 2026-11-09, the synthetic grows 37.9% a year against the real fund's 40.0% (2.1 "
        "points short, mostly the missing dividends), with a 3.5% annual tracking error, a 0.9986 daily "
        "correlation and the same -82% worst drawdown. At 2x against QLD (2006 on): 1.25 points short, "
        "4.2% tracking error. So the synthetic understates the fund slightly, never flatters it.",
        "**He names the indicators, not the settings.** Every setting here is a textbook default chosen "
        "before the first run, not his; he says the workshop strategy is still being built and warns that "
        "more variables mean more risk it fails live (73:37).",
        "**Breadth uses today's Nasdaq 100 members** (marketdata/index_members.py), not each date's. A 2002 "
        "reading counts the companies that went on to be in the index in 2026 and leaves out the ones that "
        "were dropped -- survivors, which held up better, so breadth reads stronger than it was. Only "
        "members with stored prices count; before about 2000 fewer than {BREADTH_MIN_MEMBERS} have them.",
        "**Bullish percent is left out of 1.0.** He also names the point-and-figure bullish percent index "
        "(72:05); it needs a point-and-figure signal per member and is a later version.",
        "**One instrument, one market.** Two dozen round trips over nine years is a small sample, and the "
        "rule's behaviour is the index's: a flat, choppy decade is what hurts a 3x fund and what the trend "
        "rule whipsaws in.",
        "**Fills at the open assume the leveraged gap.** A 3x fund opens at about 3x the index's overnight "
        "gap; the synthetic open applies exactly that, with no spread. Costs: {cost_bps}bps a side.",
        "**He trades it intraday, not like this.** His own trading is one-minute Nasdaq futures, flat by the "
        "close (10:28). This is the daily swing version he sketches for the workshop (60:27, 70:20).",
    ),
    "entry_rules": (
        "Signal session. Read on the close of ^NDX; nothing before the start date is traded, but the "
        "averages use the history before it.",
        "Trend ({TREND_SMA}-day, on unless `--no-trend`). The index's close is above its {TREND_SMA}-day "
        "simple average (`--trend-on 3x`: the synthetic fund's close above its own).",
        "Reversal. The index's close is above its {EXIT_EMA}-day EMA (`--exit-ema` moves it).",
        "MACD (`--macd`). The histogram -- MACD line less its signal line -- is above zero.",
        "Extremes (`--rsi`, `--keltner`, `--breadth`, any of them). At least one of the switched-on extremes "
        "fired on one of the last {EXTREME_WINDOW} closes: RSI({RSI_BARS}) below {RSI_EXTREME}; a close below "
        "the lower Keltner band; under {BREADTH_EXTREME_PCT}% of members above their {BREADTH_SMA}-day.",
        "Fill. The whole book buys the synthetic fund at the next session's open, less {cost_bps}bps.",
    ),
    "exit_rules": (
        "Sold in full at the next open, less {cost_bps}bps, after a close below the {EXIT_EMA}-day EMA "
        "(BELOW_EMA) or, with the trend rule on, below the {TREND_SMA}-day average (BELOW_SMA).",
        "No stop, no target: the averages are the exit. MACD and the extremes only gate entries.",
        "Out of the market the money earns the 13-week T-bill rate, per calendar day. Whatever is held at "
        "the end of a run is valued at the final close, with no exit cost (OPEN).",
    ),
    # the runs the page offers beside the strategy as configured: the comparisons and the switches
    "commands": {
        "Compare: synthetic 3x held throughout": "python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--mode hold3x'",
        "Compare: QQQ held throughout": "python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--mode holdqqq'",
        "Compare: buy the 3x after a 25% fall, hold": "python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--mode dd25'",
        "Combined rule set": "python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage optimise --bt='--macd std --rsi --keltner --breadth'",
        "Context: the 2000-2012 crash (not a verdict)": "python -m jobs enqueue backtest --market us --strategies masonson_tqqq --stage full --start 2000-01-01 --bt='--end 2012-12-31'",
    },
}


class MasonsonTqqqStrategy(PortfolioStrategy):
    """Trend-timed 3x Nasdaq 100, with Masonson's indicators as switches."""

    key = MT_DOC["key"]
    doc = MT_DOC
    family = "masonson_tqqq"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-11",
         "First version, from Les Masonson's Tradeline interview. Settings FIXED BEFORE THE FIRST RUN, not "
         "tuned on any result: trend filter close > 200-day SMA of ^NDX (on by default); MACD histogram > 0 "
         "at 12,26,9, his 6,13,5 as a variant (off); RSI(7) < 30 (off); close below EMA(20) - 2 x ATR(10) "
         "(off); under 20% of today's Nasdaq 100 members above their 50-day (off); an extreme stays live for "
         "10 sessions; exit on a close below the 20-day EMA (he names 8, 10 and 20; 20 so the first run is "
         "not his tightest); signals on the close, fills at the next open, 5bps a side. Instrument: 3x ^NDX "
         "daily, less 0.95%/yr and 2x the 13-week T-bill rate, /252. Pass criterion written before reading "
         "a result: excess CAGR over QQQ buy-and-hold > 0, max drawdown no deeper than QQQ's, and at least "
         "20 round trips. Bullish percent is left for a later version. Tracking check before any run: "
         "synthetic 37.9%/yr vs real TQQQ total return 40.0%/yr (2010-02 to 2026-11), tracking error 3.5%, "
         "correlation 0.9986, max drawdown -82% both."),
    )
    name = MT_DOC["name"]
    description = MT_DOC["description"]
    status = MT_DOC["status"]
    thesis = MT_DOC["thesis"]
    how_it_works = tuple(MT_DOC["how_it_works"])
    caveats = tuple(MT_DOC["caveats"])
    entry_rules = tuple(MT_DOC["entry_rules"])
    exit_rules = tuple(MT_DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    horizon = "swing"
    runner = "masonson_tqqq"

    mode = "timing"
    cost_bps = 5.0

    param_docs = (
        ("Mode", "mode", "timing: the rule. hold3x / holdqqq / dd25: the comparisons."),
        ("Leverage", "LEVERAGE", "Daily multiple of the index's return."),
        ("Expense ratio", "EXPENSE_RATIO", "A year, charged daily."),
        ("Trend average", "TREND_SMA", "Sessions in the trend filter's simple average."),
        ("Exit EMA", "EXIT_EMA", "Sessions in the exit average; --exit-ema {EXIT_EMA_TIGHT} is his tightest."),
        ("RSI", "RSI_BARS", "RSI sessions; an extreme below RSI_EXTREME."),
        ("Keltner", "KELTNER_MULT", "ATR multiples below the {KELTNER_EMA}-day EMA."),
        ("Breadth extreme", "BREADTH_EXTREME_PCT", "% of members above their {BREADTH_SMA}-day, at or under."),
        ("Extreme window", "EXTREME_WINDOW", "Sessions an extreme stays live, waiting for the reversal."),
        ("Buy-the-drop", "DRAWDOWN_BUY_PCT", "dd25 mode: the fall from the high that buys."),
        ("Cost per side", "cost_bps", "Basis points per side."),
    )


# ------------------------------------------------------------------ runner

def _context_boundary(end: str | None):
    """An earlier end than the stage's, for a context run (the 2000-2012 stress test). Never later
    than the stage's own end, so an optimise run cannot use it to read into the verify years."""
    if not end:
        return contextlib.nullcontext()
    from . import windows
    outer, label = asof.end(), asof.label() or ""
    eff = pd.Timestamp(end) if outer is None else min(pd.Timestamp(end), outer)
    stage = label.split("-")[1] if label.startswith("stage-") else "full"
    return asof.boundary(eff, windows.tag(stage, eff.date().isoformat()))


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Masonson TQQQ timing")
    ap.add_argument("--strategy", default="masonson_tqqq")
    ap.add_argument("--market", default=MARKET, choices=[MARKET])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None, help="an earlier end than the stage's, for a context run")
    ap.add_argument("--mode", default=MasonsonTqqqStrategy.mode, choices=list(MODES))
    ap.add_argument("--no-trend", action="store_true", help="drop the 200-day trend rule")
    ap.add_argument("--trend-on", default="index", choices=["index", "3x"])
    ap.add_argument("--macd", default=None, choices=["std", "fast"])
    ap.add_argument("--rsi", action="store_true")
    ap.add_argument("--keltner", action="store_true")
    ap.add_argument("--breadth", action="store_true")
    ap.add_argument("--exit-ema", type=int, default=EXIT_EMA)
    ap.add_argument("--cost-bps", type=float, default=MasonsonTqqqStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    cfg = MARKETS[MARKET]
    rules = dict(trend=not a.no_trend, trend_on=a.trend_on, macd=a.macd, rsi=a.rsi, keltner=a.keltner,
                 use_breadth=a.breadth, exit_ema=a.exit_ema)
    with _context_boundary(a.end):
        tdf, eq, held, csh, costs, qqq, _syn, _readings, rate_notes = run(a.start, a.mode, a.cost_bps, **rules)
        bc = qqq.reindex(eq.index).ffill()
        if a.mode == "timing":
            on = ([] if a.no_trend else [f"trend {TREND_SMA}d" + (" on 3x" if a.trend_on == "3x" else "")]
                  + ([f"MACD {a.macd}"] if a.macd else []) + (["RSI"] if a.rsi else [])
                  + (["Keltner"] if a.keltner else []) + (["breadth"] if a.breadth else []))
            what = f"Timing rule: {', '.join(on) or 'no filter'}, exit below EMA{a.exit_ema}."
        else:
            what = {"hold3x": "Comparison: the synthetic 3x fund held throughout.",
                    "holdqqq": "Comparison: QQQ (total return) held throughout.",
                    "dd25": f"Comparison: buy the synthetic 3x after a {DRAWDOWN_BUY_PCT}% fall from its high, hold."}[a.mode]
        notes = [what,
                 f"Instrument: synthetic {LEVERAGE}x ^NDX (daily reset, {EXPENSE_RATIO * 100:.2f}%/yr expense, "
                 f"{FINANCING_MULT}x the T-bill rate financing; no dividends). Signals on the close, fills at the next open.",
                 f"Costs: {a.cost_bps:g}bps per side. Benchmark: QQQ total return.", *rate_notes]
        if a.end:
            notes.insert(0, f"CONTEXT RUN to {a.end}: not an optimise or verify window, never a verdict.")
        perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=1,
                               costs_paid=costs, bench_close=bc, cash=csh, notes=notes)
        for k, v in metrics.benchmark_stats(bc).items():
            setattr(perf, k, v)
        perf.benchmark_name = "QQQ total return"

        tag = a.mode if a.mode != "timing" else "-".join(
            (["notrend"] if a.no_trend else ["sma200" + ("x3" if a.trend_on == "3x" else "")])
            + ([f"macd{a.macd}"] if a.macd else []) + (["rsi"] if a.rsi else [])
            + (["kelt"] if a.keltner else []) + (["breadth"] if a.breadth else []) + [f"ema{a.exit_ema}"])
        name = (f"{a.start}" + (f"_to-{a.end}" if a.end else "") + f"_{tag}_{a.cost_bps:g}bps_"
                f"{MasonsonTqqqStrategy.spec_id()}")
        out = run_dir(MARKET, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 1))
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"Masonson TQQQ timing ({a.mode}), {a.start} onward" + (f" to {a.end} (context)" if a.end else ""),
            perf, eq, held, tdf, cfg.currency_symbol, 1, bc,
            "python3 -m swing_screener.backtesting.masonson_tqqq " + " ".join(argv or []))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
