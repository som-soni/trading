"""Internal bar strength (IBS) reversion on the market index -- buy a close near the day's low.

IBS = (close - low) / (high - low): 0 when the index closes at its low, 1 at its high. Practitioner
research on index ETFs (Pagonidis, "The IBS Effect", NAAIM 2013; widely repeated by quant blogs) found
that a close in the bottom fifth of the day's range is followed by an above-average next day, and a close
in the top fifth by a below-average one, in US and other index ETFs since the 1990s. The catalogue grades
it B (published backtests, not peer-reviewed or costed independently), credibility 2.

Run by `index_timing`: at each close, a rule says whether to own the index over the next session.
"""

from ..strategies.base import PortfolioStrategy
from ..strategies.swing_base import PASS_RULE_PORTFOLIO

DOC = {
    "key": "ibs_reversion",
    "name": "IBS reversion (index)",
    "description": "Buy the market index at a close in the bottom {ibs_entry} of the day's range; sell at the first "
                   "close above the previous day's high, or after {max_hold} sessions.",
    "status": ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (snap-back group, grade B, "
               "credibility 2); optimise-stage runs queued in both markets. " + PASS_RULE_PORTFOLIO + " In cash "
               "most sessions, so it is read beside the SELECTION line (the index at the same exposure)."),
    "thesis": (
        "A close at the bottom of the day's range marks selling that ran out of time rather than reasons; on a "
        "diversified index, which cannot collapse on one company's news, that selling tends to reverse the next "
        "day. Practitioner studies of index ETFs (Pagonidis 2013 and many replications on quant blogs) found "
        "low-IBS closes followed by above-average next-day returns. Short-horizon index reversal is also "
        "consistent with the liquidity-provision reading of short-term reversal (Nagel 2012). The catalogue "
        "grades it B, credibility 2: published backtests, no peer-reviewed or costed independent test."
    ),
    "how_it_works": (
        "**The series.** The market's benchmark: SPY in the US, the Nifty 500 index in India.",
        "**Signal.** At a session's close, IBS = (close − low) ÷ (high − low) below {ibs_entry}. A session with "
        "no range has no IBS and never signals. No trend filter.",
        "**Trade.** Bought at that close, {cost_bps} basis points a side, the whole book.",
        "**Exit.** Sold at the first later close above the previous session's high, or at the close of session "
        "{max_hold} after the buy, whichever comes first. No stop.",
    ),
    "entry_rules": ("Buy the index at a close whose IBS is below {ibs_entry}, {cost_bps}bps.",),
    "exit_rules": (
        "Sell at the first close above the previous session's high, or at the close of session {max_hold} after "
        "the buy, {cost_bps}bps. No stop and no target.",
    ),
    "caveats": (
        "**India's series is an index, not a fund.** A real book uses a fund or a future, whose own highs and "
        "lows (and so IBS) differ, with tracking difference and spread on top of the {cost_bps}bps.",
        "**Costs against a small edge.** The expected gain per trade is a fraction of a percent; {cost_bps}bps a "
        "side is realistic for SPY, optimistic for an Indian index fund.",
        "**The fill is the signal close.** The IBS is only known at the close, and the trade buys that same "
        "close; in practice that needs a market-on-close order placed minutes before the end on an estimate.",
        "**No stop.** A decline is held until the exit or the time limit.",
        "**Cash earns nothing here.**",
    ),
}


class IbsReversionStrategy(PortfolioStrategy):
    """Buy the index at a close near its low (internal bar strength)."""

    key = DOC["key"]
    doc = DOC
    family = "ibs_reversion"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "First version: the benchmark bought at a close with IBS below {ibs_entry}, sold at the first close "
         "above the previous high or after {max_hold} sessions, {cost_bps}bps a side, cash otherwise."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"])
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "mean_reversion"
    selection = "time_series"
    style = "snapback"
    horizon = "swing"
    runner = "index_timing"

    effect = "ibs"
    ibs_entry = 0.2
    max_hold = 5
    cost_bps = 5.0
    run_note = ("Bought at a close with IBS under {ibs_entry}; sold at the first close above the previous high or "
                "after {max_hold} sessions.")

    param_docs = (
        ("IBS entry", "ibs_entry", "Buy when (close − low) ÷ (high − low) is below this."),
        ("Maximum hold", "max_hold", "Sessions before the position is sold regardless."),
        ("Cost per side", "cost_bps", "Basis points on each buy and sale."),
    )
