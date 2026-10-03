"""Cross-sectional momentum baseline — the reference every strategy must beat.

Why a baseline matters more than another tweak
----------------------------------------------
`trend_pullback` carries 14 hard gates, 9 watch flags, 3 setups and a dozen
thresholds. Fitted against a few hundred trades, that is a lot of freedom.
Without a reference point there is no way to answer the only question that
matters: does any of that machinery beat the simplest thing that expresses
the same idea?

This is that simplest thing. Rank every eligible stock by momentum, hold
the top N, rebalance monthly, drop anything whose trend has broken. Two
real parameters (lookback, N). No gates, no setups, no watch flags, no
entry triggers, no profit targets.

It is deliberately a different shape from the Strategy ABC: ranking is a
portfolio-level decision across symbols on one date, whereas the ABC
evaluates one symbol in isolation. Forcing it into that interface would
have meant distorting one or the other.

    python3 -m swing_screener.backtesting.baseline --market us --start 2012-01-01
    python3 -m swing_screener.backtesting.baseline --market us --start 2012-01-01 --top-n 20 --lookback 126

Momentum convention: the 12-1 measure (return over the last 12 months,
skipping the most recent month) is the standard academic form — the skip
avoids the short-term reversal that contaminates the most recent weeks.
"""

import argparse
import logging

import pandas as pd

from ..marketdata import cache, universe

from . import metrics
from ..config import MARKETS

logger = logging.getLogger("baseline")

TRADING_DAYS = 252


def _momentum(close: pd.Series, lookback: int, skip: int) -> float:
    """Return over `lookback` bars ending `skip` bars ago."""
    if len(close) < lookback + skip + 1:
        return float("nan")
    end = close.iloc[-1 - skip]
    begin = close.iloc[-1 - skip - lookback]
    if begin <= 0:
        return float("nan")
    return float(end / begin - 1)


def load_prices(market: str, min_bars: int) -> tuple:
    """(close, 20d dollar volume, SMA200) frames for the whole universe.

    Split out from `run` so a parameter sweep loads the ~15M-bar universe
    ONCE instead of per variant. Deliberately NOT truncated to the backtest
    start: momentum needs the history before the window opens, and
    truncating first silently delays every signal by lookback+skip bars.
    """
    tickers = universe.load_universe(market)
    closes, dollar_vol = {}, {}
    for sym in tickers:
        d = cache.load_cached(market, sym)
        if d is None or len(d) < min_bars:
            continue
        closes[sym] = d["close"]
        # the same liquidity floor the gated strategy screens on -- without
        # it a naive momentum rank fills with illiquid microcaps, which is a
        # property of the universe, not of the momentum idea under test
        dollar_vol[sym] = (d["close"] * d["volume"]).rolling(20, min_periods=20).mean()
    if not closes:
        raise ValueError("no symbols with enough cached history")
    logger.info("%s: %d/%d symbols have enough history", market, len(closes), len(tickers))
    px = pd.DataFrame(closes).sort_index()
    dv = pd.DataFrame(dollar_vol).sort_index().reindex(px.index)
    sma200 = px.rolling(200, min_periods=200).mean()
    return px, dv, sma200


def run(
    market: str, start: str, top_n: int = 10, lookback: int = TRADING_DAYS,
    skip: int = 21, rebalance: str = "ME", trend_filter: bool = True,
    min_price: float | None = None, cost_bps: float = 5.0,
    liquidity_rank_top: int | None = 1000,
    min_dollar_volume: float | None = None,
    preloaded: tuple | None = None,
):
    """Equal-weight the top `top_n` by momentum, rebalanced monthly.

    `trend_filter` additionally requires price above its 200-day average —
    the minimal expression of "only own it while the trend is up", which is
    what separates this from pure momentum rotation."""
    cfg = MARKETS[market]
    start_ts = pd.Timestamp(start)
    floor_price = cfg.screener.min_price if min_price is None else min_price
    # The TURNOVER floor is the real universe control, not `liquidity_rank_top`:
    # the floor already cuts the tape to a few hundred names, so the rank cutoff
    # never binds above ~250 (measured: top-500/1000/2000 gave identical results
    # to the digit). Exposed as a parameter so it can actually be swept.
    liq_floor = (
        cfg.screener.min_dollar_volume if min_dollar_volume is None else min_dollar_volume
    )

    px, dv, sma200 = preloaded if preloaded is not None else load_prices(
        market, min_bars=lookback + skip + 2
    )

    dates = px.index[px.index >= start_ts]
    if len(dates) < 2:
        raise ValueError("not enough trading dates in range")

    # rebalance on the last trading day of each period present in the data
    rebal_dates = set(pd.Series(dates, index=dates).resample(rebalance).last().dropna())

    equity = float(cfg.account_size)
    holdings: dict[str, float] = {}   # symbol -> shares
    eq_rows, pos_rows, cash_rows = [], [], []
    cash = equity
    costs_total = 0.0
    turnover_notional = 0.0
    trades: list[dict] = []
    entry_info: dict[str, tuple] = {}

    for today in dates:
        row = px.loc[today]

        # mark to market
        held_value = sum(
            sh * float(row[s]) for s, sh in holdings.items()
            if s in row.index and pd.notna(row[s])
        )
        equity = cash + held_value

        if today in rebal_dates:
            hist = px.loc[:today]
            mom = {}
            for s in px.columns:
                col = hist[s].dropna()
                price_now = float(row[s]) if s in row.index and pd.notna(row[s]) else float("nan")
                if price_now != price_now or price_now < floor_price:
                    continue
                if liq_floor:
                    liq = dv.loc[today, s] if s in dv.columns else float("nan")
                    if liq != liq or liq < liq_floor:
                        continue
                if trend_filter:
                    ma = sma200.loc[today, s] if s in sma200.columns else float("nan")
                    if ma != ma or price_now <= ma:
                        continue
                m = _momentum(col, lookback, skip)
                if m == m:
                    mom[s] = m
            # Restrict the ranking pool to the most liquid names FIRST.
            # Ranking the whole 5,000-name tape by raw momentum selects the
            # most extreme movers, which are overwhelmingly speculative
            # microcaps -- that measures the universe's tail, not momentum.
            # Standard practice ranks within a liquid investable set.
            if liquidity_rank_top and len(mom) > liquidity_rank_top:
                liq_today = {
                    s: float(dv.loc[today, s]) for s in mom
                    if s in dv.columns and pd.notna(dv.loc[today, s])
                }
                pool = set(
                    sorted(liq_today, key=liq_today.get, reverse=True)[:liquidity_rank_top]
                )
                mom = {s: m for s, m in mom.items() if s in pool}
            target = sorted(mom, key=mom.get, reverse=True)[:top_n]

            # sell anything not in the new target
            for s in list(holdings):
                if s in target:
                    continue
                price = float(row[s]) if s in row.index and pd.notna(row[s]) else None
                if price is None:
                    continue
                fill = price * (1 - cost_bps / 10_000)
                proceeds = fill * holdings[s]
                cost = (price - fill) * holdings[s]
                cash += proceeds
                costs_total += cost
                turnover_notional += price * holdings[s]
                ed, ep, esh = entry_info.pop(s, (today, price, holdings[s]))
                trades.append({
                    "symbol": s, "entry_date": ed, "entry_price": round(ep, 4),
                    "exit_date": today, "exit_price": round(fill, 4), "shares": esh,
                    "exit_reason": "REBALANCE_OUT",
                    "pnl": round((fill - ep) * esh - cost, 2),
                    "notional": round(ep * esh, 2), "costs": round(cost, 2),
                    "holding_days": (today - ed).days,
                })
                del holdings[s]

            # equal-weight the target across current equity
            equity = cash + sum(
                sh * float(row[s]) for s, sh in holdings.items()
                if s in row.index and pd.notna(row[s])
            )
            if target:
                per_name = equity / len(target)
                for s in target:
                    price = float(row[s])
                    want_shares = int(per_name // price)
                    have = holdings.get(s, 0)
                    if want_shares > have:
                        buy = want_shares - have
                        fill = price * (1 + cost_bps / 10_000)
                        need = fill * buy
                        if need > cash:
                            buy = int(cash // fill)
                            need = fill * buy
                        if buy < 1:
                            continue
                        cash -= need
                        costs_total += (fill - price) * buy
                        turnover_notional += price * buy
                        holdings[s] = have + buy
                        if s not in entry_info:
                            entry_info[s] = (today, fill, holdings[s])
                    elif want_shares < have:
                        sell = have - want_shares
                        fill = price * (1 - cost_bps / 10_000)
                        cash += fill * sell
                        costs_total += (price - fill) * sell
                        turnover_notional += price * sell
                        holdings[s] = have - sell
                        if holdings[s] == 0:
                            del holdings[s]
                            entry_info.pop(s, None)

        held_value = sum(
            sh * float(row[s]) for s, sh in holdings.items()
            if s in row.index and pd.notna(row[s])
        )
        eq_rows.append(cash + held_value)
        pos_rows.append(len(holdings))
        cash_rows.append(cash)

    # close out whatever is still held, at the final close
    last = dates[-1]
    final = px.loc[last]
    for s, sh in holdings.items():
        if s not in final.index or pd.isna(final[s]):
            continue
        price = float(final[s])
        ed, ep, esh = entry_info.get(s, (last, price, sh))
        trades.append({
            "symbol": s, "entry_date": ed, "entry_price": round(ep, 4),
            "exit_date": last, "exit_price": round(price, 4), "shares": sh,
            "exit_reason": "OPEN", "pnl": round((price - ep) * sh, 2),
            "notional": round(ep * sh, 2), "costs": 0.0,
            "holding_days": (last - ed).days,
        })

    eq = pd.Series(eq_rows, index=dates)
    pos = pd.Series(pos_rows, index=dates)
    tdf = pd.DataFrame(trades)
    if not tdf.empty:
        risk_proxy = tdf["notional"].replace(0, pd.NA)
        tdf["r_multiple"] = tdf["pnl"] / risk_proxy * 10  # notional-relative, not stop-relative
    else:
        tdf = pd.DataFrame(columns=["symbol", "exit_reason", "pnl", "notional", "r_multiple"])

    bench_raw = cache.load_cached(market, cfg.benchmark_ticker)
    bench_close = (
        bench_raw["close"].reindex(eq.index).ffill()
        if bench_raw is not None and not bench_raw.empty else None
    )
    notes = [
        "SURVIVORSHIP BIAS: today's listed names only; companies delisted during "
        "the window are absent, which biases returns upward.",
        f"Costs: {cost_bps:.0f}bps per side. Dividends are excluded on BOTH the "
        "strategy and the benchmark, so absolute returns understate reality for each.",
        f"Rules: top {top_n} by {lookback}-bar momentum skipping {skip} bars, "
        f"rebalanced {rebalance}, ranked within the top "
        f"{liquidity_rank_top or 'all'} by dollar volume, liquidity floor "
        f"{cfg.currency_symbol}{liq_floor:,.0f} 20d dollar volume"
        + (", held only above the 200-day average." if trend_filter else "."),
        "'r_multiple' here is notional-relative (no stop exists), so it is NOT "
        "comparable to the gated strategy's stop-relative R.",
    ]
    perf = metrics.compute(
        equity=eq, positions_open=pos, trades=tdf, max_open_positions=top_n,
        costs_paid=costs_total, bench_close=bench_close, notes=notes,
    )
    return tdf, perf, eq, pos


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Cross-sectional momentum baseline")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--lookback", type=int, default=TRADING_DAYS, help="momentum lookback in bars")
    ap.add_argument("--skip", type=int, default=21, help="bars to skip (12-1 convention)")
    ap.add_argument("--rebalance", default="ME", help="pandas offset alias: ME, QE, W-FRI")
    ap.add_argument("--no-trend-filter", action="store_true", help="drop the >200DMA requirement")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument(
        "--min-turnover", type=float, default=None,
        help="20-day average turnover floor in account currency (overrides the market "
        "config). This is the real universe control — see --liquidity-top.",
    )
    ap.add_argument(
        "--liquidity-top", type=int, default=1000,
        help="rank momentum only within the N most liquid names (0 = whole universe). "
        "Guards against the rank filling with speculative microcaps.",
    )
    args = ap.parse_args()

    cfg = MARKETS[args.market]
    tdf, perf, eq, pos = run(
        args.market, args.start, top_n=args.top_n, lookback=args.lookback,
        skip=args.skip, rebalance=args.rebalance,
        trend_filter=not args.no_trend_filter, cost_bps=args.cost_bps,
        liquidity_rank_top=args.liquidity_top or None,
        min_dollar_volume=args.min_turnover,
    )
    from ..paths import run_dir

    # NOT `run`: this module's main entry point is also called run(), and a
    # local of that name shadows it for the whole function body
    run_name = (f"{args.start}_top{args.top_n}_mom{args.lookback}_{args.rebalance}"
                f"_{args.cost_bps:g}bps"
                + (f"_turnover{args.min_turnover:g}" if args.min_turnover else "")
                + ("_noTrendFilter" if args.no_trend_filter else ""))
    out = run_dir(args.market, "momentum_baseline", run_name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({
        "equity": eq, "positions_open": pos,
        "drawdown_pct": metrics.drawdown_series(eq) * 100,
    }).to_csv(out / "equity.csv")

    print()
    print(metrics.format_report(perf, cfg.currency_symbol, args.top_n))
    bench_raw = cache.load_cached(args.market, cfg.benchmark_ticker)
    bc = bench_raw["close"].reindex(eq.index).ffill() if bench_raw is not None else None
    print()
    print(metrics.format_equity_curve(eq, bc))
    print(f"\nRun dir -> {out}")

    try:
        from . import report as report_mod

        cmd = (
            f"python3 -m swing_screener.backtesting.baseline --market {args.market} "
            f"--start {args.start} --top-n {args.top_n} --lookback {args.lookback} "
            f"--rebalance {args.rebalance} --cost-bps {args.cost_bps}"
            + (f" --min-turnover {args.min_turnover:g}" if args.min_turnover else "")
            + (" --no-trend-filter" if args.no_trend_filter else "")
        )
        md = report_mod.write_report(
            out,
            f"{cfg.name} — momentum baseline (top {args.top_n}), {args.start} onward",
            perf, eq, pos, tdf, cfg.currency_symbol, args.top_n, bc, cmd,
        )
        print(f"Report -> {md}")
    except Exception as e:
        print(f"(markdown report not generated: {type(e).__name__}: {e})")


if __name__ == "__main__":
    main()
