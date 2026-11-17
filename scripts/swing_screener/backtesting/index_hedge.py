"""A short that is actually short in declines: the market index, shorted while its trend is down.

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.index_hedge

Follow-up to research/sleeve-turtle-trend-2026-11-17.md: `stage4_shorts` held a short on 0.2-4% of India's
sessions, so as a hedge it was cash. This sleeve is short whenever a trend rule on the market's own benchmark
says so, and in cash otherwise -- held as index futures (or an inverse ETF): the collateral earns the stored
cash rate, the short pays the index's total return (dividends included, `index_data.total_return_index`),
and each switch costs COST_BPS. The signal is read at a session's close and applies from the next session.

A research test, not a registered strategy: if it passes it becomes one, with its own docs, version and a
proper verify run.

**The rules, written before any figure was computed (2026-11-17).**

Signals (on the benchmark's price close):

    sma200      short while the close is below its 200-day average
    sma50_fall  short while the close is below its 50-day average AND that average is below its level 10
                sessions earlier (faster; built because the regime study found the 200-day too slow for crashes)
    tsmom12     short while the 12-month return (252 sessions) is negative, checked at each month's last session
                (Moskowitz, Ooi & Pedersen 2012)

The test is `sleeve_blend`'s, unchanged, with the signal chosen in the same step: in-sample (2013-2021), among
every (signal, weight) pair whose blend cuts the book's max drawdown by >= 20% (relative) while giving up at most
2 CAGR points, the one with the highest Sharpe over cash; then that pair is judged once on 2022 on -- pass if
its Sharpe >= the book's, its drawdown is shallower, and its CAGR is no more than 2 points lower. The same
weight in cash is shown beside it, as before.
"""
from __future__ import annotations

import argparse
import datetime as dt

import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, index_data
from . import metrics
from . import sleeve_blend as sb

SIGNALS = ("sma200", "sma50_fall", "tsmom12")
COST_BPS = 5.0
SMA_LONG, SMA_FAST, FAST_SLOPE_BARS, TSMOM_BARS = 200, 50, 10, 252


def short_flag(close: pd.Series, signal: str) -> pd.Series:
    """True on a session the sleeve is short over (decided at the previous close)."""
    c = close.astype(float)
    if signal == "sma200":
        sma = c.rolling(SMA_LONG, min_periods=SMA_LONG).mean()
        on = (c < sma) & sma.notna()
    elif signal == "sma50_fall":
        sma = c.rolling(SMA_FAST, min_periods=SMA_FAST).mean()
        on = (c < sma) & (sma < sma.shift(FAST_SLOPE_BARS)) & sma.notna()
    elif signal == "tsmom12":
        ret = c / c.shift(TSMOM_BARS) - 1
        month_end = pd.Series(c.index, index=c.index).groupby(c.index.to_period("M")).transform("max") == c.index
        on = (ret < 0).where(month_end).ffill().fillna(False).astype(bool)
    else:
        raise ValueError(signal)
    return on.shift(1).fillna(False).astype(bool)


def sleeve_returns(market: str, signal: str) -> tuple[pd.Series, pd.Series]:
    """(daily returns, short flag) of the sleeve on the benchmark's sessions."""
    cfg = MARKETS[market]
    close = cache.load_cached(market, cfg.benchmark_ticker)["close"].astype(float)
    tr, _ = index_data.total_return_index(market, cfg.benchmark_symbol)
    tr_ret = tr.astype(float).reindex(close.index).ffill().pct_change().fillna(0.0)
    cash = index_data.cash_rate_series(market, close.index)[0] / metrics.TRADING_DAYS
    short = short_flag(close, signal)
    switch = short.astype(int).diff().abs().fillna(0.0)
    r = cash - tr_ret.where(short, 0.0) - switch * COST_BPS / 1e4
    return r.iloc[1:], short.iloc[1:]


def main(argv=None) -> None:
    argparse.ArgumentParser(description=__doc__.split("\n")[0]).parse_args(argv)
    from ..web.server import strategy_edges
    from .regime_breakdown import episodes, phases
    edges = strategy_edges()
    sb.SLEEVE_COST_BPS = COST_BPS
    out = [f"_Computed {dt.date.today()} from stored full-period runs and the benchmarks' stored closes._"]
    for market, books in sb.BOOKS.items():
        cfg = MARKETS[market]
        close = cache.load_cached(market, cfg.benchmark_ticker)["close"].astype(float)
        phase = phases(close, episodes(close.loc["2012-01-01":]))
        sleeves = {s: sleeve_returns(market, s) for s in SIGNALS}
        L = [f"### {market.upper()} — short {cfg.benchmark_symbol} while its trend is down", "",
             "| Signal | Window | CAGR | Max DD | Sharpe over cash | Sessions short | Short on decline sessions |",
             "|---|---|---|---|---|---|---|"]
        for s, (r, short) in sleeves.items():
            for name, sl in (("2013–2021", slice(*sb.OPTIMISE)), ("2022 on", slice(sb.VERIFY_FROM, None))):
                st = sb.stats(r.loc[sl], market)
                sh = short.loc[sl]
                dec = sh[phase.reindex(sh.index) == "decline"]
                L.append(f"| `{s}` | {name} | {st['cagr']:.1f}% | {st['dd']:.1f}% | {st['sharpe']:.2f} | "
                         f"{100 * sh.mean():.0f}% | {100 * dec.mean():.0f}% |")
        out.append("\n".join(L))
        for key in books:
            book = sb._full_run_returns(key, market, edges)
            if book is None:
                continue
            book = book.loc[book.index >= pd.Timestamp("2013-01-01")]
            # every signal through the sleeve test; the pick is the best qualifying (signal, weight) in-sample
            res = {s: sb.judge(book, r, market) for s, (r, _) in sleeves.items()}
            base = res[SIGNALS[0]]["optimise"][0.0]
            cands = [(s, w) for s in SIGNALS for w in sb.WEIGHTS if res[s]["optimise"][w]
                     and res[s]["optimise"][w]["dd"] >= base["dd"] * (1 - sb.MIN_DD_CUT_PCT / 100)
                     and res[s]["optimise"][w]["cagr"] >= base["cagr"] - sb.MAX_CAGR_GIVE]
            if not cands:
                out.append(f"#### {market.upper()} — `{key}`: no (signal, weight) qualified in-sample; nothing to verify.")
                continue
            s, w = max(cands, key=lambda p: res[p[0]]["optimise"][p[1]]["sharpe"])
            r_s = sleeves[s][0]
            # re-judge with the chosen signal so the table's arrow, verdict and cash row follow the joint pick
            one = sb.judge(book, r_s, market)
            one["pick"] = w
            v, vb = one["verify"][w], one["verify"][0.0]
            one["checks"] = {"sharpe": v["sharpe"] >= vb["sharpe"], "dd": v["dd"] > vb["dd"],
                             "cagr": v["cagr"] >= vb["cagr"] - sb.MAX_CAGR_GIVE}
            one["passed"] = all(one["checks"].values())
            rf = index_data.cash_rate_series(market, book.index)[0] / metrics.TRADING_DAYS
            for name, sl in (("optimise", slice(*sb.OPTIMISE)), ("verify", slice(sb.VERIFY_FROM, None)),
                             ("full", slice(None, None))):
                one[name]["cash"] = sb.stats(sb.blend(book.loc[sl], rf.loc[sl], w), market)
            out.append(sb.to_markdown(market, key, f"index short ({s})", one))
    print("\n\n".join(out))


if __name__ == "__main__":
    main()
