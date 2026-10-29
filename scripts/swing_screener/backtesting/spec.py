"""The portfolio-level parts of the Minervini backtest specification (research/minervini-backtest-spec.md).

A one-symbol evaluation cannot know a stock's rank among all stocks, the state of the market, or how
many bases a stock has already broken out of. These run over the collected signal list before the
simulator, each using only data up to the signal's own date:

  * `rs_ratings` / `filter_min_rs` — TT-08: the RS rating, 1–99 across the tradable universe on the
    signal date, RS_raw = 0.4 × 63-day + 0.2 × 126-, 189- and 252-day return (section 3);
  * `market_filter` — no new buys in a risk-off market: MKT-01 (the benchmark above its 200-day and
    its 50-day above its 200-day) or, for minervini 1.8+, the SEPA guide's 50-day-and-breadth test;
  * `results_blackout` — no new buys with results due within a set number of days;
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
from ..core import indicators as ind
from ..marketdata import asof, cache, db

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

def split_factor_after(market: str, index: pd.DatetimeIndex, symbols) -> pd.DataFrame:
    """Per date and symbol, the product of every stored split dated AFTER it: multiply a back-adjusted
    close by this and it is the price the stock traded at that day.

    Yahoo's split rows only, because Yahoo's are the adjustments the stored prices carry (NSE's feed
    splits one event into a bonus and a face-value split, which would count it twice). Every stored
    split is read, including any after a backtest stage's end -- a deliberate exception to
    `asof.end()`: the stored prices are already adjusted for all of them, so leaving one out would put
    the early bars on the wrong scale. What comes out is the price that was public on that day, so
    nothing after it leaks into the rating.

    Only the symbols with a split after the index's first date are returned; the others' factor is 1."""
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, ex_date, value FROM corporate_actions
                       WHERE market=%s AND kind='split' AND source='yahoo' AND value > 0
                         AND ex_date > %s AND symbol = ANY(%s)""",
                    (market, index[0].date(), list(symbols)))
        rows = cur.fetchall()
    out = pd.DataFrame(1.0, index=index, columns=sorted({r[0] for r in rows}))
    for sym, ex, v in rows:
        out.loc[out.index < pd.Timestamp(ex), sym] *= float(v)
    return out


def traded_close(market: str, close: pd.DataFrame) -> pd.DataFrame:
    """`close` (dates x symbols, back-adjusted) as the price each stock traded at on each date -- what
    a price floor must read in a backtest (split_factor_after). Fills, valuation and returns keep the
    adjusted close: this frame jumps at every split."""
    out = close.astype(float)
    if close.empty:
        return out
    k = split_factor_after(market, close.index, close.columns)
    out[k.columns] = out[k.columns] * k
    return out


def rs_ratings(market: str, dates: list, young_min_bars: int = 0) -> dict:
    """{date: Series(symbol -> RS 1..99)} across the tradable universe on each date.

    `young_min_bars` > 0 also rates a listing younger than MIN_HISTORY once it has traded that many
    sessions: its return since listing, ranked against the rated universe's return over the same
    number of sessions. The rated stocks' own ratings are unchanged -- a young listing is placed
    against them, never ranked among them -- and the default leaves young listings unrated, so a
    strategy that does not ask sees exactly what it saw before."""
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
    # The price floor reads the price the stock TRADED at on each date. Stored closes are back-adjusted
    # for every later split, so NFLX's October 2009 close is stored as $0.72 against the ~$50 it traded
    # at, and a $10 floor on it left exactly the later multi-baggers unrated -- NFLX until 2013, NVDA
    # until 2020 -- and filter_min_rs then dropped their signals. The value floor needed no such fix:
    # traded value is split-invariant (see strategies/base.tradable_point_in_time).
    traded = close.copy()
    k = split_factor_after(market, close.index, close.columns)
    traded[k.columns] = close[k.columns] * k
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
        px = traded.iloc[i]

        # one definition of the score, in core.indicators; this ranks it across the market
        raw_rs = ind.rs_score(close).iloc[i]
        age_ok = (first_s <= d_use - pd.Timedelta(days=int(MIN_HISTORY * 1.4))) | (have.iloc[i] >= MIN_HISTORY)
        ok = (px >= MIN_PRICE[market]) & (v50.iloc[i] >= MIN_VALUE_50D[market]) & age_ok & raw_rs.notna()
        v = raw_rs[ok]
        if len(v) < 20:
            continue
        pct = v.rank(pct=True)
        out[d] = (1 + 98 * (pct - 1 / len(v)) / (1 - 1 / len(v))).round()
        if young_min_bars:
            h = have.iloc[i]
            young = ((px >= MIN_PRICE[market]) & (v50.iloc[i] >= MIN_VALUE_50D[market]) & ~age_ok
                     & (h >= young_min_bars) & c.notna())
            extra = {}
            for sym in young[young].index:
                k = int(h[sym]) - 1                      # sessions since its first stored close
                if k < 1 or i - k < 0:
                    continue
                first = close[sym].iloc[i - k]
                if not first == first or first <= 0:
                    continue
                r_sym = c[sym] / first - 1
                peers = (c[v.index] / close[v.index].iloc[i - k] - 1).dropna()
                if len(peers) < 20:
                    continue
                share = float((peers <= r_sym).mean())
                extra[sym] = round(1 + 98 * share)
            if extra:
                out[d] = pd.concat([out[d], pd.Series(extra, dtype=float)])
    logger.info("RS ratings: %d dates rated", len(out))
    return out


def filter_min_rs(signals: list, market: str, min_rs: int, young_min_bars: int = 0) -> tuple[list, dict]:
    """TT-08: keep signals whose stock was rated `min_rs`+ on the signal date; the rating goes in meta["rs"].
    A stock outside the rated universe that day (too cheap, too thin, too new) is dropped."""
    ratings = rs_ratings(market, [s.date for s in signals], young_min_bars)
    kept, low, unrated = [], 0, 0
    gone = {"below": [], "unrated": []}
    for s in signals:
        r = ratings.get(pd.Timestamp(s.date))
        rs = None if r is None else r.get(s.symbol)
        if rs is None or rs != rs:
            unrated += 1
            gone["unrated"].append(s)
            continue
        if rs < min_rs:
            low += 1
            gone["below"].append(s)
            continue
        kept.append(replace(s, meta={**s.meta, "rs": int(rs)}))
    logger.info("RS filter (>= %d): kept %d, below %d, outside the rated universe %d", min_rs, len(kept), low, unrated)
    return kept, {"min_rs": min_rs, "kept": len(kept), "below": low, "unrated": unrated, "dropped_signals": gone}


_RANK_ASOF: dict = {}


def rs_rank_asof(market: str, date, young_min_bars: int = 0) -> tuple[dict, bool]:
    """{symbol: RS 1-99} on one date, and whether the market could be rated at all.

    The LIVE counterpart of `filter_min_rs`, and deliberately the same `rs_ratings` it gates on:
    a stock shown live has then cleared the rating a backtested trade had to clear. Screening a
    whole market is the only place this is answerable -- a rank is cross-sectional, so a
    one-symbol evaluation has to fall back to the per-stock stand-in (screens/criteria.stage2_rs).

    `ranked` False means no rating exists for that date -- too little stored history, or fewer
    than the 20 rated names `rs_ratings` insists on. Callers must fall back rather than fail
    every stock, which is why this is a flag and not an empty dict.

    Cached per (market, date): a screening run asks once per symbol, and the query behind it
    reads the whole market's last 420 sessions.
    """
    d = pd.Timestamp(date).normalize()
    key = (market, d.isoformat(), young_min_bars)
    if key not in _RANK_ASOF:
        try:
            ser = rs_ratings(market, [d], young_min_bars).get(d)
        except Exception:                      # noqa: BLE001 -- never fail a screen over the rank
            logger.exception("RS ratings unavailable for %s on %s; falling back to the stand-in",
                             market, d.date())
            ser = None
        ranked = ser is not None and len(ser) > 0
        _RANK_ASOF[key] = ({str(k): float(v) for k, v in ser.items() if v == v} if ranked else {}, ranked)
    return _RANK_ASOF[key]


def top_dollar_volume(market: str, dates: list, n: int) -> dict:
    """{date: set of the `n` most-traded symbols by 50-day average traded value that day}.

    A RANK, not a floor. `--min-dollar-volume` asks for an absolute number of dollars,
    which means something different in 2010 than in 2026; this asks to be among the n
    most-traded names at the time, which is what "a large-cap index member" actually
    stands for and is computable point in time from prices alone. Real index membership
    cannot be: nothing here stores constituents, and today's membership is an OUTCOME of
    having grown, so applying it backwards would be lookahead of the worst kind.
    """
    dates = sorted({pd.Timestamp(d) for d in dates})
    if not dates or not n:
        return {}
    since = dates[0] - pd.Timedelta(days=150)      # enough history for a 50-session mean
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, close, volume FROM prices
                       WHERE market=%s AND date >= %s AND date <= %s AND close > 0 AND symbol NOT LIKE '^%%'""",
                    (market, since.date(), dates[-1].date()))
        raw = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "close", "volume"])
    if raw.empty:
        return {}
    raw["date"] = pd.to_datetime(raw["date"])
    value = (raw.pivot(index="date", columns="symbol", values="close").astype(float)
             * raw.pivot(index="date", columns="symbol", values="volume").astype(float)).sort_index()
    del raw
    v50 = value.rolling(50, min_periods=40).mean()
    out = {}
    for d in dates:
        row = v50[v50.index <= d]
        if row.empty:
            continue
        top = row.iloc[-1].dropna().nlargest(n)
        out[d] = set(top.index)
    return out


def filter_top_dollar_volume(signals: list, market: str, n: int) -> tuple[list, dict]:
    """Keep signals whose stock was among the `n` most-traded on the signal date."""
    ranks = top_dollar_volume(market, [s.date for s in signals], n)
    kept, outside, unknown = [], 0, 0
    gone = {"outside": []}
    for s in signals:
        top = ranks.get(pd.Timestamp(s.date))
        if top is None:
            unknown += 1
            kept.append(s)          # no ranking that day: do not silently drop the signal
            continue
        if s.symbol in top:
            kept.append(s)
        else:
            outside += 1
            gone["outside"].append(s)
    logger.info("Top-%d traded filter: kept %d, outside %d, unranked %d", n, len(kept), outside, unknown)
    return kept, {"n": n, "kept": len(kept), "outside": outside, "unranked": unknown, "dropped_signals": gone}


def filter_max_base_no(signals: list, max_base: int) -> tuple[list, dict]:
    """Keep only signals from the first `max_base` bases of a stock's advance.

    Minervini treats later bases as riskier -- by a third or fourth base the move
    is well advanced and the supply that the earlier bases absorbed has been
    replaced by holders sitting on gains. The spec records a base number for this
    reason and says in as many words to test a filter allowing only bases 1 to 3;
    until now the number was computed for the report and never acted on.

    Signals with no base number (the strategy did not supply a base_id) are KEPT,
    not dropped: an unknown base number is not evidence of a late base, and
    silently discarding them would make the filter look more selective than it is.
    """
    kept, late, unknown = [], 0, 0
    gone = {"late": []}
    for s in signals:
        bn = s.meta.get("base_no")
        if bn is None:
            unknown += 1
            kept.append(s)
            continue
        if int(bn) > max_base:
            late += 1
            gone["late"].append(s)
            continue
        kept.append(s)
    logger.info("Base-number filter (<= %d): kept %d, dropped %d as late-stage, %d without a base number",
                max_base, len(kept), late, unknown)
    return kept, {"max_base": max_base, "kept": len(kept), "late": late, "unknown": unknown, "dropped_signals": gone}


# ---------------------------------------------------------------- market filter (MKT-01)

MKT_CONFIRM_DAYS = 5     # sessions MKT-01 must hold before risk-on resumes [assumption; test 1-10]


def breadth_pct50(market: str) -> pd.Series:
    """Per date: the share (%) of the market's most-traded stocks closing above their own 50-day
    average (`breadth_daily`, built from stored prices by analytics/breadth.py)."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, n, above50 FROM breadth_daily WHERE market=%s AND n > 0 ORDER BY date", (market,))
        rows = cur.fetchall()
    if not rows:
        return pd.Series(dtype=float)
    out = pd.Series([100.0 * a / n for _, n, a in rows], index=pd.DatetimeIndex([d for d, _, _ in rows]))
    return out[out.index <= asof.end()] if asof.end() is not None else out


def highs_lows(market: str) -> pd.DataFrame:
    """Per date: new 52-week highs and lows among the market's most-traded stocks (`breadth_daily`,
    analytics/breadth.py), columns `highs` and `lows`. Empty when nothing is stored."""
    with db.get_connection().cursor() as cur:
        cur.execute("SELECT date, highs, lows FROM breadth_daily WHERE market=%s AND n > 0 "
                    "AND highs IS NOT NULL AND lows IS NOT NULL ORDER BY date", (market,))
        rows = cur.fetchall()
    out = pd.DataFrame([(h, lo) for _, h, lo in rows], columns=["highs", "lows"],
                       index=pd.DatetimeIndex([d for d, _, _ in rows]), dtype=float)
    return out[out.index <= asof.end()] if asof.end() is not None else out


def market_ok(market: str, confirm_days: int = 0, guide: bool = False) -> pd.Series:
    """Per date: may new buys be taken?

    MKT-01 (`guide=False`): benchmark close > its SMA200 and SMA50 > SMA200.
    The SEPA guide's test (`guide=True`, minervini_spec.MKT_GUIDE): the benchmark closes above its
    MKT_INDEX_SMA-day average AND that average is higher than MKT_SMA_RISING_DAYS sessions ago,
    AND breadth — the share of stocks above their 50-day — is above
    MKT_BREADTH_MIN_PCT or higher than MKT_BREADTH_RISING_DAYS sessions earlier, AND, when
    MKT_HIGHS_LOWS_DAYS is set, new 52-week highs outnumber MKT_HIGHS_LOWS_RATIO x new lows over
    that many sessions. A date with no breadth stored (before its history starts) is judged on the
    benchmark alone.

    With `confirm_days`, risk-on resumes only after the test has held that many sessions
    in a row. Risk-OFF still bites immediately — the delay is there so a benchmark
    oscillating around its average does not turn the gate on and off every other day,
    not to keep buying into a market that has just rolled over.
    """
    b = cache.load_cached(market, MARKETS[market].benchmark_ticker)
    c = b["close"].astype(float)
    if guide:
        from ..strategies import minervini_spec as ms
        sma = c.rolling(ms.MKT_INDEX_SMA).mean()
        # v2: above the average AND the average itself rising over MKT_SMA_RISING_DAYS. The slope
        # term is what separates "above a falling average on a bounce" from a market that is
        # actually turning up, and a bounce is where breakout entries fail worst.
        ok = c > sma
        if ms.MKT_SMA_RISING_DAYS:          # 0 turns the slope term off, as a sweepable parameter
            ok = ok & (sma > sma.shift(ms.MKT_SMA_RISING_DAYS))
        br = breadth_pct50(market)
        if len(br):
            breadth_ok = (br > ms.MKT_BREADTH_MIN_PCT) | (br > br.shift(ms.MKT_BREADTH_RISING_DAYS))
            known = breadth_ok.reindex(c.index)          # NaN where breadth has no row that day
            ok = ok & known.fillna(True).astype(bool)
        if ms.MKT_HIGHS_LOWS_DAYS:
            # Leadership (1.32): over the last MKT_HIGHS_LOWS_DAYS sessions, more stocks made new
            # 52-week highs than MKT_HIGHS_LOWS_RATIO x those making new lows.
            hl = highs_lows(market)
            if len(hl):
                w = int(ms.MKT_HIGHS_LOWS_DAYS)
                lead = hl["highs"].rolling(w).sum() > ms.MKT_HIGHS_LOWS_RATIO * hl["lows"].rolling(w).sum()
                lead = lead.where(hl["highs"].rolling(w).count() == w)       # NaN until a full window
                ok = ok & lead.reindex(c.index).fillna(True).astype(bool)
    else:
        s50, s200 = c.rolling(50).mean(), c.rolling(200).mean()
        ok = (c > s200) & (s50 > s200)
    if confirm_days and confirm_days > 1:
        ok = ok & (ok.rolling(int(confirm_days)).sum() >= int(confirm_days))
    return ok


def results_blackout(signals: list, market: str, days: int) -> tuple[list, dict]:
    """Drop a signal whose company files results within `days` calendar days AFTER the signal date.

    Results dates are the filing dates stored in `quarterly_results` (NSE results for India, from
    late 2020; SEC filings for the US, from 2009). A company with no stored filing near the signal
    is kept: no date, no blackout. Earnings dates are published weeks ahead, so knowing the next
    one on the signal date is not look-ahead.

    The filing is NOT the announcement, and the announcement is what gaps the stock. US filings
    land a mean 35 days after a Q1-Q3 period end but 53 after Q4, while announcements land ~30-37
    days out every quarter. So the rule leaks: on the stored US run it blocked 422 signals and
    still let 56 trades be bought into a report, AKAM on 2013-01-28 among them -- filed
    2013-03-01, announced 2013-02-06, gapped 18.7% through its stop the next morning.

    Keying on an INFERRED announcement date instead was tried and rejected, so it is not worth
    trying again without new data. No announcement calendar is stored before 2025-10
    (`stock_events`), so the date has to be reconstructed from the heaviest-volume bar of each
    quarter, and that detector is too blunt: over 220 US symbols its implied reporting lag has an
    IQR of 27-65 days, and predicting the next announcement from a company's own prior quarters
    carries a median absolute error of 13 days -- against a 14-day window. Scored over the US
    book, it blocked 75 trades to catch 16 of 44 leaks, i.e. ~4 innocent trades per leak caught
    while still missing two thirds. Shifting the filing date earlier by its mean lateness fares
    no better (60 blocked for 11 of 43; 112 for 15 of 43).

    The fix is data, not arithmetic: real announcement dates are being stored from 2025-10, so
    runs over later periods can use them. Until then the leak stands, and D2-sensitive trades
    should be read with it in mind."""
    syms = sorted({s.symbol for s in signals})
    if not syms or not days:
        return signals, {"days": days, "blocked": 0, "kept": len(signals), "dropped_signals": {"blocked": []}}
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT DISTINCT symbol, filed FROM quarterly_results
                       WHERE market=%s AND symbol = ANY(%s) AND filed IS NOT NULL ORDER BY symbol, filed""",
                    (market, syms))
        rows = cur.fetchall()
    filed: dict[str, list] = {}
    for sym, f in rows:
        filed.setdefault(sym, []).append(pd.Timestamp(f))
    kept, blocked = [], 0
    gone = {"blocked": []}
    for s in signals:
        d = pd.Timestamp(s.date)
        nxt = next((f for f in filed.get(s.symbol, []) if f > d), None)
        if nxt is not None and (nxt - d).days <= days:
            blocked += 1
            gone["blocked"].append(s)
        else:
            kept.append(s)
    logger.info("Results blackout (%d days): kept %d of %d signals", days, len(kept), len(signals))
    return kept, {"days": days, "blocked": blocked, "kept": len(kept),
                  "covered_symbols": len(filed), "of_symbols": len(syms), "dropped_signals": gone}


def market_filter(signals: list, market: str, confirm_days: int = 0, guide: bool = False) -> tuple[list, dict]:
    ok = market_ok(market, confirm_days, guide)
    kept, gone = [], {"blocked": []}
    for s in signals:
        (kept if bool(ok.asof(pd.Timestamp(s.date))) else gone["blocked"]).append(s)
    logger.info("Market filter: kept %d of %d signals", len(kept), len(signals))
    return kept, {"kept": len(kept), "blocked": len(signals) - len(kept), "confirm_days": int(confirm_days or 0),
                  "dropped_signals": gone,
                  "days_open_pct": round(float(ok[ok.index >= min(s.date for s in signals)].mean()) * 100, 1) if signals else None}


# ---------------------------------------------------------------- category (segment) filter

# The "be in sync with your universe" rule: a stock is gated by the index of its own market-cap segment,
# not one broad benchmark. Segments by 50-day traded-value RANK on the signal date (point in time;
# market cap is only stored as of today), each (rank ceiling or None for the rest, index symbol, label).
SEGMENT_INDEX = {
    "india": ((100, "^NSEI", "Nifty 50"), (250, "NSE:NIFTY_MIDCAP_150", "Nifty Midcap 150"),
              (None, "NIFTYSMLCAP250.NS", "Nifty Smallcap 250")),
    "us": ((500, "SPY", "S&P 500 (SPY)"), (900, "MDY", "S&P MidCap 400 (MDY)"), (None, "IWM", "Russell 2000 (IWM)")),
}


def traded_value_ranks(market: str, dates: list) -> dict:
    """{date: Series symbol -> rank (1 = most traded) by 50-day average traded value}, stocks only (the
    index and ETF symbols stored beside them are left out)."""
    from ..marketdata import universe
    dates = sorted({pd.Timestamp(d) for d in dates})
    if not dates:
        return {}
    skip = set(universe.index_symbols(market))
    since = dates[0] - pd.Timedelta(days=150)
    with db.get_connection().cursor() as cur:
        cur.execute("""SELECT symbol, date, close, volume FROM prices
                       WHERE market=%s AND date >= %s AND date <= %s AND close > 0 AND symbol NOT LIKE '^%%'""",
                    (market, since.date(), dates[-1].date()))
        raw = pd.DataFrame(cur.fetchall(), columns=["symbol", "date", "close", "volume"])
    raw = raw[~raw["symbol"].isin(skip)]
    if raw.empty:
        return {}
    raw["date"] = pd.to_datetime(raw["date"])
    value = (raw.pivot(index="date", columns="symbol", values="close").astype(float)
             * raw.pivot(index="date", columns="symbol", values="volume").astype(float)).sort_index()
    v50 = value.rolling(50, min_periods=40).mean()
    out = {}
    for d in dates:
        row = v50[v50.index <= d]
        if not row.empty:
            out[d] = row.iloc[-1].dropna().rank(ascending=False, method="first")
    return out


def segment_ok(market: str, days: int) -> dict:
    """{index symbol: Series date -> close above its `days`-session simple average}."""
    out = {}
    for _cap, sym, _label in SEGMENT_INDEX[market]:
        b = cache.load_cached(market, sym)
        if b is None or b.empty:
            continue
        c = b["close"].astype(float)
        out[sym] = c > c.rolling(days).mean()
    return out


def segment_filter(signals: list, market: str, days: int) -> tuple[list, dict]:
    """Drop a signal whose stock's segment index (SEGMENT_INDEX, by traded-value rank that day) closed at or
    below its `days`-session average on the signal date. A stock with no rank that day is kept."""
    if market not in SEGMENT_INDEX or not signals:
        return signals, {"days": days, "blocked": 0, "kept": len(signals), "unranked": 0, "by_segment": {},
                         "dropped_signals": {"blocked": []}}
    ranks = traded_value_ranks(market, [s.date for s in signals])
    ok = segment_ok(market, days)
    kept, gone, unranked, by = [], {"blocked": []}, 0, {}
    for s in signals:
        r = ranks.get(pd.Timestamp(s.date), pd.Series(dtype=float)).get(s.symbol)
        if r is None or r != r:
            unranked += 1
            kept.append(s)
            continue
        seg = next(x for x in SEGMENT_INDEX[market] if x[0] is None or r <= x[0])
        series = ok.get(seg[1])
        good = bool(series.asof(pd.Timestamp(s.date))) if series is not None and len(series) else True
        st = by.setdefault(seg[2], {"kept": 0, "blocked": 0})
        if good:
            kept.append(s); st["kept"] += 1
        else:
            gone["blocked"].append(s); st["blocked"] += 1
    logger.info("Segment filter (%d-day): kept %d of %d", days, len(kept), len(signals))
    return kept, {"days": days, "blocked": len(gone["blocked"]), "kept": len(kept), "unranked": unranked,
                  "by_segment": by, "dropped_signals": gone}


def tf_align_filter(signals: list, prices: dict) -> tuple[list, dict]:
    """Keep a signal only if its stock's trend was aligned on the daily, weekly and monthly charts on the
    signal date (screens/criteria.py trend_alignment — the snapshot field Trend aligned (D/W/M))."""
    from ..screens import criteria as crit
    cache_: dict = {}
    kept, gone = [], {"misaligned": []}
    for s in signals:
        df = prices.get(s.symbol)
        if df is None or df.empty:
            kept.append(s)
            continue
        if s.symbol not in cache_:
            cache_[s.symbol] = crit.trend_alignment(df["close"])["aligned"]
        a = cache_[s.symbol]
        (kept if bool(a.asof(pd.Timestamp(s.date))) else gone["misaligned"]).append(s)
    logger.info("Timeframe alignment: kept %d of %d", len(kept), len(signals))
    return kept, {"kept": len(kept), "misaligned": len(gone["misaligned"]), "dropped_signals": gone}


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
    """{symbol: [(date, base_id)]}: every bar on which a base produced ANY entry setup, from the
    strategy's cached evaluations — whether or not a run trades it.

    The spec says to record a base number "for every completed base" and then, in the next
    sentence, to increase it "each time a base produces an MV-01 signal". Those agreed when MV-01
    was the only entry. It no longer is, and MV-01 is now the rarest event in the system -- 27
    bars in the whole India universe -- so counting only MV-01 made the number almost always 1:
    209 of 210 trades came back "base 1" and the --max-base filter dropped nothing at all. A base
    that resolves into a cheat is still a base the advance has used up, which is what Minervini is
    counting when he says later bases are riskier, so any setup advances the count."""
    with db.get_connection().cursor() as cur:
        # Scoped to the CURRENT spec_id. Without it the count mixes detections made
        # by different rule versions that happen to share the cache -- the same
        # failure the signal cache's own spec_id column was added to prevent.
        from ..strategies import get_strategy
        cur.execute("""SELECT symbol, date, extras->>'base_date' FROM backtest_signals
                       WHERE market=%s AND strategy=%s AND spec_id=%s
                         AND hard_gates_passed AND has_setup
                       ORDER BY symbol, date""",
                    (market, strategy_key, get_strategy(strategy_key).spec_id()))
        out: dict = {}
        for sym, d, bid in cur.fetchall():
            if bid:
                out.setdefault(sym, []).append((pd.Timestamp(d), bid))
    return out


def base_numbers(signals: list, prices: dict, market: str, strategy_key: str) -> list:
    """Base number per signal: 1 + the other bases of this stock that produced a setup (traded or
    not) before the signal and since the trend last broke (TT-01 … TT-04 failing BASE_RESET_DAYS
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
    if "sepa" in t and t["sepa"].notna().any():
        sections.insert(2, ("By SEPA fundamentals verdict (on the signal date)", "sepa"))
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
