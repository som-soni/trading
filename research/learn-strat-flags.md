# Flags, pennants and high tight flags — buying the pause in a fast move

**In short**

- A flag is a short, shallow pause after a steep rise (the pole). Buy when the price breaks out of the pause; put the stop under the pause's low.
- The usual target is the "measured move": the pole's height added to the breakout price. It is reached in a minority of trades.
- A pennant is a flag whose pause narrows into a small triangle. The rules are the same.
- A high tight flag is the extreme case: a stock that roughly doubles in eight weeks or less, then pauses with a pullback of no more than 20–25%. It is rare, and its results swing widely in both directions.
- Flags need strict filters (pole size, pause depth and length) and small position sizes, because the stop is often 10–20% away.

## 1. The idea

In April 2024, Cochin Shipyard rose from ₹713 to ₹1,378 in about six weeks, a gain of 93%. Then it paused for eleven sessions. The deepest pullback in the pause was 15%, to ₹1,168. On 17 May it closed at ₹1,415, above the top of the pause, on 2.9 times its normal volume. Five sessions later it had added the height of the whole pole.

```series
title: Cochin Shipyard — a high tight flag, 2024
from: 2024-02-15
to: 2024-08-30
tf: D
line: india:COCHINSHIP.NS | Cochin Shipyard (adjusted) | log
line: india:COCHINSHIP.NS@vol | Volume | pane2 bars
band: 2024-05-02 2024-05-16 | the flag
mark: 2024-03-14 | pole low ₹713
mark: 2024-04-30 | pole top ₹1,378
mark: 2024-05-17 | breakout, 2.9× volume
mark: 2024-05-27 | measured move reached
caption: A 93% pole, then a pause of eleven sessions with a 15% pullback. The stop under the flag low was 18% below the entry.
```

That is a **high tight flag**, the rarest kind of flag. An ordinary **flag** has a smaller pole — a rise of 20% or more in a few weeks — and a pause of one to three weeks. The pause usually drifts sideways or a little down, on falling volume.

```pattern
bull-flag
```

Why can it work? A steep rise means buyers are in a hurry, often because of news: results, an order, a policy change. The pause is short-term holders taking profits. If the pause is shallow and quiet, the profit-taking was small compared with the demand.

When the price clears the top of the pause, the buyers who were waiting for a dip give up and buy. Who is on the other side? Traders who sold for a quick gain, and traders who bet that the stock had risen too far, too fast. When it keeps rising, some of the second group must buy back.

## 2. When it works and when it doesn't

Flags work best in **strong markets with clear themes**, when news keeps flowing into a sector and money keeps chasing it. Examples are defence and shipbuilding in India, and AI-related hardware in the US, both in 2023–2024.

They work poorly when:

- **The pole came from one piece of news that is now fully known.** The pause is then the start of a fade, not a rest.
- **The market turns.** Fast movers fall fastest.
- **The stock is tiny and thin.** Poles built on a few large orders reverse just as fast.
- **The pause is deep or long.** More than half the pole given back, or more than three to five weeks, and it is no longer a flag.

**India.** Many fast-moving small and mid caps have daily price bands. A pole made of several upper-circuit days can look strong while very few shares actually traded. Exchanges also place stocks with sharp price moves under extra surveillance (the Additional Surveillance Measure framework). That can mean higher margins, narrower price bands and, in some cases, trade-for-trade settlement. Check before you buy.

Settlement is T+1. Swing trades on the short side need futures or options; this guide covers the long side.

**US.** Flags after earnings gaps are common. Low-priced stocks produce many high tight flags that fail badly.

## 3. The rules

### Universe and filters

- **Price and liquidity.** Close at least ₹100 or $10; 50-day average turnover at least ₹10 crore or $20 million, measured before the pole began.
- **Trend.** The close is above the 200-day average, and the 50-day is above the 200-day.
- **Market (optional).** The index closes above its 50-day average.

### Setup — ordinary flag (and pennant)

- **Pole.** The highest high of the pole is at least 20% above the lowest low of the 15 sessions before it.
- **Flag length.** 5 to 15 sessions after the pole's high, with no higher high in that time.
- **Flag depth.** The flag's lowest low gives back at most 50% of the pole's height (ideally under 38%).
- **Volume.** Average volume in the flag is below the average volume in the pole.
- **Shape.** Sideways or sloping down (flag), or narrowing (pennant). A flag sloping up is weaker.

### Setup — high tight flag

```pattern
high-tight-flag
```

- **Pole.** The highest high is at least 90% above the lowest low of the 40 sessions (eight weeks) before it. O'Neil describes 100–120%.
- **Flag length.** 10 to 25 sessions (two to five weeks).
- **Flag depth.** The lowest low is no more than 25% below the pole's high (Bulkowski uses 20%).

### Entry

- **Standard.** A buy-stop one tick above the pole's high (the top of the flag). On daily data: a close above it.
- **Early.** A buy-stop above the flag's falling upper edge (a line joining the flag's highs). Cheaper, but more false starts.
- **Volume.** Breakout volume at least 1.4 times the 50-day average.
- **Chase limit.** Skip it if the price is more than 5% above the breakout level.

### Initial stop

- One tick below the flag's lowest low.
- For a high tight flag that stop is often 15–25% away. Either size the trade down to match, or use a tighter stop under a tight area that formed late in the flag (the last 3–5 sessions) and accept more stop-outs.
- Skip any trade whose stop is more than 25% below the entry.

### Exits

- **Target (measured move).** Breakout price + pole height (pole high − pole low). Sell half there.
- **Trailing.** Sell the rest on the first close below the 20-day average, or below the 10-day for a faster exit.
- **Failure.** A close back below the flag's low is the stop; do not wait.
- **Time stop.** If the price has not made a new high within 10 sessions of the entry, sell. Flags are meant to resolve quickly.

### Position size

Risk 0.5–1% of capital per trade. Shares = (capital × risk %) ÷ (entry − stop). With a 20% stop and 1% risk, the position is 5% of capital. For high tight flags, consider half the normal risk, because gaps can jump past the stop. See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Once the price reaches entry + 1R, raise the stop to the entry price.
- Do not add on the first pullback; a flag trade is short by nature.
- Note any results date. A flag that breaks out a day before results is a bet on the results.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| Minimum price / turnover | ₹100 / $10; ₹10 crore / $20m | Avoids thin poles | Most important filter for high tight flags |
| Flag: pole gain | ≥ 20% | How steep the rise was | 15–40% |
| Flag: pole window | 15 sessions | How fast it rose | 10–20 |
| Flag: length | 5–15 sessions | How long the pause | Longer pauses are bases, not flags |
| Flag: maximum retracement | 50% of the pole | Depth of the pause | 38–50% |
| HTF: pole gain | ≥ 90% | What counts as "doubling" | 90–120% |
| HTF: pole window | 40 sessions | "In eight weeks or less" | 20–40 |
| HTF: flag length | 10–25 sessions | 2–5 weeks | |
| HTF: maximum pullback | 25% | Tightness | 20–25% |
| Breakout volume | ≥ 1.4 × 50-day avg | Demand | Optional; see section 8 |
| Chase limit | 5% above breakout | Entry quality | |
| Maximum stop | 25% | Largest risk accepted | Size shrinks as the stop widens |
| Target | pole height added | First profit | Reached in a minority of trades |
| Trailing average | 20-day (10-day faster) | Second half exit | |
| Time stop | 10 sessions without a new high | Dead money | 5–15 |
| Risk per trade | 0.5–1% (half for HTF) | Size | |

## 5. Variations

- **Edwards and Magee** (*Technical Analysis of Stock Trends*) describe flags and pennants as pauses that "fly at half-mast": the move after the flag tends to repeat the pole. That is where the measured-move target comes from.
- **Thomas Bulkowski** (*Encyclopedia of Chart Patterns*) catalogues thousands of flags, pennants and high tight flags. His high tight flag requires a rise of at least 90% in under two months and a pullback of no more than 20%. He reports it among the best-performing patterns, and warns that it is rare.
- **William O'Neil** lists the high tight flag as the rarest of his bases: a rise of 100–120% in four to eight weeks, then a three-to-five-week pause of 10–25%. See [CAN SLIM breakouts](learn-strat-canslim-breakout.md).
- **Mark Minervini** trades a similar "power play": a stock up 100% or more in under eight weeks that then pauses tightly. See [SEPA and the VCP](learn-strat-vcp-sepa.md).
- **Short-term traders** trade small flags on 5-minute or hourly charts with the same logic. The costs per trade are then much larger compared with the move.

## 6. Worked examples

Prices are adjusted for later splits and bonus issues.

### Super Micro Computer, May 2023 — a flag that reached its target

```series
title: Super Micro Computer — a six-session flag, May 2023
from: 2023-04-01
to: 2023-08-15
tf: D
line: us:SMCI | Super Micro Computer (split-adjusted) | log
line: us:SMCI@vol | Volume | pane2 bars
band: 2023-05-08 2023-05-15 | the flag
mark: 2023-04-25 | pole low 9.32
mark: 2023-05-03 | +28% on 5.3× volume
mark: 2023-05-16 | breakout
mark: 2023-05-25 | target reached
caption: The pole rose 54% in eight sessions. The flag gave back a quarter of it.
```

- **Pole.** From 9.32 on 25 April 2023 to 14.35 on 5 May: +54% in eight sessions. It included a one-day gain of 28% on 3 May.
- **Flag.** Six sessions, 8–15 May. The low was 13.11 on 10 May: 8.7% below the pole high, a quarter of the pole's height. Volume in the flag was below average.
- **Entry.** The close on 16 May was 14.58, above 14.35, on 1.36 times average volume. Stop under the flag low at 13.04: risk 10.6%.
- **Target.** 14.58 plus the pole's height of 5.03 gives 19.62, a gain of 34.5%. It was reached on 25 May, seven sessions later. Sell half there.
- **Afterwards.** Sixty sessions after the breakout, the close was 25.44, +74.5%. A trailing rule for the second half would have kept part of that.

### BSE Ltd, April 2024 — an extended breakout and a news gap

```series
title: BSE Ltd — a flag breakout that failed, April 2024
from: 2024-03-01
to: 2024-07-31
tf: D
line: india:BSE.NS | BSE Ltd (adjusted) | log
line: india:BSE.NS@vol | Volume | pane2 bars
band: 2024-04-15 2024-04-22 | the flag
mark: 2024-04-23 | breakout day, +12%
mark: 2024-04-29 | gap down on 11× volume
caption: The breakout day itself rose 12%, so the stop under the flag was 16% below the entry.
```

- **Pole.** From ₹647.02 on 19 March 2024 to ₹984.97 on 12 April: +52% in 15 sessions.
- **Flag.** Five sessions, low ₹901.08 on 19 April, 8.5% below the pole high.
- **Entry.** On 23 April the stock rose 12% in one day and closed at ₹1,066.62, on 4.5 times average volume. That close was already 8% above the breakout level — past the 5% chase limit. Under the rules, skip. Had you bought, the stop under the flag low (₹896.58) was 15.9% away.
- **What happened.** On 29 April the stock fell sharply after a regulatory ruling on the exchange's fees, on 11 times average volume. The low of ₹870.70 went through the stop. The loss was 15.9%, and sixty sessions later the stock was 31% below the entry.
- **Lesson.** Two rules would have saved this trade: the chase limit, and the habit of checking for scheduled or pending news.

### Zoom Video, October 2020 — a high tight flag that failed

```series
title: Zoom Video — a high tight flag that failed, late 2020
from: 2020-07-15
to: 2021-01-31
tf: D
line: us:ZM | Zoom Video | log
line: us:ZM@vol | Volume | pane2 bars
band: 2020-09-24 2020-10-14 | the flag
mark: 2020-10-15 | breakout
mark: 2020-11-02 | stop hit
mark: 2020-11-09 | −17% in a day
caption: A 130% pole, a 14% pullback, a breakout — and a stop-out twelve sessions later.
```

- **Pole.** From $230 on 11 August 2020 to $529.74 on 23 September: +130% in 30 sessions, helped by a 41% jump after results on 1 September.
- **Flag.** Fifteen sessions; low $457.69 on 24 September, 13.6% below the pole high.
- **Entry.** On 15 October the close was $536.40, on 1.52 times average volume. Stop under the flag low at $455.40: risk 15.1%. Target: $836.14.
- **What happened.** The stock reached $588.84 on 19 October, then fell. On 2 November the low reached $440 and the stop sold at $455.40: −15.1%. On 9 November, the day the first COVID-19 vaccine results were announced, the stock fell another 17%.
- **Lesson.** High tight flags in stocks whose story depends on one event are fragile. A 15% stop at normal size would have cost two or three times a normal loss.

The Cochin Shipyard chart in section 1 is the successful high tight flag. Its stop was ₹1,162.16, 17.9% below the entry. The measured-move target of ₹2,079.50 (+47%) was reached on 27 May 2024. Sixty sessions after the breakout the close was ₹2,215.50, +56.6%.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Calling any pause after a rise a flag | Without limits on depth and length, every chart has flags |
| Buying a breakout day that is already 8–15% above the level | The stop is now far away; one failure costs a lot |
| Full-size positions with 15–25% stops | A single gap through the stop is a large loss |
| Ignoring the pole's volume and liquidity | Thin poles reverse fast; circuit-limit poles are thinner than they look |
| Holding a flag that goes nowhere | Flags should work within days; dead flags often become failures |
| Expecting the measured move every time | It is reached in a minority of trades; plan the exit for the rest |
| Ignoring results and news dates | Flags often sit right before a known event |
| Buying high tight flags in a falling market | Fast stocks fall fastest |

## 8. What the evidence says

**Published work.** Flags and pennants come from the chart-reading tradition (Edwards and Magee). Thomas Bulkowski's catalogue is the largest public collection of pattern statistics; it rates the high tight flag among the best performers and stresses that it is rare. Academic tests of chart patterns find that some carry a little information about future returns, but much less than practitioners claim (Lo, Mamaysky and Wang, 2000). Short-term momentum research is also relevant: stocks with strong recent gains tend to keep outperforming over the following months (Jegadeesh and Titman, 1993).

**An event study on stored data.**

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to July 2026. Flag: a close above a high set 5–15 sessions earlier (and not exceeded since); that high is at least 20% above the lowest low of the 15 sessions before it; the flag gives back at most half the pole. High tight flag: a close above a high set 10–25 sessions earlier; that high is at least 90% above the lowest low of the 40 sessions before it; the flag's low is within 25% of the high. One event per stock per 20 sessions. Entry at the breakout close; stop just below the flag low; target = entry + pole height; 60-session window. Liquidity at the breakout: close ≥ ₹20 / $5, 50-day average turnover ≥ ₹5 crore / $5m. Baseline: every 20th session of every liquid stock. Caveats: today's lists only (survivorship bias), no costs, gaps filled at the stop level.

| | India flags | US flags | India HTF | US HTF |
|---|---|---|---|---|
| Events | 3,922 | 9,464 | 272 | 641 |
| Median pole gain | 30% | 28% | 108% | 111% |
| Median flag pullback | 8.5% | 8.0% | 17.1% | 18.6% |
| Median stop distance | 10.9% | 10.0% | 19.4% | 21.5% |
| Median target distance | 22.4% | 21.7% | 50.7% | 51.4% |
| Target before stop | 30.5% | 25.9% | 23.5% | 20.0% |
| Stop first | 52.5% | 56.7% | 30.9% | 44.5% |
| Median 60-session return | +1.9% | +1.7% | +0.9% | +5.0% |

**How wide the outcomes are** (returns 60 sessions after the breakout):

| | India HTF | India baseline | US HTF | US baseline |
|---|---|---|---|---|
| Spread (standard deviation) | 41.0% | 22.4% | 41.6% | 24.8% |
| Share down more than 20% | 16.2% | 9.4% | 23.2% | 10.0% |
| Share up more than 50% | 13.6% | 3.1% | 10.1% | 2.0% |
| Average return | +11.3% | +3.6% | +7.5% | +2.3% |

What this shows:

- **Ordinary flags.** The target is about twice as far as the stop, and is reached first in about a quarter to a third of cases. Before costs that is roughly break-even in the US and slightly positive in India. The pattern alone is a thin edge at best.
- **High tight flags are rare.** We found 272 in India (in 211 stocks) and 641 in the US (in 496 stocks) over more than 16 years. That is roughly one per 7,000 liquid stock-days in India and one per 11,000 in the US.
- **They cluster.** 2020 and 2021 alone produced about a third of the Indian cases and about two-fifths of the US cases. They appear when speculation runs high.
- **They are volatile in both directions.** The spread of 60-session returns is nearly double that of an ordinary stock. Gains above 50% are four to five times as common; losses beyond 20% about twice as common. The average is high because of the big winners; the median is ordinary.

**What is unknown.** Whether a stricter high tight flag (higher liquidity, a tighter flag, a good market) keeps the right tail while cutting the left is not settled. With a few hundred cases, any such filter is easy to over-fit.

## 9. Building and testing it yourself

**Data.** Adjusted daily OHLCV. Results dates and corporate events. For India, price-band and surveillance-list history if you can get it.

**Look-ahead traps.**

- The pole's high is only known to be the high once the flag has formed. Fix the pole and the flag from bars before the breakout day.
- The breakout bar must not change the flag's low or the pole's high.
- Split and bonus adjustments matter: an unadjusted 1:1 bonus looks like a 50% fall.
- A day whose range covers both stop and target cannot be ordered from daily data. Assume the stop came first.

**Survivorship.** High tight flags are common in stocks that later collapsed or were delisted. A test on today's stock list will flatter them more than most patterns.

**Costs and fills.** In India, a delivery round trip costs about 0.25–0.35%. That covers STT of 0.1% each side, stamp duty of 0.015% on the buy, exchange fees, GST and depository charges. Slippage on fast breakouts is larger than usual: test 0.3–1% in mid caps, more in small caps. Upper-circuit days cannot be bought; lower-circuit days cannot be sold. Model both.

**What to test.**

- The pole size and window, and the flag's depth and length.
- The entry (close above the high, or a buy-stop).
- The stop (flag low or a late tight low).
- The exit (target, trailing average, time stop).

Report results in R, with the full distribution. Because high tight flags are few, report the number of trades and use the median as well as the mean. Hold out recent years. See [Backtesting honestly](learn-test-backtesting.md).

```
each session t, each liquid stock:
    p = index of the highest high in [t - K_max - 1, t - 1]        # K_max = 15 (flag) or 25 (HTF)
    k = t - 1 - p                                                  # flag length so far
    if k < K_min or close[t] <= high[p]: continue
    pole_low = min(low[p - W .. p])                                # W = 15 (flag) or 40 (HTF)
    flag_low = min(low[p + 1 .. t - 1])
    if high[p] / pole_low < G: continue                            # G = 1.20 or 1.90
    if flag: require (high[p] - flag_low) <= 0.5 * (high[p] - pole_low)
    if HTF:  require flag_low >= 0.75 * high[p]
    if close[t] > 1.05 * high[p]: continue                         # chase limit
    entry = close[t]; stop = flag_low - tick; target = entry + (high[p] - pole_low)
    size = capital * risk_pct / (entry - stop)
manage: stop first; sell half at target; rest on a close below the 20-day; time stop at 10 sessions
```

## 10. Checklist

- [ ] Pole: 20%+ in 15 sessions (flag) or 90%+ in 40 sessions (high tight flag)
- [ ] Pause: 5–15 sessions and at most half the pole (flag); 10–25 sessions and at most 25% (HTF)
- [ ] Volume lighter in the pause than in the pole
- [ ] Liquid before the pole began; not on a surveillance list; not locked at a price band
- [ ] Breakout within 5% of the level, ideally on 1.4× volume or more
- [ ] Stop under the flag low; skip if more than 25% away
- [ ] Size from the stop; half-size for high tight flags
- [ ] Target and trailing exit written down; time stop noted
- [ ] No results or major news due during the expected holding period, unless you accept that risk

## Further reading

- Robert Edwards and John Magee, *Technical Analysis of Stock Trends* (first edition 1948) — flags, pennants and the "half-mast" idea.
- Thomas Bulkowski, *Encyclopedia of Chart Patterns* (Wiley) — statistics on flags, pennants and high tight flags.
- William J. O'Neil, *How to Make Money in Stocks* (McGraw-Hill) — the high tight flag as a base.
- Mark Minervini, *Think & Trade Like a Champion* (2017) — the power play.
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
- Narasimhan Jegadeesh and Sheridan Titman, "Returns to Buying Winners and Selling Losers", *Journal of Finance* (1993).
- [Chart patterns](learn-chart-patterns.md), [Volume](learn-price-volume.md), [Stops and exits](learn-risk-stops-exits.md).
