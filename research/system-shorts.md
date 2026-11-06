# Shorts (draft)

Part of [my trading system](system-overview.md). When to short, what, where, and how to get out. Every rule is *proposed*,
with its source. Nothing on this page has been backtested here: the repository's strategies are long-only, and the
intraday triggers need data that is not stored. §7 is the plan to test a daily version.

**In short**

- Short only in the two daily-review states that allow it — **a correction in one area** or **a broad correction** — and
  never while the index is already stretched below its own 9-day EMA.
- The best location is a **bounce into resistance in a stock that is already breaking**: a falling 9- or 21-day EMA, an
  unfilled gap, old swing lows, an anchored VWAP from the high. Shorting the bounce gives a close, objective stop.
- Size by the tape: a probe (a small fraction of normal risk) on a doubtful day, normal on a clean one; smaller on event
  days.
- **Cover into weakness** — gap-downs and prior swing lows — instead of trailing; never add to a losing short.

---

## 0. Can I short this?

| Market | How | Constraints |
|---|---|---|
| US | Short the stock; or buy an inverse / leveraged ETF (e.g. SOXS for semis) | Borrow availability and fee; for an ETF, set the stop on the ETF itself (Luk) |
| India | Stock futures or options only, for anything held overnight | Cash shorts must close the same day; futures need a liquid next-month contract and no ban period ([Stage 4 shorts](learn-strat-stage4-shorts.md) §3) |

**Do not short volatility products** after a spike: a +100% run can go on to +36% more, and in 2020 one ran over 1000%.
Go long the index instead (Luk).

## 1. When

| Daily-review row | Short activity |
|---|---|
| Correction in one area | Probe-size shorts in the breaking group only |
| Broad correction / bear | Normal-size shorts on bounces |
| Any other row | None |

**Stretch rule (Luk).** If QQQ (or the Nifty) is far below its 9-day EMA, don't add shorts today. Wait for it to retest its
hourly 9 EMA, or its daily 9 or 21. Single stocks bounce with the index, and the bounce is where the short belongs. His one
admitted mistake that week was shorting a day early.

**Support rule (Luk).** If the sector sits on a higher-timeframe support — semis on their weekly 50 EMA — new shorts in that
sector are smaller.

## 2. Candidates

- **Relative weakness**: the stock fails to bounce when the index bounces.
- **Former leaders in Stage 3 → 4**: a long advance, a wide sideways top, now under a falling 30-week line ([Stage 4
  shorts](learn-strat-stage4-shorts.md)).
- **The breaking group**: the sector that leads the decline (semis in November 2026).
- **Crowded high-beta names**: crypto proxies, speculative growth.
- **Avoid**: short interest over about 20% of the float (squeezes); results within five sessions, unless the gap risk is
  accepted; volatility products.

## 3. Setups

| # | Setup | Where to short | Stop | Source |
|---|---|---|---|---|
| S1 | **Snap-back into a falling short average** after a big breakdown candle | The rejection at the falling 9-day EMA, or the 21; for a larger rally, the falling 50 | Above the bounce high (intraday: the trigger candle's high) | Luk |
| S2 | **A gap-up into stacked resistance that fails** | The rejection where prior highs, an hourly 100/150 average, an anchored VWAP from the high and old lows overlap — the more that stack, the better | Above the breakdown candle | Luk (AEHR) |
| S3 | **Bounce into an unfilled gap or old swing lows** | At the gap or the old lows, ideally with a falling 9-day EMA there too | Above the bounce high | Luk |
| S4 | **Failed rally to the 30-week line** | The close back below the falling 150-day (30-week) average after a rally to it | Above the rally high, plus a buffer | Weinstein ([Stage 4 shorts](learn-strat-stage4-shorts.md) entry B) |
| S5 | **52-week-low breakdown** | The breakdown close | Above the 10-day high or the 150-day | [Stage 4 shorts](learn-strat-stage4-shorts.md) entry A |

**Why S1–S3 work [inferred from Luk]:** the first rally after a breakdown is mostly trapped buyers getting out near cost
and shorts covering. Once that buying is spent at a falling average or an old level, sellers are back in control. Shorting
there gives a tight, objective stop — tighter than shorting the breakdown itself.

**Location beats the intraday trend (Luk).** Even if the intraday chart is making higher highs and higher lows, a stock
rising *into* daily resistance and showing rejection is still a short.

## 4. Execution

| Trigger timeframe | Typical stop | Trade-off | Source |
|---|---|---|---|
| 1-minute candle breakdown, or a 1-minute close under the 9 EMA | Very tight | Most stop-outs; best price; re-entries are normal | Luk |
| 5-minute 9 EMA breakdown | Tight | His usual | Luk |
| Anchored-VWAP rejection from the day's high | Tight | Needs a clear high | Luk |
| 15-minute candle breakdown | About 3–4% | "Less noise, less losing trades" | Luk |
| Daily: a close back under the falling 9/21-day EMA, entered next open | Above the bounce high | No intraday watching; worst price | Daily proxy (§7) |

- **Don't chase, don't short into weakness**: if the entry is missed, wait for the next bounce (Luk).
- **Time of day**: entries mostly near the open. A strong day is a reason to wait for tomorrow or for the 21-day EMA.

## 5. Risk

- Risk tier from the daily review: **probe** on a doubtful day (Luk risked 0.02–0.1% per attempt), **normal** on a clean one.
- Smaller on **event days**; "be prepared for the gap-ups" (Luk).
- Cap total open short risk (the Learn guide's reference: about 3% of the account) — see [risk and
  exposure](system-risk-exposure.md).
- The stop is set before entry and **never moved** (Luk). A short can gap far past its stop; size for that.

## 6. Management and exits

- **Cover into weakness (Luk)**: take a first part at the prior swing low or on a gap-down; cover the rest on the next
  gap-down open. Don't wait for a close and trail on the 9 or 21 — short-covering rallies give the gains back fast.
  - *His SNDK trade:* added on a bounce; covered a third on a gap-down into prior swing lows; the rest at the next
    gap-down's open (and so missed the one after).
  - *His COIN trade:* covered after an earnings gap-down that reached prior swing lows.
- **Never add to a losing short**: a losing short grows as a share of the account ([Stage 4 shorts](learn-strat-stage4-shorts.md)
  §3).
- **Earnings**: a sector ETF can be held through a constituent's report, with a profit cushion; a single stock usually
  should not be (Luk).
- **Weak close on an event day**: reduce exposure before the close if the market does not close strong (Luk).

## 7. Testing a daily version

A version of S1 that runs on stored daily bars:

1. **Universe**: liquid stocks in Stage 4 (close under a falling 150-day average), weaker than the index over 63 sessions.
2. **Breakdown day**: a close more than 1.5 ATR below the prior close, on above-average volume.
3. **Bounce**: within 10 sessions, a high that reaches the falling 9- or 21-day EMA.
4. **Entry**: the next close back below that EMA; enter at the following open.
5. **Stop**: above the bounce high plus 0.25 ATR.
6. **Exit A — cover into weakness**: a third at the last swing low before the bounce; the rest on the first gap-down open
   after that. **Exit B — trail**: a close above the 9-day EMA.
7. **Index condition**: compare taking all signals with taking only those where the index is *not* more than *k*% below its
   own 9-day EMA on the entry day — the stretch rule.

Report expectancy in R, win rate and the share of trades with a gap through the stop, for each exit and index condition, in
both markets (India via futures-eligible stocks).
