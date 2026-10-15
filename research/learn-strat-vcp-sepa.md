# SEPA and the VCP — Minervini's way to trade a leader

**In short**

- Mark Minervini's SEPA buys stocks that are already in a strong uptrend (the Trend Template), have strong earnings, and have just formed a tight base: a volatility contraction pattern (VCP).
- The entry is a buy-stop just above the pivot of the last, tightest contraction. The stop goes just under that contraction's low, so the risk is usually 3–8% and never more than 10%.
- Size every trade from its stop, and raise or cut your overall exposure according to whether your recent trades are working (progressive exposure).
- Move the stop to breakeven once the gain is two to three times the risk. Sell part into strength (a fast, extended move) and the rest into weakness (a close below the 50-day average).
- In broad data the shape alone adds little. The method's case rests on combining trend, earnings, a tight entry and strict loss control.

## 1. The idea

In November 2020, Havells India, an electrical-goods maker, reached ₹855 and then paused. It fell 6.9% to ₹796. It recovered to ₹844.60, then fell only 3.7%, to ₹813. In the last few days before the breakout, volume dropped to between a quarter and nine-tenths of its 50-day average. On 15 December 2020 it rose through ₹855 on 2.65 times its normal volume.

```series
title: Havells India — a short VCP and a breakout, December 2020
from: 2020-10-01
to: 2021-03-31
tf: D
line: india:HAVELLS.NS | Havells India | log
line: india:HAVELLS.NS@sma50 | 50-day average
line: india:HAVELLS.NS@vol | Volume | pane2 bars
mark: 2020-11-19 | base high ₹855
mark: 2020-11-27 | pullback 6.9%
mark: 2020-12-08 | pullback 3.7%
mark: 2020-12-15 | breakout, 2.65× volume
caption: Two pullbacks, each smaller than the one before, with volume drying up into the second. The stop sat just under ₹813.
```

That is a **volatility contraction pattern**: price swings that get smaller from left to right while volume fades. Each pullback is smaller because fewer holders are left who want to sell. When the last pullback is tiny and quiet, a small amount of buying can push the price through the top. The pattern's anatomy is covered in [VCP](learn-vcp.md). This guide is about trading it.

**SEPA** stands for Specific Entry Point Analysis. It has five parts: the trend, the fundamentals, a catalyst, the entry point and the exit. The VCP is the entry. The rest decides which VCPs are worth buying and how to get out.

Who is on the other side? Mainly two groups. Holders from lower prices sell into each rally, and their selling is what makes the early pullbacks. Short-term traders sell on each dip and give up.

By the end of the base, both groups have mostly sold. The buyers are funds and traders who want a leader with growing earnings. The tight stop is the point: if the remaining sellers were not in fact exhausted, you find out quickly and cheaply.

## 2. When it works and when it doesn't

It works best when the market is in a confirmed uptrend and many stocks pass the Trend Template. Minervini watches how many leaders are setting up and breaking out. When breakouts work, he trades more. When they fail one after another, he trades less.

It works poorly in:

- **Corrections and bear markets.** Few stocks pass the Trend Template, and the bases that form are often deep and loose.
- **Choppy markets.** Tight stops get hit by ordinary noise.
- **Low-priced, thinly traded stocks.** The pattern looks the same, but a few orders can move the price through the pivot or the stop.

It suits stocks in Stage 2 of their price cycle (see [Stages and trend in a stock](learn-price-stages.md)), with earnings and sales growth that is speeding up. Its stops are tighter than O'Neil's CAN SLIM, so it needs a precise entry and good liquidity.

**India.** Many NSE leaders are mid caps with price bands of 10% or 20% a day. A VCP breakout can lock at the upper band, and the buy-stop may not fill. A breakdown can also lock at the lower band, so the stop fills well below its level.

Prefer stocks with no daily band (most derivative-segment stocks) or with deep order books. Settlement is T+1. This is a long-only method. **US.** Liquidity is deep, and the low-priced end is where the pattern is least reliable.

## 3. The rules

Each rule below is a condition a program can check. Section 4 gives the ranges.

### Universe and filters

- **Liquidity.** Close at least ₹100 or $15. The 50-day average daily turnover is at least ₹10 crore or $20 million.
- **Trend Template.** All of these are true on the day of the setup:
  - the close is above the 150-day and the 200-day moving averages;
  - the 150-day is above the 200-day;
  - the 200-day is higher than it was 21 sessions ago (one month; Minervini prefers four to five months);
  - the 50-day is above the 150-day and the 200-day;
  - the close is above the 50-day;
  - the close is at least 30% above its 52-week low;
  - the close is within 25% of its 52-week high;
  - the stock's relative strength percentile is at least 70 (see [Relative strength](learn-price-rs.md)).
- **Fundamentals.** Quarterly EPS growth of at least 20% on the same quarter a year earlier, and higher than the quarter before (acceleration). Sales growth of at least 15%. A stable or rising profit margin. Use announced numbers only (see [Earnings that move stocks](learn-fund-earnings.md)).
- **Catalyst (optional).** A new product, a sector tailwind, an earnings surprise. It cannot be coded well, so treat it as a tie-breaker.
- **Market.** The index closes above its 50-day average, and the share of stocks above their own 50-day average is rising or above half.

### Setup

```pattern
vcp
```

- **Prior advance.** The base high is at least 30% above the lowest low of the six months before it.
- **Base length.** 3 to 65 weeks.
- **Contractions.** Find each pullback from a swing high to the next swing low, as a percentage of the high. Count 2 to 6 of them. Ignore reversals smaller than about 1.5 times the 14-day ATR.
- **Shrinking.** Each pullback is at most 0.8 times the one before.
- **Limits.** The first pullback is at most 35% deep (up to 50% after a bear market). The last is at most 10%, ideally under 6%.
- **Volume dry-up.** Average volume over the last 5–10 sessions before the breakout is at most 0.7 times the 50-day average.
- **Pivot.** The high of the last contraction. It sits within 10% of the base high.
- **Footprint.** Write it down as weeks / deepest % / last % / number of contractions, e.g. "8W 10/4 4T".

### Entry

- **Pivot buy (default).** A buy-stop order one tick above the pivot. Valid only if breakout volume reaches at least 1.4 times the 50-day average by the close. If it does not, sell or wait for another try.
- **Buy zone.** Do not buy more than 5% above the pivot.
- **Cheat entry.** A small shelf forms in the middle third of the base: 3–10 quiet sessions with a narrow range. Buy one tick above the shelf's high, stop under the shelf's low. Minervini calls a version of this the "3C" (cup completion cheat).
- **Low cheat.** The same, but in the lower third of the base. Cheaper and riskier: the base is less finished.
- **Daily-data version.** For testing, a buy-stop above the pivot fills at the pivot, or at the open if the open is higher. The trade is kept only if the close is above the pivot.

### Initial stop

- One tick under the low of the last contraction (or the shelf, for a cheat entry).
- If that is more than 10% below the entry, skip the trade. Minervini's aim is a much smaller average loss than that.

### Exits

- **Breakeven.** When the price reaches entry + 2R (two times the initial risk), raise the stop to the entry price.
- **Sell into strength.** Sell a third to a half of the position when the close is 25% or more above the 50-day average, or after the biggest up-day since the breakout, late in the move.
- **Sell into weakness.** Sell the rest on the first close below the 50-day average.
- **Failed breakout.** If the price closes back below the pivot and then below the last contraction's low, the stop handles it. Do not wait for it to recover.
- **Time.** If the trade has not reached +1R within 15 sessions, consider selling. Strong breakouts tend to move soon.

### Position size

- Risk a fixed share of capital per trade. Minervini suggests around 1.25–2.5% at most; 0.5–1% is a cautious start.
- Shares = (capital × risk %) ÷ (entry − stop). A 5% stop and 1% risk give a 20% position. Cap any one position at 25% of capital.
- See [Position sizing](learn-risk-sizing.md).

### Managing the trade

**Progressive exposure.** Begin a new period with small positions (for example a quarter of normal size). Move to full size only after two or three trades have worked. After a run of stop-outs, cut size again. Your own results become a gauge of the market.

- Never add to a losing trade.
- You may add a second piece when the price clears a new, smaller pivot above the first entry.
- A stock that stops you out can be bought again if it builds a new, valid setup. Re-entry is part of the method.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price / turnover | ₹100 / $15; ₹10 crore / $20m | Tradeability | Raise for bigger accounts |
| 200-day rising over | 21 sessions (21–105) | Trend maturity | Longer = fewer, cleaner stocks |
| Above 52-week low | ≥ 30% | Distance from the bottom | 25–100% |
| Within 52-week high | ≤ 25% | Nearness to highs | 15–25% |
| RS percentile | ≥ 70 | Leadership | 70–90 |
| Quarterly EPS growth | ≥ 20%, accelerating | Earnings strength | 20–40% |
| Sales growth | ≥ 15% | Quality of earnings growth | 10–25% |
| Prior advance | ≥ 30% | Uptrend into the base | 25–100% |
| Base length | 3–65 weeks | Base maturity | Very short bases fail more |
| Number of contractions | 2–6 | Shape | Usually 2–4 |
| Minimum swing size | 1.5 × ATR(14) | What counts as a contraction | Smaller counts noise as pullbacks |
| Contraction ratio | ≤ 0.8 × previous | "Shrinking" | 0.5–0.9 |
| First contraction | ≤ 35% | Damage in the base | Up to 50% after a bear market |
| Last contraction | ≤ 10% (ideal < 6%) | Tightness, stop distance | Sets the stop size |
| Volume dry-up | ≤ 0.7 × 50-day avg | Supply exhausted | 0.5–0.8 |
| Pivot vs base high | ≥ 0.9 | Pivot near the top | 0.85–1.0 |
| Breakout volume | ≥ 1.4 × 50-day avg | Demand | 1.4–2.0 |
| Buy zone | ≤ 5% above pivot | Chasing limit | 3–5% |
| Maximum stop | 10% | Biggest allowed risk | Most trades should be well under |
| Breakeven trigger | +2R (2–3R) | When the trade becomes free | Earlier = more scratch trades |
| Sell-into-strength trigger | close ≥ 25% above 50-day | Partial profit | 20–40%; varies with volatility |
| Part sold into strength | 1/3 to 1/2 | Locking gains | |
| Final exit | close below 50-day | Trend break | 20-day or 10-day for faster trading |
| Time stop | +1R within 15 sessions | Dead money | Optional |
| Risk per trade | 0.5–2.5% | Position size | Start low |
| Starting size (progressive exposure) | 25–50% of normal | Exposure control | Increase after wins |

## 5. Variations

- **Minervini's own books** (*Trade Like a Stock Market Wizard*, *Think & Trade Like a Champion*) are the source of the rules above. He also trades "power plays": stocks up 100% or more in under eight weeks that then go sideways briefly. That is close to the high tight flag in [Flags, pennants and high tight flags](learn-strat-flags.md).
- **O'Neil's CAN SLIM** uses the same idea with wider stops (7–8%) and named base shapes. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Stan Weinstein's stage analysis** supplies the trend filter that the Trend Template formalises: buy only in Stage 2.
- **Shorter-term versions.** Some traders use the same tight setups but exit on a close below the 10-day or 20-day average. Exits come sooner; gains are smaller and more frequent.
- **Box-style versions.** Darvas bought tight boxes at new highs with the stop at the box bottom, a simpler cousin of the VCP. See [Darvas boxes](learn-strat-darvas.md).

## 6. Worked examples

Prices are adjusted for later splits.

### Havells India, December 2020 — a short VCP that worked

This is the chart in section 1.

- **Trend Template.** On 15 December 2020 the close was ₹864.80. The 50-day was ₹779, the 150-day ₹656 and the 200-day ₹627, in the right order. The close was nearly double its 52-week low.
- **Setup.** Base high ₹855 on 19 November. Pullbacks of 6.9% and 3.7%. Footprint about "4W 7/4 2T". Volume in the five sessions before the breakout was 0.26–0.88 times average.
- **Entry.** Buy-stop at ₹855.05. The stock opened at ₹830 and traded through it. Volume was 2.65 times average. Stop at ₹809, under the ₹813 low: a risk of 5.4%, or ₹46.05 per share.
- **Management.** The price reached +2R (₹947.15) on 6 January 2021; the stop moved to breakeven.
- **Sell into strength.** On 21 January the close, ₹1,131.95, was more than 25% above the 50-day average. Sell half: +32.4%.
- **Sell into weakness.** The first close below the 50-day came on 16 March 2021, at ₹1,088.45. Sell the rest: +27.3%, about 5R.

### Lam Research, May 2023 — a four-step contraction

```series
title: Lam Research — contractions of 10%, 8%, 5% and 4%, then a breakout
from: 2023-02-15
to: 2023-08-31
tf: D
line: us:LRCX | Lam Research (split-adjusted) | log
line: us:LRCX@sma50 | 50-day average
line: us:LRCX@vol | Volume | pane2 bars
mark: 2023-04-06 | pullback 9.9%
mark: 2023-04-27 | pullback 8.0%
mark: 2023-05-09 | pullback 3.7%
mark: 2023-05-15 | breakout
mark: 2023-08-16 | close below 50-day
caption: The pivot was the 20 April high, 53.65. Volume was below average for the five sessions before the breakout.
```

- **Setup.** From late March, the pullbacks were 9.9% (to 48.04), 8.0% (to 49.34), 4.6% (to 50.72) and 3.7% (to 51.21). Footprint about "8W 10/4 4T". The Trend Template's price conditions passed.
- **Entry.** Buy-stop at 53.70, filled on 15 May 2023. Breakout volume was 1.36 times average — just under the 1.4 guide. The next day was 1.35 times. A strict reading would wait. Stop at 51.00, under the last low: risk 5.0%.
- **Management.** +2R (59.10) was reached on 18 May; the stop moved to breakeven. The close never got 25% above the 50-day average, so there was no sale into strength.
- **Exit.** The first close below the 50-day was on 16 August 2023, at 64.63. Result: +20.4%, about 4R.

### Trent, September 2023 — stopped out, then the move came without you

```series
title: Trent — a failed VCP breakout, and the base that followed
from: 2023-07-15
to: 2024-01-31
tf: D
line: india:TRENT.NS | Trent | log
line: india:TRENT.NS@sma50 | 50-day average
line: india:TRENT.NS@vol | Volume | pane2 bars
mark: 2023-09-25 | breakout, 2.87× volume
mark: 2023-10-04 | stop hit
mark: 2023-11-01 | new breakout above ₹2,185
caption: The September breakout failed within six sessions. The stock rebuilt a base and broke out again on 1 November.
```

- **Setup.** Base high ₹2,131.55 on 8 September. Pullbacks of 5.6% and then 3.2%, to ₹2,022.45 on 20 September. The Trend Template passed.
- **Entry.** Buy-stop at ₹2,131.60 on 25 September, on 2.87 times average volume. Stop at ₹2,012: risk 5.6%.
- **What happened.** The stock closed back below the pivot two days later. On 4 October the low reached ₹2,007.60 and the stop sold at ₹2,012. Loss: −5.6%, or −1R.
- **The second base.** The stock pulled back 8.1% and then 8.2%, and broke out above ₹2,185 on 1 November. Those pullbacks did not shrink, so strict VCP rules did not allow a re-entry. By May 2024 it had traded at more than double that breakout price.
- **Lesson.** The stop did its job: a small, planned loss. Strict pattern rules then missed the larger move. Whether you allow a looser re-entry rule is a parameter to test, not a matter of opinion.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Skipping the Trend Template because the pattern looks perfect | A tight base in a stock below its 200-day is not the same setup |
| Counting every wiggle as a contraction | Any choppy chart then looks like a VCP |
| Accepting a last contraction of 10%+ | The stop is far away; the base is not finished |
| Widening the stop after entry | Turns a small planned loss into a large one |
| Buying a breakout on light volume | No sign of the demand the pattern promises |
| Full size from the first trade after a correction | Progressive exposure exists because early breakouts fail most |
| Selling a winner on the first dip below the pivot | Use the stop, not your nerves |
| Never selling into strength | Fast, extended moves often give back much of the gain |
| Refusing to re-enter after a stop-out | Re-entry on a new setup is part of the method |

## 8. What the evidence says

**Minervini's record.** He won the US Investing Championship in 1997 and has described his returns in his books. A trader's personal record shows that the method can be traded well. It does not show how often its rules work for others, or how much depends on his judgement.

**Published research behind the parts:**

- **Momentum.** Stocks that rose most over the prior 3–12 months tended to keep outperforming for months (Jegadeesh and Titman, 1993). The Trend Template is a momentum filter.
- **Nearness to the 52-week high.** Stocks near their 52-week high outperformed those far below it (George and Hwang, 2004).
- **Earnings drift.** Prices keep drifting after strong earnings surprises (Bernard and Thomas, 1989).
- **Patterns in general.** An automated study of chart patterns found that some carry a little information about future returns, but far less than practitioners claim (Lo, Mamaysky and Wang, 2000).

**An event study on stored data.** We took every mechanical base breakout and looked at the parts SEPA adds.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to July 2026. A breakout is the first close above the highest high of the prior 35 sessions, out of a base 8–35% deep, near the 52-week high, after a 30%+ advance. Liquidity: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. "Trend Template" uses its price conditions only (no RS rank). "VCP" means: at least two pullbacks (3% zig-zag) since the highest high of the prior 65 sessions, each at most 0.8 times the previous, first ≤ 35%, last ≤ 10%; volume in the last 10 sessions ≤ 0.8 times average; Trend Template passed. Outcome A: +20% before −8% within 60 sessions. Outcome B: a SEPA-style stop at the lowest low of the prior 10 sessions (trades skipped if that is more than 10% away), and +3R before the stop. Caveats: survivorship (today's lists), no costs, no fundamentals, overlapping samples.

| Outcome A: +20% before −8% | India: share | India: median 60-day | US: share | US: median 60-day |
|---|---|---|---|---|
| All breakouts | 29.5% | +2.6% | 18.0% | +1.6% |
| Trend Template passed | 29.7% | +3.1% | 17.5% | +1.5% |
| Trend Template failed | 28.9% | +1.6% | 19.1% | +1.9% |
| VCP | 27.6% | +2.0% | 19.1% | +1.4% |

| Outcome B: SEPA-style stop | India | US |
|---|---|---|
| Breakouts with a stop within 10% | 3,930 of 16,933 | 25,431 of 52,444 |
| Median stop distance | 8.3% | 7.5% |
| +3R before the stop | 18.7% | 10.6% |
| Stop first | 51.9% | 53.9% |
| Average result, in R, before costs | +0.29R | +0.08R |
| VCP only: events / +3R first / average | 103 / 24.3% / +0.37R | 333 / 10.8% / +0.08R |

What this shows:

- **Strict VCPs are rare.** About 1.5% of Indian and 1.0% of US breakouts met the mechanical VCP test.
- **The shape alone adds little.** VCP breakouts did not clearly beat other breakouts. The Indian sample of 103 is too small to separate +0.37R from +0.29R.
- **The Trend Template helped slightly in India, not in the US.** Its median 60-day result was higher in India and lower in the US.
- **Tight stops are not as tight as the books suggest.** The median distance to the 10-day low was 7–8%, and most breakouts did not have a low within 10% at all.
- **Volume dry-up made no visible difference** in either market.

**What is unknown.** No study tests full SEPA — the trend, point-in-time earnings, the VCP, progressive exposure and the selling rules together. Judgement about the market and the stock's story may matter more than any single rule. Treat the method as a framework to test, not a proven edge.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV; an index; quarterly EPS and sales with announcement dates; a relative-strength rank computed across your whole universe each day.

**Look-ahead traps.**

- A swing high is only known some sessions later. The zig-zag that finds contractions must use only bars that existed on the day you test.
- The pivot must be fixed the day before the breakout; the breakout bar cannot move it.
- Earnings must be the last announced numbers, not the quarter that ended.
- The RS rank must be computed from data up to that day, across the stocks that existed then.

**Survivorship.** Use lists that include delisted companies. Failed leaders that were later delisted are exactly the trades a today's-list test leaves out.

**Costs.** In India a delivery round trip costs roughly 0.25–0.35%. That covers STT of 0.1% each side, stamp duty of 0.015% on the buy, exchange fees, GST and depository charges. With a 5% stop, that is already 0.05–0.07R per trade before slippage. Slippage on breakout buy-stops in mid caps is often 0.2–1%. Tight-stop methods are more sensitive to costs than wide-stop ones; measure results in R after costs.

**What to test.** Start with the contraction ratio, the last-contraction limit, the breakout volume and the exit rule. Change one at a time. Prefer settings in a broad flat region of good results. Hold out the last few years and test them once.

**What a good test reports.** Trades per year, win rate, average win and loss in R, expectancy after costs, the longest losing streak, drawdown, and results by market regime. Also report how many setups the rules found per year: a rule set that trades five times a year cannot be judged on a few years of data. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t:
    exposure = progressive_exposure(recent closed trades)      # 0.25 .. 1.0
    for each stock passing liquidity, trend_template(t), fundamentals(as announced by t):
        base = find_vcp(bars up to t - 1)                     # contractions, ratio, limits, dry-up
        if base is None: continue
        if high[t] > base.pivot and open[t] <= 1.05 * base.pivot:
            entry = max(open[t], base.pivot + tick)
            stop = base.last_low - tick
            if (entry - stop) / entry > 0.10: continue
            if close[t] <= base.pivot or volume[t] < 1.4 * avg_volume_50[t - 1]: exit next open
            shares = capital * risk_pct * exposure / (entry - stop)
manage daily:
    if low <= stop: sell at min(open, stop)
    if high >= entry + 2R: stop = max(stop, entry)
    if close >= 1.25 * sma50 and not sold_part: sell half
    if close < sma50: sell the rest
```

## 10. Checklist

- [ ] Market: index above its 50-day; breakouts are working; exposure set accordingly
- [ ] All eight Trend Template conditions pass
- [ ] Quarterly EPS up 20%+ and accelerating; sales up 15%+ (announced numbers)
- [ ] Prior advance of 30%+ into the base
- [ ] 2–6 contractions, each at most 0.8 times the one before; the last under 10%
- [ ] Volume dried up in the last contraction
- [ ] Footprint written: weeks / deepest / last / count
- [ ] Pivot and stop marked; stop no more than 10% (ideally under 6%) below the pivot
- [ ] Position size from the stop and the current exposure level
- [ ] Breakout volume at least 1.4 times average; entry within 5% of the pivot
- [ ] Plan written: breakeven at +2R, part sold into strength, rest on a close below the 50-day
- [ ] In India: stock not locked at its price band; no results due within two weeks

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* (McGraw-Hill, 2013) — the Trend Template, the VCP, SEPA and risk control.
- Mark Minervini, *Think & Trade Like a Champion* (2017) — entries, cheat setups, selling into strength and weakness, progressive exposure.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* (1988) — the stage analysis behind the trend filter.
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* (1993).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- [VCP](learn-vcp.md), [Bases](learn-bases.md), [Stops and exits](learn-risk-stops-exits.md).
