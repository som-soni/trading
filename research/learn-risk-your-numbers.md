# Your own numbers — win rate, average gain and average loss set your stop and your size

**In short**

- Three numbers describe any trader: how often you win, how much you make on an average win, and how much you lose on an average loss. Watch them together, every month.
- The loss you can afford depends on the other two. At a 40% win rate and a 15% average gain, losses must average under 10% just to break even.
- Rules for raising a stop work best when they are tied to your own average gain. Moving to breakeven too early costs more than it saves.
- In a hard market, the win rate and the average gain fall together. Tighten both ends and trade smaller, then widen back as the numbers recover.
- Your numbers also forecast how many trades a goal needs. That shows whether the goal is realistic before you start.

This guide follows [expectancy](learn-risk-expectancy.md), which defines R and the expectancy formula. Here the same ideas are applied to your own record, in percent, the way a trader reads a journal.

> **The illustrative trades used in this guide.** We re-ran the simple textbook rule from [expectancy](learn-risk-expectancy.md) on stored daily prices. Entry: a close above the highest high of the prior 55 sessions, bought at the next open. Stop: 2 × ATR(14) below the entry. Exit: the first close below the lowest low of the prior 20 sessions, sold at the next open. Signals from January 2010 to December 2025, at most one per stock per 20 sessions, on today's listed US and NSE companies with a close of at least $5 / ₹20 and 50-day turnover of at least $20m / ₹10 crore. 61,325 US and 18,042 Indian trades, no costs. Funds and corporate-action errors were not removed here, so the figures differ slightly from the expectancy guide. The stock lists contain only survivors, which flatters every average. The trades illustrate how management rules change results; they do not test a trading system.

---

## 1. The trading triangle

Two traders each close 20 trades in a quarter.

| | Trader A | Trader B |
|---|---|---|
| Win rate | 60% | 35% |
| Average gain | +6% | +18% |
| Average loss | −5% | −6% |
| Result per trade | 0.6 × 6 − 0.4 × 5 = **+1.6%** | 0.35 × 18 − 0.65 × 6 = **+2.4%** |

Trader A wins more often, and B makes more. Neither number alone says who is better. The three numbers form a triangle: change one, and the others decide whether the result still works.

A useful single figure is the **adjusted win/loss ratio**:

> **Adjusted ratio = (win % × average gain) ÷ (loss % × average loss)**

Trader A scores 3.6 ÷ 2.0 = 1.8. Trader B scores 6.3 ÷ 3.9 = 1.6. Above 1 makes money; a ratio near 2 means the wins pay for the losses twice over. The plain win/loss ratio (18 ÷ 6 = 3 for B) ignores how often each happens.

The illustrative breakouts show the triangle in both markets:

| | Win rate | Average win | Average loss | Adjusted ratio |
|---|---|---|---|---|
| US | 28.6% | 2.78R | 0.95R | 1.16 |
| India | 28.2% | 3.69R | 0.94R | 1.54 |

## 2. How large a loss can you afford?

Turn the formula around. Given your win rate and your average gain, it says how large your average loss may be.

| Win rate | Average gain | Largest average loss to break even | Average loss for an adjusted ratio of 2 |
|---|---|---|---|
| 30% | 10% | 4.3% | 2.1% |
| 30% | 20% | 8.6% | 4.3% |
| 40% | 10% | 6.7% | 3.3% |
| 40% | 15% | 10.0% | 5.0% |
| 40% | 20% | 13.3% | 6.7% |
| 50% | 10% | 10.0% | 5.0% |
| 50% | 20% | 20.0% | 10.0% |
| 60% | 15% | 22.5% | 11.2% |

Read across a row. A trader who wins 40% of the time with gains of about 10% cannot afford 8% losses. Each trade loses money on average. The same 8% stop is fine for someone whose gains average 20%.

So the stop is not a fixed number from a book. It follows from your own record.

A common ceiling is 10% on any one trade, because losses grow geometrically. A 10% loss needs an 11% gain to recover. A 50% loss needs a 100% gain ([sizing](learn-risk-sizing.md) §7). Below that ceiling, your average gain and win rate set where your stops should sit.

### Which pair of gain and loss works best?

Compounding makes the comparison sharper. This table shows the total return over 10 trades, each with the whole account:

| Win rate | +10% / −5% | +10% / −10% | +20% / −10% | +20% / −7% | +30% / −10% |
|---|---|---|---|---|---|
| 30% | −7.1% | −36.3% | −17.4% | +4.0% | +5.1% |
| 40% | +7.6% | −22.2% | +10.2% | +34.2% | +51.8% |
| 50% | +24.6% | −4.9% | +46.9% | +73.1% | +119.2% |
| 60% | +44.3% | +16.2% | +95.9% | +123.4% | +216.7% |

Three things stand out:

- **Equal gains and losses lose money** below a 60% win rate, because compounding works against you.
- **Cutting the loss is worth more than raising the gain** at a low win rate. At 40%, moving from −10% to −7% losses adds 24 points; the gain stays at +20%.
- **There is no single best pair.** The table's best column is the one you can actually achieve. A gain of +30% on average is rare; most traders' realistic numbers sit in the first three columns.

Win rate and gain size also move together. A wider stop wins more often but risks more; a far target wins less often but pays more. Change one and measure the others again ([stops and exits](learn-risk-stops-exits.md) §6).

## 3. When to raise the stop — keyed to your average gain

A trade is up. When should the stop move above the entry? The rule many traders follow: once the gain is a good multiple of the risk, and also above your average gain, it should not be allowed to become a loss. Once it is twice your average gain, lock in about your average gain with a *back stop*.

We tested these rules on the illustrative trades, kept to the same 20-day-low exit. In India the average win was 3.69R, so "twice the average gain" is about 7.4R. The back stop rows use round multiples of R around that:

| Rule | US avg R | India avg R | India: win rate |
|---|---|---|---|
| None | +0.111 | +0.366 | 28.2% |
| Stop to entry at +1R | +0.066 | +0.235 | 18.5% |
| Stop to entry at +2R | +0.106 | +0.331 | 24.8% |
| Stop to entry at +3R | +0.111 | +0.354 | 27.1% |
| At +4R, stop to +2R | +0.101 | +0.317 | 28.9% |
| At +6R, stop to +3R | +0.113 | +0.344 | 28.3% |
| At +8R, stop to +4R | +0.111 | +0.353 | 28.2% |

In the US the average win was 2.78R, so the +6R row is the nearest match to the rule there.

The later the stop moves, the less it costs. At +1R it scratched almost three trades in ten, and many of those would have gone on to win. At +3R the cost almost disappears: few trades that reach +3R fall all the way back. In the US it cost nothing at all. So if you use a breakeven stop, tie it to your own numbers: a multiple of your risk that is also above your average gain.

No rule raised the average by more than a rounding error; the early ones lowered it. Their value is elsewhere. A stop above the entry frees room under a limit on total open risk ([portfolio risk](learn-risk-portfolio.md)). It also protects your confidence: a large open gain that turns into a loss does more damage to a trader's judgement than its size suggests.

## 4. Staggered stops

Instead of one stop, split the position into thirds with stops at three levels. Say the plan is to risk 5%. Put a third at −3%, a third at −5% and a third at −8%. The average loss, if all three are hit, is still about 5%. But two thirds of the position can survive a dip below −5%.

We tested it on the illustrative trades. A single stop at 1R below the entry was compared with three stops, one per third of the position, as in the table.

| | US avg R | India avg R | India: trades that ended in profit |
|---|---|---|---|
| One stop at 1R | +0.111 | +0.366 | 28.2% |
| Thirds at 0.6R / 1.0R / 1.6R | +0.113 | +0.375 | 31.6% |

Staggering raised the share of trades that ended in profit, from 28.2% to 31.6% in India. In the US it rose from 28.6% to 31.2%. The average barely moved.

The cost is in the tail, because the third with the widest stop sits further away. The worst 5% of trades lost 1.09R instead of 1.00R in India. In the US they lost 1.18R instead of 1.14R.

Staggering trades a slightly larger worst case for more trades that survive a shakeout. It is most useful in volatile markets, when ordinary dips keep hitting single stops. It is not a way to avoid a stop: each third still has its own exit, decided in advance.

## 5. Sell half — the arithmetic and the psychology

A stock you hold is up 20%. Your average gain is 10% and your stop was 7%. It touched +25% and has started to slip. You like the company, and you cannot decide.

Sell half. Half the position is now booked at +20%. If the rest only breaks even, the trade still made 10%: your average. The rest could even fall 10% and the trade would still not lose money.

The psychology matters as much as the arithmetic. If the stock rises, you are glad you kept half. If it falls, you are glad you sold half. Neither outcome leaves you with regret, which is what drives the next bad decision.

One firm limit: this is for a profit only. **Never sell half on the way down** and hope for the rest. When a stop is hit, the whole position goes.

## 6. What to track, and the monthly tracker

Record these for every month and for your whole history:

| Statistic | Why it matters |
|---|---|
| Win rate | One corner of the triangle |
| Average gain, average loss | The other two corners |
| Win/loss ratio and adjusted ratio | The triangle in one number (§1) |
| Largest win and largest loss | One big loss can undo a month; one big win can hide a bad process |
| How long wins are held, and losses | Losses held longer than wins mean stops are not being kept |

The last row is worth a closer look. In the illustrative Indian trades, winners were held a median of 67 sessions and losers 10. In the US the figures were 63 and 11. That is the shape of a working method: losses cut quickly, wins given time. A journal that shows losers held longer than winners is a warning ([journaling and review](learn-process-journal.md)).

**The monthly tracker** is one row per month: trades, win rate, average gain, average loss, largest loss and the month's result. Read it as a trend, not a score. In the illustrative Indian trades, the weak years had both a lower win rate and smaller wins:

| Year | Trades | Win rate | Avg win | Avg loss | Per trade |
|---|---|---|---|---|---|
| 2011 | 240 | 10.4% | 2.06R | −0.95R | −0.64R |
| 2015 | 537 | 15.6% | 1.70R | −0.92R | −0.51R |
| 2018 | 666 | 12.5% | 1.98R | −0.93R | −0.57R |
| 2020 | 1,164 | 32.9% | 5.84R | −1.06R | +1.21R |
| 2023 | 2,608 | 39.3% | 5.27R | −0.93R | +1.51R |

The losses stayed at about 1R in every year, because the stop set them. What changed was how often trades won and how far the winners ran. That is why a hard market hurts twice.

## 7. Your personal bell curve

Draw a histogram of your trades by result. A working method has a curve skewed to the right: almost nothing beyond your maximum loss on the left, and a long tail of gains on the right.

| Result | Share of Indian illustrative trades |
|---|---|
| Worse than −1.5R | 0.8% |
| −1.5R to −1.05R | 2.7% |
| −1.05R to −0.5R | 61.8% |
| −0.5R to 0 | 6.5% |
| 0 to +1R | 8.7% |
| +1R to +2R | 5.4% |
| +2R to +5R | 8.2% |
| +5R to +10R | 4.0% |
| +10R or more | 2.0% |

Most trades are small losses near −1R. The 6% of trades that made +5R or more pay for them. The few results worse than −1.5R are gaps through the stop ([stops and exits](learn-risk-stops-exits.md) §5).

Look at your own curve each quarter. Results piling up left of your maximum loss mean stops are being moved or ignored. A right tail that is shrinking means winners are being cut short.

## 8. When the market turns hard

The yearly table in §6 shows what a hard market does: fewer winners, and smaller ones. If you keep the same stops and the same profit hopes, your adjusted ratio falls below 1 and you lose money on rules that worked a year earlier.

The usual adjustment shortens both ends at once:

- **Tighter stops.** If you normally cut losses at 7–8%, cut them at 5–6%.
- **Smaller profits.** If your gains normally average 15–20%, take profits at 10–12%.
- **No borrowed money.** Margin magnifies a falling win rate.
- **Smaller size and fewer positions** ([portfolio risk](learn-risk-portfolio.md) §8).

Then widen back in steps as your monthly tracker shows the win rate and average gain recovering. Your own results are the signal. Trading small at first, and moving up only after trades work, applies the same idea to the start of a new uptrend.

## 9. Small gains, turned over often

Six gains of 10% compound to +77%. One gain of 40% is +40%. Three gains of 20% compound to +73%.

| Trades | Gain each | Total, compounded |
|---|---|---|
| 1 | 40% | +40% |
| 3 | 20% | +73% |
| 6 | 10% | +77% |

Smaller gains, taken more often, can beat a few large ones, if you can find enough of them. A 10% move is far more common than a 40% one. But each trade also adds costs and the chance of a stop. The question is never "how big can this get?" alone. It is whether the gain is larger than your average loss, and whether you can repeat it.

This does not argue for cutting winners short. In a trend method, the large winners are most of the profit ([stops and exits](learn-risk-stops-exits.md) §7). It argues for not dismissing ordinary gains, and for freeing capital from a trade that has stopped moving.

## 10. How many trades does a goal need?

Your numbers also turn a return goal into a number of trades.

Take a ₹20 lakh account, with each position 25% of it. The trader's record: a 46% win rate, average gain 14%, average loss 7%.

- Each trade adds, on average, 0.25 × (0.46 × 14% − 0.54 × 7%) = 0.67% to the account.
- A goal of +40% in a year therefore needs about 60 trades added up, or about 51 when the gains compound.

| Win rate | Avg gain | Avg loss | Position size | Per trade | Trades for +40% (compounded) |
|---|---|---|---|---|---|
| 46% | 14% | 7% | 25% | +0.67% | 51 |
| 40% | 14% | 7% | 25% | +0.35% | 96 |
| 46% | 14% | 9% | 25% | +0.40% | 85 |

A small slip in the win rate or the average loss nearly doubles the trades needed. If you find about two good setups a month, the first row is out of reach in one year. The forecast tells you whether to change the goal, the size, or the method. It needs data, so start recording early.

## 11. What the evidence says

- **The arithmetic in §1, §2, §5, §9 and §10 is exact.** It needs no test; it follows from the formula.
- **Breakeven and back stops** (§3): on the illustrative trades, no version raised the average result. Later triggers cost less. This matches [stops and exits](learn-risk-stops-exits.md) §8.
- **Staggered stops** (§4): on the illustrative trades the average moved by under 0.01R in both markets. About 4% of all trades turned from a full stop-out into a profit.
- **Hard markets** (§6, §8): the yearly figures show the win rate and average win falling together, with the loss held by the stop. The adjustments in §8 are practitioner advice; we have not tested them as rules.
- **Practitioner sources.** The trading triangle, stops keyed to the average gain, staggered stops, the sell-half rule and the trade forecast are set out in Mark Minervini's *Think & Trade Like a Champion*. The tests here use our own illustrative trades, not his figures.

## 12. Checklist

- [ ] I know my win rate, average gain and average loss, overall and for the last three months.
- [ ] My average loss is well under the break-even loss for my win rate and average gain (§2).
- [ ] My stop moves above the entry only at a multiple of my risk that is also above my average gain.
- [ ] I sell part into strength only when in profit; on the way down, the whole position goes at the stop.
- [ ] My winners are held longer than my losers.
- [ ] I look at my histogram each quarter: nothing piling up left of my maximum loss.
- [ ] When the monthly numbers fall, I tighten stops, take smaller profits and trade smaller; I widen back only as they recover.
- [ ] I have checked how many trades my return goal needs.

## Further reading

- Mark Minervini, *Think & Trade Like a Champion* (2017) — the trading triangle, stops from your average gain, staggered stops, sell half, results-based forecasts.
- Van K. Tharp, *Trade Your Way to Financial Freedom* — R-multiples and expectancy.
- [Expectancy](learn-risk-expectancy.md), [Position sizing](learn-risk-sizing.md), [Stops and exits](learn-risk-stops-exits.md), [Portfolio risk](learn-risk-portfolio.md), [Journaling and review](learn-process-journal.md).
