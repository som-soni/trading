# Futures basis and open interest — the price of waiting, and what positioning can tell you

**In short**

- A future usually trades a little above the index. The gap, called the **basis**, is roughly the interest on the money you did not spend, minus the dividends you will not receive.
- On 15 October 2026 the three Nifty futures stood about 30, 130 and 261 points above the index, for one, two and three months.
- The basis shrinks to zero at expiry. A long futures holder pays it over time; a short holder collects it. Rolling a long position from one month to the next costs about the same rate.
- **Open interest** counts the contracts still open. Read with price, it hints at whether new positions are being built or old ones closed.
- Those hints are weak evidence. Every contract has a buyer and a seller, and many positions are hedges or arbitrage rather than bets.

## 1. Three prices for the same index

On the morning of 15 October 2026 the Nifty index stood at 22,909.85. Three Nifty futures were trading at the same moment, each a promise to buy or sell the same index on a different date.

| Contract | Futures price | Days to expiry | Basis (points) | Basis (% of index) | Basis, annualised |
|---|---|---|---|---|---|
| 27 October 2026 | 22,940.0 | 12 | 30.2 | 0.13% | 3.9% |
| 23 November 2026 | 23,040.1 | 39 | 130.3 | 0.57% | 5.3% |
| 29 December 2026 | 23,171.0 | 75 | 261.2 | 1.14% | 5.5% |

*Prices at about 10:15 on 15 October 2026, during trading; they moved through the day. Days are counted to the 3:30 pm close on expiry day. "Annualised" scales the percentage to a 365-day year.*

The further away the expiry, the higher the price. The gap grows roughly in proportion to time: each extra month added about 0.4–0.6% to the price. That pattern is not a forecast that the Nifty will rise. It is the cost of holding the index until each date.

## 2. Why the future costs more — the cost of carry

Picture two ways to own the Nifty for 75 days. You can buy the index's shares today, about ₹14.9 lakh for one lot's worth, and hold them. Or you can buy one lot of the December future and keep most of the cash in the bank.

The futures buyer earns interest on the cash they did not spend. The share buyer receives any dividends paid during those 75 days. If the future were priced at the index level, everyone would buy futures and bank the interest. So the futures price rises until the two routes cost the same. That difference is the **cost of carry**.

The usual approximation is:

```
fair futures price ≈ index × (1 + (interest rate − dividend yield) × days / 365)
```

Try it with an assumed interest rate of 6.5% a year and an assumed dividend yield of 1.2% for the Nifty. Both are round illustrative figures, not quoted market rates.

| Contract | Fair value at 6.5% and 1.2% | Actual price | Actual minus fair |
|---|---|---|---|
| 27 October 2026 | 22,950.5 | 22,940.0 | −10.5 |
| 23 November 2026 | 23,040.3 | 23,040.1 | −0.2 |
| 29 December 2026 | 23,160.1 | 23,171.0 | +10.9 |

The simple formula lands within about 11 points of each actual price. The rest is down to the exact rates traders use, the timing of dividends, and supply and demand for each contract.

**What keeps the price close to fair value.** If a future trades well above fair value, a trader can buy the shares, sell the future, and lock in the gap. This is **cash-and-carry arbitrage** — a trade that profits from a price difference without taking a view. If the future trades well below fair value, the reverse works for anyone holding the shares. Arbitrage funds and institutions do this all day, which pins the basis near its fair value.

The Reliance contracts that morning show the mechanics on one stock. The share stood at ₹1,200.4 and the October future at ₹1,204.3.

```payoff
title: Cash-and-carry on Reliance: buy 500 shares, sell one lot of the October future
underlying: 1200.4
lot: 500
range: 1100 1300
leg: buy stock @ 1200.4
leg: sell future @ 1204.3
caption: The two legs cancel. Wherever Reliance ends up on 27 October, the position earns the ₹3.9 basis on 500 shares, about ₹1,950 before costs.
```

The gross gain is about ₹1,950 on ₹6 lakh of capital for 12 days. Costs eat most of it for an individual. STT on a share purchase and sale held for delivery is 0.1% each way, about ₹1,200 on ₹6 lakh. Brokerage, exchange charges and the futures leg come on top. That is why this trade belongs to institutions with low costs and spare cash.

**A cross-check from the options market.** A call and a put at the same strike and expiry together imply a forward price — the price of the underlying for delivery on that date. That morning the 27 October 23,000 call cost ₹187.9. The put at the same strike cost ₹263.0. Their difference implies a forward near 22,925, close to the future's 22,940. The two quotes were taken about a minute apart.

## 3. Contango and backwardation

When futures trade above the spot price, the market is in **contango**. When they trade below it, it is in **backwardation**. An index future with interest rates above the dividend yield is normally in contango, as the Nifty was.

Single-stock futures vary more. The table shows the near-month basis for some of the 20 most active stock futures that morning.

| Stock | Spot price | Futures price (27 Oct) | Basis | Basis (% of spot) |
|---|---|---|---|---|
| Hindalco | 883.25 | 888.60 | +5.35 | +0.61% |
| Polycab | 8,315.0 | 8,345.0 | +30.0 | +0.36% |
| State Bank of India | 954.30 | 957.45 | +3.15 | +0.33% |
| Reliance | 1,200.4 | 1,204.3 | +3.9 | +0.32% |
| Infosys | 1,120.2 | 1,122.9 | +2.7 | +0.24% |
| HDFC Bank | 719.70 | 721.15 | +1.45 | +0.20% |
| Kotak Mahindra Bank | 440.90 | 441.00 | +0.10 | +0.02% |
| Angel One | 313.65 | 312.35 | −1.30 | −0.41% |
| Persistent Systems | 5,867.0 | 5,843.0 | −24.0 | −0.41% |
| HCL Technologies | 1,364.0 | 1,354.5 | −9.5 | −0.70% |
| Tech Mahindra | 1,629.9 | 1,615.9 | −14.0 | −0.86% |

*Prices at about 10:15 on 15 October 2026. Spot and futures prices were not captured at exactly the same second, so small gaps are noisy.*

A stock future below its spot price usually has one of two causes. The first is a dividend due before expiry: the share price will drop by the dividend, while the future does not receive it. The second is heavy demand to be short, often from traders who cannot short shares overnight in the cash market. A snapshot cannot say which applies; a check of the company's announced record dates usually can.

**Why it matters to a trader.** A short futures position in a stock that is in backwardation starts with a handicap. The future is already below the spot price and will rise toward it as expiry nears, if nothing else changes. A long position in strong contango pays the carry. Both are small next to a normal week's price move, but they are certain, while the price move is not.

## 4. The basis shrinks to zero at expiry

At expiry the future and the index must be equal, because the future settles at the index's closing value. So the basis always shrinks to zero. This is called **convergence**.

Take the November future at 23,040.1, 130.3 points above the index. Suppose the Nifty is exactly 22,909.85 again on 23 November. The future will have fallen to 22,909.85, and a long holder loses 130.3 points, about ₹8,500 per lot. The short holder gains the same amount.

That loss is not a fee anyone charged. It is the interest the long holder saved by not paying for the shares. A long futures position is economically a share position bought with borrowed money, at roughly the rate implied by the basis. Here that was about 5.3% a year.

## 5. What a roll costs

A trader holding a long Nifty position from month to month rolls it before each expiry. On 15 October the October future was 22,940.0 and the November future 23,040.1. The spread between them — the price of a **calendar spread**, one month against another — was 100.1 points.

| | Value |
|---|---|
| Spread, November minus October | 100.1 points |
| Per lot of 65 | about ₹6,500 |
| As a share of the October price | 0.44% |
| Days between the two expiries | 27 |
| Annualised | about 5.9% |

A long holder pays that spread when rolling, and a short holder collects it. Over a year, a long rolled monthly pays roughly the market interest rate on the full contract value, less dividends. That is similar to holding shares bought with a loan at that rate.

Rolling is not free beyond the spread. Each roll pays brokerage, exchange fees and STT on the sale, and the bid–ask spread on two contracts. Most traders roll in the last few sessions before expiry, when the next month is liquid enough.

Market commentators also follow the **rollover percentage**: the share of positions carried from the expiring month into the next. A high rollover with a rising spread is read as traders keen to stay long. Like the open-interest signals below, it describes positioning, not what happens next.

## 6. Open interest — what it counts

**Open interest** (OI) is the number of futures contracts that have been opened and not yet closed. It is different from volume, which counts every trade during the day.

Each trade has a buyer and a seller. What it does to open interest depends on whether each side is opening or closing:

| Buyer | Seller | Effect on open interest |
|---|---|---|
| Opens a new long | Opens a new short | Rises by one contract |
| Opens a new long | Closes an old long | Unchanged — a position changed hands |
| Closes an old short | Opens a new short | Unchanged — a position changed hands |
| Closes an old short | Closes an old long | Falls by one contract |

Open interest is concentrated in the nearest expiry. On the morning of 15 October 2026 the October Nifty future held about 85% of all open Nifty futures positions across the three months. The November contract held about 12% and December about 2%. In the last days before expiry, open interest moves from the near month to the next as traders roll.

## 7. Reading open interest with price

Traders combine the day's price change with the day's change in open interest. The four combinations have standard names in Indian markets.

| Price | Open interest | Name | The usual reading |
|---|---|---|---|
| Up | Up | Long build-up | New buyers are opening positions |
| Down | Up | Short build-up | New sellers are opening positions |
| Up | Down | Short covering | Shorts are buying back to close |
| Down | Down | Long unwinding | Longs are selling to close |

An illustrative sequence for a stock future over four sessions shows how the labels are applied. The numbers are made up for the example.

| Session | Futures price | Change | Open interest (lots) | Change | Label |
|---|---|---|---|---|---|
| 1 | 1,000 | — | 20,000 | — | — |
| 2 | 1,025 | +2.5% | 22,400 | +12% | Long build-up |
| 3 | 1,040 | +1.5% | 21,300 | −5% | Short covering |
| 4 | 1,010 | −2.9% | 23,200 | +9% | Short build-up |

The reading in session 2 is that new money arrived on the buy side. In session 3 the rise continued while positions closed, which suggests shorts were giving up rather than new buyers arriving. In session 4 new positions opened as the price fell. The labels tell you who was probably active. They do not tell you who will be right.

Exchanges publish daily open interest for every contract. Many brokers and data services show the four labels automatically for each stock future.

## 8. The limits — why this is weak evidence

**Every contract has two sides.** A rise in open interest means more longs *and* more shorts, in equal number. "Long build-up" names whichever side seems more eager from the price, not a majority.

**Many positions are not bets.** An arbitrage fund that buys shares and sells futures adds open interest on the short side with no view at all. So does an investor hedging a portfolio. A large short open interest can be mostly hedges.

**The calendar distorts the data.** Around expiry, open interest falls in the near month and rises in the next. Daily changes then reflect rolling, not new views.

**Small changes are noise.** A few percent change in open interest on one day is normal. The labels are applied to every move, however small.

**The research is thin.** Studies of commodity markets have found that growth in total futures open interest carried some information about future prices and the economy (Hong and Yogo, 2012). We are not aware of well-established published evidence that daily open-interest labels predict returns in Indian stock futures well enough to trade on alone. Treat them as context, alongside price, volume and the trend.

## 9. What can go wrong

- **Treating the basis as a forecast.** A future above the index says nothing about direction. It is interest, less dividends.
- **Forgetting that longs pay carry.** A leveraged long held for months pays roughly the interest rate on the full contract value through convergence and rolls.
- **Shorting into backwardation without checking dividends.** A stock future below spot may be pricing a dividend; the short loses that gap as expiry approaches.
- **Rolling late in a thin market.** On the last day the near month can be volatile and the next month's spread wide.
- **Reading open-interest labels as signals.** They describe who traded. They do not say what happens next, and many positions are hedges.
- **Mixing timestamps.** Spot, futures and options quotes taken seconds apart can show a basis that does not exist.

## 10. Checklist

- [ ] I know the current basis of my contract in points, in percent and annualised.
- [ ] I can explain the basis from interest and dividends, and I know if a dividend falls before expiry.
- [ ] I know what my next roll will cost, and when I plan to do it.
- [ ] For a long held for months, I have counted the carry as a cost.
- [ ] For a short, I have checked whether the future is already below spot, and why.
- [ ] I use open interest only as context, never as the reason for a trade.

Related guides: [Futures basics](learn-fno-futures-basics.md) for lots, margin and settlement; [Trading and hedging with futures](learn-fno-futures-trading.md) for how the basis affects shorts, hedges and pairs; the [map of this section](learn-fno-overview.md) for the rest.

## Further reading

- John C. Hull, *Options, Futures, and Other Derivatives* — the chapter on determining forward and futures prices.
- Bradford Cornell and Kenneth French, "Taxes and the Pricing of Stock Index Futures", *Journal of Finance*, 1983.
- A. Craig MacKinlay and Krishna Ramaswamy, "Index-Futures Arbitrage and the Behavior of Stock Index Futures Prices", *Review of Financial Studies*, 1988.
- Harrison Hong and Motohiro Yogo, "What Does Futures Market Interest Tell Us about the Macroeconomy and Asset Prices?", *Journal of Financial Economics*, 2012.
