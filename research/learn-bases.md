# Bases — what they are and how to spot one forming

Learning material: what a base is, where it sits in a stock's life, the common
types of base, and — the practical part — **how to tell a base is forming
while it is still forming**, before the breakout makes it obvious. It is a
companion to [learn-vcp.md](learn-vcp.md) (the volatility contraction
pattern, the base Mark Minervini trades) and to
[learn-chart-patterns.md](learn-chart-patterns.md) (the catalogue of
patterns, with drawings).

**Where this shows up in the app.** The `minervini` strategy finds bases with
the code in `scripts/swing_screener/core/vcp_spec.py`. The `chart_pattern`
strategy recognises named bases (cup, flat base, double bottom, flag,
triangle) with `core/chart_patterns.py`. Both show their rules on the
Strategies page. The Stage 2 screen (Screens → Stage 2 — Trend Template)
lists the stocks in which a base is *worth* watching.

---

## 1. What a base is

A base is a **sideways consolidation after an advance**. A stock that has run
up stops going up. It gives back part of the gain. Then it moves sideways
while shares pass from sellers to new buyers.

Why it happens, in terms of supply (shares for sale) and demand (buyers):

- **Profit-taking.** People who bought at lower prices sell. That selling
  pushes the price down until buyers who missed the first move are willing
  to buy those shares.
- **Overhang.** Some people bought near the top and are now sitting on a
  loss. Many of them sell when the price gets back to what they paid, just
  to get out even. That is why the old high acts as resistance.
- **Catching up.** The rally ran ahead of the moving averages and of the
  business itself. Time spent sideways lets the averages — and the
  earnings — catch up.

If big buyers are still steadily buying (accumulating), they step in sooner
on each wave of selling, so the pullbacks get smaller. Eventually the sellers
waiting at the old high have all sold. Then a modest amount of buying pushes
the price through it: the **breakout**. The base is the period that makes the
next leg up *possible*. The breakout is the evidence that it has begun.

A base is not a pattern you predict. It is a **condition you recognise**: an
uptrend that is pausing in an orderly way.

## 2. Where a base sits in a stock's life

Stan Weinstein's four stages are the simplest map:

| Stage | What price does | Bases here are… |
|---|---|---|
| 1 — Basing | Sideways after a decline; the 200-day flattens | *Bottoming* bases. Cheap, but no trend to ride yet |
| **2 — Advancing** | **Higher highs and lows above a rising 200-day** | **The ones to buy.** Continuation bases inside an uptrend |
| 3 — Topping | Sideways after an advance, with wider, messier swings; 200-day flattens | Look like bases, but big holders are selling (distribution) |
| 4 — Declining | Lower highs and lows below a falling 200-day | Not bases — just pauses in a downtrend |

The Trend Template (the Stage 2 screen, conditions M1–M8) defines Stage 2 by
fixed rules: the price is above a rising 200-day average; the 50-day average
is above the 150-day, which is above the 200-day; the price is at least 30%
above its 52-week low and within 25% of its 52-week high.

### Base count

Stocks rarely make one base and stop. A long advance is like a staircase:
base, breakout, run, then another base. The **base count** numbers the bases
since the trend last broke:

- **Bases 1–2** — the trend is young and few investors own the stock yet.
  The odds are best.
- **Base 3** — still tradeable. More people now know the story.
- **Base 4+** — late stage. The move is obvious and most of the investors
  who want the stock already own it. Late-stage bases fail far more often,
  and often turn out to be the top itself.

The count **resets** when a base falls below the prior base's low, or when a
deep correction breaks the 200-day. The next base is then a new base 1. The
backtest records the count (`base_no`; the `--max-base` option limits trades
to early bases).

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

## 4. The common base types

The numbers are the usual ones from William O'Neil and Mark Minervini. They
are guides, not laws. In a bear market a deeper base is acceptable, because
everything falls more.

| Base | Length | Depth | The shape |
|---|---|---|---|
| **Cup with handle** | 7–65 weeks | 12–35% (up to ~50% in a bear market) | Rounded U, then a small drift (the handle) in the upper half |
| **Cup without handle** | 7–65 weeks | 12–35% | The U alone; buy point is the old high |
| **Double bottom** | 7+ weeks | 20–35% | W; the second low undercuts the first, shaking out weak holders |
| **Flat base** | 5+ weeks | ≤ 15% | Tight sideways box, often right after another base |
| **High tight flag** | 3–5 weeks of flag | ≤ 25% pullback | Rare: a 100%+ run in under 8 weeks, then a short tight pause |
| **Ascending base** | 9–16 weeks | 10–20% per dip | Three pullbacks, each low higher than the last |
| **Base on base** | — | — | A new base forms just above a prior one that broke out but did not run |
| **VCP** | 3–65 weeks | first contraction ≤ ~35% | Any of the above where each pullback is smaller — see [learn-vcp.md](learn-vcp.md) |

```pattern
cup-with-handle
```

```pattern
flat-base
```

What they share matters more than the names: **an uptrend, a pause of at
least a few weeks, pullbacks that get smaller, volume that dries up, and a
clear high to break.** "VCP" is simply the name for those shared features.

## 5. How to tell a base is forming

You cannot be sure a base is a base until it breaks out. But you can see one
taking shape, roughly in the order below. Use the **weekly chart** for the
overall shape and the **daily chart** for the detail.

### Step 1 — Is the stock eligible?

Before looking for a base at all:

- It is in **Stage 2** (it passes the Trend Template, or comes close).
- It had a real **prior advance** — 30%+ into the high.
- Its **relative strength** is high (RS rating 70+, ideally 80+). Its
  industry group is not weak (the app's group-strength study found that
  strength in the group helps).

A "base" in a stock that fails these checks is usually just a pause in
Stage 1, 3 or 4.

### Step 2 — The advance stalls (week 1–2)

- The stock **stops making new highs**. Its highest high becomes the
  base high for now.
- The price pulls back. At this point it is **just a pullback**. Most
  pullbacks never become bases, so don't call it one yet.

What a healthy pullback looks like: the drop comes on **lighter volume than
the advance did**. There is no cluster of down days on heavy volume (which
would mean big holders are selling — distribution).

### Step 3 — The first low holds (weeks 2–5)

- The pullback **finds support** — commonly near the 50-day (10-week) moving
  average, a level where the stock broke out before, or the top of the
  previous base.
- The depth is **in proportion**. For a leading stock, a correction about
  1.5–2.5× as deep as the market's is normal. Falling much deeper than its
  peers or the market is a warning.
- It stays **above the 200-day**. A clear close well below it puts the
  uptrend in question.

Once the low has held for 3–5 weeks, you can start to call it a base.

### Step 4 — Volatility contracts (weeks 3 onward)

This is the most important clue, and the heart of the VCP:

- **Each rally and pullback inside the base is smaller than the last.** A
  first drop of 25%, then 12%, then 6% says the supply of shares for sale is
  drying up.
- **Daily ranges narrow** and the closing prices bunch together. On the
  weekly chart, look for two or three weeks that close within ~1–2% of each
  other ("tight closes").
- The **ATR falls** (measured as % of price).

Swings that get *bigger*, or a range that stays wide and choppy, mean the
opposite. Large amounts of stock are still changing hands at very different
prices.

### Step 5 — Volume dries up

- Volume in the later part of the base is **well below average** — the
  quietest stretch of the whole move. Days near the lows with volume 30–50%
  below the 50-day average are a good sign: the sellers have run out.
- Up weeks come on more volume than down weeks — a sign of buying
  (accumulation). Big down weeks on big volume — a sign of selling
  (distribution) — are a warning.

### Step 6 — Relative strength holds up

- The **RS line** (the stock's price divided by the index) stays near its
  highs while the price is basing. An RS line making a new high *before* the
  price does is one of the best signs.
- If the market is correcting and the stock holds *above* its lows while it bases, the
  stock is showing strength.

### Step 7 — The right side builds and a pivot appears

- The price recovers toward the base high, making **higher lows** on the way.
- The moving averages flatten and come together. The 50-day average catches
  up to just below the price.
- A **tight area** forms near the top of the base: a few days, or a week or
  two, of very small ranges on very low volume. Its high is the **pivot**.

Now the base is ready. The trade is the move through the pivot on rising
volume (typically 40–50%+ above average). You buy within about 5% of the
pivot.

### A quick way to remember it

> **Uptrend → pause → smaller swings → quieter volume → strong RS → tight near the high.**

If any link is missing, it is not a base yet — or it is a weak one.

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

## 7. How this app measures a base

The `minervini` strategy turns the description above into exact rules. They
are in `core/vcp_spec.py` and documented on the Strategies page:

- **Base high** — the most recent confirmed swing high that no *decisive*
  close has cleared. A swing high here is a bar whose high is above the 5 bars
  on either side. It is only known 5 bars later, so the rule uses no
  hindsight. To end the base, a close must clear the base high by about one
  ATR. A base's ceiling is a zone, not an exact line, so a close just barely
  above it does not count.
- **Prior advance** — the base high is at least 30% above the low of the 126
  sessions before it.
- **Length** — 15 to 325 sessions (about 3 to 65 weeks).
- **Trend through the base** — the full Trend Template passes on the day of
  the base high, and the moving averages stay in the right order every day.
  (The close may dip slightly under the 200-day, because a deep first
  contraction can legitimately do that.)
- **Base number** — 1 + the number of earlier bases in the same stock that
  produced a setup since the trend last broke. The count resets when the
  moving averages are out of order for 20 sessions in a row.

The tightness and volume steps are the VCP rules — see
[learn-vcp.md](learn-vcp.md).

## 8. What the evidence says

Read this before trusting any pattern:

- **Bases tell you *when* to buy, not whether to.** Their value is a nearby,
  logical stop. If the stock falls back into the base, you were wrong, and
  the loss is small.
- **This project's backtests found no reliable edge** from bases detected by
  rule on daily data, in either market, from 2010 — see
  [minervini-spec-sensitivity-india.md](minervini-spec-sensitivity-india.md),
  [minervini-spec-sensitivity-us.md](minervini-spec-sensitivity-us.md) and the
  record of tests in [momentum-trend-research.md](momentum-trend-research.md).
  Strict definitions find very few complete bases. Loose ones find many that
  fail.
- **Context mattered more than shape.** Skipping stocks in weak industry
  groups improved the earlier Minervini version's results in both markets.
  The market's direction matters too: most breakouts fail in a weak market.

So: learn to *see* bases. They organise when you act and where your stop
goes. But judge any system that trades them by its backtest, not by how good
the chart looks.

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

- Mark Minervini, *Trade Like a Stock Market Wizard* — Stage 2, the Trend
  Template, base counts and the VCP.
- William O'Neil, *How to Make Money in Stocks* — the cup with handle, flat
  base, double bottom and the conventions for depth and length.
- Stan Weinstein, *Secrets for Profiting in Bull and Bear Markets* — the four
  stages.
- Nicolas Darvas, *How I Made $2,000,000 in the Stock Market* — the box theory
  behind the flat base.
