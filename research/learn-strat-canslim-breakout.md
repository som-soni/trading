# CAN SLIM breakouts — buying a leader as it leaves its base

**In short**

- William O'Neil's method buys a fast-growing, market-leading stock at the moment it breaks out of a base: a cup with handle, a double bottom or a flat base.
- The buy point is the pivot. Buy only within 5% above it, and only when volume on the breakout day is well above normal.
- Losses are cut at 7–8% below the buy price, with no exceptions. Most gains are taken at 20–25%. A stock that gains 20% within three weeks is held for at least eight weeks.
- The seven letters are filters. Six describe the stock (earnings, newness, supply, leadership, institutional buying); the M says buy only when the market itself is in an uptrend.
- Breakouts alone are a weak edge in broad data. The method's claim rests on combining the shape with strong earnings, leadership and a healthy market.

## 1. The idea

In September 2023, CDSL, one of India's two securities depositories, hit ₹715 and then went sideways for seven weeks. The lowest point of that pause was ₹631, about 12% below the high. In late October it reported quarterly earnings 35.5% higher than a year earlier. On 31 October it closed at ₹728, above the old high, on 5.8 times its normal volume.

```series
title: CDSL — a flat base and a breakout on heavy volume, 2023
from: 2023-08-01
to: 2024-02-29
tf: D
line: india:CDSL.NS | CDSL (adjusted) | log
line: india:CDSL.NS@sma50 | 50-day average
line: india:CDSL.NS@vol | Volume | pane2 bars
mark: 2023-09-11 | base high ₹715
mark: 2023-10-26 | base low ₹631
mark: 2023-10-31 | breakout, 5.8× volume
caption: The pivot is the base high. The breakout close was 1.8% above it. Eight sessions later the stock was 20% higher.
```

That is a CAN SLIM breakout. A company with growing profits pauses after a rise. The pause is the **base** — a sideways range in which shares pass from short-term holders to longer-term ones. When the price clears the top of the range on heavy volume, it shows that demand has absorbed the supply that was waiting there. The top of the range is the **pivot**, the buy point.

Who is on the other side? Two groups. The first are holders who bought near the old high, saw the stock fall, and sell as soon as they get their money back. The base exists because their selling has to be absorbed.

The second are large funds that cannot buy a full position in a day. O'Neil's argument is that funds buying over weeks and months leave a trace: strong volume on up days, the price holding up while the market dips, and finally a breakout. You buy early in that buying, not before it.

The name is a list of seven letters, each a filter on the stock or the market:

| Letter | Stands for | What it asks |
|---|---|---|
| C | Current earnings | Is the latest quarter's earnings per share up sharply on the same quarter a year ago? |
| A | Annual earnings | Have yearly earnings grown strongly for several years? |
| N | New | Is there a new product, a new management or a new price high? |
| S | Supply and demand | Is volume heavier on up days than on down days? |
| L | Leader or laggard | Is the stock among the strongest in the market? |
| I | Institutional sponsorship | Are more funds buying the stock? |
| M | Market direction | Is the overall market in an uptrend? |

The base breakout is the entry; the letters decide which breakouts deserve your money. This guide covers both. For how bases form, read [learn-bases](learn-bases.md); for the shapes, [learn-chart-patterns](learn-chart-patterns.md).

## 2. When it works and when it doesn't

It works best in a **young bull market**. That is the period after a correction ends, when new leaders break out of their first or second base. O'Neil's own observation is that about three in four stocks move with the general market. So a good base in a falling market usually fails.

It works poorly in three conditions:

- **A market correction.** Breakouts fail quickly, one after another, and the 7–8% stops add up.
- **A choppy, sideways market.** Breakouts start and stall, with no follow-through.
- **Late-stage bases.** A third or fourth base after a long advance is more likely to fail. By then most investors who want the stock already own it.

It suits stocks with real earnings growth and a story that funds can understand. It suits mid and large caps better than tiny stocks: funds need liquidity to build the positions that drive the move. Cyclical stocks at the top of their cycle can show great earnings and a base, but the earnings are near a peak.

**India.** NSE breakouts often happen in sector waves: capital goods, defence, railways, capital-market stocks. Watch the sector as much as the stock.

Many small and mid caps have a daily price band (circuit limit) of 5–20%. A stock can lock at its upper limit on the breakout day, and then you cannot buy at all. Settlement is T+1, so a breakout bought today is in your account tomorrow. This is a long-only method; there is no short side to worry about.

**US.** Liquidity is deeper and costs are lower. Breakouts on results days are common, and the price often gaps far beyond the 5% buy zone at the open.

## 3. The rules

The rules below are written so that each one can be checked by a program. Every number is a parameter; section 4 gives its typical range.

### Universe and filters

- **Price and liquidity.** Close at least ₹100 in India or $15 in the US. The 50-day average of daily turnover (close × volume) is at least ₹10 crore or $20 million.
- **C — current earnings.** The latest reported quarter's EPS is at least 25% above the same quarter a year earlier. Sales are up at least 20%, or growth is speeding up.
- **A — annual earnings.** Annual EPS grew at least 25% in each of the last three years. Return on equity is at least 17%.
- **N — new high.** The pivot is within 15% of the 52-week high, and ideally the breakout makes a new 52-week high.
- **S — supply and demand.** Over the last 50 sessions, total volume on up days exceeds total volume on down days.
- **L — leader.** The stock's 12-month price performance ranks in the top 20% of all stocks (a percentile of 80 or more). See [learn-price-rs](learn-price-rs.md).
- **I — institutional sponsorship.** The number of funds holding the stock rose last quarter. In India, use the quarterly shareholding pattern: combined FII and DII holding is higher than a quarter ago.
- **M — market direction.** The index (Nifty 500 or S&P 500) closes above its 50-day average. It has had at most 4 distribution days in the last 25 sessions. See [learn-health-distribution](learn-health-distribution.md).

### Setup

First, the stock must have advanced before the base. The base's high is at least 30% above the lowest low of the six months before the base began.

Then one of three bases must be complete:

```pattern
cup-with-handle
```

- **Cup with handle.** The cup lasts 7 to 65 weeks and is 12–33% deep. The bottom is rounded, not a sharp V. The right side rises back to within 5% of the left-side high. Then a handle forms: at least 5 sessions long, at most 12% deep, sloping sideways or down. The handle's low stays in the upper half of the cup. Volume in the handle is below the 50-day average. **Pivot:** the handle's high.

```pattern
double-bottom
```

- **Double bottom.** A W shape lasting at least 7 weeks, at most 33% deep. The second low equals or slightly undercuts the first. **Pivot:** the high of the middle peak of the W.

```pattern
flat-base
```

- **Flat base.** At least 5 weeks long, at most 15% deep from high to low. It often forms after a breakout from an earlier, deeper base. **Pivot:** the base's high.

Count the bases since the stock's last major low. Take first- and second-stage bases; skip the fourth and later.

### Entry

- **Order.** A buy-stop order just above the pivot (pivot plus one tick). It triggers only if the price trades above the pivot.
- **Volume.** The breakout session's volume is at least 1.4 times its 50-day average. On daily data, check this at the close. If the session fails the volume test, sell the next day or wait for a second try.
- **Buy zone.** Do not buy above pivot × 1.05. If the stock opens above that, skip it.
- **Daily-data version.** For testing: the close is above the pivot, the close is no more than 5% above it, and volume is at least 1.4 times average. Enter at that close or the next open.

### Initial stop

Sell if the price falls 7–8% below your buy price. O'Neil treats this as absolute: never move it lower, never wait for a bounce. Testable form: exit when the low touches entry × 0.92.

### Exits

- **Profit target.** Sell most of the position when the gain reaches 20–25%.
- **The 8-week rule.** If the stock gains 20% or more within three weeks (15 sessions) of the breakout, hold it for at least eight weeks (40 sessions) from the breakout. The stop still applies. The idea: a stock that moves this fast may be a big leader, and selling at 20% gives up the rest.
- **Trend break.** After the 8 weeks, sell on a close below the 50-day average on volume at least 1.4 times average.
- **Climax.** Sell into a run of unusually large up days late in a long advance (see [learn-price-volume](learn-price-volume.md)).
- **Market.** When the M filter turns off, buy nothing new, and tighten stops on what you hold.

### Position size

O'Neil ran concentrated portfolios of a handful of stocks. A rule-based version sizes each trade from its stop. Risk a fixed 0.5–1% of capital per trade. With an 8% stop and 1% risk, that is a position of 12.5% of capital. See [learn-risk-sizing](learn-risk-sizing.md).

### Managing the trade

- O'Neil describes buying a position in pieces: a first part at the pivot, more as it rises, all within the 5% buy zone. Never add below your first price.
- Never average down.
- A breakout that closes back below the pivot is not, on its own, a sell signal. Pullbacks to the pivot are common. The 7–8% stop decides.
- Write down the pivot, entry, stop, target and the date the 8-week clock started, before you buy.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price | ₹100 / $15 | Avoids penny stocks | Low; mainly a liquidity guard |
| Minimum turnover (50-day avg) | ₹10 crore / $20m | Tradeable size, slippage | Raise it for bigger accounts |
| Quarterly EPS growth (C) | 25% (18–50%) | Earnings strength | Higher thresholds cut the universe sharply |
| Quarterly sales growth | 20% (15–30%) | Quality of the earnings rise | Optional for banks |
| Annual EPS growth (A) | 25% for 3 years | Consistency | Few Indian small caps pass three years |
| Return on equity | 17% | Profitability | Use a lower bar for capital-heavy sectors |
| Pivot vs 52-week high (N) | within 15% | Leadership | 0% means "only new highs" |
| Up/down volume (S), 50 sessions | above 1.0 | Accumulation | Noisy on its own |
| RS percentile (L) | 80 (70–90) | Leadership | See section 8: the effect is small in our data |
| Distribution days allowed (M) | 4 in 25 sessions | Market health | See [learn-health-distribution](learn-health-distribution.md) |
| Prior advance into the base | 30% | Trend before the base | 20–50% |
| Cup length | 7–65 weeks | Base maturity | Short cups fail more often |
| Cup depth | 12–33% | Damage in the base | Up to 50% after a bear market |
| Handle length / depth | ≥ 5 sessions / ≤ 12% | Shakeout of weak holders | Handle must sit in the cup's upper half |
| Double-bottom length / depth | ≥ 7 weeks / ≤ 33% | Base quality | Second low should undercut the first |
| Flat-base length / depth | ≥ 5 weeks / ≤ 15% | Base quality | Common as a second base |
| Breakout volume | ≥ 1.4× 50-day average | Demand confirmation | 1.4–2.0×; see section 8 |
| Buy zone | ≤ 5% above pivot | Entry price vs stop | Beyond 5% the stop is too far away |
| Stop | 7–8% below entry | Maximum loss | Tighter than 5% gets shaken out often |
| Profit target | 20–25% | Where most gains are taken | A 3:1 gain-to-loss ratio with an 8% stop |
| 8-week rule trigger | +20% within 15 sessions | When to hold longer | Rare: about 4–12% of breakouts |
| 8-week hold | 40 sessions | Minimum hold for fast movers | Measured from the breakout day |
| Risk per trade | 0.5–1% of capital | Position size | Sets size together with the stop |

## 5. Variations

- **O'Neil's original**, in *How to Make Money in Stocks*. The rules above follow it. Later editions added a stricter view of the market direction, using follow-through days and distribution days.
- **Gil Morales and Chris Kacher**, former O'Neil portfolio managers, in *Trade Like an O'Neil Disciple*. They add earlier entries: the "pocket pivot" (a volume surge inside the base, before the pivot) and the "buyable gap-up" (a large gap on news, bought with a stop near the gap day's low).
- **Mark Minervini's SEPA** uses the same idea with a stricter trend filter and tighter bases. It is covered in [learn-strat-vcp-sepa](learn-strat-vcp-sepa.md).
- **Nicolas Darvas** bought new highs out of tight boxes a decade before O'Neil. His box is close to O'Neil's flat base. See [learn-strat-darvas](learn-strat-darvas.md).
- **Flags and high tight flags** are the fastest bases. O'Neil lists the high tight flag as a separate, rare pattern. See [learn-strat-flags](learn-strat-flags.md).

## 6. Worked examples

Prices below are adjusted for later splits and bonus issues, so they differ from what was on screen at the time.

### NVIDIA, January 2024 — a cup with handle and the 8-week rule

```series
title: NVIDIA — cup with handle, breakout January 2024
from: 2023-07-01
to: 2024-04-30
tf: D
line: us:NVDA | NVIDIA (split-adjusted) | log
line: us:NVDA@sma50 | 50-day average
line: us:NVDA@vol | Volume | pane2 bars
mark: 2023-08-24 | left side high 50.27
mark: 2023-10-31 | cup low 39.23
mark: 2023-12-04 | handle low 45.01
mark: 2024-01-08 | breakout, 1.58× volume
mark: 2024-03-06 | 8 weeks later
caption: The cup was 22% deep and the handle 11%. The pivot was the handle high, 50.55.
```

- **Filters.** Quarterly EPS, reported in November 2023, was up 1,274% on a year earlier. Revenue was up 205.5%. The S&P 500 was above its 50-day average.
- **Setup.** The left side peaked at 50.27 on 24 August 2023. The cup bottomed at 39.23 on 31 October, 22% down. The right side reached 50.55 on 20 November. The handle dipped to 45.01 on 4 December, 11% deep, in the cup's upper half.
- **Entry.** On 8 January 2024 the close was 52.25, 3.4% above the pivot. Volume was 1.58 times average. Entry 52.25; stop 8% lower at 48.07.
- **What happened.** The price touched +20% (62.70) on 24 January, 11 sessions after the breakout. The 8-week rule applied: hold until about 6 March.
- **Exit.** Forty sessions after the breakout, on 6 March 2024, the close was 88.70. That is +69.8%. Selling at the 20% target would have given up most of that move.

### CDSL, October 2023 — a flat base in a shaky market

This is the chart in section 1.

- **Filters.** Quarterly EPS, reported in late October, was up 35.5%. The C letter passes.
- **Setup.** A flat base from the 11 September high of ₹715 to the 26 October low of ₹631. That is 12% deep and about seven weeks long, after a rise of more than 30%.
- **The M letter.** On 31 October the Nifty 500 closed at 16,801, below its 50-day average of 17,186. A strict M filter says wait. The index closed back above its 50-day on 8 November.
- **Entry.** The breakout close on 31 October was ₹728.08, 1.8% above the pivot, on 5.8 times average volume. The stop sat 8% lower, at ₹669.80.
- **What happened.** The stock touched +20% on 10 November, eight sessions later. Under the 8-week rule, hold to 29 December.
- **Exit.** The close on 29 December was ₹912.20, +25.3%. A strict M filter would have skipped this trade, or bought it a week later at a higher price.

### Bajaj Finance, January 2020 — a good base, then the market broke

```series
title: Bajaj Finance — breakout in January 2020, stopped out in March
from: 2019-09-01
to: 2020-04-30
tf: D
line: india:BAJFINANCE.NS | Bajaj Finance (adjusted) | log
line: india:BAJFINANCE.NS@sma50 | 50-day average
line: india:BAJFINANCE.NS@vol | Volume | pane2 bars
mark: 2020-01-29 | breakout, 4.2× volume
mark: 2020-02-20 | peak, +11.4%
mark: 2020-03-06 | 8% stop hit
caption: A flat base from October 2019 to January 2020, about 10% deep. The breakout worked for three weeks, then the market fell.
```

```series
title: Nifty 500 and its 50-day average, early 2020
from: 2019-10-01
to: 2020-04-30
tf: D
line: india:NIFTY500 | Nifty 500
line: india:NIFTY500@sma50 | 50-day average
mark: 2020-02-24 | index closes below its 50-day
caption: The M letter turned off about two weeks before the stock's stop was hit.
```

- **Setup.** A flat base below the 2 January 2020 high of ₹429.58. Its lowest low, ₹388.02 on 9 December, was 9.7% below that high.
- **Entry.** On 29 January the close was ₹441.90, 2.9% above the pivot, on 4.2 times average volume. The Nifty 500 was above its 50-day average. Stop: ₹406.55.
- **What happened.** The stock rose to ₹492.34 on 20 February, +11.4%. That was short of the 20% target. From 24 February the Nifty 500 closed below its 50-day average every day. The M filter said buy nothing new and tighten stops.
- **Exit.** The 8% stop was hit on 6 March. The loss was about 8%. Sixty sessions after the breakout the stock was 47.5% below the entry. The stop turned a crash into a normal loss.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Buying more than 5% above the pivot | The 8% stop is now close to the pivot; a normal pullback stops you out |
| Buying a breakout on below-average volume | Few buyers behind the move |
| Ignoring the market | Most breakouts fail in a correction, however good the base |
| Treating the 7–8% stop as a guideline | One un-cut loss can erase several winners |
| Selling a fast mover at +20% | The 8-week rule exists because the biggest winners start this way |
| Holding a +15% gain until it becomes a loss | Decide in advance where you lock in part of a gain |
| Buying a late-stage base | The trend is old and the shareholder base is full |
| Using "earnings growth" from a period that had not been reported yet | A look-ahead error in testing; see section 9 |
| Calling any sideways wiggle a base | Use the length and depth limits in section 4 |

## 8. What the evidence says

**What O'Neil's research is.** O'Neil built the method from studying the biggest stock-market winners over many decades. He listed what they had in common just before their largest advances. That is a study of winners only. It shows what winners looked like; it does not show how often stocks with those traits went on to win.

**Published research that supports parts of the method:**

- **Earnings surprises keep moving prices.** Stocks with strong earnings surprises tend to keep drifting in the same direction for weeks (Bernard and Thomas, 1989; Chan, Jegadeesh and Lakonishok, 1996). This supports the C letter. See [learn-fund-earnings](learn-fund-earnings.md).
- **Momentum.** Stocks that rose most over the past 3–12 months tended to keep outperforming over the next few months (Jegadeesh and Titman, 1993). This supports the L letter.
- **Nearness to the 52-week high.** Stocks close to their 52-week high outperformed those far from it (George and Hwang, 2004). This supports the N letter.
- **Unusual volume.** Stocks with unusually high trading volume tended to rise over the following month (Gervais, Kaniel and Mingelgrin, 2001). This is related to, but not the same as, breakout-day volume.

**An event study on stored data.** We measured every breakout that matched a simple, mechanical base rule. It does not test CAN SLIM: there are no earnings, RS or institution filters. It tests only the price-and-volume part.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to July 2026. A breakout is the first close above the highest high of the prior 35 sessions. The base must be 8–35% deep, its high within 15% of the 52-week high, after a 30%+ advance. Liquidity: close ≥ ₹20 / $5 and 50-day average turnover ≥ ₹5 crore / $5m. One breakout per stock per 20 sessions. Outcome: from the breakout close, does the high reach +20% before the low touches −8%, within 60 sessions? The baseline is every 20th session of every liquid stock. Caveats: today's lists only (survivorship bias); fixed exits, no costs; overlapping periods, so the samples are not independent.

| | India breakouts | India baseline | US breakouts | US baseline |
|---|---|---|---|---|
| Events | 16,933 | 93,419 | 52,444 | 341,321 |
| +20% before −8% | 29.5% | 25.6% | 18.0% | 18.6% |
| −8% first | 57.9% | 59.6% | 54.2% | 52.9% |
| Median 60-session return | +2.6% | +1.0% | +1.6% | +1.7% |

In India the breakouts did a little better than a random liquid stock. In the US they did no better. A mechanical breakout, without the other letters, is not an edge by itself.

**Volume on the breakout day:**

| Breakout volume vs 50-day average | India: +20% first | India: −8% first | US: +20% first | US: −8% first |
|---|---|---|---|---|
| Below 1.0× | 26.0% | 54.2% | 16.4% | 52.4% |
| 1.0–1.4× | 27.0% | 55.0% | 17.7% | 54.3% |
| 1.4–2.0× | 28.8% | 55.8% | 19.0% | 55.2% |
| 2.0–3.0× | 28.6% | 58.6% | 20.0% | 56.6% |
| 3.0× and more | 31.9% | 60.3% | 21.8% | 57.0% |

Heavier volume raised the chance of a quick 20% gain. It raised the chance of hitting the stop almost as much. High-volume breakouts are more volatile, in both directions. The volume rule did not make the median outcome better.

**The buy zone:** breakouts that closed more than 10% above the pivot hit the −8% stop most often. That happened to 65.1% of them in India and 62.6% in the US. That fits the 5% rule. The stop is simply closer to a normal pullback.

**Pullbacks below the pivot are normal.** About two in three breakouts (63.1% in India, 66.6% in the US) closed back below the pivot at least once within 10 sessions. A close below the pivot is not, on its own, a failure.

**The 8-week rule.** Breakouts that reached +20% within 15 sessions were rare. They were 12.4% of breakouts in India and 4.3% in the US. Of those, about half closed higher at session 40 than the +20% level. The share was 50.4% in India and 52.7% in the US.

Holding them had a slightly higher average result than selling at 20%, with a wider spread. It is a coin flip on any one trade, with a fatter right tail.

**The M letter.** In our sample, breakouts while the index was below its 200-day average were few (about 10% of Indian events). They did not do worse over 60 sessions. A 200-day filter is too slow to show the effect O'Neil describes; his rule uses faster signals (distribution days and follow-through days). This is unresolved.

**What is unknown.** Nobody has published a clean, out-of-sample test of the full method with point-in-time fundamentals and both markets. The practitioners' records include judgement that rules cannot capture. Treat the full method as plausible, partly supported, and yours to test.

## 9. Building and testing it yourself

**Data you need.**

- Daily open, high, low, close and volume, adjusted for splits and bonus issues.
- Quarterly and annual EPS and sales, each with the date it was announced, not only the quarter it covers.
- Index prices for the M filter, ideally with index volume for distribution days.
- Fund-holding data for the I letter (quarterly shareholding patterns in India).

**Look-ahead traps.**

- A quarter ending in March is announced in April or May. Use the announcement date. Using the quarter-end date buys stocks on news that was not yet public.
- A pivot must be known before the breakout. Compute it from bars that ended the day before.
- A 52-week high that includes today's bar makes every breakout look like a new high.
- If you enter at the close of the breakout day, the volume test uses that day's full volume. That is fine at the close, but not for an intraday buy-stop in a test.

**Survivorship.** A list of today's stocks leaves out companies that were delisted, merged or went bust. Those are disproportionately the failed breakouts. Use historical index members or a list that includes delisted stocks.

**Costs (approximate).**

| Cost | India (delivery trade) | US |
|---|---|---|
| Brokerage | ₹0–20 per order at discount brokers | Usually zero |
| STT | 0.1% on buy and on sell | — |
| Stamp duty | 0.015% on buy | — |
| Exchange and regulatory fees, GST | a few hundredths of a percent | Tiny |
| Slippage on a breakout buy-stop | 0.2–1% in mid caps, more in small caps | 0.05–0.5% |

A round trip in India costs roughly 0.25–0.35% before slippage. Breakout entries slip more than average, because you buy when everyone else does.

**Parameters to test, in this order:** the volume threshold, the buy-zone limit, the stop, and the exit rule. Test one at a time over a grid, and look for a broad flat region of good results, not a single peak. Keep 2–4 years of data out of all tuning and test on it once at the end.

**A good test reports:**

- the number of trades per year, the win rate, and the average win and loss in R (multiples of the initial risk);
- expectancy, the worst losing streak, and drawdown;
- results split by market regime and by year. See [learn-test-backtesting](learn-test-backtesting.md).

```
for each session t:
    if not market_ok(t): continue                    # M: index > 50-day, distribution days <= 4
    for each stock passing C, A, N, S, L, I as of t (announced data only):
        base = find_base(stock, end = t - 1)          # cup-with-handle, double bottom or flat base
        if base is None: continue
        pivot = base.pivot
        if close[t] > pivot and close[t] <= 1.05 * pivot and volume[t] >= 1.4 * avg_volume_50[t - 1]:
            buy at close[t]; stop = 0.92 * entry; start_day = t
manage each open trade daily:
    if low <= stop: sell at stop (or at the open, if it gaps below)
    if high >= 1.20 * entry within 15 sessions of start_day: hold until start_day + 40, stop still active
    elif high >= 1.20 * entry: sell most of the position
    after the hold: sell on a close below the 50-day average on volume >= 1.4x
```

## 10. Checklist

- [ ] The market is in an uptrend: index above its 50-day, at most 4 distribution days in 25 sessions
- [ ] Latest quarter EPS up 25%+ and sales up 20%+, using announced numbers
- [ ] Three years of strong annual EPS growth; return on equity 17%+
- [ ] RS percentile 80+; the stock is in a leading group
- [ ] A first- or second-stage base of the right length and depth
- [ ] Prior advance of at least 30% into the base
- [ ] Pivot marked before the breakout; buy-stop just above it
- [ ] Breakout volume at least 1.4 times the 50-day average
- [ ] Price no more than 5% above the pivot
- [ ] Stop set 7–8% below the entry; size set from the stop
- [ ] Profit target 20–25% written down; 8-week rule date noted if the stock moves fast
- [ ] In India: the stock is not locked at its upper price band; the order is a delivery order

## Further reading

- William J. O'Neil, *How to Make Money in Stocks* (McGraw-Hill; first edition 1988, fourth edition 2009) — the source of CAN SLIM, the bases, the buy zone and the selling rules.
- William J. O'Neil, *24 Essential Lessons for Investment Success* (2000) — a shorter summary.
- Gil Morales and Chris Kacher, *Trade Like an O'Neil Disciple* (Wiley, 2010) — pocket pivots and buyable gap-ups.
- Victor Bernard and Jacob Thomas, "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?", *Journal of Accounting Research* (1989).
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* (1993).
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance* (2004).
- Simon Gervais, Ron Kaniel and Dan Mingelgrin, "The High-Volume Return Premium", *Journal of Finance* (2001).
- [learn-bases](learn-bases.md), [learn-chart-patterns](learn-chart-patterns.md), [learn-health-distribution](learn-health-distribution.md), [learn-risk-stops-exits](learn-risk-stops-exits.md).
