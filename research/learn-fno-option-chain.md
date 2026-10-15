# Reading an option chain — what the table tells you, and what it doesn't

**In short**
- An option chain lists every strike of one expiry, with calls on the left and puts on the right.
- For a trade, the useful columns are the bid, the ask, the volume and the implied volatility. The last price can be stale.
- Open interest counts the contracts still open. Its change shows where new positions are building, but not who opened them.
- The put/call ratio, max pain and "support from open interest" are popular readings. The evidence for them as forecasts is weak.
- Liquidity falls fast away from the current price and in later expiries. Check the bid–ask spread before you trade any strike.

All numbers in this guide come from one real snapshot of NSE's option chains, taken at about 10:15 on 15 October 2026. Prices moved during the day. The snapshot is one moment, not a history, so treat every figure as an illustration of how to read the table.

## 1. A chain, row by row

On the morning of 15 October 2026 the Nifty stood at 22,906.55. It had fallen about 10% from its August high and was bouncing. Here is a slice of the chain for the monthly expiry of 27 October 2026, around the current price.

```series
title: Nifty, July to October 2026 — the backdrop to the snapshot
from: 2026-07-01
to: 2026-10-14
line: india:NIFTY50 | Nifty
line: india:NIFTY50@sma50 | 50-day average
mark: 2026-10-08 | low of the fall
caption: The index fell from about 24,770 on 3 August to about 22,230 on 8 October. The snapshot was taken on the morning of 15 October, during a bounce.
```

| Call last | Call bid / ask | Call IV % | Call OI | **Strike** | Put last | Put bid / ask | Put IV % | Put OI |
|---|---|---|---|---|---|---|---|---|
| 513.55 | 513.10 / 514.25 | 11.9 | 48,897 | **22,500** | 90.35 | 90.30 / 90.50 | 15.8 | 79,199 |
| 365.35 | 364.25 / 365.45 | 12.2 | 62,029 | **22,700** | 140.00 | 140.00 / 140.30 | 15.3 | 60,422 |
| 299.00 | 298.75 / 299.85 | 12.2 | 63,711 | **22,800** | 173.00 | 173.15 / 173.65 | 15.1 | 42,354 |
| 240.00 | 239.50 / 240.25 | 12.2 | 36,365 | **22,900** | 214.00 | 213.60 / 214.25 | 15.0 | 13,946 |
| 187.90 | 187.90 / 188.35 | 12.2 | 119,085 | **23,000** | 263.00 | 262.30 / 263.15 | 15.0 | 59,345 |
| 108.60 | 108.55 / 108.85 | 12.2 | 73,347 | **23,200** | 381.25 | 381.25 / 382.45 | 15.3 | 27,350 |
| 41.25 | 41.15 / 41.30 | 12.3 | 141,548 | **23,500** | 611.00 | 613.30 / 615.70 | 16.6 | 78,738 |

*Nifty options expiring 27 October 2026, at about 10:15 on 15 October 2026. Nifty 22,906.55. One lot is 65 units. IV = implied volatility. OI = open interest in contracts.*

Read one row at a time. The 23,000 strike has a call whose best bid was 187.90 and best ask 188.35. A buyer paying the ask for one lot pays 188.35 × 65, about ₹12,240. On the same row, the 23,000 put cost about 263.

Calls below the current price are in the money: they already have intrinsic value (the amount by which the option is in the money). Puts above the current price are in the money for the same reason. Many chain screens shade the in-the-money side so you can see where the current price sits.

The strike in the middle is the at-the-money strike, the one closest to the current price. Here it is 22,900. Most trading happens within a few strikes of it.

## 2. The columns that matter for a trade

**Bid and ask.** The bid is the best price someone will pay right now. The ask is the best price someone will sell at. A market order to buy fills at the ask; a market order to sell fills at the bid. The gap between them is a cost you pay on every round trip.

**Last price.** This is the price of the most recent trade, which may be minutes old. In the snapshot the 22,000 call (27 October) showed a last price of 950. Yet its bid was 951.35 and its ask 954.45, both above the last trade. The market had moved since that trade. Use the midpoint of bid and ask to value an option, not the last price.

**Volume.** The number of contracts traded today. It tells you whether a strike is active now. A strike with a large open interest and almost no volume today is hard to trade quickly.

**Implied volatility.** The volatility that makes a pricing model return the option's market price. It is the market's price of expected movement, quoted per year. In the slice above, puts carry higher implied volatility than calls at the same strike, and far put strikes are higher still. That pattern is the skew; [Volatility](learn-fno-volatility.md) covers it.

**Bid and ask quantity.** The number of units waiting at the best bid and ask. For Nifty these are multiples of 65, the lot size. A large order can use up the best level and fill at worse prices.

## 3. Open interest and its change

Open interest is the number of contracts that are open at a strike. Every open contract has one buyer and one seller. When a new buyer trades with a new seller, open interest rises by one. When both sides close existing positions, it falls by one. When one side hands its position to a new trader, it does not change.

The snapshot shows where open interest piled up for the weekly expiry of 19 October 2026, four days away.

| Strike | Call OI | Call OI change | Put OI | Put OI change |
|---|---|---|---|---|
| 22,500 | 39,273 | −8,527 | 163,359 | +57,706 |
| 22,600 | 50,679 | −17,959 | 140,980 | +57,427 |
| 22,700 | 81,646 | −57,575 | 201,217 | +137,673 |
| 22,800 | 99,526 | −9,707 | 138,724 | +115,297 |
| 22,900 | 101,686 | +9,015 | 52,670 | +45,070 |
| 23,000 | 140,610 | −33,230 | 30,941 | +17,557 |
| 23,200 | 106,181 | −12,145 | 3,819 | +2,175 |
| 23,500 | 115,846 | −35,037 | 4,046 | −187 |
| 24,000 | 124,373 | −14,616 | 2,848 | −351 |

*Nifty options expiring 19 October 2026, at about 10:15 on 15 October 2026. The change is measured from the previous day's close, so it covers only the first hour of trading.*

Two things stand out. Put open interest rose sharply at 22,700 and 22,800, just below the current price. Call open interest fell at almost every strike above it. The index was up more than 1% that morning.

Notice what the table does not tell you. A rise of 137,673 contracts at the 22,700 put means that many new contracts were opened. Each has a buyer and a seller. The table cannot say which side started the trade, or why.

## 4. Reading open-interest change with price

Traders often combine the price change with the open-interest change. The usual labels come from the futures market, where they are a little more meaningful.

| Price | Open interest | Usual label | The usual story |
|---|---|---|---|
| Up | Up | Long build-up | New buyers are paying up |
| Down | Up | Short build-up | New sellers are pressing |
| Up | Down | Short covering | Sellers are closing, which pushes the price up |
| Down | Down | Long unwinding | Buyers are closing, which pushes the price down |

Apply it to the 19 October puts. The index rose, and put open interest at 22,700 jumped. Puts lose value when the index rises, so the usual story is "put writers are selling puts below the market". That is a bullish reading: writers expect the index to stay above 22,700.

The story may be true. But the same numbers fit other stories. A fund may have bought those puts to protect a portfolio, with a market maker on the other side. An arbitrage desk may have opened a put as one leg of a larger trade. The chain shows contracts, not motives.

Here is the position the usual story assumes: one lot of the 22,700 put sold for its last price of 140 in the monthly expiry.

```payoff
title: Selling one Nifty 22,700 put (27 Oct 2026 expiry) — the trade "put writing" assumes
underlying: 22906.55
lot: 65
range: 21800 23600
leg: sell put 22700 @ 140
before: 6d 15%
caption: The seller keeps ₹9,100 (140 × 65) if the Nifty is above 22,700 at expiry. Below the breakeven of 22,560 the loss grows by ₹65 for every point the index falls.
```

## 5. The put/call ratio

The put/call ratio divides put open interest (or volume) by call open interest (or volume). Here are the snapshot's values, summed over every strike of each expiry.

| Chain | Put/call ratio, open interest | Put/call ratio, volume |
|---|---|---|
| Nifty, 19 Oct 2026 (weekly) | 1.45 | 0.73 |
| Nifty, 27 Oct 2026 (monthly) | 0.97 | 0.88 |
| Bank Nifty, 27 Oct 2026 | 1.02 | 0.82 |
| Reliance, 27 Oct 2026 | 0.60 | 0.32 |

*At about 10:15 on 15 October 2026. Volume is the morning's volume only.*

The same morning gave four different numbers. The weekly Nifty chain read 1.45 on open interest but 0.73 on volume. Stock chains usually run below 1, because more traders buy and sell calls on single stocks.

Two opposite readings circulate. One says a high ratio is bearish, because many traders buy puts. The other says it is bullish, because heavy put buying marks fear near a low, or because puts are being written by confident sellers. Both are guesses about who opened the trades.

The ratio is more useful compared with its own past for the same chain than as an absolute level. A weekly chain's ratio also swings with the calendar. As expiry nears, positions close and new ones open in the next week.

## 6. Max pain

Max pain is the strike at which option buyers, taken together, would receive the least money if the index settled there at expiry. To compute it, pick a settlement price. For each strike, add up what every call and put would be worth at expiry. Repeat for each candidate price and pick the lowest total.

| If the Nifty settles at | Calls pay (₹ crore) | Puts pay (₹ crore) | Total (₹ crore) |
|---|---|---|---|
| 22,700 | 470 | 3,930 | 4,399 |
| 22,800 | 632 | 3,590 | 4,223 |
| 22,900 | 841 | 3,283 | 4,124 |
| **23,000** | 1,077 | 2,987 | **4,065** |
| 23,100 | 1,394 | 2,731 | 4,125 |
| 23,200 | 1,736 | 2,489 | 4,224 |

*Intrinsic value at expiry of all open Nifty options for 27 October 2026, using open interest at about 10:15 on 15 October 2026 and a lot of 65 units. The minimum is the max-pain strike.*

For the 27 October chain, max pain was 23,000, about 0.4% above the index. For the 19 October chain it was 22,800. For Reliance's October chain it was 1,200, almost exactly at its price.

The theory behind it says option writers, as a group, push the index toward max pain to keep their premiums. Look at the table again. Moving the settlement from 22,900 to 23,000 changes the total by about ₹60 crore. That is small next to the daily value traded in Nifty futures and stocks.

Max pain also moves every day as open interest changes, and it tends to sit near the current price. Treat it as a description of where open interest is, not a target.

## 7. "Support and resistance from open interest" — weak evidence

A common reading says the strike with the largest put open interest is support and the strike with the largest call open interest is resistance. In the 27 October chain the largest call open interest was at 23,500 and the largest put open interest at 22,000.

| Rank | Calls: strike | Calls: OI | Puts: strike | Puts: OI |
|---|---|---|---|---|
| 1 | 23,500 | 141,548 | 22,000 | 83,863 |
| 2 | 23,000 | 119,085 | 22,500 | 79,199 |
| 3 | 24,000 | 98,249 | 23,500 | 78,738 |

*Nifty options expiring 27 October 2026, at about 10:15 on 15 October 2026.*

Round numbers collect open interest whatever the market thinks, because traders like round strikes. The list also contains 23,500 on both sides. Nobody can use that strike as both support and resistance.

There is a real mechanism behind the idea, but it is narrow. If dealers who hedge are net long options at a strike, their hedging (selling as the price rises, buying as it falls) can damp moves near that strike close to expiry. Dealers net short options do the opposite and can speed moves up. The chain does not show which side dealers are on. So a big number at a strike tells you there is interest, not which way it pushes.

## 8. Liquidity: the bid–ask spread by strike and expiry

The spread as a share of the option's price is what you lose by crossing it once. It grows quickly for cheap, far-away strikes and for later expiries.

| Contract (snapshot) | Bid / ask | Spread as % of mid | Open interest |
|---|---|---|---|
| Nifty 22,900 call, 19 Oct | 146.25 / 146.45 | 0.14% | 101,686 |
| Nifty 22,900 call, 27 Oct | 239.50 / 240.25 | 0.31% | 36,365 |
| Nifty 24,000 call, 27 Oct | 9.20 / 9.30 | 1.1% | 98,249 |
| Nifty 25,000 call, 27 Oct | 1.05 / 1.10 | 4.7% | 47,659 |
| Bank Nifty 57,000 call, 27 Oct | 171.55 / 172.05 | 0.29% | 31,510 |
| Bank Nifty 60,000 call, 23 Nov | 56.30 / 59.20 | 5.0% | 6,212 |
| Reliance 1,200 call, 27 Oct | 23.15 / 23.25 | 0.43% | 26,376 |
| Reliance 1,400 call, 27 Oct | 0.70 / 0.75 | 6.9% | 6,755 |

*At about 10:15 on 15 October 2026.*

Near the money, Nifty and Bank Nifty options are among the most liquid in the world. A far strike costing a rupee or two is different. A spread of 5 paise on a ₹1.10 option is almost 5% each way.

Later expiries are thinner. On the snapshot morning the 19 October Nifty chain had traded about 22.5 million contracts. The 27 October chain had traded about 1.35 million. The November Bank Nifty chain was thinner still.

Stock options are thinner than index options. Reliance is one of the most active, and its near-the-money October strikes were tight. Its November strikes and far strikes were not.

## 9. Weekly, monthly and stock chains

The weekly chain closest to expiry is where most of the volume is. Its open interest also changes the most during the day, as short-term traders open and close. The monthly chain changes more slowly. Funds and hedgers use it more, and its open interest is a better record of positions that are held for weeks.

A stock chain has fewer strikes and less depth. In India, stock options are settled by delivery of the shares at expiry, not in cash. A stock chain's open interest close to expiry therefore also reflects traders closing positions to avoid delivery. [Indian F&O rules](learn-fno-india-rules.md) explains physical settlement.

## 10. What can go wrong

- **Trading off the last price.** It may be stale. Price limit orders from the bid and the ask.
- **Treating open-interest change as a signal of direction.** It tells you contracts were opened, not who opened them or why.
- **Reading one snapshot as a trend.** Open interest at 10:15 is not open interest at 15:30. Compare like with like: same time of day, same expiry type.
- **Using max pain as a target.** It moves every day and usually sits close to the current price, so it "predicts" little.
- **Buying cheap far strikes.** A ₹2 option has a wide spread in percentage terms and needs a large move just to pay it back.
- **Ignoring the expiry calendar.** A weekly chain changes character in its last two days. [Expiry](learn-fno-expiry.md) explains why.

## 11. What the evidence says

Option prices do carry information, but mostly through implied volatility and the skew, not through open-interest maps.

Pan and Poteshman (2006) found that a put/call ratio built from new buying volume, split by trader type, predicted US stock returns over the following week. That ratio used data the public does not see. The public put/call ratio from total volume or open interest carries much weaker information in later studies.

Ni, Pearson and Poteshman (2005) found that US stocks with listed options cluster near strike prices on expiry dates more than on other days. They link it to hedging by option holders and, in part, to traders who are short options. That is evidence for "pinning" at the close of expiry day. It is not evidence that open interest marks support or resistance during the month.

A rough check on the Nifty points the same way for the index: there is little to see. From March 2019 to October 2026 the index closed within 10 points of a round 100 on about 21% of weekly expiry days. On other days the share was about 18%. If closes landed at random, the share would be 20%. The method and caveats are in [Expiry](learn-fno-expiry.md).

What is not known: no public study shows that max pain or the largest open-interest strike forecasts the Nifty's settlement better than the current price does.

## 12. Checklist

- Is the chain for the expiry you mean to trade? Check the date at the top.
- What time is the snapshot? Open-interest change is measured from the previous close.
- Where is the at-the-money strike, and how far is your strike from it, in points and in percent?
- What are the bid and the ask? What is the spread as a share of the midpoint?
- Is there volume today at your strike, not just open interest?
- Is your strike's implied volatility high or low compared with its neighbours?
- Are you reading open-interest change as a fact (contracts opened) or as a story (who opened them)?
- Will you need to exit before expiry? Is the strike liquid enough to do that in a fast market?

## Further reading

- Sheldon Natenberg, *Option Volatility and Pricing* (2nd edition, 2015) — the standard practitioner text on reading option prices.
- John C. Hull, *Options, Futures, and Other Derivatives* — the textbook for definitions, settlement and pricing.
- Jun Pan and Allen Poteshman, "The Information in Option Volume for Future Stock Prices", *Review of Financial Studies* (2006).
- Sophie Ni, Neil Pearson and Allen Poteshman, "Stock Price Clustering on Option Expiration Dates", *Journal of Financial Economics* (2005).
- NSE's option-chain pages and its F&O FAQ, for the exchange's definitions of each column.
