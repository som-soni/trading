# Hedging with options and futures — protective puts, collars and index hedges

**In short**

- A hedge is a position that gains when your holdings lose. You pay for it in premium, in given-up upside, or both.
- A protective put sets a floor under a stock or a portfolio for a fixed cost. A collar pays for that floor by selling the upside above a chosen price.
- A portfolio of Indian stocks can be hedged with Nifty puts or by selling Nifty futures. The number of lots comes from the portfolio's value and its beta.
- Insurance held all the time is expensive. Rolling monthly Nifty puts 5% below the market cost several percent of the portfolio a year. Hedge for a reason and a period, not by habit.
- Insurance is cheapest when nobody wants it. India VIX was 9.45 on 2 January 2026, at the Nifty's high, just before a 15% fall.

This guide is about protecting what you own: a single stock, or a portfolio, against a fall. It assumes you know what calls, puts and futures are (see the options basics and futures basics guides in the Futures & options section). For using options to bet on direction, see [directional options](learn-fno-directional.md); for selling them, see [selling options for income](learn-fno-income.md).

Option and futures prices in this guide come from one snapshot of NSE data, taken at about 10:15 am on 15 October 2026. They moved during the day. The snapshot is one moment, not a history.

---

## 1. The idea

Start with a real holding. At the snapshot an investor owns 500 Reliance shares at ₹1,200.8: one lot, worth about ₹6 lakh. The stock is 26% below its January high. The investor wants to keep the shares but limit the damage of another leg down.

The November **1,140 put** costs ₹14.05 a share. For the whole lot that is ₹7,025. It gives the right to sell at ₹1,140 until 23 November 2026.

```payoff
title: Protective put: 500 Reliance shares plus the 1,140 put (23 Nov 2026 expiry)
underlying: 1200.8
lot: 500
range: 1000 1350
leg: buy stock @ 1200.8
leg: buy put 1140 @ 14.05
caption: Real premium from the 15 Oct 2026 snapshot. The put costs ₹7,025, 1.2% of the holding, for 39 days. However far Reliance falls, the loss stops at ₹37,425 (6.2%). Above the market, the gain is reduced only by the premium.
```

That is the whole idea of a hedge:

- **A floor.** Below ₹1,140 the put gains a rupee for every rupee the shares lose.
- **A cost.** The ₹7,025 is gone if Reliance does not fall. It is the price of insurance for 39 days.
- **The same upside, minus the premium.** You stay in the stock if it recovers.

**Who is on the other side?** Option sellers, who collect the premium (see the [income guide](learn-fno-income.md)). They charge more than the average payout, as any insurer does. That is why hedging all the time loses money on average. The value of a hedge is not its average return. It is what it does in the few months when it matters: it keeps a bad fall from becoming a disaster, and it lets you hold a position through an event you cannot predict.

### The collar

The put's cost can be paid by selling a call above the market. Sell the November **1,260 call** at ₹20.00, and the position becomes a **collar**. It has a floor at ₹1,140 and a ceiling at ₹1,260.

```payoff
title: Collar: 500 Reliance shares, buy the 1,140 put, sell the 1,260 call (23 Nov 2026 expiry)
underlying: 1200.8
lot: 500
range: 1000 1350
leg: buy stock @ 1200.8
leg: buy put 1140 @ 14.05
leg: sell call 1260 @ 20
caption: Real premiums from the snapshot. The call pays more than the put costs, so the collar is opened for a net credit of ₹2,975. The loss is capped at ₹27,425 below ₹1,140; the gain is capped at ₹32,575 above ₹1,260.
```

The collar costs nothing up front here. Its real cost is the upside above ₹1,260 that the investor gives away. If Reliance rallies back to its 50-day average (₹1,260 on 14 October) and beyond, the collar stops gaining.

### Hedging a whole portfolio

Most investors do not hedge stock by stock. They hedge the market part of the risk with the index. At the snapshot, one Nifty lot (65 units at 22,906.55) covered about ₹14.9 lakh of index exposure.

Take a ₹30 lakh portfolio of large Indian stocks with a beta of 1.1. Beta measures how much the portfolio tends to move for each 1% move in the Nifty. The exposure to hedge is 30 × 1.1 = ₹33 lakh. That is 2.2 Nifty lots. Two lots hedge about 90% of it.

```payoff
title: A Nifty-like portfolio (2 lots' worth) plus two 22,000 puts (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 20500 24000
leg: buy 2x stock @ 22906.55
leg: buy 2x put 22000 @ 32.05
caption: Real premium from the snapshot. The portfolio is shown as two lots of the index. Two puts 4% below the market cost ₹4,167 for 12 days, 0.14% of the portfolio. Below 22,000 the loss stops falling, at about ₹1.22 lakh.
```

The other way is to **sell Nifty futures**. Selling two lots of the October future at 22,940 cancels most of the portfolio's market risk in both directions. There is no premium. But the upside goes too, and the short futures need margin and daily cash settlement.

```payoff
title: The same portfolio hedged with two short Nifty futures (27 Oct 2026 expiry)
underlying: 22909.85
lot: 65
range: 20500 24000
leg: buy 2x stock @ 22909.85
leg: sell 2x future @ 22940
caption: Real prices from the snapshot: the index at 22,909.85, the October future at 22,940. The combined position barely moves with the index. The small gain is the futures premium of about 30 points, earned as the future converges to the index at expiry.
```

| Hedge for a ₹30 lakh portfolio, beta 1.1 | Cost now | Protects | Gives up |
|---|---|---|---|
| Nothing | — | — | — |
| 2 × Nifty 22,000 put (27 Oct) | ₹4,167 premium | Falls beyond 4% | Nothing above |
| 2 × Nifty 22,500 put (27 Oct) | ₹11,746 premium | Falls beyond 1.8% | Nothing above |
| 2 × short Nifty future (Oct, 22,940) | Margin, no premium | Almost all of the market move | Almost all of the market gain |

*Prices at about 10:15 am on 15 October 2026. The hedges cover the market part of the risk only.*

---

## 2. When it works and when it doesn't

**A hedge is worth its cost when:**

- **A known event is ahead** and you would rather not sell: results for a stock, an RBI policy decision, the Union Budget, an election result (see the [economic calendar](learn-macro-calendar.md)).
- **The market's trend has turned down** but you hold positions you do not want to sell, for example for tax reasons or because they are long-term holdings. A useful test: the index closes below its 200-day moving average and the 200-day is falling (see [market trend](learn-health-trend.md)).
- **Implied volatility is low.** The same protection costs far less. In early January 2026 India VIX was near its lowest level of the past decade.
- **You have large unrealised gains** and a fall would change your plans.

**A hedge is a poor use of money when:**

- **It is bought after the fall.** Implied volatility is then high, so puts are expensive. In 2020, after the March crash, rolling monthly puts would have cost about 15% of the portfolio for the year (section 8).
- **It is held permanently.** The premium adds up to several percent a year, and the market rises in most years.
- **It hedges something else.** A Nifty hedge protects the market part of a portfolio. It does nothing for a small-cap stock that falls on its own news.

```series
title: When protection was cheap and when it was dear — Nifty and India VIX, 2025–2026
from: 2025-07-01
to: 2026-10-14
line: india:NIFTY50 | Nifty 50
line: india:INDIAVIX | India VIX | right
mark: 2026-01-02 | VIX 9.45, Nifty high
mark: 2026-03-30 | VIX 27.9
caption: India VIX was 9.45 on 2 January 2026, the day of the Nifty's closing high (26,329). By 30 March the Nifty was 15% lower and India VIX was 27.9. A put bought in January cost a fraction of the same put bought in late March.
```

### India and the US

- **India.** Index options are European and cash-settled. Stock options are physically settled. A protective put on shares you own can be exercised at expiry to deliver them, which is clean. A collar's short call that ends in the money means the shares are delivered at the strike. Only the Nifty has weekly options on NSE; the others expire monthly. Index options extend further out than stock options, but liquidity is concentrated in the nearest expiries.
- **India — futures.** Short futures need margin of very roughly 10–15% of the contract value, and losses are settled in cash every day. If the market rises, the futures lose cash daily while the shares' gains stay on paper. Keep spare cash for that.
- **India — tax.** Gains and losses on the hedge are F&O business income; gains on the shares are capital gains. They are taxed differently and may not offset. Check with a tax adviser.
- **US.** Protective puts and collars on single stocks are common, with long-dated options available. Portfolios are hedged with S&P 500 index options, which are European and cash-settled, or with index futures. There is no STT.

---

## 3. The rules

### Universe and filters

- **What to hedge:** a single stock with liquid options (bid–ask spread at most **3%** of the premium), or a portfolio of large stocks with a measurable beta to the Nifty.
- **Instrument:** for a portfolio, Nifty options or futures; for a stock, its own options, or its futures if the options are thin.
- **Beta:** estimated from at least **one year** of weekly or daily returns against the Nifty. Re-estimate every quarter.

### Setup (when to hedge)

Hedge when at least one of these is true:

- **Event:** a scheduled event inside the next **30 days** that could move the holding by more than its usual monthly range.
- **Trend:** the Nifty closes below its 200-day average, and the 200-day is lower than **20** sessions ago.
- **Gains to protect:** the holding is up more than **25%** and the gain matters to your plans.
- **Cheap protection:** India VIX is below its **20th percentile** of the past year, and you hold a large equity exposure.

### Entry

- **Expiry:** the first expiry after the event, or **one to three months** out for a trend hedge. Longer puts cost less per day than rolling short ones.
- **Strike of the put:** **3–10%** below the market. Closer puts protect more and cost more.
- **Collar call:** at a price you would accept for selling, typically **5–10%** above the market, chosen so the call's premium pays most of the put.
- **Number of lots (portfolio):** lots = portfolio value × beta ÷ (index level × lot size), rounded down. For the example above: 30 lakh × 1.1 ÷ 14.89 lakh = 2.2, so two lots.
- **Order:** limit orders at or near the mid price; for a collar, a single order for both legs if your broker allows it.

### Initial stop (the hedge budget)

A hedge has no stop of its own. What it has is a budget:

- Total premium spent on hedges is at most **2–3%** of the portfolio a year.
- For a futures hedge, the cash reserve for daily settlement is at least **10%** of the hedged value.

### Exits

- **The reason ends:** remove the hedge after the event, or when the Nifty closes back above its 200-day average.
- **The hedge has paid:** after a fall of **10%** or more, with implied volatility high, sell the put and buy a cheaper one at a lower strike (rolling down). This turns the gain into cash while keeping some protection.
- **Expiry:** close stock options at least **two sessions** before expiry unless you intend to deliver the shares.
- **Collar call threatened:** if the stock rises through the call strike and you want to keep the shares, buy the call back before expiry.

### Position size

- Hedge ratio: **50–100%** of the portfolio's beta-weighted exposure. A partial hedge costs less and still cuts the worst losses.
- Never hedge more than 100%: that turns the hedge into a short bet on the market.
- Recalculate the number of lots after a large move in the index or a change in the portfolio.

### Managing the trade

- Roll puts before the last **one or two weeks** of their life; their protection fades as expiry nears and time value is small.
- Keep a record of each hedge's cost and payout. Over a year, the total tells you whether you are hedging too often.
- For futures hedges, roll to the next month a few days before expiry. The cost of rolling is the difference between the two futures prices (the basis), which mostly reflects interest rates.

---

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Put strike | 3–10% below the market | Size of the loss before protection starts | 5% below: about 0.15–0.5% a month in normal volatility |
| Put expiry | 1–3 months; first expiry after the event | Cost per day | Longer puts cost less per day; weekly puts decay fastest |
| Collar call strike | 5–10% above the market | Upside given up | Closer: more premium, less upside |
| Hedge ratio | 50–100% of beta-weighted exposure | How much market risk remains | — |
| Beta estimation window | 1–2 years | Number of lots | Beta changes; re-estimate quarterly |
| Event window | Up to 30 days ahead | When to hedge | — |
| Trend trigger | Close below 200-day average, 200-day falling over 20 sessions | When to hedge | A shorter average hedges sooner and more often |
| Cheap-protection trigger | India VIX below its 20th percentile | When to hedge | — |
| Hedge budget | 2–3% of portfolio a year | Total cost | — |
| Futures cash reserve | 10–20% of hedged value | Ability to meet daily settlement | — |
| Roll-down trigger | Index down 10% or more | Turning a paid hedge into cash | — |
| Days before expiry to roll or close | 5–10 sessions | Time-value loss, delivery | — |

---

## 5. Variations

- **Put spreads instead of puts.** Buy a put 5% below and sell one 15% below. It costs much less and protects the first 10% of a fall, which is the common case. It does not protect a crash.
- **Zero-cost collars.** Choose the call so its premium equals the put's. Common for concentrated stock holdings, for example promoters' or employees' shares in the US.
- **Tail hedges.** Small, regular purchases of far out-of-the-money puts (10–20% below), sized to pay off only in a crash. Nassim Taleb argued for this approach. It loses in most years by design.
- **Conditional hedging.** Hedge only when a market-trend or breadth signal says the risk is high (see [market breadth](learn-health-breadth.md) and [market trend](learn-health-trend.md)). It is cheaper than permanent insurance, but it is late in a sudden crash.
- **Cash instead of hedges.** Selling part of the portfolio removes risk with no premium and no margin. In India, for long-held shares, the tax on realised gains is the main reason to hedge instead.
- **Hedging with a negatively correlated asset.** Gold or government bonds have sometimes risen in equity sell-offs. The relation is not reliable, and it is diversification, not a hedge.

---

## 6. Worked examples

Examples 1 and 2 use real snapshot prices; section 1 showed their diagrams. Examples 3 and 4 are historical. Option prices were not stored for those, so the premiums are **estimates** from the Black-Scholes model (the standard formula for an option's fair value). The estimates use India VIX plus 3 points as the implied volatility, because out-of-the-money puts trade above the at-the-money level. In the snapshot, a 27 October put 4% below the market had an implied volatility about 3 points above the at-the-money put.

### Example 1 — protecting Reliance for five weeks (snapshot)

| Choice for 500 Reliance shares at ₹1,200.8 | Cost | Worst case at 23 Nov expiry | Best case |
|---|---|---|---|
| No hedge | — | Unlimited down to zero | Unlimited |
| Buy 1,140 put | ₹7,025 | −₹37,425 | Upside minus ₹7,025 |
| Collar: buy 1,140 put, sell 1,260 call | +₹2,975 (credit) | −₹27,425 | +₹32,575 |

*Last traded prices at about 10:15 am on 15 October 2026.*

The bid–ask spreads on November Reliance options were wide: 1.8% of the price on the put, 1.2% on the call. Crossing those spreads on both legs, in and out, costs about ₹250 against mid prices. The comparison is unchanged.

### Example 2 — a portfolio hedge for eight sessions (snapshot)

The ₹30 lakh, beta 1.1 portfolio from section 1. The trader worries about the next eight sessions and chooses between the 27 October puts.

| Two lots of the put (27 Oct) | Cost | Cost, % of portfolio | Protection starts below |
|---|---|---|---|
| 22,500 put | ₹11,746 | 0.39% | 22,500 (−1.8%) |
| 22,200 put | ₹6,117 | 0.20% | 22,200 (−3.1%) |
| 22,000 put | ₹4,167 | 0.14% | 22,000 (−4.0%) |

0.39% for eight sessions looks small. Repeated every two weeks for a year, it would come to roughly 10% of the portfolio. Short-dated protection near the money is a tool for a specific risk, not a standing policy.

### Example 3 — a cheap hedge that paid: January to March 2026 (estimated premiums)

On 2 January 2026 the Nifty closed at its high of 26,329, with India VIX at 9.45. Consider a portfolio that moves with the Nifty, worth about ₹34 lakh: two lots at that level and today's lot size of 65.

1. **Setup:** cheap protection (India VIX near its lowest in years) and large gains after a long rise.
2. **Entry:** buy two Nifty puts at 25,000 (5% below), expiring at the end of March. Estimated premium: about 106 points, or about ₹13,800 for two lots (0.4% of the portfolio).
3. **What happened:** the Nifty fell to 22,331 by 30 March, 15.2% lower.
4. **Result at the end of March:**

| ₹34 lakh portfolio, beta 1 | Without the hedge | With two 25,000 puts |
|---|---|---|
| Portfolio change | −₹5.2 lakh | −₹5.2 lakh |
| Put value at 22,331 (2,669 points × 130) | — | +₹3.47 lakh |
| Premium paid | — | −₹0.14 lakh |
| Net | −₹5.2 lakh (−15.2%) | −₹1.9 lakh (−5.5%) |

The put turned a 15% loss into a loss of about 5–6%. The cheapness of protection in January was the key: with India VIX at 9.45, a three-month put 5% below the market cost well under 1% of the portfolio.

### Example 4 — insurance that cost and never paid: 2023 (estimated premiums)

In 2023 the Nifty rose 20% with no fall of 5% inside any month that would have triggered the puts. An investor who rolled a monthly Nifty put 5% below the market all year would have paid premiums of about 1% of the portfolio, and received nothing.

```series
title: 2023 — a year when the insurance never paid
from: 2022-12-01
to: 2024-01-31
line: india:NIFTY50 | Nifty 50
line: india:INDIAVIX | India VIX | right
caption: The Nifty rose 20% in 2023 and India VIX spent most of the year between 10 and 14. Monthly puts 5% below the market expired worthless every time.
```

The cost was small because India VIX was low. In 2020, after the March crash, the same policy cost about 15% of the portfolio for the year, because premiums rose with volatility (section 8). Permanent insurance costs most exactly when it is bought after a shock.

---

## 7. Common mistakes

- **Buying protection after the fall.** Puts are then at their most expensive, and the worst may be over.
- **Hedging permanently with short-dated puts near the money.** The annual cost can exceed the market's average annual return.
- **Hedging the wrong risk.** A Nifty hedge does not protect a small-cap or mid-cap portfolio against its own falls; its beta to the Nifty may be high, but much of its risk is its own.
- **Forgetting to recalculate.** After a large rise in the portfolio, the hedge covers a smaller share of it.
- **Short futures without spare cash.** A rising market brings daily cash losses on the futures while the shares' gains are unrealised.
- **Collars that sell too close.** A call just above the market gives away most of the recovery that the investor was holding for.
- **Letting a collar's call be exercised by accident.** In India the call is physically settled; the shares are delivered at the strike.
- **Over-hedging.** More lots than the exposure is a short position, not a hedge.

---

## 8. What the evidence says

**Protective puts are expensive on average.** Roni Israelov ("Pathetic Protection: The Elusive Benefits of Protective Puts", *Journal of Alternative Investments*, 2019) studied S&P 500 protective puts. He found they reduced risk less efficiently than simply holding less equity, because the premium paid exceeded the protection received on average. The same reason explains the volatility risk premium in the [income guide](learn-fno-income.md): insurers are paid for taking crash risk.

**Collars.** Roni Israelov and Matthew Klein studied collars ("Risk and Return of Equity Index Collar Strategies", *Journal of Alternative Investments*, 2016). They found that most of a collar's risk reduction came simply from holding less equity exposure, and that collars gave up return for it. Edward Szado and Thomas Schneeweis studied collars on the Nasdaq-100 ETF. They found collars reduced losses in the bear markets in their sample, at the cost of upside in rising periods.

**An event study on the Nifty: the cost of permanent insurance.**

*Method.* The test runs from January 2010 to August 2026, 195 months in all. Every 21 sessions, buy a 30-day Nifty put 5% below the market and hold it until the next purchase. Estimate the premium with Black-Scholes using India VIX. The payout is what the put is worth at the end. Both are measured as a percentage of the index level and summed by calendar year.

| Year | Premium paid, % of portfolio | Payout, % of portfolio |
|---|---|---|
| 2010 | 7.4 | 0.7 |
| 2011 | 10.3 | 15.9 |
| 2012 | 5.5 | 2.5 |
| 2013 | 5.0 | 0.0 |
| 2014 | 3.9 | 0.0 |
| 2015 | 4.1 | 5.6 |
| 2016 | 3.4 | 3.0 |
| 2017 | 1.0 | 0.0 |
| 2018 | 2.2 | 2.0 |
| 2019 | 3.5 | 0.0 |
| 2020 | 15.2 | 31.9 |
| 2021 | 3.8 | 0.1 |
| 2022 | 5.0 | 2.2 |
| 2023 | 1.0 | 0.0 |
| 2024 | 2.1 | 1.3 |
| 2025 | 1.4 | 0.0 |
| 2026 (to August) | 2.1 | 6.3 |

*Nifty 50 and India VIX daily closes. Premiums are estimates with India VIX as the implied volatility, not traded prices; no costs.*

| Summary, 2010–2026 | Value |
|---|---|
| Months in which the put paid anything | 20 of 195 |
| Total premium paid, % of index (flat India VIX) | 77% |
| Total payout, % of index | 72% |
| Total premium paid with India VIX + 3 points (closer to real put prices) | 112% |
| Median yearly premium, flat India VIX / India VIX + 3 | 3.8% / 5.8% |
| Quarterly puts 10% below the market: median yearly premium (flat India VIX) | 1.3% |

**What it shows.** At the flat-volatility estimate, permanent insurance roughly broke even before costs. At prices closer to what out-of-the-money puts really cost, it lost about 40% of the index over 16 years, or about 2.5% a year. The payouts came in a few months: 2011, 2015, March 2020 and early 2026. Cheaper, further-out quarterly puts cost much less, but they pay only in deep falls.

A collar version of the same test (selling a call 5% above the market each month) showed the other cost. Over the period, the calls gave away more upside than the puts recovered on the downside, because the Nifty rose in most months.

**Caveats.** The premiums are modelled, not traded. The flat-volatility estimate understates real put prices; the "+3 points" adjustment is a rough correction from one snapshot. Costs, taxes and the bid–ask spread are excluded. The Nifty is a price index, without dividends.

**What is unknown.** Whether conditional hedging (only when a signal says risk is high) beats permanent insurance after costs depends on the signal. It has to be tested for your own rule, and the test needs several real falls in it to mean anything.

---

## 9. Building and testing it yourself

**Data you need.** Daily closes of the Nifty and India VIX, and of your portfolio or its holdings. Historical option prices if you can get them; otherwise model premiums with Black-Scholes and add a skew for out-of-the-money puts. Futures prices, or at least a short-term interest rate, for a futures hedge. Expiry dates and lot sizes by date.

**What to measure.** Run the portfolio with and without the hedge over the same dates.

- The worst month and the largest peak-to-trough fall, with and without.
- The total cost of premiums, and the total payout.
- The return given up in rising years.
- For futures hedges: the largest cash outflow from daily settlement in a rising market.

**Look-ahead traps.**

- Choosing the hedge's start dates with hindsight ("I would have hedged before March 2020").
- Using a beta measured over the whole period, including the future.
- Using the close of a signal day as the hedge's price.

**Costs in India (approximate, October 2026; check current rates).** Brokerage per order, commonly about ₹20 at discount brokers. STT on the premium of options sold and on futures sold, and on the intrinsic value of index options exercised at expiry; stock contracts settled by delivery pay 0.1% of the full contract value. Rates were raised in October 2024 and again from 1 April 2026, and change with Budgets. Exchange charges, GST of 18% on brokerage and exchange charges, stamp duty on purchases, and the bid–ask spread.

**Parameters to test, without over-fitting.** The put's distance below the market, its expiry, the hedge ratio, and the trigger for conditional hedges. Test them one at a time, keep a holdout period, and prefer settings that work across a broad range. With only a handful of real crashes in any history, a hedging rule tuned to them will look better than it is. See [backtesting](learn-test-backtesting.md).

A sketch of a conditional hedge:

```
every session t:
    trigger = nifty_close(t) < sma200(t) and sma200(t) < sma200(t-20)
              or event_within(t, 30 days)
    if trigger and no hedge:
        lots   = floor(portfolio_value × beta / (nifty(t) × lot_size))
        strike = nifty(t) × 0.95, rounded to a listed strike
        expiry = first monthly expiry 30–90 days away (after the event, if any)
        buy lots puts at t+1, if premium_this_year + cost <= budget
    if hedge open:
        if not trigger: sell the puts
        elif nifty fell >= 10% since entry: sell puts, buy lower strike (roll down)
        elif days_to_expiry <= 7: roll to next expiry
```

---

## 10. Checklist

- [ ] The reason for the hedge is written down: an event, a trend signal, gains to protect, or cheap protection.
- [ ] The hedge has an end: a date, or a condition that removes it.
- [ ] For a portfolio: beta is recent, and lots = value × beta ÷ (index × lot size), rounded down.
- [ ] The put's strike and expiry match the risk: how far a fall you can accept, and for how long.
- [ ] Implied volatility is checked: protection bought when India VIX is high is expensive.
- [ ] The cost fits within the yearly hedge budget.
- [ ] For a collar: you are content to sell the shares at the call's strike.
- [ ] For short futures: spare cash is set aside for daily settlement.
- [ ] For stock options: you know whether you will deliver the shares or close before expiry.
- [ ] The hedge's cost and payout are recorded, so the year's total can be reviewed.

---

## Further reading

- Lawrence G. McMillan, *Options as a Strategic Investment* — protective puts, collars and index hedging.
- John C. Hull, *Options, Futures, and Other Derivatives* — hedging with index futures and the beta hedge ratio.
- Nassim Nicholas Taleb, *Dynamic Hedging* — how professionals manage option risk, and why tails matter.
- Roni Israelov, "Pathetic Protection: The Elusive Benefits of Protective Puts", *Journal of Alternative Investments*, 2019.
- Roni Israelov and Matthew Klein, "Risk and Return of Equity Index Collar Strategies", *Journal of Alternative Investments*, 2016.
- Edward Szado and Thomas Schneeweis, "Loosening Your Collar: Alternative Implementations of QQQ Collars", *Journal of Trading*, 2010.
- Related guides: [directional options](learn-fno-directional.md), [selling options for income](learn-fno-income.md), [portfolio risk](learn-risk-portfolio.md), [market volatility](learn-health-volatility.md), [market trend](learn-health-trend.md), [the economic calendar](learn-macro-calendar.md).
