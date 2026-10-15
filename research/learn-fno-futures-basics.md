# Futures basics — lots, margin, daily settlement and expiry

**In short**

- A futures contract fixes today the price at which you will buy or sell on a set date. It trades in **lots**, so even one contract controls several lakh rupees.
- You do not pay that value. You deposit **margin**, a fraction of it, and the exchange settles your profit or loss in cash at the end of every day.
- Small moves in the index become large moves in your account. In nine sessions of March 2026, one long Nifty lot lost about ₹1.1 lakh.
- Index futures settle in cash at expiry. Stock futures settle by delivery of real shares, so a position left open at expiry becomes a share trade.
- To keep a position beyond expiry you **roll** it: close this month's contract and open next month's, at a small cost.

## 1. One trade, start to finish

At 10:15 on 15 October 2026, Reliance shares traded at ₹1,200.4. The Reliance futures contract expiring on 27 October traded at ₹1,204.3. A trader who expects Reliance to rise over the next week buys one lot.

One lot of Reliance is 500 shares. So the trader has agreed to buy 500 shares at ₹1,204.3 on the expiry date. That is a contract worth about ₹6.02 lakh. No shares change hands today, and the trader does not pay ₹6.02 lakh. The broker blocks a margin deposit instead.

Suppose Reliance futures close at ₹1,230 three days later. The contract has gained ₹25.7 per share, which is ₹12,850 on the lot. That amount is credited to the trader's account the same evening, before the trade is closed. If the trader sells the lot at ₹1,230, the trade is over and the margin is released.

The same trade can be done the other way round. A trader who expects Reliance to fall can sell one lot first, without owning any shares, and buy it back later. This is the usual way to hold a **short position** for more than one day in India, because short sales of shares in the cash market must be closed the same day.

```payoff
title: Long one lot of Reliance futures (27 Oct 2026 expiry)
underlying: 1200.4
lot: 500
range: 1100 1310
leg: buy future @ 1204.3
caption: Each ₹1 move in Reliance is worth ₹500 per lot. There is no floor under the loss.
```

```payoff
title: Short one lot of Reliance futures (27 Oct 2026 expiry)
underlying: 1200.4
lot: 500
range: 1100 1310
leg: sell future @ 1204.3
caption: The mirror image: the short gains when Reliance falls and loses, without a cap, when it rises.
```

## 2. Lots and contract value

The **contract value** is the futures price times the lot size. It is the real size of your position, whatever margin you deposit. The table shows some contracts from the same morning.

| Contract (27 Oct 2026) | Futures price | Lot size | Contract value |
|---|---|---|---|
| Nifty 50 | 22,940 | 65 | ₹14.9 lakh |
| Nifty Bank (at the index level) | 55,720 | 30 | ₹16.7 lakh |
| Reliance | 1,204.3 | 500 | ₹6.0 lakh |
| State Bank of India | 957.45 | 750 | ₹7.2 lakh |
| Tata Consultancy Services | 2,371.8 | 225 | ₹5.3 lakh |
| HDFC Bank | 721.15 | 650 | ₹4.7 lakh |
| BHEL | 445.5 | 2,625 | ₹11.7 lakh |

*Prices at about 10:15 on 15 October 2026, during trading. Lot sizes are NSE's for October 2026. The Bank Nifty row uses the index level, not a futures price.*

Two things follow. First, you cannot buy half a lot, so the smallest position is large. Among the 20 most active stock futures that morning, one lot was worth between about ₹4.5 lakh and ₹11.7 lakh.

Second, lot sizes are fixed for a while and then revised. SEBI set a minimum of about ₹15 lakh for index contracts from late 2024. The Nifty lot of 65 was worth a little under that on this morning, because the index had fallen since the lot was set. Stock contracts are smaller, as the table shows.

## 3. Margin — the deposit, not the price

When you open a futures position the broker blocks **initial margin** in your account. It has two parts, both set by the exchange's clearing corporation:

- **SPAN margin** — the exchange's estimate of the worst loss the position could suffer in one day, from a set of price and volatility scenarios. SPAN is the name of the risk system that calculates it.
- **Exposure margin** — an extra buffer on top, a fixed share of the contract value.

The total changes every day with the market's volatility. For Nifty futures it has usually been somewhere around a tenth of the contract value, sometimes more. Stock futures need more, and volatile stocks much more. Your broker's margin calculator gives the exact figure on the day.

Take an illustrative margin of 12% on the Nifty lot above. The deposit is about ₹1.8 lakh against ₹14.9 lakh of exposure. That is leverage of about eight times: a 1% move in the Nifty is about an 8% gain or loss on the deposit.

| Nifty move | Gain or loss per lot (at 22,940) | As a share of a ₹1.8 lakh margin |
|---|---|---|
| 1% | ₹14,900 | 8% |
| 2% | ₹29,800 | 17% |
| 5% | ₹74,600 | 42% |
| 10% | ₹1,49,100 | 83% |

Margin can be posted as cash or as pledged shares and other approved securities, after a haircut (a cut to their value). Exchange rules require that at least half of the margin be cash or cash-like collateral. Margin must be in place before the order is placed; brokers can no longer collect it later in the day.

**Leverage is a choice, not a fixed number.** The exchange sets the minimum deposit. You decide how much capital stands behind the position. A trader who keeps the full contract value in the account, with the margin as only part of it, has no leverage at all.

## 4. Daily settlement — losses are paid every evening

Futures are **marked to market**: every evening the exchange sets a settlement price for each contract, and the day's gain or loss moves between accounts in cash. You do not wait until you close the trade to pay a loss.

The table follows one long Nifty lot bought on 2 March 2026 at the close, as the index started a sharp fall. Index closes stand in for futures settlement prices, which differ by a small amount.

| Date | Nifty close | Change (points) | Day's cash flow (1 lot of 65) | Running total | Share of a 12% margin |
|---|---|---|---|---|---|
| 2 Mar 2026 | 24,865.7 | — | bought | — | — |
| 4 Mar | 24,480.5 | −385.2 | −₹25,038 | −₹25,038 | −13% |
| 5 Mar | 24,765.9 | +285.4 | +₹18,551 | −₹6,487 | −3% |
| 6 Mar | 24,450.4 | −315.5 | −₹20,504 | −₹26,991 | −14% |
| 9 Mar | 24,028.1 | −422.4 | −₹27,456 | −₹54,447 | −28% |
| 10 Mar | 24,261.6 | +233.6 | +₹15,181 | −₹39,266 | −20% |
| 11 Mar | 23,866.9 | −394.8 | −₹25,659 | −₹64,925 | −33% |
| 12 Mar | 23,639.2 | −227.7 | −₹14,800 | −₹79,726 | −41% |
| 13 Mar | 23,151.1 | −488.1 | −₹31,723 | −₹1,11,449 | −57% |

*Margin assumed at 12% of ₹16.2 lakh, about ₹1.94 lakh. Markets were closed on 3 March.*

```series
title: Nifty 50, February–April 2026
from: 2026-02-01
to: 2026-04-30
tf: D
line: india:NIFTY50 | Nifty 50
band: 2026-03-02 2026-03-13 | The nine sessions in the table
caption: The index fell about 7% in nine sessions. A long futures lot lost more than half of a 12% margin deposit over the same days.
```

The Nifty fell about 7% in those sessions. The futures trader lost 57% of the deposit. That is leverage at work, and nothing about the move was unusual for a falling market.

If the account balance falls below the required margin, the broker asks for more money — a **margin call**. If it does not arrive in time, the broker closes the position at the market price. Brokers often close positions during the day when losses grow fast, without waiting for the evening.

## 5. Big days and gaps — how often the market jumps

A stop order caps a loss only if the price trades through it. A **gap** — an opening price far from the previous close — can skip past it. With leverage, gaps decide how bad a bad day gets.

| Nifty 50, January 2010 to 1 October 2026 | Number of sessions | Share of all sessions |
|---|---|---|
| Close-to-close move larger than 2% | 207 | 5.0% |
| Close-to-close move larger than 3% | 54 | 1.3% |
| Close-to-close move larger than 5% | 11 | 0.3% |
| Opening gap larger than 2% | 61 | 1.5% |
| Opening gap larger than 3% | 21 | 0.5% |

Big days cluster in time. In 2020 there were 42 sessions with a move larger than 2%. In 2017 there were none. The largest falls in the sample were in March 2020, when the Nifty fell 13% on 23 March. Other single-day shocks include 4 June 2024, the general-election result (−5.9%), and the 5% gap down on 7 April 2025.

Single stocks jump far more often than the index. Across about 200 stocks with futures today, measured from 2015, a typical stock had about ten days a year with a move larger than 5%. It had about one day a year with a move larger than 10%, and nearly one opening gap down of more than 5% a year.

*Method note: daily open and close prices of the Nifty 50 (2010 to 1 October 2026) and of today's stock futures list (2015 to October 2026). A gap is the open against the previous close. Using today's list leaves out companies that failed or were dropped, so the true frequency of large falls was probably higher.*

## 6. Expiry and settlement

Every futures contract has an expiry date. NSE's monthly contracts expire on the last Tuesday of the month, moved earlier when that day is a holiday. On 15 October 2026 three Nifty futures were listed: 27 October, 23 November and 29 December.

**Index futures settle in cash.** At expiry the final settlement price is the index's closing value. Your last day's gain or loss is paid, and the contract ceases to exist. Nobody delivers the 50 shares of the index.

**Stock futures settle by physical delivery.** A long Reliance futures lot still open at expiry becomes a purchase of 500 Reliance shares at the settlement price. You must pay about ₹6 lakh in full and receive the shares. A short lot open at expiry obliges you to deliver 500 shares you may not own. Brokers usually raise margins in the days before expiry for this reason, or close such positions themselves.

The practical rule for a trader: close or roll stock futures before the expiry week unless you intend to take or give delivery.

## 7. Rollover — keeping a position beyond expiry

To hold a futures position for longer than one month, you **roll** it. You close the near-month contract and open the same position in the next month. Most traders roll in the last few days before expiry.

On the morning of 15 October 2026 the November Nifty future was 100.1 points above the October one. A long trader rolling one lot would sell October at 22,940 and buy November at 23,040.1. The roll costs those 100.1 points, about ₹6,500 per lot. That gap reflects interest for the extra month, as the next guide explains.

Trading concentrates in the nearest contract. That morning the October contract held about 85% of open Nifty futures positions and 84% of the volume. The far contracts are thinner, so they usually cost more to trade.

## 8. In the US

The main US equity index futures trade on CME. The E-mini S&P 500 is worth $50 times the index, and the Micro E-mini $5 times. They trade almost 24 hours a day on weekdays, expire quarterly (March, June, September, December), and settle in cash. Margin is set by the exchange and the broker in dollars per contract.

Single-stock futures are not a practical product in the US. A US trader who wants to be short a stock for days borrows the shares and sells them in the cash market, which Indian cash markets do not allow beyond the same day.

## 9. What can go wrong

- **Forgetting the contract value.** A ₹1.8 lakh margin feels like a ₹1.8 lakh position. It is a ₹15 lakh position.
- **Using all your capital as margin.** A normal adverse move then triggers a margin call, and the broker closes the trade at the worst moment.
- **A gap past the stop.** Overnight news can open the market beyond your stop. Size for the gap, not only for the stop.
- **Delivery by accident.** A stock future held into expiry becomes a share purchase or sale of several lakh rupees.
- **Rolling without counting.** Each roll costs the spread between months plus trading costs. Over a year it adds up.
- **Trading far months.** Thin contracts have wider spreads; the price you see may not be the price you get.

## 10. Checklist

- [ ] I know the lot size and the contract value, and I size by contract value.
- [ ] I have worked out what a 2%, 5% and 10% adverse move costs per lot.
- [ ] Margin uses a small part of my capital; the rest is a buffer for adverse days.
- [ ] I know the expiry date and whether the contract settles in cash or by delivery.
- [ ] I will close or roll stock futures before the expiry week.
- [ ] I know what a roll costs today, in points and in rupees.
- [ ] I have a plan for a margin call that does not involve hoping.

Further steps: [Futures basis and open interest](learn-fno-futures-basis.md) explains why futures trade above the index; [Trading and hedging with futures](learn-fno-futures-trading.md) turns these mechanics into trades. The [map of this section](learn-fno-overview.md) lists the rest. For the full cost of a round trip, see [India's rules, costs and tax](learn-fno-india-rules.md). For sizing in general, see [Position sizing](learn-risk-sizing.md) and [Stops and exits](learn-risk-stops-exits.md).

## Further reading

- John C. Hull, *Options, Futures, and Other Derivatives* — chapters on futures markets, margin and settlement.
- NSE, contract specifications for index and stock futures, and NSE Clearing's notes on SPAN margin.
- SEBI circular of 1 October 2024 on measures to strengthen the equity index derivatives framework.
- CME Group, contract specifications for E-mini and Micro E-mini S&P 500 futures.
