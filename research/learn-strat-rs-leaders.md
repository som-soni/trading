# Relative-strength leaders — buying the strongest stocks in the strongest groups after a correction

**In short**

- After a market correction, the swing trader looks for stocks that held up best, sit near their highs, and belong to the strongest industry groups. They buy those stocks as they break out of a base, with a tight stop.
- The idea comes from William O'Neil and Mark Minervini: the next advance is usually led by stocks that showed strength during the fall.
- It differs from systematic momentum: one stock at a time, entered on a chart trigger, with a stop, held for weeks to a few months.
- The evidence is mixed. In India, leaders in strong groups beat the typical stock in 9 of 13 recoveries since 2009 over three months. In the US, leaders lagged in 6 of 7 recoveries. Much of any edge has to come from the trade management, not the selection.
- Gaps through the stop are the main risk. On 7 April 2025 several Indian leaders opened far below their stops.

---

## 1. The idea

The Nifty 500 fell 18.8% from 26 September 2024 to 28 February 2025. On 20 March 2025 it had recovered more than 5% from its low and closed above its 50-day average. On that day Bharat Electronics (BEL), a defence electronics maker, had an RS rank of 80. The RS rank is a stock's score from 1 to 99 for its recent return against all other stocks. BEL was 11.5% below its 52-week high, and its industry, aerospace and defence, was among the strongest groups in the market.

```series
title: Bharat Electronics through the 2024–25 correction
from: 2024-08-01
to: 2025-09-30
line: india:BEL.NS | BEL | log
line: india:BEL.NS@sma50 | 50-day average
line: india:BEL.NS / india:NIFTY500 | RS line: BEL ÷ Nifty 500 | pane2
band: 2024-09-26 2025-02-28 | Nifty 500 −18.8%
mark: 2025-04-29 | breakout
mark: 2025-07-18 | close below the 50-day
caption: The stock broke out on 29 April 2025 on 2.6 times its average volume. It was sold on 18 July, 27% above the entry.
```

On 29 April the stock rose above the highest high of the previous three weeks on more than twice its average volume. That was the entry. The stop went 8% below. It was sold on 18 July, the first close below its 50-day average. The exit price was 27.2% above the entry (§6).

That is the **relative-strength leader** trade. The reasoning behind it:

- **Strength in a fall shows demand.** A stock that falls less than the market, or rises, while everything else is sold, has buyers who are not leaving. Often they are institutions building a position.
- **Leaders cluster.** Strong stocks tend to come from a few strong groups, because one driver (a policy, a price, a product cycle) lifts the whole group. See [sectors and groups](learn-sectors-groups.md).
- **The first stocks to new highs often lead.** O'Neil found that the biggest winners of each cycle usually broke out early in a new market uptrend.

The measures used here, the RS line and the RS rank, are explained in [the relative strength guide](learn-price-rs.md). The bases and pivots are in [the bases guide](learn-bases.md).

**Who is on the other side.** Sellers who bought lower and take profits at the old highs. Investors who think a stock "has run too far" after holding up in a fall. And bottom-fishers who prefer the stocks that fell most. Sometimes the bottom-fishers are right (§8).

**How it differs from systematic momentum.**

| | Systematic momentum | RS leaders (this guide) |
|---|---|---|
| Unit | A portfolio of 20–30 stocks | One stock at a time |
| Selection | Rank on 12-month return | RS rank plus chart, group and market condition |
| Entry | On a calendar date | On a breakout from a base |
| Stop | None (monthly re-rank) | Tight: 5–8% below entry |
| Holding period | Months | Weeks to a few months |
| When it is used | Always invested | Mainly in the first months after a correction |
| Source of edge | Average of many stocks | Selection plus cutting losers fast and letting winners run |

The calendar version is in [cross-sectional momentum](learn-strat-xs-momentum.md).

## 2. When it works and when it doesn't

**It works best in the first months of a broad new uptrend** after a correction of 10–25%, when the leadership is clear and the market keeps rising. India in mid-2022 and spring 2023 are good examples (§8).

**It works badly after a crash with a violent rebound.** After March 2009 and March 2020, the stocks that fell most bounced most. The leaders, often defensive stocks, lagged. The same reversal drives the momentum crashes in [cross-sectional momentum](learn-strat-xs-momentum.md).

**It works badly when the "strength" was only defensiveness.** In a falling market, utilities, staples, gold miners and drug makers often hold up. That is low beta, not new demand. When the market turns, money returns to the stocks that fell most. The relative strength guide shows this for the 2022 and 2025 US sell-offs.

**It fails when the market's recovery fails.** A breakout bought in a rally that rolls over gets stopped out. That happened in India in April 2018 and November 2018 (§8).

**India notes.**

- **Price bands.** Many stocks outside the derivatives segment have daily price bands of 5%, 10% or 20%. A stock locked at its upper band cannot be bought; one locked at the lower band cannot be sold. Stocks in the F&O segment have no fixed band but are still subject to market-wide circuit breakers.
- **T+1 settlement.** Shares bought today are delivered the next day. Selling before delivery (BTST) carries a risk of short delivery.
- **Shorting.** In the cash market, shorts must be closed the same day. A swing trader who wants to hedge or short needs futures or options (see the Futures & options section).
- **Gaps.** Indian stocks open after the US session and after overnight news. On 7 April 2025, a global sell-off over US tariffs opened many leaders far below their stops.

## 3. The rules

### Universe and filters

- Price at least ₹50 (India) or $10 (US).
- Average daily traded value over 50 sessions at least ₹20 crore (India) or $20 million (US). In practice that is the 300 (India) or 1,000 (US) most-traded stocks.
- Not under exchange surveillance (ASM or GSM) and not in the trade-for-trade segment (India).
- No results announcement in the next 5 sessions, unless you accept the gap risk.

### Setup

**Market condition (all must hold):**

1. The broad index (Nifty 500 or S&P 500) fell at least 10% from its high, closing basis.
2. Since its lowest close, it has risen at least 5% and closes above its 50-day average. Call the first day this holds the **confirmation day**.
3. It is no more than 40 sessions since the confirmation day. After that, treat the market as an ordinary uptrend.

**Stock condition (on the day of the trade):**

1. **RS rank at least 80.** RS score = 40% of the 3-month return + 20% each of the 6-, 9- and 12-month returns. Rank it from 1 to 99 within the universe.
2. **Near its high:** the close is within 15% of the 52-week high.
3. **RS line strong:** the stock ÷ index line is within 2% of its own 52-week high.
4. **Trend:** the close is above the 50-day average, and the 50-day is above the 200-day.
5. **Strong group:** the stock's industry has at least 4 stocks in the universe, and its median RS rank is in the top 20% of industries.

**Base:** in the last 15–40 sessions the stock has moved sideways, with a high-to-low depth of no more than 25%. The **pivot** is the highest high of the last 15 sessions.

```pattern
flat-base
```

### Entry

- Place a buy-stop order just above the pivot.
- Fill price = the pivot, or the open if the stock gaps above it.
- The breakout day's volume must be at least 1.4 times the 50-day average volume. If it is not, sell at the close or the next open.
- Do not buy more than 5% above the pivot. If the stock is already further away, wait for the next base.

### Initial stop

- Stop = the lowest low of the 10 sessions before the breakout, but never more than 8% below the entry.
- Place it as a stop-loss order in the market where your broker allows it. In India, a stop-loss limit order may not fill in a gap; a stop-loss market order will, at the gap price.

### Exits

- **Stop:** sell if the low touches the stop. In a gap down, you are filled at the open, below the stop.
- **Trend exit:** sell on the first close below the 50-day average.
- **Optional partial profit:** sell a third at +20–25% (O'Neil's rule of thumb). Keep the rest under the trend exit.
- **Optional time stop:** if the stock is not at least 5% above the entry after 15 sessions, sell.
- **Invalidation:** sell if the RS line makes a 3-month low while you hold the stock.

### Position size

- Risk 0.5–1% of the account on each trade: shares = (account × risk %) ÷ (entry − stop).
- No single position above 20–25% of the account.
- At most two positions from one industry group.
- Start with 2–3 positions in the first weeks after the confirmation day. Add more only if the first ones work. See [position sizing](learn-risk-sizing.md).

### Managing the trade

- After the stock is 2R above the entry, raise the stop to the entry price. R is the distance from entry to initial stop.
- Do not add to a position that is below its entry price.
- If the index closes back below its 50-day average and breaks its correction low, close all new positions. The market condition has failed.
- Review every holding's group each week. If the group's RS falls out of the top half, tighten the stop. More on exits in [stops and exits](learn-risk-stops-exits.md).

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Correction size | 10% (range 8–20%) | Which market falls count | Bigger thresholds give fewer, clearer episodes |
| Confirmation | +5% off the low and above the 50-day | When to start buying | O'Neil's follow-through day is an alternative |
| Trading window | 40 sessions after confirmation | How long the setup applies | Beyond this it is a normal breakout strategy |
| RS rank minimum | 80 (range 70–90) | Strength of candidates | Higher means fewer names |
| RS weights | 40/20/20/20% on 3/6/9/12 months | What "strong" means | A 12-1 rank gives a slower list |
| Distance from 52-week high | Within 15% (range 10–25%) | Leadership | Closer means fewer but stronger |
| RS line near its high | Within 2% | Fresh relative strength | Tighter excludes many good stocks |
| Group strength | Top 20% of industries | Group support | Top 30–40% gives more names |
| Minimum group size | 4 stocks | Noise in the group measure | Small groups swing on one stock |
| Base length | 15–40 sessions | Setup quality | Shorter bases fail more often |
| Base depth | 25% or less | Setup quality | Deep bases need more time to repair |
| Pivot lookback | 15 sessions | Entry level | 10–20 sessions give similar pivots |
| Breakout volume | 1.4 times the 50-day average | Demand on the breakout | Higher means fewer, stronger signals |
| Maximum chase | 5% above the pivot | Entry price | Buying far above the pivot widens the stop |
| Initial stop | 10-session low, at most 8% | Loss per trade | O'Neil's limit is 7–8% |
| Trend exit | Close below the 50-day | Holding period | The 21-day EMA is faster; the 10-week line slower |
| Partial profit | Sell a third at +20–25% | Locks in gains | Optional |
| Time stop | +5% within 15 sessions | Dead money | Optional, untested here |
| Risk per trade | 0.5–1% of the account | Drawdown | The main risk control |
| Position cap | 20–25% of the account | Concentration | Limits gap losses |
| Positions per group | 2 at most | Correlation | |

## 5. Variations

- **William O'Neil (CAN SLIM).** Buy stocks with RS ratings of 80 or more, strong earnings and a leading group, as they break out of a proper base. Act only after a **follow-through day**: a day, usually four or more sessions into a rally attempt, when a major index rises strongly on higher volume than the day before. Cut every loss at 7–8%. Described in *How to Make Money in Stocks*.
- **Mark Minervini (SEPA).** Uses a "trend template" (price above rising 150- and 200-day averages, near the 52-week high, well above the low, high RS) and buys volatility contraction patterns. He stresses that leaders often show strength during the correction, and are among the first to new highs afterwards. See *Trade Like a Stock Market Wizard*.
- **Stan Weinstein.** Buys stocks breaking into Stage 2 (a rising 30-week average) with RS turning positive, in a strong group. See *Secrets for Profiting in Bull and Bear Markets* and [price stages](learn-price-stages.md).
- **Investor's Business Daily's RS rating.** A 1–99 rank that weights the latest quarter twice, close to the score in §3.
- **RS line new high before the price.** Some traders buy only when the RS line reaches a new high before the price does. The relative strength guide tests that signal.

## 6. Worked examples

The rules in §3 applied to stocks that were leaders on a confirmation day. Prices are split-adjusted daily data, before costs. R is the initial risk per share.

### India, success: Bharat Electronics, 2025

1. **Market:** the Nifty 500 fell 18.8% to 28 February 2025. The confirmation day was 20 March.
2. **Stock on 20 March:** RS rank 80, 11.5% below its 52-week high, in a top-20% group (aerospace and defence).
3. **Entry:** the price passed the 15-day pivot on 29 April at ₹310.3. Volume was 2.6 times the 50-day average.
4. **Stop:** 8% below, at ₹285.5.
5. **What happened:** the stock reached a closing high of ₹432.2 on 1 July.
6. **Exit:** first close below the 50-day average, on 18 July, at ₹394.8. Result: +27.2%, or +3.4R.

### India, failure: JSW Steel, 2025

```series
title: JSW Steel — a leader stopped out by a gap
from: 2025-01-01
to: 2025-06-30
line: india:JSWSTEEL.NS | JSW Steel
line: india:JSWSTEEL.NS@sma50 | 50-day average
line: india:JSWSTEEL.NS@vol | Volume | pane2 bars
mark: 2025-03-21 | breakout entry
mark: 2025-04-07 | opened below the stop
caption: Bought on a breakout to a 52-week high on 21 March 2025. The stop was 5.6% below. On 7 April the stock opened 13.9% below the entry, in a worldwide sell-off.
```

1. **Stock on 20 March:** RS rank 85, at its 52-week high, RS line at a high, in a top-20% group (steel).
2. **Entry:** 21 March 2025, at the pivot of ₹1,052.8, on 1.5 times average volume.
3. **Stop:** the 10-session low, ₹994.1 (5.6% risk).
4. **What happened:** on 7 April, a global sell-off over US tariffs opened the stock at ₹906.0.
5. **Exit:** at the open, −13.9%, or −2.5R. The stop limited nothing in a gap.

The same day stopped out other leaders bought after the same confirmation day, such as Lloyds Metals and Aavas Financiers. Gaps are why position size, not the stop alone, sets the real risk.

### India, a small win: Coromandel International, 2025

1. **Stock on 20 March:** RS rank 93, at its 52-week high, in a top-20% group (agricultural inputs).
2. **Entry:** the breakout on 15 April, at ₹2,175. Stop ₹2,001.
3. **What happened:** the best close was ₹2,492.1 on 19 May (+14.6%). Then the stock drifted back.
4. **Exit:** the first close below the 50-day, on 16 June, at ₹2,265.8. Result: +4.2%, or +0.5R.

The trend exit gave back most of the gain. A partial sale at +20% would not have triggered.

### US, success: Cardinal Health, 2025

```series
title: Cardinal Health after the April 2025 low
from: 2025-01-01
to: 2025-09-30
line: us:CAH | Cardinal Health
line: us:CAH@sma50 | 50-day average
line: us:CAH / us:SPX | RS line: CAH ÷ S&P 500 | pane2
mark: 2025-05-01 | confirmation day and breakout
mark: 2025-07-22 | close below the 50-day
caption: A drug distributor, in a strong group, at its 52-week high on the confirmation day. It rose 10.8% by the exit.
```

1. **Market:** the S&P 500 fell 18.9% to 8 April 2025. The confirmation day was 1 May.
2. **Stock on 1 May:** RS rank 92, at its 52-week high, RS line at a high, in a top-20% group (medical distribution).
3. **Entry:** 1 May, at the pivot of $141.7, on 1.5 times average volume. Stop $130.4.
4. **Exit:** close below the 50-day on 22 July at $157.1: +10.8%, or +1.4R. The best close was $168.0 on 30 June.

## 7. Common mistakes

- **Buying "strength" that is only defensiveness.** A utility that held up in a sell-off is not a growth leader. Check what kind of business it is and why it held up.
- **Buying before the market confirms.** Early buys during the fall often get stopped out in the last leg down.
- **Chasing extended stocks.** Buying 10–15% above the pivot puts the stop far away or makes it meaningless.
- **Ignoring the group.** A lone strong stock in a weak group gets less help.
- **Moving the stop down.** The stop is set before entry. It only moves up.
- **Too many positions at once.** The first weeks after a confirmation day are when failures cluster. Start small.
- **Too big a position.** A gap through the stop costs 2–3R. Size so that such a loss is survivable.
- **Treating the RS rank as a buy signal.** It is a filter. The chart setup and the market decide the timing.

## 8. What the evidence says

**Published and practitioner sources.** O'Neil's studies of past big winners (described in his books) found that most had high RS and led their groups before their large moves. That is a study of winners after the fact. It does not show how often stocks with those traits went on to win. The academic momentum research (Jegadeesh and Titman 1993, and many since) supports buying past winners on average. It also documents reversals after market crashes (Daniel and Moskowitz 2016).

**Event study: leaders on the confirmation day.**

*Method.*

| | India | US |
|---|---|---|
| Index | Nifty 500 | S&P 500 |
| Period | 2009–2025 | 2009–2025 |
| Stocks (most traded) | 300 | 1,000 |
| Episodes | 13 | 7 |

- Corrections: every fall of 10% or more in the index, measured on closes, with the low taken as the lowest close before a new index high. The low is known only afterwards, which is a mild look-ahead in choosing episode dates.
- Leaders: on each confirmation day (§3), among the most-traded stocks, an RS rank of 80 or more and within 15% of the 52-week high.
- Strong group: an industry (today's labels, at least 4 stocks) with a median RS rank in the top 20%.
- Returns: from the confirmation-day close over 3 and 6 months.
- Survivors only; no costs; no stops, so this tests selection, not the trade rules.

| Median of each episode's median return | India, 3 months | India, 6 months | US, 3 months | US, 6 months |
|---|---|---|---|---|
| All stocks in the universe | +11.2% | +10.4% | +9.1% | +11.3% |
| Leaders | +11.6% | +12.2% | +2.7% | +8.7% |
| Leaders with the RS line near its high | +14.5% | +11.2% | +3.8% | +7.9% |
| Leaders in strong groups | +17.2% | +12.2% | +2.0% | +8.5% |
| Weak stocks (RS rank below 50) | +10.9% | +12.3% | +12.4% | +10.4% |

| Episodes in which the group's median beat all stocks' median | India, 3 months | India, 6 months | US, 3 months | US, 6 months |
|---|---|---|---|---|
| Leaders | 6 of 13 | 6 of 13 | 1 of 7 | 2 of 7 |
| Leaders in strong groups | 9 of 13 | 7 of 13 | 1 of 7 | 2 of 7 |
| Weak stocks | 5 of 13 | 6 of 13 | 6 of 7 | 6 of 7 |

| Share of stocks with a big gain | India, +20% in 3 months | US, +20% in 3 months | US, +30% in 6 months |
|---|---|---|---|
| All stocks | 35% | 22% | 23% |
| Leaders in strong groups | 41% | 15% | 17% |

*What it shows.*

- **India:** leaders in strong groups did better than the typical stock over three months, in 9 of 13 recoveries. The gap shrank over six months. Leaders without the group condition were no better than average.
- **US:** leaders lagged the typical stock in almost every recovery, and were less likely to make a big gain. The weakest stocks did best. This matches the relative strength guide's three-episode study.
- **Where it failed in India:** the March 2009 and May 2020 rebounds (the beaten-down stocks rose most), and the November 2009 and January 2017 recoveries.
- **Where it worked in India:** July 2009, mid-2010, early 2012, March 2016, both 2018 recoveries (by losing less), July 2022, April 2023 and March 2025.

*What it does not show.* The test buys every leader on one day and holds without a stop. The strategy in §3 buys only breakouts, cuts losers at 8% or less, and lets winners run. Whether that management turns a neutral selection into a profitable strategy is the question your own test must answer. The three worked examples are illustrations, not evidence.

**What is unknown.** Why the US and India differ. Possible reasons include the sector mix of leaders (US leaders at these lows were often defensive), the stronger momentum effect in India generally, and chance with so few episodes.

## 9. Building and testing it yourself

**Data.**

- Daily open, high, low, close and volume, adjusted for splits and bonuses.
- An index series for the RS line and the market condition.
- Industry labels as they were at the time, if you can get them. Today's labels put companies into groups they may not have belonged to years ago.
- Delisted stocks, to avoid testing only the survivors.

**Look-ahead traps.**

- The correction's low is known only in hindsight. In a live test, the confirmation rule must work without knowing it was the low: any close 5% above the lowest close so far, above the 50-day.
- Fill at the pivot only if the open was below it. If the stock gapped above, the fill is the open.
- A stop hit in a gap fills at the open, not at the stop.
- Use RS ranks and group ranks computed from data up to the previous close.

**Costs (India, delivery trades, approximate).**

| Item | Approximate size |
|---|---|
| STT | 0.1% on the buy and 0.1% on the sell |
| Stamp duty | 0.015% on the buy |
| Exchange, SEBI, GST | about 0.01% in total |
| Brokerage | zero to 0.1% each side |
| Slippage on a breakout | 0.2–0.5%; breakouts attract many buy-stop orders |
| Gap slippage on stops | Measure it; it is the largest cost in this strategy |

**What to test.**

- RS rank 70, 80 and 90; distance from the high 10%, 15% and 25%; group in the top 20% and top 40%.
- Stop at 5%, 8% and the 10-day low.
- Trend exit on the 21-day EMA, the 50-day and the 10-week average.
- With and without the market condition, to see whether the "after a correction" timing adds anything.

**What a good test reports.** Win rate, average win and loss in R, and expectancy (see [expectancy](learn-risk-expectancy.md)). The number of trades per episode and by year. The worst losing streak. Gap losses separately from normal stop-outs. Results by market, and by episode, because a few recoveries will dominate.

```
on each day d:
    if not market_confirmed(index, d): continue      # >=10% fall, then +5% off the low and above the 50-day
    if sessions_since_confirmation(d) > 40: continue
    for stock s in universe(d):                     # liquidity, price, surveillance filters
        if rs_rank(s, d-1) < 80: continue
        if close(s, d-1) < 0.85 * high_52w(s, d-1): continue
        if rs_line(s, d-1) < 0.98 * rs_line_high_52w(s, d-1): continue
        if group_rank(s, d-1) < 80th percentile: continue
        pivot = max(high[s, d-15 .. d-1])
        if high(s, d) > pivot and volume(s, d) >= 1.4 * avg_volume_50(s, d-1):
            entry = max(pivot, open(s, d))
            if entry > 1.05 * pivot: continue
            stop = max(min(low[s, d-10 .. d-1]), 0.92 * entry)
            size = account * risk_pct / (entry - stop)
manage open trades daily:
    exit at min(open, stop) if low <= stop
    exit at close if close < sma50
```

## 10. Checklist

- [ ] The index fell 10% or more, and is now 5%+ off its low and above its 50-day average
- [ ] Fewer than 40 sessions since the confirmation day
- [ ] RS rank 80+, within 15% of the 52-week high, RS line within 2% of its high
- [ ] Above a rising 50-day, and the 50-day above the 200-day
- [ ] The group is in the top 20% of industries, and I hold at most one other stock from it
- [ ] Why did it hold up? Real demand, or just a defensive business?
- [ ] A proper base, no deeper than 25%, and a clear pivot
- [ ] Breakout volume at least 1.4 times average; entry no more than 5% above the pivot
- [ ] Stop set (10-day low, at most 8%), and the size risks 0.5–1% of the account
- [ ] No results in the next few sessions; a gap of twice the stop distance would still be survivable

## Further reading

- William J. O'Neil, *How to Make Money in Stocks*, McGraw-Hill (4th edition, 2009).
- Mark Minervini, *Trade Like a Stock Market Wizard*, McGraw-Hill, 2013.
- Mark Minervini, *Think & Trade Like a Champion*, Access Publishing, 2017.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets*, McGraw-Hill, 1988.
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance*, 1993.
- Kent Daniel and Tobias Moskowitz, "Momentum Crashes", *Journal of Financial Economics*, 2016.
- Related guides: [relative strength](learn-price-rs.md), [sectors and groups](learn-sectors-groups.md), [bases](learn-bases.md), [price stages](learn-price-stages.md), [cross-sectional momentum](learn-strat-xs-momentum.md), [sector rotation](learn-strat-sector-rotation.md).
