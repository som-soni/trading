"""Pre-holiday -- Lakonishok & Smidt (1988), Ariel (1990): hold the index over the session before a holiday.

The session before an exchange holiday earned, in Lakonishok & Smidt's ninety years of the Dow, about
twenty times an ordinary session's return; Ariel (1990) found the same in US indices. The usual readings
are behavioural (a pre-holiday mood, short sellers closing before a long break). The catalogue grades it C,
credibility 3. Run by `index_timing`: the index held over the pre-holiday session, cash otherwise.
"""

from ..strategies.base import PortfolioStrategy
from ..strategies.swing_base import PASS_RULE_PORTFOLIO

DOC = {
    "key": "pre_holiday",
    "name": "Pre-holiday",
    "description": "Hold the market index over the {days_before} session(s) before each weekday exchange holiday; "
                   "cash otherwise.",
    "status": ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (calendar group, grade C, "
               "credibility 3); optimise-stage runs queued in both markets. " + PASS_RULE_PORTFOLIO + " The book "
               "is in the market only a few sessions a year, so the test is read beside the SELECTION line (the "
               "index at the same exposure)."),
    "thesis": (
        "Before a long weekend or holiday, buyers outnumber sellers: short sellers close positions they do not "
        "want to carry through a break, and sentiment is better. Lakonishok & Smidt (1988) and Ariel (1990) "
        "found pre-holiday sessions earned many times an ordinary session's return in US indices; later work "
        "found it weaker since the 1990s. The catalogue grades it C, credibility 3."
    ),
    "how_it_works": (
        "**The series.** The market's benchmark: SPY in the US, the Nifty 500 index in India.",
        "**The holidays.** A weekday with no session between two sessions of the series is an exchange holiday. "
        "Holiday calendars are published a year ahead, so knowing one is coming is not hindsight.",
        "**The trade.** Bought at the close of the session before the window, sold at the close of the last "
        "session before the holiday -- {days_before} session(s) held -- {cost_bps} basis points a side; cash "
        "otherwise.",
    ),
    "entry_rules": (
        "Buy the whole book of the index at the close {days_before} session(s) before the last session ahead of "
        "a weekday holiday, {cost_bps}bps.",
    ),
    "exit_rules": (
        "Sell at the close of the session before the holiday, {cost_bps}bps. No stop.",
    ),
    "caveats": (
        "**Holidays are read from the series' own gaps.** A weekday missing from the stored series for any "
        "other reason (a data gap, an exchange outage) would count as a holiday; for a major index such gaps "
        "are rare, but not checked against an official calendar.",
        "**India's series is an index, not a fund**, so a real book adds tracking difference and spread.",
        "**Cash earns nothing here**, and the book is out of the market almost all year.",
        "**Few trades.** About nine to fifteen holidays a year, so the optimise window holds about a hundred "
        "trades per market: enough to see a large effect, not a small one.",
    ),
}


class PreHolidayStrategy(PortfolioStrategy):
    """Hold the index over the session before each exchange holiday (Lakonishok & Smidt 1988)."""

    key = DOC["key"]
    doc = DOC
    family = "pre_holiday"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "First version: the benchmark held over the {days_before} session(s) before each weekday holiday found "
         "in its own session list, {cost_bps}bps a side, cash otherwise."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "event_driven"
    selection = "time_series"
    style = "calendar"
    horizon = "swing"
    runner = "index_timing"

    effect = "pre_holiday"
    days_before = 1
    cost_bps = 5.0
    run_note = "Held over the {days_before} session(s) before each weekday exchange holiday."

    param_docs = (
        ("Sessions held", "days_before", "Sessions held, ending with the one before the holiday."),
        ("Cost per side", "cost_bps", "Basis points on each buy and sale."),
    )
