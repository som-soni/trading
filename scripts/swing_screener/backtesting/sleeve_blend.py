"""A long book with a hedge sleeve beside it: does a slice of `turtle_trend` make the account better?

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.sleeve_blend [--sleeve turtle_trend]

Reads stored equity curves only (each strategy's full-period run, 2013 -> today, current rules) and blends
them: the account holds the long book at (1 - w) and the sleeve at w, put back to the split at each month's
last session. A sleeve scales linearly with the capital it is given, so this is the same account as two
sub-accounts topped up monthly -- the method `combination.py` uses. Moving money between them is charged
each side's per-side cost (BOOK_COST_BPS for the stock book, SLEEVE_COST_BPS for the ETF sleeve).

A sleeve that trades the book's own market (`stage4_shorts`) is taken from that market's run; otherwise an
India book holds the US-listed sleeve in rupees: its daily return is the sleeve's dollar return times the
change in USD/INR (stored `USDINR`).

**The test, written before any blend was computed (2026-11-17).**

1. *Choose the weight in-sample* (2013-01-01 -> 2021-12-31) among WEIGHTS: of the weights whose blend has a
   max drawdown at least MIN_DD_CUT_PCT % shallower than the book alone (relative) and a CAGR no more than
   MAX_CAGR_GIVE points lower, the one with the highest Sharpe over cash. None qualifying = no sleeve.
2. *Judge that weight once out-of-sample* (2022-01-01 -> the last stored session): PASS if its Sharpe over
   cash is at least the book's, its max drawdown is shallower than the book's, and its CAGR is no more than
   MAX_CAGR_GIVE points lower.

Beside the test, each table shows the chosen weight (or 20% when none was chosen) held in CASH at the
market's stored rate instead -- added after the first results, as a comparison only: a hedge sleeve has to do
better than simply holding less of the book. The full period is shown as context. The two windows are cut from the one full-period run per strategy, so
a position open at 2021-12-31 carries across the cut -- the windows are dated, not separately simulated.

Known understatement: the `turtle_trend` runner credits no interest on idle collateral, which a real futures
or ETF account earns (US T-bills 4-5% in 2023-25), so the sleeve's own return is low by roughly the cash rate
on its idle share.
"""
from __future__ import annotations

import argparse
import datetime as dt

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import index_data
from . import metrics
from .regime_breakdown import _curve, _source_paths

WEIGHTS = (0.10, 0.20, 0.30)
MIN_DD_CUT_PCT = 20.0      # the blend's max drawdown at least this much shallower, relative (step 1)
MAX_CAGR_GIVE = 2.0        # points of CAGR the blend may give up (steps 1 and 2)
BOOK_COST_BPS = 20.0       # per side, money moved in or out of a stock book
SLEEVE_COST_BPS = 5.0      # per side, the ETF sleeve (turtle_trend's own COST_BPS)
OPTIMISE = ("2013-01-01", "2021-12-31")
VERIFY_FROM = "2022-01-01"

BOOKS = {
    "us": ("quality_momentum", "momentum_dual_combo", "dual_momentum", "value_ranking", "masonson_tqqq"),
    "india": ("momentum_dual_combo", "dual_momentum", "quality_momentum", "momentum_baseline"),
}
SLEEVE_MARKET = "us"


def _full_run_returns(key: str, market: str, edges: dict) -> pd.Series | None:
    rid = ((edges.get(key) or {}).get(market) or {}).get("full", {}) or {}
    rid = rid.get("run_id")
    if not rid:
        return None
    path = _source_paths([rid]).get(rid)
    df = _curve(path) if path else None
    return None if df is None else df["equity"].astype(float).pct_change().dropna()


def _in_currency(r_usd: pd.Series, market: str) -> pd.Series:
    if market == SLEEVE_MARKET:
        return r_usd
    fx = index_data.load(market, "USDINR").astype(float)
    fx = fx.reindex(fx.index.union(r_usd.index)).ffill()
    fx_r = fx.pct_change().reindex(r_usd.index).fillna(0.0)
    return (1 + r_usd) * (1 + fx_r) - 1


def blend(book: pd.Series, sleeve: pd.Series, w: float) -> pd.Series:
    """Daily returns of the account: two sleeves compounding apart, reset to (1-w, w) each month-end, the
    money moved charged at each side's cost. The sleeve's returns on the book's non-sessions are carried
    into the next book session, so no move is lost to a calendar mismatch."""
    idx = book.index
    sleeve = sleeve[(sleeve.index >= idx[0]) & (sleeve.index <= idx[-1])]
    s = (1 + sleeve).groupby(sleeve.index.map(lambda d: idx[idx.searchsorted(d)] if d <= idx[-1] else pd.NaT)).prod() - 1
    s = s.reindex(idx).fillna(0.0)
    month_end = set(pd.Series(idx, index=idx).groupby(idx.to_period("M")).max())
    a, b, prev, out = 1 - w, w, 1.0, []
    for d in idx:
        a *= 1 + book.at[d]
        b *= 1 + s.at[d]
        total = a + b
        if d in month_end and w > 0:
            moved = abs(b - w * total)
            total -= moved * (BOOK_COST_BPS + SLEEVE_COST_BPS) / 1e4
            a, b = (1 - w) * total, w * total
        out.append(total / prev - 1)
        prev = total
    return pd.Series(out, index=idx)


def stats(r: pd.Series, market: str) -> dict:
    if len(r) < 60:
        return {}
    eq = (1 + r).cumprod()
    years = (r.index[-1] - r.index[0]).days / 365.25
    rf = index_data.cash_rate_series(market, r.index)[0] / metrics.TRADING_DAYS
    vol, sharpe, _ = metrics.risk_stats(r, rf)
    return {"cagr": 100 * (eq.iloc[-1] ** (1 / years) - 1), "dd": 100 * float((eq / eq.cummax() - 1).min()),
            "sharpe": sharpe, "vol": vol}


def judge(book: pd.Series, sleeve: pd.Series, market: str) -> dict:
    win = {"optimise": slice(*OPTIMISE), "verify": slice(VERIFY_FROM, None), "full": slice(None, None)}
    res = {"corr": float(book.resample("ME").apply(lambda x: (1 + x).prod() - 1).corr(
        sleeve.resample("ME").apply(lambda x: (1 + x).prod() - 1)))}
    for name, sl in win.items():
        b = book.loc[sl]
        res[name] = {0.0: stats(b, market)}
        for w in WEIGHTS:
            res[name][w] = stats(blend(b, sleeve, w), market)
    base = res["optimise"][0.0]
    ok = [w for w in WEIGHTS if res["optimise"][w]
          and res["optimise"][w]["dd"] >= base["dd"] * (1 - MIN_DD_CUT_PCT / 100)
          and res["optimise"][w]["cagr"] >= base["cagr"] - MAX_CAGR_GIVE]
    pick = max(ok, key=lambda w: res["optimise"][w]["sharpe"]) if ok else None
    res["pick"] = pick
    if pick is not None and res["verify"][pick]:
        v, vb = res["verify"][pick], res["verify"][0.0]
        res["checks"] = {"sharpe": v["sharpe"] >= vb["sharpe"], "dd": v["dd"] > vb["dd"],
                         "cagr": v["cagr"] >= vb["cagr"] - MAX_CAGR_GIVE}
        res["passed"] = all(res["checks"].values())
    # the same weight held in cash instead (the market's stored cash rate): a sleeve that only matches this
    # is buying nothing a smaller book would not give. Shown beside the test; not part of the pre-set rule.
    rf = index_data.cash_rate_series(market, book.index)[0] / metrics.TRADING_DAYS
    for name, sl in win.items():
        res[name]["cash"] = stats(blend(book.loc[sl], rf.loc[sl], pick or WEIGHTS[1]), market)
    return res


def _row(label, s):
    return (f"| {label} | {s['cagr']:.1f}% | {s['dd']:.1f}% | {s['sharpe']:.2f} | {s['vol']:.1f}% |"
            if s else f"| {label} | — | — | — | — |")


def to_markdown(market: str, book: str, sleeve: str, res: dict) -> str:
    L = [f"#### {market.upper()} — `{book}` + `{sleeve}` (monthly correlation {res['corr']:+.2f})", ""]
    pick = res["pick"]
    if pick is None:
        L.append(f"**In-sample choice: none.** No weight cut the drawdown by {MIN_DD_CUT_PCT:.0f}% while giving up "
                 f"at most {MAX_CAGR_GIVE:.1f} points of CAGR, so there is nothing to verify.")
    else:
        verdict = "PASS" if res.get("passed") else "FAIL"
        failed = [k for k, v in (res.get("checks") or {}).items() if not v]
        L.append(f"**In-sample choice: {pick:.0%} sleeve. Out-of-sample: {verdict}**"
                 + (f" (failed: {', '.join(failed)})." if failed else "."))
    for name, title in (("optimise", f"In-sample {OPTIMISE[0]} → {OPTIMISE[1]}"),
                        ("verify", f"Out-of-sample {VERIFY_FROM} →"), ("full", "Full period (context)")):
        L += ["", f"*{title}*", "", "| Account | CAGR | Max drawdown | Sharpe (over cash) | Volatility |",
              "|---|---|---|---|---|", _row("Book alone", res[name][0.0])]
        for w in WEIGHTS:
            L.append(_row(f"{1 - w:.0%} book + {w:.0%} sleeve" + (" ←" if w == pick else ""), res[name][w]))
        L.append(_row(f"*{1 - (pick or WEIGHTS[1]):.0%} book + {pick or WEIGHTS[1]:.0%} cash*", res[name]["cash"]))
    return "\n".join(L)


def main(argv=None) -> None:
    global SLEEVE_COST_BPS
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sleeve", default="turtle_trend")
    ap.add_argument("--sleeve-cost-bps", type=float, default=SLEEVE_COST_BPS,
                    help="per side on money moved into or out of the sleeve (20 for a stock book)")
    a = ap.parse_args(argv)
    SLEEVE_COST_BPS = a.sleeve_cost_bps
    from ..web.server import strategy_edges
    edges = strategy_edges()
    sleeve_usd = _full_run_returns(a.sleeve, SLEEVE_MARKET, edges)
    out = [f"_Computed {dt.date.today()} from stored full-period runs; sleeve `{a.sleeve}`._"]
    for market, books in BOOKS.items():
        # a sleeve that trades this market itself (stage4_shorts) is held there; otherwise the US run, in
        # this market's currency
        own = _full_run_returns(a.sleeve, market, edges) if market != SLEEVE_MARKET else None
        if own is not None:
            sleeve, where = own, f"its own {market} run"
        elif sleeve_usd is not None:
            sleeve, where = _in_currency(sleeve_usd, market), f"the {SLEEVE_MARKET} run" + (
                "" if market == SLEEVE_MARKET else " in local currency")
        else:
            out.append(f"#### {market.upper()}: no full-period `{a.sleeve}` run stored, skipped.")
            continue
        out.append(f"_{market.upper()} sleeve: {where}, {sleeve.index[0].date()} → {sleeve.index[-1].date()}._")
        for key in books:
            book = _full_run_returns(key, market, edges)
            if book is None:
                out.append(f"#### {market.upper()} — `{key}`: no full-period run stored, skipped.")
                continue
            book = book.loc[book.index >= sleeve.index[0]]
            out.append(to_markdown(market, key, a.sleeve, judge(book, sleeve, market)))
    print("\n\n".join(out))


if __name__ == "__main__":
    main()
