# Longs — position, swing and short-term (draft)

Part of [my trading system](system-overview.md). Which stocks to buy, in which book, and — once a strategy has earned
it — how to enter and exit. **The entry and exit rules are not set yet** (§0): they will come from a tested strategy. Until
then the setups, execution and management below are *candidates under study*, each with its source and what this repository
has measured. Size always comes from the [daily market review](system-daily-market-review.md) and [risk and
exposure](system-risk-exposure.md); the stocks come from [Sectors → stocks](system-sector-selection.md).

**In short**

- Three books: **position** (months), **swing** (days to weeks) and **short-term** (1–5 days), all planned on daily bars.
  Entry and exit for each are **TBD — to be set from a tested strategy**.
- Candidates come from the **Stage 2 Trend Template**, strong relative strength and the leading and emerging groups of
  [Sectors → stocks](system-sector-selection.md); in a decline, the same plus Minervini's five things — kept as a
  **watchlist**, because "held up best" alone has not paid here.
- Eleven candidate setups, from the classic base breakout to a fast rebound's first pullback. Two have been tested
  here: the base breakout showed little edge on its own, and the fast rebound's first pullback none (rejected).
- The candidate execution and management rules — buy-stop at the pivot, no chasing; **scale out of a quick "tradable"
  move, hold a true leader** — wait for a strategy to confirm or replace them.

---

## 0. Books, and the rules still to set

| Book | Holding period | Candidates | Strategies to draw the rules from |
|---|---|---|---|
| **Position** | Months, while the trend holds | Leaders in groups leading for 4+ weeks | Minervini SEPA (its 150-day room after +3R), RS leaders, Stage analysis, 100-EMA trend, Donchian channel |
| **Swing** | Days to a few weeks | Leaders in leading and emerging groups | Minervini SEPA, Minervini coil breakout, Trend pullback, EMA pullback, Kullamägi breakout, Kell cycle, Chart patterns, Darvas box, Earnings gaps |
| **Short-term** | 1–5 sessions | The fastest movers in the week's strongest groups | Momentum burst (a time stop after a few sessions) |

Each strategy's page (Strategies) shows its rules and its measured result by stage; most have not passed a verify run. A
setup in §3 becomes a strategy when it can be coded; a strategy becomes the rule here when it passes.

> **Entry — TBD.** To be set from a tested strategy, one per book. Until then, a trade taken is a candidate setup from
> §3, sized as a probe or at reduced risk ([risk and exposure](system-risk-exposure.md) §1), and logged.
>
> **Exit — TBD.** To be set from the same strategy: the initial stop, the trailing or time exit, partial sales. The
> candidate rules are in §5. Whatever the exit, the stop is set before entry and never moved against the trade.

**Short-term is on daily bars.** A 1–5 session trade is planned at the close like any other; no position is opened and
closed in one session. Intraday trading is a separate decision, deferred ([overview](system-overview.md) §1).

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
- **Group**: a leading or emerging group from the weekly [Sectors → stocks](system-sector-selection.md) list.
- **Liquidity** per the strategy floors.
- **A glance first: the chart's Trend-health bands** (the platform-style strips Minervini's team trade from, §12.4 of the
  [Minervini note](creator-mark-minervini.md); explained in [trend indicators](learn-ind-trend.md), "Trend-health bands").
  How to read each, from what was measured on liquid stocks 2014–2026 (next 3 months vs the average stock):

  | Strip | Use it as | Measured |
  |---|---|---|
  | Trend Template (criteria met of 8; the 50-day above the 150- and 200-day counts for C4 without waiting for the 150-day to cross the 200-day) | **The filter**: red (0–5) is a pass, whatever the pattern | Red lagged in both markets (US −0.3%, India −0.9%); 8 of 8 led in India (+1.1%), weakly in the US (+0.5%, not significant) |
  | Buy risk (close and 21-day EMA vs the 50-day; green above both, amber one, red below both) | **Entry check**, read from the % above the 50-day in its tooltip, not the colour: close below the 50-day, no new buy; over 25% above it, no chase. Green covers extended stocks too | Red and amber lagged in India (−0.4%, −0.5%), barely in the US (−0.1%); inside green, US stocks over 25% above the 50-day lagged −3.0%, India's did not (+0.1%), so not a sell signal |
  | Pressure (up ÷ down volume, 20 days; green at 1.0 or more, red below) | **A reason not to add**, never a reason to sell | Mostly repeats RSI (0.71); no forward difference: green and red both within 0.1% of the average in both markets |
  | RS rank (1–99, weekly; green 70+, amber 50–69, red below 50) | The relative-strength check above: green for a leader; in India, red is a pass | Sorted India strongly (green +1.8%, red −1.0%), the US weakly (green +0.6%, red −0.2%); a stock too new to rank lagged in both (US −3.3%, India −1.7%) |

### 2.2 In a decline — the watchlist (Minervini's five things)

1. Fell least: within 25% of the 52-week high, preferably at new highs.
2. Building a base while the market falls.
3. The fastest rebound to new highs off the low.
4. A recent IPO forming its first base.
5. A proliferation of all four.

**Status: watchlist only.** In three recent sell-offs the stocks that held up best did *worse* than the average stock
afterwards, and early new highs did no better ([relative strength](learn-price-rs.md) §4.3). Strength in a decline was
mostly sector and low beta. The setup and the feedback decide, not the list.

## 3. Setups under study (candidates, not rules)

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
| L9 | **Pause pivot** — a strong stock (RS near the top) pulls back in three or four lower lows after a power move, then pauses; buy the break of the pause | Over the pause's high | Under the pause low | Ritchie/Hedgepath (Vicor, Dec 2025; Arm, May 2026) | Untested; our detector refuses it (VCP-08 tightness) |
| L10 | **Pullback buy after a missed breakout** — a low-volume 1-2-3 pullback to the cheat area or the 50-day, then an inside day or a turn | Over the inside day's (or the prior day's) high — bought as it turns up, never on the way down | Under the pullback low; out in 5–10 sessions if it does not work | Ritchie/Hedgepath (Fluence, Modine 2026); Minervini (ANF, Jan 2021: skipped the first breakout as "wedging", bought the pullback to the top of the low cheat as it cleared Friday's high) | Untested; our detector refuses Modine (VCP-06), but catches ANF on the same day as a near-miss VCP (S7) |
| L11 | **First setup after a new all-time high out of a multi-year base** — may come before the Trend Template is met | The first tight setup above the old high | Under the setup | Ritchie (Arm), Weissman (IREN, Aug 2025) | Untested; refused by the Trend Template's stacked averages (G4) |

## 4. Execution — candidate rules

- **Buy-stop at the pivot**, set the evening before (the [app manual](app-guide-pages.md) §11 routine).
- **No chasing**: not a gap, not more than 5% past the pivot. *Exception (Minervini):* a gap that stays close to the base.
  *Lesson (Minervini, BLTE):* passing on a gap is fine; failing to re-enter a few days later when it sets up again is the
  mistake.
- **"The right price, not the lowest price"**: buy where the stock should move quickly, so a wrong trade shows itself fast.
- **Intraday triggers** (Luk; [Kullamägi](learn-strat-kullamagi.md)): a lower-timeframe candle or opening-range break gives a
  tighter stop but more stop-outs. Choose the trigger timeframe by the stop width I can accept, not by which signal "works".

## 5. Management and exits — candidate rules

The two creators disagree on partial profits, and both are right for different moves:

| Situation | Rule | Source |
|---|---|---|
| A cyclical or "tradable" move — 30–50% in a couple of weeks, no new growth story | Scale out into strength | Minervini (PBF, 2022) |
| A trade goes several R in my favour within hours | **No** quick partials: a fast move is a reason to hold for the bigger swing | Luk |
| A true leader (new product, earnings growth, leading group) | Hold for the trend; add at a higher, tighter pivot | Minervini; Ritchie held longer and made more |
| A gap-up in my favour | Sell some into the gap | Luk |
| Kullamägi's default | Sell a third to a half after 3–5 days; trail the rest on a close below the 10- or 20-day | [Kullamägi](learn-strat-kullamagi.md) |
| Missed the first base | Wait for the second or third; late-stage bases can give faster, blow-off profits | Minervini |
| Up 15–20% before the first natural reaction | Sell a third or a quarter "to finance the risk", so the rest can sit through the reaction | Ritchie/Hedgepath (Seagate, Modine, Arm) |
| A news or earnings gap up while well in profit | Backstop at the gap day's low; ratchet it up as the move goes vertical; no resting trailing stop | Ritchie/Hedgepath (Modine, Micron 2026) |
| Results due | Never hold an overweight position into them; hold a remainder only with profit banked | Ritchie/Hedgepath (Broadcom, Dec 2025) |
| Last piece of a winner | Close below the 50-day, ratcheted higher once enough is made | Ritchie/Hedgepath (Seagate) |
| A winner pulls back to the top of its pivot or to the 20-day (a natural reaction) | **Add** as it turns up over the prior day's high; stop on the add under the reaction low. Different from adding at a new, higher pivot | Minervini (ANF, Feb 2021: two adds) |
| One to three natural reactions done, and the advance accelerates | Sell into the strength | Minervini (ANF) |
| A new trade starts weak — a heavy-volume reversal, a close back below the pivot, or a run of down days | **Hold to the stop**; do not add, and watch it. Selling early helped the two cases that raised it (Manappuram, Marico 2018), but lowered the average in every replay (§6) | Minervini lists these as violations; measured here |

*Proposed decision rule:* at entry, label the trade **tradable** or **leader**. Tradable → scale out into strength; leader →
hold and trail. Never take a partial only because a trade went fast.

## 6. What to test next

| Idea | How, on stored daily data |
|---|---|
| **Minervini trade-review batch (1.66)** | Queued 11 Nov 2026, optimise 2013–2021 ([trade reviews](minervini-trade-reviews.md)). 13 losing trades reviewed on the chart gave lessons L1–L4 and bugs F1–F3; a script then checked all 177 India and 909 US trades of the 1.63 runs (winners too, stored in `trade_reviews`). That **overturned L2** (a base right after a climax run: better than the rest in India, worse in the US) and **L3** (light crossing volume: no split). Carried: **L1**, re-buy a failed breakout's base when it is reclaimed (79 of 105 Indian and 432 of 558 US losers were reclaimed within 60 sessions, the run re-bought 11; 42 and 155 then gained 20%+); **L4**, skip a cheat bought within 3% of the 50-day (11% and 25% won against 44% and 40%); fixes **F1** (results on the signal day pass the blackout), **F2** (a flat base's pivot ignores a fresh higher high), **F3** (a resting order fills inside the results window). Shared batch #1532–1545 on 1.64's rules; US-only batch #1548–1554 on candidate D's lean exits (D′). Pass rules fixed first: a lesson must raise CAGR in both markets with drawdown ≤1 point deeper; fixes kept unless CAGR falls in both. **Shared result: nothing adopted.** Baseline reproduced #1517/#1518 exactly (India 10.31% / −18.0%, US −0.13% / −35.8%). L4: India +0.46, US −1.99 with drawdown 6 points deeper — fails. L1: no variant of the four raised CAGR in both markets (best India +0.65 with drawdown 2.4 deeper, best US +0.05) — fails. Fixes together: India −3.55, US −1.74 — off, untold which of the three costs. 1.66 keeps every switch off; the US D′ batch is still running. For me: one trade is an anecdote — five hand-picked losers said L2, all 1,086 trades said no |
| ~~Minervini 1.64 verify~~ | **Passed (India), 11 Nov 2026** ([CAGR gaps](minervini-cagr-gaps.md)), 2022 → today, once each. 1.64 = candidate B (no near-miss setup S7; the trend exit moves to the 150-day after +3R; new buys also need the small- and mid-cap index up over 3 months) + the 8% stop cap. Criterion fixed before the run: India CAGR above 0, average trade above 0R, max drawdown no deeper than −25%. India 6.38% CAGR / −10.9%, +0.23R over 201 trades, PF 1.28 (1.53 rules: 2.18% / −25.7%). US, reported: −3.36% / −17.4%, −0.06R (1.53 rules: −1.33% / −26.6%). Neither beats the index (India 9.46%, US 9.74%). India's gain rests on four 2023 leaders held 11–20 months by the 150-day exit (+14R to +30R); the other 197 trades lost. For me: the edge is in holding the rare big winner, so the 150-day room after +3R is the rule to keep; the next clean test is paper trading |
| ~~L3 fast rebound~~ | Done 4 Nov 2026: [event study](minervini-fast-rebound-study.md) — no edge over Stage 2 stocks bought the same day, over the index, or over buying at the new high; rejected |
| L5 failure reset | A base whose pivot fails and undercuts, followed within 30 sessions by higher lows while the index makes a lower low |
| Tradable vs leader labelling | Split past base breakouts by group (cyclical vs growth) and compare the scale-out exit with the trailing exit |
| ~~Gap-day backstop~~ | Done 11 Nov 2026 ([CAGR gaps](minervini-cagr-gaps.md); [Minervini note](creator-mark-minervini.md) §12.3): built as switch 1.60, optimise runs #1419–1425. It lowered CAGR in every pairing, in both markets — with the 150-day exit, from +3R India 8.26% → 5.77%, US 3.08% → −0.58% (+2R worse in the US); alone, India 3.71% → 2.67%, US −3.30% → −4.08%; US lean exits 5.02% → 1.13%. India's drawdown about 5 points shallower, but a filled gap is a normal day for a leader, so it sells the winners the 150-day exit keeps. Rejected as a mechanical rule; for me, a gap-day stop only on a news gap I judge, not on every 1-ATR gap |
| Earnings rule for held positions | Before a results date, sell all if the open gain is under a cushion, else sell part; needs point-in-time results dates in the backtest |
| L9 pause pivot, L10 pullback buy | As new setups in the `minervini` strategy, research switches off, with pass criteria written first |
| Add on a natural reaction | Replayed 10 Nov 2026 on the optimise runs' trades ([Minervini note](creator-mark-minervini.md) §13.3): US −0.22R an add (+0.11R with the 150-day exit), India +0.47R (+2.85R, mostly 2020–21); 57–73% stopped at the reaction low. Worth building as a research switch in the backtest only beside the 150-day exit, and judged on India first |
| ~~Weekly volume markers~~ | Done 10 Nov 2026: no right-side distribution week, or a quiet right side, made no difference to the trades' R in either market (same section). Not a filter; the daily dry-up already covers it |
| ~~Early-weakness exits~~ | Done 10 Nov 2026 ([Minervini note](creator-mark-minervini.md) §9.3; [Stops and exits](learn-risk-stops-exits.md) §10): a close back below the pivot, the same on above-average volume, 3 or 4 down closes in a row, and more down days than up, each within 5–10 sessions. On the `minervini` optimise trades none raised the average in both markets (India +0.20R → +0.04 to +0.20; US −0.040 → −0.031 to −0.052); on ~61,000 US and ~18,000 Indian textbook breakouts every version lowered it. Rejected |
| ~~Trend-health bands as signals~~ | Done 10 Nov 2026 ([trend indicators](learn-ind-trend.md), "Trend-health bands"): each strip's colour against the next 3 months on liquid stocks, 2014–2026. Used as the read in §2.1, not as entry or exit rules; the Trend Template is already the strategy's gate, and selling on pressure was measured and rejected (early-weakness exits, above) |
| ~~Tighter stop cap~~ | Done 11 Nov 2026 ([CAGR gaps](minervini-cagr-gaps.md)): `MAX_STOP_PCT` 8 passed its rule in both markets (#1440/1442, optimise: India 3.71% → 4.15%, US −3.30% → −1.83%, drawdown shallower in both); 6 lowered CAGR in both. On candidate B it passed again (#1517–1518: India 10.31% / −18.0%, US −0.13% / −35.8%), so 8% is in 1.64. For me: skip a setup whose stop is more than 8% away, rather than taking it and hoping |
| ~~A cheat needs two pullbacks~~ | From scoring the Zydus 2014 VCP ([Minervini note](creator-mark-minervini.md) §9.4): on the strategy's own trades, only a cheat's pullback count held in both markets (1 pullback −0.02R India / −0.08R US; 2 or more +0.38R / +0.05R), but on 24 and 82 one-pullback cheats. **Textbook event study, 10 Nov 2026, contradicts it:** ~25,000 cheats rebuilt from stored prices, 2014–2026, no strategy code — 0–1 pullbacks +0.23R India / +0.02R US, 2+ shallower each time +0.17R / −0.01R, 2+ other +0.20R / +0.05R; inside the noise (±0.04R / ±0.02R), in both halves of the period and both thirds of the base ([VCP and SEPA](learn-strat-vcp-sepa.md)). Likely noise. On the strategy, `CHEAT_MIN_CONTRACTIONS` (1.63, off) passed the optimise screen narrowly (#1451–1452: India 3.89%, US −1.99%), then failed on B + the 8% cap (#1519–1520: India 10.31% → 11.22%, US −0.13% → −0.21%), so it is dropped and stays off. For me: count the pullbacks to read the chart, not as a filter. The chart's cheat frame applies the switch when it is on. No composite VCP score |
