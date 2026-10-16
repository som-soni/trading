# Short squeezes and bear-market rallies — the sharp rises inside a decline

**In short**

- A **short squeeze** is a fast rise driven by short sellers buying back shares to cut their losses. Their buying pushes the price up, which forces more of them to buy.
- A **bear-market rally** is a rise of 10% or more in an index that is still in a bear market. They are common, fast and convincing, and most end at a lower high.
- For a short seller both are the main danger. Survive them with small positions, real stops and by avoiding crowded shorts.
- Trading them long is possible but hard. Use small size, a stop under the rally's start, and a target at the falling average where most of them stall.
- You cannot tell a bear rally from the start of a new bull market on day one. The rules below are built to be wrong cheaply in both cases.

## 1. The idea

On 8 January 2021, GameStop closed at $4.42 (split-adjusted). Reported short interest was above 100% of the shares available to trade: more shares had been sold short than were freely available. On 13 January the stock rose 57% in a day on 15 times its normal volume. On 27 January it closed at $86.88, almost twenty times its price of three weeks earlier.

```series
title: GameStop — the January 2021 short squeeze
from: 2020-10-01
to: 2021-03-31
tf: D
line: us:GME | GameStop (split-adjusted) | log
line: us:GME@sma50 | 50-day average
line: us:GME@vol | Volume | pane2 bars
mark: 2021-01-13 | +57% in a day
mark: 2021-01-27 | close 86.88
mark: 2021-02-04 | close 13.38
caption: A twentyfold rise in three weeks, then an 85% fall in six sessions. Prices are split-adjusted; the actual prices were four times higher.
```

That is a short squeeze. A short seller has borrowed shares and sold them, and must buy them back one day. When the price rises, the short's loss grows without limit.

Brokers ask for more margin. Some shorts buy back to stop the pain; others are forced to. Every buy-back pushes the price higher, which hurts the remaining shorts.

In January 2021, a large crowd of small buyers using call options added to the pressure. One hedge fund that was short, Melvin Capital, needed an emergency investment of $2.75 billion from two other firms.

A **bear-market rally** works the same way, at the level of the whole market. After a long fall, many traders are short or holding cash. Some good news, or simply the end of forced selling, starts a rise. Shorts cover, cash comes back in, and the index jumps 10–20% in weeks. Then the reasons for the bear market reassert themselves and the fall resumes.

Who is on the other side? In a squeeze, the buyers are short sellers who *must* buy, whatever the price. That is what makes squeezes so fast: the buyers are not choosing. In a bear rally, the sellers into the rise are holders who were waiting for a chance to get out at a better price.

## 2. When it works and when it doesn't

**Squeezes need fuel.** The fuel is short interest — the number of shares sold short — compared with the shares that trade. Two measures are common in the US:

- **Short interest as a share of the free float.** Above about 20% is high; above 40% is extreme.
- **Days to cover.** Short interest divided by average daily volume. Above 5–10 days means the shorts cannot all get out quickly.

High short interest alone does not cause a squeeze. It needs a trigger: better results, a takeover bid, a big buyer, or a crowd deciding to push the price.

**Bear rallies are common in long bear markets and rare in short ones.** The table in §8 shows it. The long declines that began in 1929, 2000 and 2007 each had several large rallies. The fast crash of 2020 had none before its bottom.

**India.** Retail traders cannot hold a short in cash overnight, so stock shorts are held mainly in futures. A squeeze in India often shows up as a fast rise with falling open interest in the futures (shorts closing) near expiry. Exchange rules damp some squeezes: a stock in the derivatives ban period allows no new positions, and price bands stop smaller stocks at 5%, 10% or 20% a day. The flip side is that a short in a stock locked at its upper band cannot be covered that day. Nifty bear rallies are just as sharp as US ones; see the 2008 example in §6.

**US.** Short interest is published twice a month. Borrow fees rise as a squeeze builds, and a broker may recall shares, forcing you to cover. Options can add fuel: when many traders buy calls, the dealers who sold them buy shares to hedge.

## 3. The rules

This guide has two sets of rules: defence for a short, and a long trade on a bear-market rally.

### Universe and filters

- **Short defence:** applies to every short you hold.
- **Bear-rally long:** an index (Nifty 50, Nifty 500, S&P 500, Nasdaq 100) or a liquid index fund, ETF or index future. Single stocks are more volatile; trade them only with smaller size.
- The index is in a bear market: at least 20% below its record close, and below a 200-day average that is lower than 20 sessions ago.

### Setup — short defence

Avoid, or size down, a short when any of these is true:

1. Short interest is above 20% of the free float (US), or futures open interest is near the market-wide limit (India).
2. Days to cover is above 5.
3. The borrow fee has more than doubled in a month.
4. The stock has a known catalyst in the next 10 sessions: results, a court ruling, a vote.
5. The stock is more than 40% below its 52-week high. Very beaten-down stocks rebound hardest.

### Setup — bear-rally long

1. The index is in a bear market (above).
2. It has fallen at least 10% in the last 30 sessions.
3. A **rally attempt** has started: the index closes higher after making a new low for the decline.
4. On day 4 or later of the attempt, the index rises at least 1.5% on higher volume than the day before. William O'Neil calls this a **follow-through day**.

### Entry

- **Bear-rally long:** buy at the close of the follow-through day, or the next open.
- **Short defence:** this is about exits; see below.

### Initial stop

- **Bear-rally long:** just below the low of the rally attempt (the new low that started it).
- **Short:** above the last rally high, as in [the Stage 4 guide](learn-strat-stage4-shorts.md). Never move it up.

### Exits

- **Bear-rally long target:** the falling 50-day average first, then the falling 200-day average. Many bear rallies stall at one of them. Take half at the first, the rest at the second or on the stop.
- **Bear-rally long time stop:** 30 sessions. Bear rallies are short.
- **Short, squeeze exit:** cover at once if the stock gains more than 3 ATR in a day on more than 3 times average volume. Cover if it closes above its 50-day average with short interest above 20%.
- **Short, profit protection:** after a fall of 2R or more, tighten the stop to the highest high of the last 5 sessions.

### Position size

- **Bear-rally long:** risk 0.5% of the account. Bear-market volatility is high, so the position will be smaller than usual for the same risk.
- **Short:** risk 0.5% or less per short, and keep total short risk under 3%. Assume a squeeze can gap the price 30% past your stop.

### Managing the trade

- A bear-rally long is a trade, not an investment. Exit on the plan, even if the news sounds better.
- If the rally carries the index back above a *rising* 200-day average, the bear market may be over. Move to your normal long rules.
- For shorts, check short interest and borrow fees every week.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Bear market | 20% below the record close | When the long rules apply | 15–25% |
| Trend average | 200-day, falling over 20 sessions | Bear regime | Use the same as your regime filter |
| Prior fall | 10% in 30 sessions | Enough selling to fuel a rally | 7–15% |
| Follow-through day | Day 4 or later; +1.5% on higher volume | Entry | O'Neil used about 1% in older work, higher later |
| Rally target | Falling 50-day, then falling 200-day | Exit | Fixed 10–15% targets also work |
| Time stop | 30 sessions | Exit | 20–40 |
| Short-interest cap | 20% of float | Avoid crowded shorts | 10–30% |
| Days to cover cap | 5 | Avoid crowded shorts | 3–10 |
| Beaten-down cap | 40% below the 52-week high | Avoid shorting near the bottom | 30–50% |
| Squeeze exit | +3 ATR in a day on 3× volume | Cover a short | 2–4 ATR |
| Profit-protection trail | 5-session high after 2R | Lock in | 3–10 sessions |
| Risk per trade | 0.5% of account | Size | 0.25–1% |
| Total short risk | 3% of account | Exposure | 2–5% |

## 5. Variations

**O'Neil's follow-through day.** In *How to Make Money in Stocks*, O'Neil says a new uptrend is confirmed when, on day four or later of a rally attempt, a major index rises strongly on higher volume. He also says that many follow-through days fail, but that no new bull market started without one. Here we use it only to time a trade, not to declare a new bull market.

**Fading the rally.** Some short sellers wait for bear rallies and short them as they reach the falling 50-day or 200-day average. That is the Stage 4 entry B in [the Stage 4 guide](learn-strat-stage4-shorts.md), applied to an index.

**Trading the squeeze long.** Some traders buy heavily shorted stocks on a breakout, hoping for a squeeze. It is a crowded, fast game. The price can fall back as fast as it rose, as GameStop did.

**Historic squeezes.**
- **Northern Pacific, May 1901.** Two groups fighting for control bought up the shares. Short sellers could not find stock to return, and the price reportedly reached $1,000 a share for a moment. It helped set off a market panic.
- **Volkswagen, October 2008.** Porsche disclosed that it controlled about three-quarters of VW's ordinary shares, partly through options. With a state government holding much of the rest, almost no shares were left for the shorts. For a day VW was briefly the world's most valuable company.
- **GameStop, January 2021.** See §1 and §6.

Allen, Litov and Mei (2006) studied such **corners** — cases where one group controls the supply that shorts need — and found that they move prices far from value.

## 6. Worked examples

### GameStop, January 2021 — a squeeze from the short side (US)

The chart is in §1. All prices are split-adjusted.

| Step | Date | What happened |
|---|---|---|
| Fuel | Dec 2020 – Jan 2021 | Reported short interest above 100% of the free float |
| Trigger | 13 Jan 2021 | +57% in a day, to 7.85, on 15× volume |
| Defence rule | 13 Jan 2021 | Squeeze exit (+3 ATR, 3× volume) fires: cover |
| Peak close | 27 Jan 2021 | 86.88 |
| Brokers restrict buying | 28 Jan 2021 | Intraday range 28.06 to 120.75 |
| Collapse | 4 Feb 2021 | 13.38, 85% below the peak close |

A short who followed the defence rules would have been out on 13 January with a loss. That loss was large for one day, but it was a fraction of what came next. A short who held faced a twentyfold rise. The defence rule in §3 would also have kept most traders out from the start: short interest above 20% of the float.

### S&P 500, 2022 — two bear-market rallies (US)

```series
title: S&P 500 — two bear-market rallies in 2022
from: 2021-10-01
to: 2023-03-31
tf: D
line: us:SP500_PRICE_LONG | S&P 500 | log
line: us:SP500_PRICE_LONG@sma200 | 200-day average
line: us:SP500_PRICE_LONG@sma50 | 50-day average
band: 2022-03-08 2022-03-29 | +11%
band: 2022-06-16 2022-08-16 | +17%
mark: 2022-10-12 | bear-market low
caption: The June–August rally gained 17% and stopped almost exactly at the falling 200-day average. The index then fell to a new low in October.
```

| Step | Date | What happened |
|---|---|---|
| Bear market | Jan–Jun 2022 | Index 24% below its January record by 16 June |
| Rally low | 16 Jun 2022 | Close 3,667 |
| Peak of rally | 16 Aug 2022 | Close 4,305, with the 200-day at 4,326 |
| Gain | — | +17.4% in 41 sessions |
| End | 12 Oct 2022 | New low at 3,577 |

A long trade on this rally, with the 200-day as the target, would have caught most of it. A short who had shorted the June low and held would have lost 17% on the index — far more on the weakest stocks. The earlier March rally (+11.1%) ended just above the 200-day average.

### Nifty 50, 2008 — three rallies on the way down (India)

```series
title: Nifty 50 — bear-market rallies in 2008
from: 2007-10-01
to: 2009-06-30
tf: D
line: india:NIFTY50 | Nifty 50 | log
line: india:NIFTY50@sma50 | 50-day average
band: 2008-01-22 2008-02-05 | +12%
band: 2008-03-17 2008-05-02 | +16%
band: 2008-07-16 2008-08-11 | +21%
mark: 2008-10-27 | low 2,524
caption: Three rallies of more than 10% each, between the January record and the October low. Each ended below the previous peak.
```

| Rally | Start (close) | End (close) | Gain |
|---|---|---|---|
| 1 | 22 Jan 2008: 4,899 | 5 Feb 2008: 5,484 | +11.9% |
| 2 | 17 Mar 2008: 4,503 | 2 May 2008: 5,228 | +16.1% |
| 3 | 16 Jul 2008: 3,817 | 11 Aug 2008: 4,620 | +21.1% |

The record close was 6,288 on 8 January 2008. The low was 2,524 on 27 October, 60% lower. The August rally took the index well above its 50-day average, then at 4,307. It stopped below the 200-day, then at 5,101. Each rally felt like a bottom at the time.

### Nifty 50, 2020 — the rally that was not a bear rally (India, the failure)

```series
title: Nifty 50 — the March 2020 low and the rally that kept going
from: 2019-10-01
to: 2021-03-31
tf: D
line: india:NIFTY50 | Nifty 50 | log
line: india:NIFTY50@sma200 | 200-day average
line: india:INDIAVIX | India VIX | pane2
mark: 2020-03-23 | low 7,610
mark: 2020-04-30 | 9,860
caption: Anyone who treated the April 2020 rally as a bear rally to short was wrong. The index rose 84% from the low by the end of the year.
```

| Step | Date | What happened |
|---|---|---|
| Record | 14 Jan 2020 | Close 12,362 |
| Low | 23 Mar 2020 | Close 7,610, 38% below the record |
| Rally | 30 Apr 2020 | Close 9,860, +29.6% from the low |
| Year end | 31 Dec 2020 | Close 13,982, +83.7% from the low |

On 30 April the rally looked like those of 2008. It was fast, it came after a crash, and the index was still below its 200-day average (about 11,200). Shorting it at the falling average would have failed. The long rules in §3 would have worked, and the "manage" rule would have kept the trade once the index rose above a rising 200-day. This is the case the rules must survive: you cannot know which kind of rally you are in.

## 7. Common mistakes

- **Shorting the most-shorted stocks.** They are the ones that squeeze. Crowded is dangerous, not safe.
- **Adding to a losing short.** In a squeeze the price can double before you can act.
- **Calling the bottom on a bear rally.** Most 10% rallies inside long bear markets ended at a lower high. Trade them; do not marry them.
- **Calling a bear rally on a real bottom.** 2020 shows the opposite error. Use stops on both sides.
- **No stop on a short because "it is overvalued".** Overvalued stocks can become much more overvalued.
- **Holding a short through a known catalyst.** Results and court rulings are common squeeze triggers.

## 8. What the evidence says

**Published research.**
- **Short interest.** Desai and co-authors (2002) and Asquith, Pathak and Ritter (2005) found that heavily shorted stocks, on average, did worse afterwards. Shorts are not usually wrong. But the average hides rare, very large losses: a squeeze.
- **Corners and squeezes.** Allen, Litov and Mei (2006) studied historic corners and found large price distortions that hurt short sellers.
- **Rebounds of losers.** Daniel and Moskowitz (2016) found that after a market fall, when volatility is high, the past losers rebound much more than the winners. That is when shorting weak stocks loses most.
- **Correlations in falls.** Longin and Solnik (2001) found that markets move together more in falls than in rises. In a bear rally, almost everything rises at once.

**Event study 1 — bear-market rallies in indices.** We took every episode in which an index fell at least 20% from a record close. Between the record and the final low, we counted rallies of 10% or more, using closes (a rally ends when the index falls 10% from its high).

| Index | Record → low | Fall | Rallies of 10%+ | Largest |
|---|---|---|---|---|
| S&P 500 | Sep 1929 → Jun 1932 | −86% | 10 | +31% |
| S&P 500 | Aug 1956 → Oct 1957 | −22% | 1 | +16% |
| S&P 500 | Dec 1961 → Jun 1962 | −28% | 0 | — |
| S&P 500 | Feb 1966 → Oct 1966 | −22% | 0 | — |
| S&P 500 | Nov 1968 → May 1970 | −36% | 0 | — |
| S&P 500 | Jan 1973 → Oct 1974 | −48% | 2 | +11% |
| S&P 500 | Nov 1980 → Aug 1982 | −27% | 2 | +12% |
| S&P 500 | Aug 1987 → Dec 1987 | −34% | 2 | +15% |
| S&P 500 | Mar 2000 → Oct 2002 | −49% | 4 | +21% |
| S&P 500 | Oct 2007 → Mar 2009 | −57% | 4 | +24% |
| S&P 500 | Feb 2020 → Mar 2020 | −34% | 0 | — |
| S&P 500 | Jan 2022 → Oct 2022 | −25% | 2 | +17% |
| Nasdaq 100 | Mar 2000 → Oct 2002 | −83% | 13 | +52% |
| Nasdaq 100 | Dec 2021 → Nov 2022 | −35% | 2 | +23% |
| Nifty 50 | Jan 2008 → Oct 2008 | −60% | 3 | +21% |
| Nifty 50 | Nov 2010 → Dec 2011 | −28% | 2 | +13% |
| Nifty 50 | Mar 2015 → Feb 2016 | −23% | 0 | — |
| Nifty 50 | Jan 2020 → Mar 2020 | −38% | 0 | — |

*What it shows.* Long, deep bear markets contain several rallies of 10–30%. The Nasdaq index had 13 of them in its 2000–02 decline. Two were above 50%. Short, sharp falls had none.

Episodes are measured from a record close, so a bear market inside an earlier one (such as 1937–42) is part of the 1929 episode. The S&P data start in 1928, the Nasdaq data in 1999 and the Nifty data in 2007.

**Event study 2 — sharp rallies in falling stocks.** We looked for squeeze-like rallies in liquid stocks from 2012 to mid-2025. The stock was at least 40% below its 52-week high and below a falling 150-day average. It then rose at least 30% in 10 sessions. Liquid means a median daily traded value of at least ₹10 crore or $10 million.

| | India, all | India, without 2020 | US, all | US, without 2020 |
|---|---|---|---|---|
| Rallies | 170 | 109 | 1,998 | 1,319 |
| Median return over the next 60 sessions | +5.2% | −5.1% | +2.0% | −7.0% |
| Share lower 60 sessions later | 42% | 62% | 48% | 60% |
| Share that gave back half the rally within 60 sessions | 22% | 32% | 31% | 42% |
| Share back below the rally's start within 60 sessions | 9% | 15% | 18% | 25% |
| Share above the 150-day average 120 sessions later | 58% | 43% | 58% | 47% |

*What it shows.* In normal years, most sharp rallies in falling stocks faded: the price was lower 60 sessions later about 60% of the time. In 2020, which supplied 61 of the Indian and 679 of the US cases, they were the start of a new uptrend. The average depends on which kind of year you are in. That is the honest answer to "will this rally last?"

*Caveats.* The stock lists are today's, so failed companies are partly missing. Events cluster in a few years, so they are not independent. No costs are included.

**What is unknown.** No reliable signal separates a bear rally from a new bull market on the day it starts. Breadth and the follow-through day help, but both fail often.

## 9. Building and testing it yourself

**Data.** Daily index closes and volume; daily stock prices. For short defence in the US, short-interest history (twice a month) and borrow fees, which are hard to find for free. For India, futures open interest and the ban list.

**Look-ahead traps.**
- A bear market is known only once the index is 20% down. Do not label the whole decline from the record.
- Short interest is published with a delay of about two weeks. Use it from the publication date.
- The rally's low is known only after the rally starts. The stop uses the lowest close up to the entry day.

**Survivorship.** Stocks that were squeezed and later collapsed may be delisted. Use a database that keeps them.

**Costs (approximate).**
- India, index futures: brokerage about ₹20 per order; STT 0.05% on the sell side (since April 2026); stamp duty about 0.002% on the buy side. Index ETFs: STT of 0.001% on the sale of equity ETF units, far below the 0.1% each side on shares; check your fund.
- US: index ETFs cost little to trade. Shorts pay borrow fees and dividends.
- In bear markets spreads widen and gaps are larger. Add slippage of 0.1–0.2% per side to a test.

**Over-fitting.** Bear markets are rare: about a dozen in a century of US data, and three or four in Indian data. Any rule tuned to them is tuned to a handful of cases. Keep the rules simple, test on several indices and countries, and expect large errors.

**What a good test reports.** Each bear market separately, not just the total. For short defence: how many squeezes the rules avoided, and how many good shorts they skipped.

```
bear[t] = close[t] <= 0.8 * max(close[0 .. t]) and sma200[t] < sma200[t-20]

rally attempt: bear[t] and close[t] > close[t-1] after a new low L for the decline
follow-through: day k >= 4 of the attempt, close[k] / close[k-1] - 1 >= 0.015
                and volume[k] > volume[k-1]
long at open[k+1], stop just below L
exit half at the falling sma50, rest at the falling sma200, or on the stop, or after 30 days

short defence (each day, each short):
  if close / close[-1] - 1 > 3 * atr14 / close[-1] and volume > 3 * avg_volume50: cover
  if short_interest_pct_float > 0.20 and close > sma50: cover
```

## 10. Checklist

**Before and during a short**
- [ ] Short interest below 20% of float; days to cover below 5; borrow fee stable.
- [ ] No catalyst in the next 10 sessions.
- [ ] The stock is not already more than 40% below its 52-week high.
- [ ] Risk 0.5% or less; total short risk under 3%; stop order in the market.
- [ ] I will cover on a +3 ATR day on 3× volume.

**Before a bear-rally long**
- [ ] The index is in a bear market and fell 10% or more in the last 30 sessions.
- [ ] A follow-through day: day 4 or later, +1.5% on higher volume.
- [ ] Stop below the rally's low; targets at the falling 50-day and 200-day; 30-session time stop.
- [ ] If the index gets above a rising 200-day, I switch to my normal long rules.

## Further reading

- William J. O'Neil, *How to Make Money in Stocks* (4th ed., 2009).
- Edwin Lefèvre, *Reminiscences of a Stock Operator* (1923).
- Franklin Allen, Lubomir Litov and Jianping Mei, "Large Investors, Price Manipulation, and Limits to Arbitrage: An Anatomy of Market Corners", *Review of Finance* 10 (2006).
- Paul Asquith, Parag A. Pathak and Jay R. Ritter, "Short Interest, Institutional Ownership, and Stock Returns", *Journal of Financial Economics* 78 (2005).
- Hemang Desai, K. Ramesh, S. Ramu Thiagarajan and Bala V. Balachandran, "An Investigation of the Informational Role of Short Interest in the Nasdaq Market", *Journal of Finance* 57 (2002).
- Kent Daniel and Tobias J. Moskowitz, "Momentum Crashes", *Journal of Financial Economics* 122 (2016).
- François Longin and Bruno Solnik, "Extreme Correlation of International Equity Markets", *Journal of Finance* 56 (2001).
- Charles P. Kindleberger, *Manias, Panics, and Crashes* (first published 1978).
