# App notes moved from learn-health-volatility (rewrite, 2026-10-15)

## Intro bullet

> - exactly how this app sizes positions off volatility.

## Where this shows in the app

**Where this shows in the app.** Markets → Breadth: the **"Options: expected
vs actual?"** card, and the *Expected / Actual / Exp ÷ act* columns of **The
last 30 days** (`/api/breadth`, `web/server.py`). Markets → Post-market: the
tone signal *"Volatility index fell (fear easing)"* (`analytics/postmarket.py`).
The screener's market-regime check (`core/regime.py`) flags **high
volatility** when the VIX closes above **25** (India VIX above **20**). Live
sizing then halves the risk per trade from **1%** to **0.5%** (`core/sizing.py`,
`config/us.py`, `config/india.py`).

## §2 The Breadth page's options card (whole section; the general method and numbers are kept in the guide)

## 2. The Breadth page's options card

**"Options: expected vs actual?"** compares two numbers. **Expected** is the
latest VIX (India VIX for India). **Actual** is the index's **realised**
volatility: how much it has really been moving. It is the standard deviation of
the S&P 500's (Nifty 50's) daily returns over the last **20 sessions** (log
returns, a standard way of measuring percentage changes), annualised with √252.

The card's text turns both into a monthly move with the rule above: *"Options
price about ±X% over a month; the index has been moving about ±Y%"*. The gauge
ranks the **ratio** expected ÷ actual against every day since 2015 ("dearer" or
"cheaper" options). The page's own note: *a ratio well above 1 means options
are dear.*

| Since 2015 | US | India |
|---|---|---|
| Median expected (VIX) | 16.6 | 15.3 |
| Median actual (20-day realised) | 12.3 | 12.3 |
| Median ratio | 1.32 | 1.25 |
| Days with ratio below 1 | 15% | 17.5% |

**Options are usually dear.** Since 2010 the VIX was above the S&P 500's
actual volatility over the *following* month on **84%** of days (median gap 4.5
points). India VIX was above on **81%** (3.4 points). That gap is the
**volatility risk premium**: what option sellers are paid for taking on the
risk of a crash.

It is also why the ±1 s.d. band is breached less often than a bell curve
predicts. The S&P 500's one-month move went beyond ±VIX/√12 on only **16%** of
days. The Nifty 50's did on **26%**, more often upward (16% against 10%).

**Reading the ratio:**

- **Well above 1** (options dear, index quiet): either fear is building ahead
  of an event, or the market has calmed after a shock and option prices have
  not yet caught up.
- **Near or below 1** (the index moving more than options price): a sell-off
  or violent rally is under way. This is when prices jump past stops. In the US
  it happened most in 2022 and 2018.

## §8 (sentences)

The app's high-volatility switch (India VIX above 20) would **not have
fired** at any point in it. Traders in small and mid-sized stocks needed
[breadth](learn-health-breadth.md) to see it.

## §9 heading and opening

> ## 9. Other sentiment gauges (not stored in the app)
>
> These are widely followed, but none is in the app's database. Check them at the source.

## §10 How the app uses volatility — exactly as coded (whole section)

## 10. How the app uses volatility — exactly as coded

| Setting | US | India |
|---|---|---|
| Volatility index (`vol_index_symbol`) | `^VIX` | `^INDIAVIX` |
| Threshold (`vol_threshold`) | 25 | 20 |
| Risk per trade (`risk_pct`) | 1% | 1% |
| Risk per trade, high volatility (`risk_pct_high_vol`) | 0.5% | 0.5% |
| Max position (`max_position_pct`) | 25% of the account | 25% |
| Days above the threshold since 2010 | 13% | 26% |

The mechanics:

1. The daily screener (`screening/pipeline.py`) reads the **last close** of the
   volatility index. The regime function (`compute_market_regime`) sets the
   high-volatility flag (`high_vol`) when that close is **strictly above** the
   threshold.
2. The sizing function (`size_position` in `core/sizing.py`) then uses the
   high-volatility risk (`risk_pct_high_vol`). The risk amount is account ×
   0.5% instead of 1%. Shares = floor(risk ÷ (entry − stop)): the risk amount
   divided by the loss per share, rounded down. The position's total value is
   still capped at the max-position limit.
3. That is all it changes. **The high-volatility flag does not change any
   decision tier.** The regime *downgrade* depends only on the broad indices
   being below their 50-day. And **backtests always size at the normal risk**:
   the backtester calls `size_position` with `vix_above_threshold=False`.

India's threshold has been exceeded on twice the share of days, so India
sizing halves more often. The Trend pullback strategy's parameter table
(`trend_pullback`) on the Strategies page shows the setting as *"Risk per
trade, high volatility"*.

## §11 opening paragraph

The app's sizing already **adjusts for each stock's volatility**. The stop sits
under a structural level: a real support point on the chart, such as a recent
low. So a volatile stock with a wide stop gets fewer shares for the same 1%
risk. The screener also requires ATR(14) above **1.5%** of price (both
markets). On top of that:

## §12 table rows

> | 15–25, normal | Normal; watch the options card for a ratio below 1 |
> | Above the threshold (25 US, 20 India) | Risk per trade halves in the app; also cut position count |

## §14 Checklist items

> - [ ] VIX / India VIX: level, and above or below the app's threshold (25 / 20)?
> - [ ] Options card: expected ÷ actual above 1 (dear) or below 1 (moves outrunning options)?
