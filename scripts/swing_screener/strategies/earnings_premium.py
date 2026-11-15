"""Earnings-announcement premium -- own a stock through the week its report is expected.

Beaver (1968) showed that prices move more in earnings weeks; Frazzini & Lamont, "The Earnings
Announcement Premium and Trading Volume" (2007), showed that stocks also EARN more, on average, in the
months they are expected to announce -- and that the premium is largest where attention spikes. They
predict the announcement point in time, from the company's own history: the next report is expected
52 weeks after the same quarter's report a year earlier. This module does the same, per stock:

  * a year-ago announcement made YEAR_DAYS - LEAD_MAX_DAYS .. YEAR_DAYS - LEAD_MIN_DAYS calendar days
    before today puts the expected report E = that date + YEAR_DAYS, LEAD_MIN_DAYS to LEAD_MAX_DAYS ahead;
  * no announcement is recorded in the RECENT_DAYS before today (the report has not already come early);
  * buy the close, hold HOLD_BARS sessions through the expected date; a sizing stop STOP_ATR x ATR14 below.

Announcement dates: `marketdata.financials.announcements` (each quarter's earliest record), which honours
the backtest stage boundary.
"""

import bisect
import datetime as dt

from ..core.context import StockContext
from ..marketdata import corporate_actions
from .base import StrategyResult
from .rs_leaders import _market_of
from .swing_base import PASS_RULE, SwingSetupStrategy

YEAR_DAYS = 364          # the next report is expected this many calendar days (52 weeks) after last year's
LEAD_MIN_DAYS = 5        # G1: the expected date is at least this many calendar days ahead
LEAD_MAX_DAYS = 9        # ...and at most this many
RECENT_DAYS = 30         # G2: no announcement recorded in this many calendar days before today
STOP_ATR = 3             # the sizing stop, this many ATR14 below the entry
MIN_STOP_PCT = 1.0       # a stop closer than this % below the entry is not bought
MAX_STOP_PCT = 25.0      # nor one further than this %
NOMINAL_TARGET_R = 2     # the plan's target, for the R column only (the backtest runs --no-target)
HOLD_BARS = 10           # backtest_args: sold at the close of this session after the entry

S1 = "S1"


class EarningsPremiumStrategy(SwingSetupStrategy):
    key = "earnings_premium"
    name = "Earnings-announcement premium"
    description = ("Frazzini & Lamont's earnings-announcement premium, per stock: buy when a report is expected "
                   "next week (52 weeks after last year's), hold through it for a fixed number of sessions.")
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "v1: the expected report is a year-ago announcement + {YEAR_DAYS} days, {LEAD_MIN_DAYS}-{LEAD_MAX_DAYS} "
         "days ahead, with nothing announced in the last {RECENT_DAYS} days; bought at the close, a {STOP_ATR} "
         "ATR14 sizing stop, no target, sold after {HOLD_BARS} sessions."),
    )
    behaviour = "event_driven"
    style = "event"
    gate_codes = ("G1", "G2")
    screen_key = "above_200"
    screen_gates: dict = {}
    setup_codes = (S1,)
    setup_names = {S1: "Report expected next week"}
    gate_titles = {"G1": "Year-ago report {LEAD_MIN_DAYS}-{LEAD_MAX_DAYS} days ahead of its anniversary",
                   "G2": "Nothing announced in {RECENT_DAYS} days"}
    order = "close"
    expiry_bdays = None
    plan_code = "EP"
    extra_columns = ("year_ago_days", "expected_in_days", "last_announce_days", "level_entry", "level_stop")
    extra_numeric_columns = extra_columns

    thesis = (
        "Stocks earn more in the weeks they are expected to report. Beaver (1968) found that prices move more "
        "around earnings announcements; Frazzini & Lamont, \"The Earnings Announcement Premium and Trading "
        "Volume\" (2007), found that stocks expected to announce in a month outperform those that are not, by a "
        "margin that has held across decades and markets, and that the premium tracks the jump in attention and "
        "volume an announcement brings. The catalogue grades it B, credibility 3. The expectation must be point "
        "in time, so, as in the paper, it comes from the company's own calendar: 52 weeks after last year's "
        "report of the same quarter."
    )
    how_it_works = (
        "**Universe.** Every liquid stock. The paper has no trend filter, so none is added; the Above the 200-day "
        "screen supplies the universe only, with no gate taken from it.",
        "**The expected date (G1).** A results announcement was made between {YEAR_DAYS} − {LEAD_MAX_DAYS} and "
        "{YEAR_DAYS} − {LEAD_MIN_DAYS} calendar days before today. The same quarter's report is expected "
        "{YEAR_DAYS} days (52 weeks) after it, so {LEAD_MIN_DAYS} to {LEAD_MAX_DAYS} days from today.",
        "**Not already reported (G2).** No announcement is recorded in the {RECENT_DAYS} days up to today: a "
        "company that reported early has nothing left to anticipate. Only dates on or before today are read.",
        "**The setup (S1).** G1 and G2 both pass: a report is expected next week. Bought at today's close. A "
        "window several days wide fires on consecutive sessions; one position per stock takes the first.",
        "**Stop and exit.** A sizing stop {STOP_ATR} ATR14 below the entry; no target; sold at the close of "
        "session {HOLD_BARS} after the entry, which covers the expected date and a few sessions after it.",
    )
    caveats = (
        "**Announcement-date coverage.** Dates come from each quarter's earliest stored results record: for the "
        "US, 8-K filings with Item 2.02, from 2005; for India, NSE results broadcasts and the board meetings that "
        "approved them, from 2005, thinner before 2007. Both cover the whole optimise window. A company with no "
        "recorded announcements (a foreign issuer filing 6-Ks, a company the exchange does not list) never "
        "signals, and some records start late: on 2026-11-15 about half the stored symbols in each market had "
        "records from 2013 or earlier, and Exxon Mobil's begin only in 2026. A stock with no year-ago record "
        "cannot signal, so coverage, not the rule, decides which stocks are tested in the early years.",
        "**The stop is not in the paper.** The paper holds through the report with no stop; the {STOP_ATR} ATR14 "
        "stop is a sizing stop so the trade can be sized by risk like every catalogue setup, and it will cut "
        "some reports the paper would have held.",
        "**A cross-section turned into a trade.** The paper's premium is a monthly, equal-weight portfolio of all "
        "stocks expected to announce against all that are not; this is a per-stock trade of {HOLD_BARS} sessions, "
        "with slots, cash and ranking, judged against the benchmark rather than against non-announcers.",
        "**The calendar shifts.** A company that moves its reporting date by more than a few days is missed or "
        "bought too early; the paper accepts the same error.",
        "**Survivorship.** The universe is today's stock lists, which flatters any long rule.",
        "**Run it with its exit flags** (`backtest_args`); the default bracket would sell at the nominal target.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (event group, grade B, credibility "
              "3); optimise-stage runs queued in both markets. " + PASS_RULE)
    gate_docs = {
        "G1": ("A report is expected soon.\n\n- **Test:** an announcement is recorded between {YEAR_DAYS} − "
               "{LEAD_MAX_DAYS} and {YEAR_DAYS} − {LEAD_MIN_DAYS} calendar days before today, so its anniversary "
               "({YEAR_DAYS} days on) is {LEAD_MIN_DAYS} to {LEAD_MAX_DAYS} days ahead.\n- **Fails:** no such "
               "announcement, or the company has no recorded announcements."),
        "G2": ("Not already reported.\n\n- **Test:** no announcement is recorded in the {RECENT_DAYS} calendar days "
               "up to and including today.\n- **Fails:** the company has just reported, so the expected report "
               "came early."),
    }
    watch_docs: dict = {}
    setup_docs = {
        S1: ("Report expected next week.\n\n- **Test:** G1 and G2 pass.\n- **Signal:** buy today's close; stop "
             "{STOP_ATR} ATR14 below; hold {HOLD_BARS} sessions."),
    }
    entry_rules = (
        "Signal. G1, G2 and S1 on today's close, with the stop between {MIN_STOP_PCT}% and {MAX_STOP_PCT}% below "
        "the entry, graded TRADE - HIGH CONFIDENCE.",
        "Order. Bought at the signal session's close.",
        "One position per stock.",
    )
    stop_rules = ("Where it goes. Entry − {STOP_ATR} × ATR14, rounded down to the tick. It defines 1R and does not "
                  "move. A sizing stop: the paper has none.",)
    target_rules = ("No target. The plan's target is entry + {NOMINAL_TARGET_R} R for the R column only; the "
                    "backtest runs with `--no-target`.",)
    exit_rules = (
        "Each session after the entry (backtest, `--no-target --time-stop-bars {HOLD_BARS}`):",
        "1. The stop, at its price or at the open if the stock gaps under it.",
        "2. The time limit: sold at the close of session {HOLD_BARS} after the entry.",
    )
    param_docs = (
        ("Year", "YEAR_DAYS", "Calendar days from last year's report to the expected one (52 weeks)."),
        ("Earliest lead", "LEAD_MIN_DAYS", "G1: the expected report is at least this many days ahead."),
        ("Latest lead", "LEAD_MAX_DAYS", "G1: and at most this many."),
        ("Recent report", "RECENT_DAYS", "G2: no announcement in this many days before today."),
        ("Stop", "STOP_ATR", "ATR14 multiples below the entry (a sizing stop)."),
        ("Minimum stop", "MIN_STOP_PCT", "A stop closer than this % below the entry is not bought."),
        ("Maximum stop", "MAX_STOP_PCT", "A stop further than this % below the entry is not bought."),
        ("Hold", "HOLD_BARS", "Sessions after the entry before the position is sold (--time-stop-bars)."),
        ("Nominal target", "NOMINAL_TARGET_R", "Target = entry + this × R, for the R column only."),
        ("Minimum history", "min_bars", "Daily bars a stock needs before it is evaluated."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "The 20-day average of close × volume, at least."),
        ("Risk per trade", "cfg.risk_pct", "Fraction of equity risked between the price paid and the stop."),
        ("Position cap", "cfg.max_open_positions", "Backtest slots."),
    )
    backtest_args = f"--no-target --time-stop-bars {HOLD_BARS} --rank-by setup_momentum --min-fill 0.5"

    _announced: dict = {}

    @classmethod
    def _announcements(cls, market_key: str) -> dict:
        """{symbol: sorted announcement dates}, cached per market AND stage boundary: the loader honours the
        boundary, so a cache keyed on the market alone would hand an optimise run's dates to a full run in the
        same process, or the reverse (as earnings_gaps does)."""
        from ..marketdata import asof, financials
        key = (market_key, asof.end_date())
        if key not in cls._announced:
            cls._announced[key] = financials.announcements(market_key, first_per_quarter=True)
        return cls._announced[key]

    def detect(self, ctx: StockContext, result: StrategyResult) -> None:
        e = ctx.extras
        dates = self._announcements(_market_of(ctx.symbol)).get(ctx.symbol) or []
        today = ctx.daily.index[-1].date()
        if not dates:
            result.fail("G1", "no recorded announcements")
            result.fail("G2", "no recorded announcements")
            return
        # G1: a year-ago announcement YEAR - LEAD_MIN (older bound) to YEAR - LEAD_MAX (newer) days back,
        # so its anniversary is LEAD_MIN to LEAD_MAX days ahead
        older = today - dt.timedelta(days=YEAR_DAYS - LEAD_MIN_DAYS)
        newer = today - dt.timedelta(days=YEAR_DAYS - LEAD_MAX_DAYS)
        i = bisect.bisect_left(dates, older)
        year_ago = dates[i] if i < len(dates) and dates[i] <= newer else None
        # G2: the latest announcement on or before today
        j = bisect.bisect_right(dates, today)
        last = dates[j - 1] if j else None
        last_days = (today - last).days if last else float("nan")
        e.update(year_ago_days=(today - year_ago).days if year_ago else float("nan"),
                 expected_in_days=(year_ago + dt.timedelta(days=YEAR_DAYS) - today).days if year_ago else float("nan"),
                 last_announce_days=last_days)
        if year_ago:
            result.ok("G1", f"reported {year_ago}; next expected {year_ago + dt.timedelta(days=YEAR_DAYS)}")
        else:
            result.fail("G1", "no report expected next week")
        if last is None or last_days > RECENT_DAYS:
            result.ok("G2", "no recent announcement" if last is None else f"last announced {last} ({last_days} days)")
        else:
            result.fail("G2", f"announced {last}, {last_days} days ago")
        close, atr = float(ctx.daily["close"].iloc[-1]), float(ctx.daily["atr14"].iloc[-1])
        e.update(level_entry=close, level_stop=close - STOP_ATR * atr)
        result.setups[S1] = bool(year_ago and (last is None or last_days > RECENT_DAYS))

    def levels(self, ctx, result, cfg):
        e = ctx.extras
        return e["level_entry"], e["level_stop"], None, (
            f"report expected in {e['expected_in_days']:.0f} days (52 weeks after last year's)")
