# Mark Minervini — research notes

*Raw material, synthesized: what Mark Minervini teaches in his talks, organized by the creator template
([Martin Luk](creator-martin-luk.md) §0), with timestamps. Everything below is **his** view and **his** numbers
unless marked otherwise; co-presenter Mark Ritchie II is named where the point is his. My inferences are marked
**[inferred]**, audio the transcript does not settle **[unclear]**. Claims about named stocks were checked
against stored prices (§9).*

*This repository already implements his VCP rules in detail ([the backtest spec](minervini-backtest-spec.md),
the `minervini_spec` strategy, [SEPA and the VCP](learn-strat-vcp-sepa.md)). This note records what the talks add
beyond those — here, **how he finds the next leaders while the market is still falling**.*

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

## 12. Source log

| Date | Source | Length | Notes |
|---|---|---|---|
| Late June–July 2022 **[inferred]** | Webinar, "How to Spot Leading Stocks in a Bear Market", with Mark Ritchie II; moderator Bob Weissman; sponsored by MarketSmith / Investor's Business Daily | 63 min; first 4.5 min promotional | Date from internal clues: he is 57 and started in 1983; "we are in the bear market"; the PBF trade of 24 May 2022 was "recent", followed by the market's new low and a return to cash; BLTE (listed spring 2022) "just recently"; the Master Trader Program "in November", its 12th or 13th year since 2010. Transcribed locally; video at 144p |
