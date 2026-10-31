"""EMA pullback — a strong trend dips to its short EMA on quiet volume, and the buy is the turn back up.

The rules are the Learn guide's (research/learn-strat-pullback-ma.md, §3 and §4), with the trend read
the way the traders who teach this setup read it: the 10-day EMA above the 21-day EMA above the 50-day
average, all three rising. Price drifts back to the fast EMA after a fresh high, the dip is quiet, and
a buy-stop over the touching session's high waits for buyers to show up:

  * qualify through the Established uptrend screen's daily structure (U3) and slope (U4) criteria;
  * the stack, a recent 20-day closing high, a run of closes above the fast EMA, quieter volume, and
    the market index above its own 50-day (the strategy's gates);
  * the setup bar's low reaches the fast EMA and its close holds the 50-day (S1);
  * buy-stop one tick over that bar's high for TRIGGER_WINDOW sessions; stop under the pullback low;
  * the backtest sells at the first close below the fast EMA (`--exit-mode ma --ma-col ema21`).

How it differs from `trend_pullback`: that strategy buys a measured dip from a high a few sessions
ago (TC-01) or a tight continuation base, wherever the dip ends. This one only buys a dip that
reaches a rising short EMA, and trails that same line. The two share the uptrend screen, so they
will often hold the same stocks.
"""

import pandas as pd

from ..config.base import MarketConfig
from ..core import indicators as ind
from ..core.context import StockContext
from ..marketdata import corporate_actions
# the Established uptrend screen's slope thresholds (G2), named here so the docs render them and the
# fingerprint covers them
from ..screens.criteria import (SMA50_FALLING_PCT, SMA50_SLOPE_BARS, SMA200_FALLING_PCT,  # noqa: F401
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

# ---- the trend stack (evaluate() reads these). Each line must be above the next, and each must be
# higher than STACK_RISE_BARS sessions ago.
STACK_FAST_EMA = 10               # the fastest line of the stack
STACK_SLOW_EMA = 21               # … above this one …
STACK_SMA = 50                    # … above this simple average
STACK_RISE_BARS = 5               # "rising": higher than this many sessions ago

# ---- the pullback (evaluate() reads these)
FAST_EMA = 21                     # the EMA the dip must touch (and the backtest trails: --ma-col ema21)
TOUCH_TOL_PCT = 0.5               # a low up to this % above the EMA counts as a touch
RUN_LENGTH = 5                    # the first touch: this many closes before today all above the EMA
ADVANCE_LOOKBACK = 10             # a 20-day closing high within this many sessions (today included)
ADVANCE_HIGH_BARS = 20            # … the closing-high window
DRYUP_BARS = 5                    # quieter volume: the average of the last this-many sessions …
DRYUP_RATIO = 1.0                 # … below this × the 50-day average volume

# ---- market (evaluate() reads these). The index is the first of MARKET_INDEX_LABELS that the market's
# config lists in broad_index_symbols, else its benchmark.
REQUIRE_MARKET = 1                # 1: G6 is a hard gate; 0: it always passes
MKT_SMA = 50                      # the index closes above this simple average
MARKET_INDEX_LABELS = ("SPY", "NIFTY500")

# ---- the order and the stop (build_plans()/classify()/signal_meta() read these, after evaluate())
TRIGGER_WINDOW = 3                # the buy-stop rests this many sessions
PULLBACK_LOOKBACK = 5             # the pullback low: the lowest low of this many sessions, today included
                                  #   (read in evaluate(), which records it, so NOT signal-exempt)
STOP_BUFFER_ATR = 0.0             # the stop sits this many ATR14 under the pullback low
MAX_RISK_PCT = 8.0                # a stop further than this % under the entry is not bought
TARGET_R = 2.0                    # the target, in R; only a bracket run sells there (the base trails)
EARNINGS_DAYS = 10                # live: results within this many sessions is WATCH - WAIT

S1 = "S1"   # today's low reached the fast EMA and the close held the 50-day


def _ema(d: pd.DataFrame, n: int) -> pd.Series:
    """The n-day EMA of closes: enrich_daily's column when it has one, else computed the same way."""
    col = f"ema{n}"
    return d[col] if col in d.columns else ind.ema(d["close"].astype(float), n)


def _sma(d: pd.DataFrame, n: int) -> pd.Series:
    col = f"sma{n}"
    return d[col] if col in d.columns else ind.sma(d["close"].astype(float), n)


class EmaPullbackStrategy(Strategy):
    selection = "time_series"
    version = "1.0"
    changelog = (
        ("1.0", "2026-10-31",
         "v1: the Learn guide's pullback to a moving average, on the {FAST_EMA}-day EMA. A trend stack of "
         "EMA{STACK_FAST_EMA} > EMA{STACK_SLOW_EMA} > SMA{STACK_SMA}, all rising; a {ADVANCE_HIGH_BARS}-day closing "
         "high in the last {ADVANCE_LOOKBACK} sessions; the first touch after {RUN_LENGTH} closes above the EMA, on "
         "quieter volume, with the index above its {MKT_SMA}-day; buy-stop over the touching bar's high, stop under "
         "the {PULLBACK_LOOKBACK}-session low, sold on a close below the EMA."),
    )
    key = "ema_pullback"
    name = "EMA pullback"
    description = (
        "Pullback to a rising short EMA: a strong trend dips to its {FAST_EMA}-day EMA on quiet volume; buy over "
        "the touching day's high, stop under the dip, sell on a close below the EMA."
    )
    style = "pullback"
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
    screen_key = "uptrend"
    screen_gates = {"G1": "U3", "G2": "U4"}
    watch_codes = ()
    setup_codes = (S1,)
    setup_names = {S1: "Touch of the fast EMA"}
    gate_titles = {
        "G1": "Daily structure", "G2": "Averages not falling",
        "G3": "EMA stack rising", "G4": "Recent closing high", "G5": "First touch",
        "G6": "Market above its {MKT_SMA}-day", "G7": "Quieter volume",
    }
    min_bars = 260

    needs_ctx_extras = True
    extra_columns = ("ema_fast", "ema_stack_fast", "ema_stack_slow", "sma_stack", "touch_pct",
                     "vol_ratio", "pullback_low", "setup_high")
    extra_numeric_columns = extra_columns
    signal_exempt_consts = (
        "TRIGGER_WINDOW", "STOP_BUFFER_ATR", "MAX_RISK_PCT", "TARGET_R", "EARNINGS_DAYS",
    )

    thesis = (
        "In a strong trend, many buyers missed the move and wait for a better price; a short rising EMA is a "
        "level they watch. A quiet dip to it is profit-taking, not a change of mind, and a buy over the touching "
        "day's high waits for those buyers to return. The stop under the dip is close, so being wrong is cheap. "
        "The guide's own event study found the touch alone adds almost nothing to being in an uptrend: any edge "
        "has to come from the trend stack, the filters and the exit."
    )
    how_it_works = (
        "**The idea.** The Learn guide's pullback to a moving average, on the {FAST_EMA}-day EMA, with the trend "
        "read as a rising EMA stack.",
        "**Qualify (the Established uptrend screen's daily rules).** The 50-day above the 200-day without a "
        "break down through the 50-day (G1), and neither average falling (G2).",
        "**A strong trend.** EMA{STACK_FAST_EMA} above EMA{STACK_SLOW_EMA} above SMA{STACK_SMA}, each higher than "
        "{STACK_RISE_BARS} sessions ago (G3), and a {ADVANCE_HIGH_BARS}-day closing high within the last "
        "{ADVANCE_LOOKBACK} sessions (G4).",
        "**The first touch, quietly.** The {RUN_LENGTH} closes before today all above the {FAST_EMA}-day EMA "
        "(G5), and the last {DRYUP_BARS} sessions' average volume below {DRYUP_RATIO} × the 50-day average (G7).",
        "**The market.** The index (S&P 500 in the US, Nifty 500 in India) closes above its {MKT_SMA}-day (G6).",
        "**The setup (S1).** Today's low is at or under the {FAST_EMA}-day EMA × (1 + {TOUCH_TOL_PCT}%), and "
        "today's close is at or above the 50-day.",
        "**Buy.** A buy-stop one tick over today's high, resting {TRIGGER_WINDOW} sessions. The stop is the lowest "
        "low of the last {PULLBACK_LOOKBACK} sessions minus {STOP_BUFFER_ATR} ATR14; a stop more than "
        "{MAX_RISK_PCT}% under the entry is not bought.",
        "**Sell.** At the first close below the {FAST_EMA}-day EMA, or at the stop. The plan's target, "
        "{TARGET_R} R, sells only in a bracket run.",
        "**What the backtest buys.** Only TRADE - HIGH CONFIDENCE: every gate, S1, and a stop inside the limit. "
        "Ties between same-day signals go to the stronger 12-1 month momentum.",
    )
    caveats = (
        "**Not yet measured.** No backtest has judged it (see Status).",
        "**Daily bars, not an intraday turn.** Traders who teach this setup buy the intraday reversal off the "
        "EMA, often with a stop under that day's low. Daily bars cannot see the turn: this waits for a trade "
        "over the touching day's high, a later and dearer entry with a wider stop. Results here say nothing "
        "either way about the intraday method.",
        "**Survivorship.** The universe is today's stock lists. Stocks whose trend ended in a collapse and a "
        "delisting are missing, which flatters every trend strategy, this one included.",
        "**Overlap with trend_pullback.** Both draw from the Established uptrend screen and both buy dips. A "
        "trend_pullback TC-01 dip often reaches the 21-day EMA, so the two will often hold the same stock; read "
        "the two results as related, not independent evidence.",
        "**The touch alone has no edge in the guide's study.** On liquid US and Indian stocks, 2012–2026, the "
        "first touch of the 21-day EMA in an uptrend returned about the same over 20 sessions as any uptrend "
        "day, and quieter volume did not separate good touches from bad. Those event-study numbers came from "
        "the same years as this backtest's optimise window.",
        "**Only the first bar's order.** The guide moves the buy-stop down to each later bar that touches the EMA "
        "again. Here a later touch is not a new setup (it fails G5), so the first bar's buy-stop rests unchanged "
        "until it fills, its window ends, the low reaches the stop, or a close falls below the 50-day.",
        "**A tight trail.** The entry sits just above the EMA, so a close below it can come within days; that is "
        "the rule as taught, and many trades end small either way.",
        "**Results rule leaks.** The backtest skips signals with results filed within two weeks (`--results-blackout "
        "14`), but filings come after the announcement that gaps the stock, and India's are stored only from late "
        "2020. Some trades are held into results.",
        "**India price bands not modelled.** A stop under a lower-band close cannot fill until the band opens.",
        "**Run it with its exit flags.** `--exit-mode ma --ma-col ema21 --no-target` (the page's backtest command "
        "adds them); with `--const FAST_EMA=10` pass `--ma-col ema10`. Without them the default bracket sells at "
        "the {TARGET_R} R target.",
        corporate_actions.CAVEAT_TRADED,
    )

    status = (
        "NOT YET MEASURED. Stage: optimise (2013-2021, in-sample); verify has not been run. Pass criterion, set "
        "before any result: in the optimise stage, the base rules beat the market's benchmark CAGR AND make a "
        "positive average R after costs, in at least one market; reported beside trend_pullback's optimise run. "
        "Up-front variants, measured beside the base and never chosen as a substitute for it: FAST_EMA=10 (the "
        "10-day EMA, trailed with --ma-col ema10) and a fixed {TARGET_R} R bracket target with a 10-session time "
        "stop instead of the EMA trail."
    )
    gate_docs = {
        "G1": (
            "Daily structure (the Established uptrend screen's U3).\n\n"
            "- **Test:** the 50-day average is above the 200-day, and the close has not broken down through the "
            "50-day: not more than 2 ATR14 under it, and not the last 5 closes all under it.\n"
            "- **Fails:** either, or no averages yet."
        ),
        "G2": (
            "Neither the 50-day nor the 200-day is falling (the Established uptrend screen's U4).\n\n"
            "- **Test:** the 50-day is not more than {SMA50_FALLING_PCT}% below its value {SMA50_SLOPE_BARS} "
            "sessions ago, and the 200-day not more than {SMA200_FALLING_PCT}% below its value "
            "{SMA200_SLOPE_BARS} sessions ago."
        ),
        "G3": (
            "A strong trend: the EMA stack is in order and rising.\n\n"
            "- **Test:** EMA{STACK_FAST_EMA} > EMA{STACK_SLOW_EMA} > SMA{STACK_SMA} today, and each of the three is "
            "higher than {STACK_RISE_BARS} sessions ago.\n"
            "- **Fails:** any line out of order or not rising, or no values yet.\n\n"
            "The traders' definition of a trend strong enough to buy a dip to its short EMA."
        ),
        "G4": (
            "A recent advance.\n\n"
            "- **Test:** one of the last {ADVANCE_LOOKBACK} closes, today's included, was the highest close of its "
            "own {ADVANCE_HIGH_BARS} sessions.\n"
            "- **Fails:** no fresh closing high in that window: the trend is stale."
        ),
        "G5": (
            "The first touch.\n\n"
            "- **Test:** each of the {RUN_LENGTH} closes before today was above that day's {FAST_EMA}-day EMA.\n"
            "- **Fails:** any of them at or below it. A stock already sitting on its EMA is not pulling back to it, "
            "and later touches in the same dip are not new setups."
        ),
        "G6": (
            "The market is above its {MKT_SMA}-day average.\n\n"
            "- **Index:** the S&P 500 (SPY) in the US, the Nifty 500 in India; a market whose config lists neither "
            "uses its benchmark.\n"
            "- **Test:** today the index closes above its {MKT_SMA}-day simple average.\n"
            "- **Off switch:** with REQUIRE_MARKET = 0 (now {REQUIRE_MARKET}) the gate always passes.\n\n"
            "The guide calls it the cheapest rule and among the most useful: dips stop being bought when the "
            "market turns."
        ),
        "G7": (
            "Quieter volume on the dip.\n\n"
            "- **Test:** the average volume of the last {DRYUP_BARS} sessions, today's included, is below "
            "{DRYUP_RATIO} × the 50-day average volume.\n"
            "- **Fails:** heavier volume: selling, not a pause.\n\n"
            "Widely taught; in the guide's event study it did not separate good touches from bad."
        ),
    }
    watch_docs = {}
    setup_docs = {
        S1: (
            "Today's low reaches the {FAST_EMA}-day EMA and the close holds the 50-day.\n\n"
            "- **Touch:** today's low is at or below the EMA × (1 + {TOUCH_TOL_PCT}%).\n"
            "- **Hold:** today's close is at or above today's 50-day average.\n"
            "- **Signal:** the setup bar. The entry is a buy-stop over its high (setup quality 2)."
        ),
    }
    entry_rules = (
        "Signal. S1 with every gate passing and a stop inside the limit, graded TRADE - HIGH CONFIDENCE.",
        "Order. A buy-stop one tick over the setup bar's high, resting {TRIGGER_WINDOW} sessions from the next. "
        "An open above it fills at the open.",
        "Cancelled (backtest) when the window ends, when a low reaches the stop before it fills, or on a close "
        "below the setup bar's 50-day average.",
        "Stop test at the fill (backtest). A fill more than {MAX_RISK_PCT}% above the stop is skipped.",
        "No buy within results (live). Results within {EARNINGS_DAYS} sessions is WATCH - WAIT; the backtest "
        "skips signals with results filed within 14 days (`--results-blackout 14`).",
        "One position per stock (backtest). A signal in a stock already held, or with an order resting, is ignored.",
    )
    stop_rules = (
        "Where it goes. The lowest low of the last {PULLBACK_LOOKBACK} sessions, the setup bar's included, minus "
        "{STOP_BUFFER_ATR} × ATR14, rounded down to the tick. It defines 1R.",
        "How far is too far. More than {MAX_RISK_PCT}% under the entry is WATCH - WAIT live and skipped in the "
        "backtest: the dip was too deep for this setup.",
        "How it sells (backtest). The first session whose low touches it sells at the stop, or at the open if it "
        "opened below it.",
        "It never moves. The trail acts on closes: see Exit.",
    )
    target_rules = (
        "Entry + {TARGET_R} R. The base backtest runs with `--no-target` and sells on the EMA trail instead; the "
        "fixed-target variant runs the bracket and sells everything there.",
    )
    exit_rules = (
        "Each session after the fill, in this order (backtest, `--exit-mode ma --ma-col ema21`):",
        "1. The stop: sells at the stop, or at the open if the stock gapped through it.",
        "2. The trail: a close below that day's {FAST_EMA}-day EMA sells everything at that close.",
        "Live, the screen shows the setup; nothing manages an open position.",
        "No other exits in the base run. A position still open when the backtest ends is marked at the last close.",
    )
    sizing_rules = (
        "Risk-based. Shares = (equity × Risk per trade) ÷ (price paid − stop), rounded down, capped at Max "
        "position size × equity.",
        "Cash. When cash cannot buy the full size, the backtest buys what it can.",
        "Slots. At most Position cap positions at once. A triggered order with no free slot keeps resting.",
    )
    filter_rules = (
        "Thin stocks. The 20-day average of close × volume must be at least the Minimum liquidity.",
        "Too little history. At least {min_bars} daily bars and a usable ATR14.",
        "No price floor on split-adjusted history.",
        "Market regime. The market test is gate G6; the shared risk-off downgrade is not applied on top of it.",
    )
    regime_note = (
        "No downgrade. The market test is this strategy's own hard gate G6, so a market below its "
        "{MKT_SMA}-day is already an AVOID; the shared market-regime downgrade is not applied on top of it."
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Every gate passes, today touched the EMA and held the 50-day (S1), the stop is "
                                 "within {MAX_RISK_PCT}% of the entry, no results are due within {EARNINGS_DAYS} "
                                 "sessions and one share fits the account. The only tier the backtest buys.",
        "TRADE_ON_TRIGGER": "Not used: the setup is already a buy-stop order.",
        "WATCH_WAIT": "S1 fired but the stop is more than {MAX_RISK_PCT}% under the entry, results are due within "
                      "{EARNINGS_DAYS} sessions, or not even one share fits the account.",
        "AVOID": "A gate failed, or the plan's risk is not a positive number.",
    }
    param_docs = (
        ("Stack fast EMA", "STACK_FAST_EMA", "G3: the fastest line of the trend stack."),
        ("Stack slow EMA", "STACK_SLOW_EMA", "G3: the middle line."),
        ("Stack average", "STACK_SMA", "G3: the simple average under both EMAs."),
        ("Stack rising over", "STACK_RISE_BARS", "G3: each line higher than this many sessions ago."),
        ("Pullback EMA", "FAST_EMA", "S1, G5 and the trail: the EMA the dip touches."),
        ("Touch tolerance", "TOUCH_TOL_PCT", "S1: a low up to this % above the EMA counts as a touch."),
        ("Run length", "RUN_LENGTH", "G5: closes before today that must all be above the EMA."),
        ("Advance lookback", "ADVANCE_LOOKBACK", "G4: sessions in which a fresh closing high must fall."),
        ("Closing-high window", "ADVANCE_HIGH_BARS", "G4: the window a close must be the highest of."),
        ("Dry-up window", "DRYUP_BARS", "G7: sessions in the recent volume average."),
        ("Dry-up ratio", "DRYUP_RATIO", "G7: recent volume below this × the 50-day average volume."),
        ("Market gate", "REQUIRE_MARKET", "1: G6 is a hard gate; 0: it always passes."),
        ("Index average", "MKT_SMA", "G6: the index closes above this simple average."),
        ("Trigger window", "TRIGGER_WINDOW", "Sessions the buy-stop rests."),
        ("Pullback lookback", "PULLBACK_LOOKBACK", "Sessions whose lowest low places the stop."),
        ("Stop buffer", "STOP_BUFFER_ATR", "ATR14s under the pullback low."),
        ("Maximum risk", "MAX_RISK_PCT", "A stop further than this % under the entry is not bought."),
        ("Target", "TARGET_R", "Entry + this × R; sold only in a bracket run."),
        ("Results window", "EARNINGS_DAYS", "Live: results within this many sessions is WATCH - WAIT."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume",
         "Pre-filter: the 20-day average of close × volume must be at least this."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Max position size", "cfg.max_position_pct", "Cap on one position's value as a fraction of equity."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
        ("Tick size", "cfg.tick_size", "The buy-stop is rounded up and the stop down to this increment."),
        ("Slippage", "cfg.slippage_bps", "Backtest cost per side, in basis points of the fill price."),
    )
    backtest_args = "--exit-mode ma --ma-col ema21 --no-target --results-blackout 14 --rank-by setup_momentum"

    # ---------- market ----------

    _market_cache: dict = {}

    @classmethod
    def _market_ok(cls, market_key: str):
        """Per date: does the index pass G6? Computed once per market and cached on the class. The average
        is causal, so a value on a date reads only the index up to it."""
        if market_key not in cls._market_cache:
            from ..config import MARKETS
            from ..marketdata import cache
            cfg = MARKETS[market_key]
            label = next((x for x in MARKET_INDEX_LABELS if x in cfg.broad_index_symbols), None)
            ticker = cfg.broad_index_symbols[label] if label else cfg.benchmark_ticker
            b = cache.load_cached(market_key, ticker)
            if b is None or b.empty:
                cls._market_cache[market_key] = None
            else:
                c = b["close"].astype(float)
                cls._market_cache[market_key] = c > ind.sma(c, MKT_SMA)
        return cls._market_cache[market_key]

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
        # G1 and G3 on one row, so the backtest skips the bars they would fail anyway
        s50, s200 = last.get("sma50"), last.get("sma200")
        if pd.isna(s50) or pd.isna(s200) or not s50 > s200:
            return False, "50-day not above the 200-day"
        f, s, m = (last.get(f"ema{STACK_FAST_EMA}"), last.get(f"ema{STACK_SLOW_EMA}"),
                   last.get(f"sma{STACK_SMA}"))
        if f is not None and s is not None and m is not None and not (f > s > m):
            return False, "EMA stack out of order"
        return True, "passed"

    # ---------- gates ----------

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        d = ctx.daily
        self.apply_screen(ctx, result)
        e = ctx.extras
        close = d["close"].astype(float)
        fast_ema = _ema(d, FAST_EMA)
        ema_f, ema_s, sma_m = _ema(d, STACK_FAST_EMA), _ema(d, STACK_SLOW_EMA), _sma(d, STACK_SMA)
        e["ema_fast"] = float(fast_ema.iloc[-1])
        e["ema_stack_fast"], e["ema_stack_slow"], e["sma_stack"] = (float(ema_f.iloc[-1]), float(ema_s.iloc[-1]),
                                                                    float(sma_m.iloc[-1]))

        # G3: the stack
        n = len(d)
        if n <= STACK_RISE_BARS:
            result.fail("G3", "insufficient history for the stack")
        else:
            now = [float(x.iloc[-1]) for x in (ema_f, ema_s, sma_m)]
            then = [float(x.iloc[-1 - STACK_RISE_BARS]) for x in (ema_f, ema_s, sma_m)]
            if any(v != v for v in now + then):
                result.fail("G3", "no stack values yet")
            elif not now[0] > now[1] > now[2]:
                result.fail("G3", f"stack out of order: EMA{STACK_FAST_EMA} {now[0]:.2f}, "
                                  f"EMA{STACK_SLOW_EMA} {now[1]:.2f}, SMA{STACK_SMA} {now[2]:.2f}")
            elif not all(a > b for a, b in zip(now, then)):
                result.fail("G3", f"a stack line is not higher than {STACK_RISE_BARS} sessions ago")
            else:
                result.ok("G3", "")

        # G4: a recent closing high
        hi = close.rolling(ADVANCE_HIGH_BARS, min_periods=ADVANCE_HIGH_BARS).max()
        recent = (close.iloc[-ADVANCE_LOOKBACK:] >= hi.iloc[-ADVANCE_LOOKBACK:]).any()
        if recent:
            result.ok("G4", "")
        else:
            result.fail("G4", f"no {ADVANCE_HIGH_BARS}-day closing high in the last {ADVANCE_LOOKBACK} sessions")

        # G5: the first touch
        if n <= RUN_LENGTH:
            result.fail("G5", "insufficient history for the run")
        else:
            prev_c = close.iloc[-RUN_LENGTH - 1:-1].to_numpy()
            prev_e = fast_ema.iloc[-RUN_LENGTH - 1:-1].to_numpy()
            if (prev_c > prev_e).all():
                result.ok("G5", "")
            else:
                result.fail("G5", f"not all of the last {RUN_LENGTH} closes above the {FAST_EMA}-day EMA")

        # G6: the market
        if REQUIRE_MARKET:
            ok = self._market_ok(_market_of(ctx.symbol))
            if ok is None:
                result.fail("G6", "no index history")
            elif bool(ok.asof(d.index[-1])):
                result.ok("G6", "")
            else:
                result.fail("G6", f"index at or below its {MKT_SMA}-day")
        else:
            result.ok("G6", "market gate off")

        # G7: quieter volume
        vol50 = d["vol_sma50"].iloc[-1] if "vol_sma50" in d.columns else float("nan")
        recent_vol = float(d["volume"].iloc[-DRYUP_BARS:].astype(float).mean())
        ratio = recent_vol / float(vol50) if vol50 == vol50 and vol50 else float("nan")
        e["vol_ratio"] = ratio
        if ratio == ratio and ratio < DRYUP_RATIO:
            result.ok("G7", f"volume {ratio:.2f} × average")
        else:
            result.fail("G7", f"volume {ratio:.2f} × average (not below {DRYUP_RATIO})")

        # S1: the touch and the hold
        last = d.iloc[-1]
        ema_now = e["ema_fast"]
        low, sma50 = float(last["low"]), last.get("sma50")
        e["touch_pct"] = (low / ema_now - 1) * 100 if ema_now == ema_now and ema_now else float("nan")
        e["setup_high"] = float(last["high"])
        e["pullback_low"] = float(d["low"].iloc[-PULLBACK_LOOKBACK:].astype(float).min())
        touched = ema_now == ema_now and low <= ema_now * (1 + TOUCH_TOL_PCT / 100)
        held = sma50 is not None and sma50 == sma50 and ctx.close >= float(sma50)
        result.setups[S1] = bool(touched and held)
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
        atr14 = ctx.atr
        if pd.isna(atr14) or not atr14:
            return PlanChoice(None, None, "missing ATR")
        e = ctx.extras
        tick = cfg.tick_size if cfg.tick_size > 0 else 0.01
        entry = round_tick(float(e["setup_high"]) + tick, cfg.tick_size, "up")
        stop = round_tick(float(e["pullback_low"]) - STOP_BUFFER_ATR * float(atr14), cfg.tick_size, "down")
        risk = entry - stop
        target = entry + TARGET_R * risk
        plan = TradePlan(
            plan="EP", setup=S1, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=TARGET_R if risk > 0 else float("nan"),
            nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"touched the {FAST_EMA}-day EMA {e['ema_fast']:.2f}; buy over {entry:.2f}")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        meta = {"expiry_bdays": TRIGGER_WINDOW, "max_risk_pct": MAX_RISK_PCT / 100}
        sma50 = ctx.daily["sma50"].iloc[-1]
        if sma50 == sma50:
            meta["cancel_close_below"] = float(sma50)
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
        elif risk_pct > MAX_RISK_PCT:
            label, reason = "WATCH_WAIT", f"stop {risk_pct:.1f}% under the entry (> {MAX_RISK_PCT}%)"
        elif earnings_days_away is not None and earnings_days_away <= EARNINGS_DAYS:
            label, reason = "WATCH_WAIT", f"results in {earnings_days_away} sessions"
        else:
            label, reason = "TRADE_HIGH_CONFIDENCE", f"first touch of the {FAST_EMA}-day EMA; stop {risk_pct:.1f}% away"
        return Decision(LABELS[label], LABELS[label], reason, risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult, plan: TradePlan | None) -> dict:
        e = ctx.extras
        r = lambda v: round(float(v), 2) if v is not None and v == v else None
        return {k: r(e.get(k)) for k in self.extra_columns}

    def chart_anatomy(self, sig: dict) -> list[dict]:
        """The EMA the dip touched, the buy-stop over the setup bar and the pullback low under it."""
        e = sig.get("extras") or {}
        d = str(sig["date"])
        out: list[dict] = []
        if e.get("ema_fast"):
            out.append({"shape": "level", "bars": RUN_LENGTH + 1, "to": d, "price": float(e["ema_fast"]),
                        "role": "support", "label": f"{FAST_EMA}-day EMA {e['ema_fast']:g} — the touch"})
        if e.get("setup_high"):
            out.append({"shape": "level", "bars": 2, "to": d, "price": float(e["setup_high"]), "role": "pivot",
                        "label": f"setup high {e['setup_high']:g} — a trade above it is the buy"})
        if e.get("pullback_low"):
            out.append({"shape": "level", "bars": PULLBACK_LOOKBACK, "to": d, "price": float(e["pullback_low"]),
                        "role": "stop", "label": f"pullback low {e['pullback_low']:g} — the stop"})
            out.append({"shape": "note", "at": d, "price": float(e["pullback_low"]),
                        "text": f"EMA pullback {d}: first touch of the {FAST_EMA}-day EMA, volume "
                                f"{e.get('vol_ratio') or 0:.2f} × average."})
        return out or super().chart_anatomy(sig)
