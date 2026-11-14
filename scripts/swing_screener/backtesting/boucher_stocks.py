"""Boucher stock timing — hold the S&P 500 only while its trend and interest rates agree; T-bills otherwise.

From Mark Boucher, *The Hedge Fund Edge* (Wiley, 1999). Page numbers below are the PDF's pages of the
book. The rules are paraphrased, never quoted, and every threshold is his published one, fixed before
the first run (see the 1.0 changelog entry).

    base rule  (pp. 56-57, his Spreadsheet 2.25) -- weekly closes: the S&P above its 40-week average AND
               either the 3-month T-bill yield or the long Treasury yield below its own 40-week average
    switches   each a monthly gate on the base rule (or, with --no-base, a model on its own, as he tested
               them): the liquidity models of pp. 38-43 (T-bill and long-yield 12-month change, a
               corporate bond index's 12-month change, the yield-curve ratio, and the first three
               together), the economic models of pp. 45-49 (capacity utilization, industrial production,
               unemployment against 29 months earlier, CPI fast vs slow, CPI with GDP) and consumer
               sentiment (p. 76)
    brake      his late-cycle sequence (pp. 51-52), the combination he describes in words: step aside
               when the economy is overheated AND inflation is turning up AND the rate models agree
    Nasdaq     the OTC 7.9% momentum reversal (pp. 73-74), a separate mode: long/short as he ran it, or
               long/T-bills

The S&P is traded as a total-return series: SPY (dividend-adjusted) where it exists, from 1993-01-29,
and the Vanguard 500 fund (VFINX, total return) before that. Signals are read on the close of the
S&P 500 PRICE index (^GSPC), as he did, and filled at the close FILL_DELAY_SESSIONS later.

PUBLICATION LAG. An economic number is not known on the date FRED stamps it (the first day of the
period it describes). Each series here is usable only from that date plus a fixed, conservative
release lag (`*_LAG_DAYS`). Market series (yields, prices) are known at the close. The stored values
are FRED's current vintage, not first prints -- see the caveats.
"""
from __future__ import annotations

import argparse
import logging

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, index_data
from ..strategies.base import PortfolioStrategy
from . import metrics

logger = logging.getLogger("backtest")

MARKET = "us"
SP_TICKER = "^GSPC"          # the signal: the S&P 500 price index, stored from 1927
OTC_TICKER = "^IXIC"         # the Nasdaq Composite price index, stored from 1971
SP_TR_EARLY = "SP500_TR"     # VFINX total return, from 1980 -- the instrument before SPY
SP_TR = "SPY"                # SPY total return, from 1993-01-29
TBILL = "CASH_YIELD"         # ^IRX, the 13-week T-bill yield in %, from 1960 -- the signal and the cash leg
LONG_YIELD = "US_UST_30Y"    # from 1977
LONG_YIELD_EARLY = "US_UST_10Y"   # from 1962: stands in before the 30-year exists

MODES = ("timing", "otc", "otc_long", "hold", "hold_otc")

# ---- the base rule (pp. 56-57)
TREND_WEEKS = 40
# The zero bound (1.1). Below this 13-week T-bill yield the T-bill condition gives NO signal and the long
# yield decides the rates leg alone. FIXED BEFORE ANY RUN, from the rule's intent, and never to be tuned:
# the T-bill leg reads the direction of Fed policy, and with the Fed at its floor (funds target 0-0.25%)
# a bill yield cannot fall because policy eases -- its 1-3bp moves are bill supply and money-market
# technicals, not a liquidity cycle. 0.50% is the top of the first 25bp policy step above that floor, so
# a bill must have cleared the zero-rate band and one hike before its trend counts as policy. Every
# weekly ^IRX reading in the stored 1960-1997 history (his fitting period) is above 2%, so the floor
# never touches the regime the rule was built on.
TBILL_FLOOR_PCT = 0.50

# ---- the switches, his published thresholds (fixed before the first run)
ROC_MONTHS = 12
TBILL_ROC_MAX_PCT = 6.0          # 2. T-bill yield 12-month % change below this (pp. 38-39)
BOND_ROC_MIN_PCT = -1.5          # 3. corporate bond index 12-month change above this (pp. 38-40)
BOND_PROXY_YEARS = 20            #    the proxy index: a constant-maturity Baa bond of this many years
LONG_ROC_MAX_PCT = 9.0           # 4. long Treasury yield 12-month % change at or below this (pp. 40-41)
CURVE_RATIO_MIN = 1.15           # 5. long yield / T-bill yield above this (p. 42)
CAPACITY_MAX_PCT = 81.5          # 7. capacity utilization at or below this (p. 45)
INDPRO_ROC_MAX_PCT = 5.6         # 8. industrial production 12-month change at or below this (p. 46)
UNEMP_LOOKBACK_MONTHS = 29       # 9. unemployment above its level this many months earlier (p. 47)
CPI_FAST_MONTHS = 11             # 10. CPI change over this many months ...
CPI_SLOW_MONTHS = 13             #     ... below the change of its 13-month average on the 13 before (pp. 48-49)
CPI_MAX_PCT = 3.2                # 11. CPI year-on-year ... (p. 48)
GDP_MAX_PCT = 4.0                #     ... and GDP quarterly growth, annualised
SENTIMENT_MAX = 99.5             # 12. consumer sentiment at or below this (p. 76)
OVERHEAT_CAPACITY_PCT = 88.5     # the brake: capacity utilization above this (pp. 45, 51) ...
OVERHEAT_INDPRO_PCT = 7.0        #     ... or industrial production growth above this (pp. 46, 51)
OTC_REVERSAL_PCT = 7.9           # 14. the Nasdaq reversal (p. 73)

# ---- publication lags, calendar days after the date FRED stamps the observation
CPI_LAG_DAYS = 55                # month M is stamped the 1st of M; released about the 13th-25th of M+1
INDPRO_LAG_DAYS = 50             # Fed G.17, about the 15th-17th of M+1
CAPACITY_LAG_DAYS = 50           # the same G.17 release
UNEMP_LAG_DAYS = 40              # the jobs report, the first Friday of M+1
SENTIMENT_LAG_DAYS = 35          # the final reading, the last Friday of M
BAA_LAG_DAYS = 32                # a monthly average, complete when M ends
GDP_LAG_DAYS = 125               # quarter Q stamped its first day; the advance estimate ~4 weeks after it ends

# ---- the book
FILL_DELAY_SESSIONS = 1          # a signal on a close fills at the close this many sessions later
OTC_DIV_YIELD = 0.010            # the Nasdaq Composite is a price index: ~1%/yr dividends, credited to longs
                                 # and to its buy-and-hold, charged to shorts

SWITCHES = ("tbill_roc", "bond_roc", "long_roc", "curve", "monetary", "capacity", "indpro",
            "unemployment", "cpi_trend", "cpi_gdp", "sentiment", "brake")


# ------------------------------------------------------------------ data

def closes(ticker: str) -> pd.Series:
    """A stored price series' closes (honours the stage boundary through cache.load_cached)."""
    raw = cache.load_cached(MARKET, ticker)
    if raw is None or raw.empty:
        raise SystemExit(f"{MARKET}: no stored prices for {ticker}")
    c = raw["close"].astype(float).sort_index()
    return c[c > 0].dropna()


def sp_total_return() -> pd.Series:
    """SPY's total return, chained onto VFINX's before SPY lists."""
    early, spy = index_data.load(MARKET, SP_TR_EARLY), index_data.load(MARKET, SP_TR)
    first = spy.index[0]
    if early.index[0] >= first:
        return spy
    head = early[early.index <= first]
    scale = head.iloc[-1] / spy.iloc[0]
    return pd.concat([head.iloc[:-1], spy * scale]).sort_index()


def long_yield() -> pd.Series:
    """The 30-year Treasury yield, with the 10-year standing in before the 30-year's first date."""
    lng, early = index_data.load(MARKET, LONG_YIELD), index_data.load(MARKET, LONG_YIELD_EARLY)
    return pd.concat([early[early.index < lng.index[0]], lng]).sort_index()


def lagged(s: pd.Series, lag_days: int) -> pd.Series:
    """A series of observations re-dated to when it could first be read: FRED's date + `lag_days`."""
    s = s.dropna().copy()
    s.index = s.index + pd.Timedelta(days=lag_days)
    return s


def as_of(by_date: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """The latest value dated on or before each of `dates` (NaN before the first)."""
    s = by_date.dropna()
    s = s[~s.index.duplicated(keep="last")].sort_index()
    return s.reindex(s.index.union(dates)).ffill().reindex(dates)


def bond_price(coupon, yld, years: float):
    """Price per 100 of a semiannual bond paying `coupon` with `years` to run, at yield `yld` (both in %)."""
    c, y, n = np.asarray(coupon, float) / 100, np.asarray(yld, float) / 100, 2 * years
    h = y / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        annuity = np.where(np.abs(h) > 1e-9, (1 - (1 + h) ** -n) / h, n)
    return 100 * (c / 2 * annuity + (1 + h) ** -n)


def bond_index(yld: pd.Series, years: float = BOND_PROXY_YEARS, carry: bool = False) -> pd.Series:
    """An index of a constant-maturity bond, base 100: each period, last period's par bond (coupon =
    last period's yield) is re-priced at this period's yield. `carry` adds the coupon accrued over the
    calendar days held (a total return); without it the index is price only, like the DJ 20."""
    y = yld.dropna()
    ret = pd.Series(bond_price(y.shift(1), y, years) / 100.0, index=y.index)
    if carry:
        days = y.index.to_series().diff().dt.days
        ret = ret + y.shift(1) / 100.0 * days / 365.0
    return 100.0 * ret.fillna(1.0).cumprod()


def week_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """The last session of each calendar week (Friday, or the session before a Friday holiday)."""
    s = index.to_series()
    return pd.DatetimeIndex(s.groupby(s.index.to_period("W-FRI")).max().values)


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = index.to_series()
    return pd.DatetimeIndex(s.groupby(s.index.to_period("M")).max().values)


def hysteresis(enter: pd.Series, leave: pd.Series) -> pd.Series:
    """True from a date `enter` holds until a date `leave` holds; unchanged when neither does."""
    en, lv = enter.fillna(False).astype(bool), leave.fillna(False).astype(bool)
    state = pd.Series(np.nan, index=enter.index)
    state[en] = 1.0
    state[lv & ~en] = 0.0
    return state.ffill().fillna(0.0).astype(bool)


def to_sessions(state: pd.Series, sessions: pd.DatetimeIndex) -> pd.Series:
    """A state read on some sessions (week-ends, month-ends), carried to every session until the next."""
    return state.astype(float).reindex(sessions).ffill().fillna(0.0).astype(bool)


# ------------------------------------------------------------------ the rules

def base_rule(sp: pd.Series, tbill: pd.Series, lng: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """(state, readings) on each week's last session (pp. 56-57)."""
    wk = week_ends(sp.index)
    c, tb, lb = sp.reindex(wk), as_of(tbill, wk), as_of(lng, wk)
    r = pd.DataFrame({"sp": c, "sp_ma": c.rolling(TREND_WEEKS).mean(),
                      "tbill": tb, "tbill_ma": tb.rolling(TREND_WEEKS).mean(),
                      "long": lb, "long_ma": lb.rolling(TREND_WEEKS).mean()})
    # at the zero bound the T-bill condition is silent (TBILL_FLOOR_PCT): it cannot vote either way
    r["tbill_live"] = r["tbill"] >= TBILL_FLOOR_PCT
    tbill_easing = r["tbill_live"] & (r["tbill"] < r["tbill_ma"])
    state = (r["sp"] > r["sp_ma"]) & (tbill_easing | (r["long"] < r["long_ma"]))
    return state, r


def monthly_readings(sessions: pd.DatetimeIndex, tbill: pd.Series, lng: pd.Series) -> pd.DataFrame:
    """Every switch's input, as it could be read at each month-end close."""
    me = month_ends(sessions)
    r = pd.DataFrame(index=me)
    tb, lb = as_of(tbill, me), as_of(lng, me)
    r["tbill"], r["long"] = tb, lb
    with np.errstate(divide="ignore", invalid="ignore"):
        r["tbill_roc"] = (tb / tb.shift(ROC_MONTHS) - 1) * 100
        r["long_roc"] = (lb / lb.shift(ROC_MONTHS) - 1) * 100
        r["curve"] = lb / tb
    r = r.replace([np.inf, -np.inf], np.nan)

    # 3. the Dow Jones 20 bond index is discontinued: a Baa bond price index stands in
    bi = bond_index(index_data.load(MARKET, "US_BAA_YIELD"))
    r["bond_roc"] = as_of(lagged((bi / bi.shift(ROC_MONTHS) - 1) * 100, BAA_LAG_DAYS), me)

    cpi = index_data.load(MARKET, "US_CPI")
    avg = cpi.rolling(CPI_SLOW_MONTHS).mean()
    r["cpi_fast"] = as_of(lagged((cpi / cpi.shift(CPI_FAST_MONTHS) - 1) * 100, CPI_LAG_DAYS), me)
    r["cpi_slow"] = as_of(lagged((avg / avg.shift(CPI_SLOW_MONTHS) - 1) * 100, CPI_LAG_DAYS), me)
    r["cpi_yoy"] = as_of(lagged((cpi / cpi.shift(ROC_MONTHS) - 1) * 100, CPI_LAG_DAYS), me)

    gdp = index_data.load(MARKET, "US_GDP")
    r["gdp_growth"] = as_of(lagged(((gdp / gdp.shift(1)) ** 4 - 1) * 100, GDP_LAG_DAYS), me)

    ip = index_data.load(MARKET, "US_INDPRO")
    r["indpro_roc"] = as_of(lagged((ip / ip.shift(ROC_MONTHS) - 1) * 100, INDPRO_LAG_DAYS), me)
    r["capacity"] = as_of(lagged(index_data.load(MARKET, "US_CAPACITY_UTIL"), CAPACITY_LAG_DAYS), me)
    un = index_data.load(MARKET, "US_UNEMPLOYMENT")
    r["unemp_change"] = as_of(lagged(un - un.shift(UNEMP_LOOKBACK_MONTHS), UNEMP_LAG_DAYS), me)
    r["sentiment"] = as_of(lagged(index_data.load(MARKET, "US_CONSUMER_SENTIMENT"), SENTIMENT_LAG_DAYS), me)
    return r


def switch_states(r: pd.DataFrame) -> pd.DataFrame:
    """Each switch's bullish state at each month-end; a missing input reads as not bullish."""
    s = pd.DataFrame(index=r.index)
    s["tbill_roc"] = r["tbill_roc"] < TBILL_ROC_MAX_PCT
    s["bond_roc"] = r["bond_roc"] > BOND_ROC_MIN_PCT
    s["long_roc"] = r["long_roc"] <= LONG_ROC_MAX_PCT
    s["curve"] = r["curve"] > CURVE_RATIO_MIN
    s["monetary"] = s["tbill_roc"] & s["bond_roc"] & s["long_roc"]
    s["capacity"] = r["capacity"] <= CAPACITY_MAX_PCT
    s["indpro"] = r["indpro_roc"] <= INDPRO_ROC_MAX_PCT
    # in when unemployment is above its level 29 months back, out when below; unchanged when equal
    s["unemployment"] = hysteresis(r["unemp_change"] > 0, r["unemp_change"] < 0)
    s["cpi_trend"] = r["cpi_fast"] < r["cpi_slow"]
    # in when both are under their thresholds, out only when both are over (his Spreadsheet 2.16)
    s["cpi_gdp"] = hysteresis((r["cpi_yoy"] < CPI_MAX_PCT) & (r["gdp_growth"] < GDP_MAX_PCT),
                              (r["cpi_yoy"] > CPI_MAX_PCT) & (r["gdp_growth"] > GDP_MAX_PCT))
    s["sentiment"] = r["sentiment"] <= SENTIMENT_MAX
    # the brake allows a holding unless the whole late-cycle sequence is in place (pp. 51-52)
    overheated = (r["capacity"] > OVERHEAT_CAPACITY_PCT) | (r["indpro_roc"] > OVERHEAT_INDPRO_PCT)
    cpi_rising = r["cpi_fast"] >= r["cpi_slow"]
    s["brake"] = ~(overheated & cpi_rising & ~s["monetary"])
    return s.fillna(False).astype(bool)


def timing_target(sp: pd.Series, tbill: pd.Series, lng: pd.Series, *, base: bool = True,
                  switches: tuple[str, ...] = ()) -> tuple[pd.Series, pd.DataFrame]:
    """(want, readings): want is the position (1 or 0) decided at each session's close."""
    if not base and not switches:
        raise SystemExit("--no-base needs at least one switch")
    idx = sp.index
    want = pd.Series(True, index=idx)
    readings = pd.DataFrame(index=idx)
    if base:
        st, r = base_rule(sp, tbill, lng)
        want &= to_sessions(st, idx)
        readings = readings.join(r.add_prefix("w_"))
    if switches:
        mr = monthly_readings(idx, tbill, lng)
        ss = switch_states(mr)
        for k in switches:
            want &= to_sessions(ss[k], idx)
        readings = readings.join(mr.add_prefix("m_")).join(ss[list(switches)].add_prefix("on_"))
    return want.astype(int), readings


def otc_target(c: pd.Series, short: bool = True) -> pd.Series:
    """The 7.9% reversal (pp. 73-74), on daily closes: long from a close 7.9% above the lowest close
    since the short began; short (or out) from a close 7.9% below the highest close since the long
    began. Starts long on the first close."""
    k = OTC_REVERSAL_PCT / 100
    pos, ext = 1, float(c.iloc[0])
    out = np.empty(len(c))
    for i, px in enumerate(c.to_numpy(float)):
        if pos == 1:
            ext = max(ext, px)
            if px <= ext * (1 - k):
                pos, ext = -1, px
        else:
            ext = min(ext, px)
            if px >= ext * (1 + k):
                pos, ext = 1, px
        out[i] = pos
    s = pd.Series(out, index=c.index).astype(int)
    return s if short else s.clip(lower=0)


# ------------------------------------------------------------------ the book

def simulate(price: pd.Series, want: pd.Series, cash_rate: pd.Series, start: str, cost_bps: float,
             capital: float, symbol: str, div_yield: float = 0.0, delay: int = FILL_DELAY_SESSIONS,
             quote: pd.Series | None = None):
    """Whole-book long (1), short (-1) or T-bills (0), switched at the close `delay` sessions after the
    close that decided it. A long earns the instrument's return (+ `div_yield` a year, for a price
    index); a short earns minus that plus the T-bill rate on its proceeds, rebalanced daily like an
    inverse fund; cash earns the T-bill rate per calendar day. `cost_bps` per side, on the book.

    `price` is what the book earns (a total-return series, scaled to whatever level it was chained at);
    `quote` is the instrument's own traded close, written to the trade log as `entry_price` /
    `exit_price` (blank on a date it has none, e.g. SPY before 1993). Without a `quote` the log's prices
    are `price` itself (right when `price` is the instrument, like the Nasdaq index). Either way the
    total-return levels are logged as `entry_tr_level` / `exit_tr_level`, and `costs` holds the entry
    fee plus the exit fee (both are inside `pnl`).

    -> (trades, equity, held, cash, costs, position)."""
    px = price.dropna()
    pos = want.reindex(px.index).ffill().fillna(0).shift(delay).fillna(0).astype(int)
    rate = cash_rate.reindex(px.index).ffill().fillna(0.0)
    days = px.index.to_series().diff().dt.days.fillna(0)
    r = px.pct_change().fillna(0.0) + div_yield * days / 365.0
    carry = (1 + rate.shift(1).fillna(0.0) / 365.0) ** days - 1
    held = pos.shift(1).fillna(0)                        # the position carried into each session
    ret = pd.Series(np.where(held > 0, r, np.where(held < 0, -r + carry, carry)), index=px.index)
    keep = px.index >= pd.Timestamp(start)
    ret, pos, p = ret[keep], pos[keep], px[keep]
    if ret.empty:
        raise SystemExit(f"no prices on or after {start}")
    ret.iloc[0] = 0.0                                    # the book opens in cash at the first close
    prev = pos.shift(1).fillna(0)
    prev.iloc[0] = 0
    q = p if quote is None else quote.reindex(p.index)
    eq, cash_log, trades, costs = [], [], [], 0.0
    e, open_ = float(capital), None
    for d in pos.index:
        e *= 1.0 + float(ret.at[d])
        if pos.at[d] != prev.at[d]:
            if open_ is not None:
                fee = e * cost_bps / 10_000
                e, costs = e - fee, costs + fee
                trades.append(_row(symbol, open_, d, float(p.at[d]), float(q.at[d]), e, fee, "SIGNAL"))
                open_ = None
            if pos.at[d] != 0:
                fee = e * cost_bps / 10_000
                open_ = (d, float(p.at[d]), float(q.at[d]), e, int(pos.at[d]), fee)
                e, costs = e - fee, costs + fee
        eq.append((d, e))
        cash_log.append((d, e if pos.at[d] == 0 else 0.0))
    equity = pd.Series(dict(eq)).sort_index()
    if open_ is not None:
        d = equity.index[-1]
        trades.append(_row(symbol, open_, d, float(p.at[d]), float(q.at[d]), e, 0.0, "OPEN"))
    return (pd.DataFrame(trades), equity, (pos != 0).astype(int), pd.Series(dict(cash_log)).sort_index(),
            costs, pos)


def _px(x: float):
    return None if pd.isna(x) else round(x, 4)


def _row(symbol, entry, d, level, price, value, fee, why) -> dict:
    """One round trip. `paid` is the book before the entry fee, so `pnl` is net of both fees, and
    `costs` is both fees. `r_multiple` is the trade's fractional return: there is no stop, so no true R."""
    ed, el, ep, paid, side, entry_fee = entry
    return {"symbol": symbol, "side": "long" if side > 0 else "short", "entry_date": ed,
            "entry_price": _px(ep), "exit_date": d, "exit_price": _px(price),
            "entry_tr_level": round(el, 4), "exit_tr_level": round(level, 4),
            "exit_reason": why, "pnl": round(value - paid, 2), "notional": round(paid, 2),
            "costs": round(entry_fee + fee, 2), "holding_days": (d - ed).days,
            "r_multiple": round(value / paid - 1, 4)}


def run(start: str, mode: str = "timing", cost_bps: float = 5.0, base: bool = True,
        switches: tuple[str, ...] = ()):
    cfg = MARKETS[MARKET]
    tbill = index_data.load(MARKET, TBILL)
    rate = (tbill / 100.0).clip(lower=0.0)
    readings = pd.DataFrame()
    if mode in ("otc", "otc_long", "hold_otc"):
        c = closes(OTC_TICKER)
        bench = c * (1 + OTC_DIV_YIELD) ** ((c.index - c.index[0]).days / 365.0)
        want = pd.Series(1, index=c.index) if mode == "hold_otc" else otc_target(c, short=(mode == "otc"))
        price, symbol, div, quote = c, OTC_TICKER, OTC_DIV_YIELD, None
        bench_name = f"Nasdaq Composite price + {OTC_DIV_YIELD * 100:g}%/yr dividends"
    else:
        price = sp_total_return()
        bench, symbol, div, quote = price, "SPY", 0.0, closes(SP_TR)
        if mode == "hold":
            want = pd.Series(1, index=price.index)
        else:
            want, readings = timing_target(closes(SP_TICKER), tbill, long_yield(), base=base, switches=switches)
        bench_name = "S&P 500 total return (SPY; VFINX before 1993)"
    tdf, eq, held, csh, costs, pos = simulate(price, want, rate, start, cost_bps, float(cfg.account_size),
                                              symbol, div_yield=div, quote=quote)
    return tdf, eq, held, csh, costs, bench, bench_name, readings, pos


# ------------------------------------------------------------------ docs

BS_DOC = {
    "key": "boucher_stocks",
    "name": "Boucher stock timing",
    "description": "Hold the S&P 500 while it is above its {TREND_WEEKS}-week average and the T-bill or long "
                   "Treasury yield is below its own; T-bills otherwise. Mark Boucher's liquidity, economic and "
                   "sentiment models as monthly switches; his Nasdaq {OTC_REVERSAL_PCT}% reversal as a mode.",
    "status": (
        "1.1 (ZERO-BOUND RATES LEG) -- PASS CRITERIA FIXED 2026-11-14 BEFORE ANY 1.1 RUN, optimise stage "
        "(2013-2021, in-sample), each against the 1.0 base-rule run 10876 (11.46%, -12.4%, 20 trades): "
        "(a) round trips cut by at least 25% (15 or fewer); (b) CAGR up at least 0.5 point (11.96% or more); "
        "(c) max drawdown no deeper than -15%; (d) at 20bps a side, CAGR at least 0.5 point above the 1.0 "
        "rule at 20bps (10.75%, so 11.25% or more); (e) no worse than 10876 in at least 5 of the 9 calendar "
        "years. All five must hold for the floor to count as a fix; a miss is reported, never tuned "
        "({TBILL_FLOOR_PCT}% and the {TREND_WEEKS}-week length stay). The strategy's own pass rule against "
        "buy-and-hold (below) is unchanged and is reported beside them. Context 1980-2012 is reported, never "
        "a verdict (the floor is inert there until 2008-12). 1.1 RESULT: not yet run. "
        "1.0 FIGURES (behaviour unchanged by 1.1 except the floor): "
        "OPTIMISE STAGE (2013-2021, in-sample) -- THE BASE RULE FAILS THE PASS RULE; ONE SWITCH ON ITS OWN "
        "PASSES. Thresholds are his published ones, fixed before any run. The pass rule, written before "
        "reading a result: excess CAGR over S&P 500 total-return buy-and-hold above zero with a max drawdown "
        "no deeper, or a materially shallower drawdown at a CAGR within 1 point. Base rule (40-week trend + "
        "rates): 11.46% CAGR against 16.18%, excess -4.72, max drawdown -12.4% against -33.7%, Sharpe 1.11 "
        "against 1.00, 20 trades, 74% won, invested 67% of the time: far shallower, but 4.7 points short. "
        "Every switch added to it lowers CAGR (monetary composite 4.52%, invested 27%; his late-cycle brake "
        "10.50%). Switches alone: consumer sentiment passes (16.00%, excess -0.18, drawdown -23.0%, Sharpe "
        "1.19, 6 trades, invested 93%); capacity utilization never turns bearish in the window and equals "
        "buy-and-hold; industrial production (15.18%) and the curve (15.01%) miss on drawdown. Nasdaq 7.9% "
        "reversal: long/short 10.43% against 20.86%, drawdown -35.4% against -30.1% (fails); long/cash "
        "16.41%, excess -4.46, drawdown -19.9% (fails). Context, full stage 1980-2012 (never a verdict): base "
        "rule 9.00% against 10.07%, drawdown -29.1% against -55.2% (1.07 points short); monetary alone "
        "-0.41, drawdown -39.4%; Nasdaq long/cash +1.39, drawdown -46.8% against -77.4%. Few trades "
        "everywhere (1-28 in nine years), so every figure is a handful of decisions. No verify run; the "
        "sentiment switch is a candidate, not a result, and was one of 26 variants tried."
    ),
    "thesis": (
        "Boucher's liquidity cycle: stocks are fed by money that reaches the bond and bill markets first, so "
        "falling rates and a rising market together mark a safe environment, and rising rates mark the risk. "
        "His economic models turn the usual intuition round -- a hot economy (high capacity use, fast "
        "production growth, falling unemployment, rising inflation) is bad for stocks because it precedes "
        "a liquidity squeeze, and a weak one is good. The base rule asks only the two questions that need "
        "no forecast: is the market trending up, and are rates trending down?"
    ),
    "how_it_works": (
        "Base rule (pp. 56-57), on each week's last close: hold the S&P while the S&P 500 index closes above "
        "its {TREND_WEEKS}-week simple average AND either the 13-week T-bill yield or the 30-year Treasury "
        "yield is below its own {TREND_WEEKS}-week average. Otherwise hold T-bills.",
        "The zero bound (1.1): while the T-bill yield is below {TBILL_FLOOR_PCT}% the T-bill condition gives "
        "no signal, so the 30-year yield against its average decides the rates leg alone. The rule reads the "
        "bill as the direction of Fed policy; at the zero floor its basis-point moves are money-market "
        "noise (1.0 left the S&P eight times for a week on 1bp crossings). The floor is the top of the first "
        "25bp policy step above zero, fixed before any run; his own data never had a bill under 2%.",
        "Switches, each read at month-end closes as he tested them, each a gate added to the base rule "
        "(`--no-base` runs a switch alone, as his models were published). Liquidity (pp. 38-43): "
        "`--tbill-roc` the T-bill yield up less than {TBILL_ROC_MAX_PCT}% on a year earlier (a ratio, not "
        "points); `--bond-roc` the corporate bond proxy's {ROC_MONTHS}-month change above {BOND_ROC_MIN_PCT}%; "
        "`--long-roc` the 30-year yield up no more than {LONG_ROC_MAX_PCT}% on a year earlier; `--curve` "
        "30-year / T-bill yield above {CURVE_RATIO_MIN}; `--monetary` the first three together (his Model 5).",
        "Economic (pp. 45-49): `--capacity` capacity utilization at or below {CAPACITY_MAX_PCT}%; `--indpro` "
        "industrial production up no more than {INDPRO_ROC_MAX_PCT}% on a year earlier; `--unemployment` "
        "the unemployment rate above its level {UNEMP_LOOKBACK_MONTHS} months earlier (out when below, "
        "unchanged when equal); `--cpi-trend` CPI's {CPI_FAST_MONTHS}-month change below the change of its "
        "{CPI_SLOW_MONTHS}-month average on the {CPI_SLOW_MONTHS} months before; `--cpi-gdp` in when CPI "
        "inflation is under {CPI_MAX_PCT}% and annualised quarterly GDP growth under {GDP_MAX_PCT}%, out only "
        "when both are over. Sentiment (p. 76): `--sentiment` Michigan sentiment at or below {SENTIMENT_MAX}.",
        "The combination (`--brake`, pp. 51-52): he describes stepping aside when the economy is overheated "
        "(capacity utilization above {OVERHEAT_CAPACITY_PCT}% or industrial production up more than "
        "{OVERHEAT_INDPRO_PCT}%), inflation is turning up (CPI fast at or above slow) and the rate markets "
        "confirm (the monetary composite bearish). The brake holds T-bills only while all three hold.",
        "Nasdaq mode (pp. 73-74): `--mode otc` is always in the market on the Nasdaq Composite, long or "
        "short, reversing on a close {OTC_REVERSAL_PCT}% beyond the extreme close since the last reversal; "
        "`--mode otc_long` holds T-bills instead of the short. `--mode hold` and `--mode hold_otc` hold the "
        "benchmark throughout, for comparison.",
    ),
    "caveats": (
        "**His figures are not comparable as printed.** He annualised returns over the time invested, on "
        "price only, with no costs and no publication lag, and fitted the thresholds on 1943-1997. Here "
        "returns compound over the whole window, include dividends and T-bill interest, pay {cost_bps}bps "
        "a side, and read economic data only after its release.",
        "**Publication lag is a fixed estimate, and the data are today's vintage.** Each economic series is "
        "used only {CPI_LAG_DAYS} (CPI), {INDPRO_LAG_DAYS} (industrial production, capacity), {UNEMP_LAG_DAYS} "
        "(unemployment), {SENTIMENT_LAG_DAYS} (sentiment), {BAA_LAG_DAYS} (Baa yield) and {GDP_LAG_DAYS} "
        "(GDP) days after the date FRED stamps it. The values are FRED's latest revisions, not the first "
        "prints a trader saw: GDP, industrial production and capacity utilization are revised for years, "
        "so the economic switches read a cleaner economy than was known at the time.",
        "**The Dow Jones 20 Bond index is discontinued.** `--bond-roc` uses a proxy: a price index (no "
        "coupons, like the DJ 20) of a constant-maturity {BOND_PROXY_YEARS}-year bond re-priced each month at "
        "Moody's Baa corporate yield (FRED BAA, a monthly average). It moves with corporate bond prices but "
        "is not his index.",
        "**Rate-of-change on a near-zero yield is erratic.** `--tbill-roc` is a percent change of the yield "
        "itself, as he defined it. With the T-bill at 0.02-0.2% (2009-2015, 2020-2021) a few basis points "
        "read as a 50-200% rise, so this switch, and the composite, flicker in those years. A yield of zero "
        "now against a positive one a year earlier reads as -100%, which is bullish; a zero a year earlier "
        "makes the change undefined, which reads as not bullish. No month-end in 2012-2021 has a zero or "
        "negative ^IRX, so neither case occurs in the optimise window. The {TBILL_FLOOR_PCT}% floor applies "
        "to the base rule's T-bill condition only, not to this switch.",
        "**The zero-bound floor is a judgement from the rule's intent, not a fit.** It was fixed before any "
        "run and no other value is tried. It is not testable in his period (no zero bound) and moves "
        "2013-2015 and 2020-2021, about two-thirds of the optimise weeks; in 1980-2012 it acts only from "
        "December 2008.",
        "**The trade log.** The S&P is earned as a total-return series chained at VFINX's level, so the "
        "log's `entry_price` / `exit_price` are SPY's own close (blank before 1993) and the series levels "
        "are logged apart as `entry_tr_level` / `exit_tr_level`. `costs` is both fees; `r_multiple` is the "
        "trade's fractional return (there is no stop).",
        "**The instruments.** The S&P is held as SPY's total return from 1993 and the Vanguard 500 fund "
        "before it; signals use the ^GSPC price index. The T-bill yield is ^IRX (13-week) for the signal "
        "and the cash return. The long yield is the 30-year Treasury, the 10-year before 1977. The Nasdaq "
        "mode trades the Composite price index itself (no fund tracks it before 2003) with an assumed "
        "{OTC_DIV_YIELD} a year in dividends; its short is rebalanced daily, like an inverse fund, earns the "
        "T-bill rate on its proceeds and pays no borrow fee.",
        "**Fills.** A signal on a close fills at the close {FILL_DELAY_SESSIONS} session later; he filled "
        "on the signal's own close.",
        "**Left out of 1.0.** Breadth thrusts (pp. 74-75) need daily NYSE advances, declines and up "
        "volume, which are not stored. The valuation overlay, help-wanted index, sensitive-materials prices "
        "and the deflation switch are not specified fully enough or have no available series. India: the "
        "Nifty with the stored T-bill and 10-year G-sec is possible, but the 10-year history starts in "
        "2011, short of a 40-week average plus a nine-year window; not built.",
        "**One market, few trades.** A weekly and monthly rule on one index makes a handful of trades in "
        "nine years; a result rests on how few market declines the window holds.",
    ),
    "entry_rules": (
        "Base rule, at each week's last close: ^GSPC above its {TREND_WEEKS}-week average, and the T-bill "
        "yield (only while it is at least {TBILL_FLOOR_PCT}%) or the 30-year yield below its "
        "{TREND_WEEKS}-week average.",
        "Every switched-on switch is bullish as of the latest month-end close, reading only economic numbers "
        "already released by then.",
        "Fill: the whole book buys the S&P total-return series at the close {FILL_DELAY_SESSIONS} session "
        "after the signal close, less {cost_bps}bps.",
        "Nasdaq mode: long from the close after a close {OTC_REVERSAL_PCT}% above the lowest close since the "
        "short (or the exit) began.",
    ),
    "exit_rules": (
        "Sold in full at the close {FILL_DELAY_SESSIONS} session after a week-end or month-end close at which "
        "the base rule or any switched-on switch is no longer bullish, less {cost_bps}bps.",
        "No stop and no target: the rules are the exit. Out of the market the money earns the 13-week "
        "T-bill rate per calendar day. A holding at the end of a run is valued at the final close (OPEN).",
        "Nasdaq mode: the long reverses to short (`otc`) or to T-bills (`otc_long`) after a close "
        "{OTC_REVERSAL_PCT}% below the highest close since the long began.",
    ),
    "commands": {
        "Base rule (optimise)": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage optimise",
        "Base + monetary composite": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage optimise --bt='--monetary'",
        "The combination: base + late-cycle brake": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage optimise --bt='--brake'",
        "A model alone, as he tested it (e.g. capacity)": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage optimise --bt='--no-base --capacity'",
        "Nasdaq 7.9% reversal, long/short": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage optimise --bt='--mode otc'",
        "Compare: S&P 500 held throughout": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage optimise --bt='--mode hold'",
        "Context: 1980-2012 (not a verdict)": "python -m jobs enqueue backtest --market us --strategies boucher_stocks --stage full --start 1980-01-01 --bt='--end 2012-12-31'",
    },
}


class BoucherStocksStrategy(PortfolioStrategy):
    """Boucher's 40-week trend + rates timing of the S&P, with his monthly models as switches."""

    key = BS_DOC["key"]
    doc = BS_DOC
    family = "boucher_stocks"
    version = "1.1"
    changelog = (
        ("1.1", "2026-11-14",
         "Review 2026-11-14 (tracker #75). (1) The zero bound: while the 13-week T-bill yield is below "
         "TBILL_FLOOR_PCT = 0.50% its condition in the base rule gives no signal and the 30-year yield decides "
         "the rates leg alone. Fixed before any run from the rule's intent (the bill reads Fed policy; at the "
         "zero floor its 1-3bp moves are noise -- 1.0's eight one-week exits), never tuned; the 40-week length "
         "untouched. Pass criteria written into the status before the run. (2) The shared trade log "
         "(simulate, also used by boucher_bonds_gold): `costs` now holds the entry fee plus the exit fee (it "
         "held only the exit fee; the entry fee was, and is, inside pnl); `entry_price` / `exit_price` are "
         "SPY's own close, and the VFINX-scaled total-return levels moved to `entry_tr_level` / "
         "`exit_tr_level`. Reporting only: equity unchanged. (3) Caveat corrected: a zero T-bill now against a "
         "positive one a year earlier reads -100% (bullish) for --tbill-roc, not 'no signal'."),
        ("1.0", "2026-11-13",
         "First version, from Mark Boucher's The Hedge Fund Edge (1999). Every threshold is his published "
         "one, FIXED BEFORE THE FIRST RUN: base rule ^GSPC > 40-week SMA and (T-bill yield < 40-week SMA or "
         "30-year yield < 40-week SMA), weekly (pp. 56-57); switches at month-end, off by default: T-bill "
         "12m change < 6%, Baa bond-price proxy 12m change > -1.5%, 30-year 12m change <= 9%, 30y/T-bill > "
         "1.15, the first three together, capacity utilization <= 81.5%, industrial production 12m <= 5.6%, "
         "unemployment vs 29 months earlier, CPI 11-month vs 13-month-average change, CPI < 3.2% with GDP "
         "< 4% (out when both over), sentiment <= 99.5; the brake (overheated: CU > 88.5% or IP > 7%, and "
         "CPI fast >= slow, and the monetary composite bearish); Nasdaq 7.9% reversal long/short or "
         "long/cash. Release lags CPI 55, IP/CU 50, unemployment 40, sentiment 35, Baa 32, GDP 125 days "
         "after FRED's date. Fills at the next close, 5bps a side. Pass rule written before any result: "
         "excess CAGR > 0 vs S&P total-return buy-and-hold with a max drawdown no deeper, or a materially "
         "shallower drawdown at a CAGR within 1 point."),
    )
    name = BS_DOC["name"]
    description = BS_DOC["description"]
    status = BS_DOC["status"]
    thesis = BS_DOC["thesis"]
    how_it_works = tuple(BS_DOC["how_it_works"])
    caveats = tuple(BS_DOC["caveats"])
    entry_rules = tuple(BS_DOC["entry_rules"])
    exit_rules = tuple(BS_DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    horizon = "positional"
    runner = "boucher_stocks"

    mode = "timing"
    cost_bps = 5.0

    param_docs = (
        ("Mode", "mode", "timing: the base rule and switches. otc / otc_long: the Nasdaq reversal. hold / hold_otc: buy-and-hold."),
        ("Trend average", "TREND_WEEKS", "Weeks in the S&P's and both yields' simple averages."),
        ("T-bill floor", "TBILL_FLOOR_PCT", "13-week T-bill yield (%) below which the base rule's T-bill condition is silent and the long yield decides alone."),
        ("T-bill change", "TBILL_ROC_MAX_PCT", "% change of the T-bill yield on {ROC_MONTHS} months earlier, below which --tbill-roc is bullish."),
        ("Bond proxy change", "BOND_ROC_MIN_PCT", "% change of the {BOND_PROXY_YEARS}-year Baa price proxy, above which --bond-roc is bullish."),
        ("Long-yield change", "LONG_ROC_MAX_PCT", "% change of the 30-year yield, at or below which --long-roc is bullish."),
        ("Curve ratio", "CURVE_RATIO_MIN", "30-year / T-bill yield, above which --curve is bullish."),
        ("Capacity", "CAPACITY_MAX_PCT", "Capacity utilization, at or below which --capacity is bullish."),
        ("Industrial production", "INDPRO_ROC_MAX_PCT", "12-month % change, at or below which --indpro is bullish."),
        ("Unemployment lookback", "UNEMP_LOOKBACK_MONTHS", "Months back the unemployment rate is compared with."),
        ("CPI fast / slow", "CPI_FAST_MONTHS", "Months in the fast change; the slow compares {CPI_SLOW_MONTHS}-month averages."),
        ("CPI and GDP", "CPI_MAX_PCT", "CPI year-on-year; with GDP growth under {GDP_MAX_PCT}%, annualised."),
        ("Sentiment", "SENTIMENT_MAX", "Michigan sentiment, at or below which --sentiment is bullish."),
        ("Overheated", "OVERHEAT_CAPACITY_PCT", "The brake: capacity above this, or production growth above {OVERHEAT_INDPRO_PCT}%."),
        ("Nasdaq reversal", "OTC_REVERSAL_PCT", "% beyond the extreme close that reverses the Nasdaq position."),
        ("CPI release lag", "CPI_LAG_DAYS", "Days after FRED's date before a CPI reading is used (released mid-to-late next month)."),
        ("IP / capacity lag", "INDPRO_LAG_DAYS", "Days after FRED's date (Fed G.17, mid next month); capacity {CAPACITY_LAG_DAYS}."),
        ("Unemployment lag", "UNEMP_LAG_DAYS", "Days after FRED's date (the jobs report, first Friday of the next month)."),
        ("Sentiment lag", "SENTIMENT_LAG_DAYS", "Days after FRED's date (the final reading, end of the month)."),
        ("Baa lag", "BAA_LAG_DAYS", "Days after FRED's date (a monthly average, complete at month-end)."),
        ("GDP lag", "GDP_LAG_DAYS", "Days after the quarter's first day (the advance estimate, ~4 weeks after the quarter)."),
        ("Fill delay", "FILL_DELAY_SESSIONS", "Sessions between the signal close and the fill close."),
        ("Nasdaq dividends", "OTC_DIV_YIELD", "Annual yield added to the Nasdaq price index (credited long, charged short)."),
        ("Cost per side", "cost_bps", "Basis points per side."),
    )


# ------------------------------------------------------------------ runner

def context_boundary(end: str | None):
    """An earlier end than the stage's, for a context run; never later than the stage's own end."""
    from .masonson_tqqq import _context_boundary
    return _context_boundary(end)


def finish(a, argv, cls, tdf, eq, held, csh, costs, bench, bench_name, what: str, tag: str, title: str,
           module: str, start_note: str = "") -> dict:
    """Metrics, the run directory (through paths.run_dir), the files and the report -- shared with
    boucher_bonds_gold."""
    from ..paths import run_dir
    cfg = MARKETS[MARKET]
    bc = bench.reindex(eq.index).ffill()
    notes = [what, f"Signals on the close, fills at the close {FILL_DELAY_SESSIONS} session later; cash earns "
             "the 13-week T-bill yield (^IRX).", f"Costs: {a.cost_bps:g}bps per side. Benchmark: {bench_name}."]
    if start_note:
        notes.insert(0, start_note)
    if a.end:
        notes.insert(0, f"CONTEXT RUN to {a.end}: not an optimise or verify window, never a verdict.")
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=1,
                           costs_paid=costs, bench_close=bc, cash=csh, notes=notes)
    for k, v in metrics.benchmark_stats(bc).items():
        setattr(perf, k, v)
    perf.benchmark_name = bench_name
    name = (f"{a.start}" + (f"_to-{a.end}" if a.end else "") + f"_{tag}_{a.cost_bps:g}bps_{cls.spec_id()}")
    out = run_dir(MARKET, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "cash": csh, "positions_open": held,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 1))
    try:
        from . import report as report_mod
        md = report_mod.write_report(out, title + (f" to {a.end} (context)" if a.end else ""), perf, eq, held,
                                     tdf, cfg.currency_symbol, 1, bc,
                                     f"python3 -m swing_screener.backtesting.{module} " + " ".join(argv or []))
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


def main(argv: list[str] | None = None) -> dict | None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Boucher stock timing")
    ap.add_argument("--strategy", default=BoucherStocksStrategy.key)
    ap.add_argument("--market", default=MARKET, choices=[MARKET])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", default=None, help="an earlier end than the stage's, for a context run")
    ap.add_argument("--mode", default=BoucherStocksStrategy.mode, choices=list(MODES))
    ap.add_argument("--no-base", action="store_true", help="run the switches alone, without the 40-week rule")
    for sw in SWITCHES:
        ap.add_argument("--" + sw.replace("_", "-"), action="store_true")
    ap.add_argument("--cost-bps", type=float, default=BoucherStocksStrategy.cost_bps)
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)

    on = tuple(sw for sw in SWITCHES if getattr(a, sw))
    with context_boundary(a.end):
        tdf, eq, held, csh, costs, bench, bench_name, _r, _pos = run(a.start, a.mode, a.cost_bps,
                                                                     base=not a.no_base, switches=on)
        if a.mode == "timing":
            what = ("Timing: " + ("40-week trend + rates" if not a.no_base else "no base rule")
                    + (f", switches {', '.join(on)} (month-end)" if on else "") + ".")
            tag = "-".join((["nobase"] if a.no_base else ["base40w"]) + [sw.replace("_", "") for sw in on])
        else:
            what = {"otc": f"Nasdaq {OTC_REVERSAL_PCT}% reversal, long/short.",
                    "otc_long": f"Nasdaq {OTC_REVERSAL_PCT}% reversal, long/T-bills.",
                    "hold": "Comparison: S&P 500 total return held throughout.",
                    "hold_otc": "Comparison: the Nasdaq Composite held throughout."}[a.mode]
            tag = a.mode
        if a.mode == "timing" and on:
            what += " Economic data used only after its release lag."
        return finish(a, argv, BoucherStocksStrategy, tdf, eq, held, csh, costs, bench, bench_name, what, tag,
                      f"Boucher stock timing ({tag}), {a.start} onward", "boucher_stocks")


if __name__ == "__main__":
    main()
