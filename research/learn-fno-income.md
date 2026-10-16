# Selling options for income — covered calls, cash-secured puts, credit spreads and iron condors

**In short**

- Option sellers collect a premium up front and keep it if the price stays away from the strike. They win often, because options are usually priced for more movement than arrives.
- The catch is the shape of the results: many small gains and a few large losses. One bad month can take back a year of premiums.
- Defined-risk structures (credit spreads, iron condors) cap that loss. Size every trade by its maximum loss, or by a stress loss if the risk is open-ended, never by the margin.
- Covered calls and cash-secured puts suit an investor who is happy to own the stock or sell it at the strike. They are a way of being paid to wait, not a source of free money.
- In India, stock options settle by delivery, so a sold stock option that ends in the money becomes a purchase or sale of shares.

This guide covers the main ways to sell options: covered calls, cash-secured puts, credit spreads and iron condors. It assumes you know calls, puts, strikes and premiums (the options basics guide in the Futures & options section). For buying options, see [directional options](learn-fno-directional.md).

The option prices here come from one snapshot of NSE's option chains, taken at about 10:15 am on 15 October 2026. Prices moved during the day. The snapshot is one moment, not a history.

---

## 1. The idea

Start with a real price. At the snapshot the Nifty stood at 22,906.55. The **22,000 put** expiring on 27 October 2026 traded at ₹32.05. That strike was about 4% below the market, eight sessions before expiry.

One lot is 65 units. Sell one lot and you receive 32.05 × 65 = **₹2,083**. If the Nifty closes above 22,000 on 27 October, the put expires worthless and you keep all of it.

```payoff
title: Selling one Nifty 22,000 put (27 Oct 2026 expiry), one lot of 65
underlying: 22906.55
lot: 65
range: 20500 23500
leg: sell put 22000 @ 32.05
before: 6d 17.8%
caption: Real premium from the 15 Oct 2026 snapshot. The most this trade can earn is ₹2,083. It loses below 21,968, and the loss grows by ₹65 for every point the Nifty falls further. A 10% fall, to about 20,600, would cost about ₹88,000 — more than 40 times the premium.
```

That picture is the whole business of selling options:

- **The odds favour you.** The put pays you if the Nifty does anything except fall more than 4% in eight sessions. Most of the time it doesn't.
- **The payoff does not.** You can earn ₹2,083 at most, and lose many times that.

**Why it can work.** Buyers of options are often buying insurance: fund managers protecting portfolios, traders capping risk. They will pay more than the expected loss to be protected. Market makers who take the other side charge for the risk of being wrong in a crash. The result is a **volatility risk premium**: the implied volatility in option prices tends to be above the volatility that follows. On the Nifty, India VIX was above the next month's realised volatility on about four days in five since 2010 (section 8).

**Who is on the other side.** Hedgers who want protection, and buyers who want a cheap, leveraged bet. Both pay for something other than a fair price, and the seller collects that difference.

**Why it can fail.** The premium is payment for carrying crash risk. When the crash comes, the seller pays. A seller who has not survived the worst month in the data has not yet earned the premium.

---

## 2. When it works and when it doesn't

**Conditions that favour selling:**

- **Implied volatility is high against its own history and against realised volatility.** You are paid more for the same risk. In March 2026 India VIX reached 27.9; in December 2025 it was near 9.
- **A range or a slow trend.** Time decay is the seller's income. It accumulates when nothing much happens.
- **After a volatility spike has peaked.** Implied volatility tends to fall back after a shock, which lifts the seller's position.

**Conditions that work against it:**

- **Very low implied volatility.** Premiums are small, so the reward is small for the same crash risk. India VIX was 9.45 on 2 January 2026, the Nifty's high, just before a 15% fall.
- **A market falling with rising volatility.** Short puts lose on the price move and on the rise in implied volatility at the same time.
- **Scheduled events inside the option's life**: results, an RBI policy decision, the Union Budget, elections (see the [economic calendar](learn-macro-calendar.md)). The premium may look rich, but it is rich for a reason.
- **Expiry day.** Gamma (how fast an option's sensitivity to price changes) is highest in the last hours. Small moves change the position's value sharply. SEBI also charges extra margin on short options on expiry day.

```series
title: Implied volatility tends to sit above what follows — India VIX and the Nifty, 2019–2026
from: 2019-01-01
to: 2026-10-14
line: india:INDIAVIX | India VIX
line: india:NIFTY50 | Nifty 50 | right log
mark: 2020-03-23 | Nifty −13% in one day
caption: India VIX is the market's estimate of the Nifty's volatility over the next 30 days. It was above the volatility that actually followed on most days. The exceptions are sudden falls such as March 2020, when realised volatility shot past what had been priced.
```

### India and the US

- **India.** Index options are cash-settled and European. Stock options settle by delivery: a sold Reliance call that ends in the money means delivering 500 shares. Selling any option needs margin, and since 2024 the option buyer must also pay the premium up front. Only the Nifty has weekly expiries on NSE.
- **India — margin.** A short index option needs margin of the same order as a futures position on the same lot. That is usually several times the premium, and it rises when volatility rises. Margin is collateral, not a measure of risk.
- **US.** Covered calls and cash-secured puts are standard in retirement and brokerage accounts. Stock options are American, so a short call can be assigned early, most often just before an ex-dividend date. Index options such as those on the S&P 500 are European and cash-settled. Many US traders sell options with zero days to expiry; the risk profile of those is closer to a bet on a single day.

---

## 3. The rules

Four structures, with one set of shared rules. Every number is a parameter, listed in section 4.

| Structure | You do | You want | Risk |
|---|---|---|---|
| Covered call | Own the shares; sell a call above the price | The stock to rise slowly, or stay flat | The stock falls (you still own it); upside above the strike is given away |
| Cash-secured put | Sell a put below the price; keep the cash to buy the shares | The stock to stay above the strike, or to buy it cheaper | The stock falls far below the strike |
| Credit spread | Sell an option; buy a further one as protection | The price to stay on your side of the sold strike | Capped at the strike gap minus the credit |
| Iron condor | A put credit spread below and a call credit spread above | The price to stay in the range | Capped, on one side at a time |

### Universe and filters

- Underlying: the Nifty or Bank Nifty for spreads and condors; for covered calls and cash-secured puts, a stock you would be content to own at the strike.
- Liquidity: each leg has a bid–ask spread of at most **3%** of the mid price and open interest of at least **500** contracts. Sellers fight the spread twice, at entry and exit.
- Volatility: India VIX (or the stock's implied volatility) is at or above its **40th percentile** of the past year. Below that, the premium is too small for the risk.
- Events: no result announcement, RBI policy decision or Budget before expiry.

### Setup

- **Credit spreads and condors.** The short strike is outside the expected move. Measure the expected move by the at-the-money straddle: the call plus the put. At the snapshot the 27 October straddle cost 454 points, about ±2%. Pick the short strike with a delta of **0.15–0.30** (roughly a 15–30% chance of ending in the money).
- **Direction for a single spread.** A put spread (bullish) when the close is above the 50-day moving average. A call spread (bearish) when it is below and the 50-day is falling.
- **Covered call.** You own (or buy) the shares. The call's strike is at or above a price at which you would happily sell.
- **Cash-secured put.** The put's strike is a price at which you would happily buy, for example near support (see [support and demand zones](learn-supply-demand.md)).

### Entry

- Expiry: **20–45 days** for monthly structures. Time decay accelerates in the last weeks, and longer expiries pay more in total.
- Width of a credit spread: **1–2%** of the index (for the Nifty, 200–500 points). Wider pays more credit but raises the maximum loss.
- Minimum credit: at least **one quarter** of the spread's width for a spread with a short delta near 0.25.
- Order: a single limit order for the whole structure, at or near the mid price.

### Initial stop

- **Credit spread or condor:** close the threatened side if its value reaches **2 times** the credit received. Or close if the index closes beyond the short strike.
- **Cash-secured put:** decide in advance whether you will take the shares. If not, close when the stock closes below the strike.
- **Covered call:** the stop belongs to the shares. Use the stop you would use without the call (see [stops and exits](learn-risk-stops-exits.md)), and buy back the call when you sell the shares.

### Exits

- **Profit target:** close at **50%** of the maximum profit. The rest takes the longest to earn and carries the most gamma risk.
- **Time:** close **5–7 days** before expiry, whatever the profit, for monthly structures.
- **Stock options:** close at least **two sessions** before expiry unless you intend delivery.

### Position size

Size by the **maximum loss**, never by margin.

- **Spreads and condors.** Maximum loss = (strike width − credit) × lot. Lots = account × risk per trade ÷ maximum loss per lot, with risk per trade at **1–2%**.
- **Naked short options.** The maximum loss is open. Size by a **stress loss**: the loss if the index falls (or rises) **10%** at once. The Nifty fell 13% on 23 March 2020 alone. Keep that stress loss at or below **5%** of the account.
- **Total.** The sum of maximum losses across all open income positions stays below **10–15%** of the account. Many short options on related underlyings are one bet.

### Managing the trade

- **Roll** (close and reopen further out in time) only for a net credit, and only if the original reason still holds. Rolling a losing position again and again turns a capped loss into an open one.
- If one side of a condor is tested, close that side or the whole condor. Do not widen the losing side.
- After a covered call is assigned or a put is exercised, you own new exposure. Treat it as a new trade, with its own stop.

---

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Short strike delta | 0.15–0.30 (puts and calls) | Win rate vs premium | Lower delta wins more often but pays less and loses as much in a crash |
| Days to expiry at entry | 20–45 | Premium and decay speed | Weeklies decay faster but give no time to react |
| Spread width | 1–2% of index; 5–10% of stock | Maximum loss per lot | — |
| Minimum credit | ¼–⅓ of width | Reward for the risk | Below ¼, costs eat most of the edge |
| Minimum IV percentile | 30–50th | When to sell at all | Higher threshold: fewer, better-paid trades |
| Bid–ask limit | 2–3% of mid | Cost | Stock options often fail it |
| Minimum open interest | 200–1,000 contracts | Ability to exit | — |
| Stop | 1.5–3 × credit, or a close beyond the short strike | Loss per trade | Tight stops cut many trades that would have recovered |
| Profit target | 40–75% of maximum profit | Holding time | — |
| Time exit | 5–7 days before expiry | Gamma risk | — |
| Risk per trade (spreads) | 1–2% of account at maximum loss | Size | — |
| Stress move (naked) | 10–20% gap | Size of open-risk trades | The largest one-day fall since 2007 was 13% (23 March 2020) |
| Stress loss limit | 3–5% of account | Size of open-risk trades | — |
| Total maximum loss | 10–15% of account | Portfolio risk | Count correlated underlyings together |

---

## 5. Variations

- **The wheel.** Sell cash-secured puts on a stock until assigned; then sell covered calls on the shares until they are called away; repeat. Popular in the US. In India it is limited by lot sizes and three-month expiries, and by delivery margins near expiry.
- **The 45-day, 50% rule.** A practitioner approach popularised by the tastytrade network: sell at around 45 days to expiry, close at 50% of maximum profit, and keep each trade small. It is close to the rules in section 3.
- **Index buy-write and put-write.** The Cboe publishes the BXM index (S&P 500 with a monthly at-the-money call sold against it) and the PUT index (cash-secured S&P 500 puts). They are the long-run benchmarks for covered calls and put selling (section 8).
- **Delta-hedged selling.** Professionals sell options and hedge the price risk with futures, keeping only the volatility exposure. Roni Israelov and Lars Nielsen argue for this in "Covered Calls Uncovered". It needs frequent adjustment and is costly for an individual in India.
- **Broken-wing structures.** A condor or butterfly with one wing wider than the other, to take less risk on one side. Butterflies are covered in the volatility strategies guide in the Futures & options section.
- **Jade lizard and similar.** A short put plus a short call spread, sized so that there is no loss on the upside. Still open-ended on the downside.

---

## 6. Worked examples

Examples 1 and 2 use real prices from the snapshot. Examples 3 and 4 are historical. No option prices were stored for those, so the premiums are **estimates** from the Black-Scholes model (the standard formula for an option's fair value), with India VIX as the implied volatility. Real out-of-the-money puts usually cost more than this estimate, which would have helped the seller a little.

### Example 1 — a Nifty iron condor (snapshot)

The straddle said ±2% by 27 October. A trader who expects the Nifty to stay inside that range sells both sides.

```payoff
title: Bull put spread on Nifty, 22,500 / 22,200 (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 21800 23300
leg: sell put 22500 @ 90.35
leg: buy put 22200 @ 47.05
caption: Real premiums from the snapshot. Credit 43.30 points (₹2,815 a lot). Maximum loss 256.70 points (₹16,686) below 22,200. Breakeven 22,457, about 2% below the market.
```

```payoff
title: Bear call spread on Nifty, 23,500 / 23,800 (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 22500 24200
leg: sell call 23500 @ 41.25
leg: buy call 23800 @ 15.1
caption: Real premiums from the snapshot. Credit 26.15 points (₹1,700 a lot). Maximum loss 273.85 points (₹17,800) above 23,800. Breakeven 23,526, about 2.7% above the market.
```

```payoff
title: Iron condor on Nifty: both spreads together (27 Oct 2026 expiry)
underlying: 22906.55
lot: 65
range: 21800 24200
leg: buy put 22200 @ 47.05
leg: sell put 22500 @ 90.35
leg: sell call 23500 @ 41.25
leg: buy call 23800 @ 15.1
before: 6d 14%
caption: Real premiums from the snapshot. Credit 69.45 points (₹4,514 a lot). The Nifty can end anywhere from 22,431 to 23,569 for a profit. Only one side can lose at expiry, so the maximum loss is 230.55 points (₹14,986).
```

| Piece (one lot) | Credit | Maximum loss | Short strike delta | Breakeven |
|---|---|---|---|---|
| Put spread 22,500 / 22,200 | ₹2,815 | ₹16,686 | about −0.24 | 22,457 |
| Call spread 23,500 / 23,800 | ₹1,700 | ₹17,800 | about 0.15 | 23,526 |
| Iron condor | ₹4,514 | ₹14,986 | — | 22,431 and 23,569 |

*Last traded prices at about 10:15 am on 15 October 2026; Nifty at 22,906.55. Deltas estimated from NSE's implied volatilities.*

The condor risks about 3.3 rupees to make 1. That is normal for a range trade: it wins most of the time and loses more when it loses. Bid–ask spreads near the money were 0.2–0.5% of each premium. Crossing them on four legs, in and out, costs under one point of the 69-point credit. Brokerage and STT come on top, on every leg.

Sizing: a ₹10 lakh account risking 2% (₹20,000) can sell one condor.

### Example 2 — covered call and cash-secured put on Reliance (snapshot)

Reliance traded at ₹1,200.8 at the snapshot, 26% below its January high. Suppose an investor would hold it for the long run, and would also be happy to buy more nearer ₹1,140.

```payoff
title: Covered call on Reliance: own 500 shares, sell the 1,260 call (23 Nov 2026 expiry)
underlying: 1200.8
lot: 500
range: 1050 1350
leg: buy stock @ 1200.8
leg: sell call 1260 @ 20
caption: Real premium from the snapshot. The call pays ₹10,000 on 500 shares (1.7% for 39 days). Above ₹1,260 the gain is capped at ₹39,600. Below, the shares lose almost as much as without the call: the premium only lowers the breakeven to ₹1,180.80.
```

```payoff
title: Cash-secured put on Reliance: sell the 1,140 put (23 Nov 2026 expiry)
underlying: 1200.8
lot: 500
range: 1000 1300
leg: sell put 1140 @ 14.05
caption: Real premium from the snapshot. The seller collects ₹7,025 and must buy 500 shares at ₹1,140 (₹5.7 lakh) if Reliance ends below that. The effective purchase price is ₹1,125.95, about 6% below the market.
```

Two facts from the chain matter here. The November strikes were thinly traded: the 1,140 put's bid was ₹13.55, below its last price. And these are stock options, settled by delivery. Keep the full cash for the shares even though the margin required is smaller.

### Example 3 — a quiet month: a put spread in July 2026 (estimated premiums)

On 1 July 2026 the Nifty closed at 24,006 with India VIX at 13.2. Take a put spread 5% and 8% below the market. It sells the 22,800 put and buys the 22,100 put. For about 30 days, its credit is estimated at 23 points.

| Step | Value |
|---|---|
| Entry, 1 July 2026 | Nifty 24,006; credit about 23 points (₹1,497 at today's lot of 65) |
| Maximum loss | 677 points (₹44,000 a lot) |
| Lowest close in the month | 23,767 on 24 July |
| Close on 29 July | 24,250 — both puts expire worthless |
| Result | Credit kept: about ₹1,500 a lot |

This is the usual outcome. It risked ₹44,000 to earn ₹1,500, and the price never came near the short strike.

### Example 4 — a month that went wrong: February–March 2026 (estimated premiums)

On 24 February 2026 the Nifty closed at 25,425 with India VIX at 14.2. A seller had two choices: sell the 24,150 put alone (5% below), or sell it with the 23,400 put bought as protection.

```series
title: The Nifty in February–March 2026: through both strikes
from: 2026-01-15
to: 2026-04-15
line: india:NIFTY50 | Nifty 50
line: india:INDIAVIX | India VIX | right
mark: 2026-02-24 | Put sold, Nifty 25,425
mark: 2026-03-23 | Low close 22,513
caption: The Nifty fell from 25,425 on 24 February to 22,513 on 23 March, 11% lower, while India VIX rose from 14 to the mid-20s. It closed at 23,306 on 25 March.
```

| Per lot of 65 (estimated) | Naked 24,150 put | 24,150 / 23,400 put spread |
|---|---|---|
| Premium received | ₹2,390 (36.8 points) | ₹2,054 (31.6 points) |
| Loss at the low close, 23 March | about ₹1.04 lakh | ₹46,693 (the maximum) |
| Loss at 25 March, near expiry | ₹52,440 | ₹46,693 |
| Loss as a multiple of the premium | about 22× | about 23× |

Held on, both lost about 22–23 times the premium. The spread's loss was capped; the naked put's loss at the low was more than twice as large.

The stop in section 3 would have changed the outcome. At the 2 March close (Nifty 24,866, India VIX 17.1) both positions were worth more than twice their credit. Closing there would have cost an estimated ₹4,800 a lot for the spread and ₹6,600 for the naked put. That is more than the planned loss of one credit, because the price jumped past the stop level between closes. It is still a small fraction of the loss from holding on.

---

## 7. Common mistakes

- **Sizing by margin.** Margin tells you what the broker needs, not what you can lose. A trader with ₹5 lakh may be able to sell several Nifty puts. A 10% fall would cost far more than the account.
- **Selling cheap premium.** Selling far out-of-the-money options for a few rupees risks the same crash for very little reward. The 22,000 put earned ₹2,083 a lot and would have lost about ₹88,000 on a 10% fall.
- **No stop, because "it usually comes back".** It usually does. The few times it doesn't decide the result.
- **Selling into events.** Results, policy decisions and Budgets come with rich premiums because the move is often large.
- **Rolling losers forever.** Each roll adds time and risk. A string of rolls turns a capped loss into an open one.
- **Treating many positions as diversified.** Short puts on the Nifty, Bank Nifty and five bank stocks all lose together in a sell-off.
- **Forgetting delivery.** A sold stock option that ends in the money becomes a share purchase or sale, with the cash or shares needed.
- **Holding to the last day.** The last day holds most of the gamma risk and little of the income.

---

## 8. What the evidence says

**The volatility risk premium is real.** Peter Carr and Liuren Wu (*Review of Financial Studies*, 2009) measured the gap between implied and realised variance across US indexes and stocks. On the S&P 500 it was large and persistent: sellers of variance were paid on average. Gurdip Bakshi and Nikunj Kapadia (2003) reached a similar conclusion with delta-hedged options.

**Benchmarks for covered calls and put selling.** Robert Whaley (*Journal of Derivatives*, 2002) studied the BXM buy-write index from 1988 to 2001. It earned a return close to the S&P 500's with about two-thirds of the volatility. Roni Israelov and Lars Nielsen (*Financial Analysts Journal*, 2015) showed that most of a covered call's risk is ordinary equity risk. The option-selling part adds a modest return, not a large one.

**Indian retail results.** SEBI's studies of individual F&O traders (January 2023, on FY22; September 2024, on FY22 to FY24) found that about 9 in 10 lost money. Selling options does not exempt anyone: short-option traders are part of those figures.

**An event study on the Nifty.** The first question: how often has implied volatility been above what followed? For each day from January 2010, compare India VIX with the Nifty's realised volatility over the next 21 sessions. Realised volatility is the annualised standard deviation of daily log returns.

| Measure, 2010–2026 (4,084 days) | Value |
|---|---|
| Days when India VIX was above the next month's realised volatility | 81% |
| Median gap, VIX minus realised | 3.4 points |
| Average India VIX | 17.7 |
| Average realised volatility over the next month | 14.8 |

The second question: what would selling monthly Nifty options have earned? The method: from January 2010 to August 2026, open a position every 21 sessions, 195 in all. Estimate 30-day premiums with Black-Scholes and India VIX, and value the position 21 sessions later.

| Monthly sale, 2010–2026 | Months profitable | Premium collected, total (% of index) | Net result, total (% of index) | Worst month |
|---|---|---|---|---|
| Put 5% below the market | 91% | 77% | +5.5% | −238× the premium (Feb–Mar 2020) |
| Put spread, 5% / 8% below | 91% | 48% | +13.4% | −2.9% of the index |
| Iron condor, 5% / 8% each side | 78% | — | +18.8% | −2.7% of the index |
| Call 5% above the market | 79% | — | — | −16× the premium |

*Nifty 50 and India VIX daily closes. Premiums are estimates, not traded prices. "Total" adds the monthly results as a percentage of the index level.*

**What it shows.** Implied volatility was above realised most of the time, so the seller had an edge. But the naked put kept less than a tenth of everything it collected; one month (from 20 February 2020) cost about 30% of the index. The defined-risk versions kept more, because their worst months were capped. Calls 5% above the market were breached more often than puts below, because the Nifty mostly rose.

**Caveats.** India VIX ignores the skew, so real put premiums were higher than modelled. Costs, bid–ask spreads, taxes and margin were not included; on small credits they take a large share. Lot sizes and margins changed over the period. And 16 years contain only one crash as sharp as March 2020. A strategy can look good for a decade and still be short a disaster.

**What is unknown.** Whether the premium will be as large in future. As more traders sell options, the premium may shrink. Nobody can say how large the next crash will be.

---

## 9. Building and testing it yourself

**Data you need.**

- Daily closes of the underlying, and daily implied volatility (India VIX for the Nifty; at-the-money implied volatility for stocks if available).
- Historical option prices, if you can get them. Without them, model premiums as section 8 did and add a skew: in the snapshot, puts 4–5% below the market had implied volatilities 2–4 points above the at-the-money level.
- Lot sizes, margin rules and expiry dates by date. All have changed several times.

**Look-ahead traps.**

- Using the day's close to choose strikes and filling at the same close.
- Using a volatility percentile that includes future days.
- Ignoring that a stop hit intraday fills at a worse price than the close.

**Survivorship and regime.** A test starting after 2020 misses the March 2020 crash; one starting in 2010 has one such crash. Test the strategy's worst months explicitly: what would March 2020, October 2008 or a 13% one-day fall have cost?

**Costs in India (approximate, October 2026; check current rates).** Brokerage is a flat fee per order, commonly about ₹20. STT is charged on the premium of options you sell (0.15% from April 2026), and at the same rate on the intrinsic value of index options exercised at expiry. Stock options settled by delivery pay 0.1% of the full contract value. Add exchange transaction charges, GST of 18% on brokerage and exchange fees, stamp duty on purchases, and the bid–ask spread. A four-legged condor pays these on every leg, twice.

**Tax.** F&O income in India is generally treated as non-speculative business income, taxed at your slab rate. Covered calls on shares you hold also create a capital-gains event when the shares are called away. Check with a tax adviser.

**What to test, without over-fitting.** Test the short delta, the days to expiry, the stop multiple and the profit target, one at a time. Look for a broad range of settings that work, not a single best one. Keep the last two or three years out of sample. See [backtesting](learn-test-backtesting.md).

**What a good test reports.**

- Win rate and average win and loss in rupees and as a share of the account.
- The worst month, and the worst three consecutive months.
- The return on the capital actually set aside: margin plus a buffer, not margin alone.
- Results split by India VIX level at entry.
- The skewness: how much of the total came from the few largest losses.

A sketch of the core logic:

```
every session t:
    if no open condor and vix_percentile(t) >= 40 and no event before expiry:
        expiry  = first expiry 20–45 days away
        short_p = put strike with delta nearest −0.20
        short_c = call strike with delta nearest 0.20
        width   = 1–2% of index
        credit  = (bid of shorts) − (ask of longs)
        if credit >= width / 4:
            lots = floor(account × 0.02 / ((width − credit) × lot_size))
            open condor at t+1
    for each open condor:
        if value_of_tested_side >= 2 × its credit: close that side
        elif profit >= 0.5 × credit: close
        elif days_to_expiry <= 6: close
```

---

## 10. Checklist

- [ ] Implied volatility is at or above its 40th percentile, and above recent realised volatility.
- [ ] No result, policy decision, Budget or election before expiry.
- [ ] The short strike is outside the straddle's expected move (delta 0.15–0.30).
- [ ] Every leg has a tight bid–ask spread and enough open interest.
- [ ] The credit is at least a quarter of the spread's width.
- [ ] Size: maximum loss (or a 10% stress loss for naked positions) is within the limit.
- [ ] Total maximum loss across all short-option positions is within 10–15% of the account.
- [ ] Stop (2 × credit or a close beyond the short strike), profit target (50%) and time exit are written down.
- [ ] For stock options: the cash or shares for delivery are available, or the exit date is set two sessions before expiry.
- [ ] For a covered call or cash-secured put: you are content to sell or buy the shares at the strike.

---

## Further reading

- Lawrence G. McMillan, *Options as a Strategic Investment* — covered writing, put selling and spreads in detail.
- Sheldon Natenberg, *Option Volatility and Pricing* — volatility, and why selling it is a business with tail risk.
- Euan Sinclair, *Volatility Trading* and *Positional Option Trading* — how the volatility risk premium is earned and lost.
- Antti Ilmanen, *Expected Returns* — the volatility risk premium among other sources of return.
- Peter Carr and Liuren Wu, "Variance Risk Premiums", *Review of Financial Studies*, 2009.
- Robert E. Whaley, "Return and Risk of CBOE Buy Write Monthly Index", *Journal of Derivatives*, 2002.
- Roni Israelov and Lars N. Nielsen, "Covered Calls Uncovered", *Financial Analysts Journal*, 2015.
- SEBI, studies of profit and loss of individual traders in equity F&O (January 2023 and September 2024).
- Related guides: [directional options](learn-fno-directional.md), [hedging with options](learn-fno-hedging.md), [position sizing](learn-risk-sizing.md), [portfolio risk](learn-risk-portfolio.md), [market volatility](learn-health-volatility.md), [the economic calendar](learn-macro-calendar.md).
