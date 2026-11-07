"""Darvas boxes — buying the breakout from a confirmed range at a new 52-week high.

Nicolas Darvas's method (How I Made $2,000,000 in the Stock Market, 1960), built to the rules of
research/learn-strat-darvas.md, sections 3 and 4. A box top is a 52-week high that holds for
TOP_CONFIRM sessions; its bottom is the lowest low after it, held for BOTTOM_CONFIRM sessions while
the top was not exceeded. Once the box is complete a buy-stop rests just above the top and a
sell-stop just below the bottom. Each later, higher box raises the stop to its own bottom; that is
the only exit.

The boxes come from core/darvas.py, the one implementation: this module's entry and the backtest's
`darvas` exit mode (backtesting/portfolio_sim.py), which trails the stop by the same boxes, both call
it with the constants below.

Not the same thing as chart_pattern_spec's FBASE / RECT or core/chart_patterns' FLAT: those fit a
fixed window to a finished range. A Darvas box is defined by its confirmation sessions, and exists
only from the session that confirms its bottom.
"""

import datetime as dt

import numpy as np
import pandas as pd

from ..config.base import MarketConfig
from ..core import darvas
from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import (
    tradable_point_in_time,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
# Reused rather than copied: the suffix-driven market lookup and the tick rounding already exist.
from .rs_leaders import _market_of
from .trend_pullback import round_tick

# ---- the box (guide §3 "Setup", §4)
NEW_HIGH_LOOKBACK = 250    # the box top's high is the highest of this many sessions, itself included
TOP_CONFIRM = 3            # ...and the next this-many sessions' highs are all lower
BOTTOM_CONFIRM = 3         # the bottom is held for this many sessions in a row
MAX_BOX_DEPTH_PCT = 15.0   # G2: (top - bottom) / top, at most this

# ---- entry and stop (guide §3 "Entry", "Initial stop")
ENTRY_BUFFER_PCT = 0.1     # the buy-stop sits this far above the box top (the guide's "one tick", as a
                           # test-friendly 0.1%); the stop sits one market tick below the bottom
NOMINAL_TARGET_R = 10.0    # for sizing and reporting only: there is no profit target

# ---- research switches, all OFF (guide §3 "Universe and filters", "Entry", "Exits")
REQUIRE_BREAKOUT_VOLUME = 0  # 1 = a fill whose session's volume is under BREAKOUT_VOL_MULT x its
BREAKOUT_VOL_MULT = 1.4      #     50-day average sells at the next open (portfolio_sim min_breakout_vol)
REQUIRE_MARKET_UPTREND = 0   # 1 = G3: the market's benchmark closes above its MARKET_SMA-day average
MARKET_SMA = 50
REQUIRE_EPS_GROWTH = 0       # 1 = G4: the latest published quarter's EPS up at least MIN_EPS_GROWTH_PCT
MIN_EPS_GROWTH_PCT = 20.0    #     on the same quarter a year earlier
TIME_STOP_BARS = 0           # the guide's optional time stop, 40 sessions when on: sold at the close of
                             # this session after the entry if no higher box has formed by then and
                             # that close is below the entry (0 = off)

DV01 = "S1"   # a complete Darvas box, not yet broken either way

#: Scans kept per process (`_boxes`): a backtest walks one symbol's bars in order, so the last few
#: symbols are all a scan ever reuses.
_SCAN_CACHE_SIZE = 8


def stop_below(bottom: float, tick: float) -> float:
    """The sell-stop under a box bottom: one market tick below it. The entry's initial stop and the
    darvas exit mode's trailing stop (backtesting/portfolio_sim.py) both use this, so they agree."""
    return round_tick(bottom - tick, tick, "down") if tick > 0 else bottom


def buy_above(top: float, tick: float) -> float:
    """The buy-stop over a box top: ENTRY_BUFFER_PCT above it, rounded up to the tick. The entry and the
    simulator's box pyramid (`--pyramid-at box`, backtesting/portfolio_sim.py) both use this."""
    return round_tick(float(top) * (1 + ENTRY_BUFFER_PCT / 100), tick, "up")


class DarvasStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-03",
         "v1 baseline: Darvas boxes to research/learn-strat-darvas.md sections 3-4. A 250-session-high "
         "top held 3 sessions, a bottom held 3 sessions, at most 15% deep; a buy-stop 0.1% over the top, "
         "a stop one tick under the bottom, trailed by each higher box (the new `darvas` exit mode). The "
         "volume, market, earnings and time-stop rules are switches, all off. No pyramiding."),
    )
    key = "darvas"
    name = "Darvas box"
    description = (
        "Nicolas Darvas's boxes: buy the break of a confirmed range at a new 52-week high, and "
        "trail the stop up by each higher box."
    )
    style = "breakout"
    behaviour = "trend_momentum"
    horizon = "swing"
    gate_codes = ("G1", "G2", "G3", "G4")
    screen_key = "near_highs"
    screen_gates = {"G1": "H3"}
    watch_codes = ()
    setup_codes = (DV01,)
    setup_names = {DV01: "Darvas box"}
    gate_titles = {"G1": "Near the 52-week high", "G2": "Box at most {MAX_BOX_DEPTH_PCT}% deep",
                   "G3": "Market above its {MARKET_SMA}-day", "G4": "EPS growth"}
    nominal_target = True
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("box_top", "box_bottom", "box_depth_pct", "box_top_date", "box_bottom_date", "box_done_date")
    extra_numeric_columns = ("box_top", "box_bottom", "box_depth_pct")
    # Read only after evaluate(): by build_plans, signal_meta and the darvas exit mode.
    signal_exempt_consts = ("ENTRY_BUFFER_PCT", "NOMINAL_TARGET_R", "REQUIRE_BREAKOUT_VOLUME",
                            "BREAKOUT_VOL_MULT", "TIME_STOP_BARS")

    thesis = (
        "A stock at a new high has no trapped holders above it, and a tight range there shows sellers "
        "are not pushing it down. Buy the break of that range, cut the loss at its floor, and let each "
        "higher range raise the floor: many small losses, paid for by the few trends that run for many boxes."
    )
    how_it_works = (
        "**The idea.** Darvas's method as the Learn guide writes it: a range that forms at a new "
        "52-week high, bought on its break, held until a box bottom breaks.",
        "**Qualify.** The market's liquidity floor, then the close near the 52-week high (G1, the "
        "Near-highs screen's H3). "
        "A box bought is at most {MAX_BOX_DEPTH_PCT}% deep (G2), so a live one passes G1 too.",
        "**The box (S1).** A top: a session whose high is the highest of {NEW_HIGH_LOOKBACK} sessions, "
        "followed by {TOP_CONFIRM} lower highs. A bottom: the lowest low since the top, then "
        "{BOTTOM_CONFIRM} sessions that do not go below it, with no high above the top meanwhile. A "
        "high above the top first means no box; the search restarts there. See Setups.",
        "**Buy.** From the session that confirms the bottom, a buy-stop {ENTRY_BUFFER_PCT}% above "
        "the top, renewed each session while no high has gone above the top and no low below the "
        "bottom. A gap above it fills at the open. See Entry.",
        "**Stop.** One tick below the box bottom. Each later box whose top is above the last one's "
        "raises it to one tick under the new bottom; it is never lowered. See Stop and Exit.",
        "**Sell.** Only on the stop. No profit target; the time stop is a switch, off. See Exit.",
        "**Switches, all off.** Breakout volume, a market filter (index above its {MARKET_SMA}-day), "
        "Darvas's earnings rule (EPS up {MIN_EPS_GROWTH_PCT}%+) and the guide's 40-session time "
        "stop. Each is a parameter for a backtest variant, not part of the shipped rules.",
    )
    caveats = (
        "**No pyramiding.** Darvas added to a winner on each new box's breakout; version 1.0 buys "
        "once per position and only trails the stop. A breakout from a higher box while held is not "
        "bought. The backtester can test his add as a variant (`--pyramid 0.5 --pyramid-at box`: half "
        "size at the breakout, the rest over the next higher box's top, the stop then under its "
        "bottom) -- one add, not his repeated ones, and not part of the strategy's rules.",
        "**Daily bars, worse case first.** A session whose range covers both the buy-stop and the stop "
        "buys and sells the same session, at the stop. A gap below the stop fills at the open, so a "
        "loss can exceed 1R.",
        "**The new-high test needs a full year.** A top must be the highest of {NEW_HIGH_LOOKBACK} "
        "sessions, so a listing younger than that has no boxes; Darvas's preferred all-time high is "
        "not tested.",
        "**Deep boxes still trail.** The {MAX_BOX_DEPTH_PCT}% limit is on the box that is bought. A "
        "later box of any depth raises the stop, as in the guide's Bharat Electronics example, where a "
        "29%-deep box moved the stop from 221 to 230.",
        "**A resting order can outlive its box.** The buy-stop is renewed only while the box is intact. "
        "A session that trades above the top but not up to the buy-stop leaves an order that rests for "
        "the simulator's usual 10 business days before it expires.",
        "**The guide's floors are not used.** Its $15 / ₹100 price and $20m / ₹10 crore turnover floors "
        "are replaced by the market's own liquidity floor (see Filters): a price floor on "
        "split-adjusted history deletes the early years of exactly the stocks that rose most.",
        "**Run it with its exit.** `--exit-mode darvas --no-target` (the page's backtest command adds "
        "them). Without them the default bracket sells at the nominal target and never trails.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "FAILS ITS IN-SAMPLE CRITERION in both markets. Pass criterion, written before the runs: excess "
        "CAGR over the market's benchmark above 0 in-sample, on more than 50 trades. v1.0, optimise stage "
        "(2013-2021, in-sample), as configured (every switch off), measured 2026-11-05: US 6.76% CAGR, "
        "excess -7.25 points a year, Sharpe 0.49 (benchmark 0.88), max drawdown -38.2% (benchmark -34.1%), "
        "848 trades, 39% won, average +0.16R, median hold 27 days; India 8.07% CAGR, excess -5.46 (-7.94 "
        "at the standard cost), Sharpe 0.63 (0.86), max drawdown -27.5% (-38.3%), 527 trades, 37% won, "
        "average +0.21R, median hold 24 days. The box trail sells most trades early (three in four exits "
        "are a trailed stop, median R -0.28 US, -0.40 India), so the few long runs (about one trade in "
        "twenty reaches 3R) do not pay for the rest. Same stage, for comparison: Donchian v1.5 excess "
        "-10.40 US, -1.69 India; Chart patterns excess -9.22 US (v1.18), -6.13 India (v1.19). Verify not "
        "run, and not to be run on this version: it failed before verify. VARIANTS, optimise stage, "
        "measured 2026-11-07, all FAIL their criterion (written before them, per market: excess CAGR above "
        "0 at the run's and at the standard cost, on more than 50 trades). Exit on a close below the "
        "50-day average (--exit-mode ma): US 12.26% CAGR, excess -1.75 (-1.91 standard cost), Sharpe 0.79, "
        "max drawdown -26.9%, 612 trades, median hold 39 days; India excess -4.34 (-6.16), Sharpe 0.68, "
        "max drawdown -26.5%. A 3-ATR chandelier trail (--exit-mode trail_atr): US excess -8.70, India "
        "-3.73 (-6.07), Sharpe 0.77. The market switch (G3 on, box exit): US excess -8.13, India -6.69 -- "
        "worse in both. The slower exit is the only change that moved the US result much: it keeps more "
        "of the long runs (6% of trades reach 3R against 4.5%). No variant has become a version. LAST "
        "ROUND, queued 2026-11-07, US only, on the 50-day exit, optimise stage: momentum ranking "
        "(--rank-by momentum), Darvas's box add (--pyramid 0.5 --pyramid-at box), and both. Same "
        "criterion, written before them. Six US variants will then have been tried, so a pass by a "
        "small margin is weak evidence; if none passes, the method is judged not to beat buy and hold "
        "here and the refining stops."
    )
    gate_docs = {
        "G1": (
            "Close near the 52-week high: the Near-highs screen's H3, whose threshold that screen's page "
            "shows.\n\n"
            "Implied, while H3 allows {MAX_BOX_DEPTH_PCT}% or more, by any live box that passes G2 (the "
            "close is above a bottom at most {MAX_BOX_DEPTH_PCT}% under a 52-week-high top), so it "
            "records where the candidates come from rather than refusing boxes. The screen's "
            "200-day tests (H1, H2) are not applied: Darvas used no moving average."
        ),
        "G2": (
            "The box is at most {MAX_BOX_DEPTH_PCT}% deep.\n\n"
            "- **Depth:** (top − bottom) ÷ top × 100, of the latest complete box.\n"
            "- **Fails:** deeper. A deeper box means a wider stop.\n"
            "- With no complete box it passes as not reached; the missing setup (S1) stops the trade."
        ),
        "G3": (
            "The market's benchmark closes above its {MARKET_SMA}-day simple average -- a research "
            "switch, OFF unless REQUIRE_MARKET_UPTREND is 1 (it is {REQUIRE_MARKET_UPTREND}). While off, "
            "G3 always passes.\n\n"
            "Darvas noticed his boxes failed together in bad markets and stopped buying then. The "
            "benchmark is the market's configured one, read as of the session evaluated."
        ),
        "G4": (
            "The latest published quarter's EPS is up at least {MIN_EPS_GROWTH_PCT}% on the same "
            "quarter a year earlier -- a research switch, OFF unless REQUIRE_EPS_GROWTH is 1 (it is "
            "{REQUIRE_EPS_GROWTH}). While off, G4 always passes.\n\n"
            "- **Latest published:** the newest quarter filed by the session evaluated (one with no "
            "filing date counts from the stored filing lag after its end).\n"
            "- **Growth:** the shared quarterly EPS growth (fundamentals/growth.py), on one share basis.\n"
            "- **Fails:** growth under the minimum, growth not measurable (a loss a year earlier), or "
            "no stored quarter."
        ),
    }
    watch_docs = {}
    setup_docs = {
        DV01: (
            "A complete Darvas box that has not yet broken either way.\n\n"
            "- **Top:** a session whose high is the highest of the {NEW_HIGH_LOOKBACK} sessions ending "
            "on it, and the next {TOP_CONFIRM} sessions' highs are all lower. It is known on the last "
            "of those sessions.\n"
            "- **Bottom:** the lowest low after the top, once {BOTTOM_CONFIRM} sessions in a row have not "
            "gone below it (an equal low holds it). The session that confirms it completes the box.\n"
            "- **Restart:** a high above the top before the bottom is confirmed means no box; the "
            "search starts again, and that session may itself be the next top.\n"
            "- **Live:** from the completing session on, while no high has gone above the top and no low "
            "below the bottom. Each live session is a signal (one order rests at a time).\n\n"
            "Only the latest complete box counts. Detected by core/darvas.py, the same code the "
            "darvas exit trails with."
        ),
    }
    entry_rules = (
        "Signal. Each session the latest box is live (S1), with G1-G4 passing, is TRADE - HIGH "
        "CONFIDENCE: place, or keep, the buy-stop.",
        "Order. A buy-stop at the box top + {ENTRY_BUFFER_PCT}%, rounded up to the market's tick, "
        "resting from the next session.",
        "Fill. On the first session whose high reaches it, at the higher of the order and that "
        "session's open (a gap above the top fills at the open), plus slippage.",
        "Cancel. A session whose low reaches the stop before the high reaches the order cancels it: "
        "the box broke down. The order also lapses after 10 business days unfilled, and is renewed "
        "while the box stays live.",
        "Breakout volume (switch, off). With REQUIRE_BREAKOUT_VOLUME, a fill on a session whose volume "
        "is under {BREAKOUT_VOL_MULT} × its 50-day average sells at the next open. A buy-stop cannot "
        "know the day's volume when it fills, so this is the testable form.",
        "One position per stock, one entry per box. A box that was bought is not bought again.",
    )
    stop_rules = (
        "Where it goes. One market tick below the box bottom, placed with the buy order.",
        "It defines 1R: the distance from the price paid to this stop.",
        "How it sells (backtest). The first session whose low reaches it sells at the stop, or at the "
        "open if it opened below. A gap can lose more than 1R.",
        "It moves only up, by boxes. See Exit.",
    )
    target_rules = (
        "None. The plan's target is entry + {NOMINAL_TARGET_R} × the risk, a nominal number for "
        "the R column; the backtest runs with `--no-target` and never sells there.",
    )
    exit_rules = (
        "Trailing by boxes. After each session the boxes are re-read on the bars up to it. A box "
        "completed that session whose top is above the last box's top -- the bought box at first -- "
        "raises the stop to one tick under its bottom, from the next session. Never lowered. A higher "
        "box of any depth counts.",
        "The stop is the only exit in the original method.",
        "Time stop (switch, off). With TIME_STOP_BARS above 0 (the guide suggests 40), the position "
        "sells at the close of that session after the entry if no higher box has formed by then and "
        "the close is below the entry. It is {TIME_STOP_BARS} (off).",
        "No target, breakeven or partial sale. A position still open when the backtest ends is marked "
        "at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped at "
        "Max position size × equity; when cash cannot buy the full size, it buys what it can.",
        "Slots. At most Position cap positions at once. A triggered order with no free slot keeps "
        "resting until it lapses.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity, "
        "live and in the backtest. No price floor (see Caveats).",
        "Too little history. At least {min_bars} daily bars; a box top also needs {NEW_HIGH_LOOKBACK} "
        "sessions before it.",
        "Market and earnings. Switches G3 and G4, off. Results dates are otherwise ignored.",
        "Already in the stock, or the box already bought. See Entry.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "A live box (S1), all four gates pass, and one share fits the account: "
                                 "place or keep the buy-stop. The only tier the backtest buys.",
        "WATCH_WAIT": "A live box whose plan does not fit even one share in the risk budget and position "
                      "cap, or a HIGH CONFIDENCE lowered by a risk-off market.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number. A stock that passes the "
                 "gates with no live box shows as NO SETUP instead.",
    }
    param_docs = (
        ("New-high lookback", "NEW_HIGH_LOOKBACK", "Sessions whose highest high a box top must equal (itself included)."),
        ("Top confirmation", "TOP_CONFIRM", "Sessions after the top whose highs must all be lower. The guide's range: 2-5."),
        ("Bottom confirmation", "BOTTOM_CONFIRM", "Sessions in a row that must not go below the bottom. Usually equal to the top's."),
        ("Maximum box depth", "MAX_BOX_DEPTH_PCT", "G2: the deepest box bought, % of the top. The guide's range: 10-20."),
        ("Entry buffer", "ENTRY_BUFFER_PCT", "The buy-stop sits this % above the box top."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × risk; only for the R column."),
        ("Breakout volume", "REQUIRE_BREAKOUT_VOLUME", "Switch: 1 = sell a fill at the next open when its session's volume is light."),
        ("Breakout volume multiple", "BREAKOUT_VOL_MULT", "With the switch: the fill session's volume must reach this × its 50-day average."),
        ("Market filter", "REQUIRE_MARKET_UPTREND", "Switch: 1 = G3, the benchmark above its average."),
        ("Market average", "MARKET_SMA", "G3's simple average of the benchmark's closes, in sessions."),
        ("Earnings filter", "REQUIRE_EPS_GROWTH", "Switch: 1 = G4, the latest quarter's EPS growth."),
        ("Minimum EPS growth", "MIN_EPS_GROWTH_PCT", "G4: year-on-year quarterly EPS growth, %."),
        ("Time stop", "TIME_STOP_BARS", "Sessions after the entry for the optional time stop; 0 = off. The guide's: 40."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct", "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "The entry is rounded up to it; the stop sits one tick under the bottom."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--exit-mode darvas --no-target"

    # ---------- the boxes ----------

    _scans: dict = {}

    @classmethod
    def _boxes(cls, symbol: str, d: pd.DataFrame) -> list:
        """Every complete box in `d`, oldest first (core/darvas.scan with this module's constants).

        A backtest evaluates one symbol on a growing slice of the same history, bar after bar, so a
        fresh scan each time would be quadratic. The scan is causal, so a longer history with the same
        prefix continues from where the last one stopped, and a shorter one keeps the boxes that were
        complete within it -- both exactly what a fresh scan returns."""
        h = d["high"].to_numpy(dtype=float)
        lo = d["low"].to_numpy(dtype=float)
        n = len(h)
        hit = cls._scans.get(symbol)
        if hit is not None:
            ch, cl, st = hit
            m = min(len(ch), n)
            if (np.array_equal(ch[:m], h[:m], equal_nan=True)
                    and np.array_equal(cl[:m], lo[:m], equal_nan=True)):
                if len(ch) >= n:
                    return [b for b in st.boxes if b.done_i < n]
                darvas.scan(h, lo, NEW_HIGH_LOOKBACK, TOP_CONFIRM, BOTTOM_CONFIRM, st)
                cls._scans[symbol] = (h, lo, st)
                return list(st.boxes)
        st = darvas.scan(h, lo, NEW_HIGH_LOOKBACK, TOP_CONFIRM, BOTTOM_CONFIRM)
        cls._scans.pop(symbol, None)
        while len(cls._scans) >= _SCAN_CACHE_SIZE:
            cls._scans.pop(next(iter(cls._scans)))
        cls._scans[symbol] = (h, lo, st)
        return list(st.boxes)

    # ---------- the switches' data ----------

    _market: dict = {}

    @classmethod
    def _market_up(cls, market_key: str, day: pd.Timestamp) -> bool:
        """G3: the market's benchmark closed above its MARKET_SMA-day average on `day` (the last close
        on or before it). Cached per market AND stage boundary; a benchmark that is not stored, or too
        short to judge, counts as up."""
        from ..config import MARKETS
        from ..marketdata import asof, cache
        key = (market_key, asof.end_date())
        if key not in cls._market:
            px = cache.load_cached(market_key, MARKETS[market_key].benchmark_ticker)
            if px is None or px.empty:
                cls._market[key] = None
            else:
                c = px["close"].astype(float)
                sma = c.rolling(MARKET_SMA, min_periods=MARKET_SMA).mean()
                cls._market[key] = (c > sma).where(sma.notna())
        up = cls._market[key]
        if up is None:
            return True
        up = up[up.index <= day].dropna()
        return bool(up.iloc[-1]) if len(up) else True

    _quarters: dict = {}

    @classmethod
    def _latest_quarter(cls, symbol: str, day: pd.Timestamp) -> dict | None:
        """G4: the newest quarter published by `day`, with its year-on-year EPS growth -- or None.
        Read through the shared measures, as earnings_gaps' `_announced_quarter` does:
        marketdata.financials.load (cut at the stage boundary) and fundamentals.growth.growth_series
        (one row per stored quarter, in the same order). Published = filed, or FILING_LAG_DAYS after
        the quarter ended when no filing date is stored. Cached per market AND stage boundary."""
        from ..marketdata import asof, financials
        from fundamentals import growth
        market = _market_of(symbol)
        key = (market, asof.end_date())
        if key not in cls._quarters:
            cls._quarters[key] = {"rows": financials.load(market), "series": {}}
        c = cls._quarters[key]
        if symbol not in c["series"]:
            rows = c["rows"].get(symbol) or []
            series = growth.growth_series(rows) if rows else []
            known = [r.get("filed") or (r["period_end"] + dt.timedelta(days=financials.FILING_LAG_DAYS))
                     for r in rows]
            c["series"][symbol] = list(zip(known, series))
        today = day.date()
        q = [s for k, s in c["series"][symbol] if pd.Timestamp(k).date() <= today]
        return q[-1] if q else None

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        return tradable_point_in_time(cfg, last)

    # ---------- gates and setup ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        e = ctx.extras
        self.apply_screen(ctx, result)   # G1, the Near-highs screen's H3

        found = self._boxes(ctx.symbol, d)
        box = found[-1] if found else None
        live = False
        if box is not None:
            after = slice(box.done_i + 1, len(d))
            hi_after = d["high"].iloc[after]
            lo_after = d["low"].iloc[after]
            live = bool((hi_after <= box.top).all() and (lo_after >= box.bottom).all())
            day = lambda i: str(d.index[i].date())
            e.update(box_top=box.top, box_bottom=box.bottom, box_depth_pct=round(box.depth_pct, 2),
                     box_top_date=day(box.top_i), box_bottom_date=day(box.bottom_i),
                     box_done_date=day(box.done_i))
        result.setups[DV01] = live

        # G2 -- depth of the latest box
        if box is None:
            result.ok("G2", "no complete box")
        elif box.depth_pct <= MAX_BOX_DEPTH_PCT:
            result.ok("G2", f"box {box.depth_pct:.1f}% deep")
        else:
            result.fail("G2", f"box {box.depth_pct:.1f}% deep (over {MAX_BOX_DEPTH_PCT:g}%)")

        # G3 -- the market (off unless REQUIRE_MARKET_UPTREND)
        if not REQUIRE_MARKET_UPTREND:
            result.ok("G3", "off")
        elif self._market_up(_market_of(ctx.symbol), d.index[-1]):
            result.ok("G3")
        else:
            result.fail("G3", f"the benchmark is not above its {MARKET_SMA}-day average")

        # G4 -- Darvas's earnings rule (off unless REQUIRE_EPS_GROWTH)
        if not REQUIRE_EPS_GROWTH:
            result.ok("G4", "off")
        else:
            q = self._latest_quarter(ctx.symbol, d.index[-1])
            g = q.get("eps_g") if q else None
            if q is None:
                result.fail("G4", "no published quarter stored")
            elif g is None:
                result.fail("G4", f"EPS growth not measurable for the quarter ended {q['end']}")
            elif g * 100 >= MIN_EPS_GROWTH_PCT:
                result.ok("G4", f"quarter ended {q['end']}: EPS {g * 100:+.0f}%")
            else:
                result.fail("G4", f"quarter ended {q['end']}: EPS {g * 100:+.0f}%, under {MIN_EPS_GROWTH_PCT:g}%")

        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.setups.get(DV01) else 0.0

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """The order is placed as soon as the box is complete: a live box IS the signal to rest the
        buy-stop (the breakout itself is the fill, which the simulator decides)."""
        return bool(result.setups.get(DV01))

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no live box")
        e = ctx.extras
        top, bottom = e.get("box_top"), e.get("box_bottom")
        if top is None or bottom is None:
            return PlanChoice(None, None, "missing box")
        entry = buy_above(float(top), cfg.tick_size)
        stop = stop_below(float(bottom), cfg.tick_size)
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(
            plan="DV", setup=DV01, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R if risk > 0 else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"Darvas box {float(top):.2f} / {float(bottom):.2f}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """The box, for the darvas exit (its top is the first one a trailing box must beat) and for
        one entry per box (`base_id`: the top's date)."""
        e = ctx.extras
        meta = {"box_top": float(e["box_top"]), "box_bottom": float(e["box_bottom"]),
                "base_id": f"darvas:{e['box_top_date']}", "setup_start": e["box_top_date"]}
        if REQUIRE_BREAKOUT_VOLUME:
            meta["min_breakout_vol"] = BREAKOUT_VOL_MULT
        return meta

    # ---------- decision ----------

    def classify(self, ctx: StockContext, result: StrategyResult, plan: TradePlan, sizing_result,
                 earnings_days_away: int | None, regime_downgrade_active: bool) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID", f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if sizing_result.too_large:
            label, reasons = "WATCH_WAIT", ["too large for account"]
        else:
            label = "TRADE_HIGH_CONFIDENCE"
            reasons = [f"buy-stop {plan.entry:.2f} over the box top, stop {plan.stop:.2f}"]
        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        return {k: ctx.extras.get(k) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The box the signal stood on, from the stored row: its top and bottom, the buy-stop and the stop."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        if not e.get("box_top") or not e.get("box_top_date"):
            return super().chart_anatomy(sig)
        top, bot = float(e["box_top"]), float(e["box_bottom"])
        return [
            {"shape": "box", "from": e["box_top_date"], "to": e.get("box_done_date") or d, "top": top,
             "bottom": bot, "role": "base", "label": f"Darvas box {top:g} / {bot:g} · {e.get('box_depth_pct')}% deep"},
            {"shape": "level", "from": e.get("box_done_date") or d, "to": d, "price": top, "role": "pivot",
             "label": f"box top {top:g} — buy-stop just above"},
            {"shape": "level", "from": e.get("box_done_date") or d, "to": d, "price": bot, "role": "stop",
             "label": f"box bottom {bot:g} — stop one tick under"},
            {"shape": "note", "at": d, "price": top,
             "text": f"Darvas box: top {top:g} on {e['box_top_date']} (a {NEW_HIGH_LOOKBACK}-session high held "
                     f"{TOP_CONFIRM} sessions), bottom {bot:g} on {e.get('box_bottom_date')} (held {BOTTOM_CONFIRM}), "
                     f"complete on {e.get('box_done_date')}."},
        ]
