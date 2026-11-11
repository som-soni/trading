---
name: backtest-review
description: Review a strategy's optimise-stage backtests from its Strategy page URL — is the edge real and where does it come from, how does the code compare with the method as its originator and the research describe it, what do the runs show — and propose robust, prioritised improvements per key parameter with a test plan and a paper-trading gate. Analysis only — never reads verify runs, edits code or queues jobs.
argument-hint: <strategy page URL, e.g. http://localhost:8000/#/strategies/minervini>
disable-model-invocation: true
---

# Backtest review

Review a strategy's backtests and propose prioritised improvements.

Strategy page: $ARGUMENTS

If no URL was given, ask for one (or a strategy key) and stop.

Work in /Users/admin/Workspace/trading and follow CLAUDE.md, especially "backtests run in stages"
and "every strategy change updates its Strategy page". The strategy key is the path segment after
`#/strategies/`. The web app runs at the URL's host; read data through its APIs, the code, or the
database read-only (`scripts/swing_screener/marketdata/db.py`). Download nothing. Write any working
script to the scratchpad, not the repo.

## 1. Find the runs to review

- GET `/api/strategies/<key>`: the strategy's rules, its current version and spec_id, `status`,
  and `backtests` (each with market, stage, spec_id, version, archived, and its variant overrides).
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
- List the runs you chose (id, market, version, stage, overrides) before you analyse anything.

## 2. Read each baseline (per market)

GET `/api/reports/<id>` (report + summary), `/api/reports/<id>/tables/<name>` (`trades`, `equity`, and
`cost_sensitivity` where present), `/api/reports/<id>/funnel` and `/funnel/<stage>` (where candidates
were lost), and `/api/reports/<id>/trade-anatomy` for individual trades. Build a KEY-PARAMETER
scorecard: CAGR, excess CAGR vs buy-and-hold, max drawdown and longest drawdown, Sharpe, Sortino or
Calmar, trades per year, win rate, average R, profit factor, exposure, turnover and costs, average
days held, and R by exit reason. One table per market, with sample sizes.

## 3. Is the edge real, and where does it come from?

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
  were as good or better, slots, ranking or sizing are costing the edge.
- **Concentration.** How much of the total R the best 5% of trades made, and the best and worst years.

State every sample size. If the strategy shows no selection edge and no edge over buy-and-hold, say so
first. Then decide what that means: for a method with a strong, documented record by its originator
or in research (Minervini's SEPA, O'Neil, Weinstein, dual momentum…), suspect the implementation
before the method — close the fidelity gaps of step 4 first, and recommend retiring only once a
faithful version has been tested and still fails. For a method without such a record, recommend
retiring or rethinking it before proposing tweaks.

## 4. The method, from the knowledge base

Step back from this implementation and use what you know about the method itself. Read the strategy's
rules (`gate_docs`, `setup_docs`, `entry_rules`, `exit_rules`, `param_docs`, `backtest_args`), its
`thesis`, `caveats` and `changelog`, and any spec it cites (e.g. `research/minervini-backtest-spec.md`).

- **Fidelity check.** Compare the rules with the method as its originator teaches it (books, interviews,
  published rules). List every deviation in a table — rule, the originator's version, this code's
  version, missing / simplified / added / different threshold — and whether it plausibly matters.
- **Literature.** What published research and long practitioner experience say about this class of
  strategy: the market conditions it works and fails in, its known failure modes, and how exits,
  sizing, market filters and universe are usually handled. State sources accurately; say plainly when
  something is practitioner lore rather than tested evidence. Never invent a citation or a number.
- **Known choices.** A deviation the `changelog` or `caveats` show was made on purpose and already
  tested is reported as a known choice with that outcome, not re-proposed.
- Everything from this step is a **hypothesis to test**, not a finding. It enters step 6 with the
  type "from the method" or "from the literature", and the data decides how far it ranks: supported by
  the runs, it ranks with that evidence; contradicted, the data wins and you say so.

## 5. Diagnose (evidence from the optimise runs only)

For every weak key parameter, find the cause in the data:
- which gates / setups / exits produce the losers (R by setup code, exit reason, year, market regime,
  sector, stop width, entry gap, days held);
- where the funnel throws away candidates (gates dropping most bars, signals skipped for full
  slots, gaps above the buy range, order expiry);
- what step 3 found about selection, signals and concentration.

A pattern seen on fewer than ~30 trades is a hypothesis, not a finding.

## 6. Propose improvements, prioritised per key parameter

For each key parameter (e.g. max drawdown, average R, win rate, trade count, excess CAGR), give a
ranked list of changes:

| Priority | Change | Parameter it targets | Evidence (run id, table, numbers, n — or source) | Expected effect | Side effects on other parameters | Robustness | Type |
|---|---|---|---|---|---|---|---|

- Type is one of: parameter change (an existing constant, as `--const NAME=VALUE`), new rule
  (a gate, setup, exit or sizing change that needs code), mechanics (`backtest_args`, e.g. exit mode),
  from the method (closes a fidelity gap from step 4), or from the literature (a published or
  well-established practice from step 4). Evidence for the last two names the source and what the
  runs say about it (supports / contradicts / untested here).
- **Robustness gate.** A change ranks high only if its case does not rest on one spike: say for each
  whether its evidence holds across neighbouring values of the parameter (a plateau, not a peak),
  across most years and both up and down markets, in both markets (or why one market only), and with
  costs doubled and realistic gap slippage (`cost_sensitivity` where the run has it). Mark it
  "fragile" otherwise, and rank fragile changes last whatever their headline gain.
- Rank by expected impact × strength of evidence × robustness × simplicity. Mark trade-offs
  (e.g. tighter stop: higher win-rate loss, fewer big winners).
- Put improvements where step 3 found the edge: with no selection edge, entry-filter tweaks are low
  priority; if skipped signals beat traded ones, fix ranking / slots before the rules.
- Prefer few, large, well-evidenced changes over many small tweaks; each new variant is another trial
  (step 3). Do not propose a variant already tested (step 1). Never base a change on verify results.
- Balance the two sources: do not drop a well-founded method gap just because these runs cannot show
  it yet, and do not promote a textbook idea over a clear contrary result in the data.

## 7. Test plan (do not run it unless asked)

- Pass criteria for each proposed variant, written BEFORE any run: which key parameters must
  improve, by how much, which must not get worse beyond what limit, and the robustness checks it must
  pass (neighbouring values, years, markets, doubled costs).
- The exact queue commands, optimise stage only, one variant per change first, then the best
  combination:
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

1. Runs reviewed.
2. Scorecard per market.
3. Is the edge real: trials and deflated Sharpe, selection vs timing, signal vs portfolio, concentration.
4. The method: fidelity table, what the literature says, known choices.
5. Diagnosis with evidence from the runs.
6. The prioritised improvement table per key parameter, with robustness.
7. Test plan: pass criteria, commands, verify condition, paper-trading gate.
8. What you could not determine and which data would settle it.

Report bad news plainly; if the strategy has no demonstrated edge, say so before proposing tweaks.
Do not edit code, queue jobs or commit.
