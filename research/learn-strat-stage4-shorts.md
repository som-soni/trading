# Shorting Stage 4 stocks — selling a stock that is already falling

**In short**

- A Stage 4 stock is in a long decline: it trades below a falling 30-week (about 150-day) average, with lower highs and lower lows. Stan Weinstein's rule is to own none of them, and to short the weakest.
- There are two entries: the **breakdown** below support, and the **rally back to the falling average** that fails. Our data favours the second.
- The stop goes above the last rally high or above the falling average. A short has no limit to its loss, so the stop and the size matter more than on a long.
- Shorts face risks longs do not: gaps up on news, short squeezes, borrow costs and recalls. Risk less per short than per long.
- In India a swing short is held through stock futures (see the Futures & options section). In the cash market you can only short for the day.

## 1. The idea

In August 2024, IndusInd Bank had been falling for four months. Its 150-day average had turned down in July. On 7 August it closed at ₹1,345, below its lowest close of the past year, on twice its normal volume. In September it rallied to the falling 150-day line and touched ₹1,498. On 24 September it closed back below the line, at ₹1,448.

```series
title: IndusInd Bank — a Stage 4 decline, 2024–25
from: 2024-03-01
to: 2025-04-30
tf: D
line: india:INDUSINDBK.NS | IndusInd Bank | log
line: india:INDUSINDBK.NS@sma150 | 150-day average (≈ 30-week)
line: india:INDUSINDBK.NS@vol | Volume | pane2 bars
mark: 2024-08-07 | new 52-week low
mark: 2024-09-24 | rally fails at the line
mark: 2024-10-25 | results, −19%
mark: 2025-03-11 | accounting disclosure, −27%
caption: The September rally stopped at the falling 150-day line. From the failed rally on 24 September to 11 March, the stock fell 55%.
```

That is a Stage 4 short. Stan Weinstein divided a stock's life into four stages, read off its 30-week moving average. Stage 4 is the decline: the price is below a falling average, and each rally stops lower than the one before. [The price stages guide](learn-price-stages.md) explains all four stages.

Why does the decline continue? Holders who bought higher are losing money.

Each rally back toward their purchase price brings out sellers who want to get out even. Funds that decide to leave a stock sell for months, not days. Bad news also tends to come in a series, and the price absorbs it slowly. Hong, Lim and Stein (2000) found that bad news reaches prices more slowly than good news in stocks that few analysts follow.

Who is on the other side? Mostly buyers who think the stock is cheap. They are bottom-fishers, value buyers and holders averaging down. Sometimes they are right, and that is the short seller's main risk: a falling stock can turn sharply when the news improves.

## 2. When it works and when it doesn't

**It works best in a bear market.** When most stocks fall, a Stage 4 stock falls further. Weinstein advised shorting only when the market itself is in Stage 3 or Stage 4. In a rising market, a Stage 4 stock often goes sideways into a Stage 1 base instead of falling.

**It works best on stocks with a reason to fall.** Falling earnings, a broken business, a sector in decline, an accounting question. IndusInd Bank had weak results and then an accounting disclosure. A stock in Stage 4 only because its sector is out of favour can turn as soon as the sector does.

**It works badly after a crash.** A stock that has just fallen 50% in a few days is stretched far below its average. Rallies from there are violent. Short the first rally that fails, not the crash.

**It works badly in a sharp market turn.** At a bear-market bottom, the weakest stocks often rise the most. Daniel and Moskowitz (2016) found that momentum strategies suffer their worst losses in these rebounds, and the losses come mostly from the stocks that had been falling. See [the squeezes and bear-market rallies guide](learn-strat-squeezes-bear-rallies.md).

**India.** You cannot hold a short overnight in the cash market as a retail trader. A cash short must be bought back the same day. A swing short needs stock futures or put options (see the Futures & options section). Only about two hundred stocks have them, mostly the larger ones. Three things follow:

- **Lots.** A futures contract has a fixed lot size, usually worth several lakh rupees. Your stop must fit your risk budget in whole lots.
- **Expiry and rolling.** Futures expire monthly. To hold a short longer, close it and sell the next month's contract. Futures usually trade a little above the share price; that premium shrinks toward expiry, which helps a short slightly.
- **Delivery and bans.** Stock futures settle by delivery, so a short held to expiry means delivering shares. When open interest passes 95% of the market-wide limit, the stock enters a ban period and you can only reduce positions.

**US.** You borrow the shares through your broker and sell them. Large stocks are cheap to borrow. Small, heavily shorted stocks can cost tens of percent a year, and the lender can recall the shares. The short pays any dividends. After a 10% one-day fall, new short sales are allowed only above the best bid for the rest of that day and the next.

## 3. The rules

### Universe and filters

- Median daily traded value over the last 50 sessions at least ₹10 crore or $10 million; price at least ₹50 or $5.
- India: the stock has futures, and is not in a ban period. US: borrow is available at a fee below 5% a year.
- Market filter: the index is below its 200-day average, or its 200-day average is lower than 20 sessions ago.
- Avoid stocks with a very large short interest (in the US, more than about 20% of the free float). Crowded shorts squeeze.
- Avoid stocks with results due in the next 5 sessions, unless you accept the gap risk.

### Setup

The stock is in Stage 4:

1. The close is below the 150-day average.
2. The 150-day average is lower than it was 20 sessions ago.
3. The 50-day average is below the 150-day average.
4. Relative strength is weak: the stock has done worse than its index over the last 63 sessions.

### Entry

There are two entries. Test them separately.

- **A. Breakdown.** The stock closes below its lowest close of the prior 250 sessions (a new 52-week closing low). Volume is at least 1.5 times its 50-day average. Weinstein noted that volume is less important on a breakdown than on a breakout; test with and without it.
- **B. Failed rally to the line.** The stock has been in Stage 4 for at least 40 sessions. It rallies until the high comes within 1% of the falling 150-day average, or briefly above it. Then it closes back below the line. Enter at that close, or the next open.

### Initial stop

- **Entry A:** above the highest high of the last 10 sessions, or above the 150-day average, whichever is lower.
- **Entry B:** above the high of the rally into the line.
- Add a buffer of 0.25 times the 14-day ATR.
- If the stop is more than 15% above the entry, skip the trade.

### Exits

- **Trailing stop:** from the 20th session, move the buy-stop down to the highest high of the last 20 sessions. Weinstein moves the stop down above each new lower rally peak; this is a testable version of that.
- **Trend exit:** cover on a close above the 50-day average, once the price has been below it.
- **Stage exit:** cover on a weekly close above the 30-week average. The decline is over.
- **Time stop:** cover after 60 sessions if the trade has not reached 1R.

### Position size

Risk 0.5% of the account per short (0.25–1%). Shares or lots = account risk ÷ (stop − entry), rounded down. Keep the total risk on all shorts at once to about 3% of the account. A short can gap far past its stop, so the real loss can be larger than planned. [The position sizing guide](learn-risk-sizing.md) shows the arithmetic.

### Managing the trade

- A short grows as the price rises. A losing short becomes a bigger share of your account, the opposite of a losing long. Never add to it.
- Watch for news: results, takeover rumours, a big investor buying. These cause gaps up.
- If the stock jumps more than 3 ATR in a day on heavy volume, take that as a warning. Tighten the stop to the day's low or cover.
- In India, roll before expiry. Check that the next month's contract is liquid.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Trend average | 150-day (≈ 30-week); 100–200 | Defines Stage 4 | Weinstein uses the 30-week |
| Slope lookback | 20 sessions (10–40) | "Falling" average | Longer is stricter |
| Breakdown low | Lowest close of 250 sessions (52 weeks); 60–250 | Entry A | A shorter low gives more, weaker signals |
| Breakdown volume | 1.5× the 50-day average (1–2×) | Entry A | Optional, see §5 |
| Time in Stage 4 before entry B | 40 sessions (20–60) | Entry B | Avoids the first dip after a top |
| Touch distance | High within 1% of the average | Entry B | 0–3% |
| Relative strength lookback | 63 sessions | Weakness filter | 63–126 |
| Stop buffer | 0.25 × ATR(14) | Room above the high | 0.1–0.5 |
| Maximum stop distance | 15% of entry | Skips trades after crashes | 10–20% |
| Trailing stop lookback | 20 sessions | How close the trail is | 10–40 |
| Time stop | 60 sessions | Dead trades | 20–90 |
| Risk per short | 0.5% of account | Size | 0.25–1% |
| Total short risk | 3% of account | Exposure | 2–5% |
| Short-interest cap (US) | 20% of float | Squeeze risk | 10–30% |
| Market filter | Index below its 200-day, or 200-day falling | Shorts only in weak markets | Test both |

## 5. Variations

**Weinstein's own method.** In *Secrets for Profiting in Bull and Bear Markets* (1988), Weinstein shorts when a stock breaks below the support of a Stage 3 top, with the 30-week average flat or turning down. He prefers to short on the pullback toward the breakdown point, and places the buy-stop above the prior rally peak and the average. He looks for weak relative strength and a weak sector. He says a breakdown does not need a burst of volume, because a stock can fall of its own weight.

**O'Neil's short rules.** William O'Neil, in *How to Make Money in Stocks*, shorts former market leaders after a clear top. He favours a head-and-shoulders top, shorting on the third or fourth rally to the right shoulder, and only in a bear market. He warns that shorting is harder than buying and that most investors should not do it.

```pattern
head-and-shoulders
```

**Former support becomes resistance.** Many traders short a rally back to the old breakdown level rather than to the moving average. A level where buyers once held now holds sellers who want to get out even.

```pattern
role-reversal
```

**Put options instead of a short.** Buying a put limits the loss to the premium paid. It costs time decay and needs the fall to come fast. In India, options are the only way to short some setups if futures lots are too large (see the Futures & options section).

**Pairs.** Some traders short a Stage 4 stock and buy a strong stock in the same sector. The market's moves largely cancel. It halves the market risk but doubles the costs.

## 6. Worked examples

Prices are split-adjusted closes from daily data. R is the profit or loss divided by the initial risk.

### IndusInd Bank, 2024 — a failed rally to the line (India, via futures)

The chart is in §1.

| Step | Date | What happened |
|---|---|---|
| Stage 4 | Jul–Aug 2024 | Close below the 150-day; the 150-day lower than 20 sessions earlier |
| Breakdown | 7 Aug 2024 | Close ₹1,345.15, below the 52-week closing low of ₹1,364.50, on 2.1× volume |
| Rally to the line | 19 Sep 2024 | High ₹1,498, with the 150-day at ₹1,460 |
| Entry B | 24 Sep 2024 | Close ₹1,448.30, back below the line |
| Initial stop | — | Above the rally high: ₹1,500. Risk ₹51.70 (3.6%) |
| What happened | 25 Oct 2024 | Weak results; the stock fell 19% to ₹1,041.60 |
| Exit | 3 Jan 2025 | Trailing stop hit at ₹1,007.95 |
| Result | — | +30%, about +8.5R |

Note the breakdown entry. Suppose you had shorted on 7 August, with a stop just above the 150-day line at about ₹1,495. The high on 19 September would have hit that stop. The failed rally gave a tighter stop and a better price. The stock later fell to ₹656 in March 2025, after the bank disclosed accounting problems.

### PayPal, November 2021 — a breakdown short (US)

```series
title: PayPal — breakdown into Stage 4, 2021–22
from: 2021-06-01
to: 2022-06-30
tf: D
line: us:PYPL | PayPal | log
line: us:PYPL@sma150 | 150-day average
line: us:PYPL@vol | Volume | pane2 bars
mark: 2021-11-19 | new 52-week low
mark: 2022-03-18 | trailing stop
caption: The 150-day average had turned down in October. The stock fell from 193.61 to 113.54 before the trailing stop was hit.
```

| Step | Date | What happened |
|---|---|---|
| Stage 4 | Nov 2021 | 150-day at 266.29, below its 270.80 of 20 sessions earlier; close far below it |
| Breakdown | 19 Nov 2021 | Close 193.61, below the 52-week closing low of 200.50, on 1.95× volume |
| Initial stop | — | Above the 16 November high of 215.97: 216.00. Risk 22.39 (11.6%) |
| What happened | Feb 2022 | Results with a weak outlook; the stock fell about a quarter in a day |
| Exit | 18 Mar 2022 | Trailing stop hit at 113.54 |
| Result | — | +41%, about +3.6R |

With the trend exit instead, the short would have been covered on the first close above the 50-day average, on 4 April 2022 at 121.86.

### Adani Enterprises, February 2023 — shorting after a crash (India, a failure)

```series
title: Adani Enterprises — a short after the crash, squeezed in March 2023
from: 2022-11-01
to: 2023-06-30
tf: D
line: india:ADANIENT.NS | Adani Enterprises | log
line: india:ADANIENT.NS@sma150 | 150-day average
line: india:ADANIENT.NS@vol | Volume | pane2 bars
mark: 2023-01-27 | after the short-seller report
mark: 2023-02-22 | new 52-week low
mark: 2023-03-06 | ₹1,983
caption: After a 60% fall in a month, the stock made one more low and then rose 66% in five sessions.
```

| Step | Date | What happened |
|---|---|---|
| Background | 24 Jan 2023 | A US short seller published a report accusing the group of fraud. The stock fell from ₹3,442 to ₹1,565 in six sessions |
| Breakdown | 22 Feb 2023 | Close ₹1,404.85, below the 52-week closing low of ₹1,543.95, on 1.5× volume. 150-day falling |
| Initial stop | — | Above the last rally high of ₹1,874.95: risk ₹470 (33%) |
| Rule check | — | The stop is more than 15% away. **The rules say skip.** |
| What happened | 27 Feb – 6 Mar 2023 | Low close ₹1,193.50, then a news-driven rally to ₹1,982.90 |
| If taken anyway | 3 Mar 2023 | Stop hit: −1R, a 33% loss on the position |

This shows why the maximum stop rule exists. After a crash, volatility is huge: the 14-day ATR was ₹261, about 19% of the price. Any sensible stop is far away. In early March a US fund announced a large investment in the group, and the stock rose 66% in five sessions from its low close. A short taken at the low was squeezed.

## 7. Common mistakes

- **Shorting a stock because it "has gone up too much".** That is a Stage 2 or Stage 3 stock. Wait for Stage 4.
- **Shorting after the crash.** Short the failed rally, not the big down day.
- **No stop, or a mental stop.** A short's loss has no ceiling. Put the stop in the market.
- **Too big.** Shorts gap. Risk half of what you risk on a long.
- **Shorting in a bull market.** Most Stage 4 stocks then drift sideways, and a few squeeze hard.
- **Crowded shorts.** A stock that everyone is short can rise violently on small good news.
- **India: the wrong instrument.** A cash short left open at the close goes to auction. Use futures or options for anything beyond the day.

## 8. What the evidence says

**Published research.**
- **Momentum's short side.** Jegadeesh and Titman (1993) found that the past year's losers kept underperforming the winners for the next several months. Later work found the effect strongest among small, little-followed stocks.
- **Distance from the high.** George and Hwang (2004) found that stocks far below their 52-week high tended to do worse than stocks near it.
- **Crashes of the short side.** Daniel and Moskowitz (2016) showed that the losers rebound violently after market falls, when volatility is high. Shorting the weakest stocks is most dangerous right after a bear market.
- **Short sellers.** Boehmer, Jones and Zhang (2008) found that heavily shorted stocks did worse than lightly shorted ones. Lamont and Thaler (2003) documented cases where shorting was so hard that prices stayed clearly too high.

None of these papers tests Weinstein's rules directly. Weinstein's own book shows examples, not statistics.

**Our event study.** We measured what Stage 4 stocks did after the two entries in §3. The sample is liquid Indian and US stocks from 2012 to mid-2025.

*Method.* Liquid means a median daily traded value of at least ₹10 crore or $10 million. The price had to be at least ₹50 or $5.

Stage 4 means a close below a 150-day average that is lower than 20 sessions earlier. A **breakdown** is a close below the lowest close of the prior 250 sessions, on at least 1.5 times average volume. A **rally to the line** needs 40 sessions in Stage 4, then a day whose high is within 1% of the average and whose close is below it. One event per stock per 60 sessions (40 for rallies). Returns are from the event close; "minus index" subtracts the Nifty 500 or S&P 500 total return.

| Breakdown to a new 52-week low | India | US |
|---|---|---|
| Events | 962 | 9,068 |
| Median return, next 60 sessions | +3.2% | +4.0% |
| Median return minus index, 60 sessions | −0.5% | −1.2% |
| Share that lagged the index, 60 sessions | 52% | 53% |
| Share that rose 10% or more within 20 sessions | 38% | 41% |
| Share that rose 20% or more within 20 sessions | 11% | 15% |

| Failed rally to the falling 150-day | India | US |
|---|---|---|
| Events | 1,237 | 7,705 |
| Median return, next 60 sessions | +1.6% | +0.2% |
| Median return minus index, 60 sessions | −2.1% | −3.0% |
| Share that lagged the index, 60 sessions | 57% | 59% |
| Share that rose 10% or more within 20 sessions | 30% | 26% |
| Share that rose 20% or more within 20 sessions | 8% | 7% |

*What it shows.* A new 52-week low on its own was a poor short. The typical stock rose afterwards, lagged its index only slightly, and two in five rallied 10% within a month. The failed rally to the line was better on every measure: it lagged the index more often, and it rallied hard less often. Neither is a large edge before stops, exits and a market filter. Both need the weak-market condition that Weinstein insisted on.

*Caveats.* Today's stock lists leave out many delisted companies, which were often the best shorts, so the short side is understated. The Indian sample is small before 2016, because few stocks met the rupee liquidity filter. Events cluster in bad years such as 2018 and 2022, so they are not independent. No costs, borrow fees or stops are included.

**What is unknown.** How much the market filter and an exit rule add. That is the test to run yourself.

## 9. Building and testing it yourself

**Data.** Daily prices adjusted for splits, with volume. Index closes. For India, the derivatives list and ban list on each date. For the US, short interest and borrow fees if you can get them; few free sources have history.

**Look-ahead traps.**
- Moving averages and 52-week lows must use data up to the signal day only.
- A stock must have had futures *on the signal date* to count as an Indian short.
- Do not use today's sector labels or index membership for the past.

**Survivorship.** This matters more for shorts than for anything else. The stocks that went to zero are missing from today's lists. A test on survivors will make shorting look worse than it was, and a test that adds back only famous collapses will make it look better. Use a database with delisted stocks.

**Costs (approximate).**
- India, stock futures: brokerage about ₹20 per order; STT 0.05% on the sell side (since April 2026); stamp duty about 0.002% on the buy side; exchange fees and GST. Add the cost of rolling each month: two more trades and the spread.
- US: the spread, plus a borrow fee (under 1% a year for most large stocks, far more for crowded ones), plus dividends paid while short.
- Slippage: shorts are stopped out on gaps up. Fill at the open when the open is beyond the stop.

**Over-fitting.** Fix the stage definition first (150-day, 20-session slope) and do not tune it. Test the entries and exits on top of it. Vary one parameter at a time and look for broad, flat regions of results. Hold out recent years.

**What a good test reports.**

- Trades, win rate, and the average win and loss in R.
- Expectancy, and the largest single loss in R (gaps).
- Results by year and by market regime.
- Total short exposure over time, and the effect of costs and borrow.

```
stage4[t] = close[t] < sma150[t] and sma150[t] < sma150[t-20] and sma50[t] < sma150[t]

entry A: stage4[t] and close[t] < min(close[t-250 .. t-1])
                    and volume[t] >= 1.5 * mean(volume[t-50 .. t-1])
         stop = min(max(high[t-9 .. t]), sma150[t]) + 0.25 * atr14[t]

entry B: all(stage4[t-40 .. t-1]) and high[t] >= 0.99 * sma150[t] and close[t] < sma150[t]
         stop = max(high of the rally into the line) + 0.25 * atr14[t]

skip if (stop - entry) / entry > 0.15 or market filter is off
manage: from day 20, stop = min(stop, max(high[last 20]))
        cover on stop, on a close above sma50 (after being below it), or after 60 days if < 1R
```

## 10. Checklist

- [ ] The stock is in Stage 4: below a falling 150-day average, 50-day below the 150-day, lagging its index.
- [ ] The market is weak: index below its 200-day, or its 200-day falling.
- [ ] Entry is a failed rally to the line, or a breakdown to a new 52-week low.
- [ ] The stock has not just crashed; the stop is no more than 15% away.
- [ ] I can short it: futures in India (not in the ban period); cheap borrow in the US; short interest not extreme.
- [ ] No results in the next few sessions, or I accept the gap risk.
- [ ] Risk is 0.5% of the account or less; total short risk under 3%.
- [ ] Stop order is in the market. I know the expiry date.

## Further reading

- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* (1988).
- William J. O'Neil, *How to Make Money in Stocks* (4th ed., 2009).
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* 48 (1993).
- Harrison Hong, Terence Lim and Jeremy C. Stein, "Bad News Travels Slowly", *Journal of Finance* 55 (2000).
- Thomas J. George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* 59 (2004).
- Kent Daniel and Tobias J. Moskowitz, "Momentum Crashes", *Journal of Financial Economics* 122 (2016).
- Ekkehart Boehmer, Charles M. Jones and Xiaoyan Zhang, "Which Shorts Are Informed?", *Journal of Finance* 63 (2008).
- Owen A. Lamont and Richard H. Thaler, "Can the Market Add and Subtract? Mispricing in Tech Stock Carve-outs", *Journal of Political Economy* 111 (2003).
