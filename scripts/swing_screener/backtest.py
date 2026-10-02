"""Walk-forward backtest, strategy-agnostic — a true day-by-day
simulation where every date only sees data up to and including itself.

Methodology, stated plainly (so results aren't over-trusted):
* Entry: a trade opens on the first day the active strategy's own
  classify() grades the symbol TRADE - HIGH CONFIDENCE. Delegating to the
  strategy (rather than re-implementing a subset of its thresholds here)
  means the backtest can't drift from the live rules — an earlier version
  hand-checked risk/R/demand-supply but omitted the watch-flag cap, so it
  took trades the live system would only ever have rated TRADE ON TRIGGER.
* Entries are resting buy-stop orders, filled only when a LATER bar trades
  through the trigger — never a same-day fill at a price the symbol never
  reached. Unfilled orders expire after PENDING_EXPIRY_DAYS.
* Exit: whichever of stop/target is touched first on a later day's
  low/high. If both would be touched on the same bar, the stop is
  assumed to fill first (conservative — can't know the intraday order
  from daily bars).
* Stop and target are fixed at entry (no trailing — nothing in the live
  system implements trailing stops either, it's a label, not a rule).
* Earnings (D2) is NOT enforced historically — there's no cached
  point-in-time earnings calendar, so a trade that live would have been
  blocked by an upcoming earnings date may appear here. This is a real
  gap, not a rounding error; treat D2-sensitive trades with that in mind.
* Universe is pre-filtered through TODAY's pre-filter before walking
  back, to keep runtime bounded against thousands of cached tickers — a
  stock that qualified mid-window but fails today is invisible here. Said
  out loud rather than silently assumed.
* Market regime downgrade and sector-cap-of-3 are NOT applied — this
  tests the gate/entry/setup logic itself, not the portfolio-construction
  overlay on top of it.

Usage:
    python3 -m swing_screener.backtest --market us --start 2025-01-01
    python3 -m swing_screener.backtest --market us --start 2025-01-01 --strategy breakout
"""

import argparse
import json
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import cache, db, universe, indicators as ind, sizing
from . import context as ctx_mod
from .context import StockContext
from .config import MarketConfig, MARKETS
from .strategies import DEFAULT_STRATEGY, StrategyResult, get_strategy, list_strategies

logger = logging.getLogger("backtest")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

REPORT_DIR = Path(__file__).resolve().parent.parent / "reports"


@dataclass
class Trade:
    market: str
    symbol: str
    setup: str
    entry_date: pd.Timestamp
    entry_price: float
    stop: float
    target: float
    shares: int
    exit_date: pd.Timestamp
    exit_reason: str  # TARGET / STOP / OPEN
    exit_price: float

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.shares

    @property
    def pct_return(self) -> float:
        return (self.exit_price / self.entry_price - 1) * 100

    @property
    def r_multiple(self) -> float:
        risk = self.entry_price - self.stop
        return (self.exit_price - self.entry_price) / risk if risk > 0 else float("nan")

    @property
    def holding_days(self) -> int:
        return (self.exit_date - self.entry_date).days


_SIGNAL_FIELDS = (
    "hard_gates_passed", "first_failed_gate", "has_setup", "setups",
    "h_value", "h_index", "l_value", "p_value", "prior_swing_low",
    "overhead_levels", "watch_flags", "watch_notes",
)


def _load_cached_signal(
    market_key: str, strategy, symbol: str, date: pd.Timestamp
) -> "tuple[StockContext, StrategyResult] | None":
    """A signal cache hit skips build_context()+compute_gates() entirely —
    that's the expensive part (swing-structure detection, every gate). The
    daily tail (with precomputed indicators) comes from the `prices` table,
    which is cheap regardless of total history length since it's indexed
    and backward-only."""
    conn = db.get_connection()
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT {', '.join(_SIGNAL_FIELDS)} FROM backtest_signals "
            f"WHERE market=%s AND strategy=%s AND symbol=%s AND date=%s",
            (market_key, strategy.key, symbol, date.date()),
        )
        row = cur.fetchone()
    if row is None:
        return None
    vals = dict(zip(_SIGNAL_FIELDS, row))

    daily = cache.load_cached_with_indicators(market_key, symbol, date, tail=70)
    if daily is None or len(daily) < 15:
        return None  # not enough tail data cached for entry/demand-supply math — recompute fresh

    result = StrategyResult(
        first_hard_fail=vals["first_failed_gate"],
        setups=vals["setups"] or {},
        entry_setup_codes=strategy.setup_codes,
        watch_flags=vals["watch_flags"] or {}, watch_notes=vals["watch_notes"] or {},
    )
    ctx = StockContext(
        symbol=symbol, daily=daily, weekly=pd.DataFrame(), monthly=pd.DataFrame(),
        h_value=vals["h_value"], h_index=pd.Timestamp(vals["h_index"]) if vals["h_index"] else None,
        l_value=vals["l_value"], p_value=vals["p_value"], prior_swing_low=vals["prior_swing_low"],
        overhead=vals["overhead_levels"] or [], history_months=24,  # unused downstream of a cache hit
    )
    # weekly/monthly are intentionally empty on the cache-hit path: nothing
    # between here and the trade decision reads them. If a strategy ever
    # does, it must not use the signal cache (or this must be widened).
    return ctx, result


def _signal_row(
    market_key: str, strategy, symbol: str, date: pd.Timestamp,
    ctx: StockContext, result: StrategyResult,
) -> tuple:
    return (
        market_key, strategy.key, symbol, date.date(),
        result.hard_gates_passed, result.first_hard_fail,
        result.has_setup, json.dumps({k: bool(v) for k, v in result.setups.items()}),
        ctx.h_value, ctx.h_index.date() if ctx.h_index is not None else None,
        ctx.l_value, ctx.p_value, ctx.prior_swing_low,
        json.dumps(ctx.overhead),
        json.dumps({k: bool(v) for k, v in result.watch_flags.items()}),
        json.dumps(result.watch_notes),
    )


def _save_signals(rows: list[tuple]) -> None:
    if not rows:
        return
    query = """
        INSERT INTO backtest_signals
            (market, strategy, symbol, date, hard_gates_passed, first_failed_gate,
             has_setup, setups, h_value, h_index, l_value, p_value,
             prior_swing_low, overhead_levels, watch_flags, watch_notes)
        VALUES %s
        ON CONFLICT (market, strategy, symbol, date) DO NOTHING
    """
    db.execute_values(query, rows)


def backtest_symbol(
    symbol: str, raw_daily: pd.DataFrame, cfg: MarketConfig, start_date: pd.Timestamp,
    strategy=None, market_key: str = "", use_signal_cache: bool = True,
) -> list[Trade]:
    if strategy is None:
        strategy = get_strategy(DEFAULT_STRATEGY)
    trades: list[Trade] = []
    new_signal_rows: list[tuple] = []
    if raw_daily is None or len(raw_daily) < 260:
        return trades

    sim_dates = raw_daily.index[raw_daily.index >= start_date]
    if len(sim_dates) < 2:
        return trades

    # The screen, as of every bar. One enrich over the full history is
    # equivalent to re-enriching each slice (every indicator is
    # backward-looking) and vastly cheaper. A bar where the screen fails is
    # a bar on which the live pipeline would never have shown this symbol,
    # so it must not produce a new entry.
    screened_in = strategy.prefilter_mask(cfg, ind.enrich_daily(raw_daily))

    in_position = False
    pos: dict | None = None

    # `_compute_trigger` always starts from the CURRENT day's own high and
    # only ever moves the trigger up — so the computed entry is, by
    # construction, always >= that day's high. It can never fill on the
    # day the signal was identified; it's a resting buy-stop order that
    # fills (or doesn't) on a LATER day. `pending` models that order.
    pending: dict | None = None
    PENDING_EXPIRY_DAYS = 10  # matches S-02's '3-10 bars' pullback-duration convention

    for current_date in sim_dates:
        row = raw_daily.loc[current_date]

        if in_position:
            stop_hit = row["low"] <= pos["stop"]
            target_hit = row["high"] >= pos["target"]
            if stop_hit:  # conservative: stop wins a same-bar tie
                trades.append(_close_trade(pos, current_date, "STOP", pos["stop"]))
                in_position, pos = False, None
            elif target_hit:
                trades.append(_close_trade(pos, current_date, "TARGET", pos["target"]))
                in_position, pos = False, None
            continue  # either way, no new entry on the exit bar itself

        if pending is not None:
            triggered = row["high"] >= pending["entry"]
            stopped_first = (not triggered) and (row["low"] <= pending["stop"])
            expired = current_date > pending["expires"]
            if stopped_first or expired:
                pending = None  # price fell away (or time ran out) before the order ever filled — not a trade
            elif triggered:
                pos = {
                    "market": cfg.name, "symbol": symbol, "setup": pending["setup"],
                    "entry_date": current_date, "entry_price": pending["entry"],
                    "stop": pending["stop"], "target": pending["target"], "shares": pending["shares"],
                }
                in_position, pending = True, None
                # same-bar check: a huge-range day could clear the trigger
                # and the stop in one session
                if row["low"] <= pos["stop"]:
                    trades.append(_close_trade(pos, current_date, "STOP", pos["stop"]))
                    in_position, pos = False, None
                elif row["high"] >= pos["target"]:
                    trades.append(_close_trade(pos, current_date, "TARGET", pos["target"]))
                    in_position, pos = False, None
                continue
            else:
                continue  # still resting, unfilled — don't also scan for a brand-new setup this bar

        # point-in-time screen: not "does it pass today", but "did it pass
        # on THIS bar". Checked after the position/pending handling above so
        # an open trade is still managed if the symbol drops out of the screen.
        if not bool(screened_in.get(current_date, False)):
            continue

        cached = (
            _load_cached_signal(market_key, strategy, symbol, current_date)
            if (use_signal_cache and market_key) else None
        )
        if cached is not None:
            ctx, result = cached
        else:
            slice_df = raw_daily.loc[:current_date]
            if len(slice_df) < 260:
                continue
            try:
                ctx = ctx_mod.build_context(symbol, slice_df, earnings_days_away=None)
            except Exception:
                continue
            if ctx is None:
                continue
            try:
                result = strategy.evaluate(ctx)
            except Exception:
                continue
            if market_key:
                new_signal_rows.append(
                    _signal_row(market_key, strategy, symbol, current_date, ctx, result)
                )

        if not result.hard_gates_passed or not result.has_setup:
            continue
        if not strategy.entry_signal_fired(ctx, result):
            continue
        plan = strategy.build_plans(ctx, result, cfg).chosen
        if plan is None or not plan.is_valid:
            continue
        sz = sizing.size_position(cfg, plan.entry, plan.stop, vix_above_threshold=False)
        if sz.too_large:
            continue
        # Match the live TRADE - HIGH CONFIDENCE bar, not just gates+setup+
        # signal. classify() is the SINGLE arbiter of risk/R admissibility --
        # the inline risk%/R test that used to sit here duplicated thresholds
        # classify already enforces, so it could only ever drift out of sync
        # with the live pipeline (and silently did, when the cap moved to ATRs).
        dec = strategy.classify(ctx, result, plan, sz, None, False)
        if dec.label_before != "TRADE - HIGH CONFIDENCE":
            continue

        # a resting buy-stop order, not an instant fill — see note above
        pending = {
            "setup": plan.setup, "entry": plan.entry, "stop": plan.stop,
            "target": plan.target, "shares": sz.shares,
            "expires": current_date + pd.tseries.offsets.BDay(PENDING_EXPIRY_DAYS),
        }

    if in_position:
        last_date = raw_daily.index[-1]
        last_close = float(raw_daily["close"].iloc[-1])
        trades.append(_close_trade(pos, last_date, "OPEN", last_close))

    _save_signals(new_signal_rows)  # one batched write per symbol, not one per day
    return trades


def _close_trade(pos: dict, exit_date: pd.Timestamp, reason: str, exit_price: float) -> Trade:
    return Trade(
        market=pos["market"], symbol=pos["symbol"], setup=pos["setup"],
        entry_date=pos["entry_date"], entry_price=pos["entry_price"],
        stop=pos["stop"], target=pos["target"], shares=pos["shares"],
        exit_date=exit_date, exit_reason=reason, exit_price=exit_price,
    )


def _coverage_is_sufficient(
    raw: pd.DataFrame | None, start: pd.Timestamp, warmup_bars: int,
    stale_after_days: int = 7,
) -> bool:
    """True when cached history already spans what the backtest needs:
    `warmup_bars` bars before the window opens, and a tail that reaches
    roughly the present. Re-pulling those symbols costs a lot of network
    time and returns the same data."""
    if raw is None or raw.empty:
        return False
    if int((raw.index < start).sum()) < warmup_bars:
        return False
    age_days = (pd.Timestamp.now().normalize() - raw.index[-1].normalize()).days
    return age_days <= stale_after_days


def refresh_deep_history(
    provider, market_key: str, symbols: list[str], deep_lookback_days: int,
    start: pd.Timestamp | None = None, warmup_bars: int = 260,
) -> dict[str, pd.DataFrame]:
    """Ensure `symbols` have `deep_lookback_days` of history (batched, not
    one-by-one) — the normal incremental cache only extends the tail, it
    won't backfill MORE history before the existing start, so a longer
    backtest window needs this explicit deep re-pull.

    Symbols whose cache already covers the window are reused rather than
    refetched, so a re-run after a parameter tweak doesn't re-download the
    whole candidate set."""
    out: dict[str, pd.DataFrame] = {}
    to_fetch: list[str] = []
    for sym in symbols:
        raw = cache.load_cached(market_key, sym)
        if start is not None and _coverage_is_sufficient(raw, start, warmup_bars):
            out[sym] = raw
        else:
            to_fetch.append(sym)

    logger.info(
        "Deep history: %d/%d symbols already cover the window; fetching %d to %d trading days",
        len(out), len(symbols), len(to_fetch), deep_lookback_days,
    )
    if to_fetch:
        fresh = provider.get_many_daily_bars(to_fetch, deep_lookback_days)
        for sym, df in fresh.items():
            if df is not None and not df.empty:
                cache.save_cached(market_key, sym, df)
                out[sym] = df
        logger.info("Deep refresh: got data for %d/%d fetched symbols", len(fresh), len(to_fetch))
    logger.info("Deep history ready for %d/%d candidates", len(out), len(symbols))
    return out


def run_backtest(
    market_key: str, start_date: str, limit: int | None = None, deep_lookback_days: int = 1000,
    use_signal_cache: bool = True, strategy_key: str = DEFAULT_STRATEGY,
) -> pd.DataFrame:
    db.init_schema()
    cfg = MARKETS[market_key]
    strategy = get_strategy(strategy_key)
    start = pd.Timestamp(start_date)
    logger.info("Strategy: %s (%s)", strategy.key, strategy.name)

    tickers = universe.load_universe(market_key)
    logger.info(
        "Universe: %d tickers; applying the pre-filter POINT-IN-TIME over the window...",
        len(tickers),
    )

    # A symbol is a candidate if it would have been screened in on AT LEAST
    # ONE bar in the window -- not if it passes today. Selecting on today's
    # row leaks the present into the past: a stock that trended all through
    # the window but is consolidating now (low ADX today) would be dropped
    # from the entire simulation, discarding trades the live screener would
    # genuinely have taken.
    candidates: list[str] = []
    excluded_today: list[str] = []
    for sym in tickers:
        raw = cache.load_cached(market_key, sym)
        if raw is None or len(raw) < 260:
            continue
        enriched = ind.enrich_daily(raw)
        mask = strategy.prefilter_mask(cfg, enriched)
        in_window = mask[mask.index >= start]
        if bool(in_window.any()):
            candidates.append(sym)
            if not bool(strategy.passes_prefilter(cfg, enriched)[0]):
                excluded_today.append(sym)
    logger.info(
        "Pre-filter (%s): %d/%d symbols qualify on >=1 bar in the window",
        strategy.key, len(candidates), len(tickers),
    )
    logger.info(
        "  of those, %d would have been MISSED by selecting on today's row",
        len(excluded_today),
    )

    if limit:
        candidates = candidates[:limit]
        logger.info("Capped to %d symbols for this run", len(candidates))

    from .providers import YFinanceProvider

    deep_data = refresh_deep_history(
        YFinanceProvider(), market_key, candidates, deep_lookback_days,
        start=start, warmup_bars=strategy.min_bars,
    )

    all_trades: list[Trade] = []
    for i, sym in enumerate(candidates):
        raw = deep_data.get(sym)
        if raw is None:
            raw = cache.load_cached(market_key, sym)
        trades = backtest_symbol(
            sym, raw, cfg, start, strategy=strategy,
            market_key=market_key, use_signal_cache=use_signal_cache,
        )
        all_trades.extend(trades)
        if (i + 1) % 50 == 0:
            logger.info("Backtested %d/%d symbols, %d trades so far", i + 1, len(candidates), len(all_trades))

    logger.info("Done: %d trades across %d symbols", len(all_trades), len(candidates))
    return trades_to_df(all_trades)


def trades_to_df(trades: list[Trade]) -> pd.DataFrame:
    rows = [
        {
            "market": t.market, "symbol": t.symbol, "setup": t.setup,
            "entry_date": t.entry_date.date(), "entry_price": round(t.entry_price, 2),
            "stop": round(t.stop, 2), "target": round(t.target, 2),
            "exit_date": t.exit_date.date(), "exit_reason": t.exit_reason,
            "exit_price": round(t.exit_price, 2), "shares": t.shares,
            "pnl": round(t.pnl, 2), "pct_return": round(t.pct_return, 2),
            "r_multiple": round(t.r_multiple, 2), "holding_days": t.holding_days,
        }
        for t in trades
    ]
    cols = [
        "market", "symbol", "setup", "entry_date", "entry_price", "stop", "target",
        "exit_date", "exit_reason", "exit_price", "shares", "pnl", "pct_return",
        "r_multiple", "holding_days",
    ]
    return pd.DataFrame(rows, columns=cols)


def print_summary(df: pd.DataFrame, currency_symbol: str) -> None:
    if df.empty:
        print("No trades.")
        return
    closed = df[df["exit_reason"] != "OPEN"]
    wins = closed[closed["exit_reason"] == "TARGET"]
    losses = closed[closed["exit_reason"] == "STOP"]
    open_trades = df[df["exit_reason"] == "OPEN"]

    print(f"Total trades: {len(df)}  (closed: {len(closed)}, still open: {len(open_trades)})")
    if len(closed):
        win_rate = len(wins) / len(closed) * 100
        print(f"Win rate: {win_rate:.1f}% ({len(wins)}W / {len(losses)}L)")
        print(f"Avg R-multiple (closed): {closed['r_multiple'].mean():.2f}")
        print(f"Total P&L (closed): {currency_symbol}{closed['pnl'].sum():,.2f}")
    if len(open_trades):
        print(f"Open trades unrealized P&L: {currency_symbol}{open_trades['pnl'].sum():,.2f}")
    print(f"Total P&L (incl. open, mark-to-market): {currency_symbol}{df['pnl'].sum():,.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward backtest")
    parser.add_argument("--market", choices=list(MARKETS.keys()), required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="cap number of symbols tested")
    parser.add_argument("--strategy", default=DEFAULT_STRATEGY, choices=list_strategies())
    parser.add_argument(
        "--deep-lookback-days", type=int, default=1000,
        help="trading days of history to pull for candidates before simulating (default 1000 "
        "~= 4 years, enough buffer for a ~21-month backtest window with all 24-month gates intact)",
    )
    parser.add_argument(
        "--no-signal-cache", action="store_true",
        help="recompute gates/setup from scratch instead of reusing backtest_signals — use this "
        "when you've changed a strategy's gate logic, not just trade-sim params "
        "(stop buffer, risk/R thresholds, pending-order expiry) which don't need it",
    )
    args = parser.parse_args()

    df = run_backtest(
        args.market, args.start, args.limit, args.deep_lookback_days,
        use_signal_cache=not args.no_signal_cache, strategy_key=args.strategy,
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"{args.market}_{args.strategy}_backtest_{args.start}.csv"
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df)} trades to {out_path}\n")
    print_summary(df, MARKETS[args.market].currency_symbol)
    if not df.empty:
        print("\nTrades:")
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
