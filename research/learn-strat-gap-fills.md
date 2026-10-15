# Gap fills and gap trading — fading the gap or riding it

**In short**

- A **gap** is a jump between one day's close and the next day's open. It is "filled" when the price later trades back to the previous close.
- Traders sort gaps into common, breakaway, runaway and exhaustion gaps. Common gaps tend to fill; breakaway gaps on news and heavy volume often do not.
- "Gaps always fill" is false. On stored data, about 1 in 7 US gap-ups of 5% to 10% was still unfilled a year later. Small gaps filled quickly, mostly because daily price swings are about that size anyway.
- There are two opposite trades: **fading** the gap (betting on the fill) and **trading the continuation** (betting it holds). Which one fits depends on the gap's size, volume, news and where it starts.
- A gap that runs into new highs on heavy volume is a reason not to fade it.

This guide belongs to the mean-reversion group, with [RSI(2) mean reversion](learn-strat-rsi2.md) and [Bollinger band reversion](learn-strat-bollinger-reversion.md). The continuation trade on results is covered in [earnings gaps and episodic pivots](learn-strat-earnings-gaps.md). Intraday versions are covered in [opening-range breakouts](learn-strat-orb.md).

## 1. The idea

### An example first

On Saturday 1 June 2024, exit polls for India's general election were published. On Monday 3 June, Reliance Industries opened 3.7% above Friday's close of 1,430.40. It traded at a new 52-week high. Election results came the next day and the market fell sharply. Reliance traded down to 1,359.30 on 4 June, below Friday's close: the gap was filled within one session.

```series
title: Reliance Industries — a gap filled the next day, June 2024
from: 2024-04-01
to: 2024-07-31
line: india:RELIANCE.NS | Reliance Industries
line: india:RELIANCE.NS@vol | Volume | pane2 bars
mark: 2024-06-03 | Gap up 3.7% on exit polls
caption: The gap up of 3 June 2024 was filled on 4 June, when the election results came out. The stock then recovered and went higher.
```

Now a second case. Kaynes Technology gapped up 9.8% on results on 17 May 2023, with volume about 14 times normal. It never traded back to the previous close of 998.95. The first gap was news that the market reversed. The second was news that changed what the company was worth.

### What the trade is

A **gap up** opens above the previous close; a **gap down** opens below it. A **full gap** leaves an empty space on the chart: the day's whole range is above the previous day's high (or below its low). A gap is **filled** when the price trades back to the previous close.

The **fade** trades against the gap, expecting a fill: sell (or short) a gap up, buy a gap down. The **continuation trade** goes with the gap: buy a gap up, sell a gap down, expecting it to hold.

### The four kinds of gap

Robert Edwards and John Magee described four kinds in *Technical Analysis of Stock Trends* (1948):

| Kind | Where it happens | Volume | Usual outcome |
|---|---|---|---|
| Common gap | Inside a trading range, no major news | Normal | Usually filled within days |
| Breakaway gap | Out of a range or base, often on news | Heavy | Often not filled for a long time |
| Runaway (measuring) gap | In the middle of a strong trend | Above normal | Often not filled; the trend continues |
| Exhaustion gap | After a long, fast move | Very heavy | Filled soon; the move is ending |

The labels are given with hindsight. On the day, a breakaway gap and an exhaustion gap can look the same. The study in section 8 uses simple rules to tell them apart.

### Why fills happen, and why some don't

In India, overnight news is turned into an opening price by a short pre-open auction, which takes orders from 9:00 am. Orders at the open come mostly from people reacting fast, and from stop orders. When the news is minor, the reaction is too large, and later trading brings the price back. When the news is big, buyers keep coming for days and the gap holds.

### Who is on the other side

A fader of a gap up sells to buyers who rushed in at the open. If the news is minor, those buyers paid too much. If it is major, the fader is selling to well-informed funds, and loses. A continuation buyer faces the reverse risk.

## 2. When it works and when it doesn't

**Fading works on small gaps without news.** Gaps of 2% to 5% inside a trading range, on normal volume, filled most often. Market-wide gaps (the whole index gapping on global news) also tend to fill in liquid large stocks.

**Fading fails on news gaps.** Results, takeover bids, regulatory decisions and guidance changes move value for good. A gap on several times normal volume, out of a base or to a new 52-week high, is the worst gap to fade.

**After a long run, gaps fill.** A gap up after a stock has risen 50% or more in three months often marks exhaustion. In the US these gaps filled more often than any other kind, and the stock fell afterwards (section 8).

**India.** The opening price comes from the pre-open call auction, so gaps in India are set in one price, not in a few seconds of trading. Stocks outside the futures list have price bands; a stock that opens locked at its band cannot be traded. 

Fading a gap up in India means selling short. In the cash market that is only possible intraday. Holding the fade overnight needs stock futures, which exist only for larger stocks. Gap-down fades (buying) are simple, with T+1 settlement.

**US.** Gaps form in pre-market trading, which is thin. Many US results come out before the open or after the close, so results gaps are common. Shorting a gap up overnight is possible if the shares can be borrowed.

## 3. The rules

These rules describe two separate strategies. Test them separately.

### Universe and filters

- Price above ₹100 or $10; 20-day average traded value above ₹10 crore or $10 million.
- For the fade: the stock is in a large-cap or mid-cap index.

### Setup — the fade (a gap down, buying the fill)

- The open is 2% to 8% below the previous close (*fade gap range*).
- Volume on the gap day is below 2 times its 50-day average (*fade volume limit*).
- The low of the gap day is above the 52-week low: no new low.
- The close of the previous day is above the 200-day average (the stock was in an uptrend).
- No results or stock-specific news. A market-wide gap is preferred: the index also gapped down by 1% or more.

### Setup — the continuation (a gap up, buying strength)

- The open is at least 3% above the previous close (*continuation minimum gap*).
- Volume at least 2 times its 50-day average (*continuation volume*).
- The high of the gap day is a new 52-week high, or above the top of a base of at least 6 weeks.
- A news check: the news is a lasting change (results, a large order, an approval).
- The stock has not risen more than 50% in the last 60 sessions (*run-up limit*). Otherwise it may be an exhaustion gap.

### Entry

- Fade, swing version: buy at the gap day's close, if the close is above the gap day's low by at least a third of the day's range. Intraday version: buy when the price trades above the high of the first 15 or 30 minutes.
- Continuation: buy on a move above the gap day's high in the next 5 sessions.

### Initial stop

- Fade: below the gap day's low.
- Continuation: below the gap day's low. If that is more than 12% away, skip the trade.

### Exits

- Fade: target the previous close (the fill). Time stop: 10 sessions (*fade time stop*).
- Continuation: trail with the 20-day average; time stop 10 sessions if the price is not above the entry.

### Position size

Risk 0.5% of capital per trade, sized from the stop. Market-wide gap days give many signals at once; cap the total at 3 to 5 fade trades on the same day, because they all depend on the same market move.

### Managing the trade

- Fade: if the price closes below the gap day's low, the gap was not common. Exit.
- Continuation: if the price trades back into the gap and closes below the previous day's close, the gap has failed. Exit.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| *Fade gap range* | 2–8% | Which gaps to fade | Smaller gaps fill more often but pay less |
| *Fade volume limit* | Below 2× (1.5–3×) | Excludes news gaps | Key filter |
| Trend filter | Above the 200-day | Buys dips in uptrends only | |
| Market-wide gap | Index gap 1% or more | Prefers gaps without company news | |
| *Fade time stop* | 10 sessions (3–20) | Exit if no fill | About 70% of small gaps filled within 5 sessions |
| *Continuation minimum gap* | 3% (3–10%) | Which gaps to ride | |
| *Continuation volume* | 2× (2–5×) | Signs of large buyers | |
| New high or base breakout | 52-week high or 6-week base | The breakaway context | |
| *Run-up limit* | 50% in 60 sessions | Avoids exhaustion gaps | Exhaustion gaps filled most often |
| Stop cap | 12% | Skips very wide stops | |
| Risk per trade | 0.5% | Account risk | |

## 5. Variations

- **Edwards and Magee.** The classic view: common and exhaustion gaps fill, breakaway and runaway gaps do not. The runaway gap is used to project a target: the move after it is often about as long as the move before it.
- **Intraday gap fades.** Many day traders fade small opening gaps in index futures and large stocks, targeting the previous close the same day. In the study below, about 4 in 10 small US gaps and half of small Indian gaps filled on the gap day itself. See [opening-range breakouts](learn-strat-orb.md) for the opposite intraday trade.
- **Island reversals.** A gap up, a few days of trading, then a gap down, leaving the days in between as an "island". It is treated as a strong reversal signal.
- **Buyable gap-ups.** The continuation trade on results, with the stop at the gap day's low, is the core of the [episodic pivot](learn-strat-earnings-gaps.md).
- **Overnight against intraday returns.** Lou, Polk and Skouras (2019) found that some stock returns are earned mostly overnight and others mostly during the day. Gaps are where the overnight part shows.

## 6. Worked examples

### Reliance Industries, April 2025 (India): the fade worked

In early April 2025 markets around the world fell after new US tariffs were announced. On 7 April 2025 Reliance opened 6.0% below the previous close of 1,204.70. Volume was about 1.9 times normal: below the fade volume limit. There was no company news; the whole market gapped down.

```series
title: Reliance Industries — a market-wide gap down that filled, April 2025
from: 2025-02-15
to: 2025-06-15
line: india:RELIANCE.NS | Reliance Industries
line: india:RELIANCE.NS@sma200 | 200-day average
line: india:RELIANCE.NS@vol | Volume | pane2 bars
mark: 2025-04-07 | Gap down 6.0% with the whole market
caption: The gap filled within four sessions, and the stock kept rising into May.
```

| Step | Date | Value |
|---|---|---|
| Gap day | 7 Apr 2025 | Open 1,132.20, low 1,114.85, close 1,165.70 |
| Entry | Close, 7 Apr 2025 | 1,165.70 (closed well off the low) |
| Stop | | Below 1,114.85: risk about 4.4% |
| Target | | The previous close, 1,204.70 |
| Filled | 11 Apr 2025 | High 1,222.65: exit at 1,204.70, +3.3% |

One caveat: the stock was below its 200-day average, so the trend filter in section 3 was not met. A strict rule-follower would have skipped this trade. It worked, but that is one case.

### Trent, July 2025 (India): the fade failed

On 4 July 2025 Trent opened 8.3% below the previous close of 6,191, and fell to 5,350 during the day. It closed at 5,456, down 11.9%. Volume was about 6 times normal.

```series
title: Trent — a gap down that did not fill, July 2025
from: 2025-05-01
to: 2025-10-31
line: india:TRENT.NS | Trent
line: india:TRENT.NS@sma50 | 50-day average
line: india:TRENT.NS@vol | Volume | pane2 bars
mark: 2025-07-04 | Gap down 8.3% on heavy volume
caption: The gap was never filled. The highest close in the following months was 5,529.
```

The fade rules would have rejected this trade twice. The gap was larger than 8%, and volume was above 2 times normal. A trader who bought it anyway, expecting the "gap must fill", waited in vain. Through October 2026 the price never traded back to 6,191.

### Kaynes Technology, May 2023 (India): a breakaway gap

| Step | Date | Value |
|---|---|---|
| Gap day | 17 May 2023 | Open 9.8% above the previous close of 998.95; volume about 14× normal |
| Continuation entry | 18 May 2023 | Above the gap day's high, 1,190 |
| Stop | | The gap day's low, 1,075.10 |
| Fill | Never | The gap never filled |

This is the case where fading loses the most and the continuation trade wins. The details are in [earnings gaps](learn-strat-earnings-gaps.md).

## 7. Common mistakes

- **Believing "gaps always fill".** Some gaps fill after years, some never. A trade needs a fill within days.
- **Fading news.** Check the news before fading any gap. Results gaps are the worst to fade.
- **Ignoring volume.** Heavy volume on a gap means large investors acted. Do not stand in front of them.
- **Shorting a gap up overnight in Indian cash shares.** It is not allowed; positions are squared off the same day. Use futures, or trade intraday only.
- **Counting fills from the wrong price.** A gap is filled at the previous close (or the previous high for a full gap). Be consistent in tests.

## 8. What the evidence says

**Published research.** Edwards and Magee's classification is descriptive, from chart reading. Thomas Bulkowski catalogued gap statistics in his books on chart patterns. Academic work on overnight returns (Lou, Polk and Skouras, 2019) shows that overnight and daytime returns behave differently, but there is little peer-reviewed work testing gap-fill trading rules directly.

**Event study on stored data.** For liquid stocks, I found every day that opened at least 2% away from the previous close. A gap is "filled" when a later low (for a gap up) or high (for a gap down) reaches the previous close. Fill times count the gap day as day 0. I only used gaps with at least 250 sessions of data after them.

US, 2005–2026, share of gaps filled within:

| Gap | Events | Same day | 5 sessions | 20 sessions | 60 sessions | 250 sessions |
|---|---|---|---|---|---|---|
| Up 2–5% | 243,216 | 40% | 70% | 83% | 89% | 93% |
| Up 5–10% | 40,274 | 26% | 53% | 69% | 78% | 86% |
| Up 10% or more | 11,219 | 17% | 41% | 56% | 69% | 82% |
| Down 2–5% | 239,698 | 38% | 70% | 84% | 91% | 96% |
| Down 5–10% | 38,918 | 25% | 54% | 70% | 82% | 92% |
| Down 10% or more | 11,409 | 11% | 28% | 43% | 58% | 75% |

India, 2004–2026:

| Gap | Events | Same day | 5 sessions | 20 sessions | 60 sessions | 250 sessions |
|---|---|---|---|---|---|---|
| Up 2–5% | 57,502 | 51% | 76% | 86% | 91% | 95% |
| Up 5–10% | 5,979 | 33% | 61% | 76% | 84% | 91% |
| Up 10% or more | 916 | 32% | 54% | 69% | 77% | 87% |
| Down 2–5% | 37,883 | 52% | 78% | 87% | 92% | 96% |
| Down 5–10% | 6,209 | 38% | 67% | 78% | 85% | 92% |
| Down 10% or more | 1,319 | 36% | 69% | 76% | 81% | 88% |

By kind of gap (gaps of 3% or more), with the median return from the gap day's close:

| Kind (rule used) | Market | Events | Filled within 20 sessions | Median return after 20 sessions | After 60 sessions |
|---|---|---|---|---|---|
| Common gap up: inside the 52-week range, volume below 1.5× | US | 74,429 | 82% | +0.4% | +2.8% |
| Breakaway gap up: new 52-week high, volume 2× or more | US | 11,033 | 48% | +0.2% | +0.4% |
| Exhaustion candidate: gap up after a 50%+ rise in 60 sessions | US | 15,410 | 89% | −6.6% | −12.3% |
| Common gap up | India | 13,970 | 85% | +1.3% | +2.1% |
| Breakaway gap up | India | 3,447 | 73% | +0.3% | +1.1% |
| Exhaustion candidate | India | 5,234 | 85% | −1.1% | −1.8% |

**What this says.** Most gaps fill eventually, but not all, and not soon enough for every trade. Bigger gaps fill less often, especially large gaps down in the US. Breakaway gaps in the US filled within 20 sessions only about half the time. 

The clearest result was the exhaustion gap. In the US, gaps up after a 50% run filled 89% of the time within 20 sessions. Over 60 sessions, those stocks fell by a median 12.3%. In India, gaps filled more often across the board, and breakaway gaps were less distinct.

A fill does not mean a profitable fade. A 2% gap is about one normal day's range, so the price often touches the previous close by chance. A real test must include the stop and the cost of the trade.

**Caveats.** Today's stock lists (survivorship bias). Daily data cannot show the order of moves within a day. The "kind" rules are simple stand-ins for what chart readers judge by eye.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume; for intraday fades, minute bars; a news or results calendar; delisted stocks.

**Look-ahead traps.**
- The gap is known at the open, but the gap day's volume and close are not. A rule that uses the day's volume cannot enter at the open.
- "Filled" must be checked only on days after the entry.

**Survivorship.** Stocks that gapped down and kept falling until delisting are the fade's worst trades. Include them.

**Costs (India, approximate).** Delivery: about 0.25% to 0.35% per round trip. Intraday: lower STT (about 0.025% on the sell side) but a short holding time, so slippage matters more. Futures: a small STT on the sell side, plus margin. On a gap day spreads are wider than usual; allow extra slippage.

**What to test.** The fade and the continuation as separate strategies. For the fade: gap size, volume limit, trend filter, market-wide or not. For the continuation: gap size, volume, new-high requirement. Results by year and by market direction.

**What a good test reports.** Trades, fill rate within the time stop, average gain and loss, the worst trade, how many signals came on the same days, and results by year.

```
for each day t with gap = open[t]/close[t-1] - 1:
    # fade a gap down
    if -8% <= gap <= -2% and volume[t] < 2 * avg_volume_50[t-1]
       and close[t-1] > sma200[t-1] and no company news:
        buy at close[t]; target = close[t-1]; stop = low[t]
        exit on target | stop | 10 sessions
    # ride a gap up
    if gap >= 3% and volume[t] >= 2 * avg_volume_50[t-1]
       and high[t] > highest_high_252[t-1] and close[t-1]/close[t-61] < 1.5:
        buy above high[t] within 5 sessions; stop = low[t]
        exit on close < sma20 | stop | 10 sessions without gain
```

## 10. Checklist

- [ ] What kind of gap is it: common, breakaway, runaway or exhaustion?
- [ ] Is there news, and is it a lasting change?
- [ ] How heavy is the volume compared with normal?
- [ ] Where does the gap start: inside a range, out of a base, or after a long run?
- [ ] Fade: is the gap between 2% and 8%, on normal volume, in an uptrending stock?
- [ ] Continuation: is it a new high on heavy volume, not after a 50% run?
- [ ] Where is my stop (beyond the gap day's extreme), and my time stop?
- [ ] India: can I hold this position overnight (long, or short through futures)?

## Further reading

- Robert D. Edwards and John Magee, *Technical Analysis of Stock Trends* (1948; later editions revised by W. H. C. Bassetti).
- Thomas N. Bulkowski, *Encyclopedia of Chart Patterns* (Wiley, 2nd ed. 2005).
- Dong Lou, Christopher Polk and Spyros Skouras, "A tug of war: Overnight versus intraday expected returns", *Journal of Financial Economics* (2019).
- Gil Morales and Chris Kacher, *Trade Like an O'Neil Disciple* (Wiley, 2010).
