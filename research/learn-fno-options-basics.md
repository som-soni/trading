# Options basics — calls, puts and what you actually own

**In short**

- An option is a contract that gives its buyer a right, not an obligation: to buy (a call) or sell (a put) at a fixed price until a fixed date.
- The buyer pays a price up front, the premium. The most the buyer can lose is that premium; the seller keeps it but carries the risk.
- An option's price has two parts: what it would be worth if it ended now (intrinsic value) and a payment for the time left (time value).
- In India, index options are cash-settled and can only be exercised at expiry. Stock options end in real delivery of shares if they finish in the money.
- Every example below uses real NSE prices from one moment: 10.15 am on 15 October 2026, during the trading day.

All option prices in this guide come from NSE's option chains at about 10.15 am IST on 15 October 2026. They are a single snapshot taken while the market was open. Prices moved during the rest of the day, so treat them as a realistic illustration, not as a record of where anything closed.

---

## 1. One option, start to finish

At 10.15 am on 15 October 2026 the Nifty 50 index stood at **22,906.55**. It had risen about 1.3% that morning. A trader who expected it to keep rising could buy one **Nifty 23,000 call expiring on 27 October 2026**. The last traded price was **187.90**.

Here is what that trade means, piece by piece:

| Term | In this example | What it means |
|---|---|---|
| Underlying | Nifty 50 index | The thing the option is about |
| Call | The right to buy | A call gains when the underlying rises |
| Strike price | 23,000 | The fixed price in the contract |
| Expiry | 27 Oct 2026 | The last day the option exists |
| Premium | 187.90 points | The option's price, paid by the buyer |
| Lot size | 65 | Options trade in fixed bundles; one Nifty lot covers 65 units of the index |
| Cash paid | 187.90 × 65 = ₹12,213.50 | Premium times lot size |

Index points convert to rupees one-for-one per unit. So one Nifty lot gains or loses ₹65 for every point the option's price moves.

Now jump to expiry. Say the Nifty settles at **23,400** on 27 October. The call lets its owner "buy" the index at 23,000 when it is worth 23,400. So the option is worth 400 points. The trader paid 187.90, so the profit is 212.10 points, or ₹13,786.50 per lot.

If instead the Nifty settles at or below 23,000, the right to buy at 23,000 is worthless. The trader loses the whole premium of ₹12,213.50. Nothing more can be lost, however far the index falls.

The **breakeven** is the strike plus the premium: 23,000 + 187.90 = **23,187.90**. The Nifty has to rise about 1.2% from 22,906.55 by expiry just for the buyer to get their money back.

## 2. Calls and puts

The same morning, a trader worried about a fall could buy a **Nifty 22,500 put expiring 27 October** for **90.35**. A put is the right to *sell* the underlying at the strike. It gains when the price falls.

The put costs 90.35 × 65 = ₹5,872.75 per lot. If the Nifty settles at 22,000 on expiry, the right to sell at 22,500 is worth 500 points. If it settles above 22,500, the put expires worthless.

| | Call | Put |
|---|---|---|
| The buyer's right | Buy at the strike | Sell at the strike |
| Gains when the underlying | Rises above the strike | Falls below the strike |
| Value at expiry | Underlying − strike, or zero | Strike − underlying, or zero |
| Breakeven for the buyer | Strike + premium | Strike − premium |
| A common use | A bullish bet with a known maximum loss | Insurance for a portfolio, or a bearish bet |

A put works like an insurance policy. The premium is what the cover costs. The strike is the level below which the policy pays out. The guide on hedging, in the Futures & options section, takes this further.

## 3. The buyer and the seller

Every option has a seller on the other side, called the **writer**. The writer receives the premium. In return the writer must deliver what the buyer is owed at expiry.

So one contract creates four basic positions. The diagrams below show profit and loss per lot at expiry, using the real premiums from the snapshot. The solid line is the result at expiry; the shaded areas are profit (above zero) and loss (below zero).

```payoff
title: Buy one Nifty 23,000 call (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22200 23900
leg: buy call 23000 @ 187.9
caption: The buyer's loss is capped at the premium paid (₹12,213.50 per lot). Above the breakeven of 23,187.90 the profit grows with the index.
```

```payoff
title: Sell one Nifty 23,000 call (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22200 23900
leg: sell call 23000 @ 187.9
caption: The mirror image. The seller keeps at most the premium, and the loss keeps growing the further the index rises.
```

```payoff
title: Buy one Nifty 22,500 put (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 21700 23300
leg: buy put 22500 @ 90.35
caption: A put gains as the index falls below 22,500. The breakeven is 22,500 − 90.35 = 22,409.65.
```

```payoff
title: Sell one Nifty 22,500 put (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 21700 23300
leg: sell put 22500 @ 90.35
caption: The put seller earns ₹5,872.75 per lot if the index stays above 22,500, and loses heavily in a sharp fall.
```

The two sides are exact mirrors. What the buyer gains, the seller loses, before costs. Options are a **zero-sum** game between the two parties, and costs make it slightly negative-sum for both.

The shapes tell you the character of each side:

- **Buyers** lose a little most of the time and occasionally win big. Their loss is limited to the premium.
- **Sellers** win a little most of the time and occasionally lose big. A call seller's loss has no fixed limit, and a put seller can lose almost the whole strike value.

Neither shape is better by itself. What matters is whether the premium is a fair price for the risk. The guide on pricing and the Greeks, [Option pricing and the Greeks](learn-fno-pricing-greeks.md), shows what goes into that price.

## 4. In, at and out of the money

**Moneyness** describes where the strike sits relative to the current price. It decides how much of the premium is real value today.

| Strike | Call is… | Put is… |
|---|---|---|
| Below the current price (e.g. 22,500) | In the money (ITM) | Out of the money (OTM) |
| Near the current price (e.g. 22,900) | At the money (ATM) | At the money (ATM) |
| Above the current price (e.g. 23,000) | Out of the money (OTM) | In the money (ITM) |

An **in-the-money** option would be worth something if it expired right now. An **out-of-the-money** option would be worth nothing. **At the money** means the strike is the one closest to the current price.

Traders also speak of "deep" in or out of the money. A Nifty 24,000 call on this morning was deep out of the money: it needed a rise of almost 5% in 12 days to pay anything. It cost just 9.25.

## 5. Intrinsic value and time value

Look at three calls and two puts on the same expiry, 27 October, with the Nifty at 22,906.55.

| Option | Last price | Intrinsic value | Time value |
|---|---|---|---|
| 22,500 call (ITM) | 513.55 | 406.55 | 107.00 |
| 22,900 call (ATM) | 240.00 | 6.55 | 233.45 |
| 23,000 call (OTM) | 187.90 | 0 | 187.90 |
| 23,000 put (ITM) | 263.00 | 93.45 | 169.55 |
| 22,500 put (OTM) | 90.35 | 0 | 90.35 |

The **intrinsic value** is what the option would pay if it expired now. For a call it is the current price minus the strike, if that is positive. For a put it is the strike minus the current price, if positive. Otherwise it is zero.

The **time value** is the rest of the premium. It is what buyers pay for the chance that the option becomes worth more before expiry. Two things stand out in the table:

- Time value is **largest at the money** (233.45 for the 22,900 call). That strike is where the outcome is most uncertain.
- An out-of-the-money option is **all time value**. If the index does not move past the strike by expiry, every rupee of it disappears.

Time value shrinks as expiry approaches and is zero on the last day. The same 23,000 call on the earlier expiry, 19 October, cost about **96** that morning. That is half the price of the 27 October contract. The only difference was eight fewer days. The guide on [pricing and the Greeks](learn-fno-pricing-greeks.md) shows how fast this decay runs.

## 6. How an option ends

An option can end in three ways:

1. **Closed before expiry.** You sell the call you bought (or buy back the call you sold) at the market price. Most retail positions end this way.
2. **Expires worthless.** It finishes out of the money. The buyer loses the premium; the seller keeps it.
3. **Exercised.** It finishes in the money, and the buyer receives what the contract promises.

**Exercise** means the buyer uses the right. **Assignment** is the other side of it: the seller is told they must deliver. The exchange assigns exercised options to sellers holding the same contract.

### European and American options

A **European** option can be exercised only at expiry. An **American** option can be exercised on any day up to expiry. All options on NSE, index and stock, are European. In practice this matters less than it sounds, because you can still sell your option in the market at any time before expiry.

### Cash settlement: index options

Nifty, Bank Nifty and the other index options are **cash-settled**. Nobody delivers an index. At expiry the exchange takes the final settlement price, which is based on the index's closing level that day. In-the-money options are exercised automatically, and the difference is paid in cash.

Example: you hold one Nifty 23,000 call and the index settles at 23,400. The option is worth 400 points. Times the lot of 65, you receive ₹26,000, and the seller pays it.

### Physical settlement: stock options

Stock options in India are **physically settled**. If a stock option finishes in the money, it turns into a real purchase or sale of shares. This has been the rule for all stock derivatives since 2019.

Take Reliance on the same morning. The stock traded at about **₹1,200.90**. One Reliance lot is 500 shares. The 1,200 call expiring 27 October cost **23.25** per share. So one lot cost ₹11,625.

```payoff
title: Buy one Reliance 1,200 call (27 Oct 2026 expiry)
underlying: 1200.9
lot: 500
range: 1120 1290
leg: buy call 1200 @ 23.25
before: 6d 25%
caption: Per lot of 500 shares. The second curve is the model value six days before expiry; at expiry only the solid line counts.
```

Suppose Reliance closes at ₹1,250 on expiry day and you still hold the call. You do not get the ₹25,000 gain in cash. Instead you must **buy 500 shares at ₹1,200**, paying ₹6,00,000, and you receive the shares. If you have not got the money, your broker will act for you.

The seller of that call must **deliver 500 shares** at ₹1,200. A put works the other way round. The put buyer must deliver shares; the put seller must take them and pay for them.

This is why many brokers close out in-the-money stock option positions in the last days before expiry, unless the account holds enough money or shares. The exchange also raises the margin on such positions in expiry week. Check your broker's rules well before expiry.

## 7. What one contract really costs

Options trade in lots, and the exchange sets the lot size so that one contract is a meaningful amount of money. Here are the lot sizes for October 2026 contracts and the contract value at the snapshot prices:

| Contract | Lot size | Underlying at 10.15 am | Contract value (lot × price) |
|---|---|---|---|
| Nifty 50 | 65 | 22,906.55 | about ₹14.9 lakh |
| Nifty Bank | 30 | 55,719.75 | about ₹16.7 lakh |
| Nifty Financial Services | 60 | — | — |
| Nifty Midcap Select | 120 | — | — |
| Nifty Next 50 | 25 | — | — |
| Reliance Industries | 500 | 1,200.90 | about ₹6.0 lakh |

Lot sizes are revised from time to time as prices move. In 2024 SEBI, India's market regulator, raised the minimum value of an index derivative contract to about ₹15 lakh.

The **contract value** is your real exposure. A buyer of one Nifty 23,000 call pays only ₹12,213.50. But near the strike, the position's rupee value moves the way a few lakh rupees of the index would. Section 3 of [the pricing guide](learn-fno-pricing-greeks.md) measures this with delta.

Buyers and sellers put up money differently:

- **Buyers pay the full premium up front.** Under SEBI's 2024 measures it must be collected in full before the trade; there is no credit on it.
- **Sellers post margin.** The exchange works out a margin from the worst likely loss on the position over a day. For a short Nifty option it is a sizeable slice of the contract value, many times the premium received. Margin can be raised at any time, especially when markets are volatile.

The guide on futures basics, in the Futures & options section, explains how margin is calculated and collected.

## 8. Reading a quote

Each line of an option chain shows several numbers for each strike. Here is the 23,000 strike for 27 October from the snapshot:

| | Call | Put |
|---|---|---|
| Last traded price | 187.90 | 263.00 |
| Best bid (what buyers offer) | 187.90 | 262.30 |
| Best ask (what sellers want) | 188.35 | 263.15 |
| Open interest (contracts open) | 1,19,085 | 59,345 |
| Contracts traded so far today | 83,664 | 32,969 |

The gap between the bid and the ask is the cost of trading in and out at once. At this busy strike it was under half a point, tiny next to the premium. Far from the money, or in less active stocks, it can be several percent of the option's price.

**Open interest** is the number of contracts that are still open: bought by someone and sold by someone else, and not yet closed. High open interest usually means an active strike that is easy to trade.

Chains also show an implied volatility figure for each strike. It is the volatility that makes a pricing model match the option's price. The [volatility guide](learn-fno-volatility.md) explains it. The guide on reading an option chain, in the Futures & options section, covers the rest of the chain.

## 9. In the US

US options follow the same logic, with some differences worth knowing:

| | India (NSE) | United States |
|---|---|---|
| Stock options | European, physically settled | American (exercise any day), physically settled |
| Index options (e.g. S&P 500) | European, cash-settled | European, cash-settled |
| Contract size | Lot set by the exchange (e.g. 65 for Nifty) | Usually 100 shares per contract |
| Price steps | Fixed tick sizes | Many options quoted in cents |
| Very short expiries | One weekly index per exchange | Options expiring every trading day on the S&P 500 (often called 0DTE, "zero days to expiry") |
| Transaction tax | STT on option sales and on exercise | None of that kind; small regulatory fees |

American exercise brings one practical risk for sellers. A short call can be assigned early, typically just before the stock goes ex-dividend. The seller then wakes up short the shares.

## 10. What can go wrong

- **Buying far-out-of-the-money options because they are cheap.** The 24,000 call at 9.25 looks like a lottery ticket, and it is priced like one. The underlying must move far, fast, before time value runs out.
- **Selling options because they "usually expire worthless".** Most out-of-the-money options do. The losses on the ones that don't can wipe out months of premium, as the seller's payoff diagram shows.
- **Forgetting physical settlement.** An in-the-money stock option held into expiry becomes a purchase or sale of shares worth lakhs of rupees.
- **Confusing the premium with the exposure.** ₹12,213.50 bought a position whose value moves with a ₹14.9 lakh contract near the strike. See [position sizing](learn-risk-sizing.md).
- **Ignoring the bid–ask spread.** On illiquid strikes, crossing the spread can cost more than the move you hoped to capture.
- **Holding a short option into a scheduled event.** Results, policy decisions and elections can move the underlying far beyond what the premium paid for.

SEBI's studies of individual F&O traders found that about 9 in 10 lost money. Its September 2024 study covered the years FY22 to FY24. That is the base rate. The rest of this section of guides is about understanding why, so that you do not join the majority by accident.

## 11. Checklist

Before your first option trade, you should be able to answer each of these:

- Is it a call or a put, and am I the buyer or the seller?
- What is the strike, the expiry and the lot size? What is the contract value?
- Is it in, at or out of the money? How much of the premium is time value?
- What is my breakeven at expiry, and how far is it from today's price in %?
- What is my maximum loss in rupees? If I am a seller, what does a 5% move against me cost?
- Is it cash-settled (index) or physically settled (stock)? What will I do before expiry?
- How wide is the bid–ask spread, and how much open interest is there?
- Is there a scheduled event (results, a policy meeting, a budget) before expiry?

## Further reading

- John C. Hull, *Options, Futures, and Other Derivatives* — the standard textbook; the early chapters cover mechanics and payoffs.
- Lawrence G. McMillan, *Options as a Strategic Investment* — a practitioner's reference on every basic position.
- Sheldon Natenberg, *Option Volatility and Pricing* — the classic trader's introduction; read after this guide and [the pricing guide](learn-fno-pricing-greeks.md).
- SEBI, *Study on analysis of profit and loss of individual traders dealing in equity F&O segment* (January 2023, and the update of September 2024).
- NSE's contract specifications for index and stock derivatives, and its circulars on lot sizes and physical settlement.
