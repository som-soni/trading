# Moving averages — SMA, EMA, WMA, DEMA, Hull, KAMA, the Alligator and ribbons

**In short**

- Every moving average makes the same trade: a smoother line reacts later, and a faster line reacts to noise. No design escapes it.
- Lag has a simple measure: the average age of the prices inside the line. A 20-day SMA is about 9.5 days behind in a steady trend.
- The faster designs (EMA, WMA, DEMA, Hull, KAMA) turned sooner after a swing top or bottom. They also crossed the price far more often.
- The Alligator and ribbons are several averages drawn together. They show whether a trend is ordered or tangled, still with the lag of their slowest line.
- Choose one average for the job, and judge it by both numbers: how late it turns, and how often it is crossed.

This guide goes past the simple and exponential averages into the designs built to reduce their lag. It measures what each design gains and what it pays. The basics are in [Indicators — trend and volatility: moving averages, ATR and ADX](learn-price-indicators.md). How to trade with averages is in [Moving-average trend following](learn-strat-ma-trend.md) and [Pullback to a moving average](learn-strat-pullback-ma.md). For the whole set of indicator families, see [Indicators — the map](learn-ind-map.md).

---

## 1. What this family measures

On 8 April 2025 Apple closed at $172.42, after falling about a third from its December high. Six common 20-day averages read as follows that evening.

| Average (20 days unless noted) | Value | Close below it by |
|---|---|---|
| Simple (SMA) | $211.84 | 19% |
| Exponential (EMA) | $210.59 | 18% |
| Weighted (WMA) | $208.06 | 17% |
| Double exponential (DEMA) | $197.66 | 13% |
| Hull | $200.55 | 14% |
| Kaufman adaptive (KAMA, 10/2/30) | $198.95 | 13% |

All six describe the same 20 sessions of prices. They disagree by $14 because each weights those prices differently. The SMA still counted the $220s of late March in full. The DEMA and KAMA were already about $13 closer to the price.

A moving average answers one question: **which way has the price been going, with the day-to-day noise removed?** Every design answers it with a delay, and the delay is the price of the smoothing.

### 1.1 Lag is the average age of the prices

Think of each average as a set of weights on past closes. Find where those weights balance, like a seesaw. That balance point is how many days old the "typical" price inside the average is.

For an SMA of n days, every close counts equally. The balance point sits in the middle, (n − 1) ÷ 2 days back. In a steady trend, that is how far behind the price the line runs.

| Average, n = 20 | Weights on past closes | Balance point (lag in a steady trend) |
|---|---|---|
| SMA | Equal | 9.5 days |
| EMA (α = 2 ÷ (n + 1)) | Falling by a fixed share each day | 9.5 days |
| WMA | Falling in a straight line: 20, 19 … 1 | 6.3 days |
| Wilder's smoothing (α = 1 ÷ n) | Falling slowly | 19 days |
| DEMA | Two EMAs combined so the lags cancel | About 0 days |
| Hull | Two WMAs combined, then smoothed again | About 1 day |

The last two look like magic. They are not. They reach near-zero lag by projecting the recent slope forward. In a straight-line trend, that projection is right. When the trend bends, the projection keeps going the old way for a few bars, and the line overshoots.

### 1.2 The one trade-off

A line that turns sooner also turns on moves that reverse the next week. So every design sits somewhere between two failures:

- **Too slow:** it confirms a turn after much of the move is gone.
- **Too fast:** it turns, and is crossed by the price, on ordinary noise.

Section 11 measures both on hundreds of stocks. The short answer: the faster designs bought a few sessions of earlier turns with many more crossings.

```series
title: Apple, late 2024 to mid-2025 — four 20-period averages through a top and a bottom
from: 2024-10-01
to: 2025-06-30
line: us:AAPL | Apple
line: us:AAPL@sma(length=20).ma | SMA 20
line: us:AAPL@ema(length=20).ma | EMA 20
line: us:AAPL@hma(length=20).ma | Hull 20
line: us:AAPL@kama.ma | KAMA (10, 2, 30)
mark: 2024-12-26 | Top $259.02
mark: 2025-04-08 | Low $172.42
caption: After the top, KAMA turned down two sessions later and the SMA seven. After the April low, KAMA and Hull turned up within five sessions; the SMA took seventeen. In the choppy weeks after the low, KAMA went almost flat.
```

Sessions until each line turned, on this chart:

| Line | Turned down after the top | Close that day | Turned up after the low | Close that day |
|---|---|---|---|---|
| SMA 20 | 7 sessions | $242.21 | 17 sessions | $205.35 |
| EMA 20 | 4 | $243.85 | 10 | $204.60 |
| Hull 20 | 3 | $250.42 | 5 | $202.14 |
| KAMA (10, 2, 30) | 2 | $252.20 | 4 | $202.52 |

| Times the close crossed the line, Oct 2024 – Jun 2025 | SMA 20 | EMA 20 | Hull 20 | KAMA |
|---|---|---|---|---|
| Apple | 20 | 30 | 29 | 40 |

One stock, one turn: an illustration, not a measurement. Note that the fastest turner here, KAMA, was also crossed most often.

## 2. SMA and EMA — the two basics

The simple average gives equal weight to the last n closes. The exponential average gives the newest close the most weight, with α = 2 ÷ (n + 1). Both are explained with worked numbers in [Indicators — trend and volatility: moving averages, ATR and ADX](learn-price-indicators.md). Two points matter for the rest of this guide.

**An SMA's direction depends on two closes.** Each day it changes by (today's close − the close that drops out) ÷ n. So it turns down as soon as the price falls below where it was n sessions ago, whatever happened in between.

**An EMA and an SMA of the same length have the same average age.** The EMA reacts faster to the last few bars, but it never forgets fully. It carries a thin tail of very old prices.

## 3. WMA — weights in a straight line

The weighted moving average answers the same question as the SMA, with recent days counting more. The newest close gets the most weight, the one before a little less, and so on down to the oldest, in equal steps.

```
WMA = (n × C(today) + (n − 1) × C(yesterday) + … + 1 × C(n − 1 days ago)) ÷ (n × (n + 1) ÷ 2)
Default: 20 closes. Lag in a steady trend: (n − 1) ÷ 3 days.
```

**Worked example.** On Apple's top day, 26 December 2024, the close was $259.02. The 20-day SMA was $247.49 and the EMA $247.85. The WMA was $250.87. The WMA sat closer to the price because the prices inside it are younger on average: 6.3 days against 9.5.

Unlike the EMA, the WMA forgets completely: a close older than n days has no weight at all. That makes it a building block for the Hull average (section 6). On its own it is rarely used.

## 4. Wilder's smoothing (RMA) — the slow average inside RSI and ATR

Wilder's smoothing answers nothing new by itself. It matters because it sits inside RSI, ATR and ADX, and because its length misleads.

```
RMA(today) = RMA(yesterday) + (value − RMA(yesterday)) ÷ n
Same as an EMA of length 2n − 1.  RSI14 and ATR14 use n = 14, i.e. an EMA of about 27 days.
```

J. Welles Wilder used it in 1978 for RSI, ATR and ADX. So "ATR14" remembers about as much as a 27-day EMA. When a 14-day ATR seems slow to react to a volatility spike, this is why. The Alligator (section 8) also uses this smoothing; there it is called the smoothed moving average.

## 5. DEMA — two EMAs combined to cancel the lag

Patrick Mulloy's double exponential moving average (published in 1994) asks: can an EMA be made to keep up with a steady trend? It takes an EMA, then an EMA of that EMA, and combines the two.

```
E1 = EMA(close, n);  E2 = EMA(E1, n)
DEMA = 2 × E1 − E2
Default: n = 20.
```

Why it works: in a steady trend, E1 lags the price by some amount L, and E2 lags by about 2L. Twice E1 minus E2 puts the line back on the price. Despite the name, DEMA is not "an EMA applied twice". It is a correction that uses the second EMA to estimate the first one's lag.

**Worked example.** At Apple's April 2025 low, the 20-day DEMA was $197.66, against $210.59 for the EMA of the same length. A week later, on 15 April, the stock had bounced to $202.14. The DEMA had already turned up; the EMA was still falling.

**Pitfall:** the correction assumes the trend continues. In a sideways market the "lag" it removes is just noise, and DEMA follows the noise. Across the sample, the 20-day DEMA was crossed by the close about 47 times a year (section 11).

## 6. Hull — a fast WMA with its lag subtracted, then smoothed

Alan Hull's moving average asks the same question as DEMA, using weighted averages. It cancels the lag the same way, then smooths the result over a short window to remove the jitter.

```
raw  = 2 × WMA(close, n ÷ 2) − WMA(close, n)
Hull = WMA(raw, √n)
Common default: n = 9 (n = 20 and 50 are used for swing trading).
```

**Worked example.** On 26 February 2025 Apple closed at $240.36, after falling from $247.04 the day before. The 20-day Hull read $248.63. That was **above every close of the previous 20 sessions**. The line had projected the late-February rise forward and overshot the price.

On 21 March 2025 it did the same downward: Hull $208.22, below every close of the past 20 sessions. Over October 2024 to June 2025, the 20-day Hull sat outside the range of recent closes on 13 sessions. An SMA can never do that; an average of closes always lies within their range.

**Pitfall:** at longer lengths, the projection can make Hull *slower* to confirm a turn. Across the sample, the 50-day Hull took a median 7 sessions to turn after a swing top or bottom. The 50-day SMA took 6 (section 11). After a long trend, Hull keeps projecting the old slope for a while.

## 7. KAMA — an average that slows down in noise

Perry Kaufman's adaptive moving average asks: how much of the recent movement was trend, and how much was noise? It moves fast when the price travels in a straight line and almost stops when the price chops.

The measure is the **efficiency ratio (ER)**: the net move over n days, divided by the sum of every daily move.

```
ER = |close − close n days ago| ÷ sum of |daily change| over the n days      (0 = pure noise, 1 = straight line)
fast = 2 ÷ (2 + 1),  slow = 2 ÷ (30 + 1)
SC   = (ER × (fast − slow) + slow)²
KAMA(today) = KAMA(yesterday) + SC × (close − KAMA(yesterday))
Default: n = 10, fast 2, slow 30.
```

**Worked example (Apple).** Each line shows the 10 days ending that date.

| Date | Net move | Sum of daily moves | ER | Smoothing used (SC) | Acts like an EMA of about |
|---|---|---|---|---|---|
| 26 Dec 2024 (top) | $12.53 | $23.39 | 0.54 | 0.150 | 12 days |
| 8 Apr 2025 (low) | $51.33 | $67.95 | 0.76 | 0.27 | 6 days |
| 15 Apr 2025 | $21.05 | $99.51 | 0.21 | 0.037 | 53 days |

During the fall into the April low, the moves were mostly in one direction, so KAMA tracked the price closely. In the week after, Apple swung up and down by large amounts. KAMA barely moved, from $198.95 to $198.60, while the stock rose 17%.

**Pitfall:** a nearly flat line is crossed by every swing. KAMA was crossed 40 times on the Apple chart, more than any other line. Its quick "turns" are often a tiny tick of an almost flat line.

## 8. The Williams Alligator — three averages of the bar's midpoint

Bill Williams' Alligator asks: is the market trending, or sleeping? It draws three smoothed averages of each bar's midpoint, (high + low) ÷ 2, each pushed forward in time.

```
Jaw   (blue)  = smoothed average (Wilder) of the midpoint, 13 bars, drawn 8 bars forward
Teeth (red)   = the same, 8 bars, drawn 5 bars forward
Lips  (green) = the same, 5 bars, drawn 3 bars forward
```

Williams' reading: when the three lines are tangled, the Alligator is "sleeping" and there is no trade. When they fan out in order — lips above teeth above jaw — it is "eating" an uptrend. Lips below teeth below jaw is a downtrend.

The forward shift is a display choice: each line is drawn as if its value belonged to a later bar. On today's bar, the jaw shows the 13-bar average from 8 bars ago. That adds lag on top of the smoothing.

```series
title: Reliance Industries, Oct 2024 – Aug 2025 — the Williams Alligator
from: 2024-10-01
to: 2025-08-29
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@alligator.jaw | Jaw (13, shifted 8)
line: india:RELIANCE.NS@alligator.teeth | Teeth (8, shifted 5)
line: india:RELIANCE.NS@alligator.lips | Lips (5, shifted 3)
mark: 2025-04-07 | Lines read "up", price below all three
caption: The lines fanned downward in late 2024, were mostly tangled from January to April 2025, then fanned upward from late April to mid-July. On 7 April the order still read up, yet the close was 6–8% below all three lines.
```

**Worked example (Reliance).**

| Date | Close | Lips | Teeth | Jaw | Order |
|---|---|---|---|---|---|
| 14 Nov 2024 | ₹1,267.60 | ₹1,308.17 | ₹1,335.29 | ₹1,369.65 | Down, and the close below all three |
| 7 Apr 2025 | ₹1,165.70 | ₹1,266.74 | ₹1,262.36 | ₹1,245.27 | Up, but the close far below |
| 30 Jun 2025 | ₹1,500.60 | ₹1,449.03 | ₹1,437.18 | ₹1,422.20 | Up, and the close above all three |

The three lines were ordered upward for 59 sessions from 28 April to 18 July 2025. The stock rose from ₹1,368.80 to ₹1,476.00 over that run. Between mid-January and late April the order changed about 15 times, and no reading lasted long.

**Pitfall:** the 7 April row is the Alligator's weakness. The lines describe the bars of one to two weeks earlier. A sharp fall can take the price below all three while their order still says "up". Read the order together with where the price sits.

## 9. Moving-average ribbons — many lengths at once

A ribbon asks the same question as the Alligator with plain averages: are the short, medium and long trends lined up? The usual form draws four simple or exponential averages, from 20 days out to 200. Daryl Guppy's multiple moving averages use two groups of six EMAs, a fast group and a slow group.

The reading is the order and the spacing:

- **Stacked up** (20 above 50 above 100 above 200) and spreading: a mature uptrend.
- **Tangled:** a range, or a trend changing.
- **Stacked down:** a downtrend.

```series
title: Microsoft, 2025–2026 — a 20/50/100/200-day SMA ribbon through a full cycle
from: 2025-06-01
to: 2026-10-27
line: us:MSFT | Microsoft
line: us:MSFT@ribbon.m1 | 20-day
line: us:MSFT@ribbon.m2 | 50-day
line: us:MSFT@ribbon.m3 | 100-day
line: us:MSFT@ribbon.m4 | 200-day
mark: 2025-10-28 | Top $542.07
mark: 2026-06-25 | Low $352.83
caption: The ribbon stayed stacked up for three weeks after the October 2025 top, then tangled. It was stacked down only from February 2026, and stacked up again from mid-September 2026, after the stock had already risen more than 40% from its low.
```

| Microsoft ribbon state | From | To | Close at start → end |
|---|---|---|---|
| Stacked up | 8 Oct 2025 | 18 Nov 2025 | $524.80 → $493.80 |
| Tangled | 19 Nov 2025 | 11 Feb 2026 | $487.10 → $404.40 |
| Stacked down | 12 Feb 2026 | 24 Apr 2026 | $401.80 → $424.60 |
| Tangled, then stacked up | 27 Apr 2026 | 27 Oct 2026 | $424.80 → $531.30 |

A fully stacked ribbon is a description of a trend that is already old. It has the lag of its slowest line, the 200-day. Traders use it as a filter on which side to trade, not as a timing signal.

## 10. The family side by side

| Average | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| SMA | Average price, equal weights | 20, 50, 200 | The price | Trend filters; pullback levels |
| EMA | Average price, recent weighted | 10, 20/21, 50 | The SMA of the same length | Short-term trend; trailing exits |
| WMA | Same, straight-line weights | 20 | The EMA | Building block for Hull |
| Wilder (RMA) | A slow EMA | 14 (≈ 27-day EMA) | A longer EMA | Inside RSI, ATR, ADX, Alligator |
| DEMA | Average with the lag cancelled | 20 | The price, with noise | Faster crossover systems |
| Hull | Same, with WMAs, then smoothed | 9; 20 | The price, with overshoot | Turn spotting on short swings |
| KAMA | Trend speed that adapts to noise | 10, 2, 30 | An EMA in trends; a flat line in chop | Trend line that goes quiet in ranges |
| Alligator | Trending or sleeping? | 13/8/5, shifted 8/5/3 | A ribbon of slow averages | Stay out while the lines tangle |
| Ribbon | Short and long trends aligned? | 20/50/100/200 | Its slowest line | Which side to trade |

**What they repeat.** A raw average just tracks the price, so it has no useful correlation with momentum readings. The *distance* from an average is different. The close's distance from its 50-day correlated 0.88 with RSI14 in US stocks, and 0.89 in Indian stocks. So "how far above the average" is a momentum reading, covered in [Momentum II — how fast the price is changing](learn-ind-momentum-rate.md).

## 11. What the evidence says

> **Method.** 300 US stocks (random, fixed seed) and 147 Indian stocks, each with at least 1,500 sessions since 2015 and high daily turnover. Daily bars, 2015 to October 2026. Turns: the tops and bottoms of a 10% zig zag (a swing that reversed by at least 10%). For each turn, the sessions until the average first moved the other way. Crossings: days the close switched sides of the average. Each figure is the median across stocks.

| Average | US crossings a year | US sessions to turn | India crossings a year | India sessions to turn |
|---|---|---|---|---|
| SMA 20 | 30 | 6 | 29 | 6 |
| EMA 20 | 34 | 3.5 | 32 | 4 |
| WMA 20 | 38 | 4 | 37 | 4 |
| DEMA 20 | 47 | 3 | 46 | 3 |
| Hull 20 | 55 | 4 | 54 | 4 |
| KAMA (10, 2, 30) | 36 | 3 | 35 | 3 |
| SMA 50 | 18 | 6 | 17 | 6 |
| EMA 50 | 21 | 5 | 20 | 5.5 |
| WMA 50 | 24 | 6 | 23 | 6 |
| DEMA 50 | 30 | 4 | 29 | 5 |
| Hull 50 | 33 | 7 | 32 | 7 |

What it shows:

- **Faster designs turned sooner.** At 20 days, every design beat the SMA by two or three sessions. The two markets agree closely.
- **They paid in crossings.** The 20-day Hull was crossed nearly twice as often as the 20-day SMA. Each crossing is a potential false signal for a crossover rule.
- **There is no free lunch.** No design turned earlier *and* was crossed less often than the SMA.
- **Hull 50 was the exception the wrong way.** It was crossed more often than the 50-day SMA *and* turned later. Its forward projection keeps it going after a long trend ends.
- **KAMA came closest to a good deal.** It turned a session sooner than Hull 20, with about two-thirds of its crossings. Many of its turns are small ticks of a flat line, though.

Published research. The academic work on moving-average rules is mostly on simple averages. Brock, Lakonishok and LeBaron (1992) found simple moving-average rules on the Dow had predictive power over 1897–1986. Sullivan, Timmermann and White (1999) showed the best rule did not hold up after 1986, once the many rules tried were allowed for. Trend filters' main measured benefit on indices is avoiding the deepest drawdowns ([Moving-average trend following](learn-strat-ma-trend.md)).

**Limits.** The sample is today's listed stocks, so firms that failed are missing. Turn lag and crossings describe the lines, not the profit of any rule. No costs are included. A 10% swing is one definition of a turn; smaller swings would favour the faster lines less.

## 12. Checklist

- [ ] What is this average for: a trend filter, a pullback level, or a trailing exit?
- [ ] How old are the prices inside it? Have I used (n − 1) ÷ 2 to see how far behind it runs?
- [ ] If I chose a fast design to turn sooner, do I accept roughly twice as many crossings?
- [ ] Is the line nearly flat? Then crossings and "turns" mean little.
- [ ] With Hull or DEMA: has the line run outside the recent prices — an overshoot, not a level?
- [ ] With the Alligator or a ribbon: does the price agree with the order of the lines, or is the order a week old?
- [ ] Am I comparing two averages that are really the same line at different speeds?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the smoothing inside RSI, ATR and ADX.
- Perry Kaufman, *Smarter Trading* (1995) and *Trading Systems and Methods* — the adaptive moving average and the efficiency ratio.
- Patrick Mulloy's articles in *Technical Analysis of Stocks & Commodities* (1994) — DEMA.
- Bill Williams, *Trading Chaos* (second edition, 2004) — the Alligator.
- Brock, Lakonishok and LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns" (*Journal of Finance*, 1992).
- Sullivan, Timmermann and White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap" (*Journal of Finance*, 1999).
