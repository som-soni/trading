# Morales and Kacher — pocket pivots, buyable gap-ups and the 7-week rule

**In short**

- Gil Morales and Chris Kacher trade leading stocks in the O'Neil style, but they buy earlier: on a **pocket pivot** inside a base, or on a **buyable gap-up** after news.
- A pocket pivot is an up day whose volume beats every down day's volume of the prior ten sessions, near the 10-day average. A buyable gap-up is a big gap on heavy volume, stopped at the gap day's low.
- They sell on **moving-average violations**, and the **7-week rule** decides which average to watch: the 10-day at first, the 50-day once a stock has held its 10-day for seven weeks.
- On stored data, pocket pivots did no better than other up days in an uptrend. Most gap-ups lost their gap-day low within days. The slower 50-day exit did better than the 10-day in both markets.

## 1. The idea

In early January 2024, General Electric (now GE Aerospace) was resting just above its 10-day average after a strong run. On 8 January it rose 1.6% on 6.9 million shares. In the ten sessions before, its heaviest down day had traded 5.2 million.

```series
title: GE — a pocket pivot near the 10-day, and a trend that held for five months (adjusted for the 2024 spin-off)
from: 2023-10-15
to: 2024-07-31
tf: D
line: us:GE | GE | log
line: us:GE@sma10 | 10-day average
line: us:GE@sma50 | 50-day average
line: us:GE@vol | Volume | pane2 bars
mark: 2024-01-08 | pocket pivot
mark: 2024-02-28 | 7 weeks
mark: 2024-06-14 | exit
caption: The pocket pivot's volume beat every down day of the prior two weeks. After seven weeks above the 10-day, the 50-day became the sell line; it was violated in June.
```

That day was a **pocket pivot**. A Morales–Kacher trade bought it at the close, 102.38. Seven weeks later the stock had not broken its 10-day average, so the 50-day became the sell line. That line broke in mid-June, about 50% higher.

The idea is to **see a fund's buying before the breakout**. A big buyer cannot hide its volume. If an up day's volume is larger than any selling day's lately, demand has taken over, even though the price has not yet cleared the top of the base.

Who is on the other side? Mostly holders selling into a sideways stock. On down days they set the volume to beat. A pocket pivot says a buyer has absorbed more than they have been selling.

Morales and Kacher both worked as portfolio managers at William O'Neil's firm. They set out their method in *Trade Like an O'Neil Disciple* (2010) and later books. It is CAN SLIM with three changes: earlier entries, a buy for news gaps, and a sell discipline built on moving averages.

## 2. When it works and when it doesn't

It works best in a strong market with clear leaders, when institutions are buying the same few stocks. Pocket pivots then appear inside the bases of stocks that go on to break out.

It works poorly in:

- **Weak or sideways markets.** Up days on good volume happen in every market. Without a trend, they lead nowhere.
- **Extended stocks.** A pocket pivot far above the 10-day average is a late entry, not an early one. Morales and Kacher say not to buy it.
- **Thin stocks.** One large order can beat ten days of down volume on its own.

**Buyable gap-ups** need a real catalyst — results, a major contract, a new product. A gap on no news is more likely to fade.

**India.** The method suits liquid stocks in the derivatives segment, without a daily price band. A results gap in a banded stock can lock at the upper band, and the buy then cannot fill. Settlement is T+1.

**US.** Results come out before the open or after the close, so most gaps happen at the open. The gap-day low is set in the first hour, which helps place the stop early.

## 3. The rules

Each rule below is a condition a program can check. Section 4 gives the ranges.

### Universe and filters

- **Liquidity.** Close at least ₹20 or $5. The 50-day average daily turnover is at least ₹5 crore or $5 million.
- **Uptrend.** The close is above the 50-day average, the 50-day is above the 200-day, and the close is within 25% of the 52-week high. See [Stages and trend in a stock](learn-price-stages.md).
- **Leadership.** Strong relative strength, in a leading group, with growing earnings. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md) for the O'Neil filters.

### Setup — pocket pivot

- **An up day.** Today's close is above yesterday's.
- **The volume test.** Today's volume is larger than the volume of every down day in the prior 10 sessions.
- **Near the averages.** The close is at or above the 10-day and 50-day averages, and no more than about 5% above the 10-day.
- **Where.** Inside a base, near its lows or middle, or as a "continuation" pocket pivot off the 10-day in an uptrend.

The test does not ask for above-average volume. A quiet stock can show a pocket pivot on less than its 50-day average, as long as it beats the recent down days.

### Setup — buyable gap-up

- **The gap.** Today's open is above yesterday's close by at least 0.75 times the 40-day average true range (ATR). ATR is the average daily range, counting gaps.
- **The volume.** Today's volume is at least 1.5 times the 50-day average.
- **The trend.** The stock was above its 50-day average before the gap.
- **The news.** Results or another real catalyst. This part cannot be coded well.

### Entry

- **Pocket pivot.** Buy during the day, once the volume pace shows the day will beat the recent down days. For testing, buy at the close.
- **Buyable gap-up.** Buy on the gap day, near the open or once the first hour holds. For testing, buy at the close.

### Initial stop

- **Pocket pivot.** No more than 7–8% below the entry, as in O'Neil's rule. Many traders use a close below the 50-day average as a tighter stop.
- **Buyable gap-up.** Just under the gap day's intraday low. If the stock trades below it, the gap has failed.

### Exits

**A moving-average violation** is a close below the average, followed — on a later day, before any close back above it — by trading below that day's low. A single close below the line is not enough; the follow-through is the signal.

**The 7-week rule** picks the average to watch:

- For the first seven weeks (35 sessions), sell on a violation of the **10-day** average.
- If the stock holds its 10-day for seven weeks without a violation, switch to the **50-day**. A stock that strong has earned more room.

### Position size

- Risk a fixed share of capital per trade, for example 0.5–1%.
- Shares = (capital × risk %) ÷ (entry − stop). A gap-up with a 3% stop and 0.75% risk gives a position of 25% of capital, so cap position size as well.
- See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Add on a second pocket pivot or a breakout above the base, never on a down day.
- Sell before results unless the trade has a large cushion; a results gap can jump any stop.
- Re-buy a stock that was sold if it shows a new pocket pivot off its 10-day or 50-day.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price / turnover | ₹20 / $5; ₹5 crore / $5m | Tradeability | Raise for bigger accounts |
| Trend filter | Close > 50-day > 200-day; within 25% of the high | Stage 2 only | |
| Down-day lookback | 10 sessions | The volume to beat | Some use 10–15 |
| Distance above the 10-day | ≤ 5% | Not extended | See section 8 |
| Gap size | ≥ 0.75 × 40-day ATR | What counts as a gap | Bigger gaps are rarer |
| Gap-day volume | ≥ 1.5 × 50-day average | Demand behind the gap | 1.5–3× |
| Pocket-pivot stop | 7–8%, or a 50-day close | Biggest loss | |
| Gap-up stop | Under the gap day's low | When the gap has failed | Usually 2–4% away |
| Violation | Close below, then trade below that day's low | Sell signal | A plain close-below sells sooner |
| 7-week rule | 35 sessions above the 10-day | Switch to the 50-day | See section 8 |
| Risk per trade | 0.5–1% | Position size | |

## 5. Variations

- **O'Neil's CAN SLIM** buys only the breakout through the pivot, with the same 7–8% stop. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Earnings gaps and episodic pivots** buy results gaps too, often in stocks that were not leaders before. See [Earnings gaps and episodic pivots](learn-strat-earnings-gaps.md).
- **Moving-average pullbacks** buy a leader as it touches a rising average — close to a continuation pocket pivot without the volume test. See [Pullback to a moving average](learn-strat-pullback-ma.md).
- **Short selling.** Morales and Kacher also wrote on shorting failed leaders, the mirror image of these buys. See [Shorting Stage 4 stocks](learn-strat-stage4-shorts.md).
- **Volume in general**, and why it is read relative to the stock's own average, is covered in [Volume](learn-price-volume.md).

## 6. Worked examples

These use the daily-data version: entry at the signal day's close; exits by the 7-week rule. Prices are adjusted for later splits and spin-offs.

### GE, January 2024 — a pocket pivot that became a five-month trend

This is the chart in section 1.

- **The volume test.** 8 January: 6.92 million shares on an up day. The heaviest down day of the prior ten sessions was 5.19 million, on 2 January. Volume was only 1.22 times the 50-day average.
- **Near the 10-day.** The close, 102.38, was 1.2% above the 10-day average.
- **Stop.** 8% below: 94.19.
- **The 7-week rule.** By 28 February the stock had held its 10-day for seven weeks, closing at 124.19. From then on, only a 50-day violation would sell.
- **Exit.** The stock closed below its 50-day on 13 June and traded below that day's low on 14 June. Sold at 154.18: +50.6%.

### Persistent Systems, July 2021 — a buyable gap-up on results

```series
title: Persistent Systems — a results gap on eleven times normal volume
from: 2021-05-15
to: 2021-12-31
tf: D
line: india:PERSISTENT.NS | Persistent Systems | log
line: india:PERSISTENT.NS@sma10 | 10-day average
line: india:PERSISTENT.NS@sma50 | 50-day average
line: india:PERSISTENT.NS@vol | Volume | pane2 bars
mark: 2021-07-23 | gap-up
mark: 2021-11-29 | exit
caption: The gap-day low held, the stock rode its 10-day for seven weeks, and the 50-day rule kept it in until late November.
```

| Persistent Systems, 23 July 2021 | Value |
|---|---|
| Prior close | ₹1,414.30 |
| Open | ₹1,530.00 (+8.2%) |
| Gap ÷ 40-day ATR | 2.8 |
| Volume ÷ 50-day average | 10.8 |
| Entry (close) | ₹1,519.57 |
| Stop (under the gap-day low of ₹1,462.50) | ₹1,461.04, 3.9% below |

- **The 7-week rule.** The stock held its 10-day until 14 September, closing at ₹1,793.80, and switched to the 50-day rule.
- **Exit.** A 50-day violation completed on 29 November 2021, sold at ₹1,900: +25.0%. The peak had been ₹2,219.93 on 18 November.

### Infosys, July 2023 — a small gap-up a week before results

```series
title: Infosys — a gap-up that its own results gapped through
from: 2023-05-15
to: 2023-09-29
tf: D
line: india:INFY.NS | Infosys | log
line: india:INFY.NS@sma10 | 10-day average
line: india:INFY.NS@sma50 | 50-day average
line: india:INFY.NS@vol | Volume | pane2 bars
mark: 2023-07-14 | gap-up
mark: 2023-07-21 | results
caption: The gap barely met the size test. Five sessions later, results and a cut to the year's revenue forecast gapped the stock through the stop.
```

- **The gap.** On 14 July 2023, Infosys opened at ₹1,380.65, up ₹15.55 from the prior close. That is 0.8 times its 40-day ATR, just over the 0.75 test. Volume was twice average.
- **Entry and stop.** Close ₹1,425.95. Stop under the gap-day low: ₹1,379.27, 3.3% below.
- **What happened.** The stock reached ₹1,498.80 on 19 July. Infosys reported results on 20 July and cut its revenue forecast for the year. On 21 July it opened at ₹1,320.20, below the stop.
- **Result.** −7.4%, more than twice the planned loss.
- **Lesson.** A buyable gap-up is a bet on news. This one was a small gap with no news of its own, bought days before the company's own results.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Buying a pocket pivot far above the 10-day | It is a late entry with a distant stop |
| Counting volume against the 50-day average | The test is against recent down days; the two are different |
| Buying pocket pivots in a falling market | Up days on volume happen everywhere; without a trend they fade |
| Buying a gap with no news behind it | The gap has no reason to hold |
| Widening the gap-up stop | The gap-day low is the whole thesis; below it, the gap has failed |
| Selling on one close below the 10-day | The rule needs the follow-through below that day's low |
| Watching the 10-day forever | A stock that held it for seven weeks has earned the 50-day |
| Buying days before results | A results gap can jump any stop |

## 8. What the evidence says

**Their record.** Both authors report large personal returns, notably in the late-1990s boom. The figures are self-reported and not audited. They show the method can be traded well by its authors. They do not show how often its rules work for others.

**Published research behind the parts:**

- **Unusual volume.** Stocks with unusually high trading volume tended to rise over the following month (Gervais, Kaniel and Mingelgrin, 2001).
- **Volume and the direction of returns.** A price move on high volume tended to continue in stocks with more informed trading, and to reverse in stocks traded mainly for other reasons (Llorente, Michaely, Saar and Wang, 2002).
- **News gaps.** Large moves that came with public news tended to continue; large moves without news tended to reverse (Chan, 2003).
- **Results drift.** Prices kept drifting after strong earnings surprises (Bernard and Thomas, 1989).
- **Momentum.** Stocks that rose most over the prior 3–12 months tended to keep outperforming (Jegadeesh and Titman, 1993).

**An event study on stored data.** We coded both setups and the selling rules.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Liquidity on the day before: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. Uptrend on the day before: close above the 50-day, 50-day above the 200-day, close within 25% of the 52-week high. Pocket pivot: an up close, volume above every down day's volume of the prior 10 sessions, close at or above the 10-day and 50-day. "Other up days": up closes in an uptrend, above both averages, that fail the volume test. Baseline: every 10th uptrend session. Buyable gap-up: open above the prior close by ≥ 0.75 × the 40-day ATR, volume ≥ 1.5 × the 50-day average, prior close above the 50-day. One event per stock per 10 sessions per kind. Entry at the close; stop 8% below (pocket pivots) or under the gap-day low (gap-ups), gaps filled at the open. Violation: a close below the average, then a session trading below that day's low, before any close back above; sold at the lower of that low and the open. At most 250 sessions. Caveats: today's lists only (survivorship bias), no costs in the tables, daily bars instead of intraday entries, no earnings or news filter.

**Forward returns from the signal close:**

| India | Events | Median, 20 sessions | Median, 60 sessions | Up 30%+ in 60 | Down 20%+ in 60 |
|---|---|---|---|---|---|
| Pocket pivots | 43,579 | +0.37% | +1.63% | 11.5% | 9.3% |
| … within 5% of the 10-day | 26,043 | +0.38% | +1.69% | 9.9% | 7.8% |
| … more than 5% above it | 17,536 | +0.30% | +1.54% | 13.9% | 11.4% |
| Other up days | 55,163 | +0.54% | +1.99% | 10.9% | 8.3% |
| Uptrend baseline | 88,924 | +0.36% | +1.55% | 10.8% | 8.6% |
| Buyable gap-ups | 8,340 | +0.17% | +1.27% | 11.6% | 10.0% |

| US | Events | Median, 20 sessions | Median, 60 sessions | Up 30%+ in 60 | Down 20%+ in 60 |
|---|---|---|---|---|---|
| Pocket pivots | 117,536 | +0.47% | +1.46% | 4.9% | 8.1% |
| … within 5% of the 10-day | 88,862 | +0.49% | +1.49% | 3.2% | 6.0% |
| … more than 5% above it | 28,674 | +0.42% | +1.32% | 10.1% | 14.7% |
| Other up days | 211,599 | +0.55% | +1.53% | 4.6% | 7.4% |
| Uptrend baseline | 300,463 | +0.58% | +1.58% | 4.8% | 7.7% |
| Buyable gap-ups | 32,568 | +0.30% | +1.20% | 6.5% | 12.4% |

**Trades, by exit rule** (average result per trade, before costs):

| | India | US |
|---|---|---|
| Pocket pivots, 7-week rule | +0.7% | 0.0% |
| Pocket pivots, 10-day violation | +0.6% | 0.0% |
| Pocket pivots, 50-day violation | +2.8% | +0.4% |
| Other up days, 7-week rule | +0.8% | +0.1% |
| Other up days, 50-day violation | +3.0% | +0.5% |
| Gap-ups, 7-week rule | +0.4% | −0.2% |
| Gap-ups, 50-day violation | +1.5% | +0.3% |

| Buyable gap-ups | India | US |
|---|---|---|
| Median stop distance (to the gap-day low) | 2.1% | 2.5% |
| Stopped out under the gap-day low (7-week rule) | 71.9% | 64.0% |
| Median holding period | 2 sessions | 4 sessions |
| Held the gap-day low for 20 sessions | 20.6% | 26.2% |
| Median 60-session return: held the low | +12.0% | +7.5% |
| Median 60-session return: lost it | −1.3% | −1.3% |

What this shows:

- **The pocket-pivot volume test added nothing measurable.** Pocket pivots did no better than other up days in an uptrend, or a random uptrend day, in either market. Their volume relative to the 50-day average made no clear difference either.
- **Extended pocket pivots were wilder, not worse on average.** Those more than 5% above the 10-day had more big gains and more big losses — which is why the authors call them riskier.
- **The 7-week rule behaved like a 10-day exit.** The median trade lasted about eight sessions, so few trades ever reached seven weeks. The rule only matters for the rare stock that does.
- **The slower 50-day exit did better** for every setup in both markets, at the cost of larger losses on the trades that failed.
- **Most gap-ups lost their gap-day low within days.** The stop sits close, so it is hit often. The minority that held went on to clearly better results — but you only learn which ones afterwards.
- **None of this beat buying a random uptrend day by much.** The edge, if any, sits in what the code leaves out: the earnings, the group, the news behind a gap, and the market.

**What is unknown.** No study tests the full method with point-in-time fundamentals, news quality and the authors' market timing. Intraday entries, which they use for both setups, cannot be tested on daily bars. Treat the rules as a framework, and the volume test as a description rather than an edge.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV with volume; intraday volume if you want to test buying during the day; results dates; industry groups and relative strength for the leadership filter.

**Look-ahead traps.**

- The day's volume is only known at the close. An intraday entry must use the volume pace so far, not the day's total.
- The gap-day low is only final at the close. An intraday stop under it must use the low at the time of the order.
- A violation needs a later day's trading; it cannot be decided on the day of the close below the line.

**Survivorship.** Use lists that include delisted companies. Failed leaders are exactly the trades a today's-list test leaves out.

**Costs.** In India a delivery round trip costs roughly 0.25–0.35%: securities transaction tax, stamp duty, exchange fees, GST and depository charges. With averages under 1% a trade, costs decide whether the result is positive.

**What to test.** Start with the exit: the 10-day, the 50-day and the 7-week switch. Then add filters one at a time — earnings, groups, a market filter — and check whether the pocket-pivot test adds anything over a plain up day once they are in. Report results by year.

**What a good test reports.** Trades per year, win rate, average win and loss, and expectancy after costs. Also how often the gap-day low is lost, the longest losing streak, drawdown, and results by market regime. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t (for stocks in a liquid uptrend, using bars up to t):
    pocket pivot: close[t] > close[t-1]
                  and volume[t] > max(volume of down days in t-10 .. t-1)
                  and close[t] >= sma10[t], sma50[t] and close[t] <= 1.05 * sma10[t]
                  -> buy at close[t]; stop = 0.92 * close[t]
    gap-up:       open[t] - close[t-1] >= 0.75 * atr40[t-1] and volume[t] >= 1.5 * avg_volume_50[t-1]
                  -> buy at close[t]; stop = low[t] - tick
manage daily:
    if low <= stop: sell at min(open, stop)
    line = sma10 if sessions_held <= 35 else sma50          # the 7-week rule
    if a close below `line` is pending and low < that day's low: sell at min(open, that low)
```

## 10. Checklist

- [ ] Market in an uptrend; leaders acting well
- [ ] Stock in Stage 2, near its highs, a leader in a leading group
- [ ] Pocket pivot: volume above every down day of the last 10 sessions
- [ ] Pocket pivot: within about 5% of the 10-day average, not extended
- [ ] Gap-up: gap at least 0.75 × the 40-day ATR, volume at least 1.5 × average
- [ ] Gap-up: real news behind it; stop placed under the gap-day low
- [ ] No results due before the trade has a cushion
- [ ] Position size from the stop; size capped for tight gap-up stops
- [ ] Sell plan written: 10-day violation for seven weeks, then 50-day violation
- [ ] In India: stock not in a price band that could lock

## Further reading

- Gil Morales and Chris Kacher, *Trade Like an O'Neil Disciple* (Wiley, 2010) — pocket pivots, buyable gap-ups and the selling rules.
- Gil Morales and Chris Kacher, *In the Trading Cockpit with the O'Neil Disciples* (Wiley, 2012) — worked examples of the same rules.
- Simon Gervais, Ron Kaniel and Dan Mingelgrin, "The High-Volume Return Premium", *Journal of Finance* (2001).
- Guillermo Llorente, Roni Michaely, Gideon Saar and Jiang Wang, "Dynamic Volume-Return Relation of Individual Stocks", *Review of Financial Studies* (2002).
- Wesley Chan, "Stock Price Reaction to News and No-News: Drift and Reversal After Headlines", *Journal of Financial Economics* (2003).
- Victor Bernard and Jacob Thomas, "Post-Earnings-Announcement Drift", *Journal of Accounting Research* (1989).
- [CAN SLIM breakouts](learn-strat-canslim-breakout.md), [Earnings gaps and episodic pivots](learn-strat-earnings-gaps.md), [Volume](learn-price-volume.md).
