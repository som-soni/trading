# Livermore's pivotal points — new highs, building a position, and sitting tight

**In short**

- Jesse Livermore, the most famous speculator of the early 1900s, bought stocks as they broke into new high ground after a pause. He called those moments **pivotal points**.
- He tested each idea with a small first purchase and added only as it showed a profit (**pyramiding**). He never let a loss run past about 10%.
- He watched two leaders of the same group together, and trusted a move more when both confirmed it. Once a trade worked, he held it for the whole move rather than trading in and out.
- On stored data, breakouts to new 52-week highs made a small average profit in India and almost none in the US. Pyramiding gave smaller losses and smaller averages, but did not raise returns. Waiting for a sister stock did not help.

## 1. The idea

In mid-2023, Bajaj Auto made a new 52-week high in early July, then rested for two months. Its pullback was shallow: from ₹4,995 to ₹4,541, about 10%. Meanwhile, other carmakers — TVS Motor, Maruti Suzuki and Force Motors — were making new highs of their own.

On 15 September 2023, Bajaj Auto broke into new high ground. It closed at ₹5,130.50, on almost five times its usual volume.

```series
title: Bajaj Auto — a pause, a pivotal point, and a year of sitting tight
from: 2023-05-01
to: 2024-12-31
tf: D
line: india:BAJAJ-AUTO.NS | Bajaj Auto | log
line: india:BAJAJ-AUTO.NS@sma50 | 50-day average
line: india:BAJAJ-AUTO.NS@vol | Volume | pane2 bars
mark: 2023-07-06 | high
mark: 2023-09-15 | 1
mark: 2023-10-19 | 2
mark: 2023-11-17 | 3
mark: 2024-10-15 | exit
caption: 1, 2, 3: the three purchases — the breakout on 4.9× volume, then +5% and +10%. Exit: the first close below the prior 20-session low. The stock more than doubled in between.
```

A Livermore-style trade bought a third of a full position there. It bought a second third at +5% and the last third at +10%. It then sat tight for thirteen months, until the stock closed below its lowest low of the prior 20 sessions.

That is Livermore's method in one chart. **Wait for the stock to show you the trend by breaking into new ground. Buy a little; buy more only if you are right. Then sit through the move.**

Why would new high ground matter? Above the old high, nobody who bought earlier is sitting on a loss and waiting to sell at breakeven. Livermore called the easier direction the **line of least resistance**. A stock at a new high, after a quiet pause, has shown which way that line runs.

Livermore was born in 1877 and began trading as a teenager. He made several fortunes, most famously by selling short before the crashes of 1907 and 1929. He also went bankrupt more than once. His methods survive in his own short book, *How to Trade in Stocks* (1940), and in *Reminiscences of a Stock Operator* (1923), a lightly fictionalised account of his career written by Edwin Lefèvre.

## 2. When it works and when it doesn't

It works best in long, broad bull markets, when leading stocks trend for many months. Pyramiding and sitting tight only pay off when the trend lasts.

It works poorly in:

- **Sideways markets.** New highs fail and fall back. Each probe loses a little, and they add up.
- **Bear markets.** Few stocks reach new highs at all. Livermore himself made his largest gains on the short side in those periods.
- **Choppy leaders.** A stock that swings 10% a week will hit a 10% stop on ordinary noise.

**The patience problem.** Livermore said that his big money came from sitting through moves, not from his reading of the tape. Holding a winner for a year means sitting through several pullbacks of 10–20%. Most traders sell too soon.

**India.** The method suits large, liquid stocks in the derivatives segment, which have no daily price band. In banded stocks, a breakout can lock at the upper band and a failure at the lower band. Settlement is T+1.

**US.** Liquidity is deep. Results-day gaps are the main risk to a 10% stop.

## 3. The rules

Livermore wrote in general terms, not in exact rules. Each rule below is one coded reading of his ideas. Section 4 gives the ranges.

### Universe and filters

- **Liquidity.** Close at least ₹20 or $5. The 50-day average daily turnover is at least ₹5 crore or $5 million.
- **Leaders.** The stock is among the strongest in a strong group. See [Relative strength](learn-price-rs.md).
- **Sister stocks (optional).** Another leader in the same industry has also made a new high in the past two weeks. Livermore called this watching stocks "in tandem".

### Setup

```pattern
rectangle
```

- **A pause.** The stock made a new 52-week high, then went at least 20 sessions without another.
- **Shallow.** The pullback during the pause is at most 30% from the high.
- **The pivotal point.** The old high. Livermore called this a **continuation pivotal point**: a pause within a trend, and the level that ends it.
- **Reversal pivotal points.** He also watched for the end of a trend: a stock that makes a new high and then reverses sharply on heavy volume. This guide uses them as warnings, not as entries.

### Entry

- **The probe.** Buy a first part of the position when the stock closes above the pivotal point. Accounts of his method describe a first lot of about a fifth; this guide uses a third.
- **Adding.** Buy the second part only after the first shows a profit, at about +5%. Buy the third at about +10%.
- **Never add to a loss.** If the probe is not working, there is no second purchase.

### Initial stop

- Sell the whole position if the price falls 10% below the first purchase. Livermore's rule was never to let a loss pass about 10%.
- **Raise the stop as you add.** When the last part is bought, move the stop to the first purchase price. Section 6 shows what happens when you don't.

### Exits

- **Sit tight.** Hold while the stock keeps making higher highs and higher lows.
- **The reaction low.** Sell on a close below the lowest low of the prior 20 sessions. That is a coded stand-in for "the trend has turned".
- **Danger signals.** Livermore also sold on a sudden, heavy-volume reversal after a long rise, or when a leader stopped responding to good news.

### Position size

- Decide the full position size in advance, from the 10% stop. With 1% of capital at risk, a full position is 10% of capital.
- The probe uses only part of that. If the trade fails early, the loss is a fraction of the planned risk.
- See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Trade only a few stocks at a time, and know each one well.
- After a run of losses, stop and wait. Livermore said that there is a time to be out of the market entirely.
- Keep records. Livermore kept handwritten price records of a few leaders, which he called his market key.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price / turnover | ₹20 / $5; ₹5 crore / $5m | Tradeability | Raise for larger accounts |
| Pause before the breakout | ≥ 20 sessions without a new high | Base maturity | Longer pauses did no better (section 8) |
| Pause depth | ≤ 30% | Damage in the base | |
| Sister confirmation | ≥ 1 peer at a new high in 2 weeks | Group strength | Optional; see section 8 |
| First purchase | 1/5 to 1/3 of the full position | Size of the probe | |
| Add points | +5% and +10% | When to add | Closer = more adds, more whipsaws |
| Hard stop | 10% below the first purchase | Largest loss | Livermore's limit |
| Stop after the last add | First purchase price | Protects the adds | See section 6 |
| Trend exit | Close below the 20-session low | Sitting tight | 10-session = faster; 50-session = slower |
| Risk per trade | 0.5–1% of capital | Position size | |

## 5. Variations

- **Livermore's market key** is his record-keeping system: columns for rallies and reactions, and rules on how far a move must go to count. It is too detailed to cover here, and its thresholds were set for the prices of his time.
- **Round numbers.** Livermore believed that a stock crossing 100, 200 or 300 for the first time usually kept going. That idea is not tested here (see section 8).
- **Darvas boxes** are a direct descendant: buy new highs out of a tight box, raise the stop box by box. See [Darvas boxes](learn-strat-darvas.md).
- **O'Neil and Minervini** added earnings filters and named base shapes to the same idea. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md) and [SEPA and the VCP](learn-strat-vcp-sepa.md).
- **Channel breakouts** are the mechanical version: buy any new 55-day high, sell a 20-day low. See [Channel breakouts](learn-strat-channel-breakout.md).

## 6. Worked examples

These follow the rules above: a third at the breakout close, a third at +5% and a third at +10%. The stop is 10% below the first purchase; the exit is a close below the prior 20-session low. Prices are adjusted for later splits.

### Bajaj Auto, September 2023 — a group move and a long hold

This is the chart in section 1.

- **Pause.** An earlier new high on 6 July 2023. The 52-week high was ₹4,995.10. The low during the pause was ₹4,541, on 14 August.
- **Sisters.** In the two weeks before the breakout, TVS Motor, Maruti Suzuki and Force Motors all closed at new 52-week highs.
- **Probe.** Close of 15 September, ₹5,130.50, on 4.9 times average volume. Stop at ₹4,617.45.
- **Adds.** The second lot filled at ₹5,387 on 19 October, the third at ₹5,643.55 on 17 November.
- **Exit.** The first close below the prior 20-session low came on 15 October 2024, at ₹11,521.50. The stock had peaked near ₹12,478 three weeks earlier.

| Bajaj Auto | Result |
|---|---|
| Full position at the breakout | +124.6% |
| Pyramid (three lots) | +114.2% |

Pyramiding gave up some of the gain, because two-thirds were bought higher. That is its price.

### Caterpillar, September 2025 — no sister, and still a leader

```series
title: Caterpillar — a new high with no confirming peer, and a long trend
from: 2025-06-01
to: 2026-08-31
tf: D
line: us:CAT | Caterpillar | log
line: us:CAT@sma50 | 50-day average
line: us:CAT@vol | Volume | pane2 bars
mark: 2025-09-17 | breakout
mark: 2026-07-16 | exit
caption: No other heavy-machinery stock had made a new high in the two weeks before, so a sister-stock rule would have skipped this trade. The two adds came within two weeks of the breakout. Exit: the first close below the prior 20-session low.
```

- **Pause.** An earlier new high on 31 July 2025, then a pullback of about 9%, to 405.46.
- **Probe.** Close of 17 September, 450.66, on 1.6 times average volume. Stop at 405.59.
- **Sisters.** None. No other stock in its industry made a new high in the prior two weeks.
- **Adds.** 473.19 on 22 September and 495.73 on 2 October. The stop moved to 450.66.
- **Exit.** The trend held for ten months. The first close below the 20-session low came on 16 July 2026, at 877.17.

| Caterpillar | Result |
|---|---|
| Full position at the breakout | +94.6% |
| Pyramid (three lots) | +85.7% |

**Lesson.** Sister confirmation is a useful idea, but a strict rule would have missed this. Section 8 shows that, on average, it did not help.

### AMD, March 2024 — the pyramiding trap

```series
title: AMD — three lots bought on the way up, then a fall through the first lot's stop
from: 2023-12-01
to: 2024-05-31
tf: D
line: us:AMD | AMD | log
line: us:AMD@sma50 | 50-day average
line: us:AMD@vol | Volume | pane2 bars
mark: 2024-02-29 | breakout
mark: 2024-03-25 | stop
caption: Both adds came within a week of the breakout. The stock peaked at 227.30 two days after the last one, then fell back through every purchase price to the 10% stop.
```

- **Probe.** Close of 29 February 2024, 192.53. Stop at 173.28.
- **Adds.** 202.16 on 1 March and 211.78 on 6 March. The stock peaked at 227.30 two days later.
- **What happened.** It fell back. On 25 March it opened at 172.90, below the stop.

| AMD | Result |
|---|---|
| Full position at the breakout | −10.2% |
| Pyramid, stop left at 10% below the first lot | −14.3% |
| Pyramid, stop raised to the first lot's price after the last add | −4.6% |

**Lesson.** Pyramiding without moving the stop is worse than buying once. The later lots were bought higher but share the first lot's stop, so they lose up to 18%. Raising the stop to the first purchase price when the last lot is bought keeps the whole position near breakeven.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Buying before the stock breaks into new ground | You are guessing the direction instead of letting the stock show it |
| Adding to a losing position | The opposite of pyramiding: more money on the idea that is failing |
| Adding without raising the stop | The later lots carry a much larger loss than the first |
| Letting a loss run past 10% | Livermore's own limit; a large loss takes a much larger gain to recover |
| Selling a winner on the first pullback | The big gains come from sitting through the move |
| Trading too many stocks | Livermore watched a few leaders closely |
| Ignoring a heavy-volume reversal after a long run | That is a reversal pivotal point: the trend may be ending |
| Staying in the market through every condition | He took long breaks when nothing was working |

## 8. What the evidence says

**Livermore's record.** He is reported to have made very large sums in 1907 and 1929, and he went bankrupt several times. No audited record exists. His career shows that the ideas could make large gains. It also shows that a speculator's results swing hugely, and that the rules only work if they are followed.

**Published research behind the parts:**

- **New highs.** Stocks close to their 52-week high outperformed those far below it (George and Hwang, 2004). That is the closest academic test of buying new high ground.
- **Momentum.** Stocks that rose most over the prior 3–12 months tended to keep outperforming for months (Jegadeesh and Titman, 1993).
- **Industry momentum.** Much of the momentum effect comes from whole industries moving together (Moskowitz and Grinblatt, 1999). That supports watching a stock's group, though it is not a test of sister-stock confirmation.
- **Selling winners too soon.** Ordinary investors tend to sell winners too early and hold losers too long, and this costs them (Odean, 1998). That supports "sit tight" and the 10% loss limit.

**An event study on stored data.** We coded the rules in section 3 and ran them on both markets.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to October 2026. Liquidity on the day before: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. Pivotal point: the first close above the prior 52-week high, at least 20 and at most 252 sessions after the previous new-high close, from a pullback at most 30% deep. Stocks in industries with at least five listed stocks. Sister: another liquid stock in the same industry (today's classification) closed at a new 52-week high in the 14 calendar days to the breakout. Full entry: everything at the breakout close. Pyramid: a third at the close, a third when the high reaches +5%, a third at +10% (at the open if it gaps above). Stop 10% below the breakout close; trend exit on a close below the prior 20-session low; at most 250 sessions. Results are a share of one full position. One event per stock per 20 sessions. Caveats: today's lists only (survivorship bias), no costs in the tables, gaps filled at the open.

| Breakouts to new high ground, full entry | India | US |
|---|---|---|
| Events | 5,561 (1,025 stocks) | 24,998 (2,359 stocks) |
| Winning trades | 39.8% | 37.2% |
| Average winner / average loser | +23.5% / −7.8% | +11.4% / −6.1% |
| Trades that gained 50% or more | 5.0% | 0.9% |
| 10% stop hit | 32.6% | 16.9% |
| Median holding period | 32 sessions | 33 sessions |
| **Average result, before costs** | **+4.6%** | **+0.4%** |
| Average result, after costs (0.3% / 0.1% a round trip) | +4.3% | +0.3% |
| Years with a positive average | 11 of 17 | 9 of 17 |

**Pyramiding versus buying once** (share of one full position, before costs):

| | India: full | India: pyramid | India: pyramid, stop raised | US: full | US: pyramid | US: pyramid, stop raised |
|---|---|---|---|---|---|---|
| Average result | +4.6% | +3.7% | +2.7% | +0.4% | +0.2% | +0.1% |
| Average loser | −7.8% | −5.1% | −4.2% | −6.1% | −3.3% | −3.0% |
| Average winner | +23.5% | +23.8% | +23.5% | +11.4% | +10.8% | +10.4% |
| Worst 5% of trades lost at least | 10.0% | 11.9% | 8.1% | 10.0% | 8.1% | 6.3% |
| Trades losing more than 12% | 0.8% | 5.0% | 0.2% | 0.9% | 1.8% | 0.2% |

**Sister stocks and the length of the pause** (full entry, before costs):

| | India: average | India: winners | US: average | US: winners |
|---|---|---|---|---|
| No sister at a new high | +4.7% | 37.2% | +1.1% | 39.6% |
| One or two sisters | +5.1% | 40.2% | +0.6% | 38.2% |
| Three or more sisters | +4.2% | 41.1% | +0.1% | 35.9% |
| Pause of 20–60 sessions | +4.7% | 38.8% | +0.4% | 36.5% |
| Pause of more than 60 sessions | +4.4% | 43.9% | +0.5% | 39.0% |

What this shows:

- **New high ground was a modest edge in India and close to none in the US.** The Indian result rests on a few very large winners; the median trade lost about 4%.
- **Pyramiding cut losses and cut the average.** The average loss fell by a third to a half. But the winners carried less money too, so the average result fell.
- **Pyramiding without raising the stop made the worst trades worse.** In India, trades losing more than 12% went from under 1% to 5%. Raising the stop after the last add fixed that.
- **Sister confirmation did not help.** In the US, breakouts with more sisters did slightly worse. A group already full of new highs may be late in its move.
- **A longer pause did not help either.** Results were about the same after short and long pauses.

**What we could not test.** Livermore's round-number rule needs prices as they were quoted at the time. Stored prices are adjusted for later splits, so a past "first cross of 100" in the adjusted series is not the price traders saw. His danger signals and his judgement of the market are not coded at all.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV for the whole universe, to find new highs; industry groups, for sister stocks; unadjusted prices, if you want to test round numbers; an index for market context.

**Look-ahead traps.**

- The 52-week high must use only bars before the breakout day.
- Industry groups change. A classification taken today puts some stocks in groups they did not belong to at the time.
- An add at +5% must use the price the market actually reached, at the time it reached it.

**Survivorship.** Use lists that include delisted companies. Leaders that later collapsed are exactly the trades a today's-list test leaves out.

**Costs.** In India a delivery round trip costs roughly 0.25–0.35%: securities transaction tax, stamp duty, exchange fees, GST and depository charges. Pyramiding means three purchases instead of one, so slippage is paid three times.

**What to test.** Start with the add points (+3%, +5%, +10%), the size of the probe, and where the stop goes after each add. Then the trend exit: a 10, 20 or 50-session low. Report results with and without the best 1% of trades.

**What a good test reports.** Trades per year, win rate, average win and loss, and expectancy after costs. Also the largest single loss, drawdown, the share of gains from the best trades, and results by market regime. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t:
    for each liquid stock:
        prev_high = highest high of the prior 252 sessions (bars up to t - 1)
        if close[t] > prev_high and the last new-high close was 20+ sessions ago and the pause was <= 30% deep:
            if require_sister and no peer in the same industry made a new high in the last 2 weeks: continue
            buy one third at close[t]; stop = 0.90 * close[t]
manage daily:
    if low <= stop: sell everything at min(open, stop)
    if price reaches +5% (then +10%) of the first purchase: buy the next third
    if all three thirds are bought: stop = max(stop, first purchase price)
    if close < lowest low of the prior 20 sessions: sell everything
```

## 10. Checklist

- [ ] The stock has just closed in new high ground after a pause of several weeks
- [ ] The pause was orderly and no more than about 30% deep
- [ ] The group is strong; note whether a sister stock has confirmed
- [ ] Full position size decided in advance from the 10% stop
- [ ] Probe bought: only a fifth to a third of the full position
- [ ] Add points written down; no adds unless the position is in profit
- [ ] Stop raised to the first purchase price once the position is complete
- [ ] Exit rule written: a close below the last reaction low, or a heavy-volume reversal
- [ ] Ready to sit through normal pullbacks of 10–20%
- [ ] No results due before the stop is at breakeven
- [ ] In India: stock not in a price band that could lock

## Further reading

- Jesse Livermore, *How to Trade in Stocks* (1940) — his own account of pivotal points, tandem stocks, the 10% rule and his market key.
- Edwin Lefèvre, *Reminiscences of a Stock Operator* (1923) — a lightly fictionalised account of Livermore's career and lessons.
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* (1993).
- Tobias Moskowitz and Mark Grinblatt, "Do Industries Explain Momentum?", *Journal of Finance* (1999).
- Terrance Odean, "Are Investors Reluctant to Realize Their Losses?", *Journal of Finance* (1998).
- [Darvas boxes](learn-strat-darvas.md), [Channel breakouts](learn-strat-channel-breakout.md), [Stops and exits](learn-risk-stops-exits.md).
