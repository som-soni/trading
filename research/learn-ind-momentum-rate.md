# Momentum II — how fast the price is changing

**In short**

- These indicators measure change over time: how far the price has moved over some days, or how far it is from an average. Most are unbounded and swing around zero.
- Many of them are one number. Distance from the 50-day average, PPO, PMO and TSI correlated at 0.90 to 0.96 across hundreds of stocks; TRIX, KST and PMO at 0.96 to 0.98 with each other.
- The MACD histogram is mostly the change of the last two weeks. MACD and Momentum are in price units, so they cannot compare stocks; PPO and the distance in % or ATR can.
- Special K is the odd one out because it is slow: most of its weight is on changes over one to two years. DPO is different too: it compares an old price with today's average, so it measures short cycles, not trend.
- There are no fixed "overbought" lines. Compare a reading with the same stock's own past, and use it as a filter, not a trigger.

This guide covers the unbounded momentum readings: Rate of Change, Momentum, distance from a moving average, MACD, PPO, TRIX, TSI, KST, Pring's Special K, PMO and DPO. MACD is explained in depth in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md). The bounded readings, which place the close inside a range, are in [Momentum I — where the close sits in its range](learn-ind-momentum-range.md). For how the families fit together, see [Indicators — the map](learn-ind-map.md); for averages themselves, [Moving averages](learn-ind-moving-averages.md).

---

## 1. What this family measures

On 18 June 2024 Nvidia closed at $135.58. It had risen 18% in 14 sessions. It stood 36.6% above its 50-day average, which was 7.7 times its average daily range. By 7 August it had fallen 27%, to $98.91.

```series
title: Nvidia, March–October 2024 — distance from the 50-day average, in ATRs
from: 2024-03-01
to: 2024-10-31
line: us:NVDA | Nvidia
line: us:NVDA@sma(length=50).ma | 50-day average
line: us:NVDA@distma(unit=ATR).d | Distance from the 50-day, in ATRs | pane2 zero
mark: 2024-06-18 | 7.7 ATRs above
caption: On 18 June 2024 the close was 7.7 ATRs above the 50-day average. Seven weeks later it was 2.7 ATRs below it. The lower line is the gap between the price and the blue average, scaled by the stock's daily range.
```

The family's readings on those two days:

| Nvidia | 18 June 2024 | 7 August 2024 |
|---|---|---|
| Rate of Change (9 days) | +10.7% | −11.9% |
| Momentum (10 days) | +$19.14 | −$15.34 |
| Distance from 50-day | +36.6% (+7.7 ATR) | −17.8% (−2.7 ATR) |
| MACD line / histogram | 9.77 / +1.13 | −5.17 / −1.98 |
| PPO | +8.53 | −4.53 |
| TRIX | +1.26 | −0.40 |
| TSI | +54.4 | −18.0 |
| KST | +363 | −130 |
| Pring's Special K | +3,782 | +3,862 |
| PMO | +11.05 | −1.85 |
| DPO | −2.06 | +7.26 |

Nine readings flipped from positive to negative. Two did not. Special K stayed positive, because it looks back up to two years. DPO went the opposite way, because it compares an old close with today's average. Sections 8 and 10 explain both.

This family answers one question: how fast, and in which direction, is the price changing? A rate has no ceiling. A stock can rise 50% in a month, so there is no natural "overbought" line. A reading means something only against the same stock's own history.

## 2. Rate of Change and Momentum

**The question:** how much has the price changed over the last N days?

```
Rate of Change (ROC) = 100 × (close − close N days ago) ÷ close N days ago     default N = 9
Momentum             = close − close N days ago                                default N = 10
```

**Worked example.** Nvidia on 18 June 2024:

| Nvidia, 18 June 2024 | Value |
|---|---|
| Close | $135.58 |
| Close 9 sessions earlier (5 June) | $122.44 |
| ROC = 100 × 13.14 ÷ 122.44 | +10.7% |
| Close 10 sessions earlier (4 June) | $116.44 |
| Momentum = 135.58 − 116.44 | +$19.14 |

**What it repeats.** ROC (9) correlated 0.76 with RSI14 in the US. Its closest twin was the close's position in a 2.5% envelope around the 20-day average, at 0.90. In the US, Momentum (10) and ROC (9) correlated at 0.87.

**How traders use it.** A rise above zero says the price is higher than N days ago. That is the simplest trend filter there is. Over 3 to 12 months, the same idea is the momentum that research supports (section 12). The pitfalls: Momentum is in dollars or rupees, so a $19 move means one thing on Nvidia and another on a $20 stock. And both readings jump when an old, extreme day drops out of the window, even if today's price did not move.

## 3. Distance from a moving average

**The question:** how far is the close from its average, in % or in units of the stock's daily range?

```
% distance   = 100 × (close ÷ 50-day SMA − 1)
ATR distance = (close − 50-day SMA) ÷ 14-day ATR
```

ATR, the average true range, is the stock's average daily range; see [Indicators — trend and volatility](learn-price-indicators.md).

**Worked example.** Nvidia's two days from section 1:

| Nvidia | Close | 50-day average | % distance | 14-day ATR | ATR distance |
|---|---|---|---|---|---|
| 18 June 2024 | $135.58 | $99.28 | +36.6% | $4.73 | +7.7 |
| 7 August 2024 | $98.91 | $120.36 | −17.8% | $7.98 | −2.7 |

In June, 36.6% was 7.7 ATRs: extreme for this stock. In August, −17.8% was only 2.7 ATRs, because the daily range had almost doubled. The ATR version says how unusual the stretch is for the stock's current volatility.

**What it repeats.** The % distance from the 50-day correlated 0.88 with RSI14. Its closest twin was PPO, at 0.96 in both markets.

**How traders use it.** As an extension check: a stock far above its 20-day or 50-day in ATRs is stretched, and a new purchase there carries a wide stop. Some traders pass on entries more than about 2.5 to 4 ATRs above the 20-day. The pitfall: a stretch is not a top. By 18 June 2024, Nvidia had been more than 4 ATRs above its average for 17 sessions in a row.

## 4. MACD — the reference reading

MACD is the 12-day EMA minus the 26-day EMA. Its signal line is a 9-day EMA of MACD, and the histogram is the gap between the two. It is explained in [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

Two facts from the measurement matter here. The MACD line is close to the distance from an average: 0.89 with the 50-day distance in the US. The histogram is mostly the recent change. It correlated 0.72 with the 14-day % change. Its closest twin was Momentum, at 0.86.

MACD is also in price units, which is the reason PPO exists.

## 5. PPO — the Percentage Price Oscillator

**The question:** what is MACD as a share of the price, so it compares across stocks and across years?

```
PPO       = 100 × (12-day EMA − 26-day EMA) ÷ 26-day EMA
signal    = 9-day EMA of PPO;  histogram = PPO − signal
```

**Worked example.** Two Indian IT stocks on 1 August 2024:

| 1 August 2024 | TCS | Infosys |
|---|---|---|
| Close | ₹4,397 | ₹1,853 |
| MACD line | 123.2 | 80.0 |
| PPO | 2.95% | 4.60% |
| Distance from 50-day | 10.3% | 15.5% |
| TSI | 44.4 | 65.2 |
| KST | 111 | 182 |

MACD said TCS had the stronger short-term trend: 123 against 80. That was only because TCS's price was more than twice as high. As a share of price, Infosys was stronger, and every %-based reading in the table agreed.

**What it repeats.** PPO correlated at 0.96 with the distance from the 50-day, and 0.96 with PMO in the US. It is the same reading in different units.

**How traders use it.** Exactly as MACD: zero-line and signal-line crossings, and the histogram's slope. Use PPO when you compare stocks, rank them, or look back over years in which the price changed a lot.

## 6. TRIX

**The question:** how fast is a heavily smoothed average rising or falling, in % per day?

Jack Hutson introduced it. Smoothing three times removes most of the day-to-day noise; the 1-day change of what is left is the trend's speed.

```
EMA3   = 15-day EMA of the 15-day EMA of the 15-day EMA of the close
TRIX   = 100 × (EMA3 today − EMA3 yesterday) ÷ EMA3 yesterday
signal = 9-day EMA of TRIX
```

**Worked example.** On 18 June 2024 Nvidia's TRIX was +1.26: the triple-smoothed average rose 1.26% that day. On 7 August it was −0.40. On 1 August 2024 TRIX was 0.42 for TCS and 0.70 for Infosys.

**What it repeats.** Its closest twins were KST and PMO, both at 0.98 in the US. It correlated 0.88 with the distance from the 50-day.

**How traders use it.** A TRIX above zero and rising marks an established uptrend; zero and signal-line crossings are the signals. It is slow: it crossed zero about 6 times a year in the median stock. The pitfall is lag. By the time TRIX turns down, much of a sharp reversal is over.

## 7. TSI — the True Strength Index

**The question:** of all the recent daily movement, what share was in one direction?

William Blau designed it. It divides the smoothed daily change by the smoothed size of the daily change, so it runs from −100 to +100.

```
TSI    = 100 × EMA13(EMA25(daily change)) ÷ EMA13(EMA25(|daily change|))
signal = 13-day EMA of TSI
```

**Worked example.** Nvidia's TSI was +54.4 on 18 June 2024: over the smoothing window, the net move was about half of all the movement. On 7 August it was −18.0. A TSI near +100 would mean almost every day was an up day.

**What it repeats.** It correlated at 0.90 with the 50-day distance in the US and 0.92 in India. Its closest twin was PPO, at 0.92 and 0.95. It is bounded like RSI, but behaves like a rate: a smoothed trend reading.

**How traders use it.** Zero-line and signal crossings, and divergences. It is smoother than RSI and faster than TRIX.

## 8. KST and Pring's Special K

**The question:** what is the weighted sum of price changes over several lengths, each smoothed?

Martin Pring designed both. The KST ("know sure thing") adds four smoothed rates of change, giving more weight to the longer ones. Special K extends the same idea to twelve terms.

```
KST = 1 × SMA10(ROC10) + 2 × SMA10(ROC15) + 3 × SMA10(ROC20) + 4 × SMA15(ROC30)
KST signal = 9-day SMA of KST

Special K = the four KST terms, plus
            1 × SMA50(ROC40)   + 2 × SMA65(ROC65)   + 3 × SMA75(ROC75)   + 4 × SMA100(ROC100)
          + 1 × SMA130(ROC195) + 2 × SMA130(ROC265) + 3 × SMA130(ROC390) + 4 × SMA195(ROC530)
(ROC in days; 530 days is about two years)
```

**Worked example.** On 18 June 2024 Nvidia's KST was +363; on 7 August, −130. Its Special K was +3,782 and then +3,862. Over seven weeks the stock fell 27%, and Special K rose. Its long terms compared the price with where it stood one and two years earlier, when it was far lower.

```series
title: Nvidia, mid-2021 to mid-2023 — Special K through a 66% fall
from: 2021-07-01
to: 2023-06-30
line: us:NVDA | Nvidia | log
line: us:NVDA@specialk.sk | Pring's Special K | pane2 zero
caption: Nvidia fell 66% from 29 November 2021 to 14 October 2022. Special K fell from about 3,200 to a low of 62 in January 2023, but never went below zero. KST crossed zero 10 times over the same two years.
```

**What it repeats.** KST and TRIX correlated at 0.98 in the US and 0.99 in India. **Special K repeated almost nothing**: about 0.15 with RSI14 and 0.20 with the 50-day distance. A 530-day change is usually far larger than a 10-day change, so the long terms carry most of the sum. Special K answers a slower question: has the trend over many months turned?

**How traders use them.** Pring used KST's crossings of its signal line for medium-term turns. Special K was meant for the major turns of the long-term trend. Special K crossed zero about once a year in the median stock. The pitfall is scale: KST and Special K values are sums of percentages, so only the sign and direction mean anything.

## 9. PMO — the Price Momentum Oscillator

**The question:** what is the smoothed daily % change, smoothed again?

Carl Swenlin developed it for DecisionPoint. It smooths the daily % change twice. Its average uses the multiplier 2 ÷ n, not the usual 2 ÷ (n + 1).

```
step 1 = 35-day custom EMA of the 1-day % change (multiplier 2/35), times 10
PMO    = 20-day custom EMA of step 1 (multiplier 2/20)
signal = 10-day EMA of PMO
```

**Worked example.** Nvidia's PMO was +11.05 on 18 June 2024 and −1.85 on 7 August. On 1 August 2024 it was 3.45 for TCS and 5.81 for Infosys. The factor of 10 only sets the scale.

**What it repeats.** PMO correlated 0.92 with the 50-day distance in both markets. Its closest twin was TRIX, at 0.98. PMO, TRIX and KST give one reading three ways.

**How traders use it.** Crossings of its signal line, and its level against the stock's own past range. Because it is a % change, PMO values can be compared across stocks, unlike MACD.

## 10. DPO — the Detrended Price Oscillator

**The question:** is the price above or below its average for its own point in a short cycle?

The DPO removes the trend so short cycles stand out. It compares the close from about half a window ago with today's average, which is centred near that old close.

```
DPO = close (n ÷ 2 + 1) days ago − today's n-day SMA         default n = 20, so the close 11 days ago
```

**Worked example.** Nvidia on 7 August 2024: the close 11 sessions earlier, on 23 July, was $122.59. The 20-day average was $115.33. So DPO was +7.26, while the stock was in a 27% slide. The reading is about 23 July, not about 7 August.

**What it repeats.** DPO correlated **negatively** with short momentum: −0.64 with Momentum (10). When the price has just fallen, the old close is above today's average, so DPO is positive. It crossed zero about 57 times a year in the median stock, more than any other reading here.

**How traders use it.** To measure the length of short cycles: the distance between DPO's peaks. It is not a trend or timing reading for today. Many charting tools plot it shifted back by n ÷ 2 + 1 bars, which makes this clear.

## 11. The family side by side

| Indicator | Question it answers | Defaults | Mostly repeats | Typical use |
|---|---|---|---|---|
| Rate of Change | % change over N days | 9 | Envelope position (0.90) | Above/below zero; long-period trend filter |
| Momentum | Price change over N days, in price units | 10 | ROC (0.87), MACD histogram | As ROC; not comparable across stocks |
| Distance from MA | Close vs its average, in % or ATRs | 50; ATR 14 | PPO (0.96) | Extension checks |
| MACD | Fast EMA minus slow EMA | 12, 26, 9 | PPO; histogram ≈ Momentum (0.86) | Crossings; see the core guide |
| PPO | MACD as % of the slow EMA | 12, 26, 9 | Distance from 50-day (0.96) | Comparing stocks and years |
| TRIX | Daily % change of a triple EMA | 15, 9 | KST, PMO (0.98) | Slow trend speed |
| TSI | Net daily change ÷ total daily change, smoothed | 25, 13, 13 | PPO (0.92–0.95) | Smooth trend reading |
| KST | Weighted sum of four smoothed ROCs | 10/15/20/30; 9 | TRIX (0.98) | Medium-term turns |
| Special K | KST plus eight longer terms | 12 terms to 530 days | Nothing closely | Major turns over many months |
| PMO | 1-day % change, double-smoothed | 35, 20, 10 | TRIX (0.98) | Signal crossings; comparing stocks |
| DPO | Old close vs today's average | 20 | Momentum, inverted (−0.64) | Cycle length |

## 12. What the evidence says

### Most of these are one number

> **Method.** US: 300 stocks picked at random; India: all 147 that qualify. Each had at least 1,500 sessions since 2015 and a high median daily traded value. Every indicator used its default settings on daily bars. Correlations were measured day by day within each stock over 2015 to October 2026; the table shows the median across stocks. The stocks are ones listed today, so survivorship bias is possible.

| Median correlation (US / India) | RSI14 | 14-day % change | Distance from 50-day | Closest twin |
|---|---|---|---|---|
| Rate of Change (9) | 0.76 / 0.78 | 0.78 / 0.80 | 0.65 / 0.66 | Envelope position (0.90) |
| Momentum (10) | 0.74 / 0.75 | 0.77 / 0.74 | 0.63 / 0.62 | ROC (0.87) / MACD histogram (0.85) |
| Distance from 50-day | 0.88 / 0.89 | 0.77 / 0.78 | 1 | PPO (0.96) |
| MACD line | 0.76 / 0.76 | 0.69 / 0.68 | 0.89 / 0.85 | PPO (0.92 / 0.89) |
| MACD histogram | 0.57 / 0.57 | 0.72 / 0.69 | 0.37 / 0.35 | Momentum (0.86 / 0.85) |
| PPO | 0.80 / 0.82 | 0.74 / 0.75 | 0.96 / 0.96 | PMO (0.96) / distance (0.96) |
| TSI | 0.87 / 0.87 | 0.69 / 0.72 | 0.90 / 0.92 | PPO (0.92 / 0.95) |
| TRIX | 0.64 / 0.66 | 0.50 / 0.53 | 0.88 / 0.89 | KST (0.98 / 0.99) |
| KST | 0.66 / 0.68 | 0.56 / 0.57 | 0.88 / 0.89 | TRIX (0.98 / 0.99) |
| PMO | 0.71 / 0.72 | 0.58 / 0.59 | 0.92 / 0.92 | TRIX (0.98) |
| Special K | 0.15 / 0.12 | 0.08 / 0.07 | 0.20 / 0.17 | none above 0.41 |
| DPO | −0.32 / −0.32 | −0.39 / −0.38 | −0.25 / −0.24 | Momentum (−0.64) |

```series
title: Infosys, 2023 to mid-2025 — TRIX and KST
from: 2023-01-01
to: 2025-06-30
line: india:INFY.NS@trix.trix | TRIX (15)
line: india:INFY.NS@kst.kst | KST | right
caption: Two formulas, one line. For Infosys over these two and a half years, TRIX and KST correlated at 0.99, and TRIX and PMO at 0.99 too.
```

- **The distance from an average, PPO, TSI and PMO are one cluster** (0.90–0.96). **TRIX, KST and PMO are a tighter one** (0.96–0.98). Pick one slow reading and one fast one at most.
- **The MACD histogram belongs with the short rates of change**, not with the trend readings.
- **Special K and DPO are genuinely different**, for opposite reasons: one looks back two years, the other looks at a price from two weeks ago.

### How often each reading changes its verdict

Each crossing of zero changes the verdict from "rising" to "falling" or back. On the same sample:

| Zero crossings per year (median stock) | US | India |
|---|---|---|
| DPO (20) | 57 | 57 |
| Rate of Change (9) | 38 | 37 |
| Momentum (10) | 36 | 35 |
| MACD histogram | 20 | 20 |
| Distance from 50-day | 18 | 17 |
| MACD line | 9 | 8 |
| PPO | 9 | 8 |
| TSI | 9 | 8 |
| KST | 7 | 7 |
| TRIX | 6 | 6 |
| PMO | 6 | 6 |
| Special K | 1.4 | 0.9 |

Smoothing buys fewer reversals at the price of later ones. No reading gets both from the same prices.

### Published research

- **Medium-term momentum across stocks is the robust finding.** Jegadeesh and Titman (1993) found that US stocks with the best returns over the past 3 to 12 months went on to beat the worst over the following months. That compares stocks with each other, which a single stock's TRIX or PMO does not.
- **A market's own past trend has also carried forward.** Moskowitz, Ooi and Pedersen (2012) found that a futures market's return over the past 12 months predicted its next month's return, across many asset classes. That is the long-period Rate of Change used as a filter.
- **Very short-term moves have tended to reverse.** Jegadeesh (1990) found that individual stocks' monthly returns tended to reverse the next month; Lehmann (1990) found the same for weekly returns. A high 9-day ROC is not, on this evidence, a reason to expect more.
- **Single-indicator rules are mixed at best** once costs and the number of rules tried are counted; see [Momentum indicators — RSI, MACD and Bollinger Bands](learn-price-oscillators.md).

**Limits.** The sample holds today's listed stocks, so failed companies are missing. A correlation measures overlap, not predictive power. No costs are counted, and a fast reading that changes sign 38 times a year implies many trades.

## 13. Checklist

- [ ] Is the reading in price units (MACD, Momentum)? Then do not compare it across stocks or years; use PPO or the % distance.
- [ ] Do I have two of distance from an average, PPO, TSI, TRIX, KST and PMO on my chart? They say the same thing.
- [ ] How far is the close from its 20-day and 50-day, in ATRs? Is a new entry here too stretched for a sensible stop?
- [ ] Am I reading DPO as today's momentum? It describes a price from about two weeks ago.
- [ ] Am I using a short rate (9-day ROC) where I mean a long one (6 to 12 months)? Only the long one has research behind it.
- [ ] Has the reading crossed zero many times this year? Then each crossing is weak evidence.
- [ ] Is my entry and stop tied to a price level, not to the oscillator?

## Further reading

- William Blau, *Momentum, Direction, and Divergence* (1995) — TSI from its author.
- Martin Pring, *Technical Analysis Explained* (several editions) — rates of change and the KST.
- Gerald Appel, *Technical Analysis: Power Tools for Active Investors* (2005) — MACD from its author.
- Jegadeesh and Titman, "Returns to Buying Winners and Selling Losers" (*Journal of Finance*, 1993).
- Moskowitz, Ooi and Pedersen, "Time Series Momentum" (*Journal of Financial Economics*, 2012).
- Jegadeesh, "Evidence of Predictable Behavior of Security Returns" (*Journal of Finance*, 1990).
- Lehmann, "Fads, Martingales, and Market Efficiency" (*Quarterly Journal of Economics*, 1990).
