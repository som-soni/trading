# Darvas boxes — buying the breakout from a range at new highs

**In short**

- A Darvas box is a short sideways range that forms just after a stock makes a new high. Its top is a high that holds for three sessions; its bottom is a low that holds for three sessions.
- Buy with a buy-stop order just above the box top. Put the stop just below the box bottom.
- As the stock climbs, new boxes form above the old ones. Each new box raises the stop to its bottom. You sell only when a box bottom breaks.
- The method buys strength and cuts losses quickly. It gives back part of every gain, and it suffers many small losses in sideways markets.
- Modern versions are the flat base, the rectangle and the channel breakout. They all rest on the same idea: a range at highs, broken upward.

## 1. The idea

In April 2023, NVIDIA was at a new 52-week high. On 18 April it reached 28.11 (in today's split-adjusted prices) and did not go higher for the next three sessions. That set the box top.

It then dipped to 26.23 on 25 April and held above that for three sessions. That set the box bottom: a box 6.7% deep. On 1 May the price traded above 28.11, and the buy-stop filled.

```series
title: NVIDIA — Darvas boxes in 2023
from: 2023-03-15
to: 2023-09-30
tf: D
line: us:NVDA | NVIDIA (split-adjusted) | log
line: us:NVDA@vol | Volume | pane2 bars
band: 2023-04-18 2023-04-28 | box 1: 28.11 / 26.23
band: 2023-05-30 2023-06-05 | box 2: 41.94 / 37.82
mark: 2023-05-01 | buy above 28.11
mark: 2023-06-07 | box 2 bottom breaks: sell at 37.82
caption: The first trade made 34.4%. The two boxes that followed in July and August both broke down, for losses of 1.1% and 1.8%.
```

The price jumped after results in late May. A second box formed between 41.94 and 37.82, and the stop moved up to 37.82. On 7 June the price fell through that level and the stop sold. The trade made 34.4%. Two later boxes, in July and August, broke out and failed, each for a loss under 2%.

That is the whole method. Nicolas Darvas, a professional dancer, described it in his 1960 book *How I Made $2,000,000 in the Stock Market*. He traded by telegram while on tour, so he needed rules that worked with orders placed in advance: a buy-stop above the box and a sell-stop below it.

Why can it work? A stock at a new high has no holders above it who are waiting to break even. A tight box at that high shows that sellers are not pushing the price down much. When the price leaves the box upward, the buyers have absorbed what supply there was.

Who is on the other side? Holders taking profits at the high, and traders who bet that a range will hold. When the range breaks, some of them have to buy back, which adds to the move.

## 2. When it works and when it doesn't

It works in **strong trending markets**, when many stocks are making new highs and keep going. It also suits stocks with a strong reason to rise: Darvas called himself a "techno-fundamentalist" and preferred companies whose earnings were growing fast.

It works poorly in:

- **Sideways markets.** Boxes break out and fall back. Each failure is a small loss, and they add up.
- **Sharp market falls.** Boxes break down together, and gaps can open below the stop.
- **Very volatile stocks with deep boxes.** A 20% box means a 20% stop.

**India.** Box breakouts in NSE stocks often cluster by sector: defence and railways in 2023–2024 are examples. Many small and mid caps have daily price bands of 5–20%. A breakout day can lock at the upper band (your buy-stop does not fill) and a breakdown can lock at the lower band (your stop fills a day later, far lower).

Event days matter too. On 4 June 2024, election results day, several defence and other state-owned stocks fell 20% or more intraday and recovered part of it by the close. Settlement is T+1. Short boxes (breakdowns) can only be traded with futures or options for longer than a day; this guide covers the long side.

**US.** Liquidity is deep and there are no daily price bands. Results-day gaps are the main risk to a stop.

## 3. The rules

### Universe and filters

- **Price and liquidity.** Close at least ₹100 or $15; 50-day average turnover at least ₹10 crore or $20 million.
- **New high.** The box top must be a 52-week high (Darvas preferred all-time highs).
- **Earnings (optional, as Darvas did).** Latest quarterly EPS up at least 20% on a year earlier.
- **Market (optional).** The index is above its 50-day average. Darvas noticed that his boxes failed together in bad markets, and he stopped buying then.

### Setup

```pattern
rectangle
```

- **Box top.** A session whose high is a 52-week high, and the next 3 sessions' highs are all lower.
- **Box bottom.** The lowest low after the top, once 3 sessions in a row have not gone below it — while the top was not exceeded.
- **Restart.** If the price goes above the top before the bottom is confirmed, there is no box. Start again from the new high.
- **Complete box.** Both the top and the bottom are confirmed.
- **Depth filter.** (Top − bottom) ÷ top is at most 15%. Deeper boxes mean wider stops.

### Entry

- **Order.** A buy-stop at the box top plus one tick, placed as soon as the box is complete.
- **Fill.** If the session opens above the top, the order fills at the open.
- **Volume (optional).** Darvas liked rising volume as the price left the box. A testable version: breakout-day volume at least 1.4 times the 50-day average.
- **Cancel.** If the price breaks below the box bottom before it breaks out, cancel the order. The box failed.

### Initial stop

A sell-stop one tick below the box bottom, placed at the same time as the buy order.

### Exits

- **Trailing by boxes.** When a new box completes with a top above the previous box's top, raise the stop to just below the new bottom. Never lower it.
- **Exit.** The stop is hit. That is the only exit in the original method.
- **Optional time stop.** Sell if no new box forms within 40 sessions of the entry and the price is below the entry.

### Position size

Darvas used an initial position and added more when a new box broke out ("pyramiding"). A rule-based version: risk 0.5–1% of capital on the first entry, with shares = (capital × risk %) ÷ (entry − stop). See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Add a second piece only on the breakout from a new, higher box, with the combined risk still within your limit.
- Do not raise the stop between boxes by hand; the rule is what makes the method work.
- After a stop-out, the stock can be bought again from the next complete box.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price / turnover | ₹100 / $15; ₹10 crore / $20m | Tradeability | |
| New-high lookback | 250 sessions (52 weeks) | Which highs count | All-time highs = fewer, stronger boxes |
| Top confirmation | 3 sessions | How quickly a box forms | 2–5; longer = fewer, wider boxes |
| Bottom confirmation | 3 sessions | Same | Usually equal to the top's |
| Maximum box depth | 15% (10–20%) | Stop distance | Deeper boxes hit the stop less often but lose more each time |
| Breakout volume | none, or ≥ 1.4 × 50-day avg | Confirmation | Optional |
| Entry tick | 1 tick above the top | Fill level | Use 0.1–0.5% for slippage in tests |
| Stop tick | 1 tick below the bottom | Stop level | |
| Trailing | each higher box | Profit protection | The heart of the method |
| Time stop | 40 sessions | Dead money | Optional |
| Risk per trade | 0.5–1% of capital | Size | |

## 5. Variations

- **Darvas's original.** Boxes at all-time highs, earnings growth as a filter, orders placed in advance. His book claims he made about $2 million in under two years in the late 1950s.
- **O'Neil's flat base.** A box at least five weeks long and at most 15% deep, usually after an earlier base. The pivot is the box top; the stop is 7–8% below the buy. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Rectangles.** Edwards and Magee, and later Thomas Bulkowski, describe the rectangle: a range with flat top and bottom, broken either way. The measured move is the range's height added to the breakout.
- **Channel breakouts.** Richard Donchian's rule buys a close above the highest high of the last N sessions (often 20 or 55). It is a box without the confirmation rules.
- **Tighter boxes.** Minervini's tight areas and the "three weeks tight" pattern (three weekly closes within about 1–1.5% of each other) are very narrow boxes. See [SEPA and the VCP](learn-strat-vcp-sepa.md).

```pattern
flat-base
```

## 6. Worked examples

Prices are adjusted for later splits and bonus issues.

### NVIDIA, 2023 — one big winner, two small losers

This is the chart in section 1.

- **Box 1.** Top 28.11 (18 April), bottom 26.23 (25 April), 6.7% deep, complete on 28 April.
- **Entry.** Buy-stop filled at 28.14 on 1 May. Stop 26.23: risk 6.8%.
- **Box 2.** After the late-May jump, a box formed with top 41.94 (30 May) and bottom 37.82 (31 May). It completed on 5 June, and the stop moved to 37.82.
- **Exit.** The low broke 37.82 on 7 June. Sold at 37.82: +34.4%, about 5R.
- **The next two trades.** A box breakout on 13 July filled at 44.52 and stopped out at 44.04 (−1.1%). One on 21 August filled at 45.69 and stopped out at 44.89 (−1.8%). The stock then went sideways for several weeks. This is the normal pattern: one large gain, then several small losses.

### Bharat Electronics, 2024 — a box, an election-day shock, and a trailing exit

```series
title: Bharat Electronics — boxes in 2024
from: 2024-03-15
to: 2024-10-15
tf: D
line: india:BEL.NS | Bharat Electronics | log
line: india:BEL.NS@vol | Volume | pane2 bars
band: 2024-04-26 2024-05-16 | box 1: ₹241.65 / ₹221
mark: 2024-05-17 | buy above ₹241.65
mark: 2024-06-04 | results day: low ₹230.05
mark: 2024-09-09 | stop ₹281.10 hit
caption: The trailing stop rose from ₹221 to ₹230 and then to ₹281.10. The exit kept less than half of the peak gain.
```

- **Box 1.** Top ₹241.65 (26 April), bottom ₹221.00 (13 May), 8.5% deep, complete on 16 May.
- **Entry.** Filled at ₹241.89 on 17 May. Stop ₹221.00: risk 8.6%.
- **Election day.** On 3 June the stock reached ₹323. On 4 June, results day, it fell to ₹230.05 intraday on 7.1 times average volume. The stop at ₹221 held.
- **Trailing.** The next box (top ₹323, bottom ₹230) moved the stop to ₹230 on 10 June. That box was 28.8% deep — far too deep to buy, but still a valid trailing step. A box with top ₹340.50 and bottom ₹281.10 moved the stop to ₹281.10 on 26 July.
- **Exit.** The stop was hit on 9 September at ₹281.10: +16.2%. At its peak the gain had been about 41%. That is the cost of trailing by boxes: the exit waits for a whole box to fail.

### Hindustan Aeronautics, July 2024 — a failed box, a small loss

```series
title: Hindustan Aeronautics — a box breakout that failed, July 2024
from: 2024-05-15
to: 2024-09-30
tf: D
line: india:HAL.NS | Hindustan Aeronautics | log
line: india:HAL.NS@vol | Volume | pane2 bars
band: 2024-06-19 2024-06-27 | box: ₹5,582.80 / ₹5,114.60
mark: 2024-07-05 | buy
mark: 2024-07-16 | raised stop ₹5,319 hit
caption: A higher box raised the stop before the stock fell. The loss was 4.8% instead of 8.5%.
```

- **A box skipped.** Early June produced a box with top ₹5,444 and bottom ₹3,920 — 28% deep, because of the election-day fall. The depth filter rejects it.
- **Box.** Top ₹5,582.80 (19 June), bottom ₹5,114.60 (24 June), 8.4% deep, complete on 27 June.
- **Entry.** Filled at ₹5,588.38 on 5 July. Stop ₹5,114.60: risk 8.5%.
- **Trailing.** A small new box (top ₹5,674.75, bottom ₹5,319) moved the stop to ₹5,319 on 15 July.
- **Exit.** The next day the low broke ₹5,319; sold at ₹5,319: −4.8%. A week later the stock traded at ₹4,510, about 19% below the entry.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Drawing boxes by eye after the fact | Real-time boxes look different; use the 3-session rules |
| Buying boxes that are not at new highs | Old holders above the price sell into the breakout |
| Buying very deep boxes | The stop is far away; one loss costs as much as several wins make |
| Lowering the stop "just this once" | Breaks the one rule that limits losses |
| Raising the stop by hand between boxes | You get shaken out of the trend the method is built to hold |
| Quitting after three small losses in a row | Losing streaks are normal; the big winner comes rarely |
| Ignoring results dates | A results-day gap can open far below the stop |
| Trading boxes in a falling market | Boxes fail together; Darvas himself stepped aside |

## 8. What the evidence says

**Published research.**

- **Trading-range breakouts.** Brock, Lakonishok and LeBaron (1992) tested a rule that buys when the Dow Jones index breaks above its recent range, over about 90 years of data. Buy signals were followed by above-average returns. Sullivan, Timmermann and White (1999) later showed that such results weaken sharply once you account for the many rules that could have been tried, and that they faded in later data.
- **The 52-week high.** Stocks near their 52-week high outperformed those far from it (George and Hwang, 2004). Darvas boxes start at a new high, so they sit in this group.
- **Momentum.** Stocks that rose most over 3–12 months tended to keep outperforming (Jegadeesh and Titman, 1993). A box breakout is a short-term momentum entry.

**An event study on stored data.**

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to July 2026. Boxes found with the rules in section 3: the top is a 250-session high not exceeded for 3 sessions; the bottom is the lowest low since, held for 3 sessions; depth at most 20%. Entry at the top (or the open, if higher) on the first session that trades above it. Stop just below the bottom. Outcome: does the price reach entry + 2R before the stop, within 60 sessions? (No trailing; this tests the first leg only.) Liquidity: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. Caveats: today's lists only (survivorship bias), no costs, gaps filled at the stop level.

| | India | US |
|---|---|---|
| Box breakouts | 8,379 | 30,411 |
| Median box depth | 9.6% | 6.2% |
| Median risk (entry to stop) | 10.2% | 6.9% |
| Median sessions from box top to breakout | 10 | 10 |
| +2R before the stop | 31.1% | 24.5% |
| Stop first | 49.5% | 53.0% |
| Median return after 60 sessions | +2.6% | +1.4% |

| Box depth | India: +2R first | India: stop first | US: +2R first | US: stop first |
|---|---|---|---|---|
| Up to 5% | 39.2% | 57.8% | 30.0% | 61.1% |
| 5–10% | 34.8% | 54.1% | 23.3% | 52.7% |
| 10–15% | 27.9% | 47.2% | 18.4% | 42.0% |
| 15–20% | 22.6% | 36.1% | 16.5% | 37.4% |

What this shows:

- **About half of all box breakouts hit their stop** within 60 sessions. Expect it.
- **India did better than the US.** Counting only trades that hit a level, +2R and −1R give roughly +0.13R per trade in India and slightly below zero in the US, before costs and before any trailing gains.
- **Tight boxes reach +2R more often, but are also stopped more often.** A 2R target on a tight box is close by. So is the stop. Noise decides more of them.
- **The method's gains come from trailing.** A first leg near break-even means the edge, if any, must come from the few trades that run for many boxes, as NVIDIA did in 2023. That depends on trends, and trends are not steady from year to year.

**What is unknown.** Darvas's own result is one person's trades in one bull market, told in his own book. No published study tests his exact rules on modern data with costs.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV. Index prices for an optional market filter. Results dates, so you can see which stops were gapped through.

**Look-ahead traps.**

- A box top is only confirmed three sessions after the high. Your test cannot place a buy order before then.
- A box bottom is only confirmed three sessions after the low.
- The 52-week high must be computed from data up to that day.
- If a session's range covers both the stop and the buy level, you cannot know which came first from daily data. Assume the worse one.

**Survivorship.** Use lists that include delisted stocks. Boxes in companies that later failed are part of the true record.

**Costs.** In India, a delivery round trip costs about 0.25–0.35%. That covers STT of 0.1% each side, stamp duty of 0.015% on the buy, exchange fees, GST and depository charges. Buy-stops fill in a rush, so add 0.1–0.5% slippage in liquid stocks and more in small caps. A method with many small losses is very sensitive to these costs.

**What to test.** The confirmation length (2–5 sessions), the maximum depth, a volume filter and a market filter. Report the distribution of trade results, not just the average: a few large winners carry the method. Check results year by year, and hold out the last few years for one final test. See [Backtesting honestly](learn-test-backtesting.md).

```
state = seek_top
each session t:
    if in_trade and low[t] <= stop: sell at min(open[t], stop); in_trade = False
    if state == seek_top:
        if high[t] is a 250-session high and high[t+1..t+3] < high[t]   # known at t+3
            top = high[t]; state = seek_bottom
    elif state == seek_bottom:
        if high > top: state = seek_top                                # no box
        track lowest low since top; if 3 sessions have not undercut it: bottom = it; box complete
        if in_trade and top > last_top: stop = bottom - tick           # trail
        elif not in_trade and (top - bottom) / top <= 0.15: place buy-stop at top + tick
    if buy-stop pending and high[t] > top: buy at max(open[t], top + tick); stop = bottom - tick
    if buy-stop pending and low[t] < bottom: cancel
```

## 10. Checklist

- [ ] The box top is a 52-week high, held for 3 sessions
- [ ] The box bottom is held for 3 sessions, with no new high in between
- [ ] Box depth at most 15%
- [ ] Earnings growing (if you use Darvas's filter); market not in a correction
- [ ] No results date before the expected breakout, or you accept the gap risk
- [ ] Buy-stop above the top and sell-stop below the bottom, both placed together
- [ ] Size set from the stop distance
- [ ] Each higher box raises the stop to its bottom; never lower it
- [ ] In India: the stock is not locked at its price band; order type is delivery

## Further reading

- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* (1960) — the original boxes, told as a story.
- William Brock, Josef Lakonishok and Blake LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance* (1992).
- Ryan Sullivan, Allan Timmermann and Halbert White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance* (1999).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Robert Edwards and John Magee, *Technical Analysis of Stock Trends* (first edition 1948) — rectangles and other ranges.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns* (Wiley) — statistics on rectangles and other patterns.
- [Bases](learn-bases.md), [Chart patterns](learn-chart-patterns.md), [Stops and exits](learn-risk-stops-exits.md).
