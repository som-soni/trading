# Bases — what they are and how to spot one forming

**In short**

- A base is a sideways pause after a strong advance. Shares pass from sellers who want out to new buyers, and the next leg up becomes possible.
- The bases worth watching sit in Stage 2: the stock is above a rising 200-day average, after a real advance of 30% or more.
- You can see a base forming before it breaks out: the swings get smaller, volume dries up, relative strength holds, and a tight area forms near the top.
- The breakout through the pivot is the trade. The base's low points give you a nearby, logical stop.
- In broad data, breakouts from bases are only slightly better than a random liquid stock. Bases tell you *when* to act and where you are wrong, not *whether* the stock will rise.

This guide explains what a base is, where it sits in a stock's life, the common types, and how to tell a base is forming while it is still forming. For the drawn shapes, see [learn-chart-patterns](learn-chart-patterns.md). For the volatility contraction pattern (VCP), Minervini's version of a base, see [learn-vcp](learn-vcp.md).

---

## 1. What a base is

Larsen & Toubro, India's largest engineering company, rose from ₹843 in September 2020 to ₹1,593 on 2 February 2021. That is a gain of 89% in four months. Then it stopped rising.

Over the next five months it fell to ₹1,435, bounced to ₹1,565, and fell again to ₹1,306 in April. That low was 18% below the high. From May it climbed back on higher lows. In early July it spent two weeks almost still, and weekly volume fell to its lowest of the whole base. On 15 July 2021 it closed at ₹1,609, above the February high, on 3.2 times its average volume.

```series
title: Larsen & Toubro — a five-month base and its breakout, 2021
from: 2020-09-01
to: 2021-10-31
tf: D
line: india:LT.NS | Larsen & Toubro | log
line: india:LT.NS@sma50 | 50-day average
line: india:LT.NS@sma200 | 200-day average
line: india:LT.NS@vol | Volume | pane2 bars
mark: 2021-02-02 | base high ₹1,593
mark: 2021-04-19 | base low, 18% deep
mark: 2021-07-09 | tight, quiet weeks
mark: 2021-07-15 | breakout, 3.2× volume
caption: An 89% advance, then a five-month pause. The low held far above the 200-day average, the right side rose on higher lows, and volume was quietest just before the breakout.
```

That pause is a **base**: a sideways consolidation after an advance. A stock that has run up stops going up, gives back part of the gain, and then moves sideways while shares pass from sellers to new buyers.

Why it happens, in terms of supply (shares for sale) and demand (buyers):

- **Profit-taking.** People who bought at lower prices sell. That selling pushes the price down until buyers who missed the first move are willing to buy those shares.
- **Overhang.** Some people bought near the top and are now sitting on a loss. Many of them sell when the price gets back to what they paid, just to get out even. That is why the old high acts as resistance.
- **Catching up.** The rally ran ahead of the moving averages and of the business itself. Time spent sideways lets the averages, and the earnings, catch up.

If big buyers are still steadily buying (accumulating), they step in sooner on each wave of selling, so the pullbacks get smaller. Eventually the sellers waiting at the old high have all sold. Then a modest amount of buying pushes the price through it: the **breakout**.

The base is the period that makes the next leg up *possible*. The breakout is the evidence that it has begun. A base is not a pattern you predict. It is a **condition you recognise**: an uptrend that is pausing in an orderly way.

## 2. Where a base sits in a stock's life

Stan Weinstein's four stages are the simplest map (see [learn-price-stages](learn-price-stages.md)):

| Stage | What price does | Bases here are… |
|---|---|---|
| 1 — Basing | Sideways after a decline; the 200-day flattens | *Bottoming* bases. Cheap, but no trend to ride yet |
| **2 — Advancing** | **Higher highs and lows above a rising 200-day** | **The ones to buy.** Continuation bases inside an uptrend |
| 3 — Topping | Sideways after an advance, with wider, messier swings; 200-day flattens | Look like bases, but big holders are selling (distribution) |
| 4 — Declining | Lower highs and lows below a falling 200-day | Not bases — just pauses in a downtrend |

Mark Minervini's **Trend Template** defines Stage 2 by fixed rules:

- the price is above a rising 200-day average;
- the 50-day average is above the 150-day, which is above the 200-day;
- the price is at least 30% above its 52-week low;
- the price is within 25% of its 52-week high.

### Base count

Stocks rarely make one base and stop. A long advance is like a staircase: base, breakout, run, then another base. The **base count** numbers the bases since the trend last broke:

- **Bases 1–2.** The trend is young and few investors own the stock yet. The odds are best.
- **Base 3.** Still tradeable. More people now know the story.
- **Base 4 and later.** Late stage. The move is obvious, and most investors who want the stock already own it. Late-stage bases fail far more often, and often turn out to be the top itself.

The count **resets** when a base falls below the prior base's low, or when a deep correction breaks the 200-day average. The next base is then a new base 1.

## 3. Anatomy

```pattern
anatomy
```

| Part | What to measure |
|---|---|
| **Prior advance** | The run into the base. It should be roughly **30%+**; a base after a 10% drift is just noise |
| **Base high** (left side) | The peak where the base starts. Day 1 of the base |
| **Depth** | From the base high to the lowest low, as % of the high |
| **Length** | Weeks from the base high to today |
| **Right side** | The recovery back toward the base high |
| **Pivot** | The price that, once crossed, means the base is done — usually the top of the last tight area (a stretch of very small daily ranges) |
| **Volume** | Heavy on the advance, lighter in the base, quietest just before the breakout |

For L&T: a prior advance of 89% and a base high of ₹1,593. The depth was 18%, and the length about 23 weeks.

## 4. The common base types

The numbers are the usual ones from William O'Neil and Mark Minervini. They are guides, not laws. In a bear market a deeper base is acceptable, because everything falls more.

| Base | Length | Depth | The shape |
|---|---|---|---|
| **Cup with handle** | 7–65 weeks | 12–35% (up to ~50% in a bear market) | Rounded U, then a small drift (the handle) in the upper half |
| **Cup without handle** | 7–65 weeks | 12–35% | The U alone; buy point is the old high |
| **Double bottom** | 7+ weeks | 20–35% | W; the second low undercuts the first, shaking out weak holders |
| **Flat base** | 5+ weeks | ≤ 15% | Tight sideways box, often right after another base |
| **High tight flag** | 3–5 weeks of flag | ≤ 25% pullback | Rare: a 100%+ run in under 8 weeks, then a short tight pause |
| **Ascending base** | 9–16 weeks | 10–20% per dip | Three pullbacks, each low higher than the last |
| **Base on base** | — | — | A new base forms just above a prior one that broke out but did not run |
| **VCP** | 3–65 weeks | first contraction ≤ ~35% | Any of the above where each pullback is smaller — see [learn-vcp](learn-vcp.md) |

```pattern
cup-with-handle
```

```pattern
flat-base
```

What they share matters more than the names. Each has **an uptrend and a pause of at least a few weeks**. Each has **pullbacks that get smaller, volume that dries up, and a clear high to break.** "VCP" is simply the name for those shared features.

## 5. How to tell a base is forming

You cannot be sure a base is a base until it breaks out. But you can see one taking shape, roughly in the order below. Use the **weekly chart** for the overall shape and the **daily chart** for the detail.

### Step 1 — Is the stock eligible?

Before looking for a base at all, check three things:

- It is in **Stage 2**: it passes the Trend Template, or comes close.
- It had a real **prior advance**: 30% or more into the high.
- Its **relative strength** is high: a rating of 70 or more, ideally 80 or more (see [learn-price-rs](learn-price-rs.md)). Its industry group is not weak (see [learn-sectors-groups](learn-sectors-groups.md)).

A "base" in a stock that fails these checks is usually just a pause in Stage 1, 3 or 4.

### Step 2 — The advance stalls (weeks 1–2)

L&T made its high on 2 February and then stopped making new highs. That high became the base high, for now.

The price pulls back. At this point it is **just a pullback**. Most pullbacks never become bases, so don't call it one yet.

What a healthy pullback looks like: the drop comes on **lighter volume than the advance did**. There is no cluster of down days on heavy volume, which would mean big holders are selling (distribution).

### Step 3 — The first low holds (weeks 2–5)

The pullback **finds support**. Common places are the 50-day (10-week) moving average, a level where the stock broke out before, or the top of the previous base.

- The depth is **in proportion**. For a leading stock, a correction about 1.5–2.5 times as deep as the market's is normal. Falling much deeper than its peers or the market is a warning.
- It stays **above the 200-day**. A clear close well below it puts the uptrend in question. L&T's April low of ₹1,306 was still more than 10% above its 200-day average.

Once the low has held for three to five weeks, you can start to call it a base.

### Step 4 — Volatility contracts (week 3 onward)

This is the most important clue, and the heart of the VCP. **Each rally and pullback inside the base is smaller than the last.** A first drop of 25%, then 12%, then 6%, says the supply of shares for sale is drying up.

- **Daily ranges narrow** and the closing prices bunch together. On the weekly chart, look for two or three weeks that close within about 1–2% of each other ("tight closes"). L&T's weekly closes on 2 and 9 July were ₹1,485.70 and ₹1,499.60, less than 1% apart.
- The **ATR falls**, measured as a percentage of the price.

Swings that get *bigger*, or a range that stays wide and choppy, mean the opposite. Large amounts of stock are still changing hands at very different prices.

### Step 5 — Volume dries up

Volume in the later part of the base is **well below average**: the quietest stretch of the whole move. Days near the lows with volume 30–50% below the 50-day average are a good sign: the sellers have run out.

Up weeks should come on more volume than down weeks; that is a sign of buying (accumulation). Big down weeks on big volume are a sign of selling (distribution) and a warning.

### Step 6 — Relative strength holds up

The **RS line** is the stock's price divided by the index. It should stay near its highs while the price is basing. An RS line making a new high *before* the price does is one of the best signs.

If the market is correcting and the stock holds *above* its lows while it bases, the stock is showing strength.

### Step 7 — The right side builds and a pivot appears

- The price recovers toward the base high, making **higher lows** on the way. L&T's weekly lows rose from about ₹1,319 in early May to ₹1,485 in early July.
- The moving averages flatten and come together. The 50-day average catches up to just below the price.
- A **tight area** forms near the top of the base: a few days, or a week or two, of very small ranges on very low volume. Its high is the **pivot**.

Now the base is ready. The trade is the move through the pivot on rising volume, typically 40–50% or more above average. You buy within about 5% of the pivot. How traders run that trade is in [learn-strat-canslim-breakout](learn-strat-canslim-breakout.md) and [learn-strat-vcp-sepa](learn-strat-vcp-sepa.md).

### A quick way to remember it

> **Uptrend → pause → smaller swings → quieter volume → strong RS → tight near the high.**

If any link is missing, it is not a base yet, or it is a weak one.

## 6. Faulty bases — warning signs

| Sign | Why it matters |
|---|---|
| **Wide and loose** — big daily ranges, swings not shrinking | Plenty of shares still for sale; no big buyer is steadily accumulating |
| **V-shaped** — straight down, straight back up in a couple of weeks | No time for nervous holders to sell out; the sellers waiting near the old high are still there |
| **Too deep** — 40–50%+ in a normal market | The trend is damaged; many holders who bought higher are sitting on losses and will sell on the way up |
| **Handle / tight area in the lower half** of the base | Buyers too weak to bring it near the high |
| **Wedging** — drifting *up* on falling volume into the pivot | Fragile; often fails on the breakout |
| **Heavy-volume selling** inside the base | Distribution, not accumulation |
| **Below the 200-day** or a falling 200-day | Not Stage 2 |
| **Late stage** — base 4 or later | Most investors who want the stock already own it; late-stage bases often mark the top |
| **Laggard RS** — the stock bases while its group and the market run | No leadership |
| **Earnings due inside the base** | A gap can wreck a perfect pattern in one session |

## 7. Measuring a base by rule

If you want to find bases with a program, or just measure them consistently by hand, the description above needs exact rules. Common choices:

- **Base high.** A swing high is a bar whose high is above the five bars on either side. It is only known five bars later, so a fair test waits for that. Treat the ceiling as a zone, not an exact line: require a close about one ATR above the base high before calling the base finished.
- **Prior advance.** The base high is at least 30% above the lowest low of the 126 sessions (about six months) before it.
- **Length.** 15 to 325 sessions, about 3 to 65 weeks.
- **Trend through the base.** The Trend Template passes on the day of the base high, and the moving averages stay in order. Allow the close to dip slightly under the 200-day, because a deep first contraction can do that.
- **Base number.** Count the earlier bases since the trend last broke. Reset the count when the moving averages have been out of order for about a month.

The tightness and volume steps are the VCP rules; see [learn-vcp](learn-vcp.md).

## 8. What the evidence says

**What practitioners claim.** O'Neil built his base types from studying the biggest winners. That is a study of winners only. It shows what winners looked like before they ran, not how often stocks with those bases went on to win.

**An event study on stored data.** We measured every breakout to a new 52-week high out of a base, and compared it with an ordinary day in an ordinary liquid stock.

> **Method note.** Daily prices for today's NSE and US stock lists, January 2010 to July 2026. A breakout is the first close above the highest high of the prior 250 sessions. That high (the base high) must be at least 15 sessions old, and at least 30% above the lowest low of the 126 sessions before it. Depth is the fall from the base high to the lowest low since. Liquidity: close at least ₹20 or $5, and 50-day average turnover at least ₹5 crore or $5 million. At most one breakout per stock per 20 sessions. Outcome: from the breakout close, does the high reach +20% before the low touches −8%, within 60 sessions? Baseline: every 20th session of every liquid stock. Market: the Nifty 500 or the S&P 500 (total return) above or below its 50-day average. Caveats: today's lists only (survivorship bias), no costs, overlapping windows.

| | India breakouts | India baseline | US breakouts | US baseline |
|---|---|---|---|---|
| Events | 5,971 | 90,082 | 17,409 | 328,366 |
| +20% before −8% | 31.0% | 25.2% | 18.5% | 18.8% |
| −8% first | 58.3% | 59.4% | 54.4% | 52.0% |
| Median 60-session return | +2.1% | +1.0% | +1.5% | +1.9% |

**By depth of the base:**

| Depth | India events | India: +20% first | India: −8% first | US events | US: +20% first | US: −8% first |
|---|---|---|---|---|---|---|
| Under 10% | 588 | 24.5% | 48.8% | 4,161 | 11.4% | 46.4% |
| 10–15% | 1,371 | 30.3% | 57.7% | 4,162 | 16.8% | 53.0% |
| 15–25% | 2,311 | 31.4% | 59.5% | 4,807 | 19.4% | 56.1% |
| 25–35% | 1,016 | 33.5% | 59.1% | 2,155 | 22.9% | 59.8% |
| 35–50% | 560 | 32.0% | 63.9% | 1,250 | 27.4% | 61.0% |

**By the market's trend on the breakout day:**

| | India: events | India: median 60-session return | US: events | US: median 60-session return |
|---|---|---|---|---|
| Index above its 50-day average | 5,267 | +2.6% | 15,630 | +1.4% |
| Index below its 50-day average | 704 | −0.5% | 1,779 | +1.9% |

What this shows:

- **A breakout from a base is a thin edge at best.** In India it beat an ordinary liquid stock slightly. In the US it did not.
- **Deeper bases were more volatile, not better.** They reached +20% more often and hit −8% more often. Tight bases rarely reached +20% in 60 sessions; a tight base suits a tight stop and a smaller target.
- **Base length made no consistent difference.** Bases of 3–5 weeks and of 6–12 months reached +20% about as often in both markets.
- **Volume dry-up made no consistent difference** in this simple test. Breakouts after a quiet last two weeks did about as well as the rest.
- **The market's trend mattered in India, not in the US.** Indian breakouts with the Nifty 500 below its 50-day average had a negative median result. US breakouts did not.

**Limits.** The test uses fixed percentage exits, which favour volatile stocks. It does not use relative strength, earnings, industry groups or base count, which practitioners say matter most. A trained eye also picks bases differently from a rule.

So: learn to *see* bases. They organise when you act and where your stop goes. But do not expect the base itself to make money. Judge any method that trades them by a careful test, not by how good the chart looks.

## 9. Checklist

- [ ] Stage 2 — passes the Trend Template
- [ ] Prior advance of 30%+ into the base high
- [ ] RS rating 70+; industry group not weak
- [ ] At least 3–5 weeks since the high (7+ for a cup)
- [ ] Depth in proportion to the market and the stock's volatility (usually ≤ 35%)
- [ ] Holding above the 200-day; support found near the 50-day or a prior level
- [ ] Pullbacks getting smaller; ranges and ATR narrowing
- [ ] Volume drying up, quietest near the end
- [ ] RS line near its high
- [ ] Right side rising on higher lows; a tight area near the top defines the pivot
- [ ] Early-stage base (1–3); no earnings inside the next couple of weeks
- [ ] Market in an uptrend

## Further reading

- Mark Minervini, *Trade Like a Stock Market Wizard* — Stage 2, the Trend Template, base counts and the VCP.
- William O'Neil, *How to Make Money in Stocks* — the cup with handle, flat base, double bottom and the conventions for depth and length.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — the four stages.
- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* — the box theory behind the flat base. See also [learn-strat-darvas](learn-strat-darvas.md).
