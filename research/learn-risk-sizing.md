# Position sizing — how many shares, decided by the stop

**In short**

- Decide first how much you are willing to lose if the stop is hit: a fixed fraction of the account, usually 0.5–1%.
- Then shares = risk amount ÷ (entry − stop). A tighter stop means more shares, not more risk.
- Cap any one position, for example at 25% of the account. The cap is your insurance against a gap through the stop.
- Drawdowns grow with the fraction you risk. Bet too much and even a winning method can lose money.
- The Kelly formula gives a ceiling, not a target. Practitioners risk a quarter to a half of it, or less.

This is the second of four risk guides. Read [expectancy](learn-risk-expectancy.md) first; then [stops and exits](learn-risk-stops-exits.md) and [portfolio risk](learn-risk-portfolio.md).

---

## 1. Fixed-fractional risk — decide the loss first

A trader with a $50,000 account sees a breakout at $100. How many shares? The professional answer starts somewhere else: how much am I willing to lose if the stop is hit?

Set that loss as a fixed fraction of the account, typically **0.5% to 1%** and rarely above 2%. At 1%, this trader risks $500. The share count then follows from the stop.

Why a fraction rather than a fixed sum? Three reasons:

- **Losses shrink as the account shrinks.** A losing streak wears the account down gradually rather than emptying it.
- **Gains compound.** As the account grows, so does the amount risked.
- **Every trade carries the same weight.** That is what turns expectancy in R ([expectancy](learn-risk-expectancy.md)) into money.

## 2. The formula

**US, $50,000 account, $500 risk.** Buy at $100.

| Stop | Risk per share | Shares | Position | Share of account | Loss if stopped |
|---|---|---|---|---|---|
| $92 (8% below) | $8 | 62 | $6,200 | 12% | $496 |
| $95 (5% below) | $5 | 100 | $10,000 | 20% | $500 |
| $96 (4% below) | $4 | 125 | $12,500 | 25% | $500 |

**India, ₹20,00,000 account, ₹20,000 risk.** Buy at ₹1,500.

| Stop | Risk per share | Shares | Position | Share of account | Loss if stopped |
|---|---|---|---|---|---|
| ₹1,380 (8% below) | ₹120 | 166 | ₹2,49,000 | 12% | ₹19,920 |
| ₹1,410 (6% below) | ₹90 | 222 | ₹3,33,000 | 17% | ₹19,980 |
| ₹1,440 (4% below) | ₹60 | 333 | ₹4,99,500 | 25% | ₹19,980 |

The rule behind both tables:

> **Shares = risk amount ÷ (entry − stop)**, rounded down.
> Risk amount = account × risk %.

The key line: **a tighter stop means more shares, not more risk.** The loss if stopped is the same in every row; only the position grows.

Two things do change with a tight stop. First, ordinary day-to-day price wiggles are more likely to hit it. Second, as §4 shows, a gap through it does more damage.

## 3. A complete sizing rule

A full rule has four steps:

1. **Risk amount** = account × risk %. Many traders cut the risk in a nervous market, for example to 0.5% when the VIX is above 25 ([the volatility guide](learn-health-volatility.md)).
2. **Shares** = risk amount ÷ (entry − stop), rounded down to a whole share.
3. **The cap.** No position may be worth more than a set share of the account, for example 25%. If the formula asks for more, buy only up to the cap. The amount actually at risk is then smaller than planned.
4. **Too large for the account.** If the result is less than one share, skip the trade. It happens when the share price is above the cap, or when the risk per share is larger than the whole risk amount.

### When the cap binds

At 1% risk and a 25% cap, the arithmetic is simple. **The cap binds whenever the stop is less than 4% below the entry.** That 4% is simply the risk divided by the cap. At 0.5% risk it binds only when the stop is less than 2% below. So a trade with a 3% stop ends up risking 0.75%, not the planned 1%.

How often is a stop that tight? Take stops placed 2 × ATR(14) below the entry on the illustrative 55-day breakouts from the [expectancy guide](learn-risk-expectancy.md):

| Illustrative breakouts, 2010–2025 | US | India |
|---|---|---|
| Trades | 60,470 | 17,592 |
| Median stop distance | 4.6% | 6.8% |
| Stop distance, 10th to 90th percentile | 2.9% to 8.7% | 4.5% to 9.7% |
| Stop under 4% (the 25% cap binds at 1% risk) | 36% | 5% |

US stocks in that sample moved less per day than Indian ones, so their volatility stops were tighter. More than a third of the US trades would have hit the cap.

A second limit binds too: **cash**. Ten positions of up to 25% each can need 250% of the account. Without margin, you buy what the cash allows, which means less than the planned risk, never more. So the risk you actually carry is usually below the nominal 1%.

Re-measure the account regularly. If you size from today's equity, the 1% follows the account down in a losing stretch and up in a good one.

## 4. Why the cap matters: gaps

```series
title: Autodesk (ADSK), late 2017 — a tight stop, a full-size position, a gap
from: 2017-10-01
to: 2018-01-31
tf: D
line: us:ADSK | Autodesk (ADSK)
mark: 2017-11-28 | a buyer near $131, stop $126.90
mark: 2017-11-29 | opened at $114.03 after results
caption: A 3.1% stop on a $50,000 account at 1% risk asks for a 32% position; a 25% cap trims it to 95 shares. The close went from $129.95 to $109.34 overnight. Filled at the open, the trade lost about 4.1R: 3.2% of the account.
```

Suppose a trader bought Autodesk near $131 on 28 November 2017, with a stop at $126.90. The risk per share was $4.10. A $500 risk then asks for 121 shares. That is about 32% of a $50,000 account.

A 25% cap trims that to 95 shares. Results came out that evening, and the stock opened at $114.03. The sale at the open lost about $1,610, or 3.2% of the account. Without the cap, the loss would have been about 4.1%.

The formula assumes the stop fills at the stop price. When a stock gaps below the stop, the sale fills at the open. Then **the loss grows with the position, not with the planned risk**. A tight stop gives a big position, and a big position is what a gap punishes.

The cap is therefore **gap insurance**. Even a stock that opens 80% lower ([expectancy](learn-risk-expectancy.md) §3) cannot take more than a fifth of the account if the position was capped at 25%. When holding through results, size for a possible gap, not for the stop ([the calendar guide](learn-macro-calendar.md)).

## 5. Volatility-based (ATR) stops and sizing

A calm stock moves 1.5% on a typical day; a wild one moves 5%. Put both stops 2 ATRs below the entry, and the calm stock's stop is 3% away while the wild stock's is 10%. With the same 1% risk, you buy about three times as many shares of the calm stock.

That is volatility-based sizing. The stop sits a fixed number of **average true ranges** below the entry, where ATR(14) is the stock's typical daily range over the last 14 days. A stop a couple of ATRs away sits outside the stock's normal day-to-day movement. Fixed-fractional sizing then gives every position the same risk measured in units of volatility.

This is the "N" sizing used by the Turtles, a well-known group of trend-following traders trained by Richard Dennis in the 1980s. Their N was a 20-day average true range. They placed the stop 2N from the entry.

A related exit is the **chandelier stop**: the highest close since entry, minus about 3 ATRs, raised as the price rises and never lowered. It is an exit rule, not a sizing rule ([stops and exits](learn-risk-stops-exits.md)).

A good structural stop, placed under a real chart level, is usually 1–3 ATRs away. When the chart level and the ATR distance disagree, the honest choice is the wider stop with fewer shares.

Some traders also cap the stop in percent, such as "never more than 8%". In practice that mostly rejects volatile stocks, because sizing already buys fewer shares as the stop widens. A cap in ATRs says more about whether the setup itself is loose.

## 6. Why not fixed shares or fixed amounts

- **Fixed share count** ("always 100 shares"): ignores both price and stop, so the risk is random.
- **Fixed amount** ("always $10,000"): better, but the risk still scales with the stop. In the illustrative US breakouts, the 2-ATR stop ranged from 2.9% to 8.7% below entry (10th to 90th percentile). At a flat $10,000, that is $290 to $870 of risk: a threefold range. The wide-stop trades would dominate the result.
- **"Conviction" sizing** (betting more on the trades you feel best about): those trades are rarely measurably better. Let conviction decide whether to trade, and the stop decide how much.

## 7. The arithmetic of losses

Losses and gains are not symmetric:

| Loss | Gain needed to recover |
|---|---|
| 10% | 11% |
| 20% | 25% |
| 30% | 43% |
| 50% | 100% |
| 75% | 300% |

A losing streak compounds against the fraction risked:

| Risk per trade | After 10 losses | After 20 losses | After 30 losses |
|---|---|---|---|
| 0.5% | −4.9% | −9.5% | −14.0% |
| 1% | −9.6% | −18.2% | −26.0% |
| 2% | −18.3% | −33.2% | −45.5% |
| 5% | −40.1% | −64.2% | −78.5% |

Every illustrative breakout portfolio in the [expectancy guide](learn-risk-expectancy.md) §4 had a losing streak of at least 21 trades. The longest was 38. At 1% that is survivable. At 5% it is the end of the account.

### Drawdowns simulated

To see the whole range of outcomes, we simulated two methods. Each sequence had 500 trades, about ten years for an active trader. Each trade risked a fixed fraction of the current account, and we recorded the deepest fall from a peak (the maximum drawdown):

> **Simulation.** 10,000 sequences per method. Method A, a trend follower: wins 35% of the time; a win is drawn from an exponential distribution averaging 3R; a loss is −1R. Expectancy +0.40R. Method B, a thin edge: wins 40% of the time; wins average 1.6R; losses −1R. Expectancy +0.04R. Trades are independent, one at a time.

| Risk per trade | A (+0.40R): median / 1 in 10 / 1 in 100 | B (+0.04R): median / 1 in 10 / 1 in 100 | B: chance of ending below the start |
|---|---|---|---|
| 0.5% | −10% / −15% / −20% | −15% / −24% / −33% | 32% |
| 1% | −20% / −28% / −37% | −29% / −44% / −56% | 35% |
| 2% | −36% / −49% / −62% | −51% / −70% / −82% | 42% |
| 5% | −70% / −84% / −93% | −87% / −97% / −99% | 62% |

What it shows:

- **Drawdown roughly doubles with the risk fraction**, while the expectancy in R does not change at all.
- **Over-betting turns a winner into a loser.** At 5% a trade, method B's median path ends at 0.60 times the starting account, despite its positive expectancy. Big losses take away more than big wins add.
- **Even a large edge hurts at 5%.** Method A still grew, but its median path fell 70% from a peak along the way. Few people keep following a method through that.
- **This is the gentle case.** The simulation takes one trade at a time. Real portfolios hold several positions that fall together, the subject of [portfolio risk](learn-risk-portfolio.md).

## 8. Kelly — the ceiling, not the target

For method A, the Kelly formula says to risk about 13% of the account per trade. Nobody sensible does. Here is why.

The Kelly criterion gives the fraction of the account to risk that maximises long-run growth. For a simple win/lose bet, **Kelly % = W − (1 − W) ÷ payoff ratio**. W is the win rate; the payoff ratio is the average win divided by the average loss.

| Simulated method | Win rate | Payoff ratio | Simple Kelly | Kelly on the full spread of results |
|---|---|---|---|---|
| A, trend follower | 35% | 3.0 | 13.3% | 9.1% |
| B, thin edge | 40% | 1.6 | 2.6% | 1.6% |

The last column finds the growth-maximising fraction from the whole simulated spread of R, not just its averages. It is lower, because the average win hides how uneven the wins are.

Why traders stay well below it:

- **The inputs are estimates.** A thin edge is often within measurement error of zero ([expectancy](learn-risk-expectancy.md) §5). So is its true Kelly fraction. Betting the estimated Kelly on a zero edge is pure loss.
- **Full Kelly hurts.** In the simulation, risking method A's 9.1% gave a median drawdown of 91%. Half Kelly kept about 78% of the growth rate, with a median drawdown of 66%. Practitioners use a quarter to a half of Kelly, often less (Thorp, 2006).
- **The simple formula overstates methods that depend on rare big wins.** For method A it gave 13.3%, against 9.1% on the full spread.

For a thin edge like method B, a 1% risk is already more than half of Kelly. It is not conservative at all.

## 9. Adding to winners, and cutting size after losers

**Pyramiding** means adding to a position as it moves in your favour. O'Neil buys at the pivot and adds in small steps only as the stock rises, not more than about 5% above the buy point. Minervini starts with a smaller position and adds once the stock proves itself, so only stocks that are working get full size.

Pyramiding raises your average cost, and many breakouts fail soon after the add. Each add should have its own stop, and the total risk of the position should stay within your limit. Whether it helps depends on the method: test it on your own trades before you rely on it.

**Scaling down after losses** works the other way. Minervini calls it "progressive exposure": trade small while your recent record is poor, and at full size once it pays. We simulated a simple version. Risk 0.5% instead of 1% while the last ten trades together are flat or losing:

> **Simulation.** Method A from §7 (expectancy +0.40R), 500 trades, 10,000 sequences. "Independent": every trade has a 35% win rate. "Clustered": the win rate is 45% in good markets and 25% in bad ones. Each trade has a 3% chance of the market switching, so a market state lasts about 33 trades on average.

| Sequence | Sizing | Median max drawdown | 1 in 10 at least | Median ending account |
|---|---|---|---|---|
| Independent | Always 1% | −20% | −28% | 6.2× |
| Independent | Half size after losses | −15% | −22% | 4.4× |
| Clustered | Always 1% | −25% | −37% | 6.2× |
| Clustered | Half size after losses | −19% | −28% | 4.9× |

Cutting size after losses made every drawdown shallower. It also cost growth, because a positive-edge method then trades small for long stretches. The cost was smaller when results really clustered, as they do in real markets ([expectancy](learn-risk-expectancy.md) §4). It is a choice of a smoother path at some price in return.

## 10. India specifics

- **No lot sizes in the cash market.** Lot sizes (fixed minimum trade quantities) apply to futures and options. Delivery equity trades in single shares, so the formula works unchanged.
- **Costs are larger than in the US.** For delivery trades they include STT of 0.1% on both the buy and the sell, stamp duty on the buy, exchange and SEBI charges, GST on brokerage and exchange fees, and a depository charge per sale. That is roughly 0.2%–0.25% for a round trip (a buy plus a sell) at a zero-brokerage broker, before slippage. Check your broker's current schedule.
- **Costs grow in R as the stop tightens**: 0.25% is 0.06R on a 4% stop, but 0.03R on an 8% stop.
- **Price bands.** Many NSE stocks have daily circuit limits of 5%, 10% or 20%: the price may not move further than that in a day. A stock locked at its lower limit cannot be sold at all that day. That is gap risk under another name, and another reason for the position cap.
- **Tax** on short-term capital gains on listed equity (20% since the July 2024 Budget) lowers every result for a taxable account.

## 11. What the trader does

1. **Fix the risk per trade** — 0.5%–1%; halve it in high volatility or a market below its 200-day ([the trend guide](learn-health-trend.md)).
2. **Place the stop where the idea is wrong**, then compute shares from it. Never move the stop to get a bigger position.
3. **Apply a position cap** (25% is common) and accept the lower risk when it binds; with results ahead, size for the gap.
4. **Re-measure the account monthly**, so the 1% follows the equity down and up.
5. **Cut size during a losing streak**, and restore it after the record recovers.
6. **Check the total.** Add up the risk of all open positions; [portfolio risk](learn-risk-portfolio.md) covers the limit.

## 12. What the evidence says

- **Robust:** the loss-recovery arithmetic is exact. Drawdown scales with risk per trade, and over-betting destroys a positive edge (the simulation in §7).
- **Robust:** Kelly maximises growth only when the odds are known. With estimated odds, betting a fraction of Kelly is standard practice (Thorp).
- **Practitioner advice, not proof:** pyramiding and progressive exposure come from O'Neil's and Minervini's books. The simulation in §9 shows the trade-off of cutting size after losses; it does not show that any particular rule improves a real method.
- **Limits:** the simulations assume a shape for the results and take one trade at a time, so they understate real drawdowns. The illustrative breakouts come from today's listed companies, without costs.

## 13. Checklist

- [ ] Risk % for the week set (1%, or 0.5% in high volatility / weak market)
- [ ] Every entry: shares = risk ÷ (entry − stop), rounded down
- [ ] Position under the cap (e.g. 25%); actual risk noted when the cap binds
- [ ] Results inside the holding period? Size for the gap or skip
- [ ] After a losing streak: size reduced until the last 10 trades are net positive

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — position sizing.
- Ralph Vince, *The Mathematics of Money Management* — fixed-fractional sizing, optimal f and drawdowns.
- Edward O. Thorp, "The Kelly Criterion in Blackjack, Sports Betting and the Stock Market" (2006).
- Curtis Faith, *Way of the Turtle* — N (ATR) based stops and unit sizing.
- William O'Neil, *How to Make Money in Stocks*; Mark Minervini, *Trade Like a Stock Market Wizard* — pyramiding and progressive exposure.
