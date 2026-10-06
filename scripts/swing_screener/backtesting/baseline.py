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


# --- ranking signals -------------------------------------------------------
#
# Each returns a DataFrame aligned to `px` whose value at (date, symbol) is the
# score as of that date, already lagged by `skip`. Computing them as whole
# matrices rather than per-symbol-per-date keeps a 2,300 x 3,500 universe fast
# and makes each definition one readable expression.

RANKERS = ("momentum", "vol_scaled", "residual", "path_quality")


def score_matrix(
    px: pd.DataFrame, kind: str, lookback: int, skip: int,
    benchmark: "pd.Series | None" = None,
) -> pd.DataFrame:
    """Ranking score per symbol per date."""
    if kind == "momentum":
        # 12-1: total return over `lookback`, ending `skip` bars ago
        return px.shift(skip) / px.shift(skip + lookback) - 1

    rets = px.pct_change()

    if kind == "vol_scaled":
        # Barroso & Santa-Clara: momentum divided by its own volatility, so a
        # steady trend outranks a violent one of the same size. Momentum's
        # crashes come from loading into the highest-beta names before a
        # reversal; scaling by volatility is the standard mitigation.
        mom = px.shift(skip) / px.shift(skip + lookback) - 1
        vol = rets.rolling(lookback, min_periods=lookback // 2).std().shift(skip)
        return mom / vol.replace(0, pd.NA)

    if kind == "path_quality":
        # Alpha Architect's "frog in the pan": of two stocks up the same
        # amount, prefer the one that got there in many small steps rather
        # than one gap. Smooth moves reflect gradual information diffusion.
        return (rets > 0).rolling(lookback, min_periods=lookback // 2).mean().shift(skip)

    if kind == "residual":
        # Residual momentum (Blitz et al.): strip the market component, so you
        # rank on idiosyncratic strength instead of "went up because the index
        # went up". beta from a rolling regression against the benchmark.
        if benchmark is None:
            raise ValueError("residual ranking needs a benchmark series")
        b = benchmark.reindex(px.index).ffill().pct_change()
        n, mp = lookback, lookback // 2
        bb = b.rolling(n, min_periods=mp)
        var_b = bb.var()
        cov = rets.mul(b, axis=0).rolling(n, min_periods=mp).mean().sub(
            rets.rolling(n, min_periods=mp).mean().mul(bb.mean(), axis=0)
        )
        beta = cov.div(var_b.replace(0, pd.NA), axis=0)
        mom = px.shift(skip) / px.shift(skip + lookback) - 1
        bench_mom = b.add(1).rolling(n, min_periods=mp).apply(lambda x: x.prod(), raw=True) - 1
        return mom.sub(beta.shift(skip).mul(bench_mom.shift(skip), axis=0))

    raise ValueError(f"unknown ranking '{kind}', choose from {RANKERS}")


def realised_vol(px: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Annualised volatility per symbol, for inverse-vol position weighting."""
    return px.pct_change().rolling(window, min_periods=window // 2).std() * (252 ** 0.5)


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
    rank: str = "momentum",
    weighting: str = "equal",
    vol_target: float | None = None,
    vol_window: int = 63,
    fractional: bool = False,
    index_overlay: bool = False,
    overlay_months: int = 10,
    preloaded: tuple | None = None,
):
    """Hold the top `top_n` by `rank`, rebalanced on `rebalance`.

    `rank`        momentum | vol_scaled | residual | path_quality
    `weighting`   equal | inverse_vol
    `vol_target`  annualised portfolio vol to scale gross exposure to (no
                  leverage: exposure is capped at 100%)
    `index_overlay`  hold nothing while the benchmark is below its
                  `overlay_months`-month average
    `trend_filter`   require each stock above its own 200-day average
    """
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

    bench_px = None
    bench_raw = cache.load_cached(market, cfg.benchmark_ticker)
    if bench_raw is not None and not bench_raw.empty:
        bench_px = bench_raw["close"]

    # scores and vols as whole matrices, once — not per symbol per rebalance
    scores = score_matrix(px, rank, lookback, skip, benchmark=bench_px)
    vols = realised_vol(px) if weighting == "inverse_vol" else None

    # Index-level trend overlay: hold nothing while the benchmark is below its
    # own long moving average. On 33 years of SPY this cut max drawdown from
    # -50.8% to -23.0% and lifted Sharpe 0.77 -> 0.89, at the cost of CAGR in
    # bull markets. Evaluated on the PREVIOUS month's close so the decision
    # uses only information available when it is acted on.
    overlay_ok = None
    if index_overlay:
        if bench_px is None:
            raise ValueError("index overlay needs a benchmark series")
        bm = bench_px.resample("ME").last()
        bsig = (bm > bm.rolling(overlay_months).mean()).shift(1).fillna(False)
        overlay_ok = bsig.reindex(px.index, method="ffill").fillna(False)

    # Drop partial days. If the cache was refreshed for part of the universe
    # (a screener run mid-session, say), the newest date can carry prices for a
    # handful of symbols and NaN for the rest. Rebalancing on such a day trades
    # against a near-empty universe, and marking against it values the whole
    # book at zero — a -100% drawdown on the final bar.
    coverage = px.notna().sum(axis=1)
    expected = coverage.rolling(20, min_periods=1).median()
    partial = coverage < 0.5 * expected
    if partial.any():
        logger.info(
            "dropping %d partial trading day(s), e.g. %s (%d of %d symbols priced)",
            int(partial.sum()), str(px.index[partial][-1].date()),
            int(coverage[partial].iloc[-1]), px.shape[1],
        )
        px = px.loc[~partial]
        dv = dv.reindex(px.index)
        sma200 = sma200.reindex(px.index)

    # Valuation uses the last known price, not today's cell: a holding that did
    # not print today is still worth its last trade, not nothing.
    marks = px.ffill()

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
        row = px.loc[today]       # today's actual prices — used for trading
        mark = marks.loc[today]   # last known prices — used for valuation

        held_value = sum(
            sh * float(mark[s]) for s, sh in holdings.items()
            if s in mark.index and pd.notna(mark[s])
        )
        equity = cash + held_value

        if today in rebal_dates:
            score_row = scores.loc[today] if today in scores.index else None
            mom = {}
            for s in px.columns:
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
                m = float(score_row[s]) if score_row is not None and pd.notna(score_row.get(s)) else float("nan")
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
            if overlay_ok is not None and not bool(overlay_ok.get(today, False)):
                target = []   # benchmark below its trend: hold nothing

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
                sh * float(mark[s]) for s, sh in holdings.items()
                if s in mark.index and pd.notna(mark[s])
            )
            if target:
                # --- position weights ---
                if weighting == "inverse_vol" and vols is not None:
                    # Size inversely to each name's volatility so one wild
                    # holding cannot dominate portfolio risk. Equal weight is
                    # equal *capital*, not equal risk.
                    w = {}
                    for s_ in target:
                        v = vols.loc[today, s_] if s_ in vols.columns else float("nan")
                        w[s_] = 1.0 / float(v) if pd.notna(v) and v > 0 else 0.0
                    tot = sum(w.values())
                    weights = ({k: v / tot for k, v in w.items()} if tot > 0
                               else {k: 1.0 / len(target) for k in target})
                else:
                    weights = {k: 1.0 / len(target) for k in target}

                # --- volatility target: scale gross exposure, never leverage ---
                gross = 1.0
                if vol_target:
                    # Volatility of the ACTUAL weighted basket, from its own
                    # trailing returns. The previous version divided average
                    # constituent vol by sqrt(n), which assumes the holdings are
                    # uncorrelated — a momentum book is the opposite, which is
                    # precisely why it draws down 50%. That understated portfolio
                    # vol ~4x (7.7% vs a 15% target), so the cap never bound and
                    # the option did nothing.
                    win = min(vol_window, len(px.loc[:today]) - 1)
                    if win > 20:
                        hist_r = px.loc[:today, target].tail(win).pct_change()
                        wser = pd.Series(weights).reindex(hist_r.columns).fillna(0.0)
                        basket = hist_r.mul(wser, axis=1).sum(axis=1, min_count=1)
                        port_vol = float(basket.std()) * (252 ** 0.5)
                        if port_vol and port_vol == port_vol:
                            gross = min(1.0, vol_target / port_vol)

                for s in target:
                    price = float(row[s])
                    alloc = equity * weights[s] * gross
                    # Integer share counts silently drop any stock priced above
                    # its own allocation. SNDK ranked #1 by momentum on 138 of
                    # 138 rankable days and never traded, because at ~$950 per
                    # name a $2,274 share floors to zero. Fractional investing
                    # (available for US stocks through several brokers) removes
                    # the granularity entirely.
                    want_shares = (alloc / price) if fractional else int(alloc // price)
                    have = holdings.get(s, 0)
                    if want_shares > have:
                        buy = want_shares - have
                        fill = price * (1 + cost_bps / 10_000)
                        need = fill * buy
                        if need > cash:
                            buy = int(cash // fill)
                            need = fill * buy
                        if buy < (1e-6 if fractional else 1):
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
            sh * float(mark[s]) for s, sh in holdings.items()
            if s in mark.index and pd.notna(mark[s])
        )
        eq_rows.append(cash + held_value)
        pos_rows.append(len(holdings))
        cash_rows.append(cash)

    # close out whatever is still held, at the final close
    last = dates[-1]
    final = marks.loc[last]
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


# Reference documentation for the web app's Strategy page. The baseline is not
# a `Strategy` subclass (see the module docstring), so it documents itself
# here; its parameters are read live from build_parser(), so they cannot drift.
# Update this block in the same change as any change to how the baseline works.
DOC = {
    "key": "momentum_baseline",
    "name": "Cross-sectional momentum baseline",
    "description": "Rank by 12-1 month momentum, hold the top N, rebalance on a calendar; the benchmark every strategy must beat.",
    "status": "Reference portfolio, not a screener strategy. Beats the index in India; not in the US (see research/momentum-trend-research.md).",
    "thesis": "Stocks that have outperformed over the past year keep outperforming for months (cross-sectional momentum), "
              "so simply holding the strongest names should beat the index after costs.",
    "how_it_works": (
        "On each rebalance date, score every eligible stock by its return over the last `--lookback` bars, skipping the most "
        "recent `--skip` bars (the 12-1 convention, which avoids the short-term reversal of the latest month).",
        "Only the `--liquidity-top` most liquid names are ranked, so the list is not filled with speculative microcaps.",
        "With the trend filter on (the default), a stock must also be above its 200-day moving average to be held.",
        "Hold the top `--top-n` names, equal-weighted by default (`--weighting inverse_vol` sizes by inverse volatility).",
        "A holding is sold when it drops out of the top N at a rebalance or loses its trend; there are no stops, targets or entry triggers.",
        "Costs of `--cost-bps` per side are charged on every trade; whole shares only unless `--fractional`.",
    ),
    "caveats": (
        "Survivorship bias: the universe is today's listed names, which flatters every backtest here.",
        "Results depend on the rebalance cadence and N; compare runs with the same settings.",
        "Optional overlays (`--index-overlay`, `--vol-target`, alternative `--rank` signals) are experiments, not the baseline itself.",
    ),
    "screen": False,
}


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Cross-sectional momentum baseline")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--top-n", type=int, default=10)
    ap.add_argument("--lookback", type=int, default=TRADING_DAYS, help="momentum lookback in bars")
    ap.add_argument("--skip", type=int, default=21, help="bars to skip (12-1 convention)")
    ap.add_argument("--rebalance", default="ME", help="pandas offset alias: ME, QE, W-FRI")
    ap.add_argument("--no-trend-filter", action="store_true", help="drop the >200DMA requirement")
    ap.add_argument("--cost-bps", type=float, default=5.0)
    ap.add_argument("--fractional", action="store_true",
                    help="allow fractional shares — without it any stock priced "
                         "above its per-name allocation is silently skipped")
    ap.add_argument("--rank", default="momentum", choices=list(RANKERS),
                    help="ranking signal: raw momentum, volatility-scaled "
                         "(Barroso-Santa-Clara), market-residual (Blitz), or path "
                         "quality (share of positive days)")
    ap.add_argument("--weighting", default="equal", choices=["equal", "inverse_vol"],
                    help="equal capital, or inverse to each name's volatility")
    ap.add_argument("--vol-target", type=float, default=None,
                    help="annualised portfolio vol to scale gross exposure to, "
                         "e.g. 0.15. Never leverages — exposure caps at 100%%")
    ap.add_argument("--index-overlay", action="store_true",
                    help="hold nothing while the benchmark is below its long "
                         "moving average (cut SPY's max drawdown -50.8%% -> -23.0%%)")
    ap.add_argument("--overlay-months", type=int, default=10)
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
    ap.add_argument("--no-ingest", action="store_true",
                    help="skip updating the viewer database after the run")
    return ap


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = build_parser().parse_args()

    cfg = MARKETS[args.market]
    tdf, perf, eq, pos = run(
        args.market, args.start, top_n=args.top_n, lookback=args.lookback,
        skip=args.skip, rebalance=args.rebalance,
        trend_filter=not args.no_trend_filter, cost_bps=args.cost_bps,
        liquidity_rank_top=args.liquidity_top or None,
        min_dollar_volume=args.min_turnover,
        fractional=args.fractional,
        rank=args.rank, weighting=args.weighting, vol_target=args.vol_target,
        index_overlay=args.index_overlay, overlay_months=args.overlay_months,
    )
    from ..paths import run_dir

    # NOT `run`: this module's main entry point is also called run(), and a
    # local of that name shadows it for the whole function body
    run_name = (f"{args.start}_top{args.top_n}_{args.rank}{args.lookback}_{args.rebalance}"
                f"_{args.cost_bps:g}bps"
                + (f"_{args.weighting}" if args.weighting != "equal" else "")
                + (f"_vt{args.vol_target:g}" if args.vol_target else "")
                + ("_overlay" if args.index_overlay else "")
                + ("_frac" if args.fractional else "")
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
    # index the new report so the viewer shows it without a server restart
    if not getattr(args, "no_ingest", False):
        from ..web.ingest import ingest_after_run
        ingest_after_run()


if __name__ == "__main__":
    main()
