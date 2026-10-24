"""Donchian channel breakout — classical trend following, adapted to equities.

Richard Donchian's 4-week rule and the Turtle system built on it (Dennis &
Eckhardt, 1983) are the canonical systematic trend-following rules: buy an
N-day high, exit on an M-day low, stop at a multiple of volatility, size by
risk, and apply almost no other filter. The thesis is that trends persist and
that the system's edge comes from never cutting a winner short, at the cost of
a low win rate and many small losses.

Deliberately almost gate-free
----------------------------
`trend_pullback` applies 14 hard gates and passes 5.4% of symbol-days; across
13.75 years it returned -0.87% (US) and +0.57% (India). The evidence in this
repository says filtering subtracted value. This strategy is the opposite
experiment: two structural conditions and nothing else.

Why it is worth testing here
----------------------------
Of eight exit policies tested on the same 879 signals, the Donchian exit was
the ONLY one with positive per-trade expectancy (+0.095R vs the fixed
bracket's -0.044R). This takes that result and builds the entry to match.

Honest limits
-------------
Trend following's track record is in diversified FUTURES portfolios — dozens
of low-correlation markets, traded long and short. A long-only single-country
equity book has neither property, so the historical evidence for the approach
transfers only partially. There is also no profit target by construction: the
exit is the M-day low, so `r_multiple` here describes a nominal target used
for sizing, not an expectation.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import indicators as ind  # noqa: F401  (kept for symmetry/extension)
from ..core.context import StockContext
from .base import (
    tradable_point_in_time,
    CAP_ORDER,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .trend_pullback import round_tick

DC01 = "S1"   # DC-01  # breakout of the entry channel
DC02 = "S2"   # DC-02  # coiled just under the channel high


class DonchianStrategy(Strategy):
    selection = "time_series"
    version = "1.2"
    changelog = (
        ("1.2", "2026-10-16",
         "Gate, watch and setup codes renamed to one scheme shared by every strategy: G1..Gn for the hard "
         "gates, W1..Wn for the watch flags, S1..Sn for the setups. "
         "The old letters meant nothing and collided across strategies: B1-B4 were minervini's WATCH flags "
         "and breakout's GATES, so one string blocked a trade in the first and merely noted something in "
         "the second. The prefix now states the only thing that matters when reading a drop reason -- "
         "whether the code can stop a trade. No rule changed, but the code tuples are part of the "
         "fingerprint, so this moves the spec id and earlier runs stay under their own versions."
         "DC-01/02 become S1/S2 and XN1/XN2 become W1/W2; the setup docs cite DC-0n."),
        ("1.1", "2026-10-10",
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
        ("1.0", "2026-10-10",
         "v1 baseline of the Donchian channel breakout strategy."),
    )
    key = "donchian"
    name = "Donchian channel"
    description = (
        "Classical trend following: buy an N-day high, exit on an M-day low, "
        "stop at a volatility multiple, and filter almost nothing."
    )
    style = "trend"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    watch_codes = ("W1", "W2")
    setup_codes = (DC01, DC02)
    setup_names = {DC01: "Channel breakout", DC02: "Coil"}
    # short names for the chart's checklist; the rules themselves are gate_docs
    gate_titles = {"G1": "Above the 200-day", "G2": "Not already run away"}
    # the target is only for sizing: the trade ends on a close below the exit channel
    nominal_target = True
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("channel_high", "channel_low", "exit_channel", "pct_from_channel")
    extra_numeric_columns = extra_columns

    # --- the only real parameters ---
    entry_channel: int = 55      # Turtle "System 2" entry; Donchian's 4-week rule is 20
    exit_channel: int = 20       # exit on a 20-day low
    stop_atr_mult: float = 2.0   # the Turtles' 2N stop
    min_stop_pct: float = 2.0    # floor: never risk a stop tighter than this
    nominal_target_atr: float = 10.0  # far target — the real exit is the channel

    thesis = (
        "Trends persist, so buy a new N-day high and hold until the trend "
        "breaks. The edge is in never capping a winner, paid for with a low "
        "win rate and many small losses."
    )
    # Overview only; the exact tests are in the gate/watch/setup docs and the rule groups below.
    # Every fact here was checked against evaluate / build_plans / classify above, the pipeline's
    # pre-filter and backtesting/portfolio_sim.py (resting buy-stop, --exit-mode donchian).
    how_it_works = (
        "**The idea.** The Turtle-style channel system on a long-only stock book: buy a close above "
        "the {entry_channel}-day high, sell when the trend breaks, filter almost nothing.",
        "**Qualify.** A liquidity floor, then two hard gates: a close above the 200-day average (G1) "
        "and a close no more than 1 ATR past the channel high (G2). See Gates and When no new trade "
        "is taken.",
        "**Signal.** S1, a close above the highest high of the {entry_channel} sessions before today. "
        "S2 only marks a close coiled within 1 ATR under it. See Setups.",
        "**Buy.** A buy-stop 0.1% above the channel high. S1's close is already through it, so it "
        "fills at the next session's open. See Entry.",
        "**Stop.** {stop_atr_mult} ATR under the entry, never closer than {min_stop_pct}%, and it "
        "never moves. See Stop.",
        "**Sell.** The backtest sells at the first close below the lowest low of the prior 50 "
        "sessions; live, the screen shows the {exit_channel}-day low. There is no real target. See "
        "Target and Exit.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: S1 with both gates, neither watch "
        "flag, and a stop no more than 15% below the entry.",
        "**Where the rules come from.** Richard Donchian's channel rule and the Turtles' System 2 "
        "(55-day entry, 2N stop). There is no written spec with row ids: DC-01 and DC-02 are the "
        "setups' names from before the S1/S2 codes.",
    )
    caveats = (
        "**No demonstrated edge.** It trailed the index in both markets (see Status). It exists "
        "because its exit was the only one of eight exit policies, tested on the same 879 signals, "
        "with a positive expectancy per trade: +0.095R, against the fixed bracket's -0.044R.",
        "**Not a futures portfolio.** Trend following's track record is in diversified futures traded "
        "long and short. A long-only, single-market stock book has neither the cross-market "
        "diversification nor the short side.",
        "**A low win rate by design.** Judge it on expectancy and the size of its winners, never on "
        "its hit rate.",
        "**Run it with its exit flags.** `--exit-mode donchian --no-target --donchian-bars 50` (the "
        "page's backtest command adds them). Without them the default bracket sells everything at "
        "the nominal target, which caps exactly the winners the strategy exists to keep.",
        "**Live and backtest exits differ.** The screen reports the {exit_channel}-day low as the exit "
        "level, but every recorded backtest exits on the 50-day low.",
        "**Ties are arbitrary.** Every signal the backtest accepts scores the same setup quality, 2. "
        "When more breakouts trigger than there are free slots, the book fills in scan order, which "
        "is roughly alphabetical. `--rank-by` (momentum, vol_scaled, random) replaces that order.",
        "**No price floor anywhere.** Version 1.1 removed `cfg.screener.min_price` from the "
        "point-in-time pre-filter. The daily screen calls that same pre-filter, so it applies no "
        "price floor either; only the Screens page's snapshot does.",
        "**The fill session is never checked.** In the backtest the stop and the channel exit are "
        "first tested on the session after the fill. A session that triggers the buy and then trades "
        "through the stop is held overnight, and survives if the next session stays above the stop: "
        "kinder than a real stop order.",
        "**Every new high signals.** S1 is not only the first break. Every close above the prior "
        "{entry_channel} sessions' high counts, so a stock in a run signals day after day, and after "
        "an exit the next such close can buy it again.",
    )

    # --- full reference documentation (the web app's Strategy page) ---
    # Numbers are `{NAME}` placeholders of the numeric class attributes (entry_channel, ...), which
    # render_doc fills with the live values. A literal is written where the code uses a literal.
    status = (
        "No demonstrated edge: backtested from 2013 on the full universe with a 50-day "
        "channel exit and no target (v1.1, measured 2026-10-13 after the cost fix), it "
        "trailed the index in both markets: India 7.68% CAGR vs 11.7% (max drawdown "
        "-44.2%), US 6.53% vs 12.8% (max drawdown -49.3%). Trade shape is sound (profit "
        "factor ~1.2 in earlier runs) but signal selection among tied breakouts is arbitrary."
    )
    gate_docs = {
        "G1": (
            "Close above the 200-day average (the Above-the-200-day screen's A1).\n\n"
            "- **Test:** today's close is strictly above today's 200-day simple moving average of closes.\n"
            "- **Fails:** a close at or below it, or no average yet (fewer than 200 closes).\n\n"
            "The one concession to trend: a long-only stock book cannot profit from downtrends the way "
            "a long/short futures portfolio can."
        ),
        "G2": (
            "Close no more than 1 ATR above the {entry_channel}-day channel high: the breakout has not "
            "already run away.\n\n"
            "- **Channel high:** the highest high of the {entry_channel} sessions before today. Today's "
            "own high is left out, so today's close can beat it.\n"
            "- **ATR:** ATR14, the 14-day Wilder average true range, as of today's bar.\n"
            "- **Test:** close ≤ channel high + 1 × ATR14. Exactly 1 ATR above passes.\n"
            "- **Fails:** a close further above it. The stock is AVOID, and the reason gives the "
            "distance in ATR."
        ),
    }
    watch_docs = {
        "W1": (
            "A breakout (S1) on below-average volume.\n\n"
            "- **Test:** S1 is active and today's volume is below the 50-day average volume (an average "
            "that includes today).\n"
            "- **Effect:** caps the decision at TRADE ON TRIGGER and cuts setup quality from 2 to 1.5.\n\n"
            "The backtest buys only TRADE - HIGH CONFIDENCE, so it never trades a W1 breakout."
        ),
        "W2": (
            "A very wide volatility stop: {stop_atr_mult} ATR is more than 12% of the close.\n\n"
            "- **Test:** {stop_atr_mult} × ATR14 ÷ today's close × 100 > 12, on any day, setup or not.\n"
            "- **Effect:** caps the decision at TRADE ON TRIGGER, so the backtest never trades it. No "
            "effect on setup quality.\n\n"
            "A separate test in the decision is on the plan's real stop: more than 15% below the entry "
            "is WATCH - WAIT (see Stop)."
        ),
    }
    setup_docs = {
        DC01: (
            "DC-01 channel breakout: today's close is above the highest high of the {entry_channel} "
            "sessions before today.\n\n"
            "- **Channel high:** the highest high of those {entry_channel} sessions. Today's bar is "
            "excluded.\n"
            "- **Test:** close > channel high, strictly. There is no volume test; low volume only "
            "raises W1.\n"
            "- **Signal:** the setup is the entry signal. It is the only setup that can reach TRADE - "
            "HIGH CONFIDENCE and the only one the backtest buys (setup quality 2).\n\n"
            "It fires on every such close, not only the first, so a stock making a string of new highs "
            "signals each day. With G2, a tradeable close lies above the channel high but no more than "
            "1 ATR above it."
        ),
        DC02: (
            "DC-02 coil: today's close sits within 1 ATR below the {entry_channel}-day channel high.\n\n"
            "- **Test:** channel high − ATR14 ≤ close ≤ channel high, both ends included.\n"
            "- **Signal:** none yet. It builds a plan with the same entry and stop as S1, but the "
            "decision is at best TRADE ON TRIGGER: buy only if price takes out the channel.\n\n"
            "The backtest never buys it (setup quality 1)."
        ),
    }
    entry_rules = (
        "Signal. An S1 close above the {entry_channel}-day channel high, graded TRADE - HIGH "
        "CONFIDENCE. Live, an S2 coil or a capped S1 is TRADE ON TRIGGER: the same order, placed by "
        "the trader.",
        "Order. A buy-stop at the channel high + 0.1%, rounded up to the market's tick. It is set at "
        "the channel, not at today's high, so a wild intraday spike does not raise the entry.",
        "Fill. S1's close is already through the channel, so in practice the order fills at the next "
        "session's open. In the backtest it fills on the first later session whose high reaches the "
        "entry, at the higher of the entry and that session's open, plus slippage. It never fills on "
        "the signal session itself.",
        "Expiry and cancel (backtest). An unfilled order rests for up to 10 business days. It is "
        "cancelled if a session's low reaches the stop while its high stays under the entry, and "
        "skipped if the fill would be at or above the nominal target.",
        "One position per stock (backtest). A signal in a stock already held, or with an order "
        "already resting, is ignored.",
        "No re-test at the fill. The 15% stop test uses the planned entry. A gap up at the open raises "
        "the price paid but not the stop, so the real risk is wider than planned.",
    )
    stop_rules = (
        "Where it goes. The lower of entry − {stop_atr_mult} × ATR14 (the Turtles' 2N) and entry × "
        "(1 − {min_stop_pct}%), rounded down to the tick. So it is {stop_atr_mult} ATR under the "
        "entry, but never closer than {min_stop_pct}%: on a very quiet stock {stop_atr_mult} ATR "
        "would be a stop that ordinary daily noise takes out.",
        "It defines 1R. The distance from the price paid to the stop is the trade's risk, 1R. Results "
        "are counted in R.",
        "How far is too far. If entry − stop is more than 15% of the entry, the plan is WATCH - WAIT "
        "and is not bought. W2 already caps any stock whose {stop_atr_mult}-ATR stop is more than 12% "
        "of the close.",
        "How it sells (backtest). A standing sell order: the first session whose low touches the stop "
        "sells at the stop, or at the open if it opened below it. A gap can therefore lose more than "
        "1R, and slippage is charged on top.",
        "It never moves. No trailing and no breakeven. The channel exit (see Exit) is what protects "
        "a gain.",
    )
    target_rules = (
        "There is no sell order at the target. The target is entry + {nominal_target_atr} × ATR14, a "
        "far, nominal number so that the plan has an R column. The backtest runs with `--no-target`, "
        "so it never sells there.",
        "No reward test. No minimum R is required: a trend system has no real target, so testing R "
        "against a nominal one would test an assumption, not the setup.",
        "One use in the backtest. An order whose fill would be at or above the nominal target is "
        "skipped. With the target {nominal_target_atr} ATR above the entry, that practically never "
        "happens.",
        "Without `--no-target`, the default bracket exit sells the whole position at the nominal "
        "target.",
    )
    exit_rules = (
        "The channel exit (backtest). Each session after the fill, the stop is checked first (see "
        "Stop). If it did not sell, a close below the lowest low of the prior 50 sessions "
        "(`--donchian-bars 50`, today excluded) sells the whole position at that close.",
        "Early on, the stop decides. Right after a {entry_channel}-day breakout the 50-day low usually "
        "sits below the stop, so a failed breakout ends at the stop. The channel exit takes over once "
        "the 50-day low has risen above the stop.",
        "Live, the exit level shown is the {exit_channel}-day low: the lowest low of the "
        "{exit_channel} sessions before today (channel_low), also drawn on the chart. Nothing manages "
        "an open position; the trader applies the exit.",
        "No other exits. No target, time stop, breakeven or partial sale. A position still open when "
        "the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down. Example: "
        "$100,000 at 1% risks $1,000; paying $50 with the stop at $46 risks $4 a share, so 250 shares.",
        "Capped. The position may not be worth more than Max position size × equity. With 1% risk and "
        "a 25% cap, any stop closer than 4% below the price paid hits the cap, and the trade then "
        "risks less than 1%.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can instead of skipping.",
        "Backtest and live. The backtest sizes from current equity at the fill. The live screen sizes "
        "from the configured account size, at the lower high-volatility risk when the volatility "
        "index is above the market's threshold. A plan that cannot buy even one share is WATCH - WAIT.",
        "Slots. At most Position cap positions at once. A triggered order with no free slot keeps "
        "resting until it expires, and may fill later at a higher open.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity, "
        "live and in the backtest.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "No price floor. Neither the daily screen nor the backtest applies the Minimum price (see "
        "Caveats). India's daily screen also drops companies below the India config's minimum market "
        "cap.",
        "No earnings rule. Results dates are ignored, live and in the backtest: a breakout the day "
        "before results is bought like any other.",
        "Market regime. Live, a risk-off market lowers every decision one tier, so nothing is HIGH "
        "CONFIDENCE. The backtest does not apply it.",
        "Already in the stock, or no room. See Entry and Position size.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Both gates pass, today's close is above the {entry_channel}-day channel "
                                 "high (S1), neither watch flag is raised, the stop is no more than 15% "
                                 "below the entry and one share fits the account. The only tier the "
                                 "backtest buys.",
        "TRADE_ON_TRIGGER": "An S2 coil (the close within 1 ATR under the channel high: buy only on the "
                            "break), or an S1 breakout capped by W1 or W2, or a HIGH CONFIDENCE "
                            "lowered by a risk-off market.",
        "WATCH_WAIT": "The stop would be more than 15% below the entry, or not even one share fits the "
                      "account's risk budget and position cap, or a TRADE ON TRIGGER lowered by a "
                      "risk-off market.",
        "AVOID": "G1 or G2 failed, or the plan's risk is not a positive number. A stock that passes both "
                 "gates with no setup shows as NO SETUP instead.",
    }
    regime_note = (
        "Live only. When the market is risk-off (the first two broad indices in the market's config "
        "both close at or below their 50-day average), every decision except AVOID drops one tier "
        "(HIGH CONFIDENCE → ON TRIGGER → WATCH → AVOID) and the reason says 'market-regime downgrade "
        "applied'. The backtest does not apply it."
    )
    param_docs = (
        ("Entry channel", "entry_channel",
         "Sessions before today whose highest high is the channel high (S1, S2, G2). The Turtles' "
         "System 2 uses 55; Donchian's original 4-week rule is 20."),
        ("Exit channel (live)", "exit_channel",
         "Sessions before today whose lowest low the screen reports as the exit level. The backtest "
         "exits on --donchian-bars 50 instead."),
        ("Stop distance", "stop_atr_mult",
         "Stop = entry − this × ATR14 (the Turtles' 2N), unless the minimum stop is wider."),
        ("Minimum stop", "min_stop_pct",
         "The stop is never closer than this % below the entry."),
        ("Nominal target", "nominal_target_atr",
         "Target = entry + this × ATR14. Only for the plan's R column; never a sell order in the "
         "recommended backtest."),
        ("Minimum history", "min_bars",
         "Daily bars a stock needs before it is evaluated."),
        ("Minimum price", "cfg.screener.min_price",
         "Not applied by this strategy: the daily screen and the backtest both use the point-in-time "
         "pre-filter, which skips it. Only the Screens page's snapshot applies it."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct",
         "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct",
         "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions",
         "Backtest slots. With many tied breakouts this is the binding limit."),
        ("Tick size", "cfg.tick_size",
         "The entry is rounded up and the stop rounded down to this increment."),
        ("Slippage", "cfg.slippage_bps",
         "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--exit-mode donchian --no-target --donchian-bars 50"

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        # Deliberately NO trend/ADX/momentum screen: the channel breakout is
        # the signal, and pre-filtering on trend duplicates it.
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        close = ctx.close
        atr14 = float(d["atr14"].iloc[-1])

        ch_high = float(d["high"].iloc[-(self.entry_channel + 1) : -1].max())
        ch_low = float(d["low"].iloc[-(self.exit_channel + 1) : -1].min())
        ctx.extras["channel_high"] = ch_high
        ctx.extras["channel_low"] = ch_low

        # N1: long-only concession — don't buy breakouts under the 200-day (the Above-200 screen's A1)
        self.apply_screen(ctx, result)

        # N2: the breakout has already run away
        if atr14 and close > ch_high + atr14:
            result.fail(
                "G2",
                f"already {(close - ch_high) / atr14:.1f} ATR above the channel high",
            )
        else:
            result.ok("G2")

        result.setups[DC01] = bool(close > ch_high)
        result.setups[DC02] = bool(
            atr14 and ch_high - atr14 <= close <= ch_high
        )

        result.recompute_first_fail()
        self._watch_flags(ctx, result, atr14, ch_high)
        return result

    def _watch_flags(self, ctx, result, atr14, ch_high) -> None:
        d = ctx.daily
        # XN1: thin volume on the breakout — not disqualifying, but noted
        vol, vol_sma50 = float(d["volume"].iloc[-1]), d["vol_sma50"].iloc[-1]
        thin = pd.notna(vol_sma50) and vol_sma50 and vol < vol_sma50
        result.watch_flags["W1"] = bool(thin and result.setups.get(DC01))
        if result.watch_flags["W1"]:
            result.watch_notes["W1"] = "breakout on below-average volume"
        # XN2: very wide stop relative to price
        risk_pct = (self.stop_atr_mult * atr14 / ctx.close * 100) if ctx.close else float("nan")
        result.watch_flags["W2"] = bool(risk_pct == risk_pct and risk_pct > 12)
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = f"2 ATR stop is {risk_pct:.0f}% of price"

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("W1"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("W2"):
            caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        score = 2.0 if result.setups.get(DC01) else (1.0 if result.setups.get(DC02) else 0.0)
        if result.watch_flags.get("W1"):
            score -= 0.5
        return score

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """For a channel breakout the signal IS the setup: DC-01 means today's
        close is already through the channel high."""
        return bool(result.setups.get(DC01))

    def build_plans(
        self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig
    ) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        atr14 = ctx.atr
        ch_high = ctx.extras.get("channel_high")
        if ch_high is None or pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing channel/ATR")

        setup = DC01 if result.setups.get(DC01) else DC02
        # The entry is the CHANNEL HIGH — that is where a resting buy-stop
        # would have been filled. Using max(today's high, channel) instead
        # inflates the entry whenever today had a wild range: AZTA spiked to
        # 41.99 and closed at 38.75, which produced an entry of 42.04 — above
        # a level the stock had already rejected. Gate N2 handles the case
        # where price has genuinely run away from the channel.
        entry = round_tick(float(ch_high) * 1.001, cfg.tick_size, "up")

        # 2N is the Turtle stop, but on a very quiet equity it degenerates:
        # ATKR's ATR is 0.40% of price, so 2 ATR is a 0.8% stop that ordinary
        # daily noise would take out immediately — fatal for a system whose
        # edge is holding trends. Floor it.
        atr_stop = entry - self.stop_atr_mult * atr14
        floor_stop = entry * (1 - self.min_stop_pct / 100)
        stop = round_tick(min(atr_stop, floor_stop), cfg.tick_size, "down")
        # A nominal far target only so sizing and reporting have a number. The
        # REAL exit is a close below the exit channel — see the caveats.
        target = entry + self.nominal_target_atr * atr14

        plan = TradePlan(
            plan="DC", setup=setup, entry=entry, stop=stop, target=target,
            risk_per_share=entry - stop, reward_per_share=target - entry,
            r_multiple=(target - entry) / (entry - stop) if entry > stop else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"{setup} channel breakout above {ch_high:.2f}")

    # ---------- decision ----------

    def classify(
        self,
        ctx: StockContext,
        result: StrategyResult,
        plan: TradePlan,
        sizing_result,
        earnings_days_away: int | None,
        regime_downgrade_active: bool,
    ) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision(
                "AVOID", "AVOID",
                f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                float("nan"), float("nan"), 0.0,
            )
        if not plan.is_valid:
            return Decision(
                "AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                float("nan"), float("nan"), 0.0,
            )

        risk_pct = plan.risk_per_share / plan.entry * 100
        cap = self.watch_cap(result)
        fired = self.entry_signal_fired(ctx, result)
        reasons: list[str] = []

        # NOTE: deliberately no minimum-R test. A trend system has no profit
        # target, so requiring R >= 2 against a nominal one would be testing an
        # assumption rather than the setup.
        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        elif risk_pct > 15:
            label = "WATCH_WAIT"
            reasons.append(f"2 ATR stop is {risk_pct:.1f}% of price (> 15%)")
        elif not fired:
            label = "TRADE_ON_TRIGGER"
            reasons.append("coiled under the channel, breakout not yet confirmed")
        elif cap == "TRADE_HIGH_CONFIDENCE":
            label = "TRADE_HIGH_CONFIDENCE"
            reasons.append(f"{plan.setup} broke the {self.entry_channel}-day channel")
        else:
            label = cap
            for code in ("W1", "W2"):
                if result.watch_flags.get(code):
                    reasons.append(result.watch_notes.get(code, code))

        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")

        return Decision(
            LABELS[before], LABELS[label], "; ".join(reasons),
            risk_pct, plan.r_multiple, self.setup_quality(result),
        )

    def report_extras(
        self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None
    ) -> dict:
        ch = ctx.extras.get("channel_high")
        return {
            "channel_high": round(ch, 2) if ch else None,
            "channel_low": round(ctx.extras["channel_low"], 2)
            if ctx.extras.get("channel_low") else None,
            "exit_channel": self.exit_channel,
            "pct_from_channel": round((ctx.close / ch - 1) * 100, 2) if ch else None,
        }

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """For the chart's Trade setups layer: the advance into the channel (zone 1), the
        {entry_channel}-day channel as a band, the coil zone 1 ATR under its high that DC-02 marks, and
        the {exit_channel}-day low the trade exits on — the windows evaluate() itself reads."""
        d = ctx.daily
        day = lambda ts: str(pd.Timestamp(ts).date())
        out: list[dict] = []
        win = d.iloc[-(self.entry_channel + 1): -1]
        if len(win) < 2:
            return self.chart_anatomy(sig)
        hi, lo = float(win["high"].max()), float(win["low"].min())
        lo_day = win["low"].idxmin()
        run = win.loc[lo_day:]
        if len(run) > 1 and lo > 0:
            hi_day = run["high"].idxmax()
            out.append({"shape": "line", "from": day(lo_day), "to": day(hi_day), "p0": lo, "p1": float(run["high"].max()),
                        "role": "uptrend", "arrow": True,
                        "label": f"+{(float(run['high'].max()) / lo - 1) * 100:.0f}% in {len(win.loc[lo_day:hi_day]) - 1} days"})
        out.append({"shape": "box", "from": day(win.index[0]), "to": day(win.index[-1]), "top": hi, "bottom": lo,
                    "role": "base", "label": f"{self.entry_channel}-day channel"})
        atr = float(ctx.atr) if ctx.atr == ctx.atr and ctx.atr else None
        if atr:
            out.append({"shape": "box", "from": day(win.index[-min(10, len(win))]), "to": day(d.index[-1]),
                        "top": hi, "bottom": hi - atr, "role": "tight", "label": "coil zone · 1 ATR"})
        out.append({"shape": "level", "from": day(win.index[-1]), "to": day(d.index[-1]), "price": hi, "role": "pivot",
                    "label": f"{self.entry_channel}-day high {hi:,.2f} — buy its break"})
        if ctx.extras.get("channel_low"):
            xl = float(ctx.extras["channel_low"])
            out.append({"shape": "level", "from": day(d.index[-min(self.exit_channel + 1, len(d))]), "to": day(d.index[-1]),
                        "price": xl, "role": "support", "label": f"exit: a close below the {self.exit_channel}-day low, {xl:,.2f}"})
        return out

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The entry and exit channels — the whole strategy is these two lines."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        if e.get("channel_high"):
            out.append({"shape": "level", "bars": self.entry_channel, "to": d, "price": float(e["channel_high"]),
                        "role": "pivot", "label": f"{self.entry_channel}-day high {e['channel_high']:g} — buy its break"})
        if e.get("channel_low"):
            out.append({"shape": "level", "bars": self.exit_channel, "to": d, "price": float(e["channel_low"]),
                        "role": "support", "label": f"{self.exit_channel}-day low {e['channel_low']:g} — exit on its break"})
        if e.get("channel_high"):
            out.append({"shape": "note", "at": d, "price": float(e["channel_high"]),
                        "text": f"Donchian entry {d}: price took out the {self.entry_channel}-day high "
                                f"{e['channel_high']:g}. No pattern claim — the channel break IS the signal; "
                                f"the exit trails the {self.exit_channel}-day low."})
        return out or super().chart_anatomy(sig)
