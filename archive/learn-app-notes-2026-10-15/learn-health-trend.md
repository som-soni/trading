# App notes moved from learn-health-trend (rewrite, 2026-10-15)

## Intro (opening paragraph, phrase)

> ... and exactly what this app's own market-regime check does.

## Where this shows in the app (intro section)

**Where this shows in the app.** Every screening run computes a market regime:
a summary of the market's condition (`scripts/swing_screener/core/regime.py`).
It is built from the broad indices in each market's config: SPY, QQQ and IWM
for the US; the Nifty 50 (`^NSEI`), Nifty 500 (`^CRSLDX`) and a Midcap 150
entry for India. The result is printed at the top of the run's report. It shows
VIX, the high-volatility flag (`high_vol`), and the share of stocks above their
20- and 50-day averages. It also shows **downgrade active** when the downgrade
rule fires. The Strategies page shows the rule as each strategy's regime note.
Markets → Breadth opens with the card **"S&P 500 against its 50 DMA?"** (Nifty
50 for India) and charts the index.

## §3 Weinstein's stages — last sentence

> The app's regime check uses a 30-week *exponential* average instead (§7).

## §7 The app's own regime, exactly as coded (whole section)

## 7. The app's own regime, exactly as coded

The regime check lives in `core/regime.py`. For each broad index it records a
set of yes/no readings (`IndexRegime`):

- close above the 50-day;
- close above the 200-day;
- **50-day rising** (above its value 10 sessions ago);
- **weekly close above a rising 30-week EMA**.

Across all the stocks loaded for the run, it computes the share above their 20-
and 50-day averages. It also reads the volatility index: VIX for the US, India
VIX for India. When that index is above the market's threshold, it sets the
high-volatility flag. The flag is `high_vol` and the threshold `vol_threshold`:
**25** for the US and **20** for India, set in `config/us.py` and
`config/india.py`.

Only two of those readings change a decision:

1. **Sizing.** The sizing code (`core/sizing.py`) risks 1% of the account per
   trade (`risk_pct`). When the high-volatility flag is set it risks 0.5%
   instead (`risk_pct_high_vol`). Either way, a position is capped at 25% of the
   account (`max_position_pct`).
2. **The downgrade.** The screening pipeline takes the *first two* broad
   indices: SPY and QQQ, or the Nifty 50 and Nifty 500. When **every one of
   them closes below its 50-day average**, it sets the downgrade flag
   (`downgrade_active`). Strategies then lower their decision:

| Strategy | What the downgrade does |
|---|---|
| Trend pullback, Volume breakout, Donchian channel, Chart patterns | Every label down one tier (HIGH CONFIDENCE → ON TRIGGER → WATCH → AVOID) |
| Minervini SEPA | TRADE tiers become WATCH ("market filter: no new buys"); the watchlist is kept |

The Strategies page's regime note describes the first group. Minervini keeps
the watchlist on purpose: a weak market is exactly when you want to know which
stocks are building setups. The other readings (200-day, slope, 30-week EMA,
breadth) are **reported, not acted on**.

Two caveats. First, if a downgrade index has no data, the rule cannot fire: the
code (`all()`) needs both indices present and both below. Second, the rule
switches on and off quickly. Since 2010, SPY and QQQ were both below their
50-day on about 23% of sessions. That happened in seven or eight spells a year,
with a median length of three sessions. **The downgrade flickers.** Read it as
"be pickier today", not as a change in the market's condition.

**In backtests** the downgrade is not applied (`backtesting/backtest.py` says
so). The Minervini spec backtest has an optional market filter
(`--market-filter`, MKT-01 in `backtesting/spec.py`). It blocks new entries
while the benchmark is below its 200-day, or while its 50-day is below its
200-day. Open positions are untouched. With `--mkt-confirm`, it waits a few
sessions before new buying is allowed again. The momentum baseline's trend
filter is on each stock's own 200-day, not the market's.

## §8.2 Combine trend, breadth and volatility — volatility bullet

> - **Volatility** ([the volatility guide](learn-health-volatility.md)): when VIX or India VIX stays above the threshold, the app halves risk.

## §9 What the evidence says — last bullet (phrase)

> The backtests do not apply the live downgrade.

## §10 Checklist item

> - [ ] Did the screener report say **downgrade active**? Is VIX above the threshold?
