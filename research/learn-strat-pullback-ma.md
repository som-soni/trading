# Pullback to a moving average — buying a dip inside an uptrend

**In short**
- In a stock that is already rising, wait for a short dip back to a moving average, then buy when the rise resumes.
- The stop goes just under the low of the dip, so the risk is small and clearly defined.
- A "healthy" dip is shallow, on lighter volume, and holds the average; a dip that breaks the 50-day average is not this trade.
- On its own, touching the average gives almost no edge in large samples. The edge comes from what you add: stock selection, a market filter, and patient trade management.
- Test it on your own data before you trust it, including costs and gaps.

## 1. The idea

Start with a real case. In late December 2023, Nvidia had been rising for weeks. On 2 January 2024 it dipped to its 21-day exponential average (EMA) and closed just under it. Two more quiet sessions followed. On 5 January it traded above the high of the day before, and the rise resumed.

```series
title: Nvidia, a pullback to the 21-day EMA, January 2024 (split-adjusted)
from: 2023-11-01
to: 2024-02-15
line: us:NVDA | Nvidia | log
line: us:NVDA@ema21 | 21-day EMA
line: us:NVDA@sma50 | 50-day average
mark: 2024-01-02 | Dips to the 21-day EMA
mark: 2024-01-05 | Trades above the prior day's high
caption: The dip lasted three sessions and held well above the 50-day average. The rise resumed on 5 January, and the stock rose about 12% from the entry over the next week.
```

That is the whole trade. A stock is in an uptrend. It pauses and drifts back to a moving average that has acted as a floor. You buy when it starts to rise again, and you place the stop under the low of the dip.

Why can it work? In an uptrend, many buyers missed the first move and want in at a better price. A moving average is a level many of them watch. When price comes back to it, those buyers step in.

Meanwhile the sellers in a healthy dip are mostly short-term holders taking profits, not owners who have changed their minds. Once their selling is done, the larger buyers are still there.

Who is on the other side? On the way down, it is the short-term trader who takes profit or panics at a red day. At your entry, it is anyone selling into the first bounce. You are betting that the uptrend's buyers are stronger than both.

The appeal is the risk. A breakout buyer may have to risk 7–8% to a stop under the base. A pullback buyer often risks 2–4%, because the low of the dip is close. A small risk means a larger position for the same rupee or dollar loss. It also means the stop is hit more often, as section 8 shows.

## 2. When it works and when it doesn't

**It works in a steady uptrend.** The best conditions are a market index above its own 50-day average and a stock that is a leader in a strong group. Then dips are bought quickly. See [Trend health](learn-health-trend.md) and [Relative strength](learn-price-rs.md).

**It fails when the market turns.** At a market top, dips to the average stop being bought. The first sign is often a pullback that looks healthy but never resumes. Bharti Airtel in October 2024 is a clean example (section 6).

**It fails in sideways stocks.** If the 50-day average is flat, the stock is not trending. Price crosses the average back and forth, and every "touch" looks like a setup.

**Fast averages suit fast stocks.** A strong growth stock often pulls back only to its 10-day or 21-day average. A slower, larger stock may pull back to its 50-day. Using the 50-day on a fast stock means you rarely get a signal. Using the 10-day on a slow stock means many false ones.

**India and the US differ in a few ways:**

| | US | India (NSE) |
|---|---|---|
| Overnight gaps | Common around results | Common, also on global cues and policy news |
| Price limits | None for most stocks | Many stocks have 5%, 10% or 20% daily bands (circuit limits) |
| Settlement | T+1 | T+1 |
| Stop orders across days | Good-till-cancelled stops at most brokers | Many brokers offer GTT (good-till-triggered) orders |
| Costs per round trip | Spread and slippage; commissions near zero | About 0.25–0.35% before slippage (STT, stamp duty, charges) |
| Shorting the mirror trade | Possible in cash | Only via futures and options |

In India, avoid stocks in a 5% or 10% band for this trade. A stop below the band limit may not fill until the next day.

## 3. The rules

Each rule below is a condition you can test on daily data. Names in backticks are parameters listed in section 4.

### Universe and filters

- Price at least `min price` (for example ₹50 or $10).
- Average daily traded value over 50 sessions at least `min liquidity` (for example ₹10 crore or $20 million).
- The stock's 6-month return ranks in the top `RS rank` of the universe. This keeps you in leaders.
- No results announcement within the next `earnings gap` sessions.
- The market index closes above its 50-day average.

### Setup

All of these on the setup day:

1. **Uptrend.** The close is above the 50-day average. The 50-day average is above the 200-day average. Both averages are higher than they were 20 sessions ago.
2. **A prior advance.** The stock made a 20-day closing high within the last `advance lookback` sessions.
3. **First touch.** The previous `run length` closes were all above the `fast average`.
4. **The touch.** Today's low is at or below the `fast average` × (1 + `touch tolerance`).
5. **Holds the trend.** Today's close is at or above the 50-day average.

Optional "healthy pullback" checks, each worth testing separately:

- **Volume dries up.** The average volume over the last 5 sessions is below `dry-up ratio` × the 50-day average volume.
- **Momentum resets.** RSI(14) is between `RSI low` and `RSI high`. It has cooled from overbought but is not weak.
- **Shallow.** The close is no more than `max depth` below the 20-day high.

The bar that touched the average is the **setup bar**.

### Entry

- Place a buy-stop order one tick above the high of the setup bar.
- If the next session does not trigger but touches the average again, the newest touching bar becomes the setup bar. Move the buy-stop to its high.
- Cancel after `trigger window` sessions without a trigger, or if any close is below the 50-day average.
- If the stock gaps above the trigger, you are filled at the open. Record that price, not the trigger.

This is the "high of the prior day" entry. It waits for buyers to show up before you commit. A common variant enters on a reversal bar: a session that dips into the average and closes in the top third of its range. See [Candlestick patterns](learn-candlestick-patterns.md).

### Initial stop

- The pullback low is the lowest low from `pullback lookback` sessions before the setup bar to the day before entry.
- Initial stop = pullback low − `stop buffer` × ATR(14).
- If the entry-to-stop distance is more than `max risk` of the entry price, skip the trade. The dip was too deep for this setup.

### Exits

- **Target.** Sell half at `target R`. **1R** is the distance from entry to the initial stop.
- **Trail.** For the rest, exit on the first close below the `fast average` after the trade has reached +1R.
- **Time stop.** If the trade has not reached +1R within `time stop` sessions, exit at the close.
- **Invalidation.** Exit on any close below the 50-day average, even if the stop is not hit.
- **Stop.** Exit if the stop is hit. If the stock opens below the stop, exit at the open.

### Position size

- Shares = (account × `risk %`) ÷ (entry − stop).
- Cap any one position at `max position` of the account.
- India: round down to whole shares. In F&O stocks, the futures lot size is usually far too large for this.
- See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- Do not add to a position that is below entry.
- Before results, either exit or cut to a size whose gap loss you can accept.
- If the market index closes below its 50-day average, tighten the trail to the prior day's low.
- Write down why you exited. Pullback traders learn most from the trades that never resumed.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| `fast average` | 10-day or 21-day EMA; 20-day SMA | Which dip counts | Faster for fast stocks; test both |
| Slow average | 50-day SMA (also 200-day for the trend) | Trend filter and invalidation | Standard values; rarely worth tuning |
| `run length` | 3–10 closes above the fast average | "First touch" rule | Longer means fewer, cleaner setups |
| `advance lookback` | 5–15 sessions | Requires a recent new high | Removes stale trends |
| `touch tolerance` | 0–1% | How close counts as a touch | Above 1% catches dips that never reach the average |
| `dry-up ratio` | 0.7–1.0 | Volume quality check | No consistent effect in the study in section 8 |
| `RSI low` / `RSI high` | 40 / 60 | Momentum reset check | No consistent effect in section 8 |
| `max depth` | 8–15% below the 20-day high, or 3 ATR | Rejects deep dips | Deep dips are a different trade |
| `trigger window` | 2–5 sessions | How long you wait for the turn | Longer adds trades that are already failing |
| `pullback lookback` | 5 sessions | Where the pullback low is measured | Stable |
| `stop buffer` | 0–1 × ATR(14) | Room under the low | The most sensitive parameter; see section 8 |
| `max risk` | 5–8% of entry | Skips wide stops | Lower in large caps |
| `target R` | 2–3R for the first half | Profit-taking | Interacts with the stop buffer |
| `time stop` | 5–15 sessions | Exits dead trades | Shorter for fast averages |
| `earnings gap` | 5–15 sessions | Avoids results inside the trade | Results gaps dwarf the stop |
| `RS rank` | Top 20–30% by 6-month return | Leader filter | Common in practice; test it |
| `min price` / `min liquidity` | ₹50 / ₹10 crore; $10 / $20 million | Tradability | Raise for larger accounts |
| `risk %` | 0.5–1% of the account | Loss if stopped | Keep fixed while testing |
| `max position` | 15–25% of the account | Concentration | Small stops make positions large |

## 5. Variations

**Linda Raschke's "Holy Grail".** In *Street Smarts* (1995), Laurence Connors and Linda Raschke describe buying the first pullback to the 20-period EMA after the ADX rises above 30. ADX is used as a measure of trend strength. The entry is a trade above the prior bar's high, the same trigger as here.

**Alexander Elder's value zone.** In *Come Into My Trading Room* (2002), Elder describes a "value zone" between a fast and a slow EMA of a rising trend. He buys pullbacks into that zone rather than to one line. His earlier Triple Screen method uses a weekly trend filter and a daily oscillator for the timing.

**William O'Neil's 10-week line.** In *How to Make Money in Stocks*, O'Neil treats the first and second pullbacks to the 10-week (about 50-day) average after a breakout as possible places to add. He warns that later touches are weaker, as a trend matures.

**Different averages.** The 10-day EMA suits stocks in a steep advance. The 21-day EMA is the common middle ground. The 50-day SMA suits large, slower stocks and is watched by many institutions. Some traders require a touch of two averages at once.

## 6. Worked examples

All prices are split-adjusted daily prices. The rules are those of section 3, with a 21-day EMA, a 3-session trigger window and no stop buffer.

### Example 1 — Nvidia, January 2024 (US, a clean resumption)

| Step | Date | Detail |
|---|---|---|
| Setup bar | 2 Jan 2024 | Low 47.60 under the 21-day EMA (48.44); close 48.17, well above the 50-day (46.81) |
| New setup bars | 3–4 Jan | Both dipped to the EMA again; the trigger moved down to 48.50 |
| Entry | 5 Jan | Traded above 48.50; filled near 48.50 |
| Stop | | Pullback low 47.32 (3 Jan); risk about 1.18, or 2.4% |
| Target 2R | 8 Jan | 2R = about 50.86; the high that day was 52.28 |

Volume during the dip stayed below its 50-day average. RSI fell to about 47. The S&P 500 was above its 50-day average. Every filter was green, and the trade paid quickly. This is the textbook case, and it is not the typical one.

### Example 2 — Bharat Electronics, November 2023 (India, two touches and a slow trigger)

```series
title: Bharat Electronics, a pullback to the 21-day EMA, November 2023
from: 2023-09-15
to: 2024-01-15
line: india:BEL.NS | Bharat Electronics | log
line: india:BEL.NS@ema21 | 21-day EMA
line: india:BEL.NS@vol | Volume | pane2 bars
mark: 2023-11-23 | Touches the EMA
mark: 2023-11-29 | Trigger
caption: The stock touched its 21-day EMA on 23 and 24 November and triggered on 29 November. Volume expanded as it broke higher in early December.
```

| Step | Date | Detail |
|---|---|---|
| Setup bar | 23 Nov 2023 | Low 139.10 under the EMA (139.64); close 139.35, above the 50-day (137.56) |
| New setup bar | 24 Nov | Low 137.35 touched again; trigger moved to its high, 142.15 |
| Entry | 29 Nov | Traded above 142.15, the third session after the first touch |
| Stop | | Pullback low 137.35; risk 4.80, or 3.4% |
| Target 2R | 4 Dec | 2R = 151.75; the high that day was 157.50 |

Volume during the dip was light, 0.56–0.76 times average, until the touch days. The Nifty 50 was above its 50-day average. The stock rose about 28% in the 20 sessions after entry. Selling half at 2R and trailing the rest under the EMA kept most of that move.

### Example 3 — Meta, April 2024 (US, a failure two filters would have avoided)

```series
title: Meta, a pullback that failed, April 2024
from: 2024-02-15
to: 2024-05-31
line: us:META | Meta | log
line: us:META@ema21 | 21-day EMA
line: us:META@sma50 | 50-day average
mark: 2024-04-18 | Entry
mark: 2024-04-19 | Stopped
mark: 2024-04-25 | Results gap
caption: The trade triggered on 18 April and was stopped the next day. A week later, the results gap took the stock far below the stop.
```

| Step | Date | Detail |
|---|---|---|
| Setup bar | 15 Apr 2024 | Low 497.28 under the EMA (505.26); close 500.23, above the 50-day |
| New setup bars | 16–17 Apr | Touched again; trigger moved down to 503.16 |
| Entry | 18 Apr | Traded above 503.16 |
| Stop | | Pullback low 487.14; risk 16.02, or 3.2% |
| Exit | 19 Apr | Low 475.73; stopped at about 487.14, −1R |

Two rules would have skipped this trade. The S&P 500 closed below its 50-day average on 17 April. And Meta reported results on 24 April, inside any sensible `earnings gap`. On 25 April the stock opened about 15% below the prior close. A trader who had ignored the stop would have lost about 5R overnight.

### Example 4 — Bharti Airtel, October 2024 (India, a "healthy" pullback in a market turning down)

| Step | Date | Detail |
|---|---|---|
| Setup bar | 21 Oct 2024 | Low 1662.00 under the EMA (1684.61); close 1692.55 |
| Quality checks | | Volume 0.48–0.66 times average; RSI about 54; a shallow dip |
| Entry | 22 Oct | Traded above 1708.95 |
| Stop | | Pullback low 1662.00; risk 46.95, or 2.7% |
| Exit | 24 Oct | Low 1657.40; stopped at about 1662.00, −1R |

By every "healthy pullback" test, this was a good setup. The market was the problem. The Nifty 500 had peaked in late September and closed below its 50-day average on 21 October. The market filter alone would have skipped the trade. Over the next two weeks the stock fell below its 50-day average, and the pullback became a downtrend.

## 7. Common mistakes

- **Buying the touch, not the turn.** A stock that touches its average can keep falling. Wait for the trigger.
- **Moving the stop lower "to give it room".** If the pullback low breaks, the setup has failed. Decide the buffer before entry.
- **Treating the fourth or fifth touch like the first.** Later touches in an old trend fail more often, as O'Neil warned.
- **Trading pullbacks in a falling market.** The market filter is the cheapest rule in this guide and among the most useful.
- **Holding through results.** One results gap can erase many small wins.
- **Confusing a pullback with a breakdown.** A close below the 50-day average on heavy volume is not a dip to buy.
- **Using one average for every stock.** Match the average to how the stock has actually behaved in its trend.

## 8. What the evidence says

**Published research on moving averages is mixed.** Brock, Lakonishok and LeBaron (1992) found that simple moving-average rules had predictive power on the Dow Jones index from 1897 to 1986. Sullivan, Timmermann and White (1999) showed that once you account for how many rules were tried, the result weakens a lot, and it largely fails after 1986. Han, Yang and Zhou (2013) found that moving-average timing worked better in more volatile portfolios. None of these papers tests the pullback-entry rule itself.

**Our event study: does the touch itself help?** We took liquid US and Indian stocks from 2012 to mid-2026. A "touch" is the setup of section 3, without the optional checks. We compared the return over the next 20 sessions with the return from a sample of all uptrend days, using the same uptrend rule.

| Sample | Events | Mean 20-session return | Median | Share higher |
|---|---|---|---|---|
| US, all uptrend days (baseline) | 251,685 | +0.64% | +0.67% | 54.0% |
| US, first touch of the 21-day EMA | 116,525 | +0.72% | +0.75% | 54.2% |
| US, first touch of the 50-day | 72,314 | +0.88% | +0.88% | 54.8% |
| India, all uptrend days (baseline) | 87,377 | +1.84% | +0.67% | 53.2% |
| India, first touch of the 21-day EMA | 41,165 | +1.79% | +0.74% | 53.4% |
| India, first touch of the 50-day | 25,404 | +1.57% | +0.52% | 52.4% |

The touch makes almost no difference. A stock touching its average in an uptrend behaves much like any stock in an uptrend. The trend is doing the work, not the touch.

**Do the "healthy pullback" signs help?** We split the touches by volume: was the 5-day average volume below the 50-day average or not?

| Sample | Volume dried up | Volume not dried up |
|---|---|---|
| US, 21-day EMA touches | +0.71% | +0.73% |
| US, 50-day touches | +0.98% | +0.72% |
| India, 21-day EMA touches | +1.85% | +1.64% |
| India, 50-day touches | +1.55% | +1.67% |

The differences are small and point in both directions. RSI at the touch showed no consistent pattern either. These signs are widely taught. On daily data in large samples, they do not separate good pullbacks from bad ones.

**How often does the stop come first?** For each touch that triggered, we asked which came first within 30 sessions: the stop at the pullback low, or a gain of 2R. We ran the same test from random uptrend days, with a stop under the prior 5-day low.

| Entry | Stop first | 2R first | Neither | Median risk |
|---|---|---|---|---|
| US, 21-day EMA trigger | 65.0% | 31.5% | 3.6% | 2.4% |
| US, random uptrend day | 59.9% | 28.4% | 11.7% | 2.8% |
| India, 21-day EMA trigger | 64.0% | 31.7% | 4.3% | 3.7% |
| India, random uptrend day | 58.7% | 29.6% | 11.7% | 4.1% |

With a 2R target you break even if you win one trade in three. Among trades that reached the stop or the target, the trigger entries won about 33% of the time. Random uptrend entries did about the same. Adding a buffer of 1 ATR under the low cut the stop-first share by 12–15 points. But the 2R share fell too.

What this means: the entry rule alone is close to a coin toss at these odds, before costs. Any edge must come from the filters you add and how you manage the winners. Examples 3 and 4 show that the market filter and the results calendar matter. Test them yourself.

Method notes: daily prices from 2012 to June 2026. US stocks priced at $10 or more, with at least $20 million average daily traded value. Indian stocks priced at ₹50 or more, with at least ₹10 crore.

The universe is today's list of stocks, so delisted stocks are missing. That survivorship lifts all the returns, but it affects the touches and the baseline alike. Intraday order is unknown: if a session hit both the stop and the target, we counted the stop.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume, adjusted for splits and bonus issues. You need delisted stocks too, or your results will be too good. You also need results dates, and an index series for the market filter.

**Look-ahead traps:**
- The setup uses the day's close. The earliest entry is the next session's trigger, never the setup day's close.
- Averages must use only data up to that day.
- Results dates must be the dates known at the time. Some data sources fill in dates after the fact.
- A universe chosen by today's leaders is survivorship bias. Pick the universe as it was on each date.

**Costs (approximate).** US: assume a spread and slippage cost of 0.05–0.10% each way for liquid stocks. India, delivery trades: brokerage of zero to ₹20 per order, STT of 0.1% on each side, stamp duty of 0.015% on buys, plus exchange charges and GST. That is about 0.25–0.35% per round trip before slippage. On a 2.5% risk, that is a tenth of 1R lost on every trade.

**Gaps.** Model a stop hit on a gap at the open price, not at the stop. In India this matters more, because many news events land outside market hours.

**What to test, one at a time:**
- The fast average: 10-day, 21-day EMA and the 50-day.
- The stop buffer: 0, 0.5 and 1 ATR.
- The market filter on and off.
- The results filter on and off.
- The leader filter on and off.

**Avoid over-fitting.** Fix the trend rule and the trigger first. Change one parameter at a time and look for a broad plateau of good values, not a single best one. Keep the last few years out of the test until the very end.

```
for each stock s, each day t:
    trend   = close > sma50 > sma200 and sma50 > sma50[t-20] and sma200 > sma200[t-20]
    first   = all(close[t-k] > ema21[t-k] for k in 1..run_length)
    touch   = low[t] <= ema21[t] * (1 + touch_tolerance) and close[t] >= sma50[t]
    if not (trend and first and touch and filters_pass(s, t)): continue
    trigger = high[t]
    for k in 1..trigger_window:
        if close[t+k-1] < sma50[t+k-1]: cancel
        if high[t+k] > trigger:
            entry = max(open[t+k], trigger)
            stop  = min(low[t-pullback_lookback .. t+k-1]) - stop_buffer * atr14[t]
            manage(entry, stop)       # target, trail, time stop, invalidation, gaps
            break
        if low[t+k] <= ema21[t+k]: trigger = min(trigger, high[t+k])
```

**A good test reports:**

- the number of trades per year;
- the win rate and the average win and loss in R;
- expectancy per trade after costs;
- the worst run of losses;
- results split by year and by market regime.

Compare with a simple baseline, such as buying random uptrend days with the same exits. If your rules cannot beat that baseline, the pullback is not adding anything. See [Expectancy](learn-risk-expectancy.md) and [Backtesting](learn-test-backtesting.md).

## 10. Checklist

- [ ] The market index is above its 50-day average.
- [ ] The stock is a leader: strong 6-month return, a strong group.
- [ ] Close above the 50-day, 50-day above the 200-day, both rising.
- [ ] A new 20-day high in the last few sessions; this is the first touch of the average.
- [ ] The dip held: the close is above the 50-day average.
- [ ] No results inside my holding period.
- [ ] Buy-stop above the setup bar's high, with a cancel date.
- [ ] Stop under the pullback low, with the buffer decided now.
- [ ] Position size from my risk %, capped.
- [ ] Target, trail and time stop written down.

## Further reading

- William Brock, Josef Lakonishok and Blake LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance*, 1992.
- Ryan Sullivan, Allan Timmermann and Halbert White, "Data-Snooping, Technical Trading Rule Performance, and the Bootstrap", *Journal of Finance*, 1999.
- Yufeng Han, Ke Yang and Guofu Zhou, "A New Anomaly: The Cross-Sectional Profitability of Technical Analysis", *Journal of Financial and Quantitative Analysis*, 2013.
- Laurence Connors and Linda Bradford Raschke, *Street Smarts: High Probability Short-Term Trading Strategies*, 1995.
- Alexander Elder, *Come Into My Trading Room*, 2002.
- William O'Neil, *How to Make Money in Stocks*.
- Related guides: [Moving averages and indicators](learn-price-indicators.md), [Oscillators](learn-price-oscillators.md), [Stops and exits](learn-risk-stops-exits.md), [Pullback to support](learn-strat-pullback-support.md), [Retracements](learn-strat-retracements.md).
