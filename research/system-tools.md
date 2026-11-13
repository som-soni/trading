# Tools for the trading system

Part of [my trading system](system-overview.md). The system has to outlast any one source. Today it draws on two creators,
and it will draw on more, on books, and on what my own trades teach me. So the tools are not built *per rule* or *per
creator*. They are four general parts, the market-level twin of what the app already does for stocks. A new idea then
becomes **data** (a reading, a rule, a study), not a new tool.

**In short**

- Four parts: **readings** (the market snapshot), **rules** over those readings, a **journal** of my trades and daily
  calls, and **studies** that test a rule on stored history.
- They mirror the stock side: snapshot fields → screens → screen study. A market rule is to the market snapshot what a
  screen is to the stock snapshot.
- A creator, a book or my own review adds **rules with a source tag**. If two sources agree, it's one rule with two
  sources; if they disagree, it's two rules, and a study decides.
- **Built:** the market snapshot (5 Nov 2026), shown on Today as **Market readings**. **Next:** the rule registry on
  Today's Market card, then the journal, then the generic rule study.
- Tools show readings and which rules fire. The call — rung, bias, risk tier, hunt — stays mine.

---

## 1. The design

| Stocks (exists) | Market (this design) | Status |
|---|---|---|
| **Stock snapshot**: one row per stock per day, a documented field catalog (`screens/snapshot.py` `FIELDS`) | **Market snapshot**: one value per market, session, subject and field; documented catalog (`analytics/market_snapshot.py` `FIELDS`) | **Built** |
| **Screens**: conditions over fields; built-in ones in code with named constants, your own saved from the app | **Market rules**: a condition over market fields, an *effect* on the review, its *sources*, its *status* | Next |
| — | **Journal**: my closed trades (with the stop planned at entry) and each day's review call | Then |
| **Screen study**: forward returns after a screen qualifies a stock | **Rule study**: forward index or strategy returns after a rule fires, inside the backtest stages | Then |
| **Strategies page**, generated from each strategy's code docs | **System page** of rules by decision step, generated from the registry | Later |

Four ground rules hold for every part:

| # | Rule | Why |
|---|---|---|
| G1 | **Readings, not decisions.** A tool may say "stretch rule fires"; the five fields of the review are mine | The point is to train judgement, not to replace it |
| G2 | **Point in time.** Every reading is what that evening would have shown | Past reviews can be replayed, and every rule tested on the numbers I would have traded on |
| G3 | **One definition.** Reuse the code that already defines a thing — the strategies' market gate, the Stage model, the screens' predicates | Two versions of "follow-through day" disagree on exactly the cases that matter |
| G4 | **No display for a rejected rule.** A rule a study rejects is kept, marked rejected, and stops firing | A dead rule on screen keeps steering me |

## 2. Readings — the market snapshot (built)

**What it holds.** For each market, every session since the data starts (US 1993, India 2005), three kinds of subject:

| Subject | Fields |
|---|---|
| Each review index (config: `broad_index_symbols` plus `review_symbols`) — US: SPY, QQQ, IWM, RSP; India: Nifty 50, Nifty 500, Midcap 150, Smallcap 250 | Close and day change; distance from the 9- and 21-day EMA; the high against the 9-day EMA (a retest); distance from the 50- and 200-day and their slopes; distance from the weekly 9, 21 and 50 EMA; distance below the 52-week high; distribution days in 25 sessions; volume against its 50-day |
| The market | Breadth (advancers, share above the 5- and 50-day, new highs and lows, big movers); the volatility index and its distance from the market's threshold; **the strategies' own market gate** (risk on / pilot / off); whether a follow-through day is in force |
| Each ratio pair (config: `breadth_pairs`) — SPY ÷ RSP; Nifty 50 ÷ Nifty 500 and ÷ Midcap 150 | The ratio, its 1-month change, its distance from its 50-day |

**Where it shows.** Today → **Market readings**: one table of the indexes, one list of the market-wide readings. The
card applies no rule. Each heading's tooltip is the field's doc from the catalog.

**How it's kept.** Job `market_snapshot` (analytics layer) runs in the close routine after breadth, and rewrites the
last ten sessions each night. `tests.test_market_snapshot` checks that every field is documented and computed, and that
values are point in time: computed on prices cut off at a session, they equal the stored history's row.

**Checked against the hand-made review of 2 November 2026:** QQQ −3.65% from its 9-day EMA (the review said −3.7%),
8 distribution days (8), VIX 21.15 (21.1), 60% advancers (601 of 1,000).

**Adding a reading** (when a rule needs one): a `Field` entry with its doc, its computation in
`instrument_fields` / `market_fields` / `pair_fields` (reusing existing code per G3), then `--full` to backfill and the
test. A field earns its place when a rule uses it.

**Not in it yet:**

| Reading | Why not yet |
|---|---|
| The number of stocks passing the Trend Template, daily | The screen's predicates are replayed per stock per bar; a daily count over all history is a heavier job, best added to the breadth job. Needed for the "bottoming" row |
| Count of breakouts holding vs failing, rolling | Needs the breakout scan (`research_breakouts.py`) run daily |
| Hourly readings (the hourly 9 EMA retest) | No intraday prices are stored |
| Scheduled events (central banks, CPI, budgets, elections) | No event table yet (§5) |

## 3. Rules — the registry (next)

**What a rule is.**

| Part | Example: the stretch rule |
|---|---|
| Condition over readings | The benchmark's `vs_ema9_pct` ≤ −2 (QQQ: −3), until a session whose `high_vs_ema9_pct` ≥ 0 |
| Effect | Hunt: no new shorts until the retest. Effects can only *reduce* rung or size, never raise them |
| Decision step | Market → stretch (review Q2) |
| Sources | Luk, stream of 3 Nov 2026 |
| Status | Tested — supported for shorts ([rule tests](daily-review-rule-tests.md) §2); the long mirror rejected |

**Where rules live.** Like the built-in screens: in code, thresholds as named constants, documented with `{NAME}`
placeholders so the page shows live values, with a version and changelog so a change is visible. Ad-hoc rules I'm
exploring can be saved from the app, the way custom screens are.

**Where they show.** Today's **Market** card already has the right shape (a verdict, then ✓/✗ signals). Today it is fed
by six hard-coded tone signals in the post-market report. Those six become the first registry entries, the strategies'
market gate the next, and the card lists the adopted rules that fire, with their effect.

**Creators are source tags.** Minervini's "size by results" and the repository's progressive exposure are one rule with
two sources. If a later source says the opposite of an existing rule, it becomes a second rule beside the first, both
marked proposed, and the rule study (§5) decides.

## 4. Journal (then)

The only part whose history can't be rebuilt later, so it should start soon.

| Record | Fields | Feeds |
|---|---|---|
| **Trade** | Market, symbol, side, entry and exit (date, price, size), **the stop planned at entry** (no stop, no R), setup code, strategy if one produced it | Net R of the last 10 trades and losses in a row (the feedback rule); the month's result (the hot-streak rule) |
| **Daily call** | Rung, bias, risk tier, hunt and events, as I set them; which rules fired; a note | Grading my calls against what followed; checking whether override days actually lost less |

**Run after exit** (proposed; a Reddit post, Nov 2026, lesson 10). For each closed trade, the best and worst move *after*
the exit at 5, 20 and 60 sessions, in R, computed from stored closes, so I enter nothing by hand. A pattern of big runs
after exit says my exits are too early. Fix it with a tested exit rule (the 150-day or 50-day trend exit, already measured
here), not with the post's ad-hoc "leave 10% to run". The strategies' backtest trades could get the same column, to compare
my exits with the rules'.

Entry: a form on Today and an import of the broker's tradebook CSV. The broker module reads holdings, positions and margins
only. Letting it also read orders and trades would still be read-only, but it widens a boundary set on purpose, so it
would be its own decision.

## 5. Rule study and data sources (then)

**Rule study.** Pick a rule (or a condition), a market and a stage; get forward index returns after it fires against all
other sessions, and the same for a strategy's trades. It replaces the one-off scratch studies (the stretch study, the
fast-rebound study) with one tool. It must keep the stage discipline: tune on 2013–2021, verify once on 2022 to today.

**Data sources,** each a table that feeds a field, never a tool of its own:

| Source | Feeds | Upkeep |
|---|---|---|
| Market events: FOMC, RBI MPC, CPI, the Budget, elections | An `event_next_session` field; the event rule and its study | The Fed, RBI and BLS publish a year of dates: a yearly entry, or a download job later |
| My trades | §4 | Form and CSV import |
| Intraday prices (optional) | The hourly retest | A new download; only if the hourly rule earns it |

## 6. Where the earlier tool list went

| Earlier idea | Now |
|---|---|
| T1 Index stretch panel | Fields `vs_ema9_pct`, `vs_ema21_pct`, `high_vs_ema9_pct`, the weekly EMAs — **built**; the stretch *rule* goes in the registry |
| T2 Distribution and follow-through counter | Fields `dist_days`, `ftd` — **built** |
| T3 Narrow vs broad panel | Pair fields — **built**; no rule (rejected as a forecast) |
| T4 Setup supply series | A field still to add (§2) |
| T5 Are breakouts working? | A field still to add (§2) |
| T6 Trade log and feedback dial | The journal (§4) plus the feedback and hot-streak rules |
| T7 Event calendar | A data source feeding a field (§5) |
| T8 Short-side list | A short strategy's live setups on Today's setups — the strategy framework already does this |
| T9 Daily review sheet | Today itself: readings, then the rules that fire, then the call saved to the journal |

## 7. Order to build

| Step | Part | Status |
|---|---|---|
| 1 | Market snapshot | **Done** 5 Nov 2026 |
| 2 | Rule registry on Today's Market card; the six tone signals and the market gate as its first rules; the review's tested rules next | Next |
| 3 | Journal: trades and daily calls | |
| 4 | Rule study | |
| 5 | Snapshot fields: Trend Template count, breakout tally; the event table | When a rule needs them |

## 8. Decisions for me to make

1. **Trade log source.** A form plus the tradebook CSV, or letting the broker module read orders and trades. And the US:
   which broker, if any.
2. **Event calendar upkeep.** A yearly manual entry, or a download job.
3. **Intraday data.** Whether the hourly retest is worth a new download.
