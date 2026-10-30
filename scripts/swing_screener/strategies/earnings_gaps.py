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
the filing's broadcast). The bracket remains
for a company with no recorded announcements -- every US company, since SEC filing dates come after
the announcement rather than at it.

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
MIN_CLOSE_POS = 0.70       # (close - low) / (high - low): closed in the top of its range
NEGLECT_LOOKBACK = 60      # sessions over which "already extended" is measured
NEGLECT_MAX_RUN_PCT = 30.0 # a stock up more than this into the news is noted, not refused

# ---- the catalyst bracket (see the module docstring)
CATALYST_MIN_DAYS = 10     # a reaction day sits at least this far after the quarter end
CATALYST_FILED_GRACE = 5   # ...and no later than this many days after that quarter's filing
ANNOUNCE_WINDOW_DAYS = 3   # with recorded announcements: results published at most this many calendar
                           # days before the reaction day, or on it -- the guide's own rule

# ---- entry and risk (guide §3, "Entry" / "Initial stop")
ENTRY_BUFFER_PCT = 0.1     # the buy-stop sits this far above the reaction day's high
ENTRY_EXPIRY_BDAYS = 5     # how long the buy-stop waits before it is cancelled
REACTION_WINDOW = 5        # sessions a reaction day keeps offering its setup
MAX_STOP_PCT = 12.0        # widest stop, as a share of the entry
MAX_STOP_ATR = 1.5         # ...or this multiple of the 14-day ATR, whichever binds first
NOMINAL_TARGET_R = 3.0     # for sizing and reporting only — the real exit is the trail

EG01 = "S1"   # EG-01: the break of the reaction day's high


class EarningsGapStrategy(Strategy):
    selection = "time_series"
    family = "earnings_gaps"
    version = "1.4"
    changelog = (
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
    screen_key = "above_200"
    screen_gates = {"G1": "A1"}
    gate_codes = ("G1", "G2", "G3", "G4")
    watch_codes = ("W1", "W2")
    setup_codes = (EG01,)
    setup_names = {EG01: "Results-gap breakout"}
    gate_titles = {"G1": "Above the 200-day", "G2": "A results-day reaction",
                   "G3": "Linked to a results window", "G4": "Stop close enough to carry"}
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
        "India and the US tie a reaction to results differently. India uses the exchange's recorded "
        "announcement times, back to 2007, which is the guide's rule and is tight -- a few days. The "
        "US has no announcement history, so it uses the quarter-end-to-filing window, about five weeks "
        "wide. A US run therefore admits more non-results spikes, and the two markets' results are not "
        "a like-for-like comparison of the same rule. (Before 1.3, India used the window too, and its "
        "quarters began in March 2020, so the 2013-2021 window had three Indian trades.)",
        "The results link is a window, not a calendar. It runs from {CATALYST_MIN_DAYS} days after "
        "the quarter end to {CATALYST_FILED_GRACE} days after the filing — about five weeks at the "
        "median — so a non-results spike that lands inside it is admitted. In the US the filing is "
        "the SEC filing, and for a fourth quarter that is the annual report, which can come weeks "
        "after the announcement, so the window is widest there.",
        "India's announcements are refreshed weekly (the `announcements` job). A results board meeting "
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
        "the session; with no announcement calendar stored, the window here is about five weeks wide.\n"
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
              "- **Effect:** a turnaround still below its 200-day is never bought.",
        "G2": "A results-day reaction in the last {REACTION_WINDOW} sessions: a big move on heavy "
              "volume that closed near the day's high.\n\n"
              "- **Window:** the signal session and the sessions just before it, {REACTION_WINDOW} "
              "in all. If several days qualify, the most recent is used, even when an older one "
              "would have passed G3 and it does not.\n"
              "- **Big move:** the close is at least {MIN_MOVE_PCT}% above the previous session's "
              "close, OR the open is at least {MIN_GAP_PCT}% above it. Either is enough; W2 marks a "
              "day that qualified on the gap alone.\n"
              "- **Heavy volume:** the day's volume is at least {MIN_REL_VOLUME} times its 50-day "
              "average. The average is the simple mean of the 50 sessions ending on that day, so it "
              "includes the reaction day's own volume.\n"
              "- **Close near the high:** (close − low) ÷ (high − low) is at least "
              "{MIN_CLOSE_POS}, where 0 is a close on the low and 1 a close on the high. A day with "
              "no range counts as 1.\n"
              "- **News:** nothing here looks at news. Any session in the window can be the "
              "reaction day; G3 makes the link to results afterwards.",
        "G3": "The reaction day is tied to a results announcement. Two ways, depending on what is "
              "stored for the company:\n\n"
              "- **Recorded announcements (India, back to 2007):** results were published at most "
              "{ANNOUNCE_WINDOW_DAYS} calendar days before the reaction day, or on it. This is the "
              "guide's own rule. A quarter can carry several dates and any one qualifies: the day of "
              "the board meeting that approved the results (the results come out that day, often "
              "after the close, so they tie to the next session's move) and the exchange's broadcast "
              "time for the results filing, which in older years is often days later.\n"
              "- **No recorded announcements (every US company, and any Indian one the exchange does "
              "not list):** the window below.\n\n"
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
              "paid (see Entry).",
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
    }
    entry_rules = (
        "The signal. Any session on which G1 to G4 pass is a signal; the first is normally the "
        "reaction day's own close. It places a buy-stop order at the reaction high + "
        "{ENTRY_BUFFER_PCT}% (rounded up to the tick), live from the next session. Nothing is "
        "bought at the signal close.",
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
        "From the session after the fill. The backtest settles exits before fills, so the stop is "
        "not checked on the day of the buy. A stock that falls through the stop that same day is "
        "sold the next session, at the stop or at a lower open.",
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
        ("Minimum close position", "MIN_CLOSE_POS", "G2: (close − low) ÷ (high − low); 1 is a close on the high."),
        ("Reaction window", "REACTION_WINDOW", "G2: sessions, counting the signal session, in which a reaction day still offers its setup."),
        ("Catalyst: earliest", "CATALYST_MIN_DAYS", "G3: calendar days after a quarter end before a reaction can be linked to it."),
        ("Announcement window", "ANNOUNCE_WINDOW_DAYS", "G3, with recorded announcements: calendar days "
                                                        "before the reaction day the results may have come out."),
        ("Catalyst: latest", "CATALYST_FILED_GRACE", "G3: calendar days after that quarter's filing after which it cannot."),
        ("Maximum stop", "MAX_STOP_PCT", "G4 and at the fill: widest stop, in % below the trigger or the price paid."),
        ("Maximum stop (ATR)", "MAX_STOP_ATR", "G4: widest stop as a multiple of the 14-day ATR."),
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
                       WHERE market=%s AND period_end IS NOT NULL AND filed IS NOT NULL""",
                    (market_key,))
                for sym, pe, filed in cur.fetchall():
                    lo = pd.Timestamp(pe) + pd.Timedelta(days=CATALYST_MIN_DAYS)
                    hi = pd.Timestamp(filed) + pd.Timedelta(days=CATALYST_FILED_GRACE)
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

    @classmethod
    def _linked_to_results(cls, symbol: str, day: pd.Timestamp) -> bool:
        return cls._link(symbol, day) is not None

    # ---------- screening ----------

    def prefilter_row(self, cfg: MarketConfig, last) -> tuple[bool, str]:
        ok, why = tradable_point_in_time(cfg, last)
        if not ok:
            return False, why
        if pd.isna(last.get("atr14")) or not last.get("atr14"):
            return False, "no ATR"
        return True, "passed"

    # ---------- gates ----------

    def _reaction_day(self, d: pd.DataFrame) -> dict | None:
        """The most recent qualifying reaction day within the window, or None.

        Walks backwards so the NEWEST event wins: a second results gap inside five sessions is a
        new event with a new high and a new stop, not a continuation of the first.
        """
        n = len(d)
        first = max(1, n - REACTION_WINDOW)
        for i in range(n - 1, first - 1, -1):
            o, h, l, c = (float(d["open"].iloc[i]), float(d["high"].iloc[i]),
                          float(d["low"].iloc[i]), float(d["close"].iloc[i]))
            prev_c = float(d["close"].iloc[i - 1])
            v50 = d["vol_sma50"].iloc[i]
            if not prev_c or pd.isna(v50) or not v50:
                continue
            move = (c / prev_c - 1) * 100
            gap = (o / prev_c - 1) * 100
            if move < MIN_MOVE_PCT and gap < MIN_GAP_PCT:
                continue
            rel_vol = float(d["volume"].iloc[i]) / float(v50)
            if rel_vol < MIN_REL_VOLUME:
                continue
            rng = h - l
            pos = (c - l) / rng if rng > 0 else 1.0
            if pos < MIN_CLOSE_POS:
                continue
            return {"i": i, "date": d.index[i], "high": h, "low": l,
                    "move_pct": move, "gap_pct": gap, "rel_volume": rel_vol, "close_pos": pos}
        return None

    def evaluate(self, ctx: StockContext) -> StrategyResult:
        d = ctx.daily
        result = StrategyResult(entry_setup_codes=self.setup_codes)
        e = ctx.extras
        self.apply_screen(ctx, result)   # G1, from the Above-the-200-day screen

        r = self._reaction_day(d)
        if r is None:
            result.fail("G2", f"no results-day reaction in the last {REACTION_WINDOW} sessions")
            result.ok("G3", "not reached")
            result.ok("G4", "not reached")
            result.recompute_first_fail()
            return result

        result.ok("G2", f"{r['move_pct']:+.1f}% on {r['rel_volume']:.1f}x volume, "
                        f"closing at {r['close_pos'] * 100:.0f}% of range")
        e["reaction_date"] = str(r["date"].date())
        e["reaction_high"] = r["high"]
        e["reaction_low"] = r["low"]
        e["reaction_move_pct"] = round(r["move_pct"], 2)
        e["reaction_rel_volume"] = round(r["rel_volume"], 2)
        e["reaction_close_pos"] = round(r["close_pos"], 3)

        # G3 — the news link
        how = self._link(ctx.symbol, r["date"])
        if how:
            result.ok("G3", how)
        elif self._announcements(_market_of(ctx.symbol)).get(ctx.symbol):
            result.fail("G3", f"no results announced in the {ANNOUNCE_WINDOW_DAYS} days before the move")
        else:
            result.fail("G3", "the move is not inside a stored results window")

        # G4 — is the reaction low a stop we can carry?
        entry = r["high"] * (1 + ENTRY_BUFFER_PCT / 100)
        risk = entry - r["low"]
        atr14 = ctx.atr
        risk_pct = risk / entry * 100 if entry else float("inf")
        atr_mult = risk / atr14 if atr14 and atr14 == atr14 else float("inf")
        if risk <= 0:
            result.fail("G4", "the reaction day's low is not below the trigger")
        elif risk_pct > MAX_STOP_PCT:
            result.fail("G4", f"stop is {risk_pct:.1f}% below the entry (over {MAX_STOP_PCT:g}%)")
        elif atr_mult > MAX_STOP_ATR:
            result.fail("G4", f"stop is {atr_mult:.1f} ATR below the entry (over {MAX_STOP_ATR:g})")
        else:
            result.ok("G4")

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

        result.setups[EG01] = bool(result.hard_gates_passed)
        result.recompute_first_fail()
        return result

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
        hi, lo = e.get("reaction_high"), e.get("reaction_low")
        if hi is None or lo is None:
            return PlanChoice(None, None, "missing reaction day")
        entry = round_tick(float(hi) * (1 + ENTRY_BUFFER_PCT / 100), cfg.tick_size, "up")
        stop = round_tick(float(lo), cfg.tick_size, "down")
        if stop <= 0 or stop >= entry:
            return PlanChoice(None, None, "degenerate stop")
        risk = entry - stop
        target = entry + NOMINAL_TARGET_R * risk
        plan = TradePlan(
            plan="EG", setup=EG01, entry=entry, stop=stop, target=target,
            risk_per_share=risk, reward_per_share=target - entry,
            r_multiple=NOMINAL_TARGET_R, nearest_overhead_above_entry=None,
        )
        return PlanChoice(plan, None, f"buy-stop above the {e['reaction_date']} reaction high")

    def signal_meta(self, ctx: StockContext, result: StrategyResult, plan: TradePlan) -> dict:
        """A resting buy-stop, one per event, cancelled after {ENTRY_EXPIRY_BDAYS} sessions.

        No `max_fill`: the guide is explicit that a stock opening above the trigger is filled at
        the open and that the worse price should be counted. The stop-width cap at the fill is
        what refuses the cases where that gap made the trade unsizeable.
        """
        return {
            "order": "stop",
            "base_id": ctx.extras.get("reaction_date"),
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
            reasons.append(f"buy-stop above the {ctx.extras.get('reaction_date')} reaction high")
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
