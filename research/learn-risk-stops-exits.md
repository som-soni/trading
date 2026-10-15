# Stops and exits — where a trade is wrong, and how it ends

**In short**

- Decide the stop before the entry: it is the price at which the reason for the trade is proven wrong. Raise it by rule; never lower it.
- Put the stop under a real chart level. A stop that is too tight gets hit by noise; one that is far too wide says the setup is loose.
- A stop is not a guaranteed price. When a stock opens below it, often on results day or in a market-wide drop, the loss is bigger than 1R.
- The exit decides how big the winners get. On the same breakout entries, a fixed target capped the best trade near +14R; a trend exit let some run past +100R.
- Moving the stop to breakeven early, selling every breakout that dips back, and time stops all cut some of the rare big winners.

This is the third of four risk guides, after [Expectancy](learn-risk-expectancy.md) and [Position sizing](learn-risk-sizing.md); [Portfolio risk](learn-risk-portfolio.md) follows.

> **The illustrative trades in this guide** are the textbook 55-day breakouts described in the [expectancy guide](learn-risk-expectancy.md): a close above the prior 55-session high, bought at the next open, with a stop 2 × ATR(14) below the entry. Signals 2010–2025 on today's listed US and NSE companies (about 60,500 US and 17,600 Indian trades), no costs. Below, the same entries are given different stops and exits, so the comparison is fair. These trades illustrate how stops and exits behave. They are not a test of any trading system: only companies that survived are included, which flatters every average, and many trades overlap in time.

---

## 1. The stop is decided before the entry

You plan to buy a breakout at $100 because the stock has cleared a tight base whose low is $94. If it falls back below $94, the base has failed and the reason for the trade is gone. So the stop goes just under $94. You decide that before you buy.

A stop is **the price at which the reason for the trade is proven wrong**. Decide it first, for three reasons:

- **Size comes from it**: shares = risk ÷ (entry − stop) ([sizing](learn-risk-sizing.md)).
- **It sets the reward test.** A target 2R away means something only if R is known. Many traders skip any plan with less than 2R of room to the next obstacle.
- **It is the only calm decision.** Once a trade is losing, every reason to lower the stop looks good. So: **raise a stop by rule, never lower it.**

## 2. Where to put it — under structure

Put the stop **just below the level that must hold if the idea is right**. That is the nearest demand: the nearest price where buyers stepped in before ([supply and demand](learn-supply-demand.md)). It may be a swing low, a base's tight area, or a pattern's low. Add a small buffer below it, such as a tenth of an ATR, so an exact touch does not trigger it.

Well-known methods place it like this:

| Method | Initial stop | Limit |
|---|---|---|
| O'Neil (CAN SLIM) | 7–8% below the buy point | Never more than 8% |
| Minervini (VCP) | Just under the low of the last, tightest contraction | Losses averaging 6–7%; 10% at most |
| Turtle traders | 2N below the entry, where N is the 20-day ATR | None in percent; size adjusts |
| Chart patterns | Under the level that breaks the pattern | Skip the trade if it is too far |
| Pullback in an uptrend | Under the pullback's low, minus a small buffer | Often capped at about 3 ATRs |

Most of these are *structural* stops: placed under a chart level, with a limit on how wide they may be. The Turtles' stop is set by volatility alone.

## 3. How wide may a stop be?

Sizing already makes every planned loss 1R, so a wide stop does not mean a bigger loss. The width limit is about **what a wide stop says**. A base whose support is 12% away is loose, and loose bases fail more often.

Minervini aims for losses averaging 6–7%, with an absolute maximum near 10% (*Trade Like a Stock Market Wizard*). O'Neil's rule is to sell at 7–8%. Both are limits for breakouts from tight bases in leading stocks.

Volatility matters too. In the illustrative trades, a stop 2 ATRs away had a median distance of 4.6% in the US and 6.8% in India. The same rule gives wider stops in India, because its mid- and small-cap stocks move more per day.

## 4. Too tight against too wide — measured

To see what width does, we gave the same breakout entries five different stops, from 1 to 4 ATRs below the entry. Every trade then exited on the first close below its prior 20-day low, or at the stop.

| Stop distance | US: median stop | US: stopped out | US: win rate | US: median days | US: avg R | India: stopped out | India: avg R |
|---|---|---|---|---|---|---|---|
| 1 ATR | 2.3% | 79% | 18% | 7 | +0.10 | 81% | +0.34 |
| 1.5 ATR | 3.5% | 68% | 24% | 16 | +0.11 | 71% | +0.35 |
| 2 ATR | 4.6% | 57% | 29% | 28 | +0.11 | 60% | +0.35 |
| 3 ATR | 6.9% | 37% | 35% | 42 | +0.11 | 37% | +0.33 |
| 4 ATR | 9.3% | 19% | 38% | 48 | +0.10 | 18% | +0.28 |

"Stopped out" is the share of trades closed by the initial stop. Average R is before costs.

- **Wider stops are hit less often and held longer.** At 1 ATR, four trades in five were stopped out, and the median trade lasted a week. At 4 ATR, fewer than one in five were.
- **Average R hardly moved.** Each trade risked the same 1R, so a wide stop meant fewer shares, and the results evened out. No width was clearly best.
- **Costs change that.** A 1-ATR stop is about 2% away in the US, so a 0.2% round trip costs 0.1R. A tight stop also turns the money over faster, so you pay those costs more often.

So **the stop comes from structure**, not from a taste for tight or wide. A stop well inside one day's normal range is a coin toss. A stop far wider than the base says the setup is loose. Both are reasons to pass.

## 5. Gaps — when the stop is not the price you get

```series
title: Autodesk (ADSK) through its November 2017 results
from: 2017-09-01
to: 2018-01-31
tf: D
line: us:ADSK | Autodesk
mark: 2017-11-28 | a buyer near $131
mark: 2017-11-29 | results gap
caption: A breakout bought near $131 with a stop at $126.90 (3.1% risk). Results came that evening; the stock opened at $114.03 and closed at $109.34. A stop order fills at the open: about −4.1R.
```

Autodesk released its results on the evening of 28 November 2017. A trader who had bought its breakout that day near $131, with a stop at $126.90, could do nothing overnight. The stock opened at $114.03, and the stop order sold there. The loss was about four times the planned risk.

A stop order becomes a market order when the price touches it. If the stock **opens below it**, you get the opening price. In the illustrative trades, a "gap" is a fill more than 0.5% below the stop:

| Illustrative stop-outs (2-ATR stop) | US | India |
|---|---|---|
| Stop exits | 34,703 | 10,475 |
| Gapped through the stop | 9.3% | 4.6% |
| Average result of a gapped stop | −1.57R | −1.38R |
| Median result of a gapped stop | −1.33R | −1.25R |
| Stops filled worse than −1.2R | 6.6% | 2.8% |

Clean stops cost almost exactly −1R. **About one US stop in eleven gapped**, and one Indian stop in twenty. The worst cases are far worse. The worst US gap in the sample cost 11.5R: First Horizon, a bank, opened 16% lower on 1 March 2023, when its takeover by TD Bank was delayed.

### What causes them

For US companies, the quarterly filing dates are known. We counted a stop as "near results" if a quarterly report was filed within three weeks after it (six weeks for the annual report). That is a rough stand-in, since results come out days to weeks before the filing.

| US stop-outs, June 2010–2025 | Near results | Index down more than 2% that day | Neither |
|---|---|---|---|
| Gapped stops (2,386) | 50% | 19% | 37% |
| Clean stops (24,591) | 31% | 11% | 61% |

**Results are the biggest single cause, not the only one.** Gapped stops were also nearly twice as likely to fall on a day the S&P 500 dropped 2% or more. The days with the most gapped stops include 24 August 2015, 24 February 2020, 11 June 2020 and 5 August 2024. The rest were single-stock news that no calendar shows.

The best defence is the simplest: **know the results date; do not buy just before it** ([the calendar guide](learn-macro-calendar.md)). Size so that an occasional −3R to −5R gap is survivable ([sizing](learn-risk-sizing.md) §4).

## 6. Six ways to end the same trade

```series
title: Vistra (VST), 2023–2024 — one entry, six exits
from: 2023-06-01
to: 2024-08-31
tf: D
line: us:VST | Vistra | log
line: us:VST@sma50 | 50-day average
mark: 2023-07-03 | 55-day breakout, bought at $26.16
mark: 2023-07-21 | +2R target
mark: 2023-10-02 | 3-ATR trailing stop
mark: 2024-07-18 | close below the 20-day low
caption: Stop at $25.12, so 1R was $1.04. The +2R target sold three weeks in; the 20-day-low exit held for a year and sold at $77.48, about +49R, after a 27% fall from the May peak.
```

Vistra, a power producer, broke out to a 55-session high at the start of July 2023. It was bought at $26.16, with a 2-ATR stop at $25.12. The trade risked $1.04 a share. Here is how six common exits would have ended it:

| Exit rule | Exit date | Result |
|---|---|---|
| Fixed target at +2R | 21 Jul 2023 | +2.0R |
| Sell after 20 sessions | 31 Jul 2023 | +1.8R |
| Fixed target at +3R | 9 Aug 2023 | +3.3R |
| Trailing stop: highest close minus 3 ATRs | 2 Oct 2023 | +5.7R |
| First close below the 50-day average | 16 Oct 2023 | +5.6R |
| First close below the prior 20-day low | 18 Jul 2024 | +49.5R |

Each rule is common. A **target** sells into strength at a set price. A **time exit** sells after a set number of sessions. A **trailing stop** follows the price up and sells when it falls a set distance from its high. A **trend exit** sells when the price closes below an average or a recent low.

The same comparison over every illustrative trade:

| Exit (same entries, 2-ATR stop) | US win rate | US avg R | US median days | US best trade | India avg R | India best trade |
|---|---|---|---|---|---|---|
| Close below the prior 20-day low | 29.0% | +0.11 | 28 | +123.7R | +0.35 | +84.3R |
| Close below the 50-day average | 30.4% | +0.09 | 27 | +130.9R | +0.30 | +84.4R |
| Fixed target at +3R | 28.4% | +0.12 | 22 | +14.4R | +0.15 | +5.4R |
| Fixed target at +2R | 36.1% | +0.07 | 18 | +14.4R | +0.06 | +4.7R |
| Trailing stop, 3 ATRs below the highest close | 33.6% | +0.03 | 21 | +42.7R | +0.08 | +28.6R |
| Sell after 20 sessions | 41.9% | +0.03 | 25 | +24.1R | +0.05 | +12.8R |

Days are calendar days; results are before costs. What it shows:

- **Wide trend exits did well in both markets.** The 20-day-low and 50-day-average exits had the highest or near-highest average R.
- **The tight trailing stop did poorly.** Three ATRs below the highest close sold many trades on an ordinary pullback.
- **Targets raise the win rate and cap the best trade.** A +3R target matched the trend exit in the US sample, but fell well short in India, where the big trends were larger.
- **The time exit had the highest win rate and one of the lowest averages.**

## 7. Targets against letting winners run

In the illustrative US trades with the 20-day-low exit, the best 5% of trades made +25,181R. All trades together made +6,838R. In India the best 5% made +10,119R, against +6,151R in total.

**The top 5% of trades made more than the whole sample.** Without them, both markets lose money. So an exit that cuts those trades short removes the edge it means to protect.

A **fixed target caps the best outcomes**. With a +2R target, nearly every winner made less than +3R. The rare larger ones came from a stock opening far above the target after news. A **trend exit leaves no cap**, but most trends end soon: the median trade under the 20-day-low exit was still a −1R loss.

The trade-off is about how you want the results to feel. A target gives more frequent, smaller wins. A trend exit gives long losing stretches broken by a few very large wins ([expectancy](learn-risk-expectancy.md) §3).

## 8. Breakeven stops

A trade reaches +1R, and you move the stop up to the entry price. It feels free: the trade can no longer lose. But it turns a normal pullback into a scratch, a trade closed for about nothing.

We tested it on the illustrative trades with the 20-day-low exit. The stop moved to the entry once the high reached +1R, or once it reached +2R:

| Breakeven rule | US: closed at breakeven | US avg R | India: closed at breakeven | India avg R |
|---|---|---|---|---|
| None | — | +0.11 | — | +0.35 |
| Stop to entry at +2R | 8.6% | +0.11 | 9.9% | +0.31 |
| Stop to entry at +1R | 30.3% | +0.07 | 30.7% | +0.21 |

Moving the stop at +1R scratched three trades in ten. Without the rule, most of those would have gone on to lose. But about three in ten would have won. And 3–5% of them would have made +5R or more. Losing those few large wins cost more than the small losses saved.

Breakeven stops have a real use elsewhere. A stop at the entry means the position no longer risks capital, which frees room under a limit on total open risk ([portfolio risk](learn-risk-portfolio.md)). It is a portfolio choice, not free insurance.

## 9. Selling into strength, selling into weakness

```series
title: Selling into strength — Regeneron, 2013
from: 2013-01-01
to: 2013-07-31
tf: D
line: us:REGN | Regeneron
line: us:REGN@sma50 | 50-day average
mark: 2013-03-20 | bought at $175.67
mark: 2013-04-10 | a third sold at 3R
mark: 2013-05-03 | climax: 40% above the 50-day
caption: Stop at $167.67, so 1R was $8. A third sold at $199.66 (3R) on 10 April; the rest at the next open after the climax, near $264. Blended result about +8.4R. The stock peaked a week later, then fell 24% into June.
```

Take a worked example on real prices. A trader buys Regeneron at $175.67 on 20 March 2013, with a stop at $167.67. On 10 April the price reaches $199.66, three times the risk, and the trader sells a third.

Then the stock races: up 10%, 5% and 7% on three straight days. By 3 May it is 40% above its 50-day average. The trader sells the rest at the next open, near $264, for a blended result of about +8.4R. The stock peaked a week later and then fell 24% into June.

That is **selling into strength**: selling while the stock is still rising. It happens at a target, at a set multiple of R, or on a *climax*. A climax is a burst of excessive buying: the biggest up days on the biggest volume since entry, or a price far above its averages. You get a good price, but you give up whatever the stock does next.

**Selling into weakness** waits until the stock turns down: a close under the 50-day average, a new 20-day low, or a trailing stop. You stay in for the whole trend, but give back the part between the top and the exit signal. Vistra, in §6, fell 27% from its peak before the 20-day-low exit sold it.

A blend is a sensible default: **sell some into strength, and let the rest go on weakness.** Minervini's books describe exactly that ([SEPA and the VCP](learn-strat-vcp-sepa.md)).

## 10. Failed breakouts and time stops

**Failed breakouts.** A common rule says: if a breakout closes back below the breakout level within a few days, sell at once. On the illustrative trades, that happened within five sessions to half of all breakouts (50% in the US, 47% in India).

Those trades were worse than average. Held to the 20-day-low exit, they averaged −0.22R in the US and −0.16R in India. But selling them at the next open did worse still: −0.32R and −0.37R. About 3% of them later made +5R or more, and the rule sold those too.

| Rule applied to all illustrative trades | US avg R | India avg R |
|---|---|---|
| No extra rule (20-day-low exit) | +0.11 | +0.35 |
| Sell after a close back below the breakout level within 5 sessions | +0.07 | +0.25 |
| Sell after 15 sessions if the trade never reached +1R | +0.08 | +0.29 |

**Time stops.** Another rule sells a trade that has gone nowhere: for example, one that has not reached +1R after 15 sessions. About a fifth of the illustrative trades fit that description and were still open. Held on, they averaged +0.20R in the US and +0.30R in India. Sold at the fifteenth session's close, they averaged +0.05R and −0.04R.

On these trades, both rules cost money, because both sell some trades before they become large winners. They may still suit a method with a fixed target, or a trader who needs the capital for new setups. Test them on your own method before adopting them.

## 11. What a trader does

1. **Write the stop before the entry**, under the structure that proves the idea wrong, and enter it as an order.
2. **Pass on setups whose stop is wider than your limit** (about 8% for a breakout from a tight base). Do not shrink the stop to make the trade fit.
3. **Check the results date**; no new position in the week or two before it.
4. **Budget for gaps**: about one stop in ten costing around 1.5R, and an occasional −4R or worse. Size so that survives.
5. **Choose the exit style in advance** — target, trend exit, or part into strength and the rest on a trend break — never on the day.
6. **Raise stops only by rule**; never lower them.

## 12. What the evidence says

- **Robust:** a trend-following method's result comes from a few big trades. Predefined stops keep the typical loss near 1R. Gaps make a small but real share of losses worse than that.
- **Consistent in the illustrative trades:** wide trend exits beat tight trailing stops; fixed targets capped the best trades. Results and market-wide drops explained most gaps.
- **Not shown:** that any stop width is best in R. Early breakeven stops, failed-breakout rules and time stops lowered the average on these trades. They might still help a different method.
- **Limits:** the trades come from one textbook entry rule on today's listed companies (survivorship bias), with daily bars and no costs. Many trades overlap in time, so the samples are less independent than their size suggests. They show how exits behave, not what any method will earn.

## 13. Checklist

- [ ] Stop written before entry, under a structural level, entered as an order
- [ ] Stop within the limit for the setup (about 8% for breakouts and VCPs)
- [ ] Results date checked — none in the next two weeks for a new position
- [ ] Open positions: any stop to raise by rule (a trailing level, a new swing low)?
- [ ] Any holding far above its 50-day after a burst of buying — sell some into it?
- [ ] Review the week's exits by reason: stops honoured? any gaps?

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* — the maximum-loss rule and selling into strength.
- William O'Neil, *How to Make Money in Stocks* — the 7–8% loss rule and taking profits at 20–25%.
- Van K. Tharp, *Trade Your Way to Financial Freedom* — R-multiples, and exits as the larger half of a system.
- Curtis Faith, *Way of the Turtle* — channel and volatility stops, and why trend followers live on a few trades.
- Chuck LeBeau and David Lucas, *Technical Traders Guide to Computer Analysis of the Futures Market* — the chandelier (ATR trailing) exit.
