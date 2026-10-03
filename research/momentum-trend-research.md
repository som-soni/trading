# Momentum & Trend Research Log

A living record of what has been tested, what the numbers were, and what
survived scrutiny. Append to the ledger as new strategies are tried; the
methodology and bias sections apply to everything in it.

**Last updated:** 2026-10-03 · **Window used throughout:** 2013-01-01 → 2026-10-01 (13.75y)

---

## 1. Where things stand

Three conclusions are well supported, and one earlier conclusion was wrong and
has been corrected.

1. **The hand-built `trend_pullback` strategy has no edge in either market.**
   US −0.87% CAGR, India +0.57%, against indices returning 12.79% and 11.68%.
2. **Simple cross-sectional momentum beats the index in India, not in the US.**
   India +6.23% excess across 8 of 8 parameter configurations; US 1 of 9 on
   return, 0 of 9 on Sharpe.
3. **India's momentum premium lives in small/mid caps and disappears in large
   caps.** Monotonic decay from +14.2% excess at a ₹1cr turnover floor to
   −9.3% at ₹500cr.
4. **Corrected:** an earlier conclusion that "stock selection adds no value,
   buy the index" was drawn from US data alone and over-generalised. India
   contradicts it.

The practical consequence: the gates are the problem, not the premise — but
only in India. In the US the premise fails too.

---

## 2. Results ledger

Every row is a completed backtest. **Append new strategies here.**
`excess` = strategy CAGR − benchmark CAGR, same window and currency.

### India (benchmark: Nifty 500 `^CRSLDX` — CAGR 11.68%, maxDD −38.3%, Sharpe 0.78)

| strategy | config | CAGR | maxDD | Sharpe | Calmar | excess | trades |
|---|---|---|---|---|---|---|---|
| momentum baseline | top 50, ₹1cr floor, 25bps | **29.01%** | −55.3% | **1.14** | **0.52** | **+17.33** | 2674 |
| momentum baseline | top 20, ₹1cr floor, 25bps | 25.92% | −63.0% | 1.00 | 0.41 | +14.24 | 1195 |
| momentum baseline | top 20, ₹10cr floor, 25bps | 24.55% | −48.7% | 0.99 | 0.50 | +12.86 | 1271 |
| momentum baseline | top 20, ₹25cr floor, 25bps | 24.52% | −49.0% | 1.03 | 0.50 | +12.84 | 1199 |
| momentum baseline | top 50, ₹10cr floor, 25bps | 22.40% | −44.0% | 1.00 | 0.51 | +10.72 | 2745 |
| momentum baseline | top 50, ₹25cr floor, 25bps | 20.23% | −43.7% | 0.96 | 0.46 | +8.55 | 2531 |
| momentum baseline | top 20, ₹50cr floor, 25bps | 17.91% | −49.9% | 0.81 | 0.36 | +6.23 | 1159 |
| momentum baseline | top 50, ₹50cr, quarterly, 25bps | 17.30% | −39.9% | 0.87 | 0.43 | +5.62 | 1188 |
| momentum baseline | top 50, ₹50cr floor, 25bps | 16.90% | −42.5% | 0.84 | 0.40 | +5.22 | 2370 |
| momentum baseline | top 20, ₹100cr floor, 25bps | 12.82% | −45.4% | 0.64 | 0.28 | +1.14 | 1151 |
| momentum baseline | top 50, ₹100cr floor, 25bps | 11.15% | −49.4% | 0.63 | 0.23 | −0.53 | 2164 |
| momentum baseline | top 20, ₹250cr floor, 25bps | 9.10% | −49.6% | 0.51 | 0.18 | −2.59 | 890 |
| momentum baseline | top 20, ₹500cr floor, 25bps | 2.59% | −46.9% | 0.23 | 0.06 | −9.10 | 567 |
| **trend_pullback** | 500-symbol sample, bracket exits | **0.57%** | −18.5% | 0.12 | 0.03 | **−11.11** | 183 |

### US (benchmark: SPY — CAGR 12.79%, maxDD −34.1%, Sharpe 0.80)

| strategy | config | CAGR | maxDD | Sharpe | Calmar | excess | trades |
|---|---|---|---|---|---|---|---|
| momentum baseline | top 50, no 200DMA, 5bps | **15.56%** | −45.7% | 0.62 | 0.34 | **+2.77** | 2590 |
| momentum baseline | top 50, 5bps | 9.33% | −50.3% | 0.45 | 0.19 | −3.46 | 2811 |
| momentum baseline | top 100, 5bps | 8.17% | −37.8% | 0.46 | 0.22 | −4.62 | 4900 |
| momentum baseline | top 20, 5bps | 2.92% | −62.7% | 0.27 | 0.05 | −9.87 | 1240 |
| momentum baseline | top 10, 5bps | −4.85% | −79.7% | 0.11 | −0.06 | −17.64 | 681 |
| momentum baseline | top 20, 3mo lookback | −5.86% | −89.5% | 0.02 | −0.07 | −18.65 | 2013 |
| **trend_pullback** | 500-symbol sample, bracket exits | **−0.87%** | −40.6% | −0.02 | −0.02 | **−13.67** | 301 |

### Index-level trend overlays (no stock selection — survivorship-bias free)

Longest clean test available: SPY since 1993, QQQ since 1999.

| strategy | window | CAGR | maxDD | Sharpe | Calmar |
|---|---|---|---|---|---|
| QQQ buy & hold | 27.7y | **10.78%** | −81.1% | 0.56 | 0.13 |
| **QQQ + 10mo SMA → Treasuries** | 27.7y | 10.04% | **−36.5%** | **0.74** | **0.27** |
| QQQ + 10mo SMA → cash | 27.7y | 8.96% | −36.5% | 0.69 | 0.25 |
| SPY buy & hold | 33.7y | **10.79%** | −50.8% | 0.77 | 0.21 |
| SPY + 10mo SMA → cash | 33.7y | 9.24% | **−23.0%** | **0.89** | **0.40** |
| 60/40 static | 24y | 8.31% | −29.5% | 0.94 | 0.28 |

Sub-period behaviour (SPY, 10-month rule) is the whole story:

| period | buy & hold | timed |
|---|---|---|
| 1993–99 bull | **+21.09%** | +15.57% |
| 2000–09 dot-com + GFC | −1.01%, DD −50.8% | **+6.90%, DD −11.0%** |
| 2010–26 bull | **+14.15%** | +8.09% |

Trend following is insurance: it costs in bull markets and pays in bears.

---

## 3. What each experiment established

### 3.1 The gate stack subtracts value

`trend_pullback` applies 14 hard gates, 9 watch flags and 3 setup gates.
Only **5.4% of symbol-days pass**. Five gates cause 83% of rejections
(W1 21.7%, T3 21.3%, D5 18.0%, D3 11.1%, T1 11.0%); six cause under 6%
combined, with D7 firing 50 times in 290,000 rejections.

Consequences measured in India: **56.4% exposure**, an average of **1.2
positions held**, and only 399 signals in 13.75 years. Per-trade expectancy is
actually positive (profit factor 1.03) — there simply aren't enough trades to
compound.

### 3.2 The confidence tiers carry no information

Across 484 trades, `TRADE - HIGH CONFIDENCE` performed no better than the
`TRADE ON TRIGGER` tier it downgrades (25.1% vs 29.7% win rate; both t<0.4
after correcting for censoring and regime). The X1–X9 machinery is not
discriminating.

Concrete cost: Micron's 2025-10-23 signal was correct — entry 214.97, target
292.90, and it reached target on 2025-12-29 for **+3.32R**. It was rejected
because it graded TRADE ON TRIGGER.

### 3.3 Exits are not the lever

Eight exit policies on the identical 879-signal set, 13.74 years:

| variant | CAGR | maxDD | Sharpe | avgR |
|---|---|---|---|---|
| donchian-50d-noTarget | **+1.06%** | −38.8% | 0.15 | **+0.095** |
| bracket-withTarget *(current)* | −0.87% | −40.6% | −0.02 | −0.044 |
| trail_atr-5ATR-noTarget | −1.60% | −46.5% | −0.07 | −0.073 |
| ma-sma50-noTarget | −1.98% | −38.2% | −0.11 | −0.088 |
| donchian-20d-noTarget | −2.06% | −40.0% | −0.11 | −0.080 |
| trail_atr-3ATR-withTarget | −3.08% | −42.1% | −0.32 | −0.141 |
| ma-sma20-noTarget | −4.05% | −46.5% | −0.47 | −0.174 |
| trail_atr-3ATR-noTarget | −4.81% | −51.9% | −0.50 | −0.221 |

**Seven of eight are worse than the fixed bracket.** Tighter trailing is
monotonically worse. Note that higher win rate went with *worse* returns —
`trail_atr-3ATR` raised win rate to 29.1% and cut CAGR to −3.08%, while the
best variant had the lowest win rate (20.6%). Win rate is not an objective.

### 3.4 Why a 20× move produced nothing

Micron ran **20.4×** and SanDisk **84.4×** from the April 2025 low. The
strategy made nothing on either:

- **Target caps the win at 7.5% of the move.** MU's correct signal would have
  exited at +36.3% on 2025-12-29, **276 days before** the +483.8% peak.
- **Parabolic moves don't offer the required pullbacks.** 306 bars during MU's
  run produced only 20 with gates-plus-setup (6.5%).
- **Watch flags punish what defines a generational run.** 18 of MU's 20 setup
  bars were capped at TRADE_ON_TRIGGER; X1 flags "2.5 ATR above SMA20", and a
  20× stock lives there permanently.
- **SNDK was unsizeable** — 14 HIGH CONFIDENCE bars, all with `shares = 0` at
  ₹1,600–2,400/share on a ₹10 lakh account.

### 3.5 Universe restriction (answered)

Restricting to larger/more liquid names makes India **worse**, monotonically.
See the ledger. The `liquidity_rank_top` parameter was found to be inert — the
turnover floor already cuts the tape, so rank cutoffs above ~250 change
nothing. The turnover floor is the real control.

---

## 4. Methodology

Decisions that materially affect results, and why.

- **Point-in-time candidate selection.** A symbol qualifies if it passed the
  screen on ≥1 bar *in the window*, not if it passes today. Selecting on
  today's row discarded 2,167 of 3,290 US candidates.
- **Portfolio-level simulation.** One capital pool, a position cap, costs on
  both sides, sizing compounding off current equity. The old per-symbol mode
  implied up to 51 simultaneous positions needing ~13× the stated capital; its
  P&L was never achievable.
- **Pessimistic fills.** A bar gapping past the stop fills at the open, not the
  stop (16.4% of stop exits gap through, averaging −1.50R not −1.00R). A
  buy-stop gapping above its trigger fills at the open. An order gapping past
  its target is cancelled.
- **R measured against the stop at entry**, never a trailed stop.
- **Right-censoring.** Losers resolve in ~14 days, winners in ~35. Trades
  entered near the window's end are biased toward losses; summary statistics
  must exclude them or say so.
- **Total returns** (dividends reinvested) for index comparisons; **price
  only** for the stock-level backtests, which understates both sides.
- **Costs:** 5bps/side US, 25bps/side India (STT + stamp + exchange + GST).

---

## 5. Known biases — read before trusting any number

1. **Survivorship bias (largest unfixed).** The universe is today's listed
   names. Every company delisted, acquired or bankrupted during the window is
   absent, which biases returns upward — and *worse at the small-cap end*,
   which is exactly where India's premium appears. A quarter of the India
   universe still shows only 38 bars. Fixing it needs point-in-time
   constituent data (CMIE Prowess, Refinitiv, or NSE filings rebuilt by hand).
2. **Data-snooping.** The regime filter, cost assumptions and several splits
   were chosen after seeing results. In-sample numbers are optimistic.
3. **No fundamentals.** yfinance gives 4–5 annual periods and a *present-day*
   ratio snapshot. Ranking 2015 stocks by a 2026 P/B is severe lookahead bias,
   so no fundamental overlay has been tested.
4. **Costs are flat.** 25bps everywhere is too generous for ₹1cr-turnover
   names at 4× annual rotation; real impact could be 100–300bps/side.
5. **Taxes are not modelled.** Turnover of 4.5×/yr at Indian STCG rates is a
   material drag that none of these numbers reflect.
6. **One regime.** 2013–2026 contains no prolonged bear market. The index-level
   overlays (§2) are the only tests covering 2000–02 and 2008.

---

## 6. Open questions / experiment queue

| # | experiment | needs | why |
|---|---|---|---|
| 1 | Volatility-scaled momentum (Barroso–Santa-Clara) | nothing new | Directly targets the −49.9% drawdown; the most cited momentum fix |
| 2 | Volatility-weighted positions + portfolio vol target | nothing new | Standard in managed futures; usually lifts Sharpe more than it costs |
| 3 | Index-level trend overlay on the India momentum book | nothing new | Cut SPY's drawdown from −50.8% to −23.0%; untested on Nifty |
| 4 | Residual momentum (strip market beta before ranking) | nothing new | Reported Sharpe gains; we have `^CRSLDX` to regress against |
| 5 | Path quality / % positive days (Alpha Architect) | nothing new | Prefers smooth momentum over gap-driven |
| 6 | Gate ablation — drop each gate, measure | one full re-run | `hard_gates` JSONB now captures the full vector |
| 7 | Value + momentum blend (Asness et al.) | **point-in-time fundamentals** | Most robust pairing in the literature; blocked on data |
| 8 | Full-universe India run (not a 500 sample) | ~9h compute | Firms up the headline numbers |

---

## 7. Reproducing anything here

```bash
cd scripts

# long history first — nothing is trustworthy on 2 years of data
PYTHONPATH=. python3 -m swing_screener.marketdata.backfill --market india --years 16

# the momentum baseline
PYTHONPATH=. python3 -m swing_screener.backtesting.baseline \
    --market india --start 2013-01-01 --top-n 50 --rebalance QE \
    --cost-bps 25 --min-turnover 100000000

# the gated strategy, portfolio-level
PYTHONPATH=. python3 -m swing_screener.backtesting.backtest \
    --market india --start 2013-01-01 --sample 500

# controlled A/B over one signal set
PYTHONPATH=. python3 -m swing_screener.backtesting.experiments \
    --market india --start 2013-01-01 --sample 500 --exits

# re-render any finished run as markdown + charts
PYTHONPATH=. python3 -m swing_screener.backtesting.report --list
```

Reports land in `reports/<market>/<strategy>/<run>/` — `report.md`,
`trades.csv`, `equity.csv`, `figures/`.

---

## 8. Changelog

| date | change |
|---|---|
| 2026-10-03 | Universe/turnover sweep: premium is small/mid-cap, decays monotonically to −9.3% excess at ₹500cr |
| 2026-10-03 | Restructured into topic sub-packages; reports moved to repo root, one directory per run |
| 2026-10-02 | India results: momentum +6.23% excess (8/8 configs); gated strategy +0.57% |
| 2026-10-02 | Index-level trend overlays tested on 33y of SPY and 27y of QQQ |
| 2026-10-02 | 16-year backfill both markets (US 14.6M bars, India 6.2M) |
| 2026-10-02 | Portfolio simulator, metrics and markdown reporting added |
| 2026-10-02 | Fixed: point-in-time candidate selection, gap-through fills, own-H overhead veto, ATR-relative risk caps |
