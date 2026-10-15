# Journaling and review — what to record, and how to find what actually works

**In short**

- Memory edits your trades: you remember the big winner and forget the twelve small stop-outs. A written record, made before you know the outcome, is the fix.
- Record each trade's plan before the order, every change during it, and the result after it — including MAE and MFE, how far the trade went against you and for you.
- Review weekly without changing anything, and monthly by splitting results: by setup, market regime, holding period, entry quality and exit reason.
- Most splits are noise. Eight setups with the same true edge can look like winners and losers on 50 trades each, so write the sample size beside every number.
- Grade each trade twice: did you follow the plan, and did it make money. Rule breaks are the fastest thing a journal finds.

This is the second of three process guides, after [a trading plan and routine](learn-process-plan.md) and before
[biases](learn-process-biases.md). The review in §6 is run on illustrative trades from two textbook rules,
standing in for a real journal.

---

## 1. Why journal

Think back over your last twenty trades. Which do you remember? Probably the big winner, and the loss that hurt.
The twelve small stop-outs between them have faded.

**Memory is unreliable, and in predictable ways.** Once you know how a trade ended, you recall your reasons as
better than they were. Wins feel like skill and losses like luck. The [biases guide](learn-process-biases.md)
covers why. The remedy for all of them is one habit: **write it down before you know the outcome**.

**A journal is the only way to measure your own edge.** A tested rule tells you what the *rules* earn. You trade
the rules plus missed entries, early exits, skipped signals and the trade taken out of boredom. The gap between the
two is your execution cost, and only a record of your own trades shows it.

A journal also turns moods into numbers. "Breakouts aren't working" becomes "my last 30 breakouts averaged −0.2R".
It might add: "most of the losses were entries more than 5% above the pivot".

## 2. What to record on every trade

The *before* fields are written before the order is placed. That is what keeps them honest.

| When | Field | Why |
|---|---|---|
| **Before** | Date, symbol, setup (e.g. falling wedge breakout, cup without handle) | The review is done *by setup* (§6.1) |
| | Entry, stop, target or exit rule; risk per share, R in money, shares, position % | Fixes what 1R is; checks the [sizing](learn-risk-sizing.md) |
| | Market regime: index against its 50-day and 200-day, breadth, VIX | Split by regime (§6.2); [the trend guide](learn-health-trend.md) |
| | Sector and group strength | Did leadership help? [Sectors and groups](learn-sectors-groups.md) |
| | Next earnings date | A gap risk of its own ([calendar guide](learn-macro-calendar.md)) |
| | Reason, and what would prove you wrong | The thesis you grade later |
| | Entry quality: distance from the pivot and the 50-day, base count | "Did I chase?" (§6.4) |
| | Chart picture | What you saw, not what you remember |
| **During** | Every change — stop moved, partial sale, add — with date and reason | Plan versus improvisation |
| **After** | Exit date, price and reason | Review by exit reason (§6.5) |
| | R net of costs; days held | The unit of every review ([expectancy](learn-risk-expectancy.md)) |
| | MAE and MFE in R | Tests stop and exit placement (§6.6) |
| | Followed the plan? Mistakes by category (§8); one word for the emotion | Process grade, apart from the result |

### MAE and MFE

An example. You buy at ₹500 with a stop at ₹470. Your risk, 1R, is ₹30 a share.

- The lowest low while you held it is ₹482. That is (482 − 500) ÷ 30 = **−0.6R**.
- The highest high is ₹590. That is **+3.0R**.
- You sold at ₹545, which is **+1.5R** — half the best move.

The −0.6R is the trade's **MAE — maximum adverse excursion**: the worst point it reached against you while you
held it. The +3.0R is its **MFE — maximum favourable excursion**: the best point in your favour. Both are measured
from the entry, in R.

MAE tests the stop: do winners dip close to it? MFE tests the exit: do losers first go up +1R? The daily lows and
highs on any chart are all you need.

## 3. A template

Write the top half before the order. Fill in the bottom half when the trade closes.

```
## Before — 2026-10-15
- Setup: falling wedge breakout     Market: India
- Entry 812   Stop 768   Target 930   (1R = 44 / share)
- Shares 113   Risk ₹4,972 = 1.0% of account   Position 9.2%
- Regime: Nifty above rising 50 & 200-day; 61% of stocks above 50-day
- Group: leading     Earnings: 2026-11-06 (22 days)
- Reason: falling wedge breakout on 2× volume; wrong if back inside the wedge
- Entry quality: 1.8% above pivot, 6% above 50-day, first base
## During
- (date): stop raised to … — reason:
## After
- Exit date / price / reason:        R (net):      Days held:
- MAE:      MFE:      Followed plan?      Mistakes:      Emotion:
```

## 4. Where to keep it

Any tool works if it keeps three things together: the plan written before the trade, the numbers after it, and a
way to sort and count.

**A spreadsheet** is the practical core. Use one row per trade and the columns of §2. The review in §5 is then a
few pivot tables (summary tables grouped by a column).

**A notes app or notebook** holds the words: the reason, the chart picture, the lesson. Link each note to its row,
for example by date and symbol.

**Tags** make the review a few clicks. A simple scheme:

| Tags | Use |
|---|---|
| `open`, `closed` | Status, changed at the exit |
| `fwdg`, `cupnh`, `vcp` … | The setup, one per trade |
| `win`, `loss`, `scratch` | Result |
| `err-chase`, `err-early-exit`, `err-stop-moved`, `err-size`, `err-no-plan` | One per mistake (§8) |
| `regime-up`, `regime-mixed`, `regime-down` | Market at entry |

Your broker's statement is the check on the record. Reconcile the two each week: every fill in the statement
should have a row, and every row a fill.

## 5. The weekly and monthly review

**Weekly (30 minutes):** close out the week's trades — R, MAE, MFE, exit reason, tags. Read each plan against what
happened, and count rule breaks. Change no rule.

**Monthly (an hour or two):** recompute expectancy — average R, win rate, average win and loss — over all closed
trades. Then split it:

| Split | Question | Trap |
|---|---|---|
| Setup | Which patterns pay? | Small groups (§6.1) |
| Regime at entry | Stand aside when the index is weak? | Few trades in bad regimes (§6.2) |
| Holding period | What does a winner look like? | An outcome, not a choice (§6.3) |
| Entry quality | Does chasing cost me? | Noise posing as a pattern (§6.4) |
| Exit reason, month | Where does the money come from? | §6.5 |
| Plan followed or broken | What do my mistakes cost? | The most useful split of all (§8) |

Write the sample size beside every number. A group of under 20 trades says almost nothing
([expectancy](learn-risk-expectancy.md) §5).

## 6. What such a review finds — illustrative trades as a stand-in journal

To show what the splits look like, we ran two textbook rules on stored daily prices, 2013–2026. They are
illustrations of the review, not strategies to trade:

- **55-day breakout** (a trend-following rule): buy at the next open after a close above the prior 55-day high.
  The stop is two ATRs below the entry. Exit at the next open after a close below the prior 20-day low.
- **20-day breakout with a 2R target**: buy after a close above the prior 20-day high, with the close above the
  50-day average and the 50-day above the 200-day. Same stop. Sell at +2R, or after 20 sessions.

Each rule holds at most ten positions at once in liquid US or Indian stocks. Results are in R, before costs.

| Rule (market) | Trades | Losing trades | Expectancy |
|---|---|---|---|
| 55-day breakout (US) | 1,055 | 69% | +0.14R |
| 55-day breakout (India) | 966 | 72% | +0.16R |
| 20-day breakout, 2R target (US) | 2,722 | 55% | +0.09R |
| 20-day breakout, 2R target (India) | 2,597 | 59% | +0.04R |

### 6.1 By setup

Suppose your journal holds eight setups, A to H. Here is the catch: we made them all identical. Each setup's trades
were drawn at random from the same pool, the 55-day breakout's US trades. Every setup's true expectancy is
therefore +0.14R.

The standard error below is the typical amount by which an expectancy could be off through chance alone:

| Setup | Trades | Win % | Expectancy | Std error | First half | Second half |
|---|---|---|---|---|---|---|
| A | 200 | 36.0% | +0.32R | 0.18 | +0.53 | +0.12 |
| B | 107 | 27.1% | −0.06R | 0.23 | −0.55 | +0.41 |
| C | 52 | 26.9% | −0.07R | 0.26 | +0.10 | −0.24 |
| D | 48 | 29.2% | +0.20R | 0.33 | +0.32 | +0.08 |
| E | 34 | 32.4% | +0.09R | 0.36 | +0.06 | +0.12 |
| F | 27 | 29.6% | −0.19R | 0.29 | −0.06 | −0.31 |
| G | 27 | 33.3% | +0.24R | 0.36 | +0.77 | −0.25 |
| H | 13 | 23.1% | +0.52R | 1.03 | −0.52 | +1.42 |

Read as a journal, this says "drop F, it lost in both halves" and "H is my best setup". Both are pure chance.

We repeated the draw 5,000 times. Typically, the best and worst of the eight setups differed by about 1.1R a
trade. Three of the eight showed a loss, though none truly had one. A setup's rank in the first half had no
relation to its rank in the second half.

**The standard errors are larger than the gaps between setups.** A setup that loses in your journal is a reason
to *watch* it and test a change on more data. It is not a reason to drop it on 50 trades.

### 6.2 By market regime

Split each rule's trades by whether the index (S&P 500, Nifty 50) closed above its 200-day average on the entry
date:

| Rule (market) | Index above 200-day: trades, expectancy | Below: trades, expectancy |
|---|---|---|
| 55-day breakout (US) | 808, **+0.17R** | 247, +0.05R |
| 55-day breakout (India) | 629, **+0.30R** | 337, **−0.10R** |
| 20-day breakout (US) | 2,270, +0.10R | 452, +0.00R |
| 20-day breakout (India) | 1,998, +0.05R | 599, −0.03R |

All four did worse with the index below its 200-day. The standard errors are 0.03–0.13R, so the gap is clear in
India's 55-day rule and modest elsewhere. This is the kind of split that can justify a rule such as "half size
below the 200-day" ([regime filters](learn-strat-regime-filters.md)). Test it before adopting it.

### 6.3 By holding period

| Days held (calendar) | 55-day breakout (US): trades, expectancy | 55-day breakout (India): trades, expectancy |
|---|---|---|
| 10 or fewer | 325, −1.09R | 301, −1.03R |
| 11–30 | 224, −1.04R | 218, −1.01R |
| 31–90 | 332, +0.23R | 294, +0.18R |
| Over 90 | 174, **+3.80R** | 153, **+4.12R** |

Nearly every trade closed within 30 days lost. But "hold longer" is the wrong lesson. **Holding period is an
outcome, not a decision.** The stop ends losers early, and the trend lets winners run.

The table shows what a normal trade looks like. So a journal full of winners sold after 12 days says the exits
are too quick.

### 6.4 By entry quality

Two measures, each cut into thirds. The first is stop width: entry to stop, as a % of the entry. The second is how
far the price was above its 50-day average at entry ("extended"):

| Rule (market) | Tight-stop third | Wide-stop third | Least extended third | Most extended third |
|---|---|---|---|---|
| 55-day breakout (US) | +0.18R (1.6–4.1%) | +0.03R (6.5% and wider) | +0.40R | +0.06R |
| 55-day breakout (India) | +0.10R (1.9–5.8%) | +0.14R (8.0–17.7%) | +0.17R | +0.15R |
| 20-day breakout (US) | +0.16R (1.1–3.6%) | +0.03R (5.6% and wider) | +0.16R | +0.04R |
| 20-day breakout (India) | +0.07R (1.1–5.4%) | +0.01R (7.4–17.0%) | +0.09R | −0.01R |

Standard errors are 0.04–0.19R. Tight stops and less extended entries did better in three of the four runs. In
the 20-day runs the gaps are two or three standard errors wide. India's 55-day rule shows no such pattern.

So this is a lead, not a rule. Trust a split only if it moves steadily in one direction, makes sense, and holds in
both halves of the record. **Most entry-quality splits are noise**, and a personal journal has far fewer trades
than these.

### 6.5 By exit reason, and by month

The 55-day breakout in the US, by how each trade ended:

- 494 stop-outs at the stop price cost −494R (−1.0R each);
- 95 stops that gapped cost −142R (−1.5R each);
- 466 trend exits (a close below the 20-day low) made +784R (+1.7R each).

The best 53 trades — 5% of the total — made +435R. That is nearly three times the whole run's +148R. In India the
best 48 trades made +427R, against a total of +155R. **The edge lives in a handful of exits.** Anything that cuts
those winners short erases it ([stops and exits](learn-risk-stops-exits.md)).

By month, the share of calendar months whose closed trades added up to a loss:

| Rule (market) | Months | Losing months |
|---|---|---|
| 55-day breakout (US) | 160 | 49% |
| 55-day breakout (India) | 156 | 54% |
| 20-day breakout (US) | 166 | 40% |
| 20-day breakout (India) | 166 | 47% |

By year of entry, the US 55-day rule's worst year was 2022, at −0.49R a trade. Its best was 2013, at +0.83R. **Four to five
months in ten lose, even in rules with a positive expectancy.** Judge a method month by month and you will abandon
every method.

### 6.6 MAE and MFE

Computed from stored daily prices for every trade (method below):

| Rule (market) | Winners: median MAE | Winners that first fell −0.5R or more | Losers that first reached +1R | Winners: median MFE → realised |
|---|---|---|---|---|
| 55-day breakout (US) | −0.36R | 39% | 28% | +3.96R → +1.61R |
| 55-day breakout (India) | −0.42R | 42% | 28% | +4.26R → +1.67R |
| 20-day breakout (US) | −0.32R | 34% | 16% | +1.83R → +1.51R |
| 20-day breakout (India) | −0.36R | 36% | 15% | +2.00R → +1.88R |

**Winners dip.** More than a third went half-way to the stop first, so a much tighter stop would have cut them.
**More than a quarter of the trend rule's losers were up +1R first.** That is the case people make for a breakeven stop,
tested in §9. **The trend exit kept about 40% of the winners' peak profit.** That is the price of catching the
rare, very large winners.

```series
title: Alpha Pro Tech (APT), 2020 — a +15R open profit that ended at −1R
from: 2020-01-15
to: 2020-04-30
tf: D
line: us:APT | APT | log
mark: 2020-02-26 | 55-day breakout entry $10.81, stop $8.76
mark: 2020-02-28 | High $41.59: MFE +15.0R
mark: 2020-03-10 | Low $8.33: stopped at $8.76, −1.0R
caption: The mask maker's shares quadrupled in three days early in the pandemic, then fell back. The rule's exit waited for a close below the 20-day low, which was far below, and its stop never moved up. So the trade went from +15R at the high to −1R within two weeks.
```

**Method.** MAE is the lowest daily low from the day *after* entry to the day *before* exit, or the exit price if
that is lower. MFE is the same with highs. Both are divided by the initial risk (entry − initial stop). The
entry-day and exit-day highs and lows are left out, because a daily bar cannot say whether they came before or
after the fill. That is why the 20-day rule's winners show a median MFE close to the 2R target.

## 7. Your live R against what you expected

After 20 live trades you will want to know whether you are trading the method or something worse. A bootstrap
shows how widely an honest average moves by chance. It takes 20,000 random samples of N trades from a rule's
trades (the same trade can be drawn more than once). Each cell gives the 10th to 90th percentile of the average,
and the chance it is below zero:

| Rule (true expectancy) | 20 trades | 50 trades | 100 trades |
|---|---|---|---|
| 55-day breakout, US (+0.14R) | −0.49 to +0.82; 46% | −0.28 to +0.60; 39% | −0.17 to +0.49; 32% |
| 55-day breakout, India (+0.16R) | −0.49 to +0.93; 46% | −0.28 to +0.66; 36% | −0.16 to +0.52; 29% |
| 20-day breakout, US (+0.09R) | −0.28 to +0.46; 39% | −0.14 to +0.32; 32% | −0.08 to +0.26; 25% |

**A method truly earning +0.14R a trade shows a loss after twenty trades almost half the time.** A negative live
average over 20–50 trades proves nothing by itself. An average below the 10th percentile for your trade count is
worth investigating now.

Faster evidence comes from **rule breaks**. Compare the plan with the actual fill on every trade, and they show up
from the first trade. See [expectancy](learn-risk-expectancy.md) §5 for how many trades a verdict needs.

## 8. Error categories — process versus outcome

Grade each trade twice: **did I follow the plan**, and **did it make money**.

| | Made money | Lost money |
|---|---|---|
| **Followed the plan** | Good trade, good result | **Good trade, bad result** — the cost of business; change nothing |
| **Broke the plan** | **Bad trade, good result** — the dangerous one: it teaches the wrong lesson | Bad trade, bad result — fix the process |

In the illustrative rules, 55–72% of trades lose, and every one was executed exactly to plan. A losing trade is
not an error. Errors are failures of process:

| Category | Examples | Shows up as |
|---|---|---|
| Selection | Outside your setups; bad regime ignored; earnings in two days | Lower win rate |
| Entry | Chased above the pivot; bought before the trigger | Smaller R on winners |
| Sizing | 3% risk "because it looked great"; cap ignored | Drawdowns out of proportion |
| Management | Stop moved wider; added to a loser | Average loss worse than −1R |
| Exit | Winner sold early; exit signal ignored | The biggest winners cut short |
| Admin | No plan written; R not recorded | Nothing to review |

Two numbers a month summarise discipline: **the share of trades that followed the plan**, and **the total R of
those that did not**. The second is usually negative, and often larger than any difference between setups in §6.

## 9. From finding to rule change — one at a time

1. **Write the finding with its sample size**: "28% of my breakout losers first reached +1R (729 losers)."
2. **State the change exactly**: "once the high reaches entry + 1R, raise the stop to entry from the next day."
3. **Test it on the whole record and on each half separately.**
4. **Change one rule at a time** and log it with a date and a version number, so later results can be read
   against it.
5. **Re-review after enough trades** (§7), not after one bad week.

That breakeven idea was tested trade by trade on the stored daily bars. The stop moves to the entry price the day
after the high first reaches +1R. If a later low touches it, the trade exits at the entry price, or at the open if
the price gapped below. Otherwise the original result stands:

| Rule (market) | Trades changed | Expectancy before → after | 2013–19 | 2020–26 |
|---|---|---|---|---|
| 55-day breakout (US) | 281 of 1,055 | +0.14R → **+0.07R** | +0.24 → +0.21 | +0.06 → −0.05 |
| 55-day breakout (India) | 277 of 966 | +0.16R → **+0.07R** | +0.21 → +0.17 | +0.12 → −0.03 |
| 20-day breakout (US) | 415 of 2,722 | +0.09R → +0.09R | +0.15 → +0.15 | +0.03 → +0.03 |
| 20-day breakout (India) | 408 of 2,597 | +0.04R → +0.03R | +0.03 → +0.03 | +0.04 → +0.02 |

For the trend rule it **halved the edge, in both halves of both markets**. The winners it closed at breakeven on a
normal dip (§6.6) outnumbered the losers it rescued. For the target rule it changed hundreds of trades and almost
nothing in total.

The test ignores the capital such an exit frees for the next trade ([stops and exits](learn-risk-stops-exits.md)
§8). Still, a rule that feels like free insurance tested as a cost or as nothing. That is why a change is tested
before it is traded.

## 10. What the evidence says

- **Robust:** process and outcome are separate. Each illustrative rule loses on 55–72% of trades and in four to
  five months out of ten while following its rules exactly.
- **Robust:** splits on small samples mislead. Eight identical setups looked like clear winners and losers on
  13–200 trades each (§6.1). A personal journal has fewer trades than that.
- **Supported here:** breakout rules earned less, or lost, with the index below its 200-day (all four runs,
  §6.2).
- **Widely held, not measured here:** that a written review improves trading. Performance coaches (Steenbarger,
  Tharp) put it at the centre. Its measurable payoff is that it exposes the gap between your plan and what you
  actually did.
- **Folklore:** that a breakeven stop is free protection (§9), or that the holding-period split says "hold longer"
  (§6.3).
- **Limits:** the stand-in journal is two textbook rules on today's listed stocks (so delisted failures are
  missing), daily bars, no costs and perfect execution. Your record adds execution errors; finding them is the
  point.

## 11. Checklist

- [ ] Weekly: every closed trade has R (net), days held, MAE, MFE, exit reason and tags
- [ ] Weekly: each plan read against what happened; rule breaks tagged `err-…`; no rule changed
- [ ] Weekly: the record reconciled with the broker's statement
- [ ] Monthly: expectancy, win rate, average win and loss — with the trade count
- [ ] Monthly: split by setup, regime, holding period, entry quality, exit reason; sample size beside each
- [ ] Average loss no worse than about −1.1R; if worse, find the stops that slipped
- [ ] Live average R against the 10th–90th percentile for your trade count (§7)
- [ ] Share of trades that followed the plan, and the total R of those that did not
- [ ] At most one rule change — written exactly, tested on the full record and both halves, dated

## Further reading

- Van K. Tharp, *Trade Your Way to Financial Freedom* — R-multiples and judging a
  system by its distribution of results.
- John Sweeney, *Maximum Adverse Excursion: Analyzing Price Fluctuations for
  Trading Management* — MAE as a tool for placing stops.
- Brett N. Steenbarger, *The Daily Trading Coach* — journaling and self-review.
- Annie Duke, *Thinking in Bets* — judging decisions apart from outcomes.
- Daniel Kahneman, *Thinking, Fast and Slow* — hindsight and the biases a written
  record guards against.
- Mark Minervini, *Think & Trade Like a Champion* — post-analysis of your own trades.
