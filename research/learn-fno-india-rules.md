# Indian F&O rules, costs and tax — in one place

**In short**
- A Nifty contract is worth about ₹15 lakh. You put up only a margin, but you carry the profit and loss of the whole contract.
- A round trip in one lot of Nifty options costs roughly ₹70–75 in charges plus the bid–ask spread. A round trip in one lot of Nifty futures costs roughly ₹440.
- Index options settle in cash. Stock futures and options settle by delivery of the shares.
- F&O profits and losses are business income for tax. Keep records of every trade and ask a tax adviser.
- SEBI's studies found that about 9 in 10 individual F&O traders lost money. Costs are one of the reasons.

Rates and rules in this guide are approximate and dated October 2026. Exchange charges, STT and margin rules change, often in the Union Budget or by SEBI circular. Check the current figures with your broker and the exchange before you rely on them.

## 1. One round trip, every rupee

On the morning of 15 October 2026 a trader buys one lot of the Nifty 23,000 call expiring 27 October. The ask is 188.35 and the lot is 65 units, so the premium is ₹12,242.75. A few days later the trader sells at 230. The gross profit is 41.65 points, or ₹2,707.25.

| Charge | How it is charged (approximate) | This trade |
|---|---|---|
| Brokerage | Flat fee per order at a discount broker, say ₹20 | ₹40.00 |
| STT (securities transaction tax) | 0.15% of the premium, on the sale only | ₹22.43 |
| Exchange transaction charge | About 0.035% of premium, both sides | ₹9.53 |
| SEBI fee | ₹10 per crore of turnover | ₹0.03 |
| Stamp duty | 0.003% of premium, on the purchase only | ₹0.37 |
| GST | 18% of brokerage, exchange charge and SEBI fee | ₹8.92 |
| **Total charges** | | **₹81.27** |

*Option premium turnover: ₹12,242.75 bought, ₹14,950 sold. STT at the rate in force from 1 April 2026; check current rates.*

The charges come to about 1.25 points per unit, or 3% of the profit. The trader also crossed the spread on the way in: the bid was 187.90, so buying at the ask cost about ₹29. The exit costs a similar amount. So the full cost of the round trip is around ₹140, or about 2 points.

That looks small for one trade. It is not small for an active trader. Five such round trips a day, for a year of about 250 sessions, cost roughly ₹1.75 lakh. The account has to earn that before it makes a rupee.

Futures cost more per lot because STT and the exchange charge are on the full contract value, not a premium.

| One lot of Nifty futures, bought at 22,940, sold at 23,040 | Amount |
|---|---|
| Contract value bought | ₹14,91,100 |
| Contract value sold | ₹14,97,600 |
| Brokerage (two orders) | ₹40.00 |
| STT (0.05% on the sale) | ₹748.80 |
| Exchange charge (about 0.0017%, both sides) | ₹51.70 |
| SEBI fee | ₹2.99 |
| Stamp duty (0.002% on the purchase) | ₹29.82 |
| GST | ₹17.04 |
| **Total charges** | **₹890.36** |
| Gross profit (100 points × 65) | ₹6,500 |

*Futures last price 22,940 for the 27 October 2026 contract at about 10:15 on 15 October 2026. The sale price is illustrative. STT at the rate in force from 1 April 2026; check current rates.*

The futures round trip costs about 7 index points in charges. A trader who aims for 20 points a trade gives up about a third of it.

## 2. Lot sizes and contract value

Every F&O contract has a fixed lot size, set by the exchange. You trade whole lots only. Here are the lot sizes for October 2026 contracts from NSE's official list, with contract values at the snapshot's prices.

| Contract | Lot size (Oct 2026) | Price at about 10:15, 15 Oct 2026 | Contract value |
|---|---|---|---|
| Nifty 50 | 65 | 22,906.55 | ₹14.9 lakh |
| Bank Nifty | 30 | 55,719.75 | ₹16.7 lakh |
| Fin Nifty | 60 | — | — |
| Midcap Select | 120 | — | — |
| Nifty Next 50 | 25 | — | — |
| Reliance | 500 | 1,200.40 | ₹6.0 lakh |
| HDFC Bank | 650 | 719.70 | ₹4.7 lakh |
| ICICI Bank | 700 | 1,361.80 | ₹9.5 lakh |

*Lot sizes from NSE's market-lot file for the October 2026 contract month. Contract value = lot × price. Prices are the underlying values reported with the snapshot.*

Since November 2024 SEBI has required index derivatives to be worth at least about ₹15 lakh when the lot size is set. Lot sizes are reviewed from time to time, not every day. Between reviews, the contract value moves with the index.

```series
title: Nifty in 2026 — the same 65-unit lot, a different contract value
from: 2026-01-01
to: 2026-10-14
line: india:NIFTY50 | Nifty
mark: 2026-01-02 | about 26,330: one lot ≈ ₹17.1 lakh
mark: 2026-10-08 | about 22,230: one lot ≈ ₹14.4 lakh
caption: The Nifty fell about 15% from its January high to its October low. With the lot fixed at 65, one contract's value fell from about ₹17 lakh to under ₹15 lakh.
```

Stock contracts are smaller. Among the 20 most active stock futures in the snapshot, contract values ranged from about ₹4.5 lakh to about ₹12 lakh.

## 3. Margin

You do not pay the contract value to buy a future or to sell an option. You deposit a margin with your broker, who passes it to the clearing corporation.

The margin has two parts. **SPAN margin** comes from the exchange's risk model. It estimates how much the position could lose in one bad day across a range of price and volatility moves. **Exposure margin** is an extra buffer on top.

For a Nifty future the total is a fraction of the contract value, often around a tenth. It is higher for single stocks and rises when markets are volatile.

Every day, open futures are marked to market. Each evening the day's profit or loss is credited to or taken from your account in cash. If losses take your balance below the required margin, you must add money. If you do not, the broker can close your positions.

**Buying an option needs the full premium.** Since February 2025 brokers must collect the premium upfront. You cannot buy options on margin.

**Selling an option needs margin like a future.** A short at-the-money Nifty option can need about as much margin as a Nifty future. The premium you receive does not cover the risk.

**Hedged positions need less.** A short option with a long option further out (a spread) needs less margin, because its loss is capped. On expiry day the offset between different expiries no longer applies. [Expiry](learn-fno-expiry.md) explains the expiry-day rules.

Brokers must also collect the full margin during the day, not only at the close. A trade the account cannot margin is rejected.

## 4. The expiry calendar

NSE's expiry day is Tuesday. Nifty options expire weekly. Nifty futures, Bank Nifty, Fin Nifty, Midcap Select and stock futures and options expire on the last Tuesday of the month. When the Tuesday is a holiday, expiry moves to the trading day before.

| Contract | Expiries available (snapshot) |
|---|---|
| Nifty options | Weekly and monthly, plus quarterly and half-yearly up to 2031 |
| Nifty futures | Three monthly: October, November, December 2026 |
| Bank Nifty options | Monthly, plus quarterly into 2027 |
| Reliance (stock F&O) | Three monthly |

*From NSE's option-chain and futures lists on 15 October 2026.*

BSE's weekly index contract is on the Sensex, expiring on Thursdays. [Expiry](learn-fno-expiry.md) covers what happens in the last days.

## 5. Settlement

**Index futures and options settle in cash.** At expiry, the difference between your price and the settlement price is paid in cash. The settlement price for index options is the index's official closing value on expiry day. Index options are European: they can be exercised only at expiry.

**Stock futures and options settle by delivery.** An open stock future at expiry becomes a purchase or sale of the shares. An in-the-money stock option is exercised into one. A long call holder pays for the shares at the strike. A short call writer must deliver them. Out-of-the-money stock options expire worthless.

Delivery needs cash or shares on the day. In the last few days before expiry, the exchange charges extra margin on in-the-money stock positions. Many brokers close such positions themselves before expiry if the account is not ready for delivery.

## 6. Position limits and the F&O ban

Limits cap how large a position one trader, one broker or the whole market may hold. Most retail traders never come near the client limits. The rule they do meet is the **F&O ban** on single stocks.

Each stock has a market-wide position limit: the total open interest allowed across everyone. When open interest passes 95% of that limit, the stock enters the ban period. During the ban, traders can only reduce their positions in that stock's F&O. New positions are not allowed. The ban lifts when open interest falls back below a lower threshold.

A ban can trap a plan. A trader who planned to add to a position, or to roll it, cannot. The exchange publishes the ban list every day.

Since April 2025 the exchanges also check index position limits during the day, not only at the close.

## 7. All the charges, at a glance

| Charge | Options | Futures |
|---|---|---|
| STT | 0.15% of premium on sale | 0.05% of value on sale |
| STT if an index option is exercised | 0.15% of intrinsic value, paid by the buyer | — |
| STT if a stock contract is settled by delivery | 0.1% of the full contract value, buyer and seller | Same |
| Exchange charge (NSE) | About 0.035% of premium | About 0.0017% of value |
| SEBI fee | ₹10 per crore | ₹10 per crore |
| Stamp duty | 0.003% of premium on purchase | 0.002% of value on purchase |
| GST | 18% of brokerage, exchange charge and SEBI fee | Same |
| Brokerage | Set by broker; often a flat ₹20 per order | Same |

*Approximate rates. STT on futures and options was raised in October 2024 and again from 1 April 2026 (the 2026–27 Budget); it is set by the Union Budget, so check the current rate.*

The last two STT rows matter at expiry. An in-the-money index option held to expiry is exercised automatically. Since April 2026 its STT, 0.15% of the intrinsic value, is about the same as selling it, so the old rule "always sell before the close" matters less for index options.

Stock contracts are different. An in-the-money stock option or a stock future held to expiry is settled by delivery of the shares. Both sides then pay delivery STT of 0.1% on the full contract value, which is far more than the STT on the option's premium.

The bid–ask spread is not on any contract note, but it is often the largest cost. For an at-the-money Nifty option it was under 1 rupee in the snapshot. For a cheap far-away strike it can be 5% of the price.

## 8. Tax

In India, profits and losses from F&O trading are treated as non-speculative business income. They are not capital gains. That has several effects:

- Profits are added to your income and taxed at your slab rate.
- Expenses that are directly for the trading business may be deductible.
- Losses can be set off against other business income, and under conditions carried forward to later years.
- You file the return form for business income and keep books of account.
- A tax audit can be needed, depending on turnover and profit. For options, "turnover" is defined in a particular way.

The details depend on your whole income and change with the law. Keep a record of every trade and every contract note. Ask a tax adviser before you file.

## 9. SEBI's studies — the honest odds

SEBI has studied the results of individual F&O traders twice.

| Study | Period | Share of individual traders who lost money |
|---|---|---|
| January 2023 | FY 2021–22 | About 89% |
| September 2024 | FY 2021–22 to FY 2023–24 | About 93% |

*SEBI, "Analysis of Profit and Loss of Individual Traders dealing in Equity F&O Segment". Losses include transaction costs.*

Over the three years in the second study, the average loss-maker lost about ₹2 lakh, including costs. Very few traders made meaningful profits after costs.

Costs explain part of this, as section 1 shows. Leverage and short-dated options explain more. [Risk and position sizing in F&O](learn-fno-risk-sizing.md) covers how accounts blow up.

## 10. In the US

US listed options differ in a few ways that matter if you trade both markets.

- **Stock options are American.** They can be exercised on any day, so a short option can be assigned early, usually around a dividend.
- **Index options on the S&P 500 (SPX) are European and cash-settled**, like Nifty options. Options on ETFs such as SPY are American and settle in shares.
- **The usual contract is 100 shares.** Contract values are much smaller than an Indian lot.
- **Prices move in one-cent steps** for many options.
- **There is no STT.** Costs are commissions, small exchange and regulatory fees, and the spread.
- **Same-day expiries.** SPX has options expiring every trading day ("0DTE", zero days to expiry).

## 11. What can go wrong

- **Using old rates.** STT, exchange charges and margins change. A cost model from last year can be wrong this year.
- **Forgetting the spread.** It is often larger than all the statutory charges together.
- **Trading futures for small targets.** Charges of about 14 Nifty points per round trip eat a small target.
- **Holding a stock position into expiry without the cash or the shares.** It turns into delivery, or the broker closes it for you.
- **Letting an in-the-money stock option expire.** It settles by delivery, and both sides pay STT of 0.1% on the full contract value.
- **Running into a ban.** You cannot add to or roll a position in a stock under the F&O ban.
- **Mixing F&O with investment income at tax time.** It is business income with its own rules.

## 12. Checklist

- What is the lot size and contract value of what you are about to trade?
- What margin will it need now, and on expiry day?
- What will one round trip cost in charges and in spread, in points?
- Is it cash-settled or delivery-settled? If delivery, are you ready for it?
- Is the stock in, or close to, the F&O ban?
- Are the rates in your cost model current?
- Are you keeping every contract note for tax?

## Further reading

- SEBI, "Analysis of Profit and Loss of Individual Traders dealing in Equity F&O Segment" (January 2023; September 2024).
- SEBI, circular "Measures to strengthen Equity Index Derivatives framework for increased investor protection and market stability" (1 October 2024).
- NSE, F&O contract specifications, the market-lot file and the daily ban list (on the exchange's website).
- NSE Clearing, the explanation of SPAN and exposure margins (on the clearing corporation's website).
- John C. Hull, *Options, Futures, and Other Derivatives* — settlement, margin and marking to market.
