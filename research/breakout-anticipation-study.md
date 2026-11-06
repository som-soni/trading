# Breakout anticipation: what shows up before a real breakout (US and India)

A study of which conditions, visible before a breakout, raise the odds that a stock near resistance breaks out
*and follows through* in the next four weeks. Measured against a control set (failed breakouts and bases that
never broke), tuned on 2017–2021, and checked once on 2022–2026 with rules frozen beforehand.
Run 2026-11-06. Reproduce with `analytics/breakout_study.py` (end of this note). Its result is the US-only
**Breakout watch** screen.

**In short**

- **Most standard pre-breakout lore did not discriminate.** Volatility contraction, VCP-style shrinking
  pullbacks, volume dry-up, higher lows, MA compression, shallow bases, accumulation days and a healthy index
  all scored within a few percent of the base rate, or below it, in at least one window.
- **What held up in the US:** relative strength at a new high before price, OBV at a new high, and a strong
  industry group. Combined, they hit **13.9% vs an 8.5% base rate** on the 2022–2026 hold-out, a lift of 1.63
  (95% interval 1.47–1.81), flagging 275 of 6,403 real breakouts (recall 4.3%).
- **Nothing survived in India.** Every frozen Indian rule scored a lift of about 1.0 on the hold-out. Of the
  individual signals, only OBV at a new high (1.10) and nearness to the pivot (1.13) replicated, and both are weak.
- **These signals predict that a breakout *happens*, not that it *works*.** In discovery the US rule lifted
  the chance of any breakout from 22.8% to 31.8%. The chance that a breakout followed through stayed at about 36%.
- **Use:** the US rule is a watchlist filter, not a trade signal: about 6 in 7 alerts do not become a real
  breakout within four weeks. India needs a separate, forward-tested approach.

## Why 2017–2021 and not "the last five years"

The brief asked for the last five years, Nov 2021 → Nov 2026. Those years are the project's **verify** window,
where no threshold may be chosen (CLAUDE.md, "backtests run in stages"). So discovery ran on the last five years
of the **optimise** window, 2017–2021. 2022–2026 became the out-of-sample test that Step 7 asks for: run once,
on rules frozen before any 2022+ row was read (`FROZEN` in the module), with the pass criteria written down first.

## 1. Definitions (fixed before the data)

**Breakout event, day d** (the `breakout` strategy's S1 setup and its trend gates G1–G3):

| Condition | Rule |
|---|---|
| Price | close[d] > pivot = highest high of the 55 sessions before d (`BREAKOUT_LOOKBACK`) |
| Volume | volume[d] > 1.5 × its 50-day average (`VOL_MULT`) |
| Trend | close > 200-day average; 200-day not falling (≥ 0.995 × its value 20 sessions earlier) |
| Near highs | close ≥ 0.95 × 52-week high |
| Liquidity | 20-day average traded value ≥ the market's floor (US $10M, India ₹50 crore) |

The strategy's own tight-base gate (G4) is deliberately left out: base tightness is one of the signals tested.

**Follow-through (a real breakout):** within the 20 sessions after d, a close at least 2 × ATR14 above the
breakout close comes before any close more than 0.5 × ATR14 below the pivot. Anything else (a reversal, or a
stall that reaches neither level) is a **failed** breakout.

**Candidate (the unit of observation):** the last session t of each week where the stock is liquid, above a
non-falling 200-day, between 0% and 5% below its 55-session pivot, and within 10% of its 52-week high. That is a
base near resistance, the moment an anticipation screen would look.

**Outcome:** the first breakout in sessions t+1 … t+20 (**the anticipation window**: the signal must be visible
1–20 sessions before the breakout), labelled TRUE (real), FAILED, or NONE (no breakout: the near-miss).
**Every feature uses bars up to t only.** Nothing from the breakout day or later enters a feature.

**Universe:** companies only. Indices and ETFs are excluded by requiring an industry classification; that
dropped 153 US and 38 India symbols, such as SPY, IVV and `^NSEI`. The RS line is measured against the Sectors
page's benchmark (S&P 500, Nifty 500), the same series the snapshot uses.

## 2. Samples

Breakout events (all, before the candidate filter):

| Market | Window | Breakouts | Followed through |
|---|---|---:|---:|
| US | 2017–Nov 2021 | 15,029 | 35.3% |
| US | 2022–Nov 2026 | 16,218 | 35.6% |
| India | 2017–Nov 2021 | 3,327 | 35.9% |
| India | 2022–Nov 2026 | 7,227 | 37.1% |

Candidate weeks (the study sample, and its control set):

| Market | Window | Candidate weeks | Stocks | TRUE | FAILED | NONE (near-miss) | Base rate (TRUE) |
|---|---|---:|---:|---:|---:|---:|---:|
| US | discovery | 91,547 | 1,958 | 7,527 | 13,346 | 70,674 | 8.2% |
| US | hold-out | 75,390 | 2,490 | 6,403 | 11,220 | 57,767 | 8.5% |
| India | discovery | 7,541 | 329 | 1,155 | 2,063 | 4,323 | 15.3% |
| India | hold-out | 13,766 | 736 | 2,216 | 3,738 | 7,812 | 16.1% |

The control set is FAILED + NONE. India's discovery sample is small, at 329 stocks above a ₹50 crore liquidity
floor, and that matters for what follows.

## 3. Candidate signals: priors, not findings

Every row below is a **hypothesis taken from trading literature**. Thresholds are the textbook-style values
chosen before any result was looked at. None was tuned.

| Code | Type | Signal at t |
|---|---|---|
| P1 | Price | Volatility contraction: ATR(10) / ATR(50) < 0.8 |
| P2 | Price | Range tightening: 10-session range / 40-session range < 0.4 |
| P3 | Price | VCP-style: pullback depth shrinking over [t−59, t−30] > [t−29, t−10] > [t−9, t] |
| P4 | Price | Higher lows: lowest low of each of the last three 10-session blocks rising |
| P5 | Price | Base ≥ 5 weeks: the pivot high was set ≥ 25 sessions ago |
| P6 | Price | Shallow base: pivot to 55-session low ≤ 15% |
| P7 | Price | Within 2% of the pivot |
| P8 | Price | NR7: today's range is the narrowest of 7 |
| P9 | Price | Strong closes: 5-day average close-location value > 0.3 |
| V1 | Volume | Dry-up: 10-day average volume < 0.8 × 50-day |
| V2 | Volume | Up-day volume > 1.2 × down-day volume over 50 sessions |
| V3 | Volume | A volume spike (> 2.5×) with a move < 1% in the last 20 sessions |
| V4 | Volume | OBV at or above its highest of the 55 sessions before t (while price is below its pivot) |
| V5 | Volume | A/D line up over 20 sessions while price moved within ±3% |
| V6 | Volume | ≥ 2 up days on > 1.5× volume in the last 20 sessions |
| R1 | RS | RS line (stock ÷ benchmark) up over 20 sessions |
| R2 | RS | RS line at or above its highest of the 55 sessions before t, before price clears its pivot |
| R3 | RS | 6-month return in the top 20% of liquid stocks that day |
| M1 | MA | close > 50-day > 150-day > 200-day |
| M2 | MA | 10/20/50-day averages within 3% of each other |
| M3 | MA | 50-day rising over 10 sessions |
| M4 | MA | close above the 10- and 20-day |
| K1 | Market | Index above its 50- and 200-day |
| K2 | Market | Index 50-day rising |
| K3 | Market | Breadth: ≥ 60% of stocks above their 50-day |
| K4 | Market | Industry group RS rating ≥ 70 (point in time, rebuilt from stored prices) |
| K5 | Market | Index within 5% of its 52-week high |
| D1 | India | Delivery %: 10-day average ≥ 1.1 × 50-day |
| D2 | India | A high-delivery day (≥ 1.5 × its 20-day average) in the last 20 sessions |

## 4. Results

**Lift** = P(TRUE | signal) ÷ P(TRUE). The 95% interval comes from a bootstrap over **stocks**, because one
stock's consecutive weeks are not independent. The verdict rule was fixed in advance:

| Verdict | Rule |
|---|---|
| CONFIRMED | lift ≥ 1.10, interval above 1, at least 100 true breakouts flagged |
| CONTRADICTED | interval entirely below 1 |
| UNSUPPORTED | the rest, with at least 100 true breakouts flagged |
| INSUFFICIENT | fewer than 100 flagged |

"Breakout lift" and "follow-through lift" split each signal's effect into two parts: does a breakout happen,
and does it work once it happens.

### US

| Signal | Flagged weeks (disc.) | TRUE flagged | Lift, discovery | 95% interval | Breakout lift | Follow-through lift | Lift, hold-out | 95% interval |
|---|---:|---:|---:|---|---:|---:|---:|---|
| R2 RS new high first | 8,432 | 831 | **1.20** | 1.12–1.28 | 1.21 | 0.99 | **1.21** | 1.15–1.28 |
| V4 OBV at 55-day high | 14,794 | 1,399 | **1.15** | 1.09–1.21 | 1.14 | 1.01 | **1.20** | 1.14–1.26 |
| K4 group RS ≥ 70 | 34,561 | 3,202 | **1.13** | 1.08–1.17 | 1.10 | 1.02 | 1.09 | 1.05–1.14 |
| P7 within 2% of pivot | 40,298 | 3,707 | **1.12** | 1.09–1.15 | 1.13 | 0.99 | **1.14** | 1.11–1.17 |
| R3 RS rank top 20% | 27,648 | 2,472 | 1.09 | 1.03–1.14 | 1.11 | 0.98 | 1.13 | 1.08–1.18 |
| P3 VCP contractions | 48,413 | 4,306 | 1.08 | 1.06–1.11 | 1.03 | 1.05 | 1.05 | 1.02–1.08 |
| P1 ATR contraction | 12,091 | 1,070 | 1.08 | 1.00–1.15 | 1.00 | 1.08 | **0.89** | 0.81–0.98 |
| M4 above 10 and 20-day | 67,804 | 5,902 | 1.06 | 1.05–1.07 | 1.07 | 0.99 | 1.06 | 1.05–1.08 |
| P2 range tightening | 33,417 | 2,844 | 1.04 | 1.00–1.07 | 0.98 | 1.05 | **0.95** | 0.91–0.99 |
| V1 volume dry-up | 19,997 | 1,701 | 1.03 | 0.98–1.09 | 0.99 | 1.05 | **0.90** | 0.84–0.96 |
| P4 higher lows | 52,395 | 4,401 | 1.02 | 1.00–1.05 | 1.01 | 1.01 | 0.98 | 0.95–1.00 |
| K3 breadth ≥ 60% | 63,504 | 5,245 | 1.00 | 0.98–1.02 | 1.02 | 0.99 | 1.04 | 1.01–1.07 |
| K1 index above 50 & 200-day | 80,888 | 6,603 | 0.99 | 0.98–1.00 | 1.00 | 0.99 | 1.08 | 1.06–1.09 |
| P5 base ≥ 5 weeks | 16,048 | 1,312 | 0.99 | 0.93–1.06 | 0.99 | 1.00 | 0.97 | 0.91–1.04 |
| V6 accumulation days | 28,995 | 2,295 | 0.96 | 0.92–1.01 | 1.00 | 0.96 | 1.01 | 0.96–1.05 |
| M2 MA compression | 35,624 | 2,735 | **0.93** | 0.89–0.98 | 0.95 | 0.98 | **0.93** | 0.88–0.99 |
| V5 A/D up, price flat | 19,712 | 1,513 | **0.93** | 0.88–0.99 | 0.93 | 1.00 | **0.92** | 0.85–0.98 |
| P6 shallow base (≤ 15%) | 44,054 | 3,341 | **0.92** | 0.88–0.96 | 0.94 | 0.99 | **0.83** | 0.78–0.88 |
| V3 volume spike, no move | 8,210 | 569 | **0.84** | 0.74–0.95 | 0.86 | 0.98 | **0.84** | 0.75–0.92 |

The remaining signals (P8, P9, R1, V2, M1, M3, K2, K5) sat between 0.99 and 1.05 in discovery. The module
prints the full tables.

### India

| Signal | Flagged weeks (disc.) | TRUE flagged | Lift, discovery | 95% interval | Breakout lift | Follow-through lift | Lift, hold-out | 95% interval |
|---|---:|---:|---:|---|---:|---:|---:|---|
| P9 strong closes | 662 | 122 | **1.20** | 1.03–1.38 | 1.08 | 1.11 | 1.01 | 0.90–1.11 |
| R2 RS new high first | 903 | 165 | **1.19** | 1.02–1.36 | 1.13 | 1.05 | 0.97 | 0.89–1.06 |
| V4 OBV at 55-day high | 1,525 | 268 | **1.15** | 1.04–1.25 | 1.15 | 1.00 | **1.10** | 1.02–1.19 |
| V1 volume dry-up | 1,883 | 326 | **1.13** | 1.02–1.24 | 0.95 | 1.19 | 0.91 | 0.82–1.00 |
| D1 delivery % rising | 1,331 | 225 | 1.12 | 0.99–1.24 | 0.98 | 1.14 | 0.94 | 0.79–1.08 |
| K4 group RS ≥ 70 | 2,213 | 378 | 1.12 | 0.97–1.27 | 1.09 | 1.02 | 1.02 | 0.95–1.10 |
| P7 within 2% of pivot | 2,542 | 425 | 1.09 | 1.00–1.17 | 1.09 | 1.00 | **1.13** | 1.07–1.19 |
| D2 high-delivery day in 20 sessions | 3,317 | 542 | 1.08 | 0.99–1.16 | 1.02 | 1.06 | 1.01 | 0.92–1.10 |
| K3 breadth ≥ 60% | 4,610 | 754 | 1.07 | 1.01–1.13 | 1.05 | 1.02 | 1.10 | 1.06–1.13 |
| P3 VCP contractions | 3,435 | 556 | 1.06 | 0.98–1.14 | 0.98 | 1.08 | 1.01 | 0.96–1.07 |
| P2 range tightening | 2,436 | 368 | 0.99 | 0.90–1.07 | 0.92 | 1.07 | 1.03 | 0.97–1.09 |
| P4 higher lows | 4,695 | 695 | 0.97 | 0.92–1.02 | 0.98 | 0.99 | 1.04 | 1.00–1.07 |
| P6 shallow base | 1,656 | 243 | 0.96 | 0.78–1.16 | 0.99 | 0.97 | 0.92 | 0.80–1.03 |
| V5 A/D up, price flat | 603 | 80 | 0.87 (insufficient) | 0.68–1.06 | 0.84 | 1.04 | **0.77** | 0.62–0.91 |

India's 2017–2021 sample produced four "confirmed" signals, and three of them vanished on 2022–2026. With
29 signals tested per market, one or two false confirmations at the 95% level are expected by chance alone.
India's small sample let more through.

### Combinations (discovery, then the hold-out)

Pre-stated method: a greedy AND over the market's confirmed signals, stopping when the lift gain falls below
0.05 or fewer than 100 true breakouts stay flagged. Two alternatives were frozen with it: B, one unified rule
for both markets (the two signals confirmed in both), and C, at least 2 of the market's confirmed signals.
Pass criteria (frozen): hold-out lift ≥ 1.20, interval above 1, at least 100 true breakouts flagged, and at
least half of the discovery excess lift kept.

| Market | Rule | Discovery: alerts / precision / recall / lift | Hold-out: alerts / precision / recall / lift (95% interval) | Alerts a week | Verdict |
|---|---|---|---|---:|---|
| US | **A: R2 + V4 + K4** | 1,738 / 11.3% / 2.6% / 1.38 | 1,983 / **13.9%** / 4.3% / **1.63** (1.47–1.81) | 8 | **PASS** |
| US | B: R2 + V4 | 3,398 / 10.8% / 4.9% / 1.31 | 3,488 / 12.3% / 6.7% / 1.45 (1.33–1.57) | 14 | **PASS** |
| US | C: ≥ 2 of R2, V4, K4, P7 | 26,124 / 9.7% / 33.7% / 1.18 | 22,539 / 10.2% / 35.9% / 1.2005 (1.16–1.25) | 92 | borderline |
| India | A: P9 | 662 / 18.4% / 10.6% / 1.20 | 1,588 / 16.2% / 11.6% / 1.01 (0.90–1.11) | 6.5 | FAIL |
| India | B: R2 + V4 | 449 / 20.3% / 7.9% / 1.32 | 1,253 / 16.0% / 9.0% / 0.99 (0.87–1.12) | 5 | FAIL |
| India | C: ≥ 2 of P9, R2, V4, V1 | 1,022 / 19.2% / 17.0% / 1.25 | 2,540 / 15.4% / 17.6% / 0.95 (0.87–1.04) | 10 | FAIL |

US C clears the 1.20 bar by 0.0005 here and missed it by 0.002 in the first run of the same design (on SPY
rather than the S&P 500 index). It is counted as **not a pass**: a rule that sits on the line does not earn one.

**Precision vs restrictiveness, US:**
- **Rule A** keeps about 4% of real breakouts and lifts precision from 8.5% to 13.9%.
- **Rule B** keeps 6.7% and reaches 12.3%.
- **Rule C** keeps a third, and its precision is barely above the base rate.

**Two checks on what the US signals mean:**
- *Attempts vs success.* Among discovery candidates, rule A lifted P(any breakout in four weeks) from 22.8% to
  31.8%. P(follow-through | breakout) was 36.1% without it and 35.6% with it. On the hold-out it was 36.3% vs 40.4%.
- *Not just proximity.* R2 and V4 kept their lift both within 2% of the pivot (discovery 1.12 and 1.10) and
  further away (1.14 and 1.06).

## 5. What the data showed vs what the knowledge base assumed

**(1) Confirmed by this data** (discovery and hold-out, adequate samples)
- **US — RS line at a new high before price (R2):** 1.20 discovery, 1.21 hold-out; 831 and 991 true breakouts flagged.
- **US — OBV at a 55-session high (V4):** 1.15 and 1.20; 1,399 and 1,241 flagged.
- **US — within 2% of the pivot (P7):** 1.12 and 1.14. Nearly mechanical, but it works.
- **US — the combination R2 + V4 + K4:** 1.38 and 1.63; 196 and 275 flagged.
- **India — none as a rule.** OBV at a new high (1.15, 1.10) and nearness to the pivot (1.09, 1.13) replicated
  weakly. Neither clears the bar in both windows.
- **Weak but real, US:** RS rank (1.09, 1.13) and group RS (1.13, 1.09) are real effects but small.

**(2) Contradicted or unsupported, despite being standard lore**
- **MA compression:** US 0.93 in both windows (contradicted). India 1.00 in discovery, 0.92 on the hold-out.
- **Shallow base (≤ 15%):** US 0.92 / 0.83 (contradicted). Shallower bases broke out *less* often. India ~0.96.
- **Volume spike without a price move:** US 0.84 / 0.84 (contradicted).
- **A/D line rising while price is flat:** US 0.93 / 0.92 (contradicted). India 0.77 on the hold-out.
- **Volatility contraction (ATR) and range tightening:** US 1.04–1.08 in discovery, then *below* 1 on the
  hold-out (0.89, 0.95). India ~1.0. They nudge follow-through slightly (1.05–1.08) and attempts not at all.
- **VCP-style shrinking pullbacks:** US 1.08 / 1.05, India 1.06 / 1.01. Small, below the bar.
- **Volume dry-up:** US 1.03 then 0.90. India 1.13 then 0.91.
- **Higher lows, base ≥ 5 weeks, accumulation days, MA stack, 50-day rising:** all within ±0.06 of 1.
- **Market context:** the index trend (K1, K2, K5) and breadth (K3) scored ~1.00 in discovery. They predict
  nothing *between* candidates. That does not test whether a weak market produces *fewer* candidates, which it
  may; this design measures lift among stocks already near a pivot.
- **India's delivery %:** rising delivery (1.12, interval 0.99–1.24; hold-out 0.94) and a recent high-delivery
  day (1.08; 1.01) both unsupported.

**(3) Plausible but untestable here**

| Signal | Data needed |
|---|---|
| Upper-circuit behaviour in India (stocks pinned at the band) | Daily NSE price-band file (band % per stock per day) |
| Earnings or news catalysts in the window | Point-in-time scheduled results dates. Stored results exist but were not tested in this pass |
| Institutional accumulation (13F, FII/DII holdings) | Point-in-time ownership history |
| Intraday volume profile and opening-range behaviour | Intraday bars |
| Short interest and squeeze potential (US) | Point-in-time short interest |
| Options open interest and call skew | Point-in-time options chain history (India F&O bhavcopy is stored; not used here) |
| Float and supply | Point-in-time free float |

## 6. India vs the US

- **The confirmed set differs.** RS at a new high and the three-signal rule work in the US and fail in India.
- **The bases look different.** The median candidate week before a real breakout was 6 sessions after the
  pivot high in the US and 4 in India. A 5-week-plus base preceded 17% of US and 13% of Indian real breakouts.
- **Follow-through is similar:** 35–37% of breakouts in both markets.
- **The sample decides the verdict.** India's discovery sample (329 stocks, 1,155 true breakouts) is a tenth of
  the US one. That is enough to confirm a lift above about 1.15–1.20, not to tell a real 1.10 from noise.
- **Verdict:** a single unified rule is **not justified**. The unified R2 + V4 passed in the US (1.45) and failed
  in India (0.99). India needs its own, forward-tested approach, not US thresholds.

## 7. The anticipation screen: Breakout watch (US only)

Built as the preset `breakout_watch` in `screens/definitions.py`, on three new point-in-time snapshot fields:
`pivot_55`, `rs_line_high` and `obv_high` (screens/snapshot.py `_leads`, computed by the same `core/indicators`
functions the study uses). `tests/test_breakout_watch.py` checks that the snapshot's values equal the study's
on every bar. Evaluated on each session's snapshot:

1. **Candidate:** tradable (the market's price and liquidity floor); close > 200-day average; 200-day not
   falling; close below the 55-session pivot and at least 95% of it (`BREAKOUT_WATCH_MAX_PCT_BELOW_PIVOT`);
   close ≥ 90% of the 52-week high (`BREAKOUT_WATCH_MIN_FRAC_OF_52W_HIGH`).
2. **RS leads price:** `rs_line_high`. The RS line (close ÷ the S&P 500) is at or above its highest of the
   55 sessions before today.
3. **OBV leads price:** `obv_high`. On-balance volume is at or above its highest of the 55 sessions before today.
4. **Strong group:** `group_rs` ≥ 70 (`BREAKOUT_WATCH_MIN_GROUP_RS`, the Sectors page's industry-group rating).

The screen's floor is `tradable`, which adds a $10 minimum traded price and a year of history to the study's
dollar-volume floor. It is slightly stricter than the rule measured.

| Window | Alerts | Alerts a week | Precision (real breakout within 4 weeks) | Base rate | Recall |
|---|---:|---:|---:|---:|---:|
| 2017–2021 (discovery) | 1,738 | 6.9 | 11.3% | 8.2% | 2.6% |
| 2022–2026 (hold-out, run once) | 1,983 | 8.1 | 13.9% | 8.5% | 4.3% |

**Overfitting caveat.** Which signals entered the rule was chosen on 2017–2021, so the discovery figures are an
optimistic ceiling. The thresholds themselves were not tuned. The hold-out figure is the honest one, and it held
up (it was even higher). But this is one hold-out, and every year to October 2026 informed some earlier
decision in this project. The clean remaining test is **forward data**:
- the `breakout_watch` job records the screen's members after every snapshot, in `screen_alerts` (screens/alerts.py);
- `breakout_study --forward` scores them with this study's outcome rule, against every candidate on the same weeks;
- judge it after at least 100 real breakouts have been flagged forward.

At 8 alerts a week and a 14% hit rate, that takes about two years. The Screens page's forward-return study
also covers the screen once the month-end history carries the new fields (`screen_history --refill`).

**What it is not.** At 13.9% precision, about 6 in 7 alerts do not become a real breakout within four weeks.
The rule lifts the odds of a breakout *happening*, not of it *working*: follow-through stays at about 36–40%.
It is a way to rank a watchlist, not a reason to buy before the breakout. In India it is not offered.

## Limits

- **Survivorship:** today's listings and today's industry classification, so delisted companies are absent.
- **One definition:** the breakout, follow-through and candidate rules are one choice each, never varied. A
  different follow-through bar (e.g. 3 ATR, or 40 sessions) could change the ranking.
- **Overlap:** weekly samples of one stock overlap, handled by the stock-level bootstrap. Overlapping 4-week
  windows across stocks in the same week (market-wide moves) are not separately modelled.
- **Multiple testing:** 29 signals in each of two markets. Expect one or two false "confirmations" a window by
  chance, which is why the hold-out was required.
- **India's floor:** India's ₹50 crore liquidity floor limits it to the larger, liquid stocks.

## Reproduce

From `scripts/`, about 3 minutes for both markets. It reads stored data only (prices, the Sectors page's
benchmark, breadth, `group_rs_history`, `delivery_daily`, the industry classification) and downloads nothing:

```bash
PYTHONPATH=. .venv/bin/python -m swing_screener.analytics.breakout_study --market us india
```

Add `--forward` to score the logged Breakout watch alerts. The first run of this design (2026-11-06, from
scratch scripts, RS line on SPY, OBV compared over 54 sessions) gave the same verdicts, with lifts within 0.03.
The module is the one to cite.
