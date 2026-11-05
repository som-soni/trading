"""Earnings gaps and episodic pivots — buying the big results-day gap.

The Learn guide `research/learn-strat-earnings-gaps.md` is the specification; this is its
testable form. A stock reports, jumps a long way on enormous volume and closes near the day's
high. The trade buys a break of that reaction day's high, stops under its low, and trails the
rest out on the 20-day average. Pradeep Bonde calls it the episodic pivot — an episode of news
that pivots a stock from one price level to another; Kristjan Kullamägi trades the same shape
intraday.

Why it is worth testing beside the rest of the shelf
----------------------------------------------------
Every other per-symbol strategy here keys on chart STRUCTURE — a base, a channel, a pullback —
and that family has not picked better than the index held at the same exposure in any of the
eight runs on the 2013 cohort (`research/selection-vs-drag.md` §7). This one keys on an EVENT
instead. It is the only remaining strategy in the Learn list that does, which is the whole
reason to build it: it tests a different claim, not a tenth variation of the failing one.

Locating the news without a calendar
------------------------------------
The guide asks for "results announced in the window from 3 days before this session to this
session", and warns that without that link "you buy random spikes". No announcement calendar is
stored before 2025-10, so the link is made the other way round: a reaction day must fall inside
a window bracketed by data that IS recorded — at least {CATALYST_MIN_DAYS} days after a stored
quarter end, and no later than {CATALYST_FILED_GRACE} days after that quarter's filing. A
company announces after the quarter closes and files at or after it announces, so the true
announcement always lies inside that bracket. It is looser than a calendar — roughly a third of
the quarter rather than four days — but it is made of recorded facts rather than inferred ones,
which is the lesson of the blackout work in `backtesting/spec.py`: an inferred announcement date
carries a median error of 13 days and is not worth keying a rule on.

Since 1.3, where an announcement IS recorded the guide's own rule is used instead: the reaction day
must come within {ANNOUNCE_WINDOW_DAYS} calendar days after the company published results. India
has these back to 2007 (`marketdata/financials.py`, `results_announcements`: NSE's broadcast time for
every results filing, including the pre-2017 ones that carry no XBRL document, and since 1.4 the date
of the board meeting that approved the results, which in the older feed is usually days earlier than
the filing's broadcast). Since 1.9 the US has them too, back to 2005:
each 8-K with Item 2.02, which a company files the day it releases results. The bracket remains for a
company with no recorded announcements -- a foreign issuer filing 6-Ks, or an Indian company the exchange
does not list.

Honest limits
-------------
* The bracket admits a non-results spike that happens to land in the window. It narrows the
  false positives, it does not eliminate them.
* The guide's optional year-on-year profit filter is NOT implemented: it needs point-in-time
  fundamentals on the reaction day, which this path does not carry. Its neglect filter IS, as a
  watch flag, because the guide marks it optional and untested.
* The guide's partial sale after 3-5 sessions and its 10-session time stop are not modelled —
  the shared exit engine's trailing-average mode carries the initial stop and the trail, and
  nothing else. So this measures the stop-and-trail core of the method, not Kullamägi's
  management of it.
* India releases results mid-session as often as overnight, so the open-gap test fires less
  there; the close-to-close move is the test that travels, which is why either one qualifies.
"""

import pandas as pd

from ..marketdata import corporate_actions
from ..config.base import MarketConfig
from ..core.context import StockContext
from .base import (
    tradable_point_in_time,
    DOWNGRADE_MAP,
    LABELS,
    Decision,
    PlanChoice,
    Strategy,
    StrategyResult,
    TradePlan,
)
# Reused rather than copied: the suffix-driven market lookup and the tick rounding already exist,
# and a second copy of either is the duplication CLAUDE.md warns about.
from .rs_leaders import _market_of
from .trend_pullback import round_tick

# ---- the reaction day (guide §3, "Setup")
MIN_MOVE_PCT = 10.0        # close at least this far above the previous close
MIN_GAP_PCT = 5.0          # ...or the open at least this far above it
MIN_REL_VOLUME = 3.0       # volume against its 50-day average
# 1.8: the 50-day average the reaction day is measured against ends the session BEFORE it. Ending on the day
# itself put the spike in its own yardstick: SPOT's 22 Oct 2026 results gap traded 3.10x the 50 sessions before
# it but 2.97x an average that included it, and failed the 3x test. 0 = the average includes the day (1.7).
REL_VOL_PRIOR = 1
MIN_CLOSE_POS = 0.70       # (close - low) / (high - low): closed in the top of its range
REQUIRE_GAP = 0            # 1 = the reaction day must OPEN at least MIN_GAP_PCT up; a close-only move
                           # no longer qualifies. Research switch, off (1.5).
NEGLECT_LOOKBACK = 60      # sessions over which "already extended" is measured
NEGLECT_MAX_RUN_PCT = 30.0 # a stock up more than this into the news is noted, not refused

# ---- Kullamägi's own version (1.7): research switches, all OFF, so a default run trades as 1.6.
# His definition (qullamaggie.com, "How to master a setup: Episodic Pivots", 2021): a gap of 10%+ on
# massive volume, bought on the opening-range high of day ONE, stopped at the low of the day; best
# after 3-6+ months sideways; for an earnings EP, ideally big earnings and sales growth.
ENTRY_AT_CLOSE = 0         # 1 = buy the reaction day's own close, stopped at its low: his day-one entry
                           # as closely as daily bars allow (the default waits for day TWO to break the
                           # whole day's high, which also widens the stop to the full day's range)
MIN_GROWTH_PCT = 0.0       # G6: above 0 = the announced quarter's sales OR EPS up at least this much on
                           # the same quarter a year earlier; 0 = off
NEGLECT_GATE = 0           # 1 = G7: refuse a stock already up more than NEGLECT_MAX_RUN_PCT over the
                           # NEGLECT_LOOKBACK sessions BEFORE the reaction day (W1 only notes it)
SCREEN_GATE = 1            # G1, the Above-the-200-day screen: 1 = enforced (as shipped); 0 = off. He
                           # buys neglected stocks, which often sit below the 200-day: G1 refused 60%
                           # of the US 10%+ gaps of 2014-2021 before any other rule looked at them

# ---- the catalyst bracket (see the module docstring)
CATALYST_MIN_DAYS = 10     # a reaction day sits at least this far after the quarter end
CATALYST_FILED_GRACE = 5   # ...and no later than this many days after that quarter's filing
# 1.8: a quarter stored without a filing date -- a foreign issuer, filing 6-K/20-F rather than 10-Q (187 US
# symbols, SPOT among them) -- links a reaction up to this many days after its quarter end. Without it they
# could never trade. 0 = such quarters link nothing (1.7).
CATALYST_UNFILED_DAYS = 50
ANNOUNCE_WINDOW_DAYS = 3   # with recorded announcements: results published at most this many calendar
                           # days before the reaction day, or on it -- the guide's own rule

# ---- entry and risk (guide §3, "Entry" / "Initial stop")
ENTRY_BUFFER_PCT = 0.1     # the buy-stop sits this far above the reaction day's high
ENTRY_EXPIRY_BDAYS = 5     # how long the buy-stop waits before it is cancelled
REACTION_WINDOW = 5        # sessions a reaction day keeps offering its setup
MAX_STOP_PCT = 12.0        # widest stop, as a share of the entry
MAX_STOP_ATR = 1.5         # ...or this multiple of the 14-day ATR, whichever binds first
# 1.8, S2: the flag after the gap -- the second buy of a results-gap trader, after the gap day's own breakout
# has passed (Venu's "PEG, then flags/bases"). From the session after the reaction window to FLAG_WINDOW
# sessions after the reaction day, the stock rests: its range since the reaction day is at most
# FLAG_MAX_RANGE_PCT, no close has filled the gap (fallen back to the close before the reaction), it has
# rested at least FLAG_MIN_DAYS sessions, and today's close is within FLAG_COIL_PCT under the flag's high.
# A buy-stop goes above the flag's high, stopped under its low; only MAX_STOP_PCT caps that stop (the ATR
# cap is about the gap day's own range). FLAG_ON = 0 turns S2 off.
FLAG_ON = 1
FLAG_WINDOW = 25
FLAG_MIN_DAYS = 5
FLAG_MAX_RANGE_PCT = 12.0
FLAG_COIL_PCT = 8.0
NOMINAL_TARGET_R = 3.0     # for sizing and reporting only — the real exit is the trail

# ---- the market (G5)
MARKET_GATE = 0            # 1 = buy only while the market index closes above its 200-day average
                           # (backtesting/regime.py index_sma). Research switch, off (1.5).
#: The index G5 reads: the small-cap segment, where an India reaction's follow-through was measured
#: to depend on it (2018: the Smallcap 250 fell 26.8% and four of five trades under it lost).
MARKET_GATE_INDEX = {"india": "NIFTYSMLCAP250.NS", "us": "IWM"}

EG01 = "S1"   # EG-01: the break of the reaction day's high
EG02 = "S2"   # 1.8: the break of the flag that follows the reaction (FLAG_*)


class EarningsGapStrategy(Strategy):
    selection = "time_series"
    family = "earnings_gaps"
    version = "1.9"
    # 1.7 adds gates to evaluate(), so signal_version is NOT pinned: a pin across a scan change would
    # replay old detections (CLAUDE.md). It defaults to `version`, which rescans.
    changelog = (
        ("1.9", "2026-11-05",
         "US reactions are tied to recorded results announcements, as India's are: each 8-K with Item 2.02, "
         "back to 2005 (the `announcements` job, `financials.sec_announcements`). Until now every US company "
         "used the quarter-end-to-filing bracket, about five weeks wide and widest after a fourth quarter, "
         "whose 10-K lands weeks after the results, so a US run admitted non-results spikes India refused. "
         "A company with no 8-K 2.02 recorded keeps the bracket. Bumped by hand: no constant moved, the data "
         "did."),
        ("1.8", "2026-11-04",
         "Two changes from Spotify's October 2026 results gap, which a PEG trader bought and 1.7 refused. (1) The "
         "reaction day's volume is measured against the 50 sessions BEFORE it (REL_VOL_PRIOR): an average ending "
         "on the day includes its own spike -- SPOT traded 3.10x the sessions before but 2.97x that average, and "
         "failed MIN_REL_VOLUME. (2) S2, the flag after the gap (FLAG_*): once the gap day's own window has passed, "
         "a tight rest of at least FLAG_MIN_DAYS sessions that has not filled the gap, coiled under its high, "
         "places a buy-stop above that high, stopped under the flag's low. Changes evaluate(); cached signals are "
         "rescanned. (3) A quarter stored without a filing date -- a foreign issuer such as Spotify, 187 US symbols -- links a reaction up to CATALYST_UNFILED_DAYS after its quarter end; they could never trade before."),
        ("1.7", "2026-11-02",
         "Kullamägi's own version, as four research switches, each defaulting to the shipped "
         "behaviour, so a default run trades "
         "exactly as 1.6. His definition differs from the guide's in three ways that daily bars can "
         "express: he buys on the reaction day itself (ENTRY_AT_CLOSE buys its close, stopped at its "
         "low, where 1.6 waits for the next session to break the whole day's high -- later, higher, and "
         "with a stop as wide as the day's range, which the {MAX_STOP_ATR} ATR cap then refuses); he "
         "wants earnings and sales growth (G6, MIN_GROWTH_PCT: the announced quarter's sales or EPS up "
         "that much on a year earlier, from fundamentals/growth.growth_series); and the best EPs come "
         "after months sideways (G7, NEGLECT_GATE: W1's test as a gate, measured up to the session "
         "BEFORE the reaction so the gap itself does not count); and he buys neglected stocks, which "
         "often sit below the 200-day (SCREEN_GATE=0 turns off G1, which refused 60% of the US 10%+ "
         "gaps of 2014-2021 before any other rule saw them). His 10% gap is REQUIRE_GAP=1 with "
         "MIN_GAP_PCT=10. His opening-range entry and non-earnings catalysts need intraday prices "
         "and a news history, neither of which is stored."),
        ("1.6", "2026-10-31",
         "Backtest mechanics, no rule changed (backtesting/portfolio_sim, REVIEW-2026-10-31 item 7): a "
         "fill now sees only what had happened by its own moment in the session. An exit frees its "
         "slot and cash only for a fill at or after it, so a position sold at a session's close, or by "
         "a stop during it, no longer pays for a buy that filled at that session's open. Fills are "
         "sized from the other positions' previous closes, not from the fill session's close. The fill "
         "session now tests the stop: a session that triggers the buy-stop and also trades down to the "
         "stop sells at the stop, because the bar does not say which came first and the stop wins the "
         "tie, as on every other session; before, such a buy was held overnight. signal_version stays "
         "at 1.5: only the simulator changed, so the cached signal rows still describe this scan. "
         "Results move, so stored runs of earlier versions are not comparable."),
        ("1.5", "2026-10-31",
         "Two research switches, both OFF, so a default run trades exactly as 1.4: REQUIRE_GAP (G2 admits "
         "only a reaction day that opened at least {MIN_GAP_PCT}% up) and MARKET_GATE (a new gate, G5: the "
         "small-cap index above its 200-day, the shared index_sma rule). Both came from India's 35 "
         "loosened-G2 trades over 2013-2021 -- close-only moves averaged -0.57R against +0.97R for gaps, "
         "and trades under a falling Smallcap 250 -0.17R against +0.75R -- so they are tested on the US "
         "optimise window, which those trades did not inform, before either is turned on. G5 is evaluated "
         "last so G1-G4 keep their codes."),
        ("1.4", "2026-10-29",
         "G3's India announcement dates include the board meeting that approved each quarter's results "
         "(NSE's board-meeting feed, `financials.nse_results_meetings`), beside NSE's broadcast of the results "
         "filing. The filing's broadcast was mostly late: on 80 sampled companies over 2013-2021, 77% of "
         "stored broadcast dates came after the meeting and 27% by eight days or more (84-99% each year to "
         "2018), so a reaction on the morning after the meeting failed G3 -- TNPETRO's board met on "
         "2018-10-24, the stock rose 11.8% on the 25th, and the filing is dated the 26th. On those companies "
         "the qualifying reaction days tied to results go from 57 to 114 of 807. The rule itself is "
         "unchanged; a meeting counts once it is past, and it is intimated in advance, so this reads "
         "nothing from the future. Bumped by hand: no constant moved."),
        ("1.3", "2026-10-27",
         "G3 uses the guide's own rule where a company's results announcements are recorded: the results "
         "must have been published at most {ANNOUNCE_WINDOW_DAYS} calendar days before the reaction day, or "
         "on it. India now has them back to 2007 -- NSE's broadcast time for every results filing, including "
         "the pre-2017 ones with no XBRL document (`results_announcements`). Before, India used the "
         "quarter-end-to-filing window like the US, and its stored quarters began in March 2020, so the "
         "2013-2021 optimise window held three Indian trades and the market could not be tuned at all. "
         "Checked against the guide's worked example: Kaynes published on 2023-05-16 and gapped on the 17th, "
         "inside the window. The US has no announcement history and keeps the window, so a company with no "
         "recorded announcements is judged exactly as before."),
        ("1.2", "2026-10-25",
         "Backtest mechanics, no rule changed: special dividends and demergers are credited "
         "(marketdata/corporate_actions.py). On the ex-date a held position receives the cash and its "
         "entry, stop, target and other levels move down by the payout; before, the stored close fell by "
         "it and the trade booked the payout as a loss, or was stopped out by it. An order resting in the "
         "stock that day is cancelled. Only trades held across such an ex-date move. Stored prices were "
         "also corrected where the source left a split unadjusted before its year-start (MOTILALOFS and "
         "GPIL 2024-01-01, PARAS 2025-01-01 and others) or carried a stray bar (marketdata/splits.py "
         "correct)."),
        ("1.1", "2026-10-22",
         "The backtest takes trades. A signal now places its buy-stop (entry_signal_fired is true "
         "whenever the setup is present, as for Minervini's pivot buy), where before it was never "
         "true, so the backtest dropped every setup before a plan was made. The backtest command "
         "adds --accept-labels 'TRADE ON TRIGGER', the strategy's best decision; the default "
         "accepts only TRADE - HIGH CONFIDENCE, which it never reaches. No entry, stop or exit "
         "rule changed: 1.0 never traded in a backtest."),
        ("1.0", "2026-10-22",
         "First version, from the Learn guide: a results-day reaction of at least "
         "{MIN_MOVE_PCT}% close-to-close or a {MIN_GAP_PCT}% opening gap, on at least "
         "{MIN_REL_VOLUME}x its 50-day volume, closing in the top {MIN_CLOSE_POS} of its range "
         "and bracketed to a stored results window; bought on a break of that day's high with "
         "the stop under its low. Built as the one EVENT-driven per-symbol strategy on the "
         "shelf, because the structure-driven family has no positive selection on the 2013 "
         "cohort. The guide's year-on-year growth filter and its partial sale and time stop are "
         "not implemented -- see the module docstring."),
    )
    key = "earnings_gaps"
    name = "Earnings gaps"
    description = (
        "Buy the stock that jumps on its results — a large move on enormous volume, closing "
        "near the high — on a break of that day's high, stopped under its low."
    )
    style = "event"
    horizon = "swing"
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    gate_codes = ("G1", "G2", "G3", "G4", "G5", "G6", "G7")
    watch_codes = ("W1", "W2")
    setup_codes = (EG01, EG02)
    setup_names = {EG01: "Results-gap breakout", EG02: "Flag after a results gap"}
    gate_titles = {"G1": "Above the 200-day", "G2": "A results-day reaction",
                   "G3": "Linked to a results window", "G4": "Stop close enough to carry",
                   "G5": "Market above its 200-day", "G6": "Growth in the quarter announced",
                   "G7": "Not already extended into the news"}
    nominal_target = True
    min_bars = 260
    needs_ctx_extras = True
    # Read after the scan, never by evaluate(): a `--const` variant moving only these starts from the
    # shipped run's signal rows (base.Strategy.signal_exempt_consts) — the order expiry (signal_meta) and the nominal target (build_plans).
    signal_exempt_consts = ("ENTRY_EXPIRY_BDAYS", "NOMINAL_TARGET_R")
    extra_columns = ("reaction_date", "reaction_high", "reaction_low", "reaction_move_pct",
                     "reaction_rel_volume", "reaction_close_pos")
    extra_numeric_columns = ("reaction_high", "reaction_low", "reaction_move_pct",
                             "reaction_rel_volume", "reaction_close_pos")
    backtest_args = "--exit-mode ma --no-target --ma-col sma20 --accept-labels 'TRADE ON TRIGGER'"

    thesis = (
        "A large surprise changes what a business is worth, but investors do not all act on the "
        "same day: funds need meetings, analysts rebuild models over weeks, and some buyers wait "
        "for the next quarter to confirm the change. That slow adjustment is the same "
        "under-reaction that post-earnings drift trades, taken at its sharpest point. The volume "
        "is what separates the two cases — a jump on ordinary turnover is a few traders chasing a "
        "headline, while a jump on {MIN_REL_VOLUME} times normal volume means large holders were "
        "active, and if they are still buying they will keep buying for weeks."
    )
    # Every rule below was checked against the code that trades it: _reaction_day, evaluate,
    # build_plans, signal_meta and classify above, and portfolio_sim.simulate under this strategy's
    # backtest_args (--exit-mode ma --no-target --ma-col sma20 --accept-labels 'TRADE ON TRIGGER'). The rules come from the Learn guide
    # research/learn-strat-earnings-gaps.md; the page describes the code, and where it departs from
    # the guide is one caveat.
    how_it_works = (
        "The idea. A stock reports results, jumps a long way on heavy volume and closes near the "
        "day's high. The trade buys the break of that day's high and holds until the stock closes "
        "below its 20-day average. The rules are a testable, daily-bar form of the Learn guide on "
        "earnings gaps; where they depart from it is listed under Known caveats.",
        "Step 1 — the reaction day (G2). One of the last {REACTION_WINDOW} sessions with a big "
        "move, heavy volume and a close near the high. The exact tests are under Rules.",
        "Step 2 — the news link (G3). Where the company's results announcements are recorded, the "
        "results must have been published at most {ANNOUNCE_WINDOW_DAYS} days before that day, or on "
        "it -- dated by the board meeting that approved them or by the exchange's broadcast of the "
        "filing, whichever fits. Where they are not, the day must fall inside a window built from the stored quarter-end "
        "and filing dates.",
        "Step 3 — the stop and the order (G4, Entry, Stop). The reaction day's low must be close "
        "enough to carry. Then a buy-stop waits just above the reaction day's high.",
        "Step 4 — the exit (Exit). The stop sells during the session if touched. Otherwise the "
        "first close below the 20-day average sells everything. There is no target and no other exit.",
        "Timing. Every check is made on a session's close. The order can fill from the next session "
        "on, during the day. The stop sells during the day; the 20-day exit sells at that day's close.",
    )
    caveats = (
        "Only stocks with stored quarterly results can ever trade. With nothing to link a move to, "
        "G3 refuses it. Without the link the trade would be buying random spikes, but it shrinks the universe hard: about 1,800 US and 580 Indian symbols "
        "had stored, dated quarters in October 2026. When the strategy was built, an alphabetical "
        "sample of 300 symbols a side had 113 US and 50 Indian ones covered; among those, the "
        "window linked 65% of US reaction days and 32% of Indian ones.",
        "Both markets tie a reaction to recorded announcements, the guide's rule: India the exchange's "
        "broadcast times and results board meetings, back to 2007; the US (since 1.9) each 8-K with Item "
        "2.02, back to 2005. An 8-K 2.02 also covers a mid-quarter update or pre-announcement, so a US "
        "reaction to one of those links too. A company with none recorded -- a foreign issuer filing 6-Ks, "
        "a symbol with no SEC CIK -- falls back to the quarter-end-to-filing window, about five weeks wide. "
        "(Before 1.3, India used the window too; before 1.9 every US company did.)",
        "The results link is a window, not a calendar. It runs from {CATALYST_MIN_DAYS} days after "
        "the quarter end to {CATALYST_FILED_GRACE} days after the filing — about five weeks at the "
        "median — so a non-results spike that lands inside it is admitted. In the US the filing is "
        "the SEC filing, and for a fourth quarter that is the annual report, which can come weeks "
        "after the announcement, so the window is widest there.",
        "Announcements are refreshed weekly in both markets (the `announcements` job). A results board meeting "
        "is intimated days ahead, so live it is usually stored before the reaction; one called at short "
        "notice, and a filing's broadcast, can be refused until the next refresh stores them. The "
        "backtest has every announcement and links it.",
        "Live, G3 can refuse a fresh reaction that the backtest would link. A quarter enters the "
        "results table only once its filing is stored. The backtest sees each quarter's eventual "
        "filing date, so it links a reaction that came days before the filing. The live screen "
        "cannot link it until the filing is fetched, and by then the {REACTION_WINDOW}-session "
        "window may have passed. The rule needs nothing from the future — the quarter ended at "
        "least {CATALYST_MIN_DAYS} days ago and was not filed more than {CATALYST_FILED_GRACE} days "
        "ago — but the code reads it only from stored filings, so expect fewer live candidates "
        "than the backtest finds.",
        "W1 includes the jump it is meant to come before. A neglect test should measure the rise "
        "before the news; W1 measures from {NEGLECT_LOOKBACK} sessions back to the signal session, so the "
        "reaction day's own jump is included, and a stock that sat flat and then gapped more than "
        "{NEGLECT_MAX_RUN_PCT}% is flagged. W1 never blocks a trade, so the backtest is unaffected; "
        "only the live note is misleading.",
        "Same-day ties are not ranked by relative volume. A code comment says relative volume "
        "ranks signals, but every signal scores the same, so when slots are scarce the order "
        "placed first is filled first.",
                "The strategy has no profit target by construction, so the reported reward-to-risk is "
        "always a nominal {NOMINAL_TARGET_R}R, not an expectation.",
        "**Where the code departs from the Learn guide.**\n\n"
        "- **G1, the 200-day:** the guide filters the market, not the stock, and likes turnarounds; "
        "here a stock below its 200-day is never bought, because every strategy draws from a screen.\n"
        "- **G2, the reaction day:** the guide measures the first session after the news; here any "
        "session in the {REACTION_WINDOW}-session window can be the reaction day, and G3 links it to "
        "results afterwards.\n"
        "- **G3, the news link:** the guide wants results announced from 3 days before the session to "
        "the session; here up to {ANNOUNCE_WINDOW_DAYS} days before, and about five weeks for a company "
        "with no recorded announcements.\n"
        "- **Universe:** the guide asks for $5 million or ₹5 crore of daily traded value and a $5 or "
        "₹50 price; here the market's liquidity floor applies and there is no price floor.\n"
        "- **W1, neglect:** the guide's optional filter is only a note here, because it is untested.\n"
        "- **Profit growth:** the guide's optional year-on-year filter is not implemented — it needs "
        "point-in-time fundamentals this path does not carry — so results are for the unfiltered setup.\n"
        "- **Trade management:** the guide's partial sale of a third after 3 to 5 sessions (stop to "
        "the entry) and its 10-session time stop are not modelled; the shared backtest's time stop "
        "and partial sale work differently, so this tests the stop-and-trail core only.\n"
        "- **Faster exit:** the guide's 10-day average for faster stocks is not used; every trade "
        "exits on the 20-day.\n"
        "- **Intraday entry:** the break of the reaction day's opening range cannot be tested on "
        "daily bars, so the buy comes a day later and higher.",
        corporate_actions.CAVEAT_TRADED,
    )
    status = (
        "INDIA: TOO FEW TRADES TO JUDGE. In-sample (optimise, 2013-2021) at v1.4, with board-meeting "
        "dates linking results to their reaction day, India makes 9 trades from 41 signals across 452 "
        "eligible stocks, against v1.3's 3 trades from 15: 0.35% CAGR at 5.8% exposure, max drawdown "
        "-5.8%, one winner in nine. That winner (HINDALCO 2016, +9.1R) carries the profit factor of 1.54; "
        "the other eight lost. Most bars stop at G2 -- a big, heavy-volume results-day move is rare -- "
        "not at the results link, so more dates cannot make India a strategy on their own. "
        "Otherwise not yet measured. Built as the shelf's only event-driven per-symbol strategy, to test "
        "whether keying on news rather than chart structure behaves differently from the "
        "structure family, which has no positive selection number on the 2013 cohort. Read its "
        "first run against the index held at the same exposure, not against its own CAGR: this "
        "strategy sits in cash most of the time, and cash drag and selection move in opposite "
        "directions."
    )
    gate_docs = {
        "G1": "The close is above the 200-day moving average (the Above-the-200-day screen's A1).\n\n"
              "- **Test:** the signal session's close is strictly above the 200-day simple average "
              "of closes.\n"
              "- **When:** on every signal session, not only on the reaction day.\n"
              "- **Effect:** a turnaround still below its 200-day is never bought.\n"
              "- **Switch:** SCREEN_GATE (it is {SCREEN_GATE}) at 0 turns G1 off, for the Kullamägi "
              "variant: he buys neglected stocks, which often sit below the 200-day.",
        "G2": "A results-day reaction in the last {REACTION_WINDOW} sessions: a big move on heavy "
              "volume that closed near the day's high.\n\n"
              "- **Window:** the signal session and the sessions just before it, {REACTION_WINDOW} "
              "in all. If several days qualify, the most recent is used, even when an older one "
              "would have passed G3 and it does not.\n"
              "- **Big move:** the close is at least {MIN_MOVE_PCT}% above the previous session's "
              "close, OR the open is at least {MIN_GAP_PCT}% above it. Either is enough; W2 marks a "
              "day that qualified on the gap alone. With the research switch REQUIRE_GAP at 1 "
              "(it is {REQUIRE_GAP}), the open must be at least {MIN_GAP_PCT}% up and a close-only "
              "move does not qualify.\n"
              "- **Heavy volume:** the day's volume is at least {MIN_REL_VOLUME} times its 50-day "
              "average: the simple mean of the 50 sessions ending the session BEFORE it, so the "
              "spike is not part of its own yardstick (REL_VOL_PRIOR, {REL_VOL_PRIOR}).\n"
              "- **For S2, the flag:** the reaction may be up to {FLAG_WINDOW} sessions old, if a "
              "flag has followed it (see S2).\n"
              "- **Close near the high:** (close − low) ÷ (high − low) is at least "
              "{MIN_CLOSE_POS}, where 0 is a close on the low and 1 a close on the high. A day with "
              "no range counts as 1.\n"
              "- **News:** nothing here looks at news. Any session in the window can be the "
              "reaction day; G3 makes the link to results afterwards.",
        "G3": "The reaction day is tied to a results announcement. Two ways, depending on what is "
              "stored for the company:\n\n"
              "- **Recorded announcements (India back to 2007, the US back to 2005):** results were published at most "
              "{ANNOUNCE_WINDOW_DAYS} calendar days before the reaction day, or on it. This is the "
              "guide's own rule. A quarter can carry several dates and any one qualifies: the day of "
              "the board meeting that approved the results (the results come out that day, often "
              "after the close, so they tie to the next session's move) and the exchange's broadcast "
              "time for the results filing, which in older years is often days later. In the US, "
              "the day of the 8-K with Item 2.02 the company filed with its results release.\n"
              "- **No recorded announcements (a US company with no 8-K 2.02 on file, such as a "
              "foreign issuer, and any Indian one the exchange does not list):** the window below.\n\n"
              "The window: the reaction day falls at least {CATALYST_MIN_DAYS} days after a quarter "
              "end and at most {CATALYST_FILED_GRACE} days after that quarter's filing.\n\n"
              "- **Data:** the stored quarterly results — each quarter's end date and filing date. "
              "A US filing date is when the quarter's figures were first filed with the SEC (the "
              "10-Q, or the annual 10-K for a fourth quarter). An Indian one is the date of the "
              "results filing on NSE. No announcement calendar is used.\n"
              "- **Window per quarter:** from the quarter end + {CATALYST_MIN_DAYS} calendar days "
              "to the filing date + {CATALYST_FILED_GRACE} calendar days, both ends included. The "
              "reaction day must lie inside the window of at least one stored quarter of that "
              "company.\n"
              "- **No filing date:** a quarter stored without one (a foreign issuer filing 6-K or "
              "20-F reports, not 10-Q) runs to the quarter end + {CATALYST_UNFILED_DAYS} calendar "
              "days instead.\n"
              "- **Why it holds:** a company announces after its quarter closes and files on or "
              "after the day it announces, so the announcement lies inside the window (unless it "
              "came within {CATALYST_MIN_DAYS} days of the quarter end).\n"
              "- **Width:** about five weeks at the median, so a non-results spike that lands "
              "inside the window is admitted too.\n"
              "- **No stored quarters:** the company cannot be linked and always fails.",
        "G4": "The reaction day's low is a stop the trade can carry: no more than {MAX_STOP_PCT}% "
              "and no more than {MAX_STOP_ATR} ATR below the trigger.\n\n"
              "- **Distance:** the trigger (the reaction high + {ENTRY_BUFFER_PCT}%) minus the "
              "reaction low.\n"
              "- **Percent cap:** the distance ÷ the trigger is at most {MAX_STOP_PCT}%.\n"
              "- **ATR cap:** the distance ÷ the 14-day ATR is at most {MAX_STOP_ATR}. The ATR is "
              "the signal session's, so it already includes the reaction day's own wide range.\n"
              "- **At the fill:** only the percent cap is tested again, on the price actually "
              "paid (see Entry).\n"
              "- **For S2, the flag:** the distance is from the flag's buy-stop to the flag's low, and "
              "only the percent cap applies.",
        "G5": "The market index closes above its 200-day average -- a research switch, OFF unless "
              "MARKET_GATE is 1 (it is {MARKET_GATE}). While off, G5 always passes.\n\n"
              "- **Index:** the small-cap segment -- the Nifty Smallcap 250 in India, IWM (Russell "
              "2000) in the US.\n"
              "- **Test:** the index's close on the signal session (its last close on or before it) "
              "is above its own 200-day simple average -- the shared index_sma regime rule, the "
              "same one the monthly portfolio runners use. An index too short to judge counts as on.\n"
              "- **Why it exists:** in India's 2013-2021 window, trades taken with the Smallcap 250 "
              "below its 200-day averaged -0.17R against +0.75R above it. Found on those trades, so "
              "it is tested on the US before it is adopted anywhere.",
        "G6": "The quarter the reaction announced grew -- a research switch, OFF unless MIN_GROWTH_PCT "
              "is above 0 (it is {MIN_GROWTH_PCT}). While off, G6 always passes.\n\n"
              "- **Test:** that quarter's sales OR its EPS is up at least {MIN_GROWTH_PCT}% on the same "
              "quarter a year earlier. Either is enough: Kullamägi notes that fast-growing companies "
              "with no earnings yet have worked as well as profitable ones.\n"
              "- **Which quarter:** the latest that ended at least {CATALYST_MIN_DAYS} days before the "
              "reaction day -- the one the results announced. Its figures are the news itself, so "
              "reading them on the reaction day is not look-ahead.\n"
              "- **Growth from a loss** is not measurable, so a turnaround passes only on sales.\n"
              "- **Figures** come from the shared growth measure the Fundamentals page uses: the filed "
              "year-earlier comparatives where a filing carries them (the US), the year-earlier "
              "quarter matched where it does not (India), and EPS on one share basis across splits.",
        "G7": "Not already extended going into the news -- a research switch, OFF unless NEGLECT_GATE "
              "is 1 (it is {NEGLECT_GATE}). While off, G7 always passes.\n\n"
              "- **Test:** the close on the session BEFORE the reaction day is no more than "
              "{NEGLECT_MAX_RUN_PCT}% above the close {NEGLECT_LOOKBACK} sessions before that.\n"
              "- **Why before the reaction:** W1 ends its span on the signal session, so the gap itself "
              "counts toward it; a neglected stock that gaps 35% would read as extended. This gate "
              "measures the run INTO the news, which is what Kullamägi means by a stock that has gone "
              "sideways for months.",
    }
    watch_docs = {
        "W1": "Up more than {NEGLECT_MAX_RUN_PCT}% over {NEGLECT_LOOKBACK} sessions: noted, never "
              "blocking.\n\n"
              "- **Test:** the signal session's close is more than {NEGLECT_MAX_RUN_PCT}% above "
              "the close {NEGLECT_LOOKBACK} sessions earlier.\n"
              "- **What it includes:** the span ends on the signal session, so the reaction day's "
              "own jump is inside it (see Caveats).\n"
              "- **Effect:** none on the decision; the note is added to its reason.\n"
              "- **Why:** a stock that sat flat before the news has few holders ready to sell into "
              "the jump. The filter is untested, so it never blocks.",
        "W2": "Qualified on the opening gap alone: the close-to-close move was under "
              "{MIN_MOVE_PCT}%.\n\n"
              "- **Test:** the open was at least {MIN_GAP_PCT}% above the previous close, but the "
              "close was less than {MIN_MOVE_PCT}% above it.\n"
              "- **Effect:** none on the decision; the gap and the close's move are added to its "
              "reason.\n"
              "- **Why the gap counts:** an overnight, US-style release shows as an opening gap. "
              "Indian results often come mid-session, so there the close-to-close move is the test "
              "that matters.",
    }
    setup_docs = {
        EG01: "Results-gap breakout: every gate passes, so a buy-stop waits just above the reaction "
              "day's high.\n\n"
              "- **Trigger:** the reaction high + {ENTRY_BUFFER_PCT}%, rounded up to the tick.\n"
              "- **Stop:** the reaction low, rounded down to the tick.\n"
              "- **Present when:** G1 to G4 all pass on the signal session. There is no other "
              "condition.\n\n"
              "Nothing is bought on the signal session itself. The decision is TRADE ON TRIGGER "
              "and the order waits for the price (see Entry).",
        EG02: "Flag after a results gap: the second buy, once the gap day's own window has passed. A "
              "trader who missed the gap -- or was stopped -- buys the first tight rest above it.\n\n"
              "- **When:** more than {REACTION_WINDOW} and at most {FLAG_WINDOW} sessions after a "
              "reaction day that passes G2.\n"
              "- **The flag:** every session since the reaction day, at least {FLAG_MIN_DAYS} of them; "
              "from its highest high to its lowest low at most {FLAG_MAX_RANGE_PCT}%; no close back to "
              "the close before the reaction (the gap is not filled); today's close within "
              "{FLAG_COIL_PCT}% under the flag's high.\n"
              "- **Trigger:** the flag's high + {ENTRY_BUFFER_PCT}%; **stop:** the flag's low. G4's "
              "percent cap applies, its ATR cap does not.\n"
              "- **Its own entry:** a flag can be bought after the gap-day buy was stopped out.\n\n"
              "Off with FLAG_ON = 0.",
    }
    entry_rules = (
        "The signal. Any session on which G1 to G4 pass is a signal; the first is normally the "
        "reaction day's own close. It places a buy-stop order at the reaction high + "
        "{ENTRY_BUFFER_PCT}% (rounded up to the tick), live from the next session. Nothing is "
        "bought at the signal close -- unless the research switch ENTRY_AT_CLOSE is 1 (it is "
        "{ENTRY_AT_CLOSE}), which buys the reaction day's own close instead, stopped at its low, and "
        "only on the reaction day itself.",
        "How it fills. A buy-stop, not a buy at the next open: it fills on the first session whose "
        "high reaches the trigger, at the trigger. If the stock opens above the trigger, it fills "
        "at that open, and the backtest counts that worse price. No close above the "
        "trigger is needed. The market's per-side slippage is added to the fill.",
        "How long it waits. Until the {ENTRY_EXPIRY_BDAYS}th weekday after the signal day, then it "
        "is cancelled (a market holiday still counts as a weekday). It is cancelled sooner if a "
        "session trades down to the stop without reaching the trigger; a session that reaches both "
        "fills.",
        "Skipped at the fill. Two checks are made again on the price actually paid: the stop must "
        "be no more than {MAX_STOP_PCT}% below it (G4's ATR cap is not re-tested), and the price "
        "must be below the nominal target (see Target). A fill that fails either is not bought.",
        "One buy per reaction day. Once a reaction day has been bought it is never bought again, "
        "even after a stop-out. A cancelled or skipped order is not final: while the reaction day "
        "is still inside the {REACTION_WINDOW}-session window and the gates still pass, the next "
        "session's signal places it again.",
        "One order per stock. A signal in a stock already held, or with an order already waiting, "
        "is ignored.",
    )
    stop_rules = (
        "Where it goes. The reaction day's low, rounded down to the tick, with no buffer under it. "
        "A stock that gives back the whole results day has rejected the news.",
        "It defines the risk. The distance from the price paid to the stop is the trade's risk, "
        "1R. Results are counted in R.",
        "How far is too far. More than {MAX_STOP_PCT}% or {MAX_STOP_ATR} ATR below the trigger "
        "at the signal (G4), or more than {MAX_STOP_PCT}% below the price paid at the fill, and "
        "the trade is not taken.",
        "How it sells. A standing sell order: the position is sold during the first session whose "
        "low reaches the stop, at the stop. If the stock opens below the stop — on news overnight, "
        "or at the next results a quarter later — it sells at that open, so a gap can lose more "
        "than 1R.",
        "From the fill session. A session that triggers the buy-stop and also trades down to the stop "
        "sells at the stop that session (the bar does not say which came first, so the stop wins the tie, as on every session). From the next session it sells at the stop or at a "
        "lower open.",
        "It never moves. No break-even stop and no trailing stop: the 20-day exit does the "
        "trailing (see Exit).",
    )
    target_rules = (
        "There is no sell order at a target. The backtest runs with `--no-target`, so winners "
        "are sold only by the 20-day exit.",
        "The nominal target. The trigger + {NOMINAL_TARGET_R} × the risk (trigger − stop). A "
        "trade plan needs a target, so this one is reported: the reward-to-risk shown is always "
        "{NOMINAL_TARGET_R}, and the chart labels the level nominal. The position size does not "
        "depend on it.",
        "Its one effect. A fill at or above it is skipped as having gapped past the whole reward "
        "(see Entry).",
    )
    exit_rules = (
        "Each session after the buy, the stop is checked first (see Stop). If it did not sell, "
        "the close is checked against the 20-day average.",
        "Trend exit. The first close below the 20-day simple average of closes sells the whole "
        "position at that same close, not at the next open.",
        "Nothing else sells. No partial sale, no time stop and no sale before the next results: a "
        "position still open a quarter later is held through its next report, with the gap risk "
        "described under Stop. A position still open when the backtest ends is valued at the last "
        "close.",
    )
    sizing_rules = (
        "Risk per trade. Shares = equity × the market's risk per trade (see Parameters) ÷ (price "
        "paid − stop), so a stop-out without a gap loses about that share of the account. Equity "
        "is cash plus open positions at the latest close.",
        "Caps. No position may be worth more than the market's largest-position share of equity "
        "(see Parameters). If cash is short, fewer shares are bought rather than none.",
        "Positions at once. At most the market's position limit (see Parameters). An order that "
        "triggers with no slot free keeps waiting until it expires, and fills if a slot frees "
        "first.",
        "Same-day ties. Every signal scores the same, so when more orders trigger than slots are "
        "free, the order placed first is filled first.",
        "Costs. The market's per-side slippage is inside every fill price. No commission or other "
        "charges are added unless the run asks for them.",
    )
    filter_rules = (
        "Too thin. On the signal session the 20-day average traded value (close × volume) must "
        "reach the market's liquidity floor (see Parameters), and a 14-day ATR must exist. There "
        "is no price floor, because back-adjusted prices would remove early winners.",
        "Too little history. At least {min_bars} daily bars.",
        "Not linked to results. A stock with no stored quarter whose window holds the reaction "
        "day is never bought (G3).",
        "Market regime. The backtest command adds no market filter, so the backtest buys in any "
        "market. Live, a risk-off market lowers TRADE ON TRIGGER to WATCH (see Decisions).",
        "No results blackout. Unlike other strategies, results due soon do not block a buy: the "
        "trade is on results just reported, and the next report is about a quarter away.",
    )
    decision_docs = {
        "TRADE_HIGH_CONFIDENCE": "Never reached by this strategy. Its entry is always a resting "
                                 "buy-stop, so its best tier is TRADE ON TRIGGER.",
        "TRADE_ON_TRIGGER": "G1 to G4 pass and the plan is valid: place the buy-stop "
                            "{ENTRY_BUFFER_PCT}% above the reaction high. W1 and W2 add their "
                            "notes to the reason but do not lower the tier. The backtest command "
                            "takes these (--accept-labels 'TRADE ON TRIGGER').",
        "WATCH_WAIT": "The plan is valid but not one share fits — one share would risk more than "
                      "the risk budget, or be worth more than the largest-position cap (reason: "
                      "too large for account). Or a risk-off market lowered TRADE ON TRIGGER to "
                      "this tier.",
        "AVOID": "A gate failed (the reason names the first of G1 to G4 that did), or the plan is "
                 "degenerate (no positive distance from trigger to stop), or a risk-off market "
                 "lowered WATCH to this tier.",
    }
    regime_note = ("When the market regime is risk-off, the live decision drops one tier: TRADE ON "
                   "TRIGGER becomes WATCH and WATCH becomes AVOID, and the reason says "
                   "'market-regime downgrade applied'. A backtest never applies it, and the "
                   "backtest command adds no market filter, so backtest trades are taken in any "
                   "regime.")
    param_docs = (
        ("Minimum move", "MIN_MOVE_PCT", "G2: close-to-close rise, in %, that makes a session a reaction day."),
        ("Minimum gap", "MIN_GAP_PCT", "G2: opening gap over the previous close, in %, that qualifies instead."),
        ("Minimum relative volume", "MIN_REL_VOLUME", "G2: the day's volume ÷ its 50-day average volume."),
        ("Require a gap", "REQUIRE_GAP", "G2, research switch: 1 = the open must be at least the minimum gap up; 0 = off."),
        ("Market gate", "MARKET_GATE", "G5, research switch: 1 = buy only while the small-cap index is above its 200-day; 0 = off."),
        ("Entry at the close", "ENTRY_AT_CLOSE", "Research switch: 1 = buy the reaction day's own close, stopped at its low; 0 = a buy-stop above its high from the next session."),
        ("Minimum growth", "MIN_GROWTH_PCT", "G6, research switch: the announced quarter's sales or EPS up at least this % on a year earlier; 0 = off."),
        ("Screen gate", "SCREEN_GATE", "G1, research switch: 1 = the stock must close above its 200-day (as shipped); 0 = off."),
        ("Neglect gate", "NEGLECT_GATE", "G7, research switch: 1 = refuse a stock up more than the neglect threshold in the sessions before the news; 0 = off."),
        ("Minimum close position", "MIN_CLOSE_POS", "G2: (close − low) ÷ (high − low); 1 is a close on the high."),
        ("Reaction window", "REACTION_WINDOW", "G2: sessions, counting the signal session, in which a reaction day still offers its setup."),
        ("Catalyst: earliest", "CATALYST_MIN_DAYS", "G3: calendar days after a quarter end before a reaction can be linked to it."),
        ("Announcement window", "ANNOUNCE_WINDOW_DAYS", "G3, with recorded announcements: calendar days "
                                                        "before the reaction day the results may have come out."),
        ("Catalyst: latest", "CATALYST_FILED_GRACE", "G3: calendar days after that quarter's filing after which it cannot."),
        ("Catalyst: no filing date", "CATALYST_UNFILED_DAYS", "G3: for a quarter stored without a filing date (a "
         "foreign issuer), calendar days after the quarter end up to which a reaction links; 0 = never."),
        ("Maximum stop", "MAX_STOP_PCT", "G4 and at the fill: widest stop, in % below the trigger or the price paid."),
        ("Maximum stop (ATR)", "MAX_STOP_ATR", "G4: widest stop as a multiple of the 14-day ATR (not for S2)."),
        ("Volume yardstick", "REL_VOL_PRIOR", "G2: 1 = the 50-day average ends the session before the reaction; 0 = it includes the day (1.7)."),
        ("Flag entry", "FLAG_ON", "S2: 1 = buy the flag after a results gap; 0 = off."),
        ("Flag window", "FLAG_WINDOW", "S2: sessions after the reaction day in which its flag can still be bought."),
        ("Flag length", "FLAG_MIN_DAYS", "S2: sessions the flag must have rested."),
        ("Flag depth", "FLAG_MAX_RANGE_PCT", "S2: the flag's high to its low, at most this %."),
        ("Flag coil", "FLAG_COIL_PCT", "S2: today's close within this % under the flag's high."),
        ("Entry buffer", "ENTRY_BUFFER_PCT", "How far above the reaction high, in %, the buy-stop sits."),
        ("Entry window", "ENTRY_EXPIRY_BDAYS", "Weekdays after the signal day before an unfilled buy-stop is cancelled."),
        ("Neglect threshold", "NEGLECT_MAX_RUN_PCT", "W1: rise, in %, over {NEGLECT_LOOKBACK} sessions above which W1 is noted."),
        ("Nominal target", "NOMINAL_TARGET_R", "Reported reward-to-risk; a fill at or above the level is skipped. Not a sell order."),
        ("Risk per trade", "cfg.risk_pct", "Share of equity risked per trade (0.01 = 1%)."),
        ("Largest position", "cfg.max_position_pct", "Largest position as a share of equity."),
        ("Positions at once", "cfg.max_open_positions", "Most positions held at the same time."),
        ("Minimum liquidity", "cfg.screener.min_dollar_volume", "20-day average traded value, in the market's currency."),
    )

    # ---------- the results calendar ----------

    _quarters: dict = {}

    @classmethod
    def _results_windows(cls, market_key: str) -> dict:
        """{symbol: [(earliest, latest), ...]} — the bracket each stored quarter admits.

        Cached on the class: every symbol on every bar asks the same question of the same table,
        and one query per bar would dominate the scan.
        """
        if market_key in cls._quarters:
            return cls._quarters[market_key]
        from ..marketdata import db
        out: dict = {}
        try:
            with db.get_connection().cursor() as cur:
                cur.execute(
                    """SELECT symbol, period_end, filed FROM quarterly_results
                       WHERE market=%s AND period_end IS NOT NULL""",
                    (market_key,))
                for sym, pe, filed in cur.fetchall():
                    if filed is None and not CATALYST_UNFILED_DAYS:
                        continue
                    lo = pd.Timestamp(pe) + pd.Timedelta(days=CATALYST_MIN_DAYS)
                    hi = (pd.Timestamp(filed) + pd.Timedelta(days=CATALYST_FILED_GRACE) if filed is not None
                          else pd.Timestamp(pe) + pd.Timedelta(days=CATALYST_UNFILED_DAYS))
                    if hi >= lo:
                        out.setdefault(sym, []).append((lo, hi))
        except Exception:   # noqa: BLE001 — no results table is "nothing can be linked", not a crash
            out = {}
        cls._quarters[market_key] = out
        return out

    _announced: dict = {}

    @classmethod
    def _announcements(cls, market_key: str) -> dict:
        """{symbol: sorted announcement dates}, cached per market AND stage boundary: the loader honours
        the boundary, so a cache keyed on the market alone would hand an optimise run's dates to a full
        run in the same process, or the reverse."""
        from ..marketdata import asof, financials
        key = (market_key, asof.end_date())
        if key not in cls._announced:
            cls._announced[key] = financials.announcements(market_key)
        return cls._announced[key]

    @classmethod
    def _link(cls, symbol: str, day: pd.Timestamp) -> str | None:
        """How the reaction day is tied to results, or None when it is not.

        With recorded announcements, the guide's rule: published within ANNOUNCE_WINDOW_DAYS before the
        reaction day, or on it (an Indian company often publishes after the close, so its reaction is
        the next session). Without them, the bracket of stored quarter end and filing date.
        """
        market = _market_of(symbol)
        dates = cls._announcements(market).get(symbol)
        if dates:
            import bisect
            d = day.date()
            i = bisect.bisect_left(dates, d - pd.Timedelta(days=ANNOUNCE_WINDOW_DAYS).to_pytimedelta())
            return f"results announced {dates[i]}" if i < len(dates) and dates[i] <= d else None
        wins = cls._results_windows(market).get(symbol)
        if wins and any(lo <= day <= hi for lo, hi in wins):
            return "inside a stored results window"
        return None

    _market: dict = {}

    @classmethod
    def _market_on(cls, market_key: str, day: pd.Timestamp) -> bool:
        """G5: is the market index above its 200-day on `day`? The shared index_sma rule
        (backtesting/regime.py), read as of `day`. Cached per market AND stage boundary, like the
        announcements; an index that is not stored, or too short to judge, counts as on."""
        from ..backtesting import regime
        from ..marketdata import asof, cache
        key = (market_key, asof.end_date())
        if key not in cls._market:
            ticker = MARKET_GATE_INDEX.get(market_key)
            px = cache.load_cached(market_key, ticker) if ticker else None
            cls._market[key] = (None if px is None or px.empty else
                                regime.regime_on("index_sma", px.index, bench_px=px["close"], px=None,
                                                 sma200=None, dv=None, liq_floor=None))
        on = cls._market[key]
        if on is None:
            return True
        on = on[on.index <= day]
        return bool(on.iloc[-1]) if len(on) else True

    @classmethod
    def _linked_to_results(cls, symbol: str, day: pd.Timestamp) -> bool:
        return cls._link(symbol, day) is not None

    _quarters_fin: dict = {}

    @classmethod
    def _announced_quarter(cls, symbol: str, day: pd.Timestamp) -> dict | None:
        """G6: the quarter a reaction announced, with its year-on-year growth -- or None.

        Read through the shared measures rather than restated: marketdata.financials.load (one row
        per quarter, oldest first, cut at the backtest stage's boundary) and
        fundamentals.growth.growth_series (the filed year-earlier comparatives where a filing carries
        them, the year-earlier quarter matched where it does not, EPS on one share basis). The quarter
        is the latest that ended at least CATALYST_MIN_DAYS before the reaction. Cached per market
        AND stage boundary, like the announcements.
        """
        from ..marketdata import asof, financials
        from fundamentals import growth
        market = _market_of(symbol)
        key = (market, asof.end_date())
        if key not in cls._quarters_fin:
            cls._quarters_fin[key] = {"rows": financials.load(market), "series": {}}
        c = cls._quarters_fin[key]
        if symbol not in c["series"]:
            rows = c["rows"].get(symbol)
            c["series"][symbol] = growth.growth_series(rows) if rows else []
        cutoff = (day - pd.Timedelta(days=CATALYST_MIN_DAYS)).date()
        q = [x for x in c["series"][symbol] if x["end"] <= cutoff]
        return q[-1] if q else None

    # ---------- screening ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- gates ----------

    def _reaction_day(self, d: pd.DataFrame, window: int = REACTION_WINDOW) -> dict | None:
        """The most recent qualifying reaction day within the last `window` sessions, or None.

        Walks backwards so the NEWEST event wins: a second results gap inside five sessions is a
        new event with a new high and a new stop, not a continuation of the first.
        """
        n = len(d)
        first = max(1, n - window)
        for i in range(n - 1, first - 1, -1):
            o, h, l, c = (float(d["open"].iloc[i]), float(d["high"].iloc[i]),
                          float(d["low"].iloc[i]), float(d["close"].iloc[i]))
            prev_c = float(d["close"].iloc[i - 1])
            v50 = d["vol_sma50"].iloc[i - 1] if REL_VOL_PRIOR else d["vol_sma50"].iloc[i]
            if not prev_c or pd.isna(v50) or not v50:
                continue
            move = (c / prev_c - 1) * 100
            gap = (o / prev_c - 1) * 100
            if move < MIN_MOVE_PCT and gap < MIN_GAP_PCT:
                continue
            if REQUIRE_GAP and gap < MIN_GAP_PCT:
                continue
            rel_vol = float(d["volume"].iloc[i]) / float(v50)
            if rel_vol < MIN_REL_VOLUME:
                continue
            rng = h - l
            pos = (c - l) / rng if rng > 0 else 1.0
            if pos < MIN_CLOSE_POS:
                continue
            return {"i": i, "date": d.index[i], "high": h, "low": l, "close": c, "prev_close": prev_c,
                    "move_pct": move, "gap_pct": gap, "rel_volume": rel_vol, "close_pos": pos}
        return None

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        e = ctx.extras
        if SCREEN_GATE:
            self.apply_screen(ctx, result)   # G1, from the Above-the-200-day screen
        else:
            result.ok("G1", "off")

        r = self._reaction_day(d)
        flag = None
        if r is None and FLAG_ON and not ENTRY_AT_CLOSE:
            # S2: a reaction older than the gap day's own window, followed by a tight flag
            r = self._reaction_day(d, FLAG_WINDOW)
            flag = self._flag(d, r) if r is not None else None
            if flag is None:
                r = None
        if r is None:
            result.fail("G2", f"no results-day reaction in the last {REACTION_WINDOW} sessions"
                              + (f", nor a flag after one in the last {FLAG_WINDOW}" if FLAG_ON else ""))
            for g in ("G3", "G4", "G5", "G6", "G7"):
                result.ok(g, "not reached")
            result.recompute_first_fail()
            return result
        if ENTRY_AT_CLOSE and r["i"] != len(d) - 1:
            # a close order buys the close of its own signal session, so only the reaction day can
            # place it; a reaction from an earlier session has no close left to buy
            result.fail("G2", f"the reaction was {len(d) - 1 - r['i']} session(s) ago; a close entry "
                              f"buys only on the reaction day itself")
            for g in ("G3", "G4", "G5", "G6", "G7"):
                result.ok(g, "not reached")
            result.recompute_first_fail()
            return result

        result.ok("G2", f"{r['move_pct']:+.1f}% on {r['rel_volume']:.1f}x volume, "
                        f"closing at {r['close_pos'] * 100:.0f}% of range")
        e["reaction_date"] = str(r["date"].date())
        e["reaction_high"] = r["high"]
        e["reaction_low"] = r["low"]
        e["reaction_close"] = r["close"]
        e["reaction_move_pct"] = round(r["move_pct"], 2)
        e["reaction_rel_volume"] = round(r["rel_volume"], 2)
        e["reaction_close_pos"] = round(r["close_pos"], 3)
        if flag:
            e.update(flag_high=flag["high"], flag_low=flag["low"], flag_days=flag["days"],
                     flag_range_pct=round(flag["range_pct"], 2))

        # G3 — the news link
        how = self._link(ctx.symbol, r["date"])
        if how:
            result.ok("G3", how)
        elif self._announcements(_market_of(ctx.symbol)).get(ctx.symbol):
            result.fail("G3", f"no results announced in the {ANNOUNCE_WINDOW_DAYS} days before the move")
        else:
            result.fail("G3", "the move is not inside a stored results window")

        # G4 — is the reaction low a stop we can carry? Measured from the entry this run will use.
        if flag:
            entry = flag["high"] * (1 + ENTRY_BUFFER_PCT / 100)
            risk = entry - flag["low"]
        else:
            entry = r["close"] if ENTRY_AT_CLOSE else r["high"] * (1 + ENTRY_BUFFER_PCT / 100)
            risk = entry - r["low"]
        atr14 = ctx.atr
        risk_pct = risk / entry * 100 if entry else float("inf")
        atr_mult = risk / atr14 if atr14 and atr14 == atr14 else float("inf")
        if risk <= 0:
            result.fail("G4", "the reaction day's low is not below the trigger")
        elif risk_pct > MAX_STOP_PCT:
            result.fail("G4", f"stop is {risk_pct:.1f}% below the entry (over {MAX_STOP_PCT:g}%)")
        elif atr_mult > MAX_STOP_ATR and not flag:
            result.fail("G4", f"stop is {atr_mult:.1f} ATR below the entry (over {MAX_STOP_ATR:g})")
        else:
            result.ok("G4")

        # G5 — the market (off unless MARKET_GATE)
        if not MARKET_GATE:
            result.ok("G5", "off")
        elif self._market_on(_market_of(ctx.symbol), d.index[-1]):
            result.ok("G5")
        else:
            result.fail("G5", f"{MARKET_GATE_INDEX.get(_market_of(ctx.symbol))} is not above its 200-day average")

        # G6 — growth in the quarter the reaction announced (off unless MIN_GROWTH_PCT)
        if MIN_GROWTH_PCT <= 0:
            result.ok("G6", "off")
        else:
            q = self._announced_quarter(ctx.symbol, r["date"])
            got = {k: q.get(k) for k in ("rev_g", "eps_g")} if q else {}
            best = max((v for v in got.values() if v is not None), default=None)
            seen = ", ".join(f"{'sales' if k == 'rev_g' else 'EPS'} {v * 100:+.0f}%"
                             for k, v in got.items() if v is not None)
            if q is None:
                result.fail("G6", "no stored quarter before the reaction")
            elif best is None:
                result.fail("G6", f"growth not measurable for the quarter ended {q['end']}")
            elif best * 100 >= MIN_GROWTH_PCT:
                result.ok("G6", f"quarter ended {q['end']}: {seen}")
            else:
                result.fail("G6", f"quarter ended {q['end']}: {seen}, under {MIN_GROWTH_PCT:g}%")

        # G7 — not already extended INTO the news (off unless NEGLECT_GATE)
        if not NEGLECT_GATE:
            result.ok("G7", "off")
        else:
            i, j = r["i"] - 1, r["i"] - 1 - NEGLECT_LOOKBACK
            if j < 0:
                result.ok("G7", "too little history to judge")
            else:
                before, then = float(d["close"].iloc[i]), float(d["close"].iloc[j])
                run_in = (before / then - 1) * 100 if then else 0.0
                if run_in > NEGLECT_MAX_RUN_PCT:
                    result.fail("G7", f"up {run_in:.0f}% in the {NEGLECT_LOOKBACK} sessions before the news "
                                      f"(over {NEGLECT_MAX_RUN_PCT:g}%)")
                else:
                    result.ok("G7", f"{run_in:+.0f}% in the {NEGLECT_LOOKBACK} sessions before the news")

        # W1 — already extended into the news (Bonde's neglect point)
        if len(d) > NEGLECT_LOOKBACK:
            then = float(d["close"].iloc[-(NEGLECT_LOOKBACK + 1)])
            run = (ctx.close / then - 1) * 100 if then else 0.0
            if run > NEGLECT_MAX_RUN_PCT:
                result.watch_flags["W1"] = True
                result.watch_notes["W1"] = (f"up {run:.0f}% in {NEGLECT_LOOKBACK} sessions "
                                            f"before the news")
            else:
                result.watch_flags["W1"] = False
        # W2 — qualified on the gap alone
        result.watch_flags["W2"] = bool(r["move_pct"] < MIN_MOVE_PCT)
        if result.watch_flags["W2"]:
            result.watch_notes["W2"] = (f"gapped {r['gap_pct']:+.1f}% but closed "
                                        f"{r['move_pct']:+.1f}%")

        result.setups[EG01] = bool(result.hard_gates_passed) and not flag
        result.setups[EG02] = bool(result.hard_gates_passed) and bool(flag)
        result.recompute_first_fail()
        return result

    @staticmethod
    def _flag(d: pd.DataFrame, r: dict) -> dict | None:
        """S2's flag after reaction `r`, as of the last bar, or None: past the reaction window, at least
        FLAG_MIN_DAYS sessions old, at most FLAG_MAX_RANGE_PCT from its high to its low, no close back to the
        pre-reaction close (the gap unfilled), and the last close within FLAG_COIL_PCT under the flag's high."""
        n = len(d)
        days = n - 1 - r["i"]
        if days < max(FLAG_MIN_DAYS, REACTION_WINDOW) or days > FLAG_WINDOW:
            return None
        seg = d.iloc[r["i"] + 1:]
        hi, lo = float(seg["high"].max()), float(seg["low"].min())
        if not hi or (hi - lo) / hi * 100 > FLAG_MAX_RANGE_PCT:
            return None
        if float(seg["close"].min()) <= r["prev_close"]:
            return None
        if float(d["close"].iloc[-1]) < hi * (1 - FLAG_COIL_PCT / 100):
            return None
        return {"high": hi, "low": lo, "days": days, "range_pct": (hi - lo) / hi * 100}

    # ---------- entry ----------

    def entry_signal_fired(self, ctx: StockContext, result: StrategyResult) -> bool:
        """The setup places its order today: a resting buy-stop above the reaction high, filled by
        the break of that high from the next session on. Like Minervini's MV-02, the order IS the
        signal -- returning False here made the backtest drop every setup before it was planned."""
        return result.has_setup

    def setup_quality(self, result: StrategyResult) -> float:
        """Relative volume is the guide's strongest claim about which gaps hold, so it ranks."""
        if not result.has_setup:
            return 0.0
        return 1.0

    def build_plans(self, ctx: StockContext, result: StrategyResult,
                    cfg: MarketConfig) -> PlanChoice:
        if not result.has_setup:
            return PlanChoice(None, None, "no active setup")
        e = ctx.extras
        flag = bool(result.setups.get(EG02))
        hi, lo = (e.get("flag_high"), e.get("flag_low")) if flag else (e.get("reaction_high"), e.get("reaction_low"))
        if hi is None or lo is None:
            return PlanChoice(None, None, "missing reaction day")
        if ENTRY_AT_CLOSE and not flag:
            entry = float(e.get("reaction_close") or ctx.close)   # bought at that close, as it printed
        else:
            entry = round_tick(float(hi) * (1 + ENTRY_BUFFER_PCT / 100), cfg.tick_size, "up")
        stop = round_tick(float(lo), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(
            plan="EG", setup=EG02 if flag else EG01, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R, nearest_overhead_above_entry=None,
        )
        how = ("buy-stop above the flag after the {d} reaction" if flag else
               "buy the {d} reaction close" if ENTRY_AT_CLOSE else "buy-stop above the {d} reaction high")
        return PlanChoice(plan, None, how.format(d=e["reaction_date"]))

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """A resting buy-stop, one per event, cancelled after {ENTRY_EXPIRY_BDAYS} sessions.

        No `max_fill`: the guide is explicit that a stock opening above the trigger is filled at
        the open and that the worse price should be counted. The stop-width cap at the fill is
        what refuses the cases where that gap made the trade unsizeable.
        """
        if ENTRY_AT_CLOSE:
            # the simulator's close order: filled at the close of its own signal session, which is
            # a completed bar, so nothing later is read; one that cannot fill that day is dropped
            return {"order": "close", "base_id": ctx.extras.get("reaction_date"),
                    "max_risk_pct": MAX_STOP_PCT / 100}
        # a flag is its own entry: it may follow a gap-day buy that was stopped out
        flag = plan.setup == EG02
        return {
            "order": "stop",
            "base_id": f"{ctx.extras.get('reaction_date')}-flag" if flag else ctx.extras.get("reaction_date"),
            "max_risk_pct": MAX_STOP_PCT / 100,
            "expiry_bdays": ENTRY_EXPIRY_BDAYS,
        }

    # ---------- decision ----------

    def classify(self, ctx: StockContext, result: StrategyResult, plan: TradePlan,
                 sizing_result, earnings_days_away: int | None,
                 regime_downgrade_active: bool) -> Decision:
        if not result.hard_gates_passed:
            code = result.first_hard_fail
            return Decision("AVOID", "AVOID",
                            f"fails hard gate {code}: {result.hard_notes.get(code, '')}",
                            float("nan"), float("nan"), 0.0)
        if not plan.is_valid:
            return Decision("AVOID", "AVOID", "degenerate plan (non-positive or undefined risk)",
                            float("nan"), float("nan"), 0.0)

        risk_pct = plan.risk_per_share / plan.entry * 100
        reasons: list[str] = []
        if sizing_result.too_large:
            label = "WATCH_WAIT"
            reasons.append("too large for account")
        else:
            # The entry is a resting buy-stop that has not been hit yet, which is exactly what
            # TRADE_ON_TRIGGER means. There is no higher tier for this strategy by construction.
            label = "TRADE_ON_TRIGGER"
            reasons.append(f"buy-stop above the flag after the {ctx.extras.get('reaction_date')} reaction"
                           if plan.setup == EG02 else
                           f"buy the {ctx.extras.get('reaction_date')} reaction close" if ENTRY_AT_CLOSE
                           else f"buy-stop above the {ctx.extras.get('reaction_date')} reaction high")
            for code in ("W1", "W2"):
                if result.watch_flags.get(code):
                    reasons.append(result.watch_notes.get(code, code))

        before = label
        if regime_downgrade_active and label != "AVOID":
            label = DOWNGRADE_MAP[label]
            reasons.append("market-regime downgrade applied")
        return Decision(LABELS[before], LABELS[label], "; ".join(reasons),
                        risk_pct, plan.r_multiple, self.setup_quality(result))

    def report_extras(self, ctx: StockContext, result: StrategyResult,
                      plan: TradePlan | None) -> dict:
        e = ctx.extras
        return {
            "reaction_date": e.get("reaction_date"),
            "reaction_high": round(e["reaction_high"], 2) if e.get("reaction_high") else None,
            "reaction_low": round(e["reaction_low"], 2) if e.get("reaction_low") else None,
            "reaction_move_pct": e.get("reaction_move_pct"),
            "reaction_rel_volume": e.get("reaction_rel_volume"),
            "reaction_close_pos": e.get("reaction_close_pos"),
        }
