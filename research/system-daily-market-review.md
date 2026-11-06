# Daily market review (draft)

Part of [my trading system](system-overview.md). Ten to fifteen minutes after the close, ending in a **written decision**
— not a mood. Every rule is *proposed* until I adopt it, and each names its source. The page-by-page routine in the app
manual ([§11](app-guide-pages.md)) shows where to read things; this page says what they mean and what to decide.

**In short**

- Review the same instruments every day: for the US, **SPY, QQQ, IWM, RSP (equal-weight), the leading sector ETF and the
  VIX**; for India, **Nifty 50, Nifty 500, Nifty Midcap 150, India VIX and FII/DII flows**.
- Answer seven questions in order — trend, stretch, breadth, volume, leadership and setup supply, volatility and events,
  my own results — then pick a row of the **decision table** (§4).
- The output is one line: **rung, bias, risk tier, what to hunt, event flags**. It goes in the daily journal.
- Four overrides can only *reduce* risk: index **stretched** in the trade's direction, a **scheduled event**, **poor recent
  results**, and **a hot streak**.
- Worked example (§5): 2 November 2026 — a semis-led drop with the average stock still healthy.

---

**What this review is for.** Swing decisions, not day trades: it is done after the close, and it sets how much risk,
on which side and in which setups for the *next* session's swing entries, and whether open positions should be cut. The
readings it starts from are on Today → **Market readings** (the market snapshot); the setups it points to are the
strategies' live setups on Today → **Today's setups**. See [what the system trades](system-overview.md) §1.

## 1. The output

```
US 2026-11-02 → for 3 Nov
Rung: Reduced | Bias: short-selective (semis, high beta) | Risk: probe until QQQ retests its 9-day EMA
Hunt: shorts on bounces into falling 9/21-day EMAs in the breaking group; long watchlist of stocks holding near highs
Events: US Election Day — no full-size entries; cut exposure into a weak close
```

The five fields, defined:

| Field | Values | Set by |
|---|---|---|
| **Rung** | Full · Reduced · Minimal · Probe | §4 decision table |
| **Bias** | Long · Long-selective · Mixed · Short-selective · Flat | §4 |
| **Risk tier** | Normal · Reduced · Probe | §4 and the overrides (§4.2) — see [risk and exposure](system-risk-exposure.md) |
| **Hunt** | Which setups to look for today | §4, then the [swing longs](system-swing-longs.md) or [shorts](system-shorts.md) page |
| **Events** | Anything scheduled that can gap the market | Q6 |

## 2. What to review

### US

| Instrument | What it stands for | Why it is on the list |
|---|---|---|
| SPY (S&P 500) | The benchmark | Trend and regime |
| QQQ (Nasdaq 100) | Large-cap growth | Where most momentum leaders live; leads both ways |
| IWM (Russell 2000) | Small caps | Risk appetite; a divergence from QQQ says the move is narrow |
| **RSP (equal-weight S&P 500)** | The average large stock | **Narrow vs broad**: the cap-weighted index can fall on a handful of giants while the average stock holds (Luk, 3 Nov) |
| The leading sector's ETF (now SMH / SOXX semis, IGV software) | Leadership | A leadership break shows here first |
| VIX | Expected volatility | Size tier; above 25 is this repository's US high-volatility threshold |

### India

| Instrument | What it stands for | Why |
|---|---|---|
| Nifty 50 | Large caps | The headline |
| Nifty 500 | The broad market | The benchmark used here |
| Nifty Midcap 150 | Mid caps | Where most swing candidates are — "the Nifty is not the market" ([index trend](learn-health-trend.md) §6) |
| India VIX | Expected volatility | Above 20 is this repository's India high-volatility threshold |
| FII / DII net flows | Foreign vs domestic money | Context for gaps; stored daily from late October 2026 |

Both: the breadth readings (rising vs falling, new highs vs lows, share above the 50-day) and the sector table.

## 3. Seven questions, in order

**Q1. Trend — what regime?** Each index against its 50-day and 200-day averages (30-week on the weekly chart), and the
slope of each. Name the stage: 2 (rising), 3 (topping: flat, wide swings), 4 (falling). *Source:* [index
trend](learn-health-trend.md); Luk on the 2021–22 Stage 3 → 4 analogue (a long uptrend, a sideways year, then a decline).

**Q2. Stretch — is the index extended in the direction I want to trade?** Distance from the 9- and 21-day EMA on the
daily chart, and the 9 EMA on the hourly. Then the weekly 9, 21 and 50 EMAs as the higher-timeframe levels.
*Rule (proposed, Luk):* if the index is stretched in the trade's direction, don't add in that direction today — wait for
it to retest its 9 or 21 EMA (hourly first, daily second), because single stocks bounce with the index. A weekly 50 EMA
under a falling sector is "a pretty strong support": shorts there are smaller. *Tested (§6):* "stretched" is a close
**≥2% under the 9-day EMA (SPY, Nifty 50, Nifty 500) or ≥3% (QQQ)**; waiting for the retest bought shorts a better
price, but the long-side mirror failed — don't delay buys because the index is stretched up.

**Q3. Breadth — narrow or broad?** Compare the cap-weighted index with the equal-weighted one (SPY vs RSP; Nifty 50 vs
Nifty 500 and Midcap). Then rising vs falling stocks, new highs vs lows, and the share above the 50-day. Which sectors are
breaking? Is there **panic** — an acceleration down, a washout — or just a grind? *Source:* Luk wants panic and broadening
before calling a bear market; [breadth](learn-health-breadth.md) §6 for washout readings. *Tested (§6):* narrow vs
broad has not forecast the index's next 1–6 months — read it as *where* the selling is, not *how much* comes next.

**Q4. Volume — is there selling, or a turn?** Distribution days on SPY, QQQ and IWM in the last 25 sessions; after a low, a
follow-through day. *Source:* [distribution and follow-through](learn-health-distribution.md): eight or more distribution
days is the unusual reading; about a third of follow-through days fail within five weeks, so one is **permission to buy
small**, not a prediction.

**Q5. Leadership and setup supply — what is the market offering?**

- Long side (Minervini): how many stocks pass the Trend Template, and is the count **rising or falling**? How many RS lines
  are making new highs out of bases? How many quality setups today, in how many groups (true leadership is three to five
  groups)? Are the most recent breakouts **working**?
- Short side (Luk): how many Stage 4 or breaking stocks are bouncing into falling short averages, and in which groups?
- *Caution (tested here):* "held up best in the sell-off" is not, by itself, a buy signal — such stocks did worse than
  average after three recent sell-offs ([relative strength](learn-price-rs.md) §4.3). Use it as a watchlist, and let the
  breakout and the feedback decide.

**Q6. Volatility and events — how big can a gap be?** VIX / India VIX against its threshold and its direction. Any
scheduled event in the next session: central-bank decisions, CPI, elections, results of the biggest index weights.
*Rule (proposed, Luk):* on an event day, no full-size new positions, and reduce into a weak close.

**Q7. My own results — is the market paying me?** Net R of my last 10 closed trades; losses in a row; how the last month
went. *Rules (proposed):* poor recent results → pilot size whatever the market looks like (Minervini; the repository's
progressive exposure); a strong month → raise size more slowly than equity (Luk).

## 4. The judgement call

### 4.1 The decision table

Pick the row that fits Q1–Q5 best; then apply the overrides.

| State | Typical evidence | Rung | Bias | Risk tier | Hunt |
|---|---|---|---|---|---|
| **Confirmed uptrend, broad** | Indexes above rising 50- and 200-day; equal-weight confirms; setup count rising; breakouts working | Full | Long | Normal | Base breakouts in leading groups ([swing longs](system-swing-longs.md)) |
| **Uptrend, narrowing** | Cap-weighted up, equal-weighted lagging; distribution building; fewer new highs | Reduced | Long-selective | Normal on the best setups only | Leaders only; tighten stops on laggards |
| **Correction in one area** | One sector breaking (e.g. semis −25%), the average stock near its highs | Reduced | Mixed | Probe on new shorts; normal on longs in strong groups | Shorts on bounces in the breaking group; watchlist of stocks holding near highs |
| **Broad correction / bear** | Indexes below a falling 50-day, Stage 3 → 4, breadth weak, panic days | Minimal (long) | Short-selective | Normal on short bounces, none long | Shorts into falling 9/21-day EMAs ([shorts](system-shorts.md)); build the "sore thumbs" list |
| **Bottoming** | A lower low in the index but the setup count rising; stocks bottomed first; a follow-through day | Probe | Long-probe | Probe | Predictive and coincident setups; the first pullback after a fast rebound |
| **Recovery confirmed** | A string of early breakouts working; no distribution after the follow-through day | Step up one rung at a time | Long | Normal | Confirming setups; higher, tighter pivots |

*Sources:* the rungs follow the [index trend](learn-health-trend.md) §8.1 exposure ladder; the bottoming and recovery
rows follow Minervini's predictive / coincident / confirming windows; the correction rows follow Luk.

### 4.2 Overrides — they can only reduce

| Override | Trigger | Effect | Source |
|---|---|---|---|
| **Stretch** | The index is stretched in the trade's direction (Q2) | No adds in that direction today; wait for the retest | Luk; tested — holds for shorts, not for longs (§6) |
| **Event** | A scheduled event can gap the next session (Q6) | No full-size entries; cut into a weak close | Luk |
| **Feedback** | The last 10 closed trades are net negative, or two losses in a row (Q7) | Pilot size (half risk) | Minervini; the repository's progressive exposure |
| **Hot streak** | A strong month just ended (Q7) | Size grows more slowly than equity | Luk |
| **Data** | Data health is not current | No orders from today's setups | App manual §11 |

## 5. Worked example — US, close of 2 November 2026 (for 3 November)

**The readings**

| Question | Reading | Source |
|---|---|---|
| Q1 Trend | SPY 1.7% under its 50-day EMA, 3.1% above its 200-day; QQQ 5.6% under its 50-day, sitting on its 200-day (+0.2%); IWM on its 21-day | Stored prices |
| Q2 Stretch | **QQQ 3.7% under its 9-day EMA**; SPY 1.5%; IWM at its 9-day. Weekly: IWM on its 9/21 EMAs; SOXX and SMH on their weekly 50 EMA | Stored prices |
| Q3 Breadth | **Narrow.** Semis 24–31% off their highs (SMH, SOXX), software 12% (IGV) — but **RSP 1.3% from its high**, above all three EMAs. Of the 1,000 most-traded stocks, 601 rose and 397 fell; 47 new highs vs 20 lows; 57% above the 50-day | Stored prices and breadth |
| Q4 Volume | Distribution days in 25 sessions: QQQ 8, SPY 7, IWM 5 | Stored prices |
| Q5 Leadership | The AI and semis leaders breaking: AMD 28%, MU 27%, SNDK 54% off their highs. Energy (XLE) still on its 21-day and above its 50-day | Stored prices |
| Q6 Events | VIX 21.1, up from 16.9 on 28 October (under the 25 threshold). **3 November: US Election Day** | Stored VIX; calendar |
| Q7 Results | (personal) | — |

**The call:** row 3, *correction in one area*. Rung **Reduced**; bias **short-selective** in semis and high-beta names;
risk tier **probe** on new shorts, because the **stretch** override applies (QQQ far under its 9-day EMA) and the **event**
override applies (Election Day). No new longs: the average stock is fine, but long setups need broadening first.

**What the two creators did with the same picture**

- *Luk (that day):* exactly this — a short bias, but "today may not be the best day for the shorts"; two probes in SK Hynix
  at 0.02–0.1% risk; all new shorts under 20% size; waiting for QQQ to retest its 9 EMA; ready to cut exposure into a weak
  close. ([notes](creator-martin-luk.md) §2, §6)
- *Minervini (his 2022 playbook):* "chicken camp" — no full positions; run the Trend Template count and the RS-line screen;
  list stocks holding within 25% of their highs while QQQ falls; wait for proliferation and a follow-through day.
  ([notes](creator-mark-minervini.md) §2)

## 6. What is tested and what is not

| Rule | Status |
|---|---|
| Be less invested when the index is weak (a market filter) | **Tested** — the one rule here that improved return and drawdown together ([strategy families](app-guide-strategy-families.md) §5) |
| Size by recent results (progressive exposure) | **Tested** — cut the US drawdown on its own; overlaps with the market filter rather than adding to it ([Minervini notes](creator-mark-minervini.md) §9.2) |
| A follow-through day as permission, not prediction | **Measured** — about a third fail within five weeks ([distribution guide](learn-health-distribution.md)) |
| "The stocks that held up best will lead" | **Contradicted** in three sell-offs ([relative strength](learn-price-rs.md) §4.3) — watchlist only |
| The stretch override, short side (wait for the 9-day EMA retest) | **Tested — supported as a timing rule** ([rule tests](daily-review-rule-tests.md) §2). After a close ≥2% under the 9-day EMA (SPY, Nifty 50, Nifty 500) or ≥3% (QQQ), shorting weak stocks at their first close back under their own 9-day EMA *after* the index retests its 9-day beat shorting on the stretched day by about +1.3 to +1.6 points (US) and +1.5 to +3 (India) to a common exit, against ~0 to +0.65 on ordinary days. It buys a better price, not a better trade; SPY's 2% version did not repeat in 2022–2026. The US index does bounce (QQQ ≥3%: 5-day mean +2.0%, 73% up); the Nifty does not. Hourly retest and weekly 50 EMA sub-rule untested |
| The stretch override, long side (don't add longs while stretched up) | **Rejected** ([rule tests](daily-review-rule-tests.md) §2.4) — the index did not pull back, strong stocks kept outperforming, and waiting to buy on a retest cost up to 2.2 points (India) |
| Narrow vs broad (cap- vs equal-weight) as a regime input | **Tested — rejected as a forecast** ([rule tests](daily-review-rule-tests.md) §3). Neither the narrow picture nor broad declines were followed by worse 1–6-month index returns than ordinary days (US); in India the sign flipped between 2009–2021 and 2022–2026. Keep it as a description: it says *where* the selling is, which decides what to hunt |
| The event override | Untested — gap sizes on scheduled event days vs other days |
| The hot-streak override | Untested — needs a personal trade log |
