# Opening-range breakout — trading the first decisive move of the day

**In short**

- The opening range is the high and low of the first few minutes of the session, usually 5, 15 or 30 minutes.
- You buy if the price breaks above that range and sell short if it breaks below, with the stop on the other side or at the middle, and you are flat by the close.
- It works best on days with news or a big opening gap, in very liquid stocks and index futures, because those days move further than usual.
- On quiet, two-sided days it loses steadily: both sides of the range get broken, and costs take most of what the small moves earn.
- Most retail intraday traders lose money after costs; treat this as a strategy to test carefully, not as a shortcut.

This guide belongs to the intraday group, with [VWAP strategies](learn-strat-vwap.md) and [intraday momentum and trend days](learn-strat-intraday-momentum.md). Only daily prices are used for the charts here. The tables of intraday prices are illustrative: they show the mechanics with made-up minute-by-minute numbers, not recorded trades.

## 1. The idea

### An example first

On 17 January 2024 HDFC Bank reported quarterly results that disappointed the market. The stock opened 6.5% below the previous close. Volume that day was about five times its 50-day average. The stock closed near the day's low, in the bottom 13% of the day's range.

```series
title: HDFC Bank — the results gap of 17 January 2024
from: 2023-11-15
to: 2024-03-15
line: india:HDFCBANK.NS | HDFC Bank
line: india:HDFCBANK.NS@vol | Volume | pane2 bars
mark: 2024-01-17 | Gap down 6.5% on results
caption: HDFC Bank opened 6.5% lower on 17 January 2024, traded about 5 times its 50-day average volume, and closed in the bottom 13% of the day's range. Prices are adjusted for later bonus issues.
```

The daily bar tells you how the day ended, but not the order of events inside it. So here is how an opening-range trader handles a day like that, on invented numbers for an invented stock that opens at 500 after bad results.

| Time (IST) | Illustrative price | What the trader does |
|---|---|---|
| 9.15–9.30 am | Trades between 496 and 503 | Waits. The first 15 minutes set the opening range: high 503, low 496. |
| 9.42 am | Falls to 495.75 | The price breaks below 496. A sell-stop order at 495.75 fills: short. |
| 9.42 am | — | Stop placed just above the range high, at 503.25. Risk per share: 7.5. |
| 11.00 am | 489 | The trade is 6.75 in profit; the stop stays where it is. |
| 3.15 pm | 487.5 | Exit at the market before the broker's automatic square-off. Profit: 8.25 a share, about 1.1R. |

On this invented path the trade earned a little more than it risked. If the day's full range was 4% (20 rupees), the trade caught well under half of it. That is normal: the opening range absorbs part of the move, and the exit at the close gives back part of the rest.

### What the trade is

The **opening range** is the highest and lowest price traded in the first N minutes of the session. N is usually 5, 15 or 30. A **breakout** of the range is a trade above its high; a **breakdown** is a trade below its low. The opening-range breakout (ORB) buys the breakout or sells the breakdown, and closes the position the same day.

### Why it can work

The open is when the night's news is turned into orders. Results, guidance, a broker's downgrade, a move in global markets: all of it arrives at once. For the first minutes buyers and sellers argue over the new price, and the range is the area of that argument. When the price leaves the range, it shows one side was larger than the first minutes revealed.

Large investors cannot buy or sell their whole order at the open. A fund cutting a bank stock after bad results will sell through the day, often benchmarked to the day's average price (see [VWAP strategies](learn-strat-vwap.md)). That steady selling is what an ORB short hopes to ride.

Toby Crabel studied this in the late 1980s. His book on opening-range breakouts (1990) tested entries a fixed distance above and below the open across many futures markets. His finding, in plain words: on many days the price moves away from the open in one direction and does not come back.

### Who is on the other side

Three groups take the other side of a breakout trade. Traders who sell rallies and buy dips inside the range — they are right on quiet days. Traders whose stop orders sit just beyond the range — their forced buying or selling adds to the move. And market makers, who provide the shares you buy and are paid by the bid-ask spread.

On a quiet day the first group wins and you pay the spread twice. On a news day the second group's stops and the funds' steady orders push the price your way. The whole strategy is a bet that today is the second kind of day.

## 2. When it works and when it doesn't

### Days that move further than usual

A breakout needs room to run. The table measures how far the price travelled on gap days compared with ordinary days. The range is the day's high minus its low, divided by the average true range (ATR) of the previous 14 days.

| Opening gap (size, either direction) | US: day's range in ATRs (median) | India: day's range in ATRs (median) |
|---|---|---|
| Under 0.5% | 0.82 | 0.84–0.86 |
| 2–4% | 0.93–0.97 | 1.03–1.09 |
| 4–8% | 1.13–1.21 | 1.26–1.27 |
| 8% or more | 1.54–1.76 | 1.77–1.90 |

*Event study, 2015–2025, liquid stocks only; the method is in section 8. Ranges show gap-up and gap-down days separately.*

A stock gapping 8% or more typically travels about twice its normal daily range. That is why practitioners concentrate ORB on "stocks in play": stocks with news, a gap or unusual early volume.

### But the gap does not tell you the direction

The same study asked whether the close finished beyond the open in the direction of the gap. For US gaps of 2–8% the answer was yes on about 48% of days: a coin toss. In India big gaps more often reversed: after gaps of 8% or more, only about a third of days kept going from the open.

So the gap is a reason to watch the stock, not a reason to take a side. The breakout of the opening range is what decides the side. Many ORB traders take the trade in either direction, whichever side breaks first.

### Range days

On a range day the price swings back and forth through the opening range and closes near where it opened. Both a long and a short may trigger, and both may be stopped. Range days are more common than trend days: in the event study, only about 18% of days opened near one end of the day's range and closed near the other.

Warning signs of a range day: no news, a small gap, volume below normal in the first half-hour, and an index waiting for a scheduled event later in the day.

### What to trade

- **Index futures**: Nifty and Bank Nifty futures in India, the E-mini S&P 500 and Nasdaq futures in the US. Deep liquidity, one spread, no single-company surprises.
- **Large, liquid stocks with news**: results days, block deals, upgrades. In India, stocks in the F&O segment (stocks with futures and options) are the usual choice, because they trade heavily and have no fixed daily price band.
- **Avoid**: thinly traded stocks, where the spread and slippage can be larger than the whole edge, and stocks near their circuit limits.

### India specifics

- **Hours**: the cash market trades 9.15 am to 3.30 pm IST. A pre-open session before 9.15 am sets the opening price for most liquid stocks through a call auction (orders are matched at one price).
- **Circuit limits**: many stocks have a fixed daily price band (2%, 5%, 10% or 20%). A stock that hits its band can stop trading in one direction, and your stop may not fill.
- **Shorting**: in the cash market you may sell short only intraday, and the position must be closed the same day. That suits ORB, which is always flat by the close.
- **Automatic square-off**: brokers close intraday (MIS) positions themselves in the last few minutes, usually between 3.15 pm and 3.25 pm, and many charge a fee for it. Exit before that, on your own terms.
- **Leverage**: intraday margin for cash stocks has been limited since the peak-margin rules of 2020–21; the maximum is roughly five times for the most liquid stocks, less for others.
- **Expiry days**: on weekly index option expiry days, index moves near the close can be driven by option positions rather than news.

### US specifics

- The regular session runs 9.30 am to 4.00 pm Eastern time.
- In a US margin account, making four or more day trades within five business days marks you as a "pattern day trader", which requires at least $25,000 of equity. FINRA has proposed changing this rule; check the current version with your broker.
- Commissions are near zero at many brokers, but the spread and slippage are not.

## 3. The rules

The rules below are one complete, testable version. Every number is a parameter, listed with its range in section 4.

### Universe and filters

- **Instrument**: an index future, or a stock whose average daily turnover over the last 20 sessions is at least ₹100 crore (India) or $100 million (US).
- **Price**: at least ₹100 or $10, so that one tick is a small part of the price.
- **In play** (for stocks): at least one of — an opening gap of 2% or more from the previous close; first-15-minute volume at least twice the average first-15-minute volume of the last 20 sessions; a scheduled news event (results, a policy decision) before the open.
- **Not near a band**: for stocks with a fixed price band, the open is at least 3 percentage points away from the band.

### Setup

- The **opening range** (OR) is the high and low of the first 15 minutes of regular trading. In India, that is 9.15 am to 9.30 am; in the US, 9.30 am to 9.45 am.
- **OR width** = OR high − OR low.
- The width must be between 0.25 and 1.0 times the 14-day ATR. Narrower ranges get broken by noise; wider ranges make the stop too far away.

### Entry

- **Long**: a buy-stop order at OR high + buffer. The buffer is 0.05% of price or two ticks, whichever is larger.
- **Short**: a sell-stop order at OR low − buffer.
- Orders are live from the end of the opening range until the entry cutoff, 90 minutes after the open. A break after that is ignored.
- One trade per instrument per day. Once one side fills, cancel the other order.
- **Optional direction filter**: on gap days, take only the side in the direction of the gap. Test this; the event study above suggests it is not obviously better.

A stop order becomes a market order when the trigger price trades, so you may fill a little worse than the trigger. Some traders use a stop-limit order instead, which caps the fill price but may not fill at all on a fast move.

### Initial stop

- **Standard**: the other side of the range. For a long, OR low − buffer; for a short, OR high + buffer.
- **Tighter variant**: the middle of the range. Smaller risk per share, more stop-outs.
- **Cap**: if the stop is more than 0.5 ATR away from the entry, use the midpoint or skip the trade.

### Exits

- **Time exit** (always): close the position at the market 10 minutes before the session ends. In India, exit by 3.15 pm, before the broker's square-off.
- **Target** (optional): a limit order at 2R from the entry. R is the distance from the entry to the initial stop.
- **Trailing stop** (optional): after the trade is 1R in profit, move the stop to breakeven; after that, trail it below the low (for a long) of the last completed 15-minute bar.
- **Invalidation** (optional): if the price closes a 5-minute bar back inside the opening range, exit. Many failed breakouts show themselves this way.

### Position size

Risk a fixed fraction of the account per trade, for example 0.25% to 0.5%. Shares = (account × risk fraction) ÷ (entry − stop).

For a ₹10 lakh account risking 0.25%, the risk is ₹2,500. With a stop 7.5 rupees away, that allows 333 shares. Then check that the position fits within the intraday margin your broker allows; if not, cut the size, never widen the stop. See [position sizing](learn-risk-sizing.md) for the general method.

### Managing the trade

- Do not move the stop further away. Ever.
- Do not re-enter the same side after a stop-out on the same day unless that rule is written down and tested.
- Stop trading for the day after a fixed daily loss, for example 1% of the account.
- Note every fill price and the trigger price; the difference is your real slippage.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Opening-range length | 15 min (5–30) | How much of the opening fight you wait out | 5 min: more trades, more false breaks. 30 min: fewer, later entries, wider stops. |
| Minimum gap for "in play" | 2% (1–4%) | Which stocks qualify | Bigger gaps mean bigger ranges but fewer trades. |
| Relative volume, first 15 min | 2× (1.5–5×) | Evidence of unusual interest | Needs intraday history to compute. |
| Minimum turnover | ₹100 crore / $100M (₹25 crore–₹500 crore) | Liquidity and slippage | Lower values raise slippage sharply. |
| Minimum price | ₹100 / $10 | Tick size relative to price | — |
| Distance from price band | 3 percentage points | Risk of a locked stock | India only. |
| OR width, in ATRs | 0.25–1.0 | Filters noise and over-wide stops | One of the most sensitive settings. |
| Entry buffer | 0.05% or 2 ticks | False triggers by a single print | Larger buffers cut false starts but give up price. |
| Entry cutoff | 90 min after the open (60–180) | Late, weaker breakouts | Later breaks have less time to run. |
| Stop placement | Other side of OR, or midpoint | Risk per share and stop-out rate | Midpoint roughly halves risk and raises the stop-out rate. |
| Stop cap | 0.5 ATR (0.3–0.75) | Maximum risk per share | — |
| Target | none, or 2R (1–3R) | Profit taking | Targets raise the win rate and cut the big winners. |
| Breakeven trigger | 1R | When risk is removed | Too early turns winners into scratches. |
| Time exit | 10 min before close; 3.15 pm IST | Overnight risk and square-off | Fixed by the strategy: ORB is flat by the close. |
| Risk per trade | 0.25–0.5% of equity | Account volatility | Intraday traders take many trades; keep it small. |
| Daily loss limit | 1% of equity | Tilt and loss streaks | — |

## 5. Variations

- **Crabel's open-plus-stretch**: Toby Crabel placed entries a set distance (his "stretch") above and below the opening price, rather than waiting for a timed range. He also favoured days after a narrow-range day. His NR4 and NR7 days are days whose range is the smallest of the last 4 or 7 days (see [candlestick patterns](learn-candlestick-patterns.md)). The idea is that quiet days tend to be followed by wider ones.
- **Larry Williams' volatility breakout**: buy when the price rises above the open by a fixed fraction of the previous day's range. It is the same idea with the range taken from yesterday rather than today's first minutes.
- **Mark Fisher's ACD method** (*The Logical Trader*, 2002): uses the opening range plus fixed offsets ("A" and "C" levels) above and below it. A trade is confirmed only if the price holds beyond the level for a set time.
- **The initial balance** (Market Profile, as taught by James Dalton in *Mind Over Markets*): the range of the first hour. A break of the first hour's range is read as a sign of a trend day; failure to extend is read as a range day.
- **Five-minute ORB on stocks in play**: recent working papers by Carlo Zarattini, Andrew Aziz and co-authors test a 5-minute opening range on US stocks with the highest relative volume that morning. They trade in the direction of the first 5-minute bar and hold to the close. These are unreviewed working papers; read their cost assumptions closely.
- **ORB with a trend filter**: take longs only when the daily trend is up (for example, the close is above the 50-day average), shorts only when it is down. This connects the day's trade to the bigger picture.

## 6. Worked examples

In each example the daily open, high, low and close are real. What happened inside the day is not stored, so each example states what the daily bar proves and what it cannot tell you.

### Example 1 — HDFC Bank, 17 January 2024 (India, the short side)

Covered in section 1. The facts from the daily bar:

| | Value |
|---|---|
| Gap from the previous close | −6.5% |
| High above the open | +1.7% |
| Low below the open | −2.7% |
| Close relative to the open | −2.1% |
| Close's position in the day's range | bottom 13% |

The close was only 0.6% above the low. So a short entered anywhere above the close, and not stopped out first, was in profit at the close. The bar cannot tell us whether the 1.7% rally above the open came in the first 15 minutes. If it did, the opening range was wide and the stop far away, and the width filter might have skipped the trade.

### Example 2 — Nifty 50, 3 June 2024 (India, a gap that went nowhere)

On Saturday 1 June 2024 the exit polls for India's general election suggested a large win for the ruling alliance. On Monday the Nifty opened 3.6% higher.

```series
title: Nifty 50 — exit-poll gap, then the results day
from: 2024-05-15
to: 2024-06-21
line: india:^NSEI | Nifty 50
mark: 2024-06-03 | Gap up 3.6%, opened at the high
mark: 2024-06-04 | Results day
caption: On 3 June 2024 the Nifty opened 3.6% above the previous close at almost exactly the day's high, and closed 0.3% below its open. The next day, results day, it fell 5.9%.
```

The day's high was less than 1 point above the open. So the opening-range high was, in effect, the day's high: a buy-stop above it never filled. The gap was a large news event, and yet the long side of ORB had no trade at all. The close was 0.3% below the open: a small move for an index that had just gapped 3.6%. Whether a short on a break of the range low made money depends on where that low was, which the daily bar cannot show.

The lesson: a big gap does not promise a big move after the open. Much of the news was already in the opening price.

### Example 3 — NVIDIA, 25 May 2023 (US, a failed long)

NVIDIA's quarterly results on the evening of 24 May 2023 included a far higher revenue forecast than expected. The stock opened 26% higher, on about 3.4 times its average volume.

```series
title: NVIDIA — the guidance gap of 25 May 2023
from: 2023-04-20
to: 2023-06-30
line: us:NVDA | NVIDIA
line: us:NVDA@vol | Volume | pane2 bars
mark: 2023-05-25 | Gap up 26%, closed below the open
caption: NVIDIA opened 26% higher on 25 May 2023, rose 2.5% above the open, fell 4.9% below it, and closed 1.4% below the open.
```

The facts are enough to judge the long side without knowing the path. A long breakout entry is always above the open, because the open is inside the opening range. The close was 1.4% below the open. So any long that triggered lost money by the close, or was stopped out earlier.

This is a case where the stock went on to rise strongly over the following weeks. A swing trader buying the gap was right; an ORB trader buying the same day's breakout was not. The two strategies answer different questions.

### Example 4 — SPDR S&P 500 ETF (SPY), 5 August 2024 (US, a failed short)

After weak US jobs data and a sharp fall in Japanese shares, SPY opened 4.0% lower on 5 August 2024.

```series
title: SPY — the gap down of 5 August 2024
from: 2024-07-01
to: 2024-09-06
line: us:SPY | SPY
line: us:VIX | VIX | right
mark: 2024-08-05 | Gap down 4.0%, closed above the open
caption: SPY opened 4.0% lower on 5 August 2024. Its low was only 0.3% below the open; it closed 1.1% above the open.
```

The day's low was just 0.3% below the open. A short breakdown entry is always below the open, so every short entry was within 0.3% of the day's low. The close was 1.4% above the low, and therefore above any short entry. Every ORB short on SPY that day lost money.

The lesson: a panic open is often the low of the day. Sellers had done their selling overnight and at the open; there was nobody left to push the price lower.

## 7. Common mistakes

- **Trading every day.** Most days are not trend days. ORB on quiet days is a slow way to pay the spread.
- **Ignoring costs.** A typical index day moves less than half a percent from open to close. A round trip that costs 0.1% is a large share of that.
- **Widening the stop** after entry because the trade "needs room". The stop is part of the measured strategy; change it and you are trading something untested.
- **Chasing a break** long after the cutoff, or entering with a market order after the price has run far past the trigger.
- **Holding past the close** in the hope of a gap tomorrow. That is a different trade with different risks; in India's cash market a short cannot be held overnight at all.
- **Using too much leverage.** Intraday margin lets you take a position several times your capital. A normal stop then becomes a large loss of capital.
- **Testing on daily data only.** Whether a stop was hit before the target cannot be known from daily bars.

## 8. What the evidence says

### Published work

- **Toby Crabel (1990)** documented opening-range and open-plus-stretch breakouts across futures markets and popularised the narrow-range day filters. His tests are from an older market with higher costs and fewer algorithms; treat them as a source of ideas, not as current evidence.
- **Intraday momentum in the index** (Gao, Han, Li and Zhou, 2018) found that the S&P 500 ETF's return in the first half-hour helps predict its return in the last half-hour. It supports the broader idea that early moves carry information. It does not test ORB directly; see [intraday momentum](learn-strat-intraday-momentum.md).
- **Day traders' results**: studies of complete trading records in Taiwan (Barber, Lee, Liu and Odean) and Brazil (Chague, De-Losso and Giovannetti) found that the large majority of day traders lose money, and that very few earn reliable profits after costs. SEBI's 2024 study of Indian intraday traders in the cash segment found that about 7 in 10 made a net loss in 2022–23.
- **Recent working papers** on 5-minute ORB in US stocks in play report good results before and after modelled costs. They are not peer-reviewed, and results of this kind tend to shrink once published and traded.

### Event study: gap days on daily data

**Method.** For every liquid stock from 2015 to 2025, each day was grouped by the size of its opening gap.
Liquid means an average daily turnover, over the prior 20 sessions, of at least $50 million in the US or ₹50 crore in India. The price also had to be at least $10 or ₹100. For each group: the median range (high − low) in multiples of the prior 14-day ATR; the share of days closing beyond the open in the gap's direction; and the share of "trend days". A trend day here means the open was in the top or bottom 20% of the day's range and the close in the opposite 20%.

**Sample.** The data behind each result:

| Market | Stock-days | Stocks |
|---|---|---|
| US | about 2.2 million | 2,296 |
| India | about 466,000 | 976 |

| Gap | US: closed beyond open in gap direction | India: closed beyond open in gap direction | US: trend days | India: trend days |
|---|---|---|---|---|
| 2–4% up | 47.7% | 41.9% | 19.1% | 20.9% |
| 2–4% down | 48.0% | 41.9% | 18.5% | 20.4% |
| 4–8% up | 47.5% | 40.0% | 19.8% | 22.3% |
| 4–8% down | 48.7% | 38.2% | 17.6% | 21.4% |
| 8%+ up | 45.8% | 35.9% | 19.6% | 29.0% |
| 8%+ down | 53.0% | 31.1% | 17.9% | 32.8% |
| All days | — | — | 18.0% | 17.5% |

**What it shows.** Gap days have wider ranges, so a breakout has more room (section 2).
The gap's direction is not a reliable guide to the rest of the day, and in India large gaps more often reversed after the open. Trend days are a minority on any kind of day.

**Caveats.** The stock lists are today's, so companies that later failed are missing (survivorship bias).
About 6% of Indian stock-days in the data have an open exactly equal to the previous close, which is suspicious; they fall in the smallest-gap group and do not affect the rows above. In India some big gaps open at or near a price band, which limits the move in one direction. Most important, daily bars cannot show whether an ORB trade would have been stopped before the close. This study describes the days ORB trades in; it does not test ORB.

### What is not known

Whether a simple ORB has a lasting edge after realistic costs in Indian stocks is not established in published research. The honest default is that it does not, until your own careful test says otherwise.

## 9. Building and testing it yourself

### Data

You need intraday bars: 1-minute or 5-minute open, high, low, close and volume for every stock and day you test. Daily bars are not enough, because the order of the high and low within the day decides whether the stop or the exit came first. Include the previous close and 14-day ATR, computed from daily bars up to the previous day only.

### Look-ahead traps

- The opening range is only known when its last minute ends. No order can be placed before then.
- "Stocks in play" must be chosen with information available at the time: the gap and the first minutes' volume, not the whole day's volume.
- If both the stop and the target fall inside one bar, you cannot know which came first. Assume the stop did.
- Daily ATR must come from the previous day, not including today.

### Survivorship

Test on the stocks that were listed and liquid on each date, including those since delisted. A list of today's stocks hides the companies that collapsed.

### Costs and slippage

Approximate costs for an intraday round trip (buy and sell the same day) in the Indian cash market:

| Cost | Rough size |
|---|---|
| Brokerage (discount broker) | ₹20 per order or 0.03%, whichever is lower |
| STT | 0.025% on the sell side |
| Exchange transaction charges | about 0.003% each side |
| Stamp duty | 0.003% on the buy side |
| GST | 18% on brokerage and exchange charges |
| Slippage and spread | 0.02–0.10% each side, more on fast breakouts |

On a ₹1 lakh position the charges come to roughly ₹80, about 0.08% for the round trip, before slippage. Index futures have lower charges per rupee traded, but STT on futures sales was raised in October 2024 and again in April 2026, to 0.05%. In the US, commissions are often zero, but the spread and slippage remain. Model slippage on stop entries as worse than the trigger, because breakouts fill in a hurry.

### What to test, and how not to fool yourself

- Vary one parameter at a time: range length, width filter, stop placement, cutoff. Look for broad plateaus where results stay similar, not a single best value.
- Keep the last two or three years out of the tuning, and test the final rules on them once.
- Split results by gap size, by market (India and US), and by year. A strategy that only worked in 2020 is not robust.
- Report the number of trades, win rate, average win and loss in R, expectancy after costs, maximum drawdown, and the share of profit from the best 10 days. See [backtesting](learn-test-backtesting.md).

### Core logic

```
for each day, for each instrument passing the universe filters:
    or_high, or_low = max(high), min(low) over the first OR_MINUTES bars
    width = or_high - or_low
    if not (W_MIN * atr14_yesterday <= width <= W_MAX * atr14_yesterday): skip
    long_trigger  = or_high + buffer
    short_trigger = or_low  - buffer
    for each bar after the opening range, until ENTRY_CUTOFF:
        if bar.high >= long_trigger:  enter long at max(long_trigger, bar.open) + slippage
                                      stop = short_trigger (or midpoint); break
        if bar.low  <= short_trigger: enter short, mirror image; break
    manage: if a bar touches the stop -> exit at the stop (worse if it gaps)
            if target used and touched -> exit at target (stop first if both in one bar)
    at EXIT_TIME: exit at the bar's close minus slippage
    record R = (exit - entry) / (entry - initial stop), net of costs
```

## 10. Checklist

- [ ] Is this instrument liquid enough (turnover, price, spread)?
- [ ] Is it in play today: a gap, news, or unusual early volume?
- [ ] Is a big scheduled event due later in the day that could reverse the move?
- [ ] Is the opening range between 0.25 and 1.0 ATR wide?
- [ ] Are both stop orders placed, with the buffer, and set to cancel each other?
- [ ] Is the size calculated from the stop, and does it fit the margin limit?
- [ ] Is the stock well away from its price band?
- [ ] Is the exit time set, before the broker's square-off?
- [ ] Have I already hit today's loss limit?

## Further reading

- Toby Crabel, *Day Trading with Short Term Price Patterns and Opening Range Breakout* (1990).
- Mark B. Fisher, *The Logical Trader: Applying a Method to the Madness* (2002).
- James F. Dalton, Eric T. Jones and Robert B. Dahlquist, *Mind Over Markets* (1990; updated edition 2013).
- Larry Williams, *Long-Term Secrets to Short-Term Trading* (1999).
- Lei Gao, Yufeng Han, Sophia Zhengzi Li and Guofu Zhou, "Market Intraday Momentum", *Journal of Financial Economics* (2018).
- Brad M. Barber, Yi-Tsung Lee, Yu-Jane Liu and Terrance Odean, "The Cross-Section of Speculator Skill: Evidence from Day Trading", *Journal of Financial Markets* (2014).
- Fernando Chague, Rodrigo De-Losso and Bruno Giovannetti, "Day Trading for a Living?" (working paper, 2019).
- SEBI, study of profit and loss of individual intraday traders in the equity cash segment (July 2024).
