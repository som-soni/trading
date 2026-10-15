# Using the app — how it computes its numbers

**In short**

- Every number on a page comes from stored daily bars, filings or dates, computed by the code named
  here. The thresholds are module constants, so this guide names the constant beside its value.
- Two market readings change a live decision: the **downgrade** (both main indices below their 50-day)
  lowers decision labels, and **high volatility** (VIX above 25, India VIX above 20) halves the risk
  per trade. Everything else is reported, not acted on.
- RS ratings for stocks and for groups use the same weights: 40% on the last three months, 20% each on
  6, 9 and 12 months, ranked 1–99.
- Backtests do not apply the downgrade, high-volatility sizing, the sector cap or the earnings gates.
- What each page shows, and how to read it, is in [the pages guide](app-guide-pages.md). Paths are
  relative to `scripts/swing_screener/` unless they start with `fundamentals/` or `jobs/`.

This is the reference for checking a number. If the code changes, the code wins: each Strategies →
Rules tab and each Screens rule list is generated from the live constants. The ideas behind the numbers
are in the linked [Learn](learn-start-here.md) guides.

---

## 1. Data sources and the universe

| Data | Source | Where |
|---|---|---|
| Daily prices | Yahoo (yfinance), unadjusted for dividends (`auto_adjust=False`); splits as the source returns them, with the weekly `splits` job repairing gaps the incremental refresh missed | `providers/yfinance_provider.py`, `marketdata/splits.py` |
| Indices, VIX, India VIX, USD/INR | Yahoo, stored in `index_series` | `analytics/breadth.py` (`INDEXES`, `VOL_INDEX`), `marketdata/index_data.py` |
| Macro strip | Yahoo, raw closes | `marketdata/macro.py` (`SERIES`, `STRIP`) |
| Quarterly and annual financials | US: SEC XBRL (`quarterly_source="sec_edgar"`); India: NSE results filings (`"nse"`); Yahoo as fallback | `marketdata/financials.py` |
| Earnings dates | Yahoo's calendar per ticker, refreshed at most weekly (`CACHE_REFRESH_DAYS` = 7); `data/earnings_<market>.csv` overrides it | `marketdata/earnings.py` |
| News and events | Google News RSS; SEC 8-K filings (US); NSE announcements, corporate actions and board meetings (India); Yahoo for dividends, splits and ratings | `marketdata/news.py` |
| Sector and industry | Yahoo's classification, refreshed monthly; sub-industries are this app's own splits (`data/sub_industries.csv` plus rules) | `marketdata/industries.py`, `marketdata/subindustries.py` |

The universe is a fixed list of today's listed stocks (`data/universe_<market>.csv`). Companies delisted
in the past are missing, so every historical number carries survivorship bias.

**Floors.** Different parts of the app use different liquidity floors, each for its own job:

| Used by | US | India | Constant |
|---|---|---|---|
| Screens: the *Tradable* field | Price ≥ $10; 20-day average traded value ≥ $10M; 260 bars; a valid ATR | No price floor; ≥ ₹50 crore a day | `config/us.py`, `config/india.py` (`min_price`, `min_dollar_volume`); `screens/base.py` (`MIN_BARS`) |
| Strategies' pre-filter | Traded value only (the price floor is left out, because split-adjusted history would drop early winners) | Same, plus market cap ≥ ₹5,000 crore in the live run (unknown caps pass) | `strategies/base.py` `tradable_point_in_time`; `INDIA_MIN_MARKET_CAP_CR` |
| Breadth | The 1,000 most-traded common stocks by 20-day turnover; closed-end funds flagged by `classify` dropped | Same; symbols not classified as equity (`symbol_kind`) dropped | `BREADTH_N`, `eligible` |
| Sectors page | ≥ $2M a day at $3+ | ≥ ₹2 crore a day at ₹10+ | `analytics/sectors.py` `MIN_VALUE`, `MIN_PRICE` |
| Post-market lists, Movers | ≥ $10M a day at $5+ | ≥ ₹10 crore a day at ₹20+ | `analytics/postmarket.py` `LIQUID_VALUE`, `LIQUID_PRICE`; `web/server.py` `MOVER_LIQUID` |

## 2. Freshness: when is a number current?

A market's session counts as due once its close plus a data delay has passed: **17:30 New York** and
**17:00 Kolkata**, on weekdays (`marketdata/freshness.py`, `MARKET_CLOSE`). Holidays are not modelled.

On the Status page a dataset with the expected session is **ok**, one trading day behind is **warn** (a
holiday, or the update has not run yet), and two or more behind is **stale**.

Reference data is judged by age instead (`web/status.py`, `AGE_LIMITS`, days ok / warn): universe 8 / 15,
industries 35 / 60, names 60 / 120, quality scores 8 / 32, earnings dates 8 / 15.

The **readiness** job (`jobs/registry.py`) ends each open routine. It fails when the last session's
prices or any strategy's setups are missing. Today's *Data health* banner reads the same freshness items
(prices, breadth, screening), the job worker and failed runs. The screens' snapshot reports itself stale
when newer prices exist or when one of its present-only inputs (fundamentals, quality, peer-group RS,
industries, earnings dates) changed after it was built (`screens/snapshot.py`, `stale_inputs`).

## 3. The market regime and the downgrade

`core/regime.py` (`compute_market_regime`) runs in every screening run. Its inputs are each market's
broad indices (`broad_index_symbols`): SPY, QQQ and IWM for the US; Nifty 50 (`^NSEI`), Nifty 500
(`^CRSLDX`) and Nifty Midcap 150 for India. For each index it records (`IndexRegime`):

| Reading | Definition |
|---|---|
| `above_sma50`, `above_sma200` | Close above the 50- / 200-day simple average |
| `sma50_rising` | The 50-day above its value 10 sessions ago |
| `weekly_above_rising_30w_ema` | Weekly close above the 30-week EMA, and that EMA above last week's value |

It also records the share of the run's stocks above their 20- and 50-day averages, and the volatility
index's last close.

**Only two readings change a decision.**

1. **High volatility.** `high_vol` is set when the volatility index closes **strictly above**
   `vol_threshold`: **25** for the US (`^VIX`), **20** for India (`^INDIAVIX`). It halves the risk per
   trade (§4). It does not change any label.
2. **The downgrade.** The pipeline takes the *first two* broad indices — SPY and QQQ, or Nifty 50 and
   Nifty 500 (`screening/pipeline.py`). When **every one of them closes below its 50-day**,
   `downgrade_active` is set. If either index has no data, the rule cannot fire.

| Strategy | What the downgrade does |
|---|---|
| Trend pullback, Volume breakout, Donchian channel, Chart patterns | Every label down one tier (`DOWNGRADE_MAP` in `strategies/base.py`): HIGH CONFIDENCE → ON TRIGGER → WATCH → AVOID |
| Minervini SEPA | TRADE tiers become WATCH, reason "market filter: no new buys"; WATCH and AVOID are untouched |

The 200-day, the slope, the 30-week EMA and the breadth shares are printed in the run's report but drive
nothing. The downgrade switches on and off often; read it as "be pickier today". See
[the market's trend](learn-health-trend.md) and [regime filters](learn-strat-regime-filters.md).

## 4. Position sizing and the caps

`size_position` in `core/sizing.py`, with the account settings of `config/us.py` and `config/india.py`:

| Setting | US | India |
|---|---|---|
| Configured account (`account_size`) | $50,000 | ₹20,00,000 |
| Risk per trade (`risk_pct`) | 1% | 1% |
| Risk per trade, high volatility (`risk_pct_high_vol`) | 0.5% | 0.5% |
| Largest position (`max_position_pct`) | 25% of the account | 25% |
| Tradeable picks per sector per run (`sector_limit_per_sector`) | 3 | 3 |
| Open positions in a backtest (`max_open_positions`) | 10 | 10 |
| Backtest slippage per side (`slippage_bps`) | 5 bp | 10 bp |

The steps:

1. Risk amount = account × `risk_pct` (or `risk_pct_high_vol` when `high_vol` is set).
2. Shares = floor(risk amount ÷ (entry − stop)).
3. If shares × entry exceeds 25% of the account, shares = floor(25% of the account ÷ entry). The row then
   reports the smaller actual amount at risk (`usd_at_risk`).
4. Under one share, the row is flagged too large; the strategies grade it WATCH – WAIT, "too large for
   account".

At 1% risk and a 25% cap, the cap binds whenever the stop is less than 4% below the entry.

**The sector cap** (`screening/portfolio.py`, `apply_sector_filter`) keeps at most three tradeable names per
sector in a run. They are ranked by setup quality, then target R, then RS vs index; the rest become
**WATCH - SECTOR LIMIT**. It applies to a day's candidates, not to what you hold.

The live screener sizes off the configured account; a backtest sizes off its current equity and always
at normal risk (`vix_above_threshold=False`). See [position sizing](learn-risk-sizing.md) and
[portfolio risk](learn-risk-portfolio.md).

## 5. Breadth

`analytics/breadth.py` writes one row per market per day to `breadth_daily`, from 2015
(`HISTORY_START`), for the `BREADTH_N` = 1,000 most-traded common stocks that day.

| Field | Definition |
|---|---|
| `adv`, `dec` | Close above / below the previous close |
| `up4`, `dn4` | Up / down at least 4% on the day (`BIG_MOVE`) |
| `highs`, `lows` | Today's high (low) is the extreme of the last 252 bars; needs 200 bars (`MIN_HISTORY_BARS`) |
| `above5`, `above50` | Close above its 5- / 50-day simple average |
| `up25m`, `dn25m`, `up50m`, `dn50m` | Up / down 25% or 50% over the last 21 bars (`MONTH_BARS`) |

The Breadth page (`/api/breadth` in `web/server.py`) adds:

- **Ranks.** Each card's gauge is the percentile of today's value among every day since 2015. The
  highs/lows and rising/falling cards rank the 10-day average of highs − lows and of advancers −
  decliners. The 5 & 50 DMA card's gauge ranks the 50-day share.
- **Index card.** The first index of `INDEXES` (S&P 500 `^GSPC`; Nifty 50 `^NSEI`) against its 50-day.
- **Options card.** Expected = the VIX (India VIX). Actual = the standard deviation of the index's daily
  log returns over 20 sessions × √252 × 100. The card divides both by √12 for a one-month move and ranks
  expected ÷ actual.
- **Events.** The 50-day share crossing 30% (washout) or rising above 70%; the 10-day highs − lows or
  advancers − decliners at its weakest or strongest in over 90 days; the index crossing its 50-day.
- **Shading** in *The last 30 days*: a reading in its top or bottom fifth since 2015 (20th / 80th
  percentile).

No page counts index distribution days or follow-through days, and the regime check reads no index
volume. See [breadth](learn-health-breadth.md), [distribution days](learn-health-distribution.md) and
[volatility](learn-health-volatility.md).

## 6. Post-market tone and the macro read

**Tone** (`analytics/postmarket.py`, `TONE_RULES`): six yes/no signals on the benchmark (S&P 500, Nifty
50) and that day's breadth row — above the 50-day, above the 200-day, `adv` > `dec`, `highs` > `lows`,
`above50` ≥ half of the stocks counted, and the volatility index down on the day. The count names the day
(`TONE`): 5–6 Strong, 4 Positive, 2–3 Mixed, 1 Weak, 0 Negative.

Other post-market numbers: unusual volume is volume ≥ `UNUSUAL_RVOL` = 2.5× the 50-day average with a
move of at least `UNUSUAL_MOVE` = 2%; group day returns clip each member at ±50% (`DAILY_CLIP`) and need
`MIN_MEMBERS` = 3; "earnings soon" is within `EARNINGS_DAYS` = 10 **calendar** days.

**Macro read** on Today (`marketdata/macro.py`, `SIGNALS`), seven signals per market:

| Signal | Headwind when | Constant |
|---|---|---|
| Rates | US 10-year up 25 bp or more in a month | `RATE_JUMP_BP` |
| Curve (US) | 10-year below the 5-year | — |
| Dollar | Dollar index up 2% or more in a month | `DOLLAR_SURGE_PCT` |
| Oil | WTI (US) / Brent (India) up 15% or more in a month | `OIL_SPIKE_PCT` |
| Rupee (India) | USD/INR up 1.5% or more in a month | `INR_WEAK_PCT` |
| Credit | HYG below its 50-day average | `CREDIT_SMA` |
| Growth | Gold outpacing copper over three months | — |
| Fear | VIX ≥ 20 (India VIX ≥ 18) | `VIX_CALM`, `INDIA_VIX_CALM` |

The supportive count names the backdrop (`MACRO_TONE`): 6+ Supportive, 5 Mostly supportive, 3–4 Mixed,
2 Cautious, 0–1 Hostile, scaled when a series is missing. The fear levels here (20 / 18) are not the
sizing thresholds (25 / 20). See the macro guides: [rates](learn-macro-rates.md),
[yield curve](learn-macro-yield-curve.md), [currencies](learn-macro-currencies.md),
[commodities](learn-macro-commodities.md), [credit](learn-macro-liquidity-credit.md).

## 7. Group and sector RS, and the rotation quadrants

`analytics/sectors.py`, three levels: sector (11), industry group (Yahoo, about 145) and sub-industry.

| Item | Definition | Constant |
|---|---|---|
| Members | Common stocks above the Sectors floor (§1); a group needs 3+ | `MIN_MEMBERS` |
| Group index | Equal-weight: the members' average daily return, compounded; each day's member return clipped at ±50% | `DAILY_CLIP` |
| Yardstick | The typical stock: the equal-weight average of every stock analysed (the S&P 500 / Nifty 500 is shown for reference) | `BENCH_INDEX` |
| RS score | Group return minus the typical stock's over 63, 126, 189 and 252 bars, weighted 40 / 20 / 20 / 20 | `RS_WEIGHTS` |
| RS rating | The score ranked across groups at that level, 1–99 | `_rank` |
| Δ 1M | Rating now minus the rating 21 bars ago | `RS_CHANGE_BARS` |
| RS-Ratio | 100 × the group's weekly RS line ÷ its 10-week average | `RRG_WEEKS` |
| RS-Momentum | 100 × RS-Ratio ÷ its value 4 weeks ago | `RRG_MOM_WEEKS` |
| Tail | The last 8 weekly points | `RRG_TAIL` |

"Weekly" means every fifth session counting back from the latest. The quadrant (`quadrant`):

| Quadrant | RS-Ratio | RS-Momentum |
|---|---|---|
| Leading | ≥ 100 | ≥ 100 |
| Weakening | ≥ 100 | < 100 |
| Lagging | < 100 | < 100 |
| Improving | < 100 | ≥ 100 |

Breadth inside a group: % of members above the 50- and 200-day, and members at a new 52-week *closing* high
or low. Ratings for past dates (the screen study's month-ends) are rebuilt into `group_rs_history`
(`analytics/group_history.py`) from prices up to each date, with today's classification.

A stock's **peer group** (`screens/snapshot.py`, `add_peers`) is its sub-industry when the industry group
is split and the sub-industry has at least `PEER_MIN` = 3 tradable stocks and a rating; otherwise its
industry group. See [sectors and groups](learn-sectors-groups.md).

## 8. The stock RS rank, and the other RS numbers

**RS rank** (`screens/snapshot.py`: `_rs_raw`, ranked in `_finish`). For every stock with 252 bars:

**score = 2 × r63 + r126 + r189 + r252**, where rN is the return over N sessions.

The scores of every stock in the snapshot are ranked into 1–99. The return is raw, not minus the index;
subtracting one index return from every stock would not change the order. An RS rank of 80 beat about 80%
of the stocks ranked that day.

| RS number | Definition | Where |
|---|---|---|
| RS rank 70 | Stage 2 screen, C8 (`RS_MIN_RANK`) | `screens/criteria.py` |
| 12-1 momentum ≥ 10% | C8's stand-in when one stock is checked alone or in a backtest (`RS_MIN_MOM` = 0.10) | `screens/criteria.py` |
| Leaders preset | Stock RS 70+ (`LEADER_MIN_RS`) in a peer group rated 80+ (`LEADER_GROUP_RS`) | `screens/definitions.py` |
| RS vs index | The stock's 3-month return (63 bars) minus SPY's (US) or the Nifty 500's (India), in points | `screening/pipeline.py` |
| RS vs sector | The same against the stock's sector index or ETF (`sector_index_map`) | `screening/pipeline.py` |
| Chart study *Relative Strength vs index* | Close ÷ SPY (US) or Nifty 50 (India), restated to 100 at the first bar, with a 50-bar average | `web/static/studies.js` |
| Backtest RS (`rs_ratings`) | Ranked only among stocks above a floor that day, so close to but not the same as the screen's | `backtesting/spec.py` |

**12-1 momentum** (`mom_12_1`) is the close 21 bars ago ÷ the close 252 bars ago − 1: a year's return
that skips the latest month. See [relative strength](learn-price-rs.md).

## 9. The screens' criteria

All four screens apply the *Tradable* floor first (§1). Moving averages are simple averages of daily
closes; the 52-week high and low are the highest high and lowest low of 252 bars (`high_252`, `low_252`).

**Stage 2 — Trend Template** (`stage2`):

| Code | Rule | Constant |
|---|---|---|
| C1 · C2 · C3 | Close above the 50-, 150- and 200-day | — |
| C4 | 50-day > 150-day > 200-day | — |
| C5 | 200-day higher than 21 sessions ago | `SMA200_RISING_BARS` = 21 |
| C6 | Close at least 30% above the 52-week low | `MIN_PCT_ABOVE_52W_LOW` = 30 |
| C7 | Close within 25% of the 52-week high | `MAX_PCT_BELOW_52W_HIGH` = 25 |
| C8 | RS rank 70+ (whole market); 12-1 momentum ≥ 0.10 (single stock) | `RS_MIN_RANK`, `RS_MIN_MOM` |

**Established uptrend** (`uptrend`):

| Code | Rule |
|---|---|
| U1 | Weekly close above a rising 30-week EMA |
| U2 | Weekly 20-week average above the 50-week |
| U3 | 50-day above the 200-day, and no breakdown: not more than 2 ATR below the 50-day, and not 5 closes in a row under it |
| U4 | Neither the 50-day nor the 200-day is falling |
| U5 | The last two confirmed swing lows of the last ~50 sessions are rising |
| U6 | Close 21 bars ago above the close 252 bars ago |
| U7 | Close within 25% of the 52-week high (`UPTREND_MAX_PCT_BELOW_52W_HIGH`) |
| U8 | Not both a negative 63-bar return and a flat or falling 50-day |

**Near highs, rising 200-day** (`near_highs`): H1 close above the 200-day; H2 the 200-day not falling; H3
within 15% of the 52-week high (`NEAR_HIGHS_MAX_PCT_BELOW_52W_HIGH`). **Above the 200-day**
(`above_200`): A1 close above the 200-day.

**Rising, flat, falling** (`core/indicators.py`, `slope_state`): *rising* is above its value N bars ago;
*falling* is more than a set % below it; anything else is *flat*.

| Average | N bars | Falling when more than | Constants |
|---|---|---|---|
| 50-day | 10 | 1% below | `SMA50_SLOPE_BARS`, `SMA50_FALLING_PCT` |
| 200-day | 20 | 0.5% below | `SMA200_SLOPE_BARS`, `SMA200_FALLING_PCT` |

The built-in screens' conditions (`screens/definitions.py`) are generated from these constants and
proven equal to the coded criteria by `tests.test_screen_definitions`. See
[stages](learn-price-stages.md) and [screens versus strategies](app-guide-screens-strategies.md).

## 10. Indicators

**Screening code** (`core/indicators.py`, `enrich_daily`), computed for every stock each run:

| Column | Definition |
|---|---|
| `sma20/50/100/150/200` | Simple average of closes; empty until N bars exist |
| `ema20` | Exponential average, α = 2 ÷ (N + 1), started from the first close |
| `rsi14` | Wilder's RSI: average gain ÷ average loss, each smoothed with α = 1/14 |
| `rsi_ma` | 14-day simple average of RSI14 (stored; no rule reads it) |
| `atr14` | True range (the largest of high − low, high − previous close, low − previous close), Wilder-smoothed over 14 |
| `atr_pct` | ATR14 ÷ close × 100 |
| `adx14` | Wilder's ADX from +DM / −DM and the true range, all smoothed over 14 |
| `vol_sma50` | 50-day average volume, including today |
| `dollar_vol_sma20` | 20-day average of close × volume |
| `high_252`, `low_252` | Highest high / lowest low of 252 bars |
| `mom_12_1` | Close 21 bars ago ÷ close 252 bars ago − 1 |

Weekly bars add a 20- and 50-week SMA and a 30-week EMA (`enrich_weekly`). No screening code computes
MACD or Bollinger Bands.

**Strategy pre-filters** read these columns: trend pullback needs the 50-day above the 200-day, ADX14
above `adx_min` = 15 and ATR% above `atr_pct_min` = 1.5; Volume breakout needs a close above the 200-day,
ATR% above 1.5 and a close within 20% of the 52-week high; Donchian and Chart patterns need only a valid
ATR; Minervini needs the Trend Template. Each strategy's own thresholds are on its Rules tab.

**Chart page studies** (`web/static/studies.js`, 35 studies) follow TradingView's formulas: Wilder
smoothing for RSI, ATR and ADX; EMAs started from an SMA of the first N bars (so they differ from the
screening EMA for the first few dozen bars); Bollinger Bands on the population standard deviation. The
Volume study's line is a 20-bar average, while every screening rule uses the 50-day. See
[trend and range indicators](learn-price-indicators.md) and [momentum indicators](learn-price-oscillators.md).

## 11. Volume, demand and supply

| Number | Definition | Where |
|---|---|---|
| Relative volume (*Rel vol*, `rvol`) | The day's volume ÷ `vol_sma50` | Snapshot, Movers, Post-market |
| Accumulation day | Close up at least 0.2% on volume above the previous day's | `core/demand_supply.py` |
| Distribution day | Close down at least 0.2% on volume above the previous day's | `core/demand_supply.py` |

**The demand/supply verdict** (`core/demand_supply.py`, `compute`) is used by the trend-pullback strategy
only. Three tests score +1 or −1 each:

| Test | +1 | −1 |
|---|---|---|
| Up-day volume ÷ down-day volume, last 50 sessions | ≥ 1.2 | < 0.8 |
| Accumulation vs distribution days, last 25 sessions | acc > dist + 1 | dist > acc + 1 |
| Pullback volume ÷ the volume of the rally before it | < 0.8 | > 1.1 |

A total of +2 or more is "Demand in control", −2 or less "Supply in control", anything else
"Balanced". **Supply in control caps the decision at WATCH – WAIT.** The same file marks a supply zone at
the low of any down bar on more than 1.5× average volume in the last 60 sessions that sits above the price.
These thresholds are literals in the code, not named constants. See [volume](learn-price-volume.md) and
[supply and demand](learn-supply-demand.md).

## 12. Fundamentals

**Stored.** `quarterly_results` (one row per quarter, with the filing date `filed`) and `financial_lines`
(the statement lines behind the Fundamentals page). Cash flow is annual only. Indian companies use
consolidated figures when they filed them for at least 75% of recent quarters (`CONSOLIDATED_SHARE`),
standalone otherwise, never mixed. Operating profit is the filing's operating income in the US, and
screener.in's convention in India (before other income, interest and depreciation).

**Growth metrics** (`fundamentals/growth.py`): year-over-year EPS and sales growth per quarter (blank when
the year-ago figure is not positive), net margin, trailing-twelve-month EPS, annual EPS growth over
`ANNUAL_YEARS` = 3, and ROE = TTM net income ÷ the average of the latest equity and the equity about a
year earlier (else the Quality page's annual average). Old EPS is restated to today's share count across
splits and bonus issues (`split_factors`). Results older than `STALE_RESULTS_DAYS` = 200 are stale.

**Minervini SEPA tests** (`fundamentals/sepa.py`):

| Test | Rule | Constant |
|---|---|---|
| F1 EPS growth | Latest quarter's EPS up ≥ 25% on the year-ago quarter | `EPS_Q_GROWTH_MIN` |
| F2 EPS accelerating | Growth rate rose in ≥ 2 of the last 3 quarters | `ACCEL_MIN_RISES`, `ACCEL_WINDOW` |
| F3 Sales growth | Latest sales up ≥ 20%, or sales growth rising 3 quarters running | `SALES_Q_GROWTH_MIN`, `SALES_ACCEL_QUARTERS` |
| F4 Margins expanding | Net margin above the same quarter a year earlier | — |
| F5 Annual EPS growth | ≥ 25% a year over 3 fiscal years, no loss-making year | `ANNUAL_EPS_CAGR_MIN` |
| F6 Return on equity | TTM ROE ≥ 17% | `ROE_MIN` |
| F7 Beat estimates | Latest EPS above Yahoo's consensus, matched within 45 days (`SURPRISE_MATCH_DAYS`) | — |
| F8 No slowdown | EPS growth has not slowed two quarters running by 15 points or more | `DECEL_DROP_MIN` |

Verdicts: **LEADER** — F1, F2, F3, F4 and F8 pass, and F5 and F6 pass or are unavailable; **ACCEPTABLE**
— F1, F3 and F8 pass; **WEAK** — anything else; **NO DATA** — fewer than 2 of the last four quarters
have a growth reading (`MIN_GROWTH_READINGS`), or results are stale. **CODE 33**: EPS growth, sales
growth and net margin all rising for 3 quarters (`CODE33_QUARTERS`).

**Quality scorecard** (`fundamentals/quality.py`, up to five years of annual statements, at least
`MIN_YEARS` = 3), points out of 100:

| Test | Points | Rule |
|---|---|---|
| ROIC | 20 | Average ≥ 15% (banks and insurers: ROE ≥ 12%) |
| ROIC floor | 10 | No year below 10% (banks and insurers: latest ROA ≥ 1%) |
| Profitable | 10 | Profit in every year |
| Revenue growth | 10 | ≥ 7% a year |
| EPS growth | 10 | Diluted EPS ≥ 7% a year |
| Margin | 10 | Operating margin ≥ 15% |
| Margin trend | 5 | Latest margin within 1 point of the earlier average |
| Cash conversion | 10 | FCF positive every year and ≥ 80% of net income |
| Balance sheet | 10 | Net debt ≤ 2× EBITDA and interest covered 8× |
| No dilution | 5 | Share count up ≤ 1% a year |

Banks and insurers skip margin, margin trend, cash conversion and balance sheet, and are rescaled to 100.
**High quality** = score ≥ `HIGH_QUALITY_SCORE` = 70 and no red flag (a loss in any year, or negative
free cash flow in the latest year).

**Valuation and zones**, recomputed from each close. Three signals vote +1 / 0 / −1: FCF yield (cheap ≥
5%, fair ≥ 3%), P/E against the company's own median (cheap ≥ 20% below it, expensive > 10% above), PEG
(cheap ≤ 1, fair ≤ 1.5). An average vote ≥ +1/3 is Attractive, ≥ −1/3 Fair, else Expensive. A pullback is
any of: ≥ 15% below the 52-week high, within 3% of the 200-day, RSI14 ≤ 35. A falling knife is more than
15% below the 200-day.

| Zone | Rule |
|---|---|
| BUY ZONE | High quality + Attractive + a pullback + not a falling knife |
| ACCUMULATE | High quality + Fair or better + at most 10% above the 200-day (`ACCUMULATE_MAX_ABOVE_200`) + not a falling knife |
| WAIT | Everything else |
| AT YOUR PRICE | Added when the close reaches your own buy-below price |

No screen, strategy or backtest filters on valuation. See [earnings](learn-fund-earnings.md),
[quality](learn-fund-quality.md) and [valuation](learn-fund-valuation.md).

## 13. Earnings dates and the earnings gates

The screener counts days to the next earnings date as **weekdays** (`days_away`, `numpy.busday_count`;
holidays not modelled). The snapshot's *Days to earnings* field and Post-market's list count calendar
days. **An unknown date passes every gate.**

| Strategy (`key`) | Earnings rule in live screening |
|---|---|
| Trend pullback (`trend_pullback`) | Hard gate D2: no setup with earnings ≤ 10 days away; under 15 days blocks HIGH CONFIDENCE |
| Volume breakout (`breakout`) | Hard gate B7: no setup ≤ 10 days; ≤ 15 days blocks HIGH CONFIDENCE |
| Chart patterns (`chart_pattern`) | Hard gate S3: no setup within `EARNINGS_DAYS` = 10 days |
| Minervini SEPA (`minervini`) | Watch flag B4: earnings within `EARNINGS_WARN_DAYS` = 10 days; flagged, not rejected |
| Donchian channel (`donchian`) | No earnings rule |

Backtests apply none of these: no history of past earnings dates is stored, so tested trades hold through
results. No strategy looks at macro dates. See [the calendar](learn-macro-calendar.md).

## 14. What a backtest does differently

A backtest (`backtesting/backtest.py`, `portfolio_sim.py`) does not apply the downgrade, high-volatility
sizing, the earnings gates or the sector cap. It sizes off its current equity, with at most 10 positions (8 in the Minervini spec runs).
Minervini's spec runs use their own market filter instead (`--market-filter`, MKT-01 in
`backtesting/spec.py`): no new buys while the benchmark is below its 200-day, or its 50-day is below its
200-day.

How to read a run, and when to doubt one: [reading backtests](app-guide-backtests.md) and
[backtesting honestly](learn-test-backtesting.md). Results are on each strategy's Backtests tab and in
System → Reports archive.

## Further reading

- [Using the app — its pages, and what each shows](app-guide-pages.md)
- [Using the app — screens and strategies](app-guide-screens-strategies.md)
- [Using the app — the strategy families](app-guide-strategy-families.md)
- [Using the app — reading its backtests](app-guide-backtests.md)
