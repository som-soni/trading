# Futures & options — the map

**In short**

- A **future** is a promise to buy or sell later at a price fixed today. An **option** is a right to buy or sell at a fixed price, bought for an upfront fee.
- Traders use them for four jobs: leverage, hedging, income from selling options, and taking a view on how much prices will move.
- In India the main market is NSE: index futures and options on the Nifty 50 and a few other indices, plus futures and options on about 200 stocks.
- The odds are poor for most individuals. SEBI's own studies found that roughly 9 in 10 individual F&O traders lost money.
- This page explains what each tool does, who should use it, and the order in which to read the rest of the section.

## 1. Two contracts, one example

On the morning of 15 October 2026 (10:15) the Nifty stood at about 22,907. Two traders each expected it to rise over the next two weeks. One bought a Nifty **futures** contract. The other bought a Nifty **call option**.

A futures contract is an agreement to buy (or sell) the index at a fixed price on a fixed date, the **expiry**. Nifty futures trade in **lots** — fixed bundles of units. One lot of Nifty is 65 units, so each point the index moves is worth ₹65 per lot. The October future traded at 22,940, so one lot controlled about ₹14.9 lakh of index.

A call option is the right, but not the duty, to buy at a fixed price (the **strike**) on expiry. The buyer pays a fee for that right, the **premium**. The 23,000 call for 27 October cost ₹187.9 per unit. One lot of 65 therefore cost about ₹12,200, paid in full upfront.

Here is what each position made or lost at expiry, for a few possible Nifty levels.

| Nifty at expiry (27 Oct) | Long 1 lot future bought at 22,940 | Long 1 lot of 23,000 call bought at ₹187.9 |
|---|---|---|
| 22,000 | −₹61,100 | −₹12,214 |
| 22,500 | −₹28,600 | −₹12,214 |
| 23,000 | +₹3,900 | −₹12,214 |
| 23,500 | +₹36,400 | +₹20,287 |
| 24,000 | +₹68,900 | +₹52,787 |

*Prices at 10:15 on 15 October 2026, during trading; they moved later that day. Profit and loss ignores costs.*

```payoff
title: Long one lot of Nifty futures (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22000 24000
leg: buy future @ 22940
caption: A straight line: every point up earns ₹65 per lot, every point down loses ₹65. The loss has no floor.
```

```payoff
title: Long one lot of the Nifty 23,000 call (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22000 24000
leg: buy call 23000 @ 187.9
caption: A hockey stick: the most the buyer can lose is the premium paid. Above the breakeven near 23,188 every point earns ₹65.
```

The two shapes are the whole difference in one picture. The future is a straight line: gains and losses are symmetric and the loss is open-ended. The option is bent: the buyer's loss stops at the premium, and in exchange the index must first travel past the strike plus the premium before the buyer earns anything.

The seller of that call has the mirror image. The seller collects ₹12,214 upfront, keeps it if Nifty stays below 23,000, and loses without limit above about 23,188. Every option has a buyer and a seller, and their results add up to zero before costs.

## 2. What they are for — four jobs

Each job below starts from a concrete case.

| Job | Example | What you give up |
|---|---|---|
| Leverage | One lot of Nifty futures controls ₹14.9 lakh for a deposit of a small fraction of that | A fall hurts as much as a rise helps, and losses can exceed the deposit |
| Hedging | An investor holding ₹30 lakh of shares sells two lots of Nifty futures before a risky event | The gain if the market rises; the hedge also removes the upside |
| Income | An options seller sells a call or put far from the current price and keeps the premium if the price stays away | Small, frequent gains in exchange for rare, large losses |
| A view on volatility | A trader buys both a call and a put before an event, betting on a big move in either direction | The premium, if the move turns out smaller than the options assumed |

**Leverage** means controlling a large position with a small deposit. The deposit is called **margin** in F&O; it is a good-faith amount the broker and exchange hold against losses. Leverage multiplies both outcomes. The guide on futures basics shows how fast a margin deposit can disappear.

**Hedging** means taking a position that gains when your main holding loses. It is the original purpose of these markets. A hedge costs something: either the premium of a put option, or the upside you give away with a short future.

**Income** usually means selling options. The seller collects premium and wins most of the time. The rare loss can wipe out months of gains, which is why sizing for sellers is a separate subject.

**Volatility** is how much a price swings. Option prices depend on how much the market expects the underlying to move, called **implied volatility**. You can trade that expectation itself, which no share or future lets you do.

## 3. Futures and options side by side

| | Futures | Options (buyer) | Options (seller) |
|---|---|---|---|
| What you hold | An obligation to buy or sell at expiry | A right, not an obligation | An obligation, if the buyer exercises |
| Cash paid upfront | Margin (a deposit), not a price | The full premium | Margin; you receive the premium |
| Most you can lose | Open-ended | The premium | Open-ended for a naked seller |
| Effect of time passing | Small (the gap to the index shrinks) | Works against you every day | Works for you every day |
| Effect of a rise in implied volatility | None directly | Helps | Hurts |
| Daily cash flows | Profit and loss settled in cash every day | None until you sell or expiry | Margin can rise as the position moves against you |

**Underlying** is the asset a contract is written on — the Nifty 50 index, Reliance shares, and so on. Futures move almost one-for-one with their underlying. Options move by a changing fraction of it, which the guide on [pricing and the Greeks](learn-fno-pricing-greeks.md) explains.

## 4. The Indian market in brief

India's equity derivatives trade mainly on NSE, with BSE offering contracts on the Sensex. The busiest contracts are index options, above all on the Nifty 50. Stock futures and options exist on a list of roughly 200 large, liquid companies.

The table shows NSE's official lot sizes for the October 2026 contracts.

| Contract | Lot size (units) | Underlying |
|---|---|---|
| Nifty 50 | 65 | The 50 largest NSE companies |
| Nifty Bank | 30 | The largest banks |
| Nifty Financial Services | 60 | Banks, lenders and insurers |
| Nifty Midcap Select | 120 | A selection of mid-sized companies |
| Nifty Next 50 | 25 | The next 50 companies after the Nifty 50 |
| Reliance Industries | 500 | One company's shares |

A few rules shape everything that follows. Each is explained properly in its own guide.

- **Expiry.** Monthly contracts expire on the last Tuesday of the month, moved earlier when that day is a holiday. Nifty also has weekly option expiries.
- **Settlement.** Index futures and options are settled in cash. Stock futures and options are settled by **physical delivery**: an open position at expiry becomes a real purchase or sale of shares.
- **Contract size.** From late 2024 SEBI raised the minimum value of an index derivative contract to about ₹15 lakh. Lot sizes are reviewed from time to time, so the value drifts with the price.
- **Upfront margin.** Brokers must collect margin before a trade, and option buyers pay the full premium upfront.
- **Costs and tax.** Securities transaction tax (STT) applies on the sell side, and was raised in October 2024 and again from 1 April 2026. Profits are taxed as business income. The [India rules guide](learn-fno-india-rules.md) covers both.

**In the US.** Stock options are American style: they can be exercised on any day, not only at expiry. Index options such as those on the S&P 500 are mostly European and cash-settled. US options trade in penny or nickel increments, there is no STT, and options expiring the same day (0DTE) are a large share of S&P 500 option volume. Individual stock futures barely trade in the US; traders short shares directly by borrowing them.

## 5. The honest odds

```series
title: Nifty 50 around the 2024 election result
from: 2024-04-15
to: 2024-07-15
tf: D
line: india:NIFTY50 | Nifty 50
mark: 2024-06-04 | Results day: −5.9%
caption: On 4 June 2024 the Nifty closed 1,379 points lower than the day before. At today's lot of 65 that is about ₹89,700 lost per long futures lot in one session.
```

Consider a trader long one lot of Nifty futures into the 2024 general-election results. On 4 June 2024 the index fell from 23,264 to 21,885 in one session. At today's lot size that is a loss of about ₹89,700 in a day. That is several times a typical daily move, and it arrived in a single session.

SEBI has studied how individual traders actually fare. A January 2023 study of the 2021–22 financial year found that about 89% of individual F&O traders lost money. A September 2024 study covered the three financial years to March 2024. It found that about 93% lost money over that period. Their combined losses over those three years came to about ₹1.8 lakh crore.

Four reasons account for most of it:

1. **Costs on every trade.** Brokerage, exchange charges, STT and the bid–ask spread are paid on each round trip. Frequent traders pay them hundreds of times a year.
2. **Leverage without a stop.** A small deposit controls a large position, so an ordinary adverse move can take most of the deposit.
3. **Option buyers fight time.** An option loses value every day the price does not move enough. Cheap far-away options mostly expire worthless.
4. **Option sellers carry hidden tail risk.** Selling premium wins often and loses rarely but heavily. One bad day can undo a year.

None of this makes F&O useless. It means the tools reward a plan, a cost estimate and strict sizing, and punish impulse.

## 6. Who should — and should not — trade them

F&O suits a trader who already has a tested approach in shares and wants a specific tool for a specific job. Typical good reasons are a hedge before a known risk, a short position held for days (which Indian cash markets do not allow), or a defined-risk way to take a view.

It does not suit someone looking for a faster way to grow a small account. It also does not suit anyone who cannot watch positions daily, or who has no written rules for size and exits. If you cannot say in advance what you will lose if you are wrong, the trade is not ready.

| Question to ask yourself | A good sign | A warning sign |
|---|---|---|
| Why use a derivative instead of shares? | It does something shares cannot (hedge, short, define risk) | It is cheaper to get a bigger position |
| What is the most you can lose? | A number you wrote down before entering | "The stop will handle it" with no gap allowance |
| How much of your capital is margin? | A small part; the rest is buffer | Almost all of it |
| Have you counted costs? | Yes, per round trip, and they fit the expected gain | No |

## 7. What can go wrong

- **A gap past your stop.** Prices can open far beyond your stop after news, so the loss is larger than planned. The futures basics guide measures how often this happens on the Nifty.
- **A margin call.** Losses are taken from your account daily. If the balance falls below the required margin, the broker can close positions at a bad price.
- **Physical delivery.** An in-the-money stock option or a stock future held into expiry turns into a real share trade worth many lakhs.
- **Illiquid contracts.** Far-dated or far-from-the-money contracts can have wide bid–ask spreads, so entering and leaving costs more than the screen suggests.
- **Rule changes.** SEBI and the exchanges revise lot sizes, margins and expiry schedules. Always check the current rules before trading.

## 8. Reading order

Read these in order. Each builds on the ones before it.

**Futures**

1. [Futures basics](learn-fno-futures-basics.md) — lots, contract value, margin, daily settlement, expiry and rollover.
2. [Futures basis and open interest](learn-fno-futures-basis.md) — why a future trades above the index, what rolling costs, and what open interest can and cannot tell you.
3. [Trading and hedging with futures](learn-fno-futures-trading.md) — leveraged longs, swing shorts, hedging a portfolio with Nifty futures, and pair trades.

**Options**

4. [Options basics](learn-fno-options-basics.md) — calls and puts, moneyness, intrinsic and time value, exercise and settlement.
5. [Pricing and the Greeks](learn-fno-pricing-greeks.md) — what moves an option's price.
6. [Volatility](learn-fno-volatility.md) — implied against realised volatility, India VIX, the skew.
7. [The option chain](learn-fno-option-chain.md) — open interest by strike, the put/call ratio, liquidity.
8. [Expiry dynamics](learn-fno-expiry.md) — weekly and monthly expiries, time decay, expiry-day rules.

**Option strategies**

9. [Directional trades](learn-fno-directional.md) — long calls and puts, and debit spreads.
10. [Income strategies](learn-fno-income.md) — covered calls, credit spreads, iron condors.
11. [Volatility strategies](learn-fno-vol-strategies.md) — straddles, strangles, butterflies, calendars.
12. [Hedging with options](learn-fno-hedging.md) — protective puts and collars.
13. [Event trades](learn-fno-event-trades.md) — results, RBI policy, the Budget, elections.

**Rules and risk**

14. [India's rules, costs and tax](learn-fno-india-rules.md) — the full cost of a round trip.
15. [Risk and position sizing in F&O](learn-fno-risk-sizing.md) — how accounts blow up, and how to avoid it.

Before you start, two existing guides are worth reading: [Position sizing](learn-risk-sizing.md) and [Volatility and sentiment](learn-health-volatility.md).

## 9. Checklist

- [ ] I can say which of the four jobs this trade does: leverage, hedge, income or volatility.
- [ ] I know the lot size and the full contract value, not just the margin.
- [ ] I have written down the most I can lose, including a gap past my stop.
- [ ] My margin uses a small part of my capital, with the rest left as a buffer.
- [ ] I have estimated round-trip costs and they are small next to the expected gain.
- [ ] I know when the contract expires and how it settles (cash or delivery).
- [ ] I have checked the current exchange rules, not last year's.

## Further reading

- John C. Hull, *Options, Futures, and Other Derivatives* — the standard textbook on how these contracts work and are priced.
- Sheldon Natenberg, *Option Volatility and Pricing* — the practitioner's book on options and volatility.
- Lawrence G. McMillan, *Options as a Strategic Investment* — a reference for option strategies.
- SEBI, *Analysis of Profit and Loss of Individual Traders dealing in Equity F&O Segment* — the January 2023 and September 2024 studies.
- NSE Academy, *Equity Derivatives* study material — the exchange's own introduction to contract specifications.
