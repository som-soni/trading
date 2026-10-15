# VWAP strategies — trading around the day's average price

**In short**

- VWAP (volume-weighted average price) is the average price paid for a stock since a starting point, with each trade weighted by its size.
- Large investors use it to judge their own trading, and many of their orders are executed to track it, so the price often reacts near it.
- Three trades use it: buying pullbacks to VWAP on a trend day, fading stretched moves back to VWAP on a range day, and anchored VWAP, which starts the average at an event.
- Anchored VWAP also works on daily charts, which makes it useful to swing traders, not only day traders.
- VWAP is a reference line, not a signal on its own; the evidence for it as a trading edge is mostly practitioner experience, not published research.

This guide belongs to the intraday group, with [opening-range breakouts](learn-strat-orb.md) and [intraday momentum and trend days](learn-strat-intraday-momentum.md). Charts here use daily prices. The intraday tables are illustrative: invented numbers that show the mechanics, not recorded trades.

## 1. The idea

### An example first

On 4 June 2024, the day India's election results came in below expectations, ICICI Bank fell to a low of 1,053.55 and closed at 1,071.45. Take that day as a starting point, and compute the average price paid by every buyer from then on, weighted by volume. That running average is an **anchored VWAP**: anchored to the results day.

```series
title: ICICI Bank after the 2024 election-results day
from: 2024-05-01
to: 2024-09-30
line: india:ICICIBANK.NS | ICICI Bank
line: india:ICICIBANK.NS@vol | Volume | pane2 bars
mark: 2024-06-04 | Anchor: results day
caption: Anchored at 4 June 2024, ICICI Bank's VWAP rose from about 1,095 to about 1,206 by 30 September; the stock closed below it on only 11 of the next 81 sessions and ended at 1,273.
```

| Date | Close | Anchored VWAP (daily approximation) | Close vs VWAP |
|---|---|---|---|
| 4 Jun 2024 (anchor) | 1,071.45 | 1,094.80 | below |
| 5 Jun 2024 | 1,108.65 | 1,094.56 | above |
| 3 Jul 2024 | 1,201.60 | 1,148.32 | above |
| 1 Aug 2024 | 1,210.10 | 1,178.89 | above |
| 30 Aug 2024 | 1,229.20 | 1,181.50 | above |
| 30 Sep 2024 | 1,273.00 | 1,205.63 | above |

From the day after the anchor, the stock held above the average price paid since the shock on most days. On the few days it dipped below, it came back within days. Everyone who had bought since the results day was, on average, in profit, and had little reason to sell in a panic.

### What VWAP is

VWAP is the total value traded divided by the total volume traded, from a starting point.

VWAP = Σ (price × volume) ÷ Σ volume

Each bar's price is usually its typical price, (high + low + close) ÷ 3. The **session VWAP** starts again every morning at the open. The **anchored VWAP** starts at a date you choose, and keeps running across days.

A small worked example, with invented 15-minute bars:

| Bar | High | Low | Close | Volume | Typical price | VWAP so far |
|---|---|---|---|---|---|---|
| 1 | 102.0 | 100.0 | 101.5 | 50,000 | 101.17 | 101.17 |
| 2 | 103.0 | 101.0 | 102.8 | 30,000 | 102.27 | 101.58 |
| 3 | 103.5 | 102.0 | 102.4 | 20,000 | 102.63 | 101.79 |
| 4 | 102.6 | 101.9 | 102.4 | 15,000 | 102.30 | 101.86 |
| 5 | 104.0 | 102.3 | 103.8 | 25,000 | 103.37 | 102.13 |

Heavy volume pulls VWAP towards its price. Bar 1 traded the most, so VWAP stays closer to bar 1's price than a simple average of the five bars would.

### Why institutions use it

In 1988 Berkowitz, Logue and Noser proposed VWAP as a benchmark for the cost of a large trade. If a fund bought below the day's VWAP, it bought better than the average buyer that day. The idea spread: today many brokers offer VWAP algorithms, which split a large order across the day in proportion to normal volume. Traders at funds are often measured against VWAP.

This has two effects that matter to a smaller trader. First, there are large orders working through the day whose aim is to trade near VWAP, so buying and selling interest gathers around it. Second, VWAP is a fair summary of who is winning: above it, the average buyer of the day is in profit; below it, in loss.

In India the line matters for another reason. NSE sets a stock's official closing price as the volume-weighted average of the last 30 minutes of trading, not the last trade.

### Who is on the other side

In a **pullback** trade you buy from short-term sellers taking profits, and you rely on larger buyers who see a price near VWAP as good value. In a **reversion** trade you sell to late buyers chasing a stretched move, and you rely on the price drifting back to where most volume traded. In an **anchored VWAP** trade you buy from holders who are giving up near their breakeven, and you rely on buyers since the event defending their average.

## 2. When it works and when it doesn't

### Trend day or range day

The pullback and the reversion trade want opposite kinds of day.

| Type of day | What price does around VWAP | Trade that suits it |
|---|---|---|
| Trend day | Stays on one side; VWAP slopes steadily; pullbacks stop near it | Pullback to VWAP in the trend's direction |
| Range day | Crosses VWAP many times; VWAP is flat | Fade stretched moves back to VWAP |
| News reversal | Crosses VWAP once, decisively, and stays on the other side | Neither, until the new side is clear |

Trend days are a minority. On daily data from 2015 to 2025, only about one day in five opened near one end of its range and closed near the other. See [intraday momentum and trend days](learn-strat-intraday-momentum.md) for how to tell the two apart early.

The slope of VWAP is the quickest clue. A rising VWAP means buyers keep paying higher prices. A flat VWAP with price crossing it repeatedly means no side is in control.

### Anchored VWAP: when the anchor means something

An anchor works when many traders would agree the date mattered. Good anchors: a results gap, a major high or low, a breakout day, a listing day, an index inclusion, a policy decision. A random date gives a random line.

### Where it suits, and where it doesn't

It suits liquid stocks and index futures, where VWAP reflects real institutional trading. It does not suit thin stocks, where a few trades move VWAP and the spread is larger than the edge. A cash index has no volume of its own, so use the index future's VWAP.

### India and US notes

- Session VWAP restarts at each open: 9.15 am IST in India, 9.30 am Eastern time in the US.
- In India's cash market a short must be closed the same day, and brokers square off intraday positions in the last minutes, usually 3.15–3.25 pm. A swing short needs futures.
- Stocks with fixed price bands can lock at the band; a VWAP rule does not help if you cannot trade. US day traders face the pattern-day-trader rule (see [opening-range breakouts](learn-strat-orb.md)).

## 3. The rules

Three separate strategies follow. Pick one, test it alone, and only then think about combining them.

### Universe and filters (all three)

- Average daily turnover over the last 20 sessions of at least ₹100 crore in India or $100 million in the US.
- Price at least ₹100 or $10.

### Strategy A — pullback to VWAP on a trend day

**Setup.**
- The first 30 minutes have ended.
- Price has stayed above session VWAP for at least the last 30 minutes.
- VWAP now is higher than it was 30 minutes ago (rising slope).
- The day's high so far is at least 0.5 ATR above VWAP, showing a real move away from it.

**Entry.**
- Wait for a pullback: a 5-minute bar whose low comes within 0.1% of VWAP, or touches it.
- That bar must close above VWAP.
- Buy with a stop order just above that bar's high. If it does not trigger within the next three bars, cancel.
- No new entries in the last 60 minutes.

**Initial stop.** The lower of the pullback bar's low and VWAP, minus a buffer of 0.1%.

**Exits.**
- Exit at the market 10 minutes before the close (by 3.15 pm in India).
- Exit if a 5-minute bar closes below VWAP by more than the buffer: the trend-day premise has failed.
- Optional target: the day's high, or 2R.

The short side is the mirror image, on a day when price stays below a falling VWAP.

### Strategy B — reversion to VWAP on a range day

**Setup.**
- At least 60 minutes have passed since the open.
- VWAP has moved less than 0.2% over the last 60 minutes (flat).
- Price has crossed VWAP at least twice since the open.
- Price is now at least 2 standard deviations from VWAP. The standard deviation here is the volume-weighted spread of prices around VWAP since the open, the same calculation that draws the usual "VWAP bands".

**Entry.** Sell short (above VWAP) or buy (below it) when a 5-minute bar closes back inside the 2-standard-deviation band.

**Initial stop.** Beyond the extreme of the stretched move, plus a buffer of 0.1%.

**Exits.**
- Target: VWAP itself.
- Time stop: exit if VWAP is not reached within 60 minutes.
- Exit at the market 10 minutes before the close in any case.
- Invalidation: if VWAP starts to slope (moves more than 0.2% in 30 minutes) in the direction of the move, exit. The range day is turning into a trend day.

### Strategy C — anchored VWAP on a daily chart (swing)

**Setup.**
- Choose an anchor day from a fixed list: a results gap of at least 5% on at least twice the 50-day average volume; or the day of a major low or high, defined as the lowest or highest close of the last 250 sessions.
- Compute the daily anchored VWAP from that day: each day's typical price, weighted by that day's volume.
- The stock is above its 50-day average, and the 50-day is higher than 20 sessions ago.
- The anchored VWAP itself is higher than 10 sessions ago (it is still rising).

**Entry.**
- The stock pulls back so that its daily low is within 1% of the anchored VWAP.
- The same day's close is above the anchored VWAP.
- Buy at the next day's open, or on a stop order above that day's high.

**Initial stop.** A close more than 1 ATR below the anchored VWAP; exit at the next open. A single close just below the line is not a stop.

**Exits.**
- Trailing: a close below a newer anchored VWAP, started at the most recent swing low.
- Time: if the stock has not made a new 20-day high within 30 sessions of entry, exit.

### Position size (all three)

Risk a fixed fraction of equity on each trade. Use 0.25–0.5% for the intraday strategies. The swing version can take 0.5–1%.

Shares = risk amount ÷ (entry − stop). For intraday trades, also check that the position fits the margin your broker allows; reduce size, not the stop. See [position sizing](learn-risk-sizing.md).

### Managing the trade

- In Strategy A, once the trade is 1R in profit, move the stop to breakeven.
- In Strategy B, take the target at VWAP; do not hope for more. The trade's logic ends there.
- In all three, stop for the day after a fixed loss, for example 1% of equity.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum turnover | ₹100 crore / $100M | Liquidity, slippage | Lower values make VWAP noisy. |
| Minimum price | ₹100 / $10 | Tick size relative to price | — |
| A: wait after the open; time above VWAP; slope look-back | 30 min each (15–60) | Lets VWAP settle; proof of a trend day | Longer = fewer, cleaner trades. |
| A: move away from VWAP | 0.5 ATR (0.3–1.0) | Real trend versus drift | — |
| A: touch distance | 0.1% (0–0.25%) | What counts as a pullback | Too wide and every wiggle counts. |
| A: trigger window; no-entry window before close | 3 bars; 60 min | Stale signals; late trades with no room | — |
| A/B: stop buffer | 0.1% (0.05–0.25%) | Stop-outs by noise | — |
| B: wait after the open | 60 min | Time to judge a range day | — |
| B: flat VWAP; crosses of VWAP | under 0.2% in 60 min; 2 or more | Range-day test | Flatness is the most important B setting. |
| B: stretch | 2 standard deviations (1.5–3) | How far is "too far" | Higher = fewer, better trades. |
| B: time stop | 60 min (30–90) | Dead trades | — |
| C: anchor gap; major low/high look-back | 5% on 2× volume; 250 sessions | Which events count | — |
| C: touch distance | 1% (0.5–2%) | What counts as a test | — |
| C: stop | 1 ATR beyond VWAP | Room to breathe | — |
| C: time stop | 30 sessions | Dead money | — |
| Exit before close | 10 min; 3.15 pm IST | Overnight risk, square-off | Fixed for A and B. |
| Risk per trade | 0.25–0.5% (intraday); 0.5–1% (swing) | Account volatility | — |
| Daily loss limit | 1% of equity | Loss streaks | — |

## 5. Variations

- **Brian Shannon's anchored VWAP**: Shannon popularised anchoring VWAP to events and credits Paul Levine with the idea. His book *Maximum Trading Gains with Anchored VWAP* (2023) anchors to earnings gaps, major highs and lows and the start of a trend. He reads the line as the average cost of the buyers (or sellers) since the event.
- **VWAP bands**: the standard-deviation bands of Strategy B. Some traders use percentage bands instead (for example 1% either side).
- **Multiple anchors**: some traders draw several anchored VWAPs at once — from the year's high, the year's low and the last results day — and look for prices where two lines meet.
- **Opening-range plus VWAP**: buy an opening-range breakout only when price is also above VWAP (see [opening-range breakouts](learn-strat-orb.md)).
- **Execution, not signal**: many large investors use VWAP only to judge execution quality. A swing trader can do the same: compare your fill price with the day's VWAP to see whether you are buying well.

## 6. Worked examples

Daily prices are real; anchored VWAPs are computed from daily bars (typical price and daily volume), which is an approximation of the true trade-by-trade figure. Prices are adjusted for later splits and bonus issues.

### Example 1 — ICICI Bank from 4 June 2024 (India, it worked)

The anchor, the chart and the values are in section 1. Applying Strategy C's rules:

| Step | What happened |
|---|---|
| Anchor | 4 June 2024, the election-results day: a major shock day, with the low of the move |
| First close above | 5 June: 1,108.65 against an anchored VWAP of 1,094.56 |
| Trend filter | The 50-day average rose every month, from 1,106 at the end of May to 1,228 at the end of September |
| Pullback | Early August 2024: closed below the line on 5 August (1,172.60 against 1,179.07) |
| Recovery | Back above on 16 August (1,187.25 against 1,178.19), with brief dips on 19 and 21 August |
| Outcome | By 30 September the close was 1,273.00, against an anchored VWAP of 1,205.63 |

Over 81 sessions the stock closed below the line only 11 times. The August dip shows the hard part: a close below the line was a warning, not the end. The rule's stop is a close more than 1 ATR below the line. The deepest close, on 14 August, was only 0.7 ATR below it, so the trade survived. A stop on the first close below would not have.

### Example 2 — Reliance Industries from 4 June 2024 (India, no edge)

Same anchor, same market, a different stock.

```series
title: Reliance Industries after the 2024 election-results day
from: 2024-05-01
to: 2024-09-30
line: india:RELIANCE.NS | Reliance
line: india:RELIANCE.NS@vol | Volume | pane2 bars
mark: 2024-06-04 | Anchor: results day
caption: Anchored at 4 June 2024, Reliance's VWAP rose to about 1,503 by 1 August, then went flat; the stock crossed it ten times and closed below it on 33 of the next 81 sessions.
```

| Date | Close | Anchored VWAP | Close vs VWAP |
|---|---|---|---|
| 4 Jun 2024 (anchor) | 1,397.28 | 1,418.21 | below |
| 3 Jul 2024 | 1,552.43 | 1,476.73 | above |
| 1 Aug 2024 | 1,515.30 | 1,503.03 | above |
| 30 Aug 2024 | 1,509.62 | 1,499.70 | above |
| 30 Sep 2024 | 1,476.57 | 1,496.24 | below |

After early July the line went flat, and the price swung back and forth across it. Each "pullback to the line" was followed by a close below it, then a close above it. 

A flat anchored VWAP is the daily-chart version of a range day: it shows that the buyers since the event have no profit to defend.

Strategy C's rules did produce a trade here. On 26 July the low came within 1% of the line and the close was back above it, with the line still rising. The buy at the next open, on 29 July, was at 1,511.95.

On 5 August the close was 1.8 ATR below the line. The exit at the next open, 1,455.15, lost about 3.8%. After that the line stopped rising, and the slope rule blocked new entries.

### Example 3 — NVIDIA from 25 May 2023 (US, a noisy start, then a trend)

NVIDIA gapped up 26% on 25 May 2023 after raising its revenue forecast far above expectations.

```series
title: NVIDIA — anchored at the guidance gap of 25 May 2023
from: 2023-05-01
to: 2023-08-31
line: us:NVDA | NVIDIA
line: us:NVDA@sma50 | 50-day average
mark: 2023-05-25 | Anchor: gap up 26%
caption: NVIDIA closed just below its own anchored VWAP on the gap day, crossed it five times in the next 11 sessions, then stayed above it from 12 June to 10 August 2023.
```

| Date | Close | Anchored VWAP | Close vs VWAP |
|---|---|---|---|
| 25 May 2023 (anchor) | 37.98 | 38.03 | below |
| 31 May 2023 | 37.83 | 38.85 | below |
| 12 Jun 2023 | 39.48 | 38.90 | above |
| 25 Jul 2023 | 45.68 | 41.85 | above |
| 11 Aug 2023 | 40.85 | 42.34 | below |
| 31 Aug 2023 | 49.35 | 43.36 | above |

The first two weeks were noisy: the line sat inside the gap day's range, and price crossed it again and again. A strict "first close below = exit" rule would have been stopped out twice before the trend began. A stop on a close more than 1 ATR below the line (about 4% of the price here) kept the trade alive. The pullback in August closed below the line on 11 August, about 0.95 ATR below it: only just inside the stop. It recovered on 14 August.

### Example 4 — an intraday VWAP pullback (illustrative)

Using the invented bars from section 1, extended by one more bar:

| Time | What happens | Decision |
|---|---|---|
| Bars 1–3 | Price rises from 100 to 103.5; VWAP rises from 101.17 to 101.79 | Price above a rising VWAP: a trend-day setup is forming |
| Bar 4 | Low 101.9, just above VWAP (101.86); close 102.4 | A pullback bar that touched the line and closed above it |
| Bar 5 | Trades above bar 4's high of 102.6 | Buy-stop at 102.65 fills |
| Stop | Below the lower of the pullback low and VWAP, minus 0.1% | Stop at about 101.75; risk 0.90 a share |

On a real trend day this pattern can repeat two or three times. On a range day the same bar 4 is followed by a fall through VWAP, and the stop is hit.

## 7. Common mistakes

- **Treating VWAP as a wall.** It is an average, not a price level that must hold. Price crosses it often, especially on range days.
- **Using both A and B on the same day.** They assume opposite kinds of day. Decide which day it is first.
- **Trading VWAP in the first minutes.** At the open, VWAP is just the first few trades. It means little until volume builds.
- **Anchoring to any date.** If the anchor was not an event that other traders care about, the line is noise.
- **Using index VWAP from a charting tool that shows no real volume.** A cash index has no traded volume; use the future.
- **Ignoring costs.** VWAP trades target small moves. A round-trip cost of 0.1% can be a third of the expected gain.
- **Exiting a swing trade on a single close below the anchored VWAP.** In all three daily examples above, a one-day break was followed by recovery at least once.

## 8. What the evidence says

### Published work

- **VWAP as a benchmark** is well established. Berkowitz, Logue and Noser (1988) introduced it for measuring trading costs, and VWAP execution is now standard practice among institutions.
- **VWAP as a trading signal** has little peer-reviewed evidence. Most of what is written comes from practitioners. Brian Shannon's books explain the anchored-VWAP method and its reasoning; they do not report systematic tests.
- **Day traders' results**: complete trading records from Taiwan and Brazil show most day traders lose money after costs. SEBI's 2024 study found that about 7 in 10 individual intraday traders in India's cash segment made a net loss in 2022–23. See [intraday momentum](learn-strat-intraday-momentum.md) for details.

### Event study: does holding the anchored VWAP after a gap mean anything?

**Method.** Events: a stock opened at least 5% above the previous close on at least twice its 50-day average volume. It also had to pass these filters:

| Filter | US | India |
|---|---|---|
| Prior 20-day average turnover | at least $20 million | at least ₹20 crore |
| Price | at least $10 | at least ₹100 |

Events are from January 2015 to June 2025, at most one per stock in any 60 sessions. The anchored VWAP starts on the gap day and uses daily typical prices and volumes. Each event was classified by how often it closed below its anchored VWAP in the 20 sessions after the gap. The return was then measured from session 20 to session 60, so the classification uses no future information.

| | US | India |
|---|---|---|
| Events (stocks) | 7,953 (2,026) | 919 (503) |
| Closed below the anchored VWAP at least once in 20 sessions | 93.4% | 95.4% |
| Never closed below it: events | 521 | 42 |
| Never closed below it: median return, session 20 to 60 | +2.1% | +4.5% |
| Closed below it at least once: median return, session 20 to 60 | +0.9% | +0.3% |
| All events: median return, session 20 to 60 | +1.0% | +0.4% |

A looser split — at most 4 closes below the line in the 20 sessions, against 5 or more — gives the same picture with larger groups:

| | US | India |
|---|---|---|
| At most 4 closes below: events | 2,118 | 204 |
| At most 4 closes below: median return, session 20 to 60 | +2.0% | +0.8% |
| 5 or more closes below: median return, session 20 to 60 | +0.6% | +0.3% |

**What it shows.** Almost every gap-up closes below its anchored VWAP at least once within a month, so "exit on the first close below" would exit nearly every trade.
Stocks that mostly stayed above the line did somewhat better over the next two months, more clearly in the US than in India. The differences are modest, and the Indian groups are small.

**Caveats.** Today's stock lists only, so failed companies are missing. Daily bars approximate the true VWAP. Events cluster in years like 2020 and 2024. Returns are before costs and are not a strategy test.

There is no strong published evidence that VWAP pullbacks or VWAP reversion earn money after costs. The reason to learn them is that VWAP shows where most volume traded, which is useful context for any intraday or swing decision.

## 9. Building and testing it yourself

### Data

- **Intraday strategies (A and B)**: 1-minute or 5-minute bars with volume. Compute VWAP yourself from the session open, and check it against your charting platform.
- **Anchored VWAP (C)**: daily bars with volume are enough for an approximation. For accuracy near the line, intraday data is better.

### Look-ahead traps

- VWAP at a bar must include only bars up to that one. A full-day VWAP used inside the day is a common, fatal bug.
- The VWAP bands' standard deviation must also be computed only from bars so far.
- A "range day" or "trend day" label must use information up to the decision time, not the day's close.
- Anchors must be chosen by a rule known at the time, not picked afterwards because the line "worked".
- Survivorship: test on the stocks that existed and were liquid on each date, including those delisted later.

### Costs and slippage

Approximate charges for an intraday round trip in the Indian cash market, before slippage:

| Cost | Rough size |
|---|---|
| Brokerage (discount broker) | ₹20 per order or 0.03%, whichever is lower |
| STT | 0.025% on the sell side |
| Exchange transaction charges | about 0.003% each side |
| Stamp duty | 0.003% on the buy side |
| GST | 18% on brokerage and exchange charges |

On a ₹1 lakh position that is roughly ₹80, or 0.08%. Add slippage of 0.02–0.10% each side. Delivery trades (Strategy C, held overnight) pay STT on both sides at 0.1%, so a round trip costs more, but the expected move is also larger.

### What to test, and how

- Test each strategy separately, then on trend days and range days separately, to see where its profit comes from.
- Vary one parameter at a time; prefer settings where results change slowly.
- Hold back the most recent two or three years, and test the final rules on them once.
- Report trades, win rate, average win and loss in R, expectancy after costs, maximum drawdown, and results by year and by market. See [backtesting](learn-test-backtesting.md).

### Core logic

```
# session VWAP, updated bar by bar (no look-ahead)
cum_pv = cum_v = 0
for bar in today's bars:
    tp = (bar.high + bar.low + bar.close) / 3
    cum_pv += tp * bar.volume;  cum_v += bar.volume
    vwap = cum_pv / cum_v
    # Strategy A, long side
    if minutes_since_open >= WAIT and above_vwap_for(ABOVE_MIN) and vwap > vwap_minutes_ago(SLOPE_LB) \
       and day_high_so_far - vwap >= MOVE_ATR * atr14_yesterday \
       and bar.low <= vwap * (1 + TOUCH) and bar.close > vwap:
        place buy-stop at bar.high + tick, valid for TRIGGER_BARS bars
        stop = min(bar.low, vwap) * (1 - BUFFER)

# anchored VWAP on daily bars
avwap[t] = sum(tp[a..t] * vol[a..t]) / sum(vol[a..t])   for anchor day a
```

## 10. Checklist

- [ ] Which strategy am I using today: pullback, reversion or anchored?
- [ ] Is today a trend day or a range day, judged only on what has happened so far?
- [ ] Is VWAP sloping (for a pullback) or flat (for reversion)?
- [ ] Has enough of the session passed for VWAP to mean something?
- [ ] For an anchored VWAP, is the anchor a real event others would agree on?
- [ ] Is the stop set beyond VWAP with a buffer, and is the size calculated from it?
- [ ] Is the exit time set, before the broker's square-off?
- [ ] Do the expected gains clearly exceed the round-trip costs?

## Further reading

- Stephen A. Berkowitz, Dennis E. Logue and Eugene A. Noser, "The Total Cost of Transactions on the NYSE", *Journal of Finance* (1988).
- Brian Shannon, *Maximum Trading Gains with Anchored VWAP* (2023).
- Brian Shannon, *Technical Analysis Using Multiple Timeframes* (2008).
- James F. Dalton, Eric T. Jones and Robert B. Dahlquist, *Mind Over Markets* (1990; updated edition 2013).
- SEBI, study of profit and loss of individual intraday traders in the equity cash segment (July 2024).
