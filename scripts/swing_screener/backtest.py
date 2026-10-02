"""Walk-forward backtest of the exact gate/entry/sizing logic used live —
not a shortcut that reuses today's indicators, a true day-by-day
simulation where every date only sees data up to and including itself.

Methodology, stated plainly (so results aren't over-trusted):
* Entry: a trade opens on the first day a symbol has an active setup
  (TC-01/TC-02), all hard gates pass, and entry.signal_present() is true
  (same 'signal already fired' test used for TRADE - HIGH CONFIDENCE
  live). Fill price = the plan's computed entry (trigger + 0.1%, same as
  live). One open position per symbol at a time — no pyramiding, no
  re-entry until the prior trade on that symbol has closed.
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
* Universe is pre-filtered through TODAY's loose screener filter before
  walking back to July, to keep runtime bounded against thousands of
  cached tickers — a stock that passed the filter in July but fails it
  today would be invisible to this backtest. Said out loud rather than
  silently assumed.
* Market regime downgrade and sector-cap-of-3 are NOT applied — this
  tests the gate/entry/setup logic itself, not the portfolio-construction
  overlay on top of it.

Usage:
    python3 -m swing_screener.backtest --market us --start 2026-07-01
    python3 -m swing_screener.backtest --market india --start 2026-07-01 --limit 300
"""

import argparse
import logging
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from . import cache, universe, indicators as ind, screener, gates, entry, sizing
from .config import MarketConfig, MARKETS

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


def backtest_symbol(
    symbol: str, raw_daily: pd.DataFrame, cfg: MarketConfig, start_date: pd.Timestamp
) -> list[Trade]:
    trades: list[Trade] = []
    if raw_daily is None or len(raw_daily) < 260:
        return trades

    sim_dates = raw_daily.index[raw_daily.index >= start_date]
    if len(sim_dates) < 2:
        return trades

    in_position = False
    pos: dict | None = None

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

        slice_df = raw_daily.loc[:current_date]
        if len(slice_df) < 260:
            continue
        try:
            ctx = gates.build_context(symbol, slice_df, earnings_days_away=None)
        except Exception:
            continue
        if ctx is None:
            continue
        try:
            result = gates.compute_gates(ctx)
        except Exception:
            continue
        if not result.hard_gates_passed or not result.has_setup:
            continue
        if not entry.signal_present(ctx, result):
            continue
        plan, _other, _reason = entry.choose_plan(ctx, result, cfg.tick_size)
        if plan is None or plan.risk_per_share <= 0:
            continue
        sz = sizing.size_position(cfg, plan.entry, plan.stop, vix_above_threshold=False)
        if sz.too_large:
            continue

        pos = {
            "market": cfg.name, "symbol": symbol, "setup": plan.setup,
            "entry_date": current_date, "entry_price": plan.entry,
            "stop": plan.stop, "target": plan.target, "shares": sz.shares,
        }
        in_position = True

    if in_position:
        last_date = raw_daily.index[-1]
        last_close = float(raw_daily["close"].iloc[-1])
        trades.append(_close_trade(pos, last_date, "OPEN", last_close))

    return trades


def _close_trade(pos: dict, exit_date: pd.Timestamp, reason: str, exit_price: float) -> Trade:
    return Trade(
        market=pos["market"], symbol=pos["symbol"], setup=pos["setup"],
        entry_date=pos["entry_date"], entry_price=pos["entry_price"],
        stop=pos["stop"], target=pos["target"], shares=pos["shares"],
        exit_date=exit_date, exit_reason=reason, exit_price=exit_price,
    )


def run_backtest(
    market_key: str, start_date: str, limit: int | None = None
) -> pd.DataFrame:
    cfg = MARKETS[market_key]
    cache_dir = cache.DEFAULT_CACHE_DIR
    start = pd.Timestamp(start_date)

    tickers = universe.load_universe(market_key)
    logger.info("Universe: %d tickers; pre-filtering on today's loose screener...", len(tickers))

    candidates: list[str] = []
    for sym in tickers:
        raw = cache.load_cached(cache_dir, market_key, sym)
        if raw is None or len(raw) < 260:
            continue
        enriched = ind.enrich_daily(raw)
        ok, _why = screener.passes_loose_filter(cfg, enriched)
        if ok:
            candidates.append(sym)
    logger.info("Pre-filter: %d/%d symbols pass today's screener", len(candidates), len(tickers))

    if limit:
        candidates = candidates[:limit]
        logger.info("Capped to %d symbols for this run", len(candidates))

    all_trades: list[Trade] = []
    for i, sym in enumerate(candidates):
        raw = cache.load_cached(cache_dir, market_key, sym)
        trades = backtest_symbol(sym, raw, cfg, start)
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
    args = parser.parse_args()

    df = run_backtest(args.market, args.start, args.limit)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = REPORT_DIR / f"{args.market}_backtest_{args.start}.csv"
    df.to_csv(out_path, index=False)
    print(f"\nWrote {len(df)} trades to {out_path}\n")
    print_summary(df, MARKETS[args.market].currency_symbol)
    if not df.empty:
        print("\nTrades:")
        print(df.to_string(index=False))


if __name__ == "__main__":
    main()
