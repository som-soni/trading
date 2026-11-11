---
name: backtest-review
description: Review a strategy's optimise-stage backtests from its Strategy page URL and propose prioritised improvements per key parameter (CAGR, drawdown, average R, win rate…), with a test plan. Analysis only — never reads verify runs, edits code or queues jobs.
argument-hint: <strategy page URL, e.g. http://localhost:8000/#/strategies/minervini>
disable-model-invocation: true
---

# Backtest review

Review a strategy's backtests and propose prioritised improvements.

Strategy page: $ARGUMENTS

If no URL was given, ask for one (or a strategy key) and stop.

Work in /Users/admin/Workspace/trading and follow CLAUDE.md, especially "backtests run in stages"
and "every strategy change updates its Strategy page". The strategy key is the path segment after
`#/strategies/`. The web app runs at the URL's host; read data through its APIs or the code. Download nothing.

## 1. Find the runs to review

- GET `/api/strategies/<key>`: the strategy's rules, its current version and spec_id, `status`,
  and `backtests` (each with market, stage, spec_id, version, archived, and its variant overrides).
  GET `/api/backtest-stages` gives the stage windows.
- Choose, per market, the latest NON-archived run of the CURRENT version in the `optimise` stage,
  run with the strategy's own `backtest_args` (no `--const` overrides): that is the baseline. Also
  collect the optimise runs of the current version that differ only by `--const` overrides: they are
  variants already tested, so do not re-propose them.
- If the current version has no optimise run, use the latest version that has one, and say clearly
  that its rules differ from today's code (diff the changelog entries in between).
- Do NOT open, read or use `verify`-stage runs (their trades, tables or figures). Tuning on them
  would make 2022+ in-sample. You may say a verify run exists and give its headline verdict from
  `status`, nothing more. Treat `full` and legacy runs as context only, never as evidence for a change.
- List the runs you chose (id, market, version, stage, overrides) before you analyse anything.

## 2. Read each baseline (per market)

GET `/api/reports/<id>` (report + summary), `/api/reports/<id>/tables/<name>` (trades, exits, by-year),
`/api/reports/<id>/funnel` and `/funnel/<stage>` (where candidates were lost), and
`/api/reports/<id>/trade-anatomy` for individual trades. Build a KEY-PARAMETER scorecard:
CAGR, excess CAGR vs the benchmark, max drawdown and longest drawdown, Sharpe, Sortino or Calmar,
trades per year, win rate, average R, profit factor, exposure, turnover and costs, average days
held, and R by exit reason. Show the numbers in one table per market, with sample sizes.

## 3. Diagnose (evidence from the optimise runs only)

For every weak key parameter, find the cause in the data, not in theory:
- which gates / setups / exits produce the losers (R by setup code, exit reason, year, market regime,
  sector, stop width, entry gap, days held);
- where the funnel throws away candidates (gates dropping most bars, signals skipped for full
  slots, gaps above the buy range, order expiry);
- concentration: how much of the total R comes from the best 5% of trades, and the worst years.

Say how big each sample is; a pattern seen on fewer than ~30 trades is a hypothesis, not a finding.

## 4. Propose improvements, prioritised per key parameter

For each key parameter (e.g. max drawdown, average R, win rate, trade count, excess CAGR), give a
ranked list of changes:

| Priority | Change | Parameter it targets | Evidence (run id, table, numbers, n) | Expected effect | Side effects on other parameters | Type |
|---|---|---|---|---|---|---|

- Type is one of: parameter change (an existing constant, as `--const NAME=VALUE`), new rule
  (a gate, setup, exit or sizing change that needs code), or mechanics (`backtest_args`, e.g. exit mode).
- Rank by expected impact × strength of evidence × simplicity. Mark trade-offs explicitly
  (e.g. tighter stop: higher win-rate loss, fewer big winners).
- Prefer few, large, well-evidenced changes over many small tweaks; flag any change that is
  curve-fitting a handful of trades.
- Never base a change on verify-stage results. Do not propose a variant already tested (step 1).

## 5. Test plan (do not run it unless asked)

- Pass criteria for each proposed variant, written BEFORE any run: which key parameters must
  improve, by how much, and which must not get worse beyond what limit.
- The exact queue commands, optimise stage only, one variant per change first, then the best
  combination:
  `python -m jobs enqueue backtest --market <m> --strategies <key> --stage optimise --const NAME=VALUE`
- For changes needing code: which file and constants, whether it changes `evaluate()` (a rescan) or
  only post-scan logic (`signal_exempt_consts` / `signal_version`), and the version bump, changelog and
  doc updates CLAUDE.md requires.
- What would justify spending the strategy's one verify run afterwards.

## Output

1. Runs reviewed.
2. Scorecard per market.
3. Diagnosis with evidence.
4. The prioritised improvement table per key parameter.
5. Test plan with pass criteria and commands.
6. What you could not determine and which data would settle it.

Report bad news plainly; if the strategy has no demonstrated edge, say so before proposing tweaks.
Do not edit code, queue jobs or commit.
