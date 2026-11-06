# Fast rebound, then the first pullback — event study

Minervini's webinar claim: after a market correction, the coming leaders "reclaim new highs within days" of the low, and
the entry is **the first pullback after that high, bought as it turns back up** (Cisco 1990; DocuSign, Teladoc and
Peloton 2020 — [creator notes](creator-mark-minervini.md) §4 and §9.1). It is setup **L3** in
[swing longs](system-swing-longs.md). This note tests it on every liquid stock after every 15%+ index correction,
US 2001–2025 and India 2006–2025, before anyone builds it as a setup. Event study only: no costs, no sizing.
Measured 4 November 2026 on data to 2 November.

**In short**

- **The setup finds the right stocks and still has no edge.** DocuSign (+10.1R), Moderna (+6.5R) and Novavax (+34R) are
  in the sample. But the median trade loses its full 1R, and only 27% (US) to 36% (India) of trades make money.
- **It does no better than any Stage 2 stock bought on the same day.** Six months out, the median entry beat that
  day's median Stage 2 stock by +0.1% in the US and +0.0% in India, with beat rates of 51% and 49%. None of the 18
  parameter settings gives a t-statistic above 1.5.
- **It lags the index.** The median entry trails SPY or the Nifty 500 by about 2–3 points over six months. Off major
  lows the gap in the US widens to −8 points: the index rebounds faster than stocks that are already at new highs.
- **Waiting for the pullback does not help.** In the US it is level with buying the same stock on its new-high day. In
  India it is about 3 points worse at six months, and worse in % to the 50-day exit (−3.4 points).
- **Verdict: rejected as a setup with an edge.** Keep the "fast rebound to new highs" as a watchlist cue, like the rest
  of Minervini's five things ([swing longs](system-swing-longs.md) §2.2). Do not trade it as a setup.

---

## 1. Method

| Item | US | India |
|---|---|---|
| Index (events) | S&P 500 (`^GSPC`), closes | Nifty 500 (`^CRSLDX`), closes |
| Index (comparison c) | SPY | Nifty 500 |
| Stock universe | today's listed common stocks (`breadth.eligible`), 1,600–5,100 with data | same, 580–2,300 |
| Liquid on the day | 50-day average turnover (close × volume) ≥ 0.32 bp of the market's turnover | ≥ 1.0 bp |
| Liquid stocks per event | 690–1,800 | 220–740 |
| Prices | `cache.load_many_cached` / `load_cached`, split-adjusted, not dividend-adjusted (stocks and index alike) | same |

**Events.** These are corrections of 15% or more, measured on closes and dated by the lowest close. A swing high
counts once the index has fallen 15% from it. A low is confirmed when the index rallies 15% off it or regains the
swing high. The next swing high is then the highest close before the next 15% fall. This counts the intermediate lows
of the 2000–02 and 2007–09 bear markets, such as April 2001 and November 2008. A "back to the old high" rule would merge
them, and with them 2010 and 2011, into two long episodes. That version is checked separately in §6.

| US low | Fall | India low | Fall |
|---|---|---|---|
| 2001-04-04 | −27.8% | 2006-06-14 | −32.6% |
| 2001-09-21 | −26.4% | 2007-03-05 | −15.3% |
| 2002-07-23 | −32.0% | 2008-03-17 | −33.8% |
| 2002-10-09 | −19.3% | 2008-07-16 | −28.7% |
| 2008-10-27 | −45.8% | 2008-10-27 | −46.8% |
| 2008-11-20 | −25.2% | 2008-11-20 | −18.4% |
| 2009-03-09 | −27.6% | 2009-03-09 | −19.2% |
| 2010-07-02 | −16.0% | 2011-12-20 | −31.8% |
| 2011-10-03 | −19.4% | 2013-08-28 | −16.7% |
| 2018-12-24 | −19.8% | 2016-02-25 | −20.8% |
| 2020-03-23 | −33.9% | 2018-10-26 | −15.8% |
| 2022-06-16 | −23.6% | 2020-03-23 | −38.3% |
| 2022-10-12 | −16.9% | 2022-06-20 | −18.5% |
| 2025-04-08 | −18.9% | 2025-02-28 | −18.8% |

**Candidates.** A candidate is a liquid stock that closes at a new 52-week closing high (above its prior 251 closes)
within *n* sessions of the index low (n = 10, 20, 30; day 0 is the low). On that day it must be in Stage 2 or
recovering into it. That means it passes the Trend Template's price tests (`screens/criteria.py` constants): close
above the 50-, 150- and 200-day averages, at least `MIN_PCT_ABOVE_52W_LOW` (30%) above the 52-week low, within
`MAX_PCT_BELOW_52W_HIGH` (25%) of the 52-week high, and RS rank ≥ `RS_MIN_RANK` (70). The RS rank is the weighted RS
score (`indicators.rs_score`) ranked 1–99 across that day's liquid stocks. A stock with the full template also has
50 > 150 > 200 and a 200-day higher than `SMA200_RISING_BARS` (21) sessions ago. A stock without it is "recovering".
Each stock counts once per event, on its first qualifying day.

**Entry.** After the new-high day, track the highest high. The first pullback is the first low at least *k*% under it
(k = 3, 5, 8). The entry is the first later close above the prior day's high, bought at that close. The stop is the
lowest low of the pullback. The entry must come within 60 sessions of the new high, and 98–99% of candidates got one
(89–98% at k = 8).

**Outcomes.**

- **Forward returns** are close to close, 21, 63 and 126 sessions (1, 3 and 6 months).
- **R** is the trade held to a **50-day-close exit**. Exit at the first close below the 50-day average, or at the stop
  if a low reaches it (at the open if it gaps through). After 252 sessions the trade is marked to market. R = (exit −
  entry) ÷ (entry − stop).

**Comparisons**, all from the same stock-day or entry date:

- **(a)** the same stock bought at the close of its new-high day. For its R the stop is the lowest low of the last
  10 sessions.
- **(b)** every liquid stock passing the *full* Trend Template on the entry day. Medians and beat rates use that
  day's Stage 2 median. Means and t-statistics use that day's Stage 2 mean, because a skewed return measured against a
  median looks better than it is.
- **(c)** the index (SPY or Nifty 500) from the entry close.

**Statistics.** Each cell reads *median · share > 0 · mean · t*. For an excess, "share > 0" is the beat rate. All
trades within one correction share its market, so t-statistics use standard errors **clustered by event**. With 12–14
clusters, read |t| < 2 as noise. Six-month windows of 2008-10/2008-11 and 2022-06/2022-10 overlap, and one stock can
qualify in both.

## 2. Headline: n = 20 sessions, k = 5% pullback

| Market | Horizon | Trades | Pullback entry | − (a) same stock, new-high day | − (b) Stage 2 stocks, same day | − (c) index |
|---|---|---|---|---|---|---|
| US | 1 month | 980 | +0.6% · 53% · +1.3% · 1.3 | −0.2% · 49% · −1.0% · −0.9 | +0.0% · 50% · +0.2% · 0.6 | −0.7% · 45% · −0.8% · −1.0 |
| | 3 months | 980 | +2.5% · 59% · +4.5% · 2.2 | −0.1% · 49% · −0.6% · −1.1 | +0.1% · 50% · +0.7% · 1.1 | −2.0% · 43% · −0.1% · −0.0 |
| | 6 months | 980 | +5.1% · 59% · +8.0% · 2.2 | −0.4% · 48% · −1.1% · −1.1 | +0.1% · 51% · +0.8% · 0.9 | −2.1% · 46% · +0.2% · 0.1 |
| India | 1 month | 199 | +2.0% · 58% · +3.6% · 2.2 | −0.5% · 47% · +0.4% · 0.4 | −0.2% · 47% · −1.3% · −1.7 | −1.4% · 42% · −1.7% · −1.4 |
| | 3 months | 199 | +6.0% · 63% · +9.0% · 3.2 | −0.9% · 49% · +0.6% · 0.4 | −2.0% · 42% · −0.9% · −0.5 | −3.0% · 44% · +0.3% · 0.1 |
| | 6 months | 199 | +9.0% · 64% · +13.5% · 3.7 | −3.0% · 38% · −2.3% · −1.5 | +0.0% · 49% · −1.2% · −0.5 | −2.9% · 46% · −0.3% · −0.1 |

The raw returns are positive and significant: buying anything after a market low usually is. Every comparison shows
the setup itself adding nothing. A typical entry came 8 sessions (US) or 7 (India) after the new high, after a
7.5–8.3% pullback, with 5.0–6.6% to the stop.

## 3. Every setting: six months

**US** (14 lows)

| n | k | New highs | Entries | 6m median · up | − (a) | − (b) | − (c) | R: median · >0 · mean · t |
|---|---|---|---|---|---|---|---|---|
| 10 | 3 | 451 | 450 | +4.7% · 57% | −0.9% · 42% · −1.2% · −1.1 | +0.5% · 52% · +2.6% · 1.3 | −2.2% · 45% · +1.5% · 0.4 | −1.00 · 26% · +0.11 · 0.4 |
| 10 | 5 | 451 | 445 | +3.8% · 56% | −0.7% · 45% · −1.4% · −1.2 | +0.9% · 53% · +3.0% · 1.5 | −1.3% · 47% · +2.0% · 0.5 | −1.00 · 28% · +0.05 · 0.2 |
| 10 | 8 | 451 | 406 | +3.4% · 57% | +0.6% · 51% · −0.7% · −0.4 | +0.0% · 50% · +2.8% · 1.1 | −1.2% · 47% · +2.2% · 0.6 | −0.50 · 32% · −0.02 · −0.1 |
| 20 | 3 | 991 | 989 | +5.5% · 59% | −0.6% · 45% · −0.9% · −1.3 | +0.2% · 51% · +0.7% · 0.8 | −2.6% · 45% · −0.1% · −0.1 | −1.00 · 26% · +0.01 · 0.1 |
| 20 | 5 | 991 | 980 | +5.1% · 59% | −0.4% · 48% · −1.1% · −1.1 | +0.1% · 51% · +0.8% · 0.9 | −2.1% · 46% · +0.2% · 0.1 | −1.00 · 27% · −0.02 · −0.1 |
| 20 | 8 | 991 | 881 | +4.7% · 57% | +1.2% · 54% · −0.5% · −0.3 | −0.2% · 50% · +0.2% · 0.2 | −2.4% · 46% · −0.0% · −0.0 | −0.50 · 30% · +0.05 · 0.3 |
| 30 | 3 | 1,504 | 1,501 | +5.0% · 58% | −0.6% · 46% · −0.7% · −0.9 | +0.2% · 51% · +0.4% · 0.9 | −2.5% · 46% · −0.2% · −0.1 | −1.00 · 26% · +0.06 · 0.3 |
| 30 | 5 | 1,504 | 1,475 | +4.9% · 58% | +0.0% · 50% · −0.6% · −0.6 | +0.1% · 51% · +0.4% · 1.3 | −1.9% · 47% · +0.1% · 0.0 | −1.00 · 27% · +0.06 · 0.4 |
| 30 | 8 | 1,504 | 1,318 | +4.1% · 58% | +1.5% · 56% · +0.3% · 0.2 | −0.4% · 49% · −0.1% · −0.2 | −2.6% · 45% · −0.1% · −0.1 | −0.51 · 30% · +0.09 · 0.6 |

**India** (13 lows with a candidate; none after 27 October 2008)

| n | k | New highs | Entries | 6m median · up | − (a) | − (b) | − (c) | R: median · >0 · mean · t |
|---|---|---|---|---|---|---|---|---|
| 10 | 3 | 101 | 101 | +9.0% · 59% | −2.4% · 38% · −0.9% · −0.8 | −0.6% · 47% · −3.6% · −0.9 | −3.4% · 42% · −4.2% · −1.1 | −0.66 · 38% · +0.87 · 1.8 |
| 10 | 5 | 101 | 100 | +7.6% · 59% | −3.1% · 34% · −2.3% · −2.1 | −1.0% · 45% · −4.6% · −1.2 | −4.5% · 44% · −4.6% · −1.2 | −0.60 · 37% · +0.79 · 1.7 |
| 10 | 8 | 101 | 98 | +9.1% · 59% | −2.4% · 39% · −2.1% · −1.3 | −0.4% · 44% · −4.4% · −1.1 | −3.7% · 44% · −3.8% · −0.9 | −0.26 · 41% · +0.90 · 1.7 |
| 20 | 3 | 201 | 201 | +9.7% · 64% | −2.4% · 39% · −1.2% · −0.8 | +0.2% · 50% · −0.2% · −0.1 | −2.9% · 45% · +0.1% · 0.1 | −1.00 · 35% · +0.86 · 1.8 |
| 20 | 5 | 201 | 199 | +9.0% · 64% | −3.0% · 38% · −2.3% · −1.5 | +0.0% · 49% · −1.2% · −0.5 | −2.9% · 46% · −0.3% · −0.1 | −0.62 · 36% · +0.73 · 1.9 |
| 20 | 8 | 201 | 196 | +9.6% · 65% | −1.8% · 43% · −2.2% · −1.0 | +0.2% · 50% · −0.7% · −0.3 | −1.1% · 48% · +0.6% · 0.2 | −0.27 · 41% · +0.80 · 2.4 |
| 30 | 3 | 344 | 344 | +11.7% · 65% | −2.4% · 38% · −1.6% · −1.8 | +0.6% · 52% · +2.1% · 1.1 | −0.1% · 50% · +4.9% · 1.7 | −0.63 · 40% · +1.15 · 2.7 |
| 30 | 5 | 344 | 340 | +9.8% · 65% | −2.8% · 38% · −2.4% · −2.3 | +0.4% · 52% · +1.2% · 0.7 | +0.3% · 51% · +4.7% · 1.7 | −0.51 · 39% · +1.00 · 2.9 |
| 30 | 8 | 344 | 335 | +9.0% · 65% | −2.6% · 41% · −3.3% · −1.8 | +0.4% · 51% · +0.5% · 0.3 | +0.3% · 51% · +4.6% · 1.8 | −0.28 · 40% · +0.95 · 2.9 |

Across all 18 settings, the six-month excess over the same-day Stage 2 median lies between −1.0% and +0.9%. Beat
rates run 44–53%, and no |t| exceeds 1.5. The three-month figures say the same (US −0.0% to +0.4%; India −2.7% to
+0.0%). A deeper pullback (k = 8) gives a shallower median loss in R, because fewer trades are stopped at once, but no
better mean. In India, buying the pullback instead of the new high cost about 2–3 points at every setting.

## 4. Per event (n = 20, k = 5, six months)

Each "−" column is the median, across that event's entries, of the trade's six-month return minus the comparison's.

**US**

| Index low | Fall | Liquid | Stage 2 at low | Entries | 6m median | − (a) | − (b) | Beat (b) | − (c) | Index 6m | R median · mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2001-04-04 | −27.8% | 688 | 85 | 128 | −5.4% | −1.5% | −0.8% | 48% | +6.5% | −10.8% | −0.57 · +0.38 |
| 2001-09-21 | −26.4% | 755 | 27 | 64 | +13.3% | +1.1% | +1.0% | 55% | +11.2% | +2.6% | −0.74 · −0.23 |
| 2002-07-23 | −32.0% | 788 | 3 | 30 | −6.8% | −0.5% | +0.6% | 57% | +0.1% | −8.7% | −1.00 · −0.73 |
| 2002-10-09 | −19.3% | 772 | 30 | 62 | +2.4% | +1.8% | +0.0% | 52% | −1.0% | +2.2% | −1.00 · −0.72 |
| 2008-10-27 | −45.8% | 1,029 | 0 | 10 | −13.6% | +3.6% | −0.5% | 40% | −17.5% | +0.1% | −1.00 · −0.72 |
| 2008-11-20 | −25.2% | 1,067 | 5 | 11 | −1.3% | +3.6% | +9.5% | 55% | −7.8% | +7.6% | −1.00 · −0.57 |
| 2009-03-09 | −27.6% | 985 | 6 | 18 | +14.4% | −0.6% | +3.9% | 50% | −15.7% | +29.9% | −1.00 · −0.50 |
| 2010-07-02 | −16.0% | 1,103 | 42 | 101 | +16.0% | +2.4% | −1.1% | 47% | −1.7% | +16.8% | −1.00 · +0.17 |
| 2011-10-03 | −19.4% | 1,154 | 14 | 100 | +11.1% | −1.0% | −0.5% | 48% | +2.3% | +10.5% | −1.00 · −0.12 |
| 2018-12-24 | −19.8% | 1,491 | 15 | 48 | +9.6% | −1.4% | −1.7% | 46% | −2.2% | +10.2% | −0.64 · +0.77 |
| 2020-03-23 | −33.9% | 1,438 | 7 | 65 | +12.2% | −2.0% | −4.2% | 42% | −11.4% | +23.0% | −1.00 · +1.00 |
| 2022-06-16 | −23.6% | 1,745 | 26 | 38 | −1.7% | −0.4% | −2.1% | 47% | −3.5% | +0.8% | −0.81 · −0.53 |
| 2022-10-12 | −16.9% | 1,786 | 81 | 174 | −4.4% | −1.5% | +3.6% | 58% | −11.0% | +6.2% | −0.86 · −0.42 |
| 2025-04-08 | −18.9% | 1,802 | 21 | 131 | +8.0% | −1.4% | +3.7% | 55% | −7.3% | +15.2% | −0.68 · +0.19 |
| **Events with median > 0** | | | | | | 5 of 14 | 7 of 14 | | 4 of 14 | | |

**India**

| Index low | Fall | Liquid | Stage 2 at low | Entries | 6m median | − (a) | − (b) | Beat (b) | − (c) | Index 6m | R median · mean |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2006-06-14 | −32.6% | 310 | 0 | 2 | +19.6% | +16.4% | −17.3% | 50% | −18.1% | +37.7% | +4.02 · +4.02 |
| 2007-03-05 | −15.3% | 281 | 22 | 10 | +44.2% | +0.7% | +11.9% | 70% | +11.5% | +35.3% | +1.17 · +3.08 |
| 2008-03-17 | −33.8% | 296 | 3 | 2 | −32.9% | −13.8% | +2.4% | 50% | +9.5% | −42.5% | −0.77 · −0.77 |
| 2008-07-16 | −28.7% | 262 | 1 | 5 | −39.2% | −1.8% | +0.1% | 60% | −2.0% | −37.1% | −1.00 · −0.82 |
| 2008-11-20 | −18.4% | 235 | 0 | 1 | +6.2% | +4.5% | — | — | −49.7% | +55.9% | +0.10 · +0.10 |
| 2009-03-09 | −19.2% | 221 | 3 | 4 | +8.4% | −11.5% | −32.3% | 50% | −45.9% | +62.5% | −1.00 · +0.84 |
| 2011-12-20 | −31.8% | 283 | 2 | 4 | +4.0% | −4.3% | −12.7% | 25% | +0.9% | +6.6% | −0.49 · +3.35 |
| 2013-08-28 | −16.7% | 266 | 12 | 25 | +16.8% | −1.7% | +0.0% | 44% | +2.5% | +13.7% | −0.19 · +0.97 |
| 2016-02-25 | −20.8% | 468 | 9 | 23 | +23.9% | −3.6% | +0.4% | 52% | +7.6% | +17.2% | −0.55 · +2.30 |
| 2018-10-26 | −15.8% | 435 | 6 | 20 | +1.3% | +1.6% | −1.6% | 50% | −7.7% | +7.2% | −1.00 · −0.82 |
| 2020-03-23 | −38.3% | 391 | 1 | 17 | +10.2% | −7.5% | −16.0% | 29% | −19.7% | +29.3% | −0.79 · −0.35 |
| 2022-06-20 | −18.5% | 616 | 18 | 52 | +4.7% | −3.9% | +2.2% | 52% | +0.5% | +10.4% | +0.33 · +1.10 |
| 2025-02-28 | −18.8% | 738 | 18 | 34 | +6.8% | +0.4% | −0.0% | 50% | −4.0% | +11.7% | −1.00 · −0.50 |
| **Events with median > 0** | | | | | | 4 of 12 | 5 of 12 | | 6 of 12 | | |

The counts tell the story: about half the events go each way against Stage 2 stocks, and fewer than half against the
index. In the sharpest rebounds the index left the setup behind: US 2009 (−15.7 points), 2020 (−11.4), 2022-10
(−11.0) and 2025 (−7.3), and India 2009 and 2020. India before 2013 had 1–10 entries per event, so its early rows are anecdotes.

## 5. Held to the 50-day exit (n = 20, k = 5)

| Market | Trade | % return: median · >0 · mean · t | R: median · >0 · mean · t | Sessions held (median) |
|---|---|---|---|---|
| US | pullback entry, stop under the pullback low | −3.2% · 27% · +0.6% · 0.5 | −1.00 · 27% · −0.02 · −0.1 | 12 |
| | (a) same stock on its new-high day, stop under its 10-day low | −3.1% · 37% · +2.4% · 1.2 | −0.24 · 37% · +0.09 · 1.0 | |
| | (b) Stage 2 stocks, same day, no stop | −2.7% · 10% · +1.0% · 0.7 | | |
| | pullback − (a) | +0.2% · 51% · −1.8% · −1.8 | | |
| | pullback − (b) | +0.0% · 51% · −0.4% · −1.0 | | |
| India | pullback entry, stop under the pullback low | −3.3% · 36% · +4.1% · 1.8 | −0.62 · 36% · +0.73 · 1.9 | 17 |
| | (a) same stock on its new-high day, stop under its 10-day low | +0.5% · 51% · +7.5% · 2.2 | +0.02 · 51% · +0.51 · 2.0 | |
| | (b) Stage 2 stocks, same day, no stop | +0.0% · 50% · +7.1% · 2.9 | | |
| | pullback − (a) | −1.7% · 37% · −3.4% · −1.7 | | |
| | pullback − (b) | −1.5% · 38% · −3.0% · −1.4 | | |

For (b) the median and ">0" columns are per-day medians, and the mean is per-day means. In the US the (b) row's 10% ">0"
says that on 90% of entry days the typical Stage 2 stock lost money to a 50-day exit. Its mean is carried by a few large
winners.

**The US trade is a coin toss in R**: −0.02R a trade. **India's +0.73R is real money but not an edge.** The same
stocks bought on their new-high day made more (+7.5% against +4.1% to the same exit), and so did the average Stage 2
stock bought on the entry day (+7.1%). India's markets rallied hard after most of these lows, and the trade collected
part of that rally. The tail carries both markets: the top 5% of trades made 62% (US) and 43% (India) of all positive
R. That is Minervini's examples seen from the population: DocuSign +10.1R, Moderna +6.5R and Novavax +34R in 2020,
next to a median trade stopped out for −1R.

## 6. Does anything rescue it?

| Market | Group (k = 5) | Trades | 6m − (b) | 6m − (c) | R |
|---|---|---|---|---|---|
| US | new high in sessions 0–10 | 445 | +0.9% · 53% · +3.0% · 1.5 | −1.3% · 47% · +2.0% · 0.5 | −1.00 · 28% · +0.05 · 0.2 |
| | 11–20 | 535 | −0.1% · 49% · −1.0% · −0.5 | −2.7% · 45% · −1.2% · −0.5 | −1.00 · 27% · −0.07 · −0.7 |
| | 21–30 | 495 | +0.0% · 50% · −0.3% · −0.2 | −1.5% · 48% · −0.3% · −0.1 | −1.00 · 27% · +0.22 · 1.0 |
| | full Trend Template on the new-high day (n ≤ 30) | 1,047 | +0.4% · 52% · +1.2% · 2.3 | −0.8% · 49% · +1.4% · 0.5 | −1.00 · 26% · +0.06 · 0.4 |
| | recovering into it (n ≤ 30) | 428 | −0.8% · 48% · −1.4% · −1.8 | −5.4% · 43% · −3.1% · −1.3 | −1.00 · 29% · +0.06 · 0.3 |
| India | new high in sessions 0–10 | 100 | −1.0% · 45% · −4.6% · −1.2 | −4.5% · 44% · −4.6% · −1.2 | −0.60 · 37% · +0.79 · 1.7 |
| | 11–20 | 99 | +0.6% · 53% · +2.2% · 0.9 | −2.4% · 47% · +4.0% · 1.6 | −0.62 · 35% · +0.66 · 1.5 |
| | 21–30 | 141 | +3.3% · 55% · +4.5% · 1.5 | +3.7% · 57% · +11.7% · 2.8 | −0.33 · 43% · +1.39 · 2.6 |
| | full Trend Template on the new-high day (n ≤ 30) | 242 | +0.4% · 52% · +0.8% · 0.4 | −0.2% · 49% · +4.7% · 1.5 | −0.38 · 39% · +0.94 · 2.7 |
| | recovering into it (n ≤ 30) | 98 | +0.5% · 52% · +2.2% · 0.6 | +2.6% · 54% · +4.5% · 1.0 | −0.88 · 39% · +1.16 · 2.3 |

- **Speed.** "Fastest back to new highs" is the heart of the claim, and it does not order the results. In the US the
  0–10-session group is a fraction ahead (t 1.5). In India it is the *worst* group, and the 21–30-session group is
  the best.
- **Full Trend Template vs recovering.** In the US, stocks already in a full Stage 2 at the new high did slightly
  better than the Stage 2 average (mean +1.2 points, t 2.3; median +0.4). Those still recovering lagged. India shows
  no such split. This is one cut among roughly forty in this note, so it is a lead, not a result.
- **Major lows only.** This counts only lows the index later recovered from: US 2002-10, 2009-03, 2018-12, 2020-03,
  2022-10, 2025-04; India 2006-06, 2007-03, 2009-03, 2016-02, 2018-10, 2020-03, 2022-06. These are real bottoms, the
  case Minervini describes. At n = 20, k = 5, six months:
  - US, 498 trades: −0.9% against (a); +0.9% · 53% · +2.3% · t 2.1 against (b); −8.3% · 37% against the index; mean R
    +0.00.
  - India, 128 trades: −3.7% · 34% against (a); +0.1% · 50% against (b); −3.4% against the index; mean R +1.01 (t 2.1).
  - Off real bottoms the index is the hardest benchmark to beat. The stocks already at new highs are, as
    [relative strength](learn-price-rs.md) §4.3 found, often the defensive ones the rebound leaves behind.
- **An intraday buy-stop** over the prior day's high is closer to "buy as it turns up". It fills at the higher of the
  open and the prior high, with the same stop and exit. It does not help: US mean R +0.01 (median −1.00, 24% > 0);
  India +0.31 (median −1.00, 24% > 0), worse than the close version. It triggers earlier and gets shaken out more.

## 7. Verdict

**L3 is rejected as a setup with an edge.** These are the questions it had to answer yes to:

1. Do its entries beat Stage 2 stocks bought the same day, by median and beat rate, with event-clustered |t| ≥ 2, in
   both markets?
2. Does the pullback improve on buying the same stock at its new high?
3. Is its expectancy positive in R?

It fails the first in every one of 18 settings. It fails the second (level in the US, worse in India). It meets the
third only in India, where buying the same stocks at their high, or any Stage 2 stock, did better.

This joins two earlier tests here. [Relative strength](learn-price-rs.md) §4.3 bought early-new-high stocks on day 30.
The `minervini_spec` base-breakout strategy finds expectancy within a few hundredths of R of zero. All three find the
same thing: **the stocks Minervini names exist, but the rule that picks them also picks many look-alikes, and the
look-alikes cancel them out.** What remains useful is a cue: a stock back at new highs soon after a low goes on the
watchlist. Whether to buy it is then decided by a base, a pivot and the market's follow-through, not by the speed of
the rebound.

## 8. Limits

- **Survivorship.** Only stocks listed today are included. Delisted names are missing from both the candidates and the
  Stage 2 comparison, so *absolute* returns are flattered. Comparisons on the same dates are much less affected.
- **The low is known in hindsight.** A zigzag confirms a low only after a 15% rally. A trader in real time does not
  know which low is the one. Conditioning on real lows is a favour to the setup, and it still shows no edge.
- **The mechanical skeleton only.** Minervini also judges the pause: tight, quiet, volume drying up. No tightness or
  volume test is applied here. Adding one now would be a new rule, chosen after seeing these results, and would need
  its own test on data it was not chosen on.
- **The RS rank** is ranked across each day's liquid stocks, not the rating universe (`spec.rs_ratings`, which also
  applies a traded-price floor). The two differ only at the margins.
- **Small samples.** India before 2013 had 1–10 entries per event. Events in 2008 and 2022 overlap. Every year to 2026
  is in the sample and nothing was tuned, so there is no hold-out. With a null result there was nothing to tune.
- **No costs.** They would only lower the figures.

## 9. Reproduce

Scratch scripts (not in the repository), run from `scripts/` with `PYTHONPATH=.:<scratch dir>`:

1. `panel.py us india` builds the price panels, Trend Template, RS rank and turnover floor. Its market-turnover series
   matches `breadth_daily.turnover` from 2009 (median ratio 1.000) and extends it back to 1998 and 2004.
2. `study.py us india`, plus `--major` for the major-lows version.
3. `report.py us india us_major india_major` for the raw grid, and `tables.py` for this note's tables.
4. `intraday.py us india` for the buy-stop variant.

`events.py` holds the correction dating. A copy is in the shared session notes for this work.
