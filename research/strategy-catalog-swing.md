# Swing strategy catalogue — the public setups, graded

*Written 2026-11-15. A map of the swing setups traders publish — named traders, books, blogs, YouTube and
X — grouped by the behaviour they bet on, graded for how credible the evidence is, and ranked within each
group by what published tests found. The last column notes what this project's own backtests found where
the setup is implemented; it never decides the rank. Own figures are optimise-stage (2013–2021,
in-sample) excess CAGR against the index for the best configuration tried, unless marked otherwise.*

**In short**

- Every swing setup is one of a few bets: **continuation** (the move keeps going), **reversal** (the trend
  turns), **snap-back** (a stretched price returns), **event** (news re-prices the stock) or **calendar**.
  Breakout is not a category of its own; it is one of five ways to enter a continuation trade.
- The setups with the strongest outside evidence are the ones built on documented anomalies: ranking by
  momentum, buying near the 52-week high, and drift after earnings surprises.
- Most named-trader setups (VCP, cup-with-handle, Qullamaggie breakouts, EMA pullbacks) rest on track
  records and chart examples, not on published tests. That puts them mid-table on credibility, however
  good the trader.
- Classic chart patterns, candlesticks, Fibonacci and indicator crossovers have been tested and mostly fail
  after costs. They sit at the bottom.
- This project's own tests agree with that ordering: the only setups with an edge here are cross-sectional
  momentum, and to a lesser degree a few continuation variants in India.

---

## 1. How the grouping works

Two questions place any setup:

1. **What does it bet on?** The behaviour.
2. **How does it get in?** The trigger.

| Behaviour (the bet) | Triggers (how it enters) | What must be true to pay |
|---|---|---|
| **Continuation** | Breakout, squeeze, pullback, burst, relative-strength rank | A trend already under way keeps going |
| **Trend following** | Channel or average cross, then ride with a trailing exit | Big trends happen, and you stay in them |
| **Reversal** | Base completion, failed low, divergence | A trend ends and a new one starts |
| **Snap-back (mean reversion)** | Oversold reading, band touch, down-streak | A stretched price returns to normal within days |
| **Fade** | Failed breakout, gap fill | A move that should have worked did not |
| **Event** | Earnings surprise, gap, index change, insider buying | News re-prices the stock, and the market is slow to finish |
| **Calendar** | Turn of month, pre-holiday | Money flows on a predictable schedule |
| **Short side** | Parabolic fade, stage 4 breakdown | The above, mirrored |

**So which categories are like breakout?** The other continuation triggers, because they make the same
bet and fail the same way, in choppy markets:

- **Squeeze.** Volatility contracts, then expands.
- **Pullback.** Buy the dip inside an uptrend instead of the break of the range.
- **Burst / gap-and-go.** A sudden large move on volume, bought on the day or the next.
- **Relative-strength rank.** Buy the strongest stocks, with no pattern needed.

Owning a breakout and a pullback strategy is not diversification. Pairing a breakout strategy with a
snap-back strategy is.

---

## 2. The credibility score (0–5)

Each setup gets a point for each test it passes:

| Points | Test |
|---|---|
| 0–2 | **Evidence.** 2 = peer-reviewed study of the underlying effect. 1 = a published backtest with full rules (book, quant blog). 0 = chart examples or track record only |
| +1 | **Survived outside the original study.** Independent replication, or it kept working after publication |
| +1 | **Testable rules.** Can be coded without judgment calls |
| +1 | **Survives costs.** Still pays after realistic commissions, spread and slippage |

A setup that has been tested and failed is capped at 1, whatever else it has.

**Public outcome grade.** This is the sort key within each group:

| Grade | Meaning |
|---|---|
| **A** | Positive after costs in independent tests outside the original sample |
| **B** | Positive in published backtests, but in-sample, before costs or not replicated |
| **C** | Mixed, or it decayed after publication |
| **D** | No published test (anecdote, trader examples, track record) |
| **E** | Tested and failed |

A trader's contest win is a track record, not a test of one setup. It earns no evidence points, but it
is noted.

---

## 3. The catalogue

### 3.1 Continuation — relative-strength rank

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Cross-sectional momentum** (buy top 12-1 month returns, monthly) | Jegadeesh & Titman (1993), replicated widely | A | 5 | Edge: India momentum beat its benchmark in-sample and out-of-sample (vol-scaled, baseline, combo) |
| 2 | **Industry / sector momentum** | Moskowitz & Grinblatt (1999); Faber's sector rotation | B | 4 | India marginal (+1.6), US fails |
| 3 | **Dual momentum** (relative plus absolute, few ETFs) | Antonacci, *Dual Momentum Investing* (2014) | C | 3 | Mixed: failed in-sample, passed out-of-sample on 14 trades |
| 4 | **RS line at a new high before price** | O'Neil / IBD | D | 2 | Not tested alone |
| 5 | **RS leaders** (top relative-strength rank plus a setup) | IBD, Minervini | D | 2 | Fails (−9 to −10) |

### 3.2 Continuation — breakout from a base

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **52-week-high proximity / breakout** | George & Hwang (2004) | A | 4 | Part of the trend template; not tested alone |
| 2 | **Donchian channel breakout** (20/55-day) | Turtle rules (Dennis, Faith); Brock et al. (1992) | C | 3 | India +3.7, US −4.7 |
| 3 | **Volatility contraction pattern (VCP)** | Minervini (US Investing Championship 1997) | D | 2 | US v1.67 passed its own out-of-sample rule but trailed SPY (−0.6); in-sample −2 to −3 |
| 4 | **Cup-with-handle / CAN SLIM base** | O'Neil, *How to Make Money in Stocks* | D | 2 | Inside chart_pattern: about −1 |
| 5 | **Qullamaggie breakout** (flag after a big move, opening-range entry) | Kristjan Kullamägi (public account statements, not audited) | D | 2 | US −6.7, India −10 |
| 6 | **High tight flag** | O'Neil; Bulkowski's pattern statistics | B | 2 | Not tested alone |
| 7 | **Darvas box** | Darvas, *How I Made $2,000,000* (1960) | D | 2 | −1.8 US, −3.7 India |
| 8 | **Pocket pivot** (volume inside the base) | Morales & Kacher (2010) | D | 2 | Not tested |
| 9 | **Weinstein stage 2 breakout** | Weinstein (1988) | D | 2 | −2 to −3.6 |
| 10 | **Ascending triangle / flat base / base-on-base** | Bulkowski; Zanger (large claimed returns, unverified) | B | 1 | Inside chart_pattern |
| 11 | **Volume-surge breakout** | Common blog rule | E | 1 | −7.8 India, −8.6 US |

### 3.3 Continuation — volatility squeeze

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **NR7 / inside-bar breakout** | Crabel (1990) | C | 2 | Not tested |
| 2 | **Bollinger squeeze** | John Bollinger | D | 1 | Not tested |
| 3 | **TTM squeeze** (Bollinger inside Keltner) | John Carter, *Mastering the Trade* | D | 1 | Not tested |
| 4 | **Minervini coil** (tight range before the pivot) | Minervini | D | 2 | Fails in-sample |

### 3.4 Continuation — pullback in a trend

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Buy short-term weakness in a long-term uptrend** (RSI(2) under 10 above the 200-day) | Connors & Alvarez (2008) | C | 3 | See snap-back: decayed |
| 2 | **Holy Grail** (ADX above 30, pullback to the 20-EMA) | Raschke & Connors, *Street Smarts* (1995) | D | 2 | Not tested |
| 3 | **EMA pullback** (8/21-EMA, 10/20-day touch) | Swing YouTube / X, Kullamägi | D | 2 | In-sample, no edge |
| 4 | **Kell's EMA crossback / cycle of price action** | Oliver Kell (US Investing Championship 2020) | D | 2 | India +9.4 (with a group-RS floor), US −11 |
| 5 | **Anchored VWAP pullback** | Brian Shannon | D | 1 | Not tested |
| 6 | **Trend pullback** (above the 50- and 200-day, dip to the 20) | Common swing rule | D | 2 | US +2.2 only with idle cash in the index; failed out-of-sample (−3.05% CAGR) |
| 7 | **Elder triple screen** | Alexander Elder, *Trading for a Living* (1993) | D | 1 | Not tested |
| 8 | **Fibonacci retracement entry** | Widespread | E | 0 | Not tested |

### 3.5 Continuation — burst / gap-and-go

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Episodic pivot** (earnings or news gap of 10%+ on huge volume) | Pradeep Bonde (Stockbee), popularised by Kullamägi | B | 3 | See event: earnings gap |
| 2 | **Momentum burst** (a 4% day on rising volume, held 3–5 days) | Stockbee | D | 2 | India +5.1 with a 20-day-average exit; US −6.7 |
| 3 | **Power play** (100% in 8 weeks, then a tight flag) | O'Neil, Minervini | D | 1 | Not tested |

### 3.6 Trend following (ride the move)

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Time-series momentum on futures / ETFs** | Moskowitz, Ooi & Pedersen (2012); Hurst, Ooi & Pedersen (2017) | A | 5 | Turtle trend: tsmom −7.6 (US) |
| 2 | **Moving-average trend** (price above the 200-day, 10-month average) | Faber (2007); Brock et al. (1992) | C | 3 | −1.8 India, −4.4 US |
| 3 | **Supertrend / ATR trailing stop** | Popular in India | D | 1 | No edge |
| 4 | **Golden cross** (50 over 200) | Widespread | E | 1 | Not tested alone |
| 5 | **MACD crossover** | Widespread | E | 1 | Not tested |

### 3.7 Reversal (trend change)

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Double bottom / inverse head-and-shoulders** | Bulkowski; Lo, Mamaysky & Wang (2000) found some information content | B | 2 | Inside chart_pattern |
| 2 | **Wyckoff spring** | Richard Wyckoff | D | 1 | Not tested |
| 3 | **1-2-3 reversal** | Victor Sperandeo | D | 1 | Not tested |
| 4 | **RSI / MACD divergence** | Widespread | E | 1 | Not tested |
| 5 | **TD Sequential 9/13** | Tom DeMark | D | 1 | Not tested |
| 6 | **Candlestick reversals** (hammer, engulfing) | Steve Nison; Marshall, Young & Rose (2006) found no value on US large caps | E | 0 | Not tested |

### 3.8 Snap-back (short-term mean reversion)

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Short-term reversal** (buy last week's or month's losers) | Jegadeesh (1990), Lehmann (1990) | C | 4 | Not tested on stocks; costs eat most of it |
| 2 | **RSI(2) on indices** | Connors & Alvarez (2008) | C | 3 | High win rate; trails the index at the same exposure |
| 3 | **Bollinger %b on indices** | Connors / Alvarez Quant Trading | C | 3 | Closest of the three; still trails the index at the same exposure |
| 4 | **Double 7s** | Connors & Alvarez (2008) | C | 3 | Trails the index at the same exposure |
| 5 | **Internal bar strength (IBS)** (buy a close near the low) | Practitioner research on index ETFs | B | 2 | Not tested |
| 6 | **Stock oversold reversion** (big caps, RSI or down-streak) | Connors | C | 2 | −11 to −16 |

### 3.9 Fade (the failed move)

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Turtle Soup** (fade a failed 20-day breakout) | Raschke & Connors (1995) | D | 2 | Not tested |
| 2 | **Gap fill** | Widespread | D | 1 | Not tested |

### 3.10 Event-driven

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Post-earnings-announcement drift** | Bernard & Thomas (1989, 1990); Chan, Jegadeesh & Lakonishok (1996) | C (weaker since the 2000s in US large caps) | 4 | −7 US, −15 India |
| 2 | **Earnings gap-up continuation** | PEAD plus the episodic pivot | B | 3 | US +7.9 (older version, 10-day exit); India −8 |
| 3 | **Earnings-announcement premium** (hold into the report) | Frazzini & Lamont (2007) | B | 3 | Not tested |
| 4 | **Insider cluster buying** | Lakonishok & Lee (2001) | B | 3 | Not tested |
| 5 | **Index inclusion** | Shleifer (1986); much smaller in recent decades | C | 3 | Not tested |
| 6 | **Short-squeeze long** (high short interest) | Asquith, Pathak & Ritter (2005) found high short interest underperforms on average | E | 1 | Not tested |

### 3.11 Calendar

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Turn of the month** | Ariel (1987); Lakonishok & Smidt (1988) | C | 4 | Not tested |
| 2 | **Pre-holiday** | Lakonishok & Smidt (1988) | C | 3 | Not tested |

### 3.12 Short side

| # | Setup | Source | Grade | Cred. | Here |
|---|---|---|---|---|---|
| 1 | **Parabolic short** (fade an extended run) | Kullamägi | D | 2 | Fails (−0.095R a trade) |
| 2 | **Stage 4 breakdown short** | Weinstein | D | 2 | −6.6 India, −14 US |
| 3 | **Failed-breakout short** | Common swing rule | D | 1 | Not tested |

---

## 4. What this suggests testing next

The empty "Here" cells with the best grades are the cheapest places to look for an edge:

1. **52-week-high proximity on its own** (A, 4), ranked across stocks rather than as a pass/fail gate.
2. **Short-term reversal on liquid stocks** (C, 4), with costs modelled honestly. It is the textbook
   counterweight to momentum.
3. **Turn of the month** (C, 4) as an overlay on the index exposure the momentum books already hold.
4. **Insider cluster buying** (B, 3), in India from exchange disclosures.
5. **Turtle Soup** (D, 2), as a diversifier to the breakout family: it profits exactly when breakouts fail.

Each is a different bet from the eight continuation strategies already here, which is the point.

## 5. Caveats

- Grades rest on published work as it is generally reported. Several anomalies (PEAD, short-term
  reversal, index inclusion) weakened after publication, which is why they grade C, not A.
- Bulkowski's pattern statistics come from his own large samples, without costs or out-of-sample checks.
  That earns a B, not an A.
- A trader's record, even a championship, mixes setup, selection, sizing and discretion. It cannot
  credit one setup.
- "Here" figures are mostly in-sample and against the index. A swing book in cash much of the time
  starts behind on that measure, by design.
