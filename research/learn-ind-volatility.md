# Volatility indicators — ATR, standard deviation, BandWidth, historical volatility, Mass Index, Ulcer Index, TTM Squeeze

**In short**

- Volatility indicators measure how much a price swings, not which way. They answer "how big are the moves?" and "is the stock quieter or wilder than usual?"
- Most of them repeat each other. BandWidth and the standard deviation of closes correlated at 0.98; historical volatility and ATR % at 0.88. Pick one.
- Two are different. The Mass Index watches the daily range widen and is the most independent of the family. The Ulcer Index counts only falls, so it moves against momentum.
- None tells you the direction of the next move. After a TTM Squeeze "fired", the next 20 sessions moved no more than usual, in either market.
- Use them to size stops and positions, to compare stocks, and to describe a base. Not as entry signals.

This guide covers the volatility family. ATR and ATR % are explained in depth in [Indicators — trend and volatility: moving averages, ATR and ADX](learn-price-indicators.md); here they get a summary. Bollinger Bands, Keltner channels and their positions are in [Bands and channels — Bollinger, Keltner, Donchian, envelopes and ATR bands](learn-ind-bands-channels.md). For the index's own volatility, the VIX, see [Volatility and sentiment — what fear costs, and when it matters](learn-health-volatility.md). For how the families fit together, see [Indicators — the map](learn-ind-map.md).

---

## 1. What this family measures

In the first week of April 2025, Apple fell from about $224 to $172 in four sessions. Then it rose 15% in a day. Every volatility indicator jumped. Here is Apple on five days, with each reading at its default setting:

| Apple (AAPL) | 14 Feb 2025 | 8 Apr 2025 | 22 Apr 2025 | 1 Jul 2025 | 27 Oct 2026 |
|---|---|---|---|---|---|
| Close | $244.60 | $172.42 | $199.74 | $207.82 | $347.10 |
| ATR % (14) | 2.5% | 5.5% | 5.1% | 2.2% | 1.8% |
| Standard deviation of closes (20) | $6.28 | $14.27 | $15.26 | $2.91 | $5.20 |
| Bollinger BandWidth (20, 2) | 10.8% | 27.0% | 29.9% | 5.8% | 6.1% |
| Historical volatility (20) | 29% | 50% | 78% | 18% | 13% |
| Mass Index (9, 25) | 26.4 | 26.2 | 26.4 | 24.4 | 24.4 |
| Ulcer Index (14) | 2.8 | 10.6 | 13.4 | 2.3 | 0.6 |
| TTM Squeeze | off | off | off | **on** | off |

Read across a row and the story is the same: calm in February, a storm in April, very quiet by July. That is the whole family's question: **how big are the moves, compared with this stock's own past?**

None of these numbers says up or down. On 8 April Apple was falling; on 22 April it was rising. Both days read as "very volatile". The one exception is the Ulcer Index, which only counts falls (section 7).

The rows also differ in units. ATR and standard deviation are in dollars. ATR %, BandWidth and historical volatility are percentages, so they compare stocks. The Mass Index and Ulcer Index have their own scales.

## 2. ATR and ATR % — the daily swing

**The question:** how far does this stock move in a typical day, gaps included?

The **true range** of a day is the largest of the high minus the low, or the distance from the previous close to the high or to the low. ATR averages it over 14 days with Wilder's smoothing. **ATR %** divides by the close, so a $50 stock and a $500 stock can be compared.

```
true range = max(high − low, |high − previous close|, |low − previous close|)
ATR        = Wilder average of the true range over 14 days
ATR %      = 100 × ATR ÷ close
```

Apple's ATR % went from 2.5% in February 2025 to 5.5% on 8 April. By October 2026 it was back to 1.8%. Stops, position sizes and "too quiet" or "too wild" filters are usually set in ATR. All of that is in [the trend and volatility indicators guide](learn-price-indicators.md), with stop placement in [Stops and exits — where a trade is wrong, and how it ends](learn-risk-stops-exits.md).

ATR is the reference reading in this guide's evidence. Its closest twin is historical volatility (section 5).

## 3. Standard deviation of closes

**The question:** how spread out have the last 20 closes been around their average?

Take five closes that average 100. Find each close's gap from the average, square the gaps, average the squares, and take the square root:

```
closes:   98, 100, 102, 100, 100      average 100
gaps:     −2,   0,  +2,   0,   0
squares:   4,   0,   4,   0,   0      mean 1.6 → standard deviation = √1.6 ≈ 1.26
```

The usual default is 20 closes. Some packages divide by 20 (population), others by 19 (sample); the two differ by about 2.6%. The version used here divides by 20.

**Worked example.** On 1 July 2025, Apple's 20 closes had a standard deviation of $2.91, on an average of $200.96. That is 1.4% of the price. On 8 April it was $14.27, or 8.3% of the close.

**What it measures — and a trap.** It measures the spread of price *levels*, not the size of daily moves.

Picture a stock that rises exactly 1% every day for 20 days. It never has a big day. Yet its closes spread from 100 to about 121. The standard deviation is about 6.3, over 5% of the price. **A steady trend looks volatile on this measure.** That is why it is related to ADX, the trend-strength reading (0.40 in the US, 0.45 in India).

**What it repeats.** Divided by the close, it correlated at 0.98 with Bollinger BandWidth: they are the same number. With ATR % it was 0.73 in the US and 0.69 in India.

**Pitfall.** In price units it cannot compare stocks, and it grows with the price. Divide by the close, or use BandWidth.

## 4. Bollinger BandWidth

**The question:** how wide are the Bollinger Bands, as a share of the price?

Bollinger Bands sit 2 standard deviations above and below a 20-day average. **BandWidth** is the distance between them, divided by the middle line:

```
upper, lower = 20-day SMA ± 2 × standard deviation (20)
BandWidth    = (upper − lower) ÷ middle = 4 × standard deviation ÷ 20-day SMA
```

So BandWidth is just four standard deviations as a share of the average. That is why it matches the standard deviation ÷ close almost exactly.

**Worked example.** On 1 July 2025 Apple's bands were $195.2 and $206.8 around a middle of $201.0. The gap of $11.6 is 5.8% of the middle line. On 22 April the bands were $173.4 and $234.4. That is a BandWidth of 29.9%.

```series
title: Apple, 2025 — Bollinger BandWidth widens in the April storm, then narrows
from: 2025-01-01
to: 2025-09-30
tf: D
line: us:AAPL | Apple
line: us:AAPL@bbw.bbw | BandWidth (20, 2), as a fraction | pane2
mark: 2025-04-08 | low close $172.42
mark: 2025-07-01 | BandWidth 5.8%
caption: BandWidth (0.10 = 10%) peaked at 31% on 21 April 2025, while the bands still held the crash days. By late June it was under 5%, and it reached the year's low, 3.5%, on 30 July.
```

**How traders use it.** John Bollinger's **squeeze** is a BandWidth at a six-month low: the stock has gone unusually quiet. Base and VCP traders look for that kind of tightness before a breakout. See [VCP — the volatility contraction pattern](learn-vcp.md).

**What the evidence says.** In [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md), a BandWidth at its lowest in 125 sessions was not followed by a bigger move than usual. The TTM Squeeze test in section 8 points the same way.

**Pitfalls.** BandWidth lags: a crash stays in it for 20 sessions, then drops out all at once. And like the standard deviation, it rises in a steady trend. Its correlation with ADX was 0.41 in the US and 0.47 in India, the highest of any volatility reading.

## 5. Historical volatility

**The question:** how big have the daily % moves been, stated as a yearly figure?

Take the daily returns, not the prices:

| Day | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| Close | 100 | 102 | 100 | 101 |
| Return | — | +2.0% | −2.0% | +1.0% |

Historical volatility is the standard deviation of those returns, scaled up to a year.

```
r          = ln(close ÷ previous close)          (the daily log return)
HV (20)    = standard deviation of r over 20 days × √252 × 100
```

A **log return** is close to the plain % change for small moves; it adds up neatly over time. The year has about 252 sessions, and √252 is about 15.9. So **HV ÷ 16 is the typical daily move**.

**Worked example.** On 1 July 2025 Apple's HV was 18.2%. Divide by 16: a typical day moved about 1.1%. On 22 April it was 77.5%, about 4.9% a day. The window then still held the 9 April jump of 15.3%.

The 1%-a-day stock from section 3 has an HV of zero: every return is the same, so they have no spread. HV measures the size of the changes, not how far the price has travelled. That makes it the cleaner volatility reading.

**Historical against implied.** Historical volatility looks back at what the stock did. **Implied volatility** is read from option prices: it is what option buyers are paying for the next weeks. The VIX is the implied volatility of the S&P 500, and India VIX that of the Nifty 50. Both are quoted on the same yearly scale as HV, so the two can be compared directly. That comparison, for the index, is in [Volatility and sentiment — what fear costs, and when it matters](learn-health-volatility.md).

```series
title: Apple, 2024–2026 — historical volatility and ATR % tell one story
from: 2024-01-01
to: 2026-10-27
tf: D
line: us:AAPL@hv.hv | Historical volatility (20), % a year
line: us:AAPL@atrp14 | ATR % (14) | right
caption: Over these years the two lines had a correlation of 0.87 for Apple. HV is the more jumpy: one 15% day lifts it sharply for exactly 20 sessions, then it drops back.
```

**What it repeats.** HV correlated at 0.88 with ATR % in the US and 0.85 in India. ATR also counts gaps and intraday ranges; HV counts only close-to-close moves. They rarely disagree for long.

**Pitfall.** One huge day dominates a 20-day HV and then falls out of the window 20 sessions later. The drop looks like calm returning, but nothing happened on that day.

## 6. Mass Index

**The question:** is the daily range widening fast, compared with its own recent average?

Donald Dorsey designed the Mass Index to spot a **reversal** when the range bulges, whichever way the price is moving. It looks at the high–low range only, not the close.

```
e1         = 9-day EMA of (high − low)
e2         = 9-day EMA of e1                     (smoothed twice)
Mass Index = sum of (e1 ÷ e2) over the last 25 bars
```

If the range stays the same, e1 equals e2. Each ratio is 1, and the sum is 25. A reading above 25 means the range has been growing faster than its smoothed average. Apple's median from 2025 to October 2026 was 25.2.

**The reversal bulge.** Dorsey's signal is a rise above 27, then a fall back below 26.5. It says a trend may be about to change. It does not say which way.

| Apple bulge | Above 27 | Back below 26.5 | Close then | Next 20 sessions |
|---|---|---|---|---|
| Summer 2024 | 20 Jun 2024 ($209.68) | 18 Jul 2024 | $224.18 | +0.2% |
| April 2025 | 10 Apr 2025 ($190.42) | 22 Apr 2025 | $199.74 | +3.6% |

**Worked example.** The April 2025 bulge peaked at 27.3 on 14 April. Apple's lowest close, $172.42, had come on 8 April, two sessions *before* the index crossed 27. The bulge confirmed a turn that had already happened. The 2024 bulge came during a strong rally and was followed by a flat month.

```series
title: Apple, 2024–2025 — the Mass Index and its two reversal bulges
from: 2024-03-01
to: 2025-09-30
tf: D
line: us:AAPL | Apple
line: us:AAPL@mass.mi | Mass Index (9, 25) | pane2
mark: 2024-06-20 | above 27
mark: 2025-04-10 | above 27
caption: The Mass Index sits near 25 most of the time. It crossed 27 only twice in these 19 months: in a sharp rally in June 2024, and two sessions after the April 2025 low.
```

**What it repeats.** Very little. It is the most independent member of the family: no correlation above 0.40 with any other reading measured. Its closest twin was historical volatility (0.35 in the US, 0.40 in India). With ATR % it was about 0.3; with relative volume, 0.17.

**Pitfalls.** It is rare: two bulges in 19 months on Apple. It gives no direction, so traders pair it with a trend reading. The thresholds 27 and 26.5 are Dorsey's conventions, not measured edges. The bulge signal is not tested in this guide.

## 7. Ulcer Index

**The question:** how deep and how long have the recent falls from a high been?

Peter Martin named it for the stress of holding a falling stock. Unlike every other reading here, **it counts only declines**. A stock that only rises has an Ulcer Index of zero, however fast it moves.

Take four closes, each measured as a % below the highest close so far:

```
drops:    0, −2, −4, −2       (% below the high)
squares:  0,  4, 16,  4       mean 6 → Ulcer Index = √6 ≈ 2.4
```

The formula:

```
drop     = 100 × (close − highest close of the last 14) ÷ that highest close
Ulcer    = √(average of drop² over the last 14 days)
```

Squaring makes deep falls count far more than shallow ones. The usual default is 14 days.

**Worked example.** On 22 April 2025, Apple was still well below its early-April high. Its Ulcer Index was 13.4, the highest of 2025–2026. On 27 October 2026, close to a new high, it was 0.6. HDFC Bank's peak in the same period was 10.9, on 2 April 2026. It came near the end of a slide from ₹925 in mid-February to ₹732 on 30 March.

**What it repeats.** Because it rises only when price falls from a high, it moves against momentum. It correlated at −0.71 with the distance from the 50-day average in the US, and −0.68 in India. With RSI it was −0.59. Its closest twin was PPO, a momentum reading, at −0.80. It also correlated about 0.7 with ATR %: falls tend to be volatile.

**How it is used.** Martin built it to rank funds by their pain, not by their swings. His **Ulcer Performance Index** divides the return above a risk-free rate by the Ulcer Index, in place of the standard deviation. For a stock chart, it is a quick read of "how bad has the recent drawdown been?" A **drawdown** is the fall from a peak.

**Pitfall.** With a 14-day setting it forgets fast. A stock 40% below its high of a year ago can read near zero if the last 14 days were calm. For long-term pain, use a longer setting.

## 8. TTM Squeeze

**The question:** is the stock so quiet that its Bollinger Bands fit inside its Keltner channel?

John Carter's squeeze compares two ways of measuring the same quietness. Bollinger Bands use the standard deviation of closes. A **Keltner channel** uses ATR. Normally the Bollinger Bands are wider.

When the closes bunch together, the Bollinger Bands shrink inside the channel. That is "squeeze on". When they widen back out, the squeeze has **fired**.

```
on        when 2 × standard deviation (20) < 1.5 × ATR (20), around the same 20-day SMA
histogram = linear-regression value over 20 bars of
            close − average(midpoint of the 20-day high–low range, 20-day SMA)
```

The histogram is a momentum reading: above zero, the close is above the middle of its recent range. Traders read its sign at the moment of firing as the likely direction.

**Worked example.** On 1 July 2025, Apple's two standard deviations came to $5.81. One and a half ATR came to $7.29. The bands sat inside the channel, so the squeeze was on, as it had been for 13 sessions.

The next day Apple rose 2.2%. Two standard deviations became $7.63, wider than the channel, and the squeeze fired with the histogram positive. Twenty sessions later Apple was 2.3% *lower*. Its ATR % had fallen from 2.2% to 1.7%.

HDFC Bank, India's largest private bank, had two squeezes in a row:

| HDFC Bank | Squeeze 1 | Squeeze 2 |
|---|---|---|
| On from | 12 Nov 2025 | 3 Feb 2026 |
| Sessions on | 39 | 12 |
| Fired | 7 Jan 2026 | 19 Feb 2026 |
| Close at the fire | ₹949.0 | ₹915.6 |
| Histogram at the fire | −11.3 (down) | −10.1 (down) |
| Close 20 sessions later | ₹949.7 | ₹780.5 |
| Move | +0.1% | −14.8% |
| ATR %: at the fire → 20 sessions later | 1.45% → 1.85% | 1.75% → 2.86% |

```series
title: HDFC Bank — two squeezes, two outcomes, winter 2025–26
from: 2025-10-15
to: 2026-04-15
tf: D
line: india:HDFCBANK.NS | HDFC Bank
line: india:HDFCBANK.NS@bb.upper | Bollinger upper (20, 2)
line: india:HDFCBANK.NS@bb.lower | Bollinger lower (20, 2)
line: india:HDFCBANK.NS@squeeze.mom | Squeeze histogram | pane2 zero
band: 2025-11-12 2026-01-06 | squeeze on
band: 2026-02-03 2026-02-18 | squeeze on
mark: 2026-01-07 | fired
mark: 2026-02-19 | fired
caption: The longer squeeze fired downward and went nowhere for a month. The short one also fired downward, and the stock fell 15% in the next 20 sessions, including a 5% drop on very heavy volume on 19 March.
```

Both fires pointed down. One was followed by nothing, the other by a large fall. A month later the same tool had given one useful warning and one false one. Section 10 shows that across more than 33,000 fires, the moves that followed were no bigger than usual.

**What it repeats.** "Squeeze on" correlated at −0.41 with BandWidth in the US (−0.46 in India): it is a yes/no version of "BandWidth is low for this stock's ATR". It was −0.26 to −0.28 with ADX: squeezes come when there is no trend. With direction readings it was near zero.

**Pitfalls.** The histogram is a smoothed momentum line, so it repeats short-term momentum and lags turns. The squeeze can fire on a tiny change, as HDFC Bank's second one did (₹23.98 against ₹23.70). And Carter's settings (2 standard deviations inside 1.5 ATR) are conventions; other packages use slightly different ones.

## 9. The family side by side

| Indicator | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| ATR / ATR % | How far does it move in a day, gaps included? | 14, Wilder | Historical volatility (0.88) | Stops, position size, volatility filters |
| Standard deviation | How spread out are the recent closes? | 20 | BandWidth (0.98) | Building bands; rarely on its own |
| Bollinger BandWidth | How wide are the bands, as a % of price? | 20, 2 | Standard deviation ÷ close (0.98) | Spotting a quiet base; the Bollinger squeeze |
| Historical volatility | How big are the daily % moves, yearly? | 20, × √252 | ATR % (0.88) | Comparing with implied volatility; sizing |
| Mass Index | Is the daily range widening fast? | 9, 25; lines 27 / 26.5 | Nothing above 0.40 | Reversal-bulge warnings |
| Ulcer Index | How deep are the recent falls from a high? | 14 | PPO (−0.80), distance from the 50-day | Drawdown pain; ranking funds or systems |
| TTM Squeeze | Are the bands inside the Keltner channel? | 20; 2 sd, 1.5 ATR | BandWidth (−0.41) | Flagging a quiet stock; timing with the histogram |

## 10. What the evidence says

> **Method.** US: a random 300 stocks; India: all 147 that qualify. Each has at least 1,500 sessions since 2015 and a large daily traded value. Every indicator was computed on daily bars at its default settings. Correlations were measured day by day within each stock over 2015 to October 2026; the figures are medians across stocks. Today's listed stocks only, so failed companies are missing.

**Overlap.** Most of the family is one number in different units.

| Pair | US | India |
|---|---|---|
| BandWidth and standard deviation ÷ close | 0.98 | 0.98 |
| Historical volatility and ATR % | 0.88 | 0.85 |
| Standard deviation ÷ close and ATR % | 0.73 | 0.69 |
| BandWidth and ADX | 0.41 | 0.47 |
| Mass Index and its closest twin (historical volatility) | 0.35 | 0.40 |
| Ulcer Index and distance from the 50-day | −0.71 | −0.68 |

**No direction.** BandWidth, historical volatility and the Mass Index barely moved with the direction readings: RSI, the 14-day % change and the distance from the 50-day. Their correlations ran from about −0.25 to 0.16. ATR % was weakly negative (about −0.2 to −0.4): within a stock, volatility runs higher when the price is below its averages. The Ulcer Index is the exception, by design.

**The TTM Squeeze test.** Does a squeeze that fires lead to a bigger move? Over the next 20 sessions:

| | US | India |
|---|---|---|
| Squeezes that fired | 22,018 (300 stocks) | 11,614 (147 stocks) |
| Share of sessions with the squeeze on | 22% | 26% |
| Median absolute 20-session move, after a fire | 5.5% | 5.6% |
| Median absolute 20-session move, all sessions | 5.4% | 5.5% |
| ATR % 20 sessions later ÷ ATR % on the day, after a fire | 0.98 | 1.00 |
| Same ratio, all sessions | 0.98 | 0.98 |

**"Compression leads to expansion" did not show up.** After a fire, the next month's move was the same size as any month's, in both markets. ATR was not higher 20 sessions later either. This matches the BandWidth test in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

Be clear about what was tested. It measured the **size** of the next move, not its direction. A trader who buys a squeeze only when it fires upward, in an uptrend, is using a different rule. And a squeeze can still mark a calm base, where a breakout has a nearby stop. Tightness as part of a base is a reason to watch, not an edge on its own.

**Published research.**

- **Volatility clusters.** Big moves follow big moves, and calm follows calm. Robert Engle's ARCH model (1982) made that measurable. It is why today's ATR is a fair guide to next month's: the ratios above sit near 1.
- **High volatility has not paid.** Ang, Hodrick, Xing and Zhang (2006) found that US stocks with high recent idiosyncratic volatility had low later returns. Idiosyncratic means the part not explained by the market.
- **Scaling by volatility.** Moreira and Muir (2017) found that cutting exposure when recent volatility was high improved risk-adjusted returns for several factor portfolios.

**Limits.** Correlation shows overlap, not predictive power. Today's listed stocks only. No costs. Overlapping 20-session windows, so the event counts overstate how many independent tests there were. The Mass Index bulge and the squeeze histogram's direction were not tested.

## 11. Checklist

- [ ] Do I have more than one of ATR %, BandWidth, standard deviation and historical volatility on my chart? Keep one.
- [ ] Is my stop at least about one ATR from entry, and is the position sized from that distance?
- [ ] Is a high BandWidth or standard deviation just a strong trend, not wild daily moves?
- [ ] Is a big HV change real, or a single huge day entering or leaving the 20-day window?
- [ ] A squeeze or a low BandWidth: what will turn it into a trade — a pivot, volume, a results date?
- [ ] A Mass Index bulge: what does the trend say about direction?
- [ ] Ulcer Index: is the setting long enough for the drawdown I care about?

## Further reading

- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — the true range and ATR.
- John Bollinger, *Bollinger on Bollinger Bands* (2001) — the bands, BandWidth and the squeeze.
- John Carter, *Mastering the Trade* — the TTM Squeeze from its author.
- Chester Keltner, *How to Make Money in Commodities* (1960) — the original Keltner channel.
- Peter Martin and Byron McCann, *The Investor's Guide to Fidelity Funds* (1989) — the Ulcer Index.
- John Hull, *Options, Futures, and Other Derivatives* — historical and implied volatility.
- Robert Engle, "Autoregressive Conditional Heteroscedasticity with Estimates of the Variance of United Kingdom Inflation" (*Econometrica*, 1982).
- Ang, Hodrick, Xing and Zhang, "The Cross-Section of Volatility and Expected Returns" (*Journal of Finance*, 2006).
- Alan Moreira and Tyler Muir, "Volatility-Managed Portfolios" (*Journal of Finance*, 2017).
