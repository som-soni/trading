"""Is one stored backtest's result robust? Outliers, stability over time, and how much luck it could be.

Reads the run's report tables through the web app's API and the benchmark's stored prices, never past
the run's window. Prints markdown, then a flags table. A flag names a weakness in the RESULT; whether
it matters is the review's call (a trend system is outlier-driven by design -- the question is whether
the outliers are many and spread out, or a handful).

    cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/robustness.py \
        --run 1730 [--host http://127.0.0.1:8000] [--reps 1000]

The benchmark here is the market's benchmark price series (no dividends), so yearly excess figures are
slightly kinder to the strategy than a total-return comparison; say so when quoting them.
"""

import argparse
import json
import math
import urllib.request

import numpy as np
import pandas as pd

from swing_screener.config import MARKETS
from swing_screener.marketdata import cache

SEED = 20261114
BLOCK_DAYS = 20               # stationary bootstrap: mean block length, keeps volatility clusters together
ROLL_SHORT, ROLL_LONG = 252, 756   # rolling one-year and three-year windows, in sessions
# flag thresholds -- fixed before looking at any run
OUTLIER_SHARE = 0.05          # "the best 5% of trades"
OUTLIER_LEFT_MIN = 0.25       # without them, less than this share of the P&L left = "partly" outlier-driven
ROLL_POSITIVE_MIN = 0.60      # fewer rolling one-year windows than this beating the benchmark = unstable
BOOT_PROB_MIN = 0.80          # bootstrap chance of positive excess below this = could be luck
BEST_YEAR_SHARE_MAX = 0.50    # one year earning more than this share of all the gain = one-year result
SYMBOL_SHARE_MAX = 0.30       # the best three stocks earning more than this share of the P&L
SYMBOLS_MIN = 20              # the stock-concentration flag applies only to a book that traded this many


def get(host, path):
    with urllib.request.urlopen(host.rstrip("/") + path, timeout=120) as r:
        return json.load(r)


def table(host, rid, name):
    try:
        t = get(host, f"/api/reports/{rid}/tables/{name}")
    except Exception:
        return None
    return pd.DataFrame(t["rows"], columns=t["columns"]) if t.get("rows") else None


def cagr(eq: pd.Series) -> float:
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100 if yrs > 0 and eq.iloc[-1] > 0 else float("nan")


def max_dd(eq: pd.Series) -> float:
    return ((eq / eq.cummax()) - 1).min() * 100


def stationary_bootstrap(n: int, rng, block: int) -> np.ndarray:
    """Indices of one stationary-bootstrap path (Politis & Romano): blocks of geometric length."""
    idx = np.empty(n, dtype=int)
    i = rng.integers(n)
    for k in range(n):
        idx[k] = i
        i = rng.integers(n) if rng.random() < 1 / block else (i + 1) % n
    return idx


def outliers(tr: pd.DataFrame, eq: pd.Series) -> tuple[list[str], dict]:
    out, fl = ["## Outliers: does the result rest on a few trades?"], {}
    if tr is None or "pnl" not in tr:
        return out + ["No trades table."], fl
    t = tr.sort_values("pnl", ascending=False).reset_index(drop=True)
    start, total = eq.iloc[0], t.pnl.sum()
    out.append(f"{len(t)} trades; total P&L {total:,.0f}; median trade "
               + (f"{t.r_multiple.median():+.2f}R; " if "r_multiple" in t else "")
               + f"CAGR {cagr(eq):.2f}%.")
    out.append("")
    out.append("| Without | Their P&L | Share of total | P&L left | CAGR left |")
    out.append("|---|---|---|---|---|")
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    for k in sorted({1, 3, 5, 10, max(1, int(round(len(t) * OUTLIER_SHARE))), max(1, int(round(len(t) * 0.10)))}):
        if k >= len(t):
            continue
        top = t.pnl.head(k).sum()
        left_end = eq.iloc[-1] - top
        c = ((left_end / start) ** (1 / yrs) - 1) * 100 if left_end > 0 else float("nan")
        label = f"best {k}" + (f" ({k / len(t) * 100:.0f}%)" if k > 10 else "")
        cs = f"{c:.2f}%" if not math.isnan(c) else "wiped out"
        out.append(f"| {label} | {top:,.0f} | {top / total * 100:.0f}% | {total - top:,.0f} | {cs} |")
        if k == max(1, int(round(len(t) * OUTLIER_SHARE))):
            left = total - top
            level = ("**yes**, nothing left" if left <= 0 else
                     "partly" if left < OUTLIER_LEFT_MIN * total else "no")
            fl["outliers"] = (level, f"without its best {k} trades ({OUTLIER_SHARE:.0%}) the P&L is {left:,.0f} "
                                     f"({left / total * 100:.0f}% of it), CAGR {cs}")
    if "r_multiple" in t:
        r = t.r_multiple.sort_values()
        lo, hi = int(len(r) * 0.05), int(len(r) * 0.95)
        out.append("")
        out.append(f"- Expectancy {r.mean():+.2f}R; trimmed of the best and worst 5% {r.iloc[lo:hi].mean():+.2f}R; "
                   f"without the best 5% only {r.iloc[:hi].mean():+.2f}R.")
    if "symbol" in t:
        by = t.groupby("symbol").pnl.sum().sort_values(ascending=False)
        s3 = by.head(3).sum() / total if total > 0 else float("nan")
        out.append(f"- Best three stocks: {', '.join(by.head(3).index)} = {s3 * 100:.0f}% of the P&L "
                   f"({len(by)} stocks traded).")
        if len(by) >= SYMBOLS_MIN:
            fl["symbols"] = (total > 0 and s3 > SYMBOL_SHARE_MAX, f"the best three stocks made {s3 * 100:.0f}% of the P&L")
        else:
            fl["symbols"] = ("n/a", f"only {len(by)} instruments traded: concentration is the design, not a flag")
    return out, fl


def over_time(eq: pd.Series, bench: pd.Series | None) -> tuple[list[str], dict]:
    out, fl = ["## Over time: steady, or a few good stretches?"], {}
    s = eq.resample("YE").last()
    yr = s.pct_change()
    yr.iloc[0] = s.iloc[0] / eq.iloc[0] - 1
    b = None
    if bench is not None:
        bs = bench.resample("YE").last()
        b = bs.pct_change()
        b.iloc[0] = bs.iloc[0] / bench.iloc[0] - 1
    out.append("| Year | Strategy | Benchmark | Excess |")
    out.append("|---|---|---|---|")
    for d, v in yr.items():
        bv = b.get(d) if b is not None else None
        out.append(f"| {d.year} | {v * 100:+.1f}% | " + (f"{bv * 100:+.1f}% | {(v - bv) * 100:+.1f} pts |" if bv is not None
                                                           else "n/a | n/a |"))
    gains = (s.diff().fillna(s.iloc[0] - eq.iloc[0]))
    total_gain = eq.iloc[-1] - eq.iloc[0]
    if total_gain > 0:
        best = gains.max() / total_gain
        out.append(f"- Best year ({gains.idxmax().year}) earned {best * 100:.0f}% of the whole gain; "
                   f"{(yr > 0).sum()} of {len(yr)} years positive"
                   + (f", {(yr > b).sum()} beat the benchmark." if b is not None else "."))
        fl["one_year"] = (best > BEST_YEAR_SHARE_MAX, f"the best year earned {best * 100:.0f}% of the whole gain")
    else:
        out.append(f"- No net gain; {(yr > 0).sum()} of {len(yr)} years positive.")
    # halves
    mid = eq.index[len(eq) // 2]
    h1, h2 = eq[eq.index <= mid], eq[eq.index >= mid]
    line = f"- First half {cagr(h1):.2f}% a year, second half {cagr(h2):.2f}%"
    if bench is not None:
        bh1, bh2 = bench[bench.index <= mid], bench[bench.index >= mid]
        e1, e2 = cagr(h1) - cagr(bh1), cagr(h2) - cagr(bh2)
        line += f" (excess {e1:+.2f} and {e2:+.2f} pts)"
        fl["halves"] = (np.sign(e1) != np.sign(e2), f"excess {e1:+.1f} pts in the first half, {e2:+.1f} in the second")
    out.append(line + f"; split at {mid.date()}.")
    # rolling windows
    if bench is not None:
        for w, name in ((ROLL_SHORT, "one-year"), (ROLL_LONG, "three-year")):
            if len(eq) <= w:
                continue
            ex = (eq.pct_change(w) - bench.pct_change(w)).dropna() * 100
            pos = (ex > 0).mean()
            out.append(f"- Rolling {name} excess: positive in {pos * 100:.0f}% of windows; "
                       f"worst {ex.min():+.1f} pts, median {ex.median():+.1f}, best {ex.max():+.1f}.")
            if w == ROLL_SHORT:
                fl["rolling"] = (pos < ROLL_POSITIVE_MIN, f"beat the benchmark in {pos * 100:.0f}% of rolling one-year windows")
    # drawdown shape
    dd = eq / eq.cummax() - 1
    under = dd < 0
    runs = (under != under.shift()).cumsum()
    longest = under.groupby(runs).sum().max()
    out.append(f"- Max drawdown {dd.min() * 100:.1f}%; longest stretch below a previous high {longest} sessions "
               f"({longest / 252:.1f} years); under water {under.mean() * 100:.0f}% of the time.")
    return out, fl


def luck(eq: pd.Series, bench: pd.Series | None, reps: int) -> tuple[list[str], dict]:
    out, fl = ["## Luck: how different could the same strategy have looked?"], {}
    r = eq.pct_change().dropna()
    br = bench.pct_change().reindex(r.index).fillna(0) if bench is not None else pd.Series(0.0, index=r.index)
    rng = np.random.default_rng(SEED)
    n, cg, ex, dds = len(r), [], [], []
    rv, bv = r.values, br.values
    for _ in range(reps):
        i = stationary_bootstrap(n, rng, BLOCK_DAYS)
        path = np.cumprod(1 + rv[i])
        bpath = np.cumprod(1 + bv[i])
        yrs = n / 252
        c = (path[-1] ** (1 / yrs) - 1) * 100
        cg.append(c)
        ex.append(c - (bpath[-1] ** (1 / yrs) - 1) * 100)
        dds.append((path / np.maximum.accumulate(path) - 1).min() * 100)
    cg, ex, dds = np.array(cg), np.array(ex), np.array(dds)
    p = (ex > 0).mean()
    out.append(f"Stationary block bootstrap of the daily returns, strategy and benchmark resampled together "
               f"(mean block {BLOCK_DAYS} sessions, {reps} paths, seed {SEED}).")
    out.append("")
    out.append("| | 5th pct | Median | 95th pct | As run |")
    out.append("|---|---|---|---|---|")
    out.append(f"| CAGR | {np.percentile(cg, 5):.2f}% | {np.median(cg):.2f}% | {np.percentile(cg, 95):.2f}% | {cagr(eq):.2f}% |")
    if bench is not None:
        out.append(f"| Excess over benchmark | {np.percentile(ex, 5):+.2f} | {np.median(ex):+.2f} | "
                   f"{np.percentile(ex, 95):+.2f} | {cagr(eq) - cagr(bench):+.2f} |")
    out.append(f"| Max drawdown | {np.percentile(dds, 5):.1f}% | {np.median(dds):.1f}% | {np.percentile(dds, 95):.1f}% | "
               f"{max_dd(eq):.1f}% |")
    out.append("")
    out.append(f"- Chance the excess is positive: {p * 100:.0f}%. A drawdown as deep as the 5th-percentile path is a "
               "realistic planning figure, not a worst case.")
    if bench is not None:
        fl["luck"] = (p < BOOT_PROB_MIN, f"{p * 100:.0f}% of resampled paths beat the benchmark")
    return out, fl


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    ap.add_argument("--reps", type=int, default=1000)
    a = ap.parse_args()
    rep = get(a.host, f"/api/reports/{a.run}")
    if (rep.get("stage") or "") == "verify":
        raise SystemExit("This is a verify-stage run: the review never reads one.")
    market, end = rep["market"], pd.Timestamp(str(rep.get("window_end") or "2100-01-01"))
    eqt = table(a.host, a.run, "equity")
    if eqt is None:
        raise SystemExit("No equity table: robustness needs the daily equity.")
    eq = eqt.set_index(pd.to_datetime(eqt["date"]))["equity"].astype(float)
    eq = eq[eq.index <= end]
    tr = table(a.host, a.run, "trades")
    px = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    bench = None
    if px is not None:
        bench = px["close"].astype(float).reindex(eq.index).ffill()
        bench = bench if bench.notna().all() else None
    print(f"# Robustness of run {a.run}: {rep.get('strategy')} {market}, stage {rep.get('stage') or 'legacy'}, "
          f"{eq.index[0].date()} to {eq.index[-1].date()}\n")
    flags = {}
    for fn in (lambda: outliers(tr, eq), lambda: over_time(eq, bench), lambda: luck(eq, bench, a.reps)):
        lines, fl = fn()
        flags.update(fl)
        print("\n".join(lines) + "\n")
    print("## Flags (thresholds fixed in the script, before any run)\n")
    print("| Check | Flag | Finding |")
    print("|---|---|---|")
    names = {"outliers": f"Rests on the best {OUTLIER_SHARE:.0%} of trades", "symbols": "Rests on three stocks",
             "one_year": "Rests on one year", "halves": "The two halves disagree",
             "rolling": "Unstable year to year", "luck": "Could be luck"}
    for k, label in names.items():
        if k in flags:
            bad, why = flags[k]
            mark = bad if isinstance(bad, str) else ("**yes**" if bad else "no")
            print(f"| {label} | {mark} | {why} |")


if __name__ == "__main__":
    main()
