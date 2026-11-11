"""Batch review of a Minervini backtest run's trades: the checks from the chart reviews, applied to every trade.

`research/minervini-trade-reviews.md` collects lessons (L1..) and fixes (F1..) from trades reviewed one at a time on
the chart. This applies the same checks to EVERY trade of one run, winners and losers alike -- a sign is a lesson
only if losers carry it more often than winners -- and stores one row per trade in `trade_reviews` (metrics + flags),
then prints a summary: per flag, trades, win rate and average R against the trades without it.

Reads stored data only (prices, the run's cached signals, results announcements). It describes a finished run; it
never changes a rule. Figures from an optimise run are in-sample: they rank lessons to test, they do not test them.

    PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.trade_review --run 4089 [--write-summary]
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, db, financials

log = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]

BUY_STOP = {"S2", "S8", "S10"}          # filled intraday by a resting order; the rest fill the open after the signal
FLAT_PIVOT = {"S6", "S8"}               # pivot = the flat base's high (`flat_base`), the F2 case
CHEAT = {"S3", "S4"}
BLACKOUT_DAYS = 14                      # the run's `--results-blackout` (rb14)
RESTING_DAYS = 10                       # portfolio_sim PENDING_EXPIRY_BDAYS
REENTRY_LOOKAHEAD = 60                  # sessions after a losing exit in which a reclaim counts (L1)
REENTRY_RUN_PCT = 20.0                  # ... and the gain after it that makes it a missed winner

# The flag thresholds: the buckets each lesson's test will use, written before reading any result here.
L2_EXT_PCT = 25.0                       # base high this far above its 50-day
L2_SPIKE_10D_PCT = 30.0                 # or this gain over the 10 sessions into the base high
L3_VOL = 1.4                            # cross / fill session volume under this x its 50-day (VOL_MULT)
L4_NEAR_PCT = 3.0                       # buy within this % above the 50-day
F2_STALE_PCT = 0.5                      # a high inside the base this far above the pivot

SCHEMA = """
CREATE TABLE IF NOT EXISTS trade_reviews (
    run_id INTEGER NOT NULL,
    market VARCHAR(16) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    entry_date DATE NOT NULL,
    setup VARCHAR(8) NOT NULL,
    r_multiple DOUBLE PRECISION,
    exit_reason VARCHAR(32),
    flags TEXT[] NOT NULL,
    metrics JSONB NOT NULL,
    reviewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, symbol, entry_date, setup)
);
"""


def _run(run_id: int) -> dict:
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT market, strategy, run_name, spec_id, stage FROM report_runs WHERE id=%s", (run_id,))
        row = cur.fetchone()
    if not row:
        raise SystemExit(f"no report run {run_id}")
    market, strategy, name, spec_id, stage = row
    path = ROOT / "reports" / market / strategy / name / "trades.csv"
    return {"market": market, "strategy": strategy, "name": name, "spec_id": spec_id, "stage": stage, "trades": path}


def _order_placed(spec_id: str, market: str, sym: str, setup: str, fill: pd.Timestamp, idx: pd.DatetimeIndex):
    """The session a buy-stop was first placed: the start of the unbroken run of `setup` signals ending the session
    before the fill, at most RESTING_DAYS back (the cached signals of the run's own spec id)."""
    k = int(idx.searchsorted(fill))
    lo = idx[max(0, k - RESTING_DAYS - 1)]
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, setups FROM backtest_signals WHERE spec_id=%s AND market=%s AND symbol=%s "
                    "AND date >= %s AND date < %s AND has_setup", (spec_id, market, sym, lo.date(), fill.date()))
        on = {pd.Timestamp(d) for d, s in cur.fetchall() if s and s.get(setup)}
    first = None
    for j in range(k - 1, max(-1, k - RESTING_DAYS - 2), -1):
        if idx[j] in on:
            first = idx[j]
        elif first is not None:
            break
    return first


def review_trade(t: pd.Series, d: pd.DataFrame, ann: list, bench: pd.DataFrame, run: dict, later: list) -> dict:
    idx = d.index
    e = pd.Timestamp(t.entry_date)
    k = int(idx.searchsorted(e))
    if k >= len(idx) or idx[k] != e:
        return {"error": "entry not in stored prices"}
    setup, pivot, entry = t.setup, float(t.pivot), float(t.entry_price)
    sig = (_order_placed(run["spec_id"], run["market"], t.symbol, setup, e, idx) if setup in BUY_STOP else None) \
        or idx[k - 1]
    s = int(idx.get_loc(sig))
    cross = k if setup in BUY_STOP else s          # the session that went through the pivot
    hi, lo, cl, vo = (d[c].to_numpy(float) for c in ("high", "low", "close", "volume"))
    s50, v50 = d["sma50"].to_numpy(float), d["vol_sma50"].to_numpy(float)
    m: dict = {"signal": str(sig.date()), "risk_pct": round((entry - float(t.initial_stop)) / entry * 100, 2)}

    # the base: from its start (base_id) to the signal; its high and where that high stood
    b0 = int(idx.searchsorted(pd.Timestamp(t.base_id))) if isinstance(t.base_id, str) else None
    if b0 is not None and b0 < s:
        hb = b0 + int(np.argmax(hi[b0:s + 1]))
        m["base_high"] = round(hi[hb], 2)
        m["base_high_vs_sma50"] = round((hi[hb] / s50[hb] - 1) * 100, 1)                  # L2
        m["gain_63d_into_high"] = round((hi[hb] / lo[max(0, hb - 63):hb + 1].min() - 1) * 100, 1)
        m["gain_10d_into_high"] = round((hi[hb] / lo[max(0, hb - 10):hb + 1].min() - 1) * 100, 1)
        # F2: a high inside the base above the pivot, before the signal (the flat base's stale pivot)
        top = hi[b0:s].max() if s > b0 else hi[b0]
        m["base_max_vs_pivot"] = round((top / pivot - 1) * 100, 2)
        m["closes_above_pivot_before"] = int((cl[b0:s] > pivot).sum())
    # L3: the crossing session's volume and how far its close cleared the pivot
    m["cross_vol"] = round(vo[cross] / v50[cross], 2) if v50[cross] > 0 else None
    m["cross_clear_pct"] = round((cl[cross] / pivot - 1) * 100, 2)
    # L4: the buy against the 50-day at the signal
    m["buy_vs_sma50"] = round((entry / s50[s] - 1) * 100, 2)
    m["sma50_slope10_pct"] = round((s50[s] / s50[max(0, s - 10)] - 1) * 100, 2)
    m["closes_below_sma50_20"] = int((cl[max(0, s - 19):s + 1] < s50[max(0, s - 19):s + 1]).sum())
    # after the fill: day one, follow-through
    m["day1_close_vs_pivot"] = round((cl[k] / pivot - 1) * 100, 2)
    risk = entry - float(t.initial_stop)
    m["mfe10_r"] = round((hi[k:k + 10].max() - entry) / risk, 2) if risk > 0 else None
    m["vol_after_2_10"] = round(float(np.nanmean(vo[k + 1:k + 10] / v50[k + 1:k + 10])), 2) if k + 2 < len(idx) else None
    # F1 / F3: results announcements around the signal and the fill
    ad = sorted(pd.Timestamp(a).normalize() for a in ann)
    m["results_signal_to_fill"] = [str(a.date()) for a in ad if sig <= a <= e]               # F1
    m["results_within_14d_of_fill"] = [str(a.date()) for a in ad if e < a <= e + pd.Timedelta(days=BLACKOUT_DAYS)]  # F3
    # the market: the benchmark's next 10 sessions and its place against its 50-day
    if bench is not None and e in bench.index:
        bi = int(bench.index.get_loc(e))
        bc = bench["close"].to_numpy(float)
        m["bench_vs_sma50"] = round((bc[bi] / bench["sma50"].iloc[bi] - 1) * 100, 2)
        m["bench_ret10"] = round((bc[min(bi + 10, len(bc) - 1)] / bc[bi] - 1) * 100, 2)
    # L1: a losing trade whose base was reclaimed later, with the move the run did not take
    x = int(idx.searchsorted(pd.Timestamp(t.exit_date))) if isinstance(t.exit_date, str) else None
    if t.r_multiple < 0 and x is not None and x < len(idx) - 1:
        ceiling = max(pivot, hi[k:x + 1].max())
        end = min(len(idx), x + 1 + REENTRY_LOOKAHEAD)
        ups = np.flatnonzero(cl[x + 1:end] > ceiling)
        if len(ups):
            j = x + 1 + int(ups[0])
            run_to = cl[j:min(len(idx), j + 120)].max()
            gain = (run_to / cl[j] - 1) * 100
            retaken = any(e < pd.Timestamp(l) <= idx[min(len(idx) - 1, j + 5)] for l in later)
            m["reclaim"] = {"date": str(idx[j].date()), "ceiling": round(ceiling, 2), "gain_after_pct": round(gain, 1),
                            "sessions_after_exit": int(j - x), "retaken": retaken}
    return m


def _clean(v):
    """NaN (a missing average early in a stock's history) as None, so the row stores as JSON."""
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, (float, np.floating)) and v != v:
        return None
    return v.item() if isinstance(v, np.generic) else v


def flags_of(m: dict, setup: str) -> list[str]:
    m = {k: (0 if v is None and k in ("base_high_vs_sma50", "gain_10d_into_high", "base_max_vs_pivot") else v)
         for k, v in m.items()}
    f = []
    if m.get("base_high_vs_sma50", 0) >= L2_EXT_PCT or m.get("gain_10d_into_high", 0) >= L2_SPIKE_10D_PCT:
        f.append("L2")
    if m.get("cross_vol") is not None and m["cross_vol"] < L3_VOL:
        f.append("L3")
    if m.get("buy_vs_sma50") is not None and m["buy_vs_sma50"] < L4_NEAR_PCT:
        f.append("L4")
    if setup in FLAT_PIVOT and m.get("base_max_vs_pivot", 0) > F2_STALE_PCT:
        f.append("F2")
    if m.get("results_signal_to_fill"):
        f.append("F1")
    if m.get("results_within_14d_of_fill"):
        f.append("F3")
    if m.get("day1_close_vs_pivot") is not None and m["day1_close_vs_pivot"] < 0:
        f.append("day1_back_under")
    if m.get("bench_ret10") is not None and m["bench_ret10"] <= -3:
        f.append("market_drop")
    rc = m.get("reclaim")
    if rc and not rc["retaken"] and rc["gain_after_pct"] >= REENTRY_RUN_PCT:
        f.append("L1")
    if setup in CHEAT:
        f.append("cheat")
    return f


def review_run(run_id: int) -> pd.DataFrame:
    run = _run(run_id)
    trades = pd.read_csv(run["trades"])
    market = run["market"]
    ann = financials.announcements(market, first_per_quarter=True)
    braw = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    bench = ind.enrich_daily(braw) if braw is not None else None
    if bench is not None and "sma50" not in bench:
        bench["sma50"] = bench["close"].rolling(50).mean()
    rows = []
    for sym, g in trades.groupby("symbol"):
        raw = cache.load_cached(market, sym)
        if raw is None:
            continue
        d = ind.enrich_daily(raw)
        entries = list(g.entry_date)
        for _, t in g.iterrows():
            m = _clean(review_trade(t, d, ann.get(sym, []), bench, run, [x for x in entries if x > t.entry_date]))
            rows.append({"symbol": sym, "entry_date": t.entry_date, "setup": t.setup, "r": float(t.r_multiple),
                         "exit_reason": t.exit_reason, "flags": flags_of(m, t.setup), "metrics": m})
    df = pd.DataFrame(rows)
    with db.get_connection() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA)
        cur.execute("DELETE FROM trade_reviews WHERE run_id=%s", (run_id,))
        for r in rows:
            cur.execute("INSERT INTO trade_reviews (run_id, market, symbol, entry_date, setup, r_multiple, exit_reason, "
                        "flags, metrics) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                        (run_id, market, r["symbol"], r["entry_date"], r["setup"], r["r"], r["exit_reason"],
                         r["flags"], json.dumps(r["metrics"], default=str)))
    return df


def summary(df: pd.DataFrame) -> str:
    """Per flag: trades, win rate, average R, total R -- against the trades without it."""
    out = ["| Flag | Trades | Win % | Avg R | Total R | Without: trades | Win % | Avg R |", "|---|---|---|---|---|---|---|---|"]
    names = ["L1", "L2", "L3", "L4", "F1", "F2", "F3", "day1_back_under", "market_drop", "cheat"]
    for f in names:
        on = df[df["flags"].apply(lambda x: f in x)]
        off = df[df["flags"].apply(lambda x: f not in x)]
        if not len(on):
            out.append(f"| {f} | 0 | | | | {len(off)} | | |")
            continue
        out.append(f"| {f} | {len(on)} | {(on.r > 0).mean() * 100:.0f} | {on.r.mean():+.2f} | {on.r.sum():+.1f} | "
                   f"{len(off)} | {(off.r > 0).mean() * 100:.0f} | {off.r.mean():+.2f} |")
    out.append(f"| all | {len(df)} | {(df.r > 0).mean() * 100:.0f} | {df.r.mean():+.2f} | {df.r.sum():+.1f} | | | |")
    return "\n".join(out)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--run", type=int, required=True, help="report_runs.id")
    a = ap.parse_args(argv)
    df = review_run(a.run)
    print(summary(df))


if __name__ == "__main__":
    main()
