# Mark Minervini — research notes

*Raw material, synthesized: what Mark Minervini teaches in his talks, organized by the creator template
([Martin Luk](creator-martin-luk.md) §0), with timestamps. Everything below is **his** view and **his** numbers
unless marked otherwise; co-presenter Mark Ritchie II is named where the point is his. My inferences are marked
**[inferred]**, audio the transcript does not settle **[unclear]**. Claims about named stocks were checked
against stored prices (§9).*

*This repository already implements his VCP rules in detail ([the backtest spec](minervini-backtest-spec.md),
the `minervini_spec` strategy, [SEPA and the VCP](learn-strat-vcp-sepa.md)). This note records what the talks add
beyond those — here, **how he finds the next leaders while the market is still falling**.*

*What went where (ANF clip, §13): Learn — [Volume](learn-price-volume.md) §4 (reading the base on weekly bars) and [SEPA and the VCP](learn-strat-vcp-sepa.md) (adding on a natural reaction; buying the turn, not the dip); trading system — [swing longs](system-swing-longs.md) L10 (a second source), two management rows and two test rows.*

*What went where (June 2026 podcast, §12): trading system — [swing longs](system-swing-longs.md) setups L9–L11, the management rows and the tests; Learn — the results-cushion rule was already in [SEPA and the VCP](learn-strat-vcp-sepa.md); the platform's indicator bands (§12.4) became the chart's Trend-health bands indicator, explained and measured in [trend indicators](learn-ind-trend.md).*

*What went where: Learn — [bases](learn-bases.md) §6 (the leader that rests — an exception to "laggard RS" — and the
failed base that resets), [the index trend](learn-health-trend.md) §8 (setup supply and your own results as exposure
inputs; an unmeasured "first breakouts are the best trades" line corrected against [relative strength](learn-price-rs.md)
§4.3). Trading system — [daily market review](system-daily-market-review.md),
[swing longs](system-swing-longs.md), [risk and exposure](system-risk-exposure.md).*

**In short**

- The next bull market's leaders are found **during the decline**, because that is when they stand out most:
  stocks in uptrends while the index is in a downtrend — "sore thumbs".
- Five things to look for after a correction: the stocks that **fell least** (within 25% of their high,
  preferably at new highs), **bases built while the market falls**, the **fastest rebounds** to new highs, recent
  **IPOs forming their first base**, and a **proliferation** of all of these.
- Setups appear in three windows around the market's low — **predictive** (before), **coincident** (at, often
  around a follow-through day) and **confirming** (after) — and there is usually a second chance as the right side
  builds out.
- You never know the low, so you **default to the stocks**: buy a few; add only if they work; go back to cash if
  they fail. Your own results are the decisive market gauge.
- Checked here: his named examples are mostly accurate, but our own test of the *population-level* rule ("the
  stocks that held up best lead") found the opposite in three recent sell-offs. The part of his advice that our
  data supports is the **regime and feedback** part, not "buy the strongest at the low".

---

## 1. Style at a glance

| Dimension | What he does | Evidence |
|---|---|---|
| Direction | Long only (in this talk) | — |
| What counts as a big winner | "Super performance" includes short, fast moves — "30, 40, 50% in a couple of weeks or a month" — because they compound | 0:16 |
| Where the "leverage" comes from | The stock's own speed ("octane"), not margin | 0:22 |
| Gate | His Stage 2 Trend Template (eight criteria); a "confirmed" Stage 2 is a version requiring it to hold for about five months **[unclear: "the five month" template]** | 0:19 |
| Setups | VCP, cup with handle, flat base, the "cheat" area, power play, IPO primary base; two named patterns, *lead and rest* and *failure reset* (§4) | throughout |
| Families (see [strategy families](app-guide-strategy-families.md)) | Breakout from a base (contraction); trend continuation | — |
| Price philosophy | "You don't want the lowest price, you want the right price… the point at which the stock moves very quickly up or down. I want to know I'm wrong just as fast as I want to know I'm right" | 0:54 |

## 2. How he reads the market

### 2.1 Corrections are where leaders are born

- "96% of the biggest winning stocks… come from corrections" (0:06) — later "upwards of 90%" (0:16). Two figures for
  the same claim; no source given.
- The ideal starting point is **from cash after a correction**. If the bear market caught you down big, "you'll be
  digging out of a hole" and the correction will not feel like an opportunity (0:06).
- **Sentiment**: "the best setup you can have in a bear market is to have everybody bearish and lots of stock setups
  that people don't believe in" (0:17). He *wants* to hear consensus that the bear market will last.
- **Health gauge**: run the Trend Template across the market. "When the market's really healthy, you'll see 700, 800,
  900 names in an uptrend"; in this bear market, "very few" (0:20). **[inferred: on a commercial screener's
  universe; the count, not the threshold, is the point.]**
- **Stocks bottom first**: "almost always the best names make their lows well ahead of the market"; the indexes can
  go to lower lows after them (0:53). Amgen in 1990, Amazon in 2002, Netflix in 2008–09 are his cases.
- **Old leaders rarely lead again**. Amazon "has become the market" — Ritchie: a one-for-one correlation with the
  Nasdaq, no more mispricing (0:28). Cisco and Microsoft after 1999 took up to twenty years to recover; Eastman Kodak
  "went sideways for 24 years, while the S&P 500 went up 500%" (0:29). The next leaders are unfamiliar names — in
  1990 Microsoft, Home Depot and Amgen were mid and small caps (0:12).
- **Breadth of leadership**: the market is "usually led by anywhere between three, four, five groups off the lows"
  (0:51).

### 2.2 Three windows around the low

| Window | When | What happens | His examples |
|---|---|---|---|
| **Predictive** | Before the market's low | Stocks set up *during* the down leg; some break out, the market makes another leg down — "this is where the rubber meets the road": they fail, or pull back to the breakout without stopping you out | Amgen 1990; Netflix 2008–09 |
| **Coincident** | At the low | Many breakouts cluster around an O'Neil **follow-through day**: "up 1%, usually on the fourth day or later coming off the lows" | Ollie's 2016 cheat; COVID plateaus 2020 |
| **Confirming** | After, as the market builds its right side | Larger bases break out; "most markets… will build out that right side at some point", so missing the low still leaves "a second really golden opportunity" | 1991 ("Cup with handles proliferate", an IBD headline around 15 January); Chipotle 2010; Alibaba 2017 |

Different bottoms produce different mixes: the slow 1990–91 bottom had all three; the 2020 V-bottom left little time
for predictive setups but still built two plateaus where "there were just tons of setups" (0:13). Ritchie says he
made more in the 2020 *confirming* period than at the low: he called Minervini scared, and was told "trust the stocks…
we buy them" (0:14). They bought their first stock on 6 April 2020, on the follow-through day.

### 2.3 You will not know the low — so default to the stocks

"You're not going to know for sure that you're at a market low… so you've got to default to the stocks and you buy a few
names. If they work, great, you can buy some more. If you're not getting traction, you hold off and you keep it small"
(0:16). What he wants to see: a **proliferation** of setups, a **string of successes** in the first breakouts, a
follow-through day and a **lack of distribution** (0:53). What he does not want: the number of setups diminishing, or
guessing at beaten-up names (0:53).

His own 2022 attempt is the worked example (0:55): toes in the water in oil names (PBF Energy, ConocoPhillips) made
"nice quick moves", "but they didn't hold… the market went to new lows… the stocks didn't hold, and so we got forced back
to cash. Now, I reset." The same test after a follow-through day: "three of them are losers, two of them are winners, you
haven't made any money, there's distribution coming out… there's no reason to start getting heavily invested" (0:54).

## 3. What he trades — the five things after a correction (0:17)

1. **The stocks that corrected least** — within 25% of the 52-week high, "preferably making new highs". Not the 90% losers:
   "How much lower can they go? Well, zero… your risk is always 100%."
2. **Stocks building bases while the market corrects**, within a long-term uptrend: "moving sideways… they're
   resisting."
3. **The fastest rebounds** — "the ones that move the most off the lows in the shortest period of time".
4. **Recent IPOs forming a primary base** (the first base after listing) as they come off a correction. Quoting David
   Ryan: the best IPO setups come in corrections, because issuers are more selective then, and strength "stands out like
   a sore thumb" (0:42).
5. **A proliferation**: "you don't wanna just see one or two names… you want to have a handful of names, and those names
   start to work on balance, and then another wave."

Two tools he names: the Trend Template (all eight criteria = Stage 2), and an **RS-line "blue dot" screen** — stocks whose
RS line makes a new high coming out of a base — which he likes "to run when the market's in a bear market or in a
correction" (0:21).

## 4. Setups and patterns

### The contrast trade: an uptrend inside a downtrend

Amgen 1990 (0:19): "Look how Amgen is in an uptrend, while the market's in a downtrend… every time the market has a little
rally, Amgen actually rallies into new high ground." Near the low it undercut a low (a shakeout), made its final pullback,
tightened on the right side and was "one of the very first stocks to come out" — about +300–350% over the next year, he
says. He bought it on a new-high day.

### Fast rebound, then the first pullback ("pause and go")

| Stock | His description | Time |
|---|---|---|
| Cisco, 1990 | Took out its IPO lows, "ripping back… in new highs in just 10 days"; bought the first pullback as it turned up near $30, sold just above $35 — "then the stock went up 70,000% and would have never stopped me out" | 0:32 |
| Peloton, 2020 | Took out its IPO lows, "back in the high ground in 18 days", pulled back, bought as it turned up; 30s to ~$140 in about six months | 0:33 |
| DocuSign, 2020 | Back to the 200-day, new high ground "in just 10 days"; a pause, then go; ~100 to ~300 in five and a half months | 0:34 |
| Teladoc, 2020 | Through the COVID crash it "didn't even close below the 50-day moving average"; back at new highs "in three days" | 0:35 |

The entry is the same each time: the first pullback after the reclaim of new highs, bought as it turns back up.

### Lead and rest (Netflix, 2008–09)

Netflix more than doubled while the S&P 500 went on to a lower low (0:40). Then, as the market rallied, Netflix based and
its **RS line lagged**. "This is where it gets a little tricky… they misread relative strength… This is the one time that
you… don't need that because you had it so strong already… the market is catching up to the stock. During this period
you're going to underperform. Don't worry about it. Just wait for it to form a base and buy that base coming out." The
condition: "if it doesn't break out and take off from there, then it's not sustainable and you just cut and you run."

### Failure reset (Dick's Sporting Goods, IPO base, 2002–03)

A textbook IPO cup with handle (pivot 22.19) never broke out — it failed and took out its lows (0:46). Then guidance news
sent it "ripping off the lows", with "a really great shakeout". While **the market went to lower lows, the stock made
higher lows** and tightened, volume "comes way down", then expanded on the breakout. He bought on a gap — "one of the few
times that I bought on a gap… this gap was not that far from the base". Lesson: "you don't want to walk away from a stock
just because… it falls apart a bit. If the fundamentals are there, if it resets…" (0:49). Ritchie, later: "it goes from
looking terrible to perfect" in about a month (0:58).

### A higher, tighter pivot (Ollie's, 2016)

Out of a cup with handle and VCP while the market made a lower low: a coincident cheat entry, then a **second pivot higher
up**, tighter, with volume "negligible" at the pivot — "the setup's even better now… you could be adding to your position
here, or… take a new position" (0:43). Pivots can step from the lower third to the middle and upper third of a base.

### Others named

- **IPO primary bases**: Amazon, September 1997 — "nobody wanted Amazon here" (0:44). BLTE (2022): "practically doubled…
  in like three days"; it gapped above his buy point and he passed — "I don't chase gaps, I don't chase stocks extended" —
  then missed a re-entry two days later: "a big mistake" (0:45).
- **Power play** (Ritchie, a smaller cap): doubled, "got really, really tight", one day of volume drive (0:37).
- **Chipotle 2010**: held up through the flash crash and built a base — "coincident to confirming" (0:30).
- **Alibaba 2017** (Ritchie): a primary base through an 18-month sideways market; "almost doubled before even closing below
  its 50-day" (0:50).
- **PCYC** (Ritchie): a $3 stock that broke out "the day the market made its low, January 20th" **[inferred: 2016]** (1:00).

## 5. Execution

- Buy on the breakout through the pivot, or at the cheat area; a new-high day out of a sound base (Amgen).
- **No chasing**: no gaps, no extended stocks — with the Dick's exception, a gap "not that far from the base".
- **Scale out of tradable moves**: PBF Energy in 2022 was a cyclical, maybe "just a tradable move"; he scaled out "as it went
  up" and kept 34% of a move that reached 50% (0:23). "I want the short-term moves to even be able to, on their own, get to my
  goal."

## 6. Risk and exposure

- **Progressive exposure**: toes in the water first; ramp up only as the first trades work; back to cash when they don't
  (§2.3). Patience, then aggression — Ritchie can "wait and wait and wait, and then strike at a moment's notice and go from
  being coy to super, super aggressive"; in mid-2022 he was "full chicken" (0:57).
- **Losers are part of it**: "of course, I had lots of losers too. And I managed that risk" (0:26).
- **Know you're wrong fast** — the "right price" is a level where the stock moves quickly either way (0:54).

## 7. Management and exits

- Sell into strength on short "tradable" moves (PBF); hold true leaders for the bigger move — in several examples Ritchie held
  longer and made more (the power play, Alibaba).
- **Multiple chances in a big winner**: a second base, a third; "sometimes the later-stage base… you get these blow-off
  moves, you actually make a faster profit, because they're in the blow-off stage" (0:51). "Don't think that you've missed it."

## 8. Process

- **Real-time examples only**: about 90% of the 500-page workbook's examples are his own trades, made "without the benefit
  of hindsight" (0:26). He shows mistakes on purpose (Lumber Liquidators, BLTE).
- **Same rules across nine bear markets**: "the same rules, the same techniques the entire time for the better part of over
  30 years… for the first six years, I didn't know what I was doing" (0:15).
- **Shut off the news** (Ritchie): "let the stocks guide you"; listening to recession talk makes you "pass on what will wind
  up being a phenomenal trading opportunity" (1:00).
- **Put in the work daily**: the next setups "might be three to six months… but it could be three to six days" (0:59).
- **How skill grows** (Ritchie): see a pattern, trade it tentatively, make a little — "when I see that again, I'm really gonna
  get aggressive" (1:01).

## 9. Checked against stored data

### 9.1 His named examples

| Claim | What the stored prices show | Verdict |
|---|---|---|
| Teladoc never closed below its 50-day in the COVID crash; back at new highs in three days | 0 closes below the 50-day from 20 Feb to 31 Mar 2020. Its lowest close of that window (21 Feb) was only 3.3% off its high, and a new closing high came 2 sessions later | Accurate |
| DocuSign back at new highs in 10 days | 13 sessions after its 12 Mar 2020 low (−24.9%) | Close |
| Peloton back at new highs in 18 days | 38 sessions after its 12 Mar 2020 low (−41.7%), against its prior 52-week closing high | Not as stated (may depend on the reference high) |
| Cisco back at new highs in 10 days, 1990 | 9 sessions after its 10 Oct 1990 low | Accurate |
| Amgen in an uptrend while the market fell, 1990 | +2.6% vs S&P 500 −19.9% (16 Jul – 11 Oct 1990), 14 new 52-week closing highs during the fall | Accurate |
| Netflix more than doubled while the S&P made a lower low | +105.7% vs SPY −9.7% (20 Nov 2008 – 9 Mar 2009) | Accurate (he said 125–150%; depends on start) |
| Amazon turned up in 2002 before the market | +56.6% vs SPY +0.7% (23 Jul 2002 – 11 Mar 2003) | Accurate |
| Chipotle held up through the 2010 correction | −4.0% vs SPY −16.1% | Accurate |
| Ollie's against a falling market, 2015–16 | +18.7% vs SPY −13.3% | Accurate |
| PBF ("BBT" in the transcript): 50% available, 34% taken | From the 24 May 2022 close, the high within 10 sessions was +45% | Consistent |

### 9.2 The rule behind them — already tested here, and it failed

[Relative strength](learn-price-rs.md) §4.3 ran the population-level version on every liquid stock in the three most
recent ~20% sell-offs (US 2022, US 2025, India 2024–25). **The stocks that held up best did worse afterwards than the typical
stock**; the "leaders at the low" (RS line and price near highs) underperformed the rest over six months in all three; and
stocks that made a new 52-week high within 30 sessions of the low did no better. Who held up was mostly sector and low beta:
energy in 2022 (PBF, Marathon Petroleum, ConocoPhillips, Exxon), gold miners and utilities in 2025.

The entry he builds on it — the fastest stocks back to a new high, bought on their first pullback — failed its own
[event study](minervini-fast-rebound-study.md) over every 15%+ correction since 2001 (US) and 2006 (India). Six months out it
matched the average Stage 2 stock bought the same day (US +0.1%, India +0.0% at the median; no setting with |t| above 1.5),
trailed the index, and did no better than buying the same stocks on their new-high day. DocuSign, Moderna and Novavax are in
the sample, as the tail: the median trade lost its full 1R.

**Reading the two together [inferred]:**

1. His examples are real, but chosen from the winners — a survivorship view. The base rate for "held up" is what §4.3
   measures.
2. His own 2022 toe-in-the-water in oil names *is* §4.3's 2022 result seen from inside: the strongest stocks at the low were
   cyclicals; they made quick moves, failed, and he went back to cash. His process survived the failure because of the
   **feedback rule** (§2.3), not because the screen picked well.
3. §4.3 tests one ingredient. His method conditions on more — Stage 2, a sound base, a pivot breakout, a follow-through day,
   then sizing by results. The full mechanical version here (the `minervini_spec` strategy) found little or no edge —
   expectancy within a few hundredths of R of zero; the one rule that improved both return and drawdown was a **market
   filter**, and **progressive exposure** on its own cut the US
   drawdown from −43.5% to −34.6% ([strategy families](app-guide-strategy-families.md) §3; the strategy's 1.6–1.8
   changelog).
4. So the most *defensible* part of this talk is the regime discipline: wait for proliferation and early successes, size by
   your own results, go back to cash fast. The least defensible part is the selection claim "the stocks that go down the least
   are going to be the ones that go up the most".

### 9.3 Selling a breakout that fails at once — checked on a backtest trade (2026-11-10)

The question came from a chart review, not a clip: on a trade that turns down right after the buy, would he wait for the
stop? The trade is Manappuram Finance (NSE), S1 in India run #3754 (1.57, optimise window). It was bought on 4 May 2018
at 126.94, with the pivot at 124.5 and the stop at 115.90, 8.7% away. It was stopped on 15 May for −1.04R.

| Date | Bar |
|---|---|
| 3 May | Breakout above 124.5 on 2.8× the 50-day average volume |
| 4 May | Bought on the close, 126.94 |
| 9 May | New high of 130.45 intraday, closed at 126.25 on 2.7× volume: an up-and-reverse day |
| 10 May | −4.1% to 121.05 on 1.7× volume: the biggest down day since the buy, closing back inside the base below the pivot |
| 15 May | Stop hit at 115.90 |

**His reading [inferred]:** 9 and 10 May are the post-breakout violations he describes selling on: a heavy-volume
reversal, then the largest decline since the breakout, on volume, back below the pivot. He also aims for an average loss
of about 5–6%, and this stop was wider. Selling at the 11 May open (121.95) would have cost about −0.45R.

**Measured:** the strategy already tested and switched off the mechanical versions. These are EX-02, a close back below
the pivot (`FAIL_DAYS`, about 80% of trades sold in 1.7 at about −0.3R each), and EX-02b, a close below the 20-day
(`FAIL_SMA20_DAYS`, off since 1.31). A replay of the stricter, volume-qualified version on the baseline trades
(2013–2021; India #3754, US #3758; each trade alone, sold at the next open) also lowered the average R:

| Exit rule | India avg R (323 trades) | US avg R (1,255 trades) |
|---|---|---|
| Hold to the stop (current) | **+0.20** | **−0.04** |
| Close below the pivot within 5 sessions | +0.08 (117 sold) | −0.045 (292 sold) |
| Down close below the pivot on above-average volume, within 3 sessions | +0.135 (24 sold) | −0.045 (86 sold) |
| Same, within 5 sessions | +0.14 (32 sold) | −0.045 (124 sold) |
| Same, within 10 sessions | +0.14 (44 sold) | −0.044 (166 sold) |

In India the trades the 5-session volume rule sells would have finished at **+0.26R on average** if held, because some
recover into 2R+ winners. Sold early they average about −0.40R. Manappuram is the case where the early sell helps, and
across the trades those cases are outweighed.

**A second case, and a second rule: down days in a row.** Marico (NSE) was S6 in the same run. It was bought on 24 Aug
2018 at 382.92, the day after a +5.4% breakout on 2.3× volume, with the pivot at 374.75 and the stop at 357.70, 6.6% away.
It then closed down four sessions running, 24 to 29 Aug, and was back below the pivot on 28 Aug. It drifted lower and was
stopped on 4 Sep for −1.06R. Here the warning is a run of down days rather than one heavy-volume break. His "more down days
than up days" after a buy is that violation. Each rule below sells at the next open, counted from the session after the
buy, in the same replay:

| Exit rule (within 10 sessions unless noted) | India avg R | Sold | US avg R | Sold |
|---|---|---|---|---|
| Hold to the stop (current) | **+0.20** | — | **−0.040** | — |
| 3 down closes in a row | +0.04 | 100 | −0.035 | 177 |
| 3 down closes in a row, close below cost | +0.15 | 71 | −0.031 | 131 |
| 4 down closes in a row | +0.15 | 31 | −0.052 | 62 |
| 4 down closes in a row, close below cost | +0.20 | 28 | −0.039 | 48 |
| More down than up days (3+), below cost, within 5 sessions | +0.19 | 71 | −0.034 | 163 |
| Same, within 10 sessions | +0.16 | 102 | −0.038 | 216 |

The rules that catch Marico cut it from −1.06R to −0.48R. In the US they help by under 0.01R; in India every one lowers
the average, and the plain three-down rule sells trades that would have averaged +0.44R. No version improves both
markets, so none is proposed.

**Takeaway [inferred]:** as a mechanical rule, holding to the stop is better here. His early sells likely rely on context
the rule cannot see: the market's tone, his recent results, and the whole chart. Not adopted, and nothing queued. A
narrower test that remains is a tighter cap on the initial stop, aiming at his 5–6% average loss, rather than an early exit. `MAX_STOP_PCT` (SL-03) skips fills with a stop more than 10% away, and no tighter value has been run.

### 9.4 Scoring a VCP on several dimensions — checked on the backtest trades (2026-11-10)

The question came from a chart review: Zydus Lifesciences (NSE) was bought as a cheat on 4 December 2014 and stopped
on 17 December for −1.05R. Why was it a base at all, and could a multi-part score have rejected it?

**Why it was a base.** The detector starts a base at the first high the price has not beaten. Here that was ₹352.03 on
11 November 2014, after a 22% run in 20 sessions. The base was 16 sessions, 15.5% deep, one pullback, and the stock's
third base. It failed the VCP test (VCP-04, two pullbacks needed). It was bought as an **S4 cheat**, which only needs a
tight shelf (₹302.32–323.59) in the middle third of a base that clears VCP-01 to VCP-03. A cheat buys before the VCP
finishes, so it does not require one. **[inferred]** Minervini would likely call this a single pullback after a
spike, not a base that has contracted.

**Measured.** Each trade of runs #3779 (India, 324 trades) and #3790 (US, 1,072), 2013–2021, joined to its base's stored
measurements:

- **Most dimensions did not separate winners from losers** among trades the rules already accept. That covers base
  length, depth, final tightness, volume dry-up, base number, the run into the base and RS rank. Each was flat,
  contradicted itself between markets, or moved less than the noise (about ±0.4R per tercile in India).
- **A full VCP did worse**: India +0.12R against +0.16R for the rest, US −0.31R against −0.01R. A score rewarding the
  textbook pattern would point the wrong way.
- **One dimension held in both markets:**

| Cheat entries (S3, S4) | India avg R (trades) | US avg R (trades) |
|---|---|---|
| Base with 1 pullback | −0.02 (24) | −0.08 (82) |
| Base with 2 or more | +0.38 (91) | +0.05 (197) |

**What was done.** No composite score: its weights would be fitted to noise. The one rule became a research switch,
`CHEAT_MIN_CONTRACTIONS` (1.63, off). Set to 2, it refuses both Zydus cheats. Optimise runs #1451 (India) and #1452
(US) are queued ([CAGR gaps](minervini-cagr-gaps.md)). The rule was sliced from the same window, so those runs can
only rule it out; a pass earns one verify run with criteria written first.

**On the chart.** The chart's setups drawing applies the same check, so the frame agrees with the backtest. With the
switch on, a cheat's card gets a *Pullbacks* row ("1, at least 2"). A one-dip cheat then reads "trade skipped" and
the card gives the pullback count as the reason. With the switch off, which is the default, nothing on the chart changes. Checked on
Zydus, Marico, Britannia and Manappuram: only the one-pullback cheats change, among them Zydus's 2001 and Britannia's
2013.

**Textbook cheats disagree (event study, 2026-11-10).** Rebuilt from stored prices with no strategy code, 2014–2026,
liquid stocks: a 5-session shelf at most 8% wide, in the lower two thirds of a 10–40% base, quiet volume, above a
rising 200-day; buy the next open, stop under the shelf, measured at the stop or after 40 sessions. Pullbacks are
4% dips on closes.

| Base before the cheat | India avg R (n) | US avg R (n) |
|---|---|---|
| 0–1 pullbacks | +0.23 (2,902) | +0.02 (8,100) |
| 2+, each shallower | +0.17 (1,643) | −0.01 (3,495) |
| 2+, other | +0.20 (2,939) | +0.05 (6,581) |

No split, in either half of the period or either third of the base; short one-dip bases like Zydus's did no worse.
The strategy-trade split above rests on 24 India and 82 US one-pullback cheats, so it is likely noise. Expect
#1451–1452 to fail; the Learn guide now says the count is a way to read a chart, not an edge. Script:
`cheat_study.py` (session scratchpad, not kept).

## 10. How it compares

- **With the repository's Minervini implementation**: the spec covers the Trend Template, the VCP, pivots, stops, the market
  filter (MKT-01) and progressive exposure (PE-01 to PE-04). Not yet encoded: the predictive / coincident / confirming
  timing, the "fastest rebound then first pullback" entry, *lead and rest*, *failure reset*, IPO primary bases, and a
  Trend-Template **count** as a market gauge.
- **With [Martin Luk](creator-martin-luk.md)**: both probe small before committing and want broadening before going long.
  Minervini reads a bottom from the stocks that *refuse to fall*; Luk from the *panic* in the ones that do.

## 11. Open questions

- The "96%" / "upwards of 90%" statistic: which universe, which years, what counts as a correction.
- "Confirmed Stage 2 = five months": is it the template holding for five months, or a five-month-old 200-day uptrend?
- What "fastest rebound" means numerically — his examples ran from 3 to 18 days to a new high.
- How "corrected the least" interacts with beta: is a defensive stock that held up a leader, or just low-beta?

## 12. The team's own trades, 2025–26 (second source)

*TraderLion podcast, recorded about 15 June 2026: Mark Ritchie II and Brandon Hedgepath (Minervini Private Access
portfolio managers, trading as a team since about 2011, "$100,000 into $20 million" over 15 years) and Bob
Weissman (2025 US Investing Championship, money-manager division, 115%). They walk through their trades on
Minervini's charting platform. Minervini himself is not on it. Timestamps are from a local transcript; dollar
figures heard in it are marked **[unclear]** where the audio is doubtful.*

### 12.1 The trades shown

| Stock | Their entry | What they bought | How they sold | Our strategy on stored data |
|---|---|---|---|---|
| Seagate (STX) | 18 Aug 2025 | First viable base after the April-low rally; tried in July and shaken out, "the base improved"; lowest-volume day of the base right before the buy (5:05) | A third at +20% "to finance the risk"; more as it stretched; last piece on a close under the 50-day, ratcheted up (15:45) | **Caught**: S8 (flat base coiled) on 13–15 Aug, tradable |
| Vicor (VICR) | Dec 2025 | A "pause pivot" after three lower lows following an earnings power move, RPR 98; bought the break of the pause two days later (19:18) | Pieces into back-to-back extension days; held a remainder through earnings on the cushion (22:32) | **Missed**: VCP-08 (not tight enough) all week |
| Fluence (FLNC) | — | Missed the first breakout off the 50-day; bought the low-volume 1-2-3 pullback to the cheat area plus an inside day (35:19) | Leaked out into strength; last piece on the earnings gap down | Not scored (no date given) |
| Modine (MOD) | 7 Apr 2026 | Pullback buy on the market's follow-through day; added on the gap; volume dry on the pullback (40:23) | A piece at +15–20% before the first natural reaction; more on the earnings gap; rest on a backstop at the gap day's low (41:53) | **Missed**: VCP-06 (contractions not shrinking enough) |
| Arm (ARM) | 13 May 2026 | Early turn after three lower lows, out of a multi-year base to all-time highs; small size; trend stage not yet confirmed (50:22) | A quarter at +17.75%, a quarter next day, rest the day after: +40% in days (53:28) | No stored prices |
| IREN | 15 Aug 2025 | Weissman, short-term: new all-time high out of a three-year base, then the first setup; intraday entry (56:49) | Out in 4–5 days, before earnings, +10–15% | **Missed**: G4 (averages not yet stacked) |

### 12.2 What they add to this note

**Selection**

- **Bottom-up, never theme-first** (7:22): run the screens, and the theme shows up in what passes, not the other way
  round. Correlated names breaking out the same day are fine; manage the total risk, not the group.
- **Relative performance near the top**: their names are RPR 98–100, a 1–100 rank of every stock against every other
  (19:30, 34:46). A stock's first move to an **all-time high out of a long dormant base** is what puts it on the radar
  (50:27, 61:04).

**Entries**

- **More entries than the pivot breakout:**
  - a **pause pivot** after three or four lower lows, where a stock under accumulation stabilises (20:03, 51:27);
  - a **pullback buy** to the cheat area or the 50-day, on low volume, confirmed by an inside day or a turn (35:19);
  - an **early turn** for a power play or a big base, before the trend stage confirms (51:51).
- **Buy incrementally between two pivots**: the first reversal high, then the range high (12:22).
- **Pay up to be right**: "I'd much rather pay up 1% to be sure that the stock is free and clear" (12:44).
- **No big gap**: a 12–13% gap clearing a base is passed; a 3–4% gap through a pivot is fine (46:26, 47:11).
- **A buy should prove itself fast**: "pretty much all our losers look the same, it doesn't work within one to five
  days, max, probably five to ten. We're gone" (35:48). But a stock "acting normal" is held: there is no reason to
  sell without a violation of the rules (11:05).

**Sizing and exposure**

- Their Seagate position was **7.5%** of the account (9:48), small because their results were not yet good. "If I
  have a tight entry and I'm running hot… I'm coming in big right off the hop. If things aren't working… I'm going to
  start smaller" (10:31): sizing follows **their own results**, not the index.
- **The stocks over the index** (54:28): in June 2026 they bought breakouts on the day they shorted the S&P 500 and
  the Nasdaq 100, as a hedge on their long book during an 8% index pullback, not as a market call. The index is
  context; the leaders' own action decides.
- Weissman made about 80% of his 2025 gain in August–October (56:49); Minervini was in cash for half of 1997, the year
  he won with 155% (57:20).

**Management and exits: the part most specific to this source**

- **Sell part early to finance the risk**: a third (or a quarter) at about +15–20%, which makes the rest a "free
  roll" (15:45, 53:28). Its purpose is to **sit through the first natural reaction** without pressure (41:21).
- **Then sell into strength in steps** as the stock stretches from its averages, measured against the stock's own
  historical extension levels, "multiples and multiples of our risk" (17:14).
- **A backstop on the gap day's low**: after a news gap, put the stop at that day's low; if the momentum continues,
  it keeps you in; if the gap fills, it takes you out. Ratchet it up intraday when the move goes vertical (42:40, 43:13).
  No resting trailing stop.
- **The last piece on a close below the 50-day**, ratcheted higher once enough has been made (15:45).
- **Earnings**: "never hold an overweight position into an announcement" (23:40). Hold through only with profit
  already banked; how much is a personal "pillow factor" (25:13). Broadcom (Dec 2025) fell on record results; they recalled "about a 15 or 16 or 18% gap". Stored prices show a 6.5% gap
  down, 11% lost on the day and 21% within a week. They had trimmed into the rally and broke even on the rest (25:52).
- **Why sell into strength** (Weissman, 38:03): the equity curve. Return is judged against risk, and a stock that is
  sold and keeps rising costs less than one held through a 20–30% reaction, because the capital moves to the next
  low-risk setup.
- **The target**: about a 50% win rate with the average win twice the average loss (39:48).

### 12.3 Against this strategy and its backtests **[inferred]**

- **Caught one of four testable entries.** The breakout of a finished base (Seagate) is caught. The pause pivot
  (Vicor), the pullback buy (Modine) and the early turn out of a long base (IREN) are not entries this strategy has.
  The early turn fails the Trend Template by design; the other two fail the VCP's tightness or shrink rules.
- **Selling part at +15–20% conflicts with the backtests**, and only in part. Here a third sold at +2R (about the
  same point, with a 7% stop) cost about 0.1R a trade in the India replay (nothing in the US), and moving it to +3R changed portfolio CAGR by under a point
  ([CAGR gaps](minervini-cagr-gaps.md) §3, Results). Their reason is not expectancy but sitting through the first
  reaction and through earnings. The backtest does not hold into earnings differently, so it cannot see that benefit.
- **Their fast cut contradicts the measured time stop.** The coded time stop (+1R within 15 sessions) cost
  expectancy. Their "doesn't work within five to ten days" is a judgement of how the stock acts, which the time stop
  does not capture.
- **Their market view supports the book cases**: the index gate refuses most of Minervini's book trades. They keep
  buying the leaders and hedge with an index short instead of stopping. A hedge is not modelled here.
- **New and testable**: the gap-day backstop, an earnings rule for held positions, a stop raised to the first natural
  reaction's low, the pause pivot and the pullback buy. See [swing longs](system-swing-longs.md) for how each is
  proposed.
- **The gap-day backstop, tested (2026-11-11): rejected.** Built as a research switch (1.60: from +2R or +3R, a gap
  of at least 1 ATR moves the stop to the gap day's low and ratchets on later gaps). Optimise runs #1419–1425, 2013–2021,
  in-sample. It lowered CAGR in every pairing, in both markets:

  | Variant | India CAGR / max DD | US CAGR / max DD | Compared with (India · US) |
  |---|---|---|---|
  | From +3R, with the 150-day exit | 5.77% / −15.4% | −0.58% / −26.5% | 8.26% / −20.9% · 3.08% / −23.9% |
  | From +2R, with the 150-day exit | 5.82% / −15.3% | −1.84% / −32.6% | the same |
  | From +3R alone | 2.67% / −14.7% | −4.08% / −40.7% | 3.71% / −20.1% · −3.30% / −40% |
  | US: lean exits + 150-day + backstop | — | 1.13% / −24.4% | 5.02% / −25.9% |

  It keeps more of each gain and cuts India's drawdown by about 5 points, but a filled gap is a normal day for a
  leader, so it sells the winners the 150-day exit is there to keep. **[inferred]** The team applies it with judgement,
  intraday and on news gaps they read; a mechanical rule on every 1-ATR gap is not that. The switch stays off
  ([CAGR gaps](minervini-cagr-gaps.md)).

### 12.4 The platform's indicator bands, and the version built here (2026-11-10)

The podcast's charts are on Minervini's own platform (Minervini Markets 360). Its indicator panel, read from a
frame of the Fluence chart, has colour strips named **Minervini RPR**, **Minervini Pressure**, **Minervini Buy Risk
(Colors)** and **Minervini TTR (Colors)**, plus a news-alert count. The page header shows an ER and an SR score
(FLNC: ER 42, SR 91). None of the formulas is published. What is known:

| Strip | What it appears to be | Source |
|---|---|---|
| RPR | "Relative performance ranking… rating every stock against every other stock, not the indexes" (21:10); leaders read 98–100 | The speakers |
| Pressure | Whether a stock is "under pressure" (34:46): selling outweighing buying | The speakers; third-party TradingView copies describe it as accumulation vs distribution |
| Buy Risk | Green, yellow or red by distance above the 50-day; one copy uses 0–15% / 15–25% / over 25%, and "broken" below the 50-day | Third-party copies only |
| TTR | Not defined anywhere found; most likely a Trend Template rating | Inferred |
| ER / SR | Probably earnings and sales ratings | Inferred |

**Built here:** the chart's *Trend-health bands* indicator, three strips in the same style. Our thresholds are
choices, not his, and are adjustable.

- **Pressure:** volume on up closes ÷ volume on down closes over 20 sessions; green ≥ 1.25, red ≤ 0.8.
- **Buy risk:** distance above the 50-day; green 0–15%, amber 15–25%, red over 25% or below the 50-day.
- **Trend Template:** how many of the Stage 2 screen's eight criteria the bar meets, run by the screen's own code on
  the server; green 8, amber 6–7, red 0–5. C8 uses the per-stock RS floor, because a chart sees one stock.
- **RS rank (RPR's counterpart):** not yet. Ranking the market on the fly takes about 34 s for India, so a
  separate session is adding a weekly stored rating and a fourth strip.

**Measured** (liquid US and Indian stocks, each Friday June 2014–July 2026, next 3 months vs the average stock; full
table in the [trend indicators](learn-ind-trend.md) guide, "Trend-health bands"):

| Colour | US | India |
|---|---|---|
| Trend Template red (0–5 met) | −0.5% (t −3.5) | −1.1% (t −6.5) |
| Trend Template green (8 of 8) | +0.7% (t 1.6) | +1.5% (t 3.6) |
| Below the 50-day | −0.1% (t −2.0) | −0.7% (t −5.6) |
| More than 25% above the 50-day | −3.0% (t −3.1) | +1.6% (t 1.8) |
| Pressure red (≤ 0.8) | −0.1% (t −0.6) | −0.3% (t −3.2) |

**Reading it [inferred]:** the Trend Template strip does the sorting, mostly by marking the stocks to avoid.
"Extended" pointed opposite ways in the two markets, so it is not a sell rule on its own. Pressure mostly repeats
RSI (median correlation 0.71) and added little. On Marico in August 2018 the strips turned in order: all green on the
breakout day, pressure amber within four sessions, then pressure and buy risk red on the day it was stopped. That is
the "under pressure" read he describes, but §9.3 measured selling on it and it lowered results.

## 13. Abercrombie & Fitch, January–February 2021: volume markers and adding on reactions (third source)

*A 6½-minute clip in which Minervini walks through his own ANF position on daily and weekly eSignal charts. The
charts end on 24 February 2021 (last price $28.43, the stored close that day), so it was recorded on 24 or 25
February. Timestamps are from a local transcript. Prices below are stored daily bars; his own prices are not on
screen. Where a buy price is worked back from the percentages he gives, it is marked **[inferred]**.*

### 13.1 The trade

| Step | Date | What he did (timestamp) | Stored prices |
|---|---|---|---|
| Base | late Nov 2020 – early Jan 2021 | A **low cheat**: a shelf near $20–21 in the lower part of the base (0:48) | 17–31 Dec at 0.45–0.55× the 50-day volume |
| Passed | 4–5 Jan | "Almost buying it" on the 4th and on the 5th's reversal outside day, but held off: it "was wedging up a bit and didn't really form the right side fully" (0:57, 1:16) | 5 Jan: range $20.26–22.12, 1.2× volume |
| Waited | 6–8 Jan | It ran to $22.69, then pulled back "to the top of that breakout" (1:16) | 8 Jan: low $21.01, high $21.91 |
| **Buy 1** | 11 Jan (Mon) | Bought as it went above Friday's high (1:28) | Through $21.91; closed $23.04 on 2.0× volume |
| Traded around it | Jan | Sold some into the rally and bought back; "pretty much the exact same decisions" if you only built the position (2:09) | — |
| **Buy 2** | about 2–3 Feb | First natural reaction "came right to the top of the cheat"; an inside day, then the turn back up (2:27) | 1 Feb low $22.29; his +17% implies about $24.3 **[inferred]** |
| **Buy 3** | 11 Feb | Second reaction to the 20-day, turning up (2:45) | 10 Feb low $24.18 = the 20-day; above $25.03 on the 11th |
| Status | 24 Feb | Up about 30%, 17% and 11% on the three buys, about 20% on the position (5:16) | $28.43 |
| Plan | — | After **one to three natural reactions**, sell into strength if the advance accelerates (5:42) | 8 Mar: +8.8% on 2.0× volume; peak $37.88 on 18 Mar; $30.24 a week later |

He calls it a value turnaround, in vogue with the rotation from growth into value (6:08).

### 13.2 What it adds to this note

- **Buy on the way up, never on the way down** (1:45): "even though I may be buying a pullback, I'm still waiting
  until the stock turns up." The trigger is the prior day's high.
- **Waiting for the right side**: he skipped a valid-looking early entry because the base had not finished its right
  side and the move was wedging. He then bought the pullback to the top of the cheat breakout.
- **Pyramiding on natural reactions** (2:45): each add comes on a pullback to support, either the top of the earlier
  pivot or the 20-day, bought as the stock turns up. This differs from the add at a new, higher pivot (§4, Ollie's).
  There is no new base, only a reaction inside the advance.
- **Volume markers, read on the weekly** (3:20): "institutions are buying over a number of days", so their footprint
  shows on weekly bars. He wants a **selling vacuum**: few down weeks on above-average volume, and any he sees on the
  *left* side of the base, not the right side, where "supply should stop coming to market" (4:52). A down week that
  closes above the middle of its range is "not even a selling week… that's actually an accumulation week" (4:27).
- **The first volume spike off the low is not a buy** (3:48): the big up week off the bear-market low is skipped
  until the Trend Template holds (above a rising 200-day; "stage two, early turn").
- **Selling is counted in reactions**: one to three natural reactions, then sell into strength on an acceleration.

**Checked against stored weekly bars.** His reading is exact. The base has one down week on above-average volume:
4 Dec 2020, −5.9% on 1.29× its 10-week average, closing at 57% of its range. The right side then ran at 0.67×,
0.55×, 0.47× and 0.45×, and the breakout week at 1.45×. The spike he skips is the week of 28 Aug 2020: +21.8% on 2.6×.

### 13.3 Against this strategy and its backtests **[inferred]**

- **The entry is caught, on his day.** The strategy flags ANF on 11 Jan 2021 as a near-miss VCP (S7). The miss is
  VCP-08: the tight area was only two sessions old, short of the five it needs. It fills at the next open, $23.01,
  with a stop of $20.90. Run alone, the backtest holds it to 21 May and sells on the close under the 50-day at
  $34.48: **+5.4R**. Its strength sale (a third at 25% over the 50-day) falls on 9 March, the acceleration he planned
  to sell into.
- **But the full US run never takes it.** On 11–12 Jan 2021 the 8-position cap was full. ZBRA and SAIA (both S8,
  higher RS) took the last slots. Separately, the "no near-miss" candidate in [CAGR gaps](minervini-cagr-gaps.md)
  would drop this trade. It is one trade, not evidence either way.
- **Weekly volume markers do not separate our trades.** Every traded base in the 1.56/1.57 optimise runs (US 1,255
  trades, India 323) was split by its weekly bars:
  - **No right-side distribution week** (down, above-average volume, closing in the lower half of the range): US
    −0.05R over 1,012 trades against about −0.01R for the 243 with one or more. India +0.13R over 240 against +0.57R
    for 63 with exactly one.
  - **Quietest third of right sides** against the loudest: US −0.04R against +0.01R; India +0.12R against +0.14R.

  The strategy already requires a daily dry-up (VCP-10), so the weekly reading adds nothing measurable here. Not
  proposed as a filter.
- **Adding on natural reactions is mixed.** This replay adds to each held, profitable trade:
  - **Trigger**: a pullback of 5% or more from the trade's high, to within 2% of the 20-day and above the 50-day.
  - **Fill**: the turn above the prior day's high, at most two adds, with a new high needed between them.
  - **Stop**: under the reaction low. Otherwise the add leaves with the trade.

  | Run (optimise, 2013–2021) | Adds | Mean R per add | Median | Won | Stopped at the reaction low |
  |---|---|---|---|---|---|
  | US, 1.56 | 260 | −0.22 | −1.00 | 23% | 65% |
  | US, 150-day after +3R | 212 | +0.11 | −1.00 | 21% | 73% |
  | India, 1.57 | 159 | +0.47 | −1.00 | 31% | 57% |
  | India, 150-day after +3R | 126 | +2.85 | −1.00 | 33% | 58% |

  India's +2.85R comes mostly from 2020–21 (42 adds at about +8R). Over 2013–19 it is about +0.35R an add. The replay
  ignores partial sales and cash, so it is a screen for whether to build the rule, not a result. See
  [swing longs](system-swing-longs.md) §6.

## 14. Source log

| Date | Source | Length | Notes |
|---|---|---|---|
| Late June–July 2022 **[inferred]** | Webinar, "How to Spot Leading Stocks in a Bear Market", with Mark Ritchie II; moderator Bob Weissman; sponsored by MarketSmith / Investor's Business Daily | 63 min; first 4.5 min promotional | Date from internal clues: he is 57 and started in 1983; "we are in the bear market"; the PBF trade of 24 May 2022 was "recent", followed by the market's new low and a return to cash; BLTE (listed spring 2022) "just recently"; the Master Trader Program "in November", its 12th or 13th year since 2010. Transcribed locally; video at 144p |
| ~15 June 2026 | TraderLion podcast, "Trading $100K Into $20 Million With Only One Setup: The VCP Strategy"; Mark Ritchie II, Brandon Hedgepath, Bob Weissman; host Richard Moglen | 72 min; sponsor read 13:43–15:01 | Date from the transcript ("the middle of June here, June 15th"; a 12 June IPO "yesterday"). Charts on Minervini's platform (RPR, "trend stage", pressure and buy-risk bands, news count). Transcribed locally (Whisper small.en); frames read at 480p, so chart dates are from the speakers, not the screen |
| 24–25 Feb 2021 **[inferred]** | Short clip, Minervini on his Abercrombie & Fitch (ANF) position: "volume markers" on daily and weekly charts | 6.5 min | Date from the charts, which end on the 24 Feb 2021 close ($28.43). eSignal daily and weekly charts at 442×360, so chart dates are read against stored prices. Transcribed locally (Whisper small.en) |
