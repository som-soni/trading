# Bollinger band mean reversion — buying the lower band in a range

**In short**

- Bollinger bands sit two standard deviations above and below a 20-day average. A close below the lower band means the price is unusually low compared with its recent past.
- In a sideways market (a range), the price tends to come back towards the middle band. The trade buys the lower band and sells at the middle.
- In a downtrend the price can keep closing at or below the lower band for days or weeks. This is called "walking the band", and it is how this trade loses most.
- On stored data, a lower-band close in single stocks was followed by about the same returns as an ordinary day. Fewer than 4 in 10 reached the middle band within 10 sessions. The edge depends on the market being a range, which is hard to know in advance.
- Use the bands to measure how stretched a price is, and require other evidence of a range before buying.

This guide belongs to the mean-reversion group, with [RSI(2) mean reversion](learn-strat-rsi2.md) and [gap fills](learn-strat-gap-fills.md). How the bands are computed is covered in [momentum indicators](learn-price-oscillators.md).

## 1. The idea

### An example first

In early 2023 HDFC Bank traded sideways, roughly between 770 and 850 (prices adjusted for a later bonus issue). On 15 March 2023 it closed at 770.95, just under its lower band of 771.11. The middle band, the 20-day average, was at 805.67.

```series
title: HDFC Bank — a lower-band close inside a range, March 2023
from: 2022-12-01
to: 2023-05-31
line: india:HDFCBANK.NS | HDFC Bank
line: india:HDFCBANK.NS@bbup20 | Upper band
line: india:HDFCBANK.NS@bblo20 | Lower band
mark: 2023-03-15 | Close below the lower band
caption: The 50-day average was flat, and the price came back to the middle band within two weeks. Prices are adjusted for a later bonus issue.
```

A buyer at that close set a target at the middle band. The price closed above the middle band on 29 March 2023, at 793.90. The gain was 3.0% in 10 sessions, and the price never closed below the entry in between.

### What the trade is

**Bollinger bands**, created by John Bollinger in the 1980s, are three lines. The middle band is the 20-day simple average of the close. The upper and lower bands are 2 standard deviations above and below it. A **standard deviation** measures how widely the closes have been spread around their average. When the price is calm, the bands narrow; when it swings, they widen.

Bollinger also defined **%B**: where the close sits between the bands. %B = (close − lower band) ÷ (upper band − lower band). A %B of 0 is on the lower band, 1 is on the upper band, and below 0 is under the lower band.

The trade: in a range, buy when %B closes below 0, and sell when the close returns to the middle band.

A worked %B, from the HDFC Bank example:

| Item | Value on 15 Mar 2023 |
|---|---|
| Middle band (20-day average) | 805.67 |
| Lower band | 771.11 |
| Upper band (middle + the same distance) | about 840.2 |
| Close | 770.95 |
| %B = (770.95 − 771.11) ÷ (840.2 − 771.11) | about 0.00 |

A %B of −0.2 would mean the close was a fifth of the band's width below the lower band. That is a much deeper move.

### Why it can work

In a range, buyers and sellers agree roughly on value. Moves to the edges come from short bursts of selling or buying that are not backed by new information. When the burst ends, the price drifts back to where most trading happens. The bands measure the edge of that range in a way that adapts to volatility.

### Who is on the other side

The sellers at the lower band are traders whose stops were hit and investors who lost patience. In a range, they are selling at a temporary low. In a downtrend they are early, and you are the one who is wrong. The strategy is only as good as your judgement of which of the two you are in.

## 2. When it works and when it doesn't

**A range, not a trend.** A **range** is a period when the price moves sideways between a roughly fixed high and low. The moving averages are flat, and new highs and lows are not being made. A **trend** is a series of higher highs and higher lows (uptrend) or lower ones (downtrend). Mean reversion works in the first and fails in the second.

**The failure mode: walking the band.** Bollinger himself warned that a close outside a band is not a signal by itself. In a strong move, the price "walks" along the band, closing at or beyond it day after day. In the event study below, about 6 in 10 lower-band closes were followed by another lower-band close within 5 sessions.

**A flat average is not enough.** The study's surprise was that a flat 50-day average did not make lower-band buys better. In India, they were worse than an ordinary day. A flat average often marks the end of an uptrend, just before a decline starts. Look for a range that has held for weeks, with clear tests of both edges.

**Telling a range from a trend.** No single number does it. These signs, read together, are the practical test:

| Sign | Range | Trend |
|---|---|---|
| 50-day average | Flat, crossed often by the price | Sloping, price stays on one side |
| Highs and lows of the last 3 months | Similar highs, similar lows | Higher highs and lows, or lower ones |
| ADX (14-day) | Below 20 | Above 25 |
| Band width | Steady | Widening in the direction of the move |
| Closes outside a band | Single closes, quickly back inside | Several in a row (walking the band) |
| Volume on down days | Normal | Heavy, rising |

**Before results.** A results announcement can break any range. Do not buy the lower band with results due before your target is likely to be reached.

**India.** Large, steady stocks (banks, consumer staples, IT services) spend long periods in ranges. Small stocks trend and gap more. Settlement is T+1. Selling the upper band short for more than a day needs stock futures. Price bands on stocks outside the futures list can stop you exiting on a bad day.

**US.** Index ETFs and large stocks are cheap to trade. Bollinger's own work used many markets; the same caution about trends applies.

## 3. The rules

### Universe and filters

- Price above ₹100 or $10; 20-day average traded value above ₹10 crore or $10 million.
- No results announcement in the next 10 sessions.

### Setup

The stock must be in a range. Use at least two of these tests:

- The 50-day average has changed by less than 2% over the last 20 sessions (*slope limit*).
- The 14-day ADX is below 20 (*ADX limit*). ADX measures trend strength regardless of direction.
- Over the last 60 sessions (*range length*), the price has touched within 3% of the range low at least twice, and within 3% of the range high at least twice.
- The close is above the range low of the last 60 sessions.

### Entry

- Trigger: the close is below the lower band (%B below 0) (*entry %B*).
- Better: wait for a close back inside the band (%B above 0) after a close below it. This avoids buying the first day of a band walk, at the cost of a worse price.
- Order: buy at the close, or at the next open.

### Initial stop

- A close more than 2% below the 60-session range low, or 2 ATR below the entry, whichever is closer (*stop distance*).

### Exits

- **Target:** the first close at or above the middle band.
- **Second target:** half at the middle band, the rest at the upper band.
- **Time stop:** sell after 10 sessions if neither the target nor the stop is reached (*maximum hold*).
- **Invalidation:** two more closes below the lower band within 5 sessions. The band walk has started.

### Position size

Risk 0.5% of capital per trade, sized from the stop (see [position sizing](learn-risk-sizing.md)). Cap each position at 10% to 15% of capital.

### Managing the trade

Do not average down on further lower-band closes. If the range low breaks, the range is over.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Band length | 20 days (10–50) | The average and the volatility window | Bollinger's default |
| Band width | 2 standard deviations (1.5–2.5) | How far outside "unusual" is | 2.5 gives fewer, deeper signals |
| *Entry %B* | Below 0 (−0.2 to 0.1) | How stretched before buying | Lower means fewer trades |
| *Slope limit* | ±2% over 20 sessions | Flat 50-day average | Alone it did not help in the study |
| *ADX limit* | Below 20 (15–25) | Weak trend | Untested here |
| *Range length* | 60 sessions (40–120) | How long the range has held | Longer is more reliable, rarer |
| *Stop distance* | 2 ATR, or 2% below the range low | Where the range is broken | |
| Target | Middle band | Where to take profit | Reached within 10 sessions in about 37% of all signals |
| *Maximum hold* | 10 sessions (5–20) | Time stop | |
| Risk per trade | 0.5% | Account risk | |

## 5. Variations

- **Bollinger's own approach.** In *Bollinger on Bollinger Bands* (2001), Bollinger combines the bands with patterns and volume indicators. One pattern is a **W-bottom**: a first low outside the lower band, then a second low inside it. The second low shows selling pressure weakening.
- **Connors' %B rule.** Connors and Alvarez test buying ETFs when %B is below 0.2 for several days, above the 200-day average. This is a dip in an uptrend, like [RSI(2)](learn-strat-rsi2.md).
- **Keltner channels.** Bands set by ATR instead of standard deviation. They widen less after a single large day.
- **The squeeze.** When the bands are very narrow, a large move often follows. Bollinger uses this for breakouts, the opposite of reversion. See [momentum indicators](learn-price-oscillators.md).
- **Selling the upper band.** The mirror trade sells short at the upper band in a range. In India, overnight shorts need futures.

## 6. Worked examples

### HDFC Bank, March 2023 (India): it worked

| Step | Date | Value |
|---|---|---|
| Range check | Mid-March 2023 | 50-day average down 0.4% over 20 sessions: flat |
| Signal | 15 Mar 2023 | Close 770.95, lower band 771.11, %B about 0 |
| Entry | Close, 15 Mar 2023 | 770.95 |
| Target reached | 29 Mar 2023 | Close 793.90, above the middle band |
| Result | 10 sessions | +3.0% |

### Asian Paints, October–November 2024 (India): walking the band

On 31 October 2024 Asian Paints closed at 2,935.65, just under its lower band of 2,936.42. The 50-day average was flat, down only 0.2% over 20 sessions. By the slope test, it was a range.

```series
title: Asian Paints — walking the lower band, November 2024
from: 2024-08-01
to: 2025-01-31
line: india:ASIANPAINT.NS | Asian Paints
line: india:ASIANPAINT.NS@bbup20 | Upper band
line: india:ASIANPAINT.NS@bblo20 | Lower band
mark: 2024-10-31 | Close below the lower band
caption: The price closed below the lower band again and again, then gapped down on results.
```

| Step | Date | Value |
|---|---|---|
| Entry | Close, 31 Oct 2024 | 2,935.65 |
| Closes below the lower band | 5, 7 and 8 Nov 2024 | The band walk had started |
| Results gap | 11 Nov 2024 | Opened 7.4% lower, closed at 2,543.10 |
| 20 sessions after entry | | 15.6% below the entry |

Three rules would have prevented or limited this loss. The results date was inside the holding period. Two more lower-band closes within 5 sessions meant the trade was invalid by 7 November. And the stock had just come down from an uptrend: the range test of two touches at each edge was not met.

### S&P 500 ETF, October 2024 (US): a dip in an uptrend

This one is not a range trade. On 31 October 2024 the S&P 500 ETF closed at 568.64, just under its lower band of 569.01. Its 50-day average had risen 2.7% over 20 sessions, so the market was trending up.

| Step | Date | Value |
|---|---|---|
| Signal | 31 Oct 2024 | %B about −0.02; 50-day average rising |
| Entry | Close, 31 Oct 2024 | 568.64 |
| Target reached | 6 Nov 2024 | Close 591.04, above the middle band |
| Result | 4 sessions | +3.9% |

The study in section 8 found that this kind of signal, a lower-band close while the 50-day average rises, did best. It is closer to [RSI(2)](learn-strat-rsi2.md) than to range trading.

## 7. Common mistakes

- **Treating a band touch as a signal.** Bollinger says this repeatedly. A close outside the band says the move is strong, not that it is over.
- **Buying the lower band in a downtrend.** That is catching a falling price. Check the trend first, and check it with more than one average.
- **Ignoring results dates.** One results gap is larger than several reversion gains.
- **No stop.** Unlike an index, a single stock can leave a range and never come back.
- **Using the upper band as the target every time.** In a range, the middle band is reached far more often.

## 8. What the evidence says

**Published research.** There is little academic support for Bollinger band trading on its own. Lento, Gradojevic and Wright (2007) tested band rules on several stock indices and an exchange rate, and found they did not beat buy-and-hold after costs. Short-term reversal in general is well documented (see [RSI(2)](learn-strat-rsi2.md)). Bollinger presents the bands as a framework for comparing prices with their own past, not as a complete system.

**Event study on stored data.** For liquid stocks (US and India since 2004), I found every close below the lower band of a 20-day, 2-standard-deviation band. I measured the return over the next 10 sessions. I grouped signals by how much the 50-day average had changed over the previous 20 sessions. A rise of more than 2% is "rising", a fall of more than 2% is "falling", and anything between is "flat". "Base" is the average 10-day return of all days in the same group.

| Market | 50-day slope | Signals | Base: 10-day return | After a lower-band close | Up after 10 days | Reached the middle band within 10 sessions |
|---|---|---|---|---|---|---|
| US | All | 390,558 | +0.33% | +0.32% | 53% | 37% |
| US | Flat | 134,066 | +0.25% | +0.06% | 53% | 37% |
| US | Rising | 135,422 | +0.23% | +0.34% | 53% | 38% |
| US | Falling | 121,070 | +0.56% | +0.58% | 54% | 36% |
| India | All | 81,292 | +0.59% | +0.40% | 52% | 37% |
| India | Flat | 24,527 | +0.32% | −0.23% | 50% | 35% |
| India | Rising | 31,057 | +0.78% | +0.88% | 54% | 38% |
| India | Falling | 25,708 | +0.50% | +0.43% | 52% | 37% |

In every group, 58% to 60% of signals were followed by another close below the lower band within 5 sessions.

The same test on the two indices, with 10-day returns. The US index data start in 1993, and the Indian data in 2007.

| Index | 50-day slope | Signals | Base | After a lower-band close | Up after 10 days |
|---|---|---|---|---|---|
| S&P 500 ETF | Flat | 272 | +0.31% | +0.27% | 55% |
| S&P 500 ETF | Rising | 77 | +0.36% | +1.03% | 70% |
| Nifty 50 | Flat | 120 | −0.16% | −1.53% | 46% |
| Nifty 50 | Rising | 56 | +0.62% | +1.74% | 55% |

**What this says.** On its own, a lower-band close in a single stock predicted nothing useful over 10 days. The best results came when the 50-day average was rising: a dip in an uptrend, not a range trade. A flat average was the worst case in India, for stocks and the index. So the slope test is not a good test of a range. The range must be shown by the price itself, with repeated tests of both edges.

**Caveats.** The stock lists are today's (survivorship bias), which flatters any dip-buying. Signals on consecutive days overlap. No costs. The study did not test the full range rules of section 3, which is the reader's job.

## 9. Building and testing it yourself

**Data.** Daily highs, lows and closes; results dates; delisted stocks.

**Look-ahead traps.**
- A range identified by looking at the chart afterwards is look-ahead. The range rules must use only the 60 sessions before the signal.
- Bands use the standard deviation of the last 20 closes, including today's. That is fine for a trade at today's close, not for one at today's open.

**Survivorship.** Stocks that broke their ranges downward and were later delisted are exactly the losing trades. Include them.

**Costs (India, approximate).** About 0.25% to 0.35% per round trip in delivery, plus slippage. With average gains of 2% to 3% per winning trade and many small losers, costs matter.

**What to test.** First, the range test alone: how often does a "range" by your rules stay a range for the next 10 sessions? Then the entry (%B below 0, or the close back inside). Then the exits. Report each step.

**What a good test reports.** Trades, win rate, average win and loss, the share of trades stopped by the band-walk rule, results by year, and results by range length.

```
for each day t:
    mid = sma(close, 20); sd = stdev(close, 20)
    lower = mid - 2*sd; upper = mid + 2*sd
    in_range = abs(sma50[t]/sma50[t-20] - 1) < 2% and adx14[t] < 20
               and touches_of(range_low_60) >= 2 and touches_of(range_high_60) >= 2
    if in_range and close[t] < lower[t] and no results in next 10 sessions:
        buy at close[t]; stop = max(entry - 2*atr14, range_low_60 * 0.98)
        exit on: close >= mid | stop | 2 more closes < lower within 5 sessions | 10 sessions
```

## 10. Checklist

- [ ] Has the stock been in a range for at least 60 sessions, with two tests of each edge?
- [ ] Is the 50-day average flat and the ADX low, and is the range still intact?
- [ ] Is there no results announcement before my target is likely to be reached?
- [ ] Did the close fall below the lower band, or did it just close back inside?
- [ ] Where is my stop (below the range low)? Is the position sized from it?
- [ ] Is my target the middle band, and is my time stop set?
- [ ] Will I exit if it closes below the lower band twice more?

## Further reading

- John Bollinger, *Bollinger on Bollinger Bands* (McGraw-Hill, 2001).
- Larry Connors and Cesar Alvarez, *High Probability ETF Trading* (2009).
- Camillo Lento, Nikola Gradojevic and Mark Wright, "Investment information content in Bollinger Bands?", *Applied Financial Economics Letters* (2007).
- J. Welles Wilder, *New Concepts in Technical Trading Systems* (1978) — ADX and ATR.
