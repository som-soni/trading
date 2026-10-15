# Risk and position sizing in F&O — size by what you can lose

**In short**
- Size an F&O position by the most it can lose, never by the margin it needs. Margin tells you what the broker will allow, not what you can afford.
- One Nifty future is a ₹15 lakh position. A 1% move in the index is about ₹15,000 per lot.
- Stops do not protect against gaps. The Nifty opened more than 2% away from the previous close on about 1 day in 70 since 2010; single stocks gap far more.
- A position with a capped loss (a bought option, a spread) can be sized exactly. A short option has no cap, so size it by a stress test.
- Most F&O accounts that blow up do it the same way: too many lots, short options with no protection, and one large move.

Option prices here come from one real snapshot of NSE's chains at about 10:15 on 15 October 2026, when the Nifty stood at 22,906.55. Prices moved during the day. Model values and assumptions are labelled. Charges, margins and settlement rules are in [Indian F&O rules](learn-fno-india-rules.md).

## 1. Notional versus margin

A trader with ₹10 lakh buys one lot of Nifty futures at 22,940. The lot is 65 units, so the position is worth ₹14.9 lakh. The broker asks for a margin of perhaps ₹1.5 lakh, about a tenth of that.

The margin is not the risk. Every point the Nifty moves is ₹65 of profit or loss. A 1% move is about 230 points, or about ₹14,900. On ₹10 lakh of capital, that one lot moves the account by about 1.5% for each 1% move in the index.

| Index move | Points (from 22,940) | Profit or loss per lot | As % of ₹10 lakh capital |
|---|---|---|---|
| 1% | 229 | ₹14,911 | 1.5% |
| 2% | 459 | ₹29,822 | 3.0% |
| 5.9% (4 June 2024) | 1,353 | ₹87,975 | 8.8% |
| 13% (23 March 2020) | 2,982 | ₹1,93,843 | 19.4% |

*One lot of Nifty futures (65 units) at 22,940. The last two rows are the Nifty's largest one-day falls in 2024 and 2020.*

Notional (the full contract value) is the right number for risk. Margin is the right number only for the question "will the broker let me do this?"

The leverage in the table is set by the number of lots, not by the margin. If the margin allowed five lots, five lots would turn the 2024 election-day fall into a loss of about 44% of the account in one session.

## 2. Size by the maximum loss

The rule is the same as for shares. Decide how much of your capital you will lose if the trade is wrong, then work out how many lots that allows.

```
lots = floor( risk budget / loss per lot if the trade is wrong )
loss per lot = (entry − exit at the stop or at the worst case) × lot size + costs
```

The difference in F&O is the "worst case". It depends on the instrument. Here is the same idea, a bullish view on the Nifty, sized four ways on a ₹10 lakh account that risks 1% (₹10,000) per trade.

| Position (27 Oct 2026 expiry) | Loss per lot if wrong | How the loss is set | Lots for ₹10,000 of risk |
|---|---|---|---|
| Long future at 22,940, stop 150 points lower | ₹9,750 plus costs | The stop, if it fills | 1 |
| Long 23,000 call at 188.35 | ₹12,243 | The premium | 0 (one lot risks 1.2%) |
| Bull call spread 23,000 / 23,500 | ₹9,532 | The net premium | 1 |
| Short 22,500 put at 90.35 | No fixed cap | A stress test (section 4) | See section 4 |

*Snapshot prices at about 10:15 on 15 October 2026. Lot of 65 units.*

The bought option and the spread are the easiest to size. The most they can lose is the premium paid. Nothing can make that loss larger, not a gap and not a halt.

```payoff
title: Bull call spread on the Nifty, 23,000 / 23,500, 27 Oct 2026 expiry
underlying: 22906.55
lot: 65
range: 22200 23900
leg: buy call 23000 @ 187.9
leg: sell call 23500 @ 41.25
before: 6d 12%
caption: The net cost is 146.65 points, or ₹9,532 per lot, and that is the most the position can lose. It makes money above 23,146.65 at expiry, up to ₹22,968 per lot above 23,500.
```

The future looks the same as the spread on paper: about ₹10,000 at risk. It is not the same. The future's loss is set by a stop order, and a stop only fills if the market trades through it. Section 3 shows why that matters.

The long call is the case people get wrong. One lot of a ₹188 option feels small. But it is ₹12,243, and it can go to zero. With a ₹10,000 budget, the honest answer is no trade, a cheaper strike, or a spread.

## 3. Gap risk — the stop is not the price you get

On the evening of 31 January 2024, the Reserve Bank of India restricted Paytm Payments Bank. Shares of its parent, One 97 Communications, then fell by the 20% daily price limit in each of the next two sessions. A stop placed 5% below the 31 January close did nothing.

```series
title: Paytm (One 97 Communications), January–February 2024
from: 2024-01-15
to: 2024-02-20
tf: D
line: india:PAYTM.NS | Paytm
line: india:PAYTM.NS@vol | Volume | pane2 bars
mark: 2024-02-01 | first 20% fall
caption: The close went from 761.20 on 31 January to 609 on 1 February and 487.20 on 2 February: two falls of 20% in a row.
```

A one-lot futures position in such a stock loses its whole stop budget and much more before the trader can act. Paytm was not a one-off. Adani Energy Solutions fell 20% on 21 November 2024, after US authorities charged members of the group's leadership. The index gaps too.

| Nifty, January 2010 to October 2026 | Share of sessions | About how often |
|---|---|---|
| Opened more than 1% from the previous close | 6.6% | About 16 times a year |
| More than 2% | 1.5% | About 4 times a year |
| More than 3% | 0.5% | About once a year |

*Event study: Nifty open against the previous close, 4,101 sessions from January 2010 to 1 October 2026. The largest gap was a fall of about 9% at the open on 23 March 2020.*

Single stocks gap far more often than the index. Among the stocks that have F&O contracts today, the record since 2015 looks like this.

| Today's F&O stocks, 2015 to October 2026 | Count | About how often per stock |
|---|---|---|
| Opened more than 5% from the previous close | 3,262 | 1.6 times a year |
| Opened more than 10% away | 254 | Once in about 8 years |
| Opened more than 10% lower | 168 | — |

*Event study: daily open against previous close for 213 of today's F&O stocks, about 503,000 stock-days. Today's list only, so stocks that left F&O or failed are missing (survivorship bias). A few of the largest gaps are data errors from demergers and similar corporate actions.*

About 4 in 10 of these stocks had at least one opening gap down of more than 10% in the period. For a stock futures position, plan on a gap through your stop sometime. Size so that a 10% gap against you is survivable, not just the stop distance.

## 4. Short options — size by a stress test

A short option has a limited gain (the premium) and a loss that grows with the move. Its loss is not fixed by a stop, because option prices jump with volatility as well as with the index.

Take a short strangle from the snapshot, for the 27 October expiry. The seller sells the 22,500 put at 90.35. The seller also sells the 23,300 call at 79.90. Together they bring in 170.25 points, about ₹11,066 per lot.

```payoff
title: Short strangle on the Nifty, 22,500 put / 23,300 call, 27 Oct 2026 expiry
underlying: 22906.55
lot: 65
range: 21500 24300
leg: sell put 22500 @ 90.35
leg: sell call 23300 @ 79.9
before: 6d 15%
caption: The most it can make is ₹11,066 per lot, if the Nifty ends between 22,500 and 23,300. Outside 22,329.75 and 23,470.25 it loses ₹65 for every point, with no limit.
```

The expiry picture hides the danger before expiry. If the index falls fast, implied volatility rises, and the options gain value from both effects. The next table re-prices the strangle the day after a fall, with 11 days left.

| Fall in the Nifty | Loss per lot at expiry | Loss per lot next day, implied volatility 15% | Next day, implied volatility 25% |
|---|---|---|---|
| 2% | Profit ₹7,713 | ₹5,907 | ₹22,020 |
| 3% | ₹7,176 | ₹13,562 | ₹27,367 |
| 5.9% (as on 4 June 2024) | ₹50,355 | ₹48,435 | ₹54,269 |
| 13% (as on 23 March 2020) | ₹1,56,068 | ₹1,53,206 | ₹1,53,263 |

*Model values (Black-Scholes, interest rate 6.5%) for the short 22,500 put and 23,300 call, from snapshot premiums. India VIX closed at 26.75 on 4 June 2024 and at 71.99 on 23 March 2020, so 25% is a mild assumption for a crisis day.*

Read across the 3% row. At expiry the loss is small. But the morning after a 3% fall, with volatility up, the position shows a loss of about 2.5 times the premium collected. That is the loss a margin call is based on.

The sizing rule follows. Pick a stress move you must survive, such as the largest one-day fall of the last ten years. Compute the loss per lot in that move, with volatility raised. Size so that the stress loss is a set share of capital, for example 5% to 10%.

For the strangle, a 5.9% fall costs about ₹54,000 per lot. Allowing 10% of a ₹10 lakh account for that scenario gives one lot. Sizing by margin might allow several. That gap between the two answers is how short-option accounts are wiped out.

## 5. Margin calls and forced closes

Futures and short options are marked to market every day. Losses are taken from your account in cash each evening. When the balance falls below the required margin, the broker asks for more money, often the same day.

Margins also rise when markets are volatile. The exchange's risk model raises SPAN margin when volatility rises. So a fall can raise your required margin at the same time as it takes cash from your account.

If you cannot add money, the broker closes positions. It does not wait for a good price. A forced close usually happens near the worst point of a move, which turns a temporary loss into a permanent one.

Keep spare cash in the account: a common rule is at least as much again as the margin in use. Never let margin use approach 100% of the account.

## 6. Liquidity — getting out costs more than getting in

In the snapshot, an at-the-money Nifty option had a bid–ask spread under 0.5% of its price. A far-away Nifty strike had a spread near 5%. A far Reliance strike was near 7%. In a fast market, spreads widen and the quantity at the best price shrinks.

So an exit costs more than the calm-market spread suggests. Prefer strikes near the money and the nearer monthly or weekly expiry ([Reading an option chain](learn-fno-option-chain.md) shows spreads by strike). Trade fewer lots in thin contracts. For a stop on an option, use a limit order with room, or decide in advance to close on a fixed index level.

## 7. Assignment and physical delivery

Stock futures and options in India settle by delivery. A short put that ends in the money means you buy the shares.

Suppose a trader sells one Reliance 1,180 put for 27 October at 11.65. One lot is 500 shares, so the trader collects ₹5,825. If Reliance closes at 1,150 on expiry day, the put is exercised. The trader must pay ₹5.9 lakh (1,180 per share) for shares then worth ₹5.75 lakh.

The cash must be in the account. Before expiry, the exchange raises the margin on in-the-money stock positions. Brokers often close them a day or two early if the cash is not there. Either way, the position needs more money near expiry than it did when it was opened.

Index options do not have this problem; they settle in cash. [Expiry](learn-fno-expiry.md) covers the last days in more detail.

## 8. How F&O accounts blow up

The same few patterns recur.

1. **Sizing by margin.** The account takes as many lots as the broker allows. One ordinary bad week wipes out months.
2. **Selling options with no protection.** Many small wins build confidence, then one large move takes them all back and more.
3. **Averaging down on a losing short option.** Selling more of the same option at a worse price, to "bring the average up".
4. **Buying cheap options every expiry.** Small total losses, many times a month, add up to more than the occasional win.
5. **No cash buffer.** A margin call at the wrong time forces a close at the bottom.
6. **Holding stock positions into expiry.** Delivery, or a forced close at a poor price.
7. **Ignoring costs.** Many small trades, each paying spread and charges.

Some well-known cases show the second pattern. In October 1997 the funds run by Victor Niederhoffer were wiped out after a sharp fall in US stocks; they had sold large numbers of S&P 500 put options. In November 2018 clients of OptionSellers.com, which sold natural-gas call options, lost more than their account balances when gas prices spiked. In February 2018 an exchange-traded note that profited from falling US volatility lost more than 90% of its value in one day.

Each of those positions had made money steadily before the loss. A long run of small gains is what short-option risk looks like before the large loss.

## 9. A sizing routine

Use the same steps for every F&O trade.

1. Write down what makes the trade wrong: an index level, a date, or a loss amount.
2. Work out the loss per lot at that point. For a bought option or a spread, it is the premium. For a future, it is the stop distance, then add a gap scenario. For a short option, run a stress test with volatility raised.
3. Divide your risk budget by that loss to get the number of lots. Round down.
4. Add up the worst-case loss of all open F&O positions together. Positions on the Nifty, Bank Nifty and large stocks often fall together.
5. Check the margin last. If the margin is more than you can comfortably hold with a cash buffer, trade fewer lots.

The portfolio risk guide covers the fourth step for share portfolios; the same arithmetic applies here ([Portfolio risk](learn-risk-portfolio.md)). Position sizing for shares, with the formula behind the first three steps, is in [Position sizing](learn-risk-sizing.md).

## 10. What can go wrong

- **Treating margin as the risk.** The risk is the contract value times the move.
- **Assuming the stop will fill.** Index and stocks gap. Plan for the gap, not only the stop.
- **Sizing a short option by its premium.** The premium is the most it can make, not the most it can lose.
- **Forgetting volatility.** In a fall, implied volatility rises and short options lose faster than the index moves.
- **Counting each position alone.** Several bullish positions on Indian large caps are one bet.
- **No cash buffer.** A margin call forces you out at the worst time.
- **Holding stock F&O into expiry by accident.** It becomes delivery.

## 11. What the evidence says

SEBI's studies are the most direct evidence on individual traders in Indian F&O. The January 2023 study found that about 89% of individual traders lost money in 2021–22. The September 2024 study found about 93% lost money over the three years to 2023–24. Losses include transaction costs.

The gap studies in section 3 are simple and have limits. The stock list is today's F&O list, so it misses stocks that were removed or collapsed. A few large gaps are data errors from corporate actions. Both points mean the true record of large gaps is probably somewhat worse, not better.

The option stress test uses a pricing model with a single implied volatility. Real markets add a skew (far puts rise more in a fall), wider spreads and margin increases. All three make real losses larger than the model's.

What is not known: the right stress size for your own account. It depends on how much loss you can bear without changing your plan or your life. The checklist below asks you to write it down.

## 12. Checklist

- What is the full contract value of the position, and what does a 1% move cost?
- What is the most it can lose? Is that loss capped by the structure, or only by a stop?
- If it is a future, what does a 3% gap through the stop cost? For a stock, what does 10% cost?
- If it is a short option, what is the loss after a large fall with volatility raised? Is that within your stress limit?
- How many lots does your risk budget allow? Is that fewer than the margin allows? It should be.
- How much spare cash will remain after the margin is blocked?
- For stock F&O: will you close before expiry, or are you ready for delivery?
- What is the total worst-case loss of all your open F&O positions together?

## Further reading

- SEBI, "Analysis of Profit and Loss of Individual Traders dealing in Equity F&O Segment" (January 2023; September 2024).
- Sheldon Natenberg, *Option Volatility and Pricing* (2nd edition, 2015) — risk management and position sizing for option traders.
- Euan Sinclair, *Positional Option Trading* (2020) — sizing option positions and the risks of short volatility.
- Nassim Nicholas Taleb, *Dynamic Hedging* (1997) — how option positions behave in large moves.
- Victor Niederhoffer, *The Education of a Speculator* (1997) — written by a trader before his own 1997 loss.
- Van K. Tharp, *Trade Your Way to Financial Freedom* — position sizing as the core of a trading plan.
