---
name: backtest-review
description: Comprehensive review of a strategy's optimise-stage backtests from its Strategy page URL — is the implementation correct (no look-ahead, accounting that reconciles, fills inside the bar, stops honoured), are position sizing and risk management applied as the rules say, does each trade obey the rules, how faithfully does the code follow the method as its originator and the research describe it, which market regimes it works and fails in (and whether it should hold the index or cash there), is the edge real and where does it come from, is the result robust or does it rest on a few outlier trades, one stock, one year, big swings over time or luck (outlier removal, yearly and rolling excess, halves, block bootstrap, parameter neighbourhood), does it beat buy-and-hold fairly (total return and cash, survivorship, beta vs alpha, equal-weight and momentum alternatives, after tax, capacity, statistical power, luck across all strategies, contribution to the book) — then propose robust, prioritised improvements (bugs first) with a test plan and a paper-trading gate. Analysis only — never reads verify runs, edits code or queues jobs.
argument-hint: <strategy page URL, e.g. http://localhost:8000/#/strategies/minervini>
disable-model-invocation: true
---

# Backtest review

Skill version: 5

Review a strategy's backtests end to end and propose prioritised improvements. One strategy per run;
every finished review is recorded (see Output), so the tracker says which strategies are due.

Strategy page: $ARGUMENTS

If no URL was given, ask for one (or a strategy key) and stop.

Work in /Users/admin/Workspace/trading and follow CLAUDE.md, especially "backtests run in stages"
and "every strategy change updates its Strategy page". The strategy key is the path segment after
`#/strategies/`. The web app runs at the URL's host; read data through its APIs, the code, or the
database read-only (`scripts/swing_screener/marketdata/db.py`). Download nothing. Write any working
script to the scratchpad, not the repo.

The review answers, in order of what can invalidate what: **is the code right** (step 3) → **is it the
method** (step 7) → **is the edge real** (step 4) → **is it robust** (step 5) → **does it beat buy-and-hold fairly** (step 6) → **when does it work**
(step 8) → **what to change** (steps 9–11). A look-ahead bug makes every later number meaningless, so bugs are found first and ranked
first.

## 0. Check the tracker

```bash
cd scripts && PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.strategy_reviews status
```

It lists every strategy as **never reviewed**, **strategy changed** (its version moved since the last
review), **skill updated** (reviewed before checks this skill has added since) or **current**. If this
strategy is current, say so, give the stored headline (`... strategy_reviews show --strategy <key>`) and
ask whether to review it again before going on. If it was reviewed before, read that review first: start
from its bugs and proposed changes, and say in the new review which were fixed, tested or are still open.

## 1. Find the runs to review

- GET `/api/strategies/<key>`: the strategy's rules (`gates`, `setups`, `entry_rules`, `exit_rules`,
  `stop_rules`, `target_rules`, `sizing_rules`, `filter_rules`, `market_rules`, `regime_note`,
  `params`), its current version and spec_id, `status`, `source` (the code file), and `backtests`
  (each with market, stage, spec_id, version, archived, and its variant overrides).
  GET `/api/backtest-stages` gives the stage windows; GET `/api/strategy-edges` gives the strategy's
  edge badge per market (excess over buy-and-hold, and the stage it was judged in).
- Choose, per market, the latest NON-archived run of the CURRENT version in the `optimise` stage,
  run with the strategy's own `backtest_args` (no `--const` overrides): that is the baseline. Also
  collect the optimise runs of the current version that differ only by `--const` overrides: they are
  variants already tested, so do not re-propose them.
- If the current version has no optimise run, use the latest version that has one, and say clearly
  that its rules differ from today's code (diff the changelog entries in between).
- Do NOT open, read or use `verify`-stage runs (their trades, tables or figures). Tuning on them
  would make 2022+ in-sample. You may quote the edge badge and the `status` headline, nothing more.
  Treat `full` and legacy runs as context only, never as evidence for a change.
- A portfolio strategy (a timing or rotation book with its own runner, no per-symbol scan) has no
  funnel, signal cache or trade anatomy: skip those parts and say so.
- List the runs you chose (id, market, version, stage, overrides) before you analyse anything.

## 2. Read each baseline (per market)

GET `/api/reports/<id>` (report + summary), `/api/reports/<id>/tables/<name>` (`trades`, `equity`, and
`cost_sensitivity` where present), `/api/reports/<id>/funnel` and `/funnel/<stage>` (where candidates
were lost), and `/api/reports/<id>/trade-anatomy?symbol=<sym>` for individual trades. Build a
KEY-PARAMETER scorecard: CAGR, excess CAGR vs buy-and-hold, max drawdown and longest drawdown, Sharpe,
Sortino or Calmar, trades per year, win rate, average R, profit factor, exposure, turnover and costs,
average days held, and R by exit reason. One table per market, with sample sizes.

## 3. Audit the implementation

Run the bundled audit on each baseline (it reads the run's tables and stored prices, never past the
run's window):

```bash
cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/audit_run.py \
    --run <id> --host <the URL's host> --risk-pct <the strategy's risk per trade, if it has one>
```

It prints accounting, fills against the day's bar, stops, sizing and open heat, and a regime split
(used in step 8). Every flag it raises is a **lead**, not a finding: follow each one into the code and,
for trades, the chart, and classify it as a **bug**, an **explained** behaviour (say what explains
it), or **unresolved**. Then check what the script cannot:

**Point in time (read the code path: `build_context`, `evaluate`, the loaders, the runner).**
- Fills: a signal on a bar's close fills on a later bar (next open or next close), never the same
  close. An entry or exit outside the bar's low–high range is look-ahead, an adjustment mismatch
  (check the split and dividend history), or a modelled gap fill.
- Every input is read as of its publication: fundamentals and earnings by filing date, economic data
  with its release lag, ranks and percentiles computed from data up to that day only.
- Universe: the stocks as they were on each date (`universe_history`), not today's members.
- Indicators: no centred windows, no `shift(-n)`, no full-sample normalisation or z-scores.
- The stage boundary: say whether `tests.test_backtest_stages` covers this strategy (it covers every
  registered one with `--all`).

**Accounting.** Equity reconciles with the trades (the script's "unexplained" line), costs are charged
on both sides, cash never goes negative unless the rules allow leverage, open positions never exceed
the slot limit, and the funnel adds up (signals = taken + passed up for slots + for cash + skipped at
the fill). Where the runner has a buy-and-hold mode, it must equal the benchmark exactly.

**Fill timing.** Match each trade to the signal whose planned stop it carries (an order that rests
keeps its signal's levels) and measure the sessions from signal to fill and how far the price paid sits
above the plan, in ATR. Report average R and n for: filled next session; filled later near the plan (the
breakout faded back and re-triggered); filled later more than 1 ATR above it (chased). An order that
waits for a slot can fill past the strategy's own anti-chase gate and stop cap, and in a slot-limited
book this can be most of the trades — the donchian review (`research/review-donchian-2026-11-14.md`)
found 62% of US trades there at +0.03R against +0.77R for next-session fills.

**Position sizing and risk management, against the rules as written** (`sizing_rules`, `stop_rules`,
`params`):
- Risk per trade at entry matches the rule (e.g. 1% of equity), and where it does not, which cap
  explains it (position-size cap, cash, slots).
- Stops are where the rules place them (distance from entry, ATR multiple, structure) and are honoured:
  losses cluster at −1R; the tail beyond −1.5R is gaps (count them) or a stop not acted on (a bug).
- Open heat (total risk on at once), the largest single position, and any concentration the rules
  intend to limit (sector, correlated names).
- Then against the method and the literature (step 7): how the originator sizes and stops, and what
  is known about fixed-fractional risk, volatility sizing and drawdown control. Hypotheses, not findings.

**Trade-by-trade audit.** Pick a stratified sample per market: the 5 best and 5 worst trades by R, the
longest hold, and 10 drawn at random (state the seed). For each, open its trade anatomy and stored
signal, and check that the gates passed, the setup is the one the rules describe, and the entry, stop,
target, size and exit reason sit where the rules put them. Winners matter as much as losers: a rule
broken on winners is still broken. Report a verdict per trade — **obeys**, **violates (bug)**, or
**the rule is ambiguous** (say which reading the code took) — in a table.

## 4. Is the edge real, and where does it come from?

The edge badge already says whether the strategy beat buy-and-hold. Answer what it cannot:

- **Trials.** Count the optimise-stage runs of this strategy across versions and variants (every one
  is an attempt). Report the count, and the baseline's Sharpe deflated for it (Bailey & López de Prado's
  deflated Sharpe ratio, from the number of trials and the variance of the trials' Sharpes; say which
  inputs you used). A result that only survives as the best of many tries is not an edge yet.
- **Edge source: selection vs timing.** Build a matched random-entry null from stored prices: for each
  baseline trade, draw stocks that passed the strategy's pre-filter (or, failing that, the market's
  liquidity floor) on the same entry date, held over the same dates; repeat at least 200 times. Compare
  the trades' mean return with the null's distribution (percentile, difference in R or %). If random
  entries do about as well, the edge is in exposure, timing and exits, not in the stock choice — say so,
  because it changes where improvements should go.
- **Signal edge vs portfolio mechanics.** The baseline traded only the signals that won a slot. Score
  every signal the scan produced (`backtest_signals` for the run's spec_id: hard gates passed and a
  setup) on forward returns at 5, 20 and 60 sessions, and maximum favourable / adverse excursion, from
  stored prices up to 2021-12-31. Compare the traded signals with the skipped ones. If the skipped ones
  were as good or better, slots, ranking or sizing are costing the edge. (The cache keeps only the
  current version's rows; for an older run say the signals are gone rather than re-scanning.)
- **Concentration** is measured in step 5.

State every sample size. If the strategy shows no selection edge and no edge over buy-and-hold, say so
first. Then decide what that means: for a method with a strong, documented record by its originator
or in research (Minervini's SEPA, O'Neil, Weinstein, dual momentum…), suspect the implementation
before the method — close the fidelity gaps of step 7 and the bugs of step 3 first, and recommend
retiring only once a faithful version has been tested and still fails. For a method without such a
record, recommend retiring or rethinking it before proposing tweaks.

## 5. Is the result robust?

An edge that comes from a handful of trades, one stock, one year or one lucky ordering of returns is not
something to trade. Run the bundled script on each baseline:

```bash
cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/robustness.py \
    --run <id> --host <the URL's host>
```

It reports, and flags against thresholds fixed in the script before any run:

- **Outliers.** P&L and CAGR left without the best 1, 3, 5, 10 trades and the best 5% and 10%;
  expectancy trimmed of the best and worst 5%; the share of P&L from the best three stocks.
- **Over time.** Every year against the benchmark; the share of the whole gain earned in the best year;
  the first half against the second; rolling one-year and three-year excess (share of windows positive,
  worst, median); the longest stretch below a previous high and the time spent under water.
- **Luck.** A stationary block bootstrap of the daily returns, strategy and benchmark resampled
  together: the 5th–95th percentile of CAGR, excess and max drawdown, and the chance the excess is
  positive. The 5th-percentile drawdown is the planning figure, not the backtest's own.

Then add what the script can't see:

- **Parameter neighbourhood.** Place the baseline among the variants already run (step 1) that move one
  parameter: is it on a plateau (neighbours within a point or two) or a peak (neighbours much worse)?
  A peak means the shipped values were fitted. Name the runs.
- **Markets.** Does the same rule set work in both markets? A result in one market only needs a reason
  that isn't "that's where it worked".
- **Costs.** `cagr_std_cost` / `excess_std_cost` in the summary (and `cost_sensitivity` where the run
  has it): does the result survive the market's standard cost and doubled slippage?

Read the flags with the method in mind. A trend or breakout system is outlier-driven by design, so for it
the question is whether the winners are **many and spread** (many stocks, several years) or a handful.
A rebalancing or rotation book with few instruments makes the stock-concentration flag meaningless (the
script says so). Give a one-line verdict per market: **robust**, **fragile** (name the flags that
decide it), or **not enough evidence** (too few trades, years or episodes). A fragile baseline caps how
high any improvement built on it can rank in step 10.

## 6. Does it really beat buy-and-hold?

The goal is a strategy worth trading instead of the index, so the comparison has to be fair and the
win has to be skill, not exposure, a simpler rule, the tax bill or luck. Run both scripts on each
baseline:

```bash
cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/benchmark_check.py \
    --run <id> --host <the URL's host>
cd scripts && PYTHONPATH=. .venv/bin/python ../.claude/skills/backtest-review/scripts/cross_strategy.py \
    --run <id> --host <the URL's host>
```

- **A fair benchmark.** Buy-and-hold with dividends (total return), the strategy's idle cash earning
  the cash rate, and an optimistic dividend credit on what it holds: the fair excess is a range. In
  India the total-return index is a proxy; when the script says the measured dividend yield looks low,
  re-run with `--div-yield` set from NSE's published index yield and report both.
- **Survivorship.** The stored universe is today's listed stocks, so failed companies are missing from
  every backtest but present in the index. A small excess over buy-and-hold is inside this bias — say
  so whenever the excess is a few points or less.
- **Beta or alpha.** Beta, alpha and its Newey-West t-statistic against the total-return index; the
  index held at the strategy's own daily exposure; the strategy scaled to the index's volatility. An
  excess that vanishes against the exposure-matched index is market exposure. A strategy that trails on
  return but wins at equal volatility has an edge that a larger allocation could use.
- **Simpler alternatives.** The same liquid universe held equal-weight, and a plain 12-1 momentum top
  decile, monthly. The strategy's selection must beat owning everything it picks from, and a plainer
  rule. These books carry no costs: allow for that before calling a winner. (The index with a trend
  filter is in the audit's regime section, step 8.)
- **After tax.** The strategy taxed each year on realised gains (short- and long-term by holding
  period, losses carried forward, cash interest taxed), buy-and-hold taxed once at the end. India uses
  today's rates; the US rates are an assumed bracket — say which. A pre-tax win that turns into an
  after-tax loss is not a win for a taxable account.
- **Capacity.** Positions against each stock's 20-day traded value at entry, the capital at which they
  reach 1% of it, and R by liquidity quintile. An edge living in the thinnest fifth may not exist at
  real size.
- **Statistical power.** Tracking error, information ratio, the years needed to tell a 3-point edge from
  noise, and the minimum track record for the observed excess. When that is decades, the backtest
  cannot settle the question: say so, and size the paper-trading gate (step 11) by it.
- **Luck across strategies.** The deflated Sharpe counted against every optimise and legacy backtest in
  the market, not only this strategy's. If the strategy is being judged because it looked best among
  many, this is the figure that applies.
- **Book contribution.** Correlation with every other strategy's baseline, and the equal-weight book
  with and without it. A strategy that trails buy-and-hold alone keeps a role only if it lifts the book's
  Sharpe or cuts its drawdown.
- **Other market cycles.** 2013–2021 was mostly a bull market, the hardest for timing to beat
  buy-and-hold. If a context run before 2013 exists (`full` stage with an earlier `--start`), report how
  the strategy fared through the 2008 bear market and the 2000s — as context, never as the verdict, and
  never a reason to change a rule. If none exists, name the command that would make one (step 11).

Close the step with one line per market: **beats buy-and-hold fairly** (net of exposure, simpler
alternatives and tax), **matches it with less risk** (a role in the book or with more allocation), or
**does not** — and which check decided it.

## 7. The method, from the knowledge base

Step back from this implementation and use what you know about the method itself. Read the strategy's
rules, its `thesis`, `caveats` and `changelog`, and any spec it cites (e.g.
`research/minervini-backtest-spec.md`, `research/*-spec.md`, `research/creator-*.md`).

- **Fidelity table.** One row per rule of the method as its originator teaches it (books, interviews,
  published rules, with page or source): the originator's version, this code's version, and a status:
  - **faithful** — same rule, same threshold;
  - **proxy** — the data does not exist, a stand-in is used (name it; say how close it tracks);
  - **deliberate deviation** — changed on purpose for realism (lags, costs, next-bar fills);
  - **omitted** — left out;
  - **added** — not in the method;
  - **accidental** — the code does not do what its own docs or the method say. This is a **bug**: it
    goes to step 10 with the bugs from step 3.
  Say whether each deviation plausibly matters. Proxies, deliberate deviations and omissions are
  documented in `caveats`, not "fixed": check that they are.
- **Literature.** What published research and long practitioner experience say about this class of
  strategy: the market conditions it works and fails in, its known failure modes, and how exits,
  sizing, market filters and universe are usually handled. State sources accurately; say plainly when
  something is practitioner lore rather than tested evidence. Never invent a citation or a number.
- **Published figures.** If the source publishes results, list how its assumptions differ from this
  backtest (period, costs, lags, total return vs price, how returns are annualised, universe). A gap
  between the two is explained step by step — author's assumptions → + lags → + costs → + total
  return and cash → + fills → out of the author's period — where runs exist for a step; otherwise
  name the variant runs that would build that table (step 11). An unexplained gap points back to step 3.
- **Known choices.** A deviation the `changelog` or `caveats` show was made on purpose and already
  tested is reported as a known choice with that outcome, not re-proposed.
- Everything from this step except bugs is a **hypothesis to test**, not a finding. It enters step 10
  with the type "from the method" or "from the literature", and the data decides how far it ranks.

## 8. Market regimes: when does it work, and what should it hold otherwise?

A strategy can earn its edge in one regime and give it back in another. Any strategy looks regime-bound
in hindsight, so a regime here is a rule to test, not a finding.

- **Define regimes before reading results, point in time.** The audit script's split uses index trend
  (prior close vs 200-day average) and volatility (20-day realised vs its trailing one-year median).
  Add at most one or two lenses that fit the method (breadth from the snapshot, a rates or liquidity
  regime), fixed before looking, and count every lens tried as a trial (step 4).
- **Per regime:** the strategy's return and excess over the index, trades entered and their win rate
  and average R, and the number of separate **episodes**, not days — two bear markets are two
  observations however many sessions they hold.
- **Can it be acted on?** Regimes must last well beyond the detection lag; measure the loss suffered
  before a switch flipped and the switches per year (each costs).
- **The overlay test:** compare the index buy-and-hold, the index held only in the good regime (else
  cash), the strategy, and the strategy only in the good regime. If the filtered index does as well
  as the filtered strategy, the filter carries the result and the strategy adds nothing.
- **Overlap:** many strategies already gate on the market (`market_rules`, `regime_note`, a market
  filter in `backtest_args`). Say whether a regime rule would only double-count that gate.
- **The off state** (cash, the index, bonds) follows from the method's thesis, not from trying each.
- A regime rule that survives this goes to step 10 as type "regime overlay": a gate with a fixed
  threshold, a version bump, optimise first, verify once.

## 9. Diagnose (evidence from the optimise runs only)

For every weak key parameter, find the cause in the data:
- which gates / setups / exits produce the losers (R by setup code, exit reason, year, regime from
  step 8, sector, stop width, entry gap, days held);
- where the funnel throws away candidates (gates dropping most bars, signals skipped for full
  slots, gaps above the buy range, order expiry);
- what steps 3–6 and 8 found about implementation, selection, robustness, the benchmark, sizing and regimes.

A pattern seen on fewer than ~30 trades is a hypothesis, not a finding.

## 10. Propose improvements, prioritised

Bugs first, in their own table: what is wrong, the evidence (run, trade, code line), which figures it
contaminates, and the fix. A bug fix is a behaviour change (version bump, re-run) but not a tuning
choice: it ranks above every improvement because results from buggy code cannot be compared.

Then, for each key parameter (e.g. max drawdown, average R, win rate, trade count, excess CAGR), a
ranked list of changes:

| Priority | Change | Parameter it targets | Evidence (run id, table, numbers, n — or source) | Expected effect | Side effects on other parameters | Robustness | Type |
|---|---|---|---|---|---|---|---|

- Type is one of: parameter change (an existing constant, as `--const NAME=VALUE`), new rule
  (a gate, setup, exit or sizing change that needs code), mechanics (`backtest_args`, e.g. exit mode),
  risk management (sizing, stops, heat, concentration), regime overlay (step 8), from the method
  (closes a fidelity gap from step 7), or from the literature. Evidence for the last two names the
  source and what the runs say about it (supports / contradicts / untested here).
- **Robustness gate.** A change ranks high only if its case does not rest on one spike: say for each
  whether its evidence holds across neighbouring values of the parameter (a plateau, not a peak),
  across most years and both up and down markets, in both markets (or why one market only), and with
  costs doubled and realistic gap slippage (`cost_sensitivity` where the run has it). Mark it
  "fragile" otherwise, and rank fragile changes last whatever their headline gain.
- Rank by expected impact × strength of evidence × robustness × simplicity. Mark trade-offs
  (e.g. tighter stop: higher win-rate loss, fewer big winners).
- Put improvements where step 4 found the edge: with no selection edge, entry-filter tweaks are low
  priority; if skipped signals beat traded ones, fix ranking / slots before the rules.
- Never move a published threshold because the result improves: that turns a test of the method into
  a fit to 2013–2021. Prefer few, large, well-evidenced changes over many small tweaks; each new
  variant is another trial. Do not propose a variant already tested (step 1). Never base a change on
  verify results.
- Balance the two sources: do not drop a well-founded method gap just because these runs cannot show
  it yet, and do not promote a textbook idea over a clear contrary result in the data.

## 11. Test plan (do not run it unless asked)

- Pass criteria for each proposed variant, written BEFORE any run: which key parameters must
  improve, by how much, which must not get worse beyond what limit, and the robustness checks it must
  pass (neighbouring values, years, markets, doubled costs).
- The exact queue commands, optimise stage only, bug fixes first, then one variant per change, then
  the best combination:
  `python -m jobs enqueue backtest --market <m> --strategies <key> --stage optimise --const NAME=VALUE`
- For changes needing code: which file and constants, whether it changes `evaluate()` (a rescan) or
  only post-scan logic (`signal_exempt_consts` / `signal_version`), and the version bump, changelog and
  doc updates CLAUDE.md requires.
- What would justify spending the strategy's one verify run afterwards.
- **Paper-trading gate.** Strategies refined before October 2026 have no clean historical hold-out, so
  forward data is the final test. Say what paper record would confirm the edge: how many trades, over
  how long, which key parameters must hold and at what levels — and whether the strategy already has a
  paper book (`paper_orders`) and what it shows so far.

## Output

Write the full review to `research/review-<key>-<YYYY-MM-DD>.md` (do not commit it), with a chart
wherever a block of comparable figures sits (regimes, R by exit, years), and give the headline in chat:
the verdict, the bugs, and the top three changes.

Then **record it in the tracker**. This is the one write the review makes; it stores the markdown in
Postgres, so the review survives a worktree being cleaned up:

```bash
cd scripts && PYTHONPATH=. .venv/bin/python -m swing_screener.backtesting.strategy_reviews record \
    --strategy <key> --file ../research/review-<key>-<YYYY-MM-DD>.md \
    --runs '{"us": <id>, "india": <id>}' --bugs <n> \
    --verdicts '{"us": {"code": "...", "edge": "...", "robust": "...", "vs_buy_hold": "..."}, "india": {...}}' \
    --headline "<the verdict in a sentence or two>" --changes '["<change 1>", "<change 2>", "<change 3>"]'
```

Verdict values: `code` clean | bugs | unresolved (step 3 and accidental gaps from step 7); `edge` yes |
small | no | not enough evidence (step 4); `robust` robust | fragile | not enough evidence (step 5);
`vs_buy_hold` beats | matches with less risk | does not (step 6). Give only the markets reviewed. If the
baseline was an older version's run (step 1), pass `--spec-id` and `--version` of that run.

1. Runs reviewed.
2. Scorecard per market.
3. Implementation audit: point in time, accounting, sizing and risk, the trade sample — each flag
   classified as bug, explained or unresolved.
4. Is the edge real: trials and deflated Sharpe, selection vs timing, signal vs portfolio.
5. Is it robust: outliers, years and halves, rolling windows, the bootstrap, parameter neighbourhood,
   markets and costs — the flags table and a verdict per market (robust / fragile / not enough evidence).
6. Against buy-and-hold, fairly: total-return benchmark and cash, survivorship, beta and alpha,
   exposure- and volatility-matched books, simpler alternatives, after tax, capacity, statistical power,
   luck across strategies, book contribution, other cycles — and a verdict per market.
7. The method: fidelity table with statuses, literature, published figures and the gap, known choices.
8. Regimes: the split, episodes, the overlay test, and whether the strategy should stand aside.
9. Diagnosis with evidence from the runs.
10. Bugs, then the prioritised improvement table per key parameter, with robustness.
11. Test plan: pass criteria, commands, verify condition, paper-trading gate.
12. What you could not determine and which data would settle it.

Report bad news plainly; if the code has a bug, say so before anything else, and if the strategy has
no demonstrated edge, say so before proposing tweaks. Do not edit code, queue jobs or commit; recording
the review in the tracker is the only write.

## Skill versions

A change that adds or changes a check bumps "Skill version" above and adds a line here, so the tracker
marks reviews made before it as "skill updated".

- **5** (2026-11-14) Does it really beat buy-and-hold (step 6): a fair total-return benchmark, beta and alpha,
  simpler alternatives, after tax, capacity, power, luck across strategies, book contribution. The tracker.
- **4** (2026-11-14) Is it robust (step 5): outliers, years and halves, rolling excess, bootstrap, neighbourhood.
- **3** (2026-11-14) Implementation audit (step 3, with fill timing), position sizing and risk, the trade
  sample, fidelity statuses, market regimes (step 8).
- **2** (2026-11-12) The method from the knowledge base; is the edge real; suspect the implementation of a
  proven method first. The family reviews of 2026-11-12 were made under this version.
- **1** (2026-11-11) Prioritised improvements from the optimise-stage runs.
