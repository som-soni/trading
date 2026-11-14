"""One strategy among all of them: luck across every strategy tried, and what it adds to the book.

1. Trials across strategies. The deflated Sharpe within one strategy counts its own variants; the best
   of thirty strategies beating buy-and-hold is a second selection. This deflates the run's Sharpe for
   every optimise and legacy backtest stored in the market.
2. Book contribution. The daily returns of every other strategy's own baseline (current version,
   optimise stage, no overrides) in the same market: correlation with this run, and the equal-weight
   book of the others with and without it.

    cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/cross_strategy.py \
        --run 1730 [--host http://127.0.0.1:8000]
"""

import argparse
import json
import math
import urllib.request
from statistics import NormalDist

import numpy as np
import pandas as pd

from swing_screener.marketdata import db

N = NormalDist()
GAMMA = 0.5772156649          # Euler-Mascheroni, in the expected maximum of N Sharpe ratios


def get(host, path):
    with urllib.request.urlopen(host.rstrip("/") + path, timeout=120) as r:
        return json.load(r)


def equity(host, rid, end) -> pd.Series | None:
    try:
        t = get(host, f"/api/reports/{rid}/tables/equity")
    except Exception:
        return None
    if not t.get("rows"):
        return None
    e = pd.DataFrame(t["rows"], columns=t["columns"])
    dcol = next((c for c in e.columns if "date" in c.lower()), e.columns[0])
    vcol = next((c for c in e.columns if c.lower() in ("equity", "value", "nav", "portfolio")), None)
    if vcol is None:
        return None          # a runner whose equity table has no value column: skipped, not guessed
    try:
        s = e.set_index(pd.to_datetime(e[dcol]))[vcol].astype(float)
    except (ValueError, TypeError):
        return None
    return s[s.index <= end]


def sr_daily(r: pd.Series) -> float:
    return r.mean() / r.std() if r.std() > 0 else float("nan")


def book(rets: pd.DataFrame) -> tuple[float, float, float]:
    r = rets.mean(axis=1)
    eq = (1 + r).cumprod()
    yrs = (r.index[-1] - r.index[0]).days / 365.25
    return (eq.iloc[-1] ** (1 / yrs) - 1) * 100, sr_daily(r) * math.sqrt(252), ((eq / eq.cummax()) - 1).min() * 100


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=int, required=True)
    ap.add_argument("--host", default="http://127.0.0.1:8000")
    a = ap.parse_args()
    rep = get(a.host, f"/api/reports/{a.run}")
    if (rep.get("stage") or "") == "verify":
        raise SystemExit("This is a verify-stage run: the review never reads one.")
    market, key = rep["market"], rep["strategy"]
    end = pd.Timestamp(str(rep.get("window_end") or "2100-01-01"))
    eq = equity(a.host, a.run, end)
    r = eq.pct_change().dropna()
    print(f"# Across strategies: run {a.run}, {key} {market}, stage {rep.get('stage') or 'legacy'}\n")

    # ---- 1. trials across every strategy ----
    cur = db.get_connection().cursor()
    cur.execute("SELECT strategy, summary->>'sharpe' FROM report_runs WHERE kind='backtest' AND market=%s "
                "AND coalesce(stage, 'legacy') IN ('optimise', 'legacy')", (market,))
    rows = [(s, float(x)) for s, x in cur.fetchall() if x not in (None, "", "n/a")]
    srs = np.array([x for _, x in rows])
    n_all, n_strat = len(srs), len({s for s, _ in rows})
    own = np.array([x for s, x in rows if s == key])
    T = len(r)
    sr = sr_daily(r)
    z = (r - r.mean()) / r.std()
    g3, g4 = (z ** 3).mean(), (z ** 4).mean()
    den = math.sqrt(max(1 - g3 * sr + (g4 - 1) / 4 * sr ** 2, 1e-12))

    def dsr(n, v):
        if n < 2:
            return float("nan"), float("nan")
        sr0 = math.sqrt(v) * ((1 - GAMMA) * N.inv_cdf(1 - 1 / n) + GAMMA * N.inv_cdf(1 - 1 / (n * math.e)))
        return sr0 * math.sqrt(252), N.cdf((sr - sr0) * math.sqrt(T - 1) / den)

    print("## 1. Luck across every strategy tried\n")
    print(f"{n_all} optimise and legacy backtests of {n_strat} strategies in {market}; this run's Sharpe "
          f"{sr * math.sqrt(252):.2f} (daily, annualised).\n")
    print("| Trials counted | n | Sharpe the best null trial would reach | Deflated Sharpe (P that the true Sharpe > 0) |")
    print("|---|---|---|---|")
    for name, arr in ((f"{key} only", own), ("every strategy in the market", srs)):
        s0, p = dsr(len(arr), (arr / math.sqrt(252)).var(ddof=1) if len(arr) > 1 else float("nan"))
        print(f"| {name} | {len(arr)} | {s0:.2f} | {p:.2f} |")
    print("\nThe second row is the honest one when this strategy was picked because it looked best among many. "
          "Trials are runs, and a variant re-run after a bug fix is still a trial.\n")

    # ---- 2. book contribution ----
    print("## 2. What it adds to the book\n")
    others = {}
    for s in get(a.host, "/api/strategies"):
        k = s["key"]
        if k == key:
            continue
        try:
            d = get(a.host, f"/api/strategies/{k}")
        except Exception:
            continue
        base = [b for b in d.get("backtests", []) if b["market"] == market and b["stage"] == "optimise"
                and not b.get("archived") and not b.get("overrides") and str(b.get("version")) == str(d.get("version"))]
        if not base:
            continue
        e = equity(a.host, max(base, key=lambda b: b["id"])["id"], end)
        if e is not None and len(e) > 252:
            others[k] = e.pct_change()
    if not others:
        print("No other strategy has a current-version optimise baseline in this market.")
        return
    rets = pd.DataFrame(others).reindex(r.index).fillna(0)
    corr = rets.corrwith(r).sort_values(ascending=False)
    print(f"Baselines found for {len(others)} other strategies (current version, optimise, no overrides). "
          "Daily-return correlation with this run:\n")
    print("| Strategy | Correlation |")
    print("|---|---|")
    for k, c in corr.items():
        print(f"| {k} | {c:+.2f} |")
    without = book(rets)
    with_ = book(pd.concat([rets, r.rename(key)], axis=1))
    print("\n| Equal-weight book, daily rebalanced | CAGR | Sharpe | Max DD |")
    print("|---|---|---|---|")
    print(f"| The other {len(others)} strategies | {without[0]:.2f}% | {without[1]:.2f} | {without[2]:.1f}% |")
    print(f"| … plus {key} | {with_[0]:.2f}% | {with_[1]:.2f} | {with_[2]:.1f}% |")
    print(f"\nMean correlation with the others {corr.mean():+.2f}. A strategy that trails buy-and-hold alone can still "
          "earn its place if it lifts the book's Sharpe or cuts its drawdown; one that does neither has no role. "
          "Equal weight and daily rebalancing are a yardstick, not a proposed allocation.")


if __name__ == "__main__":
    main()
