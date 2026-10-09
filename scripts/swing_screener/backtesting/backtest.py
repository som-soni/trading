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
    python3 -m swing_screener.backtesting.backtest --market us --start 2025-01-01
    python3 -m swing_screener.backtesting.backtest --market us --start 2025-01-01 --strategy breakout
"""

import argparse
import json
import logging
from dataclasses import dataclass, replace as dc_replace
from pathlib import Path

import pandas as pd

from ..marketdata import cache, db, universe

from ..core import indicators as ind, sizing
from ..core import context as ctx_mod
from ..core.context import StockContext
from ..config import MarketConfig, MARKETS
from ..strategies import DEFAULT_STRATEGY, StrategyResult, get_strategy, list_strategies

logger = logging.getLogger("backtest")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from ..paths import REPORTS_DIR as REPORT_DIR  # noqa: F401

# Live progress hook. The `backtest` job (jobs/registry.py) points this at its run-log step so the
# Runs page shows movement during a long run ("scanned 1,200/2,148 symbols…"); the CLI leaves it
# unset and relies on the logger. Callers may invoke it per item — the consumer throttles.
on_progress = None


def _progress(text: str) -> None:
    if on_progress:
        on_progress(text)


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
    decision: str = ""  # the classify() label this entry was accepted under

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
    "hard_gates_passed", "first_failed_gate", "hard_gates", "has_setup", "setups",
    "h_value", "h_index", "l_value", "p_value", "prior_swing_low",
    "overhead_levels", "watch_flags", "watch_notes", "extras",
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

    # A strategy whose build_plans() reads ctx.extras cannot use a row written
    # before extras were persisted: rebuilding from it yields an empty extras
    # dict and the strategy silently emits no signals. Treat that as a miss.
    if getattr(strategy, "needs_ctx_extras", False) and not vals.get("extras"):
        return None

    daily = cache.load_cached_with_indicators(market_key, symbol, date, tail=70)
    if daily is None or len(daily) < 15:
        return None  # not enough tail data cached for entry/demand-supply math — recompute fresh

    result = StrategyResult(
        first_hard_fail=vals["first_failed_gate"],
        hard_gates=vals.get("hard_gates") or {},
        setups=vals["setups"] or {},
        entry_setup_codes=strategy.setup_codes,
        watch_flags=vals["watch_flags"] or {}, watch_notes=vals["watch_notes"] or {},
    )
    ctx = StockContext(
        symbol=symbol, daily=daily, weekly=pd.DataFrame(), monthly=pd.DataFrame(),
        h_value=vals["h_value"], h_index=pd.Timestamp(vals["h_index"]) if vals["h_index"] else None,
        l_value=vals["l_value"], p_value=vals["p_value"], prior_swing_low=vals["prior_swing_low"],
        overhead=vals["overhead_levels"] or [], history_months=24,  # unused downstream of a cache hit
        extras=dict(vals.get("extras") or {}),
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
        json.dumps({k: bool(v) for k, v in result.hard_gates.items()}),
        result.has_setup, json.dumps({k: bool(v) for k, v in result.setups.items()}),
        ctx.h_value, ctx.h_index.date() if ctx.h_index is not None else None,
        ctx.l_value, ctx.p_value, ctx.prior_swing_low,
        json.dumps(ctx.overhead),
        json.dumps({k: bool(v) for k, v in result.watch_flags.items()}),
        json.dumps(result.watch_notes),
        json.dumps({k: db.py_value(v) for k, v in (ctx.extras or {}).items()}),
    )


def _save_signals(rows: list[tuple]) -> None:
    if not rows:
        return
    query = """
        INSERT INTO backtest_signals
            (market, strategy, symbol, date, hard_gates_passed, first_failed_gate,
             hard_gates, has_setup, setups, h_value, h_index, l_value, p_value,
             prior_swing_low, overhead_levels, watch_flags, watch_notes, extras)
        VALUES %s
        ON CONFLICT (market, strategy, symbol, date) DO UPDATE SET
            hard_gates=EXCLUDED.hard_gates, setups=EXCLUDED.setups,
            watch_flags=EXCLUDED.watch_flags, watch_notes=EXCLUDED.watch_notes,
            extras=EXCLUDED.extras
    """
    db.execute_values(query, rows)


def backtest_symbol(
    symbol: str, raw_daily: pd.DataFrame, cfg: MarketConfig, start_date: pd.Timestamp,
    strategy=None, market_key: str = "", use_signal_cache: bool = True,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
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
                # A bar that OPENS past the stop never traded at the stop --
                # the realistic fill is the open. 16.4% of stop exits gap
                # through, and they average -1.50R rather than the -1.00R a
                # fill-at-the-stop assumption reports.
                fill = min(pos["stop"], float(row["open"]))
                trades.append(_close_trade(pos, current_date, "STOP", fill))
                in_position, pos = False, None
            elif target_hit:
                # symmetric on the upside: a favourable gap fills better
                fill = max(pos["target"], float(row["open"]))
                trades.append(_close_trade(pos, current_date, "TARGET", fill))
                in_position, pos = False, None
            continue  # either way, no new entry on the exit bar itself

        if pending is not None:
            triggered = row["high"] >= pending["entry"]
            stopped_first = (not triggered) and (row["low"] <= pending["stop"])
            expired = current_date > pending["expires"]
            if stopped_first or expired:
                pending = None  # price fell away (or time ran out) before the order ever filled — not a trade
            elif triggered:
                # a resting buy-stop that gaps open above its trigger fills at
                # the open, not the trigger -- a worse entry, so assuming the
                # trigger price flatters both entry and every R computed from it
                fill_entry = max(pending["entry"], float(row["open"]))
                if fill_entry >= pending["target"]:
                    # gapped clean past the target: the whole reward is gone
                    # before we could be filled, so the order is simply dead
                    pending = None
                    continue
                pos = {
                    "market": cfg.name, "symbol": symbol, "setup": pending["setup"],
                    "entry_date": current_date, "entry_price": fill_entry,
                    "stop": pending["stop"], "target": pending["target"], "shares": pending["shares"],
                    "decision": pending["decision"],
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
        if dec.label_before not in accept_labels:
            continue

        # a resting buy-stop order, not an instant fill — see note above
        pending = {
            "decision": dec.label_before,
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


def collect_signals(
    symbol: str, raw_daily: pd.DataFrame, cfg: MarketConfig, start_date: pd.Timestamp,
    strategy=None, market_key: str = "", use_signal_cache: bool = True,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
) -> list:
    """Every bar on which the strategy would have placed an order.

    Unlike backtest_symbol this holds NO position state: it does not skip a
    bar because a previous trade is still open, because in portfolio mode
    that arbitration belongs to the portfolio engine (which knows about
    capital and slot limits), not to the per-symbol scan.
    """
    from .portfolio_sim import Signal

    if strategy is None:
        strategy = get_strategy(DEFAULT_STRATEGY)
    out: list = []
    new_signal_rows: list[tuple] = []
    if raw_daily is None or len(raw_daily) < strategy.min_bars:
        return out

    sim_dates = raw_daily.index[raw_daily.index >= start_date]
    if len(sim_dates) < 2:
        return out

    screened_in = strategy.prefilter_mask(cfg, ind.enrich_daily(raw_daily))

    for current_date in sim_dates:
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
            if len(slice_df) < strategy.min_bars:
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
        # sizing here is only an input to classify (it mirrors the live
        # pipeline); the portfolio engine does the real sizing off current
        # equity, so `too_large` is deliberately NOT a filter at this stage
        sz = sizing.size_position(cfg, plan.entry, plan.stop, vix_above_threshold=False)
        dec = strategy.classify(ctx, result, plan, sz, None, False)
        if dec.label_before not in accept_labels:
            continue

        out.append(Signal(
            date=current_date, symbol=symbol, setup=plan.setup,
            entry=plan.entry, stop=plan.stop, target=plan.target,
            decision=dec.label_before, quality=dec.setup_quality,
            meta=strategy.signal_meta(ctx, result, plan),
        ))

    _save_signals(new_signal_rows)
    return out


RANK_MODES = ("setup", "momentum", "vol_scaled", "random")


def rerank_signals(
    signals: "list[Signal]", prices: dict[str, pd.DataFrame], kind: str = "setup",
    seed: int = 20260101,
) -> "list[Signal]":
    """Overwrite `Signal.quality` with a cross-sectional score.

    Why this exists: once the cash constraint is fixed, the position cap is what
    binds -- the full-universe India donchian run declined 63,383 signals for
    want of a slot against 109 for want of cash. Every taken trade scored
    identically on the strategy's own 5-level `setup_quality`, so ties fell
    through to Python's stable sort and the book filled in scan order, i.e.
    roughly alphabetically. Which signals you take is then doing more work than
    which signals you generate, and nothing was choosing them.

    `setup` keeps the strategy's own score (the default -- no behaviour change).
    `momentum` is 12-1 month total return, the ranking the momentum baseline
    earns its edge from. `vol_scaled` divides that by realised volatility.
    `random` is the control: if an informative ranking does not beat a seeded
    coin flip, the ranking is not the lever after all.

    Scores are computed strictly from bars at or before each signal's own date,
    so this cannot leak future information.
    """
    if kind == "setup":
        return signals
    if kind not in RANK_MODES:
        raise ValueError(f"unknown rank mode {kind!r}, choose from {RANK_MODES}")

    if kind == "random":
        import random as _random
        rng = _random.Random(seed)
        return [dc_replace(s, quality=rng.random()) for s in signals]

    # one score series per symbol, then a point-in-time lookup per signal
    scores: dict[str, pd.Series] = {}
    for sym, df in prices.items():
        if df is None or df.empty or "close" not in df:
            continue
        c = df["close"].astype(float)
        # 12-1: skip the most recent ~21 sessions, the short-term reversal month
        mom = c.shift(21) / c.shift(252) - 1.0
        if kind == "vol_scaled":
            vol = c.pct_change().rolling(126).std()
            mom = mom / vol.replace(0.0, pd.NA)
        scores[sym] = mom

    out: list = []
    missing = 0
    for sig in signals:
        ser = scores.get(sig.symbol)
        val = None
        if ser is not None and sig.date in ser.index:
            v = ser.at[sig.date]
            if pd.notna(v):
                val = float(v)
        if val is None:
            missing += 1
            # unrankable goes last, never first -- an unknown score must not
            # win a slot by accident
            val = float("-inf")
        out.append(dc_replace(sig, quality=val))
    if missing:
        logger.info("rerank(%s): %d of %d signals had no score, ranked last",
                    kind, missing, len(signals))
    return out


def filter_weak_groups(signals: "list", market_key: str, min_rs: int) -> tuple[list, dict]:
    """Drop signals whose industry group was rated below `min_rs` on the signal's own date.

    A portfolio-level filter, like `--rank-by`: the strategy's rules and its cached signals are unchanged,
    so a run with the filter and one without compare the same signal set. Group RS is the Sectors page's
    rating rebuilt point in time for every signal date (analytics/group_history.py: prices up to that
    day; today's industry classification). A group too small to be rated (fewer than 3 liquid members)
    is kept — unknown is not weak. Industry group rather than sub-industry: the group-strength study found
    the finer level predicted no better, and it carries less classification look-ahead."""
    from ..analytics import group_history
    from ..marketdata import industries
    ind = industries.load(market_key)
    dates = sorted({pd.Timestamp(s.date).date() for s in signals})
    logger.info("Group filter: rating industry groups on %d signal dates (computed once, then stored)...", len(dates))
    ratings = group_history.ensure(market_key, dates)
    kept, dropped, unrated = [], 0, 0
    for s in signals:
        g = (ind.get(s.symbol) or (None, None))[1]
        rs = (ratings.get(pd.Timestamp(s.date).date(), {}).get("industry", {}) or {}).get(g) if g else None
        if rs is None:
            unrated += 1
            kept.append(s)
        elif rs >= min_rs:
            kept.append(s)
        else:
            dropped += 1
    logger.info("Group filter (industry-group RS >= %d): kept %d, dropped %d, unrated %d (kept)", min_rs, len(kept), dropped, unrated)
    return kept, {"min_rs": min_rs, "kept": len(kept), "dropped": dropped, "unrated": unrated}


def _close_trade(pos: dict, exit_date: pd.Timestamp, reason: str, exit_price: float) -> Trade:
    return Trade(
        market=pos["market"], symbol=pos["symbol"], setup=pos["setup"],
        entry_date=pos["entry_date"], entry_price=pos["entry_price"],
        stop=pos["stop"], target=pos["target"], shares=pos["shares"],
        exit_date=exit_date, exit_reason=reason, exit_price=exit_price,
        decision=pos.get("decision", ""),
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
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
) -> pd.DataFrame:
    db.init_schema()
    cfg = MARKETS[market_key]
    strategy = get_strategy(strategy_key)
    start = pd.Timestamp(start_date)
    logger.info("Strategy: %s (%s)", strategy.key, strategy.name)

    candidates = _point_in_time_candidates(cfg, strategy, market_key, start)

    if limit:
        candidates = candidates[:limit]
        logger.info("Capped to %d symbols for this run", len(candidates))

    from ..providers import YFinanceProvider

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
            accept_labels=accept_labels,
        )
        all_trades.extend(trades)
        if (i + 1) % 50 == 0:
            logger.info("Backtested %d/%d symbols, %d trades so far", i + 1, len(candidates), len(all_trades))

    logger.info("Done: %d trades across %d symbols", len(all_trades), len(candidates))
    return trades_to_df(all_trades)


def collect_portfolio_signals(
    market_key: str, cfg: MarketConfig, strategy, start: pd.Timestamp,
    candidates: list[str], deep_data: dict | None = None,
    use_signal_cache: bool = True,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
):
    """Scan every candidate once and return (signals, enriched price frames).

    Separated from the simulation so several exit policies (or position
    caps) can be compared against the SAME signal set — otherwise each
    variant would re-scan, and any difference in the scan would confound
    the comparison."""
    deep_data = deep_data or {}
    all_signals = []
    prices: dict[str, pd.DataFrame] = {}
    for i, sym in enumerate(candidates):
        raw = deep_data.get(sym)
        if raw is None:
            raw = cache.load_cached(market_key, sym)
        sigs = collect_signals(
            sym, raw, cfg, start, strategy=strategy, market_key=market_key,
            use_signal_cache=use_signal_cache, accept_labels=accept_labels,
        )
        if sigs:
            all_signals.extend(sigs)
            # enriched, not raw: the exit policies read atr14/sma50 off the bar
            prices[sym] = ind.enrich_daily(raw)
        _progress(f"scanning history: {i + 1:,}/{len(candidates):,} symbols · {len(all_signals):,} signals so far")
        if (i + 1) % 100 == 0:
            logger.info(
                "Scanned %d/%d symbols, %d signals so far",
                i + 1, len(candidates), len(all_signals),
            )
    logger.info("Collected %d signals across %d symbols", len(all_signals), len(prices))
    if not all_signals:
        raise ValueError("no signals produced — nothing to simulate")
    return all_signals, prices


def sample_candidates(
    candidates: list[str], n: int | None, seed: int = 20260101,
    include: "list[str] | None" = None,
) -> list[str]:
    """A seeded random subset.

    `--limit` slices the first N, which is universe-file order and therefore
    roughly alphabetical — a biased sample (sector and listing-age effects
    cluster by name). Full-universe runs over a 14-year window cost ~9 hours
    because build_context is re-run per bar, so a random subset is often the
    practical choice; it needs to be unbiased and reproducible."""
    import random

    pool = set(candidates)
    # `include` is ADDITIVE on top of the seeded draw, not a replacement for
    # part of it: that keeps the sample directly comparable to a previous run
    # of the same size, and keeps its signals cached.
    forced = [s for s in (include or []) if s in pool]
    missing = [s for s in (include or []) if s not in pool]
    if missing:
        logger.warning("--include symbols not in the candidate pool: %s", ", ".join(missing))

    if not n or n >= len(candidates):
        return sorted(pool)
    rng = random.Random(seed)
    picked = set(rng.sample(sorted(candidates), n)) | set(forced)
    logger.info(
        "Sampled %d of %d candidates (seed %d)%s",
        len(picked), len(candidates), seed,
        f" + forced {', '.join(forced)}" if forced else "",
    )
    return sorted(picked)


def _point_in_time_candidates(
    cfg: MarketConfig, strategy, market_key: str, start: pd.Timestamp
) -> list[str]:
    """Symbols that would have been screened in on AT LEAST ONE bar in the
    window -- not the ones that pass today.

    Selecting on today's row leaks the present into the past: a stock that
    trended all through the window but is consolidating now (low ADX today)
    gets dropped from the whole simulation, discarding trades the live
    screener would genuinely have taken. Measured on US data, selecting on
    today's row silently excluded 1,421 of 2,544 real candidates.
    """
    tickers = universe.load_universe(market_key)
    logger.info(
        "Universe: %d tickers; applying the pre-filter POINT-IN-TIME over the window...",
        len(tickers),
    )
    candidates: list[str] = []
    excluded_today = 0
    for i, sym in enumerate(tickers):
        _progress(f"selecting candidates point in time: {i + 1:,}/{len(tickers):,} symbols · {len(candidates):,} qualify")
        raw = cache.load_cached(market_key, sym)
        if raw is None or len(raw) < 260:
            continue
        enriched = ind.enrich_daily(raw)
        mask = strategy.prefilter_mask(cfg, enriched)
        if bool(mask[mask.index >= start].any()):
            candidates.append(sym)
            if not bool(strategy.passes_prefilter(cfg, enriched)[0]):
                excluded_today += 1
    logger.info(
        "Pre-filter (%s): %d/%d symbols qualify on >=1 bar in the window",
        strategy.key, len(candidates), len(tickers),
    )
    logger.info(
        "  of those, %d would have been MISSED by selecting on today's row",
        excluded_today,
    )
    return candidates


def run_portfolio_backtest(
    market_key: str, start_date: str, limit: int | None = None,
    deep_lookback_days: int = 1000, use_signal_cache: bool = True,
    strategy_key: str = DEFAULT_STRATEGY,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
    max_positions: int | None = None,
    exit_policy=None,
    sample: int | None = None,
    include: list[str] | None = None,
    refresh_history: bool = False,
    risk_pct: float | None = None,
    max_position_pct: float | None = None,
    rank_by: str = "setup",
    min_group_rs: int | None = None,
    min_rs: int | None = None,
    use_market_filter: bool = False,
    spec_costs: bool = False,
    max_open_risk_pct: float | None = None,
    max_adv_pct: float | None = None,
):
    """Portfolio-level backtest: one capital pool, a position cap and costs.

    `min_rs`, `use_market_filter`, `spec_costs`, `max_open_risk_pct` and `max_adv_pct` are the
    Minervini spec's portfolio rules (backtesting/spec.py); `rank_by="rs"` is its PF-03 ranking.

    Returns (trades_df, Performance, PortfolioResult)."""
    from . import spec as spec_mod
    from . import metrics
    from .portfolio_sim import ExitPolicy, simulate, trades_to_df as p_trades_to_df

    policy = exit_policy or ExitPolicy()

    db.init_schema()
    cfg = MARKETS[market_key]
    # Sizing overrides, so a sweep's winning (risk, cap) pair can be carried
    # into a full run without editing the market config. `max_positions` x
    # `max_position_pct` can exceed 100% of capital, in which case the book
    # runs out of cash before it runs out of slots -- see the sizing sweep.
    if risk_pct is not None or max_position_pct is not None:
        import dataclasses as _dc
        cfg = _dc.replace(
            cfg,
            risk_pct=cfg.risk_pct if risk_pct is None else risk_pct,
            max_position_pct=(cfg.max_position_pct if max_position_pct is None
                              else max_position_pct),
        )
        logger.info("Sizing override: risk_pct=%.3f%% max_position_pct=%.0f%%",
                    cfg.risk_pct * 100, cfg.max_position_pct * 100)
    strategy = get_strategy(strategy_key)
    start = pd.Timestamp(start_date)
    logger.info("Strategy: %s (%s)", strategy.key, strategy.name)

    _progress("selecting point-in-time candidates")
    candidates = _point_in_time_candidates(cfg, strategy, market_key, start)
    candidates = sample_candidates(candidates, sample, include=include) if sample else (
        candidates[:limit] if limit else candidates
    )

    deep_data: dict = {}
    if refresh_history:
        from ..providers import YFinanceProvider
        deep_data = refresh_deep_history(
            YFinanceProvider(), market_key, candidates, deep_lookback_days,
            start=start, warmup_bars=strategy.min_bars,
        )

    all_signals, prices = collect_portfolio_signals(
        market_key, cfg, strategy, start, candidates, deep_data,
        use_signal_cache=use_signal_cache, accept_labels=accept_labels,
    )
    spec_notes = []
    # the base count runs before any filter: a base counts whether or not its breakout was tradable
    if any(s.meta.get("base_id") is not None for s in all_signals):
        all_signals = spec_mod.base_numbers(all_signals, prices, market_key, strategy.key)
    if min_rs is not None:
        all_signals, r = spec_mod.filter_min_rs(all_signals, market_key, min_rs)
        spec_notes.append(f"RS rating (TT-08): signals from stocks rated below {min_rs} (1-99 across the tradable universe "
                          f"on the signal date) skipped: {r['below']} below, {r['unrated']} outside the rated universe, {r['kept']} kept.")
    if use_market_filter and all_signals:
        all_signals, m = spec_mod.market_filter(all_signals, market_key)
        spec_notes.append(f"Market filter (MKT-01): {m['blocked']} signals blocked on days the benchmark was below its "
                          f"200-day average or its 50-day was below its 200-day (open on {m['days_open_pct']}% of days).")
    if spec_costs:
        all_signals = spec_mod.annotate_costs(all_signals, prices, market_key)
    if rank_by == "rs":
        all_signals = spec_mod.rank_rs_then_tightness(all_signals)
        logger.info("Ranked %d signals by RS, then tightness", len(all_signals))
    elif rank_by != "setup":
        all_signals = rerank_signals(all_signals, prices, rank_by)
        logger.info("Re-ranked %d signals by '%s' for slot competition",
                    len(all_signals), rank_by)
    if not all_signals:
        raise ValueError("no signals left after the portfolio filters — nothing to simulate")
    _progress(f"{len(all_signals):,} signals after filters · simulating the portfolio day by day")
    group_note = None
    if min_group_rs is not None:
        all_signals, g = filter_weak_groups(all_signals, market_key, min_group_rs)
        group_note = (f"Group filter: signals whose industry group was rated below RS {g['min_rs']} on the signal date were "
                      f"skipped ({g['dropped']} dropped, {g['kept']} kept, of which {g['unrated']} in groups too small to rate). "
                      "Group RS is rebuilt point in time from prices; the industry classification is today's.")

    sim_kw = {}
    if spec_costs:
        sim_kw.update(cost_bps=spec_mod.COST_BPS[market_key], slippage_bps=spec_mod.SLIPPAGE_BPS[market_key])
    result = simulate(
        all_signals, prices, cfg, start,
        max_positions=max_positions, exit_policy=policy,
        max_open_risk_pct=max_open_risk_pct, max_adv_pct=max_adv_pct, **sim_kw,
    )
    tdf = p_trades_to_df(result.trades)

    bench_raw = cache.load_cached(market_key, cfg.benchmark_ticker)
    bench_close = None
    if bench_raw is not None and not bench_raw.empty:
        bench_close = bench_raw["close"].reindex(result.equity.index).ffill()

    cap = max_positions if max_positions is not None else cfg.max_open_positions
    notes = [
        "SURVIVORSHIP BIAS: the universe is today's listed names, so companies "
        "delisted or acquired during the window are absent entirely. This "
        "flatters results and cannot be fixed without point-in-time constituent data.",
        (f"Costs modelled (spec C-01/C-02): {spec_mod.COST_BPS[market_key]:g}bps charges plus "
         f"{spec_mod.SLIPPAGE_BPS[market_key]:g}bps slippage per side, {spec_mod.ILLIQUID_SLIPPAGE_BPS[market_key]:g}bps "
         "for stocks trading less than the illiquid threshold a day." if spec_costs else
         f"Costs modelled: {cfg.slippage_bps:.0f}bps slippage per side plus "
         f"{cfg.currency_symbol}{cfg.commission_per_order:.2f} per order. Real spreads on "
         "thin names can exceed this."),
        "Signals are generated and filled on daily bars; intraday path within a bar "
        "is unknown, so a bar touching both stop and target is scored as a stop.",
        f"{result.signals_seen} signals were generated; {result.signals_taken} were taken, "
        f"{result.signals_missed_no_slot} passed up with all {cap} slots full, "
        f"{result.signals_missed_no_cash} for insufficient cash.",
        f"Exit policy: {policy.label()}.",
    ] + ([group_note] if group_note else []) + spec_notes + (
        [f"Skipped at the fill: " + ", ".join(f"{v} {k}" for k, v in sorted(result.skipped.items(), key=lambda x: -x[1])) + "."]
        if result.skipped else [])
    perf = metrics.compute(
        equity=result.equity, positions_open=result.positions_open, trades=tdf,
        max_open_positions=cap, costs_paid=result.costs_paid,
        bench_close=bench_close, notes=notes,
    )
    return tdf, perf, result


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
            "decision": t.decision,
        }
        for t in trades
    ]
    cols = [
        "market", "symbol", "setup", "entry_date", "entry_price", "stop", "target",
        "exit_date", "exit_reason", "exit_price", "shares", "pnl", "pct_return",
        "r_multiple", "holding_days", "decision",
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


def main(argv: list[str] | None = None) -> dict | None:
    """CLI entry point. `argv` lets the `backtest` job (jobs/registry.py) run it in-process with the
    same arguments the command line would take; the portfolio branch returns {run_dir, trades, perf}
    so the job can record a result line."""
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
        "--accept-labels", default="TRADE - HIGH CONFIDENCE",
        help="comma-separated classify() labels to take as entries (default only "
        "'TRADE - HIGH CONFIDENCE'). Add 'TRADE ON TRIGGER' to test whether the "
        "confidence tiers actually separate outcomes -- the resulting CSV carries a "
        "`decision` column so the two can be compared within a single run.",
    )
    parser.add_argument(
        "--no-signal-cache", action="store_true",
        help="recompute gates/setup from scratch instead of reusing backtest_signals — use this "
        "when you've changed a strategy's gate logic, not just trade-sim params "
        "(stop buffer, risk/R thresholds, pending-order expiry) which don't need it",
    )
    parser.add_argument(
        "--per-symbol", action="store_true",
        help="use the OLD per-symbol simulation (unlimited capital, no costs, no "
        "position cap). Kept for comparison only -- its aggregate P&L is not "
        "achievable in a real account, so the portfolio mode is the default.",
    )
    parser.add_argument(
        "--max-positions", type=int, default=None,
        help="cap on simultaneously held positions (default: the market config's)",
    )
    parser.add_argument(
        "--exit-mode", default="bracket", choices=["bracket", "trail_atr", "ma", "donchian", "minervini"],
        help="how open positions are managed. 'bracket' is the strategy's fixed "
        "stop+target; the others test whether letting winners run beats capping them. "
        "'minervini' is the spec's EX-01..EX-07 (research/minervini-backtest-spec.md).",
    )
    parser.add_argument("--spec", action="store_true",
                        help="the Minervini spec's portfolio rules: --exit-mode minervini, 8 positions, RS rating >= 70, "
                             "RS-then-tightness ranking, 6%% open-risk cap, 5%% traded-value cap and the spec's costs "
                             "(each can still be overridden by its own flag)")
    parser.add_argument("--min-rs", type=int, default=None, help="skip signals whose RS rating (1-99, cross-sectional) is below this")
    parser.add_argument("--market-filter", action="store_true", help="MKT-01: no new buys while the benchmark is below its 200-day")
    parser.add_argument("--max-open-risk", type=float, default=None, help="PF-04: cap on open risk, %% of equity")
    parser.add_argument("--max-adv-pct", type=float, default=None, help="SL-06: largest order, %% of 50-day traded value")
    parser.add_argument("--partial-r", type=float, default=None, help="minervini exits: sell a third at this R (0 = off; default 3)")
    parser.add_argument("--fail-days", type=int, default=None, help="minervini exits: failed-breakout window (default 5; 0 = off)")
    parser.add_argument("--time-stop", type=int, default=None, help="minervini exits: EX-07 after this many sessions (default off)")
    parser.add_argument(
        "--no-target", action="store_true",
        help="drop the fixed profit target so winners can run (use with a trailing exit mode)",
    )
    parser.add_argument(
        "--sample", type=int, default=None,
        help="simulate a seeded RANDOM subset of N candidates (unbiased, reproducible). "
        "Prefer this over --limit, which slices alphabetically.",
    )
    parser.add_argument(
        "--include", default="",
        help="comma-separated symbols to force into the sample, in ADDITION to "
        "the seeded draw (keeps the run comparable to one without it)",
    )
    parser.add_argument(
        "--refresh-history", action="store_true",
        help="deep-refresh candidates from yfinance first (skip if backfill already ran)",
    )
    parser.add_argument("--atr-mult", type=float, default=3.0, help="for --exit-mode trail_atr")
    parser.add_argument("--ma-col", default="sma50", help="for --exit-mode ma")
    parser.add_argument("--donchian-bars", type=int, default=50, help="for --exit-mode donchian")
    parser.add_argument("--risk-pct", type=float, default=None,
                        help="risk per trade as a fraction, e.g. 0.005 (default: market config)")
    parser.add_argument("--min-group-rs", type=int, default=None,
                        help="skip signals whose industry group's RS rating (1-99, rebuilt point in time) was below this "
                             "on the signal date — e.g. 50 to avoid weak groups")
    parser.add_argument("--rank-by", default="setup", choices=list(RANK_MODES) + ["rs"],
                        help="how to rank signals competing for a slot. 'setup' "
                             "(default) keeps the strategy's own score; 'momentum' "
                             "is 12-1 month return; 'random' is the control")
    parser.add_argument("--max-position-pct", type=float, default=None,
                        help="notional cap per position as a fraction, e.g. 0.10 "
                             "(default: market config). max_positions x this should "
                             "not exceed 1.0, or the book runs out of cash before slots")
    parser.add_argument("--no-ingest", action="store_true",
                    help="skip updating the viewer database after the run")

    args = parser.parse_args(argv)
    labels = tuple(x.strip() for x in args.accept_labels.split(",") if x.strip())
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if args.per_symbol:
        df = run_backtest(
            args.market, args.start, args.limit, args.deep_lookback_days,
            use_signal_cache=not args.no_signal_cache, strategy_key=args.strategy,
            accept_labels=labels,
        )
        out_path = REPORT_DIR / f"{args.market}_{args.strategy}_persymbol_{args.start}.csv"
        df.to_csv(out_path, index=False)
        print(f"\nWrote {len(df)} trades to {out_path}\n")
        print_summary(df, MARKETS[args.market].currency_symbol)
        print(
            "\nNOTE: per-symbol mode assumes unlimited capital and zero costs. "
            "Run without --per-symbol for an achievable portfolio result."
        )
        return None

    from . import metrics

    cfg = MARKETS[args.market]
    from .portfolio_sim import ExitPolicy

    from . import spec as spec_mod
    from ..strategies import minervini_spec as ms
    if args.spec:
        if args.exit_mode == "bracket":
            args.exit_mode, args.no_target = "minervini", True
        if args.max_positions is None:
            args.max_positions = ms.MAX_POSITIONS
        if args.min_rs is None:
            args.min_rs = 70
        if args.rank_by == "setup":
            args.rank_by = "rs"
        if args.max_open_risk is None:
            args.max_open_risk = ms.MAX_OPEN_RISK_PCT
        if args.max_adv_pct is None:
            args.max_adv_pct = ms.MAX_ADV_PCT
    extra = {k: v for k, v in (("partial_r", args.partial_r), ("fail_days", args.fail_days),
                               ("time_stop_days", args.time_stop)) if v is not None}
    policy = ExitPolicy(
        mode=args.exit_mode, use_target=not args.no_target,
        atr_mult=args.atr_mult, ma_col=args.ma_col, donchian_bars=args.donchian_bars, **extra,
    )
    tdf, perf, result = run_portfolio_backtest(
        args.market, args.start, args.limit, args.deep_lookback_days,
        use_signal_cache=not args.no_signal_cache, strategy_key=args.strategy,
        accept_labels=labels, max_positions=args.max_positions, exit_policy=policy,
        sample=args.sample, refresh_history=args.refresh_history,
        include=[x.strip() for x in args.include.split(",") if x.strip()],
        risk_pct=args.risk_pct, max_position_pct=args.max_position_pct,
        rank_by=args.rank_by, min_group_rs=args.min_group_rs,
        min_rs=args.min_rs, use_market_filter=args.market_filter, spec_costs=args.spec,
        max_open_risk_pct=args.max_open_risk / 100 if args.max_open_risk is not None else None,
        max_adv_pct=args.max_adv_pct / 100 if args.max_adv_pct is not None else None,
    )
    from ..paths import run_dir

    run = f"{args.start}_{policy.label()}"
    if args.risk_pct is not None:
        run += f"_risk{args.risk_pct * 100:g}pct"
    if args.max_position_pct is not None:
        run += f"_cap{args.max_position_pct * 100:g}pct"
    if args.rank_by != "setup":
        run += f"_rank{args.rank_by}"
    if args.min_group_rs is not None:
        run += f"_grp{args.min_group_rs}"
    if args.spec:
        run += "_spec"
    elif args.min_rs is not None:
        run += f"_rs{args.min_rs}"
    if args.market_filter:
        run += "_mkt"
    if args.accept_labels != "TRADE - HIGH CONFIDENCE":
        run += "_" + "+".join("".join(w[0] for w in x.split() if w[0].isalpha()) for x in labels)
    run += f"_sample{args.sample}" if args.sample else ""
    # The strategy's version and parameter fingerprint belong in the run name:
    # without them a result cannot be traced to the rules that produced it, and
    # two versions of the same strategy silently overwrite each other's reports.
    run += f"_{get_strategy(args.strategy).spec_id()}"
    out = run_dir(args.market, args.strategy, run)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({
        "equity": result.equity, "cash": result.cash,
        "positions_open": result.positions_open,
        "drawdown_pct": metrics.drawdown_series(result.equity) * 100,
    }).to_csv(out / "equity.csv")
    print()
    print(metrics.format_report(
        perf, cfg.currency_symbol,
        args.max_positions if args.max_positions is not None else cfg.max_open_positions,
    ))
    print(f"\nRun dir -> {out}")

    _bench = cache.load_cached(args.market, cfg.benchmark_ticker)
    _bench_c = (
        _bench["close"].reindex(result.equity.index).ffill()
        if _bench is not None and not _bench.empty else None
    )

    # markdown report with charts, alongside the CSVs
    try:
        from . import report as report_mod

        cmd = (
            f"python3 -m swing_screener.backtesting.backtest --market {args.market} "
            f"--start {args.start} --strategy {args.strategy}"
            + (f" --sample {args.sample}" if args.sample else "")
            + (f" --max-positions {args.max_positions}" if args.max_positions else "")
            + (f" --exit-mode {args.exit_mode}" if args.exit_mode != "bracket" else "")
            + (" --no-target" if args.no_target else "")
            + (f" --ma-col {args.ma_col}" if args.exit_mode == "ma" else "")
            + (f" --rank-by {args.rank_by}" if args.rank_by != "setup" else "")
            + (f" --min-group-rs {args.min_group_rs}" if args.min_group_rs is not None else "")
            + (" --spec" if args.spec else (f" --min-rs {args.min_rs}" if args.min_rs is not None else ""))
            + (" --market-filter" if args.market_filter else "")
            + (f" --accept-labels '{args.accept_labels}'" if args.accept_labels != "TRADE - HIGH CONFIDENCE" else "")
            + (f" --partial-r {args.partial_r:g}" if args.partial_r is not None else "")
            + (f" --fail-days {args.fail_days}" if args.fail_days is not None else "")
            + (f" --time-stop {args.time_stop}" if args.time_stop is not None else "")
        )
        spec_md = None
        if args.exit_mode == "minervini" or args.spec:
            spec_md = spec_mod.breakdown(tdf, result.equity, cfg.currency_symbol)
            n_gap = spec_mod.trades_over_suspect_gaps(tdf, args.market)
            spec_md += (f"\n\nData check: {n_gap} of {len(tdf)} trades were held across a split-shaped gap that is still in "
                        "the source's own price history (marketdata/splits.py) — a likely false crash.\n")
        md = report_mod.write_report(
            out,
            f"{cfg.name} — {get_strategy(args.strategy).name}, {args.start} onward",
            perf, result.equity, result.positions_open, tdf,
            cfg.currency_symbol,
            args.max_positions if args.max_positions is not None else cfg.max_open_positions,
            _bench_c, cmd,
            extra_sections=[("Breakdown (spec section 13)", spec_md)] if spec_md else None,
        )
        print(f"Report  -> {md}")
        if spec_md:
            print(spec_md)
    except Exception as e:  # a chart failure must not lose the run's results
        logger.warning("markdown report not generated (%s: %s)", type(e).__name__, e)
    print()
    print(metrics.format_equity_curve(result.equity, _bench_c))

    # index the new report so the viewer shows it without a server restart
    if not getattr(args, "no_ingest", False):
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return {"run_dir": out, "trades": len(tdf), "perf": perf}


if __name__ == "__main__":
    main()
