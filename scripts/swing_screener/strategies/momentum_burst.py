"""Momentum burst — Pradeep Bonde's (Stockbee's) 4% breakout, held for a few sessions.

Bonde's observation: stocks move in short bursts of three to five days, and a burst usually starts
from a quiet stock with one decisive up day on rising volume. This is the daily-bar version the Learn
guide (research/learn-strat-momentum-burst.md, §3, §4 and the §8 method note) defines and measures:

  * the stock is in an uptrend near its highs (the `near_highs` screen) and liquid;
  * the sessions before today were quiet: no up day of more than PRIOR_MAX_GAIN_PCT% yesterday, and
    narrower ranges than usual;
  * today is the burst: a close at least BURST_MIN_PCT% above yesterday's, on more volume than
    yesterday, in the top of the day's range;
  * buy that close, stop at the day's low, sell at the close of session HOLD_BARS after the entry.

Bonde enters intraday, as the stock crosses +4% or breaks the opening range; daily bars cannot, so
this buys the close. The exit is the shared bracket with no target and a time stop
(`backtest_args`), so the hold is a command-line flag: a variant moves it with `--time-stop-bars`.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import indicators as ind
from ..core.context import StockContext
from ..marketdata import corporate_actions
# the Near highs screen's thresholds, named here so the docs render them and the fingerprint covers them
from ..screens.criteria import (NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH, SMA200_FALLING_PCT,  # noqa: F401
                                SMA200_SLOPE_BARS)
from .base import (
    tradable_point_in_time,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
from .rs_leaders import _market_of
from .trend_pullback import round_tick

# ---- the quiet before (evaluate() reads these)
PRIOR_MAX_GAIN_PCT = 2.0          # G4: yesterday closed no more than this % above the session before
QUIET_BARS = 3                    # G5: the mean range of the QUIET_BARS sessions before today …
QUIET_REF_BARS = 20               # … is at most QUIET_MAX_RANGE_FRAC × the mean of the QUIET_REF_BARS before today
QUIET_MAX_RANGE_FRAC = 1.0        # (a session's range: high − low, as a fraction of its close)

# ---- the burst (evaluate() reads these)
BURST_MIN_PCT = 4.0               # S1: today's close at least this % above yesterday's …
BURST_VOL_VS_PRIOR = 1.0          # … on volume strictly above this × yesterday's …
CLOSE_MIN_RANGE_POS = 0.7         # … closing in the top of the day's range: (close − low) ÷ (high − low) ≥ this

# ---- market (evaluate() reads these): the index is the first of MARKET_INDEX_LABELS in the market's
# broad_index_symbols (the Nasdaq-100 ETF, the Nifty 500), else its benchmark. Kullamägi's rule.
REQUIRE_MARKET = 1                # 1: G6 is a hard gate; 0: it always passes
MKT_EMA = 20                      # the index closes above its MKT_EMA-day exponential average …
MKT_FAST_EMA = 10                 # … and its MKT_FAST_EMA-day EMA is above that MKT_EMA-day one
MARKET_INDEX_LABELS = ("QQQ", "NIFTY500")

# ---- after evaluate() (classify(), the plan and the backtest's exit read these)
MIN_STOP_PCT = 1.0                # a stop closer than this % below the entry is not bought
NOMINAL_TARGET_R = 3              # a target for the plan's R column only; the backtest has no target
HOLD_BARS = 5                     # sold at the close of this session after the entry (backtest_args)

S1 = "S1"   # today is a burst
W1 = "W1"   # the burst's volume is below its 50-day average


class MomentumBurstStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-31",
         "v1: the Learn guide's daily-bar version of Bonde's momentum burst. An uptrend near the highs (Near "
         "highs screen), a quiet yesterday (up at most {PRIOR_MAX_GAIN_PCT}%, narrow ranges), then a close "
         "{BURST_MIN_PCT}%+ up on more volume than yesterday, near the high. Bought at that close, stop at the "
         "day's low, sold at the close of session {HOLD_BARS}."),
    )
    key = "momentum_burst"
    name = "Momentum burst"
    description = (
        "Bonde's 4% breakout: a quiet stock in an uptrend has one decisive up day on rising volume; buy that "
        "close with the stop at the day's low and hold a few sessions."
    )
    style = "breakout"
    horizon = "swing"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6")
    screen_key = "near_highs"
    screen_gates = {"G1": "H1", "G2": "H2", "G3": "H3"}
    watch_codes = (W1,)
    setup_codes = (S1,)
    setup_names = {S1: "Momentum burst"}
    gate_titles = {
        "G1": "Above the 200-day", "G2": "200-day not falling", "G3": "Near the 52-week high",
        "G4": "Not already moving", "G5": "Quiet ranges before", "G6": "Market uptrend",
    }
    nominal_target = True
    min_bars = 210

    needs_ctx_extras = True
    extra_columns = ("burst_pct", "vol_vs_prior", "vol_vs_avg", "close_pos", "prior_gain_pct",
                     "quiet_range_frac")
    extra_numeric_columns = extra_columns
    # HOLD_BARS is not exempt: it is read at import, into backtest_args, so a `--const` could not move it
    signal_exempt_consts = ("MIN_STOP_PCT", "NOMINAL_TARGET_R")

    thesis = (
        "Stocks do not trend smoothly; they move in short bursts and rest in between. A burst that starts from a "
        "quiet stock, with one decisive up day on rising volume, tends to carry on for a few more days before it "
        "rests again. Buying the first day and selling a few days later captures that continuation; a stop at "
        "the burst day's low makes the many failures small. The edge, if any, is a small average gain repeated "
        "over many trades."
    )
    how_it_works = (
        "**The idea.** Bonde (Stockbee): momentum bursts of three to five days, started by a 4% up day from a "
        "quiet stock. This is the daily-bar version of the Learn guide's rules.",
        "**Qualify (the Near highs screen).** The close is above the 200-day average (G1), the 200-day is not "
        "falling (G2), and the close is within {NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH}% of the 52-week high (G3).",
        "**The quiet before.** Yesterday closed no more than {PRIOR_MAX_GAIN_PCT}% above the session before it "
        "(G4), and the {QUIET_BARS} sessions before today had narrower ranges, on average, than the "
        "{QUIET_REF_BARS} before today (G5).",
        "**The market.** The index (Nasdaq-100 in the US, Nifty 500 in India) closes above its {MKT_EMA}-day "
        "exponential average, and its {MKT_FAST_EMA}-day EMA is above the {MKT_EMA}-day (G6).",
        "**Signal and buy.** S1: today closes at least {BURST_MIN_PCT}% above yesterday, on more volume than "
        "yesterday, closing at least {CLOSE_MIN_RANGE_POS} of the way from the day's low to its high. Buy at "
        "that close. The stop is today's low; the trade is skipped if that is less than {MIN_STOP_PCT}% below.",
        "**Manage.** Sell at the stop (or the open, if it gaps through), or at the close of session "
        "{HOLD_BARS} after the entry. Nothing else.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: every gate passing, S1, and a stop at least "
        "{MIN_STOP_PCT}% away. Ties between same-day signals go to the stronger 12-1 month momentum.",
    )
    caveats = (
        "**Daily bars, not his entry.** Bonde buys intraday, as the stock crosses its burst threshold or breaks "
        "its opening range, often with the stop at that day's low so far. Daily bars cannot see that: this buys "
        "the close of a day that is already up {BURST_MIN_PCT}% or more, with the whole day's range under it, so "
        "the stop is wider and part of the burst is already gone. Results here say nothing either way about the "
        "intraday method.",
        "**Survivorship.** The universe is today's stock lists. Stocks that burst and then collapsed into a "
        "delisting are missing, which flatters the result.",
        "**India price bands not modelled.** A burst that locks at the upper band cannot be bought at the close, "
        "and a failure that locks at the lower band cannot be sold at the stop. The backtest fills both. Many "
        "Indian small caps have 5% or 10% bands, so a 4% burst can sit right under a lock.",
        "**Liquidity floor, not his.** Bonde scans stocks above $3 trading 100,000 shares or more. Every strategy "
        "here applies the market's common floor instead, on the 20-day average of close × volume (Minimum "
        "liquidity, ₹50 crore / $10m today), and no price floor on split-adjusted history. The universe is "
        "narrower and more liquid than his.",
        "**An uptrend he does not always require.** Bonde trades bursts in any liquid stock and ranks them by "
        "his own reading. This version takes only stocks in the Near highs screen, the shelf's uptrend filter, "
        "because the setup was described as \"strong trend + tight price action + defined risk\".",
        "**The guide's own measurement.** Its daily-bar event study is the reference for what to expect; read "
        "it before reading a backtest result.",
        "**Fills at the stop.** On a day that does not gap through it, the stop fills at its price. On a stock "
        "that has just moved 4% the real fill is often worse.",
        "**Run it with its exit flags.** `--no-target --time-stop-bars {HOLD_BARS}` (the page's backtest command "
        "adds them). Without them the default bracket sells everything at the nominal target. HOLD_BARS only "
        "documents the flag: a hold variant changes `--time-stop-bars`, not the constant.",
        "**The fill session is never checked.** The entry is the burst session's close, so its stop and exits "
        "are first tested on the next session.",
        "**No results rule.** Many bursts are results days; this does not know results dates and holds through "
        "the next ones.",
        corporate_actions.CAVEAT_TRADED,
    )

    status = (
        "MEASURED, OPTIMISE STAGE ONLY (2013-2021, IN-SAMPLE) -- AND IT FAILS ITS OWN TEST IN BOTH MARKETS. The "
        "rules were fixed from the Learn guide's definition before its event study was run, and not changed "
        "after it. Pass criterion, set before any backtest result, judged per market: in the optimise stage the "
        "base rules beat the market's benchmark CAGR (positive excess) AND make a positive average R after "
        "costs. A market that passes may go to one verify run; one that fails does not, so neither goes to "
        "verify (none has been run). v1.0 base rules, optimise stage: US -2.15% CAGR, excess -16.16 points a "
        "year, max drawdown -61.8%, Sharpe -0.01, 2,546 trades, average R -0.005; India 3.68% CAGR, excess "
        "-9.86 (-17.37 at the standard India cost), max drawdown -32.5%, Sharpe 0.35, 1,127 trades, average R "
        "+0.058. Variants, optimise stage, measured beside the base and never a substitute for it: a 10-session "
        "hold (`--time-stop-bars 10`) US excess -6.73, India -8.90; selling on a close below the 20-day average "
        "(`--exit-mode ma --ma-col sma20 --time-stop-bars 250`) US -14.47, India +3.48 (17.02% CAGR, max "
        "drawdown -27.3%, Sharpe 1.02) -- but -0.62 at the standard India cost, in-sample, and a changed exit "
        "is a new rule set to be judged on its own. The up-front variants, a 3-session hold "
        "(`--time-stop-bars 3`) and a 5% burst (BURST_MIN_PCT=5), have not been run yet."
    )
    gate_docs = {
        "G1": (
            "The close is above the 200-day simple average (the Near highs screen's H1).\n\n"
            "- **Fails:** a close at or below it, or no 200-day yet."
        ),
        "G2": (
            "The 200-day is not falling (the Near highs screen's H2).\n\n"
            "- **Test:** it is not more than {SMA200_FALLING_PCT}% below its value {SMA200_SLOPE_BARS} sessions ago."
        ),
        "G3": (
            "Near the highs (the Near highs screen's H3).\n\n"
            "- **Test:** the close is within {NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH}% of the 52-week high (the highest "
            "high of the last 252 sessions, today included).\n\n"
            "Together G1–G3 are the uptrend: bursts are traded with the trend."
        ),
        "G4": (
            "Not already moving.\n\n"
            "- **Test:** yesterday's close is at most {PRIOR_MAX_GAIN_PCT}% above the close of the session before.\n"
            "- **Fails:** a bigger up day yesterday, so today is the second day of a move, not the first.\n\n"
            "Bonde buys the first day of a burst; by the second or third day most of it is gone."
        ),
        "G5": (
            "Quiet before the burst.\n\n"
            "- **Range:** a session's high minus its low, as a fraction of its close.\n"
            "- **Test:** the mean range of the {QUIET_BARS} sessions before today is at most "
            "{QUIET_MAX_RANGE_FRAC} × the mean range of the {QUIET_REF_BARS} sessions before today.\n"
            "- **Fails:** wider-than-usual days just before, or too little history.\n\n"
            "The burst should come out of contraction: narrow days, then one wide up day."
        ),
        "G6": (
            "The market is in a short-term uptrend.\n\n"
            "- **Index:** the Nasdaq-100 (QQQ) in the US, the Nifty 500 in India; a market whose config lists "
            "neither uses its benchmark.\n"
            "- **Test:** today the index closes above its {MKT_EMA}-day exponential average, and its "
            "{MKT_FAST_EMA}-day EMA is above the {MKT_EMA}-day.\n"
            "- **Off switch:** with REQUIRE_MARKET = 0 (now {REQUIRE_MARKET}) the gate always passes.\n\n"
            "The same test as the Kullamägi breakout's, so the two short-term strategies share a market rule."
        ),
    }
    watch_docs = {
        W1: (
            "The burst's volume is below its 50-day average.\n\n"
            "- **Test:** today's volume is under the 50-day simple average of volume.\n"
            "- **Never blocks:** S1 needs only more volume than yesterday, Bonde's rule. Above-average volume is "
            "the stronger version; the flag lets a reader compare the two."
        ),
    }
    setup_docs = {
        S1: (
            "Today is a momentum burst.\n\n"
            "- **Gain:** today's close is at least {BURST_MIN_PCT}% above yesterday's.\n"
            "- **Volume:** today's volume is strictly above {BURST_VOL_VS_PRIOR} × yesterday's.\n"
            "- **Close near the high:** (close − low) ÷ (high − low) is at least {CLOSE_MIN_RANGE_POS}.\n"
            "- **Signal:** the setup is the entry signal (setup quality 2)."
        ),
    }
    entry_rules = (
        "Signal. S1 with every gate passing and a stop at least {MIN_STOP_PCT}% away, graded TRADE - HIGH "
        "CONFIDENCE.",
        "Order. Buy at the burst session's close (backtest: a close order filled that session, plus slippage). "
        "This is the daily-bar stand-in for his intraday entry.",
        "One position per stock (backtest). A signal in a stock already held is ignored.",
    )
    stop_rules = (
        "Where it goes. The burst session's low, rounded down to the tick. It defines 1R.",
        "How close is too close. A stop less than {MIN_STOP_PCT}% below the entry is WATCH - WAIT live and not "
        "bought in the backtest: a gap-up day with a tiny range leaves no room.",
        "How it sells (backtest). The first session whose low touches it sells at the stop, or at the open if it "
        "opened below it.",
        "It never moves.",
    )
    target_rules = (
        "There is no sell order at the target. The target is entry + {NOMINAL_TARGET_R} R, so that the plan has an "
        "R column. The backtest runs with `--no-target`.",
    )
    exit_rules = (
        "Each session after the entry, in this order (backtest, bracket mode with `--no-target --time-stop-bars "
        "{HOLD_BARS}`):",
        "1. The stop: the position sells at the stop, or at the open if the stock gapped through it.",
        "2. The time limit: at the close of session {HOLD_BARS} after the entry, the position sells at that close.",
        "Live, the screen shows the setup; nothing manages an open position.",
        "No other exits. A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped at Max position "
        "size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots. At most Position cap positions at once. A close order with no free slot is dropped.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "No price floor on split-adjusted history and no results rule.",
        "Market regime. The market test is gate G6; the shared risk-off downgrade is not applied on top of it.",
    )
    regime_note = (
        "No downgrade. The market test is this strategy's own hard gate G6, so a risk-off market is already an "
        "AVOID; the shared market-regime downgrade is not applied on top of it."
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, today is a burst (S1), the stop is at least {MIN_STOP_PCT}% "
                                 "below the entry, and one share fits the account. The only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Not used.",
        "WATCH_WAIT": "S1 fired but the stop is under {MIN_STOP_PCT}% away, or not even one share fits the account.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number.",
    }
    param_docs = (
        ("Near-high ceiling", "NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH", "G3: how far below the 52-week high, %, at most "
                                                                   "(Near highs screen)."),
        ("200-day falling", "SMA200_FALLING_PCT", "G2: the 200-day fails if this % below its earlier value."),
        ("200-day slope window", "SMA200_SLOPE_BARS", "G2: sessions back for that comparison."),
        ("Yesterday's gain", "PRIOR_MAX_GAIN_PCT", "G4: yesterday's close-to-close gain, %, at most."),
        ("Quiet sessions", "QUIET_BARS", "G5: sessions before today whose ranges are averaged."),
        ("Reference sessions", "QUIET_REF_BARS", "G5: sessions before today they are compared with."),
        ("Quiet ratio", "QUIET_MAX_RANGE_FRAC", "G5: the quiet mean range at most this × the reference mean."),
        ("Burst size", "BURST_MIN_PCT", "S1: today's close-to-close gain, %, at least."),
        ("Burst volume", "BURST_VOL_VS_PRIOR", "S1: today's volume above this × yesterday's."),
        ("Close in range", "CLOSE_MIN_RANGE_POS", "S1: where the close sits in the day's range, 0 low to 1 high."),
        ("Market gate", "REQUIRE_MARKET", "1: G6 is a hard gate; 0: it always passes."),
        ("Index EMA", "MKT_EMA", "G6: the index closes above this exponential average."),
        ("Index fast EMA", "MKT_FAST_EMA", "G6: this EMA must be above the slower one."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (the --time-stop-bars flag)."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct", "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "The stop is rounded down to this increment."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = f"--no-target --time-stop-bars {HOLD_BARS} --rank-by setup_momentum"

    # ---------- market ----------

    _market_cache: dict = {}

    @classmethod
    def _market_ok(cls, market_key: str):
        """Per date: does the index pass G6? Cached per market and per (MKT_EMA, MKT_FAST_EMA), so a
        `--const` variant of either is not served the base series. The averages are causal."""
        k = (market_key, MKT_EMA, MKT_FAST_EMA)
        if k not in cls._market_cache:
            from ..config import MARKETS
            from ..marketdata import cache
            cfg = MARKETS[market_key]
            label = next((x for x in MARKET_INDEX_LABELS if x in cfg.broad_index_symbols), None)
            ticker = cfg.broad_index_symbols[label] if label else cfg.benchmark_ticker
            b = cache.load_cached(market_key, ticker)
            if b is None or b.empty:
                cls._market_cache[k] = None
            else:
                c = b["close"].astype(float)
                slow, fast = ind.ema(c, MKT_EMA), ind.ema(c, MKT_FAST_EMA)
                cls._market_cache[k] = (c > slow) & (fast > slow)
        return cls._market_cache[k]

    def market_risk_off(self, market_key: str, default: bool) -> bool:
        """The market test is gate G6, so the shared downgrade is not applied on top of it."""
        return False

    # ---------- screen ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        d = ctx.daily
        self.apply_screen(ctx, result)
        e = ctx.extras
        n = len(d)
        c = d["close"].astype(float)

        if n < 3:
            result.fail("G4", "insufficient history")
        else:
            prior_gain = (float(c.iloc[-2]) / float(c.iloc[-3]) - 1) * 100
            e["prior_gain_pct"] = prior_gain
            if prior_gain <= PRIOR_MAX_GAIN_PCT:
                result.ok("G4", f"yesterday {prior_gain:+.1f}%")
            else:
                result.fail("G4", f"yesterday already up {prior_gain:.1f}% (> {PRIOR_MAX_GAIN_PCT}%)")

        if n < QUIET_REF_BARS + 1:
            result.fail("G5", "insufficient history for the ranges")
        else:
            rng = ((d["high"] - d["low"]).astype(float) / c).iloc[-QUIET_REF_BARS - 1:-1]
            frac = float(rng.iloc[-QUIET_BARS:].mean()) / float(rng.mean()) if rng.mean() > 0 else float("nan")
            e["quiet_range_frac"] = frac
            if frac <= QUIET_MAX_RANGE_FRAC:
                result.ok("G5", f"recent ranges {frac:.2f}× the {QUIET_REF_BARS}-session mean")
            else:
                result.fail("G5", f"recent ranges {frac:.2f}× the {QUIET_REF_BARS}-session mean "
                                  f"(> {QUIET_MAX_RANGE_FRAC})")

        if REQUIRE_MARKET:
            ok = self._market_ok(_market_of(ctx.symbol))
            if ok is None:
                result.fail("G6", "no index history")
            elif bool(ok.asof(d.index[-1])):
                result.ok("G6", "")
            else:
                result.fail("G6", "index not in a short-term uptrend")
        else:
            result.ok("G6", "market gate off")

        burst = False
        if n >= 2:
            last, prev = d.iloc[-1], d.iloc[-2]
            hi, lo, close = float(last["high"]), float(last["low"]), float(last["close"])
            pct = (close / float(prev["close"]) - 1) * 100
            vprev = float(prev["volume"])
            pos = (close - lo) / (hi - lo) if hi > lo else float("nan")
            e["burst_pct"], e["close_pos"] = pct, pos
            e["vol_vs_prior"] = float(last["volume"]) / vprev if vprev > 0 else float("nan")
            burst = (pct >= BURST_MIN_PCT and float(last["volume"]) > BURST_VOL_VS_PRIOR * vprev
                     and pos >= CLOSE_MIN_RANGE_POS)
            avg = last.get("vol_sma50")
            e["vol_vs_avg"] = float(last["volume"]) / float(avg) if avg and avg == avg else float("nan")
            low_vol = bool(e["vol_vs_avg"] < 1)   # NaN (no average yet) compares False
            result.watch_flags[W1] = low_vol
            if low_vol:
                result.watch_notes[W1] = f"volume {e['vol_vs_avg']:.2f}× its 50-day average"
        result.setups[S1] = bool(burst)
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
        entry = float(ctx.close)
        stop = round_tick(float(ctx.last["low"]), cfg.tick_size, "down")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(
            plan="MB", setup=S1, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R if risk > 0 else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"burst {ctx.extras.get('burst_pct', 0):+.1f}% on rising volume")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        return {"order": "close"}

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
        elif risk_pct < MIN_STOP_PCT:
            label, reason = "WATCH_WAIT", f"stop only {risk_pct:.1f}% away (< {MIN_STOP_PCT}%)"
        else:
            label, reason = "TRADE_HIGH_CONFIDENCE", f"momentum burst; stop {risk_pct:.1f}% away"
        return Decision(LABELS[label], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 3) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def setup_shapes(self, ctx: StockContext, result: StrategyResult, sig: dict) -> list[dict]:
        """For the chart's Trade setups layer: the {QUIET_BARS} quiet sessions G5 measured (boxed), the burst
        day itself, and the line {BURST_MIN_PCT}% over yesterday's close that S1's close had to clear -- the bars
        evaluate() reads. The plan's buy (the close) and stop (the day's low) are drawn by the layer."""
        d = ctx.daily
        if len(d) < QUIET_BARS + 2:
            return self.chart_anatomy(sig)
        day = lambda ts: str(pd.Timestamp(ts).date())
        e = ctx.extras
        quiet, last = d.iloc[-QUIET_BARS - 1:-1], d.iloc[-1]
        prev_c = float(d["close"].iloc[-2])
        frac = e.get("quiet_range_frac")
        out = [{"shape": "box", "from": day(quiet.index[0]), "to": day(quiet.index[-1]),
                "top": float(quiet["high"].max()), "bottom": float(quiet["low"].min()), "role": "base",
                "label": f"quiet: {QUIET_BARS} sessions" + (f", ranges {frac:.2f}× the {QUIET_REF_BARS}-session mean"
                                                          if frac is not None and frac == frac else "")},
               {"shape": "level", "from": day(quiet.index[0]), "to": day(d.index[-1]), "price": prev_c * (1 + BURST_MIN_PCT / 100),
                "role": "pivot", "label": f"+{BURST_MIN_PCT:g}% over yesterday's close, {prev_c * (1 + BURST_MIN_PCT / 100):,.2f}"},
               {"shape": "box", "from": day(d.index[-1]), "to": day(d.index[-1]), "top": float(last["high"]),
                "bottom": float(last["low"]), "role": "tight",
                "label": (f"burst {e['burst_pct']:+.1f}% on {e.get('vol_vs_prior') or 0:.1f}× yesterday's volume, "
                          f"closing at {(e.get('close_pos') or 0) * 100:.0f}% of its range")
                         if e.get("burst_pct") is not None else "burst day"}]
        return out + [s for s in self.chart_anatomy(sig) if s.get("shape") == "note"]

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The burst day and its stop."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        if e.get("burst_pct") is not None:
            out.append({"shape": "note", "at": d,
                        "text": f"Momentum burst {d}: {e.get('burst_pct') or 0:+.1f}% on "
                                f"{e.get('vol_vs_prior') or 0:.1f}× yesterday's volume; bought the close, stop at "
                                f"the day's low, sold after {HOLD_BARS} sessions."})
        return out or super().chart_anatomy(sig)
