# Daily-review rule tests — the stretch override and narrow vs broad

Two rules of the [daily market review](system-daily-market-review.md) came from Martin Luk's reads and were marked
*proposed, untested*: the **stretch override** (§3 Q2, §4.2 — don't add shorts while the index is stretched below its
9-day EMA; wait for the retest) and **narrow vs broad** (§3 Q3 — a cap-weighted index falling while the equal-weighted
one holds near its high is "a few giants", not the market). This note measures both on stored daily prices, US and
India, 2009–2026. Event studies only: no costs, no stops, no sizing. Measured 4 November 2026 on data to 2 November.

**In short**

- **US: the index does bounce after a stretched close.** After QQQ closed 3%+ under its 9-day EMA, its next five
  sessions averaged +2.0% (73% up) against +0.4% on all days; weak stocks bounced with it (+2.3%), not more than it.
- **Waiting for the retest gave shorts a better price — in both countries.** Shorting a weak stock at its first close
  back under its own 9-day EMA, after the index had retested its 9-day, beat shorting it on the stretched day by about
  +1.3 to +3 points to a common exit; on ordinary days the same wait gained about nothing (US) or +0.65 (India). It
  improves the *entry price*, not the trade after entry.
- **India: no index bounce, yet the same timing gain.** Nifty stretched days were not followed by a reliable bounce, and
  weak stocks kept falling for a day or two — they bounced later, inside the 10–12 sessions the wait took.
- **The long-side mirror fails.** Stretched *up*, the index did not pull back, strong stocks kept outperforming, and
  waiting for a retest to buy cost money (India −0.7 to −2.2 points, t −2 to −5). Do not delay buys for it.
- **Narrow vs broad does not forecast the index.** Neither the narrow picture nor a broad decline was followed by worse
  1-, 3- or 6-month index returns than an ordinary day in the US; in India the sign flipped between 2009–2021 and
  2022–2026. Keep it as a *description* (where the damage is, what to hunt), not a regime forecast.

---

## 1. Data and method

| Item | US | India |
|---|---|---|
| Indexes | SPY, QQQ (stretch); SPY vs RSP (breadth) | Nifty 50, Nifty 500 (stretch); Nifty 50 vs Nifty 500 and vs Nifty Midcap 50 (breadth) |
| Index history used | 2009-07 → 2026-11-02 (stretch); RSP from 2003-05 (breadth) | 2009-07 → 2026-11-02 (stretch); from 2008-09 (breadth) |
| Stock universe | each day's 1,000 most-traded common stocks by 20-day average turnover (close × volume), as the breadth table counts them | same, 1,000 most-traded |
| Loaders | `cache.load_many_cached` / `load_cached` (prices), `breadth.eligible` (common stocks only) | same |

- **9-day EMA**: exponential average of closes, span 9. *Stretch* = close ÷ 9-day EMA − 1.
- **Weak stock** (short candidate): close below its 50-day average, the 50-day below its value 10 sessions ago
  (falling), and 63-session return in the bottom third of that day's universe (ranking by return or by return minus
  the index is the same thing on one day). **Strong stock** (long mirror): above a rising 50-day, top third.
- **Forward returns** are close to close; stock returns clipped to ±50% before averaging (bad prints). Stock results
  are first averaged across stocks *per day*, so each day counts once.
- **t-statistics.** Index and per-day comparisons ("stretched days vs all other days") use Newey–West standard errors,
  lag 2×horizon (at least 5), because stretched days come in runs. Trade comparisons use one average per *episode*
  and a plain t over episodes. Read |t| < 2 as noise.
- **Periods.** Results are shown for 2009–2026 and split at 2022-01-01, the repository's optimise / verify boundary.
  Both halves were computed in one pass, and every year up to October 2026 informed earlier decisions, so the
  2022–2026 column is a robustness check, not a clean hold-out.
- **Survivorship.** Only stocks listed today are in the universe; names that later delisted (often the best shorts) are
  missing. That biases *absolute* short returns down. A–B comparisons on the same stocks are much less affected.

## 2. Study 1 — the stretch override

### 2.1 The index after a stretched-down close

| Index | Close vs 9-day EMA | Days | Episodes | 1-day mean | 3-day mean | 5-day mean | 5-day median | 5-day share up | t (5-day vs other days) |
|---|---|---|---|---|---|---|---|---|---|
| SPY | all days | 4,361 | — | +0.05% | +0.16% | +0.27% | +0.41% | 60% | — |
| | ≥1% below | 615 | 235 | +0.15% | +0.46% | +0.74% | +0.83% | 63% | +2.3 |
| | ≥2% below | 237 | 109 | +0.16% | +0.73% | +1.19% | +1.54% | 68% | +2.2 |
| | ≥3% below | 90 | 41 | +0.09% | +0.54% | +1.04% | +1.33% | 66% | +0.9 |
| | ≥4% below | 40 | 19 | +0.56% | +1.20% | +1.96% | +2.55% | 78% | +1.2 |
| QQQ | all days | 4,361 | — | +0.08% | +0.23% | +0.38% | +0.57% | 60% | — |
| | ≥1% below | 763 | 272 | +0.14% | +0.45% | +0.70% | +0.83% | 60% | +2.0 |
| | ≥2% below | 356 | 164 | +0.25% | +0.79% | +1.21% | +1.13% | 65% | +3.1 |
| | ≥3% below | 161 | 85 | +0.55% | +1.24% | +1.99% | +1.73% | 73% | +4.1 |
| | ≥4% below | 65 | 38 | +1.03% | +1.69% | +2.48% | +2.71% | 75% | +3.3 |
| Nifty 50 | all days | 4,257 | — | +0.05% | +0.13% | +0.23% | +0.32% | 56% | — |
| | ≥1% below | 744 | 252 | +0.02% | +0.19% | +0.35% | +0.47% | 57% | +0.7 |
| | ≥2% below | 262 | 126 | +0.20% | +0.39% | +0.43% | +0.58% | 59% | +0.4 |
| | ≥3% below | 85 | 45 | +0.33% | +0.60% | +0.56% | +0.96% | 58% | +0.3 |
| | ≥4% below | 29 | 15 | −0.02% | −0.38% | −1.33% | −0.32% | 45% | −0.6 |
| Nifty 500 | all days | 4,266 | — | +0.05% | +0.15% | +0.25% | +0.40% | 57% | — |
| | ≥1% below | 752 | 244 | +0.01% | +0.20% | +0.38% | +0.58% | 58% | +0.7 |
| | ≥2% below | 292 | 136 | +0.09% | +0.28% | +0.39% | +0.67% | 59% | +0.3 |
| | ≥3% below | 98 | 56 | +0.36% | +0.57% | +0.67% | +1.38% | 63% | +0.4 |
| | ≥4% below | 33 | 17 | +0.01% | −0.48% | −1.32% | +0.56% | 52% | −0.7 |

*Episodes* = separate runs of stretched days. The US bounce is real and grows with the stretch on QQQ; SPY's is smaller
and noisier past 2%. The Nifty indexes show no reliable bounce at any threshold.

### 2.2 Weak stocks after a stretched-down close

| Index | Close vs 9-day EMA | Days | Weak stocks per day | 1-day mean | 3-day mean | 5-day mean (other days) | 5-day share up | t | 5-day excess vs index | t |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | ≥1% below | 611 | 278 | +0.15% | +0.56% | +0.86% (+0.21%) | 57% | +1.7 | +0.13% | +0.6 |
| SPY | ≥2% below | 236 | 293 | +0.16% | +0.97% | +1.53% (+0.23%) | 62% | +1.7 | +0.35% | +0.9 |
| SPY | ≥3% below | 89 | 307 | +0.11% | +0.77% | +1.47% (+0.28%) | 60% | +0.7 | +0.46% | +0.5 |
| SPY | ≥4% below | 40 | 311 | +0.73% | +1.88% | +3.00% (+0.28%) | 66% | +1.1 | +1.04% | +0.7 |
| QQQ | ≥1% below | 760 | 266 | +0.09% | +0.39% | +0.64% (+0.23%) | 55% | +1.4 | −0.05% | +0.2 |
| QQQ | ≥2% below | 354 | 280 | +0.16% | +0.80% | +1.27% (+0.22%) | 59% | +2.2 | +0.06% | +0.5 |
| QQQ | ≥3% below | 159 | 296 | +0.42% | +1.31% | +2.28% (+0.23%) | 64% | +2.7 | +0.30% | +0.8 |
| QQQ | ≥4% below | 65 | 313 | +0.93% | +1.97% | +2.83% (+0.27%) | 64% | +1.8 | +0.36% | +0.5 |
| Nifty 50 | ≥1% below | 744 | 269 | −0.25% | −0.23% | −0.02% (+0.44%) | 48% | −1.4 | −0.37% | −3.5 |
| Nifty 50 | ≥2% below | 262 | 273 | −0.11% | −0.02% | +0.14% (+0.37%) | 50% | −0.3 | −0.29% | −1.6 |
| Nifty 50 | ≥3% below | 85 | 275 | −0.05% | +0.51% | +0.51% (+0.35%) | 54% | +0.1 | −0.06% | −0.3 |
| Nifty 50 | ≥4% below | 29 | 277 | −0.77% | −1.26% | −2.72% (+0.38%) | 43% | −1.0 | −1.39% | −1.6 |
| Nifty 500 | ≥1% below | 752 | 275 | −0.24% | −0.10% | +0.13% (+0.41%) | 49% | −0.9 | −0.25% | −2.9 |
| Nifty 500 | ≥2% below | 292 | 280 | −0.18% | −0.04% | +0.20% (+0.37%) | 51% | −0.3 | −0.19% | −1.4 |
| Nifty 500 | ≥3% below | 98 | 279 | +0.09% | +0.66% | +0.90% (+0.35%) | 56% | +0.4 | +0.23% | +0.3 |
| Nifty 500 | ≥4% below | 33 | 280 | −0.50% | −0.90% | −2.09% (+0.38%) | 46% | −0.9 | −0.77% | −1.3 |

*t* = stretched days vs all other days. **US:** weak stocks bounce *with* the index (raw t up to +2.7 on QQQ ≥3%), and
not significantly *more* than it (excess t ≤ 0.9) — Luk's "single stocks bounce with the index" holds, and a short
opened on the stretched day sits through it. **India:** the opposite in the first days — weak stocks lag the index
(1-day excess −0.25% to −0.37%, t −3 to −8 on ≥1%), so there is no immediate bounce to wait for. Part of this may
be slow price discovery in thinly traded names (catching up with yesterday's index move), which a trader could not
have shorted at the prices shown.

### 2.3 Shorting on the stretched day vs after the retest

An **episode** starts on the first stretched close after a non-stretched one, at least 10 sessions after the previous
episode. The weak stocks of that day are the candidates. Three entries:

- **A — the stretched day:** short at that close.
- **B — after the retest:** wait for the index's high to reach its 9-day EMA (within 20 sessions; it did in all but a
  handful of episodes), then short each stock at its **first close back below its own 9-day EMA** after having closed
  at or above it, on or after the retest day and within 30 sessions of the stretched day. About 95% of candidates got a
  B trigger.
- **Control:** the same stock trigger, started on days the index was within ±1% of its 9-day EMA.

Two measures. *10-day hold* — the return of each trade over the 10 sessions after its own entry. *Common exit* — both
A and B held to the same day, 20 sessions after the stretched day; B − A is then the price gained by waiting (positive =
waiting was better), net of the shorter time short. t is over episode averages.

| Index | Close vs 9-day EMA | Episodes | Trades (A / B) | A: 10-day short mean / median / win | B: 10-day short mean / median / win | B entry above A (median) | Sessions to B | **B − A, common exit**, 2009–2026 (t) | 2009–2021 (t) | 2022–2026 (t) |
|---|---|---|---|---|---|---|---|---|---|---|
| SPY | ≥1% below | 144 | 36,033 / 34,366 | −1.08% / −1.20% / 43% | −1.07% / −0.93% / 44% | +0.67% | 10 | +0.72 (+2.1, 142 ep) | +1.14 (+2.7, 102 ep) | −0.25 (−0.5, 40 ep) |
| SPY | ≥2% below | 74 | 20,126 / 19,271 | −1.74% / −1.63% / 41% | −1.67% / −1.56% / 41% | +1.27% | 11 | **+1.26** (+2.8, 74 ep) | +1.82 (+3.1, 52 ep) | +0.07 (+0.2, 22 ep) |
| SPY | ≥3% below | 29 | 8,048 / 7,766 | −1.30% / −1.41% / 43% | −1.62% / −1.53% / 41% | +1.15% | 10 | +0.99 (+1.1, 29 ep) | +1.00 (+0.7, 21 ep) | +0.96 (+0.9, 8 ep) |
| SPY | ≥4% below | 14 | 4,171 / 4,024 | +0.49% / −0.22% / 49% | −3.55% / −3.19% / 33% | +1.38% | 10 | +0.46 (+0.2, 14 ep) | −0.56 (−0.2, 11 ep) | +3.40 (+2.4, 3 ep) |
| SPY | control | | | | | | 6 | +0.01 (−0.3) | +0.05 (−0.1) | −0.01 (−0.2) |
| QQQ | ≥1% below | 169 | 41,086 / 39,195 | −0.77% / −0.93% / 44% | −0.82% / −0.82% / 45% | +0.62% | 10 | +0.53 (+1.3, 167 ep) | +0.72 (+1.8, 114 ep) | +0.14 (−0.5, 53 ep) |
| QQQ | ≥2% below | 101 | 26,284 / 24,898 | −1.89% / −2.04% / 39% | −1.20% / −1.26% / 42% | +1.10% | 11 | +0.95 (+1.7, 99 ep) | +1.38 (+2.3, 67 ep) | +0.14 (−0.3, 32 ep) |
| QQQ | ≥3% below | 57 | 16,089 / 15,181 | −2.21% / −2.34% / 39% | −1.61% / −1.54% / 42% | +1.60% | 10 | **+1.60** (+2.3, 55 ep) | +1.19 (+1.2, 32 ep) | +2.12 (+2.2, 23 ep) |
| QQQ | ≥4% below | 26 | 7,784 / 7,554 | −1.14% / −1.39% / 44% | −1.89% / −1.71% / 40% | +0.95% | 10 | +0.61 (+0.5, 26 ep) | −0.07 (−0.1, 17 ep) | +1.66 (+1.6, 9 ep) |
| QQQ | control | | | | | | 6 | +0.20 (+1.1) | +0.23 (+1.2) | +0.11 (+0.2) |
| Nifty 50 | ≥1% below | 160 | 38,808 / 36,373 | −0.49% / +0.15% / 51% | −0.20% / +0.54% / 53% | +0.22% | 11 | +0.75 (+1.4, 159 ep) | +1.11 (+1.9, 116 ep) | −0.20 (−0.5, 43 ep) |
| Nifty 50 | ≥2% below | 84 | 22,021 / 20,440 | −0.79% / −0.09% / 49% | −0.95% / +0.00% / 50% | +0.87% | 12 | **+1.52** (+1.9, 83 ep) | +1.37 (+1.1, 60 ep) | +1.88 (+2.0, 23 ep) |
| Nifty 50 | ≥3% below | 30 | 7,889 / 7,243 | −2.86% / −1.90% / 41% | −2.71% / −1.09% / 44% | +2.49% | 12 | +3.38 (+1.2, 30 ep) | +2.89 (+0.4, 22 ep) | +4.36 (+2.4, 8 ep) |
| Nifty 50 | ≥4% below | 11 | 2,650 / 2,330 | −0.96% / −0.51% / 48% | −1.51% / −0.59% / 47% | +2.98% | 12 | +5.74 (+0.4, 11 ep) | +5.77 (+0.3, 10 ep) | (1 ep) |
| Nifty 50 | control | | | | | | 6 | +0.65 (+3.2) | +0.86 (+3.5) | +0.11 (+0.1) |
| Nifty 500 | ≥1% below | 160 | 39,789 / 37,101 | −0.06% / +0.47% / 52% | −0.29% / +0.44% / 52% | +0.12% | 11 | +0.49 (+0.9, 157 ep) | +0.74 (+1.1, 114 ep) | −0.12 (−0.2, 43 ep) |
| Nifty 500 | ≥2% below | 90 | 23,956 / 22,358 | −0.92% / −0.24% / 48% | −0.86% / +0.04% / 50% | +0.91% | 12 | **+1.48** (+2.0, 89 ep) | +1.49 (+1.2, 61 ep) | +1.47 (+1.9, 28 ep) |
| Nifty 500 | ≥3% below | 40 | 10,705 / 9,991 | −1.98% / −1.41% / 43% | −1.41% / −0.14% / 49% | +2.45% | 11 | +2.95 (+1.6, 40 ep) | +2.84 (+0.9, 28 ep) | +3.16 (+2.1, 12 ep) |
| Nifty 500 | ≥4% below | 13 | 3,202 / 2,860 | +0.47% / −0.56% / 47% | −2.91% / −1.59% / 42% | +2.83% | 12 | +3.17 (+0.3, 13 ep) | +2.46 (−0.1, 11 ep) | (2 ep) |
| Nifty 500 | control | | | | | | 6 | +0.66 (+3.3) | +0.85 (+3.4) | +0.15 (+0.5) |

What it says:

1. **Waiting gets a higher short price.** B's entry was a median +0.1% to +3% above A's, about 10–12 sessions later.
   To a common exit that was worth +1.3 (SPY ≥2%), +1.6 (QQQ ≥3%), +1.5 (Nifty 50 and Nifty 500 ≥2%) points per trade,
   t 1.9–2.8. On ordinary days the same wait gained nothing in the US (+0.01, +0.20) and +0.65 in India — so most of
   the gain is the stretch, not the trigger.
2. **It does not pick better trades.** Over the 10 sessions after each entry, paired B − A differences had mixed
   signs and |t| < 2 in every row. The value is the price, nothing after it.
3. **Shorting weak stocks mostly lost money here** (10-day short means between −3.6% and +0.5%, win rates 33–53%).
   That is partly survivorship (§1) and partly a 2009–2026 bull market; it is not a test of a full short strategy
   with stops, which [the shorts page](system-shorts.md) would need.
4. **Thresholds.** The gain is clearest at **2% below** the 9-day EMA for SPY and the Nifty indexes, and **3% below**
   for QQQ (a more volatile index, so a 3% stretch on QQQ is about as unusual as 2% on SPY). Beyond 4% there are too few
   episodes (11–26) to say anything.
5. **2022–2026.** QQQ ≥3% (+2.1, t 2.2), Nifty 50 ≥2% (+1.9, t 2.0) and Nifty 500 ≥2% (+1.5, t 1.9) held up. **SPY ≥2%
   did not** (+0.07, t 0.2, 22 episodes).

The 2 November 2026 reading — QQQ 3.7% under its 9-day EMA, SPY 1.5% — sits in the QQQ ≥3% row: the row where the bounce
and the timing gain were both clearest.

### 2.4 The long-side mirror — index stretched up

| Index | Close vs 9-day EMA | Episodes | Index 5-day mean (all days) | t | Strong stocks 5-day excess vs index | t | **B − A, common exit** 2009–2026 (t) | 2022–2026 (t) | Control (t) |
|---|---|---|---|---|---|---|---|---|---|
| SPY | ≥1% above | 200 | +0.26% (+0.27%) | −0.2 | −0.05% | +0.9 | −0.26 (−3.3) | −0.13 (−1.1) | −0.20 (−2.6) |
| SPY | ≥2% above | 57 | +0.20% | −0.3 | +0.33% | +1.7 | +0.39 (−0.4) | −0.15 (−0.9) | |
| QQQ | ≥2% above | 111 | +0.23% (+0.38%) | −0.8 | −0.06% | +1.1 | −0.09 (−1.9) | +0.05 (−1.0) | −0.29 (−4.0) |
| QQQ | ≥3% above | 36 | +0.50% | +0.3 | +0.51% | +2.3 | −0.32 (−1.7) | −0.96 (−2.3) | |
| Nifty 50 | ≥1% above | 196 | +0.28% (+0.23%) | +0.6 | +0.55% | +3.1 | −0.69 (−5.1) | −0.84 (−3.6) | −0.64 (−5.9) |
| Nifty 50 | ≥2% above | 81 | +0.55% | +1.9 | +0.79% | +2.0 | −1.13 (−4.3) | −1.54 (−2.5) | |
| Nifty 50 | ≥3% above | 25 | +0.51% | +0.7 | +1.96% | +3.8 | −2.24 (−3.3) | −1.41 (−1.4) | |
| Nifty 500 | ≥2% above | 77 | +0.75% (+0.25%) | +2.7 | +0.68% | +2.0 | −1.09 (−4.6) | −1.26 (−2.2) | −0.59 (−5.5) |

Mirror definitions: strong stocks; A buys on the stretched-up close; B waits for the index's low to reach its 9-day
EMA, then buys at the stock's first close back above its own 9-day EMA. (t of a B − A row is over episode averages, so
its sign can differ from the pooled mean, as in SPY ≥2%.) Stretched up, **the index did not pull back** (US t ≈ 0; India
slightly *continued*), **strong stocks kept beating it** (India 5-day excess +0.5% to +2.0%, t 2–4), and **waiting to buy
on a retest cost** up to 2.2 points in India (little either way in the US), about as much as or more than waiting
on an ordinary day. The proposed rule only
covers the short side, and this is why it should stay that way.

### 2.5 Verdict — stretch override

**Tested — supported for shorts, as a timing rule; rejected for longs.**

- Don't open shorts on a close **≥2% under the 9-day EMA (SPY, Nifty 50, Nifty 500) or ≥3% (QQQ)**; wait for the index
  to retest its 9-day EMA and short weak stocks on their own failure back under their 9-day. Expected gain: a better
  entry, about +1.3 to +1.6 points (US) and +1.5 to +3 (India) per trade, on the measured history.
- It is a price rule, not a selection rule: the trades after entry were no better. And it says nothing about whether
  shorting weak stocks pays at all — in this survivorship-biased sample it did not.
- Weak spot: SPY ≥2% did not repeat in 2022–2026. Prefer QQQ's 3% reading in the US.
- In India there is no bounce to *see* in the first days (weak stocks fall further); the gain arrives later, inside the
  10–12 sessions the wait takes.
- Long side: do not delay buys because the index is stretched up.

Not tested: the hourly 9-day EMA retest (no intraday data stored), and the weekly 50 EMA "strong support" sub-rule.

## 3. Study 2 — narrow vs broad

### 3.1 Definitions

- **Spread** = cap-weighted index 20-session return − broad index 20-session return. US: SPY vs RSP (equal-weight).
  India has no equal-weight series stored, so two proxies: Nifty 50 vs **Nifty 500** (broad but still cap-weighted) and
  vs **Nifty Midcap 50**.
- **Cap-weighted falling**: its 20-session return < 0.
- **Narrow picture** (2 November 2026): cap-weighted falling, spread in its bottom fifth over the sample (cap-weighted
  lagging most: ≤ −0.95 pt US, ≤ −0.89 pt Nifty 500, ≤ −3.0 pt Midcap 50), and the broad index within 3% of its 252-session
  high. Also shown without the near-high condition.
- **Broad decline**: cap-weighted falling, broad index falling as much or more (spread ≥ 0) and more than 5% under its
  high.
- **Forward**: the cap-weighted index's return over 21, 63 and 126 sessions (1, 3, 6 months) and its worst close within
  6 months. *Spells* = runs separated by 21+ sessions without the condition — the real number of independent cases.
  t = Newey–West, lag = horizon, condition vs all other days. The bottom-fifth cut uses the whole sample (a small
  look-ahead).

### 3.2 Results

**US — SPY vs RSP, 2004–2026 (SPY forward)**

| Condition | Days | Spells | 1m median (t) | 3m median / share up (t) | 6m median (t) | 6m median worst drawdown |
|---|---|---|---|---|---|---|
| All days | 5,664 | — | +1.4% | +3.5% / 72% | +6.2% | −4.0% |
| SPY falling (20-session) | 1,961 | 75 | +1.9% (+1.5) | +4.2% / 73% (+1.4) | +7.0% (+1.0) | −4.4% |
| Narrow picture: SPY lagging, RSP within 3% of high | 104 | 20 | +1.8% (+0.0) | +4.9% / 89% (+1.8) | +11.0% (+0.5) | −4.3% |
| Narrow, any distance from high | 335 | 40 | +0.5% (−1.8) | +4.5% / 76% (+0.5) | +6.0% (−0.2) | −7.7% |
| Broad decline | 758 | 53 | +3.1% (+3.1) | +5.9% / 71% (+1.4) | +9.7% (+1.7) | −4.5% |
| Other falling days | 868 | 76 | +1.6% (−0.1) | +3.4% / 74% (−0.3) | +5.9% (−1.0) | −4.0% |

**India — Nifty 50 vs Nifty 500, 2008–2026 (Nifty 50 forward)**

| Condition | Days | Spells | 1m median (t) | 3m median / share up (t) | 6m median (t) | 6m median worst drawdown |
|---|---|---|---|---|---|---|
| All days | 4,434 | — | +1.1% | +3.4% / 66% | +5.7% | −4.9% |
| Nifty 50 falling | 1,765 | 54 | +1.0% (−0.0) | +3.5% / 66% (+0.6) | +7.0% (+1.9) | −5.4% |
| Narrow picture | 116 | 25 | +0.6% (−0.9) | +2.5% / 64% (−1.0) | +8.8% (+0.4) | −3.1% |
| Narrow, any distance from high | 274 | 47 | +1.0% (−0.3) | +2.5% / 64% (−1.0) | +8.3% (+1.6) | −4.2% |
| Broad decline | 728 | 45 | +1.4% (+0.3) | +4.8% / 73% (+1.5) | +8.3% (+2.0) | −5.1% |
| Other falling days | 763 | 69 | +0.8% (−0.3) | +2.4% / 60% (−1.1) | +5.2% (−0.8) | −6.6% |

**India — Nifty 50 vs Nifty Midcap 50, 2008–2026 (Nifty 50 forward)**

| Condition | Days | Spells | 1m median (t) | 3m median / share up (t) | 6m median (t) | 6m median worst drawdown |
|---|---|---|---|---|---|---|
| All days | 4,406 | — | +1.1% | +3.4% / 66% | +5.8% | −4.9% |
| Nifty 50 falling | 1,758 | 52 | +1.1% (+0.2) | +3.4% / 66% (+0.6) | +7.0% (+2.0) | −5.4% |
| Narrow picture | 90 | 19 | −0.2% (−1.8) | +2.1% / 65% (−1.6) | +10.1% (+0.4) | −6.9% |
| Narrow, any distance from high | 196 | 41 | +0.2% (−1.1) | +1.8% / 58% (−1.6) | +8.7% (+1.7) | −6.8% |
| Broad decline | 955 | 55 | +1.8% (+0.8) | +4.4% / 70% (+1.7) | +7.3% (+2.0) | −5.4% |
| Other falling days | 607 | 59 | +0.4% (−0.3) | +2.7% / 61% (−1.2) | +5.6% (−1.1) | −5.2% |

**Split at 2022 — the two conditions that matter (cap-weighted index forward)**

| Pair | Condition | 2009–2021: spells · 1m median (t) · 3m median (t) | 2022–2026: spells · 1m median (t) · 3m median (t) |
|---|---|---|---|
| SPY vs RSP | Narrow picture | 13 · +2.4% (+2.9) · +4.6% (+2.2) | 7 · +0.2% (−1.3) · +5.5% (+0.6) |
| SPY vs RSP | Broad decline | 41 · +2.8% (+1.9) · +5.1% (+0.9) | 12 · +4.8% (+4.8) · +9.4% (+2.2) |
| Nifty 50 vs Nifty 500 | Narrow picture | 19 · −1.7% (−1.9) · −0.1% (−1.6) | 6 · +2.5% (+1.7) · +5.0% (+2.3) |
| Nifty 50 vs Nifty 500 | Broad decline | 31 · +1.8% (+0.2) · +5.4% (+1.3) | 14 · +0.6% (+0.7) · +4.2% (+1.2) |
| Nifty 50 vs Midcap 50 | Narrow picture | 11 · −3.5% (−2.8) · −2.4% (−2.0) | 8 · +1.5% (+1.2) · +2.5% (+1.4) |
| Nifty 50 vs Midcap 50 | Broad decline | 39 · +2.2% (+0.4) · +4.3% (+1.4) | 17 · +1.2% (+1.4) · +4.5% (+1.1) |

(US first window starts 2004.) By spread fifth over all days, SPY's forward returns were U-shaped and flat within noise
(3-month t between −1.3 and +1.7 in every fifth); the same held for both Indian pairs.

What it says:

1. **US: the narrow picture was not followed by worse SPY returns.** If anything better (3-month median +4.9%, 89% of
   cases up), with drawdowns no deeper than average — but only 20 spells, t < 2, and the 1-month edge vanished after
   2021.
2. **Broad declines were followed by the stronger rebounds** (US 1-month median +3.1%, t 3.1; India 3-month +4.4–4.8%).
   The damage of a broad decline is mostly the decline already taken.
3. **India flips sign.** The Midcap narrow picture preceded a weak quarter before 2022 (1-month −3.5%, t −2.8, 11
   spells — January 2020 among them, −21.6% over 3 months) and a good one after (+1.5%, 8 spells). Eleven cases and one
   pandemic do not make a rule.

### 3.3 The reading on 2 November 2026

| Pair | Cap 20-session | Broad 20-session | Spread | Broad from 252-session high | Rank |
|---|---|---|---|---|---|
| SPY vs RSP | −2.9% | +4.2% | −7.1 pt | −1.3% | 10 of 5,895 days since 2003 were this wide or wider |
| Nifty 50 vs Nifty 500 | +4.5% | +1.8% | +2.8 pt | −7.7% | 99th percentile (the *opposite* picture) |
| Nifty 50 vs Midcap 50 | +4.5% | −0.7% | +5.3 pt | −9.6% | 94th percentile |

The US gap is among the widest in RSP's history. Days with a gap of 4 points or more (85 of them) clustered in
2008–09 and 2020–21, when equal-weight led a rebound, with a few in 2003 and 2024; SPY's 3-month median after them was
+7.4% — too few spells to read as a signal. India today shows the reverse: the large caps leading while the broad market sits 8–10%
under its high.

### 3.4 Verdict — narrow vs broad

**Tested — rejected as a forecast; keep as a description.** "Cap-weighted falling while equal-weight holds near its
high" was not followed by worse — or reliably better — index returns or drawdowns than broad declines or ordinary days,
over 1, 3 or 6 months, in either country; where a sign appeared it reversed between 2009–2021 and 2022–2026. Use the
reading for what it is: it tells you **where** the selling is (a group, not the market), which decides *what to hunt*
(shorts in the breaking group, a watchlist of stocks holding up) — not how much to expect from the index next.

## 4. Limits

- **Survivorship**: today's listed stocks only. Delisted losers are missing, which flatters longs and hurts shorts.
- **No costs, no borrow, no stops**. Short borrow in India's cash market is not generally available for swing holds
  (shorts there mean futures or intraday), so the India short results are a price study, not a tradable record.
- **India's stock results are skewed**: strong-stock means of +1% to +4% sit on medians near zero, so a few large
  winners carry them. The universe also reaches into thinly traded names, whose slow prices may explain part of the
  "weak stocks keep falling" result.
- **Overlap**: index stretched days come in runs; 6-month breadth windows overlap heavily. Newey–West helps but the
  honest sample is the spell count — 20–25 narrow-picture spells per pair.
- **One pass, both windows**: the thresholds (2% / 3%) were read off the full-period table with the split visible, so the
  2022–2026 column is not an untouched hold-out. The forward data from here is.

## 5. Reproduce

Scratch scripts (not in the repository), run from `scripts/` with `PYTHONPATH=.:<scratch dir>`:
`load_panel.py us india` (price panels from `cache.load_many_cached`, common stocks from `breadth.eligible`),
`stretch_study.py us india`, `control.py us india`, `breadth_study.py`, `condense.py`. A copy is in the shared session
notes for this work; they would become `swing_screener/research_daily_review.py` if the study is to be re-run on new data.
