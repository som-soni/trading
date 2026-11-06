"""Breakout anticipation: which conditions, visible before a breakout, raise the odds of a real one?

A re-runnable measurement behind research/breakout-anticipation-study.md and the Breakout watch screen
(screens/definitions.py `breakout_watch`). It reads stored data only: prices, the Sectors page's benchmark,
breadth, point-in-time group RS (analytics/group_history.py) and India's delivery data.

Definitions (fixed before the first run, 2026-11-06):

  * Breakout on day d -- the breakout strategy's S1 setup and its trend gates: close above the pivot (the
    highest high of the BREAKOUT_LOOKBACK sessions before d) on more than VOL_MULT x the 50-day volume; above
    a 200-day that is not falling; within 5% of the 52-week high; liquid (the market's dollar-volume floor).
  * Follow-through (a REAL breakout): within FT_BARS sessions a close FT_UP_ATR x ATR14 above the breakout
    close comes before a close FT_DN_ATR x ATR14 below the pivot. Anything else is a FAILED breakout.
  * Candidate (the unit of observation): the last session of each week where a liquid company (indices and
    ETFs have no industry and are left out) is above a non-falling 200-day, at most
    BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT% under its pivot (and not above it), within 10% of its 52-week high.
  * Outcome: the first breakout in the next HORIZON sessions -- TRUE (real), FAILED, or NONE (the near-miss,
    no breakout). Every signal reads bars up to the candidate's session only.

Windows: discovery = candidates from 2017-01-01 whose latest possible follow-through (40 sessions on) falls in
2021 -- the last five years of the optimise stage; hold-out = 2022 onward. The rule frozen on discovery is
FROZEN below; the hold-out was read once, after it was written (2026-11-06). `forward` scores the alerts the
breakout_watch job has logged since (screens/alerts.py) against every candidate on the same dates.

A signal's lift is P(TRUE | signal) / P(TRUE), with a 95% interval from a bootstrap over stocks (one stock's
weeks are not independent). CONFIRMED: lift >= MIN_LIFT, interval above 1, >= MIN_TRUE true breakouts
flagged; CONTRADICTED: interval below 1; UNSUPPORTED: the rest with >= MIN_TRUE; INSUFFICIENT: fewer.

Run from scripts/ (about 3 minutes for both markets):
    PYTHONPATH=. .venv/bin/python -m swing_screener.analytics.breakout_study --market us india
    ... --forward                       # score the logged Breakout watch alerts
Caveats: today's stock lists and classification (survivorship); one definition of breakout and
follow-through; 29 signals per market, so a false confirmation or two per window is expected by chance.
"""

from __future__ import annotations

import argparse
import json
import logging
import time

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import db, industries
from ..screens import criteria as crit
from ..screens import definitions as sdef
from ..screens.snapshot import LEAD_HIGH_BARS, PIVOT_BARS, _bench
from ..strategies.breakout import BREAKOUT_LOOKBACK, VOL_MULT

logger = logging.getLogger(__name__)

HIGH52_BO = 0.95          # the breakout strategy's G3: close within 5% of the 52-week high (a literal in its code)
HORIZON = 20              # sessions after a candidate in which its breakout must come
FT_BARS, FT_UP_ATR, FT_DN_ATR = 20, 2.0, 0.5
NEAR_PIVOT = 1 - sdef.BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT / 100
NEAR_HIGH = sdef.BREAKOUT_WATCH_MIN_FRAC_OF_52W_HIGH
SMA200_KEEP = 1 - crit.SMA200_FALLING_PCT / 100      # "not falling": >= this x its value SMA200_SLOPE_BARS ago
DISCOVERY = ("2017-01-01", "2021-12-31")
HOLDOUT_START = "2022-01-01"
LOAD_FROM = "2015-06-01"
B, MIN_TRUE, MIN_LIFT = 1000, 100, 1.10

# Frozen on the discovery window, before any hold-out row was read (2026-11-06). A: the greedy AND over the
# market's confirmed signals (stop when the lift gain < 0.05 or < MIN_TRUE flagged); B: one unified rule (the
# signals confirmed in both markets); C: >= 2 of the market's confirmed signals. The hold-out passed A and B in
# the US and failed every rule in India. US A is the Breakout watch screen.
FROZEN = {
    "us": {"A_greedy": ["R2_rs_new_high_first", "V4_obv_at_55d_high", "K4_group_rs_70"],
           "B_unified": ["R2_rs_new_high_first", "V4_obv_at_55d_high"],
           "C_score2_of": ["R2_rs_new_high_first", "V4_obv_at_55d_high", "K4_group_rs_70", "P7_within_2pct_of_pivot"]},
    "india": {"A_greedy": ["P9_strong_closes_5d"],
              "B_unified": ["R2_rs_new_high_first", "V4_obv_at_55d_high"],
              "C_score2_of": ["P9_strong_closes_5d", "R2_rs_new_high_first", "V4_obv_at_55d_high", "V1_volume_dryup"]},
}
PASS = ("hold-out lift >= 1.20 with the interval above 1, >= MIN_TRUE true breakouts flagged, and at least half "
        "the discovery excess lift kept")


def _q(sql, args=()):
    with db.get_connection().cursor() as c:
        c.execute(sql, args)
        return pd.DataFrame(c.fetchall(), columns=[d[0] for d in c.description])


def _load(market):
    cfg = MARKETS[market]
    floor = cfg.screener.min_dollar_volume
    syms = _q("SELECT DISTINCT symbol FROM prices WHERE market=%s AND date >= '2017-01-01' AND dollar_vol_sma20 >= %s",
              (market, floor))["symbol"].tolist()
    px = _q("""SELECT symbol, date, open, high, low, close, volume, sma50, sma200, atr14, vol_sma50, dollar_vol_sma20, high_252
               FROM prices WHERE market=%s AND date >= %s AND symbol = ANY(%s) ORDER BY symbol, date""", (market, LOAD_FROM, syms))
    for c in px.columns[2:]:
        px[c] = pd.to_numeric(px[c], errors="coerce").astype("float64")
    px["date"] = pd.to_datetime(px["date"])
    bench = _bench(market, LOAD_FROM)          # the Sectors page's benchmark, as the snapshot's RS line uses
    br = _q("SELECT date, n, above50 FROM breadth_daily WHERE market=%s ORDER BY date", (market,))
    br["date"] = pd.to_datetime(br["date"])
    br["breadth50"] = br["above50"].astype(float) / br["n"].astype(float)
    grs = _q("SELECT date, grp, rs FROM group_rs_history WHERE market=%s AND level='industry' AND date >= '2016-06-01'", (market,))
    grs["date"] = pd.to_datetime(grs["date"])
    deliv = None
    if market == "india":
        from ..marketdata import delivery
        if delivery.covers(cfg):
            deliv = _q("SELECT symbol, date, deliv_pct FROM delivery_daily WHERE market=%s AND date >= %s", (market, LOAD_FROM))
            deliv["date"] = pd.to_datetime(deliv["date"])
            deliv["deliv_pct"] = deliv["deliv_pct"].astype(float)
    return cfg, px, bench, br, grs, deliv


def _per_symbol(g, floor, bench_close, deliv_s):
    S = pd.Series
    o, h, l, c, v = (g[k].to_numpy() for k in ("open", "high", "low", "close", "volume"))
    sma50, sma200, atr, vs50, dv, h252 = (g[k].to_numpy() for k in ("sma50", "sma200", "atr14", "vol_sma50", "dollar_vol_sma20", "high_252"))
    n = len(c)
    pivot = ind.prior_high(g["high"], BREAKOUT_LOOKBACK).to_numpy()
    sma200_ago = S(sma200).shift(crit.SMA200_SLOPE_BARS).to_numpy()
    trend_ok = (c > sma200) & (sma200 >= SMA200_KEEP * sma200_ago)
    liquid = dv >= floor
    bo = (c > pivot) & (v > VOL_MULT * vs50) & trend_ok & (c >= HIGH52_BO * h252) & liquid

    real = np.zeros(n, dtype=bool)
    for d in np.flatnonzero(bo):
        seg = c[d + 1: d + 1 + FT_BARS]
        up = np.flatnonzero(seg >= c[d] + FT_UP_ATR * atr[d])
        dn = np.flatnonzero(seg < pivot[d] - FT_DN_ATR * atr[d])
        real[d] = up.size > 0 and (dn.size == 0 or up[0] < dn[0])

    pos = np.flatnonzero(bo)
    nxt = np.full(n, -1)
    if len(pos):
        j = np.searchsorted(pos, np.arange(n) + 1)
        ok = j < len(pos)
        cand_next = np.where(ok, pos[np.minimum(j, len(pos) - 1)], -1)
        within = ok & (cand_next - np.arange(n) <= HORIZON)
        nxt[within] = cand_next[within]

    # ---- signals at t (bars <= t)
    prev_c = S(c).shift(1).to_numpy()
    tr = np.maximum(h - l, np.maximum(np.abs(h - prev_c), np.abs(l - prev_c)))
    atr10, atr50 = S(tr).rolling(10).mean().to_numpy(), S(tr).rolling(50).mean().to_numpy()
    hi10, lo10 = S(h).rolling(10).max().to_numpy(), S(l).rolling(10).min().to_numpy()
    hi40, lo40 = S(h).rolling(40).max().to_numpy(), S(l).rolling(40).min().to_numpy()

    def depth(a, b):        # high-to-low depth over bars [t-a, t-b]
        H = S(h).shift(b).rolling(a - b + 1).max().to_numpy()
        L = S(l).shift(b).rolling(a - b + 1).min().to_numpy()
        return (H - L) / H
    d1, d2, d3 = depth(59, 30), depth(29, 10), depth(9, 0)
    lowA, lowB, lowC = (S(l).shift(k).rolling(10).min().to_numpy() for k in (0, 10, 20))
    hs = np.concatenate([[np.nan], h[:-1]])               # sessions since the pivot high was made
    since = np.full(n, np.nan)
    if n >= BREAKOUT_LOOKBACK + 1:
        w = np.lib.stride_tricks.sliding_window_view(np.nan_to_num(hs, nan=-np.inf), BREAKOUT_LOOKBACK)
        since[BREAKOUT_LOOKBACK - 1:] = BREAKOUT_LOOKBACK - (BREAKOUT_LOOKBACK - 1 - np.argmax(w[:, ::-1], axis=1))
    rng = h - l
    up, dn = c > prev_c, c < prev_c
    upv, dnv = S(np.where(up, v, 0.0)).rolling(50).sum().to_numpy(), S(np.where(dn, v, 0.0)).rolling(50).sum().to_numpy()
    ret = c / prev_c - 1
    clv = np.where(h > l, ((c - l) - (h - c)) / np.where(h > l, h - l, 1), 0.0)
    ad = np.cumsum(clv * v)
    c20 = c / S(c).shift(20).to_numpy() - 1
    rsl = S(c / bench_close)
    sma10, sma20, sma150 = (S(c).rolling(k).mean().to_numpy() for k in (10, 20, 150))
    f = {
        "P1_atr_contraction": atr10 / atr50 < 0.8,
        "P2_range_tightening": (hi10 - lo10) / (hi40 - lo40) < 0.4,
        "P3_vcp_contractions": (d1 > d2) & (d2 > d3),
        "P4_higher_lows": (lowA > lowB) & (lowB > lowC),
        "P5_base_5wk_plus": since >= 25,
        "P6_shallow_base": (pivot - S(l).rolling(BREAKOUT_LOOKBACK).min().to_numpy()) / pivot <= 0.15,
        "P7_within_2pct_of_pivot": c >= 0.98 * pivot,
        "P8_nr7_today": rng <= S(rng).rolling(7).min().to_numpy(),
        "P9_strong_closes_5d": S(clv).rolling(5).mean().to_numpy() > 0.3,
        "V1_volume_dryup": S(v).rolling(10).mean().to_numpy() / vs50 < 0.8,
        "V2_updown_volume": upv / np.where(dnv > 0, dnv, np.nan) > 1.2,
        "V3_spike_no_move_20d": S(((v > 2.5 * vs50) & (np.abs(ret) < 0.01)).astype(float)).rolling(20).max().to_numpy() > 0,
        "V4_obv_at_55d_high": ind.at_prior_high(ind.obv(g["close"], g["volume"]), LEAD_HIGH_BARS).to_numpy(),
        "V5_ad_up_price_flat": ((ad - S(ad).shift(20).to_numpy()) > 0) & (np.abs(c20) <= 0.03),
        "V6_accum_days_2plus": S(((v > 1.5 * vs50) & up).astype(float)).rolling(20).sum().to_numpy() >= 2,
        "R1_rs_line_rising_20d": (rsl / rsl.shift(20) - 1).to_numpy() > 0,
        "R2_rs_new_high_first": ind.at_prior_high(rsl, LEAD_HIGH_BARS).to_numpy(),
        "M1_ma_stack": (c > sma50) & (sma50 > sma150) & (sma150 > sma200),
        "M2_ma_compression": (np.maximum.reduce([sma10, sma20, sma50]) - np.minimum.reduce([sma10, sma20, sma50])) / c < 0.03,
        "M3_sma50_rising": sma50 > S(sma50).shift(10).to_numpy(),
        "M4_above_10_and_20": (c > sma10) & (c > sma20),
    }
    cand = liquid & trend_ok & (c < pivot) & (c >= NEAR_PIVOT * pivot) & (c >= NEAR_HIGH * h252)
    out = pd.DataFrame({"date": g["date"].to_numpy(), "cand": cand, "since": since, "i": np.arange(n),
                        "ret126": c / S(c).shift(126).to_numpy() - 1})
    out["label"] = np.where(nxt < 0, "NONE", np.where(real[np.maximum(nxt, 0)], "TRUE", "FAILED"))
    for k, a in f.items():
        out[k] = np.asarray(a, dtype=bool)
    if deliv_s is not None:
        dps = S(deliv_s.reindex(g["date"]).to_numpy())
        d10, d50 = dps.rolling(10, min_periods=8).mean().to_numpy(), dps.rolling(50, min_periods=40).mean().to_numpy()
        hd = dps.to_numpy() >= 1.5 * dps.shift(1).rolling(20, min_periods=15).mean().to_numpy()
        out["D1_delivery_rising"] = np.nan_to_num(d10 / d50 >= 1.1, nan=0).astype(bool)
        out["D2_high_delivery_day_20d"] = S(hd.astype(float)).rolling(20).max().to_numpy() > 0
        out["has_deliv"] = ~np.isnan(d50)
    dates = g["date"].to_numpy()
    t40 = dates[np.minimum(out["i"].to_numpy() + 40, n - 1)].copy()
    t40[out["i"].to_numpy() + 40 >= n] = np.datetime64("NaT")
    out["t40"] = t40
    return out, pd.DataFrame({"date": dates[bo], "real": real[bo]})


def build(market: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(candidate weeks with every signal and their outcome, every breakout event with its follow-through)."""
    t0 = time.time()
    cfg, px, bench, br, grs, deliv = _load(market)
    floor = cfg.screener.min_dollar_volume
    ind_ = industries.load(market)       # companies only: indices and ETFs have no industry
    dgroups = dict(tuple(deliv.groupby("symbol"))) if deliv is not None else {}
    cands, everyday, events = [], [], []
    for sym, g in px.groupby("symbol", sort=False):
        if len(g) < 300 or not (ind_.get(sym) and ind_[sym][1]):
            continue
        g = g.reset_index(drop=True)
        bc = bench.reindex(g["date"], method="ffill").to_numpy()
        ds = (dgroups[sym].set_index("date")["deliv_pct"] if sym in dgroups else pd.Series(dtype=float)) if deliv is not None else None
        out, ev = _per_symbol(g, floor, bc, ds)
        wk = g["date"].dt.isocalendar()
        key = wk["year"].astype(int) * 100 + wk["week"].astype(int)
        last = key.ne(key.shift(-1)).to_numpy()            # the week's last stored session
        out["sym"] = sym
        cands.append(out[last & out["cand"].to_numpy()])
        everyday.append(pd.DataFrame({"date": out["date"], "sym": sym, "ret126": out["ret126"],
                                      "liq": (g["dollar_vol_sma20"] >= floor).to_numpy()}))
        events.append(ev)
    c = pd.concat(cands, ignore_index=True)
    allr = pd.concat(everyday, ignore_index=True)
    allr = allr[allr["liq"] & allr["ret126"].notna()]
    allr["pct"] = allr.groupby("date")["ret126"].rank(pct=True)
    c = c.merge(allr[["date", "sym", "pct"]], on=["date", "sym"], how="left")
    c["R3_rs_rank_80"] = c["pct"] >= 0.80
    i50, i200 = bench.rolling(50).mean(), bench.rolling(200).mean()
    ctx = pd.DataFrame({"K1_index_above_50_200": (bench > i50) & (bench > i200), "K2_index_50d_rising": i50 > i50.shift(10),
                        "K5_index_near_high": bench >= 0.95 * bench.rolling(252).max()})
    ctx = ctx.reindex(pd.DatetimeIndex(sorted(c["date"].unique())), method="ffill")
    c = c.merge(ctx, left_on="date", right_index=True, how="left")
    c["K3_breadth_60"] = c["date"].map(br.set_index("date")["breadth50"]).fillna(0) >= 0.60
    c["grp"] = c["sym"].map(lambda s: ind_[s][1])
    c = c.merge(grs.rename(columns={"rs": "grp_rs"}).astype({"grp_rs": float}), on=["date", "grp"], how="left")
    c["K4_group_rs_70"] = c["grp_rs"] >= sdef.BREAKOUT_WATCH_MIN_GROUP_RS
    for k in ("K1_index_above_50_200", "K2_index_50d_rising", "K5_index_near_high"):
        c[k] = c[k].fillna(False).astype(bool)
    logger.info("%s: %d candidate weeks from %d stocks (%.0fs)", market, len(c), c["sym"].nunique(), time.time() - t0)
    return c, pd.concat(events, ignore_index=True)


# ------------------------------------------------------------------ judging

def signals(c: pd.DataFrame) -> list[str]:
    return [x for x in c.columns if len(x) > 3 and x[0] in "PVRMKD" and x[1].isdigit() and x[2] == "_"]


def discovery(c):
    return c[(c.date >= DISCOVERY[0]) & (c.t40 <= DISCOVERY[1])]


def holdout(c):
    return c[(c.date >= HOLDOUT_START) & c.t40.notna()]


def boot_lift(c, mask, rng) -> tuple[float, float]:
    codes, uq = pd.factorize(c.sym)
    W = rng.poisson(1.0, size=(B, len(uq))).astype(float)
    t = c.label.eq("TRUE").to_numpy().astype(float)
    m = np.asarray(mask, dtype=float)
    agg = lambda a: np.bincount(codes, weights=a, minlength=len(uq))
    n, tt, ns, ts = agg(np.ones_like(t)), agg(t), agg(m), agg(m * t)
    with np.errstate(divide="ignore", invalid="ignore"):
        L = (W @ ts / (W @ ns)) / (W @ tt / (W @ n))
    lo, hi = np.nanpercentile(L, [2.5, 97.5])
    return float(lo), float(hi)


def judge(c, name, mask, rng) -> dict:
    mask = np.asarray(mask, dtype=bool)
    T, F, N0 = (c.label.eq(x).to_numpy() for x in ("TRUE", "FAILED", "NONE"))
    p, ns, ts = T.mean(), mask.sum(), (mask & T).sum()
    lift = (ts / ns) / p if ns else float("nan")
    lo, hi = boot_lift(c, mask, rng) if ns else (float("nan"), float("nan"))
    bo = T | F
    verdict = ("INSUFFICIENT" if ts < MIN_TRUE else "CONFIRMED" if lift >= MIN_LIFT and lo > 1
               else "CONTRADICTED" if hi < 1 else "UNSUPPORTED")
    return dict(signal=name, flagged=int(ns), true_flagged=int(ts), precision=ts / ns if ns else None, recall=ts / T.sum(),
                lift=lift, lo=lo, hi=hi, in_true=ts / T.sum(), in_failed=(mask & F).sum() / F.sum(),
                in_none=(mask & N0).sum() / N0.sum(),
                bo_lift=((bo & mask).sum() / ns) / bo.mean() if ns else None,
                ft_lift=(ts / (bo & mask).sum()) / (T.sum() / bo.sum()) if (bo & mask).sum() else None, verdict=verdict)


def rule_mask(c, name, sigs):
    if name.startswith("C_"):
        return sum(c[s].to_numpy().astype(int) for s in sigs) >= 2
    return np.logical_and.reduce([c[s].to_numpy().astype(bool) for s in sigs])


def table(c, rng) -> pd.DataFrame:
    rows = []
    for s in signals(c):
        cc = c[c["has_deliv"].astype(bool)] if s.startswith("D") else c   # delivery signals: where delivery is stored
        rows.append(judge(cc, s, cc[s], rng))
    return pd.DataFrame(rows).sort_values("lift", ascending=False)


def greedy(c, confirmed, rng) -> list[dict]:
    """The pre-stated combination search: AND in the confirmed signal that lifts most, while the lift gains
    >= 0.05 and >= MIN_TRUE true breakouts stay flagged."""
    T, base = c.label.eq("TRUE").to_numpy(), c.label.eq("TRUE").mean()
    chosen, steps, cur = [], [], 1.0
    while True:
        best = None
        for s in confirmed:
            if s in chosen:
                continue
            mk = rule_mask(c, "A", chosen + [s])
            ts = (mk & T).sum()
            if ts >= MIN_TRUE and (best is None or (ts / mk.sum()) / base > best[1]):
                best = (s, (ts / mk.sum()) / base)
        if best is None or best[1] - cur < 0.05:
            return steps
        chosen.append(best[0]); cur = best[1]
        steps.append({"rules": list(chosen), **judge(c, "+".join(chosen), rule_mask(c, "A", chosen), rng)})


def forward(market: str, c: pd.DataFrame, rng) -> dict:
    """The Breakout watch alerts logged since the screen went live, against every candidate on the same weeks."""
    from ..screens import alerts
    a = alerts.load(market, "breakout_watch")
    if a.empty:
        return {"alerts": 0, "note": "no alerts logged yet"}
    f = c[(c.date >= a.date.min()) & c.t40.notna()].copy()
    flagged = f.set_index(["date", "sym"]).index.isin(a.set_index(["date", "symbol"]).index)
    if not f.label.eq("TRUE").any():
        return {"alerts": int(len(a)), "scored_weeks": len(f), "note": "no outcome is complete yet"}
    return {"alerts": int(len(a)), "since": str(a.date.min().date()), **judge(f, "breakout_watch (forward)", flagged, rng)}


def run(market: str, do_forward: bool = False) -> dict:
    rng = np.random.default_rng(7)
    c, ev = build(market)
    d, h = discovery(c), holdout(c)
    head = lambda x: dict(candidates=len(x), stocks=int(x.sym.nunique()), **x.label.value_counts().to_dict(),
                          base=float(x.label.eq("TRUE").mean()))
    out = {"market": market, "discovery": head(d), "holdout": head(h),
           "events": {k: dict(breakouts=len(e), real_share=float(e.real.mean())) for k, e in
                      (("discovery", ev[(ev.date >= DISCOVERY[0]) & (ev.date <= "2021-11-30")]), ("holdout", ev[ev.date >= HOLDOUT_START]))}}
    td = table(d, rng)
    out["signals"] = td.to_dict("records")
    out["greedy"] = greedy(d, td[td.verdict == "CONFIRMED"].signal.tolist(), rng)
    out["frozen"] = {k: {"rule": sigs, "discovery": judge(d, k, rule_mask(d, k, sigs), rng),
                         "holdout": judge(h, k, rule_mask(h, k, sigs), rng)} for k, sigs in FROZEN[market].items()}
    out["signals_holdout"] = table(h, rng).to_dict("records")
    if do_forward:
        out["forward"] = forward(market, c, rng)
    return out


def _print(r: dict) -> None:
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    f3 = lambda x: f"{x:.3f}"
    print(f"\n===== {r['market']}  discovery {r['discovery']}\n      hold-out {r['holdout']}\n      events {r['events']}")
    cols = ["signal", "flagged", "true_flagged", "precision", "lift", "lo", "hi", "bo_lift", "ft_lift", "verdict"]
    print("-- discovery signals\n" + pd.DataFrame(r["signals"])[cols].to_string(index=False, float_format=f3))
    print("-- greedy\n" + (pd.DataFrame(r["greedy"])[["signal", "flagged", "true_flagged", "precision", "recall", "lift", "lo", "hi"]]
                           .to_string(index=False, float_format=f3) if r["greedy"] else "none"))
    fz = pd.DataFrame([{"rule": k, "disc_lift": v["discovery"]["lift"], **{x: v["holdout"][x] for x in
                        ("flagged", "true_flagged", "precision", "recall", "lift", "lo", "hi")}} for k, v in r["frozen"].items()])
    print("-- frozen rules on the hold-out\n" + fz.to_string(index=False, float_format=f3))
    print("-- hold-out signals\n" + pd.DataFrame(r["signals_holdout"])[cols].to_string(index=False, float_format=f3))
    if "forward" in r:
        print("-- forward", r["forward"])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", nargs="+", default=list(MARKETS), choices=list(MARKETS))
    ap.add_argument("--forward", action="store_true", help="also score the logged Breakout watch alerts")
    ap.add_argument("--json", help="write the results to this file")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    res = [run(m, a.forward) for m in a.market]
    for r in res:
        _print(r)
    if a.json:
        json.dump(res, open(a.json, "w"), default=float, indent=1)


if __name__ == "__main__":
    main()
