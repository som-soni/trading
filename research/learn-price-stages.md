# Stages and trend in a stock — where a stock is in its life, and whether to own it

**In short**

- Most stocks move through four stages: a sideways base (1), an advance (2), a sideways top (3) and a decline (4). Stan Weinstein read them off the 30-week moving average, about the 150-day on a daily chart.
- Buy in Stage 2, own nothing in Stage 4. Three questions tell you the stage: is the price above the average, which way does the average slope, and are the swings rising or falling?
- Swings turn first and averages confirm later. Mark Minervini's Trend Template turns Stage 2 into eight yes/no rules, but it passes only after a large part of the move.
- Measured on stored prices, a typical Stage 2 lasts five to six months from the day it qualifies. Most of the gain comes from a minority of long runs.
- A trend filter narrows the list to better-than-average stocks. It is not a trading system on its own: the entry, stop and exit still decide the result.

This guide is about the trend of a single stock. [The index trend guide](learn-health-trend.md) does the same for the whole market. For the basic words (moving average, 52-week high), start with [Start here](learn-start-here.md).

---

## 1. A stock's life in four stages

Trent, an Indian retailer, spent eighteen months going sideways from late 2021. Then it rose more than fivefold in sixteen months. It churned for three months at the top and then lost half its value. Section 4 walks through that chart.

Weinstein noticed that most stocks move through the same four phases, over and over. He read them off one line: the **30-week moving average** of weekly closes. On a daily chart the nearest equivalent is the **150-day** average (30 weeks × 5 sessions).

| Stage | What the price does | The 30-week line | Who is in control |
|---|---|---|---|
| **1 — Basing** | Moves sideways after a long fall; crosses the line back and forth | Stops falling, goes flat | Neither side. Sellers are running out |
| **2 — Advancing** | Makes higher highs and higher lows, stays above the line | Rising | Buyers. Demand is larger than supply |
| **3 — Topping** | Moves sideways after a long rise; swings get wider; crosses the line | Stops rising, goes flat | Neither side. Big holders are selling into strength |
| **4 — Declining** | Makes lower highs and lower lows, stays below the line | Falling | Sellers. Supply is larger than demand |

**Weinstein's rule is short: buy in Stage 2, own nothing in Stage 4.** Stage 1 can last for years and pays nothing while you wait. Stage 3 often looks like a base, but the buyers are now the late ones. A stock can also skip from Stage 2 straight to Stage 4 when bad news hits.

Why do stages exist at all? Large investors cannot buy or sell a big position in a day. A fund that wants to own a stock buys for months, and that steady buying is Stage 2. When funds decide to leave, they sell for months, and that is Stage 4. [The supply and demand guide](learn-supply-demand.md) explains the mechanism at the level of single price zones.

## 2. Reading the stage: position, slope and swings

Three questions tell you the stage. Ask them in this order.

### 2.1 Is the price above or below the average?

Look at Trent's advance in section 4. For 358 sessions the price did not close below its 150-day average once. Above that average, the buyers of the last several months are, on average, in profit. Below it they are, on average, holding a loss. Many of them will sell when the price gets back to what they paid.

### 2.2 Which way is the average sloping?

**A price above a falling average is a bounce, not an uptrend.** The slope is what separates a base from an advance, and a top from a decline. A screen needs a fixed definition of "rising" and "falling", so that it gives the same answer every time. Common choices look like this:

| Test | A typical fixed rule |
|---|---|
| 200-day **rising** (the Trend Template's test) | Higher than it was 21 sessions ago |
| 200-day **falling** | More than 0.5% below its value 20 sessions ago |
| 50-day **falling** | More than 1% below its value 10 sessions ago |
| 30-week line rising (weekly chart) | The 30-week exponential average is above last week's value, and the weekly close is above it |

Between "rising" and "falling" the average is **flat**. A flat 200-day after a long rise is the first sign of Stage 3. A flat one after a long fall is the first sign of Stage 1.

### 2.3 Are the swings rising or falling?

A trend is, before anything else, a sequence of swings: swing highs, and swing lows (troughs with higher prices on both sides). **An uptrend makes higher highs and higher lows. A downtrend makes lower highs and lower lows.**

Swings turn before averages do, because an average needs months of prices to change direction. So read swings for the early warning and the average for confirmation.

A simple mechanical check is that the last two swing lows of the past 50 or so sessions are rising. A common way to confirm a swing low is that its low is the lowest of the seven bars centred on it. That means three bars on each side.

## 3. Worked example: Nvidia, 2021–2023 — from Stage 4 to an early Stage 2

```series
title: Nvidia and its 150-day average, 2021–2023
from: 2021-06-01
to: 2023-12-31
tf: W
line: us:NVDA | Nvidia (split-adjusted) | log
line: us:NVDA@sma150 | 150-day average (≈ 30 weeks)
band: 2021-11-29 2022-10-14 | Stages 3 and 4
band: 2022-10-14 2023-01-31 | Stage 1
mark: 2022-10-14 | 2022 low
mark: 2023-04-14 | passes the Trend Template
caption: Lower highs all through 2022, a higher low in late December, the average turning up in February 2023 — and the Trend Template only passing in April, 138% off the low.
```

Prices here are adjusted for later stock splits, so they are lower than the prices quoted at the time.

- **Stage 3 to 4.** Nvidia closed at a record 33.38 on 29 November 2021. Its 200-day average stopped rising on 11 May 2022.
- **Stage 4.** Each rally stopped lower than the one before: swing highs of 28.7 (29 March), 19.6 (2 June), 19.2 (4 August) and 18.1 (13 December 2022). The lows fell too, to 11.23 on 14 October 2022: 66% below the record.
- **Stage 1.** The price first closed back above its 150-day on 11 November 2022 and above its 200-day on 12 December. On 28 December it made a low of 14.0, **above** the October low. That higher low is the first swing that points up.
- **Stage 2.** The 150-day stopped falling in mid-January 2023 and was rising by 1 February. The 50-day crossed above the 200-day on 24 January. The 200-day itself was rising again by 22 February.
- **The Trend Template passed on 14 April 2023**, at 26.76. By then the stock was already 138% above its October low. It then rose another 88% to 50.41 on 20 November 2023.

**The lesson: the Trend Template confirms Stage 2; it does not find its first day.** Its 200-day test needs months of rising prices. A trader who reads the swings and the 30-week line sees Stage 2 forming earlier, at a lower price. The cost is less certainty: many Stage 1 bases fail and sink again.

## 4. Worked example: Trent, 2022–2025 — a full four-stage cycle

```series
title: Trent and its 150-day average, 2022–2025
from: 2022-01-01
to: 2025-12-31
tf: W
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma150 | 150-day average (≈ 30 weeks)
band: 2022-01-01 2023-05-29 | Stage 1
band: 2023-05-30 2024-10-11 | Stage 2
band: 2024-10-11 2025-01-17 | Stage 3
band: 2025-01-20 2025-12-31 | Stage 4
mark: 2023-05-30 | breaks out of the range
mark: 2024-10-11 | peak
caption: Eighteen months sideways, sixteen months up (+428% from the breakout), three months of churning at the top, then a decline of half.
```

| Stage | Dates | What happened |
|---|---|---|
| 1 | Late 2021 – May 2023 | A range between about 998 (December 2021) and 1,558 (1 November 2022). The 150-day went flat; it was rising again from 1 March 2023 |
| 2 | 30 May 2023 – 11 Oct 2024 | First close above the 2022 high on 30 May 2023. Trend Template passed from 1 August 2023 at 1,708. Peak close 8,235 on 11 October 2024 |
| 3 | Oct 2024 – Jan 2025 | Closes between about 6,160 and 8,190. Last Trend Template pass on 6 January 2025 |
| 4 | Jan 2025 onward | First close below the 150-day on 10 January, below the 200-day on 20 January; the 150-day was falling from 18 February. Low of 4,018 on 10 December 2025, 51% below the peak |

**Stage 2 was a staircase.** The swing lows rose in four steps:

| Swing low | Price |
|---|---|
| July 2023 | 1,666 |
| October 2023 | 1,992 |
| February 2024 | 3,027 |
| July 2024 | 5,166 |

The swing highs rose with them. Over those 358 sessions the stock closed below its 50-day only five times. It never closed below its 150-day.

**Stage 3 showed in the swings before the averages.** The events after the 11 October 2024 peak, in order:

- 7 November 2024: a fall of 6.5% on 4.5 times average volume. The next day held a low of 6,299.
- 20 December: a second low at 6,832, higher than the first. The structure was still intact.
- 2 January 2025: the rally stopped at 7,321, a **lower high**.
- 10 January: the first close below the 150-day.
- 14 January: a close at 6,161, below the November low. That was the first **lower low**.
- 20 January: the first close below the 200-day. The 150-day itself only turned down a month later.

## 5. Worked example: Super Micro, 2022–2024 — late Stage 2, and a fast Stage 4

```series
title: Super Micro Computer and its 150-day average, 2022–2025
from: 2022-07-01
to: 2025-06-30
tf: W
line: us:SMCI | Super Micro (split-adjusted) | log
line: us:SMCI@sma150 | 150-day average (≈ 30 weeks)
line: us:SMCI / us:SMCI@sma200 | Price ÷ its 200-day | pane2
band: 2024-03-13 2024-08-01 | Stage 3
mark: 2024-03-13 | peak
caption: The lower pane shows how stretched the price was: 3.2 times its 200-day at the March 2024 peak. Five months of lower highs followed, then a fall of 85%.
```

Super Micro rose from a low of 3.90 on 5 July 2022 (split-adjusted) to 118.8 on 13 March 2024. That is about thirty-fold in 20 months. It passed the Trend Template on and off through 2022. It passed on most days of November and December, while the S&P 500 was in a bear market.

**The late stage was easy to see in one number: distance from the average.** In February 2024 the price stood at 3.4 times its 200-day average. At the peak it was 3.2 times. A stock that far above its long-term average has run far ahead of what most holders paid. Any selling then has a long way to fall before it reaches buyers.

Stage 3 then lasted about five months:

- **Lower highs:** 118.8 (13 March), 95.2 (15 May), 92.0 (18 June), 91.0 (12 July).
- **The averages held for a while:** first close below the 50-day on 12 April; last Trend Template pass on 15 May; first close below the 150-day on 24 July.
- **The break:** on 7 August 2024 the stock fell 20% in a day, on 2.7 times its average volume. That took it below the April low of 71.4 — the first lower low. It had closed below the 200-day on 2 August.
- **Stage 4:** on 28 August it fell another 19% on 4.7 times average volume. That followed a short-seller's report (a published case that the stock will fall) and a delay to the company's annual filing. The 150-day was falling from 16 September. The low was 18.01 on 14 November 2024, 85% below the peak.

**Extension alone does not mark the top.** Trent was 64% above its 150-day in February 2024 and still had eight months of rise ahead. Extension tells you the risk is high. The lower highs and the first lower low tell you the stage has changed.

## 6. Minervini's Trend Template

Minervini turned Stage 2 into eight yes/no rules. A stock must pass **all** of them. Nvidia passed on 14 April 2023 (section 3); Trent passed from 1 August 2023 (section 4).

| # | Rule | Usual setting |
|---|---|---|
| 1 | Close above the 50-day average | — |
| 2 | Close above the 150-day average | — |
| 3 | Close above the 200-day average | — |
| 4 | 50-day above the 150-day, and 150-day above the 200-day | — |
| 5 | 200-day higher than it was a month ago | 21 sessions |
| 6 | Close well above the 52-week low | at least 30% |
| 7 | Close near the 52-week high | within 25% |
| 8 | Relative strength (RS) rank high | 70 or more |

The 52-week high and low are the highest high and lowest low of the last 252 sessions. The averages are simple averages of daily closes.

**RS rank.** RS rank means relative strength rank: where the stock's recent performance stands against every other stock. A common recipe adds up four returns over the past year. The latest quarter's return counts twice; the 6-, 9- and 12-month returns count once. All stocks are then ranked from 1 to 99.

**An RS rank of 70 means the stock did better than about 70% of the market.** When you check a single stock, there is no whole market to rank against. A simple stand-in is to require a 12-1 month return of at least 10%. That is the return from a year ago to a month ago, skipping the latest month. [The relative strength guide](learn-price-rs.md) covers RS in depth.

The settings above are Minervini's minimums. His book prefers the 200-day to rise for four to five months, not one. It also prefers an RS rank of 80–90, not 70. A stricter trader can tighten either rule.

### 6.1 How often stocks pass

How many stocks pass on a typical day? We counted on month-end data, among liquid stocks only.

> **Method note.** 62 month-ends, August 2021 to September 2026, using point-in-time prices for each date. Liquid means: in the US, a price of at least $10 and at least $10 million traded per day (20-day average); in India, at least ₹50 crore traded per day. A stock also needs a year of history. RS rank is the full ranking across all liquid stocks. Caveats: today's stock lists (survivorship); a short period.

| | US | India |
|---|---|---|
| Liquid stocks per month-end (average) | about 1,760 | about 305 |
| Passing all eight (average) | about 335 | about 72 |
| Share passing, median month | 19% | 22% |
| Lowest | 2.5% (40 stocks, 30 June 2022) | 2.8% (9 stocks, 28 February 2025) |
| Highest | 32% (540 stocks, 30 August 2024) | 43% (151 stocks, 31 May 2024) |
| Latest (30 September 2026) | 12% (260 of 2,131) | 28% (118 of 415) |

**The pass rate is a breadth reading in its own right.** In the US it fell to 2.5% at the end of June 2022, in the middle of that year's bear market. In India it fell to 2.8% at the end of February 2025. The Nifty Midcap 50 was then 20% below its September 2024 high. When fewer than one stock in twenty passes, the few that do are worth a close look. They are the ones holding up while the market falls.

Which rule cuts the most? On the average month, these shares of liquid stocks passed each condition on its own:

| Condition | US | India |
|---|---|---|
| Close above the 50-day | 52% | 59% |
| Close above the 200-day | 55% | 65% |
| 200-day rising | 58% | 68% |
| At least 30% above the 52-week low | 53% | 64% |
| Within 25% of the 52-week high | 67% | 74% |
| RS rank 70+ | 37% | 39% |

The RS rule is the hardest single test, by design. The others mostly ask the same question — is the stock in an uptrend? — so they pass and fail together. That is why all eight together still pass about one stock in five.

## 7. Early Stage 2, late Stage 2, Stage 3: telling them apart

| | Early Stage 2 | Late Stage 2 | Stage 3 |
|---|---|---|---|
| Distance above the 200-day | Modest: the price close to its rising averages | Large: the price far above its averages | Shrinking as the price churns |
| Base count | First or second base | Third, fourth or later | The "base" is the top |
| Swings | Higher highs and higher lows | Still higher, but the moves are steeper | First lower high, then a lower low |
| 150/200-day | Just turned up | Rising steeply | Flattening |
| Volume | Heavy on up days | Climax days: the biggest gains on the heaviest volume | Heavy on down days |
| What to do | Buy sound breakouts | Hold winners; new buys smaller, stops tighter | Sell into strength; no new buys |

Base counting is covered in [the bases guide](learn-bases.md). Volume patterns are in [the volume guide](learn-price-volume.md).

## 8. How long does Stage 2 last?

Nvidia's Stage 2 ran for more than a year; many others end within weeks. To put a number on it, we scanned stored daily prices for **fresh Trend Template passes**. A fresh pass is the first day a stock passed all eight rules after six months without passing. Each case was followed until the stock **stopped being above a rising 200-day**.

> **Method note.** Daily prices for today's US and NSE stock lists; qualification dates from 2005 to the end of 2024. "Six months" is 126 sessions. The RS rule used the single-stock stand-in (12-1 month return of 10% or more). The stock had to clear the liquidity floor of section 6.1 on the day. The run ended at the first close below the 200-day, or the first day the 200-day was no higher than 21 sessions earlier. Caveats: survivorship (companies that went bust are under-counted); no costs; this is a measurement of the trend, not a trading test.

| After a fresh pass | US | India |
|---|---|---|
| Cases (stocks) | 8,455 (2,034) | 884 (354) |
| Median sessions above a rising 200-day | 107 (about five months) | 124 (about six months) |
| Middle half of cases | 57 to 175 sessions | 65 to 220 sessions |
| Ended within 3 months (63 sessions) | 28% | 24% |
| Lasted more than a year (252 sessions) | 11% | 19% |
| Median sessions to the first close below the 150-day | 79 | 91 |
| Median best gain before the end | +13% | +20% |
| Share that gained 50%+ at some point / doubled | 14% / 5% | 28% / 13% |
| Median return at the end (exit on the 200-day rule) | −3.8% | −2.5% |
| Average return at the end | +4.2% | +16% |

The picture is the same in both markets. **A typical Stage 2, measured from the day it qualifies, lasts five to six months.** The typical one makes little money if you wait for the 200-day to break before selling. Only 40% of US cases and 46% of Indian ones were up at that point. The average is pulled up by a minority of long runs:

| | US | India |
|---|---|---|
| Runs that ended within 3 months: median return at the end | −11% | −14% |
| Runs that lasted more than a year: median return at the end | +43% | +66% |
| Runs that lasted more than a year: median best gain | +69% | +106% |

The two samples differ. India's ₹50 crore floor is in today's rupees, so most Indian cases come from 2020 onward. The US cases spread across 2005–2024. Read the shape, not the decimals.

## 9. Do Stage 2 stocks do better?

### 9.1 A forward-return study

Do stocks that pass the Trend Template beat other stocks over the next few months? We applied the rules on each month-end and compared the qualifiers' returns with the average liquid stock.

> **Method note.** The same 62 month-ends and liquidity floor as section 6.1. "Excess" is the qualifiers' average return minus the average liquid stock's, over the next 1, 3 and 6 months. The "t" figure is a t-statistic: roughly, how far the result stands out from chance (about 2 or more is usually taken as meaningful). It is computed on 1-month returns only, because the 3- and 6-month windows overlap. Caveats: five years, no costs, survivors only.

| Trend Template | US | India |
|---|---|---|
| 1-month excess return | +0.46% (t 1.5) | +0.93% (t 2.4) |
| 3-month excess | +0.63% | +1.84% |
| 6-month excess | +2.53% | +2.67% |
| Hit rate (share of qualifiers beating the median stock), 6 months | 53% | 52% |
| Month-ends on which qualifiers won, 6 months | 75% | 62% |

Looser trend filters, over six months, for comparison:

| 6-month excess | US | India |
|---|---|---|
| Orderly uptrend on weekly and daily charts, near highs | +2.01% | +1.38% |
| Above a rising 200-day, within 15% of the 52-week high | +1.64% | +1.23% |
| Above the 200-day only | +1.50% | +0.84% |

**The stricter the trend filter, the better its stocks did**, in both markets. That is the order you would expect if the trend itself carries information. But look at the hit rate: only just over half of Stage 2 stocks beat the median stock. **The edge comes from a minority of big winners, not from most qualifiers doing well.** That matches section 8.

### 9.2 A filter is not a system

A trend filter only says which stocks to look at. It does not say when to buy, where the stop goes or when to sell. Section 8 shows why that matters: the typical Stage 2 run gave back its gain before the 200-day rule said sell.

Published research points the same way. Momentum portfolios have earned more than the market on average, but with rare, deep crashes, often when a bear market turns up sharply (Daniel and Moskowitz, 2016). Timing rules on a long average, such as a 10-month line, have mainly cut drawdowns on whole asset classes rather than raised returns (Faber, 2007). Neither result tells you how a single-stock trend rule will trade. That has to be tested with entries, stops and costs (see [Backtesting honestly](learn-test-backtesting.md)).

## 10. What the trader does

1. **Check the market's stage first** ([Reading the market's trend](learn-health-trend.md)). Most stocks move with the market. Traders hold that breakouts fail more often while the index falls; that guide explains why. A market-level filter is covered in [Regime filters](learn-strat-regime-filters.md).
2. **Fish in the Stage 2 list.** Start from the stocks passing the Trend Template. When the list is short, look at the names that stay on it: they are the leaders.
3. **Prefer early Stage 2.** The 30-week line just turned up, a first or second base, the price not far above its 200-day. A stock three times its 200-day is late, however strong it looks.
4. **Buy a setup, not a stage.** Stage 2 says *which* stock. The entry comes from a base and a breakout ([Bases](learn-bases.md), [VCP](learn-vcp.md)), with a stop under it ([Stops and exits](learn-risk-stops-exits.md)). Full methods built on Stage 2 are in [Stage analysis](learn-strat-stage-analysis.md) and [SEPA and the VCP](learn-strat-vcp-sepa.md).
5. **Watch the swings in the stocks you own.** The first lower high, then a lower low, is the Stage 3 warning. Sell into strength or tighten the stop. Do not wait for the 200-day: by then Trent was 26% off its peak and Super Micro 47%.
6. **Own nothing in Stage 4.** A stock below a falling 30-week line is not cheap; it is in a downtrend. Put it on a watchlist for the next Stage 1. Shorting Stage 4 is covered in [Shorting Stage 4 stocks](learn-strat-stage4-shorts.md).

## 11. What the evidence says

- **Robust:** stocks in Stage 2 have, on average, done better than other stocks over the next months. That held in the five-year study above in both markets, and in many published momentum studies. Stricter trend filters did better than looser ones.
- **Robust:** the gain is concentrated. Only about half of Stage 2 stocks beat the median stock, and the typical Stage 2 run lasted five to six months.
- **Lags are built in.** The Trend Template passed Nvidia 138% off its low. The 200-day rule confirmed Trent's top more than three months late. Swings turn first; averages confirm.
- **Not shown here:** that the Trend Template plus a chart pattern beats the index. The studies above measure the filter, not a trading method.
- **Limits of the studies:** today's stock lists (survivorship), no costs, a short period for the month-end study, and overlapping windows.
- **Folklore:** that a stage can be named exactly in real time. Stages are clear in hindsight. On the day, Stage 1 and Stage 3 look alike, and many Stage 1 bases fail.

## 12. Checklist

- [ ] Market stage: index above a rising 30-week line?
- [ ] Stock passes the Trend Template (or misses only on RS or the 200-day slope)?
- [ ] 150-day: rising, flat or falling? Has it changed this week?
- [ ] Swings: last high and last low higher than the ones before?
- [ ] How far above the 200-day? Early (modest) or late (stretched)?
- [ ] Base count: first or second base, or later?
- [ ] Open positions: any lower high followed by a lower low? Any stock now below a flattening 150-day?
- [ ] Share of stocks passing the Trend Template this week: rising or falling?

## Further reading

- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — the four stages and the 30-week moving average.
- Mark Minervini, *Trade Like a Stock Market Wizard* — the Trend Template and Stage 2 as the precondition for every buy.
- William O'Neil, *How to Make Money in Stocks* — leaders, relative strength and base counts.
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers" (Journal of Finance, 1993) — the academic evidence that past winners keep winning for months.
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes" (Journal of Financial Economics, 2016).
- Mebane Faber, "A Quantitative Approach to Tactical Asset Allocation" (Journal of Wealth Management, 2007).
