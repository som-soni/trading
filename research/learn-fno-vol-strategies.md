# Volatility strategies — straddles, strangles, butterflies, calendars and ratio spreads

**In short**

- An option's price is mostly a bet on *how far* the underlying will move, not which way. Volatility strategies trade that bet on its own.
- Buy a straddle or strangle when you expect a bigger move than the options price in. Sell one when you expect a smaller move.
- Implied volatility has usually been higher than the volatility that followed. Since 2010, India VIX was above Nifty's next-month realised volatility on about 4 days in 5. Sellers earn that gap and give much of it back in crashes.
- Butterflies, calendars and ratio spreads shape the same bet, with a capped loss or a different time profile.
- Size every short-volatility trade by what it loses in a gap, never by the margin the broker asks for.

## 1. The idea

### A straddle on Nifty, 15 October 2026

At 10:15 on 15 October 2026, Nifty stood at 22,906.55. The 22,900 call expiring on 27 October last traded at 240. The 22,900 put on the same expiry traded at 214. Buying both is a **long straddle**: two options with the same strike (the agreed price) and the same expiry date.

```payoff
title: Long straddle on Nifty, 22,900 strike, 27 Oct 2026 expiry
underlying: 22906.55
lot: 65
range: 21900 23900
leg: buy call 22900 @ 240
leg: buy put 22900 @ 214
before: 6d 13.6%
caption: Prices at 10:15 on 15 October 2026 (intraday; they moved during the day). The straddle costs 454 points, or ₹29,510 for one lot of 65. At expiry it makes money only if Nifty finishes more than 454 points away from 22,900. The blue line is its value six days before expiry if implied volatility stays at 13.6%: time alone eats into it.
```

The straddle costs 454 points. One Nifty lot is 65 units, so that is ₹29,510. At expiry the buyer profits only if Nifty ends below 22,446 or above 23,354. That is a move of about 2% either way, in eight trading sessions.

So the straddle's price *is* the market's estimate of the coming move. A handy rule of thumb links the two:

> At-the-money straddle ≈ 0.8 × underlying price × implied volatility × √(days to expiry ÷ 365)

With an implied volatility of 13.6% and 12 days to go, that gives about 452 points. The market paid 454. **Implied volatility** is the volatility that, put into a pricing model, gives today's option price. The guide on [option pricing and the Greeks](learn-fno-pricing-greeks.md) explains the model itself.

### Who is on the other side

The straddle buyer is betting that Nifty will move more than 2%. The seller is betting it will move less, and collects the 454 points for taking the risk. Neither cares about direction.

Most of the time sellers have been paid for that risk. Many buyers of options are not trading volatility at all. Fund managers buy index puts to insure portfolios, and they pay for insurance whatever it costs. Speculators buy cheap out-of-the-money options as lottery tickets. That steady demand keeps option prices a little above what the later moves justify.

The seller's reward is not free money. It is payment for carrying crash risk: a small, regular income and an occasional large loss. Researchers call the gap the **volatility risk premium**: the difference between implied volatility and the realised volatility that follows.

### Implied against realised volatility in India

```series
title: India VIX — the market's 30-day implied volatility for Nifty
from: 2010-01-01
to: 2026-10-14
tf: M
line: india:INDIAVIX | India VIX
line: india:NIFTY50 | NIFTY 50 | right log
mark: 2020-03-24 | COVID crash: 83.6
mark: 2024-06-04 | election results
caption: India VIX spikes in sell-offs and drifts lower in calm markets. Its all-time high close was 83.61 on 24 March 2020; its low was 9.15 on 26 December 2025. On 14 October 2026 it closed at 14.62.
```

**Realised volatility** is how much the index actually moved. Here it is the standard deviation of daily log returns over a window, multiplied by √252 to make it annual. The table compares India VIX each day with Nifty's realised volatility over the next 21 sessions.

| Year | Average India VIX | Average realised volatility over the next 21 sessions | Days VIX was higher |
|---|---|---|---|
| 2012 | 19.7 | 14.6 | 96% |
| 2017 | 12.6 | 8.9 | 99% |
| 2020 | 26.9 | 25.1 | 77% |
| 2023 | 12.4 | 9.6 | 95% |
| 2024 | 14.6 | 13.3 | 68% |
| 2025 | 13.4 | 10.8 | 87% |
| 2010 – Sep 2026, all days | median 16.4 | median 13.4 | 81% |

*Method: Nifty 50 daily closes and India VIX closes, 4 January 2010 to 11 September 2026 (4,084 days with a full forward window). Realised volatility uses log returns over the following 21 sessions. The windows overlap, so the days are not independent.*

On the median day, India VIX was about 3.4 points above the realised volatility that followed. But the worst days were enormous. In late February and early March 2020, realised volatility over the next month came in more than 60 points above VIX. A seller who earned three points a month for years gave it all back in weeks.

### The toolkit: five shapes of the same bet

Each structure below uses real 27 October Nifty premiums from the same snapshot. Read them as one family.

**Short strangle.** Sell an out-of-the-money put and an out-of-the-money call. You collect less than a straddle, but the price must move further before you lose.

```payoff
title: Short strangle on Nifty — sell 22,500 put and 23,300 call, 27 Oct 2026
underlying: 22906.55
lot: 65
range: 21800 24000
leg: sell put 22500 @ 90.35
leg: sell call 23300 @ 79.9
before: 6d 13.6%
caption: Credit 170.25 points, or ₹11,066 per lot. Breakevens at expiry are about 22,330 and 23,470. Beyond them the loss keeps growing; nothing caps it.
```

**Long butterfly.** Buy one call below, sell two at the middle strike, buy one above. It is a cheap bet that the price ends near the middle strike.

```payoff
title: Long call butterfly on Nifty — 22,700 / 22,900 / 23,100, 27 Oct 2026
underlying: 22906.55
lot: 65
range: 22400 23400
leg: buy call 22700 @ 365.35
leg: sell 2x call 22900 @ 240
leg: buy call 23100 @ 144.1
before: 6d 13.6%
caption: Debit 29.45 points (₹1,914 per lot), which is also the most it can lose. Maximum profit is 170.55 points (₹11,086) if Nifty settles exactly at 22,900. It is a short-volatility trade with a floor under the loss.
```

**Ratio spread.** Buy one option and sell two further out. Here: buy the 23,000 call, sell two 23,300 calls.

```payoff
title: Call ratio spread on Nifty — buy 1 × 23,000 call, sell 2 × 23,300 call, 27 Oct 2026
underlying: 22906.55
lot: 65
range: 22500 24000
leg: buy call 23000 @ 187.9
leg: sell 2x call 23300 @ 79.9
caption: Debit 28.1 points. Best case is Nifty at 23,300 at expiry: 271.9 points, or ₹17,674 per lot. Above about 23,572 the extra short call loses without limit. It pays for a moderate rise and punishes a sharp one.
```

**Calendar spread.** Sell a near expiry and buy a later one at the same strike. Here both legs are 22,900 calls:

| Leg | Expiry | Price (points) |
|---|---|---|
| Sell call | 19 October | 146.6 |
| Buy call | 27 October | 240 |
| Net debit | | 93.4 |

The two legs expire on different days, so the payoff is not a fixed line. The table values the position at the 19 October expiry with a pricing model. The later call then has 8 days left.

| Nifty at 19 Oct expiry | Value if 27 Oct IV is 10% | If IV is 12.2% (as now) | If IV is 13.6% |
|---|---|---|---|
| 22,300 | −₹5,671 | −₹5,080 | −₹4,569 |
| 22,600 | −₹3,416 | −₹1,933 | −₹923 |
| 22,800 | +₹678 | +₹2,575 | +₹3,788 |
| 22,900 | +₹3,814 | +₹5,740 | +₹6,966 |
| 23,000 | +₹1,206 | +₹3,025 | +₹4,203 |
| 23,200 | −₹2,017 | −₹698 | +₹231 |
| 23,500 | −₹3,666 | −₹3,174 | −₹2,725 |

*Profit or loss per lot of 65, Black-Scholes value of the 27 October call with an interest rate of 6.5%. The most you can lose is the debit, ₹6,071 per lot.*

A calendar profits when the price stays near the strike, like a butterfly. Unlike a butterfly, it also gains if implied volatility *rises*, because the long option has more time left and more vega (sensitivity to implied volatility). It is the one structure here that is short realised volatility and long implied volatility at once.

## 2. When it works and when it doesn't

**Long volatility** (buying straddles and strangles) works when the move is bigger than the price paid. That happens when implied volatility is low compared with what follows: at the start of a sell-off, after a long quiet spell ends, or before a shock nobody scheduled. It fails in calm markets, because time decay — **theta**, the daily loss of an option's time value — eats the premium every day.

**Short volatility** (selling straddles, strangles and iron flies) works when implied volatility is high compared with what follows. The best times have been just after a spike has started to fade, and in range-bound markets. It fails in trending crashes and overnight gaps, when realised volatility jumps far above implied.

Volatility has a few habits that both sides should know:

- **It clusters.** A volatile week tends to be followed by another. Realised volatility over the last 10 sessions is a better guide to the next 10 than any long average.
- **It mean-reverts.** India VIX spikes have always faded, usually within weeks. A low VIX can stay low for months.
- **It rises when prices fall.** Index volatility jumps in sell-offs, not in rallies. A short strangle loses faster on the put side.
- **Scheduled events inflate it.** Implied volatility rises before results, the Budget or an election, and drops right after. The guide [on event trades](learn-fno-event-trades.md) covers that case.

### India

- **Which contracts.** On NSE, only Nifty has weekly options; Bank Nifty, Fin Nifty and Midcap Select have monthly ones. Stock options are monthly.
- **Liquidity.** Nifty options near the money are among the most liquid in the world. In the snapshot, the bid–ask on the 22,900 call was 0.75 points on 240. Stock options thin out fast away from the money.
- **Physical settlement.** Stock options that end in the money become delivery of shares. Close stock option positions before expiry unless you want the shares.
- **Costs.** STT is charged on the premium when you sell an option. An index option exercised in the money at expiry pays STT on its intrinsic value instead, at the same rate. A stock option settles by delivery, with delivery STT of 0.1% on the full contract value, so close in-the-money stock options before expiry.
- **Margin.** The buyer pays the full premium upfront. The seller of a naked option posts margin of more than ₹1 lakh per Nifty lot, and more on expiry day. Buying wings (far options) cuts the margin sharply.
- **Swing shorts.** A trader who wants to be short a stock for days cannot do it in the cash market in India. Puts, put spreads and futures are the way.

### In the US

Index options on the S&P 500 expire every weekday, so "zero days to expiry" (0DTE) options are traded heavily. US stock options are American style: they can be exercised any day, so a short call can be assigned early, typically the day before a dividend. Prices move in increments of a cent or five cents, and there is no STT.

## 3. The rules

These rules give two playbooks. **Playbook S** sells volatility with defined risk when implied volatility is rich. **Playbook L** buys it when implied volatility is cheap. Every condition can be tested on daily data.

### Universe and filters

1. The underlying is Nifty, Bank Nifty, or a stock with listed options.
2. The at-the-money option's bid–ask spread is at most **2%** of its mid price.
3. Open interest at each strike you trade is at least **1,000 contracts** (index) or **500 contracts** (stock).
4. No scheduled binary event falls before expiry: company results, the Budget, election results. Event trades follow their own rules.

### Setup

Measure three things at the close:

- **IV**: the average of the at-the-money call and put implied volatility for your expiry. For Nifty, India VIX is a fair stand-in.
- **RV10** and **RV20**: Nifty's realised volatility over the last 10 and 20 sessions, annualised.
- **IV rank**: where today's IV sits in its range over the last 252 sessions (0 = lowest, 100 = highest).

**Playbook S (sell):**

1. IV is at least **2 points** above RV10.
2. IV rank is at least **40**.
3. The spike is fading: India VIX has closed below its 10-day high for **3** sessions in a row.

**Playbook L (buy):**

1. IV is at least **1 point** below RV10, or IV rank is at most **15**.
2. RV10 is higher than RV20. Realised volatility is waking up, not falling asleep.

### Entry

- **Expiry.** Playbook S: **20–35** calendar days to expiry (a monthly). Playbook L: **10–30** days.
- **Strikes for S.** Sell the strikes nearest to one expected move away: price × IV × √(days ÷ 365). Buy wings **1.5–2** expected moves away, so the loss is capped (an iron condor or iron fly).
- **Strikes for L.** Buy the at-the-money straddle, or a strangle with strikes about **0.5** expected moves away.
- **Order.** Use a limit order at the mid price. Step it toward the worse side by one tick at a time, at most **3** ticks. Do not use market orders on options.
- **Timing.** Enter after the first **30 minutes** of the session, when spreads have settled.

### Initial stop

- **Playbook S:** close everything if the position's loss reaches **1.5–2×** the credit received, or if the underlying closes beyond a short strike.
- **Playbook L:** the premium paid is the maximum loss. Add a time stop: exit when **half** of the days to expiry have passed with less than half the expected move.

### Exits

- **S, target:** buy back when **50%** of the credit has been earned.
- **S, time:** close **2** sessions before expiry, whatever the profit. The last days carry the most gamma risk — gamma is how fast an option's delta (its sensitivity to the underlying) changes.
- **L, target:** sell when the position is worth **1.5–2×** what you paid, or when IV rank goes above **80**.
- **Both, invalidation:** a new scheduled event appears before expiry (a policy meeting is called, a results date is set). Close or re-plan.

### Position size

- **Defined-risk trades:** the maximum loss (wing width minus credit, times the lot) is at most **1–2%** of the account.
- **Undefined-risk trades** (naked strangles, ratio spreads): stress-test a gap of **6%** in the index overnight. The loss in that gap must be at most **5%** of the account.

A worked number: the short strangle above (22,500 put and 23,300 call) collected 170.25 points. A 6% fall from 22,906 takes Nifty to about 21,532. The put is then worth about 968 points, so the loss is about 798 points, or ₹51,870 per lot. To keep that within 5% of the account, each lot needs an account of about ₹10.4 lakh.

### Managing the trade

- Check the **delta** of the whole position once a day. Delta is how much the position gains or loses for a one-point move in the underlying. If it exceeds a quarter of one lot's exposure, roll the untested side closer or close the trade.
- Never add to a losing short-volatility trade. Averaging into a move is how small accounts are wiped out.
- Do not adjust on expiry day. Close instead.
- Track margin daily. A gap can raise the margin required at the same moment the position loses money.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Spread filter | ≤ 2% of mid | Tradability | Wider spreads eat most of the edge in short-dated options |
| Minimum open interest | 1,000 (index) / 500 (stock) contracts | Exit liquidity | Check the strike you will exit, not just at-the-money |
| IV − RV10 to sell | ≥ 2 points (1–4) | How rich IV must be | Higher = fewer trades, larger cushion |
| IV − RV10 to buy | ≤ −1 point | How cheap IV must be | Rare in indices; more common in stocks |
| IV rank to sell / buy | ≥ 40 / ≤ 15 | Context within the year | Window of 252 sessions; 126 reacts faster |
| Spike-fading check | VIX below 10-day high for 3 sessions | Avoid selling into a rising spike | The most important filter for sellers |
| Days to expiry | 20–35 (sell), 10–30 (buy) | Time decay and gamma | Weekly selling has the worst gap risk for its premium |
| Short strike distance | 1 expected move (0.8–1.2) | Probability of finishing out of the money | One expected move ≈ 16-delta option |
| Wing distance | 1.5–2 expected moves | Maximum loss and margin | Closer wings: less credit, smaller loss |
| Seller stop | 1.5–2× credit | Cuts the tail | Tighter stops are hit by noise |
| Seller profit target | 50% of credit | Time in the trade | Higher targets add gamma risk for little gain |
| Seller time exit | 2 sessions before expiry | Expiry-week risk | |
| Buyer target | 1.5–2× debit, or IV rank > 80 | Locking in the move | |
| Buyer time stop | Half the days gone, under half the move | Theta drain | |
| Risk per defined-risk trade | 1–2% of account | Survival | |
| Stress gap / stress loss | 6% gap, ≤ 5% of account | Undefined-risk sizing | June 2024 saw a 5.9% one-day fall |

## 5. Variations

- **Delta-neutral trading (Sheldon Natenberg).** Professional market makers buy or sell options and hedge the direction away with futures. They profit if realised volatility differs from the implied volatility they traded. It needs frequent re-hedging, and costs matter.
- **Forecast first (Euan Sinclair).** Sinclair's books treat the edge as the gap between implied volatility and *your* forecast of realised volatility. He argues for small positions, many independent trades, and a written forecasting rule.
- **Mechanical premium selling.** A widely followed retail approach sells strangles or iron condors about 45 days out when IV rank is high, and closes at half the credit. It is popular because it wins often. Its results depend heavily on how it handles the rare large loss.
- **Cross-section of stocks (Goyal and Saretto).** Rank stocks by the gap between their historical and implied volatility. Buy straddles where implied is low against history; sell where it is high.
- **Expiry-day selling in India.** Many Indian traders sell weekly Nifty options on expiry morning to collect the last day's decay. SEBI's 2024–25 rules raised expiry-day margins because of this. The premium is small and a single trending day can erase months.

## 6. Worked examples

The examples below apply Playbook S. Option prices for past dates are not stored. For those, premiums are **estimates**: a Black-Scholes value using India VIX as the implied volatility and today's lot of 65. Real out-of-the-money puts usually trade at a higher implied volatility than VIX and calls at a lower one, so treat the rupee figures as rough.

### Example 1 — 15 October 2026: the rules say "no trade"

```series
title: Nifty and India VIX, July–October 2026
from: 2026-07-01
to: 2026-10-14
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
caption: Nifty fell from its 3 August high into October. India VIX dropped to 10.35 on 23 September, then rose to about 15. On 14 October, VIX (14.62) and Nifty's 20-day realised volatility (about 14.8) were almost equal.
```

1. **Setup check, 14 October close.** India VIX was 14.62. RV10 was about 17.1 and RV20 about 14.8.
2. **Playbook S, rule 1** needs IV at least 2 points above RV10. IV was about 2.5 points *below* it. Fail.
3. **Playbook L, rule 1** needs IV at least 1 point below RV10. It passes. **Rule 2** needs RV10 above RV20: 17.1 against 14.8. It passes too.
4. **Entry check.** The next morning's chain put the 27 October at-the-money IV near 13.6%. The straddle cost 454 points (about 2%).
5. **Decision.** The setup favours buying, but only just. A cautious trader buys a small long straddle, or nothing. A seller has no edge here.

### Example 2 — June 2024: a strangle sold into an event (failure)

```series
title: Nifty and India VIX around the 2024 election results
from: 2024-05-01
to: 2024-06-28
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
mark: 2024-06-03 | strangle sold
mark: 2024-06-04 | results
mark: 2024-06-06 | expiry
caption: India VIX was about 24 in the last week of May. Nifty rose to 23,264 on 3 June after exit polls, fell 5.9% to 21,885 on results day, and was back at 22,821 by the 6 June weekly expiry.
```

1. **The tempting signal.** On 31 May, India VIX was 24.6 and RV10 was about 11. That is a gap of more than 13 points. Rules 1 and 2 of Playbook S passed easily.
2. **The filter that should have stopped it.** Election results were due on 4 June, before the weekly expiry. The universe rule excludes scheduled binary events. The gap was not an edge; it was the price of the event.
3. **The trade, if taken.** On 3 June, Nifty closed at 23,263.90. A trader sells the 22,800 put and the 23,700 call for the 6 June expiry. Estimated credit: about 71 points, or ₹4,643 per lot.
4. **What happened.** On 4 June, Nifty closed at 21,884.50 and VIX at 26.75. The strangle was worth about 911 points. The loss was about ₹54,500 per lot, roughly 12 times the credit.
5. **The stop.** A stop at 2× the credit would have closed it on 4 June near that loss. Gaps jump over stops.

The ending is a lesson too. On 6 June, Nifty closed at 22,821 and both options would have expired worthless. Only a trader who could carry a ₹54,500 mark-to-market loss per lot, plus higher margin, would have seen that. Most could not.

### Example 3 — April 2026: selling after the spike faded (success)

```series
title: Nifty and India VIX, March–May 2026
from: 2026-03-01
to: 2026-05-29
tf: D
line: india:NIFTY50 | NIFTY 50
line: india:INDIAVIX | India VIX | right
mark: 2026-03-30 | VIX peak 27.89
mark: 2026-04-23 | setup passes
mark: 2026-05-04 | 50% target hit
caption: India VIX peaked at 27.89 on 30 March 2026. By 23 April it had fallen to 18.59 while Nifty traded around 24,000.
```

1. **Setup, 23 April 2026.** India VIX was 18.59. RV10 was about 15.0, so IV was about 3.6 points above it. VIX had not closed at a new 10-day high since 30 March. IV rank over the past year was about 50. All three conditions passed.
2. **Entry.** Nifty closed at 24,173.05. One expected move over 30 days was about 1,288 points. The trader sells the 22,900 put and the 25,450 call. Estimated credit: about 224 points, or ₹14,570 per lot. For a defined-risk version, add wings 1.5 expected moves out.
3. **The path.** Nifty dipped to 23,897.95 the next day. The position showed a small loss. It never came close to the stop.
4. **Exit.** On 4 May 2026, Nifty closed at 24,119.30. The strangle's estimated value was about 100 points, below half the credit. The 50% target closed it for about ₹8,100 per lot.
5. **After the exit.** On 12 May, Nifty fell to 23,379.55 and VIX rose to 19.28. Leaving the trade on would have given back most of the gain for a while.

## 7. Common mistakes

- **Selling because premiums "look high" before an event.** High implied volatility before results or an election is fair pay for the jump, not a gift.
- **Sizing by margin.** Margin tells you what the broker needs today. It says nothing about the loss in a 6% gap.
- **Holding short options into the last day for the final rupees.** Gamma is highest then. One move can turn a full profit into a loss.
- **Buying straddles in quiet markets "because something must happen".** Theta charges you every day that nothing does.
- **Reading the exchange's IV column at face value.** NSE's published IVs for the call and the put at the same strike can differ a lot. At 22,900 on 27 October they were 12.2% and 15.0%. The gap mostly comes from how the figure is computed, so average the two, or use the out-of-the-money option at each strike.
- **Ignoring the skew.** Out-of-the-money index puts carry higher implied volatility than calls. A "neutral" strangle collects more on the put side because the market fears falls more.
- **Letting stock options expire in the money in India.** They settle by delivery of shares, and both sides pay delivery STT of 0.1% on the full contract value.

## 8. What the evidence says

- **The volatility risk premium is real.** Carr and Wu (2009) found that implied variance has exceeded realised variance on average for the S&P 500 and most large US stocks. Bakshi and Kapadia (2003) found that delta-hedged long option positions lose money on average. Both point the same way: option sellers have been paid.
- **Long at-the-money index straddles have lost on average.** Coval and Shumway (2001) reported average losses of roughly 3% *per week* on market-neutral S&P 500 straddles. That is the buyer's cost of insurance.
- **The premium comes with crash risk.** The gains for sellers are small and frequent; the losses are rare and large. Our India data shows the same shape: about 3.4 points of median premium, and months like March 2020 when realised volatility beat implied by more than 60 points.
- **Cross-sectional signals exist.** Goyal and Saretto (2009) found that US stock straddles where implied volatility was well below historical volatility outperformed those where it was well above.
- **Retail results in India are poor.** SEBI's January 2023 study (on FY22) and its September 2024 study (on FY22 to FY24) found that about 9 in 10 individual F&O traders lost money. Costs, leverage and sizing explain much of that.

What is unknown: how big the premium will be in future, and whether India's high retail option selling has changed it. Weekly Nifty options are recent; the rule changes of 2024–25 changed expiry patterns again. Treat any long history with care.

*Event study method: India VIX against the realised volatility of the Nifty 50 over the next 21 sessions, from closes stored from 2010 to October 2026. This compares an index of 30-day implied volatility with realised volatility, not the returns of any options strategy.*

## 9. Building and testing it yourself

**Data.** You need daily option prices by strike and expiry (bhavcopies from the exchange), with bid and ask if you can get them. Index prices and India VIX are not enough to test strike-level trades. If you only have VIX, test the *signal* (did IV exceed later RV?), not the trade.

**Traps.**

- **Look-ahead.** The close you use for the signal is the close you cannot trade at. Enter at the next session's prices.
- **Last-traded prices.** Illiquid strikes show stale last prices. Use the mid of bid and ask, or skip strikes with no trades that day.
- **Expiry calendar.** Expiry weekdays and lot sizes in India changed several times between 2019 and 2026. Rebuild the calendar for each date; do not assume today's.
- **Survivorship.** Stock option lists change. Use the list of stocks that had options *on each date*.

**Costs (approximate, as of 2026).** Per order, a discount broker charges about ₹20. STT applies to option premium on the sell side. Exchange charges, GST on charges and stamp duty add a little more. The bigger cost is the spread: half the bid–ask on every leg, in and out. For a four-leg iron condor that is eight half-spreads.

| Option (snapshot, 15 Oct 2026) | Last price | Bid–ask width | Width as % of price |
|---|---|---|---|
| Nifty 22,900 call, 27 Oct | 240 | 0.75 | 0.3% |
| Nifty 23,500 call, 27 Oct | 41.25 | 0.15 | 0.4% |
| Bank Nifty 56,000 call, 23 Nov | 1,132 | 6.90 | 0.6% |
| Reliance 1,200 call, 27 Oct | 23.25 | 0.10 | 0.4% |
| Reliance 1,230 call, 23 Nov | 29.30 | 0.30 | 1.0% |

**Parameters to test.** Test a few values of each parameter in §4, not every combination. Keep the strike rule in units of expected moves, so the same rule works when volatility changes. Hold out the last few years and look at them once, at the end.

**What a good test reports.** The number of trades, win rate, average win and average loss, and the **worst single trade** and worst month. Report how much margin was needed at the worst moment. A short-volatility test that shows no big loss has not seen enough history.

```
for each session t:
    iv   = atm_iv(expiry nearest 30 days, t)
    rv10 = stdev(log returns, last 10) * sqrt(252)
    if no_event_before(expiry) and iv - rv10 >= 2 and iv_rank(iv, 252) >= 40 \
       and vix(t) < max(vix, last 10) for 3 sessions:
        em    = price(t) * iv * sqrt(days_to_expiry / 365)
        sell  put at price - em, call at price + em      # at next session's mid
        buy   put at price - 1.5*em, call at price + 1.5*em
        size  so that (wing width - credit) * lot <= 1% of equity
    manage: close at 50% of credit, at a loss of 2x credit, or 2 sessions before expiry
```

## 10. Checklist

- [ ] Is a scheduled event (results, Budget, policy, election) due before expiry? If yes, use the event-trade rules instead.
- [ ] What are IV, RV10, RV20 and IV rank today? Write them down.
- [ ] Which playbook passes, if any? Is the edge at least 2 points?
- [ ] Is VIX still rising? Never sell into a rising spike.
- [ ] Are the bid–ask spread and open interest acceptable at every strike, including the exit?
- [ ] What is the maximum loss, or the loss in a 6% gap? Is it within limits?
- [ ] Can I carry that loss and a higher margin without being forced to close?
- [ ] Where is the profit target, the stop and the time exit?
- [ ] For stock options: will I close before expiry to avoid delivery?

## Further reading

- Sheldon Natenberg, *Option Volatility and Pricing* (2nd edition, 2015).
- Euan Sinclair, *Volatility Trading* (2nd edition, 2013) and *Positional Option Trading* (2020).
- Lawrence G. McMillan, *Options as a Strategic Investment* (5th edition, 2012).
- John C. Hull, *Options, Futures, and Other Derivatives*.
- Peter Carr and Liuren Wu, "Variance Risk Premiums", *Review of Financial Studies* (2009).
- Gurdip Bakshi and Nikunj Kapadia, "Delta-Hedged Gains and the Negative Market Volatility Risk Premium", *Review of Financial Studies* (2003).
- Joshua Coval and Tyler Shumway, "Expected Option Returns", *Journal of Finance* (2001).
- Amit Goyal and Alessio Saretto, "Cross-Section of Option Returns and Volatility", *Journal of Financial Economics* (2009).
- SEBI, studies on the profit and loss of individual traders in equity F&O (January 2023 and September 2024).
- Related guides: [implied and realised volatility](learn-fno-volatility.md), [income strategies](learn-fno-income.md), [India's F&O rules and costs](learn-fno-india-rules.md), [volatility and sentiment](learn-health-volatility.md), [position sizing](learn-risk-sizing.md), [expectancy](learn-risk-expectancy.md), [backtesting](learn-test-backtesting.md).
