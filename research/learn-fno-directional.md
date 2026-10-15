# Directional options — calls, puts and debit spreads

**In short**

- Buying a call or a put lets you bet on a move with a loss capped at what you paid. The price of that cap is that the stock must move far enough, and soon enough, to cover the premium.
- A debit spread (buy one option, sell a further one) costs less and breaks even sooner, but it caps the profit. For most swing trades it is the better default.
- Choose the option from the trade plan: the expiry from how long the move should take, the strike from how far the stock should go.
- Size by the premium at risk, not by the number of lots you can afford. Most bought options that are held to expiry lose money.
- In India, index options settle in cash; stock options become a delivery of shares at expiry if they finish in the money.

This guide is about using options to express a view on direction: up or down, over days to weeks. It assumes you know what a call and a put are. The basics (calls, puts, strikes, premium, expiry) are covered in the options basics guide in the Futures & options section. The price sensitivities (delta, theta, vega) are in the pricing and greeks guide in the same section.

All option prices in this guide come from one snapshot of NSE's option chains. The prices were taken at about 10:15 am on 15 October 2026, during trading. They moved during the day, and they are one moment, not a history.

---

## 1. The idea

Start with a real case. At the snapshot, the Nifty stood at 22,906.55. A trader who expected a rise over the next eight sessions could buy the **23,000 call** expiring on 27 October 2026 for ₹187.90 per unit.

One Nifty option lot is 65 units. So one lot cost 187.90 × 65 = **₹12,214**. That is the most the trade can lose.

```payoff
title: Long Nifty 23,000 call (27 Oct 2026 expiry), one lot of 65
underlying: 22906.55
lot: 65
range: 22300 23900
leg: buy call 23000 @ 187.9
before: 6d 12.2%
caption: Real premium from the 15 Oct 2026 snapshot. The call breaks even at 23,188 on expiry day, 1.2% above where the Nifty stood. Below 23,000 the whole premium is lost. The blue line shows the value six days before expiry: the same price is worth less as time runs out.
```

Compare the same view taken with Nifty futures. One futures lot of 65 at 22,940 controls about ₹14.9 lakh of index. A 2% fall costs about ₹30,000. A 5% gap would cost about ₹75,000, and nothing caps it.

The call caps the loss at ₹12,214. In exchange, the index must rise 188 points before the call makes a rupee.

That is the whole trade-off of buying options:

- **You pay a premium** (the option's price) for a limit on the loss.
- **The premium has two parts.** One is *intrinsic value*: what the option is worth if exercised now. The other is *time value*: the rest, which is the price of what might still happen.
- **Time value melts.** It falls to zero at expiry, faster in the last days. This decay is called *theta*.
- **So you need the move, and you need it in time.** Being right after expiry pays nothing.

**Who is on the other side?** Mostly professional option sellers: market makers who hedge, and traders who sell options for income. They charge a margin over fair value. Across most of history, the implied volatility built into option prices has been above the volatility that followed (section 8). A buyer is paying for insurance, and insurance is priced to make the insurer money on average.

So when can buying options work? When your forecast of direction has a real edge, and that edge is larger than the premium's built-in margin. Options do not create an edge. They change its shape: smaller, capped losses, more frequent losses, and occasionally a large gain.

### The debit spread

The usual improvement is to sell a second option further out of the money. Buy the 23,000 call at ₹187.90. Sell the 23,500 call at ₹41.25. This is a **bull call spread**, and the net cost is ₹146.65 per unit.

```payoff
title: Bull call spread on Nifty, 23,000 / 23,500 (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22300 23900
leg: buy call 23000 @ 187.9
leg: sell call 23500 @ 41.25
before: 6d 12.2%
caption: Real premiums from the snapshot. The spread costs ₹9,532 a lot and can be worth at most ₹32,500 (500 points × 65). It breaks even at 23,147, about 41 points sooner than the call alone. Above 23,500 the profit stops growing.
```

The sold call pays for part of the bought one, so the spread breaks even sooner and loses less if wrong. It also suffers less from time decay and from a fall in implied volatility, because the two legs offset each other. What you give up is everything above 23,500.

The mirror image for a fall is the **bear put spread**: buy a put near the money, sell a lower one.

```payoff
title: Bear put spread on Nifty, 22,900 / 22,400 (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22000 23600
leg: buy put 22900 @ 214
leg: sell put 22400 @ 72.7
caption: Real premiums from the snapshot. Net cost 141.30 points (₹9,185 a lot); maximum value 500 points. It breaks even at 22,759.
```

| Structure (27 Oct expiry, one lot) | Cost | Breakeven | Move needed | Maximum profit |
|---|---|---|---|---|
| Buy 23,000 call | ₹12,214 | 23,188 | +1.2% | No cap |
| Buy 23,500 call | ₹2,681 | 23,541 | +2.8% | No cap |
| Bull call spread 23,000 / 23,500 | ₹9,532 | 23,147 | +1.1% | ₹22,968 |
| Buy 22,900 put | ₹13,910 | 22,686 | −1.0% | Large (to zero) |
| Bear put spread 22,900 / 22,400 | ₹9,185 | 22,759 | −0.6% | ₹23,316 |

*Nifty at 22,906.55; last traded prices at about 10:15 am on 15 October 2026.*

---

## 2. When it works and when it doesn't

**It works when the move is larger than the market expects.** The market's expectation is visible. Add the at-the-money call and put of one expiry: this is the *straddle* price. At the snapshot, the 22,900 call and put for 27 October cost 240 + 214 = 454 points. The market was pricing a typical move of about ±2% by expiry.

If your setup usually produces moves larger than that within the time left, buying options can pay. If it produces moves of about that size, you are paying full price for an average outcome.

**Conditions that favour buying:**

- **Implied volatility is low against its own history.** Options are cheap when the market is calm. India VIX (the Nifty's 30-day implied volatility) closed at 14.6 on 14 October 2026, against a high of 27.9 in March 2026.
- **A trend with momentum and a clear trigger.** A breakout from a base, or a trend that resumes after a pullback, with a stop level that defines when the idea is wrong (see [breakouts and bases](learn-bases.md)).
- **A move expected soon.** The shorter the wait, the less time value you pay for.

**Conditions that work against it:**

- **Implied volatility is high**, after a fall or ahead of an event. You pay for a large expected move. After the event, implied volatility usually drops and the option loses value even if the price moved your way (the volatility guide in the Futures & options section calls this a volatility crush).
- **A sideways market.** Time decay takes a little every day while nothing happens.
- **Slow trends.** A stock that rises 1% a week can beat a short-dated option's decay only barely. Owning the shares or futures fits a slow trend better.

```series
title: India VIX and the Nifty, 2025–2026: when options were cheap and when they were dear
from: 2025-06-01
to: 2026-10-14
line: india:NIFTY50 | Nifty 50
line: india:INDIAVIX | India VIX | right
mark: 2026-03-30 | VIX 27.9
caption: India VIX was 9.45 on 2 January 2026, at the Nifty's high. It reached 27.9 on 30 March, after a 15% fall. In early April it was still near 25, so an option cost far more for the same strike distance than in January.
```

### India and the US

- **India.** Index options (Nifty, Bank Nifty, Fin Nifty, Midcap Select) are the liquid market; near the money, the Nifty's bid–ask spread was about 0.2–0.4% of the premium at the snapshot. Stock options are thinner: Reliance's November options showed spreads of about 1–5%. Only the Nifty has weekly expiries on NSE; the others expire monthly. Stock options go out about three months.
- **India — settlement.** Index options are European (exercised only at expiry) and settled in cash. Stock options are physically settled: a long Reliance call that ends in the money becomes an obligation to buy 500 shares. Close stock options before expiry unless you want the shares.
- **US.** Stock options are American (exercisable any day), cover 100 shares, and trade in one-cent steps. Long-dated options (one to two years, often called LEAPS) exist on most large stocks, which suits slower trends. There is no STT.

---

## 3. The rules

The rules below are a starting specification. Each is written as a condition you can test. Every number is a parameter, listed with its range in section 4.

### Universe and filters

- Underlying: an index (Nifty, Bank Nifty) or a stock with listed options.
- Liquidity: the option you buy and the one you sell each have a bid–ask spread of at most **2%** of the mid price, and open interest of at least **500** contracts. At the snapshot, Nifty strikes near the money passed easily; many Reliance November strikes did not.
- No result announcement before expiry, unless the trade is about the result (the event-trades guide in the Futures & options section covers that case).
- India VIX (or the stock's own implied volatility) is below its **70th percentile** of the past year when buying a single option. Above it, use a spread instead.

### Setup

The setup comes from your stock or index method, not from the option chain. Two examples:

- **Breakout (bullish).** The close is above the highest close of the previous **60** sessions. Volume that day is at least **2.5 times** the 50-day average. The close is above the 50-day moving average.
- **Breakdown (bearish).** The close is below the lowest close of the previous **60** sessions, below the 50-day average, and the 50-day average is lower than **20** sessions ago.

The setup also defines two prices you need for the option choice:

- **The invalidation level**: where the idea is wrong. For a breakout, a close back below the breakout level.
- **The target**: where you expect the move to reach. For example the next resistance level, or a multiple of the stop distance (2R).

### Entry

- Choose the **expiry**: the first expiry at least **1.5 times** the expected holding period away. A two-week idea needs at least three weeks of option life.
- Choose the **strike** for a single option: the strike with delta between **0.40 and 0.60** (at the money). Delta is roughly how much the option moves for a one-point move in the underlying. At the snapshot, the Nifty 23,000 call had a delta of about 0.47 and the 23,500 call about 0.15.
- Choose the **spread**: buy the at-the-money strike and sell the strike nearest your target. On the snapshot, a Nifty target of 23,500 gives the 23,000 / 23,500 spread.
- Order type: a **limit order** at or just above the mid price. Enter a spread as a single spread order where your broker allows it, so both legs fill together.
- Timing: enter after the setup is confirmed at the close, or in the next session after the first 15 minutes. The opening minutes have the widest spreads.

### Initial stop

An option's own price is a poor stop level, because it moves with time and volatility as well as price. Stop on the underlying:

- **Exit the whole position if the underlying closes beyond the invalidation level** (for a breakout, a close back below the breakout level).
- Backstop on the premium: exit if the position has lost **50%** of what you paid.

### Exits

- **Target:** exit when the underlying reaches the target, or when a spread is worth **80%** of its maximum value. The last 20% takes the longest to earn.
- **Time:** exit when **one third** of the option's life remains and the move has not come. Time decay is fastest at the end.
- **Before expiry:** close stock options at least **two sessions** before expiry, to avoid physical delivery and the higher STT charged on exercise.
- **Invalidation:** the stop above.

### Position size

Size by the premium at risk, because a bought option can go to zero:

```
lots = floor( account × risk per trade / (premium per unit × lot size) )
```

- The risk per trade is **0.5–1%** of the account, the same as for a stock trade (see [position sizing](learn-risk-sizing.md)).
- If you plan to exit at a 50% loss of premium, you may size on half the premium, but gaps and fast moves can make the loss larger. Sizing on the full premium is the safer choice.
- Example: a ₹10 lakh account risking 1% has ₹10,000. One Nifty lot of the 23,000 / 23,500 spread costs ₹9,532, so the size is one lot. The single 23,000 call at ₹12,214 is too large for this account.

### Managing the trade

- Do not add to a losing option position.
- When a long call has doubled, you can **roll up**: sell it and buy a higher strike, taking the original cost off the table.
- Or convert a winning call into a spread by selling a higher call. This locks in part of the gain and cuts the time decay.
- Check implied volatility at every review. A large rise lifts the value of a bought option; take it if the price has also moved your way.

---

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Maximum bid–ask spread | 1–3% of mid | Cost of entry and exit | Nifty near the money ≈ 0.2–0.4%; stock options often 1–5% |
| Minimum open interest | 200–1,000 contracts | Ability to exit | A thin strike can quote a price you cannot trade at |
| IV percentile limit for single options | 50–80th | When to buy outright vs use a spread | Lower limit means fewer, cheaper trades |
| Breakout lookback | 20–120 sessions | Setup | From the stock method, not the option |
| Breakout volume | 1.5–3 × 50-day average | Setup | As above |
| Expiry multiple | 1.2–2 × expected holding period | Time bought | Longer costs more but decays more slowly |
| Single-option delta | 0.40–0.60 (0.30–0.70) | How much of the move you capture | Lower delta is cheaper but needs a bigger move |
| Short strike of the spread | At the target | Where profit stops | Nearer: cheaper, smaller profit |
| Premium backstop | 40–60% loss | Maximum loss before the price stop | Tighter cuts more good trades |
| Spread profit target | 70–90% of maximum value | When to bank a spread | — |
| Time exit | ⅓ to ½ of option life left | Exposure to fast decay | — |
| Days before expiry to close stock options | 2–5 sessions | Delivery and exercise STT | Brokers may close positions themselves |
| Risk per trade | 0.5–1% of account | Size | Count the full premium as at risk |

---

## 5. Variations

- **Stock replacement.** Buy a deep in-the-money call (delta **0.80** or more) instead of the shares. It has little time value and behaves almost like the stock, for a fraction of the capital. Lawrence McMillan describes this use in *Options as a Strategic Investment*. In India the three-month limit on stock options makes this a short-term tool; in the US, long-dated calls make it practical for months.
- **Out-of-the-money "lottery" calls.** Cheap calls with delta under **0.20**. They rarely pay (section 8). Researchers who studied US retail option traders found a strong preference for exactly these short-dated, far-out options, and poor results from them.
- **Ratio and backspreads.** Buying more options than you sell (a backspread) keeps unlimited upside with little or no cost, but loses most at the far strike. These are covered in the volatility strategies guide in the Futures & options section.
- **Diagonal spreads.** Buy a later expiry and sell a nearer one at a higher strike. The sold option decays faster than the bought one. This suits a slow move.
- **Futures with a protective option.** Buy a future and a put (a synthetic call). Useful where the future is more liquid than the calls, as for many Indian stocks. See the [hedging guide](learn-fno-hedging.md).
- **Sheldon Natenberg's approach** in *Option Volatility and Pricing*: choose the structure from the volatility view first. If implied volatility looks cheap, buy single options; if it looks dear, sell an option against the one you buy.

---

## 6. Worked examples

Examples 1 and 2 use real premiums from the snapshot. Examples 3 and 4 are historical; for those, option prices were not stored, so the premiums are **estimates** from the Black-Scholes model. Black-Scholes is the standard formula for an option's fair value. The estimates use the stock's own volatility over the previous 20 sessions as the implied volatility. Real prices would have differed, usually upwards after a big move.

### Example 1 — a Nifty view with three structures (snapshot)

On 15 October 2026 the Nifty was rising 1.3% in the morning after closing at 22,623 the day before. The index was 14% below its January high. Suppose a trader expects a rebound to 23,500 by 27 October, with the idea wrong below 22,600.

| Structure | Cost per lot | Value if Nifty is 23,500 at expiry | Value if 22,600 |
|---|---|---|---|
| Buy 23,000 call | ₹12,214 | ₹32,500 (+166%) | ₹0 |
| Buy 23,500 call | ₹2,681 | ₹0 | ₹0 |
| 23,000 / 23,500 spread | ₹9,532 | ₹32,500 (+241%) | ₹0 |

If the target is reached exactly, the spread earns more than the call, at lower cost. The cheap 23,500 call earns nothing at all, because the target is its strike. The call beats the spread only if the Nifty goes well past 23,500. In practice the stop at 22,600 would close the trade before expiry. At that point each structure would still have some time value left.

### Example 2 — a Reliance rebound, with a spread (snapshot)

Reliance closed at ₹1,175 on 14 October 2026, and its 50-day average was ₹1,260. The stock was 26% below its January high. At the snapshot it traded at ₹1,200.8. A trader betting on a rebound to the 50-day average by late November could use the November options (lot 500).

```payoff
title: Reliance bull call spread, 1,200 / 1,260 (23 Nov 2026 expiry), one lot of 500
underlying: 1200.8
lot: 500
range: 1100 1320
leg: buy call 1200 @ 43.3
leg: sell call 1260 @ 20
before: 20d 25%
caption: Real premiums from the snapshot. Cost ₹23.30 a share (₹11,650 a lot); maximum value ₹60 a share (₹30,000). Breakeven ₹1,223.30. The single 1,200 call would cost ₹21,650 and break even at ₹1,243.30.
```

Two cautions come from the chain itself. The November strikes were thin. The bid–ask spread was 0.8% of the price on the lower call, and 1.2% on the higher one. Crossing those spreads in and out of both legs costs about 2–3% of what the spread costs. And this is a stock option: if the spread is still open at expiry with Reliance above ₹1,200, the bought call becomes a purchase of 500 shares (₹6 lakh).

### Example 3 — a breakout that ran: BHEL, April 2026 (estimated premiums)

```series
title: BHEL breakout, April 2026
from: 2026-01-01
to: 2026-06-15
line: india:BHEL.NS | BHEL
line: india:BHEL.NS@sma50 | 50-day average
line: india:BHEL.NS@vol | Volume | pane2 bars
mark: 2026-04-13 | Breakout close 287.8
caption: On 13 April 2026 BHEL closed at 287.8, above its highest close of the previous 60 sessions (284.7), on 3.1 times its average volume. A month later, on 13 May, it closed at 403.9.
```

The rules applied step by step:

1. **Setup** (13 April): close above the 60-session high, volume 3.1 times average, close above the 50-day average (261). Invalidation: a close below 284.7.
2. **Option choice**: an expiry about a month away. BHEL's 20-day volatility was 47%, so the estimated price of a one-month 290 call was about ₹15. A 290 / 315 call spread was estimated at about ₹8.60.
3. **Size**: at the October 2026 lot of 2,625 shares, one lot of the call costs about ₹39,600, and one lot of the spread about ₹22,600. A ₹25 lakh account risking 1% (₹25,000) can take one spread, not one call.
4. **What happened**: BHEL never closed below 284.7. By 13 May it was at 403.9.
5. **Exit**: by the estimate, the spread passed 80% of its maximum on 23 April, seven sessions in, with BHEL at 337.6. Exiting there returned about 2.4 times its cost. Held to the end, it was worth ₹25 a share, 2.9 times its cost. The single call would have been worth about ₹114, about 7.5 times its cost.

This is the case where the single call wins. A strong, fast move far beyond the target rewards the uncapped structure.

### Example 4 — a breakout that failed: KEI Industries, March 2026 (estimated premiums)

```series
title: KEI Industries: a breakout that reversed, March 2026
from: 2025-12-01
to: 2026-04-30
line: india:KEI.NS | KEI Industries
line: india:KEI.NS@sma50 | 50-day average
line: india:KEI.NS@vol | Volume | pane2 bars
mark: 2026-03-02 | Breakout close 5,206
caption: KEI closed at 5,206 on 2 March 2026, above its 60-session high of 5,080, on 5.5 times average volume. Two sessions later it closed at 4,979, and on 30 March at 4,038.
```

1. **Setup** (2 March): all conditions met. Invalidation: a close below 5,080.
2. **Option**: one-month 5,205 call, estimated at about ₹199 with KEI's 31% volatility. At the lot of 175, about ₹34,800.
3. **Stop**: on 4 March KEI closed at 4,979, below 5,080, so the rule says exit. Valued at that close, the call was worth about ₹93, a loss of about ₹18,500 (53%).
4. **Without the stop**: by 30 March KEI was at 4,038. The call would have expired worthless.

The stop on the underlying did its job. The loss was still about half the premium, because a short-dated option loses value fast when the price falls. That is why section 3 sizes on the full premium.

---

## 7. Common mistakes

- **Buying far out-of-the-money options because they are cheap.** A cheap option is cheap because it rarely pays. A ₹2,681 Nifty call that needs a 2.8% rise in eight sessions is a lottery ticket.
- **Buying weekly options for a multi-week idea.** The weekly 23,000 Nifty call (expiring 19 October) cost ₹96 against ₹187.90 for the 27 October call. The cheaper option has four days to be right.
- **Sizing by lots instead of by risk.** Ten lots of a cheap option is ten times the loss when it expires worthless.
- **Ignoring implied volatility.** Buying calls after a crash, or before results, often means paying for a move that has already been priced in.
- **Using the option's price as the stop.** It falls with time even when the idea is intact. Stop on the underlying.
- **Holding stock options into expiry.** In India this can turn into a delivery obligation, and exercise is charged a higher STT.
- **Legging into spreads.** Buying one leg and waiting to sell the other turns a defined-risk trade into an open bet.
- **Trading the opening minutes.** Spreads are widest then, and the first prices are often not tradable.

---

## 8. What the evidence says

**Bought options lose on average.** Joshua Coval and Tyler Shumway (*Journal of Finance*, 2001) measured US index option returns. Calls earned less than their risk would suggest, and puts lost heavily on average. Gurdip Bakshi and Nikunj Kapadia (*Review of Financial Studies*, 2003) found that option buyers pay a volatility risk premium: options are priced for more volatility than usually arrives.

**Retail traders lose most.** SEBI's study of individual F&O traders in India (published in September 2024, covering FY22 to FY24) found that about 9 in 10 lost money. An earlier SEBI study, of FY22, found the same proportion. In the US, Svetlana Bryzgalova, Anna Pavlova and Taisiya Sikorskaya (*Journal of Finance*, 2023) found that retail option traders favour cheap, short-dated options and lose money on them, with large costs from bid–ask spreads.

**An event study on the Nifty.** The question: had you bought a one-month Nifty option at a regular interval since 2010, how often would it have paid?

*Method.* Every 21 sessions from January 2010 to August 2026 (195 non-overlapping months), estimate the premium of a 30-day Nifty option with Black-Scholes. Use India VIX that day as the implied volatility and a 6.5% interest rate. Value the option at the Nifty's close 21 sessions later.

| Position (one month) | Months profitable | Median result, % of premium | Average result, % of premium | Median premium, % of index |
|---|---|---|---|---|
| Buy at-the-money call | 41% | −51% | +2% | 2.1% |
| Buy call 3% out of the money | 26% | −100% | −9% | 0.9% |
| Buy at-the-money put | 29% | −100% | −2% | 1.6% |
| Call spread, at the money / 3% out | 48% | −21% | +12% | 1.2% |

*Nifty 50 and India VIX daily closes, January 2010 – September 2026. Premiums are estimates, not traded prices.*

**What it shows.** Bought options lose in most months. The typical outcome is a large loss of premium, offset on average by rare big gains. The at-the-money call roughly broke even before costs, helped by a Nifty that rose more than fourfold over the period. Out-of-the-money options did worst. The call spread won more often and had the best average.

**Caveats.** India VIX is an at-the-money measure, so this method ignores the *skew*: real out-of-the-money puts cost more and calls less (the snapshot showed put implied volatilities 2–5 points above the at-the-money level). Costs, bid–ask spreads and taxes are left out. The Nifty is a price index, without dividends. And no entry signal was used: these are random-timing results, the baseline a real method must beat.

**What is unknown.** Whether a given setup's edge survives option costs is specific to the setup. No published study answers that for Indian swing setups. You have to test it (section 9).

---

## 9. Building and testing it yourself

**Data you need.**

- Daily prices of the underlying, adjusted for splits and bonuses.
- Historical option prices, or at least daily implied volatility (India VIX for the Nifty; for stocks, the at-the-money implied volatility if you can get it).
- Lot sizes by date. NSE revises them, and contract values matter for sizing.
- Expiry dates by date. India's expiry days and weekly contracts have changed several times.

**If you have no historical option prices,** estimate them as section 8 did. Use the underlying's implied volatility where you have it. Without it, use recent realised volatility plus a margin of a few points, because implied volatility is usually higher than realised (section 8 of the [income guide](learn-fno-income.md)). Add a skew for out-of-the-money strikes. Say clearly in your results that the prices are modelled.

**Look-ahead traps.**

- Entering at the close that confirmed the setup. You only know the close after it prints; enter at the next session's price.
- Using implied volatility from a time after the entry.
- Choosing the strike from where the stock went, rather than from the target known at entry.

**Survivorship.** Today's F&O list contains stocks that did well enough to stay in it. Stocks removed from F&O, or delisted, are missing unless your data includes them. Results on today's list will flatter the method.

**Costs in India (approximate, October 2026; check current rates).**

- Brokerage: a flat fee per order at discount brokers, commonly about ₹20.
- STT on the sale of an option, as a percentage of the premium. A higher STT applies to the intrinsic value if an option is exercised at expiry. Rates were raised from 1 October 2024 and can change with each Budget.
- Exchange transaction charges on the premium, GST of 18% on brokerage and exchange charges, stamp duty on purchases, and a small SEBI fee.
- The bid–ask spread, which is often the largest cost. Model fills at the bid when selling and the ask when buying.

**Tax.** In India, F&O profits are generally taxed as business income (non-speculative), at your slab rate, and losses can be carried forward under conditions. Rules change; check with a tax adviser.

**Parameters to test, and how not to over-fit.** Test the expiry multiple, the strike (delta), and the spread width. Keep the stock setup fixed while you do it. Change one parameter at a time and look for a broad plateau of good results, not a single best value. Hold out the last two or three years as an untouched test period. See [backtesting](learn-test-backtesting.md) for the general method.

**What a good test reports.** Number of trades; win rate; average win and loss as a multiple of premium; expectancy per trade after costs; the worst run of losses; results by year and by volatility level (low, middle and high India VIX). Compare with the same signals traded in shares or futures. If the options version does not beat that after costs, the option is adding cost, not value.

A sketch of the core logic:

```
for each session t:
    if setup(t) and liquid(option chain at t+1):
        expiry  = first expiry >= 1.5 × expected_hold
        long_k  = strike with delta closest to 0.50
        short_k = strike nearest to target
        lots    = floor(account × risk / (debit × lot_size))
        enter at t+1 at ask(long_k) − bid(short_k)
    for each open position:
        if close(underlying) beyond invalidation: exit at t+1
        elif value >= 0.8 × max_value: exit
        elif days_left <= life / 3: exit
        elif stock option and sessions_to_expiry <= 2: exit
```

---

## 10. Checklist

- [ ] The trade comes from a setup with a defined invalidation level and target, not from the option chain.
- [ ] No result announcement or other scheduled event before expiry, unless that is the trade.
- [ ] The expiry is at least 1.5 times the expected holding period away.
- [ ] Implied volatility is checked: single option if it is low, spread if it is high.
- [ ] Both legs have a bid–ask spread under 2% and enough open interest.
- [ ] The breakeven is written down, and the expected move reaches it with room to spare.
- [ ] Size: the full premium at risk is no more than 0.5–1% of the account.
- [ ] Order is a limit order (a single spread order for spreads), not in the opening minutes.
- [ ] Stop on the underlying, premium backstop, profit target and time exit are written down.
- [ ] For stock options: the exit date is at least two sessions before expiry.

---

## Further reading

- Lawrence G. McMillan, *Options as a Strategic Investment* — the reference for every structure here.
- Sheldon Natenberg, *Option Volatility and Pricing* — how implied volatility changes the choice of strategy.
- John C. Hull, *Options, Futures, and Other Derivatives* — the textbook treatment of pricing.
- Euan Sinclair, *Positional Option Trading* — a practitioner's view of where option edges come from.
- Joshua D. Coval and Tyler Shumway, "Expected Option Returns", *Journal of Finance*, 2001.
- Gurdip Bakshi and Nikunj Kapadia, "Delta-Hedged Gains and the Negative Market Volatility Risk Premium", *Review of Financial Studies*, 2003.
- Svetlana Bryzgalova, Anna Pavlova and Taisiya Sikorskaya, "Retail Trading in Options and the Rise of the Big Three Wireless Brokers", *Journal of Finance*, 2023.
- SEBI, studies of profit and loss of individual traders in equity F&O (January 2023 and September 2024).
- Related guides: [position sizing](learn-risk-sizing.md), [stops and exits](learn-risk-stops-exits.md), [expectancy](learn-risk-expectancy.md), [market volatility](learn-health-volatility.md), [income strategies](learn-fno-income.md), [hedging](learn-fno-hedging.md).
