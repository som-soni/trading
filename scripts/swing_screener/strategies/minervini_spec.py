"""Minervini VCP, built to the written backtest specification (research/minervini-backtest-spec.md).

A second, rule-for-rule version of `minervini`, kept alongside it so the two can be compared: the
original stays the baseline. What differs from `minervini`:

- **Base detection** (core/vcp_spec.py) anchors on the base high — the last confirmed swing high no
  later close has exceeded — and measures every contraction from there, with the spec's numbers:
  swing points of `SWING_K` bars each side, a prior advance of `PRIOR_ADVANCE_PCT`%, a base of
  `BASE_MIN_DAYS`–`BASE_MAX_DAYS` sessions, `MIN_CONTRACTIONS`–`MAX_CONTRACTIONS` contractions each at
  most `SHRINK` × the one before, the first no deeper than `MAX_FIRST_DEPTH_PCT`%, a final tight area of
  `TIGHT_DAYS` sessions within `TIGHT_PCT`%, a pivot within `PIVOT_NEAR_HIGH` of the base high, and
  volume drying up to `DRYUP_RATIO` × its average.
- **MV-01 is the breakout day itself**, judged against the pivot frozen on the day before (the
  breakout bar must not move its own pivot), and confirmed by volume, a close in the upper half of
  the range and a close no more than `BUY_RANGE_PCT`% past the pivot. It is entered at the next
  open (EN-01). **MV-02** is the coil below the pivot, entered by a buy-stop through it (EN-02).
- **Stops** sit `STOP_BUFFER_PCT`% under the tight low and may be no more than `MAX_STOP_PCT`% below the
  fill (checked at the fill, not at the signal). One entry per base.
- **Exits** are the spec's EX-01 … EX-06: the stop, a failed breakout, breakeven at 2R, a third sold
  at 3R, climax runs, and a 50-day break on volume — the portfolio simulator's `minervini` mode.

The backtest adds the cross-sectional parts a one-symbol evaluation cannot do: the RS rating (TT-08),
ranking by RS then tightness, the market filter, the base number, and the spec's costs
(backtesting/backtest.py `--spec`).
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import vcp_spec
from ..core import swings as sw
from ..core.context import StockContext
from ..screens.criteria import (  # noqa: F401 (doc placeholders)
    MAX_PCT_BELOW_52W_HIGH, MIN_PCT_ABOVE_52W_LOW, RS_MIN_MOM, RS_MIN_RANK, SMA200_RISING_BARS,
)
from .base import LABELS, Decision, PlanChoice, Strategy, StrategyResult, TradePlan
from .minervini import MinerviniStrategy
from .trend_pullback import round_tick

MV01 = "MV-01"   # confirmed breakout through the frozen pivot
MV02 = "MV-02"   # coiled just below the pivot
MV03 = "MV-03"   # low cheat: a shelf in the lower third of the base
MV04 = "MV-04"   # cheat / 3C: a shelf in the middle third of the base

# ---- section 5: base and VCP (core/vcp_spec.py)
SWING_K = 5
MIN_SWING_PCT = 2.0
PRIOR_ADVANCE_PCT = 30.0
BASE_MIN_DAYS = 15
BASE_MAX_DAYS = 325
MIN_CONTRACTIONS = 2
MAX_CONTRACTIONS = 6
MAX_FIRST_DEPTH_PCT = 35.0
SHRINK = 0.80
TIGHT_DAYS = 10
TIGHT_PCT = 10.0
PIVOT_NEAR_HIGH = 0.90
DRYUP_RATIO = 0.70
VCP = vcp_spec.VcpParams(
    swing_k=SWING_K, min_swing_pct=MIN_SWING_PCT, prior_advance_pct=PRIOR_ADVANCE_PCT,
    base_min_days=BASE_MIN_DAYS, base_max_days=BASE_MAX_DAYS, min_contractions=MIN_CONTRACTIONS,
    max_contractions=MAX_CONTRACTIONS, max_first_depth_pct=MAX_FIRST_DEPTH_PCT, shrink=SHRINK,
    tight_days=TIGHT_DAYS, tight_pct=TIGHT_PCT, pivot_near_high=PIVOT_NEAR_HIGH, dryup_ratio=DRYUP_RATIO,
)

# ---- section 6: setups
COIL_PCT = 8.0          # MV-02: close within this % below the pivot
VOL_MULT = 1.4          # MV-01a: breakout volume ≥ this × the 50-day average
BUY_RANGE_PCT = 5.0     # MV-01b: close no more than this % above the pivot (and EN-01/EN-02 fills)
UPPER_HALF = 0.5        # MV-01c: close in at least this fraction of the day's range

# ---- section 8: stop
# MV-03, the low cheat, is OFF. Minervini calls it the riskiest of his three
# in-base entries and says he uses it sparingly, in stocks he already knows; the
# India backtest agrees emphatically -- 25 trades, a 4% win rate and -0.515R
# average, Rs257k of losses that turned a book the 3C had made Rs213k on into a
# Rs101k loss. An int rather than a bool so spec_params fingerprints it: flipping
# it has to change the spec_id, or two runs with different rules would share a
# cache and a report directory. `--const LOW_CHEAT_ENABLED=1` puts it back.
LOW_CHEAT_ENABLED = 0

CHEAT_SHELF_DAYS = 7    # MV-03/MV-04: sessions in the shelf (mirrors VcpParams.cheat_shelf_days)
CHEAT_SHELF_PCT = 8.0   # MV-03/MV-04: widest shelf that counts  (mirrors VcpParams.cheat_shelf_pct)

STOP_BUFFER_PCT = 0.5   # SL-01: stop this % under the tight low
MAX_STOP_PCT = 8.0      # SL-03: skip a fill whose stop is further below it than this
NOMINAL_TARGET_R = 3.0  # reporting only: the exits are rules (and EX-04 sells a third at 3R)
# Minervini's stated minimum reward-to-risk (ChartMill's SEPA write-up and the
# books both give 2:1 as the floor, 3:1 preferred). A rejection threshold, never
# a target floor: a setup projecting less is skipped, not padded.
MIN_STRUCTURAL_R = 2.0
# How far above the BASE HIGH a swing high has to sit before it counts as
# external supply rather than part of the base's own ceiling. A base's ceiling
# is not a single line: `swings.overhead_levels` collects every swing high, and
# a consolidation prints several within a hair of its high (both sides of the
# range, every retest of the pivot). `chart_pattern.overhead_cluster_atr` is the
# same guard for the same reason.
OVERHEAD_CLUSTER_ATR = 1.0

# ---- section 10 / backtest (backtesting/backtest.py --spec)
MAX_POSITIONS = 8               # PF-02
MAX_OPEN_RISK_PCT = 6.0         # PF-04
MAX_ADV_PCT = 5.0               # SL-06
EARNINGS_WARN_DAYS = 10


class MinerviniSpecStrategy(Strategy):
    selection = "time_series"
    family = "minervini"
    version = "1.5"
    changelog = (
        ("1.5", "2026-10-10",
         "MV-03, the low cheat, is off by default (LOW_CHEAT_ENABLED). On India 2010 onward with "
         "both entry modes, the three cheats and the pivot buy produced 210 trades: MV-04 made "
         "Rs213,395 over 177 trades at +0.070R, while MV-03 lost Rs257,039 over 25 at -0.515R on a "
         "4% win rate, turning a profitable book into a Rs101,290 loss on its own. Minervini "
         "describes the low cheat as the riskiest of his three in-base entries, used sparingly and "
         "only in stocks he knows well, so this is his own caveat showing up in the data rather "
         "than a surprise. Kept as a switch rather than deleted: 25 trades is a thin basis for "
         "removing an entry outright, and it should be confirmed on US data."),
        ("1.4", "2026-10-10",
         "The cheat entries (MV-03 low cheat, MV-04 \"3C\"). Minervini buys three points inside a "
         "base -- the lower third, the middle third and the pivot at the top -- and this spec only "
         "ever implemented the last, which is why it found nothing in stocks that never complete a "
         "textbook VCP. A cheat is a short shelf with a pivot of its own, and it runs off any base "
         "clearing VCP-01/02/03 rather than a completed VCP, because a cheat is taken while the base "
         "is still FORMING; waiting for completion IS the pivot buy. Its stop is the SHELF low, not "
         "the base low, which is the reason he takes it. Measured over ten leaders in both markets, "
         "2013 onward: valid trade plans 10 -> 74, with cheats appearing in 9 of 10 names including "
         "NVDA, BAJFINANCE, TRENT and SMCI, which produce no full VCP base at all. Median R 2.92 "
         "(MV-04) and 3.34 (MV-03) against 2.45 for the pivot buy, and every cheat plan clears the "
         "2:1 minimum. Whether they MAKE money is a separate question the backtest has to answer."),
        ("1.3", "2026-10-10",
         "The base high is a zone, not a line (VcpParams.bh_break_atr). The spec ends a base "
         "on ANY close above BH, so a leader making new highs can never hold one: VCP-02 then "
         "wants 15 more sessions from a fresh swing high. Across ten leaders in both markets "
         "the detector found 13 bases in 13 years and ZERO volume-confirmed breakouts, with "
         "NVDA (+1554%), CELH, SMCI, BAJFINANCE (+2063%) and TRENT yielding no base at all. "
         "A close must now clear BH by bh_break_atr x ATR to resolve the base, the same "
         "zone-not-line reasoning as chart_pattern.overhead_cluster_atr and this strategy's "
         "own OVERHEAD_CLUSTER_ATR. Measured: 'no base high at all' rejections fall 966 -> 738 "
         "(-24%) and detected breakouts rise 8 -> 11. It is a CORRECTNESS fix and nothing more "
         "-- bases stay at 13 and MV-01 stays at 0, because the freed bars fail VCP-04 (451) "
         "and VCP-06 (521) instead. bh_break_atr=0 reproduces the spec exactly."),
        ("1.2", "2026-10-10",
         "The point-in-time pre-filter no longer applies cfg.screener.min_price. The floor keeps "
         "live screening out of penny stocks, but a backtest reads it against SPLIT-ADJUSTED "
         "history, so it deleted the early years of exactly the stocks that went up most -- "
         "splitting is what winners do. NVDA traded about $15 in 2013 on $126m a day, 12x the "
         "liquidity floor; stored back-adjusted through a 4:1 and a 10:1 split that is $0.39, "
         "under the $10 US floor, so NVDA did not qualify until 2020-07-08 and SMCI not until "
         "2023. Liquidity is now carried by min_dollar_volume alone, which is split-invariant "
         "(close falls by the split factor, volume rises by it). Live screening keeps the price "
         "floor in screens/base.py, where today's price really is today's price. On NVDA this "
         "takes evaluable bars from 815 to 1,841 of 3,464; India is unaffected (min_price=0)."),
        ("1.1", "2026-10-10",
         "EN-02 now needs a confirming close. The resting buy-stop filled on any intraday "
         "poke through the pivot, with no volume or close test, so it systematically bought "
         "exactly what MV-01 is built to reject -- and EX-02 then sold it at the next open "
         "as a failed breakout. Over India 2010 onward, 9 of 14 trades filled on a bar that "
         "closed BELOW the entry (CDSL filled 956.78, closed 936.90) and 11 of 14 exited "
         "FAILED_BREAKOUT with a median hold of one day, for -0.40R each. The order now fills "
         "only on a bar that closes at or above the pivot, and fills AT that close: the close "
         "is what confirmed it, so paying the intraday stop price would be buying on "
         "information that did not exist at the touch. A poke that closes back below leaves "
         "the order resting -- the base is intact until it closes below the tight low."),
        ("1.0", "2026-10-10",
         "v1 baseline of the Minervini SEPA implementation: Trend Template gates (TT-01-08) with point-in-time RS, the VCP detector (VCP-01-11) segmented by an ATR-scaled zig-zag whose threshold shrinks with the contractions, the MV-01/MV-02 setups, the exit ladder (EX-01-07), a 2:1 minimum reward-to-risk measured from the base's own measured move, and overhead supply binding only at least OVERHEAD_CLUSTER_ATR above the base high. Earlier iteration history is in the git log."),
    )
    key = "minervini"
    name = "Minervini SEPA"
    description = (
        "The written Minervini backtest specification, rule for rule: Trend Template, a base-high "
        "anchored VCP, confirmed breakouts at the next open or buy-stops through the pivot, and the "
        "spec's exits (failed breakout, breakeven, partial profit, climax, 50-day break)."
    )
    style = "breakout"

    gate_codes = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8")
    watch_codes = ("B1", "B2", "B3", "B4")
    setup_codes = (MV01, MV02, MV03, MV04)
    extra_columns = ("pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                     "first_depth_pct", "last_depth_pct", "tightness_pct", "dryup_ratio", "breakout_volume_ratio",
                     "vcp_fail", "rs_mom")
    extra_numeric_columns = ("pivot", "tight_low", "pct_from_pivot", "base_high", "base_days", "contractions",
                             "first_depth_pct", "last_depth_pct", "tightness_pct", "dryup_ratio",
                             "breakout_volume_ratio", "rs_mom")
    needs_ctx_extras = True
    screen_key = "stage2"
    screen_gates = {"M1": "C1", "M2": "C2", "M3": "C3", "M4": "C4", "M5": "C5", "M6": "C6", "M7": "C7", "M8": "C8"}
    min_bars = 300

    thesis = (
        "The same edge as Minervini's SEPA — buy Stage-2 leaders as a volatility contraction completes, "
        "with small, capped losses against large winners — but tested exactly as the written "
        "specification defines it, so that the result measures the method rather than one reading of it."
    )
    how_it_works = (
        "Gates M1–M8 are the Trend Template (the Stage 2 screen's criteria): price above the 50/150/200-day "
        "averages, the averages stacked, the 200-day rising over {SMA200_RISING_BARS} sessions, at least "
        "{MIN_PCT_ABOVE_52W_LOW}% above the 52-week low and within {MAX_PCT_BELOW_52W_HIGH}% of the high, and "
        "relative strength. The backtest applies the true cross-sectional RS rating of {RS_MIN_RANK}+ on top.",
        "The base starts at the base high: the most recent confirmed swing high ({SWING_K} bars either side, "
        "known only {SWING_K} bars later) that no close has exceeded since. It must follow a {PRIOR_ADVANCE_PCT}% "
        "advance, last {BASE_MIN_DAYS}–{BASE_MAX_DAYS} sessions, start with the full template in force, and keep "
        "the long averages in order every day of it.",
        "Contractions run from each swing high to the lowest low before the next. There must be "
        "{MIN_CONTRACTIONS}–{MAX_CONTRACTIONS}, the first no deeper than {MAX_FIRST_DEPTH_PCT}% and each at most "
        "{SHRINK} × the one before. Wiggles under {MIN_SWING_PCT}% are ignored.",
        "The final tight area is the last {TIGHT_DAYS} sessions: its high is the pivot, its low the tight low. "
        "It must span at most {TIGHT_PCT}%, the pivot must be within {PIVOT_NEAR_HIGH} of the base high, and its "
        "volume must have dried up to {DRYUP_RATIO} × the 50-day average.",
        "MV-02 (coiled): the base is complete and the close is within {COIL_PCT}% below the pivot. A buy-stop "
        "rests just above the pivot.",
        "MV-01 (breakout): the base was complete yesterday, yesterday's close was at or below yesterday's "
        "pivot and today's close is above it — on at least {VOL_MULT} × average volume, in the upper half of "
        "the day's range, and no more than {BUY_RANGE_PCT}% past the pivot. Bought at the next open.",
    )
    caveats = (
        "**Survivorship bias.** The universe is today's listed stocks; companies delisted since are missing, "
        "which flatters every result.",
        "**Corporate actions.** Prices are adjusted when fetched; a split or bonus after a symbol's last full "
        "fetch shows as a crash until its history is re-fetched (`marketdata.splits`).",
        "**Relative strength** is applied twice: the per-stock gate M8 uses 12-1 month momentum of "
        "{RS_MIN_MOM}+ (a stand-in that a one-symbol evaluation can compute), and the backtest's `--min-rs` "
        "applies the true RS rating across the market. The stand-in rarely binds when the rating is 70+.",
        "**The fundamental screen (SEPA part 2) is not part of the spec or the backtest** — there is no "
        "point-in-time fundamental history.",
        "**Circuit limits** (C-03, India) are not modelled: a stop on a locked day fills at the next open, "
        "which daily bars cannot tell apart from a gap.",
        "**Base number** counts the bases that produced a breakout since the trend last broke; it is "
        "worked out by the backtest from the signal list, and only reported, not filtered on by default.",
        "EN-03 (buying inside the tight area before any breakout) is not implemented.",
        "The detector turns a chart-reading judgement into numbers; every threshold is a parameter of the "
        "spec (section 11), most of them marked there as assumptions.",
    )
    status = (
        "No demonstrated edge (India, 2010 onward, `--spec`). Confirmed breakouts (EN-01): 9 trades in 16 years, "
        "CAGR −0.1% — the spec's base rules almost never complete on Indian daily data. Buy-stops (EN-02): 114 trades, "
        "expectancy −0.03R, profit factor 0.86, CAGR 0.1% against the index's ~12%, max drawdown −8.6%; the "
        "failed-breakout exit closes ~80% of trades for −0.3R each. No parameter at either end of the spec's test "
        "ranges, and no failed-breakout window, gives an edge that holds both in and out of sample "
        "(research/minervini-spec-sensitivity-india.md). US, same rules: EN-01 26 trades, −0.14R; EN-02 526 trades, "
        "−0.02R, CAGR −0.8% (index ~13%), max drawdown −30% — +0.05R to 2019, −0.12R since; the stricter variants that "
        "help in sample all turn negative after 2019 (research/minervini-spec-sensitivity-us.md)."
    )

    gate_docs = {
        "M1": "TT-05: close above the 50-day average.",
        "M2": "TT-01: close above the 150-day average.",
        "M3": "TT-01: close above the 200-day average.",
        "M4": "TT-02 and TT-04: the 50-day above the 150-day above the 200-day.",
        "M5": "TT-03: the 200-day higher than {SMA200_RISING_BARS} sessions ago.",
        "M6": "TT-06: close at least {MIN_PCT_ABOVE_52W_LOW}% above the 52-week low.",
        "M7": "TT-07: close within {MAX_PCT_BELOW_52W_HIGH}% of the 52-week high.",
        "M8": "TT-08 stand-in: 12-1 month momentum of at least {RS_MIN_MOM}. The backtest also requires the "
              "true RS rating of {RS_MIN_RANK}+ across the market.",
    }
    watch_docs = {
        "B1": "Closed through the pivot on light volume — under {VOL_MULT} × the 50-day average (MV-01a), "
              "so not a confirmed breakout.",
        "B2": "Closed more than {BUY_RANGE_PCT}% past the pivot (MV-01b): extended beyond the buy range.",
        "B3": "Closed through the pivot but in the lower half of the day's range (MV-01c).",
        "B4": "Earnings are due within {EARNINGS_WARN_DAYS} days (live screen only).",
    }
    setup_docs = {
        MV01: "Breakout: yesterday's base was complete, and today's close went through yesterday's pivot "
              "on volume, in the upper half of the range, within {BUY_RANGE_PCT}% of the pivot.",
        MV02: "Coiled: the base is complete and the close is within {COIL_PCT}% below the pivot.",
        MV03: "Low cheat (OFF by default, {LOW_CHEAT_ENABLED}; `--const LOW_CHEAT_ENABLED=1` enables it): "
              "a shelf of {CHEAT_SHELF_DAYS} sessions spanning no more than "
              "{CHEAT_SHELF_PCT}% sits in the LOWER third of a base that has cleared VCP-01/02/03, and "
              "today's close went through its high. Taken while the base is still forming, so the stop "
              "is the shelf low rather than the base low. Minervini calls this the riskiest of his "
              "three in-base entries and uses it mainly in stocks he already knows.",
        MV04: "Cheat (\"3C\"): the same shelf in the MIDDLE third of the base — the cup-completion "
              "cheat, entered as the base recovers but before it reaches its old high.",
    }
    entry_rules = (
        "MV-01 (EN-01): buy at the next session's open; skip it if that open is more than {BUY_RANGE_PCT}% "
        "above the pivot or at or below the tight low.",
        "MV-02 (EN-02): a buy-stop at the pivot plus 0.1%, resting for up to 10 sessions. It fills only on a "
        "session that CLOSES at or above the pivot, and fills at that close (or the stop price if the close is "
        "below it); a session that pokes through the pivot and closes back below leaves the order resting. It is "
        "skipped if the fill would be more than {BUY_RANGE_PCT}% above the pivot, and cancelled by a close below "
        "the tight low.",
        "Stop: {STOP_BUFFER_PCT}% under the tight low. A fill whose stop is more than {MAX_STOP_PCT}% below "
        "it is skipped. Size: 1% of equity at risk, capped at the market's position limit.",
        "MV-03 / MV-04 (cheats): bought at the close of the session that clears the shelf high, stopped "
        "{STOP_BUFFER_PCT}% under the SHELF low rather than the base low — a nearby stop is the reason "
        "the entry exists. The objective is the base high plus the base's measured move from there.",
        "One entry per base: a base already traded is not entered again.",
        "Target: the base's measured move — its first (deepest) contraction projected from entry — "
        "capped by overhead supply at least {OVERHEAD_CLUSTER_ATR} ATR above the base high. A setup "
        "projecting under {MIN_STRUCTURAL_R}R on that basis is refused rather than padded up to it. "
        "{NOMINAL_TARGET_R}R remains the nominal figure used for sizing and reporting.",
    )
    exit_rules = (
        "In priority order, each session: EX-01 the stop (filled at the open if it gapped through); EX-02 a "
        "close below the pivot within 5 sessions of entry — a failed breakout, sold at the next open; EX-03 "
        "once the high reaches 2R, the stop rises to breakeven plus costs; EX-04 one third sold at 3R; EX-05 "
        "a climax run once up 25% (the biggest up day on the biggest volume since entry, 8 of 10 up closes, "
        "70% above the 200-day, or a 3% gap after a 50% gain), sold at the next open; EX-06 a close below "
        "the 50-day average on at least average volume, sold at the next open.",
        "Backtest: `--exit-mode minervini` in the portfolio simulator; the spec's run adds `--spec`, which "
        "sets {MAX_POSITIONS} positions, a {MAX_OPEN_RISK_PCT}% open-risk cap, a {MAX_ADV_PCT}% liquidity cap, "
        "RS ranking and the spec's costs.",
    )
    param_docs = (
        ("Swing confirmation", "SWING_K", "Bars either side of a swing point; it is known only this many bars later."),
        ("Prior advance", "PRIOR_ADVANCE_PCT", "Rise into the base high from the low of the 126 sessions before (VCP-01)."),
        ("Base length, minimum", "BASE_MIN_DAYS", "Sessions from the base high (VCP-02)."),
        ("Base length, maximum", "BASE_MAX_DAYS", "About 65 weeks (VCP-02)."),
        ("Contractions, minimum", "MIN_CONTRACTIONS", "VCP-04."),
        ("Contractions, maximum", "MAX_CONTRACTIONS", "VCP-04."),
        ("First contraction, deepest", "MAX_FIRST_DEPTH_PCT", "VCP-05."),
        ("Shrink factor", "SHRINK", "Each contraction at most this × the previous (VCP-06)."),
        ("Tight area", "TIGHT_DAYS", "Sessions in the final tight area (VCP-08)."),
        ("Tight-area span", "TIGHT_PCT", "Deepest final contraction and widest tight area (VCP-08)."),
        ("Pivot near the base high", "PIVOT_NEAR_HIGH", "VCP-09."),
        ("Volume dry-up", "DRYUP_RATIO", "Tight-area volume against its 50-day average (VCP-10)."),
        ("Coil distance", "COIL_PCT", "MV-02: how far below the pivot still counts."),
        ("Breakout volume", "VOL_MULT", "MV-01a."),
        ("Buy range", "BUY_RANGE_PCT", "MV-01b, and the most a fill may sit above the pivot."),
        ("Stop buffer", "STOP_BUFFER_PCT", "SL-01."),
        ("Maximum stop", "MAX_STOP_PCT", "SL-03, checked at the fill."),
        ("Cheat shelf length", "CHEAT_SHELF_DAYS", "Sessions in the shelf a cheat is bought from (MV-03/MV-04)."),
        ("Cheat shelf tightness", "CHEAT_SHELF_PCT", "Widest shelf, high to low, that counts as a cheat."),
        ("Minimum reward-to-risk", "MIN_STRUCTURAL_R", "Setups whose measured move projects less are refused."),
        ("Overhead cluster", "OVERHEAD_CLUSTER_ATR", "ATRs above the base high before a swing high caps the target."),
        ("Positions", "MAX_POSITIONS", "PF-02, with --spec."),
        ("Open-risk cap", "MAX_OPEN_RISK_PCT", "PF-04, with --spec."),
        ("Liquidity cap", "MAX_ADV_PCT", "SL-06: largest order as a % of 50-day average traded value, with --spec."),
        ("Minimum history", "min_bars", "Bars required before the template can judge a symbol."),
    )
    # No --strategy here: jobs/registry.py already passes "--strategy <key>", and a second
    # one wins on argparse, so naming the key twice broke the moment the key was renamed.
    backtest_args = "--spec --accept-labels 'TRADE - HIGH CONFIDENCE'"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        """The Trend Template and the market's liquidity floor, as of one row (shared with `minervini`)."""
        return MinerviniStrategy.prefilter_row(self, cfg, last)

    # ---------- evaluation ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        self.apply_screen(ctx, result)
        e = ctx.extras
        today, prev = vcp_spec.detect(d, VCP), vcp_spec.detect(d.iloc[:-1], VCP)
        last = d.iloc[-1]
        close, high, low, vol = (float(last[k]) for k in ("close", "high", "low", "volume"))
        v50 = float(last["vol_sma50"]) if pd.notna(last.get("vol_sma50")) else float("nan")
        prev_close = float(d["close"].iloc[-2])

        breakout = bool(prev["ok"] and prev_close <= prev["pivot"] < close)
        base = prev if breakout else today
        vol_ratio = vol / v50 if v50 and v50 == v50 else float("nan")
        rng = high - low
        upper = (close - low) / rng if rng > 0 else 1.0
        confirmed = {
            "B1": not (vol_ratio >= VOL_MULT),
            "B2": breakout and close > base["pivot"] * (1 + BUY_RANGE_PCT / 100),
            "B3": upper < UPPER_HALF,
        }
        mv01 = breakout and not any(confirmed.values())
        mv02 = bool(not breakout and today["ok"] and today["pivot"] * (1 - COIL_PCT / 100) <= close <= today["pivot"])
        # The cheat entries. Minervini buys three points in a base -- the low cheat
        # (lower third), the cheat/"3C" (middle third) and the pivot buy at the top
        # -- and only the last was implemented. A cheat is taken while the base is
        # still FORMING, so it runs off any base clearing VCP-01/02/03 rather than a
        # completed VCP, and its stop is the shelf low rather than the base low,
        # which is the whole reason he takes it: the stop is near.
        # yesterday's shelf, not today's: the shelf's high is the max over a window
        # that INCLUDES the current bar, so today's close can never exceed it and the
        # cross would be unsatisfiable. MV-01 freezes the pivot the same way.
        ch = prev if prev.get("cheat_ok") else None
        cheat_cross = bool(ch and prev_close <= ch["cheat_pivot"] < close)
        mv03 = bool(LOW_CHEAT_ENABLED and cheat_cross and ch["cheat_zone"] == "low")
        mv04 = bool(cheat_cross and ch["cheat_zone"] == "mid")
        result.setups[MV01], result.setups[MV02] = mv01, mv02
        result.setups[MV03], result.setups[MV04] = mv03, mv04

        for code in ("B1", "B2", "B3"):
            on = bool(breakout and confirmed[code])
            result.watch_flags[code] = on
        if result.watch_flags["B1"]:
            result.watch_notes["B1"] = f"volume {vol_ratio:.2f}× its 50-day average"
        if result.watch_flags["B2"]:
            result.watch_notes["B2"] = f"{(close / base['pivot'] - 1) * 100:.1f}% above the pivot"
        if result.watch_flags["B3"]:
            result.watch_notes["B3"] = f"closed at {upper * 100:.0f}% of the day's range"
        ed = ctx.earnings_days_away
        result.watch_flags["B4"] = bool(ed is not None and 0 <= ed <= EARNINGS_WARN_DAYS)
        if result.watch_flags["B4"]:
            result.watch_notes["B4"] = f"earnings in {ed} days"

        depths = base.get("depths") or []
        if ch is not None:
            e.update(cheat_pivot=ch["cheat_pivot"], cheat_low=ch["cheat_low"],
                     cheat_zone=ch["cheat_zone"], cheat_pos=ch["cheat_pos"],
                     cheat_range_pct=ch["cheat_range_pct"], base_low=ch.get("base_low"))
        e.update(
            pivot=base["pivot"], tight_low=base["tight_low"], base_high=base["bh"],
            base_date=str(base["bh_date"].date()) if base["bh_date"] is not None else None,
            base_days=base["base_days"], contractions=len(depths),
            first_depth_pct=depths[0] if depths else None, last_depth_pct=depths[-1] if depths else None,
            tightness_pct=base["tight_range_pct"], dryup_ratio=base["dryup"],
            breakout_volume_ratio=vol_ratio if breakout else None,
            vcp_fail=base["fail"], breakout=breakout,
        )
        result.recompute_first_fail()
        return result

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """MV-01 is bought at the next open, MV-02 by a resting buy-stop: both place an order today."""
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        if result.setups.get(MV01):
            return 2.0
        if result.setups.get(MV02):
            return 1.0
        # a cheat is a lower-confidence entry than the pivot buy, and the low cheat
        # lower than the 3C -- he describes it as the riskiest of the three
        return 0.8 if result.setups.get(MV04) else (0.6 if result.setups.get(MV03) else 0.0)

    # ---------- plan ----------

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        cheat = result.setups.get(MV03) or result.setups.get(MV04)
        pivot, tl = e.get("pivot"), e.get("tight_low")
        # Only the pivot buy needs the FINAL tight area. A cheat is taken while the
        # base is still forming, so that area does not exist yet -- requiring it here
        # rejected 122 of 133 cheats before they reached their own branch.
        if not cheat and (not pivot or tl is None or pd.isna(tl)):
            return PlanChoice(None, None, "missing pivot / tight low")
        if cheat:
            # A cheat is bought at its shelf, not the base's pivot, and stopped under
            # the SHELF low. That nearby stop is the entire point of the entry: the
            # base low is far away mid-base, and risking down to it would make the
            # trade worse than the pivot buy rather than better.
            setup = MV03 if result.setups.get(MV03) else MV04
            cp, cl = e.get("cheat_pivot"), e.get("cheat_low")
            if not cp or cl is None or pd.isna(cl):
                return PlanChoice(None, None, "missing cheat shelf")
            pivot = float(cp)
            entry = float(ctx.close)          # confirmed by the close, as EN-02 is since v1.1
            stop = round_tick(float(cl) * (1 - STOP_BUFFER_PCT / 100), cfg.tick_size, "down")
        else:
            setup = MV01 if result.setups.get(MV01) else MV02
            # MV-01 fills at tomorrow's open, whose best estimate today is the close; MV-02 at the buy-stop
            entry = float(ctx.close) if setup == MV01 else round_tick(float(pivot) * 1.001, cfg.tick_size, "up")
            stop = round_tick(float(tl) * (1 - STOP_BUFFER_PCT / 100), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        # Reward has to come from the CHART, not from the risk. `entry + 3 * risk`
        # restates the formula and reports an R the setup does not offer -- the same
        # trap breakout.py documents. The measured move of a VCP is its own depth:
        # the base high less its deepest low, which (because VCP-06 forces each
        # contraction to shrink) is the first contraction's low.
        bh, first_depth = e.get("base_high"), e.get("first_depth_pct")
        if cheat and bh:
            # A cheat is bought below the old high, so the nearest objective is that
            # high; the base's own measured move is projected from there. first_depth
            # is absent when the base never reached the contraction step, in which
            # case the old high alone is the objective.
            measured_move = float(bh) - entry + (float(bh) * float(first_depth) / 100
                                                 if first_depth else 0.0)
        else:
            measured_move = (float(bh) * float(first_depth) / 100
                             if bh and first_depth else float("nan"))
        target = entry + measured_move if measured_move == measured_move else entry + risk
        # Overhead supply caps the move — but measured from the BASE HIGH, not from
        # entry. The pivot sits below the base high by construction (VCP-09 only
        # requires it within 90%), so everything between them is the consolidation
        # being resolved, not external resistance. Capping at entry made the base's
        # OWN high the ceiling and crushed every projection: TITAN's 2017 setup, a
        # base the strategy actually traded, scored 0.84R instead of 2.28R.
        # ... but `> base_high` is not enough on its own: the levels a hair above
        # the base high ARE the base high, so the cap still landed on the base's
        # own structure. Measured over the 15 India v2.3 breakouts, 8 were capped
        # within 1.5% of their own base high (GODREJPROP at 1697.85 against a
        # 1697.85 base high, THERMAX at 5699.95 against 5699.95), which dropped
        # the median projection from 1.81R to 0.90R and rejected them for an
        # artefact of the base's own definition. Only supply at least
        # OVERHEAD_CLUSTER_ATR above the base high can cap the move.
        ceiling_from = max(entry, float(bh)) if bh else entry
        cluster_edge = ceiling_from + OVERHEAD_CLUSTER_ATR * ctx.atr
        nearest_above = sw.nearest_overhead_above(ceiling_from, ctx.overhead)  # reported, not binding
        binding = min((lvl for lvl in ctx.overhead if lvl >= cluster_edge), default=None)
        if binding is not None and binding < target:
            target = binding
        ctx.extras["overhead_caps_target"] = bool(binding is not None and binding < entry + measured_move) \
            if measured_move == measured_move else None
        structural_r = (target - entry) / risk if risk > 0 else float("nan")
        ctx.extras["structural_r"] = round(structural_r, 2) if structural_r == structural_r else None
        ctx.extras["measured_move"] = round(measured_move, 2) if measured_move == measured_move else None

        # Minervini's stated hard rule: a minimum reward-to-risk of 2:1, ideally 3:1.
        # "If the stock's realistic upside isn't at least twice the distance to your
        # stop, the trade isn't worth taking even if everything else lines up."
        # Rejected here rather than padded up to look acceptable.
        if not (structural_r >= MIN_STRUCTURAL_R):
            return PlanChoice(
                None, None,
                f"projects only {structural_r:.2f}R against the {MIN_STRUCTURAL_R:g}:1 minimum",
            )

        plan = TradePlan(plan="MV", setup=setup, entry=entry, stop=stop, target=target,
                         risk_per_share=risk, reward_per_share=target - entry,
                         r_multiple=round(structural_r, 2),
                         nearest_overhead_above_entry=nearest_above)
        return PlanChoice(plan, None,
                          f"{setup}: pivot {pivot:.2f}, stop {(entry - stop) / entry * 100:.1f}% "
                          f"below entry, projects {structural_r:.2f}R")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """How the portfolio simulator should place and manage this order (portfolio_sim docstring)."""
        e = ctx.extras
        # A cheat has no FINAL tight area -- its base is still forming -- so its
        # levels are the shelf's. Reading e["pivot"] unconditionally here is the
        # same mistake build_plans made, and it crashed the run rather than
        # degrading, because the cheat path never set those keys.
        if plan.setup in (MV03, MV04):
            pivot, tl = float(e["cheat_pivot"]), float(e["cheat_low"])
        else:
            pivot, tl = float(e["pivot"]), float(e["tight_low"])
        meta = {"pivot": pivot, "tight_low": tl, "max_fill": pivot * (1 + BUY_RANGE_PCT / 100),
                "max_risk_pct": MAX_STOP_PCT / 100, "base_id": e.get("base_date"),
                "tightness": e.get("tightness_pct")}
        if plan.setup == MV01:
            meta.update(order="open", min_open=tl)
        elif plan.setup == MV02:
            meta.update(order="stop", cancel_close_below=tl, confirm_close_above=pivot)
        else:
            # the shelf was cleared on today's close, so the fill is the next open,
            # as MV-01 does; cancel if it closes back under the shelf low
            meta.update(order="open", min_open=tl)
        return meta

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        q = self.setup_quality(result)
        if not result.hard_gates_passed:
            return Decision(LABELS["AVOID"], LABELS["AVOID"],
                            f"fails trend template gate {result.first_hard_fail}: {result.hard_notes.get(result.first_hard_fail, '')}",
                            0.0, 0.0, q)
        if plan is None or not plan.is_valid:
            return Decision(LABELS["AVOID"], LABELS["AVOID"], "no valid entry plan", 0.0, 0.0, q)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if plan.setup == MV01:
            label, reasons = "TRADE_HIGH_CONFIDENCE", ["confirmed breakout: buy at the next open"]
        elif plan.setup == MV02:
            label, reasons = "TRADE_ON_TRIGGER", ["coiled below the pivot: buy-stop through it"]
        else:
            # a cheat is neither coiled nor a buy-stop: it cleared its shelf on the close
            where = "lower" if plan.setup == MV03 else "middle"
            label = "TRADE_ON_TRIGGER"
            reasons = [f"cheat: cleared a shelf in the {where} third of the base, "
                       f"stopped under the shelf low"]
        if risk_pct > MAX_STOP_PCT:
            label = "WATCH_WAIT"
            reasons.append(f"stop {risk_pct:.1f}% below entry exceeds the {MAX_STOP_PCT:g}% maximum")
        label_before = label
        if regime_downgrade_active and label in ("TRADE_HIGH_CONFIDENCE", "TRADE_ON_TRIGGER"):
            label = "WATCH_WAIT"
            reasons.append("market filter: no new buys")
        return Decision(LABELS[label_before], LABELS[label], "; ".join(reasons), risk_pct, plan.r_multiple, q)

    def watch_cap(self, result: StrategyResult) -> str:
        return "TRADE_HIGH_CONFIDENCE"

    def report_extras(self, ctx, result, plan) -> dict:
        e = ctx.extras
        pivot = e.get("pivot")

        def r(k, n=2):
            v = e.get(k)
            return round(float(v), n) if v is not None and pd.notna(v) else None
        return {
            "pivot": r("pivot"), "tight_low": r("tight_low"),
            "pct_from_pivot": round((ctx.close / pivot - 1) * 100, 2) if pivot else None,
            "base_high": r("base_high"), "base_days": e.get("base_days"), "contractions": e.get("contractions"),
            "first_depth_pct": r("first_depth_pct", 1), "last_depth_pct": r("last_depth_pct", 1),
            "tightness_pct": r("tightness_pct", 1), "dryup_ratio": r("dryup_ratio"),
            "breakout_volume_ratio": r("breakout_volume_ratio"), "vcp_fail": e.get("vcp_fail"),
            "rs_mom": r("rs_mom", 3),
        }


    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The base box the VCP was anchored to, its pivot and tight-area low, and a note saying
        how the base was identified — all from the signal's own cached extras (see base.py)."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        bh, bd, tl = e.get("base_high"), e.get("base_date"), e.get("tight_low")
        if bh and bd:
            depths = (f"{e['first_depth_pct']:g}% → {e['last_depth_pct']:g}%"
                      if e.get("first_depth_pct") is not None and e.get("last_depth_pct") is not None else "?")
            out.append({"shape": "box", "from": str(bd), "to": d, "top": float(bh),
                        "bottom": float(tl) if tl else float(bh) * (1 - (e.get("first_depth_pct") or 10) / 100),
                        "role": "base", "label": f"base {e.get('base_days', '?')}d · {e.get('contractions', '?')}c {depths}"})
            note = (f"Base: highest high {bh:g} on {bd}, {e.get('base_days', '?')} sessions. "
                    f"{e.get('contractions', '?')} contractions shrinking {depths} (each must be ≤ {SHRINK:g}× the one before). ")
            if e.get("tightness_pct") is not None:
                note += f"Final tight area {e['tightness_pct']:g}% deep"
                note += f", volume {e['dryup_ratio']:g}× the 50-day average (dry-up). " if e.get("dryup_ratio") is not None else ". "
            if e.get("cheat_pivot") and e.get("cheat_zone"):
                out.append({"shape": "box", "bars": CHEAT_SHELF_DAYS, "to": d,
                            "top": float(e["cheat_pivot"]), "bottom": float(e["cheat_low"]),
                            "role": "base", "dash": True,
                            "label": f"cheat shelf · {e['cheat_zone']} third of the base"})
                note += (f"Cheat shelf {e['cheat_low']:g}-{e['cheat_pivot']:g} in the "
                         f"{e['cheat_zone']} third of the base; bought on the close through its "
                         f"high, stopped under its low. ")
            note += (f"VCP rejected: {e['vcp_fail']}." if e.get("vcp_fail")
                     else f"Pivot {e['pivot']:g} — the final contraction's high; a buy-stop goes just above it." if e.get("pivot") else "")
            out.append({"shape": "note", "at": d, "price": float(bh), "text": note})
        if e.get("pivot"):
            out.append({"shape": "level", "from": str(bd) if bd else None, "bars": None if bd else 40, "to": d,
                        "price": float(e["pivot"]), "role": "pivot", "label": f"pivot {e['pivot']:g}"})
        if tl:
            out.append({"shape": "level", "from": str(bd) if bd else None, "bars": None if bd else 40, "to": d,
                        "price": float(tl), "role": "support", "label": f"tight-area low {tl:g} — the stop's anchor"})
        return out or super().chart_anatomy(sig)
