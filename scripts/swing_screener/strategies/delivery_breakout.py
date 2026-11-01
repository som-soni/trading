"""Delivery-% breakout — buying the break of a day when buyers took shares home.

The source is a trading video (research/video-strategy-notes.md §1): an Indian stock has a session
whose delivery % and volume are both far above its own recent days -- the example went from about
48-50% delivered to 86% -- and the trade buys when that day's high is crossed within five sessions,
stopped under its low, with a target of at least 1.5R (2R ideally) that stays below a nearby
52-week high. Half is booked at the target and the stop goes to breakeven. Risk is at most 2% a
trade, with room for five positions.

Why delivery
------------
An Indian intraday trade squares off and is never delivered, so the delivery % is the share of the
day's volume that changed hands to be held (marketdata/delivery.py, NSE's security-wise delivery
file). A heavy-volume day that is mostly delivered is accumulation by the reading the video
proposes; a heavy-volume day that is mostly intraday is churn. No other strategy here reads it,
and no US equivalent exists, so the strategy is India-only by its data.

What the video did not say, chosen here
---------------------------------------
* "Unusually high" has no threshold. Here: at least {MIN_DELIV_RATIO}x the stock's average delivery
  % over the {DELIV_AVG_SESSIONS} sessions before, and at least {MIN_DELIV_PCT}% outright, on at
  least {MIN_REL_VOLUME}x its 50-day volume -- the example's 86% against ~49% is a 1.75x ratio.
* The direction of the day is not stated. Here the day must close above the previous close: heavy
  delivery on a falling day is as likely to be a holder getting out.
* "Don't buy a gap through it": a fill more than {MAX_CHASE_PCT}% above the trigger is skipped.
* The trend: every strategy draws from a screen, so the loosest one applies (above the 200-day).
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
from ..marketdata import corporate_actions, delivery
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
from .rs_leaders import _market_of
from .trend_pullback import round_tick

# ---- the signal day (G2)
SIGNAL_WINDOW = 5          # sessions, counting the signal session, a signal day keeps offering its setup
DELIV_AVG_SESSIONS = 20    # the stock's own baseline: mean delivery % of this many sessions before the day
DELIV_MIN_HISTORY = 15     # ...of which at least this many must have a stored delivery %
MIN_DELIV_RATIO = 1.5      # the day's delivery % against that baseline
MIN_DELIV_PCT = 50.0       # ...and at least this much of the day's volume delivered
MIN_REL_VOLUME = 2.0       # the day's volume against its 50-day average
MIN_UP_MOVE_PCT = 0.0      # the day closes more than this % above the previous close

# ---- entry and stop (G3)
ENTRY_BUFFER_PCT = 0.1     # the buy-stop sits this far above the signal day's high
MAX_CHASE_PCT = 1.0        # a fill more than this % above the trigger is skipped (no chasing a gap)
ENTRY_EXPIRY_BDAYS = 5     # how long the buy-stop waits before it is cancelled
MAX_STOP_PCT = 8.0         # widest stop, as a share of the trigger
MAX_STOP_ATR = 2.0         # ...or this multiple of the 14-day ATR, whichever binds first

# ---- the target (G4)
TARGET_R = 2.0             # the target: trigger + this x the risk ...
MIN_TARGET_R = 1.5         # ...brought down to the 52-week high when that is nearer, but never under this
HIGH_LOOKBACK = 252        # sessions in "the 52-week high"

DB01 = "S1"   # the break of the signal day's high


class DeliveryBreakoutStrategy(Strategy):
    selection = "time_series"
    family = "delivery_breakout"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-01",
         "First version, from a trading video (research/video-strategy-notes.md): a session delivering "
         "at least {MIN_DELIV_RATIO}x the stock's own {DELIV_AVG_SESSIONS}-session delivery % and at least "
         "{MIN_DELIV_PCT}%, on {MIN_REL_VOLUME}x its 50-day volume and an up close; bought on a break of "
         "that day's high within {ENTRY_EXPIRY_BDAYS} sessions, stopped under its low; a {TARGET_R}R "
         "target cut to the 52-week high when nearer but never under {MIN_TARGET_R}R; half sold at the "
         "target, stop to breakeven. The video gave no thresholds -- every number here is a choice."),
    )
    key = "delivery_breakout"
    name = "Delivery-% breakout"
    description = (
        "Buy the break of a session when an Indian stock's delivery % and volume jumped far above its "
        "own recent days, stopped under that day's low, with a 1.5–2R target."
    )
    style = "event"
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    gate_codes = ("G1", "G2", "G3", "G4")
    watch_codes = ()
    setup_codes = (DB01,)
    setup_names = {DB01: "Delivery-day breakout"}
    gate_titles = {"G1": "Above the 200-day", "G2": "A high-delivery day",
                   "G3": "Stop close enough to carry", "G4": "Room to the target"}
    min_bars = 260
    needs_ctx_extras = True
    # Read after the scan, never by evaluate(): the order's expiry and its chase cap (signal_meta).
    signal_exempt_consts = ("ENTRY_EXPIRY_BDAYS", "MAX_CHASE_PCT")
    extra_columns = ("signal_date", "signal_high", "signal_low", "signal_deliv_pct",
                     "signal_deliv_ratio", "signal_rel_volume", "high_52w")
    extra_numeric_columns = ("signal_high", "signal_low", "signal_deliv_pct",
                             "signal_deliv_ratio", "signal_rel_volume", "high_52w")
    backtest_args = ("--exit-mode bracket --partial-at-target 0.5 --breakeven-r 1.5 --risk-pct 0.02 "
                     "--max-positions 5 --accept-labels 'TRADE ON TRIGGER'")

    thesis = (
        "In India an intraday trade is squared off and never delivered, so the share of a day's volume "
        "taken into delivery is the share bought to be held. A session where that share jumps to "
        "{MIN_DELIV_RATIO} times the stock's normal, on {MIN_REL_VOLUME} times its normal volume and a "
        "rising close, says someone accumulated rather than traded. If that buyer is not finished, the "
        "stock should clear the day's high soon, and a buyer who defended the day should not let it "
        "fall back under its low. The claim is a trading video's, untested; this strategy is the test."
    )
    how_it_works = (
        "The idea. A stock has a session with far more of its volume delivered than usual, on heavy "
        "volume, closing up. A buy-stop waits above that day's high for {ENTRY_EXPIRY_BDAYS} sessions; "
        "the stop is the day's low. The rules are a testable form of a trading video's method; the "
        "video gave no numbers, so the thresholds are this strategy's choices (see Known caveats).",
        "Step 1 — the delivery day (G2). One of the last {SIGNAL_WINDOW} sessions delivered at least "
        "{MIN_DELIV_RATIO} times its own {DELIV_AVG_SESSIONS}-session average and at least "
        "{MIN_DELIV_PCT}%, on at least {MIN_REL_VOLUME} times its 50-day volume, closing up.",
        "Step 2 — the stop (G3). The day's low must be no more than {MAX_STOP_PCT}% or {MAX_STOP_ATR} ATR "
        "below the trigger.",
        "Step 3 — the target (G4). {TARGET_R}R above the trigger, brought down to the 52-week high when "
        "that is nearer; a target that would then be under {MIN_TARGET_R}R refuses the trade.",
        "Step 4 — the exit. Half is sold at the target. The stop goes to breakeven once the price has "
        "reached 1.5R, and after the half is sold the rest trails 3 ATR under its highest close.",
        "Timing. Every check is made on a session's close. The order can fill from the next session "
        "on, during the day; the stop and the target act during the day.",
    )
    caveats = (
        "India only. Delivery data is NSE's; a US run finds no stock with any and trades nothing.",
        "Every threshold is a choice. The video showed one example (about 49% delivered rising to 86%) "
        "and said only 'unusually high'. {MIN_DELIV_RATIO}x, {MIN_DELIV_PCT}%, {MIN_REL_VOLUME}x volume "
        "and the up close were picked before any backtest, so the first optimise run is the test of the "
        "idea, not of tuned values.",
        "Delivery % is gross, at client level, as NSE reports it. Block and bulk deals deliver by "
        "nature, so a single large negotiated trade can make a delivery day without any broad buying.",
        "A delivery % is only read where one is stored. The days NSE published no file (rare) leave a "
        "gap, and a baseline with fewer than {DELIV_MIN_HISTORY} stored sessions out of "
        "{DELIV_AVG_SESSIONS} is not judged.",
        "Breakeven is not tied to the target. The video moves the stop to breakeven when half is booked "
        "at the target; the shared exit engine raises it at a fixed 1.5R, which is at or before every "
        "target here (G4's floor is {MIN_TARGET_R}R). The remainder after the half then trails 3 ATR "
        "under its highest close -- the video named no rule for it.",
        "Live, a delivery day is seen the evening NSE publishes its file. If the screen runs before "
        "the `delivery` job, the day is picked up the next session, still inside the "
        "{SIGNAL_WINDOW}-session window.",
        "The 52-week high is the highest high of the last {HIGH_LOOKBACK} sessions, including the "
        "signal day. A stock already at a new high has no cap and takes the full {TARGET_R}R.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "NO EDGE AS STATED. In-sample (optimise, 2013-2021) at v1.0, India: 106 trades from 666 signals "
        "across 451 eligible stocks, -0.28% CAGR at 37% exposure, max drawdown -14.8%, win rate 36%, "
        "-0.02R a trade, profit factor 0.95. The index held at the same exposure made 1.9% a year. 63 "
        "trades hit the first stop (-0.99R on average), 25 the breakeven stop (+0.61R, the half sold at "
        "target) and 18 trailed out (+2.50R). Most bars stop at G2 or G1; 84 orders were skipped for "
        "gapping more than {MAX_CHASE_PCT}% through the trigger. The thresholds were fixed before this "
        "run, from the video, and have not been tuned."
    )
    gate_docs = {
        "G1": "The close is above the 200-day moving average (the Above-the-200-day screen's A1).\n\n"
              "- **Test:** the signal session's close is strictly above the 200-day simple average "
              "of closes.\n"
              "- **Why:** every strategy draws from a screen; the video set no trend rule, so the "
              "loosest one applies.",
        "G2": "A high-delivery day in the last {SIGNAL_WINDOW} sessions.\n\n"
              "- **Window:** the signal session and the sessions just before it, {SIGNAL_WINDOW} in "
              "all. If several qualify, the most recent is used.\n"
              "- **Delivery ratio:** the day's delivery % is at least {MIN_DELIV_RATIO} times the mean "
              "delivery % of the {DELIV_AVG_SESSIONS} sessions before it (the day itself is not in the "
              "mean). At least {DELIV_MIN_HISTORY} of them must have a stored value.\n"
              "- **Delivery floor:** the day's delivery % is at least {MIN_DELIV_PCT}%.\n"
              "- **Volume:** the day's volume is at least {MIN_REL_VOLUME} times its 50-day average "
              "(the 50 sessions ending on that day).\n"
              "- **Direction:** the day closes more than {MIN_UP_MOVE_PCT}% above the previous close.",
        "G3": "The signal day's low is a stop the trade can carry: no more than {MAX_STOP_PCT}% and no "
              "more than {MAX_STOP_ATR} ATR below the trigger.\n\n"
              "- **Distance:** the trigger (the signal high + {ENTRY_BUFFER_PCT}%) minus the signal low.\n"
              "- **ATR:** the signal session's 14-day ATR.\n"
              "- **At the fill:** the percent cap is tested again on the price actually paid.",
        "G4": "There is room to the target.\n\n"
              "- **Target:** the trigger + {TARGET_R} × the risk, or the 52-week high (the highest high "
              "of the last {HIGH_LOOKBACK} sessions) when that is above the trigger and nearer.\n"
              "- **Test:** the target is at least {MIN_TARGET_R} × the risk above the trigger. A stock "
              "just under a 52-week high it would hit first is refused.",
    }
    watch_docs = {}
    setup_docs = {
        DB01: "Delivery-day breakout: every gate passes, so a buy-stop waits just above the signal "
              "day's high.\n\n"
              "- **Trigger:** the signal high + {ENTRY_BUFFER_PCT}%, rounded up to the tick.\n"
              "- **Stop:** the signal low, rounded down to the tick.\n"
              "- **Present when:** G1 to G4 all pass on the signal session.",
    }
    entry_rules = (
        "The signal. Any session on which G1 to G4 pass places a buy-stop at the signal high + "
        "{ENTRY_BUFFER_PCT}% (rounded up to the tick), live from the next session. Nothing is bought "
        "at the signal close.",
        "How it fills. On the first session whose high reaches the trigger, at the trigger, or at the "
        "open if the stock opens above it -- unless that open is more than {MAX_CHASE_PCT}% above the "
        "trigger, when the order is skipped: the video's rule is not to buy a gap through the high. "
        "The market's per-side slippage is added.",
        "How long it waits. Until the {ENTRY_EXPIRY_BDAYS}th weekday after the signal day, then it is "
        "cancelled. It is cancelled sooner if a session trades down to the stop without reaching the "
        "trigger.",
        "Skipped at the fill. The stop must be no more than {MAX_STOP_PCT}% below the price paid.",
        "One buy per signal day; one order per stock. A stock already held, or with an order waiting, "
        "ignores a new signal.",
    )
    stop_rules = (
        "Where it goes. The signal day's low, rounded down to the tick. A stock that loses the whole "
        "delivery day has rejected it.",
        "It defines the risk. The distance from the price paid to the stop is 1R.",
        "How it sells. During the first session whose low reaches it, at the stop, or at the open if "
        "the stock opens below it -- a gap can lose more than 1R.",
        "Breakeven. Once a session's high reaches 1.5R above the price paid, from the next session the "
        "stop is the entry plus round-trip costs.",
        "After the half is sold. The rest trails 3 × the 14-day ATR under its highest close, never "
        "lower than the breakeven stop.",
    )
    target_rules = (
        "Where it goes. The trigger + {TARGET_R} × the risk, brought down to the 52-week high when that "
        "is above the trigger and nearer. G4 refuses a target under {MIN_TARGET_R}R.",
        "What it does. A sell order for half the position, during the session that reaches it (at the "
        "open if the stock gaps above it). The other half has no target.",
    )
    exit_rules = (
        "Each session the stop is checked first, then the target (see Stop and Target).",
        "Nothing else sells: no time stop and no trend exit. A position still open when the backtest "
        "ends is valued at the last close.",
    )
    sizing_rules = (
        "Risk per trade. Shares = equity × 2% ÷ (price paid − stop) -- the video's cap, set by the "
        "backtest command (--risk-pct 0.02) rather than the market's default.",
        "Positions at once. At most 5 (--max-positions 5), the video's number.",
        "Caps. No position may be worth more than the market's largest-position share of equity (see "
        "Parameters). If cash is short, fewer shares are bought.",
        "Same-day ties. Every signal scores the same; the order placed first is filled first.",
        "Costs. The market's per-side slippage is inside every fill price.",
    )
    filter_rules = (
        "Too thin. The 20-day average traded value must reach the market's liquidity floor (see "
        "Parameters), and a 14-day ATR must exist.",
        "No delivery data. A market with no delivery file is refused before any gate.",
        "Too little history. At least {min_bars} daily bars.",
        "Market regime. The backtest command adds no market filter. Live, a risk-off market lowers "
        "TRADE ON TRIGGER to WATCH (see Decisions).",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Never reached: the entry is always a resting buy-stop.",
        "TRADE_ON_TRIGGER": "G1 to G4 pass and the plan is valid: place the buy-stop {ENTRY_BUFFER_PCT}% "
                            "above the signal high. The backtest command takes these.",
        "WATCH_WAIT": "The plan is valid but not one share fits the risk budget or the position cap, or "
                      "a risk-off market lowered TRADE ON TRIGGER to this tier.",
        "AVOID": "A gate failed (the reason names the first), or the plan is degenerate, or a risk-off "
                 "market lowered WATCH to this tier.",
    }
    regime_note = ("When the market regime is risk-off, the live decision drops one tier: TRADE ON "
                   "TRIGGER becomes WATCH and WATCH becomes AVOID. A backtest never applies it.")
    param_docs = (
        ("Signal window", "SIGNAL_WINDOW", "G2: sessions, counting the signal session, in which a delivery day still offers its setup."),
        ("Delivery baseline", "DELIV_AVG_SESSIONS", "G2: sessions before the day whose mean delivery % is the stock's normal."),
        ("Baseline coverage", "DELIV_MIN_HISTORY", "G2: stored sessions the baseline needs to be judged."),
        ("Delivery ratio", "MIN_DELIV_RATIO", "G2: the day's delivery % ÷ the baseline."),
        ("Delivery floor", "MIN_DELIV_PCT", "G2: the day's delivery %, at least."),
        ("Relative volume", "MIN_REL_VOLUME", "G2: the day's volume ÷ its 50-day average."),
        ("Up close", "MIN_UP_MOVE_PCT", "G2: close-to-close rise, in %, the day must exceed."),
        ("Entry buffer", "ENTRY_BUFFER_PCT", "How far above the signal high, in %, the buy-stop sits."),
        ("Chase cap", "MAX_CHASE_PCT", "A fill more than this % above the trigger is skipped."),
        ("Entry window", "ENTRY_EXPIRY_BDAYS", "Weekdays after the signal day before an unfilled buy-stop is cancelled."),
        ("Maximum stop", "MAX_STOP_PCT", "G3 and at the fill: widest stop, in % below the trigger or the price paid."),
        ("Maximum stop (ATR)", "MAX_STOP_ATR", "G3: widest stop as a multiple of the 14-day ATR."),
        ("Target", "TARGET_R", "G4: the target in R above the trigger, before the 52-week-high cap."),
        ("Minimum target", "MIN_TARGET_R", "G4: the smallest target, in R, the cap may leave."),
        ("52-week lookback", "HIGH_LOOKBACK", "G4: sessions in the 52-week high."),
        ("Largest position", "cfg.max_position_pct", "Largest position as a share of equity."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "20-day average traded value, in the market's currency."),
    )

    # ---------- delivery data ----------

    _deliv: dict = {}

    @classmethod
    def _delivery(cls, symbol: str) -> pd.Series | None:
        """The stock's stored delivery % by date, or None. Cached per market AND stage boundary (the
        loader honours it, so an optimise run's rows never reach a full run in the same process), and
        per symbol: one query per stock, not per bar."""
        from ..marketdata import asof
        key = (_market_of(symbol), asof.end_date())
        per = cls._deliv.setdefault(key, {})
        if symbol not in per:
            try:
                df = delivery.load(key[0], [symbol])
            except Exception:   # noqa: BLE001 -- no table is "no delivery data", not a crash
                df = pd.DataFrame()
            per[symbol] = (None if df.empty else
                           df.set_index("date")["deliv_pct"].astype(float).sort_index())
        return per[symbol]

    # ---------- screening ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        if not delivery.covers(cfg):
            return False, "no delivery data in this market"
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    def _signal_day(self, d: pd.DataFrame, deliv: pd.Series) -> dict | None:
        """The most recent qualifying delivery day within the window, or None (newest wins: a second
        delivery day is a new event with a new high and a new stop)."""
        n = len(d)
        dates = deliv.index
        for i in range(n - 1, max(1, n - SIGNAL_WINDOW) - 1, -1):
            day = d.index[i]
            j = dates.searchsorted(day)
            if j >= len(dates) or dates[j] != day:
                continue
            pct = float(deliv.iloc[j])
            before = deliv.iloc[max(0, j - DELIV_AVG_SESSIONS):j].dropna()
            # the baseline is the stock's own previous sessions, so it must not reach back past them
            before = before[before.index >= d.index[max(0, i - DELIV_AVG_SESSIONS)]]
            if len(before) < DELIV_MIN_HISTORY or pct < MIN_DELIV_PCT:
                continue
            base = float(before.mean())
            ratio = pct / base if base > 0 else float("inf")
            if ratio < MIN_DELIV_RATIO:
                continue
            c, prev_c = float(d["close"].iloc[i]), float(d["close"].iloc[i - 1])
            if not prev_c or (c / prev_c - 1) * 100 <= MIN_UP_MOVE_PCT:
                continue
            v50 = d["vol_sma50"].iloc[i]
            if pd.isna(v50) or not v50:
                continue
            rel_vol = float(d["volume"].iloc[i]) / float(v50)
            if rel_vol < MIN_REL_VOLUME:
                continue
            return {"i": i, "date": day, "high": float(d["high"].iloc[i]), "low": float(d["low"].iloc[i]),
                    "deliv_pct": pct, "ratio": ratio, "rel_volume": rel_vol}
        return None

    @staticmethod
    def _target(entry: float, risk: float, high_52w: float) -> float:
        full = entry + TARGET_R * risk
        return min(full, high_52w) if high_52w > entry else full

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        e = ctx.extras
        self.apply_screen(ctx, result)   # G1

        deliv = self._delivery(ctx.symbol)
        r = self._signal_day(d, deliv) if deliv is not None else None
        if r is None:
            result.fail("G2", ("no delivery data stored" if deliv is None else
                               f"no high-delivery day in the last {SIGNAL_WINDOW} sessions"))
            result.ok("G3", "not reached")
            result.ok("G4", "not reached")
            result.recompute_first_fail()
            return result

        result.ok("G2", f"{r['deliv_pct']:.0f}% delivered ({r['ratio']:.1f}x its normal) on "
                        f"{r['rel_volume']:.1f}x volume")
        e["signal_date"] = str(r["date"].date())
        e["signal_high"] = r["high"]
        e["signal_low"] = r["low"]
        e["signal_deliv_pct"] = round(r["deliv_pct"], 2)
        e["signal_deliv_ratio"] = round(r["ratio"], 2)
        e["signal_rel_volume"] = round(r["rel_volume"], 2)

        # G3 -- is the signal low a stop we can carry?
        entry = r["high"] * (1 + ENTRY_BUFFER_PCT / 100)
        risk = entry - r["low"]
        atr14 = ctx.atr
        risk_pct = risk / entry * 100 if entry else float("inf")
        atr_mult = risk / atr14 if atr14 and atr14 == atr14 else float("inf")
        if risk <= 0:
            result.fail("G3", "the signal day's low is not below the trigger")
        elif risk_pct > MAX_STOP_PCT:
            result.fail("G3", f"stop is {risk_pct:.1f}% below the entry (over {MAX_STOP_PCT:g}%)")
        elif atr_mult > MAX_STOP_ATR:
            result.fail("G3", f"stop is {atr_mult:.1f} ATR below the entry (over {MAX_STOP_ATR:g})")
        else:
            result.ok("G3")

        # G4 -- room to the target under the 52-week high
        hi52 = float(d["high"].iloc[-HIGH_LOOKBACK:].max())
        e["high_52w"] = hi52
        if risk > 0:
            room = (self._target(entry, risk, hi52) - entry) / risk
            if room < MIN_TARGET_R:
                result.fail("G4", f"the 52-week high {hi52:.2f} is only {room:.1f}R above the trigger "
                                  f"(under {MIN_TARGET_R:g}R)")
            else:
                result.ok("G4", f"target {room:.1f}R")
        else:
            result.ok("G4", "not reached")

        result.setups[DB01] = bool(result.hard_gates_passed)
        result.recompute_first_fail()
        return result

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """The order is the signal: a resting buy-stop above the signal high."""
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        return 1.0 if result.has_setup else 0.0

    def build_plans(self, ctx: StockContext, result: StrategyResult,
                    cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        hi, lo = e.get("signal_high"), e.get("signal_low")
        if hi is None or lo is None:
            return PlanChoice(None, None, "missing signal day")
        entry = round_tick(float(hi) * (1 + ENTRY_BUFFER_PCT / 100), cfg.tick_size, "up")
        stop = round_tick(float(lo), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        target = round_tick(self._target(entry, risk, float(e.get("high_52w") or 0.0)), cfg.tick_size, "down")
        if target <= entry:
            return PlanChoice(None, None, "no room to a target")
        plan = TradePlan(
            plan="DB", setup=DB01, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=(target - entry) / risk, nearest_overhead_above_entry=e.get("high_52w"),
        )
        return PlanChoice(plan, None, f"buy-stop above the {e['signal_date']} delivery-day high")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """A resting buy-stop, one per signal day, cancelled after {ENTRY_EXPIRY_BDAYS} sessions and
        skipped when the stock gaps more than {MAX_CHASE_PCT}% through the trigger."""
        return {
            "order": "stop",
            "base_id": ctx.extras.get("signal_date"),
            "max_fill": plan.entry * (1 + MAX_CHASE_PCT / 100),
            "max_risk_pct": MAX_STOP_PCT / 100,
            "expiry_bdays": ENTRY_EXPIRY_BDAYS,
        }

    # ---------- decision ----------

    def classify(self, ctx: StockContext, result: StrategyResult, plan: TradePlan,
                 sizing_result, earnings_days_away: int | None,
                 regime_downgrade_active: bool) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID",
                            f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if sizing_result.too_large:
            label, reasons = "WATCH_WAIT", ["too large for account"]
        else:
            label = "TRADE_ON_TRIGGER"
            reasons = [f"buy-stop above the {ctx.extras.get('signal_date')} delivery-day high"]
        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult,
                      plan: TradePlan | None) -> dict:
        e = ctx.extras
        return {k: (round(e[k], 2) if isinstance(e.get(k), float) else e.get(k))
                for k in self.extra_columns}
