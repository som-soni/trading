"""100-EMA trend — a long weekly uptrend dips under its daily 100 EMA, and the buy is the close back above it.

The rules are Hitesh Somani's second swing setup (research/video-strategy-notes.md §5, "two swing setups",
setup 2), on daily bars only; his faster version, timed on the 1-hour chart, needs intraday data that is not
stored:

  * the weekly close above its 100-week EMA (G2), and the weekly trend 2 years old or more: every weekly
    close of the last TREND_WEEKS above that EMA, and the EMA higher than TREND_WEEKS weeks ago (G3);
  * the Above the 200-day screen's A1 as the shared floor (G1), and his "Nifty 500 only" read as the
    TOP_N most-traded stocks on the signal date (`--top-dollar-volume`, both markets);
  * after one or more closes at or under the daily 100 EMA, today's close is back above it (S1);
  * buy-stop one tick over that crossing candle's high; stop under the dip's low (STOP_AT_DIP_LOW);
  * no target. The backtest sells only when a close below the 100 EMA is followed by a session that trades
    under that candle's low (`--exit-mode ma_low --ma-col ema100`): a close below alone is not an exit.

Re-entry is allowed: once out, the next fresh close back above the EMA is a new signal.

How it differs from `ema_pullback`: that strategy buys the first touch of a short (21-day) EMA in a strong,
rising stack and sells on the first close under it. This one buys the reclaim of a slow EMA after the dip has
gone under it, in a trend measured on the weekly chart, and gives the trade the room of a confirmed break.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import indicators as ind
from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import (
    tradable_point_in_time,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .trend_pullback import round_tick

# ---- the weekly trend (evaluate() reads these)
WEEKLY_EMA = 100                  # the weekly close is above this EMA of weekly closes (G2)
TREND_WEEKS = 104                 # G3: every weekly close of this many weeks above that EMA (2 years) …
TREND_MIN_ABOVE_PCT = 100         # … or at least this % of them (100: every one; the video's examples)

# ---- the daily cross (evaluate() reads these)
DAILY_EMA = 100                   # the EMA the dip goes under and the close crosses back above (S1);
                                  #   the backtest's exit line too (--ma-col ema100)

# ---- the universe (the backtest's --top-dollar-volume). Read at import into backtest_args, so it is NOT
# signal-exempt (tests/test_signal_exempt): a --const TOP_N run would not change the flag anyway
TOP_N = 500                       # "Nifty 500 only": the this-many most-traded stocks on the signal date

# ---- the order and the stop (build_plans()/signal_meta() read these, after evaluate())
TRIGGER_WINDOW = 5                # the buy-stop rests this many sessions
STOP_AT_DIP_LOW = 1               # 1: the stop is under the dip's lowest low; 0: under the crossing candle's low
NOMINAL_TARGET_R = 10             # a far target for the plan's R column only; the backtest has no target

S1 = "S1"   # the daily close crossed back above the 100 EMA after a dip under it


def _ema(d: pd.DataFrame, n: int) -> pd.Series:
    """The n-day EMA of closes: enrich_daily's column when it has one, else computed the same way."""
    col = f"ema{n}"
    return d[col] if col in d.columns else ind.ema(d["close"].astype(float), n)


class Ema100TrendStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-02",
         "v1: Hitesh Somani's 100 EMA trend setup, daily bars only. The weekly close above its "
         "{WEEKLY_EMA}-week EMA, every weekly close of the last {TREND_WEEKS} above it and the EMA rising over "
         "them; a daily close back above the {DAILY_EMA}-day EMA after a dip under it; buy-stop over the crossing "
         "candle's high for {TRIGGER_WINDOW} sessions, stop under the dip's low; no target, sold when a close "
         "under the EMA is followed by a break of that candle's low (new exit mode ma_low). The {TOP_N} "
         "most-traded stocks only."),
    )
    key = "ema100_trend"
    name = "100-EMA trend"
    description = (
        "A weekly uptrend of two years or more dips under its daily {DAILY_EMA} EMA; buy over the high of the "
        "close back above it, stop under the dip, no target: sell only on a close under the EMA whose low then breaks."
    )
    style = "trend"
    gate_codes = ("G1", "G2", "G3")
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    watch_codes = ()
    setup_codes = (S1,)
    setup_names = {S1: "Close back above the 100 EMA"}
    gate_titles = {
        "G1": "Above the 200-day", "G2": "Weekly close above its {WEEKLY_EMA}-week EMA",
        "G3": "A {TREND_WEEKS}-week weekly uptrend",
    }
    nominal_target = True
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("ema_daily", "setup_high", "setup_low", "dip_low", "dip_bars", "weekly_close",
                     "weekly_ema", "weeks_above_pct")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = ("TRIGGER_WINDOW", "STOP_AT_DIP_LOW", "NOMINAL_TARGET_R")

    thesis = (
        "A stock that has held above a slow weekly average for years is in a trend that big holders keep "
        "buying. A dip under the daily 100 EMA is profit booking, not a change of trend, and the close back above "
        "it is the sign that buyers have returned; buying over that candle's high asks the next session to agree. "
        "The exit is deliberately slow — a close under the EMA has to be confirmed by a break of its low — so a "
        "winner can run for months and the system's return comes from a few large trends."
    )
    how_it_works = (
        "**The idea.** Hitesh Somani's 100 EMA trend setup, as stated in his swing video, on daily bars. His "
        "faster version, timed on the 1-hour chart, is not tested: intraday bars are not stored.",
        "**The universe.** His \"Nifty 500 only, for liquidity\" is read as the {TOP_N} most-traded stocks by "
        "50-day traded value on the signal date, in both markets (`--top-dollar-volume {TOP_N}`): point in time, "
        "where today's index list would not be.",
        "**Qualify.** The close is above the 200-day average (G1, the Above the 200-day screen), the weekly close "
        "is above its {WEEKLY_EMA}-week EMA (G2), and every one of the last {TREND_WEEKS} weekly closes was above "
        "that EMA, which is higher than {TREND_WEEKS} weeks ago (G3) — a weekly uptrend of two years or more.",
        "**The setup (S1).** Yesterday's close was at or under the {DAILY_EMA}-day EMA and today's close is "
        "above it: the dip is over.",
        "**Buy.** A buy-stop one tick over the crossing candle's high, resting {TRIGGER_WINDOW} sessions; a close "
        "back under that day's EMA value cancels it. The stop is one tick under the dip's lowest low "
        "(STOP_AT_DIP_LOW = {STOP_AT_DIP_LOW}).",
        "**Sell.** No target. A close under the {DAILY_EMA}-day EMA arms the exit; the next session sells if it "
        "trades under that candle's low. A close back above the EMA disarms it. Or the stop.",
        "**Again.** Once out, the next close back above the EMA after a dip is a new trade.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: every gate and S1. Ties between same-day "
        "signals go to the stronger 12-1 month momentum.",
    )
    caveats = (
        "**Not yet measured.** No backtest has judged it (see Status).",
        "**The video's figures are unverified.** His examples are charts he chose; no win rate or return was "
        "given, and none is assumed here.",
        "**Choices the video did not make.** The stop (the dip's low, not the crossing candle's), the buy-stop's "
        "{TRIGGER_WINDOW}-session window, the reading of \"2-year-plus uptrend\" as every weekly close of "
        "{TREND_WEEKS} weeks above a rising EMA, and the {TOP_N}-name universe are this strategy's, fixed before "
        "the first run. G1 (above the 200-day) is the shared screen floor, not his rule; in a stock two years above "
        "its 100-week EMA it rarely binds at a reclaim of the 100-day.",
        "**The weekly bar is the week so far.** Mid-week, the weekly close is today's close: what the weekly chart "
        "shows on that day, never a week not yet finished.",
        "**No market filter and no results rule.** The video gives neither, so neither is applied: the strategy "
        "buys in falling markets and into results.",
        "**A wide first stop.** A long dip puts the stop far under the entry. The position is sized on that risk, "
        "so a long dip buys fewer shares; R is measured against it, so a typical loss on the EMA exit is a "
        "fraction of 1R.",
        "**Survivorship.** The universe is today's stock lists. Stocks whose trend ended in a collapse and a "
        "delisting are missing, which flatters every trend strategy, this one included.",
        "**India price bands not modelled.** A stop under a lower-band close cannot fill until the band opens.",
        "**Run it with its exit flags.** `--exit-mode ma_low --ma-col ema100 --no-target --top-dollar-volume "
        "{TOP_N}` (the page's backtest command adds them). Without them the default bracket sells at the nominal "
        "target and the universe is every stock above the liquidity floor.",
        corporate_actions.CAVEAT_TRADED,
    )

    status = (
        "NOT YET MEASURED. Stage: optimise (2013-2021, in-sample); verify has not been run. Reported against the "
        "market's index at the same exposure, in both markets; no rule is tuned on these years."
    )
    gate_docs = {
        "G1": (
            "The close is above the 200-day average (the Above the 200-day screen's A1).\n\n"
            "- **Fails:** the close at or under it, or no 200-day yet.\n\n"
            "The shared long-term floor; not in the video."
        ),
        "G2": (
            "The weekly close is above its {WEEKLY_EMA}-week EMA.\n\n"
            "- **Test:** this week's close so far (today's close) above the {WEEKLY_EMA}-week EMA of weekly closes.\n"
            "- **Fails:** at or under it, or fewer than {WEEKLY_EMA} weeks of history."
        ),
        "G3": (
            "A weekly uptrend of two years or more.\n\n"
            "- **Test:** at least {TREND_MIN_ABOVE_PCT}% of the last {TREND_WEEKS} weekly closes, this week's "
            "included, above that week's {WEEKLY_EMA}-week EMA, and the EMA higher than {TREND_WEEKS} weeks ago.\n"
            "- **Fails:** a weekly close under the EMA in that window, a flat or falling EMA, or too little "
            "history ({WEEKLY_EMA} + {TREND_WEEKS} weeks).\n\n"
            "The video's examples had held above the line for 2 to 6 years."
        ),
    }
    watch_docs = {}
    setup_docs = {
        S1: (
            "The daily close crosses back above the {DAILY_EMA}-day EMA after a dip under it.\n\n"
            "- **Dip:** yesterday's close at or under yesterday's {DAILY_EMA}-day EMA (one close is enough).\n"
            "- **Cross:** today's close above today's {DAILY_EMA}-day EMA.\n"
            "- **Signal:** the crossing candle. The entry is a buy-stop over its high (setup quality 2)."
        ),
    }
    entry_rules = (
        "Signal. S1 with every gate passing, graded TRADE - HIGH CONFIDENCE.",
        "Universe (backtest). Only signals in the {TOP_N} most-traded stocks by 50-day traded value that day "
        "(`--top-dollar-volume {TOP_N}`).",
        "Order. A buy-stop one tick over the crossing candle's high, resting {TRIGGER_WINDOW} sessions from the "
        "next. An open above it fills at the open.",
        "Cancelled (backtest) when the window ends, when a low reaches the stop before it fills, or on a close "
        "under the crossing day's {DAILY_EMA}-day EMA.",
        "One position per stock (backtest). A signal in a stock already held, or with an order resting, is "
        "ignored; after an exit the next cross is a new signal.",
    )
    stop_rules = (
        "Where it goes. With STOP_AT_DIP_LOW = 1 (now {STOP_AT_DIP_LOW}), one tick under the dip's lowest low: the "
        "run of closes at or under the EMA before the cross, and the crossing candle. With 0, one tick under the "
        "crossing candle's low. It defines 1R.",
        "Why the dip's low. The video says only \"under the low\"; the dip's low is the level that, once broken, "
        "says the profit booking was more than that. The crossing candle's low is tighter and is the variant.",
        "How it sells (backtest). The first session whose low touches it sells at the stop, or at the open if it "
        "opened below it.",
        "It never moves.",
    )
    target_rules = (
        "None. The plan carries entry + {NOMINAL_TARGET_R} R only so that it has an R column; the backtest runs "
        "with `--no-target`.",
    )
    exit_rules = (
        "On the fill session, the stop only: a session that triggers the buy-stop and also trades down to the "
        "stop sells at the stop (the bar does not say which came first, so the stop wins the tie).",
        "Each session after the fill, in this order (backtest, `--exit-mode ma_low --ma-col ema100`):",
        "1. The stop: sells at the stop, or at the open if the stock gapped through it.",
        "2. The confirmed break: if the previous session (the fill session included) closed under its "
        "{DAILY_EMA}-day EMA and this session trades under that candle's low, everything sells at that low, or at "
        "the open if it opened under it.",
        "A close under the EMA alone never sells; a close back above it cancels the armed exit, and each new close "
        "under it arms at its own low.",
        "Live, the screen shows the setup; nothing manages an open position.",
        "No other exits. A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped at Max "
        "position size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots. At most Position cap positions at once. A triggered order with no free slot keeps resting.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14; G2 and G3 need {WEEKLY_EMA} + "
        "{TREND_WEEKS} weeks.",
        "No price floor on split-adjusted history.",
        "Market regime. None: the video gives no market rule, and the shared risk-off downgrade is not applied.",
    )
    regime_note = (
        "No downgrade. The video gives no market rule, so a risk-off market does not change the decision; the "
        "backtest runs without a market filter too."
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, today's close crossed back above the {DAILY_EMA}-day EMA (S1) "
                                 "and one share fits the account. The only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Not used: the setup is already a buy-stop order.",
        "WATCH_WAIT": "S1 fired but not even one share fits the account.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number.",
    }
    param_docs = (
        ("Weekly EMA", "WEEKLY_EMA", "G2, G3: the EMA of weekly closes the trend is read against."),
        ("Trend length", "TREND_WEEKS", "G3: weeks the weekly close must have held above the EMA."),
        ("Weeks above", "TREND_MIN_ABOVE_PCT", "G3: % of those weekly closes that must be above it."),
        ("Daily EMA", "DAILY_EMA", "S1 and the exit: the EMA the dip goes under and the close reclaims."),
        ("Universe", "TOP_N", "Backtest: only the this-many most-traded stocks on the signal date."),
        ("Trigger window", "TRIGGER_WINDOW", "Sessions the buy-stop rests."),
        ("Stop at the dip's low", "STOP_AT_DIP_LOW", "1: under the dip's lowest low; 0: under the crossing candle's low."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct", "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "The buy-stop is rounded up and the stop down to this increment."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = (f"--exit-mode ma_low --ma-col ema{DAILY_EMA} --no-target --top-dollar-volume {TOP_N} "
                     "--rank-by setup_momentum")

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """The video gives no market rule, so the shared downgrade is not applied."""
        return False

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        # G1 and S1's cross side on one row
        s200, e = last.get("sma200"), last.get(f"ema{DAILY_EMA}")
        if pd.isna(s200) or not last["close"] > s200:
            return False, "close not above the 200-day"
        if e is not None and not pd.isna(e) and not last["close"] > e:
            return False, f"close not above the {DAILY_EMA}-day EMA"
        return True, "passed"

    def prefilter_mask(self, cfg: MarketConfig, enriched_daily) -> "pd.Series":
        """The row test plus the cross itself (yesterday's close at or under the EMA), vectorised, so the
        backtest evaluates only crossing days. S1 tests the same cross again in evaluate()."""
        d = enriched_daily
        if d is None or d.empty:
            return pd.Series(dtype=bool)
        close = d["close"].astype(float)
        ema = _ema(d, DAILY_EMA)
        ok = (close > d["sma200"]) & (close > ema) & (close.shift(1) <= ema.shift(1))
        ok &= d["atr14"].notna() & (d["atr14"] > 0)
        if cfg.screener.min_dollar_volume:
            ok &= d["dollar_vol_sma20"] >= cfg.screener.min_dollar_volume
        ok &= pd.Series(range(len(d)), index=d.index) >= 209
        return ok.fillna(False).astype(bool)

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        d = ctx.daily
        self.apply_screen(ctx, result)
        e = ctx.extras

        # G2 / G3: the weekly trend
        wc = ctx.weekly["close"].astype(float)
        wema = ind.ema(wc, WEEKLY_EMA)
        e["weekly_close"] = float(wc.iloc[-1]) if len(wc) else float("nan")
        e["weekly_ema"] = float(wema.iloc[-1]) if len(wema) else float("nan")
        if e["weekly_ema"] != e["weekly_ema"]:
            result.fail("G2", f"fewer than {WEEKLY_EMA} weeks of history")
        elif e["weekly_close"] > e["weekly_ema"]:
            result.ok("G2", f"weekly close {e['weekly_close']:.2f} > EMA {e['weekly_ema']:.2f}")
        else:
            result.fail("G2", f"weekly close {e['weekly_close']:.2f} at or under its {WEEKLY_EMA}-week EMA "
                              f"{e['weekly_ema']:.2f}")
        if len(wema) <= TREND_WEEKS or wema.iloc[-1 - TREND_WEEKS] != wema.iloc[-1 - TREND_WEEKS]:
            e["weeks_above_pct"] = float("nan")
            result.fail("G3", f"fewer than {WEEKLY_EMA} + {TREND_WEEKS} weeks of history")
        else:
            above = (wc.iloc[-TREND_WEEKS:] > wema.iloc[-TREND_WEEKS:]).mean() * 100
            e["weeks_above_pct"] = float(above)
            if above < TREND_MIN_ABOVE_PCT:
                result.fail("G3", f"{above:.0f}% of the last {TREND_WEEKS} weekly closes above the EMA "
                                  f"(< {TREND_MIN_ABOVE_PCT}%)")
            elif not wema.iloc[-1] > wema.iloc[-1 - TREND_WEEKS]:
                result.fail("G3", f"the {WEEKLY_EMA}-week EMA is not higher than {TREND_WEEKS} weeks ago")
            else:
                result.ok("G3", f"{above:.0f}% of {TREND_WEEKS} weekly closes above a rising EMA")

        # S1: the cross, and the dip it ends
        close = d["close"].astype(float)
        ema = _ema(d, DAILY_EMA)
        last = d.iloc[-1]
        e["ema_daily"] = float(ema.iloc[-1])
        e["setup_high"], e["setup_low"] = float(last["high"]), float(last["low"])
        crossed = (len(d) >= 2 and ema.iloc[-1] == ema.iloc[-1] and ema.iloc[-2] == ema.iloc[-2]
                   and close.iloc[-1] > ema.iloc[-1] and close.iloc[-2] <= ema.iloc[-2])
        if crossed:
            under = (close <= ema).to_numpy()
            i = len(d) - 2
            while i >= 0 and under[i]:
                i -= 1
            e["dip_bars"] = float(len(d) - 2 - i)
            e["dip_low"] = float(d["low"].iloc[i + 1:].astype(float).min())   # the dip and the crossing candle
        else:
            e["dip_bars"], e["dip_low"] = 0.0, float("nan")
        result.setups[S1] = bool(crossed)
        result.recompute_first_fail()
        return result

    def setup_quality(self, result: StrategyResult) -> float:
        return 2.0 if result.setups.get(S1) else 0.0

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        return bool(result.setups.get(S1))

    def build_plans(self, ctx: StockContext, result: StrategyResult, cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        tick = cfg.tick_size if cfg.tick_size > 0 else 0.01
        entry = round_tick(float(e["setup_high"]) + tick, cfg.tick_size, "up")
        low = float(e["dip_low"]) if STOP_AT_DIP_LOW else float(e["setup_low"])
        stop = round_tick(low - tick, cfg.tick_size, "down")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(
            plan="E100", setup=S1, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R if risk > 0 else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"closed back above the {DAILY_EMA}-day EMA {e['ema_daily']:.2f} after "
                                      f"{e['dip_bars']:.0f} sessions under it; buy over {entry:.2f}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        meta = {"expiry_bdays": TRIGGER_WINDOW}
        ema = ctx.extras.get("ema_daily")
        if ema == ema and ema:
            meta["cancel_close_below"] = float(ema)
        return meta

    # ---------- decision ----------

    def classify(self, ctx, result, plan, sizing_result, earnings_days_away, regime_downgrade_active) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID", f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)
        risk_pct = plan.risk_per_share / plan.entry * 100
        if sizing_result.too_large:
            label, reason = "WATCH_WAIT", "too large for account"
        else:
            label, reason = "TRADE_HIGH_CONFIDENCE", (f"back above the {DAILY_EMA}-day EMA in a weekly uptrend; "
                                                      f"stop {risk_pct:.1f}% away")
        return Decision(LABELS[label], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The EMA the close reclaimed, the buy-stop over the crossing candle and the dip's low under it."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        bars = int(e.get("dip_bars") or 0) + 1
        out: list[dict] = []
        if e.get("ema_daily"):
            out.append({"shape": "level", "bars": bars + 1, "to": d, "price": float(e["ema_daily"]),
                        "role": "support", "label": f"{DAILY_EMA}-day EMA {e['ema_daily']:g} — the close back above it"})
        if e.get("setup_high"):
            out.append({"shape": "level", "bars": 2, "to": d, "price": float(e["setup_high"]), "role": "pivot",
                        "label": f"crossing high {e['setup_high']:g} — a trade above it is the buy"})
        low = e.get("dip_low") if STOP_AT_DIP_LOW else e.get("setup_low")
        if low:
            out.append({"shape": "level", "bars": bars, "to": d, "price": float(low), "role": "stop",
                        "label": f"{'dip' if STOP_AT_DIP_LOW else 'crossing'} low {low:g} — the stop"})
            out.append({"shape": "note", "at": d, "price": float(low),
                        "text": f"100-EMA trend {d}: back above the {DAILY_EMA}-day EMA after "
                                f"{bars - 1} sessions under it."})
        return out or super().chart_anatomy(sig)
