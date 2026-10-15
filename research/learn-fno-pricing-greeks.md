# Option pricing and the Greeks — what moves an option's price

**In short**

- An option's price depends on five things: the underlying's price, the strike, the time left, the expected volatility and (a little) interest rates.
- The Black-Scholes model turns those into a price. Traders run it backwards: the volatility that makes the model match the market price is the option's implied volatility.
- The Greeks measure how the price reacts to each input: delta to the underlying, gamma to changes in delta, theta to time passing, vega to volatility.
- Time decay is slow at first and fast near expiry. A buyer pays it every day; a seller collects it, in exchange for the risk of a large move.
- All figures here are worked from real NSE option prices at about 10.15 am IST on 15 October 2026.

This guide assumes you know what a call, a put, a strike and a premium are. If not, read [Options basics](learn-fno-options-basics.md) first.

All option prices below come from NSE's option chains at about 10.15 am on 15 October 2026, while the market was open. They are one snapshot, not closing prices. The Greeks were computed from those prices with the standard model, as described in section 9.

---

## 1. Same strike, different price

On that morning the Nifty 50 stood at **22,906.55**. Here are four options with the same strike, 23,000, side by side:

| Option | Days to expiry | Price (mid of bid and ask) |
|---|---|---|
| 23,000 call, 19 Oct expiry | 4.2 | 96.2 |
| 23,000 call, 27 Oct expiry | 12.2 | 188.1 |
| 23,000 put, 19 Oct expiry | 4.2 | 177.8 |
| 23,000 put, 27 Oct expiry | 12.2 | 262.7 |

The strike and the underlying are the same in every row. Yet the 27 October call costs almost twice as much as the 19 October call. The only difference is eight more days for the index to move.

Compare Reliance at about ₹1,200.90 that morning. Its 1,200 call for 27 October cost 23.2. That is **1.9%** of the share price. The Nifty's nearest call, the 22,900 strike, cost 239.9, which is **1.0%** of the index. Reliance options are dearer, relative to price, because the market expects Reliance to move more than the index.

Those two comparisons contain the whole idea of option pricing. An option is worth more when there is more time and more expected movement, because both raise the chance of a big payoff.

## 2. What goes into the price

| Input | If it rises, a call… | …and a put | Why |
|---|---|---|---|
| Underlying price | Gains | Loses | A call pays above the strike, a put below it |
| Strike | Loses | Gains | A higher strike is harder for a call to reach, easier for a put |
| Time to expiry | Gains | Gains (usually) | More time, more room to move |
| Expected volatility | Gains | Gains | Bigger swings make big payoffs more likely; losses are capped at the premium |
| Interest rate | Gains slightly | Loses slightly | Holding the index through a futures-like position costs interest |
| Dividends expected before expiry | Loses | Gains | The share price drops by the dividend |

The volatility row is the one beginners miss. An option's buyer has a capped loss and an open-ended gain. So more uncertainty helps the buyer in either direction, and both calls and puts get dearer when the market expects bigger swings.

## 3. The Black-Scholes idea, without the maths

In 1973 Fischer Black and Myron Scholes, with Robert Merton, published a formula for the fair price of a European option. Its logic can be followed without the equations:

1. Start from where the underlying is expected to be at expiry. For an index that is roughly today's price plus interest for the time left, minus expected dividends. This is the **forward price**.
2. Spread the possible prices at expiry around that centre in a bell shape. The width of the bell is set by the volatility and grows with the square root of the time left.
3. For every possible price, work out what the option would pay.
4. Average those payoffs, weighted by how likely each price is, and discount back to today.

For the 27 October 23,000 call the inputs were:

| Input | Value |
|---|---|
| Nifty | 22,906.55 |
| Forward price for 27 Oct, from the options themselves | about 22,926 |
| Strike | 23,000 |
| Time to expiry | 12.2 days, or 0.033 years |
| Interest rate | 6.5% a year |
| Volatility | 13.35% a year |
| Model price | 188.1 |

The model price equals the market's mid price of 188.1 exactly. That is not luck: the volatility of 13.35% was chosen to make it so.

Every input in the model is known except one, the future volatility. Traders therefore turn the model around. They take the market price as given and solve for the volatility that produces it. That number is the option's **implied volatility**: the market's price for movement, in the same units as historical volatility.

The [volatility guide](learn-fno-volatility.md) is all about it.

Two facts follow from the bell shape:

- **The at-the-money straddle measures the expected move.** Buying both the 22,900 call and the 22,900 put for 27 October cost 239.9 + 213.9 = 453.8 points. That is about **±2.0%** of the Nifty. A straddle is worth about 0.8 times the market's one-standard-deviation move to expiry.
- **Option prices grow with the square root of time.** Four times the time left buys about twice the price, not four times.

## 4. Delta — sensitivity to the underlying

The **delta** of an option is how much its price changes when the underlying moves one point. Here are 27 October Nifty calls and puts that morning:

| Strike | Call price | Call delta | Put price | Put delta |
|---|---|---|---|---|
| 22,500 | 513.7 | 0.76 | 90.4 | −0.24 |
| 22,700 | 364.9 | 0.65 | 140.2 | −0.35 |
| 22,900 | 239.9 | 0.52 | 213.9 | −0.48 |
| 23,000 | 188.1 | 0.45 | 262.7 | −0.55 |
| 23,100 | 144.6 | 0.38 | 317.6 | −0.62 |
| 23,300 | 80.1 | 0.25 | 451.5 | −0.75 |
| 23,500 | 41.2 | 0.15 | 614.5 | −0.85 |

The 23,000 call has a delta of **0.45**. If the Nifty rises 100 points, the call should gain about 45 points. Repricing it with the model gives **+48.6**. The extra 3.5 points come from gamma, in the next section.

Delta reads in three useful ways:

- **As a share of the move.** Calls run from 0 (far out of the money) to 1 (deep in the money). Puts run from 0 to −1. At the money, delta is close to ±0.5.
- **As an equivalent position.** One lot of the 23,000 call has a delta of 0.45 × 65 ≈ 29. For small moves it behaves like owning 29 units of the Nifty, about ₹6.7 lakh of index.
- **As a rough probability.** A call's delta is close to the chance, under the model, that it finishes in the money. The 23,000 call's delta of 0.45 sits near a 44% model chance.

A call delta and the matching put delta at the same strike add up to about 1 in size: 0.45 and −0.55. Holding the call and selling the put is close to holding one unit of the index.

## 5. Gamma — how fast delta changes

Delta does not stay put. As the Nifty rises, the 23,000 call moves towards the money and its delta climbs. **Gamma** is the change in delta for a one-point move in the underlying.

| Option | Days left | Delta | Gamma (per point) | Delta after a 100-point rise |
|---|---|---|---|---|
| 23,000 call, 27 Oct | 12.2 | 0.45 | 0.0007 | about 0.52 |
| 23,000 call, 19 Oct | 4.2 | 0.41 | 0.0012 | about 0.52 |
| 23,300 call, 19 Oct | 4.2 | 0.12 | 0.0006 | about 0.19 |

Gamma is highest **at the money** and **close to expiry**. The 19 October option had 4 days left and nearly twice the gamma of the 27 October one.

Gamma is what makes option buyers' gains run faster than their losses. A buyer is **long gamma**: delta rises as the trade works and falls as it fails. That is why the 23,000 call gained 48.6 points on a 100-point rise. An equal fall cost it only 41.6.

A seller is **short gamma**, and the effect runs the other way. As the market moves against a short option, its delta grows, and each further point hurts more than the last. Near expiry, gamma at the money becomes very large. A short at-the-money option on expiry day can swing from almost worthless to a large loss in an hour. The guide on expiry, in the Futures & options section, covers this.

## 6. Theta — the cost of time

**Theta** is how much an option loses in a day if nothing else changes. On that morning the 27 October 23,000 call had a theta of about **−9.2** points a day. Per lot that is about ₹600 a day.

The decay is not steady. Holding the Nifty and the implied volatility fixed, here is the model value of the 23,000 call as expiry approaches:

| Days to expiry | Value of the 23,000 call | Lost since the row above |
|---|---|---|
| 30 | 313.0 | — |
| 20 | 249.7 | 63.3 over 10 days |
| 12.2 (the snapshot) | 188.1 | 61.6 over 8 days |
| 7 | 134.6 | 53.5 over 5 days |
| 3 | 77.6 | 57.0 over 4 days |
| 1 | 33.6 | 44.0 over 2 days |
| At expiry, if the Nifty is still at 22,926 | 0 | 33.6 |

The last week takes more value than the two weeks before it. That is the square-root rule again, run backwards. An at-the-money option with 12 days left loses about 4% of its value a day, and one with 2 days left loses a quarter or more.

The two diagrams show the same position at different dates. The second curve is the model value before expiry; the solid line is the value at expiry.

```payoff
title: Long Nifty 23,000 call, valued 12 days before expiry
underlying: 22906.55
lot: 65
range: 22300 23700
leg: buy call 23000 @ 188.1
before: 12d 13.35%
caption: With 12 days left the curve sits well above the expiry line: that gap is time value, and it is what the buyer stands to lose if the index does not move.
```

```payoff
title: The same call, valued 2 days before expiry
underlying: 22906.55
lot: 65
range: 22300 23700
leg: buy call 23000 @ 188.1
before: 2d 13.35%
caption: Two days out, the curve has nearly collapsed onto the expiry line. If the Nifty is still near 22,900, most of the premium has gone.
```

Theta and gamma are two sides of one trade. A buyer pays theta every day to own gamma, the chance of a big move. A seller collects theta every day and is short gamma. Neither side gets something for nothing; who wins depends on whether the underlying moves more or less than the option price assumed.

Weekends and holidays count as calendar days in the model. In practice, option prices often fall ahead of a weekend, so the Monday open shows less of a drop than the calendar suggests.

## 7. Vega — sensitivity to volatility

**Vega** is how much an option's price changes when implied volatility moves by one percentage point. The 27 October 23,000 call had a vega of about **16.6**. If implied volatility rose from 13.35% to 14.35%, the call would gain about 16.6 points with no move in the Nifty at all.

| Option | Days left | Vega (points per 1 point of implied volatility) |
|---|---|---|
| 23,000 call, 19 Oct | 4.2 | 9.6 |
| 23,000 call, 27 Oct | 12.2 | 16.6 |
| 23,500 call, 27 Oct | 12.2 | 9.7 |
| Reliance 1,200 call, 27 Oct (per share) | 12.2 | 0.87 |

Vega is largest for at-the-money options with **more time left**. Short-dated options react mainly to the underlying and to time; longer-dated ones react more to changes in implied volatility.

Vega can swamp everything else.

Suppose implied volatility fell by 3 points. The 27 October 23,000 call would lose about 50 points. That is as much as five days of time decay, gone at once. This is the "volatility crush" that hits option buyers after results and other events. The [volatility guide](learn-fno-volatility.md) shows it on real data.

## 8. Putting the Greeks together

The Greeks let you estimate a position's next-day result before it happens. Take one lot of the 27 October 23,000 call, bought at 188.1. Suppose that by the next day the Nifty is up 100 points and implied volatility is down 1 point.

| Source | Estimate (points) |
|---|---|
| Delta: 0.45 × 100 | +45.1 |
| Gamma: ½ × 0.0007 × 100 × 100 | +3.5 |
| Theta: one day | −9.2 |
| Vega: −1 point of volatility | −16.6 |
| Total by the Greeks | +22.8 |
| Full model repricing | +23.3 |

The index rose 100 points, yet the call gained less than a quarter of that. Time and a small drop in implied volatility took more than half of the gain that delta delivered. That is why a correct view on direction is not enough to make money with options.

Here is a summary of who wants what:

| Greek | Option buyer | Option seller |
|---|---|---|
| Delta | Wants the move in the chosen direction | Wants the move not to come |
| Gamma | Long: gains speed up | Short: losses speed up |
| Theta | Pays it daily | Collects it daily |
| Vega | Gains if implied volatility rises | Gains if implied volatility falls |

## 9. How the numbers here were made

The prices in this guide are the mid-point of the best bid and best ask in the snapshot. The model is the standard Black-Scholes model in the form that uses the forward price. The forward for each expiry was taken from the options themselves. At the three strikes nearest the index, the call price minus the put price fixes the forward, by a relationship called **put-call parity**.

Time is counted in calendar days to 3.30 pm on expiry day. The interest rate is 6.5% a year. Theta is the model's change over one calendar day. Vega is per one percentage point of volatility. Small changes to these choices move the Greeks a little but do not change any conclusion.

## 10. What can go wrong

- **The model is a map, not the market.** Black-Scholes assumes volatility is constant and prices move smoothly. Real prices jump on news, and implied volatility differs by strike (the skew, in the [volatility guide](learn-fno-volatility.md)).
- **Greeks change as the market moves.** A delta of 0.45 today is 0.52 after a 100-point rise. Re-check positions, especially short ones, after every large move.
- **Near expiry, gamma dominates.** Estimates based on today's delta can be far off for a move of even 1% on the last day.
- **Stock options carry dividends and physical delivery.** A dividend before expiry lowers calls and raises puts. An in-the-money stock option held to expiry becomes a delivery of shares.
- **Mid prices are not trade prices.** You buy at the ask and sell at the bid. On thin strikes the spread can be larger than a day's theta.
- **A long option needs a large enough move fast enough.** Being right on direction but slow is a losing trade, as section 8 shows.

## 11. In the US

The ideas are identical. Two practical differences:

- US stock options are American and can be exercised early. Models for them adjust for that; for calls on stocks that pay no dividend it makes almost no difference.
- The S&P 500 has options expiring every trading day. Their gamma and theta on the last day are extreme, for the reasons in sections 5 and 6.

## 12. Checklist

- What are the delta and the rupee delta per lot (delta × lot size × price)? Is that the exposure I intended?
- How many days are left? What is theta per day in rupees, and what is it over my planned holding period?
- Is the position long or short gamma? What does a 2% move against me cost?
- What is the vega? What happens to the price if implied volatility falls 3 points, for example after an event?
- Does my expected move beat the at-the-money straddle's expected move, after costs?
- Am I using mid prices for planning and bid or ask prices for the real numbers?

## Further reading

- Fischer Black and Myron Scholes, "The Pricing of Options and Corporate Liabilities", *Journal of Political Economy* (1973).
- Robert C. Merton, "Theory of Rational Option Pricing", *Bell Journal of Economics and Management Science* (1973).
- John C. Hull, *Options, Futures, and Other Derivatives* — chapters on the Black-Scholes-Merton model and the Greek letters.
- Sheldon Natenberg, *Option Volatility and Pricing* — the trader's view of the Greeks, with many worked examples.
- Euan Sinclair, *Option Trading: Pricing and Volatility Strategies and Techniques* — practical, with a sceptical eye on what models miss.
