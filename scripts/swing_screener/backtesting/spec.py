"""The portfolio-level parts of the Minervini backtest specification (research/minervini-backtest-spec.md).

A one-symbol evaluation cannot know a stock's rank among all stocks, the state of the market, or how
many bases a stock has already broken out of. These run over the collected signal list before the
simulator, each using only data up to the signal's own date:

  * `rs_ratings` / `filter_min_rs` — TT-08: the RS rating, 1–99 across the tradable universe on the
    signal date, RS_raw = 0.4 × 63-day + 0.2 × 126-, 189- and 252-day return (section 3);
  * `market_filter` — MKT-01: no new buys unless the benchmark closes above its 200-day average and
    its 50-day is above its 200-day;
  * `rank_rs_then_tightness` — PF-03: slots go to the highest RS, then the tightest tight area;
  * `base_numbers` — the base count (section 5), reported by `breakdown`;
  * `annotate_costs` — C-02's liquidity-dependent slippage and SL-06's traded-value cap input;
  * `breakdown` — section 13's metrics, by year, setup, exit, base number and in/out of sample.
"""

import logging
from dataclasses import replace

import numpy as np
import pandas as pd

from ..config import MARKETS
from ..marketdata import cache, db

logger = logging.getLogger(__name__)

# U-01 / U-02: the tradable universe the RS rating ranks across
MIN_PRICE = {"india": 50.0, "us": 10.0}
MIN_VALUE_50D = {"india": 1e8, "us": 5e6}          # ₹10 crore / $5 million average daily traded value
MIN_HISTORY = 260                                    # U-03

# C-01 / C-02, per side, in basis points of notional
COST_BPS = {"india": 12.0, "us": 1.0}               # statutory + brokerage (US: SEC/FINRA fees, no commission)
SLIPPAGE_BPS = {"india": 15.0, "us": 5.0}
ILLIQUID_SLIPPAGE_BPS = {"india": 30.0, "us": 10.0}
ILLIQUID_VALUE_50D = {"india": 2.5e8, "us": 2.5e7}  # below ₹25 crore (US: $25 million) traded a day

BASE_RESET_DAYS = 20       # the base count resets after this many sessions with TT-01 … TT-04 failing
IS_END = "2019-12-31"      # in-sample through this date, out-of-sample after (section 13)


# ---------------------------------------------------------------- RS rating (TT-08)

def rs_ratings(market: str, dates: list) -> dict:
    """{date: Series(symbol -> RS 1..99)} across the tradable universe on each date."""
    dates = sorted({pd.Timestamp(d) for d in dates})
    if not dates:
        return {}
    since = dates[0] - pd.Timedelta(days=420)
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, close, volume FROM prices
                       WHERE market=%s AND date >= %s AND date <= %s AND close > 0 AND symbol NOT LIKE '^%%'""",
                    (market, since.date(), dates[-1].date()))
        raw = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "close", "volume"])
    raw["date"] = pd.to_datetime(raw["date"])
    close = raw.pivot(index="date", columns="symbol", values="close").sort_index().astype(float)
    value = (close * raw.pivot(index="date", columns="symbol", values="volume").reindex_like(close).astype(float))
    del raw
    n = close.notna().sum(axis=1)
    close = close[n >= 0.5 * n.rolling(20, min_periods=1).median()]          # sessions, not stray holiday rows
    value = value.reindex(close.index)
    v50 = value.rolling(50, min_periods=40).mean()
    have = close.notna().cumsum()
    with db.get_connection().cursor() as cur:   # full history length, not just the loaded window
        cur.execute("SELECT symbol, min(date) FROM prices WHERE market=%s GROUP BY symbol", (market,))
        first = {s: pd.Timestamp(d) for s, d in cur.fetchall()}
    first_s = pd.Series(first).reindex(close.columns)
    out = {}
    for d in dates:
        if d not in close.index:
            prior = close.index[close.index <= d]
            if not len(prior):
                continue
            d_use = prior[-1]
        else:
            d_use = d
        i = close.index.get_loc(d_use)
        if i < 252:
            continue
        c = close.iloc[i]

        def ret(k):
            return c / close.iloc[i - k] - 1
        raw_rs = 2 * ret(63) + ret(126) + ret(189) + ret(252)
        age_ok = (first_s <= d_use - pd.Timedelta(days=int(MIN_HISTORY * 1.4))) | (have.iloc[i] >= MIN_HISTORY)
        ok = (c >= MIN_PRICE[market]) & (v50.iloc[i] >= MIN_VALUE_50D[market]) & age_ok & raw_rs.notna()
        v = raw_rs[ok]
        if len(v) < 20:
            continue
        pct = v.rank(pct=True)
        out[d] = (1 + 98 * (pct - 1 / len(v)) / (1 - 1 / len(v))).round()
    logger.info("RS ratings: %d dates rated", len(out))
    return out


def filter_min_rs(signals: list, market: str, min_rs: int) -> tuple[list, dict]:
    """TT-08: keep signals whose stock was rated `min_rs`+ on the signal date; the rating goes in meta["rs"].
    A stock outside the rated universe that day (too cheap, too thin, too new) is dropped."""
    ratings = rs_ratings(market, [s.date for s in signals])
    kept, low, unrated = [], 0, 0
    for s in signals:
        r = ratings.get(pd.Timestamp(s.date))
        rs = None if r is None else r.get(s.symbol)
        if rs is None or rs != rs:
            unrated += 1
            continue
        if rs < min_rs:
            low += 1
            continue
        kept.append(replace(s, meta={**s.meta, "rs": int(rs)}))
    logger.info("RS filter (>= %d): kept %d, below %d, outside the rated universe %d", min_rs, len(kept), low, unrated)
    return kept, {"min_rs": min_rs, "kept": len(kept), "below": low, "unrated": unrated}


# ---------------------------------------------------------------- market filter (MKT-01)

def market_ok(market: str) -> pd.Series:
    """Per date: benchmark close > its SMA200 and SMA50 > SMA200."""
    b = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    c = b["close"].astype(float)
    s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
    return (c > s200) & (s50 > s200)


def market_filter(signals: list, market: str) -> tuple[list, dict]:
    ok = market_ok(market)
    kept = [s for s in signals if bool(ok.asof(pd.Timestamp(s.date)))]
    logger.info("Market filter: kept %d of %d signals", len(kept), len(signals))
    return kept, {"kept": len(kept), "blocked": len(signals) - len(kept),
                  "days_open_pct": round(float(ok[ok.index >= min(s.date for s in signals)].mean()) * 100, 1) if signals else None}


# ---------------------------------------------------------------- ranking, base count, costs

def rank_rs_then_tightness(signals: list) -> list:
    """PF-03: quality = RS, ties broken by the tighter tight area (tightness ≤ 10%, so it only breaks ties)."""
    out = []
    for s in signals:
        rs = s.meta.get("rs") or 0
        t = s.meta.get("tightness")
        out.append(replace(s, quality=float(rs) - (float(t) / 1000 if t is not None and t == t else 0.01)))
    return out


def _breakout_bases(market: str, strategy_key: str) -> dict:
    """{symbol: [(date, base_id)]}: every bar the strategy judged an MV-01 breakout with the template
    passing, from its cached evaluations (backtest_signals) — whether or not a run trades MV-01."""
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, extras->>'base_date' FROM backtest_signals
                       WHERE market=%s AND strategy=%s AND hard_gates_passed AND (setups->>'MV-01')::boolean
                       ORDER BY symbol, date""", (market, strategy_key))
        out: dict = {}
        for sym, d, bid in cur.fetchall():
            if bid:
                out.setdefault(sym, []).append((pd.Timestamp(d), bid))
    return out


def base_numbers(signals: list, prices: dict, market: str, strategy_key: str) -> list:
    """Base number per signal: 1 + the other bases of this stock that produced an MV-01 breakout (traded
    or not) before the signal and since the trend last broke (TT-01 … TT-04 failing BASE_RESET_DAYS
    sessions in a row)."""
    breakouts = _breakout_bases(market, strategy_key)
    out = list(signals)
    for k, s in enumerate(signals):
        bid = s.meta.get("base_id")
        df = prices.get(s.symbol)
        if bid is None or df is None:
            continue
        c, s50, s150, s200, s200p = (df[col] for col in ("close", "sma50", "sma150", "sma200", "sma200_21d_ago"))
        broken = ~((c > s150) & (c > s200) & (s150 > s200) & (s200 > s200p) & (s50 > s150) & (s50 > s200))
        run = broken.groupby((~broken).cumsum()).cumsum()            # consecutive failing sessions
        resets = run.index[(run >= BASE_RESET_DAYS) & (run.index <= s.date)]
        since = resets[-1] if len(resets) else pd.Timestamp.min
        prior = {b for d, b in breakouts.get(s.symbol, []) if since < d <= s.date and b != bid}
        out[k] = replace(s, meta={**s.meta, "base_no": len(prior) + 1})
    return out


def annotate_costs(signals: list, prices: dict, market: str) -> list:
    """meta["adv"] (50-day average traded value, for SL-06) and meta["slippage_bps"] (C-02)."""
    out = []
    v50 = {sym: (df["close"] * df["volume"]).rolling(50, min_periods=40).mean() for sym, df in prices.items()}
    for s in signals:
        a = v50.get(s.symbol)
        adv = float(a.asof(pd.Timestamp(s.date))) if a is not None else float("nan")
        slip = ILLIQUID_SLIPPAGE_BPS[market] if adv == adv and adv < ILLIQUID_VALUE_50D[market] else SLIPPAGE_BPS[market]
        out.append(replace(s, meta={**s.meta, "adv": adv if adv == adv else None, "slippage_bps": slip}))
    return out


# ---------------------------------------------------------------- reporting (section 13)

def _stats(t: pd.DataFrame) -> dict:
    closed = t[t["exit_reason"] != "OPEN"]
    if closed.empty:
        return {"trades": len(t)}
    r = closed["r_multiple"].astype(float)
    win, loss = r[r > 0], r[r <= 0]
    gp, gl = closed.loc[closed["pnl"] > 0, "pnl"].sum(), -closed.loc[closed["pnl"] <= 0, "pnl"].sum()
    return {
        "trades": len(t), "win_rate": len(win) / len(r) * 100,
        "avg_win_r": win.mean() if len(win) else None, "avg_loss_r": loss.mean() if len(loss) else None,
        "expectancy_r": r.mean(), "profit_factor": gp / gl if gl > 0 else None,
        "hold_win": closed.loc[r > 0, "holding_days"].mean() if len(win) else None,
        "hold_loss": closed.loc[r <= 0, "holding_days"].mean() if len(loss) else None,
        "big_losses_pct": (r < -1.5).sum() / len(loss) * 100 if len(loss) else None,
        "pnl": closed["pnl"].sum(),
    }


def _fmt(v, d=2, suffix=""):
    return "—" if v is None or v != v else f"{v:,.{d}f}{suffix}"


def trades_over_suspect_gaps(trades: pd.DataFrame, market: str) -> int:
    """How many trades were held across a split-shaped gap that is still in the source data
    (marketdata/splits.py `source_suspects`) — a false crash the stop would have acted on."""
    from ..marketdata import splits
    if trades.empty:
        return 0
    sus = splits.source_suspects(market)
    if sus.empty:
        return 0
    gaps = sus.groupby("symbol")["date"].apply(lambda x: [pd.Timestamp(d) for d in x]).to_dict()
    n = 0
    for t in trades.itertuples():
        for d in gaps.get(t.symbol, []):
            if pd.Timestamp(t.entry_date) < d <= pd.Timestamp(t.exit_date):
                n += 1
                break
    return n


def breakdown(trades: pd.DataFrame, equity: pd.Series, currency: str) -> str:
    """Markdown tables: the spec's metrics overall and by year, setup, exit, base number and sample."""
    if trades.empty:
        return "No trades."
    t = trades.copy()
    t["year"] = pd.to_datetime(t["entry_date"]).dt.year
    t["sample"] = np.where(pd.to_datetime(t["entry_date"]) <= pd.Timestamp(IS_END), f"in-sample (≤{IS_END[:4]})", f"out-of-sample (>{IS_END[:4]})")
    head = ("| | Trades | Win % | Avg win R | Avg loss R | Expectancy R | Profit factor | Days held, winners | "
            "Days held, losers | Losses beyond −1.5R | P&L |\n|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    def row(name, s):
        return (f"| {name} | {s.get('trades', 0)} | {_fmt(s.get('win_rate'), 1)} | {_fmt(s.get('avg_win_r'))} | "
                f"{_fmt(s.get('avg_loss_r'))} | {_fmt(s.get('expectancy_r'))} | {_fmt(s.get('profit_factor'))} | "
                f"{_fmt(s.get('hold_win'), 0)} | {_fmt(s.get('hold_loss'), 0)} | {_fmt(s.get('big_losses_pct'), 1, '%')} | "
                f"{currency}{_fmt(s.get('pnl'), 0)} |")

    L = [head, row("All trades", _stats(t))]
    sections = [("By sample", "sample"), ("By setup / entry mode", "setup"), ("By exit", "exit_reason"), ("By year of entry", "year")]
    if "base_no" in t and t["base_no"].notna().any():
        t["base"] = t["base_no"].apply(lambda b: "—" if b != b or b is None else (f"base {int(b)}" if b < 4 else "base 4+"))
        sections.insert(2, ("By base number", "base"))
    out = ["### Overall", "", *L, ""]
    for title, col in sections:
        out += [f"### {title}", "", head]
        for k, g in t.groupby(col, sort=True):
            out.append(row(k, _stats(g)))
        out.append("")
    if len(equity):
        is_eq, oos_eq = equity[equity.index <= IS_END], equity[equity.index > IS_END]

        def cagr(e):
            if len(e) < 2:
                return None
            yrs = (e.index[-1] - e.index[0]).days / 365.25
            return ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100 if yrs > 0 else None
        out += ["### CAGR in and out of sample", "",
                f"In-sample (to {IS_END}): {_fmt(cagr(is_eq), 2, '%')} · out-of-sample (after): {_fmt(cagr(oos_eq), 2, '%')}", ""]
    return "\n".join(out)
