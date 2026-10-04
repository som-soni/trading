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

DC01 = "DC-01"  # breakout of the entry channel
DC02 = "DC-02"  # coiled just under the channel high


class DonchianStrategy(Strategy):
    key = "donchian"
    name = "Donchian channel breakout"
    description = (
        "Classical trend following: buy an N-day high, exit on an M-day low, "
        "stop at a volatility multiple, and filter almost nothing."
    )
    gate_codes = ("N1", "N2")
    watch_codes = ("XN1", "XN2")
    setup_codes = (DC01, DC02)
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
    how_it_works = (
        "**Screen** only for price, liquidity and enough history — no trend, "
        "momentum or volatility filter.",
        "**Gate N1** requires price above its 200-day average (the one "
        "concession: this is a long-only equity book, not a long/short futures "
        "portfolio that can profit from downtrends).",
        "**Gate N2** rejects a stock already more than 1 ATR above the channel "
        "high, i.e. the breakout has run away before you could act.",
        f"**Setup DC-01** fires when the close exceeds the highest high of the "
        f"last {entry_channel} bars; DC-02 marks a coil within 1 ATR below it.",
        f"**Entry** is the channel high — where a resting buy-stop fills. "
        f"**Stop** is {stop_atr_mult:g} ATR below it (the Turtles' 2N), floored "
        f"at {min_stop_pct:g}% so a very quiet stock does not get a stop that "
        "daily noise alone would trigger.",
        f"**Exit** is a close below the {exit_channel}-day low. There is no "
        "profit target: that is the whole point.",
    )
    caveats = (
        "**NOT YET BACKTESTED** as a complete strategy. Its exit rule is the "
        "only one of eight tested that showed positive per-trade expectancy, "
        "which is why it exists — that is suggestive, not evidence.",
        "Trend following's track record is in diversified futures traded long "
        "and short. A long-only single-market equity book removes both the "
        "cross-market diversification and the short side.",
        "Expect a LOW win rate (30-40%) by design. Judge it on expectancy and "
        "the size of winners, never on hit rate.",
        "Run it with `--exit-mode donchian --no-target`; the bracket exit "
        "defeats the strategy's entire premise.",
    )

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        if cfg.screener.min_price and last["close"] < cfg.screener.min_price:
            return False, f"price {last['close']:.2f} < {cfg.screener.min_price}"
        if cfg.screener.min_dollar_volume:
            dv = last.get("dollar_vol_sma20")
            if pd.isna(dv) or dv < cfg.screener.min_dollar_volume:
                return False, f"liquidity below {cfg.screener.min_dollar_volume:,.0f}"
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

        # N1: long-only concession — don't buy breakouts under the 200-day
        sma200 = d["sma200"].iloc[-1]
        if pd.isna(sma200):
            result.fail("N1", "insufficient history for SMA200")
        elif close > sma200:
            result.ok("N1")
        else:
            result.fail("N1", "close below SMA200")

        # N2: the breakout has already run away
        if atr14 and close > ch_high + atr14:
            result.fail(
                "N2",
                f"already {(close - ch_high) / atr14:.1f} ATR above the channel high",
            )
        else:
            result.ok("N2")

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
        result.watch_flags["XN1"] = bool(thin and result.setups.get(DC01))
        if result.watch_flags["XN1"]:
            result.watch_notes["XN1"] = "breakout on below-average volume"
        # XN2: very wide stop relative to price
        risk_pct = (self.stop_atr_mult * atr14 / ctx.close * 100) if ctx.close else float("nan")
        result.watch_flags["XN2"] = bool(risk_pct == risk_pct and risk_pct > 12)
        if result.watch_flags["XN2"]:
            result.watch_notes["XN2"] = f"2 ATR stop is {risk_pct:.0f}% of price"

    def watch_cap(self, result: StrategyResult) -> str:
        caps = []
        if result.watch_flags.get("XN1"):
            caps.append("TRADE_ON_TRIGGER")
        if result.watch_flags.get("XN2"):
            caps.append("TRADE_ON_TRIGGER")
        return min(caps, key=CAP_ORDER.index) if caps else "TRADE_HIGH_CONFIDENCE"

    def setup_quality(self, result: StrategyResult) -> float:
        score = 2.0 if result.setups.get(DC01) else (1.0 if result.setups.get(DC02) else 0.0)
        if result.watch_flags.get("XN1"):
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
            for code in ("XN1", "XN2"):
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
