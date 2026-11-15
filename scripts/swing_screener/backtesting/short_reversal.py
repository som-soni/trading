"""Short-term reversal on liquid stocks -- Jegadeesh (1990) and Lehmann (1990), as a weekly portfolio.

Both papers found that stocks which fell most over the last week or month tend to rebound over the next,
and Nagel (2012) reads the rebound as pay for supplying liquidity when many sell at once. It is the
textbook counterweight to momentum, which is why 12-1 momentum skips the last month. It is also the
anomaly costs eat most completely: a weekly book of last week's losers turns over almost entirely every
week. The catalogue (research/strategy-catalog-swing.md §4) names it, grade C, credibility 4, as the second
untested idea, "with costs modelled honestly".

So the universe is narrowed to the most liquid names (where the spread is smallest and the effect, per
the literature, weakest -- the honest place to test whether anything survives), and the cost is
`cost_bps` a side, several times the momentum baseline's.

No loop of its own: `baseline.run` with the `reversal` ranker (`baseline.score_matrix`), a weekly
rebalance and the 200-day trend test off (losers are what it buys).
"""

from ..marketdata import corporate_actions
from ..strategies.base import PortfolioStrategy
from ..strategies.swing_base import PASS_RULE_PORTFOLIO

DOC = {
    "key": "short_reversal",
    "name": "Short-term reversal",
    "description": "Each week, buy the {top_n} liquid stocks that fell most over the last {lookback} sessions; "
                   "hold a week.",
    "status": ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (snap-back group, grade C, "
               "credibility 4); optimise-stage runs queued in both markets. " + PASS_RULE_PORTFOLIO),
    "thesis": (
        "When many holders sell one stock at once, its price is pushed below what it is worth, and whoever buys "
        "from them is paid a few percent for the liquidity when it rebounds. Jegadeesh (1990) and Lehmann (1990) "
        "found last month's and last week's losers beat the winners the following period; the effect is "
        "peer-reviewed and replicated, but it is largest in small, illiquid stocks, has shrunk since the 1990s, "
        "and its turnover means costs take most of it. The catalogue grades it C, credibility 4."
    ),
    "how_it_works": (
        "**Universe.** The momentum baseline's floors (turnover, price; ETFs and funds out), then only the "
        "{liquidity_top} most liquid of what passes, by 20-day average traded value: the liquid end, where "
        "costs are smallest.",
        "**Score.** Minus the return over the last {lookback} sessions, so the biggest losers rank first. "
        "Total-return closes, so a special dividend is not counted as a loss.",
        "**Selection.** At the last session of each week, the {top_n} highest scores (the {top_n} worst "
        "performers), equal weight. No 200-day test: a falling stock is exactly what it buys.",
        "**Trades.** At that close, {cost_bps} basis points a side. Every name not in the new {top_n} is sold, "
        "so the book turns over most of its holdings each week.",
    ),
    "entry_rules": (
        "Bought at a week's last close when among the {top_n} worst {lookback}-session returns of the "
        "{liquidity_top} most liquid stocks, {cost_bps}bps a side.",
    ),
    "exit_rules": (
        "Sold at the next week's last close unless it is again among the {top_n} worst. No stop and no target.",
    ),
    "caveats": (
        "**Costs decide it.** Turnover is close to the whole book every week, so about {cost_bps}bps × 2 × 52 "
        "comes off a year before any edge. India's securities transaction tax alone is 0.1% of each delivery "
        "buy and sale, so the true India cost is near the {cost_bps}bps charged here and higher on thin days.",
        "**No stop.** A loser that keeps falling is held a week and bought again if it is still among the worst; "
        "a stock collapsing on news (a fraud, a failed trial) is exactly the kind of 'loser' that does not "
        "revert, and the rule cannot tell it from a liquidity sell-off.",
        "**Close-to-close.** The score and the fill are the same close. The papers skip a day between ranking "
        "and buying to avoid bid-ask bounce; here the fill at the ranking close includes that bounce, which "
        "flatters the result. A next-open fill (`--fill next_open`) is the variant that removes it.",
        "**Survivorship.** Today's stock lists. The losers that went on to delist are missing, which flatters a "
        "buy-the-losers book more than most.",
    ),
}


class ShortReversalStrategy(PortfolioStrategy):
    """Buy last week's biggest losers among the liquid stocks; rebalance weekly."""

    key = DOC["key"]
    doc = DOC
    family = "short_reversal"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "First version: the {liquidity_top} most liquid stocks, the {top_n} worst {lookback}-session returns, "
         "equal weight, weekly at the close, no 200-day test, {cost_bps}bps a side."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"]) + (corporate_actions.CAVEAT_HELD,)
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "mean_reversion"
    selection = "cross_sectional"
    style = "snapback"
    horizon = "swing"

    rank = "reversal"
    top_n = 20
    lookback = 5
    skip = 0
    rebalance = "W-FRI"
    trend_filter = False
    cost_bps = 20.0
    liquidity_top = 300

    param_docs = (
        ("Ranking", "rank", "reversal: minus the return over the lookback, so losers rank first."),
        ("Holdings", "top_n", "Names held, equal weight."),
        ("Lookback", "lookback", "Sessions of return ranked (5 = a week, Lehmann; 21 = a month, Jegadeesh)."),
        ("Skip", "skip", "Sessions the score is lagged; 0 ranks on the rebalance close itself."),
        ("Rebalance", "rebalance", "Pandas offset alias; W-FRI trades at each week's last session."),
        ("Cost per side", "cost_bps", "Basis points on every buy and sale."),
        ("Liquidity cutoff", "liquidity_top", "Only the N most liquid names that pass the floors are ranked."),
    )
