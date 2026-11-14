"""Mechanical checks on one stored backtest run: accounting, fills, stops, sizing and risk, regimes.

Reads the run's report tables through the web app's API and stored prices read-only; reads nothing
after the run's own window end. Prints markdown for the review to quote. It flags; it does not judge --
a flag is a lead to check against the code and the trade chart, not a finding.

    cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/audit_run.py \
        --run 2357 [--host http://127.0.0.1:8000] [--risk-pct 1.0]

Works for per-symbol strategies (a `trades` table with entry, stop and shares). A portfolio runner
without stops still gets accounting and regimes; the sizing and stop sections say what is missing.
"""

import argparse
import json
import math
import urllib.request

import numpy as np
import pandas as pd

from swing_screener.config import MARKETS
from swing_screener.marketdata import cache

FILL_TOL = 0.005        # a fill this far outside the bar's low-high range is flagged (adjustment noise below it)
GAP_TOL = 0.005         # a stop exit this far below the stop is a gap-through
TREND_DAYS = 200        # index trend: prior close above its 200-day average
VOL_DAYS = 20           # realised volatility window
VOL_RANK_DAYS = 252     # high volatility: above its own trailing one-year median
MIN_EPISODE_DAYS = 5    # a regime run shorter than this is noise, not an episode


def get(host: str, path: str):
    with urllib.request.urlopen(host.rstrip("/") + path, timeout=120) as r:
        return json.load(r)


def table(host: str, rid: int, name: str) -> pd.DataFrame | None:
    try:
        t = get(host, f"/api/reports/{rid}/tables/{name}")
    except Exception:
        return None
    if not t.get("rows"):
        return None
    return pd.DataFrame(t["rows"], columns=t["columns"])


def pct(x: float) -> str:
    return "n/a" if x is None or (isinstance(x, float) and math.isnan(x)) else f"{x:.2f}%"


def q(s: pd.Series, ps=(5, 25, 50, 75, 95)) -> str:
    s = s.dropna()
    if s.empty:
        return "n/a"
    return ", ".join(f"p{p} {np.percentile(s, p):.2f}" for p in ps) + f" (n={len(s)})"


def cagr_dd(ret: pd.Series) -> tuple[float, float]:
    eq = (1 + ret.fillna(0)).cumprod()
    years = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    return (eq.iloc[-1] ** (1 / years) - 1) * 100, ((eq / eq.cummax()) - 1).min() * 100


def episodes(state: pd.Series) -> int:
    runs = (state != state.shift()).cumsum()
    lens = state.groupby(runs).agg(["first", "size"])
    return int(((lens["first"]) & (lens["size"] >= MIN_EPISODE_DAYS)).sum())


def accounting(tr: pd.DataFrame | None, eq: pd.DataFrame | None, start: str, end: str) -> list[str]:
    out = ["## Accounting"]
    if eq is None:
        return out + ["No equity table: cannot reconcile."]
    e = eq.set_index(pd.to_datetime(eq["date"]))
    out.append(f"- Equity {e['equity'].iloc[0]:,.0f} -> {e['equity'].iloc[-1]:,.0f}, "
               f"{e.index[0].date()} to {e.index[-1].date()} (window {start} to {end}).")
    if e.index[-1] > pd.Timestamp(end):
        out.append(f"- **FLAG** equity runs past the window end ({e.index[-1].date()}).")
    if "cash" in e and (e["cash"] < -1).any():
        out.append(f"- **FLAG** cash below zero on {(e['cash'] < -1).sum()} days (min {e['cash'].min():,.0f}): leverage the rules may not allow.")
    if "positions_open" in e:
        out.append(f"- Open positions: max {int(e['positions_open'].max())}, median {e['positions_open'].median():.0f} "
                   "(compare the max with the slot limit in the rules).")
    if tr is not None and "pnl" in tr:
        closed = tr[tr["exit_date"].notna()] if "exit_date" in tr else tr
        cred = tr["credited"].fillna(0).sum() if "credited" in tr else 0.0
        resid = e["equity"].iloc[-1] - e["equity"].iloc[0] - closed["pnl"].sum()
        out.append(f"- Sum of trade P&L {closed['pnl'].sum():,.0f} (of which credited dividends/demergers {cred:,.0f}, "
                   f"if the runner books them into P&L); unexplained {resid:,.0f} "
                   f"({resid / e['equity'].iloc[0] * 100:.2f}% of start). The rest should be cash interest, positions "
                   "still open at the end, or rounding: anything large is a lead.")
        if "costs" in tr:
            out.append(f"- Costs {tr['costs'].sum():,.0f} over {len(tr)} trades "
                       f"({tr['costs'].sum() / tr['notional'].sum() * 1e4:.1f} bps of notional, both sides)." if "notional" in tr
                       else f"- Costs {tr['costs'].sum():,.0f}.")
        late = tr[pd.to_datetime(tr["entry_date"]) > pd.Timestamp(end)] if "entry_date" in tr else []
        if len(late):
            out.append(f"- **FLAG** {len(late)} trades enter after the window end.")
        if {"entry_date", "exit_date"} <= set(tr):
            bad = tr[pd.to_datetime(tr["exit_date"]) < pd.to_datetime(tr["entry_date"])]
            if len(bad):
                out.append(f"- **FLAG** {len(bad)} trades exit before they enter.")
    return out


def fills(tr: pd.DataFrame, market: str) -> list[str]:
    out = ["## Fills against the day's bar"]
    if not {"symbol", "entry_date", "entry_price"} <= set(tr):
        return out + ["No per-symbol fills to check."]
    bad_in, bad_out, missing = [], [], 0
    for sym, g in tr.groupby("symbol"):
        px = cache.load_cached(market, sym)
        if px is None or px.empty:
            missing += len(g)
            continue
        for _, t in g.iterrows():
            for when, price, bucket in (("entry_date", "entry_price", bad_in), ("exit_date", "exit_price", bad_out)):
                if pd.isna(t.get(when)) or pd.isna(t.get(price)):
                    continue
                d = pd.Timestamp(t[when])
                if d not in px.index:
                    continue
                lo, hi = px.at[d, "low"], px.at[d, "high"]
                if t[price] < lo * (1 - FILL_TOL) or t[price] > hi * (1 + FILL_TOL):
                    bucket.append(f"{sym} {d.date()} {t[price]:.2f} vs bar {lo:.2f}-{hi:.2f}")
    out.append(f"- Entries outside the bar: {len(bad_in)}; exits outside the bar: {len(bad_out)}; "
               f"trades with no stored prices: {missing}.")
    for x in (bad_in + bad_out)[:8]:
        out.append(f"  - {x}")
    if bad_in or bad_out:
        out.append("  A fill outside the bar is either a look-ahead (filled at a price the day never traded), a split "
                   "or adjustment mismatch, or a modelled gap fill: check each against the code and a split list.")
    return out


def stops_and_sizing(tr: pd.DataFrame, eq: pd.DataFrame | None, risk_pct: float | None) -> list[str]:
    out = ["## Stops"]
    need = {"entry_price", "initial_stop", "shares"}
    if not need <= set(tr):
        return out + [f"No stop columns ({', '.join(sorted(need - set(tr)))} missing): stops and sizing not checkable here."]
    t = tr.copy()
    t["risk_ps"] = t["entry_price"] - t["initial_stop"]
    inv = t[t["risk_ps"] <= 0]
    if len(inv):
        out.append(f"- **FLAG** {len(inv)} long trades with the initial stop at or above the entry.")
    t["stop_pct"] = t["risk_ps"] / t["entry_price"] * 100
    out.append(f"- Stop distance % of entry: {q(t['stop_pct'])}.")
    if "exit_reason" in t and "exit_price" in t:
        st = t[t["exit_reason"].astype(str).str.upper().str.contains("STOP")]
        stop_col = "stop" if "stop" in t else "initial_stop"
        gap = st[st["exit_price"] < st[stop_col] * (1 - GAP_TOL)]
        out.append(f"- Stop exits {len(st)}; gapped through the stop {len(gap)} "
                   f"({len(gap) / max(len(st), 1) * 100:.0f}%).")
    if "r_multiple" in t:
        out.append(f"- R per trade: {q(t['r_multiple'])}; losses worse than -1.5R: {(t['r_multiple'] < -1.5).sum()}, "
                   f"worse than -2R: {(t['r_multiple'] < -2).sum()}. A stop rule caps losses near -1R; the tail is gaps, "
                   "slippage or a stop that was not honoured.")
    out.append("## Sizing and risk")
    if eq is None:
        return out + ["No equity table: cannot express risk as a share of equity."]
    e = eq.set_index(pd.to_datetime(eq["date"]))["equity"]
    t["eq_before"] = [e[e.index < pd.Timestamp(d)].iloc[-1] if (e.index < pd.Timestamp(d)).any() else e.iloc[0]
                      for d in t["entry_date"]]
    t["risk_eq"] = t["shares"] * t["risk_ps"] / t["eq_before"] * 100
    t["size_eq"] = t["shares"] * t["entry_price"] / t["eq_before"] * 100
    out.append(f"- Risk at entry, % of equity: {q(t['risk_eq'])}.")
    out.append(f"- Position value, % of equity: {q(t['size_eq'])}; positions under 0.5% of equity: "
               f"{(t['size_eq'] < 0.5).sum()} (crumbs left by cash or slot limits, or partial fills: check the rule that sized them).")
    if risk_pct:
        over = t[t["risk_eq"] > risk_pct * 1.1]
        under = t[t["risk_eq"] < risk_pct * 0.5]
        out.append(f"- Against the rule's {risk_pct}%: {len(over)} trades risk more than 110% of it, {len(under)} less "
                   "than half (often the position-size cap binding: check which rule did).")
    # open heat: initial risk of every position open that day, as % of that day's equity
    heat = pd.Series(0.0, index=e.index)
    for _, r in t.iterrows():
        if pd.isna(r.get("exit_date")):
            continue
        heat[(heat.index >= pd.Timestamp(r["entry_date"])) & (heat.index < pd.Timestamp(r["exit_date"]))] += \
            r["shares"] * max(r["risk_ps"], 0)
    heat = heat / e * 100
    out.append(f"- Open heat (initial risk of all open positions, % of equity): {q(heat[heat > 0])}; max {heat.max():.1f}%.")
    return out


def regimes(market: str, eq: pd.DataFrame | None, tr: pd.DataFrame | None, start: str, end: str) -> list[str]:
    out = ["## Regimes (point in time: each day uses the PRIOR close)"]
    tk = MARKETS[market].benchmark_ticker
    px = cache.load_cached(market, tk)
    if px is None or eq is None:
        return out + [f"No index prices for {tk} or no equity table."]
    c = px["close"][px.index <= pd.Timestamp(end)]
    sma = c.rolling(TREND_DAYS).mean()
    vol = c.pct_change().rolling(VOL_DAYS).std() * math.sqrt(252)
    vmed = vol.rolling(VOL_RANK_DAYS).median()
    state = pd.DataFrame({"up": (c > sma), "hivol": (vol > vmed)}).shift(1)   # known at today's open
    e = eq.set_index(pd.to_datetime(eq["date"]))["equity"]
    days = e.index[e.index >= pd.Timestamp(start)]
    s_ret = e.pct_change().reindex(days)
    i_ret = c.pct_change().reindex(days)
    st = state.reindex(days)
    st = st[st.notna().all(axis=1)].astype(bool)
    out.append(f"Index {tk}. Trend: prior close above its {TREND_DAYS}-day average. Volatility: {VOL_DAYS}-day "
               f"realised above its trailing {VOL_RANK_DAYS}-day median. Episodes count runs of at least "
               f"{MIN_EPISODE_DAYS} days.")
    out.append("")
    out.append("| Regime | Days | Episodes | Strategy ann. return | Index ann. return | Excess |")
    out.append("|---|---|---|---|---|---|")
    for name, mask in (("Uptrend", st["up"]), ("Downtrend", ~st["up"]),
                       ("Low volatility", ~st["hivol"]), ("High volatility", st["hivol"]),
                       ("Up + low vol", st["up"] & ~st["hivol"]), ("Down + high vol", ~st["up"] & st["hivol"])):
        d = mask[mask].index
        if len(d) < 20:
            out.append(f"| {name} | {len(d)} | - | too few days | | |")
            continue
        sr, ir = s_ret.reindex(d).mean() * 252 * 100, i_ret.reindex(d).mean() * 252 * 100
        out.append(f"| {name} | {len(d)} | {episodes(mask)} | {sr:.1f}% | {ir:.1f}% | {sr - ir:+.1f} pts |")
    if tr is not None and {"entry_date", "r_multiple"} <= set(tr):
        t = tr.copy()
        t["up"] = st["up"].reindex(pd.to_datetime(t["entry_date"])).values
        out.append("")
        out.append("| Trades entered in | n | Win rate | Avg R | Total R |")
        out.append("|---|---|---|---|---|")
        for name, m in (("Uptrend", t["up"] == True), ("Downtrend", t["up"] == False)):  # noqa: E712
            g = t[m]
            if len(g):
                out.append(f"| {name} | {len(g)} | {(g['r_multiple'] > 0).mean() * 100:.0f}% | "
                           f"{g['r_multiple'].mean():+.2f} | {g['r_multiple'].sum():+.1f} |")
    # the overlay test: what a trend filter is worth on its own, and on top of the strategy
    up = st["up"].reindex(days).fillna(False)
    rows = [("Index, buy and hold", i_ret), ("Index, only in uptrends (else cash at 0%)", i_ret.where(up, 0.0)),
            ("Strategy as run", s_ret), ("Strategy, only in uptrends (approximation)", s_ret.where(up, 0.0))]
    out.append("")
    out.append("| Book | CAGR | Max DD |")
    out.append("|---|---|---|")
    for name, r in rows:
        cg, dd = cagr_dd(r.dropna())
        out.append(f"| {name} | {cg:.2f}% | {dd:.1f}% |")
    out.append("")
    out.append("The strategy-in-uptrends row zeroes the strategy's own daily returns on downtrend days; a real "
               "overlay would also change which trades were open, so it is a first look, not a result. If the "
               "filtered index matches the filtered strategy, the filter, not the strategy, carries the result. "
               "Cash earns 0% here, which flatters neither side.")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("--risk-pct", type=float, default=None, help="the strategy's risk per trade, %% of equity")
    ap.add_argument("--no-fills", action="store_true", help="skip the bar-range check (slow on many symbols)")
    a = ap.parse_args()
    rep = get(a.host, f"/api/reports/{a.run}")
    if (rep.get("stage") or "") == "verify":
        raise SystemExit("This is a verify-stage run: the review never reads one.")
    market, start, end = rep["market"], str(rep.get("window_start") or "1900-01-01"), str(rep.get("window_end") or "2100-01-01")
    tr, eq = table(a.host, a.run, "trades"), table(a.host, a.run, "equity")
    print(f"# Audit of run {a.run}: {rep.get('strategy')} {market}, stage {rep.get('stage') or 'legacy'}, {start} to {end}\n")
    for block in (accounting(tr, eq, start, end),
                  [] if tr is None or a.no_fills else fills(tr, market),
                  [] if tr is None else stops_and_sizing(tr, eq, a.risk_pct),
                  regimes(market, eq, tr, start, end)):
        if block:
            print("\n".join(block) + "\n")


if __name__ == "__main__":
    main()
