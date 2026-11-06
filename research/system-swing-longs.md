# Swing longs (draft)

Part of [my trading system](system-overview.md). Which stocks to buy, on which pattern, how to enter, and how to manage
them. Every rule is *proposed*, with its source; the status column says what this repository has measured. Size always
comes from the [daily market review](system-daily-market-review.md) and [risk and exposure](system-risk-exposure.md).

**In short**

- Candidates come from the **Stage 2 Trend Template**, strong relative strength and leading groups; in a decline, the
  same plus Minervini's five things — kept as a **watchlist**, because "held up best" alone has not paid here.
- Eight setups are on the table, from the classic base breakout to a fast rebound's first pullback. Two have been
  tested here: the base breakout showed little edge on its own, and the fast rebound's first pullback none (rejected).
- Enter at the pivot on a buy-stop; don't chase gaps or extended stocks; the stop goes under the base's tight area.
- Management depends on the kind of move: **scale out of a quick "tradable" move**, **hold a true leader** — and don't
  take quick partials just because a trade went fast (Luk).

---

## 1. When to look

| Daily-review row | Long activity |
|---|---|
| Confirmed uptrend, broad | Full: base breakouts in leading groups |
| Uptrend, narrowing | Only the best setups in the strongest groups |
| Correction in one area | Watchlist; buy only in groups that are not breaking |
| Broad correction / bear | None — build the watchlist (§2.2) |
| Bottoming | Probes in predictive and coincident setups |
| Recovery confirmed | Step up; confirming setups and higher pivots |

The **windows around a market low** (Minervini): *predictive* setups form before the low and some break out early —
when the market makes another leg down they either fail or pull back to the pivot without stopping you out; *coincident*
setups cluster around the follow-through day; *confirming* setups break out as the market builds its right side. Missing
the low still leaves the right-side build-out ([notes](creator-mark-minervini.md) §2.2).

## 2. Candidates

### 2.1 Always

- **Stage 2**: the Trend Template — all criteria ([SEPA and the VCP](learn-strat-vcp-sepa.md)).
- **Relative strength**: a high RS rank; an RS line at or near a new high ([relative strength](learn-price-rs.md)). In India,
  the RS line *and* price at a 52-week high together was the best month-end combination measured here (§4.4 there).
- **Group**: one of the three to five leading groups ([sector playbook](sector-analysis-playbook.md)).
- **Liquidity** per the strategy floors.

### 2.2 In a decline — the watchlist (Minervini's five things)

1. Fell least: within 25% of the 52-week high, preferably at new highs.
2. Building a base while the market falls.
3. The fastest rebound to new highs off the low.
4. A recent IPO forming its first base.
5. A proliferation of all four.

**Status: watchlist only.** In three recent sell-offs the stocks that held up best did *worse* than the average stock
afterwards, and early new highs did no better ([relative strength](learn-price-rs.md) §4.3). Strength in a decline was
mostly sector and low beta. The setup and the feedback decide, not the list.

## 3. Setups

| # | Setup | Entry | Stop | Source | Status here |
|---|---|---|---|---|---|
| L1 | **Base breakout** — VCP, cup with handle, flat base | Buy-stop just above the pivot; volume ≥ 1.4× average on the day; no more than 5% past the pivot | Under the tight area's low | Minervini | **Tested**: the `minervini_spec` strategy — expectancy within a few hundredths of R of zero; better with the market filter |
| L2 | **Cheat / low cheat** — an early pivot inside the base | Buy-stop over the cheat area's high | Under the cheat low | Minervini | In the same strategy (MV-03 / MV-04) |
| L3 | **Fast rebound, first pullback** — reclaims new highs within days of the market low, then pauses | As the first pullback turns back up | Under the pullback low | Minervini (Cisco 1990, DocuSign and Teladoc 2020) | **Rejected** ([event study](minervini-fast-rebound-study.md), 14 US lows 2001–2025, 13 India lows 2006–2025). Entries did no better than Stage 2 stocks bought the same day (6-month median excess −1.0% to +0.9% over 18 settings, no \|t\| above 1.5), trailed the index by about 2–3 points, and did no better than buying the same stock at its new high (India: about 3 points worse). Median trade −1R; mean −0.02R in the US. His winners are in the sample, as the tail. Keep the fast rebound as a watchlist cue (§2.2), not a setup |
| L4 | **IPO primary base** coming off a correction | Pivot of the first base after listing | Under the tight area | Minervini, quoting David Ryan | Untested; needs listing dates |
| L5 | **Failure reset** — a base fails and undercuts, then rips back, makes higher lows while the market makes lower lows, and tightens | Breakout of the new base; a small gap near the base is acceptable | Under the new tight area | Minervini (Dick's 2002–03) | Untested |
| L6 | **Higher, tighter pivot** — a second pivot higher in the same base | New entry, or an add | Under the new tight area | Minervini (Ollie's 2016) | Untested |
| L7 | **Lead and rest** — a stock that ran far during the decline bases while the market catches up; its RS line lags | Base breakout; the RS-line lag is *allowed* here | Under the tight area; cut fast if no follow-through | Minervini (Netflix 2009) | Untested |
| L8 | **Anchored-VWAP pullback** in an uptrend | First try where the hourly line is touched; second try at the daily line after an intraday breakout | Under the try's low | Luk (SK Hynix); [VWAP](learn-strat-vwap.md) Strategy C | The daily version is in the Learn guide; untested here |

## 4. Execution

- **Buy-stop at the pivot**, set the evening before (the [app manual](app-guide-pages.md) §11 routine).
- **No chasing**: not a gap, not more than 5% past the pivot. *Exception (Minervini):* a gap that stays close to the base.
  *Lesson (Minervini, BLTE):* passing on a gap is fine; failing to re-enter a few days later when it sets up again is the
  mistake.
- **"The right price, not the lowest price"**: buy where the stock should move quickly, so a wrong trade shows itself fast.
- **Intraday triggers** (Luk; [Kullamägi](learn-strat-kullamagi.md)): a lower-timeframe candle or opening-range break gives a
  tighter stop but more stop-outs. Choose the trigger timeframe by the stop width I can accept, not by which signal "works".

## 5. Management and exits

The two creators disagree on partial profits, and both are right for different moves:

| Situation | Rule | Source |
|---|---|---|
| A cyclical or "tradable" move — 30–50% in a couple of weeks, no new growth story | Scale out into strength | Minervini (PBF, 2022) |
| A trade goes several R in my favour within hours | **No** quick partials: a fast move is a reason to hold for the bigger swing | Luk |
| A true leader (new product, earnings growth, leading group) | Hold for the trend; add at a higher, tighter pivot | Minervini; Ritchie held longer and made more |
| A gap-up in my favour | Sell some into the gap | Luk |
| Kullamägi's default | Sell a third to a half after 3–5 days; trail the rest on a close below the 10- or 20-day | [Kullamägi](learn-strat-kullamagi.md) |
| Missed the first base | Wait for the second or third; late-stage bases can give faster, blow-off profits | Minervini |

*Proposed decision rule:* at entry, label the trade **tradable** or **leader**. Tradable → scale out into strength; leader →
hold and trail. Never take a partial only because a trade went fast.

## 6. What to test next

| Idea | How, on stored daily data |
|---|---|
| ~~L3 fast rebound~~ | Done 4 Nov 2026: [event study](minervini-fast-rebound-study.md) — no edge over Stage 2 stocks bought the same day, over the index, or over buying at the new high; rejected |
| L5 failure reset | A base whose pivot fails and undercuts, followed within 30 sessions by higher lows while the index makes a lower low |
| Tradable vs leader labelling | Split past base breakouts by group (cyclical vs growth) and compare the scale-out exit with the trailing exit |
