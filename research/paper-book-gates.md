# Paper-book gates

Written 2026-11-12, when the books below were opened, **before any paper result existed**. Each
gate is fixed here and is not re-tuned on paper months. A book that misses its gate goes back to the
optimise stage as a new version. The criteria come from `research/strategy-review-summary.md`
(section 6) and the family reviews.

Strategies refined before October 2026 have no clean historical hold-out, so forward paper data is
the only clean test. All of these books trade the shipped rules unchanged.

## Books

| Book | Market | Opened | Spec at opening | Capital |
|---|---|---|---|---|
| `momentum_vol_scaled@paper` | India | 2026-11-09 (latest stored session) | v1.9-1c842ba9 | ₹20 lakh |
| `quality_momentum@paper` | US | 2026-11-11 | v1.6-4312e8bd | $50,000 |
| `quality_momentum@paper` | India | 2026-11-09 | v1.6-4312e8bd | ₹20 lakh |
| `minervini@paper` | India | 2026-11-09 | v1.67-ebac5f47 (the review read 1.66; 1.67 is another thread's change, uncommitted on 2026-11-12) | ₹20 lakh |
| `momentum_dual_combo@paper` | India | 2026-11-05 (opened earlier) | — | ₹20 lakh |
| `dual_momentum@paper`, `momentum_baseline@paper` | India | 2026-11-05 (opened earlier) | — | ₹20 lakh |
| `ma_trend@paper` (index mode) | US, India | 2026-11-13 (latest stored session 2026-11-11) | v2.4-96972c5b | $50,000; ₹20 lakh |

`ma_trend@paper` (index mode), US and India, was opened 2026-11-13 (latest stored session 2026-11-11),
spec v2.4-96972c5b, once its live selection was built (`ma_trend.current_selection`). Its month-end
decision matched the backtest's at all 142 month-ends since 2015 in both markets. It holds the traded
index price (SPY, the Nifty 500 level) with idle cash at 0%, so it trails the total-return backtest by
dividends and interest; the gate below judges rule fidelity and drawdown, not return.

## Gates

### `momentum_vol_scaled` India
- **Sample:** 12 month-end rebalances and ≥ 150 closed holding periods.
- **Confirms if:**
  - excess over the Smallcap 250 is ≥ +3 points;
  - the top 20 beat their pool by ≥ +0.3% a month, positive in ≥ 7 of 12 months;
  - costs stay ≤ 50 bps a side.
- **Stop early if** the book is 15 points behind its benchmark, or costs exceed 100 bps a side.

### `quality_momentum` US and India
- **Sample:** 12 rebalances.
- **Confirms if:**
  - excess is ≥ +2 points;
  - it beats a paper `filings_covered` control by ≥ 2 points. The control book still has to be
    built: it needs a selection without the quality leg.

### `minervini` India
- **Sample:** ≥ 12 months and ≥ 30 closed trades.
- **Confirms if:**
  - average R ≥ +0.15R and profit factor ≥ 1.2;
  - drawdown no deeper than −15%;
  - fills land within 2× the modelled 32 bps;
  - every paper signal reconciles with a replay of the rules on the same close.
- **Caveats:**
  - Exit ladders are not paper-traded: a position exits whole (`backtesting/paper.py`).
  - A rule change during the test starts a new book. It does not continue this one.

### `momentum_dual_combo` India (open since 2026-11-05)
- **Sample:** 12 rebalances.
- **Confirms if:**
  - excess over the blend is > 0;
  - drawdown is no deeper than 1.2× the benchmark's.

### `ma_trend` index mode, US and India (opened 2026-11-13)
- **Sample:** 24 month-end decisions.
- **Confirms if:**
  - 0 mismatches between the book's decisions and a replay of the rule;
  - drawdown is ≤ 0.6× the index's. Judged only if the index falls ≥ 10% during the test.

## Books to open later (each only after its optimise test passes)

| Book | Opens after | Confirms the edge if |
|---|---|---|
| `darvas` US, SMA50 exit | v1.1 ships (rank 3) | ≥ 60 trades; ≥ +0.15R; profit factor ≥ 1.25; drawdown ≥ −20%; still beats a random near-highs stock |
| `kell_cycle` India | the P1/P3 version ships | ≥ 40 trades and ≥ 12 months; ≥ +0.20R; profit factor ≥ 1.3; drawdown never beyond −25%; beats the momentum paper book; expectancy ≥ 0 without the best 5% |
| `earnings_gaps` US (E1) | it passes optimise | ≥ 40 trades over ≥ 9 months; ≥ +0.15R; profit factor ≥ 1.3 |
| `pead` India (EAR) | it passes optimise | ≥ 60 trades over two results seasons; 60-session excess ≥ +1.0% |
| `momentum_burst` India, 20-day exit | rank 9 and B1/B3 pass | 12 months and ≥ 60 trades; ≥ +0.15R; drawdown ≥ −25%; at least the Nifty 500's return |
| `fno_income` put spreads | F1/F5 pass | ≥ 9 months and ≥ 40 structures at quoted bid/ask; median slippage ≤ 2.5 points a leg; retire if above 3.1 |
