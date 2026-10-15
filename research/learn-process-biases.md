# Biases — the predictable ways a trader breaks a working plan

This guide is about the mental habits that turn a method that makes money on
average (a positive expectancy) into a losing record. It covers loss aversion,
fear after losses, revenge trading, overconfidence, chasing, anchoring,
recency, confirmation, hindsight and sunk cost. For each one it gives what the
research found, how it shows up in a trader, **what it would have cost on this
app's own backtest trades**, and a countermeasure. It is the third of three
process guides, after [A trading plan and routine](learn-process-plan.md) and
[Journaling and review](learn-process-journal.md).

**Where this shows in the app.** The app does not place orders or track your
positions, so the discipline is up to you. Its tools for it are written ones:

- **Library → Notes** has note templates: *Trade plan* (with a "What would
  prove me wrong" field), *Trade review*, and *Daily journal* (with a
  "Lessons" field).
- **Watchlists** hold a note per stock. For companies you track under
  Screens → Quality, you can also set a buy-below price.
- The decision tags on **Strategies** say what to do with a setup: *TRADE ON
  TRIGGER*, or *WATCH — WAIT* when a setup is extended (the price has already
  run too far past its entry).
- Each strategy's **Backtests** tab groups its runs by rule version.

---

## 1. Why biases matter more than setups

The [expectancy guide](learn-risk-expectancy.md) showed that in every strategy
here the **median trade loses**, and the **best tenth of trades makes more than
all the profit** (the other nine-tenths, together, lose money). Both are what
the mind handles worst. A method that loses 70% of the time tempts you to skip
trades, tinker with the rules and quit. A method whose profit comes from a few
long holds tempts you to sell early.

### The data and the method

Each bias is **simulated on the stored trade lists** of five backtests. For
each strategy that is its latest full-history run under its current rules,
counting closed trades only. (For US Minervini it is the v1.6 run with the
market filter — the rules that became v1.7.)

| Run | Period | Trades | Win % | Total R | Worst R drawdown |
|---|---|---|---|---|---|
| Donchian channel, US | 2013–2026 | 496 | 28.6% | +241R | −86R |
| Donchian channel, India | 2013–2026 | 437 | 27.2% | +183R | −41R |
| Volume breakout, US | 2013–2026 | 703 | 34.3% | +30R | −40R |
| Chart patterns, India | 2013–2026 | 515 | 32.0% | +73R | −38R |
| Minervini SEPA, US | 2010–2026 | 482 | 28.2% | +27R | −27R |

**Method.** Every trade risks 1R, and results are net of modelled trading
costs. Trades are added up in the order they exited, without compounding. The
R drawdown is the deepest fall of that running total. (At 1% of the account
risked per trade, −20R is roughly a 20% drawdown.) A rule that reacts to wins
or losses sees only trades that have already closed. Some biases change what
happens to the trade itself: holding past a stop, selling early, buying late.
Those trades are replayed on the stored daily prices, starting from the
backtest's own entry. These are **simulations on backtests**, not live
results: they use today's listed stocks, daily bars, modelled costs and
perfect execution. No randomness is involved.

## 2. Loss aversion and the disposition effect

**What it is.** Kahneman and Tversky's *prospect theory* (1979) describes how
people choose under risk. They judge outcomes as gains and losses from a
reference point, such as the price they paid. And **losses weigh more than
equal gains** — about twice as much, in Tversky and Kahneman's later estimate
(1992). So people gamble to avoid a sure loss, and play safe to keep a sure
gain. Shefrin and Statman (1985) named the result in trading the **disposition
effect**: selling winners too early and riding losers too long. Odean (1998)
studied about 10,000 discount-brokerage accounts. Investors sold stocks at a
gain about one and a half times as readily as stocks at a loss. And the
winners they sold went on to beat the losers they kept. In a trader it sounds
like this: waiting "for a bounce" at the stop; lowering the stop "to give it
room"; selling a +1.5R winner before it "comes back".

### Holding losers past the stop — measured

Every trade that ended at its stop was replayed two ways.

- **Widen**: the stop is moved to 2R below entry. The stock is sold when it
  gets back to the entry price ("get even"), or 60 sessions (trading days)
  later.
- **No stop**: the stock is held until it gets back to even, or until 120
  sessions after the original stop-out.

| Run | Base: total / drawdown | Widen to 2R: total / drawdown | Widened losers ending at −2R | No stop: total / drawdown | Held losers below −3R | Worst |
|---|---|---|---|---|---|---|
| Donchian, US | +241 / −86 | +233 / −109 | 50% | +348 / −63 | 7% | −9.4R |
| Donchian, India | +183 / −41 | +190 / −43 | 44% | +264 / −60 | 8% | −8.6R |
| Volume breakout, US | +30 / −40 | +23 / −64 | 51% | +171 / −75 | 11% | −8.2R |
| Chart patterns, India | +73 / −38 | +81 / −54 | 47% | +123 / −68 | 14% | −8.5R |
| Minervini, US | +27 / −27 | +27 / −24 | 49% | +69 / −27 | 8% | −7.2R |

- **Widening the stop bought nothing.** Total R moved by less than 9R, up or
  down. Half the widened trades lost 2R instead of 1R. Drawdowns deepened in
  four runs of five. And the R earned per day of capital in use fell in all
  five.
- **Abandoning the stop "worked" on paper.** 69–80% of stopped-out stocks were
  back at the entry price within 120 sessions. That is how the habit is
  learned.
- **The cost is the tail** — the rare, very large losses. 7–14% of held losers
  ended below −3R. Held a full year, the worst ended at −8.6R to −16.6R. At 1%
  risk that is 9–17% of the account, from one position. The days spent holding
  positions rose 1.4–2.4 times. That is capital stuck in losers, which blocks
  new setups (a cost not counted here).
- **The sample flatters it.** The stocks tested are **today's listed stocks**.
  So the bankruptcies and delistings — the losers that never come back — are
  missing. And 2013–2026 was mostly a rising market. Kaminski and Lo (2014)
  show that stops cost return when prices mean-revert (tend to move back toward
  where they were), and help when prices trend. You cannot know which kind the
  next loss will be.

```series
title: IDEXX Laboratories (IDXX), 2021–2022 — the loser that was not sold
from: 2021-08-01
to: 2022-12-30
tf: D
line: us:IDXX | IDEXX (IDXX) | log
mark: 2021-09-24 | Minervini entry about $679, stop $648
mark: 2021-09-27 | Stop hit: −1R
mark: 2022-09-22 | Held a year: about $326, −11.5R
caption: The US Minervini backtest sold at the stop for −1R. Held "until it comes back", it did not come back within the year. It ended about −11.5R — 11.5% of the account at 1% risk.
```

### Cutting winners early — measured

Each trade was replayed with a profit cap. The whole position is sold on the
first session after entry whose high reaches +1R, +2R or +3R. If the cap is
never reached, the trade ends as it did in the backtest.

| Run | Base total R | Cap +1R | Cap +2R | Cap +3R | Win rate: base → +1R cap |
|---|---|---|---|---|---|
| Donchian, US | +241 | −32 | +2 | +33 | 29% → 48% |
| Donchian, India | +183 | −10 | +6 | +26 | 27% → 49% |
| Volume breakout, US | +30 | −11 | +44 | +38 | 34% → 51% |
| Chart patterns, India | +73 | +16 | +33 | +61 | 32% → 53% |
| Minervini, US | +27 | +11 | +33 | +33 | 28% → 44% |

- **For trend followers it is fatal.** A +2R cap takes US Donchian from +241R
  to +2R. Their edge *is* the tail: the few trades that run very far
  ([stops and exits](learn-risk-stops-exits.md) §7).
- **A +1R cap makes you right about half the time, and it lowers total R in
  every run.** The feeling of winning is what the bias buys.
- **Not every cap is a cost.** In the breakout and Minervini runs the average
  winner is about 2R. There, a +2R cap matched or beat the base. A rule for
  taking profits is a strategy decision you test, not a feeling after three
  good days.

**Countermeasures.** Place the stop as a real order when the position opens.
Write the *Trade plan* note (entry, stop, exit rule, size) before buying. The
*Trade review* then compares your exit with that plan. If your average loss is
worse than about −1.1R, your stops are slipping
([expectancy](learn-risk-expectancy.md) §9). Exit by the strategy's rule
(target, trend exit, climax), not by open P&L — the profit or loss showing on
the position right now.

## 3. Fear after losses

**What it is.** After a run of losses, the next trade *feels* more likely to
lose. This is loss aversion plus what Tversky and Kahneman (1971) called the
"law of small numbers": reading a short streak as if it carried information.
Benartzi and Thaler (1995) gave the name *myopic loss aversion* to the extra
pain of losses that you check often. In a trader it sounds like this: "I'll sit
out a few until it turns." (A pause after three losses is tested in
[the plan guide](learn-process-plan.md) §9.) The test here: skip the next N
entries after K losing exits in a row.

| Run | Expectancy after ≥3 losses (trades) | Expectancy, all trades | Skip 3 after 2 losses: total | Skip 5 after 3: trades skipped (their R) → total | Drawdown, skip 5 after 3 |
|---|---|---|---|---|---|
| Donchian, US | +0.77R (225) | +0.49R | +136 | 200 (+134R) → +107 | −58 |
| Donchian, India | +0.90R (197) | +0.42R | +112 | 196 (+142R) → +41 | −30 |
| Volume breakout, US | +0.02R (236) | +0.04R | +36 | 241 (+22R) → +8 | −31 |
| Chart patterns, India | +0.12R (173) | +0.14R | +37 | 207 (+69R) → +3 | −31 |
| Minervini, US | +0.08R (200) | +0.06R | −3 | 205 (+53R) → −26 | −35 |

**A streak did not predict the next trade.** After three losses, expectancy
was at most 0.02R lower than usual. In Donchian it was higher: a losing run
ends when a trend starts. At these win rates, "sit out after three losses"
sits out **35–45% of all trades**. Skipping five trades cost R in every run.
Drawdowns fell in four runs, but only because fewer trades means less of
everything.

**Countermeasures.** Cut exposure by a *mechanical* rule, set in advance. The
backtester has one, called progressive exposure (`--pe`). It halves risk after
two losses, or while the last ten trades net zero or less. It cut Minervini's
drawdown (v1.6, no market filter) from −43.5% to −34.6%, at a small cost
([position sizing](learn-risk-sizing.md) §9). After three losses, review them
against their plans. If each one followed the plan, take the next trade at
normal size.

## 4. Revenge trading and overtrading

**What it is.** The urge to win back a loss quickly, by trading bigger or more
often. Coval and Shumway (2005) studied professional futures traders. Those who
lost in the morning took **more** risk in the afternoon. Barber and Odean (2000)
found that the households that traded most earned several percentage points a
year less, after costs, than those that traded least. In a trader it looks like
this: a bigger position "to get it back"; a trade that is on no setup list;
re-buying the stock that just stopped you out.

Only the sizing half can be simulated. The test: double the size of the next 3
entries after 2 losing exits. (These are the system's own trades, not
impulsive ones.)

| Run | Base: total / drawdown | Revenge: total / drawdown | R per unit of risk |
|---|---|---|---|
| Donchian, US | +241 / −86 | +430 / −130 | +0.49 → +0.57 |
| Donchian, India | +183 / −41 | +334 / −66 | +0.42 → +0.50 |
| Volume breakout, US | +30 / −40 | +37 / −59 | +0.04 → +0.04 |
| Chart patterns, India | +73 / −38 | +118 / −58 | +0.14 → +0.16 |
| Minervini, US | +27 / −27 | +48 / −39 | +0.06 → +0.07 |

More risk made more R. It also **deepened the worst drawdown by 44–61% in all
five runs**. The real damage is **off-plan trades**: trades with no setup, stop
or size rule. No backtest contains those, but a journal can count them.

**Countermeasures.** Size every trade from the formula, risk ÷ (entry − stop),
never from the last result. Take no trade without a *Trade plan* note. Set a
daily loss limit; once it is hit, place no new orders. Tag off-plan trades
`err-…` and total their R each month ([journal](learn-process-journal.md) §8).

## 5. Overconfidence after a streak

**What it is.** After wins, people credit their own skill and expect more wins.
Barber and Odean (2001) linked overconfidence to trading: men traded markedly
more than women, and lost more return to it. The **hot hand** is the idea that
a streak predicts the next result. In basketball it was called a fallacy
(Gilovich, Vallone and Tversky, 1985). Miller and Sanjurjo (2018) later found a
statistical flaw in that test, so for sport it is still debated. For trades it
can be measured. The test: double the size of the next 3 entries after 3
winning exits ("pressing").

| Run | Expectancy after ≥3 wins (trades) | Pressing: total / drawdown | Base: total / drawdown |
|---|---|---|---|
| Donchian, US | −0.44R (19) | +262 / −94 | +241 / −86 |
| Donchian, India | +2.19R (21) | +219 / −39 | +183 / −41 |
| Volume breakout, US | −0.34R (43) | +11 / −54 | +30 / −40 |
| Chart patterns, India | −0.05R (37) | +78 / −39 | +73 / −38 |
| Minervini, US | +0.20R (15) | +32 / −31 | +27 / −27 |

Three-win streaks are rare at a 30% win rate. What followed them swung from
−0.44R to +2.19R: that is **noise**. Pressing deepened the drawdown in four
runs, and cut the breakout's total by about two-thirds.

**Countermeasures.** If your size grows with success, let a rule decide it,
judged over a long run of trades. The backtester has one (`--pe-press`): it
presses only once the last ten trades total +4R or better. It added little
([portfolio risk](learn-risk-portfolio.md) §8). After a streak, re-read the
entry criteria.

## 6. FOMO and chasing

**What it is.** Buying because a stock is already moving. You get a worse price
for the same stop, so you take more risk per share and have less room before
the stop. The breakout fired yesterday, today the stock is 3% higher, and you
buy anyway. The replay: a buyer waits N sessions and buys at that day's close,
**but only if the stock is already above the entry price**. The buyer keeps
the original stop and exit, and risks the same amount of money.

| Run | Trades chased (3 sessions late) | Their expectancy: on time → chased | Same, 1 session late |
|---|---|---|---|
| Donchian, US | 226 | +1.54R → +0.79R | +1.39R → +0.83R |
| Donchian, India | 183 | +1.39R → +0.73R | +0.99R → +0.56R |
| Volume breakout, US | 327 | +0.50R → +0.02R | +0.44R → +0.08R |
| Chart patterns, India | 251 | +0.76R → +0.13R | +0.65R → +0.18R |
| Minervini, US | 248 | +0.46R → −0.03R | +0.37R → +0.03R |

The chaser buys only the trades that were already working. Even so, the chaser
**gives up half the edge in the trend followers, and nearly all of it
elsewhere**. The median move the chaser waited through was only about
0.3–0.4R. Being one day late already costs most of the edge.

**Countermeasures.** Use a chase limit: a maximum distance past the entry
price, beyond which you do not buy. The app's strategies have one. Chart
patterns fails gate S5 when the price is more than 4% past the trigger.
Minervini SEPA skips a fill more than 5% past the pivot (flag B2). Volume
breakout flags a stock that has already run far above its 20-day average
(XB1) and will rate it no higher than *TRADE ON TRIGGER*, which means wait for
the price to trigger the entry rather than buy now. Missed it? Put it
on a watchlist with a note of the price you would pay, and wait for the next
setup. **A missed trade costs nothing; a chased one costs the edge.**

## 7. Anchoring

**What it is.** People make an estimate by starting from some number, even an
arbitrary one, and then adjust too little (Tversky and Kahneman, 1974). A
trader has two common anchors. One is the **buy price**. It is prospect
theory's reference point, and it turns "sell at the stop" into "wait until I'm
even" (§2). The other is **old prices**: "it was $40 last month, I won't pay
$46". The simulation: instead of buying at the signal, place a limit order
0.5R below it, kept for 10 sessions. Trades that never dip that far are
missed.

| Run | Filled | Total R: base → anchored | Best-10% trades caught |
|---|---|---|---|
| Donchian, US | 52% | +241 → +16 | 12 of 50 |
| Donchian, India | 58% | +183 → +146 | 13 of 44 |
| Volume breakout, US | 60% | +30 → +69 | 29 of 71 |
| Chart patterns, India | 59% | +73 → +4 | 17 of 52 |
| Minervini, US | 55% | +27 → −1 | 10 of 49 |

A cheaper fill improves each trade that fills. But **the trades that never look
back are the ones that pay**: 60–80% of the best trades were missed. The
breakout run was the exception. The lesson there: a pullback entry is a
strategy to test, not a price to wait for.

**Countermeasures.** Judge the stock by today's setup, not by what you paid or
what it once cost. In the *Trade review*, ask: "would I buy it here, with this
stop?" If not, the position is a hope.

## 8. Recency — abandoning a method after a drawdown

**What it is.** What comes to mind easily feels likely. Tversky and Kahneman
(1973) called this the availability heuristic. During a drawdown, the drawdown
feels like proof that the method "stopped working". Last year's winning
strategy feels like the one to switch to. The test below: stop trading a
strategy when its drawdown reaches −20R, and see what it did next.

| Run | Quit when a drawdown reaches −20R | Next 2 years | Rest of the run |
|---|---|---|---|
| Donchian, US | Aug 2015 | +118R | +199R (407 trades) |
| Chart patterns, India | Jun 2019 | +27R | +63R |
| Volume breakout, US | May 2016 | +3R | +28R |
| Minervini, US | Jan 2017 | +2R | +11R |
| Donchian, India | Apr 2013 (first time) | +88R | +182R |
| Donchian, India | Apr 2025 (fourth time) | −26R (to date) | −26R |

Quitting at the bottom usually sold the recovery. Once (India Donchian, 2025)
it avoided more losses. A drawdown cannot tell you which of the two you are
in. US Donchian's worst 30-trade stretch (−32R, ending in October 2022) was
followed by +77R in the next 100 trades.

**Strategy hopping** was tested across seven runs (these five, plus Trend
pullback US and India), 2014–2025. The rule: each year, trade only the run that
had the best R the year before. The total was **−14R**, against **+68R** for
the average of all seven. A run's rank one year said nothing about its rank
the next: the year-to-year rank correlation was zero.

**Countermeasures.** Decide in advance what drawdown is normal, and what means
the method is broken. For normal, use the bootstrap ranges in
[position sizing](learn-risk-sizing.md) §7 — the spread of drawdowns found by
resampling the backtest's trades many times. Broken means a live record
outside the backtest's range ([journal](learn-process-journal.md) §7), not a
bad quarter. Change one rule at a time, as a new version with its own
backtest. The **Backtests** tab shows when runs no longer reflect the current
rules.

## 9. Confirmation bias

**What it is.** Seeking out, and giving too much weight to, evidence for what
you already believe (Nickerson, 1998). Once you own a stock, you read the
bullish news and explain the breakdown away. A favourite measure that has never
been tested picks the "best-looking" setups. Here is a test. In US Minervini,
the trades in the highest quarter of relative strength (RS) rank at entry
(86–98) made −0.02R a trade. The lowest quarter (70–74) made +0.38R. In India,
textbook cup-with-handle patterns made +0.10R a trade, against +0.14R for the
whole run. The standard errors (the likely size of chance variation) are
0.12–0.16R, and results do not rise or fall steadily from low rank to high. So
this is mostly noise ([journal](learn-process-journal.md) §6.4). But there is
no sign that the most convincing trades were better.

**Countermeasures.** On the *Trade plan*, fill in "What would prove me wrong"
as a price, before buying. Read the bear case: the argument that the stock
will fall. Let the screen and strategy choose the trades. Your own preference
is a hypothesis, to test over 100 trades.

## 10. Hindsight bias

**What it is.** Once the outcome is known, people believe they "knew it all
along" (Fischhoff, 1975). A correct stop-out becomes "I should have seen it". A
lucky win becomes skill. So were the best trades visible at entry? The table
compares the top 10% of trades with the rest:

| Run | Stop width at entry: best 10% / rest | Best 10% that first fell −0.5R or more | Rest that did |
|---|---|---|---|
| Donchian, US | 7.1% / 7.5% | 44% | 82% |
| Donchian, India | 9.0% / 8.8% | 41% | 86% |
| Volume breakout, US | 5.1% / 4.7% | 49% | 83% |
| Chart patterns, India | 6.1% / 6.3% | 40% | 84% |
| Minervini, US | 5.2% / 5.5% | 20% | 74% |

At entry they looked the same. And up to half of the best trades first fell
half-way to the stop. The +53R NVIDIA trade in US Donchian was the same channel
breakout signal as the 288 trades that were stopped out. **The outcome is not
the grade of the decision.**

**Countermeasures.** Write the reason and the plan *before* the trade. Then the
review compares your decisions with what was known at the time. Grade every
trade twice: was the plan followed (yes / no), and what was the result in R
([journal](learn-process-journal.md) §8).

## 11. Sunk cost

**What it is.** Continuing because of what has already been spent (Arkes and
Blumer, 1985). It sounds like "I've lost too much to sell now". It shows up as
averaging down: buying more as the price falls. The simulation keeps the
**stop in place** and buys as many shares again at 0.5R below entry. It added
on 68–81% of trades. The worst R drawdowns went from −86R to −131R (US
Donchian), −41 to −63, −40 to −63, −38 to −68, and −27 to −33R. R per unit of
risk rose in three runs and fell in two. Even with a stop, averaging down is
simply **more risk**: −1.5R on every failure. Without the stop, it is §2's
tail, doubled.

**Countermeasures.** Set the size once, at entry. Add only to a position that
is working, and only by a written rule ([position sizing](learn-risk-sizing.md)
§9). Ask §7's question: would I buy it here?

## 12. What the evidence says

- **Robust (research):** loss aversion and the disposition effect are among the
  best-replicated findings in behavioural finance (found again and again by
  new studies). Heavy trading costs individual investors return. Knowing the
  outcome distorts how people judge the decision.
- **Measured here, consistent across runs:** chasing cost most of the edge.
  Capping winners at +1–2R gutted the trend followers. Skipping trades after
  losing streaks cost R. Streaks did not predict the next trade. Hopping to
  last year's best strategy did worse than holding them all.
- **Measured here, uncomfortable:** ignoring stops raised total R. But these
  samples are survivorship-biased (they contain only stocks still listed
  today) and come from mostly rising markets. And the price was single losses
  of −7R to −17R. Doubling after losses raised R and deepened every drawdown.
- **Not measured:** off-plan trades, hesitation and mood. A backtest cannot
  contain them; your journal can.
- **Limits:** five backtests, one history each, simulated behaviour, modelled
  costs, daily bars. Trust the direction of each result more than its size.

## 13. Checklist — the one-page bias check

**Before the trade**
- [ ] The stock is on today's setups, or on my watchlist from a screen — not from a tip, and not just because it is moving
- [ ] *Trade plan* written: entry, stop, exit rule, size, what would prove me wrong
- [ ] Within the chase limit; if not, a watchlist note with the price you would pay
- [ ] Size from the formula — not bigger after a loss or a winning streak
- [ ] Taken even after recent losses, if the plan says so

**During the trade**
- [ ] The stop is a live order and has only moved up; no averaging down
- [ ] Exit by the strategy's rule, not open P&L
- [ ] "Would I buy it here, with this stop?" — if not, why am I holding?

**Weekly**
- [ ] *Trade review* for each closed trade: plan followed (yes / no), R, what was known at entry
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
- Daniel Kahneman, *Thinking, Fast and Slow*; Mark Douglas, *Trading in the Zone*.
