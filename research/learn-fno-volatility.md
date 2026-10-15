# Volatility for option traders — implied, realised, skew and crush

**In short**

- Realised volatility is how much a price actually moved. Implied volatility is how much movement option prices are paying for. Options are priced on the second and paid out on the first.
- India VIX is the Nifty's 30-day implied volatility. Since 2015 it has been above the Nifty's next-month realised volatility on about 4 days in 5. That gap is what option sellers earn on average, and what they lose in a crash.
- Implied volatility is not the same at every strike: in Nifty options, out-of-the-money puts cost more volatility than calls. That pattern is the skew.
- Implied volatility differs by expiry too (the term structure), and it collapses after a known event such as an election result. That collapse is volatility crush.
- IV rank and IV percentile say whether volatility is high or low for that underlying. They answer different questions and can disagree sharply.

This guide builds on [Options basics](learn-fno-options-basics.md) and [Option pricing and the Greeks](learn-fno-pricing-greeks.md). The market-wide view of volatility, as a gauge of fear for stock traders, is in [the volatility and sentiment guide](learn-health-volatility.md).

Option figures below come from NSE's option chains at about 10.15 am IST on 15 October 2026, during trading. They are one snapshot, not history. Daily index figures come from closing prices; section 10 says how they were computed.

---

## 1. Two numbers for one market

On 14 October 2026 the Nifty 50 closed at 22,622.70. Two volatility numbers described it that evening:

| Measure | Value | What it is |
|---|---|---|
| India VIX | 14.62 | The volatility that Nifty options were pricing for the next 30 days |
| Nifty 20-day realised volatility | 14.75 | How much the Nifty had actually moved over the last 20 sessions |

Both are written the same way: as an **annualised standard deviation, in percent**. A standard deviation is the typical size of a move, up or down. A volatility of 14.6% means a typical move of about 14.6% over a year.

**Realised volatility** looks back. You take the daily percentage changes of the closing price, measure their standard deviation, and scale it up to a year by multiplying by √252 (there are about 252 trading days in a year). It is a fact about the past.

**Implied volatility** looks forward. It is the volatility that makes an option-pricing model match an option's market price. It is not a forecast anyone made; it is a price. If options are expensive, implied volatility is high.

On this date the two were almost equal. That was unusual, as section 4 shows. Usually implied sits above realised.

## 2. From volatility to an expected move

A yearly figure is hard to use. Scale it down by the square root of time:

| Period | Divide annual volatility by | India VIX of 14.62 becomes |
|---|---|---|
| One year | 1 | ±14.6% |
| One month | √12 ≈ 3.5 | ±4.2% |
| One week | √52 ≈ 7.2 | ±2.0% |
| One day | √252 ≈ 15.9 | ±0.92% |

These are one-standard-deviation moves. If returns followed a bell curve, about two periods in three would stay inside them.

The option chain gives the same answer directly. On the morning of the snapshot the 27 October at-the-money straddle cost 453.8 points. A straddle is a call plus a put at the same strike. Its price is about 0.8 times the expected one-standard-deviation move to expiry. So the options were pricing a typical move of roughly ±570 points, or ±2.5%, by 27 October.

How did the Nifty's real moves compare with what the India VIX implied? Over every trading day from 2015, comparing the VIX with the Nifty's move over the next 21 sessions:

| | Bell curve would give | What the Nifty did (2015–2026) |
|---|---|---|
| Month's move inside ±1 standard deviation | 68% | 74% |
| Month's move beyond ±2 standard deviations | 4.6% | 2.9% |

Most months were quieter than options priced. That is the first sign of the gap studied in section 4.

## 3. India VIX through the years

```series
title: India VIX and the Nifty 50, 2010–2026
from: 2010-01-01
tf: W
line: india:INDIAVIX | India VIX
line: india:NIFTY50 | Nifty 50 | right log
caption: India VIX spikes when the Nifty falls hard and drifts down while it climbs. The highest close, 83.61, came on 24 March 2020; the lowest, 9.15, on 26 December 2025.
```

Since 2010, India VIX has spent most of its time in a fairly narrow band:

| Percentile of daily closes, 2010–2026 | India VIX |
|---|---|
| 10th | 12.0 |
| 25th | 13.7 |
| Median | 16.4 |
| 75th | 20.2 |
| 90th | 24.5 |

Three features of the chart matter for option traders.

**Volatility comes in clusters.** Calm weeks follow calm weeks, and wild weeks follow wild ones. After the March 2020 crash India VIX took months to settle.

**Spikes are short; calm is long.** India VIX shot from 17.0 on 24 February 2020 to 83.61 a month later. It then spent most of 2023 to 2025 below 16.

**It falls when the market rises.** The VIX is mostly a price for protection against a fall. When the Nifty drops, demand for puts jumps, and implied volatility jumps with it.

What happened next, after different VIX readings? Over all days since 2010, here is India VIX now and 21 sessions later:

| India VIX reading | Days | Median VIX 21 sessions later | Share of cases where it was lower |
|---|---|---|---|
| Below 12 | 410 | 11.8 | 30% |
| 12 to 16 | 1,494 | 14.2 | 47% |
| 16 to 20 | 1,131 | 17.4 | 53% |
| 20 to 25 | 700 | 20.5 | 64% |
| 25 and above | 365 | 23.6 | 88% |

High readings usually fall back, and low readings usually drift up. This **mean reversion** is one of the most reliable patterns in volatility. It says nothing about when: a VIX of 25 can become 50 before it becomes 15.

## 4. Implied versus realised: the volatility premium

Since 2015, India VIX has had a median of **15.3**. The Nifty's 20-day realised volatility has had a median of **12.3**. Implied has usually been the higher of the two.

The fair test compares today's India VIX with the volatility the Nifty went on to show over the **next** 21 sessions. Over 2,863 trading days from January 2015 to September 2026:

| Result | Value |
|---|---|
| Days when India VIX was above the next month's realised volatility | 80% |
| Median gap (India VIX minus next month's realised) | 3.3 points |

This gap is the **volatility risk premium**. Option buyers, on average, pay for more movement than they get. Sellers, on average, collect it. Studies of US index options have found the same thing over decades; Carr and Wu (2009) and Bakshi and Kapadia (2003) are two well-known examples.

The average hides the cost. On 24 February 2020 India VIX was **17.0**. Over the next 21 sessions the Nifty's realised volatility was about **76**. A seller who sold options that day at a volatility of 17 then lived through moves priced for more than four times that.

The premium exists because it is payment for this risk. Sellers earn small amounts most months and give back a large amount in the rare crash. Whether selling is worth it depends on surviving those crashes, which is a question of position size. See the risk guides, starting with [position sizing](learn-risk-sizing.md).

The premium also varies a lot from year to year. It was smallest in 2026 so far, on 64% of days. It was largest in 2017, on 99% of days.

## 5. IV rank and IV percentile

A Reliance option at 25% implied volatility and a Nifty option at 14% are both normal for their underlyings. To judge whether implied volatility is high, compare it with its own past. Two common measures do that, usually over the last year:

- **IV rank**: where today's level sits between the year's low and high. (Today − low) ÷ (high − low).
- **IV percentile**: the share of days in the last year when implied volatility was lower than today.

India VIX on 14 October 2026 shows how far apart they can be:

| | Value |
|---|---|
| India VIX on 14 Oct 2026 | 14.62 |
| Lowest in the past year | 9.15 (26 Dec 2025) |
| Highest in the past year | 27.89 (30 Mar 2026) |
| IV rank | 29 |
| IV percentile | 70 |

The rank says volatility is low: it sits only 29% of the way from the year's low to its high. The percentile says it is fairly high: it was higher than on 70% of the year's days.

The difference comes from one spike. The March 2026 high stretched the range, so every later level looks low by rank. Most of the year was calm, so a middling level looks high by percentile.

Use the percentile when the year contains a one-off spike. Use either with caution after a regime change, such as the end of a long calm spell. Neither tells you whether implied volatility is high **relative to the realised volatility that will follow**, which is what an option trade is really betting on.

## 6. The skew: implied volatility by strike

If the Black-Scholes model were exactly right, every strike on one expiry would show the same implied volatility. It doesn't. Here are Nifty options for the 27 October expiry, using the out-of-the-money option at each strike: puts below the index, calls above it.

| Strike | Option used | Implied volatility |
|---|---|---|
| 22,000 | Put | 17.3% |
| 22,200 | Put | 16.2% |
| 22,400 | Put | 15.3% |
| 22,600 | Put | 14.5% |
| 22,800 | Put | 13.9% |
| 22,900 (at the money) | Call and put | 13.6% |
| 23,000 | Call | 13.4% |
| 23,200 | Call | 13.0% |
| 23,400 | Call | 12.9% |
| 23,600 | Call | 12.9% |
| 23,800 | Call | 13.3% |
| 24,000 | Call | 14.1% |

The 22,000 put, about 4% below the index, was priced at a volatility of 17.3%. The 23,800 call, about 4% above, was priced at 13.3%. Protection against a fall cost more, in volatility terms, than a bet on a rise of the same size.

This tilted shape is the **skew**, sometimes called the smirk. Index options have shown it in most markets since the US crash of October 1987. Before that crash, US index options showed little of it. Rubinstein (1994) documents the change. Three reasons are usually given:

- **Indices fall faster than they rise.** Big down days are more common than big up days, so far puts pay out more often than the bell curve allows.
- **Portfolio managers buy puts as insurance**, and few people sell it willingly. Demand lifts the price.
- **Volatility rises when prices fall.** A put pays off just when implied volatility jumps, which makes it worth more.

Single stocks often show more of a **smile**: both ends higher than the middle. Reliance on the same morning, 27 October expiry:

| Strike | Option used | Implied volatility |
|---|---|---|
| 1,100 | Put | 29.1% |
| 1,150 | Put | 26.1% |
| 1,180 | Put | 24.4% |
| 1,200 (at the money) | Call and put | 24.7% |
| 1,220 | Call | 25.4% |
| 1,250 | Call | 27.9% |
| 1,300 | Call | 32.0% |

A stock can jump either way on news, so upside calls are also in demand. Wings far from the money also trade less, and their wider bid–ask spreads add noise to these numbers.

What the skew means in practice:

- **Out-of-the-money puts are dear; out-of-the-money calls are cheap**, compared with the at-the-money option. Spreads that sell a far put and buy a nearer one collect this difference, and carry the crash risk it pays for.
- **A fall lifts the at-the-money volatility.** As the index drops, the new at-the-money strike is one that was already priced at a higher volatility.

The exchange's chain prints its own implied volatility for each option. In this snapshot the 22,900 call showed 12.2%, while the put at the same strike showed 15.0%. The same strike and expiry should carry one volatility. The gap comes from the calculation's assumptions, such as the interest rate and the price used for the index. The figures in this guide were recomputed from mid prices with one forward price per expiry, so calls and puts agree (section 10).

## 7. The term structure: implied volatility by expiry

The same comparison across expiries gives the **term structure**. Here is the at-the-money implied volatility for each expiry in the snapshot:

| Underlying | Near expiry | Implied volatility | Later expiry | Implied volatility |
|---|---|---|---|---|
| Nifty 50 | 19 Oct (4 days) | 13.9% | 27 Oct (12 days) | 13.6% |
| Nifty Bank | 27 Oct (12 days) | 15.0% | 23 Nov (39 days) | 13.9% |
| Reliance | 27 Oct (12 days) | 24.7% | 23 Nov (39 days) | 25.1% |

In calm markets, near-term implied volatility is usually **below** longer-term volatility. Uncertainty grows with the horizon, and the curve slopes up. In stressed markets the curve **inverts**: near expiries carry the higher volatility, because the danger is now.

On this morning the Nifty and Bank Nifty curves were slightly inverted. The Nifty had fallen about 15% from its January high to its low on 8 October, so a nervous near term fits. Reliance's curve sloped gently upward.

A scheduled event shows up as a bump. An expiry just after a company's results, a central bank decision or an election carries extra volatility. The expiry just before it does not. Comparing the two tells you how big a move the market expects from the event alone. The guide on event trades, in the Futures & options section, shows how to work it out.

## 8. Volatility crush

The 2024 general election in India shows the full cycle.

```series
title: India VIX and the Nifty 50 around the 2024 election result
from: 2024-04-01
to: 2024-07-15
tf: D
line: india:INDIAVIX | India VIX
line: india:NIFTY50 | Nifty 50 | right
mark: 2024-06-04 | Result day
caption: India VIX doubled in the weeks before the result, peaked on the day, and was back near its April level ten days later.
```

| Date | India VIX | Nifty 50 close | What happened |
|---|---|---|---|
| 23 Apr 2024 | 10.20 | — | Low point before the run-up |
| 31 May 2024 | 24.60 | 22,530.70 | Last trading day before the exit polls |
| 3 Jun 2024 | 20.94 | 23,263.90 | Up 3.3% after the exit polls |
| 4 Jun 2024 | 26.75 | 21,884.50 | Result day: down 5.9% |
| 7 Jun 2024 | 16.88 | 23,290.15 | Back above the 3 June close |
| 14 Jun 2024 | 12.82 | — | Near April levels |

Implied volatility built up for a month because everyone knew a big announcement was coming. Once the result was known, the uncertainty it priced was gone. India VIX fell by more than a third in three sessions, even though the market had just had a 5.9% day.

Here is what that did to an option buyer, in a model illustration. Take an at-the-money Nifty straddle at strike 22,550 with 30 days left, priced on 31 May with India VIX as its volatility.

| | 31 May 2024 | 7 Jun 2024 | 7 Jun, if volatility had stayed at 24.6 |
|---|---|---|---|
| Nifty | 22,530.70 | 23,290.15 | 23,290.15 |
| Days left | 30 | 23 | 23 |
| Volatility used | 24.6% | 16.9% | 24.6% |
| Model value of the straddle | about 1,267 | about 1,042 | about 1,317 |

The buyer lived through two large moves and still lost about 18% in a week. Without the fall in implied volatility the same straddle would have shown a gain. The difference, about 275 points, is the crush.

The same happens to stock options after quarterly results, and to index options after a policy decision or a budget. The rule: **an event that everyone can see coming is already in the price**. To profit from buying options into it, the move has to beat what the options priced, not just be large.

## 9. What can go wrong

- **Treating high implied volatility as a sell signal by itself.** India VIX at 25 usually falls, but sometimes goes to 80. The 2020 numbers in section 4 are the risk you are paid to take.
- **Treating low implied volatility as free money for buyers.** Cheap options can stay cheap for months while time decay eats them.
- **Comparing implied volatility across underlyings.** Reliance at 25% and the Nifty at 14% were both ordinary. Compare an underlying with its own history.
- **Reading IV rank alone.** One spike in the last year can make every later level look low.
- **Using the exchange's printed implied volatility without checking.** Calls and puts at one strike can show different numbers because of the calculation's assumptions.
- **Buying options into a known event without asking what move is priced.** The crush can cost more than the event's move pays.
- **Forgetting that realised volatility is also an estimate.** A 20-day window jumps when one big day enters or leaves it.

## 10. How the numbers here were made

**Realised volatility.** From daily Nifty 50 closes. Daily log returns, their standard deviation over the window, times √252, in percent. In outline:

```
r[t]       = ln(close[t] / close[t-1])
realised20 = stdev(r over the last 20 sessions) * sqrt(252) * 100
forward21  = stdev(r over the next 21 sessions) * sqrt(252) * 100   # known only afterwards
```

**Implied versus realised.** India VIX on each day from January 2015 against the forward 21-session realised volatility (2,863 days, the last in September 2026). The VIX covers 30 calendar days, about 21 sessions, so the match is close but not exact.

**Expected move test.** The Nifty's absolute change over the next 21 sessions against India VIX ÷ √12, every day from 2015.

**VIX after VIX.** Every India VIX close from 2010, grouped by level, compared with the close 21 sessions later. Days overlap, so the cases are not independent; read the table as a description, not as proof.

**Skew and term structure.** From the 15 October 2026 snapshot. Mid prices of the best bid and ask. The forward price for each expiry from put-call parity at the three strikes nearest the index. Black-Scholes in its forward form, time to 3.30 pm on expiry day, interest rate 6.5%. Strikes with no two-sided quote were left out.

**Election illustration.** A model, not traded prices: India VIX used as the volatility of a 30-day straddle, interest rate 6.5%.

## 11. Checklist

- What is the implied volatility of the option I am trading, and what has the underlying's realised volatility been over 20 and 60 days?
- Is implied high or low against its own past year? Do IV rank and IV percentile agree? If not, why?
- Where does my strike sit on the skew? Am I buying expensive volatility (far puts) or cheap volatility (far calls)?
- Is there a scheduled event before expiry? How much extra volatility does the expiry after it carry?
- If I am selling volatility, what happens if implied volatility doubles and the underlying moves 5% against me?
- If I am buying volatility, how large and how fast must the move be to beat the premium and the likely crush?

## Further reading

- Sheldon Natenberg, *Option Volatility and Pricing* — chapters on volatility, the skew and volatility trading.
- Euan Sinclair, *Volatility Trading* — how to measure realised volatility and trade it against implied.
- Peter Carr and Liuren Wu, "Variance Risk Premiums", *Review of Financial Studies* (2009).
- Gurdip Bakshi and Nikunj Kapadia, "Delta-Hedged Gains and the Negative Market Volatility Risk Premium", *Review of Financial Studies* (2003).
- Mark Rubinstein, "Implied Binomial Trees", *Journal of Finance* (1994) — documents the index skew that appeared after 1987.
- NSE, *India VIX* white paper — how the index is calculated from Nifty option prices.
