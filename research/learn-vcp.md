# VCP — the volatility contraction pattern

**In short**

- A volatility contraction pattern (VCP) is a base in which each pullback is smaller than the one before, volume dries up, and the price ends in a tight area near the high.
- The idea: each smaller pullback means fewer sellers are left. When almost none remain, a little buying can push the price through the top.
- The buy point is the pivot, the high of the last tight area. The stop goes just under that area's low, so the risk is usually small.
- Measure every VCP you study as a "footprint": weeks, deepest and last pullback, and number of pullbacks.
- Strict VCPs are rare, and in broad data the shape alone did not beat other breakouts. Use it to time a low-risk entry in a stock you already have reasons to own.

This guide is about reading the pattern. A VCP is a particular way of looking at a base, so read [Bases](learn-bases.md) first. For the full trading method built on it, see [SEPA and the VCP](learn-strat-vcp-sepa.md).

---

## 1. The idea

Lam Research, a maker of chip-making equipment, peaked at 53.31 (split-adjusted) at the end of March 2023. Over the next six weeks it pulled back four times:

| Pullback | From | To | Depth |
|---|---|---|---|
| 1 | 53.31 (31 March) | 48.04 (6 April) | 9.9% |
| 2 | 53.65 (20 April) | 49.34 (27 April) | 8.0% |
| 3 | 53.15 (1 May) | 50.72 (4 May) | 4.6% |
| 4 | 53.15 (8 May) | 51.21 (9 May) | 3.7% |

In the five sessions before 15 May, volume was well below its 50-day average. On 15 May 2023 it closed at 55.23. That was above the high of 20 April 2023, 53.65.

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
caption: Each pullback was smaller than the one before, and volume faded into the last two. The pivot was the 20 April high, 53.65.
```

That is a VCP. A stock in a strong uptrend pauses. The first pullback is the biggest, because that is when the most holders take profits and the most nervous holders sell. Buyers step in and the price rallies. Then sellers return, but **fewer of them**, so the next pullback is smaller.

Each pullback (each "contraction") is smaller because the shares for sale are being used up while someone keeps buying. At the end, the price barely moves and volume is unusually low: the sellers have run out. Then a modest amount of buying lifts the stock through the top of that last tight range. With few sellers left above, it can move fast.

```pattern
vcp
```

That is the whole pattern. **The swings get smaller, volume dries up, and the price ends in a tight area near the high.** It is less a new shape than the common core of every good base. A cup with handle is a VCP with two contractions. A high tight flag is a VCP with one.

## 2. Anatomy

| Part | Meaning |
|---|---|
| **Base high** | Where the pattern starts: the peak before the first pullback |
| **Contractions (T1, T2, T3…)** | Each high-to-low pullback inside the base, measured as % of its own high |
| **Depth sequence** | The contractions in order, e.g. 25% → 12% → 6% → 3% |
| **Tight area** | The last few days to two weeks: very small ranges, very low volume |
| **Pivot** | The high of the tight area — the buy point |
| **Tight low** | The low of the tight area — the stop goes just under it |

### The footprint

Minervini summarises a VCP in one short line called a footprint. It has three parts:

| Footprint | Example | Meaning |
|---|---|---|
| Weeks | 20W | the base lasted 20 weeks |
| Deepest / final contraction | 32/3 | the deepest contraction was 32%, the final one 3% |
| Number of contractions | 4T | four contractions |
| Written together | 20W 32/3 4T | the whole footprint |

Lam Research's base lasted about eight weeks, with four contractions. Its deepest was 10% and its last 4%. Writing every base you study this way is good practice. It makes you measure instead of guessing by eye, and it lets you compare bases with each other.

## 3. The rules of thumb

| Rule | Typical value | Common exact version |
|---|---|---|
| Stage 2 uptrend | Trend Template passes | All its conditions, often with an RS rating of 70 or more |
| Prior advance into the base | 30%+ | Base high ≥ 30% above the lowest low of the prior 126 sessions |
| Base length | 3–65 weeks | 15–325 sessions |
| Number of contractions | 2–6 (usually 2–4) | 2–6 |
| First contraction | ≤ ~35% (up to ~50% in a bear market) | ≤ 35% |
| Each contraction vs the previous | Roughly half | ≤ 0.8 × the previous |
| Final contraction | ≤ ~10%, ideally under 5–6% | Last contraction and tight area ≤ 10% |
| Pivot location | Near the top of the base | Pivot ≥ 0.9 × base high |
| Volume in the tight area | Well below average | ≤ 0.7 × the 50-day average |

The two that matter most are **pullbacks that get shallower** and **volume that dries up**. A base can be any length and any of the named shapes. If its pullbacks are not shrinking and its volume is not drying up, it is not a VCP.

## 4. Reading one on a chart, step by step

Use the weekly chart to see the base and the daily chart to measure it.

1. **Check the stock first.** Stage 2, strong RS (80 or more is better), a real prior advance, a healthy industry group, and a market that is not falling apart. A perfect VCP in a weak stock or a weak market is still a low-odds trade.
2. **Mark the base high**: the peak that the stock has not closed clearly above since.
3. **Measure each pullback.** Go from each swing high to the lowest low before the next rally, as a percentage of that high. Ignore wiggles of a percent or two, and count only real reversals. A common filter is to ignore any reversal smaller than about 1.5 times the ATR.
4. **Check that the sequence shrinks.** 25 → 12 → 6 is a VCP. 10 → 15 → 8 is not. A pullback *deeper* than the one before means the sellers came back.
5. **Check volume.** It should fade as the pullbacks shrink, and be at its lowest in the final tight area. Down days on heavy volume late in the base are a warning.
6. **Find the tight area.** Several sessions near the top of the base with small ranges and closes bunched together. On the weekly chart this often looks like two or three weeks closing at almost the same price.
7. **Mark the pivot and the stop.** The pivot is the tight area's high; the stop sits just under the tight area's low. Check the distance. If the stop is more than about 8% below the pivot, the base is not tight enough to buy at the pivot.
8. **Wait.** Nothing happens until the price crosses the pivot.

## 5. Where to buy

### The pivot buy (the default)

Lam Research crossed its pivot of 53.65 on 15 May 2023. A buy-stop order at 53.70 would have filled that day. Volume was 1.36 times its 50-day average, just short of the usual guide. The stop went under the last low of 51.21, a risk of about 5%.

The rule: buy as the price moves through the pivot, **on volume**. Ideally volume is 40–50% or more above the 50-day average. Do **not** buy more than about 5% above the pivot. Above that, the stop is too far away and you are chasing the price.

There are two common ways to do it:

| Entry | How | Trade-off |
|---|---|---|
| **Confirmed breakout** | Wait for a day that closes above the pivot on at least 1.4 times average volume, in the upper half of its range; buy at the next open | Fewer false starts; a worse price; few signals |
| **Buy-stop** | Place an order just above the pivot, which buys automatically once the price reaches it | A better price; more failed breakouts |

### The cheat entries (inside the base)

Minervini also buys *before* the pivot when a smaller shelf forms inside the base. A shelf is a few quiet sessions with their own small high:

- **Cheat ("3C")** — a shelf in the middle third of the base, bought as the price clears the shelf high.
- **Low cheat** — the same, in the lower third. It is riskier.

The appeal is a much closer stop (the shelf low) and a lower price. The cost is that the base is not finished, so more of these fail.

## 6. Where the stop goes, and what happens next

- **Initial stop:** just below the tight low. Never more than about 8% below your buy price; 10% is the absolute limit. If the chart needs a wider stop, don't take the trade, and never widen the stop.
- **Size the position from the stop:** risk about 1% of the account per trade (see [Position sizing](learn-risk-sizing.md)). A tight VCP stop is what lets you hold a meaningful position while risking little.
- **Failed breakout:** if the price closes back under the pivot within the first few days, the breakout may be failing. Good breakouts usually keep going without falling back much. See [Failed breakouts and bull traps](learn-strat-failed-breakouts.md).
- **Protect gains:** once the trade is up two to three times the initial risk, move the stop to your buy price (breakeven). It is common to sell part of the position while the price is still rising, for example a third at three times the risk.
- **Exit on a climax or a trend break:** a run of unusually large up days late in a move, or a close under the 50-day average on heavy volume.

Lam Research reached twice its risk within three sessions, so the stop moved to breakeven. Its first close below the 50-day average came in mid-August 2023, about 20% above the entry.

## 7. Common mistakes

| Mistake | Why it hurts |
|---|---|
| Counting every wiggle as a contraction | Makes any choppy chart look like a VCP |
| Contractions that are not shrinking | Growing swings mean big holders are selling (distribution), not buying (accumulation) |
| A deep final contraction (10%+) | The stop is far away; the base is not finished |
| Buying a breakout on light volume | Few buyers behind the move; many of these fail |
| Buying 5–10% above the pivot | The stop is now far below; the possible gain no longer justifies the risk |
| Ignoring the market | In a correction most breakouts fail, however good the base |
| Late-stage bases (4th+) | The trend is old, and most investors who want the stock already own it |
| Trading the pattern in a stock that is not a leader | A stock with weak RS lacks the buying demand needed to break out |
| Holding through a failed breakout | The pattern was wrong; the loss only grows |

## 8. Detecting a VCP by rule

If you write a program to find VCPs, two details matter. They are where a computer and a human reading the same chart differ.

**Contractions need a zig-zag whose threshold shrinks.** A zig-zag joins swing highs and lows, ignoring any reversal smaller than a set threshold. One fixed threshold cannot catch both a 25% first contraction and a 3% last one.

So start the threshold wide, then narrow it to a fraction of the contraction just measured. Do not let it go below about 1.5 times the ATR, because a smaller "reversal" is just one bar's noise.

**No hindsight.** A swing high is only known some sessions later; with a five-bar rule, five sessions later. Judge the breakout against the pivot as it stood the day *before*, so the breakout bar cannot move its own pivot.

A good detector also records the first rule a stock fails, such as "contractions not shrinking" or "volume not drying up". That shows you *why* a chart is not a VCP, which is how you learn to see one.

## 9. What the evidence says

**Minervini's record.** He won the US Investing Championship in 1997 and describes his methods and results in his books. That shows the method can be traded well by a skilled trader. It does not show how often the pattern works for others.

**Published research.** No academic study tests the VCP itself. Lo, Mamaysky and Wang (2000) found that computer-detected chart patterns carry a little information about future returns, far less than practitioners claim. The research behind momentum and the 52-week high supports the setting a VCP must sit in: a strong stock near its highs (see [SEPA and the VCP](learn-strat-vcp-sepa.md)).

**An event study on stored data.** The SEPA guide measured mechanical base breakouts on daily prices for today's NSE and US stock lists, 2010 to 2026. It then picked out the ones that met a strict VCP test. Outcome: did the price reach +20% before falling 8%, within 60 sessions?

| | India: +20% first | India: median 60-session return | US: +20% first | US: median 60-session return |
|---|---|---|---|---|
| All base breakouts | 29.5% | +2.6% | 18.0% | +1.6% |
| VCP breakouts | 27.6% | +2.0% | 19.1% | +1.4% |

What this shows:

- **Strict VCPs are rare.** About 1.5% of Indian and 1.0% of US breakouts met the mechanical test.
- **The shape alone added little.** VCP breakouts did not clearly beat other breakouts in either market.
- **Volume dry-up made no visible difference** in that study.

The method note, the stop-based results and the caveats are in [SEPA and the VCP](learn-strat-vcp-sepa.md).

**Limits.** A rule-based test cannot capture the judgement in Minervini's own trading: reading the market, knowing the stock's story, and knowing when not to trade. The study uses today's stock lists (survivorship bias), no costs, and no earnings or relative-strength filters.

What it does show is that **the shape alone, applied by fixed rules, is not an edge**. Treat the VCP as a way to time a low-risk entry in a stock you already have reasons to own. Its tight stop tells you quickly when you are wrong.

## 10. Checklist

- [ ] Stage 2, RS 70+ (80+ better), healthy group, market in an uptrend
- [ ] Prior advance of 30%+
- [ ] 2–6 contractions, each clearly smaller than the last
- [ ] First contraction ≤ ~35%; final ≤ ~10%, ideally under 5–6%
- [ ] Volume fading through the base, quietest in the tight area
- [ ] Tight area near the top of the base (pivot within ~10% of the high)
- [ ] Stop just under the tight low, no more than ~8% below the pivot
- [ ] Breakout on volume 40–50%+ above average; buy within ~5% of the pivot
- [ ] Early-stage base; no earnings due within a couple of weeks
- [ ] Write the footprint: weeks, max/final depth, number of contractions

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* and *Think & Trade Like a Champion* — the VCP, the footprint, pivots, cheat entries and risk control.
- Andrew Lo, Harry Mamaysky and Jiang Wang, "Foundations of Technical Analysis", *Journal of Finance* (2000).
- [Chart patterns](learn-chart-patterns.md) — the named bases, with drawings.
- [SEPA and the VCP](learn-strat-vcp-sepa.md) — the full SEPA method, with worked trades.
