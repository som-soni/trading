"""Shorting Stage 4 stocks -- the first SHORT book on this shelf, judged as a hedge.

Every other strategy here is long-only, so in a bad year they all fall together. A short sleeve is
the one idea in the Learn module that should pay when everything else loses, so the question this
module answers is not "does it make money on its own" but "does adding it to the long momentum book
lower that book's drawdown, and at what cost in the years it does not pay". Both answers are
reported by the same run: the standalone result, and a month-end blend with the stored
`momentum_baseline` run of the same market and stage at a few sleeve weights.

WHY ITS OWN RUNNER. The per-symbol engine (`backtest.py`, `portfolio_sim.py`) is long-only in every
layer -- the plan geometry (stop below entry), the stop and gap fills, the exit modes, R, the sizing
and the open-risk cap -- and it is being edited by other work. Teaching it a direction would touch
all of those at once. A short book needs only a handful of rules, so it is simulated here, the way
`pead` and `mean_reversion` simulate theirs, and nothing the long strategies run on moves.

ONE STAGE MODEL. "Stage 4" is `stage_analysis.stage_series` -- the weekly state machine on the
30-week simple average that the Stage analysis strategy, its chart indicator and its market gate
all read. It is not re-derived from a daily 150-day rule (the guide's testable shorthand), because
two stage classifiers would disagree on exactly the borderline stocks a short book trades. A
week's stage is known at that week's last close and holds until the next week's.

THE COSTS ARE THE RESULT. A short pays what a long does not: a borrow fee (US) or a monthly
futures roll (India), and the dividends paid while short -- stored prices are split-adjusted but
not dividend-adjusted, so a short would otherwise pocket every ex-dividend drop. No interest is
credited on short proceeds or collateral. Each run is repeated at COST_LEVELS of those costs and all
three are reported, so the sign of the result can be read against its assumptions.
"""
from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..core import indicators as ind
from ..marketdata import cache, universe
from ..strategies.base import PortfolioStrategy
from ..strategies.stage_analysis import MA_WEEKS, ma30, stage_series
from . import metrics

logger = logging.getLogger("backtest")

MIN_BARS = 300

# ---- the setup (guide §3): Stage 4 from the stage model, plus weak relative strength
RS_BARS = 63                  # the stock has done worse than its index over this many sessions
LIQ_BARS = 50                 # median traded value over this many sessions >= the market's floor
#: India only: overnight shorts need stock futures, and the futures list is NOT stored
#: (`derivatives_bhav` holds index contracts only). The proxy is the stocks ranked in the top
#: FNO_PROXY_TOP by 50-day median traded value on the signal date -- NSE's list ran at roughly
#: 150-220 names over 2013-2021, chosen mostly on size and liquidity.
FNO_PROXY_TOP = 200

# ---- the entries (guide §3 Entry). 1 = on. Numbers, not bools, so a variant gets its own spec id.
ENTRY_FAILED_RALLY = 1        # B: a rally to the falling line that closes back below it
ENTRY_BREAKDOWN = 0           # A: a close at a new 52-week closing low on volume
STAGE4_MIN_SESSIONS = 40      # B: sessions already in Stage 4 before the rally counts
TOUCH_PCT = 1.0               # B: the day's high within this % of the line, or above it
RALLY_BARS = 10               # B's stop: above the highest high of this many sessions (the rally)
BREAKDOWN_BARS = 250          # A: below the lowest close of this many prior sessions
BREAKDOWN_VOL_MULT = 1.5      # A: volume at least this multiple of its 50-session average
BREAKDOWN_STOP_BARS = 10      # A's stop: the lower of this many sessions' high and the line
STOP_ATR_BUFFER = 0.25        # stop buffer, in ATR(14)
ATR_BARS = 14
MAX_STOP_PCT = 15.0           # skip a short whose stop is further than this above the entry

# ---- the market filter (guide §3): shorts only while the index is weak. 1 = on.
MARKET_FILTER = 1
INDEX_SMA = 200
INDEX_SLOPE_BARS = 20         # "falling": lower than this many sessions ago

# ---- the exits (guide §3 Exits)
TRAIL_START = 20              # from this session the stop trails ...
TRAIL_BARS = 20               # ... down to the highest high of this many sessions
TREND_SMA = 50                # cover on a close above this average, once the price was below it
TIME_STOP = 60                # cover after this many sessions if the trade never reached 1R

# ---- size (guide §3 Position size)
RISK_PCT = 0.5                # of equity per short
MAX_OPEN_RISK_PCT = 3.0       # open risk on all shorts together
MAX_GROSS_PCT = 100.0         # short notional on all positions together: no leverage
#: One short's notional. Not in the guide, which sizes from the stop alone -- but a stop a fraction of
#: a percent above the open then sizes one short at most of the account, and that is the position a
#: squeeze takes the whole book with.
MAX_POSITION_PCT = 20.0

# ---- costs: conservative and explicit. See the caveats; COST_LEVELS scales all but dividends.
US_COST_BPS = 10.0            # per side: spread and slippage on a liquid stock
US_BORROW_PCT = 1.0           # a year, of the short notional: general-collateral large caps run under 1%
US_DIVIDEND_PCT = 2.0         # a year, paid while short; the S&P 500 yielded about 1.8-2.2% in 2013-21
INDIA_COST_BPS = 15.0         # per side on a stock future: spread, slippage, STT, fees
INDIA_ROLL_BPS = 15.0         # per monthly roll: two more legs' spread plus STT on the new sale
INDIA_DIVIDEND_PCT = 1.5      # a year: a future prices dividends out, so a short does not gain them
COST_LEVELS = (0.5, 1.0, 2.0)  # the sensitivity: low, the base case, stress
SESSIONS_PER_MONTH = 21

# ---- the sleeve test: the long book it is judged beside, and the weights tried
LONG_BOOK = "momentum_baseline"
SLEEVE_WEIGHTS = (0, 20, 30)  # percent of the account in the short sleeve, rebalanced each month-end
CRASH_YEARS = (2015, 2016, 2018, 2020)


def short_costs(market: str, level: float = 1.0) -> dict:
    """{cost_bps per side, carry % a year} for shorting in `market`, at a multiple of the base case.

    Refuses a market with no stated assumption: a short's result is mostly its cost of carry, so a
    new market must say what borrowing (or its substitute) costs there before it can be run.
    """
    if market == "us":
        return {"cost_bps": US_COST_BPS * level,
                "carry_pct": US_BORROW_PCT * level + US_DIVIDEND_PCT, "futures_only": False}
    if market == "india":
        return {"cost_bps": INDIA_COST_BPS * level,
                "carry_pct": INDIA_ROLL_BPS * level * 12 / 100 + INDIA_DIVIDEND_PCT, "futures_only": True}
    raise SystemExit(f"{market}: no shorting-cost assumption is stated for this market (stage4_shorts.short_costs)")


def _weekly_on_daily(df: pd.DataFrame, weekly_vals: pd.Series) -> pd.Series:
    """A weekly series placed on the LAST session of each week, NaN elsewhere -- the same mapping as
    `portfolio_sim.weekly_line`, so a week's stage is read only once its week is over. The final stored
    bar counts as a week's last only on a Friday."""
    out = pd.Series(np.nan, index=df.index)
    week = pd.Series(df.index.to_period("W-FRI"), index=df.index)
    last = week != week.shift(-1)
    last.iloc[-1] = df.index[-1].weekday() == 4
    ends = week[last].map(lambda p: p.end_time.normalize())
    out[last] = weekly_vals.reindex(ends.values).values
    return out


def symbol_frame(df: pd.DataFrame, bench_close: pd.Series) -> pd.DataFrame:
    """Everything the entries and exits read, per daily bar, causal.

    `stage` and `line` are the last COMPLETED week's (forward-filled from week-ends); `wk_line` is
    set only on a week's last session, where the stage exit reads it.
    """
    df = df[["open", "high", "low", "close", "volume"]].astype(float)
    weekly = ind.resample_weekly(df)
    stage_w = stage_series(weekly).astype(float)
    line_w = ma30(weekly)
    out = pd.DataFrame(index=df.index)
    for c in ("open", "high", "low", "close"):
        out[c] = df[c]
    out["wk_line"] = _weekly_on_daily(df, line_w)
    out["line"] = out["wk_line"].ffill()
    out["stage"] = _weekly_on_daily(df, stage_w).ffill().fillna(0)
    s4 = (out["stage"] == 4).astype(int)
    out["stage4_run"] = s4.groupby((s4 == 0).cumsum()).cumsum()
    out["sma50"] = df["close"].rolling(TREND_SMA).mean()
    out["atr"] = ind.atr(df, ATR_BARS)
    out["turnover"] = (df["close"] * df["volume"]).rolling(LIQ_BARS, min_periods=LIQ_BARS).median()
    b = bench_close.reindex(df.index).ffill()
    out["rs_excess"] = (df["close"] / df["close"].shift(RS_BARS) - b / b.shift(RS_BARS)) * 100
    # entry B: a rally into the falling line that closes back below it
    rally_b = ((out["stage4_run"].shift(1) >= STAGE4_MIN_SESSIONS) & (out["stage"] == 4)
               & (df["high"] >= out["line"] * (1 - TOUCH_PCT / 100)) & (df["close"] < out["line"]))
    out["stop_b"] = df["high"].rolling(RALLY_BARS).max() + STOP_ATR_BUFFER * out["atr"]
    out["sig_b"] = rally_b
    # entry A: a new 52-week closing low on volume, in Stage 4
    low_prior = df["close"].shift(1).rolling(BREAKDOWN_BARS, min_periods=BREAKDOWN_BARS).min()
    vol_avg = df["volume"].shift(1).rolling(50, min_periods=50).mean()
    out["sig_a"] = ((out["stage"] == 4) & (df["close"] < low_prior)
                    & (df["volume"] >= BREAKDOWN_VOL_MULT * vol_avg))
    out["stop_a"] = (np.minimum(df["high"].rolling(BREAKDOWN_STOP_BARS).max(), out["line"])
                     + STOP_ATR_BUFFER * out["atr"])
    return out


def market_weak(bench_close: pd.Series) -> pd.Series:
    """The guide's filter: the index below its 200-day, or its 200-day lower than 20 sessions ago."""
    sma = bench_close.rolling(INDEX_SMA, min_periods=INDEX_SMA).mean()
    return (bench_close < sma) | (sma < sma.shift(INDEX_SLOPE_BARS))


def prepare(market: str) -> dict:
    """Load the universe once and turn it into per-symbol frames plus a candidate list.

    Returned as a dict so `main` can run several cost levels and entry variants off ONE load.
    """
    cfg = MARKETS[market]
    braw = cache.load_cached(market, cfg.benchmark_ticker)
    if braw is None:
        raise SystemExit(f"{market}: no stored benchmark {cfg.benchmark_ticker}")
    bench = braw["close"].astype(float)
    skip = universe.non_stock_symbols(market)
    tickers = [t for t in universe.load_universe(market) if t not in skip and t != cfg.benchmark_ticker]
    frames, turnover = {}, {}
    for i in range(0, len(tickers), 400):
        for sym, d in cache.load_many_cached(market, tickers[i:i + 400]).items():
            if d is None or len(d) < MIN_BARS:
                continue
            try:
                f = symbol_frame(d, bench)
            except Exception as e:   # noqa: BLE001 -- one malformed history must not end the run
                logger.warning("%s: skipped (%s)", sym, e)
                continue
            if not (f["sig_a"].any() or f["sig_b"].any()):
                continue
            frames[sym] = f
            turnover[sym] = f["turnover"]
        logger.info("%s: %d/%d symbols read, %d with a Stage 4 signal", market, min(i + 400, len(tickers)),
                    len(tickers), len(frames))
    fno_rank = None
    if short_costs(market)["futures_only"] and turnover:
        # ranked among the symbols with a signal ever; a stock that never signals cannot displace one
        # that does, so the rank is a lower bound on the true rank and the proxy is slightly generous.
        # Ranking the full tape would need every frame in memory; see the caveats.
        fno_rank = pd.DataFrame(turnover).rank(axis=1, ascending=False)
    return {"market": market, "bench": bench, "frames": frames, "fno_rank": fno_rank,
            "weak": market_weak(bench), "n_universe": len(tickers)}


def candidates(prep: dict, entries: str, use_filter: bool, start: pd.Timestamp) -> dict:
    """{signal date: [candidate, ...]}, weakest relative strength first."""
    cfg = MARKETS[prep["market"]]
    floor = cfg.screener.min_dollar_volume or 0
    weak = prep["weak"]
    out: dict = {}
    dropped = {"liquidity": 0, "fno": 0, "rs": 0, "stop": 0, "market": 0}
    for sym, f in prep["frames"].items():
        for kind in entries:
            col = "sig_b" if kind == "B" else "sig_a"
            stop_col = "stop_b" if kind == "B" else "stop_a"
            hits = f.index[f[col].values & (f.index >= start)]
            for d in hits:
                r = f.loc[d]
                if not (r["turnover"] >= floor):
                    dropped["liquidity"] += 1
                    continue
                if prep["fno_rank"] is not None:
                    rk = prep["fno_rank"].at[d, sym] if d in prep["fno_rank"].index else float("nan")
                    if not (rk <= FNO_PROXY_TOP):
                        dropped["fno"] += 1
                        continue
                if not (r["rs_excess"] < 0):
                    dropped["rs"] += 1
                    continue
                stop, close = float(r[stop_col]), float(r["close"])
                if not (stop > close and (stop / close - 1) * 100 <= MAX_STOP_PCT):
                    dropped["stop"] += 1
                    continue
                if use_filter and not bool(weak.asof(d)):
                    dropped["market"] += 1
                    continue
                out.setdefault(d, []).append({"symbol": sym, "entry": kind, "stop": stop,
                                              "signal_close": close, "rs_excess": float(r["rs_excess"]),
                                              "atr": float(r["atr"])})
    for d in out:
        out[d].sort(key=lambda c: c["rs_excess"])
    return out, dropped


def run(prep: dict, start: str, entries: str = "B", use_filter: bool = True, cost_level: float = 1.0,
        cands: tuple | None = None):
    """Simulate the short book. Returns (trades, equity, positions, gross exposure %, costs, dropped)."""
    market = prep["market"]
    cfg = MARKETS[market]
    sc = short_costs(market, cost_level)
    side = sc["cost_bps"] / 10_000
    carry_day = sc["carry_pct"] / 100 / 252
    start_ts = pd.Timestamp(start)
    sig, dropped = cands if cands is not None else candidates(prep, entries, use_filter, start_ts)
    frames = prep["frames"]
    cal = prep["bench"].index[prep["bench"].index >= start_ts]
    cash = float(cfg.account_size)
    open_pos: dict = {}
    pending: list = []
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs_total = 0.0
    skipped = {"gap_past_stop": 0, "risk_budget": 0, "no_open": 0}

    def bar(sym, d):
        f = frames[sym]
        return f.loc[d] if d in f.index else None

    def cover(sym, p, d, price, reason):
        nonlocal cash, costs_total
        fee = p["shares"] * price * side
        cash -= p["shares"] * price + fee
        costs_total += fee
        pnl = p["proceeds"] - p["shares"] * price - fee - p["fee"] - p["carry"]
        risk = p["shares"] * p["risk_ps"]
        trades.append({
            "symbol": sym, "direction": "short", "setup": p["entry"], "entry_date": p["date"],
            "entry_price": round(p["price"], 4), "initial_stop": round(p["stop0"], 4),
            "exit_date": d, "exit_price": round(price, 4), "shares": round(p["shares"], 4),
            "exit_reason": reason, "pnl": round(pnl, 2), "notional": round(p["proceeds"], 2),
            "costs": round(fee + p["fee"], 2), "carry": round(p["carry"], 2),
            "holding_days": (d - p["date"]).days, "sessions": p["n"],
            "r_multiple": round(pnl / risk, 4) if risk > 0 else float("nan"),
            "mfe_r": round(p["mfe"] / p["risk_ps"], 3) if p["risk_ps"] > 0 else float("nan"),
        })
        del open_pos[sym]

    last_close: dict = {}
    for d in cal:
        # ---- equity at the previous close, which sizes today's entries
        liab = sum(p["shares"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        equity = cash - liab
        # ---- entries at today's open, from yesterday's signals
        for c in pending:
            s = c["symbol"]
            if s in open_pos:
                continue
            b = bar(s, d)
            if b is None or not (b["open"] > 0):
                skipped["no_open"] += 1
                continue
            o, stop = float(b["open"]), c["stop"]
            # the open must still be below the structure the stop sits above (the stop less its ATR
            # buffer): an open past it means the rally has already resumed, and the risk to the stop is a
            # sliver -- v1.0 took those and booked R multiples in the thousands on them
            if o >= stop - STOP_ATR_BUFFER * c["atr"] or (stop / o - 1) * 100 > MAX_STOP_PCT:
                skipped["gap_past_stop"] += 1
                continue
            open_risk = sum(p["shares"] * max(p["stop"] - last_close.get(x, p["price"]), 0)
                            for x, p in open_pos.items())
            budget = min(equity * RISK_PCT / 100, equity * MAX_OPEN_RISK_PCT / 100 - open_risk)
            gross = sum(p["shares"] * last_close.get(x, p["price"]) for x, p in open_pos.items())
            shares = min(budget / (stop - o), (equity * MAX_GROSS_PCT / 100 - gross) / o,
                         equity * MAX_POSITION_PCT / 100 / o) if budget > 0 else 0
            if shares * o < equity * RISK_PCT / 100 * 0.25:   # too small to be worth a slot
                skipped["risk_budget"] += 1
                continue
            fee = shares * o * side
            cash += shares * o - fee
            costs_total += fee
            open_pos[s] = {"shares": shares, "price": o, "proceeds": shares * o, "fee": fee, "date": d,
                           "stop": stop, "stop0": stop, "risk_ps": stop - o, "entry": c["entry"], "n": 0,
                           "carry": 0.0, "mfe": 0.0, "was_below50": False, "trailed": False}
        pending = []
        # ---- the day's exits, intraday stop first, then the close rules
        for s in list(open_pos):
            p = open_pos[s]
            b = bar(s, d)
            if b is None:
                continue
            p["n"] += 1
            hi, lo, cl, op = float(b["high"]), float(b["low"]), float(b["close"]), float(b["open"])
            if hi >= p["stop"]:
                # a gap up through the buy-stop fills at the open, not at the stop
                fill = p["stop"] if p["n"] == 1 else max(p["stop"], op)
                cover(s, p, d, fill, "TRAIL" if p["trailed"] else "STOP")
                continue
            p["mfe"] = max(p["mfe"], p["price"] - lo)
            ch = p["shares"] * cl * carry_day
            cash -= ch
            p["carry"] += ch
            costs_total += ch
            reason = None
            sma50 = b["sma50"]
            if p["was_below50"] and sma50 == sma50 and cl > sma50:
                reason = "TREND"
            elif b["wk_line"] == b["wk_line"] and cl > b["wk_line"]:
                reason = "STAGE"
            elif p["n"] >= TIME_STOP and p["mfe"] < p["risk_ps"]:
                reason = "TIME"
            if reason:
                cover(s, p, d, cl, reason)
                continue
            if sma50 == sma50 and cl < sma50:
                p["was_below50"] = True
            if p["n"] >= TRAIL_START:
                f = frames[s]
                k = f.index.get_loc(d)
                trail = float(f["high"].iloc[max(0, k - TRAIL_BARS + 1):k + 1].max())
                if trail < p["stop"]:
                    p["stop"], p["trailed"] = trail, True
        for s in open_pos:
            b = bar(s, d)
            if b is not None:
                last_close[s] = float(b["close"])
        liab = sum(p["shares"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        val = cash - liab
        eq_log.append((d, val))
        held_log.append((d, len(open_pos)))
        gross_log.append((d, liab / val * 100 if val > 0 else float("nan")))
        pending = list(sig.get(d, []))
    for s in list(open_pos):   # valued at the last close, marked OPEN
        cover(s, open_pos[s], cal[-1], last_close.get(s, open_pos[s]["price"]), "OPEN")
    eq = pd.Series(dict(eq_log)).sort_index()
    dropped = {**dropped, **skipped}
    return (pd.DataFrame(trades), eq, pd.Series(dict(held_log)).sort_index(),
            pd.Series(dict(gross_log)).sort_index(), costs_total, dropped)


# ------------------------------------------------------------------ the sleeve test

def _stats(eq: pd.Series) -> dict:
    eq = eq.dropna()
    yrs = max((eq.index[-1] - eq.index[0]).days / 365.25, 1e-9)
    r = eq.pct_change().dropna()
    return {"cagr": ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100,
            "max_dd": float(metrics.drawdown_series(eq).min() * 100),
            "vol": float(r.std() * math.sqrt(252) * 100),
            "sharpe": float(r.mean() / r.std() * math.sqrt(252)) if r.std() > 0 else float("nan")}


def blend(long_eq: pd.Series, short_eq: pd.Series, weight_pct: float) -> pd.Series:
    """The account with `weight_pct` in the short sleeve and the rest in the long book, put back to the
    split at every month-end close. Each sleeve scales linearly with its capital, so blending daily
    returns with month-end rebalancing is the same account as two sub-accounts topped up monthly.
    Moving money between sleeves is not charged (it is a cash transfer; the trades inside each sleeve
    already paid their costs)."""
    idx = long_eq.index.intersection(short_eq.index)
    lr = long_eq.reindex(idx).pct_change().fillna(0)
    sr = short_eq.reindex(idx).pct_change().fillna(0)
    w = weight_pct / 100
    out, val = [], 1.0
    a, b = (1 - w) * val, w * val
    month = idx[0].to_period("M")
    for d in idx:
        if d.to_period("M") != month:   # the previous session was a month-end: rebalance at its close
            val = a + b
            a, b = (1 - w) * val, w * val
            month = d.to_period("M")
        a *= 1 + lr[d]
        b *= 1 + sr[d]
        out.append(a + b)
    return pd.Series(out, index=idx)


def find_long_book(market: str, out_dir: Path) -> Path | None:
    """The newest stored `LONG_BOOK` run with the same start and stage tag as this run, or None. The start
    matters as much as the tag: a shorter run of the long book has no crash years to compare."""
    tag = out_dir.name[out_dir.name.find("_stage-"):] if "_stage-" in out_dir.name else ""
    start = out_dir.name.split("_", 1)[0]
    root = out_dir.parent.parent / LONG_BOOK
    if not tag or not root.exists():
        return None
    runs = [p for p in root.iterdir() if p.name.endswith(tag) and p.name.startswith(start + "_")
            and (p / "equity.csv").exists()]
    return max(runs, key=lambda p: (p / "equity.csv").stat().st_mtime) if runs else None


def sleeve_table(long_eq: pd.Series, short_eq: pd.Series) -> tuple[pd.DataFrame, str]:
    """The blend at each sleeve weight, beside the CONTROL that decides it: the same weight held in
    cash. The short book is flat in most sessions, so any sleeve weight lowers the long book's drawdown
    by dilution alone; only the gap between the short sleeve and the cash sleeve is the hedge."""
    rows = []
    flat = pd.Series(1.0, index=short_eq.index)
    for w, sleeve in [(w, k) for w in SLEEVE_WEIGHTS for k in (("short",) if w == 0 else ("short", "cash"))]:
        e = blend(long_eq, short_eq if sleeve == "short" else flat, w)
        st = _stats(e)
        yr = e.resample("YE").last().pct_change()
        yr.iloc[0] = e.resample("YE").last().iloc[0] / e.iloc[0] - 1
        row = {"short_sleeve_pct": w, "sleeve": "none" if w == 0 else sleeve, "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
               "vol_pct": round(st["vol"], 2), "sharpe": round(st["sharpe"], 3)}
        for y in CRASH_YEARS:
            v = yr[yr.index.year == y]
            row[f"ret_{y}"] = round(float(v.iloc[0]) * 100, 2) if len(v) else float("nan")
        # the drawdown inside each crash year, which a calendar return can hide
        for y in CRASH_YEARS:
            s = e[e.index.year == y]
            row[f"dd_{y}"] = round(float(metrics.drawdown_series(s).min() * 100), 2) if len(s) else float("nan")
        rows.append(row)
    t = pd.DataFrame(rows)
    lines = ["| Sleeve | CAGR | Max DD | Vol | Sharpe | " + " | ".join(f"{y} ret / DD" for y in CRASH_YEARS) + " |",
             "|---|---|---|---|---|" + "---|" * len(CRASH_YEARS)]
    for r in rows:
        lines.append(f"| {r['short_sleeve_pct']}% {r['sleeve']} | {r['cagr_pct']:+.2f}% | {r['max_dd_pct']:.1f}% | "
                     f"{r['vol_pct']:.1f}% | {r['sharpe']:.2f} | "
                     + " | ".join(f"{r[f'ret_{y}']:+.1f}% / {r[f'dd_{y}']:.1f}%" for y in CRASH_YEARS) + " |")
    return t, "\n".join(lines)


# ------------------------------------------------------------------ documentation

DOC = {
    "key": "stage4_shorts",
    "name": "Stage 4 shorts",
    "description": (
        "Short a Stage 4 stock -- below a falling 30-week line and lagging its index -- when a rally "
        "to the line fails, only while the index itself is weak; cover on a trailing stop, a close "
        "above the 50-day, a weekly close above the line, or after {TIME_STOP} sessions short of 1R. "
        "Judged as a hedge beside the long momentum book, not on its own return."
    ),
    "status": (
        "FAILS ITS PASS CRITERION IN BOTH MARKETS (optimise stage, 2013-2021, v1.1; no verify run). "
        "Standalone, the shipped rule (failed rally to the line, market filter on, base costs) lost "
        "2.0% a year in the US (max drawdown -22%, 215 trades, 24% won, -0.26R a trade) and 4.0% in "
        "India (-32%, 267 trades, 23% won, -0.35R). As a 20% sleeve beside momentum_baseline it did "
        "not beat the same 20% held in cash: drawdown +0.4 points better in the US and 0.4 worse in "
        "India, against the 2 points required, with a lower Sharpe ratio in both. It helped in 2018 "
        "and a little in 2020, but the book is too small and too late to matter -- about 8% of the "
        "sleeve is short on an average day, because the weekly stage and the market filter confirm "
        "after the fall has begun. The breakdown entry (A) about broke even in the US (-0.04% a year) "
        "and did no better as a hedge. The one variant that cleared the drawdown test, India without "
        "the market filter (+2.9 points over cash, Sharpe 0.77 vs 0.75), fails it at stress costs "
        "(+1.6) and was found in-sample, so it is a hypothesis for a new version, not a result."
    ),
    "thesis": (
        "Every strategy on this shelf is long, so they all lose together in a bad year. Stage 4 stocks "
        "keep falling for the reason they started -- holders who bought higher sell into every rally, "
        "and bad news arrives in a series (Hong, Lim and Stein 2000) -- and momentum's losers keep "
        "lagging (Jegadeesh and Titman 1993). Shorting them only while the market is weak should "
        "earn little in a bull market and pay in a bear one, which is what a hedge for a long "
        "momentum book needs. The known danger is the rebound: losers rally hardest at a bear-market "
        "bottom (Daniel and Moskowitz 2016)."
    ),
    "how_it_works": (
        "The idea. Short the weakest stocks while they are falling, and only while the whole market "
        "is weak, so the book is small or empty in a bull market and largest in a bear one. The rules "
        "are the testable form of the Learn guide on shorting Stage 4 stocks (its section 3), on the "
        "stage model the Stage analysis strategy uses.",
        "Step 1 -- the stage. Each stock's stage comes from the weekly state machine on its 30-week "
        "simple average (Stage analysis, `stage_series`). A week's stage is read at that week's last "
        "close and holds until the next week ends.",
        "Step 2 -- the candidate. In Stage 4, with a 50-session median traded value at or above the "
        "market's liquidity floor, and a {RS_BARS}-session return below the index's. In India it must "
        "also be among the {FNO_PROXY_TOP} most traded stocks that day, the stand-in for having futures.",
        "Step 3 -- the signal. Entry B (the shipped one): after at least {STAGE4_MIN_SESSIONS} sessions "
        "in Stage 4, the day's high comes within {TOUCH_PCT}% of the line or above it and the close is "
        "back below it. Entry A (a variant): a close below the lowest close of the prior "
        "{BREAKDOWN_BARS} sessions on at least {BREAKDOWN_VOL_MULT} times average volume.",
        "Step 4 -- the market. A signal counts only if the index is below its {INDEX_SMA}-day average "
        "or that average is lower than {INDEX_SLOPE_BARS} sessions ago.",
        "Step 5 -- the short, at the next open, sized to risk {RISK_PCT}% of equity to the stop, with "
        "at most {MAX_OPEN_RISK_PCT}% at risk on all shorts together.",
        "Step 6 -- the cover: the stop (trailing from session {TRAIL_START}), a close above the "
        "{TREND_SMA}-day average once below it, a weekly close above the 30-week line, or the time stop.",
        "Judged twice. Standalone, and as a sleeve: each run blends its equity with the stored "
        "momentum_baseline run of the same market and stage, rebalanced to the weights at every "
        "month-end, and reports the blend's drawdown and its returns in the crash years.",
        "Running it. `python -m jobs enqueue backtest --market us --strategies stage4_shorts --stage "
        "optimise`; variants through `--bt`, e.g. `--bt '--entries A'` or `--bt '--no-market-filter'`.",
    ),
    "entry_rules": (
        "Stage 4. The stage model's stage for the last completed week is 4: the weekly close has held "
        "below a falling 30-week simple average long enough for the state machine to confirm it.\n\n"
        "**Guide (§3 Setup):** close below a falling 150-day average with the 50-day below it. "
        "Differs: the stage comes from the shelf's one stage model, on weekly bars, not a second "
        "daily classifier.",
        "Weak relative strength. The stock's {RS_BARS}-session return is below the benchmark index's.\n\n"
        "**Guide (§3 Setup):** the same.",
        "Liquid, and shortable. The {LIQ_BARS}-session median traded value is at or above the market's "
        "liquidity floor ($10 million US, ₹50 crore India, as configured). India: the stock also ranks "
        "in the top {FNO_PROXY_TOP} by that measure among the stocks with any Stage 4 signal -- a proxy "
        "for the futures list, which is not stored. No price floor: stored prices are split-adjusted, "
        "so a floor would drop stocks for splits they had not yet done.\n\n"
        "**Guide (§3 Universe):** ₹10 crore or $10 million, ₹50 or $5; futures available and not "
        "banned in India; borrow under 5% a year and short interest under 20% in the US. Differs: the "
        "futures list, the ban list, borrow rates and short interest are not stored -- see caveats.",
        "Entry B, failed rally to the line (the shipped entry). At least {STAGE4_MIN_SESSIONS} "
        "sessions in Stage 4 before today; today's high at or above the line less {TOUCH_PCT}%; "
        "today's close below the line. The line is the last completed week's 30-week average.\n\n"
        "**Guide (§3 Entry B):** the same, on the 150-day average.",
        "Entry A, breakdown (a variant, off by default). In Stage 4, a close below the lowest close "
        "of the prior {BREAKDOWN_BARS} sessions, on volume at least {BREAKDOWN_VOL_MULT} times its "
        "50-session average.\n\n**Guide (§3 Entry A):** the same.",
        "Initial stop. B: the highest high of the last {RALLY_BARS} sessions (the rally into the "
        "line) plus {STOP_ATR_BUFFER} ATR({ATR_BARS}). A: the lower of the {BREAKDOWN_STOP_BARS}-session "
        "high and the line, plus the same buffer. A signal whose stop is more than {MAX_STOP_PCT}% "
        "above the close is skipped, and so is one whose next open is above the high the stop sits "
        "over (the stop less its buffer) or more than {MAX_STOP_PCT}% below the stop.\n\n**Guide (§3 Initial stop):** the same.",
        "Market filter. The signal's date has the index below its {INDEX_SMA}-day average, or that "
        "average below its value {INDEX_SLOPE_BARS} sessions earlier.\n\n"
        "**Guide (§3 Universe):** the same (the guide says test both; the variant without it is run).",
        "The short. At the next session's open. Shares = {RISK_PCT}% of equity / (stop - open), cut "
        "so that the open risk on all shorts stays within {MAX_OPEN_RISK_PCT}% of equity and the short "
        "notional within {MAX_GROSS_PCT}% (and one short's within {MAX_POSITION_PCT}%). When several signals land on one day, the weakest "
        "relative strength is shorted first. Fractional shares; India's futures lots are ignored.\n\n"
        "**Guide (§3 Position size):** the same, in whole lots. Differs: the {MAX_POSITION_PCT}% cap on one "
        "short is added -- without it a stop just above the open sizes one short at most of the account.",
        "Costs (base case). US: {US_COST_BPS} bps a side, a borrow fee of {US_BORROW_PCT}% a year and "
        "dividends of {US_DIVIDEND_PCT}% a year on the short notional. India: {INDIA_COST_BPS} bps a "
        "side, {INDIA_ROLL_BPS} bps per monthly futures roll, and dividends of {INDIA_DIVIDEND_PCT}% a "
        "year. Every run also reports the result at {COST_LEVELS} times the trading, borrow and roll "
        "costs. No interest is credited on short proceeds.",
    ),
    "exit_rules": (
        "Each session the stop is checked first, then the close rules in this order; the first that "
        "applies covers the whole position.",
        "Stop. The day's high at or above the buy-stop covers at the stop, or at the open when the "
        "stock gaps up through it.\n\n**Guide (§3 Exits):** the same; the guide adds the fill rule "
        "under costs.",
        "Trailing stop. From session {TRAIL_START}, after each close the stop moves down to the highest "
        "high of the last {TRAIL_BARS} sessions when that is lower. Never up.\n\n"
        "**Guide (§3 Exits):** the same.",
        "Trend exit. A close above the {TREND_SMA}-day average, once a close since the short has been "
        "below it, covers at that close.\n\n**Guide (§3 Exits):** the same.",
        "Stage exit. On a week's last session, a close above that week's 30-week average covers at "
        "that close.\n\n**Guide (§3 Exits):** the same.",
        "Time stop. After {TIME_STOP} sessions, if the price never fell 1R below the entry, cover at "
        "the close.\n\n**Guide (§3 Exits):** the same.",
        "A position open when the backtest ends is covered at its last close and marked OPEN.",
    ),
    "caveats": (
        "**COST ASSUMPTIONS, which carry the result.** US: {US_BORROW_PCT}% a year borrow, the "
        "general-collateral rate for a liquid stock; hard-to-borrow names can cost tens of percent and "
        "are not identified, because borrow rates and short interest are not stored. Dividends are "
        "charged at a flat {US_DIVIDEND_PCT}% a year because stored prices are not dividend-adjusted. "
        "India: a short is held through stock futures, so it pays {INDIA_ROLL_BPS} bps per month to "
        "roll and a flat {INDIA_DIVIDEND_PCT}% dividend yield (futures price dividends out). No interest "
        "is credited on short proceeds or collateral -- conservative in India, where a futures short "
        "earns roughly the repo rate (4-8%) over the spot move, and close to neutral in the US in "
        "2013-2021, when rates were near zero.",
        "**India's futures list is a proxy.** The stored derivatives are index contracts only, so "
        "'has futures' is read as 'ranks in the top {FNO_PROXY_TOP} by traded value that day' among "
        "stocks with any Stage 4 signal. The real list differs, the ban list is not applied, and lot "
        "sizes (several lakh rupees) are ignored, which a ₹20 lakh account could not ignore.",
        "**Survivorship works against this strategy here.** The stored universe is today's lists, which "
        "leave out companies that collapsed and were delisted -- often the best shorts. The guide's own "
        "warning: a test on survivors makes shorting look worse than it was.",
        "**The R figures are true risk multiples**: profit after costs and carry over the initial "
        "risk to the stop. Gaps through the stop can make a loss larger than -1R.",
        "**PASS CRITERION, written before the first run (2026-10-25).** Judged on the optimise "
        "stage, base cost level, entry B with the market filter, per market, against the CONTROL of "
        "the same weight held in cash -- the short book is flat most of the time, so a sleeve lowers "
        "the long book's drawdown by dilution alone. It passes as a hedge if the 20% short sleeve "
        "beside momentum_baseline (a) has a maximum drawdown at least 2 points shallower than the 20% "
        "cash sleeve, (b) has a Sharpe ratio no lower than the long book alone, (c) beats the cash "
        "sleeve's return or drawdown in at least two of 2015, 2016, 2018 and 2020, and (d) still meets "
        "(a) at the stress cost level. A standalone loss is allowed. Only a version that passes goes to "
        "verify, once.",
        "**The weekly stage confirms late.** The stage model needs {MA_WEEKS}-week and confirmation "
        "history, and Stage 4 is confirmed weeks after a top -- by design, but it means the first "
        "leg of a crash is never shorted.",
    ),
}


class Stage4ShortsStrategy(PortfolioStrategy):
    """Weinstein's Stage 4 short, as the Learn guide states it, judged as a hedge sleeve."""

    key = DOC["key"]
    doc = DOC
    family = "stage4_shorts"
    version = "1.1"
    changelog = (("1.1", "2026-10-25",
                  "Skip a short whose next open is above the high its stop sits over (the stop less its ATR "
                  "buffer). v1.0 shorted those opens with a sliver of risk to the stop -- one US trade risked "
                  "0.01% and booked +4,677R -- so its R statistics were meaningless, though the 20% position "
                  "cap kept the equity effect small. Found on the v1.0 optimise runs; a degenerate geometry, "
                  "not a tuned threshold."),
                 ("1.0", "2026-10-25",
                  "First version, built to research/learn-strat-stage4-shorts.md §3 on the Stage analysis "
                  "stage model. Its own short simulator (the per-symbol engine is long-only); explicit "
                  "borrow, roll and dividend costs with a three-level sensitivity; a month-end sleeve "
                  "blend against momentum_baseline in every run."),)
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    runner = "stage4_shorts"

    param_docs = (
        ("Entries", "ENTRY_FAILED_RALLY", "1 shorts the failed rally to the line (B); ENTRY_BREAKDOWN 1 the breakdown (A)."),
        ("Time in Stage 4", "STAGE4_MIN_SESSIONS", "Sessions in Stage 4 before a rally to the line counts."),
        ("Touch distance", "TOUCH_PCT", "How close the day's high must come to the line, %."),
        ("Maximum stop", "MAX_STOP_PCT", "Skip a short whose stop is further above the entry, %."),
        ("Market filter", "MARKET_FILTER", "1 shorts only while the index is below or under a falling 200-day."),
        ("Trailing stop", "TRAIL_BARS", "Highest high of this many sessions, from session TRAIL_START."),
        ("Time stop", "TIME_STOP", "Sessions after which a trade that never reached 1R is covered."),
        ("Risk per short", "RISK_PCT", "Percent of equity risked to the stop."),
        ("Total short risk", "MAX_OPEN_RISK_PCT", "Open risk on all shorts together, % of equity."),
        ("US borrow fee", "US_BORROW_PCT", "Percent a year of the short notional."),
        ("India futures roll", "INDIA_ROLL_BPS", "Basis points per monthly roll."),
        ("Futures proxy", "FNO_PROXY_TOP", "India: most-traded stocks treated as having futures."),
    )


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Stage 4 shorts")
    ap.add_argument("--strategy", default="stage4_shorts")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    default_entries = ("B" if ENTRY_FAILED_RALLY else "") + ("A" if ENTRY_BREAKDOWN else "")
    ap.add_argument("--entries", default=default_entries, choices=["A", "B", "AB", "BA"],
                    help="B = failed rally to the line, A = breakdown to a 52-week low")
    ap.add_argument("--no-market-filter", action="store_true", help="short in any market")
    ap.add_argument("--no-ingest", action="store_true")
    a = ap.parse_args(argv)
    use_filter = bool(MARKET_FILTER) and not a.no_market_filter
    cfg = MARKETS[a.market]
    short_costs(a.market)   # refuses a market with no stated cost before loading anything

    prep = prepare(a.market)
    start_ts = pd.Timestamp(a.start)
    cands = candidates(prep, a.entries, use_filter, start_ts)
    runs = {lvl: run(prep, a.start, a.entries, use_filter, lvl, cands) for lvl in COST_LEVELS}
    tdf, eq, held, gross, costs, dropped = runs[1.0]
    bc = prep["bench"].reindex(eq.index).ffill()

    sens_lines = ["| Cost level | Per side | Carry a year | CAGR | Max DD | Avg R | Trades |", "|---|---|---|---|---|---|---|"]
    sens = []
    for lvl, (t, e, *_r) in runs.items():
        sc = short_costs(a.market, lvl)
        st = _stats(e)
        closed = t[t["exit_reason"] != "OPEN"] if len(t) else t
        avg_r = float(closed["r_multiple"].mean()) if len(closed) else float("nan")
        sens.append({"level": lvl, "cost_bps": sc["cost_bps"], "carry_pct": sc["carry_pct"],
                     "cagr_pct": round(st["cagr"], 2), "max_dd_pct": round(st["max_dd"], 2),
                     "avg_r": round(avg_r, 3), "trades": int(len(t))})
        sens_lines.append(f"| ×{lvl:g} | {sc['cost_bps']:g} bps | {sc['carry_pct']:.2f}% | {st['cagr']:+.2f}% | "
                          f"{st['max_dd']:.1f}% | {avg_r:+.2f} | {len(t)} |")

    by_year = (eq.resample("YE").last().pct_change() * 100).round(2)
    first = eq.resample("YE").last()
    by_year.iloc[0] = round((first.iloc[0] / eq.iloc[0] - 1) * 100, 2)
    bench_year = (bc.resample("YE").last().pct_change() * 100).round(2)
    bench_year.iloc[0] = round((bc.resample("YE").last().iloc[0] / bc.iloc[0] - 1) * 100, 2)
    notes = [
        f"SHORT BOOK. Entries {a.entries}; market filter {'on' if use_filter else 'off'}. "
        f"{len(prep['frames']):,} of {prep['n_universe']:,} stocks ever signalled; "
        f"{sum(len(v) for v in cands[0].values()):,} candidate signals on "
        f"{len(cands[0]):,} sessions. Dropped: {dropped}.",
        f"Average short exposure {gross.mean():.1f}% of equity (max {gross.max():.1f}%); "
        f"{(held > 0).mean() * 100:.0f}% of sessions hold any short.",
        "Cost sensitivity -- " + "; ".join(f"x{s['level']:g}: CAGR {s['cagr_pct']:+.2f}%, DD {s['max_dd_pct']:.1f}%, "
                                          f"avg R {s['avg_r']:+.2f}" for s in sens),
        "By year (strategy / index): " + ", ".join(
            f"{y.year} {v:+.1f}/{bench_year.get(y, float('nan')):+.1f}" for y, v in by_year.items()),
        "Stored prices are not dividend-adjusted; dividends are charged as a flat yield (see caveats). "
        "No interest is credited on short proceeds.",
    ]
    perf = metrics.compute(equity=eq, positions_open=held, trades=tdf, max_open_positions=0,
                           costs_paid=costs, bench_close=bc, cash=None, notes=notes)
    perf.benchmark_name = f"{cfg.benchmark_symbol} ({cfg.benchmark_ticker})"

    name = (f"{a.start}_entry{a.entries}_{'mkt' if use_filter else 'nomkt'}_risk{RISK_PCT:g}"
            f"_{Stage4ShortsStrategy.spec_id()}")
    out = run_dir(a.market, a.strategy, name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({"equity": eq, "positions_open": held, "gross_short_pct": gross,
                  "drawdown_pct": metrics.drawdown_series(eq) * 100}).to_csv(out / "equity.csv")
    for lvl, (_t, e, *_r) in runs.items():
        if lvl != 1.0:
            e.rename("equity").to_csv(out / f"equity_cost{lvl:g}.csv")
    pd.DataFrame(sens).to_csv(out / "cost_sensitivity.csv", index=False)

    extra = [("Cost sensitivity", "\n".join(sens_lines))]
    long_dir = find_long_book(a.market, out)
    if long_dir is not None:
        leq = pd.read_csv(long_dir / "equity.csv", index_col=0, parse_dates=True)["equity"]
        tables = []
        for lvl in (1.0, max(COST_LEVELS)):
            t, md = sleeve_table(leq, runs[lvl][1])
            t.insert(0, "cost_level", lvl)
            tables.append(t)
            extra.append((f"As a sleeve beside {LONG_BOOK} (cost x{lvl:g})",
                          f"Long book: `{long_dir.name}`. Monthly rebalance to the split.\n\n{md}"))
        pd.concat(tables).to_csv(out / "sleeve_blend.csv", index=False)
        perf.notes.append(f"Sleeve test against {long_dir.name}: see sleeve_blend.csv.")
    else:
        perf.notes.append(f"Sleeve test skipped: no stored {LONG_BOOK} run with this run's stage tag.")
    print()
    print(metrics.format_report(perf, cfg.currency_symbol, 0))
    for _t, body in extra:
        print("\n" + _t + "\n" + body)
    try:
        from . import report as report_mod
        md = report_mod.write_report(
            out, f"{cfg.name} — Stage 4 shorts, {a.start} onward", perf, eq, held, tdf,
            cfg.currency_symbol, 0, bc,
            f"python3 -m swing_screener.backtesting.stage4_shorts --market {a.market} --start {a.start} "
            f"--entries {a.entries}" + ("" if use_filter else " --no-market-filter"),
            extra_sections=extra)
        print(f"Report -> {md}")
    except Exception as e:   # noqa: BLE001
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    if not a.no_ingest:
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}


if __name__ == "__main__":
    main()
