"""Shorting Stage 4 stocks -- the first SHORT book on this shelf, judged as a hedge.

Every other strategy here is long-only, so in a bad year they all fall together. A short sleeve is
the one idea in the Learn module that should pay when everything else loses, so the question this
module answers is not "does it make money on its own" but "does adding it to the long momentum book
lower that book's drawdown, and at what cost in the years it does not pay". Every run answers it
against two controls that earn the cash rate -- an index-futures short at the strategy's own beta, and
a cash sleeve of the same weight -- beside the market's best long book (`LONG_BOOKS`), rebalanced
monthly (`hedge_tests`).

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
not dividend-adjusted, so a short would otherwise pocket every ex-dividend drop. The account's equity
earns the market's cash rate (the collateral's interest, CREDIT_INTEREST). Each run is repeated at
COST_LEVELS of those costs and all three are reported, so the sign of the result can be read against
its assumptions.
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
from ..core import swings as sw
from ..marketdata import cache, corporate_actions, index_data, industries, universe
from ..strategies.base import PortfolioStrategy
from ..strategies.stage_analysis import MA_WEEKS, SWING_WEEKS, _stage_machine, ma30, stage_series
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
#: C + P, Weinstein's own entry (1.5, the shipped one): C shorts the weekly close that breaks a Stage 3
#: top's low, P the first weekly pullback to that broken level that closes back below it. Both are read
#: off the stage machine's own onsets (`_stage_machine`), so the top is the one the Stage analysis
#: strategy and its chart draw, and both are decided on a week's last close.
ENTRY_WEINSTEIN = 1
ENTRY_FAILED_RALLY = 0        # B: a rally to the falling line that closes back below it (1.0-1.4's entry)
ENTRY_BREAKDOWN = 0           # A: a close at a new 52-week closing low on volume
PULLBACK_WEEKS = 8            # P: the pullback must come within this many weeks of the breakdown
#: C and P: the stock's industry group ranks at or below this on the stored point-in-time group RS
#: (1-99, `group_history`): a weak group, the half of Weinstein's selection 1.0-1.4 left out. A rank, not
#: the sector index's stage, because India's sector indices are stored only from 2022.
WEAK_GROUP_MAX_RANK = 30
#: C and P: the market index's own weekly stage (the same machine) must be this -- Weinstein's "the
#: market itself in Stage 4" -- in place of B's daily 200-day filter.
MARKET_STAGE = 4
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
#: 1 credits interest at the market's cash rate (index_data.cash_rate_series) on the account's equity each
#: session: the collateral a margin account holds earns it, and 1.0-1.4 left about 6.5% a year uncredited
#: in India. The comparators below earn the same rate, so the test is like for like.
CREDIT_INTEREST = 1
#: India's minimum stock-futures contract value (NSE, from 2015): a stand-in for the lot size, which is not
#: stored. Each run reports how many shorts reached one such lot at the account size.
INDIA_LOT_MIN_VALUE = 500_000

# ---- the hedge tests: the long book it is judged beside, the controls, and the weights tried
#: The best long book per market, not momentum_baseline: momentum_vol_scaled is India's strongest
#: optimise-stage stock book; quality_momentum is the US momentum stock book whose filings variant passed
#: its verify run. A market not listed falls back to momentum_baseline.
LONG_BOOKS = {"us": "quality_momentum", "india": "momentum_vol_scaled"}
LONG_BOOK = "momentum_baseline"
SLEEVE_WEIGHTS = (0, 20, 30)  # percent of the account in the short sleeve, rebalanced each month-end
CRASH_YEARS = (2015, 2016, 2018, 2020)
#: The first comparator, an index-futures short at the strategy's own beta, pays this per monthly roll.
INDEX_ROLL_BPS = 5.0
PASS_DD_POINTS = 2.0          # criterion 2: the sleeve's drawdown this much shallower than the cash sleeve's
PASS_SLEEVE_PCT = 20          # criterion 2 is judged at this sleeve weight


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


def default_entries() -> str:
    """The shipped entries, as the letters `--entries` takes."""
    return (("CP" if ENTRY_WEINSTEIN else "") + ("B" if ENTRY_FAILED_RALLY else "")
            + ("A" if ENTRY_BREAKDOWN else ""))


def _weekly_on_daily(df: pd.DataFrame, weekly_vals: pd.Series) -> pd.Series:
    """A weekly series placed on the LAST session of each week, NaN elsewhere -- the same mapping as
    `portfolio_sim.weekly_line`, so a week's stage is read only once its week is over. The final stored
    bar counts as a week's last only on a Friday."""
    out = pd.Series(np.nan, index=df.index)
    week = pd.Series(df.index.to_period("W-FRI"), index=df.index)
    last = week != week.shift(-1)
    last.iloc[-1] = df.index[-1].weekday() == 4
    ends = pd.PeriodIndex(week[last]).end_time.normalize()   # vectorised: a per-row map was most of the run
    out[last] = weekly_vals.reindex(ends).values
    return out


def weinstein_weeks(weekly: pd.DataFrame) -> pd.DataFrame:
    """Entries C and P per weekly bar, each decided at that week's close (point in time).

    C, the breakdown: the stage known at the previous week's close is 3 (a top), and this week closes below
    the top's low -- the lowest weekly low from the week the stage machine dates the top's onset to the
    previous week -- and below the 30-week line. That is the close that STARTS the machine's 3 -> 4 run; the
    machine confirms Stage 4 CONFIRM_WEEKS later, and Weinstein shorts the break, not the confirmation. Its
    stop sits above the top's last rally peak: the last weekly swing high known at that close.

    P, the first pullback: within PULLBACK_WEEKS of a C, the first week whose high comes within TOUCH_PCT of
    the broken level (or above it) and closes back below it and below the line. Its stop sits above the
    highest high since the breakdown. A week that closes back above the broken level ends the watch: the
    breakdown failed, and there is no pullback to short.
    """
    vals, onset, _ = _stage_machine(weekly)
    n = len(weekly)
    hi, lo = weekly["high"].astype(float).to_numpy(), weekly["low"].astype(float).to_numpy()
    cl, line = weekly["close"].astype(float).to_numpy(), ma30(weekly).to_numpy()
    is_hi = sw.swing_high_mask(weekly["high"].astype(float), SWING_WEEKS, SWING_WEEKS).to_numpy()
    swing_hi, last = np.full(n, np.nan), np.nan
    for j in range(n):
        if j >= SWING_WEEKS and is_hi[j - SWING_WEEKS]:   # a swing high is known SWING_WEEKS weeks later
            last = hi[j - SWING_WEEKS]
        swing_hi[j] = last
    sig_c, sig_p = np.zeros(n, bool), np.zeros(n, bool)
    sup_c, sup_p, peak_c, peak_p = (np.full(n, np.nan) for _ in range(4))
    broken = b_week = None
    for i in range(1, n):
        if vals[i - 1] == 3 and onset[i - 1] is not None and onset[i - 1] < i and line[i] == line[i]:
            top_low = float(lo[onset[i - 1]:i].min())
            if cl[i] < top_low and cl[i] < line[i]:
                sig_c[i], sup_c[i], peak_c[i] = True, top_low, swing_hi[i]
                broken, b_week = top_low, i
                continue
        if broken is None:
            continue
        if i - b_week > PULLBACK_WEEKS or cl[i] > broken:
            broken = None
        elif hi[i] >= broken * (1 - TOUCH_PCT / 100) and cl[i] < broken and cl[i] < line[i]:
            sig_p[i], sup_p[i], peak_p[i] = True, broken, float(hi[b_week + 1:i + 1].max())
            broken = None
    return pd.DataFrame({"sig_c": sig_c, "sig_p": sig_p, "support_c": sup_c, "support_p": sup_p,
                         "peak_c": peak_c, "peak_p": peak_p, "swing_hi": swing_hi}, index=weekly.index)


def symbol_frame(df: pd.DataFrame, bench_close: pd.Series, cr: pd.DataFrame | None = None) -> pd.DataFrame:
    """Everything the entries and exits read, per daily bar, causal.

    `stage` and `line` are the last COMPLETED week's (forward-filled from week-ends); `wk_line` is
    set only on a week's last session, where the stage exit reads it.

    `cr` (this symbol's credited special dividends and demergers): the stage, the lines, the ATR and
    the signals are computed on the series back-adjusted for them, so a demerger is not read as a
    Stage 4 breakdown, and every price level is then put back on its own bar's scale (`pit_scale`),
    so a stop never carries an action dated after it. Fills read the traded prices; turnover reads them too,
    with the sessions before a payout put on the bar's own price basis (`corporate_actions.traded_value`).
    """
    raw = df[["open", "high", "low", "close", "volume"]].astype(float)
    df = corporate_actions.back_adjust_ohlc(raw, cr)
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
    # traded prices, each session valued on this bar's basis after a payout (corporate_actions.traded_value)
    out["turnover"] = corporate_actions.traded_value(raw["close"], raw["volume"], cr, LIQ_BARS, stat="median")
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
    # entries C and P, Weinstein's: weekly, off the stage machine's own onsets
    wk = weinstein_weeks(weekly)
    for c in ("sig_c", "sig_p"):
        out[c] = _weekly_on_daily(df, wk[c].astype(float)).fillna(0).astype(bool)
    for c in ("support_c", "support_p"):
        out[c] = _weekly_on_daily(df, wk[c])
    out["stop_c"] = _weekly_on_daily(df, wk["peak_c"]) + STOP_ATR_BUFFER * out["atr"]
    out["stop_p"] = _weekly_on_daily(df, wk["peak_p"]) + STOP_ATR_BUFFER * out["atr"]
    # the last confirmed weekly swing high, known from its week's close: C and P's trailing stop
    out["swing_hi"] = _weekly_on_daily(df, wk["swing_hi"]).ffill()
    if cr is not None and len(cr):
        k = corporate_actions.pit_scale(raw["close"], df["close"])
        for c in ("wk_line", "line", "sma50", "atr", "stop_b", "stop_a", "stop_c", "stop_p",
                  "support_c", "support_p", "swing_hi"):
            out[c] = out[c] * k
        for c in ("open", "high", "low", "close"):
            out[c] = raw[c]
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
    cr = corporate_actions.credits(market)
    cr_by = {s: g for s, g in cr.groupby("symbol")} if len(cr) else {}
    for i in range(0, len(tickers), 400):
        for sym, d in cache.load_many_cached(market, tickers[i:i + 400]).items():
            if d is None or len(d) < MIN_BARS:
                continue
            try:
                f = symbol_frame(d, bench, cr_by.get(sym))
            except Exception as e:   # noqa: BLE001 -- one malformed history must not end the run
                logger.warning("%s: skipped (%s)", sym, e)
                continue
            if not (f["sig_a"].any() or f["sig_b"].any() or f["sig_c"].any() or f["sig_p"].any()):
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
            "weak": market_weak(bench), "mkt_stage": market_stage(braw), "n_universe": len(tickers),
            "group": group_ranks(market), "cash_rate": index_data.cash_rate_series(market, bench.index)[0],
            # a short PAYS a special dividend or a demerger's value on the ex-date (the flat yield
            # covers ordinary dividends only)
            "credits": corporate_actions.Credits.for_market(market, list(frames))}


def market_stage(bench_raw: pd.DataFrame) -> pd.Series:
    """The market index's weekly stage on each daily bar, as known at the last completed week's close."""
    b = bench_raw[["open", "high", "low", "close", "volume"]].astype(float)
    return _weekly_on_daily(b, stage_series(ind.resample_weekly(b)).astype(float)).ffill().fillna(0)


def group_ranks(market: str) -> dict:
    """{"by_date": {date: {industry: rank}}, "dates": sorted dates, "industry": {symbol: industry}}.

    The rank is the stored point-in-time industry-group RS (`analytics.group_history`, 1-99, high is
    strong). The symbol's industry is today's classification (`industries.load` keeps no history)."""
    from ..analytics import group_history
    g = group_history.load(market)
    by_date = {pd.Timestamp(d): v.get("industry", {}) for d, v in g.items()}
    return {"by_date": by_date, "dates": pd.DatetimeIndex(sorted(by_date)),
            "industry": {s: ind_ for s, (_sec, ind_, _cap) in industries.load(market).items()}}


def group_rank(prep: dict, sym: str, d) -> float:
    """The symbol's industry-group rank on the last stored date at or before `d`; NaN when unknown."""
    g = prep.get("group")
    if not g or not len(g["dates"]):
        return float("nan")
    k = int(g["dates"].searchsorted(pd.Timestamp(d), side="right")) - 1
    if k < 0:
        return float("nan")
    r = g["by_date"][g["dates"][k]].get(g["industry"].get(sym))
    return float(r) if r is not None else float("nan")


# The filters a signal passes, in the order they are applied; `screen_signal` names the first that refused.
# The chart's Trade setups layer (`Stage4ShortsStrategy.setups_live`) lists them in this order too.
FILTERS = ("liquidity", "fno", "rs", "stop", "market", "group")
REFUSED = {"liquidity": "too little traded", "fno": "no stock future (proxy)", "rs": "not weaker than the index",
           "stop": "stop too far above the close", "market": "the market is not weak",
           "group": "the industry group is not weak"}
#: Weinstein's entries (C, P) read his market and group conditions; the guide's (A, B) the daily filter.
WEINSTEIN_KINDS = ("C", "P")


def screen_signal(prep: dict, sym: str, f: pd.DataFrame, d, kind: str, use_filter: bool) -> tuple[dict | None, str]:
    """One signal through the filters: (its candidate, "") or (None, the FILTERS key that refused it)."""
    floor = MARKETS[prep["market"]].screener.min_dollar_volume or 0
    r = f.loc[d]
    if not (r["turnover"] >= floor):
        return None, "liquidity"
    if prep["fno_rank"] is not None:
        rk = prep["fno_rank"].at[d, sym] if d in prep["fno_rank"].index else float("nan")
        if not (rk <= FNO_PROXY_TOP):
            return None, "fno"
    if not (r["rs_excess"] < 0):
        return None, "rs"
    stop, close = float(r[f"stop_{kind.lower()}"]), float(r["close"])
    if not (stop > close and (stop / close - 1) * 100 <= MAX_STOP_PCT):
        return None, "stop"
    if kind in WEINSTEIN_KINDS:
        if use_filter and not float(prep["mkt_stage"].asof(d)) == MARKET_STAGE:
            return None, "market"
        if not (group_rank(prep, sym, d) <= WEAK_GROUP_MAX_RANK):
            return None, "group"
    elif use_filter and not bool(prep["weak"].asof(d)):
        return None, "market"
    return {"symbol": sym, "entry": kind, "stop": stop, "signal_close": close,
            "rs_excess": float(r["rs_excess"]), "atr": float(r["atr"])}, ""


def candidates(prep: dict, entries: str, use_filter: bool, start: pd.Timestamp) -> dict:
    """{signal date: [candidate, ...]}, weakest relative strength first."""
    out: dict = {}
    dropped = {k: 0 for k in FILTERS}
    for sym, f in prep["frames"].items():
        for kind in entries:
            hits = f.index[f[f"sig_{kind.lower()}"].values & (f.index >= start)]
            for d in hits:
                c, why = screen_signal(prep, sym, f, d, kind, use_filter)
                if c is None:
                    dropped[why] += 1
                    continue
                out.setdefault(d, []).append(c)
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
    # A signal dated on a session the benchmark did not trade (India's Saturday Muhurat sessions) is moved to
    # the last benchmark session before it, so it fills at the first session after its own date like any
    # other. 1.0-1.4 walked the benchmark's calendar and silently dropped those (18 on 2020-11-14).
    moved: dict = {}
    for d, cs in sig.items():
        if d in cal or not len(cal) or d < cal[0]:
            moved.setdefault(d, []).extend(cs)
            continue
        k = int(cal.searchsorted(d, side="right")) - 1
        moved.setdefault(cal[k], []).extend(cs)
    for cs in moved.values():
        cs.sort(key=lambda c: c["rs_excess"])
    sig = moved
    rate = prep.get("cash_rate")
    rate = (rate.reindex(cal).ffill().fillna(0.0) if (CREDIT_INTEREST and rate is not None)
            else pd.Series(0.0, index=cal))
    cash = float(cfg.account_size)
    open_pos: dict = {}
    pending: list = []
    trades, eq_log, held_log, gross_log = [], [], [], []
    costs_total = interest_total = 0.0
    skipped = {"gap_past_stop": 0, "risk_budget": 0, "no_open": 0}

    def bar(sym, d):
        f = frames[sym]
        return f.loc[d] if d in f.index else None

    def cover(sym, p, d, price, reason):
        nonlocal cash, costs_total
        fee = p["shares"] * price * side
        cash -= p["shares"] * price + fee
        costs_total += fee
        pnl = p["proceeds"] - p["shares"] * price - fee - p["fee"] - p["carry"] - p["paid"]
        risk = p["shares"] * p["risk_ps"]
        trades.append({
            "symbol": sym, "direction": "short", "setup": p["entry"], "entry_date": p["date"],
            "entry_price": round(p["price"], 4), "initial_stop": round(p["stop0"], 4),
            "exit_date": d, "exit_price": round(price, 4), "shares": round(p["shares"], 4),
            "exit_reason": reason, "pnl": round(pnl, 2), "notional": round(p["proceeds"], 2),
            "costs": round(fee + p["fee"], 2), "carry": round(p["carry"], 2), "paid": round(p["paid"], 2),
            "holding_days": (d - p["date"]).days, "sessions": p["n"],
            "r_multiple": round(pnl / risk, 4) if risk > 0 else float("nan"),
            "mfe_r": round(p["mfe"] / p["risk_ps"], 3) if p["risk_ps"] > 0 else float("nan"),
        })
        del open_pos[sym]

    last_close: dict = {}
    credits = prep.get("credits")
    credit_after = cal[0] - pd.Timedelta(days=1)
    for d in cal:
        # ---- a special dividend or demerger on a name held short: the short pays it, and the stop
        # and entry move down with the price (as for a long in portfolio_sim.credit_action)
        if credits is not None:
            for s, c in credits.on(d, credit_after, open_pos).items():
                p = open_pos[s]
                cash -= c * p["shares"]
                p["paid"] += c * p["shares"]
                for k in ("price", "stop", "stop0"):
                    p[k] -= c
                if s in last_close:
                    last_close[s] -= c
            credit_after = d
        # ---- equity at the previous close, which sizes today's entries; the collateral earns a day's interest
        liab = sum(p["shares"] * last_close.get(s, p["price"]) for s, p in open_pos.items())
        equity = cash - liab
        interest = equity * float(rate.get(d, 0.0)) / 252 if equity > 0 else 0.0
        cash += interest
        interest_total += interest
        equity += interest
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
                           "carry": 0.0, "paid": 0.0, "mfe": 0.0, "was_below50": False, "trailed": False}
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
            weinstein = p["entry"] in WEINSTEIN_KINDS
            if not weinstein and p["was_below50"] and sma50 == sma50 and cl > sma50:
                reason = "TREND"
            elif b["wk_line"] == b["wk_line"] and cl > b["wk_line"]:
                reason = "STAGE"
            elif not weinstein and p["n"] >= TIME_STOP and p["mfe"] < p["risk_ps"]:
                reason = "TIME"
            if reason:
                cover(s, p, d, cl, reason)
                continue
            if weinstein:
                # Weinstein's trail: the buy-stop comes down above each lower rally peak -- the last confirmed
                # weekly swing high, plus the stop buffer -- and never goes up
                sh = b["swing_hi"]
                if sh == sh:
                    lvl = float(sh) + STOP_ATR_BUFFER * float(b["atr"])
                    if cl < lvl < p["stop"]:
                        p["stop"], p["trailed"] = lvl, True
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
    dropped = {**dropped, **skipped, "interest": round(interest_total, 2)}
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
    """The newest stored run of the market's long book (`LONG_BOOKS`) with the same start and stage tag as this
    run and no overrides (the strategy as configured, not an experiment on it), or None. The start matters as
    much as the tag: a shorter run of the long book has no crash years to compare."""
    tag = out_dir.name[out_dir.name.find("_stage-"):] if "_stage-" in out_dir.name else ""
    start = out_dir.name.split("_", 1)[0]
    root = out_dir.parent.parent / LONG_BOOKS.get(market, LONG_BOOK)
    if not tag or not root.exists():
        return None

    def clean(p: Path) -> bool:
        f = p / "overrides.json"
        if not f.exists():
            return True
        try:
            import json
            return not json.loads(f.read_text()).get("overrides")
        except Exception:   # noqa: BLE001
            return False
    runs = [p for p in root.iterdir() if p.name.endswith(tag) and p.name.startswith(start + "_")
            and (p / "equity.csv").exists() and clean(p)]
    return max(runs, key=lambda p: (p / "equity.csv").stat().st_mtime) if runs else None


def excess_sharpe(eq: pd.Series, rf: pd.Series) -> float:
    """Annualised Sharpe ratio of the daily returns over the cash rate (`rf` is per session)."""
    r = eq.pct_change().dropna()
    x = r - rf.reindex(r.index).fillna(0.0)
    return float(x.mean() / x.std() * math.sqrt(252)) if x.std() > 0 else float("nan")


def index_short(eq: pd.Series, bench: pd.Series, rf: pd.Series) -> tuple[pd.Series, float]:
    """The first comparator: a short of the index at the strategy's own beta, through index futures, on capital
    that earns the cash rate. Beta is the slope of the strategy's daily excess return on the index's daily
    return over the run; the futures roll costs INDEX_ROLL_BPS a month on the short notional. Price returns,
    so the short pays no dividends -- a future prices them out."""
    r = eq.pct_change().dropna()
    ri = bench.reindex(eq.index).ffill().pct_change().reindex(r.index).fillna(0.0)
    x = r - rf.reindex(r.index).fillna(0.0)
    beta = float(np.cov(x, ri)[0, 1] / ri.var()) if ri.var() > 0 else 0.0
    out = rf.reindex(r.index).fillna(0.0) + beta * ri - abs(beta) * INDEX_ROLL_BPS / 10_000 / SESSIONS_PER_MONTH
    return pd.concat([pd.Series([1.0], index=eq.index[:1]), (1 + out).cumprod()]), beta


def hedge_tests(eq: pd.Series, bench: pd.Series, rf: pd.Series, long_eq: pd.Series | None,
                gross: pd.Series | None = None) -> tuple[dict, pd.DataFrame, str]:
    """The pass criteria, scored: (verdict, sleeve table, markdown).

    1. Standalone, against the beta-matched index short: a higher Sharpe ratio AND a shallower drawdown.
    2. Beside the long book at PASS_SLEEVE_PCT: the short sleeve's drawdown at least PASS_DD_POINTS shallower
       than a cash sleeve of the same weight, without a lower Sharpe ratio than that cash sleeve.
    Every Sharpe ratio is over the cash rate, and the cash sleeve and the index short earn it too.
    """
    idx_eq, beta = index_short(eq, bench, rf)
    cash_eq = (1 + rf.reindex(eq.index).fillna(0.0)).cumprod()
    st, si = _stats(eq), _stats(idx_eq)
    sh, shi = excess_sharpe(eq, rf), excess_sharpe(idx_eq, rf)
    verdict = {"beta": round(beta, 4), "sharpe": round(sh, 3), "max_dd": round(st["max_dd"], 2),
               "cagr": round(st["cagr"], 2), "index_short_sharpe": round(shi, 3),
               "index_short_max_dd": round(si["max_dd"], 2), "index_short_cagr": round(si["cagr"], 2)}
    verdict["c1"] = bool(sh > shi and st["max_dd"] > si["max_dd"])
    if gross is not None:
        crash = gross.loc["2020-02-19":"2020-03-23"]
        verdict["short_pct_mar2020"] = round(float(crash.mean()), 1) if len(crash) else float("nan")
    lines = [f"Beta to the index {beta:+.3f}. Every Sharpe ratio is over the cash rate.", "",
             "| Book | CAGR | Max DD | Sharpe |", "|---|---|---|---|",
             f"| Stage 4 shorts | {st['cagr']:+.2f}% | {st['max_dd']:.1f}% | {sh:.2f} |",
             f"| Index short at the same beta | {si['cagr']:+.2f}% | {si['max_dd']:.1f}% | {shi:.2f} |", "",
             f"**Criterion 1 (beats the index short on Sharpe and drawdown): {'PASS' if verdict['c1'] else 'FAIL'}.**"]
    rows = []
    if long_eq is not None:
        sleeves = {"short": eq, "cash": cash_eq, "index_short": idx_eq}
        for w in SLEEVE_WEIGHTS:
            for k in (("none",) if w == 0 else tuple(sleeves)):
                e = blend(long_eq, sleeves.get(k, eq), w)
                s_ = _stats(e)
                row = {"sleeve_pct": w, "sleeve": k, "cagr_pct": round(s_["cagr"], 2),
                       "max_dd_pct": round(s_["max_dd"], 2), "sharpe": round(excess_sharpe(e, rf), 3)}
                for y in CRASH_YEARS:
                    part = e[e.index.year == y]
                    row[f"dd_{y}"] = round(float(metrics.drawdown_series(part).min() * 100), 2) if len(part) else float("nan")
                rows.append(row)
        t = pd.DataFrame(rows).set_index(["sleeve_pct", "sleeve"])
        a, c = t.loc[(PASS_SLEEVE_PCT, "short")], t.loc[(PASS_SLEEVE_PCT, "cash")]
        gain = float(a["max_dd_pct"] - c["max_dd_pct"])
        verdict.update({"sleeve_dd_gain": round(gain, 2), "sleeve_sharpe": float(a["sharpe"]),
                        "cash_sleeve_sharpe": float(c["sharpe"]),
                        "c2": bool(gain >= PASS_DD_POINTS and a["sharpe"] >= c["sharpe"])})
        lines += ["", "| Sleeve | CAGR | Max DD | Sharpe | " + " | ".join(f"{y} DD" for y in CRASH_YEARS) + " |",
                  "|---|---|---|---|" + "---|" * len(CRASH_YEARS)]
        for (w, k), r in t.iterrows():
            lines.append(f"| {w}% {k} | {r['cagr_pct']:+.2f}% | {r['max_dd_pct']:.1f}% | {r['sharpe']:.2f} | "
                         + " | ".join(f"{r[f'dd_{y}']:.1f}%" for y in CRASH_YEARS) + " |")
        lines += ["", f"**Criterion 2 ({PASS_SLEEVE_PCT}% sleeve: drawdown at least {PASS_DD_POINTS:g} points shallower "
                  f"than the cash sleeve, Sharpe not lower): {'PASS' if verdict['c2'] else 'FAIL'}** "
                  f"(drawdown {gain:+.1f} points; Sharpe {a['sharpe']:.2f} vs {c['sharpe']:.2f})."]
    else:
        verdict["c2"] = None
        lines += ["", "Criterion 2 not scored: no stored long-book run with this run's start and stage."]
    return verdict, pd.DataFrame(rows), "\n".join(lines)


# ------------------------------------------------------------------ documentation

DOC = {
    "key": "stage4_shorts",
    "name": "Stage 4 shorts",
    "description": (
        "Weinstein's short: sell the weekly close that breaks a Stage 3 top's low, or the first pullback to that "
        "broken level, in a weak industry group while the market itself is in Stage {MARKET_STAGE}; buy back on a "
        "stop lowered above each lower rally peak or a weekly close above the 30-week line. Judged as a hedge, "
        "against an index short at the same beta and beside the best long book, not on its own return."
    ),
    "status": (
        "NOT YET MEASURED (v1.5). The last test before retirement: Weinstein's own entry (C + P), the hedge "
        "measured against a beta-matched index-futures short and a cash sleeve, both earning the cash rate, beside "
        "the best long book. Queued for the optimise stage (2013-2021) only, with the pass criteria written in the "
        "caveats before the runs. v1.4 (failed rally to the line, optimise): -1.8% a year US, -3.7% India, no "
        "selection edge, and no hedge value against a cash sleeve beside any of 47 long books."
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
        "Step 3 -- the signal. Entry C (shipped from 1.5): a weekly close below the low of a Stage 3 top "
        "and below the 30-week line. Entry P (shipped): within {PULLBACK_WEEKS} weeks, the first week that "
        "rallies back to the broken low and closes below it again. Entries B and A (1.0-1.4, variants): "
        "a failed rally to the line after {STAGE4_MIN_SESSIONS} sessions in Stage 4, and a close at a new "
        "{BREAKDOWN_BARS}-session low on volume.",
        "Step 4 -- the market and the group. C and P need the market index's own weekly stage to be "
        "{MARKET_STAGE} and the stock's industry group to rank at most {WEAK_GROUP_MAX_RANK} on group "
        "relative strength. B and A need the index below its {INDEX_SMA}-day average or that average lower "
        "than {INDEX_SLOPE_BARS} sessions ago.",
        "Step 5 -- the short, at the next open, sized to risk {RISK_PCT}% of equity to the stop, with "
        "at most {MAX_OPEN_RISK_PCT}% at risk on all shorts together.",
        "Step 6 -- the cover. C and P: the stop, lowered above each new lower weekly rally peak, or a weekly "
        "close above the 30-week line. B and A: the stop (trailing from session {TRAIL_START}), a close above "
        "the {TREND_SMA}-day average once below it, a weekly close above the line, or the time stop.",
        "Judged as a hedge, in every run. (1) Against an index short at the strategy's own beta, held through "
        "index futures on capital earning the cash rate: it must have the higher Sharpe ratio and the shallower "
        "drawdown. (2) As a {PASS_SLEEVE_PCT}% sleeve beside the market's best long book (momentum_vol_scaled "
        "in India, quality_momentum in the US), rebalanced each month-end: its drawdown must be at least "
        "{PASS_DD_POINTS} points shallower than a cash sleeve of the same weight, without a lower Sharpe ratio. "
        "The account's equity earns the cash rate too, so all three books are on the same footing.",
        "Running it. `python -m jobs enqueue backtest --market us --strategies stage4_shorts --stage "
        "optimise`; the 1.4 entry through `--bt '--entries B'`.",
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
        "Entry C, breakdown from a Stage 3 top (shipped from 1.5). The stage known at the previous week's close "
        "is 3, and this week closes below the top's low -- the lowest weekly low from the week the stage machine "
        "dates the top's start to the previous week -- and below the 30-week line. That is the close that starts "
        "the machine's 3 -> 4 transition; the machine confirms Stage 4 weeks later, and the short does not wait. "
        "Decided at the week's last close.\n\n**Weinstein (1988, ch. 7):** short the break below a top's "
        "support. **Guide (§5):** the same.",
        "Entry P, the first pullback (shipped from 1.5). Within {PULLBACK_WEEKS} weeks of a C, the first week "
        "whose high comes within {TOUCH_PCT}% of the broken low (or above it) and closes back below it and below "
        "the line. A week that closes above the broken low first ends the watch.\n\n**Weinstein:** his "
        "preferred short, the pullback toward the breakdown point.",
        "Weak group and weak market (C and P). The stock's industry group ranks at most {WEAK_GROUP_MAX_RANK} on "
        "the stored point-in-time group relative strength (1-99) on the signal day, and the market index's own "
        "weekly stage, from the same machine, is {MARKET_STAGE}.\n\n**Weinstein:** short weak stocks in weak "
        "groups, with the market in Stage 3 or 4. Differs: the market must be in Stage {MARKET_STAGE} itself, "
        "as the test brief specified.",
        "Entry B, failed rally to the line (1.0-1.4's entry, a variant from 1.5). At least {STAGE4_MIN_SESSIONS} "
        "sessions in Stage 4 before today; today's high at or above the line less {TOUCH_PCT}%; "
        "today's close below the line. The line is the last completed week's 30-week average.\n\n"
        "**Guide (§3 Entry B):** the same, on the 150-day average.",
        "Entry A, breakdown (a variant, off by default). In Stage 4, a close below the lowest close "
        "of the prior {BREAKDOWN_BARS} sessions, on volume at least {BREAKDOWN_VOL_MULT} times its "
        "50-session average.\n\n**Guide (§3 Entry A):** the same.",
        "Initial stop. C: the top's last rally peak (the last weekly swing high known at the signal week's "
        "close) plus {STOP_ATR_BUFFER} ATR({ATR_BARS}). P: the highest high since the breakdown plus the same "
        "buffer. B: the highest high of the last {RALLY_BARS} sessions (the rally into the "
        "line) plus {STOP_ATR_BUFFER} ATR({ATR_BARS}). A: the lower of the {BREAKDOWN_STOP_BARS}-session "
        "high and the line, plus the same buffer. A signal whose stop is more than {MAX_STOP_PCT}% "
        "above the close is skipped, and so is one whose next open is above the high the stop sits "
        "over (the stop less its buffer) or more than {MAX_STOP_PCT}% below the stop.\n\n**Guide (§3 Initial stop):** the same.",
        "Market filter (B and A). The signal's date has the index below its {INDEX_SMA}-day average, or that "
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
        "costs. From 1.5 the account's equity earns the market's cash rate each session (the collateral's "
        "interest); 1.0-1.4 credited none.",
    ),
    "exit_rules": (
        "Each session the stop is checked first, then the close rules in this order; the first that "
        "applies covers the whole position.",
        "Stop. The day's high at or above the buy-stop covers at the stop, or at the open when the "
        "stock gaps up through it.\n\n**Guide (§3 Exits):** the same; the guide adds the fill rule "
        "under costs.",
        "C and P (Weinstein's). The stop, then a weekly close above the 30-week line (the stage exit below). After "
        "each close the stop comes down to the last confirmed weekly swing high plus {STOP_ATR_BUFFER} ATR when "
        "that is lower and still above the close -- above each lower rally peak. No trend exit and no time stop."
        "\n\n**Weinstein (1988):** lower the buy-stop above each new lower rally peak; hold while the line falls.",
        "Trailing stop (B and A). From session {TRAIL_START}, after each close the stop moves down to the highest "
        "high of the last {TRAIL_BARS} sessions when that is lower. Never up.\n\n"
        "**Guide (§3 Exits):** the same.",
        "Trend exit (B and A). A close above the {TREND_SMA}-day average, once a close since the short has been "
        "below it, covers at that close.\n\n**Guide (§3 Exits):** the same.",
        "Stage exit. On a week's last session, a close above that week's 30-week average covers at "
        "that close.\n\n**Guide (§3 Exits):** the same.",
        "Time stop (B and A). After {TIME_STOP} sessions, if the price never fell 1R below the entry, cover at "
        "the close.\n\n**Guide (§3 Exits):** the same.",
        "A position open when the backtest ends is covered at its last close and marked OPEN.",
    ),
    "caveats": (
        "**COST ASSUMPTIONS, which carry the result.** US: {US_BORROW_PCT}% a year borrow, the "
        "general-collateral rate for a liquid stock; hard-to-borrow names can cost tens of percent and "
        "are not identified, because borrow rates and short interest are not stored. Dividends are "
        "charged at a flat {US_DIVIDEND_PCT}% a year because stored prices are not dividend-adjusted. "
        "India: a short is held through stock futures, so it pays {INDIA_ROLL_BPS} bps per month to "
        "roll and a flat {INDIA_DIVIDEND_PCT}% dividend yield (futures price dividends out). From 1.5 the "
        "account's equity earns the cash rate (US T-bills; India's realised liquid-fund yield); 1.0-1.4 "
        "credited none, which understated India by about 6.5% a year.",
        "**India's futures list is a proxy.** The stored derivatives are index contracts only, so "
        "'has futures' is read as 'ranks in the top {FNO_PROXY_TOP} by traded value that day' among "
        "stocks with any Stage 4 signal. The real list differs and the ban list is not applied. Lot sizes are "
        "not stored either; each run counts the shorts that reached one lot by NSE's minimum contract value "
        "({INDIA_LOT_MIN_VALUE} rupees). At a ₹20 lakh account almost none do, so India's stock book is an "
        "upper bound; the tradeable form is the index-futures short it is compared with.",
        "**Survivorship works against this strategy here.** The stored universe is today's lists, which "
        "leave out companies that collapsed and were delisted -- often the best shorts. The guide's own "
        "warning: a test on survivors makes shorting look worse than it was.",
        "**The R figures are true risk multiples**: profit after costs and carry over the initial "
        "risk to the stop. Gaps through the stop can make a loss larger than -1R.",
        "**PASS CRITERIA FOR 1.5, written before its runs (2026-11-14): the last test.** Optimise stage, base "
        "costs, entries C + P, in BOTH markets: (1) a higher Sharpe ratio (over the cash rate) AND a shallower "
        "maximum drawdown than an index-futures short at the strategy's own beta, earning the cash rate; (2) as a "
        "{PASS_SLEEVE_PCT}% sleeve beside the best long book, a maximum drawdown at least {PASS_DD_POINTS} points "
        "shallower than a cash sleeve of the same weight (earning the cash rate) without a lower Sharpe ratio. "
        "Failing either retires the strategy as a hedge. 1.0's criterion (beside momentum_baseline, no interest) "
        "is superseded.",
        "**The group gate reads today's industry labels.** The group's rank is point in time, but which group a "
        "stock belongs to is its classification today (no history is stored).",
        "**The market's own Stage 4 comes late in this window.** Over 2013-2021 the index was in Stage "
        "{MARKET_STAGE} on about 6% of US sessions and 21% of India's, mostly after the falls -- from 13 March 2020 "
        "in both -- so C and P short mainly in the rebounds. A real bear market (2008) is outside the stages.",
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
    version = "1.5"
    changelog = (
        ("1.5", "2026-11-14",
         "The last test before retirement (review 2026-11-14). Weinstein's own entry ships: C, the weekly close "
         "below a Stage 3 top's low (off the stage machine's onsets), and P, the first pullback to that broken "
         "level, gated by a weak industry group (group RS rank at most WEAK_GROUP_MAX_RANK) and the market index "
         "itself in Stage MARKET_STAGE, with Weinstein's exits (a stop lowered above each lower rally peak, the "
         "stage exit). The 1.4 entry B stays as a variant. Measurement: the account earns the cash rate; every "
         "run scores the hedge against an index short at the same beta and a cash sleeve, both earning it, beside "
         "the best long book (LONG_BOOKS) instead of momentum_baseline. Bug: a signal on a session missing from "
         "the benchmark's calendar (India's Muhurat Saturdays) was dropped; it now fills at the next session."),
        ("1.4", "2026-11-06",
         "The stage model moved under it: Stage analysis 2.11 rebuilt `stage_series` on Weinstein's definitions -- "
         "Stage 4 now also starts on a close below the stage's support (a base's low, the last weekly swing low, a "
         "top's low) and holds while the close stays below the line, instead of waiting for the line to fall for the "
         "confirmation weeks; a top no longer becomes a base, and Stage 2 needs a breakout. This strategy's own rules "
         "are unchanged, but which weeks read Stage 4 is not, so its signals move and the version is bumped by hand "
         "(the fingerprint cannot see a change in another module's code)."),
        ("1.3", "2026-10-26",
         "Signals read total return: the stage, the 30-week line, the 50-day, the ATR and both entries are computed on prices back-adjusted for credited special dividends and demergers, so a demerger is no longer read as a Stage 4 breakdown; each stop and line is then put back on its own day's price scale (corporate_actions.pit_scale), so none carries a later action. Fills and turnover read traded prices."),
        ("1.2", "2026-10-25",
         "Backtest mechanics, no rule changed: a short now pays special dividends and demergers on the "
         "ex-date (marketdata/corporate_actions.py), with its stop moved down by the payout; the flat "
         "dividend yield covers ordinary ones only. Before, a short pocketed the payout as a fall. Stored "
         "prices were also corrected where the source left a split unadjusted before its year-start "
         "(MOTILALOFS and GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar "
         "(marketdata/splits.py correct)."),
        ("1.1", "2026-10-25",
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
    caveats = tuple(DOC["caveats"]) + (corporate_actions.CAVEAT_SHORT,)
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "time_series"
    style = "trend"
    horizon = "swing"
    runner = "stage4_shorts"

    param_docs = (
        ("Entries", "ENTRY_WEINSTEIN", "1 shorts Weinstein's breakdown from a Stage 3 top (C) and its first pullback (P)."),
        ("Pullback window", "PULLBACK_WEEKS", "Weeks after a breakdown in which the first pullback is shorted."),
        ("Weak group", "WEAK_GROUP_MAX_RANK", "C and P: the industry group's RS rank (1-99) at most this."),
        ("Market stage", "MARKET_STAGE", "C and P: the market index's own weekly stage must be this."),
        ("Cash interest", "CREDIT_INTEREST", "1 credits the cash rate on the account's equity each session."),
        ("Old entries", "ENTRY_FAILED_RALLY", "1 shorts the failed rally to the line (B); ENTRY_BREAKDOWN 1 the breakdown (A)."),
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

    @classmethod
    def setups_live(cls, raw: pd.DataFrame, cfg, symbol: str, years: int | None = 5, anchors=None) -> list[dict]:
        """The chart's Trade setups layer: this symbol's signals of the shipped entries, through `screen_signal`,
        each replayed through `run` on this one symbol (backtesting/portfolio_setups.py)."""
        from . import portfolio_setups as pset
        market = pset.market_of(cfg)
        braw = cache.load_cached(market, cfg.benchmark_ticker)
        if braw is None or len(raw) < MIN_BARS:
            return []
        bench = braw["close"].astype(float)
        cr = corporate_actions.credits(market, [symbol])
        f = symbol_frame(raw, bench, cr if len(cr) else None)
        start = pset.since(f, years)
        # one symbol cannot be ranked against the tape, so India's futures proxy is not checked here
        prep = {"market": market, "bench": bench[bench.index <= f.index[-1]], "frames": {symbol: f}, "fno_rank": None,
                "weak": market_weak(bench), "mkt_stage": market_stage(braw), "group": group_ranks(market),
                "cash_rate": index_data.cash_rate_series(market, bench.index)[0],
                "credits": corporate_actions.Credits.for_market(market, [symbol])}
        entries = default_entries()
        use_filter = bool(MARKET_FILTER)
        trades = run(prep, str(start.date()), entries, use_filter)[0]
        by_entry = {pd.Timestamp(t["entry_date"]): t for t in trades.to_dict("records")}
        floor = cfg.screener.min_dollar_volume or 0
        low_prior = f["close"].shift(1).rolling(BREAKDOWN_BARS, min_periods=BREAKDOWN_BARS).min()
        names = {"B": "Failed rally to the line", "A": "Breakdown to a 52-week low",
                 "C": "Breakdown from a Stage 3 top", "P": "First pullback to the broken top"}
        traded = pset.anchor_bars(f, anchors, lag=1)   # a run's short fills at the open after its signal
        out = []
        for kind in entries:
            hits = [k for k in range(len(f)) if bool(f[f"sig_{kind.lower()}"].iloc[k]) and f.index[k] >= start]
            for ep, at in (p for g in pset.group(hits) for p in pset.parts(g, traded)):
                judged = [(k, *screen_signal(prep, symbol, f, f.index[k], kind, use_filter)) for k in ep]
                # judged on the bar a selected run traded, else the first that passed, else the first
                k, c, why = ([x for x in judged if x[0] == at] or [x for x in judged if x[1] is not None] or judged)[0]
                d, r = f.index[k], f.iloc[k]
                stop = float(r[f"stop_{kind.lower()}"])
                states = pset.ordered([(x,) for x in FILTERS], why)
                gates = pset.rows([
                    ("liquidity", "Liquidity", float(r["turnover"]), f"{LIQ_BARS}-session median traded value at least {floor:,.0f}", states[0]),
                    ("fno", "Futures proxy", "not checked here", f"India: among the {FNO_PROXY_TOP} most traded (a stock future to short)", None),
                    ("rs", "Weaker than the index", f"{float(r['rs_excess']):+.1f} points", f"worse than the index over {RS_BARS} sessions", states[2]),
                    ("stop", "Stop distance", f"{(stop / float(r['close']) - 1) * 100:.1f}%", f"above the close, at most {MAX_STOP_PCT:g}% away", states[3]),
                    (("market", "Market in Stage 4", f"stage {int(prep['mkt_stage'].asof(d))}",
                      f"the index's own weekly stage is {MARKET_STAGE}", states[4] if use_filter else None)
                     if kind in WEINSTEIN_KINDS else
                     ("market", "Weak market", "yes" if bool(prep["weak"].asof(d)) else "no",
                      f"the index below its {INDEX_SMA}-day, or the {INDEX_SMA}-day lower than {INDEX_SLOPE_BARS} sessions ago"
                      + ("" if use_filter else " (off)"), states[4] if use_filter else None)),
                    ("group", "Weak group", f"rank {group_rank(prep, symbol, d):.0f}",
                     f"industry group RS rank at most {WEAK_GROUP_MAX_RANK}",
                     states[5] if kind in WEINSTEIN_KINDS else None)])
                setup = pset.rows([(("stage", "Stage 3 top", f"stage {int(r['stage'])}",
                                     "a top the stage machine dated, broken by a weekly close", True)
                                    if kind in WEINSTEIN_KINDS else
                                    ("stage", "Stage 4", f"{int(r['stage4_run'])} sessions", "the last completed week's stage is 4", True)),
                                   (kind, names[kind], "yes", "the signal", True)])
                day = lambda i: str(f.index[i].date())
                shapes = [{"shape": "level", "bars": 15, "to": day(k), "price": float(r["line"]), "role": "pivot",
                           "label": f"30-week line {float(r['line']):,.2f}"}]
                if kind in WEINSTEIN_KINDS:
                    lvl = float(r[f"support_{kind.lower()}"])
                    shapes.append({"shape": "level", "bars": 30, "to": day(k), "price": lvl, "role": "tight",
                                   "label": f"the top's broken low {lvl:,.2f}"})
                elif kind == "B":
                    w = f.iloc[max(0, k - RALLY_BARS + 1): k + 1]
                    shapes.append({"shape": "box", "from": str(w.index[0].date()), "to": day(k), "top": float(w["high"].max()),
                                   "bottom": float(w["low"].min()), "role": "base", "label": f"the rally: {RALLY_BARS} sessions"})
                else:
                    shapes.append({"shape": "level", "bars": 30, "to": day(k), "price": float(low_prior.iloc[k]), "role": "tight",
                                   "label": f"{BREAKDOWN_BARS}-session closing low {float(low_prior.iloc[k]):,.2f}"})
                nxt = f.index[k + 1] if k + 1 < len(f) else None
                trade = by_entry.get(nxt) if c is not None and nxt is not None else None
                oc = pset.outcome(f, "short", trade, "not shorted: the next open was past the stop's structure, "
                                  "the risk was over the limit, or the stock was already short" if c is not None else "")
                text = (f"{names[kind]} on {d.date()}: " + {
                    "B": "the high reached the falling 30-week line and the close fell back below it.",
                    "A": f"a close below the lowest close of {BREAKDOWN_BARS} sessions on volume.",
                    "C": "the week closed below the Stage 3 top's low and below the 30-week line.",
                    "P": "the week rallied back to the broken low and closed below it again."}[kind])
                out.append(pset.episode(
                    f, ep, k, name=names[kind], side="short", kind="pass" if c is not None else "fail",
                    why=REFUSED.get(why, why), gates=gates, setup_rows=setup,
                    shapes=shapes, text=text, entry=float(r["close"]), stop=stop,
                    entry_text=" ".join(cls.render_doc(x) for x in cls.entry_rules),
                    outcome_=oc if c is not None else None, anchored=at is not None))
        return sorted(out, key=lambda e: e["base_from"])


def main(argv: list[str] | None = None) -> dict | None:
    from ..paths import run_dir
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    ap = argparse.ArgumentParser(description="Stage 4 shorts")
    ap.add_argument("--strategy", default="stage4_shorts")
    ap.add_argument("--market", required=True, choices=list(MARKETS.keys()))
    ap.add_argument("--start", required=True)
    ap.add_argument("--entries", default=default_entries(), choices=["CP", "C", "P", "A", "B", "AB", "BA"],
                    help="C = Weinstein's breakdown from a Stage 3 top, P = its first pullback, "
                         "B = failed rally to the line, A = breakdown to a 52-week low")
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
        + (f"Interest at the cash rate is credited on the account's equity: {dropped.get('interest', 0):,.0f} over the run."
           if CREDIT_INTEREST else "No interest is credited."),
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
    if short_costs(a.market)["futures_only"] and len(tdf):
        fit = int((tdf["notional"] >= INDIA_LOT_MIN_VALUE).sum())
        perf.notes.append(f"Whole lots: {fit} of {len(tdf)} shorts reached one futures lot (proxy: a contract worth at "
                          f"least {INDIA_LOT_MIN_VALUE:,.0f}) at an account of {cfg.account_size:,.0f}.")
    rf = prep["cash_rate"].reindex(eq.index).ffill().fillna(0.0) / 252
    long_dir = find_long_book(a.market, out)
    leq = (pd.read_csv(long_dir / "equity.csv", index_col=0, parse_dates=True)["equity"]
           if long_dir is not None else None)
    tables, verdicts = [], {}
    for lvl in (1.0, max(COST_LEVELS)):
        v, t, md = hedge_tests(runs[lvl][1], prep["bench"], rf, leq, runs[lvl][3])
        verdicts[lvl] = v
        if len(t):
            t.insert(0, "cost_level", lvl)
            tables.append(t)
        book = (f"Long book: `{long_dir.parent.name}/{long_dir.name}`. " if long_dir is not None else "")
        extra.append((f"Hedge tests (cost x{lvl:g})", f"{book}Monthly rebalance to the split.\n\n{md}"))
    if tables:
        pd.concat(tables).to_csv(out / "sleeve_blend.csv", index=False)
    pd.DataFrame(verdicts).T.to_csv(out / "hedge_tests.csv")
    base = verdicts[1.0]
    perf.notes.append(
        f"HEDGE TESTS (base cost): criterion 1, beats the index short at beta {base['beta']:+.3f} on Sharpe "
        f"({base['sharpe']:.2f} vs {base['index_short_sharpe']:.2f}) and drawdown ({base['max_dd']:.1f}% vs "
        f"{base['index_short_max_dd']:.1f}%): {'PASS' if base['c1'] else 'FAIL'}; criterion 2, "
        + ("not scored (no long-book run)." if base.get("c2") is None else
           f"{PASS_SLEEVE_PCT}% sleeve beside {long_dir.parent.name} vs a cash sleeve: drawdown "
           f"{base['sleeve_dd_gain']:+.1f} points, Sharpe {base['sleeve_sharpe']:.2f} vs "
           f"{base['cash_sleeve_sharpe']:.2f}: {'PASS' if base['c2'] else 'FAIL'}.")
        + f" Average short in the 2020 crash: {base.get('short_pct_mar2020', float('nan')):.1f}% of equity.")
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
