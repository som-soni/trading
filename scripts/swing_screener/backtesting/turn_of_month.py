"""Turn of the month -- Ariel (1987), Lakonishok & Smidt (1988): hold the index over the month's turn only.

The documented calendar effect with the best record: the last session of a month and the first three of
the next have earned a large share of the index's return, in the US for a century and in most markets
tested since. One explanation is flows -- salaries, pension contributions and fund inflows arrive at the
month's turn and are invested. The catalogue (research/strategy-catalog-swing.md §4) names it, grade C,
credibility 4, as an overlay on the index exposure the momentum books hold; this version measures the
effect on its own, the index held at the turn and cash otherwise, run by `index_timing`.
"""

from ..strategies.base import PortfolioStrategy
from ..strategies.swing_base import PASS_RULE_PORTFOLIO

DOC = {
    "key": "turn_of_month",
    "name": "Turn of the month",
    "description": "Hold the market index over the last {days_before} session(s) of each month and the first "
                   "{days_after} of the next; cash otherwise.",
    "status": ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (calendar group, grade C, "
               "credibility 4); optimise-stage runs queued in both markets. " + PASS_RULE_PORTFOLIO + " Because "
               "the book is in cash most sessions, the excess-CAGR test is read beside the SELECTION line (the "
               "index held at the same exposure): the effect is real only if those few sessions beat the index's "
               "average session after costs."),
    "thesis": (
        "Money arrives on a schedule: wages, pension and retirement-plan contributions and fund inflows land "
        "around the turn of each month and are invested in the first days of the new one. Ariel (1987) and "
        "Lakonishok & Smidt (1988) found the turn-of-month sessions earned most of the US index's return over "
        "decades; McConnell & Xu (2008) found it still present from 1987 to 2005 and in 30 of 35 countries. "
        "Weaker since, hence the catalogue's C, credibility 4."
    ),
    "how_it_works": (
        "**The series.** The market's benchmark: SPY in the US, the Nifty 500 index in India.",
        "**The window.** The last {days_before} trading session(s) of a month and the first {days_after} of the "
        "next, counted in the series' own sessions. Month ends and starts are known in advance (exchange "
        "holiday calendars are published a year ahead), so marking them is not hindsight.",
        "**The trade.** Bought at the close of the session before the window opens, sold at the close of its "
        "last session, {cost_bps} basis points a side; fully invested inside the window, in cash outside it.",
    ),
    "entry_rules": (
        "Buy the whole book of the index at the close of the session before the month's last {days_before} "
        "session(s), {cost_bps}bps.",
    ),
    "exit_rules": (
        "Sell at the close of the new month's session {days_after}, {cost_bps}bps. No stop.",
    ),
    "caveats": (
        "**India's series is an index, not a fund.** The Nifty 500 cannot be bought directly; a real book uses a "
        "fund or a future, with tracking difference and spread on top of the {cost_bps}bps charged.",
        "**Cash earns nothing here**, and the book is in cash about four sessions in five, so the headline CAGR "
        "understates what an account earning interest would make. The SELECTION line is the fair comparison.",
        "**As a standalone book, not the overlay the catalogue suggests.** An overlay (extra exposure at the "
        "turn on top of a momentum book) is a different construction; this measures whether the effect exists "
        "in these years at all, which the overlay would need first.",
        "**No dividends** on either the strategy or the benchmark.",
    ),
}


class TurnOfMonthStrategy(PortfolioStrategy):
    """Hold the index over the turn of each month (Lakonishok & Smidt 1988)."""

    key = DOC["key"]
    doc = DOC
    family = "turn_of_month"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "First version: the benchmark held from the close before the month's last {days_before} session(s) to "
         "the close of the new month's session {days_after}, {cost_bps}bps a side, cash otherwise."),
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

    effect = "turn_of_month"
    days_before = 1
    days_after = 3
    cost_bps = 5.0
    run_note = ("Held over the last {days_before} session(s) of each month and the first {days_after} of the next "
                "(Lakonishok & Smidt's window).")

    param_docs = (
        ("Sessions before the turn", "days_before", "The month's last sessions held."),
        ("Sessions after the turn", "days_after", "The new month's first sessions held."),
        ("Cost per side", "cost_bps", "Basis points on each buy and sale."),
    )
