# Earnings gaps and episodic pivots — buying the big results-day gap

**In short**

- An **episodic pivot** is a stock that jumps on news, usually quarterly results, with a large gap and very heavy volume, after months of being ignored.
- You buy when the price trades above the gap day's high (or the high of the first minutes of trading), with the stop at the low of the gap day.
- The stop is wide, so the position is small. Many trades fail within a few weeks; the strategy lives on a few big winners.
- On stored data, results-day jumps of 10% or more on heavy volume did only slightly better than an average results day in the US since 2009. In India since 2020 they did clearly better, on a much smaller sample.
- Use it in a healthy market, on stocks with a real change in the business, and judge it on many trades, not one.

This guide belongs to the event-driven group, with [post-earnings drift](learn-strat-pead.md) and [index and news events](learn-strat-index-news-events.md). For how to read a results report, see [earnings that move stocks](learn-fund-earnings.md).

## 1. The idea

### An example first

Kaynes Technology, an Indian electronics manufacturer, reported its results for the March 2023 quarter. On 17 May 2023 the stock opened 9.8% above the previous close of 998.95. Volume was about 14 times its 50-day average. The stock closed at 1,169.30, up 17.1% on the day.

```series
title: Kaynes Technology — the results gap of 17 May 2023
from: 2023-03-01
to: 2023-08-31
line: india:KAYNES.NS | Kaynes Technology
line: india:KAYNES.NS@sma20 | 20-day average
line: india:KAYNES.NS@vol | Volume | pane2 bars
mark: 2023-05-17 | Results gap, about 14 times normal volume
caption: The gap of 17 May 2023 never closed. The stock rose from 1,169 to 2,014 by the end of August.
```

The next day the price traded above the gap day's high of 1,190. A buyer there had a stop at the gap day's low, 1,075.10, about 9.7% below. The stock never came back to that low. It closed at 2,014 on 31 August 2023.

### What the trade is

The trade buys a stock on the day after (or the day of) a large upward gap caused by news. The news is usually results: profits far above what the market expected, or a change in guidance. It can also be an order win, a regulatory approval or a new product.

Pradeep Bonde, who writes and teaches as Stockbee, named this setup the **episodic pivot**: an episode (a piece of news) that pivots the stock from one price level to a new one. Kristjan Kullamägi, a Swedish trader known as Qullamaggie, made it widely known among retail traders through his blog and streams. Both describe it in their own material; the rules below are a testable version, not a copy of either trader's method.

### Why it can work

A big surprise changes what a business is worth. But investors do not all react on the same day. Funds need meetings, analysts revise their models over days, and some buyers wait for the next quarter to confirm the change. That slow adjustment is the same effect behind [post-earnings drift](learn-strat-pead.md).

The volume matters. A gap on ordinary volume can be a few traders chasing headlines. A gap on ten times normal volume means large holders were active. If they are still buying, they will keep buying in the weeks after.

### Who is on the other side

The sellers on the gap day are mostly holders taking a quick profit, short sellers covering, and traders who think the jump is overdone. If the news really changed the business, they sold too early. If the news was a one-off, they were right, and the gap fades. Your job is to tell those cases apart, and to cut the trade fast when you are wrong.

## 2. When it works and when it doesn't

**Market conditions.** Gap-ups follow the market. In a falling market, even good results get sold within days. Trade this setup when the index is above a rising 50-day average (see [reading the market's trend](learn-health-trend.md)). In the event study below, Indian gaps did badly in the weak years up to 2022, and well after that.

**Stock types.** It suits stocks where a single quarter can change the story. These are small and mid-sized growth companies, recent listings, and turnarounds. A gap in a very large, widely followed company is usually absorbed fast, because hundreds of analysts were already watching.

**Neglect helps.** Bonde stresses stocks that went nowhere for months before the news. A stock that already doubled into its results has many holders ready to sell. A stock that sat flat for a year has few.

**India.** Indian companies often release results during market hours, or after the close. When results arrive mid-session, the move happens inside the day rather than as an opening gap. So in India, look for a large close-to-close move, not only an opening gap.

Stocks outside the futures and options list have price bands (circuit limits) of 5%, 10% or 20%. A stock locked at its upper band cannot be bought, and the next day may open far higher. Settlement is T+1. Overnight short selling of cash shares is not possible, so the short side of this setup (a gap down) needs stock futures.

**US.** Results come before the open or after the close, so the reaction shows as an opening gap. Liquidity is deep in most names. Pre-market trading lets you see the gap form, but pre-market prices are thin and can mislead.

## 3. The rules

### Universe and filters

- Price at least ₹50 (India) or $5 (US).
- 20-day average traded value at least ₹5 crore or $5 million, before the event.
- The stock is not under a regulatory restriction (for example an additional surveillance list in India).

### Setup

All conditions are measured on the reaction day, the first session after the news.

- An identifiable catalyst: results announced in the window from 3 days before this session to this session.
- The close is at least 10% above the previous close (*minimum move*), or the open is at least 5% above it (*minimum gap*).
- Volume is at least 3 times its 50-day average (*minimum relative volume*).
- The close is in the top 30% of the day's range (*minimum close position*): (close − low) ÷ (high − low) ≥ 0.7.
- Optional quality filter: net profit up at least 25% on the same quarter a year earlier (*minimum growth*).
- Optional neglect filter: the stock's close is less than 30% above its level 60 sessions earlier.

### Entry

- Trigger: a buy-stop order just above the reaction day's high, valid for 5 sessions (*entry window*).
- Intraday version: buy above the high of the first 5 to 30 minutes of the reaction day itself (the opening range). This is how Kullamägi describes his entries.
- If the stock opens above the trigger, you are filled at the open, a worse price. Count that in tests.

### Initial stop

- The low of the reaction day. With the intraday entry, the low of the day so far.
- If that stop is more than 1.5 times the stock's 14-day ATR below the entry, or more than 12% below, skip the trade or use the intraday entry, which gives a closer stop.

### Exits

- **Stop:** a close (or a trade, if you use a resting stop order) below the reaction-day low.
- **Partial profit:** sell a third of the position after 3 to 5 sessions if the trade is in profit (*partial-sale day*). Kullamägi describes selling a third to a half at this point and moving the stop to breakeven.
- **Trailing exit:** sell the rest on the first close below the 20-day average (*trailing average*). Use the 10-day for faster stocks.
- **Time stop:** if the close is not above the entry after 10 sessions (*time stop*), sell.

### Position size

Size from the stop, as in [position sizing](learn-risk-sizing.md). Risk 0.25% to 1% of capital per trade (*risk per trade*). With a 10% stop and 0.5% risk, the position is 5% of the account. Cap any one position at 10% to 20% of capital, because a second results gap a quarter later can open below the stop.

### Managing the trade

- Do not add to a position that is below the entry.
- After the partial sale, move the stop to the entry price.
- Before the next results date, decide: hold through it, or sell. Holding means accepting a gap that can jump the stop.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| *minimum move* | 10% (8–20%) | Size of the reaction-day move | Higher means fewer, stronger events |
| *minimum gap* | 5% (3–10%) | Opening gap, for US-style releases | In India use the move instead |
| *minimum relative volume* | 3× (2–10×) | Volume against the 50-day average | Most big gaps pass 3× anyway |
| *minimum close position* | 0.7 (0.5–0.8) | Where the reaction day closes in its range | Strongest single filter in the study below |
| *minimum growth* | 25% (0–50%) | Year-on-year profit growth | Helped in both markets, smaller samples |
| Neglect | Under 30% rise in 60 sessions | Avoids stocks already extended | Untested here; Bonde's emphasis |
| Results window | 3 days before to the session | Links the move to the news | Without it you buy random spikes |
| *entry window* | 5 sessions (1–10) | How long the buy-stop waits | Longer windows add late, weaker entries |
| Stop width cap | 12% or 1.5 ATR | Skips trades with stops too wide | Tighter caps skip the biggest gaps |
| *partial-sale day* | 3–5 sessions | When to sell the first third | |
| *trailing average* | 20-day (10–50) | Trailing exit | Shorter exits earlier, keeps less of big runs |
| *time stop* | 10 sessions (5–20) | Exit if nothing happens | |
| *risk per trade* | 0.5% (0.25–1%) | Account risk per trade | |

## 5. Variations

- **Bonde's episodic pivot.** Bonde groups catalysts into kinds (earnings, new products, regulation, sector news) and stresses a stock that was neglected before. He looks for very large volume relative to normal.
- **Kullamägi's version.** Kullamägi buys on the break of the opening-range high on the gap day itself, with the stop at the day's low. He sells part after a few days and trails the rest with the 10-day or 20-day average.
- **O'Neil-style "buyable gap-up".** Gil Morales and Chris Kacher, in *Trade Like an O'Neil Disciple* (2010), describe buying a gap-up on heavy volume in a leading stock, with the stop near the gap day's low.
- **Delayed entry.** Some traders wait for the first pullback, a few days of tight trading after the gap, and buy the break above it. The stop is closer, but many of the strongest gaps never pull back.
- **Fading the gap.** The opposite trade sells gaps on weak closes. In India that needs stock futures; see the section on [gap fills](learn-strat-gap-fills.md).

## 6. Worked examples

### Kaynes Technology, May 2023 (India): it worked

| Step | Date | Price | Note |
|---|---|---|---|
| Reaction day | 17 May 2023 | Open 1,097, high 1,190, low 1,075.10, close 1,169.30 | Up 17.1%, volume about 14× average, close in top 18% of range |
| Entry | 18 May 2023 | 1,190 | The buy-stop above the gap day's high filled |
| Initial stop | — | 1,075.10 | Risk 9.7% per share |
| Exit | 30 Jun 2023 | 1,505.40 | First close below the 20-day average |

The trade made 26.5%, or about 2.7 times the amount risked (2.7R). The highest close during the trade was 1,600.50, on 13 June. The exit gave back part of that, which is the cost of a trailing exit.

### Angel One, October 2024 (India): it failed

Angel One, a stockbroker, rose 18.4% on 15 October 2024 after results, on about 13 times its average volume. The gap at the open was 8.0%, and the close was near the top of the day.

```series
title: Angel One — a results jump that failed, October 2024
from: 2024-08-01
to: 2024-12-31
line: india:ANGELONE.NS | Angel One
line: india:ANGELONE.NS@sma20 | 20-day average
line: india:ANGELONE.NS@vol | Volume | pane2 bars
mark: 2024-10-15 | Up 18% on results
caption: The gap day looked strong, but the stock fell back through the gap day's low within a week. Prices are adjusted for a later split.
```

| Step | Date | Price | Note |
|---|---|---|---|
| Reaction day | 15 Oct 2024 | High 325.80, low 286.60, close 322.45 | All setup conditions met |
| Entry | 16 Oct 2024 | 325.80 | Filled above the gap day's high |
| Initial stop | — | 286.60 | Risk 12.0%, at the upper edge of the stop cap |
| Exit | 22 Oct 2024 | 286.60 | Stopped out: a loss of 1R |

Nothing in the setup warned of this. The trade lost one unit of risk, which the position size had already limited. That is the normal shape of this strategy: losses of about 1R, often, and occasional gains of several R.

### Palantir, May 2023 (US): a large winner

Palantir opened 19.1% higher on 9 May 2023 after results, and closed up 23.4% on about 7.5 times its average volume.

```series
title: Palantir — the results gap of 9 May 2023
from: 2023-03-01
to: 2023-08-31
line: us:PLTR | Palantir
line: us:PLTR@sma20 | 20-day average
line: us:PLTR@vol | Volume | pane2 bars
mark: 2023-05-09 | Gap up 19% on results
caption: The stock nearly doubled from the gap in about two months.
```

The buy-stop above the gap day's high of 9.69 filled at 9.73 on 10 May. The stop was the gap day's low, 8.65, a risk of 11.0%. The first close below the 20-day average came on 21 June 2023, at 14.64. The trade made 50.5%, about 4.6R.

### Sona BLW, October 2024 (India): no trade

Sona BLW rose 13.3% on 24 October 2024, on about 14 times its normal volume. The price never traded above that day's high of 744.90 in the next 5 sessions. The buy-stop expired, and no trade was taken. A trigger that is never hit is a filter doing its job.

## 7. Common mistakes

- **Buying the gap at the open without a plan.** The first minutes are the most volatile of the day. Without a trigger and a stop, you are guessing.
- **Ignoring how wide the stop is.** A 15% stop with a full-size position is a large loss. Size from the stop, or skip the trade.
- **Treating every gap as a pivot.** Many gaps come from one-off gains, takeover rumours or index inclusion. Read the results before you buy.
- **Holding a failed gap.** When the price closes back below the gap day's low, the market has rejected the news. Exit.
- **Judging the strategy on a few trades.** With a win rate near half and large winners, ten trades prove nothing. See [expectancy](learn-risk-expectancy.md).
- **Chasing in a falling market.** In a weak market, gap-ups get sold. Check the index first.

## 8. What the evidence says

**Published research.** The idea that prices underreact to earnings news goes back to Ball and Brown (1968), covered in the [post-earnings drift](learn-strat-pead.md) guide. Wesley Chan (2003) found that stocks with large moves on public news tended to continue, while large moves without news tended to reverse. That supports requiring a real catalyst. There is little peer-reviewed work on the exact episodic-pivot rules. Practitioner accounts are real, but they report the trader's own results, which cannot be checked.

**Event study on stored data.** I took every quarterly results filing date for stocks that passed the universe filters. The reaction day is the session with the largest close-to-close move from 3 days before the filing date to one session after. I measured the stock's return from the reaction-day close to 60 sessions later, minus the index return over the same days (the S&P 500 ETF in the US, the Nifty 50 in India). "Low broken" means the price traded below the reaction-day low within 20 sessions.

| Group | Events | Excess return over 60 sessions, median | Mean | Beat the index | Low broken within 20 sessions |
|---|---|---|---|---|---|
| US, all results days, 2009–2026 | 65,652 | −0.5% | +0.3% | 48% | 76% |
| US, up 10%+ on 3× volume | 2,278 | −0.2% | +1.7% | 50% | 47% |
| US, same, close in top 30% of range | 1,378 | 0.0% | +1.5% | 50% | 37% |
| US, same as row 2, profit growth 25%+ | 643 | +1.1% | +1.8% | 52% | 42% |
| India, all results days, 2020–2026 | 5,669 | +1.3% | +3.8% | 54% | 77% |
| India, up 10%+ on 3× volume | 195 | +5.8% | +7.4% | 58% | 41% |
| India, same, close in top 30% of range | 158 | +6.6% | +7.2% | 58% | 35% |
| India, same as row 6, profit growth 25%+ | 68 | +9.3% | +9.3% | 60% | 34% |

By period, the Indian group did very differently:

| India, up 10%+ on 3× volume | Events | Excess return over 60 sessions, median | Beat the index |
|---|---|---|---|
| 2020–2022 | 31 | −0.6% | 39% |
| 2023–2026 | 164 | +7.9% | 62% |

**What this says.** In the US, a big results-day jump on its own predicted almost nothing over 60 sessions. The mean beats the median, so a few large winners lift the average. 

In India the edge looks large, but the sample is small and mostly from 2023–2026, a strong period for smaller companies. Even the average Indian results day beat the Nifty 50 then, because the Nifty 50 holds only the largest companies. Two filters helped in both markets: a close near the day's high, and strong profit growth. Both mean fewer gap days broke below their low.

**Caveats.** The universe is today's list of stocks, so companies that later delisted are missing (survivorship bias). The filing date is not always the release date, especially in the US, so some events are misdated. Indian results data start in late 2020. These are average outcomes from a close, not a trading strategy with entries, stops and costs.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume; results announcement dates with the time of day (before, during or after the session); quarterly profit figures as first reported. For the intraday entry you need minute bars of the reaction day.

**Look-ahead traps.**
- Do not use the reaction day's close to decide a trade entered at the open of that same day.
- Do not use profit figures filed after the trade date. Use the filing date, not the quarter-end date.
- Results announced after the close belong to the next session.

**Survivorship.** Include delisted stocks. Many small companies that gapped up later failed and left the exchange.

**Fills.** A buy-stop above a high often fills at the next day's open, above the trigger. Model that. Stops on gap-down days fill at the open, below the stop.

**Costs in India (approximate, delivery trades).** STT is about 0.1% on both the buy and the sell. Stamp duty is about 0.015% on the buy. Exchange and regulator charges are a few thousandths of a percent, with GST on brokerage and charges. A depository charge of about ₹15 applies to each sale.

Add slippage of 0.1% to 0.3% for mid-sized stocks on high-volume days. In the US, commissions are near zero, but allow 0.05% to 0.2% slippage.

**What to test.** Vary *minimum move*, *minimum close position* and the trailing average one at a time. Prefer settings where nearby values give similar results. Split the data by year and by market regime. Hold back the most recent two years until the end.

**What a good test reports.** The number of trades, the win rate, and the average win and loss in R. Expectancy per trade and the largest losing streak. Results by year, and the share of profit that came from the top tenth of trades.

```
for each results event:
    R = reaction session (largest move from filing-3 days to filing+1 session)
    if close[R]/close[R-1]-1 < move_min: skip
    if volume[R] < rvol_min * avg_volume_50[R-1]: skip
    if (close[R]-low[R]) / (high[R]-low[R]) < close_pos_min: skip
    trigger = high[R]; stop = low[R]
    for day in next entry_window sessions:
        if high[day] > trigger:
            entry = max(open[day], trigger); break
    size = account * risk_pct / (entry - stop)
    exit on: low <= stop | close < sma(trail_ma) | no gain after time_stop sessions
```

## 10. Checklist

- [ ] Is the market in an uptrend (index above a rising 50-day average)?
- [ ] Is there real news, and have I read it? Is it a lasting change, not a one-off gain?
- [ ] Did the stock move 10% or more on at least 3 times normal volume?
- [ ] Did it close in the top third of the day's range?
- [ ] Was the stock quiet or neglected before the news?
- [ ] Where is my trigger, and where is my stop (the reaction-day low)?
- [ ] Is the stop narrower than my cap? Is the position sized from it?
- [ ] When will I take a partial profit, and what is my trailing exit?
- [ ] When is the next results date?
- [ ] India: is the stock near its price band? Can I exit if it locks at the lower band?

## Further reading

- Pradeep Bonde (Stockbee) — his blog and course material on episodic pivots.
- Kristjan Kullamägi (Qullamaggie) — his blog posts and recorded streams describing the setup.
- Gil Morales and Chris Kacher, *Trade Like an O'Neil Disciple* (Wiley, 2010) — buyable gap-ups.
- William J. O'Neil, *How to Make Money in Stocks* (McGraw-Hill, 4th ed. 2009).
- Ray Ball and Philip Brown, "An Empirical Evaluation of Accounting Income Numbers", *Journal of Accounting Research* (1968).
- Wesley S. Chan, "Stock price reaction to news and no-news: drift and reversal after headlines", *Journal of Financial Economics* (2003).
