"""52-week-high proximity, ranked across stocks -- George & Hwang (2004), as a portfolio strategy.

George and Hwang ("The 52-Week High and Momentum Investing", Journal of Finance, 2004) ranked stocks by
how close their price sits to its 52-week high and found that the nearest outperform the furthest, that
this explains most of what 12-month momentum earns, and that unlike momentum it does not reverse in the
long run. Their explanation is anchoring: investors treat the 52-week high as a reference and are slow to
bid a stock through it on good news.

Here the trend template already USES the 52-week high, as a pass/fail gate (within 25% of it). That is a
different test from ranking every liquid stock by the ratio and holding the nearest; the catalogue
(research/strategy-catalog-swing.md §4) names this, grade A, as the first untested idea to try.

No loop of its own: the universe, floors, fills, costs and rebalance are `baseline.run`'s, with the
`high52` ranker (`baseline.score_matrix`). The 200-day trend test is off, because George and Hwang used
none and the ratio already measures where the price sits.
"""

from ..marketdata import corporate_actions
from ..strategies.base import PortfolioStrategy
from ..strategies.swing_base import PASS_RULE_PORTFOLIO
from .baseline import TRADING_DAYS
from .baseline import high52_tiebreak as HIGH52_TIEBREAK  # noqa: F401  (rendered and fingerprinted here)

DOC = {
    "key": "high52_rank",
    "name": "52-week-high proximity",
    "description": "Rank liquid stocks by their close over their 52-week high and hold the {top_n} nearest, "
                   "rebalanced every month-end.",
    "status": ("NOT YET RUN. v1.0 implemented 2026-11-15 from the swing catalogue (relative-strength rank / "
               "breakout group, grade A, credibility 4); optimise-stage runs queued in both markets. "
               + PASS_RULE_PORTFOLIO),
    "thesis": (
        "Investors anchor on the 52-week high: good news that would carry a stock through it is under-reacted "
        "to, so stocks trading at or near their highs keep drifting up. George & Hwang (2004) found that the "
        "nearest-to-high stocks beat the furthest by about 0.5% a month in US data from 1963 to 2001, that this "
        "explains most of 12-month momentum's return, and that it does not reverse later. The catalogue grades "
        "it A (independent replications in other markets), credibility 4."
    ),
    "how_it_works": (
        "**Universe.** The momentum baseline's: stocks above the market's turnover floor (the 20-day average "
        "of close × volume) and price floor, ETFs and funds out, ranked within the {liquidity_top} most liquid.",
        "**Score.** The close divided by the highest close of the last {lookback} sessions: 1.0 at a new high, "
        "0.6 forty percent below it. Read on total-return closes, so a special dividend or demerger does not "
        "look like a fall.",
        "**Selection.** At every month-end close, the {top_n} highest scores, equal weight. No 200-day trend "
        "test (the paper used none). A stock at its high scores exactly 1.0, so on a strong month-end many tie; "
        "{HIGH52_TIEBREAK} × the 12-1 return is added to every score, which orders tied names by momentum and is "
        "too small to reorder any others.",
        "**Trades.** At the month-end close, {cost_bps} basis points a side. Names that left the top {top_n} "
        "are sold; new ones bought; the rest resized to equal weight.",
    ),
    "entry_rules": (
        "Bought at a month-end close when among the {top_n} highest close ÷ {lookback}-session high, "
        "{cost_bps}bps a side.",
    ),
    "exit_rules": (
        "Sold at the next month-end close where it is no longer in the top {top_n}. No stop and no target.",
    ),
    "caveats": (
        "**Ties at the high are broken by momentum.** Many stocks sit exactly at their 52-week high on a strong "
        "month-end; the paper used deciles, so ties did not matter there. Here they are ordered by 12-1 momentum, "
        "so in a strong market this book and the momentum baseline hold overlapping names.",
        "**Closes, not highs.** The paper's 52-week high is the highest daily price; this uses the highest "
        "close, so a stock that spiked intraday and closed lower reads nearer its high than the paper would "
        "say.",
        "**Concentrated, not deciles.** The paper held the top 30% against the bottom 30%; this holds {top_n} "
        "names long only, the way the rest of this project's ranking books do, so its result includes the "
        "market's own move.",
        "**Survivorship.** Today's stock lists; delisted names are missing.",
    ),
}


class High52RankStrategy(PortfolioStrategy):
    """Hold the liquid stocks nearest their 52-week highs (George & Hwang 2004)."""

    key = DOC["key"]
    doc = DOC
    family = "high52_rank"
    version = "1.0"
    changelog = (
        ("1.0", "2026-11-15",
         "First version: the baseline's universe, ranked by close ÷ {lookback}-session high, top {top_n} equal "
         "weight at month-end, no 200-day test, {cost_bps}bps a side."),
    )
    name = DOC["name"]
    description = DOC["description"]
    status = DOC["status"]
    thesis = DOC["thesis"]
    how_it_works = tuple(DOC["how_it_works"])
    caveats = tuple(DOC["caveats"]) + (corporate_actions.CAVEAT_HELD,)
    entry_rules = tuple(DOC["entry_rules"])
    exit_rules = tuple(DOC["exit_rules"])

    behaviour = "trend_momentum"
    selection = "cross_sectional"
    style = "rank"
    horizon = "positional"

    rank = "high52"
    top_n = 20
    lookback = TRADING_DAYS
    skip = 0
    rebalance = "ME"
    trend_filter = False
    cost_bps = 20.0
    liquidity_top = 1000

    param_docs = (
        ("Ranking", "rank", "high52: the close over the highest close of the lookback."),
        ("Tie-break", "HIGH52_TIEBREAK", "Weight on the 12-1 return added to every score, to order names tied at the high."),
        ("Holdings", "top_n", "Names held, equal weight."),
        ("High window", "lookback", "Sessions in the 52-week high."),
        ("Skip", "skip", "Sessions the score is lagged; 0 reads the rebalance close."),
        ("Rebalance", "rebalance", "Pandas offset alias; ME is month-end."),
        ("Cost per side", "cost_bps", "Basis points on every buy and sale."),
        ("Liquidity cutoff", "liquidity_top", "Only the N most liquid names that pass the floors are ranked."),
    )
