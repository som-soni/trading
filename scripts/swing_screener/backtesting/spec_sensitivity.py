"""Sensitivity of the Minervini spec backtest to its VCP and setup parameters (spec section 13, step 3).

Moves one parameter at a time to each end of the spec's test range (section 11) and runs the full
`--spec` portfolio backtest for both entry modes — EN-01 (confirmed breakout, next open) and EN-02
(buy-stop through the pivot) — reporting trades, expectancy, profit factor, CAGR and drawdown overall
and in / out of sample. "A real edge degrades gradually; an edge that disappears with a small change is
probably overfitted."

Why a separate runner: every parameter change re-detects every base, and the normal path rebuilds a
full StockContext (weekly / monthly frames, swing structure, overhead levels) per bar — about 40
minutes per variant for India. `minervini_spec` reads only the enriched daily frame (its Trend Template
gates are the Stage 2 criteria, which read only the daily row), so here each bar gets a daily-only
context; the data, the point-in-time candidate masks and the RS ratings are loaded once and shared, and
variants run in parallel processes. `--check` proves the shortcut reproduces the cached default run.

    PYTHONPATH=. python3 -m swing_screener.backtesting.spec_sensitivity --market india
    PYTHONPATH=. python3 -m swing_screener.backtesting.spec_sensitivity --market india --check
"""

import argparse
import dataclasses
import logging
import multiprocessing as mp
import time
from types import SimpleNamespace

import pandas as pd

from .. import paths
from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, db
from ..strategies import get_strategy
from ..strategies import minervini_spec as ms
from . import spec as spec_mod
from .backtest import _point_in_time_candidates
from .portfolio_sim import ExitPolicy, Signal, simulate

logger = logging.getLogger(__name__)
START = "2010-01-01"

# (label, kind, name, value): kind "vcp" = a VcpParams field, "const" = a minervini_spec module constant.
# The spec's test ranges (section 11), each end, one at a time.
VARIANTS = [
    ("default", None, None, None),
    ("swing_k 3", "vcp", "swing_k", 3), ("swing_k 7", "vcp", "swing_k", 7),
    ("min_swing 1%", "vcp", "min_swing_pct", 1.0), ("min_swing 4%", "vcp", "min_swing_pct", 4.0),
    ("prior_advance 25%", "vcp", "prior_advance_pct", 25.0), ("prior_advance 50%", "vcp", "prior_advance_pct", 50.0),
    ("first_depth 25%", "vcp", "max_first_depth_pct", 25.0), ("first_depth 50%", "vcp", "max_first_depth_pct", 50.0),
    ("shrink 0.6", "vcp", "shrink", 0.6), ("shrink 1.0 (just smaller)", "vcp", "shrink", 0.9999),
    ("tight_days 5", "vcp", "tight_days", 5), ("tight_days 15", "vcp", "tight_days", 15),
    ("tight_pct 6%", "vcp", "tight_pct", 6.0), ("tight_pct 12%", "vcp", "tight_pct", 12.0),
    ("pivot_near_high 0.85", "vcp", "pivot_near_high", 0.85), ("pivot_near_high 0.95", "vcp", "pivot_near_high", 0.95),
    ("dryup 0.5", "vcp", "dryup_ratio", 0.5), ("dryup 0.85", "vcp", "dryup_ratio", 0.85),
    ("vol_mult 1.0", "const", "VOL_MULT", 1.0), ("vol_mult 2.0", "const", "VOL_MULT", 2.0),
    ("buy_range 3%", "const", "BUY_RANGE_PCT", 3.0), ("buy_range 7%", "const", "BUY_RANGE_PCT", 7.0),
]
MODES = {"EN-01": "TRADE - HIGH CONFIDENCE", "EN-02": "TRADE ON TRIGGER"}

_DATA: dict = {}     # filled in the parent before forking: market, cfg, frames, masks, ratings, start
# the columns minervini_spec (its gates, the VCP detector) and the simulator read; the rest are dropped so a
# large market's frames fit in memory alongside the forked workers
COLUMNS = ["open", "high", "low", "close", "volume", "sma50", "sma150", "sma200", "sma200_21d_ago",
           "high_252", "low_252", "mom_12_1", "vol_sma50", "atr14"]


def _ratings(market: str, dates: list) -> dict:
    """RS ratings, computed in a short-lived child: the bulk price load behind them is several GB for
    the US, and memory a process has used is not handed back before the workers fork."""
    with mp.get_context("fork").Pool(1) as pool:
        return pool.apply(spec_mod.rs_ratings, (market, dates))


def load(market: str, start: str = START) -> None:
    t0 = time.time()
    cfg = MARKETS[market]
    strat = get_strategy("minervini")
    st = pd.Timestamp(start)
    syms = _point_in_time_candidates(cfg, strat, market, st)
    frames, masks = {}, {}
    for s in syms:
        raw = cache.load_cached(market, s)
        if raw is None or len(raw) < strat.min_bars:
            continue
        e = ind.enrich_daily(raw)
        m = strat.prefilter_mask(cfg, e)
        if not m[m.index >= st].any():
            continue
        frames[s], masks[s] = e[COLUMNS].copy(), m
    dates = sorted({d for s, m in masks.items() for d in m.index[m.values & (m.index >= st)]})
    logger.info("%s: %d candidates, %d screened-in dates; rating RS…", market, len(frames), len(dates))
    ratings = _ratings(market, dates)
    _DATA.update(market=market, cfg=cfg, frames=frames, masks=masks, ratings=ratings, start=st)
    logger.info("loaded in %.0fs", time.time() - t0)


_DEFAULTS = {"VCP": ms.VCP, **{k: getattr(ms, k) for _, kind, k, _ in VARIANTS if kind == "const"}}


def _apply(kind, name, value) -> None:
    """Set ONE parameter, starting from the defaults (a worker process runs several variants in turn)."""
    for k, v in _DEFAULTS.items():
        setattr(ms, k, v)
    if kind == "vcp":
        ms.VCP = dataclasses.replace(ms.VCP, **{name: value})
    elif kind == "const":
        setattr(ms, name, value)


def signals(kind=None, name=None, value=None) -> list:
    """Every order minervini_spec would place, for both entry modes, with one parameter changed."""
    _apply(kind, name, value)
    strat, cfg = get_strategy("minervini"), _DATA["cfg"]
    out = []
    for sym, e in _DATA["frames"].items():
        m = _DATA["masks"][sym]
        for i in [k for k, (d, ok) in enumerate(zip(m.index, m.values)) if ok and d >= _DATA["start"]]:
            if i + 1 < strat.min_bars:
                continue
            d = e.iloc[: i + 1]
            last = d.iloc[-1]
            ctx = SimpleNamespace(symbol=sym, daily=d, last=last, close=float(last["close"]), extras={},
                                  earnings_days_away=None, atr=float(last["atr14"]))
            r = strat.evaluate(ctx)
            if not r.hard_gates_passed or not r.has_setup or not strat.entry_signal_fired(ctx, r):
                continue
            plan = strat.build_plans(ctx, r, cfg).chosen
            if plan is None or not plan.is_valid:
                continue
            dec = strat.classify(ctx, r, plan, None, None, False)
            if dec.label_before not in MODES.values():
                continue
            out.append(Signal(date=d.index[-1], symbol=sym, setup=plan.setup, entry=plan.entry, stop=plan.stop,
                              target=plan.target, decision=dec.label_before, quality=dec.setup_quality,
                              meta=strat.signal_meta(ctx, r, plan)))
    return out


def _with_rs(sigs: list, min_rs: int = 70) -> list:
    out = []
    for s in sigs:
        r = _DATA["ratings"].get(pd.Timestamp(s.date))
        rs = None if r is None else r.get(s.symbol)
        if rs is not None and rs == rs and rs >= min_rs:
            out.append(dataclasses.replace(s, meta={**s.meta, "rs": int(rs)}))
    return out


def _cagr(eq: pd.Series):
    if len(eq) < 2 or eq.iloc[0] <= 0:
        return None
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    return ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100 if yrs > 0 else None


def backtest(sigs: list, mode: str) -> dict:
    """The `--spec` portfolio backtest of one entry mode."""
    market, cfg = _DATA["market"], _DATA["cfg"]
    sel = [s for s in sigs if s.decision == MODES[mode]]
    sel = spec_mod.rank_rs_then_tightness(spec_mod.annotate_costs(_with_rs(sel), _DATA["frames"], market))
    if not sel:
        return {"signals": 0, "trades": 0}
    prices = {s: _DATA["frames"][s] for s in {x.symbol for x in sel}}
    res = simulate(sel, prices, cfg, _DATA["start"], max_positions=ms.MAX_POSITIONS,
                   exit_policy=ExitPolicy(mode="minervini", use_target=False),
                   cost_bps=spec_mod.COST_BPS[market], slippage_bps=spec_mod.SLIPPAGE_BPS[market],
                   max_open_risk_pct=ms.MAX_OPEN_RISK_PCT / 100, max_adv_pct=ms.MAX_ADV_PCT / 100)
    eq = res.equity
    t = pd.DataFrame([{"entry": x.entry_date, "r": x.r_multiple, "pnl": x.pnl, "open": x.exit_reason == "OPEN"} for x in res.trades])
    out = {"signals": len(sel), "trades": len(t), "cagr": _cagr(eq),
           "max_dd": float((eq / eq.cummax() - 1).min() * 100)}
    closed = t[~t["open"]] if len(t) else t
    for tag, part in (("", closed), ("is_", closed[closed["entry"] <= spec_mod.IS_END] if len(closed) else closed),
                      ("oos_", closed[closed["entry"] > spec_mod.IS_END] if len(closed) else closed)):
        if len(part):
            gp, gl = part.loc[part.pnl > 0, "pnl"].sum(), -part.loc[part.pnl <= 0, "pnl"].sum()
            out.update({f"{tag}n": len(part), f"{tag}exp": float(part["r"].mean()),
                        f"{tag}pf": float(gp / gl) if gl > 0 else None, f"{tag}win": float((part["r"] > 0).mean() * 100)})
    out["is_cagr"] = _cagr(eq[eq.index <= spec_mod.IS_END])
    out["oos_cagr"] = _cagr(eq[eq.index > spec_mod.IS_END])
    return out


def _variant(v) -> tuple:
    label, kind, name, value = v
    t0 = time.time()
    sigs = signals(kind, name, value)
    res = {mode: backtest(sigs, mode) for mode in MODES}
    logger.info("%-26s %5d signals, EN-01 %s trades, EN-02 %s trades (%.0fs)", label, len(sigs),
                res["EN-01"].get("trades"), res["EN-02"].get("trades"), time.time() - t0)
    return label, res


def _f(v, d=2, pct=False):
    return "—" if v is None or v != v else f"{v:+.{d}f}{'%' if pct else ''}" if pct else f"{v:.{d}f}"


def report(market: str, results: list) -> str:
    L = [f"# Minervini spec — parameter sensitivity, {MARKETS[market].name}", "",
         f"*Generated {pd.Timestamp.today().date()} by `python -m swing_screener.backtesting.spec_sensitivity --market {market}`.* "
         f"Each row moves ONE parameter from the spec's default to one end of its test range (section 11); everything else is "
         f"the `--spec` backtest from {START}: RS rating ≥ 70, RS-then-tightness ranking, {ms.MAX_POSITIONS} positions, the spec's "
         f"exits and costs. In-sample is to {spec_mod.IS_END}, out-of-sample after. Expectancy is per trade in R; PF is profit factor.", ""]
    for mode in MODES:
        L += [f"## {mode} — {'confirmed breakout, next open' if mode == 'EN-01' else 'buy-stop through the pivot'}", "",
              "| Variant | Trades | Win % | Expectancy R | PF | CAGR | Max DD | IS trades | IS exp. R | IS CAGR | OOS trades | OOS exp. R | OOS CAGR |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
        for label, res in results:
            r = res[mode]
            L.append(f"| {label} | {r.get('trades', 0)} | {_f(r.get('win'), 0)} | {_f(r.get('exp'))} | {_f(r.get('pf'))} | "
                     f"{_f(r.get('cagr'), 2, True)} | {_f(r.get('max_dd'), 1)}% | {r.get('is_n', 0)} | {_f(r.get('is_exp'))} | "
                     f"{_f(r.get('is_cagr'), 2, True)} | {r.get('oos_n', 0)} | {_f(r.get('oos_exp'))} | {_f(r.get('oos_cagr'), 2, True)} |")
        L.append("")
    return "\n".join(L)


def check(market: str) -> None:
    """The daily-only shortcut must reproduce the cached default run's signals exactly."""
    sigs = signals()
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, setups FROM backtest_signals WHERE market=%s AND strategy='minervini'
                       AND hard_gates_passed AND date >= %s""", (market, START))
        rows = cur.fetchall()
    cached = {(s, pd.Timestamp(d)) for s, d, st in rows if st.get("MV-01") or st.get("MV-02")}
    mine = {(s.symbol, pd.Timestamp(s.date)) for s in sigs}
    print(f"shortcut: {len(mine)} orders; cached evaluations with a setup: {len(cached)}; "
          f"shortcut ⊆ cached: {mine <= cached}; cached-only {len(cached - mine)} (setups refused by the plan/classify step)")
    for mode in MODES:
        print(mode, backtest(sigs, mode))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--market", required=True, choices=list(MARKETS))
    ap.add_argument("--check", action="store_true", help="verify the shortcut against the cached default run")
    ap.add_argument("--workers", type=int, default=6)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    load(a.market)
    if a.check:
        check(a.market)
        return
    with mp.get_context("fork").Pool(a.workers, maxtasksperchild=1) as pool:
        results = pool.map(_variant, VARIANTS, chunksize=1)
    text = report(a.market, results)
    out = paths.RESEARCH_DIR / f"minervini-spec-sensitivity-{a.market}.md"
    out.write_text(text)
    print(text)
    print(f"\nWritten to {out}")


if __name__ == "__main__":
    main()
