"""Earnings gaps and episodic pivots — buying the big results-day gap.

The Learn guide `research/learn-strat-earnings-gaps.md` is the specification; this is its
testable form. A stock reports, jumps a long way on enormous volume and closes near the day's
high. The trade buys a break of that reaction day's high, stops under its low, and trails the
rest out on the 20-day average. Pradeep Bonde calls it the episodic pivot — an episode of news
that pivots a stock from one price level to another; Kristjan Kullamägi trades the same shape
intraday.

Why it is worth testing beside the rest of the shelf
----------------------------------------------------
Every other per-symbol strategy here keys on chart STRUCTURE — a base, a channel, a pullback —
and that family has not picked better than the index held at the same exposure in any of the
eight runs on the 2013 cohort (`research/selection-vs-drag.md` §7). This one keys on an EVENT
instead. It is the only remaining strategy in the Learn list that does, which is the whole
reason to build it: it tests a different claim, not a tenth variation of the failing one.

Locating the news without a calendar
------------------------------------
The guide asks for "results announced in the window from 3 days before this session to this
session", and warns that without that link "you buy random spikes". No announcement calendar is
stored before 2025-10, so the link is made the other way round: a reaction day must fall inside
a window bracketed by data that IS recorded — at least {CATALYST_MIN_DAYS} days after a stored
quarter end, and no later than {CATALYST_FILED_GRACE} days after that quarter's filing. A
company announces after the quarter closes and files at or after it announces, so the true
announcement always lies inside that bracket. It is looser than a calendar — roughly a third of
the quarter rather than four days — but it is made of recorded facts rather than inferred ones,
which is the lesson of the blackout work in `backtesting/spec.py`: an inferred announcement date
carries a median error of 13 days and is not worth keying a rule on.

Honest limits
-------------
* The bracket admits a non-results spike that happens to land in the window. It narrows the
  false positives, it does not eliminate them.
* The guide's optional year-on-year profit filter is NOT implemented: it needs point-in-time
  fundamentals on the reaction day, which this path does not carry. Its neglect filter IS, as a
  watch flag, because the guide marks it optional and untested.
* The guide's partial sale after 3-5 sessions and its 10-session time stop are not modelled —
  the shared exit engine's trailing-average mode carries the initial stop and the trail, and
  nothing else. So this measures the stop-and-trail core of the method, not Kullamägi's
  management of it.
* India releases results mid-session as often as overnight, so the open-gap test fires less
  there; the close-to-close move is the test that travels, which is why either one qualifies.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core.context import StockContext
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
# Reused rather than copied: the suffix-driven market lookup and the tick rounding already exist,
# and a second copy of either is the duplication CLAUDE.md warns about.
from .rs_leaders import _market_of
from .trend_pullback import round_tick

# ---- the reaction day (guide §3, "Setup")
MIN_MOVE_PCT = 10.0        # close at least this far above the previous close
MIN_GAP_PCT = 5.0          # ...or the open at least this far above it
MIN_REL_VOLUME = 3.0       # volume against its 50-day average
MIN_CLOSE_POS = 0.70       # (close - low) / (high - low): closed in the top of its range
NEGLECT_LOOKBACK = 60      # sessions over which "already extended" is measured
NEGLECT_MAX_RUN_PCT = 30.0 # a stock up more than this into the news is noted, not refused

# ---- the catalyst bracket (see the module docstring)
CATALYST_MIN_DAYS = 10     # a reaction day sits at least this far after the quarter end
CATALYST_FILED_GRACE = 5   # ...and no later than this many days after that quarter's filing

# ---- entry and risk (guide §3, "Entry" / "Initial stop")
ENTRY_BUFFER_PCT = 0.1     # the buy-stop sits this far above the reaction day's high
ENTRY_EXPIRY_BDAYS = 5     # how long the buy-stop waits before it is cancelled
REACTION_WINDOW = 5        # sessions a reaction day keeps offering its setup
MAX_STOP_PCT = 12.0        # widest stop, as a share of the entry
MAX_STOP_ATR = 1.5         # ...or this multiple of the 14-day ATR, whichever binds first
NOMINAL_TARGET_R = 3.0     # for sizing and reporting only — the real exit is the trail

EG01 = "S1"   # EG-01: the break of the reaction day's high


class EarningsGapStrategy(Strategy):
    selection = "time_series"
    family = "earnings_gaps"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-22",
         "First version, from the Learn guide: a results-day reaction of at least "
         "{MIN_MOVE_PCT}% close-to-close or a {MIN_GAP_PCT}% opening gap, on at least "
         "{MIN_REL_VOLUME}x its 50-day volume, closing in the top {MIN_CLOSE_POS} of its range "
         "and bracketed to a stored results window; bought on a break of that day's high with "
         "the stop under its low. Built as the one EVENT-driven per-symbol strategy on the "
         "shelf, because the structure-driven family has no positive selection on the 2013 "
         "cohort. The guide's year-on-year growth filter and its partial sale and time stop are "
         "not implemented -- see the module docstring."),
    )
    key = "earnings_gaps"
    name = "Earnings gaps"
    description = (
        "Buy the stock that jumps on its results — a large move on enormous volume, closing "
        "near the high — on a break of that day's high, stopped under its low."
    )
    style = "event"
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    gate_codes = ("G1", "G2", "G3", "G4")
    watch_codes = ("W1", "W2")
    setup_codes = (EG01,)
    setup_names = {EG01: "Results-gap breakout"}
    gate_titles = {"G1": "Above the 200-day", "G2": "A results-day reaction",
                   "G3": "Linked to a results window", "G4": "Stop close enough to carry"}
    nominal_target = True
    min_bars = 260
    needs_ctx_extras = True
    extra_columns = ("reaction_date", "reaction_high", "reaction_low", "reaction_move_pct",
                     "reaction_rel_volume", "reaction_close_pos")
    extra_numeric_columns = ("reaction_high", "reaction_low", "reaction_move_pct",
                             "reaction_rel_volume", "reaction_close_pos")
    backtest_start = "2020-01-01"
    backtest_args = "--exit-mode ma --no-target --ma-col sma20"

    thesis = (
        "A large surprise changes what a business is worth, but investors do not all act on the "
        "same day: funds need meetings, analysts rebuild models over weeks, and some buyers wait "
        "for the next quarter to confirm the change. That slow adjustment is the same "
        "under-reaction that post-earnings drift trades, taken at its sharpest point. The volume "
        "is what separates the two cases — a jump on ordinary turnover is a few traders chasing a "
        "headline, while a jump on {MIN_REL_VOLUME}x normal means large holders were active, and "
        "if they are still buying they will keep buying for weeks."
    )
    how_it_works = (
        "Each session the strategy looks back {REACTION_WINDOW} sessions for a results-day "
        "reaction: a close at least {MIN_MOVE_PCT}% above the previous close, or an open at "
        "least {MIN_GAP_PCT}% above it, on at least {MIN_REL_VOLUME} times the 50-day average "
        "volume, closing in the top {MIN_CLOSE_POS} of the day's range.",
        "That day must be linked to results. No announcement calendar is stored this far back, "
        "so the link is made from the two dates that ARE recorded: the reaction must fall at "
        "least {CATALYST_MIN_DAYS} days after a stored quarter end and no more than "
        "{CATALYST_FILED_GRACE} days after that quarter's filing. A company announces after its "
        "quarter closes and files at or after it announces, so the announcement always lies "
        "inside that bracket.",
        "The order is a buy-stop {ENTRY_BUFFER_PCT}% above the reaction day's high, resting for "
        "{ENTRY_EXPIRY_BDAYS} sessions. A stock that opens above the trigger is filled at the "
        "open, at a worse price, as the guide asks.",
        "The stop is the reaction day's low. If that is more than {MAX_STOP_PCT}% below the "
        "entry or more than {MAX_STOP_ATR} times the 14-day ATR, the trade is refused rather "
        "than taken with a stop too wide to size.",
        "One entry per event: once an order has been placed against a reaction day, that day "
        "never offers another.",
    )
    caveats = (
        "Only a stock with stored quarterly results can ever trade: with nothing to link a move "
        "to, G3 refuses it. That is the guide's own requirement -- without the link you are "
        "buying random spikes -- but it shrinks the universe hard, to the 2,002 US and 579 "
        "Indian symbols the results table covers. Measured over an alphabetical sample of 300 "
        "symbols a side, 113 US and 50 Indian ones were covered; among those, the bracket linked "
        "65% of US reaction days and 32% of Indian ones, the rest being moves on news that was "
        "not results.",
        "The results link is only as good as the stored quarters, and India's start in March "
        "2020 and are thin until 2022 (15 filed rows for 2020, about a thousand for 2021, "
        "against six to seven thousand a year for the US throughout). So G3 refuses most early "
        "Indian reactions for want of a quarter to link them to, and the Indian arm is in "
        "practice a 2022-onward test with a smaller universe. The US arm is the one with full "
        "coverage over the window.",
        "The results link is a bracket, not a calendar. It spans roughly a third of a quarter, "
        "so a non-results spike landing inside it is admitted. It narrows the false positives "
        "rather than removing them.",
        "The guide's optional year-on-year profit-growth filter is not implemented: it needs "
        "point-in-time fundamentals on the reaction day, which this path does not carry. Results "
        "here are therefore the unfiltered version of the setup, which the guide expects to be "
        "the weaker one.",
        "The guide's partial sale after 3-5 sessions and its 10-session time stop are not "
        "modelled. The shared exit engine carries the initial stop and the trailing average and "
        "nothing else, so this measures the core of the method rather than its management.",
        "The strategy has no profit target by construction — the exit is a close below the "
        "20-day average — so the reported reward-to-risk describes a nominal {NOMINAL_TARGET_R}R "
        "used for sizing, not an expectation.",
        "The guide's own event study found results-day jumps did only slightly better than an "
        "average results day in the US since 2009, and clearly better in India since 2020 on a "
        "much smaller sample. Expect a low win rate carried by a few large winners, and judge it "
        "on many trades.",
        "Intraday entry — Kullamägi's break of the opening range on the reaction day itself — "
        "cannot be tested on daily bars. The daily version enters a day later and higher.",
    )
    status = (
        "Not yet measured. Built as the shelf's only event-driven per-symbol strategy, to test "
        "whether keying on news rather than chart structure behaves differently from the "
        "structure family, which has no positive selection number on the 2013 cohort. Read its "
        "first run against the index held at the same exposure, not against its own CAGR: this "
        "strategy sits in cash most of the time, and cash drag and selection move in opposite "
        "directions."
    )
    gate_docs = {
        "G1": "The close is above the 200-day moving average (the Above-the-200-day screen's A1). "
              "The guide does not ask for this -- it filters the MARKET, not the stock, and it likes "
              "turnarounds. It is here because every strategy draws its candidates from a screen and "
              "this is the loosest one, and it is the clearest deviation from the guide in this "
              "implementation: deep-turnaround gaps are excluded.",
        "G2": "A results-day reaction in the last {REACTION_WINDOW} sessions: the close at least "
              "{MIN_MOVE_PCT}% above the previous close OR the open at least {MIN_GAP_PCT}% "
              "above it, volume at least {MIN_REL_VOLUME}x its 50-day average, and the close in "
              "the top {MIN_CLOSE_POS} of the day's range.",
        "G3": "That reaction day is linked to results: at least {CATALYST_MIN_DAYS} days after a "
              "stored quarter end and at most {CATALYST_FILED_GRACE} days after that quarter's "
              "filing. A company with no stored quarters cannot be linked, and is refused.",
        "G4": "The reaction day's low is a usable stop: no more than {MAX_STOP_PCT}% below the "
              "trigger and no more than {MAX_STOP_ATR}x the 14-day ATR.",
    }
    watch_docs = {
        "W1": "Already extended into the news: the close is more than {NEGLECT_MAX_RUN_PCT}% "
              "above its level {NEGLECT_LOOKBACK} sessions ago. Bonde's point is that a stock "
              "that sat flat for a year has few holders ready to sell, while one that already "
              "doubled has many. Noted, not blocking — the guide marks the filter optional and "
              "untested.",
        "W2": "The gap qualified on the opening gap alone, not on the close-to-close move: the "
              "day gave back part of its jump. Noted only.",
    }
    setup_docs = {
        EG01: "The break of the reaction day's high, bought with a resting buy-stop "
              "{ENTRY_BUFFER_PCT}% above it.",
    }
    entry_rules = (
        "A buy-stop {ENTRY_BUFFER_PCT}% above the reaction day's high, resting for "
        "{ENTRY_EXPIRY_BDAYS} sessions and then cancelled.",
        "A stock that opens above the trigger fills at the open, which is worse. The guide asks "
        "for that to be counted rather than assumed away.",
        "Stop: the reaction day's low. Refused if that sits more than {MAX_STOP_PCT}% below the "
        "entry or more than {MAX_STOP_ATR}x the 14-day ATR.",
        "One entry per reaction day, so a single event cannot be traded twice.",
        "Target: none. {NOMINAL_TARGET_R}R is a nominal figure for sizing and reporting only.",
    )
    exit_rules = (
        "The initial stop is the reaction day's low and never moves down.",
        "The rest is sold on the first close below the 20-day average (the guide's trailing "
        "exit; it suggests the 10-day for faster stocks).",
        "The guide's partial sale after 3-5 sessions and its 10-session time stop are NOT "
        "modelled here — see the caveats.",
    )
    param_docs = (
        ("Minimum move", "MIN_MOVE_PCT", "Close-to-close move that makes a session a reaction day."),
        ("Minimum gap", "MIN_GAP_PCT", "Opening gap that qualifies instead, for overnight releases."),
        ("Minimum relative volume", "MIN_REL_VOLUME", "Volume against the 50-day average."),
        ("Minimum close position", "MIN_CLOSE_POS", "Where the reaction day closes in its range."),
        ("Reaction window", "REACTION_WINDOW", "Sessions a reaction day keeps offering its setup."),
        ("Entry buffer", "ENTRY_BUFFER_PCT", "How far above the reaction high the buy-stop sits."),
        ("Entry window", "ENTRY_EXPIRY_BDAYS", "Sessions the buy-stop rests before cancellation."),
        ("Maximum stop", "MAX_STOP_PCT", "Widest stop as a share of the entry."),
        ("Maximum stop (ATR)", "MAX_STOP_ATR", "Widest stop as a multiple of the 14-day ATR."),
        ("Neglect threshold", "NEGLECT_MAX_RUN_PCT", "Rise over {NEGLECT_LOOKBACK} sessions above which W1 is noted."),
        ("Catalyst: earliest", "CATALYST_MIN_DAYS", "Days after a quarter end before a reaction can be linked to it."),
        ("Catalyst: latest", "CATALYST_FILED_GRACE", "Days after that quarter's filing beyond which it cannot."),
        ("Nominal target", "NOMINAL_TARGET_R", "Reward-to-risk used for sizing only; there is no real target."),
    )

    # ---------- the results calendar ----------

    _quarters: dict = {}

    @classmethod
    def _results_windows(cls, market_key: str) -> dict:
        """{symbol: [(earliest, latest), ...]} — the bracket each stored quarter admits.

        Cached on the class: every symbol on every bar asks the same question of the same table,
        and one query per bar would dominate the scan.
        """
        if market_key in cls._quarters:
            return cls._quarters[market_key]
        from ..marketdata import db
        out: dict = {}
        try:
            with db.get_connection().cursor() as cur:
                cur.execute(
                    """SELECT symbol, period_end, filed FROM quarterly_results
                       WHERE market=%s AND period_end IS NOT NULL AND filed IS NOT NULL""",
                    (market_key,))
                for sym, pe, filed in cur.fetchall():
                    lo = pd.Timestamp(pe) + pd.Timedelta(days=CATALYST_MIN_DAYS)
                    hi = pd.Timestamp(filed) + pd.Timedelta(days=CATALYST_FILED_GRACE)
                    if hi >= lo:
                        out.setdefault(sym, []).append((lo, hi))
        except Exception:   # noqa: BLE001 — no results table is "nothing can be linked", not a crash
            out = {}
        cls._quarters[market_key] = out
        return out

    @classmethod
    def _linked_to_results(cls, symbol: str, day: pd.Timestamp) -> bool:
        wins = cls._results_windows(_market_of(symbol)).get(symbol)
        if not wins:
            return False
        return any(lo <= day <= hi for lo, hi in wins)

    # ---------- screening ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- gates ----------

    def _reaction_day(self, d: pd.DataFrame) -> dict | None:
        """The most recent qualifying reaction day within the window, or None.

        Walks backwards so the NEWEST event wins: a second results gap inside five sessions is a
        new event with a new high and a new stop, not a continuation of the first.
        """
        n = len(d)
        first = max(1, n - REACTION_WINDOW)
        for i in range(n - 1, first - 1, -1):
            o, h, l, c = (float(d["open"].iloc[i]), float(d["high"].iloc[i]),
                          float(d["low"].iloc[i]), float(d["close"].iloc[i]))
            prev_c = float(d["close"].iloc[i - 1])
            v50 = d["vol_sma50"].iloc[i]
            if not prev_c or pd.isna(v50) or not v50:
                continue
            move = (c / prev_c - 1) * 100
            gap = (o / prev_c - 1) * 100
            if move < MIN_MOVE_PCT and gap < MIN_GAP_PCT:
                continue
            rel_vol = float(d["volume"].iloc[i]) / float(v50)
            if rel_vol < MIN_REL_VOLUME:
                continue
            rng = h - l
            pos = (c - l) / rng if rng > 0 else 1.0
            if pos < MIN_CLOSE_POS:
                continue
            return {"i": i, "date": d.index[i], "high": h, "low": l,
                    "move_pct": move, "gap_pct": gap, "rel_volume": rel_vol, "close_pos": pos}
        return None

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        e = ctx.extras
        self.apply_screen(ctx, result)   # G1, from the Above-the-200-day screen

        r = self._reaction_day(d)
        if r is None:
            result.fail("G2", f"no results-day reaction in the last {REACTION_WINDOW} sessions")
            result.ok("G3", "not reached")
            result.ok("G4", "not reached")
            result.recompute_first_fail()
            return result

        result.ok("G2", f"{r['move_pct']:+.1f}% on {r['rel_volume']:.1f}x volume, "
                        f"closing at {r['close_pos'] * 100:.0f}% of range")
        e["reaction_date"] = str(r["date"].date())
        e["reaction_high"] = r["high"]
        e["reaction_low"] = r["low"]
        e["reaction_move_pct"] = round(r["move_pct"], 2)
        e["reaction_rel_volume"] = round(r["rel_volume"], 2)
        e["reaction_close_pos"] = round(r["close_pos"], 3)

        # G3 — the news link
        if self._linked_to_results(ctx.symbol, r["date"]):
            result.ok("G3")
        else:
            result.fail("G3", "the move is not inside a stored results window")

        # G4 — is the reaction low a stop we can carry?
        entry = r["high"] * (1 + ENTRY_BUFFER_PCT / 100)
        risk = entry - r["low"]
        atr14 = ctx.atr
        risk_pct = risk / entry * 100 if entry else float("inf")
        atr_mult = risk / atr14 if atr14 and atr14 == atr14 else float("inf")
        if risk <= 0:
            result.fail("G4", "the reaction day's low is not below the trigger")
        elif risk_pct > MAX_STOP_PCT:
            result.fail("G4", f"stop is {risk_pct:.1f}% below the entry (over {MAX_STOP_PCT:g}%)")
        elif atr_mult > MAX_STOP_ATR:
            result.fail("G4", f"stop is {atr_mult:.1f} ATR below the entry (over {MAX_STOP_ATR:g})")
        else:
            result.ok("G4")

        # W1 — already extended into the news (Bonde's neglect point)
        if len(d) > NEGLECT_LOOKBACK:
            then = float(d["close"].iloc[-(NEGLECT_LOOKBACK + 1)])
            run = (ctx.close / then - 1) * 100 if then else 0.0
            if run > NEGLECT_MAX_RUN_PCT:
                result.watch_flags["W1"] = True
                result.watch_notes["W1"] = (f"up {run:.0f}% in {NEGLECT_LOOKBACK} sessions "
                                            f"before the news")
            else:
                result.watch_flags["W1"] = False
        # W2 — qualified on the gap alone
        result.watch_flags["W2"] = bool(r["move_pct"] < MIN_MOVE_PCT)
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = (f"gapped {r['gap_pct']:+.1f}% but closed "
                                        f"{r['move_pct']:+.1f}%")

        result.setups[EG01] = bool(result.hard_gates_passed)
        result.recompute_first_fail()
        return result

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """The reaction day is the signal; the break of its high is the TRIGGER, and a resting
        buy-stop is what fills it. So this is never "already fired" on the signal bar."""
        return False

    def setup_quality(self, result: StrategyResult) -> float:
        """Relative volume is the guide's strongest claim about which gaps hold, so it ranks."""
        if not result.has_setup:
            return 0.0
        return 1.0

    def build_plans(self, ctx: StockContext, result: StrategyResult,
                    cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        hi, lo = e.get("reaction_high"), e.get("reaction_low")
        if hi is None or lo is None:
            return PlanChoice(None, None, "missing reaction day")
        entry = round_tick(float(hi) * (1 + ENTRY_BUFFER_PCT / 100), cfg.tick_size, "up")
        stop = round_tick(float(lo), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(
            plan="EG", setup=EG01, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R, nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"buy-stop above the {e['reaction_date']} reaction high")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """A resting buy-stop, one per event, cancelled after {ENTRY_EXPIRY_BDAYS} sessions.

        No `max_fill`: the guide is explicit that a stock opening above the trigger is filled at
        the open and that the worse price should be counted. The stop-width cap at the fill is
        what refuses the cases where that gap made the trade unsizeable.
        """
        return {
            "order": "stop",
            "base_id": ctx.extras.get("reaction_date"),
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
        reasons: list[str] = []
        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        else:
            # The entry is a resting buy-stop that has not been hit yet, which is exactly what
            # TRADE_ON_TRIGGER means. There is no higher tier for this strategy by construction.
            label = "TRADE_ON_TRIGGER"
            reasons.append(f"buy-stop above the {ctx.extras.get('reaction_date')} reaction high")
            for code in ("W1", "W2"):
                if result.watch_flags.get(code):
                    reasons.append(result.watch_notes.get(code, code))

        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult,
                      plan: TradePlan | None) -> dict:
        e = ctx.extras
        return {
            "reaction_date": e.get("reaction_date"),
            "reaction_high": round(e["reaction_high"], 2) if e.get("reaction_high") else None,
            "reaction_low": round(e["reaction_low"], 2) if e.get("reaction_low") else None,
            "reaction_move_pct": e.get("reaction_move_pct"),
            "reaction_rel_volume": e.get("reaction_rel_volume"),
            "reaction_close_pos": e.get("reaction_close_pos"),
        }
