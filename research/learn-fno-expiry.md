# Expiry — what happens in an option's last days

**In short**
- An option loses its time value as expiry approaches, and the loss speeds up in the last few sessions.
- Close to expiry, a small move in the index makes a large change in an option's price. That is gamma, and it cuts both ways.
- In India, Nifty options expire every week (Tuesday) and every month (the last Tuesday). Bank Nifty, Fin Nifty and stock options expire monthly.
- Index options settle in cash at the index's closing value. Stock options and futures settle by delivery of the shares.
- SEBI's rules add margin for short options on expiry day and remove some margin offsets. Plan for them before the day, not on it.

All option prices here come from one real snapshot of NSE's chains at about 10:15 on 15 October 2026. Prices moved during the day. Model values are labelled as such.

## 1. Two expiries, one morning

On 15 October 2026 the Nifty stood at 22,906.55. Two Nifty expiries were trading side by side: a weekly one on 19 October and the monthly one on 27 October. Here is the same strike in both.

| Expiry | Sessions left (about) | 22,900 call | 22,900 put | Call + put | As % of the index |
|---|---|---|---|---|---|
| 19 Oct 2026 (weekly) | 3 | 146.60 | 127.25 | 273.85 | 1.2% |
| 27 Oct 2026 (monthly) | 8 | 240.00 | 214.00 | 454.00 | 2.0% |

*Last prices at about 10:15 on 15 October 2026. Sessions left counts 15 October as one. Tuesday 20 October was a market holiday, which is why the weekly expiry fell on a Monday.*

The later expiry has almost three times as many sessions left. Its at-the-money call and put cost only about 1.7 times as much. Option value grows with the square root of time, not with time itself. The square root of 8 divided by 3 is about 1.6, close to what the market paid.

The same rule works backwards. As expiry nears, the value left has to fall faster and faster to reach zero for an at-the-money option on the last day.

## 2. The Indian expiry calendar

The snapshot's own list of Nifty expiries shows how the calendar works.

| Kind | Dates in the snapshot (2026) | Rule |
|---|---|---|
| Weekly | 19 Oct, 3 Nov, 9 Nov, 17 Nov | Every Tuesday that is not a monthly expiry |
| Monthly | 27 Oct, 23 Nov, 29 Dec | The last Tuesday of the month |
| Longer-dated | March and June 2027, onwards to 2031 | Quarterly and half-yearly contracts |

*Nifty expiries listed in NSE's option chain on 15 October 2026.*

When the Tuesday is a market holiday, the expiry moves to the trading day before it. That is why 19 October, 9 November and 23 November are Mondays. Check the exchange's holiday list at the start of each month.

Since late 2024 SEBI allows each exchange only one index with weekly expiries. NSE's is the Nifty. BSE's is the Sensex, which expires on Thursdays. Bank Nifty, Fin Nifty and Midcap Select now have monthly expiries only. Stock futures and options have three monthly expiries open at a time.

NSE moved its expiry day from Thursday to Tuesday in September 2025. Older charts, articles and data before then use Thursday expiries.

## 3. Time decay speeds up

The daily loss of time value is called theta. A model makes the shape easy to see. The table holds the index, the strike and the volatility fixed and lets only time pass.

| Days to expiry | At-the-money call value | Lost over the next day | Lost per lot (65 units) |
|---|---|---|---|
| 30 | 404 | 8 | ₹512 |
| 20 | 320 | 9 | ₹596 |
| 10 | 217 | 12 | ₹793 |
| 5 | 149 | 17 | ₹1,090 |
| 3 | 114 | 22 | ₹1,419 |
| 2 | 92 | 28 | ₹1,808 |
| 1 | 64 | 64 | ₹4,174 |

*Model values (Black-Scholes): Nifty and strike 22,900, implied volatility 13%, interest rate 6.5%, calendar days. Real decay is uneven: weekends and holidays are partly priced in on the trading day before.*

Thirty days out, the option loses about 2% of its value a day. With two days left it loses about 30%. On the last day, everything that is left goes, unless the index moves.

The chart below shows the same idea on a real position. It is a short straddle: one 19 October call and one 19 October put, both at 22,900, sold at the snapshot's prices. The curved line is the position's model value two days before expiry. The straight lines are its value at expiry.

```payoff
title: Short straddle on the Nifty, 22,900 strike, 19 Oct 2026 expiry
underlying: 22906.55
lot: 65
range: 22300 23500
leg: sell call 22900 @ 146.6
leg: sell put 22900 @ 127.25
before: 2d 13%
caption: The seller collects 273.85 × 65, about ₹17,800. If the index sits still, time decay turns the curve into the tent by expiry. A move of more than 274 points either way is a loss.
```

That curve is why selling options close to expiry is popular. The tent is how it loses: the profit is capped, and the loss is not.

## 4. Gamma — small moves, large price changes

Delta is how much an option's price moves for a one-point move in the index. Gamma is how fast delta itself changes. Close to expiry, gamma near the strike becomes very large.

Take a call at 23,100, just out of the money. The table shows its model value at three index levels, with one day left and with twelve days left.

| Index level | Value, 1 day left | Value, 12 days left |
|---|---|---|
| 22,900 | 7.9 | 149.0 |
| 23,000 | 26.0 | 192.1 |
| 23,100 | 64.8 | 242.5 |

*Model values (Black-Scholes) for a Nifty 23,100 call: implied volatility 13%, interest rate 6.5%.*

With one day left, a 200-point rise (under 1%) multiplies the call's price about eight times. With twelve days left, the same rise adds about 60%. For a buyer, that is the lottery ticket that draws traders to expiry day. For a seller, it is the risk: a position that looked safe in the morning can lose many times its premium by the afternoon.

Here is the buyer's side of that trade with the snapshot's real price: one 19 October 23,100 call.

```payoff
title: Buying one Nifty 23,100 call, 19 Oct 2026 expiry
underlying: 22906.55
lot: 65
range: 22600 23600
leg: buy call 23100 @ 59.25
before: 2d 13%
caption: The call costs 59.25 × 65, about ₹3,850. It needs the Nifty above 23,159 at expiry to make money. If the index does not rise, most of the premium is gone within two sessions.
```

Most short-dated out-of-the-money calls bought this way expire worthless. Gamma explains both the occasional large win and the frequent total loss.

## 5. What happens at expiry

**Index options settle in cash.** They are European: they can only be exercised at expiry. The settlement price is the index's official closing value on expiry day. An in-the-money option pays its intrinsic value in cash. An out-of-the-money option expires worthless. You do not need to do anything.

**Stock options and futures settle by delivery.** An open stock future at expiry becomes a purchase or sale of the shares. An in-the-money stock option is exercised into a purchase or sale of the shares. Someone long one lot of an in-the-money Reliance call (500 shares) must pay for 500 shares at the strike. A short call seller must deliver them.

**Exercise has a tax cost.** STT on an option that is exercised is charged at a higher rate than STT on selling the same option in the market. For an in-the-money long option, selling it before the close is usually cheaper than letting it be exercised. [Indian F&O rules](learn-fno-india-rules.md) has the rates.

**Trading continues until the close.** Expiring options trade until 15:30 on expiry day. Their prices can move from a few rupees to hundreds in the last hour.

## 6. Pinning and expiry-day moves — what the Nifty data shows

Two beliefs about expiry day are common. One says the index is "pinned" to a big strike at the close. The other says expiry days are unusually volatile. A simple test on daily Nifty data checks both.

| Since March 2019 | Weekly expiry days | Other days |
|---|---|---|
| Number of days | 396 | 1,475 |
| Average size of the day's move (close to close) | 0.71% | 0.74% |
| Median size of the day's move | 0.51% | 0.53% |
| Average high–low range | 1.11% | 1.14% |
| Close within 10 points of a round hundred | 21.5% | 17.8% |

*Event study on daily Nifty data, 1 March 2019 to 1 October 2026. Expiry days are taken as the last session on or before Thursday each week until August 2025, and on or before Tuesday after. If closes landed at random, 20% would fall within 10 points of a round hundred.*

```series
title: Nifty and its daily change, with the weekly expiries marked (Sep–Oct 2026)
from: 2026-08-25
to: 2026-10-14
tf: D
line: india:NIFTY50 | Nifty
line: india:NIFTY50@chg1 | Daily change, % | pane2 bars zero
mark: 2026-09-01 | expiry
mark: 2026-09-08 | expiry
mark: 2026-09-15 | expiry
mark: 2026-09-22 | expiry
mark: 2026-09-29 | expiry
mark: 2026-10-06 | expiry
mark: 2026-10-13 | expiry
caption: Expiry Tuesdays look like other days. The largest rise in the window, 1.6% on 13 October, came on an expiry day; the largest fall, 1.6% on 8 October, did not.
```

The index did not move more on expiry days, measured from close to close. The pinning share was 21.5% against 20% for random closes. With 396 days, that difference is within normal sampling noise.

What the daily test cannot see is the path within the day. Option prices near the strike can swing hard in the last hour even if the index ends close to where it started. The test also uses approximate expiry dates (holiday shifts are ignored) and the index close, not settlement prices of single stocks.

## 7. India's expiry-day rules and margins

SEBI introduced measures in late 2024 and early 2025 that matter on and around expiry day. These are the ones a trader meets most often.

| Rule | What it means for you |
|---|---|
| Extra margin on short options expiring that day | Short index options expiring today need extra margin (an additional 2% of contract value) |
| No calendar-spread benefit on expiry day | A short expiring option is no longer offset against a long option in a later expiry. Margin rises |
| One weekly index per exchange | Only Nifty (NSE) and Sensex (BSE) have weekly options |
| Option premium collected upfront | A buyer must have the full premium in the account before buying |
| Position limits checked during the day | Limits apply intraday, not only at the close |

*Measures announced by SEBI in October 2024, effective between November 2024 and April 2025. Check the current circulars before trading; rules change.*

The calendar-spread rule surprises people. Suppose you sold a weekly put and bought a monthly put as a hedge. On the weekly's expiry day the broker may ask for much more margin. If the account is short of it, the broker can close positions without asking you.

Stock positions carry their own expiry risk. In the last few days before expiry, exchanges charge extra margin on in-the-money stock futures and options because they will turn into delivery. Many brokers close such positions on their own a day or two before expiry. Learn your broker's rule before you hold a stock position into expiry week.

## 8. Rolling a position

Rolling means closing a position in the expiring contract and opening the same position in a later one. A futures trader who wants to stay long rolls from the October future to the November future before October expires. An option seller may buy back this week's option and sell next week's.

A roll is two trades, so it costs two spreads and two sets of charges. For futures, the later contract usually trades at a premium to the near one, and the roll pays that difference; [Futures basis](learn-fno-futures-basis.md) explains it. Roll before the last day, when the near contract's liquidity and the margin rules both work against you.

## 9. What can go wrong

- **Selling options on expiry day for small premiums.** The win is a few rupees; a fast move of half a percent can cost many times that.
- **Buying cheap out-of-the-money options on expiry day.** Most expire worthless. A rare large win does not pay for a long run of small total losses.
- **Forgetting the holiday shift.** An expiry moved to Monday leaves one less session than you planned.
- **Holding a stock position into expiry without the cash or shares.** In-the-money stock options and futures turn into delivery. Brokers may close them for you at a poor price.
- **Letting an in-the-money long option be exercised.** The STT on exercise is higher than on a sale.
- **Not budgeting for expiry-day margin.** The extra margin and the lost spread benefit can force a close at the worst moment.

## 10. What the evidence says

Time decay and gamma are not opinions. They follow from how options are priced, and every pricing model shows the same shape: slow decay far from expiry, fast decay near it.

Ni, Pearson and Poteshman (2005) found that US stocks with heavily traded options closed near a strike price on expiry dates more often than on other days. Avellaneda and Lipkin (2003) gave a model of how hedging by option holders can pull a stock toward a strike. Both concern single stocks with large option positions relative to their trading volume.

For the Nifty, the simple test above found no large pinning effect at the daily close and no extra volatility on expiry days. That fits the view that the index is too large and too widely traded for option hedging to pin it.

SEBI's studies of individual F&O traders found that about 9 in 10 lost money. Heavy trading in index options on their expiry day was one of the concerns SEBI gave for the 2024 measures.

What is not known: whether intraday moves near the close of expiry day are larger than on other days. Testing that needs minute-by-minute data.

## 11. Checklist

- Which expiry is this, and how many trading sessions are left? Check the holiday list.
- Is the option weekly or monthly? Is the underlying an index (cash-settled) or a stock (delivery)?
- How much of the premium is time value? How much will it lose per day from here?
- If you are short, what does a move of 1% against you cost, at expiry and today?
- Do you have the margin for expiry day, including the extra margin and the lost spread benefit?
- For a stock position, do you have the cash or the shares for delivery? What is your broker's close-out rule?
- Will you close an in-the-money long option before 15:30 to avoid exercise STT?
- If you will roll, when, and what does the roll cost?

## Further reading

- Sheldon Natenberg, *Option Volatility and Pricing* (2nd edition, 2015) — chapters on time decay and gamma.
- John C. Hull, *Options, Futures, and Other Derivatives* — exercise, settlement and the Greeks.
- Sophie Ni, Neil Pearson and Allen Poteshman, "Stock Price Clustering on Option Expiration Dates", *Journal of Financial Economics* (2005).
- Marco Avellaneda and Michael Lipkin, "A Market-Induced Mechanism for Stock Pinning", *Quantitative Finance* (2003).
- SEBI, circular "Measures to strengthen Equity Index Derivatives framework for increased investor protection and market stability" (1 October 2024).
- SEBI, "Analysis of Profit and Loss of Individual Traders dealing in Equity F&O Segment" (January 2023 and September 2024 studies).
