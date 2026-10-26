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
import inspect
import json
import math
import logging
import os
import time
from dataclasses import dataclass, replace as dc_replace
from pathlib import Path

import pandas as pd

from ..marketdata import asof, cache, corporate_actions, db, universe

from ..core import indicators as ind, sizing
from ..core import context as ctx_mod
from ..core.context import StockContext
from ..config import MarketConfig, MARKETS
from ..strategies import DEFAULT_STRATEGY, StrategyResult, get_strategy, list_strategies

logger = logging.getLogger("backtest")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

from ..paths import REPORTS_DIR as REPORT_DIR  # noqa: F401
from . import funnel as funnel_mod

# Live progress hook. The `backtest` job (jobs/registry.py) points this at its run-log step so the
# Runs page shows movement during a long run ("scanned 1,200/2,148 symbols…"); the CLI leaves it
# unset and relies on the logger. Callers may invoke it per item — the consumer throttles.
on_progress = None


def _progress(text: str, *, done: int | None = None, total: int | None = None) -> None:
    if on_progress:
        on_progress(text, done=done, total=total)


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
            f"WHERE market=%s AND strategy=%s AND symbol=%s AND date=%s "
            # a row written by a different version of the rules is not a hit: it
            # describes detections the current code would not make
            f"AND spec_id = %s",
            (market_key, strategy.key, symbol, date.date(), strategy.spec_id()),
        )
        row = cur.fetchone()
    if row is None:
        return None
    vals = dict(zip(_SIGNAL_FIELDS, row))
    result = _cached_result(strategy, vals)
    if result is None:
        return None
    ctx = _cached_ctx(market_key, symbol, date, vals, tail=True)
    return (ctx, result) if ctx is not None else None


def _cached_signal_rows(market_key: str, strategy, symbol: str, start: pd.Timestamp) -> dict:
    """{date: row} of every cached signal row of this symbol under the current spec_id from `start`
    on — one query per symbol instead of one per bar, which is what a warm scan mostly waited on.

    A symbol with no rows of its own takes its peers' (_signal_peers: the same signal_id, so the same
    rows) first, copied under this spec_id so the run's record is its own, as seed_signal_cache does."""
    q = (f"SELECT date, {', '.join(_SIGNAL_FIELDS)} FROM backtest_signals "
         f"WHERE market=%s AND strategy=%s AND symbol=%s AND spec_id=%s AND date >= %s")
    args = (market_key, strategy.key, symbol, strategy.spec_id(), start.date())
    with db.get_connection().cursor() as cur:
        cur.execute(q, args)
        rows = cur.fetchall()
        peers = [] if rows else _signal_peers(market_key, strategy)
        if peers:
            cols = "market, strategy, symbol, date, " + ", ".join(_SIGNAL_FIELDS)
            cur.execute(
                f"INSERT INTO backtest_signals ({cols}, spec_id) "
                f"SELECT DISTINCT ON (date) {cols}, %s FROM backtest_signals "
                f"WHERE market=%s AND strategy=%s AND symbol=%s AND spec_id = ANY(%s) "
                f"ORDER BY date, array_position(%s::text[], spec_id::text) "
                f"ON CONFLICT (market, strategy, symbol, date, spec_id) DO NOTHING",
                (strategy.spec_id(), market_key, strategy.key, symbol, peers, peers),
            )
            if cur.rowcount:
                cur.execute(q, args)
                rows = cur.fetchall()
    return {pd.Timestamp(r[0]): dict(zip(_SIGNAL_FIELDS, r[1:])) for r in rows}


def _cached_result(strategy, vals: dict) -> "StrategyResult | None":
    """The StrategyResult a cached row records, or None when the row cannot stand in for a scan."""
    # A strategy whose build_plans() reads ctx.extras cannot use a row written
    # before extras were persisted: rebuilding from it yields an empty extras
    # dict and the strategy silently emits no signals. Treat that as a miss.
    if getattr(strategy, "needs_ctx_extras", False) and not vals.get("extras"):
        return None
    # ...nor one written before the strategy recorded something it now reads
    if not strategy.cached_signal_ok(vals.get("extras") or {}):
        return None
    return StrategyResult(
        first_hard_fail=vals["first_failed_gate"],
        hard_gates=vals.get("hard_gates") or {},
        setups=vals["setups"] or {},
        entry_setup_codes=strategy.setup_codes,
        watch_flags=vals["watch_flags"] or {}, watch_notes=vals["watch_notes"] or {},
    )


def _cached_ctx(market_key: str, symbol: str, date: pd.Timestamp, vals: dict, tail: bool) -> "StockContext | None":
    """The StockContext of a cached row. `tail` loads the daily tail the entry and plan read; a bar that
    stops before them (a gate failed, no setup) needs none, so the scan skips that query (None = the
    tail is too short: recompute the bar)."""
    if tail:
        daily = cache.load_cached_with_indicators(market_key, symbol, date, tail=70)
        if daily is None or len(daily) < 15:
            return None  # not enough tail data cached for entry/demand-supply math — recompute fresh
    else:
        daily = pd.DataFrame()
    # weekly/monthly are intentionally empty on the cache-hit path: nothing
    # between here and the trade decision reads them. If a strategy ever
    # does, it must not use the signal cache (or this must be widened).
    return StockContext(
        symbol=symbol, daily=daily, weekly=pd.DataFrame(), monthly=pd.DataFrame(),
        h_value=vals["h_value"], h_index=pd.Timestamp(vals["h_index"]) if vals["h_index"] else None,
        l_value=vals["l_value"], p_value=vals["p_value"], prior_swing_low=vals["prior_swing_low"],
        overhead=vals["overhead_levels"] or [], history_months=24,  # unused downstream of a cache hit
        extras=dict(vals.get("extras") or {}),
    )


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
        strategy.spec_id(),
    )


def _save_signals(rows: list[tuple]) -> None:
    if not rows:
        return
    try:
        _upsert_signals(rows, db.signal_conflict_target())
    except Exception as exc:  # noqa: BLE001
        # the key moved between reading it and writing (db.ensure_signal_key swapping it
        # mid-run): re-read it once rather than lose the rows or the run
        if "ON CONFLICT" not in str(exc):
            raise
        _upsert_signals(rows, db.signal_conflict_target())


def _upsert_signals(rows: list[tuple], target: str) -> None:
    query = f"""
        INSERT INTO backtest_signals
            (market, strategy, symbol, date, hard_gates_passed, first_failed_gate,
             hard_gates, has_setup, setups, h_value, h_index, l_value, p_value,
             prior_swing_low, overhead_levels, watch_flags, watch_notes, extras, spec_id)
        VALUES %s
        ON CONFLICT {target} DO UPDATE SET
            -- EVERY column, not a subset. Leaving has_setup, hard_gates_passed and
            -- the swing structure out left a row claiming the new spec_id while
            -- carrying the old version's values: NVDA came back with MV-04 true on
            -- 31 rows and has_setup false on 30 of them, because has_setup was
            -- written before the cheats existed and never refreshed. That makes a
            -- row internally inconsistent -- fresh setups beside a stale context --
            -- and every diagnostic that reads has_setup silently wrong.
            hard_gates_passed=EXCLUDED.hard_gates_passed,
            first_failed_gate=EXCLUDED.first_failed_gate,
            hard_gates=EXCLUDED.hard_gates, has_setup=EXCLUDED.has_setup,
            setups=EXCLUDED.setups,
            h_value=EXCLUDED.h_value, h_index=EXCLUDED.h_index,
            l_value=EXCLUDED.l_value, p_value=EXCLUDED.p_value,
            prior_swing_low=EXCLUDED.prior_swing_low,
            overhead_levels=EXCLUDED.overhead_levels,
            watch_flags=EXCLUDED.watch_flags, watch_notes=EXCLUDED.watch_notes,
            extras=EXCLUDED.extras, spec_id=EXCLUDED.spec_id
    """
    db.execute_values(query, rows)


def seed_signal_cache(
    market_key: str, strategy, source_spec: str, start: pd.Timestamp, symbols: list[str] | None = None,
) -> int:
    """Copy `source_spec`'s cached signal rows under this strategy's own spec_id, from `start` on.

    Only for a source with the same `signal_id` -- a `--const` variant whose overrides beyond the
    source's are all `signal_exempt_consts`, which evaluate() never reads -- so each copied row is
    exactly the row this variant's own scan would write, and the scan then reads it as an ordinary
    hit. Copied rather than shared, so everything keyed on a run's spec_id (the trade-anatomy
    overlay, a re-run of this variant) finds its own rows. Existing rows are kept. Returns the
    number copied."""
    if source_spec == strategy.spec_id():
        return 0
    with db.get_connection().cursor() as cur:
        if not db.signal_key_has_spec(cur):
            return 0   # one row per bar: a copy would overwrite the source
    cols = ("market, strategy, symbol, date, hard_gates_passed, first_failed_gate, hard_gates, has_setup, "
            "setups, h_value, h_index, l_value, p_value, prior_swing_low, overhead_levels, watch_flags, "
            "watch_notes, extras")
    t0 = time.time()
    with db.get_connection().cursor() as cur:
        cur.execute(
            f"INSERT INTO backtest_signals ({cols}, spec_id) "
            f"SELECT {cols}, %s FROM backtest_signals "
            f"WHERE market=%s AND strategy=%s AND spec_id=%s AND date >= %s "
            f"AND (%s::text[] IS NULL OR symbol = ANY(%s::text[])) "
            f"ON CONFLICT (market, strategy, symbol, date, spec_id) DO NOTHING",
            (strategy.spec_id(), market_key, strategy.key, source_spec, start.date(), symbols, symbols),
        )
        n = cur.rowcount
    logger.info("Signal cache: seeded %d rows from %s (same signal_id %s) in %.0fs",
                n, source_spec, strategy.signal_id(), time.time() - t0)
    return n


def record_signal_spec(market_key: str, strategy) -> None:
    """Record the signal_id this spec's cached rows are written under (backtest_signal_specs), so a
    later spec with the same signal_id — a version bump that kept `signal_version`, a `--const` variant
    of post-scan constants, or the shipped rules after such a variant — finds them as its peers
    (_signal_peers) and starts from their rows instead of rescanning."""
    with db.get_connection().cursor() as cur:
        cur.execute(
            "INSERT INTO backtest_signal_specs (market, strategy, spec_id, signal_id) VALUES (%s, %s, %s, %s) "
            "ON CONFLICT (market, strategy, spec_id) DO UPDATE SET signal_id = EXCLUDED.signal_id, seen_at = now()",
            (market_key, strategy.key, strategy.spec_id(), strategy.signal_id()),
        )
    _PEERS.pop((market_key, strategy.key, strategy.spec_id()), None)


_PEERS: dict = {}   # (market, strategy, spec_id) -> the other spec ids with its signal_id


def _signal_peers(market_key: str, strategy) -> list[str]:
    """Other spec ids whose cached rows are exactly this spec's (same signal_id), newest first."""
    k = (market_key, strategy.key, strategy.spec_id())
    if k not in _PEERS:
        with db.get_connection().cursor() as cur:
            cur.execute(
                "SELECT spec_id FROM backtest_signal_specs WHERE market=%s AND strategy=%s AND signal_id=%s "
                "AND spec_id <> %s ORDER BY seen_at DESC",
                (market_key, strategy.key, strategy.signal_id(), strategy.spec_id()),
            )
            _PEERS[k] = [r[0] for r in cur.fetchall()]
    return _PEERS[k]


def backtest_symbol(
    symbol: str, raw_daily: pd.DataFrame, cfg: MarketConfig, start_date: pd.Timestamp,
    strategy=None, market_key: str = "", use_signal_cache: bool = True,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
) -> list[Trade]:
    if strategy is None:
        strategy = get_strategy(DEFAULT_STRATEGY)
    trades: list[Trade] = []
    new_signal_rows: list[tuple] = []
    if raw_daily is None or len(raw_daily) < strategy.min_bars:
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
    fn: "funnel.Funnel | None" = None,
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

    # Enrich once per symbol, not once per bar: build_context used to re-derive the
    # daily/weekly/monthly frames on every qualifying bar of a growing slice, which
    # is quadratic and was ~89% of a scan. tests/test_context_frames.py checks the
    # sliced context is identical to the rebuilt one.
    frames = ctx_mod.prepare_frames(raw_daily)
    screened_in = strategy.prefilter_mask(cfg, frames.daily)
    cached_rows = (_cached_signal_rows(market_key, strategy, symbol, sim_dates[0])
                   if (use_signal_cache and market_key) else {})

    for current_date in sim_dates:
        if not bool(screened_in.get(current_date, False)):
            continue
        if fn:
            fn.reached("bars", symbol=symbol)

        # a cache hit: the same row _load_cached_signal reads, with the price tail loaded only for a
        # bar that reaches the entry and plan (the rest never read ctx.daily)
        cached = None
        vals = cached_rows.get(current_date)
        if vals is not None:
            result = _cached_result(strategy, vals)
            if result is not None:
                ctx = _cached_ctx(market_key, symbol, current_date, vals,
                                  tail=result.hard_gates_passed and result.has_setup)
                cached = (ctx, result) if ctx is not None else None
        if cached is not None:
            ctx, result = cached
        else:
            bars_so_far = int(raw_daily.index.searchsorted(current_date, side="right"))
            if bars_so_far < strategy.min_bars:
                if fn:
                    fn.dropped("bars", "not enough history yet", symbol=symbol)
                continue
            try:
                ctx = ctx_mod.build_context(symbol, raw_daily, earnings_days_away=None,
                                            frames=frames, as_of=current_date)
            except Exception:
                if fn:
                    fn.dropped("bars", "context could not be built", symbol=symbol)
                continue
            if ctx is None:
                if fn:
                    fn.dropped("bars", "context could not be built", symbol=symbol)
                continue
            try:
                result = strategy.evaluate(ctx)
            except Exception:
                if fn:
                    fn.dropped("bars", "the strategy raised while evaluating", symbol=symbol)
                continue
            if market_key:
                new_signal_rows.append(
                    _signal_row(market_key, strategy, symbol, current_date, ctx, result)
                )

        if not result.hard_gates_passed:
            if fn:
                fn.dropped("bars", f"hard gate {result.first_hard_fail}"
                           if result.first_hard_fail else "a hard gate", symbol=symbol)
            continue
        if fn:
            fn.reached("hard_gates", symbol=symbol)
        if not result.has_setup:
            # the strategy's own code for an incomplete setup (minervini records
            # the VCP gate that refused); otherwise just "no setup"
            if fn:
                fn.dropped("hard_gates", ctx.extras.get("vcp_fail") or "no setup formed", symbol=symbol)
            continue
        if fn:
            fn.reached("setup", symbol=symbol)
        if not strategy.entry_signal_fired(ctx, result):
            if fn:
                fn.dropped("setup", "entry trigger did not fire", symbol=symbol)
            continue
        if fn:
            fn.reached("entry", symbol=symbol)
        choice = strategy.build_plans(ctx, result, cfg)
        plan = choice.chosen
        if plan is None or not plan.is_valid:
            # choice.reason is the rule that refused, in its own words -- this
            # is where a reward-to-risk minimum shows up
            if fn:
                fn.dropped("entry", choice.reason if plan is None else "plan not valid", symbol=symbol)
            continue
        if fn:
            fn.reached("plan", symbol=symbol)
        # sizing here is only an input to classify (it mirrors the live
        # pipeline); the portfolio engine does the real sizing off current
        # equity, so `too_large` is deliberately NOT a filter at this stage
        sz = sizing.size_position(cfg, plan.entry, plan.stop, vix_above_threshold=False)
        dec = strategy.classify(ctx, result, plan, sz, None, False)
        if dec.label_before not in accept_labels:
            if fn:
                fn.dropped("plan", f'decision was "{dec.label_before}", not accepted'
                           if dec.label_before else "no decision", symbol=symbol)
            continue
        if fn:
            fn.reached("accepted", symbol=symbol)

        out.append(Signal(
            date=current_date, symbol=symbol, setup=plan.setup,
            entry=plan.entry, stop=plan.stop, target=plan.target,
            decision=dec.label_before, quality=dec.setup_quality,
            meta=strategy.signal_meta(ctx, result, plan),
        ))

    _save_signals(new_signal_rows)
    return out


RANK_MODES = ("setup", "momentum", "vol_scaled", "random", "setup_momentum")
# Bounded below the smallest gap between any strategy's setup-quality levels (0.5 today), so the
# tie-break can reorder exact ties and nothing else.
TIEBREAK_SCALE = 1e-3


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
    `setup_momentum` KEEPS the strategy's own score and uses 12-1 momentum only to
    break exact ties. The other modes replace the score, which throws away a
    strategy's own ordering (a confirmed breakout over an unconfirmed one, a
    flag's penalty); this keeps it and removes only the alphabetical fallback.

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
        if kind == "setup_momentum":
            # the strategy's score decides; momentum only orders an exact tie, squashed into
            # (0, TIEBREAK_SCALE) so it can never cross a gap between quality levels. Unknown
            # momentum adds nothing, so it sorts below every known one at the same level.
            if val is None:
                missing += 1
                tb = 0.0
            else:
                tb = TIEBREAK_SCALE * (math.atan(val) / math.pi + 0.5)
            out.append(dc_replace(sig, quality=float(sig.quality) + tb))
            continue
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


def filter_stage3(signals: "list", market_key: str, prices: dict) -> tuple[list, dict]:
    """Drop signals whose stock had already left Stage 2 for Stage 3 (topping) on the signal date.

    A portfolio-level filter, like `--min-group-rs`: the strategy's rules and its cached signals are
    unchanged, so a run with it and one without compare the same signal set.

    The Trend Template and the stage machine disagree about this more often than it looks, because
    they read different things: the template's 200-day test lags, while the stage machine leaves
    Stage 2 on a lower swing low or the 150-day ceasing to rise -- "swings turn before averages".
    A stock can therefore be structurally topping while still passing all eight gates. Measured on
    the v1.20 runs, that is 24.8% of Indian trades and 31.9% of US ones, losing in both at a profit
    factor of 0.80 and 0.83; Minervini's instruction is to buy Stage 2, not Stage 3.

    Not lookahead: `stage_cycle` records the 2->3 switch on the bar the swing low is CONFIRMED
    (i - _stage_swing_bars), not on the swing low itself, so the stage on a bar is decided only by
    bars up to it.

    A symbol without enough history to stage is KEPT -- unknown is not topping.
    """
    import numpy as np

    from ..config import MARKETS
    from ..strategies.minervini_spec import stage_cycle

    cfg = MARKETS[market_key]
    by: dict = {}
    for s in signals:
        by.setdefault(s.symbol, []).append(s)
    logger.info("Stage filter: staging %d symbols...", len(by))
    kept, dropped, unknown = [], 0, 0
    gone = {"dropped": []}
    for sym, sigs in by.items():
        df = prices.get(sym)
        if df is None or len(df) < 200:
            kept.extend(sigs)
            unknown += len(sigs)
            continue
        # `passes` only feeds each Stage 2 run's `confirmed` date, which this does not read, so a
        # stub skips a per-bar Trend Template evaluation over the whole history.
        runs = stage_cycle(df, cfg, [(False, "")] * len(df))
        stage = np.zeros(len(df), dtype=np.int8)
        idx = df.index
        for r in runs:
            a = int(idx.searchsorted(pd.Timestamp(r["from"])))
            b = int(idx.searchsorted(pd.Timestamp(r["to"]), side="right")) if r.get("to") else len(df)
            stage[a:b] = int(r["stage"])
        for s in sigs:
            i = int(idx.searchsorted(pd.Timestamp(s.date)))
            if i >= len(df) or idx[i] != pd.Timestamp(s.date):
                kept.append(s); unknown += 1; continue
            if stage[i] == 3:
                dropped += 1
                gone["dropped"].append(s)
            else:
                kept.append(s)
    logger.info("Stage filter (no Stage 3): kept %d, dropped %d, unstaged %d (kept)", len(kept), dropped, unknown)
    return kept, {"kept": len(kept), "dropped": dropped, "unknown": unknown, "dropped_signals": gone}


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
    gone = {"dropped": []}
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
            gone["dropped"].append(s)
    logger.info("Group filter (industry-group RS >= %d): kept %d, dropped %d, unrated %d (kept)", min_rs, len(kept), dropped, unrated)
    return kept, {"min_rs": min_rs, "kept": len(kept), "dropped": dropped, "unrated": unrated, "dropped_signals": gone}


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
    signal_source: str | None = None,
) -> pd.DataFrame:
    db.init_schema()
    db.ensure_signal_key()   # a backtest is where no older-code writer can still be running (see db)
    cfg = MARKETS[market_key]
    strategy = get_strategy(strategy_key)
    start = pd.Timestamp(start_date)
    logger.info("Strategy: %s (%s)", strategy.key, strategy.name)

    candidates = _point_in_time_candidates(cfg, strategy, market_key, start)

    if limit:
        candidates = candidates[:limit]
        logger.info("Capped to %d symbols for this run", len(candidates))
    if signal_source and use_signal_cache:
        seed_signal_cache(market_key, strategy, signal_source, start, candidates)
    if use_signal_cache:
        record_signal_spec(market_key, strategy)

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


class NoSignals(ValueError):
    """A run that found nothing. Still carries the funnel: "zero trades" is a
    result, and the only useful thing about it is WHERE the candidates stopped,
    which is exactly what the funnel records. Subclasses ValueError so existing
    callers that catch that keep working."""

    def __init__(self, message: str, funnel=None):
        super().__init__(message)
        self.funnel = funnel


# Filled in the parent, before the pool forks (collect_portfolio_signals / _point_in_time_candidates,
# workers>1): cfg, strategy, start, market_key, plus use_signal_cache, accept_labels, deep_data for
# the scan. Fork gives every worker a read-only copy-on-write view of this for free; only `sym` (a
# string) crosses the pool's IPC pipe per task, not a whole DataFrame/Strategy per call. Same idiom as spec_sensitivity.py's `_DATA`.
_POOL_CTX: dict = {}


# How many scan processes a backtest forks when not told (`--workers`): one per core, at most
# MAX_SCAN_WORKERS, and no more than the memory free at the start holds at SCAN_WORKER_MEM_MB each — a
# worker pushed into swap is slower than none. Measured on the M4 (4 performance + 6 efficiency cores),
# a cold 40-symbol US breakout scan: 1 worker 713s, 4 workers 247s, 6 workers 157s, trades identical;
# the efficiency cores still pay because a scan partly waits on Postgres. Each worker peaked near
# 110 MB (785 MB for the whole tree at 6), so SCAN_WORKER_MEM_MB keeps ~3x headroom for longer
# histories. Speed only: the scan is per symbol and merged in candidate order, so the trades are the
# same for any count (windows._SPEED_ONLY_BT).
MAX_SCAN_WORKERS = 6
SCAN_WORKER_MEM_MB = 350


def _free_memory_mb() -> int | None:
    """Memory the OS can hand out now (free + inactive + speculative pages), or None if unknown."""
    import subprocess
    try:
        out = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        try:
            return os.sysconf("SC_AVPHYS_PAGES") * os.sysconf("SC_PAGE_SIZE") // 2**20
        except (ValueError, OSError, AttributeError):
            return None
    import re
    page = int(m.group(1)) if (m := re.search(r"page size of (\d+) bytes", out)) else 4096
    pages = sum(int(m.group(1)) for k in ("free", "inactive", "speculative")
                if (m := re.search(rf"Pages {k}:\s+(\d+)", out)))
    return pages * page // 2**20 if pages else None


def default_workers() -> int:
    """The scan's process count when `--workers` is not given (see MAX_SCAN_WORKERS)."""
    n = min(os.cpu_count() or 1, MAX_SCAN_WORKERS)
    free = _free_memory_mb()
    if free is not None:
        n = min(n, free // SCAN_WORKER_MEM_MB)
    return max(1, n)


def _pool_worker_init() -> None:
    """Runs once per forked worker, before its first task, so the worker opens its own DB connection
    (db.get_connection() is a module-level singleton — see marketdata/db.py).

    The parent closed its connection before forking (collect_portfolio_signals), so what this drops
    is an already-closed object: dropping a LIVE inherited one would let its finaliser send the
    server a terminate over the socket the parent still shares, ending the parent's session.

    GSSAPI is off for the worker's connect: libpq tries Kerberos encryption by default, and on macOS
    the Kerberos frameworks are not fork-safe — a forked child hangs forever inside connect (every
    worker at 0% CPU, no error). A local Postgres has no use for it."""
    os.environ.setdefault("PGGSSENCMODE", "disable")
    db._connection = None


def _collect_one(sym: str) -> tuple[str, list, "pd.DataFrame | None", "funnel_mod.Funnel"]:
    """One candidate's scan, run in a pool worker. Its own Funnel, so results merge back into the
    caller's in candidate order (Funnel.merge) instead of racing to update a shared one."""
    ctx = _POOL_CTX
    raw = ctx["deep_data"].get(sym)
    if raw is None:
        raw = cache.load_cached(ctx["market_key"], sym)
    fn = funnel_mod.Funnel()
    sigs = collect_signals(
        sym, raw, ctx["cfg"], ctx["start"], strategy=ctx["strategy"], market_key=ctx["market_key"],
        use_signal_cache=ctx["use_signal_cache"], accept_labels=ctx["accept_labels"], fn=fn,
    )
    enriched = ind.enrich_daily(raw) if sigs else None
    # drop_symbols is a defaultdict whose factory is a lambda, which cannot be pickled back to the
    # parent; Funnel.merge only reads it with .items(), so a plain dict of the same content will do.
    fn.drop_symbols = {stage: dict(reasons) for stage, reasons in fn.drop_symbols.items()}
    return sym, sigs, enriched, fn


def collect_portfolio_signals(
    market_key: str, cfg: MarketConfig, strategy, start: pd.Timestamp,
    candidates: list[str], deep_data: dict | None = None,
    use_signal_cache: bool = True,
    accept_labels: tuple[str, ...] = ("TRADE - HIGH CONFIDENCE",),
    fn: "funnel_mod.Funnel | None" = None,
    workers: int = 1,
):
    """Scan every candidate once and return (signals, enriched price frames).

    Separated from the simulation so several exit policies (or position
    caps) can be compared against the SAME signal set — otherwise each
    variant would re-scan, and any difference in the scan would confound
    the comparison.

    `workers` > 1 forks that many processes and scans `workers` symbols at once (each symbol is
    independent, so this is embarrassingly parallel). It pays off on a cold signal cache (e.g. right
    after a strategy version bump), where build_context runs on every bar and the work is CPU-bound,
    and on a warm one too: there a symbol is one read of its cached rows (_cached_signal_rows) plus the
    price tail of each bar that reaches a plan, so a scan is mostly waiting on round trips, which
    overlap across processes. Measured: 4 workers took a warm 40-symbol India scan from 26s to 6s; a
    cold 40-symbol US breakout scan took 713s with 1 worker, 247s with 4 and 157s with 6
    (default_workers)."""
    deep_data = deep_data or {}
    all_signals = []
    prices: dict[str, pd.DataFrame] = {}

    if workers <= 1:
        for i, sym in enumerate(candidates):
            raw = deep_data.get(sym)
            if raw is None:
                raw = cache.load_cached(market_key, sym)
            sigs = collect_signals(
                sym, raw, cfg, start, strategy=strategy, market_key=market_key,
                use_signal_cache=use_signal_cache, accept_labels=accept_labels, fn=fn,
            )
            if sigs:
                all_signals.extend(sigs)
                # enriched, not raw: the exit policies read atr14/sma50 off the bar
                prices[sym] = ind.enrich_daily(raw)
            _progress(f"scanning history: {i + 1:,}/{len(candidates):,} symbols · {len(all_signals):,} signals so far",
                      done=i + 1, total=len(candidates))
            if (i + 1) % 100 == 0:
                logger.info(
                    "Scanned %d/%d symbols, %d signals so far",
                    i + 1, len(candidates), len(all_signals),
                )
    else:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor

        global _POOL_CTX
        _POOL_CTX = dict(
            cfg=cfg, strategy=strategy, start=start, market_key=market_key,
            use_signal_cache=use_signal_cache, accept_labels=accept_labels, deep_data=deep_data,
        )
        logger.info("Scanning %d symbols with %d worker processes", len(candidates), workers)
        # Close, don't share: each worker opens its own (_pool_worker_init), and this process
        # reopens lazily on its next query.
        if db._connection is not None and not db._connection.closed:
            db._connection.close()
        # ProcessPoolExecutor, not multiprocessing.Pool: when a worker dies (a segfault in a C
        # library, the OOM killer) Pool silently waits forever for the lost task, while the executor
        # raises BrokenProcessPool at once — a multi-hour run must fail loudly, not hang at 0% CPU.
        with ProcessPoolExecutor(workers, mp_context=mp.get_context("fork"), initializer=_pool_worker_init) as pool:
            # map yields in candidate order, same as the serial path, so funnel sampling and anything
            # else order-sensitive stay reproducible.
            for i, (sym, sigs, enriched, sub_fn) in enumerate(pool.map(_collect_one, candidates)):
                if fn:
                    fn.merge(sub_fn)
                if sigs:
                    all_signals.extend(sigs)
                    prices[sym] = enriched
                _progress(f"scanning history: {i + 1:,}/{len(candidates):,} symbols · {len(all_signals):,} signals so far",
                          done=i + 1, total=len(candidates))
                if (i + 1) % 100 == 0:
                    logger.info(
                        "Scanned %d/%d symbols, %d signals so far",
                        i + 1, len(candidates), len(all_signals),
                    )
        _POOL_CTX = {}
    logger.info("Collected %d signals across %d symbols", len(all_signals), len(prices))
    if not all_signals:
        raise NoSignals("no signals produced — nothing to simulate", fn)
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


def _prefilter_symbol(
    cfg: MarketConfig, strategy, market_key: str, start: pd.Timestamp, sym: str,
) -> tuple[bool, bool]:
    """(passes the pre-filter on >=1 bar from `start`, but not on today's row) for one symbol."""
    raw = cache.load_cached(market_key, sym)
    if raw is None or len(raw) < 260:
        return False, False
    enriched = ind.enrich_daily(raw)
    mask = strategy.prefilter_mask(cfg, enriched)
    if not bool(mask[mask.index >= start].any()):
        return False, False
    return True, not bool(strategy.passes_prefilter(cfg, enriched)[0])


def _prefilter_one(sym: str) -> tuple[bool, bool]:
    """_prefilter_symbol in a pool worker, its arguments read from _POOL_CTX
    (_point_in_time_candidates, workers>1). Touches no Funnel: the caller sets the
    funnel's counts once, from the merged candidate list."""
    ctx = _POOL_CTX
    return _prefilter_symbol(ctx["cfg"], ctx["strategy"], ctx["market_key"], ctx["start"], sym)


_CODE_SIG: list = []


def _prefilter_key(cfg: MarketConfig, strategy, market_key: str, start: pd.Timestamp) -> str:
    """What a stored pre-filter answer depends on besides the symbol's prices: the strategy's spec id
    (every constant), the market config (a --min-dollar-volume override changes it), the window, and the
    source of the packages the pre-filter runs (strategies, screens, core indicators, config) — a code
    change without a version bump must not replay old answers."""
    import hashlib
    from .. import paths
    if not _CODE_SIG:
        h = hashlib.sha256()
        for pkg in ("strategies", "screens", "core", "config"):
            for f in sorted((paths.SCRIPTS_DIR / "swing_screener" / pkg).rglob("*.py")):
                h.update(f.name.encode() + f.read_bytes())
        h.update(inspect.getsource(_prefilter_symbol).encode())
        _CODE_SIG.append(h.hexdigest())
    blob = "|".join([strategy.key, strategy.spec_id(), repr(cfg), str(start.date()), str(asof.end_date()), _CODE_SIG[0]])
    return hashlib.sha256(blob.encode()).hexdigest()[:24]


def _price_sigs(market_key: str) -> dict[str, str]:
    """{symbol: fingerprint of its stored prices up to the stage's end}, in one query. Exact numeric
    sums, not float ones, so the fingerprint cannot drift with the order a parallel aggregate adds in."""
    end = asof.end_date()
    with db.get_connection().cursor() as cur:
        cur.execute(
            "SELECT symbol, count(*), min(date), max(date), sum(round(close::numeric, 6)), "
            "sum(round(high::numeric, 6)), sum(round(low::numeric, 6)), "
            "sum(round(open::numeric, 6)), sum(volume::numeric) FROM prices WHERE market=%s"
            + (" AND date <= %s" if end else "") + " GROUP BY symbol",
            (market_key, end) if end else (market_key,),
        )
        return {r[0]: "|".join(map(str, r[1:])) for r in cur.fetchall()}


def _point_in_time_candidates(
    cfg: MarketConfig, strategy, market_key: str, start: pd.Timestamp,
    fn: "funnel_mod.Funnel | None" = None,
    workers: int = 1,
) -> list[str]:
    """Symbols that would have been screened in on AT LEAST ONE bar in the
    window -- not the ones that pass today.

    Selecting on today's row leaks the present into the past: a stock that
    trended all through the window but is consolidating now (low ADX today)
    gets dropped from the whole simulation, discarding trades the live
    screener would genuinely have taken. Measured on US data, selecting on
    today's row silently excluded 1,421 of 2,544 real candidates.

    `workers` > 1 pre-filters that many symbols at once in forked processes (same pattern
    as collect_portfolio_signals); the candidate list comes back in universe order, identical
    to the serial path (workers=1, the default).
    """
    tickers = universe.load_universe(market_key)
    logger.info(
        "Universe: %d tickers; applying the pre-filter POINT-IN-TIME over the window...",
        len(tickers),
    )
    candidates: list[str] = []
    excluded_today = 0
    # Answers stored by an earlier run with the same rules, window and prices (backtest_prefilter_cache):
    # only the symbols whose prices changed since, or never seen, are pre-filtered again.
    key, sigs = _prefilter_key(cfg, strategy, market_key, start), _price_sigs(market_key)
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT symbol, data_sig, qualifies, missed_today FROM backtest_prefilter_cache "
                    "WHERE market=%s AND key=%s", (market_key, key))
        known = {r[0]: (r[2], r[3]) for r in cur.fetchall() if sigs.get(r[0]) == r[1]}
    todo = [t for t in tickers if t not in known]
    logger.info("Pre-filter: %d of %d symbols answered by the stored pre-filter, %d to compute",
                len(tickers) - len(todo), len(tickers), len(todo))
    fresh: dict[str, tuple[bool, bool]] = {}
    if workers <= 1:
        for i, sym in enumerate(todo):
            _progress(f"selecting candidates point in time: {i + 1:,}/{len(todo):,} symbols",
                      done=i + 1, total=len(todo))
            fresh[sym] = _prefilter_symbol(cfg, strategy, market_key, start, sym)
    elif todo:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor

        global _POOL_CTX
        _POOL_CTX = dict(cfg=cfg, strategy=strategy, market_key=market_key, start=start)
        logger.info("Pre-filtering %d symbols with %d worker processes", len(tickers), workers)
        # Same fork discipline as collect_portfolio_signals: close the parent's connection so no
        # worker inherits a live one, fork-safe init per worker, and an executor that fails loudly.
        if db._connection is not None and not db._connection.closed:
            db._connection.close()
        with ProcessPoolExecutor(workers, mp_context=mp.get_context("fork"), initializer=_pool_worker_init) as pool:
            # map keeps universe order, so `candidates` is the same list the serial path builds.
            # chunksize batches the IPC round trips: one symbol is only a few milliseconds of work.
            results = pool.map(_prefilter_one, todo, chunksize=16)
            for i, (sym, res) in enumerate(zip(todo, results)):
                fresh[sym] = res
                _progress(f"selecting candidates point in time: {i + 1:,}/{len(todo):,} symbols",
                          done=i + 1, total=len(todo))
        _POOL_CTX = {}
    if fresh:
        from psycopg2.extras import execute_values
        with db.get_connection().cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO backtest_prefilter_cache (market, key, symbol, data_sig, qualifies, missed_today) VALUES %s "
                "ON CONFLICT (market, key, symbol) DO UPDATE SET data_sig = EXCLUDED.data_sig, "
                "qualifies = EXCLUDED.qualifies, missed_today = EXCLUDED.missed_today, seen_at = now()",
                [(market_key, key, sym, sigs.get(sym, ""), bool(q), bool(m)) for sym, (q, m) in fresh.items()],
            )
    for sym in tickers:   # universe order, whichever way each answer came
        qualifies, missed_today = known[sym] if sym in known else fresh[sym]
        if qualifies:
            candidates.append(sym)
            excluded_today += missed_today
    logger.info(
        "Pre-filter (%s): %d/%d symbols qualify on >=1 bar in the window",
        strategy.key, len(candidates), len(tickers),
    )
    if fn:
        fn.set_count("symbols", len(tickers))
        fn.set_count("candidates", len(candidates))
        fn.set_symbols("candidates", candidates)
        if len(candidates) <= funnel_mod.Funnel.MAX_NAMED:
            fn.symbols = list(candidates)
        fn.drop_symbols["symbols"]["never passed the pre-filter in the window"] = set(
            sorted(set(tickers) - set(candidates))[: funnel_mod.Funnel.MAX_DROP_NAMES])
        fn.dropped("symbols", "never passed the pre-filter in the window",
                   len(tickers) - len(candidates))
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
    block_stage3: bool = False,
    min_rs: int | None = None,
    max_base_no: int | None = None,
    top_dollar_volume: int | None = None,
    min_dollar_volume: float | None = None,
    pyramid_frac: float | None = None,
    pyramid_add_pct: float = 2.0,
    use_market_filter: bool = False,
    mkt_confirm: int = 0,
    market_guide: bool = False,
    results_blackout_days: int | None = None,
    exposure: "portfolio_sim.Exposure | None" = None,
    spec_costs: bool = False,
    max_open_risk_pct: float | None = None,
    max_adv_pct: float | None = None,
    only_symbols: list[str] | None = None,
    fundamentals: str | None = None,
    workers: int = 1,
    signal_source: str | None = None,
):
    """Portfolio-level backtest: one capital pool, a position cap and costs.

    `fundamentals` ("covered" / "acceptable" / "leader") applies Minervini's SEPA fundamental tests
    to each signal from the results public on its date (backtesting/fundamental_filter.py).

    `min_rs`, `use_market_filter`, `spec_costs`, `max_open_risk_pct` and `max_adv_pct` are the
    Minervini spec's portfolio rules (backtesting/spec.py); `rank_by="rs"` is its PF-03 ranking.

    `workers` fans the point-in-time candidate selection (_point_in_time_candidates) and the
    symbol scan (collect_portfolio_signals) out across forked processes. Both gain, on a cold
    signal cache or a warm one (see those functions' docstrings).

    Returns (trades_df, Performance, PortfolioResult)."""
    from . import spec as spec_mod
    from . import metrics
    from .portfolio_sim import ExitPolicy, simulate, trades_to_df as p_trades_to_df

    policy = exit_policy or ExitPolicy()

    db.init_schema()
    db.ensure_signal_key()   # a backtest is where no older-code writer can still be running (see db)
    cfg = MARKETS[market_key]
    # Sizing overrides, so a sweep's winning (risk, cap) pair can be carried
    # into a full run without editing the market config. `max_positions` x
    # `max_position_pct` can exceed 100% of capital, in which case the book
    # runs out of cash before it runs out of slots -- see the sizing sweep.
    if min_dollar_volume is not None:
        import dataclasses as _dc
        cfg = _dc.replace(cfg, screener=_dc.replace(cfg.screener, min_dollar_volume=min_dollar_volume))
        logger.info("Traded-value floor overridden: %s%,.0f/day", cfg.currency_symbol, min_dollar_volume)
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
    fn = funnel_mod.Funnel()
    candidates = _point_in_time_candidates(cfg, strategy, market_key, start, fn=fn, workers=workers)
    if only_symbols:
        want = {s.strip().upper() for s in only_symbols if s and s.strip()}
        missing = sorted(w for w in want if w not in {c.upper() for c in candidates})
        candidates = [c for c in candidates if c.upper() in want]
        logger.info("Restricted to %d requested symbol(s): %s", len(candidates), ", ".join(candidates) or "none")
        if missing:
            logger.warning("  not in the point-in-time candidate set (no qualifying bar in the window): %s",
                           ", ".join(missing))
        # attribute the cut, or it shows up as "not attributed to a named rule"
        dropped_by_request = int(fn.counts.get("candidates", 0)) - len(candidates)
        if dropped_by_request > 0:
            fn.dropped("symbols", "not in --symbols", dropped_by_request)
        fn.set_count("candidates", len(candidates))
        fn.set_symbols("candidates", candidates)
        fn.symbols = list(candidates)
    candidates = sample_candidates(candidates, sample, include=include) if sample else (
        candidates[:limit] if limit else candidates
    )
    if signal_source and use_signal_cache:
        seed_signal_cache(market_key, strategy, signal_source, start, candidates)
    if use_signal_cache:
        record_signal_spec(market_key, strategy)

    deep_data: dict = {}
    if refresh_history:
        from ..providers import YFinanceProvider
        deep_data = refresh_deep_history(
            YFinanceProvider(), market_key, candidates, deep_lookback_days,
            start=start, warmup_bars=strategy.min_bars,
        )

    all_signals, prices = collect_portfolio_signals(
        market_key, cfg, strategy, start, candidates, deep_data,
        use_signal_cache=use_signal_cache, accept_labels=accept_labels, fn=fn, workers=workers,
    )
    spec_notes = []
    # the base count runs before any filter: a base counts whether or not its breakout was tradable
    if any(s.meta.get("base_id") is not None for s in all_signals):
        all_signals = spec_mod.base_numbers(all_signals, prices, market_key, strategy.key)
    if max_base_no is not None:
        all_signals, b = spec_mod.filter_max_base_no(all_signals, max_base_no)
        spec_notes.append(
            f"Base number: only the first {max_base_no} bases of a stock's advance are traded "
            f"({b['late']} signals dropped as late-stage, {b['kept']} kept"
            + (f", {b['unknown']} had no base number and were kept)." if b["unknown"] else ")."))
        fn.dropped_each("accepted", f"base number above {max_base_no}", b["dropped_signals"]["late"])
    if min_rs is not None:
        all_signals, r = spec_mod.filter_min_rs(all_signals, market_key, min_rs)
        spec_notes.append(f"RS rating (TT-08): signals from stocks rated below {min_rs} (1-99 across the tradable universe "
                          f"on the signal date) skipped: {r['below']} below, {r['unrated']} outside the rated universe, {r['kept']} kept.")
        fn.dropped_each("accepted", f"RS rating below {min_rs}", r["dropped_signals"]["below"])
        fn.dropped_each("accepted", "outside the rated universe", r["dropped_signals"]["unrated"])
    if top_dollar_volume and all_signals:
        all_signals, tdv = spec_mod.filter_top_dollar_volume(all_signals, market_key, top_dollar_volume)
        fn.dropped_each("accepted", f"outside the {top_dollar_volume} most-traded stocks", tdv["dropped_signals"]["outside"])
        spec_notes.append(
            f"Traded-value rank: only signals whose stock was among the {top_dollar_volume} most-traded "
            f"by 50-day average value ON THE SIGNAL DATE ({tdv['kept']} kept, {tdv['outside']} outside). "
            "A rank, not a dollar floor, so it means the same thing in 2010 as in 2026; it stands in for "
            "index membership, which cannot be reconstructed point in time here.")
    regime_ok = spec_mod.market_ok(market_key, mkt_confirm, market_guide) if use_market_filter else None
    if use_market_filter and all_signals:
        all_signals, m = spec_mod.market_filter(all_signals, market_key, mkt_confirm, market_guide)
        if market_guide:
            from ..strategies import minervini_spec as _ms
            fn.dropped_each("accepted", "market filter: index or breadth weak", m["dropped_signals"]["blocked"])
            spec_notes.append(
                f"Market filter (the SEPA guide's): {m['blocked']} signals blocked on days the benchmark closed below "
                f"its {_ms.MKT_INDEX_SMA}-day average, or breadth (stocks above their 50-day) was at or below "
                f"{_ms.MKT_BREADTH_MIN_PCT:g}% and not higher than {_ms.MKT_BREADTH_RISING_DAYS} sessions earlier "
                f"(open on {m['days_open_pct']}% of days).")
        else:
            fn.dropped_each("accepted", "market filter: benchmark below its 200-day", m["dropped_signals"]["blocked"])
            spec_notes.append(f"Market filter (MKT-01): {m['blocked']} signals blocked on days the benchmark was below its "
                              f"200-day average or its 50-day was below its 200-day (open on {m['days_open_pct']}% of days).")
    if results_blackout_days and all_signals:
        all_signals, rb = spec_mod.results_blackout(all_signals, market_key, results_blackout_days)
        fn.dropped_each("accepted", f"results due within {results_blackout_days} days", rb["dropped_signals"]["blocked"])
        spec_notes.append(
            f"Results blackout: {rb['blocked']} signals skipped with results filed within {results_blackout_days} days "
            f"after the signal; results dates known for {rb['covered_symbols']} of {rb['of_symbols']} signalled stocks "
            "(the rest are never blocked).")
    if fundamentals and all_signals:
        from . import fundamental_filter
        all_signals, f = fundamental_filter.filter_signals(all_signals, market_key, fundamentals)
        v = f["verdicts"]
        fn.dropped_each("accepted", f"SEPA fundamentals below '{fundamentals}'", f["dropped_signals"]["below"])
        spec_notes.append(
            f"Fundamentals (SEPA part 2, level '{fundamentals}'): each signal judged on the quarterly results public on its "
            f"date; {f['kept']} of {f['of']} kept. Verdicts: " + ", ".join(f"{n} {k}" for k, n in sorted(v.items(), key=lambda x: -x[1]))
            + ". NO DATA means no scorable results then (fundamental history starts in 2021, for part of the universe); "
              "F7 (estimates) is never available point in time.")
    elif all_signals:
        # No fundamentals GATE, but every trade still records what the company's results looked like
        # on its signal date, so the report can be cut by verdict. Annotation only: nothing is dropped
        # and no trade changes, which is why it runs whether or not --fundamentals was asked for.
        from . import fundamental_filter
        all_signals, f = fundamental_filter.annotate_signals(all_signals, market_key)
        v = f["verdicts"]
        spec_notes.append(
            "Fundamentals (SEPA part 2): recorded, not enforced — each signal keeps the verdict its company's "
            f"results supported on its own date, and none was dropped for it. Verdicts: "
            + ", ".join(f"{n} {k}" for k, n in sorted(v.items(), key=lambda x: -x[1]))
            + ". NO DATA means no scorable results then (Indian history starts late 2020, US in 2009, and only "
              "for part of the universe); F7 (estimates) is never available point in time.")
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
        raise NoSignals("no signals left after the portfolio filters — nothing to simulate", fn)
    fn.set_count("ranked", len(all_signals))
    fn.set_symbols("ranked", [s.symbol for s in all_signals])
    _progress(f"{len(all_signals):,} signals after filters · simulating the portfolio day by day")
    group_note = None
    if block_stage3 and all_signals:
        all_signals, s3 = filter_stage3(all_signals, market_key, prices)
        fn.dropped_each("ranked", "stock already in Stage 3 (topping)", s3["dropped_signals"]["dropped"])
        spec_notes.append(
            f"Stage filter: {s3['dropped']} signals skipped because the stage machine had the stock in "
            f"Stage 3 (topping) on the signal date -- it leaves Stage 2 on a lower swing low or the "
            f"150-day ceasing to rise, which the Trend Template's 200-day test lags. "
            f"{s3['unknown']} signals could not be staged and were kept.")
    if min_group_rs is not None:
        all_signals, g = filter_weak_groups(all_signals, market_key, min_group_rs)
        fn.dropped_each("ranked", f"industry group rated below RS {g['min_rs']}", g["dropped_signals"]["dropped"])
        group_note = (f"Group filter: signals whose industry group was rated below RS {g['min_rs']} on the signal date were "
                      f"skipped ({g['dropped']} dropped, {g['kept']} kept, of which {g['unrated']} in groups too small to rate). "
                      "Group RS is rebuilt point in time from prices; the industry classification is today's.")

    sim_kw = {}
    if spec_costs:
        sim_kw.update(cost_bps=spec_mod.COST_BPS[market_key], slippage_bps=spec_mod.SLIPPAGE_BPS[market_key])
    credits = corporate_actions.Credits.for_market(market_key, list(prices))
    spec_notes.append(credits.note())
    result = simulate(
        all_signals, prices, cfg, start,
        max_positions=max_positions, exit_policy=policy,
        max_open_risk_pct=max_open_risk_pct, max_adv_pct=max_adv_pct,
        pyramid_frac=pyramid_frac, pyramid_add_pct=pyramid_add_pct,
        exposure=exposure, regime_ok=regime_ok, credits=credits, **sim_kw,
    )
    tdf = p_trades_to_df(result.trades)
    # what the simulator refused: slots, cash, and the per-fill checks it records
    fn.set_count("taken", len(result.trades))
    fn.set_symbols("taken", [t.symbol for t in result.trades])
    # each with the symbol and the session it was refused on, so a stored run can answer
    # "why didn't CRWD trade?" without a replay
    fn.dropped_each("ranked", "all position slots full", result.missed_slot_at)
    fn.dropped_each("ranked", "not enough cash", result.missed_cash_at)
    for _reason, _at in result.skipped_at.items():
        fn.dropped_each("ranked", _reason, _at)
    result.funnel = fn

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
        bench_close=bench_close, cash=result.cash, notes=notes,
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


def _exposure_from(args):
    """PE-01..PE-04 from the command line, or None when --pe was not asked for."""
    if not getattr(args, "pe", False):
        return None
    from .portfolio_sim import Exposure
    return Exposure(enabled=True, window=args.pe_window, warmup=args.pe_warmup,
                    pilot_frac=args.pe_pilot, press_net_r=args.pe_press)



def _portfolio_suffix(args, cfg) -> str:
    """Run-name parts for the portfolio limits that change a result.

    A run is filed under its name, so every input that changes the trades has to be in it, or two
    different runs share a directory and the later one silently replaces the earlier -- with the
    stored report then describing the wrong configuration. `--max-positions`, `--max-open-risk`,
    `--max-adv-pct` and `--max-base` were missing: a `--max-positions 4` run overwrote the default
    run it was meant to be compared against, and `--max-base 1` and `--max-base 2` named the same
    directory.

    A part is added only when the value differs from the default the run would have used anyway
    (spec mode fills these from the strategy's constants), so existing runs keep their names.
    """
    from ..strategies import minervini_spec as ms
    spec = bool(getattr(args, "spec", False))
    parts = []
    default = ms.MAX_POSITIONS if spec else cfg.max_open_positions
    if args.max_positions is not None and args.max_positions != default:
        parts.append(f"_mp{args.max_positions}")
    default = ms.MAX_OPEN_RISK_PCT if spec else None
    if args.max_open_risk is not None and args.max_open_risk != default:
        parts.append(f"_or{args.max_open_risk:g}")
    default = ms.MAX_ADV_PCT if spec else None
    if args.max_adv_pct is not None and args.max_adv_pct != default:
        parts.append(f"_adv{args.max_adv_pct:g}")
    if getattr(args, "max_base", None) is not None:
        parts.append(f"_maxbase{args.max_base}")
    return "".join(parts)

def main(argv: list[str] | None = None) -> dict | None:
    """CLI entry point. `argv` lets the `backtest` job (jobs/registry.py) run it in-process with the
    same arguments the command line would take; the portfolio branch returns {run_dir, trades, perf}
    so the job can record a result line."""
    parser = argparse.ArgumentParser(description="Walk-forward backtest")
    parser.add_argument("--market", choices=list(MARKETS.keys()), required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--limit", type=int, default=None, help="cap number of symbols tested")
    parser.add_argument(
        "--workers", type=int, default=None, metavar="N",
        help="pre-filter and scan N symbols at once in forked processes (portfolio mode; "
        "--per-symbol stays single-process). Speeds up the point-in-time candidate selection "
        "and the signal scan, on a cold signal cache or a warm one; the trades do not change. "
        f"Default: one per core, at most {MAX_SCAN_WORKERS}, fewer if free memory is short "
        "(default_workers). 1 scans in this process.",
    )
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
        "--exit-mode", default="bracket", choices=["bracket", "trail_atr", "ma", "weekly_ma", "donchian", "supertrend", "minervini"],
        help="how open positions are managed. 'bracket' is the strategy's fixed "
        "stop+target; the others test whether letting winners run beats capping them. "
        "'weekly_ma' sells at a week's last close when that week closes below the --ma-weeks average of weekly closes. "
        "'supertrend' sells at the close that turns the Supertrend down (the supertrend strategy's ATR_PERIOD and MULTIPLIER). "
        "'minervini' is the spec's EX-01..EX-07 (research/minervini-backtest-spec.md).",
    )
    parser.add_argument("--spec", action="store_true",
                        help="the Minervini spec's portfolio rules: --exit-mode minervini, 8 positions, RS rating >= 70, "
                             "RS-then-tightness ranking, 6%% open-risk cap, 5%% traded-value cap and the spec's costs "
                             "(each can still be overridden by its own flag)")
    parser.add_argument("--min-rs", type=int, default=None, help="skip signals whose RS rating (1-99, cross-sectional) is below this")
    parser.add_argument("--market-filter", action="store_true",
                        help="no new buys in a risk-off market. With --spec, the minervini strategy's own test "
                             "(the SEPA guide's: index above its 50-day and breadth healthy); otherwise MKT-01, "
                             "the benchmark below its 200-day")
    parser.add_argument("--mkt01", action="store_true",
                        help="with --spec --market-filter: use MKT-01 (the 200-day test, minervini 1.7) instead of the guide's")
    parser.add_argument("--results-blackout", type=int, default=None, metavar="DAYS",
                        help="skip signals with results filed within DAYS after the signal date "
                             "(--spec default: the strategy's EARNINGS_BLACKOUT_DAYS; 0 = off)")
    parser.add_argument("--max-open-risk", type=float, default=None, help="PF-04: cap on open risk, %% of equity")
    parser.add_argument("--max-adv-pct", type=float, default=None, help="SL-06: largest order, %% of 50-day traded value")
    parser.add_argument("--partial-r", type=float, default=None,
                        help="minervini exits: also sell a part at this R, as 1.7 did at 3 (default off)")
    parser.add_argument("--strength-ext", type=float, default=None, metavar="PCT",
                        help="minervini exits: sell a part once the close is PCT%% above the 50-day "
                             "(default: the strategy's STRENGTH_EXT_PCT; 0 = off)")
    parser.add_argument("--climax-full", action="store_true",
                        help="minervini exits: a climax run sells the whole position (1.7) rather than a part")
    parser.add_argument("--trend-volume", action="store_true",
                        help="minervini exits: the 50-day trend exit needs above-average volume (1.7)")
    parser.add_argument("--fail-days", type=int, default=None,
                        help="minervini exits: failed-breakout window (default: the strategy's FAIL_DAYS, 0 = off; 1.7 used 5)")
    # Exposed so the exit ladder can be TESTED rather than argued about. The
    # breakeven stop is the sharpest suspect: trades exiting on it reached a
    # median 2.75R while held and realised -0.04R, i.e. it converts winners
    # into scratches, and it was the one rule with no flag.
    parser.add_argument("--breakeven-r", type=float, default=None,
                        help="raise the stop to breakeven (entry + round-trip costs) once the high reaches "
                             "entry + this x R, from the next session. minervini exits: EX-03 (0 = off; default: "
                             "the strategy's BREAKEVEN_R); any other exit mode: off unless given (exit reason BREAKEVEN)")
    # Trade management for the shared exit modes, all opt-in so they can be MEASURED against the
    # fixed bracket rather than assumed: a chart_pattern trade (ICICIBANK, 2017) came within 2.5% of
    # its measured target and then gave it all back over 167 days to a full -1R stop.
    parser.add_argument("--time-stop-bars", type=int, default=None, metavar="N",
                        help="non-minervini exits: sell at the close of the Nth session after the entry "
                             "(exit reason TIME); with --time-stop-mult, the fallback for a signal with no duration")
    parser.add_argument("--time-stop-mult", type=float, default=None, metavar="X",
                        help="non-minervini exits: time stop at X times the setup's duration in bars, for a "
                             "signal that carries its start (chart_pattern: the pattern's first key point)")
    parser.add_argument("--partial-at-target", type=float, default=None, metavar="FRAC",
                        help="non-minervini exits: sell FRAC of the position at the target and trail the rest "
                             "(bracket: --atr-mult x ATR14 under its highest close; a trailing mode keeps its own)")
    parser.add_argument("--no-trend-volume", action="store_true",
                        help="minervini exits: let a trend break fire without volume confirmation (the default since 1.8)")
    parser.add_argument("--no-climax", action="store_true",
                        help="minervini exits: disable the climax (sell into strength) rule")
    parser.add_argument("--time-stop", type=int, default=None,
                        help="minervini exits: EX-07, sold if +1R is not reached within this many sessions "
                             "(default: the strategy's TIME_STOP_DAYS; 0 = off)")
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
        "--symbols", default="",
        help="comma-separated symbols to restrict the ENTIRE run to, e.g. --symbols NVDA,MU,GOOG. "
             "The point-in-time pre-filter still applies to each, so this shows what the strategy "
             "would have done on those names and nothing else. Unlike --include it is a restriction, "
             "not an addition. Note the RS filter ranks a signal against the universe present in the "
             "run, so on a handful of symbols that ranking is not meaningful.",
    )
    parser.add_argument(
        "--pe", action="store_true",
        help="progressive exposure (PE-01..PE-04): enter at a pilot size while the recent record is "
             "not paying, full size once it is. Sizing is read once per session from trades closed on "
             "EARLIER sessions, so today's stop-out cannot resize today's entry.",
    )
    parser.add_argument("--pe-window", type=int, default=10, metavar="N",
                        help="PE-01: closed trades in the rolling window (default 10; test 5-20)")
    parser.add_argument("--pe-warmup", type=int, default=5, metavar="N",
                        help="PE-02: pilot size until this many trades have closed (default 5)")
    parser.add_argument("--pe-pilot", type=float, default=0.5, metavar="FRAC",
                        help="PE-02: fraction of --risk-pct at pilot size (default 0.5; test 0.33-0.66)")
    parser.add_argument("--pe-press", type=float, default=None, metavar="NET_R",
                        help="PE-04, off by default: net R over the window that unlocks 1.25x risk and "
                             "two extra position slots (the spec suggests +4)")
    parser.add_argument("--top-dollar-volume", type=int, default=None, metavar="N",
                        help="keep only signals whose stock was among the N most-traded (50-day average "
                             "value) on the signal date. A rank rather than --min-dollar-volume's absolute "
                             "floor, so it carries the same meaning across the whole window.")
    parser.add_argument("--mkt-confirm", type=int, default=0, metavar="N",
                        help="with --market-filter: sessions MKT-01 must hold before risk-on resumes, so the "
                             "gate does not flap around the 200-day (test 1-10). Risk-off still bites at once.")
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
    parser.add_argument("--ma-weeks", type=int, default=30,
                        help="for --exit-mode weekly_ma: weeks in the simple average of weekly closes")
    parser.add_argument("--donchian-bars", type=int, default=50, help="for --exit-mode donchian")
    parser.add_argument("--risk-pct", type=float, default=None,
                        help="risk per trade as a fraction, e.g. 0.005 (default: market config)")
    parser.add_argument("--fundamentals", default=None, choices=["covered", "acceptable", "leader", "guide"],
                        help="SEPA part 2, point in time: keep signals whose company's results public on the signal date "
                             "score 'leader', 'acceptable'+, pass the SEPA guide's tests ('guide': the minervini "
                             "strategy's FUND_* thresholds) or can be scored at all ('covered' — the control, since "
                             "fundamental history exists only from 2021 and for part of the universe)")
    parser.add_argument("--block-stage3", action="store_true",
                        help="drop signals whose stock the stage machine had in Stage 3 (topping) on the "
                             "signal date -- the Trend Template's 200-day test lags a top by months")
    parser.add_argument("--min-group-rs", type=int, default=None,
                        help="skip signals whose industry group's RS rating (1-99, rebuilt point in time) was below this "
                             "on the signal date — e.g. 50 to avoid weak groups")
    parser.add_argument("--pyramid", type=float, default=None, metavar="FRAC",
                        help="build positions in two tranches: take FRAC of full size at entry "
                             "(e.g. 0.5) and rest a buy-stop above it for the remainder. Minervini "
                             "adds into strength, never into weakness, and the add is refused above "
                             "the buy range so the average cost stays near the pivot.")
    parser.add_argument("--pyramid-add-pct", type=float, default=2.0, metavar="PCT",
                        help="how far above the entry the second tranche rests (default 2%%)")
    parser.add_argument("--min-dollar-volume", type=float, default=None, metavar="X",
                        help="override the market's traded-value floor for this run, e.g. "
                             "--min-dollar-volume 100e6 to drop small and micro caps. Point in time "
                             "(SMA20 of close x volume per bar), unlike a market-cap filter, which "
                             "would use today's cap and so look ahead.")
    parser.add_argument("--max-base", type=int, default=None, metavar="N",
                        help="trade only the first N bases of a stock's advance (Minervini treats later "
                             "bases as riskier; the spec suggests testing 1-3). Off by default: the spec "
                             "says to TEST it, not to adopt it, so it stays opt-in.")
    parser.add_argument("--const", action="append", default=None, metavar="NAME=VALUE",
                        help="override a numeric module constant of the strategy for this run, e.g. "
                             "--const MIN_STRUCTURAL_R=0. Repeatable. Like --vcp it changes the spec "
                             "fingerprint, so the variant gets its own signal cache and run directory.")
    parser.add_argument("--vcp", action="append", default=None, metavar="KEY=VALUE",
                        help="override a VcpParams field for this run, e.g. --vcp base_min_days=5. "
                             "Repeatable. Changes the spec fingerprint, so the variant gets its own "
                             "signal cache and run directory and cannot be confused with the "
                             "shipped rules.")
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
    signal_source = None   # a run whose cached signal rows this one would write too (seed_signal_cache)
    if getattr(args, "vcp", None):
        # Rebind the strategy module's VCP before anything reads it. spec_params()
        # expands that dataclass, so the fingerprint -- and therefore the signal cache
        # namespace and the run directory -- change automatically: an experiment cannot
        # silently reuse or overwrite the shipped rules' results.
        import dataclasses as _dc
        import importlib

        # The module, not the key: renaming minervini_spec's key to "minervini" left
        # the module as minervini_spec.py, so importing by key silently loaded the
        # RETIRED minervini.py instead of the registered strategy's own module.
        mod = importlib.import_module(type(get_strategy(args.strategy)).__module__)
        if not hasattr(mod, "VCP"):
            parser.error(f"--vcp: {args.strategy} has no VCP parameters to override")
        kw = {}
        for item in args.vcp:
            k, _, v = item.partition("=")
            k = k.strip()
            if not hasattr(mod.VCP, k):
                parser.error(f"--vcp: unknown VcpParams field {k!r}")
            cur = getattr(mod.VCP, k)
            kw[k] = type(cur)(float(v)) if isinstance(cur, (int, float)) else v
        mod.VCP = _dc.replace(mod.VCP, **kw)
        logger.info("VCP override %s -> spec %s", kw, get_strategy(args.strategy).spec_id())
    if args.const:
        # Same contract as --vcp, for the tunables that are module constants rather
        # than VcpParams fields (MIN_STRUCTURAL_R, MAX_STOP_PCT, VOL_MULT ...).
        # spec_params() reads every uppercase numeric module constant, so the
        # fingerprint moves here too and the variant cannot overwrite the shipped run.
        # One implementation, shared with a strategy's live_variant -- and it REFUSES an override
        # that would move the fingerprint without moving the behaviour (strategies/variants.py).
        from ..strategies.variants import apply_consts, split_signal_exempt

        # The overrides the scan reads go first: the spec id between the two applications is the
        # run that would write exactly the rows this variant writes, so its cache can seed ours.
        scan_c, exempt_c = split_signal_exempt(args.strategy, dict(item.partition("=")[::2] for item in args.const))
        try:
            applied = apply_consts(args.strategy, scan_c)
            source_spec, source_signal = get_strategy(args.strategy).spec_id(), get_strategy(args.strategy).signal_id()
            applied.update(apply_consts(args.strategy, exempt_c))
        except ValueError as e:
            parser.error(f"--const: {e}")
        logger.info("const override %s -> spec %s", applied, get_strategy(args.strategy).spec_id())
        if exempt_c and get_strategy(args.strategy).signal_id() == source_signal:
            signal_source = source_spec
            logger.info("%s are read only after the signal scan: seeding the signal cache from %s",
                        sorted(exempt_c), source_spec)
    # A backtest must be attributable to a recorded version. If the rules have
    # moved without a version bump + `versions --update`, the report directory
    # would claim a version whose rules no longer match, so refuse instead.
    # `--vcp` is the deliberate exception: an override is an experiment that
    # carries its own fingerprint into the run name and cache key.
    if not args.vcp and not args.const:
        from ..strategies import versions as _versions
        _stale = _versions.verify(args.strategy)
        if _stale:
            parser.error(
                f"{_stale}\n    Bump `version` and add a changelog entry, then record it:\n"
                f"      PYTHONPATH=. python3 -m swing_screener.strategies.versions --update\n"
                f"    (an unrecorded experiment can still run via --vcp / --const)")
    labels = tuple(x.strip() for x in args.accept_labels.split(",") if x.strip())
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    if args.per_symbol:
        df = run_backtest(
            args.market, args.start, args.limit, args.deep_lookback_days,
            use_signal_cache=not args.no_signal_cache, strategy_key=args.strategy,
            accept_labels=labels, signal_source=signal_source,
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
            # TT-08's own threshold, the one the live screen gates G8 on -- a literal here would
            # leave backtests on the old number the day RS_MIN_RANK is tuned
            args.min_rs = int(ms.RS_MIN_RANK)
        if args.rank_by == "setup":
            args.rank_by = "rs"
        if args.max_open_risk is None:
            args.max_open_risk = ms.MAX_OPEN_RISK_PCT
        if args.max_adv_pct is None:
            args.max_adv_pct = ms.MAX_ADV_PCT
        if args.results_blackout is None:
            args.results_blackout = ms.EARNINGS_BLACKOUT_DAYS
    # the strategy's own market filter (the SEPA guide's) under --spec, MKT-01 otherwise or with --mkt01
    market_guide = bool(args.spec and ms.MKT_GUIDE and not args.mkt01)
    if args.exit_mode == "minervini" and any(
            x is not None for x in (args.time_stop_bars, args.time_stop_mult, args.partial_at_target)):
        parser.error("--time-stop-bars / --time-stop-mult / --partial-at-target manage the shared exit modes; "
                     "the minervini ladder has its own (--time-stop, --partial-r)")
    if args.partial_at_target is not None and not 0 < args.partial_at_target < 1:
        parser.error("--partial-at-target is a fraction between 0 and 1, e.g. 0.5")
    managed = args.exit_mode != "minervini"
    extra = {k: v for k, v in (("partial_r", args.partial_r), ("fail_days", args.fail_days),
                               ("breakeven_r" if not managed else "be_r", args.breakeven_r),
                               ("time_stop_bars", args.time_stop_bars), ("time_stop_mult", args.time_stop_mult),
                               ("partial_at_target", args.partial_at_target),
                               ("strength_ext", args.strength_ext / 100 if args.strength_ext is not None else None),
                               ("climax_partial", False if args.climax_full else None),
                               ("trend_volume", True if args.trend_volume else (False if args.no_trend_volume else None)),
                               ("climax", False if args.no_climax else None),
                               ("time_stop_days", args.time_stop)) if v is not None}
    policy = ExitPolicy(
        mode=args.exit_mode, use_target=not args.no_target,
        atr_mult=args.atr_mult, ma_col=args.ma_col, ma_weeks=args.ma_weeks, donchian_bars=args.donchian_bars, **extra,
    )
    workers = args.workers if args.workers is not None else default_workers()
    logger.info("Scan workers: %d%s", workers, "" if args.workers is not None else " (default_workers)")
    try:
        tdf, perf, result = run_portfolio_backtest(
            args.market, args.start, args.limit, args.deep_lookback_days,
            use_signal_cache=not args.no_signal_cache, strategy_key=args.strategy, workers=workers,
            signal_source=signal_source,
            accept_labels=labels, max_positions=args.max_positions, exit_policy=policy,
            sample=args.sample, refresh_history=args.refresh_history,
            include=[x.strip() for x in args.include.split(",") if x.strip()],
            risk_pct=args.risk_pct, max_position_pct=args.max_position_pct,
            rank_by=args.rank_by, min_group_rs=args.min_group_rs, block_stage3=args.block_stage3,
                min_rs=args.min_rs, max_base_no=args.max_base,
            min_dollar_volume=args.min_dollar_volume,
            pyramid_frac=args.pyramid, pyramid_add_pct=args.pyramid_add_pct,
            use_market_filter=args.market_filter, mkt_confirm=args.mkt_confirm,
            market_guide=market_guide, results_blackout_days=args.results_blackout or None,
            top_dollar_volume=args.top_dollar_volume,
            exposure=_exposure_from(args),
            spec_costs=args.spec,
            max_open_risk_pct=args.max_open_risk / 100 if args.max_open_risk is not None else None,
            max_adv_pct=args.max_adv_pct / 100 if args.max_adv_pct is not None else None,
            only_symbols=[x.strip() for x in args.symbols.split(",") if x.strip()],
            fundamentals=args.fundamentals,
        )
    except NoSignals as exc:
        # "no trades" is a result. Write the funnel anyway -- without it the run
        # leaves nothing at all behind, and WHERE the candidates stopped is the
        # only informative thing about an empty run.
        from ..paths import run_dir as _run_dir
        out = _run_dir(args.market, args.strategy,
                       f"{args.start}_{policy.label()}_{get_strategy(args.strategy).spec_id()}_NO-SIGNALS")
        fn = getattr(exc, "funnel", None)
        if fn is not None:
            fn.write(out)
            (out / "report.md").write_text(
                f"# {MARKETS[args.market].name} — {get_strategy(args.strategy).name}, {args.start} onward\n\n"
                f"**No trades: {exc}**\n\n" + fn.render_md())
        logger.warning("%s — funnel written to %s", exc, out)
        print(f"\nNo trades. The funnel says where the candidates stopped:\n")
        print(fn.render_md() if fn is not None else "(no funnel recorded)")
        print(f"Run dir -> {out}")
        return None
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
    if args.block_stage3:
        run += "_nos3"
    if args.spec:
        run += "_spec"
    elif args.min_rs is not None:
        run += f"_rs{args.min_rs}"
    if args.market_filter:
        run += ("_mktg" if market_guide else "_mkt") + (f"c{args.mkt_confirm}" if args.mkt_confirm else "")
    if args.results_blackout:
        run += f"_rb{args.results_blackout}"
    if args.top_dollar_volume:
        run += f"_top{args.top_dollar_volume}"
    if args.pe:
        run += f"_pe{args.pe_window}w{args.pe_pilot:g}" + (f"press{args.pe_press:g}" if args.pe_press is not None else "")
    if args.fundamentals:
        run += f"_fund{args.fundamentals}"
    if args.accept_labels != "TRADE - HIGH CONFIDENCE":
        run += "_" + "+".join("".join(w[0] for w in x.split() if w[0].isalpha()) for x in labels)
    run += f"_sample{args.sample}" if args.sample else ""
    if args.min_dollar_volume:
        run += f"_dv{args.min_dollar_volume / 1e6:g}m"
    if args.pyramid:
        run += f"_pyr{args.pyramid:g}at{args.pyramid_add_pct:g}pct"
    run += _portfolio_suffix(args, cfg)
    if args.symbols:
        picked = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]
        run += "_only-" + ("+".join(picked) if len(picked) <= 4 else f"{len(picked)}syms")
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
    _fn = getattr(result, "funnel", None)
    if _fn is not None:
        _fn.write(out)
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
            + (f" --ma-weeks {args.ma_weeks}" if args.exit_mode == "weekly_ma" else "")
            + (f" --rank-by {args.rank_by}" if args.rank_by != "setup" else "")
            + (f" --min-group-rs {args.min_group_rs}" if args.min_group_rs is not None else "")
            + (" --block-stage3" if args.block_stage3 else "")
            + (f" --fundamentals {args.fundamentals}" if args.fundamentals else "")
            + (" --spec" if args.spec else (f" --min-rs {args.min_rs}" if args.min_rs is not None else ""))
            + (" --market-filter" if args.market_filter else "")
            + (" --mkt01" if args.mkt01 else "")
            + (f" --results-blackout {args.results_blackout}" if args.results_blackout is not None and not args.spec else "")
            + (" --pe" if args.pe else "")
            + (f" --accept-labels '{args.accept_labels}'" if args.accept_labels != "TRADE - HIGH CONFIDENCE" else "")
            + (f" --partial-r {args.partial_r:g}" if args.partial_r is not None else "")
            + (f" --fail-days {args.fail_days}" if args.fail_days is not None else "")
            + (f" --time-stop {args.time_stop}" if args.time_stop is not None else "")
            + (f" --breakeven-r {args.breakeven_r:g}" if args.breakeven_r is not None else "")
            + (f" --time-stop-bars {args.time_stop_bars}" if args.time_stop_bars is not None else "")
            + (f" --time-stop-mult {args.time_stop_mult:g}" if args.time_stop_mult is not None else "")
            + (f" --partial-at-target {args.partial_at_target:g}" if args.partial_at_target is not None else "")
            + (f" --atr-mult {args.atr_mult:g}" if args.partial_at_target is not None and args.atr_mult != 3.0 else "")
            + (f" --strength-ext {args.strength_ext:g}" if args.strength_ext is not None else "")
            + (" --climax-full" if args.climax_full else "")
            + (" --trend-volume" if args.trend_volume else "")
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
            extra_sections=([("Funnel", _fn.render_md())] if _fn is not None and _fn.render_md() else [])
                           + ([("Breakdown (spec section 13)", spec_md)] if spec_md else []) or None,
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
