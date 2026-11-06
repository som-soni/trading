# Martin Luk — research notes

*Raw material, synthesized: what Martin Luk says and does on his daily streams, organized by the
creator template (§0), with timestamps. Everything below is **his** view and **his** numbers unless marked
otherwise. My inferences are marked **[inferred]**; words the audio does not settle are marked **[unclear]**.
Where a claim could be checked against stored prices, the check is shown.*

*What went where: the generalizable mechanics went to the Learn guides ([Stage 4 shorts](learn-strat-stage4-shorts.md)
§3 and §5 — the snap-back short, minding the index, covering into weakness; [VWAP](learn-strat-vwap.md) §2 — a respected
line, one anchor on several bar sizes; [the index trend](learn-health-trend.md) §8.2 — narrow or broad, stretch); the
decisions went to the trading-system drafts
([daily market review](system-daily-market-review.md), [shorts](system-shorts.md),
[risk and exposure](system-risk-exposure.md)).*

**In short**

- A short-horizon swing trader in the Kullamägi lineage who trades **both directions**, from Hong Kong, with
  entries timed on 1-, 5- and 15-minute candles but trades meant to last **days to weeks**.
- His edge as he describes it is **location + timing**: short a bounce into a *declining* short average (daily
  9/21 EMA), a prior swing low, an unfilled gap or an anchored VWAP — and only when the index itself is not
  stretched, because individual stocks bounce with the index.
- Risk is scaled to his **conviction in the tape**, not to the setup: on a day he judged poor for shorts he
  still took the setup he liked, at an estimated 0.02–0.1% of the account per attempt.
- Shorts are covered **into weakness** (gap-downs, prior swing lows) rather than trailed; fast moves in his
  favour are *held*, not scaled out of.
- On 3 November 2026 he was short-biased but cautious: a semis-led decline with the rest of the market still
  intact, the Nasdaq stretched below its 9-day EMA, and Election-Day gap risk.

---

## 0. Template

Every creator note uses the same sections so creators can be compared side by side: **1** style at a glance,
**2** how they read the market, **3** what they trade, **4** setups, **5** execution, **6** risk and sizing,
**7** management and exits, **8** process, **9** nuances worth keeping, **10** how it compares, **11** open
questions, **12** source log. Section 2 feeds the daily market review; 4–7 feed the setup playbooks; 6 feeds
risk and exposure.

## 1. Style at a glance

| Dimension | What he does | Evidence |
|---|---|---|
| Direction | Long and short; short-biased on this stream ("Adding shorts again") | Title; 1:45 "not attracted to any longs right now" |
| Holding period | Multi-day to multi-week swings; "not targeting a day trade or a one- to two-day move" | 1:47 |
| Timeframe stack | Study: daily and weekly. Levels: daily first, hourly and weekly as a range. Triggers: 1-, 5-, 15-minute candles | 0:40, 2:22, 2:11 |
| Instruments | US stocks, 3× sector ETFs (SOXS to be short semis), Asian stocks (SK Hynix), leveraged ETFs on single names | 2:08, 1:43, 1:06 |
| Families (see [strategy families](app-guide-strategy-families.md)) | Trend continuation on the short side (short the bounce in a downtrend); reversal / failed move (short a gap-up that fails at resistance) | §4 |
| Risk per attempt | Very small when the tape is doubtful: "less than 0.1%… maybe 0.02% per trade" | 1:09 |
| Session | Trades mostly near the US open, sometimes midday, rarely near the close (Hong Kong time zone) | 2:04 |

## 2. How he reads the market

### 2.1 What he said on 3 November 2026

- **The day before was ugly**: a bounce in the first ~16 minutes, then selling the rest of the day (0:06). He
  dislikes "the increasing volatility, the wide **[unclear]** candles up here" — the index's daily ranges
  widening near the top — and reads it as needing "more time, or maybe more downside" (0:06).
- **Narrow, not broad (yet)**: "we're getting [panics] in the semi-sector, but outside of the semi-sector,
  things are still doing fine" (0:07). He wants to *see panic* — an acceleration to the downside — and is
  "not really seeing the acceleration" (0:08).
- **The regime worry**: possibly "the start of a bear market, given the really poor breadth, the extension of
  the previous moves, and the lack of correction in the past three to four years" (0:08). He compares it with
  the 2021–22 Stage 3 → Stage 4 transition: a 2020–21 easy-money uptrend, sideways from mid-2021, then the
  Stage 4 decline (0:09).
- **Weekly levels on the indexes**: the Russell is at its weekly 9 and 21 EMAs; the semis are at the weekly
  50 EMA, "a pretty strong support on the weekly chart" (0:11). (Both names were misheard by the transcriber;
  the weekly data below settles them.) He agrees that a higher-timeframe EMA is usually stronger support or
  resistance (1:44).
- **Index extension is a timing filter for shorts**: SK Hynix "is a pretty decent short", but "the Qs is so
  extended from the 9, SPY is also pretty extended… the Russell is still near all the EMAs". So he would "at
  least wait for the hourly 9 on the Qs, or maybe just wait for tomorrow, or the daily 9 EMA" — adding that he
  "made a mistake… shorting too early on Monday" (0:20–0:21).
- **Long side**: not attracted to longs; "I just want more confirmation and a little bit wider participation
  from different sectors, different types of stocks" (1:45, on a Palantir question).
- **Event risk**: "the gap risk on those shorts are a bit higher today than usual" (1:51). The downside
  extension "could suggest the market is pricing in the bearish case for the elections or any events" — but
  "sometimes I don't like to overthink" (1:55). 3 November 2026 was the US midterm Election Day **[inferred:
  the event he means]**. If there is no strong close, he "may reduce exposure before the close" (1:54).

### 2.2 What the stored data says he was looking at (close of 2 November 2026)

| Instrument | vs 9-day EMA | vs 21-day EMA | vs 50-day EMA | Off its 52-week high | Weekly |
|---|---|---|---|---|---|
| SPY (S&P 500) | −1.5% | −1.9% | −1.7% | −3.5% | near its weekly 21 EMA |
| QQQ (Nasdaq 100) | **−3.7%** | −5.1% | −5.6% | −10.3% | −4.0% vs weekly 9 EMA |
| IWM (Russell 2000) | 0.0% | +0.1% | −1.2% | −8.5% | **−0.7% / −1.4% vs weekly 9 / 21** |
| RSP (equal-weight S&P) | +1.0% | +1.8% | +2.3% | **−1.3%** | |
| SMH (semis) | −6.0% | −8.7% | −10.5% | −24.0% | **+1.8% vs weekly 50 EMA** |
| SOXX (semis) | −7.8% | −11.1% | −13.5% | −30.7% | **−0.7% vs weekly 50 EMA** |
| IGV (software) | −5.0% | −5.6% | −4.0% | −11.9% | |

His reading checks out on every point: the Nasdaq was stretched well below its 9-day EMA; semis had already
fallen a quarter to a third; yet the **equal-weight** S&P sat 1.3% from its high, above all three averages —
"outside of the semi-sector, things are still doing fine". (The week's bar holds only 2 November.)

### 2.3 The reasoning underneath **[inferred]**

1. **Narrow vs broad decides conviction.** A cap-weighted index falling while the equal-weight index holds is a
   leadership problem, not yet a market problem. He wants it to broaden — "panics" — before treating it as a
   bear market.
2. **The index sets the clock for single-stock shorts.** Shorting a weak stock while the index is stretched
   below its 9-day EMA means shorting just before the likely reflex bounce. The better short comes *after*
   the index bounces back to its short average, when the weak stock bounces too — into resistance.
3. **Higher-timeframe support on the sector caps short conviction.** Semis at a weekly 50 EMA is exactly
   where a bounce is likeliest, so he holds the semis short but sizes the next shorts small.

## 3. What he trades

- **Relative weakness**: stocks failing to bounce with the indexes ("SK Hynix is showing some relative weakness
  to the indices", 0:25).
- **Former leaders in a Stage 3 → 4 transition** (AEHR, 1:19) and crowded high-beta names (MSTR, COIN, BMNR —
  crypto proxies; SNDK).
- **Sector views through 3× ETFs**: long SOXS = short semis. The ETF cuts single-stock risk "maybe 50%", and in
  earnings season you cannot dodge every constituent's report (Intel, Marvell, Lumentum, Western Digital that
  week), so he holds it through them (2:08).
- **Not volatility products**: shorting UVXY after a 100% run can still cost another ~36%, and in 2020 it rose
  "more than 1000%". Better to be long the Qs than short UVXY (1:39).

## 4. Setups

### S1 — Short the snap-back into a falling short average

| | |
|---|---|
| Shape | A stock breaks down hard (a "huge breakdown candle"), then snaps back over the next one or two sessions |
| Where to short | Into the **declining** daily 9 EMA, "or maybe even at the 21"; for a bigger rally, the declining 50 EMA ("if SK Hynix can rally into this declining 50 EMA, that would be the best") |
| Why it works (his words) | "after this type of huge breakdown candle, if we got a really quick snapback… it's pretty shortable" (1:17) |
| Context needed | The index not stretched in the same direction (§2.1); relative weakness |
| Examples | A stock "nowhere near any daily EMAs" — still a candidate because "the declining 9" falls toward price each weak close (1:16); SK Hynix (1:10); MSTR pushing into the daily 9 (1:24) |

**[inferred] The bet:** the first rally after a breakdown is made of trapped buyers getting out near cost and
of shorts covering. Once that buying is spent at a falling average, sellers are back in control. Shorting the
bounce gives a nearby, objective stop (above the bounce) — far tighter than shorting the breakdown itself.

### S2 — Short a gap-up into resistance that fails

Walked through on AEHR (2:10–2:18), a former leader that gapped up into a cluster of resistance:

- **The level is a confluence**: prior highs, the hourly 150 EMA, the hourly 100 SMA, an anchored VWAP from the
  swing high, prior swing lows acting as resistance, an unfilled gap. "Many confluence" makes it "a better entry
  for the shorts" (2:17).
- **Entries — several are valid; "pick the one you like"** (2:13):
  - the 5-minute 9 EMA breakdown (stop at the breakdown candle's high);
  - a 1-minute candle breakdown, "a little bit more aggressive", if price first reaches the 150 EMA;
  - an anchored-VWAP rejection from the high of day;
  - a 15-minute candle breakdown — wider stop, fewer stop-outs.
- **Re-entries are normal**: he would "trade this one, and just stop out, and then trade this one".
- **Time of day matters**: "the day looks a little bit too strong… I will wait for tomorrow at least, or at the
  21 EMA" (1:21). If AEHR closes weak, "the 21 is going to follow through down" and the rejection "looks much
  better" (2:15).

### S3 — Short the bounce into a gap or old lows

"[BE, unclear] is now heading towards this unfilled gap and slightly above the declining 9" (0:24); another name
was "pulled back into the declining 9, previous swing lows", with a weekly bounce that stayed under the
weekly 9 and 21 (2:19). The resistance is overhead supply: holders who bought the old lows or before the gap
get out near breakeven.

### Location beats intraday structure

Asked whether he would short while the intraday chart makes higher highs and higher lows: "It depends on…
where the price has moved to." Even if the Qs are making higher highs intraday, if price is moving **into
daily resistance** (say the daily 9 EMA) and shows "rejection, distribution, selling", he still shorts it —
and the mirror image for longs (2:06).

### The long mirror — anchored VWAP pullbacks

On a pullback in SK Hynix toward its IPO-anchored VWAP: if the daily price has not reached the line but the
hourly is slightly undercutting it, he "may take the first try on the hourly chart", and if that fails and
price shows strength again — an intraday breakout — near the daily line, "another try" (2:24).

## 5. Execution

- **Triggers are lower-timeframe candles**: a candle-low breakdown, a 1-minute close below the 9 EMA, an
  anchored-VWAP rejection. "These entries can be very creative and flexible… you don't have to use the same
  trigger" (2:14).
- **Trigger timeframe sets stop width.** His 1- to 5-minute entries suit "really tight stops". With 2–3% stops,
  "use the 15-minute candle breakdown… slightly above 3% stop, 4% stop… definitely if you use a higher time
  frame you would get less noise, less losing trades" (2:15–2:16).
- **No chasing**: SK Hynix "missed the entry on this one-minute candle and then I hesitated… I really don't want
  to chase, I really don't want to short into the weakness, so let's see whether we can get some bounce" (0:34).
- **Timing in the session**: mostly near the open (2:04). Some trades need the close — "the gold and silver
  shorts back in late January… I have to wait for the close" (2:01).

## 6. Risk and sizing

| Rule | His words / example | Time |
|---|---|---|
| Risk scales with conviction in the tape | On a "not the best day for shorts" he takes the setup anyway at "less than 0.1%… maybe 0.02% risk per trade… only losing like 0.05% for the two losses, to potentially catch the fade" | 1:09 |
| Tighter stop on a doubtful day | Stop at 152.1 rather than above the daily VWAP: "starting at the VWAP is very reasonable… but given that today may not be the best day on the short side, I want to limit my loss" | 1:03 |
| Size in % of account, capped | "All the shorts today are less than 20% sizing" | 1:50 |
| **Size up slower than the account after a good run** | "I got a really good run last month, so I'm sizing up way slower than my account… prevent oversizing after a good period" | 1:50 |
| Event days | Gap risk "a bit higher today than usual"; "don't do crazy sizing and be prepared for the gap ups" | 1:51, 2:20 |
| Stops on the traded instrument | For leveraged ETFs the stop is set on the ETF, not the underlying, even if the ETF's stop occasionally hits when the stock's would not | 1:43 |
| **Never move a stop after entry** | "I just don't like moving my stops after I enter the trade. I'm afraid that could become a bad habit" | 1:43 |

The "donation" framing (1:12): a probe that is stopped out "becomes the donation… but if it worked, then that's
the killer trade". The cost of being wrong is set so low that being early is cheap.

## 7. Management and exits

- **No quick partials**: if a trade goes 3R in his favour within minutes or hours, he does *not* take partial
  profits. "If a stock moves really fast in my direction, I will probably consider it a positive sign to hold
  the position for a longer and bigger swing" (1:47).
- **Shorts are covered into weakness**, not trailed: "for short, I tend to… cover into weakness, instead of
  waiting for the close and trailing with the 9 or 21 EMA. Generally I would love to close at the gap downs"
  (2:30). For longs, the mirror: sell into gap-ups.
  - *SNDK (October)*: shorted, added on a bounce; covered a third on a gap-down into the previous swing lows; the
    rest near the open of the next gap-down — and so missed the gap-down after that (2:29).
  - *COIN*: shorted on a Friday, covered after an earnings gap-down that reached the previous swing lows, "near
    the low 140s" (2:31).
- **Earnings**: holds the semis ETF through a constituent's report — "I got enough profit cushion", the ETF
  dilutes the single-stock risk, and "for trading we have to accept a bit of the uncertainty" (2:08).
- **A plain exit rule he used**: an oil position was closed near the prior day's low on a close below the hourly 9
  EMA — "not really the best exit" (0:13). **[unclear: long or short; XLE fell 4% that day, so a long exit
  fits.]**

## 8. Process

- **How he built pattern recognition** (0:38): zoom out on daily and weekly charts to find two things — explosive
  moves (a large % in one to three weeks or a month) and long-lasting trends (six months, a year or more), **up and
  down**. He started by going through every Nasdaq-100 and S&P 500 stock one by one; now he studies the past
  moves of whatever he recently traded (e.g. BMNR). Intraday replay goes back only one or two years on hourly or
  15-minute bars, "so the sample size would be much smaller".
- **Studies alone**: chat rooms are "too much noise", mostly new traders, "always opinions different from you…
  just like another social media"; trading "is not a group project" and "is very personalized". A strong
  partner helps, but is unlikely early on (0:44–0:50).
- **Public track record**: he enters the US Investing Championship to build a five-to-ten-year record "as early
  as possible" and to "hold myself accountable for all the trades" — the pressure "is actually healthy" (1:31).
  He started with about $1k in 2020 and added about $13k over three years to reach the $20k minimum (1:29).
- **Self-checks out loud**: "I'm really afraid that I'm over-trading here" (0:34); "not being patient enough, not
  really waiting for the best opportunities" (1:50); "maybe getting a little bit FOMO on this one" (1:11).
- **Lifestyle cost of leverage**: from Hong Kong the US close is 4–5 a.m.; he stays up only when volatility is up
  and he carries heavy exposure or margin — "the cost of getting highly leveraged… is going to affect your
  sleeping schedule or lifestyle", and he expects to give up some performance for health with age (1:57–2:00).

## 9. Nuances worth keeping

1. **Two dials, not one.** The setup decides *whether* to trade; the tape decides *how much*. On a poor day the
   same setup is a probe at a fraction of normal risk. This keeps him engaged with the trade he likes without
   letting a bad day become a bad week.
2. **The index's stretch is the timing filter.** Short weak stocks after the index bounces to its short average,
   not while it is stretched below it. His one admitted mistake this week was shorting too early.
3. **Shorts and longs are managed differently.** Shorts are covered into gap-downs and old lows because
   short-covering rallies are fast and violent **[inferred]**; trailing a 9/21 EMA on a short gives too much back.
4. **Anti-hot-hand sizing.** After a strong month he raises size more slowly than his equity grows — the
   opposite of the usual reflex.
5. **Express a sector view with a sector instrument.** A 3× sector ETF lets him stay short semis through
   earnings season without a stop-out on any single report.
6. **The trigger timeframe is a choice about stop width,** not about which signal is "right". Lower-timeframe
   triggers buy a tight stop at the price of more stop-outs.

## 10. How it compares

- **With Kullamägi** (see [Kullamägi's momentum breakouts](learn-strat-kullamagi.md)): same lineage —
  intraday-timed entries for multi-day swings, small risk, a few large winners. Differences heard here: he takes
  **no quick partials** (Kullamägi sells a third to a half after three to five days); he **covers shorts into
  weakness** rather than trailing; and he leans on **declining EMAs and anchored VWAPs** as short-entry
  locations.
- **With Minervini** (see [Mark Minervini](creator-mark-minervini.md)): both wait for the market to show
  broadening before committing on the long side, and both probe small first. Minervini is long-only and reads
  bottoms from *which stocks hold up*; Luk reads them from *panic* — acceleration and broadening of the
  decline.
- **With this repository**: every strategy here is long-only and runs on daily bars. Shorts are "blocked by the
  account" ([strategy families](app-guide-strategy-families.md) §4), and his 1- to 15-minute triggers need
  intraday data that is not stored. A **daily-bar proxy of S1** is testable on stored data: Stage 4 stock, a
  breakdown day, then a close back below a falling 9- or 21-day EMA after a rally into it; enter next open;
  stop above the rally high; cover a third at the prior swing low.

## 11. Open questions

- His **normal** risk per trade (only today's "tiny" probes were stated).
- How he chooses between shorting the breakdown and shorting the bounce, beyond "pick the one you like".
- Whether he trails *longs* on the 9/21 EMA (he described only short exits).
- Does an anchored VWAP weaken with repeated tests? He did not know (2:32).
- Tickers not settled by the audio: the "unfilled gap" name at 0:24 (BE?); the name "nowhere near any daily
  EMAs" at 1:16; the space-theme short at 2:18.

## 12. Source log

| Date | Source | Length | Notes |
|---|---|---|---|
| 2026-11-03 | Daily stream, "Adding shorts again" (US session, Hong Kong night) | 2 h 36 min, about half of it talk | Transcribed locally twice (speech model, second pass primed with ticker and indicator names). Video at 144p: chart labels unreadable, tickers from audio, two resolved against stored weekly data (§2.2). Viewer questions are read aloud; only his answers are used |

### Trades and ideas mentioned, 3 November 2026

| Name | Side | What he said | Time |
|---|---|---|---|
| SK Hynix | Short (probes) | Two tiny-risk attempts stopped; best if it rallies into the declining 50 EMA; relative weakness vs indexes | 0:20, 1:06 |
| SOXS (−3× semis) | Long = short semis | Held through AMD's report: profit cushion, ETF dilutes single-stock risk | 2:08 |
| QQQ / SPY | — | Too stretched below the 9 EMA to add shorts; wait for the hourly or daily 9 | 0:20 |
| MSTR | Short candidate | Extended to the downside; pushing into the daily 9 | 0:21, 1:24 |
| AEHR | Short candidate | Gap-up into stacked resistance; entry walkthrough (S2) | 1:19, 2:10 |
| [BE, unclear] | Short | Heading into an unfilled gap, just above the declining 9 | 0:24 |
| Oil position | Exited | On a close below the hourly 9 EMA, near the prior day's low | 0:13 |
| SNDK (October) | Short, closed | Added on a bounce; covered into two gap-downs | 2:29 |
| COIN | Short, closed | Covered after an earnings gap-down near the low 140s | 2:31 |
| Palantir | No long | Market not favouring longs; wants wider participation | 1:45 |
| UVXY | Would not short | Volatility products can run far further | 1:39 |
