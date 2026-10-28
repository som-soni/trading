# Volume indicators — relative volume, OBV, A/D line, Chaikin Money Flow and Oscillator, MFI, Force Index, Ease of Movement, VWAP and volume by price

**In short**

- Volume indicators combine the number of shares traded with the price. Most of them end up measuring the price far more than the volume.
- Relative volume (today's volume ÷ its 50-day average) is the one reading that is truly about volume. Nothing measured correlated with it above about 0.17.
- MFI, Force Index, Ease of Movement and the distance from VWAP mostly repeat short-term momentum. MFI correlated 0.76 with the plain 14-day % change.
- OBV and the A/D line are running totals. Traders read them for divergences against price. Those divergence claims are not tested here.
- Use relative volume to judge a day, and VWAP or volume by price to find levels. Treat the volume oscillators as momentum readings.

This guide covers the volume family of indicators. How to read volume itself — breakouts, dry-ups, climaxes and capitulation — is in [Volume — how strongly a move is supported](learn-price-volume.md). Trading around VWAP is in [VWAP strategies — trading around the day's average price](learn-strat-vwap.md). For momentum readings these indicators repeat, see [Momentum II — how fast the price is changing](learn-ind-momentum-rate.md). For how the families fit together, see [Indicators — the map](learn-ind-map.md).

---

## 1. What this family measures

On 28 April 2025, Reliance Industries rose 5.3% on about 2.5 times its normal volume. On 6 January 2026 it fell 4.5% on 2.9 times its normal volume. Here is what each volume indicator said, at its default setting:

| Reliance (RELIANCE.NS) | 25 Apr 2025 | 28 Apr 2025 | 6 Jan 2026 |
|---|---|---|---|
| Close | ₹1,300.4 | ₹1,368.8 | ₹1,507.6 |
| Change on the day | −0.1% | +5.3% | −4.5% |
| Relative volume (÷ 50-day average) | 1.17 | 2.50 | 2.87 |
| On Balance Volume, change on the day | −14.4 million | +31.1 million | −27.4 million |
| A/D line, change on the day | −4.9 million | +24.5 million | −18.9 million |
| Chaikin Money Flow (20) | 0.05 | 0.17 | −0.18 |
| Money Flow Index (14) | 70.7 | 78.0 | 53.0 |
| Force Index (13), ₹ | 5.6 crore | 35.2 crore | −26.7 crore |
| Distance from 20-day VWAP | +4.2% | +8.9% | −2.9% |
| RSI (14), for comparison | 62.7 | 73.1 | 39.4 |

Two kinds of reading are mixed here. **Relative volume** says how busy the day was, and nothing else: both big days score high, up or down. Every other row has a sign, and the sign follows the price. They weight the price change by volume.

That is the family's question: **how much business was done, and did it come with rising or falling prices?** The second half of the question is where most of these indicators turn into momentum readings. MFI moved with RSI from 70.7 to 78.0 and back to 53.0.

## 2. Relative volume

**The question:** is today busier than normal for this stock?

```
relative volume = today's volume ÷ average volume of the last 50 sessions
```

1.0 is a normal day; 2.0 is twice normal. Some charts draw a 20-day average line under the volume bars instead.

**Worked example.** On 28 April 2025, Reliance traded 31.1 million shares. Its 50-day average before that day was about 12.4 million. So relative volume was about 2.5.

```series
title: Reliance, spring 2025 — relative volume on the up days
from: 2025-03-01
to: 2025-06-30
tf: D
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@rvol50 | Relative volume (÷ 50-day) | pane2 bars
mark: 2025-04-28 | +5.3% on 2.5×
caption: The two heaviest days of the spring came on 28 and 29 April, both up, both about 2.5× normal. By 5 May the stock was 4.6% above the 28 April close.
```

**What it repeats.** Nothing. It is the most independent reading measured: no correlation above about 0.17 with any other indicator. With RSI it was −0.09 in the US and 0.06 in India. That makes it the one volume reading worth adding to a chart of price indicators.

**How traders use it.** It is the base of almost every volume rule: breakout volume of 1.4–1.5× or more, a dry-up under 0.7×, a climax at the heaviest volume of a run. How well those rules held up is measured in [Volume — how strongly a move is supported](learn-price-volume.md). The short answer: a heavy day mattered mainly because it came with a bigger price move.

**Pitfalls.** Results days, index changes, options expiry and block trades inflate volume for mechanical reasons. Indian stocks trade far more unevenly than US stocks, so 2× is a lower bar in India.

## 3. On Balance Volume

**The question:** has more volume traded on up days or on down days, added up over time?

Joseph Granville's rule is simple. On a day the close rises, add the day's volume. On a day it falls, subtract it. On an unchanged close, do nothing.

```
OBV today = OBV yesterday + volume    if close > previous close
          = OBV yesterday − volume    if close < previous close
          = OBV yesterday             otherwise
```

**Worked example.** On 28 April 2025, Reliance closed up, so its OBV rose by the whole day's 31.1 million shares. It did not matter that the rise was 5.3% rather than 0.1%. On 6 January 2026 it closed down, so OBV fell by 27.4 million.

The level of OBV means nothing; it depends on the day the count began. Only its direction and its turns matter.

```series
title: Reliance, mid-2024 to mid-2025 — On Balance Volume follows the price
from: 2024-07-01
to: 2025-08-29
tf: D
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@obv.obv | On Balance Volume | pane2
mark: 2025-03-04 | low close ₹1,161.9
caption: OBV fell from about 4,044 million in July 2024 to 3,871 million at the March 2025 low, then rose to 4,080 million in July 2025. At the March low it also made a lower low: no divergence here. Over these 14 months its correlation with the close was 0.90.
```

**How traders use it.** Granville read OBV for **divergences**. If the price makes a new high and OBV does not, the volume is not confirming the move. If the price makes a new low and OBV does not, sellers may be running out. Those claims are not tested in this guide.

**What it repeats.** A running total trends with whatever it adds up. So its correlation with other readings mostly measures whether both trended, and is not comparable with the other numbers here. OBV's day-to-day correlation with RSI was near zero (0.10 in the US, 0.05 in India).

**Pitfalls.** A 0.1% rise and a 5% rise add the same volume. One huge day, such as an index rebalance, can shift the line for years.

## 4. The Accumulation/Distribution line

**The question:** did the stock close near the top or the bottom of its day's range, weighted by volume?

Marc Chaikin's A/D line refines OBV. It does not add all the volume. It adds a share of it, depending on where the close sits in the day's range. The **close location value** is +1 at the high, −1 at the low and 0 at the middle.

```
close location = ((close − low) − (high − close)) ÷ (high − low)
A/D today      = A/D yesterday + close location × volume
```

**Worked example.** On 28 April 2025, Reliance's range was ₹1,320.2 to ₹1,374.6, and it closed at ₹1,368.8:

```
close location = ((1368.8 − 1320.2) − (1374.6 − 1368.8)) ÷ (1374.6 − 1320.2)
               = (48.6 − 5.8) ÷ 54.4 ≈ 0.79
A/D change     = 0.79 × 31.1 million ≈ +24.5 million
```

OBV added all 31.1 million; the A/D line added 79% of it.

**The gap blind spot.** The A/D line looks only inside the day. A stock that gaps up and then closes in the lower half of its range *loses* A/D, even though it rose. In the stored daily bars, Reliance's whole rise since 2015 came between one close and the next open. From open to close it lost ground, on balance.

So its A/D line fell from about −246 million in 2015 to −1,876 million in October 2026, while the stock rose about sixfold. TCS and HDFC Bank showed the same split: gains overnight, losses during the session.

| Reliance | 1 Jan 2015 | 27 Oct 2026 |
|---|---|---|
| Close (adjusted) | ₹203 | ₹1,196 |
| On Balance Volume | 450 million | 3,612 million |
| A/D line | −246 million | −1,876 million |

That eleven-year "divergence" says nothing about buyers and sellers. It is a property of the formula. It is also why OBV and the A/D line correlated at 0.74 in the US but **−0.50** in India.

**How traders use it.** Like OBV: for divergences against the price, and as the input to the Chaikin Oscillator. Not tested here.

## 5. Chaikin Money Flow and the Chaikin Oscillator

### 5.1 Chaikin Money Flow

**The question:** over the last 20 days, did the closes sit mostly near the highs or the lows, weighted by volume?

Chaikin Money Flow is the A/D idea over a fixed window. It runs from −1 to +1, so it does not drift like a running total.

```
CMF = sum of (close location × volume) over 20 days ÷ sum of volume over 20 days
```

Above zero means closes have been in the upper part of their ranges on the heavier days. Some packages use 21 days.

**Worked example.** Reliance's CMF was 0.05 on 25 April 2025 and 0.17 after the 28 April jump. On 6 January 2026 it was −0.18.

**What it repeats.** Partly its own. It correlated 0.58 with RSI in the US and 0.61 in India. Its closest twin was the Chaikin Oscillator (0.71 and 0.66).

**Pitfall.** It shares the A/D line's gap blind spot. A stock gapping up and fading inside the day reads as distribution.

### 5.2 Chaikin Oscillator

**The question:** is the A/D line speeding up or slowing down?

```
Chaikin Oscillator = 3-day EMA of the A/D line − 10-day EMA of the A/D line
```

It is a MACD of the A/D line. Above zero, the A/D line has been rising faster lately. Its units are shares, so its size cannot be compared across stocks.

**Worked example.** Reliance's oscillator went from +9.4 million on 25 April 2025 to +15.4 million on 28 April. On 6 January 2026 it was −10.5 million.

**What it repeats.** About half price momentum: 0.55 with RSI in the US, 0.53 in India. Its closest twin was the Ultimate Oscillator, a range-position momentum reading (0.76 and 0.71).

## 6. Money Flow Index

**The question:** RSI, but with each day's move weighted by its volume.

Gene Quong and Avrum Soudack built MFI the way RSI is built, using "money flow" in place of price change. The **typical price** is the average of the high, low and close.

```
typical price  = (high + low + close) ÷ 3
money flow     = typical price × volume
positive flow  = sum over 14 days of money flow on days the typical price rose
negative flow  = sum over 14 days of money flow on days it fell
MFI            = 100 − 100 ÷ (1 + positive flow ÷ negative flow)
```

Like RSI it runs from 0 to 100. The usual lines are 80 (overbought) and 20 (oversold).

**Worked example.** Reliance's MFI was 70.7 on 25 April 2025 and 78.0 after the jump. It reached 96.6 on 5 May. RSI on those days was 62.7 and 73.1.

```series
title: Reliance, 2025 — Money Flow Index and RSI on one panel
from: 2025-01-01
to: 2025-08-29
tf: D
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@mfi.mfi | Money Flow Index (14) | pane2
line: india:RELIANCE.NS@rsi14 | RSI (14) | pane2
caption: The two lines rise and fall together; their correlation over these eight months was 0.84. MFI swings wider, from 96.6 on 5 May to 14.7 on 28 July, because volume amplifies the busiest days.
```

**What it repeats.** Mostly price. MFI correlated 0.76 with the plain 14-day % change in the US, and 0.79 in India. With RSI it was 0.74. Its closest twin was the Vortex spread, a trend-direction reading, at 0.85. The volume weighting changes the size of its swings more than their direction.

**Pitfalls.** The same as RSI's: a strong stock stays "overbought" for weeks. See [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

## 7. Force Index

**The question:** how much force was behind the latest moves — their size times their volume?

Alexander Elder multiplies each day's price change by its volume, then smooths the result.

```
raw force   = (close − previous close) × volume
Force Index = 13-day EMA of raw force         (Elder also uses a 2-day EMA, for short-term timing)
```

**Worked example.** On 28 April 2025, Reliance rose ₹68.4 on 31.1 million shares. The raw force was about ₹213 crore. The 13-day average absorbed one-seventh of the jump, so the Force Index rose from ₹5.6 crore to ₹35.2 crore.

**What it repeats.** Short-term momentum: 0.61 with the 14-day % change in the US, 0.58 in India. Its closest twin was the position inside a moving-average envelope (0.70 and 0.64).

**Pitfalls.** Its units are price times shares. A ₹35 crore reading on Reliance cannot be compared with any other stock, or with Reliance ten years ago. Read only its sign and its swings against its own past.

## 8. Ease of Movement

**The question:** how far did the price move for each unit of volume?

Richard Arms built Ease of Movement from his Equivolume charts. A big move on light volume scores high: the price moved easily. A small move on heavy volume scores near zero.

```
midpoint move = (high + low) ÷ 2 − (previous high + previous low) ÷ 2
raw EOM       = 10,000 × midpoint move × (high − low) ÷ volume
EOM           = 14-day average of raw EOM
```

The 10,000 only rescales the numbers; packages use different divisors.

**Worked example.** Reliance's EOM was 0.06 on 25 April 2025 and 0.12 after the jump. On 6 January 2026 it dropped from 0.12 to 0.01, despite a 4.5% fall. Dividing by that day's heavy volume shrank its reading. On normal volume, the same move would have counted about three times as much.

**What it repeats.** Short-term momentum: 0.71 with Momentum (10) in the US, 0.65 in India.

**Pitfall.** It divides by volume, so its scale depends on the stock's price and share count. Only its sign and its own history are meaningful.

## 9. VWAP — rolling and anchored

**The question:** what is the average price paid per share over a period, weighted by volume?

```
VWAP = sum of (typical price × volume) ÷ sum of volume
```

A **rolling VWAP** uses the last N days (20 by default here). An **anchored VWAP** starts at a date you choose, such as a results day or a major low, and keeps running. A **session VWAP** restarts every morning; day traders use it.

**Worked example.** Reliance's 20-day VWAP was ₹1,257.2 on 28 April 2025. The close of ₹1,368.8 was 8.9% above it. Its 14-day % change that day was 9.6%: almost the same number.

**What it repeats.** The distance from this VWAP correlated 0.92 with the 14-day % change in the US, and 0.91 in India. Its closest twin was the position inside a 20-day moving-average envelope (0.99): volume weighting barely changes a 20-day average.

**How traders use it.** The line itself is the point, not the distance. Large funds judge their buying against VWAP. An anchored VWAP shows whether the average buyer since an event is in profit or loss. The trades built on it are in [VWAP strategies — trading around the day's average price](learn-strat-vwap.md).

## 10. Volume by price

**The question:** at which prices did the most shares change hands?

Every indicator above is drawn against time. **Volume by price**, also called the **volume profile**, is a histogram drawn on the price axis. Each bar shows how many shares traded at that price over a chosen period.

Three terms come with it:

- The **point of control**: the price with the most volume.
- The **value area**: the range around it holding most of the volume, commonly 70%.
- **High- and low-volume nodes**: prices where much or little traded.

Traders treat high-volume prices as likely support or resistance: many holders have a cost there. Price tends to cross low-volume gaps quickly. This connects to [Support and resistance — drawing the levels that matter](learn-support-resistance.md) and [Supply and demand — zones, and why price levels matter](learn-supply-demand.md).

**Pitfall.** Built from daily bars, it has to spread each day's volume across that day's range, because the bar does not say where in the range the shares traded. That is an approximation. Intraday data gives a truer profile. It is not measured in this guide.

## 11. The family side by side

| Indicator | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| Relative volume | Is today busier than normal? | ÷ 50-day average | Nothing (≤ 0.17) | Judging breakouts, climaxes, dry-ups |
| On Balance Volume | Volume on up days minus down days, running | — | A running total: trend | Divergences against price |
| A/D line | Where the close sits in the range, × volume, running | — | A running total: trend | Divergences; input to the Chaikin Oscillator |
| Chaikin Money Flow | Closes near highs or lows, on heavy days? | 20 | Chaikin Oscillator (0.71); RSI (0.58) | Buying or selling pressure over a month |
| Chaikin Oscillator | Is the A/D line speeding up? | 3, 10 | Ultimate Oscillator (0.76) | Turns in the A/D line |
| Money Flow Index | A volume-weighted RSI | 14; lines 80 / 20 | Vortex spread (0.85); 14-day % change (0.76) | Overbought/oversold, as RSI |
| Force Index | Price change × volume | 13 (and 2) | Envelope position (0.70) | Short-term pushes; pullback timing |
| Ease of Movement | Price move per unit of volume | 14 | Momentum (10) (0.71) | Easy moves on light volume |
| Distance from VWAP | How far above the volume-weighted average? | 20 | 14-day % change (0.92) | Levels; extension |
| Volume by price | Where did the most shares trade? | A chosen period | — | Support and resistance zones |

## 12. What the evidence says

> **Method.** US: a random 300 stocks; India: all 147 that qualify. Each has at least 1,500 sessions since 2015 and a large daily traded value. Every indicator was computed on daily bars at its default settings. Correlations were measured day by day within each stock over 2015 to October 2026; the figures are medians across stocks. Today's listed stocks only, so failed companies are missing.

**Relative volume stands alone.** Its correlations with five other readings ran only from −0.10 to 0.11. Those were RSI, the 14-day % change, the distance from the 50-day, ATR % and ADX. Its closest twin anywhere was the Mass Index, at 0.17.

**Most volume indicators are mostly price.**

| Indicator | Closest reading (US) | US | India |
|---|---|---|---|
| Distance from 20-day VWAP | 14-day % change | 0.92 | 0.91 |
| Money Flow Index | Vortex spread (+VI − −VI) | 0.85 | 0.86 |
| Money Flow Index | 14-day % change | 0.76 | 0.79 |
| Ease of Movement | Momentum (10) | 0.71 | 0.65 |
| Force Index | Envelope position (20, 2.5%) | 0.70 | 0.64 |
| Chaikin Money Flow | RSI (14) | 0.58 | 0.61 |
| Chaikin Oscillator | RSI (14) | 0.55 | 0.53 |

So adding MFI to a chart that already shows RSI adds almost nothing. Chaikin Money Flow and the Chaikin Oscillator are partly their own: about half price, half something else.

**Running totals cannot be compared this way.** OBV and the A/D line add up day after day. A correlation between two running totals mostly says whether both trended over the same years. Their day-to-day links with RSI were near zero. OBV and the A/D line agreed in the US (0.74) and disagreed in India (−0.50), for the gap reason in section 4.

**Divergences are not tested.** "OBV fails to confirm a new high" is the classic use of OBV and the A/D line. This guide has not measured whether it predicts anything.

**Published research.**

- Gervais, Kaniel and Mingelgrin (2001) found that stocks with unusually high volume over a day or a week tended to do slightly better over the following month.
- Lee and Swaminathan (2000) found that past trading volume helps predict how strong and how lasting price momentum is.
- Blume, Easley and O'Hara (1994) argued in theory that volume carries information that prices alone do not.

**Limits.** Correlation shows overlap, not predictive power. Today's listed stocks only. No costs. Daily bars only, so intraday VWAP and volume profiles are not measured.

## 13. Checklist

- [ ] Am I reading volume as relative volume, against the stock's own 50-day average?
- [ ] Do I have MFI or Force Index beside RSI? They say mostly the same thing.
- [ ] An OBV or A/D divergence: is there a price level and a stop, not just the divergence?
- [ ] An Indian stock with a falling A/D line: is it just gaps up and fades inside the day?
- [ ] Is a volume spike explained by results, an index change, expiry or a block deal?
- [ ] Am I comparing Force Index or Chaikin Oscillator values across stocks? Their units do not allow it.
- [ ] Is there a VWAP anchor or a high-volume price nearby that could act as support or resistance?

## Further reading

- Joseph Granville, *Granville's New Key to Stock Market Profits* — On Balance Volume.
- Alexander Elder, *Trading for a Living* (1993) — the Force Index.
- Richard Arms, *Volume Cycles in the Stock Market* — Equivolume and Ease of Movement.
- James F. Dalton, Eric T. Jones and Robert B. Dahlquist, *Mind Over Markets* — market profile and value areas.
- Simon Gervais, Ron Kaniel and Dan Mingelgrin, "The High-Volume Return Premium", *Journal of Finance* (2001).
- Charles Lee and Bhaskaran Swaminathan, "Price Momentum and Trading Volume", *Journal of Finance* (2000).
- Lawrence Blume, David Easley and Maureen O'Hara, "Market Statistics and Technical Analysis: The Role of Volume", *Journal of Finance* (1994).
