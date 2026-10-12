# Bases — what they are and how to spot one forming

Learning material: what a base is, where it sits in a stock's life, the common
base types, and — the practical part — **how to tell a base is forming while it
is still forming**, before the breakout makes it obvious. Companion to
[learn-vcp.md](learn-vcp.md) (the volatility contraction pattern, the base
Minervini trades) and [learn-chart-patterns.md](learn-chart-patterns.md) (the
pattern catalogue with drawings).

**Where this shows up in the app.** The `minervini` strategy finds bases with
`scripts/swing_screener/core/vcp_spec.py`; the `chart_pattern` strategy
recognises named bases (cup, flat base, double bottom, flag, triangle) with
`core/chart_patterns.py`. Both show their rules on the Strategies page. The
Stage 2 screen (Screens → Stage 2 — Trend Template) is the list of stocks in
which a base is *worth* watching.

---

## 1. What a base is

A base is a **sideways consolidation after an advance** — a period in which a
stock that has run up stops going up, gives back part of the gain, and moves
sideways while the shares change hands.

Why it happens, in supply-and-demand terms:

- **Profit-taking.** Holders from lower prices sell. That supply pushes price
  down until buyers who missed the first move are willing to absorb it.
- **Overhang.** Anyone who bought near the top and is now under water sells
  when price returns to their entry. That is why the old high is resistance.
- **Digestion.** The rally ran ahead of the moving averages and the business.
  Time spent sideways lets the averages — and the earnings — catch up.

If big buyers are still accumulating, each wave of selling is met sooner and
the pullbacks get smaller. Eventually the supply at the old high is used up,
and a modest amount of demand pushes price through it: the **breakout**. A
base is the period that makes the next leg up *possible*; the breakout is the
evidence that it has begun.

A base is not a pattern you predict — it is a **condition you recognise**: an
uptrend that is pausing in an orderly way.

## 2. Where a base sits in a stock's life

Stan Weinstein's four stages are the simplest map:

| Stage | What price does | Bases here are… |
|---|---|---|
| 1 — Basing | Sideways after a decline; the 200-day flattens | *Bottoming* bases. Cheap, but no trend to ride yet |
| **2 — Advancing** | **Higher highs and lows above a rising 200-day** | **The ones to buy.** Continuation bases inside an uptrend |
| 3 — Topping | Sideways after an advance, wider and sloppier; 200-day flattens | Look like bases, are distribution |
| 4 — Declining | Lower highs and lows below a falling 200-day | Not bases — rests in a downtrend |

The Trend Template (Stage 2 screen, gates M1–M8) is a mechanical definition of
Stage 2: price above a rising 200-day, the 50 above the 150 above the 200, at
least 30% off the 52-week low and within 25% of the high.

### Base count

Stocks rarely make one base and stop. A long advance is a staircase: base,
breakout, run, base again. The **base count** numbers them since the trend
last broke:

- **Bases 1–2** — the trend is young, few people own it, the odds are best.
- **Base 3** — still tradeable; more people now know the story.
- **Base 4+** — late stage. The move is obvious, ownership is crowded, and
  late-stage bases fail far more often (often as the top itself).

A base that undercuts the prior base's low, or a deep correction that breaks
the 200-day, **resets the count** — the next base is a new base 1. The
backtest records it (`base_no`; `--max-base` limits trades to early bases).

## 3. Anatomy

```pattern
anatomy
```

| Part | What to measure |
|---|---|
| **Prior advance** | The run into the base. Wants roughly **30%+**; a base after a 10% drift is just noise |
| **Base high** (left side) | The peak where the base starts. Day 1 of the base |
| **Depth** | Base high to the lowest low, as % of the high |
| **Length** | Weeks from the base high to today |
| **Right side** | The recovery back toward the base high |
| **Pivot** | The price that, once crossed, means the base is done — usually the top of the last tight area |
| **Volume** | Heavy on the advance, lighter in the base, quietest just before the breakout |

## 4. The common base types

The numbers are the conventional ones (O'Neil, Minervini) — guides, not laws.
Depth tolerances widen in a bear market because everything falls more.

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
well-defined high to break.** The VCP is simply the name for that shared core.

## 5. How to tell a base is forming

You cannot know a base is a base until it breaks out — but you can see one
taking shape, in roughly this order. Use the **weekly chart** for the shape
and the **daily chart** for the detail.

### Step 1 — Is the stock eligible?

Before looking for a base at all:

- It is in **Stage 2** (passes the Trend Template, or close to it).
- It had a real **prior advance** — 30%+ into the high.
- Its **relative strength** is high (RS rating 70+, ideally 80+), and its
  industry group is not weak (the group-strength study found group RS helps).

A "base" in a stock that fails these is usually a Stage 1, 3 or 4 rest.

### Step 2 — The advance stalls (week 1–2)

- The stock **stops making new highs**. The highest high becomes the
  provisional base high.
- Price pulls back. At this point it is **just a pullback** — most pullbacks
  never become bases. Don't label it yet.

What healthy looks like: the drop comes on **lighter volume than the advance**,
and there is no cluster of heavy-volume down days (distribution).

### Step 3 — The first low holds (weeks 2–5)

- The pullback **finds support** — commonly near the 50-day (10-week) moving
  average, a prior breakout level, or the top of the previous base.
- Depth is **in proportion**: a correction about 1.5–2.5× the market's is
  normal for a leader; far deeper than its peers or the market is a warning.
- It stays **above the 200-day**. Closing decisively below it means the
  uptrend is in question.

After 3–5 weeks with the low holding, you can start to call it a base.

### Step 4 — Volatility contracts (weeks 3 onward)

This is the most important tell, and the core of the VCP:

- **Each rally and pullback inside the base is smaller than the last.** A
  first drop of 25% followed by 12%, then 6% says supply is drying up.
- **Daily ranges narrow** and the closes cluster. On the weekly chart, look
  for two or three weeks closing within ~1–2% of each other ("tight closes").
- The **ATR falls** (average true range as % of price).

Swings that get *bigger*, or a range that stays wide and loose, mean the
opposite: the stock is still changing hands violently.

### Step 5 — Volume dries up

- Volume in the latter part of the base is **well below average** — the
  quietest stretch of the whole move. Days with volume 30–50% below the 50-day
  average near the lows are a good sign (sellers are exhausted).
- Up weeks come on more volume than down weeks (accumulation). Big down weeks
  on big volume (distribution) are a warning.

### Step 6 — Relative strength holds up

- The **RS line** (stock ÷ index) stays near its highs while price is basing.
  An RS line making a new high *before* price does is one of the best signs.
- If the market is correcting and the stock is basing *above* its lows, it is
  showing strength.

### Step 7 — The right side builds and a pivot appears

- Price recovers toward the base high on **higher lows**.
- Moving averages flatten and converge; the 50-day catches up under price.
- A **tight area** forms near the top of the base — a few days or a week or
  two of very small ranges on very low volume. Its high is the **pivot**.

Now the base is ready. The trade is the move through the pivot on rising
volume (typically 40–50%+ above average), bought within about 5% of the pivot.

### A quick way to remember it

> **Uptrend → pause → smaller swings → quieter volume → strong RS → tight near the high.**

If any link is missing, it is not a base yet — or it is a weak one.

## 6. Faulty bases — warning signs

| Sign | Why it matters |
|---|---|
| **Wide and loose** — big daily ranges, swings not shrinking | Supply still heavy; no one is accumulating |
| **V-shaped** — straight down, straight back up in a couple of weeks | No time to shake out weak holders; overhead supply intact |
| **Too deep** — 40–50%+ in a normal market | Damage to the trend; many trapped holders above |
| **Handle / tight area in the lower half** of the base | Buyers too weak to bring it near the high |
| **Wedging** — drifting *up* on falling volume into the pivot | Fragile; often fails on the breakout |
| **Heavy-volume selling** inside the base | Distribution, not accumulation |
| **Below the 200-day** or a falling 200-day | Not Stage 2 |
| **Late stage** — base 4 or later | The move is crowded; late-stage bases often mark the top |
| **Laggard RS** — the stock bases while its group and the market run | No leadership |
| **Earnings due inside the base** | A gap can wreck a perfect pattern in one session |

## 7. How this app measures a base

The `minervini` strategy turns the description above into rules
(`core/vcp_spec.py`, documented on the Strategies page):

- **Base high** — the most recent confirmed swing high (5 bars either side,
  known only 5 bars later — no hindsight) that no *decisive* close has cleared.
  A close must clear it by about one ATR to end the base: a base's ceiling is a
  zone, not a line, so a marginal poke leaves it intact.
- **Prior advance** — the base high at least 30% above the low of the 126
  sessions before it.
- **Length** — 15 to 325 sessions (about 3 to 65 weeks).
- **Trend through the base** — the full Trend Template on the base high's bar,
  and the moving-average structure holding every day (the close may dip
  slightly under the 200-day, because a deep first contraction legitimately
  does that).
- **Base number** — 1 + the earlier bases of the same stock that produced a
  setup since the trend last broke (the moving-average structure failing for
  20 sessions in a row resets the count).

The tightness and volume steps are the VCP rules — see
[learn-vcp.md](learn-vcp.md).

## 8. What the evidence says

Read this before trusting any pattern:

- **Bases are a filter for *when* to buy, not a reason to.** Their value is a
  nearby, logical stop: if the stock falls back into the base, you were wrong
  and the loss is small.
- **This project's backtests found no reliable edge** from mechanically
  detected bases on daily data, in either market, from 2010 — see
  [minervini-spec-sensitivity-india.md](minervini-spec-sensitivity-india.md),
  [minervini-spec-sensitivity-us.md](minervini-spec-sensitivity-us.md) and the
  ledger in [momentum-trend-research.md](momentum-trend-research.md). Strict
  definitions find very few complete bases; loose ones find many that fail.
- **Context mattered more than shape.** Skipping stocks in weak industry groups
  improved the earlier Minervini version's results in both markets. Market direction matters
  too: most breakouts fail in a weak market.

So: learn to *see* bases — they organise when you act and where your stop
goes — but judge any system that trades them by its backtest, not by how good
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
