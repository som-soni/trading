# Post-earnings announcement drift — trading the slow reaction to results

**In short**

- After a results surprise, prices tend to keep moving in the direction of the surprise for weeks. This is **post-earnings announcement drift**, first documented in 1968.
- The trade buys stocks after strong, accelerating profit growth and a positive price reaction, and holds for about 60 trading days.
- Without analysts' forecasts you can still measure surprise: compare this quarter's growth with the same quarter a year ago and with last quarter's growth.
- In large US stocks the drift has mostly disappeared since the 2000s. On stored data since 2009 it was close to zero. In India since 2020 it was visible, on a short sample.
- Treat it as a ranking tool for choosing which stocks to hold, more than as a stand-alone trade.

This guide belongs to the event-driven group, with [earnings gaps and episodic pivots](learn-strat-earnings-gaps.md) and [index and news events](learn-strat-index-news-events.md). How to read a results report is covered in [earnings that move stocks](learn-fund-earnings.md).

## 1. The idea

### An example first

Polycab India, a cable and wire maker, reported its results for the June 2023 quarter on 18 July 2023. Net profit was ₹399.3 crore, up 81.7% on the same quarter a year earlier. In the previous quarter, profit growth had been 30.6%. So growth did not just stay high; it sped up by about 51 percentage points.

```series
title: Polycab India — drift after the results of 18 July 2023
from: 2023-04-01
to: 2023-11-30
line: india:POLYCAB.NS | Polycab India
line: india:POLYCAB.NS@sma50 | 50-day average
line: india:fund.POLYCAB.NS.eps_g | EPS growth, year on year (%) | pane2
mark: 2023-07-18 | Results: profit up 82%
caption: The stock rose about 5% on results day and kept rising for three months, while the Nifty 50 went sideways.
```

The stock rose 5.5% that day on about 7 times its normal volume. A buyer at the close of the next day, 19 July, paid 4,308.85. Sixty trading days later, on 16 October 2023, the stock closed at 5,420.50. That is 25.8%, while the Nifty 50 fell 0.5% over the same days.

### What the trade is

You rank stocks by how surprising their latest results were. You buy the most positive surprises a day or two after the announcement, and hold for a fixed period, usually one quarter. A long-short version also sells short the most negative surprises.

### Why it can work

Ray Ball and Philip Brown (1968) were the first to show that prices keep moving after results. Victor Bernard and Jacob Thomas (1989, 1990) showed the drift lasted about 60 trading days. Strikingly, part of it reappeared around the next results date. Their explanation: investors treat each quarter as if it were unrelated to the last. In fact a strong quarter makes the next quarter's year-on-year growth likely to be strong too.

So the market reacts to the surprise, but not by enough. The rest of the adjustment comes as analysts raise forecasts, funds rebalance, and the next quarter confirms the trend.

### Who is on the other side

The sellers are investors who anchor on the old price, holders who take profits after a jump, and traders who expect a gap to fade. The drift is their slow change of mind. In a well-followed stock, many fast investors trade the surprise within hours, and little drift is left.

## 2. When it works and when it doesn't

**Neglected and small companies.** The drift was always strongest in small stocks with few analysts and low trading volume. Those are the stocks where trading is most expensive. That is a large part of why the effect survives on paper.

**Its decline in the US.** Tarun Chordia and co-authors (2009) found that the drift had shrunk in liquid US stocks as trading became cheaper. Charles Martineau (2022) argued that in large US stocks it had largely disappeared since the mid-2000s. The event study below agrees: in liquid US stocks since 2009, there was almost nothing to trade.

**Market conditions.** In a falling market, a good quarter can still go down with everything else. The drift is about the stock relative to the market. So a long-only version works best in a rising market.

**India.** Fewer analysts cover Indian mid- and small-caps, and results come out in a crowded few weeks. Both should help the drift survive.

Indian companies must disclose results within 30 minutes of the board meeting ending, so results can arrive during the session or after it. Use the first full session after the disclosure as the reaction day. Long-only is practical: holding a short for 60 days needs stock futures, rolled each month. T+1 settlement and delivery costs apply (section 9).

**US.** The drift is more likely to show in smaller companies, with analysts' consensus forecasts as the surprise measure. Without consensus data, as in this guide, the signal is weaker.

## 3. The rules

### Universe and filters

- Price at least ₹50 or $5; 20-day average traded value at least ₹5 crore or $5 million.
- Profit in the same quarter a year earlier was positive. A growth rate from a loss is not meaningful.
- At least 8 quarters of results history.

### Setup

Measure the surprise without analysts' forecasts. Three measures, each a number per company per quarter:

- **Year-on-year growth (YoY):** (this quarter's net profit − the same quarter a year earlier) ÷ the same quarter a year earlier.
- **Acceleration:** this quarter's YoY growth minus last quarter's YoY growth.
- **Standardised surprise (SUE):** (this quarter's EPS − EPS a year earlier) ÷ the standard deviation of that difference over the last 8 quarters. This is the measure Bernard and Thomas used.

Here are the first two measures for Polycab India, from its net profit as reported (₹ crore):

| Quarter ended | Net profit | Same quarter a year earlier | YoY growth | Acceleration |
|---|---|---|---|---|
| March 2023 | 424.8 | 325.3 | +30.6% | |
| June 2023 | 399.3 | 219.8 | +81.7% | +51 points |

Profit fell from March to June, yet the surprise was large. Comparing a quarter with the one just before it would have given the wrong answer: many businesses are seasonal. Comparing with the same quarter a year earlier removes the season.

Rules:

- YoY profit growth at least 25% (*minimum growth*), and in the top fifth of all companies reporting that season.
- Acceleration above zero.
- Revenue growth at least 10%, so the profit rise is not only from cost cuts or one-off gains.
- The price reaction confirms it: the stock beat the index over the 2 sessions from the close before the results to the close after (*minimum reaction*, above 0%).

### Entry

- Buy at the close of the second session after the results, or the next open.
- Do not chase: skip if the reaction was above 20%. That is the episodic-pivot setup, with different rules (see [earnings gaps](learn-strat-earnings-gaps.md)).

### Initial stop

- A close below the reaction-day low. The surprise has been rejected.
- Or, for a portfolio held as a ranked list, no price stop, with a smaller position in each stock (see "Position size").

### Exits

- **Time exit:** sell after 60 sessions (*holding period*), or just before the next results date if it comes first.
- **Rank exit:** sell if the next quarter's growth falls out of the top two-fifths.
- **Stop:** as above.

### Position size

- With a stop: risk 0.5% of capital per position, sized from the stop.
- As a portfolio: equal weights across 10 to 20 positions, each at most 10% of capital.

### Managing the trade

Do not add after the entry. Read the next results before the date: if growth is slowing, decide whether to sell before the announcement. Holding through a results date means holding through a possible gap.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| *Minimum growth* | 25% (20–50%) | YoY profit growth | Top fifth started near +52% (US) and +58% (India) in the study |
| Acceleration | Above 0 (0–20 points) | Growth speeding up | Similar to growth alone in the study |
| SUE threshold | Top fifth or SUE above 2 | Standardised surprise | Needs 8 quarters of history |
| Revenue growth | 10% or more | Quality of the profit rise | Untested here |
| *Minimum reaction* | Above 0% (0–5%) | Market confirms the surprise | Helped in India, not in the US |
| Maximum reaction | 20% | Leaves big gaps to the gap strategy | |
| Entry delay | 2 sessions after results | Avoids the reaction-day noise | |
| *Holding period* | 60 sessions (20–120) | How long to hold | Bernard and Thomas found most drift in 60 days |
| Positions | 10–20 | Spread across stocks | Fewer positions means more luck |
| Risk per trade | 0.5% | With a stop | |

## 5. Variations

- **Analyst-based surprise.** Livnat and Mendenhall (2006) found that surprise measured against analysts' consensus produced a larger drift than surprise measured against last year's quarter. If you can get consensus data, use it.
- **Earnings-announcement return.** Some researchers rank by the price reaction alone: the stock's return over the 3 days around the results, minus the market. Chan, Jegadeesh and Lakonishok (1996) found both earnings surprise and price momentum predicted returns.
- **Revenue surprise.** Profits are easier to manage than sales, so some versions require a sales surprise too.
- **CAN SLIM.** William O'Neil's "C" (current quarterly earnings up at least 25%, ideally accelerating) uses the same idea as a filter for breakouts. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Long-short.** The academic version buys the top tenth and shorts the bottom tenth. In India the short side needs futures, available only for the larger stocks.

## 6. Worked examples

### Polycab India, July 2023 (India): it worked

| Step | Date | Value |
|---|---|---|
| Net profit, June 2023 quarter | Reported 18 Jul 2023 | ₹399.3 crore |
| Same quarter a year earlier | | ₹219.8 crore: growth 81.7% |
| Growth in the previous quarter | | 30.6%: acceleration about 51 points |
| Reaction | 18 Jul 2023 | +5.5% on about 7× normal volume |
| Entry | Close, 19 Jul 2023 | 4,308.85 |
| Exit after 60 sessions | 16 Oct 2023 | 5,420.50: +25.8% |
| Nifty 50 over the same days | | −0.5% |

### Macrotech Developers (Lodha), October 2025 (India): it failed

Lodha's profit for the September 2025 quarter was ₹788.7 crore, up 86.5% on a year earlier. Growth in the June quarter had been 41.9%, so acceleration was about 45 points. The stock rose 2.3% on 31 October 2025, on about 5 times normal volume, and another 3.1% the next session.

```series
title: Lodha — strong results, then a decline
from: 2025-08-01
to: 2026-03-31
line: india:LODHA.NS | Macrotech Developers (Lodha)
line: india:LODHA.NS@sma50 | 50-day average
line: india:fund.LODHA.NS.eps_g | EPS growth, year on year (%) | pane2
mark: 2025-10-31 | Results: profit up 86%
caption: Every surprise measure was positive, but the stock fell steadily after the results.
```

| Step | Date | Value |
|---|---|---|
| Entry | Close, 3 Nov 2025 | 1,235.10 |
| Exit after 60 sessions | 29 Jan 2026 | 951.40: −23.0% |
| Nifty 50 over the same days | | −1.3% |

With the stop rule, the trade would have ended much earlier, on the first close below the reaction-day low of 1,184.20. That came on 21 November 2025, at 1,176.80, a loss of 4.7%. One example proves nothing either way; it shows why positions are spread across many stocks.

### Apple, January 2012 (US): the textbook case

Apple's EPS for the December 2011 quarter was 13.87, as reported then (before later splits), against 6.43 a year earlier. That is growth of about 116%. The previous quarter's growth had been about 52%. The stock rose 6.3% on 25 January 2012.

| Step | Date | Value (split-adjusted price) |
|---|---|---|
| Entry | Close, 26 Jan 2012 | 15.88 |
| Exit after 60 sessions | 23 Apr 2012 | 20.42: +28.6% |
| S&P 500 ETF over the same days | | +3.7% |

This was one of the largest companies in the world, with dozens of analysts. The drift still happened. But the study below shows such cases were not the rule in the US since 2009.

## 7. Common mistakes

- **Growth from a tiny or negative base.** A profit rising from ₹1 crore to ₹5 crore is "400% growth". Require a positive and meaningful base.
- **One-off gains.** A land sale or tax refund inflates profit once. Check revenue and operating profit.
- **Using the quarter-end date.** Results come 4 to 8 weeks after the quarter ends. Use the announcement date.
- **Ignoring the reaction.** If great numbers meet a falling price, the market knows something, often about guidance. In India a negative reaction cut the drift sharply.
- **Too few positions.** The edge, where it exists, is a small average across many stocks.

## 8. What the evidence says

**Published research.** Ball and Brown (1968) found the drift. Foster, Olsen and Shevlin (1984) confirmed it. Bernard and Thomas (1989, 1990) showed it lasted about 60 trading days. For decades it was one of the most robust anomalies.

Chordia and co-authors (2009) found it was concentrated in illiquid stocks. Martineau (2022) concluded that in large US stocks it had largely gone. Evidence for India is thinner.

**Event study on stored data.** For every results filing, the reaction day is the session with the largest move from 3 days before the filing date to one session after. I measured profit growth against the same quarter a year earlier, from stored quarterly net profit. The drift is the stock's return from the close of the session after the reaction day to 60 sessions later, minus the index (the S&P 500 ETF in the US, the Nifty 50 in India). I sorted events into five equal groups (quintiles) by each measure.

US, liquid stocks, 2009–2026, by YoY profit growth:

| Growth quintile | Events | Drift, mean | Drift, median |
|---|---|---|---|
| Lowest (−35% or worse) | 10,219 | +0.26% | −0.55% |
| 2 | 10,218 | −0.35% | −0.66% |
| 3 | 10,218 | −0.48% | −0.52% |
| 4 | 10,218 | +0.02% | −0.11% |
| Highest (+52% or better) | 10,218 | +0.48% | −0.29% |

The gap between the highest and lowest groups was 0.22 percentage points over 60 sessions. That is far below trading costs. By reaction size it was reversed: the stocks that fell most on results (by 8% on average) drifted up more than those that rose most.

India, liquid stocks, 2020–2026:

| Measure | Lowest quintile, mean / median | Highest quintile, mean / median | Highest minus lowest, mean |
|---|---|---|---|
| YoY profit growth | +3.39% / +0.91% | +7.03% / +3.56% | +3.64 points |
| Acceleration | +3.36% / +1.72% | +6.19% / +3.87% | +2.83 points |
| 2-day price reaction | +2.33% / +0.09% | +6.39% / +2.98% | +4.07 points |

Combining growth with the reaction, in India:

| Group | Events | Drift, mean | Drift, median | Beat the index |
|---|---|---|---|---|
| Top-fifth growth, positive reaction | 466 | +7.78% | +4.22% | 59% |
| Top-fifth growth, negative reaction | 273 | +5.75% | +2.98% | 58% |
| Bottom-fifth growth, negative reaction | 431 | +2.14% | +0.69% | 52% |

**What this says.** In liquid US stocks since 2009, ranking by growth, acceleration or reaction gave almost no drift. That matches the published decline. In India the ranking worked in the expected direction, by a few percentage points over 60 sessions. But every group beat the Nifty 50 on average. Smaller Indian companies rose faster than the 50 largest in 2023–2024, so read the differences between groups, not the levels.

**Caveats.** Indian results data start in late 2020, so this is one market cycle. The stock list is today's (survivorship bias). Filing dates are not always announcement dates. Quarters overlap, so the events are not independent.

## 9. Building and testing it yourself

**Data.** Quarterly results as first reported, with announcement dates and times. Restated figures leak future knowledge. Daily prices and an index. Ideally, analysts' consensus forecasts.

**Look-ahead traps.**
- Use only results announced before the entry date.
- Quintile cut-offs must use only events known at the time: rank within the current results season, not across the whole history.
- A company's own history (for SUE) must end at the current quarter.

**Survivorship.** Include delisted companies. Small companies with big growth spikes sometimes collapse.

**Costs (India, approximate).** A round trip in delivery costs about 0.25% to 0.35% before slippage. That is STT of about 0.1% on each side and stamp duty of about 0.015% on the buy. Small exchange charges, GST on charges and a depository charge per sale make up the rest. For mid-caps add 0.1% to 0.3% slippage. Compare that with the 3- to 4-point spread found above.

**What to test.** Each surprise measure alone, then combined. Holding periods of 20, 60 and 120 sessions. Results by year. Long-only against the index, since shorting in India needs futures.

**What a good test reports.** The average drift by quintile and its spread, the hit rate, results by year, turnover and costs, and how much the result depends on the smallest stocks.

```
for each results announcement (date A):
    g      = profit[q] / profit[q-4] - 1          # needs profit[q-4] > 0
    accel  = g - (profit[q-1] / profit[q-5] - 1)
    react  = stock return - index return, close[A-1] to close[A+1]
    rank g and accel within the current results season
    if g in top fifth and accel > 0 and 0 < react < 20%:
        buy at close[A+2]
        sell at close[A+62], or before the next results, or on close < low[A]
```

## 10. Checklist

- [ ] Is the profit growth from a positive, meaningful base?
- [ ] Is growth in the top fifth this season, and faster than last quarter?
- [ ] Did revenue grow too, and is there no one-off gain?
- [ ] Did the price confirm, beating the index over the 2 days around results?
- [ ] Was the reaction below 20% (otherwise use the gap rules)?
- [ ] Is the market in an uptrend?
- [ ] Do I hold enough positions for the average to matter?
- [ ] When is my exit date, and when are the next results?

## Further reading

- Ray Ball and Philip Brown, "An Empirical Evaluation of Accounting Income Numbers", *Journal of Accounting Research* (1968).
- George Foster, Chris Olsen and Terry Shevlin, "Earnings Releases, Anomalies, and the Behavior of Security Returns", *The Accounting Review* (1984).
- Victor Bernard and Jacob Thomas, "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?", *Journal of Accounting Research* (1989).
- Victor Bernard and Jacob Thomas, "Evidence that Stock Prices Do Not Fully Reflect the Implications of Current Earnings for Future Earnings", *Journal of Accounting and Economics* (1990).
- Louis Chan, Narasimhan Jegadeesh and Josef Lakonishok, "Momentum Strategies", *Journal of Finance* (1996).
- Joshua Livnat and Richard Mendenhall, "Comparing the Post-Earnings Announcement Drift for Surprises Calculated from Analyst and Time Series Forecasts", *Journal of Accounting Research* (2006).
- Tarun Chordia, Amit Goyal, Gil Sadka, Ronnie Sadka and Lakshmanan Shivakumar, "Liquidity and the Post-Earnings-Announcement Drift", *Financial Analysts Journal* (2009).
- Charles Martineau, "Rest in Peace Post-Earnings Announcement Drift", *Critical Finance Review* (2022).
