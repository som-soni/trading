---
name: strategy-scout
description: Rank every backtested strategy by the strength and robustness of its edge — beyond the edge badge, adjusted for how many variants were tried, and how the strategies overlap — and recommend which to develop, which to retire, which to paper-trade and which combinations add something. Analysis only — never reads verify runs beyond their verdicts, edits code or queues jobs.
argument-hint: "[market: us | india | all] (default all)"
disable-model-invocation: true
---

# Strategy scout

Find where the edge is across all strategies, so effort goes to the ones worth developing.

Scope: $ARGUMENTS (a market from config/MARKETS, or empty for every market).

Work in /Users/admin/Workspace/trading and follow CLAUDE.md, especially "backtests run in stages".
The web app runs at http://localhost:8000; read through its APIs, the code, or the database read-only
(`scripts/swing_screener/marketdata/db.py`). Download nothing. Write any working script to the
scratchpad, not the repo.

## 1. Inventory

- GET `/api/strategy-edges` (each strategy's badge per market: level, excess over buy-and-hold, stage,
  version, whether it is the current version) and `/api/strategies` (name, kind, behaviour, horizon,
  version, `status`). Skip long-term trackers.
- Per strategy and market, pick the baseline: the latest non-archived optimise run of the current
  version with the strategy's own `backtest_args`, as `/backtest-review` does. Note when only an older
  version has one.
- Verify runs: use their verdict (the badge level, `windows.verdict_details()`) and nothing else — no
  trades, tables or figures, so no idea is tuned on 2022+.

## 2. Score each strategy (per market)

| Strategy | Badge | Excess CAGR (stage) | Max DD | Sharpe | Trials | Deflated Sharpe | Trades/yr | Avg R | Exposure | Robustness | Paper record |
|---|---|---|---|---|---|---|---|---|---|---|---|

- **Trials:** the number of optimise runs of the strategy across versions and variants, and the
  baseline Sharpe deflated for it (Bailey & López de Prado, from the trial count and the variance of the
  trials' Sharpes; say the inputs). Many trials and a thin edge is the profile of a lucky fit.
- **Robustness**, from what is stored: the edge in both markets or one; how many years of the window
  beat buy-and-hold; how much of the R came from the best 5% of trades; `cost_sensitivity` where present.
  Summarise as robust / mixed / fragile with the reason.
- **Paper record:** the strategy's paper book (`paper_orders`), if any — trades so far and how they
  compare with the backtest.

## 3. Overlap and combinations

From the baselines' `equity` tables (optimise window only), the correlation of monthly returns
between strategies in each market, and how many of their trades share symbol and month. Name the
clusters that are the same bet under different names, and pairs whose combination would lower
drawdown without giving up return. Say when a combination is already a strategy in the registry.

## 4. Verdicts

Sort every strategy into one of:

- **Develop**: a real, robust edge in the optimise window that is not explained away by trials, or a
  verified edge — worth a `/backtest-review`.
- **Paper-trade**: verified, or the best of what exists, and not yet proven forward — what paper record
  would confirm it.
- **Rethink**: no edge as built, but the method has a known, well-founded case (from the knowledge base;
  say what the implementation likely misses).
- **Retire**: no edge in-sample after a reasonable number of tries and no strong case from the method.
- **Not judged**: no usable baseline; say which run would settle it.

Give the evidence for each verdict in one line. Then the top three actions across the whole set, in
order — which strategy, what to do next, and the command or skill to do it (e.g.
`/backtest-review http://localhost:8000/#/strategies/<key>`).

## Output

1. Inventory: strategies, baselines chosen, gaps.
2. Score table per market.
3. Overlap: clusters and promising combinations.
4. Verdicts with one-line evidence.
5. Top three actions.
6. What could not be judged and which run or data would settle it.

Report plainly; most strategies having no demonstrated edge is a normal result and should be said.
Do not edit code, queue jobs or commit.
