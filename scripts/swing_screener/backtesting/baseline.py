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
import shlex
import logging

import pandas as pd

from ..marketdata import cache, corporate_actions, universe

from . import metrics
from . import regime as _regime
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

RANKERS = ("momentum", "vol_scaled", "residual", "path_quality", "rs_range")


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

    if kind == "rs_range":
        # Where the RELATIVE-STRENGTH line sits inside its own trailing range: the continuous
        # form of the chartist's "RS line at a new high", which is what rs_leaders gates on.
        #
        # It has to be the line's POSITION IN ITS RANGE, not its return. Ranking by relative
        # return is mathematically identical to ranking by plain momentum -- on any single date
        # the benchmark term is the same scalar for every symbol, so dividing by it cannot
        # reorder anything. The range position is path-dependent (it depends on the line's own
        # low as well as its high), so it asks a question momentum does not: did this stock's
        # relative line hold up, or did it round-trip to get here?
        if benchmark is None:
            raise ValueError("rs_range ranking needs a benchmark series")
        rs = px.div(benchmark.reindex(px.index).ffill(), axis=0)
        n, mp = lookback, lookback // 2
        lo = rs.rolling(n, min_periods=mp).min()
        hi = rs.rolling(n, min_periods=mp).max()
        return ((rs - lo) / (hi - lo).replace(0, pd.NA)).shift(skip)

    raise ValueError(f"unknown ranking '{kind}', choose from {RANKERS}")


def realised_vol(px: pd.DataFrame, window: int = 63) -> pd.DataFrame:
    """Annualised volatility per symbol, for inverse-vol position weighting."""
    return px.pct_change().rolling(window, min_periods=window // 2).std() * (252 ** 0.5)


def load_prices(market: str, min_bars: int) -> tuple:
    """(close, 20d dollar volume, SMA200, total-return close) frames for the whole universe.

    `close` is what was traded: fills, valuation, the price floor and dollar volume read it. The
    total-return close is the same series back-adjusted for the special dividends and demergers a
    holder is credited (corporate_actions.back_adjust); every SIGNAL reads it -- momentum, volatility
    and the 200-day trend test (SMA200 is computed on it) -- so a demerged parent does not read as a
    crash for the next year. Ratios only, so no action dated after the bar can leak into it.

    Split out from `run` so a parameter sweep loads the ~15M-bar universe
    ONCE instead of per variant. Deliberately NOT truncated to the backtest
    start: momentum needs the history before the window opens, and
    truncating first silently delays every signal by lookback+skip bars.
    """
    # ETFs and liquid funds are not candidates for an equity momentum book, and a
    # volatility-weighted one is actively broken by them: see universe.non_stock_symbols.
    skip = universe.non_stock_symbols(market)
    tickers = [t for t in universe.load_universe(market) if t not in skip]
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
    tr = corporate_actions.back_adjust(px, corporate_actions.credits(market, list(px.columns)))
    sma200 = tr.rolling(200, min_periods=200).mean()
    return px, dv, sma200, tr


def eligible_scores(symbols, price_row, dv_row, sma200_row, score_row, *,
                    floor_price: float, liq_floor: float | None, trend_filter: bool,
                    liquidity_rank_top: int | None, trend_row=None) -> dict:
    """{symbol: score} for the names eligible on one date -- the strategy's whole selection rule.

    Extracted from `run`'s rebalance branch so a LIVE view of what the strategy would hold can
    call the same code instead of restating it. A second implementation of the selection is free
    to drift from the one that is backtested and versioned, and would drift silently.

    `price_row` is the traded close (the price floor); `trend_row`, when given, is the total-return
    close the 200-day test compares with `sma200_row` (both from `load_prices`).
    """
    out = {}
    for s in symbols:
        price_now = float(price_row[s]) if s in price_row.index and pd.notna(price_row[s]) else float("nan")
        if price_now != price_now or price_now < floor_price:
            continue
        if liq_floor:
            liq = dv_row[s] if dv_row is not None and s in dv_row.index else float("nan")
            if liq != liq or liq < liq_floor:
                continue
        if trend_filter:
            ma = sma200_row[s] if sma200_row is not None and s in sma200_row.index else float("nan")
            trend_now = price_now if trend_row is None else (
                float(trend_row[s]) if s in trend_row.index and pd.notna(trend_row[s]) else float("nan"))
            if ma != ma or trend_now != trend_now or trend_now <= ma:
                continue
        m = float(score_row[s]) if score_row is not None and pd.notna(score_row.get(s)) else float("nan")
        if m == m:
            out[s] = m
    # Restrict the ranking pool to the most liquid names FIRST. Ranking the whole 5,000-name tape
    # by raw momentum selects the most extreme movers, which are overwhelmingly speculative
    # microcaps -- that measures the universe's tail, not momentum. Standard practice ranks within
    # a liquid investable set.
    if liquidity_rank_top and len(out) > liquidity_rank_top and dv_row is not None:
        liq_today = {s: float(dv_row[s]) for s in out if s in dv_row.index and pd.notna(dv_row[s])}
        pool = set(sorted(liq_today, key=liq_today.get, reverse=True)[:liquidity_rank_top])
        out = {s: m for s, m in out.items() if s in pool}
    return out


def regime_series(market: str, ticker: str | None, default: "pd.Series | None") -> "pd.Series | None":
    """The close series the market-regime switch reads: `ticker` when a strategy names one, else
    `default` (the market's broad benchmark).

    A filter should watch the market the book actually holds. momentum_vol_scaled holds small and mid
    caps, and on the broad index the switch stayed on through 2018, when the Nifty 500 fell 3.4% and
    the Smallcap 250 26.8%: the book lost 28.1% with the filter "on". Raises rather than falling back
    when a named index is not stored -- a silent fallback would run the old filter under the new name.
    """
    if not ticker:
        return default
    raw = cache.load_cached(market, ticker)
    if raw is None or raw.empty:
        raise ValueError(f"regime index {ticker} is not stored for {market}")
    return raw["close"].astype(float)


def buffered_target(ranked: list, held, top_n: int, hold_rank: int | None) -> list:
    """The names to hold after a rebalance: buy into the top `top_n`, hold until outside `hold_rank`.

    Without a buffer the book is the fresh top `top_n` every rebalance, so a name that slips one
    place -- rank 20 to 21 -- is sold outright and something else bought. The ranking here is
    12-1 momentum, which barely moves in a month, yet the measured book was held a median 33 days
    and turned over 4.6-5.2x a year: rank noise, not signal, was deciding most of the trades, and
    at the default cost each turn of the book costs about a point of return.

    With `hold_rank` set, a name already held stays while it ranks within `hold_rank` and is
    still eligible (`ranked` is the eligible list, so a name that fails the trend or turnover
    floor is sold regardless), and free slots go to the best-ranked names not held. `None`, or
    any value not above `top_n`, is the plain top-`top_n` rule.

    `ranked` is best first; `held` is any collection of the symbols held going in.
    """
    if not hold_rank or hold_rank <= top_n:
        return list(ranked[:top_n])
    band = set(ranked[:hold_rank])
    held = set(held)
    keep = [s for s in ranked if s in held and s in band]          # in rank order
    fill = [s for s in ranked if s not in held][: max(0, top_n - len(keep))]
    return (keep + fill)[:top_n]


_SELECTION_CACHE: dict = {}


def current_selection(market: str, strategy_key: str, limit: int | None = None,
                      replay_months: int = 36) -> dict:
    """What the strategy would hold if it rebalanced on the latest stored bar.

    The portfolio equivalent of a screener's "setups today", and computed by the SAME selection the
    backtest uses (`eligible_scores`) rather than a restatement of it -- which is the only way the
    page and the measured strategy cannot disagree.

    It is a ranking as of the last bar, not a rebalance: the strategy only acts on its rebalance
    date, so this answers "what does the rule point at now", not "what should I buy today".
    """
    from ..strategies import portfolio_strategies

    cls = portfolio_strategies()[strategy_key]
    # A ranking only exists for the stock-ranking strategies this module runs. The others (dual momentum,
    # sector rotation, mean reversion, ...) have their own `runner` and no lookback/skip/rank to score
    # with: say so rather than fail on a missing attribute.
    if not hasattr(cls, "lookback") or not hasattr(cls, "skip"):
        return {"as_of": None, "rows": [], "strategy": strategy_key, "market": market, "available": False,
                "note": f"{cls.name} does not rank stocks, so it has no ranked holdings to show here."}
    # A ranking narrowed by more than prices (quality_momentum's point-in-time fundamentals) would be
    # shown here WITHOUT its filter -- a list the strategy does not hold. Say so instead.
    if getattr(cls, "live_selection", True) is False:
        return {"as_of": None, "rows": [], "strategy": strategy_key, "market": market, "available": False,
                "note": f"{cls.name} filters its ranking on point-in-time fundamentals, which this live "
                        "ranking does not apply, so it has no live holdings view yet."}
    # each knob as the backtest reads it: a strategy that does not set one gets run()'s default
    rank, weighting = getattr(cls, "rank", "momentum"), getattr(cls, "weighting", "equal")
    vol_window = getattr(cls, "vol_window", 63)
    # ONE bounded query, not load_prices' per-symbol read of 16 years: a single date's ranking needs
    # only enough history to score it (lookback + skip) and to set a 200-day average. load_prices
    # takes ~70s on this universe, which is not a page load.
    need = cls.lookback + cls.skip + 260
    # With a rank buffer, what is held depends on what was held last month, so the live view has to
    # replay recent month-ends rather than rank one date: `replay_months` of them, from an empty
    # book. A parameter of this view, not a module constant -- it changes what the page shows, not
    # what the strategy does, so it must not move the strategy's fingerprint.
    hold_rank = getattr(cls, "hold_rank", None)
    buffered = bool(hold_rank and hold_rank > cls.top_n)
    if buffered:
        need += replay_months * 21
    since = pd.Timestamp.today().normalize() - pd.Timedelta(days=int(need * 1.6))
    skip = universe.non_stock_symbols(market)   # the same exclusion load_prices applies
    bars = cache.load_many_cached(market, [t for t in universe.load_universe(market) if t not in skip], since=since)
    closes, dollar_vol = {}, {}
    for sym, d in bars.items():
        if d is None or len(d) < 300:   # the same min_bars load_prices applies, so the same cohort
            continue
        closes[sym] = d["close"]
        dollar_vol[sym] = (d["close"] * d["volume"]).rolling(20, min_periods=20).mean()
    if not closes:
        return {"as_of": None, "rows": [], "strategy": strategy_key, "market": market}
    px = pd.DataFrame(closes).sort_index()
    dv = pd.DataFrame(dollar_vol).reindex_like(px)
    # the same total-return series load_prices gives the backtest's signals
    tr = corporate_actions.back_adjust(px, corporate_actions.credits(market, list(px.columns)))
    sma200 = tr.rolling(200, min_periods=200).mean()
    if px is None or px.empty:
        return {"as_of": None, "rows": [], "strategy": strategy_key, "market": market}
    # The same partial-day rule run() applies: if the cache was refreshed for part of the universe
    # the newest date prices a handful of symbols and NaNs the rest, and ranking against it returns
    # nothing at all. Use the last session with normal coverage.
    coverage = px.notna().sum(axis=1)
    full = coverage >= 0.5 * coverage.rolling(20, min_periods=1).median()
    if not full.any():
        return {"as_of": None, "rows": [], "strategy": strategy_key, "market": market}
    today = px.index[full][-1]
    key = (market, strategy_key, str(today.date()), cls.spec_id())
    if key in _SELECTION_CACHE:
        return _SELECTION_CACHE[key]

    cfg = MARKETS[market]
    bench = cache.load_cached(market, cfg.benchmark_ticker)
    bench_close = bench["close"].astype(float) if bench is not None else None
    scores = score_matrix(tr, rank, cls.lookback, cls.skip, benchmark=bench_close)
    liq_floor = cls.min_turnover_for(market) if hasattr(cls, "min_turnover_for") else None
    mom = eligible_scores(
        px.columns, px.loc[today],
        dv.loc[today] if today in dv.index else None,
        sma200.loc[today] if today in sma200.index else None,
        scores.loc[today] if today in scores.index else None,
        floor_price=cfg.screener.min_price, liq_floor=liq_floor,
        trend_filter=True, liquidity_rank_top=(cls.liquidity_top or None), trend_row=tr.loc[today],
    )
    full = sorted(mom, key=mom.get, reverse=True)
    rank_of = {sym: i + 1 for i, sym in enumerate(full)}
    replayed = 0
    if buffered:
        # The book a buffered rule would be carrying into today: replay each month-end rebalance
        # in the loaded window with the SAME selection the backtest runs, starting from nothing.
        # From an empty book the first rebalance is the plain top-N, and the replay converges on
        # the full-history book as names cycle out. Measured on India at hold_rank 40: 18 of 20
        # names match after 3 months of replay, 19 after 6, all 20 from 12 on; the US matches all
        # 20 from 3 months on. The default of 36 carries a threefold margin over the slower market.
        month_ends = pd.Series(px.index, index=px.index).resample("ME").last().dropna()
        book: list = []
        for d in month_ends:
            if d >= today or d not in scores.index or scores.loc[d].notna().sum() == 0:
                continue
            m_d = eligible_scores(
                px.columns, px.loc[d], dv.loc[d] if d in dv.index else None,
                sma200.loc[d] if d in sma200.index else None, scores.loc[d],
                floor_price=cfg.screener.min_price, liq_floor=liq_floor,
                trend_filter=True, liquidity_rank_top=(cls.liquidity_top or None), trend_row=tr.loc[d],
            )
            book = buffered_target(sorted(m_d, key=m_d.get, reverse=True), book, cls.top_n, hold_rank)
            replayed += 1
        held = buffered_target(full, book, cls.top_n, hold_rank)
    else:
        held = full[: cls.top_n]
    # The market-regime switch, read on the same close as the ranking with the same rule run() uses:
    # while it is off the strategy holds nothing, so the page must not list a book it would not hold.
    regime_state = None
    kind = cls.regime_for(market) if hasattr(cls, "regime_for") else None
    if kind:
        from . import regime as regime_mod
        rix = cls.regime_index_for(market) if hasattr(cls, "regime_index_for") else None
        on = bool(regime_mod.regime_on(kind, pd.DatetimeIndex([today]),
                                       bench_px=regime_series(market, rix, bench_close), px=tr,
                                       sma200=sma200, dv=dv, liq_floor=liq_floor).iloc[0])
        regime_state = {"kind": kind, "on": on}
        if not on:
            held = []
    # what the page lists: the top of the ranking, plus any held name the buffer kept below it
    ranked = full[: (limit or cls.top_n)]
    ranked += [sym for sym in held if sym not in set(ranked)]
    # The weight the strategy would actually put on each name, by its own rule. The RANK says what
    # it points at; the weight says where the money goes, and the two differ enough to matter --
    # the liquid-ETF defect v1.1 fixed was invisible in the ranking and obvious in the weights.
    weights = {}
    if weighting == "inverse_vol":
        vols = realised_vol(tr, vol_window)
        inv = {}
        for sym in held:
            v = vols.loc[today, sym] if sym in vols.columns and today in vols.index else float("nan")
            inv[sym] = 1.0 / float(v) if pd.notna(v) and v > 0 else 0.0
        tot = sum(inv.values())
        weights = {k: v / tot for k, v in inv.items()} if tot > 0 else {}
    else:
        weights = {sym: 1.0 / len(held) for sym in held} if held else {}
    rows = [{
        "rank": rank_of[sym], "symbol": sym, "score": round(float(mom[sym]), 4),
        "close": round(float(px.loc[today, sym]), 2),
        "turnover": (round(float(dv.loc[today, sym])) if today in dv.index and sym in dv.columns
                     and pd.notna(dv.loc[today, sym]) else None),
        "weight_pct": (round(weights[sym] * 100, 2) if sym in weights else None),
        "held": sym in set(held),
    } for sym in ranked]
    out = {"as_of": str(today.date()), "strategy": strategy_key, "market": market,
           "spec_id": cls.spec_id(), "eligible": len(mom), "top_n": cls.top_n, "rows": rows,
           "hold_rank": hold_rank if buffered else None, "replayed_rebalances": replayed,
           "regime": regime_state}
    if len(_SELECTION_CACHE) > 8:
        _SELECTION_CACHE.clear()
    _SELECTION_CACHE[key] = out
    return out


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
    hold_rank: int | None = None,
    fractional: bool = False,
    index_overlay: bool = False,
    overlay_months: int = 10,
    regime: str | None = None,
    regime_index: str | None = None,
    preloaded: tuple | None = None,
    universe_filter=None,
    credit_actions: bool = True,
):
    """Hold the top `top_n` by `rank`, rebalanced on `rebalance`.

    `rank`        momentum | vol_scaled | residual | path_quality
    `weighting`   equal | inverse_vol
    `hold_rank`   buy into the top `top_n`, hold until a name ranks outside
                  `hold_rank` (None = the plain top-`top_n` rule); see buffered_target
    `vol_target`  annualised portfolio vol to scale gross exposure to (no
                  leverage: exposure is capped at 100%)
    `index_overlay`  hold nothing while the benchmark is below its
                  `overlay_months`-month average
    `trend_filter`   require each stock above its own 200-day average
    `regime`      index_sma | breadth | both (backtesting/regime.py): at a rebalance where the
                  market is off, hold nothing; that cash earns the stored cash rate
    `universe_filter`  optional `(date, {symbol: score}) -> {symbol: score}` applied to the eligible,
                  scored pool on each rebalance before the top `top_n` are taken -- how a variant
                  (quality_momentum) narrows the pool without a second copy of this loop. A
                  `notes()` method on it, if present, adds lines to the report's caveats.
    `credit_actions`  credit a held position the cash of a special dividend or a demerger on its
                  ex-date (marketdata/corporate_actions.py), where the stored close only falls
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

    px, dv, sma200, tr = preloaded if preloaded is not None else load_prices(
        market, min_bars=lookback + skip + 2
    )

    bench_px = None
    bench_raw = cache.load_cached(market, cfg.benchmark_ticker)
    if bench_raw is not None and not bench_raw.empty:
        bench_px = bench_raw["close"]

    # scores and vols as whole matrices, once — not per symbol per rebalance
    # signals read the total-return close (load_prices); fills and valuation the traded one
    scores = score_matrix(tr, rank, lookback, skip, benchmark=bench_px)
    vols = realised_vol(tr, vol_window) if weighting == "inverse_vol" else None

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
        tr = tr.reindex(px.index)

    # Valuation uses the last known price, not today's cell: a holding that did
    # not print today is still worth its last trade, not nothing.
    marks = px.ffill()

    dates = px.index[px.index >= start_ts]
    if len(dates) < 2:
        raise ValueError("not enough trading dates in range")

    # Market-regime switch (off by default). Read on the rebalance session's close, like the
    # per-stock trend filter. Only the cash the switch creates earns interest, so an arm differs
    # from its control by the switch alone -- the control's leftover cash still earns nothing.
    regime_ok = cash_rate = None
    regime_off_days = 0
    if regime:
        from . import regime as regime_mod
        from ..marketdata import index_data
        regime_ok = regime_mod.regime_on(regime, px.index, bench_px=regime_series(market, regime_index, bench_px),
                                         px=tr, sma200=sma200, dv=dv, liq_floor=liq_floor)
        cash_rate = index_data.cash_rate_series(market, dates)[0]
    in_regime_cash, prev_day = False, None
    # special dividends and demergers: the stored close falls by the payout, the holder gets it in cash
    credits = corporate_actions.Credits.for_market(market, list(px.columns)) if credit_actions else None
    credited: dict[str, float] = {}   # symbol -> cash credited to the open position
    credited_total, credit_after = 0.0, dates[0] - pd.Timedelta(days=1)

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
        if in_regime_cash and prev_day is not None:
            # calendar-day accrual, index_core's rule (rate/252 per bar under-pays)
            r_ = float(cash_rate.get(today, float("nan")))
            if r_ == r_ and r_ > 0:
                cash *= (1.0 + r_ / 365.0) ** (today - prev_day).days
        prev_day = today
        if credits is not None:
            for s, c in credits.on(today, credit_after, holdings).items():
                cash += c * holdings[s]
                credited[s] = credited.get(s, 0.0) + c * holdings[s]
                credited_total += c * holdings[s]
            credit_after = today

        held_value = sum(
            sh * float(mark[s]) for s, sh in holdings.items()
            if s in mark.index and pd.notna(mark[s])
        )
        equity = cash + held_value

        if today in rebal_dates:
            mom = eligible_scores(
                px.columns, row,
                dv.loc[today] if today in dv.index else None,
                sma200.loc[today] if today in sma200.index else None,
                scores.loc[today] if today in scores.index else None,
                floor_price=floor_price, liq_floor=liq_floor, trend_filter=trend_filter,
                liquidity_rank_top=liquidity_rank_top, trend_row=tr.loc[today],
            )
            if universe_filter is not None:
                mom = universe_filter(today, mom)
            target = buffered_target(sorted(mom, key=mom.get, reverse=True), holdings,
                                     top_n, hold_rank)
            if overlay_ok is not None and not bool(overlay_ok.get(today, False)):
                target = []   # benchmark below its trend: hold nothing
            if regime_ok is not None:
                in_regime_cash = not bool(regime_ok.get(today, True))
                if in_regime_cash:
                    target = []   # market regime off: hold cash until a rebalance finds it on

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
                cr = credited.pop(s, 0.0)
                trades.append({
                    "symbol": s, "entry_date": ed, "entry_price": round(ep, 4),
                    "exit_date": today, "exit_price": round(fill, 4), "shares": esh,
                    "exit_reason": "REBALANCE_OUT",
                    "pnl": round((fill - ep) * esh - cost + cr, 2), "credited": round(cr, 2),
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
                        hist_r = tr.loc[:today, target].tail(win).pct_change()
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
                            credited.pop(s, None)

        held_value = sum(
            sh * float(mark[s]) for s, sh in holdings.items()
            if s in mark.index and pd.notna(mark[s])
        )
        eq_rows.append(cash + held_value)
        regime_off_days += int(in_regime_cash)
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
        cr = credited.get(s, 0.0)
        trades.append({
            "symbol": s, "entry_date": ed, "entry_price": round(ep, 4),
            "exit_date": last, "exit_price": round(price, 4), "shares": sh,
            "exit_reason": "OPEN", "pnl": round((price - ep) * sh + cr, 2), "credited": round(cr, 2),
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
        f"Costs: {cost_bps:.0f}bps per side. Ordinary dividends are excluded on BOTH the "
        "strategy and the benchmark, so absolute returns understate reality for each.",
        f"Rules: top {top_n} by {lookback}-bar momentum skipping {skip} bars, "
        f"rebalanced {rebalance}, ranked within the top "
        f"{liquidity_rank_top or 'all'} by dollar volume, liquidity floor "
        f"{cfg.currency_symbol}{liq_floor:,.0f} 20d dollar volume"
        + (", held only above the 200-day average." if trend_filter else "."),
        "'r_multiple' here is notional-relative (no stop exists), so it is NOT "
        "comparable to the gated strategy's stop-relative R.",
    ]
    if regime:
        notes.append(
            f"Regime filter '{regime}' (index close > its {regime_mod.INDEX_SMA_DAYS}-day average"
            f" / >= {regime_mod.BREADTH_MIN_PCT:g}% of liquid names above their 200-day): off on "
            f"{100.0 * regime_off_days / len(dates):.1f}% of sessions, held in cash at the stored cash rate.")
    if credits is not None:
        notes.append(credits.note() + f" Credited to this run's holdings: {cfg.currency_symbol}{credited_total:,.0f}.")
    if universe_filter is not None and hasattr(universe_filter, "notes"):
        notes += list(universe_filter.notes())
    perf = metrics.compute(
        equity=eq, positions_open=pos, trades=tdf, max_open_positions=top_n,
        costs_paid=costs_total, bench_close=bench_close, notes=notes,
    )
    return tdf, perf, eq, pos


# Reference documentation for the web app's Strategy page. The baseline is not
# a `Strategy` subclass (see the module docstring), so it documents itself
# here; its parameters are read live from build_parser(), so they cannot drift.
# Update this block in the same change as any change to how the baseline works.
from ..strategies.base import PortfolioStrategy


DOC = {
    "key": "momentum_baseline",
    "name": "Momentum baseline",
    "description": "Rank liquid stocks by their 12-month return ending one month ago, hold the top {top_n} "
                   "equal-weighted, rebalance at every month-end; the benchmark every strategy must beat.",
    "status": "Reference portfolio, not a screener strategy. Beats the index in India; not in the US (see research/momentum-trend-research.md).",
    "thesis": "Stocks that have outperformed over the past year tend to keep outperforming for the next few months "
              "-- cross-sectional momentum, documented by Jegadeesh and Titman (1993) and in many markets since. "
              "If that holds, simply owning the strongest names should beat the index after costs. This is the "
              "plainest form of the idea, kept naive on purpose: a strategy that cannot beat it is not adding "
              "anything with its extra rules.",
    "how_it_works": (
        "Once a month, on the last stored session of the month, the whole universe is filtered, ranked by its "
        "past-year return and the top {top_n} are held at equal weight until the next month-end. Nothing "
        "happens between month-ends.",
        "The steps, in order, on each month-end: drop stocks below the price and turnover floors or not above "
        "their 200-day average; keep the {liquidity_top} most liquid of the rest; score each by its 12-1 "
        "momentum; sell every holding that is not in the new top {top_n}; resize the holdings that stay and "
        "buy the new names. Every trade is at that session's close. Entry and Exit give each test exactly.",
        "There is no stop, no target and no entry trigger. The rank is the whole rule, so a holding is "
        "replaced, never stopped out.",
        "The flags under Parameters can change the window, the number held, the weighting and the costs for an "
        "experiment. The strategy itself is the values on this page: {lookback}-session momentum skipping "
        "{skip}, top {top_n}, {cost_bps}bps a side, month-end rebalance, trend filter on.",
    ),
    "entry_rules": (
        "Universe. Every stock stored for the market, minus ETFs, liquid funds and other listings that are not "
        "operating companies, with at least {lookback} + {skip} + 2 stored sessions of history.",
        "Eligible on the month-end session. A stock must pass all four tests on that session's close.\n\n"
        "- **Price floor:** close at or above $10 in the US (on split-adjusted history, see the caveats); no "
        "floor in India.\n"
        "- **Turnover floor:** 20-session average of close × volume at or above $10 million a day in the US, "
        "₹50 crore in India (the market's screener floor).\n"
        "- **Trend:** close strictly above its 200-session simple moving average, which needs a price on each "
        "of the last 200 sessions.\n"
        "- **Score exists:** the stock has a close on both ends of the momentum window.",
        "Liquid pool. If more than {liquidity_top} stocks pass, only the {liquidity_top} with the highest "
        "20-session average turnover are ranked; the rest are dropped before ranking. With the turnover floor "
        "in place this rarely binds.",
        "Momentum score (12-1). Close {skip} sessions ago ÷ close {lookback} + {skip} sessions ago − 1: a full "
        "{lookback}-session (12-month) return that ends one month ago, so it starts about 13 months back. "
        "Example: at the end of January 2025 it is roughly the return from late December 2023 to late "
        "December 2024. Leaving out the latest month avoids its short-term reversal. The usual academic "
        "12-1 (Fama-French's momentum factor, months t−12 to t−2) covers eleven months; this one covers twelve.",
        "Selection. Highest score first; the top {top_n} are held. Any score qualifies, including a negative "
        "one. With fewer than {top_n} eligible stocks it holds only those, each at the larger equal weight.",
        "Weighting. Equal: each name held is sized to 1 ÷ (names held) of the account's value -- cash plus "
        "holdings at their last price. Holdings that stay in the top {top_n} are resized to that weight every "
        "month, so a winner is trimmed and a laggard topped up. Whole shares only, rounded down, so a stock "
        "priced above its slot is not bought unless `--fractional`. `--weighting inverse_vol` sizes by "
        "1 ÷ 63-session volatility instead (the `--vol-window` default).",
        "Fill and cost. Every trade is at the month-end session's close: a buy pays the close plus {cost_bps}bps, "
        "a sale receives the close minus {cost_bps}bps. Sales are done first, then buys in rank order; if cash "
        "runs short, a buy is cut to the whole shares the cash covers.",
        "When it holds cash. When no stock is eligible, and for whatever rounding to whole shares leaves over. "
        "Optional `--index-overlay` (off): hold nothing while the benchmark's month-end close is not above the "
        "average of its last 10 month-end closes (`--overlay-months`), read from an earlier month-end so the "
        "decision uses only known prices. Optional `--vol-target` (off): scale every position down so the "
        "basket's trailing volatility is at most the target, never above 100% invested.",
    ),
    "exit_rules": (
        "Sold at a month-end. A holding is sold in full at that session's close, less {cost_bps}bps, when it is "
        "not in the new top {top_n}: outranked, or failing a test that day -- the close at or below its 200-day "
        "average, turnover under the floor, price under the floor, or outside the {liquidity_top}-name liquid "
        "pool.",
        "Resized at a month-end. A holding that stays in the top {top_n} is sold down or bought up to the equal "
        "weight, at the same close and cost.",
        "Nothing sells between month-ends. There is no stop and no target: a stock that closes below its "
        "200-day average on the 3rd is held until the month-end test, and a fall of any size in between is "
        "held.",
        "No price that day. A holding with no close on the month-end session cannot be sold; it is carried at "
        "its last price until a month-end on which it trades.",
        "End of the test. Whatever is still held is valued at the final close, with no exit cost.",
    ),
    "caveats": (
        "**Survivorship bias.** The universe is today's listed names; companies delisted during the window are "
        "absent, which flatters every backtest here.",
        "**India runs made before 2026-10-22 sat in cash for long stretches.** Stored prices then carried a few "
        "weekend dates priced for a handful of stocks (2010-02-06, 2012-01-07, 2012-03-03, 2012-09-08). Each "
        "left a gap in every other stock's last 200 sessions, so its 200-day average was missing, and the stock "
        "ineligible, for the next 200 sessions: almost nothing passed from February to October 2010 or from "
        "January 2012 to June 2013. Those dates are now removed from stored prices; a run made before then "
        "still shows the cash months.",
        "**A stock with no bar on a real session loses its 200-day average for 200 sessions.** The average needs "
        "a price on each of the last 200 sessions of the whole market. A stock the source did not price on a "
        "session most of the market traded — a Diwali Muhurat hour, a Saturday budget day — fails the trend "
        "test for the next 200 sessions.",
        "**US: a $10 floor on split-adjusted prices.** Stored history is divided by every later split, so a "
        "stock that split heavily reads under $10 in its early years and is excluded exactly while it was "
        "rising (NVDA does not clear it until mid-2020). The gated backtests drop the price floor for this "
        "reason; this one keeps it.",
        "**Ordinary dividends are left out** of both the strategy and the benchmark (SPY, Nifty 500): stored "
        "prices are split-adjusted closes only, so absolute returns understate both.",
        corporate_actions.CAVEAT_HELD,
        "**The live ranking is not quite the backtest.** The current-holdings ranking skips the turnover floor "
        "for this strategy (it declares no per-market floor) and needs 300 stored sessions, so it can list names "
        "the backtest would not hold.",
        "**A run that ends mid-month rebalances on its last session**, because the last stored day counts as "
        "that month's month-end.",
        "**Settings change the answer.** Results depend on the rebalance cadence and N; compare runs with the "
        "same settings. `--index-overlay`, `--vol-target` and the other `--rank` signals are experiments, not "
        "the baseline. The overlay reads the previous month-end's comparison, or the one before it when the "
        "month's last session falls before the calendar month-end.",
    ),
    "screen": False,
}


def build_parser() -> argparse.ArgumentParser:
    from ..strategies import portfolio_strategies
    ap = argparse.ArgumentParser(description="Cross-sectional momentum portfolios")
    # Which registered portfolio strategy's tunables to run. Its class attributes become the
    # argparse DEFAULTS (see main), so a strategy is the configuration that was measured rather
    # than a set of flags someone has to remember -- and an explicit flag still overrides it.
    ap.add_argument("--strategy", default="momentum_baseline", choices=sorted(portfolio_strategies()),
                    help="registered portfolio strategy to run; its own settings replace the defaults below")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--top-n", type=int, default=10, help="number of stocks held after each rebalance")
    ap.add_argument("--lookback", type=int, default=TRADING_DAYS, help="momentum window in sessions: the score is the return over this many sessions, "
                         "ending --skip sessions ago")
    ap.add_argument("--skip", type=int, default=21, help="most recent sessions left out of the score; 21 (one month) with a 252 lookback "
                         "is the 12-1 convention")
    ap.add_argument("--rebalance", default="ME", help="pandas period alias; trades on the last stored session of each period "
                         "(ME month-end, QE quarter-end, W-FRI weekly)")
    ap.add_argument("--no-trend-filter", action="store_true", help="drop the requirement that the close be above its 200-day average on the "
                         "rebalance session")
    ap.add_argument("--cost-bps", type=float, default=5.0,
                    help="cost per side in basis points: added to every buy's close, taken off every sale's")
    ap.add_argument("--fractional", action="store_true",
                    help="allow fractional shares — without it any stock priced "
                         "above its per-name allocation is silently skipped")
    ap.add_argument("--rank", default="momentum", choices=list(RANKERS),
                    help="ranking signal: raw momentum, volatility-scaled "
                         "(Barroso-Santa-Clara), market-residual (Blitz), path "
                         "quality (share of positive days), or rs_range (position of "
                         "the relative-strength line in its own range)")
    ap.add_argument("--vol-window", type=int, default=63,
                    help="bars of realised volatility for inverse_vol weights and the vol target (vol_scaled ranking uses the lookback)")
    ap.add_argument("--weighting", default="equal", choices=["equal", "inverse_vol"],
                    help="equal capital, or 1 / each name's --vol-window volatility, scaled to sum to 100%%")
    ap.add_argument("--vol-target", type=float, default=None,
                    help="annualised portfolio vol to scale gross exposure to, "
                         "e.g. 0.15. Never leverages — exposure caps at 100%%")
    ap.add_argument("--hold-rank", type=int, default=None, metavar="N",
                    help="rank buffer: buy into the top --top-n, hold a name until it ranks outside N "
                         "(default off = the plain top-N rule)")
    ap.add_argument("--index-overlay", action="store_true",
                    help="hold nothing while the benchmark's month-end close is not above the average "
                         "of its last --overlay-months month-end closes, read a month late "
                         "(cut SPY's max drawdown -50.8%% -> -23.0%%)")
    ap.add_argument("--overlay-months", type=int, default=10,
                    help="months in the --index-overlay average of the benchmark's month-end closes")
    from . import regime as _rg
    ap.add_argument("--regime-index", default=None, metavar="TICKER",
                    help="the index the --regime switch reads (default: the market's broad benchmark)")
    ap.add_argument("--regime", default=None, choices=[*_rg.KINDS, "off"],
                    help=f"market-regime switch read at each rebalance close: index_sma = benchmark above "
                         f"its {_rg.INDEX_SMA_DAYS}-day average, breadth = at least {_rg.BREADTH_MIN_PCT:g}%% of "
                         "liquid names above their own 200-day, both = both. When off, hold cash at the stored "
                         "cash rate. Default: the strategy's own per-market setting (regime_for), else off; "
                         "'off' switches a default regime off, for a control run")
    ap.add_argument(
        "--min-turnover", type=float, default=None,
        help="20-day average turnover floor in account currency (overrides the market "
        "config). This is the real universe control — see --liquidity-top.",
    )
    ap.add_argument(
        "--liquidity-top", type=int, default=1000,
        help="rank only the N names with the highest 20-day average turnover among those that pass "
        "the floors (0 = no cutoff). "
        "Guards against the rank filling with speculative microcaps.",
    )
    ap.add_argument("--no-ingest", action="store_true",
                    help="skip updating the viewer database after the run")
    return ap


#: class attribute on a PortfolioStrategy -> the run() keyword it sets
TUNABLES = {"top_n": "top_n", "lookback": "lookback", "skip": "skip", "rebalance": "rebalance",
            "cost_bps": "cost_bps", "rank": "rank", "weighting": "weighting",
            "vol_target": "vol_target", "min_turnover": "min_turnover", "vol_window": "vol_window",
            "hold_rank": "hold_rank",
            "liquidity_top": "liquidity_top"}


def _turnover_tag(value: float, cfg) -> str:
    """`_turnover10cr` / `_turnover20m` — slug-safe and readable in the market's own unit."""
    return (f"_turnover{value / 1e7:g}cr" if cfg.currency_code == "INR"
            else f"_turnover{value / 1e6:g}m")


def strategy_defaults(key: str, market: str) -> dict:
    """The registered strategy's tunables, as argparse defaults.

    A strategy IS its configuration: the measured result belongs to top-50 at a turnover floor
    with honest costs, not to whatever the flags happened to be. Reading the defaults off the
    class keeps the run and the documented spec the same thing, and keeps the fingerprint
    meaningful -- a tunable that lives only in a shell command is not versioned at all.
    """
    from ..strategies import portfolio_strategies
    cls = portfolio_strategies()[key]
    out = {arg: getattr(cls, attr) for attr, arg in TUNABLES.items() if hasattr(cls, attr)}
    # The turnover floor is in the market's own currency, so one class attribute cannot serve both
    # markets; a strategy that cares declares min_turnover_for() and resolves it per run.
    if hasattr(cls, "min_turnover_for"):
        out["min_turnover"] = cls.min_turnover_for(market)
    # Likewise the market-regime switch: adopted where it was measured to help (regime_for), so the
    # same strategy can switch it on in one market and leave it off in another.
    if hasattr(cls, "regime_for"):
        out["regime"] = cls.regime_for(market)
    if hasattr(cls, "regime_index_for"):
        out["regime_index"] = cls.regime_index_for(market)
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The command line, with the named strategy's registered tunables as its defaults.

    Split out of main() so another runner can run a registered ranking strategy exactly as its
    own runs do -- `combination` runs momentum_vol_scaled as a sleeve -- instead of restating
    which flag maps to which argument and drifting from it.
    """
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--strategy", default="momentum_baseline")
    pre.add_argument("--market")
    chosen, _ = pre.parse_known_args(argv)
    ap = build_parser()
    if chosen.market:
        ap.set_defaults(**strategy_defaults(chosen.strategy, chosen.market))
    return ap.parse_args(argv)


def changed_flags(args: argparse.Namespace) -> list[str]:
    """The command-line flags whose values differ from the strategy's own defaults, as typed.

    What the Reproduce line must add to `--strategy --market --start` to repeat THIS run. It used to
    name only those three, so the report of a `--min-turnover 100000000` experiment told the reader
    to run the default strategy -- a different run, with no sign of the difference.
    """
    plain = parse_args(["--strategy", args.strategy, "--market", args.market, "--start", str(args.start)])
    out = []
    for act in build_parser()._actions:
        dest = act.dest
        if dest in ("help", "strategy", "market", "start", "no_ingest") or not act.option_strings:
            continue
        mine, base = getattr(args, dest, None), getattr(plain, dest, None)
        if mine == base:
            continue
        flag = act.option_strings[-1]
        if isinstance(act, argparse._StoreTrueAction):
            out.append(flag)
        elif isinstance(act, argparse._StoreFalseAction):
            out.append(flag)
        elif isinstance(mine, list):
            out += [f"{flag} {shlex.quote(str(x))}" for x in mine]
        else:
            out.append(f"{flag} {shlex.quote(str(mine))}")
    return out


def run_args(args: argparse.Namespace, universe_filter=None):
    """run() for a parsed command line: the one place a flag is mapped to an argument."""
    return run(
        args.market, args.start, top_n=args.top_n, lookback=args.lookback,
        skip=args.skip, rebalance=args.rebalance,
        trend_filter=not args.no_trend_filter, cost_bps=args.cost_bps,
        liquidity_rank_top=args.liquidity_top or None,
        min_dollar_volume=args.min_turnover,
        fractional=args.fractional,
        rank=args.rank, weighting=args.weighting, vol_target=args.vol_target,
        vol_window=args.vol_window,
        index_overlay=args.index_overlay, overlay_months=args.overlay_months,
        regime=None if args.regime == "off" else args.regime,
        regime_index=args.regime_index if args.regime != "off" else None,
        hold_rank=args.hold_rank, universe_filter=universe_filter,
    )


def main(argv: list[str] | None = None, universe_filter=None, run_suffix: str = "",
         reproduce_extra: tuple = ()) -> dict | None:
    """`argv` so the job runner can call this in-process, the way backtest.main is called.

    `universe_filter` and `run_suffix` are for a runner that reuses this one with a narrowed pool
    (quality_momentum): the filter goes to run(), the suffix into the run name so its variants do
    not overwrite each other, and `reproduce_extra` onto the Reproduce line.
    """
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    from ..strategies import portfolio_strategies
    args = parse_args(argv)

    cfg = MARKETS[args.market]
    tdf, perf, eq, pos = run_args(args, universe_filter=universe_filter)
    from ..paths import run_dir

    # NOT `run`: this module's main entry point is also called run(), and a
    # local of that name shadows it for the whole function body
    run_name = (f"{args.start}_top{args.top_n}_{args.rank}{args.lookback}_{args.rebalance}"
                f"_{args.cost_bps:g}bps"
                + (f"_{args.weighting}" if args.weighting != "equal" else "")
                + (f"_vt{args.vol_target:g}" if args.vol_target else "")
                + ("_overlay" if args.index_overlay else "")
                + (f"_regime-{args.regime}" if args.regime else "")   # "off" -> _regime-off, the control
                + (f"-on-{args.regime_index}" if args.regime_index and args.regime and args.regime != "off" else "")
                + (f"_hold{args.hold_rank}" if args.hold_rank and args.hold_rank > args.top_n else "")
                + ("_frac" if args.fractional else "")
                # In the market's own unit, never %g: a Rs10cr floor formats as "1e+08", and
                # run_dir slugs "+" to "-", so the run was filed as "turnover1e-08" -- a name that
                # reads as ten nano-rupees. The run name is how a run is identified in the portal.
                + (_turnover_tag(args.min_turnover, cfg) if args.min_turnover else "")
                + ("_noTrendFilter" if args.no_trend_filter else "")
                + run_suffix
                # The spec id goes in the NAME because that is the only record of which rule set
                # produced a report: ingest lifts it out with a regex (web/ingest.spec_id_of) and
                # the Strategies page groups runs by it. Without it a portfolio run shows "—" for
                # its version and cannot be mapped back to the rules that made it, which is the
                # whole reason these strategies were registered and fingerprinted.
                + f"_{portfolio_strategies()[args.strategy].spec_id()}")
    out = run_dir(args.market, args.strategy, run_name)
    tdf.to_csv(out / "trades.csv", index=False)
    pd.DataFrame({
        "equity": eq, "positions_open": pos,
        "drawdown_pct": metrics.drawdown_series(eq) * 100,
    }).to_csv(out / "equity.csv")

    # Resolve the benchmark BEFORE reporting, and recompute its figures against the series that is
    # actually named: run() computed them against the market's default, and relabelling those
    # without recomputing would print a Nifty 500 number under a Smallcap 250 heading.
    _cls = portfolio_strategies()[args.strategy]
    _key = (getattr(_cls, "benchmark_key", None) or {}).get(args.market)
    bench_ticker = cfg.broad_index_symbols.get(_key) if _key else None
    bench_name = _key
    if bench_ticker is None or cache.load_cached(args.market, bench_ticker) is None:
        if _key:   # declared but not stored: say so rather than silently reporting a different index
            logger.warning("%s declares benchmark %s for %s but it is not stored; falling back to %s",
                           args.strategy, _key, args.market, cfg.benchmark_symbol)
        bench_ticker, bench_name = cfg.benchmark_ticker, cfg.benchmark_symbol
    bench_raw = cache.load_cached(args.market, bench_ticker)
    bc = bench_raw["close"].reindex(eq.index).ffill() if bench_raw is not None else None
    if bc is not None:
        for _k, _v in metrics.benchmark_stats(bc).items():
            setattr(perf, _k, _v)
    perf.benchmark_name = f"{bench_name} ({bench_ticker})"

    print()
    print(metrics.format_report(perf, cfg.currency_symbol, args.top_n))
    print()
    print(metrics.format_equity_curve(eq, bc))
    print(f"\nRun dir -> {out}")
    result = {"perf": perf, "run_dir": str(out), "trades": int(len(tdf))}

    try:
        from . import report as report_mod

        # The strategy IS its tunables, so the reproduce line names it rather than respelling
        # every flag -- and unlike the old spelling it cannot drift from what the page documents.
        runner = getattr(portfolio_strategies()[args.strategy], "runner", "baseline")
        cmd = " ".join([f"python3 -m swing_screener.backtesting.{runner} --strategy {args.strategy} "
                        f"--market {args.market} --start {args.start}", *changed_flags(args), *reproduce_extra])
        md = report_mod.write_report(
            out,
            f"{cfg.name} — {portfolio_strategies()[args.strategy].name} (top {args.top_n}), {args.start} onward",
            perf, eq, pos, tdf, cfg.currency_symbol, args.top_n, bc, cmd,
        )
        print(f"Report -> {md}")
    except Exception as e:
        print(f"(markdown report not generated: {type(e).__name__}: {e})")
    # index the new report so the viewer shows it without a server restart
    if not getattr(args, "no_ingest", False):
        from ..web.ingest import ingest_after_run
        ingest_after_run()
    return result


if __name__ == "__main__":
    main()


# --- registry entry -----------------------------------------------------------

#: The baseline's real tunables. Declared as class attributes rather than read
#: from the argparse defaults so the fingerprint describes the STRATEGY, not
#: whatever flags a particular run happened to pass.
VS_DOC = {
    "key": "momentum_vol_scaled",
    "name": "Volatility-scaled momentum",
    "description": "Rank liquid stocks by 12-1 momentum divided by realised volatility, hold the top {top_n} "
                   "weighted inverse to volatility, rebalance at every month-end.",
    "status": (
        "EARNS ITS EDGE IN INDIA, NOT IN THE US. Out-of-sample (verify, 2022-01-01 to 2026-10-26) India "
        "returns 22.21% CAGR, +11.06 excess over the Smallcap 250, max drawdown -32.1%, with NO market filter, "
        "which is how it runs from v1.7. The India market filter adopted in v1.5 and moved to the Smallcap 250 "
        "in v1.6 failed its pre-registered verify run against that same version without it: 14.52% CAGR, +3.37 "
        "excess, -38.5% drawdown. The criterion, written before the run, asked for a drawdown at least 5 points "
        "shallower and a CAGR no more than 2 points lower, and it failed both. 2022 is why: the month-end "
        "200-day test sold into the small-cap correction and bought back late (-28.5% against -9.9%), and 2023 "
        "made +71.4% against +90.2%. In-sample (optimise, 2013-2021) it had looked strong -- 26.13% CAGR and "
        "-25.2% drawdown against 25.31% and -50.5% -- which is the gap a hold-out exists to expose. Down years "
        "remain without it, 2022 at -9.9% and 2025 at -7.9% out-of-sample. Do NOT re-adopt the filter on its "
        "in-sample record; a different filter is a new version with its own single verify run. The US runs "
        "without a filter. "
        "Everything below is LEGACY context, measured before stages and before the filter. "
        "EARNS ITS EDGE IN INDIA, NOT IN THE US. Measured on current code from 2010 against the Nifty "
        "Smallcap 250 -- the honest control, because it drops and replaces constituents and so carries the "
        "failures a survivor-only universe cannot. India: 19.18% CAGR against the index's 11.68%, +7.51 "
        "excess, Sharpe 0.95, max drawdown -51.0% against the index's -60.8%. It holds in both halves of the "
        "window, +7.88 before 2019 and +7.12 after, and in 46 of 56 rolling 36-month windows (82%, median "
        "+6.00) -- but unevenly: the worst three years trail by 11.75 points, and 6 of 16 calendar years "
        "trail, 2020 by 15.3. From 2020 alone it adds +4.97 (24.90% against 19.93%). "
        "Chosen in v1.0 from 18 variants on worst half-period excess, and re-chosen on 2026-10-24 from 24 on "
        "current data (research/selection-vs-drag.md §12): of the twelve unbuffered variants it still has "
        "the best worst half (+7.12), though every one of them now holds in both halves, so that test "
        "separates it less sharply than it did. Picking a variant each year from trailing data only keeps "
        "79% of the hindsight pick's excess; applied to this variant's +7.51 that is about +5.9 -- TAKE "
        "ROUGHLY +5.9 AS THE EXPECTATION, NOT THE HEADLINE. A rank buffer (hold_rank, off) improved excess "
        "in 43 of 48 like-for-like pairs in that sweep and waits on a run to set its width. "
        "About 1.7 points of excess over the Nifty 500 (10.01% a year) is small-cap segment beta, which is "
        "why the control is the segment. "
        "US: every variant tested trails IWM over the cycle. This one returns 6.13% against 9.09%, -2.96 "
        "excess, Sharpe 0.35, with a deeper drawdown than the index (-49.5% against -42.3%), and trails in "
        "12 of 16 years. Against SPY the gap is -5.90, about 2.9 points of which is the 2010-2026 lead of "
        "large caps over small rather than anything this strategy did. From 2020 it shows +4.96, but a "
        "walk-forward over those years keeps 10% of the hindsight result: the choice there is luck. Two "
        "reasons, one now measured. The eligible pool is far larger -- about 657 names at the "
        "${min_turnover_usd_m} million floor against India's 186, so the top {top_n} are the top 3% of "
        "candidates rather than the top 11%, further into the noise -- and narrowing it helps at every "
        "step: excess over IWM from 2010 is -3.04 at a $20 million floor, -1.52 at $50 million, -1.05 at "
        "$100 million and -0.20 at $200 million, where about 155 names make the top {top_n} roughly as "
        "selective as India's. That recovers about 2.8 points and still does not clear the index: even at "
        "$200 million the years before 2019 trail by 4.75, and with 50 names the floor shows no pattern at "
        "all. The rest is the market: the US top momentum decile sits 0.47 above its median against "
        "India's 0.76 (measured 2026-10-17), so there is less spread to rank on."
    ),
    "thesis": "Momentum pays, but raw momentum ranks the most volatile names highest, so it buys the stocks most "
              "likely to give the gain back. Dividing by realised volatility asks which stocks rose most PER UNIT "
              "of risk taken to get there, which is a different and steadier question. The volatility scaling "
              "follows Barroso and Santa-Clara (2015), who scale the momentum portfolio by its own volatility; "
              "here each stock's score is scaled instead.",
    "how_it_works": (
        "Once a month, on the last stored session of the month, every liquid stock is scored by its past-year "
        "return per unit of volatility, and the top {top_n} are held, weighted inverse to their volatility, until "
        "the next month-end. Nothing happens between month-ends.",
        "The steps, in order, on each month-end: drop stocks below the turnover and price floors or not above "
        "their 200-day average; score the rest; sell every holding not in the new top {top_n}; resize the "
        "holdings that stay and buy the new names. Every trade is at that session's close. Entry and Exit give "
        "each test exactly.",
        "Eligibility is a turnover floor, not a liquidity rank: the floor is the universe control. The momentum "
        "premium concentrates in smaller names, and without a floor the rank fills with stocks nobody can "
        "trade.",
        "There is no stop, no target and no trigger to wait for. The rank IS the trade rule, which is why this "
        "has a Holdings tab rather than setups.",
        "No market filter, in either market: the book stays invested through a market decline and relies on "
        "the per-stock 200-day test to drop names that break down. India ran a 200-day market filter from v1.5; "
        "v1.7 dropped it after it failed its verify run on 2022 onward, where it sold into the correction and "
        "bought back late. It remains available as `--regime index_sma` for research.",
    ),
    "entry_rules": (
        "Universe. Every stock stored for the market, minus ETFs, liquid funds and other listings that are not "
        "operating companies (v1.1), with at least {lookback} + {skip} + 2 stored sessions of history.",
        "Eligible on the month-end session. A stock must pass all four tests on that session's close.\n\n"
        "- **Turnover floor:** 20-session average of close × volume at or above ₹{min_turnover_cr} crore a day "
        "in India, ${min_turnover_usd_m} million in the US.\n"
        "- **Price floor:** close at or above $10 in the US (on split-adjusted history, see the caveats); no "
        "floor in India.\n"
        "- **Trend:** close strictly above its 200-session simple moving average, which needs a price on each "
        "of the last 200 sessions.\n"
        "- **Score exists:** the stock has a close on both ends of the window and a volatility reading.",
        "No liquidity rank. Every stock that passes is ranked; there is no most-liquid-N cutoff (liquidity_top "
        "is {liquidity_top}).",
        "Score. 12-1 momentum ÷ volatility.\n\n"
        "- **Momentum:** close {skip} sessions ago ÷ close {lookback} + {skip} sessions ago − 1 -- a full "
        "{lookback}-session (12-month) return ending one month ago.\n"
        "- **Volatility:** the standard deviation of daily returns over the same {lookback} sessions, also "
        "ending {skip} sessions ago, from at least half of them.\n\n"
        "Example: two stocks both up 60%; one with 2% daily swings scores 30, one with 4% swings scores 15, so "
        "the steadier one ranks first.",
        "Selection. Highest score first; the top {top_n} are held. Any score qualifies, including a negative "
        "one -- there is no absolute-momentum test beyond the 200-day filter. With fewer than {top_n} eligible "
        "stocks it holds only those.",
        "Weighting. Inverse volatility: each name's weight is 1 ÷ its annualised volatility of daily returns "
        "over the last {vol_window} sessions up to the month-end (no skip), divided by the sum over the names "
        "held, so the weights add to 100%. A name with no volatility reading gets zero weight and is not bought. "
        "Holdings that stay are resized to their new weight every month. Whole shares only, rounded down.",
        "Fill and cost. Every trade is at the month-end session's close: a buy pays the close plus {cost_bps}bps, "
        "a sale receives the close minus {cost_bps}bps. Sales are done first, then buys in rank order; if cash "
        "runs short, a buy is cut to the whole shares the cash covers.",
        "When it holds cash. Only when no stock is eligible, and for whatever rounding to whole shares leaves "
        "over. Otherwise it is fully invested: there is no market filter (India's was dropped in v1.7 after it "
        "failed verification) and no volatility target.",
    ),
    "exit_rules": (
        "Sold at a month-end. A holding is sold in full at that session's close, less {cost_bps}bps, when it is "
        "not in the new top {top_n}: outranked, or failing a test that day -- the close at or below its 200-day "
        "average, turnover under the floor, or (US) price under $10.",
        "Resized at a month-end. A holding that stays in the top {top_n} is sold down or bought up to its new "
        "inverse-volatility weight, at the same close and cost.",
        "Nothing sells between month-ends. A position that falls is held until the month-end test drops it -- "
        "that is what makes the drawdown a small-cap drawdown (-51%) rather than a stop-managed one.",
        "No price that day. A holding with no close on the month-end session cannot be sold; it is carried at "
        "its last price until a month-end on which it trades. Whatever is still held at the end of a test is "
        "valued at the final close, with no exit cost.",
    ),
    "caveats": (
        "**Survivorship inflates this by an unknown but probably modest amount.** No price series in the universe "
        "ends early, but that is not the same as nothing failing: Indian stocks that collapse mostly keep trading, "
        "so the tape carries the whole fall -- 12% of the pre-2012 cohort is down 90%+ from its peak and 2% down "
        "99%+, RCOM and EDUCOMP among them, every bar of the way. What is missing is outright DELISTINGS, whose "
        "history Yahoo deletes, and acquisitions, which usually exit at a premium and so bias the measured return "
        "the other way. A ranking strategy sells a collapsing name long before the bottom, so the part that would "
        "have hurt it most is the part that is present.",
        "**Costs decide how much is left.** In India the excess over small caps is +10.48 at 25bps, +7.51 at "
        "{cost_bps}bps and +1.82 at 100bps; in the US -0.01, -2.96 and -8.94. {cost_bps}bps is the defensible "
        "assumption for monthly rebalancing of small caps and is the default here; turnover runs about 4.6x "
        "the book a year, and a flat per-trade figure is still a simplification of a real spread.",
        "**A stock with no bar on a real session loses its 200-day average for 200 sessions.** The average needs "
        "a price on each of the last 200 sessions of the whole market. A stock the source did not price on a "
        "session most of the market traded — a Diwali Muhurat hour, a Saturday budget day — fails the trend "
        "test for the next 200 sessions.",
        "**US: a $10 floor on split-adjusted prices.** Stored history is divided by every later split, so a "
        "stock that split heavily reads under $10 in its early years and is excluded exactly while it was "
        "rising (NVDA does not clear it until mid-2020).",
        "**The drawdown is a small-cap drawdown.** -51% peak to trough in India. It is better than the "
        "segment's -60.8%, which is a real improvement, but it is not a comfortable ride and the holding "
        "period is years. In the US it is deeper than the index's: -49.5% against -42.3%.",
        "**Benchmarked against the Nifty Smallcap 250 (US: IWM), not the broad index.** Measuring this against "
        "the Nifty 500 counts segment beta as skill. Ordinary dividends are left out of both the strategy "
        "and the benchmark: stored prices are split-adjusted closes only.",
        corporate_actions.CAVEAT_HELD,
        "**Down years are part of it, and a market filter did not fix them.** Out-of-sample the book fell 9.9% "
        "in 2022 and 7.9% in 2025. A {regime_sma_days}-day market filter was tried for India (v1.5-1.6): it "
        "looked strong in-sample, halving the 2013-2021 drawdown, and failed its verify run -- a month-end "
        "average reacts late to a fast correction, so it sold low and re-bought high. Do not re-adopt it on its "
        "in-sample record; a different filter is a new version with its own single verify run.",
    ),
}


class VolScaledMomentumStrategy(PortfolioStrategy):
    """The measured configuration, as a versioned strategy rather than a shell command.

    Separate from MomentumBaselineStrategy on purpose: a baseline has to stay naive to remain a
    control. Tuning the thing you compare against leaves nothing to compare against.
    """

    key = VS_DOC["key"]
    doc = VS_DOC                 # the renderer reads this; naming it there was the bug it replaced
    family = "momentum_vol_scaled"
    version = "1.7"
    changelog = (
        ("1.7", "2026-10-27",
         "India runs without a market filter again. The filter adopted in v1.5 (and pointed at the Smallcap "
         "250 in v1.6) failed its pre-registered verify run, India 2022-01-01 to 2026-10-26, against the same "
         "version with --regime off: 14.52% CAGR against 22.21%, excess +3.37 against +11.06, max drawdown "
         "-38.5% against -32.1%. The criterion, written before the run, asked for a drawdown at least 5 points "
         "shallower and a CAGR no more than 2 points lower; it failed both. 2022 is why: the month-end 200-day "
         "test sold into the small-cap correction and bought back late (-28.5% against -9.9%), and it went to "
         "cash at the February 2023 low and re-entered after the rebound. The test was between exactly these "
         "two versions, so dropping the filter is the decision it was set up to make, not a re-tune on the "
         "hold-out. In-sample it had looked strong (2013-2021: drawdown -25.2% against -50.5%); this is the "
         "gap a hold-out exists to expose. The switch stays available as --regime index_sma for research. "
         "Bumped by hand: regime_by_market is not numeric, so the fingerprint does not move."),
        ("1.6", "2026-10-27",
         "India's market filter reads the Nifty Smallcap 250 -- the segment the book holds and is judged "
         "against -- instead of the broad Nifty 500. In the optimise window its one losing year was 2018 "
         "(-28.1%): small caps fell 26.8% while the Nifty 500 fell 3.4% and stayed above its 200-day average, "
         "so the switch never moved to cash, and the filter did slightly worse than none (-25.5%). Estimated "
         "on v1.5's filter-off run by holding cash in each month the chosen index ended the previous month "
         "at or below its 200-day average (a method that reproduces v1.5's own filter year by year, 2018 "
         "-27.8% against -28.1%): 2018 -28% -> -15%, CAGR 24.3% -> 26.1%, month-end max drawdown -30% -> -18%; "
         "the cost is slower re-entry after a crash (2020 +27.5% -> +15.5%). The index was chosen after "
         "looking at 2018, so this is in-sample; the verify run (2022 onward, which holds a small-cap "
         "correction) is its test, against the criterion already written in the status. The 200-day "
         "length and the rule are unchanged; the US still runs without a filter."),
        ("1.5", "2026-10-26",
         "India adopts the market-regime switch by default: on a month-end where the benchmark closes at "
         "or below its 200-day average the book holds cash at the stored cash rate (backtesting/regime.py, "
         "index_sma). Measured in-sample on v1.4 (2013-2021): India 25.31% -> 24.13% CAGR, max drawdown "
         "-50.5% -> -37.1%; the breadth variant lost return and saved no drawdown, so it was not adopted. "
         "The US stays off -- it gained 0.7 points there but still trails IWM, and adopting it would tune "
         "a book with no edge. `--regime off` runs the control. The live holdings view applies the same "
         "switch, so it shows cash while the filter is off."),
        ("1.4", "2026-10-26",
         "Signals read total return: the momentum ranking, volatility weights and the 200-day trend test "
         "now use closes back-adjusted for the special dividends and demergers a holder is credited "
         "(corporate_actions.back_adjust). On traded prices a demerged parent read as a crash for a year "
         "-- out of the ranking, failing the trend test, and given a huge volatility. Fills, valuation, "
         "the price floor and turnover still read traded prices. Ratios only, so no action after the "
         "signal date can leak into it."),
        ("1.3", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited (marketdata/corporate_actions.py). On the ex-date a held position receives the cash, where the stored close only falls by it -- AURUM's 98% special dividend on 2020-12-23 was booked as a -98% loss, about 10% of the India vol-scaled book. Ordinary dividends stay out of strategy and benchmark. Stored prices were also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py correct)."),
        ("1.2", "2026-10-24",
         "A rank buffer, OFF until measured (hold_rank = None). Each month the book was rebuilt from "
         "the fresh top 20, so a name slipping from rank 20 to 21 was sold outright. The ranking is "
         "12-1 momentum, which barely moves in a month, yet the stored runs held a median 33 days and "
         "turned the book over 4.6-5.2x a year -- rank noise rather than signal decided most trades, "
         "and the caveats already say costs decide this strategy (+6.05 excess at 25bps, +3.66 at 50, "
         "gone at 100). With hold_rank set, a held name stays while it ranks within hold_rank and is "
         "still eligible; free slots go to the best names not held. The live holdings view replays "
         "recent month-ends with the same rule, so it cannot drift from the backtest once the buffer "
         "is on. At the default nothing changes: run() reproduces its prior output exactly."),
        ("1.1", "2026-10-17",
         "ETFs and liquid funds are out of the candidate universe (universe.non_stock_symbols). They "
         "were never meant to be in it, and a volatility-weighted book is actively broken by them: a "
         "money-market ETF has almost no volatility, so it scores near-infinite on both a vol-scaled "
         "rank and an inverse-vol weight. The final book was 98.8% three liquid-rate ETFs. Removing "
         "them IMPROVED the result -- CAGR 16.40% -> 17.56%, excess 4.41 -> 5.57, Sharpe 0.84 -> 0.87, "
         "drawdown unchanged -- because they were absorbing capital that belonged in equities. "
         "Historical P&L was barely touched (funds were 1% of it and absent before 2021); what changed "
         "is the recent book, and whether this is deployable at all."),
        ("1.0", "2026-10-17",
         "First version. Chosen from an 18-variant sweep on the worst half-period excess over the Nifty "
         "Smallcap 250, not on full-window CAGR: a variant that only clears the control after 2019 is a "
         "regime bet. vol_scaled/top-20/inverse-vol was the only one that held in both halves."),
    )
    name = VS_DOC["name"]
    description = VS_DOC["description"]
    status = VS_DOC["status"]
    thesis = VS_DOC["thesis"]
    how_it_works = tuple(VS_DOC["how_it_works"])
    caveats = tuple(VS_DOC["caveats"])

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "trend"

    # tunables -- these ARE the strategy
    rank = "vol_scaled"
    top_n = 20
    weighting = "inverse_vol"
    lookback = TRADING_DAYS
    skip = 21
    vol_window = 63
    rebalance = "ME"
    cost_bps = 50.0
    vol_target = None
    #: Rank buffer: hold a name until it ranks outside this (see buffered_target). None = off, the
    #: plain top-`top_n` rule, until a run says what width earns its place.
    hold_rank = None
    liquidity_top = 0            # the turnover floor is the control, not a rank cutoff
    #: Judge it against the SEGMENT it trades, not the broad index. A turnover-floored momentum
    #: book is a small-cap book: the Smallcap 250 returned 11.99% against the Nifty 500's 10.17%
    #: from 2010, so ~1.8 points of any excess over the broad index is beta, not skill. The
    #: segment index also drops and replaces constituents, so it carries the failures this
    #: survivor-only universe cannot. US: IWM (Russell 2000) for the same reason -- against SPY the
    #: US run reads -8.58, against IWM -3.92, and the difference is 2010-2026 mega-cap concentration
    #: rather than anything this strategy did. The remaining -3.9 is a real loss and stays visible.
    benchmark_key = {"india": "NIFTYSMALLCAP250", "us": "IWM"}
    #: The window every measured figure in `status` comes from. Declared because the backtest job
    #: otherwise uses its own default (2013) while the documented command says 2010 -- the button
    #: and the page would then produce different runs and disagree about the same strategy.
    min_turnover_cr = 10         # Rs crore/day (India); see min_turnover_for()
    min_turnover_usd_m = 20      # $ million/day (US)
    #: Market-regime switch per market (backtesting/regime.py), None = off -- now off everywhere (v1.7).
    #: India ran one from v1.5 and it failed its pre-registered verify run on 2022 onward: against the same
    #: version without it, 14.52% CAGR vs 22.21% and a DEEPER drawdown, -38.5% vs -32.1%. The switch stays
    #: available as `--regime index_sma` for research; re-adopting it is a new version with its own verify.
    regime_by_market: dict = {}
    #: The index that switch reads, per market (a broad_index_symbols key). India watches the SEGMENT the
    #: book holds, the Smallcap 250, not the broad Nifty 500: in 2018 small caps fell 26.8% while the
    #: Nifty 500 fell 3.4% and stayed above its 200-day, so the broad-index switch kept the book invested
    #: through a 28.1% loss (v1.6). Kept for `--regime index_sma` runs; it does nothing while the switch is off.
    regime_index_by_market = {"india": "NIFTYSMALLCAP250"}
    #: The switch's average length, mirrored from regime.INDEX_SMA_DAYS so the page renders the live
    #: value and the fingerprint moves if it ever changes.
    regime_sma_days = _regime.INDEX_SMA_DAYS

    @classmethod
    def min_turnover_for(cls, market: str) -> float:
        """The floor in the market's own currency: one number cannot serve both."""
        return (cls.min_turnover_cr * 1e7 if MARKETS[market].currency_code == "INR"
                else cls.min_turnover_usd_m * 1e6)

    @classmethod
    def regime_for(cls, market: str) -> str | None:
        """The market-regime switch this strategy runs with in `market` (None = no switch)."""
        return cls.regime_by_market.get(market)

    @classmethod
    def regime_index_for(cls, market: str) -> str | None:
        """The ticker that switch reads in `market`; None = the market's broad benchmark."""
        key = cls.regime_index_by_market.get(market)
        return MARKETS[market].broad_index_symbols.get(key) if key else None

    param_docs = (
        ("Ranking", "rank", "vol_scaled: 12-1 return divided by realised volatility."),
        ("Holdings", "top_n", "Names held at a time; 20 beat 50 on excess, 50 on drawdown."),
        ("Weighting", "weighting", "inverse_vol: capital inverse to each name's volatility."),
        ("Momentum lookback", "lookback", "Bars of return used to rank (12 months)."),
        ("Skip", "skip", "Most recent bars excluded -- the 12-1 convention that avoids short-term reversal."),
        ("Volatility window", "vol_window", "Bars of realised volatility used to weight positions. The ranking "
         "scales by volatility over the lookback instead."),
        ("Rebalance", "rebalance", "Pandas offset alias; ME is month-end."),
        ("Rank buffer", "hold_rank", "Hold a name until it ranks outside this; off (None) = sell whatever "
         "leaves the top {top_n}."),
        ("Cost per side", "cost_bps", "Basis points per side. The result is sensitive to this -- see the caveats."),
        ("Turnover floor, India", "min_turnover_cr", "Rs crore of 20-day average traded value a day."),
        ("Turnover floor, US", "min_turnover_usd_m", "$ million of 20-day average traded value a day."),
        ("Market filter average (India)", "regime_sma_days", "Days in the benchmark's moving average; at a "
         "month-end close at or below it the India book holds cash. The US runs without the filter."),
    )


class MomentumBaselineStrategy(PortfolioStrategy):
    """Cross-sectional momentum, in the registry so it gets a version.

    It was the only approach here that beats its index and the only one with
    no version, no fingerprint and no generated spec -- the strategy most
    worth refining was the one whose changes nothing recorded.

    It is a PortfolioStrategy, not a Strategy: it ranks the whole universe on
    each rebalance date and holds the top N, so it has no per-symbol gate,
    entry trigger or stop to express.
    """

    key = "momentum_baseline"
    doc = DOC
    family = "momentum_baseline"
    version = "1.2"
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "trend"

    # tunables — these ARE the strategy
    top_n = 10
    lookback = TRADING_DAYS
    skip = 21
    cost_bps = 5.0
    liquidity_top = 1000

    param_docs = (
        ("Holdings", "top_n", "How many names are held at a time."),
        ("Momentum lookback", "lookback", "Bars of return used to rank (12 months)."),
        ("Skip", "skip", "Most recent bars excluded, the 12-1 convention that avoids short-term reversal."),
        ("Cost per side", "cost_bps", "Basis points charged on every trade, both sides."),
        ("Liquidity cutoff", "liquidity_top", "Only the N most liquid names are ranked."),
    )

    changelog = (
        ("1.2", "2026-10-26",
         "Signals read total return: the momentum ranking, volatility weights and the 200-day trend test "
         "now use closes back-adjusted for the special dividends and demergers a holder is credited "
         "(corporate_actions.back_adjust). On traded prices a demerged parent read as a crash for a year "
         "-- out of the ranking, failing the trend test, and given a huge volatility. Fills, valuation, "
         "the price floor and turnover still read traded prices. Ratios only, so no action after the "
         "signal date can leak into it."),
        ("1.1", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited (marketdata/corporate_actions.py). On the ex-date a held position receives the cash, where the stored close only falls by it -- AURUM's 98% special dividend on 2020-12-23 was booked as a -98% loss, about 10% of the India vol-scaled book. Ordinary dividends stay out of strategy and benchmark. Stored prices were also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py correct)."),
        ("1.0", "2026-10-09",
         "Brought into the registry so it carries a version and a generated "
         "spec. Defaults unchanged: top 10, 12-1 momentum, monthly rebalance, "
         "5bps a side, 200-day trend filter on."),
    )
