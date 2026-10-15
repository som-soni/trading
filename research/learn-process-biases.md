# Biases — the predictable ways a trader breaks a working plan

**In short**

- A method with a positive expectancy can still produce a losing record, because the trader bends it: holding a loser past the stop, selling a winner early, chasing, sitting out after losses.
- Each bias has a well-studied cause. Loss aversion, the law of small numbers, anchoring, recency, confirmation, hindsight and sunk cost are among the best-replicated findings in behavioural research.
- We replayed each habit on illustrative trades from two textbook breakout rules. Chasing a breakout one day late gave up two-thirds or more of the edge. Capping winners at +1R gutted the trend rule.
- Ignoring stops raised average results on this sample of surviving stocks, but left single losses of −15R to −47R. You cannot know in advance which loss will be the one that never comes back.
- Every countermeasure is a rule written before the trade: the stop as a live order, size from a formula, a chase limit, and changes made only at a scheduled review.

This is the third of three process guides, after [a trading plan and routine](learn-process-plan.md) and
[journaling and review](learn-process-journal.md).

---

## 1. Why biases matter more than setups

Picture a method that loses seven trades in ten. Its profit comes from a handful of trades that run for months.
Two things about it are hard to live with. Most trades lose, which tempts you to skip trades, tinker and quit. The
profit comes from a few long holds, which tempts you to sell early.

That is what breakout and trend methods look like. In the illustrative rules below, the best tenth of trades made
more than the whole profit; the other nine-tenths, together, lost money ([expectancy](learn-risk-expectancy.md)).
Both features are what the mind handles worst.

### The data and the method

To measure what each bias costs, we need a set of trades to bend. We used two textbook rules on stored daily
prices, 2013–2026. They are illustrations, not strategies to trade:

- **55-day breakout** (a trend-following rule): buy at the next open after a close above the prior 55-day high.
  The stop is two ATRs below the entry. Exit at the next open after a close below the prior 20-day low.
- **20-day breakout with a 2R target**: buy after a close above the prior 20-day high, with the close above the
  50-day average and the 50-day above the 200-day. Same stop. Sell at +2R, or after 20 sessions.

Each rule holds at most ten positions at once in liquid US or Indian stocks:

| Rule (market) | Trades | Win % | Total R | Worst R drawdown |
|---|---|---|---|---|
| 55-day breakout (US) | 1,055 | 30.9% | +148R | −61R |
| 55-day breakout (India) | 966 | 28.0% | +155R | −87R |
| 20-day breakout (US) | 2,722 | 44.6% | +237R | −58R |
| 20-day breakout (India) | 2,597 | 41.5% | +91R | −85R |

**Method.** Every trade risks 1R, before costs. Trades are added up in the order they exited, without compounding.
The R drawdown is the deepest fall of that running total. At 1% of the account risked per trade, −20R is roughly
a 20% drawdown.

A rule that reacts to wins or losses sees only trades that have already closed. Some biases change the trade
itself: holding past a stop, selling early, buying late. Those trades are replayed on the stored daily prices from
the rule's own entry. A replay does not free or block capital for other trades.

These are **simulations on illustrative trades**, not live results. They use today's listed stocks, daily bars,
no costs and perfect execution. No randomness is involved.

## 2. Loss aversion and the disposition effect

```series
title: Netflix (NFLX), 2021–2022 — the loser that was not sold
from: 2021-09-01
to: 2022-07-29
tf: D
line: us:NFLX | Netflix (split-adjusted) | log
mark: 2021-11-18 | 20-day breakout entry $69.16, stop $65.88
mark: 2021-11-22 | Stop hit: −1R
mark: 2022-05-16 | Held 120 sessions: $18.65, −15.4R
caption: The rule sold at the stop for −1R. Held "until it comes back", it did not come back within six months. It ended about −15R — 15% of the account at 1% risk.
```

**What it is.** Kahneman and Tversky's *prospect theory* (1979) describes how people choose under risk. They judge
outcomes as gains and losses from a reference point, such as the price they paid. **Losses weigh more than equal
gains** — about twice as much, in Tversky and Kahneman's later estimate (1992). So people gamble to avoid a sure
loss, and play safe to keep a sure gain.

Shefrin and Statman (1985) named the result in trading the **disposition effect**: selling winners too early and
riding losers too long. Odean (1998) studied about 10,000 discount-brokerage accounts. Investors sold stocks at a
gain about one and a half times as readily as stocks at a loss. And the winners they sold went on to beat the
losers they kept.

In a trader it sounds like this: waiting "for a bounce" at the stop; lowering the stop "to give it room"; selling a
+1.5R winner before it "comes back".

### Holding losers past the stop — measured

Every trade that ended at its stop was replayed two ways:

- **Widen**: the stop is moved to 2R below the entry. The stock is sold when it gets back to the entry price ("get
  even"), or 60 sessions (trading days) later.
- **No stop**: the stock is held until it gets back to even, or until 120 sessions after the original stop-out.

| Rule (market) | Base: total / drawdown | Widen to 2R: total / drawdown | Widened losers ending at −2R | No stop: total / drawdown | Held losers below −3R | Worst |
|---|---|---|---|---|---|---|
| 55-day breakout (US) | +148 / −61 | +169 / −64 | 49% | +382 / −41 | 10% | −15.3R |
| 55-day breakout (India) | +155 / −87 | +234 / −64 | 44% | +311 / −75 | 11% | −46.9R |
| 20-day breakout (US) | +237 / −58 | +378 / −67 | 46% | +795 / −83 | 11% | −15.4R |
| 20-day breakout (India) | +91 / −85 | +179 / −85 | 47% | +535 / −65 | 10% | −14.9R |

- **On this sample, bending the stop "worked" on paper.** Total R rose in all four runs. 78–82% of stopped-out
  stocks were back at the entry price within 120 sessions. That is how the habit is learned.
- **Widening doubled half the losses.** Nearly half the widened trades lost 2R instead of 1R.
- **The cost is the tail** — the rare, very large losses. About a tenth of held losers ended below −3R. The worst
  ended at −15R to −47R. At 1% risk, that is 15–47% of the account from one position.
- **Capital gets stuck.** The days spent holding positions rose 1.7–2.8 times. That money cannot fund new
  setups, a cost not counted here.
- **The sample flatters it.** The stocks tested are **today's listed stocks**, so the bankruptcies and delistings
  — the losers that never come back — are missing. And 2013–2026 was mostly a rising market.

Kaminski and Lo (2014) show that stops cost return when prices mean-revert (tend to move back toward where they
were), and help when prices trend. You cannot know which kind the next loss will be.

### Cutting winners early — measured

Each trade was replayed with a profit cap. The whole position is sold on the first session whose high reaches
+1R, +2R or +3R. If the cap is never reached, the trade ends as it did.

| Rule (market) | Base total R | Cap +1R | Cap +2R | Cap +3R | Win rate: base → +1R cap |
|---|---|---|---|---|---|
| 55-day breakout (US) | +148 | +20 | +116 | +101 | 31% → 51% |
| 55-day breakout (India) | +155 | −22 | +0 | +46 | 28% → 49% |
| 20-day breakout (US) | +237 | +183 | +237 | +237 | 45% → 54% |
| 20-day breakout (India) | +91 | +91 | +91 | +91 | 42% → 50% |

- **For the trend rule it is fatal.** A +1R cap takes the US 55-day breakout from +148R to +20R. Its edge *is* the
  tail: the few trades that run very far ([stops and exits](learn-risk-stops-exits.md) §7).
- **A +1R cap makes you right about half the time.** The feeling of winning is what the bias buys.
- **Not every cap is a cost.** The 20-day rule already sells at +2R, so higher caps change nothing. A rule for
  taking profits is a strategy decision you test, not a feeling after three good days.

**Countermeasures.** Place the stop as a real order when the position opens. Write the trade plan (entry, stop,
exit rule, size) before buying. Then the review compares your exit with that plan. If your average loss is worse
than about −1.1R, your stops are slipping ([expectancy](learn-risk-expectancy.md) §9). Exit by the method's rule
(target, trend exit, climax), not by open P&L — the profit or loss showing on the position right now.

## 3. Fear after losses

**What it is.** After a run of losses, the next trade *feels* more likely to lose. This is loss aversion plus what
Tversky and Kahneman (1971) called the "law of small numbers": reading a short streak as if it carried
information. Benartzi and Thaler (1995) gave the name *myopic loss aversion* to the extra pain of losses that you
check often.

In a trader it sounds like this: "I'll sit out a few until it turns." The test here: skip the next N entries after
K losing exits in a row.

| Rule (market) | Expectancy after ≥3 losses (trades) | Expectancy, all trades | Skip 3 after 2 losses: total | Skip 5 after 3: trades skipped (their R) → total | Drawdown: base → skip 5 after 3 |
|---|---|---|---|---|---|
| 55-day breakout (US) | +0.08R (410) | +0.14R | +100 | 355 (+11R) → +137 | −61 → −48 |
| 55-day breakout (India) | +0.13R (395) | +0.16R | +121 | 312 (−48R) → +203 | −87 → −40 |
| 20-day breakout (US) | +0.08R (798) | +0.09R | +246 | 692 (+55R) → +182 | −58 → −48 |
| 20-day breakout (India) | −0.03R (837) | +0.04R | +96 | 737 (+44R) → +48 | −85 → −56 |

**A streak carried a little information, but mostly about the market.** After three losses, expectancy was
somewhat lower in all four runs. The reason is that the positions move together. A market drop stops out several
at once, and the next entries meet the same weak market.

The cure is not a feeling. "Sit out after three losses" would have sat out 29–41% of all entries. Skipping five
trades lowered total R in three runs of four. Drawdowns were shallower in all four, partly because fewer trades
means less of everything.

**Countermeasures.** Cut exposure by a *mechanical* rule, set in advance. A rule based on the market itself is the
direct answer ([regime filters](learn-strat-regime-filters.md)). So is halving size after losses, which cut
drawdowns in all four runs ([the plan guide](learn-process-plan.md) §9). After three losses, review them against
their plans. If each one followed the plan, take the next trade at the size the rules give.

## 4. Revenge trading and overtrading

**What it is.** The urge to win back a loss quickly, by trading bigger or more often. Coval and Shumway (2005)
studied professional futures traders. Those who lost in the morning took **more** risk in the afternoon. Barber
and Odean (2000) found that the households that traded most earned several percentage points a year less, after
costs, than those that traded least.

In a trader it looks like this: a bigger position "to get it back"; a trade that is on no setup list; re-buying the
stock that just stopped you out.

Only the sizing half can be simulated. The test: double the size of the next 3 entries after 2 losing exits.
(These are the rule's own trades, not impulsive ones.)

| Rule (market) | Base: total / drawdown | Revenge: total / drawdown | R per unit of risk |
|---|---|---|---|
| 55-day breakout (US) | +148 / −61 | +216 / −81 | +0.14 → +0.15 |
| 55-day breakout (India) | +155 / −87 | +263 / −136 | +0.16 → +0.20 |
| 20-day breakout (US) | +237 / −58 | +256 / −90 | +0.09 → +0.07 |
| 20-day breakout (India) | +91 / −85 | +102 / −109 | +0.04 → +0.03 |

More risk made more R. It also **deepened the worst drawdown by 28–56% in all four runs**. The real damage is
**off-plan trades**: trades with no setup, stop or size rule. No simulation contains those, but a journal can count
them.

**Countermeasures.** Size every trade from the formula, risk ÷ (entry − stop), never from the last result. Take no
trade without a written plan. Set a daily loss limit; once it is hit, place no new orders. Tag off-plan trades and
total their R each month ([journal](learn-process-journal.md) §8).

## 5. Overconfidence after a streak

**What it is.** After wins, people credit their own skill and expect more wins. Barber and Odean (2001) linked
overconfidence to trading: men traded markedly more than women, and lost more return to it. The **hot hand** is
the idea that a streak predicts the next result.

In basketball the hot hand was called a fallacy (Gilovich, Vallone and Tversky, 1985). Miller and Sanjurjo (2018)
later found a statistical flaw in that test, so for sport it is still debated. For trades it can be measured. The
test: double the size of the next 3 entries after 3 winning exits ("pressing").

| Rule (market) | Expectancy after ≥3 wins (trades) | Pressing: total / drawdown | Base: total / drawdown |
|---|---|---|---|
| 55-day breakout (US) | −0.33R (74) | +138 / −66 | +148 / −61 |
| 55-day breakout (India) | +0.16R (47) | +185 / −92 | +155 / −87 |
| 20-day breakout (US) | +0.18R (456) | +293 / −76 | +237 / −58 |
| 20-day breakout (India) | −0.01R (378) | +82 / −97 | +91 / −85 |

What followed a three-win streak swung from −0.33R to +0.18R a trade: that is **noise**. Pressing deepened the
drawdown in all four runs, and raised total R in only two.

**Countermeasures.** If your size grows with success, let a rule decide it, judged over a long run of trades. One
example: raise risk per trade only when the account makes a new high
([portfolio risk](learn-risk-portfolio.md) §8). After a streak, re-read the entry criteria.

## 6. FOMO and chasing

**What it is.** Buying because a stock is already moving. The breakout fired yesterday, today the stock is 3%
higher, and you buy anyway. You get a worse price for the same stop. So you take more risk per share and have less
room before the stop.

The replay: a buyer waits N sessions and buys at that day's close, **but only if the stock is already above the
entry price**. The buyer keeps the original stop and exit, and risks the same amount of money.

| Rule (market) | Trades chased (3 sessions late) | Their expectancy: on time → chased | Same, 1 session late |
|---|---|---|---|
| 55-day breakout (US) | 528 | +0.79R → +0.10R | +0.69R → +0.22R |
| 55-day breakout (India) | 420 | +0.99R → +0.25R | +0.58R → +0.14R |
| 20-day breakout (US) | 1,376 | +0.59R → +0.05R | +0.49R → +0.09R |
| 20-day breakout (India) | 1,104 | +0.58R → +0.06R | +0.52R → +0.10R |

The chaser buys only the trades that were already working. Even so, the chaser **gives up three-quarters or more
of the edge** three sessions late. The median move the chaser waited through was only 0.3–0.5R. Being one day late
already cost two-thirds or more.

**Countermeasures.** Use a chase limit: a maximum distance past the entry price, beyond which you do not buy. Many
published methods set one. O'Neil and Minervini both advise against buying more than 5% above the pivot
([VCP and SEPA](learn-strat-vcp-sepa.md)). Missed it? Put it on a watchlist with a note of the price you would pay,
and wait for the next setup. **A missed trade costs nothing; a chased one costs the edge.**

## 7. Anchoring

**What it is.** People make an estimate by starting from some number, even an arbitrary one, and then adjust too
little (Tversky and Kahneman, 1974). A trader has two common anchors.

One is the **buy price**. It is prospect theory's reference point, and it turns "sell at the stop" into "wait until
I'm even" (§2). The other is **old prices**: "it was $40 last month, I won't pay $46".

The simulation: instead of buying at the signal, place a limit order 0.5R below it, kept for 10 sessions. Trades
that never dip that far are missed.

| Rule (market) | Filled | Total R: base → anchored | Best-10% trades caught |
|---|---|---|---|
| 55-day breakout (US) | 63% | +148 → +59 | 29 of 106 |
| 55-day breakout (India) | 67% | +155 → +215 | 35 of 97 |
| 20-day breakout (US) | 60% | +237 → +156 | 132 of 549 |
| 20-day breakout (India) | 63% | +91 → +232 | 133 of 537 |

A cheaper fill improves each trade that fills. In India that was enough to raise total R; in the US it was not.
But in every run, **the trades that never looked back were the ones missed**: 64–76% of the best tenth. The lesson:
a pullback entry is a strategy to test, not a price to wait for.

**Countermeasures.** Judge the stock by today's setup, not by what you paid or what it once cost. In each trade
review, ask: "would I buy it here, with this stop?" If not, the position is a hope.

## 8. Recency — abandoning a method after a drawdown

**What it is.** What comes to mind easily feels likely. Tversky and Kahneman (1973) called this the availability
heuristic. During a drawdown, the drawdown feels like proof that the method "stopped working". Last year's winning
method feels like the one to switch to.

The test below: stop trading a rule when its drawdown reaches −20R, and see what it did next.

| Rule (market) | Quit when a drawdown reaches −20R | Next 2 years | Rest of the run |
|---|---|---|---|
| 55-day breakout (US) | Nov 2015 (first time) | +0R | +94R (867 trades) |
| 55-day breakout (India) | Mar 2013 (first time) | +75R | +176R |
| 20-day breakout (US) | Oct 2014 (first time) | +3R | +193R |
| 20-day breakout (India) | Dec 2014 (first time) | −32R | +65R |
| 55-day breakout (India) | May 2022 (fourth time) | +52R | −30R |

Across all four rules, a −20R drawdown came 16 times with two full years of data after it. In 11 of those the
next two years made money, and in 5 they lost. Quitting at the bottom usually sold the recovery. Sometimes it
avoided more losses. A drawdown cannot tell you which of the two you are in.

The worst 30-trade stretch of the US 20-day rule lost 27R, ending in April 2020. The next 100 trades made +43R.

**Method hopping** is the same bias over years. A rule's rank among the four in one year said nothing about its
rank the next: the year-to-year rank correlation was zero. Morningstar's yearly "Mind the Gap" studies find the
same pattern among fund investors. They tend to buy after good years, and so earn less than the funds they own.

**Countermeasures.** Decide in advance what drawdown is normal, and what means the method is broken. For normal, use
the bootstrap ranges in [position sizing](learn-risk-sizing.md) §7 — the spread of drawdowns found by resampling a
method's trades many times. Broken means a live record outside the tested range ([journal](learn-process-journal.md)
§7), not a bad quarter. Change one rule at a time, as a new version with its own test.

## 9. Confirmation bias

**What it is.** Seeking out, and giving too much weight to, evidence for what you already believe (Nickerson,
1998). Once you own a stock, you read the bullish news and explain the breakdown away. A favourite measure that has
never been tested picks the "best-looking" setups.

Here is a test. Traders like a breakout on heavy volume: it *looks* convincing. We split each rule's trades into
quarters by breakout-day volume, relative to the 50-day average:

| Rule (market) | Lightest-volume quarter | Second | Third | Heaviest-volume quarter |
|---|---|---|---|---|
| 55-day breakout (US) | +0.54R | +0.11R | −0.09R | −0.00R |
| 55-day breakout (India) | +0.16R | +0.23R | +0.09R | +0.17R |
| 20-day breakout (US) | +0.04R | +0.17R | +0.01R | +0.12R |
| 20-day breakout (India) | +0.04R | +0.03R | −0.01R | +0.08R |

The standard errors (the likely size of chance variation) are 0.05–0.25R. Results do not rise steadily from light
volume to heavy. So most of this is noise ([journal](learn-process-journal.md) §6.4). But there is no sign that
the most convincing breakouts were better. Volume may still matter inside a specific pattern; that has to be
tested, not assumed ([volume](learn-price-volume.md)).

**Countermeasures.** In the trade plan, write "what would prove me wrong" as a price, before buying. Read the bear
case: the argument that the stock will fall. Let your written rules choose the trades. Your own preference is a
hypothesis, to test over 100 trades.

## 10. Hindsight bias

**What it is.** Once the outcome is known, people believe they "knew it all along" (Fischhoff, 1975). A correct
stop-out becomes "I should have seen it". A lucky win becomes skill.

So were the best trades visible at entry? The table compares the top 10% of trades with the rest:

| Rule (market) | Stop width at entry: best 10% / rest | Best 10% that first fell −0.5R or more | Rest that did |
|---|---|---|---|
| 55-day breakout (US) | 5.2% / 5.1% | 36% | 82% |
| 55-day breakout (India) | 6.5% / 6.8% | 40% | 86% |
| 20-day breakout (US) | 4.4% / 4.4% | 20% | 82% |
| 20-day breakout (India) | 6.3% / 6.3% | 23% | 84% |

At entry they looked the same. And a fifth to two-fifths of the best trades first fell half-way to the stop. The
best US trade, Sprouts Farmers Market from 2023 to 2024, made +50R. It came from the same breakout signal as the
589 US trades that were stopped out. **The outcome is not the grade of the decision.**

**Countermeasures.** Write the reason and the plan *before* the trade. Then the review compares your decisions with
what was known at the time. Grade every trade twice: was the plan followed (yes / no), and what was the result in R
([journal](learn-process-journal.md) §8).

## 11. Sunk cost

**What it is.** Continuing because of what has already been spent (Arkes and Blumer, 1985). It sounds like "I've
lost too much to sell now". It shows up as averaging down: buying more as the price falls.

The simulation keeps the **stop in place** and buys as many shares again at 0.5R below the entry. It added on
70–82% of trades.

| Rule (market) | Worst drawdown: base → averaging down | R per unit of risk |
|---|---|---|
| 55-day breakout (US) | −61R → −82R | +0.14 → +0.19 |
| 55-day breakout (India) | −87R → −129R | +0.16 → +0.18 |
| 20-day breakout (US) | −58R → −98R | +0.09 → +0.09 |
| 20-day breakout (India) | −85R → −132R | +0.04 → +0.04 |

The worst drawdown deepened in all four runs, by a third or more. R per unit of risk rose in two runs and held in
two. Even with a stop, averaging down is simply **more risk**: −1.5R on every failure. Without the stop, it is §2's
tail, doubled.

**Countermeasures.** Set the size once, at entry. Add only to a position that is working, and only by a written
rule ([position sizing](learn-risk-sizing.md) §9). Ask §7's question: would I buy it here?

## 12. What the evidence says

- **Robust (research):** loss aversion and the disposition effect are among the best-replicated findings in
  behavioural finance (found again and again by new studies). Heavy trading costs individual investors return.
  Knowing the outcome distorts how people judge the decision.
- **Measured here, consistent across runs:** chasing cost most of the edge. Capping winners at +1R gutted the
  trend rule. Doubling size after losses, pressing after wins and averaging down all deepened every drawdown.
  Winning streaks did not predict the next trade.
- **Measured here, uncomfortable:** ignoring stops raised total R. But the sample holds only stocks still listed
  today, in mostly rising markets. And the price was single losses of −15R to −47R. Losing streaks did carry a
  little information, mostly about the market as a whole.
- **Not measured:** off-plan trades, hesitation and mood. A simulation cannot contain them; your journal can.
- **Limits:** two textbook rules, one history each, simulated behaviour, no costs, daily bars. Trust the direction
  of each result more than its size.

## 13. Checklist — the one-page bias check

**Before the trade**
- [ ] The stock came from my written setups or a watchlist built from them — not from a tip, and not just because it is moving
- [ ] Trade plan written: entry, stop, exit rule, size, what would prove me wrong
- [ ] Within the chase limit; if not, a watchlist note with the price I would pay
- [ ] Size from the formula — not bigger after a loss or a winning streak
- [ ] Taken even after recent losses, if the plan says so

**During the trade**
- [ ] The stop is a live order and has only moved up; no averaging down
- [ ] Exit by the method's rule, not open P&L
- [ ] "Would I buy it here, with this stop?" — if not, why am I holding?

**Weekly**
- [ ] A review for each closed trade: plan followed (yes / no), R, what was known at entry
- [ ] Average loss no worse than about −1.1R; off-plan trades counted, their R totalled
- [ ] No rule changed because of this week's results

## Further reading

- Kahneman and Tversky, "Prospect Theory: An Analysis of Decision under Risk",
  *Econometrica* (1979); Tversky and Kahneman, "Advances in Prospect Theory",
  *Journal of Risk and Uncertainty* (1992).
- Shefrin and Statman, "The Disposition to Sell Winners Too Early and Ride
  Losers Too Long", *Journal of Finance* (1985).
- Terrance Odean, "Are Investors Reluctant to Realize Their Losses?", *Journal
  of Finance* (1998).
- Barber and Odean, "Trading Is Hazardous to Your Wealth", *Journal of Finance*
  (2000), and "Boys Will Be Boys", *Quarterly Journal of Economics* (2001).
- Coval and Shumway, "Do Behavioral Biases Affect Prices?", *Journal of Finance* (2005).
- Kaminski and Lo, "When Do Stop-Loss Rules Stop Losses?", *Journal of
  Financial Markets* (2014).
- Tversky and Kahneman, "Judgment under Uncertainty: Heuristics and Biases",
  *Science* (1974); Fischhoff, "Hindsight ≠ Foresight" (1975); Arkes and
  Blumer, "The Psychology of Sunk Cost" (1985).
- Morningstar, "Mind the Gap" (annual) — investor returns against the returns of the funds they hold.
- Daniel Kahneman, *Thinking, Fast and Slow*; Mark Douglas, *Trading in the Zone*.
