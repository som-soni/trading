# Pullback to support — buying the retest of a level

**In short**
- After a stock breaks above a price level, it often comes back to test it. The old ceiling can then act as a floor.
- You buy near that level, called a zone, and place the stop just under it. The risk is small and the reason for the trade is clear.
- Most breakouts that run come back to the level at least once. About two in three of those retests hold, and the rest fail.
- Buying blindly at the level gives no edge in large samples. You need a confirmation rule, a tight stop under the zone, and good stock selection.
- In India, gaps and price bands make the zone wider in practice. Plan for an entry above your trigger and an exit below your stop.

## 1. The idea

Start with a real case. State Bank of India spent the autumn of 2023 under a ceiling near ₹614. On 8 December 2023 it closed above that level, and a week later it touched ₹650.

Then it drifted back. In January 2024 it returned to the old ceiling twice. On 24 January it dipped under ₹614, then closed back above it near the day's high.

```series
title: State Bank of India, a breakout and its retest, Dec 2023 to Feb 2024
from: 2023-10-01
to: 2024-02-29
line: india:SBIN.NS | State Bank of India | log
line: india:SBIN.NS@sma50 | 50-day average
line: india:SBIN.NS@vol | Volume | pane2 bars
mark: 2023-12-08 | Breakout above ₹614
mark: 2024-01-24 | Retest: dips under the level, closes back above
mark: 2024-02-08 | Run to new highs
caption: The old ceiling near ₹614 held as a floor in January. The stock rose to about ₹725 by early February.
```

That is the trade. A level that stopped the price on the way up is broken. When the price comes back to it, you buy, with the stop just under the level. If the old ceiling has become a floor, the risk is small and the next leg up is large.

```pattern
role-reversal
```

Why can it work? This is **role reversal**: broken resistance often becomes support. Three groups act at the level.

Buyers from the breakout defend their entry price. Traders who missed the breakout see a second chance. And the sellers who created the ceiling have sold their shares, so less supply is waiting there. See [Supply and demand](learn-supply-demand.md) for how a zone forms and how to grade one.

Who is on the other side? Mostly short-term holders who bought the breakout and sell when it stalls, and some late sellers who treat the dip as a failed breakout. If the level holds, they sold to you near the low. If it fails, they were right, and your stop takes you out quickly.

The same logic applies to other kinds of support. The top of a prior base, a well-defined **demand zone** (the starting point of a strong rally), or an old swing high can all play the role of the level. This guide uses the breakout level as the main case, because it is the easiest to define and test.

```pattern
demand-zone
```

## 2. When it works and when it doesn't

**It works when the breakout was real.** A breakout on rising volume, from a tight base, in a stock that is a leader, is more likely to hold its level. A breakout that only scraped above the ceiling on light volume often slips back through it. See [Bases](learn-bases.md) and [Price and volume](learn-price-volume.md).

**It works in a rising market.** The same as all long setups: when the index is above its 50-day average, retests hold more often. When the market turns, levels fail together. See [Trend health](learn-health-trend.md).

**It fails when the level is crowded with history.** A level that has been crossed many times is not a clean ceiling. Price will cut through it without reacting.

**It fails on the third and fourth retest.** Each test uses up some of the buyers waiting at the level. The first retest is the trade. Later ones are closer to a coin toss.

**India and the US differ in mechanics:**

| | US | India (NSE) |
|---|---|---|
| Gaps through the zone | Mostly around results | Also on global cues, policy and block deals |
| Price bands | None for most stocks | 5%, 10% or 20% bands on many stocks; avoid 5% and 10% bands here |
| Order types for the stop | Stop or stop-limit, good till cancelled | SL and SL-M orders for the day; GTT orders at many brokers for multi-day stops |
| Costs per round trip | Spread and slippage; commissions near zero | About 0.25–0.35% before slippage |
| Shorting a failed retest | Possible in cash | Only via futures and options |

## 3. The rules

Each rule is a condition you can test on daily data. Names in backticks are parameters listed in section 4.

### Universe and filters

- Price at least `min price` (for example ₹50 or $10), and average daily traded value over 50 sessions at least `min liquidity`.
- The close is above the 200-day average.
- The market index closes above its 50-day average.
- No results announcement within the next `earnings gap` sessions.
- India: not in a 5% or 10% price band.

### Setup

1. **The level.** The level P is the highest high of the `base length` sessions before the breakout. The range of that base, from its low to P, is at most `max base depth`.
2. **The breakout.** A close above P. This is the first breakout in `breakout spacing` sessions.
3. **The run.** After the breakout, the price trades at least `min run` above P before it comes back. Without a run, there is no pullback, only a stall.
4. **No early failure.** No close more than `fail depth` below P before the run.
5. **The zone.** Zone top = P + `zone width` × ATR(14). Zone bottom = P − `zone width` × ATR(14). Use the ATR on the day the price first returns.
6. **The retest.** Within `retest window` sessions of the breakout, the low reaches the zone top or below. This is the first retest.

### Entry

**Confirmed entry (the main rule).**
- Wait for a **reversal bar**: a session whose low is in or below the zone, whose close is at or above P, and whose close is in the top third of its range.
- The reversal bar must come within `confirm window` sessions of the first touch.
- Place a buy-stop one tick above the reversal bar's high, valid for the next session only.
- If the stock gaps above the trigger, you are filled at the open. Record that price.
- Cancel the setup if any close is below the zone bottom.

**Aggressive entry (the variant).**
- Place a limit buy at the zone top once the run is complete. You are filled when the price comes back.
- This gets you in at a better price on every retest that holds. It also gets you in on every retest that fails.

### Initial stop

- Confirmed entry: stop = the lower of the reversal bar's low and the zone bottom, minus `stop buffer` × ATR(14).
- Aggressive entry: stop = zone bottom − `stop buffer` × ATR(14).
- If the risk is more than `max risk` of the entry price, skip the trade or reduce the size.

### Exits

- **Target.** Sell half at `target R`, or at the next resistance above, whichever comes first. **1R** is the distance from entry to the initial stop.
- **Trail.** Trail the rest under the 21-day EMA, or under the most recent higher swing low.
- **Time stop.** If the trade has not reached +1R within `time stop` sessions, exit.
- **Invalidation.** A close below the zone bottom ends the trade, even if the stop is not touched.
- **Gaps.** If the stock opens below the stop, exit at the open.

### Position size

- Shares = (account × `risk %`) ÷ (entry − stop).
- Cap any position at `max position` of the account.
- See [Position sizing](learn-risk-sizing.md).

### Managing the trade

- A retest that holds should leave the zone within a few sessions. A stock that sits in the zone for a week is using up its buyers.
- Before results, exit or cut the size to an amount whose gap you can accept.
- If the stock breaks out to a new high, the next pullback is a [moving-average pullback](learn-strat-pullback-ma.md), not this trade.

## 4. The parameters

| Parameter | Typical value / range | What it controls | Sensitivity / notes |
|---|---|---|---|
| `base length` | 40–65 sessions | Which ceiling counts as the level | Longer bases give stronger levels and fewer trades |
| `max base depth` | 20–35% | Rejects loose, wide ranges | Tighter bases make cleaner levels |
| `breakout spacing` | 20 sessions | One event per breakout | Stable |
| `min run` | 3–8% above P | Proves the breakout moved away | Too small and every stall counts |
| `fail depth` | 2–4% below P | Early failure before any run | |
| `zone width` | 0.25–0.75 × ATR(14) either side of P | How wide the zone is | Wider zones catch more retests and need wider stops |
| `retest window` | 20–40 sessions | How long the level stays relevant | Old levels fade |
| `confirm window` | 5–10 sessions | How long to wait for a reversal bar | Longer adds stale setups |
| `stop buffer` | 0–0.5 × ATR(14) | Room under the zone | The most sensitive choice |
| `max risk` | 5–9% of entry | Skips trades whose stop is too far | Wider for volatile Indian midcaps |
| `target R` | 2–3R | First profit-take | Compare with the next resistance |
| `time stop` | 10–15 sessions | Exits dead trades | |
| `earnings gap` | 5–15 sessions | Avoids results inside the trade | |
| `min price` / `min liquidity` | ₹50 / ₹10 crore; $10 / $20 million | Tradability | Raise for larger accounts |
| `risk %` | 0.5–1% | Loss if stopped | |
| `max position` | 15–25% | Concentration | |

## 5. Variations

**Edwards and Magee.** *Technical Analysis of Stock Trends* (first published 1948) describes the change of roles: a broken resistance level tends to act as support on a later decline, and the reverse. It is the oldest written source for this trade.

**Wyckoff's "back-up".** In the Wyckoff method, after price jumps above a trading range, a "back-up to the edge of the creek" is the test of the broken range top. It is bought if volume shrinks on the way down and grows on the way back up.

**William O'Neil's pullback to the buy point.** In *How to Make Money in Stocks*, O'Neil notes that many good breakouts pull back to near the pivot (the buy point) soon after. He treats a close well below the pivot as a sign to sell. Buying the pullback is a lower-risk second entry for traders who missed the breakout.

**Al Brooks' breakout pullback.** In *Trading Price Action Trends* (2012), Brooks describes the "breakout pullback": the first pullback after a breakout, bought when a bar turns back in the direction of the breakout. It is the same trigger as the reversal bar here, applied on any time frame.

**Supply and demand zone trading.** Some traders draw demand zones at the base a strong rally started from, not at the breakout level. They buy the first return with a limit order and a stop under the zone. That is the aggressive entry, applied to a different level.

**Other levels.** The rules work the same for a prior base top, an old all-time high, or a round number. Many traders give extra weight to a level where two kinds of support overlap, such as a broken high near a rising 50-day average.

## 6. Worked examples

All prices are split-adjusted daily prices. The rules are those of section 3. The zone is ±0.5 ATR around the level, and the stop buffer is 0.25 ATR. The first target is 2R.

### Example 1 — State Bank of India, January 2024 (India; the second touch confirms)

| Step | Date | Detail |
|---|---|---|
| Level P | | 614.00, the 60-session high before the breakout |
| Breakout | 8 Dec 2023 | Close 614.15, volume 1.28 times average |
| Run | 15 Dec | High 650.00, about 6% above P |
| First touch | 10 Jan 2024 | Low 618.20, inside the zone; close in the middle of the range, no reversal bar |
| Undercut | 23 Jan | Low 600.65; close 605.10, below P; no entry |
| Reversal bar | 24 Jan | Low 603.10, close 618.30 (above P, top third of the range) |
| Entry | 25 Jan | Buy-stop above 622.35 filled |
| Stop | | 603.10 − 0.25 × ATR (14.13) = about 599.57; risk 22.78, or 3.7% |
| Target 2R | 8 Feb | 2R = about 667.90; the high that day was 718.90 |

Note what the rules did. The first touch did not produce a reversal bar, so there was no trade. The undercut on 23 January would have stopped an aggressive buyer whose stop sat just under the level. The confirmed entry came only after buyers had pushed the price back above ₹614.

### Example 2 — Uber, May 2023 (US; a slow, quiet retest)

| Step | Date | Detail |
|---|---|---|
| Level P | | 37.58 |
| Breakout | 3 May 2023 | Close 37.84, volume 3.05 times average |
| Run | 18 May | High 39.49, 5% above P |
| Touches | 24–30 May | Three sessions in the zone (37.02–38.14); none closed in the top third |
| Reversal bar | 31 May | Low 37.07, close 37.93, high 38.05 |
| Entry | 1 Jun | Buy-stop above 38.05 filled |
| Stop | | Zone bottom 37.02 − 0.25 × ATR (1.11) = about 36.74; risk 1.31, or 3.4% |
| Target 2R | 5 Jun | 2R = about 40.67; the high that day was 40.79 |

The retest took a week of small, quiet bars. Volume stayed below average. The reversal bar on 31 May dipped to the bottom of the zone and closed near its high. The stock went on to about 45 by mid-July.

### Example 3 — Mahindra & Mahindra, April 2024 (India; a gap over the trigger)

| Step | Date | Detail |
|---|---|---|
| Level P | | 1982.30 |
| Breakout | 3 Apr 2024 | Close 1989.30 |
| Run | 8 Apr | High 2087.00 |
| Reversal bar | 19 Apr | Low 1998.20 (in the zone), close 2082.90, high 2087.00 |
| Entry | 22 Apr | Opened at 2124.55, above the trigger; filled at the open |
| Stop | | Zone bottom 1954.70 − 0.25 × ATR (55.16) = about 1940.90; risk 183.65, or 8.6% |
| Target 2R | 17 May | 2R = about 2491.85; the high that day was 2557.95 |

The gap over the trigger cost about 37 rupees a share. It also widened the risk to 8.6%, close to the `max risk` limit. The size had to be smaller to keep the same rupee risk. The trade worked, helped by results in mid-May. This is common in India: plan for fills above the trigger.

### Example 4 — Titan, October 2024 (India; the failure)

```series
title: Titan, a retest that failed, October 2024
from: 2024-07-15
to: 2024-11-29
line: india:TITAN.NS | Titan | log
line: india:TITAN.NS@sma50 | 50-day average
line: india:NIFTY500 | Nifty 500 | right
mark: 2024-08-26 | Breakout above ₹3,625
mark: 2024-10-03 | Retest
mark: 2024-10-07 | Breaks the zone
caption: Titan came back to its breakout level as the Indian market turned down in October 2024. The level gave way within three sessions.
```

| Step | Date | Detail |
|---|---|---|
| Level P | | 3625.00 |
| Breakout | 26 Aug 2024 | Close 3630.20, volume only 0.72 times average |
| Run | 20 Sep | High 3819.00 |
| Retest | 3 Oct | Low 3650.05, inside the zone (3585.50–3664.50); close in the bottom fifth of the range |
| Aggressive entry | 3 Oct | Limit at 3664.50 filled; stop about 3565.70; risk 98.80, or 2.7% |
| Exit | 7 Oct | Low 3552.30; stopped, −1R |
| Confirmed entry | | Never triggered: no session closed in the top third of its range above P |

Three warnings were visible. The breakout came on below-average volume. The Indian market had peaked in late September and was falling. And the retest bars closed weak, near their lows.

The confirmation rule kept you out; the aggressive limit order did not. Titan fell to about ₹3,400 within two weeks.

## 7. Common mistakes

- **Buying a level the price never left.** Without a run away from the level, there is no retest, only a stall at the ceiling.
- **Drawing the level after the fact.** Fix P from the base before the breakout, not from wherever the price happened to turn.
- **Putting the stop exactly at the level.** Everyone can see it. Stops cluster there and get run, as on SBI on 23 January 2024.
- **Buying the third or fourth retest.** Each test uses up buyers.
- **Ignoring how the breakout happened.** A breakout on light volume often fails its retest.
- **Averaging down through the zone.** A close below the zone bottom means the level has failed.
- **Holding a failed retest because "it is support".** Broken support often becomes resistance. The level now works against you.

## 8. What the evidence says

**Support and resistance are partly about where orders sit.** Osler (2000) tested support and resistance levels published by six firms for currency traders. Intraday exchange-rate trends were interrupted at those levels more often than at arbitrary levels.

Osler (2003) traced this to clusters of stop and take-profit orders near round numbers. Kavajecz and Odders-White (2004) found that support and resistance levels in US stocks line up with peaks in the depth of the limit-order book. So levels are real places where orders wait. That does not mean they always hold.

**Trading-range breakouts had predictive power on old data.** Brock, Lakonishok and LeBaron (1992) found that buying breaks above a recent high on the Dow index outperformed from 1897 to 1986. Sullivan, Timmermann and White (1999) showed this weakens after accounting for data mining. George and Hwang (2004) found that stocks near their 52-week high tend to keep outperforming, which fits the idea that old highs act as anchors.

**Our event study: what happens after a breakout?** We took liquid US and Indian stocks from 2012 to mid-2026. A breakout is a close above the highest high of the prior 60 sessions, above the 200-day average, from a base no deeper than 30%. We followed each for 40 sessions.

| Outcome within 40 sessions | US | India |
|---|---|---|
| Breakouts | 37,547 | 7,603 |
| Failed first: closed 3% below the level before running 5% above it | 39.2% | 32.1% |
| Ran 5% above, then came back within 1% of the level | 32.3% | 47.1% |
| Ran 5% above and never came back | 24.7% | 20.1% |
| Neither | 3.9% | 0.7% |

Of the breakouts that ran, 57% in the US and 70% in India came back to the level within 40 sessions. A retest is common, so waiting for one is a reasonable plan. But a large share of breakouts fail before they ever run.

**Do retests hold?** "Held" means no close more than 3% below the level in the 10 sessions after the touch.

| Retests | US | India |
|---|---|---|
| Number | 12,131 | 3,581 |
| Held | 64.7% | 62.6% |
| Mean / median return, 20 sessions from the retest close | +0.24% / +0.66% | +1.28% / +0.65% |
| Retests that held (known only afterwards) | +3.07% | +4.34% |
| Retests that broke (known only afterwards) | −4.94% | −3.84% |

Buying at the retest close, with no other rule, gave about the same 20-session return as any day in an uptrend. The outcome depends almost entirely on whether the level holds. You cannot know that at entry, which is why the stop under the zone matters so much.

**Does confirmation help?** For each first retest, we compared the two entries of section 3. Each trade was a race, within 30 sessions, between the stop and a gain of 2R.

| Entry | Trades | Stop first | 2R first | Neither |
|---|---|---|---|---|
| US, aggressive limit at the zone top | 11,291 | 63.8% | 34.2% | 1.9% |
| US, confirmed reversal bar | 5,758 | 55.4% | 26.0% | 18.6% |
| India, aggressive limit at the zone top | 3,536 | 64.9% | 32.4% | 2.7% |
| India, confirmed reversal bar | 1,731 | 53.4% | 25.4% | 21.3% |

With a 2R target, you break even if you win one trade in three. Among trades that reached the stop or the target, the aggressive entry won 33–35% of the time, and the confirmed entry about 32%. Neither is an edge on its own. The confirmed entry traded only about half the retests and was stopped less often. Its main value is avoiding cases like Titan, not raising the win rate.

The lesson is the same as for moving-average pullbacks. The level gives you a place to put the stop. Any edge has to come from what you add: breakout quality, market filter, stock selection and exits.

Method notes: daily data. US stocks priced at $10 or more, with at least $20 million average daily traded value. Indian stocks priced at ₹50 or more, with at least ₹10 crore. The universe is today's list, so delisted stocks are missing; this survivorship lifts all returns. When a session touched both the stop and the target, we counted the stop.

## 9. Building and testing it yourself

**Data.** Daily open, high, low, close and volume, adjusted for splits and bonus issues, including delisted stocks. Results dates as they were known at the time. An index series for the market filter.

**Look-ahead traps:**
- The level must come from data before the breakout. Drawing it from a later chart is the most common error in testing support.
- The reversal bar is known only at its close. Entry is the next session.
- "The level held" is known only afterwards. Never use it as a filter.

**Costs (approximate).** US: 0.05–0.10% each way in spread and slippage for liquid stocks. India, delivery: brokerage of zero to ₹20 per order, STT of 0.1% on each side, stamp duty of 0.015% on buys, plus exchange charges and GST. That comes to about 0.25–0.35% per round trip before slippage.

**Gaps.** Fill a buy-stop at the open when the stock gaps over it. Fill a stop at the open when the stock gaps under it.

**What to test, one at a time:**
- Zone width: 0.25, 0.5 and 0.75 ATR.
- Stop buffer: 0, 0.25 and 0.5 ATR.
- Aggressive against confirmed entry.
- Breakout volume filter: breakout-day volume above 1.5 times average, or not.
- The market filter on and off.

```
for each stock s, each day t:
    P = max(high[t-base_length .. t-1]);  base_low = min(low[t-base_length .. t-1])
    if close[t] <= P or P / base_low - 1 > max_base_depth or not filters_pass(s, t): continue
    wait for high >= P * (1 + min_run); cancel if close < P * (1 - fail_depth) first
    r0 = first day after the run with low <= P + zone_width * atr14
    zone_top, zone_bot = P + zone_width * atr14[r0], P - zone_width * atr14[r0]
    for r in r0 .. r0 + confirm_window:
        if close[r] < zone_bot: cancel
        if low[r] <= zone_top and close[r] >= P and close_in_top_third(r):
            entry = max(open[r+1], high[r]) if high[r+1] > high[r] else none
            stop  = min(low[r], zone_bot) - stop_buffer * atr14[r0]
            manage(entry, stop)     # target, trail, time stop, invalidation, gaps
            break
```

**A good test reports:** trades per year; win rate, average win and average loss in R; expectancy after costs; the worst run of losses; and results by year and by market regime. Compare with a baseline that buys random uptrend days with the same exits. See [Expectancy](learn-risk-expectancy.md) and [Backtesting](learn-test-backtesting.md).

## 10. Checklist

- [ ] The level was clear before the breakout, and I wrote it down.
- [ ] The breakout came on good volume from a reasonably tight base.
- [ ] The stock ran away from the level before coming back.
- [ ] This is the first retest.
- [ ] The market index is above its 50-day average.
- [ ] No results inside my holding period; India: not in a tight price band.
- [ ] A reversal bar closed above the level, in the top third of its range.
- [ ] Buy-stop above its high; stop under the zone with the buffer decided now.
- [ ] Size from my risk %, with room for a gap fill above the trigger.
- [ ] Target, trail and time stop written down.

## Further reading

- Robert Edwards and John Magee, *Technical Analysis of Stock Trends*.
- William O'Neil, *How to Make Money in Stocks*.
- Al Brooks, *Trading Price Action Trends*, 2012.
- Carol Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates", *Federal Reserve Bank of New York Economic Policy Review*, 2000.
- Carol Osler, "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *Journal of Finance*, 2003.
- Kenneth Kavajecz and Elizabeth Odders-White, "Technical Analysis and Liquidity Provision", *Review of Financial Studies*, 2004.
- William Brock, Josef Lakonishok and Blake LeBaron, "Simple Technical Trading Rules and the Stochastic Properties of Stock Returns", *Journal of Finance*, 1992.
- Thomas George and Chuan-Yang Hwang, "The 52-Week High and Momentum Investing", *Journal of Finance*, 2004.
- Related guides: [Supply and demand](learn-supply-demand.md), [Bases](learn-bases.md), [Candlestick patterns](learn-candlestick-patterns.md), [Stops and exits](learn-risk-stops-exits.md), [Pullback to a moving average](learn-strat-pullback-ma.md), [Retracements](learn-strat-retracements.md).
